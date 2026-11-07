'use strict';
// Impressão compartilhada UBX: safeOn é resolvido na chamada, após o boot do app.js.
(function () {
  if (globalThis.__EPI_MODULE_SHARED_PRINT_POPUP_LOADED__) { return; }
  globalThis.__EPI_MODULE_SHARED_PRINT_POPUP_LOADED__ = true;

  function openAndPrintPopup(html, features = 'width=1100,height=800') {
    const popup = globalThis.open('', '_blank', features);
    if (!popup) { return null; }
    const markup = String(html || '').trim();
    if (!markup) { return popup; }
    popup.document.open();
    popup.document.write(markup);
    popup.document.close();
    const triggerPrint = () => {
      try {
        popup.focus();
        popup.print();
      } catch (error) {
        console.warn('[print] Falha ao disparar impressão da popup', error);
      }
    };
    if (popup.document.readyState === 'complete') {
      setTimeout(triggerPrint, 80);
    } else {
      safeOn(popup, 'load', () => setTimeout(triggerPrint, 80), { once: true });
      setTimeout(triggerPrint, 500);
    }
    return popup;
  }

  globalThis.openAndPrintPopup = openAndPrintPopup;
  globalThis.__EPI_SHARED_PRINT_POPUP__ = Object.freeze({ openAndPrintPopup });
})();
