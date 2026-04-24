'use strict';

(function () {
  const globalScope = typeof globalThis !== 'undefined' ? globalThis : window;
  const doc = typeof document === 'undefined' ? null : document;
  if (!doc) return;
  if (globalScope.__EPI_GESTAO_COLAB_BOUND__) return;
  globalScope.__EPI_GESTAO_COLAB_BOUND__ = true;

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

  globalScope.__EPI_SETUP_GESTAO_COLAB_PILOT__ = function setupGestaoColabPilot(config = {}) {
    try {
      const enabled = typeof config.enabled === 'boolean'
        ? config.enabled
        : resolveFeatureFlag('gestao_colaborador_htmx_enabled', { defaultValue: false, allowStorage: false });
      const viewSelector = config.viewSelector || '#gestao-colaborador-view';
      const root = doc.querySelector(viewSelector);
      if (!root) return;
      if (config.onlyWhenViewActive === true && !isViewActive(viewSelector)) return;

      const status = doc.querySelector(config.statusSelector || '#phase2-gestao-colab-status');
      const loading = doc.querySelector(config.loadingSelector || '#phase2-gestao-colab-loading');
      const refreshButton = root.querySelector('[data-gestao-colab-refresh]');
      const filtersContainer = root.querySelector('[data-gestao-colab-filters]');

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

      if (root.dataset.gestaoColabPilotBound === '1') return;
      root.dataset.gestaoColabPilotBound = '1';
      debugLog('[fase2:gestao-colaborador] setup concluído');

      let updateTimer = null;
      const queueProgressFeedback = () => {
        setLoading(true);
        setStatus('Aplicando filtros de gestão…');
        if (updateTimer) globalScope.clearTimeout(updateTimer);
        updateTimer = globalScope.setTimeout(() => {
          setLoading(false);
          setStatus('Gestão de colaboradores atualizada (piloto ativo).');
        }, 220);
      };

      safeOn(filtersContainer, 'input', (event) => {
        const target = event?.target;
        if (!target || typeof target.id !== 'string') return;
        if (!target.id.startsWith('employees-ops-filter-')) return;
        queueProgressFeedback();
      });

      safeOn(filtersContainer, 'change', (event) => {
        const target = event?.target;
        if (!target || typeof target.id !== 'string') return;
        if (!target.id.startsWith('employees-ops-filter-')) return;
        queueProgressFeedback();
      });

      safeOn(refreshButton, 'click', (event) => {
        event.preventDefault();
        queueProgressFeedback();
        if (typeof globalScope.__EPI_REFRESH_GESTAO_COLAB__ === 'function') {
          globalScope.__EPI_REFRESH_GESTAO_COLAB__();
        }
      });

      safeOn(doc.body, 'htmx:afterRequest', (event) => {
        const trigger = event?.detail?.elt;
        if (!trigger || trigger.dataset?.phase2RefreshModule !== (config.moduleName || 'gestao-colaborador')) return;
        setLoading(false);
        setStatus('Atualização parcial concluída sem recarregar a tela.');
      });

      safeOn(doc.body, 'htmx:responseError', (event) => {
        const trigger = event?.detail?.elt;
        if (!trigger || trigger.dataset?.phase2RefreshModule !== (config.moduleName || 'gestao-colaborador')) return;
        setLoading(false);
        setStatus('Falha na atualização parcial. Fluxo clássico permanece disponível.');
      });
    } catch (error) {
      reportNonCriticalError('[fase2:gestao-colaborador] setup falhou', error);
    }
  };
})();
