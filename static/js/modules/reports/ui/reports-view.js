'use strict';
/* global tr, hasPermission, requirePermission, recordOptionalBootstrapSectionSkipped, isOperationalProfile,
   filterByUserCompany, formatUnitOption, syncReportLegalEntityOptions, formatDate, formatDateTime, renderBadge --
   globais do app.js e de views/{view,ui}-helpers.js, resolvidos na chamada (ver abaixo) */

// UI: Relatórios — filtros, resumo, arquivo de fichas e PDF
// (Refatoração UBX-V3, Etapa 4 — extraído de static/app.js).
//
// Camada UI: lê o formulário, desenha o resumo e a tabela do arquivo, abre o
// PDF. Validação dos filtros → modules/reports/business/report-filters.js;
// endpoints → modules/reports/integrations/reports-api.js.
//
// Estado e refs: os MESMOS objetos do app.js (`state` e `refs` são `const` no
// app.js, publicados como globalThis.__EPI_APP_STATE__ / __EPI_REFS__ e nunca
// reatribuídos), lidos na chamada. Os demais helpers (hasPermission,
// requirePermission, recordOptionalBootstrapSectionSkipped, isOperationalProfile,
// filterByUserCompany, formatUnitOption, syncReportLegalEntityOptions, formatDate,
// formatDateTime, reportNonCriticalError, tr) continuam globais do app.js e das
// views e são resolvidos na chamada, como antes. RBAC: as checagens de
// permissão são as originais; a autorização efetiva é do backend.
//
// renderReports e loadArchiveReports são `async function`: no app.js eram de
// bloco (sem Annex B) e só o próprio app.js as chamava; agora são publicadas
// em globalThis e o app.js chega a elas pelo nome global.
(function () {
  if (globalThis.__EPI_MODULE_REPORTS_UI_LOADED__) { return; }
  globalThis.__EPI_MODULE_REPORTS_UI_LOADED__ = true;

  function reportsBusiness() { return globalThis.__EPI_REPORTS_BUSINESS__; }
  function reportsApi() { return globalThis.__EPI_REPORTS_API__; }

  function syncReportOptions() {
    const state = globalThis.__EPI_APP_STATE__;
    syncReportLegalEntityOptions();
    const companyField = document.getElementById('report-company');
    const unitField = document.getElementById('report-unit');
    const employeeField = document.getElementById('report-employee');
    const unitHint = document.getElementById('report-unit-hint');
    if (!companyField || !unitField || !employeeField) {return;}
    const lockByOperationalProfile = isOperationalProfile();
    const operationalUnitId = String(state.user?.operational_unit_id || '').trim();
    if (lockByOperationalProfile && state.user?.company_id) {
      companyField.value = String(state.user.company_id);
    }
    const companyId = companyField.value || state.user?.company_id || '';
    let units = filterByUserCompany(state.units).filter((item) => !companyId || String(item.company_id) === String(companyId));
    if (lockByOperationalProfile && !operationalUnitId) {units = [];}
    if (lockByOperationalProfile && operationalUnitId) {
      units = units.filter((item) => String(item.id) === operationalUnitId);
    }
    const previousUnit = String(unitField.value || '');
    unitField.innerHTML = `${lockByOperationalProfile ? '' : `<option value="">${tr('employee.filterAllUnits', 'Todas')}</option>`}${units.map(formatUnitOption).join('')}`;
    if (!units.length) {
      unitField.innerHTML = '<option value="" data-i18n="employee.noActiveOperationalUnit">Sem unidade operacional ativa</option>';
      unitField.value = '';
    } else if (lockByOperationalProfile) {
      unitField.value = String(units[0].id);
    } else if (previousUnit && units.some((item) => String(item.id) === previousUnit)) {
      unitField.value = previousUnit;
    }
    companyField.disabled = lockByOperationalProfile;
    unitField.disabled = lockByOperationalProfile;
    if (unitHint) {unitHint.style.display = lockByOperationalProfile ? 'block' : 'none';}
    const selectedUnitId = String(unitField.value || '');
    const employees = filterByUserCompany(state.employees).filter((item) => {
      if (companyId && String(item.company_id) !== String(companyId)) {return false;}
      if (!selectedUnitId) {return true;}
      const employeeUnitId = String(item.current_unit_id || item.unit_id || '');
      return employeeUnitId === selectedUnitId;
    });
    const previousEmployee = String(employeeField.value || '');
    employeeField.innerHTML = `<option value="">${tr('employee.allEmployees', 'Todos os colaboradores')}</option>` + employees.map((item) => `<option value="${item.id}">${item.employee_id_code} - ${item.name}</option>`).join('');
    if (previousEmployee && employees.some((item) => String(item.id) === previousEmployee)) {
      employeeField.value = previousEmployee;
    } else {
      employeeField.value = '';
    }
  }

  function collectReportFilters() {
    const reportForm = document.getElementById('report-filter-form');
    // Leitura do formulário (UI); validação e limpeza na camada de negócio, na
    // mesma ordem de campos e com as mesmas mensagens de antes.
    return reportsBusiness().normalizeReportFilterValues({
      company_id: reportForm?.querySelector('#report-company')?.value,
      legal_entity_id: reportForm?.querySelector('#report-legal-entity')?.value,
      unit_id: reportForm?.querySelector('#report-unit')?.value,
      employee_id: reportForm?.querySelector('#report-employee')?.value,
      sector: reportForm?.querySelector('#report-sector')?.value,
      tipo_vinculo: reportForm?.querySelector('#report-tipo-vinculo')?.value,
      epi_id: reportForm?.querySelector('#report-epi')?.value,
      status: reportForm?.querySelector('#report-ficha-status')?.value,
      start_date: reportForm?.querySelector('input[name="start_date"]')?.value,
      end_date: reportForm?.querySelector('input[name="end_date"]')?.value
    });
  }

  async function renderReports(filters = null) {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    if (!hasPermission('reports:view')) {
      recordOptionalBootstrapSectionSkipped('reports', 'missing_permission', { permission: 'reports:view' });
      return;
    }
    const normalizedFilters = filters || collectReportFilters();
    const params = new URLSearchParams({ ...normalizedFilters, actor_user_id: state.user.id });
    try {
      state.reports = await reportsApi().fetchReports(params);
    } catch (error) {
      if (Number(error?.status || 0) === 403) {
        recordOptionalBootstrapSectionSkipped('reports', 'forbidden', { status: 403, permission: 'reports:view' });
        return;
      }
      reportNonCriticalError('[renderReports] falha ao carregar relatório', error);
      if (refs.reportSummary) {refs.reportSummary.innerHTML = '<div class="summary-item hint">Não foi possível carregar os relatórios agora. Tente novamente.</div>';}
      return;
    }
    refs.reportSummary.innerHTML = `<div class="summary-item"><strong>${tr('delivery.list', 'Entregas')}:</strong> ${state.reports.deliveries.length}</div><div class="summary-item"><strong>${tr('report.totalDelivered', 'Total entregue')}:</strong> ${state.reports.total_quantity}</div>`;
    refs.reportUnits.innerHTML = Object.entries(state.reports.by_unit).map((item) => `<div class="report-row"><strong>${item[0]}</strong> ${item[1]}</div>`).join('') || `<div class="summary-item">${tr('report.noData', 'Sem dados.')}</div>`;
    refs.reportSectors.innerHTML = Object.entries(state.reports.by_sector).map((item) => `<div class="report-row"><strong>${item[0]}</strong> ${item[1]}</div>`).join('') || `<div class="summary-item">${tr('report.noData', 'Sem dados.')}</div>`;
    const reportTipoVinculoEl = document.getElementById('report-tipo-vinculo-summary');
    if (reportTipoVinculoEl) {
      reportTipoVinculoEl.innerHTML = Object.entries(state.reports.by_tipo_vinculo || {}).map((item) => `<div class="report-row"><strong>${item[0]}</strong> ${item[1]}</div>`).join('') || `<div class="summary-item">${tr('report.noData', 'Sem dados.')}</div>`;
    }
    if (!refs.reportEmployeeFichas) {return;}
    const employeeFichas = state.reports.employee_fichas || [];
    refs.reportEmployeeFichas.innerHTML = employeeFichas.map((item) => {
      return `<div class="summary-item"><strong>${item.employee_name} (${item.employee_id_code})</strong><div>${tr('report.period', 'Período')}: ${formatDate(item.period_start)} a ${formatDate(item.period_end)} | ${tr('delivery.status', 'Status')}: ${item.status}</div><div>${tr('unit.title', 'Unidade')}: ${item.unit_name || '-'} | ${tr('report.items', 'Itens')}: ${item.total_items} | ${tr('report.totalQuantity', 'Quantidade total')}: ${item.total_quantity}</div></div>`;
    }).join('') || `<div class="summary-item">${tr('report.selectEmployeeRecords', 'Selecione um colaborador para visualizar as fichas de EPI.')}</div>`;
    await loadArchiveReports(reportsBusiness().archiveFiltersFromReportFilters(normalizedFilters));
  }

  function retentionStatusBadge(status) {
    const normalized = String(status || 'archived').toLowerCase();
    if (normalized === 'expired') {return renderBadge('status', 'warning', 'expirada');}
    if (normalized === 'purged') {return renderBadge('status', 'inactive', 'purgada');}
    return renderBadge('status', 'active', 'arquivada');
  }

  function renderArchiveTable() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    if (!refs.reportArchiveTable) {return;}
    refs.reportArchiveTable.innerHTML = (state.reportArchiveItems || []).map((item) => `
    <tr>
      <td>${formatDateTime(item.generated_at)}</td>
      <td>${item.employee_name || '-'} (${item.employee_id_code || '-'})</td>
      <td>${item.company_name || '-'}</td>
      <td>${item.unit_name || '-'}</td>
      <td>${retentionStatusBadge(item.status)}</td>
      <td><code>${String(item.html_sha256 || '').slice(0, 12)}...</code></td>
      <td>
        <div class="action-group">
          <button class="ghost" data-archive-view="${item.id}" data-i18n="ui.compras.visualizar_1acb4b">Visualizar</button>
          <button class="ghost" data-archive-print="${item.id}" data-i18n="records.print">Imprimir</button>
          <button class="ghost" data-archive-export="${item.id}" data-i18n="export">Exportar</button>
        </div>
      </td>
    </tr>
  `).join('') || globalThis.dsTableState({ colspan: 7, message: 'Sem fichas arquivadas para os filtros informados.' });
    if (refs.reportArchivePagination) {
      refs.reportArchivePagination.textContent = `Registros: ${state.reportArchiveTotal} | Página ${state.reportArchivePage}`;
    }
  }

  async function loadArchiveReports(filters = {}) {
    const state = globalThis.__EPI_APP_STATE__;
    if (!hasPermission('reports:view')) {
      recordOptionalBootstrapSectionSkipped('report_archive', 'missing_permission', { permission: 'reports:view' });
      return;
    }
    const params = new URLSearchParams({
      ...filters,
      page: String(state.reportArchivePage || 1),
      page_size: String(state.reportArchivePageSize || 50),
      actor_user_id: String(state.user?.id || '')
    });
    let payload;
    try {
      payload = await reportsApi().fetchFichaArchive(params);
    } catch (error) {
      if (Number(error?.status || 0) === 403) {
        recordOptionalBootstrapSectionSkipped('report_archive', 'forbidden', { status: 403, permission: 'reports:view' });
        return;
      }
      reportNonCriticalError('[loadArchiveReports] falha ao carregar arquivo', error);
      state.reportArchiveItems = [];
      state.reportArchiveTotal = 0;
      renderArchiveTable();
      return;
    }
    state.reportArchiveItems = payload.items || [];
    state.reportArchiveTotal = Number(payload.total || 0);
    state.fichaRetentionPolicy = payload.retention_policy || state.fichaRetentionPolicy;
    renderArchiveTable();
  }

  function exportReportPdf() {
    const state = globalThis.__EPI_APP_STATE__;
    if (!requirePermission('reports:view')) {return;}
    let filters;
    try {
      filters = collectReportFilters();
    } catch (error) {
      alert(error?.message || 'Filtros inválidos.');
      return;
    }
    const params = new URLSearchParams({ actor_user_id: state.user?.id || '', ...filters });
    globalThis.open(reportsApi().reportPdfUrl(params), '_blank');
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  const reportsViewExports = {
    syncReportOptions,
    collectReportFilters,
    renderReports,
    retentionStatusBadge,
    renderArchiveTable,
    loadArchiveReports,
    exportReportPdf
  };

  for (const [name, fn] of Object.entries(reportsViewExports)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_REPORTS_VIEW__ = Object.freeze({ ...reportsViewExports });
})();
