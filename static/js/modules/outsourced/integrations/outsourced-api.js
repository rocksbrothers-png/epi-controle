'use strict';

// Integração: Terceirizados e Prestadores — endpoints (Refatoração UBX-V4, Etapa B2).
//
// As chamadas que o app.js fazia direto, pelo cliente único (globalThis.api)
// resolvido na CHAMADA. Mesmos métodos, caminhos, query e corpos (chaves na
// mesma ordem). Caminho LITERAL em cada ramo, nunca a ação interpolada na URL:
// tests/test_frontend_api_contract.py confronta cada chamada com as rotas do
// router e não resolve enum-em-path. Autorização, escopo por Unidade e
// isolamento por empresa continuam no backend. Sem DOM.
(function () {
  if (globalThis.__EPI_MODULE_OUTSOURCED_INTEGRATIONS_LOADED__) { return; }
  globalThis.__EPI_MODULE_OUTSOURCED_INTEGRATIONS_LOADED__ = true;

  // ── Empresas terceirizadas/prestadoras ──────────────────────────────────
  function listOutsourcedCompanies(actorQueryString) {
    return globalThis.api(`/api/outsourced-companies?${actorQueryString}`);
  }

  function linkOutsourcedCompanyToUnit(entityId, actorUserId) {
    return globalThis.api(`/api/outsourced-companies/${entityId}/link`, {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: actorUserId }),
    });
  }

  // activate truthy → desarquiva nesta Unidade; senão arquiva (vínculo local).
  function setOutsourcedCompanyUnitLink(entityId, activate, actorUserId, reason) {
    const path = activate
      ? `/api/outsourced-companies/${entityId}/unit-link/activate`
      : `/api/outsourced-companies/${entityId}/unit-link/deactivate`;
    return globalThis.api(path, {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: actorUserId, reason }),
    });
  }

  function createOutsourcedCompanyUpdateRequest(entityId, actorUserId, message) {
    return globalThis.api(`/api/outsourced-companies/${entityId}/update-requests`, {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: actorUserId, message }),
    });
  }

  function listPendingOutsourcedCompanyUpdateRequests(actorQueryString) {
    return globalThis.api(`/api/outsourced-companies/update-requests?status=pending&${actorQueryString}`);
  }

  function resolveOutsourcedCompanyUpdateRequest(requestId, actorUserId, notes) {
    return globalThis.api(`/api/outsourced-companies/update-requests/${requestId}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: actorUserId, status: 'resolved', resolution_notes: notes }),
    });
  }

  function promoteOutsourcedCompany(entityId, actorUserId) {
    return globalThis.api(`/api/outsourced-companies/${entityId}/promote`, {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: actorUserId }),
    });
  }

  // ── Colaboradores terceirizados/prestadores ─────────────────────────────
  // action: 'link' (vincular), 'activate' (reativar) ou qualquer outro valor
  // (arquivar nesta Unidade) — mesma cascata do app.js.
  function setEmployeeUnitLink(entityId, action, actorUserId, reason) {
    let path;
    if (action === 'link') {
      path = `/api/employees/${entityId}/link`;
    } else if (action === 'activate') {
      path = `/api/employees/${entityId}/unit-link/activate`;
    } else {
      path = `/api/employees/${entityId}/unit-link/deactivate`;
    }
    return globalThis.api(path, {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: actorUserId, reason }),
    });
  }

  function getEmployee(entityId, actorQueryString) {
    return globalThis.api(`/api/employees/${entityId}?${actorQueryString}`);
  }

  function getOutsourcedEmployeesSummary(actorQueryString) {
    return globalThis.api(`/api/outsourced-companies/employees-summary?${actorQueryString}`);
  }

  globalThis.__EPI_OUTSOURCED_API__ = Object.freeze({
    listOutsourcedCompanies,
    linkOutsourcedCompanyToUnit,
    setOutsourcedCompanyUnitLink,
    createOutsourcedCompanyUpdateRequest,
    listPendingOutsourcedCompanyUpdateRequests,
    resolveOutsourcedCompanyUpdateRequest,
    promoteOutsourcedCompany,
    setEmployeeUnitLink,
    getEmployee,
    getOutsourcedEmployeesSummary
  });
})();
