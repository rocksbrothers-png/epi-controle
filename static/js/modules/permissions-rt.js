'use strict';

// Runtime de permissões — verifica se usuário pode acessar recurso/view
(function () {
  if (globalThis.__EPI_MODULE_PERMISSIONS_RT_LOADED__) return;
  globalThis.__EPI_MODULE_PERMISSIONS_RT_LOADED__ = true;

  function normalizeRole(rawRole) {
    const role = String(rawRole || '').toLowerCase().trim();
    const aliases = globalThis.ROLE_ALIASES;
    if (aliases && aliases[role]) return aliases[role];
    return role;
  }

  function getPermissionsForRole(role) {
    const normalized = normalizeRole(role);
    const permsMap = globalThis.ROLE_PERMISSIONS;
    if (!permsMap) return [];
    return Array.isArray(permsMap[normalized]) ? permsMap[normalized] : [];
  }

  function hasPermission(roleOrPermsList, permission) {
    if (!permission) return false;

    let permsList;
    if (Array.isArray(roleOrPermsList)) {
      permsList = roleOrPermsList;
    } else {
      permsList = getPermissionsForRole(String(roleOrPermsList || ''));
    }

    return permsList.includes(permission);
  }

  function canViewRoute(viewName, roleOrPermsList) {
    const viewPerms = globalThis.VIEW_PERMISSIONS;
    if (!viewPerms) return false;
    const required = viewPerms[String(viewName || '')];
    if (!required) return false;
    return hasPermission(roleOrPermsList, required);
  }

  function getCurrentUserPermissions() {
    try {
      const state = globalThis.__EPI_APP_STATE__;
      if (state && Array.isArray(state.permissions)) return state.permissions;

      const STORAGE_KEYS = globalThis.STORAGE_KEYS || {};
      const safeRead = typeof globalThis.safeStorageRead === 'function'
        ? globalThis.safeStorageRead
        : function (k, d) { try { return window.localStorage.getItem(k) ?? d; } catch (_e) { return d; } };

      const raw = safeRead(STORAGE_KEYS.permissions || 'epi-session-v4-permissions', '[]');
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch (_error) {
      return [];
    }
  }

  function currentUserHasPermission(permission) {
    return hasPermission(getCurrentUserPermissions(), permission);
  }

  function currentUserCanViewRoute(viewName) {
    return canViewRoute(viewName, getCurrentUserPermissions());
  }

  globalThis.normalizeRole = normalizeRole;
  globalThis.getPermissionsForRole = getPermissionsForRole;
  globalThis.hasPermission = hasPermission;
  globalThis.canViewRoute = canViewRoute;
  globalThis.getCurrentUserPermissions = getCurrentUserPermissions;
  globalThis.currentUserHasPermission = currentUserHasPermission;
  globalThis.currentUserCanViewRoute = currentUserCanViewRoute;

  const helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
  helpers.hasPermission = hasPermission;
  helpers.canViewRoute = canViewRoute;
  helpers.normalizeRole = normalizeRole;
  globalThis.__EPI_FRONTEND_HELPERS__ = helpers;
})();
