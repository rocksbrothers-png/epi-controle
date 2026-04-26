'use strict';

(function () {
  if (typeof window === 'undefined' || typeof document === 'undefined') return;
  if (window.__EPI_SHARE_MODAL_INIT_BOUND__) return;
  window.__EPI_SHARE_MODAL_INIT_BOUND__ = true;
  window.__EPI_SHARE_MODAL_VERSION__ = '20260426-09';

  function safeOn(target, eventName, handler, options) {
    if (!target || typeof handler !== 'function') return false;
    if (typeof target.addEventListener !== 'function') return false;
    try {
      target.addEventListener(eventName, handler, options);
      return true;
    } catch (error) {
      console.warn('[share-modal] falha ao registrar evento', error);
      return false;
    }
  }

  function bindShareModal() {
    const root = document.querySelector('[data-share-modal], #share-modal, .share-modal');
    if (!root) return false;
    if (root.dataset.epiShareModalBound === '1') return true;

    const openButtons = Array.from(document.querySelectorAll('[data-share-open]'));
    const closeButtons = Array.from(document.querySelectorAll('[data-share-close]'));
    if (!openButtons.length && !closeButtons.length) return false;

    root.dataset.epiShareModalBound = '1';

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
      if (event?.target === root) closeModal();
    });

    return true;
  }

  function bindDownloadButton() {
    const editorContainer = document.querySelector('.tui-image-editor-main-container');
    if (!editorContainer) return false;

    const button = editorContainer.querySelector('.tui-image-editor-download-btn');
    if (!button) return false;
    if (button.dataset.epiDownloadBound === '1') return true;

    button.dataset.epiDownloadBound = '1';
    safeOn(button, 'click', (event) => {
      if (!event) return;
    });
    return true;
  }

  function bindWhenReady() {
    const modalWasBound = bindShareModal();
    if (modalWasBound) {
      safeOn(document.body || document.documentElement || document, 'htmx:afterSwap', bindShareModal);
    }
    bindDownloadButton();
  }

  if (document.readyState === 'loading') {
    safeOn(document, 'DOMContentLoaded', bindWhenReady, { once: true });
  } else {
    bindWhenReady();
  }
})();
