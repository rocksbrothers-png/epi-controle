"""Serviços de resolução de tenant (empresa) a partir de URL/host.

Permite que o frontend identifique automaticamente empresa, tema e idioma
antes mesmo do login, viabilizando o modelo White Label multiempresa.
"""

from __future__ import annotations

import json
import re
from urllib.parse import urlparse

from epi_backend.db import row_to_dict

_SUPPORTED_LANGUAGES = {'pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO'}
_LANGUAGE_FALLBACK = 'pt-BR'

_SELECT_TENANT = """
    SELECT
        id, name, slug, subdomain, custom_domain,
        logo_type, login_logo_type, favicon_type,
        primary_color, secondary_color, accent_color,
        default_language, institutional_message,
        contact_email, contact_phone, website,
        theme_json, active, license_status
    FROM companies
    WHERE active = 1
      AND license_status NOT IN ('suspended', 'expired')
"""


def _normalize_host(raw_host: str) -> str:
    """Remove porta e www. do host."""
    host = str(raw_host or '').strip().lower()
    host = host.split(':')[0]
    if host.startswith('www.'):
        host = host[4:]
    return host


def _extract_subdomain(host: str, base_domain: str) -> str | None:
    """Retorna o subdomínio se host terminar com .base_domain."""
    base = _normalize_host(base_domain)
    h = _normalize_host(host)
    if h.endswith('.' + base) and h != base:
        return h[: -(len(base) + 1)]
    return None


def resolve_tenant_by_host(connection, host: str, base_domain: str = 'epicontrole.com') -> dict | None:
    """Resolve tenant a partir do host HTTP.

    Ordem de busca:
    0. tenant_domains (tabela dedicada, apenas domínios verificados)
    1. custom_domain exato (coluna legada)
    2. subdomain (extraído do host)
    3. slug como primeiro segmento do path (passado via host)
    """
    normalized = _normalize_host(host)

    # 0. tabela dedicada de domínios (verificação CNAME/propriedade)
    from modules.tenant.domains_service import find_company_id_by_host
    company_id = find_company_id_by_host(connection, normalized, base_domain)
    if company_id:
        row = connection.execute(
            _SELECT_TENANT + " AND id = ? LIMIT 1",
            (int(company_id),),
        ).fetchone()
        if row:
            return _build_tenant_response(row, match_type='tenant_domain')

    # 1. custom_domain exato
    row = connection.execute(
        _SELECT_TENANT + " AND custom_domain = ? LIMIT 1",
        (normalized,),
    ).fetchone()
    if row:
        return _build_tenant_response(row, match_type='custom_domain')

    # 2. subdomain
    sub = _extract_subdomain(normalized, base_domain)
    if sub:
        row = connection.execute(
            _SELECT_TENANT + " AND subdomain = ? LIMIT 1",
            (sub,),
        ).fetchone()
        if row:
            return _build_tenant_response(row, match_type='subdomain')

    return None


def resolve_tenant_by_slug(connection, slug: str) -> dict | None:
    """Resolve tenant a partir do slug (path-based routing)."""
    clean = str(slug or '').strip().lower()
    if not clean:
        return None
    row = connection.execute(
        _SELECT_TENANT + " AND slug = ? LIMIT 1",
        (clean,),
    ).fetchone()
    if row:
        return _build_tenant_response(row, match_type='slug')
    return None


def resolve_tenant_by_id(connection, company_id: int) -> dict | None:
    """Resolve tenant a partir do company_id (uso interno/admin)."""
    row = connection.execute(
        """
        SELECT id, name, slug, subdomain, custom_domain,
               logo_type, login_logo_type, favicon_type,
               primary_color, secondary_color, accent_color,
               default_language, institutional_message,
               contact_email, contact_phone, website,
               theme_json, active, license_status
        FROM companies WHERE id = ? LIMIT 1
        """,
        (int(company_id),),
    ).fetchone()
    if row:
        return _build_tenant_response(row, match_type='id')
    return None


def _build_tenant_response(row, match_type: str = 'unknown') -> dict:
    d = row_to_dict(row)
    lang = str(d.get('default_language') or _LANGUAGE_FALLBACK)
    if lang not in _SUPPORTED_LANGUAGES:
        lang = _LANGUAGE_FALLBACK

    theme_raw = str(d.get('theme_json') or '{}')
    try:
        theme = json.loads(theme_raw)
    except Exception:
        theme = {}

    return {
        'tenant': {
            'id': d.get('id'),
            'name': d.get('name') or '',
            'slug': d.get('slug') or '',
            'subdomain': d.get('subdomain') or '',
            'custom_domain': d.get('custom_domain') or '',
        },
        'branding': {
            'logo_type': d.get('logo_type') or '',
            'login_logo_type': d.get('login_logo_type') or '',
            'favicon_type': d.get('favicon_type') or '',
            'primary_color': d.get('primary_color') or '#1565C0',
            'secondary_color': d.get('secondary_color') or '#42A5F5',
            'accent_color': d.get('accent_color') or '#FF6F00',
            'institutional_message': d.get('institutional_message') or '',
            'contact_email': d.get('contact_email') or '',
            'contact_phone': d.get('contact_phone') or '',
            'website': d.get('website') or '',
            'theme': theme,
        },
        'i18n': {
            'default_language': lang,
            'supported_languages': sorted(_SUPPORTED_LANGUAGES),
        },
        'match_type': match_type,
    }


def list_tenant_slugs(connection) -> list[dict]:
    """Lista todos os slugs/subdomínios ativos (para geração de sitemap/routing)."""
    rows = connection.execute(
        "SELECT id, name, slug, subdomain, custom_domain FROM companies "
        "WHERE active = 1 ORDER BY name ASC"
    ).fetchall()
    result = []
    for row in rows:
        d = row_to_dict(row)
        result.append({
            'id': d.get('id'),
            'name': d.get('name') or '',
            'slug': d.get('slug') or '',
            'subdomain': d.get('subdomain') or '',
            'custom_domain': d.get('custom_domain') or '',
        })
    return result


def validate_slug(slug: str) -> str:
    """Valida e normaliza um slug de empresa."""
    clean = str(slug or '').strip().lower()
    if not clean:
        raise ValueError('Slug não pode ser vazio.')
    if not re.match(r'^[a-z0-9][a-z0-9\-]{1,62}[a-z0-9]$', clean):
        raise ValueError(
            'Slug inválido. Use apenas letras minúsculas, números e hífens. '
            'Deve ter entre 3 e 64 caracteres e não pode começar ou terminar com hífen.'
        )
    return clean


def ensure_slug_unique(connection, slug: str, exclude_company_id: int | None = None) -> None:
    """Lança ValueError se o slug já estiver em uso por outra empresa."""
    query = "SELECT id FROM companies WHERE slug = ?"
    params: list = [slug]
    if exclude_company_id:
        query += " AND id != ?"
        params.append(exclude_company_id)
    row = connection.execute(query, params).fetchone()
    if row:
        raise ValueError(f"Slug '{slug}' já está em uso por outra empresa.")
