'use strict';

// Marca da plataforma: mesmo POST, corpo e cliente canônico; sem DOM/estado.
// Autorização efetiva permanece no backend (require_master_actor).
(function () {
  if (globalThis.__EPI_MODULE_PLATFORM_BRAND_API_LOADED__) { return; }
  globalThis.__EPI_MODULE_PLATFORM_BRAND_API_LOADED__ = true;

  function saveBrand(values) {
    return globalThis.api('/api/platform-brand', { method: 'POST', body: JSON.stringify(values) });
  }

  globalThis.__EPI_PLATFORM_BRAND_API__ = Object.freeze({ saveBrand });
})();
