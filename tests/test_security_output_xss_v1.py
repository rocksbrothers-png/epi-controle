"""SECURITY-OUTPUT-XSS-V1 — dados de cadastro não viram HTML executável.

Cobre o lado servidor:
  - Ficha EPI em HTML (servida na mesma origem e guardada em snapshot): todo
    campo de registro sai escapado; a assinatura só entra como data URL base64
    de imagem; dados legítimos saem como antes.
  - CSP das rotas da ficha: nenhum script além do de impressão do arquivo
    (liberado por hash) — protege também snapshots gravados antes da correção.
  - Foto do EPI: só data URL base64 de imagem ao gravar; a foto já gravada
    reenviada pelo formulário não bloqueia a edição.
"""
import base64
import hashlib
import re
from pathlib import Path

import pytest

import modules.epis.service as epis_service
import modules.ficha.routes as routes
from modules.epis.service import validate_epi_photo_payload
from modules.ficha.service import render_ficha_epi_html_document
from tests.test_ficha_archive_view_print_export import (  # noqa: F401 — fixture reaproveitada
    _call,
    patched,
)

PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
EVIL = '<img src=x onerror=alert(1)>'
EVIL_IMAGE = 'data:image/png;base64,AAA" onerror="alert(1)'

CONFIG = {'titulo': 'Ficha EPI', 'declaracao': 'Declaro\nque recebi', 'observacoes': 'OBS', 'rastreabilidade': 'R-1'}


def _render(**overrides):
    data = dict(
        employee={'name': 'João', 'role_name': 'Operador', 'sector': 'Ops'},
        company={'name': 'ACME', 'cnpj': '11.222.333/0001-81', 'logo_type': ''},
        unit={'name': 'Base'}, deliveries=[], devolutions=[], config=dict(CONFIG))
    data.update(overrides)
    return render_ficha_epi_html_document(**data)


# ── Ficha HTML ────────────────────────────────────────────────────────────────

FIELDS = {
    'nome': dict(employee={'name': EVIL, 'role_name': 'x', 'sector': 'x'}),
    'função': dict(employee={'name': 'x', 'role_name': EVIL, 'sector': 'x'}),
    'setor': dict(employee={'name': 'x', 'role_name': 'x', 'sector': EVIL}),
    'empresa de origem': dict(employee={'name': 'x', 'tipo_vinculo': 'Terceirizado', 'empresa_origem': EVIL}),
    'empregador': dict(company={'name': EVIL, 'cnpj': '1', 'logo_type': PNG}),
    'cnpj': dict(company={'name': 'x', 'cnpj': EVIL}),
    'unidade': dict(unit={'name': EVIL}),
    'período': dict(period_label=EVIL),
    'título': dict(config={**CONFIG, 'titulo': EVIL}),
    'declaração': dict(config={**CONFIG, 'declaracao': EVIL}),
    'observações': dict(config={**CONFIG, 'observacoes': EVIL}),
    'rodapé': dict(config={**CONFIG, 'rastreabilidade': EVIL}),
    'epi': dict(deliveries=[{'epi_name': EVIL}]),
    'ca': dict(deliveries=[{'ca': EVIL}]),
    'unidade de medida': dict(deliveries=[{'unit_measure': EVIL}]),
    'datas': dict(deliveries=[{'delivery_date': EVIL, 'returned_date': EVIL, 'manufacture_date': EVIL}]),
    'devolução': dict(devolutions=[{'epi_name': EVIL, 'reason': EVIL, 'received_by_name': EVIL,
                                    'signature_name': EVIL, 'condition': EVIL, 'destination': EVIL}]),
}


@pytest.mark.parametrize('field', list(FIELDS))
def test_ficha_html_escapes_every_record_field(field):
    html = _render(**FIELDS[field])
    assert EVIL not in html and EVIL.upper() not in html, field
    # aparece como texto (a unidade de medida sai em maiúsculas)
    assert '&lt;img src=x onerror=alert(1)&gt;' in html or '&lt;IMG SRC=X ONERROR=ALERT(1)&gt;' in html, field


@pytest.mark.parametrize('value', [EVIL_IMAGE, 'data:image/svg+xml;utf8,<svg onload=alert(1)>',
                                   'javascript:alert(1)', 'assinado-por-token-123'])
def test_ficha_html_signature_never_injected(value):
    html = _render(deliveries=[{'epi_name': 'Luva', 'signature_data': value}])
    assert 'onerror' not in html and 'onload' not in html and '<img' not in html


def test_ficha_html_keeps_legit_signature_logo_and_text():
    html = _render(company={'name': 'ACME', 'cnpj': '11.222.333/0001-81', 'logo_type': PNG},
                   deliveries=[{'epi_name': 'Luva nitrílica', 'ca': '123', 'quantity': 2,
                                'delivery_date': '2026-01-02', 'signature_data': PNG}])
    assert f'<img src="{PNG}" style="max-height:28px;max-width:80px;">' in html
    assert f'<img src="{PNG}" style="max-height:60px;max-width:180px;">' in html
    assert '<td>Luva nitrílica</td>' in html and '>2026-01-02<' in html
    assert '<div class="declaracao">Declaro<br>que recebi</div>' in html  # quebra de linha preservada
    assert '<span>João</span>' in html and '<span>11.222.333/0001-81</span>' in html


def test_ficha_html_plain_data_output_unchanged_apart_from_special_chars():
    # Texto sem & < > " ' sai idêntico ao que era antes (snapshots novos iguais aos antigos).
    html = _render()
    assert '<title>Ficha EPI - João</title>' in html
    assert '<div class="titulo">Ficha EPI</div>' in html and '<div class="rodape">R-1</div>' in html


# ── CSP das rotas da ficha ────────────────────────────────────────────────────

def test_ficha_csp_allows_only_the_print_script_by_hash():
    csp = routes.FICHA_HTML_CSP
    digest = base64.b64encode(hashlib.sha256(routes._FICHA_PRINT_SCRIPT.encode()).digest()).decode()
    script_src = re.search(r"script-src ([^;]+)", csp).group(1).strip()
    assert script_src == f"'sha256-{digest}'"
    assert "'unsafe-inline'" not in script_src and "'unsafe-eval'" not in csp
    assert "default-src 'none'" in csp and 'img-src data:' in csp and "base-uri 'none'" in csp


@pytest.mark.parametrize('action', ['snapshot_view', 'snapshot_print', 'snapshot_export'])
def test_archive_routes_send_csp(patched, action):  # noqa: F811 — fixture importada
    handler = _call(action)
    assert handler.status == 200
    assert handler.sent_headers['Content-Security-Policy'] == routes.FICHA_HTML_CSP
    if action == 'snapshot_print':
        assert f'<script>{routes._FICHA_PRINT_SCRIPT}</script>'.encode() in handler.wfile.body


def test_all_ficha_html_routes_send_csp():
    source = Path(routes.__file__).read_text(encoding='utf-8')
    assert source.count("send_header('Content-Type', 'text/html; charset=utf-8')") == 3
    assert source.count("send_header('Content-Security-Policy', FICHA_HTML_CSP)") == 3


# ── Foto do EPI ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize('value', [PNG, 'data:image/jpeg;base64,/9j/4AAQ', 'data:image/webp;base64,UklGRg==',
                                   'data:image/svg+xml;base64,PHN2Zz48L3N2Zz4='])
def test_epi_photo_accepts_base64_images(value):
    assert validate_epi_photo_payload(value) == value


@pytest.mark.parametrize('value', [EVIL_IMAGE, 'x" onerror="alert(1)', 'javascript:alert(1)', 'https://evil.test/x.png',
                                   'data:text/html;base64,PHNjcmlwdD4=', 'data:image/svg+xml,<svg onload=alert(1)>',
                                   'data:image/png;base64,'])
def test_epi_photo_rejects_unsafe_values(value):
    with pytest.raises(ValueError):
        validate_epi_photo_payload(value)


def test_epi_photo_empty_clears_and_stored_legacy_does_not_block_edit():
    assert validate_epi_photo_payload('') == '' and validate_epi_photo_payload(None) == ''
    assert validate_epi_photo_payload(EVIL_IMAGE, stored=EVIL_IMAGE) == EVIL_IMAGE  # mantido; a exibição o ignora
    with pytest.raises(ValueError):
        validate_epi_photo_payload('x" onerror="y', stored=EVIL_IMAGE)  # valor novo segue a regra


def test_epi_create_and_update_call_photo_validation():
    source = Path(epis_service.__file__).read_text(encoding='utf-8')
    assert "payload['epi_photo_data'] = validate_epi_photo_payload(payload.get('epi_photo_data'))" in source
    assert "validate_epi_photo_payload(payload['epi_photo_data'], current.get('epi_photo_data'))" in source
