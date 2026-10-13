"""EST-V3 operacional contra PostgreSQL REAL (constraints/triggers da EST-V2).

A suíte SQLite exercita a lógica operacional, mas NÃO impõe as constraints/
triggers que só existem em PostgreSQL (migrations 030/031): CHECK de
expiry_source+evidence junto de physical_expiry_date, e o trigger que exige o
responsável do bloqueio na mesma empresa. Aqui provamos que as ESCRITAS
operacionais da EST-V3 satisfazem essas regras no banco real.
"""

import os
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL', '').startswith('postgres'),
    reason='EST-V3 operacional exige PostgreSQL real.',
)

PAST = (date.today() - timedelta(days=10)).isoformat()
SOON = (date.today() + timedelta(days=5)).isoformat()
FUTURE = (date.today() + timedelta(days=365)).isoformat()


@pytest.fixture(scope='module')
def conn():
    from core.bootstrap import init_db
    from core.database import get_connection
    init_db()
    connection = get_connection()
    yield connection
    connection.close()


@pytest.fixture
def seed(conn):
    c = conn
    c.execute('SAVEPOINT est_v3')
    now = datetime.now(timezone.utc).isoformat()
    sfx = uuid4().hex
    company = c.execute('INSERT INTO companies(name,cnpj,logo_type) VALUES (?,?,?)',
                        ('EST-V3 ' + sfx, sfx, 'text')).lastrowid
    company2 = c.execute('INSERT INTO companies(name,cnpj,logo_type) VALUES (?,?,?)',
                         ('EST-V3b ' + sfx, sfx + 'b', 'text')).lastrowid
    unit = c.execute('INSERT INTO units(company_id,name,unit_type,city) VALUES (?,?,?,?)',
                     (company, 'Unid', 'base', 'Test')).lastrowid
    epi = c.execute('INSERT INTO epis(company_id,unit_id,name,purchase_code,ca,sector,unit_measure,'
                    'ca_expiry,epi_validity_date,manufacture_date,validity_days) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                    (company, unit, 'EPI', sfx, 'CA', 'S', 'un', '2026-01-01', FUTURE, '2020-01-01', 0)).lastrowid
    actor = c.execute('INSERT INTO users(username,password,full_name,role,company_id) VALUES (?,?,?,?,?)',
                      (sfx, 'x', 'Actor', 'general_admin', company)).lastrowid
    actor2 = c.execute('INSERT INTO users(username,password,full_name,role,company_id) VALUES (?,?,?,?,?)',
                       (sfx + 'b', 'x', 'Actor2', 'general_admin', company2)).lastrowid

    def item(status='in_stock'):
        from modules.stock.service import create_stock_item, next_company_qr_sequence
        seqv = next_company_qr_sequence(c, company)
        iid = create_stock_item(c, company, unit, epi, 'N/A', 'M', 'N/A', seqv,
                                'QR-' + uuid4().hex, None, '', '', 'unit', '', '', actor, now)
        if status != 'in_stock':
            c.execute('UPDATE epi_stock_items SET status=? WHERE id=?', (status, iid))
        return iid

    yield dict(c=c, company=company, company2=company2, unit=unit, epi=epi,
               actor=actor, actor2=actor2, now=now, item=item)
    c.execute('ROLLBACK TO SAVEPOINT est_v3')
    c.execute('RELEASE SAVEPOINT est_v3')
    c.rollback()


def test_receipt_physical_write_satisfies_pg_check(seed):
    from modules.stock.service import item_physical_expiry, record_received_item_physical
    iid = seed['item']()
    # Se expiry_source/evidence estivessem errados, o CHECK EST-V2 rejeitaria.
    record_received_item_physical(seed['c'], iid, FUTURE, seed['actor'], seed['now'])
    row = seed['c'].execute(
        'SELECT physical_expiry_date, expiry_source, expiry_evidence, status FROM epi_stock_items WHERE id=?', (iid,)
    ).fetchone()
    assert str(row['physical_expiry_date']) == FUTURE
    assert row['expiry_source'] == 'manufacturer_document' and row['expiry_evidence']
    assert row['status'] == 'in_stock'
    assert item_physical_expiry(seed['c'], iid) == FUTURE


def test_expired_receipt_blocks_with_same_company_actor(seed):
    from modules.stock.service import blocked_physical_quantity, record_received_item_physical
    iid = seed['item']()
    record_received_item_physical(seed['c'], iid, PAST, seed['actor'], seed['now'])
    row = seed['c'].execute(
        'SELECT status, blocking_reason_code, blocked_by_user_id FROM epi_stock_items WHERE id=?', (iid,)
    ).fetchone()
    assert row['status'] == 'blocked_expired'
    assert row['blocking_reason_code'] == 'expired'
    assert row['blocked_by_user_id'] == seed['actor']
    assert blocked_physical_quantity(seed['c'], seed['company'], seed['unit'], seed['epi']) == 1


def test_block_actor_from_another_company_is_rejected_by_pg_trigger(seed):
    import psycopg2
    from modules.stock.service import record_received_item_physical
    iid = seed['item']()
    seed['c'].execute('SAVEPOINT foreign_actor')
    with pytest.raises(psycopg2.Error):
        # actor2 pertence a outra empresa → trigger stock_item_block_actor_scope recusa
        record_received_item_physical(seed['c'], iid, PAST, seed['actor2'], seed['now'])
    seed['c'].execute('ROLLBACK TO SAVEPOINT foreign_actor')


def test_block_then_unblock_structured_fields(seed):
    from modules.stock.service import set_stock_item_status
    iid = seed['item']()
    it = seed['c'].execute('SELECT * FROM epi_stock_items WHERE id=?', (iid,)).fetchone()
    set_stock_item_status(seed['c'], it, 'blocked_rejected', 'reprovado', seed['actor'], 'Actor', seed['now'])
    row = seed['c'].execute('SELECT status, blocking_reason_code, blocked_by_user_id FROM epi_stock_items WHERE id=?', (iid,)).fetchone()
    assert row['status'] == 'blocked_rejected' and row['blocking_reason_code'] == 'rejected'
    assert row['blocked_by_user_id'] == seed['actor']
    it2 = seed['c'].execute('SELECT * FROM epi_stock_items WHERE id=?', (iid,)).fetchone()
    set_stock_item_status(seed['c'], it2, 'in_stock', '', seed['actor'], 'Actor', seed['now'])
    row = seed['c'].execute('SELECT status, blocking_reason_code, blocked_by_user_id FROM epi_stock_items WHERE id=?', (iid,)).fetchone()
    assert row['status'] == 'in_stock' and row['blocking_reason_code'] is None and row['blocked_by_user_id'] is None


def test_unblock_of_physically_expired_is_refused(seed):
    from modules.stock.service import record_received_item_physical, set_stock_item_status
    iid = seed['item']()
    record_received_item_physical(seed['c'], iid, PAST, seed['actor'], seed['now'])  # vira blocked_expired
    it = seed['c'].execute('SELECT * FROM epi_stock_items WHERE id=?', (iid,)).fetchone()
    with pytest.raises(ValueError, match='vencido'):
        set_stock_item_status(seed['c'], it, 'in_stock', 'liberar', seed['actor'], 'Actor', seed['now'])


def test_fefo_orders_by_physical_expiry_on_real_schema(seed):
    from modules.stock.service import fetch_available_stock_items, record_received_item_physical
    later = seed['item']()
    sooner = seed['item']()
    unknown = seed['item']()
    record_received_item_physical(seed['c'], later, FUTURE, seed['actor'], seed['now'])
    record_received_item_physical(seed['c'], sooner, SOON, seed['actor'], seed['now'])
    from modules.stock.service import upsert_unit_stock
    upsert_unit_stock(seed['c'], seed['company'], seed['unit'], seed['epi'], 3)
    ids = [r['id'] for r in fetch_available_stock_items(seed['c'], seed['company'], seed['unit'], seed['epi'])]
    assert ids == [sooner, later]
    assert unknown not in ids
