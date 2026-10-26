'use strict';
/* global tr, hasPermission, requirePermission, actorQuery, escapeHtml, syncViewTabsVisibility --
   globais do app.js e de views/*, resolvidos na chamada (ver abaixo) */

// UI: Terceirizados e Prestadores — solicitações de atualização cadastral
// (Refatoração UBX-V4, Etapa B2 — extraído de static/app.js).
//
// Administrador Local/Gestor de EPI REGISTRAM o pedido; Geral/Registro
// (employees:update completo) veem a caixa e resolvem. HTTP em
// ../integrations/outsourced-api.js; estado e refs do app.js lidos na chamada;
// gates hasPermission/requirePermission do app.js (quem autoriza é o backend).
// As três funções async eram `async function` de bloco no app.js; agora são globais.
(function () {
  if (globalThis.__EPI_MODULE_OUTSOURCED_REQUESTS_UI_LOADED__) { return; }
  globalThis.__EPI_MODULE_OUTSOURCED_REQUESTS_UI_LOADED__ = true;

  function outsourcedApi() { return globalThis.__EPI_OUTSOURCED_API__; }

  // "Solicitar atualização cadastral" (ADR-0002 §12) — modal simples
  // (mensagem livre), mesmo padrão de openRequestReportModal/submitReportRequest
  // (estoque.html), só que sem tela dedicada: usa prompt() para manter o
  // escopo proporcional a "avisar que um campo precisa de correção".
  async function requestOutsourcedCompanyUpdate(entityId) {
    const state = globalThis.__EPI_APP_STATE__;
    if (!requirePermission(['employees:update', 'employees:update_simplified'])) {return;}
    const message = prompt(tr(
      'outsourcedCompany.requestUpdatePrompt',
      'Descreva o que precisa ser corrigido/atualizado no cadastro corporativo:',
    ));
    if (!message || !message.trim()) {return;}
    try {
      await outsourcedApi().createOutsourcedCompanyUpdateRequest(entityId, state.user.id, message.trim());
      alert(tr('outsourcedCompany.requestUpdateSent', 'Solicitação enviada ao Administrador Geral/de Registro.'));
    } catch (error) {
      alert(error.message);
    }
  }

  // ── Inbox de "Solicitações" (Geral/Registro, ADR-0002 §12) ────────────────
  async function loadOutsourcedCompanyUpdateRequests() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    // Card (e por tabela, a própria aba "Solicitações" — syncViewTabsVisibility
    // esconde uma aba cujo painel não tem nenhum filho visível) só existe para
    // quem tem employees:update completo (Geral/Registro): Administrador
    // Local/Gestor de EPI só REGISTRAM pedido (requestOutsourcedCompanyUpdate),
    // nunca veem a fila de resolução dos outros.
    const allowed = hasPermission('employees:update');
    if (refs.outsourcedCompanyUpdateRequestsCard) {refs.outsourcedCompanyUpdateRequestsCard.hidden = !allowed;}
    const nav = document.querySelector('[data-vtabs="terceirizados"]');
    if (nav && typeof syncViewTabsVisibility === 'function') {syncViewTabsVisibility(nav);}
    if (!allowed) {return;}
    try {
      const data = await outsourcedApi().listPendingOutsourcedCompanyUpdateRequests(actorQuery());
      state.outsourcedCompanyUpdateRequests = data.outsourced_company_update_requests || data.items || [];
    } catch (error) {
      state.outsourcedCompanyUpdateRequests = [];
      reportNonCriticalError('[terceirizados] falha ao carregar solicitações de atualização', error);
    }
    renderOutsourcedCompanyUpdateRequests();
  }

  function renderOutsourcedCompanyUpdateRequests() {
    const state = globalThis.__EPI_APP_STATE__;
    const refs = globalThis.__EPI_REFS__;
    if (!refs.outsourcedCompanyUpdateRequestsTable) {return;}
    const items = state.outsourcedCompanyUpdateRequests || [];
    refs.outsourcedCompanyUpdateRequestsTable.innerHTML = items.map((request) => {
      const companyName = (state.outsourcedCompanies || [])
        .find((c) => String(c.id) === String(request.outsourced_company_id))?.legal_name || `#${request.outsourced_company_id}`;
      return `<tr><td>${escapeHtml(companyName)}</td><td>${escapeHtml(request.requested_by_name || '')}</td>`
        + `<td>${escapeHtml(request.message || '')}</td><td>${escapeHtml(request.created_at || '')}</td>`
        + `<td><button class="ghost" data-outsourced-company-update-request-resolve="${escapeHtml(String(request.id))}">${escapeHtml(tr('outsourcedCompany.resolveRequest', 'Resolver'))}</button></td></tr>`;
    }).join('') || globalThis.dsTableState({
      colspan: 5,
      message: tr('outsourcedCompany.requestsEmpty', 'Nenhuma solicitação pendente.'),
    });
  }

  async function resolveOutsourcedCompanyUpdateRequest(requestId) {
    const state = globalThis.__EPI_APP_STATE__;
    if (!requirePermission('employees:update')) {return;}
    const notes = prompt(tr('outsourcedCompany.resolveRequestNotesPrompt', 'Notas da resolução (opcional):')) || '';
    try {
      await outsourcedApi().resolveOutsourcedCompanyUpdateRequest(requestId, state.user.id, notes);
      await loadOutsourcedCompanyUpdateRequests();
    } catch (error) {
      alert(error.message);
    }
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  const exportsMap = {
    requestOutsourcedCompanyUpdate,
    loadOutsourcedCompanyUpdateRequests,
    renderOutsourcedCompanyUpdateRequests,
    resolveOutsourcedCompanyUpdateRequest
  };

  for (const [name, fn] of Object.entries(exportsMap)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_OUTSOURCED_REQUESTS_UI__ = Object.freeze({ ...exportsMap });
})();
