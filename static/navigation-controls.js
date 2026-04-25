(function () {
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
  var createScopedAbortController = typeof helpers.createScopedAbortController === 'function'
    ? helpers.createScopedAbortController
    : function () { return new AbortController(); };

  function isEnabled() {
    try {
      if (typeof helpers.getFeatureFlag === 'function') {
        return helpers.getFeatureFlag('ux_navigation_controls_enabled', { defaultValue: false, allowStorage: true });
      }
      return new URLSearchParams(globalThis.location.search).get('ux_nav_controls') === '1';
    } catch (_error) {
      return false;
    }
  }

  if (!isEnabled()) return;
  if (globalThis.__EPI_NAV_CONTROLS_BOUND__ === true) return;
  globalThis.__EPI_NAV_CONTROLS_BOUND__ = true;

  var controller = createScopedAbortController('navigation_controls_phase53a');
  var signal = controller && controller.signal ? controller.signal : undefined;

  var NAV_TREE = {
    operacao: {
      label: 'Operação',
      children: [
        { view: 'dashboard', label: 'Dashboard' },
        { view: 'empresas', label: 'Empresas' },
        { view: 'usuarios', label: 'Usuários' },
        { view: 'unidades', label: 'Unidades' },
        {
          label: 'Colaboradores',
          children: [
            { view: 'colaboradores', label: 'Cadastro' },
            { view: 'gestao-colaborador', label: 'Gestão' }
          ]
        },
        {
          label: 'EPI',
          children: [
            { view: 'epis', label: 'Cadastro' },
            { view: 'estoque', label: 'Estoque' },
            { view: 'entregas', label: 'Entrega' },
            { view: 'fichas', label: 'Ficha' }
          ]
        },
        { view: 'relatorios', label: 'Relatórios' }
      ]
    }
  };

  var VIEW_PATHS = {
    dashboard: ['Operação', 'Dashboard'],
    empresas: ['Operação', 'Empresas'],
    usuarios: ['Operação', 'Usuários'],
    unidades: ['Operação', 'Unidades'],
    colaboradores: ['Operação', 'Colaboradores', 'Cadastro'],
    'gestao-colaborador': ['Operação', 'Colaboradores', 'Gestão'],
    epis: ['Operação', 'EPI', 'Cadastro'],
    estoque: ['Operação', 'EPI', 'Estoque'],
    entregas: ['Operação', 'EPI', 'Entrega'],
    fichas: ['Operação', 'EPI', 'Ficha'],
    relatorios: ['Operação', 'Relatórios'],
    configuracao: ['Operação', 'Configuração']
  };

  var refs = {
    content: document.getElementById('main-content'),
    menu: document.getElementById('menu'),
    burger: document.getElementById('mobile-menu-toggle'),
    config: document.getElementById('top-config-trigger'),
    back: document.getElementById('hierarchy-back-btn'),
    crumbWrap: document.getElementById('hierarchy-breadcrumb-wrap'),
    crumb: document.getElementById('hierarchy-breadcrumb')
  };

  var navStack = [];
  var overlays = { settings: false, operation: false };
  var ui = {};

  function currentView() {
    var active = document.querySelector('.view.active');
    return (active && active.id ? active.id.replace(/-view$/, '') : '') || 'dashboard';
  }

  function canAccessView(view) {
    try {
      return globalThis.__EPI_APP_NAV_API__?.canAccessView ? globalThis.__EPI_APP_NAV_API__.canAccessView(view) : true;
    } catch (_error) {
      return true;
    }
  }

  function navigateTo(view, options) {
    var navApi = globalThis.__EPI_APP_NAV_API__;
    if (navApi && typeof navApi.navigateToView === 'function') {
      navApi.navigateToView(view, options || { historyMode: 'push', partial: true });
      return;
    }
    var item = document.querySelector('.menu-link[data-view="' + view + '"]');
    if (item) item.click();
  }

  function closeAllOverlays(exceptKey) {
    Object.keys(overlays).forEach(function (key) {
      if (exceptKey && key === exceptKey) return;
      overlays[key] = false;
    });
    syncOverlays();
  }

  function togglePanel(panelKey) {
    var willOpen = !overlays[panelKey];
    closeAllOverlays();
    overlays[panelKey] = willOpen;
    syncOverlays();
    return willOpen;
  }

  function syncOverlays() {
    var settingsOpen = overlays.settings === true;
    var operationOpen = overlays.operation === true;
    if (ui.settingsPanel) ui.settingsPanel.hidden = !settingsOpen;
    if (ui.operationPanel) ui.operationPanel.hidden = !operationOpen;
    if (refs.config) {
      refs.config.classList.toggle('active', settingsOpen);
      refs.config.setAttribute('aria-expanded', settingsOpen ? 'true' : 'false');
      refs.config.setAttribute('aria-controls', 'ux-settings-panel');
      refs.config.setAttribute('aria-label', settingsOpen ? 'Fechar configuração' : 'Abrir configuração');
    }
    if (refs.burger) {
      refs.burger.classList.toggle('active', operationOpen);
      refs.burger.setAttribute('aria-expanded', operationOpen ? 'true' : 'false');
      refs.burger.setAttribute('aria-controls', 'ux-operation-panel');
      refs.burger.hidden = false;
      refs.burger.title = 'Operação';
      refs.burger.setAttribute('aria-label', operationOpen ? 'Fechar menu Operação' : 'Abrir menu Operação');
    }
    document.body.classList.toggle('ux-nav-controls-enabled', true);
    document.body.classList.toggle('ux-settings-open', settingsOpen);
    document.body.classList.toggle('ux-operation-open', operationOpen);
  }

  function bindClickOutside(panel, trigger, closeKey) {
    safeOn(document, 'click', function (event) {
      if (!overlays[closeKey]) return;
      var t = event && event.target;
      if (panel && panel.contains(t)) return;
      if (trigger && trigger.contains(t)) return;
      overlays[closeKey] = false;
      syncOverlays();
    }, { signal: signal, passive: true });
  }

  function bindEscapeToClose() {
    safeOn(document, 'keydown', function (event) {
      if (event && event.key !== 'Escape') return;
      closeAllOverlays();
    }, { signal: signal });
  }

  function buildOperationItems(nodes, level) {
    return nodes.map(function (entry) {
      if (entry.view) {
        if (!canAccessView(entry.view)) return '';
        return '<button class="ux-operation-item level-' + level + '" type="button" data-nav-view="' + entry.view + '">' + entry.label + '</button>';
      }
      return [
        '<div class="ux-operation-group level-' + level + '">',
        '  <div class="ux-operation-group-title">' + entry.label + '</div>',
        '  <div class="ux-operation-group-body">' + buildOperationItems(entry.children || [], level + 1) + '</div>',
        '</div>'
      ].join('');
    }).join('');
  }

  function renderBreadcrumb(view) {
    if (!refs.crumb || !refs.crumbWrap) return;
    var path = VIEW_PATHS[view] || ['Operação', 'Dashboard'];
    refs.crumbWrap.hidden = false;
    if (refs.back) {
      refs.back.hidden = false;
      refs.back.disabled = false;
      refs.back.title = 'Voltar';
    }
    refs.crumb.innerHTML = path.map(function (segment, idx) {
      var isLast = idx === path.length - 1;
      var klass = isLast ? 'hierarchy-crumb is-active' : 'hierarchy-crumb is-link';
      return '<button type="button" class="' + klass + '" data-crumb-index="' + idx + '">' + segment + '</button>';
    }).join('<span class="hierarchy-sep">&gt;</span>');
  }

  function handleBack() {
    closeAllOverlays();
    if (navStack.length > 1) {
      navStack.pop();
      var previous = navStack[navStack.length - 1] || 'dashboard';
      navigateTo(previous, { historyMode: 'replace', partial: true });
      return;
    }
    if (globalThis.history.length > 1) {
      globalThis.history.back();
      return;
    }
    navigateTo('dashboard', { historyMode: 'replace', partial: true });
  }

  function setupPanels() {
    if (!refs.content) return;
    ui.settingsPanel = document.createElement('aside');
    ui.settingsPanel.id = 'ux-settings-panel';
    ui.settingsPanel.className = 'ux-settings-panel';
    ui.settingsPanel.hidden = true;
    ui.settingsPanel.innerHTML = [
      '<div class="ux-panel-head"><strong>Configuração</strong><small>Ações rápidas da área</small></div>',
      '<button type="button" class="ux-panel-link" data-nav-view="configuracao">Abrir configurações do sistema</button>',
      '<button type="button" class="ux-panel-link" data-nav-view="dashboard">Voltar ao dashboard</button>'
    ].join('');

    ui.operationPanel = document.createElement('aside');
    ui.operationPanel.id = 'ux-operation-panel';
    ui.operationPanel.className = 'ux-operation-panel';
    ui.operationPanel.hidden = true;
    ui.operationPanel.innerHTML = [
      '<div class="ux-panel-head"><strong>Operação</strong><small>Módulos e submódulos</small></div>',
      '<nav class="ux-operation-tree" aria-label="Navegação Operação">',
      buildOperationItems(NAV_TREE.operacao.children, 0),
      '</nav>'
    ].join('');

    refs.content.appendChild(ui.settingsPanel);
    refs.content.appendChild(ui.operationPanel);
  }

  function bind() {
    try {
      setupPanels();

      if (refs.burger) {
        safeOn(refs.burger, 'click', function (event) {
          event.preventDefault();
          togglePanel('operation');
        }, { signal: signal });
      }

      if (refs.config) {
        safeOn(refs.config, 'click', function (event) {
          event.preventDefault();
          togglePanel('settings');
        }, { signal: signal });
      }

      safeOn(refs.back, 'click', function (event) {
        event.preventDefault();
        handleBack();
      }, { signal: signal });

      safeOn(document, 'epi:viewchange', function (event) {
        var view = event?.detail?.view || currentView();
        if (!navStack.length || navStack[navStack.length - 1] !== view) navStack.push(view);
        if (navStack.length > 40) navStack = navStack.slice(-40);
        renderBreadcrumb(view);
        closeAllOverlays();
      }, { signal: signal });

      safeOn(document, 'click', function (event) {
        var action = event?.target?.closest?.('[data-nav-view]');
        if (!action) return;
        var view = action.dataset.navView;
        if (!view) return;
        event.preventDefault();
        navigateTo(view, { historyMode: 'push', partial: true });
        closeAllOverlays();
      }, { signal: signal });

      safeOn(refs.crumb, 'click', function (event) {
        var button = event?.target?.closest?.('[data-crumb-index]');
        if (!button) return;
        var index = Number(button.dataset.crumbIndex);
        var view = currentView();
        var path = VIEW_PATHS[view] || VIEW_PATHS.dashboard;
        if (index >= path.length - 1) return;
        var targetByDepth = {
          0: 'dashboard',
          1: view === 'configuracao' ? 'configuracao' : (view === 'colaboradores' || view === 'gestao-colaborador' ? 'colaboradores' : (view === 'epis' || view === 'estoque' || view === 'entregas' || view === 'fichas' ? 'epis' : view))
        };
        navigateTo(targetByDepth[index] || 'dashboard', { historyMode: 'push', partial: true });
      }, { signal: signal });

      bindClickOutside(ui.settingsPanel, refs.config, 'settings');
      bindClickOutside(ui.operationPanel, refs.burger, 'operation');
      bindEscapeToClose();

      navStack = [currentView()];
      renderBreadcrumb(currentView());
      syncOverlays();
    } catch (error) {
      console.warn('[nav-controls] setup failed', error);
    }
  }

  if (document.readyState === 'loading') {
    safeOn(document, 'DOMContentLoaded', bind, { once: true, signal: signal });
  } else {
    bind();
  }

  globalThis.__EPI_NAV_CONTROLS_API__ = {
    togglePanel: togglePanel,
    closeAllOverlays: closeAllOverlays,
    bindClickOutside: bindClickOutside,
    bindEscapeToClose: bindEscapeToClose
  };
})();
