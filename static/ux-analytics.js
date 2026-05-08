'use strict';

(function () {
  const globalScope = typeof globalThis !== 'undefined' ? globalThis : window;
  const win = typeof window !== 'undefined' ? window : null;
  const doc = typeof document !== 'undefined' ? document : null;
  if (!win || !doc) return;
  if (globalScope.__EPI_ANALYTICS_BOUND__) return;
  globalScope.__EPI_ANALYTICS_BOUND__ = true;

  try {
  const STORAGE_KEY = 'epi.analytics.master.events';
  const LEGACY_STORAGE_KEY = 'epi.analytics.events';
  var MAX_EVENTS = 100;
  var REPETITIVE_EVENTS = new Set(['ui:click', 'ui:hover', 'ui:input', 'ui:filter', 'ui:search']);
  var MAX_BYTES = 28000;
  const DUPLICATE_WINDOW_MS = 450;
  const MAIN_CLICK_DEBOUNCE_MS = 600;
  const FLOW_ABANDON_TIMEOUT_MS = 15000;
  const SESSION_KEY = (globalScope.STORAGE_KEYS && globalScope.STORAGE_KEYS.session) || 'epi-session-v4';
  const helpers = globalScope.__EPI_FRONTEND_HELPERS__ || {};

  function safeCall(fn, fallback) {
    try {
      return fn();
    } catch (_error) {
      return fallback;
    }
  }

  function normalizeRole(role) {
    return String(role || '')
      .trim()
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/\s+/g, '_');
  }

  function isMasterRole(role) {
    const normalized = normalizeRole(role);
    return normalized === 'master_admin' || normalized === 'administrador_master';
  }

  function resolveCurrentRole() {
    return safeCall(() => {
      const appStateRole = globalScope.__EPI_APP_STATE__?.user?.role;
      if (appStateRole) return appStateRole;
      const raw = win.localStorage.getItem(SESSION_KEY);
      if (!raw) return '';
      const parsed = JSON.parse(raw);
      return parsed?.role || '';
    }, '');
  }

  function canAccessAnalytics() {
    return isMasterRole(resolveCurrentRole());
  }

  function parseFlagValue(value) {
    if (value === '1') return true;
    if (value === '0') return false;
    return null;
  }

  function isEnabledForMaster() {
    return safeCall(() => {
      if (!canAccessAnalytics()) return false;
      if (typeof helpers.getFeatureFlag === 'function') {
        return helpers.getFeatureFlag('ux_analytics_enabled', { defaultValue: false, allowStorage: true }) === true;
      }
      const params = new URLSearchParams(win.location.search);
      const query = parseFlagValue(params.get('ux_analytics'));
      return query === true;
    }, false);
  }

  function shouldResetByQuery() {
    return safeCall(() => {
      if (!canAccessAnalytics()) return false;
      const params = new URLSearchParams(win.location.search);
      return parseFlagValue(params.get('ux_analytics_reset')) === true;
    }, false);
  }

  function safeStorageRead() {
    return safeCall(() => {
      const raw = win.localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    }, []);
  }

  function safeStorageWrite(events) {
    return safeCall(() => {
      win.localStorage.setItem(STORAGE_KEY, JSON.stringify(events));
      return true;
    }, false);
  }

  function clearAnalyticsStorage() {
    safeCall(() => {
      win.localStorage.removeItem(STORAGE_KEY);
      win.localStorage.removeItem(LEGACY_STORAGE_KEY);
      return true;
    }, false);
  }

  function ensureUnauthorizedStorageIsNotExposed() {
    if (canAccessAnalytics()) return;
    clearAnalyticsStorage();
  }

  function getActiveView() {
    return safeCall(() => doc.querySelector('.view.active')?.id?.replace(/-view$/, '') || 'unknown', 'unknown');
  }

  const analyticsState = {
    enabled: isEnabledForMaster(),
    queue: [],
    queueScheduled: false,
    recentEvents: new Map(),
    currentView: getActiveView(),
    viewOpenedAt: Date.now(),
    viewUsage: {},
    flowStates: {},
    errorCountByView: {}
  };

  function enqueue(task) {
    try {
      analyticsState.queue.push(task);
      if (analyticsState.queueScheduled) return;
      analyticsState.queueScheduled = true;
      Promise.resolve().then(flushQueue);
    } catch (_error) {
      // fail-safe
    }
  }

  function flushQueue() {
    analyticsState.queueScheduled = false;
    while (analyticsState.queue.length) {
      const task = analyticsState.queue.shift();
      safeCall(() => task(), null);
    }
  }

  function shouldIgnoreDuplicate(eventName, moduleName, metadata) {
    const signature = `${eventName}|${moduleName}|${JSON.stringify(metadata || {})}`;
    const now = Date.now();
    const lastAt = analyticsState.recentEvents.get(signature) || 0;
    analyticsState.recentEvents.set(signature, now);
    if (analyticsState.recentEvents.size > 200) {
      const staleBefore = now - 3000;
      analyticsState.recentEvents.forEach((at, key) => {
        if (at < staleBefore) analyticsState.recentEvents.delete(key);
      });
    }
    return now - lastAt < DUPLICATE_WINDOW_MS;
  }

  function buildSafeMetadata(metadata) {
    const source = metadata && typeof metadata === 'object' ? metadata : {};
    const safe = {};
    Object.keys(source).forEach((key) => {
      const value = source[key];
      if (typeof value === 'boolean' || typeof value === 'number') {
        safe[key] = value;
      } else if (value == null) {
        return;
      } else {
        safe[key] = String(value).slice(0, 40).replace(/[^a-z0-9_\-:.]/gi, '_');
      }
    });
    return safe;
  }

  function pushEvent(payload) {
    enqueue(() => {
      if (!canAccessAnalytics()) return;
      const moduleName = String(payload?.module || getActiveView() || 'unknown');
      const metadata = buildSafeMetadata(payload?.metadata || {});
      const eventName = String(payload?.event || 'unknown_event');
      const name = eventName;
      if (REPETITIVE_EVENTS.has(name)) {
        if (shouldIgnoreDuplicate(eventName, moduleName, metadata)) return;
      } else if (shouldIgnoreDuplicate(eventName, moduleName, metadata)) {
        return;
      }
      const eventItem = {
        event: eventName,
        module: moduleName,
        timestamp: Number(payload?.timestamp || Date.now()),
        duration: Number(payload?.duration || 0),
        metadata
      };
      const events = safeStorageRead();
      events.push(eventItem);
      while (events.length > MAX_EVENTS) events.shift();
      safeStorageWrite(events);
    });
  }

  function markViewInteraction(type) {
    enqueue(() => {
      const view = getActiveView();
      if (!analyticsState.viewUsage[view]) {
        analyticsState.viewUsage[view] = { filtersUsed: false, searchUsed: false, formsSubmitted: 0 };
      }
      if (type === 'filter') analyticsState.viewUsage[view].filtersUsed = true;
      if (type === 'search') analyticsState.viewUsage[view].searchUsed = true;
      if (type === 'submit') analyticsState.viewUsage[view].formsSubmitted += 1;
    });
  }

  function closeCurrentView(reason) {
    enqueue(() => {
      const now = Date.now();
      const current = analyticsState.currentView || 'unknown';
      const duration = Math.max(0, now - Number(analyticsState.viewOpenedAt || now));
      const usage = analyticsState.viewUsage[current] || { filtersUsed: false, searchUsed: false, formsSubmitted: 0 };
      pushEvent({
        event: 'view_duration',
        module: current,
        timestamp: now,
        duration,
        metadata: {
          reason: reason || 'switch',
          filtersUsed: usage.filtersUsed,
          searchUsed: usage.searchUsed,
          formsSubmitted: usage.formsSubmitted
        }
      });
      analyticsState.currentView = current;
      analyticsState.viewOpenedAt = now;
    });
  }

  function openView(nextView, source) {
    enqueue(() => {
      const now = Date.now();
      analyticsState.currentView = String(nextView || getActiveView() || 'unknown');
      analyticsState.viewOpenedAt = now;
      if (!analyticsState.viewUsage[analyticsState.currentView]) {
        analyticsState.viewUsage[analyticsState.currentView] = { filtersUsed: false, searchUsed: false, formsSubmitted: 0 };
      }
      pushEvent({
        event: 'view_open',
        module: analyticsState.currentView,
        timestamp: now,
        duration: 0,
        metadata: { source: source || 'navigation' }
      });
    });
  }

  function trackViewChange(nextView, source) {
    enqueue(() => {
      const previous = analyticsState.currentView || getActiveView();
      const target = String(nextView || getActiveView() || 'unknown');
      if (previous === target) return;
      closeCurrentView('view_change');
      pushEvent({
        event: 'view_change',
        module: target,
        timestamp: Date.now(),
        duration: 0,
        metadata: { source: source || 'menu' }
      });
      openView(target, source || 'view_change');
    });
  }

  function detectPrimaryAction(button) {
    if (!button) return { isPrimary: false, source: 'none', action: 'none' };
    const explicitAction = String(button.dataset.analyticsAction || button.dataset.primaryAction || '').trim();
    if (explicitAction) {
      return { isPrimary: true, source: 'data_attribute', action: explicitAction.toLowerCase().slice(0, 30) };
    }
    const fallbackPrimary = button.classList.contains('btn-primary') || button.classList.contains('primary');
    return {
      isPrimary: fallbackPrimary,
      source: fallbackPrimary ? 'class_fallback' : 'none',
      action: fallbackPrimary ? 'primary_button' : 'none'
    };
  }

  function trackMainButtonClick(button) {
    enqueue(() => {
      const now = Date.now();
      const primary = detectPrimaryAction(button);
      if (!primary.isPrimary) return;
      const key = `main_btn:${primary.source}:${primary.action}`;
      const lastAt = analyticsState.recentEvents.get(key) || 0;
      analyticsState.recentEvents.set(key, now);
      if (now - lastAt < MAIN_CLICK_DEBOUNCE_MS) return;
      pushEvent({
        event: 'main_button_click',
        module: getActiveView(),
        timestamp: now,
        duration: 0,
        metadata: {
          source: primary.source,
          interactionCount: 1
        }
      });
    });
  }

  function flowStart(flowName, details) {
    enqueue(() => {
      const key = String(flowName || 'generic_action');
      analyticsState.flowStates[key] = {
        startedAt: Date.now(),
        view: getActiveView()
      };
      pushEvent({
        event: 'flow_start',
        module: getActiveView(),
        timestamp: Date.now(),
        duration: 0,
        metadata: {
          flow: key,
          source: details?.source || 'custom_event'
        }
      });
    });
  }

  function flowFinish(flowName, status, extra) {
    enqueue(() => {
      const key = String(flowName || 'generic_action');
      const start = analyticsState.flowStates[key];
      const now = Date.now();
      const duration = start ? Math.max(0, now - start.startedAt) : 0;
      delete analyticsState.flowStates[key];
      pushEvent({
        event: status === 'success' ? 'flow_success' : 'flow_error',
        module: getActiveView(),
        timestamp: now,
        duration,
        metadata: {
          flow: key,
          statusCategory: status === 'success' ? 'ok' : 'error',
          source: extra?.source || 'custom_event'
        }
      });
    });
  }

  function flowAbandonOnUnload() {
    enqueue(() => {
      const now = Date.now();
      Object.keys(analyticsState.flowStates).forEach((key) => {
        const flow = analyticsState.flowStates[key];
        if (!flow) return;
        const elapsed = Math.max(0, now - Number(flow.startedAt || now));
        if (elapsed < FLOW_ABANDON_TIMEOUT_MS) return;
        pushEvent({
          event: 'flow_abandon',
          module: flow.view || getActiveView(),
          timestamp: now,
          duration: elapsed,
          metadata: { flow: key, source: 'beforeunload' }
        });
      });
    });
  }

  function trackError(errorType) {
    enqueue(() => {
      const view = getActiveView();
      analyticsState.errorCountByView[view] = Number(analyticsState.errorCountByView[view] || 0) + 1;
      const monitorSnapshot = safeCall(() => globalScope.__EPI_MONITORING__?.getSnapshot?.(), null);
      pushEvent({
        event: 'screen_error',
        module: view,
        timestamp: Date.now(),
        duration: 0,
        metadata: {
          type: errorType,
          errorCountByView: analyticsState.errorCountByView[view],
          monitorErrorCount: Number(monitorSnapshot?.errorsByModule?.[`${view}-view`] || monitorSnapshot?.errorsByModule?.[view] || 0),
          hasAutoRollback: Boolean(monitorSnapshot?.autoRollbackActive)
        }
      });
    });
  }

  function bindEventListeners() {
    safeCall(() => {
      doc.addEventListener('epi:viewchange', (event) => {
        trackViewChange(event?.detail?.view, 'epi:viewchange');
      });
    }, null);

    safeCall(() => {
      doc.addEventListener('click', (event) => {
        const button = event?.target?.closest('button, [role="button"], [data-analytics-action], [data-primary-action]');
        if (!button) return;
        trackMainButtonClick(button);
      }, { passive: true });
    }, null);

    safeCall(() => {
      doc.addEventListener('submit', (event) => {
        const form = event?.target;
        if (!form || form.tagName !== 'FORM') return;
        markViewInteraction('submit');
        pushEvent({
          event: 'form_submit',
          module: getActiveView(),
          timestamp: Date.now(),
          duration: 0,
          metadata: {
            formsSubmitted: 1,
            fieldCount: Number(form.querySelectorAll('input,select,textarea').length || 0)
          }
        });
        pushEvent('form:submit', { module: getActiveView(), metadata: { source: 'submit_listener' } });
      }, true);
    }, null);

    safeCall(() => {
      doc.addEventListener('change', (event) => {
        const target = event?.target;
        if (!target) return;
        const fieldId = `${target.id || ''} ${target.name || ''}`.toLowerCase();
        if (!fieldId.includes('filter') && !fieldId.includes('filtro')) return;
        markViewInteraction('filter');
        pushEvent({
          event: 'filters_use',
          module: getActiveView(),
          timestamp: Date.now(),
          duration: 0,
          metadata: { filtersUsed: true, interactionCount: 1 }
        });
      }, true);
    }, null);

    safeCall(() => {
      let searchDebounce = null;
      doc.addEventListener('input', (event) => {
        const target = event?.target;
        if (!target) return;
        const isSearch = String(target.type || '').toLowerCase() === 'search'
          || /search|busca/.test(`${target.id || ''} ${target.name || ''}`.toLowerCase());
        if (!isSearch) return;
        markViewInteraction('search');
        if (searchDebounce) win.clearTimeout(searchDebounce);
        searchDebounce = win.setTimeout(() => {
          pushEvent({
            event: 'search_use',
            module: getActiveView(),
            timestamp: Date.now(),
            duration: 0,
            metadata: { searchUsed: true, interactionCount: 1 }
          });
        }, 300);
      }, { passive: true });
    }, null);

    safeCall(() => {
      doc.addEventListener('epi:delivery-submit-start', () => {
        flowStart('delivery_epi', { source: 'epi:delivery-submit-start' });
        pushEvent('flow:start', { module: getActiveView(), metadata: { source: 'epi:delivery-submit-start' } });
      });
      doc.addEventListener('epi:delivery-submit-success', () => {
        flowFinish('delivery_epi', 'success', { source: 'epi:delivery-submit-success' });
        pushEvent('flow:complete', { module: getActiveView(), metadata: { source: 'epi:delivery-submit-success' } });
      });
      doc.addEventListener('epi:delivery-submit-error', () => {
        flowFinish('delivery_epi', 'error', { source: 'epi:delivery-submit-error' });
        pushEvent('form:error', { module: getActiveView(), metadata: { source: 'epi:delivery-submit-error' } });
      });
      doc.addEventListener('epi:action-success', () => {
        flowFinish('generic_action', 'success', { source: 'epi:action-success' });
      });
      doc.addEventListener('epi:action-error', () => {
        flowFinish('generic_action', 'error', { source: 'epi:action-error' });
      });
    }, null);

    safeCall(() => {
      doc.addEventListener('click', (event) => {
        const target = event?.target?.closest?.('#phase43-confirm, [data-phase44-confirm-yes], [data-confirm-action]');
        if (!target) return;
        pushEvent('flow:confirm', { module: getActiveView(), metadata: { source: 'confirm_click' } });
      }, { passive: true });
    }, null);

    safeCall(() => {
      win.addEventListener('error', () => {
        trackError('window_error');
      });
      win.addEventListener('unhandledrejection', () => {
        trackError('unhandled_rejection');
      });
      win.addEventListener('beforeunload', () => {
        closeCurrentView('beforeunload');
        flowAbandonOnUnload();
      });
      doc.addEventListener('visibilitychange', () => {
        if (doc.visibilityState !== 'hidden') return;
        closeCurrentView('hidden');
      });
    }, null);
  }

  function getEventsForApi() {
    if (!canAccessAnalytics()) {
      ensureUnauthorizedStorageIsNotExposed();
      return { allowed: false, events: [] };
    }
    return { allowed: true, events: safeStorageRead() };
  }

  const analyticsApi = Object.freeze({
    isEnabled: () => analyticsState.enabled && canAccessAnalytics(),
    getEvents: () => getEventsForApi(),
    clearEvents: () => {
      if (!canAccessAnalytics()) return { allowed: false, events: [] };
      safeStorageWrite([]);
      return { allowed: true, events: [] };
    },
    track: (eventName, metadata) => {
      if (!canAccessAnalytics() || !analyticsState.enabled) return false;
      pushEvent({ event: String(eventName || 'custom_event'), module: getActiveView(), timestamp: Date.now(), duration: 0, metadata });
      return true;
    },
    enqueueFlush: () => {
      if (!canAccessAnalytics() || !analyticsState.enabled) return false;
      enqueue(() => {
        // fase futura: envio com navigator.sendBeacon
      });
      return true;
    }
  });

  Object.defineProperty(globalScope, '__EPI_ANALYTICS__', {
    value: analyticsApi,
    writable: false,
    configurable: false,
    enumerable: false
  });

  if (shouldResetByQuery()) {
    clearAnalyticsStorage();
  }

  ensureUnauthorizedStorageIsNotExposed();

  if (!analyticsState.enabled) return;
  if (!canAccessAnalytics()) return;

  bindEventListeners();
  openView(analyticsState.currentView, 'initial');

  } catch (e) {
    console.warn('[analytics] erro controlado', e);
  }
})();
