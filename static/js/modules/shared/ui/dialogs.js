'use strict';
// safeOn é global do app.js (declarado na config do ESLint), resolvido na chamada:
// bindModalKeyboard só é chamado depois do boot.

// UI compartilhada: diálogos (Refatoração UBX-V4, Etapa A — extraído de static/app.js).
//
// confirmDestructive: confirmação estilizada de ações destrutivas. Delega ao
// dsConfirm (views/ui-helpers.js) quando presente; senão cai no confirm nativo.
// Mesmo contrato de retorno: Promise do booleano de dsConfirm/confirm — quem
// chama decide; nada é executado aqui.
// openModal/closeModal/bindModalKeyboard/getFocusableElements: abertura e
// fechamento de modais com devolução de foco, Escape e ciclo de Tab, usados
// pelo app.js e por views/devolution.js (que os resolve em globalThis).
// O estado de foco/teclado (WeakMaps) era de bloco no app.js e só estas
// funções o usavam; continua privado, agora no módulo.
// confirmDestructive era `async function` de bloco no app.js; agora é global.
(function () {
  if (globalThis.__EPI_MODULE_SHARED_DIALOGS_LOADED__) { return; }
  globalThis.__EPI_MODULE_SHARED_DIALOGS_LOADED__ = true;

  const modalFocusState = new WeakMap();
  const modalKeydownState = new WeakMap();

  async function confirmDestructive(opts) {
    const o = opts || {};
    if (typeof globalThis.dsConfirm === 'function') { return globalThis.dsConfirm(o); }
    return globalThis.confirm(o.message || '');
  }

  function getFocusableElements(container) {
    if (!container) {return [];}
    return Array.from(container.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'))
      .filter((el) => !el.disabled && !el.hidden && el.getAttribute('aria-hidden') !== 'true');
  }

  function openModal(modalElement) {
    if (!modalElement) {return;}
    modalFocusState.set(modalElement, document.activeElement instanceof HTMLElement ? document.activeElement : null);
    modalElement.hidden = false;
    if ('inert' in modalElement) {modalElement.inert = false;}
    modalElement.classList.add('is-open');
    const focusables = getFocusableElements(modalElement);
    (focusables[0] || modalElement).focus?.();
  }

  function closeModal(modalElement) {
    if (!modalElement) {return;}
    if (modalElement.contains(document.activeElement)) {document.activeElement?.blur?.();}
    modalElement.hidden = true;
    if ('inert' in modalElement) {modalElement.inert = true;}
    modalElement.classList.remove('is-open');
    const previousFocus = modalFocusState.get(modalElement);
    if (previousFocus?.isConnected) {previousFocus.focus();}
  }

  function bindModalKeyboard(modalElement, onClose) {
    if (!modalElement || modalKeydownState.has(modalElement)) {return;}
    const keydownHandler = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose?.();
        return;
      }
      if (event.key !== 'Tab') {return;}
      const focusables = getFocusableElements(modalElement);
      if (!focusables.length) {return;}
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    safeOn(modalElement, 'keydown', keydownHandler);
    modalKeydownState.set(modalElement, keydownHandler);
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  const dialogsExports = {
    confirmDestructive,
    getFocusableElements,
    openModal,
    closeModal,
    bindModalKeyboard
  };

  for (const [name, fn] of Object.entries(dialogsExports)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_SHARED_DIALOGS__ = Object.freeze({ ...dialogsExports });
})();
