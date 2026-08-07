if (!globalThis.__EPI_APP_RUNTIME_LOADED__) {
  globalThis.__EPI_APP_RUNTIME_LOADED__ = true;

var STORAGE_KEYS = globalThis.STORAGE_KEYS || Object.freeze({
  session: 'epi-session-v4',
  permissions: 'epi-session-v4-permissions',
  token: 'epi-session-v4-token',
  changeRequired: 'epi-session-v4-password-change-required'
});
globalThis.STORAGE_KEYS = STORAGE_KEYS;
const USER_COMPANY_REQUIRED_ROLES = Object.freeze(['general_admin', 'registry_admin', 'admin', 'user', 'buyer', 'approver', 'employee']);
const ROLE_LABELS = {
  master_admin: 'Administrador Master',
  general_admin: 'Administrador Geral',
  registry_admin: 'Administrador de Registro',
  admin: 'Administrador Local',
  user: 'Gestor de EPI',
  buyer: 'Comprador',
  approver: 'Aprovador',
  employee: 'Funcionário'
};

var tr = (globalThis.EpiI18nHelper && typeof globalThis.EpiI18nHelper.resolveLegacyTranslator === 'function')
  ? globalThis.EpiI18nHelper.resolveLegacyTranslator()
  : ((typeof globalThis.trEpi === 'function') ? globalThis.trEpi : function tr(key, fallback) {
    try {
      const v = (typeof window !== 'undefined' && typeof window.t === 'function') ? window.t(key) : null;
      return (v && v !== key) ? v : (fallback !== undefined ? fallback : key);
    } catch (_e) {
      return fallback !== undefined ? fallback : key;
    }
  });
if (typeof globalThis.trEpi !== 'function') globalThis.trEpi = tr;
const PURCHASE_PERMS = ['purchase_requests:view', 'purchase_requests:create', 'purchase_requests:update', 'purchase_orders:view', 'purchase_orders:create', 'purchase_orders:upload', 'purchase_orders:approve', 'purchase_orders:receive', 'purchase_orders:review', 'finance:view'];
const SUPPLIERS_MANAGE_PERM = 'suppliers:manage';
const PPE_TEST_ALL_PERMS = ['ppe_test:view', 'ppe_test:suggest', 'ppe_test:triage', 'ppe_test:manage', 'ppe_test:evaluate', 'ppe_test:tech_review', 'ppe_test:decide', 'ppe_test:homologate'];
// master_admin e registry_admin não retêm employees:create/update/delete,
// deliveries:create, stock:adjust nem purchase_requests:create/update de
// forma permanente (docs/PAPEIS_E_ATRIBUICOES.md #1 e #3; decisão de
// 2026-07-29) — mesmo escopo de core/permissions.py, aqui só como fallback
// de bootstrap indisponível.
// ADR-0002 §10 (Cadastro de Colaboradores simplificado): igual ao backend
// (core/permissions.py MASTER_ADMIN_OPERATIONAL_EXCLUSIONS), master_admin
// também não retém employees:create_simplified/update_simplified de forma
// permanente — mesma razão dos pares completos acima.
const MASTER_ADMIN_OPERATIONAL_EXCLUSIONS = ['employees:create', 'employees:update', 'employees:delete', 'employees:create_simplified', 'employees:update_simplified', 'deliveries:create', 'stock:adjust', 'purchase_requests:create', 'purchase_requests:update'];
// Centro de Migração de Dados (ADR-0003 §2.5): só master_admin e
// general_admin, exatamente como PERM_DATA_MIGRATION_MANAGE em
// core/permissions.py. Administrador Local, Gestores e Colaboradores nunca
// recebem — o backend é quem decide, isto aqui é só fallback de bootstrap.
const DATA_MIGRATION_PERM = 'data_migration:manage';
const ROLE_PERMISSIONS = {
  master_admin: ['dashboard:view', 'users:view', 'users:create', 'users:update', 'users:delete', 'units:view', 'units:create', 'units:update', 'units:delete', 'employees:view', 'employees:create', 'employees:update', 'employees:transfer', 'employees:delete', 'employees:create_simplified', 'employees:update_simplified', 'epis:view', 'epis:create', 'epis:update', 'epis:delete', 'deliveries:view', 'deliveries:create', 'fichas:view', 'reports:view', 'alerts:view', 'companies:view', 'companies:create', 'companies:update', 'companies:license', 'commercial:view', 'usage:view', 'stock:view', 'stock:adjust', 'settings:view', 'settings:update', 'companies:support', ...PURCHASE_PERMS, SUPPLIERS_MANAGE_PERM, 'unit_links:manage', 'ppe_test:view', DATA_MIGRATION_PERM].filter(p => !MASTER_ADMIN_OPERATIONAL_EXCLUSIONS.includes(p)),
  general_admin: ['dashboard:view', 'users:view', 'users:create', 'users:update', 'users:delete', 'units:view', 'units:create', 'units:update', 'units:delete', 'employees:view', 'employees:create', 'employees:update', 'employees:transfer', 'employees:delete', 'employees:create_simplified', 'employees:update_simplified', 'epis:view', 'epis:create', 'epis:update', 'epis:delete', 'deliveries:view', 'deliveries:create', 'fichas:view', 'reports:view', 'alerts:view', 'companies:view', 'stock:view', 'stock:adjust', 'settings:view', 'settings:update', ...PURCHASE_PERMS, SUPPLIERS_MANAGE_PERM, 'unit_links:manage', 'epi_feedback:view', 'epi_feedback:triage', 'epi_feedback:manager_eval', 'epi_evaluation:view', 'epi_evaluation:decide', 'epi_evaluation:accept_suggestion', 'company_settings:view', 'company_settings:update', DATA_MIGRATION_PERM, ...PPE_TEST_ALL_PERMS],
  registry_admin: ['dashboard:view', 'users:view', 'users:create', 'users:update', 'users:delete', 'units:view', 'units:create', 'units:update', 'units:delete', 'employees:view', 'employees:create', 'employees:update', 'employees:transfer', 'employees:delete', 'employees:create_simplified', 'employees:update_simplified', 'epis:view', 'epis:create', 'epis:update', 'epis:delete', 'deliveries:view', 'fichas:view', 'reports:view', 'alerts:view', 'stock:view', 'settings:view', 'settings:update', 'purchase_requests:view', 'purchase_orders:view', 'finance:view', 'epi_feedback:view', 'epi_feedback:triage', 'epi_feedback:manager_eval', 'epi_evaluation:view', 'epi_evaluation:decide', 'ppe_test:view', 'ppe_test:suggest', 'ppe_test:triage', 'ppe_test:manage', 'ppe_test:evaluate', 'ppe_test:tech_review'],
  // Sem employees:update: edição de cadastro e reativação são atribuição do
  // Administrador de Registro. O Administrador Local transfere colaboradores
  // entre unidades via employees:transfer. Tem, porém,
  // employees:create_simplified/update_simplified (ADR-0002 §10.2): Cadastro
  // de Colaboradores só cobre terceirizado/prestador, nunca CLT — por isso é
  // uma permissão própria, não employees:create/update.
  admin: ['dashboard:view', 'users:view', 'units:view', 'employees:view', 'employees:transfer', 'employees:create_simplified', 'employees:update_simplified', 'epis:view', 'deliveries:view', 'deliveries:create', 'fichas:view', 'reports:view', 'alerts:view', 'stock:view', 'stock:adjust', 'purchase_requests:view', 'purchase_requests:create', 'purchase_requests:update', 'purchase_orders:view', 'purchase_orders:review', 'purchase_orders:receive', 'finance:view', 'epi_feedback:view', 'epi_evaluation:view', 'ppe_test:view', 'ppe_test:suggest'],
  buyer: ['dashboard:view', 'epis:view', 'units:view', 'stock:view', 'purchase_requests:view', 'purchase_requests:update', 'purchase_orders:view', 'purchase_orders:create', 'purchase_orders:upload', 'finance:view'],
  approver: ['dashboard:view', 'epis:view', 'units:view', 'stock:view', 'purchase_requests:view', 'purchase_orders:view', 'purchase_orders:approve', 'finance:view'],
  // `epi_manager` é apelido de `user` (ROLE_ALIASES em core/roles.py) — o
  // mesmo papel Gestor de EPI, que também triagem/revê tecnicamente o EPI em
  // teste e faz a revisão HSEQ do feedback. Ganha employees:create_simplified/
  // update_simplified pelo mesmo motivo do Administrador Local acima.
  // Achado em verificação de navegador real (ADR-0002 §12): este array
  // incluía 'employees:update' (completo) por engano — o comentário acima
  // já dizia que o Gestor de EPI ganha só as variantes _simplified, pelo
  // mesmo motivo do Administrador Local; o backend (core/permissions.py,
  // PERMISSIONS['user']) nunca concedeu employees:update completo. Mais
  // que cosmético: com o array errado, hasPermission('employees:update')
  // isolado (não numa lista OR) mentia "sim" no cliente para o Gestor de
  // EPI — a rota protegida no backend sempre rejeitava (403), mas o
  // cliente tentava a chamada e chegava a oferecer UI para uma ação sem
  // efeito, como a aba "Solicitações" de Terceirizados (ADR-0002 §12.5).
  user: ['dashboard:view', 'deliveries:view', 'deliveries:create', 'fichas:view', 'alerts:view', 'units:view', 'employees:view', 'employees:create_simplified', 'employees:update_simplified', 'epis:view', 'stock:view', 'stock:adjust', 'epi_feedback:view', 'epi_feedback:triage', 'epi_feedback:create', 'epi_feedback:hseq_review', 'epi_feedback:manager_eval', 'epi_evaluation:view', 'ppe_test:view', 'ppe_test:suggest', 'ppe_test:manage', 'ppe_test:evaluate', 'ppe_test:triage', 'ppe_test:tech_review'],
  employee: []
};
const VIEW_PERMISSIONS = {
  dashboard: 'dashboard:view',
  empresas: 'companies:view',
  comercial: 'commercial:view',
  usuarios: 'users:view',
  unidades: 'units:view',
  cnpjs: 'legal_entities:view',
  colaboradores: 'employees:view',
  // Reaproveita o mesmo piso técnico de criar colaborador (ADR-0002) — sem
  // permissão dedicada, por decisão explícita do ADR.
  terceirizados: 'employees:create',
  // Só transferência entre unidades (form + tabela somente-leitura) — nunca
  // teve edição de dados cadastrais, então a permissão certa sempre foi a de
  // movimentação, não a de update genérico.
  'gestao-colaborador': 'employees:transfer',
  epis: 'epis:view',
  estoque: 'stock:view',
  entregas: 'deliveries:view',
  fichas: 'fichas:view',
  compras: 'purchase_requests:view',
  configuracao: 'settings:view',
  relatorios: 'reports:view',
  avaliacoes: 'epi_evaluation:view',
  // Centro de Migração de Dados (ADR-0003). Permissão exclusiva de
  // master_admin/general_admin — nunca Administrador Local, Gestores ou
  // Colaboradores, que não a têm em core/permissions.py.
  migracao: 'data_migration:manage'
};
// Mapa view → módulo estrutural (espelha `MODULE_REQUIRED_PERMISSIONS`/
// `routeModules` do backend e do Flutter). Só as views cobertas pela
// personalização do Administrador Geral (Configuração → Regras →
// Visualização) entram aqui; as demais seguem só a permissão técnica acima,
// sem mudança de comportamento.
const VIEW_MODULE = {
  dashboard: 'dashboard',
  empresas: 'administracao',
  usuarios: 'administracao',
  cnpjs: 'administracao',
  // Módulo opt-in próprio (ADR-0002): diferente de `cnpjs` acima, nasce
  // OCULTO para todo papel — mesmo quem tem a permissão técnica — até o
  // Administrador Geral ligá-lo explicitamente por tenant.
  terceirizados: 'terceirizados',
  estoque: 'estoque',
  entregas: 'entregas',
  fichas: 'fichas',
  compras: 'compras',
  configuracao: 'configuracoes',
  relatorios: 'relatorios',
  // Opt-in como `terceirizados`: mesmo o Administrador Geral só vê depois de
  // ligar em Configuração → Regras → Visualização (_OPT_IN_MODULES no
  // rule_engine.py).
  migracao: 'migracao'
};
// Rótulos dos módulos configuráveis na aba Visualização — mesmas chaves de
// `VIEW_MODULE` acima e de `MODULE_KEYS` em epi_backend/rule_engine.py.
const MODULE_VISIBILITY_LABELS = {
  dashboard: 'Dashboard',
  compras: 'Compras',
  estoque: 'Estoque',
  entregas: 'Entregas',
  solicitacoes: 'Solicitações',
  fichas: 'Fichas de EPI',
  relatorios: 'Relatórios',
  administracao: 'Administração',
  configuracoes: 'Configurações',
  terceirizados: 'Terceirizados e Prestadores',
  migracao: 'Migração de Dados',
  // Módulo opt-in irmão (ADR-0002 §10.3): Cadastro de Colaboradores
  // simplificado dentro da mesma tela de Terceirizados e Prestadores —
  // liga/desliga independente do módulo acima (admin/user só têm a
  // permissão técnica deste, nunca do de Empresas).
  terceirizados_colaboradores: 'Cadastro de Colaboradores'
};
// Espelha _UNIT_SCOPED_ROLES de epi_backend/rule_engine.py: só admin
// (Administrador Local) e user (Gestor de EPI) têm vínculo de unidade
// única, então só eles fazem sentido com override por Unidade. É só
// controle de exibição do seletor — o backend valida de novo e é quem
// decide de fato (save_module_visibility rejeita unit_id para qualquer
// outro perfil).
const MODULE_VISIBILITY_UNIT_SCOPED_ROLES = ['admin', 'user'];
// Módulo alternativo que também libera a view (correção do ADR-0002 §10.3):
// Terceirizados e Prestadores tem duas abas com módulos opt-in distintos —
// qualquer um dos dois ligado libera a view; a aba em si ainda respeita seu
// próprio módulo/permissão (ver syncViewTabsVisibility e o formulário de
// Cadastro de Colaboradores, escondido quando terceirizados_colaboradores
// está desligado).
const VIEW_MODULE_ALTERNATIVES = {
  terceirizados: 'terceirizados_colaboradores'
};
// Permissão alternativa que também libera a view — mesma ideia acima, para o
// piso técnico: admin/user só têm employees:create_simplified, nunca
// employees:create.
const VIEW_PERMISSION_ALTERNATIVES = {
  terceirizados: 'employees:create_simplified'
};
const VIEW_EYEBROW = {
  dashboard: 'Visão Geral',
  empresas: 'Administração',
  comercial: 'Administração',
  usuarios: 'Administração',
  unidades: 'Cadastro',
  cnpjs: 'Cadastro',
  colaboradores: 'Cadastro',
  terceirizados: 'Cadastro',
  'gestao-colaborador': 'Operação',
  epis: 'Cadastro',
  estoque: 'Operação',
  entregas: 'Operação',
  fichas: 'Operação',
  compras: 'Compras',
  configuracao: 'Configuração',
  relatorios: 'Relatórios',
  avaliacoes: 'Avaliações',
  migracao: 'Administração'
};
const CONFIGURATION_ADMIN_ROLES = Object.freeze(['master_admin', 'general_admin', 'registry_admin']);
const DEFAULT_CONFIGURATION_FRAMEWORK = Object.freeze({
  version: 1,
  feature_flags: {
    enable_new_rules_engine: false,
    execution_mode: 'off',
    allow_new_engine_response: false,
    enabled_profiles: [],
    enabled_user_ids: [],
    enabled_company_ids: [],
    enabled_endpoints: [],
    enabled_environments: [],
    rollout_percentage: 0
  },
  hierarchy: {
    role_priority: ['master_admin', 'general_admin', 'registry_admin', 'admin', 'user', 'employee'],
    who_can_view_what: {}
  },
  visibility_rules: [],
  report_scopes: {
    stock_by_unit: { enabled: true, enforce_unit_scope: true, enforce_visibility_rules: false, allowed_profiles: ['master_admin', 'general_admin', 'registry_admin', 'admin', 'user'] },
    delivery_by_employee: { enabled: true, enforce_unit_scope: true, enforce_visibility_rules: false, allowed_profiles: ['master_admin', 'general_admin', 'registry_admin', 'admin', 'user'] },
    movement: { enabled: true, enforce_unit_scope: true, enforce_visibility_rules: false, allowed_profiles: ['master_admin', 'general_admin', 'registry_admin', 'admin', 'user'] },
    epi_ficha: { enabled: true, enforce_unit_scope: true, enforce_visibility_rules: false, allowed_profiles: ['master_admin', 'general_admin', 'registry_admin', 'admin', 'user'] },
    alerts: { enabled: true, enforce_unit_scope: true, enforce_visibility_rules: false, allowed_profiles: ['master_admin', 'general_admin', 'registry_admin', 'admin', 'user'] }
  },
  observability: { audit_decisions: false, debug_visibility: false }
});
const ROLE_ALIASES = {
  master_admin: 'master_admin',
  masteradmin: 'master_admin',
  general_admin: 'general_admin',
  generaladmin: 'general_admin',
  registry_admin: 'registry_admin',
  registryadmin: 'registry_admin',
  admin: 'admin',
  buyer: 'buyer',
  comprador: 'buyer',
  approver: 'approver',
  aprovador: 'approver',
  user: 'user',
  employee: 'employee'
};

const DEFAULT_COMPANY_LOGO = `data:image/svg+xml;utf8,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80"><rect width="80" height="80" rx="20" fill="#f6d8c8"/><path d="M20 56h40M26 48V26h28v22" fill="none" stroke="#96401c" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/></svg>')}`;
const DEFAULT_PLATFORM_BRAND = { display_name: 'Sua Empresa', legal_name: '', cnpj: '', logo_type: '', login_logo_type: '' };
const DEFAULT_COMMERCIAL_SETTINGS = {
  unit_price: 42,
  plans: {
    individual: { label: 'Individual', min_users: 1, max_users: 1 },
    start: { label: 'Start', min_users: 1, max_users: 10 },
    business: { label: 'Business', min_users: 11, max_users: 25 },
    corporate: { label: 'Corporate', min_users: 26, max_users: 100 },
    enterprise: { label: 'Enterprise', min_users: 101, max_users: null }
  }
};
const EPI_ALL_UNITS_VALUE = '__ALL_UNITS__';
const EPI_COMPANY_LEVEL_FILTER_VALUE = '__COMPANY_LEVEL_ALL_UNITS__';
const EPI_ALL_UNITS_PROFILES = Object.freeze(['general_admin', 'registry_admin']);
const UX_FRONTEND_FLAGS = Object.freeze({
  collaboratorHtmxEnabled: 'colaborador_htmx_enabled',
  collaboratorHtmxEnabledLegacy: 'ux_phase2_nav_interactivity_v1',
  collaboratorListHtmxEnabled: 'colaborador_list_htmx_enabled',
  gestaoColaboradorHtmxEnabled: 'gestao_colaborador_htmx_enabled',
  phase2NavInteractivity: 'ux_phase2_nav_interactivity_v1',
  epiHtmxEnabled: 'epi_htmx_enabled',
  estoqueHtmxEnabled: 'estoque_htmx_enabled',
  entregaEpiHtmxEnabled: 'entrega_epi_htmx_enabled',
  dashboardInterativoEnabled: 'dashboard_interativo_enabled',
  spaNavigationEnabled: 'spa_navigation_enabled',
  uxGlobalEnabled: 'ux_global_enabled',
  uxPerformanceHardeningEnabled: 'ux_performance_hardening_enabled',
  uxInteractiveAppEnabled: 'ux_interactive_app_enabled',
  uxToolsFunctionalEnabled: 'ux_tools_functional_enabled',
  uxPhase41Enabled: 'ux_phase41_enabled',
  uxPhase42Enabled: 'ux_phase42_enabled',
  uxPhase43Enabled: 'ux_phase43_enabled',
  uxPhase44Enabled: 'ux_phase44_enabled',
  uxHierarchicalNavigationEnabled: 'ux_hierarchical_navigation_enabled',
  uxMultitabNavigationEnabled: 'ux_multitab_navigation_enabled',
  uxAnalyticsEnabled: 'ux_analytics_enabled',
  uxMobileEnabled: 'ux_mobile_enabled',
  uxNavigationControlsEnabled: 'ux_navigation_controls_enabled',
  htmxAlpineProductionEnabled: 'htmx_alpine_production_enabled',
  uxGlobalKillSwitch: 'ux_global_kill_switch'
});
const UX_FORCE_CLASSIC_FLAGS = Object.freeze(new Set([
  'ux_phase41_enabled',
  'ux_phase42_enabled',
  'ux_phase43_enabled',
  'ux_phase44_enabled',
  'ux_hierarchical_navigation_enabled',
  'ux_multitab_navigation_enabled',
  'spa_navigation_enabled',
  'ux_global_enabled',
  'dashboard_interativo_enabled',
  'entrega_epi_htmx_enabled'
]));
const FEATURE_FLAG_DEFINITIONS = Object.freeze({
  colaborador_htmx_enabled: { queryParam: 'ux_phase2_colaboradores', storageKeys: [UX_FRONTEND_FLAGS.collaboratorHtmxEnabled, UX_FRONTEND_FLAGS.collaboratorHtmxEnabledLegacy] },
  colaborador_list_htmx_enabled: { queryParam: 'ux_phase2_colab_list', storageKeys: [UX_FRONTEND_FLAGS.collaboratorListHtmxEnabled] },
  gestao_colaborador_htmx_enabled: { queryParam: 'ux_phase2_gestao_colab', storageKeys: [UX_FRONTEND_FLAGS.gestaoColaboradorHtmxEnabled] },
  epi_htmx_enabled: { queryParam: 'ux_phase2_epis', storageKeys: [UX_FRONTEND_FLAGS.epiHtmxEnabled] },
  estoque_htmx_enabled: { queryParam: 'ux_phase2_estoque', storageKeys: [UX_FRONTEND_FLAGS.estoqueHtmxEnabled] },
  entrega_epi_htmx_enabled: { queryParam: 'ux_entrega_epi', storageKeys: [UX_FRONTEND_FLAGS.entregaEpiHtmxEnabled] },
  dashboard_interativo_enabled: { queryParam: 'ux_dashboard_interativo', storageKeys: [UX_FRONTEND_FLAGS.dashboardInterativoEnabled] },
  spa_navigation_enabled: { queryParam: 'ux_spa_navigation', storageKeys: [UX_FRONTEND_FLAGS.spaNavigationEnabled] },
  ux_global_enabled: { queryParam: 'ux_global', storageKeys: [UX_FRONTEND_FLAGS.uxGlobalEnabled] },
  ux_performance_hardening_enabled: { queryParam: 'ux_perf_hardening', storageKeys: [UX_FRONTEND_FLAGS.uxPerformanceHardeningEnabled] },
  ux_interactive_app_enabled: { queryParam: 'ux_interactive_app', storageKeys: [UX_FRONTEND_FLAGS.uxInteractiveAppEnabled] },
  ux_tools_functional_enabled: { queryParam: 'ux_tools_functional', storageKeys: [UX_FRONTEND_FLAGS.uxToolsFunctionalEnabled] },
  ux_phase41_enabled: { queryParam: 'ux_phase41', storageKeys: [UX_FRONTEND_FLAGS.uxPhase41Enabled] },
  ux_phase42_enabled: { queryParam: 'ux_phase42', storageKeys: [UX_FRONTEND_FLAGS.uxPhase42Enabled] },
  ux_phase43_enabled: { queryParam: 'ux_phase43', storageKeys: [UX_FRONTEND_FLAGS.uxPhase43Enabled] },
  ux_phase44_enabled: { queryParam: 'ux_phase44', storageKeys: [UX_FRONTEND_FLAGS.uxPhase44Enabled] },
  ux_hierarchical_navigation_enabled: { queryParam: 'ux_hierarchy', storageKeys: [UX_FRONTEND_FLAGS.uxHierarchicalNavigationEnabled] },
  ux_multitab_navigation_enabled: { queryParam: 'ux_multitab', storageKeys: [UX_FRONTEND_FLAGS.uxMultitabNavigationEnabled] },
  ux_analytics_enabled: { queryParam: 'ux_analytics', storageKeys: [UX_FRONTEND_FLAGS.uxAnalyticsEnabled] },
  ux_mobile_enabled: { queryParam: 'ux_mobile', storageKeys: [UX_FRONTEND_FLAGS.uxMobileEnabled] },
  ux_navigation_controls_enabled: { queryParam: 'ux_nav_controls', storageKeys: [UX_FRONTEND_FLAGS.uxNavigationControlsEnabled] },
  htmx_alpine_production_enabled: { queryParam: 'ux_htmx_prod', storageKeys: [UX_FRONTEND_FLAGS.htmxAlpineProductionEnabled] },
  ux_global_kill_switch: { queryParam: 'ux_kill_switch', storageKeys: [UX_FRONTEND_FLAGS.uxGlobalKillSwitch] }
});

if (!globalThis.__EPI_PHASE42_SCRIPT_REQUESTED__) {
  globalThis.__EPI_PHASE42_SCRIPT_REQUESTED__ = true;
  try {
    const phase42Script = document.createElement('script');
    phase42Script.defer = true;
    phase42Script.src = '/ux-phase42.js?v=20260424-50';
    document.head.appendChild(phase42Script);
  } catch (error) {
    reportNonCriticalError('phase42 script bootstrap failed', error);
  }
}
if (!globalThis.__EPI_PHASE43_SCRIPT_REQUESTED__) {
  globalThis.__EPI_PHASE43_SCRIPT_REQUESTED__ = true;
  try {
    const phase43Script = document.createElement('script');
    phase43Script.defer = true;
    phase43Script.src = '/ux-phase43.js?v=20260424-50';
    document.head.appendChild(phase43Script);
  } catch (error) {
    reportNonCriticalError('phase43 script bootstrap failed', error);
  }
}
if (!globalThis.__EPI_PHASE44_SCRIPT_REQUESTED__) {
  globalThis.__EPI_PHASE44_SCRIPT_REQUESTED__ = true;
  try {
    const phase44Script = document.createElement('script');
    phase44Script.defer = true;
    phase44Script.src = '/ux-phase44.js?v=20260424-50';
    document.head.appendChild(phase44Script);
  } catch (error) {
    reportNonCriticalError('phase44 script bootstrap failed', error);
  }
}
const PHASE2_STORAGE_ROLLOUT_KEY = 'epi_phase2_rollout_storage_enabled';
const PHASE2_FLAG_MATRIX = Object.freeze([
  { flag: 'colaborador_htmx_enabled', queryParam: 'ux_phase2_colaboradores', moduleName: 'Cadastro de Colaborador', defaultValue: false, status: 'pilot_stable' },
  { flag: 'colaborador_list_htmx_enabled', queryParam: 'ux_phase2_colab_list', moduleName: 'Listagem de Colaboradores', defaultValue: false, status: 'pilot_stable' },
  { flag: 'gestao_colaborador_htmx_enabled', queryParam: 'ux_phase2_gestao_colab', moduleName: 'Gestão de Colaborador', defaultValue: false, status: 'pilot_stable' },
  { flag: 'epi_htmx_enabled', queryParam: 'ux_phase2_epis', moduleName: 'Cadastro de EPI', defaultValue: false, status: 'pilot_stable' },
  { flag: 'estoque_htmx_enabled', queryParam: 'ux_phase2_estoque', moduleName: 'Controle de Estoque (read-only + filtros)', defaultValue: false, status: 'pilot_controlled' }
]);
const PHASE3_FLAG_MATRIX = Object.freeze([
  {
    flag: 'spa_navigation_enabled',
    queryParam: 'ux_spa_navigation',
    moduleName: 'Navegação SPA-like',
    defaultValue: false,
    risk: 'Médio: risco de regressão de navegação/back-forward.',
    rollback: 'Desativar flag + limpar storage da sessão controlada.'
  },
  {
    flag: 'ux_global_enabled',
    queryParam: 'ux_global',
    moduleName: 'UX global unificada',
    defaultValue: false,
    risk: 'Baixo/Médio: risco visual em telas com maior densidade de cards/tabelas.',
    rollback: 'Desativar flag para retorno imediato ao layout clássico.'
  },
  {
    flag: 'dashboard_interativo_enabled',
    queryParam: 'ux_dashboard_interativo',
    moduleName: 'Dashboard interativo',
    defaultValue: false,
    risk: 'Médio: risco de fallback parcial em estados de carga/erro.',
    rollback: 'Desativar flag e manter dashboard clássico ativo.'
  },
  {
    flag: 'ux_performance_hardening_enabled',
    queryParam: 'ux_perf_hardening',
    moduleName: 'Hardening de listeners/eventos',
    defaultValue: false,
    risk: 'Baixo: impacto controlado no binding de eventos.',
    rollback: 'Desativar flag e restaurar comportamento padrão de listeners.'
  },
  {
    flag: 'ux_interactive_app_enabled',
    queryParam: 'ux_interactive_app',
    moduleName: 'Comportamento interativo avançado',
    defaultValue: false,
    risk: 'Baixo/Médio: eventos globais de teclado/dropdown e histórico de navegação.',
    rollback: 'Desativar flag para voltar ao comportamento padrão imediatamente.'
  },
  {
    flag: 'ux_tools_functional_enabled',
    queryParam: 'ux_tools_functional',
    moduleName: 'Ferramentas UX funcionais',
    defaultValue: false,
    risk: 'Médio: refresh/filtros com feedback real em módulos de operação.',
    rollback: 'Desativar flag para restaurar somente o fluxo clássico.'
  }
]);

function isDebugModeEnabled() {
  return globalThis.__EPI_DEBUG__ === true;
}

function debugLog(context, payload) {
  if (!isDebugModeEnabled()) return;
  if (payload === undefined) {
    console.debug(`[debug] ${context}`);
    return;
  }
  console.debug(`[debug] ${context}`, payload);
}

function reportNonCriticalError(context, error) {
  if (!error) return;
  if (!isDebugModeEnabled()) return;
  console.debug(`[non-critical] ${context}`, error);
}

const EPI_PERF_RUNTIME = {
  debugEnabled: false,
  listenerCount: 0,
  analyticsCount: 0,
  activeTabs: 0,
  render: { lastMs: 0, samples: [] },
  activeRequests: new Map(),
  storageTimers: new Map(),
  storagePending: new Map(),
  hud: null
};

function isUxPerfDebugEnabled() {
  if (EPI_PERF_RUNTIME.debugEnabled) return true;
  try {
    const params = new URLSearchParams(globalThis.location.search || '');
    const byQuery = params.get('ux_perf_debug') === '1';
    let role = String(globalThis.__EPI_APP_STATE__?.user?.role || '');
    if (!role) {
      const rawSession = safeStorageRead(STORAGE_KEYS.session, '{}');
      const parsedSession = safeJsonParse(rawSession, {});
      role = String(parsedSession?.role || '');
    }
    const isMasterAdmin = role === 'master_admin';
    EPI_PERF_RUNTIME.debugEnabled = byQuery && isMasterAdmin;
    return EPI_PERF_RUNTIME.debugEnabled;
  } catch (_error) {
    return false;
  }
}

function renderPerfHud() {
  if (!isUxPerfDebugEnabled()) return;
  try {
    let hud = EPI_PERF_RUNTIME.hud;
    if (!hud) {
      hud = document.createElement('aside');
      hud.id = 'epi-perf-debug';
      hud.className = 'epi-perf-debug';
      document.body.appendChild(hud);
      EPI_PERF_RUNTIME.hud = hud;
    }
    hud.innerHTML = [
      '<strong>UX Perf Debug</strong>',
      `<span>render: ${Math.round(EPI_PERF_RUNTIME.render.lastMs || 0)}ms</span>`,
      `<span>listeners: ${EPI_PERF_RUNTIME.listenerCount}</span>`,
      `<span>analytics: ${EPI_PERF_RUNTIME.analyticsCount}</span>`,
      `<span>tabs: ${EPI_PERF_RUNTIME.activeTabs}</span>`
    ].join('');
  } catch (error) {
    console.warn('[perf] render HUD indisponível', error);
  }
}

function ensureModuleBound(moduleKey) {
  const key = `__EPI_${String(moduleKey || 'MODULE').toUpperCase().replace(/[^A-Z0-9]+/g, '_')}_BOUND__`;
  if (globalThis[key]) {
    debugLog(`[perf] duplicate bind blocked: ${moduleKey}`);
    return false;
  }
  globalThis[key] = true;
  return true;
}

function markRenderStart() {
  return globalThis.performance && typeof globalThis.performance.now === 'function'
    ? globalThis.performance.now()
    : Date.now();
}

function markRenderEnd(startTs) {
  const endTs = globalThis.performance && typeof globalThis.performance.now === 'function'
    ? globalThis.performance.now()
    : Date.now();
  const elapsed = Math.max(0, endTs - Number(startTs || endTs));
  EPI_PERF_RUNTIME.render.lastMs = elapsed;
  EPI_PERF_RUNTIME.render.samples.push(elapsed);
  EPI_PERF_RUNTIME.render.samples = EPI_PERF_RUNTIME.render.samples.slice(-60);
  renderPerfHud();
}

function trackAnalyticsEvent() {
  EPI_PERF_RUNTIME.analyticsCount = Math.min(10000, EPI_PERF_RUNTIME.analyticsCount + 1);
  renderPerfHud();
}

function setActiveTabsCount(count) {
  EPI_PERF_RUNTIME.activeTabs = Math.max(0, Number(count || 0));
  renderPerfHud();
}

function queueStorageWrite(key, value, options = {}) {
  const wait = Math.max(80, Number(options.wait || 180));
  const maxBytes = Number(options.maxBytes || 50000);
  const payload = String(value ?? '');
  EPI_PERF_RUNTIME.storagePending.set(key, { payload, maxBytes });
  const previous = EPI_PERF_RUNTIME.storageTimers.get(key);
  if (previous) globalThis.clearTimeout(previous);
  const timer = globalThis.setTimeout(() => {
    EPI_PERF_RUNTIME.storageTimers.delete(key);
    const pending = EPI_PERF_RUNTIME.storagePending.get(key);
    EPI_PERF_RUNTIME.storagePending.delete(key);
    if (!pending) return;
    try {
      if (pending.payload.length > pending.maxBytes) return;
      safeStorageWrite(key, pending.payload);
    } catch (error) {
      reportNonCriticalError(`[perf] storage write failed for ${key}`, error);
    }
  }, wait);
  EPI_PERF_RUNTIME.storageTimers.set(key, timer);
}

function flushPendingStorageWrites() {
  if (!EPI_PERF_RUNTIME.storagePending.size) return;
  EPI_PERF_RUNTIME.storagePending.forEach((pending, key) => {
    try {
      if (!pending || typeof pending.payload !== 'string') return;
      if (pending.payload.length > Number(pending.maxBytes || 50000)) return;
      safeStorageWrite(key, pending.payload);
    } catch (error) {
      reportNonCriticalError(`[perf] storage flush failed for ${key}`, error);
    }
  });
  EPI_PERF_RUNTIME.storagePending.clear();
}

function createScopedAbortController(scopeKey) {
  const key = `__EPI_${String(scopeKey || 'SCOPE').toUpperCase().replace(/[^A-Z0-9]+/g, '_')}_ABORT__`;
  try {
    const previous = globalThis[key];
    if (previous && typeof previous.abort === 'function') previous.abort();
  } catch (error) {
    reportNonCriticalError(`[perf] abort controller cleanup failed for ${scopeKey}`, error);
  }
  const controller = new AbortController();
  globalThis[key] = controller;
  return controller;
}

function registerAbortableRequest(requestKey) {
  const key = String(requestKey || '');
  if (!key) return new AbortController();
  const previous = EPI_PERF_RUNTIME.activeRequests.get(key);
  if (previous && typeof previous.abort === 'function') previous.abort();
  const controller = new AbortController();
  EPI_PERF_RUNTIME.activeRequests.set(key, controller);
  controller.signal.addEventListener('abort', () => {
    if (EPI_PERF_RUNTIME.activeRequests.get(key) === controller) {
      EPI_PERF_RUNTIME.activeRequests.delete(key);
    }
  }, { once: true });
  return controller;
}

const SAFE_ON_REGISTRY = new WeakMap();

function resolveListenerOptionSignature(options) {
  if (typeof options === 'boolean') return options ? 'capture:1' : 'capture:0';
  if (!options || typeof options !== 'object') return 'capture:0';
  return options.capture ? 'capture:1' : 'capture:0';
}

function safeOn(target, eventName, handler, options) {
  if (!target || typeof target.addEventListener !== 'function' || typeof handler !== 'function') return false;
  try {
    if (isUxPerformanceHardeningEnabled()) {
      const eventMap = SAFE_ON_REGISTRY.get(target) || new Map();
      const key = `${eventName}:${resolveListenerOptionSignature(options)}`;
      const handlers = eventMap.get(key) || new WeakSet();
      if (handlers.has(handler)) {
        debugLog(`[safeOn] duplicate listener blocked: ${eventName}`);
        return false;
      }
      handlers.add(handler);
      eventMap.set(key, handlers);
      SAFE_ON_REGISTRY.set(target, eventMap);
    }
    target.addEventListener(eventName, handler, options);
    EPI_PERF_RUNTIME.listenerCount += 1;
    if (options && typeof options === 'object' && options.signal && typeof options.signal.addEventListener === 'function') {
      options.signal.addEventListener('abort', () => {
        EPI_PERF_RUNTIME.listenerCount = Math.max(0, EPI_PERF_RUNTIME.listenerCount - 1);
        renderPerfHud();
      }, { once: true });
    }
    renderPerfHud();
    return true;
  } catch (error) {
    reportNonCriticalError(`[safeOn] falha ao registrar listener ${eventName}`, error);
    return false;
  }
}

function isViewActive(viewSelector) {
  if (!viewSelector) return false;
  const viewElement = document.querySelector(viewSelector);
  if (!viewElement) return false;
  return viewElement.classList.contains('active');
}

function resolveFormFieldAutocomplete(field) {
  if (!field || typeof field.getAttribute !== 'function') return null;
  const tag = String(field.tagName || '').toLowerCase();
  if (tag === 'select' || tag === 'textarea') return 'off';
  const type = String(field.getAttribute('type') || 'text').toLowerCase();
  if (['hidden', 'checkbox', 'radio', 'file', 'button', 'submit', 'reset', 'range', 'color'].includes(type)) return null;
  if (type === 'password') {
    const marker = String(field.id || field.name || '').toLowerCase();
    if (marker.includes('new') || marker.includes('confirm') || marker.includes('recovery')) return 'new-password';
    return 'current-password';
  }
  const marker = String((field.id || '') + ' ' + (field.name || '')).toLowerCase();
  if (marker.includes('user') || marker.includes('login')) return 'username';
  if (marker.includes('email')) return 'email';
  if (marker.includes('phone') || marker.includes('whatsapp') || marker.includes('tel')) return 'tel';
  if (marker === 'name' || marker.endsWith(' name') || marker.includes('-name') || marker.includes('_name')) return 'name';
  if (type === 'search' || type === 'date' || type === 'number') return 'off';
  return 'off';
}


function describeFieldNode(node) {
  if (!node || !(node instanceof HTMLElement)) return null;
  const nearestForm = node.closest('form');
  const id = getElementIdAttribute(node);
  const classSuffix = String(node.className || '').trim().split(/\s+/).filter(Boolean).slice(0, 2).join('.');
  const selector = `${String(node.tagName || '').toLowerCase()}${id ? `#${id}` : ''}${classSuffix ? `.${classSuffix}` : ''}`;
  return {
    id,
    rawDomIdProperty: String(node.id || ''),
    tagName: String(node.tagName || '').toLowerCase(),
    name: String(node.getAttribute('name') || ''),
    type: String(node.getAttribute('type') || ''),
    placeholder: String(node.getAttribute('placeholder') || ''),
    nearestFormId: getElementIdAttribute(nearestForm),
    formId: getElementIdAttribute(nearestForm),
    nearestFormId: String((nearestForm && nearestForm.id) || ''),
    formId: String((nearestForm && nearestForm.id) || ''),
    outerHTML: String(node.outerHTML || '').replace(/\s+/g, ' ').trim().slice(0, 220),
    selector
  };
}

function getElementIdAttribute(node) {
  if (!node || typeof node.getAttribute !== 'function') return '';
  return String(node.getAttribute('id') || '').trim();
}

function isValidDomId(value) {
  if (typeof value !== 'string') return false;
  const normalized = value.trim();
  if (!normalized) return false;
  if (normalized.includes('[object')) return false;
  if (/[<>"']/.test(normalized)) return false;
  if (/^(undefined|null|nan)$/i.test(normalized)) return false;
  return true;
}

function toSafeId(value, fallback) {
  const raw = typeof value === 'string' ? value : '';
  const base = raw.trim() || String(fallback || 'form');
  const sanitized = String(base)
    .replace(/[^a-zA-Z0-9_-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .toLowerCase();
  return sanitized || String(fallback || 'form');
}

function setElementIdAttribute(node, value, contextLabel = 'unknown') {
  if (!node || typeof node.setAttribute !== 'function') return false;
  if (value instanceof HTMLElement) {
    console.warn('[forms] tentativa de usar elemento como ID ignorada', { contextLabel });
    return false;
  }
  if (typeof value !== 'string') {
    console.warn('[forms] id inválido ignorado', { contextLabel });
    return false;
  }
  const normalized = String(value || '').trim();
  if (!isValidDomId(normalized)) return false;
  node.setAttribute('id', normalized);
  return true;
}

function normalizeInvalidDomIds(root = document) {
  if (!root || typeof root.querySelectorAll !== 'function') return [];
  const isObjectLikeId = (value) => /^\[object\s+[^\]]+\]$/i.test(String(value || '').trim());
  const allNodes = Array.from(document.querySelectorAll('[id]'));
  const idCounts = new Map();
  allNodes.forEach((node) => {
    const id = getElementIdAttribute(node);
    if (!id) return;
    idCounts.set(id, (idCounts.get(id) || 0) + 1);
  });
  const toNormalize = allNodes.filter((node) => {
    const id = getElementIdAttribute(node);
    return Boolean(id) && (isObjectLikeId(id) || (idCounts.get(id) || 0) > 1);
  });
  const updates = [];
  toNormalize.forEach((node, index) => {
    const previousId = getElementIdAttribute(node);
    if (!previousId) return;
    const tagName = String(node.tagName || 'node').toLowerCase();
    const nearestForm = node.closest('form');
    const basePrefix = nearestForm ? `${nearestForm.id || 'epi-form'}-${tagName}` : `epi-${tagName}`;
    let candidateId = `${basePrefix}-normalized-${index + 1}`.replace(/[^a-zA-Z0-9_-]+/g, '-');
    let seq = 1;
    while (candidateId && document.getElementById(candidateId) && document.getElementById(candidateId) !== node) {
      seq += 1;
      candidateId = `${basePrefix}-normalized-${index + 1}-${seq}`.replace(/[^a-zA-Z0-9_-]+/g, '-');
    }
    if (!candidateId) return;
    setElementIdAttribute(node, candidateId, 'normalizeInvalidDomIds');
    Array.from(document.querySelectorAll(`label[for="${CSS.escape(previousId)}"]`)).forEach((label) => {
      label.setAttribute('for', candidateId);
    });
    updates.push({ previousId, newId: candidateId, node: describeFieldNode(node) });
  });
  return updates;
}

function ensureFormFieldAttributes(root = document) {
  if (!root || typeof root.querySelectorAll !== 'function') return;
  if (!globalThis.__EPI_FORM_FIELD_ID_SEQ__) globalThis.__EPI_FORM_FIELD_ID_SEQ__ = 0;

  const isObjectLikeId = (value) => /^\[object\s+[^\]]+\]$/i.test(String(value || '').trim());
  const hasDuplicateId = (value, exceptNode = null) => {
    const normalized = String(value || '').trim();
    if (!normalized) return false;
    const nodes = Array.from(document.querySelectorAll(`[id="${CSS.escape(normalized)}"]`));
    if (!exceptNode) return nodes.length > 1;
    return nodes.some((node) => node !== exceptNode);
  };
  const buildSafeFieldId = (baseId) => {
    let candidateId = String(baseId || '').trim() || `epi-field-${Date.now()}`;
    while (document.getElementById(candidateId)) {
      globalThis.__EPI_FORM_FIELD_ID_SEQ__ += 1;
      candidateId = `${String(baseId || 'epi-field').trim() || 'epi-field'}-${globalThis.__EPI_FORM_FIELD_ID_SEQ__}`;
    }
    return candidateId;
  };
  const buildStableFieldId = (formId, field, fieldIndex) => {
    const safeFormId = isValidDomId(formId) ? formId : `form-${fieldIndex + 1}`;
    const rawName = String(field?.getAttribute?.('name') || getElementIdAttribute(field) || field?.getAttribute?.('type') || 'field');
    const normalizedName = rawName.toLowerCase().replace(/[^a-z0-9_-]+/g, '-').replace(/^-+|-+$/g, '') || 'field';
    return buildSafeFieldId(`${String(safeFormId || 'form').replace(/[^a-zA-Z0-9_-]+/g, '-')}-${normalizedName}-${fieldIndex + 1}`);
  };

  const forms = Array.from(root.querySelectorAll('form'));
  if (root instanceof HTMLFormElement) forms.unshift(root);

  forms.forEach((form, formIndex) => {
    const currentFormId = getElementIdAttribute(form);
    let formId = currentFormId;

    if (!isValidDomId(formId) || isObjectLikeId(formId) || hasDuplicateId(formId, form)) {
      const fallback = `form-${formIndex + 1}`;
      const safeId = toSafeId(form.getAttribute('name'), fallback);
      formId = buildSafeFieldId(safeId);
      setElementIdAttribute(form, formId, 'ensureFormFieldAttributes:form');
    }

    const fields = Array.from(form.querySelectorAll('input, select, textarea'));
    fields.forEach((field, fieldIndex) => {
      const hasId = field.hasAttribute('id');
      const hasName = field.hasAttribute('name');
      const currentFieldId = getElementIdAttribute(field);
      const shouldNormalizeInvalidId = hasId && (!isValidDomId(currentFieldId) || isObjectLikeId(currentFieldId) || hasDuplicateId(currentFieldId, field));

      if (shouldNormalizeInvalidId || (!hasId && !hasName)) {
        const previousId = currentFieldId;
        const fallback = `${formId || 'form'}-${field.getAttribute('name') || field.getAttribute('type') || 'field'}-${fieldIndex + 1}`;
        let candidateId = toSafeId(currentFieldId, fallback);
        if (!isValidDomId(candidateId) || isObjectLikeId(candidateId) || hasDuplicateId(candidateId, field)) {
          candidateId = buildStableFieldId(formId, field, fieldIndex);
        }
        setElementIdAttribute(field, candidateId, 'ensureFormFieldAttributes:field');
        if (previousId && previousId !== candidateId) {
          Array.from(form.querySelectorAll(`label[for="${CSS.escape(previousId)}"]`)).forEach((label) => {
            if (!label.control || label.control === field) label.setAttribute('for', candidateId);
          });
        }
      }

      if ((field.hasAttribute('id') || field.hasAttribute('name')) && !field.hasAttribute('autocomplete')) {
        const autocompleteValue = resolveFormFieldAutocomplete(field);
        if (autocompleteValue) field.setAttribute('autocomplete', autocompleteValue);
      }
    });
  });
}

function auditFormFieldIssues(root = document) {
  if (!root || typeof root.querySelectorAll !== 'function') return { missingIdOrName: 0, missingAutocomplete: 0, duplicateIds: [], brokenLabels: [] };
  const scope = root.querySelectorAll ? root : document;
  const fields = Array.from(scope.querySelectorAll('form input, form select, form textarea'));
  const missingIdOrName = fields.filter((field) => !field.id && !field.name).length;
  const missingAutocomplete = fields.filter((field) => {
    if (!field.id && !field.name) return false;
    if (field.hasAttribute('autocomplete')) return false;
    return Boolean(resolveFormFieldAutocomplete(field));
  }).length;

  const idMap = new Map();
  Array.from(document.querySelectorAll('[id]')).forEach((node) => {
    const id = getElementIdAttribute(node);
    if (!id) return;
    if (!idMap.has(id)) {
      idMap.set(id, { count: 0, nodes: [] });
    }
    const entry = idMap.get(id);
    entry.count += 1;
    const tag = String(node.tagName || 'node').toLowerCase();
    const marker = node.className ? `${tag}#${id}.${String(node.className).trim().replace(/\s+/g, '.')}` : `${tag}#${id}`;
    if (entry.nodes.length < 4) entry.nodes.push(marker);
  });
  const duplicateIds = Array.from(idMap.entries())
    .filter(([, entry]) => entry.count > 1)
    .map(([id, entry]) => ({ id, count: entry.count, nodes: entry.nodes }));

  const brokenLabels = Array.from(document.querySelectorAll('label[for]')).filter((label) => {
    const targetId = String(label.getAttribute('for') || '').trim();
    if (!targetId) return false;
    return !document.getElementById(targetId);
  }).map((label) => label.getAttribute('for'));

  return { missingIdOrName, missingAutocomplete, duplicateIds, brokenLabels };
}

function setupFormFieldHardening() {
  if (globalThis.__EPI_FORM_FIELD_HARDENING_BOUND__) return;
  globalThis.__EPI_FORM_FIELD_HARDENING_BOUND__ = true;

  ensureFormFieldAttributes(document);
  const normalizedIdsOnBoot = normalizeInvalidDomIds(document);
  ensureFormFieldAttributes(document);
  if (normalizedIdsOnBoot.length && globalThis.__EPI_DEBUG_FORMS__) console.warn('[forms] normalized invalid ids on boot', normalizedIdsOnBoot);
  const observer = new MutationObserver((records) => {
    records.forEach((record) => {
      record.addedNodes.forEach((node) => {
        if (!(node instanceof HTMLElement)) return;
        if (node.matches('form, input, select, textarea')) {
          ensureFormFieldAttributes(node.closest('form') || node);
          normalizeInvalidDomIds(node.closest('form') || document);
          return;
        }
        if (node.querySelector) {
          ensureFormFieldAttributes(node);
          normalizeInvalidDomIds(node);
        }
      });
    });
  });
  observer.observe(document.body, { childList: true, subtree: true });
  globalThis.__EPI_FORM_FIELD_HARDENING_OBSERVER__ = observer;

  const audit = auditFormFieldIssues(document);
  globalThis.__EPI_FORM_FIELD_AUDIT__ = audit;
  if (audit.missingIdOrName || audit.missingAutocomplete || audit.duplicateIds.length || audit.brokenLabels.length) {
    const duplicateIdNames = audit.duplicateIds.map((entry) => `${entry.id} (${entry.count}x)`).join(', ');
    const duplicateNodes = audit.duplicateIds.flatMap((entry) => {
      const escapedId = CSS.escape(String(entry.id || ''));
      return Array.from(document.querySelectorAll(`[id="${escapedId}"]`)).map((node) => ({
        duplicateId: entry.id,
        ...describeFieldNode(node)
      }));
    });
    console.warn('[forms] pending accessibility issues', {
      ...audit,
      duplicateIdsSummary: duplicateIdNames || 'none',
      duplicateNodes
    });
  }
}

function deepClone(value) {
  return globalThis.structuredClone?.(value) ?? JSON.parse(JSON.stringify(value));
}

function cloneDefaultCommercialSettings() {
  return deepClone(DEFAULT_COMMERCIAL_SETTINGS);
}

function safeStorageRead(key, fallback = 'null') {
  try {
    return localStorage.getItem(key) ?? fallback;
  } catch (error) {
    reportNonCriticalError(`storage read failed for ${key}`, error);
    return fallback;
  }
}

function safeJsonParse(rawValue, fallbackValue) {
  try {
    return JSON.parse(rawValue);
  } catch (error) {
    reportNonCriticalError('json parse fallback used', error);
    return fallbackValue;
  }
}

function safeStorageWrite(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch (error) {
    reportNonCriticalError(`storage write failed for ${key}`, error);
  }
}

function esc(value) {
  return escapeHtml(value);
}

function safeStorageRemove(key) {
  try {
    localStorage.removeItem(key);
  } catch (error) {
    reportNonCriticalError(`storage remove failed for ${key}`, error);
  }
}

function parseFeatureFlagValue(value) {
  if (value === '1') return true;
  if (value === '0') return false;
  return null;
}

function readFeatureFlagFromSources(definition, options = {}) {
  if (!definition) return { value: null, source: 'default', storageKey: null };
  const allowStorage = options.allowStorage !== false;
  const params = new URLSearchParams(globalThis.location.search);
  const queryValue = parseFeatureFlagValue(params.get(definition.queryParam));
  if (queryValue !== null) {
    return { value: queryValue, source: 'querystring', storageKey: null };
  }
  if (allowStorage) {
    for (const storageKey of definition.storageKeys || []) {
      const storageValue = parseFeatureFlagValue(safeStorageRead(storageKey, '0'));
      if (storageValue !== null) {
        return { value: storageValue, source: 'localStorage', storageKey };
      }
    }
  }
  return { value: null, source: 'default', storageKey: null };
}

function isGlobalUxKillSwitchEnabled() {
  if (globalThis.__EPI_AUTO_ROLLBACK_ACTIVE__ === true) return true;
  const killSwitchDefinition = FEATURE_FLAG_DEFINITIONS.ux_global_kill_switch;
  const resolution = readFeatureFlagFromSources(killSwitchDefinition, { allowStorage: true });
  return resolution.value === true;
}

function getFeatureFlag(flagName, options = {}) {
  const definition = FEATURE_FLAG_DEFINITIONS[flagName];
  const defaultValue = Boolean(options.defaultValue ?? false);
  if (!definition) return defaultValue;
  if (flagName !== 'ux_global_kill_switch' && UX_FORCE_CLASSIC_FLAGS.has(flagName) && isGlobalUxKillSwitchEnabled()) {
    return false;
  }

  const resolution = readFeatureFlagFromSources(definition, options);
  if (resolution.value !== null) return resolution.value;
  return defaultValue;
}

function getFeatureFlagResolution(flagName, options = {}) {
  const definition = FEATURE_FLAG_DEFINITIONS[flagName];
  const defaultValue = Boolean(options.defaultValue ?? false);
  if (!definition) {
    return { value: defaultValue, source: 'default', queryParam: null, storageKey: null };
  }
  if (flagName !== 'ux_global_kill_switch' && UX_FORCE_CLASSIC_FLAGS.has(flagName) && isGlobalUxKillSwitchEnabled()) {
    return { value: false, source: 'kill_switch', queryParam: definition.queryParam, storageKey: null };
  }

  const resolution = readFeatureFlagFromSources(definition, options);
  if (resolution.value !== null) {
    return {
      value: resolution.value,
      source: resolution.source,
      queryParam: definition.queryParam,
      storageKey: resolution.storageKey
    };
  }

  return { value: defaultValue, source: 'default', queryParam: definition.queryParam, storageKey: null };
}

function isPhase2StorageRolloutEnabled() {
  const params = new URLSearchParams(globalThis.location.search);
  const queryEnabled = parseFeatureFlagValue(params.get('ux_phase2_storage'));
  if (queryEnabled !== null) return queryEnabled;
  const stored = parseFeatureFlagValue(safeStorageRead(PHASE2_STORAGE_ROLLOUT_KEY, '0'));
  return stored === true;
}

function loadScript(src) {
  try {
    if (!src || typeof src !== 'string') return false;
    const normalizedSrc = src.trim();
    if (!normalizedSrc) return false;
    const isAnalyticsScript = normalizedSrc.includes('ux-analytics.js');
    const existing = isAnalyticsScript
      ? document.querySelector('script[src*="ux-analytics.js"]')
      : document.querySelector(`script[src="${normalizedSrc}"]`);
    if (existing) return true;
    const script = document.createElement('script');
    script.src = normalizedSrc;
    script.defer = true;
    script.dataset.epiManaged = '1';
    safeOn(script, 'error', (event) => {
      reportNonCriticalError('analytics script load error', event);
      console.warn('[analytics] falha ao carregar', event);
    }, { once: true });
    document.head.appendChild(script);
    return true;
  } catch (error) {
    reportNonCriticalError('analytics script bootstrap failed', error);
    console.warn('[analytics] falha ao carregar', error);
    return false;
  }
}

globalThis.__EPI_FRONTEND_HELPERS__ = Object.freeze({
  safeOn,
  debugLog,
  reportNonCriticalError,
  isViewActive,
  getFeatureFlag,
  getFeatureFlagResolution,
  isPhase2StorageRolloutEnabled,
  ensureModuleBound,
  createScopedAbortController,
  queueStorageWrite,
  registerAbortableRequest,
  markRenderStart,
  markRenderEnd,
  trackAnalyticsEvent,
  setActiveTabsCount,
  isUxPerfDebugEnabled
});
globalThis.__EPI_PHASE2_FLAG_MATRIX__ = PHASE2_FLAG_MATRIX;
globalThis.__EPI_PHASE3_FLAG_MATRIX__ = PHASE3_FLAG_MATRIX;
const EPI_FEATURE_FLAGS_API = Object.freeze({
  definitions: FEATURE_FLAG_DEFINITIONS,
  resolve: getFeatureFlagResolution,
  isKillSwitchEnabled: isGlobalUxKillSwitchEnabled
});
Object.defineProperty(globalThis, '__EPI_FEATURE_FLAGS__', {
  value: EPI_FEATURE_FLAGS_API,
  writable: false,
  configurable: false,
  enumerable: false
});
if (document.readyState === 'loading') {
  safeOn(document, 'DOMContentLoaded', renderPerfHud, { once: true });
} else {
  renderPerfHud();
}
try {
  if (getFeatureFlag('ux_analytics_enabled')) {
    loadScript('/static/ux-analytics.js');
  }
} catch (error) {
  console.warn('[analytics] falha ao carregar', error);
}

safeOn(globalThis, 'beforeunload', flushPendingStorageWrites);
safeOn(globalThis, 'pagehide', flushPendingStorageWrites);
safeOn(document, 'visibilitychange', () => {
  if (document.visibilityState === 'hidden') flushPendingStorageWrites();
});

function isPhase2NavInteractivityEnabled() {
  const queryOnly = getFeatureFlag('colaborador_htmx_enabled', { defaultValue: false, allowStorage: false });
  if (queryOnly) return true;
  if (!isPhase2StorageRolloutEnabled()) return false;
  return getFeatureFlag('colaborador_htmx_enabled', { defaultValue: false, allowStorage: true });
}

function isEpiHtmxPilotEnabled() {
  const queryOnly = getFeatureFlag('epi_htmx_enabled', { defaultValue: false, allowStorage: false });
  if (queryOnly) return true;
  if (!isPhase2StorageRolloutEnabled()) return false;
  return getFeatureFlag('epi_htmx_enabled', { defaultValue: false, allowStorage: true });
}

function isColabListHtmxPilotEnabled() {
  const queryOnly = getFeatureFlag('colaborador_list_htmx_enabled', { defaultValue: false, allowStorage: false });
  if (queryOnly) return true;
  if (!isPhase2StorageRolloutEnabled()) return false;
  return getFeatureFlag('colaborador_list_htmx_enabled', { defaultValue: false, allowStorage: true });
}

function isGestaoColaboradorHtmxPilotEnabled() {
  const queryOnly = getFeatureFlag('gestao_colaborador_htmx_enabled', { defaultValue: false, allowStorage: false });
  if (queryOnly) return true;
  if (!isPhase2StorageRolloutEnabled()) return false;
  return getFeatureFlag('gestao_colaborador_htmx_enabled', { defaultValue: false, allowStorage: true });
}

function isEstoqueHtmxPilotEnabled() {
  const queryOnly = getFeatureFlag('estoque_htmx_enabled', { defaultValue: false, allowStorage: false });
  if (queryOnly) return true;
  if (!isPhase2StorageRolloutEnabled()) return false;
  return getFeatureFlag('estoque_htmx_enabled', { defaultValue: false, allowStorage: true });
}

function isPhase3ModernUiEnabled() {
  return false;
}

function isDashboardInterativoEnabled() {
  if (state.bootstrapDegraded) return false;
  const queryOnly = getFeatureFlag('dashboard_interativo_enabled', { defaultValue: false, allowStorage: false });
  if (queryOnly) return true;
  if (!isPhase2StorageRolloutEnabled()) return true;
  return getFeatureFlag('dashboard_interativo_enabled', { defaultValue: false, allowStorage: true });
}

function isSpaNavigationEnabled() {
  const queryOnly = getFeatureFlag('spa_navigation_enabled', { defaultValue: false, allowStorage: false });
  if (queryOnly) return true;
  const frameworkFlag = Boolean(state?.configurationFramework?.feature_flags?.spa_navigation_enabled);
  if (frameworkFlag) return true;
  if (!isPhase2StorageRolloutEnabled()) return false;
  return getFeatureFlag('spa_navigation_enabled', { defaultValue: false, allowStorage: true });
}

function isUxPerformanceHardeningEnabled() {
  return getFeatureFlag('ux_performance_hardening_enabled', { defaultValue: false, allowStorage: true });
}

function isUxInteractiveAppEnabled() {
  return getFeatureFlag('ux_interactive_app_enabled', { defaultValue: false, allowStorage: true });
}

function isUxToolsFunctionalEnabled() {
  return getFeatureFlag('ux_tools_functional_enabled', { defaultValue: false, allowStorage: true });
}

function isHtmxAlpineProductionEnabled() {
  return getFeatureFlag('htmx_alpine_production_enabled', { defaultValue: false, allowStorage: true });
}

function isHtmxAlpineProductionActive() {
  return isHtmxAlpineProductionEnabled() && isUxToolsFunctionalEnabled();
}

function isUxMobileEnabled() {
  return getFeatureFlag('ux_mobile_enabled', { defaultValue: false, allowStorage: true });
}

function applyPhase2Visibility(moduleName, enabled) {
  document.querySelectorAll(`[data-phase2="${moduleName}"]`).forEach((element) => {
    element.hidden = !enabled;
  });
}

async function refreshPhase2Module(moduleName) {
  if (moduleName !== 'colaboradores') return;
  await loadBootstrap();
  renderEmployees();
}

async function refreshPhase2EpisModule() {
  await loadBootstrap();
  renderEpis();
}

function isPhase2ModuleTrigger(element, definition) {
  if (!(element instanceof HTMLElement)) return false;
  if (element.dataset?.phase2RefreshModule !== definition.moduleName) return false;
  if (!definition.viewSelector) return true;
  return Boolean(element.closest(definition.viewSelector));
}

function getPhase2GlobalKey(moduleName, suffix) {
  return `__PHASE2_${String(moduleName || '').toUpperCase()}_${suffix}__`;
}

function setPhase2ModuleEnabled(moduleName, enabled) {
  globalThis[getPhase2GlobalKey(moduleName, 'ENABLED')] = enabled;
}

function isPhase2ModuleEnabled(moduleName) {
  return globalThis[getPhase2GlobalKey(moduleName, 'ENABLED')] === true;
}

function bindPhase2ModuleListeners(definition) {
  const body = document?.body;
  if (!body) return;
  const listenersBoundKey = getPhase2GlobalKey(definition.moduleName, 'HTMX_LISTENERS_BOUND');
  if (globalThis[listenersBoundKey]) return;
  const listenersController = new AbortController();
  globalThis[listenersBoundKey] = true;
  globalThis[getPhase2GlobalKey(definition.moduleName, 'HTMX_ABORT_CONTROLLER')] = listenersController;

  safeOn(body, 'htmx:afterRequest', (event) => {
    const trigger = event?.detail?.elt;
    if (!isPhase2ModuleTrigger(trigger, definition)) return;
    if (!isPhase2ModuleEnabled(definition.moduleName)) return;
    void definition.refresh(event).catch((error) => {
      reportNonCriticalError(`[fase2:${definition.moduleName}] refresh falhou`, error);
      showToast(definition.toastRefreshError, 'error');
    });
  }, { signal: listenersController.signal });

  safeOn(body, 'htmx:responseError', (event) => {
    const trigger = event?.detail?.elt;
    if (!isPhase2ModuleTrigger(trigger, definition)) return;
    if (!isPhase2ModuleEnabled(definition.moduleName)) return;
    showToast(definition.toastResponseError, 'error');
  }, { signal: listenersController.signal });
}

function getPhase2ModuleBoundKey(moduleName) {
  const normalized = String(moduleName || '')
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, '_');
  return `__EPI_${normalized}_BOUND__`;
}

function setupPhase2ModuleShell(config = {}) {
  const {
    moduleName = '',
    viewSelector = '',
    statusSelector = '',
    activeMessage = 'Ferramentas avançadas disponíveis.',
    inactiveMessage = 'Fluxo clássico ativo.',
    enabled = false
  } = config;
  try {
    const guardKey = getPhase2ModuleBoundKey(moduleName);
    if (globalThis[guardKey]) return;
    const root = viewSelector ? document.querySelector(viewSelector) : null;
    if (!root) return;
    globalThis[guardKey] = true;
    if (!isViewActive(viewSelector)) return;
    const status = statusSelector ? document.querySelector(statusSelector) : null;
    if (!status) return;
    status.textContent = enabled ? activeMessage : inactiveMessage;
  } catch (error) {
    reportNonCriticalError(`[fase2:${moduleName}] setup shell falhou`, error);
  }
}

const PHASE2_MODULE_DEFINITIONS = Object.freeze([
  {
    moduleName: 'colaboradores',
    flagResolver: isPhase2NavInteractivityEnabled,
    viewSelector: '#colaboradores-view',
    setup: ({ enabled }) => {
      setupPhase2ModuleShell({
        moduleName: 'colaboradores',
        enabled,
        viewSelector: '#colaboradores-view',
        statusSelector: '#phase2-colaboradores-status',
        activeMessage: 'Filtros em tempo real e atualização parcial disponíveis.',
        inactiveMessage: 'Fluxo clássico de colaboradores ativo.'
      });
    },
    refresh: async (event) => {
      const moduleName = event?.detail?.elt?.dataset?.phase2RefreshModule;
      await refreshPhase2Module(moduleName);
    },
    toastRefreshError: 'Não foi possível atualizar agora. Tente novamente.',
    toastResponseError: 'Não foi possível atualizar agora. Tente novamente.'
  },
  {
    moduleName: 'colaborador-lista',
    flagResolver: isColabListHtmxPilotEnabled,
    viewSelector: '#colaborador-list-view',
    refresh: async () => {
      syncEmployeesSearchFilters('employees');
    },
    setup: ({ enabled }) => {
      if (typeof globalThis.__EPI_SETUP_COLAB_LIST_PILOT__ === 'function') {
        globalThis.__EPI_SETUP_COLAB_LIST_PILOT__({
          enabled,
          moduleName: 'colaborador-lista',
          viewSelector: '#colaborador-list-view',
          statusSelector: '#phase2-colab-list-status',
          loadingSelector: '#phase2-colab-list-loading'
        });
      }
    },
    toastRefreshError: 'Não foi possível atualizar agora. Tente novamente.',
    toastResponseError: 'Não foi possível atualizar agora. Tente novamente.'
  },
  {
    moduleName: 'gestao-colaborador',
    flagResolver: isGestaoColaboradorHtmxPilotEnabled,
    viewSelector: '#gestao-colaborador-view',
    setup: ({ enabled }) => {
      setupPhase2ModuleShell({
        moduleName: 'gestao-colaborador',
        enabled,
        viewSelector: '#gestao-colaborador-view',
        statusSelector: '#phase2-gestao-colab-status',
        activeMessage: 'Gestão com filtros em tempo real disponível.',
        inactiveMessage: 'Fluxo clássico de Gestão de Colaborador ativo.'
      });
      if (typeof globalThis.__EPI_SETUP_GESTAO_COLAB_PILOT__ === 'function') {
        globalThis.__EPI_SETUP_GESTAO_COLAB_PILOT__({
          enabled,
          moduleName: 'gestao-colaborador',
          viewSelector: '#gestao-colaborador-view',
          statusSelector: '#phase2-gestao-colab-status',
          loadingSelector: '#phase2-gestao-colab-loading'
        });
      }
    },
    refresh: async () => {
      if (typeof globalThis.__EPI_REFRESH_GESTAO_COLAB__ === 'function') {
        globalThis.__EPI_REFRESH_GESTAO_COLAB__();
      }
    },
    toastRefreshError: 'Não foi possível atualizar agora. Tente novamente.',
    toastResponseError: 'Não foi possível atualizar agora. Tente novamente.'
  },
  {
    moduleName: 'epis',
    flagResolver: isEpiHtmxPilotEnabled,
    viewSelector: '#epis-view',
    setup: ({ enabled }) => {
      setupPhase2ModuleShell({
        moduleName: 'epis',
        enabled,
        viewSelector: '#epis-view',
        statusSelector: '#phase2-epis-status',
        activeMessage: 'Cadastro de EPI com atualização parcial disponível.',
        inactiveMessage: 'Fluxo clássico de EPI ativo.'
      });
    },
    refresh: async () => {
      await refreshPhase2EpisModule();
    },
    toastRefreshError: 'Não foi possível atualizar agora. Tente novamente.',
    toastResponseError: 'Não foi possível atualizar agora. Tente novamente.'
  },
  {
    moduleName: 'estoque',
    flagResolver: isEstoqueHtmxPilotEnabled,
    viewSelector: '#estoque-view',
    setup: ({ enabled }) => {
      setupPhase2ModuleShell({
        moduleName: 'estoque',
        enabled,
        viewSelector: '#estoque-view',
        statusSelector: '#phase2-estoque-status',
        activeMessage: 'Controle de estoque com atualização parcial disponível.',
        inactiveMessage: 'Fluxo clássico de Controle de Estoque ativo.'
      });
      if (typeof globalThis.__EPI_SETUP_ESTOQUE_PILOT__ === 'function') {
        globalThis.__EPI_SETUP_ESTOQUE_PILOT__({
          enabled,
          moduleName: 'estoque',
          viewSelector: '#estoque-view',
          statusSelector: '#phase2-estoque-status',
          loadingSelector: '#phase2-estoque-loading'
        });
      }
    },
    refresh: async () => {
      if (typeof globalThis.__EPI_REFRESH_ESTOQUE_LISTA__ === 'function') {
        await globalThis.__EPI_REFRESH_ESTOQUE_LISTA__();
      }
    },
    toastRefreshError: 'Não foi possível atualizar agora. Tente novamente.',
    toastResponseError: 'Não foi possível atualizar agora. Tente novamente.'
  }
]);

function setupPhase2ModulePilot(definition) {
  const enabledByFlag = Boolean(definition.flagResolver?.());
  const requested = enabledByFlag && isHtmxAlpineProductionEnabled();
  const enabled = requested && Boolean(globalThis.htmx);
  applyPhase2Visibility(definition.moduleName, enabled);
  setPhase2ModuleEnabled(definition.moduleName, enabled);
  if (typeof definition.setup === 'function') {
    definition.setup({ enabled });
  }
  if (!requested) return;
  if (!globalThis.htmx) {
    reportNonCriticalError(`[fase2:${definition.moduleName}] HTMX indisponível`, new Error('HTMX unavailable'));
    return;
  }
  bindPhase2ModuleListeners(definition);
  debugLog(`[fase2:${definition.moduleName}] recursos ativos`);
}


function setupPhase29Ux() {
  const modules = [
    {
      name: 'colaborador-lista',
      enabled: isColabListHtmxPilotEnabled() && isHtmxAlpineProductionEnabled(),
      viewSelector: '#colaboradores-view',
      formSelector: '#employee-form',
      surfaceSelector: '#colaborador-list-view',
      tableBodySelector: '#employees-table',
      countSelector: '#phase29-colab-count',
      feedbackSelector: '#phase29-colab-feedback',
      formStatusSelector: '#phase29-colab-form-status',
      filterContainerSelector: '[data-colab-list-filters]',
      loadingSelector: '#phase2-colab-list-loading'
    },
    {
      name: 'epis',
      enabled: isEpiHtmxPilotEnabled() && isHtmxAlpineProductionEnabled(),
      viewSelector: '#epis-view',
      formSelector: '#epi-form',
      surfaceSelector: '#epis-view .phase29-focus-surface',
      tableBodySelector: '#epis-table',
      countSelector: '#phase29-epi-count',
      feedbackSelector: '#phase29-epi-feedback',
      formStatusSelector: '#phase29-epi-form-status',
      filterContainerSelector: '#epis-view .form-grid',
      loadingSelector: '#phase2-epis-loading'
    }
  ];

  const setFeedback = (element, message, tone = 'info') => {
    if (!element) return;
    element.textContent = message;
    element.dataset.tone = tone;
  };

  modules.forEach((moduleConfig) => {
    if (!moduleConfig.enabled) return;

    const view = document.querySelector(moduleConfig.viewSelector);
    const form = document.querySelector(moduleConfig.formSelector);
    const surface = document.querySelector(moduleConfig.surfaceSelector);
    const tableBody = document.querySelector(moduleConfig.tableBodySelector);
    const countElement = document.querySelector(moduleConfig.countSelector);
    const feedbackElement = document.querySelector(moduleConfig.feedbackSelector);
    const formStatusElement = document.querySelector(moduleConfig.formStatusSelector);
    const filterContainer = view?.querySelector(moduleConfig.filterContainerSelector);
    const loadingElement = document.querySelector(moduleConfig.loadingSelector);
    if (!view || !tableBody || !countElement) return;

    const updateVisibleCount = () => {
      const rows = Array.from(tableBody.querySelectorAll('tr')).filter((row) => !row.querySelector('[colspan]'));
      countElement.textContent = String(rows.length);
      if (rows.length === 0) {
        setFeedback(feedbackElement, 'Nenhum resultado para os filtros informados.', 'warning');
      } else {
        setFeedback(feedbackElement, `Exibindo ${rows.length} registro(s) com atualização parcial.`, 'success');
      }
    };

    const queueFilterFeedback = debounce(() => {
      if (loadingElement) loadingElement.classList.add('is-active');
      setFeedback(feedbackElement, 'Aplicando filtros e atualizando a área ativa...', 'info');
      globalThis.setTimeout(() => {
        updateVisibleCount();
        if (loadingElement) loadingElement.classList.remove('is-active');
      }, 180);
    }, 120);

    safeOn(filterContainer, 'input', queueFilterFeedback);
    safeOn(filterContainer, 'change', queueFilterFeedback);

    safeOn(form, 'focusin', () => {
      form.classList.add('phase29-active-pane');
      if (formStatusElement) {
        formStatusElement.textContent = 'Área ativa: cadastro em edição com feedback contínuo.';
      }
    });
    safeOn(form, 'focusout', () => {
      form.classList.remove('phase29-active-pane');
    });
    safeOn(surface, 'mouseenter', () => {
      surface.classList.add('phase29-active-pane');
    });
    safeOn(surface, 'mouseleave', () => {
      surface.classList.remove('phase29-active-pane');
    });

    const observer = new MutationObserver(() => {
      updateVisibleCount();
    });
    observer.observe(tableBody, { childList: true, subtree: true });

    safeOn(document.body, 'htmx:afterRequest', (event) => {
      const trigger = event?.detail?.elt;
      if (!trigger || trigger.dataset?.phase2RefreshModule !== moduleConfig.name) return;
      updateVisibleCount();
      setFeedback(feedbackElement, `Lista atualizada · Última atualização: ${new Date().toLocaleTimeString('pt-BR')}`, 'success');
    });

    safeOn(document.body, 'htmx:responseError', (event) => {
      const trigger = event?.detail?.elt;
      if (!trigger || trigger.dataset?.phase2RefreshModule !== moduleConfig.name) return;
      setFeedback(feedbackElement, 'Não foi possível atualizar agora. Tente novamente.', 'error');
    });

    updateVisibleCount();
  });
}

const INTERACTIVE_TOOLS_MODULES = Object.freeze({
  colaboradores: {
    statusSelector: '#phase2-colaboradores-status',
    loadingSelector: '#phase2-colaboradores-loading',
    tableSelector: '#employees-table',
    filterSelector: '[data-colab-list-filters]',
    syncFilters: () => syncEmployeesSearchFilters('employees'),
    refresh: async () => {
      await loadBootstrap();
      renderEmployees();
      syncEmployeesSearchFilters('employees');
    },
    clearFilters: () => {
      if (refs.employeesFilterCompany) refs.employeesFilterCompany.value = '';
      if (refs.employeesFilterUnit) refs.employeesFilterUnit.value = '';
      if (refs.employeesFilterSearch) refs.employeesFilterSearch.value = '';
      if (refs.employeesFilterSector) refs.employeesFilterSector.value = '';
      if (refs.employeesFilterRole) refs.employeesFilterRole.value = '';
      syncEmployeesSearchFilters('employees');
    }
  },
  'colaborador-lista': {
    statusSelector: '#phase2-colab-list-status',
    loadingSelector: '#phase2-colab-list-loading',
    tableSelector: '#employees-table',
    filterSelector: '[data-colab-list-filters]',
    syncFilters: () => syncEmployeesSearchFilters('employees'),
    refresh: async () => syncEmployeesSearchFilters('employees'),
    clearFilters: () => INTERACTIVE_TOOLS_MODULES.colaboradores.clearFilters()
  },
  'gestao-colaborador': {
    statusSelector: '#phase2-gestao-colab-status',
    loadingSelector: '#phase2-gestao-colab-loading',
    tableSelector: '#employees-table-ops',
    filterSelector: '[data-gestao-colab-filters]',
    syncFilters: () => syncEmployeesSearchFilters('ops'),
    refresh: async () => syncEmployeesSearchFilters('ops'),
    clearFilters: () => {
      if (refs.employeesOpsFilterCompany) refs.employeesOpsFilterCompany.value = '';
      if (refs.employeesOpsFilterUnit) refs.employeesOpsFilterUnit.value = '';
      if (refs.employeesOpsFilterSearch) refs.employeesOpsFilterSearch.value = '';
      if (refs.employeesOpsFilterSector) refs.employeesOpsFilterSector.value = '';
      if (refs.employeesOpsFilterRole) refs.employeesOpsFilterRole.value = '';
      syncEmployeesSearchFilters('ops');
    }
  },
  epis: {
    statusSelector: '#phase2-epis-status',
    loadingSelector: '#phase2-epis-loading',
    tableSelector: '#epis-table',
    filterSelector: '#epis-view .form-grid[data-phase3-filters]',
    syncFilters: () => syncEpisSearchFilters(),
    refresh: async () => {
      await refreshPhase2EpisModule();
      syncEpisSearchFilters();
    },
    clearFilters: () => {
      if (refs.episFilterCompany) refs.episFilterCompany.value = '';
      if (refs.episFilterUnit) refs.episFilterUnit.value = '';
      if (refs.episFilterSearch) refs.episFilterSearch.value = '';
      if (refs.episFilterProtection) refs.episFilterProtection.value = '';
      if (refs.episFilterSection) refs.episFilterSection.value = '';
      if (refs.episFilterManufacturer) refs.episFilterManufacturer.value = '';
      if (refs.episFilterSupplier) refs.episFilterSupplier.value = '';
      syncEpisSearchFilters();
    }
  },
  estoque: {
    statusSelector: '#phase2-estoque-status',
    loadingSelector: '#phase2-estoque-loading',
    tableSelector: '#stock-epis-table',
    filterSelector: '[data-estoque-filters]',
    syncFilters: () => loadStockEpis(),
    refresh: async () => { bindBlockedStockUi(); bindValidityMgmtUi(); await loadStockEpis(); await loadBlockedStock(); await loadValidityOverview(); },
    clearFilters: () => {
      if (refs.stockFilterProtection) refs.stockFilterProtection.value = '';
      if (refs.stockFilterName) refs.stockFilterName.value = '';
      if (refs.stockFilterSection) refs.stockFilterSection.value = '';
      if (refs.stockFilterManufacturer) refs.stockFilterManufacturer.value = '';
      if (refs.stockFilterCa) refs.stockFilterCa.value = '';
      void loadStockEpis();
    }
  },
  dashboard: {
    statusSelector: '#phase3-dashboard-context-status',
    loadingSelector: '#dashboard-interactive-loading',
    tableSelector: '#alerts-list',
    refresh: async () => {
      renderStats();
      renderAlerts();
      renderLatestDeliveries();
      renderDashboardInterativo();
    }
  }
});

const interactiveNavState = {
  recentViews: []
};

function resolveInteractiveToolsModule(moduleName) {
  return INTERACTIVE_TOOLS_MODULES[String(moduleName || '').trim()] || null;
}

function setInteractiveModuleStatus(moduleName, message, tone = 'info') {
  const moduleConfig = resolveInteractiveToolsModule(moduleName);
  const statusNode = moduleConfig?.statusSelector ? document.querySelector(moduleConfig.statusSelector) : null;
  if (!statusNode) return;
  statusNode.textContent = message;
  statusNode.dataset.tone = tone;
}

function isInteractiveModuleBlocked(moduleName) {
  if (!state.bootstrapDegraded) return false;
  const activeView = document.querySelector('.view.active')?.id?.replace(/-view$/, '') || defaultView();
  const moduleViewMap = {
    colaboradores: 'colaboradores',
    'colaborador-lista': 'colaboradores',
    'gestao-colaborador': 'gestao-colaborador',
    epis: 'epis',
    estoque: 'estoque',
    dashboard: 'dashboard'
  };
  const mappedView = moduleViewMap[String(moduleName || '')] || activeView;
  return BOOTSTRAP_REQUIRED_VIEWS.has(mappedView);
}

function setInteractiveModuleLoading(moduleName, active) {
  const moduleConfig = resolveInteractiveToolsModule(moduleName);
  const loadingNode = moduleConfig?.loadingSelector ? document.querySelector(moduleConfig.loadingSelector) : null;
  if (!loadingNode) return;
  loadingNode.hidden = !active;
  loadingNode.classList.toggle('is-active', Boolean(active));
}

function countVisibleRows(tableSelector) {
  const tableBody = document.querySelector(tableSelector);
  if (!tableBody) return 0;
  const rows = Array.from(tableBody.querySelectorAll('tr'));
  return rows.filter((row) => !row.querySelector('[colspan]')).length;
}

function flashUpdatedSurface(moduleName) {
  const moduleConfig = resolveInteractiveToolsModule(moduleName);
  if (!moduleConfig?.tableSelector) return;
  const tableBody = document.querySelector(moduleConfig.tableSelector);
  const surface = tableBody?.closest('.table-wrap') || tableBody;
  if (!surface) return;
  surface.classList.remove('ux-updated-flash');
  void surface.offsetWidth;
  surface.classList.add('ux-updated-flash');
}

async function runInteractiveRefresh(moduleName, triggerButton = null) {
  const moduleConfig = resolveInteractiveToolsModule(moduleName);
  if (!moduleConfig || typeof moduleConfig.refresh !== 'function') return;
  setInteractiveModuleLoading(moduleName, true);
  if (triggerButton) {
    triggerButton.disabled = true;
    triggerButton.dataset.loading = '1';
  }
  setInteractiveModuleStatus(moduleName, 'Atualizando dados...', 'info');
  try {
    await moduleConfig.refresh();
    const visibleRows = moduleConfig.tableSelector ? countVisibleRows(moduleConfig.tableSelector) : 0;
    const summary = visibleRows ? ` ${visibleRows} resultado(s).` : '';
    setInteractiveModuleStatus(moduleName, `Lista atualizada.${summary} Última atualização: ${new Date().toLocaleTimeString('pt-BR')}`, 'success');
    flashUpdatedSurface(moduleName);
  } catch (error) {
    reportNonCriticalError(`[ux-tools] falha ao atualizar ${moduleName}`, error);
    setInteractiveModuleStatus(moduleName, 'Não foi possível atualizar agora. Tente novamente.', 'error');
  } finally {
    setInteractiveModuleLoading(moduleName, false);
    if (triggerButton) {
      triggerButton.disabled = false;
      triggerButton.dataset.loading = '0';
    }
  }
}

function closeInteractiveDropdowns() {
  document.querySelectorAll('[data-ui-dropdown].is-open').forEach((node) => {
    node.classList.remove('is-open');
    const trigger = node.querySelector('[data-dropdown-trigger]');
    const panel = node.querySelector('[data-dropdown-panel]');
    if (trigger) trigger.setAttribute('aria-expanded', 'false');
    if (panel) panel.hidden = true;
  });
}

function toggleInteractiveDropdown(rootNode) {
  if (!rootNode) return;
  const trigger = rootNode.querySelector('[data-dropdown-trigger]');
  const panel = rootNode.querySelector('[data-dropdown-panel]');
  if (!trigger || !panel) return;
  const willOpen = !rootNode.classList.contains('is-open');
  closeInteractiveDropdowns();
  rootNode.classList.toggle('is-open', willOpen);
  trigger.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
  panel.hidden = !willOpen;
}

function setupInteractiveDropdowns() {
  if (!isHtmxAlpineProductionActive()) return;
  if (document.body?.dataset?.uxInteractiveDropdownBound === '1') return;
  if (document.body) document.body.dataset.uxInteractiveDropdownBound = '1';
  document.querySelectorAll('[data-ui-dropdown]').forEach((rootNode) => {
    const trigger = rootNode.querySelector('[data-dropdown-trigger]');
    if (!trigger) return;
    safeOn(trigger, 'click', (event) => {
      event.preventDefault();
      toggleInteractiveDropdown(rootNode);
    });
  });
  safeOn(document, 'click', (event) => {
    const target = event?.target;
    if (target?.closest?.('[data-ui-dropdown]')) return;
    closeInteractiveDropdowns();
  }, { passive: true });
  safeOn(document, 'keydown', (event) => {
    if (event?.key !== 'Escape') return;
    closeInteractiveDropdowns();
    if (document.getElementById('signature-modal')?.classList.contains('is-open')) {
      closeSignatureModal();
    }
  });
}

function renderInteractiveNavTabs(activeView) {
  if (!refs.interactiveNavTabs) return;
  const enabled = isUxInteractiveAppEnabled();
  refs.interactiveNavTabs.hidden = !enabled;
  if (!enabled) return;
  const labels = interactiveNavState.recentViews.slice(-5).map((viewName) => {
    const menuLabel = document.querySelector(`.menu-link[data-view="${viewName}"]`)?.textContent?.trim() || viewName;
    const activeClass = viewName === activeView ? 'is-active' : '';
    return `<button class="interactive-nav-tab ${activeClass}" type="button" data-nav-tab-view="${viewName}">${menuLabel}</button>`;
  });
  refs.interactiveNavTabs.innerHTML = labels.join('');
}

function trackInteractiveViewHistory(view) {
  if (!isUxInteractiveAppEnabled() || !view) return;
  interactiveNavState.recentViews = interactiveNavState.recentViews.filter((item) => item !== view);
  interactiveNavState.recentViews.push(view);
  renderInteractiveNavTabs(view);
}

function collectInteractiveSnapshot(view) {
  if (!isUxInteractiveAppEnabled()) return { view };
  return {
    view,
    scrollY: globalThis.scrollY || 0,
    filters: {
      employees: { ...state.employeesFilters },
      employeesOps: { ...state.employeesOpsFilters },
      epis: { ...state.episFilters }
    }
  };
}

function restoreInteractiveSnapshot(snapshot) {
  if (!isUxInteractiveAppEnabled() || !snapshot || typeof snapshot !== 'object') return;
  const filters = snapshot.filters || {};
  if (filters.employees) state.employeesFilters = { ...state.employeesFilters, ...filters.employees };
  if (filters.employeesOps) state.employeesOpsFilters = { ...state.employeesOpsFilters, ...filters.employeesOps };
  if (filters.epis) state.episFilters = { ...state.episFilters, ...filters.epis };
  applyFilterValues();
  renderTables();
  if (typeof snapshot.scrollY === 'number' && Number.isFinite(snapshot.scrollY)) {
    globalThis.setTimeout(() => globalThis.scrollTo({ top: snapshot.scrollY, behavior: 'auto' }), 0);
  }
}

function bindInteractiveToolsActions() {
  if (!isHtmxAlpineProductionActive()) return;
  if (document.body?.dataset?.uxToolsBound === '1') return;
  if (document.body) document.body.dataset.uxToolsBound = '1';

  const attachRealtimeFilterFeedback = (moduleName) => {
    const moduleConfig = resolveInteractiveToolsModule(moduleName);
    const container = moduleConfig?.filterSelector ? document.querySelector(moduleConfig.filterSelector) : null;
    if (!container) return;
    const run = debounce(() => {
      setInteractiveModuleStatus(moduleName, 'Filtros em tempo real em atualização...', 'info');
      try {
        if (typeof moduleConfig.syncFilters === 'function') moduleConfig.syncFilters();
      } finally {
        const visibleRows = moduleConfig.tableSelector ? countVisibleRows(moduleConfig.tableSelector) : 0;
        setInteractiveModuleStatus(moduleName, `Filtros em tempo real: ${visibleRows} item(ns).`, visibleRows ? 'success' : 'warning');
      }
    }, 300);
    safeOn(container, 'input', run);
    safeOn(container, 'change', run);
  };

  ['colaboradores', 'gestao-colaborador', 'epis', 'estoque'].forEach(attachRealtimeFilterFeedback);

  safeOn(document, 'click', (event) => {
    const refreshBtn = event?.target?.closest?.('[data-phase2-refresh-module]');
    if (refreshBtn && isHtmxAlpineProductionActive()) {
      const moduleName = refreshBtn.dataset.phase2RefreshModule;
      if (resolveInteractiveToolsModule(moduleName)) {
        if (isInteractiveModuleBlocked(moduleName)) {
          setInteractiveModuleStatus(moduleName, 'Dados iniciais indisponíveis. Tente carregar novamente.', 'warning');
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        void runInteractiveRefresh(moduleName, refreshBtn);
        return;
      }
    }
    const actionBtn = event?.target?.closest?.('[data-ux-action]');
    if (!actionBtn) return;
    const action = actionBtn.dataset.uxAction;
    const moduleName = actionBtn.dataset.uxModule;
    const moduleConfig = resolveInteractiveToolsModule(moduleName);
    if (!moduleConfig) return;
    if (isInteractiveModuleBlocked(moduleName)) {
      setInteractiveModuleStatus(moduleName, 'Dados iniciais indisponíveis. Tente carregar novamente.', 'warning');
      return;
    }
    event.preventDefault();
    closeInteractiveDropdowns();
    if (action === 'clear-filters') {
      moduleConfig.clearFilters?.();
      setInteractiveModuleStatus(moduleName, 'Filtros limpos.', 'success');
      return;
    }
    if (action === 'refresh-data') {
      void runInteractiveRefresh(moduleName, actionBtn);
      return;
    }
    if (action === 'scroll-top') {
      globalThis.scrollTo({ top: 0, behavior: 'smooth' });
      setInteractiveModuleStatus(moduleName, 'Você voltou ao topo.', 'info');
      return;
    }
    if (action === 'toggle-density') {
      document.body.classList.toggle('ux-density-compact');
      setInteractiveModuleStatus(moduleName, document.body.classList.contains('ux-density-compact') ? 'Modo compacto ativado.' : 'Modo detalhado ativado.', 'success');
      return;
    }
    if (action === 'close-panel') {
      closeInteractiveDropdowns();
      setInteractiveModuleStatus(moduleName, 'Painel de ações fechado.', 'info');
      return;
    }
    if (action === 'reload-section') {
      void runInteractiveRefresh(moduleName, actionBtn);
    }
  });
}

function setupPhase2PilotsSafely() {
  PHASE2_MODULE_DEFINITIONS.forEach((definition) => {
    try {
      setupPhase2ModulePilot(definition);
    } catch (error) {
      reportNonCriticalError(`[fase2] módulo ${definition.moduleName} desativado por fail-safe`, error);
    }
  });
}

globalThis.__EPI_REFRESH_COLAB_LIST__ = () => {
  syncEmployeesSearchFilters('employees');
};

globalThis.__EPI_REFRESH_GESTAO_COLAB__ = () => {
  syncEmployeesSearchFilters('ops');
};

globalThis.__EPI_REFRESH_ESTOQUE_LISTA__ = async () => {
  bindBlockedStockUi();
  bindValidityMgmtUi();
  await loadStockEpis();
  await loadBlockedStock();
  await loadValidityOverview();
};

function debounce(fn, wait = 200) {
  let timer = null;
  return (...args) => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

function bindSearchInput(target, callback, wait = 180) {
  if (!target) return;
  const handler = debounce(callback, wait);
  safeOn(target, 'input', handler);
}

function markRequiredFieldLabels() {
  const labels = Array.from(document.querySelectorAll('label'));
  labels.forEach((label) => {
    if (label.querySelector('.required-star')) return;
    const directControl = label.querySelector('input, select, textarea');
    let required = Boolean(directControl?.required);
    if (!required) {
      const htmlFor = label.getAttribute('for');
      const referenced = htmlFor ? document.getElementById(htmlFor) : null;
      required = Boolean(referenced?.required);
    }
    if (!required) return;
    const star = document.createElement('span');
    star.className = 'required-star';
    star.textContent = ' *';
    star.setAttribute('aria-hidden', 'true');
    label.appendChild(star);
  });
}

const state = {
  user: safeJsonParse(safeStorageRead(STORAGE_KEYS.session, 'null'), null),
  permissions: safeJsonParse(safeStorageRead(STORAGE_KEYS.permissions, '[]'), []),
  // Visibilidade estrutural por módulo (menu/rotas), combinando a regra
  // padrão + a configuração do Administrador Geral com a permissão técnica
  // — já resolvida pelo backend. Recarregado a cada bootstrap; não precisa
  // de cache otimista offline como `permissions`.
  moduleVisibility: {},
  token: safeStorageRead(STORAGE_KEYS.token, ''),
  configurationRules: [],
  configurationFramework: deepClone(DEFAULT_CONFIGURATION_FRAMEWORK),
  // Configuração admin de visibilidade por módulo (perfil -> módulo -> bool)
  // — distinta de `moduleVisibility` (que é a visibilidade JÁ RESOLVIDA para
  // o ator logado, usada por canAccessView). Esta é a matriz completa que a
  // tela "Configuração → Regras → Visualização" edita.
  moduleVisibilityAdminConfig: {},
  // Padrão IMUTÁVEL do sistema por perfil (perfil -> módulo -> bool),
  // calculado só a partir da permissão técnica — nunca reflete
  // personalização do Administrador Geral. Usado só para exibir o painel
  // "Permissões padrão deste perfil"; a decisão real de acesso continua
  // vindo de moduleVisibilityAdminConfig + resolve_module_visibility no
  // backend.
  moduleVisibilityDefault: {},
  fichaRetentionPolicy: { retention_years: 5, purge_enabled: false, timeline: [] },
  platformBrand: { ...DEFAULT_PLATFORM_BRAND },
  commercialSettings: cloneDefaultCommercialSettings(),
  companies: [], companyAuditLogs: [], fichaAuditLogs: [], users: [], units: [], employees: [], employeeMovements: [], epis: [], deliveries: [], alerts: [], reports: null, lowStock: [], requests: [], fichasPeriods: [], stockGeneratedLabels: [], stockEpis: [], stockEpiMovementItems: [], deliveryEpis: [], deliveryEpisScopeKey: '', deliveryReturnCandidates: [], deliveryReturnScopeKey: '', deliveryReturnPendingScopeKey: '',
  dbPoolStatus: null,
  stockMinimumEditor: { editing: false, epiId: null },
  editingUserId: null,
  editingCompanyId: null,
  selectedCompanyId: null,
  commercialContract: null,
  commercialClauseTemplate: '',
  userFilters: { company_id: '', role: '', active: '', search: '' },
  commercialFilters: { status: '', date_from: '', date_to: '', actor_name: '' },
  unitsFilters: { company_id: '', name: '', type: '', city: '' },
  legalEntitiesFilters: { search: '', type: '', showInactive: false },
  // Terceirizados e Prestadores (ADR-0002): ao contrário de `legalEntities`
  // acima, não chega no bootstrap — o módulo é opt-in/oculto por padrão, então
  // a lista só é buscada sob demanda quando a tela é aberta (ver showView).
  outsourcedCompanies: [],
  outsourcedCompaniesAvailable: [],
  outsourcedCompanyUpdateRequests: [],
  outsourcedCompaniesFilters: { search: '', kind: '' },
  // Cadastro de Colaboradores simplificado (ADR-0002 §10.2) — derivado por
  // filtro client-side sobre `state.employees` (tipo_vinculo != CLT), sem
  // rota nova de listagem: mesma lista já usada pela tela geral de
  // Colaboradores, só recortada aqui.
  outsourcedEmployeesFilters: { search: '' },
  outsourcedEmployeesSummary: [],
  archivedOutsourcedCompanies: [],
  archivedOutsourcedCompaniesFilters: { company_id: '', date: '', reason: '', user: '' },
  archivedOutsourcedEmployees: [],
  archivedOutsourcedEmployeesFilters: { company_id: '', date: '', reason: '', user: '' },
  archivedUnits: [],
  archivedUnitsFilters: { company_id: '', date: '', reason: '', user: '' },
  archivedEmployees: [],
  archivedEmployeesFilters: { company_id: '', date: '', reason: '', user: '' },
  archivedEpis: [],
  archivedEpisFilters: { company_id: '', date: '', reason: '', user: '' },
  employeesFilters: { company_id: '', unit_id: '', search: '', sector: '', role_name: '' },
  employeesOpsFilters: { company_id: '', unit_id: '', search: '', sector: '', role_name: '' },
  episFilters: { company_id: '', unit_id: '', search: '', protection: '', section: '', manufacturer: '', supplier: '', validity: '' },
  deliveriesFilters: { company_id: '', unit_id: '', employee: '', epi: '', date_from: '', date_to: '', status: '' },
  pagination: { deliveries: 1, employees: 1, epis: 1 },
  fichaFilters: { company_id: '', unit_id: '', search: '' },
  dashboardFilters: { query: '' },
  reportsRequestInFlight: false,
  reportArchivePage: 1,
  reportArchiveTotal: 0,
  reportArchivePageSize: 50,
  reportArchiveItems: [],
  signatureDraft: null,
  currentDevolutionContext: null,
  bootstrapDegraded: false,
  bootstrapError: null,
  bootstrapRetrying: false,
  bootstrapWarnings: [],
  bootstrapAutoRetryTimer: null,
  bootstrapAutoRetryCountdownTimer: null,
  bootstrapAutoRetryAttempt: 0,
  requirePasswordChange: safeJsonParse(safeStorageRead(STORAGE_KEYS.changeRequired, 'false'), false),
  fichaFinalizeClickBound: false
};
globalThis.__EPI_APP_STATE__ = state;

const qrScannerState = {
  active: false,
  stream: null,
  rafId: null,
  mode: '',
  zxingReader: null,
  zxingControls: null,
  html5Scanner: null,
  stopping: null,
  starting: false,
  startToken: 0,
  lastDecodedText: '',
  lastDecodedAt: 0,
  lastFeedbackKey: '',
  lastFeedbackAt: 0,
  sessionEmployeeId: '',
  scanSession: [],
  scanSessionIndex: new Set(),
  lastAcceptedAtByText: new Map(),
  duplicateCountByText: new Map()
};
const deliveryCodeValidationState = {
  code: '',
  source: '',
  autoValidated: false
};

const refs = {
  loginScreen: document.getElementById('login-screen'),
  mainScreen: document.getElementById('main-screen'),
  mainContent: document.getElementById('main-content'),
  interactiveNavTabs: document.getElementById('interactive-nav-tabs'),
  menu: document.getElementById('menu'),
  menuLinks: Array.from(document.querySelectorAll('.menu-link[data-view]')),
  viewNodes: Array.from(document.querySelectorAll('.view')),
  loginForm: document.getElementById('login-form'),
  loginUsername: document.getElementById('login-username'),
  loginPassword: document.getElementById('login-password'),
  loginPasswordToggle: document.getElementById('login-password-toggle'),
  recoveryPanel: document.getElementById('recovery-panel'),
  loginMessage: document.getElementById('login-message'),
  recoveryToggle: document.getElementById('forgot-password-btn'),
  recoveryUsername: document.getElementById('recovery-username'),
  recoveryPassword: document.getElementById('recovery-password'),
  recoveryKey: document.getElementById('recovery-key'),
  recoverySubmit: document.getElementById('recovery-submit'),
  platformBrandPanel: document.getElementById('platform-brand-panel'),
  loginBrandLogo: document.getElementById('login-brand-logo'),
  platformBrandLogo: document.getElementById('platform-brand-logo'),
  platformBrandName: document.getElementById('platform-brand-name'),
  profileLabel: document.getElementById('profile-label'),
  loggedUserIdentity: document.getElementById('logged-user-identity'),
  companyBadge: document.getElementById('company-badge'),
  viewTitle: document.getElementById('view-title'),
  topbarEyebrow: document.getElementById('topbar-eyebrow'),
  spaNavigationIndicator: document.getElementById('spa-navigation-indicator'),
  currentDate: document.getElementById('current-date'),
  mobileMenuToggle: document.getElementById('mobile-menu-toggle'),
  topConfigTrigger: document.getElementById('top-config-trigger'),
  statsGrid: document.getElementById('stats-grid'),
  dashboardGlobalSearch: document.getElementById('dashboard-global-search'),
  dashboardRefreshNow: document.getElementById('dashboard-refresh-now'),
  dashboardInteractivePanel: document.getElementById('dashboard-interactive-panel'),
  dashboardInteractiveKpis: document.getElementById('dashboard-interactive-kpis'),
  dashboardInteractiveLoading: document.getElementById('dashboard-interactive-loading'),
  dashboardInteractiveError: document.getElementById('dashboard-interactive-error'),
  dashboardChartDeliveriesCompany: document.getElementById('dashboard-chart-deliveries-company'),
  dashboardChartLowStockUnit: document.getElementById('dashboard-chart-low-stock-unit'),
  phase3DashboardContextStatus: document.getElementById('phase3-dashboard-context-status'),
  bootstrapDegradedBanner: document.getElementById('bootstrap-degraded-banner'),
  bootstrapDegradedPanel: document.getElementById('bootstrap-degraded-panel'),
  bootstrapDegradedPanelMessage: document.getElementById('bootstrap-degraded-panel-message'),
  alertsList: document.getElementById('alerts-list'),
  latestDeliveries: document.getElementById('latest-deliveries'),
  approvedEpiTable: document.getElementById('approved-epi-table'),
  approvedEpiSearchName: document.getElementById('approved-epi-search-name'),
  approvedEpiSearchProtection: document.getElementById('approved-epi-search-protection'),
  approvedEpiSearchCa: document.getElementById('approved-epi-search-ca'),
  approvedEpiSearchManufacturer: document.getElementById('approved-epi-search-manufacturer'),
  approvedEpiSearchSection: document.getElementById('approved-epi-search-section'),
  companiesTable: document.getElementById('companies-table'),
  companiesSummary: document.getElementById('companies-summary'),
  companyDetails: document.getElementById('company-details'),
  companyForm: document.getElementById('company-form'),
  platformBrandForm: document.getElementById('platform-brand-form'),
  commercialSettingsForm: document.getElementById('commercial-settings-form'),
  platformLogoFile: document.getElementById('platform-logo-file'),
  platformLogoPreview: document.getElementById('platform-logo-preview'),
  platformLoginLogoFile: document.getElementById('platform-login-logo-file'),
  platformLoginLogoPreview: document.getElementById('platform-login-logo-preview'),
  commercialForm: document.getElementById('commercial-form'),
  commercialCompany: document.getElementById('commercial-company'),
  commercialPlanHint: document.getElementById('commercial-plan-hint'),
  commercialStats: document.getElementById('commercial-stats'),
  commercialFilterStatus: document.getElementById('commercial-filter-status'),
  commercialFilterDateFrom: document.getElementById('commercial-filter-date-from'),
  commercialFilterDateTo: document.getElementById('commercial-filter-date-to'),
  commercialFilterActor: document.getElementById('commercial-filter-actor'),
  commercialContractPdf: document.getElementById('commercial-contract-pdf'),
  commercialExport: document.getElementById('commercial-export'),
  commercialExportExcel: document.getElementById('commercial-export-excel'),
  commercialPrint: document.getElementById('commercial-print'),
  commercialSummary: document.getElementById('commercial-summary'),
  commercialAlerts: document.getElementById('commercial-alerts'),
  commercialExpiring: document.getElementById('commercial-expiring'),
  commercialHistory: document.getElementById('commercial-history'),
  commercialContractStatus: document.getElementById('commercial-contract-status'),
  commercialContractNumber: document.getElementById('commercial-contract-number'),
  commercialContractIssueDate: document.getElementById('commercial-contract-issue-date'),
  commercialContractorAddress: document.getElementById('commercial-contractor-address'),
  commercialContractorRepresentative: document.getElementById('commercial-contractor-representative'),
  commercialContractorRole: document.getElementById('commercial-contractor-role'),
  commercialContractorEmail: document.getElementById('commercial-contractor-email'),
  commercialContractorPhone: document.getElementById('commercial-contractor-phone'),
  commercialContractorW1: document.getElementById('commercial-contractor-w1'),
  commercialContractorW2: document.getElementById('commercial-contractor-w2'),
  commercialProviderName: document.getElementById('commercial-provider-name'),
  commercialProviderLegalName: document.getElementById('commercial-provider-legal-name'),
  commercialProviderCnpj: document.getElementById('commercial-provider-cnpj'),
  commercialProviderAddress: document.getElementById('commercial-provider-address'),
  commercialProviderRepresentative: document.getElementById('commercial-provider-representative'),
  commercialProviderRole: document.getElementById('commercial-provider-role'),
  commercialProviderEmail: document.getElementById('commercial-provider-email'),
  commercialProviderPhone: document.getElementById('commercial-provider-phone'),
  commercialProviderWitnesses: document.getElementById('commercial-provider-witnesses'),
  commercialContractClauses: document.getElementById('commercial-contract-clauses'),
  commercialSignatureName: document.getElementById('commercial-signature-name'),
  commercialSignatureData: document.getElementById('commercial-signature-data'),
  commercialEmailTo: document.getElementById('commercial-email-to'),
  commercialEmailSubject: document.getElementById('commercial-email-subject'),
  commercialEmailBody: document.getElementById('commercial-email-body'),
  commercialSignedFile: document.getElementById('commercial-signed-file'),
  commercialGenerateContract: document.getElementById('commercial-generate-contract'),
  commercialViewContract: document.getElementById('commercial-view-contract'),
  commercialDownloadContract: document.getElementById('commercial-download-contract'),
  commercialUploadSigned: document.getElementById('commercial-upload-signed'),
  commercialSignContract: document.getElementById('commercial-sign-contract'),
  commercialSendContractEmail: document.getElementById('commercial-send-contract-email'),
  commercialSaveContractManagement: document.getElementById('commercial-save-contract-management'),
  commercialContractEvents: document.getElementById('commercial-contract-events'),
  usersTable: document.getElementById('users-table'),
  unitsTable: document.getElementById('units-table'),
  unitsFilterCompany: document.getElementById('units-filter-company'),
  unitsFilterName: document.getElementById('units-filter-name'),
  legalEntitiesTable: document.getElementById('legal-entities-table'),
  legalEntitiesFilterSearch: document.getElementById('legal-entities-filter-search'),
  legalEntitiesFilterType: document.getElementById('legal-entities-filter-type'),
  legalEntitiesShowInactive: document.getElementById('legal-entities-show-inactive'),
  outsourcedCompaniesTable: document.getElementById('outsourced-companies-table'),
  outsourcedCompaniesFilterSearch: document.getElementById('outsourced-companies-filter-search'),
  outsourcedCompaniesFilterKind: document.getElementById('outsourced-companies-filter-kind'),
  outsourcedCompaniesAvailableTable: document.getElementById('outsourced-companies-available-table'),
  outsourcedCompanyUpdateRequestsTable: document.getElementById('outsourced-company-update-requests-table'),
  outsourcedCompanyUpdateRequestsCard: document.getElementById('outsourced-company-update-requests-card'),
  outsourcedCompanyCorporateLockBanner: document.getElementById('outsourced-company-corporate-lock-banner'),
  outsourcedCompanyUnitArchivedCard: document.getElementById('outsourced-company-unit-archived-card'),
  outsourcedCompanyUnitArchivedTable: document.getElementById('outsourced-company-unit-archived-table'),
  outsourcedEmployeesTable: document.getElementById('outsourced-employees-table'),
  outsourcedEmployeesFilterSearch: document.getElementById('outsourced-employees-filter-search'),
  outsourcedEmployeesSummaryTable: document.getElementById('outsourced-employees-summary-table'),
  archivedOutsourcedCompaniesCard: document.getElementById('archived-outsourced-companies-card'),
  archivedOutsourcedCompaniesTable: document.getElementById('archived-outsourced-companies-table'),
  archivedOutsourcedCompaniesFilterCompany: document.getElementById('archived-outsourced-companies-filter-company'),
  archivedOutsourcedCompaniesFilterDate: document.getElementById('archived-outsourced-companies-filter-date'),
  archivedOutsourcedCompaniesFilterReason: document.getElementById('archived-outsourced-companies-filter-reason'),
  archivedOutsourcedCompaniesFilterUser: document.getElementById('archived-outsourced-companies-filter-user'),
  archivedOutsourcedEmployeesTable: document.getElementById('archived-outsourced-employees-table'),
  archivedOutsourcedEmployeesFilterCompany: document.getElementById('archived-outsourced-employees-filter-company'),
  archivedOutsourcedEmployeesFilterDate: document.getElementById('archived-outsourced-employees-filter-date'),
  archivedOutsourcedEmployeesFilterReason: document.getElementById('archived-outsourced-employees-filter-reason'),
  archivedOutsourcedEmployeesFilterUser: document.getElementById('archived-outsourced-employees-filter-user'),
  // Centro de Migração de Dados (ADR-0003 fase 2)
  migracaoCatalogCards: document.getElementById('migracao-catalog-cards'),
  migracaoCatalogFilter: document.getElementById('migracao-catalog-filter'),
  migracaoSteps: document.getElementById('migracao-steps'),
  migracaoEntity: document.getElementById('migracao-entity'),
  migracaoEntityFields: document.getElementById('migracao-entity-fields'),
  migracaoSourceKind: document.getElementById('migracao-source-kind'),
  migracaoDropzone: document.getElementById('migracao-dropzone'),
  migracaoFile: document.getElementById('migracao-file'),
  migracaoFileName: document.getElementById('migracao-file-name'),
  migracaoSheetWrap: document.getElementById('migracao-sheet-wrap'),
  migracaoSheet: document.getElementById('migracao-sheet'),
  migracaoDetected: document.getElementById('migracao-detected'),
  migracaoSampleHead: document.getElementById('migracao-sample-head'),
  migracaoSampleBody: document.getElementById('migracao-sample-body'),
  migracaoMappingSummary: document.getElementById('migracao-mapping-summary'),
  migracaoMappingSource: document.getElementById('migracao-mapping-source'),
  migracaoMappingTable: document.getElementById('migracao-mapping-table'),
  migracaoBack: document.getElementById('migracao-back'),
  migracaoNext: document.getElementById('migracao-next'),
  migracaoPreview: document.getElementById('migracao-preview'),
  migracaoRestart: document.getElementById('migracao-restart'),
  migracaoPreviewCard: document.getElementById('migracao-preview-card'),
  migracaoPreviewCounters: document.getElementById('migracao-preview-counters'),
  migracaoPreviewDiagnostics: document.getElementById('migracao-preview-diagnostics'),
  migracaoDownloadReport: document.getElementById('migracao-download-report'),
  migracaoStrategy: document.getElementById('migracao-strategy'),
  migracaoStrategyHint: document.getElementById('migracao-strategy-hint'),
  migracaoApply: document.getElementById('migracao-apply'),
  migracaoJobsTable: document.getElementById('migracao-jobs-table'),
  unitsFilterType: document.getElementById('units-filter-type'),
  unitsFilterCity: document.getElementById('units-filter-city'),
  archivedUnitsTable: document.getElementById('archived-units-table'),
  archivedUnitsFilterCompany: document.getElementById('archived-units-filter-company'),
  archivedUnitsFilterDate: document.getElementById('archived-units-filter-date'),
  archivedUnitsFilterReason: document.getElementById('archived-units-filter-reason'),
  archivedUnitsFilterUser: document.getElementById('archived-units-filter-user'),
  archivedEmployeesTable: document.getElementById('archived-employees-table'),
  archivedEmployeesFilterCompany: document.getElementById('archived-employees-filter-company'),
  archivedEmployeesFilterDate: document.getElementById('archived-employees-filter-date'),
  archivedEmployeesFilterReason: document.getElementById('archived-employees-filter-reason'),
  archivedEmployeesFilterUser: document.getElementById('archived-employees-filter-user'),
  archivedEpisTable: document.getElementById('archived-epis-table'),
  archivedEpisFilterCompany: document.getElementById('archived-epis-filter-company'),
  archivedEpisFilterDate: document.getElementById('archived-epis-filter-date'),
  archivedEpisFilterReason: document.getElementById('archived-epis-filter-reason'),
  archivedEpisFilterUser: document.getElementById('archived-epis-filter-user'),
  employeesTable: document.getElementById('employees-table'),
  employeesPagination: document.getElementById('employees-pagination'),
  employeesBulkBar: document.getElementById('employees-bulk-bar'),
  employeesSelectAll: document.getElementById('employees-select-all'),
  employeesFilterCompany: document.getElementById('employees-filter-company'),
  employeesFilterUnit: document.getElementById('employees-filter-unit'),
  employeesFilterSearch: document.getElementById('employees-filter-search'),
  employeesFilterSector: document.getElementById('employees-filter-sector'),
  employeesFilterRole: document.getElementById('employees-filter-role'),
  phase3ColaboradoresContextStatus: document.getElementById('phase3-colaboradores-context-status'),
  phase3ColaboradoresSummary: document.getElementById('phase3-colaboradores-summary'),
  employeesOpsTable: document.getElementById('employees-table-ops'),
  employeesOpsFilterCompany: document.getElementById('employees-ops-filter-company'),
  employeesOpsFilterUnit: document.getElementById('employees-ops-filter-unit'),
  employeesOpsFilterSearch: document.getElementById('employees-ops-filter-search'),
  employeesOpsFilterSector: document.getElementById('employees-ops-filter-sector'),
  employeesOpsFilterRole: document.getElementById('employees-ops-filter-role'),
  phase3GestaoContextStatus: document.getElementById('phase3-gestao-context-status'),
  phase3GestaoSummary: document.getElementById('phase3-gestao-summary'),
  episTable: document.getElementById('epis-table'),
  episPagination: document.getElementById('epis-pagination'),
  episFilterCompany: document.getElementById('epis-filter-company'),
  episFilterUnit: document.getElementById('epis-filter-unit'),
  episFilterSearch: document.getElementById('epis-filter-search'),
  episFilterProtection: document.getElementById('epis-filter-protection'),
  episFilterSection: document.getElementById('epis-filter-section'),
  episFilterManufacturer: document.getElementById('epis-filter-manufacturer'),
  episFilterSupplier: document.getElementById('epis-filter-supplier'),
  episFilterValidity: document.getElementById('epis-filter-validity'),
  phase3EpisContextStatus: document.getElementById('phase3-epis-context-status'),
  phase3EpisSummary: document.getElementById('phase3-epis-summary'),
  deliveriesTable: document.getElementById('deliveries-table'),
  deliveriesPagination: document.getElementById('deliveries-pagination'),
  deliveriesFilterCompany: document.getElementById('deliveries-filter-company'),
  deliveriesFilterUnit: document.getElementById('deliveries-filter-unit'),
  deliveriesFilterEmployee: document.getElementById('deliveries-filter-employee'),
  deliveriesFilterEpi: document.getElementById('deliveries-filter-epi'),
  deliveriesFilterDateFrom: document.getElementById('deliveries-filter-date-from'),
  deliveriesFilterDateTo: document.getElementById('deliveries-filter-date-to'),
  deliveriesFilterStatus: document.getElementById('deliveries-filter-status'),
  stockLowList: document.getElementById('stock-low-list'),
  requestsList: document.getElementById('requests-list'),
  stockEpisTable: document.getElementById('stock-epis-table'),
  stockFilterProtection: document.getElementById('stock-filter-protection'),
  stockFilterName: document.getElementById('stock-filter-name'),
  stockFilterSection: document.getElementById('stock-filter-section'),
  stockFilterManufacturer: document.getElementById('stock-filter-manufacturer'),
  stockFilterCa: document.getElementById('stock-filter-ca'),
  phase3EstoqueContextStatus: document.getElementById('phase3-estoque-context-status'),
  phase3EstoqueSummary: document.getElementById('phase3-estoque-summary'),
  stockEpiMovementSearchName: document.getElementById('stock-epi-search-name'),
  stockEpiMovementSearchManufacturer: document.getElementById('stock-epi-search-manufacturer'),
  stockEpiMovementSearchResults: document.getElementById('stock-epi-search-results'),
  deliveryEpiSearch: document.getElementById('delivery-epi-search'),
  deliveryEpiSearchManufacturer: document.getElementById('delivery-epi-search-manufacturer'),
  deliveryEpiSearchResults: document.getElementById('delivery-epi-search-results'),
  deliveryDevolutionOptions: document.getElementById('delivery-devolution-options'),
  deliveryIsDevolution: document.getElementById('delivery-is-devolution'),
  deliveryDevolutionFields: document.getElementById('delivery-devolution-fields'),
  deliveryReturnDeliveryId: document.getElementById('delivery-return-delivery-id'),
  deliveryReturnDeliveryHint: document.getElementById('delivery-return-delivery-hint'),
  deliveryReturnedDate: document.getElementById('delivery-returned-date'),
  deliveryReturnCondition: document.getElementById('delivery-return-condition'),
  deliveryReturnDestination: document.getElementById('delivery-return-destination'),
  fichaView: document.getElementById('ficha-view'),
  configRulesForm: document.getElementById('config-rules-form'),
  configRuleRole: document.getElementById('config-rule-role'),
  configRuleUnit: document.getElementById('config-rule-unit'),
  configRulesTable: document.getElementById('config-rules-table'),
  moduleVisibilityForm: document.getElementById('module-visibility-form'),
  moduleVisibilityRole: document.getElementById('module-visibility-role'),
  moduleVisibilityDefaultPanel: document.getElementById('module-visibility-default-panel'),
  moduleVisibilityDefaultList: document.getElementById('module-visibility-default-list'),
  moduleVisibilityUnitWrap: document.getElementById('module-visibility-unit-wrap'),
  moduleVisibilityUnit: document.getElementById('module-visibility-unit'),
  moduleVisibilityUnitHint: document.getElementById('module-visibility-unit-hint'),
  moduleVisibilityCheckboxes: document.getElementById('module-visibility-checkboxes'),
  moduleVisibilityFeedback: document.getElementById('module-visibility-feedback'),
  configFrameworkForm: document.getElementById('config-framework-form'),
  configEnableNewEngine: document.getElementById('config-enable-new-engine'),
  configExecutionMode: document.getElementById('config-execution-mode'),
  configRolloutPercentage: document.getElementById('config-rollout-percentage'),
  configAllowNewResponse: document.getElementById('config-allow-new-response'),
  configEnabledProfiles: document.getElementById('config-enabled-profiles'),
  configEnabledCompanies: document.getElementById('config-enabled-companies'),
  configEnabledEndpoints: document.getElementById('config-enabled-endpoints'),
  configEnabledEnvironments: document.getElementById('config-enabled-environments'),
  configReportScopesTable: document.getElementById('config-report-scopes-table'),
  configHierarchyTable: document.getElementById('config-hierarchy-table'),
  configHierarchyJson: document.getElementById('config-hierarchy-json'),
  configReportScopesJson: document.getElementById('config-report-scopes-json'),
  fichaAuditEmployee: document.getElementById('ficha-audit-employee'),
  fichaAuditManager: document.getElementById('ficha-audit-manager'),
  fichaAuditAction: document.getElementById('ficha-audit-action'),
  fichaAuditDateFrom: document.getElementById('ficha-audit-date-from'),
  fichaAuditDateTo: document.getElementById('ficha-audit-date-to'),
  fichaAuditTable: document.getElementById('ficha-audit-table'),
  archivalPolicyForm: document.getElementById('archival-policy-form'),
  archivalRetentionUnits: document.getElementById('archival-retention-units'),
  archivalRetentionEpis: document.getElementById('archival-retention-epis'),
  archivalRetentionEmployees: document.getElementById('archival-retention-employees'),
  archivalPolicyFeedback: document.getElementById('archival-policy-feedback'),
  fichaRetentionForm: document.getElementById('ficha-retention-form'),
  fichaRetentionYears: document.getElementById('ficha-retention-years'),
  fichaRetentionPurgeEnabled: document.getElementById('ficha-retention-purge-enabled'),
  fichaRetentionTimeline: document.getElementById('ficha-retention-timeline'),
  fichaRetentionPurgeRun: document.getElementById('ficha-retention-purge-run'),
  passwordChangeForm: document.getElementById('password-change-form'),
  fichaEmployee: document.getElementById('ficha-employee'),
  fichaFilterCompany: document.getElementById('ficha-filter-company'),
  fichaFilterUnit: document.getElementById('ficha-filter-unit'),
  fichaFilterSearch: document.getElementById('ficha-filter-search'),
  reportSummary: document.getElementById('report-summary'),
  reportUnits: document.getElementById('report-units'),
  reportSectors: document.getElementById('report-sectors'),
  reportEmployeeFichas: document.getElementById('report-employee-fichas'),
  reportArchiveTable: document.getElementById('report-archive-table'),
  reportArchivePagination: document.getElementById('report-archive-pagination'),
  signatureModal: document.getElementById('signature-modal'),
  signatureModalName: document.getElementById('signature-modal-name'),
  signatureModalAt: document.getElementById('signature-modal-at'),
  signatureModalCanvas: document.getElementById('signature-modal-canvas'),
  signatureModalComment: document.getElementById('signature-modal-comment'),
  signatureModalClear: document.getElementById('signature-modal-clear'),
  signatureModalCancel: document.getElementById('signature-modal-cancel'),
  signatureModalConfirm: document.getElementById('signature-modal-confirm'),
  deliverySignatureOpen: document.getElementById('delivery-signature-open'),
  deliverySignatureStatus: document.getElementById('delivery-signature-status'),
  deliverySignatureData: document.getElementById('delivery-signature-data'),
  deliverySignatureName: document.getElementById('delivery-signature-name'),
  deliverySignatureAt: document.getElementById('delivery-signature-at'),
  deliverySignatureComment: document.getElementById('delivery-signature-comment'),
  deliveryAvailableQr: document.getElementById('delivery-available-qr'),
  deliveryAvailableQrApply: document.getElementById('delivery-available-qr-apply'),
  deliveryAvailableQrHint: document.getElementById('delivery-available-qr-hint'),
  userForm: document.getElementById('user-form'),
  userRole: document.getElementById('user-role'),
  userLinkedEmployeeSearch: document.getElementById('user-linked-employee-search'),
  userLinkedEmployeeResults: document.getElementById('user-linked-employee-results'),
  userFilterCompany: document.getElementById('user-filter-company'),
  userFilterRole: document.getElementById('user-filter-role'),
  userFilterStatus: document.getElementById('user-filter-status'),
  userFilterSearch: document.getElementById('user-filter-search'),
  usersSummary: document.getElementById('users-summary')
};
globalThis.__EPI_REFS__ = refs;

function qrCodeImageUrl(value) {
  const normalized = encodeURIComponent(String(value || '').trim());
  return `https://api.qrserver.com/v1/create-qr-code/?size=420x420&qzone=4&ecc=M&format=png&color=000000&bgcolor=FFFFFF&data=${normalized}`;
}

function buildEmployeeAccessLink(token) {
  const normalizedToken = String(token || '').trim();
  if (!normalizedToken) return '';
  return `${globalThis.location.origin}/?employee_token=${encodeURIComponent(normalizedToken)}`;
}
// ── Camada HTTP: fonte única em static/js/modules/api-client.js (Fase 1 UBX) ──
// api-client.js é carregado ANTES de app.js (ver _scripts.html) e expõe em
// globalThis: apiFetch / apiFetchOptional / apiFetchWithRetry, além dos helpers
// (requestApiResponse, parseApiPayload, ensureExpectedApiResponse,
// throwIfApiRequestFailed, createApiError, waitMs). Estas funções eram cópias
// idênticas dessa lógica; agora delegam para a única fonte de verdade, evitando
// divergência entre as duas implementações.
async function api(path, options = {}) {
  return globalThis.apiFetch(path, options);
}

async function apiOptional(path, options = {}) {
  return globalThis.apiFetchOptional(path, options);
}

async function apiWithBootstrapRetry(path, options = {}, config = {}) {
  return globalThis.apiFetchWithRetry(path, options, config);
}

function normalizeRole(role) {
  if (!role) return '';
  const normalized = String(role)
    .normalize('NFD')
    .replaceAll(/[\u0300-\u036f]/g, '')
    .trim()
    .toLowerCase()
    .replaceAll(/[\s-]+/g, '_');
  return ROLE_ALIASES[normalized] || role;
}

// `cnpjs` entra aqui porque a tela vive inteiramente do bootstrap
// (`state.legalEntities` e `state.companies`). Fora desta lista, o
// carregamento degradado deixava a lista vazia com a mensagem "Sem CNPJs
// cadastrados" — que é falsa: o CNPJ existe, só não chegou. O operador
// concluía que a empresa não tinha CNPJ nenhum.
const BOOTSTRAP_REQUIRED_VIEWS = new Set(['empresas', 'comercial', 'usuarios', 'unidades', 'cnpjs', 'colaboradores', 'gestao-colaborador', 'epis', 'estoque', 'fichas', 'relatorios', 'configuracao']);

function setBootstrapDegraded(error) {
  const wasAlreadyDegraded = state.bootstrapDegraded;
  state.bootstrapDegraded = true;
  state.bootstrapError = {
    status: Number(error?.status || 0),
    code: String(error?.code || ''),
    message: String(error?.message || 'Falha ao carregar dados iniciais.')
  };
  if (!wasAlreadyDegraded) {
    state.bootstrapAutoRetryAttempt = 0;
    scheduleBootstrapAutoRetry();
  }
}

function clearBootstrapDegraded() {
  state.bootstrapDegraded = false;
  state.bootstrapError = null;
  state.bootstrapAutoRetryAttempt = 0;
  if (state.bootstrapAutoRetryTimer) {
    clearTimeout(state.bootstrapAutoRetryTimer);
    state.bootstrapAutoRetryTimer = null;
  }
  _clearAutoRetryCountdown();
}

function recordOptionalBootstrapSectionSkipped(section, reason, detail = {}) {
  const info = {
    section: String(section || 'bootstrap'),
    reason: String(reason || 'optional_section_skipped'),
    status: Number(detail?.status || 0),
    permission: String(detail?.permission || '')
  };
  console.info('[bootstrap] optional_section_skipped', info);
}

function recordBootstrapSectionWarning(section, error) {
  const warning = {
    section: String(section || 'bootstrap'),
    message: String(error?.message || error || 'Falha parcial ao carregar dados iniciais.'),
    status: Number(error?.status || 0)
  };
  state.bootstrapWarnings = [...(state.bootstrapWarnings || []).filter((item) => item.section !== warning.section), warning];
  console.warn('[bootstrap] seção opcional indisponível', warning, error);
  if (section === 'stock') {
    setInteractiveModuleStatus('estoque', 'Estoque temporariamente indisponível. Use atualizar para tentar novamente.', 'warning');
  }
}

async function loadOptionalBootstrapSection(section, fallbackValue, loader, options = {}) {
  const permission = String(options.permission || '');
  if (permission && !hasPermission(permission)) {
    recordOptionalBootstrapSectionSkipped(section, 'missing_permission', { permission });
    return fallbackValue;
  }
  try {
    return await loader();
  } catch (error) {
    if (Number(error?.status || 0) === 403) {
      recordOptionalBootstrapSectionSkipped(section, 'forbidden', { status: 403, permission });
      return fallbackValue;
    }
    recordBootstrapSectionWarning(section, error);
    return fallbackValue;
  }
}

function buildBootstrapDegradedMessage() {
  if (!state.bootstrapError) return 'Não foi possível carregar os dados iniciais desta área.';
  const suffix = state.bootstrapError.status ? ` (HTTP ${state.bootstrapError.status})` : '';
  return `${state.bootstrapError.message}${suffix}`;
}

function updateBootstrapDegradedUi(currentView = null) {
  const activeView = currentView || document.querySelector('.view.active')?.id?.replace(/-view$/, '') || defaultView();
  if (refs.bootstrapDegradedBanner) refs.bootstrapDegradedBanner.hidden = !state.bootstrapDegraded;
  const shouldBlockActiveView = state.bootstrapDegraded && BOOTSTRAP_REQUIRED_VIEWS.has(activeView);
  if (refs.bootstrapDegradedPanel) refs.bootstrapDegradedPanel.hidden = !shouldBlockActiveView;
  if (refs.bootstrapDegradedPanelMessage) refs.bootstrapDegradedPanelMessage.textContent = buildBootstrapDegradedMessage();

  document.querySelectorAll('[data-phase2-refresh-module], [data-dropdown-trigger], [data-ux-action]').forEach((node) => {
    if (!(node instanceof HTMLButtonElement)) return;
    const moduleName = node.dataset.uxModule || node.dataset.phase2RefreshModule || '';
    const blocked = state.bootstrapDegraded && isInteractiveModuleBlocked(moduleName || activeView);
    node.disabled = blocked;
    if (blocked) {
      node.title = 'Dados iniciais indisponíveis. Tente carregar novamente.';
    } else if (node.title === 'Dados iniciais indisponíveis. Tente carregar novamente.') {
      node.title = '';
    }
  });
}

const BOOTSTRAP_AUTO_RETRY_DELAYS = [5000, 10000, 20000, 40000, 60000];
const BOOTSTRAP_AUTO_RETRY_MAX_DELAY = 60000;

function _startAutoRetryCountdown(delayMs) {
  _clearAutoRetryCountdown();
  const el = document.getElementById('bootstrap-auto-retry-status');
  if (!el) return;
  let remaining = Math.ceil(delayMs / 1000);
  const update = () => { el.textContent = `Reconectando automaticamente em ${remaining}s...`; };
  update();
  state.bootstrapAutoRetryCountdownTimer = setInterval(() => {
    remaining -= 1;
    if (remaining <= 0) {
      el.textContent = 'Reconectando...';
      _clearAutoRetryCountdown();
    } else {
      update();
    }
  }, 1000);
}

function _clearAutoRetryCountdown() {
  if (state.bootstrapAutoRetryCountdownTimer) {
    clearInterval(state.bootstrapAutoRetryCountdownTimer);
    state.bootstrapAutoRetryCountdownTimer = null;
  }
  const el = document.getElementById('bootstrap-auto-retry-status');
  if (el) el.textContent = '';
}

function scheduleBootstrapAutoRetry() {
  const attempt = state.bootstrapAutoRetryAttempt;
  if (state.bootstrapAutoRetryTimer) clearTimeout(state.bootstrapAutoRetryTimer);
  const delay = attempt < BOOTSTRAP_AUTO_RETRY_DELAYS.length
    ? BOOTSTRAP_AUTO_RETRY_DELAYS[attempt]
    : BOOTSTRAP_AUTO_RETRY_MAX_DELAY;
  console.info(`[bootstrap] auto-retry agendado em ${delay}ms (tentativa ${attempt + 1})`);
  _startAutoRetryCountdown(delay);
  state.bootstrapAutoRetryTimer = setTimeout(async () => {
    state.bootstrapAutoRetryTimer = null;
    if (!state.bootstrapDegraded) return;
    state.bootstrapAutoRetryAttempt += 1;
    await retryBootstrap();
    if (state.bootstrapDegraded) scheduleBootstrapAutoRetry();
  }, delay);
}

async function retryBootstrap() {
  if (state.bootstrapRetrying) return;
  state.bootstrapRetrying = true;
  _clearAutoRetryCountdown();
  const autoRetryStatus = document.getElementById('bootstrap-auto-retry-status');
  if (autoRetryStatus) autoRetryStatus.textContent = 'Reconectando...';
  try {
    if (refs.bootstrapDegradedPanelMessage) refs.bootstrapDegradedPanelMessage.textContent = 'Tentando carregar novamente...';
    await loadBootstrap();
    clearBootstrapDegraded();
    updateBootstrapDegradedUi();
    renderAll();
  } catch (error) {
    // Avoid re-scheduling auto-retry from setBootstrapDegraded (already degraded)
    state.bootstrapDegraded = true;
    state.bootstrapError = {
      status: Number(error?.status || 0),
      code: String(error?.code || ''),
      message: String(error?.message || 'Falha ao carregar dados iniciais.')
    };
    updateBootstrapDegradedUi();
    console.warn('[auth] retryBootstrap falhou, mantendo modo degradado', error);
  } finally {
    state.bootstrapRetrying = false;
  }
}

// Aceita uma permissão só (string), uma lista (array) ou uma string com
// várias separadas por espaço (uso comum em atributos data-* no HTML, que
// só guardam string) — verdadeiro se QUALQUER uma estiver presente. Cobre o
// caso de duas permissões alternativas liberarem a mesma ação (ex.:
// employees:create/employees:create_simplified em Empresas Terceirizadas,
// ADR-0002 §10.5) sem duplicar toda a lógica de checagem.
function normalizePermissionList(permission) {
  if (Array.isArray(permission)) return permission;
  return String(permission || '').split(/\s+/).filter(Boolean);
}

function hasPermission(permission) {
  const activePermissions = state.permissions.length ? state.permissions : normalizePermissions(state.user, []);
  return normalizePermissionList(permission).some((p) => activePermissions.includes(p));
}

function requirePermission(permission, message = 'Você não tem permissão para realizar esta ação.') {
  if (!hasPermission(permission)) {
    alert(message);
    return false;
  }
  return true;
}

function actorQuery() {
  return `actor_user_id=${encodeURIComponent(state.user?.id || '')}`;
}

function unitTypeLabel(value) {
  const normalized = String(value || '').toLowerCase();
  if (normalized === 'navio' || normalized === 'embarcacao') return tr('unit.typeVessel', 'Embarcação');
  if (normalized === 'plataforma') return tr('unit.typePlatform', 'Plataforma');
  return tr('unit.typeBase', 'Base');
}

function setLoginMessage(message = '', isError = false) {
  if (!refs.loginMessage) return;
  refs.loginMessage.textContent = message;
  refs.loginMessage.classList.toggle('error', Boolean(isError));
}

function setLoginPasswordVisibility(isVisible) {
  if (!refs.loginPassword || !refs.loginPasswordToggle) return;
  refs.loginPassword.type = isVisible ? 'text' : 'password';
  refs.loginPasswordToggle.setAttribute('aria-pressed', isVisible ? 'true' : 'false');
  refs.loginPasswordToggle.setAttribute('aria-label', isVisible ? 'Ocultar senha' : 'Mostrar senha');
}

function toggleLoginPasswordVisibility() {
  const isVisible = refs.loginPassword?.type === 'text';
  setLoginPasswordVisibility(!isVisible);
}

function sanitizeLoginUrlParams() {
  const url = new URL(globalThis.location.href);
  let changed = false;
  ['username', 'password'].forEach((key) => {
    if (url.searchParams.has(key)) {
      url.searchParams.delete(key);
      changed = true;
    }
  });
  if (changed) {
    const queryString = url.searchParams.toString();
    const nextUrl = url.pathname + (queryString ? `?${queryString}` : '') + (url.hash || '');
    globalThis.history.replaceState({}, '', nextUrl);
  }
}

function preloadLoginFromUrl() {
  const params = new URLSearchParams(globalThis.location.search);
  const username = String(params.get('username') || '').trim();
  const password = String(params.get('password') || '').trim();
  if (username && refs.loginUsername) refs.loginUsername.value = username;
  if (password && refs.loginPassword) refs.loginPassword.value = password;
  if (username || password) {
    setLoginMessage('Credenciais da URL pré-preenchidas. Clique em "Entrar" para continuar.');
    sanitizeLoginUrlParams();
  }
}

function formatCurrency(value) {
  return Number(value || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function cloneCommercialSettings(settings = DEFAULT_COMMERCIAL_SETTINGS) {
  return deepClone(settings);
}

function getCommercialSettings() {
  return state.commercialSettings || cloneCommercialSettings();
}

function planEntries() {
  return Object.entries(getCommercialSettings().plans || {});
}

function planLabel(planKey) {
  return getCommercialSettings().plans?.[planKey]?.label || planKey;
}

function planOptionMarkup(selectedPlan = '') {
  return planEntries().map(([key, plan]) => `<option value="${key}" ${key === selectedPlan ? 'selected' : ''}>${plan.label}</option>`).join('');
}

function planHintText(planKey, addendumEnabled = false) {
  const plan = getCommercialSettings().plans?.[planKey];
  if (!plan) return '';
  const maxText = plan.max_users === null ? 'sem teto' : `até ${plan.max_users}`;
  return `${plan.label}: Usuário(s), ${maxText}${addendumEnabled ? ' com aditivo contratual.' : '.'}`;
}

function formValues(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function parseMonthsValue(rawValue) {
  const digits = String(rawValue ?? '').replaceAll(/[^\d-]/g, '').trim();
  const parsed = Number.parseInt(digits || '0', 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
}

function renderEpiPhotoPreview(photoValue) {
  const preview = document.getElementById('epi-photo-preview');
  if (!preview) return;
  if (!photoValue) {
    preview.innerHTML = `<div class="summary-item">${tr('epi.photoMissing', 'Sem foto anexada.')}</div>`;
    return;
  }
  preview.innerHTML = `<div class="logo-preview-card"><img class="company-logo company-logo-lg" src="${photoValue}" alt="Preview da foto do EPI"><span>${tr('epi.photoAttached', 'Foto do EPI anexada')}</span></div>`;
}

async function handleEpiPhotoUpload(event) {
  const hiddenField = document.getElementById('epi-photo-data');
  const file = event.target.files?.[0];
  if (!hiddenField) return;
  if (!file) {
    hiddenField.value = '';
    renderEpiPhotoPreview('');
    return;
  }
  if (!String(file.type || '').startsWith('image/')) {
    alert('Envie um arquivo de imagem válido para o EPI.');
    event.target.value = '';
    return;
  }
  try {
    hiddenField.value = await fileToJpegDataUrl(file, 960);
    renderEpiPhotoPreview(hiddenField.value);
  } catch (error) {
    alert(error.message || 'Não foi possí­vel processar a foto do EPI.');
    event.target.value = '';
    hiddenField.value = '';
    renderEpiPhotoPreview('');
  }
}

function isMobileUserAgent() {
  return /android|iphone|ipad|ipod|mobile|tablet/i.test(String(navigator.userAgent || ''));
}

function openEpiPhotoPicker({ preferCamera = false } = {}) {
  const input = document.getElementById('epi-photo-file');
  if (!input) return;
  if (preferCamera && isMobileUserAgent()) {
    input.setAttribute('capture', 'environment');
  } else {
    input.removeAttribute('capture');
  }
  input.click();
}

function configureEpiPhotoInputCapture() {
  const input = document.getElementById('epi-photo-file');
  if (!input) return;
  input.setAttribute('accept', 'image/*');
  if (isMobileUserAgent()) {
    input.setAttribute('capture', 'environment');
  } else {
    input.removeAttribute('capture');
  }
}

function getCompanyFormField(name) {
  const field = refs.companyForm?.elements?.namedItem(name) || null;
  if (!field) console.error(`[company-form] Campo esperado Não encontrado: ${name}`);
  return field;
}

function setCompanyFieldValue(name, value = '', options = {}) {
  const field = options.optional ? refs.companyForm?.elements?.namedItem(name) || null : getCompanyFormField(name);
  if (field) field.value = value ?? '';
}

function readCompanyFieldValue(name, fallback = '', options = {}) {
  const field = options.optional ? refs.companyForm?.elements?.namedItem(name) || null : getCompanyFormField(name);
  return field ? field.value ?? fallback : fallback;
}


function digitsOnly(value) {
  return String(value || '').replaceAll(/\D/g, '');
}

function formatCnpj(value) {
  const digits = digitsOnly(value);
  if (digits.length !== 14) return value || '';
  return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5, 8)}/${digits.slice(8, 12)}-${digits.slice(12)}`;
}

function companyLogoSrc(logoValue) {
  return String(logoValue || '').startsWith('data:image/') ? logoValue : DEFAULT_COMPANY_LOGO;
}

function companyLogoMarkup(company, className = 'company-logo') {
  const label = company?.name || 'Empresa';
  return `<img class="${className}" src="${companyLogoSrc(company?.logo_type)}" alt="Logotipo de ${label}">`;
}

function renderPlatformLogoPreview(logoValue) {
  if (!refs.platformLogoPreview) return;
  refs.platformLogoPreview.innerHTML = `<div class="logo-preview-card">${companyLogoMarkup({ name: state.platformBrand?.display_name || 'Sua Empresa', logo_type: logoValue }, 'company-logo company-logo-lg')}<span>${logoValue ? 'Logotipo carregado' : 'Imagem padrão em uso'}</span></div>`;
}

function renderPlatformLoginLogoPreview(logoValue) {
  if (!refs.platformLoginLogoPreview) return;
  refs.platformLoginLogoPreview.innerHTML = `<div class="logo-preview-card">${companyLogoMarkup({ name: 'Logo da tela de login', logo_type: logoValue }, 'company-logo company-logo-lg')}<span>${logoValue ? 'Logotipo de login carregado' : 'Sem logotipo de login (padrão)'}</span></div>`;
}

async function handlePlatformLogoUpload(event) {
  const file = event.target.files?.[0];
  if (!file) {
    refs.platformBrandForm.elements.logo_type.value = '';
    renderPlatformLogoPreview('');
    return;
  }
  const allowed = ['image/png', 'image/jpeg', 'image/svg+xml'];
  if (!allowed.includes(file.type)) {
    alert('Envie um logotipo PNG, JPG ou SVG.');
    event.target.value = '';
    return;
  }
  try {
    refs.platformBrandForm.elements.logo_type.value = await fileToJpegDataUrl(file);
    renderPlatformLogoPreview(refs.platformBrandForm.elements.logo_type.value);
  } catch (error) {
    alert(error.message);
    event.target.value = '';
  }
}

async function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('Não foi possível ler o arquivo do logotipo.'));
    reader.onload = () => resolve(typeof reader.result === 'string' ? reader.result : '');
    reader.readAsDataURL(file);
  });
}

async function handlePlatformLoginLogoUpload(event) {
  const file = event.target.files?.[0];
  if (!file) {
    refs.platformBrandForm.elements.login_logo_type.value = '';
    renderPlatformLoginLogoPreview('');
    return;
  }
  const allowed = ['image/png', 'image/svg+xml'];
  if (!allowed.includes(file.type)) {
    alert('A logo da tela de login aceita apenas PNG ou SVG.');
    event.target.value = '';
    return;
  }
  try {
    refs.platformBrandForm.elements.login_logo_type.value = await fileToDataUrl(file);
    renderPlatformLoginLogoPreview(refs.platformBrandForm.elements.login_logo_type.value);
  } catch (error) {
    alert(error.message);
    event.target.value = '';
  }
}

async function fileToJpegDataUrl(file, maxWidth = 720) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('Não foi possí­vel ler o arquivo do logotipo.'));
    reader.onload = () => {
      const image = new Image();
      image.onerror = () => reject(new Error('Não foi possí­vel processar o logotipo enviado.'));
      image.onload = () => {
        const scale = Math.min(1, maxWidth / (image.width || maxWidth));
        const canvas = document.createElement('canvas');
        canvas.width = Math.max(1, Math.round(image.width * scale));
        canvas.height = Math.max(1, Math.round(image.height * scale));
        const context = canvas.getContext('2d');
        context.fillStyle = '#ffffff';
        context.fillRect(0, 0, canvas.width, canvas.height);
        context.drawImage(image, 0, 0, canvas.width, canvas.height);
        resolve(canvas.toDataURL('image/jpeg', 0.92));
      };
      image.src = typeof reader.result === 'string' ? reader.result : '';
    };
    reader.readAsDataURL(file);
  });
}

function renderPlatformBrand() {
  const brand = state.platformBrand || DEFAULT_PLATFORM_BRAND;
  if (refs.platformBrandName) refs.platformBrandName.textContent = brand.display_name || DEFAULT_PLATFORM_BRAND.display_name;
  if (refs.platformBrandLogo) refs.platformBrandLogo.innerHTML = companyLogoMarkup({ name: brand.display_name, logo_type: brand.logo_type }, 'company-logo company-logo-sm');
  if (refs.platformBrandForm) {
    refs.platformBrandForm.elements.display_name.value = brand.display_name || '';
    refs.platformBrandForm.elements.legal_name.value = brand.legal_name || '';
    refs.platformBrandForm.elements.cnpj.value = brand.cnpj || '';
    refs.platformBrandForm.elements.logo_type.value = brand.logo_type || '';
    refs.platformBrandForm.elements.login_logo_type.value = brand.login_logo_type || '';
  }
  if (refs.platformLogoFile) refs.platformLogoFile.value = '';
  if (refs.platformLoginLogoFile) refs.platformLoginLogoFile.value = '';
  renderPlatformLogoPreview(brand.logo_type || '');
  renderPlatformLoginLogoPreview(brand.login_logo_type || '');
  // Só re-renderiza o login logo se o platformBrand tiver um logo definido.
  // Caso contrário mantém o logo do tenant aplicado pelo tenant-init.js.
  const loginLogoSrc = brand.login_logo_type || '';
  if (refs.loginBrandLogo) {
    if (loginLogoSrc) {
      refs.loginBrandLogo.innerHTML = companyLogoMarkup({ name: brand.display_name, logo_type: loginLogoSrc }, 'company-logo company-logo-lg');
    } else if (!window.__epiTenant) {
      refs.loginBrandLogo.innerHTML = '';
    }
    // Se não há logo de plataforma mas há tenant, o tenant-init.js já aplicou
  }
}

function canManageMinimumStock() {
  return ['admin', 'user'].includes(state.user?.role);
}

function isOperationalProfile() {
  return ['admin', 'user'].includes(state.user?.role);
}

function canUseEpiAllUnitsScope() {
  return EPI_ALL_UNITS_PROFILES.includes(state.user?.role);
}

function hasConfigurationAccess() {
  return CONFIGURATION_ADMIN_ROLES.includes(state.user?.role) && hasPermission('settings:view');
}

function hasHardeningAccess() {
  return state.user?.role === 'master_admin' && hasPermission('settings:update');
}

function canViewConfiguration() {
  return hasConfigurationAccess();
}

function canManageUsers() {
  return hasPermission('users:update') || hasPermission('users:create') || hasPermission('users:delete');
}

function canManageEpi() {
  return hasPermission('epis:create') || hasPermission('epis:update') || hasPermission('epis:delete');
}

function canViewReports() {
  return hasPermission('reports:view');
}

function canAccessCommercialArea() {
  return state.user?.role === 'master_admin' && hasPermission('commercial:view');
}

function splitUserName(fullName) {
  const parts = String(fullName || '').trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return { firstName: '', lastName: '' };
  return { firstName: parts[0], lastName: parts.slice(1).join(' ') };
}

function accessibleViews() {
  return Object.entries(VIEW_PERMISSIONS).filter(([, permission]) => hasPermission(permission)).map(([view]) => view);
}

const SPA_NAV_SUPPORTED_VIEWS = Object.freeze(['dashboard', 'empresas', 'usuarios', 'unidades', 'colaboradores', 'gestao-colaborador', 'epis', 'estoque']);
const SPA_NAV_CLASSIC_FALLBACK_VIEWS = Object.freeze(['entregas', 'fichas', 'relatorios']);

function resolveRefreshHandlers(view) {
  const map = {
    dashboard: async () => {
      renderStats();
      renderAlerts();
      renderLatestDeliveries();
      renderDashboardInterativo();
    },
    empresas: async () => {
      renderCompaniesSummary();
      renderCompanies();
      renderCompanyDetails(state.selectedCompanyId);
    },
    usuarios: async () => {
      renderTables();
    },
    unidades: async () => {
      renderTables();
    },
    colaboradores: async () => {
      renderEmployees();
      if (typeof globalThis.__EPI_REFRESH_COLAB_LIST__ === 'function') globalThis.__EPI_REFRESH_COLAB_LIST__();
    },
    'gestao-colaborador': async () => {
      if (typeof globalThis.__EPI_REFRESH_GESTAO_COLAB__ === 'function') globalThis.__EPI_REFRESH_GESTAO_COLAB__();
    },
    epis: async () => {
      renderEpis();
    },
    estoque: async () => {
      if (typeof globalThis.__EPI_REFRESH_ESTOQUE_LISTA__ === 'function') {
        await globalThis.__EPI_REFRESH_ESTOQUE_LISTA__();
      } else {
        renderStockEpis();
      }
    }
  };
  return map[view];
}

const spaNavigationInflightByView = new Map();
const spaNavigationLastRunByView = new Map();

async function runSpaPartialNavigation(view) {
  if (!isSpaNavigationEnabled()) return;
  if (!SPA_NAV_SUPPORTED_VIEWS.includes(view)) return;
  const refreshHandler = resolveRefreshHandlers(view);
  if (typeof refreshHandler !== 'function') return;

  if (isUxPerformanceHardeningEnabled()) {
    if (spaNavigationInflightByView.has(view)) {
      return spaNavigationInflightByView.get(view);
    }
    const now = Date.now();
    const lastRunAt = spaNavigationLastRunByView.get(view) || 0;
    if (now - lastRunAt < 120) return;
    spaNavigationLastRunByView.set(view, now);
  }

  const task = (async () => {
    setSpaNavigationLoading(true);
    try {
      await refreshHandler();
    } catch (error) {
      reportNonCriticalError(`[spa-nav] falha na atualização parcial de ${view}`, error);
      showToast('Falha na navegação parcial. Fluxo clássico aplicado automaticamente.', 'error');
      globalThis.location.assign(buildNavigationUrl(view).toString());
    } finally {
      setSpaNavigationLoading(false);
      spaNavigationInflightByView.delete(view);
    }
  })();

  if (isUxPerformanceHardeningEnabled()) {
    spaNavigationInflightByView.set(view, task);
  }
  return task;
}

function navigateToView(view, options = {}) {
  const {
    historyMode = 'push',
    partial = true
  } = options;
  const canUseSpa = isSpaNavigationEnabled() && SPA_NAV_SUPPORTED_VIEWS.includes(view);
  if (!canUseSpa) {
    if (isSpaNavigationEnabled() && SPA_NAV_CLASSIC_FALLBACK_VIEWS.includes(view)) {
      globalThis.location.assign(buildNavigationUrl(view).toString());
      return;
    }
    showView(view, { partial: false });
    return;
  }
  if (historyMode === 'push') {
    const nextUrl = buildNavigationUrl(view);
    globalThis.history.pushState(collectInteractiveSnapshot(view), '', nextUrl);
  }
  showView(view, { partial });
}

function bindSpaNavigationHistory() {
  if (globalThis.__EPI_SPA_NAV_HISTORY_BOUND__) return;
  globalThis.__EPI_SPA_NAV_HISTORY_BOUND__ = true;
  safeOn(globalThis, 'popstate', (event) => {
    if (!state?.user) return;
    if (!isSpaNavigationEnabled()) return;
    const fallbackView = defaultView();
    const nextView = event?.state?.view || resolveViewFromLocation() || fallbackView;
    restoreInteractiveSnapshot(event?.state);
    showView(nextView, { partial: true, historyMode: 'replace' });
  });
}

// Fonte ÚNICA de acesso a uma view: permissão + restrição por papel.
// Algumas views existem em duas variantes (ex.: "colaboradores" — cadastro
// completo, só para administradores estruturais — vs. "gestao-colaborador" —
// operacional, para Administrador Local). O menu já respeita isso; este helper
// centraliza a regra para que a navegação programática (cards do dashboard,
// deep-links) não abra uma view proibida para o papel.
function canAccessView(view) {
  const permission = VIEW_PERMISSIONS[view];
  if (permission && !hasPermission(permission)) {
    // ADR-0002 §10 (correção de escopo): Terceirizados e Prestadores abre
    // com employees:create (aba Empresas) OU employees:create_simplified
    // (aba Cadastro de Colaboradores) — sem isso, admin/user (que só têm a
    // segunda) nunca alcançavam a tela mesmo com o módulo ligado.
    const altPermission = VIEW_PERMISSION_ALTERNATIVES[view];
    if (!altPermission || !hasPermission(altPermission)) return false;
  }
  const role = state.user?.role;
  // Views de cadastro estrutural: apenas administradores estruturais.
  if (['epis', 'colaboradores', 'unidades', 'usuarios'].includes(view)
      && !['master_admin', 'general_admin', 'registry_admin'].includes(role)) {
    return false;
  }
  // Gestão de colaborador (movimentação entre unidades): administradores +
  // perfis operacionais (Local/Gestor) — fora do escopo de module_visibility
  // (não é um dos módulos configuráveis), mantém a restrição fixa.
  if (view === 'gestao-colaborador'
      && !['master_admin', 'general_admin', 'registry_admin', 'admin', 'user'].includes(role)) {
    return false;
  }
  // Estoque/Entregas/Fichas de EPI: a restrição fixa de papel foi
  // substituída pela visibilidade por módulo (configurável pelo
  // Administrador Geral) logo abaixo — o padrão do sistema já nega estas
  // três para Comprador/Aprovador (MODULE_REQUIRED_PERMISSIONS/
  // _STRUCTURALLY_HIDDEN_BY_DEFAULT em rule_engine.py), mas agora pode ser
  // liberado por configuração, o que um `return false` fixo aqui impediria.
  if (view === 'configuracao') return hasConfigurationAccess();
  // Visibilidade estrutural por módulo (configuração do Administrador
  // Geral): módulo ausente do mapa é tratado como visível — só restringe
  // quando o backend explicitamente desliga o módulo para o papel. Nunca
  // amplia o que a permissão técnica acima já negou.
  const module = VIEW_MODULE[view];
  if (module && state.moduleVisibility && Object.prototype.hasOwnProperty.call(state.moduleVisibility, module)) {
    if (Boolean(state.moduleVisibility[module])) return true;
    // Mesma correção acima, agora para o módulo: terceirizados OU
    // terceirizados_colaboradores libera a view.
    const altModule = VIEW_MODULE_ALTERNATIVES[view];
    if (altModule && Object.prototype.hasOwnProperty.call(state.moduleVisibility, altModule)) {
      return Boolean(state.moduleVisibility[altModule]);
    }
    return false;
  }
  return true;
}
globalThis.canAccessView = canAccessView;

// View de colaboradores acessível ao papel atual, ou '' quando nenhuma.
// - Administradores estruturais: "colaboradores" (cadastro/lista/arquivados).
// - Administrador Local (admin): "gestao-colaborador" (movimentação entre
//   unidades, via employees:transfer — não edita cadastro).
// - Demais (ex.: Gestor de EPI, sem employees:transfer): nenhuma.
function accessibleEmployeesView() {
  if (canAccessView('colaboradores')) return 'colaboradores';
  if (canAccessView('gestao-colaborador')) return 'gestao-colaborador';
  return '';
}
globalThis.accessibleEmployeesView = accessibleEmployeesView;

function showView(view, options = {}) {
  const partial = options.partial !== false;
  const historyMode = options.historyMode || null;
  const currentActiveView = document.querySelector('.view.active')?.id || '';
  // Bloqueia navegação programática para view proibida ao papel (não só
  // sem permissão): ex.: card do dashboard tentando abrir "colaboradores"
  // (cadastro) para um Administrador Local, que só acessa "gestao-colaborador".
  if (view !== defaultView() && !canAccessView(view)) {
    view = defaultView();
  }
  const permission = VIEW_PERMISSIONS[view];
  // Mesma regra de alternativa de canAccessView() (ADR-0002 §10/§11): sem
  // isto, este segundo gate — mais estrito, só checa a permissão primária —
  // bloqueava com o alerta abaixo mesmo depois de canAccessView() já ter
  // liberado a view pela permissão alternativa (ex.: Gestor de EPI/
  // Administrador Local em Terceirizados e Prestadores, que só têm
  // employees:create_simplified). O item ficava visível no menu mas
  // inacessível ao clique.
  const altPermission = VIEW_PERMISSION_ALTERNATIVES[view];
  if (permission && !hasPermission(permission) && !(altPermission && hasPermission(altPermission))) {
    alert('Seu perfil Não pode acessar esta área.');
    console.warn('[RBAC]', {
      rota: view,
      perfil_recebido: state.user?.role,
      empresa_id: state.user?.company_id,
      permissao_necessaria: permission,
      perfis_permitidos: Object.entries(ROLE_PERMISSIONS)
        .filter(([, permissions]) => permissions.includes(permission))
        .map(([role]) => role),
      acesso_negado_motivo: state.user?.role ? 'perfil_sem_permissao' : 'perfil_ausente'
    });
    view = defaultView();
  }

  if (view === 'configuracao' && !hasConfigurationAccess()) {
    view = defaultView();
  }
  const viewElement = document.getElementById(`${view}-view`);
  if (!viewElement) {
    console.warn('[VIEW]', `View container not found for "${view}"`);
    return;
  }

  refs.viewNodes.forEach((item) => item.classList.remove('active'));
  refs.menuLinks.forEach((item) => item.classList.toggle('active', item.dataset.view === view));
  if (refs.topConfigTrigger) refs.topConfigTrigger.classList.toggle('active', view === 'configuracao');
  viewElement.classList.add('active');
  if (isSpaNavigationEnabled()) {
    viewElement.classList.remove('spa-view-enter');
    void viewElement.offsetWidth;
    viewElement.classList.add('spa-view-enter');
  }
  if (currentActiveView && currentActiveView !== `${view}-view`) {
    void stopDeliveryQrCamera();
  }
  if (refs.viewTitle) {
    const titleLink = document.querySelector(`.menu-link[data-view="${view}"]`);
    const titleText = titleLink?.textContent || (view === 'configuracao' ? 'Configuração' : 'Dashboard');
    refs.viewTitle.textContent = titleText;
    document.title = `${titleText} · Controle de EPI`;
  }
  if (refs.topbarEyebrow) {
    refs.topbarEyebrow.textContent = VIEW_EYEBROW[view] || 'EPI Controle';
  }
  if (isPhase3ModernUiEnabled()) {
    updatePhase3ContextStatus(view, 'success', 'Área ativa');
  }
  updateBootstrapDegradedUi(view);
  if (isSpaNavigationEnabled() && historyMode === 'replace') {
    const nextUrl = buildNavigationUrl(view);
    globalThis.history.replaceState(collectInteractiveSnapshot(view), '', nextUrl);
  }
  try {
    document.dispatchEvent(new CustomEvent('epi:viewchange', { detail: { view } }));
  } catch (error) {
    reportNonCriticalError('[view] falha ao notificar troca de tela', error);
  }
  if (partial && SPA_NAV_SUPPORTED_VIEWS.includes(view)) {
    void runSpaPartialNavigation(view);
  }
  if (view === 'unidades' && typeof loadArchivedUnits === 'function') {
    void loadArchivedUnits();
  }
  if (view === 'colaboradores' && typeof loadArchivedRecords === 'function') {
    void loadArchivedRecords('employee');
  }
  if (view === 'epis' && typeof loadArchivedRecords === 'function') {
    void loadArchivedRecords('epi');
  }
  if (view === 'terceirizados' && typeof loadOutsourcedCompanies === 'function') {
    void loadOutsourcedCompanies();
    renderOutsourcedEmployees();
    void loadArchivedRecords('outsourcedCompany');
    void loadArchivedRecords('outsourcedEmployee');
    void loadOutsourcedEmployeesSummary();
    // Inbox de "Solicitar atualização cadastral" (ADR-0002 §12) — só quem
    // tem employees:update completo (Geral/Registro) recebe algo; a própria
    // loadOutsourcedCompanyUpdateRequests já checa o gate e sai cedo.
    void loadOutsourcedCompanyUpdateRequests();
  }
  if (view === 'configuracao' && typeof loadArchivalPolicy === 'function') {
    void loadArchivalPolicy();
  }
  if (view === 'migracao' && typeof loadDataMigrationCatalog === 'function') {
    void loadDataMigrationCatalog();
    void loadDataMigrationJobs();
    renderDataMigrationSteps();
  }
  trackInteractiveViewHistory(view);
  trackNavBackHistory(currentActiveView.replace(/-view$/, ''), view);
}

// ── Voltar / breadcrumbs (auditoria Navegação §6) ────────────────────────────
// Pilha de histórico de telas própria (independente de flags), reaproveitando os
// elementos dormentes #hierarchy-back-btn e #hierarchy-breadcrumb do topbar.
const _navBack = { stack: [], suppress: false };

function viewLabel(view) {
  const link = document.querySelector(`.menu-link[data-view="${view}"]`);
  return (link?.textContent || '').trim() || (view === 'configuracao' ? 'Configuração' : view);
}

function trackNavBackHistory(prevView, view) {
  if (!_navBack.suppress && prevView && prevView !== view) {
    _navBack.stack.push(prevView);
    if (_navBack.stack.length > 50) _navBack.stack.shift();
  }
  updateNavBackUi(view);
}

function updateNavBackUi(view) {
  const wrap = document.getElementById('hierarchy-breadcrumb-wrap');
  const backBtn = document.getElementById('hierarchy-back-btn');
  const crumb = document.getElementById('hierarchy-breadcrumb');
  const hasHistory = _navBack.stack.length > 0;
  // A seta Voltar fica sempre visível e funcional (sem histórico volta ao
  // Dashboard); a trilha (breadcrumb) só aparece quando há histórico.
  if (wrap) wrap.hidden = false;
  if (backBtn) {
    backBtn.hidden = false;
    const prev = _navBack.stack[_navBack.stack.length - 1];
    backBtn.setAttribute('aria-label', prev
      ? `${trEpi('nav.back', 'Voltar')}: ${viewLabel(prev)}`
      : trEpi('nav.back', 'Voltar'));
    backBtn.title = backBtn.getAttribute('aria-label');
  }
  if (crumb) {
    crumb.hidden = !hasHistory;
    // Trilha compacta: até 2 níveis anteriores + atual (o atual não é clicável).
    const trail = _navBack.stack.slice(-2).concat(view);
    crumb.innerHTML = trail.map((v, i) => {
      const label = escapeHtml(viewLabel(v));
      if (i === trail.length - 1) { return `<span class="breadcrumb-current" aria-current="page">${label}</span>`; }
      return `<button type="button" class="breadcrumb-link" data-crumb-view="${escapeHtml(v)}">${label}</button>`;
    }).join('<span class="breadcrumb-sep" aria-hidden="true">›</span>');
  }
}

function navigateBack() {
  // Volta à tela anterior do histórico SPA; sem histórico, retorna ao Dashboard.
  const target = _navBack.stack.pop() || defaultView();
  _navBack.suppress = true;
  try { navigateToView(target); } finally { _navBack.suppress = false; }
  updateNavBackUi(target);
}

function bindNavBackBehavior() {
  if (globalThis.__EPI_NAV_BACK_BOUND__) { return; }
  globalThis.__EPI_NAV_BACK_BOUND__ = true;
  safeOn(document.getElementById('hierarchy-back-btn'), 'click', navigateBack);
  safeOn(document.getElementById('hierarchy-breadcrumb'), 'click', (event) => {
    const link = event.target?.closest?.('.breadcrumb-link[data-crumb-view]');
    if (!link) { return; }
    const target = link.getAttribute('data-crumb-view');
    // Ao clicar num nível anterior, descarta o histórico até ele (inclusive).
    const idx = _navBack.stack.lastIndexOf(target);
    if (idx >= 0) { _navBack.stack = _navBack.stack.slice(0, idx); }
    _navBack.suppress = true;
    try { navigateToView(target); } finally { _navBack.suppress = false; }
    updateNavBackUi(target);
  });
}


// ── Abas de módulo (padrão ERP — auditoria UI/UX) ────────────────────────────
// Navegação por abas DENTRO de cada view administrativa (Cadastro/Lista/...).
// Declarativo: <nav class="view-tabs" data-vtabs="grupo"> com botões
// <button class="vtab" data-vtab="chave"> + painéis <div class="vtab-panel"
// data-vtab-panel="chave"> na mesma view. A lógica de negócio não muda: os
// painéis inativos permanecem no DOM (renderizações por id continuam
// funcionando) — apenas deixam de ser exibidos.
const VIEW_TAB_STORAGE_PREFIX = 'epi_vtab_';

// Ações de linha que preenchem um formulário noutra aba: ao clicar, a aba do
// formulário é ativada para o usuário ver o que acabou de abrir para edição.
const VIEW_TAB_EDIT_TRIGGERS = [
  { selector: '[data-unit-edit]', group: 'unidades', tab: 'cadastro' },
  { selector: '[data-employee-edit]', group: 'colaboradores', tab: 'cadastro' },
  { selector: '[data-company-edit]', group: 'empresas', tab: 'cadastro' },
  { selector: '[data-user-edit]', group: 'usuarios', tab: 'cadastro' },
  { selector: '[data-epi-edit]', group: 'epis', tab: 'cadastro' }
];

function viewTabButtons(nav) {
  return Array.from(nav.querySelectorAll('[data-vtab]'));
}

// Painéis do grupo do nav. Suporte a sub-abas aninhadas: painéis com
// data-vtab-group pertencem apenas ao nav de mesmo grupo; sem o atributo,
// pertencem ao grupo "raiz" da view (comportamento legado preservado).
function viewTabPanelsFor(nav) {
  const root = nav.closest('.view') || document;
  const group = nav.dataset.vtabs || '';
  const scoped = Array.from(root.querySelectorAll(`[data-vtab-panel][data-vtab-group="${group}"]`));
  if (scoped.length) return scoped;
  return Array.from(root.querySelectorAll('[data-vtab-panel]:not([data-vtab-group])'));
}

function viewTabPanelFor(nav, key) {
  return viewTabPanelsFor(nav).find((panel) => panel.dataset.vtabPanel === key) || null;
}

function visibleViewTabs(nav) {
  return viewTabButtons(nav).filter((tab) => tab.style.display !== 'none');
}

function activateViewTab(nav, key, options = {}) {
  const group = nav.dataset.vtabs || '';
  viewTabButtons(nav).forEach((tab) => {
    const active = tab.dataset.vtab === key;
    tab.classList.toggle('is-active', active);
    tab.setAttribute('aria-selected', active ? 'true' : 'false');
    tab.tabIndex = active ? 0 : -1;
  });
  viewTabPanelsFor(nav).forEach((panel) => {
    panel.classList.toggle('is-active', panel.dataset.vtabPanel === key);
  });
  if (options.persist !== false) {
    try { sessionStorage.setItem(VIEW_TAB_STORAGE_PREFIX + group, key); } catch (_e) { /* storage indisponível */ }
  }
  if (options.focus) nav.querySelector(`[data-vtab="${key}"]`)?.focus();
  document.dispatchEvent(new CustomEvent('epi:vtab-change', { detail: { group, tab: key } }));
}

function syncViewTabsVisibility(nav) {
  // Aba cujo painel só tem conteúdo oculto (cards escondidos por permissão)
  // fica oculta também; se era a ativa, cai para a primeira aba visível.
  let activeHidden = false;
  viewTabButtons(nav).forEach((tab) => {
    const panel = viewTabPanelFor(nav, tab.dataset.vtab);
    if (!panel) return;
    const hasVisibleContent = Array.from(panel.children).some((child) => {
      if (child.hidden) return false;
      return child.style.display !== 'none';
    });
    tab.style.display = hasVisibleContent ? '' : 'none';
    if (!hasVisibleContent && tab.classList.contains('is-active')) activeHidden = true;
  });
  if (activeHidden) {
    const fallback = visibleViewTabs(nav)[0];
    if (fallback) activateViewTab(nav, fallback.dataset.vtab, { persist: false });
  }
}

function handleViewTabKeydown(nav, event) {
  if (!['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(event.key)) return;
  const tabs = visibleViewTabs(nav);
  if (!tabs.length) return;
  const currentIndex = Math.max(0, tabs.findIndex((tab) => tab.classList.contains('is-active')));
  let nextIndex = currentIndex;
  if (event.key === 'ArrowRight') nextIndex = (currentIndex + 1) % tabs.length;
  if (event.key === 'ArrowLeft') nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
  if (event.key === 'Home') nextIndex = 0;
  if (event.key === 'End') nextIndex = tabs.length - 1;
  event.preventDefault();
  activateViewTab(nav, tabs[nextIndex].dataset.vtab, { focus: true });
}

function findViewTabsNav(group) {
  return document.querySelector(`nav[data-vtabs="${group}"]`);
}

function setupViewTabs() {
  document.querySelectorAll('nav[data-vtabs]').forEach((nav) => {
    if (nav.dataset.vtabsBound === '1') return;
    nav.dataset.vtabsBound = '1';
    const group = nav.dataset.vtabs || '';
    nav.setAttribute('role', 'tablist');
    viewTabButtons(nav).forEach((tab) => {
      tab.setAttribute('role', 'tab');
      const panel = viewTabPanelFor(nav, tab.dataset.vtab);
      if (panel) panel.setAttribute('role', 'tabpanel');
    });
    safeOn(nav, 'click', (event) => {
      const tab = event.target?.closest?.('[data-vtab]');
      if (!tab || tab.disabled) return;
      activateViewTab(nav, tab.dataset.vtab);
    });
    safeOn(nav, 'keydown', (event) => handleViewTabKeydown(nav, event));
    let stored = '';
    try { stored = sessionStorage.getItem(VIEW_TAB_STORAGE_PREFIX + group) || ''; } catch (_e) { /* sem storage */ }
    const initial = viewTabButtons(nav).some((tab) => tab.dataset.vtab === stored)
      ? stored
      : (viewTabButtons(nav)[0]?.dataset.vtab || '');
    if (initial) activateViewTab(nav, initial, { persist: false });
    syncViewTabsVisibility(nav);
  });

  if (!globalThis.__EPI_VTABS_GLOBAL_BOUND__) {
    globalThis.__EPI_VTABS_GLOBAL_BOUND__ = true;
    // Revalida a visibilidade das abas ao trocar de view (permissões podem
    // ter ocultado cards depois do login/bootstrap).
    safeOn(document, 'epi:viewchange', (event) => {
      const view = document.getElementById(`${event?.detail?.view || ''}-view`);
      view?.querySelectorAll?.('nav[data-vtabs]').forEach((nav) => syncViewTabsVisibility(nav));
    });
    // "Editar" numa listagem preenche o formulário noutra aba → ativa a aba
    // do formulário depois que o handler delegado da tabela já rodou (bubble).
    safeOn(document, 'click', (event) => {
      const trigger = VIEW_TAB_EDIT_TRIGGERS.find(({ selector }) => event.target?.closest?.(selector));
      if (!trigger) return;
      const nav = findViewTabsNav(trigger.group);
      if (!nav) return;
      activateViewTab(nav, trigger.tab, { persist: false });
      viewTabPanelFor(nav, trigger.tab)?.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
    });
    // Ao sair da sub-aba "Registrar" de Entrega de EPI, encerra a câmera de QR
    // (que vive apenas nesse painel) para liberar o dispositivo.
    safeOn(document, 'epi:vtab-change', (event) => {
      if (event?.detail?.group === 'entregas' && event.detail.tab !== 'registrar') {
        void stopDeliveryQrCamera();
      }
    });
  }
}

function registerMultitabNavigationApi() {
  globalThis.__EPI_APP_NAV_API__ = {
    showView,
    navigateToView,
    buildNavigationUrl,
    defaultView,
    hasPermission,
    canAccessView: (view) => {
      const permission = VIEW_PERMISSIONS[view];
      return !permission || hasPermission(permission);
    },
    getCurrentView: () => document.querySelector('.view.active')?.id?.replace(/-view$/, '') || defaultView(),
    rerunSafeSetups: () => {
      try {
        applyPhase2Visibility('Cadastro de Colaborador', isPhase2NavInteractivityEnabled());
        applyPhase2Visibility('Listagem de Colaboradores', isColabListHtmxPilotEnabled());
        applyPhase2Visibility('Gestão de Colaborador', isGestaoColaboradorHtmxPilotEnabled());
        applyPhase2Visibility('Cadastro de EPI', isEpiHtmxPilotEnabled());
        applyPhase2Visibility('Controle de Estoque (read-only + filtros)', isEstoqueHtmxPilotEnabled());
      } catch (error) {
        reportNonCriticalError('[multitab] applyPhase2Visibility failed', error);
      }
      try {
        setupPhase2PilotsSafely();
      } catch (error) {
        reportNonCriticalError('[multitab] setupPhase2PilotsSafely failed', error);
      }
      try {
        setupPhase29Ux();
      } catch (error) {
        reportNonCriticalError('[multitab] setupPhase29Ux failed', error);
      }
      try {
        document.dispatchEvent(new CustomEvent('epi:ux-rebind-safe', { detail: { source: 'multitab-navigation' } }));
      } catch (error) {
        reportNonCriticalError('[multitab] ux rebind dispatch failed', error);
      }
    }
  };
}


function applyPerformanceHardeningVisibility() {
  document.body?.classList.toggle('ux-performance-hardening-enabled', isUxPerformanceHardeningEnabled());
}

function closeMobileMenu() {
  document.body?.classList.remove('mobile-menu-open');
  if (refs.mobileMenuToggle) refs.mobileMenuToggle.setAttribute('aria-expanded', 'false');
}

function openMobileMenu() {
  document.body?.classList.add('mobile-menu-open');
  if (refs.mobileMenuToggle) refs.mobileMenuToggle.setAttribute('aria-expanded', 'true');
}

function applyMobileUxVisibility() {
  const enabled = isUxMobileEnabled();
  document.body?.classList.toggle('ux-mobile-enabled', enabled);
  if (!enabled) closeMobileMenu();
  // O botão ☰ passa a ser sempre visível: no mobile abre/fecha a gaveta; no
  // desktop recolhe/expande a sidebar (auditoria Navegação §6).
  if (refs.mobileMenuToggle) refs.mobileMenuToggle.hidden = false;
  applySidebarCollapsed();
}

// ── Sidebar recolhível no desktop, com preferência persistida (Navegação §6) ──
const SIDEBAR_COLLAPSED_KEY = 'epi-sidebar-collapsed';

function isSidebarCollapsedPref() {
  return safeStorageRead(SIDEBAR_COLLAPSED_KEY, '0') === '1';
}

function applySidebarCollapsed() {
  // O colapso mini-rail só se aplica fora do modo mobile (lá a sidebar é gaveta).
  const collapsed = !isUxMobileEnabled() && isSidebarCollapsedPref();
  document.body?.classList.toggle('sidebar-collapsed', collapsed);
  if (refs.mobileMenuToggle && !isUxMobileEnabled()) {
    refs.mobileMenuToggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
    refs.mobileMenuToggle.setAttribute(
      'aria-label',
      collapsed ? trEpi('nav.expandMenu', 'Expandir menu') : trEpi('nav.collapseMenu', 'Recolher menu'),
    );
  }
}

function toggleSidebarCollapsed() {
  safeStorageWrite(SIDEBAR_COLLAPSED_KEY, isSidebarCollapsedPref() ? '0' : '1');
  applySidebarCollapsed();
}

function bindMobileUxBehavior() {
  if (globalThis.__EPI_UX_MOBILE_BOUND__) return;
  globalThis.__EPI_UX_MOBILE_BOUND__ = true;

  safeOn(refs.mobileMenuToggle, 'click', () => {
    if (!isUxMobileEnabled()) { toggleSidebarCollapsed(); return; }
    if (document.body?.classList.contains('mobile-menu-open')) {
      closeMobileMenu();
      return;
    }
    openMobileMenu();
  });

  safeOn(refs.menu, 'click', (event) => {
    const menuButton = event.target?.closest?.('.menu-link[data-view]');
    if (!menuButton || !isUxMobileEnabled()) return;
    closeMobileMenu();
  });

  safeOn(document, 'click', (event) => {
    if (!isUxMobileEnabled()) return;
    if (!document.body?.classList.contains('mobile-menu-open')) return;
    const insideSidebar = event.target?.closest?.('.sidebar');
    const isToggle = event.target?.closest?.('#mobile-menu-toggle');
    if (!insideSidebar && !isToggle) closeMobileMenu();
  });

  safeOn(globalThis, 'keydown', (event) => {
    if (event?.key === 'Escape') closeMobileMenu();
  });

  safeOn(globalThis, 'popstate', () => {
    closeMobileMenu();
  });

  safeOn(document, 'epi:viewchange', (e) => {
    closeMobileMenu();
    if (e?.detail?.view === 'compras' && hasPermission('purchase_requests:view')) {
      // Approver não cria demandas, cai direto em Requisições
      const defaultTab = hasPermission('purchase_requests:create') ? 'demandas' : 'requisicoes';
      switchComprasTab(defaultTab);
    }
  });
}

function applyPhase3UiVisibility() {
  const enabled = isPhase3ModernUiEnabled();
  document.body.classList.toggle('phase3-modern-enabled', enabled);
  document.querySelectorAll('[data-phase3-screen], #phase3-colaboradores-summary, #phase3-gestao-summary, #phase3-epis-summary, #phase3-estoque-summary')
    .forEach((node) => {
      if (!node) return;
      node.hidden = !enabled;
    });
}

function updatePhase3ContextStatus(view, tone = 'neutral', message = '') {
  if (!isPhase3ModernUiEnabled()) return;
  const map = {
    dashboard: refs.phase3DashboardContextStatus,
    colaboradores: refs.phase3ColaboradoresContextStatus,
    'gestao-colaborador': refs.phase3GestaoContextStatus,
    epis: refs.phase3EpisContextStatus,
    estoque: refs.phase3EstoqueContextStatus
  };
  const node = map[view];
  if (!node) return;
  node.classList.remove('loading', 'success', 'error');
  if (tone && tone !== 'neutral') node.classList.add(tone);
  if (message) node.textContent = message;
}

function renderPhase3SummaryCards(container, items = []) {
  if (!isPhase3ModernUiEnabled() || !container) return;
  container.innerHTML = items.map((item) => (
    `<article class="phase3-summary-card"><span>${item.label}</span><strong>${item.value}</strong></article>`
  )).join('');
}

function applyRoleVisibility() {
  // Fonte única com canAccessView() (permissão + restrições estruturais +
  // visibilidade por módulo). Duplicar a regra aqui foi o bug real: o menu
  // tinha sua própria cópia da restrição de papel e nunca ganhou o cheque de
  // module_visibility quando a política de acesso por módulo foi criada —
  // a configuração do Administrador Geral mudava o dado, mas o menu não lia.
  document.querySelectorAll('.menu-link').forEach((item) => {
    const view = item.dataset.view;
    item.style.display = canAccessView(view) ? '' : 'none';
  });
  if (refs.topConfigTrigger) refs.topConfigTrigger.style.display = hasConfigurationAccess() ? '' : 'none';
  if (!hasHardeningAccess() && refs.configFrameworkForm) {
    refs.configFrameworkForm.remove();
    refs.configFrameworkForm = null;
  }
  const companyFormCard = refs.companyForm?.closest('.user-form-card');
  if (companyFormCard) companyFormCard.style.display = hasPermission('companies:create') || hasPermission('companies:update') ? '' : 'none';
  const myCompanyForm = document.getElementById('my-company-form');
  if (myCompanyForm) myCompanyForm.style.display = canConfigureMyCompany() ? '' : 'none';
  const platformBrandCard = refs.platformBrandForm?.closest('.user-form-card');
  if (platformBrandCard) platformBrandCard.style.display = state.user?.role === 'master_admin' ? '' : 'none';
  refs.profileLabel.textContent = state.user ? roleLabel(state.user.role) : 'Perfil';
  if (refs.loggedUserIdentity) {
    const parts = splitUserName(state.user?.full_name || state.user?.username || '');
    refs.loggedUserIdentity.textContent = [parts.firstName, parts.lastName].filter(Boolean).join(' ').trim();
  }
  refs.companyBadge.innerHTML = state.user?.company_name ? `${companyLogoMarkup({ name: state.user.company_name, logo_type: state.user.logo_type }, 'company-logo company-logo-sm')}<span>${state.user.company_name}<br>${state.user.company_cnpj}</span>` : 'Acesso geral';
  const masterProfileBtn = document.getElementById('master-profile-btn');
  if (masterProfileBtn) masterProfileBtn.style.display = state.user?.role === 'master_admin' ? '' : 'none';
  // P1-4 — contexto multi-tenant sempre visível no topbar (empresa/unidade ativa).
  updateTopbarCompanyBadge();
  // P1-3 — oculta rótulos de grupo da sidebar sem nenhum item visível.
  applyMenuGroupVisibility();
}

// P2-2 — toggle de tema claro/escuro (opt-in, persistido em localStorage).
// O bootstrap inline no <head> já aplica o data-theme antes do paint; aqui só
// sincronizamos o ícone/estado do botão e tratamos o clique.
function applyThemeToggleUI() {
  const btn = document.getElementById('theme-toggle');
  if (!btn) return;
  const dark = document.documentElement.getAttribute('data-theme') === 'dark';
  btn.textContent = dark ? '☀️' : '🌙';
  btn.setAttribute('aria-pressed', dark ? 'true' : 'false');
  btn.title = dark
    ? tr('theme.toDark', 'Tema escuro ativo — clique para claro')
    : tr('theme.toLight', 'Tema claro ativo — clique para escuro');
}
function setupThemeToggle() {
  const btn = document.getElementById('theme-toggle');
  if (!btn) return;
  applyThemeToggleUI();
  bindAppListener(btn, 'click', () => {
    const dark = document.documentElement.getAttribute('data-theme') === 'dark';
    if (dark) { document.documentElement.removeAttribute('data-theme'); }
    else { document.documentElement.setAttribute('data-theme', 'dark'); }
    try { localStorage.setItem('epi-theme', dark ? 'light' : 'dark'); } catch (e) { /* ignore */ }
    applyThemeToggleUI();
  });
}

// ── Painel de Configuração em Drawer (auditoria Navegação §6.2/§7) ───────────
// A engrenagem abre um drawer lateral SOBRE a tela atual (sem trocar de rota,
// preservando estado/rolagem), reaproveitando o componente dsOpenDrawer. As
// preferências (tema/idioma/densidade) só são aplicadas ao Salvar; Cancelar/
// Fechar descartam. Persistência por dispositivo (localStorage).
const SETTINGS_DENSITY_KEY = 'epi-density';
const SETTINGS_THEME_KEY = 'epi-theme';

function applyTableDensityPref() {
  const compact = safeStorageRead(SETTINGS_DENSITY_KEY, 'normal') === 'compact';
  document.body?.classList.toggle('ux-density-compact', compact);
}

function _settingsDrawerBodyHtml() {
  const theme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  const lang = (globalThis.EpiI18n && globalThis.EpiI18n.lang) || 'pt-BR';
  const density = safeStorageRead(SETTINGS_DENSITY_KEY, 'normal') === 'compact' ? 'compact' : 'normal';
  const langs = [['pt-BR', 'Português'], ['en-GB', 'English'], ['es-ES', 'Español'], ['fr-FR', 'Français'], ['nb-NO', 'Bokmål']];
  const opt = (v, cur, label) => `<option value="${v}"${v === cur ? ' selected' : ''}>${escapeHtml(label)}</option>`;
  const advanced = hasConfigurationAccess()
    ? `<button type="button" class="ghost settings-advanced" id="settings-advanced">${tr('settings.advanced', 'Configurações avançadas')}</button>`
    : '';
  return `<div class="settings-drawer">
    <label class="settings-field"><span>${tr('settings.theme', 'Tema')}</span>
      <select id="settings-theme">${opt('light', theme, tr('settings.themeLight', 'Claro'))}${opt('dark', theme, tr('settings.themeDark', 'Escuro'))}</select></label>
    <label class="settings-field"><span>${tr('settings.language', 'Idioma')}</span>
      <select id="settings-language">${langs.map(([c, n]) => opt(c, lang, n)).join('')}</select></label>
    <label class="settings-field"><span>${tr('settings.density', 'Densidade da tabela')}</span>
      <select id="settings-density">${opt('normal', density, tr('settings.densityNormal', 'Normal'))}${opt('compact', density, tr('settings.densityCompact', 'Compacta'))}</select></label>
    <p class="hint">${tr('settings.hint', 'As preferências são salvas neste dispositivo.')}</p>
    ${advanced}
  </div>`;
}

function _settingsDrawerFooterHtml() {
  return `<button type="button" class="ghost" id="settings-restore">${tr('settings.restore', 'Restaurar padrão')}</button>`
    + '<span style="flex:1"></span>'
    + `<button type="button" class="ghost" id="settings-cancel">${tr('cancel', 'Cancelar')}</button>`
    + `<button type="button" class="primary" id="settings-save">${tr('save', 'Salvar')}</button>`;
}

function _applySettings({ theme, lang, density }) {
  if (theme === 'dark') { document.documentElement.setAttribute('data-theme', 'dark'); }
  else { document.documentElement.removeAttribute('data-theme'); }
  safeStorageWrite(SETTINGS_THEME_KEY, theme === 'dark' ? 'dark' : 'light');
  if (typeof applyThemeToggleUI === 'function') { applyThemeToggleUI(); }
  document.body?.classList.toggle('ux-density-compact', density === 'compact');
  safeStorageWrite(SETTINGS_DENSITY_KEY, density === 'compact' ? 'compact' : 'normal');
  if (lang && globalThis.EpiI18n && globalThis.EpiI18n.lang !== lang && typeof globalThis.EpiI18n.setLang === 'function') {
    void globalThis.EpiI18n.setLang(lang);
  }
}

function openSettingsDrawer() {
  if (typeof globalThis.dsOpenDrawer !== 'function') {
    // Fallback (drawer indisponível): mantém o acesso à página de configuração.
    if (hasConfigurationAccess()) {
      navigateToView('configuracao', { historyMode: isSpaNavigationEnabled() ? 'push' : null, partial: false });
    }
    return;
  }
  globalThis.dsOpenDrawer({
    title: tr('settings.title', 'Configurações'),
    bodyHtml: _settingsDrawerBodyHtml(),
    footerHtml: _settingsDrawerFooterHtml(),
  });
  const root = document.getElementById('ds-drawer-root');
  if (!root) { return; }
  const val = (sel, fallback) => root.querySelector(sel)?.value || fallback;
  bindAppListener(root.querySelector('#settings-save'), 'click', () => {
    _applySettings({
      theme: val('#settings-theme', 'light'),
      lang: val('#settings-language', 'pt-BR'),
      density: val('#settings-density', 'normal'),
    });
    globalThis.dsCloseDrawer();
  });
  bindAppListener(root.querySelector('#settings-cancel'), 'click', () => globalThis.dsCloseDrawer());
  bindAppListener(root.querySelector('#settings-restore'), 'click', () => {
    // Reseta os campos para o padrão; o usuário confirma em Salvar.
    if (root.querySelector('#settings-theme')) { root.querySelector('#settings-theme').value = 'light'; }
    if (root.querySelector('#settings-language')) { root.querySelector('#settings-language').value = 'pt-BR'; }
    if (root.querySelector('#settings-density')) { root.querySelector('#settings-density').value = 'normal'; }
  });
  bindAppListener(root.querySelector('#settings-advanced'), 'click', () => {
    globalThis.dsCloseDrawer();
    navigateToView('configuracao', { historyMode: isSpaNavigationEnabled() ? 'push' : null, partial: false });
  });
}

// P1-4 — badge de empresa/unidade ativa no topbar.
function updateTopbarCompanyBadge() {
  const badge = document.getElementById('topbar-company-badge');
  if (!badge) return;
  const company = state.user?.company_name;
  const unit = state.user?.unit_name || state.user?.current_unit_name;
  if (!company) {
    badge.hidden = false;
    badge.textContent = tr('topbar.generalAccess', 'Acesso geral');
    badge.classList.add('topbar-company-badge--general');
    return;
  }
  badge.classList.remove('topbar-company-badge--general');
  badge.hidden = false;
  const label = unit ? `${company} · ${unit}` : company;
  badge.innerHTML = `<span class="topbar-company-badge__dot" aria-hidden="true"></span><span class="topbar-company-badge__text">${escapeHtml(label)}</span>`;
}

// P1-3 — um rótulo de grupo só aparece se houver ao menos um .menu-link visível
// antes do próximo rótulo. Roda após applyRoleVisibility ajustar a visibilidade.
function applyMenuGroupVisibility() {
  const menu = document.getElementById('menu');
  if (!menu) return;
  const children = Array.from(menu.children);
  let currentLabel = null;
  let groupHasVisible = false;
  const commit = () => { if (currentLabel) currentLabel.style.display = groupHasVisible ? '' : 'none'; };
  children.forEach((node) => {
    if (node.matches('[data-menu-group]')) {
      commit();
      currentLabel = node;
      groupHasVisible = false;
    } else if (node.classList.contains('menu-link') && node.style.display !== 'none') {
      groupHasVisible = true;
    }
  });
  commit();
}

function populateRoleOptions() {
  const roleKeys = {
    master_admin: ['general_admin', 'registry_admin', 'admin', 'user', 'buyer', 'approver', 'employee'],
    general_admin: ['registry_admin', 'admin', 'user', 'buyer', 'approver', 'employee'],
    registry_admin: ['admin', 'user', 'employee']
  };
  const roles = (roleKeys[state.user?.role] || []).map((k) => [k, tr('role.' + k, ROLE_LABELS[k] || k)]);
  refs.userRole.innerHTML = roles.map((item) => `<option value="${item[0]}">${item[1]}</option>`).join('');
}

function populateUserFilters() {
  if (!refs.userFilterCompany) return;
  const all = tr('user.filterAll', 'Todos');
  const companies = state.user?.role === 'master_admin' ? state.companies : filterByUserCompany(state.companies);
  const optionsHtml = companies.map((item) => `<option value="${item.id}">${item.name}</option>`).join('');
  refs.userFilterCompany.innerHTML = `<option value="">${all}</option>` + optionsHtml;
  const roleKeys = ['master_admin', 'general_admin', 'registry_admin', 'admin', 'user', 'buyer', 'approver', 'employee'];
  refs.userFilterRole.innerHTML = `<option value="">${all}</option>` +
    roleKeys.map((k) => `<option value="${k}">${tr('role.' + k, ROLE_LABELS[k] || k)}</option>`).join('');
  refs.userFilterStatus.innerHTML = `<option value="">${all}</option>` +
    `<option value="1">${tr('user.active', 'Ativo')}</option>` +
    `<option value="0">${tr('user.inactive', 'Inativo')}</option>`;
  refs.userFilterCompany.value = state.userFilters.company_id;
  refs.userFilterRole.value = state.userFilters.role;
  refs.userFilterStatus.value = state.userFilters.active;
  refs.userFilterSearch.value = state.userFilters.search;
}

function scopedCompaniesForSearch() {
  return state.user?.role === 'master_admin' ? state.companies : filterByUserCompany(state.companies);
}

function populateSearchSelect(select, items, labelBuilder, selectedValue = '', includeAll = true, emptyLabel = tr('unit.filterAllCompanies', 'Todas')) {
  if (!select) return;
  const options = includeAll ? [`<option value="">${emptyLabel}</option>`] : [];
  options.push(...items.map((item) => `<option value="${item.id}">${labelBuilder(item)}</option>`));
  select.innerHTML = options.join('');
  const normalized = String(selectedValue || '');
  if (normalized && items.some((item) => String(item.id) === normalized)) select.value = normalized;
}

function unitsForSearchByCompany(companyId = '') {
  return filterByUserCompany(state.units).filter((item) => !companyId || String(item.company_id) === String(companyId));
}

function populateScopedSearchFilters() {
  const companies = scopedCompaniesForSearch();
  const isMaster = state.user?.role === 'master_admin';
  const companyFields = [
    ['unitsFilters', refs.unitsFilterCompany],
    ['archivedUnitsFilters', refs.archivedUnitsFilterCompany],
    ['archivedEmployeesFilters', refs.archivedEmployeesFilterCompany],
    ['archivedEpisFilters', refs.archivedEpisFilterCompany],
    ['employeesFilters', refs.employeesFilterCompany],
    ['employeesOpsFilters', refs.employeesOpsFilterCompany],
    ['episFilters', refs.episFilterCompany],
    ['deliveriesFilters', refs.deliveriesFilterCompany],
    ['fichaFilters', refs.fichaFilterCompany]
  ];
  companyFields.forEach(([stateKey, field]) => {
    populateSearchSelect(field, companies, (item) => item.name, state[stateKey]?.company_id || '');
    if (field) field.disabled = !isMaster;
  });
  if (!isMaster && companies.length === 1) {
    const scopedCompanyId = String(companies[0].id);
    state.unitsFilters.company_id = scopedCompanyId;
    state.employeesFilters.company_id = scopedCompanyId;
    state.employeesOpsFilters.company_id = scopedCompanyId;
    state.episFilters.company_id = scopedCompanyId;
    state.deliveriesFilters.company_id = scopedCompanyId;
    state.fichaFilters.company_id = scopedCompanyId;
    if (refs.unitsFilterCompany) refs.unitsFilterCompany.value = scopedCompanyId;
    if (refs.employeesFilterCompany) refs.employeesFilterCompany.value = scopedCompanyId;
    if (refs.employeesOpsFilterCompany) refs.employeesOpsFilterCompany.value = scopedCompanyId;
    if (refs.episFilterCompany) refs.episFilterCompany.value = scopedCompanyId;
    if (refs.deliveriesFilterCompany) refs.deliveriesFilterCompany.value = scopedCompanyId;
    if (refs.fichaFilterCompany) refs.fichaFilterCompany.value = scopedCompanyId;
  }
  populateSearchSelect(refs.employeesFilterUnit, unitsForSearchByCompany(state.employeesFilters.company_id), (item) => item.name, state.employeesFilters.unit_id);
  populateSearchSelect(refs.employeesOpsFilterUnit, unitsForSearchByCompany(state.employeesOpsFilters.company_id), (item) => item.name, state.employeesOpsFilters.unit_id);
  populateSearchSelect(refs.episFilterUnit, unitsForSearchByCompany(state.episFilters.company_id), (item) => item.name, state.episFilters.unit_id);
  if (refs.episFilterUnit && ['general_admin', 'registry_admin'].includes(state.user?.role)) {
    if (!Array.from(refs.episFilterUnit.options).some((option) => option.value === EPI_COMPANY_LEVEL_FILTER_VALUE)) {
      refs.episFilterUnit.insertAdjacentHTML('beforeend', `<option value="${EPI_COMPANY_LEVEL_FILTER_VALUE}">Todas a nível de empresa</option>`);
    }
    if (state.episFilters.unit_id === EPI_COMPANY_LEVEL_FILTER_VALUE) refs.episFilterUnit.value = EPI_COMPANY_LEVEL_FILTER_VALUE;
  }
  syncDeliveriesOptions();
  populateSearchSelect(refs.fichaFilterUnit, unitsForSearchByCompany(state.fichaFilters.company_id), (item) => item.name, state.fichaFilters.unit_id);
  syncFichaOptions();
  if (refs.unitsFilterName) refs.unitsFilterName.value = state.unitsFilters.name;
  if (refs.unitsFilterType) refs.unitsFilterType.value = state.unitsFilters.type;
  if (refs.unitsFilterCity) refs.unitsFilterCity.value = state.unitsFilters.city;
  if (refs.employeesFilterSearch) refs.employeesFilterSearch.value = state.employeesFilters.search;
  if (refs.employeesFilterSector) refs.employeesFilterSector.value = state.employeesFilters.sector;
  if (refs.employeesFilterRole) refs.employeesFilterRole.value = state.employeesFilters.role_name;
  if (refs.employeesOpsFilterSearch) refs.employeesOpsFilterSearch.value = state.employeesOpsFilters.search;
  if (refs.employeesOpsFilterSector) refs.employeesOpsFilterSector.value = state.employeesOpsFilters.sector;
  if (refs.employeesOpsFilterRole) refs.employeesOpsFilterRole.value = state.employeesOpsFilters.role_name;
  if (refs.episFilterSearch) refs.episFilterSearch.value = state.episFilters.search;
  if (refs.episFilterProtection) refs.episFilterProtection.value = state.episFilters.protection;
  if (refs.episFilterSection) refs.episFilterSection.value = state.episFilters.section;
  if (refs.episFilterManufacturer) refs.episFilterManufacturer.value = state.episFilters.manufacturer;
  if (refs.episFilterSupplier) refs.episFilterSupplier.value = state.episFilters.supplier;
  if (refs.episFilterValidity) refs.episFilterValidity.value = state.episFilters.validity;
  if (refs.deliveriesFilterEmployee) refs.deliveriesFilterEmployee.value = state.deliveriesFilters.employee;
  if (refs.deliveriesFilterEpi) refs.deliveriesFilterEpi.value = state.deliveriesFilters.epi;
  if (refs.deliveriesFilterDateFrom) refs.deliveriesFilterDateFrom.value = state.deliveriesFilters.date_from;
  if (refs.deliveriesFilterDateTo) refs.deliveriesFilterDateTo.value = state.deliveriesFilters.date_to;
  if (refs.deliveriesFilterStatus) refs.deliveriesFilterStatus.value = state.deliveriesFilters.status;
  if (refs.fichaFilterSearch) refs.fichaFilterSearch.value = state.fichaFilters.search;
}

function syncUnitsSearchFilters() {
  state.unitsFilters.company_id = String(refs.unitsFilterCompany?.value || '').trim();
  state.unitsFilters.name = String(refs.unitsFilterName?.value || '').trim().toLowerCase();
  state.unitsFilters.type = String(refs.unitsFilterType?.value || '').trim().toLowerCase();
  state.unitsFilters.city = String(refs.unitsFilterCity?.value || '').trim().toLowerCase();
  renderTables();
}

function syncEmployeesSearchFilters(source = 'employees') {
  const isOps = source === 'ops';
  const filters = isOps ? state.employeesOpsFilters : state.employeesFilters;
  const companyField = isOps ? refs.employeesOpsFilterCompany : refs.employeesFilterCompany;
  const unitField = isOps ? refs.employeesOpsFilterUnit : refs.employeesFilterUnit;
  const searchField = isOps ? refs.employeesOpsFilterSearch : refs.employeesFilterSearch;
  const sectorField = isOps ? refs.employeesOpsFilterSector : refs.employeesFilterSector;
  const roleField = isOps ? refs.employeesOpsFilterRole : refs.employeesFilterRole;
  filters.company_id = String(companyField?.value || '').trim();
  filters.unit_id = String(unitField?.value || '').trim();
  filters.search = String(searchField?.value || '').trim().toLowerCase();
  filters.sector = String(sectorField?.value || '').trim().toLowerCase();
  filters.role_name = String(roleField?.value || '').trim().toLowerCase();
  if (isOps) populateSearchSelect(refs.employeesOpsFilterUnit, unitsForSearchByCompany(filters.company_id), (item) => item.name, filters.unit_id);
  else populateSearchSelect(refs.employeesFilterUnit, unitsForSearchByCompany(filters.company_id), (item) => item.name, filters.unit_id);
  filters.unit_id = String(unitField?.value || '').trim();
  if (!isOps && state.pagination) state.pagination.employees = 1; // volta à 1ª página ao filtrar
  renderTables();
}

function syncEpisSearchFilters() {
  state.episFilters.company_id = String(refs.episFilterCompany?.value || '').trim();
  state.episFilters.unit_id = String(refs.episFilterUnit?.value || '').trim();
  state.episFilters.search = String(refs.episFilterSearch?.value || '').trim().toLowerCase();
  state.episFilters.protection = String(refs.episFilterProtection?.value || '').trim().toLowerCase();
  state.episFilters.section = String(refs.episFilterSection?.value || '').trim().toLowerCase();
  state.episFilters.manufacturer = String(refs.episFilterManufacturer?.value || '').trim().toLowerCase();
  state.episFilters.supplier = String(refs.episFilterSupplier?.value || '').trim().toLowerCase();
  state.episFilters.validity = String(refs.episFilterValidity?.value || '').trim();
  populateSearchSelect(refs.episFilterUnit, unitsForSearchByCompany(state.episFilters.company_id), (item) => item.name, state.episFilters.unit_id);
  if (refs.episFilterUnit && ['general_admin', 'registry_admin'].includes(state.user?.role)) {
    if (!Array.from(refs.episFilterUnit.options).some((option) => option.value === EPI_COMPANY_LEVEL_FILTER_VALUE)) {
      refs.episFilterUnit.insertAdjacentHTML('beforeend', `<option value="${EPI_COMPANY_LEVEL_FILTER_VALUE}">Todas a nível de empresa</option>`);
    }
    if (state.episFilters.unit_id === EPI_COMPANY_LEVEL_FILTER_VALUE) refs.episFilterUnit.value = EPI_COMPANY_LEVEL_FILTER_VALUE;
  }
  state.episFilters.unit_id = String(refs.episFilterUnit?.value || '').trim();
  renderTables();
}

function syncDeliveriesSearchFilters() {
  state.deliveriesFilters.company_id = String(refs.deliveriesFilterCompany?.value || '').trim();
  state.deliveriesFilters.unit_id = String(refs.deliveriesFilterUnit?.value || '').trim();
  state.deliveriesFilters.employee = String(refs.deliveriesFilterEmployee?.value || '').trim().toLowerCase();
  state.deliveriesFilters.epi = String(refs.deliveriesFilterEpi?.value || '').trim().toLowerCase();
  state.deliveriesFilters.date_from = String(refs.deliveriesFilterDateFrom?.value || '').trim();
  state.deliveriesFilters.date_to = String(refs.deliveriesFilterDateTo?.value || '').trim();
  state.deliveriesFilters.status = String(refs.deliveriesFilterStatus?.value || '').trim().toLowerCase();
  syncDeliveriesOptions();
  state.deliveriesFilters.unit_id = String(refs.deliveriesFilterUnit?.value || '').trim();
  if (state.pagination) state.pagination.deliveries = 1; // volta à 1ª página ao filtrar
  renderTables();
}

// P1-7 — chips de filtros ativos da tabela de Entregas. Cobre apenas filtros
// opcionais do usuário (colaborador, EPI, datas, status) — nunca os de escopo
// multi-tenant (empresa/unidade), para não permitir burlar a delimitação.
const DELIVERIES_CHIP_REFS = {
  employee: 'deliveriesFilterEmployee',
  epi: 'deliveriesFilterEpi',
  date_from: 'deliveriesFilterDateFrom',
  date_to: 'deliveriesFilterDateTo',
  status: 'deliveriesFilterStatus'
};

function renderDeliveriesFilterChips() {
  const container = document.getElementById('deliveries-filter-chips');
  if (!container) return;
  const f = state.deliveriesFilters || {};
  const selText = (ref) => ref?.selectedOptions?.[0]?.textContent?.trim() || '';
  const items = [];
  if (f.employee) items.push({ key: 'employee', label: `${tr('employee.singleTitle', 'Colaborador')}: ${f.employee}` });
  if (f.epi) items.push({ key: 'epi', label: `${tr('epi.title', 'EPI')}: ${f.epi}` });
  if (f.date_from) items.push({ key: 'date_from', label: `${tr('delivery.startDate', 'Data inicial')}: ${f.date_from}` });
  if (f.date_to) items.push({ key: 'date_to', label: `${tr('delivery.endDate', 'Data final')}: ${f.date_to}` });
  if (f.status) items.push({ key: 'status', label: `${tr('delivery.status', 'Status')}: ${selText(refs.deliveriesFilterStatus) || f.status}` });
  container.innerHTML = globalThis.dsFilterChips(items);
}

// P2-1 — drawer de detalhes da entrega (sem mudar de rota). Reusa dados já
// carregados em state.deliveries; renderiza com escape e o pipeline de status.
function openDeliveryDetailDrawer(deliveryId) {
  const item = (state.deliveries || []).find((d) => String(d.id) === String(deliveryId));
  if (!item || typeof globalThis.dsOpenDrawer !== 'function') return;
  const esc = globalThis.dsEsc || ((v) => String(v == null ? '' : v));
  const devolvido = String(item.returned_date || '').trim();
  const statusKey = devolvido ? 'entregue' : (item.signature_data ? 'assinado' : 'entregue');
  const pipeline = typeof globalThis.dsStatusPipeline === 'function'
    ? globalThis.dsStatusPipeline([
      { key: 'solicitado', label: tr('portal.statusRequested', 'Solicitado') },
      { key: 'aprovado', label: tr('portal.statusApproved', 'Aprovado') },
      { key: 'entregue', label: tr('delivery.delivered', 'Entregue') },
      { key: 'assinado', label: tr('delivery.signed', 'Assinado') }
    ], statusKey)
    : '';
  const row = (label, value) => `<div style="display:flex;justify-content:space-between;gap:12px;padding:8px 0;border-bottom:1px solid var(--color-border);"><span style="color:var(--color-text-muted);">${esc(label)}</span><strong style="text-align:right;">${esc(value || '—')}</strong></div>`;
  const body = `<div style="margin-bottom:14px;">${pipeline}</div>`
    + row(tr('employee.company', 'Empresa'), item.company_name)
    + row(tr('employee.singleTitle', 'Colaborador'), `${item.employee_name || ''} (${item.employee_id_code || '—'})`)
    + row(tr('epi.title', 'EPI'), item.epi_name)
    + row(tr('delivery.size', 'Tamanho'), formatItemSizeDisplay(item))
    + row(tr('stock.qtyShort', 'Qtd'), `${item.quantity || ''} ${item.quantity_label || ''}`)
    + row(tr('delivery.deliveryDate', 'Data Entrega'), formatDate(item.delivery_date))
    + row(tr('delivery.nextReplacementReturn', 'Próx. Troca / Devolução'), devolvido ? `↩ ${formatDate(item.returned_date)}` : (formatDate(item.next_replacement_date) || '—'));
  globalThis.dsOpenDrawer({ title: `${tr('delivery.details', 'Detalhes')} — ${esc(item.epi_name || '')}`, bodyHtml: body });
}

function clearDeliveriesFilterChip(key) {
  if (key === 'all') {
    Object.values(DELIVERIES_CHIP_REFS).forEach((refName) => { if (refs[refName]) refs[refName].value = ''; });
  } else {
    const refName = DELIVERIES_CHIP_REFS[key];
    if (refName && refs[refName]) refs[refName].value = '';
  }
  syncDeliveriesSearchFilters();
}

function syncFichaSearchFilters() {
  syncFichaOptions();
  state.fichaFilters.company_id = String(refs.fichaFilterCompany?.value || '').trim();
  state.fichaFilters.unit_id = String(refs.fichaFilterUnit?.value || '').trim();
  state.fichaFilters.search = String(refs.fichaFilterSearch?.value || '').trim().toLowerCase();
  populateSearchSelect(refs.fichaFilterUnit, unitsForSearchByCompany(state.fichaFilters.company_id), (item) => item.name, state.fichaFilters.unit_id);
  syncFichaOptions();
  state.fichaFilters.unit_id = String(refs.fichaFilterUnit?.value || '').trim();
  renderFicha();
}

function syncFichaOptions() {
  const companyField = refs.fichaFilterCompany;
  const unitField = refs.fichaFilterUnit;
  const unitHint = document.getElementById('ficha-unit-hint');
  if (!companyField || !unitField) return;
  const lockByOperationalProfile = isOperationalProfile();
  const operationalUnitId = String(state.user?.operational_unit_id || '').trim();
  if (lockByOperationalProfile && state.user?.company_id) {
    companyField.value = String(state.user.company_id);
    state.fichaFilters.company_id = String(state.user.company_id);
  }
  const companyId = String(companyField.value || state.user?.company_id || '').trim();
  let units = filterByUserCompany(state.units).filter((item) => !companyId || String(item.company_id) === String(companyId));
  if (lockByOperationalProfile && !operationalUnitId) units = [];
  if (lockByOperationalProfile && operationalUnitId) {
    units = units.filter((item) => String(item.id) === operationalUnitId);
  }
  const previousUnit = String(unitField.value || '');
  unitField.innerHTML = `${lockByOperationalProfile ? '' : `<option value="">${tr('employee.filterAllUnits', 'Todas')}</option>`}${units.map(formatUnitOption).join('')}`;
  if (!units.length) {
    unitField.innerHTML = '<option value="">Sem unidade operacional ativa</option>';
    unitField.value = '';
  } else if (lockByOperationalProfile) {
    unitField.value = String(units[0].id);
  } else if (previousUnit && units.some((item) => String(item.id) === previousUnit)) {
    unitField.value = previousUnit;
  }
  companyField.disabled = lockByOperationalProfile;
  unitField.disabled = lockByOperationalProfile;
  if (unitHint) unitHint.style.display = lockByOperationalProfile ? 'block' : 'none';
  if (lockByOperationalProfile) {
    state.fichaFilters.unit_id = String(unitField.value || '');
  }
}

function syncDeliveriesOptions() {
  const companyField = refs.deliveriesFilterCompany;
  const unitField = refs.deliveriesFilterUnit;
  const unitHint = document.getElementById('deliveries-unit-hint');
  if (!companyField || !unitField) return;
  const lockByOperationalProfile = isOperationalProfile();
  const operationalUnitId = String(state.user?.operational_unit_id || '').trim();
  if (lockByOperationalProfile && state.user?.company_id) {
    companyField.value = String(state.user.company_id);
    state.deliveriesFilters.company_id = String(state.user.company_id);
  }
  const companyId = String(companyField.value || state.user?.company_id || '').trim();
  let units = filterByUserCompany(state.units).filter((item) => !companyId || String(item.company_id) === String(companyId));
  if (lockByOperationalProfile && !operationalUnitId) units = [];
  if (lockByOperationalProfile && operationalUnitId) {
    units = units.filter((item) => String(item.id) === operationalUnitId);
  }
  const previousUnit = String(unitField.value || '');
  unitField.innerHTML = `${lockByOperationalProfile ? '' : `<option value="">${tr('employee.filterAllUnits', 'Todas')}</option>`}${units.map(formatUnitOption).join('')}`;
  if (!units.length) {
    unitField.innerHTML = '<option value="">Sem unidade operacional ativa</option>';
    unitField.value = '';
  } else if (lockByOperationalProfile) {
    unitField.value = String(units[0].id);
  } else if (previousUnit && units.some((item) => String(item.id) === previousUnit)) {
    unitField.value = previousUnit;
  }
  companyField.disabled = lockByOperationalProfile;
  unitField.disabled = lockByOperationalProfile;
  if (unitHint) unitHint.style.display = lockByOperationalProfile ? 'block' : 'none';
  if (lockByOperationalProfile) {
    state.deliveriesFilters.unit_id = String(unitField.value || '');
  }
}

function renderUsersSummary() {
  const visible = filteredUsers();
  const admins = visible.filter((item) => ['master_admin', 'general_admin', 'admin'].includes(item.role)).length;
  const active = visible.filter((item) => Number(item.active) === 1).length;
  refs.usersSummary.innerHTML = [
    [tr('user.kpiVisible', 'Visíveis'), visible.length],
    [tr('user.kpiAdmins', 'Administradores'), admins],
    [tr('user.kpiActive', 'Ativos'), active]
  ].map((item) => `<div class="summary-chip"><strong>${item[1]}</strong><span>${item[0]}</span></div>`).join('');
}

function renderCompaniesSummary() {
  if (!refs.companiesSummary) return;
  const visibleCompanies = filterByUserCompany(state.companies);
  const active = visibleCompanies.filter((item) => Number(item.active) === 1).length;
  const nearLimit = visibleCompanies.filter((item) => item.near_limit && Number(item.limit_reached) !== 1).length;
  const blocked = visibleCompanies.filter((item) => Number(item.active) !== 1 || ['suspended', 'expired'].includes(item.license_status)).length;
  refs.companiesSummary.innerHTML = [
    [tr('company.kpiTotal', 'Empresas'), visibleCompanies.length],
    [tr('company.kpiActive', 'Ativas'), active],
    [tr('company.kpiNearLimit', 'Próximas do limite'), nearLimit],
    [tr('company.kpiBlocked', 'Bloqueadas'), blocked]
  ].map((item) => `<div class="summary-chip"><strong>${item[1]}</strong><span>${item[0]}</span></div>`).join('');
}

function companyStatusBadges(company) {
  const badges = [renderBadge('status', Number(company.active) === 1 ? 'active' : 'inactive', Number(company.active) === 1 ? tr('company.statusActive', 'Empresa ativa') : tr('company.statusInactive', 'Empresa inativa'))];

  let licenseTone = 'inactive';
  if (company.license_status === 'active') licenseTone = 'active';
  else if (company.license_status === 'trial') licenseTone = 'warning';

  badges.push(renderBadge('status', licenseTone, tr(`license.${company.license_status}`, company.license_status_label || company.license_status)));
  if (Number(company.limit_reached) === 1) badges.push(renderBadge('status', 'inactive', tr('commercial.risk.atLimit', 'No limite')));
  else if (company.near_limit) badges.push(renderBadge('status', 'warning', tr('commercial.risk.nearLimit', 'Próxima do limite')));
  return badges.join(' ');
}

function companyUsageText(company) {
  return `${company.user_count} faturável(eis) de ${company.user_limit} contratado(s)`;
}

function formatCompanyCurrency(value) {
  return formatCurrency(value || 0);
}

function formatCompanyAvailabilityText(company) {
  return Number(company.limit_reached) === 1
    ? tr('company.limitReached', 'Limite atingido')
    : tr('company.availableSlotsText', '{count} vaga(s) disponíveis').replace('{count}', company.available_slots || 0);
}

function renderCompanyDetails(companyId = null) {
  if (!refs.companyDetails) return;
  const visibleCompanies = filterByUserCompany(state.companies);
  if (!visibleCompanies.length) {
    refs.companyDetails.innerHTML = `<div class="summary-item">${tr('company.noCompanySelected', 'Nenhuma empresa disponível.')}</div>`;
    return;
  }
  const selected = visibleCompanies.find((item) => String(item.id) === String(companyId || state.selectedCompanyId)) || visibleCompanies[0];
  state.selectedCompanyId = selected.id;
  const monthly = formatCompanyCurrency(selected.monthly_value);
  const projected = formatCompanyCurrency(selected.projected_monthly_value);
  const cnpjLabel = tr('company.cnpjLabel', 'CNPJ');
  const validityRange = tr('company.validityRange', '{start} até {end}')
    .replace('{start}', formatDate(selected.contract_start))
    .replace('{end}', formatDate(selected.contract_end));
  refs.companyDetails.innerHTML = `
    <div class="company-detail-hero">
      ${companyLogoMarkup(selected, 'company-logo company-logo-lg')}
      <div>
        <strong>${selected.name}</strong>
        <span>${selected.legal_name || '-'}</span>
        <span>${cnpjLabel}: ${selected.cnpj}</span>
      </div>
    </div>
    <div class="company-detail-badges">${companyStatusBadges(selected)}</div>
    <div class="company-detail-grid">
      <div class="summary-chip"><strong>${selected.user_count ?? '—'}</strong><span>${tr('company.possibleUsers', 'Usuários possíveis')}</span></div>
      <div class="summary-chip"><strong>${selected.user_limit ?? '—'}</strong><span>${tr('company.contractedLimit', 'Limite contratado')}</span></div>
      <div class="summary-chip"><strong>${monthly}</strong><span>${tr('company.monthlyValue', 'Valor mensal atual')}</span></div>
      <div class="summary-chip"><strong>${projected}</strong><span>${tr('company.projectedValue', 'Valor projetado')}</span></div>
      <div class="summary-chip"><strong>${selected.available_slots ?? 0}</strong><span>${tr('company.availableSlots', 'Vagas disponíveis')}</span></div>
    </div>
    <div class="company-detail-list">
      <div class="summary-item"><strong>${tr('company.planLabel', 'Plano / licença')}:</strong> ${planLabel(selected.plan_name) || '-'}</div>
      <div class="summary-item"><strong>${tr('company.unitPrice', 'Valor unitário')}:</strong> ${formatCompanyCurrency(selected.unit_price)}</div>
      <div class="summary-item"><strong>${tr('company.validity', 'Vigência')}:</strong> ${validityRange}</div>
      <div class="summary-item"><strong>${tr('company.addendum', 'Aditivo contratual')}:</strong> ${Number(selected.addendum_enabled || 0) === 1 ? tr('user.active', 'Ativo') : tr('user.inactive', 'Inativo')}</div>
      <div class="summary-item"><strong>${tr('company.commercialNotes', 'Observações comerciais')}:</strong> ${selected.commercial_notes || '-'}</div>
    </div>
    ${canAccessCommercialArea() ? `<div class="action-group"><button class="ghost" type="button" data-company-view-contract="${selected.id}">${tr('company.viewContract', 'Visualizar contrato')}</button></div>` : ''}`;
}

function filteredCommercialCompanies() {
  const companies = filterByUserCompany(state.companies);
  if (!state.commercialFilters.status) return companies;
  return companies.filter((item) => item.license_status === state.commercialFilters.status);
}

function filteredCommercialLogs() {
  const selectedCompanyId = refs.commercialCompany?.value || '';
  return state.companyAuditLogs.filter((item) => {
    if (selectedCompanyId && String(item.company_id) !== String(selectedCompanyId)) return false;
    if (state.commercialFilters.actor_name && item.actor_name !== state.commercialFilters.actor_name) return false;
    const day = String(item.created_at || '').slice(0, 10);
    if (state.commercialFilters.date_from && day < state.commercialFilters.date_from) return false;
    if (state.commercialFilters.date_to && day > state.commercialFilters.date_to) return false;
    return true;
  });
}

function daysUntil(dateValue) {
  if (!dateValue) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(`${dateValue}T00:00:00`);
  return Math.round((target - today) / 86400000);
}

function fillCommercialSettingsForm() {
  if (!refs.commercialSettingsForm) return;
  const settings = getCommercialSettings();
  refs.commercialSettingsForm.elements.unit_price.value = settings.unit_price ?? 42;
  refs.commercialSettingsForm.elements.individual_max.value = settings.plans.individual.max_users ?? 1;
  refs.commercialSettingsForm.elements.start_max.value = settings.plans.start.max_users ?? 10;
  refs.commercialSettingsForm.elements.business_max.value = settings.plans.business.max_users ?? 25;
  refs.commercialSettingsForm.elements.corporate_max.value = settings.plans.corporate.max_users ?? 100;
  refs.commercialSettingsForm.elements.enterprise_min.value = settings.plans.enterprise.min_users ?? 101;
}

function refreshCommercialPreview(company = null) {
  if (!refs.commercialForm) return;
  const currentCompany = company || state.companies.find((item) => String(item.id) === String(refs.commercialCompany?.value || ''));
  const unitPrice = Number(getCommercialSettings().unit_price || 0);
  const activeUsers = Number(currentCompany?.user_count || 0);
  const userLimit = Number(refs.commercialForm.elements.user_limit.value || currentCompany?.user_limit || 0);
  const planName = refs.commercialForm.elements.plan_name.value || currentCompany?.plan_name || 'start';
  const addendumEnabled = refs.commercialForm.elements.addendum_enabled.checked;
  refs.commercialForm.elements.unit_price_display.value = formatCurrency(unitPrice);
  refs.commercialForm.elements.monthly_value.value = formatCurrency(activeUsers * unitPrice);
  refs.commercialForm.elements.projected_monthly_value.value = formatCurrency(userLimit * unitPrice);
  if (refs.commercialPlanHint) refs.commercialPlanHint.textContent = planHintText(planName, addendumEnabled);
}

function fillCommercialForm(companyId) {
  if (!refs.commercialForm || !refs.commercialCompany) return;
  const visibleCompanies = filterByUserCompany(state.companies);
  refs.commercialCompany.innerHTML = visibleCompanies.map((item) => `<option value="${item.id}">${item.name}</option>`).join('');
  refs.commercialForm.elements.plan_name.innerHTML = planOptionMarkup();
  const selected = visibleCompanies.find((item) => String(item.id) === String(companyId || refs.commercialCompany.value)) || visibleCompanies[0];
  if (!selected) return;
  refs.commercialCompany.value = selected.id;
  refs.commercialForm.elements.company_id.value = selected.id;
  refs.commercialForm.elements.plan_name.value = selected.plan_name || 'start';
  refs.commercialForm.elements.user_limit.value = selected.user_limit || 1;
  refs.commercialForm.elements.addendum_enabled.checked = Number(selected.addendum_enabled || 0) === 1;
  refs.commercialForm.elements.contract_start.value = selected.contract_start || '';
  refs.commercialForm.elements.contract_end.value = selected.contract_end || '';
  refs.commercialForm.elements.license_status.value = selected.license_status || 'active';
  refs.commercialForm.elements.active.value = String(Number(selected.active || 1));
  refs.commercialForm.elements.commercial_notes.value = selected.commercial_notes || '';
  refreshCommercialPreview(selected);
  resetCommercialContractForm({ preserveClauses: true });
  if (canAccessCommercialArea()) loadCommercialContract(selected.id);
}

function contractStatusLabel(status) {
  const labels = {
    draft: 'Rascunho',
    generated: 'Gerado',
    sent: 'Enviado',
    pending_signature: 'Pendente de assinatura',
    signed: 'Assinado',
    active: 'Ativo',
    closed: 'Encerrado',
    archived: 'Arquivado'
  };
  return labels[String(status || '').toLowerCase()] || (status || 'Rascunho');
}

function renderCommercialContractPanel() {
  const contract = state.commercialContract;
  if (!contract) return;
  if (refs.commercialContractStatus) refs.commercialContractStatus.textContent = `Status do contrato: ${contractStatusLabel(contract.status)}`;
  if (refs.commercialContractNumber) refs.commercialContractNumber.value = contract.contract_number || '';
  if (refs.commercialContractIssueDate) refs.commercialContractIssueDate.value = contract.issue_date || '';
  if (refs.commercialContractorAddress) refs.commercialContractorAddress.value = contract.contractor_address || '';
  if (refs.commercialContractorRepresentative) refs.commercialContractorRepresentative.value = contract.contractor_representative || '';
  if (refs.commercialContractorRole) refs.commercialContractorRole.value = contract.contractor_representative_role || '';
  if (refs.commercialContractorEmail) refs.commercialContractorEmail.value = contract.contractor_email || '';
  if (refs.commercialContractorPhone) refs.commercialContractorPhone.value = contract.contractor_phone || '';
  if (refs.commercialContractorW1) refs.commercialContractorW1.value = contract.contractor_witness_1 || '';
  if (refs.commercialContractorW2) refs.commercialContractorW2.value = contract.contractor_witness_2 || '';
  if (refs.commercialProviderName) refs.commercialProviderName.value = contract.provider_name || '';
  if (refs.commercialProviderLegalName) refs.commercialProviderLegalName.value = contract.provider_legal_name || '';
  if (refs.commercialProviderCnpj) refs.commercialProviderCnpj.value = contract.provider_cnpj || '';
  if (refs.commercialProviderAddress) refs.commercialProviderAddress.value = contract.provider_address || '';
  if (refs.commercialProviderRepresentative) refs.commercialProviderRepresentative.value = contract.provider_representative || '';
  if (refs.commercialProviderRole) refs.commercialProviderRole.value = contract.provider_representative_role || '';
  if (refs.commercialProviderEmail) refs.commercialProviderEmail.value = contract.provider_email || '';
  if (refs.commercialProviderPhone) refs.commercialProviderPhone.value = contract.provider_phone || '';
  if (refs.commercialProviderWitnesses) refs.commercialProviderWitnesses.value = contract.provider_witnesses || '';
  if (refs.commercialContractClauses) {
    const clausesValue = contract.clauses_text || state.commercialClauseTemplate || refs.commercialContractClauses.value || '';
    refs.commercialContractClauses.value = clausesValue;
    state.commercialClauseTemplate = clausesValue;
  }
  if (refs.commercialEmailTo) refs.commercialEmailTo.value = contract.last_email_to || contract.contractor_email || '';
  if (refs.commercialEmailSubject) refs.commercialEmailSubject.value = contract.last_email_subject || 'Contrato comercial EPI Controle';
  if (refs.commercialEmailBody) refs.commercialEmailBody.value = contract.last_email_body || 'Segue contrato comercial para análise e assinatura.';
  if (refs.commercialContractEvents) {
    refs.commercialContractEvents.innerHTML = (contract.events || []).map((event) => `<div class="summary-item"><strong>${event.event_type}</strong><div>${formatDateTime(event.created_at)}</div></div>`).join('') || '<div class="summary-item">Sem histórico de contrato.</div>';
  }
}

function resetCommercialContractForm({ preserveClauses = true } = {}) {
  const clauses = preserveClauses ? (refs.commercialContractClauses?.value || state.commercialClauseTemplate || '') : '';
  if (refs.commercialContractStatus) refs.commercialContractStatus.textContent = 'Status do contrato: Rascunho';
  if (refs.commercialContractNumber) refs.commercialContractNumber.value = '';
  if (refs.commercialContractIssueDate) refs.commercialContractIssueDate.value = '';
  if (refs.commercialContractorAddress) refs.commercialContractorAddress.value = '';
  if (refs.commercialContractorRepresentative) refs.commercialContractorRepresentative.value = '';
  if (refs.commercialContractorRole) refs.commercialContractorRole.value = '';
  if (refs.commercialContractorEmail) refs.commercialContractorEmail.value = '';
  if (refs.commercialContractorPhone) refs.commercialContractorPhone.value = '';
  if (refs.commercialContractorW1) refs.commercialContractorW1.value = '';
  if (refs.commercialContractorW2) refs.commercialContractorW2.value = '';
  if (refs.commercialProviderName) refs.commercialProviderName.value = '';
  if (refs.commercialProviderLegalName) refs.commercialProviderLegalName.value = '';
  if (refs.commercialProviderCnpj) refs.commercialProviderCnpj.value = '';
  if (refs.commercialProviderAddress) refs.commercialProviderAddress.value = '';
  if (refs.commercialProviderRepresentative) refs.commercialProviderRepresentative.value = '';
  if (refs.commercialProviderRole) refs.commercialProviderRole.value = '';
  if (refs.commercialProviderEmail) refs.commercialProviderEmail.value = '';
  if (refs.commercialProviderPhone) refs.commercialProviderPhone.value = '';
  if (refs.commercialProviderWitnesses) refs.commercialProviderWitnesses.value = '';
  if (refs.commercialContractClauses) refs.commercialContractClauses.value = clauses;
  if (refs.commercialSignatureName) refs.commercialSignatureName.value = '';
  if (refs.commercialSignatureData) refs.commercialSignatureData.value = '';
  if (refs.commercialEmailTo) refs.commercialEmailTo.value = '';
  if (refs.commercialEmailSubject) refs.commercialEmailSubject.value = 'Contrato comercial EPI Controle';
  if (refs.commercialEmailBody) refs.commercialEmailBody.value = 'Segue contrato comercial para análise e assinatura.';
  if (refs.commercialSignedFile) refs.commercialSignedFile.value = '';
  if (refs.commercialContractEvents) refs.commercialContractEvents.innerHTML = '<div class="summary-item">Sem histórico de contrato.</div>';
  state.commercialContract = null;
  state.commercialClauseTemplate = clauses;
}

async function loadCommercialContract(companyId) {
  if (!companyId || !refs.commercialForm || !canAccessCommercialArea()) return;
  try {
    const payload = await api(`/api/commercial-contract?actor_user_id=${state.user.id}&company_id=${companyId}`);
    state.commercialContract = payload.contract || null;
    renderCommercialContractPanel();
  } catch (error) {
    if (error?.status === 403) {
      resetCommercialContractForm({ preserveClauses: true });
      return;
    }
    console.warn('[commercial-contract] Não foi possível carregar contrato', error);
  }
}

function buildCommercialContractPayload() {
  const companyId = refs.commercialCompany?.value;
  const company = state.companies.find((item) => String(item.id) === String(companyId));
  return {
    actor_user_id: state.user.id,
    company_id: Number(companyId || 0),
    contract_number: refs.commercialContractNumber?.value || '',
    issue_date: refs.commercialContractIssueDate?.value || '',
    start_date: refs.commercialForm?.elements.contract_start?.value || company?.contract_start || '',
    end_date: refs.commercialForm?.elements.contract_end?.value || company?.contract_end || '',
    status: state.commercialContract?.status || 'draft',
    contractor_name: company?.name || '',
    contractor_legal_name: company?.legal_name || '',
    contractor_trade_name: company?.name || '',
    contractor_cnpj: company?.cnpj || '',
    contractor_address: refs.commercialContractorAddress?.value || '',
    contractor_representative: refs.commercialContractorRepresentative?.value || '',
    contractor_representative_role: refs.commercialContractorRole?.value || '',
    contractor_email: refs.commercialContractorEmail?.value || '',
    contractor_phone: refs.commercialContractorPhone?.value || '',
    contractor_witness_1: refs.commercialContractorW1?.value || '',
    contractor_witness_2: refs.commercialContractorW2?.value || '',
    provider_name: refs.commercialProviderName?.value || '',
    provider_legal_name: refs.commercialProviderLegalName?.value || '',
    provider_cnpj: refs.commercialProviderCnpj?.value || '',
    provider_address: refs.commercialProviderAddress?.value || '',
    provider_representative: refs.commercialProviderRepresentative?.value || '',
    provider_representative_role: refs.commercialProviderRole?.value || '',
    provider_email: refs.commercialProviderEmail?.value || '',
    provider_phone: refs.commercialProviderPhone?.value || '',
    provider_witnesses: refs.commercialProviderWitnesses?.value || '',
    clauses_text: refs.commercialContractClauses?.value || '',
    notes: refs.commercialForm?.elements.commercial_notes?.value || ''
  };
}

function commercialRiskMeta(company) {
  if (Number(company.active) !== 1) return { label: tr('commercial.risk.inactiveCompany', 'Empresa inativa'), tone: 'inactive' };
  if (company.license_status === 'expired') return { label: tr('commercial.risk.contractExpired', 'Contrato expirado'), tone: 'inactive' };
  if (company.license_status === 'suspended') return { label: tr('commercial.risk.contractSuspended', 'Contrato suspenso'), tone: 'inactive' };
  if (Number(company.limit_reached) === 1) return { label: tr('commercial.risk.atLimit', 'No limite'), tone: 'inactive' };
  if (company.near_limit) return { label: tr('commercial.risk.nearLimit', 'Próxima do limite'), tone: 'warning' };
  return { label: tr('commercial.risk.healthy', 'Saudável'), tone: 'active' };
}

function commercialActions(company) {
  if (!hasPermission('companies:update')) return '';
  const canReactivate = company.license_status === 'suspended' || company.license_status === 'expired' || Number(company.active) !== 1;
  const actionMode = canReactivate ? 'reactivate' : 'suspend';
  const toggleLabel = canReactivate ? 'Reativar' : 'Suspender';
  return `<div class="action-group commercial-actions"><button class="ghost" data-company-commercial="${company.id}">Abrir contrato</button><button class="ghost" data-commercial-toggle="${company.id}" data-commercial-mode="${actionMode}">${toggleLabel}</button></div>`;
}

function commercialAlertTone(item) {
  return Number(item.limit_reached) === 1 || item.license_status === 'expired' ? 'danger' : 'warning';
}

function renderCommercialSummaryCard(item) {
  const usage = `${item.user_count}/${item.user_limit}`;
  const monthly = formatCurrency(item.monthly_value || 0);
  const projected = formatCurrency(item.projected_monthly_value || 0);
  const risk = commercialRiskMeta(item);
  return `<div class="commercial-card"><div class="commercial-row">${companyLogoMarkup(item, 'company-logo company-logo-sm')}<div><strong>${item.name}</strong><span>${tr('commercial.usersCount', '{count} Usuários').replace('{count}', usage)}</span><span>${monthly} ${tr('commercial.currentLabel', 'atual')} | ${projected} ${tr('commercial.projectedLabel', 'projetado')}</span><span>${planLabel(item.plan_name)}</span></div><span class="badge badge-status-${risk.tone}">${risk.label}</span></div>${commercialActions(item)}</div>`;
}

function renderCommercialAlertCard(item) {
  const reasons = [];
  if (Number(item.limit_reached) === 1) reasons.push(tr('commercial.limitReachedAlert', 'limite contratado atingido'));
  else if (item.near_limit) reasons.push(tr('commercial.nearLimitAlert', 'próxima do limite contratado'));
  if (['suspended', 'expired'].includes(item.license_status)) reasons.push(tr(`license.${item.license_status}`, item.license_status_label || item.license_status));
  if (Number(item.active) !== 1) reasons.push(tr('commercial.inactiveAlert', 'empresa inativa'));
  const tone = commercialAlertTone(item);
  return `<div class="commercial-card"><div class="alert-item ${tone}"><strong>${item.name}</strong><div>${reasons.join(' | ')}</div></div>${commercialActions(item)}</div>`;
}

function renderCommercialExpiringCard(entry) {
  const { item, days } = entry;
  const badgeTone = days <= 7 ? 'inactive' : 'warning';
  const badgeLabel = days <= 7 ? tr('commercial.urgentBadge', 'Urgente') : tr('commercial.monitorBadge', 'Acompanhar');
  const expiresText = tr('commercial.expiresOn', 'Vence em {date}').replace('{date}', formatDate(item.contract_end));
  const remainingText = tr('commercial.daysRemaining', '{days} dia(s) restantes').replace('{days}', days);
  return `<div class="commercial-card"><div class="commercial-row">${companyLogoMarkup(item, 'company-logo company-logo-sm')}<div><strong>${item.name}</strong><span>${expiresText}</span><span>${remainingText}</span></div><span class="badge badge-status-${badgeTone}">${badgeLabel}</span></div>${commercialActions(item)}</div>`;
}

async function toggleCommercialStatus(companyId, mode) {
  const company = state.companies.find((item) => String(item.id) === String(companyId));
  if (!company || !hasPermission('companies:update')) return;
  const next = mode === 'reactivate'
    ? { active: 1, license_status: 'active' }
    : { active: 0, license_status: 'suspended' };
  try {
    await api(`/api/companies/${company.id}`, {
      method: 'PUT',
      body: JSON.stringify({
        actor_user_id: state.user.id,
        name: company.name,
        legal_name: company.legal_name,
        cnpj: company.cnpj,
        logo_type: company.logo_type || '',
        plan_name: company.plan_name,
        user_limit: company.user_limit,
        contract_start: company.contract_start || '',
        contract_end: company.contract_end || '',
        monthly_value: company.monthly_value || 0,
        addendum_enabled: company.addendum_enabled || 0,
        license_status: next.license_status,
        active: next.active,
        commercial_notes: company.commercial_notes || ''
      })
    });
    await loadBootstrap();
    fillCommercialForm(company.id);
  } catch (error) { alert(error.message); }
}

function renderCommercialStats() {
  if (!refs.commercialStats) return;
  const companies = filterByUserCompany(state.companies);
  const monthlyTotal = companies.reduce((total, item) => total + Number(item.monthly_value || 0), 0);
  const activeCount = companies.filter((item) => item.license_status === 'active').length;
  const suspendedCount = companies.filter((item) => item.license_status === 'suspended').length;
  const expiredCount = companies.filter((item) => item.license_status === 'expired').length;
  refs.commercialStats.innerHTML = [
    ['Faturamento mensal', monthlyTotal.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })],
    ['Empresas ativas', activeCount],
    ['Suspensas', suspendedCount],
    ['Expiradas', expiredCount]
  ].map((item) => `<article class="stat-card"><div class="stat-label">${item[0]}</div><div class="stat-value">${item[1]}</div></article>`).join('');
}

function renderCommercialSummary() {
  if (!refs.commercialSummary) return;
  const companies = filteredCommercialCompanies();
  refs.commercialSummary.innerHTML = companies.map(renderCommercialSummaryCard).join('') || '<div class="summary-item">Sem empresas cadastradas.</div>';
}

function renderCommercialAlerts() {
  if (!refs.commercialAlerts) return;
  const alerts = filteredCommercialCompanies().filter((item) => Number(item.limit_reached) === 1 || item.near_limit || ['suspended', 'expired'].includes(item.license_status) || Number(item.active) !== 1);
  refs.commercialAlerts.innerHTML = alerts.map(renderCommercialAlertCard).join('') || '<div class="summary-item">Nenhuma empresa em alerta comercial.</div>';
}

function formatCommercialAuditDetails(details) {
  const detailsHtml = (details || []).map((detail) => `<div class="audit-detail-row"><strong>${detail.field}</strong><span>${detail.before || '-'} -> ${detail.after || '-'}</span></div>`).join('');
  return detailsHtml ? `<div class="audit-details">${detailsHtml}</div>` : '';
}

function renderCommercialHistoryItem(item) {
  const createdAt = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(item.created_at));
  return `<div class="commercial-card"><div class="commercial-row"><div class="company-logo company-logo-sm"></div><div><strong>${item.company_name}</strong><span>${item.action_label} por ${item.actor_name}</span><span>${createdAt}</span></div><span class="badge badge-status-active">${item.action_label}</span></div><div class="summary-item">${item.summary}</div>${formatCommercialAuditDetails(item.details)}</div>`;
}

function renderCommercialHistory() {
  if (!refs.commercialHistory) return;
  const logs = filteredCommercialLogs();
  refs.commercialHistory.innerHTML = logs.slice(0, 12).map(renderCommercialHistoryItem).join('') || '<div class="summary-item">Sem Histórico comercial registrado.</div>';
}

function renderCommercialExpiring() {
  if (!refs.commercialExpiring) return;
  const expiring = filterByUserCompany(state.companies)
    .map((item) => ({ item, days: daysUntil(item.contract_end) }))
    .filter((entry) => entry.days !== null && entry.days >= 0 && entry.days <= 30)
    .sort((a, b) => a.days - b.days);
  refs.commercialExpiring.innerHTML = expiring.map(renderCommercialExpiringCard).join('') || '<div class="summary-item">Nenhum contrato vencendo nos próximos 30 dias.</div>';
}

function companyRowActions(item, canManageCompanies) {
  const viewDetailsLabel = tr('company.viewDetails', 'Visualizar detalhes');
  if (!canManageCompanies) {
    return `<div class="action-group"><button class="ghost" data-company-details="${item.id}">${viewDetailsLabel}</button></div>`;
  }
  const toggleMode = Number(item.active) === 1 ? 0 : 1;
  const toggleLabel = Number(item.active) === 1 ? tr('company.deactivate', 'Inativar') : tr('company.activate', 'Ativar');
  const commercialAction = canAccessCommercialArea()
    ? `<button class="ghost" data-company-commercial="${item.id}">${tr('company.configureLicense', 'Configurar licença')}</button>`
    : '';
  return `<div class="action-group"><button class="ghost" data-company-details="${item.id}">${viewDetailsLabel}</button><button class="ghost" data-company-edit="${item.id}">${tr('company.editAction', 'Editar')}</button><button class="ghost" data-company-logo="${item.id}">Logotipo (suporte)</button>${commercialAction}<button class="ghost" data-company-toggle="${item.id}" data-company-active="${toggleMode}">${toggleLabel}</button></div>`;
}

function populateCommercialActors() {
  if (!refs.commercialFilterActor) return;
  const names = [...new Set(state.companyAuditLogs.map((item) => item.actor_name))].sort((a, b) => a.localeCompare(b, 'pt-BR'));
  const optionsHtml = names.map((name) => `<option value="${name}">${name}</option>`).join('');
  refs.commercialFilterActor.innerHTML = `<option value="">Todos</option>` + optionsHtml;
  refs.commercialFilterActor.value = state.commercialFilters.actor_name;
  refs.commercialFilterDateFrom.value = state.commercialFilters.date_from;
  refs.commercialFilterDateTo.value = state.commercialFilters.date_to;
  refs.commercialFilterStatus.value = state.commercialFilters.status;
}

function platformBrandDisplayName() {
  return state.platformBrand?.display_name || DEFAULT_PLATFORM_BRAND.display_name;
}

function exportCommercialExcel() {
  const rows = filteredCommercialLogs();
  const exportBrandName = platformBrandDisplayName();
  const header = ['Marca', 'Empresa', 'ação', 'Responsável', 'Data', 'Resumo', 'Detalhes'];
  const body = rows.map((item) => {
    const detailsHtml = formatCommercialDetails(item.details);
    const createdAt = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(item.created_at));
    return `<tr><td>${exportBrandName}</td><td>${item.company_name}</td><td>${item.action_label}</td><td>${item.actor_name}</td><td>${createdAt}</td><td>${item.summary}</td><td>${detailsHtml}</td></tr>`;
  }).join('');
  const tableStylesheet = 'table{border-collapse:collapse;width:100%;font-family:Segoe UI,Arial,sans-serif}th,td{border:1px solid var(--color-border);padding:8px;text-align:left;vertical-align:top}th{background:#f6d8c8}';
  const headerCells = header.map((item) => `<th scope="col">${item}</th>`).join('');
  const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><style>${tableStylesheet}</style></head><body><table><thead><tr>${headerCells}</tr></thead><tbody>${body}</tbody></table></body></html>`;
  const blob = new Blob([html], { type: 'application/vnd.ms-excel;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = 'historico-comercial.xls';
  link.click();
  URL.revokeObjectURL(link.href);
}

function formatCommercialFiltersLabel() {
  return [
    state.commercialFilters.status ? `Status: ${state.commercialFilters.status}` : 'Status: todos',
    state.commercialFilters.actor_name ? `Responsável: ${state.commercialFilters.actor_name}` : '',
    state.commercialFilters.date_from ? `De: ${formatDate(state.commercialFilters.date_from)}` : '',
    state.commercialFilters.date_to ? `até: ${formatDate(state.commercialFilters.date_to)}` : ''
  ].filter(Boolean).join(' | ');
}

function formatCommercialDetails(details, separator = '<br>') {
  return (details || []).map((detail) => `${detail.field}: ${detail.before || '-'} -> ${detail.after || '-'}`).join(separator);
}

function openAndPrintPopup(html, features = 'width=1100,height=800') {
  const popup = globalThis.open('', '_blank', features);
  if (!popup) return null;
  const markup = String(html || '').trim();
  if (!markup) return popup;
  popup.document.open();
  popup.document.write(markup);
  popup.document.close();
  const triggerPrint = () => {
    try {
      popup.focus();
      popup.print();
    } catch (error) {
      console.warn('[print] Falha ao disparar impressão da popup', error);
    }
  };
  if (popup.document.readyState === 'complete') {
    setTimeout(triggerPrint, 80);
  } else {
    safeOn(popup, 'load', () => setTimeout(triggerPrint, 80), { once: true });
    setTimeout(triggerPrint, 500);
  }
  return popup;
}

function printCommercialHistory() {
  const rows = filteredCommercialLogs();
  const filters = formatCommercialFiltersLabel();
  const rowsHtml = rows.map((item) => {
    const detailsHtml = formatCommercialDetails(item.details);
    const createdAt = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(item.created_at));
    return `<tr><td>${item.company_name}</td><td>${item.action_label}</td><td>${item.actor_name}</td><td>${createdAt}</td><td>${item.summary}</td><td class="detail">${detailsHtml}</td></tr>`;
  }).join('');
  const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Histórico Comercial</title></head><body><h1>Histórico Comercial</h1><p>Filtros: ${filters}</p><table><thead><tr><th scope="col">Empresa</th><th scope="col">ação</th><th scope="col">Responsável</th><th scope="col">Data</th><th scope="col">Resumo</th><th scope="col">Detalhes</th></tr></thead><tbody>${rowsHtml}</tbody></table></body></html>`;
  if (!openAndPrintPopup(html, 'width=1100,height=800')) return alert('Não tem acesso.');
}

async function savePlatformBrand(event) {
  event.preventDefault();
  if (state.user?.role !== 'master_admin') return;
  try {
    const values = formValues(refs.platformBrandForm);
    values.actor_user_id = state.user.id;
    if (values.cnpj) values.cnpj = formatCnpj(values.cnpj);
    const payload = await api('/api/platform-brand', { method: 'POST', body: JSON.stringify(values) });
    state.platformBrand = { ...DEFAULT_PLATFORM_BRAND, ...payload.brand };
    renderPlatformBrand();
    alert('Marca da sua empresa atualizada.');
  } catch (error) { alert(error.message); }
}

function downloadCommercialContractPdf() {
  const companyId = refs.commercialCompany?.value;
  if (!companyId) return;
  const params = new URLSearchParams({ actor_user_id: state.user.id, company_id: companyId });
  globalThis.open(`/api/commercial-contract.pdf?${params.toString()}`, '_blank');
}

async function saveCommercialContractDraft(showToast = false) {
  const payload = buildCommercialContractPayload();
  if (!payload.company_id) return;
  const response = await api('/api/commercial-contract/save', { method: 'POST', body: JSON.stringify(payload) });
  state.commercialContract = response.contract || null;
  renderCommercialContractPanel();
  if (showToast) alert('Contrato salvo em rascunho.');
}

async function generateCommercialContract() {
  try {
    const payload = buildCommercialContractPayload();
    const response = await api('/api/commercial-contract/generate', { method: 'POST', body: JSON.stringify(payload) });
    state.commercialContract = response.contract || null;
    renderCommercialContractPanel();
    alert('Contrato gerado com sucesso.');
  } catch (error) { alert(error.message); }
}

function viewGeneratedCommercialContract() {
  const companyId = refs.commercialCompany?.value;
  if (!companyId) return;
  const params = new URLSearchParams({ actor_user_id: state.user.id, company_id: companyId });
  globalThis.open(`/api/commercial-contract.pdf?${params.toString()}`, '_blank');
}

function downloadGeneratedCommercialContract() {
  const companyId = refs.commercialCompany?.value;
  if (!companyId) return;
  const params = new URLSearchParams({ actor_user_id: state.user.id, company_id: companyId, kind: 'generated' });
  globalThis.open(`/api/commercial-contract/file?${params.toString()}`, '_blank');
}

async function signCommercialContractAction() {
  try {
    const companyId = refs.commercialCompany?.value;
    const signatureName = refs.commercialSignatureName?.value || '';
    const signatureData = refs.commercialSignatureData?.value || '';
    const response = await api('/api/commercial-contract/sign', {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user.id, company_id: Number(companyId || 0), signature_name: signatureName, signature_data: signatureData })
    });
    state.commercialContract = response.contract || null;
    renderCommercialContractPanel();
    alert('Assinatura digital registrada.');
  } catch (error) { alert(error.message); }
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const full = String(reader.result || '');
      resolve(full.includes(',') ? full.split(',')[1] : full);
    };
    reader.onerror = () => reject(new Error('Falha ao ler arquivo.'));
    reader.readAsDataURL(file);
  });
}

async function uploadSignedCommercialContract() {
  try {
    const file = refs.commercialSignedFile?.files?.[0];
    if (!file) return alert('Selecione um PDF assinado.');
    const companyId = refs.commercialCompany?.value;
    const fileBase64 = await fileToBase64(file);
    const response = await api('/api/commercial-contract/upload-signed', {
      method: 'POST',
      body: JSON.stringify({
        actor_user_id: state.user.id,
        company_id: Number(companyId || 0),
        file_name: file.name,
        file_mime: file.type || 'application/pdf',
        file_base64: fileBase64
      })
    });
    state.commercialContract = response.contract || null;
    renderCommercialContractPanel();
    alert('Contrato assinado enviado com sucesso.');
  } catch (error) { alert(error.message); }
}

async function sendCommercialContractByEmail() {
  try {
    const companyId = refs.commercialCompany?.value;
    const response = await api('/api/commercial-contract/send-email', {
      method: 'POST',
      body: JSON.stringify({
        actor_user_id: state.user.id,
        company_id: Number(companyId || 0),
        email_to: refs.commercialEmailTo?.value || '',
        subject: refs.commercialEmailSubject?.value || '',
        body: refs.commercialEmailBody?.value || ''
      })
    });
    state.commercialContract = response.contract || null;
    renderCommercialContractPanel();
    alert('Registro de envio por e-mail atualizado.');
  } catch (error) { alert(error.message); }
}

function exportCommercialHistory() {
  const rows = filteredCommercialLogs();
  const exportBrandName = platformBrandDisplayName();
  const header = ['Marca', 'Empresa', 'ação', 'Responsável', 'Data', 'Resumo', 'Detalhes'];
  const lines = rows.map((item) => [
    exportBrandName,
    item.company_name,
    item.action_label,
    item.actor_name,
    item.created_at,
    item.summary,
    (item.details || []).map((detail) => `${detail.field}: ${detail.before || '-'} -> ${detail.after || '-'}`).join(' | ')
  ]);
  const csv = [header, ...lines].map((row) => row.map((value) => `"${String(value || '').replaceAll('"', '""')}"`).join(';')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = 'historico-comercial.csv';
  link.click();
  URL.revokeObjectURL(link.href);
}

function syncCommercialFilter() {
  state.commercialFilters.status = refs.commercialFilterStatus?.value || '';
  state.commercialFilters.date_from = refs.commercialFilterDateFrom?.value || '';
  state.commercialFilters.date_to = refs.commercialFilterDateTo?.value || '';
  state.commercialFilters.actor_name = refs.commercialFilterActor?.value || '';
  renderCommercialSummary();
  renderCommercialAlerts();
  renderCommercialHistory();
}

async function saveCommercial(event) {
  event.preventDefault();
  if (!requirePermission('commercial:view')) return;
  const companyId = refs.commercialCompany?.value;
  const company = state.companies.find((item) => String(item.id) === String(companyId));
  if (!company) return;
  try {
    const values = formValues(refs.commercialForm);
    values.actor_user_id = state.user.id;
    values.name = company.name;
    values.legal_name = company.legal_name;
    values.cnpj = company.cnpj;
    values.logo_type = company.logo_type || '';
    values.addendum_enabled = refs.commercialForm.elements.addendum_enabled.checked ? 1 : 0;
    values.monthly_value = Number(company.monthly_value || 0);
    await api(`/api/companies/${company.id}`, { method: 'PUT', body: JSON.stringify(values) });
    await loadBootstrap();
    fillCommercialForm(company.id);
  } catch (error) { alert(error.message); }
}

async function saveCommercialContractManagement() {
  if (!requirePermission('commercial:view')) return;
  try {
    await saveCommercialContractDraft(true);
  } catch (error) {
    alert(error.message);
  }
}

async function saveCommercialSettings(event) {
  event.preventDefault();
  if (state.user?.role !== 'master_admin') return;
  try {
    const form = refs.commercialSettingsForm;
    const startMax = Number(form.elements.start_max.value || 10);
    const businessMax = Number(form.elements.business_max.value || 25);
    const corporateMax = Number(form.elements.corporate_max.value || 100);
    const payload = {
      actor_user_id: state.user.id,
      unit_price: Number(form.elements.unit_price.value || 0),
      plans: {
        individual: { label: 'Individual', min_users: 1, max_users: Number(form.elements.individual_max.value || 1) },
        start: { label: 'Start', min_users: 1, max_users: startMax },
        business: { label: 'Business', min_users: startMax + 1, max_users: businessMax },
        corporate: { label: 'Corporate', min_users: businessMax + 1, max_users: corporateMax },
        enterprise: { label: 'Enterprise', min_users: Number(form.elements.enterprise_min.value || 101), max_users: null }
      }
    };
    await api('/api/commercial-settings', { method: 'POST', body: JSON.stringify(payload) });
    await loadBootstrap();
    fillCommercialSettingsForm();
    fillCommercialForm(refs.commercialCompany?.value);
  } catch (error) { alert(error.message); }
}

function formatCompanyRow(item, selectedId) {
  const actions = companyRowActions(item, hasPermission('companies:create') || hasPermission('companies:update'));
  const validityRange = tr('company.validityRange', '{start} até {end}')
    .replace('{start}', formatDate(item.contract_start))
    .replace('{end}', formatDate(item.contract_end));
  return `
      <tr class="${selectedId === String(item.id) ? 'selected-row' : ''}">
        <td><div class="company-cell"><strong>${item.name}</strong><span>${item.legal_name || '-'}</span></div></td>
        <td><div class="company-cell"><strong>${item.cnpj}</strong><span>${item.plan_name || '-'}</span></div></td>
        <td><div class="company-cell">${companyStatusBadges(item)}<span>${tr('company.validity', 'Vigência')}: ${validityRange}</span></div></td>
        <td><div class="company-logo-slot">${companyLogoMarkup(item, 'company-logo company-logo-sm')}</div></td>
        <td><div class="company-cell"><strong>${item.user_count ?? '—'}</strong><span>${formatCompanyAvailabilityText(item)}</span></div></td>
        <td><div class="company-cell"><strong>${item.user_limit ?? '—'}</strong><span>${formatCompanyCurrency(item.monthly_value)}</span></div></td>
        <td>${actions}</td>
      </tr>`;
}

function renderCompanies() {
  if (!refs.companiesTable) return;
  const visibleCompanies = filterByUserCompany(state.companies);
  const selectedId = String(state.selectedCompanyId || visibleCompanies[0]?.id || '');
  refs.companiesTable.innerHTML = visibleCompanies.map((item) => formatCompanyRow(item, selectedId)).join('') || globalThis.dsTableState({ colspan: 7, message: tr('company.noCompanies', 'Sem empresas disponíveis.') });
}

function resetCompanyForm() {
  if (!refs.companyForm) return;
  state.editingCompanyId = null;
  refs.companyForm.reset();
  setCompanyFieldValue('id', '');
  setCompanyFieldValue('active', '1');
  setCompanyFieldValue('general_admin_email', '', { optional: true });
  setCompanyFieldValue('general_admin_name', '', { optional: true });
  renderCompanyDetails();
}

function startEditCompany(companyId) {
  if (!hasPermission('companies:update')) return;
  const company = state.companies.find((item) => String(item.id) === String(companyId));
  if (!company || !refs.companyForm) return;
  state.editingCompanyId = company.id;
  state.selectedCompanyId = company.id;
  setCompanyFieldValue('id', company.id);
  setCompanyFieldValue('name', company.name || '');
  setCompanyFieldValue('legal_name', company.legal_name || '');
  setCompanyFieldValue('cnpj', company.cnpj || '');
  setCompanyFieldValue('general_admin_email', '', { optional: true });
  setCompanyFieldValue('general_admin_name', '', { optional: true });
  setCompanyFieldValue('active', String(Number(company.active || 1)));
  renderCompanies();
  renderCompanyDetails(company.id);
  refs.companyForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Suporte excepcional (auditado): o Administrador Master não edita a
// identidade visual da tenant pela rota operacional — apenas via
// support-update, com justificativa registrada no log de auditoria.
function openCompanyLogoEditor(companyId) {
  if (state.user?.role !== 'master_admin') return;
  const company = state.companies.find((item) => String(item.id) === String(companyId));
  if (!company) return;
  const reason = window.prompt(`Suporte auditado — justifique a alteração do logotipo de ${company.name} (mínimo 10 caracteres):`);
  if (reason === null) return;
  if (String(reason).trim().length < 10) {
    alert('Justificativa muito curta. Informe pelo menos 10 caracteres.');
    return;
  }
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.png,.jpg,.jpeg,.svg,image/png,image/jpeg,image/svg+xml';
  bindAppListener(input, 'change', async () => {
    const file = input.files?.[0];
    if (!file) return;
    const allowed = ['image/png', 'image/jpeg', 'image/svg+xml'];
    if (!allowed.includes(file.type)) {
      alert('Envie um logotipo PNG, JPG ou SVG.');
      return;
    }
    try {
      const logoType = await fileToJpegDataUrl(file);
      await api(`/api/companies/${company.id}/support-update`, {
        method: 'POST',
        body: JSON.stringify({ actor_user_id: state.user.id, support_reason: String(reason).trim(), logo_type: logoType })
      });
      await loadBootstrap();
      alert('Logotipo atualizado via suporte auditado.');
    } catch (error) { alert(error.message); }
  });
  input.click();
}

async function saveCompany(event) {
  event.preventDefault();
  if (!requirePermission(state.editingCompanyId ? 'companies:update' : 'companies:create')) return;
  try {
    const currentCompany = state.companies.find((item) => String(item.id) === String(state.editingCompanyId || '')) || {};
    const values = {
      actor_user_id: state.user.id,
      name: readCompanyFieldValue('name', currentCompany.name || ''),
      legal_name: readCompanyFieldValue('legal_name', currentCompany.legal_name || ''),
      cnpj: formatCnpj(readCompanyFieldValue('cnpj', currentCompany.cnpj || '')),
      logo_type: currentCompany.logo_type || '',
      plan_name: currentCompany.plan_name || 'start',
      user_limit: currentCompany.user_limit || 10,
      addendum_enabled: currentCompany.addendum_enabled || 0,
      contract_start: currentCompany.contract_start || '',
      contract_end: currentCompany.contract_end || '',
      monthly_value: currentCompany.monthly_value || 0,
      license_status: currentCompany.license_status || 'active',
      active: readCompanyFieldValue('active', String(Number(currentCompany.active ?? 1))),
      commercial_notes: currentCompany.commercial_notes || ''
    };
    if (!state.editingCompanyId) {
      values.general_admin_email = readCompanyFieldValue('general_admin_email', '', { optional: true }).trim();
      values.general_admin_name = readCompanyFieldValue('general_admin_name', '', { optional: true }).trim();
    }
    await api(state.editingCompanyId ? `/api/companies/${state.editingCompanyId}` : '/api/companies', { method: state.editingCompanyId ? 'PUT' : 'POST', body: JSON.stringify(values) });
    resetCompanyForm();
    await loadBootstrap();
  } catch (error) { alert(error.message); }
}

async function toggleCompany(companyId, active) {
  if (!hasPermission('companies:update')) return;
  const company = state.companies.find((item) => String(item.id) === String(companyId));
  if (!company) return;
  try {
    await api(`/api/companies/${companyId}`, { method: 'PUT', body: JSON.stringify({ actor_user_id: state.user.id, name: company.name, legal_name: company.legal_name, cnpj: company.cnpj, logo_type: company.logo_type, plan_name: company.plan_name, user_limit: company.user_limit, contract_start: company.contract_start || '', contract_end: company.contract_end || '', monthly_value: company.monthly_value || 0, addendum_enabled: company.addendum_enabled || 0, license_status: company.license_status, active, commercial_notes: company.commercial_notes || '' }) });
    await loadBootstrap();
  } catch (error) { alert(error.message); }
}

function filteredUsers() {
  return filterByUserCompany(state.users).filter((item) => {
    if (state.userFilters.company_id && String(item.company_id || '') !== String(state.userFilters.company_id)) return false;
    if (state.userFilters.role && item.role !== state.userFilters.role) return false;
    if (state.userFilters.active !== '' && String(Number(item.active)) !== String(state.userFilters.active)) return false;
    if (state.userFilters.search) {
      const haystack = `${item.full_name} ${item.username} ${item.company_name || ''}`.toLowerCase();
      if (!haystack.includes(state.userFilters.search)) return false;
    }
    return true;
  });
}

// Aguarda o backend ficar PRONTO antes de chamar /api/bootstrap.
//
// No cold-start do Render o backend sobe e roda as funções de schema (ensure_*)
// por dezenas de segundos; durante essa janela o gate responde 503 em
// /api/bootstrap, o que gerava uma tempestade de erros no console (bootstrap +
// todos os loaders secundários). A sonda /health responde SEMPRE 200 (mesmo no
// warmup) com { ready: bool }; então esperamos ready===true e só então seguimos.
//
// Caminho quente (backend já pronto): a primeira sonda retorna ready:true de
// imediato — sem atraso e sem mudança de comportamento. Se estourar o tempo,
// retorna false e o chamador segue no fluxo atual (retry/degradado) — sem
// regressão.
async function waitForBackendReady({ maxWaitMs = 90000, pollMs = 2000 } = {}) {
  const deadline = Date.now() + Math.max(0, maxWaitMs);
  for (;;) {
    try {
      const res = await fetch('/health', { headers: { Accept: 'application/json' }, cache: 'no-store' });
      if (res.ok) {
        const data = await res.json().catch(() => null);
        if (data && data.ready === true) return true;
      }
    } catch (_error) {
      // Blip de rede durante o boot — continua tentando até o deadline.
    }
    if (Date.now() >= deadline) return false;
    updatePhase3ContextStatus('dashboard', 'loading', 'Servidor iniciando...');
    await new Promise((resolve) => setTimeout(resolve, pollMs));
  }
}

async function loadBootstrap() {
  try {
    updatePhase3ContextStatus('dashboard', 'loading', 'Atualizando...');
    // Evita a tempestade de 503 no cold-start: espera o backend sinalizar
    // readiness via /health antes de disparar o bootstrap (e, por consequência,
    // o renderAll com seus loaders). Ver waitForBackendReady acima.
    await waitForBackendReady();
    const payload = await apiWithBootstrapRetry(`/api/bootstrap?${actorQuery()}`, {}, { maxAttempts: 6, retryDelayMs: 3000 });
    state.platformBrand = { ...DEFAULT_PLATFORM_BRAND, ...payload.platform_brand };
    state.commercialSettings = cloneCommercialSettings(payload.commercial_settings || DEFAULT_COMMERCIAL_SETTINGS);
    state.companies = Array.isArray(payload.companies) ? payload.companies : [];
    state.companyAuditLogs = payload.company_audit_logs || [];
    state.fichaAuditLogs = payload.ficha_audit_logs || [];
    state.users = Array.isArray(payload.users) ? payload.users : [];
    state.units = Array.isArray(payload.units) ? payload.units : [];
    // CNPJs (LegalEntity) do tenant. Vem vazio enquanto o schema Multi-CNPJ não
    // estiver provisionado — os campos de CNPJ ficam ocultos nesse caso.
    state.legalEntities = Array.isArray(payload.legal_entities) ? payload.legal_entities : [];
    state.employees = Array.isArray(payload.employees) ? payload.employees : [];
    state.employeeMovements = payload.employee_movements || [];
    state.epis = Array.isArray(payload.epis) ? payload.epis : [];
    state.deliveries = Array.isArray(payload.deliveries) ? payload.deliveries : [];
    state.feedbacks = Array.isArray(payload.feedbacks) ? payload.feedbacks : [];
    state.alerts = Array.isArray(payload.alerts) ? payload.alerts : [];
    state.permissions = normalizePermissions(state.user, payload.permissions || state.permissions);
    state.moduleVisibility = (payload.module_visibility && typeof payload.module_visibility === 'object') ? payload.module_visibility : {};
    state.bootstrapWarnings = Array.isArray(payload.bootstrap_warnings) ? payload.bootstrap_warnings : [];
    if (state.user?.role === 'master_admin') {
      try {
        const poolPayload = await api(`/api/db-pool/status?${actorQuery()}`);
        state.dbPoolStatus = poolPayload.pool || null;
      } catch (error) {
        console.warn('[db-pool-status] Falha ao carregar status do pool:', error);
        state.dbPoolStatus = null;
      }
    } else {
      state.dbPoolStatus = null;
    }
    if (hasPermission('stock:view')) {
      const lowStockPayload = await loadOptionalBootstrapSection(
        'stock',
        { items: [] },
        () => api(`/api/stock/low?${actorQuery()}`),
        { permission: 'stock:view' }
      );

      state.lowStock = lowStockPayload.items || [];

      await loadOptionalBootstrapSection(
        'stock',
        null,
        async () => {
          await loadStockEpis();
          return null;
        },
        { permission: 'stock:view' }
      );
    } else {
      state.lowStock = [];
      state.stockEpis = [];
    }

    if (hasPermission('purchase_requests:view')) {
      const requestsPayload = await loadOptionalBootstrapSection(
        'purchases',
        { items: [] },
        () => api(`/api/requests?${actorQuery()}`),
        { permission: 'purchase_requests:view' }
      );

      state.requests = requestsPayload.items || [];
    } else {
      state.requests = [];
    }

    if (hasPermission('fichas:view')) {
      const fichasPayload = await loadOptionalBootstrapSection(
        'fichas',
        { items: [] },
        () => api(`/api/fichas?${actorQuery()}`),
        { permission: 'fichas:view' }
      );

      state.fichasPeriods = fichasPayload.items || [];
    } else {
      state.fichasPeriods = [];
    }

    if (hasConfigurationAccess()) {
      const rulesPayload = await loadOptionalBootstrapSection(
        'configuration',
        { rules: [] },
        () => api(`/api/configuration-rules?${actorQuery()}`),
        { permission: 'settings:view' }
      );

      state.configurationRules = Array.isArray(rulesPayload.rules)
        ? rulesPayload.rules
        : [];

      const moduleVisibilityPayload = await loadOptionalBootstrapSection(
        'configuration',
        { module_visibility: {} },
        () => api(`/api/module-visibility?${actorQuery()}`),
        { permission: 'settings:view' }
      );
      state.moduleVisibilityAdminConfig = (moduleVisibilityPayload.module_visibility && typeof moduleVisibilityPayload.module_visibility === 'object')
        ? moduleVisibilityPayload.module_visibility
        : {};
      state.moduleVisibilityDefault = (moduleVisibilityPayload.default_module_visibility && typeof moduleVisibilityPayload.default_module_visibility === 'object')
        ? moduleVisibilityPayload.default_module_visibility
        : {};

      if (hasHardeningAccess()) {
        const frameworkPayload = await loadOptionalBootstrapSection(
          'configuration',
          { framework: {} },
          () => api(`/api/configuration-framework?${actorQuery()}`),
          { permission: 'settings:view' }
        );

        state.configurationFramework = {
          ...deepClone(DEFAULT_CONFIGURATION_FRAMEWORK),
          ...(frameworkPayload.framework || {})
        };
      } else {
        state.configurationFramework = deepClone(DEFAULT_CONFIGURATION_FRAMEWORK);
      }
    } else {
      state.configurationRules = [];
      state.configurationFramework = deepClone(DEFAULT_CONFIGURATION_FRAMEWORK);
      state.moduleVisibilityAdminConfig = {};
      state.moduleVisibilityDefault = {};
    }
    safeStorageWrite(STORAGE_KEYS.permissions, JSON.stringify(state.permissions));
    clearBootstrapDegraded();
    renderAll();
    updatePhase3ContextStatus('dashboard', 'success', 'Dados sincronizados');
  } catch (error) {
    updatePhase3ContextStatus('dashboard', 'error', 'Falha ao atualizar');
    if ([401, 403].includes(Number(error?.status || 0))) {
      clearSession();
      showScreen(false);
    } else if (state.user && isBootstrapRequestError(error)) {
      setBootstrapDegraded(error);
      updateBootstrapDegradedUi();
    }
    throw error;
  }
}

function populateSelect(selectId, items, labelBuilder, valueKey = 'id', includeEmpty = false, emptyLabel = 'Selecione') {
  const select = document.getElementById(selectId);
  const filtered = filterByUserCompany(items);
  const emptyOption = includeEmpty ? `<option value="">${emptyLabel}</option>` : '';
  const optionsHtml = filtered.map((item) => `<option value="${item[valueKey]}">${labelBuilder(item)}</option>`).join('');
  select.innerHTML = emptyOption + optionsHtml;
}

function bindDependentSelects() {
  const companies = state.user?.role === 'master_admin' ? state.companies : filterByUserCompany(state.companies);
  populateSelect('user-company', companies, (item) => `${item.name} - ${item.cnpj}`, 'id', true, 'Sem ví­nculo');
  populateSelect('unit-company', companies, (item) => `${item.name} - ${item.cnpj}`);
  populateSelect('employee-company', companies, (item) => `${item.name} - ${item.cnpj}`);
  populateSelect('epi-company', companies, (item) => `${item.name} - ${item.cnpj}`);
  populateSelect('epi-unit', state.units, (item) => `${item.name} - ${unitTypeLabel(item.unit_type)}`);
  populateSelect('delivery-company', companies, (item) => `${item.name} - ${item.cnpj}`, 'id', state.user?.role === 'master_admin', 'Selecione a empresa');
  populateSelect('stock-company', companies, (item) => `${item.name} - ${item.cnpj}`);
  populateSelect('delivery-unit-filter', state.units, (item) => `${item.name} - ${unitTypeLabel(item.unit_type)}`, 'id', true, tr('epi.allUnits', 'Todas as Unidades'));
  populateSelect('report-company', companies, (item) => item.name, 'id', true, tr('employee.filterAllCompanies', 'Todas'));
  populateSelect('employee-unit', state.units, (item) => `${item.name} - ${unitTypeLabel(item.unit_type)}`);
  populateSelect('outsourced-employee-company', companies, (item) => `${item.name} - ${item.cnpj}`);
  populateSelect('outsourced-employee-unit', state.units, (item) => `${item.name} - ${unitTypeLabel(item.unit_type)}`);
  populateSelect('outsourced-company-unit', state.units, (item) => `${item.name} - ${unitTypeLabel(item.unit_type)}`, 'id', true, tr('outsourcedCompany.allUnits', 'Todas as unidades (padrão)'));
  populateSelect('movement-target-unit-id', state.units, (item) => `${item.name} - ${unitTypeLabel(item.unit_type)}`);
  populateSelect('movement-employee-id', state.employees, (item) => `${item.employee_id_code} - ${item.name}`);
  populateSelect('delivery-employee', state.employees, (item) => `${item.employee_id_code} - ${item.name}`);
  populateSelect('delivery-epi', episForOperationalScope(state.epis), (item) => `${item.name} - ${item.unit_measure}`);
  populateSelect('stock-unit', state.units, (item) => `${item.name} - ${unitTypeLabel(item.unit_type)}`);
  populateSelect('stock-epi', episForOperationalScope(state.epis), (item) => `${item.name} - ${item.unit_measure}`);
  populateSelect('ficha-employee', state.employees, (item) => `${item.employee_id_code} - ${item.name}`);
  populateSelect('report-unit', state.units, (item) => item.name, 'id', true, tr('employee.filterAllUnits', 'Todas'));
  populateSelect('report-epi', episForOperationalScope(state.epis), (item) => item.name, 'id', true, tr('employee.filterAll', 'Todos'));
  populateSelect('report-employee', state.employees, (item) => `${item.employee_id_code} - ${item.name}`, 'id', true, tr('employee.allEmployees', 'Todos os colaboradores'));
  const sectors = [...new Set(filterByUserCompany(state.employees).map((item) => item.sector))].sort((a, b) => a.localeCompare(b));
  document.getElementById('report-sector').innerHTML = `<option value="">${tr('employee.filterAll', 'Todos')}</option>` + sectors.map((item) => `<option value="${item}">${item}</option>`).join('');
  const defaultCompanyId = companies[0]?.id ? String(companies[0].id) : '';
  const isMasterAdmin = state.user?.role === 'master_admin';
  ['unit-company', 'employee-company', 'epi-company', 'delivery-company', 'stock-company', 'outsourced-employee-company'].forEach((fieldId) => {
    const field = document.getElementById(fieldId);
    // master_admin: delivery-company has a "Selecione a empresa" placeholder — don't force a default
    if (fieldId === 'delivery-company' && isMasterAdmin) return;
    if (field && !field.value && defaultCompanyId) field.value = defaultCompanyId;
  });
  populateLinkedEmployeeOptions();
  syncEmployeeUnitOptions();
  syncOutsourcedEmployeeUnitOptions();
  syncOutsourcedCompanyUnitOptions();
  syncUnitLegalEntityOptions();
  syncEpiUnitOptions();
  syncDeliveryOptions();
  syncStockOptions();
  syncEmployeeUnitOptions();
  syncReportOptions();
  populateStockProtectionFilter();
}

function sameCompany(target) {
  return String(target.company_id || '') === String(state.user?.company_id || '');
}

function canManageUser(target) {
  if (!hasPermission('users:update')) return false;
  if (state.user?.role === 'master_admin') return target.role !== 'master_admin';
  if (state.user?.role === 'general_admin') return ['registry_admin', 'admin', 'user', 'employee'].includes(target.role) && sameCompany(target);
  if (state.user?.role === 'registry_admin') return ['admin', 'user', 'employee'].includes(target.role) && sameCompany(target);
  return false;
}
function canDeleteUser(target) { return hasPermission('users:delete') && canManageUser(target) && String(target.id) !== String(state.user?.id || ''); }
function canPromoteToAdmin(target) { return ['master_admin', 'general_admin', 'registry_admin'].includes(state.user?.role) && target.role === 'user' && (state.user?.role === 'master_admin' || sameCompany(target)); }
function canPromoteToGeneralAdmin(target) { return state.user?.role === 'master_admin' && ['admin', 'user'].includes(target.role); }
function canDemoteAdmin(target) { return ['master_admin', 'general_admin'].includes(state.user?.role) && target.role === 'admin' && (state.user?.role === 'master_admin' || sameCompany(target)); }
function canDemoteGeneralAdmin(target) { return state.user?.role === 'master_admin' && target.role === 'general_admin'; }
function canToggleActive(target) { return canManageUser(target) && String(target.id) !== String(state.user?.id || ''); }

function setUserFormFeedback(message = '', isError = false) {
  const field = document.getElementById('user-form-feedback');
  if (!field) return;
  field.textContent = String(message || '');
  field.classList.toggle('error', Boolean(isError));
}

function syncUserFormAccess() {
  const roleField = refs.userForm?.elements?.role;
  const companyField = refs.userForm?.elements?.company_id;
  if (!roleField || !companyField) return;

  const selectedRole = String(roleField.value || '').trim();
  const requiresCompany = USER_COMPANY_REQUIRED_ROLES.includes(selectedRole);
  const companyLocked = ['general_admin', 'registry_admin', 'admin'].includes(state.user?.role);

  if (companyLocked) {
    companyField.value = state.user?.company_id || '';
    companyField.disabled = true;
  } else {
    companyField.disabled = !requiresCompany;
    if (!requiresCompany) companyField.value = '';
  }

  if (requiresCompany && !companyField.value) {
    companyField.value = String(state.selectedCompanyId || state.user?.company_id || state.companies[0]?.id || '');
  }

  populateLinkedEmployeeOptions();
  syncUserEmployeeLink();
}

function userActionButtons(target) {
  if (!canManageUser(target) && !canDeleteUser(target) && target.role !== 'employee') return '-';
  const actions = [];
  
  addEditButtons(actions, target);
  addPromoteButtons(actions, target);
  addPasswordButtons(actions, target);
  addManagementButtons(actions, target);
  addEmployeeButtons(actions, target);
  
  if (actions.length === 0) return '-';
  return `<div class="action-group">${actions.join('')}</div>`;
}

function addEditButtons(actions, target) {
  if (canManageUser(target)) {
    actions.push(`<button class="ghost" data-user-edit="${target.id}">${tr('edit', 'Editar')}</button>`);
  }
}

function addPromoteButtons(actions, target) {
  if (canPromoteToAdmin(target)) {
    actions.push(`<button class="ghost" data-user-promote-admin="${target.id}">${tr('user.promoteToAdmin', 'Tornar Administrador')}</button>`);
  }
  if (canPromoteToGeneralAdmin(target)) {
    actions.push(`<button class="ghost" data-user-promote-general="${target.id}">${tr('user.promoteToGeneralAdmin', 'Tornar Adm. Geral')}</button>`);
  }
  if (canDemoteGeneralAdmin(target)) {
    actions.push(`<button class="ghost" data-user-demote-general="${target.id}">${tr('user.removeFromGeneral', 'Remover do Geral')}</button>`);
  }
  if (canDemoteAdmin(target)) {
    actions.push(`<button class="ghost" data-user-demote-admin="${target.id}">${tr('user.demoteToUser', 'Rebaixar para Usuário')}</button>`);
  }
}

function canGenerateRecoveryToken(target) {
  if (state.user?.role === 'master_admin') {
    return target.role !== 'master_admin' || String(target.id) === String(state.user?.id);
  }
  if (state.user?.role === 'general_admin') {
    return ['registry_admin', 'admin', 'user', 'buyer', 'approver', 'employee'].includes(target.role) && sameCompany(target);
  }
  return false;
}

function addPasswordButtons(actions, target) {
  if (canManageUser(target)) {
    actions.push(
      `<button class="ghost" data-user-temp-password="${target.id}">${tr('user.generateProvPassword', 'Gerar senha provisória')}</button>`,
      `<button class="ghost" data-user-generate-copy-password="${target.id}">${tr('user.generateCopyPassword', 'Gerar e copiar senha')}</button>`
    );
    if (Number(target.force_password_change || 0) !== 1) {
      actions.push(`<button class="ghost" data-user-force-password-change="${target.id}">${tr('user.forcePasswordChange', 'Forçar troca da senha novamente')}</button>`);
    }
  }
  if (canGenerateRecoveryToken(target)) {
    actions.push(`<button class="ghost" data-user-recovery-token="${target.id}">${tr('user.generateRecoveryKey', 'Gerar chave de recuperação')}</button>`);
  }
}

function addManagementButtons(actions, target) {
  if (canManageUser(target)) {
    actions.push(
      `<button class="ghost" data-user-copy-email="${target.id}">${tr('user.copyEmail', 'Copiar e-mail')}</button>`,
      `<button class="ghost" data-user-copy-whatsapp="${target.id}">${tr('user.copyWhatsapp', 'Copiar WhatsApp')}</button>`
    );
  }
  if (canToggleActive(target)) {
    const label = Number(target.active) === 1 ? tr('user.deactivate', 'Desativar Usuário') : tr('user.activate', 'Ativar Usuário');
    actions.push(`<button class="ghost" data-user-toggle="${target.id}">${label}</button>`);
  }
  if (canDeleteUser(target)) {
    actions.push(`<button class="ghost" data-user-delete="${target.id}">${tr('user.remove', 'Remover')}</button>`);
  }
}

function addEmployeeButtons(actions, target) {
  if (target.role === 'employee' && target.employee_access_token) {
    actions.push(`<button class="ghost" data-user-employee-qr="${target.id}">${tr('user.externalQr', 'QR Acesso Externo')}</button>`);
  }
}

function printEmployeeAccessQr(userId) {
  const target = state.users.find((item) => String(item.id) === String(userId));
  if (!target?.employee_access_token) return alert('Funcionário sem token externo.');
  const accessLink = buildEmployeeAccessLink(target.employee_access_token);
  const html = `<!doctype html><html><head><meta charset="utf-8"><title>Acesso Funcionário"></head><body><p><a href="${accessLink}">${accessLink}</a></p></body></html>`;
  if (!openAndPrintPopup(html, 'width=520,height=700')) return alert('Não tem acesso.');
}

async function printEmployeePortalLink(employeeId) {
  try {
    const payload = await api('/api/employee-portal-link', {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user.id, employee_id: Number(employeeId) })
    });
    const employee = state.employees.find((item) => String(item.id) === String(employeeId));
    const accessLink = payload.access_link || payload.qr_code_value || buildEmployeeAccessLink(payload.token);
    const html = `<!doctype html><html><head><meta charset="utf-8"><title>Link do Colaborador</title><style>body{font-family:Segoe UI,Arial,sans-serif;padding:22px;text-align:center}img{width:240px;height:240px;margin:18px auto;display:block}a{word-break:break-all;color:#96401c}</style></head><body><h2>${employee?.name || 'Colaborador'}</h2><p>Link de acesso externo</p><img src="${qrCodeImageUrl(accessLink)}" alt="Link acesso colaborador"><p><a href="${accessLink}">${accessLink}</a></p></body></html>`;
    if (!openAndPrintPopup(html, 'width=520,height=700')) return alert('Não tem acesso.');
  } catch (error) {
    alert(error.message);
  }
}

function startEditUser(userId) {
  const user = state.users.find((item) => String(item.id) === String(userId));
  if (!user) return;
  state.editingUserId = user.id;
  setUserFormFeedback('');
  refs.userForm.elements.id.value = user.id;
  refs.userForm.elements.full_name.value = user.full_name;
  refs.userForm.elements.username.value = user.username;
  refs.userForm.elements.password.value = '';
  populateRoleOptions();
  refs.userForm.elements.role.value = canManageUser(user) ? user.role : refs.userRole.value;
  refs.userForm.elements.company_id.value = user.company_id || '';
  refs.userForm.elements.linked_employee_id.value = user.linked_employee_id || '';
  syncUserFormAccess();
}

async function updateUserAccess(userId, changes, successMessage = '') {
  const target = state.users.find((item) => String(item.id) === String(userId));
  if (!target) return;
  try {
    await api(`/api/users/${userId}`, { method: 'PUT', body: JSON.stringify({ actor_user_id: state.user.id, username: target.username, full_name: target.full_name, password: '', role: changes.role || target.role, company_id: changes.company_id === undefined ? target.company_id : changes.company_id, active: changes.active === undefined ? target.active : changes.active }) });
    if (successMessage) alert(successMessage);
    setUserFormFeedback(successMessage || 'Usuário atualizado com sucesso.');
    await loadBootstrap();
  } catch (error) {
    setUserFormFeedback(error.message, true);
    alert(error.message);
  }
}

function askTemporaryPassword(defaultValue = '') {
  const password = globalThis.prompt('Defina a senha provisória:', defaultValue);
  if (password === null) return null;
  if (String(password).trim().length < 8) throw new Error('A senha provisória precisa ter pelo menos 8 caracteres.');
  return String(password).trim();
}

function generateTemporaryPassword(length = 12) {
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%';
  const cryptoObject = globalThis.crypto || globalThis.msCrypto;
  if (!cryptoObject?.getRandomValues) {
    return `Temp${Math.random().toString(36).slice(-8)}!`;
  }
  const values = new Uint32Array(length);
  cryptoObject.getRandomValues(values);
  return Array.from(values, (value) => alphabet[value % alphabet.length]).join('');
}

async function copyTextToClipboard(value) {
  if (navigator.clipboard.writeText) {
    await navigator.clipboard.writeText(value);
    return true;
  }
  const textarea = document.createElement('textarea');
  textarea.value = value;
  textarea.setAttribute('readonly', 'readonly');
  textarea.style.position = 'fixed';
  textarea.style.opacity = '0';
  document.body.appendChild(textarea);
  textarea.select();
  try {
    const copied = document.execCommand('copy');
    textarea.remove();
    return copied;
  } catch (error) {
    console.error('Copy failed:', error);
    textarea.remove();
    return false;
  }
}

function buildUserAccessMessage(target, password, channel = 'email') {
  const brand = state.platformBrand || DEFAULT_PLATFORM_BRAND;
  const brandName = brand.display_name || DEFAULT_PLATFORM_BRAND.display_name;
  const legalName = brand.legal_name || brandName;
  const brandCnpj = brand.cnpj ? `CNPJ: ${brand.cnpj}` : '';
  const companyName = target.company_name || 'sua empresa';
  const loginUrl = globalThis.location.origin;
  if (channel === 'whatsapp') {
    const footer = brandCnpj ? `${legalName} | ${brandCnpj}` : legalName;
    return [
      `${target.full_name}.`,
      '',
      `Seu acesso ao sistema ${brandName} foi liberado para a empresa ${companyName}.`,
      `Usuário: ${target.username}`,
      `Senha provisória: ${password}`,
      '',
      'No primeiro acesso, crie a sua e troque a de provisÃÂ£o.',
      `Acesso: ${loginUrl}`,
      '',
      footer
    ].join('\n');
  }
  return [
    `Assunto: Acesso ao sistema ${brandName}`,
    '',
    `${target.full_name},`,
    '',
    `Seu acesso ao sistema ${brandName} foi liberado para operação na empresa ${companyName}.`,
    '',
    'Dados de acesso inicial:',
    `Usuário: ${target.username}`,
    `Senha provisória: ${password}`,
    `Link de acesso: ${loginUrl}`,
    '',
    'Importante: no primeiro acesso, Você definir a sua provisória para senha final antes de entrar no painel.',
    '',
    'Em caso de perda ou esquecer a senha entrar em contato com sua empresa.',
    '',
    'Atenciosamente,',
    legalName,
    brandCnpj
  ].filter(Boolean).join('\n');
}

async function copyUserAccessMessage(userId, channel = 'email') {
  const target = state.users.find((item) => String(item.id) === String(userId));
  if (!target) return;
  const password = askTemporaryPassword('Temp1234');
  if (password === null) return;
  try {
    await applyTemporaryPassword(userId, password, target.username, { notify: false });
    const message = buildUserAccessMessage(target, password, channel);
    const copied = await copyTextToClipboard(message);
    const label = channel === 'whatsapp' ? 'WhatsApp' : 'e-mail';
    alert(copied ? `Mensagem de ${label} copiada para ${target.username}.` : `Mensagem de ${label} gerada para ${target.username}.`);
    await loadBootstrap();
  } catch (error) { alert(error.message); }
}

async function applyTemporaryPassword(userId, password, username, options = {}) {
  const target = state.users.find((item) => String(item.id) === String(userId));
  if (!target) return false;
  await api(`/api/users/${userId}`, { method: 'PUT', body: JSON.stringify({ actor_user_id: state.user.id, username: target.username, full_name: target.full_name, password, role: target.role, company_id: target.company_id, active: target.active, force_password_change: 1 }) });
  const label = username || target.username;
  if (options.notify !== false) alert(`Senha provisória definida para ${label}.`);
  return true;
}

async function setTemporaryPassword(userId) {
  const target = state.users.find((item) => String(item.id) === String(userId));
  if (!target) return;
  try {
    const password = askTemporaryPassword('Temp1234');
    if (password === null) return;
    await applyTemporaryPassword(userId, password, target.username);
    await loadBootstrap();
  } catch (error) { alert(error.message); }
}

async function generateAndCopyTemporaryPassword(userId) {
  const target = state.users.find((item) => String(item.id) === String(userId));
  if (!target) return;
  try {
    const password = generateTemporaryPassword(12);
    await applyTemporaryPassword(userId, password, target.username, { notify: false });
    const copied = await copyTextToClipboard(password);
    alert(copied ? `Senha provisória gerada para ${target.username}: ${password}` : 'Senha provisória gerada, mas Não foi possí­vel copiar para a Área de transferÃÂªncia.');
    await loadBootstrap();
  } catch (error) { alert(error.message); }
}

// P0-2 — confirmação estilizada para ações destrutivas (substitui window.confirm).
// Cai para o confirm nativo se o módulo de UI helpers não estiver disponível.
async function confirmDestructive(opts) {
  const o = opts || {};
  if (typeof globalThis.dsConfirm === 'function') { return globalThis.dsConfirm(o); }
  return globalThis.confirm(o.message || '');
}

async function deleteUser(userId) {
  if (!(await confirmDestructive({ title: 'Remover usuário', message: 'Deseja remover este usuário?', confirmLabel: 'Remover', variant: 'danger' }))) return;
  try {
    await api(`/api/users/${userId}?${actorQuery()}`, { method: 'DELETE' });
    if (String(state.editingUserId || '') === String(userId)) resetUserForm();
    setUserFormFeedback('Usuário removido com sucesso.');
    await loadBootstrap();
  } catch (error) {
    setUserFormFeedback(error.message, true);
    alert(error.message);
  }
}

function resetUserForm() {
  state.editingUserId = null;
  refs.userForm.reset();
  if (refs.userLinkedEmployeeSearch) refs.userLinkedEmployeeSearch.value = '';
  setUserFormFeedback('');
  refs.userForm.elements.id.value = '';
  populateRoleOptions();
  syncUserFormAccess();
}

function dashboardInteractiveEmptyMessage(message) {
  return `<div class="dashboard-chart-empty">${message}</div>`;
}

function matchesEmployeeSearchText(item, searchValue) {
  const search = String(searchValue || '').trim().toLowerCase();
  if (!search) return true;
  const haystack = `${item.name || ''} ${item.employee_id_code || ''} ${item.id || ''}`.toLowerCase();
  return haystack.includes(search);
}

function applyUnitsFilters(items) {
  return items.filter((item) => {
    if (state.unitsFilters.company_id && String(item.company_id) !== String(state.unitsFilters.company_id)) return false;
    if (state.unitsFilters.type && String(item.unit_type) !== String(state.unitsFilters.type)) return false;
    if (state.unitsFilters.name && !String(item.name || '').toLowerCase().includes(state.unitsFilters.name)) return false;
    if (state.unitsFilters.city && !String(item.city || '').toLowerCase().includes(state.unitsFilters.city)) return false;
    return true;
  });
}

function applyEmployeesFilters(items, source = 'employees') {
  const filters = source === 'ops' ? state.employeesOpsFilters : state.employeesFilters;
  return items.filter((item) => {
    if (filters.company_id && String(item.company_id) !== String(filters.company_id)) return false;
    const employeeUnitId = String(item.current_unit_id || item.unit_id || '');
    if (filters.unit_id && employeeUnitId !== String(filters.unit_id)) return false;
    if (!matchesEmployeeSearchText(item, filters.search)) return false;
    if (filters.sector && !String(item.sector || '').toLowerCase().includes(filters.sector)) return false;
    if (filters.role_name && !String(item.role_name || '').toLowerCase().includes(filters.role_name)) return false;
    return true;
  });
}

// Escopo de visibilidade de EPI por unidade operacional. Espelha o backend
// (epi_backend/epi_scope.is_epi_visible_for_unit): um EPI aparece para uma
// unidade quando é de nível empresa (GLOBAL / "Todas as Unidades") ou pertence
// àquela unidade específica.
function epiVisibleForOperationalUnit(item, unitId) {
  const uid = String(unitId || '').trim();
  if (!uid) return true;
  const scopeType = String(item.scope_type || '').toUpperCase();
  const isCompanyLevel = scopeType === 'GLOBAL'
    || String(item.scope_label || '').toLowerCase().includes('todas as unidades');
  if (isCompanyLevel) return true;
  const epiUnit = String(item.unit_id || '');
  const scopeUnit = String(item.scope_unit_id || '');
  return epiUnit === uid || scopeUnit === uid;
}

// Restringe uma lista de EPIs ao escopo da unidade operacional do usuário
// (perfis com unidade fixa: uma unidade só enxerga os EPIs cadastrados nela,
// além dos EPIs de nível empresa). Administradores de empresa (sem unidade
// operacional) continuam vendo todos os EPIs da empresa.
function episForOperationalScope(epis) {
  const opUnit = String(state.user?.operational_unit_id || '').trim();
  if (!opUnit) return epis || [];
  return (epis || []).filter((item) => epiVisibleForOperationalUnit(item, opUnit));
}

function applyEpisFilters(items) {
  const restrictToCompanyLevelAllUnits = ['general_admin', 'registry_admin'].includes(state.user?.role)
    && String(state.episFilters.unit_id || '').trim() === EPI_COMPANY_LEVEL_FILTER_VALUE;
  return items.filter((item) => {
    if (state.episFilters.company_id && String(item.company_id) !== String(state.episFilters.company_id)) return false;
    if (restrictToCompanyLevelAllUnits) {
      const isCompanyLevel = String(item.scope_type || '').toUpperCase() === 'GLOBAL'
        || String(item.scope_label || '').toLowerCase().includes('todas as unidades');
      if (!isCompanyLevel) return false;
    }
    if (state.episFilters.unit_id && state.episFilters.unit_id !== EPI_COMPANY_LEVEL_FILTER_VALUE) {
      const unitId = String(item.unit_id || '');
      const scopeUnitId = String(item.scope_unit_id || '');
      if (unitId !== String(state.episFilters.unit_id) && scopeUnitId !== String(state.episFilters.unit_id)) return false;
    }
    if (state.episFilters.search) {
      const haystack = `${item.name || ''} ${item.purchase_code || ''}`.toLowerCase();
      if (!haystack.includes(state.episFilters.search)) return false;
    }
    if (state.episFilters.protection && !String(item.sector || '').toLowerCase().includes(state.episFilters.protection)) return false;
    if (state.episFilters.section && !String(item.epi_section || '').toLowerCase().includes(state.episFilters.section)) return false;
    if (state.episFilters.manufacturer && !String(item.manufacturer || '').toLowerCase().includes(state.episFilters.manufacturer)) return false;
    if (state.episFilters.supplier && !String(item.supplier_company || '').toLowerCase().includes(state.episFilters.supplier)) return false;
    if (state.episFilters.validity) { if (!_epiMatchesValidity(item, state.episFilters.validity)) return false; }
    return true;
  });
}

// Filtro por status de validade (deep-link dos indicadores do dashboard).
// CA (ca_expiry) rege a compra; validade do fabricante (epi_validity_date) rege
// o uso/estoque. Limite de "próximo" = 30 dias.
function _epiValidityDays(dateStr) {
  const raw = String(dateStr || '').trim();
  if (!raw) return null;
  const ts = Date.parse(raw);
  if (Number.isNaN(ts)) return null;
  return Math.floor((ts - Date.now()) / 86400000);
}
function _epiMatchesValidity(item, mode) {
  const caD = _epiValidityDays(item.ca_expiry);
  const prodD = _epiValidityDays(item.epi_validity_date);
  switch (mode) {
    case 'ca_expired': return caD !== null && caD < 0;
    case 'ca_expiring': return caD !== null && caD >= 0 && caD <= 30;
    case 'product_expired': return prodD !== null && prodD < 0;
    case 'product_expiring': return prodD !== null && prodD >= 0 && prodD <= 30;
    default: return true;
  }
}

// Deep-link dos indicadores de validade do dashboard → EPIs já filtrados.
function openEpisFilteredByValidity(status) {
  state.episFilters.validity = String(status || '');
  document.querySelector('.menu-link[data-view="epis"]')?.click();
  setTimeout(() => {
    if (refs.episFilterValidity) { refs.episFilterValidity.value = state.episFilters.validity; }
    if (typeof syncEpisSearchFilters === 'function') { syncEpisSearchFilters(); }
  }, 80);
}
globalThis.openEpisFilteredByValidity = openEpisFilteredByValidity;

// Deep-link do Dashboard: abre uma view e ativa uma sub-aba específica (vtab).
// Usado pelos cards que representam itens que vivem numa aba interna
// (ex.: "Bloqueio administrativo" → Estoque → Validade e Bloqueios).
function openViewSubtab(view, tab) {
  document.querySelector(`.menu-link[data-view="${view}"]`)?.click();
  if (!tab) return;
  setTimeout(() => {
    try {
      const nav = findViewTabsNav(view);
      if (nav) activateViewTab(nav, tab);
    } catch (_e) { /* aba indisponível para o perfil */ }
  }, 90);
}
globalThis.openViewSubtab = openViewSubtab;

function applyDeliveriesFilters(items) {
  return items.filter((item) => {
    if (state.deliveriesFilters.company_id && String(item.company_id) !== String(state.deliveriesFilters.company_id)) return false;
    const unitId = String(item.unit_id || item.current_unit_id || '');
    if (state.deliveriesFilters.unit_id && unitId !== String(state.deliveriesFilters.unit_id)) return false;
    if (state.deliveriesFilters.employee && !matchesEmployeeSearchText(item, state.deliveriesFilters.employee)) return false;
    if (state.deliveriesFilters.epi && !String(item.epi_name || '').toLowerCase().includes(state.deliveriesFilters.epi)) return false;
    const day = String(item.delivery_date || '').slice(0, 10);
    if (state.deliveriesFilters.date_from && day < state.deliveriesFilters.date_from) return false;
    if (state.deliveriesFilters.date_to && day > state.deliveriesFilters.date_to) return false;
    if (state.deliveriesFilters.status === 'devolved' && !String(item.returned_date || '').trim()) return false;
    if (state.deliveriesFilters.status === 'delivered' && String(item.returned_date || '').trim()) return false;
    return true;
  });
}

function applyFichaEmployeeFilters(items) {
  return items.filter((item) => {
    if (state.fichaFilters.company_id && String(item.company_id) !== String(state.fichaFilters.company_id)) return false;
    const unitId = String(item.current_unit_id || item.unit_id || '');
    if (state.fichaFilters.unit_id && unitId !== String(state.fichaFilters.unit_id)) return false;
    return matchesEmployeeSearchText(item, state.fichaFilters.search);
  });
}

function employmentTypeLabel(value) {
  const normalized = String(value || '').trim().toLowerCase();
  if (normalized === 'clt') return tr('employee.vincClt', 'CLT');
  if (normalized === 'terceirizado') return tr('employee.vincOutsourced', 'Terceirizado');
  if (normalized === 'temporário' || normalized === 'temporario') return tr('employee.vincTemporary', 'Temporário');
  if (normalized === 'prestador de serviço' || normalized === 'prestador de servico') return tr('employee.vincServiceProvider', 'Prestador de Serviço');
  if (normalized === 'menor aprendiz') return tr('employee.vincApprentice', 'Menor Aprendiz');
  if (normalized === 'praticante') return tr('employee.vincTrainee', 'Praticante');
  if (normalized === 'estagiário' || normalized === 'estagiario') return tr('employee.vincIntern', 'Estagiário');
  return value || 'CLT';
}

function allocationTypeLabel(value) {
  return value === 'temporary' ? tr('employee.allocationTemporary', 'Temporário') : tr('employee.allocationPrimary', 'Principal');
}

function buildEmployeeRow(item, canManageRecords) {
  const actions = canManageRecords ? `<div class="action-group"><button class="ghost" data-employee-edit="${item.id}">${tr('edit', 'Editar')}</button><button class="ghost" data-employee-archive="${item.id}">${tr('employee.archive', 'Arquivar')}</button></div>` : '-';
  const allocation = allocationTypeLabel(item.unit_allocation_type);
  const preferredLabel = String(item.preferred_contact_channel || '').toLowerCase() === 'email' ? 'E-mail' : 'WhatsApp';
  const contact = [item.whatsapp ? `WhatsApp: ${item.whatsapp}` : '', item.email ? `E-mail: ${item.email}` : '', `${tr('employee.preferredContactLabel', 'Preferido')}: ${preferredLabel}`].filter(Boolean).join('<br>') || '-';
  const tipoVinculoRaw = item.tipo_vinculo || 'CLT';
  const tipoVinculo = employmentTypeLabel(tipoVinculoRaw);
  const empresaOrigem = tipoVinculoRaw !== 'CLT' && item.empresa_origem ? `<br><small>${item.empresa_origem}</small>` : '';
  const checkCell = employeesBulk ? `<td class="ds-bulk-cell"><input type="checkbox" class="ds-bulk-checkbox" data-emp-check="${item.id}" aria-label="Selecionar ${item.name}"${employeesBulk.has(item.id) ? ' checked' : ''}></td>` : '';
  return `<tr>${checkCell}<td>${item.company_name}</td><td>${item.employee_id_code}</td><td>${item.name}</td><td>${contact}</td><td>${item.sector}</td><td>${item.role_name}</td><td>${tipoVinculo}${empresaOrigem}</td><td>${item.current_unit_name || item.unit_name}</td><td>${allocation}</td><td>-</td><td>${actions}</td></tr>`;
}

function buildEmployeeOpsRow(item) {
  const allocation = allocationTypeLabel(item.unit_allocation_type);
  const tipoVinculoRaw = item.tipo_vinculo || 'CLT';
  const tipoVinculo = employmentTypeLabel(tipoVinculoRaw);
  const empresaOrigem = tipoVinculoRaw !== 'CLT' && item.empresa_origem ? `<br><small>${item.empresa_origem}</small>` : '';
  return `<tr><td>${item.company_name}</td><td>${item.employee_id_code}</td><td>${item.name}</td><td>${item.sector}</td><td>${item.role_name}</td><td>${tipoVinculo}${empresaOrigem}</td><td>${item.current_unit_name || item.unit_name}</td><td>${allocation}</td><td><button class="ghost" style="font-size:12px;padding:4px 10px;" data-ops-select-employee="${item.id}">${tr('employee.select', 'Selecionar')}</button></td></tr>`;
}

function epiProtectionLabel(value) {
  const labels = {
    'Proteção-Membros Superiores': tr('epi.protectionUpperLimbs', 'Proteção-Membros Superiores'),
    'Proteção-Membros Inferiores': tr('epi.protectionLowerLimbs', 'Proteção-Membros Inferiores'),
    'Proteção-Auditiva': tr('epi.protectionHearing', 'Proteção-Auditiva'),
    'Proteção-Olhos e Face': tr('epi.protectionEyesFace', 'Proteção-Olhos e Face'),
    'Proteção-Respiratória': tr('epi.protectionRespiratory', 'Proteção-Respiratória'),
    'Proteção-Mãos e Braços': tr('epi.protectionHandsArms', 'Proteção-Mãos e Braços'),
    'Proteção-Cabeça': tr('epi.protectionHead', 'Proteção-Cabeça'),
    'Proteção-Combate a Incêndio': tr('epi.protectionFirefighting', 'Proteção-Combate a Incêndio'),
    'Proteção-Contra Queda': tr('epi.protectionFallProtection', 'Proteção-Contra Queda'),
    'Proteção-Eletricidade': tr('epi.protectionElectricity', 'Proteção-Eletricidade')
  };
  return labels[value] || value || '-';
}

function epiMeasureLabel(value) {
  const normalized = String(value || '').toLowerCase();
  if (normalized === 'unidade') return tr('epi.measureUnit', 'Unidade');
  if (normalized === 'par') return tr('epi.measurePair', 'Par');
  return value || '-';
}

function buildEpiRow(item, canManageEpiRecords) {
  const actions = canManageEpiRecords ? `<div class="action-group"><button class="ghost" data-epi-edit="${item.id}">${tr('edit', 'Editar')}</button><button class="ghost" data-epi-archive="${item.id}">${tr('epi.archive', 'Arquivar')}</button></div>` : '-';
  const scopeLabel = item.scope_label
    || (String(item.scope_type || '').toUpperCase() === 'GLOBAL'
      ? tr('epi.allUnits', 'Todas as Unidades')
      : `${item.unit_name || '-'}${Number(item.is_joint_venture || 0) === 1 ? ' (Joint Venture)' : ''}`);
  return `<tr><td>${item.company_name}</td><td>${scopeLabel}</td><td>${item.name}</td><td>${item.purchase_code}</td><td>${epiProtectionLabel(item.sector)}</td><td>${item.epi_section || '-'}</td><td>${item.manufacturer || '-'}</td><td>${item.supplier_company || '-'}</td><td>${item.active_joinventure || '-'}</td><td>${epiMeasureLabel(item.unit_measure)}</td><td>${actions}</td></tr>`;
}

function buildDeliveryRow(item) {
  return `<tr><td>${item.company_name}</td><td>${item.employee_id_code}</td><td>${item.employee_name}</td><td>${item.epi_name}</td><td>${item.quantity}</td><td>${item.quantity_label}</td><td>${formatDate(item.delivery_date)}</td></tr>`;
}

function formatUnitTableRow(item, canManageUnitRecords) {
  const actions = canManageUnitRecords ? `<div class="action-group"><button class="ghost" data-unit-edit="${item.id}">${tr('edit', 'Editar')}</button><button class="ghost" data-unit-archive="${item.id}">${tr('unit.archive', 'Arquivar')}</button></div>` : '-';
  // Sem esta coluna, uma empresa com vários CNPJs vê uma lista em que todas as
  // unidades parecem iguais — e é justamente aqui que a distinção importa.
  const legalEntity = escapeHtml(unitLegalEntityLabel(item)) || '-';
  return `<tr><td>${item.company_name}</td><td>${legalEntity}</td><td>${item.name}</td><td>${unitTypeLabel(item.unit_type)}</td><td>${item.city}</td><td>${actions}</td></tr>`;
}

const DELIVERIES_PER_PAGE = 20;
const EMPLOYEES_PER_PAGE = 20;
const EPIS_PER_PAGE = 20;
// Seleção em lote da listagem de Colaboradores (componente reutilizável do DS).
const employeesBulk = globalThis.dsCreateBulkSelection ? globalThis.dsCreateBulkSelection() : null;

function currentEmployeesBulkScope() {
  // Base atual (empresa + filtros) — a seleção e o "selecionar todos da página"
  // operam sobre o que está visível, respeitando os filtros ativos.
  return applyEmployeesFilters(filterByUserCompany(state.employees), 'employees');
}

function exportSelectedEmployeesCsv() {
  if (!employeesBulk || employeesBulk.count() === 0) return;
  const ids = new Set(employeesBulk.ids().map(String));
  const rows = currentEmployeesBulkScope().filter((e) => ids.has(String(e.id)));
  if (!rows.length) return;
  const header = ['Empresa', 'ID', 'Nome', 'CPF', 'E-mail', 'WhatsApp', 'Setor', 'Função', 'Tipo de Vínculo', 'Unidade'];
  const lines = rows.map((e) => [
    e.company_name, e.employee_id_code, e.name, e.cpf, e.email, e.whatsapp,
    e.sector, e.role_name, employmentTypeLabel(e.tipo_vinculo || 'CLT'),
    e.current_unit_name || e.unit_name,
  ]);
  const csv = [header, ...lines]
    .map((row) => row.map((v) => `"${String(v == null ? '' : v).replaceAll('"', '""')}"`).join(';'))
    .join('\n');
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = 'colaboradores-selecionados.csv';
  link.click();
  URL.revokeObjectURL(link.href);
}

function renderEmployeesBulkUi(pageIds) {
  if (!employeesBulk || !refs.employeesBulkBar) return;
  refs.employeesBulkBar.innerHTML = globalThis.dsBulkBar(
    employeesBulk.count(),
    [{ id: 'export', label: tr('bulk.exportCsv', 'Exportar CSV'), variant: 'btn-primary' }],
    { labelPlural: tr('bulk.selectedPlural', 'selecionados'), labelSingular: tr('bulk.selectedSingular', 'selecionado'), clearLabel: tr('bulk.clear', 'Limpar seleção') }
  );
  if (refs.employeesSelectAll) {
    const st = employeesBulk.pageState(pageIds);
    refs.employeesSelectAll.checked = st === 'all';
    refs.employeesSelectAll.indeterminate = st === 'some';
  }
}

function renderTables() {
  const canManageRecords = ['master_admin', 'general_admin', 'registry_admin'].includes(state.user?.role);
  const canManageStructuralRecords = ['general_admin', 'registry_admin'].includes(state.user?.role);
  const filteredUnits = applyUnitsFilters(filterByUserCompany(state.units));
  const filteredEmployeesBase = applyEmployeesFilters(filterByUserCompany(state.employees), 'employees');
  const filteredEmployeesOps = applyEmployeesFilters(filterByUserCompany(state.employees), 'ops');
  const filteredEpis = applyEpisFilters(episForOperationalScope(filterByUserCompany(state.epis)));
  const filteredDeliveries = applyDeliveriesFilters(filterByUserCompany(state.deliveries));
  refs.usersTable.innerHTML = filteredUsers().map((item) => `<tr><td>${item.full_name}</td><td>${renderBadge('role', item.role, roleLabel(item.role))}</td><td>${userStatusBadges(item)}</td><td>${item.company_name || 'Sistema'}</td><td>${userActionButtons(item)}</td></tr>`).join('') || globalThis.dsTableState({ colspan: 5, message: 'Sem usuários cadastrados.' });
  refs.unitsTable.innerHTML = filteredUnits.map((item) => formatUnitTableRow(item, canManageStructuralRecords)).join('') || globalThis.dsTableState({ colspan: 6, message: tr('unit.empty', 'Sem unidades.') });
  // P1-1 — paginação client-side da tabela de Colaboradores (alta volumetria).
  const employeesPage = globalThis.dsPaginate(filteredEmployeesBase, state.pagination?.employees || 1, EMPLOYEES_PER_PAGE);
  if (state.pagination) state.pagination.employees = employeesPage.page;
  // Mantém a seleção em lote coerente com os filtros atuais (remove ids fora do escopo).
  if (employeesBulk) employeesBulk.retain(filteredEmployeesBase.map((e) => e.id));
  const employeesColspan = employeesBulk ? 12 : 11;
  refs.employeesTable.innerHTML = employeesPage.pageItems.map((item) => buildEmployeeRow(item, canManageRecords)).join('') || globalThis.dsTableState({ colspan: employeesColspan, message: tr('employee.empty', 'Sem colaboradores.') });
  if (refs.employeesPagination) refs.employeesPagination.innerHTML = globalThis.dsPaginationControls(employeesPage);
  renderEmployeesBulkUi(employeesPage.pageItems.map((e) => e.id));
  if (refs.employeesOpsTable) refs.employeesOpsTable.innerHTML = filteredEmployeesOps.map((item) => buildEmployeeOpsRow(item)).join('') || globalThis.dsTableState({ colspan: 9, message: tr('employee.empty', 'Sem colaboradores.') });
  // Paginação client-side do catálogo de EPIs (alta volumetria) — mesmo padrão P1-1.
  const episPage = globalThis.dsPaginate(filteredEpis, state.pagination?.epis || 1, EPIS_PER_PAGE);
  if (state.pagination) state.pagination.epis = episPage.page;
  refs.episTable.innerHTML = episPage.pageItems.map((item) => buildEpiRow(item, canManageStructuralRecords)).join('') || globalThis.dsTableState({ colspan: 11, message: tr('epi.empty', 'Sem EPIs.') });
  if (refs.episPagination) refs.episPagination.innerHTML = globalThis.dsPaginationControls(episPage);
  // P1-1 — paginação client-side da tabela de entregas (alta volumetria).
  const deliveriesPage = globalThis.dsPaginate(filteredDeliveries, state.pagination?.deliveries || 1, DELIVERIES_PER_PAGE);
  if (state.pagination) state.pagination.deliveries = deliveriesPage.page;
  refs.deliveriesTable.innerHTML = deliveriesPage.pageItems.map(buildDeliveryRowWithDevolution).join('') || globalThis.dsTableState({ colspan: 10, message: 'Sem entregas registradas.' });
  if (refs.deliveriesPagination) refs.deliveriesPagination.innerHTML = globalThis.dsPaginationControls(deliveriesPage);
  renderDeliveriesFilterChips();
  renderApprovedEpis();
  renderPurchaseFunctionControls();
  if (isPhase3ModernUiEnabled()) {
    updatePhase3ContextStatus('colaboradores', 'success', `${filteredEmployeesBase.length} colaborador(es) visível(is)`);
    updatePhase3ContextStatus('gestao-colaborador', 'success', `${filteredEmployeesOps.length} vínculo(s) no filtro`);
    updatePhase3ContextStatus('epis', 'success', `${filteredEpis.length} EPI(s) no filtro`);
  }
}

function populateStockProtectionFilter() {
  if (!refs.stockFilterProtection) return;
  const epiProtectionField = document.querySelector('#epi-form [name="sector"]');
  const fallbackOptions = [
    'Proteção-Membros Superiores',
    'Proteção-Membros Inferiores',
    'Proteção-Auditiva',
    'Proteção-Olhos e Face',
    'Proteção-Mãos e braços',
    'Proteção-Respiratória',
    'Proteção-Cabeça',
    'Proteção-Contra Incêndio', 
    'Proteção-Contra Queda',
    'Proteção-Eletricidade'
  ];
  const options = Array.from(epiProtectionField?.options || [])
    .map((option) => String(option.value || '').trim())
    .filter(Boolean);
  const protectionOptions = options.length ? options : fallbackOptions;
  const protectionHtml = protectionOptions.map((value) => `<option value="${value}">${epiProtectionLabel(value)}</option>`).join('');
  refs.stockFilterProtection.innerHTML = `<option value="">${tr('employee.filterAllUnits', 'Todas')}</option>${protectionHtml}`;
}

async function loadStockEpis() {
  if (!hasPermission('stock:view')) return;
  const params = new URLSearchParams();
  params.set('actor_user_id', String(state.user.id));
  const companyId = document.getElementById('stock-company')?.value || state.user?.company_id || '';
  const unitId = document.getElementById('stock-unit')?.value || state.user?.operational_unit_id || '';
  if (companyId) params.set('company_id', String(companyId));
  if (unitId) params.set('unit_id', String(unitId));
  if (refs.stockFilterProtection?.value) params.set('protection', refs.stockFilterProtection.value);
  if (refs.stockFilterName?.value) params.set('name', refs.stockFilterName.value);
  if (refs.stockFilterSection?.value) params.set('section', refs.stockFilterSection.value);
  if (refs.stockFilterManufacturer?.value) params.set('manufacturer', refs.stockFilterManufacturer.value);
  if (refs.stockFilterCa?.value) params.set('ca', refs.stockFilterCa.value);
  const payload = await api(`/api/stock/epis?${params.toString()}`);
  state.stockEpis = payload.items || [];
  renderStockEpis();
  syncSelectedEpiMinimumStockField();
  refreshStockMovementItemsFromLocal();
}

function refreshStockMovementItemsFromLocal() {
  const companyId = document.getElementById('stock-company')?.value || state.user?.company_id || '';
  const unitId = document.getElementById('stock-unit')?.value || state.user?.operational_unit_id || '';
  const stockByEpiId = new Map((state.stockEpis || []).map((item) => [String(item.id), item]));
  const baseItems = filterByUserCompany(state.epis).filter((item) => {
    if (companyId && String(item.company_id) !== String(companyId)) return false;
    if (unitId && !stockByEpiId.has(String(item.id))) return false;
    return true;
  }).map((item) => {
    const stockEntry = stockByEpiId.get(String(item.id));
    return {
      ...item,
      stock: Number(stockEntry?.stock ?? 0),
      size_balances: Array.isArray(stockEntry?.size_balances) ? stockEntry.size_balances : []
    };
  });
  state.stockEpiMovementItems = baseItems;
  renderStockEpiSearchResults();
}

let stockSearchTimer = null;
function scheduleStockMovementSearchLoad() {
  if (stockSearchTimer) clearTimeout(stockSearchTimer);
  stockSearchTimer = setTimeout(() => {
    loadStockMovementSearchItems().catch((error) => console.error(error));
  }, 180);
}

async function loadStockMovementSearchItems() {
  if (!hasPermission('stock:view')) return;
  const params = new URLSearchParams();
  params.set('actor_user_id', String(state.user.id));
  const companyId = document.getElementById('stock-company')?.value || state.user?.company_id || '';
  const unitId = document.getElementById('stock-unit')?.value || state.user?.operational_unit_id || '';
  if (companyId) params.set('company_id', String(companyId));
  if (unitId) params.set('unit_id', String(unitId));
  const payload = await api(`/api/stock/epis?${params.toString()}`);
  state.stockEpiMovementItems = payload.items || [];
  renderStockEpiSearchResults();
}

function selectedStockEpi() {
  const epiField = document.getElementById('stock-epi');
  const selectedId = String(epiField?.value || '');
  if (!selectedId) return null;
  return (state.stockEpis || []).find((item) => String(item.id) === selectedId)
    || filterByUserCompany(state.epis).find((item) => String(item.id) === selectedId)
    || null;
}

async function loadStockMovementsReport() {
  const tbody = document.getElementById('smr-tbody');
  const summary = document.getElementById('smr-summary');
  const hint = document.getElementById('smr-hint');
  if (!tbody) return;
  try {
    const params = new URLSearchParams({ actor_user_id: String(state.user?.id || '') });
    const year = document.getElementById('smr-year')?.value?.trim();
    const month = document.getElementById('smr-month')?.value;
    const epiId = document.getElementById('smr-epi')?.value;
    const movType = document.getElementById('smr-movement-type')?.value;
    const srcType = document.getElementById('smr-source-type')?.value;
    const unitId = document.getElementById('smr-unit')?.value;
    const compliance = document.getElementById('smr-compliance')?.value;
    if (year) params.set('year', year);
    if (month) params.set('month', month);
    if (epiId) params.set('epi_id', epiId);
    if (movType) params.set('movement_type', movType);
    if (srcType) params.set('source_type', srcType);
    if (unitId) params.set('unit_id', unitId);
    // Conformidade NT 146/2015: CA vencido vs. validade do fabricante (próxima/vencida).
    if (compliance === 'ca_expired') params.set('ca_status', 'expired');
    else if (compliance === 'manufacturer_expiring') params.set('manufacturer_validity', 'expiring');
    else if (compliance === 'manufacturer_expired') params.set('manufacturer_validity', 'expired');
    tbody.innerHTML = `<tr><td colspan="14" style="text-align:center;color:var(--color-text-muted);">${tr('stock.loading', 'Carregando...')}</td></tr>`;
    const res = await api(`/api/stock/movements/report?${params.toString()}`);
    renderStockMovementsReport(res.items || []);
  } catch (e) {
    if (tbody) tbody.innerHTML = `<tr><td colspan="14" style="color:var(--color-danger);">Erro: ${escapeHtml(e.message || 'Falha ao carregar')}</td></tr>`;
  }
}

const SOURCE_TYPE_LABELS = {
  purchase_request: tr('stock.purchaseRequest', 'Requisição de Compra'),
  manual: tr('stock.manual', 'Manual'),
  delivery: tr('delivery.title', 'Entrega'),
  return: tr('stock.return', 'Devolução'),
  purchase_order: tr('purchase.order', 'Ordem de Compra'),
};

// Conformidade CA/validade de uma movimentação (dados vindos do backend:
// item.ca, item.ca_expiry, item.epi_validity_date). Indicadores:
// 🔴 vencido · 🟡 próximo do vencimento (≤30d) · 🟢 normal · — sem data.
function stockComplianceBadge(item) {
  const today = new Date().toISOString().slice(0, 10);
  const soon = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10);
  const caExp = String(item.ca_expiry || '').slice(0, 10);
  const valExp = String(item.epi_validity_date || '').slice(0, 10);
  const dates = [caExp, valExp].filter(Boolean);
  if (!dates.length) return '<span title="Sem data de validade">—</span>';
  const expired = dates.some((d) => d < today);
  const expiring = !expired && dates.some((d) => d >= today && d <= soon);
  if (expired) return `<span title="${tr('stock.expired', 'Vencido')}" style="color:var(--color-danger);font-weight:600;">🔴 ${tr('stock.expired', 'Vencido')}</span>`;
  if (expiring) return `<span title="${tr('stock.expiringSoon', 'Próximo do vencimento')}" style="color:var(--pending,#b45309);font-weight:600;">🟡 ${tr('stock.expiringSoon', 'Próximo')}</span>`;
  return `<span title="${tr('stock.compliant', 'Conforme')}" style="color:var(--color-success);">🟢 ${tr('stock.compliant', 'Normal')}</span>`;
}

function renderStockMovementsReport(items) {
  const tbody = document.getElementById('smr-tbody');
  const summary = document.getElementById('smr-summary');
  const hint = document.getElementById('smr-hint');
  if (!tbody) return;
  const totalIn = items.filter(i => i.movement_type === 'in').reduce((s, i) => s + Number(i.quantity || 0), 0);
  const totalOut = items.filter(i => i.movement_type === 'out').reduce((s, i) => s + Number(i.quantity || 0), 0);
  if (summary) {
    summary.innerHTML = items.length
      ? `<span><strong>${items.length}</strong> ${tr('stock.movements', 'movimentações')}</span>`
        + `<span style="color:var(--color-success);">${tr('stock.entries', 'Entradas')}: <strong>${totalIn}</strong></span>`
        + `<span style="color:var(--color-danger);">${tr('stock.exits', 'Saídas')}: <strong>${totalOut}</strong></span>`
      : '';
  }
  if (hint) {
    hint.style.display = items.length >= 500 ? '' : 'none';
    hint.textContent = tr('stock.limitedResult', 'Resultado limitado a 500 registros. Use os filtros para refinar.');
  }
  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="14" style="text-align:center;color:var(--color-text-muted);">${tr('stock.noMovements', 'Nenhuma movimentação encontrada para os filtros selecionados.')}</td></tr>`;
    return;
  }
  const h = (v) => escapeHtml(String(v ?? '—'));
  tbody.innerHTML = items.map(item => {
    const typeLabel = item.movement_type === 'in'
      ? `<span style="color:var(--color-success);font-weight:600;">▲ ${tr('stock.entry', 'Entrada')}</span>`
      : `<span style="color:var(--color-danger);font-weight:600;">▼ ${tr('stock.exit', 'Saída')}</span>`;
    const srcLabel = SOURCE_TYPE_LABELS[item.source_type] || h(item.source_type);
    const ref = item.source_id ? `#${item.source_id}` : '—';
    const sizeInfo = [
      item.glove_size && item.glove_size !== 'N/A' ? `${tr('stock.gloveShort', 'Luva')}:${item.glove_size}` : '',
      item.size && item.size !== 'N/A' ? `${tr('stock.sizeShort', 'Tam')}:${item.size}` : '',
      item.uniform_size && item.uniform_size !== 'N/A' ? `${tr('stock.uniformShort', 'Unif')}:${item.uniform_size}` : ''
    ].filter(Boolean).join(' ') || '';
    const epiDisplay = sizeInfo ? `${h(item.epi_name)} <small style="color:var(--color-text-muted);">${sizeInfo}</small>` : h(item.epi_name);
    const caCell = item.ca
      ? `${h(item.ca)}${item.ca_expiry ? ` <small style="color:var(--color-text-muted);">${formatDate(item.ca_expiry)}</small>` : ''}`
      : '—';
    return `<tr>
      <td style="font-size:12px;white-space:nowrap;">${formatDate(item.created_at)}</td>
      <td>${epiDisplay}</td>
      <td style="font-size:12px;">${caCell}</td>
      <td style="font-size:12px;white-space:nowrap;">${item.epi_validity_date ? formatDate(item.epi_validity_date) : '—'}</td>
      <td style="font-size:12px;white-space:nowrap;">${stockComplianceBadge(item)}</td>
      <td style="font-size:12px;">${h(item.unit_name)}</td>
      <td>${typeLabel}</td>
      <td style="font-weight:600;">${h(item.quantity)}</td>
      <td style="color:var(--color-text-muted);font-size:12px;">${h(item.previous_stock)}</td>
      <td style="font-weight:600;">${h(item.new_stock)}</td>
      <td style="font-size:12px;">${srcLabel}</td>
      <td style="font-size:12px;">${ref}</td>
      <td style="font-size:12px;">${h(item.actor_name)}</td>
      <td style="font-size:12px;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${h(item.notes)}">${h(item.notes)}</td>
    </tr>`;
  }).join('');
}

function setupStockMovementsReport() {
  const form = document.getElementById('stock-movements-report-form');
  if (!form || form.dataset.smrBound) return;
  form.dataset.smrBound = '1';
  safeOn(form, 'submit', (e) => {
    e.preventDefault();
    loadStockMovementsReport().catch(console.error);
  });
  const epiSelect = document.getElementById('smr-epi');
  if (epiSelect) {
    const epis = episForOperationalScope(filterByUserCompany(state.epis || []));
    epiSelect.innerHTML = `<option value="">${tr('unit.filterAll', 'Todos')}</option>`
      + epis.map(ep => `<option value="${ep.id}">${escapeHtml(ep.name || '')}</option>`).join('');
  }
  const role = state.user?.role || '';
  const unitLabel = document.getElementById('smr-unit-label');
  const unitSelect = document.getElementById('smr-unit');
  if (unitLabel && unitSelect && (role === 'general_admin' || role === 'registry_admin' || role === 'master_admin')) {
    unitLabel.style.display = '';
    const units = filterByUserCompany(state.units || []);
    unitSelect.innerHTML = `<option value="">${tr('unit.filterAllUnits', 'Todas')}</option>`
      + units.map(u => `<option value="${u.id}">${escapeHtml(u.name || '')}</option>`).join('');
  }
  // Aprovador: mostrar unidade e botão solicitar relatório
  if (role === 'approver') {
    const approverUnitLabel = document.getElementById('smr-unit-label');
    const approverUnitSelect = document.getElementById('smr-unit');
    if (approverUnitLabel && approverUnitSelect) {
      approverUnitLabel.style.display = '';
      const approverUnits = (state.units || []).filter(u => String(u.company_id) === String(state.user?.company_id));
      approverUnitSelect.innerHTML = `<option value="">${tr('unit.filterAllUnits', 'Todas')}</option>`
        + approverUnits.map(u => `<option value="${u.id}">${escapeHtml(u.name || '')}</option>`).join('');
    }
    const reqBtn = document.getElementById('smr-request-report-btn');
    if (reqBtn) reqBtn.style.display = '';
  }
  // Admin Local: mostrar solicitações pendentes de relatório
  if (role === 'admin' || role === 'general_admin' || role === 'registry_admin') {
    loadPendingReportRequests().catch(() => {});
  }
  bindAppListener(document.getElementById('smr-request-report-btn'), 'click', openRequestReportModal);
  bindAppListener(document.getElementById('smr-req-report-confirm'), 'click', submitReportRequest);
  bindAppListener(document.getElementById('smr-req-report-cancel'), 'click', () => {
    const modal = document.getElementById('smr-request-report-modal');
    if (modal) modal.style.display = 'none';
  });
}

function openRequestReportModal() {
  const modal = document.getElementById('smr-request-report-modal');
  if (!modal) return;
  const unitSel = document.getElementById('smr-req-unit');
  if (unitSel) {
    const units = (state.units || []).filter(u => String(u.company_id) === String(state.user?.company_id));
    unitSel.innerHTML = `<option value="">${tr('epi.allUnits', 'Todas as unidades')}</option>`
      + units.map(u => `<option value="${u.id}">${escapeHtml(u.name || '')}</option>`).join('');
  }
  const yearSel = document.getElementById('smr-req-year');
  if (yearSel && !yearSel.value) yearSel.value = new Date().getFullYear();
  modal.style.display = 'flex';
}

async function submitReportRequest() {
  const modal = document.getElementById('smr-request-report-modal');
  const unitId = document.getElementById('smr-req-unit')?.value;
  const year = document.getElementById('smr-req-year')?.value;
  const month = document.getElementById('smr-req-month')?.value;
  const notes = document.getElementById('smr-req-notes')?.value?.trim();
  try {
    await api('/api/report-requests', {
      method: 'POST',
      body: JSON.stringify({
        actor_user_id: state.user?.id,
        unit_id: unitId ? Number(unitId) : null,
        period_year: year ? Number(year) : null,
        period_month: month ? Number(month) : null,
        notes: notes || ''
      })
    });
    if (modal) modal.style.display = 'none';
    showToast('Relatório solicitado com sucesso. O Administrador Local foi notificado.');
  } catch(e) {
    showToast('Erro ao solicitar relatório: ' + (e.message || 'Falha'), 'error');
  }
}

async function loadPendingReportRequests() {
  const container = document.getElementById('smr-pending-requests');
  if (!container) return;
  try {
    const res = await api(`/api/report-requests?${actorQuery()}&status=pending`);
    const pending = (res.items || []).filter(r => r.status === 'pending');
    if (!pending.length) {
      container.style.display = 'none';
      return;
    }
    container.style.display = '';
    const h = (v) => escapeHtml(String(v ?? '—'));
    container.innerHTML = `<div style="font-weight:600;margin-bottom:8px;color:var(--color-warning);">Solicitações de Relatório Pendentes (${pending.length})</div>`
      + pending.map(r => {
        const period = r.period_year ? `${r.period_year}${r.period_month ? '/' + String(r.period_month).padStart(2,'0') : ''}` : 'Todos os períodos';
        return `<div style="border:1px solid var(--color-border);border-radius:6px;padding:10px;margin-bottom:8px;background:var(--warning-soft);">
          <div><strong>${h(r.requester_name)}</strong> solicitou relatório para <strong>${h(r.unit_name || 'todas as unidades')}</strong></div>
          <div style="font-size:12px;color:var(--color-text-muted);">Período: ${period} | ${formatDate(r.created_at)}</div>
          ${r.notes ? `<div style="font-size:12px;margin-top:4px;">${h(r.notes)}</div>` : ''}
          <button class="btn ghost" style="margin-top:8px;font-size:12px;" data-mark-report-done="${r.id}">Marcar como Enviado</button>
        </div>`;
      }).join('');
    container.querySelectorAll('[data-mark-report-done]').forEach(btn => {
      bindAppListener(btn, 'click', async () => {
        const id = btn.dataset.markReportDone;
        try {
          await api(`/api/report-requests/${id}/mark-done`, {
            method: 'POST', body: JSON.stringify({ actor_user_id: state.user?.id })
          });
          loadPendingReportRequests().catch(() => {});
        } catch(e) {
          showToast('Erro: ' + (e.message || 'Falha'), 'error');
        }
      });
    });
  } catch(e) {
    container.style.display = 'none';
  }
}

function syncSelectedEpiMinimumStockField() {
  const valueField = document.getElementById('stock-minimum-selected-value');
  const editButton = document.getElementById('stock-minimum-selected-edit');
  const saveButton = document.getElementById('stock-minimum-selected-save');
  const selected = selectedStockEpi();
  if (!valueField) return;
  const selectedId = selected?.id ? String(selected.id) : null;
  const keepEditingCurrentEpi = Boolean(
    state.stockMinimumEditor.editing
    && selectedId
    && String(state.stockMinimumEditor.epiId || '') === selectedId
  );
  if (keepEditingCurrentEpi) {
    valueField.focus();
    valueField.select();
  } else {
    valueField.value = String(Number(selected?.minimum_stock ?? 0));
    valueField.readOnly = true;
    valueField.classList.remove('is-editing');
    state.stockMinimumEditor.editing = false;
    state.stockMinimumEditor.epiId = selectedId;
  }
  const enabled = canManageMinimumStock() && Boolean(selected?.id);
  if (editButton) editButton.disabled = !enabled;
  if (saveButton) saveButton.disabled = !enabled || !keepEditingCurrentEpi;
}

function toggleSelectedMinimumStockEditMode(editing) {
  const valueField = document.getElementById('stock-minimum-selected-value');
  const saveButton = document.getElementById('stock-minimum-selected-save');
  const selected = selectedStockEpi();
  if (!valueField) return;
  if (editing && !selected?.id) return;
  state.stockMinimumEditor.editing = Boolean(editing);
  state.stockMinimumEditor.epiId = selected?.id ? String(selected.id) : null;
  valueField.readOnly = !editing;
  valueField.classList.toggle('is-editing', Boolean(editing));
  if (editing) {
    valueField.focus();
    valueField.select();
  }
  if (saveButton) saveButton.disabled = !canManageMinimumStock() || !selected?.id || !editing;
  if (!valueField) return;
  valueField.readOnly = !editing;
  if (editing) valueField.focus();
  if (saveButton) saveButton.disabled = !canManageMinimumStock() || !selectedStockEpi();
}

async function saveSelectedEpiMinimumStock() {
  if (!canManageMinimumStock()) {
    alert('Apenas Administrador Local e Gestor de EPI podem gerenciar estoque mí­nimo.');
    return;
  }
  if (!requirePermission('stock:adjust')) return;
  const selected = selectedStockEpi();
  const valueField = document.getElementById('stock-minimum-selected-value');
  if (!selected?.id || !valueField) return alert('Selecione um EPI para definir o estoque mí­nimo.');
  const minimumStock = Math.max(0, Number(valueField.value || 0));
  try {
    await api('/api/stock/minimum', {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user.id, epi_id: Number(selected.id), minimum_stock: minimumStock })
    });
    for (const list of [state.stockEpis, state.epis]) {
      const target = (list || []).find((item) => String(item.id) === String(selected.id));
      if (target) target.minimum_stock = minimumStock;
    }
    valueField.value = String(minimumStock);
    toggleSelectedMinimumStockEditMode(false);
    state.stockMinimumEditor.epiId = String(selected.id);
    await loadStockEpis();
    await loadStockEpis();
    alert('Estoque mí­nimo salvo com sucesso.');
  } catch (error) {
    alert(error.message);
  }
}

function stockEpiMatchesMovementSearch(item) {
  const searchTerms = `${String(refs.stockEpiMovementSearchName?.value || '').trim()} ${String(refs.stockEpiMovementSearchManufacturer?.value || '').trim()}`
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean);
  if (!searchTerms.length) return true;
  const haystack = [
    item.name,
    item.manufacturer,
    item.ca,
    item.sector,
    item.epi_section,
    item.glove_size,
    item.size,
    item.uniform_size,
    ...(Array.isArray(item.size_balances) ? item.size_balances.map(formatItemSizeDisplay) : []),
    item.model_reference
  ].map((value) => String(value || '').toLowerCase()).join(' ');
  if (!searchTerms.every((term) => haystack.includes(term))) return false;
  return true;
}

function renderStockEpiSearchResults() {
  const list = refs.stockEpiMovementSearchResults;
  if (!list) return;
  const source = (state.stockEpiMovementItems || []).filter(stockEpiMatchesMovementSearch);
  if (!source.length && (refs.stockEpiMovementSearchName?.value || refs.stockEpiMovementSearchManufacturer?.value)) {
    list.innerHTML = `<div class="summary-item">${tr('stock.noEpiFound', 'Nenhum EPI encontrado com esse nome/fabricante na unidade selecionada.')}</div>`;
    return;
  }
  list.innerHTML = source.slice(0, 40).map((item) => {
    const summary = `${item.name || '-'} | ${tr('stock.fabShort', 'Fab')}: ${item.manufacturer || '-'} | ${tr('epi.caShort', 'CA')}: ${item.ca || '-'} | ${tr('stock.protectionShort', 'Proteção')}: ${epiProtectionLabel(item.sector || '-')} | ${tr('stock.sizeShort', 'Tam')}: ${item.size || item.glove_size || item.uniform_size || 'N/A'} | ${tr('stock.balanceShort', 'Saldo')}: ${item.stock || 0}`;
    return `<button type="button" class="ghost stock-epi-search-item" data-stock-epi-pick="${item.id}">${summary}</button>`;
  }).join('') || `<div class="summary-item">${tr('stock.typeNameManufacturer', 'Digite nome e/ou fabricante para buscar o EPI.')}</div>`;
}

function selectStockEpiFromSearch(epiId) {
  const epiField = document.getElementById('stock-epi');
  if (!epiField) return;
  epiField.value = String(epiId);
  epiField.dispatchEvent(new Event('change', { bubbles: true }));
  syncStockSizeDefaults();
  syncSelectedEpiMinimumStockField();
  const target = (state.stockEpiMovementItems || []).find((item) => String(item.id) === String(epiId))
    || (state.stockEpis || []).find((item) => String(item.id) === String(epiId));
  if (target) {
    if (refs.stockEpiMovementSearchName) refs.stockEpiMovementSearchName.value = String(target.name || '');
    if (refs.stockEpiMovementSearchManufacturer) refs.stockEpiMovementSearchManufacturer.value = String(target.manufacturer || '');
  }
  renderStockEpiSearchResults();
}

function syncEpiUnitOptions() {
  const companyField = document.getElementById('epi-company');
  const unitField = document.getElementById('epi-unit');
  if (!companyField || !unitField) return;
  const operationalProfile = isOperationalProfile();
  const operationalUnitId = String(state.user?.operational_unit_id || '').trim();
  if (operationalProfile && state.user?.company_id) {
    companyField.value = String(state.user.company_id);
    companyField.disabled = true;
  } else {
    companyField.disabled = false;
  }
  const companyId = companyField.value || state.user?.company_id || '';
  const units = filterByUserCompany(state.units).filter((item) => !companyId || String(item.company_id) === String(companyId));
  const previous = String(unitField.value || '');
  const unitOptions = units.map((item) => `<option value="${item.id}">${item.name} - ${unitTypeLabel(item.unit_type)}</option>`).join('');
  const allowAllUnitsScope = canUseEpiAllUnitsScope();
  if (operationalProfile) {
    const scopedUnits = units.filter((item) => String(item.id) === operationalUnitId);
    unitField.innerHTML = scopedUnits.map((item) => `<option value="${item.id}">${item.name} - ${unitTypeLabel(item.unit_type)}</option>`).join('') || '<option value="">Sem unidade operacional vinculada</option>';
    unitField.value = scopedUnits.length ? String(scopedUnits[0].id) : '';
    unitField.disabled = true;
  } else {
    const allUnitsOption = allowAllUnitsScope ? `<option value="${EPI_ALL_UNITS_VALUE}">${tr('epi.allUnits', 'Todas as Unidades')}</option>` : '';
    unitField.innerHTML = `${allUnitsOption}${unitOptions}`;
    if (allowAllUnitsScope && (!previous || previous === EPI_ALL_UNITS_VALUE)) {
      unitField.value = EPI_ALL_UNITS_VALUE;
    } else if (previous && units.some((item) => String(item.id) === previous)) {
      unitField.value = previous;
    } else if (units.length) {
      unitField.value = String(units[0].id);
    } else {
      unitField.value = '';
    }
    unitField.disabled = false;
  }
  applyEpiJoinventureRules();
}

function currentJoinventures() {
  const hidden = document.getElementById('epi-joinventures');
  const companyId = document.getElementById('epi-company')?.value || state.user?.company_id || '';
  if (!hidden) return [];
  try {
    const parsed = JSON.parse(hidden.value || '[]');
    if (!Array.isArray(parsed)) return [];
    const normalized = parsed.map((entry) => {
      if (typeof entry === 'string') {
        return { name: entry.trim(), unit_id: null };
      }
      if (!entry || typeof entry !== 'object') return null;
      const name = String(entry.name || '').trim();
      const unitId = entry.unit_id === null || entry.unit_id === undefined || entry.unit_id === '' ? null : String(entry.unit_id).trim();
      return name ? { name, unit_id: unitId || null } : null;
    }).filter(Boolean);
    return normalized.filter((entry) => {
      if (!entry.unit_id) return true;
      const unit = state.units.find((item) => String(item.id) === String(entry.unit_id));
      return unit && (!companyId || String(unit.company_id) === String(companyId));
    });
  } catch (error) {
    console.error('[stock-movement] Falha ao sincronizar estoque:', error);
    return [];
  }
}

function persistJoinventures(values) {
  const hidden = document.getElementById('epi-joinventures');
  if (!hidden) return;
  hidden.value = JSON.stringify(values.map((item) => ({ name: item.name, unit_id: item.unit_id || null })));
}

function activeJoinventureToken(entry) {
  if (!entry?.name) return '';
  return `${entry.name}@@${entry.unit_id || ''}`;
}

function parseActiveJoinventureToken(value) {
  const raw = String(value || '').trim();
  if (!raw) return { name: '', unit_id: null };
  if (!raw.includes('@@')) return { name: raw, unit_id: null };
  const [name, unitId] = raw.split('@@');
  return { name: String(name || '').trim(), unit_id: String(unitId || '').trim() || null };
}

function applyEpiJoinventureRules() {
  const unitField = document.getElementById('epi-unit');
  const activeSelect = document.getElementById('epi-joinventure-active');
  const hint = document.getElementById('epi-unit-rule-hint');
  if (!unitField || !activeSelect) return;
  const selected = parseActiveJoinventureToken(activeSelect.value);
  if (selected.name && selected.unit_id) {
    unitField.value = String(selected.unit_id);
    unitField.disabled = true;
    if (hint) hint.textContent = tr('epi.lockedByJoinventureHint', 'Unidade travada pela Joint Venture ativa: {name}.').replace('{name}', selected.name);
  } else {
    unitField.disabled = isOperationalProfile();
    if (!unitField.value && !isOperationalProfile() && canUseEpiAllUnitsScope()) unitField.value = EPI_ALL_UNITS_VALUE;
    if (hint) hint.textContent = tr('epi.noActiveJoinventureHint', 'Sem Joint Venture ou Unidade Única ativa: você pode usar "Todas as Unidades" para aprovar o EPI em nível de empresa.');
  }
}

function formatActiveJoinventureOption(entry) {
  const token = activeJoinventureToken(entry);
  const unitLabel = entry.unit_id
    ? state.units.find((item) => String(item.id) === String(entry.unit_id))?.name || `Unidade #${entry.unit_id}`
    : '';
  const label = unitLabel ? `${entry.name} - ${unitLabel}` : entry.name;
  return `<option value="${token}">${label}</option>`;
}

function renderJoinventureList() {
  const list = document.getElementById('epi-joinventure-list');
  const activeSelect = document.getElementById('epi-joinventure-active');
  const addButton = document.getElementById('epi-joinventure-add');
  const addInput = document.getElementById('epi-joinventure-name');
  if (!list || !activeSelect) return;
  const canManageJoinventure = ['master_admin', 'general_admin', 'registry_admin'].includes(state.user?.role);
  if (addButton) addButton.disabled = !canManageJoinventure;
  if (addInput) addInput.disabled = !canManageJoinventure;
  const values = currentJoinventures();
  persistJoinventures(values);
  list.innerHTML = values.map((entry) => {
    const unit = state.units.find((item) => String(item.id) === String(entry.unit_id || ''));
    const unitLabel = unit ? unit.name : tr('unit.undefined', 'Sem unidade definida');
    const token = activeJoinventureToken(entry);
    return `<button class="ghost" type="button" data-joinventure-remove="${token}">${entry.name} (${unitLabel}) - ${tr('delete', 'Apagar')}</button>`;
  }).join('') || `<span class="hint">${tr('epi.noJoinventure', 'Nenhuma JoinVenture cadastrada ou Unidade Única.')}</span>`;
  const previous = parseActiveJoinventureToken(activeSelect.value);
  activeSelect.innerHTML = `<option value="">${tr('epi.noActiveJoinventureOption', 'Sem Joint Venture ou Unidade Única ativa (EPI geral)')}</option>` + values.map(formatActiveJoinventureOption).join('');
  const previousToken = activeJoinventureToken(previous);
  const stillExists = values.some((entry) => activeJoinventureToken(entry) === previousToken);
  activeSelect.value = stillExists ? previousToken : '';
  applyEpiJoinventureRules();
}

function addJoinventure() {
  if (!['master_admin', 'general_admin', 'registry_admin'].includes(state.user?.role)) return;
  const input = document.getElementById('epi-joinventure-name');
  const unitField = document.getElementById('epi-unit');
  if (!input || !unitField) return;
  const name = String(input.value || '').trim();
  if (!name) return;
  if (String(unitField.value || '') === EPI_ALL_UNITS_VALUE) {
    alert('Selecione uma unidade especí­fica antes de cadastrar uma Joint Venture.');
    return;
  }
  const unitId = String(unitField.value || '').trim();
  const values = currentJoinventures();
  if (!values.some((item) => item.name.toLowerCase() === name.toLowerCase() && String(item.unit_id || '') === unitId)) {
    values.push({ name, unit_id: unitId });
  }
  persistJoinventures(values);
  input.value = '';
  renderJoinventureList();
}

function removeJoinventure(token) {
  const values = currentJoinventures().filter((item) => activeJoinventureToken(item) !== String(token));
  persistJoinventures(values);
  renderJoinventureList();
}

function setFormSubmitLabel(formId, text) {
  const button = document.querySelector(`#${formId} button[type="submit"]`);
  if (button) button.textContent = text;
}

// Leva o operador até o formulário que acabou de ser preenchido.
//
// `showView` troca a *view*, mas não a aba interna. Quando a lista e o
// cadastro são abas da mesma view, clicar "Editar" preenchia o formulário numa
// aba escondida: da perspectiva de quem clicou, nada acontecia — e ao abrir o
// cadastro depois, aparecia um formulário em modo de atualização sem
// explicação.
function focusRegistrationTab(group) {
  focusViewTab(group, 'cadastro');
}

// Mesma ideia de focusRegistrationTab, para qualquer aba interna: o
// assistente de migração precisa levar o operador do cartão até a aba do
// assistente, e do "Confirmar importação" até o histórico.
function focusViewTab(group, key) {
  const nav = document.querySelector(`[data-vtabs="${group}"]`);
  if (nav) activateViewTab(nav, key);
}

function startEditUnit(unitId) {
  const item = state.units.find((unit) => String(unit.id) === String(unitId));
  const form = document.getElementById('unit-form');
  if (!item || !form) return;
  form.elements.id.value = item.id;
  form.elements.company_id.value = item.company_id;
  form.elements.name.value = item.name || '';
  form.elements.unit_type.value = item.unit_type || 'base';
  form.elements.city.value = item.city || '';
  form.elements.notes.value = item.notes || '';
  // A lista de CNPJs depende da empresa, que acabou de ser preenchida.
  syncUnitLegalEntityOptions();
  if (form.elements.legal_entity_id) {
    form.elements.legal_entity_id.value = item.legal_entity_id ? String(item.legal_entity_id) : '';
  }
  setFormSubmitLabel('unit-form', 'Atualizar unidade');
  showView('unidades');
  focusRegistrationTab('unidades');
}

// Único ponto que decide a visibilidade de "Empresa de Origem": chamado no
// setup inicial, no 'change' do select, na edição e no reset do formulário —
// nunca `row.hidden = ...` duplicado nesses lugares, para não divergir.
function syncEmpresaOrigemVisibility() {
  const tv = document.getElementById('employee-tipo-vinculo')?.value || 'CLT';
  const row = document.getElementById('employee-empresa-origem-row');
  if (row) row.hidden = tv === 'CLT';
}

function startEditEmployee(employeeId) {
  const item = state.employees.find((employee) => String(employee.id) === String(employeeId));
  const form = document.getElementById('employee-form');
  if (!item || !form) return;
  form.elements.id.value = item.id;
  form.elements.company_id.value = item.company_id;
  syncEmployeeUnitOptions();
  form.elements.unit_id.value = item.unit_id || '';
  // CNPJ é o vínculo jurídico do contrato: imutável na edição comum. Mostramos
  // o valor atual, mas desabilitado — alterar exige o processo administrativo
  // auditado de transferência, e o backend ignora este campo no update.
  setEmployeeLegalEntityLock(item.legal_entity_id || '', true);
  form.elements.employee_id_code.value = item.employee_id_code || '';
  form.elements.cpf.value = item.cpf || '';
  form.elements.name.value = item.name || '';
  form.elements.email.value = item.email || '';
  form.elements.whatsapp.value = item.whatsapp || '';
  form.elements.preferred_contact_channel.value = item.preferred_contact_channel || 'whatsapp';
  form.elements.sector.value = item.sector || '';
  form.elements.role_name.value = item.role_name || '';
  form.elements.schedule_type.value = item.schedule_type || '14x14';
  form.elements.admission_date.value = item.admission_date || '';
  form.elements.tipo_vinculo.value = item.tipo_vinculo || 'CLT';
  form.elements.empresa_origem.value = item.empresa_origem || '';
  syncEmpresaOrigemVisibility();
  setFormSubmitLabel('employee-form', 'Atualizar colaborador');
  showView('colaboradores');
}

function startEditEpi(epiId) {
  const item = state.epis.find((epi) => String(epi.id) === String(epiId));
  const form = document.getElementById('epi-form');
  if (!item || !form) return;
  form.elements.id.value = item.id;
  form.elements.company_id.value = item.company_id;
  syncEpiUnitOptions();
  form.elements.unit_id.value = item.unit_id || '';
  form.elements.name.value = item.name || '';
  form.elements.purchase_code.value = item.purchase_code || '';
  form.elements.ca.value = item.ca || '';
  form.elements.sector.value = item.sector || '';
  form.elements.epi_section.value = item.epi_section || '';
  form.elements.model_reference.value = item.model_reference || '';
  if (!form.elements.sector.value) form.elements.sector.value = 'Proteção-Membros Superiores';
  form.elements.manufacturer.value = item.manufacturer || '';
  form.elements.supplier_company.value = item.supplier_company || '';
  form.elements.unit_measure.value = item.unit_measure || 'unidade';
  form.elements.ca_expiry.value = item.ca_expiry || '';
  form.elements.epi_validity_date.value = item.epi_validity_date || '';
  if (form.elements.glove_size) form.elements.glove_size.value = item.glove_size || 'N/A';
  if (form.elements.size) form.elements.size.value = item.size || 'N/A';
  if (form.elements.uniform_size) form.elements.uniform_size.value = item.uniform_size || 'N/A';
  form.elements.manufacturer_validity_months.value = String(item.manufacturer_validity_months ?? item.validity_months ?? 0);
  form.elements.manufacturer_recommendations.value = item.manufacturer_recommendations || '';
  form.elements.epi_photo_data.value = item.epi_photo_data || '';
  if (document.getElementById('epi-photo-file')) document.getElementById('epi-photo-file').value = '';
  renderEpiPhotoPreview(form.elements.epi_photo_data.value);
  document.getElementById('epi-joinventures').value = item.joinventures_json || '[]';
  renderJoinventureList();
  const existingEntry = currentJoinventures().find((entry) => entry.name === String(item.active_joinventure || '').trim());
  form.elements.active_joinventure.value = existingEntry ? activeJoinventureToken(existingEntry) : '';
  applyEpiJoinventureRules();
  setFormSubmitLabel('epi-form', 'Atualizar EPI');
  showView('epis');
}

// ── Arquivamento de Unidades (soft delete com retenção mínima de 5 anos) ─────

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

async function archiveUnit(unitId) {
  if (!requirePermission('units:delete')) return;
  const unit = state.units.find((item) => String(item.id) === String(unitId));
  const unitName = unit ? unit.name : `#${unitId}`;
  const message = `${tr('unit.title', 'Unidade')}: "${unitName}"\n\n${tr('unit.archiveConfirm',
    'Esta Unidade será arquivada e deixará de receber novas operações (colaboradores, EPIs, entregas, estoque e compras).\n\nTodo o histórico permanecerá preservado pelo período mínimo de retenção configurado (mínimo de 5 anos) para consultas, relatórios e auditorias.\n\nNenhum dado será excluído.')}`;
  if (!(await confirmDestructive({ title: tr('unit.archiveTitle', 'Arquivar Unidade'), message, confirmLabel: tr('unit.archive', 'Arquivar'), variant: 'danger' }))) return;
  const reason = globalThis.prompt(tr('unit.archiveReasonPrompt', 'Motivo do arquivamento (registrado na auditoria):'), '') ?? '';
  try {
    await api(`/api/units/${unitId}/archive`, {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user.id, reason }),
    });
    await loadBootstrap();
    await loadArchivedUnits();
  } catch (error) {
    alert(error.message);
  }
}

async function loadArchivedUnits() {
  if (!hasPermission('units:view')) return;
  try {
    const data = await api(`/api/units/archived?${actorQuery()}`);
    state.archivedUnits = data.units || [];
  } catch (error) {
    state.archivedUnits = [];
    reportNonCriticalError('[unidades] falha ao carregar unidades arquivadas', error);
  }
  renderArchivedUnits();
}

function applyArchivedUnitsFilters(items) {
  const filters = state.archivedUnitsFilters;
  return items.filter((item) => {
    if (filters.company_id && String(item.company_id) !== String(filters.company_id)) return false;
    if (filters.date && !String(item.archived_at || '').startsWith(filters.date)) return false;
    if (filters.reason && !String(item.archive_reason || '').toLowerCase().includes(filters.reason)) return false;
    if (filters.user && !String(item.archived_by_name || '').toLowerCase().includes(filters.user)) return false;
    return true;
  });
}

function formatArchivedUnitRow(item, canManage, canPurge) {
  const retentionOver = Number(item.retention_days_remaining || 0) <= 0;
  const retentionLabel = retentionOver
    ? tr('unit.retentionExpired', 'Retenção cumprida')
    : `${item.retention_days_remaining} ${tr('unit.retentionDays', 'dia(s)')}`;
  const statusBadge = item.status === 'pending_deletion' ? ` <span class="badge">${tr('unit.pendingDeletion', 'Em processo de exclusão')}</span>` : '';
  const holdBadge = Number(item.legal_hold || 0) ? ` <span class="badge">${tr('unit.legalHold', 'Bloqueio jurídico')}</span>` : '';
  const actions = [];
  if (canManage) actions.push(`<button class="ghost" data-unit-restore="${item.id}">${tr('unit.restore', 'Desarquivar')}</button>`);
  if (canPurge && retentionOver && !Number(item.legal_hold || 0)) {
    actions.push(`<button class="ghost" data-unit-purge="${item.id}">${tr('unit.purge', 'Excluir definitivamente')}</button>`);
  }
  return `<tr><td>${item.company_name}</td><td>${item.name}${statusBadge}${holdBadge}</td><td>${formatDate(item.archived_at)}</td><td>${item.archive_reason || '-'}</td><td>${item.archived_by_name || '-'}</td><td>${retentionLabel}</td><td>${actions.length ? `<div class="action-group">${actions.join('')}</div>` : '-'}</td></tr>`;
}

function renderArchivedUnits() {
  if (!refs.archivedUnitsTable) return;
  const canManage = ['general_admin', 'registry_admin'].includes(state.user?.role);
  const canPurge = ['master_admin', 'general_admin'].includes(state.user?.role);
  const items = applyArchivedUnitsFilters(filterByUserCompany(state.archivedUnits));
  refs.archivedUnitsTable.innerHTML = items.map((item) => formatArchivedUnitRow(item, canManage, canPurge)).join('')
    || globalThis.dsTableState({ colspan: 7, message: tr('unit.archivedEmpty', 'Nenhuma unidade arquivada.') });
}

function syncArchivedUnitsFilters() {
  state.archivedUnitsFilters.company_id = String(refs.archivedUnitsFilterCompany?.value || '').trim();
  state.archivedUnitsFilters.date = String(refs.archivedUnitsFilterDate?.value || '').trim();
  state.archivedUnitsFilters.reason = String(refs.archivedUnitsFilterReason?.value || '').trim().toLowerCase();
  state.archivedUnitsFilters.user = String(refs.archivedUnitsFilterUser?.value || '').trim().toLowerCase();
  renderArchivedUnits();
}

async function restoreArchivedUnit(unitId) {
  if (!requirePermission('units:update')) return;
  if (!(await confirmDestructive({ title: tr('unit.restoreTitle', 'Desarquivar Unidade'), message: tr('unit.restoreConfirm', 'A unidade será desarquivada e voltará a ficar ativa, podendo receber novas operações. Todo o histórico preservado permanece intacto. Continuar?'), confirmLabel: tr('unit.restore', 'Desarquivar'), variant: 'primary' }))) return;
  try {
    await api(`/api/units/${unitId}/restore`, { method: 'POST', body: JSON.stringify({ actor_user_id: state.user.id }) });
    await loadBootstrap();
    await loadArchivedUnits();
  } catch (error) {
    alert(error.message);
  }
}

// Exclusão definitiva em duas etapas: resumo do histórico + confirmação com
// justificativa obrigatória e digitação do nome exato da unidade.
async function purgeArchivedUnit(unitId) {
  if (!requirePermission('units:delete')) return;
  const unit = state.archivedUnits.find((item) => String(item.id) === String(unitId));
  if (!unit) return;
  try {
    const step1 = await api(`/api/units/${unitId}/purge-request`, {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user.id }),
    });
    const records = step1.records || {};
    const lines = Object.entries(UNIT_PURGE_RECORD_LABELS)
      .map(([key, label]) => `• ${label}: ${Number(records[key] || 0)}`)
      .join('\n');
    const message = `${tr('unit.purgeSummaryIntro', 'ATENÇÃO: exclusão definitiva e irreversível. Os seguintes registros históricos serão removidos:')}\n\n${lines}\n\n${tr('unit.purgeSummaryOutro', 'O registro de auditoria desta operação será preservado permanentemente.')}`;
    if (!(await confirmDestructive({ title: tr('unit.purgeTitle', 'Excluir definitivamente'), message, confirmLabel: tr('continue', 'Continuar'), variant: 'danger' }))) {
      await api(`/api/units/${unitId}/purge-cancel`, { method: 'POST', body: JSON.stringify({ actor_user_id: state.user.id }) });
      await loadArchivedUnits();
      return;
    }
    const justification = globalThis.prompt(tr('unit.purgeJustification', 'Justificativa obrigatória da exclusão definitiva (mínimo 10 caracteres):'), '') ?? '';
    const confirmName = globalThis.prompt(`${tr('unit.purgeConfirmName', 'Digite o nome exato da unidade para confirmar:')}\n"${unit.name}"`, '') ?? '';
    if (!justification.trim() || !confirmName.trim()) {
      await api(`/api/units/${unitId}/purge-cancel`, { method: 'POST', body: JSON.stringify({ actor_user_id: state.user.id }) });
      await loadArchivedUnits();
      return;
    }
    await api(`/api/units/${unitId}/purge-confirm`, {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user.id, justification, confirm_name: confirmName }),
    });
    alert(tr('unit.purgeDone', 'Unidade excluída definitivamente. O registro da operação foi gravado na auditoria.'));
    await loadBootstrap();
    await loadArchivedUnits();
  } catch (error) {
    alert(error.message);
    await loadArchivedUnits();
  }
}

// ── Arquivamento genérico (Colaboradores e EPIs) — mesma política das Unidades ─

const ARCHIVAL_ENTITIES = {
  employee: {
    path: '/api/employees',
    stateList: 'employees',
    archivedList: 'archivedEmployees',
    filters: 'archivedEmployeesFilters',
    tableRef: 'archivedEmployeesTable',
    i18nPrefix: 'employee',
    labelFallback: 'Colaborador',
    responseKey: 'employees',
    deletePermission: 'employees:delete',
    updatePermission: 'employees:update',
    purgeLabels: {
      deliveries: 'Entregas', devolutions: 'Devoluções', epi_requests: 'Requisições de EPI',
      feedbacks: 'Avaliações e feedbacks', ficha_periods: 'Fichas de EPI', ficha_items: 'Itens de ficha',
      unit_movements: 'Movimentações de unidade', portal_links: 'Links do portal',
      portal_audit_logs: 'Logs do portal',
    },
  },
  epi: {
    path: '/api/epis',
    stateList: 'epis',
    archivedList: 'archivedEpis',
    filters: 'archivedEpisFilters',
    tableRef: 'archivedEpisTable',
    i18nPrefix: 'epi',
    labelFallback: 'EPI',
    responseKey: 'epis',
    deletePermission: 'epis:delete',
    updatePermission: 'epis:update',
    purgeLabels: {
      deliveries: 'Entregas', devolutions: 'Devoluções', stock_items: 'Itens de estoque (QR Codes)',
      stock_movements: 'Movimentações de estoque', epi_requests: 'Requisições de EPI',
      feedbacks: 'Avaliações e feedbacks', ficha_items: 'Itens de ficha',
      purchase_request_items: 'Itens de requisição de compra', purchase_order_items: 'Itens de pedido de compra',
    },
  },
  // Empresa terceirizada/prestadora (ADR-0002 §10.4/§10.5) — mesma política
  // de arquivamento de Colaboradores/Unidades/EPIs, mas SEM purge: o
  // backend não oferece exclusão definitiva aqui de propósito (risco de
  // referência pendente em employees.outsourced_company_id/
  // service_contracts sem FK garantida). `identityKind` existe porque
  // `kind` aqui não é 'employee' nem 'epi' — reaproveita a mesma coluna de
  // identidade que o EPI usa (nome + segunda coluna), só trocando o texto
  // da segunda coluna. Segunda permissão (`employees:update_simplified`):
  // Administrador Local/Gestor de EPI, restrito à própria Unidade
  // operacional — o backend (ensure_actor_outsourced_company_scope +
  // ensure_module_enabled_for_unit, modules/outsourced_companies/routes.py)
  // valida de novo e é quem decide de fato.
  outsourcedCompany: {
    path: '/api/outsourced-companies',
    stateList: 'outsourcedCompanies',
    archivedList: 'archivedOutsourcedCompanies',
    filters: 'archivedOutsourcedCompaniesFilters',
    tableRef: 'archivedOutsourcedCompaniesTable',
    i18nPrefix: 'outsourcedCompany',
    labelFallback: 'Empresa terceirizada',
    responseKey: 'outsourced_companies',
    deletePermission: 'employees:update employees:update_simplified',
    updatePermission: 'employees:update employees:update_simplified',
    supportsPurge: false,
    identityKind: 'outsourcedCompanyLike',
  },
  // Colaborador terceirizado/prestador (ADR-0002 §10.4/§10.5) — MESMA
  // tabela/rota de arquivamento do colaborador CLT
  // (`/api/employees/<id>/archive` etc.), só a LISTAGEM de arquivados é
  // filtrada (?outsourced_only=1, via archivedQueryExtra) para não
  // misturar com "Colaboradores Arquivados" do cadastro completo.
  // `identityKind: 'employee'` reaproveita a mesma formatação de linha e os
  // mesmos textos i18n (`employee.*`) do colaborador CLT — é o mesmo tipo
  // de registro, só filtrado. Segunda permissão
  // (`employees:update_simplified`): Administrador Local/Gestor de EPI só
  // arquivam/desarquivam o PRÓPRIO Cadastro de Colaboradores (terceirizado/
  // prestador, nunca CLT) — o backend
  // (_load_employee_for_lifecycle/outsourced_alternative,
  // modules/employees/routes.py) recusa qualquer tentativa contra um
  // colaborador CLT ou de outra Unidade.
  outsourcedEmployee: {
    path: '/api/employees',
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
    purgeLabels: {
      deliveries: 'Entregas', devolutions: 'Devoluções', epi_requests: 'Requisições de EPI',
      feedbacks: 'Avaliações e feedbacks', ficha_periods: 'Fichas de EPI', ficha_items: 'Itens de ficha',
      unit_movements: 'Movimentações de unidade', portal_links: 'Links do portal',
      portal_audit_logs: 'Logs do portal',
    },
  },
};

// Item 1: EPI com saldo/vínculos vivos exige decisão autorizada. Consome
// EXCLUSIVAMENTE a regra do backend (#735): GET archival-state para decidir e
// POST /archive com block_and_archive. Nenhuma regra é duplicada no frontend.
async function _epiArchivalPreflight(recordId) {
  try {
    const resp = await api(`/api/epis/${recordId}/archival-state?${actorQuery()}`);
    return resp.archival_state || null;
  } catch (error) {
    reportNonCriticalError('[epi] falha ao consultar estado de arquivamento', error);
    return null;
  }
}

async function archiveEntityRecord(kind, recordId) {
  const cfg = ARCHIVAL_ENTITIES[kind];
  if (!cfg || !requirePermission(cfg.deletePermission)) return;
  const record = (state[cfg.stateList] || []).find((item) => String(item.id) === String(recordId));
  const recordName = record ? record.name : `#${recordId}`;

  let blockAndArchive = false;
  if (kind === 'epi') {
    const st = await _epiArchivalPreflight(recordId);
    if (st && st.has_open_links) {
      const linkMsg = `${cfg.labelFallback}: "${recordName}"\n\n`
        + `${tr('epi.archiveHasStock', 'Este EPI possui saldo ou vínculos vivos:')}\n`
        + `• ${tr('epi.stockAvailable', 'Disponível')}: ${st.available}\n`
        + `• ${tr('epi.stockInTransit', 'Reservado/em trânsito')}: ${st.in_transit}\n`
        + `• ${tr('epi.stockInPossession', 'Em posse (colaborador)')}: ${st.in_possession}\n`
        + `• ${tr('epi.stockBlocked', 'Bloqueado')}: ${st.blocked}\n`
        + `• ${tr('epi.pendingRequests', 'Solicitações abertas')}: ${st.pending_requests}\n`
        + `• ${tr('epi.pendingPurchase', 'Pedidos abertos')}: ${st.pending_purchase}\n\n`
        + (st.blockable > 0
          ? tr('epi.archiveBlockExplain', 'Ao continuar, o saldo disponível será BLOQUEADO (movido para Estoque Bloqueado — rastreável, nada some) e o EPI será arquivado.')
          : tr('epi.archiveNoBlockable', 'Não há saldo físico livre para bloquear; itens em posse/pedidos permanecem em seus fluxos. O EPI será arquivado.'));
      if (!(await confirmDestructive({
        title: tr('epi.blockAndArchive', 'Bloquear saldo e arquivar'),
        message: linkMsg,
        confirmLabel: tr('epi.blockAndArchive', 'Bloquear saldo e arquivar'),
        variant: 'danger',
      }))) return;
      blockAndArchive = true;
    }
  }

  if (!blockAndArchive) {
    const message = `${cfg.labelFallback}: "${recordName}"\n\n${tr(`${cfg.i18nPrefix}.archiveConfirm`, 'Este registro será arquivado e deixará de receber novas operações. Todo o histórico permanecerá preservado pelo período mínimo de retenção configurado (mínimo de 5 anos). Nenhum dado será excluído.')}`;
    if (!(await confirmDestructive({ title: tr(`${cfg.i18nPrefix}.archiveTitle`, `Arquivar ${cfg.labelFallback}`), message, confirmLabel: tr(`${cfg.i18nPrefix}.archive`, 'Arquivar'), variant: 'danger' }))) return;
  }

  const reason = globalThis.prompt(tr('unit.archiveReasonPrompt', 'Motivo do arquivamento (registrado na auditoria):'), '') ?? '';
  if (blockAndArchive && !String(reason).trim()) {
    showToast(tr('epi.archiveReasonRequired', 'Motivo é obrigatório para bloquear o saldo e arquivar.'), 'error');
    return;
  }
  try {
    const result = await api(`${cfg.path}/${recordId}/archive`, {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user.id, reason, block_and_archive: blockAndArchive }),
    });
    if (blockAndArchive && Number(result?.blocked_stock_items) > 0) {
      showToast(`${result.blocked_stock_items} ${tr('epi.itemsBlockedArchived', 'item(ns) de estoque bloqueado(s) e EPI arquivado.')}`, 'success');
    } else {
      showToast(tr('epi.archivedOk', 'Registro arquivado.'), 'success');
    }
    await loadBootstrap();
    await loadArchivedRecords(kind);
    // Atualiza imediatamente as telas de estoque (itens recém-bloqueados aparecem em Estoque Bloqueado)
    if (kind === 'epi') { globalThis.loadBlockedStock?.(); }
  } catch (error) {
    showToast(error.message || tr('epi.archiveFailed', 'Não foi possível arquivar.'), 'error');
  }
}

async function loadArchivedRecords(kind) {
  const cfg = ARCHIVAL_ENTITIES[kind];
  if (!cfg || !hasPermission(cfg.updatePermission.replace(':update', ':view'))) return;
  try {
    const data = await api(`${cfg.path}/archived?${actorQuery()}${cfg.archivedQueryExtra || ''}`);
    state[cfg.archivedList] = data[cfg.responseKey] || [];
  } catch (error) {
    state[cfg.archivedList] = [];
    reportNonCriticalError(`[${kind}] falha ao carregar arquivados`, error);
  }
  renderArchivedRecords(kind);
}

function formatArchivedRecordRow(kind, item, canManage, canPurge) {
  const cfg = ARCHIVAL_ENTITIES[kind];
  const retentionOver = Number(item.retention_days_remaining || 0) <= 0;
  const retentionLabel = retentionOver
    ? tr('unit.retentionExpired', 'Retenção cumprida')
    : `${item.retention_days_remaining} ${tr('unit.retentionDays', 'dia(s)')}`;
  const statusBadge = item.status === 'pending_deletion' ? ` <span class="badge">${tr('unit.pendingDeletion', 'Em processo de exclusão')}</span>` : '';
  const holdBadge = Number(item.legal_hold || 0) ? ` <span class="badge">${tr('unit.legalHold', 'Bloqueio jurídico')}</span>` : '';
  const actions = [];
  if (canManage) actions.push(`<button class="ghost" data-archived-restore="${kind}:${item.id}">${tr('unit.restore', 'Desarquivar')}</button>`);
  if (canPurge && cfg.supportsPurge !== false && retentionOver && !Number(item.legal_hold || 0)) {
    actions.push(`<button class="ghost" data-archived-purge="${kind}:${item.id}">${tr('unit.purge', 'Excluir definitivamente')}</button>`);
  }
  const actionsCell = actions.length ? `<div class="action-group">${actions.join('')}</div>` : '-';
  const identityKind = cfg.identityKind || kind;
  const identity = identityKind === 'employee'
    ? `<td>${item.employee_id_code || '-'} · ${item.name}${statusBadge}${holdBadge}</td><td>${item.unit_name || '-'}</td>`
    : identityKind === 'outsourcedCompanyLike'
      ? `<td>${item.legal_name || item.trade_name || ''}${statusBadge}${holdBadge}</td><td>${item.cnpj || '-'}</td>`
      : `<td>${item.name}${statusBadge}${holdBadge}</td><td>${item.ca || '-'}</td>`;
  return `<tr><td>${item.company_name || '-'}</td>${identity}<td>${formatDate(item.archived_at)}</td><td>${item.archive_reason || '-'}</td><td>${item.archived_by_name || '-'}</td><td>${retentionLabel}</td><td>${actionsCell}</td></tr>`;
}

function renderArchivedRecords(kind) {
  const cfg = ARCHIVAL_ENTITIES[kind];
  const table = refs[cfg.tableRef];
  if (!table) return;
  // Administrador Local/Gestor de EPI (ADR-0002 §10.5): só desarquivam
  // Empresas Terceirizadas/Colaboradores terceirizados/prestadores da
  // própria Unidade — nunca exclusão definitiva (purge continua exclusivo
  // de master_admin/general_admin, em qualquer kind). O backend
  // (ensure_actor_outsourced_company_scope / _load_employee_for_lifecycle)
  // é quem decide de fato; isto só evita mostrar um botão que o backend
  // vai recusar para os demais kinds (employee CLT / epi).
  const unitScopedManageKinds = ['outsourcedCompany', 'outsourcedEmployee'];
  const canManage = ['master_admin', 'general_admin', 'registry_admin'].includes(state.user?.role)
    || (unitScopedManageKinds.includes(kind) && ['admin', 'user'].includes(state.user?.role));
  const canPurge = ['master_admin', 'general_admin'].includes(state.user?.role);
  const filters = state[cfg.filters];
  const items = filterByUserCompany(state[cfg.archivedList] || []).filter((item) => {
    if (filters.company_id && String(item.company_id) !== String(filters.company_id)) return false;
    if (filters.date && !String(item.archived_at || '').startsWith(filters.date)) return false;
    if (filters.reason && !String(item.archive_reason || '').toLowerCase().includes(filters.reason)) return false;
    if (filters.user && !String(item.archived_by_name || '').toLowerCase().includes(filters.user)) return false;
    return true;
  });
  table.innerHTML = items.map((item) => formatArchivedRecordRow(kind, item, canManage, canPurge)).join('')
    || `<tr><td colspan="8">${tr(`${cfg.i18nPrefix}.archivedEmpty`, 'Nenhum registro arquivado.')}</td></tr>`;
}

function syncArchivedRecordsFilters(kind) {
  const cfg = ARCHIVAL_ENTITIES[kind];
  const prefix = cfg.tableRef.replace('Table', '');
  state[cfg.filters].company_id = String(refs[`${prefix}FilterCompany`]?.value || '').trim();
  state[cfg.filters].date = String(refs[`${prefix}FilterDate`]?.value || '').trim();
  state[cfg.filters].reason = String(refs[`${prefix}FilterReason`]?.value || '').trim().toLowerCase();
  state[cfg.filters].user = String(refs[`${prefix}FilterUser`]?.value || '').trim().toLowerCase();
  renderArchivedRecords(kind);
}

async function restoreArchivedRecord(kind, recordId) {
  const cfg = ARCHIVAL_ENTITIES[kind];
  if (!cfg || !requirePermission(cfg.updatePermission)) return;
  if (!(await confirmDestructive({ title: tr('unit.restoreTitle', 'Desarquivar'), message: tr(`${cfg.i18nPrefix}.restoreConfirm`, 'O registro será desarquivado e voltará a ficar ativo, podendo receber novas operações. Todo o histórico preservado permanece intacto. Continuar?'), confirmLabel: tr('unit.restore', 'Desarquivar'), variant: 'primary' }))) return;
  try {
    await api(`${cfg.path}/${recordId}/restore`, { method: 'POST', body: JSON.stringify({ actor_user_id: state.user.id }) });
    await loadBootstrap();
    await loadArchivedRecords(kind);
  } catch (error) {
    alert(error.message);
  }
}

// Exclusão definitiva em duas etapas (habilitada só após a retenção mínima).
async function purgeArchivedRecord(kind, recordId) {
  const cfg = ARCHIVAL_ENTITIES[kind];
  if (!cfg || cfg.supportsPurge === false || !requirePermission(cfg.deletePermission)) return;
  const record = (state[cfg.archivedList] || []).find((item) => String(item.id) === String(recordId));
  if (!record) return;
  try {
    const step1 = await api(`${cfg.path}/${recordId}/purge-request`, {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user.id }),
    });
    const records = step1.records || {};
    const lines = Object.entries(cfg.purgeLabels)
      .map(([key, label]) => `• ${label}: ${Number(records[key] || 0)}`)
      .join('\n');
    const message = `${tr('unit.purgeSummaryIntro', 'ATENÇÃO: exclusão definitiva e irreversível. Os seguintes registros históricos serão removidos:')}\n\n${lines}\n\n${tr('unit.purgeSummaryOutro', 'O registro de auditoria desta operação será preservado permanentemente.')}`;
    if (!(await confirmDestructive({ title: tr('unit.purgeTitle', 'Excluir definitivamente'), message, confirmLabel: tr('continue', 'Continuar'), variant: 'danger' }))) {
      await api(`${cfg.path}/${recordId}/purge-cancel`, { method: 'POST', body: JSON.stringify({ actor_user_id: state.user.id }) });
      await loadArchivedRecords(kind);
      return;
    }
    const justification = globalThis.prompt(tr('unit.purgeJustification', 'Justificativa obrigatória da exclusão definitiva (mínimo 10 caracteres):'), '') ?? '';
    const confirmName = globalThis.prompt(`${tr('unit.purgeConfirmName', 'Digite o nome exato para confirmar:')}\n"${record.name}"`, '') ?? '';
    if (!justification.trim() || !confirmName.trim()) {
      await api(`${cfg.path}/${recordId}/purge-cancel`, { method: 'POST', body: JSON.stringify({ actor_user_id: state.user.id }) });
      await loadArchivedRecords(kind);
      return;
    }
    await api(`${cfg.path}/${recordId}/purge-confirm`, {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user.id, justification, confirm_name: confirmName }),
    });
    alert(tr('unit.purgeDone', 'Registro excluído definitivamente. A operação foi gravada na auditoria.'));
    await loadBootstrap();
    await loadArchivedRecords(kind);
  } catch (error) {
    alert(error.message);
    await loadArchivedRecords(kind);
  }
}

async function deleteRegistryEntity(path, entityId, permission, message) {
  if (!requirePermission(permission)) return;
  if (!(await confirmDestructive({ title: 'Confirmar exclusão', message, confirmLabel: 'Excluir', variant: 'danger' }))) return;
  try {
    await api(`${path}/${entityId}?actor_user_id=${encodeURIComponent(state.user.id)}`, { method: 'DELETE' });
    await loadBootstrap();
  } catch (error) {
    alert(error.message);
  }
}

function formatUnitOption(item) {
  return `<option value="${item.id}">${item.name} - ${unitTypeLabel(item.unit_type)}</option>`;
}

function syncDeliveryOptions() {
  const companyField = document.getElementById('delivery-company');
  const unitFilterField = document.getElementById('delivery-unit-filter');
  const searchField = document.getElementById('delivery-employee-search');
  const employeeField = document.getElementById('delivery-employee');
  const epiField = document.getElementById('delivery-epi');
  const unitHint = document.getElementById('delivery-unit-hint');
  if (!companyField || !employeeField || !epiField) return;
  const operationalUnitId = state.user?.operational_unit_id;
  const lockByOperationalProfile = isOperationalProfile();
  if (lockByOperationalProfile && state.user?.company_id) {
    companyField.value = String(state.user.company_id);
  }
  const companyId = companyField.value || state.user?.company_id || '';
  const lockUnitByProfile = lockByOperationalProfile && operationalUnitId;
  const units = filterByUserCompany(state.units).filter((item) => !companyId || String(item.company_id) === String(companyId));
  let unitOptions;
  if (lockByOperationalProfile) {
    unitOptions = lockUnitByProfile ? units.filter((item) => String(item.id) === String(operationalUnitId)) : [];
  } else {
    unitOptions = units;
  }
  
  populateUnitFilterField(unitFilterField, lockByOperationalProfile, lockUnitByProfile, unitOptions);
  // Operational profiles (admin/user) with a locked unit auto-select it; general_admin/registry_admin
  // start with "Todas" so they can see employees from all units without being forced into one.
  if (lockByOperationalProfile && lockUnitByProfile && unitFilterField && unitOptions.length) {
    unitFilterField.value = String(unitOptions[0].id);
  }

  // master_admin can always freely change company even if some other path sets lockByOperationalProfile
  companyField.disabled = lockByOperationalProfile && state.user?.role !== 'master_admin';
  if (unitHint) unitHint.style.display = lockByOperationalProfile ? 'block' : 'none';
  
  const unitFilter = lockByOperationalProfile
    ? String(operationalUnitId || '__NO_UNIT__')
    : String(unitFilterField?.value || '');
  
  const search = String(searchField?.value || '').trim().toLowerCase();
  
  const employees = getFilteredDeliveryEmployees(companyId, unitFilter, search);
  populateDeliveryEmployeeField(employeeField, employees, search);
  populateDeliveryEpiField(epiField, getFilteredDeliveryEpis(companyId, unitFilter));
  syncDeliveryQrSessionOwner({ warn: false });
  clearDeliveryStockItemSelection();
  void loadDeliveryUnitEpis(companyId, unitFilter);
  void loadAvailableQrsForSelectedEpi();
}

function clearDeliveryStockItemSelection() {
  const stockItemIdField = document.getElementById('delivery-stock-item-id');
  const stockCodeField = document.getElementById('delivery-stock-item-code');
  const stockQrHiddenField = document.getElementById('delivery-stock-qr-code');
  if (stockItemIdField) stockItemIdField.value = '';
  if (stockCodeField) stockCodeField.value = '';
  if (stockQrHiddenField) stockQrHiddenField.value = '';
  deliveryCodeValidationState.code = '';
  deliveryCodeValidationState.source = '';
  deliveryCodeValidationState.autoValidated = false;
}

function markDeliveryCodeValidation(stockItem, source = '') {
  const code = String(stockItem?.qr_code_value || '').trim();
  deliveryCodeValidationState.code = code;
  deliveryCodeValidationState.source = String(source || '').trim();
  deliveryCodeValidationState.autoValidated = Boolean(code && source === 'stock_selection');
}

function isCodeAutoValidatedBySelection(currentCode) {
  const normalizedCurrentCode = String(currentCode || '').trim().toLowerCase();
  const normalizedStoredCode = String(deliveryCodeValidationState.code || '').trim().toLowerCase();
  return Boolean(
    deliveryCodeValidationState.autoValidated
    && normalizedCurrentCode
    && normalizedStoredCode
    && normalizedCurrentCode === normalizedStoredCode
    && deliveryCodeValidationState.source === 'stock_selection'
  );
}

async function loadAvailableQrsForSelectedEpi() {
  const target = refs.deliveryAvailableQr;
  if (!target) return;
  const hint = refs.deliveryAvailableQrHint;
  const companyId = String(document.getElementById('delivery-company')?.value || state.user?.company_id || '').trim();
  const unitId = String(document.getElementById('delivery-unit-filter')?.value || state.user?.operational_unit_id || '').trim();
  const epiId = String(document.getElementById('delivery-epi')?.value || '').trim();
  if (!companyId || !unitId || !epiId) {
    target.innerHTML = `<option value="">${tr('delivery.availableQrLoadPrompt', 'Selecione empresa/unidade/EPI para carregar os QRs')}</option>`;
    if (hint) hint.textContent = tr('delivery.availableQrSelectHint', 'Selecione empresa, unidade e EPI para listar os QRs disponíveis.');
    return;
  }
  target.innerHTML = `<option value="">${tr('delivery.loadingAvailableQrs', 'Carregando QRs disponíveis...')}</option>`;
  try {
    const params = new URLSearchParams({
      actor_user_id: String(state.user?.id || ''),
      company_id: companyId,
      unit_id: unitId,
      epi_id: epiId
    });
    const payload = await apiWithBootstrapRetry(`/api/stock/available-items?${params.toString()}`);
    const items = Array.isArray(payload?.items) ? payload.items : [];
    if (!items.length) {
      target.innerHTML = `<option value="">${tr('delivery.noQrAvailable', 'Nenhum QR disponível para este EPI na unidade')}</option>`;
      if (hint) hint.textContent = tr('delivery.noQrAvailableHint', 'Nenhum QR disponível para este EPI na unidade selecionada.');
      return;
    }
    // FEFO: os itens já chegam ordenados por validade mais próxima. O primeiro
    // com data de fabricação é o recomendado (vence primeiro) e recebe destaque.
    const fefoIndex = items.findIndex((item) => String(item.manufacture_date || '').trim());
    target.innerHTML = `<option value="">${tr('delivery.selectPhysicalQr', 'Selecione o QR físico correto')}</option>` + items.map((item, index) => {
      const mfg = String(item.manufacture_date || '').trim();
      const fefoTag = index === fefoIndex ? `★ ${tr('delivery.fefoFirst', 'vence primeiro')} — ` : '';
      const mfgLabel = mfg ? ` — ${tr('delivery.manufactureShort', 'Fab.')}: ${escapeHtml(mfg)}` : '';
      return `<option value="${item.id}" data-qr-code="${escapeHtml(String(item.qr_code_value || ''))}">${fefoTag}${escapeHtml(String(item.qr_code_value || ''))} — ${escapeHtml(String(item.epi_name || 'EPI'))} — ${tr('delivery.sizeShort', 'Tam.')}: ${escapeHtml(formatItemSizeDisplay(item))}${mfgLabel}</option>`;
    }).join('');
    if (hint) hint.textContent = tr('delivery.qrCountAvailableFefo', '{count} QR(s) disponível(is), ordenados por validade (FEFO — o que vence primeiro no topo).').replace('{count}', String(items.length));
  } catch (error) {
    target.innerHTML = `<option value="">${tr('delivery.qrLoadFailure', 'Falha ao carregar QR disponíveis')}</option>`;
    if (hint) hint.textContent = tr('delivery.qrLoadFailureHint', 'Falha ao carregar QRs disponíveis: {error}').replace('{error}', String(error?.message || 'erro desconhecido'));
  }
}
  

function populateUnitFilterField(unitFilterField, lockByOperationalProfile, lockUnitByProfile, unitOptions) {
  if (!unitFilterField) return;
  const previous = String(unitFilterField.value || '');
  unitFilterField.innerHTML = `${lockByOperationalProfile ? '' : `<option value="">${tr('epi.allUnits', 'Todas as Unidades')}</option>`}${unitOptions.map(formatUnitOption).join('')}`;
  if (lockUnitByProfile && unitOptions.length) {
    unitFilterField.value = String(unitOptions[0].id);
  } else if (lockByOperationalProfile && !unitOptions.length) {
    unitFilterField.innerHTML = `<option value="">${tr('employee.noActiveOperationalUnit', 'Sem unidade operacional ativa')}</option>`;
  } else if (previous && unitOptions.some((item) => String(item.id) === previous)) {
    unitFilterField.value = previous;
  }
  unitFilterField.disabled = lockByOperationalProfile;
}

function getFilteredDeliveryEmployees(companyId, unitFilter, search) {
  return filterByUserCompany(state.employees).filter((item) => {
    if (unitFilter === '__NO_UNIT__') return false;
    if (companyId && String(item.company_id) !== String(companyId)) return false;
    const currentUnitId = item.current_unit_id || item.unit_id;
    if (unitFilter && String(currentUnitId) !== String(unitFilter)) return false;
    return matchesEmployeeSearchText(item, search);
  });
}

function getFilteredDeliveryEpis(companyId, unitFilter) {
  const source = state.deliveryEpis || [];
  return source.filter((item) => {
    if (unitFilter === '__NO_UNIT__') return false;
    if (companyId && String(item.company_id) !== String(companyId)) return false;
    return true;
  });
}

async function loadDeliveryUnitEpis(companyId, unitFilter) {
  if (!hasPermission('deliveries:view')) return;
  if (unitFilter === '__NO_UNIT__') {
    state.deliveryEpis = [];
    state.deliveryEpisScopeKey = `${companyId || ''}|${unitFilter || ''}`;
    const epiField = document.getElementById('delivery-epi');
    if (epiField) populateDeliveryEpiField(epiField, []);
    return;
  }
  const unitId = String(unitFilter || '').trim();
  if (!companyId || !unitId) {
    state.deliveryEpis = [];
    state.deliveryEpisScopeKey = `${companyId || ''}|${unitId || ''}`;
    const epiField = document.getElementById('delivery-epi');
    if (epiField) populateDeliveryEpiField(epiField, []);
    return;
  }
  const scopeKey = `${companyId}|${unitId}`;
  if (state.deliveryEpisScopeKey === scopeKey && state.deliveryEpis.length) return;
  const params = new URLSearchParams({ actor_user_id: String(state.user.id), company_id: String(companyId), unit_id: unitId });
  try {
    const payload = await apiWithBootstrapRetry(`/api/stock/epis?${params.toString()}`);
    state.deliveryEpis = payload.items || [];
    state.deliveryEpisScopeKey = scopeKey;
    const epiField = document.getElementById('delivery-epi');
    if (!epiField) return;
    populateDeliveryEpiField(epiField, getFilteredDeliveryEpis(companyId, unitFilter));
    refreshDeliveryContext();
  } catch (error) {
    console.error('[delivery-epis] Falha ao carregar EPI por unidade:', error);
    state.deliveryEpis = [];
    state.deliveryEpisScopeKey = scopeKey;
    const epiField = document.getElementById('delivery-epi');
    if (epiField) epiField.innerHTML = '';
  }
}

function populateDeliveryEmployeeField(employeeField, employees, search) {
  const previousValue = String(employeeField.value || '').trim();
  const hasSearch = Boolean(String(search || '').trim());
  const baseOptions = employees.map((item) => `<option value="${item.id}">${item.employee_id_code} - ${item.name}</option>`);
  if (!hasSearch) {
    const hasPreviousInList = previousValue && employees.some((item) => String(item.id) === previousValue);
    if (previousValue && !hasPreviousInList) {
      const selectedEmployee = state.employees.find((item) => String(item.id) === previousValue);
      if (selectedEmployee) {
        baseOptions.unshift(`<option value="${selectedEmployee.id}">${selectedEmployee.employee_id_code} - ${selectedEmployee.name}</option>`);
      }
    }
  }
  employeeField.innerHTML = baseOptions.join('');
  if (!hasSearch && previousValue && Array.from(employeeField.options || []).some((option) => String(option.value) === previousValue)) {
    employeeField.value = previousValue;
    return;
  }
  if (employees.length) employeeField.value = String(employees[0].id);
}

function populateDeliveryEpiField(epiField, epis) {
  epiField.innerHTML = epis.map((item) => {
    const stock = Number(item.stock || 0);
    const stockLabel = stock > 0 ? `${stock} ${tr('delivery.inStock', 'em estoque')}` : tr('delivery.noStock', 'Sem saldo');
    const sizeLabel = formatSizeBalancesDisplay(item.size_balances).replace(/<br>/g, ' | ');
    return `<option value="${item.id}">${item.name} - ${item.unit_measure} (${stockLabel}) - ${tr('delivery.sizeShort', 'Tam.')}: ${escapeHtml(sizeLabel)}</option>`;
  }).join('') || `<option value="">${tr('delivery.noEpiForUnit', 'Nenhum EPI disponível para a unidade')}</option>`;
  if (epis.length && !epis.some((item) => String(item.id) === String(epiField.value))) {
    epiField.value = String(epis[0].id);
    epiField.dispatchEvent(new Event('change', { bubbles: true }));
  }
  renderDeliveryEpiSearchResults();
}

function deliveryEpiMatchesSearch(item) {
  const tokens = `${String(refs.deliveryEpiSearch?.value || '').trim()} ${String(refs.deliveryEpiSearchManufacturer?.value || '').trim()}`
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean);
  if (!tokens.length) return true;
  const haystack = [
    item.name,
    item.manufacturer,
    item.ca,
    item.sector,
    item.epi_section,
    item.glove_size,
    item.size,
    item.uniform_size,
    ...(Array.isArray(item.size_balances) ? item.size_balances.map(formatItemSizeDisplay) : []),
    item.model_reference
  ].map((value) => String(value || '').toLowerCase()).join(' ');
  return tokens.every((token) => haystack.includes(token));
}

function renderDeliveryEpiSearchResults() {
  const list = refs.deliveryEpiSearchResults;
  if (!list) return;
  const companyId = document.getElementById('delivery-company')?.value || state.user?.company_id || '';
  const unitFilter = document.getElementById('delivery-unit-filter')?.value || state.user?.operational_unit_id || '';
  const source = getFilteredDeliveryEpis(companyId, unitFilter).filter(deliveryEpiMatchesSearch);
  if (!source.length) {
    list.innerHTML = `<div class="summary-item">${tr('delivery.noEpiSearch', 'Nenhum EPI encontrado para esta busca/unidade.')}</div>`;
    return;
  }
  list.innerHTML = source.slice(0, 30).map((item) => {
    const sizeSummary = formatSizeBalancesDisplay(item.size_balances).replace(/<br>/g, ' | ');
    const summary = `${item.name || '-'} | ${tr('epi.manufacturer', 'Fabricante')}: ${item.manufacturer || '-'} | ${tr('epi.caShort', 'CA')}: ${item.ca || '-'} | ${tr('delivery.protectionLabel', 'Proteção')}: ${item.sector || '-'} | ${tr('delivery.sizeShort', 'Tam.')}: ${sizeSummary} | ${tr('delivery.balanceLabel', 'Saldo')}: ${item.stock || 0}`;
    return `<button type="button" class="ghost stock-epi-search-item" data-delivery-epi-pick="${item.id}">${summary}</button>`;
  }).join('');
}

function selectDeliveryEpiFromSearch(epiId) {
  const epiField = document.getElementById('delivery-epi');
  if (!epiField) return;
  epiField.value = String(epiId);
  epiField.dispatchEvent(new Event('change', { bubbles: true }));
  const target = (state.deliveryEpis || []).find((item) => String(item.id) === String(epiId));
  if (target) {
    if (refs.deliveryEpiSearch) refs.deliveryEpiSearch.value = String(target.name || '');
    if (refs.deliveryEpiSearchManufacturer) refs.deliveryEpiSearchManufacturer.value = String(target.manufacturer || '');
  }
  refreshDeliveryContext();
  renderDeliveryEpiSearchResults();
}

function syncEmployeeUnitOptions() {
  const companyField = document.getElementById('employee-company');
  const unitField = document.getElementById('employee-unit');
  if (!companyField || !unitField) return;
  const companyId = companyField.value || state.user?.company_id || '';
  const units = filterByUserCompany(state.units).filter((item) => !companyId || String(item.company_id) === String(companyId));
  unitField.innerHTML = units.map((item) => `<option value="${item.id}">${item.name} - ${unitTypeLabel(item.unit_type)}</option>`).join('');
  if (units.length && !units.some((item) => String(item.id) === String(unitField.value))) {
    unitField.value = String(units[0].id);
  }
  // O CNPJ acompanha a empresa selecionada, então é resincronizado junto.
  syncEmployeeLegalEntityOptions();
}

// ── Multi-CNPJ: seletores de vínculo jurídico ────────────────────────────────

// Regras puras vivem em js/views/legal-entity-fields.js (testadas no harness);
// aqui ficam apenas os wrappers que leem o estado e mexem no DOM.
function legalEntityHelpers() {
  return globalThis.__EPI_LEGAL_ENTITY_FIELDS__ || {};
}

function legalEntitiesForCompany(companyId, options) {
  const helper = legalEntityHelpers().legalEntitiesForCompany;
  return helper ? helper(state.legalEntities, companyId, options) : [];
}

function unitLegalEntityLabel(unit) {
  const helper = legalEntityHelpers().unitLegalEntityLabel;
  return helper ? helper(unit) : String(unit?.legal_entity_cnpj || '');
}

function legalEntityOptionsHtml(entities) {
  const label = legalEntityHelpers().legalEntityLabel || ((item) => String(item?.cnpj || ''));
  return entities
    .map((item) => `<option value="${item.id}">${escapeHtml(label(item))}</option>`)
    .join('');
}

// Vínculo jurídico do colaborador.
//
// O campo só aparece quando a empresa tem CNPJs cadastrados, e só é obrigatório
// quando há mais de um ativo: com CNPJ único o backend resolve sozinho, e
// exigir escolha seria ruído. Com mais de um, o backend recusa o cadastro sem
// o campo — por isso a obrigatoriedade aqui espelha a regra do servidor em vez
// de inventar uma própria.
function syncEmployeeLegalEntityOptions() {
  const field = document.getElementById('employee-legal-entity');
  const wrapper = document.getElementById('employee-legal-entity-field');
  if (!field || !wrapper) return;
  const companyId = document.getElementById('employee-company')?.value || state.user?.company_id || '';
  const entities = legalEntitiesForCompany(companyId);
  const previous = field.value;
  const required = legalEntityHelpers().employeeLegalEntityRequired;
  const mandatory = required ? required(entities) : entities.length > 1;
  wrapper.hidden = entities.length === 0;
  field.required = mandatory;
  const placeholder = mandatory
    ? `<option value="">${tr('legalEntity.select', 'Selecione o CNPJ')}</option>`
    : `<option value="">${tr('legalEntity.auto', 'Automático (CNPJ único)')}</option>`;
  field.innerHTML = placeholder + legalEntityOptionsHtml(entities);
  if (previous && entities.some((item) => String(item.id) === String(previous))) {
    field.value = previous;
  }
}

// Trava (ou destrava) o seletor de CNPJ do colaborador.
//
// Na edição o campo fica visível e desabilitado: o operador precisa VER a qual
// CNPJ o colaborador pertence, mas não pode trocar por aqui. Campo desabilitado
// não é serializado no submit, o que também impede o envio acidental do valor.
function setEmployeeLegalEntityLock(legalEntityId, locked) {
  const field = document.getElementById('employee-legal-entity');
  if (!field) return;
  syncEmployeeLegalEntityOptions();
  if (legalEntityId) field.value = String(legalEntityId);
  field.disabled = Boolean(locked);
  if (locked) field.required = false;
}

// ── Tela de CNPJs (web legado) ───────────────────────────────────────────────

// Regras puras vivem em js/views/legal-entities-view.js (testadas no harness);
// aqui ficam a leitura do estado, o DOM e as chamadas de API.
function legalEntitiesViewHelpers() {
  return globalThis.__EPI_LEGAL_ENTITIES_VIEW__ || {};
}

function renderLegalEntities() {
  if (!refs.legalEntitiesTable) return;
  const helpers = legalEntitiesViewHelpers();
  const visible = helpers.visibleLegalEntities
    ? helpers.visibleLegalEntities(state.legalEntities, state.legalEntitiesFilters)
    : (state.legalEntities || []);
  const canUpdate = hasPermission('legal_entities:update');
  const canDelete = hasPermission('legal_entities:delete');
  refs.legalEntitiesTable.innerHTML = visible
    .map((item) => formatLegalEntityRow(item, { canUpdate, canDelete }))
    .join('') || globalThis.dsTableState({
      colspan: 6,
      message: tr('legalEntity.empty', 'Sem CNPJs cadastrados.'),
    });
}

function formatLegalEntityRow(item, permissions) {
  const helpers = legalEntitiesViewHelpers();
  const typeLabel = helpers.entityTypeLabel ? helpers.entityTypeLabel(item.entity_type) : '';
  const active = helpers.isActive ? helpers.isActive(item) : Boolean(item.active);
  const status = active
    ? tr('legalEntity.statusActive', 'Ativo')
    : tr('legalEntity.statusInactive', 'Inativo');
  // O botão de inativar só aparece quando a ação é possível: o backend recusa
  // o último CNPJ ativo, e oferecer o botão só geraria mensagem de erro.
  const showDeactivate = permissions.canDelete
    && (helpers.canDeactivate ? helpers.canDeactivate(item, state.legalEntities) : active);
  // O id vira atributo HTML: escapado como qualquer outro dado vindo do
  // servidor, mesmo sendo numérico na prática.
  const entityId = escapeHtml(String(item.id ?? ''));
  const buttons = [];
  if (permissions.canUpdate) {
    buttons.push(`<button class="ghost" data-legal-entity-edit="${entityId}">${escapeHtml(tr('edit', 'Editar'))}</button>`);
  }
  if (showDeactivate) {
    buttons.push(`<button class="ghost" data-legal-entity-deactivate="${entityId}">${escapeHtml(tr('legalEntity.deactivate', 'Inativar'))}</button>`);
  }
  const actions = buttons.length ? `<div class="action-group">${buttons.join('')}</div>` : '-';
  return `<tr><td>${escapeHtml(item.cnpj || '')}</td><td>${escapeHtml(item.legal_name || '')}</td>`
    + `<td>${escapeHtml(item.trade_name || '') || '-'}</td><td>${escapeHtml(typeLabel)}</td>`
    + `<td>${escapeHtml(status)}</td><td>${actions}</td></tr>`;
}

function syncLegalEntitiesFilters() {
  state.legalEntitiesFilters.search = String(refs.legalEntitiesFilterSearch?.value || '').trim();
  state.legalEntitiesFilters.type = String(refs.legalEntitiesFilterType?.value || '').trim();
  state.legalEntitiesFilters.showInactive = Boolean(refs.legalEntitiesShowInactive?.checked);
  renderLegalEntities();
}

// Empresa só é escolhida pelo Administrador Master, que atende vários clientes.
// Para os demais o campo some: a empresa é a do próprio usuário, e mostrar um
// seletor de uma opção só induz a erro.
function syncLegalEntityCompanyField() {
  const field = document.getElementById('legal-entity-company');
  const wrapper = document.getElementById('legal-entity-company-field');
  const hint = document.getElementById('legal-entity-company-hint');
  if (!field || !wrapper) return;
  const isMaster = state.user?.role === 'master_admin';

  if (isMaster) {
    // Só o Master escolhe: ele atende vários clientes e não tem empresa
    // própria de onde deduzir. O placeholder faz uma seleção vazia ler como
    // "escolha uma", e não como campo quebrado.
    const previous = field.value;
    wrapper.hidden = false;
    field.disabled = false;
    field.required = true;
    populateSelect('legal-entity-company', state.companies, (item) => `${item.name} - ${item.cnpj}`);
    field.insertBefore(
      new Option(tr('company.select', 'Selecione a empresa'), ''),
      field.firstChild,
    );
    field.value = previous || '';
    if (hint) hint.hidden = true;
    return;
  }

  // Demais perfis: a empresa é a da conta e não se escolhe. Mostrar o nome —
  // desabilitado, como o CNPJ do colaborador na edição — informa em qual
  // empresa o CNPJ vai nascer sem oferecer uma decisão que não existe.
  //
  // Esconder o campo também evitaria o erro, mas tiraria essa confirmação
  // justamente na tela onde ela importa: a de cadastrar pessoa jurídica.
  const companyName = String(state.user?.company_name || '').trim();
  // Sem nome não há o que afirmar; nesse caso o campo some, e o aviso geral de
  // dados indisponíveis explica a tela.
  wrapper.hidden = companyName === '';
  field.required = false;
  // Desabilitado não é serializado no submit — de propósito: o backend resolve
  // a empresa pela sessão, e enviar um palpite daqui seria uma forma de gravar
  // na empresa errada.
  field.disabled = true;
  field.replaceChildren(new Option(companyName, String(state.user?.company_id || '')));
  if (hint) hint.hidden = wrapper.hidden;
}

// Alterna o formulário entre cadastrar e atualizar.
//
// O estado precisa ser visível: o rótulo do botão muda e a saída ("Novo CNPJ")
// só aparece quando há de onde sair. Um formulário preso em "Atualizar" sem
// nenhuma indicação de por quê foi exatamente o que se viu em produção.
function setLegalEntityFormMode(mode) {
  const cancel = document.getElementById('legal-entity-cancel-edit');
  if (cancel) cancel.hidden = mode !== 'edit';
}

function resetLegalEntityForm() {
  const form = document.getElementById('legal-entity-form');
  if (!form) return;
  form.reset();
  form.elements.id.value = '';
  // `reset()` devolve o valor do atributo `value` do HTML, que é '1'; sendo
  // explícito aqui para não depender do markup na hora de voltar a cadastrar.
  if (form.elements.active) form.elements.active.value = '1';
  setFormSubmitLabel('legal-entity-form', tr('legalEntity.save', 'Salvar CNPJ'));
  setLegalEntityFormMode('create');
  syncLegalEntityCompanyField();
}

function startEditLegalEntity(entityId) {
  const item = (state.legalEntities || []).find((entity) => String(entity.id) === String(entityId));
  const form = document.getElementById('legal-entity-form');
  if (!item || !form) return;
  form.elements.id.value = item.id;
  syncLegalEntityCompanyField();
  if (form.elements.company_id) form.elements.company_id.value = item.company_id || '';
  form.elements.cnpj.value = item.cnpj || '';
  form.elements.legal_name.value = item.legal_name || '';
  form.elements.trade_name.value = item.trade_name || '';
  form.elements.entity_type.value = item.entity_type || 'matriz';
  form.elements.state_registration.value = item.state_registration || '';
  form.elements.municipal_registration.value = item.municipal_registration || '';
  form.elements.cnae.value = item.cnae || '';
  form.elements.opening_date.value = item.opening_date || '';
  form.elements.address.value = item.address || '';
  form.elements.municipality.value = item.municipality || '';
  form.elements.uf.value = item.uf || '';
  form.elements.cep.value = item.cep || '';
  form.elements.notes.value = item.notes || '';
  // Preserva a situação atual: sem isso o backend assumiria `active = 1` e a
  // simples edição de um CNPJ inativo o reativaria.
  const helpers = legalEntitiesViewHelpers();
  const active = helpers.isActive ? helpers.isActive(item) : Boolean(item.active);
  form.elements.active.value = active ? '1' : '0';
  setFormSubmitLabel('legal-entity-form', tr('legalEntity.update', 'Atualizar CNPJ'));
  setLegalEntityFormMode('edit');
  showView('cnpjs');
  focusRegistrationTab('cnpjs');
}

async function deactivateLegalEntity(entityId) {
  if (!requirePermission('legal_entities:delete')) return;
  const item = (state.legalEntities || []).find((entity) => String(entity.id) === String(entityId));
  if (!item) return;
  const confirmed = confirm(tr(
    'legalEntity.deactivateConfirm',
    'Inativar este CNPJ? O histórico jurídico e fiscal é preservado; ele apenas deixa de ser usado em novas operações.',
  ) + `\n\n${item.cnpj} — ${item.legal_name}`);
  if (!confirmed) return;
  try {
    await api(`/api/legal-entities/${entityId}?${actorQuery()}`, { method: 'DELETE' });
    await loadBootstrap();
  } catch (error) {
    alert(error.message);
  }
}

// ── Tela de Terceirizados e Prestadores (web legado, ADR-0002) ──────────────

// Regras puras vivem em js/views/outsourced-companies-view.js (testadas no
// harness); aqui ficam a leitura do estado, o DOM e as chamadas de API.
function outsourcedCompaniesViewHelpers() {
  return globalThis.__EPI_OUTSOURCED_COMPANIES_VIEW__ || {};
}

// Diferente de `state.legalEntities`, esta lista não chega no bootstrap — o
// módulo nasce oculto por padrão, então só busca quando a tela é aberta
// (chamado a partir de showView).
async function loadOutsourcedCompanies() {
  // Gate alinhado ao backend (handle_get_outsourced_companies exige só
  // PERM_EMPLOYEES_VIEW, igual a loadOutsourcedEmployeesSummary logo abaixo)
  // — 'employees:create' era restritivo demais e nunca é concedido a
  // Administrador Local/Gestor de EPI (só têm employees:create_simplified),
  // então a lista nunca carregava para esses perfis: nem a aba "Lista" nem o
  // seletor de empresa do Cadastro de Colaboradores (syncOutsourcedEmployeeCompanySelect,
  // chamado por renderOutsourcedCompanies logo abaixo) recebiam dados.
  if (!hasPermission('employees:view')) return;
  try {
    const data = await api(`/api/outsourced-companies?${actorQuery()}`);
    state.outsourcedCompanies = data.outsourced_companies || data.items || [];
    // Empresas do tenant ainda não vinculadas à própria Unidade (ADR-0002
    // §12 — compartilhamento por tenant): campos públicos só, mascarados no
    // backend (fetch_outsourced_companies/annotate_outsourced_company_visibility) —
    // nunca contrato/nota/colaborador de outra Unidade. Vazio para quem não
    // é escopado por Unidade (já vê tudo em outsourcedCompanies).
    state.outsourcedCompaniesAvailable = data.available_outsourced_companies || [];
  } catch (error) {
    state.outsourcedCompanies = [];
    state.outsourcedCompaniesAvailable = [];
    reportNonCriticalError('[terceirizados] falha ao carregar empresas terceirizadas', error);
  }
  renderOutsourcedCompanies();
}

function renderOutsourcedCompanies() {
  if (!refs.outsourcedCompaniesTable) return;
  const helpers = outsourcedCompaniesViewHelpers();
  // Perfis escopados por Unidade (Administrador Local/Gestor de EPI) são os
  // únicos cujos itens vêm com local_status (annotate_outsourced_company_visibility,
  // só roda para eles) — é o que diferencia "arquivar nesta Unidade" (por
  // vínculo) do arquivamento global do corporativo, que continua exclusivo
  // de quem não é escopado.
  const isUnitScoped = ['admin', 'user'].includes(state.user?.role);
  const allLinked = state.outsourcedCompanies || [];
  const isArchivedInUnit = helpers.isArchivedInUnit || ((item) => String(item?.local_status || '') === 'inactive');
  const activeLinked = isUnitScoped
    ? allLinked.filter((item) => !isArchivedInUnit(item))
    : allLinked;
  const visible = helpers.visibleOutsourcedCompanies
    ? helpers.visibleOutsourcedCompanies(activeLinked, state.outsourcedCompaniesFilters)
    : activeLinked;
  const canUpdate = hasPermission(['employees:update', 'employees:update_simplified']);
  refs.outsourcedCompaniesTable.innerHTML = visible
    .map((item) => formatOutsourcedCompanyRow(item, { canUpdate }))
    .join('') || globalThis.dsTableState({
      colspan: 7,
      message: tr('outsourcedCompany.empty', 'Nenhuma empresa terceirizada cadastrada.'),
    });
  // Empresas do tenant que a própria Unidade ainda não vinculou (ADR-0002
  // §12) — seção separada da "Lista" principal, nunca junto: mostrar como
  // "vinculável" algo que ainda não é gerenciável evitaria confundir com o
  // que já está sob a Unidade do ator.
  if (refs.outsourcedCompaniesAvailableTable) {
    const available = state.outsourcedCompaniesAvailable || [];
    refs.outsourcedCompaniesAvailableTable.innerHTML = available
      .map((item) => formatOutsourcedCompanyAvailableRow(item))
      .join('') || globalThis.dsTableState({
        colspan: 5,
        message: tr('outsourcedCompany.availableEmpty', 'Nenhuma empresa disponível para vincular.'),
      });
  }
  // Empresas arquivadas NESTA Unidade (Administrador Local/Gestor de EPI) —
  // mesma ação de vínculo local (toggleOutsourcedCompanyUnitLink), só
  // exibida em seção separada da Lista principal; nunca duplica o
  // arquivamento global (ARCHIVAL_ENTITIES.outsourcedCompany/"restaurar"),
  // que continua exclusivo de quem não é escopado por Unidade — os dois
  // cartões da aba "Empresas Arquivadas" são mutuamente exclusivos por
  // perfil, nunca mostrados juntos.
  if (refs.outsourcedCompanyUnitArchivedCard) refs.outsourcedCompanyUnitArchivedCard.hidden = !isUnitScoped;
  if (refs.archivedOutsourcedCompaniesCard) refs.archivedOutsourcedCompaniesCard.hidden = isUnitScoped;
  if (isUnitScoped && refs.outsourcedCompanyUnitArchivedTable) {
    const archived = allLinked.filter((item) => isArchivedInUnit(item));
    refs.outsourcedCompanyUnitArchivedTable.innerHTML = archived
      .map((item) => formatOutsourcedCompanyUnitArchivedRow(item))
      .join('') || globalThis.dsTableState({
        colspan: 6,
        message: tr('outsourcedCompany.unitArchivedEmpty', 'Nenhuma empresa arquivada nesta Unidade.'),
      });
  }
  // O seletor de empresa do Cadastro de Colaboradores depende da mesma
  // lista — resincroniza sempre que ela muda (mesma lógica de
  // bindDependentSelects, mas esta lista não vem do bootstrap).
  syncOutsourcedEmployeeCompanySelect();
  renderOutsourcedEmployees();
}

// Linha de "Empresas arquivadas nesta Unidade" — mesmos dados do vínculo
// local (unit_link_deactivated_at/reason/by_user_id, anexados por
// annotate_outsourced_company_visibility), só que renderizados numa seção
// separada da Lista, com "Desarquivar" em vez de "Editar".
function formatOutsourcedCompanyUnitArchivedRow(item) {
  const entityId = escapeHtml(String(item.id ?? ''));
  const responsible = (state.users || []).find((u) => String(u.id) === String(item.unit_link_deactivated_by_user_id));
  const responsibleName = responsible ? (responsible.full_name || '') : '';
  return `<tr><td>${escapeHtml(item.legal_name || '')}</td><td>${escapeHtml(item.cnpj || '') || '-'}</td>`
    + `<td>${formatDate(item.unit_link_deactivated_at)}</td><td>${escapeHtml(item.unit_link_deactivation_reason || '') || '-'}</td>`
    + `<td>${escapeHtml(responsibleName) || '-'}</td>`
    + `<td><button class="ghost" data-outsourced-company-toggle-link="${entityId}" data-activate="1">${escapeHtml(tr('outsourcedCompany.activateLink', 'Desarquivar nesta Unidade'))}</button></td></tr>`;
}

function formatOutsourcedCompanyRow(item, permissions) {
  const helpers = outsourcedCompaniesViewHelpers();
  const kindLabel = helpers.companyKindLabel ? helpers.companyKindLabel(item.company_kind) : (item.company_kind || '');
  const modeLabel = helpers.registrationModeLabel ? helpers.registrationModeLabel(item) : '';
  const hasFullUpdate = hasPermission('employees:update');
  // Promover só faz sentido para quem ainda está no Simplificado — o backend
  // também recusa promover quem já é Padrão, mas oferecer o botão sempre só
  // geraria mensagem de erro sem efeito. Ação exclusiva de Administrador
  // Geral/de Registro (employees:update completo) — Administrador Local/
  // Gestor de EPI (só employees:update_simplified) nunca a alcançam no
  // backend (handle_post_outsourced_company_promote não foi ampliada de
  // propósito, ADR-0002 §10.5), então o botão fica fora para eles também.
  const showPromote = hasFullUpdate && (helpers.canPromote ? helpers.canPromote(item) : true);
  // Trava pós-promoção (ADR-0002 §12): "Editar" só continua valendo se o
  // ator tem employees:update completo OU a empresa ainda está no
  // Simplificado — espelha ensure_actor_can_edit_outsourced_company_corporate_fields
  // do backend, que é quem decide de fato. Travado + ainda pode gerenciar
  // (permissions.canUpdate) → oferece "Solicitar atualização" no lugar.
  const corporateLocked = helpers.isCorporateLocked ? helpers.isCorporateLocked(item) : false;
  const canEditCorporate = helpers.canEditCorporateFields
    ? helpers.canEditCorporateFields(item, hasFullUpdate) : true;
  const entityId = escapeHtml(String(item.id ?? ''));
  const buttons = [];
  if (permissions.canUpdate && canEditCorporate) {
    buttons.push(`<button class="ghost" data-outsourced-company-edit="${entityId}">${escapeHtml(tr('edit', 'Editar'))}</button>`);
  } else if (permissions.canUpdate && corporateLocked) {
    buttons.push(`<button class="ghost" data-outsourced-company-request-update="${entityId}">${escapeHtml(tr('outsourcedCompany.requestUpdate', 'Solicitar atualização cadastral'))}</button>`);
  }
  if (showPromote) {
    buttons.push(`<button class="ghost" data-outsourced-company-promote="${entityId}">${escapeHtml(tr('outsourcedCompany.promote', 'Promover a Cadastro Padrão'))}</button>`);
  }
  // "Arquivar nesta Unidade" (vínculo local, ex-"Desativar vínculo local" —
  // ADR-0002 §12 item 8/Problema 4 do pedido): nunca a mesma coisa que
  // arquivar o corporativo (ARCHIVAL_ENTITIES.outsourcedCompany, exclusivo
  // de quem não é escopado por Unidade) — sempre liberado para quem já
  // gerencia a empresa, independente de registration_mode/trava acima.
  // `local_status` só vem preenchido para quem é escopado por Unidade
  // (fetch_outsourced_companies/annotate_outsourced_company_visibility) —
  // ausente para Geral/Registro, que não têm UMA Unidade só para alternar.
  // Na prática só chega aqui com linkActive === true: renderOutsourcedCompanies
  // já filtra local_status === 'inactive' para fora desta tabela (formatOutsourcedCompanyUnitArchivedRow
  // cobre a seção "Empresas arquivadas nesta Unidade") — o ramo inativo
  // segue aqui só como defesa, nunca alcançado no fluxo normal.
  const linkStatus = item.local_status;
  if (permissions.canUpdate && linkStatus !== undefined && linkStatus !== null) {
    const linkActive = String(linkStatus) !== 'inactive';
    const toggleLabel = linkActive
      ? tr('outsourcedCompany.deactivateLink', 'Arquivar nesta Unidade')
      : tr('outsourcedCompany.activateLink', 'Desarquivar nesta Unidade');
    buttons.push(`<button class="ghost" data-outsourced-company-toggle-link="${entityId}" data-activate="${linkActive ? '0' : '1'}">${escapeHtml(toggleLabel)}</button>`);
  }
  const actions = buttons.length ? `<div class="action-group">${buttons.join('')}</div>` : '-';
  const linkStatusLabel = linkStatus === undefined || linkStatus === null
    ? '-'
    : (String(linkStatus) === 'inactive' ? tr('outsourcedCompany.linkInactive', 'Arquivado') : tr('outsourcedCompany.linkActive', 'Ativo'));
  return `<tr><td>${escapeHtml(item.legal_name || '')}</td><td>${escapeHtml(item.cnpj || '') || '-'}</td>`
    + `<td>${escapeHtml(kindLabel)}</td><td>${escapeHtml(item.epi_responsibility || '')}</td>`
    + `<td>${escapeHtml(modeLabel)}</td><td>${escapeHtml(linkStatusLabel)}</td><td>${actions}</td></tr>`;
}

// Empresas do tenant ainda não vinculadas à Unidade do ator — linha com só
// os campos públicos (ADR-0002 §12 item 12 do pedido: nunca contrato, nota
// ou colaborador de outra Unidade) + a ação "Vincular à minha unidade".
function formatOutsourcedCompanyAvailableRow(item) {
  const helpers = outsourcedCompaniesViewHelpers();
  const modeLabel = helpers.registrationModeLabel ? helpers.registrationModeLabel(item) : '';
  const entityId = escapeHtml(String(item.id ?? ''));
  return `<tr><td>${escapeHtml(item.legal_name || '')}</td><td>${escapeHtml(item.trade_name || '') || '-'}</td>`
    + `<td>${escapeHtml(item.cnpj || '') || '-'}</td><td>${escapeHtml(modeLabel)}</td>`
    + `<td><button class="ghost" data-outsourced-company-link="${entityId}">${escapeHtml(tr('outsourcedCompany.linkToMyUnit', 'Vincular à minha unidade'))}</button></td></tr>`;
}

function syncOutsourcedCompaniesFilters() {
  state.outsourcedCompaniesFilters.search = String(refs.outsourcedCompaniesFilterSearch?.value || '').trim();
  state.outsourcedCompaniesFilters.kind = String(refs.outsourcedCompaniesFilterKind?.value || '').trim();
  renderOutsourcedCompanies();
}

// Alterna o formulário entre cadastrar e atualizar — mesmo padrão de
// setLegalEntityFormMode.
function setOutsourcedCompanyFormMode(mode) {
  const cancel = document.getElementById('outsourced-company-cancel-edit');
  if (cancel) cancel.hidden = mode !== 'edit';
}

// Unidade de origem (ADR-0002 §12): imutável depois de criada — nem
// Administrador Geral reatribui por aqui, o backend nem lê mais esse campo
// no update. No CADASTRO (sem id ainda), continua o comportamento de
// sempre: Administrador Local/Gestor de EPI (isOperationalProfile())
// travados na própria unidade operacional (resolve_outsourced_company_unit_id
// só roda no create), demais perfis com seletor livre. Auto-detecta o modo
// pelo próprio estado do formulário (mesmo `editingId` que saveSimpleForm
// usa), então funciona tanto chamado por startEditOutsourcedCompany/
// resetOutsourcedCompanyForm quanto por bindDependentSelects (que não sabe
// se há uma edição em andamento).
function syncOutsourcedCompanyUnitOptions() {
  const unitField = document.getElementById('outsourced-company-unit');
  if (!unitField) return;
  const form = document.getElementById('outsourced-company-form');
  const editingId = form?.elements?.id?.value ? String(form.elements.id.value) : '';
  if (editingId) {
    const item = (state.outsourcedCompanies || []).find((entity) => String(entity.id) === editingId);
    const origin = item?.unit_id != null
      ? (state.units || []).find((unit) => String(unit.id) === String(item.unit_id))
      : null;
    unitField.innerHTML = origin
      ? `<option value="${origin.id}">${escapeHtml(origin.name)} - ${escapeHtml(unitTypeLabel(origin.unit_type))}</option>`
      : `<option value="">${escapeHtml(tr('outsourcedCompany.allUnits', 'Todas as unidades (padrão)'))}</option>`;
    unitField.value = origin ? String(origin.id) : '';
    unitField.disabled = true;
    return;
  }
  const lockByOperationalProfile = isOperationalProfile();
  if (!lockByOperationalProfile) {
    unitField.disabled = false;
    return;
  }
  const operationalUnitId = String(state.user?.operational_unit_id || '').trim();
  const scopedUnit = filterByUserCompany(state.units || []).find((item) => String(item.id) === operationalUnitId);
  unitField.innerHTML = scopedUnit
    ? `<option value="${scopedUnit.id}">${scopedUnit.name} - ${unitTypeLabel(scopedUnit.unit_type)}</option>`
    : '<option value="">Sem unidade operacional ativa</option>';
  unitField.value = scopedUnit ? String(scopedUnit.id) : '';
  unitField.disabled = true;
}

// Trava pós-promoção (ADR-0002 §12): quando o ator não tem employees:update
// completo e a empresa já é Cadastro Padrão, os campos corporativos ficam
// só-leitura com um aviso — mesma decisão que
// ensure_actor_can_edit_outsourced_company_corporate_fields toma no
// backend (que é quem decide de fato); aqui só evita deixar o formulário
// "sumir" sem explicação quando "Solicitar atualização" é a única ação
// oferecida na linha (formatOutsourcedCompanyRow).
const OUTSOURCED_COMPANY_CORPORATE_FIELDS = ['legal_name', 'trade_name', 'cnpj', 'company_kind', 'epi_responsibility'];

function applyOutsourcedCompanyCorporateLock(item) {
  const form = document.getElementById('outsourced-company-form');
  const banner = refs.outsourcedCompanyCorporateLockBanner;
  const helpers = outsourcedCompaniesViewHelpers();
  const locked = Boolean(item) && helpers.isCorporateLocked
    && helpers.isCorporateLocked(item) && !hasPermission('employees:update');
  if (form) {
    OUTSOURCED_COMPANY_CORPORATE_FIELDS.forEach((name) => {
      const field = form.elements[name];
      if (field) field.disabled = locked;
    });
    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) submitButton.hidden = locked;
  }
  if (banner) banner.hidden = !locked;
}

function resetOutsourcedCompanyForm() {
  const form = document.getElementById('outsourced-company-form');
  if (!form) return;
  form.reset();
  form.elements.id.value = '';
  syncOutsourcedCompanyUnitOptions();
  applyOutsourcedCompanyCorporateLock(null);
  setFormSubmitLabel('outsourced-company-form', tr('outsourcedCompany.save', 'Salvar Empresa'));
  setOutsourcedCompanyFormMode('create');
}

function startEditOutsourcedCompany(entityId) {
  const item = (state.outsourcedCompanies || []).find((entity) => String(entity.id) === String(entityId));
  const form = document.getElementById('outsourced-company-form');
  if (!item || !form) return;
  form.elements.id.value = item.id;
  form.elements.legal_name.value = item.legal_name || '';
  form.elements.trade_name.value = item.trade_name || '';
  form.elements.cnpj.value = item.cnpj || '';
  form.elements.company_kind.value = item.company_kind || 'outsourced';
  form.elements.epi_responsibility.value = item.epi_responsibility || 'Conforme Contrato';
  syncOutsourcedCompanyUnitOptions();
  applyOutsourcedCompanyCorporateLock(item);
  setFormSubmitLabel('outsourced-company-form', tr('outsourcedCompany.update', 'Atualizar Empresa'));
  setOutsourcedCompanyFormMode('edit');
  showView('terceirizados');
  focusRegistrationTab('terceirizados');
}

// "Vincular à minha unidade" (ADR-0002 §12) — cria o vínculo local sem
// duplicar o cadastro corporativo; usado tanto pelo botão na seção
// "Empresas disponíveis para vinculação" quanto pelo fluxo de duplicidade
// de CNPJ (handleOutsourcedCompanyDuplicateError, perto de saveSimpleForm).
async function linkOutsourcedCompanyToMyUnit(entityId) {
  if (!requirePermission(['employees:update', 'employees:update_simplified'])) return;
  try {
    await api(`/api/outsourced-companies/${entityId}/link`, {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user.id }),
    });
    await loadOutsourcedCompanies();
  } catch (error) {
    alert(error.message);
  }
}

// Arquiva/desarquiva a empresa NESTA Unidade (vínculo local) — nunca o
// cadastro corporativo (ADR-0002 §12 item 8 do pedido: não confundir com o
// arquivamento global de ARCHIVAL_ENTITIES.outsourcedCompany, exclusivo de
// quem não é escopado por Unidade). Some da Lista e do seletor de novos
// colaboradores desta Unidade; outras Unidades vinculadas não são afetadas.
async function toggleOutsourcedCompanyUnitLink(entityId, activate) {
  if (!requirePermission(['employees:update', 'employees:update_simplified'])) return;
  let reason = '';
  if (!activate) {
    reason = prompt(tr('outsourcedCompany.deactivateLinkReasonPrompt', 'Motivo do arquivamento (opcional):')) || '';
    if (reason === null) return;
  }
  // Caminho literal em cada ramo (em vez de interpolar activate/deactivate
  // na URL) — mesma convenção do resto do app.js, path dinâmico só para
  // IDs numéricos; test_frontend_api_contract.py confronta cada chamada
  // com as rotas registradas no router e não resolve enum-em-path.
  const path = activate
    ? `/api/outsourced-companies/${entityId}/unit-link/activate`
    : `/api/outsourced-companies/${entityId}/unit-link/deactivate`;
  try {
    await api(path, {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user.id, reason }),
    });
    await loadOutsourcedCompanies();
  } catch (error) {
    alert(error.message);
  }
}

// "Solicitar atualização cadastral" (ADR-0002 §12) — modal simples
// (mensagem livre), mesmo padrão de openRequestReportModal/submitReportRequest
// (estoque.html), só que sem tela dedicada: usa prompt() para manter o
// escopo proporcional a "avisar que um campo precisa de correção".
async function requestOutsourcedCompanyUpdate(entityId) {
  if (!requirePermission(['employees:update', 'employees:update_simplified'])) return;
  const message = prompt(tr(
    'outsourcedCompany.requestUpdatePrompt',
    'Descreva o que precisa ser corrigido/atualizado no cadastro corporativo:',
  ));
  if (!message || !message.trim()) return;
  try {
    await api(`/api/outsourced-companies/${entityId}/update-requests`, {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user.id, message: message.trim() }),
    });
    alert(tr('outsourcedCompany.requestUpdateSent', 'Solicitação enviada ao Administrador Geral/de Registro.'));
  } catch (error) {
    alert(error.message);
  }
}

// ── Inbox de "Solicitações" (Geral/Registro, ADR-0002 §12) ────────────────
async function loadOutsourcedCompanyUpdateRequests() {
  // Card (e por tabela, a própria aba "Solicitações" — syncViewTabsVisibility
  // esconde uma aba cujo painel não tem nenhum filho visível) só existe para
  // quem tem employees:update completo (Geral/Registro): Administrador
  // Local/Gestor de EPI só REGISTRAM pedido (requestOutsourcedCompanyUpdate),
  // nunca veem a fila de resolução dos outros.
  const allowed = hasPermission('employees:update');
  if (refs.outsourcedCompanyUpdateRequestsCard) refs.outsourcedCompanyUpdateRequestsCard.hidden = !allowed;
  const nav = document.querySelector('[data-vtabs="terceirizados"]');
  if (nav && typeof syncViewTabsVisibility === 'function') syncViewTabsVisibility(nav);
  if (!allowed) return;
  try {
    const data = await api(`/api/outsourced-companies/update-requests?status=pending&${actorQuery()}`);
    state.outsourcedCompanyUpdateRequests = data.outsourced_company_update_requests || data.items || [];
  } catch (error) {
    state.outsourcedCompanyUpdateRequests = [];
    reportNonCriticalError('[terceirizados] falha ao carregar solicitações de atualização', error);
  }
  renderOutsourcedCompanyUpdateRequests();
}

function renderOutsourcedCompanyUpdateRequests() {
  if (!refs.outsourcedCompanyUpdateRequestsTable) return;
  const items = state.outsourcedCompanyUpdateRequests || [];
  refs.outsourcedCompanyUpdateRequestsTable.innerHTML = items.map((request) => {
    const companyName = (state.outsourcedCompanies || [])
      .find((c) => String(c.id) === String(request.outsourced_company_id))?.legal_name || `#${request.outsourced_company_id}`;
    return `<tr><td>${escapeHtml(companyName)}</td><td>${escapeHtml(request.requested_by_name || '')}</td>`
      + `<td>${escapeHtml(request.message || '')}</td><td>${escapeHtml(request.created_at || '')}</td>`
      + `<td><button class="ghost" data-outsourced-company-update-request-resolve="${escapeHtml(String(request.id))}">${escapeHtml(tr('outsourcedCompany.resolveRequest', 'Resolver'))}</button></td></tr>`;
  }).join('') || globalThis.dsTableState({
    colspan: 5,
    message: tr('outsourcedCompany.requestsEmpty', 'Nenhuma solicitação pendente.'),
  });
}

async function resolveOutsourcedCompanyUpdateRequest(requestId) {
  if (!requirePermission('employees:update')) return;
  const notes = prompt(tr('outsourcedCompany.resolveRequestNotesPrompt', 'Notas da resolução (opcional):')) || '';
  try {
    await api(`/api/outsourced-companies/update-requests/${requestId}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user.id, status: 'resolved', resolution_notes: notes }),
    });
    await loadOutsourcedCompanyUpdateRequests();
  } catch (error) {
    alert(error.message);
  }
}

// Chamado só pelo catch de saveSimpleForm para o outsourced-company-form
// (ADR-0002 §12 itens 14-15 do pedido). Devolve `true` quando já tratou o
// erro (a mensagem genérica não deve mais aparecer via alert()).
async function handleOutsourcedCompanyDuplicateError(error, form) {
  if (error?.code === 'duplicate_cnpj') {
    const existingId = error.payload?.existing_company_id;
    const confirmed = confirm(
      `${error.message}\n\n${tr('outsourcedCompany.duplicateCnpjLinkPrompt', 'Deseja vincular essa empresa à sua Unidade em vez de cadastrar de novo?')}`,
    );
    if (confirmed && existingId) {
      await linkOutsourcedCompanyToMyUnit(existingId);
    }
    return true;
  }
  if (error?.code === 'possible_duplicate') {
    const matches = error.payload?.matches || [];
    const names = matches.map((item) => `- ${item.legal_name}${item.trade_name ? ` (${item.trade_name})` : ''}`).join('\n');
    const confirmed = confirm(
      `${error.message}\n\n${names}\n\n${tr('outsourcedCompany.confirmCreateAnyway', 'Cadastrar mesmo assim?')}`,
    );
    if (confirmed) {
      form.dataset.confirmDuplicate = '1';
      if (typeof form.requestSubmit === 'function') form.requestSubmit();
      else form.dispatchEvent(new Event('submit', { cancelable: true }));
    }
    return true;
  }
  return false;
}

async function promoteOutsourcedCompany(entityId) {
  if (!requirePermission('employees:update')) return;
  const item = (state.outsourcedCompanies || []).find((entity) => String(entity.id) === String(entityId));
  if (!item) return;
  const confirmed = confirm(tr(
    'outsourcedCompany.promoteConfirm',
    'Promover ao Cadastro Padrão? A empresa passa a ser tratada como Cadastro Padrão. É preciso ter um CNPJ preenchido.',
  ) + `\n\n${item.legal_name}`);
  if (!confirmed) return;
  try {
    await api(`/api/outsourced-companies/${entityId}/promote`, {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user.id }),
    });
    await loadOutsourcedCompanies();
  } catch (error) {
    alert(error.message);
  }
}

// Popula o seletor de empresa terceirizada/prestadora do Cadastro de
// Colaboradores — depende de state.outsourcedCompanies, que (ao contrário de
// state.companies/state.units) só chega quando a tela é aberta, então este
// sync roda de novo a cada loadOutsourcedCompanies(), não em
// bindDependentSelects() (que só cobre dados do bootstrap).
function syncOutsourcedEmployeeCompanySelect() {
  const field = document.getElementById('outsourced-employee-outsourced-company');
  if (!field) return;
  const previous = field.value;
  // Empresa arquivada NESTA Unidade não pode ser oferecida para novos
  // colaboradores — mesmo espelho do backend
  // (is_outsourced_company_available_to_unit, Problema 3 do pedido): some
  // do seletor assim que arquivada, volta assim que desarquivada. Some
  // sozinho quando o próprio state.outsourcedCompanies muda (toggleOutsourcedCompanyUnitLink
  // recarrega a lista), sem precisar de lógica extra aqui.
  const helpers = outsourcedCompaniesViewHelpers();
  const isArchivedInUnit = helpers.isArchivedInUnit || ((item) => String(item?.local_status || '') === 'inactive');
  const companies = filterByUserCompany(state.outsourcedCompanies || [])
    .filter((item) => !isArchivedInUnit(item));
  field.innerHTML = companies
    .map((item) => `<option value="${item.id}">${escapeHtml(item.trade_name || item.legal_name || '')}</option>`)
    .join('');
  if (previous && companies.some((item) => String(item.id) === previous)) field.value = previous;
}

// Administrador Local/Gestor de EPI (isOperationalProfile()) só operam
// dentro da própria unidade operacional — o backend já força isso em
// create/update_employee_outsourced_simplified
// (ensure_actor_unit_scope_for_target), mas até esta correção o campo
// aparecia como um seletor livre, deixando esses perfis escolherem outra
// unidade na UI e só descobrirem o bloqueio depois de tentar salvar.
// Mesmo padrão já usado em syncEpiUnitOptions/hint de Unidade nos filtros
// de Ficha/Entregas: preenche com a própria unidade e desabilita o campo.
function syncOutsourcedEmployeeUnitOptions() {
  const companyField = document.getElementById('outsourced-employee-company');
  const unitField = document.getElementById('outsourced-employee-unit');
  const unitHint = document.getElementById('outsourced-employee-unit-hint');
  if (!companyField || !unitField) return;
  const companyId = companyField.value || state.user?.company_id || '';
  const units = filterByUserCompany(state.units).filter((item) => !companyId || String(item.company_id) === String(companyId));
  const lockByOperationalProfile = isOperationalProfile();
  const operationalUnitId = String(state.user?.operational_unit_id || '').trim();
  const scopedUnits = lockByOperationalProfile
    ? units.filter((item) => String(item.id) === operationalUnitId)
    : units;
  unitField.innerHTML = scopedUnits.length
    ? scopedUnits.map((item) => `<option value="${item.id}">${item.name} - ${unitTypeLabel(item.unit_type)}</option>`).join('')
    : '<option value="">Sem unidade operacional ativa</option>';
  if (scopedUnits.length && !scopedUnits.some((item) => String(item.id) === String(unitField.value))) {
    unitField.value = String(scopedUnits[0].id);
  } else if (!scopedUnits.length) {
    unitField.value = '';
  }
  unitField.disabled = lockByOperationalProfile;
  if (unitHint) unitHint.hidden = !lockByOperationalProfile;
}

// ── Cadastro de Colaboradores simplificado (ADR-0002 §10.2) ─────────────────
// Só terceirizado/prestador, nunca CLT (o backend recusa). Sem rota de
// listagem própria — deriva de state.employees (já carregado pelo
// bootstrap, `fetch_employees` inclui tipo_vinculo/outsourced_company_id),
// mesma estratégia do app Flutter: filtro client-side, sem endpoint novo.

function outsourcedEmployeesViewHelpers() {
  return globalThis.__EPI_OUTSOURCED_EMPLOYEES_VIEW__ || {};
}

function outsourcedEmployeesList() {
  const helpers = outsourcedEmployeesViewHelpers();
  const all = filterByUserCompany(state.employees || []);
  return helpers.outsourcedEmployeesOnly ? helpers.outsourcedEmployeesOnly(all) : all.filter((item) => {
    const tipo = String(item.tipo_vinculo || '').trim();
    return Boolean(tipo) && tipo !== 'CLT' && Boolean(item.outsourced_company_id);
  });
}

function renderOutsourcedEmployees() {
  if (!refs.outsourcedEmployeesTable) return;
  const helpers = outsourcedEmployeesViewHelpers();
  const all = outsourcedEmployeesList();
  const visible = helpers.visibleOutsourcedEmployees
    ? helpers.visibleOutsourcedEmployees(all, state.outsourcedEmployeesFilters)
    : all;
  const canUpdate = hasPermission('employees:update_simplified');
  refs.outsourcedEmployeesTable.innerHTML = visible
    .map((item) => formatOutsourcedEmployeeRow(item, { canUpdate }))
    .join('') || globalThis.dsTableState({
      colspan: 6,
      message: tr('outsourcedCompany.employeesEmpty', 'Nenhum colaborador terceirizado/prestador cadastrado.'),
    });
}

function formatOutsourcedEmployeeRow(item, permissions) {
  const helpers = outsourcedEmployeesViewHelpers();
  const vincLabel = helpers.tipoVinculoLabel ? helpers.tipoVinculoLabel(item.tipo_vinculo) : (item.tipo_vinculo || '');
  const outsourcedCompany = (state.outsourcedCompanies || []).find((c) => String(c.id) === String(item.outsourced_company_id));
  const companyLabel = outsourcedCompany ? (outsourcedCompany.trade_name || outsourcedCompany.legal_name) : '-';
  const entityId = escapeHtml(String(item.id ?? ''));
  const buttons = [];
  if (permissions.canUpdate) {
    buttons.push(`<button class="ghost" data-outsourced-employee-edit="${entityId}">${escapeHtml(tr('edit', 'Editar'))}</button>`);
  }
  if (hasPermission('employees:delete')) {
    buttons.push(`<button class="ghost" data-outsourced-employee-archive="${entityId}">${escapeHtml(tr('employee.archive', 'Arquivar'))}</button>`);
  }
  const actions = buttons.length ? `<div class="action-group">${buttons.join('')}</div>` : '-';
  return `<tr><td>${escapeHtml(item.name || '')}</td><td>${escapeHtml(item.role_name || '')}</td>`
    + `<td>${escapeHtml(vincLabel)}</td><td>${escapeHtml(companyLabel)}</td>`
    + `<td>${escapeHtml(item.unit_name || '')}</td><td>${actions}</td></tr>`;
}

function syncOutsourcedEmployeesFilters() {
  state.outsourcedEmployeesFilters.search = String(refs.outsourcedEmployeesFilterSearch?.value || '').trim();
  renderOutsourcedEmployees();
}

function setOutsourcedEmployeeFormMode(mode) {
  const cancel = document.getElementById('outsourced-employee-cancel-edit');
  if (cancel) cancel.hidden = mode !== 'edit';
}

function resetOutsourcedEmployeeForm() {
  const form = document.getElementById('outsourced-employee-form');
  if (!form) return;
  form.reset();
  form.elements.id.value = '';
  syncOutsourcedEmployeeUnitOptions();
  setFormSubmitLabel('outsourced-employee-form', tr('outsourcedCompany.employeeSave', 'Salvar Colaborador'));
  setOutsourcedEmployeeFormMode('create');
}

// Diferente de startEditOutsourcedCompany (que reaproveita state.outsourcedCompanies
// já carregado), o Cadastro de Colaboradores só tem no bootstrap os campos da
// listagem geral — origin_company_registration/badge_number/notes só vêm do
// item único (GET /api/employees/:id), por isso busca de novo ao editar.
async function startEditOutsourcedEmployee(entityId) {
  const form = document.getElementById('outsourced-employee-form');
  if (!form) return;
  try {
    const data = await api(`/api/employees/${entityId}?${actorQuery()}`);
    const item = data.employee || data;
    if (!item || !item.id) return;
    form.elements.id.value = item.id;
    if (form.elements.company_id) form.elements.company_id.value = item.company_id || '';
    syncOutsourcedEmployeeUnitOptions();
    if (form.elements.unit_id) form.elements.unit_id.value = item.unit_id || '';
    syncOutsourcedEmployeeCompanySelect();
    if (form.elements.outsourced_company_id) form.elements.outsourced_company_id.value = item.outsourced_company_id || '';
    form.elements.name.value = item.name || '';
    form.elements.cpf.value = item.cpf || '';
    form.elements.role_name.value = item.role_name || '';
    form.elements.tipo_vinculo.value = item.tipo_vinculo || 'Terceirizado';
    form.elements.admission_date.value = item.admission_date || '';
    if (form.elements.origin_company_registration) form.elements.origin_company_registration.value = item.origin_company_registration || '';
    if (form.elements.badge_number) form.elements.badge_number.value = item.badge_number || '';
    if (form.elements.notes) form.elements.notes.value = item.notes || '';
    setFormSubmitLabel('outsourced-employee-form', tr('outsourcedCompany.employeeUpdate', 'Atualizar Colaborador'));
    setOutsourcedEmployeeFormMode('edit');
    showView('terceirizados');
    const nav = document.querySelector('[data-vtabs="terceirizados"]');
    if (nav) activateViewTab(nav, 'colaboradores');
  } catch (error) {
    alert(error.message);
  }
}

// Arquivar reaproveita a MESMA rota/regra do colaborador CLT
// (/api/employees/:id/archive) — é o mesmo registro, só filtrado nesta
// tela; reusa archiveEntityRecord('employee', ...) para não duplicar o
// fluxo de motivo/confirmação/auditoria.
async function archiveOutsourcedEmployee(entityId) {
  await archiveEntityRecord('employee', entityId);
  renderOutsourcedEmployees();
}

// ── Relatório de headcount por empresa terceirizada/prestadora (ADR-0002
// §10.4) — GET /api/outsourced-companies/employees-summary. ─────────────────
async function loadOutsourcedEmployeesSummary() {
  if (!hasPermission('employees:view')) return;
  try {
    const data = await api(`/api/outsourced-companies/employees-summary?${actorQuery()}`);
    state.outsourcedEmployeesSummary = data.outsourced_employees_summary || data.items || [];
  } catch (error) {
    state.outsourcedEmployeesSummary = [];
    reportNonCriticalError('[terceirizados] falha ao carregar relatório de colaboradores', error);
  }
  renderOutsourcedEmployeesSummary();
}

function renderOutsourcedEmployeesSummary() {
  if (!refs.outsourcedEmployeesSummaryTable) return;
  const items = state.outsourcedEmployeesSummary || [];
  refs.outsourcedEmployeesSummaryTable.innerHTML = items.map((entry) => {
    const byTipo = Object.entries(entry.by_tipo_vinculo || {})
      .map(([tipo, count]) => `${escapeHtml(tipo)}: ${count}`)
      .join(' · ') || '-';
    const name = entry.trade_name || entry.legal_name || '';
    return `<tr><td>${escapeHtml(name)}</td><td>${entry.active_count ?? 0}</td>`
      + `<td>${entry.archived_count ?? 0}</td><td>${byTipo}</td></tr>`;
  }).join('') || globalThis.dsTableState({
    colspan: 4,
    message: tr('outsourcedCompany.reportsEmpty', 'Nenhuma empresa terceirizada/prestadora cadastrada.'),
  });
}

// ── Centro de Migração de Dados (ADR-0003, fase 2) ─────────────────────────
//
// O assistente monta um rascunho local (`state.migracao`) e só conversa com o
// servidor em três momentos: analisar o arquivo, simular (dry-run) e aplicar.
// Nenhuma decisão de autorização acontece aqui — o backend revalida permissão,
// módulo, catálogo e mapeamento a cada chamada.

function dataMigrationHelpers() {
  return globalThis.__EPI_DATA_MIGRATION_VIEW__ || {};
}

function migracaoState() {
  if (!state.migracao) {
    state.migracao = {
      entities: [], sources: [], jobs: [],
      step: 'entidade', entity: '', sourceKind: 'xlsx',
      fileName: '', fileBase64: '', sheet: '',
      columns: [], sample: [], detected: {}, details: [],
      mapping: {}, mappingSource: '', totalRows: 0,
      preview: null, busy: false,
    };
  }
  return state.migracao;
}

function migracaoEntityDescriptor() {
  const draft = migracaoState();
  return (draft.entities || []).find((item) => item.key === draft.entity) || null;
}

async function loadDataMigrationCatalog() {
  if (!hasPermission('data_migration:manage')) return;
  const draft = migracaoState();
  try {
    const data = await api(`/api/data-migration/catalog?${actorQuery()}`);
    draft.entities = data.entities || [];
    draft.sources = data.sources || [];
  } catch (error) {
    draft.entities = [];
    draft.sources = [];
    reportNonCriticalError('[migracao] falha ao carregar o catálogo', error);
  }
  renderDataMigrationCatalog();
  syncDataMigrationSelectors();
}

function renderDataMigrationCatalog() {
  if (!refs.migracaoCatalogCards) return;
  const helpers = dataMigrationHelpers();
  const draft = migracaoState();
  const term = String(refs.migracaoCatalogFilter?.value || '').trim().toLowerCase();
  const cards = (helpers.dashboardCards ? helpers.dashboardCards(draft.entities) : [])
    .filter((card) => !term || card.label.toLowerCase().includes(term) || card.key.includes(term));
  refs.migracaoCatalogCards.innerHTML = cards.map((card) => {
    const badge = card.enabled
      ? `<span class="badge badge-status-active">${escapeHtml(tr('dataMigration.cardReady', 'Disponível'))}</span>`
      : `<span class="badge badge-role-user">${escapeHtml(tr('dataMigration.cardSoon', 'Em breve'))}</span>`;
    const fields = tr('dataMigration.cardFields', '{n} campos').replace('{n}', String(card.fieldCount));
    return `<button type="button" class="migracao-card${card.enabled ? '' : ' is-disabled'}"`
      + ` data-migracao-card="${escapeHtml(card.key)}"${card.enabled ? '' : ' disabled'}>`
      + `<strong>${escapeHtml(card.label)}</strong>${badge}`
      + `<small class="muted">${escapeHtml(fields)}</small></button>`;
  }).join('') || `<p class="muted">${escapeHtml(tr('dataMigration.catalogEmpty', 'Nenhuma entidade encontrada.'))}</p>`;
}

function syncDataMigrationSelectors() {
  const draft = migracaoState();
  const helpers = dataMigrationHelpers();
  if (refs.migracaoEntity) {
    refs.migracaoEntity.innerHTML = (draft.entities || [])
      .filter((entity) => entity.enabled)
      .map((entity) => `<option value="${escapeHtml(entity.key)}">${escapeHtml(entity.label)}</option>`)
      .join('');
    if (draft.entity) refs.migracaoEntity.value = draft.entity;
    else draft.entity = refs.migracaoEntity.value || '';
  }
  if (refs.migracaoSourceKind) {
    refs.migracaoSourceKind.innerHTML = (draft.sources || []).map((source) => {
      const label = source.enabled
        ? source.kind.toUpperCase()
        : `${source.kind.toUpperCase()} — ${tr('dataMigration.cardSoon', 'Em breve')}`;
      return `<option value="${escapeHtml(source.kind)}"${source.enabled ? '' : ' disabled'}>${escapeHtml(label)}</option>`;
    }).join('');
    if (draft.sourceKind) refs.migracaoSourceKind.value = draft.sourceKind;
  }
  if (refs.migracaoStrategy && !refs.migracaoStrategy.options.length) {
    refs.migracaoStrategy.innerHTML = (helpers.APPLY_STRATEGIES || []).map((strategy) => {
      const label = tr(`dataMigration.strategy.${strategy}`, strategy);
      return `<option value="${escapeHtml(strategy)}">${escapeHtml(label)}</option>`;
    }).join('');
    refs.migracaoStrategy.value = 'upsert';
  }
  renderDataMigrationEntityFields();
  syncDataMigrationStrategyHint();
}

function renderDataMigrationEntityFields() {
  if (!refs.migracaoEntityFields) return;
  const descriptor = migracaoEntityDescriptor();
  if (!descriptor) { refs.migracaoEntityFields.textContent = ''; return; }
  const required = (descriptor.fields || []).filter((field) => field.required).map((field) => field.label);
  const optional = (descriptor.fields || []).filter((field) => !field.required).length;
  refs.migracaoEntityFields.textContent = tr(
    'dataMigration.entityFieldsHint',
    'Obrigatórios: {required}. Mais {optional} campos opcionais.',
  ).replace('{required}', required.join(', ') || '-').replace('{optional}', String(optional));
}

function syncDataMigrationStrategyHint() {
  if (!refs.migracaoStrategyHint || !refs.migracaoStrategy) return;
  const strategy = refs.migracaoStrategy.value || 'upsert';
  refs.migracaoStrategyHint.textContent = tr(`dataMigration.strategyHint.${strategy}`, '');
}

function renderDataMigrationSteps() {
  const draft = migracaoState();
  const helpers = dataMigrationHelpers();
  const steps = helpers.WIZARD_STEPS || [];
  if (refs.migracaoSteps) {
    Array.from(refs.migracaoSteps.querySelectorAll('[data-step]')).forEach((node) => {
      const index = steps.indexOf(node.dataset.step);
      const current = steps.indexOf(draft.step);
      node.classList.toggle('active', node.dataset.step === draft.step);
      node.classList.toggle('done', index >= 0 && current >= 0 && index < current);
    });
  }
  document.querySelectorAll('[data-step-panel]').forEach((node) => {
    node.hidden = node.dataset.stepPanel !== draft.step;
  });
  if (refs.migracaoBack) refs.migracaoBack.disabled = draft.step === steps[0];
  const isLast = draft.step === steps[steps.length - 1];
  if (refs.migracaoNext) refs.migracaoNext.hidden = isLast;
  if (refs.migracaoPreview) refs.migracaoPreview.hidden = !isLast;
  if (refs.migracaoNext) {
    refs.migracaoNext.disabled = draft.busy
      || !(helpers.canAdvance ? helpers.canAdvance(draft.step, migracaoDraftForRules()) : false);
  }
  if (refs.migracaoPreview) {
    refs.migracaoPreview.disabled = draft.busy
      || !(helpers.canAdvance ? helpers.canAdvance('mapeamento', migracaoDraftForRules()) : false);
  }
}

function migracaoDraftForRules() {
  const draft = migracaoState();
  const descriptor = migracaoEntityDescriptor();
  return {
    entity: draft.entity,
    sourceKind: draft.sourceKind,
    fileName: draft.fileName,
    totalRows: draft.totalRows,
    fields: descriptor ? descriptor.fields : [],
    mapping: draft.mapping,
  };
}

function renderDataMigrationReading() {
  const draft = migracaoState();
  if (refs.migracaoDetected) {
    const detected = draft.detected || {};
    const rows = [
      ['dataMigration.detEncoding', 'Codificação', detected.encoding],
      ['dataMigration.detDelimiter', 'Separador', detected.delimiter],
      ['dataMigration.detRows', 'Linhas', detected.total_rows],
      ['dataMigration.detColumns', 'Colunas', detected.column_count],
    ];
    refs.migracaoDetected.innerHTML = rows
      .filter(([, , value]) => value !== undefined && value !== null && value !== '')
      .map(([key, fallback, value]) => `<dt>${escapeHtml(tr(key, fallback))}</dt><dd>${escapeHtml(String(value))}</dd>`)
      .join('');
  }
  if (refs.migracaoSampleHead) {
    refs.migracaoSampleHead.innerHTML = `<tr>${(draft.columns || [])
      .map((column) => `<th scope="col">${escapeHtml(column)}</th>`).join('')}</tr>`;
  }
  if (refs.migracaoSampleBody) {
    refs.migracaoSampleBody.innerHTML = (draft.sample || []).slice(0, 10).map((row) => {
      const cells = (draft.columns || []).map((column) => `<td>${escapeHtml(String(row[column] ?? ''))}</td>`);
      return `<tr>${cells.join('')}</tr>`;
    }).join('') || globalThis.dsTableState({
      colspan: Math.max((draft.columns || []).length, 1),
      message: tr('dataMigration.sampleEmpty', 'Nenhuma linha lida.'),
    });
  }
}

function renderDataMigrationMapping() {
  const draft = migracaoState();
  const helpers = dataMigrationHelpers();
  const descriptor = migracaoEntityDescriptor();
  const fields = descriptor ? descriptor.fields || [] : [];
  const missing = helpers.missingRequiredFields ? helpers.missingRequiredFields(fields, draft.mapping) : [];
  if (refs.migracaoMappingSummary) {
    const summary = helpers.mappingSummary ? helpers.mappingSummary(draft.details, missing) : null;
    refs.migracaoMappingSummary.textContent = summary
      ? tr('dataMigration.mappingSummary', '{mapped} de {total} colunas reconhecidas · {review} para conferir')
        .replace('{mapped}', String(summary.mapped))
        .replace('{total}', String(summary.total))
        .replace('{review}', String(summary.review))
      : '';
  }
  if (refs.migracaoMappingSource) {
    refs.migracaoMappingSource.hidden = draft.mappingSource !== 'saved';
  }
  if (!refs.migracaoMappingTable) return;
  refs.migracaoMappingTable.innerHTML = (draft.columns || []).map((column) => {
    const detail = (draft.details || []).find((item) => item.source_column === column) || {};
    const selected = draft.mapping[column] || '';
    const options = helpers.availableTargets ? helpers.availableTargets(fields, draft.mapping, column) : fields;
    const optionHtml = [`<option value="">${escapeHtml(tr('dataMigration.mapIgnore', '— não importar —'))}</option>`]
      .concat(options.map((field) => {
        const flag = field.required ? ' *' : '';
        return `<option value="${escapeHtml(field.name)}"${field.name === selected ? ' selected' : ''}>`
          + `${escapeHtml(field.label + flag)}</option>`;
      })).join('');
    const level = helpers.confidenceLevel ? helpers.confidenceLevel(detail.confidence) : 'none';
    const badgeClass = level === 'exact' || level === 'high' ? 'badge-status-active'
      : (level === 'medium' ? 'badge-status-warning' : 'badge-role-user');
    const strategyLabel = detail.strategy
      ? tr(`dataMigration.mapStrategy.${detail.strategy}`, detail.strategy)
      : tr('dataMigration.mapStrategy.none', 'Sem correspondência');
    return `<tr><td>${escapeHtml(column)}</td>`
      + `<td><select data-migracao-map="${escapeHtml(column)}">${optionHtml}</select></td>`
      + `<td><span class="badge ${badgeClass}">${escapeHtml(strategyLabel)}</span></td></tr>`;
  }).join('') || globalThis.dsTableState({
    colspan: 3,
    message: tr('dataMigration.mappingEmpty', 'Nenhuma coluna lida.'),
  });
}

function renderDataMigrationPreview() {
  const draft = migracaoState();
  const helpers = dataMigrationHelpers();
  const preview = draft.preview;
  if (refs.migracaoPreviewCard) refs.migracaoPreviewCard.hidden = !preview;
  if (!preview) return;
  if (refs.migracaoPreviewCounters) {
    const counters = [
      ['dataMigration.pvTotal', 'Linhas lidas', preview.total_rows],
      ['dataMigration.pvValid', 'Válidas', preview.valid_rows],
      ['dataMigration.pvInvalid', 'Com problema', preview.invalid_rows],
      ['dataMigration.pvInsert', 'Serão criadas', preview.will_insert],
      ['dataMigration.pvUpdate', 'Serão atualizadas', preview.will_update],
    ];
    refs.migracaoPreviewCounters.innerHTML = counters.map(([key, fallback, value]) => (
      `<div class="migracao-counter"><strong>${escapeHtml(String(value ?? 0))}</strong>`
      + `<span>${escapeHtml(tr(key, fallback))}</span></div>`
    )).join('');
  }
  if (refs.migracaoPreviewDiagnostics) {
    const grouped = helpers.groupDiagnostics ? helpers.groupDiagnostics(preview.diagnostics) : [];
    refs.migracaoPreviewDiagnostics.innerHTML = grouped.map((bucket) => (
      `<tr><td>${escapeHtml(tr(`dataMigration.diag.${bucket.kind}`, bucket.kind))}</td>`
      + `<td>${bucket.count}</td><td>${escapeHtml(bucket.rows.join(', '))}</td></tr>`
    )).join('') || globalThis.dsTableState({
      colspan: 3,
      message: tr('dataMigration.diagEmpty', 'Nenhum problema encontrado.'),
    });
  }
  if (refs.migracaoApply) refs.migracaoApply.disabled = Boolean(preview.blocking) || draft.busy;
}

async function analyzeDataMigrationSource() {
  const draft = migracaoState();
  if (!draft.fileBase64) return;
  draft.busy = true;
  renderDataMigrationSteps();
  try {
    const data = await api('/api/data-migration/analyze', {
      method: 'POST',
      body: JSON.stringify({
        actor_user_id: state.user?.id,
        entity: draft.entity,
        source_kind: draft.sourceKind,
        source_name: draft.fileName,
        sheet: draft.sheet || null,
        content_base64: draft.fileBase64,
      }),
    });
    draft.columns = data.columns || [];
    draft.sample = data.sample || [];
    draft.detected = data.detected || {};
    draft.details = data.details || [];
    draft.mapping = { ...(data.mapping || {}) };
    draft.mappingSource = data.mapping_source || '';
    draft.totalRows = Number(data.detected?.total_rows || 0);
    draft.preview = null;
  } catch (error) {
    draft.totalRows = 0;
    showToast(migracaoErrorMessage(error), 'error');
  } finally {
    draft.busy = false;
  }
  renderDataMigrationReading();
  renderDataMigrationMapping();
  renderDataMigrationPreview();
  renderDataMigrationSteps();
}

async function runDataMigration(strategy) {
  const draft = migracaoState();
  draft.busy = true;
  renderDataMigrationSteps();
  try {
    const result = await api('/api/data-migration/run', {
      method: 'POST',
      body: JSON.stringify({
        actor_user_id: state.user?.id,
        entity: draft.entity,
        source_kind: draft.sourceKind,
        source_name: draft.fileName,
        sheet: draft.sheet || null,
        content_base64: draft.fileBase64,
        mapping: draft.mapping,
        strategy,
      }),
    });
    draft.preview = result.preview || null;
    if (result.applied) {
      const totals = result.totals || {};
      showToast(tr(
        'dataMigration.applied',
        'Importação #{job} concluída: {inserted} criados, {updated} atualizados, {skipped} ignorados, {failed} com erro.',
      ).replace('{job}', String(result.job_id))
        .replace('{inserted}', String(totals.inserted ?? 0))
        .replace('{updated}', String(totals.updated ?? 0))
        .replace('{skipped}', String(totals.skipped ?? 0))
        .replace('{failed}', String(totals.failed ?? 0)), 'success');
      await loadDataMigrationJobs();
      focusViewTab('migracao', 'historico');
    }
  } catch (error) {
    showToast(migracaoErrorMessage(error), 'error');
  } finally {
    draft.busy = false;
  }
  renderDataMigrationPreview();
  renderDataMigrationSteps();
}

async function loadDataMigrationJobs() {
  if (!hasPermission('data_migration:manage')) return;
  const draft = migracaoState();
  try {
    const data = await api(`/api/data-migration/jobs?${actorQuery()}`);
    draft.jobs = data.jobs || [];
  } catch (error) {
    draft.jobs = [];
    reportNonCriticalError('[migracao] falha ao carregar o histórico', error);
  }
  renderDataMigrationJobs();
}

function renderDataMigrationJobs() {
  if (!refs.migracaoJobsTable) return;
  const draft = migracaoState();
  const helpers = dataMigrationHelpers();
  refs.migracaoJobsTable.innerHTML = (draft.jobs || []).map((job) => {
    const counters = helpers.jobCounters ? helpers.jobCounters(job) : {};
    const summary = tr('dataMigration.jobSummary', '{inserted} criados · {updated} atualizados · {failed} com erro')
      .replace('{inserted}', String(counters.inserted ?? 0))
      .replace('{updated}', String(counters.updated ?? 0))
      .replace('{failed}', String(counters.failed ?? 0));
    const revertible = helpers.canRevert ? helpers.canRevert(job) : false;
    const action = revertible
      ? `<button type="button" class="ghost" data-migracao-revert="${escapeHtml(String(job.id))}">`
        + `${escapeHtml(tr('dataMigration.revert', 'Reverter Importação'))}</button>`
      : `<span class="muted">${escapeHtml(job.reverted_at
        ? tr('dataMigration.alreadyReverted', 'Já revertida')
        : tr('dataMigration.notRevertible', '-'))}</span>`;
    return `<tr><td>${escapeHtml(String(job.id))}</td>`
      + `<td>${escapeHtml(String(job.entity || ''))}</td>`
      + `<td>${escapeHtml(String(job.source_name || job.source_kind || ''))}</td>`
      + `<td>${escapeHtml(tr(`dataMigration.strategy.${job.strategy}`, String(job.strategy || '')))}</td>`
      + `<td>${escapeHtml(tr(`dataMigration.status.${job.status}`, String(job.status || '')))}</td>`
      + `<td>${escapeHtml(summary)}</td>`
      + `<td>${escapeHtml(String(job.actor_name || ''))}</td>`
      + `<td>${escapeHtml(formatDateTime(job.finished_at || job.created_at))}</td>`
      + `<td>${action}</td></tr>`;
  }).join('') || globalThis.dsTableState({
    colspan: 9,
    message: tr('dataMigration.historyEmpty', 'Nenhuma importação realizada ainda.'),
  });
}

async function revertDataMigrationJob(jobId) {
  if (!confirm(tr('dataMigration.revertConfirm', 'Reverter esta importação? Os registros criados serão removidos e os atualizados voltarão ao valor anterior.'))) return;
  try {
    const result = await api(`/api/data-migration/jobs/${encodeURIComponent(jobId)}/revert`, {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user?.id }),
    });
    showToast(tr(
      'dataMigration.reverted',
      'Importação revertida: {deleted} removidos, {restored} restaurados.',
    ).replace('{deleted}', String(result.deleted ?? 0)).replace('{restored}', String(result.restored ?? 0)), 'success');
  } catch (error) {
    showToast(migracaoErrorMessage(error), 'error');
  }
  await loadDataMigrationJobs();
}

function migracaoErrorMessage(error) {
  const raw = String(error?.message || error || '').trim();
  return raw || tr('dataMigration.genericError', 'Não foi possível concluir a operação de migração.');
}

function downloadDataMigrationReport() {
  const draft = migracaoState();
  const helpers = dataMigrationHelpers();
  const preview = draft.preview;
  if (!preview) return;
  const grouped = helpers.groupDiagnostics ? helpers.groupDiagnostics(preview.diagnostics) : [];
  const header = ['problema', 'ocorrencias', 'linhas'];
  const lines = [header.join(';')].concat(grouped.map((bucket) => [
    tr(`dataMigration.diag.${bucket.kind}`, bucket.kind),
    String(bucket.count),
    bucket.rows.join(' '),
  ].join(';')));
  const blob = new Blob([`﻿${lines.join('\n')}`], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `migracao-${draft.entity || 'preview'}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function readDataMigrationFile(file) {
  const draft = migracaoState();
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    const result = String(reader.result || '');
    draft.fileBase64 = result.includes(',') ? result.slice(result.indexOf(',') + 1) : result;
    draft.fileName = file.name || '';
    if (refs.migracaoFileName) refs.migracaoFileName.textContent = draft.fileName;
    renderDataMigrationSteps();
  };
  reader.onerror = () => {
    showToast(tr('dataMigration.fileError', 'Não foi possível ler o arquivo escolhido.'), 'error');
  };
  reader.readAsDataURL(file);
}

function resetDataMigrationWizard() {
  const draft = migracaoState();
  draft.step = 'entidade';
  draft.fileName = '';
  draft.fileBase64 = '';
  draft.sheet = '';
  draft.columns = [];
  draft.sample = [];
  draft.detected = {};
  draft.details = [];
  draft.mapping = {};
  draft.mappingSource = '';
  draft.totalRows = 0;
  draft.preview = null;
  if (refs.migracaoFile) refs.migracaoFile.value = '';
  if (refs.migracaoFileName) refs.migracaoFileName.textContent = '';
  if (refs.migracaoSheet) refs.migracaoSheet.value = '';
  renderDataMigrationReading();
  renderDataMigrationMapping();
  renderDataMigrationPreview();
  renderDataMigrationSteps();
}

function bindDataMigrationEvents() {
  const helpers = dataMigrationHelpers();
  const draft = migracaoState();

  // Tudo via bindAppListener: ele delega a safeOn, que registra o listener
  // no AbortController de escopo da aplicação. addEventListener direto aqui
  // vazaria o listener a cada re-render (regra verificada em
  // tests/test_phase52a_runtime_stability.py).
  bindAppListener(refs.migracaoCatalogFilter, 'input', renderDataMigrationCatalog);
  bindAppListener(refs.migracaoCatalogCards, 'click', (event) => {
    const button = event.target.closest('[data-migracao-card]');
    if (!button || button.disabled) return;
    draft.entity = button.dataset.migracaoCard;
    if (refs.migracaoEntity) refs.migracaoEntity.value = draft.entity;
    renderDataMigrationEntityFields();
    resetDataMigrationWizard();
    focusViewTab('migracao', 'assistente');
  });
  bindAppListener(refs.migracaoEntity, 'change', () => {
    draft.entity = refs.migracaoEntity.value || '';
    renderDataMigrationEntityFields();
    resetDataMigrationWizard();
  });
  bindAppListener(refs.migracaoSourceKind, 'change', () => {
    draft.sourceKind = refs.migracaoSourceKind.value || 'xlsx';
    if (refs.migracaoSheetWrap) {
      refs.migracaoSheetWrap.hidden = !['xlsx', 'xls', 'ods'].includes(draft.sourceKind);
    }
    renderDataMigrationSteps();
  });
  bindAppListener(refs.migracaoSheet, 'input', () => { draft.sheet = refs.migracaoSheet.value || ''; });

  bindAppListener(refs.migracaoDropzone, 'click', () => refs.migracaoFile?.click());
  bindAppListener(refs.migracaoDropzone, 'keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); refs.migracaoFile?.click(); }
  });
  ['dragenter', 'dragover'].forEach((name) => {
    bindAppListener(refs.migracaoDropzone, name, (event) => {
      event.preventDefault();
      refs.migracaoDropzone.classList.add('is-dragging');
    });
  });
  ['dragleave', 'drop'].forEach((name) => {
    bindAppListener(refs.migracaoDropzone, name, (event) => {
      event.preventDefault();
      refs.migracaoDropzone.classList.remove('is-dragging');
    });
  });
  bindAppListener(refs.migracaoDropzone, 'drop', (event) => {
    readDataMigrationFile(event.dataTransfer?.files?.[0]);
  });
  bindAppListener(refs.migracaoFile, 'change', () => readDataMigrationFile(refs.migracaoFile.files?.[0]));

  bindAppListener(refs.migracaoNext, 'click', () => {
    const steps = helpers.WIZARD_STEPS || [];
    const wasOrigin = draft.step === 'origem';
    draft.step = helpers.nextStep ? helpers.nextStep(draft.step) : steps[0];
    renderDataMigrationSteps();
    // Sair da etapa 2 é o gatilho da leitura automática: o usuário acabou de
    // escolher o arquivo e espera ver o que o sistema entendeu dele.
    if (wasOrigin) void analyzeDataMigrationSource();
  });
  bindAppListener(refs.migracaoBack, 'click', () => {
    draft.step = helpers.previousStep ? helpers.previousStep(draft.step) : draft.step;
    renderDataMigrationSteps();
  });
  bindAppListener(refs.migracaoRestart, 'click', resetDataMigrationWizard);
  bindAppListener(refs.migracaoPreview, 'click', () => void runDataMigration('dry_run'));
  bindAppListener(refs.migracaoApply, 'click', () => void runDataMigration(refs.migracaoStrategy?.value || 'upsert'));
  bindAppListener(refs.migracaoStrategy, 'change', syncDataMigrationStrategyHint);
  bindAppListener(refs.migracaoDownloadReport, 'click', downloadDataMigrationReport);

  bindAppListener(refs.migracaoMappingTable, 'change', (event) => {
    const select = event.target.closest('[data-migracao-map]');
    if (!select) return;
    const column = select.dataset.migracaoMap;
    if (select.value) draft.mapping[column] = select.value;
    else delete draft.mapping[column];
    // Redesenha porque um destino escolhido some das opções das demais
    // colunas — é a mesma unicidade que normalize_manual_mapping exige.
    renderDataMigrationMapping();
    renderDataMigrationSteps();
  });

  bindAppListener(refs.migracaoJobsTable, 'click', (event) => {
    const button = event.target.closest('[data-migracao-revert]');
    if (!button) return;
    void revertDataMigrationJob(button.dataset.migracaoRevert);
  });
}

// Vínculo jurídico da unidade.
//
// Diferente do colaborador, aqui não há imutabilidade: a unidade pode mudar de
// CNPJ responsável (reorganização societária, troca de operadora da JV). O que
// o backend não faz é *limpar* o vínculo — enviar vazio mantém o valor atual —
// então o seletor não oferece uma opção "nenhum" que não teria efeito.
function syncUnitLegalEntityOptions() {
  const field = document.getElementById('unit-legal-entity');
  const wrapper = document.getElementById('unit-legal-entity-field');
  if (!field || !wrapper) return;
  const companyId = document.getElementById('unit-company')?.value || state.user?.company_id || '';
  const entities = legalEntitiesForCompany(companyId);
  const previous = field.value;
  wrapper.hidden = entities.length === 0;
  field.innerHTML = `<option value="">${tr('legalEntity.selectOptional', 'Selecione o CNPJ')}</option>`
    + legalEntityOptionsHtml(entities);
  if (previous && entities.some((item) => String(item.id) === String(previous))) {
    field.value = previous;
  }
}

function syncReportLegalEntityOptions() {
  const field = document.getElementById('report-legal-entity');
  const wrapper = document.getElementById('report-legal-entity-field');
  if (!field || !wrapper) return;
  const companyId = document.getElementById('report-company')?.value || state.user?.company_id || '';
  const entities = legalEntitiesForCompany(companyId, { activeOnly: false });
  const previous = field.value;
  wrapper.hidden = entities.length === 0;
  field.innerHTML = `<option value="">${tr('employee.filterAll', 'Todos')}</option>`
    + legalEntityOptionsHtml(entities);
  if (previous && entities.some((item) => String(item.id) === String(previous))) {
    field.value = previous;
  }
}

function syncReportOptions() {
  syncReportLegalEntityOptions();
  const companyField = document.getElementById('report-company');
  const unitField = document.getElementById('report-unit');
  const employeeField = document.getElementById('report-employee');
  const unitHint = document.getElementById('report-unit-hint');
  if (!companyField || !unitField || !employeeField) return;
  const lockByOperationalProfile = isOperationalProfile();
  const operationalUnitId = String(state.user?.operational_unit_id || '').trim();
  if (lockByOperationalProfile && state.user?.company_id) {
    companyField.value = String(state.user.company_id);
  }
  const companyId = companyField.value || state.user?.company_id || '';
  let units = filterByUserCompany(state.units).filter((item) => !companyId || String(item.company_id) === String(companyId));
  if (lockByOperationalProfile && !operationalUnitId) units = [];
  if (lockByOperationalProfile && operationalUnitId) {
    units = units.filter((item) => String(item.id) === operationalUnitId);
  }
  const previousUnit = String(unitField.value || '');
  unitField.innerHTML = `${lockByOperationalProfile ? '' : `<option value="">${tr('employee.filterAllUnits', 'Todas')}</option>`}${units.map(formatUnitOption).join('')}`;
  if (!units.length) {
    unitField.innerHTML = '<option value="">Sem unidade operacional ativa</option>';
    unitField.value = '';
  } else if (lockByOperationalProfile) {
    unitField.value = String(units[0].id);
  } else if (previousUnit && units.some((item) => String(item.id) === previousUnit)) {
    unitField.value = previousUnit;
  }
  companyField.disabled = lockByOperationalProfile;
  unitField.disabled = lockByOperationalProfile;
  if (unitHint) unitHint.style.display = lockByOperationalProfile ? 'block' : 'none';
  const selectedUnitId = String(unitField.value || '');
  const employees = filterByUserCompany(state.employees).filter((item) => {
    if (companyId && String(item.company_id) !== String(companyId)) return false;
    if (!selectedUnitId) return true;
    const employeeUnitId = String(item.current_unit_id || item.unit_id || '');
    return employeeUnitId === selectedUnitId;
  });
  const previousEmployee = String(employeeField.value || '');
  employeeField.innerHTML = `<option value="">${tr('employee.allEmployees', 'Todos os colaboradores')}</option>` + employees.map((item) => `<option value="${item.id}">${item.employee_id_code} - ${item.name}</option>`).join('');
  if (previousEmployee && employees.some((item) => String(item.id) === previousEmployee)) {
    employeeField.value = previousEmployee;
  } else {
    employeeField.value = '';
  }
}

function formatEpiOptionLabel(item) {
  const sizeParts = [item.glove_size, item.size, item.uniform_size].filter((value) => value && value !== 'N/A');
  const manufacturer = item.manufacturer || '';
  const sizeLabel = sizeParts.length ? ` Tam: ${sizeParts.join(' / ')}` : '';
  const manufacturerLabel = manufacturer ? ` | Fab: ${manufacturer}` : '';
  return `${item.name}${manufacturerLabel}${sizeLabel} | ${item.unit_measure}`;
}

function syncStockOptions() {
  const companyField = document.getElementById('stock-company');
  const unitField = document.getElementById('stock-unit');
  const epiField = document.getElementById('stock-epi');
  const unitHint = document.getElementById('stock-unit-hint');
  if (!companyField || !unitField || !epiField) return;
  const operationalUnitId = state.user?.operational_unit_id;
  const lockByOperationalProfile = isOperationalProfile();
  if (lockByOperationalProfile && state.user?.company_id) {
    companyField.value = String(state.user.company_id);
  }
  const companyId = companyField.value || state.user?.company_id || '';
  const lockUnitByProfile = lockByOperationalProfile && operationalUnitId;
  let units = filterByUserCompany(state.units).filter((item) => !companyId || String(item.company_id) === String(companyId));
  if (lockByOperationalProfile && !operationalUnitId) units = [];
  if (lockUnitByProfile) units = units.filter((item) => String(item.id) === String(operationalUnitId));

  const previousUnit = String(unitField.value || '');
  unitField.innerHTML = units.map(formatUnitOption).join('');
  if (!units.length) {
    unitField.innerHTML = '<option value="">Sem unidade operacional ativa</option>';
    unitField.value = '';
  } else if (lockUnitByProfile) {
    unitField.value = String(units[0].id);
  } else if (previousUnit && units.some((item) => String(item.id) === previousUnit)) {
    unitField.value = previousUnit;
  } else if (!String(unitField.value || '').trim()) {
    unitField.value = String(units[0].id);
  }
  const stockScopedEpis = (state.stockEpis || []).filter((item) => {
    if (companyId && String(item.company_id) !== String(companyId)) return false;
    return true;
  });
  const epis = stockScopedEpis.length
    ? stockScopedEpis
    : filterByUserCompany(state.epis).filter((item) => !companyId || String(item.company_id) === String(companyId));
  unitField.disabled = lockByOperationalProfile;
  companyField.disabled = lockByOperationalProfile;
  if (unitHint) unitHint.style.display = lockByOperationalProfile ? 'block' : 'none';
  epiField.innerHTML = epis.map((item) => `<option value="${item.id}">${formatEpiOptionLabel(item)}</option>`).join('');
  if (epis.length && !epis.some((item) => String(item.id) === String(epiField.value))) epiField.value = String(epis[0].id);
  epiField.dispatchEvent(new Event('change', { bubbles: true }));
  syncStockSizeDefaults();
  syncSelectedEpiMinimumStockField();
  refreshStockMovementItemsFromLocal();
  scheduleStockMovementSearchLoad();
  renderStockEpiSearchResults();
  setupStockLabelCustomFields();
}

function syncStockSizeDefaults() {
  const form = document.getElementById('stock-form');
  const epiField = document.getElementById('stock-epi');
  if (!form || !epiField) return;
  const selectedEpi = state.epis.find((item) => String(item.id) === String(epiField.value || ''));
  if (!selectedEpi) return;
  if (form.elements.glove_size) form.elements.glove_size.value = selectedEpi.glove_size || 'N/A';
  if (form.elements.size) form.elements.size.value = selectedEpi.size || 'N/A';
  if (form.elements.uniform_size) form.elements.uniform_size.value = selectedEpi.uniform_size || 'N/A';
}

function setupStockLabelCustomFields() {
  const printerSelect = document.getElementById('stock-label-printer');
  const printerCustom = document.getElementById('stock-label-printer-custom');
  const formatSelect = document.getElementById('stock-label-format');
  const formatCustom = document.getElementById('stock-label-format-custom');
  if (!printerSelect || !printerCustom || !formatSelect || !formatCustom) {
    return false;
  }
  const bindOnce = (element, key, listener) => {
    if (element.dataset[key] === '1') return;
    element.dataset[key] = '1';
    safeOn(element, 'change', listener);
  };
  const syncCustomField = (selectField, customField, triggerValue) => {
    const shouldShow = String(selectField.value || '').trim() === triggerValue;
    customField.style.display = shouldShow ? 'block' : 'none';
    customField.required = shouldShow;
    if (!shouldShow) customField.value = '';
  };
  const syncPrinter = () => syncCustomField(printerSelect, printerCustom, '__outro__');
  const syncFormat = () => syncCustomField(formatSelect, formatCustom, '__personalizado__');
  bindOnce(printerSelect, 'customFieldBound', syncPrinter);
  bindOnce(formatSelect, 'customFieldBound', syncFormat);
  syncPrinter();
  syncFormat();
  return true;
}

function ensureStockLabelCustomFieldBinding() {
  if (setupStockLabelCustomFields()) return;
  if (globalThis.__EPI_STOCK_CUSTOM_OBSERVER__) return;
  const observer = new MutationObserver(() => {
    if (setupStockLabelCustomFields()) {
      observer.disconnect();
      globalThis.__EPI_STOCK_CUSTOM_OBSERVER__ = null;
    }
  });
  observer.observe(document.body || document.documentElement, { childList: true, subtree: true });
  globalThis.__EPI_STOCK_CUSTOM_OBSERVER__ = observer;
}

function resolveItemSize(formValuesPayload = {}) {
  const gloveSize = normalizeStockSizeValue(formValuesPayload.glove_size);
  const size = normalizeStockSizeValue(formValuesPayload.size);
  const uniformSize = normalizeStockSizeValue(formValuesPayload.uniform_size);
  const selectedSize = gloveSize || size || uniformSize || null;
  return {
    selectedSize,
    glove_size: gloveSize || 'N/A',
    size: selectedSize || 'N/A',
    uniform_size: uniformSize || 'N/A'
  };
}

function renderDeliveryQrSession() {
  const sessionViews = [
    {
      summary: document.getElementById('delivery-qr-session-summary'),
      count: document.getElementById('delivery-qr-session-count'),
      list: document.getElementById('delivery-qr-session-list')
    },
    {
      summary: document.getElementById('delivery-qr-session-summary-inline'),
      count: document.getElementById('delivery-qr-session-count-inline'),
      list: document.getElementById('delivery-qr-session-list-inline')
    }
  ].filter((entry) => entry.summary && entry.list);
  const sessionEmployeeId = normalizeSessionEmployeeId(qrScannerState.sessionEmployeeId);
  const employee = state.employees.find((item) => normalizeSessionEmployeeId(item.id) === sessionEmployeeId);
  sessionViews.forEach(({ count }) => {
    if (count) count.textContent = String(qrScannerState.scanSession.length || 0);
  });
  if (!sessionViews.length) return;
  if (!qrScannerState.scanSession.length) {
    sessionViews.forEach(({ summary, list }) => {
      list.innerHTML = '<li class="hint">Nenhum QR confirmado nesta sessão.</li>';
      summary.style.display = 'none';
    });
    return;
  }
  sessionViews.forEach(({ summary }) => {
    summary.style.display = 'grid';
  });
  const employeeLine = employee
    ? `<li class="hint"><strong>Colaborador fixado:</strong> ${escapeHtml(employee.employee_id_code || '-') } - ${escapeHtml(employee.name || '-')}</li>`
    : '';
  const html = qrScannerState.scanSession
    .map((item, index) => {
      const duplicateCount = Number(item.duplicate_count || 0);
      const duplicateSuffix = duplicateCount > 0 ? ` <small class="hint">(duplicidades: ${duplicateCount})</small>` : '';
      const statusLabel = item.signed ? tr('delivery.signed', 'Assinado') : tr('delivery.pending', 'Pendente');
      return `<li><strong>#${index + 1}</strong> ${escapeHtml(item.qr_code_value || item.raw || '')} — ${escapeHtml(item.epi_name || 'EPI')} — ${tr('delivery.sizeShort', 'Tam.')}: ${escapeHtml(formatItemSizeDisplay(item))} <small class="hint">(${statusLabel})</small>${duplicateSuffix}</li>`;
    })
    .join('') + employeeLine;
  sessionViews.forEach(({ list }) => {
    list.innerHTML = html;
  });
}

function normalizeSessionEmployeeId(value) {
  const normalized = String(value ?? '').trim();
  if (!normalized) return '';
  if (/^\d+$/.test(normalized)) return String(Number(normalized));
  return normalized;
}

function getCurrentDeliveryEmployeeId() {
  return normalizeSessionEmployeeId(document.getElementById('delivery-employee')?.value || '');
}

function syncDeliveryQrSessionOwner(options = {}) {
  const selectedEmployeeId = getCurrentDeliveryEmployeeId();
  const sessionEmployeeId = normalizeSessionEmployeeId(qrScannerState.sessionEmployeeId);
  if (!sessionEmployeeId || sessionEmployeeId === selectedEmployeeId) return false;
  if (!qrScannerState.scanSession.length) {
    qrScannerState.sessionEmployeeId = '';
    return false;
  }
  const shouldWarn = options.warn !== false;
  resetDeliveryQrSession();
  clearDeliveryStockItemSelection();
  if (shouldWarn) {
    setDeliveryQrStatus('Colaborador alterado: sessão de leitura anterior foi encerrada para evitar mistura de entregas.', true);
  }
  return true;
}

function resetDeliveryQrSession() {
  qrScannerState.sessionEmployeeId = '';
  qrScannerState.scanSession = [];
  qrScannerState.scanSessionIndex = new Set();
  qrScannerState.lastAcceptedAtByText = new Map();
  qrScannerState.duplicateCountByText = new Map();
  renderDeliveryQrSession();
}

function removeStockQrFromSession(qrValue) {
  const key = String(qrValue || '').trim().toLowerCase();
  if (!key) return;
  qrScannerState.scanSession = qrScannerState.scanSession.filter((item) => String(item.qr_code_value || '').trim().toLowerCase() !== key);
  qrScannerState.scanSessionIndex.delete(key);
  qrScannerState.duplicateCountByText.delete(key);
  if (!qrScannerState.scanSession.length) qrScannerState.sessionEmployeeId = '';
  renderDeliveryQrSession();
}

function addStockQrToSession(stockItem) {
  const currentEmployeeId = getCurrentDeliveryEmployeeId();
  if (!currentEmployeeId) return { added: false, reason: 'missing_employee' };
  const sessionEmployeeId = normalizeSessionEmployeeId(qrScannerState.sessionEmployeeId);
  if (sessionEmployeeId && sessionEmployeeId !== currentEmployeeId) {
    return { added: false, reason: 'employee_changed' };
  }
  const qrValue = String(stockItem?.qr_code_value || '').trim();
  if (!qrValue) return { added: false, reason: 'invalid' };
  const key = qrValue.toLowerCase();
  const now = Date.now();
  const lastAt = Number(qrScannerState.lastAcceptedAtByText.get(key) || 0);
  qrScannerState.lastAcceptedAtByText.set(key, now);
  if (qrScannerState.scanSessionIndex.has(key)) {
    const duplicates = Number(qrScannerState.duplicateCountByText.get(key) || 0) + 1;
    qrScannerState.duplicateCountByText.set(key, duplicates);
    const current = qrScannerState.scanSession.find((item) => String(item.qr_code_value || '').trim().toLowerCase() === key);
    if (current) current.duplicate_count = duplicates;
    renderDeliveryQrSession();
    return { added: false, reason: 'duplicate' };
  }
  if (now - lastAt < 900) return { added: false, reason: 'throttled' };
  qrScannerState.sessionEmployeeId = currentEmployeeId;
  qrScannerState.scanSessionIndex.add(key);
  qrScannerState.scanSession.push({ ...stockItem, session_employee_id: currentEmployeeId, duplicate_count: 0, pending_registration: true });
  renderDeliveryQrSession();
  return { added: true, reason: 'ok' };
}

function applyStockItemToDeliveryForm(stockItem) {
  if (!stockItem) return;
  const preservedEmployeeId = String(document.getElementById('delivery-employee')?.value || '').trim();
  const companyField = document.getElementById('delivery-company');
  const epiField = document.getElementById('delivery-epi');
  if (companyField) companyField.value = String(stockItem.company_id || '');
  syncDeliveryOptions();
  if (preservedEmployeeId) {
    const employeeField = document.getElementById('delivery-employee');
    if (employeeField) {
      employeeField.value = preservedEmployeeId;
      emitInputChangeEvents(employeeField);
    }
  }
  if (epiField) epiField.value = String(stockItem.epi_id || '');
  if (epiField) epiField.dispatchEvent(new Event('change', { bubbles: true }));
  const stockItemIdField = document.getElementById('delivery-stock-item-id');
  const stockCodeField = document.getElementById('delivery-stock-item-code');
  const stockQrHiddenField = document.getElementById('delivery-stock-qr-code');
  if (stockItemIdField) stockItemIdField.value = String(stockItem.id || '');
  if (stockCodeField) stockCodeField.value = String(stockItem.qr_code_value || '');
  if (stockQrHiddenField) stockQrHiddenField.value = String(stockItem.qr_code_value || '');
  refreshDeliveryContext();
}

function applyStockItemToDeliverySelection(stockItem, options = {}) {
  if (!stockItem) return false;
  const epiField = document.getElementById('delivery-epi');
  if (!epiField) return false;
  const targetValue = String(stockItem.epi_id || '').trim();
  if (!targetValue) return false;
  if (!Array.from(epiField.options || []).some((option) => String(option.value || '').trim() === targetValue)) {
    const fallbackLabel = [
      String(stockItem.epi_name || 'EPI'),
      String(stockItem.unit_measure || 'unidade')
    ].filter(Boolean).join(' - ');
    const fallbackOption = document.createElement('option');
    fallbackOption.value = targetValue;
    fallbackOption.textContent = fallbackLabel || `EPI ${targetValue}`;
    epiField.appendChild(fallbackOption);
    return false;
  }
  epiField.value = targetValue;
  epiField.dispatchEvent(new Event('change', { bubbles: true }));
  const stockItemIdField = document.getElementById('delivery-stock-item-id');
  const stockCodeField = document.getElementById('delivery-stock-item-code');
  const stockQrHiddenField = document.getElementById('delivery-stock-qr-code');
  if (stockItemIdField) stockItemIdField.value = String(stockItem.id || '');
  if (stockCodeField) stockCodeField.value = String(stockItem.qr_code_value || '');
  if (stockQrHiddenField) stockQrHiddenField.value = String(stockItem.qr_code_value || '');
  markDeliveryCodeValidation(stockItem, options.source || '');
  return true;
}

async function handleDeliveryQrScan(options = {}) {
  const input = document.getElementById('delivery-qr-scan');
  const value = String(options.sourceValue || input?.value || '').trim();
  if (!value) return false;
  const companyField = document.getElementById('delivery-company');
  const unitField = document.getElementById('delivery-unit-filter');
  const companyId = companyField?.value || state.user?.company_id || '';
  const unitId = unitField?.value || state.user?.operational_unit_id || '';
  if (!companyId || !unitId) {
    setDeliveryQrStatus('Selecione empresa/unidade antes de ler o QR.', true);
    return false;
  }
  let stockItem = null;
  const interpreted = resolveStockQrPayload(value);
  const normalizedInputCode = String(interpreted?.qr_code || value).trim().toLowerCase();
  try {
    const params = new URLSearchParams({
      actor_user_id: String(state.user?.id || ''),
      company_id: String(companyId),
      unit_id: String(unitId),
      qr_code: interpreted?.qr_code || value
    });
    if (interpreted?.stock_item_id && ['json', 'simple'].includes(String(interpreted?.format || '').toLowerCase())) {
      params.set('stock_item_id', String(interpreted.stock_item_id));
    }
    const payload = await api(`/api/stock/lookup-qr?${params.toString()}`);
    stockItem = payload?.stock_item || null;
    if (options.debugManual === true) {
      console.info('[qr-manual] resposta lookup', {
        requested_qr_code: String(interpreted?.qr_code || value).trim(),
        requested_stock_item_id: params.get('stock_item_id') || '',
        returned_qr_code: String(stockItem?.qr_code_value || '').trim(),
        returned_stock_item_id: String(stockItem?.id || '')
      });
    }
  } catch (error) {
    console.warn('[qr][scan] rejeitado na validação', { raw: value, interpreted, reason: error?.message || 'erro_desconhecido' });
    const loweredMessage = String(error?.message || '').toLowerCase();
    if (loweredMessage.includes('não encontrado')) {
      setDeliveryQrStatus('Código não encontrado no estoque.', true);
    } else {
      setDeliveryQrStatus(`QR Não validado no estoque: ${error.message}`, true);
    }
    return false;
  }
  if (!stockItem) {
    console.warn('[qr][scan] rejeitado: não encontrado', { raw: value, interpreted });
    setDeliveryQrStatus('Código não encontrado no estoque.', true);
    return false;
  }
  const returnedCode = String(stockItem?.qr_code_value || '').trim().toLowerCase();
  const shouldEnforceStrictCodeMatch = Boolean(options.strictCodeMatch)
    || String(interpreted?.format || '').toLowerCase() === 'stock-label'
    || /^epi-item-/i.test(value);
  if (shouldEnforceStrictCodeMatch && normalizedInputCode && returnedCode !== normalizedInputCode) {
    console.warn('[qr-manual] divergência entre código digitado e código retornado', {
      input_code: value,
      normalized_input: normalizedInputCode,
      returned_code: returnedCode,
      returned_stock_item_id: stockItem?.id
    });
    setDeliveryQrStatus('Código não encontrado no estoque.', true);
    return false;
  }
  if (input) input.value = value;
  if (options.applyToForm !== false) applyStockItemToDeliveryForm(stockItem);
  setDeliveryQrStatus(`Unidade validada: ${stockItem.epi_name || stockItem.qr_code_value || stockItem.id}`);
  return stockItem;
}

async function queueDeliveryQrForCurrentSession(options = {}) {
  const input = document.getElementById('delivery-qr-scan');
  const rawInputValue = String(options.sourceValue || input?.value || '').trim();
  if (!rawInputValue) {
    showToast('Digite ou leia um código antes de validar.', 'error');
    return false;
  }
  const normalizedInputValue = String(rawInputValue).trim();
  if (options.trigger === 'manual_button') {
    console.info('[qr-manual] validar clicado', {
      rawInputValue,
      normalizedInputValue,
      previousSessionValue: String(qrScannerState.scanSession[qrScannerState.scanSession.length - 1]?.qr_code_value || ''),
      stateCurrentCode: String(document.getElementById('delivery-stock-item-code')?.value || ''),
      scannedItems: (qrScannerState.scanSession || []).map((item) => String(item?.qr_code_value || ''))
    });
  }
  const stockItem = await handleDeliveryQrScan({
    ...options,
    sourceValue: normalizedInputValue,
    applyToForm: false,
    debugManual: options.trigger === 'manual_button',
    strictCodeMatch: options.trigger === 'manual_button'
  });
  if (!stockItem) return false;
  const addResult = addStockQrToSession(stockItem);
  if (!addResult.added) {
    if (addResult.reason === 'missing_employee') {
      setDeliveryQrStatus('Selecione o colaborador antes de validar o QR.', true);
      return false;
    }
    if (addResult.reason === 'employee_changed') {
      setDeliveryQrStatus('Colaborador alterado durante a sessão. Limpe a lista e inicie nova leitura.', true);
      return false;
    }
    if (addResult.reason === 'duplicate') {
      setDeliveryQrStatus('Este código já está na lista/conferência.', true);
      return false;
    }
    return false;
  }
  applyQrFeedbackOnce(`estoque:${stockItem.qr_code_value}`);
  const epiSelected = applyStockItemToDeliverySelection(stockItem, { source: 'manual_validation' });
  if (!epiSelected) {
    removeStockQrFromSession(stockItem.qr_code_value);
    setDeliveryQrStatus(`QR validado (${stockItem.qr_code_value}), mas o EPI não está disponível no seletor atual.`, true);
    return false;
  }
  refreshDeliveryContext();
  setDeliveryQrStatus(`QR validado e EPI selecionado automaticamente (${qrScannerState.scanSession.length}): ${stockItem.qr_code_value}`);
  setDeliveryQrStatus(`QR validado e pendente de registro (${qrScannerState.scanSession.length}): ${stockItem.qr_code_value}`);
  return true;
}

async function applySelectedAvailableDeliveryQr() {
  const selectField = refs.deliveryAvailableQr;
  if (!selectField) return false;
  const selectedStockItemId = String(selectField.value || '').trim();
  if (!selectedStockItemId) {
    setDeliveryQrStatus('Selecione um QR disponível antes de aplicar.', true);
    return false;
  }
  const selectedOption = selectField.options?.[selectField.selectedIndex] || null;
  const selectedCode = String(selectedOption?.dataset?.qrCode || '').trim();
  if (!selectedCode) {
    setDeliveryQrStatus('QR selecionado inválido. Atualize a lista e tente novamente.', true);
    return false;
  }
  const stockItem = await handleDeliveryQrScan({
    sourceValue: selectedCode,
    applyToForm: false
  });
  if (!stockItem) return false;
  if (String(stockItem.id || '') !== selectedStockItemId) {
    setDeliveryQrStatus('Divergência entre QR escolhido e item validado. Selecione novamente o código físico.', true);
    return false;
  }
  const addResult = addStockQrToSession(stockItem);
  if (!addResult.added && addResult.reason === 'duplicate') {
    setDeliveryQrStatus('Este QR já foi adicionado na sessão.', true);
    return false;
  }
  if (!addResult.added && addResult.reason === 'missing_employee') {
    setDeliveryQrStatus('Selecione o colaborador antes de escolher o QR.', true);
    return false;
  }
  applyStockItemToDeliverySelection(stockItem, { source: 'stock_selection' });
  const qrInput = document.getElementById('delivery-qr-scan');
  if (qrInput) qrInput.value = stockItem.qr_code_value || '';
  refreshDeliveryContext();
  setDeliveryQrStatus(`QR escolhido e validado automaticamente: ${stockItem.qr_code_value}`);
  return true;
}

async function handleDeliveryManualValidationRequest() {
  const rawCode = String(document.getElementById('delivery-qr-scan')?.value || '').trim();
  if (isCodeAutoValidatedBySelection(rawCode)) {
    setDeliveryQrStatus('Este código já foi validado automaticamente via seleção do sistema.');
    return false;
  }
  return queueDeliveryQrForCurrentSession({ trigger: 'manual_button' });
}

function setupDrawingCanvas(canvas, clearButton) {
  if (!canvas) return { getData: () => '', clear: () => {}, hasStroke: () => false };
  if (canvas.__signaturePadController) return canvas.__signaturePadController;
  const ctx = canvas.getContext('2d');
  let drawing = false;
  let hasStroke = false;
  const drawStart = (x, y) => {
    drawing = true;
    ctx?.beginPath();
    ctx?.moveTo(x, y);
  };
  const drawMove = (x, y) => {
    if (!drawing || !ctx) return;
    ctx.lineTo(x, y);
    ctx.lineWidth = 2;
    ctx.strokeStyle = '#333';
    ctx.stroke();
    hasStroke = true;
  };
  const stopDraw = () => { drawing = false; };
  canvas.addEventListener('mousedown', (event) => drawStart(event.offsetX, event.offsetY));
  canvas.addEventListener('mousemove', (event) => drawMove(event.offsetX, event.offsetY));
  canvas.addEventListener('mouseup', stopDraw);
  canvas.addEventListener('mouseleave', stopDraw);
  canvas.addEventListener('touchstart', (event) => {
    const rect = canvas.getBoundingClientRect();
    const touch = event.touches[0];
    drawStart(touch.clientX - rect.left, touch.clientY - rect.top);
    event.preventDefault();
  }, { passive: false });
  canvas.addEventListener('touchmove', (event) => {
    const rect = canvas.getBoundingClientRect();
    const touch = event.touches[0];
    drawMove(touch.clientX - rect.left, touch.clientY - rect.top);
    event.preventDefault();
  }, { passive: false });
  canvas.addEventListener('touchend', stopDraw);
  const clear = () => {
    ctx?.clearRect(0, 0, canvas.width, canvas.height);
    hasStroke = false;
  };
  safeOn(clearButton, 'click', clear);
  const controller = {
    getData: () => (hasStroke ? canvas.toDataURL('image/png') : ''),
    clear,
    hasStroke: () => hasStroke
  };
  canvas.__signaturePadController = controller;
  return controller;
}

let signaturePadController = null;
const modalFocusState = new WeakMap();
const modalKeydownState = new WeakMap();

function getFocusableElements(container) {
  if (!container) return [];
  return Array.from(container.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'))
    .filter((el) => !el.disabled && !el.hidden && el.getAttribute('aria-hidden') !== 'true');
}

function openModal(modalElement) {
  if (!modalElement) return;
  modalFocusState.set(modalElement, document.activeElement instanceof HTMLElement ? document.activeElement : null);
  modalElement.hidden = false;
  if ('inert' in modalElement) modalElement.inert = false;
  modalElement.classList.add('is-open');
  const focusables = getFocusableElements(modalElement);
  (focusables[0] || modalElement).focus?.();
}

function closeModal(modalElement) {
  if (!modalElement) return;
  if (modalElement.contains(document.activeElement)) document.activeElement?.blur?.();
  modalElement.hidden = true;
  if ('inert' in modalElement) modalElement.inert = true;
  modalElement.classList.remove('is-open');
  const previousFocus = modalFocusState.get(modalElement);
  if (previousFocus?.isConnected) previousFocus.focus();
}

function bindModalKeyboard(modalElement, onClose) {
  if (!modalElement || modalKeydownState.has(modalElement)) return;
  const keydownHandler = (event) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      onClose?.();
      return;
    }
    if (event.key !== 'Tab') return;
    const focusables = getFocusableElements(modalElement);
    if (!focusables.length) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };
  safeOn(modalElement, 'keydown', keydownHandler);
  modalKeydownState.set(modalElement, keydownHandler);
}

function signatureModalRefs() {
  return {
    modal: document.getElementById('signature-modal'),
    name: document.getElementById('signature-modal-name'),
    at: document.getElementById('signature-modal-at'),
    canvas: document.getElementById('signature-modal-canvas'),
    comment: document.getElementById('signature-modal-comment'),
    clear: document.getElementById('signature-modal-clear'),
    cancel: document.getElementById('signature-modal-cancel'),
    confirm: document.getElementById('signature-modal-confirm')
  };
}
function signatureNowLabel() {
  return new Date().toLocaleString('pt-BR');
}

function ensureSignatureModalDom() {
  if (document.getElementById('signature-modal')) return;
  const modal = document.createElement('div');
  modal.id = 'signature-modal';
  modal.className = 'signature-modal';
  modal.hidden = true;
  modal.inert = true;
  modal.tabIndex = -1;
  modal.innerHTML = [
    '<div class="signature-modal__dialog" role="dialog" aria-modal="true" aria-labelledby="signature-modal-title">',
    `<header class="signature-modal__header"><h3 id="signature-modal-title">${tr('delivery.digitalSignature', 'Assinatura digital')}</h3></header>`,
    '<div class="signature-modal__body">',
    `<label>${tr('portal.signerName', 'Nome do assinante')}<input id="signature-modal-name" type="text" readonly></label>`,
    `<label>${tr('signature.dateTime', 'Data e hora')}<input id="signature-modal-at" type="text" readonly></label>`,
    `<p id="signature-modal-canvas-label" class="hint"><strong>${tr('delivery.digitalSignature', 'Assinatura digital')}</strong></p>`,
    '<canvas id="signature-modal-canvas" width="560" height="200" aria-labelledby="signature-modal-canvas-label"></canvas>',
    `<div class="action-group"><button id="signature-modal-clear" class="ghost" type="button">${tr('signature.clear', 'Limpar assinatura')}</button></div>`,
    `<label>${tr('delivery.notes', 'Observações')}<textarea id="signature-modal-comment" rows="3" placeholder="${tr('portal.signatureCommentPlaceholder', 'Caso não reconheça algum EPI, informe neste campo')}"></textarea></label>`,
    '</div>',
    '<footer class="signature-modal__footer">',
    `<button id="signature-modal-cancel" class="ghost" type="button">${tr('cancel', 'Cancelar')}</button>`,
    '<button id="signature-modal-confirm" class="primary" type="button">OK</button>',
    '</footer>',
    '</div>'
  ].join('');
  document.body.appendChild(modal);
  setupSignatureModal();
}

function closeSignatureModal() {
  const modalRefs = signatureModalRefs();
  closeModal(modalRefs.modal);
  state.signatureDraft = null;
}

function openSignatureModal({ signerName = '', comment = '', onConfirm, parentModal = null, context = null, onAfterConfirm = null }) {
  ensureSignatureModalDom();
  const modalRefs = signatureModalRefs();
  if (!modalRefs.modal || !modalRefs.canvas) return;
  signaturePadController = setupDrawingCanvas(modalRefs.canvas, modalRefs.clear);
  signaturePadController.clear();
  const signedAt = signatureNowLabel();
  if (modalRefs.name) modalRefs.name.value = signerName;
  if (modalRefs.at) modalRefs.at.value = signedAt;
  if (modalRefs.comment) modalRefs.comment.value = comment;
  // P0-3 — exige confirmação de identidade a cada abertura (NR-6).
  const identityCheck = document.getElementById('signature-modal-identity');
  if (identityCheck) identityCheck.checked = false;
  const identityErr = document.getElementById('signature-modal-identity-error');
  if (identityErr) identityErr.hidden = true;
  openModal(modalRefs.modal);
  state.signatureDraft = { onConfirm, parentModal, context, onAfterConfirm };
}

function setupSignatureModal() {
  const modalRefs = signatureModalRefs();
  bindModalKeyboard(modalRefs.modal, closeSignatureModal);
  safeOn(modalRefs.cancel, 'click', closeSignatureModal);
  safeOn(modalRefs.modal, 'click', (event) => {
    if (event.target === modalRefs.modal) closeSignatureModal();
  });
  safeOn(modalRefs.confirm, 'click', () => {
    if (!state.signatureDraft?.onConfirm) return closeSignatureModal();
    const signatureData = signaturePadController?.getData?.() || '';
    if (!signatureData) {
      alert(tr('portal.signatureRequiredDraw', 'Assinatura digital obrigatória. Desenhe no campo de assinatura.'));
      return;
    }
    // P0-3 — bloqueia o envio sem a declaração de identidade (validade legal).
    const identityCheck = document.getElementById('signature-modal-identity');
    if (identityCheck && !identityCheck.checked) {
      const identityErr = document.getElementById('signature-modal-identity-error');
      if (identityErr) {
        identityErr.hidden = false;
        identityErr.textContent = tr('signature.identityRequired', 'Confirme a declaração de identidade para assinar.');
      }
      identityCheck.focus();
      return;
    }
    const signaturePayload = {
      signature_name: String(modalRefs.name?.value || '').trim() || 'Assinatura digital',
      signature_data: signatureData,
      signature_at: new Date().toISOString(),
      signature_comment: String(modalRefs.comment?.value || '').trim()
    };
    state.signatureDraft.onConfirm(signaturePayload);
    state.signatureDraft.onAfterConfirm?.(signaturePayload, state.signatureDraft?.context || null, state.signatureDraft?.parentModal || null);
    closeSignatureModal();
  });
}

function applyDeliverySignature(payload) {
  if (refs.deliverySignatureData) refs.deliverySignatureData.value = String(payload.signature_data || '');
  if (refs.deliverySignatureName) refs.deliverySignatureName.value = String(payload.signature_name || tr('delivery.digitalSignature', 'Assinatura digital'));
  if (refs.deliverySignatureAt) refs.deliverySignatureAt.value = String(payload.signature_at || '');
  if (refs.deliverySignatureComment) refs.deliverySignatureComment.value = String(payload.signature_comment || '');
  if (refs.deliverySignatureStatus) refs.deliverySignatureStatus.textContent = tr('delivery.signedByAt', 'Assinado por {name} em {date}.').replace('{name}', payload.signature_name || tr('delivery.digitalSignature', 'Assinatura digital')).replace('{date}', signatureNowLabel());
  qrScannerState.scanSession = (qrScannerState.scanSession || []).map((item) => ({ ...item, signed: true }));
  renderDeliveryQrSession();
}

function selectedDeliveryEmployee() {
  const employeeId = String(document.getElementById('delivery-employee')?.value || '').trim();
  return state.employees.find((item) => String(item.id) === employeeId) || null;
}

function resetDeliverySignatureDraft() {
  if (refs.deliverySignatureData) refs.deliverySignatureData.value = '';
  if (refs.deliverySignatureName) refs.deliverySignatureName.value = '';
  if (refs.deliverySignatureAt) refs.deliverySignatureAt.value = '';
  if (refs.deliverySignatureComment) refs.deliverySignatureComment.value = '';
  if (refs.deliverySignatureStatus) refs.deliverySignatureStatus.textContent = tr('delivery.signaturePendingFicha', 'Assinatura pendente (pode assinar agora ou depois no período da ficha).');
}

function setupDeliverySignatureCanvas() {
  safeOn(refs.deliverySignatureOpen, 'click', () => {
    const employee = selectedDeliveryEmployee();
    openSignatureModal({
      signerName: employee?.name || state.user?.full_name || tr('delivery.digitalSignature', 'Assinatura digital'),
      comment: refs.deliverySignatureComment?.value || '',
      onConfirm: applyDeliverySignature
    });
  });
}

async function applyEmployeeQrLookup() {
  const qrValue = String(document.getElementById('delivery-employee-qr-scan')?.value || '').trim();
  if (!qrValue) return;
  try {
    const payload = await api('/api/employee-lookup', {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user.id, employee_qr_code: qrValue })
    });
    const employee = payload.employee;
    if (!employee) return;
    document.getElementById('delivery-company').value = String(employee.company_id);
    syncDeliveryOptions();
    document.getElementById('delivery-employee').value = String(employee.id);
    refreshDeliveryContext({ syncUnit: true });
  } catch (error) {
    alert(error.message);
  }
}

// ── Acesso do colaborador pela Entrega (QR lookup + link + envio) ─────────────
// Reativado (auditoria F-05): a UI vive em static/views/entregas.html e reusa os
// endpoints existentes /api/employee-portal-link e /api/employee-contact-launch.
// Todos os leitores de DOM são protegidos por optional chaining (null-safe).
let _deliveryEmployeeLinkExpiresAt = '';

function setDeliveryEmployeeAccessStatus(kind, message) {
  const status = document.getElementById('delivery-employee-access-status');
  if (!status) return;
  status.textContent = String(message || '');
  status.dataset.state = String(kind || 'info');
}

function _deliveryEmployeeAccessButtons() {
  return ['delivery-employee-link-generate', 'delivery-employee-link-qr', 'delivery-employee-link-copy',
    'delivery-employee-link-open', 'delivery-employee-link-whatsapp', 'delivery-employee-link-email']
    .map((id) => document.getElementById(id)).filter(Boolean);
}

function _setDeliveryEmployeeAccessBusy(busy) {
  _deliveryEmployeeAccessButtons().forEach((btn) => { btn.disabled = Boolean(busy); });
}

function _deliveryEmployeeLinkIsExpired() {
  if (!_deliveryEmployeeLinkExpiresAt) return false;
  const expiry = new Date(_deliveryEmployeeLinkExpiresAt).getTime();
  return Number.isFinite(expiry) && expiry <= Date.now();
}

function _currentDeliveryEmployeeId() {
  return Number(document.getElementById('delivery-employee')?.value || 0);
}

function _currentDeliveryEmployeeLink() {
  return String(document.getElementById('delivery-employee-link')?.value || '').trim();
}

async function generateDeliveryEmployeeLink() {
  const employeeId = _currentDeliveryEmployeeId();
  if (!employeeId) {
    setDeliveryEmployeeAccessStatus('error', tr('delivery.employeeAccessSelectFirst', 'Selecione um colaborador primeiro.'));
    return;
  }
  _setDeliveryEmployeeAccessBusy(true);
  setDeliveryEmployeeAccessStatus('loading', tr('delivery.employeeAccessGenerating', 'Gerando link…'));
  try {
    const payload = await api('/api/employee-portal-link', {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user.id, employee_id: employeeId })
    });
    const accessLink = payload.access_link || '';
    const linkField = document.getElementById('delivery-employee-link');
    if (linkField) linkField.value = accessLink;
    _deliveryEmployeeLinkExpiresAt = String(payload.expires_at || '');
    if (_deliveryEmployeeLinkExpiresAt) {
      const expiryLabel = new Date(_deliveryEmployeeLinkExpiresAt).toLocaleString();
      setDeliveryEmployeeAccessStatus('success',
        tr('delivery.employeeAccessGenerated', 'Link gerado. Válido até {expiry}.').replace('{expiry}', expiryLabel));
    } else {
      setDeliveryEmployeeAccessStatus('success', tr('delivery.employeeAccessGeneratedNoExpiry', 'Link gerado com sucesso.'));
    }
  } catch (error) {
    setDeliveryEmployeeAccessStatus('error', error.message);
  } finally {
    _setDeliveryEmployeeAccessBusy(false);
  }
}

async function copyDeliveryEmployeeLink() {
  const accessLink = _currentDeliveryEmployeeLink();
  if (!accessLink) {
    setDeliveryEmployeeAccessStatus('error', tr('delivery.employeeAccessNoLink', 'Gere um link antes de continuar.'));
    return;
  }
  if (_deliveryEmployeeLinkIsExpired()) {
    setDeliveryEmployeeAccessStatus('expired', tr('delivery.employeeAccessExpired', 'Link expirado. Gere um novo link.'));
    return;
  }
  const copied = await copyTextToClipboard(accessLink);
  setDeliveryEmployeeAccessStatus(copied ? 'success' : 'error',
    copied ? tr('delivery.employeeAccessCopied', 'Link copiado.')
           : tr('delivery.employeeAccessCopyManual', 'Não foi possível copiar automaticamente. Copie manualmente.'));
}

function openDeliveryEmployeeLink() {
  const accessLink = _currentDeliveryEmployeeLink();
  if (!accessLink) {
    setDeliveryEmployeeAccessStatus('error', tr('delivery.employeeAccessNoLink', 'Gere um link antes de continuar.'));
    return;
  }
  if (_deliveryEmployeeLinkIsExpired()) {
    setDeliveryEmployeeAccessStatus('expired', tr('delivery.employeeAccessExpired', 'Link expirado. Gere um novo link.'));
    return;
  }
  const popup = globalThis.open(accessLink, '_blank', 'noopener,noreferrer');
  if (!popup) {
    setDeliveryEmployeeAccessStatus('error', tr('delivery.employeeAccessOpenBlocked', 'O navegador bloqueou a abertura. Permita pop-ups e tente novamente.'));
  }
}

async function showDeliveryEmployeeLinkQr() {
  const employeeId = _currentDeliveryEmployeeId();
  if (!employeeId) {
    setDeliveryEmployeeAccessStatus('error', tr('delivery.employeeAccessSelectFirst', 'Selecione um colaborador primeiro.'));
    return;
  }
  _setDeliveryEmployeeAccessBusy(true);
  setDeliveryEmployeeAccessStatus('loading', tr('delivery.employeeAccessGenerating', 'Gerando link…'));
  try {
    await printEmployeePortalLink(employeeId);
    setDeliveryEmployeeAccessStatus('success', tr('delivery.employeeAccessQrOpened', 'QR Code aberto para impressão.'));
  } catch (error) {
    setDeliveryEmployeeAccessStatus('error', error.message);
  } finally {
    _setDeliveryEmployeeAccessBusy(false);
  }
}

async function sendDeliveryEmployeeMessage(channelOverride) {
  const employeeId = _currentDeliveryEmployeeId();
  if (!employeeId) {
    setDeliveryEmployeeAccessStatus('error', tr('delivery.employeeAccessSelectFirst', 'Selecione um colaborador primeiro.'));
    return;
  }
  const channel = ['whatsapp', 'email'].includes(String(channelOverride))
    ? String(channelOverride)
    : String(document.getElementById('delivery-employee-message-model')?.value || 'whatsapp');
  const employee = state.employees.find((item) => Number(item.id) === employeeId);
  if (channel === 'whatsapp' && !String(employee?.whatsapp || '').trim()) {
    setDeliveryEmployeeAccessStatus('error', tr('delivery.employeeAccessNoWhatsapp', 'Colaborador sem WhatsApp cadastrado.'));
    return;
  }
  if (channel === 'email' && !String(employee?.email || '').trim()) {
    setDeliveryEmployeeAccessStatus('error', tr('delivery.employeeAccessNoEmail', 'Colaborador sem e-mail cadastrado.'));
    return;
  }
  _setDeliveryEmployeeAccessBusy(true);
  setDeliveryEmployeeAccessStatus('loading', tr('delivery.employeeAccessSending', 'Enviando…'));
  try {
    const payload = await api('/api/employee-contact-launch', {
      method: 'POST',
      body: JSON.stringify({
        actor_user_id: state.user.id,
        employee_id: employeeId,
        channel,
        access_link: _currentDeliveryEmployeeLink()
      })
    });
    const launchUrl = String(payload?.launch_url || '').trim();
    if (!launchUrl) throw new Error(tr('delivery.employeeAccessLaunchError', 'Não foi possível gerar a URL de envio.'));
    const sentMsg = channel === 'whatsapp'
      ? tr('delivery.employeeAccessSentWhatsapp', 'Envio aberto no WhatsApp.')
      : tr('delivery.employeeAccessSentEmail', 'Envio aberto no e-mail.');
    const popup = globalThis.open(launchUrl, '_blank', 'noopener,noreferrer');
    setDeliveryEmployeeAccessStatus(popup ? 'success' : 'error',
      popup ? sentMsg
            : tr('delivery.employeeAccessOpenBlocked', 'O navegador bloqueou a abertura. Permita pop-ups e tente novamente.'));
  } catch (error) {
    setDeliveryEmployeeAccessStatus('error', error.message);
  } finally {
    _setDeliveryEmployeeAccessBusy(false);
  }
}

function setDeliveryQrStatus(message, isError = false) {
  const status = document.getElementById('delivery-qr-status');
  if (!status) return;
  status.textContent = String(message || '');
  status.style.color = isError ? 'var(--danger)' : 'var(--accent)';
}

function resolveQrPayload(decodedText) {
  const text = String(decodedText || '').trim();
  if (!text) return null;
  const normalized = text.normalize('NFKC');
  if (normalized.startsWith('{') && normalized.endsWith('}')) {
    const parsed = safeJsonParse(normalized, null);
    const type = String(parsed?.type || '').trim().toLowerCase();
    const id = String(parsed?.id || '').trim();
    if (!id) return null;
    if (['colaborador', 'employee', 'colab'].includes(type)) return { type: 'colaborador', id, raw: text };
    if (type === 'epi') return { type: 'epi', id, raw: text };
    if (type === 'ficha') return { type: 'ficha', id, raw: text };
    return null;
  }
  const match = normalized.match(/^(COLAB|EPI|FICHA)\s*:\s*(.+)$/i);
  if (!match) return null;
  const kind = String(match[1] || '').toUpperCase();
  const id = String(match[2] || '').trim();
  if (!id) return null;
  if (kind === 'COLAB') return { type: 'colaborador', id, raw: text };
  if (kind === 'EPI') return { type: 'epi', id, raw: text };
  if (kind === 'FICHA') return { type: 'ficha', id, raw: text };
  return null;
}

function resolveStockQrPayload(decodedText) {
  const rawText = String(decodedText || '').trim();
  if (!rawText) return null;
  const normalized = rawText.normalize('NFKC');
  if (normalized.startsWith('{') && normalized.endsWith('}')) {
    const parsed = safeJsonParse(normalized, null);
    const type = String(parsed?.type || '').trim().toLowerCase();
    const id = Number(parsed?.id || 0);
    const code = String(parsed?.code || parsed?.qr_code_value || '').trim();
    if (['stock_item', 'epi_stock_item', 'stockitem'].includes(type) && (id > 0 || code)) {
      return { stock_item_id: id > 0 ? id : null, qr_code: code || null, format: 'json' };
    }
  }
  const simplified = normalized.match(/^EPIITEM\s*:\s*(\d+)$/i);
  if (simplified) {
    return { stock_item_id: Number(simplified[1]), qr_code: null, format: 'simple' };
  }
  const stockLabelMatch = normalized.match(/^EPI-ITEM-(\d{4})-(\d{4})-(\d{8})$/i);
  if (stockLabelMatch) {
    return {
      stock_item_id: Number(stockLabelMatch[3]),
      qr_code: normalized,
      format: 'stock-label'
    };
  }
  return { stock_item_id: null, qr_code: normalized, format: 'raw' };
}

function emitInputChangeEvents(field) {
  if (!field) return;
  field.dispatchEvent(new Event('input', { bubbles: true }));
  field.dispatchEvent(new Event('change', { bubbles: true }));
}

function applySelectValueWithFallback(field, rawValue) {
  if (!field) return false;
  const normalizedValue = String(rawValue || '').trim();
  if (!normalizedValue) return false;
  field.value = normalizedValue;
  if (String(field.value) === normalizedValue) return true;
  const option = Array.from(field.options || []).find((candidate) => {
    const optionValue = String(candidate.value || '').trim();
    const optionLabel = String(candidate.textContent || '').trim();
    const optionPrefix = optionLabel.split('-')[0]?.trim() || '';
    return optionValue === normalizedValue || optionPrefix === normalizedValue;
  });
  if (!option) return false;
  field.value = option.value;
  return String(field.value) === String(option.value);
}

function applyQrFeedbackOnce(key) {
  const now = Date.now();
  if (!key) return;
  if (qrScannerState.lastFeedbackKey === key && now - qrScannerState.lastFeedbackAt < 1500) return;
  qrScannerState.lastFeedbackKey = key;
  qrScannerState.lastFeedbackAt = now;

  const AudioCtx = globalThis.AudioContext || globalThis.webkitAudioContext;
  if (AudioCtx) {
    const ctx = new AudioCtx();
    const oscillator = ctx.createOscillator();
    const gain = ctx.createGain();
    oscillator.type = 'sine';
    oscillator.frequency.value = 1080;
    gain.gain.setValueAtTime(0.0001, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.12, ctx.currentTime + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.18);
    oscillator.connect(gain);
    gain.connect(ctx.destination);
    oscillator.start();
    oscillator.stop(ctx.currentTime + 0.2);
    oscillator.onended = () => ctx.close().catch(() => null);
  }
  if (navigator?.vibrate) navigator.vibrate(80);
}

function preencherCampoPorQr(decodedData) {
  if (!decodedData?.type || !decodedData?.id) return false;
  const value = String(decodedData.id).trim();
  if (!value) return false;
  if (decodedData.type === 'colaborador') {
    const field = document.getElementById('delivery-employee');
    if (!field) return false;
    const applied = applySelectValueWithFallback(field, value);
    if (!applied) return false;
    emitInputChangeEvents(field);
    refreshDeliveryContext();
    return true;
  }
  if (decodedData.type === 'epi') {
    const field = document.getElementById('delivery-epi');
    if (!field) return false;
    const applied = applySelectValueWithFallback(field, value);
    if (!applied) return false;
    emitInputChangeEvents(field);
    refreshDeliveryContext();
    return true;
  }
  if (decodedData.type === 'ficha') {
    const field = document.getElementById('ficha-employee');
    if (!field) return false;
    const applied = applySelectValueWithFallback(field, value);
    if (!applied) return false;
    showView('fichas');
    emitInputChangeEvents(field);
    return true;
  }
  return false;
}

async function onQrScanSuccess(decodedText) {
  const text = String(decodedText || '').trim();
  if (!text) {
    setDeliveryQrStatus('Leitura vazia ignorada.', true);
    return;
  }
  const now = Date.now();
  if (qrScannerState.lastDecodedText === text && now - qrScannerState.lastDecodedAt < 1200) return;
  qrScannerState.lastDecodedText = text;
  qrScannerState.lastDecodedAt = now;

  const parsed = resolveQrPayload(text);
  if (parsed && parsed.type !== 'epi') {
    setDeliveryQrStatus('QR de colaborador/ficha ignorado no fluxo de entrega. Selecione o colaborador manualmente.', true);
    return;
  }

  const stockItem = await handleDeliveryQrScan({ sourceValue: text, applyToForm: false });
  if (!stockItem) {
    console.warn('[qr][scan] leitura sem confirmação', { raw: text, reason: 'stock_lookup_failed' });
    setDeliveryQrStatus('QR lido, mas não reconhecido para preenchimento automático.', true);
    return;
  }
  const addResult = addStockQrToSession(stockItem);
  if (!addResult.added) {
    if (addResult.reason === 'duplicate') {
      setDeliveryQrStatus(`QR duplicado ignorado: ${stockItem.qr_code_value}`);
      return;
    }
    if (addResult.reason === 'throttled') return;
    setDeliveryQrStatus('QR lido, mas inválido para a sessão.', true);
    return;
  }
  applyQrFeedbackOnce(`estoque:${stockItem.qr_code_value}`);
  const epiSelected = applyStockItemToDeliverySelection(stockItem, { source: 'scanner' });
  if (!epiSelected) {
    removeStockQrFromSession(stockItem.qr_code_value);
    setDeliveryQrStatus(`QR confirmado (${stockItem.qr_code_value}), mas o EPI não pôde ser selecionado automaticamente.`, true);
    return;
  }
  refreshDeliveryContext();
  setDeliveryQrStatus(`QR confirmado e EPI selecionado (${qrScannerState.scanSession.length}): ${stockItem.qr_code_value}`);
}

let zxingLoaderPromise = null;
let html5QrcodeLoaderPromise = null;
function loadHtml5QrcodeLibrary() {
  if (globalThis.Html5Qrcode) return Promise.resolve(globalThis.Html5Qrcode);
  if (html5QrcodeLoaderPromise) return html5QrcodeLoaderPromise;
  html5QrcodeLoaderPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js';
    script.async = true;
    script.onload = () => globalThis.Html5Qrcode ? resolve(globalThis.Html5Qrcode) : reject(new Error('Falha ao carregar html5-qrcode.'));
    script.onerror = () => reject(new Error('Falha ao carregar biblioteca html5-qrcode.'));
    document.head.appendChild(script);
  }).catch((error) => {
    html5QrcodeLoaderPromise = null;
    throw error;
  });
  return html5QrcodeLoaderPromise;
}

function loadZxingLibrary() {
  if (globalThis.ZXingBrowser?.BrowserMultiFormatReader) return Promise.resolve(globalThis.ZXingBrowser);
  if (zxingLoaderPromise) return zxingLoaderPromise;
  zxingLoaderPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://unpkg.com/@zxing/browser@0.1.5/umd/index.min.js';
    script.async = true;
    script.onload = () => globalThis.ZXingBrowser?.BrowserMultiFormatReader ? resolve(globalThis.ZXingBrowser) : reject(new Error('Falha ao carregar biblioteca ZXing.'));
    script.onerror = () => reject(new Error('Falha ao carregar biblioteca de leitura.'));
    document.head.appendChild(script);
  });
  return zxingLoaderPromise;
}

async function stopDeliveryQrCamera(options = {}) {
  const preserveStarting = options?.preserveStarting === true;
  if (qrScannerState.stopping) return qrScannerState.stopping;
  qrScannerState.stopping = (async () => {
    qrScannerState.startToken += 1;
    if (!preserveStarting) qrScannerState.starting = false;
    qrScannerState.active = false;
    if (qrScannerState.rafId) cancelAnimationFrame(qrScannerState.rafId);
    qrScannerState.rafId = null;
    if (qrScannerState.zxingControls?.stop) {
      try {
        await Promise.resolve(qrScannerState.zxingControls.stop());
      } catch (error) {
        console.warn('[qr] Falha ao parar ZXing controls', error);
      }
    }
    qrScannerState.zxingControls = null;
    qrScannerState.zxingReader = null;
    if (qrScannerState.html5Scanner) {
      const scanner = qrScannerState.html5Scanner;
      qrScannerState.html5Scanner = null;
      try {
        await scanner.stop();
      } catch (error) {
        console.warn('[qr] Falha ao parar html5-qrcode', error);
      }
      try {
        await scanner.clear();
      } catch (error) {
        console.warn('[qr] Falha ao limpar html5-qrcode', error);
      }
    }
    qrScannerState.mode = '';
    if (qrScannerState.stream) {
      qrScannerState.stream.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch (error) {
          console.warn('[qr] Falha ao encerrar track da câmera', error);
        }
      });
    }
    qrScannerState.stream = null;
    const wrap = document.getElementById('delivery-qr-camera-wrap');
    const video = document.getElementById('delivery-qr-video');
    const readerBox = document.getElementById('delivery-qr-reader-box');
    if (video) {
      video.pause?.();
      video.srcObject = null;
      video.style.display = 'block';
      video.hidden = false;
    }
    if (readerBox) {
      readerBox.style.display = 'none';
      readerBox.innerHTML = '';
    }
    if (wrap) {
      wrap.style.display = 'none';
      wrap.classList.remove('is-active');
      wrap.classList.remove('qr-camera-fullscreen');
    }
    setDeliveryQrStatus('Leitura encerrada.');
  })()
    .finally(() => {
      qrScannerState.stopping = null;
    });
  return qrScannerState.stopping;
}

async function enableDeliveryBarcodeReaderMode() {
  await stopDeliveryQrCamera();
  const input = document.getElementById('delivery-qr-scan');
  input?.focus();
  if (input) input.select?.();
  setDeliveryQrStatus('Modo leitor USB ativo: Faça o bip no campo de código.');
}

function finalizeDeliveryQrSession() {
  const lastItem = qrScannerState.scanSession[qrScannerState.scanSession.length - 1] || null;
  if (!lastItem) {
    setDeliveryQrStatus('Nenhum QR válido lido para aplicar no movimento.', true);
    return false;
  }
  applyStockItemToDeliveryForm(lastItem);
  setDeliveryQrStatus(`Leitura finalizada. ${qrScannerState.scanSession.length} código(s) conferido(s). Último item aplicado no formulário.`);
  return true;
}

async function finishDeliveryQrCameraSession() {
  const applied = finalizeDeliveryQrSession();
  if (applied) await stopDeliveryQrCamera();
  if (!applied) return;
  const input = document.getElementById('delivery-qr-scan');
  input?.focus();
}

async function startDeliveryQrWithBarcodeDetector(video, input) {
  const detector = new BarcodeDetector({ formats: ['qr_code', 'ean_13', 'ean_8', 'code_128', 'code_39', 'upc_a', 'upc_e', 'itf'] });
  qrScannerState.mode = 'barcode-detector';
  const detectFrame = async () => {
    if (!qrScannerState.active) return;
    try {
      const codes = await detector.detect(video);
      if (codes?.length) {
        const rawValue = String(codes[0].rawValue || '').trim();
        if (rawValue) {
          input.value = rawValue;
          setDeliveryQrStatus(`Código lido (${codes[0].format || 'desconhecido'}): ${rawValue}`);
          void onQrScanSuccess(rawValue);
        }
      }
    } catch (error) {
      console.error('QR detection error:', error);
      setDeliveryQrStatus('Erro na leitura por câmera. Tentando novamente...', true);
    }
    qrScannerState.rafId = requestAnimationFrame(detectFrame);
  };
  setDeliveryQrStatus('Câmera ativa. Aponte para QR Code ou código de barras.');
  detectFrame();
}

async function startDeliveryQrWithZxing(videoElementId, input) {
  const ZXingBrowser = await loadZxingLibrary();
  qrScannerState.mode = 'zxing';
  qrScannerState.zxingReader = new ZXingBrowser.BrowserMultiFormatReader();
  setDeliveryQrStatus('Câmera ativa (modo compatibilidade). Aponte para QR/Barcode.');
  qrScannerState.zxingControls = await qrScannerState.zxingReader.decodeFromVideoDevice(undefined, videoElementId, (result, error) => {
    if (result?.text) {
      input.value = String(result.text).trim();
      setDeliveryQrStatus(`Código lido: ${input.value}`);
      void onQrScanSuccess(input.value);
    } else if (error?.name && error.name !== 'NotFoundException') {
      setDeliveryQrStatus('Aguardando leitura...', false);
    }
  });
}

async function startDeliveryQrWithHtml5Qrcode(input) {
  const Html5Qrcode = await loadHtml5QrcodeLibrary();
  const readerBox = document.getElementById('delivery-qr-reader-box');
  const video = document.getElementById('delivery-qr-video');
  if (!readerBox) throw new Error('Área de Câmera indisponível.');
  if (video) video.style.display = 'none';
  readerBox.style.display = 'block';
  qrScannerState.mode = 'html5-qrcode';
  const scanner = new Html5Qrcode('delivery-qr-reader-box');
  qrScannerState.html5Scanner = scanner;
  let cameraConfig = { facingMode: { ideal: 'environment' } };
  if (typeof Html5Qrcode.getCameras === 'function') {
    const cameras = await Html5Qrcode.getCameras();
    const rear = cameras.find((camera) => /back|rear|traseira|environment/i.test(String(camera?.label || '')));
    if (rear?.id) cameraConfig = { deviceId: { exact: rear.id } };
    else if (cameras?.[0]?.id) cameraConfig = { deviceId: { exact: cameras[0].id } };
  }
  setDeliveryQrStatus('Câmera ativa (QR contínuo). Alinhe o QR na área central.');
  await scanner.start(
    cameraConfig,
    {
      fps: 12,
      qrbox: (viewfinderWidth, viewfinderHeight) => {
        const side = Math.round(Math.min(viewfinderWidth, viewfinderHeight) * 0.75);
        return { width: Math.max(200, Math.min(side, 320)), height: Math.max(200, Math.min(side, 320)) };
      }
    },
    (decodedText) => {
      input.value = String(decodedText || '').trim();
      void onQrScanSuccess(input.value);
    },
    () => null
  );
}

function handleDeliveryCameraStartClick(event) {
  if (event) event.preventDefault();
  console.info('[qr-click] Ler com câmera clicado');
  void startDeliveryQrCamera();
}

function bindDeliveryQrCameraDelegatedClick() {
  if (globalThis.__EPI_QR_CAMERA_DELEGATED_BOUND__) return;
  const delegatedHandler = (event) => {
    const button = event?.target?.closest?.('#delivery-qr-start, [data-action="delivery-qr-camera"]');
    if (!button || button.disabled) return;
    handleDeliveryCameraStartClick(event);
  };
  safeOn(document, 'click', delegatedHandler);
  globalThis.__EPI_QR_CAMERA_DELEGATED_BOUND__ = true;
}

async function startDeliveryQrCamera() {
  const input = document.getElementById('delivery-qr-scan');
  const wrap = document.getElementById('delivery-qr-camera-wrap');
  const video = document.getElementById('delivery-qr-video');
  const readerBox = document.getElementById('delivery-qr-reader-box');
  console.info('[qr] startDeliveryQrCamera', {
    input: Boolean(input),
    wrap: Boolean(wrap),
    video: Boolean(video)
  });

  if (!input || !wrap) {
    console.error('[qr] INPUT/WRAP não encontrados no DOM.');
    alert('Leitor de QR indisponível nesta tela. Recarregue a página e tente novamente.');
    return;
  }
  if (!video) {
    console.error('[qr] VIDEO NÃO ENCONTRADO');
    alert('Elemento de vídeo não encontrado. Recarregue a página e tente novamente.');
    return;
  }
  if (qrScannerState.starting) {
    setDeliveryQrStatus('Aguardando permissão da câmera. Conclua a solicitação do navegador.');
    return;
  }
  qrScannerState.starting = true;
  try {
    await stopDeliveryQrCamera({ preserveStarting: true });
    const startToken = qrScannerState.startToken;
    if (!qrScannerState.starting) return;
    setDeliveryQrStatus('Iniciando câmera...');
    wrap.hidden = false;
    wrap.classList.add('is-active');
    wrap.style.display = 'block';
    wrap.style.visibility = 'visible';
    video.hidden = false;
    video.setAttribute('playsinline', '');
    video.setAttribute('autoplay', '');
    video.muted = true;
    video.autoplay = true;

    if (navigator.permissions?.query) {
      try {
        const cameraPermission = await navigator.permissions.query({ name: 'camera' });
        if (cameraPermission?.state === 'prompt') {
          setDeliveryQrStatus('Permita o acesso à câmera no navegador para iniciar a leitura.');
        }
      } catch (permissionError) {
        console.warn('[qr] consulta de permissão de câmera indisponível', permissionError);
      }
    }

    if (!('mediaDevices' in navigator) || !navigator.mediaDevices.getUserMedia) {
      setDeliveryQrStatus('Navegador sem acesso à câmera. Use leitor USB ou digite o código.', true);
      alert('Câmera não disponível neste navegador. Você pode digitar ou usar leitor USB.');
      return;
    }
    const isLocalhost = ['localhost', '127.0.0.1'].includes(String(location.hostname || '').toLowerCase());
    if (location.protocol !== 'https:' && !isLocalhost) {
      setDeliveryQrStatus('Câmera exige HTTPS para funcionar neste navegador.', true);
      return;
    }

    if (startToken !== qrScannerState.startToken) return;
    resetDeliveryQrSession();

    wrap.style.display = 'grid';
    wrap.classList.add('qr-camera-fullscreen');
    if (video.srcObject && typeof video.srcObject.getTracks === 'function') {
      video.srcObject.getTracks().forEach((track) => track.stop());
    }
    video.style.display = 'none';
    video.srcObject = null;
    if (readerBox) {
      readerBox.style.display = 'block';
      readerBox.innerHTML = '';
    }
    qrScannerState.active = true;
    setDeliveryQrStatus('Solicitando permissão da câmera...');
    if (readerBox) {
      const html5Timeout = new Promise((_, reject) => {
        setTimeout(() => {
          const timeoutError = new Error('camera-permission-timeout');
          timeoutError.name = 'PermissionPromptTimeout';
          reject(timeoutError);
        }, 15000);
      });
      await Promise.race([
        (async () => {
          await new Promise((resolve) => requestAnimationFrame(resolve));
          return startDeliveryQrWithHtml5Qrcode(input);
        })(),
        html5Timeout
      ]);
      if (startToken !== qrScannerState.startToken) {
        await stopDeliveryQrCamera();
        return;
      }
      return;
    }
  } catch (html5Error) {
    console.warn('[qr] html5-qrcode indisponível, aplicando fallback:', html5Error);
  }

  try {
    const getUserMediaWithTimeout = async (constraints, timeoutMs = 15000) => {
      let timeoutId = null;
      const timeoutPromise = new Promise((_, reject) => {
        timeoutId = setTimeout(() => {
          const timeoutError = new Error('Permissão de câmera pendente por muito tempo.');
          timeoutError.name = 'PermissionPromptTimeout';
          reject(timeoutError);
        }, timeoutMs);
      });
      try {
        return await Promise.race([
          navigator.mediaDevices.getUserMedia(constraints),
          timeoutPromise
        ]);
      } finally {
        if (timeoutId) clearTimeout(timeoutId);
      }
    };
    let stream;
    try {
      console.info('[qr] solicitando câmera');
      stream = await getUserMediaWithTimeout({
        video: { facingMode: { ideal: 'environment' } },
        audio: false
      });
      console.info('[qr] stream principal iniciado');
    } catch (primaryError) {
      console.warn('[qr] fallback para câmera padrão', primaryError);
      stream = await getUserMediaWithTimeout({ video: true, audio: false });
      console.info('[qr] stream fallback iniciado');
    }

    qrScannerState.stream = stream;
    qrScannerState.active = true;
    wrap.style.display = 'grid';
    wrap.style.visibility = 'visible';
    if (readerBox) readerBox.style.display = 'none';
    video.srcObject = stream;
    video.style.display = 'block';
    await video.play();
    console.info('[qr] vídeo em reprodução', {
      paused: video.paused,
      readyState: video.readyState,
      videoWidth: video.videoWidth,
      videoHeight: video.videoHeight
    });
    if (startToken !== qrScannerState.startToken) {
      await stopDeliveryQrCamera();
      return;
    }

    if ('BarcodeDetector' in globalThis) {
      await startDeliveryQrWithBarcodeDetector(video, input);
    } else {
      await startDeliveryQrWithZxing('delivery-qr-video', input);
    }
  } catch (error) {
    console.error('[qr] erro ao iniciar câmera', error);
    await stopDeliveryQrCamera();
    const message = String(error?.message || '');
    const blocked = ['NotAllowedError', 'PermissionDeniedError'].includes(String(error?.name || ''));
    if (String(error?.name || '') === 'PermissionPromptTimeout') {
      setDeliveryQrStatus('Permita o acesso à câmera no navegador e tente novamente.', true);
      alert('Permita o acesso à câmera no navegador.');
      return;
    }
    if (blocked) {
      setDeliveryQrStatus('permissão de Câmera negada.', true);
      alert('permissão da Câmera negada. Autorize o acesso no navegador e tente novamente.');
      return;
    }
    if (String(error?.name || '') === 'NotFoundError') {
      setDeliveryQrStatus('Nenhuma câmera encontrada neste dispositivo.', true);
      alert('Nenhuma câmera foi encontrada neste dispositivo.');
      return;
    }
    if (String(error?.name || '') === 'NotReadableError') {
      setDeliveryQrStatus('Câmera ocupada por outro aplicativo/aba.', true);
      alert('A câmera está em uso por outro aplicativo ou aba.');
      return;
    }
    if (String(error?.name || '') === 'OverconstrainedError') {
      setDeliveryQrStatus('Configuração de câmera não suportada; tentando modo compatível.', true);
      alert('Configuração de câmera não suportada neste dispositivo.');
      return;
    }
    if (String(error?.name || '') === 'AbortError') {
      setDeliveryQrStatus('Inicialização da câmera foi interrompida.', true);
      return;
    }
    setDeliveryQrStatus('Falha ao iniciar câmera neste dispositivo/navegador.', true);
    alert(`Não foi possível iniciar a câmera automaticamente. Você pode usar "Ler por imagem" ou "Usar leitor de código de barras". ${message}`.trim());
  } finally {
    qrScannerState.starting = false;
  }
}

async function handleDeliveryQrImageUpload(event) {
  const inputField = document.getElementById('delivery-qr-scan');
  const file = event?.target?.files?.[0];
  if (!file || !inputField) return;
  try {
    const ZXingBrowser = await loadZxingLibrary();
    const imageReader = new ZXingBrowser.BrowserMultiFormatReader();
    const imageUrl = URL.createObjectURL(file);
    const tempImage = new Image();
    tempImage.src = imageUrl;
    await tempImage.decode();
    const result = await imageReader.decodeFromImageElement(tempImage);
    URL.revokeObjectURL(imageUrl);
    if (!result?.text) throw new Error('Não identificado na imagem.');
    inputField.value = String(result.text).trim();
    setDeliveryQrStatus(`Código lido por imagem: ${inputField.value}`);
    void onQrScanSuccess(inputField.value);
  } catch (error) {
    console.error('Image QR detection error:', error);
    setDeliveryQrStatus('ler código da imagem.', true);
    alert('Falha ao ler imagem. Tente outra foto com melhor iluminação e foco.');
  } finally {
    if (event?.target) event.target.value = '';
  }
}

const isFichaFinalizeDebugEnabled = () => Boolean(globalThis.__EPI_DEBUG_FICHA_FINALIZE__);
const logFichaFinalizeTiming = (t0, stage, extra = null) => {
  if (!isFichaFinalizeDebugEnabled()) return;
  const elapsed = Math.round(performance.now() - t0);
  if (extra === null) {
    console.info('[ficha-finalize]', stage, elapsed);
    return;
  }
  console.info('[ficha-finalize]', stage, elapsed, extra);
};


const finalizeFichaPeriod = async (periodId, options = {}) => {
  if (!requirePermission('fichas:view')) return;
  const finalizeButton = options && options.button instanceof HTMLElement
    ? options.button
    : refs.fichaView?.querySelector(`[data-ficha-finalize="${periodId}"]`);
  if (finalizeButton) {
    if (finalizeButton.dataset.loading === '1') return;
    finalizeButton.dataset.loading = '1';
    finalizeButton.disabled = true;
    finalizeButton.setAttribute('aria-busy', 'true');
  }

  const channel = String(refs.fichaView?.querySelector(`[data-ficha-channel="${periodId}"]`)?.value || 'whatsapp').trim();
  const employee = (state.employees || []).find((item) => String(item.id) === String(refs.fichaEmployee?.value || ''));
  const removeManualWhatsAppLink = () => {
    const existing = refs.fichaView?.querySelector('[data-manual-whatsapp-link]');
    if (existing) existing.remove();
  };
  const buildWhatsAppHref = ({ phone, message }) => {
    const safeMessage = String(message || '').trim();
    if (!safeMessage) throw new Error('Mensagem do WhatsApp inválida.');
    const normalizedPhone = String(phone || '').replace(/\D/g, '');
    const encodedMessage = encodeURIComponent(safeMessage);
    return normalizedPhone
      ? `https://wa.me/${normalizedPhone}?text=${encodedMessage}`
      : `https://wa.me/?text=${encodedMessage}`;
  };
  const renderManualWhatsAppLink = (href) => {
    removeManualWhatsAppLink();
    if (!refs.fichaView) return;
    const wrapper = document.createElement('div');
    wrapper.className = 'summary-item';
    wrapper.setAttribute('data-manual-whatsapp-link', '1');
    wrapper.innerHTML = `<strong>Compartilhamento pronto.</strong><div style="margin-top:8px;"><a href="${escapeHtml(String(href || '').trim())}" target="_blank" rel="noopener noreferrer">Abrir WhatsApp</a></div>`;
    refs.fichaView.prepend(wrapper);
  };
  const isMobileWhatsAppTarget = () => /Android|iPhone|iPad|iPod/i.test(navigator.userAgent || '');
  let whatsappLaunchHandled = false;
  const launchWhatsAppOrFallback = (launchUrl) => {
    const safeUrl = String(launchUrl || '').trim();
    if (!safeUrl) throw new Error('Não foi possível abrir o compartilhamento. Gere o link novamente.');
    if (whatsappLaunchHandled) return;
    whatsappLaunchHandled = true;
    const mobileTarget = isMobileWhatsAppTarget();
    if (mobileTarget) {
      renderManualWhatsAppLink(safeUrl);
      return;
    }
    const popup = globalThis.open(safeUrl, '_blank', 'noopener,noreferrer');
    if (!popup) {
      renderManualWhatsAppLink(safeUrl);
    }
  };

  const extractLinkFromMessage = (messageText) => {
    const match = String(messageText || '').match(/https?:\/\/[^\s]+/i);
    return String(match?.[0] || '').trim();
  };
  const resolveEmployeePhone = () => {
    const digits = String(employee?.whatsapp || '').replace(/\D/g, '');
    if (!digits) return '';
    if (digits.length === 10 || digits.length === 11) return `55${digits}`;
    return digits;
  };
  const normalizeWhatsappText = (value) => String(value || '').replace(/�/g, '').normalize('NFC');
  const resolveLaunchUrl = (payloadData) => {
    const accessLink = String(payloadData?.access_link || '').trim() || extractLinkFromMessage(payloadData?.message);
    if (!/^https?:\/\//i.test(accessLink)) throw new Error('Não foi possível gerar um link válido da ficha para compartilhamento.');
    if (channel === 'whatsapp') {
      const providedLaunchUrl = String(payloadData?.launch_url || '').trim();
      if (/^https:\/\/(wa\.me|api\.whatsapp\.com)\//i.test(providedLaunchUrl)) {
        const parsed = new URL(providedLaunchUrl);
        const phoneFromQuery = String(parsed.searchParams.get('phone') || '').replace(/\D/g, '');
        const phoneFromPath = String(parsed.pathname || '').replace(/\//g, '').replace(/\D/g, '');
        const message = String(parsed.searchParams.get('text') || '').trim();
        return buildWhatsAppHref({ phone: phoneFromQuery || phoneFromPath, message });
    }

    const phone = resolveEmployeePhone();
	if (!phone) {
    	throw new Error('WhatsApp do colaborador não cadastrado.');
    }
    const message = normalizeWhatsappText(
    	String(payloadData?.message || `Link da Ficha de EPI: ${accessLink}`).trim());
      return buildWhatsAppHref({ phone, message });
    }

    const managerEmail = String(payloadData?.manager_email || state.user?.email || '').trim().toLowerCase();
    if (!managerEmail) { 
      throw new Error('E-mail do gestor não cadastrado.');
    }
    const subject = encodeURIComponent(`Assinatura da Ficha de EPI - ${employee?.name || 'Colaborador'}`);
    const body = encodeURIComponent([
      `Colaborador: ${employee?.name || '-'}`,
      '',
      String(payloadData?.message || `Link da Ficha de EPI: ${accessLink}`).trim()
    ].join('\n'));
    return `mailto:${managerEmail}?subject=${subject}&body=${body}`;
  };

  const openValidatedUrl = (targetUrl) => {
    const safeUrl = String(targetUrl || '').trim();
    
    if (!safeUrl) { 
      throw new Error('Não foi possível abrir o compartilhamento. Gere o link novamente.');
    }
      
    const isWhatsApp = /^https:\/\/(wa\.me|api\.whatsapp\.com)\//i.test(safeUrl);
    if (isWhatsApp) return;

    if (/^mailto:/i.test(safeUrl)) {
      globalThis.open(safeUrl, '_blank', 'noopener,noreferrer');
      return;
    }

    if (!/^https:\/\//i.test(safeUrl)) {
      throw new Error('URL de compartilhamento inválida.');
    }
    
    globalThis.open(safeUrl, '_blank', 'noopener,noreferrer');
  };
		  
  let popupRef = null;

  const _FINALIZE_MAX_RETRIES = 3;
  const _FINALIZE_RETRY_DELAY_MS = 3000;

  try {
    const timingStart = performance.now();
    logFichaFinalizeTiming(timingStart, 'click_start', { periodId: Number(periodId), channel });
    removeManualWhatsAppLink();
    if (channel === 'whatsapp') {
      popupRef = globalThis.open('about:blank', '_blank');
    }

    let _res, _raw;
    for (let _attempt = 1; _attempt <= _FINALIZE_MAX_RETRIES; _attempt += 1) {
      logFichaFinalizeTiming(timingStart, 'fetch_start', { attempt: _attempt });
      _res = await fetch('/api/fichas/finalize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          actor_user_id: state.user.id,
          ficha_period_id: Number(periodId),
          channel
        })
      });
      logFichaFinalizeTiming(timingStart, 'fetch_done', { status: _res.status, attempt: _attempt });
      _raw = await _res.json();
      logFichaFinalizeTiming(timingStart, 'json_parsed', { attempt: _attempt });

      const _errCode = String(_raw?.error?.code || '').toUpperCase();
      const _isBootstrap = _res.status === 503 || _errCode === 'DB_BOOTSTRAP_NOT_READY';
      if (!_raw.ok && _isBootstrap && _attempt < _FINALIZE_MAX_RETRIES) {
        showToast(`Servidor inicializando, aguardando... (tentativa ${_attempt}/${_FINALIZE_MAX_RETRIES})`, 'warning');
        await new Promise((r) => setTimeout(r, _FINALIZE_RETRY_DELAY_MS));
        continue;
      }
      break;
    }

    if (!_raw.ok) {
      const _errCode = String(_raw.error?.code || '').toUpperCase();
      const _errMsg = (_res.status === 503 || _errCode === 'DB_BOOTSTRAP_NOT_READY')
        ? 'O servidor ainda está inicializando. Aguarde alguns instantes e tente novamente.'
        : (_raw.error?.message || 'Erro ao finalizar período.');
      throw new Error(_errMsg);
    }

    const data = _raw.data || _raw;
    const launchUrl = resolveLaunchUrl(data);
    if (channel === 'whatsapp') {
      const canRedirectPopup = popupRef && !popupRef.closed;
      if (canRedirectPopup) {
        popupRef.location.href = launchUrl;
      } else {
        launchWhatsAppOrFallback(launchUrl);
      }
      await loadBootstrap();
      renderFicha();
      showToast('Link gerado. Clique em "Abrir WhatsApp" para compartilhar.', 'success');
      return;
    }
    openValidatedUrl(launchUrl);
    await loadBootstrap();
    renderFicha();
    showToast('Link de fechamento gerado e enviado. O período permanece aberto até o colaborador concluir no portal.', 'success');
  } catch (error) {
    alert(error.message);
  } finally {
    if (finalizeButton) {
      finalizeButton.dataset.loading = '0';
      finalizeButton.disabled = false;
      finalizeButton.removeAttribute('aria-busy');
    }
  }
};

async function copyFichaPeriodMessage(periodId) {
  try {
    const channel = String(refs.fichaView?.querySelector(`[data-ficha-channel="${periodId}"]`)?.value || 'whatsapp').trim();
    const payload = await api('/api/fichas/finalize', {
      method: 'POST',
      body: JSON.stringify({
        actor_user_id: state.user.id,
        ficha_period_id: Number(periodId),
        channel,
        preview_only: true
      })
    });
    const copied = await copyTextToClipboard(String(payload?.message || '').trim());
    alert(copied ? 'Mensagem copiada com sucesso.' : 'Mensagem pronta. Copie manualmente.');
  } catch (error) {
    alert(error.message);
  }
}

async function renderReports(filters = null) {
  if (!hasPermission('reports:view')) {
    recordOptionalBootstrapSectionSkipped('reports', 'missing_permission', { permission: 'reports:view' });
    return;
  }
  const normalizedFilters = filters || collectReportFilters();
  const params = new URLSearchParams({ ...normalizedFilters, actor_user_id: state.user.id });
  try {
    state.reports = await api(`/api/reports?${params.toString()}`);
  } catch (error) {
    if (Number(error?.status || 0) === 403) {
      recordOptionalBootstrapSectionSkipped('reports', 'forbidden', { status: 403, permission: 'reports:view' });
      return;
    }
    reportNonCriticalError('[renderReports] falha ao carregar relatório', error);
    if (refs.reportSummary) refs.reportSummary.innerHTML = '<div class="summary-item hint">Não foi possível carregar os relatórios agora. Tente novamente.</div>';
    return;
  }
  refs.reportSummary.innerHTML = `<div class="summary-item"><strong>${tr('delivery.list', 'Entregas')}:</strong> ${state.reports.deliveries.length}</div><div class="summary-item"><strong>${tr('report.totalDelivered', 'Total entregue')}:</strong> ${state.reports.total_quantity}</div>`;
  refs.reportUnits.innerHTML = Object.entries(state.reports.by_unit).map((item) => `<div class="report-row"><strong>${item[0]}</strong> ${item[1]}</div>`).join('') || `<div class="summary-item">${tr('report.noData', 'Sem dados.')}</div>`;
  refs.reportSectors.innerHTML = Object.entries(state.reports.by_sector).map((item) => `<div class="report-row"><strong>${item[0]}</strong> ${item[1]}</div>`).join('') || `<div class="summary-item">${tr('report.noData', 'Sem dados.')}</div>`;
  const reportTipoVinculoEl = document.getElementById('report-tipo-vinculo-summary');
  if (reportTipoVinculoEl) {
    reportTipoVinculoEl.innerHTML = Object.entries(state.reports.by_tipo_vinculo || {}).map((item) => `<div class="report-row"><strong>${item[0]}</strong> ${item[1]}</div>`).join('') || `<div class="summary-item">${tr('report.noData', 'Sem dados.')}</div>`;
  }
  if (!refs.reportEmployeeFichas) return;
  const employeeFichas = state.reports.employee_fichas || [];
  refs.reportEmployeeFichas.innerHTML = employeeFichas.map((item) => {
    return `<div class="summary-item"><strong>${item.employee_name} (${item.employee_id_code})</strong><div>${tr('report.period', 'Período')}: ${formatDate(item.period_start)} a ${formatDate(item.period_end)} | ${tr('delivery.status', 'Status')}: ${item.status}</div><div>${tr('unit.title', 'Unidade')}: ${item.unit_name || '-'} | ${tr('report.items', 'Itens')}: ${item.total_items} | ${tr('report.totalQuantity', 'Quantidade total')}: ${item.total_quantity}</div></div>`;
  }).join('') || `<div class="summary-item">${tr('report.selectEmployeeRecords', 'Selecione um colaborador para visualizar as fichas de EPI.')}</div>`;
  await loadArchiveReports({
    company_id: normalizedFilters.company_id || '',
    unit_id: normalizedFilters.unit_id || '',
    employee_id: normalizedFilters.employee_id || '',
    sector: normalizedFilters.sector || '',
    status: normalizedFilters.status || '',
    date_from: normalizedFilters.start_date || '',
    date_to: normalizedFilters.end_date || '',
  });
}


function retentionStatusBadge(status) {
  const normalized = String(status || 'archived').toLowerCase();
  if (normalized === 'expired') return renderBadge('status', 'warning', 'expirada');
  if (normalized === 'purged') return renderBadge('status', 'inactive', 'purgada');
  return renderBadge('status', 'active', 'arquivada');
}

function renderArchiveTable() {
  if (!refs.reportArchiveTable) return;
  refs.reportArchiveTable.innerHTML = (state.reportArchiveItems || []).map((item) => `
    <tr>
      <td>${formatDateTime(item.generated_at)}</td>
      <td>${item.employee_name || '-'} (${item.employee_id_code || '-'})</td>
      <td>${item.company_name || '-'}</td>
      <td>${item.unit_name || '-'}</td>
      <td>${retentionStatusBadge(item.status)}</td>
      <td><code>${String(item.html_sha256 || '').slice(0, 12)}...</code></td>
      <td>
        <div class="action-group">
          <button class="ghost" data-archive-view="${item.id}">Visualizar</button>
          <button class="ghost" data-archive-print="${item.id}">Imprimir</button>
          <button class="ghost" data-archive-export="${item.id}">Exportar</button>
        </div>
      </td>
    </tr>
  `).join('') || globalThis.dsTableState({ colspan: 7, message: 'Sem fichas arquivadas para os filtros informados.' });
  if (refs.reportArchivePagination) {
    refs.reportArchivePagination.textContent = `Registros: ${state.reportArchiveTotal} | Página ${state.reportArchivePage}`;
  }
}

async function loadArchiveReports(filters = {}) {
  if (!hasPermission('reports:view')) {
    recordOptionalBootstrapSectionSkipped('report_archive', 'missing_permission', { permission: 'reports:view' });
    return;
  }
  const params = new URLSearchParams({
    ...filters,
    page: String(state.reportArchivePage || 1),
    page_size: String(state.reportArchivePageSize || 50),
    actor_user_id: String(state.user?.id || '')
  });
  let payload;
  try {
    payload = await api(`/api/ficha-archive?${params.toString()}`);
  } catch (error) {
    if (Number(error?.status || 0) === 403) {
      recordOptionalBootstrapSectionSkipped('report_archive', 'forbidden', { status: 403, permission: 'reports:view' });
      return;
    }
    reportNonCriticalError('[loadArchiveReports] falha ao carregar arquivo', error);
    state.reportArchiveItems = [];
    state.reportArchiveTotal = 0;
    renderArchiveTable();
    return;
  }
  state.reportArchiveItems = payload.items || [];
  state.reportArchiveTotal = Number(payload.total || 0);
  state.fichaRetentionPolicy = payload.retention_policy || state.fichaRetentionPolicy;
  renderArchiveTable();
}

async function loadArchivalPolicy() {
  if (!refs.archivalPolicyForm || !hasConfigurationAccess()) return;
  try {
    const params = new URLSearchParams({ actor_user_id: String(state.user.id) });
    if (state.user?.role === 'master_admin' && state.user?.company_id) {
      params.set('company_id', String(state.user.company_id));
    }
    const policy = await api(`/api/archival-policy?${params.toString()}`);
    if (refs.archivalRetentionUnits) refs.archivalRetentionUnits.value = String(policy.unit_retention_years || 5);
    if (refs.archivalRetentionEpis) refs.archivalRetentionEpis.value = String(policy.epi_retention_years || 5);
    if (refs.archivalRetentionEmployees) refs.archivalRetentionEmployees.value = String(policy.employee_retention_years || 5);
    const canEdit = ['master_admin', 'general_admin'].includes(state.user?.role);
    [refs.archivalRetentionUnits, refs.archivalRetentionEpis, refs.archivalRetentionEmployees].forEach((field) => {
      if (field) field.disabled = !canEdit;
    });
    const submit = refs.archivalPolicyForm.querySelector('button[type="submit"]');
    if (submit) submit.disabled = !canEdit;
  } catch (error) {
    reportNonCriticalError('[configuracao] falha ao carregar política de arquivamento', error);
  }
}

function renderRetentionPolicy() {
  if (refs.fichaRetentionYears) refs.fichaRetentionYears.value = String(state.fichaRetentionPolicy?.retention_years || 5);
  if (refs.fichaRetentionPurgeEnabled) refs.fichaRetentionPurgeEnabled.checked = Boolean(state.fichaRetentionPolicy?.purge_enabled);
  if (refs.fichaRetentionTimeline) {
    const timeline = Array.isArray(state.fichaRetentionPolicy?.timeline) && state.fichaRetentionPolicy.timeline.length
      ? state.fichaRetentionPolicy.timeline
      : [
        { label: 'Fechamento: snapshot gerado' },
        { label: 'Ano 1-2: retenção ativa' },
        { label: 'Ano 3-4: auditoria legal' },
        { label: '5 anos: expiração NR-6' },
        { label: 'Purge automático (se habilitado)' },
      ];
    refs.fichaRetentionTimeline.innerHTML = timeline.map((item) => `<li>${item.label}</li>`).join('');
  }
}

async function loadRetentionPolicy() {
  if (!hasConfigurationAccess()) return;
  // Captura o erro internamente (como os loaders irmãos): chamado via
  // `void loadRetentionPolicy()` no renderAll, uma rejeição não tratada aqui
  // vira "Uncaught (in promise)" no console. Falha é não-crítica.
  try {
    const payload = await api(`/api/ficha-retention-policy?${actorQuery()}`);
    state.fichaRetentionPolicy = payload || state.fichaRetentionPolicy;
    renderRetentionPolicy();
  } catch (error) {
    console.warn('[retention-policy] erro ao carregar', error);
  }
}

function collectReportFilters() {
  const reportForm = document.getElementById('report-filter-form');
  const normalizeOptionalInt = (fieldName, value) => {
    const raw = String(value || '').trim();
    if (!raw) return '';
    if (!/^\d+$/.test(raw)) {
      throw new Error(`Filtro inválido: ${fieldName} deve ser numérico.`);
    }
    return raw;
  };
  const normalizeOptionalDate = (fieldName, value) => {
    const raw = String(value || '').trim();
    if (!raw) return '';
    if (!/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
      throw new Error(`Filtro inválido: ${fieldName} deve estar no formato AAAA-MM-DD.`);
    }
    return raw;
  };
  const values = {
    company_id: normalizeOptionalInt('company_id', reportForm?.querySelector('#report-company')?.value),
    legal_entity_id: normalizeOptionalInt('legal_entity_id', reportForm?.querySelector('#report-legal-entity')?.value),
    unit_id: normalizeOptionalInt('unit_id', reportForm?.querySelector('#report-unit')?.value),
    employee_id: normalizeOptionalInt('employee_id', reportForm?.querySelector('#report-employee')?.value),
    sector: String(reportForm?.querySelector('#report-sector')?.value || '').trim(),
    tipo_vinculo: String(reportForm?.querySelector('#report-tipo-vinculo')?.value || '').trim(),
    epi_id: normalizeOptionalInt('epi_id', reportForm?.querySelector('#report-epi')?.value),
    status: String(reportForm?.querySelector('#report-ficha-status')?.value || '').trim(),
    start_date: normalizeOptionalDate('start_date', reportForm?.querySelector('input[name="start_date"]')?.value),
    end_date: normalizeOptionalDate('end_date', reportForm?.querySelector('input[name="end_date"]')?.value)
  };
  return Object.fromEntries(Object.entries(values).filter(([, value]) => value !== ''));
}

function exportReportPdf() {
  if (!requirePermission('reports:view')) return;
  let filters;
  try {
    filters = collectReportFilters();
  } catch (error) {
    alert(error?.message || 'Filtros inválidos.');
    return;
  }
  const params = new URLSearchParams({ actor_user_id: state.user?.id || '', ...filters });
  globalThis.open(`/api/reports.pdf?${params.toString()}`, '_blank');
}

function refreshDeliveryContext({ syncUnit = false } = {}) {
  const employee = state.employees.find((item) => String(item.id) === String(document.getElementById('delivery-employee').value));
  const deliveryCompanyField = document.getElementById('delivery-company');
  const deliveryUnitFilterField = document.getElementById('delivery-unit-filter');
  const unit = state.units.find((item) => String(item.id) === String(employee?.current_unit_id || employee?.unit_id || ''));
  const linkField = document.getElementById('delivery-employee-link');
  const channelModelField = document.getElementById('delivery-employee-message-model');
  if (employee?.company_id && deliveryCompanyField) deliveryCompanyField.value = String(employee.company_id);
  let unitChanged = false;
  if (syncUnit && unit?.id && deliveryUnitFilterField && String(deliveryUnitFilterField.value || '') !== String(unit.id)) {
    deliveryUnitFilterField.value = String(unit.id);
    unitChanged = true;
  }
  if (unitChanged) {
    syncDeliveryOptions();
  }
  if (linkField) {
    const accessLink = buildEmployeeAccessLink(employee?.employee_access_token || '');
    linkField.value = accessLink;
    // Link de token permanente do colaborador — não é o link gerado de 48h,
    // portanto zera o rastreio de expiração e informa o estado.
    _deliveryEmployeeLinkExpiresAt = '';
    if (typeof setDeliveryEmployeeAccessStatus === 'function') {
      setDeliveryEmployeeAccessStatus(
        accessLink ? 'info' : 'info',
        accessLink
          ? tr('delivery.employeeAccessReady', 'Link de acesso pronto. Use os botões para gerar QR, copiar ou enviar.')
          : tr('delivery.employeeAccessHint', 'Selecione um colaborador para gerar o link de acesso (válido por 48h).'));
    }
  }
  if (channelModelField) {
    channelModelField.value = ['whatsapp', 'email'].includes(String(employee?.preferred_contact_channel || '').toLowerCase())
      ? String(employee.preferred_contact_channel).toLowerCase()
      : 'whatsapp';
  }
  document.getElementById('delivery-unit').value = unit ? `${unit.name} - ${unitTypeLabel(unit.unit_type)}` : '';
  document.getElementById('delivery-employee-code').value = employee?.employee_id_code || '';
  document.getElementById('delivery-sector').value = employee?.sector || '';
  document.getElementById('delivery-role').value = employee?.role_name || '';
  const selectedEpiId = String(document.getElementById('delivery-epi')?.value || '').trim();
  const selectedEpi = (state.deliveryEpis || []).find((item) => String(item.id) === selectedEpiId);
  if (selectedEpi && Number(selectedEpi.stock || 0) <= 0) {
    setDeliveryQrStatus('EPI selecionado sem saldo em estoque. Escolha outro item com saldo para entrega.', true);
  }
  const sizesPanel = document.getElementById('delivery-epi-sizes');
  if (sizesPanel) {
    const balances = Array.isArray(selectedEpi?.size_balances) ? selectedEpi.size_balances : [];
    if (balances.length) {
      const parts = balances.map((s) => {
        const label = [s.glove_size !== 'N/A' ? `Luva ${s.glove_size}` : '', s.size !== 'N/A' ? `Tam. ${s.size}` : '', s.uniform_size !== 'N/A' ? `Unif. ${s.uniform_size}` : ''].filter(Boolean).join(' / ');
        return label ? `<strong>${label}</strong>: ${s.quantity} un.` : '';
      }).filter(Boolean);
      sizesPanel.innerHTML = `<span style="font-weight:600;margin-right:6px;">Saldo por tamanho:</span>${parts.join('<span style="margin:0 8px;color:var(--color-text-muted)">|</span>')}`;
      sizesPanel.style.display = '';
    } else {
      sizesPanel.style.display = 'none';
    }
  }
  applyDeliveryReplacementSuggestion({ force: true });
  void loadOpenDeliveriesForCurrentPair().finally(() => syncDeliveryDevolutionOptions());
}

function normalizeSearchText(value) {
  return String(value || '')
    .normalize('NFD')
    .replaceAll(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

function filteredLinkedEmployees() {
  const companyId = refs.userForm?.elements.company_id?.value || state.user?.company_id || '';
  const searchValue = normalizeSearchText(refs.userLinkedEmployeeSearch?.value || '');
  return filterByUserCompany(state.employees).filter((item) => {
    if (companyId && String(item.company_id) !== String(companyId)) return false;
    if (!searchValue) return true;
    const haystack = normalizeSearchText(`${item.employee_id_code || ''} ${item.name || ''} ${item.role_name || ''}`);
    return haystack.includes(searchValue);
  });
}

function renderLinkedEmployeeSearchResults() {
  const box = refs.userLinkedEmployeeResults;
  if (!box) return;
  const employees = filteredLinkedEmployees();
  if (!employees.length) {
    box.innerHTML = `<div class="summary-item">${tr('user.noEmployeeFound', 'Nenhum colaborador encontrado para o filtro informado.')}</div>`;
    return;
  }
  box.innerHTML = employees.slice(0, 8).map((item) => {
    const subtitle = `${item.employee_id_code} - ${item.role_name || 'Sem funÃÂ§ÃÂ£o'} ${item.name}`;
    return `<button type="button" class="ghost" data-user-linked-pick="${item.id}">${subtitle}</button>`;
  }).join('');
}

function populateLinkedEmployeeOptions() {
  const field = document.getElementById('user-linked-employee');
  if (!field) return;
  const employees = filteredLinkedEmployees();
  const canUseWithoutLink = ['master_admin', 'general_admin'].includes(state.user?.role);
  const firstOption = canUseWithoutLink ? `<option value="">${tr('user.noLink', 'Sem vínculo')}</option>` : '';
  const employeeOptions = employees.map((item) => `<option value="${item.id}">${item.employee_id_code} - ${item.name}</option>`).join('');
  field.innerHTML = `${firstOption}${employeeOptions}`;
  if (!canUseWithoutLink && !field.value && employees.length) field.value = String(employees[0].id);
  renderLinkedEmployeeSearchResults();
}

function setManualEmployeeFieldsEnabled(enabled) {
  const editableFields = [
    'employee_id_code',
    'employee_role_name',
    'employee_sector',
    'employee_schedule_type',
    'employee_admission_date',
    'employee_unit_id'
  ];
  editableFields.forEach((name) => {
    const input = refs.userForm?.elements?.[name];
    if (!input) return;
    if (input.tagName === 'SELECT') input.disabled = !enabled;
    else input.readOnly = !enabled;
  });
}

function syncUserEmployeeLink() {
  const selectedRole = String(refs.userForm?.elements?.role?.value || '').trim();
  const linkedId = refs.userForm?.elements.linked_employee_id?.value;
  const companyId = refs.userForm?.elements.company_id?.value || state.user?.company_id || '';
  const unitField = refs.userForm?.elements.employee_unit_id;
  const unitFieldLabel = unitField?.closest('label');
  
  if (unitField) {
    const units = filterByUserCompany(state.units).filter((item) => !companyId || String(item.company_id) === String(companyId));
    const unitOptions = units.map((item) => `<option value="${item.id}">${item.name} - ${unitTypeLabel(item.unit_type)}</option>`).join('');
    unitField.innerHTML = `<option value="">Selecione</option>${unitOptions}`;
  }
  
  const employee = state.employees.find((item) => String(item.id) === String(linkedId || ''));
  const canManual = ['master_admin', 'general_admin'].includes(state.user?.role);
  const isWithoutLink = !linkedId;
  const isOperationalRole = ['admin', 'user'].includes(selectedRole);

  populateUserEmployeeFields(employee, isWithoutLink, canManual, unitField);
  
  const allowManualEmployeeCreation = isWithoutLink && canManual && selectedRole === 'employee';
  if (isOperationalRole && !employee && refs.userForm?.elements.linked_employee_id) {
    refs.userForm.elements.linked_employee_id.value = '';
  }
  if (unitFieldLabel) {
    unitFieldLabel.style.display = allowManualEmployeeCreation ? '' : 'none';
  }
  setManualEmployeeFieldsEnabled(allowManualEmployeeCreation);
}

function populateUserEmployeeFields(employee, isWithoutLink, canManual, unitField) {
  if (employee) {
    refs.userForm.elements.employee_id_code.value = employee.employee_id_code || '';
    refs.userForm.elements.employee_role_name.value = employee.role_name || '';
    refs.userForm.elements.employee_sector.value = employee.sector || '';
    refs.userForm.elements.employee_schedule_type.value = employee.schedule_type || '';
    refs.userForm.elements.employee_admission_date.value = employee.admission_date || '';
    if (unitField) unitField.value = String(employee.unit_id || '');
    if (employee?.company_id) refs.userForm.elements.company_id.value = employee.company_id;
  } else if (isWithoutLink && !canManual) {
    refs.userForm.elements.linked_employee_id.value = '';
  } else {
    clearUserEmployeeFields(unitField);
  }
}

function clearUserEmployeeFields(unitField) {
  refs.userForm.elements.employee_id_code.value = '';
  refs.userForm.elements.employee_role_name.value = '';
  refs.userForm.elements.employee_sector.value = '';
  refs.userForm.elements.employee_schedule_type.value = '';
  refs.userForm.elements.employee_admission_date.value = '';
  if (unitField) unitField.value = '';
}

function renderAll() {
  refs.currentDate.textContent = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'full' }).format(new Date());
  applySpaNavigationVisibility();
  applyPhase3UiVisibility();
  applyRoleVisibility();
  renderPlatformBrand();
  populateRoleOptions();
  populateUserFilters();
  bindDependentSelects();
  populateScopedSearchFilters();
  hydrateConfigurationForms();
  renderStats();
  renderAlerts();
  renderLatestDeliveries();
  renderDashboardInterativo();
  renderCompaniesSummary();
  renderCompanies();
  renderCompanyDetails();
  fillCommercialSettingsForm();
  if (canAccessCommercialArea()) fillCommercialForm();
  populateCommercialActors();
  renderCommercialStats();
  renderCommercialSummary();
  renderCommercialAlerts();
  renderCommercialExpiring();
  renderCommercialHistory();
  renderTables();
  renderLegalEntities();
  syncLegalEntityCompanyField();
  renderOutsourcedCompanies();
  if (canManagePurchaseFunctions()) void loadPurchaseFunctions();
  renderLowStock();
  renderRequests();
  renderStockEpis();
  setupStockMovementsReport();
  renderFicha();
  if (hasConfigurationAccess()) void loadFichaConfig();
  if (canConfigureMyCompany()) void loadMyCompanyCard(true);
  if (hasConfigurationAccess()) void loadRetentionPolicy();
  if (hasConfigurationAccess()) void loadComprasPurchaseConfig();
  if (canViewConfiguration()) void loadFichaAuditLogs();
  if (hasPermission('reports:view')) void renderReports();
  refreshDeliveryContext();
  syncUserFormAccess();
  syncStructuralCrudAccess();
  markRequiredFieldLabels();
  updateBootstrapDegradedUi();
  if (hasPermission('purchase_requests:view')) {
    // Buyer/approver: pré-carrega seus próprios vínculos para filtrar selects de unidade
    if (['buyer','approver'].includes(state.user?.role)) {
      api(`/api/user-unit-links?user_id=${state.user.id}`)
        .then(res => { _unitLinksCache = (res.items || []).map(lk => ({ unit_id: lk.unit_id })); })
        .catch(() => {})
        .finally(() => initPurchaseModule());
    } else {
      initPurchaseModule();
    }
  }
  const preferredView = isSpaNavigationEnabled() ? resolveViewFromLocation() : '';
  const nextView = preferredView && VIEW_PERMISSIONS[preferredView] ? preferredView : defaultView();
  showView(nextView, { partial: isSpaNavigationEnabled(), historyMode: isSpaNavigationEnabled() ? 'replace' : null });

}

function syncStructuralCrudAccess() {
  const canManageStructuralRecords = ['general_admin', 'registry_admin'].includes(state.user?.role);
  const unitSubmit = document.querySelector('#unit-form button[type="submit"]');
  const epiSubmit = document.querySelector('#epi-form button[type="submit"]');
  if (unitSubmit) {
    unitSubmit.style.display = canManageStructuralRecords ? '' : 'none';
    unitSubmit.disabled = !canManageStructuralRecords;
  }
  if (epiSubmit) {
    epiSubmit.style.display = canManageStructuralRecords ? '' : 'none';
    epiSubmit.disabled = !canManageStructuralRecords;
  }
}

async function handleLogin(event) {
  event.preventDefault();
  setLoginMessage('');

  const submitButton = refs.loginForm?.querySelector('button[type="submit"]');

  try {
    const username = String(refs.loginUsername?.value || '').trim();
    const password = String(refs.loginPassword?.value || '');

    if (!username || !password.trim()) {
      setLoginMessage('Informe Usuário e senha para entrar.', true);
      return;
    }

    if (submitButton) submitButton.disabled = true;

    console.info('[auth] Tentativa de login', { username });

    const totpCode = String(document.getElementById('login-totp')?.value || '').trim();
    const loginBody = { username, password };
    if (totpCode) loginBody.totp_code = totpCode;
    const payload = await api('/api/login', {
      method: 'POST',
      body: JSON.stringify(loginBody)
    });

    if (!payload?.user || !payload?.token) {
      throw new Error('Falha ao autenticar: resposta inválida do servidor.');
    }

    console.info('[auth] Login concluído com sucesso', {
      user_id: payload.user.id,
      username: payload.user.username
    });

    saveSession(payload.user, payload.permissions || [], payload.token || '');
    setPasswordChangeRequired(Boolean(payload.require_password_change));
    if (state.requirePasswordChange) {
      handlePasswordChangeAfterLogin(password);
      return;
    }
    try {
      await loadBootstrap();
    } catch (bootstrapError) {
      if (isBootstrapRequestError(bootstrapError)) {
        setBootstrapDegraded(bootstrapError);
        console.warn('[auth] fallback para login manual ativado');
        console.warn('[auth] bootstrap falhou após login manual, mantendo sessão ativa', bootstrapError);
        // Still render the app shell so navigation works even in degraded mode.
        // updateBootstrapDegradedUi() inside renderAll() will show the banner.
        try { renderAll(); } catch (_renderErr) { reportNonCriticalError('[auth] renderAll em modo degradado', _renderErr); }
      } else {
        const wrapped = new Error(bootstrapError?.message || 'Falha ao carregar dados iniciais após autenticação.');
        wrapped.phase = 'post_login_bootstrap';
        wrapped.status = bootstrapError?.status;
        wrapped.code = bootstrapError?.code || '';
        wrapped.payload = bootstrapError?.payload;
        throw wrapped;
      }
    }
    showScreen(true);
    void maybeShowOnboardingWizard();
  } catch (error) {
    clearBootstrapDegraded();
    clearSession();
    showScreen(false);
    console.error('[auth] Falha no login', {
      phase: error?.phase || 'authentication',
      status: error?.status,
      code: error?.code,
      payload: error?.payload
    });

    const message = getLoginErrorMessage(error);
    setLoginMessage(message, true);
    // 2FA: revela o campo de código quando o backend exige/recusa o TOTP
    const totpRow = document.getElementById('login-totp-row');
    const errorCode = String(error?.code || '').toUpperCase();
    if (totpRow && (errorCode === 'TOTP_REQUIRED' || errorCode === 'TOTP_INVALID')) {
      totpRow.style.display = '';
      document.getElementById('login-totp')?.focus();
    }
  } finally {
    if (submitButton) submitButton.disabled = false;
  }
}

function handlePasswordChangeAfterLogin(currentPassword) {
  const curField = document.getElementById('current-password');
  const newField = document.getElementById('new-password');
  const confField = document.getElementById('confirm-password');
  if (curField) curField.value = currentPassword || '';
  if (newField) newField.value = '';
  if (confField) confField.value = '';
  const changeForm = document.getElementById('password-change-form');
  const loginForm = document.getElementById('login-form');
  const recovPanel = document.getElementById('recovery-panel');
  if (loginForm) loginForm.style.display = 'none';
  if (recovPanel) recovPanel.style.display = 'none';
  if (changeForm) changeForm.style.display = 'grid';
  showScreen(false);
}

async function handleForcedPasswordChange(event) {
  event.preventDefault();
  const submitButton = event.target.querySelector('button[type="submit"]');
  try {
    if (submitButton) submitButton.disabled = true;
    const curPwd = String(document.getElementById('current-password')?.value || '').trim();
    const newPwd = String(document.getElementById('new-password')?.value || '').trim();
    const confPwd = String(document.getElementById('confirm-password')?.value || '').trim();
    if (!curPwd) throw new Error('Informe a senha atual.');
    if (!newPwd) throw new Error('Informe a nova senha.');
    if (newPwd.length < 6) throw new Error('A nova senha deve ter pelo menos 6 caracteres.');
    if (newPwd !== confPwd) throw new Error('A confirmação da nova senha nao confere.');
    await api('/api/change-password', {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user?.id, current_password: curPwd, new_password: newPwd })
    });
    setPasswordChangeRequired(false);
    if (refs.passwordChangeForm) refs.passwordChangeForm.reset();
    showScreen(true);
    await loadBootstrap();
    alert('Senha atualizada com sucesso. Bem-vindo!');
  } catch (error) {
    alert(error.message || 'Nao foi possivel atualizar a senha.');
  } finally {
    if (submitButton) submitButton.disabled = false;
  }
}
async function saveUser(event) {
  event.preventDefault();
  if (!requirePermission(state.editingUserId ? 'users:update' : 'users:create')) return;
  try {
    setUserFormFeedback('');
    const values = formValues(refs.userForm);
    values.actor_user_id = state.user.id;
    if (['general_admin', 'admin'].includes(state.user.role)) values.company_id = state.user.company_id;

    values.active = Number(values.active || 1);
    if (!String(values.company_id || '').trim()) throw new Error('Empresa Usuário.');
    if (!ROLE_LABELS[values.role]) throw new Error('Perfil inválido.');
    const noLink = !String(values.linked_employee_id || '').trim();
    if (['admin', 'user'].includes(values.role) && noLink) {
      throw new Error('Administrador Local e Gestor de EPI devem ser vinculados a um colaborador com unidade.');
    }
    if (noLink && !['master_admin', 'general_admin'].includes(state.user?.role)) {
      throw new Error('Seu perfil Não permite ví­nculo de colaborador.');
    }

    await api(state.editingUserId ? `/api/users/${state.editingUserId}` : '/api/users', { method: state.editingUserId ? 'PUT' : 'POST', body: JSON.stringify(values) });
    setUserFormFeedback(state.editingUserId ? 'Usuário atualizado com sucesso.' : 'Usuário criado com sucesso.');
    resetUserForm();
    await loadBootstrap();
  } catch (error) {
    setUserFormFeedback(error.message, true);
    alert(error.message);
  }
}

function normalizeEpiSizes(values) {
  values.glove_size = String(values.glove_size || 'N/A');
  values.size = String(values.size || 'N/A');
  values.uniform_size = String(values.uniform_size || 'N/A');
}

function setEpiValidity(values) {
  const months = parseMonthsValue(values.manufacturer_validity_months);
  values.manufacturer_validity_months = months;
  values.validity_years = 0;
  values.validity_months = months;
  values.validity_days = months * 30;
}

async function setEpiPhotoData(values, editingId) {
  const photoFile = document.getElementById('epi-photo-file')?.files?.[0];
  if (photoFile) {
    values.epi_photo_data = await fileToDataUrl(photoFile);
  } else if (editingId) {
    const currentEpi = state.epis.find((epi) => String(epi.id) === String(editingId));
    values.epi_photo_data = currentEpi?.epi_photo_data || '';
  }
}

async function prepareEpiFormValues(values, editingId, event) {
  const parsedActiveJoinventure = parseActiveJoinventureToken(values.active_joinventure);
  if (parsedActiveJoinventure.name && parsedActiveJoinventure.unit_id) {
    values.unit_id = parsedActiveJoinventure.unit_id;
  }
  if (!parsedActiveJoinventure.name && String(values.unit_id || '') === EPI_ALL_UNITS_VALUE) {
    values.unit_id = '';
  }
  values.active_joinventure = parsedActiveJoinventure.name || '';
  values.stock = 0;
  
  normalizeEpiSizes(values);
  setEpiValidity(values);
  
  values.joinventures_json = document.getElementById('epi-joinventures')?.value || '[]';
  
  if (!values.epi_photo_data && editingId) {
    await setEpiPhotoData(values, editingId);
  }
  return values;
}

function resetEpiForm(form) {
  if (form.elements.id) form.elements.id.value = '';
  const hidden = document.getElementById('epi-joinventures');
  if (hidden) hidden.value = '[]';
  if (form.elements.epi_photo_data) form.elements.epi_photo_data.value = '';
  const photoFile = document.getElementById('epi-photo-file');
  if (photoFile) photoFile.value = '';
  renderEpiPhotoPreview('');
  renderJoinventureList();
  if (form.elements.unit_id) {
    form.elements.unit_id.value = canUseEpiAllUnitsScope()
      ? EPI_ALL_UNITS_VALUE
      : (form.elements.unit_id.options[0]?.value || '');
  }
  if (form.elements.active_joinventure) form.elements.active_joinventure.value = '';
  applyEpiJoinventureRules();
  setFormSubmitLabel('epi-form', 'Salvar EPI');
}

async function saveSimpleForm(event, path, permission) {
  event.preventDefault();
  if (!requirePermission(permission)) return;
  if (event.target.dataset.submitting === '1') return;
  if (event.target.id === 'delivery-form') {
    document.dispatchEvent(new CustomEvent('epi:delivery-submit-start'));
  }
  event.target.dataset.submitting = '1';
  const submitButton = event.target.querySelector('button[type="submit"]');
  if (submitButton) submitButton.disabled = true;
  try {
    const values = formValues(event.target);
    const editingId = String(values.id || '').trim();
    if ('id' in values) delete values.id;
    
    if (event.target.id === 'epi-form') {
      await prepareEpiFormValues(values, editingId, event);
    }
    // Reenvio depois do aviso de possível duplicata por nome (ADR-0002
    // §12 item 15 do pedido) — handleOutsourcedCompanyDuplicateError arma
    // esta flag e resubmete o formulário; consumo único, nunca herda para
    // o próximo cadastro.
    if (event.target.id === 'outsourced-company-form') {
      if (event.target.dataset.confirmDuplicate === '1') values.confirm_duplicate = true;
      delete event.target.dataset.confirmDuplicate;
    }
    let deliveryHandledInBatch = false;
    if (event.target.id === 'delivery-form') {
      const companyField = document.getElementById('delivery-company');
      const unitField = document.getElementById('delivery-unit-filter');
      const epiField = document.getElementById('delivery-epi');
      const employee = selectedDeliveryEmployee();
      const isDevolution = Boolean(refs.deliveryIsDevolution?.checked);
      if (!values.company_id) values.company_id = companyField?.value || state.user?.company_id || '';
      if (!values.unit_id) values.unit_id = unitField?.value || state.user?.operational_unit_id || '';
      if (!values.epi_id) values.epi_id = epiField?.value || '';
      values.signature_data = String(values.signature_data || refs.deliverySignatureData?.value || '').trim();
      values.signature_name = String(values.signature_name || refs.deliverySignatureName?.value || employee?.name || '').trim();
      values.signature_at = String(values.signature_at || refs.deliverySignatureAt?.value || '').trim();
      values.signature_comment = String(values.signature_comment || refs.deliverySignatureComment?.value || '').trim();
      if (!values.signature_data) {
        values.signature_name = '';
        values.signature_at = '';
        values.signature_comment = '';
      }
      values.signature_name = String(values.signature_name || refs.deliverySignatureName?.value || state.user?.full_name || 'Assinatura digital').trim();
      values.signature_at = String(values.signature_at || refs.deliverySignatureAt?.value || '').trim();
      values.signature_comment = String(values.signature_comment || refs.deliverySignatureComment?.value || '').trim();
      if (isDevolution) {
        const matchedDelivery = selectedOpenDeliveryForDevolution();
        if (!matchedDelivery) throw new Error('Selecione explicitamente a entrega de origem para registrar a devolução.');
        values.delivery_id = Number(matchedDelivery.id);
        values.expected_employee_id = Number(values.employee_id);
        values.expected_epi_id = Number(values.epi_id);
        values.expected_unit_id = Number(matchedDelivery.unit_id || values.unit_id || 0);
        values.returned_date = String(refs.deliveryReturnedDate?.value || '').trim() || new Date().toISOString().split('T')[0];
        values.condition = String(refs.deliveryReturnCondition?.value || 'usable').trim() || 'usable';
        values.destination = String(refs.deliveryReturnDestination?.value || 'stock').trim() || 'stock';
        values.reason = '';
        values.notes = String(values.notes || '').trim();
      } else {
        const selectedEmployeeId = normalizeSessionEmployeeId(values.employee_id || '');
        if (!selectedEmployeeId) throw new Error('Selecione um colaborador para registrar a entrega.');
        const sessionItems = Array.isArray(qrScannerState.scanSession) ? qrScannerState.scanSession.slice() : [];
        if (!sessionItems.length) {
          values.stock_item_id = Number(document.getElementById('delivery-stock-item-id')?.value || 0);
          values.stock_qr_code = String(document.getElementById('delivery-stock-qr-code')?.value || '').trim();
          values.quantity = 1;
          if (!values.stock_item_id || !values.stock_qr_code) {
            throw new Error(tr('delivery.readQrBeforeSubmit', 'Leia e valide ao menos um QR antes de clicar em "Registrar entrega".'));
          }
        } else {
          const sessionEmployeeIds = new Set(
            sessionItems
              .map((item) => normalizeSessionEmployeeId(item?.session_employee_id || ''))
              .filter(Boolean)
          );
          const sessionEmployeeId = normalizeSessionEmployeeId(qrScannerState.sessionEmployeeId || '') || (sessionEmployeeIds.size === 1 ? Array.from(sessionEmployeeIds)[0] : '');
          if (sessionEmployeeId && sessionEmployeeId !== selectedEmployeeId) {
            throw new Error('A sessão de leitura pertence a outro colaborador. Limpe a lista e refaça a leitura.');
          }
          if (!sessionEmployeeId && sessionEmployeeIds.size > 1) {
            throw new Error('A sessão de leitura está inconsistente entre colaboradores. Limpe a lista e refaça a leitura.');
          }
          for (const item of sessionItems) {
            const payloadValues = {
              ...values,
              actor_user_id: Number(state.user?.id || 0),
              stock_item_id: Number(item.id || 0),
              stock_qr_code: String(item.qr_code_value || '').trim(),
              epi_id: Number(item.epi_id || values.epi_id || 0),
              quantity: 1
            };
            if (!payloadValues.actor_user_id || !payloadValues.stock_item_id || !payloadValues.stock_qr_code || !payloadValues.epi_id) {
              throw new Error('Sessão contém item inválido. Limpe a lista e repita a leitura.');
            }
            await api('/api/deliveries', { method: 'POST', body: JSON.stringify(payloadValues) });
          }
          deliveryHandledInBatch = true;
          resetDeliveryQrSession();
          clearDeliveryStockItemSelection();
          setDeliveryQrStatus('Entrega registrada com sucesso para todos os itens validados na sessão.');
        }
      }
    }
    
    values.actor_user_id = state.user.id;
    if (state.user?.role !== 'master_admin' && values.company_id !== undefined && !values.company_id) values.company_id = state.user.company_id;
    const updatePermission = event.target.dataset.updatePermission || permission;
    if (editingId && !requirePermission(updatePermission)) return;
    let requestPath = editingId ? `${path}/${editingId}` : path;
    if (event.target.id === 'delivery-form' && refs.deliveryIsDevolution?.checked) {
      requestPath = '/api/devolutions';
      delete values.company_id;
      delete values.unit_id;
      delete values.epi_id;
      delete values.quantity;
      delete values.quantity_label;
      delete values.delivery_date;
      delete values.next_replacement_date;
      delete values.stock_item_id;
      delete values.stock_qr_code;
      delete values.return_condition;
      delete values.return_destination;
      delete values.is_devolution;
    }
    let payload = null;
    if (!deliveryHandledInBatch) {
      payload = await api(requestPath, { method: editingId ? 'PUT' : 'POST', body: JSON.stringify(values) });
    }
    
    if (event.target.id === 'employee-form' && payload?.employee_access_link) {
      await handleEmployeeFormSuccess(payload.employee_access_link);
    }
    
    event.target.reset();
    handleFormReset(event.target);
    if (event.target.id === 'delivery-form') {
      document.dispatchEvent(new CustomEvent('epi:delivery-submit-success'));
    }
    
    await loadBootstrap();
    // Terceirizados e Prestadores não vem no bootstrap (módulo opt-in) —
    // recarrega a lista à parte, mesma lógica de loadOutsourcedCompanies().
    if (event.target.id === 'outsourced-company-form') {
      await loadOutsourcedCompanies();
    }
    // Cadastro de Colaboradores simplificado: deriva de state.employees, que
    // loadBootstrap() acima já atualizou — só falta re-renderizar a tabela
    // (o reset do modo de edição já roda em handleFormReset, como no
    // outsourced-company-form).
    if (event.target.id === 'outsourced-employee-form') {
      renderOutsourcedEmployees();
    }
  } catch (error) {
    if (event.target.id === 'delivery-form') {
      document.dispatchEvent(new CustomEvent('epi:delivery-submit-error', { detail: { message: String(error?.message || '') } }));
    }
    if (event.target.id === 'outsourced-company-form' && await handleOutsourcedCompanyDuplicateError(error, event.target)) {
      return;
    }
    alert(error.message);
  } finally {
    event.target.dataset.submitting = '0';
    if (submitButton) submitButton.disabled = false;
  }
}

async function handleEmployeeFormSuccess(accessLink) {
  try {
    await navigator.clipboard?.writeText(accessLink);
  } catch (error) {
    console.warn('[employee-form] Falha ao copiar link para area de transferencia:', error);
  }
  alert(`Colaborador cadastrado com sucesso.\nLink de acesso externo:\n${accessLink}`);
}

function handleFormReset(form) {
  if (form.id === 'epi-form') {
    resetEpiForm(form);
  } else if (form.id === 'legal-entity-form') {
    setFormSubmitLabel('legal-entity-form', tr('legalEntity.save', 'Salvar CNPJ'));
    if (form.elements.active) form.elements.active.value = '1';
    setLegalEntityFormMode('create');
    syncLegalEntityCompanyField();
  } else if (form.id === 'outsourced-company-form') {
    setFormSubmitLabel('outsourced-company-form', tr('outsourcedCompany.save', 'Salvar Empresa'));
    setOutsourcedCompanyFormMode('create');
    syncOutsourcedCompanyUnitOptions();
    applyOutsourcedCompanyCorporateLock(null);
  } else if (form.id === 'outsourced-employee-form') {
    setFormSubmitLabel('outsourced-employee-form', tr('outsourcedCompany.employeeSave', 'Salvar Colaborador'));
    setOutsourcedEmployeeFormMode('create');
    syncOutsourcedEmployeeUnitOptions();
  } else if (form.id === 'unit-form') {
    setFormSubmitLabel('unit-form', 'Salvar unidade');
  } else if (form.id === 'employee-form') {
    setFormSubmitLabel('employee-form', 'Salvar colaborador');
    // Volta ao modo de admissão: o CNPJ é escolhível de novo.
    setEmployeeLegalEntityLock('', false);
    const tipoVinculoEl = document.getElementById('employee-tipo-vinculo');
    if (tipoVinculoEl) tipoVinculoEl.value = 'CLT';
    syncEmpresaOrigemVisibility();
  } else if (form.id === 'delivery-form') {
    form.elements.delivery_date.value = new Date().toISOString().split('T')[0];
    form.elements.next_replacement_date.value = new Date().toISOString().split('T')[0];
    form.elements.next_replacement_date.dataset.autoSuggested = '1';
    if (refs.deliveryReturnedDate) refs.deliveryReturnedDate.value = new Date().toISOString().split('T')[0];
    if (refs.deliveryIsDevolution) refs.deliveryIsDevolution.checked = false;
    if (refs.deliveryDevolutionFields) refs.deliveryDevolutionFields.style.display = 'none';
    state.deliveryReturnCandidates = [];
    state.deliveryReturnScopeKey = '';
    renderDeliveryReturnCandidates([]);
    resetDeliverySignatureDraft();
    if (refs.deliverySignatureData) refs.deliverySignatureData.value = '';
    if (refs.deliverySignatureName) refs.deliverySignatureName.value = '';
    if (refs.deliverySignatureAt) refs.deliverySignatureAt.value = '';
    if (refs.deliverySignatureComment) refs.deliverySignatureComment.value = '';
    if (refs.deliverySignatureStatus) refs.deliverySignatureStatus.textContent = tr('delivery.signaturePending', 'Assinatura pendente.');
    clearDeliveryStockItemSelection();
    resetDeliveryQrSession();
    syncDeliveryDevolutionOptions();
    applyDeliveryReplacementSuggestion({ force: true });
  }
}

function printStockLabels(qrItems, copies = 1) {
  if (!Array.isArray(qrItems) || !qrItems.length) return;
  const repeat = Math.max(1, Number(copies || 1));
  const blocks = qrItems.flatMap((item) => Array.from({ length: repeat }).map(() => `
    <div class="label">
      <img src="${qrCodeImageUrl(JSON.stringify({ type: 'stock_item', id: Number(item.stock_item_id || 0), code: String(item.qr_code_value || '') }))}" alt="QR item estoque">
      <div><strong>${item.epi_name}</strong></div>
      <div>Tamanho-Luvas: ${item.glove_size || 'N/A'}</div>
      <div>Etiqueta: ${item.label_measure || 'unidade'} | ${item.label_print_format || '-'}</div>
      <div>Impressora: ${item.label_printer_name || '-'}</div>
      <div>Reimpressões: ${Number(item.reprint_count || 0)}</div>
      <div>Tamanho Uniforme: ${item.uniform_size || 'N/A'}</div>
      <div>Tamanho: ${item.size || 'N/A'}</div>
      <div>ID: ${item.stock_item_id || '-'}</div>
      <div>${item.qr_code_value}</div>
      <div>${item.unit_name || '-'}</div>
    </div>
  `)).join('');
  const html = `<!doctype html><html><head><meta charset="utf-8"><title>Etiquetas EPI</title><style>body{font-family:Arial,sans-serif;padding:12px}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}.label{border:1px dashed var(--color-border);padding:8px;text-align:center;font-size:12px}img{width:110px;height:110px}</style></head><body><div class="grid">${blocks}</div></body></html>`;
  if (!openAndPrintPopup(html)) return;
}

function setStockManufactureStatus(message, tone = 'neutral') {
  const status = document.getElementById('stock-manufacture-status');
  if (!status) return;
  status.textContent = String(message || '');
  status.classList.remove('success', 'error');
  if (tone === 'success') status.classList.add('success');
  if (tone === 'error') status.classList.add('error');
}

function resetStockManufactureCaptureState() {
  const dateField = document.getElementById('stock-manufacture-date');
  if (dateField) {
    dateField.dataset.autoFilled = '';
    dateField.dataset.userEdited = '0';
  }
  setStockManufactureStatus('');
}

function setManufactureDateAutofillValue(dateField, value) {
  if (!dateField || !value) return;
  const alreadyAutoFilled = String(dateField.dataset.autoFilled || '').trim();
  const alreadyEdited = dateField.dataset.userEdited === '1';
  const canOverride = !alreadyEdited || !dateField.value || dateField.value === alreadyAutoFilled;
  if (!canOverride) return;
  dateField.value = value;
  dateField.dataset.autoFilled = value;
  dateField.dataset.userEdited = '0';
}

async function handleStockManufactureCameraCapture(event) {
  const file = event?.target?.files?.[0];
  const dateField = document.getElementById('stock-manufacture-date');
  if (!file || !dateField) return;
  if (!String(file.type || '').startsWith('image/')) {
    setStockManufactureStatus('Arquivo inválido. Use uma imagem para leitura da data.', 'error');
    event.target.value = '';
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    setStockManufactureStatus('Imagem muito grande (máximo: 10MB).', 'error');
    event.target.value = '';
    return;
  }
  setStockManufactureStatus('Processando imagem da câmera...');
  try {
    const imageData = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || ''));
      reader.onerror = () => reject(new Error('Falha ao carregar imagem para OCR.'));
      reader.readAsDataURL(file);
    });
    if (!imageData) throw new Error('Imagem inválida para OCR.');
    const payload = await api('/api/stock/manufacture-date-ocr', {
      method: 'POST',
      body: JSON.stringify({
        actor_user_id: state.user.id,
        image_data: imageData
      })
    });
    const selectedDate = String(payload?.manufacture_date || '').trim();
    const confidence = Number(payload?.confidence || 0);
    if (!selectedDate) {
      setStockManufactureStatus('Não foi possível identificar a data. Revise foco/iluminação e tente novamente.', 'error');
      return;
    }
    if (confidence > 0 && confidence < 45) {
      setStockManufactureStatus('Data detectada com baixa confiança. Confirme manualmente antes de salvar.', 'error');
    }
    setManufactureDateAutofillValue(dateField, selectedDate);
    if (dateField.value === selectedDate) {
      setStockManufactureStatus('Data de fabricação identificada com sucesso.', 'success');
    } else {
      setStockManufactureStatus('Data encontrada, mas o campo já foi ajustado manualmente.', 'error');
    }
  } catch (error) {
    console.error('[stock-manufacture-ocr] Falha na leitura OCR:', error);
    const msg = isTemporaryBootstrapUnavailable(error)
      ? 'Sistema inicializando — aguarde alguns segundos e tente novamente.'
      : `Falha na captura automática: ${error.message || 'erro desconhecido'}`;
    setStockManufactureStatus(msg, 'error');
  } finally {
    event.target.value = '';
    dateField.focus();
  }
}

// Lê uma data (validade do fabricante) a partir de uma imagem, reutilizando o
// OCR de data já existente (/api/stock/manufacture-date-ocr). Retorna a data no
// formato 'YYYY-MM-DD' ou '' quando não identificada. Usado na conferência de
// recebimento (Compras) para preencher a validade por câmera.
async function readManufacturerValidityFromImage(file) {
  if (!file || !String(file.type || '').startsWith('image/')) {
    showToast('Arquivo inválido. Use uma imagem para leitura da data.', 'error');
    return '';
  }
  if (file.size > 10 * 1024 * 1024) {
    showToast('Imagem muito grande (máximo: 10MB).', 'error');
    return '';
  }
  try {
    const imageData = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || ''));
      reader.onerror = () => reject(new Error('Falha ao carregar imagem para OCR.'));
      reader.readAsDataURL(file);
    });
    if (!imageData) throw new Error('Imagem inválida para OCR.');
    const payload = await api('/api/stock/manufacture-date-ocr', {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user?.id, image_data: imageData })
    });
    const detected = String(payload?.manufacture_date || '').trim();
    const confidence = Number(payload?.confidence || 0);
    if (!detected) {
      showToast('Não foi possível identificar a data. Revise foco/iluminação e tente novamente.', 'error');
      return '';
    }
    if (confidence > 0 && confidence < 45) {
      showToast('Data detectada com baixa confiança. Confirme manualmente.', 'warning');
    } else {
      showToast('Validade do fabricante identificada com sucesso.', 'success');
    }
    return detected;
  } catch (error) {
    console.error('[conferencia-validity-ocr] Falha na leitura OCR:', error);
    showToast(`Falha na captura automática: ${error.message || 'erro desconhecido'}`, 'error');
    return '';
  }
}

async function handleStockMovementSubmit(event) {
  event.preventDefault();
  if (!requirePermission('stock:adjust')) return;
  if (event.target.dataset.submitting === '1') return;
  event.target.dataset.submitting = '1';
  const submitButton = event.target.querySelector('button[type="submit"]');
  if (submitButton) submitButton.disabled = true;
  try {
    const values = formValues(event.target);
    const companyField = document.getElementById('stock-company');
    const unitField = document.getElementById('stock-unit');
    const epiField = document.getElementById('stock-epi');
    if (!values.company_id) values.company_id = companyField?.value || state.user?.company_id || '';
    if (!values.unit_id) values.unit_id = unitField?.value || state.user?.operational_unit_id || '';
    if (!values.epi_id) values.epi_id = epiField?.value || '';
    if (!values.company_id) throw new Error('Campo obrigatório: company_id');
    if (!values.unit_id) throw new Error('Campo obrigatório: unit_id');
    if (!values.epi_id) throw new Error('Selecione um EPI disponível no estoque da unidade para continuar.');
    values.actor_user_id = state.user.id;
    const resolvedSize = resolveItemSize(values);
    if (!resolvedSize.selectedSize) {
      throw new Error('Informe ao menos um tamanho válido (Tamanho-Luvas, Tamanho ou Tamanho Uniforme) para entrada em estoque.');
    }
    values.glove_size = resolvedSize.glove_size;
    values.size = resolvedSize.size;
    values.uniform_size = resolvedSize.uniform_size;
    values.manufacture_date = String(values.manufacture_date || '').trim();
    if (!values.manufacture_date) throw new Error('Data de fabricação ação obrigatória no recebimento do estoque.');
    const printerCustomValue = String(document.getElementById('stock-label-printer-custom')?.value || '').trim();
    const formatCustomValue = String(document.getElementById('stock-label-format-custom')?.value || '').trim();
    if (values.label_printer_name === '__outro__') {
      if (!printerCustomValue) throw new Error('Informe o modelo da impressora personalizada.');
      values.label_printer_name = printerCustomValue;
    }
    if (values.label_print_format === '__personalizado__') {
      if (!formatCustomValue) throw new Error('Informe o formato de impressão personalizado.');
      values.label_print_format = formatCustomValue;
    }
    const result = await api('/api/stock/movements', { method: 'POST', body: JSON.stringify(values) });
    state.stockGeneratedLabels = result?.qr_labels || [];
    if (state.stockGeneratedLabels.length) printStockLabels(state.stockGeneratedLabels, 1);
    event.target.reset();
    event.target.elements.glove_size.value = 'N/A';
    event.target.elements.size.value = 'N/A';
    event.target.elements.uniform_size.value = 'N/A';
    event.target.elements.quantity.value = 1;
    const printerCustomField = document.getElementById('stock-label-printer-custom');
    const formatCustomField = document.getElementById('stock-label-format-custom');
    if (printerCustomField) printerCustomField.value = '';
    if (formatCustomField) formatCustomField.value = '';
    setupStockLabelCustomFields();
    resetStockManufactureCaptureState();
    await loadBootstrap();
  } catch (error) {
    alert(error.message);
  } finally {
    event.target.dataset.submitting = '0';
    if (submitButton) submitButton.disabled = false;
  }
}

// ── Estoque Bloqueado (Fase 4b/HSE) ──────────────────────────────────────────
let _blockedStockStatuses = null;

function _blockedStockContext() {
  const companyId = String(document.getElementById('stock-company')?.value || state.user?.company_id || '').trim();
  const unitId = String(document.getElementById('stock-unit')?.value || state.user?.operational_unit_id || '').trim();
  return { companyId, unitId };
}

function _renderBlockedStatusOptions(select, selected) {
  if (!select || !_blockedStockStatuses) return;
  select.innerHTML = Object.entries(_blockedStockStatuses)
    .map(([code, label]) => `<option value="${esc(code)}"${code === selected ? ' selected' : ''}>${esc(label)}</option>`)
    .join('');
}

async function loadBlockedStock() {
  const tbody = document.getElementById('blocked-stock-tbody');
  if (!tbody) return;
  const { companyId } = _blockedStockContext();
  const params = new URLSearchParams({ actor_user_id: String(state.user?.id || '') });
  if (companyId) params.set('company_id', companyId);
  const unitId = _blockedStockContext().unitId;
  if (unitId) params.set('unit_id', unitId);
  try {
    const payload = await apiWithBootstrapRetry(`/api/stock/blocked-items?${params.toString()}`);
    _blockedStockStatuses = payload.statuses || _blockedStockStatuses;
    _renderBlockedStatusOptions(document.getElementById('blocked-stock-status'));
    const items = Array.isArray(payload.items) ? payload.items : [];
    const empty = document.getElementById('blocked-stock-empty');
    if (empty) empty.style.display = items.length ? 'none' : '';
    tbody.innerHTML = items.map((item) => {
      const label = (_blockedStockStatuses || {})[item.status] || item.status;
      const opts = Object.entries(_blockedStockStatuses || {})
        .map(([code, l]) => `<option value="${esc(code)}"${code === item.status ? ' selected' : ''}>${esc(l)}</option>`).join('');
      return `<tr>
        <td>${esc(item.epi_name || '')}</td>
        <td>${esc(item.unit_name || '')}</td>
        <td>${esc(item.lot_code || '-')}</td>
        <td>${esc(item.manufacture_date || '-')}</td>
        <td><span class="badge badge-danger">${esc(label)}</span></td>
        <td>
          <select class="blocked-row-status" data-item-id="${esc(String(item.id))}" data-unit-id="${esc(String(item.unit_id))}">${opts}</select>
          <button type="button" class="ghost blocked-row-apply" data-item-id="${esc(String(item.id))}" data-unit-id="${esc(String(item.unit_id))}">${tr('stock.applyStatus', 'Aplicar')}</button>
          <button type="button" class="ghost blocked-row-unblock" data-item-id="${esc(String(item.id))}" data-unit-id="${esc(String(item.unit_id))}">${tr('stock.unblock', 'Desbloquear')}</button>
        </td>
      </tr>`;
    }).join('');
  } catch (error) {
    reportNonCriticalError('[blocked-stock] falha ao carregar', error);
  }
}

async function _postStockItemStatus({ stockItemId, qrCode, unitId, newStatus, reason }) {
  const { companyId } = _blockedStockContext();
  return api('/api/stock/items/status', {
    method: 'POST',
    body: JSON.stringify({
      actor_user_id: state.user?.id,
      company_id: companyId || undefined,
      unit_id: unitId,
      stock_item_id: stockItemId || undefined,
      qr_code: qrCode || undefined,
      new_status: newStatus,
      reason: reason || '',
    }),
  });
}

function _setBlockFeedback(feedback, message, kind) {
  if (!feedback) return;
  feedback.textContent = message;
  feedback.style.color = kind === 'error'
    ? 'var(--color-danger)'
    : (kind === 'success' ? 'var(--color-success)' : '');
}

async function blockStockItem() {
  const qr = String(document.getElementById('blocked-stock-qr')?.value || '').trim();
  const status = String(document.getElementById('blocked-stock-status')?.value || '').trim();
  const reason = String(document.getElementById('blocked-stock-reason')?.value || '').trim();
  // unitId é opcional: o backend localiza o item pelo QR na empresa e deriva a
  // unidade do próprio item. Enviamos a unidade só como dica quando selecionada.
  const { unitId } = _blockedStockContext();
  const feedback = document.getElementById('blocked-stock-feedback');
  if (!qr) { _setBlockFeedback(feedback, tr('stock.blockedNeedQr', 'Bipe/digite o QR do item.'), 'error'); return; }
  if (!status) { _setBlockFeedback(feedback, tr('stock.blockedNeedStatus', 'Selecione o status de bloqueio.'), 'error'); return; }
  const btn = document.getElementById('blocked-stock-block-btn');
  if (btn) btn.disabled = true;
  _setBlockFeedback(feedback, tr('stock.loading', 'Processando...'), '');
  try {
    await _postStockItemStatus({ qrCode: qr, unitId: unitId || undefined, newStatus: status, reason });
    _setBlockFeedback(feedback, tr('stock.blockedDone', 'Item bloqueado.'), 'success');
    document.getElementById('blocked-stock-qr').value = '';
    document.getElementById('blocked-stock-reason').value = '';
    await loadBlockedStock();
  } catch (error) {
    _setBlockFeedback(feedback, error.message || tr('stock.blockedFailed', 'Não foi possível bloquear o item.'), 'error');
  } finally {
    if (btn) btn.disabled = false;
  }
}

function bindBlockedStockUi() {
  if (globalThis.__EPI_BLOCKED_STOCK_BOUND__) return;
  globalThis.__EPI_BLOCKED_STOCK_BOUND__ = true;
  bindAppListener(document.getElementById('blocked-stock-block-btn'), 'click', () => { void blockStockItem(); });
  bindAppListener(document.getElementById('blocked-stock-refresh'), 'click', () => { void loadBlockedStock(); });
  bindAppListener(document.getElementById('blocked-stock-tbody'), 'click', (event) => {
    const btn = event.target?.closest?.('.blocked-row-apply, .blocked-row-unblock');
    if (!btn) return;
    const itemId = btn.getAttribute('data-item-id');
    const unitId = btn.getAttribute('data-unit-id');
    const isUnblock = btn.classList.contains('blocked-row-unblock');
    const rowStatus = btn.closest('tr')?.querySelector('.blocked-row-status')?.value || '';
    const newStatus = isUnblock ? 'in_stock' : rowStatus;
    void (async () => {
      try {
        await _postStockItemStatus({ stockItemId: itemId, unitId, newStatus, reason: '' });
        await loadBlockedStock();
      } catch (error) {
        const feedback = document.getElementById('blocked-stock-feedback');
        if (feedback) feedback.textContent = error.message;
      }
    })();
  });
}

// ── Gestão de Validade (Fase 4d/HSE) ──────────────────────────────────────────
// Painel consolidado de validade: 4 indicadores clicáveis (produto/CA,
// vencido/próximo) que abrem os EPIs já filtrados, mais quebras por
// fabricante/unidade/lote com dias restantes e valor do estoque em risco.
const VALIDITY_MGMT_INDICATORS = [
  { key: 'product_expired',  validity: 'product_expired',  i18n: 'dashboard.productExpired',  fallback: 'EPIs com validade vencida',       tone: 'is-danger' },
  { key: 'product_expiring', validity: 'product_expiring', i18n: 'dashboard.productExpiring', fallback: 'EPIs próximos do vencimento',      tone: 'is-warning' },
  { key: 'ca_expired',       validity: 'ca_expired',       i18n: 'dashboard.caExpired',       fallback: 'CAs vencidos',                    tone: 'is-danger' },
  { key: 'ca_expiring',      validity: 'ca_expiring',      i18n: 'dashboard.caExpiring',      fallback: 'CAs próximos do vencimento',      tone: 'is-warning' },
];

function _validityDaysLabel(days) {
  if (days === null || days === undefined) return '—';
  const n = Number(days);
  if (n < 0) return tr('validity.overdueDays', 'vencido há {n}d').replace('{n}', String(Math.abs(n)));
  return tr('validity.inDays', 'em {n}d').replace('{n}', String(n));
}

function _renderValidityKpis(summary) {
  const host = document.getElementById('validity-mgmt-kpis');
  if (!host) return;
  host.innerHTML = VALIDITY_MGMT_INDICATORS.map((ind) => {
    const value = Number(summary?.[ind.key] || 0);
    const tone = value > 0 ? ind.tone : '';
    const label = tr(ind.i18n, ind.fallback);
    return `<button type="button" class="dashboard-kpi-card is-clickable ${tone}" data-validity="${esc(ind.validity)}" aria-label="${esc(label)}">
      <span>${esc(label)}</span><strong>${esc(String(value))}</strong>
    </button>`;
  }).join('');
}

function _renderValidityBreakdown(tbodyId, entries) {
  const tbody = document.getElementById(tbodyId);
  if (!tbody) return;
  const list = Array.isArray(entries) ? entries : [];
  tbody.innerHTML = list.map((e) => `<tr>
    <td>${esc(e.label || '—')}</td>
    <td>${esc(String(e.count || 0))}</td>
    <td>${esc(_validityDaysLabel(e.days_remaining))}</td>
    <td>${esc(formatCurrency(e.value || 0))}</td>
  </tr>`).join('');
}

async function loadValidityOverview() {
  const host = document.getElementById('validity-mgmt-kpis');
  if (!host) return;
  const { companyId, unitId } = _blockedStockContext();
  const params = new URLSearchParams({ actor_user_id: String(state.user?.id || '') });
  if (companyId) params.set('company_id', companyId);
  if (unitId) params.set('unit_id', unitId);
  try {
    const payload = await apiWithBootstrapRetry(`/api/stock/validity-overview?${params.toString()}`);
    const summary = payload.summary || {};
    _renderValidityKpis(summary);
    _renderValidityBreakdown('validity-by-manufacturer', payload.by_manufacturer);
    _renderValidityBreakdown('validity-by-unit', payload.by_unit);
    _renderValidityBreakdown('validity-by-lot', payload.by_lot);
    const valueEl = document.getElementById('validity-mgmt-value');
    if (valueEl) {
      valueEl.textContent = tr('validity.valueSummary', 'Valor do estoque em risco de perda: {v} ({n} itens).')
        .replace('{v}', formatCurrency(summary.value_at_risk || 0))
        .replace('{n}', String(summary.at_risk_total || 0));
    }
    const empty = document.getElementById('validity-mgmt-empty');
    if (empty) empty.style.display = Number(summary.at_risk_total || 0) ? 'none' : '';
  } catch (error) {
    reportNonCriticalError('[validity-mgmt] falha ao carregar', error);
  }
}

function bindValidityMgmtUi() {
  if (globalThis.__EPI_VALIDITY_MGMT_BOUND__) return;
  globalThis.__EPI_VALIDITY_MGMT_BOUND__ = true;
  bindAppListener(document.getElementById('validity-mgmt-refresh'), 'click', () => { void loadValidityOverview(); });
  bindAppListener(document.getElementById('validity-mgmt-kpis'), 'click', (event) => {
    const card = event.target?.closest?.('[data-validity]');
    if (!card) return;
    const validity = card.getAttribute('data-validity');
    if (validity && typeof globalThis.openEpisFilteredByValidity === 'function') {
      globalThis.openEpisFilteredByValidity(validity);
    }
  });
}

async function reprintStockLabelByQr() {
  const qrCode = String(document.getElementById('stock-reprint-qr')?.value || '').trim();
  if (!qrCode) return alert('Informe o código da etiqueta para reimpressão.');
  const companyId = String(document.getElementById('stock-company')?.value || state.user?.company_id || '').trim();
  const unitId = String(document.getElementById('stock-unit')?.value || state.user?.operational_unit_id || '').trim();
  if (!companyId || !unitId) return alert('Selecione empresa/unidade para reimprimir.');
  try {
    const params = new URLSearchParams({
      actor_user_id: String(state.user?.id || ''),
      company_id: companyId,
      unit_id: unitId,
      qr_code: qrCode
    });
    const lookup = await apiWithBootstrapRetry(`/api/stock/lookup-qr?${params.toString()}`);
    const item = lookup?.stock_item;
    if (!item?.id) throw new Error('Etiqueta Não encontrada.');
    const reason = prompt('Justificativa da reimpressão (Perdeu ou Rasgou):', 'Perdeu');
    if (reason === null) return;
    const normalizedReason = String(reason || '').trim().toLowerCase();
    if (!['perdeu', 'rasgou'].includes(normalizedReason)) {
      throw new Error('Justificativa inválida. Use "Perdeu" ou "Rasgou".');
    }
    const result = await apiWithBootstrapRetry('/api/stock/labels/reprint', {
      method: 'POST',
      body: JSON.stringify({
        actor_user_id: state.user.id,
        company_id: Number(companyId),
        stock_item_id: Number(item.id),
        reason_code: normalizedReason
      })
    });
    const label = result?.label || null;
    if (!label?.qr_code_value || !label?.stock_item_id) {
      throw new Error('Reimpressão concluída sem dados da etiqueta. Tente novamente.');
    }
    printStockLabels([label], 1);
    alert(`Etiqueta reimpressa. Total de Reimpressões: ${Number(label?.reprint_count || 0)}.`);
  } catch (error) {
    const rawMessage = String(error?.message || '').trim();
    const loweredMessage = rawMessage.toLowerCase();
    if (loweredMessage.includes('503') || loweredMessage.includes('service unavailable') || loweredMessage.includes('temporariamente indisponível')) {
      alert('Serviço de reimpressão temporariamente indisponível (503). Tente novamente em instantes.');
      return;
    }
    alert(rawMessage || 'Não foi possível reimprimir a etiqueta.');
  }
}

async function saveEmployeeMovement(event) {
  event.preventDefault();
  if (!requirePermission('employees:transfer')) return;
  try {
    const values = formValues(event.target);
    values.actor_user_id = state.user.id;
    await api('/api/employee-unit-movements', { method: 'POST', body: JSON.stringify(values) });
    event.target.reset();
    await loadBootstrap();
  } catch (error) {
    alert(error.message);
  }
}

function syncUserFilters() {
  state.userFilters.company_id = refs.userFilterCompany.value;
  state.userFilters.role = refs.userFilterRole.value;
  state.userFilters.active = refs.userFilterStatus.value;
  state.userFilters.search = refs.userFilterSearch.value.trim().toLowerCase();
  renderTables();
}


// ═══════════════════════════════════════════════════════
// FICHA DE EPI — configuracao e geracao
// ═══════════════════════════════════════════════════════


// ── Minha Empresa (Configurações) + assistente de implantação ────────────────
// A empresa contratante é configurada pelo Administrador Geral (Owner da
// tenant). O backend deriva a empresa do usuário autenticado — o frontend
// nunca envia company_id/tenant_id para estas rotas.

const MY_COMPANY_IMAGE_TYPES = {
  logo_type: ['image/png', 'image/jpeg', 'image/svg+xml'],
  favicon_type: ['image/png', 'image/svg+xml'],
  login_logo_type: ['image/png', 'image/svg+xml']
};
const MY_COMPANY_COLOR_DEFAULTS = { primary_color: '#1565C0', secondary_color: '#42A5F5', accent_color: '#FF6F00' };

function canConfigureMyCompany() {
  return Boolean(state.user) && hasPermission('company_settings:update');
}

function normalizeHexColor(value, fallback) {
  const v = String(value || '').trim();
  if (/^#[0-9a-fA-F]{6}$/.test(v)) return v;
  if (/^#[0-9a-fA-F]{3}$/.test(v)) return '#' + v.slice(1).split('').map((c) => c + c).join('');
  return fallback;
}

function myCompanyThemeMode(company) {
  try { return JSON.parse(company?.theme_json || '{}').mode || 'auto'; } catch { return 'auto'; }
}

function fillMyCompanyFields(container, company) {
  if (!container || !company) return;
  container.querySelectorAll('[data-mc-field]').forEach((field) => {
    const name = field.dataset.mcField;
    if (name === 'theme_mode') { field.value = myCompanyThemeMode(company); return; }
    if (field.type === 'color') {
      field.value = normalizeHexColor(company[name], MY_COMPANY_COLOR_DEFAULTS[name] || '#1565C0');
      return;
    }
    field.value = company[name] ?? '';
  });
  container.querySelectorAll('[data-mc-preview]').forEach((preview) => {
    renderMyCompanyImagePreview(container, preview.dataset.mcPreview);
  });
}

function renderMyCompanyImagePreview(container, name) {
  const preview = container.querySelector(`[data-mc-preview="${name}"]`);
  if (!preview) return;
  const hidden = container.querySelector(`[data-mc-field="${name}"]`);
  const value = hidden?.value || '';
  preview.innerHTML = `<div class="logo-preview-card">${companyLogoMarkup({ name: 'Imagem', logo_type: value }, 'company-logo company-logo-lg')}<span>${value ? 'Imagem carregada' : 'Imagem padrão em uso'}</span></div>`;
}

function collectMyCompanyFields(container) {
  const values = {};
  if (!container) return values;
  container.querySelectorAll('[data-mc-field]').forEach((field) => {
    const name = field.dataset.mcField;
    if (name === 'theme_mode') {
      values.theme_json = JSON.stringify({ mode: field.value || 'auto' });
      return;
    }
    values[name] = String(field.value || '').trim();
  });
  return values;
}

function wireMyCompanyImageInputs(container) {
  if (!container) return;
  container.querySelectorAll('[data-mc-image]').forEach((input) => {
    if (input.dataset.mcWired) return;
    input.dataset.mcWired = '1';
    bindAppListener(input, 'change', async () => {
      const name = input.dataset.mcImage;
      const file = input.files?.[0];
      const hidden = container.querySelector(`[data-mc-field="${name}"]`);
      if (!file || !hidden) return;
      if (!(MY_COMPANY_IMAGE_TYPES[name] || []).includes(file.type)) {
        alert('Formato de imagem não suportado para este campo.');
        input.value = '';
        return;
      }
      try {
        hidden.value = name === 'logo_type' ? await fileToJpegDataUrl(file) : await fileToDataUrl(file);
        renderMyCompanyImagePreview(container, name);
      } catch (error) {
        alert(error.message);
        input.value = '';
      }
    });
  });
}

async function loadMyCompany(force = false) {
  if (!canConfigureMyCompany()) return null;
  if (state.myCompany && !force) return state.myCompany;
  const payload = await api(`/api/my-company?${actorQuery()}`);
  state.myCompany = payload.company || null;
  return state.myCompany;
}

function renderMyCompanyReadonly(company) {
  const box = document.getElementById('my-company-readonly');
  if (!box || !company) return;
  box.innerHTML = `<strong>Contrato (somente leitura)</strong><span>Plano: ${company.plan_name || '-'} · Limite de usuários: ${company.user_limit || '-'} · Licença: ${company.license_status || '-'}</span>`;
}

async function loadMyCompanyCard(force = false) {
  const form = document.getElementById('my-company-form');
  if (!form || !canConfigureMyCompany()) return;
  try {
    const company = await loadMyCompany(force);
    if (!company) return;
    fillMyCompanyFields(form, company);
    renderMyCompanyReadonly(company);
    wireMyCompanyImageInputs(form);
    if (!form.dataset.mcWired) {
      form.dataset.mcWired = '1';
      bindAppListener(form, 'submit', saveMyCompany);
      bindAppListener(document.getElementById('my-company-domain-add'), 'click', addMyCompanyDomain);
      bindAppListener(document.getElementById('my-company-domains-table'), 'click', handleMyCompanyDomainAction);
    }
    void loadMyCompanyDomains();
  } catch (error) {
    console.warn('[my-company] falha ao carregar configurações da empresa', error);
  }
}

async function saveMyCompany(event) {
  event.preventDefault();
  const form = document.getElementById('my-company-form');
  if (!form || !canConfigureMyCompany()) return;
  const feedback = document.getElementById('my-company-feedback');
  if (feedback) feedback.textContent = '';
  try {
    const values = collectMyCompanyFields(form);
    values.actor_user_id = state.user.id;
    const payload = await api('/api/my-company', { method: 'PUT', body: JSON.stringify(values) });
    state.myCompany = payload.company || state.myCompany;
    if (feedback) feedback.textContent = 'Configurações da empresa salvas com sucesso.';
    await loadBootstrap();
  } catch (error) {
    if (feedback) feedback.textContent = error.message; else alert(error.message);
  }
}

// ── Assistente de implantação (primeiro acesso do Administrador Geral) ───────

const ONBOARDING_STEP_LABELS = {
  1: 'Etapa 1 de 5 — Segurança da conta',
  2: 'Etapa 2 de 5 — Dados da empresa',
  3: 'Etapa 3 de 5 — Identidade visual',
  4: 'Etapa 4 de 5 — Domínio',
  5: 'Etapa 5 de 5 — Conclusão'
};
const ONBOARDING_LAST_STEP = 5;
let onboardingStep = 1;

function onboardingModal() { return document.getElementById('onboarding-wizard-modal'); }

function setOnboardingStep(step) {
  onboardingStep = Math.min(Math.max(step, 1), ONBOARDING_LAST_STEP);
  const modal = onboardingModal();
  if (!modal) return;
  modal.querySelectorAll('[data-onboarding-step]').forEach((panel) => {
    panel.hidden = Number(panel.dataset.onboardingStep) !== onboardingStep;
  });
  const label = document.getElementById('onboarding-step-label');
  if (label) label.textContent = ONBOARDING_STEP_LABELS[onboardingStep];
  const backBtn = document.getElementById('onboarding-back');
  if (backBtn) backBtn.style.visibility = onboardingStep === 1 ? 'hidden' : 'visible';
  const nextBtn = document.getElementById('onboarding-next');
  if (nextBtn) {
    if (onboardingStep === ONBOARDING_LAST_STEP) nextBtn.textContent = 'Ir para o dashboard';
    else if (onboardingStep === 1) nextBtn.textContent = 'Continuar';
    else nextBtn.textContent = 'Salvar e continuar';
  }
  if (onboardingStep === 1) void refreshOnboarding2faStatus();
}

async function maybeShowOnboardingWizard() {
  if (!canConfigureMyCompany()) return;
  try {
    const company = await loadMyCompany(true);
    if (!company || Number(company.onboarding_completed ?? 1) === 1) return;
    const modal = onboardingModal();
    if (!modal) return;
    fillMyCompanyFields(modal, company);
    wireMyCompanyImageInputs(modal);
    wireOnboardingButtons();
    setOnboardingStep(1);
    openModal(modal);
  } catch (error) {
    console.warn('[onboarding] não foi possível verificar o assistente de implantação', error);
  }
}

function wireOnboardingButtons() {
  const modal = onboardingModal();
  if (!modal || modal.dataset.mcWired) return;
  modal.dataset.mcWired = '1';
  bindAppListener(document.getElementById('onboarding-later'), 'click', () => closeModal(modal));
  bindAppListener(document.getElementById('onboarding-back'), 'click', () => setOnboardingStep(onboardingStep - 1));
  bindAppListener(document.getElementById('onboarding-next'), 'click', advanceOnboardingStep);
  bindAppListener(document.getElementById('onboarding-2fa-setup'), 'click', startOnboarding2faSetup);
  bindAppListener(document.getElementById('onboarding-2fa-enable'), 'click', confirmOnboarding2fa);
}

// ── 2FA na etapa de segurança do assistente ──────────────────────────────────

async function refreshOnboarding2faStatus() {
  const statusBox = document.getElementById('onboarding-2fa-status');
  const setupBtn = document.getElementById('onboarding-2fa-setup');
  if (!statusBox) return;
  try {
    const payload = await api(`/api/auth/2fa/status?${actorQuery()}`);
    const enabled = Boolean(payload?.enabled);
    statusBox.innerHTML = enabled
      ? '<strong>2FA ativo</strong><span>Sua conta exige o código do autenticador a cada login.</span>'
      : '<strong>2FA desativado</strong><span>Ative para proteger o acesso de Administrador Geral.</span>';
    if (setupBtn) setupBtn.style.display = enabled ? 'none' : '';
    const panel = document.getElementById('onboarding-2fa-panel');
    if (panel && enabled) panel.hidden = true;
  } catch (error) {
    statusBox.textContent = 'Não foi possível consultar o status do 2FA.';
  }
}

async function startOnboarding2faSetup() {
  const feedback = document.getElementById('onboarding-feedback');
  try {
    const payload = await api('/api/auth/2fa/setup', { method: 'POST', body: JSON.stringify({ actor_user_id: state.user.id }) });
    const panel = document.getElementById('onboarding-2fa-panel');
    const secretEl = document.getElementById('onboarding-2fa-secret');
    const uriEl = document.getElementById('onboarding-2fa-uri');
    if (secretEl) secretEl.textContent = payload?.secret || '';
    if (uriEl) uriEl.textContent = payload?.otpauth_uri || '';
    if (panel) panel.hidden = false;
    document.getElementById('onboarding-2fa-code')?.focus();
  } catch (error) {
    if (feedback) feedback.textContent = error.message; else alert(error.message);
  }
}

async function confirmOnboarding2fa() {
  const feedback = document.getElementById('onboarding-feedback');
  try {
    const code = String(document.getElementById('onboarding-2fa-code')?.value || '').trim();
    await api('/api/auth/2fa/enable', { method: 'POST', body: JSON.stringify({ actor_user_id: state.user.id, totp_code: code }) });
    if (feedback) feedback.textContent = 'Autenticação em duas etapas ativada com sucesso.';
    await refreshOnboarding2faStatus();
  } catch (error) {
    if (feedback) feedback.textContent = error.message; else alert(error.message);
  }
}

// ── Domínios da tenant (Minha Empresa) ───────────────────────────────────────

async function loadMyCompanyDomains() {
  const table = document.getElementById('my-company-domains-table');
  if (!table || !canConfigureMyCompany()) return;
  try {
    const payload = await api(`/api/my-company/domains?${actorQuery()}`);
    renderMyCompanyDomains(Array.isArray(payload?.domains) ? payload.domains : []);
  } catch (error) {
    table.innerHTML = `<tr><td colspan="5">${error.message}</td></tr>`;
  }
}

function domainStatusLabel(status) {
  return { pending: 'Pendente', verified: 'Verificado', failed: 'Falhou', active: 'Ativo' }[status] || status || '-';
}

function renderMyCompanyDomains(domains) {
  const table = document.getElementById('my-company-domains-table');
  const instructions = document.getElementById('my-company-domain-instructions');
  if (!table) return;
  table.innerHTML = domains.map((item) => {
    const primaryMark = Number(item.is_primary) === 1 ? ' <strong>(principal)</strong>' : '';
    const actions = [];
    if (item.verification_status !== 'verified') {
      actions.push(`<button class="ghost" type="button" data-domain-verify="${item.id}">Verificar</button>`);
    } else if (Number(item.is_primary) !== 1) {
      actions.push(`<button class="ghost" type="button" data-domain-primary="${item.id}">Tornar principal</button>`);
    }
    actions.push(`<button class="ghost" type="button" data-domain-delete="${item.id}">Remover</button>`);
    return `<tr><td>${item.full_host}${primaryMark}</td><td>${item.type_label}</td>` +
      `<td>${domainStatusLabel(item.verification_status)}</td><td>${domainStatusLabel(item.ssl_status)}</td>` +
      `<td><div class="action-group">${actions.join('')}</div></td></tr>`;
  }).join('') || '<tr><td colspan="5">Nenhum domínio registrado.</td></tr>';

  const pending = domains.find((item) => item.verification_status !== 'verified' && item.domain_type !== 'platform_subdomain');
  if (instructions) {
    instructions.innerHTML = pending
      ? `Para ativar <strong>${pending.full_host}</strong>: crie um CNAME apontando para <code>${pending.cname_target}</code> ` +
        `e um registro TXT em <code>${pending.txt_record}</code> com o valor <code>${pending.verification_token}</code>, depois clique em Verificar.`
      : '';
  }
}

async function addMyCompanyDomain() {
  const feedback = document.getElementById('my-company-domain-feedback');
  if (feedback) feedback.textContent = '';
  try {
    const domain = String(document.getElementById('my-company-domain-input')?.value || '').trim();
    const domainType = String(document.getElementById('my-company-domain-type')?.value || 'custom_domain');
    if (!domain) throw new Error('Informe o domínio a registrar.');
    await api('/api/my-company/domains', { method: 'POST', body: JSON.stringify({ actor_user_id: state.user.id, domain, domain_type: domainType }) });
    const input = document.getElementById('my-company-domain-input');
    if (input) input.value = '';
    if (feedback) feedback.textContent = 'Domínio registrado. Siga as instruções de DNS e clique em Verificar.';
    await loadMyCompanyDomains();
  } catch (error) {
    if (feedback) feedback.textContent = error.message; else alert(error.message);
  }
}

async function handleMyCompanyDomainAction(event) {
  const target = event.target;
  const feedback = document.getElementById('my-company-domain-feedback');
  if (feedback) feedback.textContent = '';
  try {
    if (target.dataset.domainVerify) {
      await api(`/api/my-company/domains/${target.dataset.domainVerify}/verify`, { method: 'POST', body: JSON.stringify({ actor_user_id: state.user.id }) });
      if (feedback) feedback.textContent = 'Domínio verificado com sucesso.';
    } else if (target.dataset.domainPrimary) {
      await api(`/api/my-company/domains/${target.dataset.domainPrimary}/primary`, { method: 'POST', body: JSON.stringify({ actor_user_id: state.user.id }) });
    } else if (target.dataset.domainDelete) {
      if (!confirm('Remover este domínio da sua empresa?')) return;
      await api(`/api/my-company/domains/${target.dataset.domainDelete}`, { method: 'DELETE', body: JSON.stringify({ actor_user_id: state.user.id }) });
    } else {
      return;
    }
    await loadMyCompanyDomains();
  } catch (error) {
    if (feedback) feedback.textContent = error.message; else alert(error.message);
    await loadMyCompanyDomains();
  }
}

async function advanceOnboardingStep() {
  const modal = onboardingModal();
  if (!modal) return;
  const feedback = document.getElementById('onboarding-feedback');
  if (feedback) feedback.textContent = '';
  try {
    if (onboardingStep === ONBOARDING_LAST_STEP) {
      await api('/api/my-company/onboarding-complete', { method: 'POST', body: JSON.stringify({ actor_user_id: state.user.id }) });
      closeModal(modal);
      await loadBootstrap();
      navigateToView('dashboard');
      return;
    }
    if (onboardingStep === 1) {
      const termsBox = document.getElementById('onboarding-terms');
      if (termsBox && !termsBox.checked) {
        if (feedback) feedback.textContent = 'Aceite os termos de uso e a política de privacidade para continuar.';
        return;
      }
      if (termsBox?.checked && !termsBox.dataset.accepted) {
        await api('/api/auth/accept-terms', { method: 'POST', body: JSON.stringify({ actor_user_id: state.user.id }) });
        termsBox.dataset.accepted = '1';
      }
      setOnboardingStep(2);
      return;
    }
    const panel = modal.querySelector(`[data-onboarding-step="${onboardingStep}"]`);
    const values = collectMyCompanyFields(panel);
    if (Object.keys(values).length) {
      values.actor_user_id = state.user.id;
      const payload = await api('/api/my-company', { method: 'PUT', body: JSON.stringify(values) });
      state.myCompany = payload.company || state.myCompany;
    }
    setOnboardingStep(onboardingStep + 1);
  } catch (error) {
    if (feedback) feedback.textContent = error.message; else alert(error.message);
  }
}

// master_admin não tem empresa própria: a Ficha é por empresa, então ele
// escolhe qual tenant está configurando. Demais perfis usam a própria empresa.
function fichaConfigSelectedCompanyId() {
  if (state.user?.role !== 'master_admin') return '';
  return String(document.getElementById('ficha-config-company')?.value || '').trim();
}

function syncFichaConfigCompanyPicker() {
  const row = document.getElementById('ficha-config-company-row');
  const banner = document.getElementById('ficha-config-company-banner');
  const select = document.getElementById('ficha-config-company');
  const isMaster = state.user?.role === 'master_admin';
  if (row) row.style.display = isMaster ? '' : 'none';
  if (!isMaster || !select) {
    if (banner) banner.style.display = 'none';
    return;
  }
  const previous = select.value;
  select.innerHTML = (state.companies || []).map((c) =>
    `<option value="${c.id}">${c.name}</option>`).join('');
  if (previous) select.value = previous;
  const active = (state.companies || []).find((c) => String(c.id) === String(select.value));
  if (banner) {
    banner.style.display = active ? '' : 'none';
    banner.textContent = active ? `Administrando a empresa: ${active.name}` : '';
  }
}

async function loadFichaConfig() {
  try {
    syncFichaConfigCompanyPicker();
    const companyId = fichaConfigSelectedCompanyId();
    const query = actorQuery() + (companyId ? `&company_id=${encodeURIComponent(companyId)}` : '');
    const data = await api('/api/ficha-config?' + query);
    const f = document.getElementById('ficha-config-form');
    if (!f) return;
    f.elements.titulo.value      = data.titulo      || '';
    f.elements.declaracao.value  = data.declaracao  || '';
    f.elements.observacoes.value = data.observacoes || '';
    f.elements.rastreabilidade.value = data.rastreabilidade || '';
  } catch (e) { console.warn('[ficha-config] erro ao carregar:', e); }
}

async function saveFichaConfig(event) {
  event.preventDefault();
  const f = document.getElementById('ficha-config-form');
  if (!f) return;
  try {
    const companyId = fichaConfigSelectedCompanyId();
    if (state.user?.role === 'master_admin' && !companyId) {
      throw new Error('Selecione uma empresa para configurar a Ficha.');
    }
    const body = {
      actor_user_id: state.user.id,
      titulo:        f.elements.titulo.value,
      declaracao:    f.elements.declaracao.value,
      observacoes:   f.elements.observacoes.value,
      rastreabilidade: f.elements.rastreabilidade.value,
    };
    if (companyId) body.company_id = companyId;
    await api('/api/ficha-config', { method: 'POST', body: JSON.stringify(body) });
    alert('Configurações da ficha salvas com sucesso!');
  } catch (e) { alert(e.message); }
}

function configRoleOptions() {
  return [
    ['admin', 'Administrador Local'],
    ['registry_admin', 'Administrador de Registro'],
    ['user', 'Gestor de EPI'],
    ['employee', 'Funcionário']
  ];
}

function renderConfigurationRules() {
  if (!refs.configRulesTable) return;
  refs.configRulesTable.innerHTML = state.configurationRules.map((rule) => {
    const unit = state.units.find((item) => String(item.id) === String(rule.unit_id));
    return `
      <tr>
        <td>${roleLabel(rule.role)}</td>
        <td>${unit?.name || `#${rule.unit_id}`}</td>
        <td>${rule.unit_context === 'inside_jv' ? 'Em JV' : 'Fora de JV'}</td>
        <td>${rule.can_view_unit ? '✅' : '❌'}</td>
        <td>${rule.can_view_epis ? '✅' : '❌'}</td>
        <td>${rule.can_view_employees ? '✅' : '❌'}</td>
        <td><button class="ghost" type="button" data-remove-config-rule="${rule.id}">Remover</button></td>
      </tr>
    `;
  }).join('') || '<tr><td colspan="7">Sem regras específicas. O sistema aplicará as regras padrão por perfil.</td></tr>';
}

function hydrateConfigurationForms() {
  if (!refs.configRuleRole || !refs.configRuleUnit) return;
  refs.configRuleRole.innerHTML = configRoleOptions().map(([value, label]) => `<option value="${value}">${label}</option>`).join('');
  const units = filterByUserCompany(state.units);
  refs.configRuleUnit.innerHTML = units.map((item) => `<option value="${item.id}">${item.name}</option>`).join('');
  if (refs.fichaAuditEmployee) {
    refs.fichaAuditEmployee.innerHTML = '<option value="">Todos os colaboradores</option>' + filterByUserCompany(state.employees)
      .map((item) => `<option value="${item.id}">${item.employee_id_code} - ${item.name}</option>`).join('');
  }
  if (refs.fichaAuditManager) {
    refs.fichaAuditManager.innerHTML = '<option value="">Todos os gestores</option>' + filterByUserCompany(state.users)
      .map((item) => `<option value="${item.id}">${item.full_name}</option>`).join('');
  }
  renderConfigurationRules();
  renderConfigurationFramework();
  hydrateModuleVisibilityForm();
  renderFichaAuditLogs();
}

// Perfis válidos para a matriz de visibilidade de módulos: todos os 8
// papéis canônicos (espelha PERMISSIONS.keys() em core/permissions.py) —
// mais amplo que configRoleOptions() (que só cobre visibility_rules).
function moduleVisibilityRoleOptions() {
  return Object.keys(ROLE_LABELS).map((role) => [role, ROLE_LABELS[role]]);
}

function hydrateModuleVisibilityForm() {
  if (!refs.moduleVisibilityRole || !refs.moduleVisibilityCheckboxes) return;
  const previous = refs.moduleVisibilityRole.value;
  refs.moduleVisibilityRole.innerHTML = moduleVisibilityRoleOptions()
    .map(([value, label]) => `<option value="${value}">${label}</option>`).join('');
  refs.moduleVisibilityRole.value = previous && refs.moduleVisibilityRole.querySelector(`option[value="${previous}"]`)
    ? previous
    : refs.moduleVisibilityRole.value;
  populateModuleVisibilityUnitSelect();
  syncModuleVisibilityUnitVisibility();
  renderModuleVisibilityCheckboxes();
  renderModuleVisibilityDefaultPanel();
}

// Painel "Permissões padrão deste perfil": mostra o padrão IMUTÁVEL do
// sistema (state.moduleVisibilityDefault, nunca a configuração
// personalizada) para o perfil selecionado — deixa explícito que a
// matriz de checkboxes abaixo é uma PERSONALIZAÇÃO sobre esse padrão, não
// a definição do perfil.
function renderModuleVisibilityDefaultPanel() {
  if (!refs.moduleVisibilityRole || !refs.moduleVisibilityDefaultPanel || !refs.moduleVisibilityDefaultList) return;
  const role = refs.moduleVisibilityRole.value;
  const defaults = (state.moduleVisibilityDefault || {})[role];
  if (!defaults) {
    refs.moduleVisibilityDefaultPanel.hidden = true;
    return;
  }
  refs.moduleVisibilityDefaultPanel.hidden = false;
  const enabledModules = Object.keys(MODULE_VISIBILITY_LABELS).filter((moduleKey) => Boolean(defaults[moduleKey]));
  refs.moduleVisibilityDefaultList.innerHTML = enabledModules.length
    ? enabledModules.map((moduleKey) => `<span class="badge badge-status-active">✔ ${MODULE_VISIBILITY_LABELS[moduleKey]}</span>`).join('')
    : `<span class="badge badge-module-off">${tr('moduleVisibility.noDefaultModules', 'Nenhum módulo por padrão')}</span>`;
}

// Seletor de Unidade: só faz sentido para os papéis em
// MODULE_VISIBILITY_UNIT_SCOPED_ROLES (admin/user). Mesma fonte de
// unidades usada em hydrateConfigurationForms — já filtrada para a
// empresa do ator (filterByUserCompany, dentro de populateSelect).
function populateModuleVisibilityUnitSelect() {
  if (!refs.moduleVisibilityUnit) return;
  const previous = refs.moduleVisibilityUnit.value;
  populateSelect('module-visibility-unit', state.units, (item) => item.name, 'id', true,
    tr('moduleVisibility.allUnitsOption', 'Todas as unidades (padrão)'));
  refs.moduleVisibilityUnit.value = previous && refs.moduleVisibilityUnit.querySelector(`option[value="${previous}"]`)
    ? previous
    : '';
}

function syncModuleVisibilityUnitVisibility() {
  if (!refs.moduleVisibilityRole || !refs.moduleVisibilityUnitWrap) return;
  const role = refs.moduleVisibilityRole.value;
  const scoped = MODULE_VISIBILITY_UNIT_SCOPED_ROLES.includes(role);
  refs.moduleVisibilityUnitWrap.hidden = !scoped;
  if (refs.moduleVisibilityUnitHint) refs.moduleVisibilityUnitHint.hidden = !scoped;
  if (!scoped && refs.moduleVisibilityUnit) refs.moduleVisibilityUnit.value = '';
}

// Valor efetivo módulo a módulo para o par (perfil, unidade), espelhando
// resolve_module_visibility em epi_backend/rule_engine.py: um módulo
// ausente do bucket da Unidade herda do bucket "*"; ausente de ambos,
// assume visível (regra padrão do sistema).
function moduleVisibilityEffectiveValue(roleConfig, unitId, moduleKey) {
  const base = roleConfig['*'] || {};
  if (unitId) {
    const bucket = roleConfig[String(unitId)] || {};
    if (Object.prototype.hasOwnProperty.call(bucket, moduleKey)) return Boolean(bucket[moduleKey]);
  }
  if (Object.prototype.hasOwnProperty.call(base, moduleKey)) return Boolean(base[moduleKey]);
  return true;
}

function renderModuleVisibilityCheckboxes() {
  if (!refs.moduleVisibilityCheckboxes || !refs.moduleVisibilityRole) return;
  const role = refs.moduleVisibilityRole.value;
  const unitId = (refs.moduleVisibilityUnitWrap && !refs.moduleVisibilityUnitWrap.hidden && refs.moduleVisibilityUnit)
    ? refs.moduleVisibilityUnit.value
    : '';
  const roleConfig = (state.moduleVisibilityAdminConfig || {})[role] || {};
  refs.moduleVisibilityCheckboxes.innerHTML = Object.keys(MODULE_VISIBILITY_LABELS).map((moduleKey) => {
    const checked = moduleVisibilityEffectiveValue(roleConfig, unitId, moduleKey);
    return `<label><input type="checkbox" name="module_${moduleKey}" data-module-key="${moduleKey}" ${checked ? 'checked' : ''}> ${MODULE_VISIBILITY_LABELS[moduleKey]}</label>`;
  }).join('');
}

async function onSubmitModuleVisibility(event) {
  event.preventDefault();
  if (!hasConfigurationAccess() || !refs.moduleVisibilityRole || !refs.moduleVisibilityCheckboxes) return;
  const role = refs.moduleVisibilityRole.value;
  const unitId = (refs.moduleVisibilityUnitWrap && !refs.moduleVisibilityUnitWrap.hidden && refs.moduleVisibilityUnit)
    ? refs.moduleVisibilityUnit.value
    : '';
  const modules = {};
  refs.moduleVisibilityCheckboxes.querySelectorAll('input[data-module-key]').forEach((input) => {
    modules[input.dataset.moduleKey] = input.checked;
  });
  try {
    // Sem seletor de empresa nesta tela: general_admin/registry_admin usam a
    // própria empresa (resolvida no backend); master_admin sem seleção grava
    // no escopo global, mesma limitação herdada da aba de regras por unidade.
    const body = { actor_user_id: state.user.id, role, modules };
    if (unitId) body.unit_id = Number(unitId);
    const result = await api('/api/module-visibility', { method: 'POST', body: JSON.stringify(body) });
    const bucket = unitId ? String(unitId) : '*';
    const roleConfig = state.moduleVisibilityAdminConfig[role] || {};
    state.moduleVisibilityAdminConfig = {
      ...state.moduleVisibilityAdminConfig,
      [role]: { ...roleConfig, [bucket]: { ...(roleConfig[bucket] || {}), ...(result.after || modules) } }
    };
    if (refs.moduleVisibilityFeedback) {
      refs.moduleVisibilityFeedback.textContent = unitId
        ? tr('moduleVisibility.savedForRoleUnit', 'Visibilidade de módulos salva para {role} na Unidade {unit}.')
          .replace('{role}', roleLabel(role))
          .replace('{unit}', (state.units.find((item) => String(item.id) === unitId) || {}).name || `#${unitId}`)
        : tr('moduleVisibility.savedForRole', 'Visibilidade de módulos salva para {role}.').replace('{role}', roleLabel(role));
    }
  } catch (e) {
    if (refs.moduleVisibilityFeedback) refs.moduleVisibilityFeedback.textContent = '';
    alert(e.message);
  }
}

function roleVisibilityLabel(scope) {
  if (scope === 'all') return 'Todas';
  if (scope === 'company') return 'Empresa';
  if (scope === 'operational') return 'Operacional';
  return String(scope || 'Padrão');
}

function renderConfigurationFramework() {
  if (!refs.configFrameworkForm || !hasHardeningAccess()) return;
  const framework = { ...deepClone(DEFAULT_CONFIGURATION_FRAMEWORK), ...(state.configurationFramework || {}) };
  const flags = framework.feature_flags || {};
  if (refs.configEnableNewEngine) refs.configEnableNewEngine.checked = Boolean(flags.enable_new_rules_engine);
  if (refs.configExecutionMode) refs.configExecutionMode.value = flags.execution_mode || 'off';
  if (refs.configRolloutPercentage) refs.configRolloutPercentage.value = Number(flags.rollout_percentage || 0);
  if (refs.configAllowNewResponse) refs.configAllowNewResponse.checked = Boolean(flags.allow_new_engine_response);
  if (refs.configEnabledProfiles) refs.configEnabledProfiles.value = (flags.enabled_profiles || []).join(', ');
  if (refs.configEnabledCompanies) refs.configEnabledCompanies.value = (flags.enabled_company_ids || []).join(', ');
  if (refs.configEnabledEndpoints) refs.configEnabledEndpoints.value = (flags.enabled_endpoints || []).join(', ');
  if (refs.configEnabledEnvironments) refs.configEnabledEnvironments.value = (flags.enabled_environments || []).join(', ');

  const hierarchy = framework.hierarchy?.who_can_view_what || {};
  if (refs.configHierarchyTable) {
    refs.configHierarchyTable.innerHTML = Object.entries(hierarchy).map(([role, scope]) => `
      <tr>
        <td>${roleLabel(role)}</td>
        <td>${roleVisibilityLabel(scope?.units)}</td>
        <td>${roleVisibilityLabel(scope?.epis)}</td>
        <td>${roleVisibilityLabel(scope?.employees)}</td>
      </tr>
    `).join('') || '<tr><td colspan=\"4\">Sem hierarquia configurada.</td></tr>';
  }
  if (refs.configHierarchyJson) refs.configHierarchyJson.value = JSON.stringify(hierarchy, null, 2);

  const reportScopes = framework.report_scopes || {};
  if (refs.configReportScopesTable) {
    refs.configReportScopesTable.innerHTML = Object.entries(reportScopes).map(([reportType, scope]) => `
      <tr>
        <td>${reportType}</td>
        <td>${scope.enabled ? '✅' : '❌'}</td>
        <td>${scope.enforce_unit_scope ? '✅' : '❌'}</td>
        <td>${scope.enforce_visibility_rules ? '✅' : '❌'}</td>
        <td>${(scope.allowed_profiles || []).map((item) => roleLabel(item)).join(', ')}</td>
      </tr>
    `).join('') || '<tr><td colspan=\"5\">Sem escopos de relatório configurados.</td></tr>';
  }
  if (refs.configReportScopesJson) refs.configReportScopesJson.value = JSON.stringify(reportScopes, null, 2);
}

function parseCsvList(value) {
  return String(value || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseCsvNumberList(value) {
  return parseCsvList(value).map((item) => Number(item)).filter((item) => Number.isFinite(item) && item > 0);
}

function parseOptionalJson(rawValue, fallbackValue) {
  const trimmed = String(rawValue || '').trim();
  if (!trimmed) return fallbackValue;
  try {
    return JSON.parse(trimmed);
  } catch (error) {
    throw new Error('JSON inválido na configuração avançada: ' + error.message);
  }
}

async function saveConfigurationFramework(event) {
  event.preventDefault();
  if (!hasHardeningAccess()) return;
  const current = { ...deepClone(DEFAULT_CONFIGURATION_FRAMEWORK), ...(state.configurationFramework || {}) };
  current.feature_flags.enable_new_rules_engine = Boolean(refs.configEnableNewEngine?.checked);
  current.feature_flags.execution_mode = String(refs.configExecutionMode?.value || 'off');
  current.feature_flags.rollout_percentage = Number(refs.configRolloutPercentage?.value || 0);
  current.feature_flags.allow_new_engine_response = Boolean(refs.configAllowNewResponse?.checked);
  current.feature_flags.enabled_profiles = parseCsvList(refs.configEnabledProfiles?.value || '');
  current.feature_flags.enabled_company_ids = parseCsvNumberList(refs.configEnabledCompanies?.value || '');
  current.feature_flags.enabled_endpoints = parseCsvList(refs.configEnabledEndpoints?.value || '');
  current.feature_flags.enabled_environments = parseCsvList(refs.configEnabledEnvironments?.value || '').map((item) => item.toLowerCase());
  current.hierarchy.who_can_view_what = parseOptionalJson(refs.configHierarchyJson?.value || '', current.hierarchy.who_can_view_what || {});
  current.report_scopes = parseOptionalJson(refs.configReportScopesJson?.value || '', current.report_scopes || {});
  current.visibility_rules = state.configurationRules;
  const payload = await api('/api/configuration-framework', {
    method: 'POST',
    body: JSON.stringify({ actor_user_id: state.user.id, framework: current })
  });
  state.configurationFramework = { ...deepClone(DEFAULT_CONFIGURATION_FRAMEWORK), ...(payload.framework || {}) };
  renderConfigurationFramework();
  alert('Framework de regras salvo. O fallback legado continua ativo até ativação por feature flag.');
}

async function saveConfigurationRules() {
  state.configurationFramework.visibility_rules = state.configurationRules;
  await api('/api/configuration-rules', {
    method: 'POST',
    body: JSON.stringify({
      actor_user_id: state.user.id,
      rules: state.configurationRules
    })
  });
}

async function onSubmitConfigurationRule(event) {
  event.preventDefault();
  if (!hasConfigurationAccess()) return;
  const form = event.currentTarget;
  const entry = {
    id: `rule-${Date.now()}`,
    role: form.elements.role.value,
    unit_id: Number(form.elements.unit_id.value),
    unit_context: form.elements.unit_context.value,
    can_view_unit: Boolean(form.elements.can_view_unit.checked),
    can_view_epis: Boolean(form.elements.can_view_epis.checked),
    can_view_employees: Boolean(form.elements.can_view_employees.checked)
  };
  state.configurationRules = [...state.configurationRules, entry];
  await saveConfigurationRules();
  renderConfigurationRules();
}

async function removeConfigurationRule(ruleId) {
  if (!hasConfigurationAccess()) return;
  state.configurationRules = state.configurationRules.filter((item) => String(item.id) !== String(ruleId));
  await saveConfigurationRules();
  renderConfigurationRules();
}

function abrirFichaEpiHTML(employeeId) {
  const url = '/api/ficha-epi/' + employeeId + '.html?' + actorQuery() + '&action=view';
  const popup = window.open(url, '_blank', 'width=900,height=700,menubar=yes,toolbar=yes');
  if (!popup) alert('Permita pop-ups para visualizar a ficha.');
}

function imprimirFichaEpi(employeeId) {
  const url = '/api/ficha-epi/' + employeeId + '.html?' + actorQuery() + '&action=print';
  const popup = window.open(url, '_blank', 'width=900,height=700');
  if (popup) {
    popup.onload = () => popup.print();
  }
}


// ═══════════════════════════════════════════════════════
// DEVOLUÇÃO DE EPI
// ═══════════════════════════════════════════════════════
const DEVOLUTION_CONDITIONS = [
  {value:'usable',label:'Reutilizável'},
  {value:'damaged',label:'Danificado'},
  {value:'discarded',label:'Descartado'},
  {value:'maintenance',label:'Em manutenção'},
  {value:'quarantine',label:'Em quarentena'},
  {value:'hygiene',label:'Para higienização'},
];
const DEVOLUTION_DESTINATIONS = [
  {value:'stock',label:'Retornar ao estoque'},
  {value:'discard',label:'Descartar'},
  {value:'maintenance',label:'Encaminhar para manutenção'},
  {value:'hygiene',label:'Encaminhar para higienização'},
  {value:'quarantine',label:'Colocar em quarentena'},
];

function bindAppListener(target, eventName, handler, options = {}) {
  if (!target) return false;
  return safeOn(target, eventName, handler, options);
}

async function init() {
  const runNonCriticalSetup = (label, setupFn) => {
    try {
      setupFn();
    } catch (error) {
      reportNonCriticalError(`[init] módulo não crítico ignorado: ${label}`, error);
    }
  };

  const employeeToken = new URLSearchParams(globalThis.location.search).get('employee_token');
  if (employeeToken) {
    const normalizedToken = String(employeeToken).trim();
    const cachedCpf = getCachedPortalCpfLast3(normalizedToken);
    if (cachedCpf) {
      try {
        await renderEmployeeExternalAccess(normalizedToken, cachedCpf);
        return;
      } catch (_error) {
        sessionStorage.removeItem(portalCpfStorageKey(normalizedToken));
      }
    }
    renderEmployeeCpfValidationScreen(normalizedToken);
    return;
  }
  runNonCriticalSetup('assinatura modal', setupSignatureModal);
  runNonCriticalSetup('preload login URL', preloadLoginFromUrl);
  runNonCriticalSetup('required labels', markRequiredFieldLabels);
  runNonCriticalSetup('form field hardening', setupFormFieldHardening);
  runNonCriticalSetup('phase2 pilots', setupPhase2PilotsSafely);
  runNonCriticalSetup('phase2.9 ux', setupPhase29Ux);
  runNonCriticalSetup('spa navigation history', bindSpaNavigationHistory);
  runNonCriticalSetup('spa navigation visibility', applySpaNavigationVisibility);
  runNonCriticalSetup('interactive app dropdowns', setupInteractiveDropdowns);
  runNonCriticalSetup('interactive tools actions', bindInteractiveToolsActions);
  runNonCriticalSetup('ux performance hardening', applyPerformanceHardeningVisibility);
  runNonCriticalSetup('ux mobile visibility', applyMobileUxVisibility);
  runNonCriticalSetup('ux mobile behavior', bindMobileUxBehavior);
  runNonCriticalSetup('nav back behavior', bindNavBackBehavior);
  runNonCriticalSetup('table density preference', applyTableDensityPref);
  runNonCriticalSetup('assinatura entrega', setupDeliverySignatureCanvas);
  runNonCriticalSetup('sessão QR entrega', resetDeliveryQrSession);
  runNonCriticalSetup('delegação click câmera QR', bindDeliveryQrCameraDelegatedClick);
  document.body?.classList.toggle('ux-interactive-app-enabled', isUxInteractiveAppEnabled());
  const initBindingsController = createScopedAbortController('app_init_bindings');
  const bindAppListener = (target, eventName, handler, options = {}) => {
    if (!target) return false;
    const config = options && typeof options === 'object'
      ? { ...options, signal: initBindingsController.signal }
      : options;
    return safeOn(target, eventName, handler, config);
  };
  const LEGACY_LISTENER_EXCEPTIONS = Object.freeze({
    critical_bootstrap: ['setupSignatureCanvas', 'signature modal interactions', 'dynamic popup print'],
    ui_simple: ['canvas draw and touch listeners (high-frequency pointer path)'],
    justified: ['delegated table handlers and one-shot dynamic elements not re-bound by view lifecycle']
  });
  globalThis.__EPI_LISTENER_EXCEPTION_MAP__ = LEGACY_LISTENER_EXCEPTIONS;

  bindAppListener(refs.loginForm, 'submit', handleLogin);
  bindAppListener(refs.loginPasswordToggle, 'click', toggleLoginPasswordVisibility);
  bindAppListener(refs.passwordChangeForm, 'submit', handleForcedPasswordChange);
  bindAppListener(refs.recoveryToggle, 'click', toggleRecoveryPanel);
  bindAppListener(refs.recoverySubmit, 'click', handlePasswordRecovery);
  safeOn(document.getElementById('recovery-switch-to-email'), 'click', () => {
    document.getElementById('recovery-by-key-section').style.display = 'none';
    document.getElementById('recovery-by-email-section').style.display = 'block';
  });
  safeOn(document.getElementById('recovery-switch-to-key'), 'click', () => {
    document.getElementById('recovery-by-email-section').style.display = 'none';
    document.getElementById('recovery-by-key-section').style.display = 'block';
  });
  safeOn(document.getElementById('recovery-send-email'), 'click', () => { void handleEmailRecoveryRequest(); });
  safeOn(document.getElementById('recovery-token-copy'), 'click', () => {
    const val = document.getElementById('recovery-token-value')?.textContent || '';
    navigator.clipboard?.writeText(val).catch(() => {});
    const btn = document.getElementById('recovery-token-copy');
    if (btn) { btn.textContent = 'Copiado!'; setTimeout(() => { btn.textContent = 'Copiar'; }, 2000); }
  });
  safeOn(document.getElementById('recovery-token-close'), 'click', () => {
    const modal = document.getElementById('recovery-token-modal');
    if (modal) modal.setAttribute('hidden', '');
    const tokenEl = document.getElementById('recovery-token-value');
    if (tokenEl) tokenEl.textContent = '';
  });
  safeOn(document.getElementById('master-profile-btn'), 'click', openMasterProfileModal);
  safeOn(document.getElementById('master-profile-save'), 'click', () => { void saveMasterProfileEmail(); });
  safeOn(document.getElementById('master-profile-close'), 'click', () => {
    const modal = document.getElementById('master-profile-modal');
    if (modal) modal.setAttribute('hidden', '');
  });
  safeOn(document.getElementById('master-change-password'), 'click', () => { void handleMasterPasswordChange(); });
  bindAppListener(refs.userForm, 'submit', saveUser);
  bindAppListener(document.getElementById('purchase-functions-save'), 'click', savePurchaseFunctionLinks);
  bindAppListener(document.getElementById('purchase-functions-refresh'), 'click', loadPurchaseFunctions);
  bindAppListener(document.getElementById('purchase-function-employee-search'), 'input', (event) => {
    const currentEmployeeId = document.getElementById('purchase-function-employee')?.value || '';
    const currentSelection = new Set(_purchaseFunctionSelectedUnitIds);
    _purchaseFunctionEmployeeSearch = String(event.target.value || '');
    renderPurchaseFunctionControls();
    if (currentEmployeeId && String(document.getElementById('purchase-function-employee')?.value || '') === String(currentEmployeeId)) {
      _purchaseFunctionSelectedUnitIds.clear();
      currentSelection.forEach((unitId) => _purchaseFunctionSelectedUnitIds.add(unitId));
      renderPurchaseFunctionUnitChecks();
    }
  });
  bindAppListener(document.getElementById('purchase-function-employee'), 'change', () => {
    _syncPurchaseFunctionTypeToEmployee();
    syncPurchaseFunctionSelectionFromExistingLinks();
    renderPurchaseFunctionUnitChecks();
  });
  bindAppListener(document.getElementById('purchase-function-type'), 'change', () => {
    syncPurchaseFunctionSelectionFromExistingLinks();
    renderPurchaseFunctionUnitChecks();
  });
  bindAppListener(document.getElementById('purchase-function-unit-search'), 'input', (event) => {
    _purchaseFunctionUnitSearch = String(event.target.value || '');
    renderPurchaseFunctionUnitChecks();
  });
  bindAppListener(document.getElementById('purchase-functions-select-visible'), 'click', () => {
    filteredPurchaseFunctionUnits().forEach((unit) => _purchaseFunctionSelectedUnitIds.add(String(unit.id)));
    renderPurchaseFunctionUnitChecks();
  });
  bindAppListener(document.getElementById('purchase-functions-clear-selection'), 'click', () => {
    _purchaseFunctionSelectedUnitIds.clear();
    renderPurchaseFunctionUnitChecks();
  });
  bindAppListener(document.getElementById('purchase-function-units'), 'change', (event) => {
    if (event.target?.dataset?.purchaseFunctionUnit) setPurchaseFunctionUnitSelection(event.target.dataset.purchaseFunctionUnit, event.target.checked);
  });
  bindAppListener(document.getElementById('purchase-function-selected-units'), 'click', (event) => {
    if (event.target?.dataset?.purchaseFunctionChipRemove) setPurchaseFunctionUnitSelection(event.target.dataset.purchaseFunctionChipRemove, false);
  });
  bindAppListener(refs.companyForm, 'submit', saveCompany);
  bindAppListener(refs.platformBrandForm, 'submit', savePlatformBrand);
  bindAppListener(refs.commercialSettingsForm, 'submit', saveCommercialSettings);
  bindAppListener(refs.commercialForm, 'submit', saveCommercial);

  bindAppListener(refs.commercialCompany, 'change', () => {
    fillCommercialForm(refs.commercialCompany.value);
    renderCommercialHistory();
  });

  bindAppListener(refs.commercialForm?.elements.plan_name, 'change', () => refreshCommercialPreview());
  bindAppListener(refs.commercialForm?.elements.user_limit, 'input', () => refreshCommercialPreview());
  bindAppListener(refs.commercialForm?.elements.addendum_enabled, 'change', () => refreshCommercialPreview());

  bindAppListener(refs.commercialFilterStatus, 'change', syncCommercialFilter);
  bindAppListener(refs.commercialFilterDateFrom, 'change', syncCommercialFilter);
  bindAppListener(refs.commercialFilterDateTo, 'change', syncCommercialFilter);
  bindAppListener(refs.commercialFilterActor, 'change', syncCommercialFilter);
  bindAppListener(refs.commercialContractClauses, 'input', () => {
    state.commercialClauseTemplate = refs.commercialContractClauses?.value || '';
  });

  bindAppListener(refs.commercialContractPdf, 'click', downloadCommercialContractPdf);
  bindAppListener(refs.commercialGenerateContract, 'click', generateCommercialContract);
  bindAppListener(refs.commercialViewContract, 'click', viewGeneratedCommercialContract);
  bindAppListener(refs.commercialDownloadContract, 'click', downloadGeneratedCommercialContract);
  bindAppListener(refs.commercialUploadSigned, 'click', uploadSignedCommercialContract);
  bindAppListener(refs.commercialSignContract, 'click', signCommercialContractAction);
  bindAppListener(refs.commercialSendContractEmail, 'click', sendCommercialContractByEmail);
  bindAppListener(refs.commercialSaveContractManagement, 'click', saveCommercialContractManagement);
  bindAppListener(refs.commercialExport, 'click', exportCommercialHistory);
  bindAppListener(refs.commercialExportExcel, 'click', exportCommercialExcel);
  bindAppListener(refs.commercialPrint, 'click', printCommercialHistory);

  bindAppListener(refs.platformLogoFile, 'change', handlePlatformLogoUpload);
  bindAppListener(refs.platformLoginLogoFile, 'change', handlePlatformLoginLogoUpload);
  configureEpiPhotoInputCapture();
  bindAppListener(document.getElementById('epi-photo-file'), 'change', handleEpiPhotoUpload);
  bindAppListener(document.getElementById('epi-photo-open-camera'), 'click', () => openEpiPhotoPicker({ preferCamera: true }));
  bindAppListener(document.getElementById('epi-photo-open-files'), 'click', () => openEpiPhotoPicker({ preferCamera: false }));

  bindAppListener(refs.companyForm?.elements.cnpj, 'blur', (event) => {
    event.target.value = formatCnpj(event.target.value);
    // P2-4 — validação inline do CNPJ (não bloqueia; sinaliza em tempo real).
    const raw = String(event.target.value || '').replace(/\D/g, '');
    if (raw && typeof globalThis.dsValidateCNPJ === 'function' && !globalThis.dsValidateCNPJ(raw)) {
      globalThis.dsSetFieldError(event.target, tr('validation.cnpjInvalid', 'CNPJ inválido. Confira os dígitos.'));
    } else {
      globalThis.dsClearFieldError?.(event.target);
    }
  });
  bindAppListener(refs.companyForm?.elements.cnpj, 'input', (event) => {
    globalThis.dsClearFieldError?.(event.target); // limpa o erro ao reeditar
  });

  bindAppListener(refs.platformBrandForm?.elements.cnpj, 'blur', (event) => {
    event.target.value = formatCnpj(event.target.value);
  });

  bindAppListener(document.getElementById('unit-form'), 'submit', (event) => saveSimpleForm(event, '/api/units', 'units:create'));
  bindAppListener(document.getElementById('legal-entity-form'), 'submit', (event) => saveSimpleForm(event, '/api/legal-entities', 'legal_entities:create'));
  bindAppListener(document.getElementById('outsourced-company-form'), 'submit', (event) => saveSimpleForm(event, '/api/outsourced-companies', ['employees:create', 'employees:create_simplified']));
  bindAppListener(document.getElementById('outsourced-employee-form'), 'submit', (event) => saveSimpleForm(event, '/api/employees/outsourced-simplified', 'employees:create_simplified'));
  bindAppListener(document.getElementById('outsourced-employee-company'), 'change', syncOutsourcedEmployeeUnitOptions);
  bindAppListener(document.getElementById('employee-form'), 'submit', (event) => saveSimpleForm(event, '/api/employees', 'employees:create'));
  bindAppListener(document.getElementById('epi-form'), 'submit', (event) => saveSimpleForm(event, '/api/epis', 'epis:create'));
  bindAppListener(document.getElementById('delivery-form'), 'submit', (event) => saveSimpleForm(event, '/api/deliveries', 'deliveries:create'));
  bindAppListener(document.getElementById('stock-form'), 'submit', handleStockMovementSubmit);
  bindAppListener(document.getElementById('stock-manufacture-camera'), 'change', handleStockManufactureCameraCapture);
  bindAppListener(document.getElementById('stock-manufacture-date'), 'input', () => {
    const dateField = document.getElementById('stock-manufacture-date');
    if (!dateField) return;
    if (dateField.value !== String(dateField.dataset.autoFilled || '')) dateField.dataset.userEdited = '1';
  });
  resetStockManufactureCaptureState();
  bindAppListener(document.getElementById('epi-company'), 'change', () => {
    syncEpiUnitOptions();
  });
  bindAppListener(document.getElementById('epi-unit'), 'change', () => {
    if (String(document.getElementById('epi-joinventure-active')?.value || '').trim()) {
      applyEpiJoinventureRules();
    }
  });
  bindAppListener(document.getElementById('epi-joinventure-active'), 'change', applyEpiJoinventureRules);
  bindAppListener(document.getElementById('employee-company'), 'change', () => {
    syncEmployeeUnitOptions();
  });
  // Trocar a empresa muda o conjunto de CNPJs disponíveis: o backend recusa
  // CNPJ de outra empresa, então manter a lista anterior só geraria erro no
  // salvar.
  bindAppListener(document.getElementById('unit-company'), 'change', () => {
    syncUnitLegalEntityOptions();
  });

  bindAppListener(document.getElementById('employee-tipo-vinculo'), 'change', syncEmpresaOrigemVisibility);
  // Estado inicial: cobre o caso de o valor do select já não ser 'CLT' sem
  // que um evento 'change' tenha disparado (ex.: valor restaurado pelo
  // navegador ao recarregar a página, o que não dispara 'change').
  syncEmpresaOrigemVisibility();
  bindAppListener(document.getElementById('epi-joinventure-add'), 'click', addJoinventure);
  bindAppListener(document.getElementById('epi-joinventure-name'), 'keyup', (event) => {
    if (event.key === 'Enter') addJoinventure();
  });
  bindAppListener(document.getElementById('epi-joinventure-list'), 'click', (event) => {
    const button = event.target.closest('[data-joinventure-remove]');
    if (!button) return;
    removeJoinventure(button.dataset.joinventureRemove || '');
  });
  renderJoinventureList();
  renderEpiPhotoPreview(document.getElementById('epi-photo-data')?.value || '');

  bindAppListener(document.getElementById('movement-form'), 'submit', saveEmployeeMovement);
  bindAppListener(document.getElementById('logout-btn'), 'click', () => {
    void stopDeliveryQrCamera();
    clearSession();
    showScreen(false);
  });

  bindAppListener(document.getElementById('delivery-company'), 'change', () => {
    state.deliveryEpis = [];
    state.deliveryEpisScopeKey = '';
    state.deliveryReturnCandidates = [];
    state.deliveryReturnScopeKey = '';
    syncDeliveryOptions();
    refreshDeliveryContext();
    void loadAvailableQrsForSelectedEpi();
  });
  bindAppListener(document.getElementById('stock-company'), 'change', async () => { syncStockOptions(); await loadStockEpis(); scheduleStockMovementSearchLoad(); });
  bindAppListener(document.getElementById('stock-unit'), 'change', async () => { syncStockOptions(); await loadStockEpis(); scheduleStockMovementSearchLoad(); });
  bindAppListener(document.getElementById('stock-epi'), 'change', () => {
    syncStockSizeDefaults();
    syncSelectedEpiMinimumStockField();
    renderStockEpiSearchResults();
  });
  bindAppListener(document.getElementById('delivery-unit-filter'), 'change', () => {
    state.deliveryEpis = [];
    state.deliveryEpisScopeKey = '';
    state.deliveryReturnCandidates = [];
    state.deliveryReturnScopeKey = '';
    syncDeliveryOptions();
    refreshDeliveryContext();
    void loadAvailableQrsForSelectedEpi();
  });
  bindSearchInput(document.getElementById('delivery-employee-search'), syncDeliveryOptions, 140);
  bindSearchInput(refs.deliveryEpiSearch, renderDeliveryEpiSearchResults, 120);
  bindSearchInput(refs.deliveryEpiSearchManufacturer, renderDeliveryEpiSearchResults, 120);
  bindAppListener(document.getElementById('delivery-qr-apply'), 'click', () => { void handleDeliveryManualValidationRequest(); });
  bindAppListener(document.getElementById('delivery-qr-scan'), 'change', () => { void queueDeliveryQrForCurrentSession(); });
  bindAppListener(document.getElementById('delivery-qr-scan'), 'input', () => {
    const typedCode = String(document.getElementById('delivery-qr-scan')?.value || '').trim();
    if (!typedCode || !isCodeAutoValidatedBySelection(typedCode)) {
      deliveryCodeValidationState.code = '';
      deliveryCodeValidationState.source = '';
      deliveryCodeValidationState.autoValidated = false;
    }
  });
  bindAppListener(document.getElementById('delivery-qr-scan'), 'keyup', (event) => {
    if (event.key === 'Enter') void queueDeliveryQrForCurrentSession();
  });
  bindAppListener(document.getElementById('delivery-qr-reader'), 'click', () => { void enableDeliveryBarcodeReaderMode(); });
  bindAppListener(document.getElementById('delivery-qr-stop'), 'click', () => { void stopDeliveryQrCamera(); });
  bindAppListener(document.getElementById('delivery-qr-close-fixed'), 'click', () => { void stopDeliveryQrCamera(); });
  bindAppListener(document.getElementById('delivery-qr-finish'), 'click', () => { void finishDeliveryQrCameraSession(); });
  bindAppListener(document.getElementById('delivery-qr-session-clear'), 'click', () => {
    resetDeliveryQrSession();
    clearDeliveryStockItemSelection();
    setDeliveryQrStatus('Lista de leitura limpa.');
  });
  bindAppListener(document.getElementById('delivery-qr-image'), 'change', handleDeliveryQrImageUpload);
  bindAppListener(document.getElementById('delivery-employee-qr-apply'), 'click', applyEmployeeQrLookup);
  bindAppListener(document.getElementById('delivery-employee-qr-scan'), 'keyup', (event) => {
    if (event.key === 'Enter') applyEmployeeQrLookup();
  });
  // Acesso do colaborador: gerar link / QR / copiar / abrir / enviar (F-05 reativado)
  bindAppListener(document.getElementById('delivery-employee-link-generate'), 'click', () => { void generateDeliveryEmployeeLink(); });
  bindAppListener(document.getElementById('delivery-employee-link-qr'), 'click', () => { void showDeliveryEmployeeLinkQr(); });
  bindAppListener(document.getElementById('delivery-employee-link-copy'), 'click', () => { void copyDeliveryEmployeeLink(); });
  bindAppListener(document.getElementById('delivery-employee-link-open'), 'click', openDeliveryEmployeeLink);
  bindAppListener(document.getElementById('delivery-employee-link-whatsapp'), 'click', () => { void sendDeliveryEmployeeMessage('whatsapp'); });
  bindAppListener(document.getElementById('delivery-employee-link-email'), 'click', () => { void sendDeliveryEmployeeMessage('email'); });
  bindAppListener(document.getElementById('delivery-epi'), 'change', refreshDeliveryContext);
  bindAppListener(document.querySelector('#delivery-form input[name="delivery_date"]'), 'change', () => {
    applyDeliveryReplacementSuggestion({ force: true });
  });
  bindAppListener(document.querySelector('#delivery-form input[name="next_replacement_date"]'), 'input', (event) => {
    event.target.dataset.autoSuggested = '0';
  });
  bindAppListener(refs.deliveryIsDevolution, 'change', () => {
    const enabled = Boolean(refs.deliveryIsDevolution?.checked);
    if (refs.deliveryDevolutionFields) refs.deliveryDevolutionFields.style.display = enabled ? 'grid' : 'none';
    const submitButton = document.querySelector('#delivery-form button[type="submit"]');
    if (submitButton) submitButton.textContent = enabled ? tr('delivery.registerReturn', 'Registrar devolução') : tr('delivery.save', 'Registrar EPI');
    if (refs.deliverySignatureStatus) {
      refs.deliverySignatureStatus.textContent = enabled
        ? tr('delivery.returnSignatureOptional', 'Assinatura opcional para devolução (pode assinar agora ou no fechamento da ficha).')
        : tr('delivery.signaturePending', 'Assinatura pendente.');
    }
  });
  bindAppListener(document.getElementById('delivery-employee'), 'change', () => {
    syncDeliveryQrSessionOwner();
    clearDeliveryStockItemSelection();
    resetDeliverySignatureDraft();
    state.deliveryReturnCandidates = [];
    state.deliveryReturnScopeKey = '';
    refreshDeliveryContext({ syncUnit: true });
    void loadAvailableQrsForSelectedEpi();
  });
  bindAppListener(document.getElementById('delivery-epi'), 'change', () => {
    clearDeliveryStockItemSelection();
    state.deliveryReturnCandidates = [];
    state.deliveryReturnScopeKey = '';
    refreshDeliveryContext();
    applyDeliveryReplacementSuggestion({ force: true });
    void loadAvailableQrsForSelectedEpi();
  });
  bindAppListener(refs.deliveryAvailableQrApply, 'click', () => { void applySelectedAvailableDeliveryQr(); });
  bindAppListener(refs.deliveryEpiSearchResults, 'click', (event) => {
    const button = event.target.closest('[data-delivery-epi-pick]');
    if (!button) return;
    selectDeliveryEpiFromSearch(button.dataset.deliveryEpiPick);
  });

  bindSearchInput(refs.userFilterSearch, syncUserFilters, 140);
  bindAppListener(refs.userFilterCompany, 'change', syncUserFilters);
  bindAppListener(refs.userFilterRole, 'change', syncUserFilters);
  bindAppListener(refs.userFilterStatus, 'change', syncUserFilters);
  bindAppListener(refs.unitsFilterCompany, 'change', syncUnitsSearchFilters);
  bindAppListener(refs.unitsFilterType, 'change', syncUnitsSearchFilters);
  bindSearchInput(refs.unitsFilterName, syncUnitsSearchFilters, 120);
  bindSearchInput(refs.unitsFilterCity, syncUnitsSearchFilters, 120);
  bindSearchInput(refs.legalEntitiesFilterSearch, syncLegalEntitiesFilters, 120);
  bindAppListener(refs.legalEntitiesFilterType, 'change', syncLegalEntitiesFilters);
  bindAppListener(refs.legalEntitiesShowInactive, 'change', syncLegalEntitiesFilters);
  bindAppListener(document.getElementById('legal-entity-cancel-edit'), 'click', resetLegalEntityForm);
  bindAppListener(refs.legalEntitiesTable, 'click', (event) => {
    const edit = event.target.dataset.legalEntityEdit;
    if (edit) { startEditLegalEntity(edit); return; }
    const deactivate = event.target.dataset.legalEntityDeactivate;
    if (deactivate) void deactivateLegalEntity(deactivate);
  });
  bindSearchInput(refs.outsourcedCompaniesFilterSearch, syncOutsourcedCompaniesFilters, 120);
  bindAppListener(refs.outsourcedCompaniesFilterKind, 'change', syncOutsourcedCompaniesFilters);
  bindAppListener(document.getElementById('outsourced-company-cancel-edit'), 'click', resetOutsourcedCompanyForm);
  bindAppListener(refs.outsourcedCompaniesTable, 'click', (event) => {
    const edit = event.target.dataset.outsourcedCompanyEdit;
    if (edit) { startEditOutsourcedCompany(edit); return; }
    const promote = event.target.dataset.outsourcedCompanyPromote;
    if (promote) { void promoteOutsourcedCompany(promote); return; }
    const requestUpdate = event.target.dataset.outsourcedCompanyRequestUpdate;
    if (requestUpdate) { void requestOutsourcedCompanyUpdate(requestUpdate); return; }
    const toggleLink = event.target.dataset.outsourcedCompanyToggleLink;
    if (toggleLink) void toggleOutsourcedCompanyUnitLink(toggleLink, event.target.dataset.activate === '1');
  });
  bindAppListener(refs.outsourcedCompanyUnitArchivedTable, 'click', (event) => {
    const toggleLink = event.target.dataset.outsourcedCompanyToggleLink;
    if (toggleLink) void toggleOutsourcedCompanyUnitLink(toggleLink, event.target.dataset.activate === '1');
  });
  bindAppListener(refs.outsourcedCompaniesAvailableTable, 'click', (event) => {
    const link = event.target.dataset.outsourcedCompanyLink;
    if (link) void linkOutsourcedCompanyToMyUnit(link);
  });
  bindAppListener(refs.outsourcedCompanyUpdateRequestsTable, 'click', (event) => {
    const resolveId = event.target.dataset.outsourcedCompanyUpdateRequestResolve;
    if (resolveId) void resolveOutsourcedCompanyUpdateRequest(resolveId);
  });
  bindSearchInput(refs.outsourcedEmployeesFilterSearch, syncOutsourcedEmployeesFilters, 120);
  bindDataMigrationEvents();
  bindAppListener(document.getElementById('outsourced-employee-cancel-edit'), 'click', resetOutsourcedEmployeeForm);
  bindAppListener(refs.outsourcedEmployeesTable, 'click', (event) => {
    const edit = event.target.dataset.outsourcedEmployeeEdit;
    if (edit) { void startEditOutsourcedEmployee(edit); return; }
    const archive = event.target.dataset.outsourcedEmployeeArchive;
    if (archive) void archiveOutsourcedEmployee(archive);
  });
  bindAppListener(refs.archivedUnitsFilterCompany, 'change', syncArchivedUnitsFilters);
  bindAppListener(refs.archivedUnitsFilterDate, 'change', syncArchivedUnitsFilters);
  bindSearchInput(refs.archivedUnitsFilterReason, syncArchivedUnitsFilters, 120);
  bindSearchInput(refs.archivedUnitsFilterUser, syncArchivedUnitsFilters, 120);
  bindAppListener(refs.archivedUnitsTable, 'click', (event) => {
    if (event.target.dataset.unitRestore) restoreArchivedUnit(event.target.dataset.unitRestore);
    if (event.target.dataset.unitPurge) purgeArchivedUnit(event.target.dataset.unitPurge);
  });
  [['employee', 'archivedEmployees'], ['epi', 'archivedEpis'], ['outsourcedCompany', 'archivedOutsourcedCompanies'], ['outsourcedEmployee', 'archivedOutsourcedEmployees']].forEach(([kind, prefix]) => {
    bindAppListener(refs[`${prefix}FilterCompany`], 'change', () => syncArchivedRecordsFilters(kind));
    bindAppListener(refs[`${prefix}FilterDate`], 'change', () => syncArchivedRecordsFilters(kind));
    bindSearchInput(refs[`${prefix}FilterReason`], () => syncArchivedRecordsFilters(kind), 120);
    bindSearchInput(refs[`${prefix}FilterUser`], () => syncArchivedRecordsFilters(kind), 120);
    bindAppListener(refs[`${prefix}Table`], 'click', (event) => {
      const restoreRef = event.target.dataset.archivedRestore;
      const purgeRef = event.target.dataset.archivedPurge;
      if (restoreRef) restoreArchivedRecord(...restoreRef.split(':'));
      if (purgeRef) purgeArchivedRecord(...purgeRef.split(':'));
    });
  });

  bindAppListener(refs.employeesFilterCompany, 'change', () => syncEmployeesSearchFilters('employees'));
  bindAppListener(refs.employeesFilterUnit, 'change', () => syncEmployeesSearchFilters('employees'));
  bindSearchInput(refs.employeesFilterSearch, () => syncEmployeesSearchFilters('employees'), 120);
  bindSearchInput(refs.employeesFilterSector, () => syncEmployeesSearchFilters('employees'), 120);
  bindSearchInput(refs.employeesFilterRole, () => syncEmployeesSearchFilters('employees'), 120);

  bindAppListener(refs.employeesOpsFilterCompany, 'change', () => syncEmployeesSearchFilters('ops'));
  bindAppListener(refs.employeesOpsFilterUnit, 'change', () => syncEmployeesSearchFilters('ops'));
  bindSearchInput(refs.employeesOpsFilterSearch, () => syncEmployeesSearchFilters('ops'), 120);
  bindSearchInput(refs.employeesOpsFilterSector, () => syncEmployeesSearchFilters('ops'), 120);
  bindSearchInput(refs.employeesOpsFilterRole, () => syncEmployeesSearchFilters('ops'), 120);

  bindAppListener(refs.episFilterCompany, 'change', syncEpisSearchFilters);
  bindAppListener(refs.episFilterUnit, 'change', syncEpisSearchFilters);
  bindSearchInput(refs.episFilterSearch, syncEpisSearchFilters, 120);
  bindSearchInput(refs.episFilterProtection, syncEpisSearchFilters, 120);
  bindSearchInput(refs.episFilterSection, syncEpisSearchFilters, 120);
  bindSearchInput(refs.episFilterManufacturer, syncEpisSearchFilters, 120);
  bindSearchInput(refs.episFilterSupplier, syncEpisSearchFilters, 120);
  bindAppListener(refs.episFilterValidity, 'change', syncEpisSearchFilters);

  bindAppListener(refs.deliveriesFilterCompany, 'change', syncDeliveriesSearchFilters);
  bindAppListener(refs.deliveriesFilterUnit, 'change', syncDeliveriesSearchFilters);
  bindSearchInput(refs.deliveriesFilterEmployee, syncDeliveriesSearchFilters, 120);
  bindSearchInput(refs.deliveriesFilterEpi, syncDeliveriesSearchFilters, 120);
  bindAppListener(refs.deliveriesFilterDateFrom, 'change', syncDeliveriesSearchFilters);
  bindAppListener(refs.deliveriesFilterDateTo, 'change', syncDeliveriesSearchFilters);
  bindAppListener(refs.deliveriesFilterStatus, 'change', syncDeliveriesSearchFilters);

  bindAppListener(refs.fichaFilterCompany, 'change', syncFichaSearchFilters);
  bindAppListener(refs.fichaFilterUnit, 'change', syncFichaSearchFilters);
  bindSearchInput(refs.fichaFilterSearch, syncFichaSearchFilters, 120);

  bindAppListener(refs.userForm?.elements.company_id, 'change', () => {
    populateLinkedEmployeeOptions();
    syncUserEmployeeLink();
  });
  bindAppListener(refs.userForm?.elements.linked_employee_id, 'change', syncUserEmployeeLink);
  bindAppListener(refs.userForm?.elements.role, 'change', syncUserFormAccess);
  bindSearchInput(refs.userLinkedEmployeeSearch, () => {
    const previousValue = String(refs.userForm?.elements.linked_employee_id?.value || '');
    populateLinkedEmployeeOptions();
    if (refs.userForm?.elements.linked_employee_id) {
      const stillExists = Array.from(refs.userForm.elements.linked_employee_id.options || []).some((option) => String(option.value) === previousValue);
      refs.userForm.elements.linked_employee_id.value = stillExists ? previousValue : '';
    }
    syncUserEmployeeLink();
  });
  bindAppListener(refs.userLinkedEmployeeResults, 'click', (event) => {
    const button = event.target.closest('[data-user-linked-pick]');
    if (!button || !refs.userForm?.elements?.linked_employee_id) return;
    refs.userForm.elements.linked_employee_id.value = String(button.dataset.userLinkedPick || '');
    syncUserEmployeeLink();
  });
  bindAppListener(refs.fichaEmployee, 'change', renderFicha);
  // Devolução de EPI — delegação de evento na tabela de entregas
  bindAppListener(refs.deliveriesTable, 'click', (event) => {
    // P2-1 — botão "Detalhes" abre o drawer lateral.
    const detailBtn = event.target?.closest?.('[data-delivery-detail-id]');
    if (detailBtn) {
      openDeliveryDetailDrawer(detailBtn.getAttribute('data-delivery-detail-id'));
      return;
    }
    const btn = (event.target).closest('[data-dev-delivery]');
    if (!btn) return;
    openDevolutionModal(
      btn.getAttribute('data-dev-delivery'),
      btn.getAttribute('data-dev-epi'),
      btn.getAttribute('data-dev-emp')
    );
  });

  // P1-1 — navegação de páginas da tabela de entregas.
  bindAppListener(refs.deliveriesPagination, 'click', (event) => {
    const btn = event.target?.closest?.('[data-ds-page]');
    if (!btn || btn.disabled) return;
    const target = parseInt(btn.dataset.dsPage, 10);
    if (!Number.isFinite(target)) return;
    if (state.pagination) state.pagination.deliveries = target;
    renderTables();
  });
  // P1-1 — navegação de páginas da tabela de colaboradores.
  bindAppListener(refs.employeesPagination, 'click', (event) => {
    const btn = event.target?.closest?.('[data-ds-page]');
    if (!btn || btn.disabled) return;
    const target = parseInt(btn.dataset.dsPage, 10);
    if (!Number.isFinite(target)) return;
    if (state.pagination) state.pagination.employees = target;
    renderTables();
  });
  // Ações em lote de Colaboradores (componente reutilizável do DS).
  bindAppListener(refs.employeesTable, 'change', (event) => {
    const cb = event.target?.closest?.('[data-emp-check]');
    if (!cb || !employeesBulk) return;
    employeesBulk.toggle(cb.dataset.empCheck, cb.checked);
    const pageIds = globalThis.dsPaginate(currentEmployeesBulkScope(), state.pagination?.employees || 1, EMPLOYEES_PER_PAGE).pageItems.map((e) => e.id);
    renderEmployeesBulkUi(pageIds);
  });
  bindAppListener(refs.employeesSelectAll, 'change', (event) => {
    if (!employeesBulk) return;
    const page = globalThis.dsPaginate(currentEmployeesBulkScope(), state.pagination?.employees || 1, EMPLOYEES_PER_PAGE);
    employeesBulk.setPage(page.pageItems.map((e) => e.id), event.target.checked);
    renderTables();
  });
  bindAppListener(refs.employeesBulkBar, 'click', (event) => {
    const btn = event.target?.closest?.('[data-ds-bulk-action]');
    if (!btn || !employeesBulk) return;
    const action = btn.dataset.dsBulkAction;
    if (action === '__clear') { employeesBulk.clear(); renderTables(); return; }
    if (action === 'export') { exportSelectedEmployeesCsv(); }
  });
  // Navegação de páginas do catálogo de EPIs.
  bindAppListener(refs.episPagination, 'click', (event) => {
    const btn = event.target?.closest?.('[data-ds-page]');
    if (!btn || btn.disabled) return;
    const target = parseInt(btn.dataset.dsPage, 10);
    if (!Number.isFinite(target)) return;
    if (state.pagination) state.pagination.epis = target;
    renderTables();
  });

  // P1-7 — remoção de chips de filtros ativos (Entregas).
  bindAppListener(document.getElementById('deliveries-filter-chips'), 'click', (event) => {
    if (event.target?.closest?.('[data-ds-filter-clear-all]')) { clearDeliveriesFilterChip('all'); return; }
    const chip = event.target?.closest?.('[data-ds-filter-clear]');
    if (chip) clearDeliveriesFilterChip(chip.dataset.dsFilterClear);
  });

  // Ficha de EPI — botoes visualizar e imprimir
  bindAppListener(document.getElementById('ficha-btn-visualizar'), 'click', () => {
    const empId = refs.fichaEmployee?.value;
    if (!empId) return alert('Selecione um colaborador.');
    abrirFichaEpiHTML(empId);
  });
  bindAppListener(document.getElementById('ficha-btn-imprimir'), 'click', () => {
    const empId = refs.fichaEmployee?.value;
    if (!empId) return alert('Selecione um colaborador.');
    imprimirFichaEpi(empId);
  });
  bindAppListener(document.getElementById('ficha-config-form'), 'submit', (event) => { void saveFichaConfig(event); });
  // master_admin: trocar a empresa ativa recarrega a Ficha daquele tenant.
  bindAppListener(document.getElementById('ficha-config-company'), 'change', () => { void loadFichaConfig(); });
  bindAppListener(refs.configRulesForm, 'submit', (event) => { void onSubmitConfigurationRule(event); });
  bindAppListener(refs.configRulesTable, 'click', (event) => {
    const button = event.target.closest('[data-remove-config-rule]');
    if (!button) return;
    void removeConfigurationRule(button.dataset.removeConfigRule);
  });
  bindAppListener(refs.configFrameworkForm, 'submit', (event) => { void saveConfigurationFramework(event); });
  bindAppListener(refs.moduleVisibilityRole, 'change', () => { syncModuleVisibilityUnitVisibility(); renderModuleVisibilityCheckboxes(); renderModuleVisibilityDefaultPanel(); });
  bindAppListener(refs.moduleVisibilityUnit, 'change', () => { renderModuleVisibilityCheckboxes(); });
  bindAppListener(refs.moduleVisibilityForm, 'submit', (event) => { void onSubmitModuleVisibility(event); });
  [refs.fichaAuditEmployee, refs.fichaAuditManager, refs.fichaAuditAction, refs.fichaAuditDateFrom, refs.fichaAuditDateTo]
    .forEach((el) => bindAppListener(el, 'change', () => { void loadFichaAuditLogs(); }));

  const onFichaViewClick = (event) => {
    const copyButton = event.target.closest('[data-ficha-copy-message]');
    if (copyButton) {
      void copyFichaPeriodMessage(copyButton.dataset.fichaCopyMessage);
      return;
    }
    const button = event.target.closest('[data-ficha-finalize]');
    if (!button) return;
    if (button.dataset.loading === '1') return;
    console.info('[ficha] finalizar período clicado');
    void finalizeFichaPeriod(button.dataset.fichaFinalize, { button });
  };
  if (!state.fichaFinalizeClickBound) {
    state.fichaFinalizeClickBound = true;
    bindAppListener(document, 'click', onFichaViewClick);
  }
  bindSearchInput(refs.approvedEpiSearchName, renderApprovedEpis, 120);
  bindSearchInput(refs.approvedEpiSearchProtection, renderApprovedEpis, 120);
  bindSearchInput(refs.approvedEpiSearchCa, renderApprovedEpis, 120);
  bindSearchInput(refs.approvedEpiSearchManufacturer, renderApprovedEpis, 120);
  bindSearchInput(refs.approvedEpiSearchSection, renderApprovedEpis, 120);
  bindSearchInput(refs.dashboardGlobalSearch, () => {
    state.dashboardFilters.query = String(refs.dashboardGlobalSearch?.value || '').trim();
    renderAlerts();
    renderLatestDeliveries();
  }, 120);
  bindAppListener(refs.dashboardRefreshNow, 'click', async () => {
    try {
      updatePhase3ContextStatus('dashboard', 'loading', 'Atualizando...');
      await loadBootstrap();
    } catch (error) {
      alert(error.message);
    }
  });
  bindAppListener(refs.stockFilterProtection, 'change', loadStockEpis);
  bindSearchInput(refs.stockFilterName, loadStockEpis, 220);
  bindSearchInput(refs.stockFilterSection, loadStockEpis, 220);
  bindSearchInput(refs.stockFilterManufacturer, loadStockEpis, 220);
  bindSearchInput(refs.stockFilterCa, loadStockEpis, 220);
  bindSearchInput(refs.stockEpiMovementSearchName, scheduleStockMovementSearchLoad, 150);
  bindSearchInput(refs.stockEpiMovementSearchManufacturer, scheduleStockMovementSearchLoad, 150);
  bindSearchInput(refs.stockEpiMovementSearchName, renderStockEpiSearchResults, 80);
  bindSearchInput(refs.stockEpiMovementSearchManufacturer, renderStockEpiSearchResults, 80);
  bindAppListener(refs.stockEpiMovementSearchResults, 'click', (event) => {
    const pickButton = event.target.closest('[data-stock-epi-pick]');
    if (!pickButton) return;
    selectStockEpiFromSearch(pickButton.dataset.stockEpiPick);
  });

  bindAppListener(document.getElementById('report-filter-form'), 'submit', async (event) => {
    event.preventDefault();
    if (!requirePermission('reports:view')) return;
    if (state.reportsRequestInFlight) return;
    state.reportsRequestInFlight = true;
    try {
      await renderReports(collectReportFilters());
    } catch (error) {
      console.error('[reports] Falha ao aplicar filtros', error);
      alert(error?.message || 'Não foi possível carregar o relatório com os filtros informados.');
    } finally {
      state.reportsRequestInFlight = false;
    }
  });
  bindAppListener(document.getElementById('report-export-pdf'), 'click', exportReportPdf);
  bindAppListener(document.getElementById('report-company'), 'change', syncReportOptions);
  bindAppListener(document.getElementById('report-unit'), 'change', syncReportOptions);
  bindAppListener(refs.reportArchiveTable, 'click', (event) => {
    const target = event.target;
    const viewId = target.dataset.archiveView;
    const printId = target.dataset.archivePrint;
    const exportId = target.dataset.archiveExport;
    if (viewId) {
      globalThis.open(`/api/ficha-archive/${viewId}.html?action=snapshot_view&${actorQuery()}`, '_blank', 'noopener');
    }
    if (printId) {
      globalThis.open(`/api/ficha-archive/${printId}.html?action=snapshot_print&${actorQuery()}`, '_blank', 'noopener');
    }
    if (exportId) {
      globalThis.open(`/api/ficha-archive/${exportId}.html?action=snapshot_export&${actorQuery()}`, '_blank', 'noopener');
    }
  });

  bindAppListener(refs.fichaRetentionForm, 'submit', async (event) => {
    event.preventDefault();
    if (!hasConfigurationAccess()) return;
    try {
      const payload = await api('/api/ficha-retention-policy', {
        method: 'POST',
        body: JSON.stringify({
          actor_user_id: state.user.id,
          retention_years: Number(refs.fichaRetentionYears?.value || 5),
          purge_enabled: Boolean(refs.fichaRetentionPurgeEnabled?.checked),
        })
      });
      state.fichaRetentionPolicy = payload || state.fichaRetentionPolicy;
      renderRetentionPolicy();
      alert('Política de retenção atualizada com sucesso.');
    } catch (error) {
      alert(error.message);
    }
  });

  // ── Configurações → Regras → Arquivamento ─────────────────────────────────
  // Retenção configurável por tenant para Unidades, EPIs e Colaboradores.
  // A regra da Ficha de EPI (5 anos, NR-6) tem formulário próprio e não é
  // alterada por esta política.
  bindAppListener(refs.archivalPolicyForm, 'submit', async (event) => {
    event.preventDefault();
    if (!hasConfigurationAccess()) return;
    try {
      const payload = await api('/api/archival-policy', {
        method: 'PUT',
        body: JSON.stringify({
          actor_user_id: state.user.id,
          unit_retention_years: Number(refs.archivalRetentionUnits?.value || 5),
          epi_retention_years: Number(refs.archivalRetentionEpis?.value || 5),
          employee_retention_years: Number(refs.archivalRetentionEmployees?.value || 5),
        }),
      });
      if (refs.archivalRetentionUnits) refs.archivalRetentionUnits.value = String(payload.unit_retention_years ?? refs.archivalRetentionUnits.value);
      if (refs.archivalRetentionEpis) refs.archivalRetentionEpis.value = String(payload.epi_retention_years ?? refs.archivalRetentionEpis.value);
      if (refs.archivalRetentionEmployees) refs.archivalRetentionEmployees.value = String(payload.employee_retention_years ?? refs.archivalRetentionEmployees.value);
      if (refs.archivalPolicyFeedback) refs.archivalPolicyFeedback.textContent = tr('rules.archivalSaved', 'Política de arquivamento salva com sucesso.');
      alert(tr('rules.archivalSaved', 'Política de arquivamento salva com sucesso.'));
    } catch (error) {
      if (refs.archivalPolicyFeedback) refs.archivalPolicyFeedback.textContent = error.message;
      alert(error.message);
    }
  });

  bindAppListener(refs.fichaRetentionPurgeRun, 'click', async () => {
    if (!hasConfigurationAccess()) return;
    if (!(await confirmDestructive({ title: 'Expiração/purge', message: 'Executar rotina de expiração/purge de snapshots agora?', confirmLabel: 'Executar', variant: 'warning' }))) return;
    try {
      await api('/api/ficha-archive/purge-expired', {
        method: 'POST',
        body: JSON.stringify({ actor_user_id: state.user.id })
      });
      await renderReports(collectReportFilters());
      alert('Rotina de retenção executada com sucesso.');
    } catch (error) {
      alert(error.message);
    }
  });

  refs.menu?.querySelectorAll('.menu-link[data-view]').forEach((button) =>
    bindAppListener(button, 'click', (event) => {
      event.preventDefault();
      const targetView = button.dataset.view;
      if (!targetView) return;
      if (isPhase3ModernUiEnabled()) updatePhase3ContextStatus(targetView, 'loading', 'Carregando área...');
      navigateToView(targetView, { historyMode: isSpaNavigationEnabled() ? 'push' : null, partial: isSpaNavigationEnabled() });
    })
  );
  bindAppListener(refs.topConfigTrigger, 'click', openSettingsDrawer);
  setupThemeToggle();
  bindAppListener(refs.interactiveNavTabs, 'click', (event) => {
    const button = event.target?.closest?.('[data-nav-tab-view]');
    const targetView = button?.dataset?.navTabView;
    if (!targetView) return;
    navigateToView(targetView, { historyMode: isSpaNavigationEnabled() ? 'push' : null, partial: isSpaNavigationEnabled() });
  });

  bindAppListener(refs.companiesTable, 'click', (event) => {
    if (event.target.dataset.companyDetails) {
      state.selectedCompanyId = event.target.dataset.companyDetails;
      renderCompanies();
      renderCompanyDetails(event.target.dataset.companyDetails);
      document.querySelector('.company-details-card')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    if (event.target.dataset.companyEdit) startEditCompany(event.target.dataset.companyEdit);
    if (event.target.dataset.companyLogo) openCompanyLogoEditor(event.target.dataset.companyLogo);
    if (event.target.dataset.companyToggle) toggleCompany(event.target.dataset.companyToggle, Number(event.target.dataset.companyActive));
    if (event.target.dataset.companyCommercial) {
      if (!canAccessCommercialArea()) {
        alert('Seu perfil não pode acessar a área Comercial.');
        return;
      }
      state.selectedCompanyId = event.target.dataset.companyCommercial;
      fillCommercialForm(event.target.dataset.companyCommercial);
      showView('comercial');
    }
  });
  bindAppListener(refs.companyDetails, 'click', (event) => {
    const companyId = event.target?.dataset?.companyViewContract;
    if (!companyId) return;
    const params = new URLSearchParams({ actor_user_id: state.user.id, company_id: String(companyId) });
    globalThis.open(`/api/commercial-contract.pdf?${params.toString()}`, '_blank');
  });
    
  bindAppListener(document.getElementById('comercial-view'), 'click', (event) => {
    if (event.target.dataset.companyCommercial) {
      fillCommercialForm(event.target.dataset.companyCommercial);
    }
    if (event.target.dataset.commercialToggle) {
      toggleCommercialStatus(event.target.dataset.commercialToggle, event.target.dataset.commercialMode);
    }
  });

  function handleUsersTableClick(event) {
    const target = event.target;
    const handlers = {
      userEdit: () => startEditUser(target.dataset.userEdit),
      userDelete: () => deleteUser(target.dataset.userDelete),
      userEmployeeQr: () => printEmployeeAccessQr(target.dataset.userEmployeeQr),
      userPromoteAdmin: () => updateUserAccess(target.dataset.userPromoteAdmin, { role: 'admin' }, 'Perfil alterado para Administrador.'),
      userPromoteGeneral: () => updateUserAccess(target.dataset.userPromoteGeneral, { role: 'general_admin' }, 'Perfil alterado para Administrador Geral.'),
      userDemoteAdmin: () => updateUserAccess(target.dataset.userDemoteAdmin, { role: 'user' }, 'Administrador rebaixado para Usuário.'),
      userDemoteGeneral: () => updateUserAccess(target.dataset.userDemoteGeneral, { role: 'admin' }, 'Administrador Geral rebaixado para Administrador.')
    };

    for (const [key, handler] of Object.entries(handlers)) {
      if (target.dataset[key]) {
        handler();
        return;
      }
    }

    if (target.dataset.userToggle) {
      const user = state.users.find((item) => String(item.id) === String(target.dataset.userToggle));
      if (user) updateUserAccess(user.id, { active: Number(user.active) === 1 ? 0 : 1 }, Number(user.active) === 1 ? 'Usuário desativado.' : 'Usuário reativado.');
    }
    if (target.dataset.userRecoveryToken) {
      void generateRecoveryToken(target.dataset.userRecoveryToken);
    }
  }

  bindAppListener(refs.usersTable, 'click', handleUsersTableClick);

  bindAppListener(refs.employeesTable, 'click', (event) => {
    const button = event.target.closest('button');
    if (!button) return;
    if (button.dataset.employeeEdit) { startEditEmployee(button.dataset.employeeEdit); }
    if (button.dataset.employeeArchive) { archiveEntityRecord('employee', button.dataset.employeeArchive); }
  });
  if (refs.employeesOpsTable) {
    bindAppListener(refs.employeesOpsTable, 'click', (event) => {
      const button = event.target.closest('[data-ops-select-employee]');
      if (!button) return;
      const employeeId = button.dataset.opsSelectEmployee;
      const field = document.getElementById('movement-employee-id');
      if (field) {
        field.value = employeeId;
        field.dispatchEvent(new Event('change', { bubbles: true }));
        document.getElementById('movement-form')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  }
  bindAppListener(refs.unitsTable, 'click', (event) => {
    if (event.target.dataset.unitEdit) startEditUnit(event.target.dataset.unitEdit);
    if (event.target.dataset.unitArchive) archiveUnit(event.target.dataset.unitArchive);
  });
  bindAppListener(refs.episTable, 'click', (event) => {
    if (event.target.dataset.epiEdit) startEditEpi(event.target.dataset.epiEdit);
    if (event.target.dataset.epiArchive) archiveEntityRecord('epi', event.target.dataset.epiArchive);
  });
  bindAppListener(document.getElementById('stock-minimum-selected-edit'), 'click', () => {
    if (!canManageMinimumStock()) {
      alert('Apenas Administrador Local e Gestor de EPI podem gerenciar estoque mí­nimo.');
      return;
    }
    if (!selectedStockEpi()) {
      alert('Selecione um EPI para editar o estoque mí­nimo.');
      return;
    }
    toggleSelectedMinimumStockEditMode(true);
  });

  bindAppListener(document.getElementById('stock-minimum-selected-save'), 'click', saveSelectedEpiMinimumStock);
  bindAppListener(document.getElementById('stock-minimum-selected-value'), 'keydown', (event) => {
    if (event.key !== 'Enter') return;
    if (!state.stockMinimumEditor.editing) return;
    event.preventDefault();
    saveSelectedEpiMinimumStock();
  });

  bindAppListener(document.getElementById('stock-print-labels'), 'click', () => {
    if (!state.stockGeneratedLabels.length) return alert('Nenhuma etiqueta gerada ainda. Registre uma entrada no estoque primeiro.');
    printStockLabels(state.stockGeneratedLabels, 1);
  });
  bindAppListener(document.getElementById('stock-reprint-label'), 'click', () => { void reprintStockLabelByQr(); });

  safeOn(globalThis, 'beforeunload', stopDeliveryQrCamera);
  safeOn(globalThis, 'pagehide', () => { void stopDeliveryQrCamera(); });
  safeOn(document, 'visibilitychange', () => {
    if (document.visibilityState === 'hidden') void stopDeliveryQrCamera();
  });
  safeOn(document.body, 'htmx:beforeSwap', (event) => {
    const swapTarget = event?.detail?.target || event?.target;
    if (!(swapTarget instanceof Element)) return;
    const touchesDeliveryView = swapTarget.id === 'entregas-view'
        || Boolean(swapTarget.closest?.('#entregas-view'))
        || Boolean(swapTarget.querySelector?.('#delivery-qr-camera-wrap, #delivery-qr-start, #delivery-qr-video'));
    if (touchesDeliveryView) void stopDeliveryQrCamera();
  });
  
  resetCompanyForm();
  ensureStockLabelCustomFieldBinding();

  const deliveryDateInput = document.querySelector('#delivery-form input[name="delivery_date"]');
  if (deliveryDateInput) {
    deliveryDateInput.value = new Date().toISOString().split('T')[0];
  }

  const nextReplacementInput = document.querySelector('#delivery-form input[name="next_replacement_date"]');
  if (nextReplacementInput) {
    nextReplacementInput.value = new Date().toISOString().split('T')[0];
    nextReplacementInput.dataset.autoSuggested = '1';
  }
  if (refs.deliveryReturnedDate) refs.deliveryReturnedDate.value = new Date().toISOString().split('T')[0];
  syncDeliveryDevolutionOptions();
  registerMultitabNavigationApi();
  setupViewTabs();

  showScreen(false);
  if (state.user) {
    let hasLoggedBootstrapFallback = false;
    const tryRestoreSession = async (attempt = 1) => {
      try {
        await loadBootstrap();
        showScreen(true);
        void maybeShowOnboardingWizard();
      } catch (error) {
        if (isSessionRestoreAuthError(error)) {
          clearBootstrapDegraded();
          clearSession();
          showScreen(false);
          setLoginMessage('Sessão expirada. Faça login novamente.', true);
          return;
        }
        if (isTemporaryBootstrapUnavailable(error)) {
          const MAX_RESTORE_ATTEMPTS = 6;
          const retryDelays = [3000, 5000, 8000, 12000, 15000];
          if (attempt < MAX_RESTORE_ATTEMPTS) {
            console.info('[auth] Backend inicializando — tentativa de restauração de sessão', { attempt, maxAttempts: MAX_RESTORE_ATTEMPTS });
            setLoginMessage(`Servidor inicializando. Tentando restabelecer sessão automaticamente (${attempt}/${MAX_RESTORE_ATTEMPTS})...`, true);
            const delay = retryDelays[attempt - 1] ?? 15000;
            setTimeout(() => {
              void tryRestoreSession(attempt + 1);
            }, delay);
          } else {
            console.warn('[auth] Backend indisponível após todas as tentativas de restauração de sessão', { attempt, error });
            setLoginMessage('Servidor temporariamente indisponível (bootstrap em andamento). Você pode tentar login manual agora.', true);
          }
          return;
        }
        if (!hasLoggedBootstrapFallback) {
          console.warn('[auth] fallback para login manual ativado');
          hasLoggedBootstrapFallback = true;
        }
        console.warn('[auth] bootstrap falhou, limpando sessão', error);
        clearBootstrapDegraded();
        clearSession();
        showScreen(false);
        setLoginMessage('Não foi possível restaurar sua sessão automaticamente. Faça login para continuar.', true);
      }
    };
    void tryRestoreSession();
  }
  applyDeliveryReplacementSuggestion({ force: true });
}

if (!globalThis.__EPI_APP_DOM_READY_BOUND__) {
  globalThis.__EPI_APP_DOM_READY_BOUND__ = true;
  safeOn(document, 'DOMContentLoaded', () => {
    init().catch((error) => {
      console.error(error);
      setLoginMessage('Erro ao carregar a tela de login. Recarregue a página e tente novamente.', true);
    });
  });
}

/**
 * Quando o idioma muda em tempo real, o motor i18n já re-traduz o DOM estático
 * (atributos data-i18n). Aqui re-renderizamos a tela ativa para que o conteúdo
 * dinâmico (cards de KPI, linhas de tabela, status chips gerados em JS) também
 * seja atualizado com o idioma correto.
 */
if (!globalThis.__EPI_APP_LANGCHANGE_BOUND__) {
  globalThis.__EPI_APP_LANGCHANGE_BOUND__ = true;
  let _langRerenderTimer = null;
  safeOn(globalThis, 'epi:langchange', () => {
    if (_langRerenderTimer) clearTimeout(_langRerenderTimer);
    _langRerenderTimer = setTimeout(() => {
      try {
        if (!state || !state.user) return; // só re-renderiza quando autenticado
        const activeView = document.querySelector('.view.active')?.id?.replace(/-view$/, '');
        if (activeView && typeof showView === 'function') {
          showView(activeView, { partial: false });
        }
        // Re-executa o refresh do módulo ativo para atualizar conteúdo JS-gerado
        // (cards de KPI, seletores de filtro, botões de ação) sem buscar novos dados.
        if (activeView && typeof resolveInteractiveToolsModule === 'function') {
          const mod = resolveInteractiveToolsModule(activeView);
          if (mod && typeof mod.refresh === 'function') {
            void Promise.resolve().then(() => mod.refresh());
          }
        }
        // Atualiza os filtros de usuário (seletor de perfil e status) se visível
        if (typeof populateUserFilters === 'function') {
          try { populateUserFilters(); } catch (_e) {}
        }
        // Re-renderiza tabelas (badges de status e perfil dos usuários, etc.)
        if (typeof renderTables === 'function') {
          try { renderTables(); } catch (_e) {}
        }
        // Atualiza o select de perfil do formulário de usuário
        if (typeof populateRoleOptions === 'function') {
          try { populateRoleOptions(); } catch (_e) {}
        }
        // Atualiza o select "Vincular Colaborador" com a opção "Sem vínculo" traduzida
        if (typeof populateLinkedEmployeeOptions === 'function') {
          try { populateLinkedEmployeeOptions(); } catch (_e) {}
        }
        // Atualiza os controles de funções de compras se visíveis
        if (typeof renderPurchaseFunctionControls === 'function') {
          try { renderPurchaseFunctionControls(); } catch (_e) {}
        }
        // Re-renderiza tabela, painel de detalhes e KPIs da tela de empresas
        if (typeof renderCompanies === 'function') {
          try { renderCompanies(); } catch (_e) {}
        }
        if (typeof renderCompanyDetails === 'function') {
          try { renderCompanyDetails(); } catch (_e) {}
        }
        if (typeof renderCompaniesSummary === 'function') {
          try { renderCompaniesSummary(); } catch (_e) {}
        }
      } catch (error) {
        reportNonCriticalError('[i18n] re-render da tela ativa falhou', error);
      }
    }, 60);
  });
}


// === FIM AUTO-SUGESTAO DATA PROXIMA TROCA v2 ===

function parsePositiveInteger(value) {
  const parsed = Number.parseInt(String(value ?? '').trim(), 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
}

function addDaysFromBaseDate(baseDateIso, days) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(baseDateIso || ''))) return '';
  const baseDate = new Date(`${baseDateIso}T00:00:00`);
  if (Number.isNaN(baseDate.getTime())) return '';
  baseDate.setDate(baseDate.getDate() + Number(days));
  return baseDate.toISOString().slice(0, 10);
}

function resolveDeliveryReplacementDays(epi) {
  if (!epi) return 0;
  const defaultDays = parsePositiveInteger(epi.default_replacement_days);
  if (defaultDays > 0) return defaultDays;
  const monthsFallback = parsePositiveInteger(epi.manufacturer_validity_months);
  return monthsFallback > 0 ? monthsFallback * 30 : 0;
}

function applyDeliveryReplacementSuggestion({ force = false } = {}) {
  const deliveryDateInput = document.querySelector('#delivery-form input[name="delivery_date"]');
  const nextReplacementInput = document.querySelector('#delivery-form input[name="next_replacement_date"]');
  const hint = document.getElementById('delivery-replacement-hint');
  const presets = document.getElementById('delivery-replacement-presets');
  if (!deliveryDateInput || !nextReplacementInput) return;
  const selectedEpiId = String(document.getElementById('delivery-epi')?.value || '').trim();
  const selectedEpi = (state.deliveryEpis || state.epis || []).find((item) => String(item.id) === selectedEpiId);
  const replacementDays = resolveDeliveryReplacementDays(selectedEpi);
  if (replacementDays <= 0) {
    if (hint) {
      hint.style.display = 'block';
      hint.textContent = 'Sem prazo padrão de troca para este EPI. Defina manualmente ou use os atalhos.';
    }
    if (presets) presets.style.display = 'flex';
    return;
  }
  const baseDate = String(deliveryDateInput.value || '').trim() || new Date().toISOString().slice(0, 10);
  const suggestedDate = addDaysFromBaseDate(baseDate, replacementDays);
  if (!suggestedDate) return;
  const currentValue = String(nextReplacementInput.value || '').trim();
  if (force || !currentValue || nextReplacementInput.dataset.autoSuggested === '1') {
    nextReplacementInput.value = suggestedDate;
    nextReplacementInput.dataset.autoSuggested = '1';
  }
  if (hint) {
    hint.style.display = 'block';
    hint.textContent = `Sugestão automática: entrega + ${replacementDays} dia(s).`;
  }
  if (presets) presets.style.display = 'flex';
}

// ── Módulo de Compras (Fase 2) ───────────────────────────────────────────────

const PURCHASE_STATUS_LABELS = {
  draft: 'Rascunho', open: 'Aberta', sent_to_buyer: 'C/ Comprador', quoted: 'Cotada',
  pending_approval: 'Cotação Enviada ao Aprovador', partially_approved: 'Aprov. Parcial',
  waiting_buyer_correction: 'Aguardando Correção do Comprador', buyer_resubmitted: 'Reenviada pelo Comprador',
  waiting_requester_correction: 'Aguardando Correção do Requisitante', requester_resubmitted: 'Reenviada pelo Requisitante',
  approved: 'Aprovada', rejected: 'Reprovada', postponed: 'Prorrogada',
  returned_to_buyer: 'Retornado ao Comprador',
  po_generated: 'PO Gerada', received_partial: 'Recebida Parcialmente', received: 'Recebida Totalmente', not_received: 'Item Não Recebido', pending_receipt: 'Pendente de Recebimento', checked: 'Conferida',
  closed: 'Fechada', cancelled: 'Cancelada'
};
const ITEM_STATUS_LABELS = {
  open: 'Aberto', included_in_request: 'Em Requisição', sent_to_buyer: 'C/ Comprador',
  quoted: 'Cotado', pending_approval: 'Aguard. Aprov.', approved: 'Aprovado',
  partially_approved: 'Aprov. Parcial', rejected: 'Rejeitado', ordered: 'Pedido',
  received_partial: 'Recebido Parcial', not_received: 'Não Recebido', received: 'Recebido', checked: 'Conferido', closed: 'Fechado',
  waiting_quote: 'Aguardando Cotação', waiting_admin_review: 'Em Compra'
};
const PURCHASE_APPROVAL_REJECTION_REASONS = ['Item não necessário', 'Valor acima do esperado', 'Quantidade incorreta', 'Fornecedor inadequado', 'EPI incompatível', 'Fora do escopo da solicitação', 'Outro'];

// P1-5 — etapas canônicas do recebimento da PO e mapeamento a partir do status.
const PO_STEPPER_STEPS = [
  { label: 'Pedido' },
  { label: 'Recebido' },
  { label: 'Conferido' },
  { label: 'Fechado' }
];
const PO_STEP_INDEX = {
  open: 0, sent_to_buyer: 0, quoted: 0, waiting_quote: 0, waiting_admin_review: 0,
  pending_approval: 0, postponed: 0, approved: 0, partially_approved: 0, ordered: 0,
  received_partial: 1, received: 1, not_received: 1,
  checked: 2,
  closed: 3
};
function buildPoStepper(status) {
  if (status === 'rejected') { return ''; } // fluxo terminal sem recebimento
  const idx = Object.prototype.hasOwnProperty.call(PO_STEP_INDEX, status) ? PO_STEP_INDEX[status] : 0;
  return globalThis.dsStepper(PO_STEPPER_STEPS, idx);
}


const PURCHASE_BUYER_QUOTE_STATUSES = ['sent_to_buyer', 'returned_to_buyer', 'quoted', 'waiting_buyer_correction', 'buyer_resubmitted', 'pending_approval', 'postponed'];

function isBuyerQuotationStatus(status) {
  return PURCHASE_BUYER_QUOTE_STATUSES.includes(String(status || ''));
}

let _purchaseDemands = [];
let _selectedDemands = new Set();
let _purchaseRequests = [];
let _manualRequestItems = [];
let _purchaseOrders = [];
let _currentPrDetail = null;
let _currentPoDetail = null;
let _poItems = [];

function fmtBrl(v) {
  return Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function purchaseStatusBadge(status, extra = '') {
  const colors = { approved: 'green', closed: 'green', received: 'green', received_partial: 'orange', checked: 'green', rejected: 'red', cancelled: 'red', pending_approval: 'orange', partially_approved: 'orange', postponed: 'orange', waiting_buyer_correction: 'orange', waiting_requester_correction: 'orange', buyer_resubmitted: 'orange', requester_resubmitted: 'orange' };
  const c = colors[status] || 'gray';
  const label = (PURCHASE_STATUS_LABELS[status] || status) + (extra ? ` — ${extra}` : '');
  return `<span class="status-chip" style="background:var(--color-${c === 'gray' ? 'bg-alt' : c === 'green' ? 'success-bg' : c === 'red' ? 'danger-bg' : 'warning-bg'});color:var(--color-${c === 'gray' ? 'text-muted' : c === 'green' ? 'success' : c === 'red' ? 'danger' : 'warning'})">${label}</span>`;
}

function _initDemandsCompanyFilter() {
  const filter = document.getElementById('compras-demands-company-filter');
  if (!filter) return;
  if (state.user?.role !== 'master_admin') { filter.style.display = 'none'; return; }
  filter.style.display = '';
  const companies = state.companies || [];
  const current = filter.value;
  filter.innerHTML = '<option value="">Todas as empresas</option>' +
    companies.map(c => `<option value="${c.id}"${String(c.id) === current ? ' selected' : ''}>${c.name} - ${c.cnpj}</option>`).join('');
}

async function loadPurchaseDemands() {
  const tbody = document.getElementById('compras-demands-tbody');
  const empty = document.getElementById('compras-demands-empty');
  const table = document.getElementById('compras-demands-table');
  if (!tbody) return;
  _initDemandsCompanyFilter();
  try {
    const companyFilter = document.getElementById('compras-demands-company-filter');
    const selectedCompany = companyFilter?.style.display !== 'none' ? (companyFilter?.value || '') : '';
    const companyParam = selectedCompany ? `&company_id=${encodeURIComponent(selectedCompany)}` : '';
    const res = await api(`/api/purchase-demands?${actorQuery()}${companyParam}`);
    _purchaseDemands = res.items || [];
    _selectedDemands.clear();
    const selectAll = document.getElementById('compras-demands-select-all');
    if (selectAll) selectAll.checked = false;
    if (!_purchaseDemands.length) {
      if (table) table.style.display = 'none';
      if (empty) empty.style.display = '';
      return;
    }
    if (table) table.style.display = '';
    if (empty) empty.style.display = 'none';
    const showCompanyCol = state.user?.role === 'master_admin' && !document.getElementById('compras-demands-company-filter')?.value;
    tbody.innerHTML = _purchaseDemands.map((d, i) => {
      const originLabel = d.demand_type === 'employee_request' ? '<span style="color:var(--color-primary)">Colaborador</span>' : '<span style="color:var(--color-warning)">Estoque Mínimo</span>';
      const companyTag = showCompanyCol && d.company_name ? `<br><small style="color:var(--color-text-muted)">${d.company_name}</small>` : '';
      const who = d.demand_type === 'employee_request'
        ? `${d.employee_name || '—'}${companyTag}<br><small>${d.unit_name || ''}</small>`
        : `${d.unit_name || '—'}${companyTag}`;
      const sector = d.demand_type === 'employee_request'
        ? `${d.employee_sector || '—'} / ${d.employee_role || '—'}`
        : (d.employee_sector && d.employee_sector !== 'Estoque baixo' ? d.employee_sector : '—');
      const sizeInfo = (() => {
        // Estoque mínimo: mostra TODOS os tamanhos cadastrados com atual/mínimo/sugestão.
        if (d.demand_type === 'low_stock' && Array.isArray(d.size_demands) && d.size_demands.length) {
          const parts = d.size_demands.map(s => {
            const sp = [s.glove_size !== 'N/A' ? `Luva:${s.glove_size}` : '', s.size !== 'N/A' ? `Tam:${s.size}` : '', s.uniform_size !== 'N/A' ? `Unif:${s.uniform_size}` : ''].filter(Boolean).join(' ') || 'Único';
            return `${sp} (atual ${s.current_stock}/mín ${s.minimum_stock} → +${s.suggested_quantity})`;
          }).join('<br>');
          if (parts) return parts;
        }
        if (Array.isArray(d.size_balances) && d.size_balances.length) {
          const parts = d.size_balances.map(s => {
            const sp = [s.glove_size !== 'N/A' ? `Luva:${s.glove_size}` : '', s.size !== 'N/A' ? `Tam:${s.size}` : '', s.uniform_size !== 'N/A' ? `Unif:${s.uniform_size}` : ''].filter(Boolean).join(' ');
            return sp ? `${sp}×${s.quantity}` : `Qtd:${s.quantity}`;
          }).filter(Boolean).join(', ');
          if (parts) return parts;
        }
        const flatSize = [d.glove_size && d.glove_size !== 'N/A' ? `Luva:${d.glove_size}` : '', d.size && d.size !== 'N/A' ? `Tam:${d.size}` : '', d.uniform_size && d.uniform_size !== 'N/A' ? `Unif:${d.uniform_size}` : ''].filter(Boolean).join(' ');
        return flatSize || (d.demand_type === 'low_stock' ? 'Sem rastreio por tamanho' : '—');
      })();
      const qty = d.demand_type === 'employee_request'
        ? (d.quantity || 1)
        : (Array.isArray(d.size_demands) && d.size_demands.length
            ? d.size_demands.reduce((s, x) => s + Number(x.suggested_quantity || 0), 0) || (d.quantity_requested || 1)
            : (d.quantity_requested || 1));
      const statusBadge = d.demand_type === 'low_stock'
        ? '<span style="color:var(--color-warning,#f59e0b);font-weight:600;font-size:11px;">Estoque Baixo</span>'
        : epiRequestStatusBadge(d.status || 'solicitado');
      return `<tr>
        <td><input type="checkbox" class="demand-check" data-demand-index="${i}"></td>
        <td>${originLabel}</td>
        <td>${d.epi_name || '—'}</td>
        <td>${d.ca || '—'}</td>
        <td>${d.manufacturer || '—'}</td>
        <td style="font-size:12px;">${d.supplier || '—'}</td>
        <td>${who}</td>
        <td style="font-size:12px;">${sector}</td>
        <td style="font-size:12px;">${sizeInfo}</td>
        <td>${qty}</td>
        <td style="font-size:11px;">${statusBadge}</td>
      </tr>`;
    }).join('');
    updateCreateRequestBtn();
  } catch(e) {
    if (empty) {
      empty.style.display = '';
      empty.textContent = isTemporaryBootstrapUnavailable(e)
        ? 'Sistema inicializando — clique em Atualizar para tentar novamente.'
        : 'Erro ao carregar demandas.';
    }
  }
}

function updateCreateRequestBtn() {
  const btn = document.getElementById('compras-create-request-btn');
  if (btn) btn.style.display = _selectedDemands.size > 0 ? '' : 'none';
}

async function loadPurchaseRequests() {
  const tbody = document.getElementById('compras-req-tbody');
  const empty = document.getElementById('compras-req-empty');
  const table = document.getElementById('compras-req-table');
  if (!tbody) return;
  const status = document.getElementById('compras-req-status-filter')?.value || '';
  try {
    const qs = status ? `?status=${encodeURIComponent(status)}&${actorQuery()}` : `?${actorQuery()}`;
    const res = await api(`/api/purchase-requests${qs}`);
    _purchaseRequests = res.items || [];
    if (!_purchaseRequests.length) {
      if (table) table.style.display = 'none';
      if (empty) empty.style.display = '';
      return;
    }
    if (table) table.style.display = '';
    if (empty) empty.style.display = 'none';
    tbody.innerHTML = _purchaseRequests.map(pr => {
      const postponedExtra = pr.status === 'postponed' && pr.postponed_until ? `Até: ${pr.postponed_until}` : '';
      const poInfo = pr.linked_po_number && ['approved','partially_approved','postponed'].includes(pr.status)
        ? `<br><small style="color:var(--color-text-muted);">PO: ${pr.linked_po_number}</small>` : '';
      return `<tr>
        <td>${pr.id}</td>
        <td>${pr.title || '—'}${poInfo}</td>
        <td>${pr.unit_name || '—'}</td>
        <td>${purchaseStatusBadge(pr.status, postponedExtra)}</td>
        <td>${pr.items_count || 0}</td>
        <td style="font-size:12px;">${pr.created_by_name || '—'}</td>
        <td style="font-size:12px;">${(pr.created_at || '').slice(0,10)}</td>
        <td><button class="ghost" style="font-size:12px;padding:3px 8px;" data-pr-detail="${pr.id}">Ver</button></td>
      </tr>`;
    }).join('');
  } catch(e) {
    if (empty) { empty.style.display = ''; empty.textContent = 'Erro ao carregar requisições.'; }
  }
}

async function loadPurchaseOrders() {
  const tbody = document.getElementById('compras-po-tbody');
  const empty = document.getElementById('compras-po-empty');
  const table = document.getElementById('compras-po-table');
  if (!tbody) return;
  const newPoBtn = document.getElementById('compras-new-po-btn');
  if (newPoBtn) newPoBtn.style.display = hasPermission('purchase_orders:create') ? '' : 'none';
  const status = document.getElementById('compras-po-status-filter')?.value || '';
  try {
    const qs = status ? `?status=${encodeURIComponent(status)}&${actorQuery()}` : `?${actorQuery()}`;
    const res = await api(`/api/purchase-orders${qs}`);
    _purchaseOrders = res.items || [];
    if (!_purchaseOrders.length) {
      if (table) table.style.display = 'none';
      if (empty) empty.style.display = '';
      return;
    }
    if (table) table.style.display = '';
    if (empty) empty.style.display = 'none';
    tbody.innerHTML = _purchaseOrders.map(po => `<tr>
      <td>${po.id}</td>
      <td>${po.po_number || '—'}</td>
      <td>${po.supplier || '—'}</td>
      <td>${po.unit_name || '—'}</td>
      <td>${purchaseStatusBadge(po.status)}</td>
      <td>${fmtBrl(po.total_value)}</td>
      <td>${po.items_count || 0}</td>
      <td style="font-size:12px;">${po.created_by_name || '—'}</td>
      <td style="font-size:12px;">${(po.created_at || '').slice(0,10)}</td>
      <td style="white-space:nowrap;"><button class="ghost" style="font-size:12px;padding:3px 8px;" data-po-detail="${po.id}">Ver</button> <button class="ghost" style="font-size:12px;padding:3px 8px;" onclick="openPoSupplierActionsModal(${po.id})">Fornecedor</button></td>
    </tr>`).join('');
  } catch(e) {
    if (empty) { empty.style.display = ''; empty.textContent = 'Erro ao carregar POs.'; }
  }
}

async function openPrDetail(prId) {
  try {
    const res = await api(`/api/purchase-requests/${prId}`);
    _currentPrDetail = res;
    const pr = _currentPrDetail.item;
    const items = _currentPrDetail.items || [];
    const titleEl = document.getElementById('compras-req-detail-title');
    if (titleEl) titleEl.textContent = `Requisição #${pr.id} — ${pr.title || ''}`;
    const detailEl = document.getElementById('compras-req-detail');
    if (detailEl) detailEl.style.display = '';
    const tbody = document.getElementById('compras-req-detail-tbody');
    if (tbody) tbody.innerHTML = items.map(i => {
      const sizeInfo = [i.glove_size !== 'N/A' ? `L:${i.glove_size}`:null, i.size !== 'N/A'?`T:${i.size}`:null, i.uniform_size !== 'N/A'?`U:${i.uniform_size}`:null].filter(Boolean).join(' ') || '—';
      return `<tr>
        <td>${i.epi_name || i.epi_display_name || '—'}</td>
        <td>${i.ca || i.epi_ca || '—'}</td>
        <td>${i.manufacturer || '—'}</td>
        <td>${i.supplier || '—'}</td>
        <td>${i.employee_name || '—'}</td>
        <td>${i.origin === 'employee_request' ? 'Colaborador' : 'Estoque Mín.'}</td>
        <td style="font-size:12px;">${sizeInfo}</td>
        <td>${i.quantity_requested || 1}</td>
        <td style="white-space:nowrap;">${i.unit_price ? fmtBrl(i.unit_price) : '—'}</td>
        <td style="white-space:nowrap;font-weight:${i.total_price ? '600' : '400'};">${i.total_price ? fmtBrl(i.total_price) : '—'}</td>
        <td>${ITEM_STATUS_LABELS[i.status] || i.status}</td>
      </tr>`;
    }).join('');
    const grandTotal = items.filter(i => i.status !== 'rejected').reduce((s, i) => s + Number(i.total_price || 0), 0);
    const totalEl = document.getElementById('compras-req-detail-total');
    const tfootEl = document.getElementById('compras-req-detail-tfoot');
    if (totalEl) totalEl.textContent = grandTotal > 0 ? fmtBrl(grandTotal) : '—';
    if (tfootEl) tfootEl.style.display = grandTotal > 0 ? '' : 'none';
    renderPrStatusActions(pr);
    renderPurchaseRequestEvents(_currentPrDetail.events || []);
    renderRequesterReviewTools(pr, items);
    _setupPrDetailActions(pr, items);
    detailEl?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch(e) {
    alert('Erro ao carregar requisição.');
  }
}


const PURCHASE_REVIEW_REASONS = {
  buyer: ['Valor acima do esperado', 'Fornecedor incorreto', 'Item com preço divergente', 'Cotação incompleta', 'Necessário novo fornecedor', 'Quantidade divergente', 'Outro'],
  requester: ['Acrescentar novos itens', 'Corrigir item existente', 'Revisar quantidade', 'Reavaliar item inicialmente reprovado', 'Justificar necessidade', 'Anexar informação complementar', 'Outro'],
  reject: ['Valor acima do esperado', 'Fornecedor incorreto', 'Item com preço divergente', 'Cotação incompleta', 'Quantidade divergente', 'Outro'],
};

function _workflowReasonOptions(group) {
  return (PURCHASE_REVIEW_REASONS[group] || []).map(reason => `<option value="${esc(reason)}">${esc(reason)}</option>`).join('');
}

function renderPurchaseRequestEvents(events) {
  const eventsEl = document.getElementById('compras-req-events');
  if (!eventsEl) return;
  eventsEl.innerHTML = (events || []).length ? events.map(e => {
    const fromTo = e.status_from ? ` <em>${esc(PURCHASE_STATUS_LABELS[e.status_from] || e.status_from)} → ${esc(PURCHASE_STATUS_LABELS[e.status_to] || e.status_to)}</em>` : '';
    const role = e.actor_role ? ` <small>(${esc(roleLabel(e.actor_role))})</small>` : '';
    const destination = e.destination ? ` <small>Destino: ${esc(e.destination)}</small>` : '';
    const reason = e.reason ? ` <small>Motivo: ${esc(e.reason)}</small>` : '';
    return `<div style="padding:6px 0;border-bottom:1px solid var(--color-border);">[${esc((e.created_at || '').slice(0,16).replace('T',' '))}] <strong>${esc(e.actor_name || 'Sistema')}</strong>${role} — ${esc(e.action || '')}${fromTo}${destination}${reason}${e.comment ? `<br><span>${esc(e.comment)}</span>` : ''}</div>`;
  }).join('') : '<em>Sem histórico.</em>';
}

function renderPrStatusActions(pr) {
  const container = document.getElementById('compras-req-detail-status-actions');
  if (!container) return;
  container.innerHTML = '';
  const role = state.user?.role || '';
  const isBuyer = role === 'buyer';
  const isApprover = role === 'approver';
  const isAdmin = ['admin', 'general_admin', 'registry_admin', 'master_admin'].includes(role);
  const canUpdate = hasPermission('purchase_requests:update');
  const canQuote = isBuyer || hasPermission('purchase_orders:create') || hasPermission('purchase_orders:upload');
  const canApprove = hasPermission('purchase_orders:approve');
  const actions = [];
  const actionKeys = new Set();
  const addAction = (config) => {
    const key = `${config.action || ''}:${config.to || ''}:${config.label || ''}`;
    if (actionKeys.has(key)) return;
    actionKeys.add(key);
    actions.push(config);
  };
  if (pr.status === 'open') {
    if (canQuote || canUpdate) addAction({ action: 'send_to_buyer', to: 'sent_to_buyer', label: 'Enviar ao Comprador', legacy: true });
  } else if (pr.status === 'sent_to_buyer') {
    if (canQuote) {
      addAction({ action: 'mark_quoted', to: 'quoted', label: 'Marcar como Cotada', legacy: true });
      addAction({ action: 'buyer_return_to_requester', label: 'Retornar ao Requisitante', ghost: true, reasonGroup: 'requester', requiresReason: true, requiresComment: true, showRequesterChecklist: true, description: 'Solicite ajustes antes de enviar a cotação ao aprovador.' });
    }
  } else if (pr.status === 'quoted' || pr.status === 'returned_to_buyer') {
    if (canQuote) {
      addAction({ action: 'send_to_approver', to: 'pending_approval', label: 'Enviar ao Aprovador', legacy: true });
      addAction({ action: 'buyer_return_to_requester', label: 'Retornar ao Requisitante', ghost: true, reasonGroup: 'requester', requiresReason: true, requiresComment: true, showRequesterChecklist: true, description: 'Solicite ajustes do requisitante antes de concluir a cotação.' });
    }
  } else if (pr.status === 'waiting_buyer_correction') {
    if (canQuote) {
      addAction({ action: 'mark_quoted', to: 'quoted', label: 'Marcar como Cotada', legacy: true });
      addAction({ action: 'buyer_resubmit', label: 'Reenviar ao Aprovador' });
      addAction({ action: 'buyer_return_to_requester', label: 'Retornar ao Requisitante', ghost: true, reasonGroup: 'requester', requiresReason: true, requiresComment: true, showRequesterChecklist: true, description: 'Solicite ajustes do requisitante antes de reenviar a cotação.' });
    }
  } else if (pr.status === 'pending_approval' || pr.status === 'postponed') {
    if (canApprove) {
      addAction({ action: 'approve', label: '✔ Aprovar' });
      addAction({ action: 'return_to_buyer', label: 'Solicitar revisão da cotação', ghost: true, reasonGroup: 'buyer', requiresReason: true, requiresComment: true, description: 'Devolve para o comprador corrigir valores, fornecedor ou itens da cotação.' });
      addAction({ action: 'return_to_requester', label: 'Solicitar revisão da requisição', ghost: true, reasonGroup: 'requester', requiresReason: true, requiresComment: true, showRequesterChecklist: true, description: 'Devolve para o requisitante/Administrador Local corrigir demanda, quantidade ou justificativa.' });
      addAction({ action: 'reject', label: '✕ Reprovar', ghost: true, danger: true, reasonGroup: 'reject', requiresReason: true, requiresComment: true, description: 'Reprova a cotação/requisição e encerra o fluxo.' });
    }
  } else if (pr.status === 'waiting_requester_correction') {
    if (isAdmin || canUpdate) addAction({ action: 'requester_resubmit', label: 'Reenviar Requisição Corrigida', description: 'Após corrigir itens, quantidades ou justificativas, o fluxo retorna automaticamente à etapa adequada.' });
    
  } else if (pr.status === 'approved') {
    if (canQuote || isBuyer) addAction({ action: 'generate_po', label: 'Gerar PO' });

  } else if (pr.status === 'partially_approved') {
    if (canQuote || isBuyer) addAction({ action: 'generate_po', label: 'Gerar PO (Itens Aprovados)' });

  } else if (pr.status === 'po_generated') {
    if (isAdmin) {
      addAction({ action: 'received', to: 'received', label: 'Marcar Recebida', legacy: true });
      addAction({ action: 'closed', to: 'closed', label: 'Fechar', ghost: true, legacy: true });
    }
  } else if (pr.status === 'received' && isAdmin) {
    addAction({ action: 'conferir_recebimento', label: 'Conferir Recebimento' });
  } else if (pr.status === 'checked' && isAdmin) {
    addAction({ action: 'closed', to: 'closed', label: 'Fechar Requisição', legacy: true });
  }
  if (['checked', 'closed'].includes(pr.status) && canPrintPurchaseQrLabels()) {
    addAction({ action: 'print_qr_labels', label: '🏷️ Imprimir QR Codes', ghost: true });
  }
  const canCancelAsRequester = canUpdate && ['open', 'waiting_requester_correction'].includes(pr.status);
  const canCancelAsBuyer = canQuote && ['open', 'sent_to_buyer', 'quoted', 'returned_to_buyer', 'waiting_buyer_correction'].includes(pr.status);
  if (canCancelAsRequester || canCancelAsBuyer) {
    addAction({ action: 'cancel', to: 'cancelled', label: 'Cancelar', ghost: true, legacy: true });
  }
  actions.forEach(t => {
    const btn = document.createElement('button');
    btn.className = t.ghost ? 'btn ghost' : 'btn';
    if (t.danger) btn.style.cssText += ';border-color:var(--color-danger);color:var(--color-danger);';
    btn.style.fontSize = '13px';
    btn.textContent = t.label;
    bindAppListener(btn, 'click', () => t.legacy ? updatePrStatus(pr.id, t.to) : executePurchaseWorkflowAction(pr.id, t));
    container.appendChild(btn);
  });
}

async function executePurchaseWorkflowAction(prId, actionConfig) {
  if (actionConfig.action === 'conferir_recebimento') {
    await executePrConferenciaAction(prId, _currentPrDetail?.items || []);
    return;
  }
  if (actionConfig.action === 'print_qr_labels') {
    await openPurchaseQrPrintFromDetail(prId);
    return;
  }
  if (actionConfig.action === 'generate_po') {
    try {
      await api(`/api/purchase-requests/${prId}/status`, {
        method: 'POST',
        body: JSON.stringify({ actor_user_id: state.user?.id, status: 'po_generated', comment: '' })
      });
      showToast('Requisição enviada para geração de PO.');
      await openPrDetail(prId);
      loadPurchaseRequests();
      const poReqId = document.getElementById('po-request-id');
      if (poReqId) poReqId.value = prId;
      populatePurchaseUnitSelects();
      loadAuthorizedSuppliers();
      switchComprasTab('pos');
      const form = document.getElementById('compras-new-po-form');
      if (form) { form.style.display = ''; setTimeout(() => form.scrollIntoView({ behavior: 'smooth' }), 200); }
    } catch(e) {
      showToast(e.message || 'Erro ao gerar PO.', 'error');
    }
    return;
  }
  const modalResult = await openPurchaseWorkflowModal({
    title: actionConfig.label,
    description: actionConfig.description || `Confirmar ação para a requisição #${prId}.`,
    reasonGroup: actionConfig.reasonGroup,
    requiresReason: actionConfig.requiresReason,
    requiresComment: actionConfig.requiresComment,
    showRequesterChecklist: actionConfig.showRequesterChecklist,
    showItemSelection: ['return_to_buyer', 'return_to_requester'].includes(actionConfig.action),
    showApprovalItems: actionConfig.action === 'approve',
    items: _currentPrDetail?.items || [],
  });
  if (modalResult === null) return;
  try {
    const result = await api(`/api/purchase-requests/${prId}/workflow`, {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user?.id, action: actionConfig.action, ...modalResult })
    });
    showToast(`Fluxo atualizado: ${PURCHASE_STATUS_LABELS[result.status] || result.status}.`);
    await openPrDetail(prId);
    loadPurchaseRequests();
  } catch(e) {
    showToast(e.message || 'Erro ao executar ação da requisição.', 'error');
  }
}

async function executePrConferenciaAction(prId, prItems) {
  const result = await openConferenciaModal(prId, prItems);
  if (result === null) return;
  try {
    const res = await api(`/api/purchase-requests/${prId}/status`, {
      method: 'POST',
      body: JSON.stringify({
        actor_user_id: state.user?.id,
        status: 'checked',
        received_items: result.received_items,
        comment: result.comment,
      })
    });
    const stockMsg = res.stock_entries > 0
      ? ` ${res.stock_entries} unidade(s) adicionada(s) ao estoque automaticamente.`
      : '';
    showToast(`Conferência registrada.${stockMsg}`);
    const pendencies = Array.isArray(res.pendencies) ? res.pendencies : [];
    if (pendencies.length) {
      const totalShort = pendencies.reduce((s, p) => s + Number(p.quantity_short || 0), 0);
      showToast(`Recebimento parcial: ${pendencies.length} pendência(s) (${totalShort} item(ns) em falta) registrada(s) e o comprador foi alertado.`, 'warning');
    }
    const qrLabels = Array.isArray(res.qr_labels) ? res.qr_labels : [];
    if (qrLabels.length) {
      purchaseQrLabelsByPr[prId] = qrLabels;
      await openPrDetail(prId);
      openPurchaseQrPrintModal(prId, qrLabels);
    } else {
      await openPrDetail(prId);
    }
    loadPurchaseRequests();
  } catch(e) {
    showToast(e.message || 'Erro ao registrar conferência.', 'error');
  }
}

const purchaseQrLabelsByPr = {};

function canPrintPurchaseQrLabels() {
  return hasPermission('purchase_requests:update') || hasPermission('stock:adjust') || hasPermission('stock:view');
}

async function openPurchaseQrPrintFromDetail(prId) {
  let labels = purchaseQrLabelsByPr[prId];
  if (!labels || !labels.length) {
    try {
      const res = await api(`/api/purchase-requests/${prId}/stock-labels`);
      labels = Array.isArray(res.qr_labels) ? res.qr_labels : [];
      purchaseQrLabelsByPr[prId] = labels;
    } catch(e) {
      showToast(e.message || 'Erro ao carregar etiquetas QR.', 'error');
      return;
    }
  }
  if (!labels.length) {
    showToast('Nenhuma etiqueta QR gerada para esta requisição.', 'error');
    return;
  }
  openPurchaseQrPrintModal(prId, labels);
}

function openPurchaseQrPrintModal(prId, qrLabels) {
  const labels = Array.isArray(qrLabels) ? qrLabels : [];
  if (!labels.length) return;
  const existing = document.getElementById('pr-qr-print-modal');
  if (existing) existing.remove();
  const overlay = document.createElement('div');
  overlay.id = 'pr-qr-print-modal';
  overlay.className = 'modal-overlay';
  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.5);display:flex;align-items:center;justify-content:center;z-index:1000;';
  const rowsHtml = labels.map((label, idx) => {
    const sizeInfo = [label.glove_size && label.glove_size !== 'N/A' ? `L:${label.glove_size}` : null, label.size && label.size !== 'N/A' ? `T:${label.size}` : null, label.uniform_size && label.uniform_size !== 'N/A' ? `U:${label.uniform_size}` : null].filter(Boolean).join(' ') || '—';
    return `<tr>
      <td style="padding:4px 8px;"><input type="checkbox" value="${idx}" data-pr-qr-item checked></td>
      <td style="padding:4px 8px;">${esc(label.epi_name || '—')}</td>
      <td style="padding:4px 8px;font-size:12px;">${esc(sizeInfo)}</td>
      <td style="padding:4px 8px;font-size:12px;">${esc(label.qr_code_value || '')}</td>
      <td style="padding:4px 8px;font-size:12px;">${Number(label.reprint_count || 0)}</td>
    </tr>`;
  }).join('');
  overlay.innerHTML = `
    <div class="modal" style="background:var(--color-surface,#fff);border-radius:8px;max-width:720px;width:92%;max-height:88vh;overflow:auto;padding:18px;">
      <h3 style="margin:0 0 8px;">Imprimir QR Codes — Requisição #${esc(prId)}</h3>
      <p style="margin:0 0 12px;color:var(--color-text-muted);font-size:13px;">Selecione as etiquetas dos EPIs recebidos para imprimir ou reimprimir.</p>
      <div style="display:flex;gap:8px;margin-bottom:8px;">
        <button class="btn ghost" id="pr-qr-select-all" style="font-size:12px;">Selecionar todos</button>
        <button class="btn ghost" id="pr-qr-select-none" style="font-size:12px;">Limpar seleção</button>
      </div>
      <table style="width:100%;border-collapse:collapse;font-size:13px;border:1px solid var(--color-border);">
        <thead><tr style="background:var(--color-surface-alt,#f5f5f5);">
          <th scope="col" style="padding:4px 8px;text-align:left;"></th>
          <th scope="col" style="padding:4px 8px;text-align:left;">EPI</th>
          <th scope="col" style="padding:4px 8px;text-align:left;">Tamanho</th>
          <th scope="col" style="padding:4px 8px;text-align:left;">QR</th>
          <th scope="col" style="padding:4px 8px;text-align:left;">Reimpr.</th>
        </tr></thead>
        <tbody>${rowsHtml}</tbody>
      </table>
      <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px;">
        <button class="btn ghost" id="pr-qr-cancel">Fechar</button>
        <button class="btn ghost" id="pr-qr-print-selected">Imprimir Selecionados</button>
        <button class="btn" id="pr-qr-print-all">Imprimir Todos</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  const checkboxes = () => Array.from(overlay.querySelectorAll('[data-pr-qr-item]'));
  const selectedLabels = () => checkboxes().filter(cb => cb.checked).map(cb => labels[Number(cb.value)]).filter(Boolean);
  const close = () => overlay.remove();
  bindAppListener(overlay.querySelector('#pr-qr-select-all'), 'click', () => checkboxes().forEach(cb => { cb.checked = true; }));
  bindAppListener(overlay.querySelector('#pr-qr-select-none'), 'click', () => checkboxes().forEach(cb => { cb.checked = false; }));
  bindAppListener(overlay.querySelector('#pr-qr-cancel'), 'click', close);
  bindAppListener(overlay, 'click', (ev) => { if (ev.target === overlay) close(); });
  bindAppListener(overlay.querySelector('#pr-qr-print-all'), 'click', () => printStockLabels(labels, 1));
  bindAppListener(overlay.querySelector('#pr-qr-print-selected'), 'click', () => {
    const sel = selectedLabels();
    if (!sel.length) return alert('Selecione ao menos uma etiqueta para imprimir.');
    printStockLabels(sel, 1);
  });
}

function openConferenciaModal(prId, items) {
  return new Promise((resolve) => {
    const existing = document.getElementById('conferencia-modal');
    if (existing) existing.remove();
    const overlay = document.createElement('div');
    overlay.id = 'conferencia-modal';
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:950;display:flex;align-items:center;justify-content:center;padding:16px;';
    const eligibleStatuses = ['included_in_request', 'received', 'not_received', 'received_partial', 'approved', 'ordered'];
    const eligibleItems = items.filter(i => eligibleStatuses.includes(String(i.status || '')));
    const itemsHtml = eligibleItems.map(item => {
      const alreadyNotReceived = item.status === 'not_received';
      const sizeInfo = [item.glove_size && item.glove_size !== 'N/A' ? `L:${item.glove_size}` : null, item.size && item.size !== 'N/A' ? `T:${item.size}` : null].filter(Boolean).join(' ') || '—';
      return `<tr data-conferencia-row="${esc(item.id)}" style="${alreadyNotReceived ? 'background:var(--color-danger-bg,#fff0f0);' : ''}">
        <td style="padding:6px 8px;"><strong>${esc(item.epi_name || 'Item')}</strong><br><small style="color:var(--color-text-muted)">${tr('epi.caShort', 'CA')}: ${esc(item.ca || '—')} | ${esc(item.manufacturer || '—')}</small></td>
        <td style="padding:6px 8px;">${esc(item.employee_name || '—')}</td>
        <td style="padding:6px 8px;text-align:center;">${esc(item.quantity_requested || 1)}</td>
        <td style="padding:6px 8px;text-align:center;font-size:12px;">${esc(sizeInfo)}</td>
        <td style="padding:6px 8px;text-align:center;">
          <label style="display:flex;align-items:center;justify-content:center;gap:6px;cursor:pointer;">
            <input type="checkbox" value="${esc(item.id)}" data-conferencia-item ${alreadyNotReceived ? '' : 'checked'}>
            <span data-conferencia-label="${esc(item.id)}">${alreadyNotReceived ? 'Não Recebido' : 'Recebido'}</span>
          </label>
        </td>
        <td style="padding:6px 8px;text-align:center;">
          <div style="display:flex;gap:4px;align-items:center;justify-content:center;">
            <input type="date" data-conferencia-validity="${esc(item.id)}" data-epi="${esc(item.epi_id)}" style="font-size:12px;padding:2px 4px;" title="Validade do fabricante do EPI">
            <label class="btn ghost" style="padding:2px 6px;cursor:pointer;font-size:13px;line-height:1;" title="Ler data por câmera (OCR)">📷<input type="file" accept="image/*" capture="environment" data-conferencia-ocr="${esc(item.id)}" style="display:none;"></label>
          </div>
        </td>
      </tr>`;
    }).join('');
    overlay.innerHTML = `
      <div class="card" style="max-width:860px;width:min(860px,96vw);margin:auto;padding:24px;max-height:92vh;overflow:auto;">
        <h3 style="margin:0 0 4px;">Conferência de Recebimento — Requisição #${esc(String(prId))}</h3>
        <p style="font-size:13px;color:var(--color-text-muted);margin:0 0 12px;">Marque cada item conforme o recebimento real. Itens <strong>desmarcados</strong> serão registrados como <strong>Não Recebido</strong> para acompanhamento com o fornecedor. Informe a <strong>validade do fabricante</strong> de cada EPI antes de enviar ao estoque (use 📷 para ler por câmera). A primeira data de um mesmo EPI é aplicada automaticamente aos demais itens daquele EPI.</p>
        <div style="margin-bottom:10px;overflow-x:auto;">
          <table style="width:100%;border-collapse:collapse;font-size:13px;">
            <thead><tr style="border-bottom:2px solid var(--color-border);">
              <th scope="col" style="text-align:left;padding:6px 8px;">EPI</th>
              <th scope="col" style="text-align:left;padding:6px 8px;">Colaborador</th>
              <th scope="col" style="text-align:center;padding:6px 8px;">Qtd</th>
              <th scope="col" style="text-align:center;padding:6px 8px;">Tamanho</th>
              <th scope="col" style="text-align:center;padding:6px 8px;">Recebido?</th>
              <th scope="col" style="text-align:center;padding:6px 8px;">Validade Fabricante</th>
            </tr></thead>
            <tbody>${itemsHtml || '<tr><td colspan="6" style="text-align:center;padding:12px;color:var(--color-text-muted)">Nenhum item elegível para conferência.</td></tr>'}</tbody>
          </table>
        </div>
        <div id="conferencia-summary" style="padding:10px 12px;border-radius:6px;background:var(--color-surface,#f5f5f5);margin-bottom:12px;font-size:13px;border:1px solid var(--color-border);"></div>
        <label style="display:block;margin-bottom:14px;font-size:13px;">
          Observações sobre itens não recebidos <span style="font-size:12px;color:var(--color-text-muted)">(será usada como base para reclamação ao fornecedor)</span>
          <textarea id="conferencia-notes" rows="3" style="width:100%;margin-top:6px;" placeholder="Descreva os EPIs que não foram entregues ou com quantidade divergente. Essas informações serão registradas para contato com o fornecedor."></textarea>
        </label>
        <div id="conferencia-error" style="display:none;color:var(--color-danger,#c00);font-size:13px;margin-bottom:8px;"></div>
        <div style="display:flex;gap:8px;justify-content:flex-end;">
          <button class="btn ghost" id="conferencia-cancel">Cancelar</button>
          <button class="btn" id="conferencia-confirm">Registrar Conferência</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    const updateSummary = () => {
      const checkboxes = Array.from(overlay.querySelectorAll('[data-conferencia-item]'));
      const total = checkboxes.length;
      const receivedCount = checkboxes.filter(cb => cb.checked).length;
      const notReceivedCount = total - receivedCount;
      const summaryEl = overlay.querySelector('#conferencia-summary');
      if (summaryEl) {
        if (notReceivedCount > 0) {
          summaryEl.innerHTML = `<strong>${receivedCount}/${total}</strong> itens recebidos &nbsp;|&nbsp; <span style="color:var(--color-danger,#c00);">⚠ <strong>${notReceivedCount}</strong> item(ns) <strong>não recebido(s)</strong> — registrar para cobrança ao fornecedor</span>`;
        } else {
          summaryEl.innerHTML = `<span style="color:var(--color-success,green);">✓ Todos os <strong>${total}</strong> itens foram recebidos</span>`;
        }
      }
      checkboxes.forEach(cb => {
        const labelEl = overlay.querySelector(`[data-conferencia-label="${CSS.escape(cb.value)}"]`);
        if (labelEl) labelEl.textContent = cb.checked ? 'Recebido' : 'Não Recebido';
        const row = cb.closest('[data-conferencia-row]');
        if (row) row.style.background = cb.checked ? '' : 'var(--color-danger-bg,#fff0f0)';
      });
    };
    overlay.querySelectorAll('[data-conferencia-item]').forEach(cb => bindAppListener(cb, 'change', updateSummary));
    updateSummary();
    // Validade do fabricante por lote: ao informar a data de um EPI, aplica
    // automaticamente aos demais itens do mesmo EPI que ainda estão vazios.
    const propagateValidityByEpi = (sourceInput) => {
      const epiId = sourceInput.getAttribute('data-epi');
      const value = sourceInput.value;
      if (!epiId || !value) return;
      overlay.querySelectorAll(`[data-conferencia-validity][data-epi="${CSS.escape(epiId)}"]`).forEach((el) => {
        if (el !== sourceInput && !el.value) el.value = value;
      });
    };
    overlay.querySelectorAll('[data-conferencia-validity]').forEach((el) => {
      bindAppListener(el, 'change', () => propagateValidityByEpi(el));
    });
    overlay.querySelectorAll('[data-conferencia-ocr]').forEach((fileInput) => {
      bindAppListener(fileInput, 'change', async (event) => {
        const itemId = fileInput.getAttribute('data-conferencia-ocr');
        const dateField = overlay.querySelector(`[data-conferencia-validity="${CSS.escape(itemId)}"]`);
        const file = event?.target?.files?.[0];
        if (!file || !dateField) return;
        const detected = await readManufacturerValidityFromImage(file);
        if (detected) {
          dateField.value = detected;
          propagateValidityByEpi(dateField);
        }
        event.target.value = '';
      });
    });
    const finish = (value) => { overlay.remove(); resolve(value); };
    bindAppListener(overlay.querySelector('#conferencia-cancel'), 'click', () => finish(null));
    bindAppListener(overlay, 'click', (e) => { if (e.target === overlay) finish(null); });
    bindAppListener(overlay.querySelector('#conferencia-confirm'), 'click', () => {
      const errorEl = overlay.querySelector('#conferencia-error');
      const showError = (msg) => { if (errorEl) { errorEl.style.display = ''; errorEl.textContent = msg; } };
      const received_items = Array.from(overlay.querySelectorAll('[data-conferencia-item]')).map(cb => {
        const dateField = overlay.querySelector(`[data-conferencia-validity="${CSS.escape(cb.value)}"]`);
        return {
          id: Number(cb.value),
          received: cb.checked,
          manufacturer_validity_date: dateField?.value?.trim() || '',
        };
      });
      const comment = overlay.querySelector('#conferencia-notes')?.value?.trim() || '';
      const notReceived = received_items.filter(i => !i.received);
      if (notReceived.length > 0 && !comment) {
        showError('Informe as observações sobre os itens não recebidos.');
        return;
      }
      // Nenhum item pode entrar em estoque sem a validade do fabricante (NT 146/2015).
      const missingValidity = received_items.filter(i => i.received && !i.manufacturer_validity_date);
      if (missingValidity.length > 0) {
        showError('Informe a validade do fabricante de todos os EPIs recebidos antes de enviar ao estoque.');
        return;
      }
      finish({ received_items, comment });
    });
  });
}

async function updatePrStatus(prId, status) {
  let comment = '';
  let postponedUntil = '';
  if (status === 'postponed') {
    const modalResult = await openPurchaseWorkflowModal({ title: 'Prorrogar requisição', description: 'Informe a justificativa e use o fluxo de PO quando houver data formal de prorrogação.', requiresComment: false });
    if (modalResult === null) return;
    comment = modalResult.comment || '';
  }
  try {
    await api(`/api/purchase-requests/${prId}/status`, {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user?.id, status, comment, postponed_until: postponedUntil })
    });
    showToast(`Status atualizado: ${PURCHASE_STATUS_LABELS[status] || status}.`);
    await openPrDetail(prId);
    loadPurchaseRequests();
  } catch(e) {
    showToast(e.message || 'Erro ao alterar status.', 'error');
  }
}

async function openPoDetail(poId) {
  try {
    const res = await api(`/api/purchase-orders/${poId}`);
    _currentPoDetail = res;
    const po = _currentPoDetail.item;
    const items = _currentPoDetail.items || [];
    const events = _currentPoDetail.events || [];
    const titleEl = document.getElementById('compras-po-detail-title');
    if (titleEl) titleEl.textContent = `PO #${po.id}${po.po_number ? ' — ' + po.po_number : ''}`;
    const infoEl = document.getElementById('compras-po-detail-info');
    if (infoEl) infoEl.innerHTML = `
      <div><strong>Fornecedor</strong><br>${po.supplier || '—'}</div>
      <div><strong>Status</strong><br>${purchaseStatusBadge(po.status, po.status === 'postponed' && po.postponed_until ? `Até ${po.postponed_until}` : '')}</div>
      <div><strong>Total</strong><br>${fmtBrl(po.total_value)}</div>
      <div><strong>Nº PO</strong><br>${po.po_number || `PO-${po.id}`}</div>
      <div><strong>Unidade</strong><br>${po.unit_name || '—'}</div>
      <div><strong>Previsão Entrega</strong><br>${po.expected_delivery_date || '—'}</div>
      <div><strong>Aprovação</strong><br>${po.approved_by_name ? `${po.approved_by_name} em ${(po.approved_at || '').slice(0,10)}` : '—'}</div>
      ${po.approval_comment ? `<div style="grid-column:1/-1"><strong>Comentário</strong><br>${po.approval_comment}</div>` : ''}
    `;
    // P1-5 — stepper do ciclo de recebimento da PO.
    const stepperEl = document.getElementById('compras-po-stepper');
    if (stepperEl) stepperEl.innerHTML = buildPoStepper(po.status);
    const approvalForm = document.getElementById('compras-po-approval-form');
    const adminReviewForm = document.getElementById('compras-po-admin-review-form');
    const resubmitForm = document.getElementById('compras-po-resubmit-form');
    const receiveForm = document.getElementById('compras-po-receive-form');
    if (approvalForm) approvalForm.style.display = (['pending_approval','postponed'].includes(po.status) && hasPermission('purchase_orders:approve')) ? '' : 'none';
    if (adminReviewForm) adminReviewForm.style.display = (po.status === 'waiting_admin_review' && hasPermission('purchase_orders:review')) ? '' : 'none';
    if (resubmitForm) resubmitForm.style.display = (po.status === 'quoted' && hasPermission('purchase_orders:create')) ? '' : 'none';
    if (receiveForm) receiveForm.style.display = (['approved','received_partial','received','checked'].includes(po.status) && hasPermission('purchase_orders:receive')) ? '' : 'none';
    renderPoReceiveItems(items);
    // Show suggestions to buyer when PO was returned
    const infoEl2 = document.getElementById('compras-po-detail-info');
    if (infoEl2 && po.status === 'quoted' && po.buyer_suggestions) {
      infoEl2.insertAdjacentHTML('beforeend', `<div style="grid-column:1/-1;padding:8px;background:var(--color-warning-light,#fff3cd);border-radius:4px;"><strong>Sugestões do Admin:</strong> ${po.buyer_suggestions}</div>`);
    }
    const tbody = document.getElementById('compras-po-detail-tbody');
    if (tbody) tbody.innerHTML = items.map(i => `<tr>
      <td>${i.epi_name || '—'}</td>
      <td>${i.ca || '—'}</td>
      <td>${i.manufacturer || '—'}</td>
      <td>${i.supplier || '—'}</td>
      <td style="font-size:12px;">${[i.glove_size !== 'N/A' ? `L:${i.glove_size}`:null, i.size !== 'N/A'?`T:${i.size}`:null, i.uniform_size !== 'N/A'?`U:${i.uniform_size}`:null].filter(Boolean).join(' ') || '—'}</td>
      <td>${i.quantity}</td>
      <td>${fmtBrl(i.unit_price)}</td>
      <td>${fmtBrl(i.total_price)}</td>
      <td>${i.origin === 'employee_request' ? 'Colaborador' : 'Estoque Mín.'}</td>
      <td>${ITEM_STATUS_LABELS[i.status] || i.status}</td>
    </tr>`).join('');
    const eventsEl = document.getElementById('compras-po-events');
    if (eventsEl) {
      // P1-6 — histórico da PO como timeline visual.
      const timelineItems = events.map((e) => ({
        time: (e.created_at || '').slice(0, 16).replace('T', ' '),
        title: `${e.actor_name || '—'} — ${e.action || ''}`,
        desc: [e.status_from ? `${e.status_from} → ${e.status_to}` : '', e.comment || ''].filter(Boolean).join(' · ')
      }));
      eventsEl.innerHTML = events.length
        ? globalThis.dsTimeline(timelineItems)
        : '<em>Sem histórico.</em>';
    }
    const detailEl = document.getElementById('compras-po-detail');
    if (detailEl) { detailEl.style.display = ''; detailEl.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
  } catch(e) {
    alert('Erro ao carregar PO.');
  }
}

function renderRequesterReviewTools(pr, items) {
  const container = document.getElementById('compras-req-detail-status-actions');
  if (!container || pr.status !== 'waiting_requester_correction' || !hasPermission('purchase_requests:update')) return;
  const editBtn = document.createElement('button');
  editBtn.className = 'btn ghost';
  editBtn.textContent = 'Editar Itens/Justificativa';
  bindAppListener(editBtn, 'click', () => openRequesterReviewModal(pr, items));
  container.appendChild(editBtn);
}

async function submitPoApprovalWithItems() {
  if (!_currentPoDetail) return;
  const poItems = (_currentPoDetail.items || []).map(i => ({
    ...i,
    epi_display_name: i.epi_name,
    quantity_requested: i.quantity,
  }));
  if (!poItems.length) { alert('Esta PO não possui itens para aprovação.'); return; }
  const modalResult = await openPurchaseWorkflowModal({
    title: 'Aprovar PO — Seleção de Itens',
    description: 'Marque os itens aprovados. Itens desmarcados requerem motivo de reprovação.',
    showApprovalItems: true,
    items: poItems,
  });
  if (modalResult === null) return;
  const { decisions, comment } = modalResult;
  if (!decisions || !decisions.length) return;
  const approvedCount = decisions.filter(d => d.approved).length;
  const decision = approvedCount === decisions.length ? 'approved' : approvedCount > 0 ? 'partially_approved' : 'rejected';
  if (decision === 'rejected' && !comment) {
    alert('Comentário obrigatório para rejeição total.');
    return;
  }
  try {
    await api(`/api/purchase-orders/${_currentPoDetail.item.id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user?.id, decision, comment, decisions })
    });
    await openPoDetail(_currentPoDetail.item.id);
    loadPurchaseOrders();
  } catch(e) {
    alert(e.message || 'Erro na aprovação.');
  }
}

async function submitPoApproval(decision) {
  if (!_currentPoDetail) return;
  const comment = document.getElementById('po-approval-comment')?.value?.trim() || '';
  const postponedUntil = document.getElementById('po-postponed-until')?.value?.trim() || '';
  if (decision === 'rejected' && !comment) {
    alert('Comentário obrigatório para rejeição.');
    return;
  }
  if (decision === 'postponed' && !postponedUntil) {
    alert('Data de prorrogação obrigatória.');
    return;
  }
  try {
    await api(`/api/purchase-orders/${_currentPoDetail.item.id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user?.id, decision, comment, postponed_until: postponedUntil })
    });
    await openPoDetail(_currentPoDetail.item.id);
    loadPurchaseOrders();
  } catch(e) {
    alert(e.message || 'Erro na aprovação.');
  }
}

async function submitPoReceive(action) {
  if (!_currentPoDetail) return;
  let payload = { actor_user_id: state.user?.id, action };
  if (action === 'received' || action === 'received_partial') {
    const items = Array.from(document.querySelectorAll('[data-po-receive-item]')).map(row => ({
      id: Number(row.dataset.poReceiveItem),
      quantity_received: Number(row.querySelector('[data-po-receive-qty]')?.value || 0),
    }));
    const partial = items.some((item) => {
      const source = (_currentPoDetail.items || []).find((candidate) => Number(candidate.id) === item.id);
      return item.quantity_received < Number(source?.quantity || 1);
    });
    const notes = document.getElementById('po-receive-notes')?.value?.trim() || '';
    if (partial && !notes) { alert('Observação obrigatória em recebimento parcial.'); return; }
    payload = { ...payload, action: partial ? 'received_partial' : 'received', items, notes };
  }
  try {
    await api(`/api/purchase-orders/${_currentPoDetail.item.id}/receive`, { method: 'POST', body: JSON.stringify(payload) });
    await openPoDetail(_currentPoDetail.item.id);
    loadPurchaseOrders();
  } catch(e) {
    alert(e.message || 'Erro ao registrar recebimento.');
  }
}

function renderPoReceiveItems(items) {
  const container = document.getElementById('po-receive-items');
  if (!container) return;
  container.innerHTML = (items || []).map((item) => `<div data-po-receive-item="${esc(item.id)}" style="display:grid;grid-template-columns:1fr 90px;gap:8px;align-items:center;margin-top:6px;"><span>${esc(item.epi_name || 'Item')} <small>pedido: ${esc(item.quantity || 1)}</small></span><input type="number" min="0" max="${esc(item.quantity || 1)}" value="${esc(item.quantity_received || item.quantity || 1)}" data-po-receive-qty></div>`).join('');
}


async function submitPoAdminReview(reviewDecision) {
  if (!_currentPoDetail) return;
  const comment = document.getElementById('po-review-comment')?.value?.trim() || '';
  if (reviewDecision === 'returned_with_suggestions' && !comment) {
    alert('Informe as sugestões para devolver ao comprador.');
    return;
  }
  try {
    await api(`/api/purchase-orders/${_currentPoDetail.item.id}/review`, {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user?.id, decision: reviewDecision, comment })
    });
    await openPoDetail(_currentPoDetail.item.id);
    loadPurchaseOrders();
  } catch(e) {
    alert(e.message || 'Erro na revisão.');
  }
}

let _authorizedSuppliers = [];

async function loadAuthorizedSuppliers() {
  const tbody = document.getElementById('compras-suppliers-tbody');
  if (!tbody) return;
  try {
    const res = await api('/api/authorized-suppliers');
    _authorizedSuppliers = res.items || [];
    const canManage = hasPermission(SUPPLIERS_MANAGE_PERM);
    const canViewPOs = hasPermission('purchase_orders:view') || hasPermission('finance:view');
    populatePoSupplierSelect();
    tbody.innerHTML = _authorizedSuppliers.length
      ? _authorizedSuppliers.map(s => {
          const statusBadge = s.active
            ? `<span style="color:var(--color-success,green);font-weight:600;font-size:12px;">Ativo</span>`
            : `<span style="color:var(--color-danger,#c00);font-weight:600;font-size:12px;">Suspenso</span>`;
          const editBtn = canManage
            ? `<button class="btn ghost" style="font-size:12px;padding:3px 8px;" onclick="openEditSupplierModal(${s.id})">Editar</button>`
            : '';
          const toggleBtn = canManage
            ? `<button class="btn ghost" style="font-size:12px;padding:3px 8px;${s.active ? 'color:var(--color-danger,#c00)' : 'color:var(--color-success,green)'}" onclick="toggleSupplierActive(${s.id}, '${esc(s.name)}', ${s.active ? 1 : 0})">${s.active ? 'Suspender' : 'Reativar'}</button>`
            : '';
          const posBtn = canViewPOs
            ? `<button class="btn ghost" style="font-size:12px;padding:3px 8px;" onclick="openSupplierPOsModal(${s.id})">Ver POs</button>`
            : '';
          const catalogBtn = `<button class="btn ghost" style="font-size:12px;padding:3px 8px;" onclick="openSupplierCatalogModal(${s.id}, '${esc(s.name)}')">Catálogo</button>`;
          const integrationBtn = canManage
            ? `<button class="btn ghost" style="font-size:12px;padding:3px 8px;" onclick="openSupplierIntegrationModal(${s.id}, '${esc(s.name)}')">Integração</button>`
            : '';
          return `<tr style="${s.active ? '' : 'opacity:.6;'}">
            <td>${esc(s.name) || '—'}</td>
            <td>${s.cnpj ? formatCNPJ(s.cnpj) : '—'}</td>
            <td>${esc(s.contact_email || s.contact_name || s.email || '') || '—'}</td>
            <td>${statusBadge}</td>
            <td>${(s.created_at || '').slice(0,10) || '—'}</td>
            <td style="white-space:nowrap;">${editBtn} ${toggleBtn} ${posBtn} ${catalogBtn} ${integrationBtn}</td>
          </tr>`;
        }).join('')
      : globalThis.dsTableState({ colspan: 6, message: 'Nenhum fornecedor autorizado cadastrado.' });
  } catch(e) {
    if (tbody) tbody.innerHTML = globalThis.dsTableState({ colspan: 6, kind: 'error', message: 'Não foi possível carregar os fornecedores.' });
  }
}

function formatCNPJ(raw) {
  const d = String(raw || '').replace(/\D/g, '');
  if (d.length !== 14) return raw || '—';
  return `${d.slice(0,2)}.${d.slice(2,5)}.${d.slice(5,8)}/${d.slice(8,12)}-${d.slice(12)}`;
}

function openEditSupplierModal(id) {
  const s = _authorizedSuppliers.find(x => x.id === id);
  if (!s) return;
  document.getElementById('edit-supplier-id').value = s.id;
  document.getElementById('edit-supplier-name').value = s.name || '';
  document.getElementById('edit-supplier-cnpj').value = s.cnpj ? formatCNPJ(s.cnpj) : '';
  document.getElementById('edit-supplier-email').value = s.contact_email || s.email || '';
  document.getElementById('edit-supplier-notes').value = s.notes || '';
  document.getElementById('edit-supplier-feedback').textContent = '';
  const modal = document.getElementById('modal-edit-supplier');
  if (modal) { modal.style.display = 'flex'; }
}

async function saveEditSupplier() {
  const feedback = document.getElementById('edit-supplier-feedback');
  const id = parseInt(document.getElementById('edit-supplier-id')?.value || '0', 10);
  const name = document.getElementById('edit-supplier-name')?.value?.trim();
  if (!name) { if (feedback) feedback.textContent = 'Nome é obrigatório.'; return; }
  try {
    if (feedback) feedback.textContent = '';
    await api(`/api/authorized-suppliers/${id}`, {
      method: 'PUT',
      body: JSON.stringify({
        actor_user_id: state.user?.id,
        name,
        cnpj: document.getElementById('edit-supplier-cnpj')?.value?.trim() || '',
        contact_email: document.getElementById('edit-supplier-email')?.value?.trim() || '',
        notes: document.getElementById('edit-supplier-notes')?.value?.trim() || '',
      })
    });
    const modal = document.getElementById('modal-edit-supplier');
    if (modal) modal.style.display = 'none';
    loadAuthorizedSuppliers();
  } catch(e) {
    if (feedback) feedback.textContent = e.message || 'Erro ao salvar.';
  }
}

window.toggleSupplierActive = async function toggleSupplierActive(id, name, currentActive) {
  const action = currentActive ? 'suspender' : 'reativar';
  if (!(await confirmDestructive({ title: 'Fornecedor', message: `Deseja ${action} o fornecedor "${name}"?`, confirmLabel: 'Confirmar', variant: 'warning' }))) return;
  try {
    const res = await api(`/api/authorized-suppliers/${id}/toggle`, {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user?.id })
    });
    loadAuthorizedSuppliers();
  } catch(e) {
    alert(e.message || 'Erro ao alterar status do fornecedor.');
  }
}

const PO_STATUS_LABELS = {
  draft: 'Rascunho', waiting_admin_review: 'Em Compra', approved: 'Aprovada',
  partially_approved: 'Aprovada Parcialmente', rejected: 'Reprovada',
  postponed: 'Prorrogada', received: 'Recebida', received_partial: 'Recebida Parcialmente',
  checked: 'Conferida', closed: 'Fechada', not_received: 'Não Recebido',
};

function poStatusLabel(status) {
  if (!status) return '—';
  return tr('purchase.poStatus.' + status, PO_STATUS_LABELS[status] || status);
}

window.openSupplierPOsModal = async function openSupplierPOsModal(id) {
  const modal = document.getElementById('modal-supplier-pos');
  const tbody = document.getElementById('modal-supplier-pos-tbody');
  const summary = document.getElementById('modal-supplier-pos-summary');
  const empty = document.getElementById('modal-supplier-pos-empty');
  const title = document.getElementById('modal-supplier-pos-title');
  if (!modal) return;
  modal.style.display = 'flex';
  if (tbody) tbody.innerHTML = globalThis.dsTableState({ colspan: 8, kind: 'loading', rows: 4 });
  if (empty) empty.style.display = 'none';
  try {
    const res = await api(`/api/authorized-suppliers/${id}/purchase-orders`);
    const sup = res.supplier || {};
    const items = res.items || [];
    if (title) title.textContent = `POs — ${sup.name || ''}`;
    const totalValue = items.reduce((acc, p) => acc + (p.total_value || 0), 0);
    if (summary) summary.textContent = `${items.length} pedido(s) · Total geral: ${formatCurrency(totalValue)}`;
    if (!items.length) {
      if (tbody) tbody.innerHTML = '';
      if (empty) empty.style.display = '';
      return;
    }
    if (empty) empty.style.display = 'none';
    if (tbody) tbody.innerHTML = items.map(po => {
      const statusLabel = poStatusLabel(po.status);
      return `<tr>
        <td style="font-size:12px;">${esc(po.po_number || String(po.id))}</td>
        <td style="font-size:12px;">${esc(po.unit_name || '—')}</td>
        <td style="font-size:12px;">${statusLabel}</td>
        <td style="font-size:12px;text-align:center;">${po.items_count ?? '—'}</td>
        <td style="font-size:12px;text-align:right;">${formatCurrency(po.total_value || 0)}</td>
        <td style="font-size:12px;">${esc(po.created_by_name || '—')}</td>
        <td style="font-size:12px;">${esc(po.approved_by_name || '—')}</td>
        <td style="font-size:12px;">${(po.created_at || '').slice(0,10) || '—'}</td>
      </tr>`;
    }).join('');
  } catch(e) {
    if (tbody) tbody.innerHTML = `<tr><td colspan="8" style="color:var(--color-danger)">Erro: ${esc(e.message)}</td></tr>`;
  }
}

function checkSupplierAuthorized(cnpj) {
  const statusEl = document.getElementById('po-supplier-status');
  if (!statusEl) return;
  const clean = (cnpj || '').replace(/\D/g, '');
  if (!clean) { statusEl.textContent = ''; return; }
  const found = _authorizedSuppliers.find(s => (s.cnpj || '').replace(/\D/g, '') === clean);
  if (found) {
    statusEl.innerHTML = `<span style="color:var(--color-success,green)">✓ Fornecedor autorizado: ${found.name}</span>`;
  } else {
    const supplierName = document.querySelector('[name="supplier"]')?.value?.trim() || '';
    const mailtoHref = buildSupplierInclusionMailto(supplierName, cnpj);
    statusEl.innerHTML = `<span style="color:var(--color-warning,#c47a00)">⚠ Fornecedor não encontrado na lista autorizada — </span><a href="${mailtoHref}" target="_blank" style="font-size:12px;">Solicitar Inclusão</a>`;
  }
}

// ── Item 3: Mailto para solicitar inclusão de fornecedor ──────────────────
function buildSupplierInclusionMailto(supplierName, cnpj) {
  const subject = encodeURIComponent(`Solicitação de Inclusão de Fornecedor: ${supplierName || 'Novo Fornecedor'} — CNPJ: ${cnpj}`);
  const requester = state.user?.full_name || 'Comprador';
  const company = state.user?.company_name || '';
  const body = encodeURIComponent(
    `Prezado(a) time Financeiro,\n\n` +
    `Solicito a inclusão do seguinte fornecedor na lista de fornecedores autorizados:\n\n` +
    `Nome: ${supplierName || '(preencher)'}\n` +
    `CNPJ: ${cnpj}\n\n` +
    `Solicitante: ${requester}${company ? ` — ${company}` : ''}\n\n` +
    `Por favor, confirme a autorização para que possamos prosseguir com a cotação.\n\n` +
    `Atenciosamente,\n${requester}`
  );
  return `mailto:?subject=${subject}&body=${body}`;
}

async function _loadSheetJS() {
  if (window.XLSX) return window.XLSX;
  return new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/xlsx/dist/xlsx.full.min.js';
    s.onload = () => resolve(window.XLSX);
    s.onerror = () => reject(new Error('Não foi possível carregar suporte a XLS. Verifique sua conexão.'));
    document.head.appendChild(s);
  });
}

function _parseSuppliersRows(rawRows) {
  return rawRows
    .map(r => {
      const k = (key) => String(r[key] || r[key?.toLowerCase?.()] || r[key?.toUpperCase?.()] || '').trim();
      const name = k('nome') || k('name') || k('Name') || k('Nome') || '';
      if (!name) return null;
      return {
        name,
        cnpj: k('cnpj') || k('CNPJ') || '',
        email: k('contato') || k('email') || k('Email') || k('contact_name') || k('contact_email') || '',
      };
    })
    .filter(Boolean);
}

async function importSuppliersCSV() {
  const fileInput = document.getElementById('compras-suppliers-csv');
  const feedback = document.getElementById('compras-suppliers-csv-feedback');
  if (!fileInput?.files?.length) { if (feedback) feedback.textContent = 'Selecione um arquivo.'; return; }
  const file = fileInput.files[0];
  const ext = file.name.split('.').pop().toLowerCase();
  let rows = [];
  try {
    if (ext === 'xls' || ext === 'xlsx') {
      if (feedback) feedback.textContent = 'Carregando suporte XLS…';
      const XLSX = await _loadSheetJS();
      const buf = await file.arrayBuffer();
      const wb = XLSX.read(buf, { type: 'array' });
      const ws = wb.Sheets[wb.SheetNames[0]];
      const data = XLSX.utils.sheet_to_json(ws, { defval: '' });
      rows = _parseSuppliersRows(data);
    } else {
      const raw = await file.text();
      const text = raw.replace(/^﻿/, '');
      const lines = text.split(/\r?\n/).filter(l => l.trim());
      if (lines.length < 2) { if (feedback) feedback.textContent = 'Arquivo vazio ou sem dados.'; return; }
      const sep = lines[0].includes(';') ? ';' : ',';
      const headers = lines[0].split(sep).map(h => h.trim().toLowerCase().replace(/['"]/g, ''));
      const objRows = lines.slice(1).map(line => {
        const cols = line.split(sep).map(c => c.trim().replace(/^"|"$/g, ''));
        const obj = {};
        headers.forEach((h, i) => { obj[h] = cols[i] || ''; });
        return obj;
      });
      rows = _parseSuppliersRows(objRows);
    }
  } catch(e) {
    if (feedback) feedback.textContent = e.message || 'Erro ao ler o arquivo.';
    return;
  }
  if (!rows.length) { if (feedback) feedback.textContent = 'Nenhuma linha válida encontrada. Verifique se o arquivo tem coluna "nome".'; return; }
  try {
    const res = await api('/api/authorized-suppliers/upload', { method: 'POST', body: JSON.stringify({ actor_user_id: state.user?.id, rows }) });
    const d = res || {};
    if (feedback) feedback.textContent = `Importado: ${d.inserted || 0} novos, ${d.updated || 0} atualizados.`;
    loadAuthorizedSuppliers();
  } catch(e) {
    if (feedback) feedback.textContent = e.message || 'Erro na importação.';
  }
}

// ── Item 1: Reenvio de PO pelo comprador ──────────────────────────────────
async function submitPoResubmit() {
  if (!_currentPoDetail) return;
  const notes = document.getElementById('po-resubmit-notes')?.value?.trim() || '';
  try {
    await api(`/api/purchase-orders/${_currentPoDetail.item.id}/resubmit`, {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user?.id, notes })
    });
    await openPoDetail(_currentPoDetail.item.id);
    loadPurchaseOrders();
  } catch(e) {
    alert(e.message || 'Erro ao reenviar PO.');
  }
}


let _purchaseFunctionsCache = [];
const _purchaseFunctionSelectedUnitIds = new Set();
let _purchaseFunctionUnitSearch = '';
let _purchaseFunctionEmployeeSearch = '';

function canManagePurchaseFunctions() {
  return ['general_admin', 'registry_admin'].includes(state.user?.role) && hasPermission('unit_links:manage');
}

function _getBuyerApproverUserEntry(employeeId) {
  return (state.users || []).find(u => String(u.linked_employee_id) === String(employeeId) && ['buyer','approver'].includes(u.role));
}

function filteredBuyerApproverEmployees() {
  const employees = _getBuyerApproverEmployees();
  const query = _purchaseFunctionEmployeeSearch.trim().toLowerCase();
  if (!query) return employees;
  return employees.filter((employee) => {
    const userEntry = _getBuyerApproverUserEntry(employee.id);
    const roleLabel = userEntry?.role ? tr('role.' + userEntry.role, ROLE_LABELS[userEntry.role] || userEntry.role) : '';
    return [employee.name, employee.employee_id_code, employee.role_name, employee.sector, userEntry?.username, userEntry?.full_name, roleLabel]
      .some((value) => String(value || '').toLowerCase().includes(query));
  });
}

function renderPurchaseFunctionControls() {
  const section = document.getElementById('purchase-functions-users-section');
  if (!section) return;
  section.style.display = canManagePurchaseFunctions() ? '' : 'none';
  if (section.style.display === 'none') return;
  const employeeSel = document.getElementById('purchase-function-employee');
  const warning = document.getElementById('purchase-functions-no-users-warning');
  const searchHint = document.getElementById('purchase-function-employee-search-hint');
  if (employeeSel) {
    const prev = employeeSel.value;
    const allEligible = _getBuyerApproverEmployees();
    const filteredEligible = filteredBuyerApproverEmployees();
    const selectedOutsideFilter = prev && allEligible.find((item) => String(item.id) === String(prev)) && !filteredEligible.find((item) => String(item.id) === String(prev));
    const visibleOptions = selectedOutsideFilter
      ? [allEligible.find((item) => String(item.id) === String(prev)), ...filteredEligible]
      : filteredEligible;
    if (warning) warning.style.display = allEligible.length ? 'none' : '';
    if (searchHint) {
      const query = _purchaseFunctionEmployeeSearch.trim();
      searchHint.hidden = !query || !allEligible.length;
      const resultKey = selectedOutsideFilter ? 'purchase.functionsSearchResultSelected' : 'purchase.functionsSearchResult';
      const resultFallback = selectedOutsideFilter
        ? `${filteredEligible.length} de ${allEligible.length} usuário(s) encontrado(s); seleção atual mantida fora do filtro`
        : `${filteredEligible.length} de ${allEligible.length} usuário(s) encontrado(s)`;
      searchHint.textContent = tr(resultKey, resultFallback).replace('{filtered}', filteredEligible.length).replace('{total}', allEligible.length) + '.';
    }
    employeeSel.innerHTML = allEligible.length
      ? `<option value="">${tr('purchase.functionsSelectPlaceholder', 'Selecione...')}</option>` + visibleOptions.map(e => {
          const userEntry = _getBuyerApproverUserEntry(e.id);
          const roleLabel = userEntry?.role ? tr('role.' + userEntry.role, ROLE_LABELS[userEntry.role] || '') : '';
          const login = userEntry?.username ? ` • ${userEntry.username}` : '';
          return `<option value="${e.id}">${esc(e.name || '')} — ${esc(e.employee_id_code || '')}${esc(login)} (${esc(roleLabel)})</option>`;
        }).join('')
      : `<option value="">${tr('purchase.functionsNoUsersLinked', 'Nenhum usuário Comprador/Aprovador com colaborador vinculado')}</option>`;
    if (prev) employeeSel.value = prev;
  }
  _syncPurchaseFunctionTypeToEmployee();
  syncPurchaseFunctionSelectionFromExistingLinks();
  renderPurchaseFunctionUnitChecks();
  renderPurchaseFunctionsList();
}

function _syncPurchaseFunctionTypeToEmployee() {
  const employeeSel = document.getElementById('purchase-function-employee');
  const typeSel = document.getElementById('purchase-function-type');
  const hintEl = document.getElementById('purchase-function-employee-hint');
  if (!employeeSel || !typeSel) return;
  const selectedEmployeeId = employeeSel.value;
  if (!selectedEmployeeId) {
    if (hintEl) hintEl.hidden = true;
    _purchaseFunctionSelectedUnitIds.clear();
    renderPurchaseFunctionUnitChecks();
    return;
  }
  const userEntry = _getBuyerApproverUserEntry(selectedEmployeeId);
  if (userEntry) {
    typeSel.value = userEntry.role;
    typeSel.disabled = true;
    if (hintEl) {
      hintEl.textContent = tr('purchase.functionsUserRoleHint', `Perfil de acesso do usuário: ${roleLabel(userEntry.role)}. O tipo é fixo conforme o perfil cadastrado.`).replace('{role}', roleLabel(userEntry.role));
      hintEl.hidden = false;
    }
  } else {
    typeSel.disabled = false;
    if (hintEl) hintEl.hidden = true;
  }
}

function selectedPurchaseFunctionContext() {
  const employeeId = document.getElementById('purchase-function-employee')?.value || '';
  const roleType = document.getElementById('purchase-function-type')?.value || 'buyer';
  return { employeeId, roleType };
}

function syncPurchaseFunctionSelectionFromExistingLinks() {
  const { employeeId, roleType } = selectedPurchaseFunctionContext();
  _purchaseFunctionSelectedUnitIds.clear();
  if (!employeeId) return;
  _purchaseFunctionsCache
    .filter((item) => String(item.employee_id) === String(employeeId) && String(item.role_type) === String(roleType))
    .forEach((item) => _purchaseFunctionSelectedUnitIds.add(String(item.unit_id)));
}

function setPurchaseFunctionUnitSelection(unitId, selected) {
  const id = String(unitId || '');
  if (!id) return;
  if (selected) _purchaseFunctionSelectedUnitIds.add(id);
  else _purchaseFunctionSelectedUnitIds.delete(id);
  renderPurchaseFunctionUnitChecks();
}

function filteredPurchaseFunctionUnits() {
  const query = _purchaseFunctionUnitSearch.trim().toLowerCase();
  const units = filterByUserCompany(state.units);
  if (!query) return units;
  return units.filter((unit) => [unit.name, unit.city, unit.unit_type, unitTypeLabel(unit.unit_type)]
    .some((value) => String(value || '').toLowerCase().includes(query)));
}

function renderPurchaseFunctionSelectedUnits(units) {
  const selectedWrap = document.getElementById('purchase-function-selected-units');
  const count = document.getElementById('purchase-function-selected-count');
  if (count) {
    const n = _purchaseFunctionSelectedUnitIds.size;
    const label = n === 1
      ? tr('purchase.functionsSelectedSingularLabel', 'selecionada')
      : tr('purchase.functionsSelectedPluralLabel', 'selecionadas');
    count.textContent = `${n} ${label}`;
  }
  if (!selectedWrap) return;
  const unitsById = new Map(units.map((unit) => [String(unit.id), unit]));
  const selectedUnits = Array.from(_purchaseFunctionSelectedUnitIds).map((id) => unitsById.get(id)).filter(Boolean);
  selectedWrap.innerHTML = selectedUnits.length
    ? selectedUnits.map((unit) => `<span class="unit-link-chip">${esc(unit.name || '')}<button type="button" aria-label="${esc(tr('purchase.functionsRemoveUnit', 'Remover {name}').replace('{name}', unit.name || 'unidade'))}" data-purchase-function-chip-remove="${esc(unit.id)}">×</button></span>`).join('')
    : `<span class="hint">${tr('purchase.functionsNoUnitSelected', 'Nenhuma unidade selecionada. Use a busca abaixo para vincular sem ocupar muito espaço.')}</span>`;
}

function renderPurchaseFunctionUnitChecks() {
  const wrap = document.getElementById('purchase-function-units');
  if (!wrap) return;
  const allUnits = filterByUserCompany(state.units);
  const units = filteredPurchaseFunctionUnits();
  renderPurchaseFunctionSelectedUnits(allUnits);
  wrap.innerHTML = units.map((unit) => {
    const checked = _purchaseFunctionSelectedUnitIds.has(String(unit.id)) ? 'checked' : '';
    return `<label class="unit-link-option"><input type="checkbox" data-purchase-function-unit="${esc(unit.id)}" ${checked}><span>${esc(unit.name || '')}<small>${esc([unitTypeLabel(unit.unit_type), unit.city].filter(Boolean).join(' • ') || 'Unidade')}</small></span></label>`;
  }).join('') || `<em style="color:var(--color-muted)">${tr('purchase.functionsNoUnitFound', 'Nenhuma unidade encontrada para a busca.')}</em>`;
}

function renderPurchaseFunctionsList() {
  const list = document.getElementById('purchase-functions-list');
  if (!list) return;
  if (!_purchaseFunctionsCache.length) {
    list.innerHTML = `<em style="color:var(--color-muted)">${tr('purchase.functionsEmptyList', 'Nenhuma função de compras configurada.')}</em>`;
    return;
  }
  const grouped = {};
  _purchaseFunctionsCache.forEach(item => {
    const key = `${item.employee_id}:${item.role_type}`;
    if (!grouped[key]) grouped[key] = {
      employee_name: item.employee_name,
      role_label: item.role_label,
      has_system_user: item.has_system_user,
      system_user_login: item.system_user_login || '',
      links: []
    };
    grouped[key].links.push(item);
  });
  list.innerHTML = Object.values(grouped).map(group => {
    const userBadge = group.has_system_user
      ? `<span style="font-size:11px;color:var(--color-success,green);margin-left:6px;" title="${esc(tr('purchase.functionsUserRegisteredTitle', 'Login: {login}').replace('{login}', group.system_user_login))}">✓ ${esc(tr('purchase.functionsUserRegistered', 'Usuário cadastrado'))}</span>`
      : `<span style="font-size:11px;color:var(--color-danger,red);margin-left:6px;" title="${esc(tr('purchase.functionsNoActiveUserTitle', 'Este colaborador não possui conta de usuário com o perfil correto'))}">⚠ ${esc(tr('purchase.functionsNoActiveUser', 'Sem usuário ativo'))}</span>`;
    return `
    <div style="margin-bottom:10px;padding:8px;background:var(--color-bg-alt);border-radius:6px;">
      <strong>${esc(group.employee_name || '—')}</strong>
      <span style="font-size:11px;color:var(--color-muted)">(${esc(group.role_label || '')})</span>
      ${userBadge}
      <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:6px;">
        ${group.links.map(link => `<span style="background:var(--color-primary-light,#e8f0fe);padding:2px 8px;border-radius:12px;font-size:12px;">${esc(link.unit_name || '—')} <button class="ghost" style="border:none;cursor:pointer;font-size:11px;color:var(--color-danger);" data-remove-purchase-function="${link.id}" aria-label="Remover vínculo">✕</button></span>`).join('')}
      </div>
    </div>
  `}).join('');
  list.querySelectorAll('[data-remove-purchase-function]').forEach(btn => {
    bindAppListener(btn, 'click', () => removePurchaseFunctionLink(parseInt(btn.dataset.removePurchaseFunction)));
  });
}

async function loadPurchaseFunctions() {
  if (!canManagePurchaseFunctions()) return;
  try {
    const res = await api(`/api/purchase-functions?${actorQuery()}`);
    _purchaseFunctionsCache = res.items || [];
    renderPurchaseFunctionControls();
  } catch (error) {
    const list = document.getElementById('purchase-functions-list');
    if (list) list.innerHTML = '<em>Erro ao carregar funções de compras.</em>';
  }
}

async function savePurchaseFunctionLinks() {
  const employeeId = document.getElementById('purchase-function-employee')?.value;
  const roleType = document.getElementById('purchase-function-type')?.value || 'buyer';
  const unitIds = Array.from(_purchaseFunctionSelectedUnitIds).map((id) => parseInt(id, 10)).filter(Boolean);
  const currentLinks = _purchaseFunctionsCache.filter((item) => String(item.employee_id) === String(employeeId || '') && String(item.role_type) === String(roleType));
  const selectedUnitSet = new Set(unitIds.map((id) => String(id)));
  const linksToRemove = currentLinks.filter((link) => !selectedUnitSet.has(String(link.unit_id)));
  if (!employeeId) { alert('Selecione o colaborador.'); return; }
  if (!unitIds.length && !currentLinks.length) { alert('Selecione ao menos uma unidade.'); return; }
  if (!unitIds.length && linksToRemove.length && !(await confirmDestructive({ title: 'Desvincular unidades', message: 'Desvincular este usuário de todas as unidades selecionadas anteriormente?', confirmLabel: 'Desvincular', variant: 'warning' }))) return;
  try {
    await api('/api/purchase-functions', { method: 'POST', body: JSON.stringify({ actor_user_id: state.user?.id, employee_id: parseInt(employeeId, 10), role_type: roleType, unit_ids: unitIds }) });
    await Promise.all(linksToRemove.map((link) => api(`/api/purchase-functions/${link.id}?${actorQuery()}`, { method: 'DELETE' })));
    await loadPurchaseFunctions();
    showToast('Vínculos de unidade atualizados com sucesso.');
  } catch (error) {
    alert(error.message || 'Erro ao salvar vínculos de unidade.');
  }
}

async function removePurchaseFunctionLink(linkId) {
  if (!(await confirmDestructive({ title: 'Remover vínculo', message: 'Remover este vínculo de compras?', confirmLabel: 'Remover', variant: 'danger' }))) return;
  try {
    await api(`/api/purchase-functions/${linkId}?${actorQuery()}`, { method: 'DELETE' });
    await loadPurchaseFunctions();
  } catch (error) {
    alert(error.message || 'Erro ao remover vínculo de compras.');
  }
}

// ── Vínculos de unidade (buyer/approver) — Fornecedores: somente leitura ──
let _unitLinksCache = [];

function _renderPurchaseFunctionLinksReadOnly(items, container) {
  if (!container) return;
  if (!items.length) {
    container.innerHTML = '<em style="color:var(--color-muted)">Nenhum comprador ou aprovador vinculado a unidades.</em>';
    return;
  }
  const byUser = {};
  items.forEach(lk => {
    const key = `${lk.employee_id}:${lk.role_type}`;
    if (!byUser[key]) byUser[key] = { name: lk.employee_name, role: lk.role_type, links: [] };
    byUser[key].links.push(lk);
  });
  container.innerHTML = Object.values(byUser).map(u => `
    <div style="margin-bottom:10px;padding:8px;background:var(--color-bg-alt);border-radius:4px;">
      <strong>${esc(u.name || '—')}</strong>
      <span style="font-size:11px;color:var(--color-muted);margin-left:6px;">(${esc(roleLabel(u.role))})</span>
      <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:6px;">
        ${u.links.map(lk => `<span style="background:var(--color-primary-light,#e8f0fe);padding:2px 10px;border-radius:12px;font-size:12px;">${esc(lk.unit_name || '—')}</span>`).join('')}
      </div>
    </div>
  `).join('');
}

async function loadFornecedoresPurchaseFunctions() {
  const listEl = document.getElementById('compras-links-list');
  if (!listEl) return;
  listEl.innerHTML = '<em style="color:var(--color-muted)">Carregando...</em>';
  try {
    const res = await api(`/api/purchase-functions?${actorQuery()}`);
    const allLinks = res.items || [];
    // Só sobrescreve o cache de unidades do próprio usuário se for admin
    // Buyers/approvers têm o cache carregado no bootstrap via /api/user-unit-links
    if (hasPermission('unit_links:manage')) {
      _unitLinksCache = allLinks;
    }
    _renderPurchaseFunctionLinksReadOnly(allLinks, listEl);
  } catch(e) {
    listEl.innerHTML = '<em style="color:var(--color-danger)">Erro ao carregar vínculos.</em>';
  }
}

async function loadUnitLinks() {
  await loadFornecedoresPurchaseFunctions();
}

async function loadComprasPurchaseConfig() {
  const card = document.getElementById('compras-workflow-config-card');
  if (!card) return;
  const role = state.user?.role;
  const canConfig = ['master_admin', 'general_admin', 'registry_admin'].includes(role);
  card.style.display = canConfig ? '' : 'none';
  if (!canConfig) return;
  const companyId = state.user?.company_id || '';
  if (!companyId) { card.style.display = 'none'; return; }
  try {
    const res = await api(`/api/company-purchase-config?${actorQuery()}&company_id=${companyId}`);
    const cfg = res.config || {};
    const checkbox = document.getElementById('compras-config-require-admin-review');
    if (checkbox) checkbox.checked = !!cfg.require_admin_review;
    const saveBtn = document.getElementById('compras-config-save-btn');
    const feedback = document.getElementById('compras-config-feedback');
    if (saveBtn) saveBtn.onclick = async () => {
      try {
        await api('/api/company-purchase-config', { method: 'POST', body: JSON.stringify({ actor_user_id: state.user?.id, company_id: companyId, require_admin_review: checkbox?.checked || false }) });
        if (feedback) { feedback.style.color = 'var(--color-success)'; feedback.textContent = 'Configuração salva!'; setTimeout(() => { if (feedback) feedback.textContent = ''; }, 3000); }
      } catch(e) {
        if (feedback) { feedback.style.color = 'var(--color-danger)'; feedback.textContent = e.message || 'Erro ao salvar.'; }
      }
    };
  } catch(e) {
    console.warn('[purchase-config] Erro ao carregar:', e);
  }
}

function _sizeGloveOpts(sel) {
  return ['N/A','XP (6)','P (7)','M (8)','G (9)','XG (10)','XXG (11)']
    .map(v => `<option value="${v}"${sel===v?' selected':''}>${v}</option>`).join('');
}
function _sizeOpts(sel) {
  const base = ['N/A'];
  for (let i = 34; i <= 60; i++) base.push(`N°${i}`);
  return base.map(v => `<option value="${v}"${sel===v?' selected':''}>${v}</option>`).join('');
}
function _sizeUniformOpts(sel) {
  return ['N/A','XP','PP','P','M','G','GG','XGG','XXG']
    .map(v => `<option value="${v}"${sel===v?' selected':''}>${v}</option>`).join('');
}

function _getPoUnitEpis(unitId) {
  const all = filterByUserCompany(state.epis || []).filter(e => Number(e.active) !== 0);
  if (!unitId) return all;
  return all.filter(e => !e.unit_id || String(e.unit_id) === String(unitId));
}

function buildPoItemRow(index, epi) {
  const unitId = document.getElementById('po-unit')?.value || '';
  const epis = _getPoUnitEpis(unitId);
  const epiOpts = '<option value="">Selecione o EPI...</option>' +
    epis.map(e => `<option value="${e.id}" data-mfr="${esc(e.manufacturer||'')}"${String(e.id)===String(epi?.epi_id)?' selected':''}>${esc(e.name)}${e.ca ? ` — ${tr('epi.caShort', 'CA')} ${e.ca}` : ''}</option>`).join('');
  return `<div class="po-item-row" data-po-item="${index}" style="display:grid;grid-template-columns:2.5fr 0.6fr 1fr 0.9fr 0.9fr 1fr 1.1fr 32px;gap:5px;margin-bottom:8px;align-items:end;">
    <div style="display:flex;flex-direction:column;gap:2px;">
      <span style="font-size:11px;color:var(--color-text-muted);">EPI</span>
      <select data-poi-epi="${index}">
        ${epiOpts}
      </select>
      <input type="hidden" value="${epi?.epi_id||''}" data-poi-epi-id="${index}">
      <input type="hidden" value="${epi?.epi_name||''}" data-poi-name="${index}">
    </div>
    <div style="display:flex;flex-direction:column;gap:2px;">
      <span style="font-size:11px;color:var(--color-text-muted);">Qtd</span>
      <input type="number" min="1" value="${epi?.quantity||1}" data-poi-qty="${index}" style="width:56px;">
    </div>
    <div style="display:flex;flex-direction:column;gap:2px;">
      <span style="font-size:11px;color:var(--color-text-muted);">Vlr Unit (R$)</span>
      <input type="number" step="0.01" min="0" value="${epi?.unit_price||''}" data-poi-price="${index}" placeholder="0,00">
    </div>
    <div style="display:flex;flex-direction:column;gap:2px;">
      <span style="font-size:11px;color:var(--color-text-muted);">Luva</span>
      <select data-poi-glove="${index}">${_sizeGloveOpts(epi?.glove_size||'N/A')}</select>
    </div>
    <div style="display:flex;flex-direction:column;gap:2px;">
      <span style="font-size:11px;color:var(--color-text-muted);">Calçado</span>
      <select data-poi-size="${index}">${_sizeOpts(epi?.size||'N/A')}</select>
    </div>
    <div style="display:flex;flex-direction:column;gap:2px;">
      <span style="font-size:11px;color:var(--color-text-muted);">Uniforme</span>
      <select data-poi-uniform="${index}">${_sizeUniformOpts(epi?.uniform_size||'N/A')}</select>
    </div>
    <div style="display:flex;flex-direction:column;gap:2px;">
      <span style="font-size:11px;color:var(--color-text-muted);">Fabricante</span>
      <input type="text" value="${esc(epi?.manufacturer||'')}" data-poi-mfr="${index}" readonly style="background:var(--color-bg-alt);color:var(--color-text-muted);font-size:12px;" placeholder="Auto">
    </div>
    <button type="button" class="ghost" style="padding:4px;font-size:16px;line-height:1;align-self:flex-end;" data-po-remove-item="${index}" aria-label="Remover item">✕</button>
  </div>`;
}

function onPoItemEpiChange(idx) {
  const list = document.getElementById('po-items-list');
  const row = list?.querySelector(`[data-po-item="${idx}"]`);
  if (!row) return;
  const sel = row.querySelector(`[data-poi-epi="${idx}"]`);
  const opt = sel?.options[sel.selectedIndex];
  row.querySelector(`[data-poi-epi-id="${idx}"]`).value = sel?.value || '';
  row.querySelector(`[data-poi-name="${idx}"]`).value = opt?.text || '';
  const mfr = row.querySelector(`[data-poi-mfr="${idx}"]`);
  if (mfr) mfr.value = opt?.dataset?.mfr || '';
}

function refreshPoItemEpiSelects() {
  const unitId = document.getElementById('po-unit')?.value || '';
  const hint = document.getElementById('po-items-unit-hint');
  if (hint) hint.style.display = unitId ? 'none' : '';
  const epis = _getPoUnitEpis(unitId);
  const epiOpts = '<option value="">Selecione o EPI...</option>' +
    epis.map(e => `<option value="${e.id}" data-mfr="${esc(e.manufacturer||'')}">${esc(e.name)}${e.ca ? ` — ${tr('epi.caShort', 'CA')} ${e.ca}` : ''}</option>`).join('');
  document.querySelectorAll('[data-poi-epi]').forEach(sel => {
    const idx = sel.dataset.poiEpi;
    const curId = document.querySelector(`[data-poi-epi-id="${idx}"]`)?.value || '';
    sel.innerHTML = epiOpts;
    if (curId) sel.value = curId;
  });
}

function populatePoSupplierSelect() {
  const sel = document.getElementById('po-supplier-select');
  if (!sel) return;
  const active = (_authorizedSuppliers || []).filter(s => s.active);
  sel.innerHTML = '<option value="">Selecione o fornecedor...</option>' +
    active.map(s => `<option value="${esc(s.name)}" data-cnpj="${s.cnpj||''}">${esc(s.name)}${s.cnpj ? ` — ${formatCNPJ(s.cnpj)}` : ''}</option>`).join('');
  const currentVal = sel.value;
  if (currentVal) sel.value = currentVal;
}

function collectPoItems() {
  const list = document.getElementById('po-items-list');
  if (!list) return [];
  return Array.from(list.querySelectorAll('[data-po-item]')).map(row => {
    const idx = row.dataset.poItem;
    return {
      epi_id: row.querySelector(`[data-poi-epi-id="${idx}"]`)?.value || '',
      epi_name: row.querySelector(`[data-poi-name="${idx}"]`)?.value || '',
      quantity: parseInt(row.querySelector(`[data-poi-qty="${idx}"]`)?.value || '1'),
      unit_price: parseFloat(row.querySelector(`[data-poi-price="${idx}"]`)?.value || '0'),
      glove_size: row.querySelector(`[data-poi-glove="${idx}"]`)?.value || 'N/A',
      size: row.querySelector(`[data-poi-size="${idx}"]`)?.value || 'N/A',
      uniform_size: row.querySelector(`[data-poi-uniform="${idx}"]`)?.value || 'N/A',
      manufacturer: row.querySelector(`[data-poi-mfr="${idx}"]`)?.value || '',
    };
  }).filter(i => i.epi_id);
}

function updatePoTotal() {
  const items = collectPoItems();
  const total = items.reduce((s, i) => s + (i.unit_price * i.quantity), 0);
  const el = document.getElementById('po-total-display');
  if (el) el.textContent = items.length ? `Total: ${fmtBrl(total)}` : '';
}

function populatePurchaseUnitSelects() {
  const units = state.units || [];
  const userCompanyId = state.user?.company_id;
  let filtered = units.filter(u => !userCompanyId || String(u.company_id) === String(userCompanyId));
  // Admin/user: restrito à própria unidade operacional
  const operationalUnitId = state.user?.operational_unit_id ? String(state.user.operational_unit_id) : null;
  if (['admin', 'user'].includes(state.user?.role) && operationalUnitId) {
    filtered = filtered.filter(u => String(u.id) === operationalUnitId);
  } else if (['buyer','approver'].includes(state.user?.role) && _unitLinksCache.length) {
    const linkedUnitIds = new Set(_unitLinksCache.map(lk => String(lk.unit_id)));
    if (linkedUnitIds.size) filtered = filtered.filter(u => linkedUnitIds.has(String(u.id)));
  }
  ['purchase-request-unit', 'po-unit'].forEach(id => {
    const sel = document.getElementById(id);
    if (!sel) return;
    const prev = sel.value;
    sel.innerHTML = '<option value="">Selecione...</option>' + filtered.map(u => `<option value="${u.id}">${u.name}</option>`).join('');
    if (['admin', 'user'].includes(state.user?.role) && operationalUnitId) {
      sel.value = operationalUnitId;
    } else if (filtered.length === 1) {
      sel.value = String(filtered[0].id);
    } else if (prev) {
      sel.value = prev;
    }
  });
  // Atualiza hint e EPIs ao repopular unidade no form de PO
  refreshPoItemEpiSelects();
  _populatePurchaseRequestEpiSelect();
  // Nota (auditoria F-05): removido o preenchimento de 'links-unit-select' —
  // a UI editável de vínculos de função de compras foi substituída pelos
  // controles 'purchase-functions-*' em static/views/usuarios.html; o elemento
  // não existe mais no DOM e o bloco era código morto (no-op).
}

async function _populatePurchaseRequestEpiSelect() {
  const sel = document.getElementById('purchase-request-epi-select');
  if (!sel) return;
  // Segue a MESMA regra de visibilidade de EPI do resto do sistema
  // (Global + Joint Venture da unidade + Unidade própria), aplicada server-side
  // pelo endpoint /api/stock/epis — o mesmo usado na Entrega de EPI. Antes este
  // select mostrava todos os EPIs da empresa, ignorando o escopo da unidade.
  const unitId = String(document.getElementById('purchase-request-unit')?.value || '').trim();
  const placeholder = '<option value="">Selecione o EPI...</option>';
  if (!unitId) {
    sel.innerHTML = '<option value="">Selecione a unidade primeiro...</option>';
    return;
  }
  const prev = sel.value;
  try {
    const params = new URLSearchParams({ actor_user_id: String(state.user?.id || ''), unit_id: unitId });
    if (state.user?.company_id) params.set('company_id', String(state.user.company_id));
    const payload = await apiWithBootstrapRetry(`/api/stock/epis?${params.toString()}`);
    const epis = (payload.items || []).filter(e => Number(e.active) !== 0);
    sel.innerHTML = placeholder +
      epis.map(e => `<option value="${e.id}">${esc(e.name)}${e.ca ? ` — ${tr('epi.caShort', 'CA')} ${esc(e.ca)}` : ''}${e.manufacturer ? ` (${esc(e.manufacturer)})` : ''}</option>`).join('');
    if (prev) sel.value = prev;
  } catch (error) {
    reportNonCriticalError('[purchase-request-epi] Falha ao carregar EPIs visíveis da unidade', error);
    sel.innerHTML = placeholder;
  }
}

function _renderManualRequestItems() {
  const preview = document.getElementById('purchase-request-items-preview');
  if (!preview) return;
  if (!_manualRequestItems.length) {
    preview.innerHTML = '<p style="color:var(--color-text-muted);margin:4px 0;">Nenhum item adicionado.</p>';
    return;
  }
  const rows = _manualRequestItems.map((item, i) => {
    const epi = (state.epis || []).find(e => String(e.id) === String(item.epi_id));
    const name = epi ? `${esc(epi.name)}${epi.ca ? ` — ${tr('epi.caShort', 'CA')} ${esc(epi.ca)}` : ''}` : `EPI #${item.epi_id}`;
    const origin = item.origin === 'employee_request' ? 'Solicitação' : item.origin === 'stock_minimum' ? 'Estoque mínimo' : 'Manual';
    const sizeInfo = [
      item.glove_size && item.glove_size !== 'N/A' ? `${tr('stock.gloveShort', 'Luva')}:${item.glove_size}` : '',
      item.size && item.size !== 'N/A' ? `${tr('stock.sizeShort', 'Tam')}:${item.size}` : '',
      item.uniform_size && item.uniform_size !== 'N/A' ? `${tr('stock.uniformShort', 'Unif')}:${item.uniform_size}` : '',
    ].filter(Boolean).join(' ') || '—';
    return `<tr><td>${name}</td><td style="text-align:center;">${item.quantity_requested}</td><td style="text-align:center;color:var(--color-text-muted);font-size:11px;">${esc(sizeInfo)}</td><td style="text-align:center;color:var(--color-text-muted);font-size:11px;">${origin}</td><td style="text-align:center;"><button type="button" class="btn ghost" style="padding:1px 7px;font-size:12px;" data-remove-manual-item="${i}" aria-label="Remover item">✕</button></td></tr>`;
  }).join('');
  preview.innerHTML = `<table style="width:100%;border-collapse:collapse;margin-top:4px;"><thead><tr style="font-size:12px;color:var(--color-text-muted);"><th scope="col" style="text-align:left;padding:2px 4px;">EPI</th><th scope="col" style="padding:2px 4px;">Qtd</th><th scope="col" style="padding:2px 4px;">Tamanho</th><th scope="col" style="padding:2px 4px;">Origem</th><th scope="col"></th></tr></thead><tbody>${rows}</tbody></table>`;
}

function _syncManualRequestItemsJson() {
  const input = document.getElementById('purchase-request-items-json');
  if (input) input.value = JSON.stringify(_manualRequestItems);
}

// ── Módulo Aprovação de Solicitações de EPI ──────────────────────────────────
const EPI_REQUEST_STATUS_LABELS = {
  'solicitado': 'Solicitado',
  'em análise': 'Em Análise',
  'aprovado': 'Aprovado',
  'rejeitado': 'Reprovado',
  'prorrogado': 'Prorrogado',
  'separado': 'Separado',
  'entregue': 'Entregue',
  'assinado': 'Assinado',
  'included_in_request': 'Em Requisição'
};

function epiRequestStatusBadge(status) {
  const label = EPI_REQUEST_STATUS_LABELS[status] || status;
  const toneMap = { aprovado: 'success', rejeitado: 'danger', prorrogado: 'warning', separado: 'success', entregue: 'success', assinado: 'success' };
  const tone = toneMap[status];
  const style = tone
    ? `background:var(--color-${tone}-bg);color:var(--color-${tone})`
    : 'background:var(--color-bg-alt);color:var(--color-text-muted)';
  return `<span class="status-chip" style="${style}">${label}</span>`;
}

let _aprovacoesList = [];
let _selectedAprovacoes = new Set();

async function loadAprovacoesSolicitacoes() {
  const tbody = document.getElementById('aprovacoes-tbody');
  const empty = document.getElementById('aprovacoes-empty');
  const table = document.getElementById('aprovacoes-table');
  if (!tbody) return;
  try {
    const res = await api(`/api/requests?${actorQuery()}`);
    _aprovacoesList = (res.items || []).filter(r => ['solicitado', 'prorrogado'].includes(r.status));
    _selectedAprovacoes.clear();
    const selectAll = document.getElementById('aprovacoes-select-all');
    if (selectAll) selectAll.checked = false;
    _syncAprovacoesBtnVisibility();
    if (!_aprovacoesList.length) {
      if (table) table.style.display = 'none';
      if (empty) { empty.style.display = ''; empty.textContent = 'Nenhuma solicitação pendente de aprovação.'; }
      return;
    }
    if (table) table.style.display = '';
    if (empty) empty.style.display = 'none';
    tbody.innerHTML = _aprovacoesList.map((r, i) => {
      const sizeInfo = [r.glove_size !== 'N/A' ? `Luva:${r.glove_size}` : '', r.size !== 'N/A' ? `Tam:${r.size}` : '', r.uniform_size !== 'N/A' ? `Unif:${r.uniform_size}` : ''].filter(Boolean).join(' ') || '—';
      const extra = r.status === 'rejeitado' && r.rejection_reason ? `<br><small style="color:var(--color-danger)">${esc(r.rejection_reason)}</small>` : r.status === 'prorrogado' && r.postponed_until ? `<br><small style="color:var(--color-warning)">Até: ${formatDate(r.postponed_until)}</small>` : '';
      return `<tr>
        <td><input type="checkbox" class="aprovacao-check" data-idx="${i}"></td>
        <td>${esc(r.employee_name || '—')}<br><small>${esc(r.employee_id_code || '')}</small></td>
        <td style="font-size:12px;">${esc(r.employee_sector || '—')}</td>
        <td>${esc(r.unit_name || '—')}</td>
        <td>${esc(r.epi_name || '—')}</td>
        <td>${esc(r.ca || '—')}</td>
        <td style="font-size:12px;">${sizeInfo}</td>
        <td>${esc(r.quantity)}</td>
        <td style="font-size:12px;">${formatDate(r.requested_at)}</td>
        <td>${epiRequestStatusBadge(r.status)}${extra}</td>
      </tr>`;
    }).join('');
    tbody.querySelectorAll('.aprovacao-check').forEach(cb => {
      safeOn(cb, 'change', () => {
        const idx = parseInt(cb.dataset.idx);
        if (cb.checked) _selectedAprovacoes.add(idx); else _selectedAprovacoes.delete(idx);
        _syncAprovacoesBtnVisibility();
      });
    });
  } catch(e) {
    if (empty) {
      empty.style.display = '';
      empty.textContent = isTemporaryBootstrapUnavailable(e)
        ? 'Sistema inicializando — clique em Atualizar para tentar novamente.'
        : 'Erro ao carregar solicitações.';
    }
  }
}

function _syncAprovacoesBtnVisibility() {
  const hasSelection = _selectedAprovacoes.size > 0;
  ['aprovacoes-aprovar-btn', 'aprovacoes-reprovar-btn', 'aprovacoes-prorrogar-btn'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = hasSelection ? '' : 'none';
  });
}

async function _executarAprovacaoEmLote(updates) {
  try {
    await api('/api/requests/bulk-status', { method: 'POST', body: JSON.stringify({ actor_user_id: state.user?.id, updates }) });
    showToast('Solicitações atualizadas com sucesso!');
    _selectedAprovacoes.clear();
    await loadAprovacoesSolicitacoes();
  } catch(e) {
    alert(e.message || 'Erro ao atualizar solicitações.');
  }
}

function _buildBulkUpdates(status, extra = {}) {
  return [..._selectedAprovacoes].map(idx => ({ request_id: _aprovacoesList[idx]?.id, status, ...extra })).filter(u => u.request_id);
}

function exportAprovacoesCsv() {
  const rows = _aprovacoesList;
  if (!rows.length) { alert('Nenhuma solicitação para exportar.'); return; }
  const header = ['ID', 'Colaborador', 'Matrícula', 'Setor', 'Unidade', 'EPI', tr('epi.caShort', 'CA'), 'Luva', 'Tamanho', 'Uniforme', 'Qtd', 'Status', 'Motivo Reprovação', 'Prorrogado Até', 'Data Solicitação'];
  const lines = rows.map(r => [
    r.id, r.employee_name, r.employee_id_code, r.employee_sector, r.unit_name, r.epi_name, r.ca,
    r.glove_size !== 'N/A' ? r.glove_size : '', r.size !== 'N/A' ? r.size : '', r.uniform_size !== 'N/A' ? r.uniform_size : '',
    r.quantity, EPI_REQUEST_STATUS_LABELS[r.status] || r.status, r.rejection_reason || '', r.postponed_until || '', r.requested_at?.slice(0, 10) || ''
  ].map(v => `"${String(v || '').replace(/"/g, '""')}"`).join(';'));
  const csv = [header.join(';'), ...lines].join('\r\n');
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `solicitacoes-epi-${new Date().toISOString().slice(0,10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Export / Email / Import de Requisição e PO ───────────────────────────────

function _setupPrDetailActions(pr, items) {
  const exportBtn = document.getElementById('req-export-csv-btn');
  if (exportBtn) exportBtn.onclick = () => exportPrCsv(pr, items);
  const emailBtn = document.getElementById('req-email-buyer-btn');
  if (emailBtn) emailBtn.onclick = () => emailPrToComprador(pr, items);
  const canImport = (hasPermission('purchase_orders:create') || hasPermission('purchase_orders:upload')) && isBuyerQuotationStatus(pr.status);
  const csvPanel = document.getElementById('req-po-csv-import-panel');
  const importBtn = document.getElementById('req-import-po-btn');
  if (importBtn) {
    importBtn.style.display = canImport ? '' : 'none';
    importBtn.onclick = () => {
      if (!csvPanel) return;
      const showing = csvPanel.style.display !== 'none';
      csvPanel.style.display = showing ? 'none' : '';
      if (!showing) initPoCsvImport(pr);
    };
  }
  if (csvPanel) {
    csvPanel.style.display = canImport ? '' : 'none';
    if (canImport) initPoCsvImport(pr);
  }
}

function exportPrCsv(pr, items) {
  const header = ['Item ID', 'Requisição', 'Unidade', 'EPI', tr('epi.caShort', 'CA'), 'Fabricante', 'Fornecedor', 'Colaborador', 'Setor', 'Origem', 'Luva', 'Tamanho', 'Uniforme', 'Qtd', 'Vlr Unit. (R$)', 'Total (R$)', 'Status Item'];
  const lines = items.map(i => [
    i.id || i.purchase_request_item_id || '', pr.id || '', pr.unit_name || '',
    i.epi_name || i.epi_display_name, i.ca || i.epi_ca, i.manufacturer, i.supplier,
    i.employee_name, i.employee_sector,
    i.origin === 'employee_request' ? 'Colaborador' : 'Estoque Mínimo',
    i.glove_size !== 'N/A' ? i.glove_size : '',
    i.size !== 'N/A' ? i.size : '',
    i.uniform_size !== 'N/A' ? i.uniform_size : '',
    i.quantity_requested || 1,
    i.unit_price ? String(Number(i.unit_price).toFixed(2)).replace('.', ',') : '',
    i.total_price ? String(Number(i.total_price).toFixed(2)).replace('.', ',') : '',
    ITEM_STATUS_LABELS[i.status] || i.status
  ].map(v => `"${String(v || '').replace(/"/g, '""')}"`).join(';'));
  const csv = [header.join(';'), ...lines].join('\r\n');
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `requisicao-${pr.id}-${(pr.created_at || '').slice(0,10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function emailPrToComprador(pr, items) {
  const subject = encodeURIComponent(`Requisição de Compra de EPI #${pr.id} — ${pr.title || ''}`);
  const unit = pr.unit_name || '—';
  const date = (pr.created_at || '').slice(0, 10);
  const itemLines = items.map((i, idx) => {
    const sizeInfo = [i.glove_size !== 'N/A' ? `Luva:${i.glove_size}`:null, i.size !== 'N/A'?`Tam:${i.size}`:null, i.uniform_size !== 'N/A'?`Unif:${i.uniform_size}`:null].filter(Boolean).join(' ') || '—';
    return `${idx+1}. ${i.epi_name || i.epi_display_name} | ${tr('epi.caShort', 'CA')}: ${i.ca || '—'} | ${sizeInfo} | Qtd: ${i.quantity_requested || 1} | Colaborador: ${i.employee_name || '—'}`;
  }).join('\n');
  const body = encodeURIComponent(
    `Olá,\n\nSegue a Requisição de Compra de EPI #${pr.id}.\n` +
    `Unidade: ${unit}\nData: ${date}\n\nItens:\n${itemLines}\n\n` +
    `Por favor, crie a PO no sistema interno e faça o upload dos valores no sistema de EPI.\n\nAtenciosamente,\n${state.user?.full_name || state.user?.username || 'Administrador'}`
  );
  window.open(`mailto:?subject=${subject}&body=${body}`, '_blank');
}

let _poCsvParsed = [];

function _readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || '');
      resolve(result.includes(',') ? result.split(',', 2)[1] : result);
    };
    reader.onerror = () => reject(reader.error || new Error('Erro ao ler arquivo.'));
    reader.readAsDataURL(file);
  });
}

function _normalizeCa(ca) {
  return String(ca || '').trim().replace(/[-\s]+$/, '').replace(/^[-\s]+/, '').toLowerCase();
}

function _parsePurchaseMoney(value) {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return Math.round(value * 100) / 100;
  }
  let text = String(value ?? '').trim();
  if (!text) return 0;
  text = text.replace(/\u00a0/g, ' ')
    .replace(/r\$/gi, '')
    .replace(/\s+/g, '')
    .replace(/[^0-9,.\-]/g, '');
  if (!text || ['-', ',', '.', '-,', '-.'].includes(text)) return 0;
  const negative = text.startsWith('-');
  text = text.replace(/-/g, '');
  const commaIndex = text.lastIndexOf(',');
  const dotIndex = text.lastIndexOf('.');
  let normalized = '';
  if (commaIndex >= 0 || dotIndex >= 0) {
    const decimalSep = commaIndex > dotIndex ? ',' : '.';
    const parts = text.split(decimalSep);
    const fractional = parts.pop() || '0';
    const integer = parts.join('').replace(/[,.]/g, '') || '0';
    normalized = `${negative ? '-' : ''}${integer}.${fractional}`;
  } else {
    normalized = `${negative ? '-' : ''}${text.replace(/[,.]/g, '')}`;
  }
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? Math.round(parsed * 100) / 100 : 0;
}

function _parsePurchaseQuantity(value, fallback = 1) {
  const parsed = Number(String(value ?? '').replace(/\u00a0/g, '').replace(',', '.').replace(/[^0-9.\-]/g, ''));
  const quantity = Math.round(parsed);
  return Number.isFinite(quantity) && quantity > 0 ? quantity : fallback;
}

async function _parsePoImportFile(file) {
  const contentBase64 = await _readFileAsBase64(file);
  const response = await api('/api/purchase-quote-file/parse', {
    method: 'POST',
    body: JSON.stringify({
      actor_user_id: state.user?.id,
      filename: file.name || 'cotacao.csv',
      content_base64: contentBase64,
    })
  });
  return response.items || [];
}


function _normalizePurchaseText(value) {
  return String(value || '').trim().toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, ' ');
}

function _normalizePurchaseSize(value) {
  const text = _normalizePurchaseText(value);
  return (!text || text === 'n/a' || text === 'na') ? '' : text;
}

function _normalizePurchaseOrigin(value) {
  const text = _normalizePurchaseText(value);
  if (text.includes('colaborador') || text.includes('employee')) return 'employee_request';
  if (text.includes('estoque') || text.includes('stock')) return 'stock_minimum';
  return text;
}

function _scorePurchaseImportMatch(row, item) {
  let score = 0;
  const rowCa = _normalizeCa(row.ca);
  const rowEpi = _normalizePurchaseText(row.epi);
  const rowEmployee = _normalizePurchaseText(row.colaborador);
  const rowUnit = _normalizePurchaseText(row.unidade);
  const rowSupplier = _normalizePurchaseText(row.fornecedor);
  const rowOrigin = _normalizePurchaseOrigin(row.origem);
  const rowSize = _normalizePurchaseSize(row.tamanho);
  const rowGlove = _normalizePurchaseSize(row.tamanho_luva);
  const rowUniform = _normalizePurchaseSize(row.tamanho_uniforme);
  if (rowCa && _normalizeCa(item.ca || item.epi_ca) === rowCa) score += 4;
  if (rowEpi && _normalizePurchaseText(item.epi_name || item.epi_display_name) === rowEpi) score += 3;
  if (rowEmployee && _normalizePurchaseText(item.employee_name) === rowEmployee) score += 3;
  if (rowUnit && _normalizePurchaseText(item.unit_name) === rowUnit) score += 2;
  if (rowSupplier && _normalizePurchaseText(item.supplier) === rowSupplier) score += 1;
  if (rowOrigin && _normalizePurchaseOrigin(item.origin) === rowOrigin) score += 1;
  if (rowSize && _normalizePurchaseSize(item.size) === rowSize) score += 2;
  if (rowGlove && _normalizePurchaseSize(item.glove_size) === rowGlove) score += 2;
  if (rowUniform && _normalizePurchaseSize(item.uniform_size) === rowUniform) score += 2;
  return score;
}

function _matchPurchaseImportRows(rows, prItems) {
  const used = new Set();
  return rows.map((row) => {
    const itemId = String(row.item_id || '').trim();
    if (itemId) {
      const exactIndex = prItems.findIndex((item, idx) => !used.has(idx) && String(item.id || item.purchase_request_item_id || '') === itemId);
      if (exactIndex >= 0) {
        used.add(exactIndex);
        return prItems[exactIndex];
      }
    }
    let bestIndex = -1;
    let bestScore = 0;
    prItems.forEach((item, idx) => {
      if (used.has(idx)) return;
      const score = _scorePurchaseImportMatch(row, item);
      if (score > bestScore) {
        bestScore = score;
        bestIndex = idx;
      }
    });
    if (bestIndex >= 0 && bestScore > 0) {
      used.add(bestIndex);
      return prItems[bestIndex];
    }
    return null;
  });
}

// ── EPI Feedback Manager (Avaliações e Sugestões) ────────────────────────────


// ── Avaliações e Sugestões de EPI ─────────────────────────────────────────────

(function initAvaliaoesModule() {
  const PORTAL_STATUS_LABELS = {
    '': 'Enviada', enviado_gestor: 'Em Análise', enviado_admin: 'Encaminh. Admin',
    aceito: 'Aceito', recusado: 'Recusado', bem_avaliado: '⭐ Bem Avaliado',
    mal_avaliado: '⚠ Mal Avaliado', em_reavaliacao_3m: 'Reavaliação 3m', em_reavaliacao_6m: 'Reavaliação 6m',
  };
  const PORTAL_STATUS_COLORS = {
    aceito: 'success', recusado: 'danger', bem_avaliado: 'success', mal_avaliado: 'danger',
    em_reavaliacao_3m: 'warning', em_reavaliacao_6m: 'warning', enviado_admin: 'accent',
    enviado_gestor: 'info',
  };
  const EVAL_STATUS_LABELS = { normal: 'Normal', super_bem_avaliado: '⭐⭐ Super Bem Avaliado', super_mal_avaliado: '⚠⚠ Super Mal Avaliado' };
  const EVAL_STATUS_COLORS = { normal: '', super_bem_avaliado: 'success', super_mal_avaliado: 'danger' };
  const RISK_LABELS = { nenhum: 'Nenhum', baixo: 'Baixo', alto: '⚠ Alto' };
  const RISK_COLORS = { nenhum: '', baixo: 'warning', alto: 'danger' };

  let _summaryData = null;

  function canDecide() {
    return hasPermission('epi_evaluation:decide') && state.user?.role === 'general_admin';
  }
  function canPreEval() {
    return hasPermission('epi_evaluation:decide');
  }
  function canManagerEval() {
    return hasPermission('epi_feedback:manager_eval');
  }
  function canAcceptSuggestion() {
    return hasPermission('epi_evaluation:accept_suggestion');
  }

  function portalChip(status) {
    const label = PORTAL_STATUS_LABELS[status] || status || '—';
    const color = PORTAL_STATUS_COLORS[status] || '';
    return color
      ? `<span class="status-chip" style="background:var(--${color}-soft);color:var(--${color});font-size:11px;">${esc(label)}</span>`
      : `<span class="status-chip" style="font-size:11px;">${esc(label)}</span>`;
  }

  function evalChip(status) {
    const label = EVAL_STATUS_LABELS[status] || status || 'Normal';
    const color = EVAL_STATUS_COLORS[status] || '';
    return color
      ? `<span class="status-chip" style="background:var(--${color}-soft);color:var(--${color});font-size:11px;">${esc(label)}</span>`
      : `<span class="status-chip" style="font-size:11px;">${esc(label)}</span>`;
  }

  function riskChip(risk) {
    const label = RISK_LABELS[risk] || risk || '—';
    const color = RISK_COLORS[risk] || '';
    return color
      ? `<span class="status-chip" style="background:var(--${color}-soft);color:var(--${color});font-size:11px;">${esc(label)}</span>`
      : `<span class="status-chip" style="font-size:11px;">${esc(label)}</span>`;
  }

  function updateSummaryCards(data) {
    const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val ?? '—'; };
    setEl('aval-total-count', data.total ?? 0);
    setEl('aval-reclamacoes-count', data.reclamacoes ?? 0);
    setEl('aval-elogios-count', data.elogios ?? 0);
    setEl('aval-pendentes-count', data.pendentes ?? 0);
    setEl('aval-sugestoes-count', data.sugestoes ?? 0);
    renderDestaques(data);
  }

  function renderDestaques(data) {
    const role = state.user?.role || '';
    // `epi_manager` é apelido de `user` (ROLE_ALIASES em core/roles.py) — o
    // role do ator sempre chega normalizado como `user`, então checar o
    // apelido aqui nunca batia e escondia os destaques do Gestor de EPI.
    const canSeeDestaques = ['general_admin', 'registry_admin', 'user'].includes(role);
    const wrapper = document.getElementById('avaliacoes-destaques');
    if (!wrapper) return;
    if (!canSeeDestaques) { wrapper.style.display = 'none'; return; }
    wrapper.style.display = '';

    const reclamados = Array.isArray(data.top_reclamados) ? data.top_reclamados : [];
    const elogiados = Array.isArray(data.top_elogiados) ? data.top_elogiados : [];

    const recList = document.getElementById('aval-top-reclamados');
    if (recList) {
      if (!reclamados.length) {
        recList.innerHTML = '<li style="opacity:.5;font-size:13px;">Sem reclamações registradas.</li>';
      } else {
        recList.innerHTML = reclamados.map((item) =>
          `<li style="margin-bottom:6px;font-size:13px;">
            <strong>${escapeHtml(item.epi_name)}</strong>
            <span style="background:var(--danger-soft);color:var(--danger);border-radius:99px;padding:1px 7px;font-size:11px;margin-left:6px;">${item.count} recl.</span>
          </li>`
        ).join('');
      }
    }

    const eloList = document.getElementById('aval-top-elogiados');
    if (eloList) {
      if (!elogiados.length) {
        eloList.innerHTML = '<li style="opacity:.5;font-size:13px;">Sem elogios registrados.</li>';
      } else {
        eloList.innerHTML = elogiados.map((item) =>
          `<li style="margin-bottom:6px;font-size:13px;">
            <strong>${escapeHtml(item.epi_name)}</strong>
            <span style="background:var(--success-soft);color:var(--success);border-radius:99px;padding:1px 7px;font-size:11px;margin-left:6px;">${item.count} elog.</span>
          </li>`
        ).join('');
      }
    }
  }

  function renderPendentes(items) {
    const role = state.user?.role || '';
    const isAdmin = role === 'general_admin' || role === 'registry_admin';
    // Admins usam o tbody unificado dentro do pane avaliacao-final
    const tbodyId = isAdmin ? 'aval-unified-action-tbody' : 'aval-pendentes-tbody';
    const tbody = document.getElementById(tbodyId);
    const unifiedSection = document.getElementById('aval-unified-action-section');
    if (isAdmin && unifiedSection) unifiedSection.style.display = '';
    if (!tbody) return;
    const isGeneralAdmin = role === 'general_admin';
    const headerEl = document.querySelector('#avaliacoes-pane-pendentes h3');
    if (headerEl) headerEl.textContent = isAdmin ? 'Avaliações Pendentes de Ação Administrativa' : 'Avaliações Pendentes de Validação';

    if (!isAdmin) {
      const pending = items.filter((i) => (i.manager_eval_status || 'pendente') === 'pendente');
      if (!pending.length) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;opacity:.6;">Sem avaliações pendentes.</td></tr>';
        return;
      }
      const typeLabel = (fb) => {
        const t = fb.feedback_subtype || fb.type || '';
        if (t === 'elogio') return '<span style="background:var(--success-soft);color:var(--success);font-size:10px;padding:1px 6px;border-radius:99px;">👍 Elogio EPI</span>';
        if (t === 'reclamacao') return '<span style="background:var(--danger-soft);color:var(--danger);font-size:10px;padding:1px 6px;border-radius:99px;">👎 Reclamação EPI</span>';
        if (t === 'sugestao' || t === 'sugestao_nova' || fb.suggested_new_epi_name) return '<span style="background:var(--accent-soft);color:var(--accent);font-size:10px;padding:1px 6px;border-radius:99px;">💡 Sugestão</span>';
        return '<span style="background:var(--muted-soft);color:var(--color-text-muted);font-size:10px;padding:1px 6px;border-radius:99px;">📋 Avaliação</span>';
      };
      tbody.innerHTML = pending.map((fb) => {
        const actions = canManagerEval()
          ? `<button class="primary" style="font-size:11px;padding:3px 8px;" data-aval-validate="${esc(fb.id)}" type="button">Validar</button>
             <button class="ghost" style="font-size:11px;padding:3px 8px;margin-left:4px;" data-aval-reject="${esc(fb.id)}" type="button">Rejeitar</button>`
          : '—';
        return `<tr>
          <td>#${esc(fb.id)}</td><td>${esc(fb.epi_name || '—')}</td><td>${esc(fb.employee_name || '—')}</td>
          <td>${typeLabel(fb)}</td><td>${riskChip(fb.risk_level)}</td>
          <td style="font-size:11px;">${fb.suggested_new_epi_name ? `<em>${esc(fb.suggested_new_epi_name)}</em>` : `C:${esc(fb.comfort_rating)} Q:${esc(fb.quality_rating)} A:${esc(fb.adequacy_rating)} D:${esc(fb.performance_rating)}`}</td>
          <td style="max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${esc(fb.comments || fb.improvement_suggestion || fb.suggested_new_epi_notes || '—')}</td>
          <td>${esc(formatDate(fb.created_at))}</td>
          <td style="white-space:nowrap;">${actions}</td>
        </tr>`;
      }).join('');
      tbody.querySelectorAll('[data-aval-validate]').forEach((btn) =>
        bindAppListener(btn, 'click', () => openModal('validate', btn.dataset.avalValidate, pending))
      );
      tbody.querySelectorAll('[data-aval-reject]').forEach((btn) =>
        bindAppListener(btn, 'click', () => openModal('reject', btn.dataset.avalReject, pending))
      );
      return;
    }

    // Admin view: split into pre-eval (enviado_admin) and final-eval (avaliacao_previa)
    const preEvalItems = items.filter((i) => (i.employee_portal_status || '') === 'enviado_admin');
    const finalEvalItems = items.filter((i) => (i.employee_portal_status || '') === 'avaliacao_previa');

    const typeLabel = (fb) => {
      const t = fb.feedback_subtype || fb.type || '';
      if (t === 'elogio') return '<span style="background:var(--success-soft);color:var(--success);font-size:10px;padding:1px 6px;border-radius:99px;">👍 Elogio EPI</span>';
      if (t === 'reclamacao') return '<span style="background:var(--danger-soft);color:var(--danger);font-size:10px;padding:1px 6px;border-radius:99px;">👎 Reclamação EPI</span>';
      if (t === 'sugestao' || t === 'sugestao_nova' || fb.suggested_new_epi_name) return '<span style="background:var(--accent-soft);color:var(--accent);font-size:10px;padding:1px 6px;border-radius:99px;">💡 Sugestão</span>';
      return '<span style="background:var(--muted-soft);color:var(--color-text-muted);font-size:10px;padding:1px 6px;border-radius:99px;">📋 Avaliação</span>';
    };
    const rowHtml = (fb, actionHtml) => `<tr>
      <td>#${esc(fb.id)}</td><td>${esc(fb.epi_name || '—')}</td><td>${esc(fb.employee_name || '—')}</td>
      <td>${typeLabel(fb)}</td><td>${riskChip(fb.risk_level)}</td>
      <td style="font-size:11px;">${fb.suggested_new_epi_name ? `<em>${esc(fb.suggested_new_epi_name)}</em>` : `C:${esc(fb.comfort_rating)} Q:${esc(fb.quality_rating)} A:${esc(fb.adequacy_rating)} D:${esc(fb.performance_rating)}`}</td>
      <td style="max-width:130px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${esc(fb.comments || fb.improvement_suggestion || fb.suggested_new_epi_notes || '—')}</td>
      <td>${esc(formatDate(fb.created_at))}</td>
      <td style="white-space:nowrap;">${actionHtml}</td>
    </tr>`;

    let html = '';
    if (preEvalItems.length) {
      html += `<tr><td colspan="9" style="background:var(--warning-soft);font-weight:600;font-size:12px;padding:6px 10px;">📋 Aguardando Avaliação Prévia (${preEvalItems.length})</td></tr>`;
      html += preEvalItems.map((fb) => {
        const btn = canPreEval()
          ? `<button class="primary" style="font-size:11px;padding:3px 8px;" data-aval-pre-eval="${esc(fb.id)}" type="button">Avaliação Prévia</button>`
          : '—';
        return rowHtml(fb, btn);
      }).join('');
    }
    if (finalEvalItems.length) {
      html += `<tr><td colspan="9" style="background:var(--success-soft);font-weight:600;font-size:12px;padding:6px 10px;">✅ Aguardando Avaliação Final — Admin Geral (${finalEvalItems.length})</td></tr>`;
      html += finalEvalItems.map((fb) => {
        const btn = isGeneralAdmin && canDecide()
          ? `<button class="primary" style="font-size:11px;padding:3px 8px;background:#16a34a;" data-aval-admin-eval="${esc(fb.id)}" type="button">Avaliação Final</button>`
          : '<span style="font-size:11px;opacity:.6;">Prévia Concluída</span>';
        return rowHtml(fb, btn);
      }).join('');
    }
    if (!html) {
      tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;opacity:.6;">Sem avaliações aguardando ação administrativa.</td></tr>';
      return;
    }
    tbody.innerHTML = html;
    tbody.querySelectorAll('[data-aval-pre-eval]').forEach((btn) =>
      bindAppListener(btn, 'click', () => openModal('pre_evaluate', btn.dataset.avalPreEval, items))
    );
    tbody.querySelectorAll('[data-aval-admin-eval]').forEach((btn) =>
      bindAppListener(btn, 'click', () => openModal('admin_evaluate', btn.dataset.avalAdminEval, items))
    );
  }

  function renderReclamacoes(data) {
    const riskEl = document.getElementById('aval-risk-breakdown');
    if (riskEl) {
      const rb = data.risk_breakdown || {};
      const riscos = [['alto', '⚠ Alto', 'var(--danger)'], ['baixo', 'Baixo', 'var(--warning)'], ['nenhum', 'Nenhum', 'var(--color-text-muted)']];
      riskEl.innerHTML = riscos.map(([k, label, color]) =>
        `<article class="card" style="text-align:center;padding:10px;">
           <strong style="font-size:20px;color:${color};display:block;">${rb[k] || 0}</strong>
           <small>${esc(label)}</small>
         </article>`
      ).join('');
    }
    const tbody = document.getElementById('aval-reclamacoes-tbody');
    if (tbody) {
      const byEpi = {};
      (data.reclamacao_items || []).forEach((fb) => {
        const key = fb.epi_name || String(fb.epi_id) || 'N/A';
        if (!byEpi[key]) byEpi[key] = { epi_name: key, count: 0, high_risk: 0, ids: [] };
        byEpi[key].count++;
        if (fb.risk_level === 'alto') byEpi[key].high_risk++;
        byEpi[key].ids.push(fb.id);
      });
      const rows = Object.values(byEpi).sort((a, b) => b.count - a.count);
      tbody.innerHTML = rows.length ? rows.map((r) => {
        const evalStatus = data.items.find((i) => (i.epi_name || String(i.epi_id)) === r.epi_name)?.evaluation_status || 'normal';
        const reassessBtn = canDecide()
          ? `<button class="ghost" style="font-size:11px;padding:3px 8px;" data-aval-reassess-epi="${esc(r.ids[0])}" type="button">Reavaliação</button>`
          : '';
        return `<tr>
          <td>${esc(r.epi_name)}</td>
          <td><strong>${r.count}</strong></td>
          <td>${r.high_risk > 0 ? `<span style="color:var(--danger);font-weight:600;">${r.high_risk}</span>` : '0'}</td>
          <td>${evalChip(evalStatus)}</td>
          <td>${reassessBtn}</td>
        </tr>`;
      }).join('') : '<tr><td colspan="5" style="text-align:center;opacity:.6;">Sem reclamações.</td></tr>';
      tbody.querySelectorAll('[data-aval-reassess-epi]').forEach((btn) =>
        bindAppListener(btn, 'click', () => openModal('reassessment', btn.dataset.avalReassessEpi, data.items))
      );
    }
    const detailTbody = document.getElementById('aval-reclamacoes-detail-tbody');
    if (detailTbody) {
      const items = data.reclamacao_items || [];
      detailTbody.innerHTML = items.length ? items.map((fb) => {
        const reassessBtn = canDecide()
          ? `<button class="ghost" style="font-size:11px;padding:3px 8px;" data-aval-reassess="${esc(fb.id)}" type="button">Reavaliação</button>`
          : '';
        const portalStatus = fb.employee_portal_status || '';
        const techAction = (portalStatus === 'avaliacao_previa' && canDecide()) ? 'admin_evaluate' : (canPreEval() ? 'pre_evaluate' : null);
        const techBtn = techAction
          ? `<button class="primary" style="font-size:11px;padding:3px 8px;margin-left:4px;" data-aval-tech="${esc(fb.id)}" data-aval-tech-action="${techAction}" type="button">${techAction === 'admin_evaluate' ? 'Av. Final' : 'Av. Prévia'}</button>`
          : '';
        return `<tr>
          <td>#${esc(fb.id)}</td>
          <td>${esc(fb.epi_name || '—')}</td>
          <td>${esc(fb.employee_name || '—')}</td>
          <td>${riskChip(fb.risk_level)}</td>
          <td style="max-width:130px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${esc(fb.comments || '—')}</td>
          <td>${portalChip(fb.employee_portal_status)}</td>
          <td>${esc(formatDate(fb.created_at))}</td>
          <td style="white-space:nowrap;">${reassessBtn}${techBtn}</td>
        </tr>`;
      }).join('') : '<tr><td colspan="8" style="text-align:center;opacity:.6;">Sem reclamações.</td></tr>';
      detailTbody.querySelectorAll('[data-aval-reassess]').forEach((btn) =>
        bindAppListener(btn, 'click', () => openModal('reassessment', btn.dataset.avalReassess, data.items))
      );
      detailTbody.querySelectorAll('[data-aval-tech]').forEach((btn) =>
        bindAppListener(btn, 'click', () => openModal(btn.dataset.avalTechAction || 'pre_evaluate', btn.dataset.avalTech, data.items))
      );
    }
  }

  function renderElogios(items) {
    const tbody = document.getElementById('aval-elogios-tbody');
    if (!tbody) return;
    tbody.innerHTML = items.length ? items.map((fb) => {
      const elPortalStatus = fb.employee_portal_status || '';
      const elTechAction = (elPortalStatus === 'avaliacao_previa' && canDecide()) ? 'admin_evaluate' : (canPreEval() ? 'pre_evaluate' : null);
      const techBtn = elTechAction
        ? `<button class="primary" style="font-size:11px;padding:3px 8px;" data-aval-tech-el="${esc(fb.id)}" data-aval-el-action="${elTechAction}" type="button">${elTechAction === 'admin_evaluate' ? 'Av. Final' : 'Av. Prévia'}</button>`
        : '';
      return `<tr>
        <td>#${esc(fb.id)}</td>
        <td>${esc(fb.epi_name || '—')}</td>
        <td>${esc(fb.employee_name || '—')}</td>
        <td style="font-size:11px;">C:${esc(fb.comfort_rating)} Q:${esc(fb.quality_rating)} A:${esc(fb.adequacy_rating)} D:${esc(fb.performance_rating)}</td>
        <td style="max-width:130px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${esc(fb.comments || '—')}</td>
        <td>${evalChip(fb.evaluation_status || 'normal')}</td>
        <td>${esc(formatDate(fb.created_at))}</td>
        <td>${techBtn}</td>
      </tr>`;
    }).join('') : '<tr><td colspan="8" style="text-align:center;opacity:.6;">Sem elogios.</td></tr>';
    tbody.querySelectorAll('[data-aval-tech-el]').forEach((btn) =>
      bindAppListener(btn, 'click', () => openModal(btn.dataset.avalElAction || 'pre_evaluate', btn.dataset.avalTechEl, items))
    );
  }

  function renderSugestoes(items) {
    const tbody = document.getElementById('aval-sugestoes-tbody');
    if (!tbody) return;
    tbody.innerHTML = items.length ? items.map((fb) => {
      const acceptBtn = canAcceptSuggestion() && fb.suggested_new_epi_name
        ? `<button class="primary" style="font-size:11px;padding:3px 8px;" data-aval-accept="${esc(fb.id)}" type="button">Aceitar</button>`
        : '';
      const rejectBtn = canDecide()
        ? `<button class="ghost" style="font-size:11px;padding:3px 8px;margin-left:4px;" data-aval-reject-sug="${esc(fb.id)}" type="button">Recusar</button>`
        : '';
      const sugPortalStatus = fb.employee_portal_status || '';
      const sugTechAction = (sugPortalStatus === 'avaliacao_previa' && canDecide()) ? 'admin_evaluate' : (canPreEval() ? 'pre_evaluate' : null);
      const techBtn = sugTechAction
        ? `<button class="ghost" style="font-size:11px;padding:3px 8px;margin-left:4px;border-color:var(--color-primary,#2563eb);color:var(--color-primary,#2563eb);" data-aval-tech-sug="${esc(fb.id)}" data-aval-sug-action="${sugTechAction}" type="button">${sugTechAction === 'admin_evaluate' ? 'Av. Final' : 'Av. Prévia'}</button>`
        : '';
      return `<tr>
        <td>#${esc(fb.id)}</td>
        <td>${esc(fb.employee_name || '—')}</td>
        <td>${esc(fb.epi_name || '—')}</td>
        <td><strong>${esc(fb.suggested_new_epi_name || '—')}</strong></td>
        <td style="max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${esc(fb.suggested_new_epi_notes || fb.improvement_suggestion || '—')}</td>
        <td>${portalChip(fb.employee_portal_status)}</td>
        <td>${esc(formatDate(fb.created_at))}</td>
        <td style="white-space:nowrap;">${acceptBtn}${rejectBtn}${techBtn}</td>
      </tr>`;
    }).join('') : '<tr><td colspan="8" style="text-align:center;opacity:.6;">Sem sugestões.</td></tr>';
    tbody.querySelectorAll('[data-aval-accept]').forEach((btn) =>
      bindAppListener(btn, 'click', () => openModal('accept_suggestion', btn.dataset.avalAccept, items))
    );
    tbody.querySelectorAll('[data-aval-reject-sug]').forEach((btn) =>
      bindAppListener(btn, 'click', () => openModal('reject', btn.dataset.avalRejectSug, items))
    );
    tbody.querySelectorAll('[data-aval-tech-sug]').forEach((btn) =>
      bindAppListener(btn, 'click', () => openModal(btn.dataset.avalSugAction || 'pre_evaluate', btn.dataset.avalTechSug, items))
    );
  }

  async function renderRanking() {
    const tbody = document.getElementById('aval-ranking-tbody');
    const sugTbody = document.getElementById('aval-ranking-sug-tbody');
    try {
      const [epiData, sugData] = await Promise.all([
        api('/api/avaliacoes/ranking'),
        api('/api/avaliacoes/ranking-sugestoes'),
      ]);
      if (tbody) {
        const items = epiData.items || [];
        tbody.innerHTML = items.length ? items.map((r, idx) => {
          const score = Number(r.score) || 0;
          const scoreColor = score > 0 ? 'var(--success)' : score < 0 ? 'var(--danger)' : 'var(--color-text-muted)';
          return `<tr>
            <td><strong>${idx + 1}</strong></td>
            <td>${esc(r.epi_name)}</td>
            <td><strong style="color:${scoreColor}">${score > 0 ? '+' : ''}${score}</strong></td>
            <td style="color:var(--success);font-weight:600;">${r.rank_excelente || 0}</td>
            <td style="color:var(--success);">${r.rank_otimo || 0}</td>
            <td style="color:var(--success);">${r.rank_muito_bom || 0}</td>
            <td style="color:var(--danger);font-weight:600;">${r.rank_pessimo || 0}</td>
            <td style="color:var(--danger);">${r.rank_muito_ruim || 0}</td>
            <td style="color:var(--pending);">${r.rank_ruim || 0}</td>
            <td style="color:var(--success);">${r.total_elogios}</td>
            <td style="color:var(--danger);">${r.total_reclamacoes}</td>
            <td style="font-size:11px;">${[r.avg_comfort, r.avg_quality, r.avg_adequacy, r.avg_performance].map((v) => v ? Number(v).toFixed(1) : '—').join('/')}</td>
            <td>${evalChip(r.evaluation_status)}</td>
          </tr>`;
        }).join('') : '<tr><td colspan="13" style="text-align:center;opacity:.6;">Sem dados. Clique em "Computar Status EPIs" primeiro.</td></tr>';
      }
      if (sugTbody) {
        const sugs = sugData.items || [];
        const SUG_STATUS_LABELS = { aceito: '✓ Aceito', recusado: '✗ Recusado', '': 'Pendente' };
        const SUG_STATUS_COLORS = { aceito: 'success', recusado: 'danger', '': 'muted' };
        sugTbody.innerHTML = sugs.length ? sugs.map((s, idx) => {
          const sc = Number(s.score_sugestao) || 0;
          const stColor = SUG_STATUS_COLORS[s.portal_status || ''] || 'muted';
          const stLabel = SUG_STATUS_LABELS[s.portal_status || ''] || s.portal_status || 'Pendente';
          return `<tr>
            <td><strong>${idx + 1}</strong></td>
            <td><strong>${esc(s.sugestao_nome || '—')}</strong></td>
            <td style="font-size:11px;color:var(--color-text-muted);">${esc(s.epi_referencia || '—')}</td>
            <td><strong style="color:${sc >= 0 ? 'var(--success)' : 'var(--danger)'}">${sc > 0 ? '+' : ''}${sc}</strong></td>
            <td style="color:var(--success);font-weight:600;">${s.rank_excelente_sug || 0}</td>
            <td style="color:var(--success);">${s.rank_otima_sug || 0}</td>
            <td style="color:var(--success);">${s.rank_muito_boa_sug || 0}</td>
            <td style="color:var(--danger);font-weight:600;">${s.rank_pessima_sug || 0}</td>
            <td style="color:var(--danger);">${s.rank_muito_ruim_sug || 0}</td>
            <td style="color:var(--pending);">${s.rank_ruim_sug || 0}</td>
            <td>${s.total_avaliacoes}</td>
            <td><span style="background:var(--${stColor}-soft);color:var(--${stColor});font-size:11px;padding:2px 7px;border-radius:99px;">${esc(stLabel)}</span></td>
          </tr>`;
        }).join('') : '<tr><td colspan="12" style="text-align:center;opacity:.6;">Sem sugestões avaliadas ainda.</td></tr>';
      }
    } catch (e) {
      if (tbody) tbody.innerHTML = `<tr><td colspan="13" style="text-align:center;color:var(--danger);">${esc(e.message || 'Erro ao carregar ranking.')}</td></tr>`;
    }
  }

  async function loadSummary() {
    try {
      const data = await api('/api/avaliacoes/summary');
      _summaryData = data;
      updateSummaryCards(data);
      renderPendentes(data.items || []);
      renderReclamacoes(data);
      renderElogios(data.elogio_items || []);
      renderSugestoes(data.sugestao_items || []);
    } catch (e) {
      showToast(e.message || 'Erro ao carregar avaliações.', 'error');
    }
  }

  function showAvalTab(tabName) {
    const role = state.user?.role || '';
    const isAdmin = role === 'general_admin' || role === 'registry_admin';
    // Admins não usam o pane "Pendentes" — é redirecionado para a visão unificada
    const effectiveTab = (isAdmin && tabName === 'pendentes') ? 'avaliacao-final' : tabName;
    const panes = ['pendentes', 'reclamacoes', 'elogios', 'sugestoes', 'ranking', 'epis-teste', 'avaliacao-final'];
    panes.forEach((p) => {
      const pane = document.getElementById(`avaliacoes-pane-${p}`);
      if (pane) pane.style.display = p === effectiveTab ? '' : 'none';
      const btn = document.getElementById(`avaltab-${p}`);
      if (btn) btn.classList.toggle('is-active', p === effectiveTab);
    });
    if (effectiveTab === 'epis-teste') globalThis.loadPpeTests?.();
    if (effectiveTab === 'ranking') renderRanking();
    if (effectiveTab === 'avaliacao-final') {
      loadSummary().catch(() => {});
      loadEpiFeedbacks().catch(() => {});
    }
  }

  function openModal(action, feedbackId, allItems) {
    const modal = document.getElementById('aval-action-modal');
    if (!modal) return;
    const fb = allItems.find((i) => String(i.id) === String(feedbackId)) || {};
    document.getElementById('aval-modal-feedback-id').value = feedbackId;
    document.getElementById('aval-modal-action').value = action;
    document.getElementById('aval-modal-notes').value = '';
    const setDisplay = (id, show) => { const el = document.getElementById(id); if (el) el.style.display = show ? '' : 'none'; };
    setDisplay('aval-modal-validate-fields', action === 'validate');
    setDisplay('aval-modal-reject-fields', action === 'reject');
    setDisplay('aval-modal-reassessment-fields', action === 'reassessment');
    setDisplay('aval-modal-accept-suggestion-fields', action === 'accept_suggestion');
    setDisplay('aval-modal-admin-eval-fields', action === 'admin_evaluate' || action === 'pre_evaluate');
    if (action === 'admin_evaluate' || action === 'pre_evaluate') {
      document.querySelectorAll('.aval-problema').forEach((cb) => { cb.checked = false; });
      const techEl = document.getElementById('aval-modal-tech-decision');
      const labelEl = document.getElementById('aval-tech-decision-label-text');
      if (action === 'pre_evaluate') {
        if (labelEl) labelEl.textContent = 'Recomendação Prévia (não vinculante)';
        if (techEl) {
          techEl.innerHTML = '<option value="recomenda_aceitar">👍 Recomenda Aceitar</option><option value="recomenda_recusar">👎 Recomenda Recusar</option><option value="aguardar_info">⏳ Aguardar mais informações</option>';
          techEl.value = 'recomenda_aceitar';
        }
      } else {
        if (labelEl) labelEl.textContent = 'Decisão Final';
        if (techEl) {
          techEl.innerHTML = '<option value="aceito">✓ Aceitar</option><option value="recusado">✗ Recusar</option>';
          techEl.value = 'aceito';
        }
      }
      ['aval-modal-atende-nr', 'aval-modal-reduz-risco', 'aval-modal-durabilidade', 'aval-modal-disponibilidade'].forEach((id) => {
        const el = document.getElementById(id); if (el) el.value = '';
      });
      ['aval-modal-custo', 'aval-modal-tech-notes', 'aval-modal-marca-modelo'].forEach((id) => {
        const el = document.getElementById(id); if (el) el.value = '';
      });
    }
    const titleMap = { validate: 'Validar Avaliação', reject: 'Rejeitar Avaliação', reassessment: 'Definir Período de Reavaliação', accept_suggestion: 'Aceitar Sugestão de EPI', pre_evaluate: '📋 Avaliação Prévia Técnica', admin_evaluate: '✅ Avaliação Final — Admin Geral' };
    const titleEl = document.getElementById('aval-modal-title');
    if (titleEl) titleEl.textContent = titleMap[action] || 'Ação';
    if (action === 'validate') {
      const subtypeEl = document.getElementById('aval-modal-subtype');
      if (subtypeEl) subtypeEl.value = fb.feedback_subtype || fb.type || 'reclamacao';
      const riskEl = document.getElementById('aval-modal-risk');
      if (riskEl) riskEl.value = fb.risk_level || 'nenhum';
      const rankField = document.getElementById('aval-modal-rank-field');
      const rankSelect = document.getElementById('aval-modal-epi-rank');
      const RANK_OPTIONS = {
        elogio: [['excelente', 'Excelente'], ['otimo', 'Ótimo'], ['muito_bom', 'Muito Bom']],
        reclamacao: [['pessimo', 'Péssimo'], ['muito_ruim', 'Muito Ruim'], ['ruim', 'Ruim']],
        sugestao_nova: [
          ['excelente_sug', 'Excelente Sugestão'],
          ['otima_sug', 'Ótima Sugestão'],
          ['muito_boa_sug', 'Muito Boa Sugestão'],
          ['pessima_sug', 'Péssima Sugestão'],
          ['muito_ruim_sug', 'Muito Ruim a Sugestão'],
          ['ruim_sug', 'Ruim a Sugestão'],
        ],
      };
      function updateRankOptions(subtype) {
        const opts = RANK_OPTIONS[subtype];
        if (rankSelect) {
          rankSelect.innerHTML = '<option value="">Selecione</option>' +
            (opts ? opts.map(([v, l]) => `<option value="${v}">${l}</option>`).join('') : '');
        }
        if (rankField) rankField.style.display = opts ? '' : 'none';
      }
      updateRankOptions(subtypeEl?.value || 'reclamacao');
      if (subtypeEl) subtypeEl.onchange = () => updateRankOptions(subtypeEl.value);
    }
    modal.style.display = 'flex';
  }

  function closeModal() {
    const modal = document.getElementById('aval-action-modal');
    if (modal) modal.style.display = 'none';
  }

  async function confirmModal() {
    const feedbackId = document.getElementById('aval-modal-feedback-id')?.value;
    const action = document.getElementById('aval-modal-action')?.value;
    const notes = document.getElementById('aval-modal-notes')?.value?.trim() || '';
    if (!feedbackId || !action) return;
    try {
      if (action === 'validate') {
        const subtype = document.getElementById('aval-modal-subtype')?.value || 'reclamacao';
        const epiRank = (subtype === 'elogio' || subtype === 'reclamacao' || subtype === 'sugestao_nova') ? (document.getElementById('aval-modal-epi-rank')?.value || '') : '';
        await api('/api/feedbacks/manager-validate', {
          method: 'POST',
          body: JSON.stringify({
            actor_user_id: state.user?.id,
            feedback_id: feedbackId,
            feedback_subtype: subtype,
            risk_level: document.getElementById('aval-modal-risk')?.value || 'nenhum',
            epi_rank: epiRank,
            notes,
          }),
        });
        showToast('Avaliação validada e encaminhada ao administrador.');
      } else if (action === 'reject') {
        const rejReason = document.getElementById('aval-modal-rejection-reason')?.value || 'outro';
        const supplierEval = document.getElementById('aval-modal-supplier-eval')?.checked || false;
        await api('/api/feedbacks/manager-reject', {
          method: 'POST',
          body: JSON.stringify({ actor_user_id: state.user?.id, feedback_id: feedbackId, rejection_reason: rejReason, supplier_eval_requested: supplierEval, notes }),
        });
        showToast('Avaliação rejeitada.');
      } else if (action === 'reassessment') {
        const period = document.getElementById('aval-modal-period')?.value || '3_meses';
        await api('/api/avaliacoes/set-reassessment', {
          method: 'POST',
          body: JSON.stringify({ actor_user_id: state.user?.id, feedback_id: feedbackId, period, notes }),
        });
        showToast('Período de reavaliação definido.');
      } else if (action === 'accept_suggestion') {
        await api('/api/avaliacoes/accept-suggestion', {
          method: 'POST',
          body: JSON.stringify({ actor_user_id: state.user?.id, feedback_id: feedbackId, notes }),
        });
        showToast('Sugestão aceita — encaminhada ao fluxo de Novos EPIs em Teste.');
      } else if (action === 'pre_evaluate') {
        const preRec = document.getElementById('aval-modal-tech-decision')?.value || 'recomenda_aceitar';
        const atendeNr = document.getElementById('aval-modal-atende-nr')?.value || '';
        const reduzRisco = document.getElementById('aval-modal-reduz-risco')?.value || '';
        const problemas = Array.from(document.querySelectorAll('.aval-problema:checked')).map((cb) => cb.value);
        const custoEstimado = document.getElementById('aval-modal-custo')?.value?.trim() || '';
        const durabilidade = document.getElementById('aval-modal-durabilidade')?.value || '';
        const disponibilidade = document.getElementById('aval-modal-disponibilidade')?.value || '';
        const techNotes = document.getElementById('aval-modal-tech-notes')?.value?.trim() || '';
        const marcaModelo = document.getElementById('aval-modal-marca-modelo')?.value?.trim() || '';
        await api('/api/avaliacoes/pre-evaluate', {
          method: 'POST',
          body: JSON.stringify({
            actor_user_id: state.user?.id, feedback_id: feedbackId,
            pre_recommendation: preRec, atende_nr: atendeNr, reduz_risco: reduzRisco,
            problemas_observados: problemas, custo_estimado: custoEstimado,
            durabilidade_esperada: durabilidade, disponibilidade_mercado: disponibilidade,
            admin_tech_notes: techNotes, marca_modelo_sugerido: marcaModelo, notes,
          }),
        });
        showToast('Avaliação prévia registrada. Aguardando decisão final do Administrador Geral.');
      } else if (action === 'admin_evaluate') {
        const techDecision = document.getElementById('aval-modal-tech-decision')?.value || 'aceito';
        const atendeNr = document.getElementById('aval-modal-atende-nr')?.value || '';
        const reduzRisco = document.getElementById('aval-modal-reduz-risco')?.value || '';
        const problemas = Array.from(document.querySelectorAll('.aval-problema:checked')).map((cb) => cb.value);
        const custoEstimado = document.getElementById('aval-modal-custo')?.value?.trim() || '';
        const durabilidade = document.getElementById('aval-modal-durabilidade')?.value || '';
        const disponibilidade = document.getElementById('aval-modal-disponibilidade')?.value || '';
        const techNotes = document.getElementById('aval-modal-tech-notes')?.value?.trim() || '';
        const marcaModelo = document.getElementById('aval-modal-marca-modelo')?.value?.trim() || '';
        await api('/api/avaliacoes/admin-evaluate', {
          method: 'POST',
          body: JSON.stringify({
            actor_user_id: state.user?.id, feedback_id: feedbackId,
            tech_decision: techDecision, atende_nr: atendeNr, reduz_risco: reduzRisco,
            problemas_observados: problemas, custo_estimado: custoEstimado,
            durabilidade_esperada: durabilidade, disponibilidade_mercado: disponibilidade,
            admin_tech_notes: techNotes, marca_modelo_sugerido: marcaModelo, notes,
          }),
        });
        showToast(techDecision === 'aceito' ? 'EPI aceito após avaliação final.' : 'EPI recusado após avaliação final.');
      }
      closeModal();
      await loadSummary();
    } catch (e) {
      showToast(e.message || 'Erro ao executar ação.', 'error');
    }
  }

  async function computeStatus() {
    const btn = document.getElementById('aval-compute-btn');
    if (btn) { btn.disabled = true; btn.textContent = 'Computando...'; }
    try {
      const result = await api('/api/avaliacoes/compute-status', {
        method: 'POST',
        body: JSON.stringify({ actor_user_id: state.user?.id }),
      });
      const count = (result.items || []).length;
      showToast(`Status computado para ${count} EPI(s).`);
      await loadSummary();
    } catch (e) {
      showToast(e.message || 'Erro ao computar status.', 'error');
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = '⚙ Computar Status EPIs'; }
    }
  }

  function bindAvaliacoesView() {
    bindAppListener(document.getElementById('avaliacoes-subtabs'), 'click', (e) => {
      const btn = e.target.closest('[data-avaliacoes-tab]');
      if (btn) showAvalTab(btn.dataset.avaliacoesTab);
    });
    bindAppListener(document.getElementById('aval-reload-btn'), 'click', loadSummary);
    bindAppListener(document.getElementById('aval-unified-reload-btn'), 'click', () => { loadSummary().catch(() => {}); loadEpiFeedbacks().catch(() => {}); });
    bindAppListener(document.getElementById('aval-compute-btn'), 'click', computeStatus);
    bindAppListener(document.getElementById('aval-modal-cancel'), 'click', closeModal);
    bindAppListener(document.getElementById('aval-modal-confirm'), 'click', confirmModal);
    bindAppListener(document.getElementById('aval-action-modal'), 'click', (e) => {
      if (e.target === document.getElementById('aval-action-modal')) closeModal();
    });
  }

  bindAppListener(document, 'epi:viewchange', (e) => {
    if (e.detail?.view === 'avaliacoes') {
      const role = state.user?.role || '';
      const isAdmin = role === 'general_admin' || role === 'registry_admin';
      const avalFinalBtn = document.getElementById('avaltab-avaliacao-final');
      if (avalFinalBtn) avalFinalBtn.style.display = hasPermission('epi_feedback:view') ? '' : 'none';
      const episTesteBtn = document.getElementById('avaltab-epis-teste');
      if (episTesteBtn) episTesteBtn.style.display = hasPermission('ppe_test:view') ? '' : 'none';
      const pendentesBtn = document.getElementById('avaltab-pendentes');
      if (pendentesBtn) pendentesBtn.style.display = isAdmin ? 'none' : '';
      if (isAdmin) {
        // Admins: visão unificada (loadSummary + loadEpiFeedbacks via showAvalTab)
        showAvalTab('avaliacao-final');
      } else {
        // Gestor/outros: carregar resumo e mostrar pendentes
        loadSummary();
        showAvalTab('pendentes');
      }
    }
  });

  bindAvaliacoesView();
}());

// ── Novos EPIs em Teste (fluxo separado — produto ainda não homologado) ───────
(function initPpeTestsModule() {
  const STATUS_LABELS = {
    rascunho: 'Rascunho', em_triagem: 'Em Triagem', em_analise_tecnica: 'Em Análise Técnica',
    aprovado_para_teste: 'Aprovado para Teste', em_teste: 'Em Teste', teste_suspenso: 'Teste Suspenso',
    teste_concluido: 'Teste Concluído', em_decisao: 'Em Decisão', aprovado: 'Aprovado',
    reprovado: 'Reprovado', homologado: 'Homologado', arquivado: 'Arquivado',
  };
  const STATUS_COLORS = {
    em_teste: 'info', teste_suspenso: 'warning', teste_concluido: 'accent', em_decisao: 'pending',
    aprovado: 'success', homologado: 'success', reprovado: 'danger', arquivado: 'muted',
    aprovado_para_teste: 'accent',
  };
  const SUG_STATUS_LABELS = {
    recebida: 'Recebida', em_triagem: 'Em Triagem', aprovada_para_analise: 'Aprovada p/ Análise',
    info_solicitada: 'Mais Informações', duplicada: 'Duplicada', inviavel: 'Inviável',
    rejeitada: 'Rejeitada', convertida: 'Convertida',
  };
  const SOURCE_LABELS = {
    colaborador: 'Sugestão de colaborador', empresa: 'Proposta da empresa',
    representante: 'Representante responsável', seguranca_trabalho: 'Segurança do Trabalho',
    fornecedor: 'Fornecedor', gestor_unidade: 'Gestor da unidade',
    comissao_interna: 'Comissão interna', joint_venture: 'Joint Venture', outro: 'Outro',
  };
  const STAGE_LABELS = { inicial: 'Inicial', intermediaria: 'Intermediária', final: 'Final' };
  const SCALE_OPTIONS = [
    { value: '', label: '—' },
    { value: '1', label: '1 — Muito ruim' }, { value: '2', label: '2 — Ruim' },
    { value: '3', label: '3 — Regular' }, { value: '4', label: '4 — Bom' },
    { value: '5', label: '5 — Excelente' },
  ];

  let _suggestions = [];
  let _tests = [];
  let _detail = null;
  let _formSubmit = null;

  function statusChip(status, labels = STATUS_LABELS, colors = STATUS_COLORS) {
    const label = labels[status] || status || '—';
    const color = colors[status] || '';
    return color
      ? `<span class="status-chip" style="background:var(--${color}-soft,rgba(120,120,120,.12));color:var(--${color},inherit);font-size:11px;">${esc(label)}</span>`
      : `<span class="status-chip" style="font-size:11px;">${esc(label)}</span>`;
  }

  function fmtDate(value) {
    const raw = String(value || '');
    if (!raw) return '—';
    return raw.slice(0, 10).split('-').reverse().join('/');
  }

  // ── Modal genérico de formulário ────────────────────────────────────────────
  function openForm(title, fields, onSubmit) {
    const modal = document.getElementById('ppe-form-modal');
    const holder = document.getElementById('ppe-form-fields');
    if (!modal || !holder) return;
    document.getElementById('ppe-form-title').textContent = title;
    holder.innerHTML = fields.map((f) => {
      const req = f.required ? ' <span style="color:var(--danger);">*</span>' : '';
      if (f.type === 'section') {
        return `<h4 style="margin:14px 0 6px;border-bottom:1px solid var(--color-border,#e5e7eb);padding-bottom:4px;">${esc(f.label)}</h4>`;
      }
      if (f.type === 'select') {
        const opts = (f.options || []).map((o) => `<option value="${esc(o.value)}"${String(o.value) === String(f.value ?? '') ? ' selected' : ''}>${esc(o.label)}</option>`).join('');
        return `<label style="display:block;margin-bottom:10px;font-size:13px;">${esc(f.label)}${req}<select data-ppe-field="${esc(f.name)}" style="width:100%;margin-top:4px;">${opts}</select></label>`;
      }
      if (f.type === 'textarea') {
        return `<label style="display:block;margin-bottom:10px;font-size:13px;">${esc(f.label)}${req}<textarea data-ppe-field="${esc(f.name)}" rows="3" style="width:100%;margin-top:4px;">${esc(f.value || '')}</textarea></label>`;
      }
      if (f.type === 'checkbox') {
        return `<label style="display:flex;gap:8px;align-items:center;margin-bottom:10px;font-size:13px;"><input type="checkbox" data-ppe-field="${esc(f.name)}"${f.value ? ' checked' : ''}> ${esc(f.label)}</label>`;
      }
      const type = f.type === 'number' ? 'number' : f.type === 'date' ? 'date' : 'text';
      return `<label style="display:block;margin-bottom:10px;font-size:13px;">${esc(f.label)}${req}<input type="${type}" data-ppe-field="${esc(f.name)}" value="${esc(f.value ?? '')}" style="width:100%;margin-top:4px;"></label>`;
    }).join('');
    _formSubmit = async () => {
      const values = {};
      holder.querySelectorAll('[data-ppe-field]').forEach((el) => {
        const name = el.dataset.ppeField;
        values[name] = el.type === 'checkbox' ? el.checked : el.value.trim();
      });
      for (const f of fields) {
        if (f.required && !values[f.name]) {
          showToast(`Campo obrigatório: ${f.label}`, 'error');
          return;
        }
      }
      await onSubmit(values);
    };
    modal.style.display = 'flex';
  }

  function closeForm() {
    const modal = document.getElementById('ppe-form-modal');
    if (modal) modal.style.display = 'none';
    _formSubmit = null;
  }

  async function submitForm() {
    if (!_formSubmit) return;
    const btn = document.getElementById('ppe-form-confirm');
    if (btn) btn.disabled = true;
    try {
      await _formSubmit();
      closeForm();
    } catch (e) {
      showToast(e.message || 'Erro ao executar ação.', 'error');
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  function post(path, body) {
    return api(path, {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user?.id, ...body }),
    });
  }

  // ── Listas ──────────────────────────────────────────────────────────────────
  async function loadPpeTests() {
    const canManage = hasPermission('ppe_test:manage');
    const canSuggest = hasPermission('ppe_test:suggest');
    const sugBtn = document.getElementById('ppe-new-suggestion-btn');
    if (sugBtn) sugBtn.style.display = canSuggest ? '' : 'none';
    const candBtn = document.getElementById('ppe-new-candidate-btn');
    if (candBtn) candBtn.style.display = canManage ? '' : 'none';
    try {
      const [sugData, testData] = await Promise.all([
        api('/api/ppe-test-suggestions'),
        api('/api/ppe-tests'),
      ]);
      _suggestions = sugData.items || [];
      _tests = testData.items || [];
      renderSummary();
      renderSuggestions();
      renderTests();
    } catch (e) {
      showToast(e.message || 'Erro ao carregar EPIs em teste.', 'error');
    }
  }

  function renderSummary() {
    const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = String(v); };
    set('ppe-count-sugestoes', _suggestions.filter((s) => !['convertida', 'rejeitada', 'inviavel', 'duplicada'].includes(s.status)).length);
    set('ppe-count-andamento', _tests.filter((t) => ['em_teste', 'teste_suspenso'].includes(t.status)).length);
    set('ppe-count-decisao', _tests.filter((t) => ['teste_concluido', 'em_decisao', 'aprovado'].includes(t.status)).length);
    set('ppe-count-homologados', _tests.filter((t) => t.status === 'homologado').length);
    set('ppe-count-reprovados', _tests.filter((t) => t.status === 'reprovado').length);
  }

  function renderSuggestions() {
    const tbody = document.getElementById('ppe-suggestions-tbody');
    if (!tbody) return;
    const canTriage = hasPermission('ppe_test:triage');
    const canManage = hasPermission('ppe_test:manage');
    tbody.innerHTML = _suggestions.length ? _suggestions.map((s) => {
      const actions = [];
      if (canTriage && ['recebida', 'em_triagem', 'info_solicitada'].includes(s.status)) {
        actions.push(`<button class="btn ghost" data-ppe-sug-triage="${s.id}" style="font-size:11px;">Triagem</button>`);
      }
      if (canManage && s.status === 'aprovada_para_analise') {
        actions.push(`<button class="btn" data-ppe-sug-convert="${s.id}" style="font-size:11px;">Criar Cadastro</button>`);
      }
      return `<tr>
        <td><strong>${esc(s.suggested_name || '—')}</strong></td>
        <td>${esc(SOURCE_LABELS[s.source_type] || s.source_type || '—')}</td>
        <td>${esc(s.requester_name || s.employee_name || '—')}</td>
        <td>${esc(s.unit_name || '—')}</td>
        <td style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${esc(s.reason || '')}">${esc(s.reason || '—')}</td>
        <td>${statusChip(s.status, SUG_STATUS_LABELS, { aprovada_para_analise: 'accent', convertida: 'success', rejeitada: 'danger', inviavel: 'danger', duplicada: 'warning', info_solicitada: 'warning' })}</td>
        <td style="display:flex;gap:4px;flex-wrap:wrap;">${actions.join('') || '—'}</td>
      </tr>`;
    }).join('') : '<tr><td colspan="7" style="text-align:center;opacity:.6;">Nenhuma sugestão de novo EPI registrada.</td></tr>';
  }

  function renderTests() {
    const tbody = document.getElementById('ppe-tests-tbody');
    if (!tbody) return;
    tbody.innerHTML = _tests.length ? _tests.map((t) => {
      const period = t.plan_start_date ? `${fmtDate(t.plan_start_date)} → ${fmtDate(t.plan_end_date)}` : '—';
      const incidents = Number(t.open_incidents_count || 0);
      return `<tr>
        <td><strong>${esc(t.name)}</strong>${t.approved_epi_id ? ` <span style="font-size:10px;color:var(--success);">→ EPI oficial #${esc(t.approved_epi_id)}</span>` : ''}</td>
        <td>${esc(t.ca || '—')}</td>
        <td style="font-size:12px;">${period}</td>
        <td>${Number(t.participants_count || 0)}</td>
        <td>${Number(t.evaluations_count || 0)}</td>
        <td>${incidents ? `<span style="color:var(--danger);font-weight:600;">${incidents}</span>` : '0'}</td>
        <td>${statusChip(t.status)}</td>
        <td><button class="btn ghost" data-ppe-test-open="${t.id}" style="font-size:11px;">Abrir</button></td>
      </tr>`;
    }).join('') : '<tr><td colspan="8" style="text-align:center;opacity:.6;">Nenhum EPI em teste. Crie a partir de uma sugestão aprovada ou de um cadastro provisório.</td></tr>';
  }

  // ── Ações de sugestão ───────────────────────────────────────────────────────
  function openNewSuggestion() {
    openForm('Nova Sugestão de EPI em Teste', [
      { name: 'suggested_name', label: 'Nome do EPI sugerido', required: true },
      {
        name: 'source_type', label: 'Origem', type: 'select', value: 'colaborador',
        options: Object.entries(SOURCE_LABELS).map(([value, label]) => ({ value, label })),
      },
      { name: 'requester_name', label: 'Nome do solicitante', required: true, value: state.user?.full_name || '' },
      {
        name: 'unit_id', label: 'Unidade', type: 'select',
        options: [{ value: '', label: '—' }].concat((state.units || []).map((u) => ({ value: u.id, label: u.name }))),
      },
      {
        name: 'employee_id', label: 'Colaborador (quando origem = colaborador)', type: 'select',
        options: [{ value: '', label: '—' }].concat((state.employees || []).map((e) => ({ value: e.id, label: e.name }))),
      },
      {
        name: 'current_epi_id', label: 'EPI atual utilizado', type: 'select',
        options: [{ value: '', label: '—' }].concat((state.epis || []).map((e) => ({ value: e.id, label: e.name }))),
      },
      { name: 'reason', label: 'Motivo', type: 'textarea', required: true },
      { name: 'problem_identified', label: 'Problema identificado', type: 'textarea' },
      { name: 'expected_benefit', label: 'Benefício esperado', type: 'textarea' },
      { name: 'related_activity', label: 'Função ou atividade relacionada' },
      { name: 'risks', label: 'Riscos que pretende controlar' },
      { name: 'current_epi_issue', label: 'Dificuldade encontrada no EPI atual', type: 'textarea' },
      { name: 'notes', label: 'Observações', type: 'textarea' },
    ], async (values) => {
      await post('/api/ppe-test-suggestions', values);
      showToast('Sugestão registrada. Ela seguirá para triagem.');
      await loadPpeTests();
    });
  }

  function openTriage(suggestionId) {
    openForm('Triagem Inicial da Sugestão', [
      {
        name: 'result', label: 'Resultado da triagem', type: 'select', required: true,
        options: [
          { value: 'aprovado_analise_tecnica', label: 'Aprovado para análise técnica' },
          { value: 'solicitar_informacoes', label: 'Solicitar mais informações' },
          { value: 'duplicado', label: 'Duplicado' },
          { value: 'inviavel', label: 'Inviável para teste' },
          { value: 'rejeitado', label: 'Rejeitado na triagem' },
        ],
      },
      { name: 'ck_banco', label: 'Verificado: EPI não existe no banco aprovado', type: 'checkbox' },
      { name: 'ck_teste', label: 'Verificado: não há teste semelhante em andamento', type: 'checkbox' },
      { name: 'ck_ca', label: 'Verificado: CA válido (quando aplicável)', type: 'checkbox' },
      { name: 'ck_risco', label: 'Verificado: produto atende ao risco', type: 'checkbox' },
      { name: 'ck_fornecedor', label: 'Verificado: fornecedor regular', type: 'checkbox' },
      { name: 'ck_orcamento', label: 'Verificado: há orçamento e unidade para o piloto', type: 'checkbox' },
      { name: 'notes', label: 'Justificativa / observações (obrigatória para rejeição)', type: 'textarea' },
    ], async (values) => {
      const checklist = {};
      Object.keys(values).filter((k) => k.startsWith('ck_')).forEach((k) => { checklist[k.slice(3)] = !!values[k]; });
      await post(`/api/ppe-test-suggestions/${suggestionId}/triage`, {
        result: values.result, notes: values.notes, checklist,
      });
      showToast('Triagem registrada.');
      await loadPpeTests();
    });
  }

  function openNewCandidate(suggestionId = null) {
    const sug = suggestionId ? _suggestions.find((s) => String(s.id) === String(suggestionId)) : null;
    openForm('Cadastro Provisório do EPI em Teste', [
      { name: 'name', label: 'Nome provisório', required: true, value: sug?.suggested_name || '' },
      { name: 'category', label: 'Categoria / setor' },
      { name: 'protection_type', label: 'Tipo de proteção' },
      { name: 'manufacturer', label: 'Fabricante' },
      { name: 'model_reference', label: 'Modelo' },
      { name: 'supplier', label: 'Fornecedor' },
      { name: 'ca', label: 'CA' },
      { name: 'ca_expiry', label: 'Validade do CA', type: 'date' },
      { name: 'size', label: 'Tamanho' },
      { name: 'material', label: 'Material' },
      { name: 'test_batch', label: 'Lote de teste' },
      { name: 'quantity_available', label: 'Quantidade disponível para o teste', type: 'number', value: '0' },
      { name: 'estimated_value', label: 'Valor estimado' },
      { name: 'test_cost', label: 'Custo do teste' },
      { name: 'risks_covered', label: 'Riscos atendidos', type: 'textarea' },
      { name: 'activities', label: 'Atividades indicadas' },
      { name: 'restrictions', label: 'Restrições' },
      { name: 'notes', label: 'Observações', type: 'textarea' },
    ], async (values) => {
      await post('/api/ppe-tests', { ...values, suggestion_id: suggestionId || undefined });
      showToast('Cadastro provisório criado — fora do banco oficial de EPIs.');
      await loadPpeTests();
    });
  }

  // ── Detalhe do teste ────────────────────────────────────────────────────────
  async function openDetail(testId) {
    try {
      const data = await api(`/api/ppe-tests/${testId}`);
      _detail = data.item;
      renderDetail();
      const list = document.getElementById('ppe-test-list-area');
      if (list) list.style.display = 'none';
      const panel = document.getElementById('ppe-test-detail');
      if (panel) panel.style.display = '';
    } catch (e) {
      showToast(e.message || 'Erro ao abrir teste.', 'error');
    }
  }

  function closeDetail() {
    _detail = null;
    const list = document.getElementById('ppe-test-list-area');
    if (list) list.style.display = '';
    const panel = document.getElementById('ppe-test-detail');
    if (panel) panel.style.display = 'none';
  }

  function detailActionButtons(t) {
    const canManage = hasPermission('ppe_test:manage');
    const canTech = hasPermission('ppe_test:tech_review');
    const canEval = hasPermission('ppe_test:evaluate');
    const canDecide = hasPermission('ppe_test:decide');
    const canHomologate = hasPermission('ppe_test:homologate');
    const b = [];
    const add = (action, label, kind = 'ghost') => b.push(`<button class="btn ${kind}" data-ppe-action="${action}" style="font-size:12px;">${label}</button>`);
    switch (t.status) {
      case 'em_analise_tecnica':
        if (canTech) add('tech-review', '🔬 Análise Técnica', '');
        if (canManage) add('plan', '📋 Plano de Teste');
        break;
      case 'aprovado_para_teste':
        if (canManage) {
          add('plan', '📋 Plano de Teste');
          add('participant', '+ Participante');
          add('receive', '📦 Receber Lote');
          add('start', '▶ Iniciar Teste', '');
        }
        break;
      case 'em_teste':
        if (canManage) {
          add('participant', '+ Participante');
          add('deliver', '🤝 Entregar a Participante');
        }
        if (canEval) {
          add('evaluate', '⭐ Registrar Avaliação', '');
          add('incident', '⚠ Registrar Ocorrência');
        }
        if (canManage) {
          add('suspend', '⏸ Suspender');
          add('complete', '✔ Concluir Teste');
        }
        break;
      case 'teste_suspenso':
        if (canEval) add('incident', '⚠ Registrar Ocorrência');
        if (canManage) {
          add('resume', '▶ Retomar', '');
          add('complete', '✔ Concluir Teste');
        }
        break;
      case 'teste_concluido':
      case 'em_decisao':
        if (canDecide) {
          add('decision', '⚖ Decisão Formal', '');
          add('reject', '✖ Reprovar');
        }
        break;
      case 'aprovado':
        if (canHomologate) add('homologate', '🏛 Homologar e Definir Escopo', '');
        if (canDecide) add('reject', '✖ Reprovar');
        break;
      default:
        break;
    }
    return b.join('');
  }

  function renderDetail() {
    const t = _detail;
    if (!t) return;
    document.getElementById('ppe-detail-title').textContent = `🧪 ${t.name}`;
    document.getElementById('ppe-detail-status-chip').innerHTML = statusChip(t.status);
    const banner = document.getElementById('ppe-detail-banner');
    if (banner) banner.style.display = ['homologado', 'arquivado'].includes(t.status) ? 'none' : '';
    const res = t.results || {};
    const progress = [];
    if (res.days_elapsed != null) progress.push(`<strong>${res.days_elapsed}</strong> dias decorridos`);
    if (res.days_remaining != null) progress.push(`<strong>${res.days_remaining}</strong> dias restantes`);
    progress.push(`<strong>${res.participants_active ?? 0}</strong>/${res.participants_total ?? 0} participantes ativos`);
    progress.push(`<strong>${(res.evaluations_by_stage || {}).final || 0}</strong> avaliações finais (${res.final_response_rate ?? 0}%)`);
    if (res.incidents_open) progress.push(`<strong style="color:var(--danger);">${res.incidents_open}</strong> ocorrências abertas`);
    document.getElementById('ppe-detail-progress').innerHTML = progress.join(' · ');
    document.getElementById('ppe-detail-actions').innerHTML = detailActionButtons(t);

    const plan = t.plan;
    const sections = [];
    sections.push(`<h4 style="margin:12px 0 6px;">Resumo do Cadastro Provisório</h4>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:6px;">
        <div><strong>CA:</strong> ${esc(t.ca || '—')} ${t.ca_expiry ? `(val. ${fmtDate(t.ca_expiry)})` : ''}</div>
        <div><strong>Fabricante:</strong> ${esc(t.manufacturer || '—')}</div>
        <div><strong>Fornecedor:</strong> ${esc(t.supplier || '—')}</div>
        <div><strong>Lote de teste:</strong> ${esc(t.test_batch || '—')} (${Number(t.quantity_available || 0)} ${esc(t.unit_measure || 'un')})</div>
        <div><strong>Categoria:</strong> ${esc(t.category || '—')}</div>
        <div><strong>Riscos atendidos:</strong> ${esc(t.risks_covered || '—')}</div>
      </div>`);
    if (plan) {
      sections.push(`<h4 style="margin:14px 0 6px;">Plano de Teste</h4>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:6px;">
          <div><strong>Período:</strong> ${fmtDate(plan.start_date)} → ${fmtDate(plan.end_date)} (${plan.duration_days} dias)</div>
          <div><strong>Meta:</strong> ${plan.participants_target} participantes / ${plan.epis_quantity} EPIs</div>
          <div><strong>Mínimos:</strong> ${plan.min_participants} participantes, ${plan.min_response_rate}% respostas</div>
          <div><strong>Resp. técnico:</strong> ${esc(plan.technical_manager || '—')}</div>
          <div><strong>Resp. operacional:</strong> ${esc(plan.operational_manager || '—')}</div>
          <div><strong>Objetivo:</strong> ${esc(plan.objective || '—')}</div>
        </div>`);
    }
    const participants = t.participants || [];
    sections.push(`<h4 style="margin:14px 0 6px;">Participantes (${participants.length})</h4>
      ${participants.length ? `<div class="table-wrap"><table>
        <thead><tr><th>Colaborador</th><th>Unidade</th><th>Tamanho</th><th>Entrega</th><th>Status</th></tr></thead>
        <tbody>${participants.map((p) => `<tr>
          <td>${esc(p.employee_name || p.employee_id)}</td>
          <td>${esc(p.unit_name || '—')}</td>
          <td>${esc(p.size || '—')}</td>
          <td>${fmtDate(p.delivered_at)}</td>
          <td>${statusChip(p.status, { convidado: 'Convidado', confirmado: 'Confirmado', em_teste: 'Em Teste', afastado: 'Afastado', substituido: 'Substituído', desistente: 'Desistente', concluido: 'Concluído' }, { em_teste: 'info', concluido: 'success', desistente: 'danger', afastado: 'warning' })}</td>
        </tr>`).join('')}</tbody></table></div>` : '<p style="opacity:.6;">Nenhum participante selecionado.</p>'}`);
    const distributions = t.distributions || [];
    const bal = res.distribution || {};
    sections.push(`<h4 style="margin:14px 0 6px;">Distribuição Controlada</h4>
      <p style="margin:0 0 6px;">Recebido: <strong>${bal.recebido ?? 0}</strong> · Entregue: <strong>${bal.entregue ?? 0}</strong> · Devolvido: <strong>${bal.devolvido ?? 0}</strong> · Descartado: <strong>${bal.descartado ?? 0}</strong> · Saldo: <strong>${bal.saldo ?? 0}</strong></p>
      ${distributions.length ? `<div class="table-wrap"><table>
        <thead><tr><th>Data</th><th>Movimento</th><th>Qtd</th><th>Lote</th><th>Responsável</th><th>Obs.</th></tr></thead>
        <tbody>${distributions.map((d) => `<tr>
          <td>${fmtDate(d.created_at)}</td><td>${esc(d.movement_type)}</td><td>${d.quantity}</td>
          <td>${esc(d.batch || '—')}</td><td>${esc(d.responsible_name || '—')}</td><td>${esc(d.notes || '—')}</td>
        </tr>`).join('')}</tbody></table></div>` : ''}`);
    const evaluations = t.evaluations || [];
    if (evaluations.length || Object.keys(res.criteria_averages || {}).length) {
      const comp = res.comparison || [];
      sections.push(`<h4 style="margin:14px 0 6px;">Avaliações e Comparativo</h4>
        <p style="margin:0 0 6px;">Inicial: <strong>${(res.evaluations_by_stage || {}).inicial || 0}</strong> · Intermediárias: <strong>${(res.evaluations_by_stage || {}).intermediaria || 0}</strong> · Finais: <strong>${(res.evaluations_by_stage || {}).final || 0}</strong> · Média geral: <strong>${res.overall_average ?? '—'}</strong> · Recomendação: <strong>${res.recommend_rate ?? 0}%</strong> · Preferem novo: <strong>${(res.preferences || {}).novo || 0}</strong></p>
        ${comp.length ? `<div class="table-wrap"><table>
          <thead><tr><th>Critério</th><th>EPI atual</th><th>EPI em teste</th><th>Δ%</th></tr></thead>
          <tbody>${comp.map((c) => `<tr>
            <td>${esc(c.criterion)}</td><td>${c.atual ?? '—'}</td><td><strong>${c.novo}</strong></td>
            <td style="color:${(c.delta_pct ?? 0) >= 0 ? 'var(--success)' : 'var(--danger)'};">${c.delta_pct != null ? `${c.delta_pct > 0 ? '+' : ''}${c.delta_pct}%` : '—'}</td>
          </tr>`).join('')}</tbody></table></div>` : ''}`);
    }
    const incidents = t.incidents || [];
    if (incidents.length) {
      const canManage = hasPermission('ppe_test:manage');
      sections.push(`<h4 style="margin:14px 0 6px;">Ocorrências (${incidents.length})</h4>
        <div class="table-wrap"><table>
        <thead><tr><th>Data</th><th>Tipo</th><th>Gravidade</th><th>Descrição</th><th>Status</th><th></th></tr></thead>
        <tbody>${incidents.map((i) => `<tr>
          <td>${fmtDate(i.created_at)}</td><td>${esc(i.incident_type)}</td>
          <td>${i.severity === 'critica' ? '<strong style="color:var(--danger);">CRÍTICA</strong>' : esc(i.severity)}</td>
          <td>${esc(i.description)}</td>
          <td>${i.status === 'resolvida' ? '<span style="color:var(--success);">Resolvida</span>' : '<span style="color:var(--pending);">Aberta</span>'}</td>
          <td>${canManage && i.status !== 'resolvida' ? `<button class="btn ghost" data-ppe-incident-resolve="${i.id}" style="font-size:11px;">Tratar</button>` : ''}</td>
        </tr>`).join('')}</tbody></table></div>`);
    }
    if (t.decision) {
      sections.push(`<h4 style="margin:14px 0 6px;">Decisão</h4>
        <p style="margin:0;"><strong>${esc(t.decision)}</strong> por ${esc(t.decision_by_name)} em ${fmtDate(t.decision_at)} — ${esc(t.decision_reason)}<br>
        ${t.technical_opinion ? `<em>Parecer técnico:</em> ${esc(t.technical_opinion)}<br>` : ''}
        ${t.scope_type ? `<em>Escopo:</em> <strong>${esc(t.scope_type)}</strong>${t.scope_joint_venture ? ` (${esc(t.scope_joint_venture)})` : ''}` : ''}
        ${t.approved_epi_id ? ` · EPI oficial #${esc(t.approved_epi_id)} homologado em ${fmtDate(t.homologated_at)} por ${esc(t.homologated_by_name)}` : ''}</p>`);
    }
    const events = t.events || [];
    if (events.length) {
      sections.push(`<h4 style="margin:14px 0 6px;">Linha do Tempo / Auditoria</h4>
        <ul style="margin:0;padding-left:18px;">${events.map((e) => `<li style="margin-bottom:2px;">
          <span style="color:var(--color-text-muted);">${fmtDate(e.created_at)}</span> —
          <strong>${esc(e.action)}</strong>${e.new_status ? ` → ${esc(STATUS_LABELS[e.new_status] || e.new_status)}` : ''}
          <span style="color:var(--color-text-muted);">(${esc(e.actor_name || 'sistema')})</span>
          ${e.reason ? `<em> — ${esc(e.reason)}</em>` : ''}</li>`).join('')}</ul>`);
    }
    document.getElementById('ppe-detail-body').innerHTML = sections.join('');
  }

  // ── Ações do detalhe ────────────────────────────────────────────────────────
  const scaleFields = (names) => names.map(([name, label]) => ({
    name, label, type: 'select', options: SCALE_OPTIONS,
  }));

  function runDetailAction(action) {
    const t = _detail;
    if (!t) return;
    const id = t.id;
    const reloadDetail = async () => { await loadPpeTests(); await openDetail(id); };
    const participantOptions = (t.participants || []).map((p) => ({ value: p.id, label: p.employee_name || `#${p.employee_id}` }));
    switch (action) {
      case 'tech-review':
        openForm('Análise Técnica e Documental', [
          {
            name: 'result', label: 'Resultado', type: 'select', required: true,
            options: [
              { value: 'aprovar_para_teste', label: 'Aprovar para teste' },
              { value: 'solicitar_correcao', label: 'Solicitar correção' },
              { value: 'solicitar_documento', label: 'Solicitar documento' },
              { value: 'encaminhar_aprovacao_superior', label: 'Encaminhar para aprovação superior' },
              { value: 'rejeitar', label: 'Rejeitar' },
            ],
          },
          { name: 'ck_ca_valido', label: 'CA válido', type: 'checkbox' },
          { name: 'ck_compatibilidade_risco', label: 'Compatível com o risco', type: 'checkbox' },
          { name: 'ck_ficha_tecnica', label: 'Ficha técnica presente', type: 'checkbox' },
          { name: 'ck_normas', label: 'Normas aplicáveis atendidas', type: 'checkbox' },
          { name: 'ck_higienizacao', label: 'Instruções de uso/higienização/manutenção', type: 'checkbox' },
          { name: 'ck_compatibilidade_epis', label: 'Compatível com outros EPIs', type: 'checkbox' },
          { name: 'ck_treinamento', label: 'Necessidade de treinamento avaliada', type: 'checkbox' },
          { name: 'ck_custo', label: 'Custo/impacto operacional avaliado', type: 'checkbox' },
          { name: 'notes', label: 'Parecer / justificativa', type: 'textarea' },
        ], async (values) => {
          const checklist = {};
          Object.keys(values).filter((k) => k.startsWith('ck_')).forEach((k) => { checklist[k.slice(3)] = !!values[k]; });
          await post(`/api/ppe-tests/${id}/technical-review`, { result: values.result, notes: values.notes, checklist });
          showToast('Análise técnica registrada.');
          await reloadDetail();
        });
        break;
      case 'plan': {
        const plan = t.plan || {};
        openForm('Plano de Teste', [
          { name: 'start_date', label: 'Data inicial', type: 'date', required: true, value: plan.start_date || '' },
          { name: 'end_date', label: 'Data final prevista', type: 'date', required: true, value: plan.end_date || '' },
          {
            name: 'pilot_unit_id', label: 'Unidade piloto', type: 'select', value: plan.pilot_unit_id || '',
            options: [{ value: '', label: '—' }].concat((state.units || []).map((u) => ({ value: u.id, label: u.name }))),
          },
          { name: 'objective', label: 'Objetivo do teste', type: 'textarea', value: plan.objective || '' },
          { name: 'hypothesis', label: 'Hipótese', value: plan.hypothesis || '' },
          { name: 'sector', label: 'Setor', value: plan.sector || '' },
          { name: 'activity', label: 'Atividade', value: plan.activity || '' },
          { name: 'participants_target', label: 'Quantidade de participantes', type: 'number', value: plan.participants_target || '' },
          { name: 'epis_quantity', label: 'Quantidade de EPIs', type: 'number', value: plan.epis_quantity || '' },
          {
            name: 'current_epi_id', label: 'Modelo comparativo atual', type: 'select', value: plan.current_epi_id || '',
            options: [{ value: '', label: '—' }].concat((state.epis || []).map((e) => ({ value: e.id, label: e.name }))),
          },
          { name: 'approval_criteria', label: 'Critérios de aprovação', type: 'textarea', value: plan.approval_criteria || '' },
          { name: 'rejection_criteria', label: 'Critérios de reprovação', type: 'textarea', value: plan.rejection_criteria || '' },
          { name: 'evaluation_frequency', label: 'Frequência das avaliações (ex.: inicial, 15d, 30d, final)', value: plan.evaluation_frequency || '' },
          { name: 'technical_manager', label: 'Responsável técnico', value: plan.technical_manager || '' },
          { name: 'operational_manager', label: 'Responsável operacional', value: plan.operational_manager || '' },
          { name: 'min_participants', label: 'Mínimo de participantes p/ decisão', type: 'number', value: plan.min_participants || '' },
          { name: 'min_response_rate', label: 'Taxa mínima de respostas (%)', type: 'number', value: plan.min_response_rate || '' },
          { name: 'training_required', label: 'Exige treinamento', type: 'checkbox', value: !!plan.training_required },
          { name: 'contingency_plan', label: 'Plano de contingência', type: 'textarea', value: plan.contingency_plan || '' },
          { name: 'interruption_condition', label: 'Condição de interrupção', value: plan.interruption_condition || '' },
        ], async (values) => {
          await post(`/api/ppe-tests/${id}/plan`, values);
          showToast('Plano de teste salvo.');
          await reloadDetail();
        });
        break;
      }
      case 'participant':
        openForm('Selecionar Participante', [
          {
            name: 'employee_id', label: 'Colaborador', type: 'select', required: true,
            options: [{ value: '', label: 'Selecione' }].concat((state.employees || []).map((e) => ({ value: e.id, label: `${e.name} (${e.role_name || '—'})` }))),
          },
          { name: 'size', label: 'Tamanho necessário' },
          {
            name: 'current_epi_id', label: 'EPI atual do participante', type: 'select',
            options: [{ value: '', label: '—' }].concat((state.epis || []).map((e) => ({ value: e.id, label: e.name }))),
          },
          { name: 'orientation_confirmed', label: 'Orientação de uso confirmada', type: 'checkbox' },
          { name: 'signature_name', label: 'Assinatura (nome)' },
          {
            name: 'status', label: 'Status inicial', type: 'select', value: 'convidado',
            options: [{ value: 'convidado', label: 'Convidado' }, { value: 'confirmado', label: 'Confirmado' }],
          },
        ], async (values) => {
          await post(`/api/ppe-tests/${id}/participants`, values);
          showToast('Participante adicionado.');
          await reloadDetail();
        });
        break;
      case 'receive':
        openForm('Receber Lote de Teste', [
          { name: 'quantity', label: 'Quantidade recebida', type: 'number', required: true },
          { name: 'batch', label: 'Lote' },
          { name: 'supplier', label: 'Fornecedor' },
          { name: 'storage_location', label: 'Local de armazenamento' },
          { name: 'notes', label: 'Observações', type: 'textarea' },
        ], async (values) => {
          await post(`/api/ppe-tests/${id}/distributions`, { ...values, movement_type: 'recebimento' });
          showToast('Recebimento registrado no controle próprio do teste.');
          await reloadDetail();
        });
        break;
      case 'deliver':
        openForm('Entregar EPI de Teste (uso controlado)', [
          { name: 'participant_id', label: 'Participante', type: 'select', required: true, options: [{ value: '', label: 'Selecione' }].concat(participantOptions) },
          { name: 'quantity', label: 'Quantidade', type: 'number', required: true, value: '1' },
          { name: 'signature_name', label: 'Assinatura (nome)' },
          { name: 'expected_return', label: 'Devolução esperada', type: 'date' },
          { name: 'notes', label: 'Observações', type: 'textarea' },
        ], async (values) => {
          await post(`/api/ppe-tests/${id}/distributions`, { ...values, movement_type: 'entrega' });
          showToast('Entrega controlada registrada.');
          await reloadDetail();
        });
        break;
      case 'start':
        openForm('Iniciar Período de Teste', [
          { name: 'notes', label: 'Observações', type: 'textarea' },
        ], async (values) => {
          await post(`/api/ppe-tests/${id}/start`, values);
          showToast('Teste iniciado.');
          await reloadDetail();
        });
        break;
      case 'suspend':
        openForm('Suspender Teste', [
          { name: 'reason', label: 'Justificativa', type: 'textarea', required: true },
        ], async (values) => {
          await post(`/api/ppe-tests/${id}/suspend`, values);
          showToast('Teste suspenso.');
          await reloadDetail();
        });
        break;
      case 'resume':
        openForm('Retomar Teste', [
          { name: 'notes', label: 'Observações', type: 'textarea' },
        ], async (values) => {
          await post(`/api/ppe-tests/${id}/resume`, values);
          showToast('Teste retomado.');
          await reloadDetail();
        });
        break;
      case 'complete':
        openForm('Concluir Período de Teste', [
          { name: 'notes', label: 'Observações', type: 'textarea' },
        ], async (values) => {
          await post(`/api/ppe-tests/${id}/complete`, values);
          showToast('Teste concluído — pronto para consolidação e decisão.');
          await reloadDetail();
        });
        break;
      case 'evaluate':
        openForm('Registrar Avaliação (escala 1–5)', [
          { name: 'participant_id', label: 'Participante', type: 'select', required: true, options: [{ value: '', label: 'Selecione' }].concat(participantOptions) },
          {
            name: 'stage', label: 'Momento', type: 'select', required: true,
            options: Object.entries(STAGE_LABELS).map(([value, label]) => ({ value, label })),
          },
          { type: 'section', label: 'Critérios do EPI em teste' },
          ...scaleFields([
            ['r_conforto', 'Conforto'], ['r_ergonomia', 'Ergonomia'], ['r_mobilidade', 'Mobilidade'],
            ['r_resistencia', 'Resistência'], ['r_peso', 'Peso'], ['r_facilidade_uso', 'Facilidade de uso'],
            ['r_protecao_percebida', 'Proteção percebida'], ['r_satisfacao_geral', 'Satisfação geral'],
            ['r_durabilidade', 'Durabilidade'], ['r_adequacao_funcao', 'Adequação à função'],
          ]),
          { type: 'section', label: 'Comparação com o EPI atual (opcional)' },
          ...scaleFields([
            ['c_conforto', 'Conforto (EPI atual)'], ['c_mobilidade', 'Mobilidade (EPI atual)'],
            ['c_facilidade_uso', 'Facilidade de uso (EPI atual)'], ['c_protecao_percebida', 'Proteção percebida (EPI atual)'],
            ['c_durabilidade', 'Durabilidade (EPI atual)'],
          ]),
          {
            name: 'preference', label: 'Preferência', type: 'select',
            options: [{ value: '', label: '—' }, { value: 'novo', label: 'EPI em teste' }, { value: 'atual', label: 'EPI atual' }, { value: 'indiferente', label: 'Indiferente' }],
          },
          { name: 'recommend', label: 'Recomenda a aprovação', type: 'checkbox' },
          { name: 'continue_intent', label: 'Pretende continuar usando', type: 'checkbox' },
          { name: 'positive_points', label: 'Pontos positivos', type: 'textarea' },
          { name: 'negative_points', label: 'Pontos negativos', type: 'textarea' },
          { name: 'comments', label: 'Comentários (pergunta aberta)', type: 'textarea' },
        ], async (values) => {
          const ratings = {};
          const current = {};
          Object.entries(values).forEach(([k, v]) => {
            if (k.startsWith('r_') && v) ratings[k.slice(2)] = Number(v);
            if (k.startsWith('c_') && v) current[k.slice(2)] = Number(v);
          });
          await post(`/api/ppe-tests/${id}/evaluations`, {
            participant_id: values.participant_id, stage: values.stage,
            ratings, current_epi_ratings: current,
            preference: values.preference, recommend: !!values.recommend,
            continue_intent: !!values.continue_intent,
            positive_points: values.positive_points, negative_points: values.negative_points,
            comments: values.comments,
          });
          showToast('Avaliação registrada.');
          await reloadDetail();
        });
        break;
      case 'incident':
        openForm('Registrar Ocorrência', [
          { name: 'participant_id', label: 'Participante', type: 'select', options: [{ value: '', label: '—' }].concat(participantOptions) },
          {
            name: 'incident_type', label: 'Tipo', type: 'select', required: true,
            options: ['desconforto', 'irritacao', 'falha', 'ruptura', 'incompatibilidade', 'tamanho_inadequado', 'perda', 'dano', 'incidente', 'quase_acidente', 'interrupcao_uso', 'substituicao', 'recusa', 'treinamento_adicional'].map((v) => ({ value: v, label: v.replace(/_/g, ' ') })),
          },
          {
            name: 'severity', label: 'Gravidade', type: 'select', required: true,
            options: [{ value: 'leve', label: 'Leve' }, { value: 'moderada', label: 'Moderada' }, { value: 'grave', label: 'Grave' }, { value: 'critica', label: 'Crítica' }],
          },
          { name: 'description', label: 'Descrição', type: 'textarea', required: true },
          { name: 'evidence', label: 'Evidência' },
          { name: 'action_taken', label: 'Ação tomada' },
          { name: 'suspend_test', label: 'Suspender o teste (apenas gravidade crítica)', type: 'checkbox' },
        ], async (values) => {
          const result = await post(`/api/ppe-tests/${id}/incidents`, { ...values, suspend_test: !!values.suspend_test });
          showToast(result.suspended ? 'Ocorrência crítica registrada — teste suspenso.' : 'Ocorrência registrada.');
          await reloadDetail();
        });
        break;
      case 'decision':
        openForm('Decisão Técnica Formal', [
          {
            name: 'decision', label: 'Decisão', type: 'select', required: true,
            options: [
              { value: 'aprovar', label: 'Aprovar' },
              { value: 'aprovar_com_restricao', label: 'Aprovar com restrição' },
              { value: 'prorrogar_teste', label: 'Prorrogar teste' },
              { value: 'nova_rodada', label: 'Nova rodada de avaliação' },
              { value: 'solicitar_ajuste_fornecedor', label: 'Solicitar ajuste ao fornecedor' },
              { value: 'rejeitar', label: 'Rejeitar' },
              { value: 'arquivar', label: 'Arquivar' },
            ],
          },
          { name: 'reason', label: 'Justificativa', type: 'textarea', required: true },
          { name: 'technical_opinion', label: 'Parecer técnico (obrigatório p/ aprovação)', type: 'textarea' },
          { name: 'operational_opinion', label: 'Parecer operacional', type: 'textarea' },
          { name: 'purchasing_opinion', label: 'Parecer de compras', type: 'textarea' },
          { name: 'restrictions', label: 'Restrições' },
          { name: 'conditions', label: 'Condições' },
          { name: 'approval_validity', label: 'Validade da aprovação' },
          { name: 'new_end_date', label: 'Nova data final (se prorrogar)', type: 'date' },
          { name: 'override_minimums', label: 'Exceção justificada aos critérios mínimos', type: 'checkbox' },
        ], async (values) => {
          await post(`/api/ppe-tests/${id}/decision`, { ...values, override_minimums: !!values.override_minimums });
          showToast('Decisão registrada.');
          await reloadDetail();
        });
        break;
      case 'homologate':
        openForm('Homologar — Definir Escopo de Validade', [
          {
            name: 'scope_type', label: 'Escopo de aprovação', type: 'select', required: true,
            options: [
              { value: 'GLOBAL', label: 'Global da empresa' },
              { value: 'JOINT_VENTURE', label: 'Joint Venture' },
              { value: 'UNIT', label: 'Exclusivo de uma unidade' },
            ],
          },
          {
            name: 'scope_unit_id', label: 'Unidade (escopo UNIT ou JV)', type: 'select',
            options: [{ value: '', label: '—' }].concat((state.units || []).map((u) => ({ value: u.id, label: u.name }))),
          },
          { name: 'scope_joint_venture', label: 'Joint Venture (nome da operação, escopo JV)' },
          { name: 'official_name', label: 'Nome oficial do EPI', value: t.name },
          { name: 'purchase_code', label: 'Código oficial (vazio = automático)' },
          { name: 'manufacture_date', label: 'Data de fabricação', type: 'date' },
          { name: 'epi_validity_date', label: 'Validade do EPI', type: 'date' },
          { name: 'validity_days', label: 'Validade (dias) p/ substituição', type: 'number' },
          { name: 'notes', label: 'Observações da homologação', type: 'textarea' },
        ], async (values) => {
          const result = await post(`/api/ppe-tests/${id}/homologate`, values);
          const scope = result.scope || {};
          showToast(`EPI homologado no banco oficial (escopo ${scope.scope_type}). Obs.: com uma única empresa e unidade, o sistema aplica automaticamente o escopo UNIQUE.`);
          await reloadDetail();
        });
        break;
      case 'reject':
        openForm('Reprovar EPI em Teste', [
          { name: 'reason', label: 'Justificativa', type: 'textarea', required: true },
          {
            name: 'items_destination', label: 'Destino dos itens', type: 'select',
            options: [
              { value: '', label: '—' },
              { value: 'devolucao_fornecedor', label: 'Devolução ao fornecedor' },
              { value: 'descarte', label: 'Descarte' },
              { value: 'recolhimento', label: 'Recolhimento e guarda' },
            ],
          },
        ], async (values) => {
          await post(`/api/ppe-tests/${id}/reject`, values);
          showToast('EPI reprovado — novas distribuições bloqueadas.');
          await reloadDetail();
        });
        break;
      default:
        break;
    }
  }

  function openIncidentResolve(incidentId) {
    const t = _detail;
    if (!t) return;
    openForm('Tratar Ocorrência', [
      { name: 'action_taken', label: 'Ação tomada' },
      { name: 'conclusion_notes', label: 'Conclusão', type: 'textarea', required: true },
    ], async (values) => {
      await post(`/api/ppe-tests/${t.id}/incidents/${incidentId}/resolve`, values);
      showToast('Ocorrência tratada.');
      await loadPpeTests();
      await openDetail(t.id);
    });
  }

  // ── Bindings ────────────────────────────────────────────────────────────────
  function bindPpeTestsView() {
    const pane = document.getElementById('avaliacoes-pane-epis-teste');
    if (!pane) return;
    bindAppListener(pane, 'click', (e) => {
      const sugTriage = e.target.closest('[data-ppe-sug-triage]');
      if (sugTriage) return openTriage(sugTriage.dataset.ppeSugTriage);
      const sugConvert = e.target.closest('[data-ppe-sug-convert]');
      if (sugConvert) return openNewCandidate(sugConvert.dataset.ppeSugConvert);
      const testOpen = e.target.closest('[data-ppe-test-open]');
      if (testOpen) return openDetail(testOpen.dataset.ppeTestOpen);
      const action = e.target.closest('[data-ppe-action]');
      if (action) return runDetailAction(action.dataset.ppeAction);
      const incResolve = e.target.closest('[data-ppe-incident-resolve]');
      if (incResolve) return openIncidentResolve(incResolve.dataset.ppeIncidentResolve);
      return undefined;
    });
    bindAppListener(document.getElementById('ppe-reload-btn'), 'click', loadPpeTests);
    bindAppListener(document.getElementById('ppe-new-suggestion-btn'), 'click', () => openNewSuggestion());
    bindAppListener(document.getElementById('ppe-new-candidate-btn'), 'click', () => openNewCandidate());
    bindAppListener(document.getElementById('ppe-detail-back'), 'click', closeDetail);
    bindAppListener(document.getElementById('ppe-form-cancel'), 'click', closeForm);
    bindAppListener(document.getElementById('ppe-form-confirm'), 'click', submitForm);
    bindAppListener(document.getElementById('ppe-form-modal'), 'click', (e) => {
      if (e.target === document.getElementById('ppe-form-modal')) closeForm();
    });
  }

  bindPpeTestsView();
  Object.assign(globalThis, { loadPpeTests });
}());

// ── Employee portal feedback status enhancement ────────────────────────────────

// Exposição explícita de funções `async` no escopo global.
// O guard `if (!globalThis.__EPI_APP_RUNTIME_LOADED__) { ... }` que envolve todo
// este arquivo torna as declarações `async function` block-scoped: ao contrário
// das funções não-async (que ganham hoisting global via Annex B em modo sloppy),
// as `async function` NÃO viram propriedades de globalThis. Os módulos de view
// (purchases.js, devolution.js, etc.) as consomem via `globalThis.<fn>()`; sem
// esta exposição elas ficam `undefined`, fazendo os loaders da aba Compras
// (loadAuthorizedSuppliers, loadPurchaseDemands, …) virarem no-op silencioso e
// `globalThis.api?.()` retornar undefined (quebra em `payload.items`).
[
  ['_purchaseDemands', () => _purchaseDemands, (value) => { _purchaseDemands = Array.isArray(value) ? value : []; }],
  ['_selectedDemands', () => _selectedDemands, (value) => { _selectedDemands = value instanceof Set ? value : new Set(value || []); }],
  ['_manualRequestItems', () => _manualRequestItems, (value) => { _manualRequestItems = Array.isArray(value) ? value : []; }],
  ['_aprovacoesList', () => _aprovacoesList, (value) => { _aprovacoesList = Array.isArray(value) ? value : []; }],
  ['_selectedAprovacoes', () => _selectedAprovacoes, (value) => { _selectedAprovacoes = value instanceof Set ? value : new Set(value || []); }],
].forEach(([name, get, set]) => {
  if (!Object.getOwnPropertyDescriptor(globalThis, name)?.get) {
    Object.defineProperty(globalThis, name, { configurable: true, get, set });
  }
});

Object.assign(globalThis, {
  api, apiOptional, loadBootstrap,
  loadAuthorizedSuppliers, loadPurchaseDemands, loadPurchaseRequests,
  loadPurchaseOrders, loadAprovacoesSolicitacoes, loadFornecedoresPurchaseFunctions,
  importSuppliersCSV, saveEditSupplier, openPoDetail, openPrDetail,
  submitPoAdminReview, submitPoApproval, submitPoApprovalWithItems,
  submitPoReceive, submitPoResubmit, _parsePoImportFile, _executarAprovacaoEmLote,
  _buildBulkUpdates, _syncAprovacoesBtnVisibility, exportAprovacoesCsv,
  populatePurchaseUnitSelects, updateCreateRequestBtn, _populatePurchaseRequestEpiSelect,
  _renderManualRequestItems, _syncManualRequestItemsJson,
});

// Item 4 — Conferência de entrega pelo QR da entrega (handover_token).
// Consome EXCLUSIVAMENTE os endpoints do backend (lookup/confirm). O QR carrega
// só o token opaco; a projeção segura (sem CPF) e a regra de fechamento vêm do
// backend — nenhuma regra de negócio é duplicada aqui.
function _handoverFeedback(message, isError) {
  const el = document.getElementById('handover-feedback');
  if (!el) return;
  el.textContent = message || '';
  el.style.color = isError ? 'var(--danger, #b00020)' : '';
}

async function handoverLookup() {
  const code = String(document.getElementById('handover-code')?.value || '').trim();
  const result = document.getElementById('handover-result');
  const confirmBtn = document.getElementById('handover-confirm-btn');
  if (confirmBtn) confirmBtn.hidden = true;
  if (result) { result.hidden = true; result.innerHTML = ''; }
  if (!code) { _handoverFeedback(tr('handover.codeRequired', 'Informe o código da entrega.'), true); return; }
  try {
    const resp = await api(`/api/deliveries/handover-lookup?code=${encodeURIComponent(code)}&${actorQuery()}`);
    const h = resp.handover || {};
    const row = (label, val) => `<div><strong>${esc(label)}:</strong> ${esc(val || '-')}</div>`;
    if (result) {
      result.innerHTML =
        row(tr('handover.collaborator', 'Colaborador'), `${h.employee_first_name || ''} ${h.employee_last_name || ''}`.trim())
        + row(tr('handover.registration', 'Matrícula'), h.employee_registration)
        + row(tr('epi.title', 'EPI'), h.epi_name)
        + row(tr('delivery.size', 'Tamanho'), h.size || h.glove_size || h.uniform_size)
        + row(tr('handover.lot', 'Lote'), h.lot_code)
        + row(tr('handover.request', 'Solicitação'), h.request_id ? `#${h.request_id} (${h.request_status || ''})` : '-')
        + (h.already_confirmed ? `<div class="hint">${esc(tr('handover.alreadyConfirmed', 'Recebimento já confirmado em'))} ${esc(h.confirmed_at)}</div>` : '');
      result.hidden = false;
    }
    if (confirmBtn) confirmBtn.hidden = Boolean(h.already_confirmed);
    _handoverFeedback('');
  } catch (error) {
    _handoverFeedback(error.message || tr('handover.lookupFailed', 'Não foi possível conferir o código.'), true);
  }
}

async function handoverConfirm() {
  const code = String(document.getElementById('handover-code')?.value || '').trim();
  const confirmBtn = document.getElementById('handover-confirm-btn');
  if (!code) { return; }
  try {
    if (confirmBtn) confirmBtn.disabled = true;
    const result = await api('/api/deliveries/handover-confirm', {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user?.id, code }),
    });
    showToast(
      result.already_confirmed
        ? tr('handover.alreadyConfirmedToast', 'Entrega já estava confirmada.')
        : tr('handover.confirmedToast', 'Recebimento confirmado. Portal atualizado.'),
      'success'
    );
    await handoverLookup();
  } catch (error) {
    showToast(error.message || tr('handover.confirmFailed', 'Não foi possível confirmar o recebimento.'), 'error');
  } finally {
    if (confirmBtn) confirmBtn.disabled = false;
  }
}

bindAppListener(document, 'click', (event) => {
  const target = event.target;
  if (target?.id === 'handover-lookup-btn') { event.preventDefault(); void handoverLookup(); }
  else if (target?.id === 'handover-confirm-btn') { event.preventDefault(); void handoverConfirm(); }
});
globalThis.handoverLookup = handoverLookup;
globalThis.handoverConfirm = handoverConfirm;

// fechamento do runtime guard global __EPI_APP_RUNTIME_LOADED__
}
