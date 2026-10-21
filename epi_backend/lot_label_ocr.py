"""Sugestões distintas de fabricação/validade; datas ambíguas exigem revisão."""
import re
import unicodedata
from datetime import datetime, timezone

from epi_backend import manufacture_date_ocr as engine

DATE = re.compile(r'(?<!\d)(?:(\d{4})[./-](\d{1,2})[./-](\d{1,2})|(\d{1,2})[./-](\d{1,2})[./-](\d{4}))(?!\d)')
LABEL = re.compile(r'\b(FAB(?:RICACAO)?|MFG|MANUFACTURED|MANUFACTURE|PRODUCAO|VALIDADE|VAL|VENC(?:IMENTO)?|EXP(?:IRY|IRATION)?)\b', re.IGNORECASE)


def extract_lot_dates(text):
    normalized = ''.join(c for c in unicodedata.normalize('NFKD', str(text or '')) if not unicodedata.combining(c)).upper()
    labels = list(LABEL.finditer(normalized))
    candidates = []
    for match in DATE.finditer(normalized):
        try:
            y, m, d = (int(match[i]) for i in (1, 2, 3)) if match[1] else (int(match[i]) for i in (6, 5, 4))
            value = datetime(y, m, d, tzinfo=timezone.utc).date()
        except ValueError:
            continue
        if not 1990 <= y <= 2099:
            continue
        # Só rótulo imediatamente anterior: outra data rompe a associação.
        before = [label for label in labels if label.end() <= match.start()]
        label = before[-1] if before else None
        between = normalized[label.end():match.start()] if label else ''
        kind = ''
        if label and len(between) <= 48 and not DATE.search(between) and not re.search(r'\bCA\b', normalized[max(0, label.start()-5):match.start()]):
            kind = 'expiry' if label[0].startswith(('VAL', 'VENC', 'EXP')) else 'manufacture'
        if kind == 'manufacture' and value > datetime.now(timezone.utc).date():
            kind = ''
        candidate = {'date': value.isoformat(), 'kind': kind}
        if candidate not in candidates:
            candidates.append(candidate)
    result = {'manufacture_date': '', 'physical_expiry_date': '', 'candidates': candidates, 'review_required': True}
    for kind, field in [('manufacture', 'manufacture_date'), ('expiry', 'physical_expiry_date')]:
        dates = {c['date'] for c in candidates if c['kind'] == kind}
        if len(dates) == 1:
            result[field] = dates.pop()
    if result['manufacture_date'] and result['physical_expiry_date'] and result['manufacture_date'] > result['physical_expiry_date']:
        result['manufacture_date'] = result['physical_expiry_date'] = ''
    return result


def detect_lot_label_dates(image_data):
    runtime = engine.get_ocr_runtime_status()
    if not runtime.get('ready'):
        return {**extract_lot_dates(''), 'error': 'OCR indisponível; informe as datas manualmente.'}
    import base64
    import io

    from PIL import Image

    with Image.open(io.BytesIO(base64.b64decode(image_data.split(',', 1)[1]))) as header:
        if header.width * header.height > 32_000_000:
            raise ValueError('Imagem excede 32 megapixels; envie uma foto aproximada da etiqueta.')
    image = engine._decode_data_uri(image_data)
    height, width = image.shape[:2]
    if max(height, width) > 2000:
        scale = 2000 / max(height, width)
        image = engine.cv2.resize(image, (max(1, int(width * scale)), max(1, int(height * scale))), interpolation=engine.cv2.INTER_AREA)
    chunks, confidence = [], []
    for variant in engine._build_variants(image)[:2]:
        for config in ['--oem 1 --psm 6', '--oem 1 --psm 11']:
            profile = engine._run_ocr_profile(variant, config)
            chunks.append(profile['text'])
            confidence.append(float(profile.get('confidence') or 0))
    return {**extract_lot_dates('\n'.join(chunks)), 'confidence': round(sum(confidence) / len(confidence), 2)}
