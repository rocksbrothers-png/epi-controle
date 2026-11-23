'use strict';

// UBX Fornecedores F1 — integração: carga sob demanda do SheetJS (planilhas XLS/XLSX).
// Corpo idêntico ao do app.js; as dependências do navegador chegam por parâmetro:
//   win          — onde o SheetJS publica XLSX (a janela da página);
//   doc          — o documento onde a tag <script> é criada e anexada ao <head>;
//   errorMessage — função que devolve a mensagem traduzida; só é chamada se a carga falhar.
// URL, ordem dos passos e mensagens não mudam (CDN/SRI/CSP ficam para fatia própria).
// Publica só o namespace congelado __EPI_SUPPLIER_IMPORT_LOADER__.
(function () {
  if (globalThis.__EPI_MODULE_SUPPLIER_IMPORT_LOADER_LOADED__) { return; }
  globalThis.__EPI_MODULE_SUPPLIER_IMPORT_LOADER_LOADED__ = true;

  async function _loadSheetJS({ win, doc, errorMessage }) {
    if (win.XLSX) return win.XLSX;
    return new Promise((resolve, reject) => {
      const s = doc.createElement('script');
      s.src = 'https://cdn.jsdelivr.net/npm/xlsx/dist/xlsx.full.min.js';
      s.onload = () => resolve(win.XLSX);
      s.onerror = () => reject(new Error((errorMessage())));
      doc.head.appendChild(s);
    });
  }

  globalThis.__EPI_SUPPLIER_IMPORT_LOADER__ = Object.freeze({ _loadSheetJS });
})();
