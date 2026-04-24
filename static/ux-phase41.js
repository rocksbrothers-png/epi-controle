(function phase41Iife() {
  if (globalThis.__EPI_PHASE41_BOUND__) return;
  globalThis.__EPI_PHASE41_BOUND__ = true;

  function safeOn(target, eventName, handler, options) {
    try {
      if (typeof globalThis.safeOn === 'function') return globalThis.safeOn(target, eventName, handler, options);
      if (!target || typeof target.addEventListener !== 'function') return false;
      target.addEventListener(eventName, handler, options);
      return true;
    } catch (error) {
      console.warn('[phase41] safeOn falhou', error);
      return false;
    }
  }

  function isEnabled() {
    try {
      if (typeof globalThis.getFeatureFlag === 'function') {
        return globalThis.getFeatureFlag('ux_phase41_enabled', { defaultValue: false }) === true;
      }
      var params = new URLSearchParams(globalThis.location.search || '');
      if (params.get('ux_phase41') === '1') return true;
      if (params.get('ux_phase41') === '0') return false;
      return globalThis.localStorage?.getItem('ux_phase41_enabled') === '1';
    } catch (error) {
      return false;
    }
  }

  function byId(id) { return document.getElementById(id); }
  function activeView() { return document.querySelector('.view.active'); }
  function viewIdToName(id) { return String(id || '').replace(/-view$/, ''); }
  var runtimeState = {
    lastUserInteractionAt: 0,
    pendingFailsafeTimer: null
  };

  function markUserInteraction() {
    runtimeState.lastUserInteractionAt = Date.now();
  }

  function closeUiOverlays(options) {
    var includeModal = Boolean(options && options.includeModal);
    try {
      var hasOpenDropdown = false;
      document.querySelectorAll('[data-ui-dropdown].is-open').forEach(function (node) {
        hasOpenDropdown = true;
        node.classList.remove('is-open');
        var trigger = node.querySelector('[data-dropdown-trigger]');
        var panel = node.querySelector('[data-dropdown-panel]');
        if (trigger) trigger.setAttribute('aria-expanded', 'false');
        if (panel) panel.hidden = true;
      });
      document.querySelectorAll('.delivery-ux-dropdown.open').forEach(function (el) {
        hasOpenDropdown = true;
        el.classList.remove('open');
      });
      if (includeModal) {
        document.querySelectorAll('.signature-modal.is-open').forEach(function (modal) {
          modal.classList.remove('is-open');
          modal.setAttribute('aria-hidden', 'true');
        });
      }
      return hasOpenDropdown;
    } catch (error) {
      console.warn('[phase41] close overlays', error);
      return false;
    }
  }

  function isVisible(el) {
    if (!el) return false;
    if (el.disabled) return false;
    var style = globalThis.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden' || el.offsetParent === null) return false;
    if (el.getAttribute('aria-hidden') === 'true') return false;
    return true;
  }

  function isEditableField(element) {
    if (!element || !isVisible(element)) return false;
    if (element.readOnly) return false;
    if (element.tagName === 'SELECT') return !element.disabled;
    if (element.tagName === 'TEXTAREA') return !element.disabled;
    if (element.tagName !== 'INPUT') return false;
    var type = String(element.type || 'text').toLowerCase();
    if (['hidden', 'button', 'submit', 'reset', 'checkbox', 'radio', 'file'].includes(type)) return false;
    return !element.disabled;
  }

  var FOCUS_BY_VIEW = {
    dashboard: '#dashboard-global-search',
    empresas: '#company-form input[name="name"]',
    comercial: '#platform-brand-form input[name="display_name"]',
    usuarios: '#user-search',
    unidades: '#unit-form input[name="name"]',
    colaboradores: '#employee-form input[name="name"]',
    'gestao-colaborador': '#employee-search',
    epis: '#epi-form input[name="name"]',
    estoque: '#stock-epi-search-name',
    entregas: '#delivery-employee-search',
    fichas: '#ficha-filter-employee-name',
    relatorios: '#report-filter-form input[type="date"], #report-filter-form input[type="search"]'
  };

  function focusRelevantField() {
    try {
      var current = activeView();
      if (!current) return;
      var isTyping = Date.now() - Number(runtimeState.lastUserInteractionAt || 0) < 900;
      var activeEl = document.activeElement;
      if (isTyping && isEditableField(activeEl)) return;
      var viewName = viewIdToName(current.id);
      var selector = FOCUS_BY_VIEW[viewName];
      if (!selector) return;
      var field = current.querySelector(selector);
      if (!field || !isEditableField(field)) return;
      setTimeout(function () {
        try {
          var currentActive = document.activeElement;
          if (isEditableField(currentActive) && currentActive !== document.body) return;
          field.focus({ preventScroll: true });
          if (typeof field.select === 'function' && field.type === 'search') field.select();
        } catch (_) {}
      }, 60);
    } catch (error) {
      console.warn('[phase41] focus', error);
    }
  }

  var contextKey = 'epi:ux:phase41:context:v2';
  var scrollKey = 'epi:ux:phase41:scroll:v2';
  var SENSITIVE_FIELD_PATTERN = /(password|token|cpf|cnpj|signature|assinatura|document|recovery|qr|code|key|secret|access|link)/i;

  function shouldPersistField(field) {
    if (!field || !field.id) return false;
    var id = String(field.id || '');
    var name = String(field.name || '');
    var type = String(field.type || '').toLowerCase();
    if (type === 'password' || type === 'file' || type === 'hidden') return false;
    if (SENSITIVE_FIELD_PATTERN.test(id) || SENSITIVE_FIELD_PATTERN.test(name)) return false;
    return true;
  }

  function resetPhase41ContextIfRequested() {
    try {
      var params = new URLSearchParams(globalThis.location.search || '');
      if (params.get('ux_phase41_reset') !== '1') return;
      localStorage.removeItem(contextKey);
      localStorage.removeItem(scrollKey);
    } catch (error) {
      console.warn('[phase41] reset context', error);
    }
  }

  function saveInputContext() {
    try {
      var payload = {};
      document.querySelectorAll('input[id], select[id], textarea[id]').forEach(function (field) {
        var id = String(field.id || '').trim();
        if (!id || !isVisible(field) || !shouldPersistField(field)) return;
        payload[id] = field.type === 'checkbox' ? Boolean(field.checked) : String(field.value || '');
      });
      localStorage.setItem(contextKey, JSON.stringify(payload));
    } catch (error) {
      console.warn('[phase41] context save', error);
    }
  }

  function restoreInputContext() {
    try {
      var payload = JSON.parse(localStorage.getItem(contextKey) || '{}');
      Object.keys(payload).forEach(function (id) {
        var field = byId(id);
        if (!field || !isVisible(field) || !shouldPersistField(field)) return;
        var value = payload[id];
        if (field.type === 'checkbox') field.checked = Boolean(value);
        else field.value = String(value || '');
      });
    } catch (error) {
      console.warn('[phase41] context restore', error);
    }
  }

  function saveScrollContext() {
    try {
      var current = activeView();
      if (!current) return;
      var payload = JSON.parse(localStorage.getItem(scrollKey) || '{}');
      payload[current.id] = Number(window.scrollY || 0);
      localStorage.setItem(scrollKey, JSON.stringify(payload));
    } catch (error) {
      console.warn('[phase41] scroll save', error);
    }
  }

  function markInvalidFields(form) {
    var missing = [];
    form.querySelectorAll('[required]').forEach(function (field) {
      var invalid = !String(field.value || '').trim();
      field.classList.toggle('phase41-field-error', invalid);
      if (invalid) missing.push(field);
    });
    return missing;
  }

  function setFormFeedback(form, message) {
    if (!form) return;
    var box = form.querySelector('.phase41-inline-feedback');
    if (!box) {
      box = document.createElement('div');
      box.className = 'phase41-inline-feedback';
      form.appendChild(box);
    }
    box.textContent = String(message || '');
  }

  function applyButtonState(button, state, labels) {
    if (!button) return;
    var map = labels || {};
    button.classList.add('phase41-action-btn');
    button.dataset.phase41State = state;
    if (!button.dataset.phase41DefaultLabel) button.dataset.phase41DefaultLabel = button.textContent || '';
    if (state === 'loading') button.textContent = map.loading || 'Processando...';
    if (state === 'success') button.textContent = map.success || 'Concluído';
    if (state === 'error') button.textContent = map.error || 'Falhou';
    if (state === 'idle') button.textContent = button.dataset.phase41DefaultLabel;
  }

  var globalPending = 0;
  function clearPendingFailsafe() {
    if (!runtimeState.pendingFailsafeTimer) return;
    clearTimeout(runtimeState.pendingFailsafeTimer);
    runtimeState.pendingFailsafeTimer = null;
  }
  function startPendingFailsafe() {
    clearPendingFailsafe();
    runtimeState.pendingFailsafeTimer = setTimeout(function () {
      globalPending = 0;
      setGlobalLoading(false);
      runtimeState.pendingFailsafeTimer = null;
    }, 20000);
  }
  function setGlobalLoading(isLoading) {
    var indicator = byId('phase41-activity-indicator');
    if (!indicator) return;
    indicator.hidden = !isLoading;
    if (!isLoading) clearPendingFailsafe();
  }

  function wrapApiForActivity() {
    try {
      if (typeof globalThis.api !== 'function' || globalThis.api.__phase41Wrapped) return;
      var original = globalThis.api;
      var wrapped = async function () {
        globalPending += 1;
        setGlobalLoading(true);
        startPendingFailsafe();
        try {
          return await original.apply(this, arguments);
        } finally {
          globalPending = Math.max(0, globalPending - 1);
          setGlobalLoading(globalPending > 0);
        }
      };
      wrapped.__phase41Wrapped = true;
      globalThis.api = wrapped;
    } catch (error) {
      console.warn('[phase41] api wrap', error);
    }
  }

  function decorateForms() {
    document.querySelectorAll('form').forEach(function (form) {
      safeOn(form, 'submit', function (event) {
        try {
          var submitBtn = event.submitter || form.querySelector('button[type="submit"], .primary');
          var missing = markInvalidFields(form);
          if (missing.length) {
            event.preventDefault();
            applyButtonState(submitBtn, 'error', { error: 'Corrija os campos' });
            setFormFeedback(form, 'Preencha o campo obrigatório: ' + (missing[0].labels?.[0]?.textContent || missing[0].name || missing[0].id || 'campo obrigatório') + '.');
            missing[0].focus({ preventScroll: false });
            window.scrollTo({ top: Math.max(0, missing[0].getBoundingClientRect().top + window.scrollY - 120), behavior: 'smooth' });
            setTimeout(function () { applyButtonState(submitBtn, 'idle'); }, 1300);
            return;
          }
          setFormFeedback(form, '');
          applyButtonState(submitBtn, 'loading', { loading: 'Processando...' });
          setTimeout(function () {
            if (submitBtn?.disabled === false) {
              applyButtonState(submitBtn, 'success', { success: 'Concluído com sucesso' });
              setTimeout(function () { applyButtonState(submitBtn, 'idle'); }, 1200);
            }
          }, 900);
        } catch (error) {
          console.warn('[phase41] submit state', error);
        }
      }, true);
    });
  }

  var CRITICAL_FORMS = Object.freeze(['delivery-form', 'ficha-form', 'report-filter-form']);

  function hasAutocompleteContext(target) {
    if (!target) return false;
    if (target.tagName === 'SELECT') return true;
    if (target.closest('.delivery-ux-search-box')) return true;
    if (target.closest('.stock-epi-search-results')) return true;
    if (target.getAttribute('role') === 'combobox') return true;
    if (target.getAttribute('aria-autocomplete')) return true;
    if (target.hasAttribute('list')) return true;
    return false;
  }

  function resolveSafePrimaryAction(form) {
    if (!form) return null;
    if (CRITICAL_FORMS.includes(String(form.id || ''))) return null;
    var visiblePrimaries = Array.from(form.querySelectorAll('button.primary, button[type="submit"]')).filter(isVisible);
    if (visiblePrimaries.length !== 1) return null;
    var primary = visiblePrimaries[0];
    if (!primary || primary.disabled) return null;
    if (primary.classList.contains('ghost')) return null;
    return primary;
  }

  function setupKeyboard() {
    safeOn(document, 'keydown', function (event) {
      try {
        markUserInteraction();
        if (event.key === 'Escape') {
          closeUiOverlays({ includeModal: true });
          return;
        }
        if (event.ctrlKey && event.key === '/') {
          event.preventDefault();
          var globalSearch = byId('dashboard-global-search') || document.querySelector('input[type="search"]');
          if (globalSearch && isVisible(globalSearch)) {
            globalSearch.focus({ preventScroll: true });
            globalSearch.select?.();
          }
          return;
        }
        if (event.key === 'Enter') {
          var target = event.target;
          var isTextArea = target?.tagName === 'TEXTAREA';
          if (isTextArea || event.isComposing) return;
          if (hasAutocompleteContext(target)) return;
          var form = target?.closest?.('form');
          if (!form) return;
          var primary = resolveSafePrimaryAction(form);
          if (primary) {
            event.preventDefault();
            primary.click();
          }
        }
      } catch (error) {
        console.warn('[phase41] keyboard', error);
      }
    });

    safeOn(document, 'click', function (event) {
      markUserInteraction();
      var insideOverlay = event.target?.closest?.('[data-ui-dropdown], .signature-modal, .delivery-ux-search-box, .delivery-ux-dropdown');
      if (!insideOverlay) closeUiOverlays({ includeModal: false });
    });
  }

  function setupViewObserver() {
    var mainContent = byId('main-content');
    if (!mainContent) return;
    var previousActiveId = activeView()?.id || '';
    var observer = new MutationObserver(function () {
      var current = activeView();
      var currentId = current?.id || '';
      if (!currentId || currentId === previousActiveId) return;

      saveScrollContext();
      closeUiOverlays({ includeModal: false });
      window.scrollTo({ top: 0, behavior: 'smooth' });

      current.classList.remove('phase41-view-enter');
      void current.offsetWidth;
      current.classList.add('phase41-view-enter');

      focusRelevantField();
      saveInputContext();
      previousActiveId = currentId;

      var wrap = current.querySelector('.table-wrap');
      if (wrap) {
        wrap.classList.remove('phase41-list-refresh');
        void wrap.offsetWidth;
        wrap.classList.add('phase41-list-refresh');
      }
    });
    observer.observe(mainContent, { subtree: true, attributes: true, attributeFilter: ['class'] });
  }

  function setupRowHighlight() {
    safeOn(document, 'click', function (event) {
      var row = event.target?.closest?.('tbody tr');
      if (!row) return;
      row.parentElement?.querySelectorAll('tr.phase41-row-highlight').forEach(function (r) { r.classList.remove('phase41-row-highlight'); });
      row.classList.add('phase41-row-highlight');
    });
  }

  function init() {
    try {
      if (!isEnabled()) return;
      document.body.classList.add('phase41-enabled');
      resetPhase41ContextIfRequested();
      restoreInputContext();
      setupKeyboard();
      decorateForms();
      setupViewObserver();
      setupRowHighlight();
      wrapApiForActivity();
      focusRelevantField();

      safeOn(window, 'beforeunload', function () {
        saveInputContext();
        saveScrollContext();
      });
      safeOn(document, 'input', saveInputContext);
      safeOn(document, 'change', saveInputContext);
      safeOn(document, 'focusin', markUserInteraction);
      safeOn(document, 'pointerdown', markUserInteraction);
    } catch (error) {
      console.error('[phase41] Falha ao iniciar. Fluxo clássico mantido.', error);
    }
  }

  if (document.readyState === 'loading') safeOn(document, 'DOMContentLoaded', init, { once: true });
  else init();
})();
