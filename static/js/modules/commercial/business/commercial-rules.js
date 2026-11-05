'use strict';

// Regra comercial pura (UBX Comercial, fatia C1 — extraída de static/app.js).
//
// commercialAlertTone decide o tom do alerta comercial só a partir do item
// recebido: sem DOM, HTTP, armazenamento ou estado do app. Corpo idêntico ao
// do app.js. No app.js era declaração de função dentro do bloco de carga
// (Annex B: virava global); aqui é publicada em globalThis com o mesmo nome e
// em __EPI_COMMERCIAL_RULES__ (congelado). Carga idempotente.
(function () {
  if (globalThis.__EPI_MODULE_COMMERCIAL_RULES_LOADED__) { return; }
  globalThis.__EPI_MODULE_COMMERCIAL_RULES_LOADED__ = true;

  function commercialAlertTone(item) {
    return Number(item.limit_reached) === 1 || item.license_status === 'expired' ? 'danger' : 'warning';
  }

  const commercialRulesExports = {
    commercialAlertTone
  };

  for (const [name, fn] of Object.entries(commercialRulesExports)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_COMMERCIAL_RULES__ = Object.freeze({ ...commercialRulesExports });
})();
