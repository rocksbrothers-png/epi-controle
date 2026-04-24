'use strict';

(function initShareModalSafely() {
  try {
    const doc = typeof document === 'undefined' ? null : document;
    if (!doc) return;
    if (globalThis.__EPI_SHARE_MODAL_BOUND__) return;

    const safeOn = (target, eventName, handler, options) => {
      if (!target || typeof target.addEventListener !== 'function') return;
      target.addEventListener(eventName, handler, options);
    };

    const modalRoot = doc.querySelector('[data-share-modal], #share-modal, .share-modal');
    if (!modalRoot) return;

    const modal = modalRoot.id === 'share-modal'
      ? modalRoot
      : doc.getElementById('share-modal');
    if (!modal) return;
    if (modal.dataset.shareModalBound === '1') return;

    const openButtons = Array.from(doc.querySelectorAll('[data-share-open]'));
    const closeButtons = Array.from(doc.querySelectorAll('[data-share-close]'));
    const openModal = () => {
      modal.classList.add('is-open');
      modal.setAttribute('aria-hidden', 'false');
    };
    const closeModal = () => {
      modal.classList.remove('is-open');
      modal.setAttribute('aria-hidden', 'true');
    };

    modal.dataset.shareModalBound = '1';
    openButtons.forEach((button) => safeOn(button, 'click', openModal));
    closeButtons.forEach((button) => safeOn(button, 'click', closeModal));
    safeOn(modal, 'click', (event) => {
      if (event.target === modal) closeModal();
    });

    globalThis.__EPI_SHARE_MODAL_BOUND__ = true;
  } catch (error) {
    if (globalThis.__EPI_DEBUG__) {
      console.warn('[share-modal]', error);
    }
  }
})();
