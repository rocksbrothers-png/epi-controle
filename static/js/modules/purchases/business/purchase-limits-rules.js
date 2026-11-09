'use strict';

// Compras CO-1 — regras puras do limite de alçada (camada business).
//
// Dinheiro é tratado como TEXTO decimal (sem Number/float): a entrada do usuário
// vira a forma canônica "NNNN.DD" enviada ao backend, que é quem valida de fato
// (modules/purchases/approval_limits.py). Sem DOM, HTTP, storage ou globais.
(function () {
  if (globalThis.__EPI_MODULE_PURCHASE_LIMITS_RULES_LOADED__) { return; }
  globalThis.__EPI_MODULE_PURCHASE_LIMITS_RULES_LOADED__ = true;

  // Mesmo teto do backend: 999.999.999.999,99 (12 dígitos inteiros).
  const MAX_INTEGER_DIGITS = 12;

  // Entrada do usuário → { ok, value: "1500.50" } ou { ok: false, code }.
  // Aceita um único separador decimal ("." ou ","), sem separador de milhar —
  // "1.500,00" é ambíguo e é recusado em vez de adivinhado.
  function normalizeLimitInput(raw) {
    const text = String(raw === null || raw === undefined ? '' : raw).replace(/\s+/g, '');
    if (!text) { return { ok: false, code: 'EMPTY' }; }
    const match = /^(\d+)(?:[.,](\d{1,2}))?$/.exec(text);
    if (!match) { return { ok: false, code: 'INVALID' }; }
    const integer = match[1].replace(/^0+(?=\d)/, '');
    const fraction = (match[2] || '').padEnd(2, '0');
    if (integer.length > MAX_INTEGER_DIGITS) { return { ok: false, code: 'TOO_LARGE' }; }
    if (/^0+$/.test(integer) && /^0+$/.test(fraction)) { return { ok: false, code: 'INVALID' }; }
    return { ok: true, value: `${integer}.${fraction}` };
  }

  // "1234567.50" → texto com separadores do idioma (recebidos por parâmetro).
  function formatLimit(canonical, separators) {
    const match = /^(\d+)\.(\d{2})$/.exec(String(canonical || ''));
    if (!match) { return ''; }
    const sep = separators || {};
    const group = typeof sep.group === 'string' ? sep.group : '.';
    const decimal = typeof sep.decimal === 'string' ? sep.decimal : ',';
    const grouped = match[1].replace(/\B(?=(\d{3})+(?!\d))/g, group);
    return `${grouped}${decimal}${match[2]}`;
  }

  // Estado de apresentação a partir do que o backend devolveu.
  function describeLimits(data) {
    const source = data || {};
    const configured = typeof source.po_approval_threshold === 'string' && /^\d+\.\d{2}$/.test(source.po_approval_threshold);
    return {
      configured,
      value: configured ? source.po_approval_threshold : null,
      currency: source.currency || 'BRL',
      version: Number.isInteger(source.version) && source.version >= 0 ? source.version : 0,
      canManage: source.can_manage === true,
      updatedAt: source.updated_at || null,
      updatedByName: source.updated_by_name || null
    };
  }

  globalThis.__EPI_PURCHASE_LIMITS_RULES__ = Object.freeze({
    MAX_INTEGER_DIGITS,
    normalizeLimitInput,
    formatLimit,
    describeLimits
  });
})();
