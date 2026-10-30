"""UBX-V5, Etapa 2 (Unidades e CNPJ) — Chromium: SPA real + API sintética interceptada; nunca abre banco.

Mesmo harness de scripts/browser/fix_nav_refresh.py (Fixture), com CNPJs no
bootstrap. Confere, nos 5 idiomas, que a tela de CNPJs e a de Unidades
continuam funcionando com o código extraído para modules/legal-entities e
modules/units:

1. CNPJs: lista só os ativos, campo de empresa desabilitado fora do Master,
   editar preenche o formulário (inclusive a situação), "Novo CNPJ" volta a cadastrar; inativar pede confirmação e envia
   DELETE /api/legal-entities/<id> com o ator.
2. Unidades: a coluna de CNPJ aparece, o filtro por nome restringe a lista e
   editar preenche o formulário com o CNPJ vinculado sem sair da tela.

pip install playwright; playwright install chromium
python scripts/browser/ubx_units_legal_entities.py --output /tmp/ubx-units-legal-entities
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
LEGAL_ENTITIES = [
    dict(id=44, company_id=901, legal_name='Empresa QA', trade_name='QA Matriz', cnpj='11222333000181',
         entity_type='matriz', active=1, uf='RJ', municipality='Macaé'),
    dict(id=45, company_id=901, legal_name='Filial QA', trade_name='', cnpj='11222333000262',
         entity_type='filial', active=1),
    dict(id=46, company_id=901, legal_name='Antiga QA', cnpj='11222333000343', entity_type='filial', active=0),
]


class Fixture(nav.Fixture):
    def __init__(self, *args):
        super().__init__(*args)
        self.permissions.extend(p for p in ('legal_entities:view', 'legal_entities:create', 'legal_entities:update',
                                            'legal_entities:delete') if p not in self.permissions)
        self.legal_entities = [dict(item) for item in LEGAL_ENTITIES]
        for unit in self.units:
            unit.update(company_name='Empresa QA', city='Macaé')
        self.units[1].update(legal_entity_id=45, legal_entity_cnpj='11222333000262', legal_entity_name='Filial QA')

    def route(self, route):
        request = route.request
        path = urlsplit(request.url).path
        if path == '/api/bootstrap':
            original = route.fulfill

            def fulfill(**kwargs):
                payload = kwargs.get('json') or {}
                payload.update(legal_entities=self.legal_entities)
                kwargs['json'] = payload
                return original(**kwargs)
            route.fulfill = fulfill
            return super().route(route)
        if path == '/api/reports':
            # Relatório vazio no formato real: o fixture base devolve um payload
            # genérico, e renderReports quebraria ao montar o resumo.
            self.calls.append(dict(method='GET', path=path, query=urlsplit(request.url).query, body=None))
            return route.fulfill(json=dict(deliveries=[], total_quantity=0, by_unit={}, by_sector={},
                                           by_tipo_vinculo={}, employee_fichas=[]))
        match = re.fullmatch(r'/api/legal-entities/(\d+)', path)
        if match and request.method == 'DELETE':
            self.calls.append(dict(method='DELETE', path=path, query=urlsplit(request.url).query, body=None))
            entity = next(item for item in self.legal_entities if item['id'] == int(match.group(1)))
            entity['active'] = 0
            return route.fulfill(json=dict(ok=True))
        return super().route(route)


def rows(f, table):
    return f.page.locator(f'#{table} tr')


def cnpj_screen(f):
    f.view('cnpjs')
    f.tab('cnpjs', 'lista')
    table = rows(f, 'legal-entities-table')
    expect(table).to_have_count(2)
    expect(table.first).to_contain_text('11222333000181')
    expect(f.page.locator('[data-legal-entity-deactivate="46"]')).to_have_count(0)
    # Fora do Master a empresa não se escolhe: o campo mostra a da conta, desabilitado
    # (não vai no submit; o backend resolve pela sessão).
    company = f.page.locator('#legal-entity-company')
    expect(company).to_be_disabled()
    expect(company).to_have_value('901')
    f.page.locator('[data-legal-entity-edit="44"]').click()
    form = f.page.locator('#legal-entity-form')
    expect(form.locator('[name="cnpj"]')).to_have_value('11222333000181')
    expect(form.locator('[name="trade_name"]')).to_have_value('QA Matriz')
    expect(form.locator('[name="active"]')).to_have_value('1')
    expect(f.page.locator('#legal-entity-cancel-edit')).to_be_visible()
    assert f.page.locator('.view.active').get_attribute('id') == 'cnpjs-view', 'edit left the CNPJ screen'
    f.page.locator('#legal-entity-cancel-edit').click()
    expect(form.locator('[name="cnpj"]')).to_have_value('')
    expect(form.locator('[name="id"]')).to_have_value('')
    expect(f.page.locator('#legal-entity-cancel-edit')).to_be_hidden()


def cnpj_deactivate(f):
    f.view('cnpjs')
    f.tab('cnpjs', 'lista')
    before = len(f.calls)
    f.page.locator('[data-legal-entity-deactivate="45"]').click()
    f.page.wait_for_function('!__EPI_APP_STATE__.legalEntities.find(e=>e.id===45).active')
    deletes = [c for c in f.calls[before:] if c['method'] == 'DELETE']
    assert deletes == [dict(method='DELETE', path='/api/legal-entities/45', query='actor_user_id=7', body=None)], deletes
    assert any(d['type'] == 'confirm' and '11222333000262' in d['message'] for d in f.dialogs), f.dialogs
    expect(rows(f, 'legal-entities-table')).to_have_count(1)


def unit_screen(f):
    f.view('unidades')
    f.tab('unidades', 'lista')
    table = rows(f, 'units-table')
    expect(table).to_have_count(2)
    expect(f.page.locator('#units-table tr', has_text='Base Norte QA')).to_contain_text('11222333000262')
    f.page.locator('#units-filter-name').fill('norte')
    expect(table).to_have_count(1)
    f.page.locator('[data-unit-edit="6"]').click()
    form = f.page.locator('#unit-form')
    expect(form.locator('[name="name"]')).to_have_value('Base Norte QA')
    expect(form.locator('[name="legal_entity_id"]')).to_have_value('45')
    assert f.page.locator('.view.active').get_attribute('id') == 'unidades-view', 'unit edit left the screen'


SCENARIOS = [cnpj_screen, cnpj_deactivate, unit_screen]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/ubx-units-legal-entities-browser'))
    parser.add_argument('--locales', nargs='+', default=LOCALES)
    parser.add_argument('--scenarios', nargs='+', default=[s.__name__ for s in SCENARIOS])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(base.QuietHandler, directory=str(ROOT / 'static')))
    Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    results = []
    with sync_playwright() as playwright:
        options = dict(headless=True, args=['--no-sandbox'])
        if os.environ.get('CHROMIUM_EXECUTABLE'):
            options['executable_path'] = os.environ['CHROMIUM_EXECUTABLE']
        browser = playwright.chromium.launch(**options)
        for locale in args.locales:
            for scenario in [s for s in SCENARIOS if s.__name__ in args.scenarios]:
                context = browser.new_context(viewport=dict(width=1440, height=1000), service_workers='block', locale=locale)
                page = context.new_page()
                page.set_default_timeout(4000)
                fixture = Fixture(page, origin, locale)
                result = dict(locale=locale, scenario=scenario.__name__, status='passed')
                try:
                    fixture.open()
                    scenario(fixture)
                    assert page.evaluate('EpiI18n.lang') == locale, 'locale changed during scenario'
                    assert not fixture.errors, f'page errors: {fixture.errors}'
                except Exception as error:
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
