"""SECURITY-LOGO-XSS-V1 — Chromium: SPA real + API sintética interceptada; nunca abre banco.

Confere, nos 5 idiomas, que um logotipo malicioso gravado no banco (data URL
que fecha o atributo src e injeta onerror/onload) NÃO executa em nenhum ponto
onde o app mostra logotipos, e que um logotipo legítimo continua aparecendo:

1. Tela de login do tenant (tenant-init.js, /api/tenant/resolve — público).
2. Topo do app (empresa do usuário) e marca da plataforma (bootstrap).
3. Lista e detalhes de Empresas (Administrador Master).
4. Prévia de Minha Empresa nas Configurações (Administrador Geral).

O nome da empresa também entra no atributo alt; um nome com aspas não pode
injetar atributos.

pip install playwright; playwright install chromium
python scripts/browser/security_logo_xss.py --output /tmp/security-logo-xss
CHROMIUM_EXECUTABLE=/usr/bin/chromium seleciona um navegador já instalado.
"""
import argparse
import json
import os
import sys
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fix_colab_terc as base
import fix_nav_refresh as nav

ROOT = base.ROOT
LOCALES = base.LOCALES
# PNG 1x1 real: o logotipo legítimo tem de carregar (naturalWidth > 0).
LEGIT = ('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==')


def evil(tag):
    # Passa no filtro antigo (prefixo data:image/png) e fecha o atributo src.
    return f'data:image/png;base64,AAAA" onerror="window.__xss=(window.__xss||[]).concat(\'{tag}\')" x="'


EVIL_NAME = 'QA" onload="window.__xss=(window.__xss||[]).concat(\'alt\')" x="'


class Fixture(nav.Fixture):
    def __init__(self, *args, logo=None, login_logo=None, name='Empresa QA'):
        super().__init__(*args)
        self.logo = logo
        self.login_logo = login_logo
        self.company_name = name
        self.actor.update(company_name=name, company_cnpj='11.222.333/0001-81', logo_type=logo or '')

    def route(self, route):
        request = route.request
        path = urlsplit(request.url).path
        if path == '/api/tenant/resolve':
            if self.login_logo is None:
                return route.fulfill(json={'ok': False})
            return route.fulfill(json={'ok': True, 'tenant': {'id': 901, 'name': self.company_name},
                                       'branding': {'login_logo_type': self.login_logo, 'logo_type': ''},
                                       'i18n': {'default_language': ''}})
        if path == '/api/bootstrap':
            original = route.fulfill

            def fulfill(**kwargs):
                payload = kwargs.get('json') or {}
                payload.update(platform_brand={'display_name': self.company_name, 'logo_type': self.logo or '',
                                               'login_logo_type': ''},
                               companies=[{'id': 901, 'name': self.company_name, 'legal_name': 'Empresa QA Ltda',
                                           'cnpj': '11222333000181', 'active': 1, 'license_status': 'active',
                                           'plan_name': 'start', 'user_limit': 100, 'user_count': 3,
                                           'available_slots': 97, 'logo_type': self.logo or ''}])
                kwargs['json'] = payload
                return original(**kwargs)
            route.fulfill = fulfill
            return super().route(route)
        if path == '/api/reports':
            return route.fulfill(json={'deliveries': [], 'total_quantity': 0, 'by_unit': {}, 'by_sector': {},
                                       'by_tipo_vinculo': {}, 'employee_fichas': []})
        if path == '/api/my-company':
            return route.fulfill(json={'company': {'id': 901, 'name': self.company_name, 'logo_type': self.logo or '',
                                                   'favicon_type': '', 'login_logo_type': '', 'theme_json': '{}',
                                                   'primary_color': '#123456', 'plan_name': 'pro'}})
        if path == '/api/my-company/domains':
            return route.fulfill(json={'domains': []})
        return super().route(route)


def hits(f):
    return f.page.evaluate('window.__xss || []')


def logo_srcs(f, selector):
    return f.page.eval_on_selector_all(f'{selector} img', 'els => els.map(e => e.getAttribute("src"))')


def assert_no_injected_attributes(f, selector):
    attrs = f.page.eval_on_selector_all(
        f'{selector} img', 'els => els.flatMap(e => e.getAttributeNames().filter(n => !["class","src","alt"].includes(n)))')
    assert not attrs, f'atributos injetados em {selector}: {attrs}'


def login_page(f):
    # Página pública: o tenant-init.js aplica o logotipo antes de qualquer login.
    f.page.goto(f.origin + '/', wait_until='load')
    f.page.wait_for_function('document.readyState === "complete"')
    f.page.wait_for_timeout(300)
    assert_no_injected_attributes(f, '#login-brand-logo')
    if f.login_logo == LEGIT:
        expect(f.page.locator('#login-brand-logo img')).to_have_count(1)
        assert logo_srcs(f, '#login-brand-logo') == [LEGIT]
        f.page.wait_for_function('document.querySelector("#login-brand-logo img").naturalWidth > 0')


def app_logos(f):
    f.open()
    f.page.wait_for_timeout(200)
    for selector in ('#company-badge', '#platform-brand-logo'):
        assert_no_injected_attributes(f, selector)
    srcs = logo_srcs(f, '#company-badge') + logo_srcs(f, '#platform-brand-logo')
    assert srcs, 'nenhum logotipo renderizado no topo'
    if f.logo == LEGIT:
        assert set(srcs) == {LEGIT}, srcs
    else:
        assert LEGIT not in srcs and all(s.startswith('data:image/svg+xml;utf8,') for s in srcs), srcs


def companies(f):
    f.actor['role'] = 'master_admin'
    f.permissions.extend(p for p in ('companies:view', 'companies:update') if p not in f.permissions)
    f.open()
    f.view('empresas')
    f.tab('empresas', 'lista')
    expect(f.page.locator('#companies-table tr')).to_have_count(1)
    f.page.locator('[data-company-details="901"]').click()
    for selector in ('#companies-table', '#company-details'):
        assert_no_injected_attributes(f, selector)
    if f.logo == LEGIT:
        assert set(logo_srcs(f, '#companies-table') + logo_srcs(f, '#company-details')) == {LEGIT}


def my_company(f):
    f.actor['role'] = 'general_admin'
    f.permissions.extend(p for p in ('settings:view', 'company_settings:update') if p not in f.permissions)
    f.open()
    f.view('configuracao')
    f.tab('configuracoes', 'empresa')
    expect(f.page.locator('[data-mc-preview="logo_type"] img')).to_have_count(1)
    assert_no_injected_attributes(f, '#my-company-form')
    if f.logo == LEGIT:
        assert logo_srcs(f, '[data-mc-preview="logo_type"]') == [LEGIT]


# (cenário, logotipo do app, logotipo da tela de login, nome da empresa)
SCENARIOS = [
    ('login_malicioso', login_page, None, evil('login'), 'Empresa QA'),
    ('login_legitimo', login_page, None, LEGIT, 'Empresa QA'),
    ('topo_malicioso', app_logos, evil('topo'), None, EVIL_NAME),
    ('topo_legitimo', app_logos, LEGIT, None, 'Empresa QA'),
    ('empresas_malicioso', companies, evil('empresas'), None, EVIL_NAME),
    ('empresas_legitimo', companies, LEGIT, None, 'Empresa QA'),
    ('minha_empresa_malicioso', my_company, evil('minha-empresa'), None, EVIL_NAME),
    ('minha_empresa_legitimo', my_company, LEGIT, None, 'Empresa QA'),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/security-logo-xss-browser'))
    parser.add_argument('--locales', nargs='+', default=LOCALES)
    parser.add_argument('--scenarios', nargs='+', default=[s[0] for s in SCENARIOS])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(base.QuietHandler, directory=str(ROOT / 'static')))
    Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    results = []
    with sync_playwright() as playwright:
        options = {'headless': True, 'args': ['--no-sandbox']}
        if os.environ.get('CHROMIUM_EXECUTABLE'):
            options['executable_path'] = os.environ['CHROMIUM_EXECUTABLE']
        browser = playwright.chromium.launch(**options)
        for locale in args.locales:
            for name, scenario, logo, login_logo, company_name in [s for s in SCENARIOS if s[0] in args.scenarios]:
                context = browser.new_context(viewport={'width': 1440, 'height': 1000}, service_workers='block', locale=locale)
                page = context.new_page()
                page.set_default_timeout(4000)
                fixture = Fixture(page, origin, locale, logo=logo, login_logo=login_logo, name=company_name)
                result = {'locale': locale, 'scenario': name, 'status': 'passed'}
                try:
                    scenario(fixture)
                    page.wait_for_timeout(300)
                    assert hits(fixture) == [], f'XSS executou: {hits(fixture)}'
                    assert not fixture.errors, f'page errors: {fixture.errors}'
                except Exception as error:  # noqa: BLE001 — registra a falha do cenário e segue para o próximo
                    result.update(status='failed', error=str(error))
                finally:
                    try:
                        result['xss_hits'] = hits(fixture)
                    except Exception:  # noqa: BLE001 — página já fechada/erro de navegação
                        result['xss_hits'] = None
                    result.update(page_errors=fixture.errors, blocked_external_requests=fixture.external)
                    page.screenshot(path=str(args.output / f'{locale}-{name}.png'))
                    results.append(result)
                    print(f"{locale} {name}: {result['status']} xss={result['xss_hits']} {result.get('error', '')[:160]}", flush=True)
                    context.close()
        browser.close()
    server.shutdown()
    (args.output / 'results.json').write_text(json.dumps(results, indent=2, ensure_ascii=False) + '\n')
    return int(any(result['status'] != 'passed' for result in results))


if __name__ == '__main__':
    raise SystemExit(main())
