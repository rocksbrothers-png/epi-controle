'use strict';

(function () {
  const globalScope = typeof globalThis !== 'undefined' ? globalThis : window;
  const doc = typeof document === 'undefined' ? null : document;
  if (!doc) return;
  if (globalScope.__EPI_COLAB_LIST_BOUND__) return;
  globalScope.__EPI_COLAB_LIST_BOUND__ = true;

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

  globalScope.__EPI_SETUP_COLAB_LIST_PILOT__ = function setupColabListPilot(config = {}) {
    try {
      const enabled = typeof config.enabled === 'boolean'
        ? config.enabled
        : resolveFeatureFlag('colaborador_list_htmx_enabled', { defaultValue: false, allowStorage: false });
      const viewSelector = config.viewSelector || '#colaborador-list-view';
      const root = doc.querySelector(viewSelector);
      if (!root) return;
      if (config.onlyWhenViewActive === true && !isViewActive(viewSelector)) return;

      const status = doc.querySelector(config.statusSelector || '#phase2-colab-list-status');
      const loading = doc.querySelector(config.loadingSelector || '#phase2-colab-list-loading');
      const refreshButton = root.querySelector('[data-colab-list-refresh]');
      const filtersContainer = root.querySelector('[data-colab-list-filters]');

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

      if (root.dataset.colabListPilotBound === '1') return;
      root.dataset.colabListPilotBound = '1';
      debugLog('[fase2:colaborador-lista] setup concluído');

      let updateTimer = null;
      const queueProgressFeedback = () => {
        setLoading(true);
        setStatus('Aplicando filtros da listagem…');
        if (updateTimer) globalScope.clearTimeout(updateTimer);
        updateTimer = globalScope.setTimeout(() => {
          setLoading(false);
          setStatus('Lista atualizada.');
        }, 220);
      };

      safeOn(filtersContainer, 'input', (event) => {
        const target = event?.target;
        if (!target || typeof target.id !== 'string') return;
        if (!target.id.startsWith('employees-filter-')) return;
        queueProgressFeedback();
      });

      safeOn(filtersContainer, 'change', (event) => {
        const target = event?.target;
        if (!target || typeof target.id !== 'string') return;
        if (!target.id.startsWith('employees-filter-')) return;
        queueProgressFeedback();
      });

      safeOn(refreshButton, 'click', (event) => {
        event.preventDefault();
        queueProgressFeedback();
        if (typeof globalScope.__EPI_REFRESH_COLAB_LIST__ === 'function') {
          globalScope.__EPI_REFRESH_COLAB_LIST__();
        }
      });

      safeOn(doc.body, 'htmx:afterRequest', (event) => {
        const trigger = event?.detail?.elt;
        if (!trigger || trigger.dataset?.phase2RefreshModule !== (config.moduleName || 'colaborador-lista')) return;
        setLoading(false);
        setStatus('Lista atualizada.');
      });

      safeOn(doc.body, 'htmx:responseError', (event) => {
        const trigger = event?.detail?.elt;
        if (!trigger || trigger.dataset?.phase2RefreshModule !== (config.moduleName || 'colaborador-lista')) return;
        setLoading(false);
        setStatus('Não foi possível atualizar agora. Tente novamente.');
      });
    } catch (err) {
      reportNonCriticalError('[fase2:colaborador-lista] setup falhou', err);
    }
  };
})();
