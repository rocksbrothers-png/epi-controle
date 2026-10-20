'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const source = fs.readFileSync(path.resolve(__dirname, '../../app.js'), 'utf8');
function functionSource(name) {
  const start = new RegExp('^(?:async )?function ' + name + '\\(', 'm').exec(source);
  if (!start) throw new Error('Função ausente: ' + name);
  const end = source.slice(start.index + start[0].length).search(/^}/m);
  return source.slice(start.index, start.index + start[0].length + end + 1);
}

function harness() {
  const nodes = new Map(), sent = [], toasts = [], modalCalls = [];
  let selected = [], allowed = true;
  const node = (id) => {
    if (!nodes.has(id)) nodes.set(id, { id, value: '', innerHTML: '', textContent: '', style: {},
      listeners: {}, dataset: {}, remove() {},
      querySelector: (selector) => node(selector.slice(1)) });
    return nodes.get(id);
  };
  const context = {
    console, URLSearchParams, Map, Array,
    crypto: { randomUUID: () => '12345678901234567890123456789012' },
    document: { getElementById: node, querySelectorAll: () => selected,
      createElement: () => node('overlay'), body: { appendChild() {} } },
    state: { user: { id: 1 } },
    bindAppListener: (target, event, callback) => { target.listeners[event] = callback; },
    esc: (s) => String(s ?? ''), tr: (_key, fallback) => fallback,
    FileReader: class { readAsDataURL(file) { this.result = 'data:image/png;base64,RE9DVU1FTlRP'; if (file.fail) this.onerror(); else this.onload(); } },
    hasPermission: () => allowed, showToast: (...args) => toasts.push(args),
    _blockedStockContext: () => ({ companyId: '2', unitId: '5' }),
    _stockPanelRequests: new Map(),
    api: async (url, options) => { sent.push({ url, body: JSON.parse(options.body) }); return { items: [] }; },
    apiWithBootstrapRetry: async () => ({ items: [] }),
    loadPendingRegularization: async () => {}, loadValidityOverview: async () => {}, loadBlockedStock: async () => {}
  };
  vm.createContext(context);
  const names = ['readStockEvidenceFile', 'openRegularizeValidityModal', 'regularizePendingPiece',
    'regularizeSelectedStockLot', 'reconcileStockLot', 'loadStockLotEvidence', '_startStockPanelLoad', '_stockPanelLoadMessage', '_stockPanelLoadError'];
  vm.runInContext(names.map(functionSource).join('\n'), context);
  return {
    node, sent, toasts, modalCalls, context,
    run: (code) => vm.runInContext(code, context),
    allowed: (value) => { allowed = value; },
    selected: (rows) => { selected = rows.map((dataset) => ({ dataset })); },
    captureModal: () => { context.openRegularizeValidityModal = async (piece) => { modalCalls.push(piece); return null; }; }
  };
}

const file = { name: 'etiqueta.png', type: 'image/png', size: 68 };
module.exports = ({ testAsync, assert, eq }) => {
  testAsync('Lote físico: seleção exige mesmo EPI/unidade e transmite todos os QRs explícitos', async () => {
    const h = harness(); h.captureModal();
    const a = { id: '1', qr: 'QR-1', epi: '10', unit: '5', name: 'Luva', lot: '' };
    h.selected([a, { ...a, id: '2', qr: 'QR-2', epi: '11' }]);
    await h.run('regularizeSelectedStockLot()');
    eq(h.modalCalls.length, 0); eq(h.toasts.length, 1);
    h.selected([a, { ...a, id: '2', qr: 'QR-2' }]);
    await h.run('regularizeSelectedStockLot()');
    eq(h.modalCalls.length, 1);
    eq(h.modalCalls[0].items.length, 2);
    eq(h.modalCalls[0].items[1].qr_code, 'QR-2');
  });

  testAsync('Lote físico: sem seleção ou sem permissão não abre conferência', async () => {
    const h = harness(); h.captureModal();
    await h.run('regularizeSelectedStockLot()');
    eq(h.modalCalls.length, 0); eq(h.toasts.length, 1);
    h.allowed(false); h.selected([{ id: '1', qr: 'QR-1', epi: '10', unit: '5' }]);
    await h.run('regularizeSelectedStockLot()');
    eq(h.modalCalls.length, 0);
  });

  testAsync('Lote físico: modal exige lote, anexo e conferência física antes de confirmar', async () => {
    const h = harness();
    const promise = h.run("openRegularizeValidityModal({ id: 1, qr: 'QR-1', epiName: 'Luva' })");
    h.node('reg-date').value = '2027-01-01';
    h.node('reg-evidence').value = 'Etiqueta';
    h.node('reg-justification').value = 'Conferência';
    h.node('reg-source').value = 'label';
    const confirm = h.node('reg-confirm').listeners.click;
    await confirm(); assert(h.node('reg-error').textContent.includes('lote real'));
    h.node('reg-lot').value = 'A';
    await confirm(); assert(h.node('reg-error').textContent.includes('conferência física'));
    h.node('reg-physical-confirm').checked = true;
    await confirm(); assert(h.node('reg-error').textContent.includes('Anexe foto'));
    h.node('reg-file').files = [file];
    await confirm();
    const result = await promise;
    eq(result.lot, 'A'); eq(result.file.filename, 'etiqueta.png');
    eq(result.source, 'label');
  });

  testAsync('Lote físico: leitura do arquivo rejeita formato, tamanho e falha de leitura', async () => {
    const h = harness();
    for (const candidate of [{ ...file, type: 'text/html' }, { ...file, size: 4 * 1024 * 1024 }, { ...file, fail: true }]) {
      h.node('input').files = [candidate];
      let failed = false;
      try { await h.run("readStockEvidenceFile(document.getElementById('input'))"); } catch { failed = true; }
      assert(failed);
    }
  });

  testAsync('Lote físico: regularização envia lote, prova e seleção ao endpoint próprio', async () => {
    const h = harness();
    h.context.openRegularizeValidityModal = async () => ({ date: '2027-01-01', evidence: 'Etiqueta A',
      justification: 'Conferência', lot: 'A', source: 'label', file: { filename: 'etiqueta.png' } });
    await h.run("regularizePendingPiece({ id: 1, qr: 'QR-1', unitId: 5, items: [{ stock_item_id: 1, qr_code: 'QR-1' }, { stock_item_id: 2, qr_code: 'QR-2' }] })");
    eq(h.sent.length, 1);
    assert(h.sent[0].url.includes('/lots/'));
    eq(h.sent[0].body.items.length, 2);
    eq(h.sent[0].body.lot_code, 'A'); eq(h.sent[0].body.physical_lot_confirmed, true);
    eq(h.sent[0].body.evidence_file.filename, 'etiqueta.png');
  });

  testAsync('Lote físico: consulta distingue erro de lote vazio e renderiza download autenticado', async () => {
    const h = harness();
    h.context.apiWithBootstrapRetry = async () => { throw new Error('503'); };
    await h.run('loadStockLotEvidence()');
    assert(h.node('stock-lot-status').textContent.includes('Não foi possível carregar'));
    eq(h.node('stock-lot-empty').style.display, 'none');
    h.context.apiWithBootstrapRetry = async () => ({ items: [{ id: 8, lot_code: 'A', has_file: true }] });
    await h.run('loadStockLotEvidence()');
    assert(h.node('stock-lot-tbody').innerHTML.includes('data-lot-evidence="8"'));
  });

  testAsync('Lote físico: conciliação envia contagem explícita e apresenta os QRs gerados', async () => {
    const h = harness();
    h.node('stock-epi').value = '10';
    h.context.openRegularizeValidityModal = async (piece) => {
      assert(piece.reconcile);
      return { date: '2027-01-01', evidence: 'Etiqueta', justification: 'Contagem',
        lot: 'A', source: 'label', file: {}, quantity: 2, size: 'M', manufacture: '' };
    };
    const requests = [], printed = [];
    h.context.api = async (url, options) => { requests.push({ url, body: JSON.parse(options.body) }); return { qr_labels: [{ qr_code_value: 'NOVO-QR' }] }; };
    h.context.printStockLabels = (labels) => printed.push(labels);
    h.context.__EPI_REFRESH_ESTOQUE_LISTA__ = async () => {};
    await h.run('reconcileStockLot()');
    eq(requests.length, 1);
    assert(requests[0].url.endsWith('/reconcile'));
    eq(requests[0].body.quantity, 2); eq(requests[0].body.epi_id, 10);
    eq(requests[0].body.physical_lot_confirmed, true);
    assert(requests[0].body.idempotency_key);
    eq(printed.length, 1); eq(printed[0][0].qr_code_value, 'NOVO-QR');
    eq(h.node('stock-lot-reconcile').disabled, false);
  });

  testAsync('Lote físico: cancelar conciliação não envia dados e restaura o botão', async () => {
    const h = harness();
    h.node('stock-epi').value = '10'; h.captureModal();
    await h.run('reconcileStockLot()');
    eq(h.sent.length, 0); eq(h.node('stock-lot-reconcile').disabled, false);
  });
};
