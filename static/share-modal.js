'use strict';

(function () {
  const globalScope = typeof globalThis !== 'undefined' ? globalThis : window;
  const doc = typeof document === 'undefined' ? null : document;
  if (!doc) return;
  if (globalScope.__EPI_SHARE_MODAL_BOUND__) return;
  globalScope.__EPI_SHARE_MODAL_BOUND__ = true;

  const helpers = globalScope.__EPI_FRONTEND_HELPERS__ || {};
  const safeOn = typeof helpers.safeOn === 'function'
    ? helpers.safeOn
    : (target, eventName, handler, options) => {
      if (!target || typeof target.addEventListener !== 'function') return;
      target.addEventListener(eventName, handler, options);
    };

  const root =
    doc.getElementById('share-modal') ||
    doc.querySelector('[data-share-modal]') ||
    doc.querySelector('.share-modal');

  if (!root) return;

  try {
    const openButtons = Array.from(doc.querySelectorAll('[data-share-open]'));
    const closeButtons = Array.from(doc.querySelectorAll('[data-share-close]'));

    const openModal = () => {
      root.classList.add('is-open');
      root.setAttribute('aria-hidden', 'false');
    };

    const closeModal = () => {
      root.classList.remove('is-open');
      root.setAttribute('aria-hidden', 'true');
    };

    openButtons.forEach((button) => safeOn(button, 'click', openModal));
    closeButtons.forEach((button) => safeOn(button, 'click', closeModal));

    safeOn(root, 'click', (event) => {
      if (event.target === root) closeModal();
    });
  } catch (error) {
    if (globalScope.__EPI_DEBUG__) console.warn('[share-modal]', error);
  }
})();
