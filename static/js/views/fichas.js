'use strict';

(function () {
  if (globalThis.__EPI_MODULE_FICHAS_LOADED__) { return; }
  globalThis.__EPI_MODULE_FICHAS_LOADED__ = true;

  // ── Local wrappers ─────────────────────────────────────────────────────────
  function getState() { return globalThis.__EPI_APP_STATE__ || {}; }
  function getRefs() { return globalThis.__EPI_REFS__ || {}; }
  function api(path, opts) {
    if (typeof globalThis.api === 'function') { return globalThis.api(path, opts); }
    const options = opts || {};
    if (!options.headers) { options.headers = {}; }
    return fetch(path, options).then(async (r) => {
      const data = await r.json().catch(() => ({}));
      if (!r.ok) { throw new Error(data?.error || data?.message || `HTTP ${r.status}`); }
      return data;
    });
  }
  function renderBadge(type, value, label) { return globalThis.renderBadge?.(type, value, label) ?? ''; }
  function hasPermission(perm) { return globalThis.currentUserHasPermission?.(perm) ?? false; }
  function formatDate(d) { return globalThis.formatDate?.(d) ?? (d ?? ''); }
  function formatDateTime(d) { return globalThis.formatDateTime?.(d) ?? (d ?? ''); }
  function tr(key, fallback) { return globalThis.tr?.(key, fallback) ?? fallback ?? key; }
  function escapeHtml(s) { return globalThis.escapeHtml?.(s) ?? String(s ?? ''); }
  function filterByUserCompany(items) { return globalThis.filterByUserCompany?.(items) ?? items; }
  function applyFichaEmployeeFilters(items) { return globalThis.applyFichaEmployeeFilters?.(items) ?? items; }
  function companyLogoMarkup(company, cls) { return globalThis.companyLogoMarkup?.(company, cls) ?? ''; }
  function hasConfigurationAccess() { return globalThis.hasConfigurationAccess?.() ?? false; }
  function canViewConfiguration() { return globalThis.canViewConfiguration?.() ?? false; }
  async function apiOptional(path, opts) {
    if (typeof globalThis.apiOptional === 'function') { return globalThis.apiOptional(path, opts); }
    try {
      const payload = await api(path, opts);
      return { ok: true, payload };
    } catch (error) {
      return { ok: false, error };
    }
  }

  // ── Implementations ────────────────────────────────────────────────────────

  function renderFicha() {
    const state = getState();
    const refs = getRefs();
    const filteredEmployees = applyFichaEmployeeFilters(filterByUserCompany(state.employees));
    if (refs.fichaEmployee) {
      const previous = String(refs.fichaEmployee.value || '');
      refs.fichaEmployee.innerHTML = filteredEmployees.map((item) => `<option value="${item.id}">${item.employee_id_code} - ${item.name}</option>`).join('');
      if (previous && filteredEmployees.some((item) => String(item.id) === previous)) { refs.fichaEmployee.value = previous; }
    }
    const employeeId = refs.fichaEmployee.value || filteredEmployees[0]?.id;
    const employee = filteredEmployees.find((item) => String(item.id) === String(employeeId));
    if (!employee) { refs.fichaView.innerHTML = `<div class="summary-item">${tr('employee.noEmployeesAvailable', 'Nenhum colaborador disponível.')}</div>`; return; }
    refs.fichaEmployee.value = employee.id;
    const periods = (state.fichasPeriods || [])
      .filter((item) => String(item.employee_id) === String(employee.id))
      .sort((a, b) => String(b.period_start || '').localeCompare(String(a.period_start || '')));
    const canFinalizePeriod = hasPermission('deliveries:create');
    const fichaStatusLabel = (statusValue) => {
      const normalized = String(statusValue || '').trim().toLowerCase();
      if (normalized === 'pending_signature') { return tr('records.statusPendingSignature', 'Aguardando assinatura'); }
      if (normalized === 'closed') { return tr('portal.periodClosed', 'Fechado'); }
      if (normalized === 'signed') { return tr('portal.statusSigned', 'Assinado'); }
      return statusValue || 'open';
    };
    const periodsHtml = periods.map((item) => {
      const pendingItems = Number(item.pending_items || 0);
      const signed = String(item.batch_signature_at || '').trim() !== '';
      const isOpen = String(item.status || '').toLowerCase() === 'open';
      const isPendingSignature = String(item.status || '').toLowerCase() === 'pending_signature';
      const finalizeButton = canFinalizePeriod && (isOpen || (isPendingSignature && !signed)) && Number(item.total_items || 0) > 0
        ? `<div class="action-group">
            <select id="ficha-channel-${item.id}" name="ficha_channel_${item.id}" data-ficha-channel="${item.id}" autocomplete="off">
              <option value="whatsapp">WhatsApp</option>
              <option value="email">E-mail</option>
            </select>
            <button class="ghost" type="button" data-ficha-finalize="${item.id}">${tr('records.finalizePeriod', 'Finalizar período')}</button>
          </div>`
        : '';
      return `<div class="summary-item">
      <strong>${tr('report.period', 'Período')}: ${formatDate(item.period_start)} a ${formatDate(item.period_end)}</strong>
      <div>${tr('delivery.status', 'Status')}: ${fichaStatusLabel(item.status)} | ${tr('unit.title', 'Unidade')}: ${item.unit_name || '-'}</div>
      <div>${tr('records.itemsInPeriod', 'Itens no período')}: ${Number(item.total_items || 0)} | ${tr('records.pendingSignaturesCount', 'Pendentes de assinatura')}: ${pendingItems}</div>
      <div>${tr('records.batchSignature', 'Assinatura em lote')}: ${signed ? `${tr('common.yes', 'Sim')} (${formatDateTime(item.batch_signature_at)})` : tr('records.pendingSignatureHint', 'Pendente (pode assinar localmente ou no link do colaborador)')}</div>
      ${finalizeButton}
    </div>`;
    }).join('');
    refs.fichaView.innerHTML = `<div class="summary-item"><strong>${tr('company.title', 'Empresa')}:</strong> ${employee.company_name} (${employee.company_cnpj})</div><div class="summary-item ficha-logo"><strong>${tr('company.logo', 'Logotipo')}:</strong> ${companyLogoMarkup({ name: employee.company_name, logo_type: employee.logo_type }, 'company-logo company-logo-sm')}</div><div class="summary-item"><strong>${tr('employee.singleTitle', 'Colaborador')}:</strong> ${employee.name}</div><div class="summary-item"><strong>ID:</strong> ${employee.employee_id_code}</div><div class="summary-item"><strong>${tr('employee.sector', 'Setor')}:</strong> ${employee.sector}</div><div class="summary-item"><strong>${tr('employee.function', 'Função')}:</strong> ${employee.role_name || employee.position || '-'}</div>${periodsHtml || `<div class="summary-item">${tr('records.noPeriodsForEmployee', 'Sem períodos de ficha para este colaborador.')}</div>`}`;
  }

  function fichaAuditActionBadge(action) {
    const map = {
      view: ['status', 'active', 'visualizou'],
      print: ['status', 'warning', 'imprimiu'],
      denied: ['status', 'inactive', 'negado'],
      snapshot_view: ['status', 'active', 'snapshot'],
      snapshot_print: ['status', 'warning', 'snapshot print'],
      snapshot_export: ['status', 'active', 'snapshot export']
    };
    const [kind, tone, label] = map[action] || ['status', 'inactive', action || '-'];
    return renderBadge(kind, tone, label);
  }

  function renderFichaAuditLogs() {
    const state = getState();
    const refs = getRefs();
    if (!refs.fichaAuditTable) { return; }
    refs.fichaAuditTable.innerHTML = (state.fichaAuditLogs || []).map((item) => `
    <tr>
      <td>${formatDateTime(item.accessed_at)}</td>
      <td>${item.actor_name || '-'}</td>
      <td>${item.employee_name || '-'}</td>
      <td>${fichaAuditActionBadge(item.action)}</td>
      <td>${item.unit_name || '-'}</td>
      <td>${item.ip_address || '-'}</td>
      <td>${item.user_agent || '-'}</td>
    </tr>
  `).join('') || '<tr><td colspan="7">Sem logs de auditoria de ficha.</td></tr>';
  }

  function renderFichaAuditUnavailable(message = 'Histórico temporariamente indisponível. Tente novamente.') {
    const refs = getRefs();
    if (!refs.fichaAuditTable) { return; }
    refs.fichaAuditTable.innerHTML = `<tr><td colspan="7">${escapeHtml(message)}</td></tr>`;
  }

  async function loadFichaAuditLogs() {
    const state = getState();
    const refs = getRefs();
    if (!hasConfigurationAccess()) { return; }
    if (!canViewConfiguration()) { return; }
    if (refs.fichaAuditTable) {
      refs.fichaAuditTable.innerHTML = '<tr><td colspan="7">Carregando histórico de auditoria...</td></tr>';
    }
    const params = new URLSearchParams();
    if (refs.fichaAuditEmployee?.value) { params.set('employee_id', refs.fichaAuditEmployee.value); }
    if (refs.fichaAuditManager?.value) { params.set('actor_user_id', refs.fichaAuditManager.value); }
    if (refs.fichaAuditAction?.value) { params.set('action', refs.fichaAuditAction.value); }
    if (refs.fichaAuditDateFrom?.value) { params.set('date_from', refs.fichaAuditDateFrom.value); }
    if (refs.fichaAuditDateTo?.value) { params.set('date_to', refs.fichaAuditDateTo.value); }
    params.set('actor_user_id', state.user?.id || '');
    const response = await apiOptional(`/api/ficha-epi-audit?${params.toString()}`);
    if (!response.ok) {
      state.fichaAuditLogs = [];
      renderFichaAuditUnavailable('Histórico temporariamente indisponível. Tente novamente.');
      return;
    }
    state.fichaAuditLogs = response.payload?.items || [];
    renderFichaAuditLogs();
  }

  // ── Exports ────────────────────────────────────────────────────────────────
  const moduleExports = {
    renderFicha,
    fichaAuditActionBadge,
    renderFichaAuditLogs,
    renderFichaAuditUnavailable,
    loadFichaAuditLogs
  };

  for (const [name, fn] of Object.entries(moduleExports)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_FICHAS__ = Object.freeze({ ...moduleExports });
})();
