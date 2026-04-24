(function () {
  var helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
  var ensureModuleBound = typeof helpers.ensureModuleBound === 'function'
    ? helpers.ensureModuleBound
    : function () { return true; };
  if (!ensureModuleBound('phase46_navigation')) return;

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
      if (typeof helpers.getFeatureFlag === 'function') {
        var hierarchy = helpers.getFeatureFlag('ux_hierarchical_navigation_enabled', { defaultValue: false, allowStorage: true });
        var multitab = helpers.getFeatureFlag('ux_multitab_navigation_enabled', { defaultValue: false, allowStorage: true });
        return hierarchy && !multitab;
      }
      var params = new URLSearchParams(globalThis.location.search);
      return params.get('ux_hierarchy') === '1';
    } catch (_error) {
      return false;
    }
  }

  if (!isEnabled()) return;

  var stack = Array.isArray(globalThis.__EPI_VIEW_STACK__) ? globalThis.__EPI_VIEW_STACK__ : [];
  globalThis.__EPI_VIEW_STACK__ = stack;

  var refs = {
    topbar: document.querySelector('.topbar'),
    backButton: document.getElementById('hierarchy-back-btn'),
    breadcrumb: document.getElementById('hierarchy-breadcrumb'),
    breadcrumbWrap: document.getElementById('hierarchy-breadcrumb-wrap')
  };

  function closeTransientUi() {
    try {
      document.querySelectorAll('[data-ui-dropdown].is-open').forEach(function (node) {
        node.classList.remove('is-open');
        var trigger = node.querySelector('[data-dropdown-trigger]');
        var panel = node.querySelector('[data-dropdown-panel]');
        if (trigger) trigger.setAttribute('aria-expanded', 'false');
        if (panel) panel.hidden = true;
      });
      document.querySelectorAll('.delivery-ux-dropdown.open').forEach(function (el) {
        el.classList.remove('open');
      });
      document.querySelectorAll('.signature-modal.is-open, .modal.is-open').forEach(function (modal) {
        modal.classList.remove('is-open');
        modal.setAttribute('aria-hidden', 'true');
      });
      document.querySelectorAll('.phase2-modal:not([hidden])').forEach(function (node) {
        node.hidden = true;
      });
    } catch (error) {
      console.warn('[phase46] closeTransientUi', error);
    }
  }

  function activeViewName() {
    var node = document.querySelector('.view.active');
    return (node && node.id ? node.id.replace(/-view$/, '') : '') || 'dashboard';
  }

  function activeViewLabel(view) {
    var link = document.querySelector('.menu-link[data-view="' + view + '"]');
    return (link && link.textContent ? link.textContent.trim() : '') || 'Dashboard';
  }

  function captureContext() {
    var data = {};
    try {
      var activeView = document.querySelector('.view.active');
      if (!activeView) return data;
      var key = activeView.id || activeViewName();
      var entries = {};
      activeView.querySelectorAll('input[id], select[id], textarea[id]').forEach(function (field) {
        if (!field.id) return;
        if (field.type === 'password') return;
        entries[field.id] = field.type === 'checkbox' ? Boolean(field.checked) : field.value;
      });
      data[key] = {
        scrollY: globalThis.scrollY || 0,
        fields: entries
      };
    } catch (error) {
      console.warn('[phase46] captureContext', error);
    }
    return data;
  }

  function restoreContext(node) {
    if (!node || !node.context) return;
    try {
      Object.keys(node.context).forEach(function (key) {
        var viewContext = node.context[key];
        Object.keys(viewContext.fields || {}).forEach(function (fieldId) {
          var field = document.getElementById(fieldId);
          if (!field) return;
          var nextValue = viewContext.fields[fieldId];
          if (field.type === 'checkbox') {
            field.checked = Boolean(nextValue);
          } else {
            field.value = nextValue == null ? '' : String(nextValue);
          }
        });
      });
      globalThis.requestAnimationFrame(function () {
        globalThis.scrollTo({ top: Number(node.context[Object.keys(node.context)[0]]?.scrollY || 0), behavior: 'auto' });
      });
    } catch (error) {
      console.warn('[phase46] restoreContext', error);
    }
  }

  function drawBreadcrumb() {
    if (!refs.breadcrumb || !refs.backButton || !refs.breadcrumbWrap) return;
    var segments = stack.map(function (item) {
      return item && item.label ? item.label : 'Área';
    });
    refs.breadcrumb.innerHTML = segments.map(function (label, index) {
      var last = index === segments.length - 1;
      var safe = String(label)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
      return '<span class="hierarchy-crumb' + (last ? ' is-active' : '') + '">' + safe + '</span>';
    }).join('<span class="hierarchy-sep">&gt;</span>');
    var depth = Math.max(stack.length - 1, 0);
    refs.backButton.hidden = depth < 1;
    refs.backButton.disabled = depth < 1;
    refs.breadcrumbWrap.hidden = stack.length < 1;
    document.body.classList.toggle('ux-hierarchy-enabled', true);
    document.body.classList.toggle('ux-hierarchy-has-depth', depth > 0);
  }


  function pulseTransition() {
    try {
      var active = document.querySelector('.view.active');
      if (!active) return;
      active.classList.remove('hierarchy-view-enter');
      void active.offsetWidth;
      active.classList.add('hierarchy-view-enter');
    } catch (_error) {
      // no-op
    }
  }

  function normalizeUrl(pathSegments) {
    var url = new URL(globalThis.location.href);
    if (!pathSegments || !pathSegments.length) {
      url.searchParams.delete('hpath');
      return url;
    }
    url.searchParams.set('hpath', pathSegments.join('/'));
    return url;
  }

  function rootPush(view) {
    stack.length = 0;
    stack.push({ type: 'view', id: view, label: activeViewLabel(view), context: captureContext() });
    drawBreadcrumb();
    pulseTransition();
  }

  function pushNode(node, options) {
    var opts = options || {};
    closeTransientUi();
    stack.push({
      type: node.type || 'subview',
      id: node.id || ('sub-' + Date.now()),
      label: node.label || 'Detalhes',
      context: captureContext()
    });
    var url = normalizeUrl(stack.slice(1).map(function (item) { return item.id; }));
    try {
      globalThis.history.pushState({ epiHierarchy: true, stackDepth: stack.length }, '', url);
    } catch (_error) {
      if (!opts.silent) globalThis.location.assign(url.toString());
      return;
    }
    drawBreadcrumb();
    pulseTransition();

    var targetSelector = node.target;
    var source = node.source;
    if (targetSelector && source && globalThis.htmx && typeof globalThis.htmx.ajax === 'function') {
      try {
        globalThis.htmx.ajax('GET', source, {
          target: targetSelector,
          swap: node.swap || 'innerHTML transition:true'
        });
      } catch (error) {
        console.warn('[phase46] htmx fallback', error);
      }
    }
  }

  function popNode() {
    if (stack.length <= 1) return false;
    stack.pop();
    var node = stack[stack.length - 1];
    restoreContext(node);
    drawBreadcrumb();
    pulseTransition();
    return true;
  }

  function pushFromTrigger(trigger) {
    if (!trigger) return;
    var label = trigger.dataset.hierarchyLabel || trigger.getAttribute('aria-label') || trigger.textContent || 'Detalhes';
    var source = trigger.getAttribute('hx-get') || trigger.dataset.hxGet || '';
    var target = trigger.getAttribute('hx-target') || trigger.dataset.hxTarget || '';
    pushNode({
      id: trigger.dataset.hierarchyId || label.trim().toLowerCase().replace(/\s+/g, '-'),
      label: label.trim(),
      source: source,
      target: target,
      swap: trigger.getAttribute('hx-swap') || trigger.dataset.hxSwap || ''
    });
  }

  function annotateBuiltins() {
    var fichaViewBtn = document.getElementById('ficha-btn-visualizar');
    if (fichaViewBtn && !fichaViewBtn.dataset.hierarchyLabel) {
      fichaViewBtn.dataset.hierarchyPush = '1';
      fichaViewBtn.dataset.hierarchyId = 'ficha';
      fichaViewBtn.dataset.hierarchyLabel = 'Ficha';
      fichaViewBtn.dataset.hxTarget = '#ficha-view';
      fichaViewBtn.dataset.hxSwap = 'innerHTML transition:true';
    }

    var fichaPrintBtn = document.getElementById('ficha-btn-imprimir');
    if (fichaPrintBtn && !fichaPrintBtn.dataset.hierarchyLabel) {
      fichaPrintBtn.dataset.hierarchyPush = '1';
      fichaPrintBtn.dataset.hierarchyId = 'historico';
      fichaPrintBtn.dataset.hierarchyLabel = 'Histórico';
    }

    var table = document.getElementById('employees-table');
    if (table) {
      table.querySelectorAll('[data-employee-edit]').forEach(function (button) {
        if (button.dataset.hierarchyPush === '1') return;
        var row = button.closest('tr');
        var employeeName = row && row.cells && row.cells[1] ? row.cells[1].textContent.trim() : 'Colaborador';
        button.dataset.hierarchyPush = '1';
        button.dataset.hierarchyId = 'colaborador-' + String(button.dataset.employeeEdit || '').trim();
        button.dataset.hierarchyLabel = employeeName || 'Colaborador';
      });
    }
  }

  function bind() {
    if (document.body && document.body.dataset.epiPhase46Bound === '1') return;
    if (document.body) document.body.dataset.epiPhase46Bound = '1';

    safeOn(document, 'epi:viewchange', function (event) {
      var startTs = typeof helpers.markRenderStart === 'function' ? helpers.markRenderStart() : 0;
      var view = event && event.detail && event.detail.view ? event.detail.view : activeViewName();
      rootPush(view);
      if (typeof helpers.markRenderEnd === 'function') helpers.markRenderEnd(startTs);
    });

    safeOn(document, 'click', function (event) {
      var trigger = event.target && event.target.closest ? event.target.closest('[data-hierarchy-push="1"]') : null;
      if (!trigger) return;
      if (trigger.dataset.hierarchySkip === '1') return;
      pushFromTrigger(trigger);
    }, { passive: true });

    safeOn(refs.backButton, 'click', function (event) {
      event.preventDefault();
      if (stack.length <= 1) {
        globalThis.history.back();
        return;
      }
      if (globalThis.history.length > 1) {
        globalThis.history.back();
      } else {
        popNode();
      }
    });

    safeOn(globalThis, 'popstate', function (event) {
      if (!event || !event.state || !event.state.epiHierarchy) return;
      if (!popNode()) {
        drawBreadcrumb();
      }
    });

    safeOn(document.body, 'htmx:afterSwap', function () {
      annotateBuiltins();
      drawBreadcrumb();
    });

    annotateBuiltins();
    rootPush(activeViewName());
  }

  if (document.readyState === 'loading') {
    safeOn(document, 'DOMContentLoaded', bind, { once: true });
  } else {
    bind();
  }
})();
