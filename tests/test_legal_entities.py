"""Arquitetura Multi-CNPJ / Joint Venture (LegalEntity).

Cobre:
  - ensure_legal_entities: criação da tabela, colunas de vínculo e backfill
    idempotente da matriz padrão por empresa (com revínculo de colaboradores
    e unidades órfãos);
  - service: validação de CNPJ (inválido/duplicado), tipos/UF, hierarquia
    parent_entity, escopo por empresa, resolução do CNPJ do colaborador;
  - routes: list/get/post/put escopados e o cadastro em lote (batch);
  - retrocompatibilidade: fetch/get de colaborador seguem funcionando quando o
    schema Multi-CNPJ ainda não foi provisionado (schema parcial).
"""

import io
import json
import sqlite3
from urllib.parse import urlparse

import pytest

import modules.legal_entities.routes as routes
from core.schema import ensure_legal_entities
from modules.legal_entities.service import (
    create_legal_entity,
    ensure_default_legal_entity,
    fetch_legal_entities,
    get_default_legal_entity_id,
    legal_entities_ready,
    resolve_employee_legal_entity_id,
    validate_legal_entity_payload,
)

# CNPJs válidos (dígitos verificadores corretos) para os testes.
CNPJ_A = '11.222.333/0001-81'
CNPJ_B = '45.723.174/0001-10'
CNPJ_C = '19.131.243/0001-97'


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
            company_id INTEGER NOT NULL, name TEXT
        );
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, unit_id INTEGER, name TEXT
        );
        """
    )
    return conn


def _seed_company(conn, name, legal_name, cnpj):
    cur = conn.execute(
        'INSERT INTO companies (name, legal_name, cnpj) VALUES (?, ?, ?)',
        (name, legal_name, cnpj),
    )
    return int(cur.lastrowid)


# ── migração / backfill ───────────────────────────────────────────────────────

def test_ensure_legal_entities_creates_default_and_backfills():
    conn = _conn()
    cid = _seed_company(conn, 'LIVA MOBILE', 'LIVA MOBILE LTDA', CNPJ_A)
    conn.execute('INSERT INTO units (company_id, name) VALUES (?, ?)', (cid, 'Matriz'))
    conn.execute('INSERT INTO employees (company_id, unit_id, name) VALUES (?, ?, ?)', (cid, 1, 'Ana'))
    conn.commit()

    ensure_legal_entities(conn)

    entity_id = get_default_legal_entity_id(conn, cid)
    assert entity_id is not None
    entity = conn.execute('SELECT * FROM legal_entities WHERE id = ?', (entity_id,)).fetchone()
    assert entity['cnpj'] == CNPJ_A
    assert entity['legal_name'] == 'LIVA MOBILE LTDA'
    assert entity['entity_type'] == 'matriz'
    # backfill de colaboradores e unidades órfãos
    emp = conn.execute('SELECT legal_entity_id FROM employees WHERE name = ?', ('Ana',)).fetchone()
    assert emp['legal_entity_id'] == entity_id
    unit = conn.execute('SELECT legal_entity_id FROM units WHERE name = ?', ('Matriz',)).fetchone()
    assert unit['legal_entity_id'] == entity_id
    # nova config na tenant
    company = conn.execute('SELECT org_structure_type, stock_control_scope FROM companies WHERE id = ?', (cid,)).fetchone()
    assert company['org_structure_type'] == 'single_cnpj'
    assert company['stock_control_scope'] == 'company'


def test_ensure_legal_entities_backfills_without_optional_company_columns():
    """Instalação antiga sem ``companies.legal_name``/``cnpj`` ainda provisiona.

    O backfill não pode abortar o Multi-CNPJ inteiro por causa de uma coluna
    opcional ausente: cai para vazio e usa o nome da empresa como razão social.
    """
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE companies (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, name TEXT);
        CREATE TABLE employees (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, unit_id INTEGER, name TEXT);
        INSERT INTO companies (id, name) VALUES (1, 'ACME');
        INSERT INTO employees (company_id, unit_id, name) VALUES (1, 1, 'Ana');
        """
    )
    conn.commit()

    ensure_legal_entities(conn)

    entity_id = get_default_legal_entity_id(conn, 1)
    entity = conn.execute('SELECT * FROM legal_entities WHERE id = ?', (entity_id,)).fetchone()
    assert entity['cnpj'] == ''
    assert entity['legal_name'] == 'ACME'
    emp = conn.execute('SELECT legal_entity_id FROM employees WHERE name = ?', ('Ana',)).fetchone()
    assert emp['legal_entity_id'] == entity_id


def test_ensure_legal_entities_is_idempotent():
    conn = _conn()
    cid = _seed_company(conn, 'ACME', 'ACME SA', CNPJ_A)
    conn.commit()
    ensure_legal_entities(conn)
    ensure_legal_entities(conn)  # segunda execução não deve duplicar
    count = conn.execute('SELECT COUNT(*) AS n FROM legal_entities WHERE company_id = ?', (cid,)).fetchone()['n']
    assert count == 1


# ── service: validação ────────────────────────────────────────────────────────

def test_validate_rejects_invalid_cnpj():
    conn = _conn()
    cid = _seed_company(conn, 'ACME', 'ACME SA', CNPJ_A)
    conn.commit()
    ensure_legal_entities(conn)
    with pytest.raises(ValueError):
        validate_legal_entity_payload(conn, {'cnpj': '00.000.000/0000-00', 'legal_name': 'X'}, cid)


def test_validate_rejects_duplicate_cnpj_in_company():
    conn = _conn()
    cid = _seed_company(conn, 'ACME', 'ACME SA', CNPJ_A)
    conn.commit()
    ensure_legal_entities(conn)  # cria matriz com CNPJ_A
    with pytest.raises(ValueError):
        validate_legal_entity_payload(conn, {'cnpj': CNPJ_A, 'legal_name': 'Dup'}, cid)


def test_validate_rejects_invalid_uf():
    conn = _conn()
    cid = _seed_company(conn, 'ACME', 'ACME SA', CNPJ_A)
    conn.commit()
    ensure_legal_entities(conn)
    with pytest.raises(ValueError):
        validate_legal_entity_payload(conn, {'cnpj': CNPJ_B, 'legal_name': 'Filial', 'uf': 'ZZ'}, cid)


def test_create_and_fetch_multiple_cnpjs():
    conn = _conn()
    cid = _seed_company(conn, 'GRUPO', 'GRUPO SA', CNPJ_A)
    conn.commit()
    ensure_legal_entities(conn)
    fid = create_legal_entity(conn, {'cnpj': CNPJ_B, 'legal_name': 'Filial RJ', 'entity_type': 'filial', 'uf': 'RJ'}, cid)
    assert fid > 0
    entities = fetch_legal_entities(conn, actor={'role': 'general_admin', 'company_id': cid})
    assert len(entities) == 2
    cnpjs = {e['cnpj'] for e in entities}
    assert cnpjs == {CNPJ_A, CNPJ_B}


def test_fetch_scoped_to_actor_company():
    conn = _conn()
    c1 = _seed_company(conn, 'A', 'A SA', CNPJ_A)
    c2 = _seed_company(conn, 'B', 'B SA', CNPJ_B)
    conn.commit()
    ensure_legal_entities(conn)
    only_c1 = fetch_legal_entities(conn, actor={'role': 'general_admin', 'company_id': c1})
    assert {e['company_id'] for e in only_c1} == {c1}
    all_entities = fetch_legal_entities(conn, actor={'role': 'master_admin', 'company_id': None})
    assert {e['company_id'] for e in all_entities} == {c1, c2}


def test_parent_entity_must_be_same_company():
    conn = _conn()
    c1 = _seed_company(conn, 'A', 'A SA', CNPJ_A)
    c2 = _seed_company(conn, 'B', 'B SA', CNPJ_B)
    conn.commit()
    ensure_legal_entities(conn)
    parent_c2 = get_default_legal_entity_id(conn, c2)
    with pytest.raises(ValueError):
        validate_legal_entity_payload(conn, {'cnpj': CNPJ_C, 'legal_name': 'SPE', 'parent_entity_id': parent_c2}, c1)


# ── service: resolução do CNPJ do colaborador ─────────────────────────────────

def test_resolve_employee_legal_entity_defaults_to_matriz():
    conn = _conn()
    cid = _seed_company(conn, 'ACME', 'ACME SA', CNPJ_A)
    conn.commit()
    ensure_legal_entities(conn)
    default_id = get_default_legal_entity_id(conn, cid)
    assert resolve_employee_legal_entity_id(conn, cid, None) == default_id


def test_resolve_employee_legal_entity_rejects_other_company():
    conn = _conn()
    c1 = _seed_company(conn, 'A', 'A SA', CNPJ_A)
    c2 = _seed_company(conn, 'B', 'B SA', CNPJ_B)
    conn.commit()
    ensure_legal_entities(conn)
    other = get_default_legal_entity_id(conn, c2)
    with pytest.raises(ValueError):
        resolve_employee_legal_entity_id(conn, c1, other)


def test_ensure_default_legal_entity_idempotent():
    conn = _conn()
    cid = _seed_company(conn, 'ACME', 'ACME SA', CNPJ_A)
    conn.commit()
    ensure_legal_entities(conn)
    first = ensure_default_legal_entity(conn, cid)
    second = ensure_default_legal_entity(conn, cid)
    assert first == second


def test_legal_entities_ready_false_on_partial_schema():
    conn = _conn()  # sem ensure_legal_entities
    assert legal_entities_ready(conn) is False


# ── routes ────────────────────────────────────────────────────────────────────

class _FakeHandler:
    def __init__(self):
        self.path = '/api/legal-entities'
        self.command = 'GET'
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


def _patch(monkeypatch, conn, actor):
    # routes usam `with closing(get_connection())`, que chama .close(); o wrapper
    # devolve a própria conn de teste e neutraliza o close.
    monkeypatch.setattr(routes, 'get_connection', lambda: _NoCloseConn(conn))
    monkeypatch.setattr(routes, 'resolve_actor_user_id', lambda *a, **k: actor['id'])
    monkeypatch.setattr(routes, 'authorize_action', lambda *a, **k: actor)


class _NoCloseConn:
    def __init__(self, conn):
        self._conn = conn

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def close(self):
        pass


def test_route_post_and_get_legal_entities(monkeypatch):
    conn = _conn()
    cid = _seed_company(conn, 'GRUPO', 'GRUPO SA', CNPJ_A)
    conn.commit()
    ensure_legal_entities(conn)
    actor = {'id': 1, 'role': 'general_admin', 'company_id': cid}
    _patch(monkeypatch, conn, actor)

    h = _FakeHandler()
    payload = {'actor_user_id': 1, 'cnpj': CNPJ_B, 'legal_name': 'Filial SP', 'entity_type': 'filial', 'uf': 'SP'}
    routes.handle_post_legal_entities(h, urlparse('/api/legal-entities'), payload, None)
    assert h.status == 201
    assert h.json()['ok'] is True

    h2 = _FakeHandler()
    routes.handle_get_legal_entities(h2, urlparse('/api/legal-entities?actor_user_id=1'), None, None)
    assert h2.status == 200
    assert len(h2.json()['legal_entities']) == 2


def test_route_batch_reports_per_item_errors(monkeypatch):
    conn = _conn()
    cid = _seed_company(conn, 'JV', 'JV SA', CNPJ_A)
    conn.commit()
    ensure_legal_entities(conn)
    actor = {'id': 1, 'role': 'general_admin', 'company_id': cid}
    _patch(monkeypatch, conn, actor)

    h = _FakeHandler()
    payload = {
        'actor_user_id': 1,
        'legal_entities': [
            {'cnpj': CNPJ_B, 'legal_name': 'Empresa A', 'entity_type': 'jv_partner'},
            {'cnpj': 'invalid', 'legal_name': 'Empresa B'},
        ],
    }
    routes.handle_post_legal_entities_batch(h, urlparse('/api/legal-entities/batch'), payload, None)
    body = h.json()
    assert h.status == 207  # parcial: um criado, um com erro
    assert len(body['created_ids']) == 1
    assert len(body['errors']) == 1
    assert body['errors'][0]['index'] == 1
