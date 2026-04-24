(function uxAnalyticsIife() {
  var helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
  var ensureModuleBound = typeof helpers.ensureModuleBound === 'function'
    ? helpers.ensureModuleBound
    : function () { return true; };
  if (!ensureModuleBound('ux_analytics')) return;

  var safeOn = typeof helpers.safeOn === 'function'
    ? helpers.safeOn
    : function (target, eventName, handler, options) {
      try {
        if (!target || typeof target.addEventListener !== 'function') return false;
        target.addEventListener(eventName, handler, options);
        return true;
      } catch (_error) {
        return false;
      }
    };

  function isEnabled() {
    try {
      var params = new URLSearchParams(globalThis.location.search || '');
      if (params.get('ux_analytics') === '1') return true;
      if (params.get('ux_analytics') === '0') return false;
      if (typeof helpers.getFeatureFlag === 'function') {
        return helpers.getFeatureFlag('ux_tools_functional_enabled', { defaultValue: false, allowStorage: true }) === true;
      }
      return false;
    } catch (_error) {
      return false;
    }
  }

  if (!isEnabled()) return;

  var STORAGE_KEY = 'epi:ux:analytics:v1';
  var MAX_EVENTS = 100;
  var MAX_BYTES = 28000;
  var queue = [];
  var eventCounts = new Map();
  var writeTimer = null;
  var REPETITIVE_EVENTS = new Set(['ui:click', 'ui:hover', 'ui:input', 'ui:filter', 'ui:search']);

  function safeRead() {
    try {
      var parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
      return Array.isArray(parsed) ? parsed.slice(-MAX_EVENTS) : [];
    } catch (_error) {
      return [];
    }
  }

  function queueWrite(events) {
    var payload = JSON.stringify(events.slice(-MAX_EVENTS));
    if (payload.length > MAX_BYTES) return;
    if (typeof helpers.queueStorageWrite === 'function') {
      helpers.queueStorageWrite(STORAGE_KEY, payload, { wait: 240, maxBytes: MAX_BYTES });
      return;
    }
    if (writeTimer) clearTimeout(writeTimer);
    writeTimer = setTimeout(function () {
      try { localStorage.setItem(STORAGE_KEY, payload); } catch (_) {}
    }, 240);
  }

  function flushQueue() {
    if (!queue.length) return;
    var existing = safeRead();
    var merged = existing.concat(queue).slice(-MAX_EVENTS);
    queue.length = 0;
    eventCounts.clear();
    queueWrite(merged);
  }

  function scheduleFlush() {
    if (typeof globalThis.requestIdleCallback === 'function') {
      globalThis.requestIdleCallback(flushQueue, { timeout: 350 });
    } else {
      setTimeout(flushQueue, 180);
    }
  }

  function pushEvent(type, detail) {
    var name = String(type || 'event');
    if (REPETITIVE_EVENTS.has(name)) {
      var key = name + ':' + String(detail && detail.view ? detail.view : '') + ':' + String(detail && detail.target ? detail.target : '');
      var seen = Number(eventCounts.get(key) || 0);
      if (seen >= 3) return;
      eventCounts.set(key, seen + 1);
    }

    queue.push({
      t: new Date().toISOString(),
      type: name,
      view: String(detail && detail.view || ''),
      target: String(detail && detail.target || '')
    });
    if (typeof helpers.trackAnalyticsEvent === 'function') helpers.trackAnalyticsEvent();
    if (queue.length >= 12) flushQueue();
    else scheduleFlush();
  }

  var clickDebounce = null;
  safeOn(document, 'click', function (event) {
    if (clickDebounce) clearTimeout(clickDebounce);
    clickDebounce = setTimeout(function () {
      var target = event && event.target && event.target.closest ? event.target.closest('button, a, [data-view], [data-ux-action]') : null;
      if (!target) return;
      pushEvent('ui:click', {
        view: document.querySelector('.view.active')?.id || '',
        target: target.id || target.dataset.view || target.dataset.uxAction || target.tagName
      });
    }, 200);
  }, { passive: true });

  safeOn(document, 'epi:viewchange', function (event) {
    pushEvent('nav:viewchange', {
      view: event && event.detail && event.detail.view ? event.detail.view : ''
    });
  });

  safeOn(document, 'submit', function (event) {
    var formId = event && event.target && event.target.id ? event.target.id : 'form';
    pushEvent('form:submit', { view: document.querySelector('.view.active')?.id || '', target: formId });
  }, { capture: true });

  safeOn(document, 'epi:delivery-submit-start', function () {
    pushEvent('flow:start', { view: 'entregas-view', target: 'delivery' });
  });
  safeOn(document, 'epi:delivery-submit-success', function () {
    pushEvent('flow:complete', { view: 'entregas-view', target: 'delivery' });
  });
  safeOn(document, 'epi:delivery-submit-error', function () {
    pushEvent('form:error', { view: 'entregas-view', target: 'delivery' });
  });
  safeOn(document, 'click', function (event) {
    var target = event && event.target && event.target.closest ? event.target.closest('#phase43-confirm, [data-phase44-confirm-yes], [data-confirm-action]') : null;
    if (!target) return;
    pushEvent('flow:confirm', { view: document.querySelector('.view.active')?.id || '', target: target.id || 'confirm' });
  });

  safeOn(globalThis, 'beforeunload', flushQueue);
})();
