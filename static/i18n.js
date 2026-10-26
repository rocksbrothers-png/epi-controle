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
  // `LS_LANG_KEY` saiu na frente de Isolamento (PR C): nomeava uma chave de
  // `localStorage` com escopo DEVICE, e o idioma passou a pertencer à
  // identidade. A chave antiga é APOSENTADA pelo dono, no `app.js`, e nunca
  // mais lida. O nome dela não aparece aqui de propósito — este arquivo não
  // deve voltar a ter um caminho até ela, nem em texto.

  const _cache = {};          // locale -> dict
  let _active = {};           // dict do idioma ativo
  let _fallback = {};         // dict pt-BR para fallback de chaves
  let _lang = FALLBACK;
  let _languageSequence = 0;
  const _boundText = new WeakMap();

  /* ── Resolução de chaves aninhadas ───────────────────────────────────────── */

  function _resolve(dict, key) {
    const parts = String(key || '').split('.');
    let node = dict;
    for (const p of parts) {
      if (!node || typeof node !== 'object') {return undefined;}
      node = node[p];
    }
    return typeof node === 'string' ? node : undefined;
  }

  function _interpolate(str, vars) {
    if (!vars || typeof vars !== 'object') {return str;}
    return String(str).replace(/\{(\w+)\}/g, (m, k) => (Object.prototype.hasOwnProperty.call(vars, k) ? String(vars[k]) : m));
  }

  /**
   * Traduz uma chave. Ordem: idioma ativo → fallback pt-BR → a própria chave.
   * Suporta interpolação: t('greeting', { name: 'Ana' }) com "Olá, {name}".
   */
  function _message(dict, key, vars, locale) {
    const direct = _resolve(dict, key);
    if (direct !== undefined) {return direct;}
    if (vars && Number.isFinite(vars.count)) {
      const category = new Intl.PluralRules(locale).select(vars.count);
      return _resolve(dict, `${key}.${category}`) ?? _resolve(dict, `${key}.other`);
    }
    return undefined;
  }

  function t(key, vars) {
    let val = _message(_active, key, vars, _lang);
    if (val === undefined) {val = _message(_fallback, key, vars, FALLBACK);}
    if (val === undefined) {return key;}
    return _interpolate(val, vars);
  }

  /**
   * Tradução segura para conteúdo dinâmico gerado em JS.
   * Se a chave não existir ou o motor ainda não estiver pronto, retorna o
   * fallback em pt-BR informado pelo chamador.
   */
  function trEpi(key, fallback, vars) {
    try {
      const val = t(key, vars);
      return (val && val !== key) ? val : _interpolate(fallback !== undefined ? fallback : key, vars);
    } catch (_e) {
      return _interpolate(fallback !== undefined ? fallback : key, vars);
    }
  }

  function escapeMarkup(value) {
    return String(value ?? '').replace(/[&<>"']/g, (char) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    })[char]);
  }

  // Binding de mensagem dinâmica: valores são texto, nunca HTML executável.
  // Os parâmetros ficam no DOM para uma troca de idioma preservar o conteúdo.
  function resolveMessageVars(vars, variableKeys) {
    const resolved = { ...(vars || {}) };
    for (const [name, key] of Object.entries(variableKeys || {})) {
      if (typeof key === 'string') {
        const value = t(key);
        if (value !== key) { resolved[name] = value; }
      }
    }
    return resolved;
  }

  function bindText(key, vars, fallback, variableKeys) {
    const params = vars || {};
    const refs = variableKeys || {};
    return `<span data-i18n="${escapeMarkup(key)}" data-i18n-vars="${escapeMarkup(JSON.stringify(params))}" data-i18n-var-keys="${escapeMarkup(JSON.stringify(refs))}">${escapeMarkup(trEpi(key, fallback, resolveMessageVars(params, refs)))}</span>`;
  }

  function textFor(element, key, fallback, vars, variableKeys) {
    if (element?.setAttribute) {
      element.setAttribute('data-i18n', key);
      element.setAttribute('data-i18n-vars', JSON.stringify(vars || {}));
      element.setAttribute('data-i18n-var-keys', JSON.stringify(variableKeys || {}));
    }
    const value = trEpi(key, fallback, resolveMessageVars(vars, variableKeys));
    if (element?.setAttribute) { _boundText.set(element, value); }
    return value;
  }

  /* ── Carregamento de traduções ───────────────────────────────────────────── */

  async function _fetchLocale(locale) {
    if (_cache[locale]) {return _cache[locale];}
    try {
      const res = await fetch(`/api/i18n/${encodeURIComponent(locale)}`, {
        headers: { 'Accept': 'application/json' },
      });
      if (!res.ok) {return null;}
      const data = await res.json();
      if (data && !data.fallback && data.locale === locale && data.translations
          && typeof data.translations === 'object' && !Array.isArray(data.translations)
          && Object.keys(data.translations).length) {
        _cache[locale] = data.translations;
        return data.translations;
      }
    } catch { /* A indisponibilidade é devolvida ao carregador de idioma. */ }
    return null;
  }

  async function _ensureFallback() {
    if (Object.keys(_fallback).length) {return;}
    const fb = await _fetchLocale(FALLBACK);
    if (fb) {_fallback = fb;}
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
      if (el.textContent !== val) {el.textContent = val;}
      return;
    }
    // Procura o último nó de texto não-vazio e o substitui; senão, anexa.
    let textNode = null;
    for (let i = el.childNodes.length - 1; i >= 0; i--) {
      const n = el.childNodes[i];
      if (n.nodeType === Node.TEXT_NODE && n.textContent.trim()) { textNode = n; break; }
    }
    if (textNode) {
      if (textNode.textContent !== ' ' + val) {textNode.textContent = ' ' + val;}
    }
    else {el.appendChild(document.createTextNode(' ' + val));}
  }

  function translateDOM(root) {
    const scope = root || document;
    for (const [attr, kind] of DOM_ATTRS) {
      const nodes = Array.from(scope.querySelectorAll(`[${attr}]`));
      if (scope.nodeType === 1 && scope.hasAttribute(attr)) {nodes.unshift(scope);}
      nodes.forEach((el) => {
        const key = el.getAttribute(attr);
        if (!key) {return;}
        // Um campo reutilizado pode receber erro da API ou ficar vazio. Nesse
        // caso a mensagem anterior deixou de representar o estado atual.
        if (kind === 'text' && _boundText.has(el) && el.textContent !== _boundText.get(el)) {
          for (const binding of ['data-i18n', 'data-i18n-vars', 'data-i18n-var-keys']) {el.removeAttribute(binding);}
          _boundText.delete(el);
          return;
        }
        let vars;
        try { vars = JSON.parse(el.getAttribute('data-i18n-vars') || 'null'); } catch { vars = null; }
        let variableKeys;
        try { variableKeys = JSON.parse(el.getAttribute('data-i18n-var-keys') || 'null'); } catch { variableKeys = null; }
        vars = resolveMessageVars(vars, variableKeys);
        if (kind === 'html' && vars && typeof vars === 'object') {
          vars = Object.fromEntries(Object.entries(vars).map(([name, value]) => [name, escapeMarkup(value)]));
        }
        const val = t(key, vars);
        if (val === key) {return;} // sem tradução → preserva o texto original
        if (kind === 'text') {
          _setTextPreservingChildren(el, val);
          if (_boundText.has(el)) {_boundText.set(el, el.textContent);}
        }
        else if (kind === 'html') {el.innerHTML = val;}
        else {el.setAttribute(kind, val);}
      });
    }
    window.dispatchEvent(new CustomEvent('epi:domtranslated', { detail: { lang: _lang } }));
  }

  // Views e modais existentes inserem fragmentos depois do bootstrap. Somente
  // nós adicionados são observados; a própria troca de texto não recria HTML.
  if (typeof MutationObserver === 'function' && document.documentElement) {
    new MutationObserver((records) => {
      for (const record of records) {
        for (const node of record.addedNodes) {
          if (node.nodeType === 1) {translateDOM(node);}
        }
      }
    }).observe(document.documentElement, { childList: true, subtree: true });
  }

  /* ── API pública ─────────────────────────────────────────────────────────── */

  function isValid(code) { return SUPPORTED.includes(code); }

  // O idioma é uma das quatro preferências pessoais e tem o MESMO dono que as
  // outras três desde a frente de Isolamento (PR C). Este módulo carrega antes
  // do `app.js`, mas ambas as funções só são chamadas em tempo de execução
  // (via `tenant-init.js`, no `DOMContentLoaded`), quando o dono já existe.
  // Sem dono, o idioma cai no padrão — nunca no que estava no dispositivo.
  function getStoredLang() {
    try { return globalThis.__EPI_PREFS__?.ler()?.idioma || ''; } catch { return ''; }
  }

  function storeLang(code) {
    try { globalThis.__EPI_PREFS__?.definir({ idioma: code }); } catch { /* Preferência indisponível antes da sessão. */ }
  }

  function detectBrowserLang() {
    const nav = (navigator.language || navigator.userLanguage || FALLBACK).trim();
    if (isValid(nav)) {return nav;}
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
    // A resolução tardia do tenant não sobrepõe uma escolha já iniciada.
    if (options.initial && _languageSequence) {return _lang;}
    const target = isValid(code) ? code : FALLBACK;
    const sequence = ++_languageSequence;
    const owner = globalThis.__EPI_PREFS__?.identidade?.();

    await _ensureFallback();
    const dict = await _fetchLocale(target);
    if (sequence !== _languageSequence || owner !== globalThis.__EPI_PREFS__?.identidade?.()) { return _lang; }
    if (!dict) {
      if (!Object.keys(_active).length) { _active = _fallback; _lang = FALLBACK; }
      window.EpiI18n.loadError = { requested: target, effective: _lang };
    } else {
      _active = dict;
      _lang = target;
      window.EpiI18n.loadError = null;
    }

    if (options.persist && dict) {storeLang(_lang);}

    window.t = t;
    window.EpiI18n.lang = _lang;
    window.EpiI18n.translations = _active;
    document.documentElement.lang = _lang.toLowerCase();

    if (options.translate) {translateDOM(document);}

    if (!dict) {
      window.dispatchEvent(new CustomEvent('epi:localeerror', { detail: window.EpiI18n.loadError }));
    }
    window.dispatchEvent(new CustomEvent('epi:langchange', { detail: { lang: _lang } }));
    return _lang;
  }

  function resolveInitialLang(tenantDefault) {
    const stored = getStoredLang();
    if (stored && isValid(stored)) {return stored;}
    if (tenantDefault && isValid(tenantDefault)) {return tenantDefault;}
    return detectBrowserLang();
  }

  /* ── Exposição global ────────────────────────────────────────────────────── */

  window.t = t;
  window.trEpi = trEpi;
  window.EpiI18n = {
    SUPPORTED,
    FALLBACK,
    lang: _lang,
    translations: _active,
    t,
    trEpi,
    bindText,
    escapeMarkup,
    textFor,
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
