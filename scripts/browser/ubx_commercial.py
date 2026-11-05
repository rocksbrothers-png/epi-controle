"""UBX Comercial, fatia C1 — Chromium: SPA real + API sintética interceptada; nunca abre banco.

Equivalência no navegador real, nos 5 idiomas, entre a apresentação comercial
extraída (static/js/modules/commercial/{business,ui}) e a cópia literal do
app.js de antes da extração (static/js/test/fixtures/app-before-ubx-commercial-c1.js.txt).

Para cada idioma, na tela Comercial do Administrador Master (mesmo harness de
scripts/browser/i18n_commercial.py: empresa vencendo em 5 dias, nome e ator com
marcação, histórico com detalhes):

1. Renderiza KPIs, cartões de resumo, alertas, vencimentos, histórico e o
   formulário do contrato (opções de plano e dica) com os módulos.
2. Renderiza de novo com os módulos (a renderização é determinística).
3. Injeta a cópia literal do app.js de antes, que redefine as 13 funções
   globais, e renderiza de novo pelos MESMOS chamadores do app.js.
4. O HTML dos painéis, das opções de plano e o texto da dica são idênticos.
5. Nenhuma gravação, nenhum erro de página e nenhuma marcação executada
   durante as três renderizações. As únicas requisições são a leitura do
   contrato (GET /api/commercial-contract) que o próprio fillCommercialForm do
   app.js faz, uma por renderização, igual com os módulos e com o original.

python scripts/browser/ubx_commercial.py --output /tmp/ubx-commercial
CHROMIUM_EXECUTABLE=/usr/bin/chromium seleciona um navegador já instalado.
"""
import argparse
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fix_colab_terc as base
import i18n_commercial as commercial

ROOT = base.ROOT
LOCALES = base.LOCALES
FIXTURE = ROOT / 'static/js/test/fixtures/app-before-ubx-commercial-c1.js.txt'
NAMES = ['planEntries', 'planLabel', 'planOptionMarkup', 'planHintText', 'commercialRiskMeta', 'commercialActions',
         'commercialAlertTone', 'renderCommercialSummaryCard', 'renderCommercialAlertCard', 'renderCommercialExpiringCard',
         'formatCommercialAuditDetails', 'renderCommercialHistoryItem', 'formatCommercialDetails']
SNAPSHOT = """() => ({
  panels: ['#commercial-stats', '#commercial-summary', '#commercial-alerts', '#commercial-expiring', '#commercial-history']
    .map((sel) => document.querySelector(sel)?.innerHTML ?? null),
  planOptions: document.querySelector('#commercial-form [name="plan_name"]')?.innerHTML ?? null,
  planHint: document.getElementById('commercial-plan-hint')?.textContent ?? null
})"""
RERENDER = """() => {
  renderCommercialStats();
  renderCommercialSummary();
  renderCommercialAlerts();
  renderCommercialExpiring();
  renderCommercialHistory();
  fillCommercialForm(901);
}"""


def equivalence(f):
    f.company_list[0]['contract_end'] = (datetime.now(UTC).date() + timedelta(days=5)).isoformat()
    f.page.evaluate('async()=>{await loadBootstrap()}')
    f.view('comercial')
    f.tab('comercial', 'contratos')
    f.page.evaluate('fillCommercialForm(901)')
    f.page.wait_for_function("document.getElementById('commercial-contract-status')?.textContent.length>0")
    f.page.wait_for_timeout(200)
    owners = f.page.evaluate('(names)=>names.map((n)=>[n, typeof globalThis[n], '
                             '(globalThis.__EPI_COMMERCIAL_PRESENTATION__?.[n] || globalThis.__EPI_COMMERCIAL_RULES__?.[n]) === globalThis[n]])',
                             NAMES)
    assert all(kind == 'function' and same for _, kind, same in owners), owners
    before_calls = len(f.calls)

    f.page.evaluate(RERENDER)
    f.page.wait_for_timeout(300)
    modules_1 = f.page.evaluate(SNAPSHOT)
    reads_modules = len(f.calls) - before_calls
    f.page.evaluate(RERENDER)
    f.page.wait_for_timeout(300)
    modules_2 = f.page.evaluate(SNAPSHOT)
    assert modules_1 == modules_2, 'renderização com os módulos não é determinística'
    assert all(modules_1['panels']) and modules_1['planOptions'], modules_1

    f.page.add_script_tag(content=FIXTURE.read_text(encoding='utf-8'))
    replaced = f.page.evaluate('(names)=>names.every((n)=>globalThis[n] !== (globalThis.__EPI_COMMERCIAL_PRESENTATION__?.[n]'
                               ' || globalThis.__EPI_COMMERCIAL_RULES__?.[n]))', NAMES)
    assert replaced, 'a cópia do app.js de antes não substituiu as funções globais'
    before_original = len(f.calls)
    f.page.evaluate(RERENDER)
    f.page.wait_for_timeout(300)
    original = f.page.evaluate(SNAPSHOT)
    reads_original = len(f.calls) - before_original

    for index, (after, before) in enumerate(zip(modules_1['panels'], original['panels'])):
        assert after == before, f'painel {index} difere:\nmódulos: {after[:600]}\noriginal: {before[:600]}'
    assert modules_1 == original, {'modules': modules_1, 'original': original}
    calls = [c for c in f.calls[before_calls:] if not c['path'].startswith('/api/i18n/')]
    unexpected = [c for c in calls if (c['method'], c['path']) != ('GET', '/api/commercial-contract')]
    assert unexpected == [], f'renderização disparou requisições inesperadas: {unexpected}'
    assert reads_modules == reads_original, (reads_modules, reads_original)
    assert f.page.evaluate('window.__xss || 0') == 0, 'marcação executada'
    f.result_extra = {'panel_sizes': [len(p) for p in original['panels']], 'plan_options_size': len(original['planOptions'])}


SCENARIOS = [equivalence]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/ubx-commercial-browser'))
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
                fixture = commercial.Fixture(page, origin, locale)
                result = {'locale': locale, 'scenario': scenario.__name__, 'status': 'passed'}
                try:
                    fixture.open()
                    scenario(fixture)
                    assert not fixture.errors, f'page errors: {fixture.errors}'
                    result.update(getattr(fixture, 'result_extra', {}))
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
