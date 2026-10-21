"""Importação de ESTOQUE no Centro de Migração em PostgreSQL real (Fase 4).

Prova o writer/reverser de estoque de ponta a ponta no motor genérico:

- saldo inicial gravado como PAR movimento (`stock_movements`) + saldo
  (`unit_epi_stock`) — nunca saldo sem movimento;
- idempotência por SET (reimportar o mesmo saldo → skip, sem movimento novo);
- ajuste de saldo com movimento de correção e `previous/new` corretos;
- rollback FÍSICO dos dois casos (inserção e ajuste): o reverser apaga os
  movimentos de migração do job e o rollback genérico restaura/apaga o saldo;
- quantidade inválida/negativa bloqueia no preview e nunca grava;
- isolamento multi-tenant (unidade de outro tenant não resolve).

DATABASE_URL precisa nomear um banco isolado — o bootstrap aplica o schema.
"""
import csv
import io
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
pytestmark = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL', '').startswith('postgres'),
    reason='Importação de estoque exige PostgreSQL real.',
)


def scalar(conn, sql, params=()):
    from epi_backend.db import row_to_dict
    row = conn.execute(sql, params).fetchone()
    return next(iter(row_to_dict(row).values())) if row else None


@pytest.fixture(scope='module', autouse=True)
def schema():
    from core.bootstrap import init_db
    init_db()


def _new_company(conn, prefix):
    from tests_postgres.test_migration_journey_postgres import _valid_cnpj_from
    tag = uuid.uuid4().hex
    cid = scalar(conn, "INSERT INTO companies(name,cnpj,logo_type) VALUES(%s,%s,'') RETURNING id",
                 (f'{prefix} {tag}', _valid_cnpj_from(f'{int(tag[:12], 16) % 10**12:012d}')))
    conn.commit()
    return cid


@pytest.fixture
def ctx(schema):
    from core.database import get_connection
    c = get_connection()
    cid = _new_company(c, 'Estoque')
    # O movimento de estoque tem FK actor_user_id -> users(id): em produção o
    # ator é sempre um admin autenticado real. Cria um para a importação.
    uid = scalar(c, "INSERT INTO users(username,password,full_name,role,company_id) "
                    "VALUES(%s,'x','Synthetic Admin','general_admin',%s) RETURNING id",
                 ('estoque-' + uuid.uuid4().hex[:10], cid))
    c.commit()
    state = {'conn': c, 'company_id': cid,
             'actor': {'id': uid, 'full_name': 'Synthetic Admin', 'company_id': cid}}
    # Semeia unidade + EPI pelo próprio motor (resolvíveis por nome na importação).
    _run(state, 'unidades', [{'name': 'Almox Central', 'unit_type': 'base', 'city': 'Macaé'}])
    _run(state, 'epis', [{'name': 'Luva Nitrílica', 'purchase_code': 'EST-EPI-1', 'ca': '12345',
          'ca_expiry': '2030-01-01', 'epi_validity_date': '2031-01-01',
          'unit_measure': 'PAR', 'sector': 'Almox'}])
    yield state
    c.rollback()
    c.close()


def _run(ctx, entity, rows, strategy='insert_only'):
    from modules.data_migration.service import run_migration
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return run_migration(ctx['conn'], company_id=ctx['company_id'], entity=entity,
                         source_kind='csv', raw=stream.getvalue().encode(),
                         mapping={k: k for k in rows[0]}, strategy=strategy,
                         actor=ctx['actor'], source_name='estoque.csv')


def _stock(ctx, qty, strategy='insert_only', unit='Almox Central', epi='Luva Nitrílica'):
    return _run(ctx, 'estoque', [{'unit_id': unit, 'epi_id': epi, 'quantity': str(qty)}], strategy)


def _balance(ctx):
    return scalar(ctx['conn'], 'SELECT quantity FROM unit_epi_stock WHERE company_id=%s',
                  (ctx['company_id'],))


def _movements(ctx):
    from epi_backend.db import row_to_dict
    return [row_to_dict(r) for r in ctx['conn'].execute(
        'SELECT movement_type, quantity, previous_stock, new_stock, source_type, source_id '
        'FROM stock_movements WHERE company_id=%s ORDER BY id', (ctx['company_id'],)).fetchall()]


def test_import_sets_balance_and_records_a_migration_movement(ctx):
    job = _stock(ctx, 100)
    assert job['applied'] and job['totals']['inserted'] == 1, job['totals']
    assert _balance(ctx) == 100
    movs = _movements(ctx)
    assert len(movs) == 1, movs
    m = movs[0]
    assert m['source_type'] == 'migration' and int(m['source_id']) == job['job_id']
    assert m['movement_type'] == 'in' and m['quantity'] == 100
    assert m['previous_stock'] == 0 and m['new_stock'] == 100


def test_reimport_same_balance_is_idempotent_skip(ctx):
    _stock(ctx, 100)
    job = _stock(ctx, 100, 'upsert')  # mesmo saldo declarado → delta 0 → skip
    assert job['totals']['skipped'] == 1 and job['totals']['inserted'] == 0 \
        and job['totals']['updated'] == 0, job['totals']
    assert _balance(ctx) == 100
    assert len(_movements(ctx)) == 1  # nenhum movimento novo na reimportação


def test_upsert_adjusts_balance_with_a_correction_movement(ctx):
    _stock(ctx, 100)
    job = _stock(ctx, 80, 'upsert')
    assert job['totals']['updated'] == 1, job['totals']
    assert _balance(ctx) == 80
    movs = _movements(ctx)
    assert len(movs) == 2, movs
    assert movs[1]['movement_type'] == 'out' and movs[1]['quantity'] == 20
    assert movs[1]['previous_stock'] == 100 and movs[1]['new_stock'] == 80


def test_rollback_of_an_insert_removes_movement_and_balance(ctx):
    from modules.data_migration.service import revert_job
    job = _stock(ctx, 100)
    assert _balance(ctx) == 100 and len(_movements(ctx)) == 1
    revert_job(ctx['conn'], job['job_id'], ctx['company_id'], ctx['actor'])
    ctx['conn'].rollback()  # revert_job faz commit; limpa o snapshot da nossa txn
    assert _balance(ctx) is None          # saldo inserido pelo job foi apagado
    assert _movements(ctx) == []          # movimento de migração do job sumiu


def test_rollback_of_an_adjustment_restores_the_previous_balance(ctx):
    from modules.data_migration.service import revert_job
    _stock(ctx, 100)                       # job 1: cria saldo 100 (+1 movimento)
    job2 = _stock(ctx, 80, 'upsert')       # job 2: ajusta p/ 80 (+1 movimento de correção)
    revert_job(ctx['conn'], job2['job_id'], ctx['company_id'], ctx['actor'])
    ctx['conn'].rollback()
    assert _balance(ctx) == 100            # saldo volta ao anterior ao job 2
    movs = _movements(ctx)                 # só o movimento de correção do job 2 é removido
    assert len(movs) == 1 and movs[0]['new_stock'] == 100, movs


@pytest.mark.parametrize('qty', ['-5', '1.5', 'abc', ''])
def test_invalid_quantity_blocks_and_never_writes(ctx, qty):
    preview = _stock(ctx, qty, 'dry_run')['preview']
    assert preview['blocking'] is True, preview
    with pytest.raises(ValueError):
        _stock(ctx, qty)
    ctx['conn'].rollback()
    assert _balance(ctx) is None
    assert _movements(ctx) == []


def test_unknown_unit_is_rejected_and_never_writes(ctx):
    preview = _stock(ctx, 50, 'dry_run', unit='Unidade Inexistente')['preview']
    assert preview['blocking'] is True, preview
    with pytest.raises(ValueError):
        _stock(ctx, 50, unit='Unidade Inexistente')
    ctx['conn'].rollback()
    assert _balance(ctx) is None and _movements(ctx) == []


def test_tenant_isolation_a_unit_from_another_company_does_not_resolve(ctx):
    from core.database import get_connection
    other_conn = get_connection()
    try:
        bid = _new_company(other_conn, 'Outro')
        other = {'conn': other_conn, 'company_id': bid,
                 'actor': {'id': 0, 'full_name': 'B', 'company_id': bid}}
        _run(other, 'unidades', [{'name': 'Unidade Secreta B', 'unit_type': 'base', 'city': 'Rio'}])
    finally:
        other_conn.close()
    # Tenant A tenta importar estoque para a unidade de B → não resolve → bloqueia.
    preview = _stock(ctx, 10, 'dry_run', unit='Unidade Secreta B')['preview']
    assert preview['blocking'] is True, preview
    assert _balance(ctx) is None
