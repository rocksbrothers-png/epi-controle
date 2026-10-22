'use strict';

// Módulo de negócio: Compras — conciliação da importação de cotação/PO
// (Refatoração UBX — camada Business, extraída de static/app.js).
//
// Regras puras usadas ao importar o arquivo de cotação devolvido pelo
// fornecedor: normalizar valores monetários/quantidades em formato BR ou US e
// casar cada linha importada com o item da requisição de compra (por
// `item_id` exato ou, na falta dele, pela melhor pontuação de CA, EPI,
// colaborador, unidade, fornecedor, origem e tamanhos).
//
// Sem DOM, sem HTTP, sem estado global: toda entrada vem por parâmetro.
// Consumidor: static/js/views/purchases.js (via globalThis, contrato legado).
// O comportamento é idêntico ao das funções originais do app.js — qualquer
// mudança de regra é mudança de negócio, não de estrutura.
(function () {
  if (globalThis.__EPI_MODULE_PURCHASE_IMPORT_MATCHING_LOADED__) { return; }
  globalThis.__EPI_MODULE_PURCHASE_IMPORT_MATCHING_LOADED__ = true;

  function _normalizeCa(ca) {
    return String(ca || '').trim().replace(/[-\s]+$/, '').replace(/^[-\s]+/, '').toLowerCase();
  }

  function _parsePurchaseMoney(value) {
    if (typeof value === 'number' && Number.isFinite(value)) {
      return Math.round(value * 100) / 100;
    }
    let text = String(value ?? '').trim();
    if (!text) { return 0; }
    text = text.replace(/\u00a0/g, ' ')
      .replace(/r\$/gi, '')
      .replace(/\s+/g, '')
      .replace(/[^0-9,.-]/g, '');
    if (!text || ['-', ',', '.', '-,', '-.'].includes(text)) { return 0; }
    const negative = text.startsWith('-');
    text = text.replace(/-/g, '');
    const commaIndex = text.lastIndexOf(',');
    const dotIndex = text.lastIndexOf('.');
    let normalized = '';
    if (commaIndex >= 0 || dotIndex >= 0) {
      const decimalSep = commaIndex > dotIndex ? ',' : '.';
      const parts = text.split(decimalSep);
      const fractional = parts.pop() || '0';
      const integer = parts.join('').replace(/[,.]/g, '') || '0';
      normalized = `${negative ? '-' : ''}${integer}.${fractional}`;
    } else {
      normalized = `${negative ? '-' : ''}${text.replace(/[,.]/g, '')}`;
    }
    const parsed = Number(normalized);
    return Number.isFinite(parsed) ? Math.round(parsed * 100) / 100 : 0;
  }

  function _parsePurchaseQuantity(value, fallback = 1) {
    const parsed = Number(String(value ?? '').replace(/\u00a0/g, '').replace(',', '.').replace(/[^0-9.-]/g, ''));
    const quantity = Math.round(parsed);
    return Number.isFinite(quantity) && quantity > 0 ? quantity : fallback;
  }

  function _normalizePurchaseText(value) {
    return String(value || '').trim().toLowerCase()
      .normalize('NFD').replace(/[̀-ͯ]/g, '')
      .replace(/\s+/g, ' ');
  }

  function _normalizePurchaseSize(value) {
    const text = _normalizePurchaseText(value);
    return (!text || text === 'n/a' || text === 'na') ? '' : text;
  }

  function _normalizePurchaseOrigin(value) {
    const text = _normalizePurchaseText(value);
    if (text.includes('colaborador') || text.includes('employee')) { return 'employee_request'; }
    if (text.includes('estoque') || text.includes('stock')) { return 'stock_minimum'; }
    return text;
  }

  function _scorePurchaseImportMatch(row, item) {
    let score = 0;
    const rowCa = _normalizeCa(row.ca);
    const rowEpi = _normalizePurchaseText(row.epi);
    const rowEmployee = _normalizePurchaseText(row.colaborador);
    const rowUnit = _normalizePurchaseText(row.unidade);
    const rowSupplier = _normalizePurchaseText(row.fornecedor);
    const rowOrigin = _normalizePurchaseOrigin(row.origem);
    const rowSize = _normalizePurchaseSize(row.tamanho);
    const rowGlove = _normalizePurchaseSize(row.tamanho_luva);
    const rowUniform = _normalizePurchaseSize(row.tamanho_uniforme);
    if (rowCa && _normalizeCa(item.ca || item.epi_ca) === rowCa) { score += 4; }
    if (rowEpi && _normalizePurchaseText(item.epi_name || item.epi_display_name) === rowEpi) { score += 3; }
    if (rowEmployee && _normalizePurchaseText(item.employee_name) === rowEmployee) { score += 3; }
    if (rowUnit && _normalizePurchaseText(item.unit_name) === rowUnit) { score += 2; }
    if (rowSupplier && _normalizePurchaseText(item.supplier) === rowSupplier) { score += 1; }
    if (rowOrigin && _normalizePurchaseOrigin(item.origin) === rowOrigin) { score += 1; }
    if (rowSize && _normalizePurchaseSize(item.size) === rowSize) { score += 2; }
    if (rowGlove && _normalizePurchaseSize(item.glove_size) === rowGlove) { score += 2; }
    if (rowUniform && _normalizePurchaseSize(item.uniform_size) === rowUniform) { score += 2; }
    return score;
  }

  function _matchPurchaseImportRows(rows, prItems) {
    const used = new Set();
    return rows.map((row) => {
      const itemId = String(row.item_id || '').trim();
      if (itemId) {
        const exactIndex = prItems.findIndex((item, idx) => !used.has(idx) && String(item.id || item.purchase_request_item_id || '') === itemId);
        if (exactIndex >= 0) {
          used.add(exactIndex);
          return prItems[exactIndex];
        }
      }
      let bestIndex = -1;
      let bestScore = 0;
      prItems.forEach((item, idx) => {
        if (used.has(idx)) { return; }
        const score = _scorePurchaseImportMatch(row, item);
        if (score > bestScore) {
          bestScore = score;
          bestIndex = idx;
        }
      });
      if (bestIndex >= 0 && bestScore > 0) {
        used.add(bestIndex);
        return prItems[bestIndex];
      }
      return null;
    });
  }

  // ── Exports ───────────────────────────────────────────────────────────────
  // Os nomes globais são o contrato legado consumido por views/purchases.js
  // (`globalThis._matchPurchaseImportRows?.(...)` etc.) e antes vinham das
  // declarações de bloco do app.js. Atribuição direta (não condicional): este
  // módulo é a única definição.

  const purchaseImportExports = {
    _normalizeCa,
    _parsePurchaseMoney,
    _parsePurchaseQuantity,
    _normalizePurchaseText,
    _normalizePurchaseSize,
    _normalizePurchaseOrigin,
    _scorePurchaseImportMatch,
    _matchPurchaseImportRows
  };

  for (const [name, fn] of Object.entries(purchaseImportExports)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_PURCHASES_BUSINESS__ = Object.freeze({ ...purchaseImportExports });
})();
