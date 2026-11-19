'use strict';

// UBX Compras P1 — regra pura: status em que a cotação está com o comprador.
// Corpo idêntico ao do app.js; a global legada isBuyerQuotationStatus é preservada.
// A decisão de permissão continua com o app (hasPermission) e o backend.
(function () {
  if (globalThis.__EPI_MODULE_PURCHASE_STATUS_RULES_LOADED__) { return; }
  globalThis.__EPI_MODULE_PURCHASE_STATUS_RULES_LOADED__ = true;

  const PURCHASE_BUYER_QUOTE_STATUSES = ['sent_to_buyer', 'returned_to_buyer', 'quoted', 'waiting_buyer_correction', 'buyer_resubmitted', 'pending_approval', 'postponed'];

  function isBuyerQuotationStatus(status) {
    return PURCHASE_BUYER_QUOTE_STATUSES.includes(String(status || ''));
  }

  globalThis.isBuyerQuotationStatus = isBuyerQuotationStatus;
  globalThis.__EPI_PURCHASE_STATUS_RULES__ = Object.freeze({ PURCHASE_BUYER_QUOTE_STATUSES, isBuyerQuotationStatus });
})();
