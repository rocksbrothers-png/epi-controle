'use strict';
/* global tr, hasPermission, requirePermission, actorQuery, escapeHtml, formatDate, unitTypeLabel,
   isOperationalProfile, filterByUserCompany, setFormSubmitLabel, showView, focusRegistrationTab,
   syncOutsourcedEmployeeCompanySelect, renderOutsourcedEmployees, coalesceLoad --
   globais do app.js, de shared/ui e de views/*, resolvidos na chamada (ver abaixo) */

// UI: Terceirizados e Prestadores — empresas (Refatoração UBX-V4, Etapa B2 —
// extraído de static/app.js).
//
// Lista, empresas disponíveis para vincular, arquivadas nesta Unidade,
// formulário (Unidade de origem imutável, trava corporativa pós-promoção),
// vínculo local, duplicidade de CNPJ e promoção. A caixa de solicitações de
// atualização cadastral está em ./outsourced-company-requests-view.js. Regras puras em js/views/outsourced-companies-view.js; HTTP em
// ../integrations/outsourced-api.js. Estado e refs: os MESMOS objetos do
// app.js, lidos na chamada. Os gates hasPermission/requirePermission são os
// do app.js (fallback visual; quem autoriza é o backend) — nenhuma regra mudou.
// As funções async (load*, link*, toggle*, handle*, promote*) eram `async function` de bloco no app.js; agora são globais.
(function () {
  if (globalThis.__EPI_MODULE_OUTSOURCED_COMPANIES_UI_LOADED__) { return; }
  globalThis.__EPI_MODULE_OUTSOURCED_COMPANIES_UI_LOADED__ = true;

  function outsourcedApi() { return globalThis.__EPI_OUTSOURCED_API__; }

  // Trava pós-promoção (ADR-0002 §12): quando o ator não tem employees:update
  // completo e a empresa já é Cadastro Padrão, os campos corporativos ficam
  // só-leitura com um aviso — mesma decisão que
  // ensure_actor_can_edit_outsourced_company_corporate_fields toma no
  // backend (que é quem decide de fato); aqui só evita deixar o formulário
  // "sumir" sem explicação quando "Solicitar atualização" é a única ação
  // oferecida na linha (formatOutsourcedCompanyRow).
  const OUTSOURCED_COMPANY_CORPORATE_FIELDS = ['legal_name', 'trade_name', 'cnpj', 'company_kind', 'epi_responsibility'];

  // Regras puras vivem em js/views/outsourced-companies-view.js (testadas no
  // harness); aqui ficam a leitura do estado, o DOM e as chamadas de API.
  function outsourcedCompaniesViewHelpers() {
    return globalThis.__EPI_OUTSOURCED_COMPANIES_VIEW__ || {};
  }

  // Diferente de `state.legalEntities`, esta lista não chega no bootstrap — o
  // módulo nasce oculto por padrão, então só busca quando a tela é aberta
  // (chamado a partir de showView).
  async function loadOutsourcedCompanies() {
    const state = globalThis.__EPI_APP_STATE__;
    // Gate alinhado ao backend (handle_get_outsourced_companies exige só
    // PERM_EMPLOYEES_VIEW, igual a loadOutsourcedEmployeesSummary logo abaixo)
    // — 'employees:create' era restritivo demais e nunca é concedido a
    // Administrador Local/Gestor de EPI (só têm employees:create_simplified),
    // então a lista nunca carregava para esses perfis: nem a aba "Lista" nem o
    // seletor de empresa do Cadastro de Colaboradores (syncOutsourcedEmployeeCompanySelect,
    // chamado por renderOutsourcedCompanies logo abaixo) recebiam dados.
    if (!hasPermission('employees:view')) {return;}
    // FIX-NAV-REFRESH-V1: pedida pela tela e pela operação na mesma atualização → uma requisição.
    return coalesceLoad('outsourced-companies', async () => {
      try {
        const data = await outsourcedApi().listOutsourcedCompanies(actorQuery());
        state.outsourcedCompanies = data.outsourced_companies || data.items || [];
        // Empresas do tenant ainda não vinculadas à própria Unidade (ADR-0002
        // §12 — compartilhamento por tenant): campos públicos só, mascarados no
        // backend (fetch_outsourced_companies/annotate_outsourced_company_visibility) —
        // nunca contrato/nota/colaborador de outra Unidade. Vazio para quem não
        // é escopado por Unidade (já vê tudo em outsourcedCompanies).
        state.outsourcedCompaniesAvailable = data.available_outsourced_companies || [];
      } catch (error) {
        state.outsourcedCompanies = [];
        state.outsourcedCompaniesAvailable = [];
        reportNonCriticalError('[terceirizados] falha ao carregar empresas terceirizadas', error);
      }
      renderOutsourcedCompanies();
    });
  }

  function renderOutsourcedCompanies() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    if (!refs.outsourcedCompaniesTable) {return;}
    const helpers = outsourcedCompaniesViewHelpers();
    // Perfis escopados por Unidade (Administrador Local/Gestor de EPI) são os
    // únicos cujos itens vêm com local_status (annotate_outsourced_company_visibility,
    // só roda para eles) — é o que diferencia "arquivar nesta Unidade" (por
    // vínculo) do arquivamento global do corporativo, que continua exclusivo
    // de quem não é escopado.
    const isUnitScoped = ['admin', 'user'].includes(state.user?.role);
    const allLinked = state.outsourcedCompanies || [];
    const isArchivedInUnit = helpers.isArchivedInUnit || ((item) => String(item?.local_status || '') === 'inactive');
    const activeLinked = isUnitScoped
      ? allLinked.filter((item) => !isArchivedInUnit(item))
      : allLinked;
    const visible = helpers.visibleOutsourcedCompanies
      ? helpers.visibleOutsourcedCompanies(activeLinked, state.outsourcedCompaniesFilters)
      : activeLinked;
    const canUpdate = hasPermission(['employees:update', 'employees:update_simplified']);
    refs.outsourcedCompaniesTable.innerHTML = visible
      .map((item) => formatOutsourcedCompanyRow(item, { canUpdate }))
      .join('') || globalThis.dsTableState({
        colspan: 7,
        message: tr('outsourcedCompany.empty', 'Nenhuma empresa terceirizada cadastrada.'),
      });
    // Empresas do tenant que a própria Unidade ainda não vinculou (ADR-0002
    // §12) — seção separada da "Lista" principal, nunca junto: mostrar como
    // "vinculável" algo que ainda não é gerenciável evitaria confundir com o
    // que já está sob a Unidade do ator.
    if (refs.outsourcedCompaniesAvailableTable) {
      const available = state.outsourcedCompaniesAvailable || [];
      refs.outsourcedCompaniesAvailableTable.innerHTML = available
        .map((item) => formatOutsourcedCompanyAvailableRow(item))
        .join('') || globalThis.dsTableState({
          colspan: 7,
          message: tr('outsourcedCompany.availableEmpty', 'Nenhuma empresa disponível para vincular.'),
        });
    }
    // Empresas arquivadas NESTA Unidade (Administrador Local/Gestor de EPI) —
    // mesma ação de vínculo local (toggleOutsourcedCompanyUnitLink), só
    // exibida em seção separada da Lista principal; nunca duplica o
    // arquivamento global (ARCHIVAL_ENTITIES.outsourcedCompany/"restaurar"),
    // que continua exclusivo de quem não é escopado por Unidade — os dois
    // cartões da aba "Empresas Arquivadas" são mutuamente exclusivos por
    // perfil, nunca mostrados juntos.
    if (refs.outsourcedCompanyUnitArchivedCard) {refs.outsourcedCompanyUnitArchivedCard.hidden = !isUnitScoped;}
    if (refs.archivedOutsourcedCompaniesCard) {refs.archivedOutsourcedCompaniesCard.hidden = isUnitScoped;}
    if (isUnitScoped && refs.outsourcedCompanyUnitArchivedTable) {
      const archived = allLinked.filter((item) => isArchivedInUnit(item));
      refs.outsourcedCompanyUnitArchivedTable.innerHTML = archived
        .map((item) => formatOutsourcedCompanyUnitArchivedRow(item))
        .join('') || globalThis.dsTableState({
          colspan: 6,
          message: tr('outsourcedCompany.unitArchivedEmpty', 'Nenhuma empresa arquivada nesta Unidade.'),
        });
    }
    // O seletor de empresa do Cadastro de Colaboradores depende da mesma
    // lista — resincroniza sempre que ela muda (mesma lógica de
    // bindDependentSelects, mas esta lista não vem do bootstrap).
    syncOutsourcedEmployeeCompanySelect();
    renderOutsourcedEmployees();
  }

  // Linha de "Empresas arquivadas nesta Unidade" — mesmos dados do vínculo
  // local (unit_link_deactivated_at/reason/by_user_id, anexados por
  // annotate_outsourced_company_visibility), só que renderizados numa seção
  // separada da Lista, com "Desarquivar" em vez de "Editar".
  function formatOutsourcedCompanyUnitArchivedRow(item) {
    const state = globalThis.__EPI_APP_STATE__;
    const entityId = escapeHtml(String(item.id ?? ''));
    const responsible = (state.users || []).find((u) => String(u.id) === String(item.unit_link_deactivated_by_user_id));
    const responsibleName = responsible ? (responsible.full_name || '') : '';
    return `<tr><td>${escapeHtml(item.legal_name || '')}</td><td>${escapeHtml(item.cnpj || '') || '-'}</td>`
      + `<td>${formatDate(item.unit_link_deactivated_at)}</td><td>${escapeHtml(item.unit_link_deactivation_reason || '') || '-'}</td>`
      + `<td>${escapeHtml(responsibleName) || '-'}</td>`
      + `<td><button class="ghost" data-outsourced-company-toggle-link="${entityId}" data-activate="1">${escapeHtml(tr('outsourcedCompany.activateLink', 'Desarquivar nesta Unidade'))}</button></td></tr>`;
  }

  function formatOutsourcedCompanyRow(item, permissions) {
    const helpers = outsourcedCompaniesViewHelpers();
    const kindLabel = helpers.companyKindLabel ? helpers.companyKindLabel(item.company_kind) : (item.company_kind || '');
    const modeLabel = helpers.registrationModeLabel ? helpers.registrationModeLabel(item) : '';
    const hasFullUpdate = hasPermission('employees:update');
    // Promover só faz sentido para quem ainda está no Simplificado — o backend
    // também recusa promover quem já é Padrão, mas oferecer o botão sempre só
    // geraria mensagem de erro sem efeito. Ação exclusiva de Administrador
    // Geral/de Registro (employees:update completo) — Administrador Local/
    // Gestor de EPI (só employees:update_simplified) nunca a alcançam no
    // backend (handle_post_outsourced_company_promote não foi ampliada de
    // propósito, ADR-0002 §10.5), então o botão fica fora para eles também.
    const showPromote = hasFullUpdate && (helpers.canPromote ? helpers.canPromote(item) : true);
    // Trava pós-promoção (ADR-0002 §12): "Editar" só continua valendo se o
    // ator tem employees:update completo OU a empresa ainda está no
    // Simplificado — espelha ensure_actor_can_edit_outsourced_company_corporate_fields
    // do backend, que é quem decide de fato. Travado + ainda pode gerenciar
    // (permissions.canUpdate) → oferece "Solicitar atualização" no lugar.
    const corporateLocked = helpers.isCorporateLocked ? helpers.isCorporateLocked(item) : false;
    const canEditCorporate = helpers.canEditCorporateFields
      ? helpers.canEditCorporateFields(item, hasFullUpdate) : true;
    const entityId = escapeHtml(String(item.id ?? ''));
    const buttons = [];
    if (permissions.canUpdate && canEditCorporate) {
      buttons.push(`<button class="ghost" data-outsourced-company-edit="${entityId}">${escapeHtml(tr('edit', 'Editar'))}</button>`);
    } else if (permissions.canUpdate && corporateLocked) {
      buttons.push(`<button class="ghost" data-outsourced-company-request-update="${entityId}">${escapeHtml(tr('outsourcedCompany.requestUpdate', 'Solicitar atualização cadastral'))}</button>`);
    }
    if (showPromote) {
      buttons.push(`<button class="ghost" data-outsourced-company-promote="${entityId}">${escapeHtml(tr('outsourcedCompany.promote', 'Promover a Cadastro Padrão'))}</button>`);
    }
    // "Arquivar nesta Unidade" (vínculo local, ex-"Desativar vínculo local" —
    // ADR-0002 §12 item 8/Problema 4 do pedido): nunca a mesma coisa que
    // arquivar o corporativo (ARCHIVAL_ENTITIES.outsourcedCompany, exclusivo
    // de quem não é escopado por Unidade) — sempre liberado para quem já
    // gerencia a empresa, independente de registration_mode/trava acima.
    // `local_status` só vem preenchido para quem é escopado por Unidade
    // (fetch_outsourced_companies/annotate_outsourced_company_visibility) —
    // ausente para Geral/Registro, que não têm UMA Unidade só para alternar.
    // Na prática só chega aqui com linkActive === true: renderOutsourcedCompanies
    // já filtra local_status === 'inactive' para fora desta tabela (formatOutsourcedCompanyUnitArchivedRow
    // cobre a seção "Empresas arquivadas nesta Unidade") — o ramo inativo
    // segue aqui só como defesa, nunca alcançado no fluxo normal.
    const linkStatus = item.local_status;
    if (permissions.canUpdate && linkStatus !== undefined && linkStatus !== null) {
      const linkActive = String(linkStatus) !== 'inactive';
      const toggleLabel = linkActive
        ? tr('outsourcedCompany.deactivateLink', 'Arquivar nesta Unidade')
        : tr('outsourcedCompany.activateLink', 'Desarquivar nesta Unidade');
      buttons.push(`<button class="ghost" data-outsourced-company-toggle-link="${entityId}" data-activate="${linkActive ? '0' : '1'}">${escapeHtml(toggleLabel)}</button>`);
    }
    const actions = buttons.length ? `<div class="action-group">${buttons.join('')}</div>` : '-';
    const linkStatusLabel = linkStatus === undefined || linkStatus === null
      ? '-'
      : (String(linkStatus) === 'inactive' ? tr('outsourcedCompany.linkInactive', 'Arquivado') : tr('outsourcedCompany.linkActive', 'Ativo'));
    return `<tr><td>${escapeHtml(item.legal_name || '')}</td><td>${escapeHtml(item.cnpj || '') || '-'}</td>`
      + `<td>${escapeHtml(kindLabel)}</td><td>${escapeHtml(item.epi_responsibility || '')}</td>`
      + `<td>${escapeHtml(modeLabel)}</td><td>${escapeHtml(linkStatusLabel)}</td><td>${actions}</td></tr>`;
  }

  // Empresas do tenant ainda não vinculadas à Unidade do ator — linha com só
  // os campos públicos (ADR-0002 §12 item 12 do pedido: nunca contrato, nota
  // ou colaborador de outra Unidade) + a ação "Vincular à minha unidade".
  function formatOutsourcedCompanyAvailableRow(item) {
    const helpers = outsourcedCompaniesViewHelpers();
    const modeLabel = helpers.registrationModeLabel ? helpers.registrationModeLabel(item) : '';
    const entityId = escapeHtml(String(item.id ?? ''));
    // origin_unit_name/linked_units_count (decisão explícita do usuário,
    // reversão da máscara original — ver _mask_outsourced_company_public_fields
    // em modules/outsourced_companies/service.py). Só a Unidade de origem fica
    // '-' quando a empresa é "do tenant" (sem origem) — a contagem de vínculos
    // vale para qualquer empresa, com ou sem origem.
    const originUnitLabel = escapeHtml(item.origin_unit_name || '') || '-';
    const linkedUnitsLabel = String(Number(item.linked_units_count || 0));
    return `<tr><td>${escapeHtml(item.legal_name || '')}</td><td>${escapeHtml(item.trade_name || '') || '-'}</td>`
      + `<td>${escapeHtml(item.cnpj || '') || '-'}</td><td>${originUnitLabel}</td><td>${linkedUnitsLabel}</td>`
      + `<td>${escapeHtml(modeLabel)}</td>`
      + `<td><button class="ghost" data-outsourced-company-link="${entityId}">${escapeHtml(tr('outsourcedCompany.linkToMyUnit', 'Vincular à minha unidade'))}</button></td></tr>`;
  }

  function syncOutsourcedCompaniesFilters() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    state.outsourcedCompaniesFilters.search = String(refs.outsourcedCompaniesFilterSearch?.value || '').trim();
    state.outsourcedCompaniesFilters.kind = String(refs.outsourcedCompaniesFilterKind?.value || '').trim();
    renderOutsourcedCompanies();
  }

  // Alterna o formulário entre cadastrar e atualizar — mesmo padrão de
  // setLegalEntityFormMode.
  function setOutsourcedCompanyFormMode(mode) {
    const cancel = document.getElementById('outsourced-company-cancel-edit');
    if (cancel) {cancel.hidden = mode !== 'edit';}
  }

  // Unidade de origem (ADR-0002 §12): imutável depois de criada — nem
  // Administrador Geral reatribui por aqui, o backend nem lê mais esse campo
  // no update. No CADASTRO (sem id ainda), continua o comportamento de
  // sempre: Administrador Local/Gestor de EPI (isOperationalProfile())
  // travados na própria unidade operacional (resolve_outsourced_company_unit_id
  // só roda no create), demais perfis com seletor livre. Auto-detecta o modo
  // pelo próprio estado do formulário (mesmo `editingId` que saveSimpleForm
  // usa), então funciona tanto chamado por startEditOutsourcedCompany/
  // resetOutsourcedCompanyForm quanto por bindDependentSelects (que não sabe
  // se há uma edição em andamento).
  function syncOutsourcedCompanyUnitOptions() {
    const state = globalThis.__EPI_APP_STATE__;
    const unitField = document.getElementById('outsourced-company-unit');
    if (!unitField) {return;}
    const form = document.getElementById('outsourced-company-form');
    const editingId = form?.elements?.id?.value ? String(form.elements.id.value) : '';
    if (editingId) {
      const item = (state.outsourcedCompanies || []).find((entity) => String(entity.id) === editingId);
      const origin = item?.unit_id != null
        ? (state.units || []).find((unit) => String(unit.id) === String(item.unit_id))
        : null;
      unitField.innerHTML = origin
        ? `<option value="${origin.id}">${escapeHtml(origin.name)} - ${escapeHtml(unitTypeLabel(origin.unit_type))}</option>`
        : `<option value="">${escapeHtml(tr('outsourcedCompany.allUnits', 'Todas as unidades (padrão)'))}</option>`;
      unitField.value = origin ? String(origin.id) : '';
      unitField.disabled = true;
      return;
    }
    const lockByOperationalProfile = isOperationalProfile();
    if (!lockByOperationalProfile) {
      unitField.disabled = false;
      return;
    }
    const operationalUnitId = String(state.user?.operational_unit_id || '').trim();
    const scopedUnit = filterByUserCompany(state.units || []).find((item) => String(item.id) === operationalUnitId);
    unitField.innerHTML = scopedUnit
      ? `<option value="${escapeHtml(scopedUnit.id)}">${escapeHtml(`${scopedUnit.name}`)} - ${unitTypeLabel(scopedUnit.unit_type)}</option>`
      : '<option value="" data-i18n="employee.noActiveOperationalUnit">Sem unidade operacional ativa</option>';
    unitField.value = scopedUnit ? String(scopedUnit.id) : '';
    unitField.disabled = true;
  }

  function applyOutsourcedCompanyCorporateLock(item) {
    const refs = globalThis.__EPI_REFS__;
    const form = document.getElementById('outsourced-company-form');
    const banner = refs.outsourcedCompanyCorporateLockBanner;
    const helpers = outsourcedCompaniesViewHelpers();
    const locked = Boolean(item) && helpers.isCorporateLocked
      && helpers.isCorporateLocked(item) && !hasPermission('employees:update');
    if (form) {
      OUTSOURCED_COMPANY_CORPORATE_FIELDS.forEach((name) => {
        const field = form.elements[name];
        if (field) {field.disabled = locked;}
      });
      const submitButton = form.querySelector('button[type="submit"]');
      if (submitButton) {submitButton.hidden = locked;}
    }
    if (banner) {banner.hidden = !locked;}
  }

  function resetOutsourcedCompanyForm() {
    const form = document.getElementById('outsourced-company-form');
    if (!form) {return;}
    form.reset();
    form.elements.id.value = '';
    syncOutsourcedCompanyUnitOptions();
    applyOutsourcedCompanyCorporateLock(null);
    setFormSubmitLabel('outsourced-company-form', tr('outsourcedCompany.save', 'Salvar Empresa'));
    setOutsourcedCompanyFormMode('create');
  }

  function startEditOutsourcedCompany(entityId) {
    const state = globalThis.__EPI_APP_STATE__;
    const item = (state.outsourcedCompanies || []).find((entity) => String(entity.id) === String(entityId));
    const form = document.getElementById('outsourced-company-form');
    if (!item || !form) {return;}
    form.elements.id.value = item.id;
    form.elements.legal_name.value = item.legal_name || '';
    form.elements.trade_name.value = item.trade_name || '';
    form.elements.cnpj.value = item.cnpj || '';
    form.elements.company_kind.value = item.company_kind || 'outsourced';
    form.elements.epi_responsibility.value = item.epi_responsibility || 'Conforme Contrato';
    syncOutsourcedCompanyUnitOptions();
    applyOutsourcedCompanyCorporateLock(item);
    setFormSubmitLabel('outsourced-company-form', tr('outsourcedCompany.update', 'Atualizar Empresa'));
    setOutsourcedCompanyFormMode('edit');
    showView('terceirizados');
    focusRegistrationTab('terceirizados');
  }

  // "Vincular à minha unidade" (ADR-0002 §12) — cria o vínculo local sem
  // duplicar o cadastro corporativo; usado tanto pelo botão na seção
  // "Empresas disponíveis para vinculação" quanto pelo fluxo de duplicidade
  // de CNPJ (handleOutsourcedCompanyDuplicateError, perto de saveSimpleForm).
  async function linkOutsourcedCompanyToMyUnit(entityId) {
    const state = globalThis.__EPI_APP_STATE__;
    if (!requirePermission(['employees:update', 'employees:update_simplified'])) {return;}
    try {
      await outsourcedApi().linkOutsourcedCompanyToUnit(entityId, state.user.id);
      await loadOutsourcedCompanies();
    } catch (error) {
      alert(error.message);
    }
  }

  // Arquiva/desarquiva a empresa NESTA Unidade (vínculo local) — nunca o
  // cadastro corporativo (ADR-0002 §12 item 8 do pedido: não confundir com o
  // arquivamento global de ARCHIVAL_ENTITIES.outsourcedCompany, exclusivo de
  // quem não é escopado por Unidade). Some da Lista e do seletor de novos
  // colaboradores desta Unidade; outras Unidades vinculadas não são afetadas.
  async function toggleOutsourcedCompanyUnitLink(entityId, activate) {
    const state = globalThis.__EPI_APP_STATE__;
    if (!requirePermission(['employees:update', 'employees:update_simplified'])) {return;}
    let reason = '';
    if (!activate) {
      reason = prompt(tr('outsourcedCompany.deactivateLinkReasonPrompt', 'Motivo do arquivamento (opcional):')) || '';
      if (reason === null) {return;}
    }
    // Os dois caminhos literais (activate/deactivate) estão na integração.
    try {
      await outsourcedApi().setOutsourcedCompanyUnitLink(entityId, activate, state.user.id, reason);
      await loadOutsourcedCompanies();
    } catch (error) {
      alert(error.message);
    }
  }

  // Chamado só pelo catch de saveSimpleForm para o outsourced-company-form
  // (ADR-0002 §12 itens 14-15 do pedido). Devolve `true` quando já tratou o
  // erro (a mensagem genérica não deve mais aparecer via alert()).
  async function handleOutsourcedCompanyDuplicateError(error, form) {
    if (error?.code === 'duplicate_cnpj') {
      const existingId = error.payload?.existing_company_id;
      const confirmed = confirm(
        `${error.message}\n\n${tr('outsourcedCompany.duplicateCnpjLinkPrompt', 'Deseja vincular essa empresa à sua Unidade em vez de cadastrar de novo?')}`,
      );
      if (confirmed && existingId) {
        await linkOutsourcedCompanyToMyUnit(existingId);
      }
      return true;
    }
    if (error?.code === 'possible_duplicate') {
      const matches = error.payload?.matches || [];
      const names = matches.map((item) => `- ${item.legal_name}${item.trade_name ? ` (${item.trade_name})` : ''}`).join('\n');
      const confirmed = confirm(
        `${error.message}\n\n${names}\n\n${tr('outsourcedCompany.confirmCreateAnyway', 'Cadastrar mesmo assim?')}`,
      );
      if (confirmed) {
        form.dataset.confirmDuplicate = '1';
        if (typeof form.requestSubmit === 'function') {form.requestSubmit();}
        else {form.dispatchEvent(new Event('submit', { cancelable: true }));}
      }
      return true;
    }
    return false;
  }

  async function promoteOutsourcedCompany(entityId) {
    const state = globalThis.__EPI_APP_STATE__;
    if (!requirePermission('employees:update')) {return;}
    const item = (state.outsourcedCompanies || []).find((entity) => String(entity.id) === String(entityId));
    if (!item) {return;}
    const confirmed = confirm(tr(
      'outsourcedCompany.promoteConfirm',
      'Promover ao Cadastro Padrão? A empresa passa a ser tratada como Cadastro Padrão. É preciso ter um CNPJ preenchido.',
    ) + `\n\n${item.legal_name}`);
    if (!confirmed) {return;}
    try {
      await outsourcedApi().promoteOutsourcedCompany(entityId, state.user.id);
      await loadOutsourcedCompanies();
    } catch (error) {
      alert(error.message);
    }
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  const exportsMap = {
    outsourcedCompaniesViewHelpers,
    loadOutsourcedCompanies,
    renderOutsourcedCompanies,
    formatOutsourcedCompanyUnitArchivedRow,
    formatOutsourcedCompanyRow,
    formatOutsourcedCompanyAvailableRow,
    syncOutsourcedCompaniesFilters,
    setOutsourcedCompanyFormMode,
    syncOutsourcedCompanyUnitOptions,
    applyOutsourcedCompanyCorporateLock,
    resetOutsourcedCompanyForm,
    startEditOutsourcedCompany,
    linkOutsourcedCompanyToMyUnit,
    toggleOutsourcedCompanyUnitLink,
    handleOutsourcedCompanyDuplicateError,
    promoteOutsourcedCompany
  };

  for (const [name, fn] of Object.entries(exportsMap)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_OUTSOURCED_COMPANIES_UI__ = Object.freeze({ ...exportsMap });
})();
