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

  // ── Enterprise DS — primitivos reutilizáveis (camada .ds-*) ──────────────

  function dsEsc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // Pipeline de status do EPI (solicitado → aprovado → entregue → assinado).
  // steps: [{ key, label }]  ·  currentKey: chave do estágio atual.
  // Estágios antes do atual = is-done; o atual = is-current.
  function dsStatusPipeline(steps, currentKey) {
    const list = Array.isArray(steps) ? steps : [];
    const idx = list.findIndex((s) => String(s && s.key) === String(currentKey));
    const nodes = list.map((step, i) => {
      const cls = idx >= 0 && i < idx ? 'is-done'
        : idx >= 0 && i === idx ? 'is-current'
          : '';
      return `<span class="ds-pipeline__node ${cls}"><span class="ds-dot" aria-hidden="true"></span>${dsEsc(step && step.label)}</span>`;
    }).join('');
    return `<span class="ds-pipeline" role="list" aria-label="Status">${nodes}</span>`;
  }

  // Banner de alerta (estoque crítico / CA vencendo).
  // opts: { message, variant:'warning'|'danger', ctaLabel, ctaId, icon }
  function dsAlertBanner(opts) {
    const o = opts || {};
    const variant = o.variant === 'danger' ? ' ds-alert-banner--danger' : '';
    const role = o.variant === 'danger' ? 'alert' : 'status';
    const icon = o.icon || '⚠';
    const cta = o.ctaLabel
      ? `<button type="button" class="btn btn-sm btn-primary ds-alert-banner__cta"${o.ctaId ? ` id="${dsEsc(o.ctaId)}"` : ''}>${dsEsc(o.ctaLabel)}</button>`
      : '';
    return `<div class="ds-alert-banner${variant}" role="${role}">`
      + `<span class="ds-alert-banner__icon" aria-hidden="true">${dsEsc(icon)}</span>`
      + `<span class="ds-alert-banner__text">${dsEsc(o.message)}</span>${cta}</div>`;
  }

  // Verifica se a resposta a um desafio de identidade confere (case/acentos-insensível).
  function dsChallengeMatches(input, expected) {
    const norm = (v) => String(v == null ? '' : v).trim().toLowerCase()
      .normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    if (norm(expected) === '') { return true; }
    return norm(input) === norm(expected);
  }

  // Modal de confirmação acessível (substitui window.confirm). Promise<boolean>.
  // opts: { title, message, confirmLabel, cancelLabel, variant:'danger'|'warning',
  //         challenge:{ label, expected, placeholder } }
  function dsConfirm(opts) {
    const o = opts || {};
    if (typeof document === 'undefined' || !document.body) {
      const ok = typeof globalThis.confirm === 'function' ? globalThis.confirm(o.message || '') : true;
      return Promise.resolve(!!ok);
    }
    return new Promise((resolve) => {
      const overlay = document.createElement('div');
      overlay.className = 'modal-overlay';
      overlay.style.zIndex = 'var(--z-modal)';
      const danger = o.variant === 'danger';
      const challenge = o.challenge && o.challenge.expected != null ? o.challenge : null;
      overlay.innerHTML =
        `<div class="modal-card card" role="dialog" aria-modal="true" aria-labelledby="ds-confirm-title" style="max-width:440px;display:flex;flex-direction:column;gap:12px;">
          <h3 id="ds-confirm-title">${dsEsc(o.title || 'Confirmar')}</h3>
          <p style="margin:0;color:var(--muted);">${dsEsc(o.message || '')}</p>
          ${challenge ? `<label style="display:flex;flex-direction:column;gap:4px;font-size:13px;"><span>${dsEsc(challenge.label || 'Confirme sua identidade')}</span><input type="text" class="ds-confirm-challenge" autocomplete="off" placeholder="${dsEsc(challenge.placeholder || '')}"></label><div class="ds-confirm-challenge-err field-error-msg" role="alert" hidden></div>` : ''}
          <div class="action-group" style="justify-content:flex-end;gap:8px;">
            <button type="button" class="btn btn-ghost ds-confirm-cancel">${dsEsc(o.cancelLabel || 'Cancelar')}</button>
            <button type="button" class="btn ${danger ? 'btn-danger' : 'btn-primary'} ds-confirm-ok">${dsEsc(o.confirmLabel || 'Confirmar')}</button>
          </div>
        </div>`;
      document.body.appendChild(overlay);
      const okBtn = overlay.querySelector('.ds-confirm-ok');
      const cancelBtn = overlay.querySelector('.ds-confirm-cancel');
      const input = overlay.querySelector('.ds-confirm-challenge');
      const errEl = overlay.querySelector('.ds-confirm-challenge-err');
      const close = (result) => {
        if (!overlay.isConnected) { return; }
        document.removeEventListener('keydown', onKey);
        overlay.remove();
        resolve(result);
      };
      const onKey = (e) => {
        if (e.key === 'Escape') { close(false); }
        else if (e.key === 'Enter' && document.activeElement !== cancelBtn) { confirm(); }
      };
      const confirm = () => {
        if (challenge && !dsChallengeMatches(input && input.value, challenge.expected)) {
          if (errEl) { errEl.hidden = false; errEl.textContent = challenge.error || 'Identidade não confere.'; }
          if (input) { input.focus(); }
          return;
        }
        close(true);
      };
      okBtn.addEventListener('click', confirm);
      cancelBtn.addEventListener('click', () => close(false));
      overlay.addEventListener('click', (e) => { if (e.target === overlay) { close(false); } });
      document.addEventListener('keydown', onKey);
      setTimeout(() => { (input || cancelBtn).focus(); }, 0);
    });
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  const uiExports = {
    renderBadge,
    activeLabel,
    roleLabel,
    userStatusBadges,
    showToast,
    dsEsc,
    dsStatusPipeline,
    dsAlertBanner,
    dsChallengeMatches,
    dsConfirm
  };

  for (const [name, fn] of Object.entries(uiExports)) {
    if (typeof globalThis[name] === 'undefined') {globalThis[name] = fn;}
  }
  globalThis.__EPI_UI_HELPERS__ = Object.freeze({ ...uiExports });

  const helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
  Object.assign(helpers, uiExports);
  globalThis.__EPI_FRONTEND_HELPERS__ = helpers;
})();
