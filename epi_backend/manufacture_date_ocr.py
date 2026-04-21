import base64
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
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


def _resolve_tesseract_cmd() -> str:
    explicit = str(os.environ.get('TESSERACT_CMD') or '').strip()
    if explicit:
        return explicit
    by_path = shutil.which('tesseract')
    if by_path:
        return by_path
    for path in ('/usr/bin/tesseract', '/usr/local/bin/tesseract'):
        if Path(path).exists():
            return path
    return ''


def configure_tesseract_cmd() -> str:
    if not OCR_RUNTIME_AVAILABLE:
        return ''
    cmd = _resolve_tesseract_cmd()
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd
    return cmd


def get_ocr_runtime_status() -> Dict[str, object]:
    status: Dict[str, object] = {
        'python_dependencies_ready': OCR_RUNTIME_AVAILABLE,
        'tesseract_cmd': '',
        'tesseract_in_path': False,
        'tesseract_version_cli': '',
        'tesseract_version_python': '',
        'ready': False,
        'error': '',
    }
    if not OCR_RUNTIME_AVAILABLE:
        status['error'] = 'Dependências Python de OCR ausentes (opencv/numpy/pytesseract).'
        return status

    cmd = configure_tesseract_cmd()
    status['tesseract_cmd'] = cmd
    status['tesseract_in_path'] = bool(shutil.which('tesseract'))
    if not cmd:
        status['error'] = 'Tesseract OCR não encontrado no PATH.'
        return status

    try:
        cli = subprocess.run([cmd, '--version'], capture_output=True, text=True, check=True, timeout=5)
        status['tesseract_version_cli'] = str(cli.stdout or cli.stderr).splitlines()[0]
    except Exception as exc:
        status['error'] = f'Falha ao executar "tesseract --version": {exc}'
        return status

    try:
        status['tesseract_version_python'] = str(pytesseract.get_tesseract_version())
    except Exception as exc:
        status['error'] = f'pytesseract não conseguiu acessar o Tesseract: {exc}'
        return status

    status['ready'] = True
    return status


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


def _run_ocr_profile(image, config: str) -> Dict[str, object]:
    last_error = None
    data = None
    for lang in ('por+eng', 'eng'):
        try:
            data = pytesseract.image_to_data(
                image,
                lang=lang,
                config=config,
                output_type=pytesseract.Output.DICT,
            )
            break
        except Exception as exc:  # pragma: no cover - depende do runtime do Tesseract
            last_error = exc
    if data is None and last_error:
        raise RuntimeError(f'Falha no OCR para os idiomas configurados: {last_error}') from last_error

    words = [str(item).strip() for item in (data.get('text') or []) if str(item).strip()]
    text = ' '.join(words)
    conf_values = [
        float(value)
        for value in (data.get('conf') or [])
        if str(value).strip() not in ('', '-1')
    ]
    confidence = sum(conf_values) / len(conf_values) if conf_values else 0.0
    return {
        'text': text,
        'confidence': confidence,
        'candidates': extract_date_candidates(text),
    }


def detect_manufacture_date(image_data_uri: str) -> Dict[str, object]:
    runtime = get_ocr_runtime_status()
    if not runtime.get('ready'):
        raise RuntimeError(str(runtime.get('error') or 'OCR indisponível no servidor.'))

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
            result = _run_ocr_profile(variant, config)
            text = str(result.get('text') or '').strip()
            if text:
                raw_chunks.append(text)
            all_candidates.extend(result.get('candidates') or [])
            confidences.append(float(result.get('confidence') or 0.0))

            best_partial = choose_best_date(all_candidates)
            partial_hits = sum(1 for item in all_candidates if item.get('normalized') == best_partial)
            if best_partial and partial_hits >= 2:
                break

    best_date = choose_best_date(all_candidates)
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    return {
        'manufacture_date': best_date,
        'confidence': round(avg_conf, 2),
        'raw_text': '\n'.join(raw_chunks).strip(),
        'candidates': all_candidates,
        'runtime': runtime,
    }
