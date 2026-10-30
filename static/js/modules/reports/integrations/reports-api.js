'use strict';

// Integração: Relatórios — endpoints (Refatoração UBX-V3, Etapa 4).
//
// As três chamadas de Relatórios que o app.js fazia direto. Usa o cliente
// único (globalThis.api, de modules/api-client.js) resolvido na CHAMADA, como
// o `api(...)` do app.js. Mesmos endpoints, mesma query, mesmo contrato.
// Sem DOM.
(function () {
  if (globalThis.__EPI_MODULE_REPORTS_INTEGRATIONS_LOADED__) { return; }
  globalThis.__EPI_MODULE_REPORTS_INTEGRATIONS_LOADED__ = true;

  // params: URLSearchParams já montado pela UI (filtros + actor_user_id).
  function fetchReports(params) {
    return globalThis.api(`/api/reports?${params.toString()}`);
  }

  function fetchFichaArchive(params) {
    return globalThis.api(`/api/ficha-archive?${params.toString()}`);
  }

  // O PDF abre em nova aba (download pelo navegador, sem fetch).
  function reportPdfUrl(params) {
    return `/api/reports.pdf?${params.toString()}`;
  }

  globalThis.__EPI_REPORTS_API__ = Object.freeze({ fetchReports, fetchFichaArchive, reportPdfUrl });
})();
