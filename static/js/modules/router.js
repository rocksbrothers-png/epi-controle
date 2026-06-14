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
  if (globalThis.__EPI_MODULE_ROUTER_LOADED__) {return;}
  globalThis.__EPI_MODULE_ROUTER_LOADED__ = true;

  function getRefs() { return globalThis.__EPI_REFS__ || {}; }
  function getAppState() { return globalThis.__EPI_APP_STATE__ || {}; }

  // ── Utilitários de URL (puros) ────────────────────────────────────────────

  function resolveViewFromLocation() {
    const params = new URLSearchParams((globalThis.location || {}).search || '');
    return String(params.get('view') || '').trim();
  }

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

  // ── View DOM helpers (usam __EPI_REFS__) ─────────────────────────────────

  // Alterna visibilidade entre tela de login e app autenticado.
  function showScreen(authenticated) {
    const r = getRefs();
    if (r.loginScreen) {r.loginScreen.classList.toggle('active', !authenticated);}
    if (r.mainScreen) {r.mainScreen.classList.toggle('active', authenticated);}
  }

  // Ativa/desativa indicador de carregamento da SPA navigation.
  function setSpaNavigationLoading(active) {
    const container = getRefs().mainContent
      || (typeof document !== 'undefined' && document.getElementById('main-content'));
    if (!container) {return;}
    container.classList.toggle('spa-nav-loading', Boolean(active));
    container.setAttribute('aria-busy', active ? 'true' : 'false');
  }

  // Aplica visibilidade do indicador SPA conforme feature flag.
  function applySpaNavigationVisibility() {
    const enabled = typeof globalThis.isSpaNavigationEnabled === 'function'
      ? globalThis.isSpaNavigationEnabled()
      : false;
    if (typeof document !== 'undefined' && document.body) {
      document.body.classList.toggle('spa-navigation-enabled', enabled);
    }
    const indicator = getRefs().spaNavigationIndicator;
    if (indicator) {indicator.hidden = !enabled;}
  }

  // Resolve a view padrão permitida para o usuário atual.
  function defaultView() {
    const ordered = ['dashboard', 'comercial', 'empresas', 'usuarios', 'unidades',
      'colaboradores', 'gestao-colaborador', 'epis', 'estoque', 'entregas',
      'fichas', 'relatorios', 'configuracao'];
    const viewPerms = globalThis.VIEW_PERMISSIONS || {};
    const hperm = typeof globalThis.hasPermission === 'function'
      ? globalThis.hasPermission
      : () => false;
    const user = getAppState().user;
    const perms = getAppState().permissions || [];
    const view = ordered.find((v) => hperm(perms, viewPerms[v]));
    if (!view && perms.length > 0) {
      console.warn('[RBAC][router] nenhuma view liberada para', user?.role);
    }
    return view || 'dashboard';
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  const exports = {
    resolveViewFromLocation,
    buildNavigationUrl,
    showScreen,
    setSpaNavigationLoading,
    applySpaNavigationVisibility,
    defaultView
  };

  for (const [name, fn] of Object.entries(exports)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_ROUTER__ = Object.freeze({ ...exports });

  const helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
  Object.assign(helpers, exports);
  globalThis.__EPI_FRONTEND_HELPERS__ = helpers;
})();
