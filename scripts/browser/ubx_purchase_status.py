"""UBX Compras P1 — Chromium: SPA real + API sintética interceptada; nunca abre banco.

Equivalência, no navegador real e nos 5 idiomas, da apresentação de status de
Compras depois da extração — buildPoStepper e purchaseStatusBadge
(modules/purchases/ui/purchase-status-view.js) e isBuyerQuotationStatus
(modules/purchases/business/purchase-status-rules.js) — com o comportamento de
ANTES da P1, chamando as globais legadas que o app.js e a página usam.

O "antes" é uma referência gravada (static/js/test/fixtures/ubx-purchases-p1-browser.json),
produzida rodando ESTE MESMO roteiro contra o static/ da main anterior à P1
(`--record --static <worktree da main>/static`). Para cada idioma, com o relógio
do navegador fixo:

1. os três globais com todos os status conhecidos, valores de borda e extras;
2. a visibilidade no globalThis (os mapas de rótulos seguem fora dele, como antes:
   views/purchases.js depende disso);
3. troca de idioma sem recarregar e nova chamada.

Compara tudo com a referência e exige nenhum erro de página e nenhuma marcação
executada.

python scripts/browser/ubx_purchase_status.py --output /tmp/ubx-purchases-p1
python scripts/browser/ubx_purchase_status.py --record --static /caminho/da/main/static
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

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fix_colab_terc as base
import i18n_commercial as commercial

ROOT = base.ROOT
LOCALES = base.LOCALES
GOLDEN = ROOT / 'static/js/test/fixtures/ubx-purchases-p1-browser.json'
FIXED_NOW = '2026-11-17T12:00:00'
STATUSES = ['draft', 'open', 'sent_to_buyer', 'returned_to_buyer', 'quoted', 'waiting_quote', 'waiting_admin_review',
            'pending_approval', 'partially_approved', 'waiting_buyer_correction', 'buyer_resubmitted',
            'waiting_requester_correction', 'requester_resubmitted', 'approved', 'rejected', 'postponed', 'ordered',
            'po_generated', 'received_partial', 'received', 'not_received', 'pending_receipt', 'checked', 'closed',
            'cancelled', 'included_in_request', 'unknown_status', 'APPROVED', ' approved', '', '0', 'constructor',
            '__proto__', 'toString', '<img src=x onerror=window.__xss=(window.__xss||0)+1>']
EXERCISE = """([statuses]) => {
  const values = [...statuses, undefined, null, 0, false, true, NaN];
  const extras = ['', 'Até 2026-11-20', 0, null, undefined, 'a — b'];
  const settle = (fn) => { try { return ['ok', fn()]; } catch (e) { return ['threw', String(e)]; } };
  return {
    globals: ['buildPoStepper', 'purchaseStatusBadge', 'isBuyerQuotationStatus', 'PURCHASE_STATUS_LABELS',
      'ITEM_STATUS_LABELS', 'PO_STEPPER_STEPS', 'PO_STEP_INDEX', 'PURCHASE_BUYER_QUOTE_STATUSES'].map((n) => [n, typeof globalThis[n]]),
    rows: values.map((s) => [String(s), settle(() => buildPoStepper(s)), settle(() => isBuyerQuotationStatus(s)),
      extras.map((x) => settle(() => purchaseStatusBadge(s, x))), settle(() => purchaseStatusBadge(s))]),
    noArgs: [settle(() => buildPoStepper()), settle(() => isBuyerQuotationStatus()), settle(() => purchaseStatusBadge())]
  };
}"""


def actions(f):
    page = f.page
    steps = [{'label': 'funções', 'result': page.evaluate(EXERCISE, [STATUSES])}]
    other = 'fr-FR' if f.locale != 'fr-FR' else 'nb-NO'
    page.evaluate('(l)=>EpiI18n.setLang(l,{persist:false})', other)
    page.wait_for_function('(l)=>EpiI18n.lang===l', arg=other)
    steps.append({'label': f'troca de idioma ({other})', 'result': page.evaluate(EXERCISE, [STATUSES])})
    return steps


def run_locale(origin, browser, locale):
    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, service_workers='block', locale=locale)
    page = context.new_page()
    page.clock.set_fixed_time(FIXED_NOW)
    page.set_default_timeout(8000)
    f = commercial.Fixture(page, origin, locale)
    try:
        f.open()
        steps = actions(f)
        assert not f.errors, f'page errors: {f.errors}'
        xss = page.evaluate('window.__xss || 0')
        assert xss == 0, f'marcação executada {xss} vez(es)'
        return {'steps': steps}
    finally:
        context.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/ubx-purchases-p1'))
    parser.add_argument('--locales', nargs='+', default=LOCALES)
    parser.add_argument('--static', type=Path, default=ROOT / 'static', help='pasta static/ servida (padrão: a desta branch)')
    parser.add_argument('--record', action='store_true', help='grava a referência a partir de --static em vez de comparar')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(base.QuietHandler, directory=str(args.static)))
    Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    golden = {} if args.record else json.loads(GOLDEN.read_text(encoding='utf-8'))
    results = []
    with sync_playwright() as playwright:
        options = {'headless': True, 'args': ['--no-sandbox']}
        if os.environ.get('CHROMIUM_EXECUTABLE'):
            options['executable_path'] = os.environ['CHROMIUM_EXECUTABLE']
        browser = playwright.chromium.launch(**options)
        for locale in args.locales:
            result = {'locale': locale, 'scenario': 'equivalence', 'status': 'passed'}
            try:
                observed = run_locale(origin, browser, locale)
                (args.output / f'{locale}-observed.json').write_text(json.dumps(observed, indent=1, ensure_ascii=False) + '\n')
                if args.record:
                    golden[locale] = observed
                else:
                    for i, (now, before) in enumerate(zip(observed['steps'], golden[locale]['steps'], strict=True)):
                        if now != before:
                            raise AssertionError(f'passo {i} ({now["label"]}) difere da referência: '
                                                 f'atual {json.dumps(now, ensure_ascii=False)[:700]} '
                                                 f'antes {json.dumps(before, ensure_ascii=False)[:700]}')
                result.update(steps=len(observed['steps']))
            except Exception as error:  # noqa: BLE001 — registra a falha do cenário e segue
                result.update(status='failed', error=str(error))
            results.append(result)
            print(f"{locale} equivalence: {result['status']} {result.get('error', '')[:900]}", flush=True)
        browser.close()
    server.shutdown()
    if args.record and all(r['status'] == 'passed' for r in results):
        GOLDEN.write_text(json.dumps(golden, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (args.output / 'results.json').write_text(json.dumps(results, indent=2, ensure_ascii=False) + '\n')
    return int(any(result['status'] != 'passed' for result in results))


if __name__ == '__main__':
    raise SystemExit(main())
