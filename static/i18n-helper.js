(function initEpiI18nHelper(global) {
  'use strict';

  function fallbackTranslate(key, fallback) {
    try {
      const value = (typeof global.window !== 'undefined' && typeof global.window.t === 'function')
        ? global.window.t(key)
        : null;
      return (value && value !== key) ? value : (fallback !== undefined ? fallback : key);
    } catch (_error) {
      return fallback !== undefined ? fallback : key;
    }
  }

  function resolveLegacyTranslator() {
    const existingTranslator = global.trEpi;
    const translator = (typeof existingTranslator === 'function') ? existingTranslator : fallbackTranslate;
    if (typeof existingTranslator !== 'function') global.trEpi = translator;
    return translator;
  }

  global.EpiI18nHelper = Object.freeze({
    fallbackTranslate,
    resolveLegacyTranslator,
  });
}(globalThis));
