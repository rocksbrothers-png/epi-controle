(function phase44Iife() {
  if (globalThis.__EPI_PHASE44_BOUND__) return;
  globalThis.__EPI_PHASE44_BOUND__ = true;
  var helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
  var ensureModuleBound = typeof helpers.ensureModuleBound === 'function'
    ? helpers.ensureModuleBound
    : function () { return true; };
  if (!ensureModuleBound('phase44')) return;
  var createScopedAbortController = typeof helpers.createScopedAbortController === 'function'
    ? helpers.createScopedAbortController
    : function () { return new AbortController(); };
  var moduleController = createScopedAbortController('phase44');

  var runtime = {
    initialized: false,
    dropdownBound: new WeakSet(),
    tableBound: new WeakSet(),
    filterBound: new WeakSet(),
    confirmBound: new WeakSet(),
    actionBarBound: new WeakSet(),
    scrollTopByView: Object.create(null)
  };
  var STORAGE_NAMESPACE = 'epi.ux.phase44';
  var STORAGE_FILTER_PREFIX = STORAGE_NAMESPACE + '.filters.';
  var MAX_STORAGE_BYTES = 6000;
  var MAX_FILTER_FIELDS = 30;
  var SENSITIVE_FIELD_PATTERN = /(senha|password|token|cpf|documento|signature|assinatura|email|mail)/i;

  var VIEW_CONFIG = {
    dashboard: {
      title: 'Dashboard',
      subtitle: 'Visão consolidada com navegação e ações padronizadas.',
      primarySelector: '#dashboard-refresh-now',
      filterSelector: '#dashboard-view .qr-inline'
    },
    colaboradores: {
      title: 'Cadastro de Colaborador',
      subtitle: 'Cadastro e listagem em fluxo único com feedback contínuo.',
      primarySelector: '#employee-form button.primary',
      filterSelector: '#colaboradores-view [data-colab-list-filters]'
    },
    'gestao-colaborador': {
      title: 'Gestão de Colaborador',
      subtitle: 'Movimentações e base operacional com o mesmo padrão de UX.',
      primarySelector: '#movement-form button.primary',
      filterSelector: '#gestao-colaborador-view [data-gestao-colab-filters]'
    },
    epis: {
      title: 'Cadastro de EPI',
      subtitle: 'Cadastro, filtros e catálogo com comportamento previsível.',
      primarySelector: '#epi-form button.primary',
      filterSelector: '#epis-view .form-grid[data-phase3-filters]'
    },
    estoque: {
      title: 'Controle de Estoque',
      subtitle: 'Operação de estoque com ações e feedback padronizados.',
      primarySelector: '#stock-form button.primary',
      filterSelector: '#estoque-view [data-estoque-filters]'
    },
    entregas: {
      title: 'Entrega de EPI',
      subtitle: 'Fluxo de entrega com confirmação leve e estados consistentes.',
      primarySelector: '#delivery-form button.primary',
      filterSelector: '#entregas-view .form-grid'
    },
    fichas: {
      title: 'Ficha de EPI',
      subtitle: 'Consulta e emissão de fichas com padrão único de interação.',
      primarySelector: '#ficha-btn-visualizar',
      filterSelector: '#fichas-view .section-head .form-grid'
    }
  };

  function safeOn(target, eventName, handler, options) {
    try {
      if (typeof globalThis.safeOn === 'function') return globalThis.safeOn(target, eventName, handler, options);
      if (!target || typeof target.addEventListener !== 'function') return false;
      target.addEventListener(eventName, handler, options);
      return true;
    } catch (error) {
      console.warn('[phase44] safeOn falhou', error);
      return false;
    }
  }

  function isEnabled() {
    try {
      var helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
      if (typeof helpers.getFeatureFlag === 'function') return helpers.getFeatureFlag('ux_phase44_enabled', { defaultValue: false }) === true;
      if (typeof globalThis.getFeatureFlag === 'function') return globalThis.getFeatureFlag('ux_phase44_enabled', { defaultValue: false }) === true;
      var params = new URLSearchParams(globalThis.location.search || '');
      if (params.get('ux_phase44') === '1') return true;
      if (params.get('ux_phase44') === '0') return false;
      return globalThis.localStorage?.getItem('ux_phase44_enabled') === '1';
    } catch (_) {
      return false;
    }
  }

  function debounce(fn, wait) {
    var timer = null;
    return function debounced() {
      var ctx = this;
      var args = arguments;
      if (timer) globalThis.clearTimeout(timer);
      timer = globalThis.setTimeout(function invoke() { fn.apply(ctx, args); }, wait || 160);
    };
  }

  function isResetRequested() {
    try {
      var params = new URLSearchParams(globalThis.location.search || '');
      return params.get('ux_phase44_reset') === '1';
    } catch (_) {
      return false;
    }
  }

  function safeLocalStorageGet(key) {
    try {
      if (!globalThis.localStorage || !key) return '';
      return String(globalThis.localStorage.getItem(key) || '');
    } catch (_) {
      return '';
    }
  }

  function safeLocalStorageSet(key, value) {
    try {
      if (!globalThis.localStorage || !key) return false;
      var payload = String(value || '');
      if (payload.length > MAX_STORAGE_BYTES) return false;
      globalThis.localStorage.setItem(key, payload);
      return true;
    } catch (_) {
      return false;
    }
  }

  function removePhase44Storage() {
    try {
      if (!globalThis.localStorage) return;
      for (var i = globalThis.localStorage.length - 1; i >= 0; i -= 1) {
        var key = globalThis.localStorage.key(i);
        if (!key || key.indexOf(STORAGE_NAMESPACE + '.') !== 0) continue;
        globalThis.localStorage.removeItem(key);
      }
    } catch (_) {}
  }

  function activeViewName() {
    var active = document.querySelector('.view.active');
    return String((active && active.id) || '').replace(/-view$/, '');
  }

  function getOrCreateScreenStatus(viewName) {
    var id = 'phase44-screen-status-' + viewName;
    var node = document.getElementById(id);
    if (!node) {
      node = document.createElement('small');
      node.id = id;
      node.className = 'phase44-screen-status';
      node.dataset.state = 'idle';
      node.textContent = 'Pronto';
    }
    return node;
  }

  function setScreenStatus(viewName, text, state) {
    var node = getOrCreateScreenStatus(viewName);
    node.textContent = text || 'Pronto';
    node.dataset.state = state || 'idle';
  }

  function createBadge(label, tone) {
    var span = document.createElement('span');
    span.className = 'phase44-badge phase44-badge-' + (tone || 'neutral');
    span.textContent = label || '-';
    return span;
  }

  function createActionBar(options) {
    var cfg = options || {};
    var node = document.createElement('div');
    node.className = 'phase44-action-bar';
    node.innerHTML = [
      '<div class="phase44-action-meta">',
      '  <strong>' + (cfg.title || 'Área operacional') + '</strong>',
      '  <small>' + (cfg.subtitle || 'Ações principais com comportamento consistente.') + '</small>',
      '</div>',
      ' <div class="phase44-action-slot"></div>'
    ].join('');
    return node;
  }

  function createConfirmInline(button, options) {
    if (!button || runtime.confirmBound.has(button)) return;
    runtime.confirmBound.add(button);
    var cfg = options || {};
    safeOn(button, 'click', function onProtectedClick(event) {
      if (button.dataset.phase44BypassConfirm === '1') return;
      if (button.dataset.phase44Confirming === '1') return;
      event.preventDefault();
      event.stopPropagation();
      button.dataset.phase44Confirming = '1';
      var wrapper = document.createElement('span');
      wrapper.className = 'phase44-confirm-inline';
      wrapper.innerHTML = '<small>' + (cfg.message || 'Confirmar esta ação?') + '</small>'
        + '<button type="button" class="ghost" data-phase44-confirm-yes>Confirmar</button>'
        + '<button type="button" class="ghost" data-phase44-confirm-no>Cancelar</button>';
      button.insertAdjacentElement('afterend', wrapper);

      var cleanup = function () {
        button.dataset.phase44Confirming = '0';
        if (wrapper.parentNode) wrapper.parentNode.removeChild(wrapper);
      };

      safeOn(wrapper, 'click', function (evt) {
        var target = evt.target;
        if (!(target instanceof HTMLElement)) return;
        if (target.matches('[data-phase44-confirm-no]')) {
          cleanup();
          return;
        }
        if (target.matches('[data-phase44-confirm-yes]')) {
          cleanup();
          button.dataset.phase44BypassConfirm = '1';
          try { button.click(); } catch (_) {
            button.dataset.phase44BypassConfirm = '0';
          }
          globalThis.setTimeout(function () { button.dataset.phase44BypassConfirm = '0'; }, 0);
        }
      });
    });
  }

  function createDropdown(root) {
    if (!root || runtime.dropdownBound.has(root)) return;
    runtime.dropdownBound.add(root);

    var trigger = root.querySelector('[data-dropdown-trigger]');
    var panel = root.querySelector('[data-dropdown-panel]');
    if (!trigger || !panel) return;

    function setOpen(open) {
      var visible = Boolean(open);
      panel.hidden = !visible;
      trigger.setAttribute('aria-expanded', visible ? 'true' : 'false');
      root.classList.toggle('is-open', visible);
    }

    safeOn(trigger, 'click', function (event) {
      event.preventDefault();
      setOpen(panel.hidden);
    });

    safeOn(document, 'click', function (event) {
      if (!root.contains(event.target)) setOpen(false);
    });

    safeOn(root, 'keydown', function (event) {
      if (event.key !== 'Escape') return;
      setOpen(false);
      trigger.focus();
    });
  }

  function bindTables(viewNode) {
    if (!viewNode) return;
    var tables = viewNode.querySelectorAll('table tbody');
    tables.forEach(function (tbody) {
      if (runtime.tableBound.has(tbody)) return;
      runtime.tableBound.add(tbody);
      safeOn(tbody, 'click', function (event) {
        var row = event.target instanceof HTMLElement ? event.target.closest('tr') : null;
        if (!row) return;
        tbody.querySelectorAll('tr.phase44-row-selected').forEach(function (item) { item.classList.remove('phase44-row-selected'); });
        row.classList.add('phase44-row-selected');
      });
      var observer = new MutationObserver(function () {
        tbody.classList.add('phase44-table-updated');
        globalThis.setTimeout(function () { tbody.classList.remove('phase44-table-updated'); }, 600);
      });
      observer.observe(tbody, { childList: true, subtree: true });
    });
  }

  function bindFilterPattern(viewName, viewNode, filterSelector) {
    if (!viewNode || !filterSelector) return;
    var container = viewNode.querySelector(filterSelector.replace('#' + viewName + '-view ', '')) || viewNode.querySelector(filterSelector) || document.querySelector(filterSelector);
    if (!container || runtime.filterBound.has(container)) return;
    runtime.filterBound.add(container);

    var counter = document.createElement('small');
    counter.className = 'phase44-filter-counter';
    container.insertAdjacentElement('beforebegin', counter);

    var clearBtn = document.createElement('button');
    clearBtn.type = 'button';
    clearBtn.className = 'ghost phase44-clear-filters';
    clearBtn.textContent = 'Limpar filtros';
    container.insertAdjacentElement('afterend', clearBtn);

    function updateCounter() {
      var fields = Array.from(container.querySelectorAll('input,select,textarea'));
      var active = fields.filter(function (field) { return String(field.value || '').trim() !== ''; });
      counter.textContent = 'Filtros ativos: ' + active.length;
      setScreenStatus(viewName, active.length > 0 ? 'Filtros aplicados (' + active.length + ')' : 'Sem filtros ativos', active.length > 0 ? 'loading' : 'idle');
    }

    var persistKey = STORAGE_FILTER_PREFIX + viewName;
    function persistContext() {
      try {
        var fields = Array.from(container.querySelectorAll('input,select,textarea'));
        var payload = {};
        var count = 0;
        fields.forEach(function (field) {
          if (count >= MAX_FILTER_FIELDS) return;
          var key = field.id || field.name;
          if (!key) return;
          if (SENSITIVE_FIELD_PATTERN.test(key)) return;
          if (field.type && SENSITIVE_FIELD_PATTERN.test(field.type)) return;
          if (SENSITIVE_FIELD_PATTERN.test(field.autocomplete || '')) return;
          payload[key] = field.value;
          count += 1;
        });
        safeLocalStorageSet(persistKey, JSON.stringify(payload));
      } catch (_) {}
    }

    function restoreContext() {
      try {
        var raw = safeLocalStorageGet(persistKey);
        if (!raw) return;
        var parsed = JSON.parse(raw);
        if (!parsed || typeof parsed !== 'object') return;
        Array.from(container.querySelectorAll('input,select,textarea')).forEach(function (field) {
          var key = field.id || field.name;
          if (!key || SENSITIVE_FIELD_PATTERN.test(key)) return;
          if (!Object.prototype.hasOwnProperty.call(parsed, key)) return;
          field.value = String(parsed[key] ?? '');
          field.dispatchEvent(new Event('input', { bubbles: true }));
          field.dispatchEvent(new Event('change', { bubbles: true }));
        });
      } catch (_) {}
    }

    var debounced = debounce(function () {
      updateCounter();
      persistContext();
    }, 180);

    safeOn(container, 'input', debounced);
    safeOn(container, 'change', debounced);
    safeOn(clearBtn, 'click', function () {
      Array.from(container.querySelectorAll('input,select,textarea')).forEach(function (field) {
        if (field.tagName === 'SELECT') field.selectedIndex = 0;
        else field.value = '';
        field.dispatchEvent(new Event('input', { bubbles: true }));
        field.dispatchEvent(new Event('change', { bubbles: true }));
      });
      updateCounter();
      persistContext();
    });

    restoreContext();
    updateCounter();
  }

  function applyViewHeader(viewName, viewNode, config) {
    if (!viewNode || !config) return;
    var first = viewNode.querySelector(':scope > .phase44-header');
    if (first) return;

    var header = document.createElement('article');
    header.className = 'card phase44-header';
    header.innerHTML = [
      '<div>',
      '  <span class="eyebrow">Fase 4.4</span>',
      '  <h3>' + config.title + '</h3>',
      '  <p class="hint">' + config.subtitle + '</p>',
      '</div>',
      '<div class="phase44-header-actions"></div>'
    ].join('');

    var status = getOrCreateScreenStatus(viewName);
    header.querySelector('.phase44-header-actions').appendChild(status);
    header.querySelector('.phase44-header-actions').appendChild(createBadge('Recomendado', 'recommended'));
    header.querySelector('.phase44-header-actions').appendChild(createBadge('Recente', 'recent'));
    header.querySelector('.phase44-header-actions').appendChild(createBadge('Mais usado', 'most-used'));

    viewNode.insertBefore(header, viewNode.firstChild);

    var primary = document.querySelector(config.primarySelector);
    if (primary) {
      var bar = createActionBar({ title: 'Ação principal', subtitle: 'Posição fixa e previsível em todo o sistema.' });
      var slot = bar.querySelector('.phase44-action-slot');
      var stickyButton = document.createElement('button');
      stickyButton.type = 'button';
      stickyButton.className = 'primary phase44-primary-mirror';
      stickyButton.textContent = primary.textContent || 'Executar ação principal';
      safeOn(stickyButton, 'click', function () {
        setScreenStatus(viewName, 'Processando ação principal...', 'loading');
        try { primary.click(); } catch (_) {}
      });
      slot.appendChild(stickyButton);
      if (!runtime.actionBarBound.has(viewNode)) {
        runtime.actionBarBound.add(viewNode);
        viewNode.insertBefore(bar, header.nextSibling);
      }
    }
  }

  function bindGlobalFeedback() {
    safeOn(document, 'submit', function (event) {
      var form = event.target;
      if (!(form instanceof HTMLFormElement)) return;
      var view = form.closest('.view');
      var viewName = view ? view.id.replace(/-view$/, '') : activeViewName();
      if (!VIEW_CONFIG[viewName]) return;
      setScreenStatus(viewName, 'Ação enviada', 'loading');
    }, { signal: moduleController.signal });

    safeOn(document.body, 'htmx:responseError', function () {
      var viewName = activeViewName();
      if (VIEW_CONFIG[viewName]) setScreenStatus(viewName, 'Erro na atualização. Tente novamente.', 'error');
    }, { signal: moduleController.signal });

    safeOn(document.body, 'htmx:afterRequest', function (event) {
      var viewName = activeViewName();
      if (!VIEW_CONFIG[viewName]) return;
      var successful = Number(event?.detail?.xhr?.status || 0) < 400;
      setScreenStatus(viewName, successful ? 'Sucesso confirmado.' : 'Erro na atualização. Tente novamente.', successful ? 'success' : 'error');
    }, { signal: moduleController.signal });

    safeOn(document, 'epi:action-success', function (event) {
      var source = event && event.detail && event.detail.view ? String(event.detail.view) : activeViewName();
      if (VIEW_CONFIG[source]) setScreenStatus(source, 'Sucesso confirmado.', 'success');
    }, { signal: moduleController.signal });

    safeOn(document, 'epi:action-error', function (event) {
      var source = event && event.detail && event.detail.view ? String(event.detail.view) : activeViewName();
      if (VIEW_CONFIG[source]) setScreenStatus(source, 'Falha ao concluir ação.', 'error');
    }, { signal: moduleController.signal });
  }

  function bindFetchFeedbackBridge() {
    if (globalThis.__EPI_PHASE44_FETCH_BRIDGED__) return;
    if (typeof globalThis.fetch !== 'function') return;
    globalThis.__EPI_PHASE44_FETCH_BRIDGED__ = true;
    var originalFetch = globalThis.fetch.bind(globalThis);
    globalThis.fetch = function phase44FetchBridge() {
      var currentView = activeViewName();
      return originalFetch.apply(globalThis, arguments).then(function (response) {
        try {
          document.dispatchEvent(new CustomEvent(response && response.ok ? 'epi:action-success' : 'epi:action-error', { detail: { view: currentView, status: response && response.status } }));
        } catch (_) {}
        return response;
      }).catch(function (error) {
        try {
          document.dispatchEvent(new CustomEvent('epi:action-error', { detail: { view: currentView, error: String(error || '') } }));
        } catch (_) {}
        throw error;
      });
    };
  }

  function bindScrollPattern() {
    safeOn(document, 'epi:viewchange', function (event) {
      var nextView = event && event.detail ? event.detail.view : activeViewName();
      if (!VIEW_CONFIG[nextView]) return;
      globalThis.scrollTo({ top: 0, behavior: 'smooth' });
      document.body.classList.remove('phase44-transition-pulse');
      void document.body.offsetWidth;
      document.body.classList.add('phase44-transition-pulse');
      runtime.scrollTopByView[nextView] = globalThis.scrollY || 0;
    }, { signal: moduleController.signal });

    safeOn(document, 'invalid', function (event) {
      var field = event.target;
      if (!(field instanceof HTMLElement)) return;
      var view = field.closest('.view');
      var viewName = view ? view.id.replace(/-view$/, '') : activeViewName();
      if (!VIEW_CONFIG[viewName]) return;
      field.scrollIntoView({ block: 'center', behavior: 'smooth' });
      setScreenStatus(viewName, 'Revise os campos obrigatórios destacados.', 'error');
    }, { capture: true, signal: moduleController.signal });
  }

  function bindDropdownsAndModals() {
    document.querySelectorAll('[data-ui-dropdown]').forEach(function (dropdownRoot) {
      createDropdown(dropdownRoot);
    });

    safeOn(document, 'keydown', function (event) {
      if (event.key !== 'Escape') return;
      document.querySelectorAll('.modal:not([hidden]), [role="dialog"]').forEach(function (node) {
        if (node.hasAttribute('hidden')) return;
        node.setAttribute('hidden', 'hidden');
      });
    }, { signal: moduleController.signal });
  }

  function bindInlineConfirmationPattern(viewNode) {
    if (!viewNode) return;
    viewNode.querySelectorAll('button').forEach(function (button) {
      if (!button || button.dataset.phase44BypassConfirm === '1') return;
      var explicitConfirm = button.dataset.confirmAction === 'true' || button.dataset.criticalAction === 'true';
      var nativeConfirm = button.dataset.confirmNative === 'true' || button.hasAttribute('data-native-confirm');
      var text = String(button.textContent || '').toLowerCase();
      var fallbackTextMatch = /excluir|remover|inativar|desativar/.test(text);
      if (!explicitConfirm && !fallbackTextMatch) return;
      if (nativeConfirm) return;
      var customMessage = String(button.dataset.confirmMessage || '').trim();
      createConfirmInline(button, { message: customMessage || 'Confirma esta ação? Ela pode impactar registros relacionados.' });
    });
  }

  function bindView(viewName) {
    var config = VIEW_CONFIG[viewName];
    var viewNode = document.getElementById(viewName + '-view');
    if (!config || !viewNode) return;
    applyViewHeader(viewName, viewNode, config);
    bindTables(viewNode);
    bindFilterPattern(viewName, viewNode, config.filterSelector);
    bindInlineConfirmationPattern(viewNode);
  }

  function init() {
    if (runtime.initialized) return;
    runtime.initialized = true;
    document.body.classList.add('phase44-enabled');
    if (isResetRequested()) removePhase44Storage();

    Object.keys(VIEW_CONFIG).forEach(function (viewName) {
      bindView(viewName);
    });

    bindDropdownsAndModals();
    bindGlobalFeedback();
    bindFetchFeedbackBridge();
    bindScrollPattern();

    safeOn(document, 'epi:viewchange', function (event) {
      var nextView = event && event.detail ? event.detail.view : activeViewName();
      bindView(nextView);
    }, { signal: moduleController.signal });

    console.info('[phase44] padronização global ativa');
  }

  globalThis.createDropdown = createDropdown;
  globalThis.createActionBar = createActionBar;
  globalThis.createConfirmInline = createConfirmInline;
  globalThis.createBadge = createBadge;

  if (!isEnabled()) {
    console.info('[phase44] desabilitada: fluxo clássico mantido');
    return;
  }

  try {
    init();
  } catch (error) {
    console.warn('[phase44] falha ao inicializar padronização global', error);
  }
})();
