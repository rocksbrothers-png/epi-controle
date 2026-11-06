'use strict';
/* global tr, escapeHtml, formatCurrency, formatDate, daysUntil, filterByUserCompany, hasPermission,
   requirePermission, canAccessCommercialArea, formValues, getCommercialSettings, planOptionMarkup, planHintText,
   renderCommercialSummaryCard, renderCommercialAlertCard, renderCommercialExpiringCard, renderCommercialHistoryItem,
   formatCommercialDetails, platformBrandDisplayName, openAndPrintPopup, resetCommercialContractForm, loadBootstrap --
   globais do app.js, de shared/*, de views/view-helpers.js, de modules/auth e da C1, resolvidos na chamada */

// Interface: Comercial (UBX Comercial, fatia C3 — extraída de static/app.js).
//
// As 19 funções da tela Comercial fora do contrato: formulário da empresa
// (plano, limite, aditivo, vigência, situação, observações) e a prévia de
// valores; formulário dos parâmetros comerciais; painéis de KPIs, resumo,
// alertas, vencimentos e histórico; filtros e a lista de responsáveis;
// exportação CSV/Excel e impressão do histórico; suspender/reativar pelo
// cartão; salvar a empresa e os parâmetros. O contrato comercial está em
// ./commercial-contract-view.js; a apresentação pura na C1
// (./commercial-presentation.js e ../business/commercial-rules.js).
//
// Corpos idênticos aos do app.js (mesmas chaves de tradução, fallbacks, escapes,
// ids, classes e ordem das operações); a única linha nova em cada função é a
// leitura de `state` e `refs`, que no app.js eram constantes do bloco de carga e
// aqui vêm de globalThis.__EPI_APP_STATE__ e globalThis.__EPI_REFS__ (os MESMOS
// objetos, publicados pelo app.js; nenhum estado paralelo). HTTP só pela C2
// (../integrations/commercial-api.js) e pelo updateCompany de Empresas; nenhuma
// chamada direta a `api`. Autorização (commercial:view, Administrador Master,
// escopo da empresa) segue no backend: as checagens daqui só escondem ou evitam
// ações, como antes.
//
// Ficam no app.js: os parâmetros comerciais da sessão (getCommercialSettings e
// os clones), a marca da plataforma (platformBrandDisplayName, savePlatformBrand),
// os utilitários compartilhados openAndPrintPopup e fileToBase64, a ligação dos
// listeners, os resets de navegação e o renderAll.
//
// Publicação: as 16 síncronas eram globais do app.js (Annex B) e continuam em
// globalThis com os mesmos nomes; as 3 assíncronas (`async function` de bloco,
// nunca globais) ficam só no namespace. __EPI_COMMERCIAL_VIEW__ (congelado) é a
// fachada das 33 funções da interface comercial, na ordem do app.js, com as 14
// do contrato. Carga idempotente.
(function () {
  if (globalThis.__EPI_MODULE_COMMERCIAL_VIEW_LOADED__) { return; }
  globalThis.__EPI_MODULE_COMMERCIAL_VIEW_LOADED__ = true;

  // loadCommercialContract é assíncrona (não é global): fillCommercialForm a
  // chama pelo namespace do contrato, com o mesmo argumento e sem esperar, como antes.
  function loadCommercialContract(companyId) {
    return globalThis.__EPI_COMMERCIAL_CONTRACT_VIEW__.loadCommercialContract(companyId);
  }

  function filteredCommercialCompanies() {
    const state = globalThis.__EPI_APP_STATE__;
    const companies = filterByUserCompany(state.companies);
    if (!state.commercialFilters.status) return companies;
    return companies.filter((item) => item.license_status === state.commercialFilters.status);
  }

  function filteredCommercialLogs() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    const selectedCompanyId = refs.commercialCompany?.value || '';
    return state.companyAuditLogs.filter((item) => {
      if (selectedCompanyId && String(item.company_id) !== String(selectedCompanyId)) return false;
      if (state.commercialFilters.actor_name && item.actor_name !== state.commercialFilters.actor_name) return false;
      const day = String(item.created_at || '').slice(0, 10);
      if (state.commercialFilters.date_from && day < state.commercialFilters.date_from) return false;
      if (state.commercialFilters.date_to && day > state.commercialFilters.date_to) return false;
      return true;
    });
  }

  function fillCommercialSettingsForm() {
    const refs = globalThis.__EPI_REFS__;
    if (!refs.commercialSettingsForm) return;
    const settings = getCommercialSettings();
    refs.commercialSettingsForm.elements.unit_price.value = settings.unit_price ?? 42;
    refs.commercialSettingsForm.elements.individual_max.value = settings.plans.individual.max_users ?? 1;
    refs.commercialSettingsForm.elements.start_max.value = settings.plans.start.max_users ?? 10;
    refs.commercialSettingsForm.elements.business_max.value = settings.plans.business.max_users ?? 25;
    refs.commercialSettingsForm.elements.corporate_max.value = settings.plans.corporate.max_users ?? 100;
    refs.commercialSettingsForm.elements.enterprise_min.value = settings.plans.enterprise.min_users ?? 101;
  }

  function refreshCommercialPreview(company = null) {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    if (!refs.commercialForm) return;
    const currentCompany = company || state.companies.find((item) => String(item.id) === String(refs.commercialCompany?.value || ''));
    const unitPrice = Number(getCommercialSettings().unit_price || 0);
    const activeUsers = Number(currentCompany?.user_count || 0);
    const userLimit = Number(refs.commercialForm.elements.user_limit.value || currentCompany?.user_limit || 0);
    const planName = refs.commercialForm.elements.plan_name.value || currentCompany?.plan_name || 'start';
    const addendumEnabled = refs.commercialForm.elements.addendum_enabled.checked;
    refs.commercialForm.elements.unit_price_display.value = formatCurrency(unitPrice, globalThis.EpiI18n?.lang);
    refs.commercialForm.elements.monthly_value.value = formatCurrency(activeUsers * unitPrice, globalThis.EpiI18n?.lang);
    refs.commercialForm.elements.projected_monthly_value.value = formatCurrency(userLimit * unitPrice, globalThis.EpiI18n?.lang);
    if (refs.commercialPlanHint) refs.commercialPlanHint.textContent = planHintText(planName, addendumEnabled);
  }

  function fillCommercialForm(companyId) {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    if (!refs.commercialForm || !refs.commercialCompany) return;
    const visibleCompanies = filterByUserCompany(state.companies);
    refs.commercialCompany.innerHTML = visibleCompanies.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}</option>`).join('');
    refs.commercialForm.elements.plan_name.innerHTML = planOptionMarkup();
    const selected = visibleCompanies.find((item) => String(item.id) === String(companyId || refs.commercialCompany.value)) || visibleCompanies[0];
    if (!selected) return;
    refs.commercialCompany.value = selected.id;
    refs.commercialForm.elements.company_id.value = selected.id;
    refs.commercialForm.elements.plan_name.value = selected.plan_name || 'start';
    refs.commercialForm.elements.user_limit.value = selected.user_limit || 1;
    refs.commercialForm.elements.addendum_enabled.checked = Number(selected.addendum_enabled || 0) === 1;
    refs.commercialForm.elements.contract_start.value = selected.contract_start || '';
    refs.commercialForm.elements.contract_end.value = selected.contract_end || '';
    refs.commercialForm.elements.license_status.value = selected.license_status || 'active';
    // FIX-EMPRESAS-ACTIVE-V1: `?? 1` (não `|| 1`) — empresa inativa (0) abre como inativa e não é reativada ao salvar.
    refs.commercialForm.elements.active.value = String(Number(selected.active ?? 1));
    refs.commercialForm.elements.commercial_notes.value = selected.commercial_notes || '';
    refreshCommercialPreview(selected);
    resetCommercialContractForm({ preserveClauses: true });
    if (canAccessCommercialArea()) loadCommercialContract(selected.id);
  }

  async function toggleCommercialStatus(companyId, mode) {
    const state = globalThis.__EPI_APP_STATE__;
    const company = state.companies.find((item) => String(item.id) === String(companyId));
    if (!company || !hasPermission('companies:update')) return;
    const next = mode === 'reactivate'
      ? { active: 1, license_status: 'active' }
      : { active: 0, license_status: 'suspended' };
    try {
      await globalThis.__EPI_COMPANIES_API__.updateCompany(company.id, {
          actor_user_id: state.user.id,
          name: company.name,
          legal_name: company.legal_name,
          cnpj: company.cnpj,
          logo_type: company.logo_type || '',
          plan_name: company.plan_name,
          user_limit: company.user_limit,
          contract_start: company.contract_start || '',
          contract_end: company.contract_end || '',
          monthly_value: company.monthly_value || 0,
          addendum_enabled: company.addendum_enabled || 0,
          license_status: next.license_status,
          active: next.active,
          commercial_notes: company.commercial_notes || ''
      });
      await loadBootstrap();
      fillCommercialForm(company.id);
    } catch (error) { alert(error.message); }
  }

  function renderCommercialStats() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    if (!refs.commercialStats) return;
    const companies = filterByUserCompany(state.companies);
    const monthlyTotal = companies.reduce((total, item) => total + Number(item.monthly_value || 0), 0);
    const activeCount = companies.filter((item) => item.license_status === 'active').length;
    const suspendedCount = companies.filter((item) => item.license_status === 'suspended').length;
    const expiredCount = companies.filter((item) => item.license_status === 'expired').length;
    refs.commercialStats.innerHTML = [
      [tr('commercial.panel.statMonthlyRevenue', 'Faturamento mensal'), formatCurrency(monthlyTotal, globalThis.EpiI18n?.lang)],
      [tr('commercial.panel.statActive', 'Empresas ativas'), (globalThis.EpiI18n?.formatNumber?.(activeCount) ?? String(activeCount))],
      [tr('commercial.panel.statSuspended', 'Suspensas'), (globalThis.EpiI18n?.formatNumber?.(suspendedCount) ?? String(suspendedCount))],
      [tr('commercial.panel.statExpired', 'Expiradas'), (globalThis.EpiI18n?.formatNumber?.(expiredCount) ?? String(expiredCount))]
    ].map((item) => `<article class="stat-card"><div class="stat-label">${escapeHtml(item[0])}</div><div class="stat-value">${escapeHtml(item[1])}</div></article>`).join('');
  }

  function renderCommercialSummary() {
    const refs = globalThis.__EPI_REFS__;
    if (!refs.commercialSummary) return;
    const companies = filteredCommercialCompanies();
    refs.commercialSummary.innerHTML = companies.map(renderCommercialSummaryCard).join('') || `<div class="summary-item">${escapeHtml(tr('commercial.panel.noCompanies', 'Sem empresas cadastradas.'))}</div>`;
  }

  function renderCommercialAlerts() {
    const refs = globalThis.__EPI_REFS__;
    if (!refs.commercialAlerts) return;
    const alerts = filteredCommercialCompanies().filter((item) => Number(item.limit_reached) === 1 || item.near_limit || ['suspended', 'expired'].includes(item.license_status) || Number(item.active) !== 1);
    refs.commercialAlerts.innerHTML = alerts.map(renderCommercialAlertCard).join('') || `<div class="summary-item">${escapeHtml(tr('commercial.panel.noAlerts', 'Nenhuma empresa em alerta comercial.'))}</div>`;
  }

  function renderCommercialHistory() {
    const refs = globalThis.__EPI_REFS__;
    if (!refs.commercialHistory) return;
    const logs = filteredCommercialLogs();
    refs.commercialHistory.innerHTML = logs.slice(0, 12).map(renderCommercialHistoryItem).join('') || `<div class="summary-item">${escapeHtml(tr('commercial.panel.noHistory', 'Sem histórico comercial registrado.'))}</div>`;
  }

  function renderCommercialExpiring() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    if (!refs.commercialExpiring) return;
    const expiring = filterByUserCompany(state.companies)
      .map((item) => ({ item, days: daysUntil(item.contract_end) }))
      .filter((entry) => entry.days !== null && entry.days >= 0 && entry.days <= 30)
      .sort((a, b) => a.days - b.days);
    refs.commercialExpiring.innerHTML = expiring.map(renderCommercialExpiringCard).join('') || `<div class="summary-item">${escapeHtml(tr('commercial.panel.noExpiring', 'Nenhum contrato vencendo nos próximos 30 dias.'))}</div>`;
  }

  function populateCommercialActors() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    if (!refs.commercialFilterActor) return;
    const names = [...new Set(state.companyAuditLogs.map((item) => item.actor_name))].sort((a, b) => String(a).localeCompare(String(b), globalThis.EpiI18n?.lang || 'pt-BR'));
    const optionsHtml = names.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('');
    refs.commercialFilterActor.innerHTML = `<option value="" data-i18n="user.filterAll">Todos</option>` + optionsHtml;
    refs.commercialFilterActor.value = state.commercialFilters.actor_name;
    refs.commercialFilterDateFrom.value = state.commercialFilters.date_from;
    refs.commercialFilterDateTo.value = state.commercialFilters.date_to;
    refs.commercialFilterStatus.value = state.commercialFilters.status;
  }

  function exportCommercialExcel() {
    const rows = filteredCommercialLogs();
    const exportBrandName = platformBrandDisplayName();
    const header = [
      tr('commercial.brand', 'Marca'),
      tr('commercial.panel.colCompany', 'Empresa'),
      tr('commercial.panel.colAction', 'Ação'),
      tr('commercial.panel.colActor', 'Responsável'),
      tr('commercial.panel.colDate', 'Data'),
      tr('commercial.panel.colSummary', 'Resumo'),
      tr('commercial.panel.colDetails', 'Detalhes')
    ];
    const body = rows.map((item) => {
      const detailsHtml = formatCommercialDetails(item.details);
      const createdAt = new Intl.DateTimeFormat(globalThis.EpiI18n?.lang || 'pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(item.created_at));
      return `<tr><td>${escapeHtml(exportBrandName)}</td><td>${escapeHtml(item.company_name)}</td><td>${escapeHtml(item.action_label)}</td><td>${escapeHtml(item.actor_name)}</td><td>${createdAt}</td><td>${escapeHtml(item.summary)}</td><td>${detailsHtml}</td></tr>`;
    }).join('');
    const tableStylesheet = 'table{border-collapse:collapse;width:100%;font-family:Segoe UI,Arial,sans-serif}th,td{border:1px solid var(--color-border);padding:8px;text-align:left;vertical-align:top}th{background:#f6d8c8}';
    const headerCells = header.map((item) => `<th scope="col">${escapeHtml(item)}</th>`).join('');
    const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><style>${tableStylesheet}</style></head><body><table><thead><tr>${headerCells}</tr></thead><tbody>${body}</tbody></table></body></html>`;
    const blob = new Blob([html], { type: 'application/vnd.ms-excel;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'historico-comercial.xls';
    link.click();
    URL.revokeObjectURL(link.href);
  }

  function formatCommercialFiltersLabel() {
    const state = globalThis.__EPI_APP_STATE__;
    return [
      state.commercialFilters.status
        ? tr('commercial.panel.filterStatus', 'Status: {status}', { status: tr(`license.${state.commercialFilters.status}`, state.commercialFilters.status) })
        : tr('commercial.panel.filterStatusAll', 'Status: todos'),
      state.commercialFilters.actor_name ? tr('commercial.panel.filterActor', 'Responsável: {actor}', { actor: state.commercialFilters.actor_name }) : '',
      state.commercialFilters.date_from ? tr('commercial.panel.filterFrom', 'De: {date}', { date: formatDate(state.commercialFilters.date_from) }) : '',
      state.commercialFilters.date_to ? tr('commercial.panel.filterTo', 'até: {date}', { date: formatDate(state.commercialFilters.date_to) }) : ''
    ].filter(Boolean).join(' | ');
  }

  function printCommercialHistory() {
    const rows = filteredCommercialLogs();
    const filters = formatCommercialFiltersLabel();
    const rowsHtml = rows.map((item) => {
      const detailsHtml = formatCommercialDetails(item.details);
      const createdAt = new Intl.DateTimeFormat(globalThis.EpiI18n?.lang || 'pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(item.created_at));
      return `<tr><td>${escapeHtml(item.company_name)}</td><td>${escapeHtml(item.action_label)}</td><td>${escapeHtml(item.actor_name)}</td><td>${createdAt}</td><td>${escapeHtml(item.summary)}</td><td class="detail">${detailsHtml}</td></tr>`;
    }).join('');
    const printTitle = escapeHtml(tr('commercial.panel.printTitle', 'Histórico Comercial'));
    const printHeaders = ['colCompany', 'colAction', 'colActor', 'colDate', 'colSummary', 'colDetails']
      .map((key, index) => `<th scope="col">${escapeHtml(tr(`commercial.panel.${key}`, ['Empresa', 'Ação', 'Responsável', 'Data', 'Resumo', 'Detalhes'][index]))}</th>`).join('');
    const html = `<!DOCTYPE html><html lang="${escapeHtml(String(globalThis.EpiI18n?.lang || 'pt-BR').toLowerCase())}"><head><meta charset="utf-8"><title>${printTitle}</title></head><body><h1>${printTitle}</h1><p>${escapeHtml(tr('commercial.panel.filtersLabel', 'Filtros: {filters}', { filters }))}</p><table><thead><tr>${printHeaders}</tr></thead><tbody>${rowsHtml}</tbody></table></body></html>`;
    if (!openAndPrintPopup(html, 'width=1100,height=800')) return alert(tr('commercial.panel.popupBlocked', 'Não foi possível abrir a janela de impressão. Permita pop-ups para este site.'));
  }

  function exportCommercialHistory() {
    const rows = filteredCommercialLogs();
    const exportBrandName = platformBrandDisplayName();
    const header = [
      tr('commercial.brand', 'Marca'),
      tr('commercial.panel.colCompany', 'Empresa'),
      tr('commercial.panel.colAction', 'Ação'),
      tr('commercial.panel.colActor', 'Responsável'),
      tr('commercial.panel.colDate', 'Data'),
      tr('commercial.panel.colSummary', 'Resumo'),
      tr('commercial.panel.colDetails', 'Detalhes')
    ];
    const lines = rows.map((item) => [
      exportBrandName,
      item.company_name,
      item.action_label,
      item.actor_name,
      item.created_at,
      item.summary,
      (item.details || []).map((detail) => `${detail.field}: ${detail.before || '-'} -> ${detail.after || '-'}`).join(' | ')
    ]);
    const csv = [header, ...lines].map((row) => row.map((value) => `"${String(value || '').replaceAll('"', '""')}"`).join(';')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'historico-comercial.csv';
    link.click();
    URL.revokeObjectURL(link.href);
  }

  function syncCommercialFilter() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    state.commercialFilters.status = refs.commercialFilterStatus?.value || '';
    state.commercialFilters.date_from = refs.commercialFilterDateFrom?.value || '';
    state.commercialFilters.date_to = refs.commercialFilterDateTo?.value || '';
    state.commercialFilters.actor_name = refs.commercialFilterActor?.value || '';
    renderCommercialSummary();
    renderCommercialAlerts();
    renderCommercialHistory();
  }

  async function saveCommercial(event) {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    event.preventDefault();
    if (!requirePermission('commercial:view')) return;
    const companyId = refs.commercialCompany?.value;
    const company = state.companies.find((item) => String(item.id) === String(companyId));
    if (!company) return;
    try {
      const values = formValues(refs.commercialForm);
      values.actor_user_id = state.user.id;
      values.name = company.name;
      values.legal_name = company.legal_name;
      values.cnpj = company.cnpj;
      values.logo_type = company.logo_type || '';
      values.addendum_enabled = refs.commercialForm.elements.addendum_enabled.checked ? 1 : 0;
      values.monthly_value = Number(company.monthly_value || 0);
      await globalThis.__EPI_COMPANIES_API__.updateCompany(company.id, values);
      await loadBootstrap();
      fillCommercialForm(company.id);
    } catch (error) { alert(error.message); }
  }

  async function saveCommercialSettings(event) {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    event.preventDefault();
    if (state.user?.role !== 'master_admin') return;
    try {
      const form = refs.commercialSettingsForm;
      const startMax = Number(form.elements.start_max.value || 10);
      const businessMax = Number(form.elements.business_max.value || 25);
      const corporateMax = Number(form.elements.corporate_max.value || 100);
      const payload = {
        actor_user_id: state.user.id,
        unit_price: Number(form.elements.unit_price.value || 0),
        plans: {
          individual: { label: 'Individual', min_users: 1, max_users: Number(form.elements.individual_max.value || 1) },
          start: { label: 'Start', min_users: 1, max_users: startMax },
          business: { label: 'Business', min_users: startMax + 1, max_users: businessMax },
          corporate: { label: 'Corporate', min_users: businessMax + 1, max_users: corporateMax },
          enterprise: { label: 'Enterprise', min_users: Number(form.elements.enterprise_min.value || 101), max_users: null }
        }
      };
      await globalThis.__EPI_COMMERCIAL_API__.saveCommercialSettings(payload);
      await loadBootstrap();
      fillCommercialSettingsForm();
      fillCommercialForm(refs.commercialCompany?.value);
    } catch (error) { alert(error.message); }
  }

  const exportsMap = {
    filteredCommercialCompanies,
    filteredCommercialLogs,
    fillCommercialSettingsForm,
    refreshCommercialPreview,
    fillCommercialForm,
    toggleCommercialStatus,
    renderCommercialStats,
    renderCommercialSummary,
    renderCommercialAlerts,
    renderCommercialHistory,
    renderCommercialExpiring,
    populateCommercialActors,
    exportCommercialExcel,
    formatCommercialFiltersLabel,
    printCommercialHistory,
    exportCommercialHistory,
    syncCommercialFilter,
    saveCommercial,
    saveCommercialSettings
  };

  // Só as síncronas eram globais no app.js; as assíncronas seguem fora de globalThis.
  for (const name of [
    'filteredCommercialCompanies',
    'filteredCommercialLogs',
    'fillCommercialSettingsForm',
    'refreshCommercialPreview',
    'fillCommercialForm',
    'renderCommercialStats',
    'renderCommercialSummary',
    'renderCommercialAlerts',
    'renderCommercialHistory',
    'renderCommercialExpiring',
    'populateCommercialActors',
    'exportCommercialExcel',
    'formatCommercialFiltersLabel',
    'printCommercialHistory',
    'exportCommercialHistory',
    'syncCommercialFilter'
  ]) {
    globalThis[name] = exportsMap[name];
  }
  const contract = globalThis.__EPI_COMMERCIAL_CONTRACT_VIEW__;
  globalThis.__EPI_COMMERCIAL_VIEW__ = Object.freeze({
    filteredCommercialCompanies: exportsMap.filteredCommercialCompanies,
    filteredCommercialLogs: exportsMap.filteredCommercialLogs,
    fillCommercialSettingsForm: exportsMap.fillCommercialSettingsForm,
    refreshCommercialPreview: exportsMap.refreshCommercialPreview,
    fillCommercialForm: exportsMap.fillCommercialForm,
    contractStatusLabel: contract.contractStatusLabel,
    renderCommercialContractPanel: contract.renderCommercialContractPanel,
    resetCommercialContractForm: contract.resetCommercialContractForm,
    loadCommercialContract: contract.loadCommercialContract,
    buildCommercialContractPayload: contract.buildCommercialContractPayload,
    toggleCommercialStatus: exportsMap.toggleCommercialStatus,
    renderCommercialStats: exportsMap.renderCommercialStats,
    renderCommercialSummary: exportsMap.renderCommercialSummary,
    renderCommercialAlerts: exportsMap.renderCommercialAlerts,
    renderCommercialHistory: exportsMap.renderCommercialHistory,
    renderCommercialExpiring: exportsMap.renderCommercialExpiring,
    populateCommercialActors: exportsMap.populateCommercialActors,
    exportCommercialExcel: exportsMap.exportCommercialExcel,
    formatCommercialFiltersLabel: exportsMap.formatCommercialFiltersLabel,
    printCommercialHistory: exportsMap.printCommercialHistory,
    downloadCommercialContractPdf: contract.downloadCommercialContractPdf,
    saveCommercialContractDraft: contract.saveCommercialContractDraft,
    generateCommercialContract: contract.generateCommercialContract,
    viewGeneratedCommercialContract: contract.viewGeneratedCommercialContract,
    downloadGeneratedCommercialContract: contract.downloadGeneratedCommercialContract,
    signCommercialContractAction: contract.signCommercialContractAction,
    uploadSignedCommercialContract: contract.uploadSignedCommercialContract,
    sendCommercialContractByEmail: contract.sendCommercialContractByEmail,
    exportCommercialHistory: exportsMap.exportCommercialHistory,
    syncCommercialFilter: exportsMap.syncCommercialFilter,
    saveCommercial: exportsMap.saveCommercial,
    saveCommercialContractManagement: contract.saveCommercialContractManagement,
    saveCommercialSettings: exportsMap.saveCommercialSettings
  });
})();
