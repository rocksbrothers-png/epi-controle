'use strict';

(function () {
  const globalScope = typeof globalThis !== 'undefined' ? globalThis : window;
  const win = typeof window !== 'undefined' ? window : null;
  const doc = typeof document !== 'undefined' ? document : null;
  if (!win) return;
  if (globalScope.__EPI_ERROR_MONITOR_BOUND__) return;
  globalScope.__EPI_ERROR_MONITOR_BOUND__ = true;

  const DIAGNOSTIC_MODE_KEY = 'epi_diagnostic_mode_enabled';

  function safeStorageRead(key, fallback = '0') {
    try {
      return win.localStorage.getItem(key) ?? fallback;
    } catch (_error) {
      return fallback;
    }
  }

  function parseFlagValue(value) {
    if (value === '1') return true;
    if (value === '0') return false;
    return null;
  }

  function isDiagnosticModeEnabled() {
    try {
      const params = new URLSearchParams(win.location.search);
      const queryEnabled = parseFlagValue(params.get('ux_diagnostics'));
      if (queryEnabled !== null) return queryEnabled;
      return parseFlagValue(safeStorageRead(DIAGNOSTIC_MODE_KEY, '0')) === true;
    } catch (_error) {
      return false;
    }
  }

  function shouldLog() {
    return globalScope.__EPI_DEBUG__ === true || isDiagnosticModeEnabled();
  }

  function sanitizeText(rawValue) {
    const text = String(rawValue ?? '');
    return text
      .replace(/(password|senha)\s*[:=]\s*[^\s&]+/gi, '$1=[REDACTED]')
      .replace(/(token|bearer)\s*[:=]?\s*[^\s&]+/gi, '$1 [REDACTED]')
      .replace(/(authorization)\s*[:=]\s*[^\s&]+/gi, '$1=[REDACTED]');
  }

  function getActiveModule() {
    if (!doc) return 'unknown';
    try {
      const activeView = doc.querySelector('.view.active');
      if (activeView?.id) return activeView.id;
      const mainScreen = doc.getElementById('main-screen');
      if (mainScreen?.classList.contains('active')) return 'main-screen';
      const loginScreen = doc.getElementById('login-screen');
      if (loginScreen?.classList.contains('active')) return 'login-screen';
      return 'unknown';
    } catch (_error) {
      return 'unknown';
    }
  }

  function resolveReporter() {
    const helpers = globalScope.__EPI_FRONTEND_HELPERS__ || {};
    if (typeof helpers.reportNonCriticalError === 'function') {
      return helpers.reportNonCriticalError;
    }
    return (context, error) => {
      if (!error) return;
      if (!shouldLog()) return;
      console.debug(`[non-critical] ${context}`, error);
    };
  }

  function buildSafePayload(base) {
    return {
      message: sanitizeText(base.message || 'Unknown error'),
      file: sanitizeText(base.file || ''),
      line: Number(base.line || 0),
      column: Number(base.column || 0),
      module: getActiveModule(),
      assetsVersion: String(globalScope.__APP_VERSION__ || 'unknown')
    };
  }

  function emitErrorLog(context, payload) {
    if (!shouldLog()) return;
    try {
      const reporter = resolveReporter();
      reporter(context, payload.errorObject || new Error(payload.message));
      console.debug('[error-monitor]', payload);
    } catch (_error) {
      // fail-safe: nunca quebrar a aplicação
    }
  }

  try {
    win.addEventListener('error', (event) => {
      try {
        const payload = buildSafePayload({
          message: event?.message,
          file: event?.filename,
          line: event?.lineno,
          column: event?.colno
        });
        emitErrorLog('[error-monitor] window.error capturado', {
          ...payload,
          errorObject: event?.error instanceof Error ? event.error : undefined
        });
      } catch (_error) {
        // fail-safe
      }
    });

    win.addEventListener('unhandledrejection', (event) => {
      try {
        const reason = event?.reason;
        const message = reason instanceof Error
          ? reason.message
          : (typeof reason === 'string' ? reason : 'Unhandled promise rejection');
        const payload = buildSafePayload({
          message,
          file: '',
          line: 0,
          column: 0
        });
        emitErrorLog('[error-monitor] unhandledrejection capturado', {
          ...payload,
          errorObject: reason instanceof Error ? reason : undefined
        });
      } catch (_error) {
        // fail-safe
      }
    });
  } catch (_error) {
    // fail-safe
  }
})();
