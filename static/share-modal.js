'use strict';

(function initShareModal() {
  try {
    const doc = typeof document === 'undefined' ? null : document;
    if (!doc) return;
    if (globalThis.__EPI_SHARE_MODAL_BOUND__) return;
    const root = doc.querySelector('[data-share-modal], #share-modal, .share-modal');
    if (!root) return;

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
      const modal = root.id === 'share-modal' ? root : doc.getElementById('share-modal');
      const modal = doc.getElementById('share-modal');
      if (!modal) {
        log('Modal ausente na página; inicialização ignorada com segurança.');
        return;
      }
      if (modal.dataset.shareModalBound === '1') {
        log('Modal já inicializado anteriormente; binding idempotente preservado.');
        return;
      }
      modal.dataset.shareModalBound = '1';

      const openButtons = Array.from(doc.querySelectorAll('[data-share-open]') || []);
      const closeButtons = Array.from(doc.querySelectorAll('[data-share-close]') || []);

      const openModal = () => {
        modal.classList.add('is-open');
        modal.setAttribute('aria-hidden', 'false');
      };

      const closeModal = () => {
        modal.classList.remove('is-open');
        modal.setAttribute('aria-hidden', 'true');
      };

      openButtons.forEach((button) => {
        if (!button || button.dataset.shareOpenBound === '1') return;
        button.dataset.shareOpenBound = '1';
        safeOn(button, 'click', openModal);
      });
      closeButtons.forEach((button) => {
        if (!button || button.dataset.shareCloseBound === '1') return;
        button.dataset.shareCloseBound = '1';
        safeOn(button, 'click', closeModal);
      });
      safeOn(modal, 'click', (event) => {
        if (event.target === modal) closeModal();
      });

      log('Modal inicializado.');
    };

    globalThis.__EPI_SHARE_MODAL_BOUND__ = true;
    const safeBindModal = () => {
      try {
        bindModal();
      } catch (error) {
        console.warn('[share-modal] binding ignorado por erro não crítico:', error);
      }
    };

    if (doc.readyState === 'loading') {
      safeOn(doc, 'DOMContentLoaded', safeBindModal, { once: true });
      return;
    }
    safeBindModal();
  } catch (error) {
    console.warn('[share-modal] Inicialização ignorada por erro não crítico:', error);
  }
})();
