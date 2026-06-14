'use strict';

// Módulo de autenticação (refatoração JS — Fase 3).
//
// Reimplementação modular e testável das funções de autenticação e gestão de
// sessão de app.js. Segue o padrão aditivo dos demais módulos (permissions-rt,
// feature-flags-rt): app.js mantém suas próprias cópias locais (autoridade em
// runtime); este módulo expõe as versões canônicas em globalThis para o app
// modular futuro, scripts externos e testes unitários.
//
// As funções de sessão operam sobre o objeto de estado compartilhado
// globalThis.__EPI_APP_STATE__ (o mesmo que app.js publica), garantindo que
// callers externos manipulem exatamente o mesmo estado.
(function () {
  if (globalThis.__EPI_MODULE_AUTH_LOADED__) {return;}
  globalThis.__EPI_MODULE_AUTH_LOADED__ = true;

  // ── Helpers internos (fiéis a app.js) ────────────────────────────────────

  function getAppState() {
    return globalThis.__EPI_APP_STATE__ || null;
  }

  function getStorageKeys() {
    return globalThis.STORAGE_KEYS || {
      session: 'epi-session-v4',
      permissions: 'epi-session-v4-permissions',
      token: 'epi-session-v4-token',
      changeRequired: 'epi-session-v4-password-change-required'
    };
  }

  function storageWrite(key, value) {
    if (typeof globalThis.safeStorageWrite === 'function') {
      return globalThis.safeStorageWrite(key, value);
    }
    try { window.localStorage.setItem(key, value); } catch (_e) { /* noop */ }
  }

  function storageRemove(key) {
    if (typeof globalThis.safeStorageRemove === 'function') {
      return globalThis.safeStorageRemove(key);
    }
    try { window.localStorage.removeItem(key); } catch (_e) { /* noop */ }
  }

  // Normalização completa de role — idêntica a app.js (NFD + acentos + espaços).
  function normalizeRoleFull(role) {
    if (!role) {return '';}
    const normalized = String(role)
      .normalize('NFD')
      .replaceAll(/[\u0300-\u036f]/g, '')
      .trim()
      .toLowerCase()
      .replaceAll(/[\s-]+/g, '_');
    const aliases = globalThis.ROLE_ALIASES || {};
    return aliases[normalized] || role;
  }

  // ── Classificação de erros (puro) ────────────────────────────────────────

  function getLoginErrorMessage(error) {
    const code = String(error?.code || '').toUpperCase();
    if (error?.phase === 'post_login_bootstrap') {
      if (code === 'DB_BOOTSTRAP_NOT_READY') {
        return 'Autenticação concluída, mas o sistema ainda está inicializando. Tente novamente em instantes.';
      }
      return `Autenticação concluída, porém falhou o carregamento inicial: ${error?.message || 'erro inesperado.'}`;
    }
    if (code === 'USER_NOT_FOUND') {return 'Usuário não encontrado.';}
    if (code === 'INVALID_CREDENTIALS') {return 'Usuário ou senha inválidos.';}
    if (code === 'USER_INACTIVE') {return 'Usuário inativo. Procure o administrador do sistema.';}
    if (code === 'FORCE_PASSWORD_CHANGE') {return 'É necessário redefinir a senha antes de continuar.';}
    if (error?.status === 403 && !code) {return 'Acesso negado ou sessão inválida.';}
    return error?.message || 'Falha ao autenticar. Verifique usuário e senha.';
  }

  function isTemporaryBootstrapUnavailable(error) {
    const status = Number(error?.status || 0);
    const code = String(error?.code || error?.payload?.error?.code || '').toUpperCase();
    return [502, 503, 504].includes(status) || code === 'DB_BOOTSTRAP_NOT_READY' || code === 'HTTP_503';
  }

  function isSessionRestoreAuthError(error) {
    const status = Number(error?.status || 0);
    return status === 401 || status === 403;
  }

  function isBootstrapRequestError(error) {
    const status = Number(error?.status || 0);
    if (error?.nonFatal) {return true;}
    return status === 502 || status === 503;
  }

  // ── Gestão de sessão (opera sobre __EPI_APP_STATE__) ─────────────────────

  // Idêntica a app.js normalizePermissions: une as permissões recebidas com o
  // fallback do role a partir de ROLE_PERMISSIONS.
  function normalizePermissions(user, permissions = []) {
    const rolePerms = globalThis.ROLE_PERMISSIONS || {};
    const fallback = rolePerms[user?.role] || [];
    return [...new Set([...(permissions || []), ...fallback])];
  }

  function saveSession(user, permissions = [], token = '') {
    const state = getAppState();
    if (!state) {return;}
    const sk = getStorageKeys();
    state.user = { ...user, role: normalizeRoleFull(user?.role) };
    state.permissions = normalizePermissions(state.user, permissions);
    state.token = String(token || '');
    storageWrite(sk.session, JSON.stringify(state.user));
    storageWrite(sk.permissions, JSON.stringify(state.permissions));
    if (state.token) {storageWrite(sk.token, state.token);}
    else {storageRemove(sk.token);}
  }

  function setPasswordChangeRequired(required) {
    const state = getAppState();
    if (!state) {return;}
    const sk = getStorageKeys();
    state.requirePasswordChange = Boolean(required);
    storageWrite(sk.changeRequired, JSON.stringify(state.requirePasswordChange));
  }

  // Espelha app.js _clearAutoRetryCountdown: para o intervalo de contagem
  // regressiva e limpa o texto do elemento de status (quando há DOM).
  function clearAutoRetryCountdown(state) {
    if (state.bootstrapAutoRetryCountdownTimer) {
      clearInterval(state.bootstrapAutoRetryCountdownTimer);
      state.bootstrapAutoRetryCountdownTimer = null;
    }
    try {
      const el = (typeof document !== 'undefined' && document.getElementById)
        ? document.getElementById('bootstrap-auto-retry-status')
        : null;
      if (el) {el.textContent = '';}
    } catch (_e) { /* sem DOM */ }
  }

  function clearSession() {
    const state = getAppState();
    if (!state) {return;}
    const sk = getStorageKeys();
    state.user = null;
    state.permissions = [];
    state.token = '';
    storageRemove(sk.session);
    storageRemove(sk.permissions);
    storageRemove(sk.token);
    storageRemove(sk.changeRequired);
    state.requirePasswordChange = false;
    state.bootstrapDegraded = false;
    state.bootstrapError = null;
    state.bootstrapRetrying = false;
    state.bootstrapWarnings = [];
    state.bootstrapAutoRetryAttempt = 0;
    if (state.bootstrapAutoRetryTimer) {
      clearTimeout(state.bootstrapAutoRetryTimer);
      state.bootstrapAutoRetryTimer = null;
    }
    clearAutoRetryCountdown(state);
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  const api = {
    getLoginErrorMessage,
    isTemporaryBootstrapUnavailable,
    isSessionRestoreAuthError,
    isBootstrapRequestError,
    normalizePermissions,
    saveSession,
    setPasswordChangeRequired,
    clearSession
  };

  for (const [name, fn] of Object.entries(api)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_AUTH__ = Object.freeze({ ...api });

  const helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
  Object.assign(helpers, api);
  globalThis.__EPI_FRONTEND_HELPERS__ = helpers;
})();
