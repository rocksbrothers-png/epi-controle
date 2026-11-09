'use strict';

// Compras CO-1 — cartão "Limite de alçada de pedidos de compra" (camada UI).
//
// Vive em Configuração, ao lado do fluxo de aprovação (static/views/configuracao.html).
// O cartão só aparece para quem tem `purchase_limits:manage` (Administrador
// Geral) — esconder é conveniência de interface; quem autoriza é o backend.
// Monta sozinho ao entrar em Configuração (`epi:viewchange`), sem nada no app.js.
(function () {
  if (globalThis.__EPI_MODULE_PURCHASE_LIMITS_VIEW_LOADED__) { return; }
  globalThis.__EPI_MODULE_PURCHASE_LIMITS_VIEW_LOADED__ = true;

  const CARD_ID = 'purchase-limit-config-card';
  const MANAGE_PERMISSION = 'purchase_limits:manage';
  const HOST_VIEW = 'configuracao';

  function rules() { return globalThis.__EPI_PURCHASE_LIMITS_RULES__; }
  function limitsApi() { return globalThis.__EPI_PURCHASE_LIMITS_API__; }
  function appState() { return globalThis.__EPI_APP_STATE__ || {}; }
  function t(key, fallback, vars) {
    return typeof globalThis.trEpi === 'function' ? globalThis.trEpi(key, fallback, vars || {}) : fallback;
  }

  let generation = 0;
  let current = null;
  let busy = false;

  function el(id) { return globalThis.document ? globalThis.document.getElementById(id) : null; }

  function canManage() {
    const perms = appState().permissions || [];
    return Array.isArray(perms) && perms.includes(MANAGE_PERMISSION);
  }

  function locale() {
    const doc = globalThis.document;
    return (doc && doc.documentElement && doc.documentElement.lang) || 'pt-BR';
  }

  // Separadores do idioma ativo, só para exibição (o valor continua texto).
  function separators() {
    try {
      const parts = new Intl.NumberFormat(locale()).formatToParts(12345.6);
      return {
        group: (parts.find((p) => p.type === 'group') || {}).value || '.',
        decimal: (parts.find((p) => p.type === 'decimal') || {}).value || ','
      };
    } catch (_e) {
      return { group: '.', decimal: ',' };
    }
  }

  function formatDate(iso) {
    if (!iso) { return ''; }
    try {
      return new Intl.DateTimeFormat(locale(), { dateStyle: 'short', timeStyle: 'short' }).format(new Date(iso));
    } catch (_e) {
      return String(iso);
    }
  }

  function setFeedback(message, tone) {
    const node = el('purchase-limit-feedback');
    if (!node) { return; }
    node.textContent = message || '';
    node.dataset.tone = tone || '';
  }

  function companyLabel() {
    const state = appState();
    const user = state.user || {};
    const companies = Array.isArray(state.companies) ? state.companies : [];
    const company = companies.find((c) => String(c.id) === String(user.company_id));
    return (company && (company.trade_name || company.name)) || user.company_name || '';
  }

  function render() {
    const card = el(CARD_ID);
    if (!card) { return; }
    const view = current ? rules().describeLimits(current) : null;
    card.hidden = !canManage();
    const company = el('purchase-limit-company');
    if (company) { company.textContent = companyLabel(); }
    const value = el('purchase-limit-current');
    if (value) {
      value.textContent = view && view.configured
        ? `${view.currency} ${rules().formatLimit(view.value, separators())}`
        : t('purchase.limits.notConfigured', 'Sem limite configurado — todos os pedidos usam um nível de aprovação.');
    }
    const meta = el('purchase-limit-meta');
    if (meta) {
      meta.textContent = view && view.updatedAt
        ? t('purchase.limits.lastUpdate', 'Última alteração: {date} por {name}.', { date: formatDate(view.updatedAt), name: view.updatedByName || '—' })
        : '';
    }
    const remove = el('purchase-limit-remove-btn');
    if (remove) { remove.hidden = !(view && view.configured); }
    const editable = Boolean(view && view.canManage) && !busy;
    ['purchase-limit-input', 'purchase-limit-save-btn', 'purchase-limit-remove-btn'].forEach((id) => {
      const node = el(id);
      if (node) { node.disabled = !editable; }
    });
  }

  async function load() {
    const card = el(CARD_ID);
    if (!card) { return; }
    if (!canManage()) { card.hidden = true; return; }
    const user = appState().user;
    if (!user) { return; }
    const gen = ++generation;
    try {
      const data = await limitsApi().getPurchaseLimits(`actor_user_id=${encodeURIComponent(user.id)}`);
      if (gen !== generation) { return; }
      current = data;
      render();
    } catch (err) {
      if (gen !== generation) { return; }
      current = null;
      render();
      setFeedback((err && err.message) || t('purchase.limits.loadError', 'Não foi possível carregar o limite de alçada.'), 'error');
    }
  }

  async function submit(value) {
    const user = appState().user;
    if (!user || !current || busy) { return; }
    busy = true;
    render();
    setFeedback('');
    try {
      const data = await limitsApi().savePurchaseLimit({
        actor_user_id: user.id,
        value,
        expected_version: rules().describeLimits(current).version
      });
      current = data;
      setFeedback(value === null
        ? t('purchase.limits.removed', 'Limite de alçada removido.')
        : t('purchase.limits.saved', 'Limite de alçada salvo.'), 'success');
      const input = el('purchase-limit-input');
      if (input) { input.value = ''; }
    } catch (err) {
      // 409: outro usuário alterou antes — recarrega o valor vigente.
      // A mensagem do servidor já chega traduzida (describeApiError).
      setFeedback((err && err.message) || t('purchase.limits.saveError', 'Não foi possível salvar o limite de alçada.'), 'error');
      if (err && err.status === 409) { busy = false; await load(); return; }
    } finally {
      busy = false;
      render();
    }
  }

  function onSave(event) {
    if (event) { event.preventDefault(); }
    const input = el('purchase-limit-input');
    const parsed = rules().normalizeLimitInput(input ? input.value : '');
    if (!parsed.ok) {
      setFeedback(parsed.code === 'TOO_LARGE'
        ? t('purchase.limits.tooLarge', 'Valor acima do máximo permitido.')
        : t('purchase.limits.invalid', 'Informe um valor maior que zero, com até duas casas decimais (ex.: 15000,00).'), 'error');
      return;
    }
    submit(parsed.value);
  }

  async function onRemove(event) {
    if (event) { event.preventDefault(); }
    const dialogs = globalThis.__EPI_SHARED_DIALOGS__;
    const message = t('purchase.limits.removeConfirm', 'Remover o limite de alçada? Todos os pedidos voltarão a exigir um único nível de aprovação.');
    const confirmed = dialogs && typeof dialogs.confirmDestructive === 'function'
      ? await dialogs.confirmDestructive({ title: t('purchase.limits.remove', 'Remover limite'), message })
      : false;
    if (confirmed) { submit(null); }
  }

  function bind() {
    const doc = globalThis.document;
    if (!doc || typeof doc.addEventListener !== 'function') { return; }
    doc.addEventListener('epi:viewchange', (event) => {
      if (event && event.detail && event.detail.view === HOST_VIEW) { load(); }
    });
    doc.addEventListener('epi:langchange', render);
    const save = el('purchase-limit-save-btn');
    if (save) { save.addEventListener('click', onSave); }
    const remove = el('purchase-limit-remove-btn');
    if (remove) { remove.addEventListener('click', onRemove); }
  }

  function init() {
    bind();
    const card = el(CARD_ID);
    if (card && card.closest && card.closest('.view.active')) { load(); }
  }

  if (globalThis.document && globalThis.document.readyState === 'loading') {
    globalThis.document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }

  globalThis.__EPI_PURCHASE_LIMITS_VIEW__ = Object.freeze({ load, render, onSave, onRemove });
})();
