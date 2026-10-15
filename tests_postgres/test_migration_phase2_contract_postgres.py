"""Independent follow-up contracts: stale previews and persisted-effect truthfulness."""
import csv
import io
import uuid
import pytest
from tests_postgres.test_migration_p0_postgres import ctx as ctx, schema as schema, scalar, run, history, pytestmark as pytestmark
from modules.data_migration.service import run_migration


def invoke(ctx, rows, strategy='dry_run', mapping=None, **kwargs):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return run_migration(ctx['conn'], company_id=ctx['company_id'], entity='unidades',
                         source_kind='csv', raw=stream.getvalue().encode(),
                         mapping=mapping or {key:key for key in rows[0]}, strategy=strategy,
                         actor=ctx['actor'], source_name='synthetic-contract.csv', **kwargs)


def unit(name='P0 unit', **changes):
    return dict(name=name, unit_type='base', city='Macaé', **changes)


def count(ctx):
    return scalar(ctx['conn'], 'SELECT count(*) FROM units WHERE company_id=%s', (ctx['company_id'],))


def test_stale_preview_after_manual_edit_is_rejected_without_writes(ctx):
    run(ctx)
    rows = [unit(notes='planned import')]
    token = invoke(ctx, rows, preview_strategy='upsert')['preview']['preview_token']
    ctx['conn'].execute("UPDATE units SET notes='later manual edit' WHERE company_id=%s", (ctx['company_id'],))
    ctx['conn'].commit()
    with pytest.raises(ValueError):
        invoke(ctx, rows, 'upsert', preview_token=token)
    assert scalar(ctx['conn'], 'SELECT notes FROM units WHERE company_id=%s', (ctx['company_id'],)) == 'later manual edit'


@pytest.mark.parametrize('change', ['strategy', 'mapping'])
def test_preview_token_binds_mapping_and_strategy(ctx, change):
    run(ctx)
    rows = [unit(notes='planned import')]
    token = invoke(ctx, rows, preview_strategy='upsert')['preview']['preview_token']
    kwargs = dict(preview_token=token)
    if change == 'mapping':
        kwargs['mapping'] = {key:key for key in rows[0] if key != 'notes'}
    with pytest.raises(ValueError):
        invoke(ctx, rows, 'insert_only' if change == 'strategy' else 'upsert', **kwargs)
    assert scalar(ctx['conn'], 'SELECT notes FROM units WHERE company_id=%s', (ctx['company_id'],)) == 'import'


def test_without_token_revalidates_current_base_and_returns_actual_counts(ctx):
    rows = [unit('New item')]
    assert invoke(ctx, rows)['preview']['will_insert'] == 1
    invoke(ctx, rows, 'insert_only')
    result = invoke(ctx, rows, 'insert_only')
    assert result['preview']['will_insert'] == 0
    assert result['preview']['will_update'] == 0
    assert result['totals']['skipped'] == 1
    assert count(ctx) == 1


def test_epi_name_is_not_unique_but_ca_conflicts(ctx):
    history(ctx, strategy='dry_run')
    base = dict(name='Synthetic Glove', purchase_code='DISTINCT-CODE', ca='54321', ca_expiry='2030-01-01', epi_validity_date='2031-01-01', unit_measure='PAR', sector='Audit')
    result = run(ctx, 'epis', [base])
    assert result['totals']['inserted'] == 1
    base.update(purchase_code='ANOTHER-CODE')
    preview = run(ctx, 'epis', [base], 'dry_run')['preview']
    assert preview['blocking'], preview
    assert scalar(ctx['conn'], 'SELECT count(*) FROM epis WHERE company_id=%s', (ctx['company_id'],)) == 2


def test_numeric_reference_name_and_internal_id_collision_blocks(ctx):
    run(ctx)
    first_id = scalar(ctx['conn'], 'SELECT id FROM units WHERE company_id=%s', (ctx['company_id'],))
    run(ctx, rows=[unit(str(first_id))])
    employee = dict(name='Synthetic Employee', cpf='11144477735', employee_id_code='NUMERIC', unit_id=str(first_id), role_name='Audit', admission_date='2020-01-01')
    preview = run(ctx, 'colaboradores', [employee], 'dry_run')['preview']
    assert preview['blocking'], preview
    assert any(d.get('field') == 'unit_id' for d in preview['diagnostics'])
    assert scalar(ctx['conn'], 'SELECT count(*) FROM employees WHERE company_id=%s', (ctx['company_id'],)) == 0


def test_overwrite_clears_explicit_mapped_blank_but_preserves_unmapped(ctx):
    run(ctx)
    invoke(ctx, [unit(notes='')], 'overwrite')
    assert scalar(ctx['conn'], 'SELECT notes FROM units WHERE company_id=%s', (ctx['company_id'],)) in ('', None)
    ctx['conn'].execute("UPDATE units SET notes='manual unmapped' WHERE company_id=%s", (ctx['company_id'],))
    ctx['conn'].commit()
    invoke(ctx, [unit()], 'overwrite')
    assert scalar(ctx['conn'], 'SELECT notes FROM units WHERE company_id=%s', (ctx['company_id'],)) == 'manual unmapped'


@pytest.mark.parametrize('behavior', ['mutate', 'suppress_write', 'suppress_audit'])
def test_database_trigger_cannot_silently_commit_false_success(ctx, behavior):
    suffix = uuid.uuid4().hex
    function = 'p2_fn_' + suffix
    trigger = 'p2_tr_' + suffix
    table = 'migration_job_records' if behavior == 'suppress_audit' else 'units'
    body = "NEW.city := 'unexpected trigger value'; RETURN NEW;" if behavior == 'mutate' else 'RETURN NULL;'
    ctx['conn'].execute(f'CREATE FUNCTION {function}() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN {body} END $$')
    # Filter by synthetic tenant; concurrent tests in other tenants remain untouched.
    ctx['conn'].execute(f'CREATE TRIGGER {trigger} BEFORE INSERT ON {table} FOR EACH ROW WHEN (NEW.company_id = {int(ctx["company_id"])}) EXECUTE FUNCTION {function}()')
    ctx['conn'].commit()
    try:
        try:
            result = invoke(ctx, [unit('Trigger unit')], 'insert_only')
        except Exception:
            # Failure must have been cleaned up by the service, not this test.
            assert scalar(ctx['conn'], 'SELECT 1') == 1
        else:
            assert not result['applied'] or result['totals']['inserted'] == 0, result
        from core.database import get_connection
        observer = get_connection()
        try:
            assert scalar(observer, 'SELECT count(*) FROM units WHERE company_id=%s', (ctx['company_id'],)) == 0
        finally:
            observer.close()
    finally:
        ctx['conn'].rollback()
        ctx['conn'].execute(f'DROP TRIGGER {trigger} ON {table}')
        ctx['conn'].execute(f'DROP FUNCTION {function}()')
        ctx['conn'].commit()


def test_partial_job_reverts_only_persisted_effects_and_cannot_homologate(ctx, monkeypatch):
    from modules.data_migration.service import homologate_job, revert_job
    original = ctx['conn'].execute
    def reject(sql, params=()):
        if sql.strip().upper().startswith('INSERT INTO UNITS') and 'Rejected unit' in params:
            raise RuntimeError('synthetic row rejection')
        return original(sql, params)
    monkeypatch.setattr(ctx['conn'], 'execute', reject)
    result = invoke(ctx, [unit('Accepted unit'), unit('Rejected unit')], 'insert_only')
    monkeypatch.setattr(ctx['conn'], 'execute', original)
    assert result['totals']['inserted'] == 1 and result['totals']['failed'] == 1
    with pytest.raises(ValueError):
        homologate_job(ctx['conn'], result['job_id'], ctx['company_id'], ctx['actor'])
    assert count(ctx) == 1
    revert_job(ctx['conn'], result['job_id'], ctx['company_id'], ctx['actor'])
    assert count(ctx) == 0


def test_failure_after_job_creation_recovers_transaction_and_connection(ctx, monkeypatch):
    import modules.data_migration.service as service
    from core.database import get_connection
    original = service.create_job
    def fail_after_insert(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError('synthetic job creation failure')
    monkeypatch.setattr(service, 'create_job', fail_after_insert)
    with pytest.raises(RuntimeError, match='synthetic job creation failure'):
        invoke(ctx, [unit()], strategy='insert_only')
    assert scalar(ctx['conn'], 'SELECT 1') == 1
    observer = get_connection()
    try:
        assert scalar(observer, 'SELECT count(*) FROM migration_jobs WHERE company_id=%s', (ctx['company_id'],)) == 0
        assert scalar(observer, 'SELECT count(*) FROM units WHERE company_id=%s', (ctx['company_id'],)) == 0
    finally:
        observer.close()


def test_execution_audit_failure_rolls_back_targets_and_counters(ctx):
    from core.database import get_connection
    def fail_audit(connection, result):
        assert scalar(connection, 'SELECT count(*) FROM units WHERE company_id=%s', (ctx['company_id'],)) == 1
        raise RuntimeError('private audit exception with SQL')
    with pytest.raises(ValueError, match='Falha transacional'):
        invoke(ctx, [unit()], strategy='insert_only', audit_callback=fail_audit)
    assert scalar(ctx['conn'], 'SELECT 1') == 1
    observer = get_connection()
    try:
        assert scalar(observer, 'SELECT count(*) FROM units WHERE company_id=%s', (ctx['company_id'],)) == 0
        row = observer.execute('SELECT status,inserted_rows,error_message FROM migration_jobs WHERE company_id=%s', (ctx['company_id'],)).fetchone()
        from epi_backend.db import row_to_dict
        row = row_to_dict(row)
        assert row['status'] == 'failed' and row['inserted_rows'] == 0
        assert 'private' not in row['error_message'] and 'SQL' not in row['error_message']
    finally:
        observer.close()


def test_record_report_paginates_without_loss_or_tenant_leak(ctx):
    from modules.data_migration.service import fetch_job_records
    result = invoke(ctx, [unit(name=f'Bulk {i}') for i in range(501)], strategy='insert_only')
    first = fetch_job_records(ctx['conn'], result['job_id'], ctx['company_id'])
    last = fetch_job_records(ctx['conn'], result['job_id'], ctx['company_id'], offset=500)
    assert len(first) == 500 and len(last) == 1
    assert [r['row_number'] for r in first + last] == list(range(1,502))
    assert [r['source_line'] for r in first + last] == list(range(2,503))
    assert all(r['action'] == 'insert' for r in first + last)
    assert not fetch_job_records(ctx['conn'], result['job_id'], ctx['company_id']+1)
