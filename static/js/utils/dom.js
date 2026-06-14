'use strict';

(function () {
  if (globalThis.__EPI_UTILS_DOM_LOADED__) return;
  globalThis.__EPI_UTILS_DOM_LOADED__ = true;

  const reportNonCriticalError = typeof globalThis.reportNonCriticalError === 'function'
    ? globalThis.reportNonCriticalError
    : function (ctx, err) { if (err) console.debug(`[non-critical] ${ctx}`, err); };

  const debugLog = typeof globalThis.debugLog === 'function'
    ? globalThis.debugLog
    : function () {};

  const SAFE_ON_REGISTRY = new WeakMap();

  function isUxPerformanceHardeningEnabled() {
    try {
      const helpers = globalThis.__EPI_FRONTEND_HELPERS__;
      if (helpers && typeof helpers.getFeatureFlag === 'function') {
        return helpers.getFeatureFlag('ux_performance_hardening_enabled', { defaultValue: false });
      }
      const val = typeof safeStorageRead === 'function'
        ? safeStorageRead('ux_performance_hardening_enabled', '0')
        : '0';
      return val === '1';
    } catch (_error) {
      return false;
    }
  }

  function resolveListenerOptionSignature(options) {
    if (typeof options === 'boolean') return options ? 'capture:1' : 'capture:0';
    if (!options || typeof options !== 'object') return 'capture:0';
    return options.capture ? 'capture:1' : 'capture:0';
  }

  function safeOn(target, eventName, handler, options) {
    if (!target || typeof target.addEventListener !== 'function' || typeof handler !== 'function') return false;
    try {
      if (isUxPerformanceHardeningEnabled()) {
        const eventMap = SAFE_ON_REGISTRY.get(target) || new Map();
        const key = `${eventName}:${resolveListenerOptionSignature(options)}`;
        const handlers = eventMap.get(key) || new WeakSet();
        if (handlers.has(handler)) {
          debugLog(`[safeOn] duplicate listener blocked: ${eventName}`);
          return false;
        }
        handlers.add(handler);
        eventMap.set(key, handlers);
        SAFE_ON_REGISTRY.set(target, eventMap);
      }
      target.addEventListener(eventName, handler, options);
      if (globalThis.EPI_PERF_RUNTIME) {
        globalThis.EPI_PERF_RUNTIME.listenerCount += 1;
        if (options && typeof options === 'object' && options.signal &&
            typeof options.signal.addEventListener === 'function') {
          options.signal.addEventListener('abort', function () {
            if (globalThis.EPI_PERF_RUNTIME) {
              globalThis.EPI_PERF_RUNTIME.listenerCount = Math.max(0, globalThis.EPI_PERF_RUNTIME.listenerCount - 1);
            }
            if (typeof globalThis.renderPerfHud === 'function') globalThis.renderPerfHud();
          }, { once: true });
        }
        if (typeof globalThis.renderPerfHud === 'function') globalThis.renderPerfHud();
      }
      return true;
    } catch (error) {
      reportNonCriticalError(`[safeOn] falha ao registrar listener ${eventName}`, error);
      return false;
    }
  }

  function isViewActive(viewSelector) {
    if (!viewSelector) return false;
    const viewElement = document.querySelector(viewSelector);
    if (!viewElement) return false;
    return viewElement.classList.contains('active');
  }

  function resolveFormFieldAutocomplete(field) {
    if (!field || typeof field.getAttribute !== 'function') return null;
    const tag = String(field.tagName || '').toLowerCase();
    if (tag === 'select' || tag === 'textarea') return 'off';
    const type = String(field.getAttribute('type') || 'text').toLowerCase();
    if (['hidden', 'checkbox', 'radio', 'file', 'button', 'submit', 'reset', 'range', 'color'].includes(type)) return null;
    if (type === 'password') {
      const marker = String(field.id || field.name || '').toLowerCase();
      if (marker.includes('new') || marker.includes('confirm') || marker.includes('recovery')) return 'new-password';
      return 'current-password';
    }
    const marker = String((field.id || '') + ' ' + (field.name || '')).toLowerCase();
    if (marker.includes('user') || marker.includes('login')) return 'username';
    if (marker.includes('email')) return 'email';
    if (marker.includes('phone') || marker.includes('whatsapp') || marker.includes('tel')) return 'tel';
    if (marker === 'name' || marker.endsWith(' name') || marker.includes('-name') || marker.includes('_name')) return 'name';
    if (type === 'search' || type === 'date' || type === 'number') return 'off';
    return 'off';
  }

  function getElementIdAttribute(node) {
    try {
      return node && node.id ? String(node.id).trim() : '';
    } catch (_error) {
      return '';
    }
  }

  globalThis.safeOn = safeOn;
  globalThis.isViewActive = isViewActive;
  globalThis.resolveFormFieldAutocomplete = resolveFormFieldAutocomplete;
  globalThis.getElementIdAttribute = getElementIdAttribute;
  globalThis.SAFE_ON_REGISTRY = SAFE_ON_REGISTRY;

  const helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
  helpers.safeOn = safeOn;
  helpers.isViewActive = isViewActive;
  globalThis.__EPI_FRONTEND_HELPERS__ = helpers;
})();
