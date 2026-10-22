'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const source = fs.readFileSync(path.resolve(__dirname, '../views/stock-physical.js'), 'utf8');

function harness() {
  const nodes = new Map();
  const node = (key) => {
    if (!nodes.has(key)) {nodes.set(key, { style: {}, listeners: {}, disabled: false,
      addEventListener(event, callback) { this.listeners[event] = callback; },
      querySelector: node, remove() { this.removed = true; }, reportValidity: () => true });}
    return nodes.get(key);
  };
  const values = { action: 'donation', recipient: 'Unidade sugere destinatário', recipient_reference: 'Contato',
    shipment_reference: 'Guia-123', justification: 'Conferência', manufacture_date: '2025-01-21', size: '58', evidence: 'Etiqueta', confirmed: 'on' };
  const sent = [];
  let scope = { companyId: '2', unitId: '5' }, refreshed = 0;
  const context = { document: { getElementById: () => null, createElement: () => node('overlay'), body: { appendChild() {} } },
    FormData: class { [Symbol.iterator]() { return Object.entries(values)[Symbol.iterator](); } } };
  vm.createContext(context); vm.runInContext(source, context);
  const options = { item: { id: 89, unit_id: 5, qr_code_value: 'QR-89', epi_name: '<Capacete>', unit_name: 'Unidade', lot_code: 'REAL', size: 'N/A' },
    context: { ...scope }, currentContext: () => scope, kind: 'disposition',
    api: async (url, request) => { sent.push({ url, body: JSON.parse(request.body) }); }, refresh: async () => { refreshed += 1; } };
  return { node, values, sent, options, refreshed: () => refreshed, scope: (v) => { scope = v; },
    open: () => context.__EPI_STOCK_PHYSICAL__.dialog(options), submit: () => node('form').listeners.submit({ preventDefault() {} }) };
}

module.exports = ({ testAsync, assert, eq }) => {
  testAsync('Destinação: cancelar mantém o estoque e escapa a identificação da peça', async () => {
    const h = harness(); h.open();
    assert(h.node('overlay').innerHTML.includes('&lt;Capacete&gt;'));
    h.node('#stock-physical-cancel').listeners.click();
    eq(h.sent.length, 0); assert(h.node('overlay').removed);
  });
  testAsync('Destinação: confirmação envia destinatário da unidade e impede duplo clique', async () => {
    const h = harness(); let finish;
    h.options.api = async (url, request) => { h.sent.push({ url, body: JSON.parse(request.body) }); await new Promise((resolve) => { finish = resolve; }); };
    h.open(); const first = h.submit(); await h.submit();
    eq(h.sent.length, 1); eq(h.sent[0].body.stock_item_id, 89); eq(h.sent[0].body.unit_id, 5);
    eq(h.sent[0].body.recipient, h.values.recipient); eq(h.sent[0].body.shipment_confirmed, true);
    assert(h.node('[type="submit"]').disabled);
    finish(); await first; eq(h.refreshed(), 1); assert(h.node('overlay').removed);
  });
  testAsync('Conferência: troca de contexto recusa envio de formulário antigo', async () => {
    const h = harness(); h.open(); h.scope({ companyId: '3', unitId: '6' }); await h.submit();
    eq(h.sent.length, 0); assert(h.node('#stock-physical-error').textContent.includes('mudou'));
  });
  testAsync('Conferência: tamanho e fabricação seguem pelo QR sem mudar validade', async () => {
    const h = harness(); h.options.kind = 'metadata'; h.open(); await h.submit();
    eq(h.sent[0].url, '/api/stock/items/physical-metadata');
    eq(h.sent[0].body.size, '58'); eq(h.sent[0].body.manufacture_date, '2025-01-21');
    eq(h.sent[0].body.qr_code, 'QR-89'); eq(h.sent[0].body.physical_confirmed, true);
    assert(!Object.hasOwn(h.sent[0].body, 'physical_expiry_date'));
  });
  testAsync('Destinação: falha HTTP mantém dados e permite tentar novamente', async () => {
    const h = harness(); h.options.api = async () => { throw new Error('HTTP 503'); }; h.open(); await h.submit();
    eq(h.node('#stock-physical-error').textContent, 'HTTP 503');
    assert(!h.node('overlay').removed); assert(!h.node('[type="submit"]').disabled);
  });
};
