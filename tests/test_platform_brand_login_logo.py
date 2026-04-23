import pytest

from server_postgres import validate_login_logo_payload, validate_platform_brand_payload


def test_validate_login_logo_accepts_png_and_svg_only():
    png_payload = 'data:image/png;base64,AAA='
    svg_payload = 'data:image/svg+xml;base64,PHN2Zz48L3N2Zz4='
    assert validate_login_logo_payload(png_payload) == png_payload
    assert validate_login_logo_payload(svg_payload) == svg_payload


def test_validate_login_logo_rejects_jpg_and_jpeg():
    with pytest.raises(ValueError):
        validate_login_logo_payload('data:image/jpeg;base64,AAA=')
    with pytest.raises(ValueError):
        validate_login_logo_payload('data:image/jpg;base64,AAA=')


def test_platform_brand_payload_keeps_separate_logos():
    payload = validate_platform_brand_payload({
        'display_name': 'LIVA',
        'legal_name': 'LIVA LTDA',
        'cnpj': '24.940.022/0001-08',
        'logo_type': 'data:image/jpeg;base64,AAA=',
        'login_logo_type': 'data:image/png;base64,BBB=',
    })
    assert payload['logo_type'].startswith('data:image/jpeg')
    assert payload['login_logo_type'].startswith('data:image/png')
