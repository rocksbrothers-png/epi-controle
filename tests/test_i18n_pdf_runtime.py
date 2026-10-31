"""Verify generated PDF glyphs through an independent text extractor."""
import shutil
import subprocess

import pytest

from core.pdf import build_pdf_document


@pytest.mark.parametrize('text', [
    'Aprovação brasileira (CA 123) — proteção',
    'Brazilian Approval Certificate (CA 123) — £10.00',
    'Protección individual — España, €10,00',
    'Équipement de protection — français, €10,00',
    'Personlig verneutstyr — fødselsnummer, æøå',
])
def test_pdf_preserves_supported_language_characters(tmp_path, text):
    extractor = shutil.which('pdftotext')
    if not extractor:
        pytest.skip('Install poppler-utils for PDF text extraction')
    document = tmp_path / 'document.pdf'
    document.write_bytes(build_pdf_document([[{'text': text}]]))
    result = subprocess.run([extractor, str(document), '-'], check=True,
                            capture_output=True, text=True)
    assert text in result.stdout


def test_rfq_rows_are_escaped_only_once(tmp_path):
    from modules.purchases.quotes_service import _pdf_lines

    extractor = shutil.which('pdftotext')
    if not extractor:
        pytest.skip('Install poppler-utils for PDF text extraction')
    text = r'Équipement (CA 123) — teste \ lote'
    document = tmp_path / 'rfq.pdf'
    document.write_bytes(build_pdf_document(_pdf_lines('RFQ', 'Teste', [text])))
    result = subprocess.run([extractor, str(document), '-'], check=True,
                            capture_output=True, text=True)
    assert text in result.stdout
