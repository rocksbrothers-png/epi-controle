"""Reproduções adversariais do fechamento: completar lacunas sem substituir fatos válidos."""
import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from test_est_v3_5_postmerge_receipt import server as _server_fixture
from test_est_v3_5_r3_lot_receipt_http import _enforce_jwt as _jwt_fixture
from test_stock_expiry_disposition_http import _pieces
from test_stock_lot_evidence_http import call, prove, unknown
from test_stock_manual_receipt_validity_http import post, seed

# O pytest descobre os objetos fixture nestes nomes; os imports são usados explicitamente.
server = _server_fixture
_enforce_jwt = _jwt_fixture
pytestmark = pytest.mark.skipif(not os.environ.get('DATABASE_URL', '').startswith('postgres'), reason='Requires private PostgreSQL.')


def correct(server, s, item, **changes):
    body = {'stock_item_id': item['id'], 'qr_code': item['qr_code_value'],
            'manufacture_date': '2020-01-01', 'size': 'M', 'evidence': 'Etiqueta física conferida',
            'justification': 'Completar lacunas da peça pelo QR', 'physical_confirmed': True}
    body.update(changes)
    return call(server, s, '/api/stock/items/physical-metadata', body)


@pytest.mark.parametrize('changes', [{'manufacture_date': '2021-01-01'}, {'size': 'G'}])
def test_known_manufacture_and_size_cannot_be_overwritten(server, changes):
    s = seed()
    assert post(server, s)[0] == 201
    before = _pieces(s['company'], s['epi'])
    status, response = correct(server, s, before[0], **changes)
    assert status == 400, response
    assert _pieces(s['company'], s['epi']) == before


def test_omitted_glove_category_is_preserved_while_filling_missing_date(server):
    from test_est_v3_5_r3_lot_receipt_http import _fresh
    s = seed()
    assert post(server, s, glove_size='9', size='9')[0] == 201
    item = _pieces(s['company'], s['epi'])[0]
    with _fresh() as c:
        c.execute("UPDATE epi_stock_items SET manufacture_date='',physical_manufacture_date=NULL WHERE id=?", (item['id'],))
        c.commit()
    status, response = correct(server, s, item, size='9')
    assert status == 200, response
    assert _pieces(s['company'], s['epi'])[0]['glove_size'] == '9'


@pytest.mark.parametrize('change', ['manufacture', 'size'])
def test_lot_regularization_cannot_replace_valid_piece_metadata(server, change):
    s = unknown(server)
    before = _pieces(s['company'], s['epi'])
    changes = {'manufacture_date': '2021-01-01'} if change == 'manufacture' else {'items': [{**s['items'][0], 'size': 'G'}]}
    status, response = prove(server, s, **changes)
    assert status == 400, response
    assert _pieces(s['company'], s['epi']) == before


def test_concurrent_conflicting_gap_fills_have_one_winner(server):
    from test_est_v3_5_r3_lot_receipt_http import _fresh
    s = unknown(server)
    item = _pieces(s['company'], s['epi'])[0]
    with _fresh() as c:
        c.execute("UPDATE epi_stock_items SET size='N/A',glove_size='N/A',uniform_size='N/A',"
                  "manufacture_date='',physical_manufacture_date=NULL WHERE id=?", (item['id'],))
        c.commit()
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda size: correct(server, s, item, size=size, manufacture_date='2025-01-21'), ['P', 'G']))
    assert sorted(status for status, _ in replies) == [200, 400], replies
    assert _pieces(s['company'], s['epi'])[0]['size'] in ('P', 'G')
