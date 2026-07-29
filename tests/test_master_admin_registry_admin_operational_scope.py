"""Escopo operacional de Administrador Master e Administrador de Registro
(docs/PAPEIS_E_ATRIBUICOES.md #1 e #3).

Decisão do responsável do produto (2026-07-29): nenhum dos dois retém
permissão permanente de execução operacional sobre colaboradores, entregas,
estoque ou requisições de compra. O Administrador Master, especialmente,
só deveria acessar essas ações via um mecanismo formal de suporte
(impersonation / acesso temporário auditado) — ainda não implementado;
aqui garantimos que a concessão *permanente* no papel foi removida.

Mesmo antipadrão de fail-open já corrigido para CNPJ e escopo de unidade:
a permissão só é segura se a ausência dela também for testada, não só a
presença.
"""

import pytest

from core.auth import ensure_permission
from core.permissions import (
    PERM_DELIVERIES_CREATE,
    PERM_DELIVERIES_VIEW,
    PERM_EMPLOYEES_CREATE,
    PERM_EMPLOYEES_DELETE,
    PERM_EMPLOYEES_UPDATE,
    PERM_EMPLOYEES_VIEW,
    PERM_PO_RECEIVE,
    PERM_PO_REVIEW,
    PERM_PURCHASE_REQUESTS_CREATE,
    PERM_PURCHASE_REQUESTS_UPDATE,
    PERM_PURCHASE_REQUESTS_VIEW,
    PERM_STOCK_ADJUST,
    PERM_STOCK_VIEW,
    PERMISSIONS,
)


def _actor(role):
    return {'id': 1, 'role': role, 'company_id': 1}


# ═══════════════════════════════════════════════════════════════════════════════
# Tabela — quem cria/atualiza/arquiva colaborador, ajusta estoque, entrega EPI,
# cria requisição de compra (conforme decisão do responsável do produto)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize('role,expected', [
    ('master_admin', False),
    ('general_admin', True),
    ('registry_admin', True),
    ('admin', False),
    ('user', False),
])
def test_employee_create_matrix(role, expected):
    assert (PERM_EMPLOYEES_CREATE in PERMISSIONS[role]) is expected, role


@pytest.mark.parametrize('role,expected', [
    ('master_admin', False),
    ('general_admin', True),
    ('registry_admin', True),
    ('admin', False),
    ('user', False),
])
def test_employee_update_matrix(role, expected):
    assert (PERM_EMPLOYEES_UPDATE in PERMISSIONS[role]) is expected, role


@pytest.mark.parametrize('role,expected', [
    ('master_admin', False),
    ('general_admin', True),
    ('registry_admin', True),
    ('admin', False),
    ('user', False),
])
def test_employee_archive_matrix(role, expected):
    """`employees:delete` gate o arquivamento (soft delete) — nunca exclusão
    física; ver `modules/employees/routes.py:handle_delete_employee`."""
    assert (PERM_EMPLOYEES_DELETE in PERMISSIONS[role]) is expected, role


@pytest.mark.parametrize('role,expected', [
    ('master_admin', False),
    ('general_admin', True),
    ('registry_admin', False),
    ('admin', True),
    ('user', False),
])
def test_purchase_request_create_matrix(role, expected):
    assert (PERM_PURCHASE_REQUESTS_CREATE in PERMISSIONS[role]) is expected, role


@pytest.mark.parametrize('role,expected', [
    ('master_admin', False),
    ('general_admin', True),
    ('registry_admin', False),
])
def test_purchase_request_update_matrix(role, expected):
    assert (PERM_PURCHASE_REQUESTS_UPDATE in PERMISSIONS[role]) is expected, role


@pytest.mark.parametrize('role,expected', [
    ('master_admin', False),
    ('general_admin', True),
    ('registry_admin', False),
    ('admin', True),
    ('user', True),
])
def test_stock_adjust_matrix(role, expected):
    assert (PERM_STOCK_ADJUST in PERMISSIONS[role]) is expected, role


@pytest.mark.parametrize('role,expected', [
    ('master_admin', False),
    ('general_admin', True),
    ('registry_admin', False),
    ('admin', True),
    ('user', True),
])
def test_deliveries_create_matrix(role, expected):
    assert (PERM_DELIVERIES_CREATE in PERMISSIONS[role]) is expected, role


def test_registry_admin_keeps_purchase_pos_review_receive_removed():
    """PURCHASE_ADMIN_PERMISSIONS (PO review/receive) saiu do Registro junto
    com create/update — nenhuma ação operacional de compra permanece."""
    assert PERM_PO_REVIEW not in PERMISSIONS['registry_admin']
    assert PERM_PO_RECEIVE not in PERMISSIONS['registry_admin']


def test_registry_admin_keeps_purchase_view_for_oversight():
    """Consulta/relatório cadastral permanece — só a operação foi removida."""
    assert PERM_PURCHASE_REQUESTS_VIEW in PERMISSIONS['registry_admin']


def test_master_admin_keeps_view_only_permissions():
    """A restrição é só sobre execução — visualização (auditoria/suporte)
    permanece intacta para Administrador Master."""
    assert PERM_EMPLOYEES_VIEW in PERMISSIONS['master_admin']
    assert PERM_DELIVERIES_VIEW in PERMISSIONS['master_admin']
    assert PERM_STOCK_VIEW in PERMISSIONS['master_admin']
    assert PERM_PURCHASE_REQUESTS_VIEW in PERMISSIONS['master_admin']


def test_master_admin_keeps_unrelated_permissions():
    """A remoção é cirúrgica: PO_CREATE/PO_APPROVE (comprador/aprovador),
    empresas, CNPJs, configurações etc. não foram tocados."""
    from core.permissions import PERM_PO_APPROVE, PERM_PO_CREATE, PERM_COMPANIES_CREATE
    assert PERM_PO_CREATE in PERMISSIONS['master_admin']
    assert PERM_PO_APPROVE in PERMISSIONS['master_admin']
    assert PERM_COMPANIES_CREATE in PERMISSIONS['master_admin']


# ═══════════════════════════════════════════════════════════════════════════════
# Enforcement — ensure_permission (não só a tabela estática)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize('permission', [
    PERM_EMPLOYEES_CREATE,
    PERM_EMPLOYEES_UPDATE,
    PERM_EMPLOYEES_DELETE,
    PERM_DELIVERIES_CREATE,
    PERM_STOCK_ADJUST,
    PERM_PURCHASE_REQUESTS_CREATE,
    PERM_PURCHASE_REQUESTS_UPDATE,
])
def test_master_admin_denied_operational_permissions(permission):
    with pytest.raises(PermissionError):
        ensure_permission(_actor('master_admin'), permission)


@pytest.mark.parametrize('permission', [
    PERM_PURCHASE_REQUESTS_CREATE,
    PERM_PURCHASE_REQUESTS_UPDATE,
    PERM_PO_REVIEW,
    PERM_PO_RECEIVE,
    PERM_STOCK_ADJUST,
    PERM_DELIVERIES_CREATE,
])
def test_registry_admin_denied_purchase_and_operational_permissions(permission):
    with pytest.raises(PermissionError):
        ensure_permission(_actor('registry_admin'), permission)


def test_registry_admin_still_allowed_employee_cadastro():
    """O núcleo do papel (cadastro organizacional) não foi afetado."""
    ensure_permission(_actor('registry_admin'), PERM_EMPLOYEES_CREATE)
    ensure_permission(_actor('registry_admin'), PERM_EMPLOYEES_UPDATE)
    ensure_permission(_actor('registry_admin'), PERM_EMPLOYEES_DELETE)


def test_general_admin_unaffected():
    """Só master_admin e registry_admin foram restringidos — general_admin
    mantém o escopo administrativo amplo já documentado (#2)."""
    for permission in (
        PERM_EMPLOYEES_CREATE, PERM_EMPLOYEES_UPDATE, PERM_EMPLOYEES_DELETE,
        PERM_DELIVERIES_CREATE, PERM_STOCK_ADJUST,
        PERM_PURCHASE_REQUESTS_CREATE, PERM_PURCHASE_REQUESTS_UPDATE,
    ):
        ensure_permission(_actor('general_admin'), permission)
