'use strict';

(function () {
  const globalScope = typeof globalThis !== 'undefined' ? globalThis : window;
  const doc = typeof document === 'undefined' ? null : document;
  if (!doc) return;
  if (globalScope.__EPI_ESTOQUE_BOUND__) return;
  globalScope.__EPI_ESTOQUE_BOUND__ = true;

  const helpers = globalScope.__EPI_FRONTEND_HELPERS__ || {};
  const safeOn = typeof helpers.safeOn === 'function'
    ? helpers.safeOn
    : (target, eventName, handler, options) => {
      if (!target || typeof target.addEventListener !== 'function') return;
      target.addEventListener(eventName, handler, options);
    };
  const debugLog = typeof helpers.debugLog === 'function'
    ? helpers.debugLog
    : () => {};
  const reportNonCriticalError = typeof helpers.reportNonCriticalError === 'function'
    ? helpers.reportNonCriticalError
    : () => {};
  const isViewActive = typeof helpers.isViewActive === 'function'
    ? helpers.isViewActive
    : (selector) => Boolean(doc.querySelector(selector)?.classList.contains('active'));
  const resolveFeatureFlag = typeof helpers.getFeatureFlag === 'function'
    ? helpers.getFeatureFlag
    : (_flagName, options = {}) => Boolean(options.defaultValue ?? false);

  globalScope.__EPI_SETUP_ESTOQUE_PILOT__ = function setupEstoquePilot(config = {}) {
    try {
      const enabled = typeof config.enabled === 'boolean'
        ? config.enabled
        : resolveFeatureFlag('estoque_htmx_enabled', { defaultValue: false, allowStorage: false });
      const viewSelector = config.viewSelector || '#estoque-view';
      const root = doc.querySelector(viewSelector);
      if (!root) return;
      if (config.onlyWhenViewActive === true && !isViewActive(viewSelector)) return;

      const status = doc.querySelector(config.statusSelector || '#phase2-estoque-status');
      const loading = doc.querySelector(config.loadingSelector || '#phase2-estoque-loading');
      const refreshButton = root.querySelector('[data-estoque-refresh]');
      const filtersContainer = root.querySelector('[data-estoque-filters]');

      const setLoading = (active) => {
        if (!loading) return;
        loading.hidden = !active;
        loading.classList.toggle('is-active', active);
      };

      const setStatus = (message) => {
        if (!status) return;
        status.textContent = message;
      };

      if (!enabled) {
        setLoading(false);
        return;
      }

      if (root.dataset.estoquePilotBound === '1') return;
      root.dataset.estoquePilotBound = '1';
      debugLog('[fase2:estoque] setup concluído');

      let updateTimer = null;
      const queueProgressFeedback = () => {
        setLoading(true);
        setStatus('Aplicando filtros da listagem de estoque…');
        if (updateTimer) globalScope.clearTimeout(updateTimer);
        updateTimer = globalScope.setTimeout(() => {
          setLoading(false);
          setStatus('Listagem de estoque atualizada (piloto de leitura ativo).');
        }, 220);
      };

      safeOn(filtersContainer, 'input', (event) => {
        const target = event?.target;
        if (!target || typeof target.id !== 'string') return;
        if (!target.id.startsWith('stock-filter-')) return;
        queueProgressFeedback();
      });

      safeOn(filtersContainer, 'change', (event) => {
        const target = event?.target;
        if (!target || typeof target.id !== 'string') return;
        if (!target.id.startsWith('stock-filter-')) return;
        queueProgressFeedback();
      });

      safeOn(refreshButton, 'click', (event) => {
        event.preventDefault();
        queueProgressFeedback();
        if (typeof globalScope.__EPI_REFRESH_ESTOQUE_LISTA__ === 'function') {
          void globalScope.__EPI_REFRESH_ESTOQUE_LISTA__();
        }
      });

      safeOn(doc.body, 'htmx:afterRequest', (event) => {
        const trigger = event?.detail?.elt;
        if (!trigger || trigger.dataset?.phase2RefreshModule !== (config.moduleName || 'estoque')) return;
        setLoading(false);
        setStatus('Atualização parcial do estoque concluída sem recarregar a tela.');
      });

      safeOn(doc.body, 'htmx:responseError', (event) => {
        const trigger = event?.detail?.elt;
        if (!trigger || trigger.dataset?.phase2RefreshModule !== (config.moduleName || 'estoque')) return;
        setLoading(false);
        setStatus('Falha na atualização parcial do estoque. Fluxo clássico permanece disponível.');
      });
    } catch (error) {
      reportNonCriticalError('[fase2:estoque] setup falhou', error);
    }
  };
})();
