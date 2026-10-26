'use strict';
/* global normalizePermissions --
   global de modules/auth.js, resolvido na chamada */

// UI: contexto de acesso da interface (Refatoração UBX-V4, Etapa C).
//
// Liga as regras puras de ../business/access-rules.js ao estado do app: monta
// o contexto { actor, permissions } a cada chamada e publica os nomes legados
// (canManageUser, canDeleteUser, …, sameCompany) com as MESMAS assinaturas que
// tinham no app.js — quem chama (app.js, users-view.js) não muda.
//
// `actor` e `permissions` são getters: leem state.user e a lista ativa no
// momento em que a regra os lê, como o app.js fazia (sem pré-computar nada que
// o original não computaria). A lista ativa é a mesma fórmula de hasPermission
// no app.js — state.permissions, ou o fallback do perfil quando vazia; há teste
// travando que as duas continuem iguais.
//
// Regras de interface: não substituem a autorização do backend.
(function () {
  if (globalThis.__EPI_MODULE_ACCESS_CONTEXT_LOADED__) { return; }
  globalThis.__EPI_MODULE_ACCESS_CONTEXT_LOADED__ = true;

  function rules() { return globalThis.__EPI_ACCESS_RULES__; }

  function activePermissions() {
    const state = globalThis.__EPI_APP_STATE__;
    return state.permissions.length ? state.permissions : normalizePermissions(state.user, []);
  }

  function currentAccessContext() {
    return {
      get actor() { return globalThis.__EPI_APP_STATE__.user; },
      get permissions() { return activePermissions(); }
    };
  }

  function sameCompany(target) { return rules().sameCompany(currentAccessContext(), target); }
  function canManageUser(target) { return rules().canManageUser(currentAccessContext(), target); }
  function canDeleteUser(target) { return rules().canDeleteUser(currentAccessContext(), target); }
  function canPromoteToAdmin(target) { return rules().canPromoteToAdmin(currentAccessContext(), target); }
  function canPromoteToGeneralAdmin(target) { return rules().canPromoteToGeneralAdmin(currentAccessContext(), target); }
  function canDemoteAdmin(target) { return rules().canDemoteAdmin(currentAccessContext(), target); }
  function canDemoteGeneralAdmin(target) { return rules().canDemoteGeneralAdmin(currentAccessContext(), target); }
  function canToggleActive(target) { return rules().canToggleActive(currentAccessContext(), target); }
  function canGenerateRecoveryToken(target) { return rules().canGenerateRecoveryToken(currentAccessContext(), target); }
  function canManageUsers() { return rules().canManageUsers(currentAccessContext()); }
  function canManageEpi() { return rules().canManageEpi(currentAccessContext()); }
  function canViewReports() { return rules().canViewReports(currentAccessContext()); }
  function canAccessCommercialArea() { return rules().canAccessCommercialArea(currentAccessContext()); }
  function canConfigureMyCompany() { return rules().canConfigureMyCompany(currentAccessContext()); }
  function canPrintPurchaseQrLabels() { return rules().canPrintPurchaseQrLabels(currentAccessContext()); }
  function canManagePurchaseFunctions() { return rules().canManagePurchaseFunctions(currentAccessContext()); }

  const legacyExports = {
    sameCompany,
    canManageUser,
    canDeleteUser,
    canPromoteToAdmin,
    canPromoteToGeneralAdmin,
    canDemoteAdmin,
    canDemoteGeneralAdmin,
    canToggleActive,
    canGenerateRecoveryToken,
    canManageUsers,
    canManageEpi,
    canViewReports,
    canAccessCommercialArea,
    canConfigureMyCompany,
    canPrintPurchaseQrLabels,
    canManagePurchaseFunctions
  };

  for (const [name, fn] of Object.entries(legacyExports)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_ACCESS_CONTEXT__ = Object.freeze({ current: currentAccessContext, activePermissions, ...legacyExports });
})();
