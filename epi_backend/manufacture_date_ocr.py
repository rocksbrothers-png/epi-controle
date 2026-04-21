import base64
import re
from datetime import datetime, timezone
from typing import Dict, List, Tuple

try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore
    import pytesseract  # type: ignore
    OCR_RUNTIME_AVAILABLE = True
except ModuleNotFoundError:
    cv2 = None
    np = None
    pytesseract = None
    OCR_RUNTIME_AVAILABLE = False


def _is_plausible_date(candidate: datetime) -> bool:
    lower = datetime(1990, 1, 1, tzinfo=timezone.utc)
    upper = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return lower <= candidate <= upper


def _normalize_date(day: int, month: int, year: int) -> str:
    try:
        candidate = datetime(year, month, day, tzinfo=timezone.utc)
    except ValueError:
        return ''
    if not _is_plausible_date(candidate):
        return ''
    return candidate.strftime('%Y-%m-%d')


def _resolve_2digit_year(year_2digits: int) -> int:
    return 2000 + year_2digits if year_2digits <= 49 else 1900 + year_2digits


def extract_date_candidates(raw_text: str) -> List[Dict[str, str]]:
    text = str(raw_text or '')
    patterns: List[Tuple[re.Pattern[str], str]] = [
        (re.compile(r'\b([0-3]?\d)[./-]([01]?\d)[./-]((?:19|20)\d{2})\b'), 'dmy4'),
        (re.compile(r'\b((?:19|20)\d{2})[./-]([01]?\d)[./-]([0-3]?\d)\b'), 'ymd4'),
        (re.compile(r'\b([0-3]?\d)[./-]([01]?\d)[./-](\d{2})\b'), 'dmy2'),
    ]
    candidates: List[Dict[str, str]] = []
    for regex, mode in patterns:
        for match in regex.finditer(text):
            token = match.group(0)
            if mode == 'dmy4':
                day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
            elif mode == 'ymd4':
                year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
            else:
                day, month = int(match.group(1)), int(match.group(2))
                year = _resolve_2digit_year(int(match.group(3)))
            normalized = _normalize_date(day, month, year)
            if normalized:
                candidates.append({'token': token, 'normalized': normalized})
    return candidates


def choose_best_date(candidates: List[Dict[str, str]]) -> str:
    if not candidates:
        return ''
    frequency: Dict[str, int] = {}
    for item in candidates:
        normalized = str(item.get('normalized') or '').strip()
        if not normalized:
            continue
        frequency[normalized] = frequency.get(normalized, 0) + 1
    if not frequency:
        return ''
    best = sorted(frequency.items(), key=lambda entry: (-entry[1], entry[0]))
    return best[0][0]


def _decode_data_uri(data_uri: str):
    if not str(data_uri or '').startswith('data:image/'):
        raise ValueError('Formato de imagem inválido. Envie data URL base64.')
    _, encoded = data_uri.split(',', 1)
    blob = base64.b64decode(encoded)
    frame = cv2.imdecode(np.frombuffer(blob, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError('Não foi possível decodificar a imagem enviada.')
    return frame


def _build_variants(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    blur = cv2.GaussianBlur(clahe, (3, 3), 0)
    otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    adaptive = cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        2,
    )
    return [gray, clahe, otsu, adaptive]


def detect_manufacture_date(image_data_uri: str) -> Dict[str, object]:
    if not OCR_RUNTIME_AVAILABLE:
        raise RuntimeError('OCR indisponível no servidor (faltam dependências OpenCV/Tesseract).')
    image = _decode_data_uri(image_data_uri)
    variants = _build_variants(image)
    configs = [
        '--oem 1 --psm 7 -c tessedit_char_whitelist=0123456789./-',
        '--oem 1 --psm 6 -c tessedit_char_whitelist=0123456789./-',
        '--oem 3 --psm 11 -c tessedit_char_whitelist=0123456789./-',
    ]

    raw_chunks: List[str] = []
    all_candidates: List[Dict[str, str]] = []
    confidences: List[float] = []

    for variant in variants:
        for config in configs:
            text = str(pytesseract.image_to_string(variant, lang='por+eng', config=config) or '').strip()
            if text:
                raw_chunks.append(text)
                all_candidates.extend(extract_date_candidates(text))
            data = pytesseract.image_to_data(
                variant,
                lang='por+eng',
                config=config,
                output_type=pytesseract.Output.DICT,
            )
            conf_values = [
                float(value) for value in (data.get('conf') or [])
                if str(value).strip() not in ('', '-1')
            ]
            if conf_values:
                confidences.append(sum(conf_values) / len(conf_values))

    best_date = choose_best_date(all_candidates)
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    return {
        'manufacture_date': best_date,
        'confidence': round(avg_conf, 2),
        'raw_text': '\n'.join(raw_chunks).strip(),
        'candidates': all_candidates,
    }
