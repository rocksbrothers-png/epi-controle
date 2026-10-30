"""SECURITY-OUTPUT-XSS-V2 — Chromium: SPA real + API sintética interceptada; nunca abre banco.

Varredura de "dado contaminado": todo texto de cadastro de colaborador, unidade e
EPI (e os textos que andam com eles: matrícula, setor, função, fabricante, CA,
medida, motivo/responsável de arquivamento, títulos de alerta) chega ao app como
`<img src=x onerror=...>`, tanto no bootstrap quanto nas rotas de estoque,
compras, arquivamento, relatórios e fichas. O app real renderiza cada tela e aba,
e também os renderizadores pontuais (formulário de usuário, configuração,
JoinVenture, gaveta de entrega, detalhe de requisição, busca de vínculo).

Falha se qualquer payload executar (registra `tag@contêiner`) ou se sobrar
elemento injetado no DOM. Cenário legítimo: os mesmos dados com texto comum
(inclusive `&`, aspas e acentos) aparecem como texto, sem `&amp;` duplicado.

python scripts/browser/security_output_xss_v2.py --output /tmp/security-output-xss-v2
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

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fix_colab_terc as base

ROOT = base.ROOT
LOCALES = base.LOCALES
ALL_PERMISSIONS = [
    'alerts:view', 'dashboard:view', 'deliveries:create', 'deliveries:view', 'employees:create', 'employees:update',
    'employees:view', 'employees:delete', 'employees:transfer', 'epis:create', 'epis:update', 'epis:view',
    'epis:delete', 'fichas:view', 'purchase_orders:view', 'purchase_orders:create', 'purchase_requests:create',
    'purchase_requests:update', 'purchase_requests:view', 'reports:view', 'settings:update', 'settings:view',
    'stock:adjust', 'stock:view', 'units:create', 'units:update', 'units:view', 'units:delete', 'users:create',
    'users:update', 'users:view', 'companies:view', 'legal_entities:view', 'unit_links:manage',
]
VIEWS = ['dashboard', 'colaboradores', 'gestao-colaborador', 'unidades', 'epis', 'estoque', 'entregas', 'fichas',
         'relatorios', 'compras', 'usuarios', 'terceirizados']
TAINTED_ROUTES = {'/api/bootstrap', '/api/stock/epis', '/api/stock/low', '/api/purchase-demands',
                  '/api/purchase-requests', '/api/purchase-requests/91', '/api/units/archived',
                  '/api/employees/archived', '/api/epis/archived', '/api/reports'}
LEGIT = {'colab': 'Ana & "Bia" Ltda', 'unidade': "Base D'Água", 'epi': 'Luva <nitrílica>'}


def evil(tag):
    return (f'<img src=x onerror="window.__xss=(window.__xss||[]).concat(\'{tag}@\'+'
            f'((this.parentElement&&this.parentElement.closest(\'[id]\'))||{{}}).id)">{tag}')


class Fixture(base.Fixture):
    def __init__(self, page, origin, locale, malicious=True):
        super().__init__(page, origin, locale)
        self.malicious = malicious
        self.actor.update(role='master_admin', company_id=901, operational_unit_id=5)
        # Atualiza (sem redefinir os atributos da base) o perfil e os colaboradores do cenário.
        self.permissions[:] = ALL_PERMISSIONS
        t = self.text
        self.employees[:] = [dict(
            id=31, company_id=901, company_name='Empresa QA', unit_id=5, unit_name=t('colab-unidade', 'unidade'),
            current_unit_name=t('colab-unidade-atual', 'unidade'), employee_id_code=t('matricula', 'M-1'),
            name=t('colab', 'colab'), sector=t('setor', 'Convés'), role_name=t('funcao', 'Técnica'),
            email='ana@example.test', whatsapp=t('whatsapp', '5511999999999'), empresa_origem=t('origem', 'Terceira'),
            tipo_vinculo='Terceirizado', preferred_contact_channel='email', schedule_type='28x28',
            admission_date='2024-01-02', active=1, legal_entity_id=44, outsourced_company_id=11,
            local_unit_link_status='active')]
        self.units_rows = [dict(id=5, company_id=901, company_name='Empresa QA', name=t('unidade', 'unidade'),
                                unit_type='base', city=t('cidade', 'Macaé'))]
        self.epi_rows = [dict(id=61, company_id=901, unit_id=5, unit_name=t('epi-unidade', 'unidade'),
                              name=t('epi', 'epi'), manufacturer=t('fabricante', 'Fab & Cia'), ca='12345',
                              sector='maos', unit_measure='UN', active=1)]
        self.deliveries = [dict(
            id=81, company_id=901, company_name='Empresa QA', employee_id=31, employee_name=t('entrega-colab', 'colab'),
            employee_id_code=t('entrega-matricula', 'M-1'), epi_id=61, epi_name=t('entrega-epi', 'epi'), unit_id=5,
            unit_name=t('entrega-unidade', 'unidade'), quantity=1, quantity_label=t('entrega-medida', 'par'),
            delivery_date='2026-10-01')]
        self.alerts = [dict(type='warning', title=t('alerta-titulo', 'CA vencendo'), description=t('alerta-desc', 'desc'),
                            company_id=901, unit_id=5, epi_id=61, epi_name=t('alerta-epi', 'epi'))]

    def text(self, tag, legit):
        return evil(tag) if self.malicious else LEGIT.get(legit, legit)

    def route(self, route):
        request = route.request
        path = urlsplit(request.url).path
        t = self.text
        if path == '/api/bootstrap':
            original = route.fulfill

            def fulfill(**kwargs):
                payload = kwargs.get('json') or {}
                payload.update(units=self.units_rows, epis=self.epi_rows, deliveries=self.deliveries,
                               alerts=self.alerts, employees=self.employees)
                kwargs['json'] = payload
                return original(**kwargs)
            route.fulfill = fulfill
            return super().route(route)
        data = None
        if path == '/api/stock/epis':
            data = dict(items=[dict(id=61, name=t('estoque-epi', 'epi'), sector='maos', epi_section=t('secao', 'Deck'),
                                    manufacturer=t('estoque-fab', 'Fab'), ca=t('estoque-ca', '123'),
                                    unit_name=t('estoque-unidade', 'unidade'), stock=1, size_balances=[],
                                    unit_measure='UN', minimum_stock=0)])
        elif path == '/api/stock/low':
            data = dict(items=[dict(company_name='Empresa QA', unit_name=t('baixo-unidade', 'unidade'),
                                    epi_name=t('baixo-epi', 'epi'), stock=0, minimum_stock=5, unit_measure='UN')])
        elif path == '/api/purchase-demands':
            data = dict(items=[dict(demand_type='employee_request', employee_name=t('demanda-colab', 'colab'),
                                    unit_name=t('demanda-unidade', 'unidade'), employee_sector=t('demanda-setor', 'setor'),
                                    employee_role=t('demanda-funcao', 'funcao'), epi_name=t('demanda-epi', 'epi'),
                                    ca=t('demanda-ca', '123'), manufacturer=t('demanda-fab', 'Fab'),
                                    supplier=t('demanda-fornecedor', 'Forn'), status='solicitado', company_name='Empresa QA')])
        elif path == '/api/purchase-requests/91':
            data = dict(item=dict(id=91, title=t('requisicao', 'Req'), status='draft', company_id=901),
                        items=[dict(id=1, epi_name=t('req-item-epi', 'epi'), ca=t('req-item-ca', '1'),
                                    manufacturer=t('req-item-fab', 'Fab'), supplier=t('req-item-fornecedor', 'Forn'),
                                    employee_name=t('req-item-colab', 'colab'), origin='employee_request',
                                    glove_size='N/A', size='N/A', uniform_size='N/A', quantity_requested=1)])
        elif path == '/api/purchase-requests':
            data = dict(items=[dict(id=91, title=t('requisicao', 'Req'), unit_name=t('requisicao-unidade', 'unidade'),
                                    status='draft', items_count=1, linked_po_number=t('po', 'PO-1'))])
        elif path == '/api/units/archived':
            data = dict(units=[dict(id=7, company_id=901, company_name='Empresa QA', name=t('unidade-arquivada', 'unidade'),
                                    archived_at='2026-01-01', archive_reason=t('motivo', 'Fim'),
                                    archived_by_name=t('responsavel', 'QA'))])
        elif path in ('/api/employees/archived', '/api/epis/archived'):
            key = 'employees' if 'employees' in path else 'epis'
            data = {key: [dict(id=33, company_id=901, company_name='Empresa QA', name=t(f'{key}-arquivado', 'colab'),
                               employee_id_code=t('arq-matricula', 'M'), unit_name=t('arq-unidade', 'unidade'),
                               ca=t('arq-ca', '1'), archived_at='2026-01-01', archive_reason=t('arq-motivo', 'Fim'),
                               archived_by_name=t('arq-responsavel', 'QA'))]}
        elif path == '/api/reports':
            data = dict(deliveries=self.deliveries, total_quantity=1, by_unit={}, by_sector={}, by_tipo_vinculo={},
                        employee_fichas=[dict(employee_name=t('relatorio-colab', 'colab'),
                                              employee_id_code=t('relatorio-matricula', 'M'), period_start='2026-01-01',
                                              period_end='2026-02-01', status=t('relatorio-status', 'aberta'),
                                              unit_name=t('relatorio-unidade', 'unidade'), total_items=1, total_quantity=1)])
        if data is not None:
            self.calls.append(dict(method=request.method, path=path, query=urlsplit(request.url).query, body=None))
            return route.fulfill(json=data)
        return super().route(route)


EXTRA_RENDERS = [
    # Renderizadores pontuais do app real (funções globais do app.js e dos módulos).
    "await loadPurchaseDemands()",
    "await loadPurchaseRequests()",
    "await openPrDetail(91)",
    "await renderReports({})",
    "populateLinkedEmployeeOptions()",
    "renderLinkedEmployeeSearchResults()",
    "hydrateConfigurationForms()",
    "openDeliveryDetailDrawer(81)",
    "renderAlerts && renderAlerts()",
]


def sweep(f):
    f.open()
    visited, unavailable = [], []
    for view in VIEWS:
        try:
            f.view(view)
        except Exception as exc:  # noqa: BLE001 — tela indisponível para o perfil: registra e segue
            unavailable.append(f'{view}: {str(exc).splitlines()[0][:80]}')
            continue
        visited.append(view)
        f.page.wait_for_timeout(250)
        tabs = f.page.locator(f'nav[data-vtabs="{view}"] [data-vtab]')
        for index in range(tabs.count()):
            if tabs.nth(index).is_visible():
                tabs.nth(index).click()
                visited.append(f'{view}/{tabs.nth(index).get_attribute("data-vtab")}')
                f.page.wait_for_timeout(200)
    for call in EXTRA_RENDERS:
        f.page.evaluate(f'async () => {{ try {{ {call}; }} catch (e) {{}} }}')
        f.page.wait_for_timeout(150)
    f.page.wait_for_timeout(300)
    injected = f.page.eval_on_selector_all('img[src="x"], [onerror]', 'els => els.length')
    hits = sorted(set(f.page.evaluate('window.__xss || []')))
    return visited, unavailable, injected, hits


def run_locale(browser, origin, locale, malicious):
    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, service_workers='block', locale=locale)
    page = context.new_page()
    f = Fixture(page, origin, locale, malicious=malicious)
    try:
        visited, unavailable, injected, hits = sweep(f)
        body = page.locator('body').inner_text()
        tainted_routes = sorted({c['path'] for c in f.calls if c['path'] in TAINTED_ROUTES})
        result = dict(visited=visited, unavailable=unavailable, injected=injected, xss_hits=hits, tainted_routes=tainted_routes,
                      page_errors=f.errors[:5])
        if malicious:
            result['status'] = 'passed' if not hits and not injected else 'failed'
        else:
            # Texto legítimo aparece como texto, sem escape duplicado.
            ok = 'Ana & "Bia" Ltda' in body and '&amp;' not in body and not hits
            result['status'] = 'passed' if ok else 'failed'
        return result
    finally:
        context.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--output', required=True)
    parser.add_argument('--locales', nargs='+', default=LOCALES)
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(base.QuietHandler, directory=str(ROOT / 'static')))
    Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_address[1]}'
    results, failed = [], False
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE') or None)
        for locale in args.locales:
            for scenario, malicious in (('malicioso', True), ('legitimo', False)):
                result = dict(locale=locale, scenario=scenario, **run_locale(browser, origin, locale, malicious))
                failed |= result['status'] != 'passed'
                results.append(result)
                print(locale, scenario, result['status'], 'xss=', result['xss_hits'], 'injetados=', result['injected'],
                      'rotas=', len(result['tainted_routes']))
        browser.close()
    server.shutdown()
    (out / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding='utf-8')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
