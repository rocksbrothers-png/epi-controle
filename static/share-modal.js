'use strict';

(function initShareModal() {
  if (globalThis.__EPI_SHARE_MODAL_BOUND__) return;
  globalThis.__EPI_SHARE_MODAL_BOUND__ = true;

  const log = (message, extra) => {
    if (extra !== undefined) {
      console.debug('[share-modal]', message, extra);
      return;
    }
    console.debug('[share-modal]', message);
  };

  const bindModal = () => {
    const modal = document.getElementById('share-modal');
    if (!modal) {
      log('Modal ausente na página; inicialização ignorada com segurança.');
      return;
    }

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

    openButtons.forEach((button) => button?.addEventListener?.('click', openModal));
    closeButtons.forEach((button) => button?.addEventListener?.('click', closeModal));
    modal.addEventListener('click', (event) => {
      if (event.target === modal) closeModal();
    });

    log('Modal inicializado.');
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindModal, { once: true });
    return;
  }
  bindModal();
})();
