'use strict';

// Cadastro de Colaboradores simplificado do web legado (ADR-0002 §10.2) —
// regras puras.
//
// Segue o padrão de js/views/outsourced-companies-view.js: aqui ficam
// filtro e rótulo (funções sem DOM e sem estado global, testadas no
// harness); app.js faz a leitura do estado e a escrita no documento.
(function () {
  if (globalThis.__EPI_MODULE_OUTSOURCED_EMPLOYEES_VIEW_LOADED__) { return; }
  globalThis.__EPI_MODULE_OUTSOURCED_EMPLOYEES_VIEW_LOADED__ = true;

  var VINC_LABELS = {
    'Terceirizado': 'Terceirizado',
    'Prestador de Serviço': 'Prestador de Serviço',
  };

  function tipoVinculoLabel(value) {
    const key = String(value || '').trim();
    return VINC_LABELS[key] || key || 'Outro';
  }

  /**
   * Colaboradores elegíveis ao Cadastro de Colaboradores simplificado:
   * terceirizado/prestador com empresa vinculada — nunca CLT. Mesma regra
   * usada pelo backend (validate_employee_outsourced_simplified_payload) e
   * pelo app Flutter, aqui só para filtrar a listagem client-side (sem rota
   * de listagem própria).
   */
  function outsourcedEmployeesOnly(employees) {
    return (Array.isArray(employees) ? employees : []).filter((item) => {
      const tipo = String(item?.tipo_vinculo || '').trim();
      return Boolean(tipo) && tipo !== 'CLT' && Boolean(item?.outsourced_company_id);
    });
  }

  /**
   * Linhas visíveis da tabela: busca cobre nome e função.
   */
  function visibleOutsourcedEmployees(employees, options) {
    const term = String(options?.search || '').trim().toLowerCase();
    const list = Array.isArray(employees) ? employees : [];
    if (!term) return list;
    return list.filter((item) => {
      const haystack = [item?.name, item?.role_name]
        .map((value) => String(value || '').toLowerCase())
        .join(' ');
      return haystack.includes(term);
    });
  }

  globalThis.__EPI_OUTSOURCED_EMPLOYEES_VIEW__ = Object.freeze({
    tipoVinculoLabel,
    outsourcedEmployeesOnly,
    visibleOutsourcedEmployees,
  });
})();
