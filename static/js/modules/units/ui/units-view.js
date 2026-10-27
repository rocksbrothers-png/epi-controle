'use strict';
/* global tr, escapeHtml, unitTypeLabel, filterByUserCompany, renderTables, unitLegalEntityLabel,
   syncUnitLegalEntityOptions, setFormSubmitLabel, showView, focusRegistrationTab --
   globais do app.js, de views/* e de modules/legal-entities, resolvidos na chamada */

// UI: Unidades — busca, linha da tabela, opção de seletor e edição
// (Refatoração UBX-V5, Etapa 2 — extraído de static/app.js).
//
// Regras puras em ../business/unit-rules.js. A tabela continua sendo montada
// em renderTables (app.js), que chama applyUnitsFilters e formatUnitTableRow;
// o arquivamento de Unidades mora em modules/archival/ (Etapa 1) e o vínculo
// jurídico em modules/legal-entities/. Cadastro e atualização seguem pelo
// saveSimpleForm do app.js. Eram globais do app.js (Annex B) e continuam
// publicadas com os mesmos nomes (modules/employees e modules/reports as usam).
(function () {
  if (globalThis.__EPI_MODULE_UNITS_UI_LOADED__) { return; }
  globalThis.__EPI_MODULE_UNITS_UI_LOADED__ = true;

  function rules() { return globalThis.__EPI_UNITS_BUSINESS__; }

  function unitsForSearchByCompany(companyId = '') {
    const state = globalThis.__EPI_APP_STATE__;
    return rules().unitsOfCompany(filterByUserCompany(state.units), companyId);
  }

  function syncUnitsSearchFilters() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    state.unitsFilters.company_id = String(refs.unitsFilterCompany?.value || '').trim();
    state.unitsFilters.name = String(refs.unitsFilterName?.value || '').trim().toLowerCase();
    state.unitsFilters.type = String(refs.unitsFilterType?.value || '').trim().toLowerCase();
    state.unitsFilters.city = String(refs.unitsFilterCity?.value || '').trim().toLowerCase();
    renderTables();
  }

  function applyUnitsFilters(items) {
    const state = globalThis.__EPI_APP_STATE__;
    return rules().filterUnits(items, state.unitsFilters);
  }

  function formatUnitTableRow(item, canManageUnitRecords) {
    const actions = canManageUnitRecords ? `<div class="action-group"><button class="ghost" data-unit-edit="${item.id}">${tr('edit', 'Editar')}</button><button class="ghost" data-unit-archive="${item.id}">${tr('unit.archive', 'Arquivar')}</button></div>` : '-';
    // Sem esta coluna, uma empresa com vários CNPJs vê uma lista em que todas as
    // unidades parecem iguais — e é justamente aqui que a distinção importa.
    const legalEntity = escapeHtml(unitLegalEntityLabel(item)) || '-';
    return `<tr><td>${item.company_name}</td><td>${legalEntity}</td><td>${item.name}</td><td>${unitTypeLabel(item.unit_type)}</td><td>${item.city}</td><td>${actions}</td></tr>`;
  }

  function formatUnitOption(item) {
    return `<option value="${item.id}">${item.name} - ${unitTypeLabel(item.unit_type)}</option>`;
  }

  function startEditUnit(unitId) {
    const state = globalThis.__EPI_APP_STATE__;
    const item = state.units.find((unit) => String(unit.id) === String(unitId));
    const form = document.getElementById('unit-form');
    if (!item || !form) {return;}
    form.elements.id.value = item.id;
    form.elements.company_id.value = item.company_id;
    form.elements.name.value = item.name || '';
    form.elements.unit_type.value = item.unit_type || 'base';
    form.elements.city.value = item.city || '';
    form.elements.notes.value = item.notes || '';
    // A lista de CNPJs depende da empresa, que acabou de ser preenchida.
    syncUnitLegalEntityOptions();
    if (form.elements.legal_entity_id) {
      form.elements.legal_entity_id.value = item.legal_entity_id ? String(item.legal_entity_id) : '';
    }
    setFormSubmitLabel('unit-form', 'Atualizar unidade');
    showView('unidades');
    focusRegistrationTab('unidades');
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  const exportsMap = {
    unitsForSearchByCompany,
    syncUnitsSearchFilters,
    applyUnitsFilters,
    formatUnitTableRow,
    formatUnitOption,
    startEditUnit
  };

  for (const [name, fn] of Object.entries(exportsMap)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_UNITS_UI__ = Object.freeze({ ...exportsMap });
})();
