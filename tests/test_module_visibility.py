"""Política de acesso: visibilidade estrutural por módulo (menu/rotas/deep
links), personalizável pelo Administrador Geral em "Configuração → Regras →
Visualização" (mesmo armazenamento do framework, sem tabela nova) — por
perfil e, para Administrador Local/Gestor de EPI, também por Unidade.

Cobre a combinação `config (padrão + override do tenant, por perfil e por
Unidade) AND permissão técnica` em epi_backend/rule_engine.py e
modules/settings/service.py — a regra que garante que a configuração
administrativa nunca amplia o que a permissão técnica do perfil já não
autoriza. module_visibility é a ÚNICA fonte de verdade para
tenant+perfil+unidade+módulo: não existe mais um module_unit_scope
separado — normalize_framework_payload converte automaticamente qualquer
configuração legada que ainda o contenha, e
modules.settings.service.migrate_module_visibility_unit_model persiste
essa conversão de volta no armazenamento.
"""

import pytest

import modules.settings.service as settings_service
from core.permissions import PERMISSIONS
from epi_backend.rule_engine import (
    MODULE_KEYS,
    MODULE_REQUIRED_PERMISSIONS,
    build_context,
    default_framework_payload,
    normalize_framework_payload,
    resolve_module_visibility,
)


# ── rule_engine: regra padrão do sistema ───────────────────────────────────

def test_default_module_visibility_covers_all_canonical_roles():
    visibility = default_framework_payload()['module_visibility']
    assert set(visibility.keys()) == set(PERMISSIONS.keys())
    for role, buckets in visibility.items():
        # Toda configuração nasce só no bucket "*" (sem override de Unidade).
        assert set(buckets.keys()) == {'*'}, role
        assert set(buckets['*'].keys()) == set(MODULE_KEYS), role


def test_buyer_and_approver_are_hidden_from_estoque_entregas_fichas_by_default():
    # Restrição explícita do plano de acesso: Comprador/Aprovador continuam,
    # por padrão, sem acesso estrutural a Estoque/Entregas/Fichas de EPI —
    # mesmo tendo stock:view/deliveries:view como apoio à decisão de compra.
    visibility = default_framework_payload()['module_visibility']
    for role in ('buyer', 'approver'):
        assert visibility[role]['*']['estoque'] is False
        assert visibility[role]['*']['entregas'] is False
        assert visibility[role]['*']['fichas'] is False


def test_default_visibility_matches_technical_permission_floor():
    # Não-invasivo por padrão: quando a permissão técnica falta, o módulo já
    # nasce invisível, sem precisar de nenhuma restrição estrutural extra.
    visibility = default_framework_payload()['module_visibility']
    for role, granted in PERMISSIONS.items():
        for module, required in MODULE_REQUIRED_PERMISSIONS.items():
            if not (required & granted):
                assert visibility[role]['*'][module] is False, (role, module)


def test_master_and_general_admin_see_every_module_by_default():
    # "terceirizados" (ADR-014) e "terceirizados_colaboradores" (ADR-0002
    # §10) são opt-in: ocultos por padrão até para quem tem o piso técnico,
    # porque a subpasta só deve aparecer quando o Administrador Geral a liga
    # explicitamente por tenant.
    visibility = default_framework_payload()['module_visibility']
    for role in ('master_admin', 'general_admin'):
        modules = dict(visibility[role]['*'])
        opt_in_terceirizados = modules.pop('terceirizados')
        opt_in_colaboradores = modules.pop('terceirizados_colaboradores')
        assert all(modules.values()), role
        assert opt_in_terceirizados is False, role
        assert opt_in_colaboradores is False, role


def test_terceirizados_is_opt_in_hidden_for_every_role_by_default():
    # Condição vinculante da aprovação do ADR-014: a subpasta nasce oculta
    # por padrão em todo tenant, para todo papel — mesmo quem já tem
    # employees:create — até o Administrador Geral ligá-la explicitamente.
    visibility = default_framework_payload()['module_visibility']
    for role in PERMISSIONS:
        assert visibility[role]['*']['terceirizados'] is False, role


def test_terceirizados_can_be_turned_on_within_the_technical_ceiling():
    # Administrador Geral liga o módulo: dentro do teto técnico
    # (employees:create), a liberação vale.
    framework = normalize_framework_payload({'module_visibility': {'general_admin': {'terceirizados': True}}})
    context = build_context({'company_id': 1, 'id': 5, 'role': 'general_admin'})
    resolved = resolve_module_visibility(context, framework, PERMISSIONS['general_admin'])
    assert resolved['terceirizados'] is True


def test_terceirizados_stays_hidden_for_roles_without_employees_create_even_if_configured():
    # 'user' (Gestor de EPI) não tem employees:create — mesmo que alguém
    # tente ligar o módulo para este papel, o teto técnico bloqueia.
    framework = normalize_framework_payload({'module_visibility': {'user': {'terceirizados': True}}})
    context = build_context({'company_id': 1, 'id': 5, 'role': 'user'})
    resolved = resolve_module_visibility(context, framework, PERMISSIONS['user'])
    assert resolved['terceirizados'] is False


def test_normalize_merges_partial_override_without_wiping_other_modules():
    normalized = normalize_framework_payload({'module_visibility': {'buyer': {'estoque': True}}})
    buyer = normalized['module_visibility']['buyer']['*']
    assert buyer['estoque'] is True
    # Override de um módulo não derruba os demais (compras continua no padrão).
    assert buyer['compras'] is True
    assert buyer['entregas'] is False


def test_normalize_ignores_unknown_role_and_unknown_module():
    normalized = normalize_framework_payload({
        'module_visibility': {
            'not_a_role': {'estoque': True},
            'buyer': {'not_a_module': True, 'estoque': True},
        }
    })
    assert 'not_a_role' not in normalized['module_visibility']
    assert 'not_a_module' not in normalized['module_visibility']['buyer']['*']
    assert normalized['module_visibility']['buyer']['*']['estoque'] is True


# ── normalize_framework_payload: migração automática do formato legado ────
# Formato antigo (pré visibilidade-por-Unidade): {role: {module: bool}}
# direto, sem bucket "*"/unit_id — normalize_framework_payload converte em
# memória a cada leitura, então qualquer configuração salva antes desta
# extensão continua funcionando sem nenhuma ação manual.

def test_normalize_upgrades_legacy_flat_module_visibility_shape():
    normalized = normalize_framework_payload({
        'module_visibility': {'buyer': {'estoque': True, 'compras': False}},
    })
    buyer = normalized['module_visibility']['buyer']
    assert set(buyer.keys()) == {'*'}
    assert buyer['*']['estoque'] is True
    assert buyer['*']['compras'] is False


def test_normalize_keeps_new_nested_shape_untouched():
    normalized = normalize_framework_payload({
        'module_visibility': {'admin': {'*': {'estoque': True}, '9': {'estoque': False}}},
    })
    admin = normalized['module_visibility']['admin']
    assert admin['*']['estoque'] is True
    assert admin['9']['estoque'] is False


def test_normalize_drops_unit_bucket_keys_that_are_not_star_or_digits():
    normalized = normalize_framework_payload({
        'module_visibility': {'admin': {'*': {'estoque': True}, 'not-a-unit': {'estoque': True}}},
    })
    assert set(normalized['module_visibility']['admin'].keys()) == {'*'}


def test_normalize_folds_legacy_module_unit_scope_into_unit_overrides():
    # Formato antigo: module_unit_scope SEPARADO de module_visibility,
    # {module: [unit_id, ...]}, aplicado igualmente a admin e user. O
    # módulo estava ligado (True) na config base de ambos os perfis.
    normalized = normalize_framework_payload({
        'module_visibility': {
            'admin': {'terceirizados_colaboradores': True},
            'user': {'terceirizados_colaboradores': True},
        },
        'module_unit_scope': {'terceirizados_colaboradores': [1, 2]},
    })
    # module_unit_scope não sobrevive à normalização — o modelo novo é a
    # única fonte de verdade.
    assert 'module_unit_scope' not in normalized
    for role in ('admin', 'user'):
        buckets = normalized['module_visibility'][role]
        # Base vira False (restrição estava ativa) + override True nas
        # unidades antes autorizadas — mesmo comportamento observável do
        # allowlist antigo.
        assert buckets['*']['terceirizados_colaboradores'] is False
        assert buckets['1']['terceirizados_colaboradores'] is True
        assert buckets['2']['terceirizados_colaboradores'] is True


def test_normalize_ignores_legacy_module_unit_scope_when_base_already_false():
    # Módulo nunca foi ligado para o perfil — o escopo antigo só restringia
    # um True, nunca concedia; não há nada para converter em override.
    normalized = normalize_framework_payload({
        'module_unit_scope': {'terceirizados_colaboradores': [1, 2]},
    })
    admin = normalized['module_visibility']['admin']
    assert set(admin.keys()) == {'*'}
    assert admin['*']['terceirizados_colaboradores'] is False


def test_normalize_ignores_legacy_module_unit_scope_with_empty_allowlist():
    normalized = normalize_framework_payload({
        'module_visibility': {'admin': {'terceirizados_colaboradores': True}},
        'module_unit_scope': {'terceirizados_colaboradores': []},
    })
    admin = normalized['module_visibility']['admin']
    assert set(admin.keys()) == {'*'}
    assert admin['*']['terceirizados_colaboradores'] is True


def test_normalize_is_idempotent_on_its_own_output():
    once = normalize_framework_payload({
        'module_visibility': {'admin': {'terceirizados_colaboradores': True}},
        'module_unit_scope': {'terceirizados_colaboradores': [1]},
    })
    twice = normalize_framework_payload(once)
    assert once['module_visibility'] == twice['module_visibility']
    assert 'module_unit_scope' not in twice


# ── resolve_module_visibility: o clamp de permissão técnica ────────────────

def test_resolve_clamps_admin_config_to_technical_permission_ceiling():
    # Config libera "fichas" para o comprador, mas ele não tem fichas:view —
    # o teto técnico vence, o módulo continua invisível.
    framework = normalize_framework_payload({'module_visibility': {'buyer': {'fichas': True}}})
    context = build_context({'company_id': 1, 'id': 5, 'role': 'buyer'})
    resolved = resolve_module_visibility(context, framework, PERMISSIONS['buyer'])
    assert resolved['fichas'] is False


def test_resolve_allows_up_to_the_technical_permission_ceiling():
    # Config libera "estoque" para o comprador, que TEM stock:view — dentro
    # do teto, a liberação vale.
    framework = normalize_framework_payload({'module_visibility': {'buyer': {'estoque': True}}})
    context = build_context({'company_id': 1, 'id': 5, 'role': 'buyer'})
    resolved = resolve_module_visibility(context, framework, PERMISSIONS['buyer'])
    assert resolved['estoque'] is True


def test_resolve_config_can_restrict_below_the_default():
    # Direção oposta: admin pode desligar um módulo que a permissão técnica
    # permitiria — a config restringe, nunca amplia.
    framework = normalize_framework_payload({'module_visibility': {'admin': {'estoque': False}}})
    context = build_context({'company_id': 1, 'id': 5, 'role': 'admin'})
    resolved = resolve_module_visibility(context, framework, PERMISSIONS['admin'])
    assert resolved['estoque'] is False


# ── resolve_module_visibility: override por Unidade (TODO módulo suporta) ──
# A extensão vale para qualquer módulo, não só os dois opt-in de terceiros —
# aqui testada com "estoque" (módulo estrutural comum) de propósito, para
# provar a generalização.

def test_resolve_unit_override_takes_precedence_when_present():
    framework = normalize_framework_payload({
        'module_visibility': {'admin': {'*': {'estoque': True}, '9': {'estoque': False}}},
    })
    context = build_context({'company_id': 1, 'id': 5, 'role': 'admin'}, unit_id=9)
    resolved = resolve_module_visibility(context, framework, PERMISSIONS['admin'])
    assert resolved['estoque'] is False


def test_resolve_falls_back_to_star_bucket_for_unit_without_explicit_override():
    framework = normalize_framework_payload({
        'module_visibility': {'admin': {'*': {'estoque': True}, '9': {'estoque': False}}},
    })
    context = build_context({'company_id': 1, 'id': 5, 'role': 'admin'}, unit_id=10)  # unidade 10, não 9
    resolved = resolve_module_visibility(context, framework, PERMISSIONS['admin'])
    assert resolved['estoque'] is True


def test_resolve_falls_back_to_star_bucket_module_by_module():
    # Override da Unidade 9 só menciona "estoque" — "compras" cai no "*".
    framework = normalize_framework_payload({
        'module_visibility': {'admin': {'*': {'estoque': True, 'compras': True}, '9': {'estoque': False}}},
    })
    context = build_context({'company_id': 1, 'id': 5, 'role': 'admin'}, unit_id=9)
    resolved = resolve_module_visibility(context, framework, PERMISSIONS['admin'])
    assert resolved['estoque'] is False
    assert resolved['compras'] is True


def test_resolve_unit_override_is_ignored_without_unit_id():
    framework = normalize_framework_payload({
        'module_visibility': {'admin': {'*': {'estoque': True}, '9': {'estoque': False}}},
    })
    context = build_context({'company_id': 1, 'id': 5, 'role': 'admin'})  # sem unit_id
    resolved = resolve_module_visibility(context, framework, PERMISSIONS['admin'])
    assert resolved['estoque'] is True


def test_resolve_unit_override_never_applies_to_roles_outside_unit_scoped():
    # general_admin nunca é escopado por unidade (papel de empresa inteira) —
    # mesmo com um bucket "9" configurado, ele não é lido.
    framework = normalize_framework_payload({
        'module_visibility': {'general_admin': {'*': {'estoque': True}, '9': {'estoque': False}}},
    })
    context = build_context({'company_id': 1, 'id': 5, 'role': 'general_admin'}, unit_id=9)
    resolved = resolve_module_visibility(context, framework, PERMISSIONS['general_admin'])
    assert resolved['estoque'] is True


# ── service layer: save/get com o armazenamento (app_meta em memória) ─────

class _FakeConnection:
    def commit(self):
        pass


def _fake_meta_store(monkeypatch):
    store = {}
    monkeypatch.setattr(settings_service, 'get_meta', lambda _conn, key: store.get(key))
    monkeypatch.setattr(settings_service, 'set_meta', lambda _conn, key, value: store.__setitem__(key, value))
    return store


class _FakeUnitsConnection(_FakeConnection):
    """Conexão fake que responde à query de unidades do tenant usada por
    _configuration_scope_unit_ids (validação de pertencimento em
    save_module_visibility quando unit_id é informado)."""

    def __init__(self, unit_ids):
        self._unit_ids = set(unit_ids)

    def execute(self, _sql, _params=()):
        return _FakeUnitsRows([{'id': unit_id} for unit_id in self._unit_ids])


class _FakeUnitsRows:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


def test_save_module_visibility_returns_before_after_diff(monkeypatch):
    _fake_meta_store(monkeypatch)
    conn = _FakeConnection()
    before, after = settings_service.save_module_visibility(conn, 7, 'buyer', {'estoque': True, 'compras': False})
    assert before == {'estoque': False, 'compras': True}
    assert after == {'estoque': True, 'compras': False}


def test_save_module_visibility_rejects_unknown_role(monkeypatch):
    _fake_meta_store(monkeypatch)
    conn = _FakeConnection()
    with pytest.raises(ValueError):
        settings_service.save_module_visibility(conn, 7, 'almoxarife', {'estoque': True})


def test_save_module_visibility_rejects_payload_with_no_recognized_module(monkeypatch):
    _fake_meta_store(monkeypatch)
    conn = _FakeConnection()
    with pytest.raises(ValueError):
        settings_service.save_module_visibility(conn, 7, 'buyer', {'not_a_module': True})


def test_save_module_visibility_ignores_unknown_module_keys_mixed_with_valid_ones(monkeypatch):
    _fake_meta_store(monkeypatch)
    conn = _FakeConnection()
    before, after = settings_service.save_module_visibility(
        conn, 7, 'buyer', {'not_a_module': True, 'estoque': True},
    )
    assert before == {'estoque': False}
    assert after == {'estoque': True}


def test_get_effective_module_visibility_applies_saved_override_and_clamp(monkeypatch):
    _fake_meta_store(monkeypatch)
    conn = _FakeConnection()
    settings_service.save_module_visibility(conn, 7, 'buyer', {'estoque': True, 'fichas': True})
    effective = settings_service.get_effective_module_visibility(
        conn, {'company_id': 7, 'id': 1, 'role': 'buyer'},
    )
    assert effective['estoque'] is True   # dentro do teto técnico
    assert effective['fichas'] is False   # além do teto técnico — clampado


def test_get_effective_module_visibility_falls_back_when_storage_read_fails(monkeypatch):
    def _boom(_conn, _key):
        raise RuntimeError('app_meta indisponível')
    monkeypatch.setattr(settings_service, 'get_meta', _boom)
    conn = _FakeConnection()
    # Não pode derrubar o login/bootstrap por causa de um recurso não-crítico.
    effective = settings_service.get_effective_module_visibility(
        conn, {'company_id': 7, 'id': 1, 'role': 'admin'},
    )
    assert effective['dashboard'] is True


# ── save_module_visibility com unit_id: override por Unidade (qualquer
# módulo, não só os dois opt-in de terceiros) ───────────────────────────────

def test_save_module_visibility_with_unit_id_writes_a_separate_bucket(monkeypatch):
    _fake_meta_store(monkeypatch)
    conn = _FakeUnitsConnection({9, 10})
    settings_service.save_module_visibility(conn, 7, 'admin', {'estoque': True})  # base "*"
    before, after = settings_service.save_module_visibility(conn, 7, 'admin', {'estoque': False}, unit_id=9)
    assert before == {'estoque': True}   # herdava do "*" antes deste save
    assert after == {'estoque': False}
    config = settings_service.get_module_visibility_config(conn, 7)
    assert config['admin']['*']['estoque'] is True
    assert config['admin']['9']['estoque'] is False


def test_save_module_visibility_rejects_unit_id_for_role_not_unit_scoped(monkeypatch):
    _fake_meta_store(monkeypatch)
    conn = _FakeUnitsConnection({9})
    with pytest.raises(ValueError):
        settings_service.save_module_visibility(conn, 7, 'general_admin', {'estoque': True}, unit_id=9)


def test_save_module_visibility_rejects_unit_id_outside_tenant(monkeypatch):
    _fake_meta_store(monkeypatch)
    conn = _FakeUnitsConnection({9, 10})
    with pytest.raises(ValueError):
        settings_service.save_module_visibility(conn, 7, 'admin', {'estoque': True}, unit_id=99)


def test_get_effective_module_visibility_respects_unit_override_for_admin(monkeypatch):
    # unit_id é responsabilidade do chamador (modules.auth.service/routes,
    # via core.repository.actor_operational_unit_id) — não é recalculado
    # dentro de get_effective_module_visibility.
    _fake_meta_store(monkeypatch)
    conn = _FakeUnitsConnection({9, 10})
    settings_service.save_module_visibility(conn, 7, 'admin', {'terceirizados_colaboradores': True})
    settings_service.save_module_visibility(conn, 7, 'admin', {'terceirizados_colaboradores': False}, unit_id=10)
    effective_unit_9 = settings_service.get_effective_module_visibility(
        conn, {'company_id': 7, 'id': 1, 'role': 'admin'}, unit_id=9,
    )
    effective_unit_10 = settings_service.get_effective_module_visibility(
        conn, {'company_id': 7, 'id': 1, 'role': 'admin'}, unit_id=10,
    )
    # Unidade 9 nunca teve override — herda o "*" (True). Unidade 10 tem
    # override explícito (False).
    assert effective_unit_9['terceirizados_colaboradores'] is True
    assert effective_unit_10['terceirizados_colaboradores'] is False


# ── migrate_module_visibility_unit_model: migração explícita persistida ───

class _FakeMigrationConnection:
    """Conexão fake com uma tabela app_meta em memória — usada porque a
    migração faz `SELECT key, value FROM app_meta WHERE key LIKE ...`
    diretamente (não passa por get_meta/set_meta, que só operam uma chave
    por vez)."""

    def __init__(self, rows):
        self._rows = dict(rows)  # {key: value}

    def execute(self, sql, _params=()):
        assert 'app_meta' in sql
        return _FakeMigrationRows([{'key': k, 'value': v} for k, v in self._rows.items()])

    def commit(self):
        pass


class _FakeMigrationRows:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


def test_migrate_module_visibility_unit_model_rewrites_legacy_rows(monkeypatch):
    import json as _json

    legacy_payload = {
        'module_visibility': {
            'admin': {'terceirizados_colaboradores': True},
            'user': {'terceirizados_colaboradores': True},
        },
        'module_unit_scope': {'terceirizados_colaboradores': [1]},
    }
    conn = _FakeMigrationConnection({'configuration_framework:7': _json.dumps(legacy_payload)})
    saved = {}
    monkeypatch.setattr(settings_service, 'set_meta', lambda _conn, key, value: saved.__setitem__(key, value))

    settings_service.migrate_module_visibility_unit_model(conn)

    assert 'configuration_framework:7' in saved
    migrated = _json.loads(saved['configuration_framework:7'])
    assert 'module_unit_scope' not in migrated
    assert migrated['module_visibility']['admin']['*']['terceirizados_colaboradores'] is False
    assert migrated['module_visibility']['admin']['1']['terceirizados_colaboradores'] is True


def test_migrate_module_visibility_unit_model_skips_rows_already_on_new_model(monkeypatch):
    import json as _json

    new_payload = {'module_visibility': {'admin': {'*': {'estoque': True}}}}
    conn = _FakeMigrationConnection({'configuration_framework:7': _json.dumps(new_payload)})
    saved = {}
    monkeypatch.setattr(settings_service, 'set_meta', lambda _conn, key, value: saved.__setitem__(key, value))

    settings_service.migrate_module_visibility_unit_model(conn)

    assert saved == {}, 'linha já no formato novo não deveria ser regravada'


def test_migrate_module_visibility_unit_model_is_idempotent(monkeypatch):
    import json as _json

    legacy_payload = {
        'module_visibility': {'admin': {'terceirizados_colaboradores': True}},
        'module_unit_scope': {'terceirizados_colaboradores': [1]},
    }
    store = {'configuration_framework:7': _json.dumps(legacy_payload)}
    monkeypatch.setattr(settings_service, 'set_meta', lambda _conn, key, value: store.__setitem__(key, value))

    conn = _FakeMigrationConnection(store)
    settings_service.migrate_module_visibility_unit_model(conn)
    first_pass = store['configuration_framework:7']

    conn_again = _FakeMigrationConnection(store)
    settings_service.migrate_module_visibility_unit_model(conn_again)
    assert store['configuration_framework:7'] == first_pass


# ── ensure_module_enabled_for_unit: autoridade no BACKEND ──────────────────
# O menu oculto no Flutter/web legado é só orientação de UI — toda rota de
# escrita de um módulo escopado por Unidade precisa desta checagem
# independente, mesmo que o cliente tente contornar o menu.

def test_ensure_module_enabled_for_unit_raises_when_module_not_configured(monkeypatch):
    _fake_meta_store(monkeypatch)
    conn = _FakeUnitsConnection({9, 10})
    # Módulo nunca foi ligado pelo Administrador Geral para este perfil.
    with pytest.raises(PermissionError):
        settings_service.ensure_module_enabled_for_unit(
            conn, {'company_id': 7, 'id': 1, 'role': 'admin'}, 'terceirizados_colaboradores', 9,
        )


def test_ensure_module_enabled_for_unit_raises_when_unit_override_denies(monkeypatch):
    _fake_meta_store(monkeypatch)
    conn = _FakeUnitsConnection({9, 10})
    settings_service.save_module_visibility(conn, 7, 'admin', {'terceirizados_colaboradores': True})
    settings_service.save_module_visibility(conn, 7, 'admin', {'terceirizados_colaboradores': False}, unit_id=10)
    with pytest.raises(PermissionError):
        settings_service.ensure_module_enabled_for_unit(
            conn, {'company_id': 7, 'id': 1, 'role': 'admin'}, 'terceirizados_colaboradores', 10,
        )


def test_ensure_module_enabled_for_unit_passes_when_authorized(monkeypatch):
    _fake_meta_store(monkeypatch)
    conn = _FakeUnitsConnection({9, 10})
    settings_service.save_module_visibility(conn, 7, 'admin', {'terceirizados_colaboradores': True})
    settings_service.ensure_module_enabled_for_unit(
        conn, {'company_id': 7, 'id': 1, 'role': 'admin'}, 'terceirizados_colaboradores', 9,
    )  # não levanta — sem override específico, herda o "*" (True)


def test_ensure_module_enabled_for_unit_general_admin_not_unit_scoped(monkeypatch):
    # general_admin nunca é escopado por unidade — basta o módulo estar
    # ligado no "*", independente de qualquer bucket de unit_id.
    _fake_meta_store(monkeypatch)
    conn = _FakeUnitsConnection({9, 10})
    settings_service.save_module_visibility(conn, 7, 'general_admin', {'terceirizados_colaboradores': True})
    settings_service.ensure_module_enabled_for_unit(
        conn, {'company_id': 7, 'id': 1, 'role': 'general_admin'}, 'terceirizados_colaboradores', 10,
    )  # não levanta
