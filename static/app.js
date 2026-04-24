if (!globalThis.__EPI_APP_RUNTIME_LOADED__) {
  globalThis.__EPI_APP_RUNTIME_LOADED__ = true;

var STORAGE_KEYS = globalThis.STORAGE_KEYS || Object.freeze({
  session: 'epi-session-v4',
  permissions: 'epi-session-v4-permissions',
  token: 'epi-session-v4-token',
  changeRequired: 'epi-session-v4-password-change-required'
});
globalThis.STORAGE_KEYS = STORAGE_KEYS;
const ROLE_LABELS = {
  master_admin: 'Administrador Master',
  general_admin: 'Administrador Geral',
  registry_admin: 'Administrador de Registro',
  admin: 'Administrador Local',
  user: 'Gestor de EPI',
  employee: 'Funcionário'
};
const ROLE_PERMISSIONS = {
  master_admin: ['dashboard:view', 'users:view', 'users:create', 'users:update', 'users:delete', 'units:view', 'units:create', 'units:update', 'units:delete', 'employees:view', 'employees:create', 'employees:update', 'employees:delete', 'epis:view', 'epis:create', 'epis:update', 'epis:delete', 'deliveries:view', 'deliveries:create', 'fichas:view', 'reports:view', 'alerts:view', 'companies:view', 'companies:create', 'companies:update', 'companies:license', 'commercial:view', 'usage:view', 'stock:view', 'stock:adjust', 'settings:view', 'settings:update'],
  general_admin: ['dashboard:view', 'users:view', 'users:create', 'users:update', 'users:delete', 'units:view', 'units:create', 'units:update', 'units:delete', 'employees:view', 'employees:create', 'employees:update', 'employees:delete', 'epis:view', 'epis:create', 'epis:update', 'epis:delete', 'deliveries:view', 'deliveries:create', 'fichas:view', 'reports:view', 'alerts:view', 'companies:view', 'stock:view', 'stock:adjust', 'settings:view', 'settings:update'],
  registry_admin: ['dashboard:view', 'users:view', 'users:create', 'users:update', 'users:delete', 'units:view', 'units:create', 'units:update', 'units:delete', 'employees:view', 'employees:create', 'employees:update', 'employees:delete', 'epis:view', 'epis:create', 'epis:update', 'epis:delete', 'deliveries:view', 'fichas:view', 'reports:view', 'alerts:view', 'stock:view', 'settings:view', 'settings:update'],
  admin: ['dashboard:view', 'users:view', 'units:view', 'employees:view', 'employees:update', 'epis:view', 'deliveries:view', 'deliveries:create', 'fichas:view', 'reports:view', 'alerts:view', 'stock:view', 'stock:adjust'],
  user: ['dashboard:view', 'deliveries:view', 'deliveries:create', 'fichas:view', 'alerts:view', 'units:view', 'employees:view', 'employees:update', 'epis:view', 'stock:view', 'stock:adjust'],
  employee: []
};
const VIEW_PERMISSIONS = {
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
  configuracao: 'settings:view',
  relatorios: 'reports:view'
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
    rollback: 'Desativar flag + limpar storage da sessão piloto.'
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
    rollback: 'Desativar flag para restaurar somente os pilotos clássicos.'
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
  } catch (_error) {
    // no-op
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

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
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
  const queryOnly = getFeatureFlag('dashboard_interativo_enabled', { defaultValue: false, allowStorage: false });
  if (queryOnly) return true;
  if (!isPhase2StorageRolloutEnabled()) return false;
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
    activeMessage = 'Piloto ativo.',
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
        activeMessage: 'Piloto HTMX/Alpine ativo na navegação de colaboradores.',
        inactiveMessage: 'Fluxo clássico de colaboradores ativo.'
      });
    },
    refresh: async (event) => {
      const moduleName = event?.detail?.elt?.dataset?.phase2RefreshModule;
      await refreshPhase2Module(moduleName);
    },
    toastRefreshError: 'Falha ao atualizar lista com navegação parcial. Fluxo clássico segue disponível.',
    toastResponseError: 'Navegação parcial indisponível no momento. Use o fluxo clássico sem recarregar.'
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
    toastRefreshError: 'Falha ao atualizar listagem de colaboradores no piloto. Fluxo clássico segue disponível.',
    toastResponseError: 'Listagem parcial indisponível no momento. Use o fluxo clássico sem recarregar.'
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
        activeMessage: 'Piloto HTMX/Alpine ativo na Gestão de Colaborador.',
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
    toastRefreshError: 'Falha ao atualizar Gestão de Colaborador no piloto. Fluxo clássico segue disponível.',
    toastResponseError: 'Navegação parcial de Gestão de Colaborador indisponível. Use o fluxo clássico sem recarregar.'
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
        activeMessage: 'Piloto HTMX/Alpine ativo na navegação de EPI.',
        inactiveMessage: 'Fluxo clássico de EPI ativo.'
      });
    },
    refresh: async () => {
      await refreshPhase2EpisModule();
    },
    toastRefreshError: 'Falha ao atualizar lista de EPI no piloto. Fluxo clássico segue disponível.',
    toastResponseError: 'Navegação parcial de EPI indisponível. Use o fluxo clássico sem recarregar.'
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
        activeMessage: 'Piloto HTMX/Alpine ativo no Controle de Estoque (somente leitura).',
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
    toastRefreshError: 'Falha ao atualizar listagem de estoque no piloto. Fluxo clássico segue disponível.',
    toastResponseError: 'Atualização parcial de estoque indisponível. Use o fluxo clássico sem recarregar.'
  }
]);

function setupPhase2ModulePilot(definition) {
  const enabled = Boolean(definition.flagResolver?.());
  applyPhase2Visibility(definition.moduleName, enabled);
  setPhase2ModuleEnabled(definition.moduleName, enabled);
  if (typeof definition.setup === 'function') {
    definition.setup({ enabled });
  }
  if (!enabled) return;
  if (!globalThis.htmx) {
    reportNonCriticalError(`[fase2:${definition.moduleName}] HTMX indisponível`, new Error('HTMX unavailable'));
    return;
  }
  bindPhase2ModuleListeners(definition);
  debugLog(`[fase2:${definition.moduleName}] piloto ativo`);
}


function setupPhase29Ux() {
  const modules = [
    {
      name: 'colaborador-lista',
      enabled: isColabListHtmxPilotEnabled(),
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
      enabled: isEpiHtmxPilotEnabled(),
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
      setFeedback(feedbackElement, 'Atualização parcial concluída sem recarregar a página.', 'success');
    });

    safeOn(document.body, 'htmx:responseError', (event) => {
      const trigger = event?.detail?.elt;
      if (!trigger || trigger.dataset?.phase2RefreshModule !== moduleConfig.name) return;
      setFeedback(feedbackElement, 'Falha na atualização parcial. O fluxo clássico continua disponível.', 'error');
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
    refresh: async () => loadStockEpis(),
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

async function runInteractiveRefresh(moduleName) {
  const moduleConfig = resolveInteractiveToolsModule(moduleName);
  if (!moduleConfig || typeof moduleConfig.refresh !== 'function') return;
  setInteractiveModuleLoading(moduleName, true);
  setInteractiveModuleStatus(moduleName, 'Atualizando...', 'info');
  try {
    await moduleConfig.refresh();
    const visibleRows = moduleConfig.tableSelector ? countVisibleRows(moduleConfig.tableSelector) : 0;
    const summary = visibleRows ? ` ${visibleRows} resultado(s).` : '';
    setInteractiveModuleStatus(moduleName, `Atualizado com sucesso.${summary}`, 'success');
    flashUpdatedSurface(moduleName);
  } catch (error) {
    reportNonCriticalError(`[ux-tools] falha ao atualizar ${moduleName}`, error);
    setInteractiveModuleStatus(moduleName, 'Erro ao atualizar. Fluxo clássico mantido.', 'error');
  } finally {
    setInteractiveModuleLoading(moduleName, false);
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
  if (!isUxToolsFunctionalEnabled()) return;
  if (document.body?.dataset?.uxToolsBound === '1') return;
  if (document.body) document.body.dataset.uxToolsBound = '1';

  const attachRealtimeFilterFeedback = (moduleName) => {
    const moduleConfig = resolveInteractiveToolsModule(moduleName);
    const container = moduleConfig?.filterSelector ? document.querySelector(moduleConfig.filterSelector) : null;
    if (!container) return;
    const run = debounce(() => {
      setInteractiveModuleStatus(moduleName, 'Filtrando...', 'info');
      try {
        if (typeof moduleConfig.syncFilters === 'function') moduleConfig.syncFilters();
      } finally {
        const visibleRows = moduleConfig.tableSelector ? countVisibleRows(moduleConfig.tableSelector) : 0;
        setInteractiveModuleStatus(moduleName, `${visibleRows} resultado(s) encontrado(s).`, visibleRows ? 'success' : 'warning');
      }
    }, 300);
    safeOn(container, 'input', run);
    safeOn(container, 'change', run);
  };

  ['colaboradores', 'gestao-colaborador', 'epis', 'estoque'].forEach(attachRealtimeFilterFeedback);

  safeOn(document, 'click', (event) => {
    const refreshBtn = event?.target?.closest?.('[data-phase2-refresh-module]');
    if (refreshBtn && isUxToolsFunctionalEnabled()) {
      const moduleName = refreshBtn.dataset.phase2RefreshModule;
      if (resolveInteractiveToolsModule(moduleName)) {
        event.preventDefault();
        event.stopPropagation();
        void runInteractiveRefresh(moduleName);
        return;
      }
    }
    const actionBtn = event?.target?.closest?.('[data-ux-action]');
    if (!actionBtn) return;
    const action = actionBtn.dataset.uxAction;
    const moduleName = actionBtn.dataset.uxModule;
    const moduleConfig = resolveInteractiveToolsModule(moduleName);
    if (!moduleConfig) return;
    event.preventDefault();
    closeInteractiveDropdowns();
    if (action === 'clear-filters') {
      moduleConfig.clearFilters?.();
      setInteractiveModuleStatus(moduleName, 'Filtros limpos.', 'success');
      return;
    }
    if (action === 'refresh-data') {
      void runInteractiveRefresh(moduleName);
      return;
    }
    if (action === 'scroll-top') {
      globalThis.scrollTo({ top: 0, behavior: 'smooth' });
      setInteractiveModuleStatus(moduleName, 'Posição ajustada para o topo.', 'info');
      return;
    }
    if (action === 'toggle-density') {
      document.body.classList.toggle('ux-density-compact');
      setInteractiveModuleStatus(moduleName, document.body.classList.contains('ux-density-compact') ? 'Modo compacto ativado.' : 'Modo detalhado ativado.', 'info');
    }
  });
}

function setupPhase2PilotsSafely() {
  PHASE2_MODULE_DEFINITIONS.forEach((definition) => {
    try {
      setupPhase2ModulePilot(definition);
    } catch (error) {
      reportNonCriticalError(`[fase2] piloto ${definition.moduleName} desativado por fail-safe`, error);
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
  await loadStockEpis();
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
  token: safeStorageRead(STORAGE_KEYS.token, ''),
  configurationRules: [],
  configurationFramework: deepClone(DEFAULT_CONFIGURATION_FRAMEWORK),
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
  employeesFilters: { company_id: '', unit_id: '', search: '', sector: '', role_name: '' },
  employeesOpsFilters: { company_id: '', unit_id: '', search: '', sector: '', role_name: '' },
  episFilters: { company_id: '', unit_id: '', search: '', protection: '', section: '', manufacturer: '', supplier: '' },
  deliveriesFilters: { company_id: '', unit_id: '', employee: '', epi: '', date_from: '', date_to: '', status: '' },
  fichaFilters: { company_id: '', unit_id: '', search: '' },
  dashboardFilters: { query: '' },
  reportsRequestInFlight: false,
  reportArchivePage: 1,
  reportArchiveTotal: 0,
  reportArchivePageSize: 50,
  reportArchiveItems: [],
  signatureDraft: null,
  bootstrapDegraded: false,
  bootstrapError: null,
  bootstrapRetrying: false,
  requirePasswordChange: safeJsonParse(safeStorageRead(STORAGE_KEYS.changeRequired, 'false'), false)
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
  bootstrapDegradedRetry: document.getElementById('bootstrap-degraded-retry'),
  bootstrapDegradedPanel: document.getElementById('bootstrap-degraded-panel'),
  bootstrapDegradedPanelMessage: document.getElementById('bootstrap-degraded-panel-message'),
  bootstrapDegradedPanelRetry: document.getElementById('bootstrap-degraded-panel-retry'),
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
  companyLogoFile: document.getElementById('company-logo-file'),
  companyLogoPreview: document.getElementById('company-logo-preview'),
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
  unitsFilterType: document.getElementById('units-filter-type'),
  unitsFilterCity: document.getElementById('units-filter-city'),
  employeesTable: document.getElementById('employees-table'),
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
  episFilterCompany: document.getElementById('epis-filter-company'),
  episFilterUnit: document.getElementById('epis-filter-unit'),
  episFilterSearch: document.getElementById('epis-filter-search'),
  episFilterProtection: document.getElementById('epis-filter-protection'),
  episFilterSection: document.getElementById('epis-filter-section'),
  episFilterManufacturer: document.getElementById('epis-filter-manufacturer'),
  episFilterSupplier: document.getElementById('epis-filter-supplier'),
  phase3EpisContextStatus: document.getElementById('phase3-epis-context-status'),
  phase3EpisSummary: document.getElementById('phase3-epis-summary'),
  deliveriesTable: document.getElementById('deliveries-table'),
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

function qrCodeImageUrl(value) {
  const normalized = encodeURIComponent(String(value || '').trim());
  return `https://api.qrserver.com/v1/create-qr-code/?size=420x420&qzone=4&ecc=M&format=png&color=000000&bgcolor=FFFFFF&data=${normalized}`;
}

function buildEmployeeAccessLink(token) {
  const normalizedToken = String(token || '').trim();
  if (!normalizedToken) return '';
  return `${globalThis.location.origin}/?employee_token=${encodeURIComponent(normalizedToken)}`;
}
function buildApiHeaders(options = {}) {
  const authHeader = state.token ? { Authorization: `Bearer ${state.token}` } : {};
  return {
    'Content-Type': 'application/json',
    ...authHeader,
    ...options.headers
  };
}

async function requestApiResponse(path, options = {}) {
  try {
    return await fetch(path, {
      headers: buildApiHeaders(options),
      ...options
    });
  } catch (error) {
    if (error instanceof Error) {
      throw new Error('Falha de conexão com o servidor. Verifique sua internet e tente novamente.', { cause: error });
    }
    throw new Error('Falha de conexão com o servidor. Verifique sua internet e tente novamente.');
  }
}

async function parseApiPayload(response) {
  const contentType = String(response.headers.get('content-type') || '').toLowerCase();
  if (contentType.includes('application/json')) {
    try {
      return { contentType, payload: await response.json() };
    } catch (error) {
      reportNonCriticalError('api json parse failed', error);
      return { contentType, payload: null };
    }
  }

  const raw = await response.text();
  const compact = String(raw || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
  return {
    contentType,
    payload: raw ? { error: compact || 'Resposta não-JSON do servidor.', raw } : null
  };
}

function createApiError(message, response, payload, code = '') {
  const error = new Error(message);
  error.status = response.status;
  error.code = code || payload?.code || '';
  error.payload = payload;
  return error;
}

function ensureExpectedApiResponse(path, response, payload, contentType) {
  const expectsJson = String(path || '').startsWith('/api/');
  if (response.ok && expectsJson && !contentType.includes('application/json')) {
    throw createApiError('Resposta inválida do servidor. Tente novamente em instantes.', response, payload, 'INVALID_API_RESPONSE');
  }
}

function isBootstrapApiPath(path = '') {
  return String(path || '').startsWith('/api/bootstrap');
}

function throwIfApiRequestFailed(path, response, payload) {
  if (response.ok) return;
  const serverError = payload?.error;
  const serverMessage = typeof serverError === 'string' ? serverError : serverError?.message;
  const normalizedCode = payload?.code || serverError?.code || '';

  let fallbackMessage;
  if (response.status === 401) {
    fallbackMessage = 'Usuário ou senha inválidos.';
  } else if (response.status === 403) {
    fallbackMessage = 'Acesso negado. Faça login novamente.';
  } else if (response.status === 404) {
    fallbackMessage = 'Rota da API não encontrada. Verifique versão do frontend/backend.';
  } else {
    fallbackMessage = `Falha na requisição (${response.status}).`;
  }

  const apiError = createApiError(serverMessage || fallbackMessage, response, payload, normalizedCode);
  if (isBootstrapApiPath(path)) {
    apiError.nonFatal = true;
  }
  throw apiError;
}

async function api(path, options = {}) {
  const response = await requestApiResponse(path, options);
  const { contentType, payload } = await parseApiPayload(response);
  ensureExpectedApiResponse(path, response, payload, contentType);
  throwIfApiRequestFailed(path, response, payload);
  if (payload && typeof payload === 'object' && Object.hasOwn(payload, 'ok')) {
    if (payload.ok === false) {
      const err = payload.error || {};
      throw createApiError(err.message || 'Falha na API.', response, payload, err.code || '');
    }
    return payload.data ?? {};
  }
  return payload || {};
}

async function apiOptional(path, options = {}) {
  try {
    const payload = await api(path, options);
    return { ok: true, payload };
  } catch (error) {
    reportNonCriticalError(`[api-optional] ${path}`, error);
    return { ok: false, error };
  }
}

function normalizePermissions(user, permissions = []) {
  const fallback = ROLE_PERMISSIONS[user?.role] || [];
  return [...new Set([...(permissions || []), ...fallback])];
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

function saveSession(user, permissions = [], token = '') {
  state.user = { ...user, role: normalizeRole(user?.role) };
  state.permissions = normalizePermissions(state.user, permissions);
  state.token = String(token || '');
  safeStorageWrite(STORAGE_KEYS.session, JSON.stringify(state.user));
  safeStorageWrite(STORAGE_KEYS.permissions, JSON.stringify(state.permissions));
  if (state.token) safeStorageWrite(STORAGE_KEYS.token, state.token);
  else safeStorageRemove(STORAGE_KEYS.token);
  console.info('[AUTH]', {
    user_id: state.user?.id,
    perfil_recebido: user?.role,
    perfil_normalizado: state.user?.role,
    empresa_id: state.user?.company_id,
    permissions: state.permissions
  });
}

function setPasswordChangeRequired(required) {
  state.requirePasswordChange = Boolean(required);
  safeStorageWrite(STORAGE_KEYS.changeRequired, JSON.stringify(state.requirePasswordChange));
}

function clearSession() {
  state.user = null;
  state.permissions = [];
  state.token = '';
  safeStorageRemove(STORAGE_KEYS.session);
  safeStorageRemove(STORAGE_KEYS.permissions);
  safeStorageRemove(STORAGE_KEYS.token);
  safeStorageRemove(STORAGE_KEYS.changeRequired);
  state.requirePasswordChange = false;
  state.bootstrapDegraded = false;
  state.bootstrapError = null;
  state.bootstrapRetrying = false;
}

function isTemporaryBootstrapUnavailable(error) {
  const status = Number(error?.status || 0);
  const code = String(error?.code || error?.payload?.error?.code || '').toUpperCase();
  return status === 503 || code === 'DB_BOOTSTRAP_NOT_READY' || code === 'HTTP_503';
}

function isBootstrapRequestError(error) {
  return Boolean(error?.nonFatal) || Number(error?.status || 0) === 502;
}

const BOOTSTRAP_REQUIRED_VIEWS = new Set(['empresas', 'comercial', 'usuarios', 'unidades', 'colaboradores', 'gestao-colaborador', 'epis', 'estoque', 'entregas', 'fichas', 'relatorios', 'configuracao']);

function setBootstrapDegraded(error) {
  state.bootstrapDegraded = true;
  state.bootstrapError = {
    status: Number(error?.status || 0),
    code: String(error?.code || ''),
    message: String(error?.message || 'Falha ao carregar dados iniciais.')
  };
}

function clearBootstrapDegraded() {
  state.bootstrapDegraded = false;
  state.bootstrapError = null;
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
}

async function retryBootstrap() {
  if (state.bootstrapRetrying) return;
  state.bootstrapRetrying = true;
  try {
    if (refs.bootstrapDegradedPanelMessage) refs.bootstrapDegradedPanelMessage.textContent = 'Tentando carregar novamente...';
    await loadBootstrap();
    clearBootstrapDegraded();
    updateBootstrapDegradedUi();
    renderAll();
  } catch (error) {
    setBootstrapDegraded(error);
    updateBootstrapDegradedUi();
    console.warn('[auth] retryBootstrap falhou, mantendo modo degradado', error);
  } finally {
    state.bootstrapRetrying = false;
  }
}

function hasPermission(permission) {
  const activePermissions = state.permissions.length ? state.permissions : normalizePermissions(state.user, []);
  return activePermissions.includes(permission);
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
  if (normalized === 'navio' || normalized === 'embarcacao') return 'Embarcação';
  if (normalized === 'plataforma') return 'Plataforma';
  return 'Base';
}

function setLoginMessage(message = '', isError = false) {
  if (!refs.loginMessage) return;
  refs.loginMessage.textContent = message;
  refs.loginMessage.classList.toggle('error', Boolean(isError));
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

function formatDate(value) {
  const raw = String(value || '').trim();
  if (!raw) return '-';
  const parsed = /^\d{4}-\d{2}-\d{2}$/.test(raw)
    ? new Date(`${raw}T00:00:00`)
    : new Date(raw);
  if (Number.isNaN(parsed.getTime())) return '-';
  return new Intl.DateTimeFormat('pt-BR').format(parsed);
}

function formatDateTime(value) {
  const parsed = new Date(String(value || '').trim());
  if (Number.isNaN(parsed.getTime())) return '-';
  return parsed.toLocaleString('pt-BR');
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
    preview.innerHTML = '<div class="summary-item">Sem foto anexada.</div>';
    return;
  }
  preview.innerHTML = `<div class="logo-preview-card"><img class="company-logo company-logo-lg" src="${photoValue}" alt="Preview da foto do EPI"><span>Foto do EPI anexada</span></div>`;
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

function renderCompanyLogoPreview(logoValue) {
  if (!refs.companyLogoPreview) return;
  refs.companyLogoPreview.innerHTML = `<div class="logo-preview-card">${companyLogoMarkup({ name: 'Empresa', logo_type: logoValue }, 'company-logo company-logo-lg')}<span>${logoValue ? 'Logotipo carregado' : 'Imagem padrão em uso'}</span></div>`;
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
  if (refs.loginBrandLogo) refs.loginBrandLogo.innerHTML = companyLogoMarkup({ name: brand.display_name, logo_type: brand.login_logo_type || '' }, 'company-logo company-logo-lg');
}

async function handleCompanyLogoUpload(event) {
  const file = event.target.files?.[0];
  if (!file) {
    refs.companyForm.elements.logo_type.value = '';
    renderCompanyLogoPreview('');
    return;
  }
  const allowed = ['image/png', 'image/jpeg', 'image/svg+xml'];
  if (!allowed.includes(file.type)) {
    alert('Envie um logotipo PNG, JPG ou SVG.');
    event.target.value = '';
    return;
  }
  try {
    refs.companyForm.elements.logo_type.value = await fileToJpegDataUrl(file);
    renderCompanyLogoPreview(refs.companyForm.elements.logo_type.value);
  } catch (error) {
    alert(error.message);
    event.target.value = '';
  }
}

function showScreen(authenticated) {
  refs.loginScreen.classList.toggle('active', !authenticated);
  refs.mainScreen.classList.toggle('active', authenticated);
}

function roleLabel(role) {
  return ROLE_LABELS[role] || role;
}

function activeLabel(active) {
  return Number(active) === 1 ? 'Ativo' : 'Inativo';
}

function renderBadge(type, value, label) {
  return `<span class="badge badge-${type}-${value}">${label}</span>`;
}

function userStatusBadges(user) {
  const badges = [renderBadge('status', Number(user.active) === 1 ? 'active' : 'inactive', activeLabel(user.active))];
  if (Number(user.force_password_change || 0) === 1) badges.push(renderBadge('status', 'warning', 'Senha provisória'));
  return badges.join(' ');
}

function filterByUserCompany(items) {
  if (!state.user || state.user.role === 'master_admin') return items;
  return items.filter((item) => {
    const directCompanyId = item?.company_id;
    if (directCompanyId !== undefined && directCompanyId !== null && String(directCompanyId) !== '') {
      return String(directCompanyId) === String(state.user.company_id || '');
    }
    const isCompanyRecord = item && Object.hasOwn(item, 'license_status') && Object.hasOwn(item, 'user_limit');
    if (isCompanyRecord) {
      return String(item.id || '') === String(state.user.company_id || '');
    }
    return false;
  });
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

function defaultView() {
  const ordered = ['dashboard', 'comercial', 'empresas', 'usuarios', 'unidades', 'colaboradores', 'gestao-colaborador', 'epis', 'estoque', 'entregas', 'fichas', 'relatorios', 'configuracao'];
  const view = ordered.find((currentView) => hasPermission(VIEW_PERMISSIONS[currentView]));
  if (!view) {
    console.warn('[RBAC]', {
      rota: 'defaultView',
      perfil_recebido: state.user?.role,
      empresa_id: state.user?.company_id,
      perfis_permitidos: Object.keys(ROLE_PERMISSIONS),
      acesso_negado_motivo: 'nenhuma_view_liberada'
    });
  }
  return view || 'dashboard';
}
const SPA_NAV_SUPPORTED_VIEWS = Object.freeze(['dashboard', 'empresas', 'usuarios', 'unidades', 'colaboradores', 'gestao-colaborador', 'epis', 'estoque']);
const SPA_NAV_CLASSIC_FALLBACK_VIEWS = Object.freeze(['entregas', 'fichas', 'relatorios']);

function setSpaNavigationLoading(active) {
  const container = refs.mainContent || document.getElementById('main-content');
  if (!container) return;
  container.classList.toggle('spa-nav-loading', Boolean(active));
  container.setAttribute('aria-busy', active ? 'true' : 'false');
}

function applySpaNavigationVisibility() {
  const enabled = isSpaNavigationEnabled();
  document.body?.classList.toggle('spa-navigation-enabled', enabled);
  if (refs.spaNavigationIndicator) refs.spaNavigationIndicator.hidden = !enabled;
}

function resolveViewFromLocation() {
  const params = new URLSearchParams(globalThis.location.search);
  return String(params.get('view') || '').trim();
}

function buildNavigationUrl(view) {
  const url = new URL(globalThis.location.href);
  if (view) {
    url.searchParams.set('view', view);
  } else {
    url.searchParams.delete('view');
  }
  return url;
}

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

function showView(view, options = {}) {
  const partial = options.partial !== false;
  const historyMode = options.historyMode || null;
  const currentActiveView = document.querySelector('.view.active')?.id || '';
  const permission = VIEW_PERMISSIONS[view];
  if (permission && !hasPermission(permission)) {
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
  trackInteractiveViewHistory(view);
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
  if (refs.mobileMenuToggle) refs.mobileMenuToggle.hidden = !enabled;
}

function bindMobileUxBehavior() {
  if (globalThis.__EPI_UX_MOBILE_BOUND__) return;
  globalThis.__EPI_UX_MOBILE_BOUND__ = true;

  refs.mobileMenuToggle?.addEventListener('click', () => {
    if (!isUxMobileEnabled()) return;
    if (document.body?.classList.contains('mobile-menu-open')) {
      closeMobileMenu();
      return;
    }
    openMobileMenu();
  });

  refs.menu?.addEventListener('click', (event) => {
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

  safeOn(document, 'epi:viewchange', () => {
    closeMobileMenu();
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
  document.querySelectorAll('.menu-link').forEach((item) => {
    const view = item.dataset.view;
    let visible = hasPermission(VIEW_PERMISSIONS[view]);
    if (['epis', 'colaboradores', 'unidades', 'usuarios'].includes(view)) {
      visible = visible && ['master_admin', 'general_admin', 'registry_admin'].includes(state.user?.role);
    }
    if (['gestao-colaborador', 'estoque', 'entregas', 'fichas'].includes(view)) {
      visible = visible && ['master_admin', 'general_admin', 'registry_admin', 'admin', 'user'].includes(state.user?.role);
    }
    if (view === 'configuracao') {
      visible = visible && hasConfigurationAccess();
    }
    item.style.display = visible ? '' : 'none';
  });
  if (refs.topConfigTrigger) refs.topConfigTrigger.style.display = hasConfigurationAccess() ? '' : 'none';
  if (!hasHardeningAccess() && refs.configFrameworkForm) {
    refs.configFrameworkForm.remove();
    refs.configFrameworkForm = null;
  }
  const companyFormCard = refs.companyForm?.closest('.user-form-card');
  if (companyFormCard) companyFormCard.style.display = hasPermission('companies:create') || hasPermission('companies:update') ? '' : 'none';
  const platformBrandCard = refs.platformBrandForm?.closest('.user-form-card');
  if (platformBrandCard) platformBrandCard.style.display = state.user?.role === 'master_admin' ? '' : 'none';
  refs.profileLabel.textContent = state.user ? roleLabel(state.user.role) : 'Perfil';
  if (refs.loggedUserIdentity) {
    const parts = splitUserName(state.user?.full_name || state.user?.username || '');
    refs.loggedUserIdentity.textContent = [parts.firstName, parts.lastName].filter(Boolean).join(' ').trim();
  }
  refs.companyBadge.innerHTML = state.user?.company_name ? `${companyLogoMarkup({ name: state.user.company_name, logo_type: state.user.logo_type }, 'company-logo company-logo-sm')}<span>${state.user.company_name}<br>${state.user.company_cnpj}</span>` : 'Acesso geral';
}

function populateRoleOptions() {
  const roleMap = {
    master_admin: [['general_admin', 'Administrador Geral'], ['registry_admin', 'Administrador de Registro'], ['admin', 'Administrador Local'], ['user', 'Gestor de EPI'], ['employee', 'Funcionário']],
    general_admin: [['registry_admin', 'Administrador de Registro'], ['admin', 'Administrador Local'], ['user', 'Gestor de EPI'], ['employee', 'Funcionário']],
    registry_admin: [['admin', 'Administrador Local'], ['user', 'Gestor de EPI'], ['employee', 'Funcionário']]
  };
  const roles = roleMap[state.user?.role] || [];
  refs.userRole.innerHTML = roles.map((item) => `<option value="${item[0]}">${item[1]}</option>`).join('');
}

function populateUserFilters() {
  if (!refs.userFilterCompany) return;
  const companies = state.user?.role === 'master_admin' ? state.companies : filterByUserCompany(state.companies);
  const optionsHtml = companies.map((item) => `<option value="${item.id}">${item.name}</option>`).join('');
  refs.userFilterCompany.innerHTML = '<option value="">Todas</option>' + optionsHtml;
  refs.userFilterCompany.value = state.userFilters.company_id;
  refs.userFilterRole.value = state.userFilters.role;
  refs.userFilterStatus.value = state.userFilters.active;
  refs.userFilterSearch.value = state.userFilters.search;
}

function scopedCompaniesForSearch() {
  return state.user?.role === 'master_admin' ? state.companies : filterByUserCompany(state.companies);
}

function populateSearchSelect(select, items, labelBuilder, selectedValue = '', includeAll = true, emptyLabel = 'Todas') {
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
  populateSearchSelect(refs.deliveriesFilterUnit, unitsForSearchByCompany(state.deliveriesFilters.company_id), (item) => item.name, state.deliveriesFilters.unit_id);
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
  populateSearchSelect(refs.deliveriesFilterUnit, unitsForSearchByCompany(state.deliveriesFilters.company_id), (item) => item.name, state.deliveriesFilters.unit_id);
  state.deliveriesFilters.unit_id = String(refs.deliveriesFilterUnit?.value || '').trim();
  renderTables();
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
  unitField.innerHTML = `${lockByOperationalProfile ? '' : '<option value="">Todas</option>'}${units.map(formatUnitOption).join('')}`;
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

function renderUsersSummary() {
  const visible = filteredUsers();
  const admins = visible.filter((item) => ['master_admin', 'general_admin', 'admin'].includes(item.role)).length;
  const active = visible.filter((item) => Number(item.active) === 1).length;
  refs.usersSummary.innerHTML = [
    ['Visíveis', visible.length],
    ['Administradores', admins],
    ['Ativos', active]
  ].map((item) => `<div class="summary-chip"><strong>${item[1]}</strong><span>${item[0]}</span></div>`).join('');
}

function renderCompaniesSummary() {
  if (!refs.companiesSummary) return;
  const visibleCompanies = filterByUserCompany(state.companies);
  const active = visibleCompanies.filter((item) => Number(item.active) === 1).length;
  const nearLimit = visibleCompanies.filter((item) => item.near_limit && Number(item.limit_reached) !== 1).length;
  const blocked = visibleCompanies.filter((item) => Number(item.active) !== 1 || ['suspended', 'expired'].includes(item.license_status)).length;
  refs.companiesSummary.innerHTML = [
    ['Empresas', visibleCompanies.length],
    ['Ativas', active],
    ['Próximas do limite', nearLimit],
    ['Bloqueadas', blocked]
  ].map((item) => `<div class="summary-chip"><strong>${item[1]}</strong><span>${item[0]}</span></div>`).join('');
}

function companyStatusBadges(company) {
  const badges = [renderBadge('status', Number(company.active) === 1 ? 'active' : 'inactive', Number(company.active) === 1 ? 'Empresa ativa' : 'Empresa inativa')];
  
  let licenseTone = 'inactive';
  if (company.license_status === 'active') licenseTone = 'active';
  else if (company.license_status === 'trial') licenseTone = 'warning';
  
  badges.push(renderBadge('status', licenseTone, company.license_status_label || company.license_status));
  if (Number(company.limit_reached) === 1) badges.push(renderBadge('status', 'inactive', 'No limite'));
  else if (company.near_limit) badges.push(renderBadge('status', 'warning', 'próxima do limite'));
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
    ? 'Limite atingido'
    : `${company.available_slots || 0} vaga(s) disponíveis`;
}

function renderCompanyDetails(companyId = null) {
  if (!refs.companyDetails) return;
  const visibleCompanies = filterByUserCompany(state.companies);
  if (!visibleCompanies.length) {
    refs.companyDetails.innerHTML = '<div class="summary-item">Nenhuma empresa disponível.</div>';
    return;
  }
  const selected = visibleCompanies.find((item) => String(item.id) === String(companyId || state.selectedCompanyId)) || visibleCompanies[0];
  state.selectedCompanyId = selected.id;
  const monthly = formatCompanyCurrency(selected.monthly_value);
  const projected = formatCompanyCurrency(selected.projected_monthly_value);
  refs.companyDetails.innerHTML = `
    <div class="company-detail-hero">
      ${companyLogoMarkup(selected, 'company-logo company-logo-lg')}
      <div>
        <strong>${selected.name}</strong>
        <span>${selected.legal_name || '-'}</span>
        <span>CNPJ: ${selected.cnpj}</span>
      </div>
    </div>
    <div class="company-detail-badges">${companyStatusBadges(selected)}</div>
    <div class="company-detail-grid">
      <div class="summary-chip"><strong>${selected.user_count}</strong><span>Usuário possíveis</span></div>
      <div class="summary-chip"><strong>${selected.user_limit}</strong><span>Limite contratado</span></div>
      <div class="summary-chip"><strong>${monthly}</strong><span>Valor mensal atual</span></div>
      <div class="summary-chip"><strong>${projected}</strong><span>Valor projetado</span></div>
      <div class="summary-chip"><strong>${selected.available_slots || 0}</strong><span>Vagas disponíveis</span></div>
    </div>
    <div class="company-detail-list">
      <div class="summary-item"><strong>Plano / licença:</strong> ${planLabel(selected.plan_name) || '-'}</div>
      <div class="summary-item"><strong>Valor unitário:</strong> ${formatCompanyCurrency(selected.unit_price)}</div>
      <div class="summary-item"><strong>Vigência:</strong> ${formatDate(selected.contract_start)} até ${formatDate(selected.contract_end)}</div>
      <div class="summary-item"><strong>Aditivo contratual:</strong> ${Number(selected.addendum_enabled || 0) === 1 ? 'Ativo' : 'Inativo'}</div>
      <div class="summary-item"><strong>Observações comerciais:</strong> ${selected.commercial_notes || '-'}</div>
    </div>
    ${canAccessCommercialArea() ? `<div class="action-group"><button class="ghost" type="button" data-company-view-contract="${selected.id}">Visualizar contrato</button></div>` : ''}`;
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
  if (Number(company.active) !== 1) return { label: 'Empresa inativa', tone: 'inactive' };
  if (company.license_status === 'expired') return { label: 'Contrato expirado', tone: 'inactive' };
  if (company.license_status === 'suspended') return { label: 'Contrato suspenso', tone: 'inactive' };
  if (Number(company.limit_reached) === 1) return { label: 'No limite', tone: 'inactive' };
  if (company.near_limit) return { label: 'próxima do limite', tone: 'warning' };
  return { label: 'Saudável', tone: 'active' };
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
  return `<div class="commercial-card"><div class="commercial-row">${companyLogoMarkup(item, 'company-logo company-logo-sm')}<div><strong>${item.name}</strong><span>${usage} Usuários</span><span>${monthly} atual | ${projected} projetado</span><span>${planLabel(item.plan_name)}</span></div><span class="badge badge-status-${risk.tone}">${risk.label}</span></div>${commercialActions(item)}</div>`;
}

function renderCommercialAlertCard(item) {
  const reasons = [];
  if (Number(item.limit_reached) === 1) reasons.push('limite contratado atingido');
  else if (item.near_limit) reasons.push('próxima do limite contratado');
  if (['suspended', 'expired'].includes(item.license_status)) reasons.push(`licença ${item.license_status_label.toLowerCase()}`);
  if (Number(item.active) !== 1) reasons.push('empresa inativa');
  const tone = commercialAlertTone(item);
  return `<div class="commercial-card"><div class="alert-item ${tone}"><strong>${item.name}</strong><div>${reasons.join(' | ')}</div></div>${commercialActions(item)}</div>`;
}

function renderCommercialExpiringCard(entry) {
  const { item, days } = entry;
  const badgeTone = days <= 7 ? 'inactive' : 'warning';
  const badgeLabel = days <= 7 ? 'Urgente' : 'Acompanhar';
  return `<div class="commercial-card"><div class="commercial-row">${companyLogoMarkup(item, 'company-logo company-logo-sm')}<div><strong>${item.name}</strong><span>Vence em ${formatDate(item.contract_end)}</span><span>${days} dia(s) restantes</span></div><span class="badge badge-status-${badgeTone}">${badgeLabel}</span></div>${commercialActions(item)}</div>`;
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
  if (!canManageCompanies) {
    return `<div class="action-group"><button class="ghost" data-company-details="${item.id}">Visualizar detalhes</button></div>`;
  }
  const toggleMode = Number(item.active) === 1 ? 0 : 1;
  const toggleLabel = Number(item.active) === 1 ? 'Inativar' : 'Ativar';
  const commercialAction = canAccessCommercialArea()
    ? `<button class="ghost" data-company-commercial="${item.id}">Configurar licença</button>`
    : '';
  return `<div class="action-group"><button class="ghost" data-company-details="${item.id}">Visualizar detalhes</button><button class="ghost" data-company-edit="${item.id}">Editar</button><button class="ghost" data-company-logo="${item.id}">Alterar logotipo</button>${commercialAction}<button class="ghost" data-company-toggle="${item.id}" data-company-active="${toggleMode}">${toggleLabel}</button></div>`;
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
  const tableStylesheet = 'table{border-collapse:collapse;width:100%;font-family:Segoe UI,Arial,sans-serif}th,td{border:1px solid #cfc7bb;padding:8px;text-align:left;vertical-align:top}th{background:#f6d8c8}';
  const headerCells = header.map((item) => `<th>${item}</th>`).join('');
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
  const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Histórico Comercial</title></head><body><h1>Histórico Comercial</h1><p>Filtros: ${filters}</p><table><thead><tr><th>Empresa</th><th>ação</th><th>Responsável</th><th>Data</th><th>Resumo</th><th>Detalhes</th></tr></thead><tbody>${rowsHtml}</tbody></table></body></html>`;
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
  return `
      <tr class="${selectedId === String(item.id) ? 'selected-row' : ''}">
        <td><div class="company-cell"><strong>${item.name}</strong><span>${item.legal_name || '-'}</span></div></td>
        <td><div class="company-cell"><strong>${item.cnpj}</strong><span>${item.plan_name || '-'}</span></div></td>
        <td><div class="company-cell">${companyStatusBadges(item)}<span>Vigência: ${formatDate(item.contract_start)} até ${formatDate(item.contract_end)}</span></div></td>
        <td><div class="company-logo-slot">${companyLogoMarkup(item, 'company-logo company-logo-sm')}</div></td>
        <td><div class="company-cell"><strong>${item.user_count}</strong><span>${Number(item.limit_reached) === 1 ? 'Limite atingido' : `${item.available_slots || 0} vaga(s) dispon\u00edveis`}</span></div></td>
        <td><div class="company-cell"><strong>${item.user_limit}</strong><span>${Number(item.monthly_value || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</span></div></td>
        <td><div class="company-cell"><strong>${item.user_count}</strong><span>${formatCompanyAvailabilityText(item)}</span></div></td>
        <td><div class="company-cell"><strong>${item.user_limit}</strong><span>${formatCompanyCurrency(item.monthly_value)}</span></div></td>
        <td>${actions}</td>
      </tr>`;
}

function renderCompanies() {
  if (!refs.companiesTable) return;
  const visibleCompanies = filterByUserCompany(state.companies);
  const selectedId = String(state.selectedCompanyId || visibleCompanies[0]?.id || '');
  refs.companiesTable.innerHTML = visibleCompanies.map((item) => formatCompanyRow(item, selectedId)).join('') || '<tr><td colspan="7">Sem empresas disponíveis.</td></tr>';
}

function resetCompanyForm() {
  if (!refs.companyForm) return;
  state.editingCompanyId = null;
  refs.companyForm.reset();
  setCompanyFieldValue('id', '');
  setCompanyFieldValue('active', '1');
  setCompanyFieldValue('logo_type', '');
  if (refs.companyLogoFile) refs.companyLogoFile.value = '';
  renderCompanyLogoPreview('');
  renderCompanyDetails();
}

function startEditCompany(companyId, options = {}) {
  if (!hasPermission('companies:update')) return;
  const company = state.companies.find((item) => String(item.id) === String(companyId));
  if (!company || !refs.companyForm) return;
  state.editingCompanyId = company.id;
  state.selectedCompanyId = company.id;
  setCompanyFieldValue('id', company.id);
  setCompanyFieldValue('name', company.name || '');
  setCompanyFieldValue('legal_name', company.legal_name || '');
  setCompanyFieldValue('cnpj', company.cnpj || '');
  setCompanyFieldValue('logo_type', company.logo_type || '');
  setCompanyFieldValue('active', String(Number(company.active || 1)));
  if (refs.companyLogoFile) refs.companyLogoFile.value = '';
  renderCompanyLogoPreview(company.logo_type || '');
  renderCompanies();
  renderCompanyDetails(company.id);
  refs.companyForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
  if (options.focusLogo && refs.companyLogoFile) {
    setTimeout(() => refs.companyLogoFile.click(), 120);
  }
}

function openCompanyLogoEditor(companyId) {
  startEditCompany(companyId, { focusLogo: true });
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
      logo_type: readCompanyFieldValue('logo_type', currentCompany.logo_type || ''),
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

async function loadBootstrap() {
  try {
    updatePhase3ContextStatus('dashboard', 'loading', 'Atualizando...');
    const payload = await api(`/api/bootstrap?${actorQuery()}`);
    state.platformBrand = { ...DEFAULT_PLATFORM_BRAND, ...payload.platform_brand };
    state.commercialSettings = cloneCommercialSettings(payload.commercial_settings || DEFAULT_COMMERCIAL_SETTINGS);
    state.companies = Array.isArray(payload.companies) ? payload.companies : [];
    state.companyAuditLogs = payload.company_audit_logs || [];
    state.fichaAuditLogs = payload.ficha_audit_logs || [];
    state.users = Array.isArray(payload.users) ? payload.users : [];
    state.units = Array.isArray(payload.units) ? payload.units : [];
    state.employees = Array.isArray(payload.employees) ? payload.employees : [];
    state.employeeMovements = payload.employee_movements || [];
    state.epis = Array.isArray(payload.epis) ? payload.epis : [];
    state.deliveries = Array.isArray(payload.deliveries) ? payload.deliveries : [];
    state.alerts = Array.isArray(payload.alerts) ? payload.alerts : [];
    state.permissions = normalizePermissions(state.user, payload.permissions || state.permissions);
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
      const lowStockPayload = await api(`/api/stock/low?${actorQuery()}`);
      state.lowStock = lowStockPayload.items || [];
      const requestsPayload = await api(`/api/requests?${actorQuery()}`);
      state.requests = requestsPayload.items || [];
      await loadStockEpis();
    } else {
      state.lowStock = [];
      state.requests = [];
      state.stockEpis = [];
    }
    if (hasPermission('fichas:view')) {
      const fichasPayload = await api(`/api/fichas?${actorQuery()}`);
      state.fichasPeriods = fichasPayload.items || [];
    } else {
      state.fichasPeriods = [];
    }
    if (hasConfigurationAccess()) {
      const rulesPayload = await api(`/api/configuration-rules?${actorQuery()}`);
      state.configurationRules = Array.isArray(rulesPayload.rules) ? rulesPayload.rules : [];
      if (hasHardeningAccess()) {
        const frameworkPayload = await api(`/api/configuration-framework?${actorQuery()}`);
        state.configurationFramework = { ...deepClone(DEFAULT_CONFIGURATION_FRAMEWORK), ...(frameworkPayload.framework || {}) };
      } else {
        state.configurationFramework = deepClone(DEFAULT_CONFIGURATION_FRAMEWORK);
      }
    } else {
      state.configurationRules = [];
      state.configurationFramework = deepClone(DEFAULT_CONFIGURATION_FRAMEWORK);
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
  populateSelect('delivery-company', companies, (item) => `${item.name} - ${item.cnpj}`);
  populateSelect('stock-company', companies, (item) => `${item.name} - ${item.cnpj}`);
  populateSelect('delivery-unit-filter', state.units, (item) => `${item.name} - ${unitTypeLabel(item.unit_type)}`, 'id', true, 'Todas as Unidades');
  populateSelect('report-company', companies, (item) => item.name, 'id', true, 'Todas');
  populateSelect('employee-unit', state.units, (item) => `${item.name} - ${unitTypeLabel(item.unit_type)}`);
  populateSelect('movement-target-unit-id', state.units, (item) => `${item.name} - ${unitTypeLabel(item.unit_type)}`);
  populateSelect('movement-employee-id', state.employees, (item) => `${item.employee_id_code} - ${item.name}`);
  populateSelect('delivery-employee', state.employees, (item) => `${item.employee_id_code} - ${item.name}`);
  populateSelect('delivery-epi', state.epis, (item) => `${item.name} - ${item.unit_measure}`);
  populateSelect('stock-unit', state.units, (item) => `${item.name} - ${unitTypeLabel(item.unit_type)}`);
  populateSelect('stock-epi', state.epis, (item) => `${item.name} - ${item.unit_measure}`);
  populateSelect('ficha-employee', state.employees, (item) => `${item.employee_id_code} - ${item.name}`);
  populateSelect('report-unit', state.units, (item) => item.name, 'id', true, 'Todas');
  populateSelect('report-epi', state.epis, (item) => item.name, 'id', true, 'Todos');
  populateSelect('report-employee', state.employees, (item) => `${item.employee_id_code} - ${item.name}`, 'id', true, 'Todos os colaboradores');
  const sectors = [...new Set(filterByUserCompany(state.employees).map((item) => item.sector))].sort((a, b) => a.localeCompare(b));
  document.getElementById('report-sector').innerHTML = '<option value="">Todos</option>' + sectors.map((item) => `<option value="${item}">${item}</option>`).join('');
  const defaultCompanyId = companies[0]?.id ? String(companies[0].id) : '';
  ['unit-company', 'employee-company', 'epi-company', 'delivery-company', 'stock-company'].forEach((fieldId) => {
    const field = document.getElementById(fieldId);
    if (field && !field.value && defaultCompanyId) field.value = defaultCompanyId;
  });
  populateLinkedEmployeeOptions();
  syncEmployeeUnitOptions();
  syncEpiUnitOptions();
  syncDeliveryOptions();
  syncStockOptions();
  syncEmployeeUnitOptions();
  syncReportOptions();
  populateStockProtectionFilter();
}

function renderStats() {
  const cards = [['Empresas', state.user?.role === 'master_admin' ? state.companies.length : filterByUserCompany(state.companies).length], ['Colaboradores', filterByUserCompany(state.employees).length], ['EPIs', filterByUserCompany(state.epis).length], ['Entregas', filterByUserCompany(state.deliveries).length], ['Alertas', (state.alerts || []).length]];
  if (state.user?.role === 'master_admin' && state.dbPoolStatus?.initialized) {
    cards.push(['Pool DB (uso)', `${state.dbPoolStatus.in_use}/${state.dbPoolStatus.maxconn}`]);
    cards.push(['Pool DB (livres)', `${state.dbPoolStatus.available}`]);
  }
  refs.statsGrid.innerHTML = cards.map((item) => `<article class="stat-card"><div class="stat-label">${item[0]}</div><div class="stat-value">${item[1]}</div></article>`).join('');
  renderPhase3SummaryCards(refs.phase3ColaboradoresSummary, [
    { label: 'Total base', value: filterByUserCompany(state.employees).length },
    { label: 'Com e-mail', value: filterByUserCompany(state.employees).filter((item) => String(item.email || '').trim()).length },
    { label: 'Com WhatsApp', value: filterByUserCompany(state.employees).filter((item) => String(item.whatsapp || '').trim()).length }
  ]);
  renderPhase3SummaryCards(refs.phase3GestaoSummary, [
    { label: 'Vínculos ativos', value: filterByUserCompany(state.employees).length },
    { label: 'Movimentações', value: filterByUserCompany(state.employeeMovements || []).length },
    { label: 'Unidades', value: filterByUserCompany(state.units).length }
  ]);
  renderPhase3SummaryCards(refs.phase3EpisSummary, [
    { label: 'Catálogo', value: filterByUserCompany(state.epis).length },
    { label: 'Com foto', value: filterByUserCompany(state.epis).filter((item) => String(item.epi_photo_data || '').trim()).length },
    { label: 'Com validade CA', value: filterByUserCompany(state.epis).filter((item) => String(item.ca_expiry || '').trim()).length }
  ]);
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
  const requiresCompany = ['general_admin', 'registry_admin', 'admin', 'user', 'employee'].includes(selectedRole);
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
    actions.push(`<button class="ghost" data-user-edit="${target.id}">Editar</button>`);
  }
}

function addPromoteButtons(actions, target) {
  if (canPromoteToAdmin(target)) {
    actions.push(`<button class="ghost" data-user-promote-admin="${target.id}">Tornar Administrador</button>`);
  }
  if (canPromoteToGeneralAdmin(target)) {
    actions.push(`<button class="ghost" data-user-promote-general="${target.id}">Tornar Adm. Geral</button>`);
  }
  if (canDemoteGeneralAdmin(target)) {
    actions.push(`<button class="ghost" data-user-demote-general="${target.id}">Remover do Geral</button>`);
  }
  if (canDemoteAdmin(target)) {
    actions.push(`<button class="ghost" data-user-demote-admin="${target.id}">Rebaixar para Usuário</button>`);
  }
}

function addPasswordButtons(actions, target) {
  if (canManageUser(target)) {
    actions.push(
      `<button class="ghost" data-user-temp-password="${target.id}">Gerar senha provisória</button>`,
      `<button class="ghost" data-user-generate-copy-password="${target.id}">Gerar e copiar senha</button>`
    );
    if (Number(target.force_password_change || 0) !== 1) {
      actions.push(`<button class="ghost" data-user-force-password-change="${target.id}">Forçar troca da senha novamente</button>`);
    }
  }
}

function addManagementButtons(actions, target) {
  if (canManageUser(target)) {
    actions.push(
      `<button class="ghost" data-user-copy-email="${target.id}">Copiar e-mail</button>`,
      `<button class="ghost" data-user-copy-whatsapp="${target.id}">Copiar WhatsApp</button>`
    );
  }
  if (canToggleActive(target)) {
    const label = Number(target.active) === 1 ? 'Desativar Usuário' : 'Ativar Usuário';
    actions.push(`<button class="ghost" data-user-toggle="${target.id}">${label}</button>`);
  }
  if (canDeleteUser(target)) {
    actions.push(`<button class="ghost" data-user-delete="${target.id}">Remover</button>`);
  }
}

function addEmployeeButtons(actions, target) {
  if (target.role === 'employee' && target.employee_access_token) {
    actions.push(`<button class="ghost" data-user-employee-qr="${target.id}">QR Acesso Externo</button>`);
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

async function deleteUser(userId) {
  if (!globalThis.confirm('Deseja remover este Usuário')) return;
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

function matchesDashboardQuery(values = []) {
  const query = String(state.dashboardFilters?.query || '').trim().toLowerCase();
  if (!query) return true;
  const haystack = values.map((item) => String(item || '').toLowerCase()).join(' ');
  return haystack.includes(query);
}

function renderAlerts() {
  const items = (state.alerts || []).filter((item) => matchesDashboardQuery([item.title, item.description, item.type]));
  refs.alertsList.innerHTML = items.map((item) => `<div class="alert-item ${item.type}"><strong>${item.title}</strong><div>${item.description}</div></div>`).join('') || '<div class="summary-item">Sem alertas para o filtro atual.</div>';
}

function renderLatestDeliveries() {
  const items = filterByUserCompany(state.deliveries)
    .filter((item) => matchesDashboardQuery([item.employee_name, item.epi_name, item.company_name, item.quantity_label]))
    .slice(0, 5);
  refs.latestDeliveries.innerHTML = items.map((item) => `<div class="list-item"><strong>${item.employee_name}</strong><div>${item.epi_name} - ${item.quantity} ${item.quantity_label}(s)</div><small>${item.company_name}  ${formatDate(item.delivery_date)}</small></div>`).join('') || '<div class="summary-item">Sem entregas para o filtro atual.</div>';
}

function dashboardInteractiveEmptyMessage(message) {
  return `<div class="dashboard-chart-empty">${message}</div>`;
}

function buildDashboardMiniBars(items, { labelKey = 'label', valueKey = 'value' } = {}) {
  if (!Array.isArray(items) || !items.length) return dashboardInteractiveEmptyMessage('Sem dados para o filtro atual.');
  const max = Math.max(...items.map((item) => Number(item?.[valueKey] || 0)), 0);
  if (max <= 0) return dashboardInteractiveEmptyMessage('Sem dados para o filtro atual.');
  return `<div class="dashboard-mini-bars">${items.map((item) => {
    const value = Number(item?.[valueKey] || 0);
    const pct = Math.max(4, Math.round((value / max) * 100));
    const label = escapeHtml(item?.[labelKey] || '-');
    return `<div class="dashboard-mini-bar-row">
      <div class="dashboard-mini-bar-label"><span>${label}</span><strong>${value}</strong></div>
      <div class="dashboard-mini-bar-track"><div class="dashboard-mini-bar-fill" style="width:${pct}%"></div></div>
    </div>`;
  }).join('')}</div>`;
}

function renderDashboardInterativo() {
  if (!refs.dashboardInteractivePanel || !refs.dashboardInteractiveKpis) return;
  const enabled = isDashboardInterativoEnabled();
  refs.dashboardInteractivePanel.hidden = !enabled;
  refs.dashboardInteractiveLoading.hidden = true;
  refs.dashboardInteractiveError.hidden = true;
  if (!enabled) return;
  try {
    refs.dashboardInteractiveLoading.hidden = false;
    const scopedDeliveries = filterByUserCompany(state.deliveries || []);
    const scopedEmployees = filterByUserCompany(state.employees || []);
    const scopedEpis = filterByUserCompany(state.epis || []);
    const scopedStockLow = state.lowStock || [];
    const deliveriesThisMonth = scopedDeliveries.filter((item) => String(item.delivery_date || '').slice(0, 7) === new Date().toISOString().slice(0, 7)).length;
    const devolvidas = scopedDeliveries.filter((item) => String(item.returned_date || '').trim()).length;
    const kpis = [
      { label: 'Entregas (mês)', value: deliveriesThisMonth },
      { label: 'Entregas devolvidas', value: devolvidas },
      { label: 'EPIs cadastrados', value: scopedEpis.length },
      { label: 'Colaboradores ativos', value: scopedEmployees.length }
    ];
    refs.dashboardInteractiveKpis.innerHTML = kpis.map((item) => `<article class="dashboard-kpi-card"><span>${item.label}</span><strong>${item.value}</strong></article>`).join('');

    const deliveriesByCompany = scopedDeliveries.reduce((acc, item) => {
      const key = String(item.company_name || 'Sem empresa');
      acc.set(key, (acc.get(key) || 0) + 1);
      return acc;
    }, new Map());
    const companySeries = Array.from(deliveriesByCompany.entries())
      .map(([label, value]) => ({ label, value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 8);

    const lowByUnit = scopedStockLow.reduce((acc, item) => {
      const key = String(item.unit_name || 'Sem unidade');
      acc.set(key, (acc.get(key) || 0) + 1);
      return acc;
    }, new Map());
    const lowSeries = Array.from(lowByUnit.entries())
      .map(([label, value]) => ({ label, value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 8);

    if (refs.dashboardChartDeliveriesCompany) {
      refs.dashboardChartDeliveriesCompany.innerHTML = buildDashboardMiniBars(companySeries);
    }
    if (refs.dashboardChartLowStockUnit) {
      refs.dashboardChartLowStockUnit.innerHTML = buildDashboardMiniBars(lowSeries);
    }
    refs.dashboardInteractiveLoading.hidden = true;
  } catch (error) {
    reportNonCriticalError('dashboard interativo render failed', error);
    refs.dashboardInteractiveLoading.hidden = true;
    refs.dashboardInteractiveError.hidden = false;
  }
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
    return true;
  });
}

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

function buildEmployeeRow(item, canManageRecords) {
  const actions = canManageRecords ? `<div class="action-group"><button class="ghost" data-employee-edit="${item.id}">Editar</button><button class="ghost" data-employee-delete="${item.id}">Remover</button></div>` : '-';
  const allocation = item.unit_allocation_type === 'temporary' ? 'Temporário' : 'Principal';
  const preferredLabel = String(item.preferred_contact_channel || '').toLowerCase() === 'email' ? 'E-mail' : 'WhatsApp';
  const contact = [item.whatsapp ? `WhatsApp: ${item.whatsapp}` : '', item.email ? `E-mail: ${item.email}` : '', `Preferido: ${preferredLabel}`].filter(Boolean).join('<br>') || '-';
  return `<tr><td>${item.company_name}</td><td>${item.employee_id_code}</td><td>${item.name}</td><td>${contact}</td><td>${item.sector}</td><td>${item.role_name}</td><td>${item.current_unit_name || item.unit_name}</td><td>${allocation}</td><td>-</td><td>${actions}</td></tr>`;
}

function buildEpiRow(item, canManageEpiRecords) {
  const actions = canManageEpiRecords ? `<div class="action-group"><button class="ghost" data-epi-edit="${item.id}">Editar</button><button class="ghost" data-epi-delete="${item.id}">Remover</button></div>` : '-';
  const scopeLabel = item.scope_label
    || (String(item.scope_type || '').toUpperCase() === 'GLOBAL'
      ? 'Todas as Unidades'
      : `${item.unit_name || '-'}${Number(item.is_joint_venture || 0) === 1 ? ' (Joint Venture)' : ''}`);
  return `<tr><td>${item.company_name}</td><td>${scopeLabel}</td><td>${item.name}</td><td>${item.purchase_code}</td><td>${item.sector}</td><td>${item.epi_section || '-'}</td><td>${item.manufacturer || '-'}</td><td>${item.supplier_company || '-'}</td><td>${item.active_joinventure || '-'}</td><td>${item.unit_measure}</td><td>${actions}</td></tr>`;
}

function buildDeliveryRow(item) {
  return `<tr><td>${item.company_name}</td><td>${item.employee_id_code}</td><td>${item.employee_name}</td><td>${item.epi_name}</td><td>${item.quantity}</td><td>${item.quantity_label}</td><td>${formatDate(item.delivery_date)}</td></tr>`;
}

function formatUnitTableRow(item, canManageUnitRecords) {
  const actions = canManageUnitRecords ? `<div class="action-group"><button class="ghost" data-unit-edit="${item.id}">Editar</button><button class="ghost" data-unit-delete="${item.id}">Remover</button></div>` : '-';
  return `<tr><td>${item.company_name}</td><td>${item.name}</td><td>${unitTypeLabel(item.unit_type)}</td><td>${item.city}</td><td>${actions}</td></tr>`;
}

function renderTables() {
  const canManageRecords = ['master_admin', 'general_admin', 'registry_admin'].includes(state.user?.role);
  const canManageStructuralRecords = ['general_admin', 'registry_admin'].includes(state.user?.role);
  const filteredUnits = applyUnitsFilters(filterByUserCompany(state.units));
  const filteredEmployeesBase = applyEmployeesFilters(filterByUserCompany(state.employees), 'employees');
  const filteredEmployeesOps = applyEmployeesFilters(filterByUserCompany(state.employees), 'ops');
  const filteredEpis = applyEpisFilters(filterByUserCompany(state.epis));
  const filteredDeliveries = applyDeliveriesFilters(filterByUserCompany(state.deliveries));
  refs.usersTable.innerHTML = filteredUsers().map((item) => `<tr><td>${item.full_name}</td><td>${renderBadge('role', item.role, roleLabel(item.role))}</td><td>${userStatusBadges(item)}</td><td>${item.company_name || 'Sistema'}</td><td>${userActionButtons(item)}</td></tr>`).join('') || '<tr><td colspan="5">Sem Usuários.</td></tr>';
  refs.unitsTable.innerHTML = filteredUnits.map((item) => formatUnitTableRow(item, canManageStructuralRecords)).join('') || '<tr><td colspan="5">Sem unidades.</td></tr>';
  refs.employeesTable.innerHTML = filteredEmployeesBase.map((item) => buildEmployeeRow(item, canManageRecords)).join('') || '<tr><td colspan="10">Sem colaboradores.</td></tr>';
  if (refs.employeesOpsTable) refs.employeesOpsTable.innerHTML = filteredEmployeesOps.map((item) => buildEmployeeRow(item, canManageRecords)).join('') || '<tr><td colspan="10">Sem colaboradores.</td></tr>';
  refs.episTable.innerHTML = filteredEpis.map((item) => buildEpiRow(item, canManageStructuralRecords)).join('') || '<tr><td colspan="11">Sem EPIs.</td></tr>';
  refs.deliveriesTable.innerHTML = filteredDeliveries.map(buildDeliveryRowWithDevolution).join('') || '<tr><td colspan="9">Sem entregas.</td></tr>';
  renderApprovedEpis();
  if (isPhase3ModernUiEnabled()) {
    updatePhase3ContextStatus('colaboradores', 'success', `${filteredEmployeesBase.length} colaborador(es) visível(is)`);
    updatePhase3ContextStatus('gestao-colaborador', 'success', `${filteredEmployeesOps.length} vínculo(s) no filtro`);
    updatePhase3ContextStatus('epis', 'success', `${filteredEpis.length} EPI(s) no filtro`);
  }
}

function renderApprovedEpis() {
  if (!refs.approvedEpiTable) return;
  const byName = String(refs.approvedEpiSearchName?.value || '').toLowerCase();
  const byProtection = String(refs.approvedEpiSearchProtection?.value || '').toLowerCase();
  const byCa = String(refs.approvedEpiSearchCa?.value || '').toLowerCase();
  const byManufacturer = String(refs.approvedEpiSearchManufacturer?.value || '').toLowerCase();
  const bySection = String(refs.approvedEpiSearchSection?.value || '').toLowerCase();
  const rows = filterByUserCompany(state.epis).filter((item) =>
    String(item.name || '').toLowerCase().includes(byName)
    && String(item.sector || '').toLowerCase().includes(byProtection)
    && String(item.ca || '').toLowerCase().includes(byCa)
    && String(item.manufacturer || '').toLowerCase().includes(byManufacturer)
    && String(item.epi_section || '').toLowerCase().includes(bySection)
  );
  refs.approvedEpiTable.innerHTML = rows.map((item) => `<tr>
    <td>${item.name || '-'}</td>
    <td>${item.manufacturer || '-'}</td>
    <td>${item.model_reference || '-'}</td>
    <td>${item.ca || '-'}</td>
    <td>${formatDate(item.ca_expiry)}</td>
    <td>${Number(item.manufacturer_validity_months || 0)}</td>
    <td>${item.sector || '-'}</td>
    <td>${item.epi_section || '-'}</td>
    <td>${item.epi_photo_data ? `<img src="${item.epi_photo_data}" alt="Foto ${item.name}" style="width:56px;height:56px;object-fit:cover;border-radius:6px;">` : '-'}</td>
    <td>${item.manufacturer_recommendations || '-'}</td>
  </tr>`).join('') || '<tr><td colspan="10">Sem EPIs aprovados para os filtros informados.</td></tr>';
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
  const protectionHtml = protectionOptions.map((value) => `<option value="${value}">${value}</option>`).join('');
  refs.stockFilterProtection.innerHTML = `<option value="">Todas</option>${protectionHtml}`;
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

function formatStockEpiRow(item) {
  return `<tr>
    <td>${item.name}</td>
    <td>${item.sector || '-'}</td>
    <td>${item.epi_section || '-'}</td>
    <td>${item.manufacturer || '-'}</td>
    <td>${item.ca || '-'}</td>
    <td>${item.unit_name || '-'}</td>
    <td>${item.stock} ${item.unit_measure}(s)</td>
    <td>${Number(item.minimum_stock ?? 0)}</td>
  </tr>`;
}

function renderStockEpis() {
  if (!refs.stockEpisTable) return;
  const rows = state.stockEpis || [];
  refs.stockEpisTable.innerHTML = rows.map(formatStockEpiRow).join('') || '<tr><td colspan="8">Nenhum EPI encontrado para os filtros.</td></tr>';
  renderPhase3SummaryCards(refs.phase3EstoqueSummary, [
    { label: 'Itens filtrados', value: rows.length },
    { label: 'Estoque baixo', value: (state.lowStock || []).length },
    { label: 'Solicitações', value: (state.requests || []).length }
  ]);
  updatePhase3ContextStatus('estoque', 'success', `${rows.length} item(ns) listado(s)`);
}

function selectedStockEpi() {
  const epiField = document.getElementById('stock-epi');
  const selectedId = String(epiField?.value || '');
  if (!selectedId) return null;
  return (state.stockEpis || []).find((item) => String(item.id) === selectedId)
    || filterByUserCompany(state.epis).find((item) => String(item.id) === selectedId)
    || null;
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
    list.innerHTML = '<div class="summary-item">Nenhum EPI encontrado com esse nome/fabricante na unidade selecionada.</div>';
    return;
  }
  list.innerHTML = source.slice(0, 40).map((item) => {
    const summary = `${item.name || '-'} | Fab: ${item.manufacturer || '-'} | CA: ${item.ca || '-'} | Proteção: ${item.sector || '-'} | Tam: ${item.size || item.glove_size || item.uniform_size || 'N/A'} | Saldo: ${item.stock || 0}`;
    return `<button type="button" class="ghost stock-epi-search-item" data-stock-epi-pick="${item.id}">${summary}</button>`;
  }).join('') || '<div class="summary-item">Digite nome e/ou fabricante para buscar o EPI.</div>';
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

function renderLowStock() {
  if (!refs.stockLowList) return;
  const items = state.lowStock || [];
  refs.stockLowList.innerHTML = items.map((item) => {
    const severity = String(item.severity || 'warning');
    const badge = severity === 'critical' ? 'Crítico' : (severity === 'danger' ? 'Alto' : 'Moderado');
    return `<div class="summary-item"><strong>${item.company_name} / ${item.unit_name}</strong><div>${item.epi_name}: ${item.stock} ${item.unit_measure}(s) (mí­nimo ${item.minimum_stock})</div><small>Criticidade: ${badge}</small></div>`;
  }).join('') || '<div class="summary-item">Sem itens com estoque baixo.</div>';
}

function renderRequests() {
  if (!refs.requestsList) return;
  const items = state.requests || [];
  refs.requestsList.innerHTML = items.map((item) => `<div class="summary-item"><strong>#${item.id} - ${item.employee_name}</strong><div>${item.epi_name} - Tam: ${item.size || '-'} - ${item.quantity} ${item.unit_measure}(s)</div></div>`).join('') || '<div class="summary-item">Sem Crítico solicitações pendentes.</div>';
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
    const allUnitsOption = allowAllUnitsScope ? `<option value="${EPI_ALL_UNITS_VALUE}">Todas as Unidades</option>` : '';
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
    if (hint) hint.textContent = `Unidade travada pela Joint Venture ativa: ${selected.name}.`;
  } else {
    unitField.disabled = isOperationalProfile();
    if (!unitField.value && !isOperationalProfile() && canUseEpiAllUnitsScope()) unitField.value = EPI_ALL_UNITS_VALUE;
    if (hint) hint.textContent = 'Sem Joint Venture ou Unidade Única ativa: Você pode usar "Todas as Unidades" para aprovar o EPI em nÍvel de empresa.';
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
    const unitLabel = unit ? unit.name : 'Sem unidade definida';
    const token = activeJoinventureToken(entry);
    return `<button class="ghost" type="button" data-joinventure-remove="${token}">${entry.name} (${unitLabel}) - Apagar</button>`;
  }).join('') || '<span class="hint">Nenhuma JoinVenture cadastrada ou Unidade Única.</span>';
  const previous = parseActiveJoinventureToken(activeSelect.value);
  activeSelect.innerHTML = '<option value="">Sem Joint Venture ou Unidade Única ativa (EPI geral)</option>' + values.map(formatActiveJoinventureOption).join('');
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
  setFormSubmitLabel('unit-form', 'Atualizar unidade');
  showView('unidades');
}

function startEditEmployee(employeeId) {
  const item = state.employees.find((employee) => String(employee.id) === String(employeeId));
  const form = document.getElementById('employee-form');
  if (!item || !form) return;
  form.elements.id.value = item.id;
  form.elements.company_id.value = item.company_id;
  syncEmployeeUnitOptions();
  form.elements.unit_id.value = item.unit_id || '';
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

async function deleteRegistryEntity(path, entityId, permission, message) {
  if (!requirePermission(permission)) return;
  if (!confirm(message)) return;
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
  if (!lockByOperationalProfile && unitFilterField && !String(unitFilterField.value || '').trim() && unitOptions.length) {
    unitFilterField.value = String(unitOptions[0].id);
  }
  
  companyField.disabled = lockByOperationalProfile;
  if (unitHint) unitHint.style.display = lockByOperationalProfile ? 'block' : 'none';
  
  const unitFilter = lockByOperationalProfile
    ? String(operationalUnitId || '__NO_UNIT__')
    : String(unitFilterField?.value || '');
  
  const search = String(searchField?.value || '').trim().toLowerCase();
  
  const employees = getFilteredDeliveryEmployees(companyId, unitFilter, search);
  populateDeliveryEmployeeField(employeeField, employees);
  populateDeliveryEpiField(epiField, getFilteredDeliveryEpis(companyId, unitFilter));
  syncDeliveryQrSessionOwner({ warn: false });
  clearDeliveryStockItemSelection();
  void loadDeliveryUnitEpis(companyId, unitFilter);
}

function clearDeliveryStockItemSelection() {
  const stockItemIdField = document.getElementById('delivery-stock-item-id');
  const stockCodeField = document.getElementById('delivery-stock-item-code');
  const stockQrHiddenField = document.getElementById('delivery-stock-qr-code');
  if (stockItemIdField) stockItemIdField.value = '';
  if (stockCodeField) stockCodeField.value = '';
  if (stockQrHiddenField) stockQrHiddenField.value = '';
}
  

function populateUnitFilterField(unitFilterField, lockByOperationalProfile, lockUnitByProfile, unitOptions) {
  if (!unitFilterField) return;
  const previous = String(unitFilterField.value || '');
  unitFilterField.innerHTML = `${lockByOperationalProfile ? '' : '<option value="">Todas as Unidades</option>'}${unitOptions.map(formatUnitOption).join('')}`;
  if (lockUnitByProfile && unitOptions.length) {
    unitFilterField.value = String(unitOptions[0].id);
  } else if (lockByOperationalProfile && !unitOptions.length) {
    unitFilterField.innerHTML = '<option value="">Sem unidade operacional ativa</option>';
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
    const payload = await api(`/api/stock/epis?${params.toString()}`);
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

function populateDeliveryEmployeeField(employeeField, employees) {
  const previousValue = String(employeeField.value || '').trim();
  const baseOptions = employees.map((item) => `<option value="${item.id}">${item.employee_id_code} - ${item.name}</option>`);
  const hasPreviousInList = previousValue && employees.some((item) => String(item.id) === previousValue);
  if (previousValue && !hasPreviousInList) {
    const selectedEmployee = state.employees.find((item) => String(item.id) === previousValue);
    if (selectedEmployee) {
      baseOptions.unshift(`<option value="${selectedEmployee.id}">${selectedEmployee.employee_id_code} - ${selectedEmployee.name}</option>`);
    }
  }
  employeeField.innerHTML = baseOptions.join('');
  if (previousValue && Array.from(employeeField.options || []).some((option) => String(option.value) === previousValue)) {
    employeeField.value = previousValue;
    return;
  }
  if (employees.length) employeeField.value = String(employees[0].id);
}

function populateDeliveryEpiField(epiField, epis) {
  epiField.innerHTML = epis.map((item) => {
    const stock = Number(item.stock || 0);
    const stockLabel = stock > 0 ? `${stock} em estoque` : 'Sem saldo';
    return `<option value="${item.id}">${item.name} - ${item.unit_measure} (${stockLabel})</option>`;
  }).join('') || '<option value="">Nenhum EPI disponível para a unidade</option>';
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
    list.innerHTML = '<div class="summary-item">Nenhum EPI encontrado para esta busca/unidade.</div>';
    return;
  }
  list.innerHTML = source.slice(0, 30).map((item) => {
    const summary = `${item.name || '-'} | Fab: ${item.manufacturer || '-'} | CA: ${item.ca || '-'} | Proteção: ${item.sector || '-'} | Saldo: ${item.stock || 0}`;
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
}

function syncReportOptions() {
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
  unitField.innerHTML = `${lockByOperationalProfile ? '' : '<option value="">Todas</option>'}${units.map(formatUnitOption).join('')}`;
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
  employeeField.innerHTML = '<option value="">Todos os colaboradores</option>' + employees.map((item) => `<option value="${item.id}">${item.employee_id_code} - ${item.name}</option>`).join('');
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

function normalizeStockSizeValue(value) {
  const normalized = String(value ?? '').trim();
  if (!normalized) return '';
  const lowered = normalized.toLowerCase();
  if (['n/a', 'na', 'selecione', 'selecione o tamanho', 'null', 'undefined'].includes(lowered)) {
    return '';
  }
  return normalized;
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
      return `<li><strong>#${index + 1}</strong> ${escapeHtml(item.qr_code_value || item.raw || '')}${duplicateSuffix}</li>`;
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

function applyStockItemToDeliverySelection(stockItem) {
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
  console.info('[qr][scan] valor bruto recebido', { raw: value });
  console.info('[qr][scan] valor interpretado', interpreted);
  try {
    const params = new URLSearchParams({
      actor_user_id: String(state.user?.id || ''),
      company_id: String(companyId),
      unit_id: String(unitId),
      qr_code: interpreted?.qr_code || value
    });
    if (interpreted?.stock_item_id) params.set('stock_item_id', String(interpreted.stock_item_id));
    const payload = await api(`/api/stock/lookup-qr?${params.toString()}`);
    stockItem = payload?.stock_item || null;
  } catch (error) {
    console.warn('[qr][scan] rejeitado na validação', { raw: value, interpreted, reason: error?.message || 'erro_desconhecido' });
    setDeliveryQrStatus(`QR Não validado no estoque: ${error.message}`, true);
    return false;
  }
  if (!stockItem) {
    console.warn('[qr][scan] rejeitado: não encontrado', { raw: value, interpreted });
    setDeliveryQrStatus('QR Não encontrado no estoque da unidade.', true);
    return false;
  }
  if (input) input.value = value;
  if (options.applyToForm !== false) applyStockItemToDeliveryForm(stockItem);
  setDeliveryQrStatus(`Unidade validada: ${stockItem.epi_name || stockItem.qr_code_value || stockItem.id}`);
  return stockItem;
}

async function queueDeliveryQrForCurrentSession(options = {}) {
  const stockItem = await handleDeliveryQrScan({ ...options, applyToForm: false });
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
      setDeliveryQrStatus(`QR duplicado detectado: ${stockItem.qr_code_value}. Duplicidade registrada na sessão.`);
      return false;
    }
    return false;
  }
  applyQrFeedbackOnce(`estoque:${stockItem.qr_code_value}`);
  const epiSelected = applyStockItemToDeliverySelection(stockItem);
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

function closeSignatureModal() {
  const modalRefs = signatureModalRefs();
  modalRefs.modal?.classList.remove('is-open');
  modalRefs.modal?.setAttribute('aria-hidden', 'true');
  state.signatureDraft = null;
}

function openSignatureModal({ signerName = '', comment = '', onConfirm }) {
  const modalRefs = signatureModalRefs();
  if (!modalRefs.modal || !modalRefs.canvas) return;
  signaturePadController = setupDrawingCanvas(modalRefs.canvas, modalRefs.clear);
  signaturePadController.clear();
  const signedAt = signatureNowLabel();
  if (modalRefs.name) modalRefs.name.value = signerName;
  if (modalRefs.at) modalRefs.at.value = signedAt;
  if (modalRefs.comment) modalRefs.comment.value = comment;
  modalRefs.modal.classList.add('is-open');
  modalRefs.modal.setAttribute('aria-hidden', 'false');
  state.signatureDraft = { onConfirm };
}

function setupSignatureModal() {
  const modalRefs = signatureModalRefs();
  safeOn(modalRefs.cancel, 'click', closeSignatureModal);
  safeOn(modalRefs.modal, 'click', (event) => {
    if (event.target === modalRefs.modal) closeSignatureModal();
  });
  safeOn(modalRefs.confirm, 'click', () => {
    if (!state.signatureDraft?.onConfirm) return closeSignatureModal();
    const signatureData = signaturePadController?.getData?.() || '';
    if (!signatureData) {
      alert('Assinatura digital obrigatória. Desenhe no campo de assinatura.');
      return;
    }
    state.signatureDraft.onConfirm({
      signature_name: String(modalRefs.name?.value || '').trim() || 'Assinatura digital',
      signature_data: signatureData,
      signature_at: new Date().toISOString(),
      signature_comment: String(modalRefs.comment?.value || '').trim()
    });
    closeSignatureModal();
  });
}

function applyDeliverySignature(payload) {
  if (refs.deliverySignatureData) refs.deliverySignatureData.value = String(payload.signature_data || '');
  if (refs.deliverySignatureName) refs.deliverySignatureName.value = String(payload.signature_name || 'Assinatura digital');
  if (refs.deliverySignatureAt) refs.deliverySignatureAt.value = String(payload.signature_at || '');
  if (refs.deliverySignatureComment) refs.deliverySignatureComment.value = String(payload.signature_comment || '');
  if (refs.deliverySignatureStatus) refs.deliverySignatureStatus.textContent = `Assinado por ${payload.signature_name || 'Assinatura digital'} em ${signatureNowLabel()}.`;
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
  if (refs.deliverySignatureStatus) refs.deliverySignatureStatus.textContent = 'Assinatura pendente (pode assinar agora ou depois no período da ficha).';
}

function setupDeliverySignatureCanvas() {
  safeOn(refs.deliverySignatureOpen, 'click', () => {
    const employee = selectedDeliveryEmployee();
    openSignatureModal({
      signerName: employee?.name || state.user?.full_name || 'Assinatura digital',
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
    refreshDeliveryContext();
  } catch (error) {
    alert(error.message);
  }
}

async function generateDeliveryEmployeeLink() {
  const employeeId = Number(document.getElementById('delivery-employee')?.value || 0);
  if (!employeeId) return alert('Selecione um colaborador para gerar o link.');
  try {
    const payload = await api('/api/employee-portal-link', {
      method: 'POST',
      body: JSON.stringify({ actor_user_id: state.user.id, employee_id: employeeId })
    });
    const accessLink = payload.access_link || '';
    const linkField = document.getElementById('delivery-employee-link');
    if (linkField) linkField.value = accessLink;
    if (accessLink) await navigator.clipboard?.writeText(accessLink);
    alert('Link gerado com sucesso. O acesso estará disponível no link.');
  } catch (error) {
    alert(error.message);
  }
}

function openDeliveryEmployeeLink() {
  const linkField = document.getElementById('delivery-employee-link');
  const accessLink = String(linkField?.value || '').trim();
  if (!accessLink) {
    alert('Gere um link antes de tentar abrir.');
    return;
  }
  const popup = globalThis.open(accessLink, '_blank', 'noopener,noreferrer');
  if (!popup) {
    alert('Não foi possí­vel abrir o link automaticamente. Verifique o bloqueador de pop-up e tente novamente.');
  }
}

function buildEmployeePortalMessageModel(model, employee, accessLink) {
  const employeeName = employee?.name || 'Colaborador';
  const companyName = employee?.company_name || 'empresa';
  if (model === 'email') {
    return [
      `Assunto: Assinatura da Ficha de EPI - ${employeeName}`,
      '',
      `Olá, ${employeeName}.`,
      '',
      `Para manter a conformidade de Segurança do Trabalho da ${companyName}, acesse o link abaixo (válido por 48 horas) para:`,
      '- Assinar sua Ficha de EPI',
      '- Solicitar EPI',
      '- Avaliar EPI',
      '',
      `Link de acesso: ${accessLink}`,
      '',
      'Esse registro ação essencial para rastreabilidade e auditoria de entrega de EPIs.',
      'Em caso de dúvidas, responda este e-mail.'
    ].join('\n');
  }
  return `Olá${employeeName}! Olá·\nSeu link rápido da Ficha de EPI está pronto (válido por 48h):\n${accessLink}\nNo portal Você consegue: Assinar Ficha, Solicitar EPI e Avaliar EPI.\nAcesse agora.`;
}

async function copyDeliveryEmployeeMessage() {
  const employeeId = Number(document.getElementById('delivery-employee')?.value || 0);
  if (!employeeId) return alert('Selecione um colaborador.');
  const employee = state.employees.find((item) => Number(item.id) === employeeId);
  const accessLink = String(document.getElementById('delivery-employee-link')?.value || '').trim();
  if (!accessLink) return alert('Gere o link antes de copiar a mensagem.');
  const model = String(document.getElementById('delivery-employee-message-model')?.value || 'whatsapp');
  if (model === 'whatsapp' && !String(employee?.whatsapp || '').trim()) {
    alert('Colaborador sem WhatsApp cadastrado. Atualize no cadastro do colaborador.');
    return;
  }
  if (model === 'email' && !String(employee?.email || '').trim()) {
    alert('Colaborador sem e-mail cadastrado. Atualize no cadastro do colaborador.');
    return;
  }
  const message = buildEmployeePortalMessageModel(model, employee, accessLink);
  const copied = await copyTextToClipboard(message);
  alert(copied ? 'Mensagem copiada com sucesso.' : 'Mensagem gerada. Copie manualmente.');
}

async function sendDeliveryEmployeeMessage() {
  const employeeId = Number(document.getElementById('delivery-employee')?.value || 0);
  if (!employeeId) return alert('Selecione um colaborador.');
  const channel = String(document.getElementById('delivery-employee-message-model')?.value || 'whatsapp');
  const accessLink = String(document.getElementById('delivery-employee-link')?.value || '').trim();
  try {
    const payload = await api('/api/employee-contact-launch', {
      method: 'POST',
      body: JSON.stringify({
        actor_user_id: state.user.id,
        employee_id: employeeId,
        channel,
        access_link: accessLink
      })
    });
    const launchUrl = String(payload?.launch_url || '').trim();
    if (!launchUrl) throw new Error('Não foi possí­vel gerar URL de envio.');
    const popup = globalThis.open(launchUrl, '_blank', 'noopener,noreferrer');
    if (!popup) {
      globalThis.location.href = launchUrl;
    }
  } catch (error) {
    alert(error.message);
  }
}

function setDeliveryQrStatus(message, isError = false) {
  const status = document.getElementById('delivery-qr-status');
  if (!status) return;
  status.textContent = String(message || '');
  status.style.color = isError ? '#a13b2b' : '#96401c';
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
  const epiSelected = applyStockItemToDeliverySelection(stockItem);
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

async function stopDeliveryQrCamera() {
  if (qrScannerState.stopping) return qrScannerState.stopping;
  qrScannerState.stopping = (async () => {
    qrScannerState.starting = false;
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
  if (video) video.srcObject = null;
  if (video) video.style.display = 'block';
  if (readerBox) {
    readerBox.style.display = 'none';
    readerBox.innerHTML = '';
  }
  if (wrap) wrap.style.display = 'none';
  wrap?.classList.remove('qr-camera-fullscreen');
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
          return;
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
    { fps: 12, qrbox: { width: 300, height: 300 }, aspectRatio: 1.0 },
    (decodedText) => {
      input.value = String(decodedText || '').trim();
      void onQrScanSuccess(input.value);
    },
    () => null
  );
}

async function startDeliveryQrCamera() {
  const input = document.getElementById('delivery-qr-scan');
  const wrap = document.getElementById('delivery-qr-camera-wrap');
  const video = document.getElementById('delivery-qr-video');
  const readerBox = document.getElementById('delivery-qr-reader-box');

  if (!input || !wrap || !video || !readerBox) {
    console.warn('[qr] Elementos do scanner não encontrados no DOM.');
    alert('Leitor de QR indisponível nesta tela. Recarregue a página e tente novamente.');
    return;
  }
  if (qrScannerState.starting) {
    console.info('[qr] Inicialização já em andamento; ignorando nova tentativa.');
    return;
  }
  qrScannerState.starting = true;

  if (!('mediaDevices' in navigator) || !navigator.mediaDevices.getUserMedia) {
    setDeliveryQrStatus('Navegador sem acesso há¡ câmera. Use leitor USB ou digite o código.', true);
    alert('câmera Não disponível neste navegador. Você pode digitar ou usar leitor USB.');
    qrScannerState.starting = false;
    return;
  }
  const isLocalhost = ['localhost', '127.0.0.1'].includes(String(location.hostname || '').toLowerCase());
  if (location.protocol !== 'https:' && !isLocalhost) {
    setDeliveryQrStatus('Câmera exige HTTPS para funcionar neste navegador.', true);
    alert('Leitor de câmera requer HTTPS em dispositivos móveis. Acesse o sistema via conexão segura (https).');
    qrScannerState.starting = false;
    alert('Câmera Não disponível neste navegador. Você pode digitar ou usar leitor USB.');
    return;
  }

  await stopDeliveryQrCamera();
  resetDeliveryQrSession();

  try {
    wrap.style.display = 'grid';
    wrap.classList.add('qr-camera-fullscreen');
    if (video) {
      video.style.display = 'none';
      video.srcObject = null;
    }
    readerBox.style.display = 'block';
    readerBox.innerHTML = '';
    qrScannerState.active = true;
    setDeliveryQrStatus('Solicitando permissão da câmera...');
    await startDeliveryQrWithHtml5Qrcode(input);
    qrScannerState.starting = false;
    return;
  } catch (html5Error) {
    console.warn('[qr] html5-qrcode indisponível, aplicando fallback:', html5Error);
  }

  try {
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' } },
        audio: false
      });
    } catch (primaryError) {
      console.warn('[camera] fallback para Câmera padrão:', primaryError);
      stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    }

    qrScannerState.stream = stream;
    qrScannerState.active = true;
    wrap.style.display = 'grid';
    readerBox.style.display = 'none';
    video.srcObject = stream;
    video.style.display = 'block';
    await video.play();

    if ('BarcodeDetector' in globalThis) {
      await startDeliveryQrWithBarcodeDetector(video, input);
    } else {
      await startDeliveryQrWithZxing('delivery-qr-video', input);
    }
  } catch (error) {
    console.error('Camera access error:', error);
    await stopDeliveryQrCamera();
    const message = String(error?.message || '');
    const blocked = ['NotAllowedError', 'PermissionDeniedError'].includes(String(error?.name || ''));
    if (blocked) {
      setDeliveryQrStatus('permissão de Câmera negada.', true);
      alert('permissão da Câmera negada. Autorize o acesso no navegador e tente novamente.');
      return;
    }
    setDeliveryQrStatus('Falha ao iniciar câmera neste dispositivo/navegador.', true);
    alert(`Não foi possí­vel iniciar a câmera automaticamente. Você pode usar "Ler por imagem" ou "Usar leitor de código de barras". ${message}`.trim());
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

function renderFicha() {
  const filteredEmployees = applyFichaEmployeeFilters(filterByUserCompany(state.employees));
  if (refs.fichaEmployee) {
    const previous = String(refs.fichaEmployee.value || '');
    refs.fichaEmployee.innerHTML = filteredEmployees.map((item) => `<option value="${item.id}">${item.employee_id_code} - ${item.name}</option>`).join('');
    if (previous && filteredEmployees.some((item) => String(item.id) === previous)) refs.fichaEmployee.value = previous;
  }
  const employeeId = refs.fichaEmployee.value || filteredEmployees[0]?.id;
  const employee = filteredEmployees.find((item) => String(item.id) === String(employeeId));
  if (!employee) { refs.fichaView.innerHTML = '<div class="summary-item">Nenhum colaborador disponível.</div>'; return; }
  refs.fichaEmployee.value = employee.id;
  const periods = (state.fichasPeriods || [])
    .filter((item) => String(item.employee_id) === String(employee.id))
    .sort((a, b) => String(b.period_start || '').localeCompare(String(a.period_start || '')));
  const canFinalizePeriod = hasPermission('deliveries:create');
  const periodsHtml = periods.map((item) => {
    const pendingItems = Number(item.pending_items || 0);
    const signed = String(item.batch_signature_at || '').trim() !== '';
    const closed = String(item.status || '').toLowerCase() === 'closed';
    const finalizeButton = canFinalizePeriod && !closed
      ? `<div class="action-group">
          <select data-ficha-channel="${item.id}">
            <option value="whatsapp">WhatsApp</option>
            <option value="email">E-mail</option>
          </select>
          <button class="ghost" type="button" data-ficha-copy-message="${item.id}">Copiar mensagem</button>
          <button class="ghost" type="button" data-ficha-finalize="${item.id}">Finalizar período</button>
        </div>`
      : '';
    return `<div class="summary-item">
      <strong>Período: ${formatDate(item.period_start)} a ${formatDate(item.period_end)}</strong>
      <div>Status: ${item.status || 'open'} | Unidade: ${item.unit_name || '-'}</div>
      <div>Itens no período: ${Number(item.total_items || 0)} | Pendentes de assinatura: ${pendingItems}</div>
      <div>Assinatura em lote: ${signed ? `Sim (${formatDateTime(item.batch_signature_at)})` : 'Pendente (pode assinar após o fechamento via link)'}</div>
      ${finalizeButton}
    </div>`;
  }).join('');
  refs.fichaView.innerHTML = `<div class="summary-item"><strong>Empresa:</strong> ${employee.company_name} (${employee.company_cnpj})</div><div class="summary-item ficha-logo"><strong>Logotipo:</strong> ${companyLogoMarkup({ name: employee.company_name, logo_type: employee.logo_type }, 'company-logo company-logo-sm')}</div><div class="summary-item"><strong>Colaborador:</strong> ${employee.name}</div><div class="summary-item"><strong>ID:</strong> ${employee.employee_id_code}</div><div class="summary-item"><strong>Setor:</strong> ${employee.sector}</div><div class="summary-item"><strong>Função:</strong> ${employee.role_name || employee.position || '-'}</div>${periodsHtml || '<div class="summary-item">Sem períodos de ficha para este colaborador.</div>'}</div>`;
}

async function finalizeFichaPeriod(periodId) {
  if (!requirePermission('fichas:view')) return;
  const channel = String(refs.fichaView?.querySelector(`[data-ficha-channel="${periodId}"]`)?.value || 'whatsapp').trim();
  try {
    const payload = await api('/api/fichas/finalize', {
      method: 'POST',
      body: JSON.stringify({
        actor_user_id: state.user.id,
        ficha_period_id: Number(periodId),
        channel
      })
    });
    const launchUrl = String(payload?.launch_url || '').trim();
    if (launchUrl) {
      const popup = globalThis.open(launchUrl, '_blank', 'noopener,noreferrer');
      if (!popup) {
        const copied = await copyTextToClipboard(launchUrl);
        alert(copied
          ? 'Link do canal gerado. O navegador bloqueou a nova aba; o link foi copiado para a área de transferência.'
          : `Link do canal gerado. O navegador bloqueou a nova aba; abra manualmente: ${launchUrl}`);
      }
    }
    await loadBootstrap();
    renderFicha();
    alert('Período finalizado, link gerado e canal de envio preparado.');
  } catch (error) {
    alert(error.message);
  }
}

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
  if (!hasPermission('reports:view')) return;
  const normalizedFilters = filters || collectReportFilters();
  const params = new URLSearchParams({ ...normalizedFilters, actor_user_id: state.user.id });
  state.reports = await api(`/api/reports?${params.toString()}`);
  refs.reportSummary.innerHTML = `<div class="summary-item"><strong>Entregas:</strong> ${state.reports.deliveries.length}</div><div class="summary-item"><strong>Total entregue:</strong> ${state.reports.total_quantity}</div>`;
  refs.reportUnits.innerHTML = Object.entries(state.reports.by_unit).map((item) => `<div class="report-row"><strong>${item[0]}</strong> ${item[1]}</div>`).join('') || '<div class="summary-item">Sem dados.</div>';
  refs.reportSectors.innerHTML = Object.entries(state.reports.by_sector).map((item) => `<div class="report-row"><strong>${item[0]}</strong> ${item[1]}</div>`).join('') || '<div class="summary-item">Sem dados.</div>';
  if (!refs.reportEmployeeFichas) return;
  const employeeFichas = state.reports.employee_fichas || [];
  refs.reportEmployeeFichas.innerHTML = employeeFichas.map((item) => {
    return `<div class="summary-item"><strong>${item.employee_name} (${item.employee_id_code})</strong><div>perí­odo: ${formatDate(item.period_start)} a ${formatDate(item.period_end)} | Status: ${item.status}</div><div>Unidade: ${item.unit_name || '-'} | Itens: ${item.total_items} | Quantidade total: ${item.total_quantity}</div></div>`;
  }).join('') || '<div class="summary-item">Selecione um colaborador para visualizar as fichas de EPI.</div>';
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
  `).join('') || '<tr><td colspan="7">Sem fichas arquivadas para os filtros informados.</td></tr>';
  if (refs.reportArchivePagination) {
    refs.reportArchivePagination.textContent = `Registros: ${state.reportArchiveTotal} | Página ${state.reportArchivePage}`;
  }
}

async function loadArchiveReports(filters = {}) {
  if (!hasPermission('reports:view')) return;
  const params = new URLSearchParams({
    ...filters,
    page: String(state.reportArchivePage || 1),
    page_size: String(state.reportArchivePageSize || 50),
    actor_user_id: String(state.user?.id || '')
  });
  const payload = await api(`/api/ficha-archive?${params.toString()}`);
  state.reportArchiveItems = payload.items || [];
  state.reportArchiveTotal = Number(payload.total || 0);
  state.fichaRetentionPolicy = payload.retention_policy || state.fichaRetentionPolicy;
  renderArchiveTable();
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
  const payload = await api(`/api/ficha-retention-policy?${actorQuery()}`);
  state.fichaRetentionPolicy = payload || state.fichaRetentionPolicy;
  renderRetentionPolicy();
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
    unit_id: normalizeOptionalInt('unit_id', reportForm?.querySelector('#report-unit')?.value),
    employee_id: normalizeOptionalInt('employee_id', reportForm?.querySelector('#report-employee')?.value),
    sector: String(reportForm?.querySelector('#report-sector')?.value || '').trim(),
    epi_id: normalizeOptionalInt('epi_id', reportForm?.querySelector('#report-epi')?.value),
    status: String(reportForm?.querySelector('#report-ficha-status')?.value || '').trim(),
    start_date: normalizeOptionalDate('start_date', reportForm?.querySelector('input[name="start_date"]')?.value),
    end_date: normalizeOptionalDate('end_date', reportForm?.querySelector('input[name="end_date"]')?.value)
  };
  return Object.fromEntries(Object.entries(values).filter(([, value]) => value !== ''));
}

function refreshDeliveryContext() {
  const employee = state.employees.find((item) => String(item.id) === String(document.getElementById('delivery-employee').value));
  const deliveryCompanyField = document.getElementById('delivery-company');
  const deliveryUnitFilterField = document.getElementById('delivery-unit-filter');
  const unit = state.units.find((item) => String(item.id) === String(employee?.current_unit_id || employee?.unit_id || ''));
  const linkField = document.getElementById('delivery-employee-link');
  const channelModelField = document.getElementById('delivery-employee-message-model');
  if (employee?.company_id && deliveryCompanyField) deliveryCompanyField.value = String(employee.company_id);
  let unitChanged = false;
  if (unit?.id && deliveryUnitFilterField && String(deliveryUnitFilterField.value || '') !== String(unit.id)) {
    deliveryUnitFilterField.value = String(unit.id);
    unitChanged = true;
  }
  if (unitChanged) {
    syncDeliveryOptions();
  }
  if (linkField) {
    const accessLink = buildEmployeeAccessLink(employee?.employee_access_token || '');
    linkField.value = accessLink;
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
  applyDeliveryReplacementSuggestion({ force: true });
  void loadOpenDeliveriesForCurrentPair().finally(() => syncDeliveryDevolutionOptions());
}

function selectedOpenDeliveryForDevolution() {
  const selectedId = String(refs.deliveryReturnDeliveryId?.value || '').trim();
  if (!selectedId) return null;
  return (state.deliveryReturnCandidates || []).find((item) => String(item.id) === selectedId) || null;
}

function renderDeliveryReturnCandidates(candidates = []) {
  const field = refs.deliveryReturnDeliveryId;
  const hint = refs.deliveryReturnDeliveryHint;
  if (!field) return;
  const list = Array.isArray(candidates) ? candidates : [];
  const needsExplicitPick = list.length > 1;
  const options = list.map((item) => {
    const signatureLabel = item.signature_at ? `assinado em ${formatDateTime(item.signature_at)}` : 'assinatura pendente';
    const detail = `${formatDate(item.delivery_date)} | ${item.quantity} ${item.quantity_label || 'unidade'} | ${item.unit_name || 'Unidade não informada'} | ${signatureLabel}`;
    return `<option value="${item.id}">#${item.id} — ${detail}</option>`;
  }).join('');
  field.innerHTML = options || '<option value="">Sem entrega aberta para este colaborador + EPI</option>';
  if (needsExplicitPick) {
    field.innerHTML = `<option value="">Selecione a entrega de origem da devolução</option>${field.innerHTML}`;
    field.value = '';
  } else if (list.length === 1) {
    field.value = String(list[0].id);
  }
  if (hint) {
    if (!list.length) hint.textContent = 'Nenhuma entrega aberta para este colaborador e este EPI.';
    else if (list.length === 1) hint.textContent = 'Entrega aberta identificada automaticamente.';
    else hint.textContent = 'Foram encontradas múltiplas entregas abertas. Selecione explicitamente a entrega de origem da devolução.';
  }
}

async function loadOpenDeliveriesForCurrentPair() {
  const actorUserId = String(state.user?.id || '').trim();
  const employeeId = String(document.getElementById('delivery-employee')?.value || '').trim();
  const epiId = String(document.getElementById('delivery-epi')?.value || '').trim();
  const unitId = String(document.getElementById('delivery-unit-filter')?.value || state.user?.operational_unit_id || '').trim();
  const scopeKey = `${employeeId}|${epiId}|${unitId}`;
  if (!actorUserId || !employeeId || !epiId) {
    state.deliveryReturnCandidates = [];
    state.deliveryReturnScopeKey = '';
    state.deliveryReturnPendingScopeKey = '';
    renderDeliveryReturnCandidates([]);
    return;
  }
  if (state.deliveryReturnScopeKey === scopeKey && state.deliveryReturnCandidates.length) return;
  if (state.deliveryReturnPendingScopeKey === scopeKey) return;
  try {
    state.deliveryReturnPendingScopeKey = scopeKey;
    const payload = await api(`/api/devolutions/open-deliveries?${new URLSearchParams({ employee_id: employeeId, epi_id: epiId, unit_id: unitId, actor_user_id: actorUserId }).toString()}`);
    state.deliveryReturnCandidates = payload.items || [];
    state.deliveryReturnScopeKey = scopeKey;
    renderDeliveryReturnCandidates(state.deliveryReturnCandidates);
  } catch (error) {
    console.error('[devolution-open-deliveries] Falha ao consultar entregas abertas:', error);
    state.deliveryReturnCandidates = [];
    state.deliveryReturnScopeKey = scopeKey;
    renderDeliveryReturnCandidates([]);
  } finally {
    if (state.deliveryReturnPendingScopeKey === scopeKey) state.deliveryReturnPendingScopeKey = '';
  }
}

function syncDeliveryDevolutionOptions() {
  const selectedEpiId = String(document.getElementById('delivery-epi')?.value || '').trim();
  const employeeId = String(document.getElementById('delivery-employee')?.value || '').trim();
  const optionWrap = refs.deliveryDevolutionOptions;
  const checkField = refs.deliveryIsDevolution;
  const fieldsWrap = refs.deliveryDevolutionFields;
  const submitButton = document.querySelector('#delivery-form button[type="submit"]');
  if (!optionWrap || !checkField || !fieldsWrap) return;
  const hasSelection = Boolean(selectedEpiId && employeeId);
  optionWrap.style.display = hasSelection ? 'block' : 'none';
  if (!hasSelection) {
    state.deliveryReturnCandidates = [];
    state.deliveryReturnScopeKey = '';
    renderDeliveryReturnCandidates([]);
    checkField.checked = false;
    fieldsWrap.style.display = 'none';
    if (submitButton) submitButton.textContent = 'Registrar entrega';
    return;
  }
  const canReturnSelectedPair = Boolean((state.deliveryReturnCandidates || []).length);
  checkField.disabled = !canReturnSelectedPair;
  if (!canReturnSelectedPair) {
    checkField.checked = false;
    fieldsWrap.style.display = 'none';
  }
  if (submitButton) {
    submitButton.textContent = checkField.checked ? 'Registrar devolução' : 'Registrar entrega';
  }
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
    box.innerHTML = '<div class="summary-item">Nenhum colaborador encontrado para o filtro informado.</div>';
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
  const firstOption = canUseWithoutLink ? '<option value=>Sem ví­nculo</option>' : '';
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
  renderLowStock();
  renderRequests();
  renderStockEpis();
  renderFicha();
  if (hasConfigurationAccess()) void loadFichaConfig();
  if (hasConfigurationAccess()) void loadRetentionPolicy();
  if (canViewConfiguration()) void loadFichaAuditLogs();
  renderReports();
  refreshDeliveryContext();
  syncUserFormAccess();
  syncStructuralCrudAccess();
  markRequiredFieldLabels();
  updateBootstrapDegradedUi();
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

    const payload = await api('/api/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
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
function getLoginErrorMessage(error) {
  const code = String(error?.code || '').toUpperCase();
  if (error?.phase === 'post_login_bootstrap') {
    if (code === 'DB_BOOTSTRAP_NOT_READY') return 'Autenticação concluída, mas o sistema ainda está inicializando. Tente novamente em instantes.';
    return `Autenticação concluída, porém falhou o carregamento inicial: ${error?.message || 'erro inesperado.'}`;
  }
  if (code === 'USER_NOT_FOUND') return 'Usuário Não encontrado.';
  if (code === 'INVALID_CREDENTIALS') return 'Usuário ou senha inválidos.';
  if (code === 'USER_INACTIVE') return 'Usuário inativo. Procure o administrador do sistema.';
  if (code === 'FORCE_PASSWORD_CHANGE') return 'há¡ necessÃÂ¡rio redefinir a senha antes de continuar.';
  if (error?.status === 403 && !code) return 'Acesso negado ou sessÃÂ£o inválida.';
  return error.message || 'Falha ao autenticar. Verifique Usuário e senha.';
}

function toggleRecoveryPanel() {
  if (!refs.recoveryPanel) return;
  const isVisible = refs.recoveryPanel.style.display !== 'none';
  refs.recoveryPanel.style.display = isVisible ? 'none' : 'block';
}

async function handlePasswordRecovery() {
  try {
    const payload = {
      username: String(refs.recoveryUsername?.value || '').trim(),
      new_password: String(refs.recoveryPassword?.value || '').trim(),
      recovery_key: String(refs.recoveryKey?.value || '').trim()
    };
    await api('/api/recover-password', { method: 'POST', body: JSON.stringify(payload) });
    alert('Senha redefinida com sucesso. Faça login com a nova senha.');
    if (refs.recoveryPanel) refs.recoveryPanel.style.display = 'none';
    const passwordField = refs.loginPassword;
    if (passwordField) passwordField.value = '';
  } catch (error) {
    alert(error.message);
  }
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

    if (!String(values.password || '').trim() && !state.editingUserId) {
      throw new Error('Informe uma senha para criar o Usuário.');
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
            throw new Error('Leia e valide ao menos um QR antes de clicar em "Registrar entrega".');
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
  } catch (error) {
    if (event.target.id === 'delivery-form') {
      document.dispatchEvent(new CustomEvent('epi:delivery-submit-error', { detail: { message: String(error?.message || '') } }));
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
  } else if (form.id === 'unit-form') {
    setFormSubmitLabel('unit-form', 'Salvar unidade');
  } else if (form.id === 'employee-form') {
    setFormSubmitLabel('employee-form', 'Salvar colaborador');
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
    if (refs.deliverySignatureStatus) refs.deliverySignatureStatus.textContent = 'Assinatura pendente.';
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
  const html = `<!doctype html><html><head><meta charset="utf-8"><title>Etiquetas EPI</title><style>body{font-family:Arial,sans-serif;padding:12px}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}.label{border:1px dashed #999;padding:8px;text-align:center;font-size:12px}img{width:110px;height:110px}</style></head><body><div class="grid">${blocks}</div></body></html>`;
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
    setStockManufactureStatus(`Falha na captura automática: ${error.message || 'erro desconhecido'}`, 'error');
  } finally {
    event.target.value = '';
    dateField.focus();
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
    const lookup = await api(`/api/stock/lookup-qr?${params.toString()}`);
    const item = lookup?.stock_item;
    if (!item?.id) throw new Error('Etiqueta Não encontrada.');
    const reason = prompt('Justificativa da reimpressão (Perdeu ou Rasgou):', 'Perdeu');
    if (reason === null) return;
    const normalizedReason = String(reason || '').trim().toLowerCase();
    if (!['perdeu', 'rasgou'].includes(normalizedReason)) {
      throw new Error('Justificativa inválida. Use "Perdeu" ou "Rasgou".');
    }
    const result = await api('/api/stock/labels/reprint', {
      method: 'POST',
      body: JSON.stringify({
        actor_user_id: state.user.id,
        company_id: Number(companyId),
        stock_item_id: Number(item.id),
        reason_code: normalizedReason
      })
    });
    if (result?.label) printStockLabels([result.label], 1);
    alert(`Etiqueta reimpressa. Total de Reimpressões: ${Number(result?.label?.reprint_count || 0)}.`);
  } catch (error) {
    alert(error.message);
  }
}

async function saveEmployeeMovement(event) {
  event.preventDefault();
  if (!requirePermission('employees:update')) return;
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

function portalCpfStorageKey(token) {
  return `employee_portal_cpf_last3_${String(token || '').slice(0, 18)}`;
}

function cachePortalCpfLast3(token, cpfLast3) {
  if (!/^\d{3}$/.test(String(cpfLast3 || ''))) return;
  sessionStorage.setItem(portalCpfStorageKey(token), String(cpfLast3));
}

function getCachedPortalCpfLast3(token) {
  const cached = String(sessionStorage.getItem(portalCpfStorageKey(token)) || '').trim();
  return /^\d{3}$/.test(cached) ? cached : '';
}

function renderEmployeeCpfValidationScreen(token, message = '', locked = false) {
  document.body.innerHTML = `
    <section class="screen active">
      <div class="login-panel employee-portal-shell" style="max-width:460px;">
        <h2>Validação de CPF</h2>
        <p>Digite os 3 últimos números do CPF para acessar o portal.</p>
        <label>Últimos 3 dígitos do CPF
          <input id="employee-cpf-last3" maxlength="3" inputmode="numeric" placeholder="000" ${locked ? 'disabled' : ''}>
        </label>
        <small id="employee-cpf-feedback" class="hint" style="${message ? 'color:#b42318;' : ''}">${message || 'Você tem até 3 tentativas por token.'}</small>
        <button id="employee-cpf-submit" class="primary" type="button" ${locked ? 'disabled' : ''}>Validar acesso</button>
      </div>
    </section>
  `;
  const input = document.getElementById('employee-cpf-last3');
  const submit = document.getElementById('employee-cpf-submit');
  const feedback = document.getElementById('employee-cpf-feedback');
  if (!input || !submit || !feedback) return;
  const cached = getCachedPortalCpfLast3(token);
  if (cached && !locked) input.value = cached;
  safeOn(input, 'input', () => { input.value = String(input.value || '').replace(/\D/g, '').slice(0, 3); });
  safeOn(input, 'keyup', (event) => {
    if (event.key === 'Enter' && !locked) submit.click();
  });
  safeOn(submit, 'click', async () => {
    const cpfLast3 = String(input.value || '').replace(/\D/g, '').slice(0, 3);
    if (!/^\d{3}$/.test(cpfLast3)) {
      feedback.textContent = 'Informe exatamente os 3 últimos dígitos do CPF.';
      feedback.style.color = '#b42318';
      return;
    }
    try {
      await renderEmployeeExternalAccess(token, cpfLast3);
      cachePortalCpfLast3(token, cpfLast3);
    } catch (error) {
      const msg = String(error?.message || 'Não foi possível validar o CPF.');
      feedback.textContent = msg;
      feedback.style.color = '#b42318';
      if (msg.toLowerCase().includes('bloqueado') || msg.toLowerCase().includes('novo link')) {
        submit.disabled = true;
        input.disabled = true;
      }
    }
  });
}

async function renderEmployeeExternalAccess(token, cpfLast3 = '') {
  const payload = await api(`/api/employee-access?token=${encodeURIComponent(token)}&cpf_last3=${encodeURIComponent(cpfLast3)}`, { headers: {} });
  const employee = payload.employee || {};
  const deliveries = payload.deliveries || [];
  const fichas = payload.fichas || [];
  const requests = payload.requests || [];
  const feedbacks = payload.feedbacks || [];
  const availableEpis = payload.available_epis || [];
  const gloveSizeOptions = ['N/A', 'XP (6)', 'P (7)', 'M (8)', 'G (9)', 'XG (10)', 'XXG (11)'];
  const sizeOptions = ['N/A', 'N°34', 'N°35', 'N°36', 'N°37', 'N°38', 'N°39', 'N°40', 'N°41', 'N°42', 'N°43', 'N°44', 'N°45', 'N°46', 'N°47', 'N°48', 'N°49', 'N°50', 'N°51', 'N°52', 'N°53', 'N°54', 'N°55', 'N°56', 'N°57', 'N°58', 'N°59', 'N°60'];
  const uniformSizeOptions = ['N/A', 'XP', 'PP', 'P', 'M', 'G', 'GG', 'XGG', 'XXG'];
  const requestSizeLabel = (item) => [item.glove_size, item.size, item.uniform_size].filter((value) => value && value !== 'N/A').join(' / ') || 'N/A';
  document.body.innerHTML = `
    <section class="screen active">
      <div class="login-panel employee-portal-shell">
        <h2>Acesso do Colaborador</h2>
        <p><strong>${employee.employee_name || '-'}</strong> ${employee.company_name || '-'}</p>
        <p>ID: ${employee.employee_id_code || '-'} | Setor: ${employee.sector || '-'}</p>
        <label>Assinatura do colaborador
          <button id="employee-signature-open" class="ghost" type="button">Clique para assinar</button>
        </label>
        <small id="employee-signature-status" class="hint">Assinatura pendente para o período.</small>
        <label>perí­odo da ficha</label>
        <select id="employee-ficha-period">${fichas.map((item) => `<option value="${item.id}">${formatDate(item.period_start)} a ${formatDate(item.period_end)} (${item.status})</option>`).join('')}</select>
        <button id="employee-sign-batch" class="btn btn-primary" type="button">Assinar período selecionado</button>
        <button id="employee-download-pdf" class="btn btn-secondary" type="button">Baixar PDF da ficha</button>
        <div class="table-wrap users-table-wrap">
          <table>
            <thead>
              <tr>
                <th>EPI</th>
                <th>Data de Entrega</th>
                <th>Status</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              ${deliveries.length ? deliveries.map((item) => {
                const deliveryId = item.id || item.delivery_id || '';
                const deliveredAt = formatDate(item.delivered_at || item.created_at || item.date);
                const signed = Boolean(item.signature_at) || item.signed || String(item.status || '').toLowerCase().includes('assin');
                return `<tr>
                  <td>${item.epi_name || item.name || '-'}</td>
                  <td>${deliveredAt}</td>
                  <td>${item.status || (signed ? 'Assinado' : 'Pendente')}</td>
                  <td>${signed ? 'Assinado' : 'Pendente (use assinatura em lote do período)'}</td>
                </tr>`;
              }).join('') : '<tr><td colspan="4">Nenhuma entrega registrada.</td></tr>'}
            </tbody>
          </table>
        </div>
        <div class="portal-tabs">
          <button class="menu-link active" data-portal-tab="ficha">Ficha de EPI</button>
          <button class="menu-link" data-portal-tab="solicitacao">Solicitação de EPI</button>
          <button class="menu-link" data-portal-tab="avaliacao">Avaliação</button>
        </div>
        <div data-portal-pane="ficha">
          <h3>Ficha de EPI</h3>
          <div class="table-wrap users-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>EPI</th>
                  <th>Data de Entrega</th>
                  <th>Status</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                ${deliveries.length ? deliveries.map((item) => {
                  const deliveryId = item.id || item.delivery_id || '';
                  const deliveredAt = formatDate(item.delivered_at || item.created_at || item.date);
                  const signed = Boolean(item.signature_at) || item.signed || String(item.status || '').toLowerCase().includes('assin');
                  return `<tr>
                    <td>${item.epi_name || item.name || '-'}</td>
                    <td>${deliveredAt}</td>
                    <td>${item.status || (signed ? 'Assinado' : 'Pendente')}</td>
                    <td>${signed ? 'Assinado' : 'Pendente (use assinatura em lote do período)'}</td>
                  </tr>`;
                }).join('') : '<tr><td colspan="4">Nenhuma entrega registrada para o perí­odo selecionado.</td></tr>'}
              </tbody>
            </table>
          </div>
        </div>
        <div data-portal-pane="solicitacao" style="display:none;">
          <h3>Solicitar EPI cadastrado</h3>
          <label>EPI disponível</label>
          <select id="employee-request-epi">${availableEpis.map((item) => `<option value="${item.id}">${item.name} (${item.purchase_code || '-'})</option>`).join('')}</select>
          <fieldset class="size-group">
            <legend>Tamanhos do item</legend>
            <div class="size-grid">
              <label>Tamanho-luva
                <select id="employee-request-glove-size">${gloveSizeOptions.map((value) => `<option value="${value}">${value}</option>`).join('')}</select>
              </label>
              <label>Tamanho
                <select id="employee-request-size">${sizeOptions.map((value) => `<option value="${value}">${value}</option>`).join('')}</select>
              </label>
              <label>Tamanho-uniforme
                <select id="employee-request-uniform-size">${uniformSizeOptions.map((value) => `<option value="${value}">${value}</option>`).join('')}</select>
              </label>
            </div>
          </fieldset>
          <label>Quantidade</label>
          <input id="employee-request-quantity" type="number" min="1" value="1">
          <label>Justificativa</label>
          <textarea id="employee-request-justification" rows="3" placeholder="Motivo da solicitação"></textarea>
          <button id="employee-request-submit" class="btn btn-primary" type="button">Enviar solicitação</button>
          <div class="table-wrap users-table-wrap"><table><thead><tr><th>ID</th><th>EPI</th><th>Tamanho</th><th>Qtd</th><th>Status</th><th>Data</th></tr></thead><tbody>${requests.map((item) => `<tr><td>#${item.id}</td><td>${item.epi_name}</td><td>${requestSizeLabel(item)}</td><td>${item.quantity}</td><td>${item.status}</td><td>${formatDate(item.requested_at)}</td></tr>`).join('') || '<tr><td colspan="6">Sem Crítico solicitações.</td></tr>'}</tbody></table></div>
        </div>
        <div data-portal-pane="avaliacao" style="display:none;">
          <h3>AvaliAções</h3>
          <label>EPI utilizado</label>
          <select id="employee-feedback-epi"><option value="">Selecione (opcional para nova sugestão)</option>${availableEpis.map((item) => `<option value="${item.id}">${item.name} (${item.purchase_code || '-'})</option>`).join('')}</select>
          <div class="grid cols-2">
            <label>Conforto (0-5)<input id="employee-rate-comfort" type="number" min="0" max="5" value="0"></label>
            <label>Qualidade (0-5)<input id="employee-rate-quality" type="number" min="0" max="5" value="0"></label>
            <label>Adequação (0-5)<input id="employee-rate-adequacy" type="number" min="0" max="5" value="0"></label>
            <label>Desempenho (0-5)<input id="employee-rate-performance" type="number" min="0" max="5" value="0"></label>
          </div>
          <label>Observações</label>
          <textarea id="employee-feedback-comments" rows="3"></textarea>
          <label>sugestão de melhoria</label>
          <textarea id="employee-feedback-improvement" rows="2"></textarea>
          <label>sugestão</label>
          <input id="employee-feedback-new-name" type="text" placeholder="Nome do EPI sugerido">
          <textarea id="employee-feedback-new-notes" rows="2" placeholder="Detalhes da sugestão"></textarea>
          <button id="employee-feedback-submit" class="btn btn-primary" type="button">Enviar avaliação</button>
          <div class="table-wrap users-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>EPI</th>
                  <th>Status</th>
                  <th>Avaliação</th>
                  <th>sugestão</th>
                </tr>
              </thead>
              <tbody>
                ${feedbacks.length ? feedbacks.map((item) => `<tr><td>#${item.id}</td><td>${item.epi_name || '-'}</td><td>${item.status || '-'}</td><td>C:${item.comfort_rating} Q:${item.quality_rating} A:${item.adequacy_rating} D:${item.performance_rating}</td><td>${item.suggested_new_epi_name || '-'}</td></tr>`).join('') : '<tr><td colspan="5">Sem avaliAções registradas.</td></tr>'}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
    <div id="signature-modal" class="signature-modal" aria-hidden="true">
      <div class="signature-modal__dialog" role="dialog" aria-modal="true" aria-labelledby="signature-modal-title">
        <header class="signature-modal__header">
          <h3 id="signature-modal-title">Assinatura digital</h3>
        </header>
        <div class="signature-modal__body">
          <label>Nome
            <input id="signature-modal-name" type="text" readonly>
          </label>
          <label>Data e hora
            <input id="signature-modal-at" type="text" readonly>
          </label>
          <p id="signature-modal-canvas-label" class="hint"><strong>Assinatura digital</strong></p>
          <canvas id="signature-modal-canvas" width="560" height="200" aria-labelledby="signature-modal-canvas-label"></canvas>
          <div class="action-group"><button id="signature-modal-clear" class="ghost" type="button">Limpar assinatura</button></div>
          <label>Comentários (opcional)
            <textarea id="signature-modal-comment" rows="3" placeholder="Caso não reconheça algum EPI, informe neste campo"></textarea>
          </label>
        </div>
        <footer class="signature-modal__footer">
          <button id="signature-modal-cancel" class="ghost" type="button">Cancelar</button>
          <button id="signature-modal-confirm" class="primary" type="button">OK</button>
        </footer>
      </div>
    </div>`;
  setupSignatureModal();
  let portalSignature = null;
  const employeeSignatureStatus = document.getElementById('employee-signature-status');
  const employeeSignatureOpen = document.getElementById('employee-signature-open');
  safeOn(employeeSignatureOpen, 'click', () => {
    openSignatureModal({
      signerName: employee.employee_name || 'Assinatura digital',
      comment: portalSignature?.signature_comment || '',
      onConfirm: (payloadSignature) => {
        portalSignature = payloadSignature;
        if (employeeSignatureStatus) {
          employeeSignatureStatus.textContent = `Assinatura capturada em ${formatDateTime(payloadSignature.signature_at)}.`;
        }
      }
    });
  });

  safeOn(document.getElementById('employee-download-pdf'), 'click', () => {
    globalThis.open(`/api/employee-access/pdf?token=${encodeURIComponent(token)}&cpf_last3=${encodeURIComponent(cpfLast3)}`, '_blank');
  });
  document.querySelectorAll('[data-portal-tab]').forEach((button) => {
    safeOn(button, 'click', () => {
      document.querySelectorAll('[data-portal-tab]').forEach((item) => item.classList.remove('active'));
      document.querySelectorAll('[data-portal-pane]').forEach((pane) => { pane.style.display = 'none'; });
      button.classList.add('active');
      const pane = document.querySelector(`[data-portal-pane="${button.dataset.portalTab}"]`);
      if (pane) pane.style.display = 'block';
    });
  });
  safeOn(document.getElementById('employee-sign-batch'), 'click', async () => {
    const fichaPeriodId = document.getElementById('employee-ficha-period')?.value;
    if (!fichaPeriodId) return alert('Nenhum perí­odo de ficha selecionado para assinatura em lote.');
    if (!portalSignature?.signature_data) return alert('Clique em "Clique para assinar" antes de confirmar o período.');
    try {
      await api('/api/employee-sign-batch', {
        method: 'POST',
        body: JSON.stringify({
          token,
          cpf_last3: cpfLast3,
          ficha_period_id: fichaPeriodId,
          signature_name: portalSignature.signature_name,
          signature_data: portalSignature.signature_data,
          signature_comment: portalSignature.signature_comment
        })
      });
      alert('Assinatura em lote aplicada.');
      await renderEmployeeExternalAccess(token, cpfLast3);
    } catch (error) {
      alert(error.message);
    }
  });
  safeOn(document.getElementById('employee-request-submit'), 'click', async () => {
    try {
      const resolvedSize = resolveItemSize({
        glove_size: document.getElementById('employee-request-glove-size')?.value,
        size: document.getElementById('employee-request-size')?.value,
        uniform_size: document.getElementById('employee-request-uniform-size')?.value
      });
      if (!resolvedSize.selectedSize || resolvedSize.selectedSize === 'N/A') {
        throw new Error('Selecione o tamanho para solicitar o EPI.');
      }
      await api('/api/requests', {
        method: 'POST',
        body: JSON.stringify({
          token,
          cpf_last3: cpfLast3,
          epi_id: Number(document.getElementById('employee-request-epi')?.value || 0),
          glove_size: resolvedSize.glove_size,
          size: resolvedSize.size,
          uniform_size: resolvedSize.uniform_size,
          quantity: Number(document.getElementById('employee-request-quantity')?.value || 1),
          justification: String(document.getElementById('employee-request-justification')?.value || '').trim()
        })
      });
      alert('Solicitação enviada com sucesso.');
      await renderEmployeeExternalAccess(token, cpfLast3);
    } catch (error) {
      alert(error.message);
    }
  });
  const employeeRequestEpi = document.getElementById('employee-request-epi');
  const syncEmployeeRequestSizes = () => {
    const selectedEpi = availableEpis.find((item) => String(item.id) === String(employeeRequestEpi?.value || ''));
    if (!selectedEpi) return;
    const gloveField = document.getElementById('employee-request-glove-size');
    const sizeField = document.getElementById('employee-request-size');
    const uniformField = document.getElementById('employee-request-uniform-size');
    if (gloveField) gloveField.value = String(selectedEpi.glove_size || 'N/A');
    if (sizeField) sizeField.value = String(selectedEpi.size || 'N/A');
    if (uniformField) uniformField.value = String(selectedEpi.uniform_size || 'N/A');
  };
  safeOn(employeeRequestEpi, 'change', syncEmployeeRequestSizes);
  syncEmployeeRequestSizes();
  safeOn(document.getElementById('employee-feedback-submit'), 'click', async () => {
    try {
      await api('/api/employee-feedback', {
        method: 'POST',
        body: JSON.stringify({
          token,
          cpf_last3: cpfLast3,
          epi_id: document.getElementById('employee-feedback-epi')?.value || null,
          comfort_rating: Number(document.getElementById('employee-rate-comfort')?.value || 0),
          quality_rating: Number(document.getElementById('employee-rate-quality')?.value || 0),
          adequacy_rating: Number(document.getElementById('employee-rate-adequacy')?.value || 0),
          performance_rating: Number(document.getElementById('employee-rate-performance')?.value || 0),
          comments: String(document.getElementById('employee-feedback-comments')?.value || '').trim(),
          improvement_suggestion: String(document.getElementById('employee-feedback-improvement')?.value || '').trim(),
          suggested_new_epi_name: String(document.getElementById('employee-feedback-new-name')?.value || '').trim(),
          suggested_new_epi_notes: String(document.getElementById('employee-feedback-new-notes')?.value || '').trim()
        })
      });
      alert('Avaliação enviada com sucesso.');
      await renderEmployeeExternalAccess(token, cpfLast3);
    } catch (error) {
      alert(error.message);
    }
  });
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

async function loadFichaConfig() {
  try {
    const data = await api('/api/ficha-config?' + actorQuery());
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
    await api('/api/ficha-config', {
      method: 'POST',
      body: JSON.stringify({
        actor_user_id: state.user.id,
        titulo:        f.elements.titulo.value,
        declaracao:    f.elements.declaracao.value,
        observacoes:   f.elements.observacoes.value,
        rastreabilidade: f.elements.rastreabilidade.value,
      })
    });
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
  renderFichaAuditLogs();
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

function fichaAuditActionBadge(action) {
  const map = {
    view: ['status', 'active', 'visualizou'],
    print: ['status', 'warning', 'imprimiu'],
    denied: ['status', 'inactive', 'negado'],
    snapshot_view: ['status', 'active', 'snapshot'],
    snapshot_print: ['status', 'warning', 'snapshot print'],
    snapshot_export: ['status', 'active', 'snapshot export']
  };
  const [kind, tone, label] = map[action] || ['status', 'inactive', action || '-'];
  return renderBadge(kind, tone, label);
}

function renderFichaAuditLogs() {
  if (!refs.fichaAuditTable) return;
  refs.fichaAuditTable.innerHTML = (state.fichaAuditLogs || []).map((item) => `
    <tr>
      <td>${formatDateTime(item.accessed_at)}</td>
      <td>${item.actor_name || '-'}</td>
      <td>${item.employee_name || '-'}</td>
      <td>${fichaAuditActionBadge(item.action)}</td>
      <td>${item.unit_name || '-'}</td>
      <td>${item.ip_address || '-'}</td>
      <td>${item.user_agent || '-'}</td>
    </tr>
  `).join('') || '<tr><td colspan="7">Sem logs de auditoria de ficha.</td></tr>';
}

function renderFichaAuditUnavailable(message = 'Histórico temporariamente indisponível. Tente novamente.') {
  if (!refs.fichaAuditTable) return;
  refs.fichaAuditTable.innerHTML = `<tr><td colspan="7">${escapeHtml(message)}</td></tr>`;
}

async function loadFichaAuditLogs() {
  if (!hasConfigurationAccess()) return;
  if (!canViewConfiguration()) return;
  if (refs.fichaAuditTable) {
    refs.fichaAuditTable.innerHTML = '<tr><td colspan="7">Carregando histórico de auditoria...</td></tr>';
  }
  const params = new URLSearchParams();
  if (refs.fichaAuditEmployee?.value) params.set('employee_id', refs.fichaAuditEmployee.value);
  if (refs.fichaAuditManager?.value) params.set('actor_user_id', refs.fichaAuditManager.value);
  if (refs.fichaAuditAction?.value) params.set('action', refs.fichaAuditAction.value);
  if (refs.fichaAuditDateFrom?.value) params.set('date_from', refs.fichaAuditDateFrom.value);
  if (refs.fichaAuditDateTo?.value) params.set('date_to', refs.fichaAuditDateTo.value);
  params.set('actor_user_id', state.user?.id || '');
  const response = await apiOptional(`/api/ficha-epi-audit?${params.toString()}`);
  if (!response.ok) {
    state.fichaAuditLogs = [];
    renderFichaAuditUnavailable('Histórico temporariamente indisponível. Tente novamente.');
    return;
  }
  state.fichaAuditLogs = response.payload?.items || [];
  renderFichaAuditLogs();
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

function openDevolutionModal(deliveryId, epiName, employeeName) {
  const today = new Date().toISOString().split('T')[0];
  let devolutionSignature = null;
  document.getElementById('devolution-modal')?.remove();
  const modal = document.createElement('div');
  modal.id = 'devolution-modal';
  modal.className = 'signature-modal is-open';
  modal.innerHTML = [
    '<div class="signature-modal__dialog" role="dialog" aria-modal="true" style="max-width:540px">',
    '<header class="signature-modal__header">',
    '<h3 style="margin:0">↩ Registrar Devolução de EPI</h3>',
    '</header>',
    '<div class="signature-modal__body" style="display:flex;flex-direction:column;gap:12px">',
    '<div class="card" style="background:#f8f9fa;padding:12px;border-radius:6px;margin:0">',
    '<strong>EPI:</strong> '+epiName+'<br>',
    '<strong>Colaborador:</strong> '+employeeName,
    '</div>',
    '<label style="display:flex;flex-direction:column;gap:4px">',
    '<span>Data da devolução <span style="color:red">*</span></span>',
    '<input id="dev-date" type="date" value="'+today+'" required style="padding:8px;border:1px solid #ccc;border-radius:4px">',
    '</label>',
    '<label style="display:flex;flex-direction:column;gap:4px">',
    '<span>Condição do EPI devolvido <span style="color:red">*</span></span>',
    '<select id="dev-condition" style="padding:8px;border:1px solid #ccc;border-radius:4px">',
    '<option value="usable">✅ Reutilizável — pode voltar ao estoque</option>',
    '<option value="damaged">⚠️ Danificado — encaminhar para avaliação</option>',
    '<option value="discarded">🗑️ Descartado — sem condições de uso</option>',
    '<option value="maintenance">🔧 Em manutenção</option>',
    '<option value="hygiene">🧼 Para higienização</option>',
    '<option value="quarantine">🔒 Em quarentena</option>',
    '</select>',
    '</label>',
    '<label style="display:flex;flex-direction:column;gap:4px">',
    '<span>Destino do item <span style="color:red">*</span></span>',
    '<select id="dev-dest" style="padding:8px;border:1px solid #ccc;border-radius:4px">',
    '<option value="stock">📦 Retornar ao estoque (atualiza saldo)</option>',
    '<option value="discard">🗑️ Descartar</option>',
    '<option value="maintenance">🔧 Encaminhar para manutenção</option>',
    '<option value="hygiene">🧼 Encaminhar para higienização</option>',
    '<option value="quarantine">🔒 Colocar em quarentena</option>',
    '</select>',
    '</label>',
    '<label style="display:flex;flex-direction:column;gap:4px">',
    '<span>Motivo / Justificativa</span>',
    '<input id="dev-reason" type="text" placeholder="Ex.: rescisão de contrato, EPI vencido, troca por uso..." style="padding:8px;border:1px solid #ccc;border-radius:4px">',
    '</label>',
    '<label style="display:flex;flex-direction:column;gap:4px">',
    '<span>Observações adicionais</span>',
    '<textarea id="dev-notes" rows="2" placeholder="Informações adicionais sobre a devolução..." style="padding:8px;border:1px solid #ccc;border-radius:4px;resize:vertical"></textarea>',
    '</label>',
    '<label>Assinatura digital da devolução (opcional agora)',
    '<button id="dev-signature-open" class="ghost" type="button">Clique para assinar agora</button>',
    '</label>',
    '<small id="dev-signature-status" class="hint">Sem assinatura imediata. A assinatura pode ser aplicada no fechamento do período da ficha.</small>',
    '<div style="background:#e8f4fd;border:1px solid #b8daff;border-radius:4px;padding:10px;font-size:13px">',
    '<strong>ℹ️ O que acontece ao confirmar:</strong><br>',
    '• A devolução será vinculada à entrega original<br>',
    '• A movimentação de estoque será registrada automaticamente<br>',
    '• A Ficha de EPI do colaborador será atualizada<br>',
    '• O histórico completo ficará disponível para auditoria',
    '</div>',
    '</div>',
    '<footer class="signature-modal__footer">',
    '<button class="ghost" id="dev-cancel">Cancelar</button>',
    '<button class="primary" id="dev-confirm" style="background:#dc3545">↩ Confirmar devolução</button>',
    '</footer>',
    '</div>'
  ].join('');
  document.body.appendChild(modal);
  const devCancelBtn = document.getElementById('dev-cancel');
  if (devCancelBtn) devCancelBtn.onclick = () => modal.remove();
  modal.onclick = (e) => { if (e.target === modal) modal.remove(); };
  const devSignatureBtn = document.getElementById('dev-signature-open');
  const devSignatureStatus = document.getElementById('dev-signature-status');
  safeOn(devSignatureBtn, 'click', () => {
    openSignatureModal({
      signerName: employeeName || state.user?.full_name || 'Assinatura digital',
      comment: devolutionSignature?.signature_comment || '',
      onConfirm: (payloadSignature) => {
        devolutionSignature = payloadSignature;
        if (devSignatureStatus) {
          devSignatureStatus.textContent = `Assinatura capturada em ${formatDateTime(payloadSignature.signature_at)}.`;
        }
      }
    });
  });
  const devConfirmBtn = document.getElementById('dev-confirm');
  if (!devConfirmBtn) return;
  devConfirmBtn.onclick = async () => {
    const btn = devConfirmBtn;
    const returnedDate = document.getElementById('dev-date').value;
    if (!returnedDate) { alert('Informe a data da devolução.'); return; }
    const condition = document.getElementById('dev-condition').value;
    const destination = document.getElementById('dev-dest').value;
    const reason = document.getElementById('dev-reason').value.trim();
    const notes = document.getElementById('dev-notes').value.trim();
    const originalText = btn.textContent;
    try {
      btn.disabled = true;
      btn.textContent = 'Registrando...';
      await api('/api/devolutions', {
        method: 'POST',
        body: JSON.stringify({
          actor_user_id: state.user.id,
          delivery_id: deliveryId,
          returned_date: returnedDate,
          condition,
          destination,
          reason,
          notes,
          signature_name: devolutionSignature?.signature_name || '',
          signature_data: devolutionSignature?.signature_data || '',
          signature_at: devolutionSignature?.signature_at || '',
          signature_comment: devolutionSignature?.signature_comment || '',
        })
      });
      modal.remove();
      showToast('Devolução registrada com sucesso! Movimentação e ficha atualizadas.', 'success');
      await loadBootstrap();
    } catch(err) {
      alert('Erro: ' + (err instanceof Error ? err.message : String(err)));
      btn.disabled = false;
      btn.textContent = originalText;
    }
  };
}

function buildDeliveryRowWithDevolution(item) {
  const devolvido = String(item.returned_date || '').trim();
  // Coluna 8: Próx. Troca / Devolução
  let col8 = '';
  if (devolvido) {
    const condLabel = {
      usable:'Reutilizável', damaged:'Danificado', discarded:'Descartado',
      maintenance:'Em manutenção', quarantine:'Em quarentena', hygiene:'Para higienização'
    }[item.returned_condition || ''] || item.returned_condition || '';
    col8 = '<span class="badge badge-status-inactive" title="Condição: '+condLabel+'">'
          +'↩ Dev. '+formatDate(item.returned_date)+'</span>';
  } else {
    col8 = formatDate(item.next_replacement_date) || '<span style="color:#aaa">—</span>';
  }
  // Coluna 9: Ação
  let col9 = '';
  if (!devolvido && hasPermission('deliveries:create')) {
    col9 = '<button class="ghost" style="font-size:12px;padding:4px 10px;" '
          +'data-dev-delivery="'+item.id+'" '
          +'data-dev-epi="'+(item.epi_name||'').replace(/"/g,'&quot;')+'" '
          +'data-dev-emp="'+(item.employee_name||'').replace(/"/g,'&quot;')+'" '
          +'title="Registrar devolução deste EPI">↩ Devolver</button>';
  } else if (devolvido) {
    col9 = '<span style="color:#6c757d;font-size:12px;">Devolvido</span>';
  }
  return '<tr>'
    +'<td>'+( item.company_name||'')+'</td>'
    +'<td>'+( item.employee_id_code||'')+'</td>'
    +'<td>'+( item.employee_name||'')+'</td>'
    +'<td>'+( item.epi_name||'')+'</td>'
    +'<td>'+( item.quantity||'')+'</td>'
    +'<td>'+( item.quantity_label||'')+'</td>'
    +'<td>'+formatDate(item.delivery_date)+'</td>'
    +'<td>'+col8+'</td>'
    +'<td><div class="action-group">'+col9+'</div></td>'
    +'</tr>';
}

function showToast(message, type = 'success') {
  const existing = document.getElementById('epi-toast');
  if (existing) existing.remove();
  const toast = document.createElement('div');
  toast.id = 'epi-toast';
  const bg = type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : '#17a2b8';
  toast.style.cssText = 'position:fixed;bottom:24px;right:24px;background:'+bg+';color:#fff;padding:12px 20px;border-radius:8px;z-index:9999;font-size:14px;max-width:400px;box-shadow:0 4px 12px rgba(0,0,0,.3);';
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 5000);
}

async function init() {
  const runNonCriticalSetup = (label, setupFn) => {
    try {
      setupFn();
    } catch (error) {
      reportNonCriticalError(`[init] módulo não crítico ignorado: ${label}`, error);
    }
  };

  runNonCriticalSetup('assinatura modal', setupSignatureModal);
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

  runNonCriticalSetup('preload login URL', preloadLoginFromUrl);
  runNonCriticalSetup('required labels', markRequiredFieldLabels);
  runNonCriticalSetup('phase2 pilots', setupPhase2PilotsSafely);
  runNonCriticalSetup('phase2.9 ux', setupPhase29Ux);
  runNonCriticalSetup('spa navigation history', bindSpaNavigationHistory);
  runNonCriticalSetup('spa navigation visibility', applySpaNavigationVisibility);
  runNonCriticalSetup('interactive app dropdowns', setupInteractiveDropdowns);
  runNonCriticalSetup('interactive tools actions', bindInteractiveToolsActions);
  runNonCriticalSetup('ux performance hardening', applyPerformanceHardeningVisibility);
  runNonCriticalSetup('ux mobile visibility', applyMobileUxVisibility);
  runNonCriticalSetup('ux mobile behavior', bindMobileUxBehavior);
  runNonCriticalSetup('assinatura entrega', setupDeliverySignatureCanvas);
  runNonCriticalSetup('sessão QR entrega', resetDeliveryQrSession);
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
  bindAppListener(refs.passwordChangeForm, 'submit', handleForcedPasswordChange);
  bindAppListener(refs.recoveryToggle, 'click', toggleRecoveryPanel);
  bindAppListener(refs.recoverySubmit, 'click', handlePasswordRecovery);
  bindAppListener(refs.userForm, 'submit', saveUser);
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

  bindAppListener(refs.companyLogoFile, 'change', handleCompanyLogoUpload);
  bindAppListener(refs.platformLogoFile, 'change', handlePlatformLogoUpload);
  bindAppListener(refs.platformLoginLogoFile, 'change', handlePlatformLoginLogoUpload);
  configureEpiPhotoInputCapture();
  bindAppListener(document.getElementById('epi-photo-file'), 'change', handleEpiPhotoUpload);
  bindAppListener(document.getElementById('epi-photo-open-camera'), 'click', () => openEpiPhotoPicker({ preferCamera: true }));
  bindAppListener(document.getElementById('epi-photo-open-files'), 'click', () => openEpiPhotoPicker({ preferCamera: false }));

  bindAppListener(refs.companyForm?.elements.cnpj, 'blur', (event) => {
    event.target.value = formatCnpj(event.target.value);
  });

  bindAppListener(refs.platformBrandForm?.elements.cnpj, 'blur', (event) => {
    event.target.value = formatCnpj(event.target.value);
  });

  bindAppListener(document.getElementById('unit-form'), 'submit', (event) => saveSimpleForm(event, '/api/units', 'units:create'));
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
  });
  bindSearchInput(document.getElementById('delivery-employee-search'), syncDeliveryOptions, 140);
  bindSearchInput(refs.deliveryEpiSearch, renderDeliveryEpiSearchResults, 120);
  bindSearchInput(refs.deliveryEpiSearchManufacturer, renderDeliveryEpiSearchResults, 120);
  bindAppListener(document.getElementById('delivery-qr-apply'), 'click', () => { void queueDeliveryQrForCurrentSession(); });
  bindAppListener(document.getElementById('delivery-qr-scan'), 'change', () => { void queueDeliveryQrForCurrentSession(); });
  bindAppListener(document.getElementById('delivery-qr-scan'), 'keyup', (event) => {
    if (event.key === 'Enter') void queueDeliveryQrForCurrentSession();
  });
  bindAppListener(document.getElementById('delivery-qr-start'), 'click', startDeliveryQrCamera);
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
    if (submitButton) submitButton.textContent = enabled ? 'Registrar devolução' : 'Registrar EPI';
    if (refs.deliverySignatureStatus) {
      refs.deliverySignatureStatus.textContent = enabled
        ? 'Assinatura opcional para devolução (pode assinar agora ou no fechamento da ficha).'
        : 'Assinatura pendente.';
    }
  });
  bindAppListener(document.getElementById('delivery-employee'), 'change', () => {
    syncDeliveryQrSessionOwner();
    clearDeliveryStockItemSelection();
    resetDeliverySignatureDraft();
    state.deliveryReturnCandidates = [];
    state.deliveryReturnScopeKey = '';
    refreshDeliveryContext();
  });
  bindAppListener(document.getElementById('delivery-epi'), 'change', () => {
    clearDeliveryStockItemSelection();
    state.deliveryReturnCandidates = [];
    state.deliveryReturnScopeKey = '';
    refreshDeliveryContext();
    applyDeliveryReplacementSuggestion({ force: true });
  });
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
    const btn = (event.target).closest('[data-dev-delivery]');
    if (!btn) return;
    openDevolutionModal(
      btn.getAttribute('data-dev-delivery'),
      btn.getAttribute('data-dev-epi'),
      btn.getAttribute('data-dev-emp')
    );
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
  bindAppListener(refs.configRulesForm, 'submit', (event) => { void onSubmitConfigurationRule(event); });
  bindAppListener(refs.configRulesTable, 'click', (event) => {
    const button = event.target.closest('[data-remove-config-rule]');
    if (!button) return;
    void removeConfigurationRule(button.dataset.removeConfigRule);
  });
  bindAppListener(refs.configFrameworkForm, 'submit', (event) => { void saveConfigurationFramework(event); });
  [refs.fichaAuditEmployee, refs.fichaAuditManager, refs.fichaAuditAction, refs.fichaAuditDateFrom, refs.fichaAuditDateTo]
    .forEach((el) => bindAppListener(el, 'change', () => { void loadFichaAuditLogs(); }));

  bindAppListener(refs.fichaView, 'click', (event) => {
    const copyButton = event.target.closest('[data-ficha-copy-message]');
    if (copyButton) {
      void copyFichaPeriodMessage(copyButton.dataset.fichaCopyMessage);
      return;
    }
    const button = event.target.closest('[data-ficha-finalize]');
    if (!button) return;
    void finalizeFichaPeriod(button.dataset.fichaFinalize);
  });
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

  bindAppListener(refs.fichaRetentionPurgeRun, 'click', async () => {
    if (!hasConfigurationAccess()) return;
    if (!confirm('Executar rotina de expiração/purge de snapshots agora?')) return;
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
  bindAppListener(refs.topConfigTrigger, 'click', () => {
    if (!hasConfigurationAccess()) return;
    navigateToView('configuracao', { historyMode: isSpaNavigationEnabled() ? 'push' : null, partial: false });
  });
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
  }

  bindAppListener(refs.usersTable, 'click', handleUsersTableClick);

  bindAppListener(refs.employeesTable, 'click', (event) => {
    const button = event.target.closest('button');
    if (!button) return;
    if (button.dataset.employeeEdit) { startEditEmployee(button.dataset.employeeEdit); }
    if (button.dataset.employeeDelete) { deleteRegistryEntity('/api/employees', button.dataset.employeeDelete, 'employees:delete', 'Remover este colaborador?'); }
  });
  bindAppListener(refs.unitsTable, 'click', (event) => {
    if (event.target.dataset.unitEdit) startEditUnit(event.target.dataset.unitEdit);
    if (event.target.dataset.unitDelete) deleteRegistryEntity('/api/units', event.target.dataset.unitDelete, 'units:delete', 'Tem certeza que deseja excluir esta unidade?\nEssa ação apagarÃÂ¡ permanentemente a unidade e todos os registros vinculados a ela.\nEssa ação Não poderÃÂ¡ ser desfeita.');
  });
  bindAppListener(refs.episTable, 'click', (event) => {
    if (event.target.dataset.epiEdit) startEditEpi(event.target.dataset.epiEdit);
    if (event.target.dataset.epiDelete) deleteRegistryEntity('/api/epis', event.target.dataset.epiDelete, 'epis:delete', 'Tem certeza que deseja excluir este EPI?\nEssa ação apagarÃÂ¡ permanentemente o EPI e todos os registros vinculados a ele.\nEssa ação Não poderÃÂ¡ ser desfeita.');
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
  document.getElementById('stock-reprint-label')?.addEventListener('click', () => { void reprintStockLabelByQr(); });
  refs.bootstrapDegradedRetry?.addEventListener('click', () => { void retryBootstrap(); });
  refs.bootstrapDegradedPanelRetry?.addEventListener('click', () => { void retryBootstrap(); });

  safeOn(globalThis, 'beforeunload', stopDeliveryQrCamera);

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

  showScreen(false);
  if (state.user) {
    let hasLoggedBootstrapFallback = false;
    const tryRestoreSession = async (attempt = 1) => {
      try {
        await loadBootstrap();
        showScreen(true);
      } catch (error) {
        if (isTemporaryBootstrapUnavailable(error)) {
          console.warn('[auth] Backend temporariamente indisponível durante restauração de sessão', { attempt, error });
          setLoginMessage('Servidor inicializando. Tentando restabelecer sessão automaticamente...', true);
          if (attempt < 2) {
            setTimeout(() => {
              void tryRestoreSession(attempt + 1);
            }, 2000);
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
  }, { once: true });
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

// fechamento do runtime guard global __EPI_APP_RUNTIME_LOADED__
}
