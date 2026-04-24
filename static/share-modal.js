'use strict';

(function () {
  try {
    if (typeof document === 'undefined') return;

    if (typeof window !== 'undefined' && window.__EPI_SHARE_MODAL_BOUND__) return;
    if (typeof window !== 'undefined') window.__EPI_SHARE_MODAL_BOUND__ = true;

    const root = document.querySelector('[data-share-modal], #share-modal, .share-modal');
    if (!root) return;

    function safeOn(element, eventName, handler, options) {
      if (!element || !element.addEventListener) return;
      element.addEventListener(eventName, handler, options);
    }

    const openButtons = Array.from(document.querySelectorAll('[data-share-open]'));
    const closeButtons = Array.from(document.querySelectorAll('[data-share-close]'));

    const openModal = function () {
      root.classList.add('is-open');
      root.setAttribute('aria-hidden', 'false');
    };

    const closeModal = function () {
      root.classList.remove('is-open');
      root.setAttribute('aria-hidden', 'true');
    };

    openButtons.forEach(function (button) {
      safeOn(button, 'click', openModal);
    });

    closeButtons.forEach(function (button) {
      safeOn(button, 'click', closeModal);
    });

    safeOn(root, 'click', function (event) {
      if (event && event.target === root) closeModal();
    });
  } catch (error) {
    if (typeof window !== 'undefined' && window.__EPI_DEBUG__) console.warn('[share-modal]', error);
  }
})();
