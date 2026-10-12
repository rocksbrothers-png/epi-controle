"""EST-V2 contra bootstrap/migration reais; fixtures só no banco de testes."""

import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL', '').startswith('postgres'),
    reason='EST-V2 estrutural exige PostgreSQL real.',
)


@pytest.fixture(scope='module')
def schema_connection():
    from core.bootstrap import init_db
    from core.database import get_connection

    init_db()
    connection = get_connection()
    yield connection
    connection.close()


@pytest.fixture
def stock(schema_connection):
    c = schema_connection
    c.execute('SAVEPOINT stock_model_test')
    now = datetime.now(timezone.utc).isoformat()
    companies, units, epis, actors = [], [], [], []
    for _ in range(2):
        suffix = uuid4().hex
        company = c.execute('INSERT INTO companies(name,cnpj,logo_type) VALUES (?,?,?)',
                            ('EST-V2 fixture ' + suffix, suffix, 'text')).lastrowid
        unit = c.execute('INSERT INTO units(company_id,name,unit_type,city) VALUES (?,?,?,?)',
                         (company, 'EST-V2 fixture unit', 'base', 'Test')).lastrowid
        epi = c.execute('INSERT INTO epis(company_id,unit_id,name,purchase_code,ca,sector,unit_measure,'
                        'ca_expiry,epi_validity_date,manufacture_date,validity_days) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                        (company, unit, 'Fixture EPI', suffix, 'CA-FIXTURE', 'Test', 'unit',
                         '2026-01-01', '2040-01-01', '2020-01-01', 0)).lastrowid
        actor = c.execute('INSERT INTO users(username,password,full_name,role,company_id) VALUES (?,?,?,?,?)',
                          (suffix, 'fixture-not-a-login', 'Fixture Actor', 'general_admin', company)).lastrowid
        companies.append(company)
        units.append(unit)
        epis.append(epi)
        actors.append(actor)

    def lot(**overrides):
        values = dict(company_id=companies[0], epi_id=epis[0], receipt_unit_id=units[0],
                      receipt_key=uuid4().hex, receipt_source='manual', lot_code='SAME-LABEL',
                      manufacture_date='2026-01-01', physical_expiry_date='2027-01-01',
                      expiry_source='label', expiry_evidence='Manufacturer label fixture',
                      ca_snapshot='CA-FIXTURE', ca_expiry_snapshot='2026-01-01',
                      received_quantity=1, received_by_user_id=actors[0])
        values.update(overrides)
        names = tuple(values)
        return c.execute('INSERT INTO epi_stock_lots (' + ','.join(names) + ') VALUES ('
                         + ','.join('?' for _ in names) + ')', tuple(values.values())).lastrowid

    def item(**overrides):
        from modules.stock.service import create_stock_item, next_company_qr_sequence

        seq = next_company_qr_sequence(c, companies[0])
        item_id = create_stock_item(c, companies[0], units[0], epis[0], 'N/A', 'M', 'N/A', seq,
                                    'MODEL-QR-' + uuid4().hex, None, 'LEGACY-LABEL', '',
                                    'unit', '', '', actors[0], now)
        if overrides:
            c.execute('UPDATE epi_stock_items SET ' + ','.join(n + '=?' for n in overrides)
                      + ' WHERE id=?', (*overrides.values(), item_id))
        return item_id

    def event(item_id, **overrides):
        values = dict(company_id=companies[0], epi_id=epis[0], stock_item_id=item_id, quantity=1,
                      event_type='receipt', destination_unit_id=units[0], reason_code='receipt',
                      justification='Fixture received with traceability', actor_user_id=actors[0],
                      actor_name_snapshot='Fixture Actor', actor_role_snapshot='general_admin')
        values.update(overrides)
        names = tuple(values)
        return c.execute('INSERT INTO epi_stock_events (' + ','.join(names) + ') VALUES ('
                         + ','.join('?' for _ in names) + ')', tuple(values.values())).lastrowid

    yield dict(c=c, companies=companies, units=units, epis=epis, actors=actors,
               lot=lot, item=item, event=event, now=now)
    c.execute('ROLLBACK TO SAVEPOINT stock_model_test')
    c.execute('RELEASE SAVEPOINT stock_model_test')
    c.rollback()


def rejected(c, operation, codes=('23514', '23503', '23505')):
    import psycopg2

    c.execute('SAVEPOINT expected_rejection')
    try:
        with pytest.raises(psycopg2.Error) as caught:
            operation()
        assert caught.value.pgcode in codes
        return str(caught.value)
    finally:
        c.execute('ROLLBACK TO SAVEPOINT expected_rejection')
        c.execute('RELEASE SAVEPOINT expected_rejection')


def test_lots_keep_distinct_physical_dates_and_ca_without_changing_catalog(stock):
    s = stock
    first = s['lot'](physical_expiry_date='2027-01-01', unit_cost=None)
    second = s['lot'](physical_expiry_date='2028-01-01', unit_cost='0')
    rows = s['c'].execute('SELECT * FROM epi_stock_lots WHERE id IN (?,?) ORDER BY id', (first, second)).fetchall()
    assert str(rows[0]['physical_expiry_date']) == '2027-01-01'
    assert str(rows[1]['physical_expiry_date']) == '2028-01-01'
    assert str(rows[0]['ca_expiry_snapshot']) == '2026-01-01'
    assert rows[0]['unit_cost'] is None and rows[1]['unit_cost'] == 0
    assert s['c'].execute('SELECT epi_validity_date FROM epis WHERE id=?', (s['epis'][0],)).fetchone()[0] == '2040-01-01'


def test_legacy_unknown_information_is_not_inherited_from_catalog(stock):
    from core.schema import ensure_epi_operational_tables

    identifier = stock['item']()
    ensure_epi_operational_tables(stock['c'])
    row = stock['c'].execute('SELECT * FROM epi_stock_items WHERE id=?', (identifier,)).fetchone()
    assert row['manufacture_date'] == ''
    assert row['physical_manufacture_date'] is None and row['physical_expiry_date'] is None
    assert row['lot_id'] is None and row['unit_cost'] is None and row['expiry_source'] == 'unknown'


@pytest.mark.parametrize('overrides', [
    {'physical_expiry_date': None, 'expiry_source': 'unknown', 'expiry_evidence': None},
    {'manufacture_date': None},
])
def test_optional_unknown_lot_fields_are_preserved(stock, overrides):
    assert stock['lot'](**overrides) > 0


@pytest.mark.parametrize('overrides', [
    {'physical_expiry_date': '2027-01-01', 'expiry_source': 'unknown'},
    {'expiry_evidence': None}, {'expiry_evidence': '  '}, {'expiry_source': 'invented'},
    {'physical_expiry_date': '2020-01-01'}, {'unit_cost': '-0.01'}, {'unit_cost': 'NaN'}, {'received_quantity': 0},
])
def test_invalid_lot_information_is_rejected_by_database(stock, overrides):
    rejected(stock['c'], lambda: stock['lot'](**overrides), ('23514',))


@pytest.mark.parametrize('field,other', [('epi_id', 'epis'), ('receipt_unit_id', 'units'),
                                       ('received_by_user_id', 'actors')])
def test_lot_cannot_link_another_company(stock, field, other):
    rejected(stock['c'], lambda: stock['lot'](**{field: stock[other][1]}))


def test_item_cannot_link_a_foreign_lot_or_unit(stock):
    foreign_lot = stock['lot'](company_id=stock['companies'][1], epi_id=stock['epis'][1],
                              receipt_unit_id=stock['units'][1], received_by_user_id=stock['actors'][1])
    rejected(stock['c'], lambda: stock['item'](lot_id=foreign_lot), ('23503',))
    rejected(stock['c'], lambda: stock['item'](unit_id=stock['units'][1]), ('23503',))


def test_item_blocking_actor_cannot_cross_company(stock):
    rejected(stock['c'], lambda: stock['item'](blocked_by_user_id=stock['actors'][1]), ('23514',))
    identifier = stock['item'](blocked_by_user_id=stock['actors'][0])
    assert stock['c'].execute('SELECT blocked_by_user_id FROM epi_stock_items WHERE id=?',
                             (identifier,)).fetchone()[0] == stock['actors'][0]


def test_item_actor_scope_is_checked_on_company_change(stock):
    identifier = stock['item'](blocked_by_user_id=stock['actors'][0])
    rejected(stock['c'], lambda: stock['c'].execute(
        'UPDATE epi_stock_items SET company_id=?,unit_id=?,epi_id=? WHERE id=?',
        (stock['companies'][1], stock['units'][1], stock['epis'][1], identifier)), ('23514',))


def test_historical_blocking_actor_is_preserved_after_actor_moves_company(stock):
    identifier = stock['item'](blocked_by_user_id=stock['actors'][0])
    stock['c'].execute('UPDATE users SET company_id=? WHERE id=?',
                       (stock['companies'][1], stock['actors'][0]))
    stock['c'].execute('UPDATE epi_stock_items SET row_version=row_version+1 WHERE id=?', (identifier,))
    assert stock['c'].execute('SELECT blocked_by_user_id FROM epi_stock_items WHERE id=?',
                             (identifier,)).fetchone()[0] == stock['actors'][0]


def test_physical_item_date_requires_evidence_and_cannot_precede_manufacture(stock):
    rejected(stock['c'], lambda: stock['item'](physical_expiry_date='2027-01-01', expiry_source='label'), ('23514',))
    rejected(stock['c'], lambda: stock['item'](physical_manufacture_date='2028-01-01',
             physical_expiry_date='2027-01-01', expiry_source='label', expiry_evidence='Label'), ('23514',))


def test_operational_state_is_not_a_visual_validity_override(stock):
    rejected(stock['c'], lambda: stock['item'](status='valid'), ('23514',))
    rejected(stock['c'], lambda: stock['item'](status='unknown_status'), ('23514',))
    assert stock['item'](status='quarantine') > 0


def test_new_negative_aggregate_balance_is_rejected(stock):
    rejected(stock['c'], lambda: stock['c'].execute(
        'INSERT INTO unit_epi_stock(company_id,unit_id,epi_id,quantity,updated_at) VALUES (?,?,?,?,?)',
        (stock['companies'][0], stock['units'][0], stock['epis'][0], -1, stock['now'])), ('23514',))


def test_aggregate_balance_cannot_reference_another_company(stock):
    for unit, epi in [(stock['units'][1], stock['epis'][0]), (stock['units'][0], stock['epis'][1])]:
        rejected(stock['c'], lambda: stock['c'].execute(
            'INSERT INTO unit_epi_stock(company_id,unit_id,epi_id,quantity,updated_at) VALUES (?,?,?,?,?)',
            (stock['companies'][0], unit, epi, 1, stock['now'])), ('23503',))


def test_history_is_immutable_and_retained_after_disposition(stock):
    identifier = stock['item']()
    event = stock['event'](identifier)
    stock['c'].execute("UPDATE epi_stock_items SET status='discarded' WHERE id=?", (identifier,))
    assert stock['c'].execute('SELECT quantity FROM epi_stock_events WHERE id=?', (event,)).fetchone()[0] == 1
    rejected(stock['c'], lambda: stock['c'].execute("UPDATE epi_stock_events SET justification='changed' WHERE id=?", (event,)), ('23514',))
    rejected(stock['c'], lambda: stock['c'].execute('DELETE FROM epi_stock_events WHERE id=?', (event,)), ('23514',))
    rejected(stock['c'], lambda: stock['c'].execute('DELETE FROM epi_stock_items WHERE id=?', (identifier,)), ('23503',))


def test_event_trace_cannot_cross_company_or_have_zero_quantity(stock):
    identifier = stock['item']()
    rejected(stock['c'], lambda: stock['event'](identifier, quantity=0), ('23514',))
    rejected(stock['c'], lambda: stock['event'](identifier, actor_user_id=stock['actors'][1]), ('23514',))
    rejected(stock['c'], lambda: stock['event'](identifier, destination_unit_id=stock['units'][1]), ('23503',))


def test_receipt_identity_is_idempotent_without_collapsing_lot_labels(stock):
    stock['lot'](receipt_key='one-receipt')
    rejected(stock['c'], lambda: stock['lot'](receipt_key='one-receipt'), ('23505',))
    assert stock['lot'](receipt_key='another-receipt') > 0


def test_alert_configuration_is_per_company_and_nonnegative(stock):
    for company, actor, days in zip(stock['companies'], stock['actors'], [15, 60]):
        stock['c'].execute('INSERT INTO company_stock_validity_config(company_id,warning_days,updated_by_user_id) VALUES (?,?,?)',
                           (company, days, actor))
    assert [r[0] for r in stock['c'].execute('SELECT warning_days FROM company_stock_validity_config WHERE company_id IN (?,?) ORDER BY company_id', tuple(stock['companies'])).fetchall()] == [15, 60]
    rejected(stock['c'], lambda: stock['c'].execute('UPDATE company_stock_validity_config SET warning_days=-1 WHERE company_id=?', (stock['companies'][0],)), ('23514',))


def test_decisions_require_a_justification_and_a_recorded_decider(stock):
    identifier = stock['item']()
    values = (stock['companies'][0], stock['units'][0], stock['epis'][0], identifier,
              'discard', 'damage', 'Damage confirmed in inspection', stock['actors'][0])
    sql = 'INSERT INTO epi_stock_decisions(company_id,unit_id,epi_id,stock_item_id,action,reason_code,justification,requested_by_user_id) VALUES (?,?,?,?,?,?,?,?)'
    decision = stock['c'].execute(sql, values).lastrowid
    rejected(stock['c'], lambda: stock['c'].execute(
        "UPDATE epi_stock_decisions SET status='approved' WHERE id=?", (decision,)), ('23514',))
    rejected(stock['c'], lambda: stock['c'].execute(
        'UPDATE epi_stock_decisions SET justification=? WHERE id=?', (' ', decision)), ('23514',))
    rejected(stock['c'], lambda: stock['c'].execute(
        "UPDATE epi_stock_decisions SET status='approved', decided_by_user_id=?, decided_at=CURRENT_TIMESTAMP WHERE id=?",
        (stock['actors'][0], decision)), ('23514',))
    rejected(stock['c'], lambda: stock['c'].execute(
        "UPDATE epi_stock_decisions SET status='approved', decided_by_user_id=?, decided_at=CURRENT_TIMESTAMP, decision_justification='Approved' WHERE id=?",
        (stock['actors'][1], decision)), ('23514',))


def test_migration_is_repeatable_and_preserves_existing_data(stock):
    identifier = stock['item']()
    event = stock['event'](identifier)
    sql = (Path(__file__).resolve().parents[1] / 'supabase/migrations/20261012000000_stock_lifecycle_model.sql').read_text()
    stock['c'].execute(sql)
    assert stock['c'].execute('SELECT id FROM epi_stock_events WHERE id=?', (event,)).fetchone()[0] == event
    assert stock['c'].execute('SELECT physical_expiry_date FROM epi_stock_items WHERE id=?', (identifier,)).fetchone()[0] is None


@pytest.mark.parametrize('role', ['anon', 'authenticated'])
def test_direct_api_roles_cannot_read_new_stock_tables(stock, role):
    stock['lot']()
    stock['c'].execute('GRANT SELECT ON epi_stock_lots,epi_stock_events,epi_stock_decisions,company_stock_validity_config TO anon,authenticated')
    stock['c'].execute('SAVEPOINT direct_api_role')
    try:
        stock['c'].execute('SET LOCAL ROLE ' + role)
        assert stock['c'].execute('SELECT id FROM epi_stock_lots').fetchall() == []
    finally:
        stock['c'].execute('ROLLBACK TO SAVEPOINT direct_api_role')
        stock['c'].execute('RELEASE SAVEPOINT direct_api_role')
