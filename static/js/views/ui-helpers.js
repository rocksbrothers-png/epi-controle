'use strict';

// Helpers de apresentação (refatoração JS — Fase 6 piloto).
//
// Funções de renderização de strings reutilizadas em múltiplas views de app.js.
// São puras (sem DOM, sem estado): recebem dados e retornam strings HTML seguras.
// Servem de piloto para a Fase 6 (extração progressiva das views individuais).
(function () {
  if (globalThis.__EPI_MODULE_UI_HELPERS_LOADED__) {return;}
  globalThis.__EPI_MODULE_UI_HELPERS_LOADED__ = true;

  // ── Funções de badge/label (puras) ───────────────────────────────────────

  function renderBadge(type, value, label) {
    return `<span class="badge badge-${type}-${value}">${label}</span>`;
  }

  function activeLabel(active) {
    const tr = globalThis.trEpi || ((_key, fallback) => fallback);
    return Number(active) === 1
      ? tr('user.active', 'Ativo')
      : tr('user.inactive', 'Inativo');
  }

  function roleLabel(role) {
    const tr = globalThis.trEpi || ((_key, fallback) => fallback);
    const labels = globalThis.ROLE_LABELS || {};
    return tr('role.' + role, labels[role] || role);
  }

  function userStatusBadges(user) {
    const badges = [
      renderBadge('status', Number(user.active) === 1 ? 'active' : 'inactive', activeLabel(user.active))
    ];
    if (Number(user.force_password_change || 0) === 1) {
      badges.push(renderBadge('status', 'warning', 'Senha provisória'));
    }
    return badges.join(' ');
  }

  // ── Toast (DOM, usa __EPI_REFS__ ou fallback) ────────────────────────────

  function showToast(message, type = 'info', durationMs = 4000) {
    if (typeof globalThis.showToast === 'function' && globalThis.showToast !== showToast) {
      return globalThis.showToast(message, type, durationMs);
    }
    // Implementação real (restaurada): a Fase 8 removeu showToast de app.js e
    // deixou apenas um stub aqui, fazendo todo toast cair em console.warn. Renderiza
    // o elemento #epi-toast estilizado por styles.css (seção 12. Toast / Snackbar).
    if (typeof document === 'undefined' || !document.body) {
      console.warn('[ui-helpers] showToast (sem DOM):', type, message);
      return;
    }
    const existing = document.getElementById('epi-toast');
    if (existing) {existing.remove();}
    const toast = document.createElement('div');
    toast.id = 'epi-toast';
    const bg = type === 'success' ? '#226b4c'
      : type === 'error' ? '#a13b2b'
      : type === 'warning' ? '#c08822'
      : '#1d64c8';
    toast.style.background = bg;
    toast.style.color = '#fff';
    toast.setAttribute('role', type === 'error' ? 'alert' : 'status');
    toast.textContent = String(message == null ? '' : message);
    document.body.appendChild(toast);
    const ttl = Number(durationMs) > 0 ? Number(durationMs) : 4000;
    setTimeout(() => { if (toast.isConnected) {toast.remove();} }, ttl);
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  const uiExports = {
    renderBadge,
    activeLabel,
    roleLabel,
    userStatusBadges,
    showToast
  };

  for (const [name, fn] of Object.entries(uiExports)) {
    if (typeof globalThis[name] === 'undefined') {globalThis[name] = fn;}
  }
  globalThis.__EPI_UI_HELPERS__ = Object.freeze({ ...uiExports });

  const helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
  Object.assign(helpers, uiExports);
  globalThis.__EPI_FRONTEND_HELPERS__ = helpers;
})();
