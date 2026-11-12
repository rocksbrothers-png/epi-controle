"""F2-T01..T18: native HTTP/Bearer, production pool and isolated PostgreSQL.

Run with DATABASE_URL pointing ONLY to a disposable validation database.
"""
import base64
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
from test_db_pool_p0_postgres import (
    admin_connection,
    backend_sessions,
    custom_pool,
    get,
    wait_released,
)
from test_db_pool_p0_postgres import (
    server as _server_fixture,
)
from test_employee_ppe_360_f1_summary_postgres import (
    _company,
    _delivery,
    _employee,
    _epi,
    _unit,
    _user,
)
from test_est_v3_5_r3_lot_receipt_http import _fresh

server = _server_fixture

pytestmark = pytest.mark.skipif(not os.environ.get('DATABASE_URL', '').startswith('postgres'),
                                reason='Requires isolated real PostgreSQL')


@pytest.fixture
def w(server):
    with _fresh() as c:
        a, b = _company(c, 'F21 A'), _company(c, 'F21 B')
        u1, u2, ub = _unit(c, a, 'A1'), _unit(c, a, 'A2'), _unit(c, b, 'B1')
        p, q = _employee(c, a, u1, 'P'), _employee(c, b, ub, 'SECRET B')
        base = _employee(c, a, u1, 'Operator')
        product = _epi(c, a, u1, 'Helmet', 'Head')
        pb = _epi(c, b, ub, 'SECRET PRODUCT', 'SECRET CATEGORY')
        users = {r: _user(c, a, r, r, linked=base) for r in
                 ('general_admin', 'registry_admin', 'admin', 'user', 'buyer', 'approver', 'employee')}
        users['master_admin'] = _user(c, None, 'master_admin', 'Master')
        users['b'] = _user(c, b, 'general_admin', 'B admin')
        d1 = _delivery(c, a, u1, p, product)
        d2 = _delivery(c, a, u2, p, product)
        db = _delivery(c, b, ub, q, pb)
        c.commit()
    return dict(a=a, b=b, u1=u1, u2=u2, ub=ub, p=p, q=q, base=base, product=product,
                pb=pb, users=users, d1=d1, d2=d2, db=db)


def req(server, w, role='user', person=None, query=''):
    return get(server, w['users'][role], f"/api/employees/{person or w['p']}/ppe-360/in-use{query}")


def ids(body):
    return [i['delivery_id'] for i in body['data']['items']]


def change(sql, params):
    with _fresh() as c:
        c.execute(sql, params)
        c.commit()


def link(w, status='active'):
    change('INSERT INTO employee_unit_links(company_id,employee_id,unit_id,local_status) VALUES (?,?,?,?)',
           (w['a'], w['p'], w['u1'], status))


def encode(payload):
    return base64.urlsafe_b64encode(json.dumps(payload, separators=(',', ':')).encode()).decode().rstrip('=')


@pytest.mark.parametrize('role', ['general_admin', 'registry_admin'])
def test_F2_T01_company(server, w, role):
    status, _, body = req(server, w, role)
    assert status == 200, body
    assert set(ids(body)) == {w['d1'], w['d2']}
    assert body['data']['scope'] == dict(company_id=w['a'], mode='company',
                                        authorized_unit_ids=None, partial_by_unit=False)


@pytest.mark.parametrize('role', ['user', 'admin'])
def test_F2_T02_unit(server, w, role):
    status, _, body = req(server, w, role)
    assert status == 200 and ids(body) == [w['d1']]
    assert body['data']['scope'] == dict(company_id=w['a'], mode='operational_unit',
                                        authorized_unit_ids=[w['u1']], partial_by_unit=True)
    assert body['page'] == dict(limit=20, next_cursor=None)


@pytest.mark.parametrize('role', ['user', 'admin'])
def test_F2_T03_local_link_never_expands_rows(server, w, role):
    change('UPDATE employees SET unit_id=? WHERE id=?', (w['u2'], w['p']))
    link(w)
    status, _, body = req(server, w, role)
    assert status == 200 and ids(body) == [w['d1']]


@pytest.mark.parametrize('status', ['archived', None])
def test_F2_T04_inactive_link(server, w, status):
    change('UPDATE employees SET unit_id=? WHERE id=?', (w['u2'], w['p']))
    if status:
        link(w, status)
    actual = req(server, w)
    missing = req(server, w, person=999999999999)
    assert actual[0] == 404 and actual[2] == missing[2]


@pytest.mark.parametrize('role', ['admin', 'user'])
def test_F2_T05_missing_and_cross_tenant_actor_unit(server, w, role):
    change('UPDATE users SET linked_employee_id=NULL WHERE id=?', (w['users'][role]['id'],))
    assert req(server, w, role)[0] == 404
    change('UPDATE users SET linked_employee_id=? WHERE id=?', (w['base'], w['users'][role]['id']))
    change('UPDATE employees SET unit_id=? WHERE id IN (?,?)', (w['ub'], w['base'], w['p']))
    assert req(server, w, role)[0] == 403


@pytest.mark.parametrize('role', ['general_admin', 'user'])
def test_F2_T06_tenant_idor(server, w, role):
    change('INSERT INTO employee_unit_links(company_id,employee_id,unit_id,local_status) VALUES (?,?,?,?)',
           (w['a'], w['q'], w['u1'], 'active'))
    foreign = req(server, w, role, w['q'])
    missing = req(server, w, role, 999999999999)
    assert foreign[0] == 404 and foreign[2] == missing[2]
    assert 'SECRET' not in json.dumps(foreign[2])


def test_F2_T07_permissions_before_person_read(server, w, monkeypatch):
    import modules.employees.service as service
    from core import permissions
    calls = []
    original = service.get_employee_by_id
    def spy(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)
    monkeypatch.setattr(service, 'get_employee_by_id', spy)
    for role in ('master_admin', 'buyer', 'approver', 'employee'):
        assert req(server, w, role)[0] == 403
    original_perms = permissions.PERMISSIONS['general_admin']
    from core.roles import CERTIFICATION_READONLY_ROLE
    with _fresh() as c:
        cert = _user(c, w['a'], CERTIFICATION_READONLY_ROLE, 'Certification')
        c.commit()
    assert get(server, cert, f"/api/employees/{w['p']}/ppe-360/in-use")[0] == 403
    for permission in ('employees:view', 'deliveries:view'):
        monkeypatch.setitem(permissions.PERMISSIONS, 'general_admin',
                            original_perms - {permission})
        assert req(server, w, 'general_admin')[0] == 403
    assert calls == []


def test_F2_T08_bearer_identity_and_account_policy(server, w, monkeypatch):
    import core.security as security
    path = f"/api/employees/{w['p']}/ppe-360/in-use"
    for mode in ('off', 'shadow', 'enforce'):
        monkeypatch.setattr(security, 'JWT_ENFORCEMENT_MODE', mode)
        for auth in (None, 'Bearer invalid', 'Bearer a.b.c', 'Basic test',
                     'Bearer ' + security.create_refresh_token(w['users']['user']),
                     'Bearer ' + security._encode_jwt([]),
                     'Bearer ' + security._encode_jwt({'sub': w['users']['user']['id'], 'exp': 'bad'}),
                     'Bearer ' + security._encode_jwt({'sub': w['users']['user']['id'], 'exp': 1, 'type': 'access'})):
            headers = {'Authorization': auth} if auth else {}
            request = Request(server + path + f"?actor_user_id={w['users']['user']['id']}", headers=headers)
            with pytest.raises(HTTPError) as exc:
                urlopen(request)
            assert exc.value.code == 401
            assert json.load(exc.value)['error']['code'] == 'UNAUTHENTICATED'
    assert req(server, w, query=f"?actor_user_id={w['users']['general_admin']['id']}")[0] == 403
    change('UPDATE users SET active=0 WHERE id=?', (w['users']['user']['id'],))
    assert req(server, w)[0] == 403
    change('UPDATE users SET active=1,must_change_password=1 WHERE id=?', (w['users']['user']['id'],))
    status, _, body = req(server, w)
    assert status == 403 and body['error']['code'] == 'PASSWORD_CHANGE_REQUIRED'


def test_F2_T09_official_possession(server, w):
    with _fresh() as c:
        _delivery(c, w['a'], w['u1'], w['p'], w['product'], returned='2026-02-01')
        _delivery(c, w['a'], w['u1'], w['p'], w['product'], reverted='2026-03-01')
        migrated = _delivery(c, w['a'], w['u1'], w['p'], w['product'])
        c.execute("UPDATE deliveries SET origin='legado' WHERE id=?", (migrated,))
        c.commit()
    assert set(ids(req(server, w)[2])) == {w['d1'], migrated}
    # Native PostgreSQL NULL semantics, without altering the installed schema.
    from core.repository import require_actor
    from modules.employee_ppe_360.in_use import fetch_in_use, resolve_scope
    with _fresh() as c:
        c.execute('CREATE TEMP TABLE deliveries (id bigint,company_id bigint,employee_id bigint,epi_id bigint,'
                  'unit_id bigint,quantity integer,delivery_date text,next_replacement_date text,'
                  'returned_date text,migration_reverted_at text) ON COMMIT DROP')
        c.execute('INSERT INTO deliveries(id,company_id,employee_id,epi_id,unit_id) VALUES (1,?,?,?,?)',
                  (w['a'], w['p'], w['product'], w['u1']))
        actor = require_actor(c, w['users']['user']['id'])
        data, cursor = fetch_in_use(c, actor, {'id':w['p']}, resolve_scope(c, actor), {'limit':20,'cursor':None})
        assert data['items'][0]['quantity'] == 1 and data['items'][0]['delivery_date'] is None
        assert cursor is None


def test_F2_T10_limits_and_sql_bound(server, w, monkeypatch):
    from core.database import PostgresConnectionWrapper
    with _fresh() as c:
        for _ in range(205):
            _delivery(c, w['a'], w['u1'], w['p'], w['product'])
            _delivery(c, w['a'], w['u2'], w['p'], w['product'])
        c.commit()
    captured, all_queries, query_counts = [], [], []
    original = PostgresConnectionWrapper.execute
    def execute(self, sql, params=None):
        all_queries.append(sql)
        if sql.startswith('WITH normalized'):
            captured.append((sql, params))
        return original(self, sql, params)
    monkeypatch.setattr(PostgresConnectionWrapper, 'execute', execute)
    for query, size in [('', 20), ('?limit=1', 1), ('?limit=20', 20), ('?limit=100', 100)]:
        start_count = len(all_queries)
        status, _, body = req(server, w, query=query)
        query_counts.append(len(all_queries) - start_count)
        assert status == 200 and len(ids(body)) == size
        assert captured[-1][1][-3] == size + 1
        assert 'd.unit_id = ?' in captured[-1][0] and 'LIMIT ?' in captured[-1][0]
    assert len(captured) == 4 and query_counts[-1] <= query_counts[0]
    for value in ('0', '101', '-1', '1.5', 'bad', '20&limit=20'):
        status, _, body = req(server, w, query='?limit=' + value)
        assert status == 400 and body['error']['code'] == 'INVALID_PAGINATION'
    uid = w['users']['user']['id']
    for query in ('?company_id=1', '?unit_id=1', '?unknown=x', f'?actor_user_id={uid}&actor_user_id={uid}'):
        assert req(server, w, query=query)[0] == 400
    for person in ('abc', '0', '-1', '1234567890123', '²'):
        from urllib.parse import quote
        assert req(server, w, person=quote(person))[0] == 400


def pages(server, w, role='user'):
    result, cursor = [], None
    for _ in range(100):
        status, _, body = req(server, w, role, query='?limit=2' + ('&cursor=' + cursor if cursor else ''))
        assert status == 200, body
        result.extend(body['data']['items'])
        cursor = body['page']['next_cursor']
        if not cursor:
            return result
    raise AssertionError('cursor did not terminate')


def test_F2_T11_stable_keyset(server, w):
    expected = [w['d1']]
    with _fresh() as c:
        expected.extend(_delivery(c, w['a'], w['u1'], w['p'], w['product']) for _ in range(9))
        c.commit()
    assert [x['delivery_id'] for x in pages(server, w)] == sorted(expected, reverse=True)


def test_F2_T12_legacy_calendar(server, w):
    dates = ['2024-02-29', '2023-02-29', '2026-02-30', '0000-01-01', '', '   ',
             '03/04/2024', '2026-01-01T00:00:00', ' 2026-02-01 ', '\t2026-02-02\n', '9999-12-31']
    expected = [(w['d1'], '2026-01-10')]
    from modules.employee_ppe_360.in_use import SENTINEL, valid_date
    with _fresh() as c:
        for raw in dates:
            did = _delivery(c, w['a'], w['u1'], w['p'], w['product'], next_date=raw)
            c.execute('UPDATE deliveries SET delivery_date=? WHERE id=?', (raw, did))
            expected.append((did, valid_date(raw)))
        c.commit()
    actual = pages(server, w)
    expected.sort(key=lambda x: (x[1] or SENTINEL, x[0]), reverse=True)
    assert [(x['delivery_id'], x['delivery_date']) for x in actual] == expected
    for x in actual:
        if x['delivery_id'] != w['d1']:
            assert x['next_replacement_date'] == x['delivery_date']


def test_F2_T13_invalid_and_forged_cursor(server, w):
    invalid = ['!', 'a' * 201, encode({'s': '2026-02-30', 'i': 1}),
               encode({'s': '2026-01-01', 'i': True}), encode({'s': '2026-01-01', 'i': 2**80}),
               encode({'s': '2026-01-01', 'i': 1, 'tenant': w['b']}), encode([])]
    for cursor in invalid:
        status, _, body = req(server, w, query='?cursor=' + cursor)
        assert status == 400 and body['error']['code'] == 'INVALID_PAGINATION'
    status, _, body = req(server, w, query='?cursor=' + encode({'s': '9999-12-31', 'i': w['db']}))
    assert status == 200 and ids(body) == [w['d1']]


def test_F2_T14_reauthorize_every_page(server, w):
    link(w)
    cursor = encode({'s': '9999-12-31', 'i': w['db']})
    today = date.today()  # noqa: DTZ011 - match official operational-unit clock
    change("INSERT INTO employee_unit_movements(employee_id,company_id,source_unit_id,target_unit_id,"
           "movement_type,start_date,end_date,actor_user_id,actor_name,created_at) VALUES (?,?,?,?,'temporary',?,?,?,?,?)",
           (w['base'], w['a'], w['u1'], w['u2'], (today - timedelta(days=1)).isoformat(),
            (today + timedelta(days=1)).isoformat(), w['users']['general_admin']['id'], 'seed', today.isoformat()))
    change('UPDATE employees SET unit_id=? WHERE id=?', (w['u2'], w['p']))
    assert ids(req(server, w, query='?cursor=' + cursor)[2]) == [w['d2']]
    change('UPDATE employees SET unit_id=? WHERE id=?', (w['u1'], w['p']))
    assert req(server, w, query='?cursor=' + cursor)[0] == 404
    change('UPDATE users SET role=? WHERE id=?', ('buyer', w['users']['user']['id']))
    assert req(server, w, query='?cursor=' + cursor)[0] == 403
    assert ids(req(server, w, 'b', w['q'], '?cursor=' + cursor)[2]) == [w['db']]


def test_F2_T15_empty_archived_deleted(server, w):
    change('UPDATE deliveries SET returned_date=? WHERE id=?', ('2026-01-11', w['d1']))
    status, _, body = req(server, w)
    assert status == 200 and ids(body) == [] and body['page']['next_cursor'] is None
    assert body['data']['scope']['partial_by_unit'] is True
    change("UPDATE employees SET status='archived',archived_at='2026-01-11' WHERE id=?", (w['p'],))
    assert req(server, w)[0] == 200
    change("UPDATE employees SET deleted_at='2026-01-12' WHERE id=?", (w['p'],))
    assert req(server, w)[0] == 404


def test_F2_T16_minimal_projection_and_cross_reference(server, w):
    change('UPDATE deliveries SET epi_id=? WHERE id=?', (w['pb'], w['d1']))
    status, _, body = req(server, w)
    assert status == 200
    item = body['data']['items'][0]
    assert item['product'] is None
    assert set(item) == {'delivery_id', 'product', 'quantity', 'delivery_date', 'next_replacement_date', 'unit'}
    assert set(item['unit']) == {'id', 'name'}
    assert set(body) == {'ok', 'data', 'page'}
    assert set(body['data']) == {'employee_id', 'scope', 'items', 'generated_at'}
    assert 'SECRET' not in json.dumps(body) and 'signature' not in json.dumps(body)
    change('UPDATE deliveries SET unit_id=? WHERE id=?', (w['ub'], w['d2']))
    _, _, broad = req(server, w, 'general_admin')
    assert next(i for i in broad['data']['items'] if i['delivery_id'] == w['d2'])['unit'] is None


def test_F2_T17_persistent_audit_fail_closed(server, w, monkeypatch):
    assert req(server, w)[0] == 200
    assert req(server, w, person=w['q'])[0] == 404
    with _fresh() as c:
        rows = c.execute('SELECT company_id,action_type,details_json FROM company_audit_logs '
                         'WHERE actor_user_id=? ORDER BY id', (w['users']['user']['id'],)).fetchall()
    assert [r['action_type'] for r in rows] == ['ppe360_in_use_view', 'ppe360_in_use_denied']
    assert all(r['company_id'] == w['a'] for r in rows)
    details = json.loads(rows[0]['details_json'])[0]
    assert details['authorized_unit_ids'] == [w['u1']] and details['returned_count'] == 1
    assert 'SECRET' not in str(rows) and 'signature' not in str(rows)
    import core.audit as audit
    original_audit = audit.register_company_audit
    def broken(*args, **kwargs):
        original_audit(*args, **kwargs)
        raise RuntimeError('SECRET DATABASE FAILURE')
    monkeypatch.setattr(audit, 'register_company_audit', broken)
    for person in (w['p'], w['q']):
        status, _, body = req(server, w, person=person)
        assert status == 500 and body['error']['code'] == 'AUDIT_UNAVAILABLE'
        assert 'SECRET' not in json.dumps(body)
    with _fresh() as c:
        assert c.execute('SELECT count(*) AS n FROM company_audit_logs WHERE actor_user_id=?',
                         (w['users']['user']['id'],)).fetchone()['n'] == 2


def test_F2_T18_concurrency_saturation_regression_and_plan(server, w, monkeypatch):
    summary_path = f"/api/employees/{w['p']}/ppe-360/summary"
    before = get(server, w['users']['user'], summary_path)[2]['data']
    with custom_pool(maxconn=3, max_idle=3) as pool:
        start = time.monotonic()
        def run(i):
            if i % 2:
                status, _, body = req(server, w, 'b', w['q'])
                expected = [w['db']]
            else:
                status, _, body = req(server, w)
                expected = [w['d1']]
            assert status == 200 and ids(body) == expected
        with ThreadPoolExecutor(max_workers=12) as executor:
            list(executor.map(run, range(48)))
        stats = wait_released(pool)
        assert stats['in_use'] == 0 and stats['peak_in_use'] <= 3
        assert backend_sessions().get('idle in transaction', 0) == 0
        print('F21_CONCURRENCY', {'requests': 48, 'seconds': time.monotonic()-start, 'pool': stats})
    with custom_pool(maxconn=1, max_idle=1, acquire_timeout=0) as pool:
        held = pool.getconn()
        try:
            status, headers, body = req(server, w)
            assert status == 503 and body['error']['code'] == 'DB_POOL_SATURATED'
            assert headers['Retry-After'] == '1'
        finally:
            pool.putconn(held)
        assert req(server, w)[0] == 200
        assert wait_released(pool)['in_use'] == 0
    after = get(server, w['users']['user'], summary_path)[2]['data']
    before.pop('generated_at'); after.pop('generated_at')
    assert before == after
    first = req(server, w, 'general_admin', query='?limit=1')[2]
    cursor = first['page']['next_cursor']
    assert cursor
    change('UPDATE deliveries SET returned_date=? WHERE id=?', ('2026-01-11', w['d1']))
    assert ids(req(server, w, 'general_admin', query='?cursor=' + cursor)[2]) == []
    change('UPDATE deliveries SET returned_date=? WHERE id=?', ('', w['d1']))
    from core.repository import require_actor
    with _fresh() as c:
        c.execute("INSERT INTO deliveries(company_id,employee_id,epi_id,unit_id,quantity,quantity_label,"
                  "sector,role_name,delivery_date,next_replacement_date,signature_name) "
                  "SELECT ?,?,?,CASE WHEN g % 2 = 0 THEN ? ELSE ? END,1,'un','S','R',"
                  "'2026-01-10','','' FROM generate_series(1,10000) g".replace('%', '%%'),
                  (w['a'], w['p'], w['product'], w['u1'], w['u2']))
        c.execute('ANALYZE deliveries')
        c.commit()
    from modules.employee_ppe_360.in_use import item_query, resolve_scope
    with _fresh() as c:
        actor = require_actor(c, w['users']['user']['id'])
        sql, params = item_query(c, actor, {'id': w['p']}, resolve_scope(c, actor), {'limit': 20, 'cursor': None})
        plan = c.execute('EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) ' + sql, params).fetchone()
        print('F21_PLAN_SYNTHETIC_10000', json.dumps(dict(plan), default=str))
    with admin_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM pg_locks WHERE locktype='advisory' AND pid IN "
                    "(SELECT pid FROM pg_stat_activity WHERE datname=current_database())")
        assert cur.fetchone()[0] == 0
    import modules.employee_ppe_360.in_use_routes as route
    def broken(connection, *args):
        connection.execute('SELECT 1 / 0')  # native PostgreSQL transaction enters INERROR
    with custom_pool(maxconn=1, max_idle=1) as pool:
        monkeypatch.setattr(route, 'fetch_in_use', broken)
        status, _, body = req(server, w)
        assert status == 500 and body['error']['code'] == 'INTERNAL_ERROR'
        assert wait_released(pool)['in_use'] == 0
        assert backend_sessions().get('idle in transaction', 0) == 0

    def terminated(connection, *args):
        connection.execute('SELECT pg_terminate_backend(pg_backend_pid())')
    with custom_pool(maxconn=1, max_idle=1) as pool:
        monkeypatch.setattr(route, 'fetch_in_use', terminated)
        status, _, body = req(server, w)
        assert status == 500 and body['error']['code'] == 'INTERNAL_ERROR'
        assert wait_released(pool)['in_use'] == 0
        assert pool.status()['discarded_total'] >= 1
