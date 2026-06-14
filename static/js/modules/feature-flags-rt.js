'use strict';

(function () {
  if (globalThis.__EPI_MODULE_FEATURE_FLAGS_RT_LOADED__) return;
  globalThis.__EPI_MODULE_FEATURE_FLAGS_RT_LOADED__ = true;

  const safeStorageRead = typeof globalThis.safeStorageRead === 'function'
    ? globalThis.safeStorageRead
    : function (key, fallback) {
      try {
        return (typeof window !== 'undefined' && window.localStorage)
          ? (window.localStorage.getItem(key) ?? fallback)
          : fallback;
      } catch (_e) { return fallback; }
    };

  function parseFlagValue(value) {
    if (value === '1' || value === 'true' || value === true) return true;
    if (value === '0' || value === 'false' || value === false) return false;
    return null;
  }

  function resolveFromQueryParam(queryParam) {
    try {
      if (!queryParam || typeof globalThis.location === 'undefined') return null;
      const params = new URLSearchParams(globalThis.location.search || '');
      const val = params.get(queryParam);
      if (val === null) return null;
      return parseFlagValue(val);
    } catch (_error) {
      return null;
    }
  }

  function resolveFromStorage(storageKeys) {
    if (!Array.isArray(storageKeys)) return null;
    for (const key of storageKeys) {
      const raw = safeStorageRead(key, null);
      if (raw !== null) {
        const parsed = parseFlagValue(raw);
        if (parsed !== null) return parsed;
      }
    }
    return null;
  }

  function readFlagFromSources(def, allowStorage) {
    const fromQuery = resolveFromQueryParam(def.queryParam);
    if (fromQuery !== null) return fromQuery;
    if (allowStorage) {
      const fromStorage = resolveFromStorage(def.storageKeys);
      if (fromStorage !== null) return fromStorage;
    }
    return null;
  }

  // Mirrors app.js isGlobalUxKillSwitchEnabled() — checks auto-rollback flag first,
  // then reads ux_global_kill_switch from storage/query.
  function isUxGlobalKillSwitchActive() {
    if (globalThis.__EPI_AUTO_ROLLBACK_ACTIVE__ === true) return true;
    try {
      const defs = globalThis.FEATURE_FLAG_DEFINITIONS;
      const def = defs && defs['ux_global_kill_switch'];
      if (!def) return false;
      return readFlagFromSources(def, true) === true;
    } catch (_e) {
      return false;
    }
  }

  function getFeatureFlag(flagName, options) {
    options = options || {};
    const defaultValue = options.defaultValue !== undefined ? options.defaultValue : false;
    const allowStorage = options.allowStorage !== false;

    try {
      const defs = globalThis.FEATURE_FLAG_DEFINITIONS;
      if (!defs || !defs[flagName]) {
        if (allowStorage) {
          const raw = safeStorageRead(flagName, null);
          if (raw !== null) {
            const parsed = parseFlagValue(raw);
            if (parsed !== null) return parsed;
          }
        }
        return defaultValue;
      }

      // Mirrors app.js kill-switch logic: flags in UX_FORCE_CLASSIC_FLAGS are
      // forced off when the global UX kill switch is active.
      const forceClassic = globalThis.UX_FORCE_CLASSIC_FLAGS;
      if (
        flagName !== 'ux_global_kill_switch' &&
        forceClassic && typeof forceClassic.has === 'function' &&
        forceClassic.has(flagName) &&
        isUxGlobalKillSwitchActive()
      ) {
        return false;
      }

      const def = defs[flagName];
      const resolved = readFlagFromSources(def, allowStorage);
      if (resolved !== null) return resolved;
      return defaultValue;
    } catch (_error) {
      return defaultValue;
    }
  }

  function setFeatureFlag(flagName, value) {
    try {
      const defs = globalThis.FEATURE_FLAG_DEFINITIONS;
      const storageKey = (defs && defs[flagName] && defs[flagName].storageKeys)
        ? defs[flagName].storageKeys[0]
        : flagName;
      const strValue = value ? '1' : '0';
      if (typeof globalThis.safeStorageWrite === 'function') {
        return globalThis.safeStorageWrite(storageKey, strValue);
      }
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.setItem(storageKey, strValue);
        return true;
      }
      return false;
    } catch (_error) {
      return false;
    }
  }

  globalThis.getFeatureFlag = getFeatureFlag;
  globalThis.setFeatureFlag = setFeatureFlag;
  globalThis.isUxGlobalKillSwitchActive = isUxGlobalKillSwitchActive;

  const helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
  helpers.getFeatureFlag = getFeatureFlag;
  helpers.setFeatureFlag = setFeatureFlag;
  helpers.isUxGlobalKillSwitchActive = isUxGlobalKillSwitchActive;
  globalThis.__EPI_FRONTEND_HELPERS__ = helpers;
})();
