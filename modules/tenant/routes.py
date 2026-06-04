"""Rotas públicas de resolução de tenant e branding.

Estes endpoints são públicos (não requerem autenticação) pois são necessários
antes do login para carregar tema, idioma e logo da empresa.
"""

from __future__ import annotations

from contextlib import closing
from urllib.parse import parse_qs, urlparse

from core.database import get_connection
from core.rate_limit import get_client_ip, tenant_limiter
from epi_backend.http_utils import send_json, structured_log
from modules.tenant.service import (
    list_tenant_slugs,
    resolve_tenant_by_host,
    resolve_tenant_by_slug,
)


def _rate_check(handler):
    ip = get_client_ip(handler)
    if not tenant_limiter.is_allowed(ip):
        send_json(handler, 429, {'error': 'Muitas requisições. Aguarde e tente novamente.'})
        return False
    return True


# ── GET /api/tenant/resolve ───────────────────────────────────────────────────

def handle_get_tenant_resolve(handler, parsed, payload, match):
    if not _rate_check(handler):
        return
    qs = parse_qs(parsed.query or '')
    host = (qs.get('host') or [''])[0].strip()
    slug = (qs.get('slug') or [''])[0].strip()

    with closing(get_connection()) as connection:
        tenant = None
        if host:
            tenant = resolve_tenant_by_host(connection, host)
        if not tenant and slug:
            tenant = resolve_tenant_by_slug(connection, slug)
        if not tenant:
            # 200 com ok=false: ausência de tenant é um caso normal (host genérico),
            # não um erro. Evita poluir o console do navegador com 404.
            return send_json(handler, 200, {'ok': False, 'tenant': None})

        structured_log(
            'info',
            'tenant.resolved',
            match_type=tenant.get('match_type'),
            tenant_id=tenant.get('tenant', {}).get('id'),
            host=host or None,
            slug=slug or None,
        )
        return send_json(handler, 200, {'ok': True, **tenant})


# ── GET /api/tenant/branding ──────────────────────────────────────────────────

def handle_get_tenant_branding(handler, parsed, payload, match):
    if not _rate_check(handler):
        return
    qs = parse_qs(parsed.query or '')
    host = (qs.get('host') or [''])[0].strip()
    slug = (qs.get('slug') or [''])[0].strip()

    with closing(get_connection()) as connection:
        tenant = None
        if host:
            tenant = resolve_tenant_by_host(connection, host)
        if not tenant and slug:
            tenant = resolve_tenant_by_slug(connection, slug)
        if not tenant:
            return send_json(handler, 200, {'ok': False, 'branding': None})

        return send_json(handler, 200, {
            'ok': True,
            'branding': tenant.get('branding', {}),
            'i18n': tenant.get('i18n', {}),
            'tenant': {
                'id': tenant.get('tenant', {}).get('id'),
                'name': tenant.get('tenant', {}).get('name'),
                'slug': tenant.get('tenant', {}).get('slug'),
            },
        })


# ── GET /api/tenant/slugs ─────────────────────────────────────────────────────

def handle_get_tenant_slugs(handler, parsed, payload, match):
    """Lista slugs/subdomínios ativos. Usado para geração de rotas no frontend."""
    if not _rate_check(handler):
        return
    with closing(get_connection()) as connection:
        slugs = list_tenant_slugs(connection)
        return send_json(handler, 200, {'ok': True, 'tenants': slugs})


# ── Registro de rotas ─────────────────────────────────────────────────────────

def register_routes(router) -> None:
    router.register('GET', '/api/tenant/resolve', handle_get_tenant_resolve)
    router.register('GET', '/api/tenant/branding', handle_get_tenant_branding)
    router.register('GET', '/api/tenant/slugs', handle_get_tenant_slugs)
