"""FIX-EMPRESAS-ACTIVE-V1 — Chromium: SPA real + API sintética interceptada; nunca abre banco.

O campo Situação (`<select name="active">`) do formulário de Empresas tem de,
nos 5 idiomas:

1. Mostrar as opções traduzidas mantendo os valores 1 (ativa) e 0 (inativa).
2. Cadastrar com active=1 por padrão e com active=0 quando escolhido.
3. Ao editar, carregar o estado real da empresa — uma empresa inativa abre
   como Inativa (antes abria como Ativa) — e gravá-lo sem reativá-la.
4. Permitir trocar o estado na edição.

Reaproveita o fixture de scripts/browser/ubx_companies.py (Administrador Master).

pip install playwright; playwright install chromium
python scripts/browser/fix_empresas_active.py --output /tmp/fix-empresas-active
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

from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fix_colab_terc as base
import ubx_companies as companies

ROOT = base.ROOT
LOCALES = base.LOCALES
LABELS = {  # static/i18n/<idioma>.json: company.active / company.inactive
    locale: tuple(json.loads((ROOT / 'static/i18n' / f'{locale}.json').read_text())['company'][key] for key in ('active', 'inactive'))
    for locale in LOCALES
}


class Fixture(companies.Fixture):
    def __init__(self, *args):
        super().__init__(*args)
        # Empresa 902 inativa: o caso que a edição carregava errado.
        next(item for item in self.company_list if item['id'] == 902)['active'] = 0


def active_select(f):
    return f.page.locator('#company-form select[name="active"]')


def assert_options(f):
    options = active_select(f).locator('option')
    expect(options).to_have_count(2)
    values = options.evaluate_all('els => els.map(e => [e.value, e.textContent.trim()])')
    assert values == [['1', LABELS[f.locale][0]], ['0', LABELS[f.locale][1]]], values


def submit_and_get(f, method, path):
    before = len(f.calls)
    f.page.locator('#company-form button[type="submit"]').click()
    f.page.wait_for_function('__EPI_APP_STATE__.editingCompanyId === null')
    f.page.wait_for_timeout(200)
    sent = [c for c in companies.writes(f, before) if (c['method'], c['path']) == (method, path)]
    assert len(sent) == 1, companies.writes(f, before)
    assert not [d for d in f.dialogs if d['type'] == 'alert'], f.dialogs
    return sent[0]['body']


def fill_new(f, name):
    form = f.page.locator('#company-form')
    form.locator('[name="name"]').fill(name)
    form.locator('[name="legal_name"]').fill(f'{name} Ltda')
    form.locator('[name="cnpj"]').fill('33444555000166')
    form.locator('[name="general_admin_email"]').fill('owner@nova.test')


def create_default_active(f):
    f.view('empresas')
    f.tab('empresas', 'cadastro')
    assert_options(f)
    expect(active_select(f)).to_have_value('1')
    fill_new(f, 'Nova Ativa')
    assert submit_and_get(f, 'POST', '/api/companies')['active'] == '1'


def create_inactive(f):
    f.view('empresas')
    f.tab('empresas', 'cadastro')
    fill_new(f, 'Nova Inativa')
    active_select(f).select_option('0')
    assert submit_and_get(f, 'POST', '/api/companies')['active'] == '0'


def edit_active_keeps_active(f):
    f.view('empresas')
    f.tab('empresas', 'lista')
    f.page.locator('[data-company-edit="901"]').click()
    assert_options(f)
    expect(active_select(f)).to_have_value('1')
    assert active_select(f).evaluate('s => s.selectedOptions[0].textContent.trim()') == LABELS[f.locale][0]
    assert submit_and_get(f, 'PUT', '/api/companies/901')['active'] == '1'


def edit_inactive_keeps_inactive(f):
    f.view('empresas')
    f.tab('empresas', 'lista')
    f.page.locator('[data-company-edit="902"]').click()
    expect(active_select(f)).to_have_value('0')
    assert active_select(f).evaluate('s => s.selectedOptions[0].textContent.trim()') == LABELS[f.locale][1]
    assert submit_and_get(f, 'PUT', '/api/companies/902')['active'] == '0'


def edit_change_state(f):
    f.view('empresas')
    f.tab('empresas', 'lista')
    f.page.locator('[data-company-edit="901"]').click()
    active_select(f).select_option('0')
    assert submit_and_get(f, 'PUT', '/api/companies/901')['active'] == '0'
    f.page.wait_for_function('__EPI_APP_STATE__.companies.find(c => c.id === 901).active === "0"')
    f.view('empresas')  # a recarga pode trocar de tela (901 é a empresa do usuário)
    f.tab('empresas', 'lista')
    f.page.locator('[data-company-edit="901"]').click()
    expect(active_select(f)).to_have_value('0')  # a gravação anterior voltou como inativa
    f.view('empresas')
    f.tab('empresas', 'lista')
    f.page.locator('[data-company-edit="902"]').click()
    active_select(f).select_option('1')
    assert submit_and_get(f, 'PUT', '/api/companies/902')['active'] == '1'


SCENARIOS = [create_default_active, create_inactive, edit_active_keeps_active, edit_inactive_keeps_inactive, edit_change_state]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/fix-empresas-active-browser'))
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
