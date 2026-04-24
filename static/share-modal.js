'use strict';

(function () {
  if (window.__EPI_SHARE_MODAL_BOUND__) return;
  window.__EPI_SHARE_MODAL_BOUND__ = true;

  const doc = document;

  const safeOn = (el, ev, fn) => {
    if (!el || !el.addEventListener) return;
    el.addEventListener(ev, fn);
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
  } catch (e) {
    if (window.__EPI_DEBUG__) console.warn('[share-modal]', e);
  }
})();
