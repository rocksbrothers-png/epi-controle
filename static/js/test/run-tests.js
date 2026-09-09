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
  // #271-B4: o módulo da configuração por Unidade + EPI passa a ser CARREGADO
  // pelo harness. Ele existia desde a B3 sem nenhum teste que o executasse —
  // toda a garantia dele era estrutural (Python lendo o texto do arquivo).
  'views/estoque-config.js',
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
const asyncTests = [];
function testAsync(name, fn) { asyncTests.push({ name, fn }); }
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
  // `assert` em vez de `eq`: o `eq` embute o VALOR na mensagem de falha, e a
  // mensagem vai para o `console.error` do relatório. O CodeQL segue esse
  // caminho e o classifica como "clear-text logging of sensitive information"
  // por causa do nome do campo. O valor aqui é booleano e não revela nada,
  // mas o fluxo existe de verdade — e uma flag booleana não precisa ser
  // ecoada para a mensagem dizer o que falhou.
  assert(state.requirePasswordChange === true,
    'setPasswordChangeRequired(true) deveria marcar a flag no state');
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
test('dashboard: renderStats trava KPIs na própria unidade para Gestor de EPI (user)', () => {
  // Achado no dashboard real (screenshot): Gestor de EPI via "Todos" nos
  // filtros de CNPJ/Unidade e os KPIs somavam a empresa inteira (3
  // unidades), não só a unidade dele. isLockedProfile('user') === true deve
  // fechar o recorte na própria unidade mesmo sem a barra de filtro (aqui
  // document.getElementById sempre devolve null — ver mocks do topo do
  // arquivo), provando que a trava vive no cálculo dos KPIs, não só na UI.
  const grid = { innerHTML: '', dataset: {}, addEventListener() {} };
  globalThis.__EPI_REFS__ = { statsGrid: grid };
  globalThis.currentUserHasPermission = () => true;
  globalThis.filterByUserCompany = (items) => items;
  const units = [
    { id: 1, company_id: 1, legal_entity_id: 10 },
    { id: 2, company_id: 1, legal_entity_id: 10 },
    { id: 3, company_id: 1, legal_entity_id: 20 },
  ];
  globalThis.__EPI_APP_STATE__ = {
    user: { role: 'user', operational_unit_id: 2, company_id: 1 },
    companies: [{ id: 1 }],
    units,
    employees: [{ id: 1, unit_id: 1 }, { id: 2, unit_id: 2 }, { id: 3, unit_id: 2 }, { id: 4, unit_id: 3 }],
    deliveries: [{ id: 1, unit_id: 1, returned_date: '' }, { id: 2, unit_id: 2, returned_date: '' }, { id: 3, unit_id: 3, returned_date: '' }],
    epis: [], alerts: [], lowStock: [], feedbacks: [],
    stockCompliance: { summary: {} },
  };
  globalThis.__EPI_DASHBOARD__.renderStats();
  const html = grid.innerHTML;
  assert(/Colaboradores ativos<\/span><strong>2</.test(html), `esperado 2 colaboradores (só unidade 2); html: ${html}`);
  assert(/Entregas<\/span><strong>1</.test(html), 'esperada 1 entrega (só unidade 2)');
  assert(/Unidades<\/span><strong>1</.test(html), 'esperada 1 unidade (só a travada)');
});
test('dashboard: renderStats NÃO trava KPIs para general_admin (multi-CNPJ)', () => {
  // Administrador Geral administra múltiplos CNPJs e a hierarquia inteira
  // (docs/PAPEIS_E_ATRIBUICOES.md #2) — precisa continuar vendo a empresa
  // toda, nunca uma unidade só.
  const grid = { innerHTML: '', dataset: {}, addEventListener() {} };
  globalThis.__EPI_REFS__ = { statsGrid: grid };
  globalThis.currentUserHasPermission = () => true;
  globalThis.filterByUserCompany = (items) => items;
  const units = [
    { id: 1, company_id: 1, legal_entity_id: 10 },
    { id: 2, company_id: 1, legal_entity_id: 10 },
    { id: 3, company_id: 1, legal_entity_id: 20 },
  ];
  globalThis.__EPI_APP_STATE__ = {
    user: { role: 'general_admin', company_id: 1 },
    companies: [{ id: 1 }],
    units,
    employees: [{ id: 1, unit_id: 1 }, { id: 2, unit_id: 2 }, { id: 3, unit_id: 2 }, { id: 4, unit_id: 3 }],
    deliveries: [{ id: 1, unit_id: 1, returned_date: '' }, { id: 2, unit_id: 2, returned_date: '' }, { id: 3, unit_id: 3, returned_date: '' }],
    epis: [], alerts: [], lowStock: [], feedbacks: [],
    stockCompliance: { summary: {} },
  };
  globalThis.__EPI_DASHBOARD__.renderStats();
  const html = grid.innerHTML;
  assert(/Colaboradores ativos<\/span><strong>4</.test(html), 'general_admin deveria ver todos os colaboradores da empresa');
  assert(/Entregas<\/span><strong>3</.test(html), 'general_admin deveria ver todas as entregas da empresa');
  assert(/Unidades<\/span><strong>3</.test(html), 'general_admin deveria ver todas as unidades da empresa');
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
// ── 1.1D-C3: o Web Legado consome a classificação do backend ──────────────
//
// Antes desta fatia o Legado ignorava a classificação por Unidade inteira: uma
// varredura por `stock_status` em static/ devolvia ZERO. Exibia saldo e mínimo
// CORPORATIVOS como se fossem o número operacional da Unidade, e classificava
// "Estoque baixo" por uma terceira régua (`severity`) que não era a
// classificação de ninguém.

function _EST() { return globalThis.__EPI_ESTOQUE__; }

const _ITEM_UNIDADE = {
  name: 'Capacete', sector: 'Obras', epi_section: 'Cabeça', manufacturer: 'MSA',
  ca: '12345', unit_name: 'Unidade A', glove_size: 'N/A', size: 'G',
  uniform_size: 'N/A', size_balances: [], unit_measure: 'unidade',
  // corporativos — presentes no payload e que NÃO podem governar a tela
  stock: 300, company_stock_quantity: 300, minimum_stock: 100,
  // da Unidade
  unit_scope_id: 7, unit_stock_quantity: 4, unit_minimum_stock: 10,
  minimum_stock_source: 'unit_configured', attention_limit: 12,
  effective_attention_percentage: 20, stock_status: 'critical',
  underlying_status: 'critical', stock_condition: 'below_minimum'
};

test('estoque D-C3: saldo exibido é o da Unidade, não o corporativo', () => {
  const r = _EST().stockReading(_ITEM_UNIDADE);
  eq(r.value, 4);
  eq(r.fromUnit, true);
});
test('estoque D-C3: saldo ZERO na Unidade continua zero (sem fallback)', () => {
  // O defeito clássico: `saldo || corporativo` fazia zero virar o total da
  // empresa, porque zero é falsy. A escolha é por PRESENÇA de unit_scope_id.
  const r = _EST().stockReading({ ...(_ITEM_UNIDADE), unit_stock_quantity: 0 });
  eq(r.value, 0);
  eq(r.fromUnit, true);
});
test('estoque D-C3: sem Unidade resolvida o número é corporativo e se declara', () => {
  const r = _EST().stockReading({ ...(_ITEM_UNIDADE), unit_scope_id: null, unit_stock_quantity: null });
  eq(r.value, 300);
  eq(r.fromUnit, false);
});
test('estoque D-C3: mínimo exibido é o da Unidade, com a origem', () => {
  const m = _EST().minimumReading(_ITEM_UNIDADE);
  eq(m.value, 10);
  eq(m.source, 'unit_configured');
  eq(m.fromUnit, true);
});
test('estoque D-C3: mínimo herdado é rotulado company_default', () => {
  const m = _EST().minimumReading({ ...(_ITEM_UNIDADE), minimum_stock_source: 'company_default', unit_minimum_stock: 100 });
  eq(m.value, 100);
  eq(m.source, 'company_default');
});
test('estoque D-C3: mínimo ZERO na Unidade não cai para o corporativo', () => {
  const m = _EST().minimumReading({ ...(_ITEM_UNIDADE), unit_minimum_stock: 0 });
  eq(m.value, 0);
  eq(m.fromUnit, true);
});
test('estoque D-C3: os quatro estados têm chip próprio', () => {
  ['normal', 'near_minimum', 'critical', 'disabled'].forEach((s) => {
    const html = _EST().stockStatusBadge({ stock_status: s });
    assert(html.includes('badge-stock-' + s), 'faltou chip para ' + s);
  });
});
test('estoque D-C3: disabled nunca é renderizado como normal', () => {
  const desabilitado = _EST().stockStatusBadge({ stock_status: 'disabled' });
  const normal = _EST().stockStatusBadge({ stock_status: 'normal' });
  assert(desabilitado !== normal, 'disabled e normal ficaram idênticos');
  assert(!desabilitado.includes('badge-stock-normal'));
});
test('estoque D-C3: stock_status null NÃO vira normal', () => {
  // Ausência de classificação significa "não há Unidade resolvida". Pintar de
  // verde justamente o caso em que o sistema não sabe é o pior desfecho.
  eq(_EST().stockStatusBadge({ stock_status: null }), '');
  eq(_EST().stockStatusBadge({}), '');
  eq(_EST().stockStatusBadge({ stock_status: 'valor_novo_do_backend' }), '');
});
test('estoque D-C3: attention_limit vem do backend, não é recalculado', () => {
  const hint = _EST().attentionHint(_ITEM_UNIDADE);
  assert(hint.includes('12'), 'o limite do servidor precisa aparecer');
  // 10 × 1,20 = 12 aqui; mas o valor exibido tem que ser o do campo, não a
  // conta. Trocando só o campo, o texto acompanha.
  assert(_EST().attentionHint({ ...(_ITEM_UNIDADE), attention_limit: 99 }).includes('99'));
});
test('estoque D-C3: sem attention_limit não se inventa faixa', () => {
  eq(_EST().attentionHint({ ...(_ITEM_UNIDADE), attention_limit: null }), '');
});
test('estoque D-C3: a linha da tabela mostra Unidade e não corporativo', () => {
  const row = _EST().formatStockEpiRow(_ITEM_UNIDADE);
  assert(row.includes('>4 '), 'saldo da Unidade ausente');
  assert(!row.includes('>300 '), 'saldo corporativo vazou para a linha');
  assert(row.includes('badge-stock-critical'), 'chip de estado ausente');
});
test('estoque D-C3: a linha sem classificação não ganha chip verde', () => {
  const row = _EST().formatStockEpiRow({
    ...(_ITEM_UNIDADE), unit_scope_id: null, unit_stock_quantity: null,
    unit_minimum_stock: null, stock_status: null, attention_limit: null
  });
  assert(!row.includes('badge-stock-normal'));
  assert(!row.includes('badge-stock-'), 'nenhum chip deve ser desenhado');
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
test('outsourced-employees-view: lista de contratados é explícita, não "!= CLT"', () => {
  const V = _OEV();
  eq(V.CONTRACTED_VINCULOS.join(','), 'Terceirizado,Prestador de Serviço,Temporário');
  eq(V.isContractedVinculo('Terceirizado'), true);
  eq(V.isContractedVinculo('Temporário'), true);
  // O ponto do conserto: aprendiz/praticante/estagiário NÃO são contratados.
  // Com `!= 'CLT'` os três passavam.
  eq(V.isContractedVinculo('Menor Aprendiz'), false);
  eq(V.isContractedVinculo('Praticante'), false);
  eq(V.isContractedVinculo('Estagiário'), false);
  eq(V.isContractedVinculo('CLT'), false);
});
test('outsourced-employees-view: aprendiz com empresa vinculada não entra na lista', () => {
  const V = _OEV();
  // Combinação que o `!= 'CLT'` deixaria passar. Não deveria existir no banco
  // (o backend recusa), mas o filtro não pode depender disso.
  const filtered = V.outsourcedEmployeesOnly([
    { id: 9, tipo_vinculo: 'Menor Aprendiz', outsourced_company_id: 3 },
  ]);
  eq(filtered.length, 0);
});
test('outsourced-employees-view: Temporário é rotulado', () => {
  const V = _OEV();
  eq(V.tipoVinculoLabel('Temporário'), 'Temporário');
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

// ── Trava do filtro por perfil (Administrador Local / Gestor de EPI) ─────
test('dashboard-scope: isLockedProfile só trava admin e user', () => {
  assert(_S().isLockedProfile('admin'), 'admin deveria travar');
  assert(_S().isLockedProfile('user'), 'user (Gestor de EPI) deveria travar');
  assert(!_S().isLockedProfile('general_admin'), 'general_admin administra múltiplos CNPJs — não trava');
  assert(!_S().isLockedProfile('registry_admin'), 'registry_admin não trava');
  assert(!_S().isLockedProfile('master_admin'), 'master_admin não trava');
  assert(!_S().isLockedProfile(undefined), 'papel ausente não trava');
});
test('dashboard-scope: lockedLegalEntityId deriva o CNPJ da unidade do ator', () => {
  eq(_S().lockedLegalEntityId(_SC_UNITS, 2), 10);
  eq(_S().lockedLegalEntityId(_SC_UNITS, 3), 20);
});
test('dashboard-scope: lockedLegalEntityId é null sem unidade operacional ou sem vínculo', () => {
  eq(_S().lockedLegalEntityId(_SC_UNITS, null), null);
  eq(_S().lockedLegalEntityId(_SC_UNITS, 4), null); // unidade 4 é "Sem CNPJ"
  eq(_S().lockedLegalEntityId(_SC_UNITS, 999), null); // unidade inexistente
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

// ── #271-B4: configuração por Unidade + EPI no Web Legado ─────────────────
//
// Estes testes EXECUTAM `views/estoque-config.js`. Até a B4 o módulo era
// coberto só por asserções estruturais — Python lendo o texto do arquivo —, o
// que prova que uma linha existe mas não que ela se comporta. A distinção
// importa: `canWrite` podia estar escrito e devolver `true` para uma Unidade
// fora da lista sem nenhum gate perceber.

function _CFG() { return globalThis.__EPI_ESTOQUE_CONFIG__; }

function _escopo(over) {
  return _CFG().readSelectableUnits(Object.assign({
    units: [{ id: 5, name: 'Matriz' }, { id: 6, name: 'Filial' }],
    locked: false,
    unit_id: null,
    allows_all_units: false,
    blocks_everything: false
  }, over || {}));
}

test('config: origem é lida do servidor, nunca deduzida', () => {
  const S = _CFG().STOCK_CONFIG_SOURCES;
  eq(S.unit, 'unit_configured');
  eq(S.company, 'company_default');
  eq(S.system, 'system_default');
});

test('config: restaurar só é oferecido quando há decisão local', () => {
  // Herdado não tem o que apagar. O backend trata como no-op, mas oferecer um
  // botão que não faz nada é pior do que desabilitá-lo.
  assert(_CFG().canRestore('unit_configured'), 'unit_configured pode restaurar');
  assert(!_CFG().canRestore('company_default'), 'herdado não restaura');
  assert(!_CFG().canRestore('system_default'), 'system_default não restaura');
  assert(!_CFG().canRestore(''), 'origem vazia não restaura');
});

test('config: o mínimo lido é o da Unidade, não o corporativo', () => {
  const p = _CFG().readParameters({
    id: 11, unit_scope_id: 5,
    unit_minimum_stock: 7, minimum_stock: 999,
    minimum_stock_source: 'unit_configured',
    effective_attention_percentage: 30, attention_percentage_source: 'company_default',
    stock_alert_enabled: true, alert_source: 'system_default',
    attention_limit: 9, stock_status: 'normal', underlying_status: 'normal'
  });
  eq(p.minimum.value, 7);
  assert(p.minimum.value !== 999, 'não pode cair no mínimo corporativo');
  eq(p.minimum.source, 'unit_configured');
  eq(p.attention.source, 'company_default');
  // Derivados são EXIBIDOS como vieram, nunca recalculados.
  eq(p.attentionLimit, 9);
  eq(p.stockStatus, 'normal');
});

test('config: sem Unidade resolvida não há parâmetro para editar', () => {
  // Fail-closed na leitura: `unit_scope_id` ausente significa que o servidor
  // não resolveu Unidade, e um par sem Unidade não tem configuração.
  eq(_CFG().readParameters({ id: 11, unit_minimum_stock: 7 }), null);
  eq(_CFG().readParameters({ id: 11, unit_scope_id: null }), null);
  eq(_CFG().readParameters(null), null);
});

test('config: perfil travado não escolhe Unidade', () => {
  const escopo = _escopo({ locked: true, unit_id: 5 });
  eq(_CFG().initialUnitSelection(escopo), 5);
  // Mesmo pedindo outra, volta a do ator.
  eq(_CFG().acceptUnit(escopo, 6), 5);
});

test('config: "Todas" nunca vira seleção de escrita', () => {
  // Mesmo com o backend autorizando, escrita não consolida.
  const escopo = _escopo({ allows_all_units: true });
  eq(_CFG().initialUnitSelection(escopo), null);
  assert(!_CFG().canWrite(escopo, null), 'sem Unidade real não grava');
});

test('config: uma Unidade só é pré-selecionada', () => {
  const escopo = _escopo({ units: [{ id: 9, name: 'Única' }] });
  eq(_CFG().initialUnitSelection(escopo), 9);
});

test('config: escrita é fail-closed sem Unidade real', () => {
  const escopo = _escopo();
  assert(!_CFG().canWrite(escopo, null), 'null não grava');
  assert(!_CFG().canWrite(escopo, undefined), 'undefined não grava');
  assert(!_CFG().canWrite(escopo, 999), 'Unidade fora da lista não grava');
  assert(_CFG().canWrite(escopo, 5), 'Unidade ofertada grava');
});

test('config: carteira vazia bloqueia tudo', () => {
  // `blocks_everything` é "você não tem Unidade atribuída" — diferente de
  // "a empresa não tem Unidades", e nunca pode virar a empresa inteira.
  const escopo = _escopo({ units: [], blocks_everything: true });
  assert(!_CFG().canWrite(escopo, 5), 'carteira vazia não grava');
  eq(_CFG().initialUnitSelection(escopo), null);
});

test('config: deep link não vira autoridade', () => {
  const escopo = _escopo();
  eq(_CFG().acceptUnit(escopo, 6), 6);          // ofertada → vale
  eq(_CFG().acceptUnit(escopo, 999), null);     // não ofertada → descartada
  eq(_CFG().acceptUnit(escopo, 'abc'), null);   // lixo → descartado
  eq(_CFG().acceptUnit(escopo, null), null);
});

test('config: autorização é permissão, nunca papel', () => {
  const anterior = globalThis.__EPI_APP_STATE__;
  globalThis.__EPI_APP_STATE__ = { user: { role: 'general_admin', permissions: ['stock:adjust'] } };
  assert(_CFG().canConfigureStock(), 'general_admin com stock:adjust configura');
  globalThis.__EPI_APP_STATE__ = { user: { role: 'admin', permissions: ['stock:view'] } };
  assert(!_CFG().canConfigureStock(), 'admin sem stock:adjust não configura');
  globalThis.__EPI_APP_STATE__ = anterior;
});

test('config: mínimo recusa negativo e NÃO ganha teto', () => {
  assert(!_CFG().validateMinimum(-1).ok, 'negativo recusado');
  assert(!_CFG().validateMinimum(1.5).ok, 'fracionário recusado');
  eq(_CFG().validateMinimum(-1).error, 'negative');
  // O backend faz max(0, int(...)) e não publica teto — o cliente não inventa.
  assert(_CFG().validateMinimum(999999).ok, 'valor alto é aceito');
  eq(_CFG().validateMinimum(999999).value, 999999);
});

test('config: percentual usa o teto publicado 0-100', () => {
  assert(_CFG().validateAttention(0).ok);
  assert(_CFG().validateAttention(100).ok);
  assert(!_CFG().validateAttention(101).ok, '101 recusado');
  eq(_CFG().validateAttention(101).error, 'range');
});

test('config: toda gravação transporta a Unidade', () => {
  const C = _CFG();
  const pares = [
    C.minimumPayload(1, 5, 11, 7),
    C.attentionPayload(1, 5, 11, 30),
    C.alertPayload(1, 5, 11, false),
    C.restorePayload(1, 5, 11)
  ];
  pares.forEach((p) => {
    eq(p.unit_id, 5);
    eq(p.epi_id, 11);
    eq(p.actor_user_id, 1);
  });
});

test('config: alert_enabled falso não vira verdadeiro', () => {
  // O bug clássico: string não-vazia virando true numa conversão ingênua.
  eq(_CFG().alertPayload(1, 5, 11, false).alert_enabled, false);
  eq(_CFG().alertPayload(1, 5, 11, 'false').alert_enabled, false);
  eq(_CFG().alertPayload(1, 5, 11, true).alert_enabled, true);
});

test('config: salvar e restaurar são rotas distintas', () => {
  const R = _CFG().STOCK_CONFIG_ROUTES;
  assert(R.minimum !== R.minimumRestore, 'mínimo tem duas rotas');
  assert(R.attention !== R.attentionRestore, 'percentual tem duas rotas');
  assert(R.alert !== R.alertRestore, 'alerta tem duas rotas');
  eq(R.selectableUnits, '/api/units/selectable');
});

test('config: salvar e restaurar dizem coisas diferentes', () => {
  // Podem terminar com o MESMO valor e significam o oposto.
  const salvo = _CFG().outcomeMessage('minimum', 'saved');
  const restaurado = _CFG().outcomeMessage('minimum', 'restored');
  assert(salvo !== restaurado, 'mensagens distintas');
  assert(salvo && restaurado, 'nenhuma vazia');
});

test('config: desligar o alerta pede confirmação; ligar não', () => {
  assert(_CFG().alertNeedsConfirmation(true, false), 'silenciar pergunta');
  assert(!_CFG().alertNeedsConfirmation(false, true), 'religar não pergunta');
  assert(!_CFG().alertNeedsConfirmation(true, true), 'sem alteração não pergunta');
});

test('config: disabled nunca vira normal', () => {
  const desabilitado = _CFG().statusLabel('disabled');
  const normal = _CFG().statusLabel('normal');
  assert(desabilitado !== normal, 'disabled e normal são estados diferentes');
  // Chave desconhecida de um backend mais novo não pode virar "normal".
  assert(_CFG().statusLabel('quimera') !== normal, 'desconhecido não vira normal');
});


// ── #343 F4: o portal do colaborador não persiste os 3 dígitos do CPF ──────
//
// Estes testes são COMPORTAMENTAIS: executam `renderEmployeeCpfValidationScreen`
// de verdade, disparam o clique de submissão e observam o que o código tocou.
// O espião registra QUALQUER acesso a storage — leitura, escrita ou remoção —
// porque o contrato da F4 é ausência de estado, não "estado mais curto".
//
// O modelo de recarga é fiel de propósito: `recarregar()` troca os elementos do
// DOM (a página é reconstruída) mas MANTÉM o mesmo espião de storage — que é
// exatamente o que um reload real faz com `sessionStorage`. Se algo tivesse
// sobrevivido, sobreviveria aqui.

async function comPortalMockado(executar) {
  const documentoOriginal = globalThis.document;
  const sessionOriginal = globalThis.sessionStorage;
  const localOriginal = globalThis.localStorage;
  const acessos = [];

  const criarElemento = (id) => ({
    id, value: '', disabled: false, textContent: '', style: {}, _handlers: {},
    addEventListener(evento, fn) { this._handlers[evento] = fn; },
    click() { return this._handlers.click ? this._handlers.click() : undefined; },
  });
  let elementos = {};
  const montarDom = () => {
    elementos = {};
    ['employee-cpf-last3', 'employee-cpf-submit', 'employee-cpf-feedback']
      .forEach((id) => { elementos[id] = criarElemento(id); });
    globalThis.document = {
      body: { innerHTML: '' },
      getElementById(id) { return elementos[id] || null; },
      querySelector() { return null; },
      querySelectorAll() { return []; },
      createElement() { return criarElemento('novo'); },
    };
  };

  const espiao = (rotulo) => ({
    getItem(k) { acessos.push(`${rotulo}.getItem:${k}`); return null; },
    setItem(k, v) { acessos.push(`${rotulo}.setItem:${k}=${v}`); },
    removeItem(k) { acessos.push(`${rotulo}.removeItem:${k}`); },
    clear() { acessos.push(`${rotulo}.clear`); },
  });

  montarDom();
  globalThis.sessionStorage = espiao('session');
  globalThis.localStorage = espiao('local');
  try {
    return await executar({
      get elementos() { return elementos; },
      acessos,
      recarregar: montarDom,
    });
  } finally {
    globalThis.document = documentoOriginal;
    globalThis.sessionStorage = sessionOriginal;
    globalThis.localStorage = localOriginal;
  }
}

function apiFalsaDoPortal() {
  return {
    employee: { employee_name: 'Maria', employee_id_code: 'E101', sector: 'Ops' },
    deliveries: [], fichas: [], requests: [], feedbacks: [], available_epis: [],
  };
}

testAsync('#343 F4: a tela de validação não consulta storage e o campo nasce vazio', async () => {
  await comPortalMockado(async ({ elementos, acessos }) => {
    globalThis.renderEmployeeCpfValidationScreen('token-A-1789000000', '', false);
    eq(elementos['employee-cpf-last3'].value, '',
      'o campo de CPF veio pré-preenchido — era assim que o segundo fator vazava');
    eq(acessos.length, 0, `a tela tocou em storage: ${acessos.join(', ')}`);
  });
});

testAsync('#343 F4: validar o CPF não grava os 3 dígitos em lugar nenhum', async () => {
  await comPortalMockado(async ({ elementos, acessos }) => {
    let chamouApi = false;
    const apiOriginal = globalThis.api;
    globalThis.api = async () => { chamouApi = true; return apiFalsaDoPortal(); };
    try {
      globalThis.renderEmployeeCpfValidationScreen('token-A-1789000000', '', false);
      elementos['employee-cpf-last3'].value = '123';
      await elementos['employee-cpf-submit'].click();
      assert(chamouApi,
        'o fluxo não chegou a submeter: o teste passaria por não ter rodado, não por estar correto');
      eq(acessos.length, 0, `o portal tocou em storage ao validar: ${acessos.join(', ')}`);
      assert(!acessos.join(',').includes('123'), 'os 3 dígitos do CPF foram para storage');
    } finally { globalThis.api = apiOriginal; }
  });
});

testAsync('#343 F4: após recarregar, o portal exige os 3 dígitos de novo', async () => {
  await comPortalMockado(async (ctx) => {
    const apiOriginal = globalThis.api;
    globalThis.api = async () => apiFalsaDoPortal();
    try {
      // Ciclo 1 — o colaborador A valida com sucesso.
      globalThis.renderEmployeeCpfValidationScreen('token-A-1789000000', '', false);
      ctx.elementos['employee-cpf-last3'].value = '123';
      await ctx.elementos['employee-cpf-submit'].click();

      // Recarga: DOM novo, MESMO storage — como num reload de verdade.
      ctx.recarregar();
      const antes = ctx.acessos.length;
      globalThis.renderEmployeeCpfValidationScreen('token-A-1789000000', '', false);

      eq(ctx.elementos['employee-cpf-last3'].value, '',
        'o campo veio preenchido depois da recarga: o desafio foi pulado');
      eq(ctx.acessos.length - antes, 0,
        'a recarga consultou storage procurando um CPF salvo');
    } finally { globalThis.api = apiOriginal; }
  });
});

testAsync('#343 F4: novo ciclo na mesma aba não herda o acesso de quem validou antes', async () => {
  await comPortalMockado(async (ctx) => {
    const apiOriginal = globalThis.api;
    let chamadas = 0;
    globalThis.api = async () => { chamadas += 1; return apiFalsaDoPortal(); };
    try {
      // A valida e entra.
      globalThis.renderEmployeeCpfValidationScreen('token-A-1789000000', '', false);
      ctx.elementos['employee-cpf-last3'].value = '123';
      await ctx.elementos['employee-cpf-submit'].click();
      eq(chamadas, 1, 'premissa: o primeiro acesso precisa mesmo ter ocorrido');

      // Novo ciclo na MESMA aba, com o MESMO link de A — o cenário do achado.
      ctx.recarregar();
      globalThis.renderEmployeeCpfValidationScreen('token-A-1789000000', '', false);

      // Sem digitar nada, o acesso não acontece: nenhuma chamada nova à API.
      eq(chamadas, 1,
        'o portal abriu sem nova entrada dos 3 dígitos — a posse do link valeu sozinha');
      eq(ctx.elementos['employee-cpf-last3'].value, '',
        'o campo trouxe os dígitos de quem validou antes');

      // E com entrada errada, quem decide continua sendo o servidor.
      globalThis.api = async () => { throw new Error('CPF inválido. Tentativas restantes: 2.'); };
      ctx.elementos['employee-cpf-last3'].value = '999';
      await ctx.elementos['employee-cpf-submit'].click();
      assert(String(ctx.elementos['employee-cpf-feedback'].textContent).includes('Tentativas restantes'),
        'a recusa do servidor precisa chegar ao usuário');
      eq(ctx.acessos.length, 0, `storage foi tocado em algum ponto do ciclo: ${ctx.acessos.join(', ')}`);
    } finally { globalThis.api = apiOriginal; }
  });
});


// ── #343 F5-B: navegação sempre começa no estado padrão ────────────────────
//
// Estes gates NÃO leem o texto do arquivo: eles carregam os mesmos 48 scripts
// que `static/views/_scripts.html` serve ao navegador, num contexto `vm`
// isolado, e exercitam o mecanismo REAL de abas e de troca de módulo. O que
// existe abaixo de mock é plataforma (nós de DOM, eventos), nunca lógica de
// navegação — se alguém reintroduzir a persistência no código servido, o
// comportamento medido aqui muda e o gate cai.
//
// Contexto isolado de propósito: `static/app.js` define milhares de símbolos e
// não pode contaminar os testes dos módulos de `static/js`.

const vmF5B = require('vm');

function camelF5B(s) { return s.replace(/-([a-z])/g, (_, c) => c.toUpperCase()); }

function casaF5B(no, sel) {
  return String(sel).split(',').map((s) => s.trim()).filter(Boolean).some((parte) => {
    let resto = parte;
    if (resto.startsWith(':scope > ')) {return false;}
    const mTag = resto.match(/^([a-zA-Z]+)/);
    if (mTag) {
      if (no.tagName !== mTag[1].toUpperCase()) {return false;}
      resto = resto.slice(mTag[1].length);
    }
    for (const cls of resto.match(/\.[A-Za-z0-9_-]+/g) || []) {
      if (!no._classes.has(cls.slice(1))) {return false;}
      resto = resto.replace(cls, '');
    }
    const mNot = resto.match(/:not\(\[([a-z-]+)\]\)/);
    if (mNot) {
      if (no.dataset[camelF5B(mNot[1].replace(/^data-/, ''))] !== undefined) {return false;}
      resto = resto.replace(mNot[0], '');
    }
    const mId = resto.match(/^#([A-Za-z0-9_-]+)/);
    if (mId) {
      if (no.id !== mId[1]) {return false;}
      resto = resto.replace(mId[0], '');
    }
    for (const attr of resto.match(/\[[^\]]+\]/g) || []) {
      const corpo = attr.slice(1, -1);
      const eq = corpo.indexOf('=');
      if (eq === -1) {
        if (no.dataset[camelF5B(corpo.replace(/^data-/, ''))] === undefined) {return false;}
      } else {
        const nome = corpo.slice(0, eq);
        const valor = corpo.slice(eq + 1).replace(/^["']|["']$/g, '');
        if (String(no.dataset[camelF5B(nome.replace(/^data-/, ''))]) !== valor) {return false;}
      }
    }
    return true;
  });
}

function descendentesF5B(no) {
  const saida = [];
  (function anda(n) { n.children.forEach((f) => { saida.push(f); anda(f); }); })(no);
  return saida;
}

function criarNoF5B(tag, attrs = {}) {
  const no = {
    tagName: String(tag).toUpperCase(),
    dataset: {}, style: {}, _attrs: {}, _classes: new Set(), _handlers: {},
    children: [], parent: null, hidden: false, tabIndex: 0,
    id: attrs.id || '', value: '', disabled: false, textContent: '',
    classList: {
      add: (c) => no._classes.add(c),
      remove: (c) => no._classes.delete(c),
      contains: (c) => no._classes.has(c),
      toggle: (c, v) => {
        const ligar = v === undefined ? !no._classes.has(c) : Boolean(v);
        if (ligar) {no._classes.add(c);} else {no._classes.delete(c);}
        return ligar;
      }
    },
    setAttribute(k, v) { no._attrs[k] = String(v); },
    getAttribute(k) { return Object.prototype.hasOwnProperty.call(no._attrs, k) ? no._attrs[k] : null; },
    hasAttribute(k) { return Object.prototype.hasOwnProperty.call(no._attrs, k); },
    removeAttribute(k) { delete no._attrs[k]; },
    appendChild(filho) { filho.parent = no; no.children.push(filho); return filho; },
    insertBefore(filho, refNo) {
      filho.parent = no;
      const i = refNo ? no.children.indexOf(refNo) : -1;
      if (i === -1) {no.children.push(filho);} else {no.children.splice(i, 0, filho);}
      return filho;
    },
    insertAdjacentElement(posicao, filho) {
      const pai = no.parent;
      if (!pai) {return null;}
      const i = pai.children.indexOf(no);
      filho.parent = pai;
      pai.children.splice(posicao === 'beforebegin' ? i : i + 1, 0, filho);
      return filho;
    },
    get firstChild() { return no.children[0] || null; },
    focus() { no._focado = true; },
    scrollIntoView() {},
    addEventListener(ev, fn) { (no._handlers[ev] = no._handlers[ev] || []).push(fn); },
    removeEventListener() {},
    // Como no navegador: exceção num listener não impede os demais nem sobe
    // para quem disparou. Sem isto um listener alheio derrubaria o disparo e o
    // teste estaria medindo o mock, não o comportamento servido.
    // Propaga pela árvore como o navegador: quem escuta no container ouve o
    // evento disparado no campo. Sem isto, um gate que digita num input não
    // alcançaria o handler real — e passaria verde sem exercitar nada.
    // Exceção em listener fica isolada, também como no navegador.
    dispatchEvent(ev) {
      if (!ev.target) {ev.target = no;}
      let atual = no;
      while (atual) {
        ev.currentTarget = atual;
        (atual._handlers[ev.type] || []).forEach((fn) => {
          try { fn(ev); } catch (erro) { (no._errosDeListener = no._errosDeListener || []).push(erro); }
        });
        if (ev.bubbles === false) {break;}
        atual = atual.parent;
      }
      return true;
    },
    matches(sel) { return casaF5B(no, sel); },
    closest(sel) { let n = no; while (n) { if (casaF5B(n, sel)) {return n;} n = n.parent; } return null; },
    querySelectorAll(sel) {
      const texto = String(sel).trim();
      if (texto.startsWith(':scope > ')) {
        const resto = texto.slice(':scope > '.length);
        return no.children.filter((n) => casaF5B(n, resto));
      }
      return descendentesF5B(no).filter((n) => casaF5B(n, sel));
    },
    querySelector(sel) { return no.querySelectorAll(sel)[0] || null; }
  };
  Object.entries(attrs).forEach(([k, v]) => {
    if (k === 'id') {no.id = v;} else if (k.startsWith('data-')) {no.dataset[camelF5B(k.slice(5))] = v;} else if (k === 'class') {String(v).split(/\s+/).filter(Boolean).forEach((c) => no._classes.add(c));}
  });
  return no;
}

function montarVistaF5B(nome, grupo, abas) {
  const vista = criarNoF5B('div', { id: `${nome}-view`, class: 'view' });
  const nav = criarNoF5B('nav', { 'data-vtabs': grupo, class: 'view-tabs' });
  vista.appendChild(nav);
  abas.forEach((chave) => {
    nav.appendChild(criarNoF5B('button', { 'data-vtab': chave, class: 'vtab' }));
    const painel = criarNoF5B('div', { 'data-vtab-panel': chave, class: 'vtab-panel' });
    painel.appendChild(criarNoF5B('div', {}));
    vista.appendChild(painel);
  });
  return vista;
}

// Carrega os mesmos scripts que a página serve, na mesma ordem.
function montarAppServidoF5B(busca) {
  const raizStatic = path.resolve(JS_ROOT, '..');
  const vistas = {
    estoque: montarVistaF5B('estoque', 'estoque', ['estoque', 'movimentacoes', 'validade', 'alertas']),
    colaboradores: montarVistaF5B('colaboradores', 'colaboradores', ['cadastro', 'lista', 'arquivados']),
    dashboard: montarVistaF5B('dashboard', 'dashboard-grp', ['inicio', 'outra'])
  };
  const main = criarNoF5B('div', { id: 'main-content' });
  Object.values(vistas).forEach((v) => main.appendChild(v));
  const doc = criarNoF5B('document', {});
  doc.appendChild(main);
  doc.body = criarNoF5B('body', {});
  doc.head = criarNoF5B('head', {});
  doc.documentElement = criarNoF5B('html', {});
  doc.readyState = 'complete';
  doc.title = '';
  doc.getElementById = (id) => descendentesF5B(doc).find((n) => n.id === id) || null;
  doc.createElement = (t) => criarNoF5B(t, {});

  const sessao = {
    _s: {},
    getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
    setItem(k, v) { this._s[k] = String(v); },
    removeItem(k) { delete this._s[k]; }
  };
  const local = {
    _s: {},
    getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
    setItem(k, v) { this._s[k] = String(v); },
    removeItem(k) { delete this._s[k]; },
    key(i) { return Object.keys(this._s)[i] ?? null; },
    get length() { return Object.keys(this._s).length; }
  };

  const ctx = {
    document: doc, localStorage: local, sessionStorage: sessao,
    location: { search: busca || '', href: `http://local/${busca || ''}`, pathname: '/', assign() {}, reload() {} },
    history: { pushState() {}, replaceState() {} },
    navigator: { userAgent: 'node' }, console,
    CustomEvent: class { constructor(t, o) { this.type = t; Object.assign(this, o || {}); } },
    AbortController: class { constructor() { this.signal = { addEventListener() {} }; } abort() {} },
    MutationObserver: class { observe() {} disconnect() {} },
    setTimeout, clearTimeout, setInterval, clearInterval, Promise, URL, URLSearchParams,
    requestAnimationFrame: (fn) => setTimeout(fn, 0),
    fetch: () => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }),
    alert() {}, scrollTo() {}, matchMedia: () => ({ matches: false, addEventListener() {} })
  };
  ctx._handlers = {};
  ctx.addEventListener = (ev, fn) => { (ctx._handlers[ev] = ctx._handlers[ev] || []).push(fn); };
  ctx.removeEventListener = () => {};
  ctx.dispatchEvent = (ev) => {
    (ctx._handlers[ev.type] || []).forEach((fn) => { try { fn(ev); } catch (_erro) { /* isolado, como no navegador */ } });
    return true;
  };
  ctx.window = ctx; ctx.globalThis = ctx; ctx.self = ctx;
  vmF5B.createContext(ctx);

  const ordem = fs.readFileSync(path.join(raizStatic, 'views', '_scripts.html'), 'utf-8')
    .match(/src="\/([^"?]+\.js)/g).map((m) => m.slice(6));
  ordem.forEach((rel) => {
    try {
      vmF5B.runInContext(fs.readFileSync(path.join(raizStatic, rel), 'utf-8'), ctx, { filename: rel });
    } catch (_erro) { /* dependência de browser ausente não invalida o gate */ }
  });

  const abaAtiva = (grupo) => {
    const nav = doc.querySelector(`nav[data-vtabs="${grupo}"]`);
    const ativa = nav.querySelectorAll('[data-vtab]').find((t) => t.classList.contains('is-active'));
    return ativa ? ativa.dataset.vtab : '';
  };
  // Emite o MESMO formato que `showView` emite, incluindo `anterior` e
  // `viaHistorico` — sem isso os gates estariam exercitando uma forma de
  // evento que a aplicação nunca produz.
  let _vistaAtual = '';
  const entrarNoModulo = (nome, opcoes) => {
    const anterior = _vistaAtual;
    _vistaAtual = nome;
    return doc.dispatchEvent(new ctx.CustomEvent('epi:viewchange', {
      detail: { view: nome, anterior, viaHistorico: (opcoes || {}).viaHistorico === true }
    }));
  };
  const redesenharMesmaVista = (nome) => doc.dispatchEvent(new ctx.CustomEvent('epi:viewchange', {
    detail: { view: nome, anterior: nome, viaHistorico: false }
  }));

  return { ctx, doc, vistas, sessao, local, abaAtiva, entrarNoModulo, redesenharMesmaVista, scriptsCarregados: ordem.length };
}

let _appF5B = null;
function appServidoF5B() {
  if (!_appF5B) {
    _appF5B = montarAppServidoF5B();
    _appF5B.ctx.setupViewTabs();
  }
  return _appF5B;
}

test('#343 F5-B G0: o gate roda sobre os scripts realmente servidos', () => {
  const app = appServidoF5B();
  assert(app.scriptsCarregados >= 40, `esperava a lista de _scripts.html, veio ${app.scriptsCarregados}`);
  assert(typeof app.ctx.setupViewTabs === 'function', 'setupViewTabs não veio do app.js servido');
  assert(typeof app.ctx.resetViewTabsToInitial === 'function', 'resetViewTabsToInitial não existe no app.js servido');
});

test('#343 F5-B G1: sair do módulo e voltar abre a subtela inicial', () => {
  const app = appServidoF5B();
  eq(app.abaAtiva('estoque'), 'estoque', 'o módulo deveria abrir na primeira aba');
  app.ctx.activateViewTab(app.doc.querySelector('nav[data-vtabs="estoque"]'), 'movimentacoes');
  eq(app.abaAtiva('estoque'), 'movimentacoes', 'o clique do usuário deveria abrir a subtela');
  app.entrarNoModulo('dashboard');
  app.entrarNoModulo('estoque');
  eq(app.abaAtiva('estoque'), 'estoque', 'reentrar no módulo deveria voltar à aba inicial');
});

test('#343 F5-B G4: a aba interna não sobrevive à troca de módulo em nenhum grupo', () => {
  const app = appServidoF5B();
  app.ctx.activateViewTab(app.doc.querySelector('nav[data-vtabs="colaboradores"]'), 'arquivados');
  eq(app.abaAtiva('colaboradores'), 'arquivados');
  app.entrarNoModulo('estoque');
  app.entrarNoModulo('colaboradores');
  eq(app.abaAtiva('colaboradores'), 'cadastro', 'colaboradores deveria reabrir em "cadastro"');
});

test('#343 F5-B G6/G10: navegar não grava estado de navegação em storage nenhum', () => {
  const app = appServidoF5B();
  app.ctx.activateViewTab(app.doc.querySelector('nav[data-vtabs="estoque"]'), 'validade');
  app.entrarNoModulo('colaboradores');
  app.entrarNoModulo('estoque');
  const proibidas = /^(epi_vtab_|epi:ux:phase4[1234]|epi\.ux\.phase44)/;
  const gravadas = [...Object.keys(app.sessao._s), ...Object.keys(app.local._s)].filter((k) => proibidas.test(k));
  eq(gravadas.length, 0, `chaves de navegação gravadas: ${gravadas.join(', ')}`);
});


test('#343 F5-B G7: deep link explícito continua abrindo o destino pedido', () => {
  const app = appServidoF5B();
  assert(typeof app.ctx.resolveViewFromLocation === 'function', 'resolveViewFromLocation sumiu do app servido');
  const original = app.ctx.location.search;
  try {
    app.ctx.location.search = '?view=estoque';
    eq(app.ctx.resolveViewFromLocation(), 'estoque', 'o destino explícito da URL deveria ser respeitado');
    app.ctx.location.search = '?view=colaboradores';
    eq(app.ctx.resolveViewFromLocation(), 'colaboradores');
  } finally { app.ctx.location.search = original; }
});

test('#343 F5-B G9: snapshot com `sid` de outra sessão é recusado', () => {
  // Precisa da flag `ux_interactive_app` LIGADA: com ela desligada
  // `restoreInteractiveSnapshot` sai na primeira linha e a checagem de `sid`
  // nunca é alcançada — um gate com a flag no default mediria o nada e ficaria
  // verde mesmo com a proteção removida.
  const app = montarAppServidoF5B('?ux_interactive_app=1');
  app.ctx.setupViewTabs();
  const meu = app.ctx.collectInteractiveSnapshot('estoque');
  assert(typeof meu.sid === 'string' && meu.sid.length > 0, 'o snapshot precisa de carimbo `sid`');
  assert(meu.filters && meu.filters.employees, 'com a flag ligada o snapshot deveria carregar filtros');

  const antes = JSON.stringify(app.ctx.collectInteractiveSnapshot('estoque').filters);
  let lancou = null;
  try {
    app.ctx.restoreInteractiveSnapshot({
      view: 'estoque', sid: 'sid-de-outra-sessao', scrollY: 999,
      filters: { employees: { search: 'INVASOR' }, epis: { search: 'INVASOR' } }
    });
  } catch (erro) { lancou = erro; }
  const depois = JSON.stringify(app.ctx.collectInteractiveSnapshot('estoque').filters);
  eq(depois, antes, 'filtros de um snapshot com `sid` alheio entraram no estado atual');
  eq(lancou, null, `a recusa por sid deveria sair limpa, e lançou: ${lancou && lancou.message}`);
});

test('#343 F5-B G8: o popstate reaplica o snapshot DEPOIS da entrada no módulo', () => {
  // Ordem importa: se `restoreInteractiveSnapshot` rodasse antes do `showView`,
  // o reset de entrada apagaria o que o usuário pediu de volta no Voltar.
  const fonte = fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), 'app.js'), 'utf-8');
  const trecho = fonte.slice(fonte.indexOf("safeOn(globalThis, 'popstate'"));
  const posShow = trecho.indexOf('showView(nextView');
  const posRestore = trecho.indexOf('restoreInteractiveSnapshot(event?.state)');
  assert(posShow > -1 && posRestore > -1, 'o handler de popstate mudou de forma');
  assert(posShow < posRestore, 'o snapshot voltou a ser aplicado antes do showView');
});

test('#343 F5-B G5: sessão nova não herda navegação nenhuma da anterior', () => {
  const anterior = appServidoF5B();
  anterior.ctx.activateViewTab(anterior.doc.querySelector('nav[data-vtabs="estoque"]'), 'alertas');
  eq(anterior.abaAtiva('estoque'), 'alertas');
  // Encerrar a sessão e outra pessoa entrar = documento novo. Como nada foi
  // persistido, não existe caminho por onde a navegação de A chegue a B.
  const nova = montarAppServidoF5B();
  nova.ctx.setupViewTabs();
  eq(nova.abaAtiva('estoque'), 'estoque', 'a sessão seguinte deveria abrir na aba inicial');
  eq(Object.keys(anterior.sessao._s).filter((k) => k.startsWith('epi_vtab_')).length, 0,
    'a sessão anterior deixou aba gravada em sessionStorage');
});

// ── phase44: filtros ───────────────────────────────────────────────────────
// Carrega o ux-phase44.js SERVIDO, com a flag ligada, monta o container de
// filtros que ele procura e digita nele. O que se mede é o efeito: se voltar a
// existir gravação, a chave aparece no localStorage e o gate cai.
function comPhase44LigadoF5B(chavesPreexistentes) {
  const raizStatic = path.resolve(JS_ROOT, '..');
  const local = {
    _s: Object.assign({}, chavesPreexistentes || {}),
    getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
    setItem(k, v) { this._s[k] = String(v); },
    removeItem(k) { delete this._s[k]; },
    key(i) { return Object.keys(this._s)[i] ?? null; },
    get length() { return Object.keys(this._s).length; }
  };
  const vista = criarNoF5B('div', { id: 'colaboradores-view', class: 'view active' });
  // Header já presente: é o estado da página depois do primeiro bind, e faz
  // `applyViewHeader` sair cedo. Sem isto ele monta markup via `innerHTML`,
  // que este shim não interpreta, e o `bindFilterPattern` — o que interessa
  // medir — nunca seria alcançado.
  vista.appendChild(criarNoF5B('article', { class: 'card phase44-header' }));
  const filtros = criarNoF5B('div', { 'data-colab-list-filters': '1' });
  const campo = criarNoF5B('input', { id: 'employees-filter-search' });
  filtros.appendChild(campo);
  vista.appendChild(filtros);
  const doc = criarNoF5B('document', {});
  doc.appendChild(vista);
  doc.body = criarNoF5B('body', {});
  doc.head = criarNoF5B('head', {});
  doc.readyState = 'complete';
  doc.getElementById = (id) => descendentesF5B(doc).find((n) => n.id === id) || null;
  doc.createElement = (t) => criarNoF5B(t, {});

  const ctx = {
    document: doc, localStorage: local,
    sessionStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    location: { search: '?ux_phase44=1', href: 'http://local/?ux_phase44=1' }, console,
    CustomEvent: class { constructor(t, o) { this.type = t; Object.assign(this, o || {}); } },
    AbortController: class { constructor() { this.signal = { addEventListener() {} }; } abort() {} },
    MutationObserver: class { observe() {} disconnect() {} },
    setTimeout, clearTimeout, URL, URLSearchParams, Promise
  };
  ctx.window = ctx; ctx.globalThis = ctx; ctx.self = ctx;
  ctx.addEventListener = () => {}; ctx.dispatchEvent = () => true;
  vmF5B.createContext(ctx);
  vmF5B.runInContext(fs.readFileSync(path.join(raizStatic, 'ux-phase44.js'), 'utf-8'), ctx, { filename: 'ux-phase44.js' });
  return { ctx, local, doc, campo, filtros };
}

testAsync('#343 F5-B G2: digitar um filtro não grava nada, e a chave legada é apagada', async () => {
  const legada = { 'epi.ux.phase44.filters.colaboradores': '{"employees-filter-search":"Maria"}' };
  const { ctx, local, campo } = comPhase44LigadoF5B(legada);
  assert(ctx.document.body.classList.contains('phase44-enabled'),
    'o phase44 não chegou a iniciar — o gate estaria medindo o nada');
  eq(local.getItem('epi.ux.phase44.filters.colaboradores'), null,
    'a chave legada de navegação deveria ter sido apagada no init');

  campo.value = 'Joana';
  campo.dispatchEvent(new ctx.CustomEvent('input', { bubbles: true }));
  campo.dispatchEvent(new ctx.CustomEvent('change', { bubbles: true }));
  await new Promise((r) => setTimeout(r, 260));   // maior que o debounce de 180ms

  const gravadas = Object.keys(local._s).filter((k) => k.indexOf('epi.ux.phase44') === 0);
  eq(gravadas.length, 0, `o filtro foi persistido: ${gravadas.join(', ')}`);
});


// ── phase41: rolagem (F5-B) e rascunho de formulário (fronteira com a F5-C) ──
function comPhase41LigadoF5B() {
  const raizStatic = path.resolve(JS_ROOT, '..');
  const local = {
    _s: {},
    getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
    setItem(k, v) { this._s[k] = String(v); },
    removeItem(k) { delete this._s[k]; },
    key(i) { return Object.keys(this._s)[i] ?? null; },
    get length() { return Object.keys(this._s).length; }
  };
  const vista = criarNoF5B('div', { id: 'colaboradores-view', class: 'view active' });
  const form = criarNoF5B('form', { id: 'employee-form' });
  const campo = criarNoF5B('input', { id: 'employee-name' });
  campo.type = 'text';
  form.appendChild(campo);
  vista.appendChild(form);
  const main = criarNoF5B('div', { id: 'main-content' });
  main.appendChild(vista);
  const doc = criarNoF5B('document', {});
  doc.appendChild(main);
  doc.body = criarNoF5B('body', {});
  doc.head = criarNoF5B('head', {});
  doc.readyState = 'complete';
  doc.getElementById = (id) => descendentesF5B(doc).find((n) => n.id === id) || null;
  doc.createElement = (t) => criarNoF5B(t, {});

  const ctx = {
    document: doc, localStorage: local,
    sessionStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    location: { search: '?ux_phase41=1', href: 'http://local/?ux_phase41=1' }, console,
    CustomEvent: class { constructor(t, o) { this.type = t; Object.assign(this, o || {}); } },
    AbortController: class { constructor() { this.signal = { addEventListener() {} }; } abort() {} },
    MutationObserver: class { observe() {} disconnect() {} },
    setTimeout, clearTimeout, URL, URLSearchParams, Promise,
    scrollY: 480, scrollTo() {}
  };
  ctx.window = ctx; ctx.globalThis = ctx; ctx.self = ctx;
  ctx._handlers = {};
  ctx.addEventListener = (ev, fn) => { (ctx._handlers[ev] = ctx._handlers[ev] || []).push(fn); };
  ctx.removeEventListener = () => {};
  ctx.dispatchEvent = (ev) => {
    (ctx._handlers[ev.type] || []).forEach((fn) => { try { fn(ev); } catch (_e) { /* isolado */ } });
    return true;
  };
  vmF5B.createContext(ctx);
  vmF5B.runInContext(fs.readFileSync(path.join(raizStatic, 'ux-phase41.js'), 'utf-8'), ctx, { filename: 'ux-phase41.js' });
  return { ctx, local, doc, campo };
}

testAsync('#343 F5-B G6: a rolagem não é mais persistida em lugar nenhum', async () => {
  const { ctx, local, campo } = comPhase41LigadoF5B();
  assert(ctx.document.body.classList.contains('phase41-enabled'),
    'o phase41 não iniciou — o gate estaria medindo o nada');
  campo.value = 'Ana';
  campo.dispatchEvent(new ctx.CustomEvent('input', { bubbles: true }));
  ctx.scrollY = 900;
  ctx.dispatchEvent(new ctx.CustomEvent('beforeunload', {}));
  await new Promise((r) => setTimeout(r, 300));
  eq(local.getItem('epi:ux:phase41:scroll:v2'), null,
    'a rolagem voltou a ser gravada — reentrar no módulo restauraria a posição anterior');
});

testAsync('#343 F5-B: o rascunho de formulário NÃO foi tocado — ele é da F5-C', async () => {
  // Gate de fronteira. A F5-B remove estado de NAVEGAÇÃO; o rascunho de
  // formulário (`epi:ux:phase41:context:v2`) é categoria 3 e sai na F5-C, com
  // contrato próprio. Se alguém antecipar essa remoção aqui, este gate cai e a
  // decisão volta a ser explícita em vez de virar efeito colateral.
  const { ctx, local, campo } = comPhase41LigadoF5B();
  campo.value = 'Ana';
  campo.dispatchEvent(new ctx.CustomEvent('input', { bubbles: true }));
  ctx.dispatchEvent(new ctx.CustomEvent('beforeunload', {}));
  await new Promise((r) => setTimeout(r, 300));
  assert(local.getItem('epi:ux:phase41:context:v2') !== null,
    'o rascunho parou de ser persistido: isso é escopo da F5-C, não da F5-B');
});


// ── phase42: contexto/último registro ──────────────────────────────────────
testAsync('#343 F5-B G3: o último colaborador/EPI usado não é guardado em storage', async () => {
  const raizStatic = path.resolve(JS_ROOT, '..');
  const local = {
    _s: {},
    getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
    setItem(k, v) { this._s[k] = String(v); },
    removeItem(k) { delete this._s[k]; },
    key(i) { return Object.keys(this._s)[i] ?? null; },
    get length() { return Object.keys(this._s).length; }
  };
  const vista = criarNoF5B('div', { id: 'entregas-view', class: 'view active' });
  const form = criarNoF5B('form', { id: 'delivery-form' });
  const campos = {};
  ['delivery-company', 'delivery-unit-filter', 'delivery-employee', 'delivery-epi'].forEach((id) => {
    const c = criarNoF5B('select', { id });
    c.options = [];
    campos[id] = c;
    form.appendChild(c);
  });
  vista.appendChild(form);
  const doc = criarNoF5B('document', {});
  doc.appendChild(vista);
  doc.body = criarNoF5B('body', {});
  doc.head = criarNoF5B('head', {});
  doc.readyState = 'complete';
  doc.getElementById = (id) => descendentesF5B(doc).find((n) => n.id === id) || null;
  doc.createElement = (t) => criarNoF5B(t, {});

  const ctx = {
    document: doc, localStorage: local,
    sessionStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    location: { search: '?ux_phase42=1', href: 'http://local/?ux_phase42=1' }, console,
    CustomEvent: class { constructor(t, o) { this.type = t; Object.assign(this, o || {}); } },
    AbortController: class { constructor() { this.signal = { addEventListener() {} }; } abort() {} },
    MutationObserver: class { observe() {} disconnect() {} },
    setTimeout, clearTimeout, URL, URLSearchParams, Promise
  };
  ctx.window = ctx; ctx.globalThis = ctx; ctx.self = ctx;
  ctx.addEventListener = () => {}; ctx.dispatchEvent = () => true;
  vmF5B.createContext(ctx);
  vmF5B.runInContext(fs.readFileSync(path.join(raizStatic, 'ux-phase42.js'), 'utf-8'), ctx, { filename: 'ux-phase42.js' });

  assert(doc.body.classList.contains('phase42-enabled'),
    'o phase42 não iniciou — o gate estaria medindo o nada');

  campos['delivery-employee'].value = '77';
  campos['delivery-employee'].dispatchEvent(new ctx.CustomEvent('change', { bubbles: true }));
  campos['delivery-epi'].value = '31';
  campos['delivery-epi'].dispatchEvent(new ctx.CustomEvent('change', { bubbles: true }));
  form.dispatchEvent(new ctx.CustomEvent('submit', { bubbles: true }));
  await new Promise((r) => setTimeout(r, 300));

  const gravadas = Object.keys(local._s).filter((k) => k.indexOf('epi:ux:phase4') === 0);
  eq(gravadas.length, 0, `contexto de negócio persistido: ${gravadas.join(', ')}`);
});


function _semComentariosF5B(texto) {
  return String(texto).split('\n').filter((l) => !l.trim().startsWith('//')).join('\n');
}

// ── Migração: as chaves legadas somem mesmo com a flag DESLIGADA ───────────
//
// Este é o caso que mais importa: quem teve a flag ligada um dia, gravou a
// chave, e hoje está com ela desligada. Se a limpeza morasse dentro do `init()`
// — que sai cedo sem a flag — a chave ficaria no disco para sempre justamente
// nessa pessoa. O encerramento de sessão preserva `localStorage` de propósito
// (F2), então não há outro caminho que a apague.
// Sem parâmetro de query string, de propósito: este helper existe para medir o
// caminho da flag DESLIGADA, e uma busca com `?ux_phase4x=1` ligaria o módulo e
// faria o gate medir outra coisa. Deixar o parâmetro aberto seria um convite a
// esse engano — e o CodeQL apontou, com razão, que ele nunca variava.
function comModuloUxF5B(arquivo, chavesPreexistentes) {
  const raizStatic = path.resolve(JS_ROOT, '..');
  const local = {
    _s: Object.assign({}, chavesPreexistentes || {}),
    getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
    setItem(k, v) { this._s[k] = String(v); },
    removeItem(k) { delete this._s[k]; },
    key(i) { return Object.keys(this._s)[i] ?? null; },
    get length() { return Object.keys(this._s).length; }
  };
  const doc = criarNoF5B('document', {});
  doc.body = criarNoF5B('body', {});
  doc.head = criarNoF5B('head', {});
  doc.readyState = 'complete';
  doc.getElementById = (id) => descendentesF5B(doc).find((n) => n.id === id) || null;
  doc.createElement = (t) => criarNoF5B(t, {});
  const ctx = {
    document: doc, localStorage: local,
    sessionStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    location: { search: '', href: 'http://local/' }, console,
    CustomEvent: class { constructor(t, o) { this.type = t; Object.assign(this, o || {}); } },
    AbortController: class { constructor() { this.signal = { addEventListener() {} }; } abort() {} },
    MutationObserver: class { observe() {} disconnect() {} },
    setTimeout, clearTimeout, URL, URLSearchParams, Promise
  };
  ctx.window = ctx; ctx.globalThis = ctx; ctx.self = ctx;
  ctx.addEventListener = () => {}; ctx.dispatchEvent = () => true;
  vmF5B.createContext(ctx);
  vmF5B.runInContext(fs.readFileSync(path.join(raizStatic, arquivo), 'utf-8'), ctx, { filename: arquivo });
  return { ctx, local, doc };
}

[
  ['ux-phase42.js', 'epi:ux:phase42:memory:v2', '{"last":{"employeeId":7,"companyId":3}}'],
  ['ux-phase43.js', 'epi:ux:phase43:state:v1', '{"qty":"5"}'],
  ['ux-phase44.js', 'epi.ux.phase44.filters.colaboradores', '{"employees-filter-search":"Maria"}']
].forEach(([arquivo, chave, valor]) => {
  test(`#343 F5-B: ${arquivo} apaga a chave legada mesmo com a flag desligada`, () => {
    // Sem query param e sem flag em storage: o módulo NÃO liga.
    const { ctx, local } = comModuloUxF5B(arquivo, { [chave]: valor, 'epi-theme': 'dark' });
    assert(!ctx.document.body.classList.contains(arquivo.replace('ux-', '').replace('.js', '') + '-enabled'),
      `${arquivo} ligou: o gate mediria o caminho errado`);
    eq(local.getItem(chave), null,
      `${chave} sobreviveu com a flag desligada — quem teve a flag ligada um dia ficaria com ela no disco para sempre`);
    eq(local.getItem('epi-theme'), 'dark',
      'a limpeza passou do próprio namespace e apagou chave alheia');
  });
});

test('#343 F5-B A1: descartar o estado do phase43 fecha o resumo e solta as guardas', () => {
  const raizStatic = path.resolve(JS_ROOT, '..');
  const fonte = _semComentariosF5B(fs.readFileSync(path.join(raizStatic, 'ux-phase43.js'), 'utf-8'));
  const corpo = fonte.slice(fonte.indexOf('function descartarEstado()'));
  const fim = corpo.indexOf('\n  }');
  const bloco = corpo.slice(0, fim);
  ['runtime.manualMode = false', 'runtime.lastSuggestion = null',
   'runtime.quickOpen = false', 'runtime.userEdited.clear()', 'phase43-quick-confirm']
    .forEach((trecho) => assert(bloco.includes(trecho),
      `descartarEstado não zera "${trecho}" — reentrar em Entregas reabriria o resumo da visita anterior`));
});

test('#343 F5-B A4: Entregas e Fichas entram no reset de filtros na entrada', () => {
  const app = appServidoF5B();
  assert(typeof app.ctx.resetModuleFiltersToInitial === 'function');
  const fonte = _semComentariosF5B(fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), 'app.js'), 'utf-8'));
  const mapa = fonte.slice(fonte.indexOf('const VIEW_FILTER_RESET'), fonte.indexOf('function resetModuleFiltersToInitial'));
  ['colaboradores:', 'epis:', 'estoque:', 'entregas:', 'fichas:']
    .forEach((v) => assert(mapa.includes(v), `${v} ficou de fora do reset de filtros na entrada`));
  assert(mapa.includes('syncDeliveriesSearchFilters()'), 'Entregas não ressincroniza o estado após limpar');
  assert(mapa.includes('syncFichaSearchFilters()'), 'Fichas não ressincroniza o estado após limpar');
});

test('#343 F5-B A3: o popstate reescreve a entrada de histórico só APÓS restaurar', () => {
  // A entrada precisa acabar carimbada com o estado RESTAURADO. Se o
  // `showView` gravasse antes (via historyMode: 'replace'), ela ficaria com os
  // filtros da view que está sendo deixada, e voltar a ela depois restauraria
  // o valor errado.
  const fonte = _semComentariosF5B(fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), 'app.js'), 'utf-8'));
  const trecho = fonte.slice(fonte.indexOf("safeOn(globalThis, 'popstate'"));
  const fim = trecho.indexOf('\n  });');
  const handler = trecho.slice(0, fim);
  assert(!handler.includes("historyMode: 'replace'"),
    'o showView do popstate voltou a gravar a entrada antes da restauração');
  const posShow = handler.indexOf('showView(nextView');
  const posRestore = handler.indexOf('restoreInteractiveSnapshot(event?.state)');
  const posReplace = handler.indexOf('history.replaceState(');
  assert(posShow > -1 && posRestore > -1 && posReplace > -1, 'o handler de popstate mudou de forma');
  assert(posShow < posRestore, 'a entrada no módulo deixou de vir antes da restauração');
  assert(posRestore < posReplace, 'a entrada de histórico é reescrita antes de o snapshot ser restaurado');
});


test('#343 F5-B N2: o mesmo módulo se redesenhando NÃO zera a navegação', () => {
  // `showView` é chamado também por fluxos internos: `startEditEmployee()`
  // chama `showView("colaboradores")` estando já em colaboradores. Zerar ali
  // apagaria os filtros que o usuário acabou de usar para achar o registro
  // que está editando.
  const app = appServidoF5B();
  app.entrarNoModulo('colaboradores');
  eq(app.abaAtiva('colaboradores'), 'cadastro');
  app.ctx.activateViewTab(app.doc.querySelector('nav[data-vtabs="colaboradores"]'), 'lista');
  app.redesenharMesmaVista('colaboradores');
  eq(app.abaAtiva('colaboradores'), 'lista',
    'um redesenho da MESMA view zerou a navegação — isso é trabalho em andamento sendo destruído');
});

test('#343 F5-B N9: Voltar/Avançar não sofre o reset de entrada', () => {
  // O snapshot carimbado por `sid` carrega só filtros de colaboradores/EPIs.
  // Se o reset rodasse no `popstate`, ele apagaria aba interna e filtros de
  // estoque que o snapshot não tem como devolver — o Voltar ficaria pior do
  // que era antes da fatia.
  const app = appServidoF5B();
  app.entrarNoModulo('estoque');
  app.ctx.activateViewTab(app.doc.querySelector('nav[data-vtabs="estoque"]'), 'movimentacoes');
  app.entrarNoModulo('dashboard');
  app.entrarNoModulo('estoque', { viaHistorico: true });
  eq(app.abaAtiva('estoque'), 'movimentacoes',
    'o Voltar sofreu o reset de entrada e perdeu estado que o snapshot não recupera');
  // E a entrada normal continua zerando.
  app.entrarNoModulo('dashboard');
  app.entrarNoModulo('estoque');
  eq(app.abaAtiva('estoque'), 'estoque', 'a reentrada normal deixou de zerar');
});

test('#343 F5-B N3: o phase42 publica a memória em RAM e o phase43 a consome', () => {
  const raizStatic = path.resolve(JS_ROOT, '..');
  const p42 = _semComentariosF5B(fs.readFileSync(path.join(raizStatic, 'ux-phase42.js'), 'utf-8'));
  const p43 = _semComentariosF5B(fs.readFileSync(path.join(raizStatic, 'ux-phase43.js'), 'utf-8'));
  assert(p42.includes('globalThis.__EPI_PHASE42_MEMORIA__ = memoriaEmMemoria'),
    'o phase42 parou de publicar a memória: o phase43 fica sem sugestão dentro do fluxo');
  assert(p43.includes('globalThis.__EPI_PHASE42_MEMORIA__'),
    'o phase43 parou de ler a memória do phase42');
  const inicio = p43.indexOf('function loadPhase42Memory()');
  const corpo = p43.slice(inicio, p43.indexOf('\n  }', inicio));
  assert(corpo.includes('__EPI_PHASE42_MEMORIA__'),
    'loadPhase42Memory deixou de consultar a memória do phase42 — a ponte em memória morreu');
  // A ponte não pode ressuscitar persistência.
  assert(!p43.includes("localStorage.getItem('epi:ux:phase42"), 'a ponte voltou a passar por storage');
});

test('#343 F5-B N7: descartar a memória do phase42 apaga o que já foi renderizado', () => {
  const raizStatic = path.resolve(JS_ROOT, '..');
  const fonte = _semComentariosF5B(fs.readFileSync(path.join(raizStatic, 'ux-phase42.js'), 'utf-8'));
  const i = fonte.indexOf("safeOn(document, 'epi:viewchange'");
  assert(i > -1, 'o descarte na troca de módulo sumiu do phase42');
  const bloco = fonte.slice(i, i + 900);
  ['descartarMemoria()', 'phase42-suggestion-box', 'phase42-alerts-box',
   'phase42-quick-confirm', 'userEdited.clear()', 'autofilledFieldIds.clear()']
    .forEach((trecho) => assert(bloco.includes(trecho),
      `o descarte não cobre "${trecho}" — a recomendação anterior seguiria visível na volta`));
});


test('#343 F5-B C1/C2/C6: Usuários, Unidades, paginação e seleção entram no reset', () => {
  const fonte = _semComentariosF5B(fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), 'app.js'), 'utf-8'));
  const mapa = fonte.slice(fonte.indexOf('const VIEW_FILTER_RESET'), fonte.indexOf('function resetModuleSelectionToInitial'));
  ['colaboradores:', 'epis:', 'estoque:', 'entregas:', 'fichas:', 'usuarios:', 'unidades:']
    .forEach((v) => assert(mapa.includes(v), `${v} ficou de fora do reset de filtros`));
  assert(mapa.includes('syncUserFilters()'), 'Usuários não ressincroniza após limpar');
  assert(mapa.includes('syncUnitsSearchFilters()'), 'Unidades não ressincroniza após limpar');
  // Paginação: só o caminho de EPIs precisava, os outros já voltavam à 1ª página
  // dentro das próprias funções de sincronização.
  assert(mapa.includes('state.pagination.epis = 1'),
    'a paginação de EPIs não volta à primeira página: sair na página 3 e voltar reabriria a página 3');
  // Seleção
  const selecao = fonte.slice(fonte.indexOf('function resetModuleSelectionToInitial'));
  assert(selecao.includes('employeesBulk?.clear?.()'), 'a seleção em lote de colaboradores não é limpa');
  assert(selecao.includes('state.selectedCompanyId = null'), 'a empresa selecionada não é limpa');
  const listener = fonte.slice(fonte.indexOf("safeOn(document, 'epi:viewchange'"))
    .slice(0, 1400);
  assert(listener.includes('resetModuleSelectionToInitial('), 'o reset de seleção não está ligado à entrada de módulo');
});

test('#343 F5-B C5: o popstate grava a view REALMENTE aberta, não a pedida', () => {
  // `showView` redireciona para `defaultView()` quando o papel perdeu acesso, e
  // sai sem trocar nada se o container não existe. Gravar `nextView` cru
  // deixaria URL e snapshot apontando para outra tela.
  const fonte = _semComentariosF5B(fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), 'app.js'), 'utf-8'));
  const i = fonte.indexOf("safeOn(globalThis, 'popstate'");
  const handler = fonte.slice(i, fonte.indexOf('\n  });', i));
  assert(handler.includes(".view.active"), 'o handler deixou de resolver a view efetivamente ativa');
  assert(!/replaceState\(\s*collectInteractiveSnapshot\(nextView\)/.test(handler),
    'o replaceState voltou a gravar a view pedida em vez da aberta');
});

test('#343 F5-B C4: a sugestão do phase43 é recalculada a cada troca de colaborador', () => {
  const p43 = _semComentariosF5B(fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), 'ux-phase43.js'), 'utf-8'));
  assert(p43.includes('function recomputarSugestao('), 'a recomputação da sugestão sumiu');
  assert(/id === 'delivery-employee'\) recomputarSugestao\(/.test(p43),
    'a sugestão deixou de ser recalculada na troca de colaborador: com a memória só em RAM, ela nasceria vazia e nunca se preencheria');
  // E o bind continua computando uma vez, pela mesma porta.
  const bind = p43.slice(p43.indexOf('function bindForm('));
  assert(bind.includes('recomputarSugestao(ui, form)'), 'o bind deixou de computar a sugestão inicial');
});

testAsync('#343 F5-B C3: redesenho da MESMA view não descarta a memória do phase42', async () => {
  const raizStatic = path.resolve(JS_ROOT, '..');
  const local = {
    _s: {},
    getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
    setItem(k, v) { this._s[k] = String(v); },
    removeItem(k) { delete this._s[k]; },
    key(i) { return Object.keys(this._s)[i] ?? null; },
    get length() { return Object.keys(this._s).length; }
  };
  const vista = criarNoF5B('div', { id: 'entregas-view', class: 'view active' });
  const form = criarNoF5B('form', { id: 'delivery-form' });
  ['delivery-company', 'delivery-unit-filter', 'delivery-employee', 'delivery-epi'].forEach((id) => {
    const c = criarNoF5B('select', { id });
    c.options = [];
    form.appendChild(c);
  });
  vista.appendChild(form);
  const doc = criarNoF5B('document', {});
  doc.appendChild(vista);
  doc.body = criarNoF5B('body', {});
  doc.head = criarNoF5B('head', {});
  doc.readyState = 'complete';
  doc.getElementById = (id) => descendentesF5B(doc).find((n) => n.id === id) || null;
  doc.createElement = (t) => criarNoF5B(t, {});
  const ctx = {
    document: doc, localStorage: local,
    sessionStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    location: { search: '?ux_phase42=1', href: 'http://local/?ux_phase42=1' }, console,
    CustomEvent: class { constructor(t, o) { this.type = t; Object.assign(this, o || {}); } },
    AbortController: class { constructor() { this.signal = { addEventListener() {} }; } abort() {} },
    MutationObserver: class { observe() {} disconnect() {} },
    setTimeout, clearTimeout, URL, URLSearchParams, Promise
  };
  ctx.window = ctx; ctx.globalThis = ctx; ctx.self = ctx;
  ctx.addEventListener = () => {}; ctx.dispatchEvent = () => true;
  vmF5B.createContext(ctx);
  vmF5B.runInContext(fs.readFileSync(path.join(raizStatic, 'ux-phase42.js'), 'utf-8'), ctx, { filename: 'ux-phase42.js' });
  assert(doc.body.classList.contains('phase42-enabled'), 'o phase42 não iniciou — o gate mediria o nada');

  const memoria = ctx.__EPI_PHASE42_MEMORIA__;
  assert(memoria && typeof memoria === 'object', 'a ponte em memória não foi publicada');
  memoria.events = [{ employeeId: '7', epiId: '3' }];

  // Recarga após entrega / troca de idioma: mesma view, memória preservada.
  doc.dispatchEvent(new ctx.CustomEvent('epi:viewchange', { detail: { view: 'entregas', anterior: 'entregas' } }));
  eq(Array.isArray(ctx.__EPI_PHASE42_MEMORIA__.events) ? ctx.__EPI_PHASE42_MEMORIA__.events.length : 0, 1,
    'um redesenho da MESMA view apagou a memória — o usuário nem saiu de Entregas');

  // Saída real: descarta.
  doc.dispatchEvent(new ctx.CustomEvent('epi:viewchange', { detail: { view: 'estoque', anterior: 'entregas' } }));
  eq(Object.keys(ctx.__EPI_PHASE42_MEMORIA__).length, 0, 'sair do módulo deixou de descartar a memória');
});

test('#343 F5-B C7: o descarte do phase42 tira as marcas visuais de autofill', () => {
  const fonte = _semComentariosF5B(fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), 'ux-phase42.js'), 'utf-8'));
  const i = fonte.indexOf("safeOn(document, 'epi:viewchange'");
  const bloco = fonte.slice(i, i + 1600);
  ['clearAutofillMark(campo)', 'phase42PrevValue', 'phase42Autofill']
    .forEach((t) => assert(bloco.includes(t),
      `o descarte não remove "${t}" — a marca visual sobreviveria a um ciclo completo de saída e volta`));
});

// ── Relatório ─────────────────────────────────────────────────────────────
// Os testes assíncronos rodam ANTES do relatório. Assertar em cima de um
// handler `async` sem esperar por ele daria verde por não ter chegado a
// executar — que é a forma mais silenciosa de falso-verde.
(async () => {
  for (const t of asyncTests) {
    try {
      resetStorage();
      globalThis.location = { search: '' };
      await t.fn();
      passed += 1;
    } catch (err) {
      failures.push({ name: t.name, message: err && err.message ? err.message : String(err) });
    }
  }
  if (failures.length) {
    console.error(`\nFALHAS (${failures.length}):`);
    failures.forEach((f) => console.error(`  ✗ ${f.name}: ${f.message}`));
    console.error(`\n${passed} passaram, ${failures.length} falharam`);
    process.exit(1);
  }
  console.log(`${passed} testes JS passaram`);
  process.exit(0);
})();
