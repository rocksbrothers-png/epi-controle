'use strict';

(function () {
  if (globalThis.__EPI_CORE_PERMISSIONS_LOADED__) return;
  globalThis.__EPI_CORE_PERMISSIONS_LOADED__ = true;

  const PURCHASE_PERMS = Object.freeze([
    'purchase_requests:view', 'purchase_requests:create', 'purchase_requests:update',
    'purchase_orders:view', 'purchase_orders:create', 'purchase_orders:upload',
    'purchase_orders:approve', 'purchase_orders:receive', 'purchase_orders:review',
    'finance:view'
  ]);

  const SUPPLIERS_MANAGE_PERM = 'suppliers:manage';

  const ROLE_PERMISSIONS = Object.freeze({
    master_admin: Object.freeze([
      'dashboard:view', 'users:view', 'users:create', 'users:update', 'users:delete',
      'units:view', 'units:create', 'units:update', 'units:delete',
      'employees:view', 'employees:create', 'employees:update', 'employees:delete',
      'epis:view', 'epis:create', 'epis:update', 'epis:delete',
      'deliveries:view', 'deliveries:create', 'fichas:view',
      'reports:view', 'alerts:view',
      'companies:view', 'companies:create', 'companies:update', 'companies:license',
      'commercial:view', 'usage:view',
      'stock:view', 'stock:adjust',
      'settings:view', 'settings:update',
      ...PURCHASE_PERMS, SUPPLIERS_MANAGE_PERM, 'unit_links:manage'
    ]),

    general_admin: Object.freeze([
      'dashboard:view', 'users:view', 'users:create', 'users:update', 'users:delete',
      'units:view', 'units:create', 'units:update', 'units:delete',
      'employees:view', 'employees:create', 'employees:update', 'employees:delete',
      'epis:view', 'epis:create', 'epis:update', 'epis:delete',
      'deliveries:view', 'deliveries:create', 'fichas:view',
      'reports:view', 'alerts:view', 'companies:view',
      'stock:view', 'stock:adjust',
      'settings:view', 'settings:update',
      ...PURCHASE_PERMS, SUPPLIERS_MANAGE_PERM, 'unit_links:manage',
      'epi_feedback:view', 'epi_feedback:triage', 'epi_feedback:manager_eval',
      'epi_evaluation:view', 'epi_evaluation:decide', 'epi_evaluation:accept_suggestion'
    ]),

    registry_admin: Object.freeze([
      'dashboard:view', 'users:view', 'users:create', 'users:update', 'users:delete',
      'units:view', 'units:create', 'units:update', 'units:delete',
      'employees:view', 'employees:create', 'employees:update', 'employees:delete',
      'epis:view', 'epis:create', 'epis:update', 'epis:delete',
      'deliveries:view', 'fichas:view',
      'reports:view', 'alerts:view', 'stock:view',
      'settings:view', 'settings:update',
      'purchase_requests:view', 'purchase_requests:create', 'purchase_requests:update',
      'purchase_orders:view', 'purchase_orders:receive', 'finance:view',
      'epi_feedback:view', 'epi_feedback:triage', 'epi_feedback:manager_eval',
      'epi_evaluation:view', 'epi_evaluation:decide'
    ]),

    admin: Object.freeze([
      'dashboard:view', 'users:view', 'units:view',
      'employees:view', 'employees:update',
      'epis:view', 'deliveries:view', 'deliveries:create', 'fichas:view',
      'reports:view', 'alerts:view', 'stock:view', 'stock:adjust',
      'purchase_requests:view', 'purchase_requests:create', 'purchase_requests:update',
      'purchase_orders:view', 'purchase_orders:review', 'purchase_orders:receive',
      'finance:view', 'epi_feedback:view', 'epi_evaluation:view'
    ]),

    buyer: Object.freeze([
      'dashboard:view', 'epis:view', 'units:view', 'stock:view',
      'purchase_requests:view', 'purchase_requests:update',
      'purchase_orders:view', 'purchase_orders:create', 'purchase_orders:upload',
      'finance:view'
    ]),

    approver: Object.freeze([
      'dashboard:view', 'epis:view', 'units:view', 'stock:view',
      'purchase_requests:view', 'purchase_orders:view', 'purchase_orders:approve',
      'finance:view'
    ]),

    user: Object.freeze([
      'dashboard:view', 'deliveries:view', 'deliveries:create', 'fichas:view',
      'alerts:view', 'units:view', 'employees:view', 'employees:update',
      'epis:view', 'stock:view', 'stock:adjust',
      'epi_feedback:view', 'epi_feedback:manager_eval', 'epi_evaluation:view'
    ]),

    employee: Object.freeze([])
  });

  const VIEW_PERMISSIONS = Object.freeze({
    dashboard: 'dashboard:view',
    empresas: 'companies:view',
    comercial: 'commercial:view',
    usuarios: 'users:view',
    unidades: 'units:view',
    colaboradores: 'employees:view',
    'gestao-colaborador': 'employees:update',
    epis: 'epis:view',
    estoque: 'stock:view',
    entregas: 'deliveries:view',
    fichas: 'fichas:view',
    compras: 'purchase_requests:view',
    configuracao: 'settings:view',
    relatorios: 'reports:view',
    avaliacoes: 'epi_evaluation:view'
  });

  const VIEW_EYEBROW = Object.freeze({
    dashboard: 'Visão Geral',
    empresas: 'Administração',
    comercial: 'Administração',
    usuarios: 'Administração',
    unidades: 'Cadastro',
    colaboradores: 'Cadastro',
    'gestao-colaborador': 'Operação',
    epis: 'Cadastro',
    estoque: 'Operação',
    entregas: 'Operação',
    fichas: 'Operação',
    compras: 'Compras',
    configuracao: 'Configuração',
    relatorios: 'Relatórios',
    avaliacoes: 'Avaliações'
  });

  globalThis.PURCHASE_PERMS = PURCHASE_PERMS;
  globalThis.SUPPLIERS_MANAGE_PERM = SUPPLIERS_MANAGE_PERM;
  globalThis.ROLE_PERMISSIONS = ROLE_PERMISSIONS;
  globalThis.VIEW_PERMISSIONS = VIEW_PERMISSIONS;
  globalThis.VIEW_EYEBROW = VIEW_EYEBROW;
})();
