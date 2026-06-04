"""Rotas de internacionalização (i18n).

Serve arquivos de tradução JSON por idioma. Público (sem autenticação).
Suporta: pt-BR, en-GB, es-ES, fr-FR, nb-NO.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs

from epi_backend.config import BASE_DIR
from epi_backend.http_utils import send_json, structured_log

_I18N_DIR = Path(__file__).resolve().parent.parent.parent / 'static' / 'i18n'

_SUPPORTED: dict[str, str] = {
    'pt-BR': 'pt-BR.json',
    'pt':    'pt-BR.json',
    'en-GB': 'en-GB.json',
    'en':    'en-GB.json',
    'es-ES': 'es-ES.json',
    'es':    'es-ES.json',
    'fr-FR': 'fr-FR.json',
    'fr':    'fr-FR.json',
    'nb-NO': 'nb-NO.json',
    'nb':    'nb-NO.json',
    'no':    'nb-NO.json',
}

_FALLBACK = 'pt-BR'
_cache: dict[str, dict] = {}


def _load_translations(locale: str) -> dict:
    if locale in _cache:
        return _cache[locale]
    filename = _SUPPORTED.get(locale)
    if not filename:
        return {}
    path = _I18N_DIR / filename
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        _cache[locale] = data
        return data
    except Exception as exc:
        structured_log('warning', 'i18n.load_error', locale=locale, error=str(exc))
        return {}


# ── GET /api/i18n/{locale} ────────────────────────────────────────────────────

def handle_get_i18n(handler, parsed, payload, match):
    locale = (match.group(1) if match else '').strip()
    if not locale or locale not in _SUPPORTED:
        return send_json(handler, 400, {
            'ok': False,
            'error': f"Idioma '{locale}' não suportado.",
            'supported': sorted({k for k in _SUPPORTED if '-' in k}),
        })

    translations = _load_translations(locale)
    if not translations:
        fallback = _load_translations(_FALLBACK)
        return send_json(handler, 200, {
            'ok': True,
            'locale': _FALLBACK,
            'fallback': True,
            'translations': fallback,
        })

    return send_json(handler, 200, {
        'ok': True,
        'locale': locale,
        'fallback': False,
        'translations': translations,
    })


# ── GET /api/i18n ─────────────────────────────────────────────────────────────

def handle_get_i18n_list(handler, parsed, payload, match):
    """Lista idiomas disponíveis com metadados de localização."""
    languages = [
        {'code': 'pt-BR', 'name': 'Português', 'region': 'Brasil',  'flag': '🇧🇷', 'native': 'Português - Brasil'},
        {'code': 'en-GB', 'name': 'English',   'region': 'England', 'flag': '🇬🇧', 'native': 'English - England'},
        {'code': 'es-ES', 'name': 'Español',   'region': 'España',  'flag': '🇪🇸', 'native': 'Español - España'},
        {'code': 'fr-FR', 'name': 'Français',  'region': 'France',  'flag': '🇫🇷', 'native': 'Français - France'},
        {'code': 'nb-NO', 'name': 'Bokmål',    'region': 'Noreg',   'flag': '🇳🇴', 'native': 'Bokmål - Noreg'},
    ]
    return send_json(handler, 200, {'ok': True, 'languages': languages})


# ── Registro de rotas ─────────────────────────────────────────────────────────

def register_routes(router) -> None:
    router.register('GET', '/api/i18n', handle_get_i18n_list)
    router.register('GET', r'/api/i18n/([a-zA-Z]{2}(?:-[a-zA-Z]{2})?)', handle_get_i18n, regex=True)
