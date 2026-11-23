'use strict';

// UBX Fornecedores F1 — regra pura: linhas importadas → fornecedores autorizados.
//
// Extraída de static/app.js com o corpo idêntico, exceto pela entrada: o rótulo
// traduzido da coluna "Nome" (antes lido de tr('signature.name') a cada linha)
// chega por parâmetro. Quem chama é o importSuppliersCSV do app.js, que o
// resolve no idioma ativo. Sem DOM, sem HTTP, sem tr() e sem globais da página.
//
// rawRows: objetos { cabeçalho: valor } vindos do CSV (cabeçalhos em minúsculas)
// ou da planilha XLS/XLSX (cabeçalhos como estão no arquivo).
// Devolve [{ name, cnpj, email }] só das linhas com nome.
(function () {
  if (globalThis.__EPI_MODULE_SUPPLIER_IMPORT_RULES_LOADED__) { return; }
  globalThis.__EPI_MODULE_SUPPLIER_IMPORT_RULES_LOADED__ = true;

  function _parseSuppliersRows(rawRows, translatedNameLabel) {
    return rawRows
      .map(r => {
        const k = (key) => String(r[key] || r[key?.toLowerCase?.()] || r[key?.toUpperCase?.()] || '').trim();
        const name = k('nome') || k('name') || k('Name') || k(translatedNameLabel) || '';
        if (!name) {return null;}
        return {
          name,
          cnpj: k('cnpj') || k('CNPJ') || '',
          email: k('contato') || k('email') || k('Email') || k('contact_name') || k('contact_email') || '',
        };
      })
      .filter(Boolean);
  }

  // Global legada: o app.js chama o nome direto.
  globalThis._parseSuppliersRows = _parseSuppliersRows;
  globalThis.__EPI_SUPPLIER_IMPORT_RULES__ = Object.freeze({ _parseSuppliersRows });
})();
