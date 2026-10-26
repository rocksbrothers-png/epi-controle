'use strict';

// Módulo de negócio: Relatórios — filtros (Refatoração UBX-V3, Etapa 4).
//
// Regras puras que antes viviam dentro de collectReportFilters e
// renderReports no app.js: validar os filtros do formulário de relatório
// (ids numéricos e datas AAAA-MM-DD, com as mesmas mensagens e na mesma
// ordem de campos) e derivar os filtros do arquivo de fichas a partir deles.
//
// Sem DOM, sem HTTP, sem storage, sem estado global: tudo por parâmetro.
// A autorização efetiva continua no backend (/api/reports, /api/ficha-archive).
(function () {
  if (globalThis.__EPI_MODULE_REPORTS_BUSINESS_LOADED__) { return; }
  globalThis.__EPI_MODULE_REPORTS_BUSINESS_LOADED__ = true;

  // Ordem dos campos = ordem em que o app.js validava (a primeira falha vence).
  const REPORT_FILTER_FIELDS = [
    ['company_id', 'int'],
    ['legal_entity_id', 'int'],
    ['unit_id', 'int'],
    ['employee_id', 'int'],
    ['sector', 'text'],
    ['tipo_vinculo', 'text'],
    ['epi_id', 'int'],
    ['status', 'text'],
    ['start_date', 'date'],
    ['end_date', 'date']
  ];

  function normalizeOptionalInt(fieldName, value) {
    const raw = String(value || '').trim();
    if (!raw) { return ''; }
    if (!/^\d+$/.test(raw)) {
      throw new Error(`Filtro inválido: ${fieldName} deve ser numérico.`);
    }
    return raw;
  }

  function normalizeOptionalDate(fieldName, value) {
    const raw = String(value || '').trim();
    if (!raw) { return ''; }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
      throw new Error(`Filtro inválido: ${fieldName} deve estar no formato AAAA-MM-DD.`);
    }
    return raw;
  }

  // rawValues: { campo: valor lido do formulário (ou undefined) }.
  // Devolve só os campos preenchidos; lança Error com a mensagem original.
  function normalizeReportFilterValues(rawValues = {}) {
    const values = {};
    for (const [field, kind] of REPORT_FILTER_FIELDS) {
      const raw = rawValues[field];
      if (kind === 'int') {
        values[field] = normalizeOptionalInt(field, raw);
      } else if (kind === 'date') {
        values[field] = normalizeOptionalDate(field, raw);
      } else {
        values[field] = String(raw || '').trim();
      }
    }
    return Object.fromEntries(Object.entries(values).filter(([, value]) => value !== ''));
  }

  // Filtros do arquivo de fichas derivados dos filtros do relatório.
  function archiveFiltersFromReportFilters(filters = {}) {
    return {
      company_id: filters.company_id || '',
      unit_id: filters.unit_id || '',
      employee_id: filters.employee_id || '',
      sector: filters.sector || '',
      status: filters.status || '',
      date_from: filters.start_date || '',
      date_to: filters.end_date || ''
    };
  }

  globalThis.__EPI_REPORTS_BUSINESS__ = Object.freeze({
    REPORT_FILTER_FIELDS: Object.freeze(REPORT_FILTER_FIELDS.map((entry) => Object.freeze([...entry]))),
    normalizeReportFilterValues,
    archiveFiltersFromReportFilters
  });
})();
