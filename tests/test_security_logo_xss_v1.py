"""SECURITY-LOGO-XSS-V1 — logotipos não podem injetar HTML/atributos.

O logotipo é gravado como data URL e inserido em atributos src (app, tela de
login pública, ficha HTML servida na mesma origem). Antes, a validação só
conferia o prefixo `data:image/png` e um valor como
`data:image/png;base64,AAA" onerror="..."` era aceito e executava.

Cobre: validação ao gravar (logotipo, logotipo de login, favicon, marca da
plataforma, Minha Empresa, white-label de Empresas), saneamento na leitura
pública (/api/tenant/resolve) e na ficha HTML; e que logotipos legítimos
continuam aceitos e exibidos.
"""
import sqlite3

import pytest

import modules.companies.service as companies_service
from modules.commercial.service import (
    safe_image_data_url,
    validate_login_logo_payload,
    validate_logo_payload,
    validate_platform_brand_payload,
)
from modules.company_settings.service import validate_my_company_payload
from modules.ficha.service import render_ficha_epi_html_document
from modules.tenant.service import resolve_tenant_by_id

PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
JPEG = 'data:image/jpeg;base64,/9j/4AAQSkZJRg+abc='
JPG = 'data:image/jpg;base64,AAA='
SVG = 'data:image/svg+xml;base64,PHN2Zz48L3N2Zz4='

MALICIOUS = [
    'data:image/png;base64,AAA" onerror="alert(1)',                 # fecha o atributo src
    "data:image/png;base64,AAA' onerror='alert(1)",
    'data:image/png;base64,AAA"><script>alert(1)</script>',
    'data:image/png;base64,AAA onerror=alert(1)',                    # atributo sem aspas
    'data:image/svg+xml;utf8,<svg onload="alert(1)"></svg>',        # SVG não base64
    'data:image/svg+xml,<svg/onload=alert(1)>',
    'data:image/png;charset=utf-8;base64,AAA=',
    'data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==',   # outro tipo de conteúdo
    'data:image/gif;base64,R0lGODlhAQABAAAAACw=',
    'data:image/png;base64,',                                        # sem conteúdo
    'data:image/png;base64,AAA=\nonerror=alert(1)',
    'data:image/png;base64,AA=A',                                    # padding no meio
]


@pytest.mark.parametrize('value', [PNG, JPEG, JPG, SVG])
def test_logo_accepts_base64_image_data_urls(value):
    assert validate_logo_payload(value) == value
    assert validate_logo_payload(f'  {value}  ') == value
    assert safe_image_data_url(value) == value


@pytest.mark.parametrize('value', MALICIOUS)
def test_logo_rejects_malicious_or_malformed_data_urls(value):
    with pytest.raises(ValueError):
        validate_logo_payload(value)
    assert safe_image_data_url(value) == ''


@pytest.mark.parametrize('value', ['', None, '   '])
def test_logo_empty_means_default_logo(value):
    assert validate_logo_payload(value) == ''


@pytest.mark.parametrize('value', ['javascript:alert(1)', 'https://evil.test/x.png', '"><img src=x onerror=alert(1)>', 'Logo'])
def test_logo_non_data_legacy_text_is_dropped(value):
    # Nunca foi exibido como imagem (o app mostra o logotipo padrão); não é gravado.
    assert validate_logo_payload(value) == ''


@pytest.mark.parametrize('value', [PNG, SVG])
def test_login_logo_accepts_png_and_svg(value):
    assert validate_login_logo_payload(value) == value


@pytest.mark.parametrize('value', MALICIOUS + [JPEG, JPG, 'javascript:alert(1)', 'Logo'])
def test_login_logo_rejects_everything_else(value):
    with pytest.raises(ValueError):
        validate_login_logo_payload(value)


def test_platform_brand_rejects_malicious_logo_and_keeps_legit():
    with pytest.raises(ValueError):
        validate_platform_brand_payload({'display_name': 'X', 'logo_type': MALICIOUS[0]})
    with pytest.raises(ValueError):
        validate_platform_brand_payload({'display_name': 'X', 'login_logo_type': MALICIOUS[0]})
    brand = validate_platform_brand_payload({'display_name': 'X', 'logo_type': JPEG, 'login_logo_type': PNG})
    assert (brand['logo_type'], brand['login_logo_type']) == (JPEG, PNG)


@pytest.mark.parametrize('field', ['logo_type', 'favicon_type', 'login_logo_type'])
def test_my_company_rejects_malicious_images(field):
    with pytest.raises(ValueError):
        validate_my_company_payload(sqlite3.connect(':memory:'), {field: MALICIOUS[0]}, 1, {})


def test_my_company_keeps_legit_images():
    fields = validate_my_company_payload(sqlite3.connect(':memory:'),
                                         {'logo_type': JPEG, 'favicon_type': SVG, 'login_logo_type': PNG}, 1, {})
    assert (fields['logo_type'], fields['favicon_type'], fields['login_logo_type']) == (JPEG, SVG, PNG)


def test_company_whitelabel_validates_favicon_and_login_logo():
    # Antes o favicon era gravado sem nenhuma validação neste caminho.
    with pytest.raises(ValueError):
        companies_service.validate_company_whitelabel_payload({'favicon_type': MALICIOUS[0]})
    with pytest.raises(ValueError):
        companies_service.validate_company_whitelabel_payload({'login_logo_type': MALICIOUS[0]})
    payload = companies_service.validate_company_whitelabel_payload({'favicon_type': PNG, 'login_logo_type': SVG})
    assert (payload['favicon_type'], payload['login_logo_type']) == (PNG, SVG)


def _tenant_conn(**logos):
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT, slug TEXT, subdomain TEXT, custom_domain TEXT, "
        "logo_type TEXT, login_logo_type TEXT, favicon_type TEXT, primary_color TEXT, secondary_color TEXT, "
        "accent_color TEXT, default_language TEXT, institutional_message TEXT, contact_email TEXT, contact_phone TEXT, "
        "website TEXT, theme_json TEXT, active INTEGER, license_status TEXT)"
    )
    conn.execute('INSERT INTO companies (id, name, logo_type, login_logo_type, favicon_type, active) VALUES (1, ?, ?, ?, ?, 1)',
                 ('ACME', logos.get('logo', ''), logos.get('login', ''), logos.get('favicon', '')))
    return conn


def test_public_tenant_resolve_drops_values_stored_before_the_fix():
    # Valor já gravado (antes da validação estrita) não chega à tela de login pública.
    branding = resolve_tenant_by_id(_tenant_conn(logo=MALICIOUS[0], login=MALICIOUS[4], favicon=MALICIOUS[2]), 1)['branding']
    assert (branding['logo_type'], branding['login_logo_type'], branding['favicon_type']) == ('', '', '')


def test_public_tenant_resolve_keeps_legit_logos():
    branding = resolve_tenant_by_id(_tenant_conn(logo=JPEG, login=PNG, favicon=SVG), 1)['branding']
    assert (branding['logo_type'], branding['login_logo_type'], branding['favicon_type']) == (JPEG, PNG, SVG)
    # Logotipo de login só aceita PNG/SVG, como na gravação.
    assert resolve_tenant_by_id(_tenant_conn(login=JPEG), 1)['branding']['login_logo_type'] == ''


def _ficha(company):
    return render_ficha_epi_html_document(
        employee={'name': 'João', 'role_name': 'Operador', 'sector': 'Ops'}, company=company, unit={'name': 'Base'},
        deliveries=[], devolutions=[],
        config={'titulo': 'Ficha EPI', 'declaracao': 'D', 'observacoes': 'O', 'rastreabilidade': 'R-1'})


@pytest.mark.parametrize('value', MALICIOUS)
def test_ficha_html_never_injects_stored_malicious_logo(value):
    html = _ficha({'name': 'ACME', 'logo_type': value})
    assert 'onerror' not in html and '<script>alert' not in html and 'onload' not in html
    assert 'font-weight:bold;">ACME</div>' in html  # cai no nome da empresa


def test_ficha_html_keeps_legit_logo():
    html = _ficha({'name': 'ACME', 'logo_type': PNG})
    assert f'<img src="{PNG}" style="max-height:60px;max-width:180px;">' in html


def test_ficha_html_escapes_company_name_in_logo_fallback():
    # Escopo: o bloco do logotipo. Os demais campos de texto da ficha HTML seguem
    # sem escape (achado separado, registrado em docs/SECURITY_LOGO_XSS_V1.md).
    html = _ficha({'name': '<script>alert(1)</script>', 'logo_type': ''})
    assert 'font-weight:bold;">&lt;script&gt;alert(1)&lt;/script&gt;</div>' in html


# ── Cadastro/edição de Empresas (Administrador Master) ───────────────────────

def _company_payload(**extra):
    return {'name': 'Nova', 'legal_name': 'Nova Ltda', 'cnpj': '11.222.333/0001-81', 'plan_name': 'start',
            'user_limit': 10, 'license_status': 'active', 'active': 1, **extra}


@pytest.fixture
def company_settings(monkeypatch):
    from modules.commercial.service import default_commercial_settings
    monkeypatch.setattr(companies_service, 'get_commercial_settings', lambda _c: default_commercial_settings())
    monkeypatch.setattr(companies_service, 'count_company_users', lambda *_a, **_k: 0)
    return companies_service


@pytest.mark.parametrize('field', ['logo_type', 'login_logo_type', 'favicon_type'])
def test_company_create_rejects_malicious_images(company_settings, field):
    # Achado da auditoria: login_logo_type/favicon_type eram validados dentro de um
    # try/except que engolia o erro, e o valor bruto ia para o INSERT do cadastro.
    with pytest.raises(ValueError, match='Logotipo'):
        company_settings.validate_company_payload(sqlite3.connect(':memory:'), _company_payload(**{field: MALICIOUS[0]}), None)


def test_company_create_keeps_legit_images(company_settings):
    payload = company_settings.validate_company_payload(
        sqlite3.connect(':memory:'), _company_payload(logo_type=JPEG, login_logo_type=SVG, favicon_type=PNG), None)
    assert (payload['logo_type'], payload['login_logo_type'], payload['favicon_type']) == (JPEG, SVG, PNG)


def test_company_update_does_not_block_on_stored_legacy_image(company_settings):
    # Na edição as imagens são campos protegidos, restaurados do registro atual pela
    # rota; o app reenvia o logotipo gravado (companySavePayload/ativar/inativar).
    # Um valor antigo fora da regra não pode impedir o Master de editar ou suspender.
    payload = company_settings.validate_company_payload(
        sqlite3.connect(':memory:'), _company_payload(logo_type=MALICIOUS[0], login_logo_type=MALICIOUS[4],
                                                      favicon_type=MALICIOUS[2]), 901)
    assert (payload['logo_type'], payload['login_logo_type'], payload['favicon_type']) == ('', '', '')


# ── Valor já gravado reenviado pelos formulários ─────────────────────────────

@pytest.mark.parametrize('field', ['logo_type', 'favicon_type', 'login_logo_type'])
def test_my_company_resent_stored_legacy_image_does_not_block_saving(field):
    stored = 'data:image/svg+xml;utf8,<svg></svg>' if field != 'logo_type' else MALICIOUS[0]
    fields = validate_my_company_payload(sqlite3.connect(':memory:'), {field: stored, 'display_name': ' X '}, 1, {field: stored})
    assert fields[field] == stored  # mantido como está (a exibição o ignora); não é reescrito
    assert fields['display_name'] == 'X'


def test_my_company_new_malicious_image_still_rejected_even_with_stored_legacy():
    with pytest.raises(ValueError):
        validate_my_company_payload(sqlite3.connect(':memory:'), {'logo_type': MALICIOUS[1]}, 1, {'logo_type': MALICIOUS[0]})


def test_platform_brand_resent_stored_legacy_logo_does_not_block_saving():
    previous = {'logo_type': MALICIOUS[0], 'login_logo_type': MALICIOUS[4]}
    brand = validate_platform_brand_payload({'display_name': 'Y', 'logo_type': MALICIOUS[0], 'login_logo_type': MALICIOUS[4]}, previous)
    assert (brand['display_name'], brand['logo_type'], brand['login_logo_type']) == ('Y', MALICIOUS[0], MALICIOUS[4])
    with pytest.raises(ValueError):
        validate_platform_brand_payload({'display_name': 'Y', 'logo_type': MALICIOUS[1]}, previous)


def _meta_conn(brand):
    import json
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('CREATE TABLE app_meta (key TEXT PRIMARY KEY, value TEXT)')
    conn.execute("INSERT INTO app_meta (key, value) VALUES ('platform_brand', ?)", (json.dumps(brand),))
    return conn


def test_save_platform_brand_keeps_stored_legacy_logo_and_rejects_new_malicious():
    from modules.commercial.service import get_platform_brand, save_platform_brand
    conn = _meta_conn({'display_name': 'X', 'logo_type': MALICIOUS[0], 'login_logo_type': MALICIOUS[4]})
    saved = save_platform_brand(conn, {'display_name': 'Novo', 'logo_type': MALICIOUS[0], 'login_logo_type': MALICIOUS[4]})
    assert (saved['display_name'], saved['logo_type'], saved['login_logo_type']) == ('Novo', MALICIOUS[0], MALICIOUS[4])
    assert get_platform_brand(conn)['display_name'] == 'Novo'
    with pytest.raises(ValueError):
        save_platform_brand(conn, {'display_name': 'Novo', 'logo_type': MALICIOUS[1]})


def test_platform_brand_login_logo_keeps_png_svg_only_rule():
    with pytest.raises(ValueError):
        validate_platform_brand_payload({'display_name': 'X', 'login_logo_type': JPEG})
