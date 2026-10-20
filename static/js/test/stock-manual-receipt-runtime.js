'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const source = fs.readFileSync(path.resolve(__dirname, '../../app.js'), 'utf8');
function functionSource(name) {
  const match = new RegExp('^(?:async )?function ' + name + '\\(', 'm').exec(source);
  if (!match) throw new Error('Função ausente: ' + name);
  const end = source.slice(match.index + match[0].length).search(/^}/m);
  return source.slice(match.index, match.index + match[0].length + end + 1);
}

function harness() {
  let permission = true;
  const nodes = new Map();
  const node = (id) => {
    if (!nodes.has(id)) nodes.set(id, { value: '', disabled: false, required: false, style: {} });
    return nodes.get(id);
  };
  const sent = [], alerts = [];
  node('stock-company').value = '2';
  node('stock-unit').value = '5';
  node('stock-epi').value = '1';
  node('stock-receipt-file').files = [{ name: 'etiqueta.png', type: 'image/png', size: 68 }];
  const context = {
    FileReader: class { readAsDataURL() { this.result = 'data:image/png;base64,iVBORw0KGgo='; this.onload(); } },
    document: { getElementById: node },
    state: { user: { id: 10, company_id: 2, operational_unit_id: 5 },
      epis: [{ id: 1, epi_validity_date: '2099-12-31', ca_expiry: '2099-12-31' }] },
    hasPermission: () => permission, requirePermission: () => true,
    tr: (_key, fallback) => fallback, alert: (message) => alerts.push(message),
    formValues: (form) => ({ ...form.values }),
    resolveItemSize: () => ({ selectedSize: 'M', glove_size: 'N/A', size: 'M', uniform_size: 'N/A' }),
    api: async (url, options) => { sent.push({ url, body: JSON.parse(options.body) }); return {}; },
    setupStockLabelCustomFields() {}, resetStockManufactureCaptureState() {}, loadBootstrap: async () => {}
  };
  vm.createContext(context);
  vm.runInContext(['readStockEvidenceFile', 'syncManualReceiptValidityFields', 'manualReceiptValidityValues', 'handleStockMovementSubmit']
    .map(functionSource).join('\n'), context);
  return {
    node, sent, alerts, run: (code) => vm.runInContext(code, context),
    permission: (allowed) => { permission = allowed; },
    submit: async (values) => {
      const target = { values, dataset: {},
        elements: { glove_size: {}, size: {}, uniform_size: {}, quantity: {} },
        reset() {}, querySelector: () => null };
      await context.handleStockMovementSubmit({ target, preventDefault() {} });
    }
  };
}

module.exports = ({ test, testAsync, assert, eq }) => {
  for (const proof of ['label', 'manufacturer_document']) {
    testAsync('Entrada manual: envia lote, data e evidência próprios de ' + proof, async () => {
      const h = harness();
      await h.submit({ manufacture_date: '2020-01-01', lot_code: ' LOTE-A ',
        expiry_source: proof, physical_expiry_date: '2027-04-03', expiry_evidence: ' Prova do lote A ' });
      eq(h.sent.length, 1);
      const body = h.sent[0].body;
      eq(body.lot_code, 'LOTE-A'); eq(body.physical_expiry_date, '2027-04-03');
      eq(body.expiry_evidence, 'Prova do lote A'); eq(body.expiry_source, proof);
      eq(body.physical_validity_unknown, false);
      eq(body.manufacture_date, '2020-01-01'); eq(body.actor_user_id, 10);
    });
  }

  testAsync('Entrada manual: catálogo futuro não preenche a data física ausente', async () => {
    const h = harness();
    await h.submit({ manufacture_date: '2020-01-01', expiry_source: 'label',
      lot_code: 'LOTE-A', expiry_evidence: 'Etiqueta', physical_expiry_date: '' });
    eq(h.sent.length, 0);
    assert(h.alerts[0].includes('validade física'));
  });

  testAsync('Entrada manual: exige escolha explícita entre comprovação e pendência', async () => {
    const h = harness();
    await h.submit({ manufacture_date: '2020-01-01', expiry_source: '' });
    eq(h.sent.length, 0);
    assert(h.alerts[0].includes('comprovação'));
  });

  testAsync('Entrada manual: opção desconhecida descarta dados antigos de comprovação', async () => {
    const h = harness();
    await h.submit({ manufacture_date: '2020-01-01', expiry_source: 'unknown',
      physical_expiry_date: '2027-04-03', expiry_evidence: 'Prova antiga' });
    const body = h.sent[0].body;
    eq(body.physical_validity_unknown, true); eq(body.physical_expiry_date, '');
    eq(body.expiry_evidence, ''); eq(body.expiry_source, '');
  });

  test('Entrada manual: alternância de fonte controla campos e mostra pendência', () => {
    const h = harness();
    h.node('stock-receipt-source').value = 'label';
    h.run('syncManualReceiptValidityFields()');
    eq(h.node('stock-receipt-proof').hidden, false);
    eq(h.node('stock-receipt-lot').required, true);
    eq(h.node('stock-receipt-expiry').required, true);
    h.node('stock-receipt-expiry').value = '2027-04-03';
    h.node('stock-receipt-source').value = 'unknown';
    h.run('syncManualReceiptValidityFields()');
    eq(h.node('stock-receipt-proof').hidden, true);
    eq(h.node('stock-receipt-expiry').value, '');
    eq(h.node('stock-receipt-expiry').disabled, true);
    eq(h.node('stock-receipt-lot').required, false);
    assert(h.node('stock-receipt-validity-hint').textContent.includes('indisponíveis'));
  });

  test('Entrada manual: mudança para perfil sem permissão limpa a comprovação', () => {
    const h = harness();
    h.node('stock-receipt-source').value = 'manufacturer_document';
    h.node('stock-receipt-expiry').value = '2027-04-03';
    h.node('stock-receipt-evidence').value = 'Documento';
    h.permission(false);
    h.run('syncManualReceiptValidityFields()');
    eq(h.node('stock-receipt-source').value, 'unknown');
    eq(h.node('stock-receipt-source').disabled, true);
    eq(h.node('stock-receipt-expiry').value, '');
    eq(h.node('stock-receipt-evidence').value, '');
    h.permission(true);
    h.run('syncManualReceiptValidityFields()');
    eq(h.node('stock-receipt-source').value, '');
    eq(h.node('stock-receipt-source').disabled, false);
  });
};
