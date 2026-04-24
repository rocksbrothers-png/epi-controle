'use strict';

(function () {
  try {
    const doc = typeof document === 'undefined' ? null : document;
    if (!doc) return;

    const safeOn = (target, eventName, handler, options) => {
      if (!target || typeof target.addEventListener !== 'function') return;
      target.addEventListener(eventName, handler, options);
    };

    const log = (...args) => {
      if (globalThis.__EPI_DEBUG__) console.warn('[share-modal]', ...args);
    };

    const bindModal = () => {
      if (globalThis.__EPI_SHARE_MODAL_BOUND__) return;

      const modal = doc.getElementById('share-modal')
        || doc.querySelector('[data-share-modal]')
        || doc.querySelector('.share-modal');
      if (!modal) {
        log('Modal ausente na página; inicialização ignorada com segurança.');
        return;
      }
      if (modal.dataset.shareModalBound === '1') {
        globalThis.__EPI_SHARE_MODAL_BOUND__ = true;
        return;
      }

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
    };

    if (doc.readyState === 'loading') {
      safeOn(doc, 'DOMContentLoaded', bindModal, { once: true });
      return;
    }

    bindModal();
  } catch (err) {
    if (window.__EPI_DEBUG__) console.warn('[share-modal]', err);
  }
})();
