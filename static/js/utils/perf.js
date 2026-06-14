'use strict';

(function () {
  if (globalThis.__EPI_UTILS_PERF_LOADED__) return;
  globalThis.__EPI_UTILS_PERF_LOADED__ = true;

  const reportNonCriticalError = typeof globalThis.reportNonCriticalError === 'function'
    ? globalThis.reportNonCriticalError
    : function (ctx, err) { if (err) console.debug(`[non-critical] ${ctx}`, err); };

  const debugLog = typeof globalThis.debugLog === 'function'
    ? globalThis.debugLog
    : function () {};

  const EPI_PERF_RUNTIME = {
    debugEnabled: false,
    listenerCount: 0,
    analyticsCount: 0,
    activeTabs: 0,
    render: { lastMs: 0, samples: [] },
    activeRequests: new Map(),
    storageTimers: new Map(),
    storagePending: new Map(),
    hud: null
  };

  function isUxPerfDebugEnabled() {
    if (EPI_PERF_RUNTIME.debugEnabled) return true;
    try {
      const params = new URLSearchParams(globalThis.location.search || '');
      const byQuery = params.get('ux_perf_debug') === '1';
      let role = String(globalThis.__EPI_APP_STATE__?.user?.role || '');
      if (!role) {
        const rawSession = typeof safeStorageRead === 'function'
          ? safeStorageRead((globalThis.STORAGE_KEYS || {}).session || 'epi-session-v4', '{}')
          : '{}';
        try { role = String(JSON.parse(rawSession)?.role || ''); } catch (_e) { /* ignore */ }
      }
      EPI_PERF_RUNTIME.debugEnabled = byQuery && role === 'master_admin';
      return EPI_PERF_RUNTIME.debugEnabled;
    } catch (_error) {
      return false;
    }
  }

  function renderPerfHud() {
    if (!isUxPerfDebugEnabled()) return;
    try {
      let hud = EPI_PERF_RUNTIME.hud;
      if (!hud) {
        hud = document.createElement('aside');
        hud.id = 'epi-perf-debug';
        hud.className = 'epi-perf-debug';
        document.body.appendChild(hud);
        EPI_PERF_RUNTIME.hud = hud;
      }
      hud.innerHTML = [
        '<strong>UX Perf Debug</strong>',
        `<span>render: ${Math.round(EPI_PERF_RUNTIME.render.lastMs || 0)}ms</span>`,
        `<span>listeners: ${EPI_PERF_RUNTIME.listenerCount}</span>`,
        `<span>analytics: ${EPI_PERF_RUNTIME.analyticsCount}</span>`,
        `<span>tabs: ${EPI_PERF_RUNTIME.activeTabs}</span>`
      ].join('');
    } catch (error) {
      console.warn('[perf] render HUD indisponível', error);
    }
  }

  function markRenderStart() {
    return globalThis.performance && typeof globalThis.performance.now === 'function'
      ? globalThis.performance.now()
      : Date.now();
  }

  function markRenderEnd(startTs) {
    const endTs = globalThis.performance && typeof globalThis.performance.now === 'function'
      ? globalThis.performance.now()
      : Date.now();
    const elapsed = Math.max(0, endTs - Number(startTs || endTs));
    EPI_PERF_RUNTIME.render.lastMs = elapsed;
    EPI_PERF_RUNTIME.render.samples.push(elapsed);
    EPI_PERF_RUNTIME.render.samples = EPI_PERF_RUNTIME.render.samples.slice(-60);
    renderPerfHud();
  }

  function trackAnalyticsEvent() {
    EPI_PERF_RUNTIME.analyticsCount = Math.min(10000, EPI_PERF_RUNTIME.analyticsCount + 1);
    renderPerfHud();
  }

  function setActiveTabsCount(count) {
    EPI_PERF_RUNTIME.activeTabs = Math.max(0, Number(count || 0));
    renderPerfHud();
  }

  function queueStorageWrite(key, value, options) {
    options = options || {};
    const wait = Math.max(80, Number(options.wait || 180));
    const maxBytes = Number(options.maxBytes || 50000);
    const payload = String(value != null ? value : '');
    EPI_PERF_RUNTIME.storagePending.set(key, { payload, maxBytes });
    const previous = EPI_PERF_RUNTIME.storageTimers.get(key);
    if (previous) globalThis.clearTimeout(previous);
    const timer = globalThis.setTimeout(function () {
      EPI_PERF_RUNTIME.storageTimers.delete(key);
      const pending = EPI_PERF_RUNTIME.storagePending.get(key);
      EPI_PERF_RUNTIME.storagePending.delete(key);
      if (!pending) return;
      try {
        if (pending.payload.length > pending.maxBytes) return;
        if (typeof globalThis.safeStorageWrite === 'function') {
          globalThis.safeStorageWrite(key, pending.payload);
        }
      } catch (error) {
        reportNonCriticalError(`[perf] storage write failed for ${key}`, error);
      }
    }, wait);
    EPI_PERF_RUNTIME.storageTimers.set(key, timer);
  }

  function flushPendingStorageWrites() {
    if (!EPI_PERF_RUNTIME.storagePending.size) return;
    EPI_PERF_RUNTIME.storagePending.forEach(function (pending, key) {
      try {
        if (!pending || typeof pending.payload !== 'string') return;
        if (pending.payload.length > Number(pending.maxBytes || 50000)) return;
        if (typeof globalThis.safeStorageWrite === 'function') {
          globalThis.safeStorageWrite(key, pending.payload);
        }
      } catch (error) {
        reportNonCriticalError(`[perf] storage flush failed for ${key}`, error);
      }
    });
    EPI_PERF_RUNTIME.storagePending.clear();
  }

  function createScopedAbortController(scopeKey) {
    const key = `__EPI_${String(scopeKey || 'SCOPE').toUpperCase().replace(/[^A-Z0-9]+/g, '_')}_ABORT__`;
    try {
      const previous = globalThis[key];
      if (previous && typeof previous.abort === 'function') previous.abort();
    } catch (error) {
      reportNonCriticalError(`[perf] abort controller cleanup failed for ${scopeKey}`, error);
    }
    const controller = new AbortController();
    globalThis[key] = controller;
    return controller;
  }

  function registerAbortableRequest(requestKey) {
    const key = String(requestKey || '');
    if (!key) return new AbortController();
    const previous = EPI_PERF_RUNTIME.activeRequests.get(key);
    if (previous && typeof previous.abort === 'function') previous.abort();
    const controller = new AbortController();
    EPI_PERF_RUNTIME.activeRequests.set(key, controller);
    controller.signal.addEventListener('abort', function () {
      if (EPI_PERF_RUNTIME.activeRequests.get(key) === controller) {
        EPI_PERF_RUNTIME.activeRequests.delete(key);
      }
    }, { once: true });
    return controller;
  }

  globalThis.EPI_PERF_RUNTIME = EPI_PERF_RUNTIME;
  globalThis.isUxPerfDebugEnabled = isUxPerfDebugEnabled;
  globalThis.renderPerfHud = renderPerfHud;
  globalThis.markRenderStart = markRenderStart;
  globalThis.markRenderEnd = markRenderEnd;
  globalThis.trackAnalyticsEvent = trackAnalyticsEvent;
  globalThis.setActiveTabsCount = setActiveTabsCount;
  globalThis.queueStorageWrite = queueStorageWrite;
  globalThis.flushPendingStorageWrites = flushPendingStorageWrites;
  globalThis.createScopedAbortController = createScopedAbortController;
  globalThis.registerAbortableRequest = registerAbortableRequest;
})();
