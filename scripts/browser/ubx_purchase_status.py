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

SEC-COMPRAS-1: o rótulo do badge passou a ser escapado. A referência continua a
gravada da main (não é regravada); na comparação, o conteúdo de cada <span> do
badge da referência passa pelo mesmo escape HTML — estrutura, classes e estilo
têm de bater byte a byte e os rótulos legítimos (sem & < > " ') saem idênticos.
Além disso, um cenário de segurança de ponta a ponta renderiza a lista real de
requisições e o detalhe real da PO com a API simulada devolvendo postponed_until
e status maliciosos, e exige nenhum elemento injetado, nenhuma execução e o
conteúdo visível como texto. O modal real do requisitante é aberto com itens
bloqueados (approved, ordered, received, closed) e tem de mostrar os rótulos
oficiais do idioma ativo (não o código interno), sem executar marcação, e fechar
ao cancelar. Esse cenário não roda em --record (na main ele
reprova, que é a vulnerabilidade).

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
RECORD = False
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


import html as _html
import re as _re

BADGE = _re.compile(r'^(<span class="status-chip" style="[^"]*">)([\s\S]*)(</span>)$')


def escaped_reference(value):
    """Expectativa pós-SEC-COMPRAS-1 a partir da referência da main: só o conteúdo do badge muda."""
    if isinstance(value, str):
        m = BADGE.match(value)
        return m.group(1) + _html.escape(m.group(2), quote=True).replace('&#x27;', '&#39;') + m.group(3) if m else value
    if isinstance(value, list):
        return [escaped_reference(v) for v in value]
    if isinstance(value, dict):
        return {k: escaped_reference(v) for k, v in value.items()}
    return value


PR_ID, PO_ID = 9301, 9302
PAYLOAD = '<img src=x onerror=window.__xss=(window.__xss||0)+1>'
SECURITY = """([prId, poId, payload]) => {
  const row = document.querySelector('#compras-req-tbody tr');
  const chips = [...document.querySelectorAll('#compras-req-tbody .status-chip, #compras-po-detail-info .status-chip')];
  return {
    rows: document.querySelectorAll('#compras-req-tbody tr').length,
    chips: chips.map((c) => ({ text: c.textContent, children: c.children.length, cls: c.className, style: c.getAttribute('style') })),
    injected: document.querySelectorAll('#compras-req-tbody img, #compras-po-detail-info img, #compras-req-tbody script, #compras-po-detail-info script').length,
    xss: window.__xss || 0,
    hasRow: !!row
  };
}"""


def security(f):
    """Lista de requisições e detalhe da PO reais, com postponed_until e status maliciosos vindos da API."""
    page = f.page
    for perm in ('purchase_requests:view', 'purchase_orders:view'):
        if perm not in f.permissions:
            f.permissions.append(perm)
    requests = {'items': [
        {'id': PR_ID, 'title': 'Requisição QA', 'unit_name': 'Unidade QA', 'status': 'postponed', 'postponed_until': PAYLOAD,
         'items_count': 1, 'created_by_name': 'QA', 'created_at': '2026-11-17T10:00:00'},
        {'id': PR_ID + 1, 'title': 'Status forjado', 'unit_name': 'Unidade QA', 'status': PAYLOAD, 'items_count': 0,
         'created_by_name': 'QA', 'created_at': '2026-11-17T10:00:00'}]}
    detail = {'item': {'id': PO_ID, 'po_number': 'PO-QA', 'supplier': 'Fornecedor QA', 'status': 'postponed',
                       'postponed_until': PAYLOAD, 'total_value': 0}, 'items': [], 'events': []}
    page.route('**/api/purchase-requests?**', lambda route: route.fulfill(json=requests))
    page.route(f'**/api/purchase-orders/{PO_ID}', lambda route: route.fulfill(json=detail))
    page.evaluate('async()=>{await loadBootstrap()}')
    f.view('compras')
    page.evaluate('async()=>{await globalThis.loadPurchaseRequests()}')
    page.wait_for_function("() => document.querySelectorAll('#compras-req-tbody tr').length >= 2")
    page.evaluate(f'async()=>{{await globalThis.openPoDetail({PO_ID})}}')
    page.wait_for_function("() => document.querySelector('#compras-po-detail-info .status-chip')")
    page.wait_for_timeout(300)
    result = page.evaluate(SECURITY, [PR_ID, PO_ID, PAYLOAD])
    assert result['injected'] == 0, f'elemento injetado no DOM: {result}'
    assert result['xss'] == 0, f'marcação executada: {result}'
    assert len(result['chips']) == 3, f'badges esperados: 3, obtidos {result["chips"]}'
    for chip in result['chips']:
        assert chip['children'] == 0, f'badge com elementos filhos: {chip}'
        assert chip['cls'] == 'status-chip', chip
        assert PAYLOAD in chip['text'], f'conteúdo não aparece como texto: {chip}'
    return result


LOCKED = ['approved', 'ordered', 'received', 'closed']
MODAL = """async ([locked, payload]) => {
  const items = [...locked.map((status, i) => ({ id: 100 + i, status, epi_name: 'EPI ' + status, quantity_requested: i + 1 })),
    { id: 200, status: 'open', epi_name: payload, quantity_requested: 2 }];
  const promise = openRequesterReviewModal({ id: 77, company_id: 901, notes: '' }, items);
  const modal = document.getElementById('requester-review-modal');
  const rows = [...modal.querySelectorAll('small')].map((s) => s.textContent);
  const injected = modal.querySelectorAll('img, script').length;
  modal.querySelector('#rr-cancel').click();
  const result = await promise;
  return { rows, injected, closed: !document.getElementById('requester-review-modal'), result,
           itemsIntact: items.slice(0, locked.length).map((i) => i.status) };
}"""


def requester_modal(f):
    """Modal real do requisitante: rótulos oficiais dos itens bloqueados no idioma ativo."""
    page = f.page
    cat, fallback = commercial.catalog(f.locale), commercial.catalog('pt-BR')
    src = (ROOT / 'static/js/modules/purchases/ui/purchase-status-view.js').read_text(encoding='utf-8')
    block = src[src.index('const ITEM_STATUS_LABELS = {'):]
    block = block[:block.index('};')]
    declared = {m.group(1): m.group(2) for m in _re.finditer(r"get (\w+)\(\) \{ return \(tr\('([^']+)'", block)}
    expected = []
    for status in LOCKED:
        try:
            expected.append('(' + commercial.leaf(cat, declared[status]) + ')')
        except KeyError:
            expected.append('(' + commercial.leaf(fallback, declared[status]) + ')')
    result = page.evaluate(MODAL, [LOCKED, PAYLOAD])
    assert result['rows'] == expected, f'rótulos do modal: {result["rows"]} esperados {expected}'
    assert result['injected'] == 0 and page.evaluate('window.__xss || 0') == 0, f'marcação executada no modal: {result}'
    assert result['closed'] and result['result'] is None, f'cancelar não fechou o modal: {result}'
    assert result['itemsIntact'] == LOCKED, f'códigos internos alterados: {result}'
    return {'rows': result['rows']}


def actions(f):
    page = f.page
    steps = [{'label': 'funções', 'result': page.evaluate(EXERCISE, [STATUSES])}]
    other = 'fr-FR' if f.locale != 'fr-FR' else 'nb-NO'
    page.evaluate('(l)=>EpiI18n.setLang(l,{persist:false})', other)
    page.wait_for_function('(l)=>EpiI18n.lang===l', arg=other)
    steps.append({'label': f'troca de idioma ({other})', 'result': page.evaluate(EXERCISE, [STATUSES])})
    return steps


def _flatten(value):
    if isinstance(value, list):
        for v in value:
            yield from _flatten(v)
    elif isinstance(value, dict):
        for v in value.values():
            yield from _flatten(v)
    else:
        yield value


def run_locale(origin, browser, locale):
    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, service_workers='block', locale=locale)
    page = context.new_page()
    page.clock.set_fixed_time(FIXED_NOW)
    page.set_default_timeout(8000)
    f = commercial.Fixture(page, origin, locale)
    try:
        f.open()
        steps = actions(f)
        if not RECORD:
            steps.append({'label': 'SEC-COMPRAS-1 (lista e detalhe reais)', 'security': security(f)})
            steps.append({'label': 'modal do requisitante (rótulos oficiais)', 'security': requester_modal(f)})
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
    global RECORD
    RECORD = args.record
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
                    reference = escaped_reference(golden[locale]['steps'])
                    equivalence = [step for step in observed['steps'] if 'security' not in step]
                    for i, (now, before) in enumerate(zip(equivalence, reference, strict=True)):
                        if now != before:
                            raise AssertionError(f'passo {i} ({now["label"]}) difere da referência: '
                                                 f'atual {json.dumps(now, ensure_ascii=False)[:700]} '
                                                 f'antes {json.dumps(before, ensure_ascii=False)[:700]}')
                result.update(steps=len(observed['steps']))
                if not args.record:
                    result['escaped_badges'] = sum(1 for now, ref in zip(_flatten(golden[locale]['steps']), _flatten(reference)) if now != ref)
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
