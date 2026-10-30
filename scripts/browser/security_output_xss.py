"""SECURITY-OUTPUT-XSS-V1 — Chromium: SPA real + API sintética interceptada; nunca abre banco.

Confere, nos 5 idiomas, que texto de cadastro com HTML (nome/CNPJ de empresa,
nome de EPI, foto de EPI) não executa nem injeta elementos, e que os dados
legítimos continuam aparecendo:

1. Topo do app (nome/CNPJ da empresa do usuário) e os selects montados por
   populateSelect (empresas em todos os cadastros).
2. Comercial (cards de resumo, alerta e histórico) — Administrador Master.
3. Empresas (lista e detalhes) — Administrador Master.
4. Lista de EPIs (nome e foto); foto legítima carrega.
5. Ficha EPI em HTML (servidor): render atual com dados maliciosos e um
   snapshot gravado ANTES da correção, servidos com o CSP das rotas da ficha —
   nada executa, logotipo/assinatura legítimos carregam e o script de impressão
   do arquivo (liberado por hash) continua rodando.

pip install playwright; playwright install chromium
python scripts/browser/security_output_xss.py --output /tmp/security-output-xss
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
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import fix_colab_terc as base
import fix_nav_refresh as nav

ROOT = base.ROOT
LOCALES = base.LOCALES
PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='


def evil(tag):
    # Registra onde executou (id do contêiner mais próximo) para o relatório.
    return (f'<img src=x onerror="window.__xss=(window.__xss||[]).concat(\'{tag}@\'+'
            f'((this.parentElement&&this.parentElement.closest(\'[id]\'))||{{}}).id)">{tag}')


def evil_photo(tag):
    return f'data:image/png;base64,AAAA" onerror="window.__xss=(window.__xss||[]).concat(\'{tag}\')" x="'


class Fixture(nav.Fixture):
    def __init__(self, *args, malicious=True):
        super().__init__(*args)
        self.malicious = malicious
        name = evil('topo') if malicious else 'Empresa QA'
        cnpj = evil('cnpj') if malicious else '11.222.333/0001-81'
        self.actor.update(company_name=name, company_cnpj=cnpj)
        self.company_rows = [{
            'id': 901, 'name': evil('empresa') if malicious else 'Empresa QA',
            'legal_name': evil('razao') if malicious else 'Empresa QA Ltda',
            'cnpj': evil('cnpj-lista') if malicious else '11222333000181', 'active': 1, 'license_status': 'expired',
            'plan_name': 'start', 'user_limit': 10, 'user_count': 10, 'available_slots': 0, 'limit_reached': 1,
            'commercial_notes': evil('notas') if malicious else 'Notas', 'monthly_value': 10,
            'contract_end': '2026-11-05'}]
        self.epi_rows = [{
            'id': 61, 'company_id': 901, 'unit_id': 5, 'name': evil('epi') if malicious else 'Capacete QA',
            'manufacturer': evil('fabricante') if malicious else 'Fab', 'ca': '123', 'sector': 'Cabeça',
            'epi_section': 'Deck', 'unit_measure': 'UN', 'manufacturer_recommendations': 'Usar',
            'epi_photo_data': evil_photo('foto') if malicious else PNG, 'active': 1}]

    def route(self, route):
        request = route.request
        path = urlsplit(request.url).path
        if path == '/api/bootstrap':
            original = route.fulfill

            def fulfill(**kwargs):
                payload = kwargs.get('json') or {}
                payload.update(
                    companies=self.company_rows, epis=self.epi_rows,
                    company_audit_logs=[{'id': 1, 'company_id': 901, 'company_name': self.company_rows[0]['name'],
                                         'action_type': 'update', 'action_label': 'Atualização',
                                         'actor_name': evil('ator') if self.malicious else 'Master',
                                         'summary': evil('resumo') if self.malicious else 'Resumo',
                                         'details': [], 'created_at': '2026-10-30T10:00:00Z'}])
                kwargs['json'] = payload
                return original(**kwargs)
            route.fulfill = fulfill
            return super().route(route)
        if path == '/api/reports':
            return route.fulfill(json={'deliveries': [], 'total_quantity': 0, 'by_unit': {}, 'by_sector': {},
                                       'by_tipo_vinculo': {}, 'employee_fichas': []})
        return super().route(route)


def hits(page):
    return page.evaluate('window.__xss || []')


def no_injected(page, selector):
    count = page.eval_on_selector_all(f'{selector} img[src="x"], {selector} [onerror]', 'els => els.length')
    assert count == 0, f'elementos injetados em {selector}: {count}'


def topbar_and_selects(f):
    f.open()
    f.page.wait_for_timeout(200)
    no_injected(f.page, '#company-badge')
    text = f.page.locator('#company-badge').inner_text()
    if f.malicious:
        assert '<img src=x' in text, text  # aparece como texto, não como elemento
        option = f.page.locator('#employee-company option').first.inner_text()
        assert option.startswith('<img src=x'), option
    else:
        assert 'Empresa QA' in text and '11.222.333/0001-81' in text, text


def commercial(f):
    f.actor['role'] = 'master_admin'
    f.permissions.extend(p for p in ('companies:view', 'companies:update', 'commercial:view', 'commercial:update')
                         if p not in f.permissions)
    f.open()
    f.view('comercial')
    for tab in ('contratos', 'config'):
        f.tab('comercial', tab)
        f.page.wait_for_timeout(150)
    for selector in ('#commercial-summary', '#commercial-alerts', '#commercial-history', '#commercial-company'):
        no_injected(f.page, selector)
    summary = f.page.locator('#commercial-summary').inner_text()
    assert ('<img src=x' in summary) if f.malicious else ('Empresa QA' in summary), summary


def companies(f):
    f.actor['role'] = 'master_admin'
    f.permissions.extend(p for p in ('companies:view', 'companies:update') if p not in f.permissions)
    f.open()
    f.view('empresas')
    f.tab('empresas', 'lista')
    expect(f.page.locator('#companies-table tr')).to_have_count(1)
    f.page.locator('[data-company-details="901"]').click()
    for selector in ('#companies-table', '#company-details'):
        no_injected(f.page, selector)
    details = f.page.locator('#company-details').inner_text()
    assert ('<img src=x' in details) if f.malicious else ('Empresa QA Ltda' in details), details


def epi_list(f):
    f.permissions.extend(p for p in ('epis:view',) if p not in f.permissions)
    f.open()
    f.view('epis')
    f.tab('epis', 'lista')
    expect(f.page.locator('#approved-epi-table tr')).to_have_count(1)
    no_injected(f.page, '#approved-epi-table')
    imgs = f.page.eval_on_selector_all('#approved-epi-table img', 'els => els.map(e => e.getAttribute("src"))')
    if f.malicious:
        assert imgs == [], imgs
        assert '<img src=x' in f.page.locator('#approved-epi-table').inner_text()
    else:
        assert imgs == [PNG], imgs
        f.page.wait_for_function('document.querySelector("#approved-epi-table img").naturalWidth > 0')


def ficha_html(f):
    from modules.ficha.routes import _FICHA_PRINT_SCRIPT, FICHA_HTML_CSP
    from modules.ficha.service import render_ficha_epi_html_document
    data = dict(
        employee={'name': evil('ficha-nome'), 'role_name': evil('funcao'), 'sector': evil('setor'),
                  'empresa_origem': evil('origem'), 'tipo_vinculo': 'Terceirizado'},
        company={'name': evil('ficha-empresa'), 'cnpj': evil('ficha-cnpj'), 'logo_type': PNG},
        unit={'name': evil('unidade')},
        deliveries=[{'epi_name': evil('ficha-epi'), 'ca': evil('ca'), 'quantity': 1, 'signature_data': PNG},
                    {'epi_name': 'Luva', 'signature_data': evil_photo('assinatura')}],
        devolutions=[{'epi_name': evil('devol'), 'reason': evil('motivo'), 'received_by_name': evil('recebido')}],
        config={'titulo': evil('titulo'), 'declaracao': evil('declaracao') + '\nlinha 2', 'observacoes': evil('obs'),
                'rastreabilidade': evil('rodape')},
        period_label=evil('periodo'))
    rendered = render_ficha_epi_html_document(**data)
    # Snapshot gravado antes da correção: HTML cru com script e handler + o script de impressão do arquivo.
    legacy = ('<!DOCTYPE html><html><body><div>' + evil('snapshot') + '</div>'
              '<script>window.__xss=(window.__xss||[]).concat("snapshot-script")</script>'
              f'<script>{_FICHA_PRINT_SCRIPT}</script></body></html>')
    pages = {'/ficha-render.html': rendered, '/ficha-legacy.html': legacy}

    def handler(route):
        path = urlsplit(route.request.url).path
        route.fulfill(status=200, body=pages[path], headers={'Content-Type': 'text/html; charset=utf-8',
                                                             'Content-Security-Policy': FICHA_HTML_CSP})
    f.page.add_init_script('window.print = () => { window.__printed = (window.__printed || 0) + 1; };')
    f.page.route('**/ficha-*.html', handler)
    f.page.goto(f.origin + '/ficha-render.html', wait_until='load')
    no_injected(f.page, 'body')
    imgs = f.page.eval_on_selector_all('img', 'els => els.map(e => [e.getAttribute("src"), e.naturalWidth > 0])')
    assert imgs == [[PNG, True], [PNG, True]], imgs  # logotipo e a assinatura legítima; a maliciosa some
    body = f.page.locator('body').inner_text()
    assert '<img src=x' in body and 'linha 2' in body, body[:300]
    assert hits(f.page) == [], hits(f.page)
    f.page.goto(f.origin + '/ficha-legacy.html', wait_until='load')
    f.page.wait_for_timeout(600)
    assert hits(f.page) == [], f'snapshot antigo executou: {hits(f.page)}'
    assert f.page.evaluate('window.__printed || 0') == 1, 'script de impressão bloqueado pelo CSP'


SCENARIOS = [
    ('topo_malicioso', topbar_and_selects, True), ('topo_legitimo', topbar_and_selects, False),
    ('comercial_malicioso', commercial, True), ('comercial_legitimo', commercial, False),
    ('empresas_malicioso', companies, True), ('empresas_legitimo', companies, False),
    ('epis_malicioso', epi_list, True), ('epis_legitimo', epi_list, False),
    ('ficha_html', ficha_html, True),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/security-output-xss-browser'))
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
            for name, scenario, malicious in [s for s in SCENARIOS if s[0] in args.scenarios]:
                context = browser.new_context(viewport={'width': 1440, 'height': 1000}, service_workers='block', locale=locale)
                page = context.new_page()
                page.set_default_timeout(4000)
                fixture = Fixture(page, origin, locale, malicious=malicious)
                result = {'locale': locale, 'scenario': name, 'status': 'passed'}
                try:
                    scenario(fixture)
                    page.wait_for_timeout(200)
                    assert hits(page) == [], f'XSS executou: {hits(page)}'
                    assert not fixture.errors, f'page errors: {fixture.errors}'
                except Exception as error:  # noqa: BLE001 — registra a falha do cenário e segue para o próximo
                    result.update(status='failed', error=str(error))
                finally:
                    try:
                        result['xss_hits'] = hits(page)
                    except Exception:  # noqa: BLE001 — página fechada/erro de navegação
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
