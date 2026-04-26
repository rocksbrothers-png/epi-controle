'use strict';

(function () {
  try {
    if (typeof window === 'undefined' || typeof document === 'undefined') return;
    if (window.__EPI_SHARE_MODAL_INIT_BOUND__) return;
    window.__EPI_SHARE_MODAL_INIT_BOUND__ = true;
    window.__EPI_SHARE_MODAL_VERSION__ = '20260426-07';

    function localSafeOn(element, eventName, handler, options) {
      if (!element || typeof element.addEventListener !== 'function') return false;
      try {
        element.addEventListener(eventName, handler, options);
        return true;
      } catch (_error) {
        return false;
      }
    }
    function safeBind(element, eventName, handler, options) {
    var safeOn = function (element, eventName, handler, options) {
      if (!element || typeof element.addEventListener !== 'function') return false;
      if (typeof handler !== 'function') return false;
      return localSafeOn(element, eventName, handler, options);
    }
    var safeOn = safeBind;

    function bindShareModal() {
      var root = document.querySelector('[data-share-modal], #share-modal, .share-modal');
      if (!root) {
        console.warn('[share-modal] modal não existe no DOM');
        return false;
      }

      var openButtons = Array.from(document.querySelectorAll('[data-share-open]')).filter(function (button) {
        return button && typeof button.addEventListener === 'function';
      });
      var closeButtons = Array.from(document.querySelectorAll('[data-share-close]')).filter(function (button) {
        return button && typeof button.addEventListener === 'function';
      });
      if (!openButtons.length && !closeButtons.length) return false;
      if (root.dataset.epiShareModalBound === '1') return;
      root.dataset.epiShareModalBound = '1';

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
      var hasBoundModal = bindShareModal();
      if (!hasBoundModal) return;
      var htmxTarget = document.body || document.documentElement || document;
      safeOn(htmxTarget, 'htmx:afterSwap', bindShareModal);
    };

    if (document.readyState === 'loading') {
      safeOn(document, 'DOMContentLoaded', bindWhenReady, { once: true });
    } else {
      bindWhenReady();
    }
  } catch (error) {
    if (typeof window !== 'undefined' && window.__EPI_DEBUG__) {
      console.warn('[share-modal] fluxo clássico mantido', error);
    }
  }
})();
