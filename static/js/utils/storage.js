'use strict';

(function () {
  if (globalThis.__EPI_UTILS_STORAGE_LOADED__) return;
  globalThis.__EPI_UTILS_STORAGE_LOADED__ = true;

  function safeStorageRead(key, fallback) {
    if (fallback === undefined) fallback = null;
    try {
      const win = typeof window !== 'undefined' ? window : null;
      if (!win || !win.localStorage) return fallback;
      const val = win.localStorage.getItem(key);
      return val !== null ? val : fallback;
    } catch (_error) {
      return fallback;
    }
  }

  function safeStorageWrite(key, value) {
    try {
      const win = typeof window !== 'undefined' ? window : null;
      if (!win || !win.localStorage) return false;
      if (value === null || value === undefined) {
        win.localStorage.removeItem(key);
      } else {
        win.localStorage.setItem(key, String(value));
      }
      return true;
    } catch (_error) {
      return false;
    }
  }

  function safeStorageRemove(key) {
    try {
      const win = typeof window !== 'undefined' ? window : null;
      if (!win || !win.localStorage) return false;
      win.localStorage.removeItem(key);
      return true;
    } catch (_error) {
      return false;
    }
  }

  function safeJsonParse(raw, fallback) {
    if (fallback === undefined) fallback = null;
    try {
      return JSON.parse(raw);
    } catch (_error) {
      return fallback;
    }
  }

  function safeJsonStringify(value, fallback) {
    if (fallback === undefined) fallback = '';
    try {
      return JSON.stringify(value);
    } catch (_error) {
      return fallback;
    }
  }

  globalThis.safeStorageRead = safeStorageRead;
  globalThis.safeStorageWrite = safeStorageWrite;
  globalThis.safeStorageRemove = safeStorageRemove;
  globalThis.safeJsonParse = safeJsonParse;
  globalThis.safeJsonStringify = safeJsonStringify;

  const helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
  helpers.safeStorageRead = safeStorageRead;
  helpers.safeStorageWrite = safeStorageWrite;
  helpers.safeStorageRemove = safeStorageRemove;
  helpers.safeJsonParse = safeJsonParse;
  globalThis.__EPI_FRONTEND_HELPERS__ = helpers;
})();
