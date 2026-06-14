'use strict';

// Pure auth helper functions — no DOM, no app state, no side-effects.
// Mirrors the corresponding functions in app.js; provides globalThis exports
// for external consumers (ux-phase*.js, tests) and a testable unit.
(function () {
  if (globalThis.__EPI_MODULE_AUTH_LOADED__) return;
  globalThis.__EPI_MODULE_AUTH_LOADED__ = true;

  function getLoginErrorMessage(error) {
    const code = String(error?.code || '').toUpperCase();
    if (error?.phase === 'post_login_bootstrap') {
      if (code === 'DB_BOOTSTRAP_NOT_READY') {
        return 'Autenticação concluída, mas o sistema ainda está inicializando. Tente novamente em instantes.';
      }
      return `Autenticação concluída, porém falhou o carregamento inicial: ${error?.message || 'erro inesperado.'}`;
    }
    if (code === 'USER_NOT_FOUND') return 'Usuário não encontrado.';
    if (code === 'INVALID_CREDENTIALS') return 'Usuário ou senha inválidos.';
    if (code === 'USER_INACTIVE') return 'Usuário inativo. Procure o administrador do sistema.';
    if (code === 'FORCE_PASSWORD_CHANGE') return 'É necessário redefinir a senha antes de continuar.';
    if (error?.status === 403 && !code) return 'Acesso negado ou sessão inválida.';
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
    if (Boolean(error?.nonFatal)) return true;
    return status === 502 || status === 503;
  }

  globalThis.getLoginErrorMessage = getLoginErrorMessage;
  globalThis.isTemporaryBootstrapUnavailable = isTemporaryBootstrapUnavailable;
  globalThis.isSessionRestoreAuthError = isSessionRestoreAuthError;
  globalThis.isBootstrapRequestError = isBootstrapRequestError;

  const helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
  helpers.getLoginErrorMessage = getLoginErrorMessage;
  helpers.isTemporaryBootstrapUnavailable = isTemporaryBootstrapUnavailable;
  helpers.isSessionRestoreAuthError = isSessionRestoreAuthError;
  helpers.isBootstrapRequestError = isBootstrapRequestError;
  globalThis.__EPI_FRONTEND_HELPERS__ = helpers;
})();
