"""MIG-DATA-E2E-V1: real HTTP requests, parsers and isolated PostgreSQL.

Every enabled file format is actually analyzed, previewed and imported for
all six entities. These proofs cover the declared aggregate-stock contract;
lot/physical-expiry migration is explicitly outside that contract.
"""
import base64
import csv
import http.client
import io
import json
import threading
import uuid
from http.server import ThreadingHTTPServer
from xml.etree.ElementTree import Element, SubElement, tostring

import pytest

# Pytest discovers these fixtures/markers through module globals.
from tests_postgres.test_migration_p0_postgres import (
    ctx as ctx,  # noqa: PLC0414
)
from tests_postgres.test_migration_p0_postgres import (
    history,
    run,
    scalar,
)
from tests_postgres.test_migration_p0_postgres import (
    pytestmark as pytestmark,  # noqa: PLC0414
)
from tests_postgres.test_migration_p0_postgres import (
    schema as schema,  # noqa: PLC0414
)

ENTITIES = {
    'colaboradores': ('employees', 11), 'unidades': ('units', 4),
    'epis': ('epis', 11), 'fornecedores': ('outsourced_companies', 5),
    'historico_entregas': ('deliveries', 8), 'estoque': ('unit_epi_stock', 4),
}
FORMATS = ('csv', 'txt', 'xlsx', 'ods', 'json', 'xml')


@pytest.fixture(scope='module')
def http_server(schema):
    from app import EpiHandler
    from epi_backend.bootstrap import _get_bootstrap_state, _set_bootstrap_state
    previous = _get_bootstrap_state()
    _set_bootstrap_state(ready=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), EpiHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server.server_address[1]
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
    _set_bootstrap_state(**previous)


@pytest.fixture
def api_ctx(ctx, http_server):
    from core.security import create_jwt_token
    from modules.settings.service import save_module_visibility
    uid = scalar(ctx['conn'], "INSERT INTO users(username,password,full_name,role,company_id,active) "
                 "VALUES(%s,'synthetic-hash','Auditoria E2E','general_admin',%s,1) RETURNING id",
                 ('e2e-' + uuid.uuid4().hex, ctx['company_id']))
    ctx['actor'].update(id=uid, role='general_admin')
    save_module_visibility(ctx['conn'], ctx['company_id'], 'general_admin', {'migracao': True})
    ctx['conn'].commit()
    ctx.update(port=http_server, token=create_jwt_token(ctx['actor']))
    return ctx


def request(ctx, path, payload=None, *, token=None):
    connection = http.client.HTTPConnection('127.0.0.1', ctx['port'], timeout=30)
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + (token or ctx['token'])}
    connection.request('POST' if payload is not None else 'GET', path,
                       body=json.dumps(payload) if payload is not None else None, headers=headers)
    response = connection.getresponse()
    result = json.loads(response.read())
    status = response.status
    connection.close()
    return status, result


def encode(kind, rows):
    if kind in ('csv', 'txt'):
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter=';' if kind == 'csv' else '\t')
        writer.writeheader()
        writer.writerows(rows)
        return stream.getvalue().encode('utf-8')
    if kind == 'json':
        return json.dumps(rows, ensure_ascii=False).encode()
    if kind == 'xml':
        root = Element('rows')
        for row in rows:
            child = SubElement(root, 'row')
            for key, value in row.items():
                SubElement(child, key).text = str(value)
        return tostring(root, encoding='utf-8')
    import pandas as pd
    stream = io.BytesIO()
    pd.DataFrame(rows).to_excel(stream, index=False, engine='odf' if kind == 'ods' else 'openpyxl')
    return stream.getvalue()


def row_for(entity):
    return {
        'unidades': {'name': 'São João & Filhos', 'unit_type': 'base', 'city': 'Vitória', 'notes': 'Ação 第二'},
        'colaboradores': {'name': 'João Conceição', 'cpf': '529.982.247-25', 'employee_id_code': 'E2E-2',
            'unit_id': 'P0 unit', 'role_name': 'Soldador', 'admission_date': '25/10/2020'},
        'epis': {'name': 'Óculos & Proteção', 'purchase_code': 'E2E-2', 'ca': '54321', 'ca_expiry': '25/10/2030',
            'epi_validity_date': '25/10/2031', 'unit_measure': 'UN', 'sector': 'Ação', 'manufacturer': 'Fábrica São João'},
        'fornecedores': {'unit_id': 'P0 unit', 'legal_name': 'São João & Filhos', 'trade_name': 'Proteção',
            'cnpj': '11.222.333/0001-81', 'company_kind': 'supplier'},
        'historico_entregas': {'employee_id': 'P0-1', 'epi_id': 'Synthetic Glove', 'delivery_date': '25/10/2020',
            'quantity': '37', 'signature_name': 'João Conceição', 'notes': 'Histórico & ação'},
        'estoque': {'unit_id': 'P0 unit', 'epi_id': 'Synthetic Glove', 'quantity': '37', 'notes': 'Saldo legado & ação'},
    }[entity]


def body(ctx, entity, kind, rows):
    return {'actor_user_id': ctx['actor']['id'], 'entity': entity, 'source_kind': kind,
                'source_name': 'synthetic.' + kind, 'content_base64': base64.b64encode(encode(kind, rows)).decode(),
                'mapping': {key: key for key in rows[0]}, 'strategy': 'insert_only'}


def count(ctx, table):
    return scalar(ctx['conn'], f'SELECT count(*) FROM {table} WHERE company_id=%s', (ctx['company_id'],))


@pytest.mark.parametrize('entity', list(ENTITIES))
@pytest.mark.parametrize('kind', FORMATS)
def test_http_to_postgres_reconciliation_homologation_and_rollback(api_ctx, entity, kind):
    ctx = api_ctx
    history(ctx, strategy='dry_run')  # real dependency seeds, not target under test
    table = ENTITIES[entity][0]
    before = count(ctx, table)
    payload = body(ctx, entity, kind, [row_for(entity)])
    status, catalog = request(ctx, '/api/data-migration/catalog?actor_user_id=' + str(ctx['actor']['id']))
    assert status == 200, catalog
    assert {e['key']: len(e['fields']) for e in catalog['entities']} == {k: v[1] for k, v in ENTITIES.items()}
    status, analysis = request(ctx, '/api/data-migration/analyze', payload)
    assert status == 200, analysis
    assert analysis['entity'] == entity and analysis['detected']['total_rows'] == 1
    assert set(analysis['columns']) == set(payload['mapping'])
    status, preview = request(ctx, '/api/data-migration/run', {**payload, 'strategy': 'dry_run', 'preview_strategy': 'insert_only'})
    assert status == 200 and not preview['preview']['blocking'], preview
    assert preview['preview']['will_insert'] == 1
    assert count(ctx, table) == before
    payload['preview_token'] = preview['preview']['preview_token']
    status, result = request(ctx, '/api/data-migration/run', payload)
    assert status == 200 and result['status'] == 'completed', result
    assert result['totals'] == {'total': 1, 'processed': 1, 'inserted': 1, 'updated': 0, 'skipped': 0, 'failed': 0}
    assert result['preview_matches_result'], result
    assert count(ctx, table) == before + 1
    job_id = result['job_id']
    query = '?actor_user_id=' + str(ctx['actor']['id'])
    status, report = request(ctx, f'/api/data-migration/jobs/{job_id}' + query)
    assert status == 200 and len(report['records']) == 1, report
    record = report['records'][0]
    assert record['action'] == 'insert'
    from epi_backend.db import row_to_dict
    actual = row_to_dict(ctx['conn'].execute(f'SELECT * FROM {table} WHERE id=%s AND company_id=%s',
                         (record['target_id'], ctx['company_id'])).fetchone())
    assert actual, report
    for field, expected in result['preview']['sample'][0].items():
        if field in actual:
            assert str(actual[field]) == str(expected), (entity, field, actual[field], expected)
    if entity in ('estoque', 'historico_entregas'):
        assert actual['quantity'] == 37
    if entity == 'fornecedores':
        assert count(ctx, 'outsourced_company_unit_links') == 1
    if entity == 'estoque':
        assert scalar(ctx['conn'], 'SELECT quantity FROM stock_movements WHERE company_id=%s AND source_id=%s AND source_type=%s',
                      (ctx['company_id'], job_id, 'migration')) == 37
    status, replay = request(ctx, '/api/data-migration/run', payload)
    assert status == 400, replay  # same confirmation cannot create a second write
    assert count(ctx, table) == before + 1
    ctx['conn'].rollback()
    decision = {'actor_user_id': ctx['actor']['id']}
    status, reverted = request(ctx, f'/api/data-migration/jobs/{job_id}/revert', decision)
    assert status == 200 and reverted['deleted'] == 1, reverted
    assert count(ctx, table) == before
    ctx['conn'].rollback()
    status, preview2 = request(ctx, '/api/data-migration/run', {**payload, 'strategy': 'dry_run', 'preview_strategy': 'insert_only'})
    assert status == 200, preview2
    payload['preview_token'] = preview2['preview']['preview_token']
    status, result2 = request(ctx, '/api/data-migration/run', payload)
    assert status == 200 and result2['totals']['inserted'] == 1, result2
    job2 = result2['job_id']
    status, homologated = request(ctx, f'/api/data-migration/jobs/{job2}/homologate', decision)
    assert status == 200 and homologated['homologated'], homologated
    assert scalar(ctx['conn'], 'SELECT homologated_by FROM migration_jobs WHERE id=%s', (job2,)) == ctx['actor']['id']
    ctx['conn'].rollback()
    status, reversal = request(ctx, f'/api/data-migration/jobs/{job2}/revert', decision)
    assert status == (200 if entity == 'historico_entregas' else 400), reversal
    if entity == 'historico_entregas':
        assert reversal['marked'] == 1
    assert count(ctx, table) == before + 1
    assert scalar(ctx['conn'], "SELECT count(*) FROM company_audit_logs WHERE company_id=%s AND action_type='data_migration_executed'",
                  (ctx['company_id'],)) >= 2


@pytest.mark.parametrize('entity', ['empresas', 'usuarios', 'solicitacoes'])
@pytest.mark.parametrize('endpoint', ['analyze', 'run', 'async/submit'])
def test_excluded_entities_refused_by_direct_http_without_jobs(api_ctx, monkeypatch, entity, endpoint):
    from cryptography.fernet import Fernet
    monkeypatch.setenv('MIGRATION_ASYNC_ENABLED', '1')
    monkeypatch.setenv('MIGRATION_INPUT_KEY', Fernet.generate_key().decode())
    payload = body(api_ctx, entity, 'csv', [{'name': 'Excluded'}])
    payload.update(request_key=uuid.uuid4().hex, preview_token='forged')
    before = count(api_ctx, 'migration_jobs')
    status, result = request(api_ctx, '/api/data-migration/' + endpoint, payload)
    assert status == 400 and 'excluída' in str(result), result
    assert count(api_ctx, 'migration_jobs') == before
    assert count(api_ctx, 'migration_async_jobs') == 0


@pytest.mark.parametrize('later', ['new_link', 'status_change', 'deleted_link', 'legacy_snapshot'])
def test_supplier_rollback_preserves_later_links(api_ctx, later):
    from modules.data_migration.service import revert_job
    from modules.outsourced_companies.service import create_outsourced_company_unit_link
    ctx = api_ctx
    run(ctx)
    job = run(ctx, 'fornecedores', [row_for('fornecedores')])
    supplier_id = scalar(ctx['conn'], 'SELECT id FROM outsourced_companies WHERE company_id=%s', (ctx['company_id'],))
    if later == 'new_link':
        run(ctx, rows=[{'name': 'Other', 'unit_type': 'base', 'city': 'Macaé'}])
        unit = scalar(ctx['conn'], "SELECT id FROM units WHERE company_id=%s AND name='Other'", (ctx['company_id'],))
        create_outsourced_company_unit_link(ctx['conn'], supplier_id, ctx['company_id'], unit, ctx['actor']['id'])
    elif later == 'status_change':
        ctx['conn'].execute("UPDATE outsourced_company_unit_links SET local_status='inactive' WHERE company_id=%s", (ctx['company_id'],))
    elif later == 'deleted_link':
        ctx['conn'].execute('DELETE FROM outsourced_company_unit_links WHERE company_id=%s', (ctx['company_id'],))
    else:
        ctx['conn'].execute("UPDATE migration_job_records SET after_json=after_json::jsonb #- '{__secondary_v1__}' WHERE job_id=%s", (job['job_id'],))
    ctx['conn'].commit()
    from epi_backend.db import row_to_dict
    before = [row_to_dict(r) for r in ctx['conn'].execute('SELECT * FROM outsourced_company_unit_links WHERE company_id=%s ORDER BY id', (ctx['company_id'],)).fetchall()]
    with pytest.raises(ValueError, match='Reversão recusada'):
        revert_job(ctx['conn'], job['job_id'], ctx['company_id'], ctx['actor'])
    after = [row_to_dict(r) for r in ctx['conn'].execute('SELECT * FROM outsourced_company_unit_links WHERE company_id=%s ORDER BY id', (ctx['company_id'],)).fetchall()]
    assert after == before
    assert count(ctx, 'outsourced_companies') == 1


def test_supplier_unit_change_is_blocked_in_preview_and_apply(api_ctx):
    ctx = api_ctx
    run(ctx)
    run(ctx, rows=[{'name': 'Other', 'unit_type': 'base', 'city': 'Macaé'}])
    original = row_for('fornecedores')
    run(ctx, 'fornecedores', [original])
    changed = dict(original, unit_id='Other')
    preview = run(ctx, 'fornecedores', [changed], strategy='dry_run')['preview']
    assert preview['blocking'] and preview['will_update'] == 0
    with pytest.raises(ValueError):
        run(ctx, 'fornecedores', [changed], strategy='upsert')
    assert count(ctx, 'outsourced_company_unit_links') == 1
    assert scalar(ctx['conn'], 'SELECT u.name FROM outsourced_companies o JOIN units u ON u.id=o.unit_id WHERE o.company_id=%s', (ctx['company_id'],)) == 'P0 unit'


@pytest.mark.parametrize('entity', list(ENTITIES))
def test_required_mapping_invalid_partial_and_idor_are_blocked(api_ctx, entity):
    ctx = api_ctx
    history(ctx, strategy='dry_run')
    table = ENTITIES[entity][0]
    before = count(ctx, table)
    rows = [row_for(entity), row_for(entity)]
    from modules.data_migration.catalog import get_entity
    required = get_entity(entity).required_fields()[0]
    rows[1] = {**rows[1], required: ''}
    payload = body(ctx, entity, 'json', rows)
    status, preview = request(ctx, '/api/data-migration/run', {**payload, 'strategy': 'dry_run'})
    assert status == 200 and preview['preview']['blocking'], preview
    assert any(d.get('row') == 2 and d.get('field') for d in preview['preview']['diagnostics'])
    status, rejected = request(ctx, '/api/data-migration/run', payload)
    assert status == 400, rejected
    assert count(ctx, table) == before
    invalid_mapping = {**payload, 'mapping': {'unknown': 'company_id'}}
    status, rejected = request(ctx, '/api/data-migration/run', invalid_mapping)
    assert status == 400, rejected
    forged = {**payload, 'actor_user_id': ctx['actor']['id'] + 10000000}
    status, rejected = request(ctx, '/api/data-migration/run', forged)
    assert status == 403, rejected
    assert count(ctx, table) == before


@pytest.mark.parametrize('field', ['lote', 'manufacture_date', 'validade_fisica', 'physical_expiry_date', 'lot_code', 'expiry_source'])
def test_stock_cannot_silently_discard_physical_traceability(api_ctx, field):
    ctx = api_ctx
    history(ctx, strategy='dry_run')
    row = {**row_for('estoque'), field: '2030-01-01' if field != 'lote' else 'LOT-1'}
    payload = body(ctx, 'estoque', 'csv', [row])
    payload['mapping'].pop(field)  # ignoring the source column must still fail closed
    status, result = request(ctx, '/api/data-migration/run', {**payload, 'strategy': 'dry_run'})
    assert status == 200 and result['preview']['blocking'], result
    assert any(d.get('field') == field and d.get('row') == 1 for d in result['preview']['diagnostics'])
    status, result = request(ctx, '/api/data-migration/run', payload)
    assert status == 400, result
    assert count(ctx, 'stock_movements') == 0
    assert count(ctx, 'unit_epi_stock') == 0


def test_real_http_rbac_cross_tenant_idor_and_historical_read(api_ctx):
    from core.security import create_jwt_token
    ctx = api_ctx
    job = run(ctx)
    query = '?actor_user_id=' + str(ctx['actor']['id'])
    payload = body(ctx, 'unidades', 'csv', [row_for('unidades')])
    uid = scalar(ctx['conn'], "INSERT INTO users(username,password,full_name,role,company_id,active) "
                 "VALUES(%s,'x','Restricted','user',%s,1) RETURNING id", ('restricted-' + uuid.uuid4().hex, ctx['company_id']))
    ctx['conn'].commit()
    restricted = create_jwt_token({'id': uid, 'role': 'user', 'company_id': ctx['company_id']})
    status, result = request(ctx, '/api/data-migration/run', {**payload, 'actor_user_id': uid}, token=restricted)
    assert status == 403, result
    from tests_postgres.test_migration_journey_postgres import _valid_cnpj_from
    foreign_cid = scalar(ctx['conn'], "INSERT INTO companies(name,cnpj,logo_type) VALUES(%s,%s,'') RETURNING id",
                         ('Neighbor ' + uuid.uuid4().hex, _valid_cnpj_from(f'{uuid.uuid4().int % 10**12:012d}')))
    foreign_job = scalar(ctx['conn'], "INSERT INTO migration_jobs(company_id,entity,source_kind,strategy,status,started_at,created_at) "
                         "VALUES(%s,'unidades','csv','insert_only','completed','2020','2020') RETURNING id", (foreign_cid,))
    # Safe read compatibility: excluded historical metadata is not a new import.
    historical_job = scalar(ctx['conn'], "INSERT INTO migration_jobs(company_id,entity,source_kind,strategy,status,started_at,created_at) "
                         "VALUES(%s,'usuarios','csv','insert_only','completed','2020','2020') RETURNING id", (ctx['company_id'],))
    ctx['conn'].commit()
    status, result = request(ctx, f'/api/data-migration/jobs/{foreign_job}' + query)
    assert status == 404, result
    for operation in ('revert', 'homologate'):
        status, result = request(ctx, f'/api/data-migration/jobs/{foreign_job}/{operation}', {'actor_user_id': ctx['actor']['id']})
        assert status == 400, result
    status, result = request(ctx, f'/api/data-migration/jobs/{historical_job}' + query)
    assert status == 200 and result['job']['entity'] == 'usuarios', result
    status, result = request(ctx, f'/api/data-migration/jobs/{historical_job}/revert', {'actor_user_id': ctx['actor']['id']})
    assert status == 400 and 'excluída' in str(result), result
    assert scalar(ctx['conn'], 'SELECT status FROM migration_jobs WHERE id=%s', (job['job_id'],)) == 'completed'


def test_stock_reimport_preview_matches_zero_movement_result(api_ctx):
    ctx = api_ctx
    history(ctx, strategy='dry_run')
    row = row_for('estoque')
    run(ctx, 'estoque', [row])
    before = count(ctx, 'stock_movements')
    payload = body(ctx, 'estoque', 'csv', [row])
    payload['strategy'] = 'upsert'
    status, preview = request(ctx, '/api/data-migration/run', {**payload, 'strategy': 'dry_run', 'preview_strategy': 'upsert'})
    assert status == 200 and preview['preview']['will_skip'] == 1, preview
    assert preview['preview']['will_update'] == 0
    assert any(d['code'] == 'aggregate_stock_only' for d in preview['preview']['diagnostics'])
    status, result = request(ctx, '/api/data-migration/run', {**payload, 'preview_token': preview['preview']['preview_token']})
    assert status == 200 and result['totals']['skipped'] == 1, result
    assert result['preview_matches_result'], result
    assert count(ctx, 'stock_movements') == before


def test_stock_import_preserves_existing_tracked_lot_and_physical_dates(api_ctx):
    from datetime import datetime, timezone

    from epi_backend.db import row_to_dict
    from modules.stock.service import create_stock_item, upsert_unit_stock

    ctx = api_ctx
    history(ctx, strategy='dry_run')
    cid = ctx['company_id']
    unit = scalar(ctx['conn'], 'SELECT id FROM units WHERE company_id=%s', (cid,))
    epi = scalar(ctx['conn'], 'SELECT id FROM epis WHERE company_id=%s', (cid,))
    lot = scalar(ctx['conn'], 'INSERT INTO epi_stock_lots(company_id,epi_id,receipt_unit_id,receipt_key,'
        'receipt_source,lot_code,manufacture_date,physical_expiry_date,expiry_source,expiry_evidence,'
        'received_quantity,received_by_user_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1,%s) RETURNING id',
        (cid, epi, unit, uuid.uuid4().hex, 'manual', 'LOTE-ANTERIOR', '2020-01-01', '2027-01-01',
         'label', 'Synthetic label', ctx['actor']['id']))
    item = create_stock_item(ctx['conn'], cid, unit, epi, 'N/A', 'M', 'N/A', 1, 'E2E-' + uuid.uuid4().hex,
        None, 'LOTE-ANTERIOR', '2020-01-01', 'unit', '', '', ctx['actor']['id'], datetime.now(timezone.utc).isoformat())
    ctx['conn'].execute("UPDATE epi_stock_items SET lot_id=%s,physical_manufacture_date='2020-01-01',"
                       "physical_expiry_date='2027-01-01',expiry_source='label',expiry_evidence='Synthetic label' WHERE id=%s", (lot, item))
    upsert_unit_stock(ctx['conn'], cid, unit, epi, 1)
    ctx['conn'].commit()
    before = row_to_dict(ctx['conn'].execute('SELECT * FROM epi_stock_items WHERE id=%s', (item,)).fetchone())
    payload = body(ctx, 'estoque', 'csv', [row_for('estoque')])
    payload['strategy'] = 'upsert'
    status, result = request(ctx, '/api/data-migration/run', {**payload, 'strategy': 'dry_run', 'preview_strategy': 'upsert'})
    assert status == 200 and result['preview']['blocking'], result
    status, result = request(ctx, '/api/data-migration/run', payload)
    assert status == 400, result
    assert scalar(ctx['conn'], 'SELECT quantity FROM unit_epi_stock WHERE company_id=%s', (cid,)) == 1
    after = row_to_dict(ctx['conn'].execute('SELECT * FROM epi_stock_items WHERE id=%s', (item,)).fetchone())
    assert after == before
    assert count(ctx, 'epi_stock_lots') == 1 and count(ctx, 'stock_movements') == 0
