"""PR22 (issue reportada em produção): descentralização do cadastro de
Empresas Terceirizadas/Prestadoras (aba "Empresas", módulo `terceirizados`)
para Administrador Local/Gestor de EPI, escopada à própria Unidade
operacional — só quando o Administrador Geral autorizar explicitamente via
module_visibility (Configuração > Regras > Visualização), reaproveitando
integralmente o mecanismo já existente (nenhuma autorização nova).

Cobre o que ficou faltando nas PRs 1/10-21 (module_visibility em si): até
aqui, admin/user nunca tinham `employees:create` (o piso técnico histórico
do módulo `terceirizados`) — só `employees:create_simplified`, que sempre
foi suficiente para `terceirizados_colaboradores` (já coberto em
test_outsourced_extension_end_to_end_journey.py). Esta suíte cobre a
extensão do piso técnico do módulo `terceirizados` para aceitar também
`employees:create_simplified` (rule_engine.py), o gate real de módulo por
Unidade nas rotas de outsourced_companies (mesmo padrão de
ensure_module_enabled_for_unit já usado em modules/employees/routes.py) e o
isolamento por Unidade em si (nunca uma empresa "do tenant" nem de outra
Unidade).
"""

import sqlite3

import pytest

import core.repository as repository
from core.permissions import PERMISSIONS
from core.schema import (
    ensure_employee_simplified_registration_columns,
    ensure_legal_entities,
    ensure_outsourced_companies,
    ensure_outsourced_company_unit_links,
    ensure_outsourced_company_archival_lifecycle_columns,
)
from epi_backend.rule_engine import MODULE_REQUIRED_PERMISSIONS
from modules.outsourced_companies.service import (
    create_outsourced_company,
    ensure_actor_outsourced_company_scope,
    fetch_archived_outsourced_companies,
    fetch_outsourced_companies,
    get_outsourced_company_by_id,
    resolve_outsourced_company_unit_id,
    update_outsourced_company,
    validate_employee_outsourced_reference,
)
from modules.settings.service import ensure_module_enabled_for_unit, save_module_visibility


@pytest.fixture(autouse=True)
def _sqlite_detection(monkeypatch):
    import epi_backend.db as db_module
    monkeypatch.setattr(db_module, '_is_sqlite_connection', lambda _conn: True)


def _dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


class _PgStyleConn:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        return self._conn.execute(str(sql).replace('%s', '?'), params)

    def commit(self):
        self._conn.commit()

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = _dict_factory
    conn.executescript(
        """
        CREATE TABLE companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, legal_name TEXT DEFAULT '', cnpj TEXT, logo_type TEXT DEFAULT '',
            user_limit INTEGER NOT NULL DEFAULT 999, license_status TEXT NOT NULL DEFAULT 'active',
            active INTEGER NOT NULL DEFAULT 1, contract_end TEXT, addendum_enabled INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, name TEXT, unit_type TEXT DEFAULT '',
            city TEXT DEFAULT '', notes TEXT DEFAULT ''
        );
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, unit_id INTEGER, name TEXT,
            employee_id_code TEXT DEFAULT '', cpf TEXT DEFAULT '', email TEXT DEFAULT '',
            whatsapp TEXT DEFAULT '', preferred_contact_channel TEXT DEFAULT '',
            sector TEXT DEFAULT '', role_name TEXT DEFAULT '', admission_date TEXT DEFAULT '',
            schedule_type TEXT DEFAULT '', tipo_vinculo TEXT DEFAULT 'CLT', empresa_origem TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active'
        );
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT, password TEXT DEFAULT '', company_id INTEGER, role TEXT, full_name TEXT DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1, linked_employee_id INTEGER
        );
        CREATE TABLE employee_unit_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER, movement_type TEXT, start_date TEXT, end_date TEXT DEFAULT '',
            target_unit_id INTEGER
        );
        CREATE TABLE company_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            actor_user_id INTEGER NOT NULL, actor_name TEXT NOT NULL, action_type TEXT NOT NULL,
            summary TEXT NOT NULL, details_json TEXT NOT NULL DEFAULT '[]', created_at TEXT NOT NULL
        );
        CREATE TABLE app_meta (key TEXT PRIMARY KEY, value TEXT);
        """
    )
    return conn


def _bootstrap(conn):
    ensure_legal_entities(conn)
    ensure_outsourced_companies(conn)
    ensure_outsourced_company_unit_links(conn)
    ensure_outsourced_company_archival_lifecycle_columns(conn)
    ensure_employee_simplified_registration_columns(conn)


def _seed_company(conn, name='ACME'):
    cur = conn.execute('INSERT INTO companies (name, legal_name, cnpj) VALUES (?, ?, ?)', (name, name, ''))
    conn.commit()
    return int(cur.lastrowid)


def _seed_unit(conn, company_id, name='Unidade'):
    cur = conn.execute('INSERT INTO units (company_id, name) VALUES (?, ?)', (company_id, name))
    conn.commit()
    return int(cur.lastrowid)


def _seed_unit_scoped_actor(conn, company_id, unit_id, role='admin'):
    """Administrador Local/Gestor de EPI têm vínculo único com UMA unidade
    operacional, resolvido via linked_employee_id -> employees.unit_id
    (core.repository.actor_operational_unit_id) — precisa de uma linha em
    `employees` representando a própria pessoa, não um colaborador terceirizado."""
    cur = conn.execute(
        'INSERT INTO employees (company_id, unit_id, name) VALUES (?, ?, ?)',
        (company_id, unit_id, 'Responsável da Unidade'),
    )
    conn.commit()
    employee_id = int(cur.lastrowid)
    return {'id': 1, 'role': role, 'company_id': company_id, 'linked_employee_id': employee_id}


def _tenant_wide_actor(company_id, role='general_admin'):
    return {'id': 2, 'role': role, 'company_id': company_id}


# ── Piso técnico do módulo (rule_engine) ────────────────────────────────────

def test_terceirizados_technical_floor_accepts_either_permission():
    required = MODULE_REQUIRED_PERMISSIONS['terceirizados']
    assert required & PERMISSIONS['general_admin']  # employees:create
    assert required & PERMISSIONS['admin']  # employees:create_simplified
    assert required & PERMISSIONS['user']  # employees:create_simplified
    assert not (required & PERMISSIONS['buyer'])  # nenhuma das duas


# ── authorize_action_any ────────────────────────────────────────────────────

def test_authorize_action_any_succeeds_with_either_permission(monkeypatch):
    # require_actor() passa por enforce_company_block_rules (contagem de
    # usuários faturáveis) — fora do escopo deste teste, que é só a lógica
    # de OR entre permissões alternativas em authorize_action_any. Isolado
    # com um require_actor de teste, como os demais testes de rota deste
    # módulo (test_outsourced_pr6_routes.py) isolam authorize_action/
    # authorize_action_any da camada HTTP.
    actors = {
        1: {'id': 1, 'role': 'general_admin', 'company_id': 1},
        2: {'id': 2, 'role': 'admin', 'company_id': 1},
    }
    monkeypatch.setattr(repository, 'require_actor', lambda _conn, uid: actors[int(uid)])
    from core.permissions import PERM_EMPLOYEES_CREATE, PERM_EMPLOYEES_CREATE_SIMPLIFIED
    actions = (PERM_EMPLOYEES_CREATE, PERM_EMPLOYEES_CREATE_SIMPLIFIED)
    general_admin_actor = repository.authorize_action_any(None, 1, actions)
    assert general_admin_actor['role'] == 'general_admin'
    local_admin_actor = repository.authorize_action_any(None, 2, actions)
    assert local_admin_actor['role'] == 'admin'


def test_authorize_action_any_raises_when_no_permission_matches(monkeypatch):
    actor = {'id': 3, 'role': 'buyer', 'company_id': 1}
    monkeypatch.setattr(repository, 'require_actor', lambda _conn, uid: actor)
    from core.permissions import PERM_EMPLOYEES_CREATE, PERM_EMPLOYEES_CREATE_SIMPLIFIED
    with pytest.raises(PermissionError):
        repository.authorize_action_any(None, 3, (PERM_EMPLOYEES_CREATE, PERM_EMPLOYEES_CREATE_SIMPLIFIED))


# ── Gate real de módulo por Unidade (backend, não só menu) ─────────────────

def test_module_gate_blocks_admin_until_general_admin_authorizes_the_unit():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    local_admin = _seed_unit_scoped_actor(conn, cid, unit_a, role='admin')

    # 1) Oculto por padrão em todo tenant — mesmo tendo a permissão técnica
    # (employees:create_simplified), o módulo não foi ligado ainda.
    with pytest.raises(PermissionError):
        ensure_module_enabled_for_unit(conn, local_admin, 'terceirizados', unit_a)

    # 2) Administrador Geral autoriza para o perfil (bucket "*"): passa a valer.
    save_module_visibility(conn, cid, 'admin', {'terceirizados': True})
    ensure_module_enabled_for_unit(conn, local_admin, 'terceirizados', unit_a)

    # 3) Restringindo de novo especificamente para a Unidade A: volta a bloquear.
    save_module_visibility(conn, cid, 'admin', {'terceirizados': False}, unit_id=unit_a)
    with pytest.raises(PermissionError):
        ensure_module_enabled_for_unit(conn, local_admin, 'terceirizados', unit_a)


# ── Escopo por Unidade do cadastro em si ────────────────────────────────────

def test_admin_creates_company_forced_into_own_unit_regardless_of_payload():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    unit_b = _seed_unit(conn, cid, 'Unidade B')
    local_admin = _seed_unit_scoped_actor(conn, cid, unit_a, role='admin')

    # Mesmo mandando unit_id de outra Unidade no payload, o resultado é
    # sempre a própria Unidade operacional do ator — igual a
    # ensure_actor_unit_scope_for_target em modules/employees/service.py.
    unit_id = resolve_outsourced_company_unit_id(conn, local_admin, {'unit_id': unit_b}, cid)
    assert unit_id == unit_a

    entity_id = create_outsourced_company(
        conn, {'legal_name': 'Terceirizada Local'}, cid, actor_user_id=local_admin['id'], unit_id=unit_id,
    )
    entity = get_outsourced_company_by_id(conn, entity_id)
    assert entity['unit_id'] == unit_a


def test_general_admin_creates_tenant_wide_company_by_default():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    general_admin = _tenant_wide_actor(cid)

    unit_id = resolve_outsourced_company_unit_id(conn, general_admin, {}, cid)
    assert unit_id is None
    entity_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada Global'}, cid, unit_id=unit_id)
    entity = get_outsourced_company_by_id(conn, entity_id)
    assert entity['unit_id'] is None


def test_general_admin_can_scope_a_company_to_a_specific_unit():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    general_admin = _tenant_wide_actor(cid)

    unit_id = resolve_outsourced_company_unit_id(conn, general_admin, {'unit_id': unit_a}, cid)
    assert unit_id == unit_a


def test_resolve_unit_id_rejects_unit_from_another_tenant():
    conn = _PgStyleConn(_conn())
    cid_a = _seed_company(conn, 'ACME A')
    cid_b = _seed_company(conn, 'ACME B')
    _bootstrap(conn)
    unit_b = _seed_unit(conn, cid_b, 'Unidade de B')
    general_admin = _tenant_wide_actor(cid_a)
    with pytest.raises(ValueError):
        resolve_outsourced_company_unit_id(conn, general_admin, {'unit_id': unit_b}, cid_a)


# ── Isolamento entre Unidades e contra empresas "do tenant" ────────────────

def test_ensure_actor_scope_blocks_admin_from_tenant_wide_company():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    local_admin = _seed_unit_scoped_actor(conn, cid, unit_a, role='admin')

    tenant_wide_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada Global'}, cid)
    tenant_wide = get_outsourced_company_by_id(conn, tenant_wide_id)
    with pytest.raises(PermissionError):
        ensure_actor_outsourced_company_scope(conn, local_admin, tenant_wide)


def test_ensure_actor_scope_blocks_admin_from_another_units_company():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    unit_b = _seed_unit(conn, cid, 'Unidade B')
    local_admin_a = _seed_unit_scoped_actor(conn, cid, unit_a, role='admin')

    other_unit_company_id = create_outsourced_company(
        conn, {'legal_name': 'Terceirizada B'}, cid, unit_id=unit_b,
    )
    entity = get_outsourced_company_by_id(conn, other_unit_company_id)
    with pytest.raises(PermissionError):
        ensure_actor_outsourced_company_scope(conn, local_admin_a, entity)


def test_ensure_actor_scope_allows_admin_own_units_company():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    local_admin = _seed_unit_scoped_actor(conn, cid, unit_a, role='admin')

    own_company_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada A'}, cid, unit_id=unit_a)
    entity = get_outsourced_company_by_id(conn, own_company_id)
    ensure_actor_outsourced_company_scope(conn, local_admin, entity)  # não levanta


def test_ensure_actor_scope_never_restricts_general_admin():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    general_admin = _tenant_wide_actor(cid)
    tenant_wide_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada Global'}, cid)
    unit_scoped_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada A'}, cid, unit_id=unit_a)
    ensure_actor_outsourced_company_scope(conn, general_admin, get_outsourced_company_by_id(conn, tenant_wide_id))
    ensure_actor_outsourced_company_scope(conn, general_admin, get_outsourced_company_by_id(conn, unit_scoped_id))


def test_fetch_outsourced_companies_admin_sees_only_own_unit():
    """ADR-0002 §12 (compartilhamento por tenant): B e a "Global" não somem
    — aparecem em ``available`` (mascaradas), oferecendo vínculo, em vez de
    ficarem totalmente invisíveis como antes da extensão."""
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    unit_b = _seed_unit(conn, cid, 'Unidade B')
    local_admin_a = _seed_unit_scoped_actor(conn, cid, unit_a, role='admin')

    create_outsourced_company(conn, {'legal_name': 'Terceirizada A'}, cid, unit_id=unit_a)
    create_outsourced_company(conn, {'legal_name': 'Terceirizada B'}, cid, unit_id=unit_b)
    create_outsourced_company(conn, {'legal_name': 'Terceirizada Global'}, cid)  # unit_id=None

    visible = fetch_outsourced_companies(conn, cid, actor=local_admin_a)
    linked_names = {item['legal_name'] for item in visible['linked']}
    available_names = {item['legal_name'] for item in visible['available']}
    assert linked_names == {'Terceirizada A'}
    assert available_names == {'Terceirizada B', 'Terceirizada Global'}
    # Empresa disponível (não vinculada) nunca expõe CNPJ em claro.
    for item in visible['available']:
        assert 'notes' not in item


def test_fetch_outsourced_companies_general_admin_sees_everything():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    unit_b = _seed_unit(conn, cid, 'Unidade B')
    general_admin = _tenant_wide_actor(cid)

    create_outsourced_company(conn, {'legal_name': 'Terceirizada A'}, cid, unit_id=unit_a)
    create_outsourced_company(conn, {'legal_name': 'Terceirizada B'}, cid, unit_id=unit_b)
    create_outsourced_company(conn, {'legal_name': 'Terceirizada Global'}, cid)

    visible = fetch_outsourced_companies(conn, cid, actor=general_admin)
    names = {item['legal_name'] for item in visible['linked']}
    assert names == {'Terceirizada A', 'Terceirizada B', 'Terceirizada Global'}
    assert visible['available'] == []


def test_fetch_archived_outsourced_companies_is_scoped_by_unit_for_admin():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    unit_b = _seed_unit(conn, cid, 'Unidade B')
    local_admin_a = _seed_unit_scoped_actor(conn, cid, unit_a, role='admin')

    from core import archival
    id_a = create_outsourced_company(conn, {'legal_name': 'Terceirizada A'}, cid, unit_id=unit_a)
    id_b = create_outsourced_company(conn, {'legal_name': 'Terceirizada B'}, cid, unit_id=unit_b)
    for entity_id in (id_a, id_b):
        entity = get_outsourced_company_by_id(conn, entity_id)
        archival.archive_record(
            conn, 'outsourced_companies', entity, local_admin_a,
            entity_label='Empresa terceirizada', audit_prefix='outsourced_company',
            record_label=entity['legal_name'], reason='teste',
        )

    archived = fetch_archived_outsourced_companies(conn, local_admin_a)
    names = {item['legal_name'] for item in archived}
    assert names == {'Terceirizada A'}


def test_update_outsourced_company_never_changes_origin_unit():
    """Unidade de origem é imutável após a criação (ADR-0002 §12) —
    `update_outsourced_company` não aceita mais `unit_id` (nem como
    parâmetro, nem lido do payload): mesmo mandando um `unit_id` diferente
    no payload, o valor gravado na criação nunca muda — nem para
    Administrador Geral, que também não tem mais como reatribuir a Unidade
    de origem por aqui."""
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    unit_b = _seed_unit(conn, cid, 'Unidade B')

    entity_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada A'}, cid, unit_id=unit_a)
    update_outsourced_company(
        conn, entity_id, {'legal_name': 'Terceirizada A Renomeada', 'unit_id': unit_b}, cid,
    )
    entity = get_outsourced_company_by_id(conn, entity_id)
    assert entity['unit_id'] == unit_a
    assert entity['legal_name'] == 'Terceirizada A Renomeada'


# ── Vínculo colaborador terceirizado × empresa (unidades compatíveis) ──────

def test_employee_reference_rejects_company_from_a_different_unit():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    unit_b = _seed_unit(conn, cid, 'Unidade B')
    company_in_b = create_outsourced_company(conn, {'legal_name': 'Terceirizada B'}, cid, unit_id=unit_b)

    with pytest.raises(ValueError):
        validate_employee_outsourced_reference(
            conn, {'outsourced_company_id': company_in_b}, cid, unit_id=unit_a,
        )


def test_employee_reference_allows_company_from_the_same_unit():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    company_in_a = create_outsourced_company(conn, {'legal_name': 'Terceirizada A'}, cid, unit_id=unit_a)

    outsourced_company_id, *_rest = validate_employee_outsourced_reference(
        conn, {'outsourced_company_id': company_in_a}, cid, unit_id=unit_a,
    )
    assert outsourced_company_id == company_in_a


def test_employee_reference_allows_tenant_wide_company_from_any_unit():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    tenant_wide_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada Global'}, cid)

    outsourced_company_id, *_rest = validate_employee_outsourced_reference(
        conn, {'outsourced_company_id': tenant_wide_id}, cid, unit_id=unit_a,
    )
    assert outsourced_company_id == tenant_wide_id
