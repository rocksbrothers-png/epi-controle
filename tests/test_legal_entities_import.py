"""Bloco B Multi-CNPJ: importação de planilha de CNPJs e insumos do dashboard.

Cobre:
  - mapeamento flexível de cabeçalhos (português com/sem acento e inglês);
  - importação idempotente: CNPJ existente é atualizado, novo é criado;
  - erros reportados por linha (1-based) sem abortar a importação inteira;
  - vínculo `legal_entity_id` exposto em `fetch_units`, insumo do filtro em
    cascata Empresa → CNPJ → Unidade → Setor.
"""

import sqlite3

from core.schema import ensure_legal_entities
from modules.legal_entities.service import (
    fetch_legal_entities,
    get_default_legal_entity_id,
    import_legal_entities_rows,
    normalize_import_row,
)
from modules.units.service import create_unit, fetch_units

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
            name TEXT, legal_name TEXT DEFAULT '', cnpj TEXT, logo_type TEXT DEFAULT ''
        );
        CREATE TABLE units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, name TEXT, unit_type TEXT DEFAULT 'base',
            city TEXT DEFAULT '', notes TEXT DEFAULT ''
        );
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, unit_id INTEGER, name TEXT
        );
        """
    )
    conn.execute("INSERT INTO companies (name, legal_name, cnpj) VALUES ('ACME', 'ACME SA', ?)", (CNPJ_A,))
    conn.commit()
    ensure_legal_entities(conn)
    return conn


# ── mapeamento de cabeçalhos ──────────────────────────────────────────────────

def test_maps_portuguese_headers_with_accents():
    row = normalize_import_row({
        'CNPJ': CNPJ_B, 'Razão Social': 'Filial RJ Ltda', 'Nome Fantasia': 'Filial RJ',
        'Inscrição Estadual': '123', 'Município': 'Rio de Janeiro', 'UF': 'RJ',
        'Situação': 'ativa', 'Observações': 'importado',
    })
    assert row['cnpj'] == CNPJ_B
    assert row['legal_name'] == 'Filial RJ Ltda'
    assert row['trade_name'] == 'Filial RJ'
    assert row['state_registration'] == '123'
    assert row['municipality'] == 'Rio de Janeiro'
    assert row['uf'] == 'RJ'
    assert row['notes'] == 'importado'


def test_maps_english_headers():
    row = normalize_import_row({'cnpj': CNPJ_B, 'legal_name': 'Branch Ltd', 'trade_name': 'Branch'})
    assert row['legal_name'] == 'Branch Ltd'
    assert row['trade_name'] == 'Branch'


def test_ignores_unknown_columns():
    """Planilhas de clientes trazem colunas extras irrelevantes."""
    row = normalize_import_row({'CNPJ': CNPJ_B, 'Razao Social': 'X', 'Coluna Aleatoria': 'lixo'})
    assert 'Coluna Aleatoria' not in row
    assert row['legal_name'] == 'X'


def test_maps_entity_type_labels():
    assert normalize_import_row({'cnpj': CNPJ_B, 'tipo': 'Matriz'})['entity_type'] == 'matriz'
    assert normalize_import_row({'cnpj': CNPJ_B, 'tipo': 'Filial'})['entity_type'] == 'filial'
    assert normalize_import_row({'cnpj': CNPJ_B, 'tipo': 'Sócia'})['entity_type'] == 'jv_partner'
    assert normalize_import_row({'cnpj': CNPJ_B, 'tipo': 'SPE'})['entity_type'] == 'spe'


def test_parses_boolean_cells_in_portuguese():
    assert normalize_import_row({'cnpj': CNPJ_B, 'ativo': 'Sim'})['active'] == 1
    assert normalize_import_row({'cnpj': CNPJ_B, 'ativo': 'Não'})['active'] == 0
    assert normalize_import_row({'cnpj': CNPJ_B, 'ativo': 'inativo'})['active'] == 0


def test_active_defaults_to_true_when_column_absent():
    assert normalize_import_row({'cnpj': CNPJ_B})['active'] == 1


# ── importação ────────────────────────────────────────────────────────────────

def test_import_creates_new_cnpjs():
    conn = _conn()
    result = import_legal_entities_rows(conn, 1, [
        {'CNPJ': CNPJ_B, 'Razão Social': 'Filial RJ Ltda', 'Tipo': 'Filial'},
        {'CNPJ': CNPJ_C, 'Razão Social': 'SPE Norte Ltda', 'Tipo': 'SPE'},
    ])
    assert len(result['created_ids']) == 2
    assert result['errors'] == []
    cnpjs = {e['cnpj'] for e in fetch_legal_entities(conn, None, company_id=1)}
    assert {CNPJ_A, CNPJ_B, CNPJ_C} == cnpjs


def test_import_updates_existing_cnpj_instead_of_duplicating():
    conn = _conn()
    matriz = get_default_legal_entity_id(conn, 1)
    result = import_legal_entities_rows(conn, 1, [
        {'CNPJ': CNPJ_A, 'Razão Social': 'ACME SA — Razão Atualizada'},
    ])
    assert result['created_ids'] == []
    assert result['updated_ids'] == [matriz]
    row = conn.execute('SELECT legal_name FROM legal_entities WHERE id = ?', (matriz,)).fetchone()
    assert row['legal_name'] == 'ACME SA — Razão Atualizada'


def test_import_matches_existing_cnpj_regardless_of_formatting():
    """CNPJ sem máscara na planilha deve casar com o já cadastrado."""
    conn = _conn()
    matriz = get_default_legal_entity_id(conn, 1)
    result = import_legal_entities_rows(conn, 1, [
        {'cnpj': '11222333000181', 'razao_social': 'ACME SA'},
    ])
    assert result['updated_ids'] == [matriz]
    assert result['created_ids'] == []


def test_import_reports_errors_per_row_without_aborting():
    conn = _conn()
    result = import_legal_entities_rows(conn, 1, [
        {'CNPJ': CNPJ_B, 'Razão Social': 'Válida Ltda'},
        {'CNPJ': '00.000.000/0000-00', 'Razão Social': 'CNPJ inválido'},
        {'CNPJ': CNPJ_C, 'Razão Social': 'Outra Válida Ltda'},
    ])
    assert len(result['created_ids']) == 2   # linhas boas foram gravadas
    assert len(result['errors']) == 1
    assert result['errors'][0]['row'] == 2   # numeração 1-based, como na planilha


def test_import_requires_legal_name():
    conn = _conn()
    result = import_legal_entities_rows(conn, 1, [{'CNPJ': CNPJ_B}])
    assert result['created_ids'] == []
    assert result['errors'][0]['row'] == 1


def test_import_skips_blank_rows():
    """Linhas vazias/separadoras da planilha não viram erro."""
    conn = _conn()
    result = import_legal_entities_rows(conn, 1, [
        {}, {'CNPJ': '', 'Razão Social': ''}, {'CNPJ': CNPJ_B, 'Razão Social': 'Filial'},
    ])
    assert len(result['created_ids']) == 1
    assert result['errors'] == []


# ── insumo do filtro em cascata do dashboard ─────────────────────────────────

def test_fetch_units_exposes_legal_entity_for_cascading_filter():
    conn = _conn()
    matriz = get_default_legal_entity_id(conn, 1)
    create_unit(conn, 1, 'Base Santos', 'base', 'Santos', '', legal_entity_id=matriz)
    conn.commit()
    units = fetch_units(conn, actor={'role': 'general_admin', 'company_id': 1})
    assert units
    assert units[0]['legal_entity_id'] == matriz


def test_fetch_units_exposes_legal_entity_label():
    """O id sozinho não dá para exibir nada.

    A listagem de unidades precisa mostrar *qual* CNPJ responde pela unidade —
    no app e no web legado. Sem o rótulo vindo junto, cada tela teria de buscar
    a lista inteira de CNPJs só para traduzir um número.
    """
    conn = _conn()
    matriz = get_default_legal_entity_id(conn, 1)
    conn.execute(
        "UPDATE legal_entities SET trade_name = 'ACME Matriz' WHERE id = ?", (matriz,)
    )
    create_unit(conn, 1, 'Base Santos', 'base', 'Santos', '', legal_entity_id=matriz)
    conn.commit()
    unit = fetch_units(conn, actor={'role': 'general_admin', 'company_id': 1})[0]
    assert unit['legal_entity_cnpj']
    assert unit['legal_entity_trade_name'] == 'ACME Matriz'
    assert unit['legal_entity_legal_name']


def test_fetch_units_lists_unit_without_legal_entity():
    """Unidade ainda sem CNPJ definido continua aparecendo, com rótulo vazio.

    Se o JOIN fosse interno, a unidade sumiria da tela justamente no estado em
    que alguém precisa encontrá-la para atribuir o CNPJ.
    """
    conn = _conn()
    create_unit(conn, 1, 'Base Sem CNPJ', 'base', 'Santos', '')
    conn.commit()
    units = {u['name']: u for u in fetch_units(conn, actor={'role': 'general_admin', 'company_id': 1})}
    assert 'Base Sem CNPJ' in units
    assert not units['Base Sem CNPJ']['legal_entity_cnpj']


def test_fetch_units_works_without_legal_entity_column():
    """Retrocompatibilidade: schema sem o vínculo continua listando unidades."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT, cnpj TEXT, logo_type TEXT DEFAULT '');
        CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT,
                            unit_type TEXT, city TEXT, notes TEXT DEFAULT '');
        INSERT INTO companies (id, name, cnpj) VALUES (1, 'ACME', '11.222.333/0001-81');
        INSERT INTO units (id, company_id, name, unit_type, city) VALUES (1, 1, 'Matriz', 'base', 'SP');
        """
    )
    conn.commit()
    units = fetch_units(conn, actor={'role': 'general_admin', 'company_id': 1})
    assert len(units) == 1
    assert 'legal_entity_id' not in units[0]
