'use strict';

// Helpers de view compartilhados (refatoração JS — Fase 6).
//
// Funções puras reutilizadas em múltiplas views de app.js.
// Segue o padrão de delegação: usa globalThis.X se disponível (app.js em
// runtime), senão usa implementação local idêntica.
(function () {
  if (globalThis.__EPI_MODULE_VIEW_HELPERS_LOADED__) { return; }
  globalThis.__EPI_MODULE_VIEW_HELPERS_LOADED__ = true;

  function getState() { return globalThis.__EPI_APP_STATE__ || {}; }

  // ── Escape HTML (idêntico a app.js escapeHtml) ────────────────────────────
  function escapeHtml(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // ── Formatação de datas (idêntico a app.js formatDate) ───────────────────
  function formatDate(value) {
    const raw = String(value || '').trim();
    if (!raw) { return '-'; }
    const parsed = /^\d{4}-\d{2}-\d{2}$/.test(raw)
      ? new Date(`${raw}T00:00:00`)
      : new Date(raw);
    if (Number.isNaN(parsed.getTime())) { return '-'; }
    return new Intl.DateTimeFormat('pt-BR').format(parsed);
  }

  function formatDateTime(value) {
    const parsed = new Date(String(value || '').trim());
    if (Number.isNaN(parsed.getTime())) { return '-'; }
    return parsed.toLocaleString('pt-BR');
  }

  // ── Filtro por empresa do usuário (idêntico a app.js) ────────────────────
  function filterByUserCompany(items) {
    const state = getState();
    if (!state.user || state.user.role === 'master_admin') { return items; }
    return items.filter((item) => {
      const directCompanyId = item?.company_id;
      if (directCompanyId !== undefined && directCompanyId !== null && String(directCompanyId) !== '') {
        return String(directCompanyId) === String(state.user.company_id || '');
      }
      const isCompanyRecord = item && Object.hasOwn(item, 'license_status') && Object.hasOwn(item, 'user_limit');
      if (isCompanyRecord) {
        return String(item.id || '') === String(state.user.company_id || '');
      }
      return false;
    });
  }

  // ── Filtro de busca do dashboard (idêntico a app.js matchesDashboardQuery) ─
  function matchesDashboardQuery(values = []) {
    const query = String(getState().dashboardFilters?.query || '').trim().toLowerCase();
    if (!query) { return true; }
    const haystack = values.map((item) => String(item || '').toLowerCase()).join(' ');
    return haystack.includes(query);
  }

  // ── Formatação de tamanhos de estoque (idêntico a app.js) ─────────────────

  function normalizeStockSizeValue(value) {
    const normalized = String(value ?? '').trim();
    if (!normalized) { return ''; }
    const lowered = normalized.toLowerCase();
    if (['n/a', 'na', 'selecione', 'selecione o tamanho', 'null', 'undefined'].includes(lowered)) {
      return '';
    }
    return normalized;
  }

  function formatItemSizeDisplay(item = {}) {
    const parts = [];
    const gloveSize = normalizeStockSizeValue(item.glove_size);
    const generalSize = normalizeStockSizeValue(item.size);
    const uniformSize = normalizeStockSizeValue(item.uniform_size);
    if (gloveSize) { parts.push(`Luva: ${gloveSize}`); }
    if (generalSize && generalSize !== gloveSize && generalSize !== uniformSize) { parts.push(`Tam.: ${generalSize}`); }
    if (uniformSize) { parts.push(`Uniforme: ${uniformSize}`); }
    return parts.join(' | ') || '—';
  }

  function formatSizeBalancesDisplay(sizeBalances = []) {
    if (!Array.isArray(sizeBalances) || !sizeBalances.length) { return '—'; }
    return sizeBalances.map((item) => `${formatItemSizeDisplay(item)} (${Number(item.quantity || 0)})`).join('<br>');
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  const viewHelperExports = {
    escapeHtml,
    formatDate,
    formatDateTime,
    filterByUserCompany,
    matchesDashboardQuery,
    normalizeStockSizeValue,
    formatItemSizeDisplay,
    formatSizeBalancesDisplay
  };

  for (const [name, fn] of Object.entries(viewHelperExports)) {
    if (typeof globalThis[name] === 'undefined') { globalThis[name] = fn; }
  }
  globalThis.__EPI_VIEW_HELPERS__ = Object.freeze({ ...viewHelperExports });

  const helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
  Object.assign(helpers, viewHelperExports);
  globalThis.__EPI_FRONTEND_HELPERS__ = helpers;
})();
