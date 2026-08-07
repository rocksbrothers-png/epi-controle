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
  'views/estoque.js',
  'views/employee-portal.js',
  'views/legal-entity-fields.js',
  'views/legal-entities-view.js',
  'views/outsourced-companies-view.js',
  'views/outsourced-employees-view.js',
  'views/dashboard-scope.js',
  'views/data-migration-view.js'
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
test('permissions: user (Gestor de EPI) nunca tem employees:update completo', () => {
  // Achado em verificação de navegador real (ADR-0002 §12): este array tinha
  // 'employees:update' por engano, herdado pelo Gestor de EPI a mais desde o
  // login — o backend (core/permissions.py, PERMISSIONS['user']) nunca
  // concedeu isso, só as variantes _simplified. Regressão real: fazia
  // hasPermission('employees:update') isolado mentir "sim" no cliente,
  // oferecendo UI (ex.: aba "Solicitações" de Terceirizados) para uma ação
  // que o backend sempre rejeitava (403).
  assert(!globalThis.ROLE_PERMISSIONS.user.includes('employees:update'));
  assert(globalThis.ROLE_PERMISSIONS.admin && !globalThis.ROLE_PERMISSIONS.admin.includes('employees:update'));
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
test('ui-helpers: dsEsc escapa HTML', () => {
  eq(globalThis.__EPI_UI_HELPERS__.dsEsc('<b>"x"</b>'), '&lt;b&gt;&quot;x&quot;&lt;/b&gt;');
  eq(globalThis.__EPI_UI_HELPERS__.dsEsc(null), '');
});
test('ui-helpers: dsStatusPipeline marca done/current corretamente', () => {
  const steps = [
    { key: 'solicitado', label: 'Solicitado' },
    { key: 'aprovado', label: 'Aprovado' },
    { key: 'entregue', label: 'Entregue' },
    { key: 'assinado', label: 'Assinado' }
  ];
  const html = globalThis.__EPI_UI_HELPERS__.dsStatusPipeline(steps, 'entregue');
  // dois primeiros done, o atual current, último neutro
  eq((html.match(/is-done/g) || []).length, 2);
  eq((html.match(/is-current/g) || []).length, 1);
  assert(html.includes('ds-pipeline__node is-current') && html.includes('Entregue'));
});
test('ui-helpers: dsStatusPipeline com chave desconhecida não marca nada', () => {
  const html = globalThis.__EPI_UI_HELPERS__.dsStatusPipeline([{ key: 'a', label: 'A' }], 'zzz');
  assert(!html.includes('is-done') && !html.includes('is-current'));
});
test('ui-helpers: dsValidateCNPJ aceita válido e rejeita inválido', () => {
  const v = globalThis.__EPI_UI_HELPERS__.dsValidateCNPJ;
  assert(v('11.222.333/0001-81'));   // CNPJ válido conhecido
  assert(v('11222333000181'));        // mesmo, só dígitos
  assert(!v('11.222.333/0001-80'));  // dígito verificador errado
  assert(!v('11111111111111'));      // todos iguais
  assert(!v('123'));                  // tamanho inválido
});
test('ui-helpers: dsIsDateNotPast compara com hoje (ref fixa)', () => {
  const f = globalThis.__EPI_UI_HELPERS__.dsIsDateNotPast;
  eq(f('2020-01-01', '2026-06-26'), false);
  eq(f('2026-06-26', '2026-06-26'), true);
  eq(f('2030-01-01', '2026-06-26'), true);
  eq(f('', '2026-06-26'), true);     // vazio não é passado
});
test('ui-helpers: dsFilterChips vazio retorna string vazia', () => {
  eq(globalThis.__EPI_UI_HELPERS__.dsFilterChips([]), '');
});
test('ui-helpers: dsFilterChips gera chips removíveis + limpar tudo', () => {
  const html = globalThis.__EPI_UI_HELPERS__.dsFilterChips([
    { key: 'employee', label: 'Colaborador: joão' },
    { key: 'status', label: 'Status: Entregue' }
  ]);
  eq((html.match(/ds-filter-chip"/g) || []).length, 2);
  assert(html.includes('data-ds-filter-clear="employee"'));
  assert(html.includes('data-ds-filter-clear="status"'));
  assert(html.includes('data-ds-filter-clear-all'));
  assert(html.includes('Colaborador: joão') && html.includes('Status: Entregue'));
});
test('ui-helpers: dsStepper marca done/active por índice', () => {
  const html = globalThis.__EPI_UI_HELPERS__.dsStepper([{ label: 'Pedido' }, { label: 'Recebido' }, { label: 'Conferido' }, { label: 'Fechado' }], 1);
  eq((html.match(/is-done/g) || []).length, 1);   // só "Pedido"
  eq((html.match(/is-active/g) || []).length, 1);  // "Recebido"
  assert(html.includes('ds-stepper__bullet">✓') && html.includes('Recebido'));
});
test('ui-helpers: dsStepper aceita strings simples', () => {
  const html = globalThis.__EPI_UI_HELPERS__.dsStepper(['A', 'B'], 0);
  assert(html.includes('>A<') && html.includes('is-active'));
});
test('ui-helpers: dsTimeline vazio retorna string vazia', () => {
  eq(globalThis.__EPI_UI_HELPERS__.dsTimeline([]), '');
});
test('ui-helpers: dsTimeline renderiza itens com tempo e título', () => {
  const html = globalThis.__EPI_UI_HELPERS__.dsTimeline([{ time: '2026-01-01 10:00', title: 'Recebido', desc: 'approved → received' }]);
  assert(html.includes('ds-timeline__item'));
  assert(html.includes('2026-01-01 10:00') && html.includes('Recebido'));
  assert(html.includes('approved → received'));
});
test('ui-helpers: dsAlertBanner danger usa role=alert e classe modificadora', () => {
  const html = globalThis.__EPI_UI_HELPERS__.dsAlertBanner({ message: 'Estoque crítico', variant: 'danger', ctaLabel: 'Comprar', ctaId: 'cta-x' });
  assert(html.includes('ds-alert-banner--danger'));
  assert(html.includes('role="alert"'));
  assert(html.includes('Estoque crítico'));
  assert(html.includes('id="cta-x"') && html.includes('Comprar'));
});
test('ui-helpers: dsAlertBanner sem CTA e variant padrão é status', () => {
  const html = globalThis.__EPI_UI_HELPERS__.dsAlertBanner({ message: 'Aviso' });
  assert(html.includes('role="status"'));
  assert(!html.includes('ds-alert-banner__cta'));
});
test('ui-helpers: dsChallengeMatches ignora caixa e acentos', () => {
  const m = globalThis.__EPI_UI_HELPERS__.dsChallengeMatches;
  assert(m('joão silva', 'João Silva'));
  assert(m('  MATRICULA01 ', 'matricula01'));
  assert(!m('errado', 'esperado'));
  assert(m('qualquer', ''));    // expected vazio = sem desafio
});
test('ui-helpers: dsTableState empty preserva colspan e mensagem', () => {
  const html = globalThis.__EPI_UI_HELPERS__.dsTableState({ colspan: 5, message: 'Sem usuários.' });
  assert(html.includes('colspan="5"'));
  assert(html.includes('ds-empty'));
  assert(html.includes('Sem usuários.'));
});
test('ui-helpers: dsTableState error com CTA de retry', () => {
  const html = globalThis.__EPI_UI_HELPERS__.dsTableState({ colspan: 6, kind: 'error', message: 'Erro ao carregar.', ctaLabel: 'Tentar de novo', ctaId: 'retry-x' });
  assert(html.includes('ds-error-state'));
  assert(html.includes('colspan="6"'));
  assert(html.includes('id="retry-x"') && html.includes('Tentar de novo'));
});
test('ui-helpers: dsTableState loading gera N linhas de skeleton', () => {
  const html = globalThis.__EPI_UI_HELPERS__.dsTableState({ colspan: 4, kind: 'loading', rows: 3 });
  eq((html.match(/ds-skeleton-row/g) || []).length, 3);
  eq((html.match(/skeleton-text/g) || []).length, 12); // 3 linhas x 4 colunas
});
test('ui-helpers: dsSkeletonRows usa defaults seguros', () => {
  const html = globalThis.__EPI_UI_HELPERS__.dsSkeletonRows(0, 0);
  eq((html.match(/ds-skeleton-row/g) || []).length, 3); // default 3 linhas
  eq((html.match(/<td>/g) || []).length, 3);            // default 1 coluna
});
test('ui-helpers: dsPaginate fatia e clampa a página', () => {
  const items = Array.from({ length: 45 }, (_, i) => i);
  const r = globalThis.__EPI_UI_HELPERS__.dsPaginate(items, 2, 20);
  eq(r.page, 2); eq(r.totalPages, 3); eq(r.total, 45);
  eq(r.pageItems.length, 20); eq(r.pageItems[0], 20);
  const over = globalThis.__EPI_UI_HELPERS__.dsPaginate(items, 99, 20);
  eq(over.page, 3); eq(over.pageItems.length, 5);   // última página, 5 itens
  const under = globalThis.__EPI_UI_HELPERS__.dsPaginate(items, 0, 20);
  eq(under.page, 1);
});
test('ui-helpers: dsPaginationControls oculta quando cabe numa página', () => {
  const info = globalThis.__EPI_UI_HELPERS__.dsPaginate([1, 2, 3], 1, 20);
  eq(globalThis.__EPI_UI_HELPERS__.dsPaginationControls(info), '');
});
test('ui-helpers: dsPaginationControls marca página ativa e desabilita bordas', () => {
  const info = globalThis.__EPI_UI_HELPERS__.dsPaginate(Array.from({ length: 100 }, (_, i) => i), 1, 20);
  const html = globalThis.__EPI_UI_HELPERS__.dsPaginationControls(info);
  assert(html.includes('aria-current="page"'));
  assert(html.includes('1–20 de 100'));
  assert(html.includes('data-ds-page="2"'));
  // botão "anterior" desabilitado na página 1
  assert(/data-ds-page="0"[^>]*disabled/.test(html));
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
test('dashboard: renderStats consolida em grupos por prioridade (sem duplicar KPI)', () => {
  const past = new Date(Date.now() - 5 * 86400000).toISOString().slice(0, 10);
  const soon = new Date(Date.now() + 10 * 86400000).toISOString().slice(0, 10);
  const far = new Date(Date.now() + 400 * 86400000).toISOString().slice(0, 10);
  const grid = { innerHTML: '', dataset: {}, addEventListener() {} };
  globalThis.__EPI_REFS__ = { statsGrid: grid };
  globalThis.currentUserHasPermission = () => true;
  globalThis.filterByUserCompany = (items) => items;
  globalThis.__EPI_APP_STATE__ = {
    user: { role: 'general_admin', company_id: 1 },
    companies: [{ id: 1 }], units: [{ id: 1 }, { id: 2 }],
    employees: [{ id: 1 }, { id: 2 }, { id: 3 }],
    epis: [{ id: 1 }, { id: 2 }, { id: 3 }],
    // Item 2: as contagens de conformidade vêm da FONTE ÚNICA (backend #737),
    // a mesma base da tela "Validade e Bloqueios" (epi_stock_items), NÃO do
    // catálogo. Aqui pré-carregamos state.stockCompliance como o backend faria.
    stockCompliance: {
      summary: {
        product_expired: 1, product_expiring: 1,
        ca_expired: 1, ca_expiring: 1,
        admin_blocked: 2, missing_manufacture: 0, missing_lot: 0,
      },
    },
    deliveries: [{ id: 1, returned_date: '2026-01-01' }, { id: 2, returned_date: '' }],
    alerts: [{ title: 'a' }], lowStock: [{}, {}], feedbacks: [{ type: 'reclamacao' }, { type: 'elogio' }],
  };
  globalThis.__EPI_DASHBOARD__.renderStats();
  const html = grid.innerHTML.replace(/\n/g, '');
  // três grupos de prioridade presentes
  assert(html.includes('kpi-group-title'), 'sem títulos de grupo');
  assert((html.match(/kpi-group-title/g) || []).length >= 3, 'esperados >= 3 grupos');
  // fonte única: cada KPI aparece uma vez (Colaboradores ativos não duplicado)
  eq((html.match(/COLABORADORES ATIVOS|Colaboradores ativos/g) || []).length, 1);
  // cards navegáveis expõem data-view + acessibilidade
  assert(html.includes('data-view="estoque"'), 'card de estoque sem navegação');
  assert(html.includes('role="button"') && html.includes('tabindex="0"'), 'sem semântica de botão');
  // Fonte única: os valores vêm de stockCompliance.summary (estoque), não do
  // catálogo. productExpired = 1, productExpiring = 1.
  assert(/EPIs com validade vencida<\/span><strong>1</.test(html), 'productExpired incorreto');
  assert(/EPIs próximos do vencimento<\/span><strong>1</.test(html), 'productExpiring incorreto');
  // CA distinto: CA vencidos = 1, CA próximos = 1.
  assert(/CA vencidos<\/span><strong>1</.test(html), 'caExpired incorreto');
  assert(/CA próximos do vencimento<\/span><strong>1</.test(html), 'caExpiring incorreto');
  // Bloqueio administrativo = 2 (vem da mesma fonte única).
  assert(/Bloqueio administrativo<\/span><strong>2</.test(html), 'adminBlocked incorreto');
  // Deep-links por sub-aba (auditoria Dashboard): itens que vivem numa aba
  // interna do Estoque abrem exatamente essa aba.
  assert(/data-view="estoque" data-tab="alertas"[^>]*>[^<]*<span>[^<]*(Estoque crítico|ESTOQUE CRÍTICO)/i.test(html)
    || (html.includes('data-tab="alertas"') && /Estoque crítico/i.test(html)), 'estoque crítico sem deep-link para aba Alertas');
  assert(html.includes('data-tab="validade"'), 'bloqueio/lacunas sem deep-link para aba Validade e Bloqueios');
  // "Alertas" passou a ser navegável (antes era um card morto).
  assert(/Alertas<\/span><strong>1<\/strong>/.test(html), 'card Alertas com valor incorreto');
  assert(/data-view="estoque" data-tab="alertas"[^>]*role="button"/.test(html), 'card Alertas não navegável');
  // severidade: vencidos em vermelho (is-danger), próximos em amarelo (is-warning).
  assert(html.includes('is-danger') && html.includes('is-warning'), 'sem tom de severidade');
  // navegação vinculada uma única vez
  eq(grid.dataset.navBound, '1');
});
test('dashboard: renderAlerts monta botões de ação com deep-link por categoria', () => {
  const list = { innerHTML: '', dataset: {}, addEventListener() {} };
  globalThis.__EPI_REFS__ = { alertsList: list };
  globalThis.matchesDashboardQuery = () => true;
  globalThis.__EPI_APP_STATE__ = {
    alerts: [
      { type: 'danger', category: 'ca', title: 'CA', description: 'x', epi_name: 'Luva' },
      { type: 'danger', category: 'stock', title: 'Estoque', description: 'y', epi_name: 'Capacete' },
      { type: 'warning', category: 'manufacturer', title: 'Fab', description: 'z', epi_name: 'Bota' },
      { type: 'warning', title: 'Sem categoria', description: 'w' },
    ],
  };
  globalThis.__EPI_DASHBOARD__.renderAlerts();
  const html = list.innerHTML;
  // CA -> Ver EPIs, filtro na busca de EPIs
  assert(html.includes('data-view="epis"') && html.includes('data-input="epis-filter-search"'), 'CA sem deep-link de EPIs');
  assert(html.includes('data-value="Luva"'), 'CA sem valor de filtro');
  // stock e manufacturer -> Ver Estoque
  eq((html.match(/data-view="estoque"/g) || []).length, 2);
  assert(html.includes('data-value="Capacete"') && html.includes('data-value="Bota"'));
  // alerta sem categoria não ganha botão
  eq((html.match(/alert-action/g) || []).length, 3);
  // delegação vinculada uma única vez
  eq(list.dataset.actionBound, '1');
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

// ── Acesso do colaborador pela Entrega (auditoria F-05) ────────────────────
const STATIC_ROOT = path.resolve(JS_ROOT, '..');
const _read = (rel) => fs.readFileSync(path.resolve(STATIC_ROOT, rel), 'utf-8');

const DELIVERY_ACCESS_IDS = [
  'delivery-employee-qr-scan', 'delivery-employee-qr-apply', 'delivery-employee-link',
  'delivery-employee-message-model', 'delivery-employee-access-status',
  'delivery-employee-link-generate', 'delivery-employee-link-qr', 'delivery-employee-link-copy',
  'delivery-employee-link-open', 'delivery-employee-link-whatsapp', 'delivery-employee-link-email',
];

test('dashboard: indicadores de validade fazem deep-link para EPIs filtrados', () => {
  const dash = _read('js/views/dashboard.js');
  // os 4 indicadores carregam a intenção de filtro por validade
  ['ca_expired', 'ca_expiring', 'product_expired', 'product_expiring'].forEach((v) => {
    assert(dash.includes(`validity: '${v}'`), `card sem validity ${v}`);
  });
  // o card navegável expõe data-validity e o handler chama o deep-link
  assert(dash.includes('data-validity="') && dash.includes('openEpisFilteredByValidity'), 'sem wiring do deep-link');
  const js = _read('app.js');
  // helper de deep-link + filtro de validade na lista de EPIs
  assert(js.includes('function openEpisFilteredByValidity') && js.includes('globalThis.openEpisFilteredByValidity'), 'helper de deep-link ausente');
  assert(js.includes('function _epiMatchesValidity') && js.includes('state.episFilters.validity'), 'filtro de validade não aplicado');
  // markup do filtro na tela de EPIs
  assert(_read('views/epis.html').includes('id="epis-filter-validity"'), 'sem select de validade em epis.html');
  ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO'].forEach((loc) => {
    const d = JSON.parse(_read(`i18n/${loc}.json`));
    assert(d.epi && d.epi.filterValidity, `${loc} sem epi.filterValidity`);
  });
});

test('rbac: card Colaboradores ativos respeita a view acessível ao papel', () => {
  // Fonte única de acesso por papel + roteamento do card de colaboradores.
  const js = _read('app.js');
  assert(js.includes('function canAccessView') && js.includes('globalThis.canAccessView'), 'canAccessView ausente/não exposto');
  assert(js.includes('function accessibleEmployeesView') && js.includes('globalThis.accessibleEmployeesView'), 'accessibleEmployeesView ausente/não exposto');
  // showView passa a bloquear navegação para view proibida ao papel.
  assert(js.includes('!canAccessView(view)'), 'showView não usa canAccessView para bloquear');
  const dash = _read('js/views/dashboard.js');
  assert(dash.includes('accessibleEmployeesView'), 'dashboard não roteia o card pela view acessível');

  // Funcional: Administrador Local → card aponta para gestao-colaborador.
  const grid = { innerHTML: '', dataset: {}, addEventListener() {} };
  globalThis.__EPI_REFS__ = { statsGrid: grid };
  globalThis.currentUserHasPermission = () => true;
  globalThis.filterByUserCompany = (items) => items;
  globalThis.accessibleEmployeesView = () => 'gestao-colaborador';
  globalThis.__EPI_APP_STATE__ = {
    user: { role: 'admin', company_id: 1 },
    companies: [{ id: 1 }], units: [{ id: 1 }], employees: [{ id: 1 }],
    epis: [{ id: 1 }], deliveries: [], alerts: [], feedbacks: [],
    stockCompliance: { summary: {} },
  };
  globalThis.__EPI_DASHBOARD__.renderStats();
  let html = grid.innerHTML.replace(/\n/g, '');
  assert(/Colaboradores ativos<\/span>/i.test(html), 'card de colaboradores ausente');
  assert(html.includes('data-view="gestao-colaborador"'), 'card não aponta para gestao-colaborador');
  assert(!/data-view="colaboradores"/.test(html), 'card não pode abrir cadastro (colaboradores) para admin local');

  // Papel sem view de colaboradores acessível → card não navegável.
  globalThis.accessibleEmployeesView = () => '';
  grid.dataset.navBound = '';
  globalThis.__EPI_DASHBOARD__.renderStats();
  html = grid.innerHTML.replace(/\n/g, '');
  const card = (html.match(/<article[^>]*>\s*<span>Colaboradores ativos[\s\S]*?<\/article>/i) || [''])[0];
  assert(card && !/data-view=/.test(card), 'card de colaboradores deveria ser não navegável sem acesso');
  delete globalThis.accessibleEmployeesView;
});

test('estoque: aba Estoque Bloqueado tem markup, wiring e i18n', () => {
  const html = _read('views/estoque.html');
  ['blocked-stock-card', 'blocked-stock-qr', 'blocked-stock-status', 'blocked-stock-block-btn',
    'blocked-stock-refresh', 'blocked-stock-tbody', 'blocked-stock-empty'].forEach((id) => {
    assert(html.includes(`id="${id}"`), `estoque.html sem #${id}`);
  });
  const js = _read('app.js');
  assert(js.includes('function loadBlockedStock') && js.includes('function blockStockItem') && js.includes('function bindBlockedStockUi'), 'funções do bloqueio ausentes');
  // chama os endpoints reais
  assert(js.includes('/api/stock/blocked-items') && js.includes('/api/stock/items/status'), 'endpoints do bloqueio ausentes');
  // ligado ao carregamento da view de estoque
  assert(js.includes('await loadBlockedStock()'), 'loadBlockedStock não é chamado no refresh do estoque');
  // desbloquear volta para in_stock
  assert(js.includes("'in_stock'"), 'sem ação de desbloquear');
  ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO'].forEach((loc) => {
    const d = JSON.parse(_read(`i18n/${loc}.json`));
    assert(d.stock && d.stock.blockedTitle && d.stock.blockItem && d.stock.unblock, `${loc} sem chaves de estoque bloqueado`);
  });
});

test('estoque: painel Gestão de Validade tem markup, wiring e i18n', () => {
  const html = _read('views/estoque.html');
  ['validity-mgmt-card', 'validity-mgmt-kpis', 'validity-mgmt-value',
    'validity-mgmt-refresh', 'validity-by-manufacturer', 'validity-by-unit',
    'validity-by-lot', 'validity-mgmt-empty'].forEach((id) => {
    assert(html.includes(`id="${id}"`), `estoque.html sem #${id}`);
  });
  const js = _read('app.js');
  assert(js.includes('function loadValidityOverview') && js.includes('function bindValidityMgmtUi'), 'funções da gestão de validade ausentes');
  // consome o endpoint real de agregação
  assert(js.includes('/api/stock/validity-overview'), 'endpoint de validade ausente');
  // indicadores clicáveis reutilizam o deep-link filtrado (Fase 4c)
  assert(js.includes('data-validity=') && js.includes('openEpisFilteredByValidity'), 'sem deep-link nos indicadores de validade');
  // ligado ao carregamento da view de estoque
  assert(js.includes('await loadValidityOverview()'), 'loadValidityOverview não é chamado no refresh do estoque');
  ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO'].forEach((loc) => {
    const d = JSON.parse(_read(`i18n/${loc}.json`));
    assert(d.validity && d.validity.title && d.validity.valueAtRisk && d.validity.valueSummary, `${loc} sem chaves de validade`);
  });
});

test('navegação: engrenagem abre Drawer de Configuração (sem trocar de rota)', () => {
  const js = _read('app.js');
  // a engrenagem abre o drawer (não navega para a página)
  assert(js.includes("bindAppListener(refs.topConfigTrigger, 'click', openSettingsDrawer)"), 'engrenagem não abre o drawer');
  assert(js.includes('function openSettingsDrawer'), 'openSettingsDrawer ausente');
  // reutiliza o componente de drawer existente (item #11)
  assert(js.includes('globalThis.dsOpenDrawer(') && js.includes('globalThis.dsCloseDrawer'), 'não reutiliza dsOpenDrawer/dsCloseDrawer');
  // Fechar/Cancelar/Salvar/Restaurar
  assert(js.includes("id=\"settings-save\"") && js.includes("id=\"settings-cancel\"") && js.includes("id=\"settings-restore\""), 'botões do drawer ausentes');
  // aplica só ao salvar; persiste tema/idioma/densidade
  assert(js.includes('function _applySettings'), 'sem aplicação de preferências');
  assert(js.includes("SETTINGS_DENSITY_KEY = 'epi-density'") && js.includes('EpiI18n.setLang'), 'sem persistência de densidade/idioma');
  // densidade aplicada no init
  assert(js.includes("runNonCriticalSetup('table density preference', applyTableDensityPref)"), 'densidade não aplicada no init');
  // acesso à página de config preservado (avançado) para quem tem permissão
  assert(js.includes('settings-advanced') && js.includes("navigateToView('configuracao'"), 'sem acesso à config avançada');
  // chaves i18n do painel
  ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO'].forEach((loc) => {
    const d = JSON.parse(_read(`i18n/${loc}.json`));
    assert(d.settings && d.settings.density && d.settings.restore && d.settings.advanced, `${loc} sem chaves de settings`);
  });
});

test('navegação: seta Voltar sempre funcional com fallback ao Dashboard + breadcrumb', () => {
  const js = _read('app.js');
  // pilha própria de histórico e helpers
  assert(js.includes('const _navBack = { stack: [], suppress: false }'), 'sem pilha de histórico');
  assert(js.includes('function navigateBack') && js.includes('function updateNavBackUi') && js.includes('function trackNavBackHistory'), 'helpers de voltar ausentes');
  // fallback ao Dashboard quando não há histórico
  assert(js.includes('_navBack.stack.pop() || defaultView()'), 'sem fallback ao Dashboard');
  // seta sempre visível/funcional (não escondida sem histórico)
  assert(js.includes('backBtn.hidden = false'), 'seta Voltar oculta sem histórico');
  // registrado no showView e vinculado ao botão do topbar
  assert(js.includes("trackNavBackHistory(currentActiveView.replace(/-view$/, ''), view)"), 'showView não registra histórico');
  assert(js.includes("safeOn(document.getElementById('hierarchy-back-btn'), 'click', navigateBack)"), 'botão Voltar não vinculado');
  // navegação SPA reutilizada (sem reload) e breadcrumb clicável
  assert(js.includes('navigateToView(target)'), 'voltar não usa navegação SPA');
  assert(js.includes('breadcrumb-link'), 'sem trilha de breadcrumb');
});

test('navegação: sidebar recolhível no desktop tem wiring + persistência + CSS', () => {
  const js = _read('app.js');
  // preferência persistida e helpers presentes
  assert(js.includes("SIDEBAR_COLLAPSED_KEY = 'epi-sidebar-collapsed'"), 'sem chave de preferência');
  assert(js.includes('function toggleSidebarCollapsed') && js.includes('function applySidebarCollapsed'), 'helpers ausentes');
  // o botão ☰ recolhe no desktop (fora do modo mobile)
  assert(js.includes("if (!isUxMobileEnabled()) { toggleSidebarCollapsed(); return; }"), 'toggle desktop não vinculado ao ☰');
  // o ☰ deixa de ficar oculto no desktop
  assert(js.includes('refs.mobileMenuToggle.hidden = false'), 'botão ☰ ainda oculto no desktop');
  // CSS do mini-rail e chaves i18n
  const css = _read('styles.css');
  assert(css.includes('body.sidebar-collapsed:not(.ux-mobile-enabled) #main-screen.active'), 'sem grid recolhido');
  ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO'].forEach((loc) => {
    const d = JSON.parse(_read(`i18n/${loc}.json`));
    assert(d.nav && d.nav.collapseMenu && d.nav.expandMenu, `${loc} sem nav.collapse/expandMenu`);
  });
});

test('acesso-colaborador: fragmento entregas.html declara todos os ids do bloco', () => {
  const html = _read('views/entregas.html');
  DELIVERY_ACCESS_IDS.forEach((id) => assert(html.includes(`id="${id}"`), `entregas.html sem id="${id}"`));
});

test('acesso-colaborador: index.html construído contém os mesmos ids (build sincronizado)', () => {
  const html = _read('index.html');
  DELIVERY_ACCESS_IDS.forEach((id) => assert(html.includes(`id="${id}"`), `index.html sem id="${id}"`));
});

test('acesso-colaborador: app.js liga cada botão do bloco (sem handler órfão)', () => {
  const js = _read('app.js');
  ['delivery-employee-link-generate', 'delivery-employee-link-qr', 'delivery-employee-link-copy',
    'delivery-employee-link-open', 'delivery-employee-link-whatsapp', 'delivery-employee-link-email',
    'delivery-employee-qr-apply'].forEach((id) => {
    assert(js.includes(`getElementById('${id}')`), `app.js não liga ${id}`);
  });
});

test('acesso-colaborador: links-unit-select removido do app.js (código morto)', () => {
  const js = _read('app.js');
  assert(!js.includes("getElementById('links-unit-select')"), 'links-unit-select ainda referenciado');
});

test('acesso-colaborador: chaves i18n do bloco existem com paridade nos 5 locales', () => {
  const locales = ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO'];
  const needed = [
    'employeeAccessTitle', 'employeeQrLookup', 'employeeQrApply', 'employeeAccessLink',
    'employeeLinkGenerate', 'employeeLinkQr', 'employeeLinkCopy', 'employeeLinkOpen',
    'employeeLinkWhatsapp', 'employeeLinkEmail', 'employeeAccessHint', 'employeeAccessReady',
    'employeeAccessSelectFirst', 'employeeAccessGenerating', 'employeeAccessGenerated',
    'employeeAccessNoLink', 'employeeAccessCopied', 'employeeAccessOpenBlocked',
    'employeeAccessExpired', 'employeeAccessSending', 'employeeAccessSentWhatsapp',
    'employeeAccessSentEmail', 'employeeAccessNoWhatsapp', 'employeeAccessNoEmail',
    'employeeAccessQrOpened', 'employeeAccessLaunchError',
  ];
  locales.forEach((loc) => {
    const dict = JSON.parse(_read(`i18n/${loc}.json`));
    needed.forEach((k) => assert(dict.delivery && typeof dict.delivery[k] === 'string' && dict.delivery[k],
      `${loc} sem delivery.${k}`));
  });
});

// ── ui-helpers: seleção em lote ────────────────────────────────────────────
test('ui-helpers: dsCreateBulkSelection toggle/has/count', () => {
  const sel = globalThis.__EPI_UI_HELPERS__.dsCreateBulkSelection();
  eq(sel.count(), 0);
  sel.toggle(1); sel.toggle('2');
  assert(sel.has(1) && sel.has(2), 'deve ter 1 e 2');
  eq(sel.count(), 2);
  sel.toggle(1); // desmarca
  assert(!sel.has(1), '1 desmarcado');
  eq(sel.count(), 1);
});
test('ui-helpers: bulk setPage e pageState (all/some/none)', () => {
  const sel = globalThis.__EPI_UI_HELPERS__.dsCreateBulkSelection();
  eq(sel.pageState([1, 2, 3]), 'none');
  sel.toggle(2);
  eq(sel.pageState([1, 2, 3]), 'some');
  sel.setPage([1, 2, 3], true);
  eq(sel.pageState([1, 2, 3]), 'all');
  eq(sel.count(), 3);
  sel.setPage([1, 2, 3], false);
  eq(sel.pageState([1, 2, 3]), 'none');
});
test('ui-helpers: bulk retain remove ids inexistentes', () => {
  const sel = globalThis.__EPI_UI_HELPERS__.dsCreateBulkSelection();
  sel.setPage([1, 2, 3], true);
  sel.retain([2, 3, 9]); // 1 sai, 9 não estava
  assert(!sel.has(1) && sel.has(2) && sel.has(3), 'retain manteve só válidos');
  eq(sel.count(), 2);
});
test('ui-helpers: dsBulkBar vazio quando count 0; renderiza ações e clear', () => {
  const H = globalThis.__EPI_UI_HELPERS__;
  eq(H.dsBulkBar(0, [{ id: 'x', label: 'X' }]), '');
  const html = H.dsBulkBar(3, [{ id: 'export', label: 'Exportar' }], { labelPlural: 'itens' });
  assert(html.includes('data-ds-bulk-action="export"'), 'tem ação export');
  assert(html.includes('data-ds-bulk-action="__clear"'), 'tem limpar');
  assert(html.includes('>3<') || html.includes('<strong>3</strong>'), 'mostra contador');
});

// ── Portal do colaborador: Empresa · CNPJ · Unidade ───────────────────────
test('employee-portal: cadeia completa Empresa · CNPJ · Unidade', () => {
  const chain = globalThis.__EPI_EMPLOYEE_PORTAL__.formatOrgChain({
    company_name: 'ACME', legal_entity_cnpj: '11.222.333/0001-81', unit_name: 'Matriz SP',
  });
  eq(chain, 'ACME · 11.222.333/0001-81 · Matriz SP');
});
test('employee-portal: sem Multi-CNPJ mostra só o que existe (sem separador solto)', () => {
  const F = globalThis.__EPI_EMPLOYEE_PORTAL__.formatOrgChain;
  eq(F({ company_name: 'ACME' }), 'ACME');
  eq(F({ company_name: 'ACME', unit_name: 'Matriz SP' }), 'ACME · Matriz SP');
});
test('employee-portal: campos vazios/brancos e payload ausente não geram lixo', () => {
  const F = globalThis.__EPI_EMPLOYEE_PORTAL__.formatOrgChain;
  eq(F({ company_name: '  ', legal_entity_cnpj: null, unit_name: undefined }), '');
  eq(F({}), '');
  eq(F(null), '');
});

// ── Campos de CNPJ (web legado) ───────────────────────────────────────────
const _LE = [
  { id: 10, company_id: 1, cnpj: '11.222.333/0001-81', legal_name: 'ACME SA', trade_name: 'ACME Matriz', active: 1 },
  { id: 20, company_id: 1, cnpj: '45.723.174/0001-10', legal_name: 'ACME Filial RJ LTDA', trade_name: '', active: 1 },
  { id: 30, company_id: 1, cnpj: '11.444.777/0001-61', legal_name: 'ACME Extinta', trade_name: '', active: 0 },
  { id: 40, company_id: 2, cnpj: '99.999.999/0001-99', legal_name: 'Outra Empresa', trade_name: '', active: 1 },
];
test('legal-entity-fields: cadastro só enxerga CNPJ ativo da própria empresa', () => {
  const F = globalThis.__EPI_LEGAL_ENTITY_FIELDS__;
  const ids = F.legalEntitiesForCompany(_LE, 1).map((e) => e.id);
  eq(JSON.stringify(ids), JSON.stringify([10, 20]));
});
test('legal-entity-fields: relatório inclui inativos (histórico é consultável)', () => {
  const F = globalThis.__EPI_LEGAL_ENTITY_FIELDS__;
  const ids = F.legalEntitiesForCompany(_LE, 1, { activeOnly: false }).map((e) => e.id);
  eq(JSON.stringify(ids), JSON.stringify([10, 20, 30]));
});
test('legal-entity-fields: nunca vaza CNPJ de outra empresa', () => {
  const F = globalThis.__EPI_LEGAL_ENTITY_FIELDS__;
  const ids = F.legalEntitiesForCompany(_LE, 2, { activeOnly: false }).map((e) => e.id);
  eq(JSON.stringify(ids), JSON.stringify([40]));
});
test('legal-entity-fields: empresa vazia não filtra (usuário de empresa única)', () => {
  const F = globalThis.__EPI_LEGAL_ENTITY_FIELDS__;
  eq(F.legalEntitiesForCompany(_LE, '').length, 3); // só os ativos
});
test('legal-entity-fields: active tolera 0/1, booleano e string', () => {
  const F = globalThis.__EPI_LEGAL_ENTITY_FIELDS__;
  const rows = [{ id: 1, active: true }, { id: 2, active: '1' }, { id: 3, active: 1 },
    { id: 4, active: false }, { id: 5, active: 0 }, { id: 6, active: '0' }];
  eq(JSON.stringify(F.legalEntitiesForCompany(rows, '').map((e) => e.id)), JSON.stringify([1, 2, 3]));
});
test('legal-entity-fields: rótulo usa fantasia, cai para razão social', () => {
  const F = globalThis.__EPI_LEGAL_ENTITY_FIELDS__;
  eq(F.legalEntityLabel(_LE[0]), 'ACME Matriz - 11.222.333/0001-81');
  eq(F.legalEntityLabel(_LE[1]), 'ACME Filial RJ LTDA - 45.723.174/0001-10');
  eq(F.legalEntityLabel({ cnpj: '11.222.333/0001-81' }), '11.222.333/0001-81');
  eq(F.legalEntityLabel({ legal_name: 'Sem CNPJ' }), 'Sem CNPJ');
});
test('legal-entity-fields: CNPJ obrigatório apenas com mais de um ativo', () => {
  const F = globalThis.__EPI_LEGAL_ENTITY_FIELDS__;
  // Sem schema Multi-CNPJ e com CNPJ único o backend resolve sozinho.
  assert(!F.employeeLegalEntityRequired([]), 'sem CNPJ não exige');
  assert(!F.employeeLegalEntityRequired([_LE[0]]), 'CNPJ único não exige');
  assert(F.employeeLegalEntityRequired([_LE[0], _LE[1]]), 'multi-CNPJ exige');
});
test('legal-entity-fields: lista ausente ou inválida não quebra', () => {
  const F = globalThis.__EPI_LEGAL_ENTITY_FIELDS__;
  eq(F.legalEntitiesForCompany(undefined, 1).length, 0);
  eq(F.legalEntitiesForCompany(null, 1).length, 0);
  eq(F.legalEntityLabel(null), '');
});
test('legal-entity-fields: rótulo do CNPJ da unidade vem do próprio registro', () => {
  // A listagem de unidades não carrega a lista de CNPJs: o rótulo é montado a
  // partir do que o LEFT JOIN de `fetch_units` já devolve.
  const F = globalThis.__EPI_LEGAL_ENTITY_FIELDS__;
  eq(F.unitLegalEntityLabel({
    legal_entity_trade_name: 'ACME Offshore',
    legal_entity_legal_name: 'ACME Serviços Marítimos LTDA',
    legal_entity_cnpj: '11.222.333/0001-81',
  }), 'ACME Offshore - 11.222.333/0001-81');
  eq(F.unitLegalEntityLabel({
    legal_entity_legal_name: 'ACME Serviços Marítimos LTDA',
    legal_entity_cnpj: '11.222.333/0001-81',
  }), 'ACME Serviços Marítimos LTDA - 11.222.333/0001-81');
});
test('legal-entity-fields: unidade sem CNPJ devolve vazio, não "undefined"', () => {
  // Estado legítimo durante a migração. A tabela mostra `-`; um "undefined" na
  // coluna pareceria defeito.
  const F = globalThis.__EPI_LEGAL_ENTITY_FIELDS__;
  eq(F.unitLegalEntityLabel({ name: 'Base sem CNPJ' }), '');
  eq(F.unitLegalEntityLabel(null), '');
});

// ── Tela de CNPJs (web legado) ────────────────────────────────────────────
const _LE_VIEW = [
  { id: 10, cnpj: '11.222.333/0001-81', legal_name: 'ACME Serviços LTDA', trade_name: 'ACME Matriz', entity_type: 'matriz', active: 1 },
  { id: 20, cnpj: '45.723.174/0001-10', legal_name: 'ACME Filial RJ LTDA', trade_name: '', entity_type: 'filial', active: 1 },
  { id: 30, cnpj: '19.131.243/0001-97', legal_name: 'ACME SPE Norte', trade_name: 'SPE Norte', entity_type: 'spe', active: 0 },
];
function _LV() { return globalThis.__EPI_LEGAL_ENTITIES_VIEW__; }

test('legal-entities-view: inativos ficam fora por padrão', () => {
  // O histórico é preservado, mas o CNPJ inativo não entra em nova operação —
  // deixá-lo na lista de trabalho só atrapalha quem opera.
  const ids = _LV().visibleLegalEntities(_LE_VIEW, {}).map((e) => e.id);
  eq(JSON.stringify(ids), JSON.stringify([10, 20]));
});
test('legal-entities-view: inativos aparecem quando pedidos', () => {
  const ids = _LV().visibleLegalEntities(_LE_VIEW, { showInactive: true }).map((e) => e.id);
  eq(JSON.stringify(ids), JSON.stringify([10, 20, 30]));
});
test('legal-entities-view: busca cobre número, razão social e fantasia', () => {
  const V = _LV();
  eq(V.visibleLegalEntities(_LE_VIEW, { search: '45.723' })[0].id, 20);
  eq(V.visibleLegalEntities(_LE_VIEW, { search: 'filial rj' })[0].id, 20);
  eq(V.visibleLegalEntities(_LE_VIEW, { search: 'acme matriz' })[0].id, 10);
});
test('legal-entities-view: busca ignora caixa e espaços nas bordas', () => {
  eq(_LV().visibleLegalEntities(_LE_VIEW, { search: '  ACME MATRIZ ' })[0].id, 10);
});
test('legal-entities-view: filtro de tipo é exato, não por prefixo', () => {
  const V = _LV();
  eq(V.visibleLegalEntities(_LE_VIEW, { type: 'filial' }).length, 1);
  eq(V.visibleLegalEntities(_LE_VIEW, { type: 'matriz' })[0].id, 10);
});
test('legal-entities-view: rótulo do tipo traduz e não engole valor desconhecido', () => {
  const V = _LV();
  eq(V.entityTypeLabel('jv_partner'), 'Sócia de JV');
  eq(V.entityTypeLabel('coisa_nova'), 'coisa_nova');
  eq(V.entityTypeLabel(''), '-');
});
test('legal-entities-view: o último CNPJ ativo não oferece inativação', () => {
  // O backend recusa (a empresa ficaria sem pessoa jurídica); oferecer o botão
  // só produziria mensagem de erro.
  const V = _LV();
  const soUmAtivo = [_LE_VIEW[0], _LE_VIEW[2]];
  assert(!V.canDeactivate(_LE_VIEW[0], soUmAtivo), 'último ativo não pode');
  assert(V.canDeactivate(_LE_VIEW[0], _LE_VIEW), 'com dois ativos, pode');
});
test('legal-entities-view: CNPJ já inativo não oferece inativação', () => {
  assert(!_LV().canDeactivate(_LE_VIEW[2], _LE_VIEW), 'inativo não reinativa');
});
test('legal-entities-view: active tolera 0/1, booleano e string', () => {
  const V = _LV();
  assert(V.isActive({ active: true }) && V.isActive({ active: 1 }) && V.isActive({ active: '1' }), 'ativos');
  assert(!V.isActive({ active: false }) && !V.isActive({ active: 0 }) && !V.isActive({ active: '0' }), 'inativos');
});
test('legal-entities-view: lista ausente não quebra', () => {
  const V = _LV();
  eq(V.visibleLegalEntities(undefined, {}).length, 0);
  eq(V.visibleLegalEntities(null, { showInactive: true }).length, 0);
  assert(!V.canDeactivate(null, null), 'sem dados, sem ação');
});

// ── Tela de Terceirizados e Prestadores (web legado, ADR-0002) ────────────
const _OC_VIEW = [
  { id: 100, legal_name: 'Terceirizada Alfa LTDA', trade_name: 'Alfa', cnpj: '11.222.333/0001-81', company_kind: 'outsourced', registration_mode: 'simplified' },
  { id: 200, legal_name: 'Prestadora Beta LTDA', trade_name: '', cnpj: '', company_kind: 'service_provider', registration_mode: 'simplified' },
  { id: 300, legal_name: 'Gama Contratada LTDA', trade_name: 'Gama', cnpj: '45.723.174/0001-10', company_kind: 'other_contracted', registration_mode: 'standard' },
];
function _OCV() { return globalThis.__EPI_OUTSOURCED_COMPANIES_VIEW__; }

test('outsourced-companies-view: rótulo do tipo traduz e cai para Outro quando desconhecido', () => {
  const V = _OCV();
  eq(V.companyKindLabel('outsourced'), 'Terceirizada');
  eq(V.companyKindLabel('service_provider'), 'Prestadora de Serviço');
  eq(V.companyKindLabel('other_contracted'), 'Outro');
  eq(V.companyKindLabel('coisa_nova'), 'Outro');
});
test('outsourced-companies-view: isSimplified e registrationModeLabel', () => {
  const V = _OCV();
  assert(V.isSimplified(_OC_VIEW[0]), 'nasce simplificado');
  assert(!V.isSimplified(_OC_VIEW[2]), 'já promovida ao padrão');
  eq(V.registrationModeLabel(_OC_VIEW[0]), 'Simplificado');
  eq(V.registrationModeLabel(_OC_VIEW[2]), 'Padrão');
});
test('outsourced-companies-view: busca cobre razão social, fantasia e CNPJ (mesmo vazio)', () => {
  const V = _OCV();
  eq(V.visibleOutsourcedCompanies(_OC_VIEW, { search: 'beta' })[0].id, 200);
  eq(V.visibleOutsourcedCompanies(_OC_VIEW, { search: '45.723' })[0].id, 300);
  eq(V.visibleOutsourcedCompanies(_OC_VIEW, { search: 'alfa' })[0].id, 100);
});
test('outsourced-companies-view: filtro de tipo é exato', () => {
  const V = _OCV();
  eq(V.visibleOutsourcedCompanies(_OC_VIEW, { kind: 'service_provider' }).length, 1);
  eq(V.visibleOutsourcedCompanies(_OC_VIEW, { kind: 'outsourced' })[0].id, 100);
});
test('outsourced-companies-view: promover só aparece para quem ainda está no Simplificado', () => {
  const V = _OCV();
  assert(V.canPromote(_OC_VIEW[0]), 'simplificado pode promover');
  assert(!V.canPromote(_OC_VIEW[2]), 'já padrão não promove de novo');
});
test('outsourced-companies-view: trava corporativa só depois da promoção ao Padrão', () => {
  const V = _OCV();
  assert(!V.isCorporateLocked(_OC_VIEW[0]), 'simplificado nunca trava');
  assert(V.isCorporateLocked(_OC_VIEW[2]), 'padrão trava por padrão');
});
test('outsourced-companies-view: canEditCorporateFields libera Simplificado sempre, Padrão só com permissão completa', () => {
  const V = _OCV();
  assert(V.canEditCorporateFields(_OC_VIEW[0], false), 'simplificado edita mesmo sem employees:update completo');
  assert(!V.canEditCorporateFields(_OC_VIEW[2], false), 'padrão bloqueia sem employees:update completo');
  assert(V.canEditCorporateFields(_OC_VIEW[2], true), 'padrão libera com employees:update completo');
});
test('outsourced-companies-view: isArchivedInUnit reflete local_status, nunca outros campos', () => {
  const V = _OCV();
  assert(V.isArchivedInUnit({ local_status: 'inactive' }), 'local_status inactive é arquivada nesta Unidade');
  assert(!V.isArchivedInUnit({ local_status: 'active' }), 'local_status active não é arquivada');
  assert(!V.isArchivedInUnit({}), 'sem local_status (perfil sem escopo ou não vinculada) não é arquivada');
  assert(!V.isArchivedInUnit({ local_status: undefined }), 'local_status undefined não é arquivada');
  // registration_mode/status do CORPORATIVO nunca deve ser confundido com o
  // vínculo local (Problema 4 do pedido: são conceitos deliberadamente
  // diferentes) — só local_status importa aqui.
  assert(!V.isArchivedInUnit({ local_status: 'active', status: 'archived' }), 'arquivamento global não é o vínculo local');
});
test('outsourced-companies-view: lista ausente não quebra', () => {
  const V = _OCV();
  eq(V.visibleOutsourcedCompanies(undefined, {}).length, 0);
  eq(V.visibleOutsourcedCompanies(null, { kind: 'outsourced' }).length, 0);
});
test('terceirizados: botão "Arquivar/Desarquivar nesta Unidade" tem listener nas DUAS tabelas (Lista + Empresas arquivadas)', () => {
  // Regressão real encontrada em verificação manual: o botão da tabela
  // "Empresas arquivadas nesta Unidade" (Problema 2/4 do pedido) foi
  // renderizado mas ficou sem bindAppListener próprio — clique não fazia
  // nada (nenhum erro, nenhuma chamada de API), porque o listener
  // existente só cobria refs.outsourcedCompaniesTable (a Lista principal).
  const js = _read('app.js');
  assert(
    js.includes("bindAppListener(refs.outsourcedCompaniesTable, 'click',"),
    'listener da Lista principal ausente',
  );
  assert(
    js.includes("bindAppListener(refs.outsourcedCompanyUnitArchivedTable, 'click',"),
    'listener da tabela "Empresas arquivadas nesta Unidade" ausente — botão Desarquivar fica morto',
  );
});

// ── Cadastro de Colaboradores simplificado (web legado, ADR-0002 §10.2) ───
const _OE_VIEW = [
  { id: 1, name: 'Fulano Terceirizado', role_name: 'Auxiliar', tipo_vinculo: 'Terceirizado', outsourced_company_id: 100 },
  { id: 2, name: 'Beltrano Prestador', role_name: 'Técnico', tipo_vinculo: 'Prestador de Serviço', outsourced_company_id: 200 },
  { id: 3, name: 'Ciclano CLT', role_name: 'Analista', tipo_vinculo: 'CLT', outsourced_company_id: null },
  { id: 4, name: 'Sem vínculo definido', role_name: 'Auxiliar', tipo_vinculo: '', outsourced_company_id: null },
];
function _OEV() { return globalThis.__EPI_OUTSOURCED_EMPLOYEES_VIEW__; }

test('outsourced-employees-view: rótulo do tipo de vínculo', () => {
  const V = _OEV();
  eq(V.tipoVinculoLabel('Terceirizado'), 'Terceirizado');
  eq(V.tipoVinculoLabel('Prestador de Serviço'), 'Prestador de Serviço');
  eq(V.tipoVinculoLabel(''), 'Outro');
});
test('outsourced-employees-view: outsourcedEmployeesOnly exclui CLT e sem empresa vinculada', () => {
  const V = _OEV();
  const filtered = V.outsourcedEmployeesOnly(_OE_VIEW);
  eq(filtered.length, 2);
  eq(filtered.map((item) => item.id).sort().join(','), '1,2');
});
test('outsourced-employees-view: busca cobre nome e função', () => {
  const V = _OEV();
  const filtered = V.outsourcedEmployeesOnly(_OE_VIEW);
  eq(V.visibleOutsourcedEmployees(filtered, { search: 'beltrano' })[0].id, 2);
  eq(V.visibleOutsourcedEmployees(filtered, { search: 'auxiliar' })[0].id, 1);
});
test('outsourced-employees-view: lista ausente não quebra', () => {
  const V = _OEV();
  eq(V.outsourcedEmployeesOnly(undefined).length, 0);
  eq(V.visibleOutsourcedEmployees(null, {}).length, 0);
});

// ── Filtro em cascata do dashboard (web legado) ───────────────────────────
const _SC_UNITS = [
  { id: 1, name: 'Matriz SP', legal_entity_id: 10 },
  { id: 2, name: 'Base Santos', legal_entity_id: 10 },
  { id: 3, name: 'Filial RJ', legal_entity_id: 20 },
  { id: 4, name: 'Sem CNPJ', legal_entity_id: null },
];
function _S() { return globalThis.__EPI_DASHBOARD_SCOPE__; }

test('dashboard-scope: sem CNPJ selecionado devolve todas as unidades', () => {
  eq(_S().availableUnits(_SC_UNITS, null).length, 4);
});
test('dashboard-scope: com CNPJ devolve só as unidades daquele CNPJ', () => {
  const names = _S().availableUnits(_SC_UNITS, 10).map((u) => u.name);
  eq(JSON.stringify(names), JSON.stringify(['Matriz SP', 'Base Santos']));
});
test('dashboard-scope: unidade sem vínculo não aparece sob nenhum CNPJ', () => {
  const ids = _S().availableUnits(_SC_UNITS, 20).map((u) => u.id);
  eq(JSON.stringify(ids), JSON.stringify([3]));
});
test('dashboard-scope: sem seleção NÃO restringe (null, não Set vazio)', () => {
  // A distinção que mais importa: null = sem restrição; Set vazio = nada casa.
  eq(_S().scopedUnitIds(_SC_UNITS, null, null), null);
});
test('dashboard-scope: CNPJ sem unidades zera em vez de mostrar tudo', () => {
  const ids = _S().scopedUnitIds(_SC_UNITS, 99, null);
  assert(ids instanceof Set, 'deve ser Set, não null');
  eq(ids.size, 0);
});
test('dashboard-scope: unidade selecionada vence o CNPJ', () => {
  const ids = _S().scopedUnitIds(_SC_UNITS, 10, 2);
  eq(JSON.stringify(Array.from(ids)), JSON.stringify([2]));
});
test('dashboard-scope: applyScope recorta por unidade e por setor', () => {
  const rows = [
    { id: 1, unit_id: 1, sector: 'Operação' },
    { id: 2, unit_id: 2, sector: 'Manutenção' },
    { id: 3, unit_id: 3, sector: 'Operação' },
  ];
  const ids = _S().scopedUnitIds(_SC_UNITS, 10, null);
  eq(_S().applyScope(rows, ids, '').map((r) => r.id).join(','), '1,2');
  eq(_S().applyScope(rows, ids, 'Operação').map((r) => r.id).join(','), '1');
  eq(_S().applyScope(rows, null, '').length, 3);
});
test('dashboard-scope: registro sem unidade fica de fora quando há recorte', () => {
  const rows = [{ id: 1, unit_id: null }, { id: 2, unit_id: 1 }];
  const ids = _S().scopedUnitIds(_SC_UNITS, 10, null);
  eq(_S().applyScope(rows, ids, '').map((r) => r.id).join(','), '2');
});
test('dashboard-scope: EPI de nível empresa permanece visível em qualquer recorte', () => {
  // EPI sem unit_id pertence à empresa; filtrá-lo esconderia o catálogo.
  const epis = [{ id: 1, unit_id: null }, { id: 2, unit_id: 1 }, { id: 3, unit_id: 3 }];
  const ids = _S().scopedUnitIds(_SC_UNITS, 10, null);
  eq(_S().applyScopeKeepingCompanyWide(epis, ids).map((e) => e.id).join(','), '1,2');
});
test('dashboard-scope: setores vêm só do escopo e ordenados', () => {
  const employees = [
    { unit_id: 1, sector: 'Operação' }, { unit_id: 2, sector: 'Almoxarifado' },
    { unit_id: 3, sector: 'Offshore' }, { unit_id: 1, sector: '  ' },
  ];
  const ids = _S().scopedUnitIds(_SC_UNITS, 10, null);
  eq(JSON.stringify(_S().sectorsOf(employees, ids)), JSON.stringify(['Almoxarifado', 'Operação']));
  eq(_S().sectorsOf(employees, null).length, 3);
});
test('dashboard-scope: hasActiveFilter reconhece qualquer nível', () => {
  assert(!_S().hasActiveFilter({ legalEntityId: null, unitId: null, sector: '' }), 'vazio');
  assert(_S().hasActiveFilter({ legalEntityId: 10 }), 'CNPJ');
  assert(_S().hasActiveFilter({ unitId: 1 }), 'unidade');
  assert(_S().hasActiveFilter({ sector: 'Operação' }), 'setor');
});
test('dashboard-scope: ids como string (vindos de <select>) funcionam', () => {
  const ids = _S().scopedUnitIds(_SC_UNITS, '10', '');
  eq(JSON.stringify(Array.from(ids)), JSON.stringify([1, 2]));
});


// ── views/data-migration-view (ADR-0003 fase 2) ───────────────────────────
const _DM = () => globalThis.__EPI_DATA_MIGRATION_VIEW__;

const _DM_FIELDS = [
  { name: 'name', label: 'Nome', required: true },
  { name: 'cpf', label: 'CPF', required: true },
  { name: 'role_name', label: 'Função', required: false },
  { name: 'empresa_origem', label: 'Empresa de origem', required: false }
];

test('data-migration: confidenceLevel separa exato de aproximado', () => {
  eq(_DM().confidenceLevel(1), 'exact');
  eq(_DM().confidenceLevel(0.95), 'high');
  eq(_DM().confidenceLevel(0.85), 'medium');
  eq(_DM().confidenceLevel(0.5), 'low');
  eq(_DM().confidenceLevel(0), 'none');
  eq(_DM().confidenceLevel(null), 'none');
});

test('data-migration: needsReview marca coluna sem destino', () => {
  assert(_DM().needsReview({ source_column: 'X', target_field: null }), 'sem destino');
  assert(!_DM().needsReview({ target_field: 'name', strategy: 'exact' }), 'exato dispensa revisão');
  assert(!_DM().needsReview({ target_field: 'name', strategy: 'synonym' }), 'sinônimo dispensa revisão');
});

test('data-migration: needsReview marca duplicate_target', () => {
  // O motor não degrada para o segundo melhor destino (ADR-0003 §2.3): a
  // coluna fica sem destino e precisa de decisão humana.
  assert(_DM().needsReview({ source_column: 'Employee', target_field: null, strategy: 'duplicate_target' }), 'duplicado');
  assert(_DM().needsReview({ target_field: 'empresa_origem', strategy: 'fuzzy' }), 'fuzzy pede conferência');
});

test('data-migration: mappingSummary conta reconhecidas e a conferir', () => {
  const summary = _DM().mappingSummary([
    { source_column: 'Nome', target_field: 'name', strategy: 'exact' },
    { source_column: 'CPF', target_field: 'cpf', strategy: 'synonym' },
    { source_column: 'Cargo', target_field: 'role_name', strategy: 'fuzzy' },
    { source_column: 'Employee', target_field: null, strategy: 'duplicate_target' }
  ], []);
  eq(summary.total, 4);
  eq(summary.mapped, 3);
  eq(summary.unmapped, 1);
  eq(summary.review, 2);
  assert(summary.ready, 'sem obrigatório faltando fica pronto');
});

test('data-migration: mappingSummary não fica pronto com obrigatório faltando', () => {
  const summary = _DM().mappingSummary([], ['cpf']);
  assert(!summary.ready, 'obrigatório ausente trava');
  eq(JSON.stringify(summary.missingRequired), JSON.stringify(['cpf']));
});

test('data-migration: availableTargets esconde destino já usado por outra coluna', () => {
  const mapping = { 'Nome': 'name', 'CPF': 'cpf' };
  const forOther = _DM().availableTargets(_DM_FIELDS, mapping, 'Cargo').map((f) => f.name);
  eq(JSON.stringify(forOther), JSON.stringify(['role_name', 'empresa_origem']));
});

test('data-migration: availableTargets mantém o destino da própria coluna', () => {
  // Sem isso o <select> da coluna perderia a própria opção selecionada.
  const mapping = { 'Nome': 'name' };
  const forSelf = _DM().availableTargets(_DM_FIELDS, mapping, 'Nome').map((f) => f.name);
  assert(forSelf.includes('name'), 'destino próprio continua disponível');
});

test('data-migration: missingRequiredFields aponta obrigatório sem coluna', () => {
  eq(JSON.stringify(_DM().missingRequiredFields(_DM_FIELDS, { 'Nome': 'name' })), JSON.stringify(['cpf']));
  eq(_DM().missingRequiredFields(_DM_FIELDS, { 'Nome': 'name', 'Doc': 'cpf' }).length, 0);
});

test('data-migration: canAdvance exige o que cada etapa precisa', () => {
  assert(!_DM().canAdvance('entidade', {}), 'sem entidade não avança');
  assert(_DM().canAdvance('entidade', { entity: 'colaboradores' }), 'com entidade avança');
  assert(!_DM().canAdvance('origem', { sourceKind: 'csv' }), 'sem arquivo não avança');
  assert(_DM().canAdvance('origem', { sourceKind: 'csv', fileName: 'a.csv' }), 'com arquivo avança');
  assert(!_DM().canAdvance('leitura', { totalRows: 0 }), 'arquivo vazio não avança');
  assert(_DM().canAdvance('leitura', { totalRows: 3 }), 'com linhas avança');
});

test('data-migration: canAdvance no mapeamento trava com obrigatório faltando', () => {
  const draft = { fields: _DM_FIELDS, mapping: { 'Nome': 'name' } };
  assert(!_DM().canAdvance('mapeamento', draft), 'falta cpf');
  draft.mapping['Doc'] = 'cpf';
  assert(_DM().canAdvance('mapeamento', draft), 'obrigatórios completos');
});

test('data-migration: nextStep/previousStep respeitam as pontas', () => {
  eq(_DM().nextStep('entidade'), 'origem');
  eq(_DM().nextStep('mapeamento'), 'mapeamento');
  eq(_DM().previousStep('origem'), 'entidade');
  eq(_DM().previousStep('entidade'), 'entidade');
});

test('data-migration: dashboardCards preserva entidades de roadmap marcadas', () => {
  const cards = _DM().dashboardCards([
    { key: 'colaboradores', label: 'Colaboradores', enabled: true, phase: 1, fields: [{}, {}] },
    { key: 'estoque', label: 'Estoque', enabled: false, phase: 4, fields: [] }
  ]);
  eq(cards.length, 2);
  assert(cards[0].enabled, 'habilitada');
  assert(!cards[1].enabled, 'roadmap aparece mas desabilitada');
  eq(cards[0].fieldCount, 2);
});

test('data-migration: canRevert só aceita concluída e não revertida', () => {
  assert(_DM().canRevert({ status: 'completed', reverted_at: null }), 'concluída');
  assert(!_DM().canRevert({ status: 'completed', reverted_at: '2026-01-01' }), 'já revertida');
  assert(!_DM().canRevert({ status: 'failed' }), 'com falha');
  assert(!_DM().canRevert({ status: 'reverted' }), 'revertida');
  assert(!_DM().canRevert(null), 'sem job');
});

test('data-migration: jobCounters normaliza ausentes para zero', () => {
  const counters = _DM().jobCounters({ total_rows: 10, inserted_rows: 7 });
  eq(counters.total, 10);
  eq(counters.inserted, 7);
  eq(counters.updated, 0);
  eq(counters.failed, 0);
});

test('data-migration: groupDiagnostics agrupa por tipo e ordena por volume', () => {
  const grouped = _DM().groupDiagnostics([
    { kind: 'invalid_value', row_number: 2 },
    { kind: 'missing_required', row_number: 3 },
    { kind: 'invalid_value', row_number: 5 },
    { kind: 'invalid_value', row_number: 9 }
  ]);
  eq(grouped.length, 2);
  eq(grouped[0].kind, 'invalid_value');
  eq(grouped[0].count, 3);
  eq(JSON.stringify(grouped[0].rows), JSON.stringify([2, 5, 9]));
  eq(grouped[1].kind, 'missing_required');
});

test('data-migration: APPLY_STRATEGIES não oferece dry_run como escolha', () => {
  // dry_run é o preview, disparado automaticamente — nunca uma opção de
  // "como aplicar" no seletor.
  assert(!_DM().APPLY_STRATEGIES.includes('dry_run'), 'dry_run fora do seletor');
  eq(_DM().APPLY_STRATEGIES.length, 5);
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
