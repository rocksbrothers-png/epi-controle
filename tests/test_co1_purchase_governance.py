"""CO-1 — governança de Compras: limite de alçada (D-1, D-2) e segregação (D-17).

Cobre, sobre o esquema SQLite dos testes de PO:

* alçada: só o Administrador Geral configura, na própria empresa; sem valor
  padrão; ausência ≠ zero; zero/negativo/inválido/mais de 2 casas recusados;
  Decimal (sem float); limite exato e imediatamente superior; versão otimista;
  auditoria de criação/alteração/remoção; isolamento por empresa;
* segregação: criador da PR não aprova a PR; criador do PO não aprova o PO;
  criador da(s) PR(s) de origem não aprova o PO (inclusive PO com itens de
  várias PRs); mesma pessoa com várias contas; 1º aprovador no 2º nível;
  Administrador Geral que cria e tenta aprovar; empresa com um só usuário;
  vínculo legado ausente (auditado, não silencioso); rota genérica de status;
* rotas: permissão por perfil, códigos estáveis (403/409), auditoria da
  recusa em transação própria, isolamento do GET de configuração.

A concorrência real (transações independentes) está em
``tests/test_co1_purchase_approval_concurrency.py`` (SQLite) e
``tests_postgres/test_co1_purchase_approval_concurrency_postgres.py``.
"""

import json
from decimal import Decimal
from types import SimpleNamespace

import pytest

from core.permissions import PERM_FINANCE_VIEW, PERM_PURCHASE_LIMITS_MANAGE, PERMISSIONS
from epi_backend.purchase_order_workflow import required_approval_levels
from modules.purchases import routes as purchase_routes
from modules.purchases.approval_limits import (
    get_purchase_limits,
    parse_threshold_input,
    read_threshold,
    set_purchase_limit,
)
from modules.purchases.governance import (
    MSG_SELF_APPROVAL_PO,
    MSG_SELF_APPROVAL_PR,
    PurchaseConflictError,
    PurchaseGovernanceError,
)
from modules.purchases.service import (
    _po_company_approval_threshold,
    apply_purchase_request_item_approval,
    approve_purchase_order,
    create_purchase_order,
    get_company_purchase_config,
    get_purchase_order_by_id,
    review_purchase_order,
    set_company_purchase_config,
    update_purchase_request_status,
)
from test_purchase_orders_service import _basic_items
from test_purchase_orders_service import _conn as _po_conn

GENERAL = {'id': 1, 'company_id': 1, 'role': 'general_admin', 'full_name': 'Admin Geral', 'linked_employee_id': None}
GENERAL_B = {'id': 21, 'company_id': 2, 'role': 'general_admin', 'full_name': 'Admin Geral B', 'linked_employee_id': None}
APPROVER = {'id': 5, 'company_id': 1, 'role': 'approver', 'full_name': 'Aprovador', 'linked_employee_id': 500}
APPROVER_2 = {'id': 6, 'company_id': 1, 'role': 'approver', 'full_name': 'Aprovador 2', 'linked_employee_id': 600}
FINANCE_2 = {'id': 7, 'company_id': 1, 'role': 'general_admin', 'full_name': 'Financeiro', 'linked_employee_id': None}
LOCAL = {'id': 8, 'company_id': 1, 'role': 'admin', 'full_name': 'Admin Local', 'linked_employee_id': 800}
# Mesma pessoa (colaborador 800) com uma segunda conta, de Aprovador.
LOCAL_AS_APPROVER = {'id': 9, 'company_id': 1, 'role': 'approver', 'full_name': 'Admin Local (aprovador)',
                     'linked_employee_id': 800}


def _conn():
    conn = _po_conn()
    conn.executescript("""
        CREATE TABLE users (id INTEGER PRIMARY KEY, company_id INTEGER, role TEXT, full_name TEXT,
                            linked_employee_id INTEGER);
        INSERT INTO users (id, company_id, role, full_name, linked_employee_id) VALUES
            (1, 1, 'general_admin', 'Admin Geral', NULL), (21, 2, 'general_admin', 'Admin Geral B', NULL),
            (5, 1, 'approver', 'Aprovador', 500), (6, 1, 'approver', 'Aprovador 2', 600),
            (7, 1, 'general_admin', 'Financeiro', NULL), (8, 1, 'admin', 'Admin Local', 800),
            (9, 1, 'approver', 'Admin Local (aprovador)', 800);
        ALTER TABLE purchase_request_items ADD COLUMN quantity_requested INTEGER DEFAULT 1;
        ALTER TABLE purchase_request_items ADD COLUMN quantity_approved INTEGER DEFAULT 0;
        ALTER TABLE purchase_request_items ADD COLUMN unit_price REAL DEFAULT 10;
        ALTER TABLE purchase_request_items ADD COLUMN total_price REAL DEFAULT 10;
        ALTER TABLE purchase_request_items ADD COLUMN epi_name TEXT DEFAULT 'Luva';
        ALTER TABLE purchase_request_items ADD COLUMN rejection_reason TEXT DEFAULT '';
        ALTER TABLE purchase_request_items ADD COLUMN rejection_comment TEXT DEFAULT '';
        ALTER TABLE purchase_request_items ADD COLUMN approval_decided_by_user_id INTEGER;
        ALTER TABLE purchase_request_items ADD COLUMN approval_decided_by_name TEXT DEFAULT '';
        ALTER TABLE purchase_request_items ADD COLUMN approval_decided_at TEXT DEFAULT '';
        ALTER TABLE purchase_request_items ADD COLUMN notes TEXT DEFAULT '';
        ALTER TABLE purchase_request_items ADD COLUMN updated_at TEXT DEFAULT '';
        ALTER TABLE epis ADD COLUMN ca TEXT DEFAULT '123';
        -- Carteira dos aprovadores (regra existente, fail-closed): unidade 10.
        CREATE TABLE purchase_role_unit_links (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER,
            employee_id INTEGER, role_type TEXT, unit_id INTEGER, created_by_user_id INTEGER, created_at TEXT);
        INSERT INTO purchase_role_unit_links (company_id, employee_id, role_type, unit_id) VALUES
            (1, 500, 'approver', 10), (1, 600, 'approver', 10), (1, 800, 'approver', 10);
    """)
    conn.commit()
    return conn


def _pr(conn, creator_id, status='pending_approval', company_id=1, unit_id=10):
    pr_id = conn.execute(
        'INSERT INTO purchase_requests (company_id, unit_id, status, created_by_user_id, created_at, updated_at) '
        "VALUES (?, ?, ?, ?, '2026-01-01', '2026-01-01')", (company_id, unit_id, status, creator_id),
    ).lastrowid
    item_id = conn.execute(
        "INSERT INTO purchase_request_items (purchase_request_id, company_id, unit_id, epi_id, status) "
        "VALUES (?, ?, ?, 100, ?)", (pr_id, company_id, unit_id, 'approved' if status == 'approved' else 'open'),
    ).lastrowid
    conn.commit()
    return pr_id, item_id


def _pending_po(conn, creator=GENERAL, purchase_request_id=None):
    items = _basic_items()
    payload = {'unit_id': 10, 'items': items}
    if purchase_request_id:
        payload['purchase_request_id'] = purchase_request_id
        # Regra existente: PO de requisição aprovada aponta o item aprovado dela.
        items[0]['purchase_request_item_id'] = conn.execute(
            'SELECT id FROM purchase_request_items WHERE purchase_request_id = ?', (purchase_request_id,)
        ).fetchone()['id']
    po_id = create_purchase_order(conn, creator, payload, '')['id']
    review_purchase_order(conn, FINANCE_2, get_purchase_order_by_id(conn, po_id), 'review_approved', '', '')
    conn.commit()
    return po_id


def _approve(conn, actor, po_id, decision='approved', decisions=None, comment=''):
    return approve_purchase_order(conn, actor, get_purchase_order_by_id(conn, po_id), decision, comment,
                                  decisions or [], '', '')


def _events(conn, action):
    return conn.execute('SELECT * FROM purchase_events WHERE action = ? ORDER BY id', (action,)).fetchall()


# ══ Alçada: permissão ═════════════════════════════════════════════════════════

def test_somente_o_administrador_geral_tem_a_permissao_de_configurar_alcada():
    assert {role for role, perms in PERMISSIONS.items() if PERM_PURCHASE_LIMITS_MANAGE in perms} == {'general_admin'}


def test_finance_view_nao_concede_configuracao_de_alcada():
    holders = {role for role, perms in PERMISSIONS.items() if PERM_FINANCE_VIEW in perms}
    assert {'approver', 'buyer', 'admin', 'registry_admin', 'master_admin'} <= holders
    for role in holders - {'general_admin'}:
        assert PERM_PURCHASE_LIMITS_MANAGE not in PERMISSIONS[role], role


@pytest.mark.parametrize('role', sorted(set(PERMISSIONS) - {'general_admin'}))
def test_nenhum_outro_perfil_configura_a_alcada(role):
    conn = _conn()
    actor = {'id': 50, 'company_id': 1, 'role': role, 'full_name': role}
    with pytest.raises(PermissionError):
        set_purchase_limit(conn, actor, value='1000.00', expected_version=0)
    assert get_purchase_limits(conn, 1)['configured'] is False


# ══ Alçada: valores ═══════════════════════════════════════════════════════════

def test_sem_configuracao_nao_ha_limite_nem_valor_padrao():
    conn = _conn()
    data = get_purchase_limits(conn, 1)
    assert data == {'po_approval_threshold': None, 'currency': 'BRL', 'configured': False, 'version': 0,
                    'updated_at': None, 'updated_by_name': None}
    assert _po_company_approval_threshold(conn, 1) is None
    assert required_approval_levels('99999999.99', None) == 1


@pytest.mark.parametrize('raw,expected', [
    ('1500', Decimal('1500.00')), ('1500.5', Decimal('1500.50')), ('1500.55', Decimal('1500.55')),
    (1500, Decimal('1500.00')), ('0.01', Decimal('0.01')), ('999999999999.99', Decimal('999999999999.99')),
    (None, None),
])
def test_valores_aceitos(raw, expected):
    assert parse_threshold_input(raw) == expected


@pytest.mark.parametrize('raw', [
    '0', '0.00', 0, '-1', '-0.01', '1.555', 'abc', '', ' ', '1,500.00', '1.500,00', '1e3', 'NaN', 'Infinity',
    '.5', '5.', True, False, 1500.5, 0.1, [], {}, '+10',
])
def test_valores_recusados_zero_negativo_invalido_e_float(raw):
    with pytest.raises(ValueError):
        parse_threshold_input(raw)


def test_valor_acima_do_maximo_e_recusado():
    with pytest.raises(ValueError, match='máximo'):
        parse_threshold_input('1000000000000.00')


def test_limite_exato_exige_dois_niveis_e_um_centavo_abaixo_exige_um():
    assert required_approval_levels(Decimal('1000.00'), Decimal('1000.00')) == 2
    assert required_approval_levels(1000.0, '1000.00') == 2
    assert required_approval_levels('1000.01', '1000.00') == 2
    assert required_approval_levels('999.99', '1000.00') == 1
    # REAL do banco com ruído de ponto flutuante não muda a decisão.
    assert required_approval_levels(0.1 + 0.2, '0.30') == 2


def test_formato_legado_numerico_continua_lido_sem_float():
    assert read_threshold({'po_approval_threshold': 20000.0}) == Decimal('20000.00')
    assert read_threshold({'po_approval_threshold': 0}) is None
    assert read_threshold({'po_approval_threshold': -5}) is None
    assert read_threshold({'po_approval_threshold': 'lixo'}) is None
    assert read_threshold({}) is None


def test_criacao_alteracao_e_remocao_auditadas_com_antes_e_depois():
    conn = _conn()
    created = set_purchase_limit(conn, GENERAL, value='1000', expected_version=0, ip_address='10.0.0.1')
    assert created['po_approval_threshold'] == '1000.00' and created['version'] == 1 and created['changed']
    changed = set_purchase_limit(conn, GENERAL, value='2500.50', expected_version=1)
    assert changed['po_approval_threshold'] == '2500.50' and changed['version'] == 2
    removed = set_purchase_limit(conn, GENERAL, value=None, expected_version=2)
    assert removed['configured'] is False and removed['version'] == 3
    rows = [(r['action'], r['status_from'], r['status_to'], r['actor_user_id'], r['actor_role'])
            for r in conn.execute("SELECT * FROM purchase_events WHERE entity_type = 'company' ORDER BY id")]
    assert rows == [
        ('purchase_limit_created', '', '1000.00', 1, 'general_admin'),
        ('purchase_limit_changed', '1000.00', '2500.50', 1, 'general_admin'),
        ('purchase_limit_removed', '2500.50', '', 1, 'general_admin'),
    ]
    assert _events(conn, 'purchase_limit_created')[0]['ip_address'] == '10.0.0.1'
    stored = json.loads(conn.execute("SELECT value FROM app_meta WHERE key = 'purchase_config_1'").fetchone()['value'])
    assert 'po_approval_threshold' not in stored and stored['po_approval_threshold_version'] == 3


def test_reenvio_do_mesmo_valor_e_idempotente():
    conn = _conn()
    set_purchase_limit(conn, GENERAL, value='1000.00', expected_version=0)
    again = set_purchase_limit(conn, GENERAL, value='1000', expected_version=1)
    assert again['changed'] is False and again['version'] == 1
    assert len(_events(conn, 'purchase_limit_changed')) == 0


def test_versao_obsoleta_e_recusada_sem_sobrescrever():
    conn = _conn()
    set_purchase_limit(conn, GENERAL, value='1000.00', expected_version=0)
    with pytest.raises(PurchaseConflictError) as exc:
        set_purchase_limit(conn, GENERAL, value='5.00', expected_version=0)
    assert exc.value.code == 'PURCHASE_LIMIT_VERSION_CONFLICT' and exc.value.status == 409
    assert exc.value.details['po_approval_threshold'] == '1000.00'
    for missing in (None, '', 'x', True, -1):
        with pytest.raises(ValueError):
            set_purchase_limit(conn, GENERAL, value='5.00', expected_version=missing)


def test_moeda_diferente_de_brl_e_recusada():
    conn = _conn()
    with pytest.raises(ValueError, match='Moeda'):
        set_purchase_limit(conn, GENERAL, value='10', expected_version=0, currency='USD')
    assert set_purchase_limit(conn, GENERAL, value='10', expected_version=0, currency='BRL')['configured']


def test_limite_e_independente_por_empresa_e_a_empresa_vem_do_ator():
    conn = _conn()
    set_purchase_limit(conn, GENERAL, value='1000.00', expected_version=0)
    set_purchase_limit(conn, GENERAL_B, value='77.00', expected_version=0)
    assert get_purchase_limits(conn, 1)['po_approval_threshold'] == '1000.00'
    assert get_purchase_limits(conn, 2)['po_approval_threshold'] == '77.00'
    assert _events(conn, 'purchase_limit_created')[1]['company_id'] == 2


def test_revisao_do_admin_preserva_alcada_e_versao():
    conn = _conn()
    set_purchase_limit(conn, GENERAL, value='1000.00', expected_version=0)
    set_company_purchase_config(conn, GENERAL, 1, True)
    config = get_company_purchase_config(conn, 1)
    assert config['require_admin_review'] is True
    assert config['po_approval_threshold'] == '1000.00' and config['po_approval_threshold_version'] == 1
    assert set_purchase_limit(conn, GENERAL, value='1500.00', expected_version=1)['version'] == 2
    assert get_company_purchase_config(conn, 1)['require_admin_review'] is True


def test_mudanca_de_limite_muda_os_niveis_do_proximo_po():
    conn = _conn()
    po_a = _pending_po(conn)  # total 30.00
    assert _approve(conn, APPROVER, po_a)['status'] == 'approved'
    set_purchase_limit(conn, GENERAL, value='30.00', expected_version=0)
    po_b = _pending_po(conn)
    first = _approve(conn, APPROVER, po_b)
    assert first['status'] == 'pending_approval' and first['pending_next_level'] is True
    set_purchase_limit(conn, GENERAL, value='30.01', expected_version=1)
    po_c = _pending_po(conn)
    assert _approve(conn, APPROVER, po_c)['status'] == 'approved'


# ══ Segregação (D-17) ═════════════════════════════════════════════════════════

def test_criador_da_requisicao_nao_aprova_os_itens_dela():
    conn = _conn()
    pr_id, item_id = _pr(conn, creator_id=APPROVER['id'])
    with pytest.raises(PurchaseGovernanceError) as exc:
        apply_purchase_request_item_approval(conn, APPROVER, pr_id, {'decision': 'approve_all'})
    assert exc.value.code == 'PURCHASE_SELF_APPROVAL_FORBIDDEN' and str(exc.value) == MSG_SELF_APPROVAL_PR
    assert conn.execute('SELECT status FROM purchase_request_items WHERE id = ?', (item_id,)).fetchone()['status'] == 'open'


def test_outro_aprovador_aprova_a_requisicao():
    conn = _conn()
    pr_id, item_id = _pr(conn, creator_id=LOCAL['id'])
    out = apply_purchase_request_item_approval(conn, APPROVER, pr_id, {'decision': 'approve_all'})
    assert out['status'] == 'approved'
    assert conn.execute('SELECT status FROM purchase_request_items WHERE id = ?', (item_id,)).fetchone()['status'] == 'approved'


def test_mesma_pessoa_com_outra_conta_nao_aprova_a_requisicao():
    conn = _conn()
    pr_id, _ = _pr(conn, creator_id=LOCAL['id'])
    with pytest.raises(PurchaseGovernanceError):
        apply_purchase_request_item_approval(conn, LOCAL_AS_APPROVER, pr_id, {'decision': 'approve_all'})


def test_criador_pode_reprovar_a_propria_requisicao():
    conn = _conn()
    from epi_backend.purchase_workflow import PURCHASE_APPROVAL_REJECTION_REASONS
    pr_id, item_id = _pr(conn, creator_id=APPROVER['id'])
    out = apply_purchase_request_item_approval(
        conn, APPROVER, pr_id,
        {'rejected_item_ids': [item_id], 'reason': next(iter(PURCHASE_APPROVAL_REJECTION_REASONS)), 'comment': 'caro'},
    )
    assert out['status'] == 'rejected'


def test_criador_do_po_nao_aprova_o_po():
    conn = _conn()
    po_id = _pending_po(conn, creator=FINANCE_2)
    with pytest.raises(PurchaseGovernanceError) as exc:
        _approve(conn, FINANCE_2, po_id)
    assert exc.value.code == 'PURCHASE_SELF_APPROVAL_FORBIDDEN' and str(exc.value) == MSG_SELF_APPROVAL_PO
    assert get_purchase_order_by_id(conn, po_id)['status'] == 'pending_approval'
    assert conn.execute('SELECT COUNT(*) AS n FROM purchase_approvals').fetchone()['n'] == 0


def test_administrador_geral_que_cria_nao_aprova():
    conn = _conn()
    po_id = _pending_po(conn, creator=GENERAL)
    with pytest.raises(PurchaseGovernanceError):
        _approve(conn, GENERAL, po_id)
    with pytest.raises(PurchaseGovernanceError):
        _approve(conn, GENERAL, po_id, decision='partially_approved',
                 decisions=[{'item_id': 1, 'approved': False, 'rejection_reason': 'x'}])


def test_criador_pode_reprovar_ou_prorrogar_o_proprio_po():
    conn = _conn()
    po_id = _pending_po(conn, creator=FINANCE_2)
    assert _approve(conn, FINANCE_2, po_id, decision='rejected', comment='desisti')['status'] == 'rejected'


def test_criador_da_requisicao_de_origem_nao_aprova_o_po():
    conn = _conn()
    pr_id, _ = _pr(conn, creator_id=APPROVER['id'], status='approved')
    po_id = _pending_po(conn, creator=GENERAL, purchase_request_id=pr_id)
    with pytest.raises(PurchaseGovernanceError):
        _approve(conn, APPROVER, po_id)
    assert _approve(conn, APPROVER_2, po_id)['status'] == 'approved'


def test_po_com_itens_de_varias_requisicoes_verifica_todos_os_criadores():
    conn = _conn()
    pr_a, _ = _pr(conn, creator_id=LOCAL['id'], status='approved')
    pr_b, item_b = _pr(conn, creator_id=APPROVER['id'], status='approved')
    po_id = _pending_po(conn, creator=GENERAL, purchase_request_id=pr_a)
    conn.execute('UPDATE purchase_order_items SET purchase_request_item_id = ? WHERE purchase_order_id = ?', (item_b, po_id))
    conn.commit()
    for blocked in (APPROVER, LOCAL_AS_APPROVER, GENERAL):
        with pytest.raises(PurchaseGovernanceError):
            _approve(conn, blocked, po_id)
    assert _approve(conn, APPROVER_2, po_id)['status'] == 'approved'


def test_primeiro_aprovador_nao_executa_o_segundo_nivel_nem_com_outra_conta():
    conn = _conn()
    set_purchase_limit(conn, GENERAL, value='10.00', expected_version=0)
    po_id = _pending_po(conn, creator=GENERAL)
    assert _approve(conn, LOCAL_AS_APPROVER, po_id)['pending_next_level'] is True
    # Mesma pessoa, outra conta (Admin Local com finance:view): recusado.
    with pytest.raises(PurchaseGovernanceError) as exc:
        _approve(conn, LOCAL, po_id)
    assert exc.value.code == 'PURCHASE_SECOND_LEVEL_SAME_PERSON'
    with pytest.raises(PurchaseGovernanceError):
        _approve(conn, LOCAL_AS_APPROVER, po_id)
    final = _approve(conn, FINANCE_2, po_id)
    assert final['status'] == 'approved'
    assert conn.execute('SELECT COUNT(*) AS n FROM purchase_approvals WHERE purchase_order_id = ?', (po_id,)).fetchone()['n'] == 2


def test_segundo_nivel_ainda_exige_finance_view():
    conn = _conn()
    set_purchase_limit(conn, GENERAL, value='10.00', expected_version=0)
    po_id = _pending_po(conn, creator=GENERAL)
    _approve(conn, APPROVER, po_id)
    gestor = {'id': 30, 'company_id': 1, 'role': 'user', 'full_name': 'Gestor', 'linked_employee_id': None}
    with pytest.raises(PermissionError):
        _approve(conn, gestor, po_id)


def test_empresa_com_um_unico_usuario_fica_pendente():
    """Sem outra pessoa autorizada, não há exceção: o PO segue pendente."""
    conn = _conn()
    po_id = _pending_po(conn, creator=GENERAL)
    with pytest.raises(PurchaseGovernanceError):
        _approve(conn, GENERAL, po_id)
    assert get_purchase_order_by_id(conn, po_id)['status'] == 'pending_approval'


def test_vinculo_legado_ausente_nao_bloqueia_mas_fica_auditado():
    conn = _conn()
    pr_id, _ = _pr(conn, creator_id=None, status='approved')
    po_id = _pending_po(conn, creator=GENERAL, purchase_request_id=pr_id)
    assert _approve(conn, APPROVER, po_id)['status'] == 'approved'
    event = _events(conn, 'segregation_unverifiable')
    assert len(event) == 1 and event[0]['entity_id'] == po_id and event[0]['actor_user_id'] == APPROVER['id']
    # O criador comprovado continua bloqueado mesmo com outro vínculo ausente.
    pr2, _ = _pr(conn, creator_id=None, status='approved')
    po2 = _pending_po(conn, creator=FINANCE_2, purchase_request_id=pr2)
    with pytest.raises(PurchaseGovernanceError):
        _approve(conn, FINANCE_2, po2)


def test_rota_generica_de_status_nao_aprova_requisicao():
    conn = _conn()
    pr_id, _ = _pr(conn, creator_id=LOCAL['id'], status='pending_approval')
    pr = dict(conn.execute('SELECT * FROM purchase_requests WHERE id = ?', (pr_id,)).fetchone())
    for status in ('approved', 'partially_approved'):
        with pytest.raises(PurchaseGovernanceError) as exc:
            update_purchase_request_status(conn, LOCAL, pr, status, '', '', [], '')
        assert exc.value.code == 'PURCHASE_APPROVAL_REQUIRES_WORKFLOW'
    assert conn.execute('SELECT status FROM purchase_requests WHERE id = ?', (pr_id,)).fetchone()['status'] == 'pending_approval'


def test_estado_obsoleto_responde_conflito_sem_gravar():
    conn = _conn()
    po_id = _pending_po(conn)
    stale = get_purchase_order_by_id(conn, po_id)
    _approve(conn, APPROVER, po_id)
    events_before = conn.execute('SELECT COUNT(*) AS n FROM purchase_events').fetchone()['n']
    with pytest.raises(PurchaseConflictError) as exc:
        approve_purchase_order(conn, APPROVER_2, stale, 'approved', '', [], '', '')
    assert exc.value.code == 'PURCHASE_ORDER_STATE_CHANGED' and exc.value.status == 409
    assert exc.value.details['status'] == 'approved'
    assert conn.execute('SELECT COUNT(*) AS n FROM purchase_events').fetchone()['n'] == events_before
    assert conn.execute('SELECT COUNT(*) AS n FROM purchase_approvals').fetchone()['n'] == 1
    with pytest.raises(PurchaseConflictError):
        _approve(conn, APPROVER_2, po_id, decision='rejected', comment='tarde')


def test_aprovacao_apos_rejeicao_e_recusada():
    conn = _conn()
    po_id = _pending_po(conn)
    _approve(conn, APPROVER, po_id, decision='rejected', comment='não')
    with pytest.raises(PurchaseConflictError):
        _approve(conn, APPROVER_2, po_id)
    assert get_purchase_order_by_id(conn, po_id)['status'] == 'rejected'


def test_decisao_invalida_continua_erro_de_validacao():
    conn = _conn()
    po_id = _pending_po(conn)
    with pytest.raises(ValueError, match='Decisão de aprovação inválida'):
        _approve(conn, APPROVER, po_id, decision='talvez')


# ══ Rotas ═════════════════════════════════════════════════════════════════════

class _KeepOpenSqliteConnection:
    """Conexão SQLite compartilhada que sobrevive ao ``closing`` do handler (o nome
    contém "sqlite" para ``_is_sqlite_connection`` escolher o dialeto certo)."""

    def __init__(self, conn):
        self._conn = conn

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def close(self):
        pass


@pytest.fixture()
def http(monkeypatch):
    conn = _conn()
    users = {u['id']: u for u in (GENERAL, GENERAL_B, APPROVER, APPROVER_2, FINANCE_2, LOCAL, LOCAL_AS_APPROVER)}
    users[40] = {'id': 40, 'company_id': None, 'role': 'master_admin', 'full_name': 'Master', 'linked_employee_id': None}
    users[41] = {'id': 41, 'company_id': 1, 'role': 'buyer', 'full_name': 'Comprador', 'linked_employee_id': None}
    users[42] = {'id': 42, 'company_id': 1, 'role': 'user', 'full_name': 'Gestor de EPI', 'linked_employee_id': None}
    users[43] = {'id': 43, 'company_id': 1, 'role': 'registry_admin', 'full_name': 'Registro', 'linked_employee_id': None}
    sent = []

    def authorize(connection, actor_id, permission, company_id=None):
        actor = dict(users[int(actor_id)])
        if permission not in PERMISSIONS[actor['role']]:
            raise PermissionError('Perfil sem permissão para esta ação.')
        return actor

    def authorize_any(connection, actor_id, permissions, company_id=None):
        actor = dict(users[int(actor_id)])
        if not any(p in PERMISSIONS[actor['role']] for p in permissions):
            raise PermissionError('Perfil sem permissão para esta ação.')
        return actor

    def resolve(handler, parsed, payload=None):
        if payload and payload.get('actor_user_id'):
            return int(payload['actor_user_id'])
        from urllib.parse import parse_qs
        return int(parse_qs(parsed.query)['actor_user_id'][0])

    monkeypatch.setattr(purchase_routes, 'get_connection', lambda: _KeepOpenSqliteConnection(conn))
    monkeypatch.setattr(purchase_routes, 'authorize_action', authorize)
    monkeypatch.setattr(purchase_routes, 'authorize_action_any', authorize_any)
    monkeypatch.setattr(purchase_routes, 'resolve_actor_user_id', resolve)
    monkeypatch.setattr(purchase_routes, 'actor_operational_unit_id', lambda *a, **k: None)
    monkeypatch.setattr(purchase_routes, 'send_json', lambda handler, status, body: sent.append((status, body)))

    def call(fn, path, payload=None, match=None):
        from urllib.parse import urlparse
        handler = SimpleNamespace(client_address=('127.0.0.1', 0))
        fn(handler, urlparse(path), payload or {}, match)
        return sent[-1]

    return SimpleNamespace(conn=conn, call=call)


def test_rota_get_alcada_por_perfil(http):
    status, body = http.call(purchase_routes.handle_get_purchase_limits, '/api/purchase-limits?actor_user_id=1')
    assert status == 200 and body['data']['can_manage'] is True and body['data']['company_id'] == 1
    status, body = http.call(purchase_routes.handle_get_purchase_limits, '/api/purchase-limits?actor_user_id=5')
    assert status == 200 and body['data']['can_manage'] is False
    # Gestor de EPI (user): sem finance:view nem purchase_limits:manage.
    with pytest.raises(PermissionError):
        http.call(purchase_routes.handle_get_purchase_limits, '/api/purchase-limits?actor_user_id=42')
    with pytest.raises(ValueError):
        http.call(purchase_routes.handle_get_purchase_limits, '/api/purchase-limits?actor_user_id=40')
    status, body = http.call(purchase_routes.handle_get_purchase_limits, '/api/purchase-limits?actor_user_id=40&company_id=2')
    assert status == 200 and body['data']['company_id'] == 2 and body['data']['can_manage'] is False


@pytest.mark.parametrize('actor_id', [5, 8, 9, 40, 41, 42, 43])
def test_rota_post_alcada_recusa_quem_nao_e_administrador_geral(http, actor_id):
    with pytest.raises(PermissionError):
        http.call(purchase_routes.handle_post_purchase_limits, '/api/purchase-limits',
                  {'actor_user_id': actor_id, 'value': '10', 'expected_version': 0})
    assert get_purchase_limits(http.conn, 1)['configured'] is False


def test_rota_post_alcada_grava_na_empresa_do_ator_e_ignora_company_id(http):
    status, body = http.call(purchase_routes.handle_post_purchase_limits, '/api/purchase-limits',
                             {'actor_user_id': 21, 'value': '55.10', 'expected_version': 0, 'company_id': 1})
    assert status == 200 and body['data']['po_approval_threshold'] == '55.10'
    assert get_purchase_limits(http.conn, 2)['configured'] is True
    assert get_purchase_limits(http.conn, 1)['configured'] is False


def test_rota_post_alcada_conflito_409_auditado(http):
    http.call(purchase_routes.handle_post_purchase_limits, '/api/purchase-limits',
              {'actor_user_id': 1, 'value': '10', 'expected_version': 0})
    status, body = http.call(purchase_routes.handle_post_purchase_limits, '/api/purchase-limits',
                             {'actor_user_id': 1, 'value': '20', 'expected_version': 0})
    assert status == 409 and body['code'] == 'PURCHASE_LIMIT_VERSION_CONFLICT'
    assert body['details']['po_approval_threshold'] == '10.00'
    assert len(_events(http.conn, 'purchase_limit_conflict')) == 1
    assert get_purchase_limits(http.conn, 1)['po_approval_threshold'] == '10.00'


def test_rota_aprovacao_po_autoaprovacao_403_com_codigo_e_auditoria(http):
    po_id = _pending_po(http.conn, creator=FINANCE_2)
    match = SimpleNamespace(group=lambda i: str(po_id))
    status, body = http.call(purchase_routes.handle_post_purchase_order_approve, f'/api/purchase-orders/{po_id}/approve',
                             {'actor_user_id': 7, 'decision': 'approved'}, match)
    assert status == 403 and body['code'] == 'PURCHASE_SELF_APPROVAL_FORBIDDEN' and body['error'] == MSG_SELF_APPROVAL_PO
    denied = _events(http.conn, 'approval_denied')
    assert len(denied) == 1 and denied[0]['actor_user_id'] == 7 and denied[0]['entity_id'] == po_id
    assert 'PURCHASE_SELF_APPROVAL_FORBIDDEN' in denied[0]['comment']
    assert get_purchase_order_by_id(http.conn, po_id)['status'] == 'pending_approval'


def test_rota_aprovacao_po_reenvio_409_sem_duplicar(http):
    po_id = _pending_po(http.conn, creator=GENERAL)
    match = SimpleNamespace(group=lambda i: str(po_id))
    status, _ = http.call(purchase_routes.handle_post_purchase_order_approve, f'/api/purchase-orders/{po_id}/approve',
                          {'actor_user_id': 7, 'decision': 'approved'}, match)
    assert status == 200
    status, body = http.call(purchase_routes.handle_post_purchase_order_approve, f'/api/purchase-orders/{po_id}/approve',
                             {'actor_user_id': 7, 'decision': 'approved'}, match)
    assert status == 409 and body['code'] == 'PURCHASE_ORDER_STATE_CHANGED' and body['details']['status'] == 'approved'
    assert http.conn.execute('SELECT COUNT(*) AS n FROM purchase_approvals').fetchone()['n'] == 1
    assert len(_events(http.conn, 'approval_conflict')) == 1


def test_rota_config_de_compras_nao_le_outra_empresa(http):
    set_purchase_limit(http.conn, GENERAL_B, value='77.00', expected_version=0)
    with pytest.raises(PermissionError):
        http.call(purchase_routes.handle_get_company_purchase_config,
                  '/api/company-purchase-config?actor_user_id=1&company_id=2')
    status, body = http.call(purchase_routes.handle_get_company_purchase_config,
                             '/api/company-purchase-config?actor_user_id=21&company_id=2')
    assert status == 200 and body['config']['po_approval_threshold'] == '77.00'
    status, body = http.call(purchase_routes.handle_get_company_purchase_config,
                             '/api/company-purchase-config?actor_user_id=40&company_id=2')
    assert status == 200


def test_mensagens_de_governanca_estao_nos_5_catalogos():
    import importlib.util
    from pathlib import Path

    from modules.purchases import approval_limits, governance

    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('inv', root / 'scripts/i18n/inventory_backend_errors.py')
    inv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inv)
    cats = {loc: json.loads((root / 'static/i18n' / f'{loc}.json').read_text(encoding='utf-8'))
            for loc in ('pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO')}
    messages = [v for m in (governance, approval_limits) for k, v in vars(m).items() if k.startswith('MSG_')]
    assert len(messages) >= 11
    for message in messages:
        leaf = inv.key_for(message).split('.')[-1]
        assert cats['pt-BR']['apiErrors']['messages'][leaf] == message
        for loc in ('en-GB', 'es-ES', 'fr-FR', 'nb-NO'):
            assert cats[loc]['apiErrors']['messages'][leaf] not in ('', message), (loc, message)
