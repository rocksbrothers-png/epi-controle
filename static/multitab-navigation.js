(function () {
  if (globalThis.__EPI_MULTITAB_NAV_BOUND__) return;
  globalThis.__EPI_MULTITAB_NAV_BOUND__ = true;

  var helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
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

  function reportError(context, error) {
    if (typeof helpers.reportNonCriticalError === 'function') {
      helpers.reportNonCriticalError(context, error);
      return;
    }
    if (globalThis.__EPI_DEBUG__) console.warn(context, error);
  }

  function isEnabled() {
    try {
      if (typeof helpers.getFeatureFlag === 'function') {
        return helpers.getFeatureFlag('ux_multitab_navigation_enabled', { defaultValue: false, allowStorage: true }) === true;
      }
      return new URLSearchParams(globalThis.location.search).get('ux_multitab') === '1';
    } catch (_error) {
      return false;
    }
  }

  if (!isEnabled()) return;

  var navApi = globalThis.__EPI_APP_NAV_API__ || {};
  if (typeof navApi.showView !== 'function') return;

  var refs = {
    root: document.getElementById('multitab-nav-root'),
    tabs: document.getElementById('multitab-nav-tabs'),
    back: document.getElementById('multitab-back-btn'),
    breadcrumb: document.getElementById('multitab-breadcrumb')
  };
  if (!refs.root || !refs.tabs || !refs.back || !refs.breadcrumb) return;

  var prefersReducedMotion = false;
  try {
    prefersReducedMotion = Boolean(globalThis.matchMedia && globalThis.matchMedia('(prefers-reduced-motion: reduce)').matches);
  } catch (_error) {
    prefersReducedMotion = false;
  }

  var lastTabId = 0;
  var tabs = [];
  var activeTabId = '';
  var restoringPopState = false;
  var tabAbortControllers = new Map();

  function closeTransientUi() {
    try {
      document.querySelectorAll('[data-ui-dropdown].is-open').forEach(function (node) {
        node.classList.remove('is-open');
        var trigger = node.querySelector('[data-dropdown-trigger]');
        var panel = node.querySelector('[data-dropdown-panel]');
        if (trigger) trigger.setAttribute('aria-expanded', 'false');
        if (panel) panel.hidden = true;
      });
      document.querySelectorAll('.delivery-ux-dropdown.open').forEach(function (node) {
        node.classList.remove('open');
      });
      document.querySelectorAll('.signature-modal.is-open, .modal.is-open').forEach(function (modal) {
        modal.classList.remove('is-open');
        modal.setAttribute('aria-hidden', 'true');
      });
      document.querySelectorAll('.phase2-modal:not([hidden])').forEach(function (node) {
        node.hidden = true;
      });
    } catch (error) {
      reportError('[multitab] closeTransientUi', error);
    }
  }

  function makeTabId() {
    lastTabId += 1;
    return 'tab-' + String(lastTabId);
  }

  function getViewLabel(view) {
    var link = document.querySelector('.menu-link[data-view="' + view + '"]');
    return (link && link.textContent ? link.textContent.trim() : '') || 'Dashboard';
  }

  function getTabByView(view) {
    return tabs.find(function (tab) { return tab.view === view; }) || null;
  }

  function getTabById(tabId) {
    return tabs.find(function (tab) { return tab.id === tabId; }) || null;
  }

  function getActiveTab() {
    return getTabById(activeTabId);
  }

  function captureViewContext(view) {
    var payload = { fields: {}, scrollTop: 0 };
    try {
      var viewNode = document.getElementById(view + '-view');
      if (!viewNode) return payload;
      payload.scrollTop = Number(refsMainScrollTop());
      viewNode.querySelectorAll('input[id], select[id], textarea[id]').forEach(function (field) {
        if (!field.id || field.type === 'password' || field.type === 'hidden') return;
        if (field.type === 'checkbox' || field.type === 'radio') {
          payload.fields[field.id] = Boolean(field.checked);
          return;
        }
        payload.fields[field.id] = String(field.value || '');
      });
    } catch (error) {
      reportError('[multitab] captureViewContext', error);
    }
    return payload;
  }

  function restoreViewContext(tab) {
    if (!tab || !tab.context) return;
    try {
      Object.keys(tab.context.fields || {}).forEach(function (fieldId) {
        var field = document.getElementById(fieldId);
        if (!field) return;
        var nextValue = tab.context.fields[fieldId];
        if (field.type === 'checkbox' || field.type === 'radio') {
          field.checked = Boolean(nextValue);
        } else {
          field.value = nextValue == null ? '' : String(nextValue);
        }
      });
      var top = Number(tab.context.scrollTop || 0);
      globalThis.requestAnimationFrame(function () {
        var target = refsMainScrollContainer();
        if (target) {
          target.scrollTop = top;
        } else {
          globalThis.scrollTo({ top: top, behavior: 'auto' });
        }
      });
    } catch (error) {
      reportError('[multitab] restoreViewContext', error);
    }
  }

  function refsMainScrollContainer() {
    return document.getElementById('main-content');
  }

  function refsMainScrollTop() {
    var container = refsMainScrollContainer();
    return container ? container.scrollTop : (globalThis.scrollY || 0);
  }

  function currentStack(tab) {
    if (!tab.stack.length) {
      tab.stack.push({ view: tab.view, label: getViewLabel(tab.view), url: navApi.buildNavigationUrl(tab.view).toString() });
    }
    return tab.stack;
  }

  function drawBreadcrumb(tab) {
    var stack = currentStack(tab);
    refs.breadcrumb.innerHTML = stack.map(function (item, index) {
      var active = index === stack.length - 1 ? ' is-active' : '';
      var safeLabel = String(item.label || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      return '<span class="multitab-crumb' + active + '">' + safeLabel + '</span>';
    }).join('<span class="multitab-sep">›</span>');
    refs.back.disabled = stack.length <= 1;
    refs.back.hidden = stack.length <= 1;
  }

  function drawTabs() {
    refs.tabs.innerHTML = tabs.map(function (tab) {
      var active = tab.id === activeTabId;
      var loading = tab.loading ? '<span class="multitab-loader" aria-hidden="true"></span>' : '';
      var closeDisabled = tabs.length <= 1 ? ' disabled' : '';
      return '<button class="multitab-tab' + (active ? ' is-active' : '') + '" type="button" data-tab-id="' + tab.id + '" aria-current="' + (active ? 'page' : 'false') + '">' +
        '<span class="multitab-tab-label">' + escapeHtml(tab.title) + '</span>' + loading +
        '<span class="multitab-tab-close" role="button" aria-label="Fechar aba" data-tab-close="' + tab.id + '"' + closeDisabled + '>×</span>' +
        '</button>';
    }).join('');
    if (!tabs.length) {
      refs.tabs.innerHTML = '<div class="multitab-empty">Abra uma área no menu lateral para iniciar.</div>';
    }
  }

  function escapeHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function updateHistory(tab, mode) {
    try {
      var url = new URL(tab.url || navApi.buildNavigationUrl(tab.view).toString(), globalThis.location.origin);
      url.searchParams.set('tab', tab.id);
      var state = {
        epiMultitab: true,
        tabId: tab.id,
        view: tab.view,
        stack: tab.stack.slice()
      };
      if (mode === 'replace') {
        globalThis.history.replaceState(state, '', url.toString());
      } else {
        globalThis.history.pushState(state, '', url.toString());
      }
    } catch (error) {
      reportError('[multitab] updateHistory', error);
    }
  }

  function runSafeRebinds() {
    try {
      if (typeof navApi.rerunSafeSetups === 'function') navApi.rerunSafeSetups();
    } catch (error) {
      reportError('[multitab] runSafeRebinds', error);
    }
  }

  function markLoading(tabId, active) {
    var tab = getTabById(tabId);
    if (!tab) return;
    tab.loading = Boolean(active);
    drawTabs();
  }

  function activateTab(tabId, options) {
    var opts = options || {};
    var tab = getTabById(tabId);
    if (!tab) return;

    var current = getActiveTab();
    if (current && current.id !== tab.id) {
      current.context = captureViewContext(current.view);
    }
    activeTabId = tab.id;
    closeTransientUi();

    var controller = tabAbortControllers.get(tab.id);
    if (controller) {
      controller.abort();
      tabAbortControllers.delete(tab.id);
    }
    controller = new AbortController();
    tabAbortControllers.set(tab.id, controller);

    markLoading(tab.id, true);
    try {
      navApi.showView(tab.view, { partial: true, historyMode: 'replace' });
      restoreViewContext(tab);
      drawTabs();
      drawBreadcrumb(tab);
      runSafeRebinds();
      if (!prefersReducedMotion) {
        var node = document.getElementById(tab.view + '-view');
        if (node) {
          node.classList.remove('multitab-view-enter');
          void node.offsetWidth;
          node.classList.add('multitab-view-enter');
        }
      }
      if (!opts.skipHistory && !restoringPopState) {
        updateHistory(tab, opts.historyMode === 'replace' ? 'replace' : 'push');
      }
    } catch (error) {
      reportError('[multitab] activateTab', error);
      try {
        globalThis.location.assign(navApi.buildNavigationUrl(tab.view).toString());
      } catch (_error) {
        // no-op
      }
    } finally {
      markLoading(tab.id, false);
      if (!controller.signal.aborted) tabAbortControllers.delete(tab.id);
    }
  }

  function hasUnsavedForm(view) {
    try {
      var root = document.getElementById(view + '-view');
      if (!root) return false;
      return Array.from(root.querySelectorAll('form')).some(function (form) {
        if (form.dataset && form.dataset.ignoreUnsaved === '1') return false;
        if (form.dataset && form.dataset.dirty === '1') return true;
        return Array.from(form.querySelectorAll('input, textarea, select')).some(function (field) {
          if (field.type === 'password' || field.type === 'hidden' || field.disabled) return false;
          if (field.type === 'checkbox' || field.type === 'radio') {
            return field.checked !== field.defaultChecked;
          }
          return String(field.value || '') !== String(field.defaultValue || '');
        });
      });
    } catch (_error) {
      return false;
    }
  }

  function closeTab(tabId) {
    if (tabs.length <= 1) {
      showInfo('Não é possível fechar a última aba.');
      return;
    }
    var idx = tabs.findIndex(function (tab) { return tab.id === tabId; });
    if (idx < 0) return;
    var tab = tabs[idx];
    if (hasUnsavedForm(tab.view) && !globalThis.confirm('Existem alterações não salvas. Deseja fechar esta aba?')) {
      return;
    }
    var controller = tabAbortControllers.get(tab.id);
    if (controller) controller.abort();
    tabAbortControllers.delete(tab.id);

    tabs.splice(idx, 1);
    if (tab.id === activeTabId) {
      var previous = tabs[Math.max(0, idx - 1)] || tabs[0];
      activeTabId = previous.id;
      activateTab(previous.id, { historyMode: 'replace' });
      return;
    }
    drawTabs();
  }

  function showInfo(message) {
    try {
      if (typeof globalThis.showToast === 'function') {
        globalThis.showToast(message, 'warning');
        return;
      }
      console.info(message);
    } catch (_error) {
      console.info(message);
    }
  }

  function ensureTab(view, options) {
    var existing = getTabByView(view);
    if (existing) {
      activateTab(existing.id, options);
      return existing;
    }
    var id = makeTabId();
    var tab = {
      id: id,
      view: view,
      title: getViewLabel(view),
      stack: [{ view: view, label: getViewLabel(view), url: navApi.buildNavigationUrl(view).toString() }],
      context: {},
      loading: false,
      url: navApi.buildNavigationUrl(view).toString()
    };
    tabs.push(tab);
    activateTab(id, options);
    return tab;
  }

  function pushInternalNode(label, url) {
    var tab = getActiveTab();
    if (!tab) return;
    var nextLabel = String(label || '').trim() || 'Detalhe';
    var nextUrl = String(url || tab.url || navApi.buildNavigationUrl(tab.view).toString());
    var stack = currentStack(tab);
    stack.push({ view: tab.view, label: nextLabel, url: nextUrl });
    tab.url = nextUrl;
    drawBreadcrumb(tab);
    updateHistory(tab, 'push');
  }

  function popInternalNode() {
    var tab = getActiveTab();
    if (!tab) return;
    if (!tab.stack || tab.stack.length <= 1) return;
    tab.stack.pop();
    var current = tab.stack[tab.stack.length - 1];
    tab.url = current.url || navApi.buildNavigationUrl(tab.view).toString();
    drawBreadcrumb(tab);
    updateHistory(tab, 'replace');
    if (current.url && current.url.indexOf('#') >= 0) {
      try {
        globalThis.location.hash = current.url.split('#')[1] || '';
      } catch (_error) {
        // no-op
      }
    }
  }

  function onMenuIntercept(event) {
    try {
      var button = event.target && event.target.closest ? event.target.closest('.menu-link[data-view]') : null;
      if (!button) return;
      if (event.defaultPrevented) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      var view = String(button.dataset.view || '').trim();
      if (!view) return;
      if (typeof navApi.canAccessView === 'function' && !navApi.canAccessView(view)) return;
      ensureTab(view, { historyMode: 'push' });
    } catch (error) {
      reportError('[multitab] onMenuIntercept', error);
    }
  }

  function bindKeyboard() {
    safeOn(document, 'keydown', function (event) {
      if (event.key === 'Escape') return;
      if (event.ctrlKey && event.key === 'Tab') {
        event.preventDefault();
        if (tabs.length <= 1) return;
        var index = tabs.findIndex(function (item) { return item.id === activeTabId; });
        var next = tabs[(index + 1) % tabs.length];
        if (next) activateTab(next.id, { historyMode: 'push' });
        return;
      }
      if (event.altKey && event.key === 'ArrowLeft') {
        event.preventDefault();
        popInternalNode();
      }
    });
  }

  function bindUi() {
    safeOn(document, 'click', onMenuIntercept, { capture: true });

    safeOn(refs.tabs, 'click', function (event) {
      var closeTarget = event.target && event.target.closest ? event.target.closest('[data-tab-close]') : null;
      if (closeTarget) {
        event.preventDefault();
        event.stopPropagation();
        closeTab(closeTarget.dataset.tabClose);
        return;
      }
      var tabTarget = event.target && event.target.closest ? event.target.closest('[data-tab-id]') : null;
      if (!tabTarget) return;
      event.preventDefault();
      activateTab(tabTarget.dataset.tabId, { historyMode: 'push' });
    });

    safeOn(refs.back, 'click', function (event) {
      event.preventDefault();
      popInternalNode();
    });

    safeOn(globalThis, 'popstate', function (event) {
      if (!event || !event.state || !event.state.epiMultitab) return;
      restoringPopState = true;
      try {
        var tab = getTabById(event.state.tabId);
        if (!tab) {
          var created = ensureTab(event.state.view || navApi.defaultView(), { skipHistory: true, historyMode: 'replace' });
          tab = created;
        }
        if (Array.isArray(event.state.stack) && event.state.stack.length) {
          tab.stack = event.state.stack.slice(0, 12).map(function (node) {
            return {
              view: tab.view,
              label: String(node.label || getViewLabel(tab.view)),
              url: String(node.url || navApi.buildNavigationUrl(tab.view).toString())
            };
          });
          tab.url = tab.stack[tab.stack.length - 1].url;
        }
        activateTab(tab.id, { skipHistory: true, historyMode: 'replace' });
      } finally {
        restoringPopState = false;
      }
    });

    safeOn(document, 'epi:multitab:push', function (event) {
      var detail = event && event.detail ? event.detail : {};
      pushInternalNode(detail.label, detail.url);
    });

    safeOn(document, 'epi:viewchange', function (event) {
      var tab = getActiveTab();
      if (!tab) return;
      var view = event && event.detail && event.detail.view ? event.detail.view : tab.view;
      if (view !== tab.view) return;
      tab.title = getViewLabel(view);
      drawTabs();
    });

    bindKeyboard();
  }

  function bootstrap() {
    document.body.classList.add('ux-multitab-enabled');
    refs.root.hidden = false;
    var initialView = typeof navApi.getCurrentView === 'function' ? navApi.getCurrentView() : navApi.defaultView();
    ensureTab(initialView, { historyMode: 'replace' });
    bindUi();
  }

  if (document.readyState === 'loading') {
    safeOn(document, 'DOMContentLoaded', bootstrap, { once: true });
  } else {
    bootstrap();
  }
})();
