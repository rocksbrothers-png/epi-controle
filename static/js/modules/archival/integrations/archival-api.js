'use strict';

// Integração: Arquivamento — endpoints (Refatoração UBX-V5, Etapa 1).
//
// As chamadas que o app.js fazia com `${cfg.path}/...`, pelo cliente único
// (globalThis.api) resolvido na CHAMADA. Mesmos métodos, caminhos, query e
// corpos (chaves na ordem de quem chama). Caminho e método LITERAIS em cada
// ramo: tests/test_frontend_api_contract.py confronta cada chamada com as rotas
// do router. `resource` vem de ARCHIVAL_ENTITIES[kind].resource
// (business) ou é 'units'. Autorização, retenção e isolamento por empresa
// continuam no backend. Sem DOM.
(function () {
  if (globalThis.__EPI_MODULE_ARCHIVAL_INTEGRATIONS_LOADED__) { return; }
  globalThis.__EPI_MODULE_ARCHIVAL_INTEGRATIONS_LOADED__ = true;

  const ROUTES = {
    'employees': {
      archived: (q) => globalThis.api(`/api/employees/archived?${q}`),
      archive: (id, body) => globalThis.api(`/api/employees/${id}/archive`, { method: 'POST', body }),
      restore: (id, body) => globalThis.api(`/api/employees/${id}/restore`, { method: 'POST', body }),
      purgeRequest: (id, body) => globalThis.api(`/api/employees/${id}/purge-request`, { method: 'POST', body }),
      purgeCancel: (id, body) => globalThis.api(`/api/employees/${id}/purge-cancel`, { method: 'POST', body }),
      purgeConfirm: (id, body) => globalThis.api(`/api/employees/${id}/purge-confirm`, { method: 'POST', body }),
    },
    'epis': {
      archived: (q) => globalThis.api(`/api/epis/archived?${q}`),
      archive: (id, body) => globalThis.api(`/api/epis/${id}/archive`, { method: 'POST', body }),
      restore: (id, body) => globalThis.api(`/api/epis/${id}/restore`, { method: 'POST', body }),
      purgeRequest: (id, body) => globalThis.api(`/api/epis/${id}/purge-request`, { method: 'POST', body }),
      purgeCancel: (id, body) => globalThis.api(`/api/epis/${id}/purge-cancel`, { method: 'POST', body }),
      purgeConfirm: (id, body) => globalThis.api(`/api/epis/${id}/purge-confirm`, { method: 'POST', body }),
    },
    'outsourced-companies': {
      archived: (q) => globalThis.api(`/api/outsourced-companies/archived?${q}`),
      archive: (id, body) => globalThis.api(`/api/outsourced-companies/${id}/archive`, { method: 'POST', body }),
      restore: (id, body) => globalThis.api(`/api/outsourced-companies/${id}/restore`, { method: 'POST', body }),
      purgeRequest: (id, body) => globalThis.api(`/api/outsourced-companies/${id}/purge-request`, { method: 'POST', body }),
      purgeCancel: (id, body) => globalThis.api(`/api/outsourced-companies/${id}/purge-cancel`, { method: 'POST', body }),
      purgeConfirm: (id, body) => globalThis.api(`/api/outsourced-companies/${id}/purge-confirm`, { method: 'POST', body }),
    },
    'units': {
      archived: (q) => globalThis.api(`/api/units/archived?${q}`),
      archive: (id, body) => globalThis.api(`/api/units/${id}/archive`, { method: 'POST', body }),
      restore: (id, body) => globalThis.api(`/api/units/${id}/restore`, { method: 'POST', body }),
      purgeRequest: (id, body) => globalThis.api(`/api/units/${id}/purge-request`, { method: 'POST', body }),
      purgeCancel: (id, body) => globalThis.api(`/api/units/${id}/purge-cancel`, { method: 'POST', body }),
      purgeConfirm: (id, body) => globalThis.api(`/api/units/${id}/purge-confirm`, { method: 'POST', body }),
    },
  };

  function routes(resource) {
    const found = Object.prototype.hasOwnProperty.call(ROUTES, resource) ? ROUTES[resource] : null;
    if (!found) { throw new Error(`archival: recurso desconhecido (${resource})`); }
    return found;
  }

  // `query` já vem montada (actorQuery() + filtro extra da listagem).
  function listArchived(resource, query) {
    return routes(resource).archived(query);
  }

  function archiveRecord(resource, recordId, payload) {
    return routes(resource).archive(recordId, JSON.stringify(payload));
  }

  function restoreRecord(resource, recordId, payload) {
    return routes(resource).restore(recordId, JSON.stringify(payload));
  }

  function requestPurge(resource, recordId, payload) {
    return routes(resource).purgeRequest(recordId, JSON.stringify(payload));
  }

  function cancelPurge(resource, recordId, payload) {
    return routes(resource).purgeCancel(recordId, JSON.stringify(payload));
  }

  function confirmPurge(resource, recordId, payload) {
    return routes(resource).purgeConfirm(recordId, JSON.stringify(payload));
  }

  // EPI com saldo/vínculos vivos (#735): o backend decide; a UI só consulta.
  function getEpiArchivalState(recordId, actorQueryString) {
    return globalThis.api(`/api/epis/${recordId}/archival-state?${actorQueryString}`);
  }

  globalThis.__EPI_ARCHIVAL_API__ = Object.freeze({
    listArchived,
    archiveRecord,
    restoreRecord,
    requestPurge,
    cancelPurge,
    confirmPurge,
    getEpiArchivalState
  });
})();
