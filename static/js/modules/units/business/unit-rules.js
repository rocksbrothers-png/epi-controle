'use strict';

// Módulo de negócio: Unidades (Refatoração UBX-V5, Etapa 2 — extraído de static/app.js).
//
// Puro: sem DOM, HTTP, storage nem leitura de globais. Os filtros e a lista
// chegam por parâmetro (a UI lê state.unitsFilters / state.units, já limitados
// à empresa do usuário por filterByUserCompany). Nome e cidade comparam em
// minúsculas porque syncUnitsSearchFilters já guarda os termos assim.
(function () {
  if (globalThis.__EPI_MODULE_UNITS_BUSINESS_LOADED__) { return; }
  globalThis.__EPI_MODULE_UNITS_BUSINESS_LOADED__ = true;

  function filterUnits(items, filters) {
    return items.filter((item) => {
      if (filters.company_id && String(item.company_id) !== String(filters.company_id)) {return false;}
      if (filters.type && String(item.unit_type) !== String(filters.type)) {return false;}
      if (filters.name && !String(item.name || '').toLowerCase().includes(filters.name)) {return false;}
      if (filters.city && !String(item.city || '').toLowerCase().includes(filters.city)) {return false;}
      return true;
    });
  }

  // Unidades de uma empresa (todas, quando companyId vem vazio).
  function unitsOfCompany(units, companyId) {
    return units.filter((item) => !companyId || String(item.company_id) === String(companyId));
  }

  globalThis.__EPI_UNITS_BUSINESS__ = Object.freeze({ filterUnits, unitsOfCompany });
})();
