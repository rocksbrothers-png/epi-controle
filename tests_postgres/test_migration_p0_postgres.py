"""P0 invariants on real PostgreSQL. DATABASE_URL must name an isolated database.

All rows are synthetic and tenant-scoped; no shared/production database is safe
for this suite because bootstrap applies the project's schema migrations.
"""
import os
import sys
import threading
import time
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
pytestmark = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL', '').startswith('postgres'),
    reason='P0 regression requires explicit PostgreSQL DATABASE_URL',
)


def scalar(conn, sql, params=()):
    from epi_backend.db import row_to_dict
    row = conn.execute(sql, params).fetchone()
    return next(iter(row_to_dict(row).values())) if row else None


@pytest.fixture(scope='module', autouse=True)
def schema():
    from core.bootstrap import init_db
    init_db()


@pytest.fixture
def ctx(schema):
    from core.database import get_connection
    from tests_postgres.test_migration_journey_postgres import _valid_cnpj_from
    c = get_connection()
    tag = uuid.uuid4().hex
    cid = scalar(c, "INSERT INTO companies(name,cnpj,logo_type) VALUES(%s,%s,'') RETURNING id",
                 ('P0 ' + tag, _valid_cnpj_from(f'{int(tag[:12],16) % 10**12:012d}')))
    c.commit()
    state = {'conn': c, 'company_id': cid,
             'actor': {'id': 0, 'full_name': 'Synthetic P0 audit', 'company_id': cid}}
    yield state
    c.rollback()
    c.close()


def run(ctx, entity='unidades', rows=None, strategy='insert_only'):
    import csv
    import io
    from modules.data_migration.service import run_migration
    rows = rows or [{'name': 'P0 unit', 'unit_type': 'base', 'city': 'Macaé', 'notes': 'import'}]
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return run_migration(ctx['conn'], company_id=ctx['company_id'], entity=entity,
                         source_kind='csv', raw=stream.getvalue().encode(),
                         mapping={k: k for k in rows[0]}, strategy=strategy,
                         actor=ctx['actor'], source_name='synthetic-p0.csv')


def history(ctx, quantity='1', strategy='insert_only'):
    if 'seeded' not in ctx:
        run(ctx)
        run(ctx, 'colaboradores', [{'name': 'Synthetic Employee', 'cpf': '11144477735',
             'employee_id_code': 'P0-1', 'unit_id': 'P0 unit', 'role_name': 'Audit',
             'admission_date': '2020-01-01'}])
        run(ctx, 'epis', [{'name': 'Synthetic Glove', 'purchase_code': 'P0-EPI',
             'ca': '12345', 'ca_expiry': '2030-01-01', 'epi_validity_date': '2031-01-01',
             'unit_measure': 'PAR', 'sector': 'Audit'}])
        ctx['seeded'] = True
    return run(ctx, 'historico_entregas', [{'employee_id': 'P0-1', 'epi_id': 'Synthetic Glove',
               'delivery_date': '2020-02-01', 'quantity': quantity,
               'signature_name': 'Synthetic Employee'}], strategy)


def rejection_or_conflict(fn):
    """Both an explicit business rejection and a structured conflict are safe."""
    try:
        result = fn()
    except ValueError:
        return
    assert result.get('conflicts') or result.get('blocked') or result.get('conflict'), result


@pytest.mark.parametrize('quantity', ['1.9', 'NaN', 'Infinity', '-Infinity', '2147483648', '-2147483649', '0', '-1'])
def test_invalid_quantity_has_structured_preview_and_cannot_write(ctx, quantity):
    preview = history(ctx, quantity, 'dry_run')['preview']
    assert preview['blocking'] is True, preview
    errors = [d for d in preview['diagnostics'] if d.get('field') == 'quantity']
    assert errors, preview
    assert all(d.get('row') == 1 and d.get('entity') == 'historico_entregas' and d.get('severity') == 'error' for d in errors), errors
    with pytest.raises(ValueError):
        history(ctx, quantity)
    ctx['conn'].rollback()
    assert scalar(ctx['conn'], 'SELECT count(*) FROM deliveries WHERE company_id=%s', (ctx['company_id'],)) == 0


@pytest.mark.parametrize('strategy', ['insert_only', 'upsert'])
@pytest.mark.parametrize('column,value', [('notes', 'manual edit'), ('preferred_contact_channel', 'email')])
def test_rollback_preserves_later_manual_edits_including_unmapped_columns(ctx, strategy, column, value):
    from modules.data_migration.service import revert_job
    # preferred_contact_channel is intentionally absent from the import mapping.
    history(ctx, strategy='dry_run')
    employee = {'name': 'Synthetic Employee', 'cpf': '11144477735', 'employee_id_code': 'P0-1',
                'unit_id': 'P0 unit', 'role_name': 'New imported role', 'admission_date': '2020-01-01'}
    if strategy == 'insert_only':
        employee.update(cpf='52998224725', employee_id_code='P0-2')
    job = run(ctx, 'colaboradores', [employee], strategy)
    # role_name is mapped; preferred_contact_channel is not. Both protect the record.
    actual_col = 'role_name' if column == 'notes' else column
    ctx['conn'].execute(f'UPDATE employees SET {actual_col}=%s WHERE company_id=%s AND employee_id_code=%s',
                        (value, ctx['company_id'], employee['employee_id_code']))
    ctx['conn'].commit()
    rejection_or_conflict(lambda: revert_job(ctx['conn'], job['job_id'], ctx['company_id'], ctx['actor']))
    ctx['conn'].rollback()
    assert scalar(ctx['conn'], f'SELECT {actual_col} FROM employees WHERE company_id=%s AND employee_id_code=%s',
                  (ctx['company_id'], employee['employee_id_code'])) == value


def test_later_fk_dependency_blocks_entire_rollback(ctx):
    from modules.data_migration.service import revert_job, get_job
    job = run(ctx, rows=[{'name':'P0 unit','unit_type':'base','city':'Macaé'},
                         {'name':'Independent unit','unit_type':'base','city':'Macaé'}])
    run(ctx, 'colaboradores', [{'name':'Dependent', 'cpf':'11144477735','employee_id_code':'dep',
         'unit_id':'P0 unit','role_name':'Audit','admission_date':'2020-01-01'}])
    try:
        revert_job(ctx['conn'], job['job_id'], ctx['company_id'], ctx['actor'])
    except Exception:
        # Atomicity must be observable from a new connection, not rescued by
        # a rollback performed by the test or request teardown.
        pass
    from core.database import get_connection
    observer = get_connection()
    try:
        assert scalar(observer, 'SELECT count(*) FROM units WHERE company_id=%s', (ctx['company_id'],)) == 2
        assert get_job(observer, job['job_id'], ctx['company_id'])['status'] == 'completed'
    finally:
        observer.close()
    # Service must leave connection usable even on FK rejection.
    assert scalar(ctx['conn'], 'SELECT 1') == 1


def background_call(fn):
    results = []
    def invoke():
        try:
            results.append(fn())
        except Exception as exc:
            results.append(exc)
    thread = threading.Thread(target=invoke, daemon=True)
    thread.start()
    return thread, results


def wait_lock(observer, pid):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        observer.rollback()
        if scalar(observer, 'SELECT wait_event_type FROM pg_stat_activity WHERE pid=%s', (pid,)) == 'Lock':
            return
        time.sleep(.02)
    pytest.fail('Worker never reached expected PostgreSQL lock within 3s')


def test_homologation_serializes_with_revert_and_never_deletes_official_history(ctx):
    from core.database import get_connection
    from modules.data_migration.service import homologate_job, revert_job
    job = history(ctx)
    blocker, worker = get_connection(), get_connection()
    try:
        worker.execute("SET statement_timeout='5000ms'")
        pid = scalar(worker, 'SELECT pg_backend_pid()')
        worker.commit()
        blocker.execute('SELECT id FROM migration_jobs WHERE id=%s FOR UPDATE', (job['job_id'],))
        thread, results = background_call(lambda: revert_job(worker, job['job_id'], ctx['company_id'], ctx['actor']))
        try:
            wait_lock(ctx['conn'], pid)
            homologate_job(blocker, job['job_id'], ctx['company_id'], ctx['actor'])
        finally:
            blocker.rollback()
            thread.join(7)
        assert not thread.is_alive(), 'Rollback did not finish within bounded timeout'
        assert results and not isinstance(results[0], Exception), results
        ctx['conn'].rollback()
        assert scalar(ctx['conn'], 'SELECT count(*) FROM deliveries WHERE company_id=%s', (ctx['company_id'],)) == 1
        assert scalar(ctx['conn'], 'SELECT migration_reverted_at FROM deliveries WHERE company_id=%s', (ctx['company_id'],))
    finally:
        blocker.rollback()
        worker.rollback()
        blocker.close()
        worker.close()


@pytest.mark.parametrize('operation', ['revert', 'homologate'])
def test_same_operation_repeats_are_rejected_and_tenant_scope_is_preserved(ctx, operation):
    from modules.data_migration.service import revert_job, homologate_job, get_job
    job = history(ctx)
    fn = revert_job if operation == 'revert' else homologate_job
    with pytest.raises(ValueError):
        fn(ctx['conn'], job['job_id'], ctx['company_id'] + 1000000, ctx['actor'])
    ctx['conn'].rollback()
    assert get_job(ctx['conn'], job['job_id'], ctx['company_id'])['status'] == 'completed'
    fn(ctx['conn'], job['job_id'], ctx['company_id'], ctx['actor'])
    with pytest.raises(ValueError):
        fn(ctx['conn'], job['job_id'], ctx['company_id'], ctx['actor'])
    ctx['conn'].rollback()


@pytest.mark.parametrize('operation', ['revert', 'homologate'])
def test_concurrent_same_operation_has_one_winner_and_no_deadlock(ctx, operation):
    from core.database import get_connection
    from modules.data_migration.service import homologate_job, revert_job
    job = history(ctx)
    blocker = get_connection()
    workers = [get_connection(), get_connection()]
    running = []
    fn = revert_job if operation == 'revert' else homologate_job
    try:
        blocker.execute('SELECT id FROM migration_jobs WHERE id=%s FOR UPDATE', (job['job_id'],))
        for worker in workers:
            worker.execute("SET statement_timeout='5000ms'")
            pid = scalar(worker, 'SELECT pg_backend_pid()')
            worker.commit()
            thread, results = background_call(
                lambda c=worker: fn(c, job['job_id'], ctx['company_id'], ctx['actor']))
            running.append((thread, results))
            wait_lock(ctx['conn'], pid)
        blocker.commit()
        for thread, _ in running:
            thread.join(7)
            assert not thread.is_alive(), 'Concurrent operation exceeded bounded timeout'
        outcomes = [results[0] for _, results in running]
        assert sum(isinstance(r, dict) for r in outcomes) == 1, outcomes
        losers = [r for r in outcomes if isinstance(r, Exception)]
        assert len(losers) == 1 and isinstance(losers[0], ValueError), outcomes
        assert 'deadlock' not in str(losers[0]).lower(), outcomes
    finally:
        blocker.rollback()
        for thread, _ in running:
            thread.join(7)
        for worker in workers:
            worker.rollback()
            worker.close()
        blocker.close()


def test_rollback_failure_after_first_write_is_atomic_and_connection_recovers(ctx, monkeypatch):
    from core.database import get_connection
    from modules.data_migration.service import revert_job, get_job
    job = run(ctx, rows=[{'name':'Atomic one','unit_type':'base','city':'Macaé'},
                         {'name':'Atomic two','unit_type':'base','city':'Macaé'}])
    original = ctx['conn'].execute
    mutations = []
    def fail_second_delete(sql, params=()):
        if sql.strip().upper().startswith('DELETE FROM UNITS'):
            mutations.append(sql)
            if len(mutations) == 2:
                raise RuntimeError('synthetic failure after first rollback mutation')
        return original(sql, params)
    monkeypatch.setattr(ctx['conn'], 'execute', fail_second_delete)
    with pytest.raises((RuntimeError, ValueError)):
        revert_job(ctx['conn'], job['job_id'], ctx['company_id'], ctx['actor'])
    monkeypatch.setattr(ctx['conn'], 'execute', original)
    observer = get_connection()
    try:
        assert scalar(observer, 'SELECT count(*) FROM units WHERE company_id=%s', (ctx['company_id'],)) == 2
        assert get_job(observer, job['job_id'], ctx['company_id'])['status'] == 'completed'
    finally:
        observer.close()
    # The original connection must see the same state before test cleanup.
    assert scalar(ctx['conn'], 'SELECT count(*) FROM units WHERE company_id=%s', (ctx['company_id'],)) == 2
    assert scalar(ctx['conn'], 'SELECT 1') == 1
