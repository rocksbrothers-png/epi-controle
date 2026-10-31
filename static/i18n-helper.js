(function initEpiI18nHelper(global) {
  'use strict';

  function fallbackTranslate(key, fallback, vars) {
    try {
      const value = (typeof global.window !== 'undefined' && typeof global.window.t === 'function')
        ? global.window.t(key, vars)
        : null;
      return (value && value !== key) ? value : String(fallback !== undefined ? fallback : key).replace(/\{(\w+)\}/g, (match, name) => vars && Object.prototype.hasOwnProperty.call(vars, name) ? String(vars[name]) : match);
    } catch (_error) {
      return String(fallback !== undefined ? fallback : key).replace(/\{(\w+)\}/g, (match, name) => vars && Object.prototype.hasOwnProperty.call(vars, name) ? String(vars[name]) : match);
    }
  }

  function resolveLegacyTranslator() {
    const existingTranslator = global.trEpi;
    const translator = (typeof existingTranslator === 'function') ? existingTranslator : fallbackTranslate;
    if (typeof existingTranslator !== 'function') {global.trEpi = translator;}
    return translator;
  }

  global.EpiI18nHelper = Object.freeze({
    fallbackTranslate,
    resolveLegacyTranslator,
  });
}(globalThis));
