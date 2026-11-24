'use strict';

// UBX Fornecedores F1 — regra pura: linhas da planilha de fornecedores -> cadastros.
// Corpo idêntico ao do app.js, com uma única troca: o rótulo traduzido do cabeçalho
// "Nome" chega por parâmetro (resolveNameLabel), em vez de a função chamar o tradutor.
// É uma função para manter a avaliação preguiçosa do original: só é consultada, linha a
// linha, quando nome/name/Name estão vazios. Sem DOM, HTTP, estado ou globais; publica
// só o namespace congelado __EPI_SUPPLIER_IMPORT_RULES__.
(function () {
  if (globalThis.__EPI_MODULE_SUPPLIER_IMPORT_RULES_LOADED__) { return; }
  globalThis.__EPI_MODULE_SUPPLIER_IMPORT_RULES_LOADED__ = true;

  function _parseSuppliersRows(rawRows, resolveNameLabel) {
    return rawRows
      .map(r => {
        const k = (key) => String(r[key] || r[key?.toLowerCase?.()] || r[key?.toUpperCase?.()] || '').trim();
        const name = k('nome') || k('name') || k('Name') || k((resolveNameLabel())) || '';
        if (!name) return null;
        return {
          name,
          cnpj: k('cnpj') || k('CNPJ') || '',
          email: k('contato') || k('email') || k('Email') || k('contact_name') || k('contact_email') || '',
        };
      })
      .filter(Boolean);
  }

  globalThis.__EPI_SUPPLIER_IMPORT_RULES__ = Object.freeze({ _parseSuppliersRows });
})();
