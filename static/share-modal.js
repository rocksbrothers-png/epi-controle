'use strict';

(function setupShareModalSafe() {
  try {
  function log(message, extra) {
    if (extra !== undefined) {
      console.debug('[share-modal]', message, extra);
      return;
    }
    console.debug('[share-modal]', message);
  }

  function bindShareModal() {
    const modal = document.getElementById('share-modal');
    const openButtons = document.querySelectorAll('[data-share-open]');
    const closeButtons = document.querySelectorAll('[data-share-close]');

    if (!modal) {
      log('Elemento #share-modal não encontrado. Script opcional ignorado.');
      return;
    }

    function openModal() {
      modal.classList.add('is-open');
      modal.removeAttribute('aria-hidden');
    }

    function closeModal() {
      modal.classList.remove('is-open');
      modal.setAttribute('aria-hidden', 'true');
    }

    openButtons.forEach((button) => {
      if (button && typeof button.addEventListener === 'function') {
        button.addEventListener('click', openModal);
      }
    });

    closeButtons.forEach((button) => {
      if (button && typeof button.addEventListener === 'function') {
        button.addEventListener('click', closeModal);
      }
    });

    modal.addEventListener('click', (event) => {
      if (event.target === modal) closeModal();
    });

    log('Inicializado com sucesso');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindShareModal, { once: true });
    return;
  }
  bindShareModal();
  } catch (error) {
    console.debug('[share-modal] inicialização ignorada por erro não crítico', error);
  }
})();
