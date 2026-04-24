'use strict';

(function () {
  const globalScope = typeof globalThis !== 'undefined' ? globalThis : window;
  const win = typeof window !== 'undefined' ? window : null;
  const doc = typeof document !== 'undefined' ? document : null;
  if (!win) return;
  if (globalScope.__EPI_ERROR_MONITOR_BOUND__) return;
  globalScope.__EPI_ERROR_MONITOR_BOUND__ = true;

  const DIAGNOSTIC_MODE_KEY = 'epi_diagnostic_mode_enabled';
  const MAX_ERRORS_PER_MODULE = 50;
  const MAX_UNSTABLE_APIS = 50;
  const MAX_CRITICAL_BUFFER = 100;
  const MAX_AUTO_ROLLBACK_ERRORS = 10;
  const AUTO_ROLLBACK_WINDOW_MS = 10000;
  const MAX_CONSECUTIVE_5XX = 5;
  const UX_FLAG_STORAGE_KEYS = Object.freeze([
    'ux_phase41_enabled',
    'ux_phase42_enabled',
    'ux_phase43_enabled',
    'ux_phase44_enabled',
    'ux_hierarchical_navigation_enabled',
    'ux_multitab_navigation_enabled',
    'spa_navigation_enabled',
    'ux_global_enabled',
    'dashboard_interativo_enabled',
    'entrega_epi_htmx_enabled'
  ]);
  const monitorState = {
    errorsByModule: {},
    moduleErrorTimeline: {},
    unstableApis: {},
    unstableApiOrder: [],
    criticalFailures: []
  };
  let consecutive5xxFailures = 0;
  const recentErrorWindow = [];

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

  function countByKey(container, key) {
    const safeKey = String(key || 'unknown');
    container[safeKey] = Number(container[safeKey] || 0) + 1;
  }

  function pushModuleError(moduleName) {
    const key = String(moduleName || 'unknown');
    const timeline = monitorState.moduleErrorTimeline[key] || [];
    timeline.push(Date.now());
    if (timeline.length > MAX_ERRORS_PER_MODULE) timeline.shift();
    monitorState.moduleErrorTimeline[key] = timeline;
    monitorState.errorsByModule[key] = timeline.length;
  }

  function pushErrorWindowTick() {
    const now = Date.now();
    recentErrorWindow.push(now);
    while (recentErrorWindow.length && now - recentErrorWindow[0] > AUTO_ROLLBACK_WINDOW_MS) {
      recentErrorWindow.shift();
    }
    return recentErrorWindow.length;
  }

  function pushCriticalFailure(type, payload) {
    monitorState.criticalFailures.push({
      at: new Date().toISOString(),
      module: String(payload?.module || 'unknown'),
      type: String(type || 'critical_error')
    });
    if (monitorState.criticalFailures.length > MAX_CRITICAL_BUFFER) {
      monitorState.criticalFailures.splice(0, monitorState.criticalFailures.length - MAX_CRITICAL_BUFFER);
    }
  }

  function activateClassicMode(reason) {
    if (globalScope.__EPI_AUTO_ROLLBACK_ACTIVE__ === true) return;
    globalScope.__EPI_AUTO_ROLLBACK_ACTIVE__ = true;
    try {
      for (const key of UX_FLAG_STORAGE_KEYS) {
        win.localStorage.setItem(key, '0');
      }
    } catch (_error) {
      // fail-safe
    }
    pushCriticalFailure('auto_rollback_activated', { module: getActiveModule() });
    if (shouldLog()) {
      console.warn('[error-monitor] rollback automático ativado', reason);
    }
  }

  function trackCritical(payload) {
    if (!payload) return;
    pushModuleError(payload.module || 'unknown');
    const errorsInWindow = pushErrorWindowTick();
    if (errorsInWindow > MAX_AUTO_ROLLBACK_ERRORS) {
      activateClassicMode('error_rate_threshold');
    }
    const isCritical = /critical|failed to fetch|unexpected end|ficha_audit_unavailable|5\d\d/i.test(String(payload.message || ''));
    if (!isCritical) return;
    pushCriticalFailure('critical_error', payload);
  }

  function trackApiInstability(url, statusCode) {
    const safeUrl = String(url || 'unknown');
    const pathOnly = safeUrl.split('?')[0];
    const key = `${pathOnly}::${statusCode}`;
    if (!(key in monitorState.unstableApis)) {
      monitorState.unstableApiOrder.push(key);
      if (monitorState.unstableApiOrder.length > MAX_UNSTABLE_APIS) {
        const oldest = monitorState.unstableApiOrder.shift();
        if (oldest) delete monitorState.unstableApis[oldest];
      }
    }
    countByKey(monitorState.unstableApis, key);
    const is5xx = Number(statusCode) >= 500;
    consecutive5xxFailures = is5xx ? consecutive5xxFailures + 1 : consecutive5xxFailures;
    if (consecutive5xxFailures > MAX_CONSECUTIVE_5XX) {
      activateClassicMode('consecutive_5xx_threshold');
    }
  }

  function emitErrorLog(context, payload) {
    trackCritical(payload);
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

    if (typeof win.fetch === 'function' && win.fetch.__EPI_MONITORED_FETCH__ !== true) {
      const originalFetch = globalScope.__EPI_FETCH_MONITOR_ORIGINAL__ || win.fetch;
      globalScope.__EPI_FETCH_MONITOR_ORIGINAL__ = originalFetch;
      const monitoredFetch = async function monitoredFetch(...args) {
        const input = args[0];
        const url = typeof input === 'string' ? input : String(input?.url || '');
        try {
          const response = await originalFetch.apply(this, args);
          if (response && Number(response.status) >= 500) {
            trackApiInstability(url, response.status);
            emitErrorLog('[error-monitor] API instável detectada', buildSafePayload({
              message: `API response ${response.status} for ${url}`,
              file: '',
              line: 0,
              column: 0
            }));
          } else {
            consecutive5xxFailures = 0;
          }
          return response;
        } catch (error) {
          trackApiInstability(url, 'network_error');
          emitErrorLog('[error-monitor] Falha de rede na API', buildSafePayload({
            message: `API network error for ${url}`,
            file: '',
            line: 0,
            column: 0
          }));
          throw error;
        }
      };
      Object.defineProperty(monitoredFetch, '__EPI_MONITORED_FETCH__', {
        value: true,
        writable: false,
        configurable: false
      });
      win.fetch = monitoredFetch;
    }
  } catch (_error) {
    // fail-safe
  }
  const monitoringApi = Object.freeze({
    getSnapshot: () => ({
      errorsByModule: { ...monitorState.errorsByModule },
      unstableApis: { ...monitorState.unstableApis },
      criticalFailures: monitorState.criticalFailures.slice(),
      autoRollbackActive: globalScope.__EPI_AUTO_ROLLBACK_ACTIVE__ === true
    })
  });
  Object.defineProperty(globalScope, '__EPI_MONITORING__', {
    value: monitoringApi,
    writable: false,
    configurable: false,
    enumerable: false
  });
})();
