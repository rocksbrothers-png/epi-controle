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


WINDOWS_TESSERACT_PATHS = [
    r"C:\Users\paraty.safoff\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]
LINUX_TESSERACT_PATHS = [
    '/usr/bin/tesseract',
    '/usr/local/bin/tesseract',
    '/opt/render/project/.apt/usr/bin/tesseract',
    '/opt/render/.apt/usr/bin/tesseract',
]


def _env_truthy(name: str, default: bool = False) -> bool:
    raw = str(os.environ.get(name, '')).strip().lower()
    if not raw:
        return default
    return raw in {'1', 'true', 'yes', 'on'}


def _is_render_environment() -> bool:
    return bool(os.environ.get('RENDER') or os.environ.get('RENDER_SERVICE_ID'))


def _resolve_tesseract_cmd() -> str:
    explicit = str(os.environ.get('TESSERACT_CMD') or '').strip()
    if explicit:
        if Path(explicit).exists():
            return explicit
        explicit_from_path = shutil.which(explicit)
        if explicit_from_path:
            return explicit_from_path

    by_path = shutil.which('tesseract')
    if by_path:
        return by_path

    if _is_render_environment() and Path('/usr/bin/tesseract').exists():
        return '/usr/bin/tesseract'

    if Path('/usr/bin/tesseract').exists():
        return '/usr/bin/tesseract'
    if Path('/usr/local/bin/tesseract').exists():
        return '/usr/local/bin/tesseract'

    if os.name == 'nt':
        possible_paths = WINDOWS_TESSERACT_PATHS
    else:
        possible_paths = LINUX_TESSERACT_PATHS

    for candidate in possible_paths:
        if Path(candidate).exists():
            return candidate

    return ''


def configure_tesseract_cmd() -> str:
    if not OCR_RUNTIME_AVAILABLE:
        return ''

    cmd = _resolve_tesseract_cmd()
    if not cmd:
        return ''

    cmd_dir = str(Path(cmd).parent)
    current_path = str(os.environ.get('PATH') or '')
    current_entries = current_path.split(os.pathsep) if current_path else []
    if cmd_dir and cmd_dir not in current_entries:
        os.environ['PATH'] = f'{cmd_dir}{os.pathsep}{current_path}' if current_path else cmd_dir

    pytesseract.pytesseract.tesseract_cmd = cmd
    return cmd


def configure_tesseract() -> Dict[str, object]:
    cmd = configure_tesseract_cmd()
    if cmd:
        return {'status': 'ok', 'path': cmd}
    return {'status': 'not_found', 'path': None}


TESSERACT_PATH = configure_tesseract_cmd()


def get_ocr_runtime_status() -> Dict[str, object]:
    ocr_required = _env_truthy('OCR_REQUIRED', default=_is_render_environment())
    status: Dict[str, object] = {
        'status': 'warning',
        'message': 'OCR não disponível neste ambiente (somente em produção).',
        'version': '',
        'path': '',
        'ocr_required': ocr_required,
        'python_dependencies_ready': OCR_RUNTIME_AVAILABLE,
        'tesseract_cmd': '',
        'tesseract_in_path': False,
        'tesseract_languages': [],
        'tesseract_has_por': False,
        'tesseract_version_cli': '',
        'tesseract_version_python': '',
        'ready': False,
        'error': '',
    }

    if not OCR_RUNTIME_AVAILABLE:
        status['status'] = 'error'
        status['message'] = 'Dependências Python de OCR ausentes (opencv/numpy/pytesseract).'
        status['error'] = status['message']
        status['erro'] = status['error']
        return status

    cmd = configure_tesseract_cmd()
    status['path'] = cmd
    status['tesseract_cmd'] = cmd
    status['tesseract_in_path'] = bool(shutil.which('tesseract') or (cmd and Path(cmd).exists()))
    if not cmd:
        status['error'] = 'Tesseract OCR não encontrado no sistema.'
        status['message'] = (
            'Tesseract não instalado neste ambiente.'
            if not ocr_required else
            'Tesseract OCR não encontrado no sistema.'
        )
        status['erro'] = status['error']
        return status

    try:
        cli = subprocess.run([cmd, '--version'], capture_output=True, text=True, check=True, timeout=5)
        status['tesseract_version_cli'] = str(cli.stdout or cli.stderr).splitlines()[0]
    except Exception as exc:
        status['status'] = 'error'
        status['message'] = f'Falha ao executar "tesseract --version": {exc}'
        status['error'] = status['message']
        status['erro'] = status['error']
        return status

    try:
        langs = subprocess.run([cmd, '--list-langs'], capture_output=True, text=True, check=True, timeout=5)
        lang_lines = [line.strip() for line in str(langs.stdout or '').splitlines() if line.strip()]
        parsed_langs = [line for line in lang_lines if not line.lower().startswith('list of available languages')]
        status['tesseract_languages'] = parsed_langs
        status['tesseract_has_por'] = 'por' in parsed_langs
    except Exception:
        status['tesseract_languages'] = []
        status['tesseract_has_por'] = False

    try:
        py_version = str(pytesseract.get_tesseract_version())
        status['version'] = py_version
        status['tesseract_version_python'] = py_version
    except Exception as exc:
        status['status'] = 'error'
        status['message'] = f'pytesseract não conseguiu acessar o Tesseract: {exc}'
        status['error'] = status['message']
        status['erro'] = status['error']
        return status

    status['status'] = 'ok'
    status['message'] = 'OCR pronto para uso.'
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


def preprocess_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    return thresh


def _build_variants(image):
    base = preprocess_image(image)
    blur = cv2.GaussianBlur(base, (3, 3), 0)
    otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    adaptive = cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        2,
    )
    return [base, blur, otsu, adaptive]


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
        return {
            'manufacture_date': '',
            'confidence': 0.0,
            'raw_text': '',
            'candidates': [],
            'runtime': runtime,
            'erro': str(runtime.get('error') or 'OCR indisponível no servidor.'),
        }

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

    try:
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
    except Exception as exc:
        return {
            'manufacture_date': '',
            'confidence': 0.0,
            'raw_text': '\n'.join(raw_chunks).strip(),
            'candidates': all_candidates,
            'runtime': runtime,
            'erro': 'Falha no OCR',
            'detalhe': str(exc),
        }

    best_date = choose_best_date(all_candidates)
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    return {
        'manufacture_date': best_date,
        'confidence': round(avg_conf, 2),
        'raw_text': '\n'.join(raw_chunks).strip(),
        'candidates': all_candidates,
        'runtime': runtime,
    }
