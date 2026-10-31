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
  const _boundAttributes = new WeakMap();
  const _pluralCount = Symbol('numeric plural count');

  /* ── Resolução de chaves aninhadas ───────────────────────────────────────── */

  function _resolve(dict, key) {
    const parts = String(key || '').split('.');
    let node = dict;
    for (const p of parts) {
      if (!node || typeof node !== 'object') {return undefined;}
      if (!Object.prototype.hasOwnProperty.call(node, p)) {return undefined;}
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
    const count = vars?.[_pluralCount] ?? vars?.count;
    if (Number.isFinite(count)) {
      const category = new Intl.PluralRules(locale).select(count);
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

  // Só a ênfase sem atributos do catálogo vira elemento. Dados interpolados
  // chegam escapados e são decodificados uma vez, já como nós de texto.
  function setRichText(element, value) {
    const fragment = document.createDocumentFragment();
    const parents = [fragment];
    const entities = { '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"', '&#39;': "'" };
    const elements = {
      strong: () => document.createElement('strong'),
      em: () => document.createElement('em'),
      b: () => document.createElement('b'),
      i: () => document.createElement('i'),
      br: () => document.createElement('br'),
    };
    for (const part of String(value).split(/(<\/?(?:strong|em|b|i)>|<br\s*\/?>)/gi)) {
      if (!part) {continue;}
      const tag = /^<(\/?)(strong|em|b|i|br)\s*\/?>$/i.exec(part);
      if (tag && !tag[1]) {
        const node = elements[tag[2].toLowerCase()]();
        parents[parents.length - 1].appendChild(node);
        if (tag[2].toLowerCase() !== 'br') {parents.push(node);}
      } else if (tag && parents.length > 1 && parents[parents.length - 1].nodeName.toLowerCase() === tag[2].toLowerCase()) {
        parents.pop();
      } else {
        parents[parents.length - 1].appendChild(document.createTextNode(
          part.replace(/&(?:amp|lt|gt|quot);|&#39;/g, entity => entities[entity])));
      }
    }
    element.replaceChildren(fragment);
  }

  // Binding de mensagem dinâmica: valores são texto, nunca HTML executável.
  // Os parâmetros ficam no DOM para uma troca de idioma preservar o conteúdo.
  function formatNumber(value, options) {
    const number = Number(value);
    if (!Number.isFinite(number)) {return String(value ?? '');}
    try {return new Intl.NumberFormat(_lang, options || {}).format(number);}
    catch {return String(value ?? '');}
  }

  function formatDate(value, options) {
    if (!value) {return '';}
    const dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(String(value));
    const date = new Date(dateOnly ? `${value}T00:00:00Z` : value);
    if (!Number.isFinite(date.getTime()) || dateOnly && date.toISOString().slice(0, 10) !== value) {return String(value);}
    try {
      return new Intl.DateTimeFormat(_lang, {dateStyle:'short', ...(dateOnly ? {timeZone:'UTC'} : {}), ...(options || {})}).format(date);
    } catch {return String(value);}
  }

  function resolveMessageVars(vars, variableKeys, depth = 0) {
    const resolved = { ...(vars || {}) };
    // Display formatting may turn count into "1,234" or "1 234". PluralRules
    // must keep the original numeric operand, including in nested messages.
    const count = vars?.[_pluralCount] ?? vars?.count;
    if (Number.isFinite(count)) {Object.defineProperty(resolved, _pluralCount, {value:count});}
    if (depth > 4) {return resolved;}
    for (const [name, key] of Object.entries(variableKeys || {})) {
      if (typeof key === 'string') {
        const value = t(key);
        if (value !== key) { resolved[name] = value; }
      } else if (key && typeof key === 'object') {
        if (key.type === 'date') {resolved[name] = formatDate(key.value, key.options);}
        else if (key.type === 'number') {resolved[name] = formatNumber(key.value, key.options);}
        else if (key.type === 'message' && typeof key.key === 'string') {
          const value = t(key.key, resolveMessageVars(key.vars, key.refs, depth + 1));
          if (value !== key.key) {resolved[name] = value;}
        }
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

  function clearBinding(element, kind = 'text') {
    if (!element?.removeAttribute) {return;}
    const binding = kind === 'text' ? 'data-i18n' : 'data-i18n-' + kind;
    element.removeAttribute(binding);
    if (kind === 'text') {_boundText.delete(element);}
    else {
      element.removeAttribute(binding + '-vars');
      element.removeAttribute(binding + '-var-keys');
      _boundAttributes.get(element)?.delete(kind);
    }
  }

  function attributeFor(element, attribute, key, fallback, vars, variableKeys) {
    const value = trEpi(key, fallback, resolveMessageVars(vars, variableKeys));
    if (element?.setAttribute) {
      const binding = 'data-i18n-' + attribute;
      element.setAttribute(binding, key);
      element.setAttribute(binding + '-vars', JSON.stringify(vars || {}));
      element.setAttribute(binding + '-var-keys', JSON.stringify(variableKeys || {}));
      const attributes = _boundAttributes.get(element) || new Map();
      attributes.set(attribute, value);
      _boundAttributes.set(element, attributes);
    }
    return value;
  }

  let _apiMessageIndex;

  function _apiTemplates() {
    if (_apiMessageIndex?.source === _fallback) {return _apiMessageIndex.entries;}
    const entries = [];
    function visit(node, prefix, existingErrors = false) {
      for (const [part, value] of Object.entries(node || {})) {
        const key = prefix ? `${prefix}.${part}` : part;
        if (existingErrors && key.startsWith('apiErrors.')) {continue;}
        if (typeof value === 'string') {
          if (existingErrors && !/error|invalid|failed|denied|notfound|required|mismatch|unavailable|forbidden/i.test(key)) {continue;}
          const tokens = [...value.matchAll(/\{(\w+)\}/g)];
          entries.push({key, value, tokens, specificity:value.replace(/\{\w+\}/g, '').length});
        } else if (value && typeof value === 'object') {visit(value, key, existingErrors);}
      }
    }
    visit(_fallback.apiErrors?.messages, 'apiErrors.messages');
    visit(_fallback, '', true);
    entries.sort((a, b) => b.specificity - a.specificity);
    _apiMessageIndex = {source:_fallback, entries};
    return entries;
  }

  // Correspondência ancorada e linear. Somente mensagens de sistema do
  // namespace apiErrors participam; nomes, registros e justificativas livres
  // não são procurados no catálogo nem reescritos.
  function _matchApiTemplate(template, original) {
    if (!template.tokens.length) {return template.value === original ? {} : null;}
    if (template.specificity < 8 || original.length > 8192) {return null;}
    const vars = Object.create(null);
    let sourcePosition = 0, position = 0;
    for (let i = 0; i < template.tokens.length; i++) {
      const token = template.tokens[i];
      const before = template.value.slice(sourcePosition, token.index);
      if (!original.startsWith(before, position)) {return null;}
      position += before.length;
      sourcePosition = token.index + token[0].length;
      const next = template.tokens[i + 1];
      const after = template.value.slice(sourcePosition, next ? next.index : undefined);
      if (!after && next) {return null;}
      const end = after ? original.indexOf(after, position) : original.length;
      if (end < 0) {return null;}
      const value = original.slice(position, end);
      if (Object.prototype.hasOwnProperty.call(vars, token[1]) && vars[token[1]] !== value) {return null;}
      vars[token[1]] = value;
      position = end;
    }
    const suffix = template.value.slice(sourcePosition);
    return original.slice(position) === suffix ? vars : null;
  }

  function describeApiError(payload, fallback) {
    const error = payload?.error;
    const original = String((typeof payload === 'string' ? payload : null) || (typeof error === 'string' ? error : error?.message) || payload?.message || fallback || '');
    function result(key, vars) {
      const source = _resolve(_fallback, key);
      if (typeof source !== 'string' || [...source.matchAll(/\{(\w+)\}/g)].some(match => !Object.prototype.hasOwnProperty.call(vars, match[1]))) {return null;}
      const refs = {};
      for (const name of ['key', 'field']) {
        if (typeof vars[name] === 'string') {
          const fieldKey = 'apiErrors.fields.' + vars[name];
          if (_resolve(_fallback, fieldKey) !== undefined) {refs[name] = fieldKey;}
        }
      }
      return {key, vars, refs, text:trEpi(key, original, resolveMessageVars(vars, refs))};
    }
    const metadata = payload?.i18n || error?.i18n || payload?.validation?.i18n;
    if (typeof metadata?.key === 'string' && metadata.key.startsWith('apiErrors.')) {
      const translated = result(metadata.key, metadata.params || metadata.vars || {});
      if (translated) {return translated;}
    }
    // Um código só substitui a mensagem quando seu template corresponde aos
    // detalhes recebidos. Códigos genéricos não apagam uma validação específica.
    const code = payload?.code || error?.code || payload?.validation?.code;
    if (typeof code === 'string') {
      const key = 'apiErrors.codes.' + code, source = _resolve(_fallback, key);
      if (source) {
        const template = {value:source,tokens:[...source.matchAll(/\{(\w+)\}/g)],specificity:source.replace(/\{\w+\}/g,'').length};
        const vars = _matchApiTemplate(template, original);
        if (vars) {return result(key, vars);}
      }
    }
    for (const template of _apiTemplates()) {
      const vars = _matchApiTemplate(template, original);
      if (vars) {return result(template.key, vars);}
    }
    return {key:null, vars:{}, refs:{}, text:original};
  }

  function apiMessage(payload, fallback) {return describeApiError(payload, fallback).text;}

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
    ['data-i18n-alt',         'alt'],
  ];

  // Substitui apenas o texto de um elemento, preservando elementos filhos
  // (ex.: um <button> com <svg> ícone + rótulo de texto).
  function _ownLabel(el) {
    if (el.firstElementChild === null) {return el.textContent;}
    for (let i = el.childNodes.length - 1; i >= 0; i--) {
      const node = el.childNodes[i];
      if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) {return node.textContent;}
    }
    return '';
  }

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
        if (kind === 'text' && _boundText.has(el) && _ownLabel(el) !== _boundText.get(el)) {
          for (const binding of ['data-i18n', 'data-i18n-vars', 'data-i18n-var-keys']) {el.removeAttribute(binding);}
          _boundText.delete(el);
          return;
        }
        if (kind !== 'text' && kind !== 'html') {
          const attributes = _boundAttributes.get(el);
          if (attributes?.has(kind) && el.getAttribute(kind) !== attributes.get(kind)) {
            for (const binding of [attr, attr + '-vars', attr + '-var-keys']) {el.removeAttribute(binding);}
            attributes.delete(kind);
            return;
          }
        }
        let vars;
        try { vars = JSON.parse(el.getAttribute(attr + '-vars') || el.getAttribute('data-i18n-vars') || 'null'); } catch { vars = null; }
        let variableKeys;
        try { variableKeys = JSON.parse(el.getAttribute(attr + '-var-keys') || el.getAttribute('data-i18n-var-keys') || 'null'); } catch { variableKeys = null; }
        vars = resolveMessageVars(vars, variableKeys);
        if (kind === 'html') {
          vars = Object.fromEntries(Object.entries(vars).map(([name, value]) => [name, escapeMarkup(value)]));
        }
        const val = t(key, vars);
        if (val === key) {return;} // sem tradução → preserva o texto original
        if (kind === 'text') {
          _setTextPreservingChildren(el, val);
          _boundText.set(el, _ownLabel(el));
        }
        else if (kind === 'html') {setRichText(el, val);}
        else {
          el.setAttribute(kind, val);
          const attributes = _boundAttributes.get(el) || new Map();
          attributes.set(kind, val);
          _boundAttributes.set(el, attributes);
        }
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
    attributeFor,
    clearBinding,
    formatDate,
    formatNumber,
    describeApiError,
    apiMessage,
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
