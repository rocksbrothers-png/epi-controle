"""Independent Phase 3 contract: real PostgreSQL, no transaction mocks.

Requires an explicitly isolated PostgreSQL DATABASE_URL, as the journey suite.
The deliberate initial RED is absence of durable queue/worker implementation.
"""
import importlib
import os
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests_postgres.test_migration_p0_postgres import ctx as ctx  # noqa: PLC0414
from tests_postgres.test_migration_p0_postgres import scalar
from tests_postgres.test_migration_p0_postgres import schema as schema  # noqa: PLC0414


@pytest.fixture
def queue(ctx, monkeypatch):
    from cryptography.fernet import Fernet

    from core.security import hash_password
    from modules.settings.service import save_module_visibility
    monkeypatch.setenv('MIGRATION_ASYNC_ENABLED', '1')
    monkeypatch.setenv('MIGRATION_INPUT_KEY', Fernet.generate_key().decode())
    monkeypatch.setenv('MIGRATION_PRODUCT', 'corporate' if 'corporate' in os.getcwd() else 'saas')
    api = importlib.import_module('modules.data_migration.async_jobs')
    c = ctx['conn']
    api.install_schema(c)
    uid = scalar(c, 'INSERT INTO users(username,password,full_name,role,company_id,active) '
                 'VALUES(%s,%s,%s,%s,%s,1) RETURNING id',
                 ('phase3-' + uuid.uuid4().hex, hash_password('Synthetic@12345'),
                  'Synthetic async audit', 'general_admin', ctx['company_id']))
    ctx['actor'].update(id=uid, role='general_admin')
    save_module_visibility(c, ctx['company_id'], 'general_admin', {'migracao': True})
    c.commit()
    ctx['api'] = api
    ctx['raw'] = ('name,unit_type,city\nAsync ' + uuid.uuid4().hex + ',base,Macaé\n').encode()
    ctx['submitted'] = []
    yield ctx
    c.rollback()
    c.execute('UPDATE users SET active=1 WHERE id=%s', (uid,))
    c.commit()
    for job_id in ctx['submitted']:
        try:
            api.request_cancel(c, job_id, ctx['actor'])
        except (ValueError, PermissionError, LookupError):
            c.rollback()


def submit(q, **overrides):
    from modules.data_migration.service import run_migration
    args = {'entity': 'unidades', 'source_kind': 'csv', 'raw': q['raw'],
            'mapping': {'name': 'name', 'unit_type': 'unit_type', 'city': 'city'},
            'strategy': 'insert_only', 'request_key': uuid.uuid4().hex,
            'source_name': 'synthetic-async.csv'}
    args.update(overrides)
    preview = run_migration(q['conn'], company_id=q['company_id'], actor=q['actor'],
                            entity=args['entity'], source_kind=args['source_kind'],
                            raw=args['raw'], mapping=args['mapping'], strategy='dry_run',
                            preview_strategy=args['strategy'])
    args['preview_token'] = preview['preview']['preview_token']
    job = q['api'].submit(q['conn'], actor=q['actor'], **args)
    q['submitted'].append(job['id'])
    return job


def test_submit_is_durable_without_business_writes(queue):
    from core.database import get_connection
    job = submit(queue)
    assert job['status'] == 'queued'
    observer = get_connection()
    try:
        persisted = queue['api'].get(observer, job['id'], queue['actor'])
        assert persisted['id'] == job['id'] and persisted['status'] == 'queued'
        assert persisted['processed_rows'] == 0
        assert scalar(observer, 'SELECT count(*) FROM units WHERE company_id=%s',
                      (queue['company_id'],)) == 0
        assert queue['raw'].decode() not in str(persisted)
    finally:
        observer.close()


def test_duplicate_http_request_creates_one_job(queue):
    request_key = uuid.uuid4().hex
    first = submit(queue, request_key=request_key)
    second = submit(queue, request_key=request_key)
    assert first['id'] == second['id']


def test_duplicate_request_key_cannot_change_file(queue):
    request_key = uuid.uuid4().hex
    submit(queue, request_key=request_key)
    with pytest.raises((ValueError, PermissionError)):
        submit(queue, request_key=request_key, raw=b'name,unit_type,city\nDifferent,base,City\n')


def test_cross_tenant_read_and_cancel_are_denied(queue):
    job = submit(queue)
    actor = dict(queue['actor'], company_id=queue['company_id'] + 999999)
    for action in (queue['api'].get, queue['api'].request_cancel):
        with pytest.raises((ValueError, PermissionError, LookupError)):
            action(queue['conn'], job['id'], actor)
        queue['conn'].rollback()
    assert queue['api'].get(queue['conn'], job['id'], queue['actor'])['status'] == 'queued'


def test_forged_actor_and_revoked_user_cannot_submit(queue):
    real = dict(queue['actor'])
    queue['actor']['id'] = 0
    with pytest.raises((ValueError, PermissionError, LookupError)):
        submit(queue)
    queue['conn'].rollback()
    queue['actor'].update(real)
    queue['conn'].execute('UPDATE users SET active=0 WHERE id=%s', (real['id'],))
    queue['conn'].commit()
    with pytest.raises((ValueError, PermissionError, LookupError)):
        submit(queue)


def test_two_connections_claim_at_most_once(queue):
    from core.database import get_connection
    job = submit(queue)
    def acquire(owner):
        c = get_connection()
        try:
            return queue['api'].claim(c, owner=owner, lease_seconds=30)
        finally:
            c.close()
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(acquire, ['independent-a', 'independent-b']))
    matching = [claim for claim in claims if claim and claim['id'] == job['id']]
    assert len(matching) == 1, claims
    assert matching[0]['owner'] in ('independent-a', 'independent-b')
    assert matching[0]['attempt'] >= 1


def test_queued_cancel_is_durable_idempotent_and_unclaimable(queue):
    job = submit(queue)
    one = queue['api'].request_cancel(queue['conn'], job['id'], queue['actor'])
    two = queue['api'].request_cancel(queue['conn'], job['id'], queue['actor'])
    assert one['status'] == two['status'] == 'cancelled'
    assert queue['api'].get(queue['conn'], job['id'], queue['actor'])['status'] == 'cancelled'
    assert scalar(queue['conn'], 'SELECT count(*) FROM units WHERE company_id=%s',
                  (queue['company_id'],)) == 0


def test_worker_rechecks_revoked_permission(queue):
    from core.database import get_connection
    job = submit(queue)
    queue['conn'].execute('UPDATE users SET active=0 WHERE id=%s', (queue['actor']['id'],))
    queue['conn'].commit()
    claim = queue['api'].claim(queue['conn'], owner='revoked', lease_seconds=30)
    assert claim and claim['id'] == job['id']
    result = queue['api'].execute_claim(job['id'], 'revoked', claim['attempt'],
                                        connection_factory=get_connection)
    assert result['status'] == 'failed'
    assert scalar(queue['conn'], 'SELECT count(*) FROM units WHERE company_id=%s',
                  (queue['company_id'],)) == 0


def test_worker_final_counts_match_independent_database(queue):
    from core.database import get_connection
    job = submit(queue)
    claim = queue['api'].claim(queue['conn'], owner='completion', lease_seconds=30)
    assert claim and claim['id'] == job['id']
    result = queue['api'].execute_claim(job['id'], 'completion', claim['attempt'],
                                        connection_factory=get_connection)
    assert result['status'] == 'completed'
    observer = get_connection()
    try:
        persisted = queue['api'].get(observer, job['id'], queue['actor'])
        assert persisted['status'] == 'completed'
        assert persisted['processed_rows'] == persisted['total_rows'] == 1
        assert persisted['inserted_rows'] == 1
        assert scalar(observer, 'SELECT count(*) FROM units WHERE company_id=%s',
                      (queue['company_id'],)) == 1
        with pytest.raises((ValueError, PermissionError)):
            queue['api'].request_cancel(observer, job['id'], queue['actor'])
    finally:
        observer.close()
