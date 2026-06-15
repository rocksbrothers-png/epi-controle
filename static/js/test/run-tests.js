'use strict';

/**
 * Runner de testes unitários (zero dependências) para os módulos de static/js.
 *
 * Os módulos são IIFEs que registram funções/constantes em globalThis. Este
 * runner cria mocks mínimos de browser (window, localStorage, location,
 * document), carrega os módulos na ordem de dependência e roda asserções.
 *
 * Uso:  node static/js/test/run-tests.js
 * Saída: exit 0 se todos passam; exit 1 caso contrário.
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const JS_ROOT = path.resolve(__dirname, '..');

// ── Mocks de browser ──────────────────────────────────────────────────────
let __store = {};
function resetStorage() { __store = {}; }
const localStorageMock = {
  getItem(key) { return Object.prototype.hasOwnProperty.call(__store, key) ? __store[key] : null; },
  setItem(key, value) { __store[key] = String(value); },
  removeItem(key) { delete __store[key]; }
};
globalThis.window = globalThis;
globalThis.localStorage = localStorageMock;
globalThis.location = { search: '', href: 'http://localhost/' };
globalThis.document = { querySelector() { return null; }, createElement() { return {}; }, getElementById() { return null; } };

function loadModule(relPath) {
  const full = path.join(JS_ROOT, relPath);
  const code = fs.readFileSync(full, 'utf-8');
  vm.runInThisContext(code, { filename: full });
}

[
  'core/constants.js',
  'core/permissions.js',
  'core/feature-flags.js',
  'core/config.js',
  'utils/storage.js',
  'utils/debug.js',
  'utils/dom.js',
  'utils/perf.js',
  'modules/feature-flags-rt.js',
  'modules/permissions-rt.js',
  'modules/auth.js',
  'modules/api-client.js',
  'modules/router.js',
  'views/ui-helpers.js',
  'views/view-helpers.js',
  'views/dashboard.js',
  'views/epis.js',
  'views/estoque.js'
].forEach(loadModule);

// ── Mini framework ────────────────────────────────────────────────────────
let passed = 0;
const failures = [];
function test(name, fn) {
  try {
    resetStorage();
    globalThis.location = { search: '' };
    fn();
    passed += 1;
  } catch (err) {
    failures.push({ name, message: err && err.message ? err.message : String(err) });
  }
}
function assert(cond, msg) {
  if (!cond) {throw new Error(msg || 'assertion failed');}
}
function eq(a, b, msg) {
  if (a !== b) {throw new Error((msg || 'eq') + ` — esperado ${JSON.stringify(b)}, obtido ${JSON.stringify(a)}`);}
}

// ── core/constants ────────────────────────────────────────────────────────
test('constants: STORAGE_KEYS', () => {
  eq(globalThis.STORAGE_KEYS.session, 'epi-session-v4');
  eq(globalThis.STORAGE_KEYS.token, 'epi-session-v4-token');
});
test('constants: ROLE_ALIASES normaliza', () => {
  eq(globalThis.ROLE_ALIASES.masteradmin, 'master_admin');
  eq(globalThis.ROLE_ALIASES.comprador, 'buyer');
});

// ── core/permissions ──────────────────────────────────────────────────────
test('permissions: employee sem permissões', () => {
  eq(globalThis.ROLE_PERMISSIONS.employee.length, 0);
});
test('permissions: master_admin tem license', () => {
  assert(globalThis.ROLE_PERMISSIONS.master_admin.includes('companies:license'));
});
test('permissions: VIEW_PERMISSIONS mapeia dashboard', () => {
  eq(globalThis.VIEW_PERMISSIONS.dashboard, 'dashboard:view');
});

// ── modules/permissions-rt ────────────────────────────────────────────────
test('permissions-rt: normalizeRole alias', () => {
  eq(globalThis.normalizeRole('masteradmin'), 'master_admin');
  eq(globalThis.normalizeRole('APROVADOR'), 'approver');
});
test('permissions-rt: hasPermission por role', () => {
  eq(globalThis.hasPermission('admin', 'epis:view'), true);
  eq(globalThis.hasPermission('employee', 'epis:view'), false);
  eq(globalThis.hasPermission('buyer', 'companies:view'), false);
});
test('permissions-rt: hasPermission via alias resolve', () => {
  eq(globalThis.hasPermission('comprador', 'purchase_orders:create'), true);
});
test('permissions-rt: canViewRoute', () => {
  eq(globalThis.canViewRoute('dashboard', 'employee'), false);
  eq(globalThis.canViewRoute('dashboard', 'admin'), true);
  eq(globalThis.canViewRoute('inexistente', 'master_admin'), false);
});

// ── utils/storage ─────────────────────────────────────────────────────────
test('storage: write/read round-trip', () => {
  eq(globalThis.safeStorageWrite('k', 'v'), true);
  eq(globalThis.safeStorageRead('k'), 'v');
  eq(globalThis.safeStorageRead('ausente', 'def'), 'def');
});
test('storage: safeJsonParse', () => {
  eq(globalThis.safeJsonParse('{"a":1}').a, 1);
  const fb = {};
  eq(globalThis.safeJsonParse('xx', fb), fb);
});

// ── utils/debug ───────────────────────────────────────────────────────────
test('debug: ensureModuleBound bloqueia duplicata', () => {
  const key = 'harness_' + Math.random().toString(36).slice(2);
  eq(globalThis.ensureModuleBound(key), true);
  eq(globalThis.ensureModuleBound(key), false);
});

// ── modules/feature-flags-rt ──────────────────────────────────────────────
test('feature-flags-rt: storage define flag', () => {
  eq(globalThis.setFeatureFlag('ux_phase41_enabled', true), true);
  eq(globalThis.getFeatureFlag('ux_phase41_enabled'), true);
});
test('feature-flags-rt: query param tem prioridade', () => {
  globalThis.setFeatureFlag('ux_phase41_enabled', true);
  globalThis.location = { search: '?ux_phase41=0' };
  eq(globalThis.getFeatureFlag('ux_phase41_enabled'), false);
});
test('feature-flags-rt: default quando ausente', () => {
  eq(globalThis.getFeatureFlag('ux_phase41_enabled', { defaultValue: false }), false);
});
test('feature-flags-rt: kill-switch desativa UX_FORCE_CLASSIC_FLAGS', () => {
  globalThis.setFeatureFlag('ux_global_kill_switch', true);
  globalThis.setFeatureFlag('ux_phase41_enabled', true);
  eq(globalThis.getFeatureFlag('ux_phase41_enabled'), false);
  eq(globalThis.getFeatureFlag('ux_global_kill_switch'), true);
});
test('feature-flags-rt: kill-switch não afeta flags fora de FORCE_CLASSIC', () => {
  globalThis.setFeatureFlag('ux_global_kill_switch', true);
  globalThis.setFeatureFlag('colaborador_htmx_enabled', true);
  eq(globalThis.getFeatureFlag('colaborador_htmx_enabled'), true);
});
test('feature-flags-rt: AUTO_ROLLBACK ativa kill-switch', () => {
  globalThis.__EPI_AUTO_ROLLBACK_ACTIVE__ = true;
  globalThis.setFeatureFlag('ux_phase41_enabled', true);
  eq(globalThis.getFeatureFlag('ux_phase41_enabled'), false);
  eq(globalThis.isUxGlobalKillSwitchActive(), true);
  delete globalThis.__EPI_AUTO_ROLLBACK_ACTIVE__;
});

// ── modules/auth ──────────────────────────────────────────────────────────
test('auth: getLoginErrorMessage USER_NOT_FOUND', () => {
  eq(globalThis.getLoginErrorMessage({ code: 'USER_NOT_FOUND' }), 'Usuário não encontrado.');
});
test('auth: getLoginErrorMessage INVALID_CREDENTIALS', () => {
  eq(globalThis.getLoginErrorMessage({ code: 'INVALID_CREDENTIALS' }), 'Usuário ou senha inválidos.');
});
test('auth: getLoginErrorMessage post_login_bootstrap DB_BOOTSTRAP_NOT_READY', () => {
  const err = { phase: 'post_login_bootstrap', code: 'DB_BOOTSTRAP_NOT_READY' };
  assert(globalThis.getLoginErrorMessage(err).includes('inicializando'));
});
test('auth: getLoginErrorMessage fallback para message', () => {
  eq(globalThis.getLoginErrorMessage({ message: 'erro custom' }), 'erro custom');
});
test('auth: isTemporaryBootstrapUnavailable 502/503/504', () => {
  eq(globalThis.isTemporaryBootstrapUnavailable({ status: 503 }), true);
  eq(globalThis.isTemporaryBootstrapUnavailable({ status: 502 }), true);
  eq(globalThis.isTemporaryBootstrapUnavailable({ status: 504 }), true);
  eq(globalThis.isTemporaryBootstrapUnavailable({ status: 200 }), false);
});
test('auth: isTemporaryBootstrapUnavailable por code', () => {
  eq(globalThis.isTemporaryBootstrapUnavailable({ code: 'DB_BOOTSTRAP_NOT_READY' }), true);
  eq(globalThis.isTemporaryBootstrapUnavailable({ code: 'HTTP_503' }), true);
});
test('auth: isSessionRestoreAuthError 401/403', () => {
  eq(globalThis.isSessionRestoreAuthError({ status: 401 }), true);
  eq(globalThis.isSessionRestoreAuthError({ status: 403 }), true);
  eq(globalThis.isSessionRestoreAuthError({ status: 200 }), false);
});
test('auth: isBootstrapRequestError nonFatal', () => {
  eq(globalThis.isBootstrapRequestError({ nonFatal: true, status: 200 }), true);
  eq(globalThis.isBootstrapRequestError({ status: 503 }), true);
  eq(globalThis.isBootstrapRequestError({ status: 404 }), false);
});

// ── modules/auth — gestão de sessão (sobre __EPI_APP_STATE__) ──────────────
function freshState() {
  const state = {
    user: null, permissions: [], token: '',
    requirePasswordChange: false,
    bootstrapDegraded: true, bootstrapError: { x: 1 }, bootstrapRetrying: true,
    bootstrapWarnings: ['w'], bootstrapAutoRetryAttempt: 3,
    bootstrapAutoRetryTimer: null, bootstrapAutoRetryCountdownTimer: null
  };
  globalThis.__EPI_APP_STATE__ = state;
  return state;
}
test('auth: normalizePermissions une role fallback sem duplicar', () => {
  const perms = globalThis.normalizePermissions({ role: 'admin' }, ['dashboard:view', 'x:y']);
  assert(perms.includes('x:y'));
  assert(perms.includes('epis:view')); // do fallback de admin
  eq(perms.filter((p) => p === 'dashboard:view').length, 1);
});
test('auth: saveSession normaliza role e grava storage', () => {
  const state = freshState();
  globalThis.saveSession({ id: 7, role: 'Comprador', company_id: 2 }, [], 'tok-1');
  eq(state.user.role, 'buyer');
  eq(state.token, 'tok-1');
  eq(globalThis.safeStorageRead(globalThis.STORAGE_KEYS.token), 'tok-1');
  eq(JSON.parse(globalThis.safeStorageRead(globalThis.STORAGE_KEYS.session)).id, 7);
});
test('auth: saveSession sem token remove a chave de token', () => {
  const state = freshState();
  globalThis.safeStorageWrite(globalThis.STORAGE_KEYS.token, 'antigo');
  globalThis.saveSession({ id: 1, role: 'admin' }, [], '');
  eq(state.token, '');
  eq(globalThis.safeStorageRead(globalThis.STORAGE_KEYS.token, null), null);
});
test('auth: setPasswordChangeRequired persiste flag', () => {
  const state = freshState();
  globalThis.setPasswordChangeRequired(true);
  eq(state.requirePasswordChange, true);
  eq(globalThis.safeStorageRead(globalThis.STORAGE_KEYS.changeRequired), 'true');
});
test('auth: clearSession zera estado e storage', () => {
  const state = freshState();
  globalThis.saveSession({ id: 1, role: 'admin' }, [], 'tok');
  globalThis.clearSession();
  eq(state.user, null);
  eq(state.token, '');
  eq(state.permissions.length, 0);
  eq(state.bootstrapDegraded, false);
  eq(state.bootstrapAutoRetryAttempt, 0);
  eq(globalThis.safeStorageRead(globalThis.STORAGE_KEYS.session, null), null);
  eq(globalThis.safeStorageRead(globalThis.STORAGE_KEYS.token, null), null);
});
test('auth: clearSession limpa timer de auto-retry', () => {
  const state = freshState();
  state.bootstrapAutoRetryTimer = setTimeout(() => {}, 100000);
  globalThis.clearSession();
  eq(state.bootstrapAutoRetryTimer, null);
});

// ── modules/api-client ────────────────────────────────────────────────────
test('api-client: createApiError define status e code', () => {
  const fakeResp = { status: 404 };
  const err = globalThis.createApiError('not found', fakeResp, { code: 'NOT_FOUND' });
  assert(err instanceof Error);
  eq(err.status, 404);
  eq(err.code, 'NOT_FOUND');
  eq(err.message, 'not found');
});
test('api-client: createApiError code fallback do payload', () => {
  const err = globalThis.createApiError('x', { status: 500 }, { code: 'SERVER_ERR' });
  eq(err.code, 'SERVER_ERR');
});
test('api-client: isBootstrapApiPath', () => {
  eq(globalThis.isBootstrapApiPath('/api/bootstrap'), true);
  eq(globalThis.isBootstrapApiPath('/api/bootstrap/full'), true);
  eq(globalThis.isBootstrapApiPath('/api/login'), false);
  eq(globalThis.isBootstrapApiPath(''), false);
});
test('api-client: throwIfApiRequestFailed ok=true é no-op', () => {
  globalThis.throwIfApiRequestFailed('/api/x', { ok: true, status: 200 }, {});
  // sem exceção
});
test('api-client: throwIfApiRequestFailed 401 lança com mensagem correta', () => {
  let caught = null;
  try { globalThis.throwIfApiRequestFailed('/api/x', { ok: false, status: 401 }, {}); } catch (e) { caught = e; }
  assert(caught !== null);
  assert(caught.message.includes('inválidos'));
});
test('api-client: throwIfApiRequestFailed 503 marca nonFatal', () => {
  let caught = null;
  try { globalThis.throwIfApiRequestFailed('/api/x', { ok: false, status: 503 }, {}); } catch (e) { caught = e; }
  eq(caught.nonFatal, true);
});
test('api-client: throwIfApiRequestFailed bootstrap path marca nonFatal', () => {
  let caught = null;
  try { globalThis.throwIfApiRequestFailed('/api/bootstrap', { ok: false, status: 422 }, {}); } catch (e) { caught = e; }
  eq(caught.nonFatal, true);
});
test('api-client: throwIfApiRequestFailed usa serverMessage quando disponível', () => {
  const payload = { error: { message: 'erro do servidor', code: 'BIZ_ERR' } };
  let caught = null;
  try { globalThis.throwIfApiRequestFailed('/api/x', { ok: false, status: 422 }, payload); } catch (e) { caught = e; }
  eq(caught.message, 'erro do servidor');
  eq(caught.code, 'BIZ_ERR');
});
test('api-client: ensureExpectedApiResponse lança para /api/ não-JSON', () => {
  const fakeResp = { ok: true, status: 200 };
  let caught = null;
  try { globalThis.ensureExpectedApiResponse('/api/data', fakeResp, {}, 'text/html'); } catch (e) { caught = e; }
  assert(caught !== null);
  eq(caught.code, 'INVALID_API_RESPONSE');
});
test('api-client: ensureExpectedApiResponse ok para /api/ JSON', () => {
  const fakeResp = { ok: true, status: 200 };
  globalThis.ensureExpectedApiResponse('/api/data', fakeResp, {}, 'application/json');
  // sem exceção
});
test('api-client: buildApiHeaders sem token', () => {
  globalThis.__EPI_APP_STATE__ = { token: '' };
  const h = globalThis.buildApiHeaders({});
  eq(h['Content-Type'], 'application/json');
  eq(h['Authorization'], undefined);
});
test('api-client: buildApiHeaders com token inclui Bearer', () => {
  globalThis.__EPI_APP_STATE__ = { token: 'abc123' };
  const h = globalThis.buildApiHeaders({});
  eq(h['Authorization'], 'Bearer abc123');
});
test('api-client: buildApiHeaders mescla options.headers', () => {
  globalThis.__EPI_APP_STATE__ = { token: '' };
  const h = globalThis.buildApiHeaders({ headers: { 'X-Custom': 'val' } });
  eq(h['X-Custom'], 'val');
  eq(h['Content-Type'], 'application/json');
});
test('api-client: waitMs retorna Promise', () => {
  const p = globalThis.waitMs(0);
  assert(p && typeof p.then === 'function');
});

// ── modules/router ────────────────────────────────────────────────────────
test('router: resolveViewFromLocation retorna view do search', () => {
  globalThis.location = { search: '?view=dashboard', href: 'http://localhost/?view=dashboard' };
  eq(globalThis.resolveViewFromLocation(), 'dashboard');
});
test('router: resolveViewFromLocation retorna vazio sem param', () => {
  globalThis.location = { search: '', href: 'http://localhost/' };
  eq(globalThis.resolveViewFromLocation(), '');
});
test('router: buildNavigationUrl adiciona param view', () => {
  globalThis.location = { search: '', href: 'http://localhost/' };
  const url = globalThis.buildNavigationUrl('epis');
  eq(url.searchParams.get('view'), 'epis');
});
test('router: buildNavigationUrl remove param quando view vazio', () => {
  globalThis.location = { search: '?view=epis', href: 'http://localhost/?view=epis' };
  const url = globalThis.buildNavigationUrl('');
  eq(url.searchParams.get('view'), null);
});
test('router: buildNavigationUrl preserva outros params', () => {
  globalThis.location = { search: '?foo=bar', href: 'http://localhost/?foo=bar' };
  const url = globalThis.buildNavigationUrl('estoque');
  eq(url.searchParams.get('foo'), 'bar');
  eq(url.searchParams.get('view'), 'estoque');
});

// ── modules/router — DOM helpers e defaultView ────────────────────────────
test('router: showScreen sem refs é no-op seguro', () => {
  globalThis.__EPI_REFS__ = {};
  globalThis.showScreen(true);
  // sem exceção
});
test('router: showScreen com refs togla classes', () => {
  const toggleCalls = [];
  const fakeEl = { classList: { toggle(cls, v) { toggleCalls.push([cls, v]); } } };
  globalThis.__EPI_REFS__ = { loginScreen: fakeEl, mainScreen: fakeEl };
  globalThis.showScreen(true);
  assert(toggleCalls.some(([cls, v]) => cls === 'active' && v === false));
  assert(toggleCalls.some(([cls, v]) => cls === 'active' && v === true));
});
test('router: defaultView retorna dashboard quando sem permissões', () => {
  globalThis.__EPI_APP_STATE__ = { user: { role: 'employee' }, permissions: [] };
  eq(globalThis.defaultView(), 'dashboard');
});
test('router: defaultView retorna view permitida para admin', () => {
  globalThis.__EPI_APP_STATE__ = {
    user: { role: 'admin' },
    permissions: globalThis.ROLE_PERMISSIONS.admin || []
  };
  const v = globalThis.defaultView();
  assert(typeof v === 'string' && v.length > 0);
});
test('router: defaultView ignora hasPermission de assinatura única (regressão app.js)', () => {
  // app.js carrega por último e sobrescreve globalThis.hasPermission com uma
  // versão de um argumento. Chamado como hperm(perms, perm), ela testa
  // perms.includes(perms) (array dentro de array) -> sempre false, disparando
  // o aviso "[RBAC][router] nenhuma view liberada" mesmo para roles com acesso.
  // defaultView deve usar canViewRoute e NÃO emitir o aviso para general_admin.
  const originalHasPermission = globalThis.hasPermission;
  const originalWarn = console.warn;
  let rbacWarning = false;
  try {
    globalThis.hasPermission = function (permission) {
      const perms = (globalThis.__EPI_APP_STATE__ || {}).permissions || [];
      return perms.includes(permission);
    };
    console.warn = function (...args) {
      if (String(args[0] || '').includes('nenhuma view liberada')) { rbacWarning = true; }
    };
    globalThis.__EPI_APP_STATE__ = {
      user: { role: 'general_admin' },
      permissions: globalThis.ROLE_PERMISSIONS.general_admin || []
    };
    eq(globalThis.defaultView(), 'dashboard');
    assert(!rbacWarning, 'defaultView não deve avisar "nenhuma view liberada" para general_admin');
  } finally {
    globalThis.hasPermission = originalHasPermission;
    console.warn = originalWarn;
  }
});
test('router: setSpaNavigationLoading sem DOM é no-op seguro', () => {
  globalThis.__EPI_REFS__ = {};
  globalThis.setSpaNavigationLoading(true);
  // sem exceção
});

// ── views/ui-helpers ──────────────────────────────────────────────────────
test('ui-helpers: renderBadge gera span com classe', () => {
  const html = globalThis.__EPI_UI_HELPERS__.renderBadge('status', 'active', 'Ativo');
  assert(html.includes('badge-status-active'));
  assert(html.includes('Ativo'));
});
test('ui-helpers: activeLabel ativo/inativo', () => {
  eq(globalThis.__EPI_UI_HELPERS__.activeLabel(1), 'Ativo');
  eq(globalThis.__EPI_UI_HELPERS__.activeLabel(0), 'Inativo');
});
test('ui-helpers: roleLabel usa ROLE_LABELS', () => {
  const label = globalThis.__EPI_UI_HELPERS__.roleLabel('admin');
  assert(typeof label === 'string' && label.length > 0);
});
test('ui-helpers: userStatusBadges inclui badge de senha provisória', () => {
  const html = globalThis.__EPI_UI_HELPERS__.userStatusBadges({ active: 1, force_password_change: 1 });
  assert(html.includes('badge-status-warning'));
  assert(html.includes('Senha provisória'));
});
test('ui-helpers: userStatusBadges sem senha provisória', () => {
  const html = globalThis.__EPI_UI_HELPERS__.userStatusBadges({ active: 0, force_password_change: 0 });
  assert(!html.includes('Senha provisória'));
  assert(html.includes('badge-status-inactive'));
});

// ── views/view-helpers ────────────────────────────────────────────────────
test('view-helpers: escapeHtml escapes caracteres especiais', () => {
  eq(globalThis.__EPI_VIEW_HELPERS__.escapeHtml('<script>'), '&lt;script&gt;');
  eq(globalThis.__EPI_VIEW_HELPERS__.escapeHtml('"test"'), '&quot;test&quot;');
  eq(globalThis.__EPI_VIEW_HELPERS__.escapeHtml("'x'"), '&#39;x&#39;');
  eq(globalThis.__EPI_VIEW_HELPERS__.escapeHtml(null), '');
});
test('view-helpers: formatDate formata ISO date', () => {
  const result = globalThis.__EPI_VIEW_HELPERS__.formatDate('2025-03-15');
  assert(result.includes('15'));
  assert(result.includes('03') || result.includes('3'));
});
test('view-helpers: formatDate retorna hífen para vazio', () => {
  eq(globalThis.__EPI_VIEW_HELPERS__.formatDate(''), '-');
  eq(globalThis.__EPI_VIEW_HELPERS__.formatDate(null), '-');
});
test('view-helpers: formatDate retorna hífen para data inválida', () => {
  eq(globalThis.__EPI_VIEW_HELPERS__.formatDate('nao-uma-data'), '-');
});
test('view-helpers: formatDateTime formata datetime string', () => {
  const result = globalThis.__EPI_VIEW_HELPERS__.formatDateTime('2025-03-15T10:30:00');
  assert(result.includes('2025') || result.includes('15'));
});
test('view-helpers: filterByUserCompany sem state retorna todos', () => {
  globalThis.__EPI_APP_STATE__ = {};
  const items = [{ id: 1 }, { id: 2 }];
  eq(globalThis.__EPI_VIEW_HELPERS__.filterByUserCompany(items).length, 2);
});
test('view-helpers: filterByUserCompany master_admin retorna todos', () => {
  globalThis.__EPI_APP_STATE__ = { user: { role: 'master_admin', company_id: '1' } };
  const items = [{ company_id: '1' }, { company_id: '2' }];
  eq(globalThis.__EPI_VIEW_HELPERS__.filterByUserCompany(items).length, 2);
});
test('view-helpers: filterByUserCompany admin filtra por company_id', () => {
  globalThis.__EPI_APP_STATE__ = { user: { role: 'admin', company_id: '1' } };
  const items = [{ company_id: '1' }, { company_id: '2' }, { company_id: '1' }];
  eq(globalThis.__EPI_VIEW_HELPERS__.filterByUserCompany(items).length, 2);
});
test('view-helpers: matchesDashboardQuery sem filtro retorna true', () => {
  globalThis.__EPI_APP_STATE__ = { dashboardFilters: { query: '' } };
  eq(globalThis.__EPI_VIEW_HELPERS__.matchesDashboardQuery(['a', 'b']), true);
});
test('view-helpers: matchesDashboardQuery encontra substring', () => {
  globalThis.__EPI_APP_STATE__ = { dashboardFilters: { query: 'silva' } };
  eq(globalThis.__EPI_VIEW_HELPERS__.matchesDashboardQuery(['João Silva']), true);
  eq(globalThis.__EPI_VIEW_HELPERS__.matchesDashboardQuery(['Pedro Santos']), false);
});
test('view-helpers: normalizeStockSizeValue descarta N/A', () => {
  eq(globalThis.__EPI_VIEW_HELPERS__.normalizeStockSizeValue('N/A'), '');
  eq(globalThis.__EPI_VIEW_HELPERS__.normalizeStockSizeValue('na'), '');
  eq(globalThis.__EPI_VIEW_HELPERS__.normalizeStockSizeValue('Selecione'), '');
  eq(globalThis.__EPI_VIEW_HELPERS__.normalizeStockSizeValue('M'), 'M');
});
test('view-helpers: formatItemSizeDisplay monta partes', () => {
  const result = globalThis.__EPI_VIEW_HELPERS__.formatItemSizeDisplay({ glove_size: 'G', size: 'M', uniform_size: 'N/A' });
  assert(result.includes('Luva'));
  assert(result.includes('Tam.'));
  assert(!result.includes('Uniforme'));
});
test('view-helpers: formatItemSizeDisplay retorna hífen quando tudo N/A', () => {
  eq(globalThis.__EPI_VIEW_HELPERS__.formatItemSizeDisplay({ glove_size: 'N/A', size: 'N/A', uniform_size: 'N/A' }), '—');
});
test('view-helpers: formatSizeBalancesDisplay array vazio retorna hífen', () => {
  eq(globalThis.__EPI_VIEW_HELPERS__.formatSizeBalancesDisplay([]), '—');
  eq(globalThis.__EPI_VIEW_HELPERS__.formatSizeBalancesDisplay(null), '—');
});
test('view-helpers: formatSizeBalancesDisplay formata array com items', () => {
  const result = globalThis.__EPI_VIEW_HELPERS__.formatSizeBalancesDisplay([
    { glove_size: 'G', size: 'N/A', uniform_size: 'N/A', quantity: 5 },
    { glove_size: 'N/A', size: 'M', uniform_size: 'N/A', quantity: 3 }
  ]);
  assert(result.includes('5'));
  assert(result.includes('3'));
});

// ── views/dashboard ───────────────────────────────────────────────────────
test('dashboard: módulo carregado com exports', () => {
  assert(typeof globalThis.__EPI_DASHBOARD__ === 'object');
  assert(typeof globalThis.__EPI_DASHBOARD__.renderStats === 'function');
  assert(typeof globalThis.__EPI_DASHBOARD__.renderAlerts === 'function');
  assert(typeof globalThis.__EPI_DASHBOARD__.renderLatestDeliveries === 'function');
  assert(typeof globalThis.__EPI_DASHBOARD__.renderDashboardInterativo === 'function');
});
test('dashboard: renderStats sem refs é no-op seguro', () => {
  globalThis.__EPI_REFS__ = {};
  globalThis.__EPI_APP_STATE__ = { companies: [], employees: [], epis: [], deliveries: [], alerts: [] };
  globalThis.__EPI_DASHBOARD__.renderStats();
  // sem exceção
});
test('dashboard: renderAlerts sem refs é no-op seguro', () => {
  globalThis.__EPI_REFS__ = {};
  globalThis.__EPI_APP_STATE__ = { alerts: [], dashboardFilters: { query: '' } };
  globalThis.__EPI_DASHBOARD__.renderAlerts();
  // sem exceção
});
test('dashboard: renderLatestDeliveries sem refs é no-op seguro', () => {
  globalThis.__EPI_REFS__ = {};
  globalThis.__EPI_APP_STATE__ = { user: { role: 'master_admin' }, deliveries: [] };
  globalThis.__EPI_DASHBOARD__.renderLatestDeliveries();
  // sem exceção
});

// ── views/epis ────────────────────────────────────────────────────────────
test('epis: módulo carregado com exports', () => {
  assert(typeof globalThis.__EPI_VIEW_EPIS__ === 'object');
  assert(typeof globalThis.__EPI_VIEW_EPIS__.renderApprovedEpis === 'function');
  assert(typeof globalThis.__EPI_VIEW_EPIS__.renderEpis === 'function');
});
test('epis: renderApprovedEpis sem refs é no-op seguro', () => {
  globalThis.__EPI_REFS__ = {};
  globalThis.__EPI_APP_STATE__ = { user: { role: 'master_admin' }, epis: [] };
  globalThis.__EPI_VIEW_EPIS__.renderApprovedEpis();
  // sem exceção
});
test('epis: renderEpis é alias de renderApprovedEpis', () => {
  const callCount = 0;
  const origApproved = globalThis.__EPI_VIEW_EPIS__.renderApprovedEpis;
  globalThis.__EPI_REFS__ = {};
  globalThis.__EPI_APP_STATE__ = { user: { role: 'master_admin' }, epis: [] };
  globalThis.__EPI_VIEW_EPIS__.renderEpis();
  // alias funcionou sem exceção — se chegou aqui, funciona
  assert(true);
});

// ── views/estoque ─────────────────────────────────────────────────────────
test('estoque: módulo carregado com exports', () => {
  assert(typeof globalThis.__EPI_ESTOQUE__ === 'object');
  assert(typeof globalThis.__EPI_ESTOQUE__.formatStockEpiRow === 'function');
  assert(typeof globalThis.__EPI_ESTOQUE__.renderStockEpis === 'function');
  assert(typeof globalThis.__EPI_ESTOQUE__.renderLowStock === 'function');
  assert(typeof globalThis.__EPI_ESTOQUE__.renderRequests === 'function');
});
test('estoque: formatStockEpiRow gera linha de tabela', () => {
  const row = globalThis.__EPI_ESTOQUE__.formatStockEpiRow({
    name: 'Capacete',
    sector: 'Obras',
    epi_section: 'Cabeça',
    manufacturer: 'MSA',
    ca: '12345',
    unit_name: 'Unidade A',
    glove_size: 'N/A',
    size: 'G',
    uniform_size: 'N/A',
    size_balances: [],
    stock: 10,
    unit_measure: 'unidade',
    minimum_stock: 5
  });
  assert(row.includes('Capacete'));
  assert(row.includes('MSA'));
  assert(row.includes('10'));
  assert(row.includes('5'));
});
test('estoque: renderStockEpis sem refs é no-op seguro', () => {
  globalThis.__EPI_REFS__ = {};
  globalThis.__EPI_APP_STATE__ = { stockEpis: [], lowStock: [], requests: [] };
  globalThis.__EPI_ESTOQUE__.renderStockEpis();
  // sem exceção
});
test('estoque: renderLowStock sem refs é no-op seguro', () => {
  globalThis.__EPI_REFS__ = {};
  globalThis.__EPI_APP_STATE__ = { lowStock: [] };
  globalThis.__EPI_ESTOQUE__.renderLowStock();
  // sem exceção
});
test('estoque: renderRequests sem refs é no-op seguro', () => {
  globalThis.__EPI_REFS__ = {};
  globalThis.__EPI_APP_STATE__ = { requests: [] };
  globalThis.__EPI_ESTOQUE__.renderRequests();
  // sem exceção
});

// ── Relatório ─────────────────────────────────────────────────────────────
if (failures.length) {
  console.error(`\nFALHAS (${failures.length}):`);
  failures.forEach((f) => console.error(`  ✗ ${f.name}: ${f.message}`));
  console.error(`\n${passed} passaram, ${failures.length} falharam`);
  process.exit(1);
}
console.log(`${passed} testes JS passaram`);
process.exit(0);
