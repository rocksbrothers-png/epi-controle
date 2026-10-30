"""UBX-V5, Etapa 2 (Minha Empresa) — Chromium: SPA real + API sintética interceptada; nunca abre banco.

Mesmo harness de scripts/browser/fix_nav_refresh.py (Fixture), com o
Administrador Geral e `company_settings:update`. Confere, nos 5 idiomas, que a
aba Empresa das Configurações continua funcionando com o código extraído para
modules/my-company:

1. Carrega a empresa da sessão (GET /api/my-company), preenche o formulário
   (tema vindo de theme_json, cores), mostra o contrato somente leitura e grava
   com PUT /api/my-company (sem company_id; o backend deriva da sessão).
2. Domínios: lista, registra (POST), verifica (POST .../verify) e remove
   (DELETE com confirmação), recarregando a lista depois de cada ação.

pip install playwright; playwright install chromium
python scripts/browser/ubx_my_company.py --output /tmp/ubx-my-company
CHROMIUM_EXECUTABLE=/usr/bin/chromium seleciona um navegador já instalado.
"""
import argparse
import json
import os
import re
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
MY_COMPANY = {'id': 901, 'name': 'Empresa QA', 'legal_name': 'Empresa QA Ltda', 'cnpj': '11222333000181',
              'display_name': 'QA Display', 'primary_color': '#123456', 'secondary_color': '#42A5F5',
              'accent_color': '#FF6F00', 'theme_json': '{"mode":"dark"}', 'plan_name': 'pro', 'user_limit': 50,
              'license_status': 'active', 'logo_type': '', 'favicon_type': '', 'login_logo_type': ''}


class Fixture(nav.Fixture):
    def __init__(self, *args):
        super().__init__(*args)
        self.actor['role'] = 'general_admin'
        self.permissions.extend(p for p in ('settings:view', 'company_settings:update') if p not in self.permissions)
        self.company = dict(MY_COMPANY)
        self.domains = [{'id': 1, 'full_host': 'qa.epi.app', 'type_label': 'Subdomínio', 'domain_type': 'platform_subdomain',
                         'verification_status': 'verified', 'ssl_status': 'active', 'is_primary': 1}]

    def record(self, request, path, body=None):
        self.calls.append({'method': request.method, 'path': path, 'query': urlsplit(request.url).query, 'body': body})

    def route(self, route):
        request = route.request
        path = urlsplit(request.url).path
        body = json.loads(request.post_data or '{}') if request.method not in ('GET',) and request.post_data else None
        if path == '/api/reports':
            # Relatório vazio no formato real (o fixture base devolve um payload genérico).
            self.record(request, path)
            return route.fulfill(json={'deliveries': [], 'total_quantity': 0, 'by_unit': {}, 'by_sector': {},
                                       'by_tipo_vinculo': {}, 'employee_fichas': []})
        if path == '/api/my-company':
            self.record(request, path, body)
            if request.method == 'PUT':
                self.company.update({k: v for k, v in body.items() if k != 'actor_user_id'})
            return route.fulfill(json={'company': self.company})
        if path == '/api/my-company/domains':
            self.record(request, path, body)
            if request.method == 'POST':
                self.domains.append({'id': 2, 'full_host': body['domain'], 'type_label': 'Domínio próprio',
                                     'domain_type': body['domain_type'], 'verification_status': 'pending',
                                     'ssl_status': 'pending', 'is_primary': 0, 'cname_target': 'cname.epi.app',
                                     'txt_record': '_epi', 'verification_token': 'tok'})
                return route.fulfill(json={'ok': True})
            return route.fulfill(json={'domains': self.domains})
        match = re.fullmatch(r'/api/my-company/domains/(\d+)(?:/(verify|primary))?', path)
        if match:
            self.record(request, path, body)
            domain = next(item for item in self.domains if item['id'] == int(match.group(1)))
            if match.group(2) == 'verify':
                domain['verification_status'] = 'verified'
            elif request.method == 'DELETE':
                self.domains.remove(domain)
            return route.fulfill(json={'ok': True})
        return super().route(route)


def open_settings(f):
    f.view('configuracao')
    f.tab('configuracoes', 'empresa')
    form = f.page.locator('#my-company-form')
    expect(form.locator('[data-mc-field="name"]')).to_have_value('Empresa QA')
    return form


def settings_save(f):
    form = open_settings(f)
    expect(form.locator('[data-mc-field="theme_mode"]')).to_have_value('dark')
    expect(form.locator('[data-mc-field="primary_color"]')).to_have_value('#123456')
    expect(f.page.locator('#my-company-readonly')).to_contain_text('pro')
    form.locator('[data-mc-field="display_name"]').fill('  Novo Nome  ')
    before = len(f.calls)
    form.locator('button[type="submit"]').click()
    expect(f.page.locator('#my-company-feedback')).not_to_be_empty()
    puts = [c for c in f.calls[before:] if c['method'] == 'PUT' and c['path'] == '/api/my-company']
    assert len(puts) == 1, puts
    body = puts[0]['body']
    assert body['display_name'] == 'Novo Nome' and body['actor_user_id'] == 7, body
    assert body['theme_json'] == '{"mode":"dark"}' and 'company_id' not in body, body


def domains(f):
    open_settings(f)
    table = f.page.locator('#my-company-domains-table')
    expect(table.locator('tr')).to_have_count(1)
    f.page.locator('#my-company-domain-input').fill('  epi.cliente.com.br ')
    f.page.locator('#my-company-domain-type').select_option('custom_domain')
    before = len(f.calls)
    f.page.locator('#my-company-domain-add').click()
    expect(table.locator('tr')).to_have_count(2)
    posts = [c for c in f.calls[before:] if c['method'] == 'POST' and c['path'] == '/api/my-company/domains']
    assert len(posts) == 1 and posts[0]['body'] == {'actor_user_id': 7, 'domain': 'epi.cliente.com.br',
                                                     'domain_type': 'custom_domain'}, posts
    expect(f.page.locator('#my-company-domain-instructions')).to_contain_text('cname.epi.app')
    f.page.locator('[data-domain-verify="2"]').click()
    expect(f.page.locator('[data-domain-primary="2"]')).to_have_count(1)
    f.page.locator('[data-domain-delete="2"]').click()
    expect(table.locator('tr')).to_have_count(1)
    deletes = [c for c in f.calls[before:] if c['method'] == 'DELETE']
    assert [c['path'] for c in deletes] == ['/api/my-company/domains/2'], deletes
    assert any(d['type'] == 'confirm' for d in f.dialogs), f.dialogs


SCENARIOS = [settings_save, domains]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/ubx-my-company-browser'))
    parser.add_argument('--locales', nargs='+', default=LOCALES)
    parser.add_argument('--scenarios', nargs='+', default=[s.__name__ for s in SCENARIOS])
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
            for scenario in [s for s in SCENARIOS if s.__name__ in args.scenarios]:
                context = browser.new_context(viewport={'width': 1440, 'height': 1000}, service_workers='block', locale=locale)
                page = context.new_page()
                page.set_default_timeout(4000)
                fixture = Fixture(page, origin, locale)
                result = {'locale': locale, 'scenario': scenario.__name__, 'status': 'passed'}
                try:
                    fixture.open()
                    scenario(fixture)
                    assert page.evaluate('EpiI18n.lang') == locale, 'locale changed during scenario'
                    assert not fixture.errors, f'page errors: {fixture.errors}'
                except Exception as error:  # noqa: BLE001 — registra a falha do cenário e segue para o próximo
                    result.update(status='failed', error=str(error))
                finally:
                    result.update(calls=fixture.calls, dialogs=fixture.dialogs, page_errors=fixture.errors,
                                  blocked_external_requests=fixture.external)
                    page.screenshot(path=str(args.output / f'{locale}-{scenario.__name__}.png'))
                    results.append(result)
                    print(f"{locale} {scenario.__name__}: {result['status']} {result.get('error', '')[:200]}", flush=True)
                    context.close()
        browser.close()
    server.shutdown()
    (args.output / 'results.json').write_text(json.dumps(results, indent=2, ensure_ascii=False) + '\n')
    return int(any(result['status'] != 'passed' for result in results))


if __name__ == '__main__':
    raise SystemExit(main())
