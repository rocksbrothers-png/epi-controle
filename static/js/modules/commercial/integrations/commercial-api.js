'use strict';

// Integração: Comercial — endpoints (UBX Comercial, fatia C2; extraído de static/app.js).
//
// As chamadas que o app.js fazia direto aos nove endpoints de modules/commercial
// (contrato comercial e parâmetros comerciais), pelo cliente único
// (globalThis.api) resolvido na CHAMADA: mesmo cliente, mesma autenticação,
// mesmos cabeçalhos e o mesmo tratamento de erro. Mesmos métodos, caminhos,
// querystrings e corpos (serializados aqui com JSON.stringify sobre o mesmo
// objeto que o app.js montava). Caminho e método LITERAIS em cada função:
// tests/test_frontend_api_contract.py confronta cada chamada com as rotas do
// router. As duas rotas abertas em nova aba (PDF e arquivo gerado) só têm a URL
// montada aqui; quem abre a aba continua sendo o app.js.
//
// O PUT /api/companies/<id> usado pelo Comercial (salvar contrato e
// suspender/reativar) é o do domínio Empresas: o app.js usa
// __EPI_COMPANIES_API__.updateCompany, sem duplicar a chamada aqui.
//
// Autorização (commercial:view, Administrador Master) e isolamento por empresa
// continuam no backend. Sem DOM, sem estado do app. Publica só
// __EPI_COMMERCIAL_API__ (congelado); carga idempotente.
(function () {
  if (globalThis.__EPI_MODULE_COMMERCIAL_INTEGRATIONS_LOADED__) { return; }
  globalThis.__EPI_MODULE_COMMERCIAL_INTEGRATIONS_LOADED__ = true;

  // GET /api/commercial-contract — uma chamada de um argumento, como antes.
  function getContract(actorUserId, companyId) {
    return globalThis.api(`/api/commercial-contract?actor_user_id=${actorUserId}&company_id=${companyId}`);
  }

  // GET /api/commercial-contract.pdf — aberto em nova aba pelo app.js.
  function contractPdfUrl(query) {
    return `/api/commercial-contract.pdf?${new URLSearchParams(query).toString()}`;
  }

  // GET /api/commercial-contract/file — aberto em nova aba pelo app.js.
  function contractFileUrl(query) {
    return `/api/commercial-contract/file?${new URLSearchParams(query).toString()}`;
  }

  function saveContractDraft(payload) {
    return globalThis.api('/api/commercial-contract/save', { method: 'POST', body: JSON.stringify(payload) });
  }

  function generateContract(payload) {
    return globalThis.api('/api/commercial-contract/generate', { method: 'POST', body: JSON.stringify(payload) });
  }

  function signContract(payload) {
    return globalThis.api('/api/commercial-contract/sign', { method: 'POST', body: JSON.stringify(payload) });
  }

  function uploadSignedContract(payload) {
    return globalThis.api('/api/commercial-contract/upload-signed', { method: 'POST', body: JSON.stringify(payload) });
  }

  function sendContractEmail(payload) {
    return globalThis.api('/api/commercial-contract/send-email', { method: 'POST', body: JSON.stringify(payload) });
  }

  function saveCommercialSettings(payload) {
    return globalThis.api('/api/commercial-settings', { method: 'POST', body: JSON.stringify(payload) });
  }

  globalThis.__EPI_COMMERCIAL_API__ = Object.freeze({
    getContract,
    contractPdfUrl,
    contractFileUrl,
    saveContractDraft,
    generateContract,
    signContract,
    uploadSignedContract,
    sendContractEmail,
    saveCommercialSettings
  });
})();
