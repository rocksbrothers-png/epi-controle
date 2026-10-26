'use strict';
/* global tr, populateSearchSelect, unitsForSearchByCompany, renderTables, openAndPrintPopup, qrCodeImageUrl,
   filterByUserCompany, allocationTypeLabel, employmentTypeLabel, isContractedVinculoJs, unitTypeLabel,
   legalEntitiesForCompany, legalEntityHelpers, legalEntityOptionsHtml, setFormSubmitLabel, showView --
   globais do app.js e de shared/ui, resolvidos na chamada (ver abaixo) */

// UI: Colaboradores (Refatoração UBX-V4, Etapa B1 — extraído de static/app.js).
//
// Filtros da listagem (cadastro e operação), linhas da tabela, seleção em lote
// e exportação CSV, edição (com o CNPJ travado), unidade/CNPJ do formulário,
// "Empresa de Origem" e link/QR de acesso externo.
// Regras puras em ../business/employee-rules.js; HTTP em
// ../integrations/employees-api.js. Estado e refs: os MESMOS objetos do
// app.js, lidos na chamada. Permissões: os botões de ação dependem do
// `canManageRecords` que o app.js passa (fallback visual; quem autoriza é o
// backend). isContractedVinculoJs continua no app.js (fica com Terceirizados).
//
// employeesBulk: a seleção em lote é criada AQUI, no carregamento — este
// script carrega depois de views/ui-helpers.js (dsCreateBulkSelection) e antes
// do app.js, que lê a MESMA instância por __EPI_EMPLOYEES_VIEW__.employeesBulk.
// printEmployeePortalLink e handleEmployeeFormSuccess eram `async function`
// de bloco no app.js; agora são globais.
(function () {
  if (globalThis.__EPI_MODULE_EMPLOYEES_UI_LOADED__) { return; }
  globalThis.__EPI_MODULE_EMPLOYEES_UI_LOADED__ = true;

  function employeesBusiness() { return globalThis.__EPI_EMPLOYEES_BUSINESS__; }
  function employeesApi() { return globalThis.__EPI_EMPLOYEES_API__; }

  // Seleção em lote da listagem de Colaboradores (componente reutilizável do DS).
  const employeesBulk = globalThis.dsCreateBulkSelection ? globalThis.dsCreateBulkSelection() : null;

  function buildEmployeeAccessLink(token) {
    const normalizedToken = String(token || '').trim();
    if (!normalizedToken) {return '';}
    return `${globalThis.location.origin}/?employee_token=${encodeURIComponent(normalizedToken)}`;
  }

  function syncEmployeesSearchFilters(source = 'employees') {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    const isOps = source === 'ops';
    const filters = isOps ? state.employeesOpsFilters : state.employeesFilters;
    const companyField = isOps ? refs.employeesOpsFilterCompany : refs.employeesFilterCompany;
    const unitField = isOps ? refs.employeesOpsFilterUnit : refs.employeesFilterUnit;
    const searchField = isOps ? refs.employeesOpsFilterSearch : refs.employeesFilterSearch;
    const sectorField = isOps ? refs.employeesOpsFilterSector : refs.employeesFilterSector;
    const roleField = isOps ? refs.employeesOpsFilterRole : refs.employeesFilterRole;
    filters.company_id = String(companyField?.value || '').trim();
    filters.unit_id = String(unitField?.value || '').trim();
    filters.search = String(searchField?.value || '').trim().toLowerCase();
    filters.sector = String(sectorField?.value || '').trim().toLowerCase();
    filters.role_name = String(roleField?.value || '').trim().toLowerCase();
    if (isOps) {populateSearchSelect(refs.employeesOpsFilterUnit, unitsForSearchByCompany(filters.company_id), (item) => item.name, filters.unit_id);}
    else {populateSearchSelect(refs.employeesFilterUnit, unitsForSearchByCompany(filters.company_id), (item) => item.name, filters.unit_id);}
    filters.unit_id = String(unitField?.value || '').trim();
    if (!isOps && state.pagination) {state.pagination.employees = 1;} // volta à 1ª página ao filtrar
    renderTables();
  }

  function addEmployeeButtons(actions, target) {
    if (target.role === 'employee' && target.employee_access_token) {
      actions.push(`<button class="ghost" data-user-employee-qr="${target.id}">${tr('user.externalQr', 'QR Acesso Externo')}</button>`);
    }
  }

  function printEmployeeAccessQr(userId) {
    const state = globalThis.__EPI_APP_STATE__;
    const target = state.users.find((item) => String(item.id) === String(userId));
    if (!target?.employee_access_token) {return alert('Funcionário sem token externo.');}
    const accessLink = buildEmployeeAccessLink(target.employee_access_token);
    const html = `<!doctype html><html><head><meta charset="utf-8"><title>Acesso Funcionário"></head><body><p><a href="${accessLink}">${accessLink}</a></p></body></html>`;
    if (!openAndPrintPopup(html, 'width=520,height=700')) {return alert('Não tem acesso.');}
  }

  async function printEmployeePortalLink(employeeId) {
    const state = globalThis.__EPI_APP_STATE__;
    try {
      const payload = await employeesApi().createEmployeePortalLink(state.user.id, employeeId);
      const employee = state.employees.find((item) => String(item.id) === String(employeeId));
      const accessLink = payload.access_link || payload.qr_code_value || buildEmployeeAccessLink(payload.token);
      const html = `<!doctype html><html><head><meta charset="utf-8"><title>Link do Colaborador</title><style>body{font-family:Segoe UI,Arial,sans-serif;padding:22px;text-align:center}img{width:240px;height:240px;margin:18px auto;display:block}a{word-break:break-all;color:#96401c}</style></head><body><h2>${employee?.name || 'Colaborador'}</h2><p>Link de acesso externo</p><img src="${qrCodeImageUrl(accessLink)}" alt="Link acesso colaborador"><p><a href="${accessLink}">${accessLink}</a></p></body></html>`;
      if (!openAndPrintPopup(html, 'width=520,height=700')) {return alert('Não tem acesso.');}
    } catch (error) {
      alert(error.message);
    }
  }

  function applyEmployeesFilters(items, source = 'employees') {
    const state = globalThis.__EPI_APP_STATE__;
    const filters = source === 'ops' ? state.employeesOpsFilters : state.employeesFilters;
    return employeesBusiness().filterEmployees(items, filters);
  }

  function buildEmployeeRow(item, canManageRecords) {
    const actions = canManageRecords ? `<div class="action-group"><button class="ghost" data-employee-edit="${item.id}">${tr('edit', 'Editar')}</button><button class="ghost" data-employee-archive="${item.id}">${tr('employee.archive', 'Arquivar')}</button></div>` : '-';
    const allocation = allocationTypeLabel(item.unit_allocation_type);
    const preferredLabel = String(item.preferred_contact_channel || '').toLowerCase() === 'email' ? 'E-mail' : 'WhatsApp';
    const contact = [item.whatsapp ? `WhatsApp: ${item.whatsapp}` : '', item.email ? `E-mail: ${item.email}` : '', `${tr('employee.preferredContactLabel', 'Preferido')}: ${preferredLabel}`].filter(Boolean).join('<br>') || '-';
    const tipoVinculoRaw = item.tipo_vinculo || 'CLT';
    const tipoVinculo = employmentTypeLabel(tipoVinculoRaw);
    const empresaOrigem = isContractedVinculoJs(tipoVinculoRaw) && item.empresa_origem ? `<br><small>${item.empresa_origem}</small>` : '';
    const checkCell = employeesBulk ? `<td class="ds-bulk-cell"><input type="checkbox" class="ds-bulk-checkbox" data-emp-check="${item.id}" aria-label="Selecionar ${item.name}"${employeesBulk.has(item.id) ? ' checked' : ''}></td>` : '';
    return `<tr>${checkCell}<td>${item.company_name}</td><td>${item.employee_id_code}</td><td>${item.name}</td><td>${contact}</td><td>${item.sector}</td><td>${item.role_name}</td><td>${tipoVinculo}${empresaOrigem}</td><td>${item.current_unit_name || item.unit_name}</td><td>${allocation}</td><td>-</td><td>${actions}</td></tr>`;
  }

  function buildEmployeeOpsRow(item) {
    const allocation = allocationTypeLabel(item.unit_allocation_type);
    const tipoVinculoRaw = item.tipo_vinculo || 'CLT';
    const tipoVinculo = employmentTypeLabel(tipoVinculoRaw);
    const empresaOrigem = isContractedVinculoJs(tipoVinculoRaw) && item.empresa_origem ? `<br><small>${item.empresa_origem}</small>` : '';
    return `<tr><td>${item.company_name}</td><td>${item.employee_id_code}</td><td>${item.name}</td><td>${item.sector}</td><td>${item.role_name}</td><td>${tipoVinculo}${empresaOrigem}</td><td>${item.current_unit_name || item.unit_name}</td><td>${allocation}</td><td><button class="ghost" style="font-size:12px;padding:4px 10px;" data-ops-select-employee="${item.id}">${tr('employee.select', 'Selecionar')}</button></td></tr>`;
  }

  function currentEmployeesBulkScope() {
    const state = globalThis.__EPI_APP_STATE__;
    // Base atual (empresa + filtros) — a seleção e o "selecionar todos da página"
    // operam sobre o que está visível, respeitando os filtros ativos.
    return applyEmployeesFilters(filterByUserCompany(state.employees), 'employees');
  }

  function exportSelectedEmployeesCsv() {
    if (!employeesBulk || employeesBulk.count() === 0) {return;}
    const ids = new Set(employeesBulk.ids().map(String));
    const rows = currentEmployeesBulkScope().filter((e) => ids.has(String(e.id)));
    if (!rows.length) {return;}
    const csv = employeesBusiness().employeesCsv(rows, employmentTypeLabel);
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'colaboradores-selecionados.csv';
    link.click();
    URL.revokeObjectURL(link.href);
  }

  function renderEmployeesBulkUi(pageIds) {
    const refs = globalThis.__EPI_REFS__;
    if (!employeesBulk || !refs.employeesBulkBar) {return;}
    refs.employeesBulkBar.innerHTML = globalThis.dsBulkBar(
      employeesBulk.count(),
      [{ id: 'export', label: tr('bulk.exportCsv', 'Exportar CSV'), variant: 'btn-primary' }],
      { labelPlural: tr('bulk.selectedPlural', 'selecionados'), labelSingular: tr('bulk.selectedSingular', 'selecionado'), clearLabel: tr('bulk.clear', 'Limpar seleção') }
    );
    if (refs.employeesSelectAll) {
      const st = employeesBulk.pageState(pageIds);
      refs.employeesSelectAll.checked = st === 'all';
      refs.employeesSelectAll.indeterminate = st === 'some';
    }
  }

  function syncEmpresaOrigemVisibility() {
    const tv = document.getElementById('employee-tipo-vinculo')?.value || 'CLT';
    const row = document.getElementById('employee-empresa-origem-row');
    if (row) {row.hidden = employeesBusiness().isOwnWorkforceVinculo(tv);}
  }

  function startEditEmployee(employeeId) {
    const state = globalThis.__EPI_APP_STATE__;
    const item = state.employees.find((employee) => String(employee.id) === String(employeeId));
    const form = document.getElementById('employee-form');
    if (!item || !form) {return;}
    form.elements.id.value = item.id;
    form.elements.company_id.value = item.company_id;
    syncEmployeeUnitOptions();
    form.elements.unit_id.value = item.unit_id || '';
    // CNPJ é o vínculo jurídico do contrato: imutável na edição comum. Mostramos
    // o valor atual, mas desabilitado — alterar exige o processo administrativo
    // auditado de transferência, e o backend ignora este campo no update.
    setEmployeeLegalEntityLock(item.legal_entity_id || '', true);
    form.elements.employee_id_code.value = item.employee_id_code || '';
    form.elements.cpf.value = item.cpf || '';
    form.elements.name.value = item.name || '';
    form.elements.email.value = item.email || '';
    form.elements.whatsapp.value = item.whatsapp || '';
    form.elements.preferred_contact_channel.value = item.preferred_contact_channel || 'whatsapp';
    form.elements.sector.value = item.sector || '';
    form.elements.role_name.value = item.role_name || '';
    form.elements.schedule_type.value = item.schedule_type || '14x14';
    form.elements.admission_date.value = item.admission_date || '';
    form.elements.tipo_vinculo.value = item.tipo_vinculo || 'CLT';
    form.elements.empresa_origem.value = item.empresa_origem || '';
    syncEmpresaOrigemVisibility();
    setFormSubmitLabel('employee-form', 'Atualizar colaborador');
    showView('colaboradores');
  }

  function syncEmployeeUnitOptions() {
    const state = globalThis.__EPI_APP_STATE__;
    const companyField = document.getElementById('employee-company');
    const unitField = document.getElementById('employee-unit');
    if (!companyField || !unitField) {return;}
    const companyId = companyField.value || state.user?.company_id || '';
    const units = filterByUserCompany(state.units).filter((item) => !companyId || String(item.company_id) === String(companyId));
    unitField.innerHTML = units.map((item) => `<option value="${item.id}">${item.name} - ${unitTypeLabel(item.unit_type)}</option>`).join('');
    if (units.length && !units.some((item) => String(item.id) === String(unitField.value))) {
      unitField.value = String(units[0].id);
    }
    // O CNPJ acompanha a empresa selecionada, então é resincronizado junto.
    syncEmployeeLegalEntityOptions();
  }

  function syncEmployeeLegalEntityOptions() {
    const state = globalThis.__EPI_APP_STATE__;
    const field = document.getElementById('employee-legal-entity');
    const wrapper = document.getElementById('employee-legal-entity-field');
    if (!field || !wrapper) {return;}
    const companyId = document.getElementById('employee-company')?.value || state.user?.company_id || '';
    const entities = legalEntitiesForCompany(companyId);
    const previous = field.value;
    const required = legalEntityHelpers().employeeLegalEntityRequired;
    const mandatory = required ? required(entities) : entities.length > 1;
    wrapper.hidden = entities.length === 0;
    field.required = mandatory;
    const placeholder = mandatory
      ? `<option value="">${tr('legalEntity.select', 'Selecione o CNPJ')}</option>`
      : `<option value="">${tr('legalEntity.auto', 'Automático (CNPJ único)')}</option>`;
    field.innerHTML = placeholder + legalEntityOptionsHtml(entities);
    if (previous && entities.some((item) => String(item.id) === String(previous))) {
      field.value = previous;
    }
  }

  function setEmployeeLegalEntityLock(legalEntityId, locked) {
    const field = document.getElementById('employee-legal-entity');
    if (!field) {return;}
    syncEmployeeLegalEntityOptions();
    if (legalEntityId) {field.value = String(legalEntityId);}
    field.disabled = Boolean(locked);
    if (locked) {field.required = false;}
  }

  async function handleEmployeeFormSuccess(accessLink) {
    try {
      await navigator.clipboard?.writeText(accessLink);
    } catch (error) {
      console.warn('[employee-form] Falha ao copiar link para area de transferencia:', error);
    }
    alert(`Colaborador cadastrado com sucesso.\nLink de acesso externo:\n${accessLink}`);
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  const employeesViewExports = {
    buildEmployeeAccessLink,
    syncEmployeesSearchFilters,
    addEmployeeButtons,
    printEmployeeAccessQr,
    printEmployeePortalLink,
    applyEmployeesFilters,
    buildEmployeeRow,
    buildEmployeeOpsRow,
    currentEmployeesBulkScope,
    exportSelectedEmployeesCsv,
    renderEmployeesBulkUi,
    syncEmpresaOrigemVisibility,
    startEditEmployee,
    syncEmployeeUnitOptions,
    syncEmployeeLegalEntityOptions,
    setEmployeeLegalEntityLock,
    handleEmployeeFormSuccess
  };

  for (const [name, fn] of Object.entries(employeesViewExports)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_EMPLOYEES_VIEW__ = Object.freeze({ ...employeesViewExports, employeesBulk });
})();
