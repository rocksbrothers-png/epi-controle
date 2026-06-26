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

  // Stepper horizontal (.ds-stepper). steps: [{label}] · currentIndex (0-based).
  // Passos antes do atual = is-done; o atual = is-active.
  function dsStepper(steps, currentIndex) {
    const list = Array.isArray(steps) ? steps : [];
    const cur = Number(currentIndex);
    const nodes = list.map((step, i) => {
      const cls = i < cur ? 'is-done' : i === cur ? 'is-active' : '';
      const bullet = i < cur ? '✓' : String(i + 1);
      return `<div class="ds-stepper__step ${cls}">`
        + `<div class="ds-stepper__bullet">${dsEsc(bullet)}</div>`
        + `<div class="ds-stepper__label">${dsEsc(step && (step.label != null ? step.label : step))}</div></div>`;
    }).join('');
    return `<div class="ds-stepper" role="list" aria-label="Etapas">${nodes}</div>`;
  }

  // Timeline vertical (.ds-timeline). items: [{ title, time, muted }].
  function dsTimeline(items) {
    const list = Array.isArray(items) ? items : [];
    if (!list.length) { return ''; }
    const li = list.map((it) => {
      const o = it || {};
      const muted = o.muted ? ' is-muted' : '';
      const time = o.time ? `<div class="ds-timeline__time">${dsEsc(o.time)}</div>` : '';
      const desc = o.desc ? `<div>${dsEsc(o.desc)}</div>` : '';
      return `<li class="ds-timeline__item${muted}">${time}<div class="ds-timeline__title">${dsEsc(o.title)}</div>${desc}</li>`;
    }).join('');
    return `<ul class="ds-timeline">${li}</ul>`;
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

  // Paginação client-side (puro). Retorna a fatia da página + metadados.
  function dsPaginate(items, page, perPage) {
    const list = Array.isArray(items) ? items : [];
    const pp = Number(perPage) > 0 ? Number(perPage) : 20;
    const totalPages = Math.max(1, Math.ceil(list.length / pp));
    const p = Math.min(Math.max(1, Number(page) || 1), totalPages);
    const start = (p - 1) * pp;
    return { page: p, totalPages, perPage: pp, total: list.length, start, pageItems: list.slice(start, start + pp) };
  }

  // Controles de paginação (.ds-pagination). Retorna '' quando cabe numa página.
  function dsPaginationControls(info) {
    const i = info || {};
    const page = Number(i.page) || 1;
    const totalPages = Number(i.totalPages) || 1;
    const total = Number(i.total) || 0;
    const perPage = Number(i.perPage) || 20;
    if (total <= perPage) { return ''; }
    const from = (page - 1) * perPage + 1;
    const to = Math.min(total, page * perPage);
    const btn = (label, target, opts) => {
      const o = opts || {};
      return `<button type="button" class="ds-pagination__btn${o.active ? ' is-active' : ''}" data-ds-page="${target}" aria-label="${dsEsc(o.aria || ('Página ' + target))}"${o.active ? ' aria-current="page"' : ''}${o.disabled ? ' disabled' : ''}>${dsEsc(label)}</button>`;
    };
    const win = 2;
    const seq = [];
    for (let n = 1; n <= totalPages; n++) {
      if (n === 1 || n === totalPages || (n >= page - win && n <= page + win)) { seq.push(n); }
      else if (seq[seq.length - 1] !== '…') { seq.push('…'); }
    }
    const pageBtns = seq.map((n) => n === '…'
      ? '<span class="ds-pagination__ellipsis" aria-hidden="true">…</span>'
      : btn(String(n), n, { active: n === page })).join('');
    const infoEl = `<span class="ds-pagination__info">${from}–${to} de ${total}</span>`;
    return `<nav class="ds-pagination" aria-label="Paginação">${infoEl}`
      + `${btn('‹', page - 1, { disabled: page <= 1, aria: 'Página anterior' })}${pageBtns}`
      + `${btn('›', page + 1, { disabled: page >= totalPages, aria: 'Próxima página' })}</nav>`;
  }

  // Linhas de skeleton para carregamento de tabela (reusa .skeleton existente).
  function dsSkeletonRows(rows, cols) {
    const r = Number(rows) > 0 ? Number(rows) : 3;
    const c = Number(cols) > 0 ? Number(cols) : 1;
    let out = '';
    for (let i = 0; i < r; i++) {
      let cells = '';
      for (let j = 0; j < c; j++) { cells += '<td><div class="skeleton skeleton-text" style="width:80%"></div></td>'; }
      out += `<tr class="ds-skeleton-row" aria-hidden="true">${cells}</tr>`;
    }
    return out;
  }

  // Estado de tabela (linha <tr><td colspan>) — empty / error / loading.
  // opts: { colspan, kind:'empty'|'error'|'loading', message, title,
  //         ctaLabel, ctaId, icon, rows (loading) }
  function dsTableState(opts) {
    const o = opts || {};
    const colspan = Number(o.colspan) > 0 ? Number(o.colspan) : 1;
    const kind = o.kind || 'empty';
    if (kind === 'loading') {
      return dsSkeletonRows(o.rows, colspan);
    }
    const isError = kind === 'error';
    const cta = o.ctaLabel
      ? `<button type="button" class="btn btn-sm ${isError ? 'btn-primary' : 'btn-ghost'} ds-table-state__cta"${o.ctaId ? ` id="${dsEsc(o.ctaId)}"` : ''}>${dsEsc(o.ctaLabel)}</button>`
      : '';
    let inner;
    if (isError) {
      const title = o.title || 'Falha ao carregar';
      inner = `<div class="ds-error-state"><div class="ds-error-state__title">${dsEsc(title)}</div>`
        + `<div>${dsEsc(o.message || '')}</div>${cta}</div>`;
    } else {
      const icon = o.icon || '∅';
      const title = o.title ? `<div class="ds-empty__title">${dsEsc(o.title)}</div>` : '';
      inner = `<div class="ds-empty"><div class="ds-empty__icon" aria-hidden="true">${dsEsc(icon)}</div>`
        + `${title}<div class="ds-empty__desc">${dsEsc(o.message || '')}</div>${cta}</div>`;
    }
    return `<tr><td colspan="${colspan}">${inner}</td></tr>`;
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
    dsStepper,
    dsTimeline,
    dsAlertBanner,
    dsChallengeMatches,
    dsConfirm,
    dsSkeletonRows,
    dsTableState,
    dsPaginate,
    dsPaginationControls
  };

  for (const [name, fn] of Object.entries(uiExports)) {
    if (typeof globalThis[name] === 'undefined') {globalThis[name] = fn;}
  }
  globalThis.__EPI_UI_HELPERS__ = Object.freeze({ ...uiExports });

  const helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
  Object.assign(helpers, uiExports);
  globalThis.__EPI_FRONTEND_HELPERS__ = helpers;
})();
