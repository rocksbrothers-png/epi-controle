'use strict';

// Módulo de negócio: Colaboradores (Refatoração UBX-V4, Etapa B1 — extraído de static/app.js).
//
// Puro: sem DOM, HTTP, storage nem leitura de globais. Os filtros chegam por
// parâmetro (a UI lê state.employeesFilters / employeesOpsFilters); o rótulo
// do vínculo para o CSV também (employmentTypeLabel, de shared/ui).
// isOwnWorkforceVinculo e matchesEmployeeSearchText continuam publicados com o
// nome legado (eram globais pelo Annex B e o app.js ainda chama o segundo).
(function () {
  if (globalThis.__EPI_MODULE_EMPLOYEES_BUSINESS_LOADED__) { return; }
  globalThis.__EPI_MODULE_EMPLOYEES_BUSINESS_LOADED__ = true;

  // Único ponto que decide a visibilidade de "Empresa de Origem": chamado no
  // setup inicial, no 'change' do select, na edição e no reset do formulário —
  // nunca `row.hidden = ...` duplicado nesses lugares, para não divergir.
  // Vínculos de mão de obra própria — espelha OWN_WORKFORCE_VINCULOS do backend
  // (modules/employees/service.py). Para eles a empresa é a própria empregadora
  // e responsável pelo EPI, então "Empresa de Origem" não se aplica.
  //
  // Era `tv === 'CLT'`: com Menor Aprendiz, Praticante e Estagiário no seletor,
  // o campo aparecia para os três e o backend recusava o cadastro pedindo uma
  // empresa de origem que não existe.
  const OWN_WORKFORCE_VINCULOS = ['CLT', 'Menor Aprendiz', 'Praticante', 'Estagiário'];

  function isOwnWorkforceVinculo(value) {
    return OWN_WORKFORCE_VINCULOS.includes(String(value || 'CLT').trim());
  }

  function matchesEmployeeSearchText(item, searchValue) {
    const search = String(searchValue || '').trim().toLowerCase();
    if (!search) {return true;}
    const haystack = `${item.name || ''} ${item.employee_id_code || ''} ${item.id || ''}`.toLowerCase();
    return haystack.includes(search);
  }

  // Corpo do antigo applyEmployeesFilters: empresa, unidade atual (ou de
  // cadastro), busca por nome/matrícula/id, setor e função — nesta ordem.
  function filterEmployees(items, filters) {
    return items.filter((item) => {
      if (filters.company_id && String(item.company_id) !== String(filters.company_id)) {return false;}
      const employeeUnitId = String(item.current_unit_id || item.unit_id || '');
      if (filters.unit_id && employeeUnitId !== String(filters.unit_id)) {return false;}
      if (!matchesEmployeeSearchText(item, filters.search)) {return false;}
      if (filters.sector && !String(item.sector || '').toLowerCase().includes(filters.sector)) {return false;}
      if (filters.role_name && !String(item.role_name || '').toLowerCase().includes(filters.role_name)) {return false;}
      return true;
    });
  }

  // Conteúdo do CSV de colaboradores selecionados (antes montado dentro de
  // exportSelectedEmployeesCsv). Cabeçalho, colunas, ";" e aspas dobradas iguais.
  function employeesCsv(rows, employmentTypeLabel) {
    const header = ['Empresa', 'ID', 'Nome', 'CPF', 'E-mail', 'WhatsApp', 'Setor', 'Função', 'Tipo de Vínculo', 'Unidade'];
    const lines = rows.map((e) => [
      e.company_name, e.employee_id_code, e.name, e.cpf, e.email, e.whatsapp,
      e.sector, e.role_name, employmentTypeLabel(e.tipo_vinculo || 'CLT'),
      e.current_unit_name || e.unit_name,
    ]);
    return [header, ...lines]
      .map((row) => row.map((v) => `"${String(v == null ? '' : v).replaceAll('"', '""')}"`).join(';'))
      .join('\n');
  }

  globalThis.isOwnWorkforceVinculo = isOwnWorkforceVinculo;
  globalThis.matchesEmployeeSearchText = matchesEmployeeSearchText;
  globalThis.__EPI_EMPLOYEES_BUSINESS__ = Object.freeze({
    OWN_WORKFORCE_VINCULOS: Object.freeze([...OWN_WORKFORCE_VINCULOS]),
    isOwnWorkforceVinculo,
    matchesEmployeeSearchText,
    filterEmployees,
    employeesCsv
  });
})();
