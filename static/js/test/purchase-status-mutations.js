'use strict';
// Mutações em memória nos módulos de Compras P1: a fixture e os arquivos servidos ficam intactos.
const assert = require('assert');
const runtime = require('./purchase-status-runtime');
// Mutante equivalente conhecido (não listado): String(status ?? '') no lugar de String(status || '')
// só difere para 0/false/NaN, que viram '0'/'false'/'NaN' — nenhum deles é status de cotação.
const mutations = [
  ['view', 'rótulo trocado', "'Recebida Parcialmente'", "'Recebida Parcial'"],
  ['view', 'chave de tradução trocada', "tr('purchase.poStatus.closed',", "tr('purchase.poStatus.checked',"],
  ['view', 'getter vira valor', "get draft() { return (tr('purchase.poStatus.draft', 'Rascunho', {})); }", "draft: 'Rascunho'"],
  ['view', 'rótulo de item removido', "get waiting_quote() { return (tr('ui.app.aguardando_cotacao_c58378', 'Aguardando Cotação', {})); }, ", ''],
  ['view', 'ordem das etapas', "{ get label() { return (tr('ui.app.conferido_113f18', 'Conferido', {})); } },\n    { get label() { return (tr('portal.periodClosed', 'Fechado', {})); } }", "{ get label() { return (tr('portal.periodClosed', 'Fechado', {})); } },\n    { get label() { return (tr('ui.app.conferido_113f18', 'Conferido', {})); } }"],
  ['view', 'etapa de recebimento', 'received_partial: 1, received: 1,', 'received_partial: 0, received: 1,'],
  ['view', 'conferido', 'checked: 2,', 'checked: 1,'],
  ['view', 'reprovado deixa de ser terminal', "if (status === 'rejected') { return ''; }", "if (status === 'cancelled') { return ''; }"],
  ['view', 'hasOwnProperty trocado por in', 'Object.prototype.hasOwnProperty.call(PO_STEP_INDEX, status)', '(status in PO_STEP_INDEX)'],
  ['view', 'índice padrão', 'PO_STEP_INDEX[status] : 0;', 'PO_STEP_INDEX[status] : -1;'],
  ['view', 'cor de recebida parcial', "received_partial: 'orange'", "received_partial: 'green'"],
  ['view', 'cor de cancelada', "cancelled: 'red'", "cancelled: 'gray'"],
  ['view', 'cor padrão', "colors[status] || 'gray'", "colors[status] || 'orange'"],
  ['view', 'fallback do rótulo', '(PURCHASE_STATUS_LABELS[status] || status)', "(PURCHASE_STATUS_LABELS[status] || '')"],
  ['view', 'separador do extra', "` — ${extra}`", "` - ${extra}`"],
  ['view', 'extra falsy', "(extra ? ` — ${extra}` : '')", "(extra != null ? ` — ${extra}` : '')"],
  ['view', 'fundo verde', "c === 'green' ? 'success-bg'", "c === 'green' ? 'success'"],
  ['view', 'texto vermelho', "c === 'red' ? 'danger' :", "c === 'red' ? 'danger-bg' :"],
  ['rules', 'status removido', "'buyer_resubmitted', ", ''],
  ['rules', 'prorrogada incluída/removida', ", 'postponed']", ']'],
  ['rules', 'coerção para string', "String(status || '')", 'status'],
];

let detected = 0;
for (const [file, label, from, to] of mutations) {
  let divergence = false;
  try { runtime.compareAll([file, from, to]); } catch (error) {
    if (error.message.startsWith('mutação sem alvo:')) { throw error; }
    assert(error instanceof assert.AssertionError, label + ': erro do harness: ' + error.message);
    divergence = true;
  }
  console.log(`${divergence ? 'detectada ' : 'SOBREVIVEU'}  ${label}`);
  if (divergence) { detected++; }
}
console.log('UBX Compras P1: ' + detected + '/' + mutations.length + ' mutações detectadas');
process.exitCode = detected === mutations.length ? 0 : 1;
