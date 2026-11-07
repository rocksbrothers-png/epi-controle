"""UBX impressão compartilhada: SPA real, consumidores e popup real, cinco idiomas.

--record --static <base>/static grava a referência do próprio produto antes de extrair.
Somente a origem efêmera do servidor local é substituída no golden; paths, queries,
HTML, opções, eventos, alertas e payloads permanecem exatos. Observações brutas são guardadas.
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
import i18n_commercial as commercial

ROOT = base.ROOT
GOLDEN = ROOT / 'static/js/test/fixtures/ubx-print-popup-browser.json'
INSTALL_SPY = """() => {
  window.__qaNativeOpen = window.open;
  window.__qaBlocked = false; window.__qaPopups = [];
  window.open = (...args) => {
    const entry = {args, html:'', events:[]}; __qaPopups.push(entry);
    if (__qaBlocked) return null;
    return {document:{readyState:'complete',open(){entry.events.push('open')},
      write(html){entry.events.push('write');entry.html+=html},close(){entry.events.push('close')}},
      focus(){entry.events.push('focus')},print(){entry.events.push('print')}};
  };
  __EPI_APP_STATE__.users = [{id:30,role:'employee',employee_access_token:'QA & token'}];
  __EPI_APP_STATE__.employees = [{id:31,name:'Ana <img src=x onerror=window.__xss=1>'}];
}"""


class Fixture(commercial.Fixture):
    def __init__(self, *args):
        super().__init__(*args)
        self.portal_status = 200

    def route(self, route):
        request = route.request
        path = urlsplit(request.url).path
        if path == '/api/employee-portal-link':
            body = json.loads(request.post_data or '{}')
            self.calls.append({'method': request.method, 'path': path, 'query': urlsplit(request.url).query, 'body': body})
            if self.portal_status != 200:
                return route.fulfill(status=self.portal_status, json={'error': 'QA forbidden', 'message': 'QA forbidden'})
            return route.fulfill(json={'access_link': 'https://portal.example.test/?employee_token=QA%26token'})
        return super().route(route)


def exercise(f, context):
    page = f.page
    f.view('comercial')
    f.tab('comercial', 'contratos')
    page.evaluate(INSTALL_SPY)
    steps = []

    def capture(label):
        steps.append({'label': label, 'popups': page.evaluate('__qaPopups'), 'dialogs': f.dialogs[:],
                      'calls': [c for c in f.calls if c['path'] == '/api/employee-portal-link']})

    actions = [
        ('comercial', lambda: page.locator('#commercial-print').click()),
        ('QR do usuário', lambda: page.evaluate('printEmployeeAccessQr(30)')),
        ('portal do colaborador', lambda: page.evaluate('async()=>{await printEmployeePortalLink(31)}')),
        ('etiquetas de estoque', lambda: page.evaluate("""printStockLabels([{stock_item_id:7,epi_name:'Luva <img src=x onerror=window.__xss=1>',
          qr_code_value:'QR<&>',unit_name:'Base & Cia',glove_size:'M'}],2)""")),
    ]
    for blocked in [False, True]:
        page.evaluate('(blocked)=>{__qaBlocked=blocked}', blocked)
        for name, action in actions:
            before = page.evaluate('__qaPopups.length')
            action()
            page.wait_for_function('(n)=>__qaPopups.length===n+1', arg=before)
            if not blocked:
                page.wait_for_function('()=>__qaPopups.at(-1).events.includes("print")')
                assert page.evaluate('__qaPopups.at(-1).events') == ['open', 'write', 'close', 'focus', 'print']
            capture(name + (' bloqueado' if blocked else ''))
    f.portal_status = 403
    before = page.evaluate('__qaPopups.length')
    page.evaluate('async()=>{await printEmployeePortalLink(31)}')
    assert page.evaluate('__qaPopups.length') == before
    capture('portal: 403 sem popup')
    assert page.evaluate('window.__xss || 0') == 0
    assert not f.errors, f.errors

    # Smoke adicional com Window/Document reais: interceptar somente focus/print evita o diálogo do SO.
    page.evaluate("""() => {
      window.__qaRealEvents=[];
      window.open=(...args)=>{const w=__qaNativeOpen(...args);if(w){
        w.focus=()=>__qaRealEvents.push('focus');w.print=()=>__qaRealEvents.push('print');
      }return w;};
    }""")
    with context.expect_page() as opened:
        page.evaluate("openAndPrintPopup('<!doctype html><html><head><title>QA</title></head><body><p id=qa>Olá &amp; €</p></body></html>') !== null")
    popup = opened.value
    popup.wait_for_load_state()
    page.wait_for_function('__qaRealEvents.includes("print")')
    events = page.evaluate('__qaRealEvents')
    assert events[0:2] == ['focus', 'print']
    assert popup.locator('#qa').inner_text() == 'Olá & €'
    popup.close()
    return {'steps': steps, 'real_popup': {'content': 'Olá & €', 'focus_before_print': True}}


def canonical(value, origin):
    if isinstance(value, str):
        return value.replace(origin, 'https://fixture.example.test')
    if isinstance(value, list):
        return [canonical(v, origin) for v in value]
    if isinstance(value, dict):
        return {k: canonical(v, origin) for k, v in value.items()}
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--static', type=Path, default=ROOT / 'static')
    parser.add_argument('--locales', nargs='+', default=base.LOCALES)
    parser.add_argument('--record', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(base.QuietHandler, directory=str(args.static)))
    Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    golden = {} if args.record else json.loads(GOLDEN.read_text())
    results = []
    try:
        with sync_playwright() as pw:
            options = {'headless': True, 'args': ['--no-sandbox']}
            if os.environ.get('CHROMIUM_EXECUTABLE'):
                options['executable_path'] = os.environ['CHROMIUM_EXECUTABLE']
            browser = pw.chromium.launch(**options)
            for locale in args.locales:
                context = browser.new_context(viewport={'width': 1440, 'height': 1000}, service_workers='block', locale=locale)
                page = context.new_page()
                page.clock.set_fixed_time('2026-11-15T12:00:00')
                page.set_default_timeout(8000)
                result = {'locale': locale, 'status': 'passed'}
                try:
                    f = Fixture(page, origin, locale)
                    f.open()
                    observed = exercise(f, context)
                    (args.output / f'{locale}-observed.json').write_text(json.dumps(observed, ensure_ascii=False, indent=1) + '\n')
                    expected = canonical(observed, origin)
                    if args.record:
                        golden[locale] = expected
                    elif expected != golden[locale]:
                        changed = [a['label'] for a, b in zip(expected['steps'], golden[locale]['steps'], strict=True) if a != b]
                        raise AssertionError('divergência: ' + ', '.join(changed))
                    result.update(steps=len(observed['steps']), real_popup=True)
                except Exception as error:  # noqa: BLE001 — registra o cenário e continua
                    result.update(status='failed', error=str(error))
                finally:
                    context.close()
                results.append(result)
                print(json.dumps(result, ensure_ascii=False), flush=True)
            browser.close()
    finally:
        server.shutdown()
    if args.record and all(r['status'] == 'passed' for r in results):
        GOLDEN.write_text(json.dumps(golden, ensure_ascii=False, indent=1) + '\n')
    (args.output / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
    return int(any(r['status'] != 'passed' for r in results))


if __name__ == '__main__':
    raise SystemExit(main())
