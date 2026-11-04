'use strict';
// Apenas apresentação: os motivos usados para identificar produtos conservam
// seus valores canônicos no Business. Nenhuma associação é feita aqui.
(function () {
  const keys = Object.freeze({
    'id do item': 'item_id', CA: 'ca', descrição: 'description',
    fabricante: 'manufacturer', modelo: 'model', tamanho: 'size',
    'tamanho de luva': 'glove_size', 'tamanho de uniforme': 'uniform_size',
  });
  function matches(values) {
    return values.map(value => {
      const suffix = keys[value];
      return suffix && typeof globalThis.trEpi === 'function'
        ? globalThis.trEpi('purchase.importReview.match.' + suffix, value) : value;
    }).join(', ');
  }
  globalThis.__EPI_PURCHASE_IMPORT_LABELS__ = Object.freeze({ matches });
})();
