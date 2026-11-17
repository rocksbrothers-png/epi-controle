"""Pillow 13 e endurecimento dos três pontos que decodificam imagem no servidor.

Pontos cobertos: foto do EPI no portal (processo principal), OCR da etiqueta
de lote e worker de pré-visualização da Biblioteca de Segurança. Em todos, só
PNG/JPEG com assinatura real do tipo declarado chegam ao Pillow, e o Pillow só
tenta o decodificador desse tipo. Formatos disfarçados (TIFF, GIF, BMP, WEBP,
ICO, PDF) são recusados antes de qualquer decodificação.
"""
import base64
import io
import re
from pathlib import Path

import pytest
from PIL import Image

from epi_backend import image_signatures
from epi_backend import lot_label_ocr
from modules.safety_library import render_worker
from modules.safety_library.service import render_epi_photo

ROOT = Path(__file__).resolve().parents[1]


def _encode(image, fmt, **kwargs):
    buffer = io.BytesIO()
    image.save(buffer, format=fmt, **kwargs)
    return buffer.getvalue()


def _png(size=(4, 3), color='red'):
    return _encode(Image.new('RGB', size, color), 'PNG')


def _jpeg_with_orientation(size=(6, 2), orientation=6):
    exif = Image.Exif()
    exif[274] = orientation
    return _encode(Image.new('RGB', size, 'blue'), 'JPEG', exif=exif)


DISGUISED = {
    'TIFF': lambda: _encode(Image.new('RGB', (4, 4)), 'TIFF'),
    'GIF': lambda: _encode(Image.new('P', (4, 4)), 'GIF', comment=b'x' * 64),
    'BMP': lambda: _encode(Image.new('RGB', (4, 4)), 'BMP'),
    'WEBP': lambda: _encode(Image.new('RGB', (4, 4)), 'WEBP'),
    'ICO': lambda: _encode(Image.new('RGB', (16, 16)), 'ICO'),
    'PDF': lambda: b'%PDF-1.4\n%fake\n',
}


def _data_url(subtype, content):
    return f'data:image/{subtype};base64,' + base64.b64encode(content).decode()


# ── Dependência ──────────────────────────────────────────────────────────────

def test_requirements_pin_pillow_13_or_newer_below_14():
    lines = [line.strip() for line in (ROOT / 'requirements.txt').read_text(encoding='utf-8').splitlines()]
    pins = [line for line in lines if line.lower().startswith('pillow')]
    assert pins == ['Pillow>=13.0.0,<14']


def test_installed_pillow_is_patched_release():
    import PIL

    major = int(re.match(r'(\d+)', PIL.__version__).group(1))
    assert major >= 13, f'Pillow {PIL.__version__} ainda tem os avisos corrigidos na 13.0.0'


# ── Utilitário ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize('subtype,expected', [('png', 'PNG'), ('jpeg', 'JPEG'), ('jpg', 'JPEG'), ('JPG', 'JPEG'),
                                              ('gif', None), ('webp', None), ('svg+xml', None), ('', None), (None, None)])
def test_pillow_format_for_only_maps_png_and_jpeg(subtype, expected):
    assert image_signatures.pillow_format_for(subtype) == expected


@pytest.mark.parametrize('name', sorted(DISGUISED))
@pytest.mark.parametrize('declared', ['PNG', 'JPEG'])
def test_open_verified_rejects_disguised_formats(name, declared):
    with pytest.raises(ValueError, match='^erro$'):
        image_signatures.open_verified(DISGUISED[name](), declared, 'erro')


@pytest.mark.parametrize('declared', ['PNG', 'JPEG'])
def test_open_verified_rejects_real_signature_with_foreign_body(declared):
    signature = image_signatures.PNG_SIGNATURE if declared == 'PNG' else image_signatures.JPEG_SIGNATURE
    tiff_body = DISGUISED['TIFF']()
    with pytest.raises(ValueError, match='^erro$'):
        image_signatures.open_verified(signature + tiff_body, declared, 'erro')


def test_open_verified_rejects_cross_declared_type():
    with pytest.raises(ValueError):
        image_signatures.open_verified(_png(), 'JPEG', 'erro')
    with pytest.raises(ValueError):
        image_signatures.open_verified(_jpeg_with_orientation(), 'PNG', 'erro')


def test_open_verified_rejects_unknown_format_and_non_bytes():
    with pytest.raises(ValueError):
        image_signatures.open_verified(_png(), 'GIF', 'erro')
    with pytest.raises(ValueError):
        image_signatures.open_verified(None, 'PNG', 'erro')


def test_open_verified_accepts_real_png_and_jpeg():
    with image_signatures.open_verified(_png(), 'PNG', 'erro') as image:
        assert image.format == 'PNG' and image.size == (4, 3)
    with image_signatures.open_verified(_jpeg_with_orientation(), 'JPEG', 'erro') as image:
        assert image.format == 'JPEG'


# ── Foto do EPI (processo principal) ─────────────────────────────────────────

@pytest.mark.parametrize('name', sorted(DISGUISED))
@pytest.mark.parametrize('subtype', ['png', 'jpeg', 'jpg'])
def test_epi_photo_rejects_disguised_content(name, subtype):
    with pytest.raises(ValueError, match='Foto indisponível em formato seguro.'):
        render_epi_photo(_data_url(subtype, DISGUISED[name]()))


@pytest.mark.parametrize('subtype', ['gif', 'webp', 'tiff', 'svg+xml', 'bmp'])
def test_epi_photo_rejects_declared_types_outside_png_jpeg(subtype):
    with pytest.raises(ValueError):
        render_epi_photo(_data_url(subtype, _png()))


def test_epi_photo_png_is_sanitized_png_without_metadata():
    output = render_epi_photo(_data_url('png', _png((5, 7))))
    with Image.open(io.BytesIO(output)) as image:
        assert image.format == 'PNG' and image.size == (5, 7) and image.mode == 'RGB'
        assert not image.getexif()


def test_epi_photo_jpeg_keeps_exif_orientation():
    output = render_epi_photo(_data_url('jpeg', _jpeg_with_orientation((6, 2), orientation=6)))
    with Image.open(io.BytesIO(output)) as image:
        assert image.size == (2, 6)  # rotacionada pela orientação EXIF


def test_epi_photo_keeps_pixel_limit():
    big = _encode(Image.new('1', (3000, 3000)), 'PNG')  # 9 MP > 8 MP
    with pytest.raises(ValueError, match='Foto excede limite de pixels.'):
        render_epi_photo(_data_url('png', big))


def test_epi_photo_keeps_size_limit():
    raw = 'data:image/png;base64,' + 'A' * (8 * 1024 ** 2)
    with pytest.raises(ValueError, match='Foto indisponível em formato seguro.'):
        render_epi_photo(raw)


# ── OCR da etiqueta de lote ──────────────────────────────────────────────────

@pytest.fixture
def ocr_ready(monkeypatch):
    class Reached(Exception):
        pass

    monkeypatch.setattr(lot_label_ocr.engine, 'get_ocr_runtime_status', lambda: {'ready': True})

    def stop(_data_uri):
        raise Reached

    monkeypatch.setattr(lot_label_ocr.engine, '_decode_data_uri', stop)
    return Reached


@pytest.mark.parametrize('name', sorted(DISGUISED))
@pytest.mark.parametrize('subtype', ['png', 'jpeg'])
def test_lot_label_ocr_rejects_disguised_content_before_decoding(ocr_ready, name, subtype):
    with pytest.raises(ValueError, match='PNG ou JPEG'):
        lot_label_ocr.detect_lot_label_dates(_data_url(subtype, DISGUISED[name]()))


@pytest.mark.parametrize('value', ['', 'data:image/gif;base64,R0lGODlh', 'data:text/plain;base64,eA=='])
def test_lot_label_ocr_rejects_other_declared_types(ocr_ready, value):
    with pytest.raises(ValueError, match='PNG ou JPEG'):
        lot_label_ocr.detect_lot_label_dates(value)


def test_lot_label_ocr_real_png_reaches_the_ocr_engine(ocr_ready):
    with pytest.raises(ocr_ready):
        lot_label_ocr.detect_lot_label_dates(_data_url('png', _png()))


def test_lot_label_ocr_keeps_32_megapixel_limit(ocr_ready):
    big = _encode(Image.new('1', (6000, 6000)), 'PNG')  # 36 MP > 32 MP
    with pytest.raises(ValueError, match='32 megapixels'):
        lot_label_ocr.detect_lot_label_dates(_data_url('png', big))


# ── Worker de pré-visualização ───────────────────────────────────────────────

@pytest.mark.parametrize('name', sorted(DISGUISED))
@pytest.mark.parametrize('suffix', ['.png', '.jpg', '.jpeg'])
def test_preview_worker_rejects_disguised_content(tmp_path, name, suffix):
    (tmp_path / ('source' + suffix)).write_bytes(DISGUISED[name]())
    with pytest.raises(ValueError, match='Conteúdo não corresponde à imagem declarada.'):
        render_worker.render(tmp_path)


def test_preview_worker_rejects_png_signature_with_foreign_body(tmp_path):
    (tmp_path / 'source.png').write_bytes(image_signatures.PNG_SIGNATURE + DISGUISED['TIFF']())
    with pytest.raises(ValueError, match='Conteúdo não corresponde à imagem declarada.'):
        render_worker.render(tmp_path)


def test_preview_worker_renders_real_png(tmp_path):
    (tmp_path / 'source.png').write_bytes(_png((8, 5)))
    manifest = render_worker.render(tmp_path)
    assert manifest['renderer'] == 'safe-raster-v1'
    assert manifest['parts'][0]['pages'][0] == {'index': 0, 'width': 8, 'height': 5}
    assert (tmp_path / 'page-0-0.png').read_bytes().startswith(image_signatures.PNG_SIGNATURE)


def test_preview_worker_renders_real_jpeg_with_orientation(tmp_path):
    (tmp_path / 'source.jpg').write_bytes(_jpeg_with_orientation((6, 2), orientation=6))
    manifest = render_worker.render(tmp_path)
    page = manifest['parts'][0]['pages'][0]
    assert (page['width'], page['height']) == (2, 6)


def test_preview_worker_keeps_pixel_limit_source():
    source = Path(render_worker.__file__).read_text(encoding='utf-8')
    assert 'Image.MAX_IMAGE_PIXELS = 32_000_000' in source
    assert "formats=[expected]" in source


def test_no_unrestricted_image_open_in_server_code():
    """Toda abertura de imagem no servidor passa por formato explícito."""
    offenders = []
    for path in [ROOT / 'modules', ROOT / 'epi_backend', ROOT / 'core']:
        for file in path.rglob('*.py'):
            text = file.read_text(encoding='utf-8')
            for match in re.finditer(r'Image\.open\(([^\n]*)', text):
                if 'formats=' not in match.group(1):
                    offenders.append(f'{file.relative_to(ROOT)}: {match.group(0)[:80]}')
    assert offenders == []
