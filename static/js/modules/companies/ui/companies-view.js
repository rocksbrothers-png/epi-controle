'use strict';
/* global tr, hasPermission, requirePermission, filterByUserCompany, renderBadge, formatDate, planLabel,
   canAccessCommercialArea, companyLogoMarkup, formatCompanyCurrency, formatCompanyAvailabilityText, formatCnpj,
   fileToJpegDataUrl, bindAppListener, loadBootstrap --
   globais do app.js, de shared/*, de modules/auth e de views/*, resolvidos na chamada */

// UI: Empresas — resumo, lista, detalhes, formulário, ativar/inativar e o
// logotipo por suporte auditado (Refatoração UBX-V5, Etapa 2 — extraído de static/app.js).
//
// Regras puras e corpos de gravação em ../business/company-rules.js; HTTP em
// ../integrations/companies-api.js. Ficam no app.js, por serem compartilhados
// ou de outro domínio: companyLogoSrc/companyLogoMarkup (topo, Comercial,
// Fichas), formatCompanyCurrency (alterado pelo I18N-FULL-V1) e os filtros do
// Comercial. Eram globais do app.js (Annex B), exceto saveCompany e
// toggleCompany (async de bloco); continuam publicadas com os mesmos nomes.
(function () {
  if (globalThis.__EPI_MODULE_COMPANIES_UI_LOADED__) { return; }
  globalThis.__EPI_MODULE_COMPANIES_UI_LOADED__ = true;

  function rules() { return globalThis.__EPI_COMPANIES_BUSINESS__; }
  // SECURITY-OUTPUT-XSS-V1: nome, razão social, CNPJ, plano e observações vêm
  // do cadastro (o Administrador Geral edita o nome) e entram escapados.
  function esc(value) {
    return String(value ?? '').replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
  }
  function companiesApi() { return globalThis.__EPI_COMPANIES_API__; }

  // ── Formulário de Empresa ───────────────────────────────────────────────────

  function getCompanyFormField(name) {
    const refs = globalThis.__EPI_REFS__;
    const field = refs.companyForm?.elements?.namedItem(name) || null;
    if (!field) {console.error(`[company-form] Campo esperado Não encontrado: ${name}`);}
    return field;
  }

  function setCompanyFieldValue(name, value = '', options = {}) {
    const refs = globalThis.__EPI_REFS__;
    const field = options.optional ? refs.companyForm?.elements?.namedItem(name) || null : getCompanyFormField(name);
    if (field) {field.value = value ?? '';}
  }

  function readCompanyFieldValue(name, fallback = '', options = {}) {
    const refs = globalThis.__EPI_REFS__;
    const field = options.optional ? refs.companyForm?.elements?.namedItem(name) || null : getCompanyFormField(name);
    return field ? field.value ?? fallback : fallback;
  }

  // ── Resumo, selos e detalhes ────────────────────────────────────────────────

  function renderCompaniesSummary() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    if (!refs.companiesSummary) {return;}
    const counts = rules().companiesSummaryCounts(filterByUserCompany(state.companies));
    refs.companiesSummary.innerHTML = [
      [tr('company.kpiTotal', 'Empresas'), counts.total],
      [tr('company.kpiActive', 'Ativas'), counts.active],
      [tr('company.kpiNearLimit', 'Próximas do limite'), counts.nearLimit],
      [tr('company.kpiBlocked', 'Bloqueadas'), counts.blocked]
    ].map((item) => `<div class="summary-chip"><strong>${item[1]}</strong><span>${item[0]}</span></div>`).join('');
  }

  function companyStatusBadges(company) {
    const active = rules().isCompanyActive(company);
    const badges = [renderBadge('status', active ? 'active' : 'inactive', active ? tr('company.statusActive', 'Empresa ativa') : tr('company.statusInactive', 'Empresa inativa'))];
    badges.push(renderBadge('status', rules().licenseTone(company.license_status), tr(`license.${company.license_status}`, company.license_status_label || company.license_status)));
    const risk = rules().usageRisk(company);
    if (risk === 'atLimit') {badges.push(renderBadge('status', 'inactive', tr('commercial.risk.atLimit', 'No limite')));}
    else if (risk === 'nearLimit') {badges.push(renderBadge('status', 'warning', tr('commercial.risk.nearLimit', 'Próxima do limite')));}
    return badges.join(' ');
  }

  // Sem chamador interno; mantida publicada (global do app.js pelo Annex B).
  function companyUsageText(company) {
    return `${company.user_count} faturável(eis) de ${company.user_limit} contratado(s)`;
  }

  function validityRangeText(company) {
    return tr('company.validityRange', '{start} até {end}')
      .replace('{start}', formatDate(company.contract_start))
      .replace('{end}', formatDate(company.contract_end));
  }

  function renderCompanyDetails(companyId = null) {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    if (!refs.companyDetails) {return;}
    const visibleCompanies = filterByUserCompany(state.companies);
    if (!visibleCompanies.length) {
      refs.companyDetails.innerHTML = `<div class="summary-item">${tr('company.noCompanySelected', 'Nenhuma empresa disponível.')}</div>`;
      return;
    }
    const selected = visibleCompanies.find((item) => String(item.id) === String(companyId || state.selectedCompanyId)) || visibleCompanies[0];
    state.selectedCompanyId = selected.id;
    const monthly = formatCompanyCurrency(selected.monthly_value);
    const projected = formatCompanyCurrency(selected.projected_monthly_value);
    const cnpjLabel = tr('company.cnpjLabel', 'CNPJ');
    const validityRange = validityRangeText(selected);
    refs.companyDetails.innerHTML = `
    <div class="company-detail-hero">
      ${companyLogoMarkup(selected, 'company-logo company-logo-lg')}
      <div>
        <strong>${esc(selected.name)}</strong>
        <span>${esc(selected.legal_name || '-')}</span>
        <span>${cnpjLabel}: ${esc(selected.cnpj)}</span>
      </div>
    </div>
    <div class="company-detail-badges">${companyStatusBadges(selected)}</div>
    <div class="company-detail-grid">
      <div class="summary-chip"><strong>${selected.user_count ?? '—'}</strong><span>${tr('company.possibleUsers', 'Usuários possíveis')}</span></div>
      <div class="summary-chip"><strong>${selected.user_limit ?? '—'}</strong><span>${tr('company.contractedLimit', 'Limite contratado')}</span></div>
      <div class="summary-chip"><strong>${monthly}</strong><span>${tr('company.monthlyValue', 'Valor mensal atual')}</span></div>
      <div class="summary-chip"><strong>${projected}</strong><span>${tr('company.projectedValue', 'Valor projetado')}</span></div>
      <div class="summary-chip"><strong>${selected.available_slots ?? 0}</strong><span>${tr('company.availableSlots', 'Vagas disponíveis')}</span></div>
    </div>
    <div class="company-detail-list">
      <div class="summary-item"><strong>${tr('company.planLabel', 'Plano / licença')}:</strong> ${esc(planLabel(selected.plan_name) || '-')}</div>
      <div class="summary-item"><strong>${tr('company.unitPrice', 'Valor unitário')}:</strong> ${formatCompanyCurrency(selected.unit_price)}</div>
      <div class="summary-item"><strong>${tr('company.validity', 'Vigência')}:</strong> ${validityRange}</div>
      <div class="summary-item"><strong>${tr('company.addendum', 'Aditivo contratual')}:</strong> ${Number(selected.addendum_enabled || 0) === 1 ? tr('user.active', 'Ativo') : tr('user.inactive', 'Inativo')}</div>
      <div class="summary-item"><strong>${tr('company.commercialNotes', 'Observações comerciais')}:</strong> ${esc(selected.commercial_notes || '-')}</div>
    </div>
    ${canAccessCommercialArea() ? `<div class="action-group"><button class="ghost" type="button" data-company-view-contract="${selected.id}">${tr('company.viewContract', 'Visualizar contrato')}</button></div>` : ''}`;
  }

  // ── Lista ───────────────────────────────────────────────────────────────────

  function companyRowActions(item, canManageCompanies) {
    const viewDetailsLabel = tr('company.viewDetails', 'Visualizar detalhes');
    if (!canManageCompanies) {
      return `<div class="action-group"><button class="ghost" data-company-details="${item.id}">${viewDetailsLabel}</button></div>`;
    }
    const toggleMode = Number(item.active) === 1 ? 0 : 1;
    const toggleLabel = Number(item.active) === 1 ? tr('company.deactivate', 'Inativar') : tr('company.activate', 'Ativar');
    const commercialAction = canAccessCommercialArea()
      ? `<button class="ghost" data-company-commercial="${item.id}">${tr('company.configureLicense', 'Configurar licença')}</button>`
      : '';
    return `<div class="action-group"><button class="ghost" data-company-details="${item.id}">${viewDetailsLabel}</button><button class="ghost" data-company-edit="${item.id}">${tr('company.editAction', 'Editar')}</button><button class="ghost" data-company-logo="${item.id}">Logotipo (suporte)</button>${commercialAction}<button class="ghost" data-company-toggle="${item.id}" data-company-active="${toggleMode}">${toggleLabel}</button></div>`;
  }

  function formatCompanyRow(item, selectedId) {
    const actions = companyRowActions(item, hasPermission('companies:create') || hasPermission('companies:update'));
    const validityRange = validityRangeText(item);
    return `
      <tr class="${selectedId === String(item.id) ? 'selected-row' : ''}">
        <td><div class="company-cell"><strong>${esc(item.name)}</strong><span>${esc(item.legal_name || '-')}</span></div></td>
        <td><div class="company-cell"><strong>${esc(item.cnpj)}</strong><span>${esc(item.plan_name || '-')}</span></div></td>
        <td><div class="company-cell">${companyStatusBadges(item)}<span>${tr('company.validity', 'Vigência')}: ${validityRange}</span></div></td>
        <td><div class="company-logo-slot">${companyLogoMarkup(item, 'company-logo company-logo-sm')}</div></td>
        <td><div class="company-cell"><strong>${item.user_count ?? '—'}</strong><span>${formatCompanyAvailabilityText(item)}</span></div></td>
        <td><div class="company-cell"><strong>${item.user_limit ?? '—'}</strong><span>${formatCompanyCurrency(item.monthly_value)}</span></div></td>
        <td>${actions}</td>
      </tr>`;
  }

  function renderCompanies() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    if (!refs.companiesTable) {return;}
    const visibleCompanies = filterByUserCompany(state.companies);
    const selectedId = String(state.selectedCompanyId || visibleCompanies[0]?.id || '');
    refs.companiesTable.innerHTML = visibleCompanies.map((item) => formatCompanyRow(item, selectedId)).join('') || globalThis.dsTableState({ colspan: 7, message: tr('company.noCompanies', 'Sem empresas disponíveis.') });
  }

  // ── Cadastro, edição e ativação ─────────────────────────────────────────────

  function resetCompanyForm() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    if (!refs.companyForm) {return;}
    state.editingCompanyId = null;
    refs.companyForm.reset();
    setCompanyFieldValue('id', '');
    setCompanyFieldValue('active', '1');
    setCompanyFieldValue('general_admin_email', '', { optional: true });
    setCompanyFieldValue('general_admin_name', '', { optional: true });
    renderCompanyDetails();
  }

  function startEditCompany(companyId) {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    if (!hasPermission('companies:update')) {return;}
    const company = state.companies.find((item) => String(item.id) === String(companyId));
    if (!company || !refs.companyForm) {return;}
    state.editingCompanyId = company.id;
    state.selectedCompanyId = company.id;
    setCompanyFieldValue('id', company.id);
    setCompanyFieldValue('name', company.name || '');
    setCompanyFieldValue('legal_name', company.legal_name || '');
    setCompanyFieldValue('cnpj', company.cnpj || '');
    setCompanyFieldValue('general_admin_email', '', { optional: true });
    setCompanyFieldValue('general_admin_name', '', { optional: true });
    // FIX-EMPRESAS-ACTIVE-V1: `?? 1` (não `|| 1`) — empresa inativa (0) abre como inativa.
    setCompanyFieldValue('active', String(Number(company.active ?? 1)));
    renderCompanies();
    renderCompanyDetails(company.id);
    refs.companyForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // Suporte excepcional (auditado): o Administrador Master não edita a
  // identidade visual da tenant pela rota operacional — apenas via
  // support-update, com justificativa registrada no log de auditoria.
  function openCompanyLogoEditor(companyId) {
    const state = globalThis.__EPI_APP_STATE__;
    if (state.user?.role !== 'master_admin') {return;}
    const company = state.companies.find((item) => String(item.id) === String(companyId));
    if (!company) {return;}
    const reason = window.prompt(`Suporte auditado — justifique a alteração do logotipo de ${company.name} (mínimo 10 caracteres):`);
    if (reason === null) {return;}
    if (!rules().isValidSupportReason(reason)) {
      alert('Justificativa muito curta. Informe pelo menos 10 caracteres.');
      return;
    }
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.png,.jpg,.jpeg,.svg,image/png,image/jpeg,image/svg+xml';
    bindAppListener(input, 'change', async () => {
      const file = input.files?.[0];
      if (!file) {return;}
      if (!rules().COMPANY_LOGO_TYPES.includes(file.type)) {
        alert('Envie um logotipo PNG, JPG ou SVG.');
        return;
      }
      try {
        const logoType = await fileToJpegDataUrl(file);
        await companiesApi().supportUpdateCompany(company.id,
          { actor_user_id: state.user.id, support_reason: String(reason).trim(), logo_type: logoType });
        await loadBootstrap();
        alert('Logotipo atualizado via suporte auditado.');
      } catch (error) { alert(error.message); }
    });
    input.click();
  }

  async function saveCompany(event) {
    const state = globalThis.__EPI_APP_STATE__;
    event.preventDefault();
    if (!requirePermission(state.editingCompanyId ? 'companies:update' : 'companies:create')) {return;}
    try {
      const editing = Boolean(state.editingCompanyId);
      const currentCompany = state.companies.find((item) => String(item.id) === String(state.editingCompanyId || '')) || {};
      // Mesma ordem de avaliação do app.js: o ator primeiro (sem sessão, falha
      // antes de ler o formulário), depois os campos na ordem do corpo.
      const actorUserId = state.user.id;
      const fields = {
        name: readCompanyFieldValue('name', currentCompany.name || ''),
        legal_name: readCompanyFieldValue('legal_name', currentCompany.legal_name || ''),
        cnpj: formatCnpj(readCompanyFieldValue('cnpj', currentCompany.cnpj || '')),
      };
      fields.active = readCompanyFieldValue('active', String(Number(currentCompany.active ?? 1)));
      if (!editing) {
        fields.general_admin_email = readCompanyFieldValue('general_admin_email', '', { optional: true }).trim();
        fields.general_admin_name = readCompanyFieldValue('general_admin_name', '', { optional: true }).trim();
      }
      const values = rules().companySavePayload(actorUserId, fields, currentCompany, editing);
      if (editing) {await companiesApi().updateCompany(state.editingCompanyId, values);}
      else {await companiesApi().createCompany(values);}
      resetCompanyForm();
      await loadBootstrap();
    } catch (error) { alert(error.message); }
  }

  async function toggleCompany(companyId, active) {
    const state = globalThis.__EPI_APP_STATE__;
    if (!hasPermission('companies:update')) {return;}
    const company = state.companies.find((item) => String(item.id) === String(companyId));
    if (!company) {return;}
    try {
      await companiesApi().updateCompany(companyId, rules().companyTogglePayload(state.user.id, company, active));
      await loadBootstrap();
    } catch (error) { alert(error.message); }
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  const exportsMap = {
    getCompanyFormField,
    setCompanyFieldValue,
    readCompanyFieldValue,
    renderCompaniesSummary,
    companyStatusBadges,
    companyUsageText,
    renderCompanyDetails,
    companyRowActions,
    formatCompanyRow,
    renderCompanies,
    resetCompanyForm,
    startEditCompany,
    openCompanyLogoEditor,
    saveCompany,
    toggleCompany
  };

  for (const [name, fn] of Object.entries(exportsMap)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_COMPANIES_UI__ = Object.freeze({ ...exportsMap });
})();
