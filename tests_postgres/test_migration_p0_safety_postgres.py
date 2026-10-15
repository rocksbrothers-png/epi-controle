"""Additional adversarial PostgreSQL safety cases for migration rollback."""
import uuid

import pytest

from tests_postgres.test_migration_p0_postgres import (
    ctx as ctx, schema as schema, run, history, scalar, background_call, wait_lock,
    rejection_or_conflict, pytestmark as pytestmark,
)


def unit_id(ctx, name='P0 unit'):
    return scalar(ctx['conn'], 'SELECT id FROM units WHERE company_id=%s AND name=%s',
                  (ctx['company_id'], name))


def revert(ctx, job):
    from modules.data_migration.service import revert_job
    return revert_job(ctx['conn'], job['job_id'], ctx['company_id'], ctx['actor'])


def assert_job_unchanged(ctx, job):
    from modules.data_migration.service import get_job
    row = get_job(ctx['conn'], job['job_id'], ctx['company_id'])
    assert row['status'] == 'completed', row
    assert not row.get('reverted_at'), row
    assert scalar(ctx['conn'], 'SELECT 1') == 1


def test_aba_edit_is_conflict_even_when_visible_values_are_restored(ctx):
    job = run(ctx)
    target = unit_id(ctx)
    ctx['conn'].execute("UPDATE units SET notes='temporary later edit' WHERE id=%s", (target,))
    ctx['conn'].commit()
    ctx['conn'].execute("UPDATE units SET notes='import' WHERE id=%s", (target,))
    ctx['conn'].commit()
    rejection_or_conflict(lambda: revert(ctx, job))
    assert scalar(ctx['conn'], 'SELECT notes FROM units WHERE id=%s', (target,)) == 'import'
    assert_job_unchanged(ctx, job)


@pytest.mark.parametrize('delete_action', ['CASCADE', 'SET NULL'])
def test_later_reference_preserves_parent_and_child_for_all_fk_actions(ctx, delete_action):
    job = run(ctx)
    target = unit_id(ctx)
    name = 'p0_fk_' + uuid.uuid4().hex
    conn = ctx['conn']
    try:
        conn.execute(f'CREATE SCHEMA {name}')
        conn.execute(f'CREATE TABLE {name}.child (id integer PRIMARY KEY, '
                     f'unit_id integer REFERENCES public.units(id) ON DELETE {delete_action})')
        conn.execute(f'INSERT INTO {name}.child VALUES (1,%s)', (target,))
        conn.commit()
        rejection_or_conflict(lambda: revert(ctx, job))
        assert scalar(conn, 'SELECT id FROM units WHERE id=%s', (target,)) == target
        assert scalar(conn, f'SELECT unit_id FROM {name}.child WHERE id=1') == target
        assert_job_unchanged(ctx, job)
    finally:
        conn.rollback()
        conn.execute(f'DROP SCHEMA IF EXISTS {name} CASCADE')
        conn.commit()


def test_two_updates_of_same_target_restore_original_without_false_conflict(ctx):
    from modules.data_migration.service import revert_job
    run(ctx)
    target = unit_id(ctx)
    job = run(ctx, rows=[{'name':'P0 unit','unit_type':'base','city':'Macaé','notes':'first update'},
                         {'name':'P0 unit','unit_type':'base','city':'Macaé','notes':'second update'}],
              strategy='upsert')
    assert job['totals']['updated'] == 2, job
    result = revert_job(ctx['conn'], job['job_id'], ctx['company_id'], ctx['actor'])
    assert result.get('restored') == 2, result
    assert scalar(ctx['conn'], 'SELECT notes FROM units WHERE id=%s', (target,)) == 'import'


@pytest.mark.parametrize('snapshot', ['{}', '{malformed', '{"name":"legacy payload"}',
                                      '{"__rollback_v1__":{"row":{}}}'])
def test_legacy_or_invalid_snapshot_refuses_automatic_rollback(ctx, snapshot):
    job = run(ctx)
    target = unit_id(ctx)
    ctx['conn'].execute('UPDATE migration_job_records SET after_json=%s WHERE job_id=%s AND company_id=%s',
                        (snapshot, job['job_id'], ctx['company_id']))
    ctx['conn'].commit()
    rejection_or_conflict(lambda: revert(ctx, job))
    assert scalar(ctx['conn'], 'SELECT id FROM units WHERE id=%s', (target,)) == target
    assert_job_unchanged(ctx, job)


def test_one_conflict_keeps_entire_job_and_persists_conflict_evidence(ctx):
    job = run(ctx, rows=[{'name':'P0 unit','unit_type':'base','city':'Macaé','notes':'import'},
                         {'name':'Untouched unit','unit_type':'base','city':'Macaé','notes':'import'}])
    target = unit_id(ctx)
    ctx['conn'].execute("UPDATE units SET notes='private manual note' WHERE id=%s", (target,))
    ctx['conn'].commit()
    rejection_or_conflict(lambda: revert(ctx, job))
    assert scalar(ctx['conn'], 'SELECT count(*) FROM units WHERE company_id=%s', (ctx['company_id'],)) == 2
    assert scalar(ctx['conn'], 'SELECT notes FROM units WHERE id=%s', (target,)) == 'private manual note'
    assert_job_unchanged(ctx, job)
    from core.database import get_connection
    observer = get_connection()
    try:
        evidence = observer.execute(
            "SELECT error_message FROM migration_job_records WHERE job_id=%s AND company_id=%s "
            "AND action='rollback_conflict'", (job['job_id'], ctx['company_id'])).fetchall()
        assert evidence, 'Rejected rollback must durably record a conflict'
        from epi_backend.db import row_to_dict
        messages = [str(row_to_dict(r).get('error_message') or '') for r in evidence]
        assert all(messages), messages
        assert all('private manual note' not in message for message in messages), messages
    finally:
        observer.close()


@pytest.mark.parametrize('operation', ['homologate', 'revert'])
def test_audit_failure_rolls_back_state_and_target_mutation(ctx, operation):
    from modules.data_migration.service import homologate_job, revert_job, get_job
    job = history(ctx)
    before = scalar(ctx['conn'], 'SELECT count(*) FROM deliveries WHERE company_id=%s', (ctx['company_id'],))
    seen = []
    def fail_audit(connection, result):
        assert connection is ctx['conn']
        seen.append(result)
        raise RuntimeError('synthetic audit sink failure')
    fn = homologate_job if operation == 'homologate' else revert_job
    with pytest.raises(RuntimeError, match='synthetic audit sink failure'):
        fn(ctx['conn'], job['job_id'], ctx['company_id'], ctx['actor'], audit_callback=fail_audit)
    assert seen, 'Callback must execute inside the transaction before commit'
    assert_job_unchanged(ctx, job)
    assert not get_job(ctx['conn'], job['job_id'], ctx['company_id']).get('homologated_at')
    assert scalar(ctx['conn'], 'SELECT count(*) FROM deliveries WHERE company_id=%s', (ctx['company_id'],)) == before
    from core.database import get_connection
    observer = get_connection()
    try:
        assert not get_job(observer, job['job_id'], ctx['company_id']).get('homologated_at')
        assert get_job(observer, job['job_id'], ctx['company_id'])['status'] == 'completed'
        assert scalar(observer, 'SELECT count(*) FROM deliveries WHERE company_id=%s', (ctx['company_id'],)) == before
    finally:
        observer.close()


def test_concurrent_fk_insert_blocks_rollback_then_forces_safe_refusal(ctx):
    from core.database import get_connection
    from modules.data_migration.service import revert_job
    job = run(ctx)
    target = unit_id(ctx)
    name = 'p0_fk_' + uuid.uuid4().hex
    conn = ctx['conn']
    inserter, worker = get_connection(), get_connection()
    thread = None
    try:
        conn.execute(f'CREATE SCHEMA {name}')
        conn.execute(f'CREATE TABLE {name}.child (id integer PRIMARY KEY, '
                     'unit_id integer REFERENCES public.units(id) ON DELETE CASCADE)')
        conn.commit()
        # The uncommitted FK insertion holds KEY SHARE on the parent row.
        inserter.execute(f'INSERT INTO {name}.child VALUES (1,%s)', (target,))
        worker.execute("SET statement_timeout='5000ms'")
        pid = scalar(worker, 'SELECT pg_backend_pid()')
        worker.commit()
        thread, outcomes = background_call(lambda: revert_job(worker, job['job_id'], ctx['company_id'], ctx['actor']))
        wait_lock(conn, pid)
        inserter.commit()
        thread.join(7)
        assert not thread.is_alive(), 'Rollback failed to finish within bounded timeout'
        assert outcomes, 'Worker produced no outcome'
        assert isinstance(outcomes[0], ValueError) or (
            isinstance(outcomes[0], dict) and (outcomes[0].get('conflicts') or outcomes[0].get('blocked'))), outcomes
        conn.rollback()
        assert scalar(conn, 'SELECT id FROM units WHERE id=%s', (target,)) == target
        assert scalar(conn, f'SELECT unit_id FROM {name}.child WHERE id=1') == target
        assert_job_unchanged(ctx, job)
    finally:
        inserter.rollback()
        if thread:
            thread.join(7)
        worker.rollback()
        worker.close()
        inserter.close()
        conn.rollback()
        conn.execute(f'DROP SCHEMA IF EXISTS {name} CASCADE')
        conn.commit()
