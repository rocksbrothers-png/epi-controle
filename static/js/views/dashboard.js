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
    // Sanitização COMPLETA para uso em atributos HTML (aspas incluídas). O
    // fallback precisa escapar &, <, >, " e ' — senão um valor com aspas
    // poderia quebrar o atributo (XSS). Espelha o escapeHtml global.
    return typeof globalThis.escapeHtml === 'function'
      ? globalThis.escapeHtml(v)
      : String(v ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
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

  // Navega para uma view reutilizando o item de menu existente (mesmo mecanismo
  // do CTA do banner de estoque crítico). Delegação anexada uma única vez.
  function _bindStatCardNavigation(container) {
    if (!container || container.dataset.navBound === '1') { return; }
    container.dataset.navBound = '1';
    const go = (el) => {
      const validity = el?.getAttribute('data-validity');
      if (validity && typeof globalThis.openEpisFilteredByValidity === 'function') {
        globalThis.openEpisFilteredByValidity(validity);
        return;
      }
      const view = el?.getAttribute('data-view');
      if (!view) { return; }
      const tab = el?.getAttribute('data-tab');
      // Quando o indicador aponta para um item que vive numa sub-aba específica,
      // abre a view já na aba correta (deep-link); senão, navega para a view.
      if (tab && typeof globalThis.openViewSubtab === 'function') {
        globalThis.openViewSubtab(view, tab);
        return;
      }
      document.querySelector(`.menu-link[data-view="${view}"]`)?.click();
    };
    container.addEventListener('click', (event) => {
      const card = event.target?.closest?.('.dashboard-kpi-card[data-view]');
      if (card) { go(card); }
    });
    container.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter' && event.key !== ' ') { return; }
      const card = event.target?.closest?.('.dashboard-kpi-card[data-view]');
      if (card) { event.preventDefault(); go(card); }
    });
  }

  function _kpiCardHtml({ label, value, view, tone, validity, tab }) {
    const classes = ['dashboard-kpi-card'];
    const clickable = Boolean(view || validity);
    if (clickable) { classes.push('is-clickable'); }
    if (tone === 'danger') { classes.push('is-danger'); }
    else if (tone === 'warning') { classes.push('is-warning'); }
    const nav = clickable
      ? ` data-view="${esc(view || 'epis')}"${validity ? ` data-validity="${esc(validity)}"` : ''}${tab ? ` data-tab="${esc(tab)}"` : ''} role="button" tabindex="0"`
      : '';
    return `<article class="${classes.join(' ')}"${nav}><span>${label}</span><strong>${value}</strong></article>`;
  }

  function _kpiGroupHtml(title, cards) {
    const visible = cards.filter(Boolean);
    if (!visible.length) { return ''; }
    return `<section class="kpi-group">`
      + `<h4 class="kpi-group-title">${title}</h4>`
      + `<div class="dashboard-kpi-grid">${visible.map(_kpiCardHtml).join('')}</div>`
      + `</section>`;
  }

  // Painel executivo consolidado (auditoria Dashboard §1/§2): fonte única de KPIs
  // organizada por prioridade (Operacionais / Segurança / Gerenciais). Elimina a
  // duplicação com os KPIs do painel interativo. Todos os valores reaproveitam o
  // state já carregado — sem alterar regra de negócio.
  // Item 2: fonte ÚNICA de conformidade de estoque (backend #737). O Dashboard
  // NÃO recalcula validade sobre o catálogo — consome os mesmos números da tela
  // "Validade e Bloqueios", garantindo que o total do card = total da listagem.
  let _compliance = null;
  let _complianceLoading = false;

  // Fonte única já carregada (cache do módulo ou do state). Preferimos o state
  // quando presente para permitir pré-carga por app.js/testes de integração.
  function getCompliance() {
    return _compliance || getState().stockCompliance || null;
  }

  async function loadStockCompliance() {
    if (_complianceLoading) { return; }
    _complianceLoading = true;
    try {
      const state = getState();
      const isMaster = state.user?.role === 'master_admin';
      const companyId = isMaster ? String(state.dashboardCompanyId || state.user?.company_id || '') : '';
      const qs = companyId ? `?company_id=${encodeURIComponent(companyId)}` : '';
      const api = globalThis.api;
      if (typeof api !== 'function') { return; }
      const data = await api(`/api/stock/compliance${qs}`);
      _compliance = data && data.summary ? data : null;
      if (_compliance) { getState().stockCompliance = _compliance; }
      renderStats();
    } catch (error) {
      _compliance = { summary: {}, categories: {}, __error: true };
      globalThis.reportNonCriticalError?.('[dashboard] compliance', error);
      renderStats();
    } finally {
      _complianceLoading = false;
    }
  }

  // Permite forçar recarga (ex.: master troca de empresa no filtro do Dashboard).
  function refreshStockCompliance() {
    _compliance = null;
    const st = getState();
    if (st) { st.stockCompliance = null; }
    return loadStockCompliance();
  }

  function renderStats() {
    const state = getState();
    const refs = getRefs();
    if (!refs.statsGrid) { return; }
    const epis = filterByCompany(state.epis || []);
    const deliveries = filterByCompany(state.deliveries || []);
    const employees = filterByCompany(state.employees || []);
    const units = filterByCompany(state.units || []);
    const companies = state.user?.role === 'master_admin' ? (state.companies || []) : filterByCompany(state.companies || []);
    const feedbacks = state.feedbacks || [];
    const canFeedback = userHasPermission('epi_feedback:view');
    // Distinção conceitual (NT 146/2015, ver modules/epis/validity.py):
    //  - Validade do CA (ca_expiry): rege a AQUISIÇÃO/compra do EPI.
    //  - Validade do fabricante (epi_validity_date): rege o USO/ENTREGA e a
    //    gestão física do estoque (FEFO). É o indicador primário de estoque.
    // Item 2 (fonte única): as contagens de conformidade NÃO são recalculadas
    // sobre o catálogo (state.epis). Elas vêm do backend #737
    // (GET /api/stock/compliance), a MESMA base da tela "Validade e Bloqueios"
    // (epi_stock_items). Assim o total do card = total da listagem operacional.
    // Enquanto a fonte não chegou, dispara o carregamento e mostra placeholder.
    const comp = getCompliance();
    if (comp === null) { void loadStockCompliance(); }
    const cSummary = comp && !comp.__error ? (comp.summary || {}) : null;
    const cError = Boolean(comp && comp.__error);
    // Valor de um indicador de conformidade: número quando a fonte chegou,
    // '—' em erro, '…' enquanto carrega. Nunca recai no cálculo do catálogo.
    const cVal = (key) => {
      if (cError) { return tr('dashboard.complianceError', '—'); }
      if (!cSummary) { return tr('dashboard.loadingShort', '…'); }
      return Number(cSummary[key] || 0);
    };
    const productExpired = cVal('product_expired');
    const productExpiring = cVal('product_expiring');
    const caExpired = cVal('ca_expired');
    const caExpiring = cVal('ca_expiring');
    const adminBlocked = cVal('admin_blocked');
    const missingManufacture = cVal('missing_manufacture');
    const missingLot = cVal('missing_lot');
    const reclamacoes = feedbacks.filter((f) => (f.feedback_subtype || f.type) === 'reclamacao').length;
    const elogios = feedbacks.filter((f) => (f.feedback_subtype || f.type) === 'elogio').length;

    const operational = _kpiGroupHtml(tr('dashboard.groupOperational', 'Indicadores operacionais'), [
      { label: tr('dashboard.activeEmployees', 'Colaboradores ativos'), value: employees.length, view: 'colaboradores' },
      { label: tr('dashboard.deliveries', 'Entregas'), value: deliveries.length, view: 'entregas', tab: 'historico' },
      // Estoque crítico (estoque baixo) vive na aba "Alertas" do Controle de Estoque.
      { label: tr('dashboard.criticalStock', 'Estoque crítico'), value: (state.lowStock || []).length, view: 'estoque', tab: 'alertas' },
      { label: tr('dashboard.returnedDeliveries', 'Entregas devolvidas'), value: deliveries.filter((d) => String(d.returned_date || '').trim()).length, view: 'entregas', tab: 'historico' },
    ]);
    const safety = _kpiGroupHtml(tr('dashboard.groupSafety', 'Indicadores de segurança'), [
      // Validade do PRODUTO (fabricante) — indicador primário de estoque, FEFO.
      // Clique abre a lista de EPIs já filtrada pela validade correspondente.
      { label: tr('dashboard.productExpired', 'EPIs com validade vencida'), value: productExpired, view: 'epis', validity: 'product_expired', tone: 'danger' },
      { label: tr('dashboard.productExpiring', 'EPIs próximos do vencimento'), value: productExpiring, view: 'epis', validity: 'product_expiring', tone: 'warning' },
      // Validade do CA (certificação) — indicadores distintos da validade física.
      { label: tr('dashboard.caExpired', 'CA vencidos'), value: caExpired, view: 'epis', validity: 'ca_expired', tone: 'danger' },
      { label: tr('dashboard.caExpiring', 'CA próximos do vencimento'), value: caExpiring, view: 'epis', validity: 'ca_expiring', tone: 'warning' },
      // Bloqueio administrativo — itens de estoque fora de uso (status blocked_*).
      // Abre Estoque → "Validade e Bloqueios", onde vive o "Estoque bloqueado".
      { label: tr('dashboard.adminBlocked', 'Bloqueio administrativo'), value: adminBlocked, view: 'estoque', tab: 'validade' },
      // Lacunas de rastreabilidade (item disponível sem data de fabricação/lote).
      // Abrem a "Gestão de Validade" (mesma aba Validade e Bloqueios).
      { label: tr('dashboard.missingManufacture', 'Sem data de fabricação'), value: missingManufacture, view: 'estoque', tab: 'validade' },
      { label: tr('dashboard.missingLot', 'Sem lote'), value: missingLot, view: 'estoque', tab: 'validade' },
      // Alertas operacionais consolidados vivem na aba "Alertas" do Estoque.
      { label: tr('dashboard.alerts', 'Alertas'), value: (state.alerts || []).length, view: 'estoque', tab: 'alertas' },
      canFeedback ? { label: tr('dashboard.negativeEvaluations', 'Avaliações negativas'), value: reclamacoes, view: 'avaliacoes' } : null,
    ]);
    const managerial = _kpiGroupHtml(tr('dashboard.groupManagerial', 'Indicadores gerenciais'), [
      { label: tr('dashboard.companies', 'Empresas'), value: companies.length, view: 'empresas' },
      { label: tr('nav.units', 'Unidades'), value: units.length, view: 'unidades' },
      { label: tr('nav.epis', 'EPIs'), value: epis.length, view: 'epis' },
      canFeedback ? { label: tr('dashboard.feedbacks', 'Avaliações e Sugestões'), value: feedbacks.length, view: 'avaliacoes' } : null,
      canFeedback ? { label: tr('dashboard.complaintsPraise', '↳ Reclamações / Elogios'), value: `${reclamacoes} / ${elogios}`, view: 'avaliacoes' } : null,
    ]);
    let poolGroup = '';
    if (state.user?.role === 'master_admin' && state.dbPoolStatus?.initialized) {
      poolGroup = _kpiGroupHtml(tr('dashboard.groupSystem', 'Sistema'), [
        { label: tr('dashboard.dbPoolUse', 'Pool DB (uso)'), value: `${state.dbPoolStatus.in_use}/${state.dbPoolStatus.maxconn}` },
        { label: tr('dashboard.dbPoolFree', 'Pool DB (livres)'), value: `${state.dbPoolStatus.available}` },
      ]);
    }
    refs.statsGrid.innerHTML = `<div class="dashboard-kpi-groups">${operational}${safety}${managerial}${poolGroup}</div>`;
    _bindStatCardNavigation(refs.statsGrid);
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

  // Deep-link: abre a view alvo e aplica um filtro (auditoria Dashboard §3/§10).
  // Reutiliza o item de menu existente e os inputs de filtro já presentes na tela.
  function _openViewFiltered(view, inputId, value) {
    document.querySelector(`.menu-link[data-view="${view}"]`)?.click();
    setTimeout(() => {
      const el = document.getElementById(inputId);
      if (!el) { return; }
      el.value = value;
      el.dispatchEvent(new Event('input', { bubbles: true }));
    }, 60);
  }

  // Mapeia a categoria do alerta para uma ação navegável (tela + filtro).
  function _alertAction(alert) {
    const name = String(alert?.epi_name || '').trim();
    if (!name) { return null; }
    if (alert.category === 'ca') {
      return { label: tr('dashboard.alertViewEpis', 'Ver EPIs'), view: 'epis', input: 'epis-filter-search', value: name };
    }
    if (alert.category === 'stock' || alert.category === 'manufacturer') {
      return { label: tr('dashboard.alertViewStock', 'Ver Estoque'), view: 'estoque', input: 'stock-filter-name', value: name };
    }
    return null;
  }

  function _bindAlertActions(container) {
    if (!container || container.dataset.actionBound === '1') { return; }
    container.dataset.actionBound = '1';
    container.addEventListener('click', (event) => {
      const btn = event.target?.closest?.('.alert-action[data-view]');
      if (!btn) { return; }
      _openViewFiltered(btn.getAttribute('data-view'), btn.getAttribute('data-input'), btn.getAttribute('data-value') || '');
    });
  }

  function renderAlerts() {
    const refs = getRefs();
    renderCriticalStockBanner();
    if (!refs.alertsList) { return; }
    const items = (getState().alerts || []).filter((item) => matchesQuery([item.title, item.description, item.type]));
    refs.alertsList.innerHTML = items.map((item) => {
      const action = _alertAction(item);
      const btn = action
        ? `<button type="button" class="alert-action" data-view="${esc(action.view)}" data-input="${esc(action.input)}" data-value="${esc(action.value)}">${action.label}</button>`
        : '';
      return `<div class="alert-item ${item.type}"><div class="alert-item-body"><strong>${item.title}</strong><div>${item.description}</div></div>${btn}</div>`;
    }).join('')
      || `<div class="summary-item">${tr('dashboard.noAlertsFilter', 'Sem alertas para o filtro atual.')}</div>`;
    _bindAlertActions(refs.alertsList);
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
      // KPIs numéricos foram unificados no painel executivo consolidado
      // (renderStats). Aqui o painel interativo mantém apenas os gráficos, para
      // não repetir os mesmos indicadores (auditoria Dashboard §1).
      if (refs.dashboardInteractiveKpis) {
        refs.dashboardInteractiveKpis.innerHTML = '';
        refs.dashboardInteractiveKpis.hidden = true;
      }

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
    renderDashboardInterativo,
    loadStockCompliance,
    refreshStockCompliance
  };

  for (const [name, fn] of Object.entries(dashboardExports)) {
    if (typeof globalThis[name] === 'undefined') { globalThis[name] = fn; }
  }
  globalThis.__EPI_DASHBOARD__ = Object.freeze({ ...dashboardExports });

  const helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
  Object.assign(helpers, dashboardExports);
  globalThis.__EPI_FRONTEND_HELPERS__ = helpers;
})();
