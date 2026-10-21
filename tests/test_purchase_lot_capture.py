"""Datas rotuladas distintas e prova física obrigatória na conferência."""
import base64

import pytest

from epi_backend.lot_label_ocr import extract_lot_dates
from modules.purchases.receipt_capture import (
    prepare_receipt_capture,
    validate_capture_budget,
)

FILE = {'filename': 'lote.png', 'mime': 'image/png', 'content_base64': base64.b64encode(b'\x89PNG\r\n\x1a\nproof').decode()}


@pytest.mark.parametrize('text', [
    'FAB 10/01/2024 VAL 15/05/2032', 'Fabricação: 2024-01-10 Validade: 2032-05-15',
    'MFG:10.01.2024 EXP:15.05.2032', 'PRODUCAO 10-01-2024 VENCIMENTO 15-05-2032'])
def test_expiry_can_be_future_and_is_not_manufacture(text):
    result = extract_lot_dates(text)
    assert result['manufacture_date'] == '2024-01-10'
    assert result['physical_expiry_date'] == '2032-05-15'
    assert result['review_required'] is True


@pytest.mark.parametrize('text', ['10/01/2024 15/05/2032', 'FAB 31/02/2024', 'FAB 01/01/2099', 'Validade 05/2032'])
def test_ambiguous_invalid_future_manufacture_and_incomplete_dates_are_not_guessed(text):
    result = extract_lot_dates(text)
    assert result['manufacture_date'] == result['physical_expiry_date'] == ''


def test_multiple_candidates_for_same_field_and_reversed_dates_require_manual_choice():
    assert extract_lot_dates('FAB 01/01/2024 FAB 02/02/2024')['manufacture_date'] == ''
    result = extract_lot_dates('FAB 05/05/2024 VAL 01/01/2023')
    assert result['manufacture_date'] == result['physical_expiry_date'] == ''
    assert len(result['candidates']) == 2


def test_ca_expiry_is_not_suggested_as_physical_validity():
    assert extract_lot_dates('VALIDADE CA 01/01/2032')['physical_expiry_date'] == ''
    assert extract_lot_dates('CA VALIDADE 01/01/2032')['physical_expiry_date'] == ''


def test_one_unlabelled_date_is_not_reused_for_both_fields():
    result = extract_lot_dates('FAB 01/01/2024 01/01/2030')
    assert result['manufacture_date'] == '2024-01-01' and result['physical_expiry_date'] == ''


def lot(**changes):
    return dict(capture_version=1, quantity=3, lot_code='REAL', manufacture_date='2024-01-10',
                manufacturer_validity_date='2032-05-15', expiry_source='label', evidence='Etiqueta REAL',
                evidence_file=FILE, physical_lot_confirmed=True, **changes)


def test_legacy_payload_and_unknown_new_payload_remain_supported():
    assert prepare_receipt_capture({'quantity': 1, 'manufacturer_validity_date': '2030-01-01'}) is None
    assert prepare_receipt_capture({'capture_version': 1, 'quantity': 1}) is None


def test_manufacture_only_keeps_expiry_unknown_and_preserves_file():
    proof = prepare_receipt_capture({**lot(), 'manufacturer_validity_date': ''})
    assert proof['physical_manufacture_date'] == '2024-01-10'
    assert proof['physical_expiry_date'] is None and proof['expiry_source'] == 'unknown'
    assert proof['file']['filename'] == 'lote.png' and 'SHA-256:' in proof['expiry_evidence']


@pytest.mark.parametrize('changes', [
    {'evidence_file': None}, {'physical_lot_confirmed': False}, {'lot_code': ''}, {'evidence': ''},
    {'expiry_source': 'catalog'}, {'manufacture_date': '2099-01-01'},
    {'manufacturer_validity_date': '2023-01-01'}, {'manufacture_date': 'not-a-date'},
    {'manufacturer_validity_date': '2030-02-31'}])
def test_invalid_capture_never_becomes_a_receipt_proof(changes):
    with pytest.raises(ValueError):
        prepare_receipt_capture({**lot(), **changes})


def test_expiry_equal_to_manufacture_and_expired_lot_are_valid_facts():
    proof = prepare_receipt_capture({**lot(), 'manufacturer_validity_date': '2024-01-10'})
    assert proof['physical_expiry_date'] == proof['physical_manufacture_date']


@pytest.mark.parametrize('quantity', [0, -1, True, 1.5, '2', 501])
def test_invalid_capture_quantities_and_request_limit(quantity):
    with pytest.raises(ValueError):
        validate_capture_budget([{'lots': [{**lot(), 'quantity': quantity}]}])


def test_captures_from_11_distinct_lots_exceed_one_request_budget():
    with pytest.raises(ValueError):
        validate_capture_budget([{'lots': [{**lot(), 'quantity': 1}] * 11}])
