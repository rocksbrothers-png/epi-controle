'use strict';

(function () {
  try {
    if (typeof window === 'undefined' || typeof document === 'undefined') return;
    if (window.__EPI_SHARE_MODAL_INIT_BOUND__) return;
    window.__EPI_SHARE_MODAL_INIT_BOUND__ = true;
    window.__EPI_SHARE_MODAL_VERSION__ = '20260426-01';

    var helpers = window.__EPI_FRONTEND_HELPERS__ || {};
    var sharedSafeOn = typeof helpers.safeOn === 'function' ? helpers.safeOn : null;
    var safeOn = function (element, eventName, handler, options) {
      if (!element || typeof element.addEventListener !== 'function' || typeof handler !== 'function') return false;
      try {
        if (sharedSafeOn) return Boolean(sharedSafeOn(element, eventName, handler, options));
        element.addEventListener(eventName, handler, options);
        return true;
      } catch (_error) {
        return false;
      }
    };

    function bindShareModal() {
      var root = document.querySelector('[data-share-modal], #share-modal, .share-modal');
      if (!root) return false;
      if (root.dataset.epiShareModalBound === '1') return;
      root.dataset.epiShareModalBound = '1';

      var openButtons = Array.from(document.querySelectorAll('[data-share-open]'));
      var closeButtons = Array.from(document.querySelectorAll('[data-share-close]'));

      var openModal = function () {
        root.classList.add('is-open');
        root.setAttribute('aria-hidden', 'false');
      };

      var closeModal = function () {
        root.classList.remove('is-open');
        root.setAttribute('aria-hidden', 'true');
      };

      openButtons.forEach(function (button) { safeOn(button, 'click', openModal); });
      closeButtons.forEach(function (button) { safeOn(button, 'click', closeModal); });

      safeOn(root, 'click', function (event) {
        if (event && event.target === root) closeModal();
      });
      return true;
    }

    var bindWhenReady = function () {
      bindShareModal();
      var htmxTarget = document.body || document.documentElement || document;
      safeOn(htmxTarget, 'htmx:afterSwap', bindShareModal);
      globalThis.setTimeout(function () {
        if (!document || !document.querySelector) return;
        bindShareModal();
      }, 0);
    };

    if (document.readyState === 'loading') {
      safeOn(document, 'DOMContentLoaded', bindWhenReady, { once: true });
      return;
    }
    bindWhenReady();
  } catch (error) {
    if (typeof window !== 'undefined' && window.__EPI_DEBUG__) {
      console.warn('[share-modal] fluxo clássico mantido', error);
    }
  }
})();
