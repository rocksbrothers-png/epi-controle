"""PR2 — testes negativos de autorização para a política de visibilidade por
módulo (Configuração → Regras → Visualização, personalização pelo
Administrador Geral).

Cobre exatamente o que o plano de acesso exige como propriedade de
segurança, além da cobertura funcional já feita em test_module_visibility.py
e test_module_visibility_routes.py:

  - Isolamento entre tenants: general_admin de uma empresa não altera a
    configuração de outra manipulando `company_id`.
  - "Config nunca amplia acesso do backend": prova estrutural (a camada de
    módulo não é referenciada em nenhum ponto de decisão de autorização real)
    e prova de comportamento (abrir o módulo ao máximo não libera a rota de
    dados sem a permissão técnica).
  - Toda mudança é auditada; uma tentativa que falha não deixa auditoria
    "fantasma".
"""

import ast
import io
import json
from pathlib import Path
from urllib.parse import urlparse

import pytest

import modules.settings.routes as routes
import modules.settings.service as settings_service
from core.permissions import PERMISSIONS


class _FakeHandler:
    def __init__(self):
        self.path = '/api/module-visibility'
        self.command = 'POST'
        self.status = None
        self.wfile = io.BytesIO()

    def send_response(self, status):
        self.status = status

    def send_header(self, *_a, **_k):
        pass

    def end_headers(self):
        pass

    def json(self):
        return json.loads(self.wfile.getvalue().decode('utf-8'))


class _FakeConn:
    def commit(self):
        pass

    def close(self):
        pass


def _fake_meta_store(monkeypatch):
    store = {}
    monkeypatch.setattr(settings_service, 'get_meta', lambda _conn, key: store.get(key))
    monkeypatch.setattr(settings_service, 'set_meta', lambda _conn, key, value: store.__setitem__(key, value))
    return store


def _patch_common(monkeypatch, actor):
    monkeypatch.setattr(routes, 'get_connection', _FakeConn)
    monkeypatch.setattr(routes, 'resolve_actor_user_id', lambda *a, **k: actor['id'])
    monkeypatch.setattr(routes, 'authorize_action', lambda *a, **k: actor)


def _parsed():
    return urlparse('/api/module-visibility?actor_user_id=1')


GENERAL_ADMIN_TENANT_A = {'id': 1, 'role': 'general_admin', 'company_id': 7, 'full_name': 'Ana'}


# ── Isolamento entre tenants ─────────────────────────────────────────────────

def test_general_admin_cannot_target_another_companys_config_via_company_id(monkeypatch):
    _fake_meta_store(monkeypatch)
    _patch_common(monkeypatch, GENERAL_ADMIN_TENANT_A)
    handler = _FakeHandler()
    # Tenant A tenta gravar explicitamente no escopo do tenant B (999).
    payload = {'actor_user_id': 1, 'company_id': 999, 'role': 'buyer', 'modules': {'estoque': True}}
    with pytest.raises(PermissionError, match='própria empresa'):
        routes.handle_post_module_visibility(handler, _parsed(), payload, None)


def test_general_admin_config_write_lands_only_on_own_company_scope(monkeypatch):
    store = _fake_meta_store(monkeypatch)
    _patch_common(monkeypatch, GENERAL_ADMIN_TENANT_A)
    monkeypatch.setattr('modules.companies.service.register_company_audit', lambda *a, **k: None)
    handler = _FakeHandler()
    payload = {'actor_user_id': 1, 'role': 'buyer', 'modules': {'estoque': True}}
    routes.handle_post_module_visibility(handler, _parsed(), payload, None)
    assert 'configuration_framework:7' in store
    assert 'configuration_framework:999' not in store
    assert 'configuration_framework:global' not in store


# ── "Config nunca amplia acesso do backend" — prova estrutural ─────────────

def test_module_visibility_is_not_referenced_by_real_authorization_code():
    """Garante, lendo o código-fonte, que `module_visibility`/
    `resolve_module_visibility` nunca entram em `ensure_permission`,
    `authorize_action` ou `core/auth.py` — ou seja, é estruturalmente
    impossível esta camada (só UI: menu/rotas/deep links) autorizar dados.
    Se algum dia alguém acoplar as duas coisas, este teste quebra."""
    root = Path(__file__).resolve().parents[1]
    suspects = [
        root / 'core' / 'auth.py',
        root / 'core' / 'permissions.py',
        root / 'core' / 'repository.py',
    ]
    for path in suspects:
        source = path.read_text(encoding='utf-8')
        assert 'module_visibility' not in source, f'{path} não deveria referenciar module_visibility'
        assert 'resolve_module_visibility' not in source, f'{path} não deveria referenciar resolve_module_visibility'


def test_ensure_permission_and_authorize_action_do_not_import_rule_engine():
    """Confirma via AST que `core/auth.py` e `core/repository.py` (onde
    vivem `ensure_permission`/`authorize_action`) não importam
    `epi_backend.rule_engine` — a autorização real de dados não depende do
    motor de regras que resolve module_visibility."""
    root = Path(__file__).resolve().parents[1]
    for filename in ('auth.py', 'repository.py'):
        path = root / 'core' / filename
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        imported_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.add(alias.name)
        assert 'epi_backend.rule_engine' not in imported_modules, path


# ── "Config nunca amplia acesso do backend" — prova de comportamento ──────

def test_opening_module_to_the_maximum_never_grants_missing_technical_permission(monkeypatch):
    _fake_meta_store(monkeypatch)
    conn = _FakeConn()
    # Abre TODOS os módulos para o comprador, inclusive os que ele
    # tecnicamente não tem permissão nenhuma para ver.
    settings_service.save_module_visibility(
        conn, 7, 'buyer',
        {'estoque': True, 'entregas': True, 'fichas': True, 'administracao': True, 'configuracoes': True},
    )
    effective = settings_service.get_effective_module_visibility(
        conn, {'company_id': 7, 'id': 4, 'role': 'buyer'},
    )
    granted = PERMISSIONS['buyer']
    # fichas/administracao/configuracoes: buyer não tem NENHUMA permissão
    # técnica correspondente — permanecem fechados mesmo com a config no máximo.
    assert effective['fichas'] is False
    assert effective['administracao'] is False
    assert effective['configuracoes'] is False
    # A ausência de permissão técnica é o motivo, não um bug de dados de teste.
    assert not ({'fichas:view'} & granted)
    assert not ({'users:view', 'companies:view', 'legal_entities:view'} & granted)
    assert not ({'settings:view'} & granted)


# ── Auditoria completa, sem entradas fantasma ──────────────────────────────

def test_every_successful_save_is_audited_exactly_once(monkeypatch):
    _fake_meta_store(monkeypatch)
    _patch_common(monkeypatch, GENERAL_ADMIN_TENANT_A)
    audits = []
    monkeypatch.setattr(
        'modules.companies.service.register_company_audit',
        lambda connection, company_id, actor, action_type, summary, details=None, **kwargs:
            audits.append(action_type),
    )
    for role, modules in (
        ('buyer', {'estoque': True}),
        ('approver', {'entregas': True}),
        ('admin', {'configuracoes': True}),
    ):
        routes.handle_post_module_visibility(
            _FakeHandler(), _parsed(), {'actor_user_id': 1, 'role': role, 'modules': modules}, None,
        )
    assert audits == ['visibility_config_updated'] * 3


def test_failed_save_does_not_write_an_audit_entry(monkeypatch):
    _fake_meta_store(monkeypatch)
    _patch_common(monkeypatch, GENERAL_ADMIN_TENANT_A)
    audits = []
    monkeypatch.setattr(
        'modules.companies.service.register_company_audit',
        lambda *a, **k: audits.append(True),
    )
    # Perfil inexistente: save_module_visibility levanta ValueError antes de
    # qualquer commit/gravação — a auditoria não deve ser chamada.
    with pytest.raises(ValueError):
        routes.handle_post_module_visibility(
            _FakeHandler(), _parsed(), {'actor_user_id': 1, 'role': 'almoxarife', 'modules': {'estoque': True}}, None,
        )
    assert audits == []
