'use strict';

// Módulo de negócio: EPIs — valores do cadastro (Refatoração UBX-V3, Etapa 5).
//
// normalizeEpiSizes (tamanhos ausentes viram 'N/A', mutando os valores do
// formulário como antes) e formatEpiOptionLabel (rótulo do EPI nos seletores
// de estoque). Puro: sem DOM, HTTP, storage ou estado global. CA, fabricante,
// modelo e validade NÃO são decididos aqui — continuam no backend.
(function () {
  if (globalThis.__EPI_MODULE_EPIS_BUSINESS_LOADED__) { return; }
  globalThis.__EPI_MODULE_EPIS_BUSINESS_LOADED__ = true;

  function normalizeEpiSizes(values) {
    values.glove_size = String(values.glove_size || 'N/A');
    values.size = String(values.size || 'N/A');
    values.uniform_size = String(values.uniform_size || 'N/A');
  }

  function formatEpiOptionLabel(item) {
    const sizeParts = [item.glove_size, item.size, item.uniform_size].filter((value) => value && value !== 'N/A');
    const manufacturer = item.manufacturer || '';
    const sizeLabel = sizeParts.length ? ` Tam: ${sizeParts.join(' / ')}` : '';
    const manufacturerLabel = manufacturer ? ` | Fab: ${manufacturer}` : '';
    return `${item.name}${manufacturerLabel}${sizeLabel} | ${item.unit_measure}`;
  }

  // ── Exports ───────────────────────────────────────────────────────────────

  const epiFormValueExports = {
    normalizeEpiSizes,
    formatEpiOptionLabel
  };

  for (const [name, fn] of Object.entries(epiFormValueExports)) {
    globalThis[name] = fn;
  }
  globalThis.__EPI_EPIS_BUSINESS__ = Object.freeze({ ...epiFormValueExports });
})();
