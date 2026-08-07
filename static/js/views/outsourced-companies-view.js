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

  /**
   * Trava pós-promoção (ADR-0002 §12): uma vez promovida ao Cadastro
   * Padrão, editar dados corporativos e arquivar/reativar passam a ser
   * exclusivos de Administrador Geral/de Registro — espelha exatamente
   * `ensure_actor_can_edit_outsourced_company_corporate_fields` do backend
   * (modules/outsourced_companies/service.py), que é quem decide de fato;
   * esta função só evita oferecer "Editar"/"Arquivar" sem efeito na UI.
   */
  function isCorporateLocked(entity) {
    return !isSimplified(entity);
  }

  /**
   * Só quem tem `employees:update` completo (Administrador Geral/de
   * Registro) segue liberado para editar/arquivar um registro travado —
   * `permissions` é o array já resolvido por `hasPermission`/`state.permissions`
   * do chamador, esta função não sabe nada de `state`.
   */
  function canEditCorporateFields(entity, hasFullUpdatePermission) {
    return !isCorporateLocked(entity) || Boolean(hasFullUpdatePermission);
  }

  /**
   * "Arquivada nesta Unidade" (vínculo local desativado — Problemas 2/3/4
   * do pedido de auditoria: "Desativar vínculo local" É o arquivamento por
   * Unidade, só renomeado). `local_status` só existe em itens já
   * vinculados de perfis escopados por Unidade
   * (annotate_outsourced_company_visibility) — ausente (undefined/null,
   * perfil sem escopo ou item ainda não vinculado) nunca conta como
   * arquivado. Espelha `is_outsourced_company_available_to_unit` do
   * backend (modules/outsourced_companies/service.py), que é quem decide
   * de fato; usada tanto para tirar a empresa da Lista principal quanto do
   * seletor de novos colaboradores desta Unidade.
   */
  function isArchivedInUnit(entity) {
    return String(entity?.local_status || '') === 'inactive';
  }

  globalThis.__EPI_OUTSOURCED_COMPANIES_VIEW__ = Object.freeze({
    companyKindLabel,
    isSimplified,
    registrationModeLabel,
    visibleOutsourcedCompanies,
    canPromote,
    isCorporateLocked,
    canEditCorporateFields,
    isArchivedInUnit,
  });
})();
