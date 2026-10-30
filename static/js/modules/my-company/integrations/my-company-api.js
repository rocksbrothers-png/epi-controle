'use strict';

// Integração: Minha Empresa — endpoints (Refatoração UBX-V5, Etapa 2).
//
// As chamadas que o app.js fazia direto, pelo cliente único (globalThis.api)
// resolvido na CHAMADA. Mesmos métodos, caminhos, query e corpos (serializados
// aqui, chaves na ordem de quem chama). Caminho e método LITERAIS em cada ramo:
// tests/test_frontend_api_contract.py confronta cada chamada com as rotas do
// router. A empresa vem da sessão no backend (nunca company_id daqui). Sem DOM.
(function () {
  if (globalThis.__EPI_MODULE_MY_COMPANY_INTEGRATIONS_LOADED__) { return; }
  globalThis.__EPI_MODULE_MY_COMPANY_INTEGRATIONS_LOADED__ = true;

  function getMyCompany(actorQueryString) {
    return globalThis.api(`/api/my-company?${actorQueryString}`);
  }

  function updateMyCompany(payload) {
    return globalThis.api('/api/my-company', { method: 'PUT', body: JSON.stringify(payload) });
  }

  // ── Domínios da tenant ──────────────────────────────────────────────────────
  function listMyCompanyDomains(actorQueryString) {
    return globalThis.api(`/api/my-company/domains?${actorQueryString}`);
  }

  function addMyCompanyDomain(payload) {
    return globalThis.api('/api/my-company/domains', { method: 'POST', body: JSON.stringify(payload) });
  }

  function verifyMyCompanyDomain(domainId, payload) {
    return globalThis.api(`/api/my-company/domains/${domainId}/verify`, { method: 'POST', body: JSON.stringify(payload) });
  }

  function setPrimaryMyCompanyDomain(domainId, payload) {
    return globalThis.api(`/api/my-company/domains/${domainId}/primary`, { method: 'POST', body: JSON.stringify(payload) });
  }

  function deleteMyCompanyDomain(domainId, payload) {
    return globalThis.api(`/api/my-company/domains/${domainId}`, { method: 'DELETE', body: JSON.stringify(payload) });
  }

  globalThis.__EPI_MY_COMPANY_API__ = Object.freeze({
    getMyCompany,
    updateMyCompany,
    listMyCompanyDomains,
    addMyCompanyDomain,
    verifyMyCompanyDomain,
    setPrimaryMyCompanyDomain,
    deleteMyCompanyDomain
  });
})();
