'use strict';

// Módulo de roteamento SPA (refatoração JS — Fase 5).
//
// Extrai as funções puras de navegação SPA de app.js. Segue o padrão aditivo:
// app.js mantém suas cópias locais como autoridade em runtime.
//
// ESCOPO DESTA FASE: funções que não dependem de `refs` (objeto de referências
// DOM privado do IIFE de app.js). As funções de manipulação de DOM e orquestra-
// ção de views (showView, navigateToView, renderAll, handleLogin,
// runSpaPartialNavigation, bindSpaNavigationHistory) permanecem em app.js até
// que `refs` seja externalizado (planejado para fase futura de separação de
// estado).
(function () {
  if (globalThis.__EPI_MODULE_ROUTER_LOADED__) return;
  globalThis.__EPI_MODULE_ROUTER_LOADED__ = true;

  // ── Utilitários de URL (puros) ────────────────────────────────────────────

  // Lê o nome da view atual do parâmetro ?view= da URL.
  function resolveViewFromLocation() {
    const params = new URLSearchParams((globalThis.location || {}).search || '');
    return String(params.get('view') || '').trim();
  }

  // Constrói uma nova URL com o parâmetro ?view= atualizado (ou removido).
  // Retorna um objeto URL; use .toString() para obter a string.
  function buildNavigationUrl(view) {
    const href = (globalThis.location || {}).href || 'http://localhost/';
    const url = new URL(href);
    if (view) {
      url.searchParams.set('view', view);
    } else {
      url.searchParams.delete('view');
    }
    return url;
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  const exports = {
    resolveViewFromLocation,
    buildNavigationUrl
  };

  for (const [name, fn] of Object.entries(exports)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_ROUTER__ = Object.freeze({ ...exports });

  const helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
  Object.assign(helpers, exports);
  globalThis.__EPI_FRONTEND_HELPERS__ = helpers;
})();
