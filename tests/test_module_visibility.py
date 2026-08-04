"""Política de acesso: visibilidade estrutural por módulo (menu/rotas/deep
links), personalizável pelo Administrador Geral em "Configuração → Regras →
Visualização" (mesmo armazenamento do framework, sem tabela nova).

Cobre a combinação `config (padrão + override do tenant) AND permissão
técnica` em epi_backend/rule_engine.py e modules/settings/service.py — a
regra que garante que a configuração administrativa nunca amplia o que a
permissão técnica do perfil já não autoriza.
"""

import modules.settings.service as settings_service
from core.permissions import PERMISSIONS
from epi_backend.rule_engine import (
    MODULE_KEYS,
    MODULE_REQUIRED_PERMISSIONS,
    _UNIT_SCOPABLE_MODULES,
    build_context,
    default_framework_payload,
    normalize_framework_payload,
    resolve_module_visibility,
)


# ── rule_engine: regra padrão do sistema ───────────────────────────────────

def test_default_module_visibility_covers_all_canonical_roles():
    visibility = default_framework_payload()['module_visibility']
    assert set(visibility.keys()) == set(PERMISSIONS.keys())
    for role, modules in visibility.items():
        assert set(modules.keys()) == set(MODULE_KEYS), role


def test_buyer_and_approver_are_hidden_from_estoque_entregas_fichas_by_default():
    # Restrição explícita do plano de acesso: Comprador/Aprovador continuam,
    # por padrão, sem acesso estrutural a Estoque/Entregas/Fichas de EPI —
    # mesmo tendo stock:view/deliveries:view como apoio à decisão de compra.
    visibility = default_framework_payload()['module_visibility']
    for role in ('buyer', 'approver'):
        assert visibility[role]['estoque'] is False
        assert visibility[role]['entregas'] is False
        assert visibility[role]['fichas'] is False


def test_default_visibility_matches_technical_permission_floor():
    # Não-invasivo por padrão: quando a permissão técnica falta, o módulo já
    # nasce invisível, sem precisar de nenhuma restrição estrutural extra.
    visibility = default_framework_payload()['module_visibility']
    for role, granted in PERMISSIONS.items():
        for module, required in MODULE_REQUIRED_PERMISSIONS.items():
            if not (required & granted):
                assert visibility[role][module] is False, (role, module)


def test_master_and_general_admin_see_every_module_by_default():
    # "terceirizados" (ADR-014) e "terceirizados_colaboradores" (ADR-0002
    # §10) são opt-in: ocultos por padrão até para quem tem o piso técnico,
    # porque a subpasta só deve aparecer quando o Administrador Geral a liga
    # explicitamente por tenant.
    visibility = default_framework_payload()['module_visibility']
    for role in ('master_admin', 'general_admin'):
        modules = dict(visibility[role])
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
        assert visibility[role]['terceirizados'] is False, role


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
    buyer = normalized['module_visibility']['buyer']
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
    assert 'not_a_module' not in normalized['module_visibility']['buyer']
    assert normalized['module_visibility']['buyer']['estoque'] is True


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


# ── service layer: save/get com o armazenamento (app_meta em memória) ─────

class _FakeConnection:
    def commit(self):
        pass


def _fake_meta_store(monkeypatch):
    store = {}
    monkeypatch.setattr(settings_service, 'get_meta', lambda _conn, key: store.get(key))
    monkeypatch.setattr(settings_service, 'set_meta', lambda _conn, key, value: store.__setitem__(key, value))
    return store


def test_save_module_visibility_returns_before_after_diff(monkeypatch):
    _fake_meta_store(monkeypatch)
    conn = _FakeConnection()
    before, after = settings_service.save_module_visibility(conn, 7, 'buyer', {'estoque': True, 'compras': False})
    assert before == {'estoque': False, 'compras': True}
    assert after == {'estoque': True, 'compras': False}


def test_save_module_visibility_rejects_unknown_role(monkeypatch):
    _fake_meta_store(monkeypatch)
    conn = _FakeConnection()
    try:
        settings_service.save_module_visibility(conn, 7, 'almoxarife', {'estoque': True})
        assert False, 'deveria ter levantado ValueError'
    except ValueError:
        pass


def test_save_module_visibility_rejects_payload_with_no_recognized_module(monkeypatch):
    _fake_meta_store(monkeypatch)
    conn = _FakeConnection()
    try:
        settings_service.save_module_visibility(conn, 7, 'buyer', {'not_a_module': True})
        assert False, 'deveria ter levantado ValueError'
    except ValueError:
        pass


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


# ── module_unit_scope: escopo por Unidade (ADR-0002 §10.3) ────────────────
# Extensão do MESMO framework/module_visibility — não é mecanismo novo.
# _UNIT_SCOPABLE_MODULES restringe onde a checagem se aplica; papéis fora
# de admin/user (general_admin/registry_admin/master_admin) nunca são
# escopados por unidade, em nenhum outro fluxo do sistema.

def test_module_unit_scope_defaults_to_empty():
    assert default_framework_payload()['module_unit_scope'] == {}


def test_normalize_module_unit_scope_keeps_only_scopable_modules():
    normalized = normalize_framework_payload({
        'module_unit_scope': {
            'terceirizados_colaboradores': [2, 1, 2],
            'estoque': [3],  # não escopável por unidade — descartado
        },
    })
    assert normalized['module_unit_scope'] == {'terceirizados_colaboradores': [1, 2]}


def test_normalize_module_unit_scope_ignores_non_list_value():
    normalized = normalize_framework_payload({
        'module_unit_scope': {'terceirizados_colaboradores': 'not-a-list'},
    })
    assert normalized['module_unit_scope'] == {}


def test_resolve_module_visibility_unit_scope_blocks_admin_outside_authorized_units():
    framework = normalize_framework_payload({
        'module_visibility': {'admin': {'terceirizados_colaboradores': True}},
        'module_unit_scope': {'terceirizados_colaboradores': [1, 2]},
    })
    context = build_context({'company_id': 1, 'id': 5, 'role': 'admin'}, unit_id=9)
    resolved = resolve_module_visibility(context, framework, PERMISSIONS['admin'])
    assert resolved['terceirizados_colaboradores'] is False


def test_resolve_module_visibility_unit_scope_allows_admin_inside_authorized_units():
    framework = normalize_framework_payload({
        'module_visibility': {'admin': {'terceirizados_colaboradores': True}},
        'module_unit_scope': {'terceirizados_colaboradores': [1, 2]},
    })
    context = build_context({'company_id': 1, 'id': 5, 'role': 'admin'}, unit_id=2)
    resolved = resolve_module_visibility(context, framework, PERMISSIONS['admin'])
    assert resolved['terceirizados_colaboradores'] is True


def test_resolve_module_visibility_unit_scope_empty_list_means_unrestricted():
    framework = normalize_framework_payload({
        'module_visibility': {'admin': {'terceirizados_colaboradores': True}},
    })
    context = build_context({'company_id': 1, 'id': 5, 'role': 'admin'})  # sem unit_id
    resolved = resolve_module_visibility(context, framework, PERMISSIONS['admin'])
    assert resolved['terceirizados_colaboradores'] is True


def test_resolve_module_visibility_unit_scope_does_not_apply_to_general_admin():
    # general_admin nunca é escopado por unidade (papel de empresa inteira).
    framework = normalize_framework_payload({
        'module_visibility': {'general_admin': {'terceirizados_colaboradores': True}},
        'module_unit_scope': {'terceirizados_colaboradores': [1, 2]},
    })
    context = build_context({'company_id': 1, 'id': 5, 'role': 'general_admin'})
    resolved = resolve_module_visibility(context, framework, PERMISSIONS['general_admin'])
    assert resolved['terceirizados_colaboradores'] is True


class _FakeUnitsConnection(_FakeConnection):
    """Conexão fake que responde à query de unidades do tenant usada por
    _configuration_scope_unit_ids (validação de pertencimento em
    save_module_unit_scope)."""

    def __init__(self, unit_ids):
        self._unit_ids = set(unit_ids)

    def execute(self, _sql, _params=()):
        return _FakeUnitsRows([{'id': unit_id} for unit_id in self._unit_ids])


class _FakeUnitsRows:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


def test_save_module_unit_scope_returns_before_after_diff(monkeypatch):
    _fake_meta_store(monkeypatch)
    conn = _FakeUnitsConnection({1, 2, 3})
    before, after = settings_service.save_module_unit_scope(
        conn, 7, 'terceirizados_colaboradores', [2, 3, 3],
    )
    assert before == []
    assert after == [2, 3]


def test_save_module_unit_scope_rejects_non_scopable_module(monkeypatch):
    _fake_meta_store(monkeypatch)
    conn = _FakeUnitsConnection({1, 2})
    try:
        settings_service.save_module_unit_scope(conn, 7, 'estoque', [1])
        assert False, 'deveria ter levantado ValueError'
    except ValueError:
        pass


def test_save_module_unit_scope_rejects_non_list_payload(monkeypatch):
    _fake_meta_store(monkeypatch)
    conn = _FakeUnitsConnection({1, 2})
    try:
        settings_service.save_module_unit_scope(conn, 7, 'terceirizados_colaboradores', 'not-a-list')
        assert False, 'deveria ter levantado ValueError'
    except ValueError:
        pass


def test_save_module_unit_scope_filters_out_units_outside_tenant(monkeypatch):
    _fake_meta_store(monkeypatch)
    conn = _FakeUnitsConnection({1, 2})
    # 99 não pertence ao tenant (company_id=7) — descartado silenciosamente.
    before, after = settings_service.save_module_unit_scope(
        conn, 7, 'terceirizados_colaboradores', [1, 99],
    )
    assert before == []
    assert after == [1]


def test_get_module_unit_scope_config_reflects_saved_scope(monkeypatch):
    _fake_meta_store(monkeypatch)
    conn = _FakeUnitsConnection({1, 2, 3})
    settings_service.save_module_unit_scope(conn, 7, 'terceirizados_colaboradores', [1, 2])
    config = settings_service.get_module_unit_scope_config(conn, 7)
    assert config == {'terceirizados_colaboradores': [1, 2]}


def test_get_effective_module_visibility_respects_unit_scope_for_admin(monkeypatch):
    # unit_id é responsabilidade do chamador (modules.auth.service/routes,
    # via modules.employees.service.actor_operational_unit_id) — não é
    # recalculado dentro de get_effective_module_visibility, para não
    # importar modules.employees.service a partir de modules.settings.service
    # (evita ciclo: settings -> employees -> outsourced_companies -> settings).
    _fake_meta_store(monkeypatch)
    conn = _FakeUnitsConnection({9, 10})
    settings_service.save_module_visibility(conn, 7, 'admin', {'terceirizados_colaboradores': True})
    settings_service.save_module_unit_scope(conn, 7, 'terceirizados_colaboradores', [9])
    effective = settings_service.get_effective_module_visibility(
        conn, {'company_id': 7, 'id': 1, 'role': 'admin'}, unit_id=10,
    )
    # Administrador Local está na unidade 10, mas só a 9 foi autorizada.
    assert effective['terceirizados_colaboradores'] is False
