'use strict';

(function () {
  if (globalThis.__EPI_UTILS_DEBUG_LOADED__) {return;}
  globalThis.__EPI_UTILS_DEBUG_LOADED__ = true;

  function isDebugModeEnabled() {
    return globalThis.__EPI_DEBUG__ === true;
  }

  function debugLog(context, payload) {
    if (!isDebugModeEnabled()) {return;}
    if (payload === undefined) {
      console.debug(`[debug] ${context}`);
      return;
    }
    console.debug(`[debug] ${context}`, payload);
  }

  function reportNonCriticalError(context, error) {
    if (!error) {return;}
    if (!isDebugModeEnabled()) {return;}
    console.debug(`[non-critical] ${context}`, error);
  }

  function ensureModuleBound(moduleKey) {
    const key = `__EPI_${String(moduleKey || 'MODULE').toUpperCase().replace(/[^A-Z0-9]+/g, '_')}_BOUND__`;
    if (globalThis[key]) {
      debugLog(`[perf] duplicate bind blocked: ${moduleKey}`);
      return false;
    }
    globalThis[key] = true;
    return true;
  }

  globalThis.isDebugModeEnabled = isDebugModeEnabled;
  globalThis.debugLog = debugLog;
  globalThis.reportNonCriticalError = reportNonCriticalError;
  globalThis.ensureModuleBound = ensureModuleBound;

  // Registra no namespace de helpers compartilhados
  const helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
  helpers.debugLog = debugLog;
  helpers.reportNonCriticalError = reportNonCriticalError;
  helpers.ensureModuleBound = ensureModuleBound;
  helpers.isDebugModeEnabled = isDebugModeEnabled;
  globalThis.__EPI_FRONTEND_HELPERS__ = helpers;
})();
