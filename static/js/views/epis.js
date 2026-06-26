'use strict';

// Módulo de view: EPIs (refatoração JS — Fase 6).
//
// Reimplementação modular de renderApprovedEpis de app.js.
// Lê dados de globalThis.__EPI_APP_STATE__ e refs de globalThis.__EPI_REFS__.
(function () {
  if (globalThis.__EPI_MODULE_EPIS_LOADED__) { return; }
  globalThis.__EPI_MODULE_EPIS_LOADED__ = true;

  function getState() { return globalThis.__EPI_APP_STATE__ || {}; }
  function getRefs() { return globalThis.__EPI_REFS__ || {}; }
  function filterByCompany(items) {
    return typeof globalThis.filterByUserCompany === 'function'
      ? globalThis.filterByUserCompany(items)
      : items;
  }
  function fmtDate(v) {
    return typeof globalThis.formatDate === 'function' ? globalThis.formatDate(v) : String(v || '-');
  }

  // ── Funções de render ─────────────────────────────────────────────────────

  function renderApprovedEpis() {
    const refs = getRefs();
    if (!refs.approvedEpiTable) { return; }
    const byName = String(refs.approvedEpiSearchName?.value || '').toLowerCase();
    const byProtection = String(refs.approvedEpiSearchProtection?.value || '').toLowerCase();
    const byCa = String(refs.approvedEpiSearchCa?.value || '').toLowerCase();
    const byManufacturer = String(refs.approvedEpiSearchManufacturer?.value || '').toLowerCase();
    const bySection = String(refs.approvedEpiSearchSection?.value || '').toLowerCase();
    const rows = filterByCompany(getState().epis || []).filter((item) =>
      String(item.name || '').toLowerCase().includes(byName)
      && String(item.sector || '').toLowerCase().includes(byProtection)
      && String(item.ca || '').toLowerCase().includes(byCa)
      && String(item.manufacturer || '').toLowerCase().includes(byManufacturer)
      && String(item.epi_section || '').toLowerCase().includes(bySection)
    );
    refs.approvedEpiTable.innerHTML = rows.map((item) => `<tr>
    <td>${item.name || '-'}</td>
    <td>${item.manufacturer || '-'}</td>
    <td>${item.model_reference || '-'}</td>
    <td>${item.ca || '-'}</td>
    <td>${fmtDate(item.ca_expiry)}</td>
    <td>${Number(item.manufacturer_validity_months || 0)}</td>
    <td>${item.sector || '-'}</td>
    <td>${item.epi_section || '-'}</td>
    <td>${item.epi_photo_data ? `<img src="${item.epi_photo_data}" alt="Foto ${item.name}" style="width:56px;height:56px;object-fit:cover;border-radius:6px;">` : '-'}</td>
    <td>${item.manufacturer_recommendations || '-'}</td>
  </tr>`).join('') || globalThis.dsTableState({ colspan: 10, message: 'Sem EPIs aprovados para os filtros informados.' });
  }

  // Alias usado por resolveRefreshHandlers em router/app.js
  function renderEpis() { renderApprovedEpis(); }

  // ── Exports ───────────────────────────────────────────────────────────────

  const episExports = { renderApprovedEpis, renderEpis };

  for (const [name, fn] of Object.entries(episExports)) {
    if (typeof globalThis[name] === 'undefined') { globalThis[name] = fn; }
  }
  globalThis.__EPI_VIEW_EPIS__ = Object.freeze({ ...episExports });

  const helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
  Object.assign(helpers, episExports);
  globalThis.__EPI_FRONTEND_HELPERS__ = helpers;
})();
