"""UBX-V5, Etapa 2 (Empresas) — Chromium: SPA real + API sintética interceptada; nunca abre banco.

Mesmo harness de scripts/browser/fix_nav_refresh.py (Fixture), com o
Administrador Master e empresas no bootstrap. Confere, nos 5 idiomas, que a
tela de Empresas continua funcionando com o código extraído para
modules/companies:

1. Lista, resumo e detalhes da empresa selecionada.
2. Editar leva ao cadastro com o formulário preenchido; gravar envia PUT
   /api/companies/<id> com os valores comerciais atuais e sem o Administrador
   Geral inicial, e limpa o formulário.
3. Cadastrar envia POST /api/companies com o Administrador Geral inicial.
   O status vai como '1'/'0' (nunca o texto traduzido da opção) — §15.4.
4. Inativar envia PUT com active=0 e a empresa inteira.

pip install playwright; playwright install chromium
python scripts/browser/ubx_companies.py --output /tmp/ubx-companies
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
COMPANIES = [
    {'id': 901, 'name': 'Empresa QA', 'legal_name': 'Empresa QA Ltda', 'cnpj': '11222333000181', 'active': 1,
     'license_status': 'active', 'plan_name': 'start', 'user_limit': 100, 'user_count': 3, 'available_slots': 97,
     'monthly_value': 500, 'contract_start': '2026-01-01', 'contract_end': '2026-12-31', 'commercial_notes': 'QA'},
    {'id': 902, 'name': 'Cliente Dois', 'legal_name': 'Cliente Dois SA', 'cnpj': '22333444000155', 'active': 1,
     'license_status': 'trial', 'plan_name': 'pro', 'user_limit': 10, 'user_count': 9, 'available_slots': 1,
     'near_limit': True, 'monthly_value': 0},
]


class Fixture(nav.Fixture):
    def __init__(self, *args):
        super().__init__(*args)
        self.actor['role'] = 'master_admin'
        self.permissions.extend(p for p in ('companies:view', 'companies:create', 'companies:update')
                                if p not in self.permissions)
        self.company_list = [dict(item) for item in COMPANIES]

    def route(self, route):
        request = route.request
        path = urlsplit(request.url).path
        if path == '/api/bootstrap':
            original = route.fulfill

            def fulfill(**kwargs):
                payload = kwargs.get('json') or {}
                payload.update(companies=self.company_list)
                kwargs['json'] = payload
                return original(**kwargs)
            route.fulfill = fulfill
            return super().route(route)
        if path == '/api/reports':
            # Relatório vazio no formato real: o fixture base devolve um payload
            # genérico, e renderReports quebraria ao montar o resumo.
            self.calls.append({'method': 'GET', 'path': path, 'query': urlsplit(request.url).query, 'body': None})
            return route.fulfill(json={'deliveries': [], 'total_quantity': 0, 'by_unit': {}, 'by_sector': {},
                                       'by_tipo_vinculo': {}, 'employee_fichas': []})
        match = re.fullmatch(r'/api/companies(?:/(\d+))?', path)
        if match and request.method in ('POST', 'PUT'):
            body = json.loads(request.post_data or '{}')
            self.calls.append({'method': request.method, 'path': path, 'query': urlsplit(request.url).query, 'body': body})
            if request.method == 'POST':
                self.company_list.append(dict(body, id=903))
            else:
                company = next(item for item in self.company_list if item['id'] == int(match.group(1)))
                company.update({k: v for k, v in body.items() if k != 'actor_user_id'})
            return route.fulfill(json={'ok': True})
        return super().route(route)


def writes(f, since):
    return [c for c in f.calls[since:] if c['method'] in ('POST', 'PUT') and c['path'].startswith('/api/companies')]


def company_list(f):
    f.view('empresas')
    f.tab('empresas', 'lista')
    expect(f.page.locator('#companies-table tr')).to_have_count(2)
    expect(f.page.locator('#companies-table')).to_contain_text('Cliente Dois')
    expect(f.page.locator('#companies-summary .summary-chip')).to_have_count(4)
    expect(f.page.locator('#companies-summary .summary-chip').first).to_contain_text('2')
    f.page.locator('[data-company-details="902"]').click()
    expect(f.page.locator('#company-details')).to_contain_text('Cliente Dois SA')


def company_edit(f):
    f.view('empresas')
    f.tab('empresas', 'lista')
    f.page.locator('[data-company-edit="902"]').click()
    form = f.page.locator('#company-form')
    expect(form.locator('[name="name"]')).to_have_value('Cliente Dois')
    expect(form.locator('[name="cnpj"]')).to_have_value('22333444000155')
    expect(form.locator('[name="active"]')).to_have_value('1')
    form.locator('[name="name"]').fill('Cliente Dois Renomeado')
    before = len(f.calls)
    form.locator('button[type="submit"]').click()
    f.page.wait_for_function('__EPI_APP_STATE__.companies.some(c=>c.name==="Cliente Dois Renomeado")')
    sent = writes(f, before)
    assert [(c['method'], c['path']) for c in sent] == [('PUT', '/api/companies/902')], sent
    body = sent[0]['body']
    assert body['actor_user_id'] == 7 and body['plan_name'] == 'pro' and body['user_limit'] == 10, body
    assert 'general_admin_email' not in body and 'general_admin_name' not in body, body
    # FIX-EMPRESAS-ACTIVE-V1 (antes: active='' — docs/UBX_APPJS_AUDITORIA.md §15.4): o seletor envia 1/0.
    # §15.4: o status sai como '1'/'0' em todos os idiomas (antes, data-i18n-value trocava o value das
    # opções pelo texto traduzido e o formulário enviava active=''; o backend real recusa).
    assert body['active'] == '1', body
    expect(form.locator('[name="id"]')).to_have_value('')


def company_create(f):
    f.view('empresas')
    f.tab('empresas', 'cadastro')
    form = f.page.locator('#company-form')
    form.locator('[name="name"]').fill('Nova QA')
    form.locator('[name="legal_name"]').fill('Nova QA Ltda')
    form.locator('[name="cnpj"]').fill('33444555000166')
    form.locator('[name="general_admin_email"]').fill('owner@nova.test')
    expect(form.locator('[name="active"]')).to_have_value('1')
    form.locator('[name="active"]').select_option('0')
    before = len(f.calls)
    form.locator('button[type="submit"]').click()
    f.page.wait_for_function('__EPI_APP_STATE__.companies.some(c=>c.name==="Nova QA")')
    sent = writes(f, before)
    assert [(c['method'], c['path']) for c in sent] == [('POST', '/api/companies')], sent
    body = sent[0]['body']
    assert body['general_admin_email'] == 'owner@nova.test' and body['plan_name'] == 'start', body
    assert body['general_admin_name'] == '', body
    assert body['active'] == '1', body  # FIX-EMPRESAS-ACTIVE-V1 (ver company_edit)
    assert body['active'] == '0', body  # §15.4: escolher "Inativa" envia '0', não o texto traduzido


def company_toggle(f):
    f.view('empresas')
    f.tab('empresas', 'lista')
    before = len(f.calls)
    f.page.locator('[data-company-toggle="902"]').click()
    f.page.wait_for_function('__EPI_APP_STATE__.companies.find(c=>c.id===902).active===0')
    sent = writes(f, before)
    assert [(c['method'], c['path']) for c in sent] == [('PUT', '/api/companies/902')], sent
    assert sent[0]['body']['active'] == 0 and sent[0]['body']['name'] == 'Cliente Dois', sent[0]['body']
    assert not f.dialogs, f.dialogs  # inativar não pede confirmação nem mostra alerta


SCENARIOS = [company_list, company_edit, company_create, company_toggle]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/ubx-companies-browser'))
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
