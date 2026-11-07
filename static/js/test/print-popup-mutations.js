'use strict';
// Mutações em memória: a fixture original e os arquivos servidos ficam intactos.
const assert = require('assert');
const runtime = require('./print-popup-runtime');
const mutations = [
  ['features padrão', "features = 'width=1100,height=800'", "features = 'width=520,height=700'"],
  ['alvo da janela', "'_blank'", "'_self'"],
  ['opções descartadas', "open('', '_blank', features)", "open('', '_blank')"],
  ['bloqueio: retorno', 'if (!popup) { return null; }', 'if (!popup) { return undefined; }'],
  ['coerção de zero/false', "String(html || '')", "String(html ?? '')"],
  ['trim removido', "String(html || '').trim()", "String(html || '')"],
  ['vazio: retorno', 'if (!markup) { return popup; }', 'if (!markup) { return null; }'],
  ['document.open removido', 'popup.document.open();', ''],
  ['HTML descartado', 'popup.document.write(markup);', "popup.document.write('');"],
  ['document.close antes de write', 'popup.document.write(markup);\n    popup.document.close();', 'popup.document.close();\n    popup.document.write(markup);'],
  ['focus removido', 'popup.focus();', ''],
  ['print removido', 'popup.print();', ''],
  ['print antes de focus', 'popup.focus();\n        popup.print();', 'popup.print();\n        popup.focus();'],
  ['erro deixa de ser contido', "console.warn('[print] Falha ao disparar impressão da popup', error);", 'throw error;'],
  ['diagnóstico alterado', '[print] Falha ao disparar impressão da popup', '[print] outro diagnóstico'],
  ['readyState invertido', "readyState === 'complete'", "readyState !== 'complete'"],
  ['timer de 80ms', 'setTimeout(triggerPrint, 80)', 'setTimeout(triggerPrint, 0)'],
  ['evento errado', "safeOn(popup, 'load'", "safeOn(popup, 'DOMContentLoaded'"],
  ['load repetido', '{ once: true }', '{ once: false }'],
  ['fallback de 500ms', 'setTimeout(triggerPrint, 500)', 'setTimeout(triggerPrint, 800)'],
  ['fallback removido', 'setTimeout(triggerPrint, 500);', ''],
  ['retorno final', '\n    return popup;\n', '\n    return null;\n']
];

let detected = 0;
for (const [label, from, to] of mutations) {
  let divergence = false;
  try { runtime.compareAll([from, to]); } catch (error) {
    // Um alvo incorreto não conta como mutação detectada.
    if (error.message.startsWith('mutação sem alvo:')) { throw error; }
    assert(error instanceof assert.AssertionError, label + ': erro do harness');
    divergence = true;
  }
  assert(divergence, 'mutação sobrevivente: ' + label);
  detected++;
}
console.log('UBX impressão: ' + detected + '/' + mutations.length + ' mutações detectadas');
