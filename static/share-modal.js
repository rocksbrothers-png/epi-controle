'use strict';

(function () {
  if (typeof window === 'undefined' || typeof document === 'undefined') return;
  if (window.__EPI_SHARE_MODAL_INIT_BOUND__) return;
  window.__EPI_SHARE_MODAL_INIT_BOUND__ = true;
  window.__EPI_SHARE_MODAL_VERSION__ = '20260426-09';

  function safeBind(el, event, handler, options) {
    if (!el || typeof el.addEventListener !== 'function') return false;
    if (typeof handler !== 'function') return false;
    try {
      el.addEventListener(event, handler, options);
      return true;
    } catch (error) {
      console.warn('[share-modal] falha ao registrar evento', error);
      return false;
    }
  }

  const safeOn = safeBind;

  function bindShareModal() {
    const root = document.querySelector('[data-share-modal], #share-modal, .share-modal');
    if (!root) return false;

    if (root.dataset.epiShareModalBound === '1') return true;

    const openButtons = Array.from(document.querySelectorAll('[data-share-open]'));
    const closeButtons = Array.from(document.querySelectorAll('[data-share-close]'));

    if (!openButtons.length && !closeButtons.length) return false;

    root.dataset.epiShareModalBound = '1';

    const openModal = function () {
      root.classList.add('is-open');
      root.setAttribute('aria-hidden', 'false');
    };

    const closeModal = function () {
      root.classList.remove('is-open');
      root.setAttribute('aria-hidden', 'true');
    };

    openButtons.forEach((button) => safeOn(button, 'click', openModal));
    closeButtons.forEach((button) => safeOn(button, 'click', closeModal));

    safeOn(root, 'click', function (event) {
      if (event && event.target === root) closeModal();
    });

    return true;
  }

  function bindDownloadButton() {
    const editorContainer = document.querySelector('.tui-image-editor-main-container');
    if (!editorContainer) {
      return false;
    }

    const btn = document.querySelector(
      '.tui-image-editor-main-container .tui-image-editor-download-btn'
    );

    if (!btn) {
      console.warn('[share-modal] botão download não encontrado');
      return false;
    }

    if (btn.dataset.epiDownloadBound === '1') return true;
    btn.dataset.epiDownloadBound = '1';

    safeOn(btn, 'click', (e) => {
      if (!e) return;
    });

    return true;
  }

  function bindWhenReady() {
    const hasBoundModal = bindShareModal();
    if (hasBoundModal) {
      safeOn(document.body || document.documentElement || document, 'htmx:afterSwap', bindShareModal);
    }

    try {
      bindDownloadButton();
    } catch (error) {
      console.error('[share-modal] erro controlado:', error);
    }
  }

  if (document.readyState === 'loading') {
    safeOn(document, 'DOMContentLoaded', bindWhenReady, { once: true });
  } else {
    bindWhenReady();
  }
})();
