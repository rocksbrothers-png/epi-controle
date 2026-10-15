"""Independent Phase 2 black-box regressions; synthetic isolated PostgreSQL only."""
import json
import pytest
from tests_postgres.test_migration_p0_postgres import ctx as ctx, schema as schema, run, history, scalar, pytestmark as pytestmark


def employee(cpf='11144477735', registration='P0-1', **changes):
    return dict(name='Synthetic Employee', cpf=cpf, employee_id_code=registration,
                unit_id='P0 unit', role_name='Audit', admission_date='2020-01-01', **changes)


def seeded(ctx):
    history(ctx, strategy='dry_run')


def assert_blocked(ctx, rows):
    before = scalar(ctx['conn'], 'SELECT count(*) FROM employees WHERE company_id=%s', (ctx['company_id'],))
    preview = run(ctx, 'colaboradores', rows, 'dry_run')['preview']
    assert preview['blocking'], preview
    assert any(d.get('row') and d.get('field') and d.get('message') for d in preview['diagnostics']), preview
    with pytest.raises(ValueError):
        run(ctx, 'colaboradores', rows, 'upsert')
    assert scalar(ctx['conn'], 'SELECT count(*) FROM employees WHERE company_id=%s', (ctx['company_id'],)) == before


@pytest.mark.parametrize('cpf,registration', [('52998224725','P0-1'), ('11144477735','CHANGED')])
def test_employee_identity_mismatch_against_base_blocks(ctx, cpf, registration):
    seeded(ctx)
    assert_blocked(ctx, [employee(cpf, registration)])
    assert scalar(ctx['conn'], 'SELECT employee_id_code FROM employees WHERE company_id=%s', (ctx['company_id'],)) == 'P0-1'


@pytest.mark.parametrize('rows', [
    [employee('52998224725','NEW'), employee('12345678909','NEW')],
    [employee('52998224725','NEW'), employee('52998224725','OTHER')],
])
def test_employee_identity_mismatch_inside_file_blocks(ctx, rows):
    run(ctx)
    assert_blocked(ctx, rows)


def test_employee_two_identifiers_pointing_different_rows_never_updates(ctx):
    seeded(ctx)
    run(ctx, 'colaboradores', [employee('52998224725','P0-2')])
    assert_blocked(ctx, [employee('11144477735','P0-2')])
    assert scalar(ctx['conn'], "SELECT count(*) FROM employees WHERE company_id=%s AND role_name='Audit'", (ctx['company_id'],)) == 2


def test_identical_employee_keys_are_scoped_to_tenant(ctx):
    from core.database import get_connection
    from tests_postgres.test_migration_journey_postgres import _valid_cnpj_from
    import uuid
    seeded(ctx)
    other = get_connection()
    try:
        token = uuid.uuid4().int % 10**12
        cid = scalar(other, "INSERT INTO companies(name,cnpj,logo_type) VALUES(%s,%s,'') RETURNING id", ('Phase2 other', _valid_cnpj_from(f'{token:012d}')))
        other.commit()
        alternate = dict(conn=other, company_id=cid, actor=dict(id=0, full_name='Synthetic', company_id=cid))
        run(alternate)
        result = run(alternate, 'colaboradores', [employee()])
        assert result['totals']['inserted'] == 1
        assert scalar(other, 'SELECT count(*) FROM employees WHERE company_id=%s', (cid,)) == 1
    finally:
        other.rollback()
        other.close()


def test_epi_same_name_different_purchase_code_conflicts(ctx):
    seeded(ctx)
    row = dict(name='Synthetic Glove', purchase_code='DIFFERENT', ca='12345', ca_expiry='2030-01-01', epi_validity_date='2031-01-01', unit_measure='PAR', sector='Audit')
    preview = run(ctx, 'epis', [row], 'dry_run')['preview']
    assert preview['blocking'], preview
    with pytest.raises(ValueError):
        run(ctx, 'epis', [row], 'upsert')


def test_invalid_row_never_counted_as_insertion(ctx):
    preview = run(ctx, rows=[dict(name='Invalid', unit_type='base', city='')], strategy='dry_run')['preview']
    assert preview['blocking'] and preview['invalid_rows'] == 1
    assert preview['will_insert'] == 0 and preview['will_update'] == 0, preview


def test_empty_unit_type_is_rejected_without_default(ctx):
    preview = run(ctx, rows=[dict(name='Invalid', unit_type='', city='Macaé')], strategy='dry_run')['preview']
    assert preview['blocking'], preview
    assert any(d.get('field') == 'unit_type' for d in preview['diagnostics'])


@pytest.mark.parametrize('strategy,inserted,updated,skipped', [
    ('insert_only',1,0,1), ('update_only',0,1,1), ('upsert',1,1,0), ('skip_duplicates',1,0,1),
])
def test_preview_actions_match_selected_strategy(ctx, strategy, inserted, updated, skipped):
    run(ctx)
    result = run(ctx, rows=[dict(name='P0 unit', unit_type='base', city='New city'), dict(name='New unit', unit_type='base', city='Macaé')], strategy=strategy)
    preview = result['preview']
    assert preview['will_insert'] == inserted, preview
    assert preview['will_update'] == updated, preview
    assert result['totals']['inserted'] == inserted
    assert result['totals']['updated'] == updated
    assert result['totals']['skipped'] == skipped


def test_history_preview_counts_per_line_and_reimport_skips(ctx):
    seeded(ctx)
    rows = [dict(employee_id='P0-1', epi_id='Synthetic Glove', delivery_date='2020-02-01', quantity='1', signature_name='Synthetic Employee'), dict(employee_id='P0-1', epi_id='Synthetic Glove', delivery_date='2020-02-02', quantity='2', signature_name='Synthetic Employee')]
    preview = run(ctx, 'historico_entregas', rows, 'dry_run')['preview']
    assert preview['will_insert'] == 2 and preview['will_update'] == 0, preview
    first = run(ctx, 'historico_entregas', rows)
    second = run(ctx, 'historico_entregas', rows)
    assert first['totals']['inserted'] == 2
    assert second['totals']['skipped'] == 2 and second['totals']['inserted'] == 0
    assert second['preview']['will_insert'] == 0, second


@pytest.mark.parametrize('partial', [False, True])
def test_db_row_failures_are_truthful_sanitized_and_processed(ctx, monkeypatch, partial):
    from modules.data_migration.service import get_job, fetch_job_records
    original = ctx['conn'].execute
    def reject_insert(sql, params=()):
        if sql.strip().upper().startswith('INSERT INTO UNITS') and (not partial or 'Bad synthetic unit' in params):
            raise RuntimeError('INTERNAL_SECRET SQL INSERT INTO units password=synthetic-secret')
        return original(sql, params)
    monkeypatch.setattr(ctx['conn'], 'execute', reject_insert)
    rows = [dict(name='Bad synthetic unit', unit_type='base', city='Macaé'), dict(name='Good synthetic unit', unit_type='base', city='Macaé')]
    result = run(ctx, rows=rows)
    job = get_job(ctx['conn'], result['job_id'], ctx['company_id'])
    assert result['totals']['processed'] == 2, result
    assert result['totals']['failed'] == (1 if partial else 2)
    if partial:
        assert job['status'] == 'completed_with_rejections', job
    else:
        assert not (job['status'] == 'completed' and result['applied'] is True), result
    records = fetch_job_records(ctx['conn'], result['job_id'], ctx['company_id'])
    errors = [r for r in records if r['action'] == 'error']
    assert errors
    encoded = json.dumps(errors)
    assert 'INTERNAL_SECRET' not in encoded and 'synthetic-secret' not in encoded and 'INSERT INTO' not in encoded, errors
    assert all(r['error_message'] for r in errors)
