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

  // Vínculos de mão de obra CONTRATADA — espelha CONTRACTED_VINCULOS do
  // backend (`modules/employees/service.py`). Fonte única no frontend: quem
  // precisar da lista lê daqui pelo export congelado, em vez de repetir o
  // literal. Há teste de paridade travando a igualdade com o backend.
  //
  // "Temporário" entrou junto com a decisão de que os três vínculos
  // contratados existem exclusivamente no módulo Terceirizados (PR #214).
  var CONTRACTED_VINCULOS = ['Terceirizado', 'Prestador de Serviço', 'Temporário'];

  var VINC_LABELS = {
    'Terceirizado': 'Terceirizado',
    'Prestador de Serviço': 'Prestador de Serviço',
    'Temporário': 'Temporário',
  };

  function isContractedVinculo(value) {
    return CONTRACTED_VINCULOS.indexOf(String(value || '').trim()) !== -1;
  }

  function tipoVinculoLabel(value) {
    const key = String(value || '').trim();
    return VINC_LABELS[key] || key || 'Outro';
  }

  /**
   * Colaboradores elegíveis ao Cadastro de Colaboradores simplificado: mão de
   * obra contratada com empresa vinculada.
   *
   * A condição era `tipo !== 'CLT'` — o mesmo anti-padrão que o PR #214
   * eliminou no backend e no `app.js`, e que sobreviveu aqui. Enquanto CLT era
   * o único vínculo próprio os dois davam no mesmo; com Menor Aprendiz,
   * Praticante e Estagiário deixaram de dar. Na prática o `&&
   * outsourced_company_id` segurava (aprendiz não tem empresa terceirizada),
   * mas o predicado estava errado e era uma armadilha esperando o primeiro
   * chamador que não filtrasse por empresa.
   *
   * Agora é uma lista explícita, espelhada do backend, com teste de paridade.
   */
  function outsourcedEmployeesOnly(employees) {
    return (Array.isArray(employees) ? employees : []).filter(
      (item) => isContractedVinculo(item?.tipo_vinculo) && Boolean(item?.outsourced_company_id)
    );
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
    CONTRACTED_VINCULOS: Object.freeze(CONTRACTED_VINCULOS.slice()),
    isContractedVinculo,
    tipoVinculoLabel,
    outsourcedEmployeesOnly,
    visibleOutsourcedEmployees,
  });
})();
