/**
 * i18n.js — Motor de internacionalização global do EPI Controle
 *
 * Carregado antes de qualquer outro script. Expõe:
 *   - window.t(key, vars)        → traduz uma chave (ex: t('dashboard.title'))
 *   - window.EpiI18n.setLang()   → troca o idioma ativo e re-traduz o DOM
 *   - window.EpiI18n.translateDOM(root) → aplica traduções aos elementos data-i18n
 *   - window.EpiI18n.lang        → idioma ativo
 *   - window.EpiI18n.ready       → Promise resolvida após carregar traduções
 *
 * Tradução de DOM via atributos:
 *   data-i18n="chave"             → textContent
 *   data-i18n-html="chave"        → innerHTML
 *   data-i18n-placeholder="chave" → atributo placeholder
 *   data-i18n-title="chave"       → atributo title
 *   data-i18n-aria-label="chave"  → atributo aria-label
 *   data-i18n-value="chave"       → atributo value
 */

(function () {
  'use strict';

  const SUPPORTED = ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO'];
  const FALLBACK = 'pt-BR';
  const LS_LANG_KEY = 'epi_language';

  const _cache = {};          // locale -> dict
  let _active = {};           // dict do idioma ativo
  let _fallback = {};         // dict pt-BR para fallback de chaves
  let _lang = FALLBACK;

  /* ── Resolução de chaves aninhadas ───────────────────────────────────────── */

  function _resolve(dict, key) {
    const parts = String(key || '').split('.');
    let node = dict;
    for (const p of parts) {
      if (!node || typeof node !== 'object') return undefined;
      node = node[p];
    }
    return typeof node === 'string' ? node : undefined;
  }

  function _interpolate(str, vars) {
    if (!vars || typeof vars !== 'object') return str;
    return str.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m));
  }

  /**
   * Traduz uma chave. Ordem: idioma ativo → fallback pt-BR → a própria chave.
   * Suporta interpolação: t('greeting', { name: 'Ana' }) com "Olá, {name}".
   */
  function t(key, vars) {
    let val = _resolve(_active, key);
    if (val === undefined) val = _resolve(_fallback, key);
    if (val === undefined) return key;
    return _interpolate(val, vars);
  }

  /* ── Carregamento de traduções ───────────────────────────────────────────── */

  async function _fetchLocale(locale) {
    if (_cache[locale]) return _cache[locale];
    try {
      const res = await fetch(`/api/i18n/${encodeURIComponent(locale)}`, {
        headers: { 'Accept': 'application/json' },
      });
      if (!res.ok) return null;
      const data = await res.json();
      if (data && data.translations) {
        _cache[locale] = data.translations;
        return data.translations;
      }
    } catch {}
    return null;
  }

  async function _ensureFallback() {
    if (Object.keys(_fallback).length) return;
    const fb = await _fetchLocale(FALLBACK);
    if (fb) _fallback = fb;
  }

  /* ── Tradução de DOM ─────────────────────────────────────────────────────── */

  const DOM_ATTRS = [
    ['data-i18n',             'text'],
    ['data-i18n-html',        'html'],
    ['data-i18n-placeholder', 'placeholder'],
    ['data-i18n-title',       'title'],
    ['data-i18n-aria-label',  'aria-label'],
    ['data-i18n-value',       'value'],
  ];

  // Substitui apenas o texto de um elemento, preservando elementos filhos
  // (ex.: um <button> com <svg> ícone + rótulo de texto).
  function _setTextPreservingChildren(el, val) {
    const hasElementChild = el.firstElementChild !== null;
    if (!hasElementChild) {
      el.textContent = val;
      return;
    }
    // Procura o último nó de texto não-vazio e o substitui; senão, anexa.
    let textNode = null;
    for (let i = el.childNodes.length - 1; i >= 0; i--) {
      const n = el.childNodes[i];
      if (n.nodeType === Node.TEXT_NODE && n.textContent.trim()) { textNode = n; break; }
    }
    if (textNode) textNode.textContent = ' ' + val;
    else el.appendChild(document.createTextNode(' ' + val));
  }

  function translateDOM(root) {
    const scope = root || document;
    for (const [attr, kind] of DOM_ATTRS) {
      const nodes = scope.querySelectorAll(`[${attr}]`);
      nodes.forEach((el) => {
        const key = el.getAttribute(attr);
        if (!key) return;
        const val = t(key);
        if (val === key) return; // sem tradução → preserva o texto original
        if (kind === 'text') _setTextPreservingChildren(el, val);
        else if (kind === 'html') el.innerHTML = val;
        else el.setAttribute(kind, val);
      });
    }
    window.dispatchEvent(new CustomEvent('epi:domtranslated', { detail: { lang: _lang } }));
  }

  /* ── API pública ─────────────────────────────────────────────────────────── */

  function isValid(code) { return SUPPORTED.includes(code); }

  function getStoredLang() {
    try { return localStorage.getItem(LS_LANG_KEY) || ''; } catch { return ''; }
  }

  function storeLang(code) {
    try { localStorage.setItem(LS_LANG_KEY, code); } catch {}
  }

  function detectBrowserLang() {
    const nav = (navigator.language || navigator.userLanguage || FALLBACK).trim();
    if (isValid(nav)) return nav;
    const short = nav.split('-')[0].toLowerCase();
    const map = { pt: 'pt-BR', en: 'en-GB', es: 'es-ES', fr: 'fr-FR', nb: 'nb-NO', no: 'nb-NO' };
    return map[short] || FALLBACK;
  }

  /**
   * Define o idioma ativo, carrega traduções, persiste e re-traduz o DOM.
   * @param {string} code
   * @param {object} opts { persist:true, translate:true }
   */
  async function setLang(code, opts) {
    const options = Object.assign({ persist: true, translate: true }, opts || {});
    const target = isValid(code) ? code : FALLBACK;

    await _ensureFallback();
    const dict = await _fetchLocale(target);
    _active = dict || _fallback;
    _lang = target;

    if (options.persist) storeLang(target);

    window.t = t;
    window.EpiI18n.lang = _lang;
    window.EpiI18n.translations = _active;
    document.documentElement.lang = _lang.toLowerCase();

    if (options.translate) translateDOM(document);

    window.dispatchEvent(new CustomEvent('epi:langchange', { detail: { lang: _lang } }));
    return _lang;
  }

  function resolveInitialLang(tenantDefault) {
    const stored = getStoredLang();
    if (stored && isValid(stored)) return stored;
    if (tenantDefault && isValid(tenantDefault)) return tenantDefault;
    return detectBrowserLang();
  }

  /* ── Exposição global ────────────────────────────────────────────────────── */

  window.t = t;
  window.EpiI18n = {
    SUPPORTED,
    FALLBACK,
    lang: _lang,
    translations: _active,
    t,
    setLang,
    translateDOM,
    resolveInitialLang,
    detectBrowserLang,
    getStoredLang,
    storeLang,
    isValid,
    ready: Promise.resolve(),
  };

})();
