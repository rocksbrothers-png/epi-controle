'use strict';
/* global tr, hasPermission, requirePermission, actorQuery, escapeHtml, unitTypeLabel,
   isOperationalProfile, filterByUserCompany, setFormSubmitLabel, showView, activateViewTab,
   outsourcedEmployeeLinkLabel, outsourcedCompaniesViewHelpers, loadBootstrap, archiveEntityRecord --
   globais do app.js, de shared/ui e de views/*, resolvidos na chamada (ver abaixo) */

// UI: Terceirizados e Prestadores — colaboradores (Refatoração UBX-V4, Etapa B2 —
// extraído de static/app.js).
//
// Seletores de empresa/Unidade do formulário, lista (derivada de
// state.employees), vínculo local por Unidade, edição (GET do item), filtros e
// relatório de headcount. Regras puras em js/views/outsourced-employees-view.js;
// HTTP em ../integrations/outsourced-api.js. archiveOutsourcedEmployee reusa
// archiveEntityRecord (modules/archival/ui/archival-view.js, UBX-V5 Etapa 1).
// isContractedVinculoJs (usado pela UI de Colaboradores) mora aqui com o
// fallback da lista de vínculos contratados.
(function () {
  if (globalThis.__EPI_MODULE_OUTSOURCED_EMPLOYEES_UI_LOADED__) { return; }
  globalThis.__EPI_MODULE_OUTSOURCED_EMPLOYEES_UI_LOADED__ = true;

  function outsourcedApi() { return globalThis.__EPI_OUTSOURCED_API__; }

  // ── Cadastro de Colaboradores simplificado (ADR-0002 §10.2) ─────────────────
  // Só terceirizado/prestador, nunca CLT (o backend recusa). Sem rota de
  // listagem própria — deriva de state.employees (já carregado pelo
  // bootstrap, `fetch_employees` inclui tipo_vinculo/outsourced_company_id),
  // mesma estratégia do app Flutter: filtro client-side, sem endpoint novo.

  // Rótulo do vínculo local. Traduz o valor que o BACKEND mandou — não decide
  // nada. Os quatro estados vêm de `local_unit_link_status` (ADR-0002 §13):
  // `null`/ausente = não se aplica; 'none' = aplicável e inexistente nesta
  // Unidade; 'active' = vinculado; 'inactive' = arquivado nesta Unidade.

  // Último recurso, para o caso de `js/views/outsourced-employees-view.js` não
  // carregar. A FONTE é aquele módulo (export `CONTRACTED_VINCULOS`); aqui só
  // existe para a tela não quebrar sem ele, e o teste de paridade cobre as duas.
  const CONTRACTED_VINCULOS_FALLBACK = ['Terceirizado', 'Prestador de Serviço', 'Temporário'];

  // "É mão de obra contratada?" — a mesma pergunta que `outsourcedEmployeesList`
  // faz, com a mesma fonte: o módulo de regras, e o fallback só se ele não
  // carregou. Existe porque `buildEmployeeRow`/`buildEmployeeOpsRow` decidiam por
  // `tipoVinculoRaw !== 'CLT'`, que classifica Menor Aprendiz, Praticante e
  // Estagiário como contratados. Inofensivo enquanto o backend zera
  // `empresa_origem` para mão de obra própria e o `&&` seguinte filtra — mas é o
  // idioma que o PR #214 baniu, e ele sobreviveu aqui porque o teste de paridade
  // procurava `tipo !==`, que não casa com `tipoVinculoRaw !==`.
  function isContractedVinculoJs(tipoVinculo) {
    const helpers = outsourcedEmployeesViewHelpers();
    if (helpers.isContractedVinculo) {return helpers.isContractedVinculo(tipoVinculo);}
    const contracted = helpers.CONTRACTED_VINCULOS || CONTRACTED_VINCULOS_FALLBACK;
    return contracted.includes(String(tipoVinculo || '').trim());
  }

  // Popula o seletor de empresa terceirizada/prestadora do Cadastro de
  // Colaboradores — depende de state.outsourcedCompanies, que (ao contrário de
  // state.companies/state.units) só chega quando a tela é aberta, então este
  // sync roda de novo a cada loadOutsourcedCompanies(), não em
  // bindDependentSelects() (que só cobre dados do bootstrap).
  function syncOutsourcedEmployeeCompanySelect() {
    const state = globalThis.__EPI_APP_STATE__;
    const field = document.getElementById('outsourced-employee-outsourced-company');
    if (!field) {return;}
    const previous = field.value;
    // Empresa arquivada NESTA Unidade não pode ser oferecida para novos
    // colaboradores — mesmo espelho do backend
    // (is_outsourced_company_available_to_unit, Problema 3 do pedido): some
    // do seletor assim que arquivada, volta assim que desarquivada. Some
    // sozinho quando o próprio state.outsourcedCompanies muda (toggleOutsourcedCompanyUnitLink
    // recarrega a lista), sem precisar de lógica extra aqui.
    const helpers = outsourcedCompaniesViewHelpers();
    const isArchivedInUnit = helpers.isArchivedInUnit || ((item) => String(item?.local_status || '') === 'inactive');
    const companies = filterByUserCompany(state.outsourcedCompanies || [])
      .filter((item) => !isArchivedInUnit(item));
    field.innerHTML = companies
      .map((item) => `<option value="${item.id}">${escapeHtml(item.trade_name || item.legal_name || '')}</option>`)
      .join('');
    if (previous && companies.some((item) => String(item.id) === previous)) {field.value = previous;}
  }

  // Administrador Local/Gestor de EPI (isOperationalProfile()) só operam
  // dentro da própria unidade operacional — o backend já força isso em
  // create/update_employee_outsourced_simplified
  // (ensure_actor_unit_scope_for_target), mas até esta correção o campo
  // aparecia como um seletor livre, deixando esses perfis escolherem outra
  // unidade na UI e só descobrirem o bloqueio depois de tentar salvar.
  // Mesmo padrão já usado em syncEpiUnitOptions/hint de Unidade nos filtros
  // de Ficha/Entregas: preenche com a própria unidade e desabilita o campo.
  function syncOutsourcedEmployeeUnitOptions() {
    const state = globalThis.__EPI_APP_STATE__;
    const companyField = document.getElementById('outsourced-employee-company');
    const unitField = document.getElementById('outsourced-employee-unit');
    const unitHint = document.getElementById('outsourced-employee-unit-hint');
    if (!companyField || !unitField) {return;}
    const companyId = companyField.value || state.user?.company_id || '';
    const units = filterByUserCompany(state.units).filter((item) => !companyId || String(item.company_id) === String(companyId));
    const lockByOperationalProfile = isOperationalProfile();
    const operationalUnitId = String(state.user?.operational_unit_id || '').trim();
    const scopedUnits = lockByOperationalProfile
      ? units.filter((item) => String(item.id) === operationalUnitId)
      : units;
    unitField.innerHTML = scopedUnits.length
      ? scopedUnits.map((item) => `<option value="${item.id}">${item.name} - ${unitTypeLabel(item.unit_type)}</option>`).join('')
      : '<option value="">Sem unidade operacional ativa</option>';
    if (scopedUnits.length && !scopedUnits.some((item) => String(item.id) === String(unitField.value))) {
      unitField.value = String(scopedUnits[0].id);
    } else if (!scopedUnits.length) {
      unitField.value = '';
    }
    unitField.disabled = lockByOperationalProfile;
    if (unitHint) {unitHint.hidden = !lockByOperationalProfile;}
  }

  function outsourcedEmployeesViewHelpers() {
    return globalThis.__EPI_OUTSOURCED_EMPLOYEES_VIEW__ || {};
  }

  function outsourcedEmployeesList() {
    const state = globalThis.__EPI_APP_STATE__;
    const helpers = outsourcedEmployeesViewHelpers();
    const all = filterByUserCompany(state.employees || []);
    if (helpers.outsourcedEmployeesOnly) {return helpers.outsourcedEmployeesOnly(all);}
    // Fallback só vale se o módulo de regras não carregou. Mesmo predicado do
    // módulo — lista explícita, nunca `tipo !== 'CLT'` (ver PR #214).
    const contracted = helpers.CONTRACTED_VINCULOS || CONTRACTED_VINCULOS_FALLBACK;
    return all.filter((item) => contracted.includes(String(item.tipo_vinculo || '').trim())
      && Boolean(item.outsourced_company_id));
  }

  function renderOutsourcedEmployees() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    if (!refs.outsourcedEmployeesTable) {return;}
    const helpers = outsourcedEmployeesViewHelpers();
    const all = outsourcedEmployeesList();
    const visible = helpers.visibleOutsourcedEmployees
      ? helpers.visibleOutsourcedEmployees(all, state.outsourcedEmployeesFilters)
      : all;
    const canUpdate = hasPermission('employees:update_simplified');
    refs.outsourcedEmployeesTable.innerHTML = visible
      .map((item) => formatOutsourcedEmployeeRow(item, { canUpdate }))
      .join('') || globalThis.dsTableState({
        colspan: 7,
        message: tr('outsourcedCompany.employeesEmpty', 'Nenhum colaborador terceirizado/prestador cadastrado.'),
      });
  }

  // Vincular/ativar/desativar o colaborador NESTA Unidade (ADR-0002 §13, PR B).
  // Não arquiva a pessoa (isso é ARCHIVAL_ENTITIES.outsourcedEmployee) e não
  // autoriza entrega de EPI — o gate continua decidindo pela Unidade atual de
  // movimentação. Some da lista desta Unidade; outras Unidades não são afetadas.
  async function toggleEmployeeUnitLink(entityId, action) {
    const state = globalThis.__EPI_APP_STATE__;
    if (!requirePermission(['employees:update', 'employees:update_simplified'])) {return;}
    let reason = '';
    if (action === 'deactivate') {
      const answer = prompt(tr('employee.unitLinkDeactivateReason', 'Motivo do arquivamento (opcional):'));
      if (answer === null) {return;}
      reason = answer || '';
    }
    // Os três caminhos literais (link/activate/deactivate) estão na integração.
    try {
      await outsourcedApi().setEmployeeUnitLink(entityId, action, state.user.id, reason);
      await loadBootstrap({ preserveView: true });
      renderOutsourcedEmployees();
    } catch (error) {
      alert(error.message);
    }
  }

  function formatOutsourcedEmployeeRow(item, permissions) {
    const state = globalThis.__EPI_APP_STATE__;
    const helpers = outsourcedEmployeesViewHelpers();
    const vincLabel = helpers.tipoVinculoLabel ? helpers.tipoVinculoLabel(item.tipo_vinculo) : (item.tipo_vinculo || '');
    const outsourcedCompany = (state.outsourcedCompanies || []).find((c) => String(c.id) === String(item.outsourced_company_id));
    const companyLabel = outsourcedCompany ? (outsourcedCompany.trade_name || outsourcedCompany.legal_name) : '-';
    const entityId = escapeHtml(String(item.id ?? ''));
    const buttons = [];
    if (permissions.canUpdate) {
      buttons.push(`<button class="ghost" data-outsourced-employee-edit="${entityId}">${escapeHtml(tr('edit', 'Editar'))}</button>`);
    }
    // Mesma dupla de permissões de ARCHIVAL_ENTITIES.outsourcedEmployee.deletePermission
    // (ADR-0002 §10.5): Administrador Local/Gestor de EPI só têm
    // employees:update_simplified, nunca employees:delete — sem a segunda
    // permissão o botão nunca aparecia para o perfil que mais usa esta tela.
    if (hasPermission('employees:delete') || permissions.canUpdate) {
      buttons.push(`<button class="ghost" data-outsourced-employee-archive="${entityId}">${escapeHtml(tr('employee.archive', 'Arquivar'))}</button>`);
    }
    // Vínculo local com a Unidade selecionada (ADR-0002 §13, PR C1/C2). O estado
    // vem PRONTO do backend em `local_unit_link_status` — a tela não deduz nada:
    // não compara unit_id, não infere por empresa, não adivinha. `null`/ausente
    // significa "não se aplica" (sem Unidade selecionada, ou mão de obra
    // própria) e nenhuma ação por Unidade aparece.
    const linkStatus = item.local_unit_link_status;
    if (permissions.canUpdate && linkStatus) {
      if (linkStatus === 'active') {
        buttons.push(`<button class="ghost" data-employee-unit-link-deactivate="${entityId}">`
          + `${escapeHtml(tr('employee.unitLinkDeactivate', 'Arquivar nesta Unidade'))}</button>`);
      } else if (linkStatus === 'inactive') {
        buttons.push(`<button class="ghost" data-employee-unit-link-activate="${entityId}">`
          + `${escapeHtml(tr('employee.unitLinkActivate', 'Reativar nesta Unidade'))}</button>`);
      } else {
        buttons.push(`<button class="ghost" data-employee-unit-link="${entityId}">`
          + `${escapeHtml(tr('employee.unitLink', 'Vincular à minha unidade'))}</button>`);
      }
    }
    const actions = buttons.length ? `<div class="action-group">${buttons.join('')}</div>` : '-';
    return `<tr><td>${escapeHtml(item.name || '')}</td><td>${escapeHtml(item.role_name || '')}</td>`
      + `<td>${escapeHtml(vincLabel)}</td><td>${escapeHtml(companyLabel)}</td>`
      + `<td>${escapeHtml(item.unit_name || '')}</td>`
      + `<td>${escapeHtml(outsourcedEmployeeLinkLabel(linkStatus))}</td><td>${actions}</td></tr>`;
  }

  function syncOutsourcedEmployeesFilters() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    state.outsourcedEmployeesFilters.search = String(refs.outsourcedEmployeesFilterSearch?.value || '').trim();
    renderOutsourcedEmployees();
  }

  function setOutsourcedEmployeeFormMode(mode) {
    const cancel = document.getElementById('outsourced-employee-cancel-edit');
    if (cancel) {cancel.hidden = mode !== 'edit';}
  }

  function resetOutsourcedEmployeeForm() {
    const form = document.getElementById('outsourced-employee-form');
    if (!form) {return;}
    form.reset();
    form.elements.id.value = '';
    syncOutsourcedEmployeeUnitOptions();
    setFormSubmitLabel('outsourced-employee-form', tr('outsourcedCompany.employeeSave', 'Salvar Colaborador'));
    setOutsourcedEmployeeFormMode('create');
  }

  // Diferente de startEditOutsourcedCompany (que reaproveita state.outsourcedCompanies
  // já carregado), o Cadastro de Colaboradores só tem no bootstrap os campos da
  // listagem geral — origin_company_registration/badge_number/notes só vêm do
  // item único (GET /api/employees/:id), por isso busca de novo ao editar.
  async function startEditOutsourcedEmployee(entityId) {
    const form = document.getElementById('outsourced-employee-form');
    if (!form) {return;}
    try {
      const data = await outsourcedApi().getEmployee(entityId, actorQuery());
      const item = data.employee || data;
      if (!item || !item.id) {return;}
      form.elements.id.value = item.id;
      if (form.elements.company_id) {form.elements.company_id.value = item.company_id || '';}
      syncOutsourcedEmployeeUnitOptions();
      if (form.elements.unit_id) {form.elements.unit_id.value = item.unit_id || '';}
      syncOutsourcedEmployeeCompanySelect();
      if (form.elements.outsourced_company_id) {form.elements.outsourced_company_id.value = item.outsourced_company_id || '';}
      form.elements.name.value = item.name || '';
      form.elements.cpf.value = item.cpf || '';
      form.elements.role_name.value = item.role_name || '';
      form.elements.tipo_vinculo.value = item.tipo_vinculo || 'Terceirizado';
      form.elements.admission_date.value = item.admission_date || '';
      if (form.elements.origin_company_registration) {form.elements.origin_company_registration.value = item.origin_company_registration || '';}
      if (form.elements.badge_number) {form.elements.badge_number.value = item.badge_number || '';}
      if (form.elements.notes) {form.elements.notes.value = item.notes || '';}
      setFormSubmitLabel('outsourced-employee-form', tr('outsourcedCompany.employeeUpdate', 'Atualizar Colaborador'));
      setOutsourcedEmployeeFormMode('edit');
      showView('terceirizados');
      const nav = document.querySelector('[data-vtabs="terceirizados"]');
      if (nav) {activateViewTab(nav, 'colaboradores');}
    } catch (error) {
      alert(error.message);
    }
  }

  // ── Relatório de headcount por empresa terceirizada/prestadora (ADR-0002
  // §10.4) — GET /api/outsourced-companies/employees-summary. ─────────────────
  async function loadOutsourcedEmployeesSummary() {
    const state = globalThis.__EPI_APP_STATE__;
    if (!hasPermission('employees:view')) {return;}
    try {
      const data = await outsourcedApi().getOutsourcedEmployeesSummary(actorQuery());
      state.outsourcedEmployeesSummary = data.outsourced_employees_summary || data.items || [];
    } catch (error) {
      state.outsourcedEmployeesSummary = [];
      reportNonCriticalError('[terceirizados] falha ao carregar relatório de colaboradores', error);
    }
    renderOutsourcedEmployeesSummary();
  }

  function renderOutsourcedEmployeesSummary() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    if (!refs.outsourcedEmployeesSummaryTable) {return;}
    const items = state.outsourcedEmployeesSummary || [];
    refs.outsourcedEmployeesSummaryTable.innerHTML = items.map((entry) => {
      const byTipo = Object.entries(entry.by_tipo_vinculo || {})
        .map(([tipo, count]) => `${escapeHtml(tipo)}: ${count}`)
        .join(' · ') || '-';
      const name = entry.trade_name || entry.legal_name || '';
      return `<tr><td>${escapeHtml(name)}</td><td>${entry.active_count ?? 0}</td>`
        + `<td>${entry.archived_count ?? 0}</td><td>${byTipo}</td></tr>`;
    }).join('') || globalThis.dsTableState({
      colspan: 4,
      message: tr('outsourcedCompany.reportsEmpty', 'Nenhuma empresa terceirizada/prestadora cadastrada.'),
    });
  }

  // Arquivar reaproveita a MESMA rota/regra do colaborador CLT
  // (/api/employees/:id/archive) — é o mesmo registro, só filtrado nesta
  // tela; reusa archiveEntityRecord(...) para não duplicar o fluxo de
  // motivo/confirmação/auditoria. kind é 'outsourcedEmployee', não 'employee':
  // só o primeiro tem deletePermission com a alternativa
  // employees:update_simplified (ADR-0002 §10.5) e recarrega a lista de
  // arquivados CERTA (archivedOutsourcedEmployees, filtrada outsourced_only=1).
  async function archiveOutsourcedEmployee(entityId) {
    await archiveEntityRecord('outsourcedEmployee', entityId);
    renderOutsourcedEmployees();
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  const exportsMap = {
    isContractedVinculoJs,
    syncOutsourcedEmployeeCompanySelect,
    syncOutsourcedEmployeeUnitOptions,
    outsourcedEmployeesViewHelpers,
    outsourcedEmployeesList,
    renderOutsourcedEmployees,
    toggleEmployeeUnitLink,
    formatOutsourcedEmployeeRow,
    syncOutsourcedEmployeesFilters,
    setOutsourcedEmployeeFormMode,
    resetOutsourcedEmployeeForm,
    startEditOutsourcedEmployee,
    loadOutsourcedEmployeesSummary,
    renderOutsourcedEmployeesSummary,
    archiveOutsourcedEmployee
  };

  for (const [name, fn] of Object.entries(exportsMap)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_OUTSOURCED_EMPLOYEES_UI__ = Object.freeze({ ...exportsMap });
})();
