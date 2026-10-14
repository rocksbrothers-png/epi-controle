"""Real socket/JWT/PostgreSQL regression for pending-regularization scope."""
import json
import os
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from core.security import create_jwt_token
from test_est_v3_5_r2_rbac_http import conn, env, _enforce_jwt  # noqa: F401

pytestmark = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL', '').startswith('postgres'),
    reason='Requires disposable PostgreSQL.',
)


@pytest.fixture(scope='module')
def http_server(conn):
    import app
    app._set_bootstrap_state(ready=True, completed_at=datetime.now(timezone.utc).isoformat(),
                             error_code='', error_kind='', error_message='')
    server = ThreadingHTTPServer(('127.0.0.1', 0), app.EpiHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield 'http://127.0.0.1:' + str(server.server_port)
    server.shutdown()
    thread.join(timeout=10)
    server.server_close()


def call(base, actor, query='', payload=None):
    path = '/api/stock/pending-regularization' if payload is None else '/api/stock/items/regularize-validity'
    headers = {'Authorization': 'Bearer ' + create_jwt_token(actor)}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers['Content-Type'] = 'application/json'
    request = Request(base + path + query, data=data, headers=headers)
    try:
        response = urlopen(request, timeout=10)
    except HTTPError as exc:
        response = exc
    with response:
        return response.status, json.loads(response.read())


@pytest.mark.parametrize('role', ['admin', 'user'])
def test_authorized_scope_discards_client_unit_and_company(env, http_server, role):
    own, _ = env['mkpiece'](env['unit_a'])
    foreign, _ = env['mkpiece'](env['unit_b'])
    actor = env['mkuser'](role, env['unit_a'])
    status, body = call(http_server, actor, '?unit_id=' + str(env['unit_b']) + '&company_id=' + str(env['other_company']))
    assert status == 200
    assert body['count'] == 1
    assert [item['id'] for item in body['items']] == [own]
    assert foreign not in [item['id'] for item in body['items']]
    assert body['items'][0]['unit_id'] == env['unit_a']


def test_general_admin_read_only_and_selected_unit(env, http_server):
    own, qr = env['mkpiece'](env['unit_a'])
    other, _ = env['mkpiece'](env['unit_b'])
    actor = env['mkuser']('general_admin')
    status, body = call(http_server, actor)
    assert status == 200 and {item['id'] for item in body['items']} == {own, other}
    status, body = call(http_server, actor, '?unit_id=' + str(env['unit_a']))
    assert status == 200 and [item['id'] for item in body['items']] == [own]
    status, _ = call(http_server, actor, payload={
        'actor_user_id': actor['id'], 'qr_code': qr, 'physical_expiry_date': '2099-01-01',
        'evidence': 'Manufacturer evidence', 'justification': 'Capture physical date',
        'unit_id': env['unit_a'], 'company_id': env['company']})
    assert status == 403
    assert env['c'].execute('SELECT physical_expiry_date FROM epi_stock_items WHERE id=?', (own,)).fetchone()['physical_expiry_date'] is None


@pytest.mark.parametrize('role', ['admin', 'user'])
def test_missing_operational_unit_fails_closed(env, http_server, role):
    env['mkpiece'](env['unit_a'])
    status, _ = call(http_server, env['mkuser'](role), '?unit_id=' + str(env['unit_a']))
    assert status == 403


def test_foreign_company_and_unit_never_leak(env, http_server):
    own, _ = env['mkpiece'](env['unit_a'])
    foreign_unit = env['c'].execute('INSERT INTO units(company_id,name,unit_type,city) VALUES (?,?,?,?)',
                                   (env['other_company'], 'Foreign', 'base', 'T')).lastrowid
    env['c'].commit()
    foreign_actor = env['mkuser']('general_admin', company_id=env['other_company'])
    status, body = call(http_server, foreign_actor, '?company_id=' + str(env['company']))
    assert status == 200 and body == {'items': [], 'count': 0}
    status, _ = call(http_server, env['mkuser']('general_admin'), '?unit_id=' + str(foreign_unit))
    assert status == 400
    assert own > 0


def test_empty_authorized_scope(env, http_server):
    status, body = call(http_server, env['mkuser']('admin', env['unit_a']))
    assert status == 200 and body == {'items': [], 'count': 0}


def test_no_stock_permission_rejected(env, http_server):
    env['mkpiece'](env['unit_a'])
    status, _ = call(http_server, env['mkuser']('employee', env['unit_a']))
    assert status == 403
