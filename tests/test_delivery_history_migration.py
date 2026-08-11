"""Lote 2 do Centro de Migração — importar HISTÓRICO de entregas (issue #211).

O que este arquivo trava, e por quê cada um importa:

1. **Procedência.** Uma entrega importada carrega `origin='migracao'`,
   `source_system` e `migration_job_id`. Em auditoria trabalhista, a diferença
   entre "o sistema registrou a entrega" e "o cliente afirmou que a entrega
   ocorreu" é a diferença entre prova e declaração.
2. **Nada de estoque.** A importação não pode movimentar o saldo atual: a
   entrega é de 2019, o estoque é de hoje.
3. **Data original preservada.** É o motivo de a importação existir.
4. **`snapshot_*` intocadas.** Preenchê-las com o cadastro de hoje afirmaria
   que o vínculo atual valia na época.
5. **Reimportação não duplica.**
6. **Rollback em dois regimes**: físico antes da homologação, lógico depois.
7. **Rollback lógico realmente reverte** — a entrega marcada some das leituras
   operacionais. Um rollback que só põe um carimbo e deixa a entrega contando
   é pior do que rollback nenhum, porque parece ter funcionado.
"""

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.schema import ensure_data_migration_tables
from modules.data_migration import service
from modules.data_migration.catalog import get_entity
from modules.data_migration.sources import source_system_for


@pytest.fixture(autouse=True)
def _sqlite_detection(monkeypatch):
    import epi_backend.db as db_module
    monkeypatch.setattr(db_module, '_is_sqlite_connection', lambda _conn: True)


def _dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


class _PgStyleConn:
    """Traduz o dialeto Postgres (%s) do código para SQLite (?)."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        return self._conn.execute(str(sql).replace('%s', '?'), params)

    def commit(self):
        self._conn.commit()

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _conn():
    raw = sqlite3.connect(':memory:')
    raw.row_factory = _dict_factory
    raw.executescript(
        """
        CREATE TABLE companies (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT);
        CREATE TABLE units (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            name TEXT DEFAULT ''
        );
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL, name TEXT NOT NULL, employee_id_code TEXT NOT NULL,
            cpf TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE epis (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            name TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            epi_id INTEGER, quantity INTEGER
        );
        -- Espelha as colunas REAIS de `deliveries` que este lote toca,
        -- incluindo as NOT NULL sem default que o catálogo cobre por
        -- `column_defaults`. Fixture mais frouxa que a produção foi
        -- exatamente o que deixou passar problemas nas fases anteriores.
        CREATE TABLE deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            employee_id INTEGER NOT NULL,
            epi_id INTEGER NOT NULL,
            unit_id INTEGER,
            quantity INTEGER NOT NULL,
            quantity_label TEXT NOT NULL,
            sector TEXT NOT NULL,
            role_name TEXT NOT NULL,
            delivery_date TEXT NOT NULL,
            next_replacement_date TEXT NOT NULL,
            notes TEXT DEFAULT '',
            signature_name TEXT NOT NULL,
            signature_data TEXT NOT NULL DEFAULT '',
            signature_at TEXT NOT NULL DEFAULT '',
            signature_ip TEXT NOT NULL DEFAULT '',
            returned_date TEXT NOT NULL DEFAULT '',
            stock_movement_id INTEGER,
            idempotency_key TEXT NOT NULL DEFAULT '',
            snapshot_tipo_vinculo TEXT NOT NULL DEFAULT '',
            snapshot_outsourced_company_name TEXT NOT NULL DEFAULT '',
            snapshot_outsourced_company_cnpj TEXT NOT NULL DEFAULT '',
            snapshot_contract_ref TEXT NOT NULL DEFAULT '',
            snapshot_epi_responsibility TEXT NOT NULL DEFAULT '',
            origin TEXT NOT NULL DEFAULT 'sistema',
            source_system TEXT NOT NULL DEFAULT '',
            migration_job_id INTEGER,
            migration_reverted_at TEXT NOT NULL DEFAULT ''
        );
        CREATE UNIQUE INDEX idx_deliveries_idempotency
            ON deliveries (company_id, idempotency_key) WHERE idempotency_key <> '';
        """
    )
    conn = _PgStyleConn(raw)
    ensure_data_migration_tables(conn)
    return conn


def _seed(conn, name='ACME'):
    company_id = int(conn.execute('INSERT INTO companies (name) VALUES (?)', (name,)).lastrowid)
    conn.execute('INSERT INTO units (company_id, name) VALUES (?, ?)', (company_id, 'Base Macaé'))
    # Matrícula puramente numérica é o caso NORMAL num export legado — e é a
    # que exercita o atalho de id interno desligado no descritor.
    for code, person in (('1001', 'Maria Silva'), ('1002', 'João Souza')):
        conn.execute(
            'INSERT INTO employees (company_id, unit_id, name, employee_id_code) '
            'VALUES (?, (SELECT id FROM units WHERE company_id = ?), ?, ?)',
            (company_id, company_id, person, code),
        )
    conn.execute('INSERT INTO epis (company_id, name) VALUES (?, ?)', (company_id, 'Luva Nitrílica'))
    conn.execute('INSERT INTO epis (company_id, name) VALUES (?, ?)', (company_id, 'Capacete'))
    conn.commit()
    return company_id


def _actor(company_id, user_id=7):
    return {'id': user_id, 'role': 'general_admin', 'company_id': company_id,
            'full_name': 'Ana Geral'}


_CSV = (
    'Matrícula;EPI;Data da Entrega;Quantidade;Recebido por;Unidade\n'
    '1001;Luva Nitrílica;31/12/2019;2;Maria Silva;Base Macaé\n'
    '1002;Capacete;15/03/2020;1;João Souza;Base Macaé\n'
)

_MAPPING = {
    'Matrícula': 'employee_id', 'EPI': 'epi_id', 'Data da Entrega': 'delivery_date',
    'Quantidade': 'quantity', 'Recebido por': 'signature_name', 'Unidade': 'unit_id',
}


def _import(conn, company_id, *, raw=None, source_kind='csv', strategy='insert_only'):
    return service.run_migration(
        conn,
        company_id=company_id,
        entity='historico_entregas',
        source_kind=source_kind,
        raw=(raw if raw is not None else _CSV).encode('utf-8'),
        mapping=_MAPPING,
        strategy=strategy,
        actor=_actor(company_id),
        source_name='historico_legado.csv',
    )


def _deliveries(conn, company_id):
    return conn.execute(
        'SELECT * FROM deliveries WHERE company_id = ? ORDER BY id', (company_id,)
    ).fetchall()


# ── 1. Procedência ──────────────────────────────────────────────────────────

def test_imported_delivery_is_stamped_as_migrated_with_its_job_and_source():
    conn = _conn()
    cid = _seed(conn)
    result = _import(conn, cid)
    assert result['totals']['inserted'] == 2, result['totals']

    for row in _deliveries(conn, cid):
        assert row['origin'] == 'migracao'
        assert row['source_system'] == 'planilha'
        assert int(row['migration_job_id']) == int(result['job_id'])


def test_a_delivery_created_by_the_system_stays_marked_as_system():
    """O DEFAULT da coluna precisa ser verdadeiro para quem NÃO passa pela
    importação — é o que torna a distinção utilizável."""
    conn = _conn()
    cid = _seed(conn)
    conn.execute(
        'INSERT INTO deliveries (company_id, employee_id, epi_id, quantity, quantity_label, '
        "sector, role_name, delivery_date, next_replacement_date, signature_name) "
        "VALUES (?, 1, 1, 1, 'un', '', '', '2026-01-10', '', 'Maria Silva')",
        (cid,),
    )
    conn.commit()
    row = _deliveries(conn, cid)[0]
    assert row['origin'] == 'sistema'
    assert row['source_system'] == ''
    assert row['migration_job_id'] is None


@pytest.mark.parametrize('kind,expected', [
    ('csv', 'planilha'), ('xlsx', 'planilha'), ('ods', 'planilha'),
    ('sap', 'sap'), ('totvs', 'totvs'), ('rest', 'api'), ('graphql', 'api'),
    ('postgresql', 'banco'),
])
def test_source_system_is_derived_from_the_source_kind(kind, expected):
    """Derivar em vez de pedir ao usuário: uma integração nova entra no mapa
    uma vez e todo registro dela nasce carimbado certo."""
    assert source_system_for(kind) == expected


def test_an_unknown_source_kind_is_still_stamped_instead_of_left_blank():
    """Carimbo estranho é diagnosticável; ausência de carimbo é indistinguível
    de um bug."""
    assert source_system_for('erp_do_cliente') == 'erp_do_cliente'


# ── 2. Estoque intocado ─────────────────────────────────────────────────────

def test_importing_history_never_moves_current_stock():
    conn = _conn()
    cid = _seed(conn)
    before = conn.execute('SELECT COUNT(*) AS n FROM stock_movements').fetchone()['n']
    _import(conn, cid)
    after = conn.execute('SELECT COUNT(*) AS n FROM stock_movements').fetchone()['n']
    assert before == after == 0, 'A importação de histórico gerou movimento de estoque.'
    for row in _deliveries(conn, cid):
        assert row['stock_movement_id'] is None


# ── 3. Data original ────────────────────────────────────────────────────────

def test_the_original_delivery_date_is_preserved_and_normalized_to_iso():
    conn = _conn()
    cid = _seed(conn)
    _import(conn, cid)
    dates = [row['delivery_date'] for row in _deliveries(conn, cid)]
    assert dates == ['2019-12-31', '2020-03-15'], dates


def test_an_unparseable_date_blocks_the_file_instead_of_being_guessed():
    """"03/04/2024" pode ser 3 de abril ou 4 de março. Num histórico de EPI,
    errar o mês desloca a entrega de período de ficha — então formato não
    reconhecido é erro, nunca um chute.

    O motor bloqueia o ARQUIVO inteiro, não só a linha: importar metade de um
    histórico deixaria o cliente com um registro incompleto que ele não tem
    como auditar.
    """
    conn = _conn()
    cid = _seed(conn)
    bad = (
        'Matrícula;EPI;Data da Entrega;Quantidade;Recebido por;Unidade\n'
        '1001;Luva Nitrílica;ontem;2;Maria Silva;Base Macaé\n'
    )
    with pytest.raises(ValueError, match='bloqueada'):
        _import(conn, cid, raw=bad)
    assert _deliveries(conn, cid) == []


# ── 4. `snapshot_*` não são preenchidas ─────────────────────────────────────

SNAPSHOT_COLUMNS = (
    'snapshot_tipo_vinculo', 'snapshot_outsourced_company_name',
    'snapshot_outsourced_company_cnpj', 'snapshot_contract_ref',
    'snapshot_epi_responsibility',
)


def test_snapshot_columns_are_left_as_not_informed():
    """O snapshot congela o vínculo NO MOMENTO da entrega. Preenchê-lo com o
    cadastro de hoje afirmaria que o vínculo atual valia em 2019."""
    conn = _conn()
    cid = _seed(conn)
    _import(conn, cid)
    for row in _deliveries(conn, cid):
        for column in SNAPSHOT_COLUMNS:
            assert row[column] == '', f'{column} foi preenchida pela importação'


def test_the_import_declares_no_signature_evidence():
    """Assinatura importada tem NOME (quem recebeu, a informação que sobreviveu
    à migração) e não tem IMAGEM — este sistema não coletou nada."""
    conn = _conn()
    cid = _seed(conn)
    _import(conn, cid)
    rows = _deliveries(conn, cid)
    assert [r['signature_name'] for r in rows] == ['Maria Silva', 'João Souza']
    for row in rows:
        assert row['signature_data'] == ''
        assert row['signature_at'] == ''
        assert row['signature_ip'] == ''


# ── 5. Reimportação não duplica ─────────────────────────────────────────────

def test_reimporting_the_same_file_skips_instead_of_duplicating():
    conn = _conn()
    cid = _seed(conn)
    _import(conn, cid)
    second = _import(conn, cid)
    assert second['totals']['inserted'] == 0
    assert second['totals']['skipped'] == 2
    assert len(_deliveries(conn, cid)) == 2, 'Reimportação duplicou o histórico.'


def test_two_identical_deliveries_in_the_same_file_both_enter():
    """Duas luvas para a mesma pessoa, do mesmo EPI, no mesmo dia são entregas
    LEGÍTIMAS e distintas — é por isso que o número da linha entra na chave."""
    conn = _conn()
    cid = _seed(conn)
    twice = (
        'Matrícula;EPI;Data da Entrega;Quantidade;Recebido por;Unidade\n'
        '1001;Luva Nitrílica;31/12/2019;1;Maria Silva;Base Macaé\n'
        '1001;Luva Nitrílica;31/12/2019;1;Maria Silva;Base Macaé\n'
    )
    result = _import(conn, cid, raw=twice)
    assert result['totals']['inserted'] == 2
    assert len(_deliveries(conn, cid)) == 2


# ── 6. Matrícula numérica não vira id interno ───────────────────────────────

def test_a_numeric_registration_number_is_never_read_as_an_internal_id():
    """Com o atalho numérico ligado, a matrícula "1" seria procurada como
    `employees.id = 1` — e a entrega iria para a PESSOA ERRADA, em silêncio.

    A matrícula '2' NÃO existe neste tenant; o `employees.id = 2` existe (João).
    Com o atalho ligado, a linha entraria atribuída a João. Sem ele, a
    referência fica sem resolver e o arquivo é bloqueado — que é o resultado
    certo: melhor recusar o arquivo do que registrar que alguém recebeu um EPI
    que nunca recebeu.
    """
    assert get_entity('historico_entregas').spec_for('employee_id').accepts_internal_id is False

    conn = _conn()
    cid = _seed(conn)
    hostile = (
        'Matrícula;EPI;Data da Entrega;Quantidade;Recebido por;Unidade\n'
        '2;Luva Nitrílica;31/12/2019;1;Alguém;Base Macaé\n'
    )
    with pytest.raises(ValueError, match='bloqueada'):
        _import(conn, cid, raw=hostile)
    assert _deliveries(conn, cid) == [], (
        'Uma matrícula inexistente resolveu para um id interno — a entrega '
        'seria atribuída à pessoa errada.'
    )


# ── 7. Rollback nos dois regimes ────────────────────────────────────────────

def test_rollback_before_homologation_physically_removes_the_rows():
    conn = _conn()
    cid = _seed(conn)
    result = _import(conn, cid)
    reverted = service.revert_job(conn, result['job_id'], cid, _actor(cid))
    assert reverted['deleted'] == 2
    assert reverted['marked'] == 0
    assert _deliveries(conn, cid) == []


def test_rollback_after_homologation_preserves_the_rows_and_marks_them():
    conn = _conn()
    cid = _seed(conn)
    result = _import(conn, cid)
    service.homologate_job(conn, result['job_id'], cid, _actor(cid))

    reverted = service.revert_job(conn, result['job_id'], cid, _actor(cid))
    assert reverted['deleted'] == 0
    assert reverted['marked'] == 2

    rows = _deliveries(conn, cid)
    assert len(rows) == 2, 'Rollback lógico apagou histórico homologado.'
    for row in rows:
        assert row['migration_reverted_at'], 'Linha revertida ficou sem marcação.'
        # A procedência continua legível — é o que sustenta a auditoria.
        assert row['origin'] == 'migracao'
        assert int(row['migration_job_id']) == int(result['job_id'])


def test_homologation_is_one_way():
    """Poder "des-homologar" reabriria a porta que a homologação fecha."""
    conn = _conn()
    cid = _seed(conn)
    result = _import(conn, cid)
    service.homologate_job(conn, result['job_id'], cid, _actor(cid))
    with pytest.raises(ValueError, match='já foi homologada'):
        service.homologate_job(conn, result['job_id'], cid, _actor(cid))


def test_a_reverted_job_cannot_be_homologated():
    conn = _conn()
    cid = _seed(conn)
    result = _import(conn, cid)
    service.revert_job(conn, result['job_id'], cid, _actor(cid))
    with pytest.raises(ValueError, match='foi revertida'):
        service.homologate_job(conn, result['job_id'], cid, _actor(cid))


def test_a_homologated_entity_without_logical_rollback_is_refused_not_deleted():
    """A regra que impede o pior resultado: nunca cair no DELETE por falta de
    suporte a rollback lógico, justamente onde o dado é mais sensível."""
    conn = _conn()
    cid = _seed(conn)
    result = _import(conn, cid)
    conn.execute(
        "UPDATE migration_jobs SET homologated_at = '2026-08-11T00:00:00+00:00' WHERE id = ?",
        (result['job_id'],),
    )
    conn.commit()

    import modules.data_migration.service as svc
    original = svc.get_entity

    def _without_reversal(key):
        from dataclasses import replace
        return replace(original(key), reversal_column='')

    svc.get_entity = _without_reversal
    try:
        with pytest.raises(ValueError, match='[Rr]eversão lógica não está'):
            service.revert_job(conn, result['job_id'], cid, _actor(cid))
    finally:
        svc.get_entity = original

    assert len(_deliveries(conn, cid)) == 2, 'A recusa não impediu o DELETE.'


# ── 8. O rollback lógico realmente reverte ──────────────────────────────────

def test_a_logically_reverted_delivery_disappears_from_operational_reads():
    """Sem isto, a marcação seria decoração: a entrega revertida continuaria
    contando como posse ativa de EPI e podendo ser devolvida."""
    from modules.deliveries.visibility import active_delivery_sql

    conn = _conn()
    cid = _seed(conn)
    result = _import(conn, cid)
    service.homologate_job(conn, result['job_id'], cid, _actor(cid))
    service.revert_job(conn, result['job_id'], cid, _actor(cid))

    clause = active_delivery_sql(conn, 'deliveries', prefix=' AND ')
    assert clause, 'O predicado sumiu — as leituras deixariam de filtrar.'
    visible = conn.execute(
        f'SELECT COUNT(*) AS n FROM deliveries WHERE company_id = ?{clause}', (cid,)
    ).fetchone()['n']
    assert visible == 0, 'Entrega revertida continua visível nas leituras.'

    total = conn.execute(
        'SELECT COUNT(*) AS n FROM deliveries WHERE company_id = ?', (cid,)
    ).fetchone()['n']
    assert total == 2, 'A auditoria perdeu as linhas.'


def test_the_predicate_is_inert_when_the_column_does_not_exist_yet():
    """Tenant em schema anterior à migration 023 precisa continuar lendo
    entregas — sem a coluna, o predicado some em vez de estourar."""
    from modules.deliveries.visibility import active_delivery_sql

    raw = sqlite3.connect(':memory:')
    raw.row_factory = _dict_factory
    raw.execute('CREATE TABLE deliveries (id INTEGER PRIMARY KEY, company_id INTEGER)')
    assert active_delivery_sql(_PgStyleConn(raw), 'deliveries') == ''
