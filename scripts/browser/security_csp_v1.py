"""SECURITY-CSP-V1 — Chromium: SPA real servida com a CSP aplicada + API sintética; nunca abre banco.

O servidor estático manda, em cada resposta, o mesmo cabeçalho que o app.py manda
(`core.csp.policy_for_path`), e a página do Portal do Fornecedor com a política
própria (hash do script embutido), como a rota real. Em cada um dos 5 idiomas:

- **Autenticação:** o pré-paint (agora arquivo externo) aplica o tema da sessão; o
  formulário de login envia por `handleLogin` (sem envio nativo com a senha na URL).
- **Navegação e telas:** as 12 telas e todas as abas, e os renderizadores pontuais
  (mesma varredura da SECURITY-OUTPUT-XSS-V2, com dados legítimos): fichas,
  relatórios, estoque, compras, entregas, usuários, configuração.
- **Ações que eram `onclick` inline:** fornecedores autorizados (editar, suspender,
  POs, catálogo, integração), cotações (e-mail, portal, resposta, vencedora) e o
  botão de fornecedor da PO — cada clique tem de chegar à função.
- **Imagens:** logotipo da empresa, foto do EPI e assinatura (desenhada no modal e
  exibida) carregam (`naturalWidth > 0`); QR code externo é permitido.
- **Bibliotecas sob demanda:** html5-qrcode, ZXing e SheetJS carregam (servidas por
  stub no mesmo URL exato que a política libera).
- **Portais:** portal do colaborador (tela de validação do link) e portal do
  fornecedor (o script embutido roda e mostra a cotação).
- **Ficha:** HTML com a política da ficha mostra logotipo e assinatura e roda só o
  script de impressão.

Critério: nenhuma violação de CSP (`securitypolicyviolation`) nos fluxos legítimos.

Testes negativos (SPA e portal do fornecedor): script inline, handler inline
(`onerror`, `onclick`), script externo não autorizado, `setTimeout` com string,
`eval` e link `javascript:`. Com a CSP aplicada nada executa e cada tentativa gera
violação; o controle sem CSP mostra que as mesmas injeções executam (o teste detecta);
em Report-Only, executam mas são reportadas (o que produção passa a registrar).

python scripts/browser/security_csp_v1.py --output /tmp/security-csp-v1
CHROMIUM_EXECUTABLE=/usr/bin/chromium seleciona um navegador já instalado.
"""
import argparse
import base64
import json
import os
import re
import sys
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fix_colab_terc as base
import security_output_xss_v2 as xss

sys.path.insert(0, str(base.ROOT))
from core import csp  # noqa: E402
from modules.ficha import routes as ficha_routes  # noqa: E402
from modules.purchases import supplier_portal_page  # noqa: E402

ROOT = base.ROOT
LOCALES = base.LOCALES
PNG = ('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==')
PNG_BYTES = base64.b64decode(PNG.split(',', 1)[1])
# Bibliotecas carregadas sob demanda: o stub marca que o script rodou (a CSP liberou o URL).
LAZY_LIBS = [src for src in csp.SPA_EXTERNAL_SCRIPTS if 'htmx' not in src]
SERVER_MODE = {'value': 'enforce'}  # enforce | report-only | none

VIOLATION_RECORDER = """
window.__csp = [];
document.addEventListener('securitypolicyviolation', (e) => {
  window.__csp.push({directive: e.effectiveDirective || e.violatedDirective, blocked: e.blockedURI,
                     sample: (e.sample || '').slice(0, 60), disposition: e.disposition});
}, true);
window.print = () => { window.__printed = (window.__printed || 0) + 1; };
"""


class CspHandler(base.QuietHandler):
    """Servidor estático com a CSP do app.py (e a política própria das páginas por rota)."""

    def do_GET(self):  # noqa: N802 — nome da API do http.server
        path = urlsplit(self.path).path
        route_page = None
        if re.fullmatch(r'/fornecedor/[A-Za-z0-9_\-]+', path):
            route_page = (supplier_portal_page.PORTAL_PAGE_HTML, supplier_portal_page.PORTAL_PAGE_CSP)
        elif path == '/ficha-demo':
            route_page = (FICHA_DEMO, ficha_routes.FICHA_HTML_CSP)
        if route_page is None:
            return super().do_GET()
        body = route_page[0].encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        if SERVER_MODE['value'] != 'none':
            self.send_header('Content-Security-Policy', route_page[1])
        self.send_header('Content-Length', str(len(body)))
        self._route_csp = True
        self.end_headers()
        self.wfile.write(body)
        return None

    def end_headers(self):
        mode = SERVER_MODE['value']
        if mode != 'none' and not getattr(self, '_route_csp', False):
            header, value = csp.policy_for_path(urlsplit(self.path).path, mode=mode)
            self.send_header(header, value)
        self._route_csp = False
        super().end_headers()


FICHA_DEMO = (
    '<!doctype html><html><head><meta charset="utf-8"><title>Ficha</title></head><body>'
    f'<img id="ficha-logo" src="{PNG}" alt="logo"><p>Ficha de EPI</p>'
    f'<img id="ficha-assinatura" src="{PNG}" alt="assinatura">'
    f'<script>{ficha_routes._FICHA_PRINT_SCRIPT}</script></body></html>'
)


class Fixture(xss.Fixture):
    def __init__(self, page, origin, locale):
        super().__init__(page, origin, locale, malicious=False)
        self.actor.update(logo_type=PNG, company_name='Empresa QA')
        self.permissions[:] = xss.ALL_PERMISSIONS + ['suppliers:manage', 'quotes:manage', 'purchase_orders:update', 'finance:view']
        self.epi_rows[0].update(epi_photo_data=PNG)
        self.lazy_loaded, self.external_allowed = [], []

    def route(self, route):
        request = route.request
        url = request.url
        parts = urlsplit(url)
        path = parts.path
        if parts.netloc != urlsplit(self.origin).netloc:
            # A requisição só chega aqui se a CSP deixou o navegador fazê-la.
            self.external_allowed.append(url)
            if url in LAZY_LIBS:
                self.lazy_loaded.append(url)
                return route.fulfill(content_type='application/javascript',
                                     body=f'window.__libs=(window.__libs||[]).concat({json.dumps(url)});')
            if parts.netloc == 'api.qrserver.com':
                return route.fulfill(content_type='image/png', body=PNG_BYTES)
            return route.abort()
        data = None
        if path == '/api/bootstrap':
            original = route.fulfill

            def fulfill(**kwargs):
                payload = kwargs.get('json') or {}
                for company in payload.get('companies') or []:
                    company.update(logo_type=PNG)
                kwargs['json'] = payload
                return original(**kwargs)
            route.fulfill = fulfill
            return super().route(route)
        if path == '/api/login':
            data = dict(user=self.actor, permissions=self.permissions, token='tok-qa')
        elif path == '/api/authorized-suppliers':
            data = dict(items=[dict(id=7, name="Forn O'Brien \"Ltda\"", cnpj='11222333000181', active=1,
                                    contact_email='f@example.test', integration_level='api')])
        elif path == '/api/purchase-requests/91/quotes':
            data = dict(items=[dict(id=501, supplier_name='Forn A', status='sent', channel='email',
                                    supplier_integration_level='api', total_value=10, items=[]),
                               dict(id=502, supplier_name='Forn B', status='answered', channel='portal',
                                    total_value=9, items=[])], comparison={})
        elif re.fullmatch(r'/api/quotes/\d+/(send|portal-link|fetch-api|select)', path):
            data = dict(ok=True, item={}, url='https://epi.test/fornecedor/x')
        elif path == '/api/purchase-orders' and request.method == 'GET':
            data = dict(items=[dict(id=601, po_number='PO-601', supplier_id=7, supplier_name='Forn A', status='sent',
                                    total_value=10, unit_name='Unidade QA', company_id=901)])
        elif path == '/api/portal/supplier/tok-fornecedor':
            data = dict(ok=True, item=dict(entity_type='quote', company_name='Empresa QA', supplier_name='Forn A',
                                           quote=dict(id=501, status='sent', items=[dict(
                                               quote_item_id=1, epi_name='Luva', quantity=2, unit_measure='PAR')])))
        if data is not None:
            self.calls.append(dict(method=request.method, path=path, query=parts.query, body=None))
            return route.fulfill(json=data)
        return super().route(route)


def violations(page):
    return page.evaluate('window.__csp || []')


def new_page(browser, locale):
    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, service_workers='block', locale=locale)
    context.add_init_script(VIOLATION_RECORDER)
    return context, context.new_page()


def check_login(browser, origin, locale):
    """Pré-paint externo aplica o tema da sessão; login pelo formulário real (handleLogin)."""
    context, page = new_page(browser, locale)
    context.add_init_script("sessionStorage.setItem('epi-prefs-sessao', JSON.stringify({tema: 'dark'}))")
    f = Fixture(page, origin, locale)
    try:
        page.goto(origin + '/', wait_until='load')
        theme = page.evaluate("document.documentElement.getAttribute('data-theme')")
        page.fill('#login-username', 'qa.user')
        page.fill('#login-password', 'Senha#QA1')
        page.locator('#login-form button[type="submit"]').click()
        page.wait_for_function('() => !!(globalThis.__EPI_APP_STATE__ && __EPI_APP_STATE__.user)')
        page.wait_for_timeout(400)
        logged = [c for c in f.calls if c['path'] == '/api/login' and c['method'] == 'POST']
        ok = theme == 'dark' and len(logged) == 1 and 'Senha' not in page.url and 'password' not in page.url
        return dict(ok=ok, pre_paint_theme=theme, login_calls=len(logged), url=page.url.replace(origin, ''),
                    violations=violations(page), errors=f.errors[:3])
    finally:
        context.close()


SPY = """
() => {
  window.__spy = [];
  const wrap = (name) => { const orig = globalThis[name]; globalThis[name] = (...args) => { window.__spy.push(name + ':' + JSON.stringify(args)); return typeof orig === 'function' ? undefined : undefined; }; };
  ['openEditSupplierModal', 'toggleSupplierActive', 'openSupplierPOsModal', 'openSupplierCatalogModal',
   'openSupplierIntegrationModal', 'openPoSupplierActionsModal'].forEach(wrap);
}
"""


def check_converted_actions(f):
    """Cliques nos botões que eram onclick inline chegam às funções (via delegação)."""
    page = f.page
    page.evaluate(SPY)
    page.evaluate('async () => { await loadAuthorizedSuppliers(); }')
    for action in ('edit', 'toggle', 'pos', 'catalog', 'integration'):
        page.locator(f'#compras-suppliers-tbody [data-supplier-action="{action}"]').first.dispatch_event('click')
    supplier_calls = page.evaluate('window.__spy.slice()')
    # openEditSupplierModal é função de bloco do app.js (o espião global não a intercepta): confere o modal.
    if page.evaluate("document.getElementById('edit-supplier-name')?.value") == "Forn O'Brien \"Ltda\"":
        supplier_calls.insert(0, 'openEditSupplierModal:[7]')
    # Cotações: seleciona a requisição e clica nas ações (closures do módulo → chamadas de API).
    page.evaluate("""async () => {
      await loadCotacoes();
      const select = document.getElementById('cotacoes-pr-select');
      select.value = '91'; select.dispatchEvent(new Event('change'));
    }""")
    page.wait_for_selector('#cotacoes-tbody [data-quote-action]', state='attached')
    for action in ('email', 'portal', 'api', 'winner'):
        page.locator(f'#cotacoes-tbody [data-quote-action="{action}"]').first.dispatch_event('click')
        page.wait_for_timeout(250)
        page.wait_for_selector('#cotacoes-tbody [data-quote-action]', state='attached')
    page.locator('#cotacoes-tbody [data-quote-action="answer"]').first.dispatch_event('click')
    page.wait_for_timeout(250)
    answer_modal = page.locator('text=Forn A').count() > 0
    quote_posts = sorted({c['path'] for c in f.calls if c['method'] == 'POST' and c['path'].startswith('/api/quotes/')})
    # Botão de fornecedor da PO (compras-po-tbody), tratado pelo listener delegado de purchases.js.
    page.evaluate('async () => { await loadPurchaseOrders?.(); }')
    page.wait_for_selector('#compras-po-tbody [data-po-supplier-actions="601"]', state='attached')
    page.locator('#compras-po-tbody [data-po-supplier-actions="601"]').dispatch_event('click')
    po_calls = [c for c in page.evaluate('window.__spy.slice()') if c.startswith('openPoSupplierActionsModal')]
    expected_supplier = {'openEditSupplierModal', 'toggleSupplierActive', 'openSupplierPOsModal',
                         'openSupplierCatalogModal', 'openSupplierIntegrationModal'}
    got_supplier = {c.split(':', 1)[0] for c in supplier_calls}
    expected_posts = {'/api/quotes/501/send', '/api/quotes/501/portal-link', '/api/quotes/501/fetch-api',
                      '/api/quotes/502/select'}
    ok = got_supplier == expected_supplier and expected_posts <= set(quote_posts) and answer_modal and po_calls == ['openPoSupplierActionsModal:[601]']
    # O nome com aspas não quebra mais o atributo: a função recebe o nome íntegro.
    name_intact = any('Forn O\'Brien \\"Ltda\\"' in c for c in supplier_calls if c.startswith('toggleSupplierActive'))
    return dict(ok=ok and name_intact, supplier_calls=supplier_calls, quote_posts=quote_posts,
                answer_modal=answer_modal, po_calls=po_calls, supplier_name_intact=name_intact)


def check_images_and_libs(f):
    page = f.page
    # Foto do EPI: tabela de EPIs aprovados (dashboard).
    f.view('dashboard')
    page.wait_for_timeout(300)
    photo = page.evaluate(f"""async () => {{
      const imgs = [...document.querySelectorAll('#approved-epi-table img')].filter(i => i.src === {json.dumps(PNG)});
      await Promise.all(imgs.map(i => i.decode().catch(() => null)));
      return imgs.map(i => i.complete && i.naturalWidth > 0);
    }}""")
    logo = page.evaluate(f"""() => [...document.querySelectorAll('#company-badge img, #platform-brand-logo img, .topbar img')]
        .filter(i => i.src === {json.dumps(PNG)}).map(i => i.complete && i.naturalWidth > 0)""")
    # Assinatura: desenha no modal real, confirma e exibe o data URL gerado.
    page.evaluate("() => openSignatureModal({signerName: 'Ana QA', onConfirm: (p) => { window.__sig = p; }})")
    canvas = page.locator('#signature-modal-canvas')
    box = canvas.bounding_box()
    page.mouse.move(box['x'] + 20, box['y'] + 20)
    page.mouse.down()
    for step in range(1, 12):
        page.mouse.move(box['x'] + 20 + step * 25, box['y'] + 20 + (step % 3) * 30)
    page.mouse.up()
    identity = page.locator('#signature-modal-identity')
    if identity.count():
        identity.check()
    page.locator('#signature-modal-confirm').click()
    signature = page.evaluate("""async () => {
      const data = (window.__sig || {}).signature_data || '';
      if (!data.startsWith('data:image/')) return {ok: false, data: data.slice(0, 30)};
      const img = new Image(); img.src = data; document.body.appendChild(img);
      await img.decode().catch(() => null);
      return {ok: img.naturalWidth > 0, data: data.slice(0, 22)};
    }""")
    # QR code (api.qrserver.com) e bibliotecas sob demanda.
    qr = page.evaluate("""async () => {
      const img = new Image(); img.src = qrCodeImageUrl('QA-1'); document.body.appendChild(img);
      await img.decode().catch(() => null); return img.naturalWidth > 0;
    }""")
    page.evaluate('async () => { await loadHtml5QrcodeLibrary().catch(() => null); await loadZxingLibrary().catch(() => null); }')
    # SheetJS: pelo caminho real (importar planilha .xlsx de fornecedores); o stub não lê o arquivo.
    f.view('compras')
    page.set_input_files('#compras-suppliers-csv', files=[dict(name='fornecedores.xlsx', buffer=b'QA',
                         mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')])
    page.evaluate('async () => { await importSuppliersCSV(); }')
    libs = sorted(page.evaluate('window.__libs || []'))
    ok = bool(photo) and all(photo) and bool(logo) and all(logo) and signature['ok'] and qr and libs == sorted(LAZY_LIBS)
    return dict(ok=ok, epi_photo=photo, logo=logo, signature=signature, qr=qr, lazy_libs=libs)


def check_employee_portal(browser, origin, locale):
    context, page = new_page(browser, locale)
    f = Fixture(page, origin, locale)
    try:
        page.goto(origin + '/?employee_token=tok-colab', wait_until='load')
        page.wait_for_selector('#employee-cpf-last3', state='visible')
        page.wait_for_timeout(300)
        return dict(ok=not violations(page), violations=violations(page), errors=f.errors[:3])
    finally:
        context.close()


def check_supplier_portal(browser, origin, locale):
    context, page = new_page(browser, locale)
    f = Fixture(page, origin, locale)
    try:
        page.goto(origin + '/fornecedor/tok-fornecedor', wait_until='load')
        page.wait_for_selector('#conteudo', state='visible')
        rendered = 'Luva' in page.locator('#conteudo').inner_text()
        return dict(ok=rendered and not violations(page), rendered=rendered, violations=violations(page),
                    errors=f.errors[:3])
    finally:
        context.close()


def check_ficha(browser, origin, locale):
    context, page = new_page(browser, locale)
    try:
        page.goto(origin + '/ficha-demo', wait_until='load')
        page.wait_for_timeout(600)
        images = page.evaluate("() => [...document.images].map(i => i.complete && i.naturalWidth > 0)")
        printed = page.evaluate('window.__printed || 0')
        return dict(ok=images == [True, True] and printed == 1 and not violations(page), images=images,
                    printed=printed, violations=violations(page))
    finally:
        context.close()


NEGATIVE_SPA = """
async () => {
  window.__neg = [];
  const box = document.createElement('div'); box.id = 'csp-negativo'; document.body.appendChild(box);
  box.innerHTML = '<img src="x-nao-existe.png" onerror="window.__neg.push(\\'onerror\\')">';
  const inline = document.createElement('script'); inline.textContent = "window.__neg.push('script-inline')";
  document.body.appendChild(inline);
  await new Promise((resolve) => {
    const ext = document.createElement('script'); ext.src = 'https://evil.test/x.js';
    ext.onload = ext.onerror = resolve; document.body.appendChild(ext); setTimeout(resolve, 800);
  });
  const btn = document.createElement('button'); btn.setAttribute('onclick', "window.__neg.push('onclick')");
  box.appendChild(btn); btn.click();
  try { setTimeout("window.__neg.push('setTimeout-string')", 0); } catch (e) { /* bloqueado */ }
  try { eval("window.__neg.push('eval')"); } catch (e) { /* bloqueado */ }
  const link = document.createElement('a'); link.href = "javascript:window.__neg.push('javascript-url')";
  box.appendChild(link); link.click();
  await new Promise((r) => setTimeout(r, 600));
  return window.__neg.slice();
}
"""
NEGATIVE_KINDS = {'onerror', 'script-inline', 'onclick', 'setTimeout-string', 'eval', 'javascript-url'}


def run_negative(browser, origin, locale, where):
    context, page = new_page(browser, locale)
    f = Fixture(page, origin, locale)
    try:
        if where == 'spa':
            page.goto(origin + '/', wait_until='load')
            page.wait_for_function('!!globalThis.__EPI_APP_STATE__')
        else:
            page.goto(origin + '/fornecedor/tok-fornecedor', wait_until='load')
            page.wait_for_selector('#conteudo', state='visible')
        page.wait_for_timeout(200)
        before = len(violations(page))
        executed = sorted(set(page.evaluate(NEGATIVE_SPA)))
        found = violations(page)[before:]
        evil_requested = any('evil.test' in u for u in f.external_allowed)
        return dict(executed=executed, violations=len(found), evil_requested=evil_requested,
                    directives=sorted({v['directive'] for v in found}))
    finally:
        context.close()


def run_locale(browser, origin, locale):
    result = dict(locale=locale)
    result['login'] = check_login(browser, origin, locale)
    context, page = new_page(browser, locale)
    f = Fixture(page, origin, locale)
    try:
        visited, unavailable, injected, hits, render_errors = xss.sweep(f)
        result['sweep'] = dict(ok=not render_errors and len(visited) >= len(xss.VIEWS), visited=len(visited),
                               unavailable=unavailable, render_errors=render_errors)
        result['actions'] = check_converted_actions(f)
        result['images'] = check_images_and_libs(f)
        result['app_violations'] = violations(page)
        result['app_errors'] = [e for e in f.errors if 'Content Security Policy' in e][:5]
    finally:
        context.close()
    result['employee_portal'] = check_employee_portal(browser, origin, locale)
    result['supplier_portal'] = check_supplier_portal(browser, origin, locale)
    result['ficha'] = check_ficha(browser, origin, locale)
    checks = ('login', 'sweep', 'actions', 'images', 'employee_portal', 'supplier_portal', 'ficha')
    no_violations = not result['app_violations'] and not result['login']['violations']
    result['status'] = 'passed' if all(result[c]['ok'] for c in checks) and no_violations else 'failed'
    return result


def summary(result):
    """Resumo gravado em disco: só status, contagens e diretivas (nada de dado de formulário ou de tela)."""
    checks = ('login', 'sweep', 'actions', 'images', 'employee_portal', 'supplier_portal', 'ficha')
    return dict(locale=result['locale'], status=result['status'],
                checks={name: bool(result[name]['ok']) for name in checks},
                screens_visited=int(result['sweep']['visited']),
                violations=sorted({str(v.get('directive')) for v in result['app_violations']}),
                violation_count=len(result['app_violations']),
                lazy_libs_loaded=len(result['images'].get('lazy_libs', [])))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--output', required=True)
    parser.add_argument('--locales', nargs='+', default=LOCALES)
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(CspHandler, directory=str(ROOT / 'static')))
    Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_address[1]}'
    results, failed = dict(locales=[], negative={}), False
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE') or None)
        SERVER_MODE['value'] = 'enforce'
        for locale in args.locales:
            result = run_locale(browser, origin, locale)
            failed |= result['status'] != 'passed'
            results['locales'].append(summary(result))
            print(locale, result['status'], 'telas=', result['sweep']['visited'],
                  'violações=', len(result['app_violations']), {k: result[k]['ok'] for k in
                  ('login', 'actions', 'images', 'employee_portal', 'supplier_portal', 'ficha')})
        # Negativos: aplicada (bloqueia e reporta), sem CSP (controle: executa) e Report-Only (a SPA executa e
        # reporta; o portal do fornecedor segue bloqueando, porque a política dele é da rota).
        for mode in ('enforce', 'none', 'report-only'):
            SERVER_MODE['value'] = mode
            for where in ('spa', 'fornecedor'):
                neg = run_negative(browser, origin, args.locales[0], where)
                results['negative'][f'{mode}/{where}'] = dict(executed=list(neg['executed']),
                                                              violations=int(neg['violations']),
                                                              evil_requested=bool(neg['evil_requested']))
                if mode == 'enforce':
                    ok = not neg['executed'] and neg['violations'] >= len(NEGATIVE_KINDS) and not neg['evil_requested']
                elif mode == 'none':
                    ok = set(neg['executed']) == NEGATIVE_KINDS and neg['violations'] == 0
                elif where == 'spa':
                    ok = set(neg['executed']) == NEGATIVE_KINDS and neg['violations'] >= len(NEGATIVE_KINDS)
                else:
                    # A página do fornecedor tem a política própria, sempre aplicada (não segue CSP_MODE).
                    ok = not neg['executed'] and neg['violations'] >= len(NEGATIVE_KINDS)
                neg['status'] = 'passed' if ok else 'failed'
                results['negative'][f'{mode}/{where}']['status'] = neg['status']
                failed |= not ok
                print('negativo', mode, where, neg['status'], 'executou=', neg['executed'], 'violações=', neg['violations'])
        browser.close()
    server.shutdown()
    (out / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding='utf-8')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
