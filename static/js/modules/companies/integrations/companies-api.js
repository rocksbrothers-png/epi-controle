'use strict';

// Integração: Empresas — endpoints (Refatoração UBX-V5, Etapa 2).
//
// As chamadas que o app.js fazia direto, pelo cliente único (globalThis.api)
// resolvido na CHAMADA. Mesmos métodos, caminhos e corpos (já serializados por
// quem chama, na ordem do negócio). Caminho e método LITERAIS em cada ramo:
// tests/test_frontend_api_contract.py confronta cada chamada com as rotas do
// router. Autorização (companies:*, Master) e isolamento continuam no backend.
// Sem DOM.
(function () {
  if (globalThis.__EPI_MODULE_COMPANIES_INTEGRATIONS_LOADED__) { return; }
  globalThis.__EPI_MODULE_COMPANIES_INTEGRATIONS_LOADED__ = true;

  function createCompany(payload) {
    return globalThis.api('/api/companies', { method: 'POST', body: JSON.stringify(payload) });
  }

  function updateCompany(companyId, payload) {
    return globalThis.api(`/api/companies/${companyId}`, { method: 'PUT', body: JSON.stringify(payload) });
  }

  // Suporte excepcional do Administrador Master (logotipo), auditado no backend.
  function supportUpdateCompany(companyId, payload) {
    return globalThis.api(`/api/companies/${companyId}/support-update`, { method: 'POST', body: JSON.stringify(payload) });
  }

  globalThis.__EPI_COMPANIES_API__ = Object.freeze({ createCompany, updateCompany, supportUpdateCompany });
})();
