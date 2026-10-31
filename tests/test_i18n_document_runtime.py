"""Locale-scoped new documents: original data, BRL and identifiers stay intact."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from email.message import EmailMessage
import re
import shutil
import subprocess
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest

from modules.i18n.presentation import DocumentLocaleUnavailable, Translator, request_locale
from modules.purchases.quotes_service import build_po_email, build_rfq_email

LOCALES = ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO']


def _text(tmp_path, content, name):
    executable = shutil.which('pdftotext')
    if not executable:
        pytest.skip('Install poppler-utils for independent PDF extraction')
    path = tmp_path / name
    path.write_bytes(content)
    return subprocess.run([executable, str(path), '-'], check=True, capture_output=True, text=True).stdout


def _spaces(text):
    return re.sub(r'\s+', ' ', text).strip()


@pytest.mark.parametrize('locale,prefix',list(zip(LOCALES,[
    'Solicitação de Cotação','Request for quotation','Solicitud de cotización','Demande de devis','Tilbudsforespørsel',
])))
def test_rfq_and_po_translate_new_output_without_changing_source_or_currency(tmp_path,locale,prefix):
    presentation = Translator(locale)
    quote={'id':17,'valid_until':'2026-05-02','notes':'Observação original {name} — sem tradução'}
    supplier={'name':'Fornecedor Aprovado'}
    request={'id':19}
    items=[{'epi_name':r'EPI original (A+B) \ modelo','ca':'00123','quantity_requested':7,
            'quantity_approved':7,'unit_measure':'par','unit_price':1234.56,'glove_size':'G','size':'N/A'}]
    order={'id':23,'po_number':'PO-ORIGINAL-0007','expected_delivery_date':'2026-05-02'}
    original=deepcopy((quote,supplier,request,items,order))
    subject,body,attachments=build_rfq_email(None,quote,supplier,request,items,locale=locale)
    assert subject.startswith(prefix)
    assert str(quote['id']) in subject and str(request['id']) in subject
    assert supplier['name'] in body and quote['notes'] in body
    assert presentation.date(quote['valid_until']) in body
    rfq_text=_text(tmp_path,attachments[0][1],'rfq.pdf')
    assert prefix in rfq_text
    assert items[0]['epi_name'] in rfq_text
    assert '00123' in rfq_text and 'CA' in rfq_text and not re.search(r'\bCE\b',rfq_text)
    po_subject,po_body,po_attachments=build_po_email(order,items,supplier['name'],locale=locale)
    assert order['po_number'] in po_subject
    assert presentation.money(1234.56) in po_body
    assert presentation.money(8641.92) in po_body
    assert presentation.date(order['expected_delivery_date']) in po_body
    assert 'BRL' in presentation.money(1234.56) or 'R$' in presentation.money(1234.56)
    po_text=_text(tmp_path,po_attachments[0][1],'po.pdf')
    assert order['po_number'] in po_text
    assert _spaces(presentation.money(8641.92)) in _spaces(po_text)
    assert '{' not in po_text and '?' not in po_text
    for filename,pdf in attachments+po_attachments:
        # Unicode MIME filenames are encoded by EmailMessage, never sent here.
        message=EmailMessage();message.set_content('Synthetic local fixture')
        message.add_attachment(pdf,maintype='application',subtype='pdf',filename=filename)
        assert list(message.iter_attachments())[0].get_filename()==filename
        assert message.as_bytes()
    assert (quote,supplier,request,items,order)==original


@pytest.mark.parametrize('locale',LOCALES)
def test_localized_wrapping_keeps_all_rfq_rows_in_multi_page_pdf(tmp_path,locale):
    items=[{'epi_name':f'ORIGINAL-ITEM-{index:03d} '+('long original model ' * 3),
            'ca':'00123','quantity_requested':2,'unit_measure':'par'} for index in range(120)]
    _,_,attachments=build_rfq_email(None,{'id':17},{'name':'Original supplier'},{'id':19},items,locale=locale)
    text=_text(tmp_path,attachments[0][1],'long-rfq.pdf')
    for index in range(120):
        assert f'ORIGINAL-ITEM-{index:03d}' in text
    assert text.count('\f')>=3


@pytest.mark.parametrize('header,query,expected',[
    ('fr-FR,en-GB;q=0.8','','fr-FR'),
    ('fr-FR;q=0,en-GB;q=0.8','','en-GB'),
    ('es-ES;q=0.2,nb-NO;q=0.9','','nb-NO'),
    ('de-DE,fr-FR;q=0.8','','fr-FR'),
    ('en-US','','en-US'),
    ('no_NO','','no_NO'),
    ('en-GB','?lang=fr-FR','fr-FR'),
    ('en-GB','?lang=../../secrets','en-GB'),
    ('invalid;q=NaN','','pt-BR'),
])
def test_request_language_is_whitelisted_and_does_not_consume_identity(header,query,expected):
    handler=SimpleNamespace(headers={'Accept-Language':header})
    assert request_locale(handler,urlparse('/api/document'+query))==expected
    assert handler.headers=={'Accept-Language':header}


def test_concurrent_document_locales_and_flutter_aliases_do_not_share_state():
    locales=LOCALES+['en_US','no_NO']
    def render(code):
        translator=Translator(code)
        return translator.t('documents.po.title',id='PO-001'),translator.money('1234.56'),translator.date('2026-05-02')
    expected={code:render(code) for code in locales}
    selected=locales*20
    with ThreadPoolExecutor(max_workers=10) as executor:
        actual=list(executor.map(render,selected))
    assert actual==[expected[code] for code in selected]
    assert Translator('en_US').format_locale=='en_US'
    assert Translator('no_NO').locale=='nb-NO'
    assert Translator('en_US').date('2026-05-02')!=Translator('en-GB').date('2026-05-02')
    assert Translator('fr-FR').date('2026-02-31')=='2026-02-31'
    assert Translator('fr-FR').date('2026-05-02-invalid')=='2026-05-02-invalid'
    assert Translator('fr-FR').measure('custom-original',3)=='custom-original'


def test_missing_document_catalogue_fails_before_building_output(monkeypatch,tmp_path):
    from modules.i18n import presentation
    presentation._catalogue.cache_clear()
    monkeypatch.setattr(presentation,'_CATALOGUES',tmp_path)
    try:
        with pytest.raises(DocumentLocaleUnavailable) as actual:
            build_po_email({'id':23},[], 'Original supplier',locale='fr-FR')
        assert actual.value.code=='DOCUMENT_LOCALE_UNAVAILABLE'
    finally:
        presentation._catalogue.cache_clear()


def test_partial_document_catalogue_does_not_send_portuguese_or_raw_key(monkeypatch):
    from modules.i18n import presentation
    monkeypatch.setattr(presentation,'_catalogue',lambda locale:{'locale':locale})
    with pytest.raises(DocumentLocaleUnavailable):
        build_po_email({'id':23},[], 'Original supplier',locale='fr-FR')


def test_currency_localization_keeps_existing_float_display_rounding_and_totals():
    item={'epi_name':'-Original','ca':'00123','quantity_approved':2,'unit_price':2.675}
    original=deepcopy(item)
    _,body,_=build_po_email({'id':23},[item],'Original supplier',locale='en-GB')
    assert '-Original' in body
    assert '2 x R$2.67 = R$5.35' in body
    assert Translator('en-GB').money(2.675)=='R$2.67'
    assert item==original
