"""EST-V3.5 (Validade e Bloqueios — opção 1): LISTA de peças pendentes de
regularização (validade física DESCONHECIDA), enriquecida para a UI web.

Mesmo predicado FÍSICO de ``pending_regularization_count`` — fatos da peça,
nunca catálogo. Somente leitura; a AÇÃO de regularizar continua exigindo
``stock:regularize_validity`` (ver ``test_est_v3_5_r2_rbac_http``). Roda só em
PostgreSQL isolado.
"""
import os
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL', '').startswith('postgres'),
    reason='exige PostgreSQL real.',
)

FUTURE = (date.today() + timedelta(days=365)).isoformat()
NOW = datetime.now(timezone.utc).isoformat()


@pytest.fixture(scope='module')
def conn():
    from core.bootstrap import init_db
    from core.database import get_connection
    init_db()
    c = get_connection()
    yield c
    c.close()


@pytest.fixture
def seed(conn):
    from modules.stock.service import create_stock_item, next_company_qr_sequence
    c = conn
    c.execute('SAVEPOINT pend')
    sfx = uuid4().hex
    company = c.execute('INSERT INTO companies(name,cnpj,logo_type) VALUES (?,?,?)',
                        ('P ' + sfx, sfx, 'text')).lastrowid
    unit = c.execute('INSERT INTO units(company_id,name,unit_type,city) VALUES (?,?,?,?)',
                     (company, 'U', 'base', 'T')).lastrowid
    other_unit = c.execute('INSERT INTO units(company_id,name,unit_type,city) VALUES (?,?,?,?)',
                           (company, 'U2', 'base', 'T')).lastrowid
    epi = c.execute('INSERT INTO epis(company_id,unit_id,name,purchase_code,ca,sector,unit_measure,'
                    'ca_expiry,epi_validity_date,manufacture_date,validity_days) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                    (company, unit, 'EPI', sfx, 'CA', 'S', 'un', '2030-01-01', FUTURE, '2020-01-01', 0)).lastrowid
    actor = c.execute('INSERT INTO users(username,password,full_name,role,company_id) VALUES (?,?,?,?,?)',
                      ('la_' + sfx, 'x', 'Local', 'admin', company)).lastrowid

    def piece(u=None):
        seqv = next_company_qr_sequence(c, company)
        qr = 'QR-' + uuid4().hex
        iid = create_stock_item(c, company, u or unit, epi, 'N/A', 'M', 'N/A', seqv, qr,
                                None, '', '', 'unit', '', '', actor, NOW)  # validade DESCONHECIDA
        return iid, qr

    yield dict(c=c, company=company, unit=unit, other_unit=other_unit, epi=epi, actor=actor, piece=piece)
    c.execute('ROLLBACK TO SAVEPOINT pend')
    c.execute('RELEASE SAVEPOINT pend')
    c.rollback()


def test_lists_only_unknown_pieces_enriched(seed):
    from epi_backend.db import row_to_dict
    from modules.stock.service import pending_regularization_items, regularize_item_physical_validity
    s = seed
    (a, _), (b, _) = s['piece'](), s['piece']()        # 2 peças com validade DESCONHECIDA
    (known, _) = s['piece']()
    item = row_to_dict(s['c'].execute('SELECT * FROM epi_stock_items WHERE id=?', (known,)).fetchone())
    regularize_item_physical_validity(s['c'], item, FUTURE, 'Laudo', 'x', s['actor'], 'Local', 'admin', NOW)
    rows = pending_regularization_items(s['c'], s['company'], s['unit'])
    assert {int(r['id']) for r in rows} == {a, b}      # só as desconhecidas; a regularizada saiu
    r = next(r for r in rows if int(r['id']) == a)
    assert r['qr_code_value'] and r['epi_name'] and int(r['unit_id']) == s['unit']  # enriquecido p/ UI


def test_scoped_by_unit(seed):
    from modules.stock.service import pending_regularization_items
    s = seed
    (a, _) = s['piece'](s['unit'])
    (bb, _) = s['piece'](s['other_unit'])
    assert {int(r['id']) for r in pending_regularization_items(s['c'], s['company'], s['unit'])} == {a}
    assert {int(r['id']) for r in pending_regularization_items(s['c'], s['company'], s['other_unit'])} == {bb}
    # sem unidade: toda a empresa
    assert {a, bb} <= {int(r['id']) for r in pending_regularization_items(s['c'], s['company'])}
