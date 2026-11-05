"""SEC-C1-1 — Chromium: SPA real + API sintética interceptada; nunca abre banco.

O rótulo do plano comercial é texto livre gravado pelo Administrador Master em
/api/commercial-settings e chega à tela pelo bootstrap. planOptionMarkup monta as
<option> do formulário de contrato e o resultado entra no <select> por innerHTML;
no Chromium atual, marcação dentro de <option> é interpretada e executa.

Para cada um dos 5 idiomas, com rótulos (e, como defesa em profundidade, uma
chave) maliciosos vindos do bootstrap:

1. Nenhum payload executa (window.__xss continua 0) ao abrir o Comercial, ao
   preencher o formulário e ao trocar de plano.
2. O <select> tem uma <option> por plano e nada mais; cada value é a chave exata
   e cada texto é o rótulo exato (ida e volta sem perda, inclusive Unicode e
   entidades já escritas no rótulo).
3. A seleção funciona: o plano da empresa vem selecionado, trocar o plano
   atualiza a dica com o rótulo como texto, e salvar envia a chave crua em
   PUT /api/companies/<id> (contrato HTTP inalterado).

python scripts/browser/security_commercial_plan_xss.py --output /tmp/sec-c1-1
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
import i18n_commercial as commercial
import ubx_companies as ubx

ROOT = base.ROOT
LOCALES = base.LOCALES
MARK = 'window.__xss=(window.__xss||0)+1'
# As cinco chaves que o backend emite, com rótulos maliciosos, e uma sexta chave
# maliciosa (o backend não a emite; o frontend não deve confiar nisso).
PLANS = {
    'individual': {'label': f'<script>{MARK}</script>', 'min_users': 1, 'max_users': 1},
    'start': {'label': f'"><img src=x onerror={MARK}>', 'min_users': 1, 'max_users': 10},
    'business': {'label': f"</option></select><svg onload={MARK}></svg>", 'min_users': 11, 'max_users': 25},
    'corporate': {'label': f'<details open ontoggle={MARK}>&lt;b&gt; &amp; \' "', 'min_users': 26, 'max_users': 100},
    'enterprise': {'label': 'Enterprise — 日本語 🚀 Ωμέγα ñ', 'min_users': 101, 'max_users': None},
    f'x" autofocus onfocus="{MARK}" y="': {'label': f"' onmouseover='{MARK}'", 'min_users': 1, 'max_users': 2},
}


class Fixture(commercial.Fixture):
    def route(self, route):
        request = route.request
        if urlsplit(request.url).path == '/api/bootstrap':
            original = route.fulfill

            def fulfill(**kwargs):
                payload = kwargs.get('json') or {}
                payload['commercial_settings'] = {'unit_price': 42, 'plans': PLANS}
                kwargs['json'] = payload
                return original(**kwargs)
            route.fulfill = fulfill
        return super().route(route)


def assert_no_execution(f, step):
    f.page.wait_for_timeout(400)
    count = f.page.evaluate('window.__xss || 0')
    assert count == 0, f'{step}: payload executou {count} vez(es)'


def plan_options(f):
    return f.page.evaluate("""() => {
      const select = document.querySelector('#commercial-form [name="plan_name"]');
      return {
        options: [...select.options].map((o) => ({ value: o.value, text: o.textContent, selected: o.selected })),
        children: [...select.children].map((c) => c.tagName),
        descendants: select.querySelectorAll('*').length,
        value: select.value
      };
    }""")


def plan_xss(f):
    f.page.evaluate('async()=>{await loadBootstrap()}')
    f.view('comercial')
    f.tab('comercial', 'contratos')
    f.page.evaluate('fillCommercialForm(901)')
    f.page.wait_for_function("document.getElementById('commercial-contract-status')?.textContent.length>0")
    assert_no_execution(f, 'abrir o formulário')

    state = plan_options(f)
    keys = list(PLANS)
    assert state['children'] == ['OPTION'] * len(keys), state['children']
    assert state['descendants'] == len(keys), f"elementos além das opções dentro do <select>: {state['descendants']}"
    assert [o['value'] for o in state['options']] == keys, state['options']
    assert [o['text'] for o in state['options']] == [PLANS[k]['label'] for k in keys], state['options']
    company_plan = next(c for c in f.company_list if c['id'] == 901)['plan_name']
    assert state['value'] == company_plan, (state['value'], company_plan)

    # Trocar o plano: a dica mostra o rótulo como TEXTO (planHintText -> textContent).
    select = f.page.locator('#commercial-form [name="plan_name"]')
    select.select_option('enterprise')
    select.dispatch_event('change')
    hint = f.page.locator('#commercial-plan-hint').text_content()
    assert PLANS['enterprise']['label'] in hint, hint
    select.select_option('corporate')
    select.dispatch_event('change')
    hint = f.page.locator('#commercial-plan-hint').text_content()
    assert PLANS['corporate']['label'] in hint, hint
    assert f.page.locator('#commercial-plan-hint *').count() == 0, 'marcação interpretada na dica'
    assert_no_execution(f, 'trocar o plano')

    # Salvar envia a chave crua (contrato HTTP inalterado).
    before = len(f.calls)
    f.page.locator('#commercial-form').evaluate('(form) => form.requestSubmit()')
    f.page.wait_for_timeout(600)
    sent = ubx.writes(f, before)
    puts = [c for c in sent if (c['method'], c['path']) == ('PUT', '/api/companies/901')]
    assert puts, f'nenhum PUT de contrato: {sent}'
    assert puts[0]['body']['plan_name'] == 'corporate', puts[0]['body']
    assert_no_execution(f, 'salvar')


SCENARIOS = [plan_xss]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/sec-c1-1-browser'))
    parser.add_argument('--locales', nargs='+', default=LOCALES)
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
            for scenario in SCENARIOS:
                context = browser.new_context(viewport={'width': 1440, 'height': 1000}, service_workers='block', locale=locale)
                page = context.new_page()
                page.set_default_timeout(5000)
                fixture = Fixture(page, origin, locale)
                result = {'locale': locale, 'scenario': scenario.__name__, 'status': 'passed'}
                try:
                    fixture.open()
                    scenario(fixture)
                    assert not fixture.errors, f'page errors: {fixture.errors}'
                except Exception as error:  # noqa: BLE001 — registra a falha do cenário e segue
                    result.update(status='failed', error=str(error))
                finally:
                    result.update(calls=fixture.calls, dialogs=fixture.dialogs, page_errors=fixture.errors,
                                  blocked_external_requests=fixture.external)
                    page.screenshot(path=str(args.output / f'{locale}-{scenario.__name__}.png'), full_page=False)
                    results.append(result)
                    print(f"{locale} {scenario.__name__}: {result['status']} {result.get('error', '')[:300]}", flush=True)
                    context.close()
        browser.close()
    server.shutdown()
    (args.output / 'results.json').write_text(json.dumps(results, indent=2, ensure_ascii=False) + '\n')
    return int(any(result['status'] != 'passed' for result in results))


if __name__ == '__main__':
    raise SystemExit(main())
