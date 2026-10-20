"""Importação de FORNECEDORES no Centro de Migração em PostgreSQL real (Fase 4).

Prova a reabilitação SEGURA: a empresa é gravada pelo motor genérico e um
`post_write` cria o vínculo por Unidade — nenhuma empresa entra disponível a
todas as Unidades (o motivo exato do bloqueio original, ADR-0002 §13.6). Cobre:

- criação de empresa (cnpj canônico, paridade com cadastro manual) + vínculo;
- disponibilidade restrita à Unidade escolhida (o buraco fechado);
- `unit_id` obrigatório (empresa sem Unidade não entra);
- idempotência: reimportar não duplica empresa nem vínculo;
- rollback físico (apaga vínculo e depois empresa, na ordem da FK);
- isolamento multi-tenant (Unidade de outro tenant não resolve).

DATABASE_URL precisa nomear um banco isolado — o bootstrap aplica o schema.
"""
import csv
import io
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
pytestmark = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL', '').startswith('postgres'),
    reason='Importação de fornecedores exige PostgreSQL real.',
)

CNPJ = '11.222.333/0001-81'


def scalar(conn, sql, params=()):
    from epi_backend.db import row_to_dict
    row = conn.execute(sql, params).fetchone()
    return next(iter(row_to_dict(row).values())) if row else None


def _cnpj_for(seed):
    from tests_postgres.test_migration_journey_postgres import _valid_cnpj_from
    return _valid_cnpj_from(f'{seed % 10**12:012d}')


@pytest.fixture(scope='module', autouse=True)
def schema():
    from core.bootstrap import init_db
    init_db()


@pytest.fixture
def ctx(schema):
    from core.database import get_connection
    c = get_connection()
    tag = uuid.uuid4().hex
    cid = scalar(c, "INSERT INTO companies(name,cnpj,logo_type) VALUES(%s,%s,'') RETURNING id",
                 ('Forn ' + tag, _cnpj_for(int(tag[:12], 16))))
    c.commit()
    state = {'conn': c, 'company_id': cid, 'actor': {'id': 0, 'full_name': 'QA', 'company_id': cid}}
    _run(state, 'unidades', [{'name': 'Unidade A', 'unit_type': 'base', 'city': 'Macaé'},
                             {'name': 'Unidade B', 'unit_type': 'base', 'city': 'Rio'}])
    yield state
    c.rollback()
    c.close()


def _run(ctx, entity, rows, strategy='insert_only'):
    from modules.data_migration.service import run_migration
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return run_migration(ctx['conn'], company_id=ctx['company_id'], entity=entity, source_kind='csv',
                         raw=stream.getvalue().encode(), mapping={k: k for k in rows[0]}, strategy=strategy,
                         actor=ctx['actor'], source_name='forn.csv')


def _forn(ctx, unit='Unidade A', legal='Alfa Servicos LTDA', cnpj=CNPJ, strategy='insert_only'):
    return _run(ctx, 'fornecedores',
                [{'unit_id': unit, 'legal_name': legal, 'cnpj': cnpj, 'company_kind': 'Terceirizada'}],
                strategy)


def _unit_id(ctx, name):
    return scalar(ctx['conn'], 'SELECT id FROM units WHERE company_id=%s AND name=%s', (ctx['company_id'], name))


def _company(ctx):
    from epi_backend.db import row_to_dict
    row = ctx['conn'].execute('SELECT * FROM outsourced_companies WHERE company_id=%s',
                              (ctx['company_id'],)).fetchone()
    return row_to_dict(row) if row else None


def _company_count(ctx):
    return scalar(ctx['conn'], 'SELECT count(*) FROM outsourced_companies WHERE company_id=%s', (ctx['company_id'],))


def _links(ctx):
    from epi_backend.db import row_to_dict
    return [row_to_dict(r) for r in ctx['conn'].execute(
        'SELECT outsourced_company_id, unit_id, local_status FROM outsourced_company_unit_links '
        'WHERE company_id=%s', (ctx['company_id'],)).fetchall()]


def test_import_creates_company_and_unit_link(ctx):
    job = _forn(ctx)
    assert job['applied'] and job['totals']['inserted'] == 1, job['totals']
    comp = _company(ctx)
    assert comp and comp['cnpj_normalized'] == '11222333000181'  # canônico (paridade manual)
    assert comp['company_kind'] == 'outsourced'                  # vocabulário controlado
    links = _links(ctx)
    assert len(links) == 1 and int(links[0]['unit_id']) == _unit_id(ctx, 'Unidade A')
    assert links[0]['local_status'] == 'active'


def test_imported_company_is_available_only_to_the_linked_unit(ctx):
    """O motivo exato do bloqueio original: sem vínculo a empresa ficaria
    disponível a TODAS as Unidades. Com o vínculo, só à escolhida."""
    from modules.outsourced_companies.service import is_outsourced_company_available_to_unit
    _forn(ctx, unit='Unidade A')
    comp = _company(ctx)
    assert is_outsourced_company_available_to_unit(ctx['conn'], comp, _unit_id(ctx, 'Unidade A')) is True
    assert is_outsourced_company_available_to_unit(ctx['conn'], comp, _unit_id(ctx, 'Unidade B')) is False


def test_missing_unit_blocks_and_never_writes(ctx):
    from modules.data_migration.service import MigrationValidationError
    with pytest.raises((MigrationValidationError, ValueError)):
        _run(ctx, 'fornecedores',
             [{'legal_name': 'Sem Unidade LTDA', 'cnpj': CNPJ, 'company_kind': 'Terceirizada'}], 'dry_run')
    ctx['conn'].rollback()
    assert _company(ctx) is None


def test_reimport_does_not_duplicate_the_company_or_link(ctx):
    _forn(ctx)
    job = _forn(ctx, strategy='upsert')  # mesma empresa (cnpj) → update, sem novo vínculo
    assert job['totals']['inserted'] == 0, job['totals']
    assert _company_count(ctx) == 1
    assert len(_links(ctx)) == 1  # vínculo não duplicado


def test_rollback_removes_the_link_and_the_company(ctx):
    from modules.data_migration.service import revert_job
    job = _forn(ctx)
    assert _company(ctx) and len(_links(ctx)) == 1
    revert_job(ctx['conn'], job['job_id'], ctx['company_id'], ctx['actor'])
    ctx['conn'].rollback()  # revert_job faz commit; limpa o snapshot da nossa txn
    assert _company(ctx) is None   # empresa apagada
    assert _links(ctx) == []       # vínculo apagado antes (ordem da FK)


def test_tenant_isolation_unit_from_another_company_does_not_resolve(ctx):
    from core.database import get_connection
    other = get_connection()
    try:
        tag = uuid.uuid4().hex
        bid = scalar(other, "INSERT INTO companies(name,cnpj,logo_type) VALUES(%s,%s,'') RETURNING id",
                     ('OutroF ' + tag, _cnpj_for(int(tag[:12], 16))))
        other.commit()
        s = {'conn': other, 'company_id': bid, 'actor': {'id': 0, 'full_name': 'B', 'company_id': bid}}
        _run(s, 'unidades', [{'name': 'Unidade Secreta B', 'unit_type': 'base', 'city': 'X'}])
    finally:
        other.close()
    preview = _forn(ctx, unit='Unidade Secreta B', strategy='dry_run')['preview']
    assert preview['blocking'] is True, preview
    assert _company(ctx) is None
