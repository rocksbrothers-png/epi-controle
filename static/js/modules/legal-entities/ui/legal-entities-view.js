'use strict';
/* global tr, hasPermission, requirePermission, actorQuery, escapeHtml, populateSelect, setFormSubmitLabel,
   showView, focusRegistrationTab, loadBootstrap --
   globais do app.js e de views/*, resolvidos na chamada */

// UI: CNPJs (Multi-CNPJ) — tela de CNPJs e seletores de vínculo jurídico
// (Refatoração UBX-V5, Etapa 2 — extraído de static/app.js).
//
// Regras puras seguem em js/views/legal-entity-fields.js
// (__EPI_LEGAL_ENTITY_FIELDS__) e js/views/legal-entities-view.js
// (__EPI_LEGAL_ENTITIES_VIEW__), testadas no harness; aqui ficam a leitura do
// estado, o DOM e a chamada de inativação (../integrations/legal-entities-api.js).
// Eram funções do app.js (globais pelo Annex B, exceto deactivateLegalEntity,
// async de bloco); continuam publicadas com os mesmos nomes: o app.js,
// modules/employees, modules/reports e modules/units as chamam.
(function () {
  if (globalThis.__EPI_MODULE_LEGAL_ENTITIES_UI_LOADED__) { return; }
  globalThis.__EPI_MODULE_LEGAL_ENTITIES_UI_LOADED__ = true;

  function legalEntitiesApi() { return globalThis.__EPI_LEGAL_ENTITIES_API__; }

  // ── Multi-CNPJ: seletores de vínculo jurídico ──────────────────────────────

  function legalEntityHelpers() {
    return globalThis.__EPI_LEGAL_ENTITY_FIELDS__ || {};
  }

  function legalEntitiesForCompany(companyId, options) {
    const state = globalThis.__EPI_APP_STATE__;
    const helper = legalEntityHelpers().legalEntitiesForCompany;
    return helper ? helper(state.legalEntities, companyId, options) : [];
  }

  function unitLegalEntityLabel(unit) {
    const helper = legalEntityHelpers().unitLegalEntityLabel;
    return helper ? helper(unit) : String(unit?.legal_entity_cnpj || '');
  }

  function legalEntityOptionsHtml(entities) {
    const label = legalEntityHelpers().legalEntityLabel || ((item) => String(item?.cnpj || ''));
    return entities
      .map((item) => `<option value="${item.id}">${escapeHtml(label(item))}</option>`)
      .join('');
  }

  // Vínculo jurídico da unidade.
  //
  // Diferente do colaborador, aqui não há imutabilidade: a unidade pode mudar de
  // CNPJ responsável (reorganização societária, troca de operadora da JV). O que
  // o backend não faz é *limpar* o vínculo — enviar vazio mantém o valor atual —
  // então o seletor não oferece uma opção "nenhum" que não teria efeito.
  function syncUnitLegalEntityOptions() {
    const state = globalThis.__EPI_APP_STATE__;
    const field = document.getElementById('unit-legal-entity');
    const wrapper = document.getElementById('unit-legal-entity-field');
    if (!field || !wrapper) {return;}
    const companyId = document.getElementById('unit-company')?.value || state.user?.company_id || '';
    const entities = legalEntitiesForCompany(companyId);
    const previous = field.value;
    wrapper.hidden = entities.length === 0;
    field.innerHTML = `<option value="">${tr('legalEntity.selectOptional', 'Selecione o CNPJ')}</option>`
      + legalEntityOptionsHtml(entities);
    if (previous && entities.some((item) => String(item.id) === String(previous))) {
      field.value = previous;
    }
  }

  function syncReportLegalEntityOptions() {
    const state = globalThis.__EPI_APP_STATE__;
    const field = document.getElementById('report-legal-entity');
    const wrapper = document.getElementById('report-legal-entity-field');
    if (!field || !wrapper) {return;}
    const companyId = document.getElementById('report-company')?.value || state.user?.company_id || '';
    const entities = legalEntitiesForCompany(companyId, { activeOnly: false });
    const previous = field.value;
    wrapper.hidden = entities.length === 0;
    field.innerHTML = `<option value="">${tr('employee.filterAll', 'Todos')}</option>`
      + legalEntityOptionsHtml(entities);
    if (previous && entities.some((item) => String(item.id) === String(previous))) {
      field.value = previous;
    }
  }

  // ── Tela de CNPJs (web legado) ─────────────────────────────────────────────

  function legalEntitiesViewHelpers() {
    return globalThis.__EPI_LEGAL_ENTITIES_VIEW__ || {};
  }

  function renderLegalEntities() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    if (!refs.legalEntitiesTable) {return;}
    const helpers = legalEntitiesViewHelpers();
    const visible = helpers.visibleLegalEntities
      ? helpers.visibleLegalEntities(state.legalEntities, state.legalEntitiesFilters)
      : (state.legalEntities || []);
    const canUpdate = hasPermission('legal_entities:update');
    const canDelete = hasPermission('legal_entities:delete');
    refs.legalEntitiesTable.innerHTML = visible
      .map((item) => formatLegalEntityRow(item, { canUpdate, canDelete }))
      .join('') || globalThis.dsTableState({
        colspan: 6,
        message: tr('legalEntity.empty', 'Sem CNPJs cadastrados.'),
      });
  }

  function formatLegalEntityRow(item, permissions) {
    const state = globalThis.__EPI_APP_STATE__;
    const helpers = legalEntitiesViewHelpers();
    const typeLabel = helpers.entityTypeLabel ? helpers.entityTypeLabel(item.entity_type) : '';
    const active = helpers.isActive ? helpers.isActive(item) : Boolean(item.active);
    const status = active
      ? tr('legalEntity.statusActive', 'Ativo')
      : tr('legalEntity.statusInactive', 'Inativo');
    // O botão de inativar só aparece quando a ação é possível: o backend recusa
    // o último CNPJ ativo, e oferecer o botão só geraria mensagem de erro.
    const showDeactivate = permissions.canDelete
      && (helpers.canDeactivate ? helpers.canDeactivate(item, state.legalEntities) : active);
    // O id vira atributo HTML: escapado como qualquer outro dado vindo do
    // servidor, mesmo sendo numérico na prática.
    const entityId = escapeHtml(String(item.id ?? ''));
    const buttons = [];
    if (permissions.canUpdate) {
      buttons.push(`<button class="ghost" data-legal-entity-edit="${entityId}">${escapeHtml(tr('edit', 'Editar'))}</button>`);
    }
    if (showDeactivate) {
      buttons.push(`<button class="ghost" data-legal-entity-deactivate="${entityId}">${escapeHtml(tr('legalEntity.deactivate', 'Inativar'))}</button>`);
    }
    const actions = buttons.length ? `<div class="action-group">${buttons.join('')}</div>` : '-';
    return `<tr><td>${escapeHtml(item.cnpj || '')}</td><td>${escapeHtml(item.legal_name || '')}</td>`
      + `<td>${escapeHtml(item.trade_name || '') || '-'}</td><td>${escapeHtml(typeLabel)}</td>`
      + `<td>${escapeHtml(status)}</td><td>${actions}</td></tr>`;
  }

  function syncLegalEntitiesFilters() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    state.legalEntitiesFilters.search = String(refs.legalEntitiesFilterSearch?.value || '').trim();
    state.legalEntitiesFilters.type = String(refs.legalEntitiesFilterType?.value || '').trim();
    state.legalEntitiesFilters.showInactive = Boolean(refs.legalEntitiesShowInactive?.checked);
    renderLegalEntities();
  }

  // Empresa só é escolhida pelo Administrador Master, que atende vários clientes.
  // Para os demais o campo fica desabilitado com o nome da própria empresa: ela
  // é a da conta, e um seletor de uma opção só induz a erro.
  function syncLegalEntityCompanyField() {
    const state = globalThis.__EPI_APP_STATE__;
    const field = document.getElementById('legal-entity-company');
    const wrapper = document.getElementById('legal-entity-company-field');
    const hint = document.getElementById('legal-entity-company-hint');
    if (!field || !wrapper) {return;}
    const isMaster = state.user?.role === 'master_admin';

    if (isMaster) {
      // Só o Master escolhe: ele atende vários clientes e não tem empresa
      // própria de onde deduzir. O placeholder faz uma seleção vazia ler como
      // "escolha uma", e não como campo quebrado.
      const previous = field.value;
      wrapper.hidden = false;
      field.disabled = false;
      field.required = true;
      populateSelect('legal-entity-company', state.companies, (item) => `${item.name} - ${item.cnpj}`);
      field.insertBefore(
        new Option(tr('company.select', 'Selecione a empresa'), ''),
        field.firstChild,
      );
      field.value = previous || '';
      if (hint) {hint.hidden = true;}
      return;
    }

    // Demais perfis: a empresa é a da conta e não se escolhe. Mostrar o nome —
    // desabilitado, como o CNPJ do colaborador na edição — informa em qual
    // empresa o CNPJ vai nascer sem oferecer uma decisão que não existe.
    const companyName = String(state.user?.company_name || '').trim();
    // Sem nome não há o que afirmar; nesse caso o campo some, e o aviso geral de
    // dados indisponíveis explica a tela.
    wrapper.hidden = companyName === '';
    field.required = false;
    // Desabilitado não é serializado no submit — de propósito: o backend resolve
    // a empresa pela sessão, e enviar um palpite daqui seria uma forma de gravar
    // na empresa errada.
    field.disabled = true;
    field.replaceChildren(new Option(companyName, String(state.user?.company_id || '')));
    if (hint) {hint.hidden = wrapper.hidden;}
  }

  // Alterna o formulário entre cadastrar e atualizar: a saída ("Novo CNPJ") só
  // aparece quando há de onde sair.
  function setLegalEntityFormMode(mode) {
    const cancel = document.getElementById('legal-entity-cancel-edit');
    if (cancel) {cancel.hidden = mode !== 'edit';}
  }

  function resetLegalEntityForm() {
    const form = document.getElementById('legal-entity-form');
    if (!form) {return;}
    form.reset();
    form.elements.id.value = '';
    // `reset()` devolve o valor do atributo `value` do HTML, que é '1'; sendo
    // explícito aqui para não depender do markup na hora de voltar a cadastrar.
    if (form.elements.active) {form.elements.active.value = '1';}
    setFormSubmitLabel('legal-entity-form', tr('legalEntity.save', 'Salvar CNPJ'));
    setLegalEntityFormMode('create');
    syncLegalEntityCompanyField();
  }

  function startEditLegalEntity(entityId) {
    const state = globalThis.__EPI_APP_STATE__;
    const item = (state.legalEntities || []).find((entity) => String(entity.id) === String(entityId));
    const form = document.getElementById('legal-entity-form');
    if (!item || !form) {return;}
    form.elements.id.value = item.id;
    syncLegalEntityCompanyField();
    if (form.elements.company_id) {form.elements.company_id.value = item.company_id || '';}
    form.elements.cnpj.value = item.cnpj || '';
    form.elements.legal_name.value = item.legal_name || '';
    form.elements.trade_name.value = item.trade_name || '';
    form.elements.entity_type.value = item.entity_type || 'matriz';
    form.elements.state_registration.value = item.state_registration || '';
    form.elements.municipal_registration.value = item.municipal_registration || '';
    form.elements.cnae.value = item.cnae || '';
    form.elements.opening_date.value = item.opening_date || '';
    form.elements.address.value = item.address || '';
    form.elements.municipality.value = item.municipality || '';
    form.elements.uf.value = item.uf || '';
    form.elements.cep.value = item.cep || '';
    form.elements.notes.value = item.notes || '';
    // Preserva a situação atual: sem isso o backend assumiria `active = 1` e a
    // simples edição de um CNPJ inativo o reativaria.
    const helpers = legalEntitiesViewHelpers();
    const active = helpers.isActive ? helpers.isActive(item) : Boolean(item.active);
    form.elements.active.value = active ? '1' : '0';
    setFormSubmitLabel('legal-entity-form', tr('legalEntity.update', 'Atualizar CNPJ'));
    setLegalEntityFormMode('edit');
    showView('cnpjs');
    focusRegistrationTab('cnpjs');
  }

  async function deactivateLegalEntity(entityId) {
    const state = globalThis.__EPI_APP_STATE__;
    if (!requirePermission('legal_entities:delete')) {return;}
    const item = (state.legalEntities || []).find((entity) => String(entity.id) === String(entityId));
    if (!item) {return;}
    const confirmed = confirm(tr(
      'legalEntity.deactivateConfirm',
      'Inativar este CNPJ? O histórico jurídico e fiscal é preservado; ele apenas deixa de ser usado em novas operações.',
    ) + `\n\n${item.cnpj} — ${item.legal_name}`);
    if (!confirmed) {return;}
    try {
      await legalEntitiesApi().deactivateLegalEntity(entityId, actorQuery());
      await loadBootstrap();
    } catch (error) {
      alert(error.message);
    }
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  const exportsMap = {
    legalEntityHelpers,
    legalEntitiesForCompany,
    unitLegalEntityLabel,
    legalEntityOptionsHtml,
    syncUnitLegalEntityOptions,
    syncReportLegalEntityOptions,
    legalEntitiesViewHelpers,
    renderLegalEntities,
    formatLegalEntityRow,
    syncLegalEntitiesFilters,
    syncLegalEntityCompanyField,
    setLegalEntityFormMode,
    resetLegalEntityForm,
    startEditLegalEntity,
    deactivateLegalEntity
  };

  for (const [name, fn] of Object.entries(exportsMap)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_LEGAL_ENTITIES_UI__ = Object.freeze({ ...exportsMap });
})();
