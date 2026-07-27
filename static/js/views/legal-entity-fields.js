'use strict';

// Campos de CNPJ (LegalEntity) do web legado — helpers puros.
//
// Extraído de app.js seguindo o padrão aditivo das fases de refatoração: aqui
// ficam só funções sem DOM e sem estado global, para que a regra de quais
// CNPJs entram em cada seletor seja testável no harness. A manipulação dos
// elementos continua em app.js.
(function () {
  if (globalThis.__EPI_MODULE_LEGAL_ENTITY_FIELDS_LOADED__) { return; }
  globalThis.__EPI_MODULE_LEGAL_ENTITY_FIELDS_LOADED__ = true;

  /** `active` chega como 0/1 no SQLite e booleano no Postgres. */
  function isActive(entity) {
    const value = entity?.active;
    return value === true || value === 1 || value === '1';
  }

  /**
   * CNPJs da empresa informada.
   *
   * `activeOnly` distingue os dois usos: o cadastro só pode apontar para CNPJ
   * ativo (o backend recusa inativo), enquanto o relatório precisa dos inativos
   * — o histórico deles é preservado e continua consultável.
   *
   * `companyId` vazio não filtra, para o caso do usuário de empresa única em
   * que o seletor de empresa nem aparece.
   */
  function legalEntitiesForCompany(entities, companyId, options) {
    const activeOnly = options?.activeOnly !== false;
    const wanted = String(companyId ?? '').trim();
    return (Array.isArray(entities) ? entities : []).filter((item) => {
      if (wanted && String(item?.company_id) !== wanted) { return false; }
      return activeOnly ? isActive(item) : true;
    });
  }

  /** Rótulo do CNPJ: nome fantasia (ou razão social) seguido do número. */
  function legalEntityLabel(entity) {
    const name = String(entity?.trade_name || entity?.legal_name || '').trim();
    const cnpj = String(entity?.cnpj || '').trim();
    if (!name) { return cnpj; }
    return cnpj ? `${name} - ${cnpj}` : name;
  }

  /**
   * O CNPJ do colaborador só é obrigatório quando há mais de um ativo.
   *
   * Com CNPJ único o backend resolve sozinho e exigir escolha seria ruído; com
   * mais de um ele recusa o cadastro sem o campo. A regra aqui espelha a do
   * servidor em vez de inventar uma própria.
   */
  function employeeLegalEntityRequired(entities) {
    return (Array.isArray(entities) ? entities : []).length > 1;
  }

  globalThis.__EPI_LEGAL_ENTITY_FIELDS__ = Object.freeze({
    legalEntitiesForCompany,
    legalEntityLabel,
    employeeLegalEntityRequired,
  });
})();
