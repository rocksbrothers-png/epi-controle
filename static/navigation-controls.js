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
        return helpers.getFeatureFlag('ux_navigation_controls_enabled', { defaultValue: true, allowStorage: true });
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

  // Para novas telas, adicione entradas em VIEW_HIERARCHY para manter breadcrumb e menu consistentes.
  var VIEW_HIERARCHY = {
    dashboard: { get ["label"]() { return (globalThis.trEpi?.("dashboard.title","Dashboard",{}) ?? "Dashboard"); }, parent: 'operacao' },
    empresas: { get ["label"]() { return (globalThis.trEpi?.("company.kpiTotal","Empresas",{}) ?? "Empresas"); }, parent: 'operacao' },
    comercial: { get ["label"]() { return (globalThis.trEpi?.("nav.commercial","Comercial",{}) ?? "Comercial"); }, parent: 'operacao' },
    usuarios: { get ["label"]() { return (globalThis.trEpi?.("user.title","Usu\u00e1rios",{}) ?? "Usu\u00e1rios"); }, parent: 'operacao' },
    unidades: { get ["label"]() { return (globalThis.trEpi?.("dashboard.units","Unidades",{}) ?? "Unidades"); }, parent: 'operacao' },
    colaboradores: { get ["label"]() { return (globalThis.trEpi?.("outsourcedCompany.registrationMode","Cadastro",{}) ?? "Cadastro"); }, parent: 'colaboradores-group' },
    'gestao-colaborador': { label: 'Gestão', parent: 'colaboradores-group' },
    epis: { get ["label"]() { return (globalThis.trEpi?.("outsourcedCompany.registrationMode","Cadastro",{}) ?? "Cadastro"); }, parent: 'epi-group' },
    estoque: { get ["label"]() { return (globalThis.trEpi?.("tabs.stock","Estoque",{}) ?? "Estoque"); }, parent: 'epi-group' },
    entregas: { get ["label"]() { return (globalThis.trEpi?.("delivery.title","Entrega",{}) ?? "Entrega"); }, parent: 'epi-group' },
    fichas: { label: 'Ficha', parent: 'epi-group' },
    relatorios: { get ["label"]() { return (globalThis.trEpi?.("outsourcedCompany.reportsTab","Relat\u00f3rios",{}) ?? "Relat\u00f3rios"); }, parent: 'operacao' },
    configuracao: { get ["label"]() { return (globalThis.trEpi?.("ui.topbar.configuracao_8d60e1","Configura\u00e7\u00e3o",{}) ?? "Configura\u00e7\u00e3o"); }, parent: 'operacao' }
  };

  var TREE_GROUPS = {
    operacao: { get ["label"]() { return (globalThis.trEpi?.("nav.groupOperation","Opera\u00e7\u00e3o",{}) ?? "Opera\u00e7\u00e3o"); }, view: 'dashboard', parent: null },
    'colaboradores-group': { get ["label"]() { return (globalThis.trEpi?.("employee.listTitle","Colaboradores",{}) ?? "Colaboradores"); }, view: 'colaboradores', parent: 'operacao' },
    'epi-group': { label: 'EPI', view: 'epis', parent: 'operacao' }
  };

  var refs = {
    content: document.getElementById('main-content'),
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

  function resolveViewLabel(view) {
    var fixed = VIEW_HIERARCHY[view];
    if (fixed && fixed.label) return fixed.label;
    var menuItem = document.querySelector('.menu-link[data-view="' + view + '"]');
    if (menuItem && menuItem.textContent) return String(menuItem.textContent).trim();
    return 'Tela atual';
  }

  function canAccessView(view) {
    try {
      var api = globalThis.__EPI_APP_NAV_API__;
      if (api && typeof api.canAccessView === 'function') return api.canAccessView(view);
      return true;
    } catch (_error) {
      return true;
    }
  }

  function navigateTo(view, options) {
    if (!view) return false;
    if (!canAccessView(view)) return false;
    var navApi = globalThis.__EPI_APP_NAV_API__;
    if (navApi && typeof navApi.navigateToView === 'function') {
      navApi.navigateToView(view, options || { historyMode: 'push', partial: true });
      return true;
    }
    var item = document.querySelector('.menu-link[data-view="' + view + '"]');
    if (item && typeof item.click === 'function') {
      item.click();
      return true;
    }
    return false;
  }

  function updatePanelState(panel, isOpen) {
    if (!panel) return;
    panel.hidden = !isOpen;
    panel.setAttribute('aria-hidden', isOpen ? 'false' : 'true');
    if ('inert' in panel) panel.inert = !isOpen;
  }

  function syncOverlays() {
    var settingsOpen = overlays.settings === true;
    var operationOpen = overlays.operation === true;

    updatePanelState(ui.settingsPanel, settingsOpen);
    updatePanelState(ui.operationPanel, operationOpen);

    if (refs.config) {
      refs.config.classList.toggle('active', settingsOpen);
      refs.config.setAttribute('aria-expanded', settingsOpen ? 'true' : 'false');
      refs.config.setAttribute('aria-controls', 'ux-settings-panel');
      refs.config.setAttribute('aria-label', settingsOpen ? (globalThis.EpiI18n?.clearBinding?.(refs.config,"aria-label"), 'Fechar configuração') : (globalThis.EpiI18n?.attributeFor?.(refs.config,"aria-label","ui.topbar.abrir_configuracao_6a7a95","Abrir configura\u00e7\u00e3o",{}) ?? globalThis.trEpi?.("ui.topbar.abrir_configuracao_6a7a95","Abrir configura\u00e7\u00e3o",{}) ?? "Abrir configura\u00e7\u00e3o"));
    }

    if (refs.burger) {
      refs.burger.classList.toggle('active', operationOpen);
      refs.burger.setAttribute('aria-expanded', operationOpen ? 'true' : 'false');
      refs.burger.setAttribute('aria-controls', 'ux-operation-panel');
      refs.burger.hidden = false;
      refs.burger.title = ((globalThis.EpiI18n?.attributeFor?.(refs.burger,"title","nav.groupOperation","Opera\u00e7\u00e3o",{}) ?? globalThis.trEpi?.("nav.groupOperation","Opera\u00e7\u00e3o",{}) ?? "Opera\u00e7\u00e3o"));
      refs.burger.setAttribute('aria-label', operationOpen ? 'Fechar menu Operação' : 'Abrir menu Operação');
    }

    document.body.classList.toggle('ux-nav-controls-enabled', true);
    document.body.classList.toggle('ux-settings-open', settingsOpen);
    document.body.classList.toggle('ux-operation-open', operationOpen);
  }

  function closeAllOverlays(exceptKey) {
    Object.keys(overlays).forEach(function (key) {
      if (exceptKey && key === exceptKey) return;
      overlays[key] = false;
    });
    syncOverlays();
  }

  function togglePanel(panelKey) {
    if (!Object.prototype.hasOwnProperty.call(overlays, panelKey)) return false;
    var next = !overlays[panelKey];
    closeAllOverlays();
    overlays[panelKey] = next;
    syncOverlays();
    return next;
  }

  function buildTrail(view) {
    var trail = [];
    var known = VIEW_HIERARCHY[view];
    if (!known) {
      return [
        { label: TREE_GROUPS.operacao.label, view: TREE_GROUPS.operacao.view },
        { label: resolveViewLabel(view), view: null }
      ];
    }

    trail.unshift({ label: known.label || resolveViewLabel(view), view: view });
    var parentKey = known.parent;
    while (parentKey) {
      var group = TREE_GROUPS[parentKey];
      if (!group) break;
      trail.unshift({ label: group.label, view: group.view || null });
      parentKey = group.parent;
    }
    if (!trail.length) {
      trail.push({ label: TREE_GROUPS.operacao.label, view: TREE_GROUPS.operacao.view });
      trail.push({ label: resolveViewLabel(view), view: null });
    }
    return trail;
  }

  function renderBreadcrumb(view) {
    if (!refs.crumb || !refs.crumbWrap) return;
    var trail = buildTrail(view || currentView());
    refs.crumbWrap.hidden = false;

    if (refs.back) {
      refs.back.hidden = false;
      refs.back.disabled = false;
      refs.back.title = ((globalThis.EpiI18n?.attributeFor?.(refs.back,"title","dataMigration.back","Voltar",{}) ?? globalThis.trEpi?.("dataMigration.back","Voltar",{}) ?? "Voltar"));
      refs.back.setAttribute('aria-label', 'Voltar para área anterior');
    }

    refs.crumb.innerHTML = trail.map(function (entry, idx) {
      var isLast = idx === trail.length - 1;
      var isClickable = !isLast && entry.view && canAccessView(entry.view);
      var classes = ['hierarchy-crumb'];
      classes.push(isLast ? 'is-active' : 'is-link');
      if (!isClickable) classes.push('is-disabled');
      var attrs = isClickable ? ' data-crumb-view="' + entry.view + '"' : ' aria-disabled="true"';
      return '<button type="button" class="' + classes.join(' ') + '"' + attrs + '>' + entry.label + '</button>';
    }).join('<span class="hierarchy-sep">&gt;</span>');
  }

  function handleBack() {
    closeAllOverlays();
    if (navStack.length > 1) {
      navStack.pop();
      var previous = navStack[navStack.length - 1] || 'dashboard';
      if (!navigateTo(previous, { historyMode: 'replace', partial: true })) {
        navigateTo('dashboard', { historyMode: 'replace', partial: true });
      }
      return;
    }
    if (globalThis.history.length > 1) {
      globalThis.history.back();
      return;
    }
    navigateTo('dashboard', { historyMode: 'replace', partial: true });
  }

  function buildOperationTreeHtml() {
    var groups = [
      {
        label: (globalThis.trEpi?.("nav.groupOperation","Opera\u00e7\u00e3o",{}) ?? "Opera\u00e7\u00e3o"),
        views: ['dashboard', 'empresas', 'comercial', 'usuarios', 'unidades', 'relatorios']
      },
      {
        label: (globalThis.trEpi?.("employee.listTitle","Colaboradores",{}) ?? "Colaboradores"),
        views: ['colaboradores', 'gestao-colaborador']
      },
      {
        label: 'EPI',
        views: ['epis', 'estoque', 'entregas', 'fichas']
      }
    ];

    return groups.map(function (group, groupIndex) {
      var nodes = group.views.filter(canAccessView).map(function (view) {
        return '<button class="ux-operation-item level-' + (groupIndex > 0 ? 1 : 0) + '" type="button" data-nav-view="' + view + '">' + resolveViewLabel(view) + '</button>';
      }).join('');
      if (!nodes) return '';
      return [
        '<div class="ux-operation-group">',
        '  <div class="ux-operation-group-title">' + group.label + '</div>',
        '  <div class="ux-operation-group-body">' + nodes + '</div>',
        '</div>'
      ].join('');
    }).join('');
  }

  function buildSettingsPanelHtml() {
    var items = [];
    if (canAccessView('configuracao')) {
      items.push('<button type="button" class="ux-panel-link" data-nav-view="configuracao">Abrir configurações do sistema</button>');
    }
    items.push('<button type="button" class="ux-panel-link" data-nav-view="dashboard">Voltar ao dashboard</button>');
    return [
      "<div class=\"ux-panel-head\"><strong data-i18n=\"ui.topbar.configuracao_8d60e1\">Configura\u00e7\u00e3o</strong><small>A\u00e7\u00f5es r\u00e1pidas da \u00e1rea</small></div>",
    ].concat(items).join('');
  }

  function setupPanels() {
    if (!refs.content) return false;

    ui.settingsPanel = document.createElement('aside');
    ui.settingsPanel.id = 'ux-settings-panel';
    ui.settingsPanel.className = 'ux-settings-panel';
    ui.settingsPanel.hidden = true;
    ui.settingsPanel.setAttribute('aria-hidden', 'true');
    ui.settingsPanel.setAttribute('tabindex', '-1');
    ui.settingsPanel.innerHTML = buildSettingsPanelHtml();

    ui.operationPanel = document.createElement('aside');
    ui.operationPanel.id = 'ux-operation-panel';
    ui.operationPanel.className = 'ux-operation-panel';
    ui.operationPanel.hidden = true;
    ui.operationPanel.setAttribute('aria-hidden', 'true');
    ui.operationPanel.setAttribute('tabindex', '-1');
    ui.operationPanel.innerHTML = [
      "<div class=\"ux-panel-head\"><strong data-i18n=\"nav.groupOperation\">Opera\u00e7\u00e3o</strong><small>M\u00f3dulos e subm\u00f3dulos</small></div>",
      '<nav class="ux-operation-tree" aria-label="Navegação Operação">',
      buildOperationTreeHtml(),
      '</nav>'
    ].join('');

    refs.content.appendChild(ui.settingsPanel);
    refs.content.appendChild(ui.operationPanel);

    if (refs.config) refs.config.style.display = '';

    return true;
  }

  function bindClickOutside(panel, trigger, closeKey) {
    safeOn(document, 'pointerdown', function (event) {
      if (!overlays[closeKey]) return;
      var target = event && event.target;
      if (panel && panel.contains(target)) return;
      if (trigger && trigger.contains(target)) return;
      overlays[closeKey] = false;
      syncOverlays();
    }, { signal: signal, passive: true });
  }

  function bindEscapeToClose() {
    safeOn(document, 'keydown', function (event) {
      if (!event || event.key !== 'Escape') return;
      if (!overlays.settings && !overlays.operation) return;
      event.preventDefault();
      closeAllOverlays();
    }, { signal: signal });
  }

  function bind() {
    try {
      if (!setupPanels()) {
        console.warn('[nav-controls] painel não inicializado: #main-content ausente');
        return;
      }

      if (refs.burger) {
        safeOn(refs.burger, 'click', function (event) {
          event.preventDefault();
          event.stopImmediatePropagation();
          togglePanel('operation');
        }, { signal: signal, capture: true });
      }

      if (refs.config) {
        safeOn(refs.config, 'click', function (event) {
          event.preventDefault();
          event.stopImmediatePropagation();
          togglePanel('settings');
        }, { signal: signal, capture: true });
      }

      if (refs.back) {
        safeOn(refs.back, 'click', function (event) {
          event.preventDefault();
          event.stopImmediatePropagation();
          handleBack();
        }, { signal: signal, capture: true });
      }

      safeOn(document, 'epi:viewchange', function (event) {
        var nextView = event && event.detail ? event.detail.view : currentView();
        if (!nextView) nextView = 'dashboard';
        if (!navStack.length || navStack[navStack.length - 1] !== nextView) navStack.push(nextView);
        if (navStack.length > 50) navStack = navStack.slice(-50);
        renderBreadcrumb(nextView);
        closeAllOverlays();
      }, { signal: signal });

      safeOn(document, 'click', function (event) {
        var action = event && event.target && event.target.closest ? event.target.closest('[data-nav-view]') : null;
        if (!action) return;
        var view = action.dataset ? action.dataset.navView : '';
        if (!view) return;
        event.preventDefault();
        if (navigateTo(view, { historyMode: 'push', partial: true })) closeAllOverlays();
      }, { signal: signal });

      if (refs.crumb) {
        safeOn(refs.crumb, 'click', function (event) {
          var button = event && event.target && event.target.closest ? event.target.closest('[data-crumb-view]') : null;
          if (!button) return;
          var view = button.getAttribute('data-crumb-view');
          if (!view || view === currentView()) return;
          event.preventDefault();
          navigateTo(view, { historyMode: 'push', partial: true });
        }, { signal: signal });
      }

      safeOn(globalThis, 'popstate', function () {
        closeAllOverlays();
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
    bindEscapeToClose: bindEscapeToClose,
    buildTrail: buildTrail
  };
})();
