'use strict';
// Importação de cotação (Compras): executa o views/purchases.js REAL e o
// módulo de regras REAL num contexto isolado, com DOM mínimo, e verifica o
// que chega ao backend.
//
// Decisão de 2026-10-22 (opção C + bloqueio A): nenhuma linha é associada
// em silêncio; CA divergente bloqueia; CA ausente exige escolha manual;
// fornecedor nunca basta; a sugestão só existe quando é única; antes de
// gravar, um resumo exige confirmação explícita; o payload leva a versão do
// item vista pelo operador (alteração concorrente é rejeitada no backend).
// Também cobre os defeitos anteriores: `_currentPrDetail` invisível e
// fallback silencioso (R$ 0,00) quando as regras não carregam.
const fs = require('fs'), path = require('path'), vm = require('vm');
const JS_ROOT = path.resolve(__dirname, '..');
const read = (rel) => fs.readFileSync(path.join(JS_ROOT, rel), 'utf8');
const appSource = fs.readFileSync(path.resolve(JS_ROOT, '..', 'app.js'), 'utf8');
const BUSINESS_MODULE = 'modules/purchases/business/purchase-import-matching.js';

const STAMP = '2026-10-22T10:00:00+00:00';
const PR = { id: 999, status: 'sent_to_buyer', unit_id: 1 };
const ITEMS = [
  { id: 501, epi_id: 11, epi_name: 'Luva Nitrílica', ca: '12345', manufacturer: 'Danny', glove_size: 'M', quantity_requested: 10, supplier: 'ACME', origin: 'stock_minimum', updated_at: STAMP },
  { id: 502, epi_id: 12, epi_name: 'Óculos de Proteção', ca: '67890', manufacturer: '3M', quantity_requested: 4, supplier: 'ACME', employee_name: 'João Silva', origin: 'employee_request', updated_at: STAMP },
  { id: 503, epi_id: 13, epi_name: 'Bota de Segurança', ca: '', manufacturer: 'Marluvas', size: '42', quantity_requested: 2, supplier: 'ACME', origin: 'stock_minimum', updated_at: STAMP }
];
const DETAIL = { item: PR, items: ITEMS };
// Linha 1: CA e descrição coincidem → sugestão única.
// Linha 2: CA e descrição coincidem → sugestão única (quantidade 3,6 → 4).
// Linha 3: sem CA dos dois lados → escolha manual obrigatória.
// Linha 4: outro produto do mesmo fornecedor (CA divergente) → sem candidato.
const PARSED = [
  { line: 2, epi: 'Luva nitrilica', ca: 'CA 12345', fabricante: 'Danny', tamanho_luva: 'M', qtd: '10', valor_unitario: 'R$ 1.234,56', fornecedor: 'ACME' },
  { line: 3, epi: 'Oculos de protecao', ca: '67890', qtd: '3,6', valor_unitario: '12.5', fornecedor: 'ACME' },
  { line: 4, epi: 'Bota de segurança', ca: '', tamanho: '42', qtd: '', valor_unitario: '89,90', fornecedor: 'ACME' },
  { line: 5, epi: 'Capacete Classe B', ca: '99999', qtd: '1', valor_unitario: '50,00', fornecedor: 'ACME', origem: 'Colaborador' }
].map((row) => ({ ...row, quote_sig: `sig-${row.line}`, quote_issued_at: '2026-10-22T12:00:00+00:00' }));

function harness({ withBusiness = true, withParser = true, detail = DETAIL, parsed = PARSED, apiError = null, skipIds = null } = {}) {
  const nodes = new Map();
  const node = (id) => {
    if (!nodes.has(id)) { nodes.set(id, { id, value: '', checked: false, disabled: false, style: {}, textContent: '', innerHTML: '', files: [{ name: 'cotacao.csv' }] }); }
    return nodes.get(id);
  };
  const sent = [];
  const context = {
    console, Promise, Set, Map, Array, Object, String, Number, JSON, Math, Error,
    document: { getElementById: node, querySelector: () => null, querySelectorAll: () => [] },
    confirm: () => { throw new Error('window.confirm não deve ser usado na importação de cotação'); },
    escapeHtml: (v) => String(v ?? '').replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`),
    __EPI_APP_STATE__: { user: { id: 7 } },
    api: async (url, options) => {
      const body = JSON.parse(options.body);
      sent.push({ url, body });
      if (apiError) { throw new Error(apiError); }
      const skip = new Set((skipIds || []).map(String));
      return { ok: true, affected_item_ids: (body.items || []).map((i) => i.item_id).filter((id) => !skip.has(String(id))) };
    },
    openPrDetail: async () => {}, loadPurchaseRequests: () => {}, loadPurchaseOrders: () => {}
  };
  context.globalThis = context;
  vm.createContext(context);
  if (withParser) { context._parsePoImportFile = async () => parsed.map((r) => ({ ...r })); }
  if (detail) { context._currentPrDetail = detail; }
  if (withBusiness) { vm.runInContext(read(BUSINESS_MODULE), context); }
  vm.runInContext(read('views/purchases.js'), context);
  context.initPoCsvImport(PR);
  const h = {
    context, sent, node,
    preview: () => node('req-po-csv-preview-btn').onclick(),
    choose: (row, value) => context.setQuoteImportDecision(row, value),
    savePrices: () => node('req-po-save-prices-btn').onclick(),
    submitPo: () => { node('req-po-csv-supplier').value = 'ACME'; return node('req-po-csv-submit-btn').onclick(); },
    tick: (checked = true) => { node('req-po-csv-confirm-check').checked = checked; },
    confirm: () => node('req-po-csv-confirm-btn').onclick(),
    back: () => node('req-po-csv-confirm-cancel-btn').onclick(),
    feedback: () => node('req-po-csv-feedback').textContent,
    mapping: () => node('req-po-csv-preview-tbody').innerHTML,
    summary: () => node('req-po-csv-confirm-body').innerHTML,
    confirmVisible: () => node('req-po-csv-confirm').style.display === ''
  };
  return h;
}

// Seleção usual do operador: aceita as sugestões, escolhe a bota e não importa o capacete.
async function previewAndDecide(h) {
  await h.preview();
  h.choose(2, '503');
  h.choose(3, 'ignore');
}

module.exports = ({ test, testAsync, assert, eq }) => {
  test('Cotação: app.js publica _currentPrDetail na ponte de acessores de globalThis', () => {
    const bridge = appSource.slice(appSource.indexOf("['_purchaseDemands'"), appSource.indexOf('].forEach(([name, get, set])'));
    assert(bridge.includes("['_currentPrDetail', () => _currentPrDetail,"), 'ponte sem _currentPrDetail');
  });

  test('Cotação (regras): fornecedor coincidente com item incorreto não gera candidato', () => {
    const h = harness();
    const [row] = h.context.evaluatePurchaseImportCandidates([PARSED[3]], ITEMS);
    eq(row.candidates.length, 0);
    eq(row.suggestedItemId, null);
  });

  test('Cotação (regras): CA divergente bloqueia mesmo com descrição igual', () => {
    const h = harness();
    const [row] = h.context.evaluatePurchaseImportCandidates([{ epi: 'Luva Nitrílica', ca: '99999', fabricante: 'Danny' }], ITEMS);
    eq(row.candidates.length, 1);
    eq(row.candidates[0].itemId, 501);
    eq(row.candidates[0].blocked, true);
    eq(row.candidates[0].eligible, false);
    eq(row.suggestedItemId, null);
    const errors = h.context.validatePurchaseImportDecisions([row], ['501']);
    assert(errors[0].includes('CA divergente'), errors.join(' '));
  });

  test('Cotação (regras): CA ausente nunca gera sugestão automática', () => {
    const h = harness();
    const [row] = h.context.evaluatePurchaseImportCandidates([PARSED[2]], ITEMS);
    eq(row.caMissing, true);
    eq(row.suggestedItemId, null);
    assert(row.candidates.some((c) => c.itemId === 503 && c.eligible), 'bota deve ser candidata manual');
  });

  test('Cotação (regras): CA coincidente sozinho não identifica o produto', () => {
    const h = harness();
    const [row] = h.context.evaluatePurchaseImportCandidates([{ epi: 'Produto genérico', ca: '12345' }], ITEMS);
    eq(row.suggestedItemId, null);
    assert(row.candidates[0].divergences.some((d) => d.includes('descrição diferente')), 'divergência de descrição');
  });

  test('Cotação (regras): CA igual sem descrição ou modelo aparece, mas não é elegível', () => {
    const h = harness();
    const [row] = h.context.evaluatePurchaseImportCandidates([{ epi: '', ca: '12345' }], ITEMS);
    const luva = row.candidates.find((c) => c.itemId === 501);
    assert(luva, 'candidato com CA igual continua visível');
    eq(luva.eligible, false);
    eq(row.suggestedItemId, null);
  });

  test('Cotação (regras): múltiplos candidatos não são escolhidos sozinhos', () => {
    const h = harness();
    const twins = ITEMS.concat([{ ...ITEMS[0], id: 504, glove_size: 'M' }]);
    const [row] = h.context.evaluatePurchaseImportCandidates([PARSED[0]], twins);
    eq(row.suggestedItemId, null);
    eq(row.candidates.filter((c) => c.eligible).length, 2);
    assert(row.notes.some((n) => n.includes('Mais de um item')), row.notes.join(' '));
    const [a, b] = h.context.evaluatePurchaseImportCandidates([PARSED[0], PARSED[0]], ITEMS);
    eq(a.suggestedItemId, null);
    eq(b.suggestedItemId, null);
  });

  testAsync('Cotação: prévia lista candidatos, sugestões marcadas e divergências', async () => {
    const h = harness();
    await h.preview();
    const html = h.mapping();
    assert(html.includes('data-quote-row="0"') && html.includes('data-quote-row="3"'), 'um seletor por linha');
    assert(html.includes('<option value="501" selected>'), 'sugestão única pré-marcada e visível');
    assert(html.includes('— sugerido'), 'sugestão rotulada');
    assert(html.includes('<option value="" selected>— escolha o item —</option>'), 'linhas sem sugestão começam vazias');
    assert(html.includes('CA ausente: escolha e confirme o item manualmente.'), 'aviso de CA ausente');
    assert(html.includes('Nenhum item da requisição corresponde a esta linha.'), 'linha sem candidato');
    assert(!h.confirmVisible(), 'resumo só aparece ao pedir para salvar');
    eq(h.sent.length, 0);
  });

  testAsync('Cotação: linha pendente impede seguir; nada é enviado', async () => {
    const h = harness();
    await h.preview();
    await h.savePrices();
    eq(h.sent.length, 0);
    assert(!h.confirmVisible(), 'sem resumo com linha pendente');
    assert(h.feedback().includes('Linha 3: escolha o item'), h.feedback());
  });

  testAsync('Cotação: salvar exige resumo + conferência marcada e envia só itens confirmados', async () => {
    const h = harness();
    await previewAndDecide(h);
    await h.savePrices();
    assert(h.confirmVisible(), 'resumo visível');
    const summary = h.summary();
    assert(summary.includes('#501') && summary.includes('#502') && summary.includes('#503'), 'resumo com as associações');
    assert(summary.includes('Linhas não importadas: 1'), 'linha ignorada informada');
    assert(summary.includes('<td>10</td>') && summary.includes('<td>4</td>') && summary.includes('<td>2</td>'), 'quantidades no resumo');
    eq(h.sent.length, 0);
    await h.confirm();
    eq(h.sent.length, 0);
    assert(h.feedback().includes('Marque a conferência'), h.feedback());
    h.tick();
    await h.confirm();
    eq(h.sent.length, 1);
    eq(h.sent[0].url, '/api/purchase-requests/999/save-prices');
    eq(JSON.stringify(h.sent[0].body.items.map((i) => [i.item_id, i.unit_price, i.quantity, i.confirmed, i.expected_updated_at])),
      JSON.stringify([[501, 1234.56, 10, true, STAMP], [502, 12.5, 4, true, STAMP], [503, 89.9, 2, true, STAMP]]));
    eq(h.sent[0].body.items[2].quote_ca, '');
    eq(h.sent[0].body.items[0].quote_line, 2);
    // campos do parse vão intactos, com a assinatura do servidor
    const first = h.sent[0].body.items[0];
    eq(JSON.stringify([first.quote_sig, first.quote_issued_at, first.quote_qty, first.quote_unit_price, first.quote_glove_size]),
      JSON.stringify(['sig-2', '2026-10-22T12:00:00+00:00', '10', 'R$ 1.234,56', 'M']));
    assert(h.feedback().includes('3 item(s) confirmados'), h.feedback());
  });

  testAsync('Cotação: cancelar no resumo não grava nada', async () => {
    const h = harness();
    await previewAndDecide(h);
    await h.savePrices();
    h.tick();
    h.back();
    assert(!h.confirmVisible(), 'resumo fechado');
    await h.confirm();
    eq(h.sent.length, 0);
    assert(h.feedback().includes('Nada a confirmar'), h.feedback());
  });

  testAsync('Cotação: mudar uma escolha invalida o resumo pendente', async () => {
    const h = harness();
    await previewAndDecide(h);
    await h.savePrices();
    h.tick();
    h.choose(0, 'ignore');
    await h.confirm();
    eq(h.sent.length, 0);
  });

  testAsync('Cotação: item bloqueado ou repetido não pode ser escolhido', async () => {
    const h = harness();
    await previewAndDecide(h);
    h.choose(3, '501');
    await h.savePrices();
    assert(h.feedback().includes('Linha 4: o item escolhido não é candidato'), h.feedback());
    eq(h.sent.length, 0);
  });

  test('Cotação (regras): o mesmo item não recebe duas linhas', () => {
    const h = harness();
    const rows = h.context.evaluatePurchaseImportCandidates([PARSED[0], { ...PARSED[0], line: 9 }], ITEMS);
    const errors = h.context.validatePurchaseImportDecisions(rows, ['501', '501']);
    assert(errors.some((e) => e.includes('o item #501 já foi escolhido na linha 1')), errors.join(' '));
  });

  testAsync('Cotação: criar PO envia só associações confirmadas, com source=quote_import', async () => {
    const h = harness();
    await previewAndDecide(h);
    await h.submitPo();
    h.tick();
    await h.confirm();
    eq(h.sent.length, 1);
    eq(h.sent[0].url, '/api/purchase-orders');
    eq(h.sent[0].body.source, 'quote_import');
    eq(JSON.stringify(h.sent[0].body.items.map((i) => [i.purchase_request_item_id, i.epi_id, i.quantity, i.unit_price, i.confirmed])),
      JSON.stringify([[501, 11, 10, 1234.56, true], [502, 12, 4, 12.5, true], [503, 13, 2, 89.9, true]]));
  });

  testAsync('Cotação: alteração concorrente rejeitada pelo backend aparece ao operador', async () => {
    const h = harness({ apiError: 'Linha 2 da cotação: o item #501 foi alterado por outra operação depois da conferência.' });
    await previewAndDecide(h);
    await h.savePrices();
    h.tick();
    await h.confirm();
    eq(h.sent.length, 1);
    assert(h.feedback().includes('alterado por outra operação'), h.feedback());
    eq(h.node('req-po-csv-confirm-btn').disabled, false);
  });

  testAsync('Cotação: detalhe trocado entre a prévia e a confirmação bloqueia o envio', async () => {
    const h = harness();
    await previewAndDecide(h);
    await h.savePrices();
    h.tick();
    h.context._currentPrDetail = { ...DETAIL, item: { ...PR, id: 1000 } };
    await h.confirm();
    eq(h.sent.length, 0);
    assert(h.feedback().includes('Detalhe da requisição indisponível'), h.feedback());
  });

  testAsync('Cotação: sem detalhe da requisição, falha explícita e nada é enviado', async () => {
    const h = harness({ detail: null });
    await h.preview();
    assert(h.feedback().includes('Detalhe da requisição indisponível'), h.feedback());
    await h.savePrices();
    eq(h.sent.length, 0);
  });

  testAsync('Cotação: regras de negócio ausentes não viram R$ 0,00 silencioso', async () => {
    const h = harness({ withBusiness: false });
    await h.preview();
    assert(h.feedback().includes('Importação de cotação indisponível (evaluatePurchaseImportCandidates'), h.feedback());
    eq(h.mapping(), '');
    eq(h.context._poCsvParsed.length, 0);
    await h.savePrices();
    eq(h.sent.length, 0);
  });

  testAsync('Cotação: parser ausente vira erro, não "nenhuma linha válida"', async () => {
    const h = harness({ withParser: false });
    await h.preview();
    assert(h.feedback().includes('Importação de cotação indisponível (_parsePoImportFile'), h.feedback());
  });

  testAsync('Cotação: valores do arquivo são escapados na prévia', async () => {
    const h = harness({ parsed: [{ epi: '<img src=x onerror=alert(1)>', ca: '12345', qtd: '1', valor_unitario: '1' }] });
    await h.preview();
    assert(!h.mapping().includes('<img'), 'HTML do arquivo não pode ser injetado');
  });

  test('Cotação (regras): CA sem dígitos conta como ausente', () => {
    const h = harness();
    for (const placeholder of ['N/A', 'ISENTO', '-']) {
      const [row] = h.context.evaluatePurchaseImportCandidates([{ ...PARSED[0], ca: placeholder }], ITEMS);
      eq(row.caMissing, true);
      eq(row.suggestedItemId, null);
      assert(!row.candidates.some((c) => c.blocked), `${placeholder} não pode bloquear como CA divergente`);
    }
  });

  test('Cotação (regras): CA do cadastro atual prevalece sobre o do item', () => {
    const h = harness();
    const renewed = [{ ...ITEMS[0], epi_ca: '55555' }];
    const [row] = h.context.evaluatePurchaseImportCandidates([PARSED[0]], renewed);
    eq(row.candidates[0].blocked, true);
  });

  test('Cotação (regras): descrição parcial sem CA não identifica o produto', () => {
    const h = harness();
    const [row] = h.context.evaluatePurchaseImportCandidates([{ epi: 'Luva', ca: '', qtd: '1', valor_unitario: '1' }], ITEMS);
    const luva = row.candidates.find((c) => c.itemId === 501);
    assert(luva, 'luva aparece como candidata parecida');
    eq(luva.eligible, false);
    assert(h.context.validatePurchaseImportDecisions([row], ['501'])[0].includes('identificação inequívoca'), 'escolha recusada');
  });

  test('Cotação (regras): fabricante ou tamanho divergente torna o item inelegível', () => {
    const h = harness();
    const [byMaker] = h.context.evaluatePurchaseImportCandidates([{ epi: 'Luva Nitrílica', ca: '', fabricante: 'Vonder' }], ITEMS);
    eq(byMaker.candidates.find((c) => c.itemId === 501).eligible, false);
    const [bySize] = h.context.evaluatePurchaseImportCandidates([{ ...PARSED[0], tamanho_luva: 'G' }], ITEMS);
    const luva = bySize.candidates.find((c) => c.itemId === 501);
    eq(luva.eligible, false);
    assert(h.context.validatePurchaseImportDecisions([bySize], ['501'])[0].includes('contradiz o item #501'), 'escolha recusada');
  });

  test('Cotação (regras): CA igual com descrição contraditória não é elegível', () => {
    const h = harness();
    const [row] = h.context.evaluatePurchaseImportCandidates([{ epi: 'Capacete classe B', ca: '12345', fabricante: 'MSA' }], ITEMS);
    const luva = row.candidates.find((c) => c.itemId === 501);
    eq(luva.eligible, false);
    eq(row.suggestedItemId, null);
  });

  testAsync('Cotação: item confirmado mas já aprovado é informado ao operador', async () => {
    const h = harness({ skipIds: [502] });
    await previewAndDecide(h);
    await h.savePrices();
    h.tick();
    await h.confirm();
    assert(h.feedback().includes('Preços salvos em 2 item(s)'), h.feedback());
    assert(h.feedback().includes('Não alterados (já aprovados): #502'), h.feedback());
  });
};
