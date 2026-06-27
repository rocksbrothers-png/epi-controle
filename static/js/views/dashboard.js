'use strict';

// Módulo de view: Dashboard (refatoração JS — Fase 6).
//
// Reimplementação modular das funções de render do dashboard de app.js.
// Lê dados de globalThis.__EPI_APP_STATE__ e refs de globalThis.__EPI_REFS__.
// Delega a helpers globais (renderPhase3SummaryCards, updatePhase3ContextStatus)
// com fallback no-op para funcionar standalone (testes, scripts externos).
(function () {
  if (globalThis.__EPI_MODULE_DASHBOARD_LOADED__) { return; }
  globalThis.__EPI_MODULE_DASHBOARD_LOADED__ = true;

  function getState() { return globalThis.__EPI_APP_STATE__ || {}; }
  function getRefs() { return globalThis.__EPI_REFS__ || {}; }
  function tr(key, fallback) {
    return typeof globalThis.trEpi === 'function' ? globalThis.trEpi(key, fallback) : fallback;
  }
  function userHasPermission(perm) {
    return typeof globalThis.currentUserHasPermission === 'function'
      ? globalThis.currentUserHasPermission(perm)
      : false;
  }
  function filterByCompany(items) {
    return typeof globalThis.filterByUserCompany === 'function'
      ? globalThis.filterByUserCompany(items)
      : items;
  }
  function matchesQuery(values) {
    return typeof globalThis.matchesDashboardQuery === 'function'
      ? globalThis.matchesDashboardQuery(values)
      : true;
  }
  function esc(v) {
    return typeof globalThis.escapeHtml === 'function'
      ? globalThis.escapeHtml(v)
      : String(v ?? '').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  function fmtDate(v) {
    return typeof globalThis.formatDate === 'function' ? globalThis.formatDate(v) : String(v || '-');
  }
  function phase3Cards(container, items) {
    if (typeof globalThis.renderPhase3SummaryCards === 'function') {
      globalThis.renderPhase3SummaryCards(container, items);
    }
  }

  // ── Helpers internos ─────────────────────────────────────────────────────

  function dashboardInteractiveEmptyMessage(message) {
    return `<div class="dashboard-chart-empty">${message}</div>`;
  }

  function buildDashboardMiniBars(items, { labelKey = 'label', valueKey = 'value' } = {}) {
    if (!Array.isArray(items) || !items.length) {
      return dashboardInteractiveEmptyMessage(tr('dashboard.noDataFilter', 'Sem dados para o filtro atual.'));
    }
    const max = Math.max(...items.map((item) => Number(item?.[valueKey] || 0)), 0);
    if (max <= 0) {
      return dashboardInteractiveEmptyMessage(tr('dashboard.noDataFilter', 'Sem dados para o filtro atual.'));
    }
    return `<div class="dashboard-mini-bars">${items.map((item) => {
      const value = Number(item?.[valueKey] || 0);
      const pct = Math.max(4, Math.round((value / max) * 100));
      const label = esc(item?.[labelKey] || '-');
      return `<div class="dashboard-mini-bar-row">
      <div class="dashboard-mini-bar-label"><span>${label}</span><strong>${value}</strong></div>
      <div class="dashboard-mini-bar-track"><div class="dashboard-mini-bar-fill" style="width:${pct}%"></div></div>
    </div>`;
    }).join('')}</div>`;
  }

  // ── Funções de render ─────────────────────────────────────────────────────

  function renderStats() {
    const state = getState();
    const refs = getRefs();
    if (!refs.statsGrid) { return; }
    const cards = [
      [tr('dashboard.companies', 'Empresas'), state.user?.role === 'master_admin' ? (state.companies || []).length : filterByCompany(state.companies || []).length],
      [tr('nav.employees', 'Colaboradores'), filterByCompany(state.employees || []).length],
      [tr('nav.epis', 'EPIs'), filterByCompany(state.epis || []).length],
      [tr('dashboard.deliveries', 'Entregas'), filterByCompany(state.deliveries || []).length],
      [tr('dashboard.alerts', 'Alertas'), (state.alerts || []).length]
    ];
    if (userHasPermission('epi_feedback:view')) {
      const feedbacks = state.feedbacks || [];
      const reclamacoes = feedbacks.filter((f) => (f.feedback_subtype || f.type) === 'reclamacao').length;
      const elogios = feedbacks.filter((f) => (f.feedback_subtype || f.type) === 'elogio').length;
      cards.push([tr('dashboard.feedbacks', 'Avaliações e Sugestões'), feedbacks.length]);
      cards.push([tr('dashboard.complaintsPraise', '↳ Reclamações / Elogios'), `${reclamacoes} / ${elogios}`]);
    }
    if (state.user?.role === 'master_admin' && state.dbPoolStatus?.initialized) {
      cards.push([tr('dashboard.dbPoolUse', 'Pool DB (uso)'), `${state.dbPoolStatus.in_use}/${state.dbPoolStatus.maxconn}`]);
      cards.push([tr('dashboard.dbPoolFree', 'Pool DB (livres)'), `${state.dbPoolStatus.available}`]);
    }
    refs.statsGrid.innerHTML = cards.map((item) => `<article class="stat-card"><div class="stat-label">${item[0]}</div><div class="stat-value">${item[1]}</div></article>`).join('');
    phase3Cards(refs.phase3ColaboradoresSummary, [
      { label: 'Total base', value: filterByCompany(state.employees || []).length },
      { label: 'Com e-mail', value: filterByCompany(state.employees || []).filter((item) => String(item.email || '').trim()).length },
      { label: 'Com WhatsApp', value: filterByCompany(state.employees || []).filter((item) => String(item.whatsapp || '').trim()).length }
    ]);
    phase3Cards(refs.phase3GestaoSummary, [
      { label: 'Vínculos ativos', value: filterByCompany(state.employees || []).length },
      { label: 'Movimentações', value: filterByCompany(state.employeeMovements || []).length },
      { label: 'Unidades', value: filterByCompany(state.units || []).length }
    ]);
    phase3Cards(refs.phase3EpisSummary, [
      { label: 'Catálogo', value: filterByCompany(state.epis || []).length },
      { label: 'Com foto', value: filterByCompany(state.epis || []).filter((item) => String(item.epi_photo_data || '').trim()).length },
      { label: tr('epi.caExpiry', 'Validade do CA'), value: filterByCompany(state.epis || []).filter((item) => String(item.ca_expiry || '').trim()).length }
    ]);
  }

  // P0-6 — destaca alertas de estoque crítico / CA vencendo com um banner
  // no topo da lista (componente ds-alert-banner). Aditivo: a lista detalhada
  // permanece inalterada abaixo.
  function isCriticalAlert(item) {
    const hay = `${item && item.type || ''} ${item && item.title || ''} ${item && item.description || ''}`.toLowerCase();
    return /crit|cr[íi]t|danger|baixo|m[íi]nim|venc|expir|esgot|zerad/.test(hay);
  }

  // P0-6 — banner de estoque crítico fixo no topo do dashboard, com CTA direto
  // para Compras. Renderizado fora da lista de alertas, em destaque.
  function renderCriticalStockBanner() {
    const el = document.getElementById('dashboard-critical-banner');
    if (!el) { return; }
    const critical = (getState().alerts || []).filter(isCriticalAlert);
    if (!critical.length || typeof globalThis.dsAlertBanner !== 'function') {
      el.innerHTML = '';
      return;
    }
    const msg = tr('dashboard.criticalStockBanner', '{n} alerta(s) de estoque crítico / CA vencendo requerem atenção.')
      .replace('{n}', String(critical.length));
    el.innerHTML = globalThis.dsAlertBanner({
      message: msg,
      variant: 'danger',
      ctaLabel: tr('dashboard.goToPurchases', 'Ver compras'),
      ctaId: 'dashboard-goto-compras'
    });
    el.style.marginBottom = critical.length ? '14px' : '';
    const cta = document.getElementById('dashboard-goto-compras');
    if (cta) {
      // Aciona a navegação reutilizando o item de menu de Compras (handler já existente).
      cta.onclick = () => { document.querySelector('.menu-link[data-view="compras"]')?.click(); };
    }
  }

  function renderAlerts() {
    const refs = getRefs();
    renderCriticalStockBanner();
    if (!refs.alertsList) { return; }
    const items = (getState().alerts || []).filter((item) => matchesQuery([item.title, item.description, item.type]));
    refs.alertsList.innerHTML = items.map((item) => `<div class="alert-item ${item.type}"><strong>${item.title}</strong><div>${item.description}</div></div>`).join('')
      || `<div class="summary-item">${tr('dashboard.noAlertsFilter', 'Sem alertas para o filtro atual.')}</div>`;
  }

  function renderLatestDeliveries() {
    const refs = getRefs();
    if (!refs.latestDeliveries) { return; }
    const items = filterByCompany(getState().deliveries || [])
      .filter((item) => matchesQuery([item.employee_name, item.epi_name, item.company_name, item.quantity_label]))
      .slice(0, 5);
    refs.latestDeliveries.innerHTML = items.map((item) => `<div class="list-item"><strong>${item.employee_name}</strong><div>${item.epi_name} - ${item.quantity} ${item.quantity_label}(s)</div><small>${item.company_name}${item.unit_name ? ' / ' + esc(item.unit_name) : ''}  ${fmtDate(item.delivery_date)}</small></div>`).join('')
      || `<div class="summary-item">${tr('dashboard.noDeliveriesFilter', 'Sem entregas para o filtro atual.')}</div>`;
  }

  function renderDashboardInterativo() {
    const state = getState();
    const refs = getRefs();
    if (!refs.dashboardInteractivePanel || !refs.dashboardInteractiveKpis) {
      if (refs.dashboardInteractiveLoading) { refs.dashboardInteractiveLoading.hidden = true; }
      if (refs.dashboardInteractiveError) { refs.dashboardInteractiveError.hidden = true; }
      return;
    }
    const enabled = typeof globalThis.isDashboardInterativoEnabled === 'function'
      ? globalThis.isDashboardInterativoEnabled()
      : (typeof globalThis.getFeatureFlag === 'function' && globalThis.getFeatureFlag('dashboard_interativo_enabled', { defaultValue: false }));
    refs.dashboardInteractivePanel.hidden = !enabled;
    refs.dashboardInteractiveLoading.hidden = true;
    refs.dashboardInteractiveError.hidden = true;
    if (!enabled) { return; }
    try {
      refs.dashboardInteractiveLoading.hidden = false;
      const scopedDeliveries = filterByCompany(state.deliveries || []);
      const scopedEmployees = filterByCompany(state.employees || []);
      const scopedEpis = filterByCompany(state.epis || []);
      const deliveriesThisMonth = scopedDeliveries.filter((item) => String(item.delivery_date || '').slice(0, 7) === new Date().toISOString().slice(0, 7)).length;
      const devolvidas = scopedDeliveries.filter((item) => String(item.returned_date || '').trim()).length;
      const kpis = [
        { label: tr('dashboard.deliveriesThisMonth', 'Entregas (mês)'), value: deliveriesThisMonth },
        { label: tr('dashboard.returnedDeliveries', 'Entregas devolvidas'), value: devolvidas },
        { label: tr('dashboard.registeredEpis', 'EPIs cadastrados'), value: scopedEpis.length },
        { label: tr('dashboard.activeEmployees', 'Colaboradores ativos'), value: scopedEmployees.length }
      ];
      if (userHasPermission('epi_feedback:view')) {
        kpis.push({ label: tr('dashboard.feedbacks', 'Avaliações e Sugestões'), value: (state.feedbacks || []).length });
      }
      refs.dashboardInteractiveKpis.innerHTML = kpis.map((item) => `<article class="dashboard-kpi-card"><span>${item.label}</span><strong>${item.value}</strong></article>`).join('');

      const deliveriesByCompany = scopedDeliveries.reduce((acc, item) => {
        const key = String(item.company_name || tr('dashboard.noCompany', 'Sem empresa'));
        acc.set(key, (acc.get(key) || 0) + 1);
        return acc;
      }, new Map());
      const companySeries = Array.from(deliveriesByCompany.entries())
        .map(([label, value]) => ({ label, value }))
        .sort((a, b) => b.value - a.value)
        .slice(0, 8);
      if (refs.dashboardChartDeliveriesCompany) {
        refs.dashboardChartDeliveriesCompany.innerHTML = buildDashboardMiniBars(companySeries);
      }

      const lowStockByUnit = (state.lowStock || []).reduce((acc, item) => {
        const key = String(item.unit_name || tr('dashboard.noUnit', 'Sem unidade'));
        acc.set(key, (acc.get(key) || 0) + 1);
        return acc;
      }, new Map());
      const unitSeries = Array.from(lowStockByUnit.entries())
        .map(([label, value]) => ({ label, value }))
        .sort((a, b) => b.value - a.value)
        .slice(0, 8);
      if (refs.dashboardChartLowStockUnit) {
        refs.dashboardChartLowStockUnit.innerHTML = buildDashboardMiniBars(unitSeries);
      }

      refs.dashboardInteractiveLoading.hidden = true;
    } catch (error) {
      refs.dashboardInteractiveLoading.hidden = true;
      if (refs.dashboardInteractiveError) {
        refs.dashboardInteractiveError.hidden = false;
        refs.dashboardInteractiveError.textContent = tr('dashboard.interactiveError', 'Erro ao carregar dashboard interativo.');
      }
      if (typeof globalThis.reportNonCriticalError === 'function') {
        globalThis.reportNonCriticalError('renderDashboardInterativo', error);
      }
    }
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  const dashboardExports = {
    buildDashboardMiniBars,
    renderStats,
    renderAlerts,
    renderLatestDeliveries,
    renderDashboardInterativo
  };

  for (const [name, fn] of Object.entries(dashboardExports)) {
    if (typeof globalThis[name] === 'undefined') { globalThis[name] = fn; }
  }
  globalThis.__EPI_DASHBOARD__ = Object.freeze({ ...dashboardExports });

  const helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
  Object.assign(helpers, dashboardExports);
  globalThis.__EPI_FRONTEND_HELPERS__ = helpers;
})();
