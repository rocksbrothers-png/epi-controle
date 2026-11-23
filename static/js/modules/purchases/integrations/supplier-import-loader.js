'use strict';

// UBX Fornecedores F1 — integração: carga sob demanda do SheetJS (leitura de XLS/XLSX).
//
// Extraída de static/app.js com o mesmo fluxo, mas sem tocar a página: tudo o
// que antes vinha de window/document/tr() chega em `deps`, montado pelo
// importSuppliersCSV do app.js.
//
// deps.getXLSX()          → o SheetJS já carregado, ou falsy (window.XLSX).
// deps.createScript()     → um <script> novo (document.createElement('script')).
// deps.appendScript(s)    → anexa o <script> à página (document.head.appendChild).
// deps.loadErrorMessage() → mensagem traduzida, resolvida só se a carga falhar.
//
// Carga única como antes: se o SheetJS já está na página, nenhum <script> novo.
// A URL é a liberada na CSP (core/csp.py) e no teste de navegador
// (scripts/browser/security_csp_v1.py); mudá-la quebra os dois.
(function () {
  if (globalThis.__EPI_MODULE_SUPPLIER_IMPORT_LOADER_LOADED__) { return; }
  globalThis.__EPI_MODULE_SUPPLIER_IMPORT_LOADER_LOADED__ = true;

  const SHEETJS_URL = 'https://cdn.jsdelivr.net/npm/xlsx/dist/xlsx.full.min.js';

  async function _loadSheetJS(deps) {
    if (deps.getXLSX()) {return deps.getXLSX();}
    return new Promise((resolve, reject) => {
      const s = deps.createScript();
      s.src = SHEETJS_URL;
      s.onload = () => resolve(deps.getXLSX());
      s.onerror = () => reject(new Error(deps.loadErrorMessage()));
      deps.appendScript(s);
    });
  }

  // Global legada: o app.js chama o nome direto.
  globalThis._loadSheetJS = _loadSheetJS;
  globalThis.__EPI_SUPPLIER_IMPORT_LOADER__ = Object.freeze({ SHEETJS_URL, _loadSheetJS });
})();
