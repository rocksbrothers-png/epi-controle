'use strict';

(function () {
  const globalScope = typeof globalThis !== 'undefined' ? globalThis : window;
  const doc = typeof document === 'undefined' ? null : document;
  if (!doc) return;

  const safeOn = (target, eventName, handler, options) => {
    if (!target || typeof target.addEventListener !== 'function') return;
    target.addEventListener(eventName, handler, options);
  };

  const getFlagValue = () => {
    const queryValue = new URLSearchParams(globalScope.location?.search || '').get('ux_phase2_colab_list');
    if (queryValue === '1') return true;
    if (queryValue === '0') return false;

    try {
      const storageValue = String(globalScope.localStorage?.getItem('colaborador_list_htmx_enabled') || '').trim();
      if (storageValue === '1') return true;
      if (storageValue === '0') return false;
    } catch (_error) {
      // fail-safe: storage indisponível
    }
    return false;
  };

  globalScope.__EPI_SETUP_COLAB_LIST_PILOT__ = function setupColabListPilot(config = {}) {
    try {
      const enabled = typeof config.enabled === 'boolean' ? config.enabled : getFlagValue();
      const viewSelector = config.viewSelector || '#colaborador-list-view';
      const root = doc.querySelector(viewSelector);
      if (!root) return;

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

      let updateTimer = null;
      const queueProgressFeedback = () => {
        setLoading(true);
        setStatus('Aplicando filtros da listagem…');
        if (updateTimer) globalScope.clearTimeout(updateTimer);
        updateTimer = globalScope.setTimeout(() => {
          setLoading(false);
          setStatus('Listagem atualizada (pilot HTMX/Alpine ativo).');
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
        setStatus('Atualização parcial concluída sem recarregar a tela.');
      });

      safeOn(doc.body, 'htmx:responseError', (event) => {
        const trigger = event?.detail?.elt;
        if (!trigger || trigger.dataset?.phase2RefreshModule !== (config.moduleName || 'colaborador-lista')) return;
        setLoading(false);
        setStatus('Falha na atualização parcial. Fluxo clássico permanece disponível.');
      });
    } catch (err) {
      if (globalScope.__EPI_DEBUG__) console.warn('[colab-list]', err);
    }
  };
})();
