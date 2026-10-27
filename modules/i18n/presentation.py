"""Request-scoped presentation for newly generated documents.

Reads the existing web catalogues. No database writes, persisted preference,
process-global locale, currency conversion or business validation lives here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from functools import lru_cache
import json
from pathlib import Path
import re
from urllib.parse import parse_qs

from babel import Locale
from babel.dates import format_date
from babel.numbers import format_currency, format_decimal

_CATALOGUES = Path(__file__).resolve().parents[2] / 'static/i18n'
# Flutter's existing en_US uses the same English catalogue with US formatting.
_LOCALES = {
    'pt-br': ('pt-BR', 'pt_BR'), 'pt': ('pt-BR', 'pt_BR'),
    'en-gb': ('en-GB', 'en_GB'), 'en': ('en-GB', 'en_GB'),
    'en-us': ('en-GB', 'en_US'),
    'es-es': ('es-ES', 'es_ES'), 'es': ('es-ES', 'es_ES'),
    'fr-fr': ('fr-FR', 'fr_FR'), 'fr': ('fr-FR', 'fr_FR'),
    'nb-no': ('nb-NO', 'nb_NO'), 'nb': ('nb-NO', 'nb_NO'),
    'no-no': ('nb-NO', 'nb_NO'), 'no': ('nb-NO', 'nb_NO'),
}
_PLACEHOLDER = re.compile(r'\{(\w+)\}')


class DocumentLocaleUnavailable(ValueError):
    code = 'DOCUMENT_LOCALE_UNAVAILABLE'


def _spec(value):
    return _LOCALES.get(str(value or '').strip().replace('_', '-').lower())


def request_locale(handler, parsed=None):
    """Select only configured languages, without reading or changing identity."""
    query = parse_qs(getattr(parsed, 'query', '') or '')
    candidate = query.get('lang', [''])[0]
    if _spec(candidate):
        return candidate
    header = (getattr(handler, 'headers', None) or {}).get('Accept-Language', '')
    preferences = []
    for index, entry in enumerate(str(header).split(',')):
        parts = entry.strip().split(';')
        candidate = parts[0].strip()
        quality = 1.0
        for part in parts[1:]:
            if part.strip().startswith('q='):
                try:
                    quality = float(part.strip()[2:])
                except ValueError:
                    quality = 0.0
        if _spec(candidate) and 0 < quality <= 1:
            preferences.append((-quality, index, candidate))
    return min(preferences)[2] if preferences else 'pt-BR'


@lru_cache(maxsize=5)
def _catalogue(locale):
    try:
        with (_CATALOGUES / (locale + '.json')).open(encoding='utf-8') as source:
            value = json.load(source)
        if not isinstance(value, dict) or value.get('locale') != locale:
            raise ValueError('empty catalogue')
        return value
    except (OSError, ValueError) as error:
        raise DocumentLocaleUnavailable('Não foi possível carregar o idioma solicitado para o documento.') from error


def _lookup(catalogue, key):
    value = catalogue
    for part in key.split('.'):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _display(value):
    # Helvetica/WinAnsi supports NBSP and hyphen. Keep localized grouping/sign
    # without emitting unsupported CLDR narrow-NBSP or mathematical minus glyphs.
    return str(value).replace('\u202f', '\u00a0').replace('\u2212', '-')


@dataclass(frozen=True)
class Translator:
    requested_locale: str | None = 'pt-BR'

    @property
    def locale(self):
        return (_spec(self.requested_locale) or _LOCALES['pt-br'])[0]

    @property
    def format_locale(self):
        return (_spec(self.requested_locale) or _LOCALES['pt-br'])[1]

    def t(self, key, **params):
        value = _lookup(_catalogue(self.locale), key)
        if value is None:
            raise DocumentLocaleUnavailable('Não foi possível carregar o idioma solicitado para o documento.')
        if isinstance(value, dict):
            try:
                category = str(Locale.parse(self.format_locale).plural_form(Decimal(str(params['count'])).normalize()))
            except (KeyError, InvalidOperation, ValueError):
                category = 'other'
            value = value.get(category, value.get('other'))
        if not isinstance(value, str):
            raise DocumentLocaleUnavailable('Não foi possível carregar o idioma solicitado para o documento.')
        # One interpolation pass: original names/notes are never reinterpreted.
        display = dict(params)
        if 'count' in display:
            display['count'] = self.number(display['count'])
        return _PLACEHOLDER.sub(lambda match: str(display[match[1]]) if match[1] in display else match[0], value)

    def number(self, value):
        try:
            number = Decimal(str(value))
            if not number.is_finite():
                return str(value)
            return _display(format_decimal(number, locale=self.format_locale))
        except (InvalidOperation, ValueError, TypeError):
            return str(value)

    def money(self, value):
        try:
            # Existing document builders display floats with .2f. Preserve
            # that rounding before applying locale separators/currency marks.
            number = Decimal(format(value, '.2f')) if isinstance(value, float) else Decimal(str(value))
            if not number.is_finite():
                return str(value)
            return _display(format_currency(number, 'BRL', locale=self.format_locale))
        except (InvalidOperation, ValueError, TypeError):
            return str(value)

    def date(self, value):
        try:
            calendar_date = value.date() if isinstance(value, datetime) else value
            if not isinstance(calendar_date, date):
                raw = str(value)
                calendar_date = date.fromisoformat(raw) if len(raw) == 10 else datetime.fromisoformat(raw.replace('Z', '+00:00')).date()
            return format_date(calendar_date, format='short', locale=self.format_locale)
        except (ValueError, TypeError):
            return str(value or '')

    def measure(self, value, count):
        key = {'unidade': 'unit', 'un': 'unit', 'par': 'pair'}.get(value)
        return self.t('operationalAlerts.measure.' + key, count=count) if key else str(value or '')
