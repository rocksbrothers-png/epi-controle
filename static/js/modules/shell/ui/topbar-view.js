'use strict';
/* global tr, escapeHtml, bindAppListener, definirPreferencias */
// Shell/Topbar UBX: contexto lido na chamada; preferências e autorização mantêm seus donos.
(function () {
  if (globalThis.__EPI_MODULE_TOPBAR_VIEW_LOADED__) { return; }
  globalThis.__EPI_MODULE_TOPBAR_VIEW_LOADED__ = true;

  function updateTopbarCompanyBadge() {
    const state = globalThis.__EPI_APP_STATE__;
    const badge = document.getElementById('topbar-company-badge');
    if (!badge) {return;}
    const company = state.user?.company_name;
    const unit = state.user?.unit_name || state.user?.current_unit_name;
    if (!company) {
      badge.hidden = false;
      badge.textContent = (globalThis.EpiI18n?.textFor?.(badge,'topbar.generalAccess','Acesso geral') ?? tr('topbar.generalAccess', 'Acesso geral'));
      badge.classList.add('topbar-company-badge--general');
      return;
    }
    badge.classList.remove('topbar-company-badge--general');
    badge.hidden = false;
    const label = unit ? `${company} · ${unit}` : company;
    badge.innerHTML = `<span class="topbar-company-badge__dot" aria-hidden="true"></span><span class="topbar-company-badge__text">${escapeHtml(label)}</span>`;
  }

  function applyThemeToggleUI() {
    const btn = document.getElementById('theme-toggle');
    if (!btn) {return;}
    const dark = document.documentElement.getAttribute('data-theme') === 'dark';
    btn.textContent = dark ? '☀️' : '🌙';
    btn.setAttribute('aria-pressed', dark ? 'true' : 'false');
    btn.title = dark ? (globalThis.EpiI18n?.attributeFor?.(btn,'title','theme.toDark','Tema escuro ativo — clique para claro') ?? tr('theme.toDark', 'Tema escuro ativo — clique para claro')) : (globalThis.EpiI18n?.attributeFor?.(btn,'title','theme.toLight','Tema claro ativo — clique para escuro') ?? tr('theme.toLight', 'Tema claro ativo — clique para escuro'));
  }

  function setupThemeToggle() {
    const btn = document.getElementById('theme-toggle');
    if (!btn) {return;}
    applyThemeToggleUI();
    // O botão da topbar era um SEGUNDO escritor de tema: aplicava no DOM e
    // gravava a chave de dispositivo por conta própria, sem passar pelo drawer.
    // Duas gravações independentes da mesma preferência é como uma delas
    // sobrevive a uma correção feita só na outra — foi o `ISOL C-12` que o
    // encontrou. Agora os dois caminhos têm o mesmo dono.
    bindAppListener(btn, 'click', () => {
      const dark = document.documentElement.getAttribute('data-theme') === 'dark';
      definirPreferencias({ tema: dark ? 'light' : 'dark' });
    });
  }

  const exports = { updateTopbarCompanyBadge, applyThemeToggleUI, setupThemeToggle };
  for (const [name, fn] of Object.entries(exports)) { globalThis[name] = fn; }
  globalThis.__EPI_TOPBAR_UI__ = Object.freeze({ ...exports });
})();
