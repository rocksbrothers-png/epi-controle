/**
 * tenant-init.js — carregado após i18n.js e antes de app.js
 *
 * Responsável por:
 * 1. Resolver o tenant (empresa) pelo hostname antes do login
 * 2. Aplicar cores, logo e título da empresa (White Label)
 * 3. Exibir seletor de idioma (dropdown no topo direito, estilo SaaS)
 * 4. Inicializar o motor de i18n (window.EpiI18n) e traduzir o DOM
 */

(function () {
  'use strict';

  const I18N = window.EpiI18n;

  /* ── Bandeiras SVG inline ────────────────────────────────────────────────── */
  /* Windows não renderiza emoji de bandeiras; usamos SVG para consistência.    */

  const FLAGS = {
    'pt-BR': '<svg viewBox="0 0 28 20" width="22" height="16" aria-hidden="true"><rect width="28" height="20" fill="#009b3a"/><path d="M14 2.5 25.5 10 14 17.5 2.5 10Z" fill="#fedf00"/><circle cx="14" cy="10" r="4" fill="#002776"/></svg>',
    'en-GB': '<svg viewBox="0 0 28 20" width="22" height="16" aria-hidden="true"><rect width="28" height="20" fill="#012169"/><path d="M0 0 28 20M28 0 0 20" stroke="#fff" stroke-width="4"/><path d="M0 0 28 20M28 0 0 20" stroke="#C8102E" stroke-width="2"/><path d="M14 0V20M0 10H28" stroke="#fff" stroke-width="6"/><path d="M14 0V20M0 10H28" stroke="#C8102E" stroke-width="3.5"/></svg>',
    'es-ES': '<svg viewBox="0 0 28 20" width="22" height="16" aria-hidden="true"><rect width="28" height="20" fill="#c60b1e"/><rect y="5" width="28" height="10" fill="#ffc400"/></svg>',
    'fr-FR': '<svg viewBox="0 0 28 20" width="22" height="16" aria-hidden="true"><rect width="28" height="20" fill="#fff"/><rect width="9.34" height="20" fill="#002395"/><rect x="18.66" width="9.34" height="20" fill="#ed2939"/></svg>',
    'nb-NO': '<svg viewBox="0 0 28 20" width="22" height="16" aria-hidden="true"><rect width="28" height="20" fill="#ef2b2d"/><path d="M10 0V20M0 10H28" stroke="#fff" stroke-width="6"/><path d="M10 0V20M0 10H28" stroke="#002868" stroke-width="3"/></svg>',
  };

  const LANGS = [
    { code: 'pt-BR', name: 'Português', region: 'Brasil',  iso: 'BR' },
    { code: 'en-GB', name: 'English',   region: 'England', iso: 'GB' },
    { code: 'es-ES', name: 'Español',   region: 'España',  iso: 'ES' },
    { code: 'fr-FR', name: 'Français',  region: 'France',  iso: 'FR' },
    { code: 'nb-NO', name: 'Bokmål',    region: 'Noreg',   iso: 'NO' },
  ];

  const LS_TENANT_KEY = 'epi_tenant';

  function langByCode(code) {
    return LANGS.find(l => l.code === code) || LANGS[0];
  }

  /* ── Tradução da tela de login (elementos sem data-i18n) ─────────────────── */

  function applyTranslationsToLogin() {
    const t = window.t || ((k) => k);
    const ph = {
      'login-username':          t('login.usernameHint'),
      'login-password':          t('login.passwordHint'),
      'recovery-username':       t('login.usernameHint'),
      'recovery-email-username': t('login.usernameHint'),
    };
    for (const [id, val] of Object.entries(ph)) {
      const el = document.getElementById(id);
      if (el && val) el.setAttribute('placeholder', val);
    }

    const labelMap = {
      'login-username':          t('login.username'),
      'login-password':          t('login.password'),
      'recovery-username':       t('login.username'),
      'recovery-email-username': t('login.username'),
    };
    for (const [id, text] of Object.entries(labelMap)) {
      const input = document.getElementById(id);
      if (!input) continue;
      const label = document.querySelector(`label[for="${id}"]`);
      if (label && !label.querySelector('input') && text) label.textContent = text;
    }

    const loginBtn = document.querySelector('#login-form button[type="submit"]');
    if (loginBtn) loginBtn.textContent = t('login.button');

    const forgotBtn = document.getElementById('forgot-password-btn');
    if (forgotBtn) forgotBtn.textContent = t('login.forgotPassword');

    const recoverBtn = document.getElementById('recovery-submit');
    if (recoverBtn) recoverBtn.textContent = t('login.button');

    const h2 = document.querySelector('#login-form h2');
    if (h2) h2.textContent = t('login.title');
  }

  /* ── Tenant & Branding ───────────────────────────────────────────────────── */

  function applyBranding(branding, tenantName) {
    if (!branding) return;
    const root = document.documentElement;

    if (branding.primary_color && /^#[0-9A-Fa-f]{3,6}$/.test(branding.primary_color)) {
      root.style.setProperty('--accent', branding.primary_color);
    }
    if (branding.secondary_color && /^#[0-9A-Fa-f]{3,6}$/.test(branding.secondary_color)) {
      root.style.setProperty('--accent-secondary', branding.secondary_color);
    }
    if (branding.accent_color && /^#[0-9A-Fa-f]{3,6}$/.test(branding.accent_color)) {
      root.style.setProperty('--accent-highlight', branding.accent_color);
    }

    const logoEl = document.getElementById('login-brand-logo');
    if (logoEl) {
      const logoSrc = branding.login_logo_type || branding.logo_type || '';
      if (logoSrc && logoSrc.startsWith('data:')) {
        logoEl.innerHTML = `<img src="${logoSrc}" alt="${escHtml(tenantName || 'Logo')}" class="tenant-login-logo">`;
      }
    }

    if (tenantName) document.title = `${tenantName} — EPI Controle`;

    if (branding.institutional_message) {
      const msgEl = document.getElementById('login-institutional-msg');
      if (msgEl) {
        msgEl.textContent = branding.institutional_message;
        msgEl.style.display = 'block';
      }
    }
  }

  async function resolveTenant() {
    const host = window.location.hostname;
    const pathSlug = (window.location.pathname.split('/')[1] || '').toLowerCase();

    let url = `/api/tenant/resolve?host=${encodeURIComponent(host)}`;
    if (pathSlug && !pathSlug.startsWith('api')) {
      url += `&slug=${encodeURIComponent(pathSlug)}`;
    }

    try {
      const res = await fetch(url, { headers: { 'Accept': 'application/json' } });
      if (res.ok) {
        const data = await res.json();
        if (data && data.ok) {
          try { localStorage.setItem(LS_TENANT_KEY, JSON.stringify(data)); } catch {}
          window.__epiTenant = data;
          return data;
        }
        return null; // host genérico sem tenant (caso normal)
      }
    } catch {}

    try {
      const cached = localStorage.getItem(LS_TENANT_KEY);
      if (cached) {
        const data = JSON.parse(cached);
        window.__epiTenant = data;
        return data;
      }
    } catch {}

    return null;
  }

  /* ── Seletor de idioma (dropdown topo direito) ───────────────────────────── */

  let _outsideHandler = null;

  function closeDropdown(widget) {
    const menu = widget.querySelector('.epi-lang-menu');
    const trigger = widget.querySelector('.epi-lang-trigger');
    if (menu) menu.classList.remove('is-open');
    if (trigger) trigger.setAttribute('aria-expanded', 'false');
    if (_outsideHandler) {
      document.removeEventListener('click', _outsideHandler);
      _outsideHandler = null;
    }
  }

  function openDropdown(widget) {
    const menu = widget.querySelector('.epi-lang-menu');
    const trigger = widget.querySelector('.epi-lang-trigger');
    if (menu) menu.classList.add('is-open');
    if (trigger) trigger.setAttribute('aria-expanded', 'true');
    _outsideHandler = (e) => { if (!widget.contains(e.target)) closeDropdown(widget); };
    setTimeout(() => document.addEventListener('click', _outsideHandler), 0);
  }

  function renderLanguageSelector(activeLang) {
    const existing = document.getElementById('epi-lang-widget');
    if (existing) existing.remove();

    const active = langByCode(activeLang);

    const widget = document.createElement('div');
    widget.id = 'epi-lang-widget';
    widget.className = 'epi-lang-widget';

    const trigger = document.createElement('button');
    trigger.type = 'button';
    trigger.className = 'epi-lang-trigger';
    trigger.setAttribute('aria-haspopup', 'listbox');
    trigger.setAttribute('aria-expanded', 'false');
    trigger.setAttribute('aria-label', `Idioma: ${active.name} - ${active.region}`);
    trigger.innerHTML =
      `<span class="epi-lang-flag">${FLAGS[active.code] || ''}</span>` +
      `<span class="epi-lang-iso">${active.iso}</span>` +
      `<svg class="epi-lang-caret" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg>`;

    const menu = document.createElement('div');
    menu.className = 'epi-lang-menu';
    menu.setAttribute('role', 'listbox');

    for (const lang of LANGS) {
      const opt = document.createElement('button');
      opt.type = 'button';
      opt.className = 'epi-lang-option' + (lang.code === activeLang ? ' is-active' : '');
      opt.setAttribute('role', 'option');
      opt.setAttribute('aria-selected', String(lang.code === activeLang));
      opt.title = `${lang.name} — ${lang.region}`;
      opt.innerHTML =
        `<span class="epi-lang-flag">${FLAGS[lang.code] || ''}</span>` +
        `<span class="epi-lang-iso">${lang.iso}</span>` +
        `<span class="epi-lang-name">${lang.name}</span>` +
        `<span class="epi-lang-region">${lang.region}</span>`;

      opt.addEventListener('click', async (e) => {
        e.stopPropagation();
        closeDropdown(widget);
        if (lang.code === (I18N && I18N.lang)) return;
        if (I18N) await I18N.setLang(lang.code);
        applyTranslationsToLogin();
        renderLanguageSelector(lang.code);
      });

      menu.appendChild(opt);
    }

    trigger.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = trigger.getAttribute('aria-expanded') === 'true';
      if (isOpen) closeDropdown(widget); else openDropdown(widget);
    });

    widget.appendChild(trigger);
    widget.appendChild(menu);
    document.body.appendChild(widget);
  }

  /* ── Mensagem institucional placeholder ──────────────────────────────────── */

  function injectInstitutionalMsgPlaceholder() {
    const loginPanel = document.querySelector('.login-panel > div');
    if (!loginPanel || document.getElementById('login-institutional-msg')) return;
    const msg = document.createElement('p');
    msg.id = 'login-institutional-msg';
    msg.style.cssText = 'display:none;font-size:13px;color:var(--muted);margin:8px 0 0;line-height:1.4;';
    loginPanel.appendChild(msg);
  }

  /* ── Helpers ─────────────────────────────────────────────────────────────── */

  function escHtml(str) {
    return String(str || '').replace(/[&<>"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[c]);
  }

  /* ── Init ────────────────────────────────────────────────────────────────── */

  async function init() {
    injectInstitutionalMsgPlaceholder();

    const tenantData = await resolveTenant();
    const tenantDefault = tenantData?.i18n?.default_language || '';

    // Inicializa o motor de i18n com o idioma resolvido
    let activeLang = 'pt-BR';
    if (I18N) {
      activeLang = I18N.resolveInitialLang(tenantDefault);
      await I18N.setLang(activeLang, { persist: false });
    }

    if (tenantData?.branding) {
      applyBranding(tenantData.branding, tenantData.tenant?.name);
    }

    applyTranslationsToLogin();
    renderLanguageSelector(activeLang);

    // Re-traduz a tela de login sempre que o idioma mudar (inclui mudanças vindas do app)
    window.addEventListener('epi:langchange', () => {
      applyTranslationsToLogin();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
