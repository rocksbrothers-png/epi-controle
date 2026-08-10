"""Imutabilidade do vínculo jurídico (CNPJ) do colaborador.

Regra de negócio: o CNPJ representa o vínculo jurídico do contrato de trabalho e
é **imutável após a admissão**. A unidade representa apenas a lotação
operacional e continua alterável pelos fluxos de transferência existentes — e
essa transferência **nunca** altera o CNPJ.

Mudanças de CNPJ ocorrem somente pelo processo administrativo específico
(``transfer_employee_legal_entity``), com justificativa obrigatória, histórico
preservado e auditoria completa.
"""

import sqlite3

import pytest

from core.schema import ensure_company_audit_columns, ensure_legal_entities


@pytest.fixture(autouse=True)
def _sqlite_detection(monkeypatch):
    # create_employee/update_employee sempre passam por core.repository
    # (placeholders "%s", via _PgStyleConn) -- epi_backend.db._is_sqlite_connection
    # detecta o dialeto pelo nome da classe da conexão, e _PgStyleConn não
    # "parece" sqlite. Sem isto, table_exists/table_columns cairiam no branch
    # Postgres contra um banco SQLite de teste e legal_entities_ready()
    # retornaria False silenciosamente. Produção nunca usa este adaptador —
    # só existe em testes (mesmo padrão de test_employee_outsourced_simplified.py).
    import epi_backend.db as db_module
    monkeypatch.setattr(db_module, '_is_sqlite_connection', lambda _conn: True)

from modules.employees.service import (
    fetch_employee_legal_entity_movements,
    transfer_employee_legal_entity,
    update_employee_unit,
)
from modules.legal_entities.service import create_legal_entity, get_default_legal_entity_id

CNPJ_A = '11.222.333/0001-81'
CNPJ_B = '45.723.174/0001-10'

ACTOR = {'id': 1, 'full_name': 'Administrador Geral', 'role': 'general_admin', 'company_id': 1}


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, legal_name TEXT DEFAULT '', cnpj TEXT
        );
        CREATE TABLE units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, name TEXT,
            unit_type TEXT DEFAULT 'base', city TEXT DEFAULT '', notes TEXT DEFAULT ''
        );
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, unit_id INTEGER,
            employee_id_code TEXT, cpf TEXT, name TEXT, email TEXT DEFAULT '',
            whatsapp TEXT DEFAULT '', preferred_contact_channel TEXT DEFAULT 'whatsapp',
            sector TEXT DEFAULT '', role_name TEXT DEFAULT '',
            admission_date TEXT DEFAULT '', schedule_type TEXT DEFAULT '',
            tipo_vinculo TEXT DEFAULT 'CLT', empresa_origem TEXT DEFAULT ''
        );
        CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, company_id INTEGER);
        CREATE TABLE company_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER, actor_user_id INTEGER, actor_name TEXT,
            action_type TEXT, summary TEXT, created_at TEXT
        );
        """
    )
    conn.execute("INSERT INTO companies (name, legal_name, cnpj) VALUES ('ACME', 'ACME SA', ?)", (CNPJ_A,))
    conn.execute("INSERT INTO units (id, company_id, name) VALUES (1, 1, 'Matriz'), (2, 1, 'Base Santos')")
    conn.commit()
    ensure_company_audit_columns(conn)
    ensure_legal_entities(conn)
    conn.execute(
        "INSERT INTO employees (id, company_id, unit_id, employee_id_code, cpf, name, legal_entity_id) "
        "VALUES (5, 1, 1, 'E-001', '12345678901', 'Ana', ?)",
        (get_default_legal_entity_id(conn, 1),),
    )
    conn.commit()
    return conn


class _PgStyleConn:
    """Adaptador de teste: traduz os placeholders ``%s`` (estilo Postgres usados
    em ``core.repository``) para ``?`` do sqlite. Em produção quem faz essa
    normalização é o ``PostgresConnectionWrapper``."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        return self._conn.execute(str(sql).replace('%s', '?'), params)

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _cnpj_of(conn, employee_id=5):
    row = conn.execute('SELECT legal_entity_id FROM employees WHERE id = ?', (employee_id,)).fetchone()
    return row['legal_entity_id']


# ── transferência de unidade não altera o CNPJ ───────────────────────────────

def test_unit_transfer_never_changes_legal_entity():
    conn = _conn()
    before = _cnpj_of(conn)
    update_employee_unit(conn, 5, 2)
    conn.commit()
    row = conn.execute('SELECT unit_id, legal_entity_id FROM employees WHERE id = 5').fetchone()
    assert row['unit_id'] == 2            # lotação operacional mudou
    assert row['legal_entity_id'] == before  # vínculo jurídico intacto


# ── CNPJ imutável na edição comum ────────────────────────────────────────────

def test_ordinary_update_ignores_legal_entity_in_payload():
    """Enviar legal_entity_id no PUT de colaborador não altera o vínculo."""
    from modules.employees.service import update_employee
    conn = _conn()
    matriz = _cnpj_of(conn)
    filial = create_legal_entity(conn, {'cnpj': CNPJ_B, 'legal_name': 'Filial', 'entity_type': 'filial'}, 1)
    payload = {
        'company_id': 1, 'unit_id': 1, 'employee_id_code': 'E-001', 'cpf': '12345678901',
        'name': 'Ana Maria', 'sector': 'Operação', 'role_name': 'Técnica',
        'admission_date': '2026-01-01', 'schedule_type': 'offshore',
        'legal_entity_id': filial,  # tentativa de burlar a imutabilidade
    }
    update_employee(_PgStyleConn(conn), 5, payload, actor=ACTOR)
    row = conn.execute('SELECT name, legal_entity_id FROM employees WHERE id = 5').fetchone()
    assert row['name'] == 'Ana Maria'         # demais campos atualizam
    assert row['legal_entity_id'] == matriz   # CNPJ permanece o da admissão


# ── processo administrativo de transferência ─────────────────────────────────

def test_transfer_requires_justification():
    conn = _conn()
    filial = create_legal_entity(conn, {'cnpj': CNPJ_B, 'legal_name': 'Filial', 'entity_type': 'filial'}, 1)
    with pytest.raises(ValueError, match='Justificativa'):
        transfer_employee_legal_entity(conn, 5, filial, actor=ACTOR, reason='   ')


def test_transfer_changes_cnpj_and_records_history():
    conn = _conn()
    matriz = _cnpj_of(conn)
    filial = create_legal_entity(conn, {'cnpj': CNPJ_B, 'legal_name': 'Filial RJ', 'entity_type': 'filial'}, 1)
    result = transfer_employee_legal_entity(
        conn, 5, filial, actor=ACTOR, reason='Sucessão trabalhista para a filial RJ',
        effective_date='2026-08-01',
    )
    assert _cnpj_of(conn) == filial
    assert result['source_legal_entity_id'] == matriz
    assert result['effective_date'] == '2026-08-01'

    movements = fetch_employee_legal_entity_movements(conn, 5)
    assert len(movements) == 1
    assert movements[0]['source_legal_entity_id'] == matriz
    assert movements[0]['target_legal_entity_id'] == filial
    assert movements[0]['reason'] == 'Sucessão trabalhista para a filial RJ'
    assert movements[0]['target_cnpj'] == CNPJ_B


def test_transfer_writes_full_audit_trail():
    conn = _conn()
    filial = create_legal_entity(conn, {'cnpj': CNPJ_B, 'legal_name': 'Filial RJ', 'entity_type': 'filial'}, 1)
    transfer_employee_legal_entity(conn, 5, filial, actor=ACTOR, reason='Reorganização societária')
    row = conn.execute(
        "SELECT action_type, summary, legal_entity_id FROM company_audit_logs "
        "WHERE action_type = 'employee_legal_entity_transfer'"
    ).fetchone()
    assert row is not None
    assert row['legal_entity_id'] == filial
    assert 'Ana' in row['summary']


def test_transfer_rejects_same_cnpj():
    conn = _conn()
    matriz = _cnpj_of(conn)
    with pytest.raises(ValueError, match='já pertence'):
        transfer_employee_legal_entity(conn, 5, matriz, actor=ACTOR, reason='Sem efeito')


def test_transfer_rejects_inactive_target():
    conn = _conn()
    filial = create_legal_entity(
        conn, {'cnpj': CNPJ_B, 'legal_name': 'Filial', 'entity_type': 'filial', 'active': 0}, 1
    )
    with pytest.raises(ValueError, match='inativo'):
        transfer_employee_legal_entity(conn, 5, filial, actor=ACTOR, reason='Tentativa')


def test_transfer_rejects_cnpj_from_other_company():
    conn = _conn()
    conn.execute("INSERT INTO companies (name, legal_name, cnpj) VALUES ('OUTRA', 'OUTRA SA', ?)", (CNPJ_B,))
    conn.commit()
    ensure_legal_entities(conn)
    other = get_default_legal_entity_id(conn, 2)
    with pytest.raises(ValueError, match='não pertence'):
        transfer_employee_legal_entity(conn, 5, other, actor=ACTOR, reason='Tentativa')


def test_history_preserves_successive_transfers():
    """O histórico jurídico é cumulativo — nada é sobrescrito."""
    conn = _conn()
    filial = create_legal_entity(conn, {'cnpj': CNPJ_B, 'legal_name': 'Filial RJ', 'entity_type': 'filial'}, 1)
    matriz = _cnpj_of(conn)
    transfer_employee_legal_entity(conn, 5, filial, actor=ACTOR, reason='Ida para a filial')
    transfer_employee_legal_entity(conn, 5, matriz, actor=ACTOR, reason='Retorno para a matriz')
    movements = fetch_employee_legal_entity_movements(conn, 5)
    assert len(movements) == 2
    assert {m['target_legal_entity_id'] for m in movements} == {matriz, filial}


def test_history_empty_without_transfers():
    conn = _conn()
    assert fetch_employee_legal_entity_movements(conn, 5) == []


def test_transfer_permission_is_restricted_to_structural_admins():
    from core.permissions import PERMISSIONS
    perm = 'employees:legal_entity_transfer'
    for role in ('master_admin', 'general_admin', 'registry_admin'):
        assert perm in PERMISSIONS[role], role
    for role in ('admin', 'user', 'buyer', 'approver'):
        assert perm not in PERMISSIONS[role], role


# ── Multi-CNPJ do tenant não se aplica a terceirizado/prestador, mesmo via
# create_employee/update_employee (ADR-0002 §13.7/§13.21) ──────────────────
#
# O fix original (PR A) só tocava create_employee_outsourced_simplified.
# Revisão automatizada encontrou que create_employee/update_employee (o
# endpoint GERAL de colaborador) também aceitam tipo_vinculo != 'CLT' e
# também chamavam resolve_employee_legal_entity_id incondicionalmente --
# mesma reprodução do alerta de produção, só que por um caminho diferente,
# e update_employee podia inclusive REPOPULAR legal_entity_id numa linha
# que a migração de limpeza tinha acabado de zerar.

def _base_payload(**overrides):
    payload = {
        'company_id': 1, 'unit_id': 1, 'employee_id_code': 'E-900', 'cpf': '98765432100',
        'name': 'Carlos Terceirizado', 'sector': 'Operação', 'role_name': 'Auxiliar',
        'admission_date': '2026-01-01', 'schedule_type': 'diurno',
    }
    payload.update(overrides)
    return payload


def test_create_employee_skips_legal_entity_resolution_for_non_clt():
    from modules.employees.service import create_employee
    conn = _PgStyleConn(_conn())
    create_legal_entity(conn, {'cnpj': CNPJ_B, 'legal_name': 'Filial', 'entity_type': 'filial'}, 1)
    # 2 CNPJs ativos -- exatamente o cenário que disparava o alerta em
    # produção para o fluxo simplificado; aqui é o endpoint geral.
    employee_id = create_employee(
        conn, _base_payload(tipo_vinculo='Terceirizado', empresa_origem='Fornecedora X'), actor=ACTOR,
    )
    row = conn.execute('SELECT legal_entity_id FROM employees WHERE id = ?', (employee_id,)).fetchone()
    assert not row['legal_entity_id']


def test_create_employee_still_requires_legal_entity_for_clt_with_multiple_cnpjs():
    """Não regressão: colaborador CLT continua exigindo escolha explícita de
    CNPJ quando o tenant tem mais de um ativo -- só o terceirizado é isento.

    A fixture já cria a matriz (CNPJ_A, a partir de companies.cnpj) ao
    montar o employee id=5 -- basta criar mais uma (CNPJ_B) para ter 2 ativos.
    """
    from modules.employees.service import create_employee
    conn = _PgStyleConn(_conn())
    create_legal_entity(conn, {'cnpj': CNPJ_B, 'legal_name': 'Filial', 'entity_type': 'filial'}, 1)
    with pytest.raises(ValueError, match='CNPJ'):
        create_employee(conn, _base_payload(tipo_vinculo='CLT'), actor=ACTOR)


def test_update_employee_does_not_repopulate_legal_entity_for_non_clt():
    """Colaborador terceirizado sem legal_entity_id (já limpo pela migração,
    ou nunca teve) não pode ter o campo repopulado por uma edição comum via
    update_employee -- mesmo com múltiplos CNPJs ativos no tenant."""
    from modules.employees.service import create_employee, update_employee
    conn = _PgStyleConn(_conn())
    employee_id = create_employee(
        conn, _base_payload(tipo_vinculo='Terceirizado', empresa_origem='Fornecedora X'), actor=ACTOR,
    )
    create_legal_entity(conn, {'cnpj': CNPJ_B, 'legal_name': 'Filial', 'entity_type': 'filial'}, 1)
    update_employee(
        conn, employee_id,
        _base_payload(tipo_vinculo='Terceirizado', empresa_origem='Fornecedora X', name='Carlos Editado'),
        actor=ACTOR,
    )
    row = conn.execute('SELECT name, legal_entity_id FROM employees WHERE id = ?', (employee_id,)).fetchone()
    assert row['name'] == 'Carlos Editado'
    assert not row['legal_entity_id']
