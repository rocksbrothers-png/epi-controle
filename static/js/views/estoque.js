'use strict';

// Módulo de view: Estoque (refatoração JS — Fase 6).
//
// Reimplementação modular das funções de render de estoque de app.js:
// renderStockEpis, renderLowStock, renderRequests.
// Lê dados de globalThis.__EPI_APP_STATE__ e refs de globalThis.__EPI_REFS__.
(function () {
  if (globalThis.__EPI_MODULE_ESTOQUE_LOADED__) { return; }
  globalThis.__EPI_MODULE_ESTOQUE_LOADED__ = true;

  function getState() { return globalThis.__EPI_APP_STATE__ || {}; }
  function getRefs() { return globalThis.__EPI_REFS__ || {}; }
  function tr(key, fallback) {
    return typeof globalThis.trEpi === 'function' ? globalThis.trEpi(key, fallback) : fallback;
  }
  function esc(v) {
    return typeof globalThis.escapeHtml === 'function'
      ? globalThis.escapeHtml(v)
      : String(v ?? '').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  function epiProtectionLabel(value) {
    return typeof globalThis.epiProtectionLabel === 'function' ? globalThis.epiProtectionLabel(value) : (value || '-');
  }
  function epiMeasureLabel(value) {
    return typeof globalThis.epiMeasureLabel === 'function' ? globalThis.epiMeasureLabel(value) : (value || '-');
  }
  function fmtSizeBalances(sizeBalances) {
    return typeof globalThis.formatSizeBalancesDisplay === 'function'
      ? globalThis.formatSizeBalancesDisplay(sizeBalances)
      : '—';
  }
  function phase3Cards(container, items) {
    if (typeof globalThis.renderPhase3SummaryCards === 'function') {
      globalThis.renderPhase3SummaryCards(container, items);
    }
  }
  function phase3Status(view, tone, message) {
    if (typeof globalThis.updatePhase3ContextStatus === 'function') {
      globalThis.updatePhase3ContextStatus(view, tone, message);
    }
  }

  // ── Helpers internos ─────────────────────────────────────────────────────

  function formatStockEpiRow(item) {
    const sizesFromBalances = fmtSizeBalances(item.size_balances);
    const sizesFromEpi = [
      item.glove_size !== 'N/A' ? `${tr('stock.gloveShort', 'Luva')}:${item.glove_size}` : '',
      item.size !== 'N/A' ? `${tr('stock.sizeShort', 'Tam')}:${item.size}` : '',
      item.uniform_size !== 'N/A' ? `${tr('stock.uniformShort', 'Unif')}:${item.uniform_size}` : ''
    ].filter(Boolean).join(', ');
    const sizesDisplay = sizesFromBalances || sizesFromEpi || '—';
    return `<tr>
    <td>${item.name}</td>
    <td>${epiProtectionLabel(item.sector)}</td>
    <td>${item.epi_section || '-'}</td>
    <td>${item.manufacturer || '-'}</td>
    <td>${item.ca || '-'}</td>
    <td>${item.unit_name || '-'}</td>
    <td>${sizesDisplay}</td>
    <td>${item.stock} ${epiMeasureLabel(item.unit_measure)}(s)</td>
    <td>${Number(item.minimum_stock ?? 0)}</td>
  </tr>`;
  }

  // ── Funções de render ─────────────────────────────────────────────────────

  function renderStockEpis() {
    const state = getState();
    const refs = getRefs();
    if (!refs.stockEpisTable) { return; }
    const rows = state.stockEpis || [];
    refs.stockEpisTable.innerHTML = rows.map(formatStockEpiRow).join('')
      || `<tr><td colspan="9">${tr('stock.noEpiForFilters', 'Nenhum EPI encontrado para os filtros.')}</td></tr>`;
    phase3Cards(refs.phase3EstoqueSummary, [
      { label: tr('stock.filteredItems', 'Itens filtrados'), value: rows.length },
      { label: tr('stock.lowStock', 'Estoque baixo'), value: (state.lowStock || []).length },
      { label: tr('stock.requests', 'Solicitações'), value: (state.requests || []).length }
    ]);
    phase3Status('estoque', 'success', tr('stock.itemsListed', '{count} item(ns) listado(s)').replace('{count}', rows.length));
  }

  function renderLowStock() {
    const refs = getRefs();
    if (!refs.stockLowList) { return; }
    const items = getState().lowStock || [];
    refs.stockLowList.innerHTML = items.map((item) => {
      const severity = String(item.severity || 'warning');
      const badge = severity === 'critical' ? tr('stock.critical', 'Crítico') : (severity === 'danger' ? tr('stock.high', 'Alto') : tr('stock.moderate', 'Moderado'));
      const sizeTag = (() => {
        if (!Array.isArray(item.size_balances) || !item.size_balances.length) { return ''; }
        const parts = item.size_balances.map((s) => {
          const label = [
            s.glove_size !== 'N/A' ? s.glove_size : '',
            s.size !== 'N/A' ? s.size : '',
            s.uniform_size !== 'N/A' ? s.uniform_size : ''
          ].filter(Boolean).join('/');
          return label ? `${label}:${s.quantity}` : '';
        }).filter(Boolean).join(', ');
        return parts ? ` [${parts}]` : '';
      })();
      return `<div class="summary-item"><strong>${item.company_name} / ${item.unit_name}</strong><div>${item.epi_name}${sizeTag}: ${item.stock} ${epiMeasureLabel(item.unit_measure)}(s) (${tr('stock.minimum', 'mínimo')} ${item.minimum_stock})</div><small>${tr('stock.criticality', 'Criticidade')}: ${badge}</small></div>`;
    }).join('') || `<div class="summary-item">${tr('stock.noLowStockItems', 'Sem itens com estoque baixo.')}</div>`;
  }

  function renderRequests() {
    const refs = getRefs();
    if (!refs.requestsList) { return; }
    const items = (getState().requests || []).filter((r) => r.status === 'solicitado');
    refs.requestsList.innerHTML = items.map((item) => {
      const sizeInfo = [
        item.glove_size !== 'N/A' ? `${tr('stock.gloveShort', 'Luva')}:${item.glove_size}` : '',
        item.size !== 'N/A' ? `${tr('stock.sizeShort', 'Tam')}:${item.size}` : '',
        item.uniform_size !== 'N/A' ? `${tr('stock.uniformShort', 'Unif')}:${item.uniform_size}` : ''
      ].filter(Boolean).join(' ') || '—';
      return `<div class="summary-item">
      <strong>${esc(item.employee_name || '—')}</strong>
      <div>${esc(item.employee_sector || '—')} / ${esc(item.employee_role || '—')} — ${esc(item.unit_name || '—')}</div>
      <div>${esc(item.epi_name || '—')} ${tr('epi.caShort', 'CA')}:${esc(item.ca || '—')} ${sizeInfo} × ${item.quantity}</div>
    </div>`;
    }).join('') || `<div class="summary-item">${tr('stock.noCriticalRequests', 'Sem solicitações críticas pendentes.')}</div>`;
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  const estoqueExports = {
    formatStockEpiRow,
    renderStockEpis,
    renderLowStock,
    renderRequests
  };

  for (const [name, fn] of Object.entries(estoqueExports)) {
    if (typeof globalThis[name] === 'undefined') { globalThis[name] = fn; }
  }
  globalThis.__EPI_ESTOQUE__ = Object.freeze({ ...estoqueExports });

  const helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
  Object.assign(helpers, estoqueExports);
  globalThis.__EPI_FRONTEND_HELPERS__ = helpers;
})();
