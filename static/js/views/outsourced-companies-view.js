'use strict';

// Tela de Terceirizados e Prestadores do web legado (ADR-0002) — regras puras.
//
// Segue o padrão de js/views/legal-entities-view.js: aqui ficam filtro,
// rótulos e permissão de linha (funções sem DOM e sem estado global,
// testadas no harness); app.js faz a leitura do estado e a escrita no
// documento.
(function () {
  if (globalThis.__EPI_MODULE_OUTSOURCED_COMPANIES_VIEW_LOADED__) { return; }
  globalThis.__EPI_MODULE_OUTSOURCED_COMPANIES_VIEW_LOADED__ = true;

  // Valores técnicos estáveis (inglês) — condição vinculante do ADR-0002:
  // o rótulo em português vive só aqui, nunca é gravado na coluna.
  var KIND_LABELS = {
    outsourced: 'Terceirizada',
    service_provider: 'Prestadora de Serviço',
    other_contracted: 'Outro',
  };

  function companyKindLabel(value) {
    const key = String(value || '').trim();
    return KIND_LABELS[key] || 'Outro';
  }

  function isSimplified(entity) {
    return String(entity?.registration_mode || 'simplified') !== 'standard';
  }

  function registrationModeLabel(entity) {
    return isSimplified(entity) ? 'Simplificado' : 'Padrão';
  }

  /**
   * Linhas visíveis da tabela.
   *
   * A busca cobre razão social, nome fantasia e CNPJ — inclusive quando
   * vazio (Cadastro Simplificado permite CNPJ em branco), sem quebrar o
   * filtro por tipo.
   */
  function visibleOutsourcedCompanies(companies, options) {
    const kind = String(options?.kind || '').trim();
    const term = String(options?.search || '').trim().toLowerCase();
    return (Array.isArray(companies) ? companies : []).filter((item) => {
      if (kind && String(item?.company_kind || '') !== kind) { return false; }
      if (!term) { return true; }
      const haystack = [item?.legal_name, item?.trade_name, item?.cnpj]
        .map((value) => String(value || '').toLowerCase())
        .join(' ');
      return haystack.includes(term);
    });
  }

  /**
   * Botão "Promover ao Cadastro Padrão" só faz sentido para quem ainda está
   * no Simplificado — o backend também recusa promover quem já é Padrão,
   * mas escondê-lo aqui evita oferecer uma ação sem efeito.
   */
  function canPromote(entity) {
    return isSimplified(entity);
  }

  globalThis.__EPI_OUTSOURCED_COMPANIES_VIEW__ = Object.freeze({
    companyKindLabel,
    isSimplified,
    registrationModeLabel,
    visibleOutsourcedCompanies,
    canPromote,
  });
})();
