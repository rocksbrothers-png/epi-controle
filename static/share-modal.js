'use strict';

(function initShareModal() {
  try {
    if (typeof document === 'undefined') return;
    if (globalThis.__EPI_SHARE_MODAL_BOUND__) return;

    const log = (message, extra) => {
      if (extra !== undefined) {
        console.debug('[share-modal]', message, extra);
        return;
      }
      console.debug('[share-modal]', message);
    };
    const safeOn = (target, eventName, handler, options) => {
      if (!target || typeof target.addEventListener !== 'function') return false;
      target.addEventListener(eventName, handler, options);
      return true;
    };

    const bindModal = () => {
      const modal = document.getElementById('share-modal');
      if (!modal) {
        log('Modal ausente na página; inicialização ignorada com segurança.');
        return;
      }
      if (modal.dataset.shareModalBound === '1') {
        log('Modal já inicializado anteriormente; binding idempotente preservado.');
        return;
      }
      modal.dataset.shareModalBound = '1';

      const openButtons = Array.from(document.querySelectorAll('[data-share-open]'));
      const closeButtons = Array.from(document.querySelectorAll('[data-share-close]'));

      const openModal = () => {
        modal.classList.add('is-open');
        modal.setAttribute('aria-hidden', 'false');
      };

      const closeModal = () => {
        modal.classList.remove('is-open');
        modal.setAttribute('aria-hidden', 'true');
      };

      openButtons.forEach((button) => {
        if (!button || typeof button.addEventListener !== 'function' || button.dataset.shareOpenBound === '1') return;
        button.dataset.shareOpenBound = '1';
        button.addEventListener('click', openModal);
      });
      closeButtons.forEach((button) => {
        if (!button || typeof button.addEventListener !== 'function' || button.dataset.shareCloseBound === '1') return;
        button.dataset.shareCloseBound = '1';
        button.addEventListener('click', closeModal);
      });
      safeOn(modal, 'click', (event) => {
        if (event.target === modal) closeModal();
      });

      log('Modal inicializado.');
    };

    globalThis.__EPI_SHARE_MODAL_BOUND__ = true;
    if (document.readyState === 'loading') {
      safeOn(document, 'DOMContentLoaded', bindModal, { once: true });
      return;
    }
    bindModal();
  } catch (error) {
    console.warn('[share-modal] Inicialização ignorada por erro não crítico:', error);
  }
})();
