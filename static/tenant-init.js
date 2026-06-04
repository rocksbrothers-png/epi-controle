/**
 * tenant-init.js — carregado antes do app.js
 *
 * Responsável por:
 * 1. Resolver o tenant (empresa) pelo hostname antes do login
 * 2. Aplicar cores, logo e título da empresa (White Label)
 * 3. Exibir seletor de idioma na tela de login
 * 4. Carregar e aplicar traduções
 */

(function () {
  'use strict';

  /* ── Constantes ──────────────────────────────────────────────────────────── */

  const SUPPORTED_LANGS = [
    { code: 'pt-BR', name: 'Português', region: 'Brasil',  flag: '🇧🇷' },
    { code: 'en-GB', name: 'English',   region: 'England', flag: '🇬🇧' },
    { code: 'es-ES', name: 'Español',   region: 'España',  flag: '🇪🇸' },
    { code: 'fr-FR', name: 'Français',  region: 'France',  flag: '🇫🇷' },
    { code: 'nb-NO', name: 'Bokmål',    region: 'Noreg',   flag: '🇳🇴' },
  ];

  const LS_LANG_KEY   = 'epi_language';
  const LS_TENANT_KEY = 'epi_tenant';

  /* ── Idioma ──────────────────────────────────────────────────────────────── */

  function getStoredLang() {
    try { return localStorage.getItem(LS_LANG_KEY) || ''; } catch { return ''; }
  }

  function storeLang(code) {
    try { localStorage.setItem(LS_LANG_KEY, code); } catch {}
  }

  function isValidLang(code) {
    return SUPPORTED_LANGS.some(l => l.code === code);
  }

  function detectBrowserLang() {
    const nav = (navigator.language || navigator.userLanguage || 'pt-BR').trim();
    if (isValidLang(nav)) return nav;
    const short = nav.split('-')[0].toLowerCase();
    const map = { pt: 'pt-BR', en: 'en-GB', es: 'es-ES', fr: 'fr-FR', nb: 'nb-NO', no: 'nb-NO' };
    return map[short] || 'pt-BR';
  }

  function getActiveLang(tenantDefault) {
    const stored = getStoredLang();
    if (stored && isValidLang(stored)) return stored;
    if (tenantDefault && isValidLang(tenantDefault)) return tenantDefault;
    return detectBrowserLang();
  }

  /* ── Traduções ───────────────────────────────────────────────────────────── */

  let _translations = {};

  async function loadTranslations(lang) {
    try {
      const res = await fetch(`/api/i18n/${encodeURIComponent(lang)}`);
      if (!res.ok) return;
      const data = await res.json();
      if (data && data.translations) {
        _translations = data.translations;
        window.__epiTranslations = _translations;
        window.__epiLang = data.locale || lang;
      }
    } catch {}
  }

  function t(key) {
    const parts = key.split('.');
    let node = _translations;
    for (const p of parts) {
      if (!node || typeof node !== 'object') return key;
      node = node[p];
    }
    return typeof node === 'string' ? node : key;
  }

  function applyTranslationsToLogin() {
    const map = {
      'login-username':            ['placeholder', t('login.usernameHint')],
      'login-password':            ['placeholder', t('login.passwordHint')],
      'login-password-toggle':     ['aria-label',  t('login.showPassword')],
      'recovery-username':         ['placeholder', t('login.usernameHint')],
      'recovery-email-username':   ['placeholder', t('login.usernameHint')],
    };
    for (const [id, [attr, val]] of Object.entries(map)) {
      const el = document.getElementById(id);
      if (el) el.setAttribute(attr, val);
    }

    const labelMap = {
      'login-username':        t('login.username'),
      'login-password':        t('login.password'),
      'recovery-username':     t('login.username'),
      'recovery-email-username': t('login.username'),
    };
    for (const [id, text] of Object.entries(labelMap)) {
      const input = document.getElementById(id);
      if (!input) continue;
      const label = document.querySelector(`label[for="${id}"]`);
      if (label && !label.querySelector('input')) label.textContent = text;
    }

    const loginBtn = document.querySelector('#login-form button[type="submit"]');
    if (loginBtn) loginBtn.textContent = t('login.button');

    const forgotBtn = document.getElementById('forgot-password-btn');
    if (forgotBtn) forgotBtn.textContent = t('login.forgotPassword');

    const recoverBtn = document.getElementById('recovery-submit');
    if (recoverBtn) recoverBtn.textContent = t('login.button');

    const h2 = document.querySelector('#login-form h2');
    if (h2) h2.textContent = t('login.title');

    const htmlEl = document.documentElement;
    htmlEl.lang = (window.__epiLang || 'pt-BR').toLowerCase().replace('_', '-');
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

    // Logo da tela de login
    const logoEl = document.getElementById('login-brand-logo');
    if (logoEl) {
      const logoSrc = branding.login_logo_type || branding.logo_type || '';
      if (logoSrc && logoSrc.startsWith('data:')) {
        logoEl.innerHTML = `<img src="${logoSrc}" alt="${escHtml(tenantName || 'Logo')}" class="tenant-login-logo" style="max-height:72px;max-width:240px;object-fit:contain;">`;
      } else {
        logoEl.innerHTML = '';
      }
    }

    // Título da página
    if (tenantName) {
      document.title = `${tenantName} — EPI Controle`;
    }

    // Mensagem institucional
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
    // Extrai slug do path (/empresa/...) como fallback
    const pathSlug = (window.location.pathname.split('/')[1] || '').toLowerCase();

    let url = `/api/tenant/resolve?host=${encodeURIComponent(host)}`;
    if (pathSlug && !pathSlug.startsWith('api')) {
      url += `&slug=${encodeURIComponent(pathSlug)}`;
    }

    try {
      const res = await fetch(url);
      if (!res.ok) return null;
      const data = await res.json();
      if (data && data.ok) {
        try { localStorage.setItem(LS_TENANT_KEY, JSON.stringify(data)); } catch {}
        window.__epiTenant = data;
        return data;
      }
    } catch {}

    // Tenta usar cache local
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

  /* ── Seletor de idioma ───────────────────────────────────────────────────── */

  function renderLanguageSelector(activeLang) {
    const existing = document.getElementById('epi-lang-selector');
    if (existing) existing.remove();

    const container = document.createElement('div');
    container.id = 'epi-lang-selector';
    container.setAttribute('role', 'group');
    container.setAttribute('aria-label', 'Selecionar idioma');
    container.style.cssText = [
      'display:flex', 'gap:6px', 'flex-wrap:wrap', 'justify-content:center',
      'margin-top:16px', 'padding-top:14px',
      'border-top:1px solid rgba(29,42,36,0.10)',
    ].join(';');

    for (const lang of SUPPORTED_LANGS) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.setAttribute('data-lang', lang.code);
      btn.setAttribute('aria-pressed', String(lang.code === activeLang));
      btn.setAttribute('aria-label', `${lang.name} - ${lang.region}`);
      btn.title = `${lang.name} — ${lang.region}`;

      const isActive = lang.code === activeLang;
      btn.style.cssText = [
        'display:flex', 'align-items:center', 'gap:4px',
        'padding:5px 9px', 'border-radius:20px', 'font-size:12px',
        'font-weight:' + (isActive ? '700' : '500'),
        'background:' + (isActive ? 'var(--accent)' : 'rgba(29,42,36,0.07)'),
        'color:' + (isActive ? '#fff' : 'var(--text)'),
        'border:' + (isActive ? '2px solid var(--accent)' : '2px solid transparent'),
        'cursor:pointer', 'transition:all .15s',
      ].join(';');

      btn.innerHTML = `<span aria-hidden="true">${lang.flag}</span><span>${lang.name}</span>`;

      btn.addEventListener('click', async () => {
        if (lang.code === window.__epiLang) return;
        storeLang(lang.code);
        await loadTranslations(lang.code);
        applyTranslationsToLogin();
        renderLanguageSelector(lang.code);
        window.dispatchEvent(new CustomEvent('epi:langchange', { detail: { lang: lang.code } }));
      });

      container.appendChild(btn);
    }

    // Inserir após o formulário de login
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
      loginForm.appendChild(container);
    }
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

    // Resolver tenant (não bloqueia a exibição do login)
    const tenantData = await resolveTenant();
    const tenantDefault = tenantData?.i18n?.default_language || '';

    // Determinar idioma ativo
    const activeLang = getActiveLang(tenantDefault);
    window.__epiLang = activeLang;

    // Carregar traduções
    await loadTranslations(activeLang);

    // Aplicar branding se tenant encontrado
    if (tenantData?.branding) {
      applyBranding(tenantData.branding, tenantData.tenant?.name);
    }

    // Aplicar traduções ao login
    applyTranslationsToLogin();

    // Renderizar seletor de idioma
    renderLanguageSelector(activeLang);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
