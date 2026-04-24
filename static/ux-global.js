(function () {
  if (globalThis.__EPI_UX_GLOBAL_LOADED__) return;
  globalThis.__EPI_UX_GLOBAL_LOADED__ = true;

  const helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
  const safeOn = typeof helpers.safeOn === 'function'
    ? helpers.safeOn
    : function (target, eventName, handler, options) {
      if (!target || typeof target.addEventListener !== 'function') return false;
      target.addEventListener(eventName, handler, options);
      return true;
    };

  function parseFlagValue(value) {
    if (value === '1') return true;
    if (value === '0') return false;
    return null;
  }

  function isUxGlobalEnabled() {
    try {
      if (typeof helpers.getFeatureFlag === 'function') {
        return helpers.getFeatureFlag('ux_global_enabled', { defaultValue: false, allowStorage: true });
      }
      const params = new URLSearchParams(globalThis.location.search);
      const queryValue = parseFlagValue(params.get('ux_global'));
      if (queryValue !== null) return queryValue;
      const stored = parseFlagValue(localStorage.getItem('ux_global_enabled'));
      if (stored !== null) return stored;
    } catch (_error) {
      return false;
    }
    return false;
  }

  if (!isUxGlobalEnabled()) return;

  const TARGET_VIEWS = Object.freeze(['dashboard', 'colaboradores', 'gestao-colaborador', 'epis', 'estoque']);
  const VIEW_META = Object.freeze({
    dashboard: { title: 'Dashboard', subtitle: 'Visão consolidada de indicadores, alertas e pendências operacionais.' },
    colaboradores: { title: 'Cadastro de Colaborador', subtitle: 'Cadastro estruturado com foco em conferência e rastreabilidade dos dados.' },
    'gestao-colaborador': { title: 'Gestão de Colaborador', subtitle: 'Administração de colaboradores já cadastrados com ações rápidas e seguras.' },
    epis: { title: 'Cadastro de EPI', subtitle: 'Cadastro padronizado de EPIs com apoio visual e melhor legibilidade.' },
    estoque: { title: 'Controle de Estoque', subtitle: 'Monitoramento de saldo, filtros e movimentações em uma visualização uniforme.' }
  });

  function enhanceHeader(viewName, viewElement) {
    if (!viewElement) return;
    const meta = VIEW_META[viewName] || { title: viewName, subtitle: '' };
    let header = viewElement.querySelector('.ux-global-page-header');
    if (!header) {
      header = document.createElement('header');
      header.className = 'ux-global-page-header';
      header.innerHTML = '<div><span class="ux-kicker">UX Global</span><h3></h3><p></p></div><span class="ux-active-dot">Ativo</span>';
      viewElement.insertBefore(header, viewElement.firstChild);
    }
    const titleNode = header.querySelector('h3');
    const subtitleNode = header.querySelector('p');
    if (titleNode) titleNode.textContent = meta.title;
    if (subtitleNode) subtitleNode.textContent = meta.subtitle;
  }

  function enhanceCards(viewElement) {
    viewElement.querySelectorAll('.card').forEach((card) => card.classList.add('ux-card'));
    viewElement.querySelectorAll('.phase3-context-bar').forEach((bar) => bar.classList.add('ux-card'));
  }

  function enhanceToolbars(viewElement) {
    viewElement.querySelectorAll('.qr-inline, .section-head, .topbar-actions, .action-group').forEach((toolbar) => {
      toolbar.classList.add('ux-toolbar');
    });
  }

  function enhanceEmptyStates(viewElement) {
    viewElement.querySelectorAll('tbody').forEach((tbody) => {
      const rows = Array.from(tbody.querySelectorAll('tr'));
      if (rows.length !== 1) return;
      const row = rows[0];
      const onlyCell = row.children.length === 1 ? row.children[0] : null;
      if (!onlyCell) return;
      const raw = (onlyCell.textContent || '').trim();
      const maybeEmpty = raw.startsWith('Sem ') || raw.startsWith('Nenhum') || raw.startsWith('Nenhuma');
      if (!maybeEmpty) return;
      row.classList.add('ux-empty-row');
      onlyCell.innerHTML = '<div class="ux-empty-state"><strong>Nenhum registro para os filtros atuais.</strong><small>Revise os filtros ou realize um novo cadastro para continuar.</small></div>';
    });

    const genericContainers = ['#alerts-list', '#latest-deliveries'];
    genericContainers.forEach((selector) => {
      const node = viewElement.querySelector(selector);
      if (!node) return;
      if (node.children.length > 0 || (node.textContent || '').trim()) return;
      node.innerHTML = '<div class="ux-empty-state"><strong>Sem conteúdo por enquanto.</strong><small>Assim que novos dados forem processados, eles aparecerão aqui.</small></div>';
    });
  }

  function enhanceLoadingStates(viewElement) {
    viewElement.querySelectorAll('[id*="loading"], .htmx-indicator, .dashboard-interactive-state').forEach((item) => {
      item.classList.add('ux-loading-state');
    });
  }

  function applyActiveView(viewName) {
    TARGET_VIEWS.forEach((item) => {
      const view = document.getElementById(item + '-view');
      if (!view) return;
      view.classList.toggle('ux-view-focus', item === viewName);
    });
  }

  function enhanceView(viewName) {
    if (!TARGET_VIEWS.includes(viewName)) return;
    const viewElement = document.getElementById(viewName + '-view');
    if (!viewElement) return;
    enhanceHeader(viewName, viewElement);
    enhanceCards(viewElement);
    enhanceToolbars(viewElement);
    enhanceEmptyStates(viewElement);
    enhanceLoadingStates(viewElement);
    applyActiveView(viewName);
  }

  function resolveActiveView() {
    const activeView = document.querySelector('.view.active');
    if (!activeView || !activeView.id.endsWith('-view')) return null;
    return activeView.id.replace(/-view$/, '');
  }

  function boot() {
    document.body.classList.add('ux-global-enabled');
    TARGET_VIEWS.forEach((viewName) => enhanceView(viewName));
    const active = resolveActiveView();
    if (active) applyActiveView(active);
  }

  safeOn(document, 'epi:viewchange', function (event) {
    try {
      const viewName = event?.detail?.view;
      if (!viewName) return;
      enhanceView(viewName);
    } catch (_error) {
      /* no-op */
    }
  });

  safeOn(globalThis, 'popstate', function () {
    const active = resolveActiveView();
    if (active) enhanceView(active);
  });

  safeOn(document, 'DOMContentLoaded', boot);
  if (document.readyState !== 'loading') boot();
})();
