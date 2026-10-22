'use strict';
// Importação de cotação (Compras): executa o views/purchases.js REAL num
// contexto isolado, com DOM mínimo, e verifica o que chega ao backend.
// Cobre os dois defeitos corrigidos: `_currentPrDetail` invisível (nenhuma
// linha associada) e fallback silencioso quando as regras não carregam
// (prévia com R$ 0,00 e quantidade 1 sem aviso).
const fs = require('fs'), path = require('path'), vm = require('vm');
const JS_ROOT = path.resolve(__dirname, '..');
const read = (rel) => fs.readFileSync(path.join(JS_ROOT, rel), 'utf8');
const appSource = fs.readFileSync(path.resolve(JS_ROOT, '..', 'app.js'), 'utf8');

// Regras de conciliação: do módulo UBX quando ele existir; senão, das
// declarações originais do app.js (o teste vale antes e depois da extração).
const BUSINESS_MODULE = 'modules/purchases/business/purchase-import-matching.js';
const BUSINESS_FNS = ['_normalizeCa', '_parsePurchaseMoney', '_parsePurchaseQuantity', '_normalizePurchaseText',
  '_normalizePurchaseSize', '_normalizePurchaseOrigin', '_scorePurchaseImportMatch', '_matchPurchaseImportRows'];
function businessSource() {
  if (fs.existsSync(path.join(JS_ROOT, BUSINESS_MODULE))) { return read(BUSINESS_MODULE); }
  return BUSINESS_FNS.map((name) => {
    const start = new RegExp('^function ' + name + '\\(', 'm').exec(appSource);
    if (!start) { throw new Error('função ausente no app.js: ' + name); }
    const end = appSource.slice(start.index).search(/^}/m);
    return appSource.slice(start.index, start.index + end + 1);
  }).join('\n') + '\n' + BUSINESS_FNS.map((n) => `globalThis.${n} = ${n};`).join('\n');
}

const PR = { id: 999, status: 'sent_to_buyer', unit_id: 1 };
const DETAIL = {
  item: PR,
  items: [
    { id: 501, epi_id: 11, epi_name: 'Luva Nitrílica', ca: '12345', glove_size: 'M', quantity_requested: 10, origin: 'stock_minimum' },
    { id: 502, epi_id: 12, epi_name: 'Óculos de Proteção', ca: '67890', quantity_requested: 4, employee_name: 'João Silva', origin: 'employee_request' },
    { id: 503, epi_id: 13, epi_name: 'Bota de Segurança', ca: '11111', size: '42', quantity_requested: 2, origin: 'stock_minimum' }
  ]
};
const PARSED = [
  { epi: 'Luva nitrilica', ca: 'CA 12345', tamanho_luva: 'M', qtd: '10', valor_unitario: 'R$ 1.234,56' },
  { epi: 'Oculos de protecao', colaborador: 'joão silva', qtd: '3,6', valor_unitario: '12.5' },
  { item_id: '503', epi: 'Bota', tamanho: '42', qtd: '', valor_unitario: '89,90' },
  { epi: 'Capacete inexistente', ca: '99999', qtd: '1', valor_unitario: '50,00' }
];

function harness({ withBusiness = true, withParser = true, detail = DETAIL } = {}) {
  const nodes = new Map();
  const node = (id) => {
    if (!nodes.has(id)) { nodes.set(id, { id, value: '', style: {}, textContent: '', innerHTML: '', files: [{ name: 'cotacao.csv' }] }); }
    return nodes.get(id);
  };
  const sent = [];
  const dialogs = [];
  const context = {
    console, Promise, Set, Map, Array, Object, String, Number, JSON, Math, Error,
    document: { getElementById: node, querySelector: () => null, querySelectorAll: () => [] },
    confirm: (msg) => { dialogs.push(msg); return true; },
    escapeHtml: (v) => String(v ?? ''),
    __EPI_APP_STATE__: { user: { id: 7 } },
    api: async (url, options) => { sent.push({ url, body: JSON.parse(options.body) }); return { ok: true }; },
    openPrDetail: async () => {}, loadPurchaseRequests: () => {}, loadPurchaseOrders: () => {}
  };
  context.globalThis = context;
  vm.createContext(context);
  if (withParser) { context._parsePoImportFile = async () => PARSED.map((r) => ({ ...r })); }
  if (detail) { context._currentPrDetail = detail; }
  if (withBusiness) { vm.runInContext(businessSource(), context); }
  vm.runInContext(read('views/purchases.js'), context);
  context.initPoCsvImport(PR);
  return {
    context, sent, dialogs, node,
    preview: () => node('req-po-csv-preview-btn').onclick(),
    savePrices: () => node('req-po-save-prices-btn').onclick(),
    submitPo: () => { node('req-po-csv-supplier').value = 'ACME'; return node('req-po-csv-submit-btn').onclick(); },
    feedback: () => node('req-po-csv-feedback').textContent
  };
}

module.exports = ({ test, testAsync, assert, eq }) => {
  test('Cotação: app.js publica _currentPrDetail na ponte de acessores de globalThis', () => {
    const bridge = appSource.slice(appSource.indexOf("['_purchaseDemands'"), appSource.indexOf('].forEach(([name, get, set])'));
    assert(bridge.includes("['_currentPrDetail', () => _currentPrDetail,"), 'ponte sem _currentPrDetail');
  });

  testAsync('Cotação: prévia mostra quantidades, preços e total', async () => {
    const h = harness();
    await h.preview();
    eq(h.feedback(), '');
    const html = h.node('req-po-csv-preview-tbody').innerHTML;
    assert(html.includes('<td>10</td>') && html.includes('<td>4</td>'), 'quantidades na prévia');
    eq(h.context._poCsvParsed.length, 4);
    assert(h.node('req-po-csv-total').textContent.startsWith('Total geral:'), 'total geral');
  });

  testAsync('Cotação: salvar preços envia itens associados com preço/quantidade normalizados', async () => {
    const h = harness();
    await h.preview();
    await h.savePrices();
    eq(h.sent.length, 1);
    eq(h.sent[0].url, '/api/purchase-requests/999/save-prices');
    eq(JSON.stringify(h.sent[0].body.items), JSON.stringify([
      { item_id: 501, unit_price: 1234.56, quantity: 10 },
      { item_id: 502, unit_price: 12.5, quantity: 4 },
      { item_id: 503, unit_price: 89.9, quantity: 2 }
    ]));
  });

  testAsync('Cotação: criar PO envia só itens com EPI e confirma os ignorados', async () => {
    const h = harness();
    await h.preview();
    await h.submitPo();
    eq(h.dialogs.length, 1);
    eq(h.sent.length, 1);
    eq(h.sent[0].url, '/api/purchase-orders');
    eq(JSON.stringify(h.sent[0].body.items.map((i) => [i.purchase_request_item_id, i.epi_id, i.quantity, i.unit_price])),
      JSON.stringify([[501, 11, 10, 1234.56], [502, 12, 4, 12.5], [503, 13, 2, 89.9]]));
  });

  testAsync('Cotação: sem detalhe da requisição, falha explícita e nada é enviado', async () => {
    const h = harness({ detail: null });
    await h.preview();
    await h.savePrices();
    eq(h.sent.length, 0);
    assert(h.feedback().includes('Detalhe da requisição indisponível'), h.feedback());
    await h.submitPo();
    eq(h.sent.length, 0);
    assert(h.feedback().includes('Detalhe da requisição indisponível'), h.feedback());
  });

  testAsync('Cotação: detalhe de OUTRA requisição não é usado para associar itens', async () => {
    const h = harness({ detail: { ...DETAIL, item: { ...PR, id: 1000 } } });
    await h.preview();
    await h.savePrices();
    eq(h.sent.length, 0);
    assert(h.feedback().includes('Detalhe da requisição indisponível'), h.feedback());
  });

  testAsync('Cotação: regras de negócio ausentes não viram R$ 0,00 silencioso', async () => {
    const h = harness({ withBusiness: false });
    await h.preview();
    assert(h.feedback().includes('Importação de cotação indisponível (_parsePurchaseQuantity'), h.feedback());
    eq(h.node('req-po-csv-preview-tbody').innerHTML, '');
    eq(h.context._poCsvParsed.length, 0);
    h.context._poCsvParsed = PARSED;
    await h.savePrices();
    eq(h.sent.length, 0);
    assert(h.feedback().includes('Importação de cotação indisponível'), h.feedback());
  });

  testAsync('Cotação: parser ausente vira erro, não "nenhuma linha válida"', async () => {
    const h = harness({ withParser: false });
    await h.preview();
    assert(h.feedback().includes('Importação de cotação indisponível (_parsePoImportFile'), h.feedback());
  });
};
