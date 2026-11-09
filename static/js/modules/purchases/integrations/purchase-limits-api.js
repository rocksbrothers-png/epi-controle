'use strict';

// Integração: Compras CO-1 — limite de alçada de PO.
//
// Pelo cliente único (globalThis.api), resolvido na CHAMADA. Caminho e método
// literais (tests/test_frontend_api_contract.py confronta com o router). A
// empresa vem da sessão no backend, nunca daqui. Sem DOM.
(function () {
  if (globalThis.__EPI_MODULE_PURCHASE_LIMITS_INTEGRATIONS_LOADED__) { return; }
  globalThis.__EPI_MODULE_PURCHASE_LIMITS_INTEGRATIONS_LOADED__ = true;

  function getPurchaseLimits(actorQueryString) {
    return globalThis.api(`/api/purchase-limits?${actorQueryString}`);
  }

  // payload: { actor_user_id, value: "1500.00" | null, expected_version }
  function savePurchaseLimit(payload) {
    return globalThis.api('/api/purchase-limits', { method: 'POST', body: JSON.stringify(payload) });
  }

  globalThis.__EPI_PURCHASE_LIMITS_API__ = Object.freeze({ getPurchaseLimits, savePurchaseLimit });
})();
