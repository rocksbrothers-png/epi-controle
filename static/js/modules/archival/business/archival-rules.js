'use strict';

// Módulo de negócio: Arquivamento (Refatoração UBX-V5, Etapa 1 — extraído de static/app.js).
//
// Puro: sem DOM, HTTP, storage nem leitura de globais. Configuração por tipo de
// registro (Colaboradores, EPIs, Empresas terceirizadas, Colaboradores
// terceirizados), rótulos do resumo de exclusão definitiva das Unidades,
// filtros das listas de arquivados e quem vê cada botão. Os caminhos HTTP
// ficam em ../integrations/archival-api.js (escolhidos por `resource`).
// Decisão de fato (permissão, escopo por Unidade, retenção, bloqueio jurídico,
// isolamento por empresa) continua no backend; isto só evita mostrar um botão
// que o backend vai recusar.
(function () {
  if (globalThis.__EPI_MODULE_ARCHIVAL_BUSINESS_LOADED__) { return; }
  globalThis.__EPI_MODULE_ARCHIVAL_BUSINESS_LOADED__ = true;

  const UNIT_PURGE_RECORD_LABELS = {
    employees: 'Colaboradores',
    employee_movements: 'Movimentações de colaboradores',
    epis: 'EPIs',
    deliveries: 'Entregas',
    devolutions: 'Devoluções',
    stock_movements: 'Movimentações de estoque',
    stock_items: 'Itens de estoque (QR Codes)',
    epi_requests: 'Requisições de EPI',
    feedbacks: 'Avaliações e feedbacks',
    ficha_periods: 'Fichas de EPI',
    purchase_requests: 'Requisições de compra',
    purchase_orders: 'Pedidos de compra',
  };

  const EMPLOYEE_PURGE_LABELS = {
    deliveries: 'Entregas', devolutions: 'Devoluções', epi_requests: 'Requisições de EPI',
    feedbacks: 'Avaliações e feedbacks', ficha_periods: 'Fichas de EPI', ficha_items: 'Itens de ficha',
    unit_movements: 'Movimentações de unidade', portal_links: 'Links do portal',
    portal_audit_logs: 'Logs do portal',
  };

  // Arquivamento genérico — mesma política das Unidades. `resource` escolhe o
  // ramo de rotas na integração; `archivedQueryExtra` filtra só a LISTAGEM.
  const ARCHIVAL_ENTITIES = {
    employee: {
      resource: 'employees',
      stateList: 'employees',
      archivedList: 'archivedEmployees',
      filters: 'archivedEmployeesFilters',
      tableRef: 'archivedEmployeesTable',
      i18nPrefix: 'employee',
      labelFallback: 'Colaborador',
      responseKey: 'employees',
      deletePermission: 'employees:delete',
      updatePermission: 'employees:update',
      // FIX-COLAB-TERC-V1: arquivar/desarquivar/excluir definitivamente atualiza
      // as listas sem tirar o usuário da tela (loadBootstrap({preserveView})).
      preserveView: true,
      purgeLabels: EMPLOYEE_PURGE_LABELS,
    },
    epi: {
      resource: 'epis',
      stateList: 'epis',
      archivedList: 'archivedEpis',
      filters: 'archivedEpisFilters',
      tableRef: 'archivedEpisTable',
      i18nPrefix: 'epi',
      labelFallback: 'EPI',
      responseKey: 'epis',
      deletePermission: 'epis:delete',
      updatePermission: 'epis:update',
      // FIX-NAV-REFRESH-V1: mesma regra dos cadastros de Colaboradores.
      preserveView: true,
      purgeLabels: {
        deliveries: 'Entregas', devolutions: 'Devoluções', stock_items: 'Itens de estoque (QR Codes)',
        stock_movements: 'Movimentações de estoque', epi_requests: 'Requisições de EPI',
        feedbacks: 'Avaliações e feedbacks', ficha_items: 'Itens de ficha',
        purchase_request_items: 'Itens de requisição de compra', purchase_order_items: 'Itens de pedido de compra',
      },
    },
    // Empresa terceirizada/prestadora (ADR-0002 §10.4/§10.5/§12). Purge exclui
    // deliberadamente `employees`: um colaborador não é "histórico" da empresa
    // que o contratou (purge_outsourced_company_history no backend).
    // `identityKind` reaproveita a coluna de identidade do EPI (nome + segunda
    // coluna). Segunda permissão (`employees:update_simplified`): Administrador
    // Local/Gestor de EPI, restrito à própria Unidade — o backend
    // (ensure_actor_outsourced_company_scope + ensure_module_enabled_for_unit)
    // valida de novo e é quem decide.
    outsourcedCompany: {
      resource: 'outsourced-companies',
      stateList: 'outsourcedCompanies',
      archivedList: 'archivedOutsourcedCompanies',
      filters: 'archivedOutsourcedCompaniesFilters',
      tableRef: 'archivedOutsourcedCompaniesTable',
      i18nPrefix: 'outsourcedCompany',
      labelFallback: 'Empresa terceirizada',
      responseKey: 'outsourced_companies',
      preserveView: true,
      deletePermission: 'employees:update employees:update_simplified',
      updatePermission: 'employees:update employees:update_simplified',
      identityKind: 'outsourcedCompanyLike',
      purgeLabels: {
        service_contracts: 'Contratos de prestação de serviço', unit_links: 'Vínculos com Unidades',
        update_requests: 'Solicitações de atualização cadastral', epi_reimbursements: 'Ressarcimentos de EPI',
      },
    },
    // Colaborador terceirizado/prestador (ADR-0002 §10.4/§10.5) — MESMA rota de
    // arquivamento do colaborador CLT; só a LISTAGEM de arquivados é filtrada
    // (?outsourced_only=1) para não misturar com "Colaboradores Arquivados".
    // `identityKind: 'employee'` reaproveita a linha e os textos `employee.*`.
    // Segunda permissão: Administrador Local/Gestor de EPI só arquivam o PRÓPRIO
    // cadastro simplificado — o backend (_load_employee_for_lifecycle/
    // outsourced_alternative) recusa CLT ou outra Unidade.
    outsourcedEmployee: {
      resource: 'employees',
      stateList: 'employees',
      archivedList: 'archivedOutsourcedEmployees',
      filters: 'archivedOutsourcedEmployeesFilters',
      tableRef: 'archivedOutsourcedEmployeesTable',
      i18nPrefix: 'employee',
      labelFallback: 'Colaborador',
      responseKey: 'employees',
      deletePermission: 'employees:delete employees:update_simplified',
      updatePermission: 'employees:update employees:update_simplified',
      identityKind: 'employee',
      archivedQueryExtra: '&outsourced_only=1',
      preserveView: true,
      purgeLabels: EMPLOYEE_PURGE_LABELS,
    },
  };

  for (const cfg of Object.values(ARCHIVAL_ENTITIES)) {
    Object.freeze(cfg.purgeLabels);
    Object.freeze(cfg);
  }
  Object.freeze(ARCHIVAL_ENTITIES);

  function archivalConfig(kind) {
    return Object.prototype.hasOwnProperty.call(ARCHIVAL_ENTITIES, kind) ? ARCHIVAL_ENTITIES[kind] : undefined;
  }

  // Permissão de LEITURA da lista de arquivados. Troca só a primeira ocorrência
  // de ':update' (comportamento herdado): 'employees:update employees:update_simplified'
  // vira 'employees:view employees:update_simplified'.
  function archivedViewPermission(cfg) {
    return cfg.updatePermission.replace(':update', ':view');
  }

  // Filtros das listas de arquivados (Unidades e genérico usam os mesmos). Os
  // valores de `reason`/`user` já chegam em minúsculas (sync*Filters).
  function matchesArchivedFilters(item, filters) {
    if (filters.company_id && String(item.company_id) !== String(filters.company_id)) {return false;}
    if (filters.date && !String(item.archived_at || '').startsWith(filters.date)) {return false;}
    if (filters.reason && !String(item.archive_reason || '').toLowerCase().includes(filters.reason)) {return false;}
    if (filters.user && !String(item.archived_by_name || '').toLowerCase().includes(filters.user)) {return false;}
    return true;
  }

  function filterArchivedItems(items, filters) {
    return items.filter((item) => matchesArchivedFilters(item, filters));
  }

  // Valores dos campos de filtro → filtros normalizados.
  function normalizeArchivedFilters(values) {
    return {
      company_id: String(values.company || '').trim(),
      date: String(values.date || '').trim(),
      reason: String(values.reason || '').trim().toLowerCase(),
      user: String(values.user || '').trim().toLowerCase(),
    };
  }

  // Quem vê cada botão. Exclusão definitiva: só general_admin/registry_admin,
  // em qualquer tipo (nunca master_admin — PAPEIS_E_ATRIBUICOES.md #1).
  // Desarquivar no genérico: master/general/registry, e Administrador Local/
  // Gestor de EPI só para Empresas terceirizadas e Colaboradores terceirizados
  // da própria Unidade (ADR-0002 §10.5). Unidades: general/registry.
  const UNIT_SCOPED_MANAGE_KINDS = ['outsourcedCompany', 'outsourcedEmployee'];

  function canPurgeArchived(role) {
    return ['general_admin', 'registry_admin'].includes(role);
  }

  function canManageArchived(kind, role) {
    return ['master_admin', 'general_admin', 'registry_admin'].includes(role)
      || (UNIT_SCOPED_MANAGE_KINDS.includes(kind) && ['admin', 'user'].includes(role));
  }

  function canManageArchivedUnits(role) {
    return ['general_admin', 'registry_admin'].includes(role);
  }

  // Retenção mínima cumprida (dias restantes ≤ 0) e sem bloqueio jurídico.
  function isRetentionOver(item) {
    return Number(item.retention_days_remaining || 0) <= 0;
  }

  function hasLegalHold(item) {
    return Boolean(Number(item.legal_hold || 0));
  }

  function isPurgeable(item) {
    return isRetentionOver(item) && !hasLegalHold(item);
  }

  // Linhas do resumo da etapa 1 da exclusão definitiva.
  function purgeSummaryLines(labels, records) {
    return Object.entries(labels)
      .map(([key, label]) => `• ${label}: ${Number(records[key] || 0)}`)
      .join('\n');
  }

  // Nome exibido no pedido de confirmação. Empresas terceirizadas não têm
  // `name` (vêm com legal_name/trade_name).
  function purgeDisplayName(record) {
    return record.name || record.legal_name || record.trade_name || '';
  }

  globalThis.__EPI_ARCHIVAL_RULES__ = Object.freeze({
    UNIT_PURGE_RECORD_LABELS: Object.freeze({ ...UNIT_PURGE_RECORD_LABELS }),
    ARCHIVAL_KINDS: Object.freeze(Object.keys(ARCHIVAL_ENTITIES)),
    archivalConfig,
    archivedViewPermission,
    matchesArchivedFilters,
    filterArchivedItems,
    normalizeArchivedFilters,
    canPurgeArchived,
    canManageArchived,
    canManageArchivedUnits,
    isRetentionOver,
    hasLegalHold,
    isPurgeable,
    purgeSummaryLines,
    purgeDisplayName
  });
})();
