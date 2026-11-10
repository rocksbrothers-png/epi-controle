"""Ficha 360° de EPI — F1 (identificação e indicadores) — Chromium, 5 idiomas, desktop e mobile.

SPA real + API sintética interceptada (mesmo harness de scripts/browser/fix_colab_terc.py);
nunca abre banco. Confere, nos 5 idiomas:

1. A entrada pela linha do colaborador abre o painel com UMA requisição de resumo e mostra
   identificação, indicadores (com o detalhamento de pendências) e responsáveis vindos da API.
2. Blocos das fatias seguintes aparecem como indisponíveis, sem número nem valor monetário.
3. Terceirizado: empresa, CNPJ e contrato.
4. Estados: carregando, erro com "Tentar novamente", acesso negado (403/404).
5. Respostas obsoletas: trocar de colaborador antes da resposta anterior chegar nunca mostra
   o colaborador anterior; mudança de contexto (empresa do usuário) fecha a Ficha.
6. Escape e o botão Fechar fecham e devolvem o foco; navegar para outra tela fecha.
7. Perfil sem finance:view não vê cartões de custo; Admin Master não vê o botão.
8. Mobile (390 px): sem rolagem horizontal; cartões em duas colunas.

python scripts/browser/ubx_employee_ppe_360.py --output /tmp/ubx-employee-ppe-360
CHROMIUM_EXECUTABLE=/usr/bin/chromium seleciona um navegador já instalado.
"""
import argparse
import copy
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

ROOT = base.ROOT
LOCALES = base.LOCALES
SUMMARY_RE = re.compile(r'/api/employees/(\d+)/ppe-360/summary')


def summary_for(employee_id):
    contracted = employee_id == 32
    return {
        'employee': {
            'id': employee_id, 'name': 'Tito QA' if contracted else 'Ana QA', 'registration': f'QA-{employee_id}',
            'job_title': 'Tecnica', 'sector': 'Operacao',
            'employment_type': 'Terceirizado' if contracted else 'CLT', 'lifecycle': 'active',
            'company': {'id': 901, 'name': 'Empresa QA'},
            'unit': {'id': 5, 'name': 'Unidade QA', 'temporary_allocation': False, 'base_unit_name': ''},
            'legal_entity': None if contracted else {'name': 'Empresa QA', 'legal_name': 'Empresa QA Ltda', 'cnpj': '11.222.333/0001-81'},
            'contracted_workforce': {
                'outsourced_company': {'name': 'Terceira QA', 'legal_name': 'Terceira QA Ltda', 'cnpj': '44.555.666/0001-77'},
                'contract': {'ref': 'CT-QA-7', 'start_date': '2026-01-01', 'end_date': '2026-12-31', 'status': 'active'},
                'origin_name': ''} if contracted else None,
        },
        'responsibles': {
            'unit': [{'role': 'admin', 'name': 'Lucas Local'}, {'role': 'user', 'name': 'Gisele Gestora'}],
            'company': [{'role': 'general_admin', 'name': 'Gabriela Geral'}, {'role': 'registry_admin', 'name': 'Rafael Registro'}],
        },
        'indicators': {
            'pending_requests': {'total': 4, 'by_status': [{'code': 'SUBMITTED', 'count': 2}, {'code': 'UNDER_REVIEW', 'count': 1},
                                                           {'code': 'WAITING_STOCK', 'count': 1}]},
            'next_replacement': {'date': '2026-01-15', 'epi_name': 'Luva de vaqueta', 'overdue_count': 1},
            'in_use': {'units': 4, 'products': 3, 'categories': 2, 'uncategorized_products': 1},
        },
        'generated_at': '2026-11-09T12:00:00+00:00',
    }


class Fixture(base.Fixture):
    def __init__(self, *args):
        super().__init__(*args)
        self.permissions.extend(p for p in ('deliveries:view', 'finance:view') if p not in self.permissions)
        self.summary_status = None

    def open(self):
        super().open()
        # Atraso controlado da resposta do resumo, sem bloquear o Playwright:
        # envolve o apiFetch (o cliente único resolve globalThis.apiFetch na chamada).
        self.page.evaluate('''()=>{globalThis.__QA_DELAY__={};const original=globalThis.apiFetch;
          globalThis.apiFetch=async(path,options)=>{const m=/\\/employees\\/(\\d+)\\/ppe-360\\/summary/.exec(String(path));
            const ms=m?globalThis.__QA_DELAY__[m[1]]:0; if(ms){await new Promise(r=>setTimeout(r,ms));}
            return original(path,options);};}''')

    def delay(self, employee_id, ms):
        self.page.evaluate('([id,ms])=>{globalThis.__QA_DELAY__[id]=ms}', [employee_id, ms])

    def route(self, route):
        request = route.request
        match = SUMMARY_RE.fullmatch(urlsplit(request.url).path)
        if not match:
            return super().route(route)
        employee_id = int(match.group(1))
        self.calls.append(dict(method=request.method, path=urlsplit(request.url).path, query=urlsplit(request.url).query, body=None))
        if self.summary_status == 403:
            return route.fulfill(status=403, json={'ok': False, 'error': {'code': 'FORBIDDEN', 'message': 'Perfil sem permissão para esta consulta.'}})
        if self.summary_status == 404:
            return route.fulfill(status=404, json={'ok': False, 'error': {'code': 'EMPLOYEE_NOT_FOUND', 'message': 'Colaborador indisponível no seu escopo.'}})
        if self.summary_status == 500:
            return route.fulfill(status=500, json={'error': 'QA failure'})
        return route.fulfill(json={'ok': True, 'data': summary_for(employee_id)})

    def t(self, key):
        node = json.loads((ROOT / 'static/i18n' / f'{self.locale}.json').read_text(encoding='utf-8'))
        for part in key.split('.'):
            node = node[part]
        return node

    def summaries(self, since=0):
        return [c for c in self.calls[since:] if SUMMARY_RE.fullmatch(c['path'])]

    def open_colaboradores(self):
        self.view('colaboradores')
        self.tab('colaboradores', 'lista')
        expect(self.page.locator('#colaboradores-view [data-employee-ppe360="31"]')).to_be_visible()

    def modal(self):
        return self.page.locator('#employee-ppe-360-modal')

    def root(self):
        return self.page.locator('#employee-ppe-360-root')


def text_of(f):
    return f.root().inner_text()


def entry_and_content(f):
    f.open_colaboradores()
    button = f.page.locator('#colaboradores-view [data-employee-ppe360="31"]')
    expect(button).to_have_text(f.t('employee360.open'))
    before = len(f.calls)
    button.click()
    expect(f.modal()).to_be_visible()
    expect(f.root().locator('#ppe360-employee-name')).to_have_text('Ana QA')
    assert len(f.summaries(before)) == 1, f'uma requisição por abertura: {f.summaries(before)}'
    assert all(c['path'] == '/api/employees/31/ppe-360/summary' for c in f.summaries(before))
    other_api = [c['path'] for c in f.calls[before:] if not SUMMARY_RE.fullmatch(c['path'])]
    assert not other_api, f'requisições paralelas desnecessárias: {other_api}'
    body = text_of(f)
    for expected in ('QA-31', 'Tecnica', 'Unidade QA', 'Empresa QA', '11.222.333/0001-81', 'Luva de vaqueta',
                     'Lucas Local', 'Gisele Gestora', 'Gabriela Geral', 'Rafael Registro'):
        assert expected in body, expected
    # pendências: detalhamento por estado, com os rótulos traduzidos
    items = f.root().locator('.ppe360-breakdown li')
    expect(items).to_have_count(3)
    for code, count in (('SUBMITTED', 2), ('UNDER_REVIEW', 1), ('WAITING_STOCK', 1)):
        expect(f.root().locator(f'.ppe360-breakdown li[data-status="{code}"]')).to_have_text(f"{count} {f.t('employee360.requestStatus.' + code)}")
    expect(f.root().locator('[data-ppe360-card="pending"] .ppe360-card__value')).to_have_text('4')
    expect(f.root().locator('[data-ppe360-card="in-use"] .ppe360-card__value')).to_have_text('4')
    assert f.t('employee360.indicators.overdueOne') in body
    assert f.t('role.admin') in body and f.t('role.user') in body
    # finanças e fatias futuras: indisponíveis, sem número nem moeda
    for card in ('finance-total', 'finance-monthly', 'finance-forecast'):
        expect(f.root().locator(f'[data-ppe360-card="{card}"] .ppe360-card__value')).to_have_text(f.t('employee360.unavailable'))
    for block in f.root().locator('[data-ppe360-block]').all():
        assert not re.search(r'\d', block.inner_text()), f'bloco indisponível com número: {block.inner_text()}'
        assert block.get_attribute('aria-disabled') == 'true'
    assert f.root().locator('[data-ppe360-block]').count() == 10
    assert not re.search(r'R\$|€|£|kr\s?\d', body), 'nenhum valor monetário na F1'
    f.page.screenshot(path=str(f.evidence_dir / f'{f.locale}-desktop-ficha.png'), full_page=False)


def contracted(f):
    f.open_colaboradores()
    f.page.evaluate('()=>__EPI_EMPLOYEE_PPE_360_VIEW__.open(32)')
    expect(f.root().locator('#ppe360-employee-name')).to_have_text('Tito QA')
    body = text_of(f)
    for expected in ('Terceira QA', '44.555.666/0001-77', 'CT-QA-7'):
        assert expected in body, expected


def states(f):
    f.open_colaboradores()
    f.summary_status = 500
    f.delay(31, 600)
    f.page.locator('#colaboradores-view [data-employee-ppe360="31"]').click()
    expect(f.root().locator('.ppe360-state--loading')).to_be_visible()
    expect(f.root()).to_have_attribute('aria-busy', 'true')
    expect(f.root().locator('.ppe360-state--error')).to_be_visible()
    f.summary_status = None
    f.delay(31, 0)
    f.root().locator('[data-ppe360-action="retry"]').click()
    expect(f.root().locator('#ppe360-employee-name')).to_have_text('Ana QA')
    for status in (403, 404):
        f.summary_status = status
        f.page.locator('#employee-ppe-360-modal [data-ppe360-action="refresh"]').click()
        expect(f.root().locator('.ppe360-state--forbidden')).to_have_text(f.t('employee360.forbidden'))
        assert 'Ana QA' not in text_of(f), 'dado anterior sobreviveu à negativa'


def stale_responses(f):
    f.open_colaboradores()
    f.delay(31, 1200)
    f.page.evaluate('()=>{__EPI_EMPLOYEE_PPE_360_VIEW__.open(31)}')
    f.page.wait_for_timeout(100)
    f.page.evaluate('()=>__EPI_EMPLOYEE_PPE_360_VIEW__.open(32)')
    expect(f.root().locator('#ppe360-employee-name')).to_have_text('Tito QA')
    f.page.wait_for_timeout(1500)  # a resposta atrasada de 31 chega e é descartada
    expect(f.root().locator('#ppe360-employee-name')).to_have_text('Tito QA')
    # mudança de contexto durante a requisição: a Ficha fecha e nada é desenhado
    f.delay(31, 800)
    f.page.evaluate('()=>{__EPI_EMPLOYEE_PPE_360_VIEW__.open(31)}')
    f.page.wait_for_timeout(100)
    f.page.evaluate('()=>{__EPI_APP_STATE__.user={...__EPI_APP_STATE__.user, company_id: 902}}')
    f.page.wait_for_timeout(1100)
    expect(f.modal()).to_be_hidden()
    assert f.page.evaluate('__EPI_EMPLOYEE_PPE_360_LIFECYCLE__.getEmployeePpe360State().mounted') is False


def close_and_focus(f):
    f.open_colaboradores()
    button = f.page.locator('#colaboradores-view [data-employee-ppe360="31"]')
    button.click()
    expect(f.root().locator('#ppe360-employee-name')).to_be_visible()
    f.page.keyboard.press('Escape')
    expect(f.modal()).to_be_hidden()
    assert f.page.evaluate('document.activeElement && document.activeElement.getAttribute("data-employee-ppe360")') == '31'
    button.click()
    expect(f.root().locator('#ppe360-employee-name')).to_be_visible()
    f.page.locator('#employee-ppe-360-modal [data-ppe360-action="close"]').click()
    expect(f.modal()).to_be_hidden()
    expect(f.root()).to_be_empty()
    button.click()
    expect(f.root().locator('#ppe360-employee-name')).to_be_visible()
    f.view('dashboard')
    expect(f.modal()).to_be_hidden()


def profiles(f):
    # Administrador Local: a lista dele é a Gestão do colaborador (employees:transfer);
    # a entrada da Ficha está na linha de lá, e a Ficha fecha ao sair dessa tela.
    f.actor.update(role='admin', operational_unit_id=5)
    f.permissions = ['dashboard:view', 'employees:view', 'employees:transfer', 'deliveries:view', 'units:view']
    f.page.evaluate('(actor)=>{__EPI_APP_STATE__.user=actor}', f.actor)
    f.page.evaluate('async()=>{await loadBootstrap({preserveView:true})}')
    f.view('gestao-colaborador')
    button = f.page.locator('#gestao-colaborador-view [data-employee-ppe360="31"]')
    expect(button).to_be_visible()
    button.click()
    expect(f.root().locator('#ppe360-employee-name')).to_have_text('Ana QA')
    f.view('dashboard')
    expect(f.modal()).to_be_hidden()

    # Gestor de EPI: tem employees:view e deliveries:view, não tem finance:view
    # (o frontend soma as permissões padrão do papel, então o papel é o que conta).
    # Não há tela de listagem de colaboradores para este perfil (app.js §accessibleEmployeesView):
    # a Ficha é aberta pela API do módulo para conferir o que ele veria.
    f.actor.update(role='user', operational_unit_id=5)
    f.permissions = ['dashboard:view', 'employees:view', 'deliveries:view', 'units:view']
    f.page.evaluate('(actor)=>{__EPI_APP_STATE__.user=actor}', f.actor)
    f.page.evaluate('async()=>{await loadBootstrap({preserveView:true})}')
    assert 'finance:view' not in f.page.evaluate('__EPI_APP_STATE__.permissions')
    f.page.evaluate('()=>__EPI_EMPLOYEE_PPE_360_VIEW__.open(31)')
    expect(f.root().locator('#ppe360-employee-name')).to_have_text('Ana QA')
    assert f.root().locator('[data-ppe360-card^="finance-"]').count() == 0, 'cartões de custo sem finance:view'
    assert f.root().locator('[data-ppe360-block="consumption"]').count() == 0, 'bloco de custos sem finance:view'
    f.page.keyboard.press('Escape')

    # O Admin Master nem acessa a tela Colaboradores; a Ficha também não gera a entrada
    # nem abre por chamada direta, e nenhuma requisição sai (o backend bloqueia de novo).
    f.actor.update(role='master_admin', company_id=None)
    f.page.evaluate('(actor)=>{__EPI_APP_STATE__.user=actor}', f.actor)
    f.page.evaluate('async()=>{await loadBootstrap({preserveView:true})}')
    before = len(f.summaries())
    assert f.page.evaluate('__EPI_EMPLOYEE_PPE_360_VIEW__.openButtonHtml(31, "Ana QA")') == '', 'Admin Master não vê a entrada (DF-3)'
    assert f.page.evaluate('__EPI_EMPLOYEE_PPE_360_VIEW__.open(31).then(r=>r.reason)') == 'UNAVAILABLE'
    expect(f.modal()).to_be_hidden()
    assert len(f.summaries()) == before


def mobile(f):
    f.page.set_viewport_size({'width': 390, 'height': 844})
    f.open_colaboradores()
    f.page.evaluate('()=>__EPI_EMPLOYEE_PPE_360_VIEW__.open(31)')
    expect(f.root().locator('#ppe360-employee-name')).to_have_text('Ana QA')
    overflow = f.page.evaluate('''()=>{const d=document.querySelector('.ppe360-dialog');
      return {page: document.documentElement.scrollWidth - document.documentElement.clientWidth, dialog: d.scrollWidth - d.clientWidth}}''')
    assert overflow['dialog'] <= 1, f'rolagem horizontal no painel: {overflow}'
    columns = f.page.evaluate('getComputedStyle(document.querySelector(".ppe360-cards")).gridTemplateColumns.split(" ").length')
    assert columns == 2, f'cartões em 2 colunas no mobile: {columns}'
    f.page.screenshot(path=str(f.evidence_dir / f'{f.locale}-mobile-ficha.png'), full_page=False)


SCENARIOS = [entry_and_content, contracted, states, stale_responses, close_and_focus, profiles, mobile]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/ubx-employee-ppe-360'))
    parser.add_argument('--locales', nargs='+', default=LOCALES)
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
            for scenario in SCENARIOS:
                context = browser.new_context(viewport=dict(width=1440, height=1000), service_workers='block', locale=locale)
                page = context.new_page()
                page.set_default_timeout(5000)
                fixture = Fixture(page, origin, locale)
                fixture.evidence_dir = args.output
                result = dict(locale=locale, scenario=scenario.__name__, status='passed')
                try:
                    fixture.open()
                    scenario(fixture)
                    assert page.evaluate('EpiI18n.lang') == locale, 'locale changed during scenario'
                    assert not fixture.errors, f'erros de página: {fixture.errors}'
                except Exception as error:  # noqa: BLE001 - relatório por cenário
                    result.update(status='failed', error=str(error))
                    page.screenshot(path=str(args.output / f'{locale}-{scenario.__name__}-failed.png'))
                finally:
                    result.update(calls=copy.deepcopy(fixture.calls), page_errors=fixture.errors,
                                  blocked_external_requests=fixture.external)
                    results.append(result)
                    print(f"{locale} {scenario.__name__}: {result['status']} {result.get('error', '')[:300]}", flush=True)
                    context.close()
        browser.close()
    server.shutdown()
    (args.output / 'results.json').write_text(json.dumps(results, indent=2, ensure_ascii=False) + '\n')
    return int(any(result['status'] != 'passed' for result in results))


if __name__ == '__main__':
    raise SystemExit(main())
