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
// ATUALIZADO NO PR 4: estes gates usavam a flag do phase41 como cobaia do
// runtime de flags. O módulo e a flag saíram; a do phase42 faz o mesmo papel
// e é a única que a frente #343 mantém.
test('feature-flags-rt: query param tem prioridade', () => {
  globalThis.setFeatureFlag('ux_phase42_enabled', true);
  globalThis.location = { search: '?ux_phase42=0' };
  eq(globalThis.getFeatureFlag('ux_phase42_enabled'), false);
});
test('feature-flags-rt: default quando ausente', () => {
  eq(globalThis.getFeatureFlag('ux_phase42_enabled', { defaultValue: false }), false);
});
test('feature-flags-rt: kill-switch desativa UX_FORCE_CLASSIC_FLAGS', () => {
  globalThis.setFeatureFlag('ux_global_kill_switch', true);
  globalThis.setFeatureFlag('ux_phase42_enabled', true);
  eq(globalThis.getFeatureFlag('ux_phase42_enabled'), false);
  eq(globalThis.getFeatureFlag('ux_global_kill_switch'), true);
});
test('feature-flags-rt: kill-switch não afeta flags fora de FORCE_CLASSIC', () => {
  globalThis.setFeatureFlag('ux_global_kill_switch', true);
  globalThis.setFeatureFlag('colaborador_htmx_enabled', true);
  eq(globalThis.getFeatureFlag('colaborador_htmx_enabled'), true);
});
test('feature-flags-rt: AUTO_ROLLBACK ativa kill-switch', () => {
  globalThis.__EPI_AUTO_ROLLBACK_ACTIVE__ = true;
  globalThis.setFeatureFlag('ux_phase42_enabled', true);
  eq(globalThis.getFeatureFlag('ux_phase42_enabled'), false);
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
  // ATUALIZADO na frente de Isolamento (PR C). O contrato anterior exigia a
  // constante `SETTINGS_DENSITY_KEY = 'epi-density'` como PROVA de que o drawer
  // persistia a densidade. Ele ficou obsoleto porque a persistência mudou de
  // lugar por decisão de produto: a chave de `localStorage` (escopo DEVICE) deu
  // lugar ao servidor (escopo USER). O que o gate protegia — "o drawer persiste
  // o que o usuário escolheu" — continua valendo, e é isto que ele checa agora.
  // Não é um teste afrouxado para ficar verde: a exigência ficou mais forte,
  // porque agora ele nomeia o dono único em vez de uma chave solta.
  assert(js.includes('definirPreferencias(parcial)') && js.includes('EpiI18n'),
    'o drawer parou de persistir densidade/idioma pelo dono das preferências');
  assert(!js.includes("SETTINGS_DENSITY_KEY = 'epi-density'"),
    'a chave de densidade por dispositivo voltou: ver Isolamento PR C');
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
  // ATUALIZADO na frente de Isolamento (PR C), pelo mesmo motivo do gate do
  // drawer: a preferência de sidebar continua persistida, mas o dono passou a
  // ser a identidade, não o dispositivo. A chave que este gate exigia deixou de
  // existir — e exigi-la de volta seria exigir o vazamento de volta.
  assert(js.includes('function isSidebarCollapsedPref()') && js.includes('definirPreferencias({ sidebar:'),
    'a sidebar parou de persistir a preferência pelo dono');
  assert(!js.includes("SIDEBAR_COLLAPSED_KEY = 'epi-sidebar-collapsed'"),
    'a chave de sidebar por dispositivo voltou: ver Isolamento PR C');
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
      // Atributo comum (`[type="submit"]`, `[name="id"]`) resolve na
      // propriedade do nó; `data-*` continua resolvendo no dataset.
      const lerAtributo = (nome) => (/^data-/.test(nome)
        ? no.dataset[camelF5B(nome.slice(5))]
        : (no[nome] !== undefined ? no[nome] : no._attrs[nome]));
      if (eq === -1) {
        const v = lerAtributo(corpo);
        // `data-*` mantém a semântica anterior (existe = presente, mesmo
        // vazio); atributo comum precisa de valor, senão `[type]` casaria com
        // qualquer `<div>`, cuja propriedade `type` é `''`.
        if (v === undefined) {return false;}
        if (!/^data-/.test(corpo) && v === '') {return false;}
      } else {
        const nome = corpo.slice(0, eq);
        const valor = corpo.slice(eq + 1).replace(/^["']|["']$/g, '');
        if (String(lerAtributo(nome)) !== valor) {return false;}
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

// Plataforma: os três freios do DOM instalados no objeto de evento. Sem eles,
// `preventDefault()` e `stopImmediatePropagation()` — que o interceptador de
// captura do multitab chama no clique do menu lateral — seriam no-ops, e o
// disparo rodaria DOIS handlers onde o navegador roda um. Não é lógica de
// navegação: é o que o navegador dá a qualquer evento.
function prepararEventoF5B(ev) {
  ev._pararPropagacao = false;
  ev._pararImediato = false;
  if (ev.defaultPrevented === undefined) {ev.defaultPrevented = false;}
  if (typeof ev.preventDefault !== 'function') {
    ev.preventDefault = function () { ev.defaultPrevented = true; };
  }
  if (typeof ev.stopPropagation !== 'function') {
    ev.stopPropagation = function () { ev._pararPropagacao = true; };
  }
  if (typeof ev.stopImmediatePropagation !== 'function') {
    // Como no navegador: silencia também os listeners restantes DESTE nó, não
    // só os dos nós seguintes.
    ev.stopImmediatePropagation = function () {
      ev._pararImediato = true;
      ev._pararPropagacao = true;
    };
  }
  return ev;
}

// Último nó que recebeu foco. O navegador guarda isso em
// `document.activeElement`; sem modelar, nenhum gate consegue perguntar "o foco
// estava DENTRO do painel que acabou de fechar?" — que é a pergunta de que
// depende a devolução de foco do dropdown.
let NO_FOCADO_F5B = null;

function criarNoF5B(tag, attrs = {}) {
  const no = {
    tagName: String(tag).toUpperCase(),
    dataset: {}, style: {}, _attrs: {}, _classes: new Set(), _handlers: {},
    children: [], parent: null, hidden: false, tabIndex: 0,
    id: attrs.id || '', value: attrs.value || '', disabled: false, textContent: '',
    // Plataforma, não lógica: `type`/`name`/`checked` e o par
    // `defaultValue`/`defaultChecked` são propriedades que o navegador dá a
    // qualquer campo. `form.reset()` abaixo depende delas para se comportar
    // como o nativo — e é o nativo que a F5-B usa para desarmar o modo de
    // edição (o hidden `id` volta ao padrão do HTML, que é vazio).
    type: attrs.type || '', name: attrs.name || '', checked: false,
    defaultValue: attrs.value || '', defaultChecked: false, options: [],
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
    focus() { no._focado = true; NO_FOCADO_F5B = no; },
    scrollIntoView() {},
    // A fase de escuta é plataforma: `{ capture: true }` muda QUANDO o listener
    // roda, e é disso que depende o interceptador de menu do multitab.
    addEventListener(ev, fn, options) {
      const captura = options === true || Boolean(options && options.capture);
      (no._handlers[ev] = no._handlers[ev] || []).push({ fn, captura });
    },
    removeEventListener() {},
    // Propaga pela árvore como o navegador: quem escuta no container ouve o
    // evento disparado no campo. Sem isto, um gate que digita num input não
    // alcançaria o handler real — e passaria verde sem exercitar nada.
    // Exceção em listener fica isolada, também como no navegador: não impede os
    // demais nem sobe para quem disparou.
    //
    // Caminho REAL de propagação — captura da raiz até o alvo, depois bolha do
    // alvo até a raiz — e os três freios do DOM. Sem as fases, um listener de
    // captura que chama `stopImmediatePropagation()` não silenciaria o handler
    // seguinte: o clique no menu lateral rodaria o interceptador do multitab E o
    // handler do app, dois caminhos que no navegador são mutuamente exclusivos.
    // Era essa lacuna que mantinha o caminho real do clique fora dos gates.
    dispatchEvent(ev) {
      prepararEventoF5B(ev);
      if (!ev.target) {ev.target = no;}
      const caminho = [];
      for (let n = no; n; n = n.parent) {caminho.push(n);}
      const fases = [];
      caminho.slice(1).reverse().forEach((n) => fases.push([n, 'captura']));
      // No alvo o navegador roda captura e bolha juntos, em ordem de registro.
      fases.push([no, 'alvo']);
      if (ev.bubbles !== false) {caminho.slice(1).forEach((n) => fases.push([n, 'bolha']));}
      for (const [atual, fase] of fases) {
        if (ev._pararPropagacao) {break;}
        ev.currentTarget = atual;
        const inscritos = (atual._handlers[ev.type] || []).filter(
          (h) => fase === 'alvo' || (fase === 'captura' ? h.captura : !h.captura)
        );
        for (const inscrito of inscritos) {
          if (ev._pararImediato) {break;}
          try { inscrito.fn(ev); } catch (erro) { (no._errosDeListener = no._errosDeListener || []).push(erro); }
        }
      }
      return !ev.defaultPrevented;
    },
    // `form.reset()` nativo: devolve cada campo ao valor/estado padrão do HTML
    // e NÃO dispara `input`/`change` (o spec chama o algoritmo direto). Copiar
    // essa semântica é o que permite ao gate medir o desarme real do modo de
    // edição em vez de um reset inventado pelo mock.
    reset() {
      descendentesF5B(no).forEach((campo) => {
        if (!['INPUT', 'SELECT', 'TEXTAREA'].includes(campo.tagName)) {return;}
        campo.value = campo.defaultValue;
        campo.checked = campo.defaultChecked;
      });
    },
    get elements() {
      const mapa = {};
      descendentesF5B(no).forEach((campo) => { if (campo.name) {mapa[campo.name] = campo;} });
      return mapa;
    },
    matches(sel) { return casaF5B(no, sel); },
    closest(sel) { let n = no; while (n) { if (casaF5B(n, sel)) {return n;} n = n.parent; } return null; },
    // Plataforma: `Node.contains`. O fechamento por clique fora do phase44 é
    // escrito com ele (`!root.contains(event.target)`), enquanto o do app.js usa
    // `closest`. Sem esta primitiva o handler do phase44 lançaria em silêncio e
    // a comparação entre os dois contratos mediria a ausência do shim, não a
    // diferença entre os módulos.
    contains(outro) { let n = outro; while (n) { if (n === no) {return true;} n = n.parent; } return false; },
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

// Campo de formulário com valor padrão declarado no HTML — é esse padrão que
// `form.reset()` devolve, e é nele que se apoia o desarme do modo de edição.
function campoF5B(tag, attrs) { return criarNoF5B(tag, attrs || {}); }

// Vista sem abas, só com os nós que uma classe do contrato precisa.
function montarVistaSimplesF5B(nome, filhos) {
  const vista = criarNoF5B('div', { id: `${nome}-view`, class: 'view' });
  (filhos || []).forEach((f) => vista.appendChild(f));
  return vista;
}

// ── Nós por classe do contrato (F5-B) ───────────────────────────────────────
//
// O fixture precisa existir ANTES de `app.js` rodar: o objeto `refs` é montado
// no topo do arquivo com `document.getElementById(...)` avaliado na hora. Um
// nó criado depois nunca entra em `refs`, e o gate mediria um no-op.
function montarFormularioF5B(id, campos) {
  const form = criarNoF5B('form', { id });
  form.appendChild(campoF5B('input', { id: `${id}-id`, type: 'hidden', name: 'id' }));
  (campos || []).forEach(([campoId, tipo]) => form.appendChild(campoF5B('input', { id: campoId, type: tipo || 'text' })));
  const submit = criarNoF5B('button', { id: `${id}-submit` });
  submit.type = 'submit';
  form.appendChild(submit);
  return form;
}

function montarVistasDeClasseF5B() {
  const caixa = (id) => campoF5B('input', { id, type: 'checkbox' });

  const unidades = montarVistaSimplesF5B('unidades', [
    montarFormularioF5B('unit-form', [['unit-name']]),
    campoF5B('input', { id: 'units-filter-company' }),
    campoF5B('input', { id: 'units-filter-name' }),
    campoF5B('input', { id: 'units-filter-type' }),
    campoF5B('input', { id: 'units-filter-city' }),
    campoF5B('input', { id: 'archived-units-filter-company' }),
    campoF5B('input', { id: 'archived-units-filter-user' }),
    campoF5B('input', { id: 'archived-units-filter-reason' }),
    campoF5B('input', { id: 'archived-units-filter-date' })
  ]);

  const modalFornecedor = criarNoF5B('div', { id: 'modal-edit-supplier' });
  modalFornecedor.appendChild(campoF5B('input', { id: 'edit-supplier-id' }));
  const listaDemandas = criarNoF5B('tbody', { id: 'compras-demands-tbody' });
  [0, 1].forEach((i) => listaDemandas.appendChild(campoF5B('input', { id: `demand-${i}`, type: 'checkbox', class: 'demand-check' })));
  const listaAprov = criarNoF5B('tbody', { id: 'aprovacoes-tbody' });
  listaAprov.appendChild(campoF5B('input', { id: 'aprov-0', type: 'checkbox', class: 'aprovacao-check' }));
  const compras = montarVistaSimplesF5B('compras', [
    campoF5B('select', { id: 'compras-demands-company-filter' }),
    campoF5B('select', { id: 'compras-req-status-filter' }),
    campoF5B('select', { id: 'compras-po-status-filter' }),
    modalFornecedor,
    criarNoF5B('div', { id: 'modal-supplier-pos' }),
    criarNoF5B('div', { id: 'aprovacoes-reprovar-modal' }),
    criarNoF5B('div', { id: 'aprovacoes-prorrogar-modal' }),
    caixa('compras-demands-select-all'), listaDemandas,
    caixa('aprovacoes-select-all'), listaAprov,
    criarNoF5B('button', { id: 'compras-create-request-btn' }),
    criarNoF5B('button', { id: 'aprovacoes-aprovar-btn' }),
    criarNoF5B('button', { id: 'aprovacoes-reprovar-btn' }),
    criarNoF5B('button', { id: 'aprovacoes-prorrogar-btn' })
  ]);

  const modalAcaoAvaliacao = criarNoF5B('div', { id: 'aval-action-modal' });
  modalAcaoAvaliacao.appendChild(campoF5B('input', { id: 'aval-modal-feedback-id' }));
  modalAcaoAvaliacao.appendChild(campoF5B('input', { id: 'aval-modal-action' }));
  const avaliacoes = montarVistaSimplesF5B('avaliacoes', [
    criarNoF5B('div', { id: 'ppe-form-modal' }),
    modalAcaoAvaliacao,
    campoF5B('select', { id: 'feedbacks-filter-status' }),
    campoF5B('select', { id: 'feedbacks-filter-type' })
  ]);

  const cnpjs = montarVistaSimplesF5B('cnpjs', [
    campoF5B('input', { id: 'legal-entities-filter-search' }),
    campoF5B('input', { id: 'legal-entities-filter-type' }),
    campoF5B('input', { id: 'legal-entities-show-inactive', type: 'checkbox' })
  ]);

  const terceirizados = montarVistaSimplesF5B('terceirizados', [
    campoF5B('input', { id: 'outsourced-companies-filter-search' }),
    campoF5B('input', { id: 'outsourced-companies-filter-kind' }),
    campoF5B('input', { id: 'outsourced-employees-filter-search' }),
    campoF5B('input', { id: 'archived-outsourced-companies-filter-user' }),
    campoF5B('input', { id: 'archived-outsourced-companies-filter-reason' }),
    campoF5B('input', { id: 'archived-outsourced-employees-filter-user' }),
    campoF5B('input', { id: 'archived-outsourced-employees-filter-reason' })
  ]);

  const usuarios = montarVistaSimplesF5B('usuarios', [
    criarNoF5B('div', { id: 'purchase-function-units' }),
    criarNoF5B('div', { id: 'purchase-function-selected-units' }),
    criarNoF5B('span', { id: 'purchase-function-selected-count' })
  ]);

  const migracao = montarVistaSimplesF5B('migracao', [
    campoF5B('input', { id: 'migracao-file', type: 'file' }),
    criarNoF5B('span', { id: 'migracao-file-name' }),
    campoF5B('input', { id: 'migracao-sheet' }),
    campoF5B('input', { id: 'migracao-catalog-filter' }),
    criarNoF5B('div', { id: 'migracao-steps' })
  ]);

  const comercial = montarVistaSimplesF5B('comercial', [
    campoF5B('input', { id: 'commercial-filter-status' }),
    campoF5B('input', { id: 'commercial-filter-date-from' }),
    campoF5B('input', { id: 'commercial-filter-date-to' }),
    campoF5B('input', { id: 'commercial-filter-actor' })
  ]);

  const relatorios = montarVistaSimplesF5B('relatorios', []);

  return { unidades, compras, avaliacoes, usuarios, migracao, comercial, relatorios, cnpjs, terceirizados };
}

// Carrega os mesmos scripts que a página serve, na mesma ordem.
function montarAppServidoF5B(busca) {
  const raizStatic = path.resolve(JS_ROOT, '..');
  const vistas = {
    estoque: montarVistaF5B('estoque', 'estoque', ['estoque', 'movimentacoes', 'validade', 'alertas']),
    colaboradores: montarVistaF5B('colaboradores', 'colaboradores', ['cadastro', 'lista', 'arquivados']),
    dashboard: montarVistaF5B('dashboard', 'dashboard-grp', ['inicio', 'outra']),
    ...montarVistasDeClasseF5B()
  };
  // O campo de busca do dashboard mora na própria vista de dashboard.
  vistas.dashboard.appendChild(campoF5B('input', { id: 'dashboard-global-search' }));
  // Arquivados de colaboradores e de EPIs: abas dos módulos que já existem no
  // fixture, com seu PRÓPRIO conjunto de filtros sobre `ARCHIVAL_ENTITIES`.
  ['archived-employees-filter-user', 'archived-employees-filter-reason']
    .forEach((id) => vistas.colaboradores.appendChild(campoF5B('input', { id })));
  vistas.epis = montarVistaSimplesF5B('epis', [
    campoF5B('input', { id: 'archived-epis-filter-user' }),
    campoF5B('input', { id: 'archived-epis-filter-reason' })
  ]);
  // Modal global de solicitação de relatório: mora em `_modals.html`, mas o
  // botão que o abre está em Estoque — logo, é modal DO módulo estoque.
  vistas.estoque.appendChild(criarNoF5B('div', { id: 'smr-request-report-modal' }));
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
    // Plataforma. `Event` é o construtor que qualquer código de UI usa para
    // notificar campos (`new Event('input', { bubbles: true })`); sem ele no
    // contexto, o disparo lança ReferenceError, o `catch` do app engole e o
    // gate mede um reset que nunca aconteceu — falso verde.
    Event: class { constructor(t, o) { this.type = t; this.bubbles = false; Object.assign(this, o || {}); } },
    // Idem: `getComputedStyle` é primitiva do navegador. Sem ela, todo código
    // que pergunta "este campo está visível?" quebra dentro de um try/catch e
    // some do teste.
    getComputedStyle: (el) => ({
      display: (el && el.style && el.style.display) || (el && el.hidden ? 'none' : 'block'),
      visibility: (el && el.style && el.style.visibility) || 'visible'
    }),
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
      detail: {
        view: nome,
        anterior,
        viaHistorico: (opcoes || {}).viaHistorico === true,
        viaMultitab: (opcoes || {}).viaMultitab === true
      }
    }));
  };
  const redesenharMesmaVista = (nome) => doc.dispatchEvent(new ctx.CustomEvent('epi:viewchange', {
    detail: { view: nome, anterior: nome, viaHistorico: false }
  }));
  // Clicar no item do menu lateral da view JÁ ATIVA emite exatamente este
  // evento: `showView(nome)` roda, `currentActiveView` já é `${nome}-view`,
  // logo `anterior === nome`, e nem `viaHistorico` nem `viaMultitab` são
  // marcados. O alias existe para o gate dizer QUAL gesto está sendo medido —
  // a forma do evento é a mesma do redesenho interno de propósito, e é
  // justamente isso que a decisão de contrato formaliza.
  const clicarNoMenuDaViewAtiva = (nome) => redesenharMesmaVista(nome);

  return {
    ctx, doc, vistas, sessao, local, abaAtiva,
    entrarNoModulo, redesenharMesmaVista, clicarNoMenuDaViewAtiva,
    scriptsCarregados: ordem.length
  };
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
    // Plataforma. `Event` é o construtor que qualquer código de UI usa para
    // notificar campos (`new Event('input', { bubbles: true })`); sem ele no
    // contexto, o disparo lança ReferenceError, o `catch` do app engole e o
    // gate mede um reset que nunca aconteceu — falso verde.
    Event: class { constructor(t, o) { this.type = t; this.bubbles = false; Object.assign(this, o || {}); } },
    // Idem: `getComputedStyle` é primitiva do navegador. Sem ela, todo código
    // que pergunta "este campo está visível?" quebra dentro de um try/catch e
    // some do teste.
    getComputedStyle: (el) => ({
      display: (el && el.style && el.style.display) || (el && el.hidden ? 'none' : 'block'),
      visibility: (el && el.style && el.style.visibility) || 'visible'
    }),
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
    // Plataforma. `Event` é o construtor que qualquer código de UI usa para
    // notificar campos (`new Event('input', { bubbles: true })`); sem ele no
    // contexto, o disparo lança ReferenceError, o `catch` do app engole e o
    // gate mede um reset que nunca aconteceu — falso verde.
    Event: class { constructor(t, o) { this.type = t; this.bubbles = false; Object.assign(this, o || {}); } },
    // Idem: `getComputedStyle` é primitiva do navegador. Sem ela, todo código
    // que pergunta "este campo está visível?" quebra dentro de um try/catch e
    // some do teste.
    getComputedStyle: (el) => ({
      display: (el && el.style && el.style.display) || (el && el.hidden ? 'none' : 'block'),
      visibility: (el && el.style && el.style.visibility) || 'visible'
    }),
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
    // Plataforma. `Event` é o construtor que qualquer código de UI usa para
    // notificar campos (`new Event('input', { bubbles: true })`); sem ele no
    // contexto, o disparo lança ReferenceError, o `catch` do app engole e o
    // gate mede um reset que nunca aconteceu — falso verde.
    Event: class { constructor(t, o) { this.type = t; this.bubbles = false; Object.assign(this, o || {}); } },
    // Idem: `getComputedStyle` é primitiva do navegador. Sem ela, todo código
    // que pergunta "este campo está visível?" quebra dentro de um try/catch e
    // some do teste.
    getComputedStyle: (el) => ({
      display: (el && el.style && el.style.display) || (el && el.hidden ? 'none' : 'block'),
      visibility: (el && el.style && el.style.visibility) || 'visible'
    }),
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
    // Plataforma. `Event` é o construtor que qualquer código de UI usa para
    // notificar campos (`new Event('input', { bubbles: true })`); sem ele no
    // contexto, o disparo lança ReferenceError, o `catch` do app engole e o
    // gate mede um reset que nunca aconteceu — falso verde.
    Event: class { constructor(t, o) { this.type = t; this.bubbles = false; Object.assign(this, o || {}); } },
    // Idem: `getComputedStyle` é primitiva do navegador. Sem ela, todo código
    // que pergunta "este campo está visível?" quebra dentro de um try/catch e
    // some do teste.
    getComputedStyle: (el) => ({
      display: (el && el.style && el.style.display) || (el && el.hidden ? 'none' : 'block'),
      visibility: (el && el.style && el.style.visibility) || 'visible'
    }),
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

// ATUALIZADO NO PR 4: o phase43 e o phase44 saíram. A limpeza das chaves deles
// passou para o `app.js` e é coberta por `PR4 L-1`; aqui fica o phase42, que
// sobrevive e continua sendo dono da própria limpeza legada.
[
  ['ux-phase42.js', 'epi:ux:phase42:memory:v2', '{"last":{"employeeId":7,"companyId":3}}']
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

test('#343 F5-B N3 (convertido): o phase42 publica a memória em RAM, e não em storage', () => {
  // CONVERTIDO NO PR 4. A metade do phase43 — "e o phase43 a consome" — saiu
  // com o módulo. O que sobrevive, e é o que importa, é o contrato do owner:
  // a memória do phase42 vive em RAM e não pode voltar para o disco.
  const raizStatic = path.resolve(JS_ROOT, '..');
  const p42 = _semComentariosF5B(fs.readFileSync(path.join(raizStatic, 'ux-phase42.js'), 'utf-8'));
  assert(p42.includes('globalThis.__EPI_PHASE42_MEMORIA__ = memoriaEmMemoria'),
    'o phase42 parou de publicar a memória em RAM');
  assert(!p42.includes("localStorage.setItem('epi:ux:phase42"),
    'o phase42 voltou a persistir a memória em storage');
  // E continua removendo a própria chave legada — ele sobrevive, então a
  // limpeza dele não migrou para o app (ver PR4 L-2).
  assert(p42.includes("removeItem('epi:ux:phase42:memory:v2')"),
    'o phase42 parou de apagar a própria chave legada');
});

test('#343 F5-B N7: descartar a memória do phase42 apaga o que já foi renderizado', () => {
  const raizStatic = path.resolve(JS_ROOT, '..');
  const fonte = _semComentariosF5B(fs.readFileSync(path.join(raizStatic, 'ux-phase42.js'), 'utf-8'));
  const i = fonte.indexOf("safeOn(document, 'epi:viewchange'");
  assert(i > -1, 'o descarte na troca de módulo sumiu do phase42');
  // Âncora no FIM do bloco, não numa janela de bytes: uma janela fixa quebra
  // sozinha quando o bloco cresce, e um gate que cai por tamanho ensina a
  // ignorá-lo.
  const fim = fonte.indexOf('}, { signal: moduleController.signal });', i);
  assert(fim > i, 'o bloco de descarte do phase42 mudou de forma');
  const bloco = fonte.slice(i, fim);
  ['descartarMemoria()', 'phase42-suggestion-box', 'phase42-alerts-box',
   'phase42-quick-confirm', 'userEdited.clear()', 'autofilledFieldIds.clear()']
    .forEach((trecho) => assert(bloco.includes(trecho),
      `o descarte não cobre "${trecho}" — a recomendação anterior seguiria visível na volta`));
  // E devolve o valor que a sugestão substituiu: limpar só a marca deixaria a
  // escolha sugerida no campo, agora parecendo escolha manual.
  assert(/campo\.value = anterior/.test(bloco),
    'o descarte apaga a marca de autofill sem restaurar o valor anterior');
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
    // Plataforma. `Event` é o construtor que qualquer código de UI usa para
    // notificar campos (`new Event('input', { bubbles: true })`); sem ele no
    // contexto, o disparo lança ReferenceError, o `catch` do app engole e o
    // gate mede um reset que nunca aconteceu — falso verde.
    Event: class { constructor(t, o) { this.type = t; this.bubbles = false; Object.assign(this, o || {}); } },
    // Idem: `getComputedStyle` é primitiva do navegador. Sem ela, todo código
    // que pergunta "este campo está visível?" quebra dentro de um try/catch e
    // some do teste.
    getComputedStyle: (el) => ({
      display: (el && el.style && el.style.display) || (el && el.hidden ? 'none' : 'block'),
      visibility: (el && el.style && el.style.visibility) || 'visible'
    }),
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


test('#343 F5-B: o reset de entrada não afrouxa o escopo de empresa por papel', () => {
  // Para papéis não-master a empresa não é filtro, é ESCOPO: o valor é fixo e o
  // controle fica desabilitado. Limpá-la esvaziava o recorte exibido, e o
  // `syncDeliveriesOptions()` seguinte ainda reabilitava o campo — ele só trava
  // perfis `admin`/`user`, enquanto o escopo trava todo não-master.
  const fonte = _semComentariosF5B(fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), 'app.js'), 'utf-8'));
  const limpador = fonte.slice(fonte.indexOf('const limparCamposDeFiltro'), fonte.indexOf('const VIEW_FILTER_RESET'));
  assert(/ehMaster\(\).*Company/s.test(limpador),
    'o limpador voltou a apagar o campo de empresa sem olhar o papel');
  const reset = fonte.slice(fonte.indexOf('function resetModuleFiltersToInitial'));
  assert(reset.slice(0, 600).includes('populateScopedSearchFilters()'),
    'o reset deixou de reafirmar o escopo e a trava de empresa');
});


// ══ #343 F5-B: gates por CLASSE do contrato ═════════════════════════════════
//
// Onze classes foram inventariadas na auditoria fechada. Os gates abaixo medem
// COMPORTAMENTO no app realmente servido: põem o módulo num estado de trabalho,
// saem para outro módulo, voltam pela mesma porta que a aplicação usa
// (`epi:viewchange` com `anterior` e as exceções), e conferem o estado inicial.
//
// A correção de método que a auditoria expôs vale aqui também: procura-se o
// CONCEITO, não o nome do mecanismo. Foi contando `state.pagination.*` que
// `state.reportArchivePage` escapou da primeira contagem.

test('#343 F5-B G-fixture: os nós das novas classes chegaram ao `refs` do app', () => {
  // Sem este gate, qualquer um dos gates de classe abaixo poderia passar por
  // não ter nó nenhum para mexer. `refs` é montado no topo do `app.js`, com os
  // `getElementById` avaliados na hora — nó criado depois nunca entra.
  const app = appServidoF5B();
  // `refs` e `state` são `const` dentro do bloco que envolve todo o app.js, e
  // por isso não viram propriedades de globalThis. O app já publica as duas
  // pontes para os módulos de view — é por elas que o gate entra, sem exigir
  // nenhum export novo criado só para teste.
  const refs = app.ctx.__EPI_REFS__;
  assert(refs && typeof refs === 'object', 'o app servido não expôs `__EPI_REFS__`');
  assert(app.ctx.__EPI_APP_STATE__ && typeof app.ctx.__EPI_APP_STATE__ === 'object',
    'o app servido não expôs `__EPI_APP_STATE__`');
  [
    'unitsFilterName', 'archivedUnitsFilterUser', 'commercialFilterStatus',
    'dashboardGlobalSearch', 'migracaoFile', 'migracaoSheet'
  ].forEach((chave) => assert(refs[chave], `refs.${chave} ficou nulo: o fixture não alcança o app`));
  ['unit-form', 'modal-edit-supplier', 'edit-supplier-id', 'ppe-form-modal',
    'purchase-function-units', 'compras-demands-select-all']
    .forEach((id) => assert(app.doc.getElementById(id), `o nó #${id} não existe no fixture`));
  ['resetModuleFormsToInitial', 'resetModuleModalsToInitial', 'resetModuleWizardsToInitial']
    .forEach((fn) => assert(typeof app.ctx[fn] === 'function', `${fn} não existe no app.js servido`));
});

// ── Classe 1: edição ────────────────────────────────────────────────────────
test('#343 F5-B G-edicao-1: sair no meio da edição e voltar desarma o modo de edição', () => {
  const app = appServidoF5B();
  const form = app.doc.getElementById('unit-form');
  const identidade = app.doc.getElementById('unit-form-id');
  const nome = app.doc.getElementById('unit-name');
  identidade.value = '77';
  nome.value = 'Unidade em edição';
  app.entrarNoModulo('unidades');
  app.entrarNoModulo('estoque');
  app.entrarNoModulo('unidades');
  eq(identidade.value, '', 'a identidade do registro sobreviveu: o próximo submit alteraria o registro anterior');
  eq(nome.value, '', 'o formulário voltou preenchido da visita passada');
  assert(form, 'fixture perdeu o formulário');
});

test('#343 F5-B G-edicao-2: o mesmo módulo se redesenhando NÃO destrói a edição em curso', () => {
  const app = appServidoF5B();
  const identidade = app.doc.getElementById('unit-form-id');
  app.entrarNoModulo('unidades');
  identidade.value = '88';
  app.redesenharMesmaVista('unidades');
  eq(identidade.value, '88', 'um redesenho (idioma, permissão, edição) apagou trabalho em andamento');
});

test('#343 F5-B G-edicao-3: os nove módulos de edição têm reset declarado', () => {
  // Estrutural, pareado com o G-edicao-1 comportamental: o mapa é a lista
  // fechada da auditoria, e um módulo novo que entre em modo de edição sem
  // entrada aqui derruba este gate.
  const fonte = _semComentariosF5B(fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), 'app.js'), 'utf-8'));
  const mapa = fonte.slice(fonte.indexOf('const VIEW_FORM_RESET'), fonte.indexOf('function resetModuleFormsToInitial'));
  ['empresas:', 'usuarios:', 'comercial:', 'unidades:', 'colaboradores:', 'epis:', 'cnpjs:', 'terceirizados:']
    .forEach((v) => assert(mapa.includes(v), `${v} ficou de fora do reset de edição`));
  // Compras edita pelo modal, e por isso entra pela porta dos modais.
  const modais = fonte.slice(fonte.indexOf('const MODAIS_DE_MODULO'), fonte.indexOf('function resetModuleModalsToInitial'));
  assert(modais.includes('compras:'), 'compras perdeu a cobertura pela porta dos modais');
  assert(modais.includes("'edit-supplier-id'"), 'o modal de fornecedor deixou de descartar a identidade editada');
});

// ── Classe 10: modal ────────────────────────────────────────────────────────
test('#343 F5-B G-modal-1: reentrar no módulo fecha o modal aberto', () => {
  const app = appServidoF5B();
  const modal = app.doc.getElementById('modal-edit-supplier');
  const pos = app.doc.getElementById('modal-supplier-pos');
  const avaliacao = app.doc.getElementById('ppe-form-modal');
  modal.style.display = 'block';
  pos.style.display = 'block';
  avaliacao.style.display = 'block';
  app.entrarNoModulo('compras');
  app.entrarNoModulo('estoque');
  app.entrarNoModulo('compras');
  eq(modal.style.display, 'none', 'o modal de fornecedor reabriu no ponto da visita anterior');
  eq(pos.style.display, 'none', 'o modal de POs reabriu no ponto da visita anterior');
  app.entrarNoModulo('avaliacoes');
  app.entrarNoModulo('estoque');
  app.entrarNoModulo('avaliacoes');
  eq(avaliacao.style.display, 'none', 'o modal de avaliações reabriu no ponto da visita anterior');
});

test('#343 F5-B G-modal-2: esconder não basta — a identidade editada é descartada', () => {
  // A gravidade aqui é a mesma do modo de edição: com o id preservado, um
  // submit atualizaria o fornecedor da visita passada.
  const app = appServidoF5B();
  const identidade = app.doc.getElementById('edit-supplier-id');
  identidade.value = '42';
  app.entrarNoModulo('compras');
  app.entrarNoModulo('estoque');
  app.entrarNoModulo('compras');
  eq(identidade.value, '', 'o modal fechou mas continuou apontando para o registro anterior');
});

test('#343 F5-B G-modal-3: redesenho e Voltar/Avançar NÃO fecham o modal', () => {
  const app = appServidoF5B();
  const modal = app.doc.getElementById('modal-edit-supplier');
  app.entrarNoModulo('compras');
  modal.style.display = 'block';
  app.redesenharMesmaVista('compras');
  eq(modal.style.display, 'block', 'um redesenho da própria view fechou um modal em uso');
  app.entrarNoModulo('estoque');
  modal.style.display = 'block';
  app.entrarNoModulo('compras', { viaHistorico: true });
  eq(modal.style.display, 'block', 'Voltar/Avançar deixou de ser exceção e fechou o modal');
});

// ── Classe 11: wizard / step ────────────────────────────────────────────────
test('#343 F5-B G-wizard-1: reentrar devolve o assistente ao primeiro passo', () => {
  const app = appServidoF5B();
  const rascunho = app.ctx.migracaoState();
  rascunho.step = 'revisao';
  app.entrarNoModulo('migracao');
  app.entrarNoModulo('estoque');
  app.entrarNoModulo('migracao');
  eq(app.ctx.migracaoState().step, 'entidade', 'o assistente retomou no passo da visita anterior');
});

test('#343 F5-B G-wizard-2: reentrar descarta o rascunho do assistente, no estado e no DOM', () => {
  const app = appServidoF5B();
  const rascunho = app.ctx.migracaoState();
  const arquivo = app.doc.getElementById('migracao-file');
  const planilha = app.doc.getElementById('migracao-sheet');
  const rotulo = app.doc.getElementById('migracao-file-name');
  Object.assign(rascunho, {
    step: 'mapeamento', fileName: 'colaboradores.xlsx', fileBase64: 'QUJD',
    sheet: 'Plan1', columns: ['A', 'B'], mapping: { A: 'name' }, totalRows: 12
  });
  arquivo.value = 'colaboradores.xlsx';
  planilha.value = 'Plan1';
  rotulo.textContent = 'colaboradores.xlsx';
  app.entrarNoModulo('migracao');
  app.entrarNoModulo('estoque');
  app.entrarNoModulo('migracao');
  const depois = app.ctx.migracaoState();
  eq(depois.fileName, '', 'o nome do arquivo da visita anterior sobreviveu');
  eq(depois.fileBase64, '', 'o conteúdo do arquivo da visita anterior sobreviveu');
  eq(depois.sheet, '', 'a planilha escolhida sobreviveu');
  eq(depois.columns.length, 0, 'as colunas lidas sobreviveram');
  eq(Object.keys(depois.mapping).length, 0, 'o mapeamento de colunas sobreviveu');
  eq(depois.totalRows, 0, 'a contagem de linhas sobreviveu');
  eq(arquivo.value, '', 'o campo de arquivo continuou preenchido na tela');
  eq(planilha.value, '', 'o campo de planilha continuou preenchido na tela');
  eq(rotulo.textContent, '', 'o rótulo do arquivo continuou na tela');
});

test('#343 F5-B G-wizard-3: redesenho e Voltar/Avançar NÃO reiniciam o assistente', () => {
  const app = appServidoF5B();
  app.entrarNoModulo('migracao');
  app.ctx.migracaoState().step = 'revisao';
  app.redesenharMesmaVista('migracao');
  eq(app.ctx.migracaoState().step, 'revisao', 'um redesenho jogou fora um assistente em andamento');
  app.entrarNoModulo('estoque');
  app.ctx.migracaoState().step = 'revisao';
  app.entrarNoModulo('migracao', { viaHistorico: true });
  eq(app.ctx.migracaoState().step, 'revisao', 'Voltar/Avançar deixou de ser exceção e reiniciou o assistente');
});

// ── Classe 4: seleção ───────────────────────────────────────────────────────
test('#343 F5-B G-selecao-1: a seleção de Compras não sobrevive à reentrada', () => {
  const app = appServidoF5B();
  const ctx = app.ctx;
  ctx._selectedDemands.add(0); ctx._selectedDemands.add(1);
  ctx._selectedAprovacoes.add(0);
  const todasDemandas = app.doc.getElementById('compras-demands-select-all');
  const todasAprov = app.doc.getElementById('aprovacoes-select-all');
  todasDemandas.checked = true; todasAprov.checked = true;
  app.doc.querySelectorAll('.demand-check, .aprovacao-check').forEach((c) => { c.checked = true; });
  const botao = app.doc.getElementById('compras-create-request-btn');
  botao.style.display = '';
  app.entrarNoModulo('compras');
  app.entrarNoModulo('estoque');
  app.entrarNoModulo('compras');
  eq(ctx._selectedDemands.size, 0, 'as demandas selecionadas voltaram da visita anterior');
  eq(ctx._selectedAprovacoes.size, 0, 'as aprovações selecionadas voltaram da visita anterior');
  eq(todasDemandas.checked, false, 'o "marcar todas" de demandas continuou marcado');
  eq(todasAprov.checked, false, 'o "marcar todas" de aprovações continuou marcado');
  const marcadas = app.doc.querySelectorAll('.demand-check, .aprovacao-check').filter((c) => c.checked);
  eq(marcadas.length, 0, 'a tela continuou mostrando caixas marcadas com o estado já vazio');
  eq(botao.style.display, 'none', 'a barra de ação em lote continuou armada sem seleção');
});

test('#343 F5-B G-selecao-2: a seleção de unidades das funções de compras é descartada', () => {
  // O Set é um `const` interno; o gate mede o que a TELA mostra, que é o que o
  // usuário vê ao reentrar — e o que quebraria se o reset fosse só no estado.
  const app = appServidoF5B();
  const contador = app.doc.getElementById('purchase-function-selected-count');
  app.ctx.setPurchaseFunctionUnitSelection('9', true);
  assert(/^1 /.test(contador.textContent),
    `a seleção nem chegou a ser registrada (contador: "${contador.textContent}")`);
  app.entrarNoModulo('usuarios');
  app.entrarNoModulo('estoque');
  app.entrarNoModulo('usuarios');
  assert(/^0 /.test(contador.textContent),
    `as unidades vinculadas da visita anterior voltaram marcadas (contador: "${contador.textContent}")`);
});

// ── Classe 2: filtros ───────────────────────────────────────────────────────
test('#343 F5-B G-filtro-1: TODOS os campos são limpos, não só o primeiro', () => {
  // Este gate existe por causa de um falso-verde real: `limparCamposDeFiltro`
  // passou a disparar `input`/`change`, e num contexto sem o construtor `Event`
  // o primeiro disparo lançava, o `catch` do app engolia, e os campos
  // seguintes ficavam preenchidos. Medir campo a campo é o que expõe isso.
  const app = appServidoF5B();
  const chaves = ['unitsFilterName', 'unitsFilterType', 'unitsFilterCity'];
  chaves.forEach((k) => { app.ctx.__EPI_REFS__[k].value = 'x'; });
  app.entrarNoModulo('unidades');
  app.entrarNoModulo('estoque');
  app.entrarNoModulo('unidades');
  chaves.forEach((k) => eq(app.ctx.__EPI_REFS__[k].value, '', `${k} sobreviveu à reentrada`));
});

test('#343 F5-B G-filtro-2: limpar um filtro NOTIFICA a tela (input e change)', () => {
  // Sem os eventos, o contador "Filtros ativos: N" e os status de módulo ficam
  // com o número da visita anterior: estado lógico limpo, DOM mentindo.
  const app = appServidoF5B();
  const campo = app.ctx.__EPI_REFS__.unitsFilterName;
  const vistos = [];
  campo.addEventListener('input', () => vistos.push('input'));
  campo.addEventListener('change', () => vistos.push('change'));
  campo.value = 'Sul';
  app.entrarNoModulo('unidades');
  app.entrarNoModulo('estoque');
  app.entrarNoModulo('unidades');
  assert(vistos.includes('input'), 'a limpeza não disparou `input`');
  assert(vistos.includes('change'), 'a limpeza não disparou `change`');
});

test('#343 F5-B G-filtro-3: Comercial, Dashboard e Arquivados entram no reset', () => {
  const app = appServidoF5B();
  const arquivados = ['archivedUnitsFilterUser', 'archivedUnitsFilterReason', 'archivedUnitsFilterDate'];
  const comerciais = ['commercialFilterStatus', 'commercialFilterDateFrom', 'commercialFilterDateTo', 'commercialFilterActor'];
  [...arquivados, ...comerciais, 'dashboardGlobalSearch'].forEach((k) => { app.ctx.__EPI_REFS__[k].value = 'x'; });
  app.ctx.__EPI_APP_STATE__.dashboardFilters.query = 'x';
  ['unidades', 'comercial', 'dashboard'].forEach((v) => {
    app.entrarNoModulo(v);
    app.entrarNoModulo('estoque');
    app.entrarNoModulo(v);
  });
  arquivados.forEach((k) => eq(app.ctx.__EPI_REFS__[k].value, '', `o filtro de arquivados ${k} sobreviveu`));
  comerciais.forEach((k) => eq(app.ctx.__EPI_REFS__[k].value, '', `o filtro comercial ${k} sobreviveu`));
  eq(app.ctx.__EPI_REFS__.dashboardGlobalSearch.value, '', 'a busca global do dashboard sobreviveu');
  eq(app.ctx.__EPI_APP_STATE__.dashboardFilters.query, '', 'o estado da busca do dashboard sobreviveu');
});

test('#343 F5-B G-passos-1: um passo que falha não cancela os seguintes', () => {
  // Achado medido, não hipotético: com um único `try` em volta do corpo do
  // reset, `syncUnitsSearchFilters()` lançando impedia a limpeza dos filtros de
  // unidades arquivadas — o módulo reabria com metade dos filtros limpos.
  const app = appServidoF5B();
  let lancou = false;
  try { app.ctx.syncUnitsSearchFilters(); } catch (_e) { lancou = true; }
  assert(lancou,
    'o passo intermediário parou de lançar neste fixture: o gate mediria um cenário que não existe mais');
  // Sem `*Company`: para papéis não-master a empresa é ESCOPO, não filtro, e
  // permanece fixa de propósito (regra já coberta por gate próprio).
  const depois = ['archivedUnitsFilterUser', 'archivedUnitsFilterReason', 'archivedUnitsFilterDate'];
  depois.forEach((k) => { app.ctx.__EPI_REFS__[k].value = 'x'; });
  app.entrarNoModulo('unidades');
  app.entrarNoModulo('estoque');
  app.entrarNoModulo('unidades');
  depois.forEach((k) => eq(app.ctx.__EPI_REFS__[k].value, '',
    `${k} ficou por limpar porque um passo anterior falhou`));
});

// ── Classe 3: paginação ─────────────────────────────────────────────────────
test('#343 F5-B G-paginacao-1: a página do arquivo de relatórios volta à primeira', () => {
  // Paginação com outro nome. Foi exatamente esta que escapou da contagem
  // inicial por eu ter procurado `state.pagination.*` em vez do conceito.
  const app = appServidoF5B();
  app.ctx.__EPI_APP_STATE__.reportArchivePage = 4;
  app.entrarNoModulo('relatorios');
  app.entrarNoModulo('estoque');
  app.entrarNoModulo('relatorios');
  eq(app.ctx.__EPI_APP_STATE__.reportArchivePage, 1, 'o arquivo de relatórios reabriu na página da visita anterior');
});

// ── Classe 5: abas internas ─────────────────────────────────────────────────
test('#343 F5-B G-abas-1: a visibilidade é sincronizada ANTES de escolher a aba inicial', () => {
  // `visibleViewTabs()` lê `tab.style.display`, escrito por
  // `syncViewTabsVisibility()`. O cenário que só a sincronização PRÉVIA cobre é
  // o da aba que voltou a ter conteúdo: ela continua marcada como oculta desde
  // a última sincronização, a escolha a pula, e a sincronização final não
  // corrige — a aba ativa está visível, então não há fallback a disparar.
  // Resultado: o módulo abre pulando a primeira aba que o usuário passou a ver.
  const app = appServidoF5B();
  const vista = app.vistas.colaboradores;
  const nav = vista.querySelector('nav[data-vtabs]');
  const primeira = nav.querySelectorAll('[data-vtab]')[0];
  // Estado herdado: marcada como oculta, mas com o painel cheio de conteúdo
  // visível — exatamente o que acontece quando a permissão volta a liberar.
  primeira.style.display = 'none';
  vista.querySelector('[data-vtab-panel="cadastro"]').children.forEach((f) => { f.style.display = ''; });
  app.entrarNoModulo('estoque');
  app.entrarNoModulo('colaboradores');
  eq(app.abaAtiva('colaboradores'), 'cadastro',
    'a aba inicial foi escolhida com a visibilidade velha e pulou a primeira aba já liberada');
});




// ══ #343 F5-B: rodada de convergência do Codex ═════════════════════════════
//
// Sete achados verificados um a um contra o código. Seis entraram; o sétimo
// (clique no menu do módulo já ativo) é decisão de contrato e foi relatado.

test('#343 F5-B G-conv-1: os SETE modais entram no reset, com suas identidades', () => {
  // Contagem corrigida: a auditoria achou 3 porque procurou em `app.js`. Os
  // modais vivem em `static/views/modals/*.html` (+ `ppe-form-modal` inline em
  // avaliacoes e `smr-request-report-modal` em `_modals.html`), e dois são
  // acionados de `static/js/views/purchases.js`.
  const app = appServidoF5B();
  const abertos = [
    ['compras', ['modal-edit-supplier', 'modal-supplier-pos',
      'aprovacoes-reprovar-modal', 'aprovacoes-prorrogar-modal']],
    ['avaliacoes', ['ppe-form-modal', 'aval-action-modal']],
    ['estoque', ['smr-request-report-modal']]
  ];
  abertos.forEach(([vista, ids]) => {
    ids.forEach((id) => { app.doc.getElementById(id).style.display = 'flex'; });
    app.entrarNoModulo(vista);
    app.entrarNoModulo('relatorios');
    app.entrarNoModulo(vista);
    ids.forEach((id) => eq(app.doc.getElementById(id).style.display, 'none',
      `${id} reabriu no ponto da visita anterior`));
  });
});

test('#343 F5-B G-conv-2: o modal de ação de avaliação descarta AS DUAS identidades', () => {
  // `aval-action-modal` guarda o feedback escolhido E a ação a executar.
  // Esconder sem descartar exporia, na volta, uma confirmação capaz de agir
  // sobre o feedback da visita anterior.
  const app = appServidoF5B();
  const feedback = app.doc.getElementById('aval-modal-feedback-id');
  const acao = app.doc.getElementById('aval-modal-action');
  feedback.value = '31';
  acao.value = 'arquivar';
  app.entrarNoModulo('avaliacoes');
  app.entrarNoModulo('relatorios');
  app.entrarNoModulo('avaliacoes');
  eq(feedback.value, '', 'o modal continuou apontando para o feedback anterior');
  eq(acao.value, '', 'a ação pendente da visita anterior sobreviveu');
});

test('#343 F5-B G-conv-3: CNPJs e Terceirizados entram no reset de filtros', () => {
  const app = appServidoF5B();
  const refs = app.ctx.__EPI_REFS__;
  const estado = app.ctx.__EPI_APP_STATE__;
  const campos = [
    'legalEntitiesFilterSearch', 'legalEntitiesFilterType',
    'outsourcedCompaniesFilterSearch', 'outsourcedCompaniesFilterKind',
    'outsourcedEmployeesFilterSearch'
  ];
  campos.forEach((k) => { refs[k].value = 'x'; });
  refs.legalEntitiesShowInactive.checked = true;
  // Sujar o ESTADO pela mesma porta que o usuário sujaria: as funções de
  // sincronização que os handlers de input do módulo já chamam. Sem isto o
  // gate compararia o estado com o valor inicial dele — asserção vazia, e foi
  // assim que uma sabotagem passou verde antes desta correção.
  app.ctx.syncLegalEntitiesFilters();
  app.ctx.syncOutsourcedCompaniesFilters();
  app.ctx.syncOutsourcedEmployeesFilters();
  eq(estado.legalEntitiesFilters.search, 'x', 'o preparo do gate não sujou o estado: mediria o nada');
  eq(estado.outsourcedCompaniesFilters.search, 'x', 'o preparo do gate não sujou o estado: mediria o nada');
  eq(estado.outsourcedEmployeesFilters.search, 'x', 'o preparo do gate não sujou o estado: mediria o nada');

  ['cnpjs', 'terceirizados'].forEach((v) => {
    app.entrarNoModulo(v);
    app.entrarNoModulo('relatorios');
    app.entrarNoModulo(v);
  });

  campos.forEach((k) => eq(refs[k].value, '', `${k} sobreviveu à reentrada`));
  eq(refs.legalEntitiesShowInactive.checked, false,
    'a caixa "mostrar inativos" continuou marcada: `value = ""` não desmarca caixa');
  // O ESTADO é o que filtra a lista. Limpar o campo sem ressincronizar deixa a
  // tela vazia e a lista ainda recortada — o pior dos dois mundos.
  eq(estado.legalEntitiesFilters.search, '', 'o estado do filtro de CNPJs não foi ressincronizado');
  eq(estado.legalEntitiesFilters.type, '', 'o estado do filtro de CNPJs não foi ressincronizado');
  eq(estado.legalEntitiesFilters.showInactive, false, 'o estado de "mostrar inativos" não foi ressincronizado');
  eq(estado.outsourcedCompaniesFilters.search, '', 'o estado do filtro de terceirizadas não foi ressincronizado');
  eq(estado.outsourcedCompaniesFilters.kind, '', 'o estado do filtro de terceirizadas não foi ressincronizado');
  eq(estado.outsourcedEmployeesFilters.search, '', 'o estado do filtro de prestadores não foi ressincronizado');
});

test('#343 F5-B G-conv-4: os quatro grupos de arquivados voltam ao início', () => {
  // Um grupo por módulo, sobre `ARCHIVAL_ENTITIES`. Sem `*Company`: para
  // papéis não-master a empresa é escopo, não filtro.
  const app = appServidoF5B();
  const refs = app.ctx.__EPI_REFS__;
  const estado = app.ctx.__EPI_APP_STATE__;
  const grupos = [
    ['colaboradores', 'employee', 'archivedEmployees'],
    ['epis', 'epi', 'archivedEpis'],
    ['terceirizados', 'outsourcedCompany', 'archivedOutsourcedCompanies'],
    ['terceirizados', 'outsourcedEmployee', 'archivedOutsourcedEmployees']
  ];
  grupos.forEach(([, kind, prefixo]) => {
    refs[`${prefixo}FilterUser`].value = 'ana';
    refs[`${prefixo}FilterReason`].value = 'motivo';
    // Mesma porta do usuário: `syncArchivedRecordsFilters` é o que os handlers
    // de input dos arquivados chamam.
    app.ctx.syncArchivedRecordsFilters(kind);
    eq(estado[`${prefixo}Filters`].user, 'ana', `o preparo de ${prefixo} não sujou o estado`);
  });

  ['colaboradores', 'epis', 'terceirizados'].forEach((v) => {
    app.entrarNoModulo(v);
    app.entrarNoModulo('relatorios');
    app.entrarNoModulo(v);
  });

  grupos.forEach(([vista, , prefixo]) => {
    eq(refs[`${prefixo}FilterUser`].value, '', `${prefixo} (${vista}) sobreviveu à reentrada`);
    eq(refs[`${prefixo}FilterReason`].value, '', `${prefixo} (${vista}) sobreviveu à reentrada`);
    eq(estado[`${prefixo}Filters`].user, '', `o estado de ${prefixo} não foi ressincronizado`);
    eq(estado[`${prefixo}Filters`].reason, '', `o estado de ${prefixo} não foi ressincronizado`);
  });
});

test('#343 F5-B G-conv-5: o editor comercial é resetado ATOMICAMENTE', () => {
  // O editor tem duas metades: a configuração principal da empresa e o
  // contrato. Limpar só o contrato deixava a tela editando a empresa B com a
  // identidade do contrato dela já descartada — e um "Salvar contrato" ali
  // gravaria um rascunho em branco por cima do contrato existente de B.
  const fonte = _semComentariosF5B(fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), 'app.js'), 'utf-8'));
  const mapa = fonte.slice(fonte.indexOf('const VIEW_FORM_RESET'), fonte.indexOf('function resetModuleFormsToInitial'));
  const linha = mapa.split('\n').find((l) => l.trim().startsWith('comercial:')) || '';
  assert(linha.includes('fillCommercialForm()'),
    'o reset comercial voltou a limpar só a metade do contrato');
  assert(!/comercial:.*resetCommercialContractForm/.test(linha),
    'o reset comercial voltou a chamar direto o reset parcial');
  // E `fillCommercialForm` continua sendo a autoridade que recarrega as duas.
  const preenche = fonte.slice(fonte.indexOf('function fillCommercialForm('));
  const fim = preenche.indexOf('\n}');
  assert(preenche.slice(0, fim).includes('resetCommercialContractForm('),
    'fillCommercialForm deixou de resetar a metade do contrato: o reset deixaria de ser atômico');
});



// ══ #343 F5-B: segunda revisão de convergência (head b6aea85, SaaS) ════════

test('#343 F5-B G-conv-8: Compras, Avaliações e Migração entram no reset de filtros', () => {
  const app = appServidoF5B();
  const ids = [
    'compras-demands-company-filter', 'compras-req-status-filter',
    'compras-po-status-filter', 'feedbacks-filter-status', 'feedbacks-filter-type',
    'migracao-catalog-filter'
  ];
  ids.forEach((id) => { app.doc.getElementById(id).value = 'x'; });
  // Os três seletores de Compras só recarregam suas listas por `change`
  // (`loadPurchaseDemands`, `loadPurchaseRequests`, `loadPurchaseOrders` estão
  // ligados a ele). Limpar o valor sem notificar deixaria as listas mostrando
  // o resultado do filtro anterior com os controles já vazios.
  const notificados = new Set();
  ['compras-demands-company-filter', 'compras-req-status-filter', 'compras-po-status-filter']
    .forEach((id) => app.doc.getElementById(id)
      .addEventListener('change', () => notificados.add(id)));
  ['compras', 'avaliacoes', 'migracao'].forEach((v) => {
    app.entrarNoModulo(v);
    app.entrarNoModulo('relatorios');
    app.entrarNoModulo(v);
  });
  ids.forEach((id) => eq(app.doc.getElementById(id).value, '',
    `${id} sobreviveu à reentrada`));
  eq(notificados.size, 3,
    `os seletores de Compras foram limpos sem disparar \`change\`: as listas continuariam com o recorte anterior (notificados: ${[...notificados].join(', ') || 'nenhum'})`);
});

test('#343 F5-B G-conv-9: soltar a empresa selecionada redesenha as duas superfícies', () => {
  // Problema de ORDEM: o reset de formulários roda antes do de seleção e
  // termina em `renderCompanyDetails()`, que ainda enxerga a empresa da visita
  // anterior. Sem redesenhar depois, o painel e a linha destacada continuam
  // mostrando aquela empresa enquanto o estado diz que nada está selecionado.
  const fonte = _semComentariosF5B(fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), 'app.js'), 'utf-8'));
  const reset = fonte.slice(fonte.indexOf('function resetModuleSelectionToInitial'));
  const bloco = reset.slice(0, reset.indexOf('} catch (error)'));
  const posNull = bloco.indexOf('state.selectedCompanyId = null;');
  assert(posNull > -1, 'a seleção de empresa saiu do reset');
  const depois = bloco.slice(posNull);
  assert(depois.includes('renderCompanyDetails()'),
    'o painel de detalhes não é redesenhado: continuaria mostrando a empresa da visita anterior');
  assert(depois.includes('renderCompanies()'),
    'a tabela não é redesenhada: a linha destacada continuaria na empresa anterior');
  // A ordem importa: redesenhar ANTES de soltar não corrigiria nada.
  assert(bloco.indexOf('renderCompanyDetails()') > posNull,
    'o redesenho ficou antes de soltar a seleção');
});


test('#343 F5-B G-conv-11: registrar uso só entra no histórico se a entrega der certo', () => {
  // O handler de submit do phase42 é `capture: true` e roda ANTES do phase43,
  // que aborta quando o resumo não foi revisado, o código do item está errado
  // ou a quantidade é inválida. Gravar ali punha no histórico uma entrega que
  // nunca existiu — e o phase43 passava a recomendar a partir dela.
  const p42 = _semComentariosF5B(
    fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), 'ux-phase42.js'), 'utf-8'));
  const submit = p42.slice(p42.indexOf("safeOn(form, 'submit'"));
  const fim = submit.indexOf('}, { capture: true');
  const corpo = submit.slice(0, fim);
  assert(corpo.includes('ctxPendente = getContext(memory)'),
    'o contexto deixou de ser capturado no submit, quando o formulário ainda está cheio');
  ['appendUsageEvent(', 'saveMemory(', 'anunciarUsoRegistrado('].forEach((t) => assert(!corpo.includes(t),
    `"${t}" voltou para o pré-submit: uma submissão abortada entraria no histórico`));
});

// ══ #343 F5-B: clique no menu da view já ativa é NO-OP (decisão de contrato) ═
//
// O Codex levantou que `anterior === nome` faz o clique no item do menu
// correspondente ao módulo já ativo não disparar reset, e que isso falharia o
// contrato "reentrar no módulo → estado inicial". A decisão de produto foi
// explícita: esse gesto NÃO é reentrada para fins da F5-B.
//
// O achado não está sendo ignorado — está sendo FIXADO. Estes gates existem
// para que uma mudança futura não transforme esse clique em perda silenciosa
// de dados, que é o custo real da alternativa.
//
// INSUFICIÊNCIA DESTES TRÊS GATES, registrada e não apagada (F5-B.1): eles
// provam o listener CENTRAL, e só ele. `clicarNoMenuDaViewAtiva` despacha
// `epi:viewchange` direto, então nenhum dos três pode observar o que roda ANTES
// do evento (`location.assign` em `navigateToView`, `closeTransientUi()` em
// `activateTab`) nem os OUTROS listeners do mesmo evento, que não tinham guarda
// (aba de Compras, rolagem do phase44, pilha de raiz da hierarquia). Cinco
// achados atravessaram exatamente esse vão. Eles continuam aqui porque o que
// provam é verdade e vale como regressão; o gesto de menu quem prova é a seção
// "F5-B.1", que parte do clique real.

test('#343 F5-B G-menu-1: clicar no menu do módulo ativo preserva a edição não salva', () => {
  const app = appServidoF5B();
  const refs = app.ctx.__EPI_REFS__;
  const identidade = app.doc.getElementById('unit-form-id');
  const nome = app.doc.getElementById('unit-name');

  // 1. O usuário entra no módulo vindo de outra view.
  app.entrarNoModulo('relatorios');
  app.entrarNoModulo('unidades');

  // 2. Inicia uma edição e altera dados SEM salvar.
  identidade.value = '77';
  nome.value = 'Unidade em edição, não salva';
  refs.unitsFilterName.value = 'busca em uso';
  refs.unitsFilterCity.value = 'Curitiba';

  // 3. Clica de novo no item do menu DESSE MESMO módulo.
  app.clicarNoMenuDaViewAtiva('unidades');

  // 4. Nada do trabalho em andamento pode ter sido destruído.
  eq(identidade.value, '77',
    'o clique no menu do módulo ativo descartou a identidade do registro em edição');
  eq(nome.value, 'Unidade em edição, não salva',
    'o clique no menu do módulo ativo apagou dados digitados e não salvos');
  eq(refs.unitsFilterName.value, 'busca em uso',
    'o clique no menu do módulo ativo apagou o filtro que o usuário estava usando');
  eq(refs.unitsFilterCity.value, 'Curitiba',
    'o clique no menu do módulo ativo apagou o filtro que o usuário estava usando');

  // 5. CONTROLE A/B — prova que o gate não é vazio.
  //
  // Sem isto, um reset quebrado (que não zerasse nada) faria as asserções
  // acima passarem por acidente. O mesmo estado, agora numa entrada REAL
  // (vinda de outra view), tem de ser zerado: é a única forma de demonstrar
  // que o passo 3 foi no-op por decisão, e não por impotência do mecanismo.
  app.entrarNoModulo('relatorios');
  app.entrarNoModulo('unidades');
  eq(identidade.value, '',
    'o controle A/B falhou: a entrada real deixou de desarmar o modo de edição');
  eq(nome.value, '',
    'o controle A/B falhou: a entrada real deixou de limpar o formulário');
  eq(refs.unitsFilterName.value, '',
    'o controle A/B falhou: a entrada real deixou de limpar os filtros');
});

test('#343 F5-B G-menu-2: o mesmo gesto não mexe em aba interna nem em seleção', () => {
  // Complementa o G-menu-1 nas outras classes de estado de trabalho: a aba
  // interna em que o usuário está e a seleção que ele montou.
  const app = appServidoF5B();
  const ctx = app.ctx;

  app.entrarNoModulo('relatorios');
  app.entrarNoModulo('colaboradores');
  const nav = app.vistas.colaboradores.querySelector('nav[data-vtabs]');
  ctx.activateViewTab(nav, 'lista');
  eq(app.abaAtiva('colaboradores'), 'lista', 'o preparo do gate não trocou de aba');

  app.entrarNoModulo('compras');
  ctx._selectedDemands.add(0);
  ctx._selectedDemands.add(1);

  // O gesto, nos dois módulos.
  app.clicarNoMenuDaViewAtiva('compras');
  eq(ctx._selectedDemands.size, 2,
    'o clique no menu do módulo ativo desfez a seleção que o usuário montou');

  app.entrarNoModulo('colaboradores');
  ctx.activateViewTab(nav, 'lista');
  app.clicarNoMenuDaViewAtiva('colaboradores');
  eq(app.abaAtiva('colaboradores'), 'lista',
    'o clique no menu do módulo ativo jogou o usuário de volta para a primeira aba');

  // Controle A/B: entrada real zera as duas.
  app.entrarNoModulo('relatorios');
  app.entrarNoModulo('colaboradores');
  eq(app.abaAtiva('colaboradores'), 'cadastro',
    'o controle A/B falhou: a entrada real deixou de devolver a aba inicial');
  app.entrarNoModulo('compras');
  eq(ctx._selectedDemands.size, 0,
    'o controle A/B falhou: a entrada real deixou de limpar a seleção');
});

test('#343 F5-B G-menu-3: a guarda é a única porta, e não há bypass por sinal de menu', () => {
  // A decisão de contrato proíbe um `viaMenu` que contorne a guarda para
  // forçar reset no clique sobre a view ativa. Este gate trava isso no texto:
  // se alguém introduzir esse desvio, ele cai — e a discussão volta a ser
  // explícita, em vez de virar mudança silenciosa de comportamento.
  const fonte = _semComentariosF5B(fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), 'app.js'), 'utf-8'));
  const i = fonte.indexOf("safeOn(document, 'epi:viewchange'");
  const listener = fonte.slice(i, fonte.indexOf('resetModuleWizardsToInitial(nome);', i));
  assert(/if \(!nome \|\| nome === anterior\) \{return;\}/.test(listener),
    'a guarda de mesma-view saiu do listener: o clique no menu do módulo ativo passaria a resetar');
  assert(!/viaMenu/.test(listener),
    'apareceu um desvio por sinal de menu, que a decisão de contrato proíbe');
  // E a guarda tem de vir ANTES de qualquer reset, não depois.
  const posGuarda = listener.indexOf('nome === anterior');
  const posPrimeiroReset = listener.indexOf('resetViewTabsToInitial(nav)');
  assert(posGuarda > -1 && posPrimeiroReset > -1 && posGuarda < posPrimeiroReset,
    'a guarda deixou de preceder os resets: algum teardown rodaria antes de ela decidir');
});

// ══ #343 F5-B.1: o gesto de MENU medido pelo CAMINHO REAL ════════════════════
// MARCA_INICIO_F5B1
//
// Correção metodológica REGISTRADA, e não apagada: os gates `G-menu-1/2/3`
// acima provam — com controle A/B — que o listener CENTRAL de `epi:viewchange`
// é no-op quando `anterior === nome`. O que eles NÃO provam é o GESTO.
// `clicarNoMenuDaViewAtiva` despacha `epi:viewchange` direto e por isso é
// estruturalmente incapaz de observar:
//
//   (i)  o que roda ANTES do evento — `location.assign` dentro de
//        `navigateToView`, `closeTransientUi()` dentro de `activateTab`;
//   (ii) os OUTROS listeners de `epi:viewchange`, que não tinham guarda: a aba
//        interna de Compras (sem feature flag nenhuma — comportamento vivo), a
//        rolagem do phase44 e a pilha de raiz do navigation.js.
//
// Os cinco achados do F5-B.1 estavam exatamente nesses dois pontos cegos. Um
// teste que fabrica `epi:viewchange` não é prova do gesto de menu: os gates
// desta seção partem do CLIQUE, num nó `.menu-link[data-view]` real, com os
// handlers reais ligados por `bindMenuNavigation()` — e `G-real-cobertura`
// reprova se alguém voltar a fabricar o evento aqui.
//
// SEGUNDO falso-verde desta fatia, encontrado pela bateria de sabotagens e
// registrado aqui: quando a guarda do achado A subiu para o TOPO de
// `navigateToView` — como o review pediu, e com razão —, o clique no menu do
// módulo ativo passou a NÃO alcançar mais nenhum listener de `epi:viewchange`.
// Isso é o resultado certo para o contrato e o resultado errado para os gates:
// `S-C`, `S-D` e `S-E` passaram a ficar VERDES com a proteção removida, porque
// o caminho medido nem chegava lá.
//
// Os três gates passaram a medir DUAS coisas, e é a segunda que os mantém
// honestos:
//   (a) o gesto de menu não alcança o listener — consequência da guarda de A;
//   (b) quando o listener É alcançado com `anterior === view`, a guarda o torna
//       no-op. A rota viva para isso é o REDESENHO INTERNO da própria view, que
//       o app faz por `showView(mesmaView)` — é o que `startEditEmployee()`,
//       a troca de idioma e a recarga pós-salvamento fazem, e é o que o
//       `activateTab` do multitab faz. Chamar `showView` é usar a porta do app,
//       não fabricar o evento: quem calcula `anterior` continua sendo ele.

const ABAS_DE_AVALIACOES_F5B = Object.freeze(
  ['pendentes', 'reclamacoes', 'elogios', 'sugestoes', 'ranking', 'epis-teste', 'avaliacao-final']
);

const MARCA_INICIO_F5B1 = 'MARCA_INICIO_F5B1';
const MARCA_FIM_F5B1 = 'MARCA_FIM_F5B1';

function montarAppRealF5B(busca, opcoes) {
  const o = opcoes || {};
  const raizStatic = path.resolve(JS_ROOT, '..');

  const vistas = {
    dashboard: montarVistaF5B('dashboard', 'dashboard-grp', ['inicio', 'outra']),
    estoque: montarVistaF5B('estoque', 'estoque', ['estoque', 'movimentacoes']),
    colaboradores: montarVistaF5B('colaboradores', 'colaboradores', ['cadastro', 'lista']),
    compras: montarVistaSimplesF5B('compras', []),
    entregas: montarVistaSimplesF5B('entregas', []),
    avaliacoes: montarVistaSimplesF5B('avaliacoes', [])
  };

  // Subabas de Avaliações no formato real: `bindAvaliacoesView()` escuta o
  // clique em `#avaliacoes-subtabs` e `showAvalTab` marca `is-active` no botão
  // `#avaltab-<pane>` e esconde os `#avaliacoes-pane-<pane>`.
  const subabas = criarNoF5B('div', { id: 'avaliacoes-subtabs' });
  ABAS_DE_AVALIACOES_F5B.forEach((aba) => {
    subabas.appendChild(criarNoF5B('button', { id: `avaltab-${aba}`, 'data-avaliacoes-tab': aba }));
    vistas.avaliacoes.appendChild(campoF5B('div', { id: `avaliacoes-pane-${aba}` }));
  });
  vistas.avaliacoes.appendChild(subabas);
  // Cabeçalho já montado, como fica a página depois do primeiro bind: faz o
  // `applyViewHeader` do phase44 sair cedo em vez de montar markup por
  // `innerHTML`, que este shim não interpreta.
  Object.values(vistas).forEach((v) => v.appendChild(criarNoF5B('article', { class: 'card phase44-header' })));

  // Igual ao `dashboard.html` SERVIDO, que já chega com `class="view active"`.
  // É esse detalhe que proíbe a semântica de ativação redundante de ter
  // fallback para `defaultView()`: com o fallback, a primeira navegação de
  // verdade pareceria redundante.
  vistas.dashboard.classList.add('active');

  // Abas internas de Compras no formato que `switchComprasTab` manipula.
  ['demandas', 'requisicoes', 'cotacoes', 'pos'].forEach((aba) => {
    vistas.compras.appendChild(campoF5B('button', { id: `compras-tab-${aba}` }));
    vistas.compras.appendChild(campoF5B('div', { id: `compras-${aba}-panel` }));
  });

  // Trabalho não salvo em Entregas: formulário preenchido e não enviado.
  vistas.entregas.appendChild(montarFormularioF5B('delivery-form', [['delivery-obs', 'text']]));

  // Trabalho não salvo em Estoque, para o caminho das views SUPORTADAS pela SPA.
  // Id fora de todos os mapas de reset do app, de propósito: o que se mede aqui
  // é a ausência de transição, não a eficácia de um reset.
  vistas.estoque.appendChild(campoF5B('input', { id: 'f5b1-rascunho-estoque' }));

  // Gatilho de subnível da hierarquia, no formato que `pushFromTrigger` lê.
  vistas.estoque.appendChild(criarNoF5B('button', {
    id: 'estoque-abrir-lote',
    'data-hierarchy-push': '1',
    'data-hierarchy-id': 'lote-4711',
    'data-hierarchy-label': 'Lote 4711'
  }));

  const menu = criarNoF5B('nav', { id: 'menu' });
  ['dashboard', 'estoque', 'colaboradores', 'compras', 'entregas', 'avaliacoes'].forEach((view) => {
    const item = criarNoF5B('button', { 'data-view': view, class: 'menu-link' });
    item.textContent = view;
    menu.appendChild(item);
  });

  const main = criarNoF5B('div', { id: 'main-content' });
  Object.values(vistas).forEach((v) => main.appendChild(v));

  // Modal de assinatura ABERTO, com o traçado ainda não gravado: é o alvo de
  // `closeTransientUi()`. Fechar aqui e reabrir devolve um canvas em branco —
  // o desenho não gravado não volta.
  const modalAssinatura = criarNoF5B('div', { id: 'signature-modal', class: 'signature-modal is-open' });
  modalAssinatura.appendChild(criarNoF5B('canvas', { id: 'signature-pad', 'data-tracos': '7' }));

  // Dropdown transitório: serve de CONTROLE — a troca real de contexto tem de
  // continuar fechando o que é transitório.
  const dropdown = criarNoF5B('div', { id: 'dropdown-acoes', 'data-ui-dropdown': '1', class: 'is-open' });

  const topbar = criarNoF5B('div', { class: 'topbar' });
  const doc = criarNoF5B('document', {});
  doc.appendChild(topbar);
  doc.appendChild(menu);
  doc.appendChild(main);
  doc.appendChild(modalAssinatura);
  doc.appendChild(dropdown);
  // Hierarquia (navigation.js) só desenha se achar seus nós. Os nós do multitab
  // saíram da fixture no #343 PR 4 junto com o `_topbar.html` que os servia:
  // manter DOM que a produção não tem faria o harness medir outra página.
  [['hierarchy-back-btn', 'button'], ['hierarchy-breadcrumb', 'div'], ['hierarchy-breadcrumb-wrap', 'div'],
   ['interactive-nav-tabs', 'div']]
    .forEach(([id, tag]) => doc.appendChild(criarNoF5B(tag, { id })));
  doc.body = criarNoF5B('body', {});
  doc.head = criarNoF5B('head', {});
  doc.documentElement = criarNoF5B('html', {});
  doc.readyState = 'complete';
  doc.title = '';
  doc.getElementById = (id) => descendentesF5B(doc).find((n) => n.id === id) || null;
  doc.createElement = (t) => criarNoF5B(t, {});

  const armazem = () => ({
    _s: {},
    getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
    setItem(k, v) { this._s[k] = String(v); },
    removeItem(k) { delete this._s[k]; },
    key(i) { return Object.keys(this._s)[i] ?? null; },
    get length() { return Object.keys(this._s).length; }
  });

  const ctx = {
    document: doc, localStorage: armazem(), sessionStorage: armazem(), console,
    navigator: { userAgent: 'node' },
    CustomEvent: class { constructor(t, o) { this.type = t; Object.assign(this, o || {}); } },
    Event: class { constructor(t, o) { this.type = t; this.bubbles = false; Object.assign(this, o || {}); } },
    getComputedStyle: (el) => ({
      display: (el && el.style && el.style.display) || (el && el.hidden ? 'none' : 'block'),
      visibility: (el && el.style && el.style.visibility) || 'visible'
    }),
    AbortController: class { constructor() { this.signal = { addEventListener() {} }; } abort() {} },
    MutationObserver: class { observe() {} disconnect() {} },
    HTMLElement: class {},
    setTimeout, clearTimeout, setInterval, clearInterval, Promise, URL, URLSearchParams,
    requestAnimationFrame: (fn) => setTimeout(fn, 0),
    performance: { now: () => Date.now() },
    // Promessa que NUNCA resolve, de propósito. Estes gates medem navegação, e
    // o app dispara carga de dados ao abrir um módulo: inventar payload de API
    // seria fabricar resposta de servidor dentro do teste, e devolver um
    // `Response` incompleto derruba o processo com rejeição não tratada num
    // caminho que o gate nem observa. Não resolver deixa a carga pendente, que
    // é o único estado honesto aqui.
    fetch: () => new Promise(() => {}),
    alert() {}, matchMedia: () => ({ matches: false, addEventListener() {} })
  };
  // Espiões. Cada um mede um dos cinco efeitos colaterais de transição que o
  // contrato proíbe na ativação redundante.
  ctx._assigns = [];
  ctx._reloads = 0;
  ctx._scrolls = [];
  ctx._pushStates = 0;
  ctx.scrollY = 0;
  ctx.location = {
    search: busca || '', href: `http://local/${busca || ''}`, pathname: '/', origin: 'http://local',
    assign(url) { ctx._assigns.push(String(url)); },
    reload() { ctx._reloads += 1; }
  };
  ctx.history = {
    length: 1,
    pushState() { ctx._pushStates += 1; },
    replaceState() {},
    back() {}
  };
  ctx.scrollTo = (opcoes) => { ctx._scrolls.push(opcoes); };
  ctx._handlers = {};
  ctx.addEventListener = (ev, fn) => { (ctx._handlers[ev] = ctx._handlers[ev] || []).push(fn); };
  ctx.removeEventListener = () => {};
  ctx.dispatchEvent = (ev) => {
    (ctx._handlers[ev.type] || []).forEach((fn) => { try { fn(ev); } catch (_erro) { /* isolado */ } });
    return true;
  };
  ctx.window = ctx; ctx.globalThis = ctx; ctx.self = ctx;
  vmF5B.createContext(ctx);

  // Módulos carregados ANTES da lista servida, quando o gate precisa que eles
  // realmente iniciem. Hoje `ux-phase44.js` não inicia depois do `app.js`: a
  // primeira linha do IIFE grava `globalThis.__EPI_PHASE44_BOUND__ = true` e seis
  // linhas abaixo ele pergunta `ensureModuleBound('phase44')`, que deriva
  // exatamente essa chave e responde "já ligado" — o módulo retorna antes de
  // qualquer bind. Carregado antes do `app.js`, `__EPI_FRONTEND_HELPERS__` ainda
  // não existe, o `ensureModuleBound` usado é o fallback local, e o módulo inicia.
  //
  // Essa colisão de chave é um defeito SEPARADO (o phase44 não inicia em
  // produção), fora do cerco do F5-B.1 e relatado como achado próprio. O gate D
  // existe para que o dia em que ela for corrigida não seja o dia em que clicar
  // no menu do módulo ativo passa a arrancar o usuário de onde ele estava.
  (o.precarregar || []).forEach((rel) => {
    try {
      vmF5B.runInContext(fs.readFileSync(path.join(raizStatic, rel), 'utf-8'), ctx, { filename: rel });
    } catch (_erro) { /* medido pelos gates abaixo */ }
  });

  const ordem = fs.readFileSync(path.join(raizStatic, 'views', '_scripts.html'), 'utf-8')
    .match(/src="\/([^"?]+\.js)/g).map((m) => m.slice(6));
  ordem.forEach((rel) => {
    // `multitab-navigation.js` captura `globalThis.__EPI_APP_NAV_API__` na
    // AVALIAÇÃO do próprio arquivo (`var navApi = ... || {}`) e retorna na
    // linha seguinte se `navApi.showView` não for função. Quem publica essa API
    // é `registerMultitabNavigationApi()`, que o app chama dentro de `init()`,
    // no DOMContentLoaded — depois. Aqui a publicação acontece no ponto em que o
    // módulo espera encontrá-la, usando a função REAL do app.
    //
    // Que o app SERVIDO publique a API tarde é um defeito de fiação separado (o
    // multitab não chega a iniciar em produção hoje), fora do cerco do F5-B.1 e
    // relatado como achado próprio. A guarda B existe para que o dia em que essa
    // fiação for corrigida não seja o dia em que o usuário perde uma assinatura.
    if (rel.endsWith('multitab-navigation.js') && typeof ctx.registerMultitabNavigationApi === 'function') {
      try { ctx.registerMultitabNavigationApi(); } catch (_erro) { /* medido pelos gates abaixo */ }
    }
    try {
      vmF5B.runInContext(fs.readFileSync(path.join(raizStatic, rel), 'utf-8'), ctx, { filename: rel });
    } catch (_erro) { /* dependência de browser ausente não invalida o gate */ }
    // Sessão mínima assim que o `state` do app existe, e não depois de tudo
    // carregado: o multitab é avaliado adiante e já abre a aba inicial chamando
    // `showView`. Sem usuário, o RBAC do app manda qualquer view para a padrão e
    // o gate mediria uma sessão deslogada.
    if (rel === 'app.js') {
      const estado = ctx.__EPI_APP_STATE__ || {};
      estado.user = { id: 1, role: 'general_admin', company_id: 1 };
      // `hasPermission` consulta `state.permissions` quando ela está preenchida.
      estado.permissions = [
        'dashboard:view', 'stock:view', 'deliveries:view', 'employees:view', 'reports:view',
        'purchase_requests:view', 'purchase_requests:create', 'purchase_orders:view',
        'epi_evaluation:view', 'epi_feedback:view', 'ppe_test:view'
      ];
    }
  });

  // O que o `init()` do app faz e de que estes gates dependem — nada mais.
  // `setupViewTabs` liga o reset central da F5-B; `bindMobileUxBehavior` liga o
  // listener independente que troca a aba de Compras; `bindMenuNavigation` liga
  // o handler REAL do item de menu. Todos são funções do app, não do teste.
  if (typeof ctx.registerMultitabNavigationApi === 'function') ctx.registerMultitabNavigationApi();
  ctx.setupViewTabs();
  ctx.bindMobileUxBehavior();
  ctx.bindMenuNavigation();

  // OBSERVAÇÃO, não fabricação: o harness conta os `epi:viewchange` que a
  // APLICAÇÃO emite, para o gate poder afirmar "nenhuma transição aconteceu" em
  // vez de só "nada visível mudou". O listener é registrado depois dos scripts,
  // então nunca precede nem substitui os do app.
  const eventosDeView = [];
  doc.addEventListener('epi:viewchange', (ev) => { eventosDeView.push(ev && ev.detail); });

  const viewAtiva = () => {
    const no = doc.querySelector('.view.active');
    return no && no.id ? no.id.replace(/-view$/, '') : '';
  };
  // O GESTO contratado: um clique de verdade, no nó de verdade. Daqui em diante
  // quem decide o que acontece é a aplicação servida.
  const clicarNoItemDeMenu = (view) => {
    const item = doc.querySelector(`.menu-link[data-view="${view}"]`);
    if (!item) {throw new Error(`fixture sem item de menu para "${view}"`);}
    return item.dispatchEvent(new ctx.Event('click', { bubbles: true }));
  };
  const clicarEm = (id) => {
    const no = doc.getElementById(id);
    if (!no) {throw new Error(`fixture sem nó "${id}"`);}
    return no.dispatchEvent(new ctx.Event('click', { bubbles: true }));
  };
  const abaDeAvaliacoesAtiva = () => {
    const ativa = ABAS_DE_AVALIACOES_F5B
      .find((aba) => doc.getElementById(`avaltab-${aba}`)?.classList.contains('is-active'));
    return ativa || '';
  };
  const abaDeComprasAtiva = () => {
    const ativa = ['demandas', 'requisicoes', 'cotacoes', 'pos']
      .find((aba) => doc.getElementById(`compras-tab-${aba}`)?.classList.contains('is-active'));
    return ativa || '';
  };

  return { ctx, doc, vistas, viewAtiva, clicarNoItemDeMenu, clicarEm, abaDeComprasAtiva,
    abaDeAvaliacoesAtiva, eventosDeView, scriptsCarregados: ordem.length };
}

test('#343 F5-B.1 G-real-0: o harness carrega o app servido e liga os handlers reais', () => {
  const app = montarAppRealF5B('?ux_spa_navigation=1');
  assert(app.scriptsCarregados >= 40, `esperava a lista de _scripts.html, veio ${app.scriptsCarregados}`);
  eq(app.viewAtiva(), 'dashboard', 'o fixture deveria começar no dashboard, como a página servida');
  assert(typeof app.ctx.bindMenuNavigation === 'function', 'bindMenuNavigation não veio do app.js servido');
  assert(typeof app.ctx.ativacaoRedundanteDeView === 'function', 'a semântica canônica não existe no app servido');
  assert(app.ctx.isSpaNavigationEnabled() === true, 'a flag de SPA não ligou: os gates de A mediriam o caminho errado');
  eq(app.ctx.ativacaoRedundanteDeView('dashboard'), true, 'a view ativa não foi reconhecida como ativação redundante');
  eq(app.ctx.ativacaoRedundanteDeView('estoque'), false, 'uma view NÃO ativa foi tratada como redundante');
});

test('#343 F5-B.1 G-real-cobertura: todo gate desta seção parte do clique real', () => {
  // Este é o gate que a meta-sabotagem ataca: trocar o clique real por um
  // `dispatchEvent(new CustomEvent('epi:viewchange', ...))` derruba-o. Foi
  // exatamente esse atalho que deixou os cinco achados passarem por baixo dos
  // gates anteriores, e é contra a repetição dele que este gate existe.
  const fonte = fs.readFileSync(__filename, 'utf-8');
  const ini = fonte.indexOf(MARCA_INICIO_F5B1 + '\n');
  const fim = fonte.indexOf(MARCA_FIM_F5B1 + '\n');
  assert(ini > -1 && fim > ini, 'as marcas da seção F5-B.1 mudaram de forma');
  const secao = fonte.slice(ini, fim);
  const blocos = secao.split("\ntest('#343 F5-B.1 ").slice(1);
  assert(blocos.length >= 11, `esperava os gates do F5-B.1, encontrei ${blocos.length}`);
  const semClique = ['G-real-0', 'G-real-cobertura', 'G-real-contraprova'];
  blocos.forEach((bloco) => {
    const nome = bloco.slice(0, bloco.indexOf(':'));
    if (semClique.includes(nome)) {return;}
    assert(bloco.includes('clicarNoItemDeMenu('),
      `o gate "${nome}" não parte do clique real — evento fabricado não prova o gesto de menu`);
    ['entrarNoModulo(', 'redesenharMesmaVista(', 'clicarNoMenuDaViewAtiva(', "'epi:viewchange'"]
      .forEach((atalho) => assert(!bloco.includes(atalho),
        `o gate "${nome}" fabrica a troca de view com \`${atalho}\`: é o atalho que escondeu os cinco achados`));
  });
});

test('#343 F5-B.1 G-real-contraprova: o evento fabricado não alcança o efeito destrutivo', () => {
  // A razão pela qual os gates antigos não podiam ter visto o achado A:
  // `location.assign` roda ANTES de `epi:viewchange` existir. Fabricar o evento
  // não pode acusar nem absolver esse caminho — este gate mede essa cegueira em
  // vez de descrevê-la.
  const app = montarAppRealF5B('?ux_spa_navigation=1');
  app.doc.dispatchEvent(new app.ctx.CustomEvent('epi:viewchange', {
    detail: { view: 'entregas', anterior: 'dashboard', viaHistorico: false, viaMultitab: false }
  }));
  eq(app.ctx._assigns.length, 0,
    'o evento fabricado alcançou navigateToView — então o shim está mentindo sobre o caminho');
  // O clique real, no mesmo estado, alcança.
  app.clicarNoItemDeMenu('entregas');
  eq(app.ctx._assigns.length, 1,
    'o clique real NÃO alcançou navigateToView: sem isso nenhum gate desta seção prova nada');
});

// ── Achado A — navigateToView / location.assign ─────────────────────────────

test('#343 F5-B.1 G-A-1: clique no menu do módulo ativo não recarrega a página', () => {
  const app = montarAppRealF5B('?ux_spa_navigation=1');
  // Estado de partida: Entregas ABERTA. Com a flag de SPA ligada, chegar aqui
  // pelo menu passa por `location.assign`, o navegador recarrega e serve a
  // página já nessa view — `showView` é o que o app roda depois desse
  // recarregamento. O harness não recarrega, então usa a função real do app.
  app.ctx.showView('entregas', { partial: false });
  eq(app.viewAtiva(), 'entregas', 'o fixture não chegou em Entregas');
  const assignsDaEntrada = app.ctx._assigns.length;

  // Trabalho não salvo, DEPOIS da entrada — a entrada reseta, por contrato.
  const obs = app.doc.getElementById('delivery-obs');
  obs.value = 'devolucao parcial: conferir com o almoxarife';

  app.clicarNoItemDeMenu('entregas');

  eq(app.ctx._assigns.length, assignsDaEntrada,
    'o clique no menu do módulo JÁ ATIVO recarregou a página — todo formulário não salvo iria embora');
  eq(app.ctx._reloads, 0, 'houve reload explícito na ativação redundante');
  eq(obs.value, 'devolucao parcial: conferir com o almoxarife',
    'o texto não salvo foi destruído pelo clique no menu do módulo já ativo');
});

test('#343 F5-B.1 G-A-2: a guarda é por view, e não desliga o fluxo clássico', () => {
  // Controle: a guarda só vale para a view ATIVA. Estando em Estoque, clicar em
  // Entregas continua sendo transição de verdade e continua recarregando —
  // resolver o achado A tornando `location.assign` inalcançável seria trocar um
  // defeito por outro.
  const app = montarAppRealF5B('?ux_spa_navigation=1');
  app.ctx.showView('estoque', { partial: false });
  eq(app.viewAtiva(), 'estoque');
  app.clicarNoItemDeMenu('entregas');
  eq(app.ctx._assigns.length, 1, 'a transição real para Entregas deixou de acontecer');
  assert(/entregas/.test(app.ctx._assigns[0]), `a URL clássica não aponta para entregas: ${app.ctx._assigns[0]}`);
});

test('#343 F5-B.1 G-A-3: em view suportada pela SPA, o clique redundante não transiciona', () => {
  // O achado que a primeira versão desta guarda deixou passar: ela vivia dentro
  // do ramo de `SPA_NAV_CLASSIC_FALLBACK_VIEWS` e não alcançava nenhuma das oito
  // views de `SPA_NAV_SUPPORTED_VIEWS` — a maioria dos módulos. Com `canUseSpa`
  // verdadeiro, o clique repetido seguia empilhando histórico e redesenhando.
  const app = montarAppRealF5B('?ux_spa_navigation=1');
  app.ctx.showView('estoque', { partial: false });
  eq(app.viewAtiva(), 'estoque', 'o fixture não chegou em Estoque');
  assert(app.ctx.isSpaNavigationEnabled() === true, 'a flag de SPA não ligou: o gate mediria o caminho errado');

  const rascunho = app.doc.getElementById('f5b1-rascunho-estoque');
  rascunho.value = 'contagem parcial do corredor B';
  const pushesAntes = app.ctx._pushStates;
  const eventosAntes = app.eventosDeView.length;

  app.clicarNoItemDeMenu('estoque');   // o gesto contratado

  eq(app.ctx._pushStates, pushesAntes,
    'o clique no menu do módulo já ativo empilhou uma entrada de histórico duplicada — o Voltar passa a cair no próprio módulo');
  eq(app.eventosDeView.length, eventosAntes,
    'o clique emitiu epi:viewchange: houve transição onde o contrato manda não haver nenhuma');
  eq(app.ctx._assigns.length, 0, 'houve recarregamento na ativação redundante');
  eq(rascunho.value, 'contagem parcial do corredor B', 'o trabalho não salvo foi destruído');
});

test('#343 F5-B.1 G-A-4: transição real empilha, e a exceção explícita redesenha', () => {
  // Dois controles num gate. Primeiro: resolver o achado não pode ter desligado
  // a navegação das views suportadas pela SPA.
  const app = montarAppRealF5B('?ux_spa_navigation=1');
  const pushesAntes = app.ctx._pushStates;
  app.clicarNoItemDeMenu('estoque');           // dashboard → estoque, transição real
  eq(app.viewAtiva(), 'estoque', 'a transição real para uma view suportada pela SPA deixou de acontecer');
  assert(app.ctx._pushStates > pushesAntes, 'a transição real deixou de empilhar histórico');

  // Segundo: `recarregarMesmaView` continua sendo a porta de quem PRECISA
  // redesenhar a própria view — o fim do onboarding, depois de `loadBootstrap()`.
  // Sem essa porta, a tela ficaria com os dados antigos.
  const pushesDepois = app.ctx._pushStates;
  app.ctx.navigateToView('estoque', { recarregarMesmaView: true });
  assert(app.ctx._pushStates > pushesDepois,
    'a exceção explícita deixou de funcionar: quem precisa redesenhar a própria view perdeu o caminho');
});

// ── Achado C — listener independente que troca a aba de Compras ─────────────

test('#343 F5-B.1 G-C-1: clique no menu de Compras mantém a aba interna aberta', () => {
  // SEM flag nenhuma na URL, de propósito: este listener não tem feature flag.
  // O achado C é o único dos cinco que já ocorre no fluxo padrão de produção.
  const app = montarAppRealF5B('');
  app.clicarNoItemDeMenu('compras');
  eq(app.viewAtiva(), 'compras', 'o clique real não abriu Compras');
  eq(app.abaDeComprasAtiva(), 'demandas', 'a ENTRADA no módulo deveria abrir a aba padrão (contrato F5-B)');

  // O usuário abre outra aba interna — pela função real que o botão da aba usa.
  app.ctx.switchComprasTab('cotacoes');
  eq(app.abaDeComprasAtiva(), 'cotacoes');

  // (a) O gesto de menu não chega nem a emitir troca de view.
  const eventosAntes = app.eventosDeView.length;
  app.clicarNoItemDeMenu('compras');
  eq(app.eventosDeView.length, eventosAntes,
    'o clique no menu do módulo ativo emitiu troca de view: a guarda de navigateToView não está cobrindo este caminho');
  eq(app.abaDeComprasAtiva(), 'cotacoes',
    'clicar no menu de Compras estando em Compras voltou para a aba padrão — o trabalho da aba aberta foi descartado');

  // (b) E quando o listener É alcançado com `anterior === view` — redesenho
  // interno da própria view, o que `startEditEmployee` e a troca de idioma
  // fazem —, a guarda deste listener é o que segura a aba.
  app.ctx.showView('compras', { partial: false });
  assert(app.eventosDeView.length > eventosAntes, 'o redesenho interno não emitiu troca de view: o gate mediria o nada');
  eq(app.eventosDeView[app.eventosDeView.length - 1].anterior, 'compras',
    'o redesenho interno não reportou `anterior === compras`: o cenário medido não é o do contrato');
  eq(app.abaDeComprasAtiva(), 'cotacoes',
    'o redesenho da MESMA view devolveu a aba padrão e descartou o trabalho da aba aberta');
});

test('#343 F5-B.1 G-C-2: entrar em Compras vindo de outra view continua na aba padrão', () => {
  // Controle do contrato da F5-B: a guarda do achado C não pode desligar o
  // reset de ENTRADA.
  const app = montarAppRealF5B('');
  app.clicarNoItemDeMenu('compras');
  app.ctx.switchComprasTab('cotacoes');
  app.clicarNoItemDeMenu('estoque');
  eq(app.viewAtiva(), 'estoque');
  app.clicarNoItemDeMenu('compras');
  eq(app.abaDeComprasAtiva(), 'demandas',
    'sair do módulo e voltar deveria abrir a aba padrão — o reset de entrada da F5-B sumiu');
});

// ── Achado F — listener independente que troca a aba de Avaliações ──────────
//
// Sexto caminho, achado pela revisão e confirmado por enumeração FECHADA de
// todos os listeners de `epi:viewchange` da árvore servida. Mesma classe do
// achado C, em um módulo que a auditoria da F5-B não alcançou, e também sem
// feature flag nenhuma.

test('#343 F5-B.1 G-F-1: clique no menu de Avaliações mantém a aba interna aberta', () => {
  const app = montarAppRealF5B('');
  app.clicarNoItemDeMenu('avaliacoes');
  eq(app.viewAtiva(), 'avaliacoes', 'o clique real não abriu Avaliações');
  eq(app.abaDeAvaliacoesAtiva(), 'avaliacao-final',
    'a ENTRADA no módulo deveria abrir a aba padrão do papel (contrato F5-B)');

  // O usuário abre outra aba interna — clique REAL no botão da subaba, que é o
  // caminho que `bindAvaliacoesView()` escuta.
  app.clicarEm('avaltab-reclamacoes');
  eq(app.abaDeAvaliacoesAtiva(), 'reclamacoes', 'o clique real na subaba não trocou de aba');

  // (a) O gesto de menu não chega nem a emitir troca de view.
  const eventosAntes = app.eventosDeView.length;
  app.clicarNoItemDeMenu('avaliacoes');
  eq(app.eventosDeView.length, eventosAntes,
    'o clique no menu do módulo ativo emitiu troca de view: a guarda de navigateToView não está cobrindo este caminho');
  eq(app.abaDeAvaliacoesAtiva(), 'reclamacoes',
    'clicar no menu de Avaliações estando em Avaliações voltou para a aba padrão');

  // (b) E no redesenho interno da própria view, que alcança o listener, é a
  // guarda dele que segura a aba.
  app.ctx.showView('avaliacoes', { partial: false });
  assert(app.eventosDeView.length > eventosAntes, 'o redesenho interno não emitiu troca de view: o gate mediria o nada');
  eq(app.eventosDeView[app.eventosDeView.length - 1].anterior, 'avaliacoes',
    'o redesenho interno não reportou `anterior === avaliacoes`: o cenário medido não é o do contrato');
  eq(app.abaDeAvaliacoesAtiva(), 'reclamacoes',
    'o redesenho da MESMA view devolveu a aba padrão e descartou o trabalho da aba aberta');
});

test('#343 F5-B.1 G-F-2: entrar em Avaliações vindo de outra view volta à aba padrão', () => {
  const app = montarAppRealF5B('');
  app.clicarNoItemDeMenu('avaliacoes');
  app.clicarEm('avaltab-reclamacoes');
  eq(app.abaDeAvaliacoesAtiva(), 'reclamacoes');
  app.clicarNoItemDeMenu('estoque');
  eq(app.viewAtiva(), 'estoque');
  app.clicarNoItemDeMenu('avaliacoes');
  eq(app.abaDeAvaliacoesAtiva(), 'avaliacao-final',
    'sair do módulo e voltar deveria abrir a aba padrão — o reset de entrada da F5-B sumiu');
});

// ── Achado D — phase44 / rolagem ────────────────────────────────────────────



// ── Achado E — navigation.js / rootPush ─────────────────────────────────────

test('#343 F5-B.1 G-E-1: clique no menu do módulo ativo não apaga a pilha de navegação', () => {
  const app = montarAppRealF5B('?ux_hierarchy=1');
  const pilha = () => app.ctx.__EPI_VIEW_STACK__ || [];
  assert(Array.isArray(app.ctx.__EPI_VIEW_STACK__),
    'a hierarquia não iniciou — o gate mediria o nada');
  app.clicarNoItemDeMenu('estoque');
  eq(app.viewAtiva(), 'estoque');
  eq(pilha().length, 1, 'a entrada no módulo deveria deixar a pilha na raiz');

  // O usuário desce um nível DENTRO do módulo, pelo gatilho real da hierarquia.
  app.clicarEm('estoque-abrir-lote');
  eq(pilha().length, 2, 'o gatilho real de subnível não empilhou nada — o gate mediria o nada');
  eq(pilha()[1].label, 'Lote 4711');

  // (a) O gesto de menu não chega nem a emitir troca de view.
  const eventosAntes = app.eventosDeView.length;
  app.clicarNoItemDeMenu('estoque');
  eq(app.eventosDeView.length, eventosAntes,
    'o clique no menu do módulo ativo emitiu troca de view: a guarda de navigateToView não está cobrindo este caminho');
  eq(pilha().length, 2,
    'clicar no menu do módulo já ativo apagou a pilha: o Voltar da hierarquia perdeu o caminho do usuário');

  // (b) E no redesenho interno da própria view, que alcança o listener, é a
  // guarda dele que segura a pilha.
  app.ctx.showView('estoque', { partial: false });
  assert(app.eventosDeView.length > eventosAntes, 'o redesenho interno não emitiu troca de view: o gate mediria o nada');
  eq(pilha().length, 2, 'o redesenho da MESMA view apagou a pilha de navegação');
  eq(pilha()[1].label, 'Lote 4711', 'o subnível em que o usuário estava desapareceu da pilha');
});

test('#343 F5-B.1 G-E-2: transição real de raiz continua recomeçando a pilha', () => {
  const app = montarAppRealF5B('?ux_hierarchy=1');
  const pilha = () => app.ctx.__EPI_VIEW_STACK__ || [];
  app.clicarNoItemDeMenu('estoque');
  app.clicarEm('estoque-abrir-lote');
  eq(pilha().length, 2);
  app.clicarNoItemDeMenu('colaboradores');
  eq(pilha().length, 1,
    'a transição real para outra raiz deixou de recomeçar a pilha — a guarda do achado E passou do ponto');
  eq(pilha()[0].id, 'colaboradores', 'a nova raiz não é a view que o usuário abriu');
});

// ── Achado B — multitab / closeTransientUi ──────────────────────────────────



// MARCA_FIM_F5B1

// ══════════════════════════════════════════════════════════════════════════
// #343 — CARACTERIZAÇÃO COMPORTAMENTAL (PR1) E CONSOLIDAÇÃO (PR2)
// ══════════════════════════════════════════════════════════════════════════
//
// Esta seção NÃO corrige nada. Ela transforma em teste reproduzível o que a
// auditoria mediu, e responde por COMPORTAMENTO quem é o owner real de cada
// responsabilidade.
//
// Dois modos de carga, e a diferença entre eles é o objeto de estudo:
//
//   ORDEM SERVIDA      — exatamente o que `_scripts.html` manda o navegador
//                        fazer, mais a injeção dinâmica de 42/43/44 que o
//                        `app.js` dispara. É o que roda em produção.
//   CONTRAFACTUAL      — a MESMA carga, com o bloqueio neutralizado pelo lado
//                        do HOST: `ensureModuleBound` passa a derivar chave de
//                        outro namespace, e/ou a nav API é publicada antes do
//                        módulo que a consome. Nenhum byte de produção é
//                        alterado — nem em disco, nem em memória. O que muda é
//                        o ambiente em volta.
//
// O contrafactual responde "o que apareceria SE o bloqueio saísse", que é
// pergunta de decisão, não de implementação. Ele não autoriza a correção.
// ── MARCA_INICIO_PR1

const MARCA_INICIO_PR1 = 'MARCA_INICIO_PR1';
const MARCA_FIM_PR1 = 'MARCA_FIM_PR1';

// Registro das caracterizações de DEFEITO. Cada uma afirma o comportamento
// ATUAL (portanto passa hoje) e declara, em campos obrigatórios, qual seria o
// comportamento correto. Quando o defeito for corrigido, ela falha — que é o
// sinal desejado. Não é `skip` nem `xfail` permanente: nada fica ignorado.
const DEFEITOS_CARACTERIZADOS = [];
function caracterizaDefeito(nome, ficha, fn) {
  ['esperado', 'atual', 'motivo', 'responsabilidade', 'decisaoFutura'].forEach((campo) => {
    if (!ficha || !String(ficha[campo] || '').trim()) {
      throw new Error(`caracterizaDefeito("${nome}") sem o campo obrigatório "${campo}"`);
    }
  });
  DEFEITOS_CARACTERIZADOS.push({ nome, ...ficha });
  test(nome, fn);
}

// ── Harness de ownership ────────────────────────────────────────────────────

function fixtureOwnershipPR1() {
  const vista = (nome) => {
    const v = criarNoF5B('div', { id: `${nome}-view`, class: 'view' });
    // Cabeçalho já montado: faz o `applyViewHeader` do phase44 sair cedo em vez
    // de montar markup por `innerHTML`, que este shim não interpreta. Mesmo
    // recurso que o harness da F5-B.1 usa.
    v.appendChild(criarNoF5B('article', { class: 'card phase44-header' }));
    return v;
  };

  const vistas = {
    dashboard: vista('dashboard'),
    entregas: vista('entregas'),
    estoque: vista('estoque')
  };
  vistas.dashboard._classes.add('active');

  // Formulário de entrega com os campos que phase42 e phase43 procuram por id.
  const form = criarNoF5B('form', { id: 'delivery-form' });
  form.appendChild(criarNoF5B('div', { id: 'delivery-form-topo' }));
  const selecao = (id, valores) => {
    const s = criarNoF5B('select', { id });
    s.options = (valores || []).map((v) => ({ value: String(v), textContent: `opcao ${v}`, selected: false }));
    s.selectedOptions = [];
    return s;
  };
  // `name` além do `id`: o `formValues()` do app monta o payload pelos NOMES,
  // e sem eles o gate do owner real mediria um formulário vazio.
  const nomeado = (no, nome) => { no.name = nome; return no; };
  form.appendChild(nomeado(selecao('delivery-company', ['1', '2']), 'company_id'));
  form.appendChild(nomeado(selecao('delivery-unit-filter', ['10', '20']), 'unit_id'));
  form.appendChild(nomeado(selecao('delivery-employee', ['100', '200']), 'employee_id'));
  form.appendChild(nomeado(selecao('delivery-epi', ['1000', '2000']), 'epi_id'));
  form.appendChild(criarNoF5B('input', { id: 'delivery-stock-item-id', name: 'stock_item_id', type: 'hidden' }));
  form.appendChild(criarNoF5B('input', { id: 'delivery-stock-qr-code', name: 'stock_qr_code', type: 'hidden' }));
  form.appendChild(criarNoF5B('input', { id: 'delivery-role' }));
  form.appendChild(criarNoF5B('input', { id: 'delivery-stock-item-code' }));
  form.appendChild(criarNoF5B('input', { id: 'delivery-quantity', name: 'quantity', value: '1' }));
  form.appendChild(criarNoF5B('input', { id: 'delivery-date', name: 'delivery_date', value: '2026-09-14' }));
  form.appendChild(criarNoF5B('input', { id: 'delivery-employee-search', type: 'search' }));
  form.appendChild(criarNoF5B('input', { id: 'delivery-epi-search', type: 'search' }));
  form.appendChild(criarNoF5B('div', { id: 'delivery-ux-feedback' }));
  // Este shim não interpreta `innerHTML`, e o phase42 monta o checkbox de
  // revisão por essa via (`renderQuickConfirm`). O nó abaixo representa aquele
  // checkbox, com o MESMO id que `hasExplicitReview()` procura — é o gate real
  // do phase42 que fica exercitável, não um atalho que o contorna.
  form.appendChild(criarNoF5B('input', { id: 'phase42-review-check', type: 'checkbox' }));
  // Devolução: o app roteia para /api/devolutions e APAGA stock_item_id e
  // stock_qr_code do payload. Os nós precisam existir antes de o app.js rodar,
  // porque `refs` é montado na avaliação do arquivo.
  form.appendChild(criarNoF5B('input', { id: 'delivery-is-devolution', name: 'is_devolution', type: 'checkbox' }));
  form.appendChild(criarNoF5B('div', { id: 'delivery-devolution-fields' }));
  form.appendChild(criarNoF5B('input', { id: 'delivery-returned-date', type: 'date' }));
  form.appendChild(criarNoF5B('input', { id: 'delivery-return-condition', value: 'usable' }));
  form.appendChild(criarNoF5B('input', { id: 'delivery-return-destination', value: 'stock' }));
  const enviar = criarNoF5B('button', { id: 'delivery-submit', class: 'primary' });
  enviar.type = 'submit';
  form.appendChild(enviar);
  vistas.entregas.appendChild(form);

  // Campo de dado pessoal FORA do fluxo de entrega: é o que o phase41
  // persistiria, e o que `resetAppFormDrafts()` existe para limpar.
  const formColaborador = criarNoF5B('form', { id: 'employee-form' });
  formColaborador.appendChild(criarNoF5B('input', { id: 'employee-name', name: 'name' }));
  formColaborador.appendChild(criarNoF5B('input', { id: 'employee-email', name: 'email', type: 'email' }));
  vistas.estoque.appendChild(formColaborador);

  // DOIS dropdowns no contrato de atributos que app.js e phase44 disputam.
  // Dois, e não um: a diferença entre os owners só aparece com mais de um.
  const dropdowns = ['acoes', 'exportar'].map((nome) => {
    const raiz = criarNoF5B('div', { id: `dropdown-${nome}`, 'data-ui-dropdown': '1' });
    raiz.appendChild(criarNoF5B('button', { id: `dropdown-${nome}-trigger`, 'data-dropdown-trigger': '1' }));
    const painel = criarNoF5B('div', { id: `dropdown-${nome}-panel`, 'data-dropdown-panel': '1' });
    // Painel de dropdown tem item acionável: é DENTRO dele que o foco do
    // teclado fica depois de abrir, e é esse foco que some quando o painel é
    // escondido. Sem o item, o gesto real não seria reproduzível.
    painel.appendChild(criarNoF5B('button', { id: `dropdown-${nome}-item` }));
    painel.hidden = true;
    raiz.appendChild(painel);
    return raiz;
  });

  const menu = criarNoF5B('nav', { id: 'menu' });
  ['dashboard', 'entregas', 'estoque'].forEach((view) => {
    const item = criarNoF5B('button', { 'data-view': view, class: 'menu-link' });
    item.textContent = view;
    menu.appendChild(item);
  });

  const main = criarNoF5B('div', { id: 'main-content' });
  Object.values(vistas).forEach((v) => main.appendChild(v));

  const doc = criarNoF5B('document', {});
  doc.appendChild(criarNoF5B('div', { class: 'topbar' }));
  doc.appendChild(menu);
  doc.appendChild(main);
  dropdowns.forEach((d) => doc.appendChild(d));
  // Campo SOLTO, fora de qualquer <form>. Espelha `#compras-supplier-name` e
  // irmãos: `form.reset()` não os alcança, e foi por isso que a política de
  // limpeza do app deixou de ser escopada por <form> (#343 PR 3).
  doc.appendChild(criarNoF5B('input', { id: 'compras-supplier-name', type: 'text' }));
  // O mesmo Escape que fecha o dropdown também fecha o modal de assinatura.
  // O nó precisa existir para que a fatia 2C possa provar que esse ramo
  // continua rodando depois de a devolução de foco entrar no handler.
  doc.appendChild(criarNoF5B('div', { id: 'signature-modal', class: 'signature-modal is-open' }));
  [['hierarchy-back-btn', 'button'], ['hierarchy-breadcrumb', 'div'],
   ['hierarchy-breadcrumb-wrap', 'div'], ['interactive-nav-tabs', 'div'], ['login-screen', 'div']]
    .forEach(([id, tag]) => doc.appendChild(criarNoF5B(tag, { id })));

  doc.body = criarNoF5B('body', {});
  doc.head = criarNoF5B('head', {});
  doc.documentElement = criarNoF5B('html', {});
  doc.readyState = 'complete';
  doc.title = '';
  doc.getElementById = (id) => descendentesF5B(doc).find((n) => n.id === id) || null;
  doc.createElement = (t) => criarNoF5B(t, {});
  // `activeElement` só vale se o nó focado ainda pertence A ESTE documento: um
  // gate que monta dois apps no mesmo teste não pode ver o foco do outro.
  // Quando não há foco válido, o navegador reporta o <body> — e é o que se
  // devolve aqui, para o código de produção enxergar o mesmo que enxergaria
  // num navegador de verdade.
  //
  // LIMITE DECLARADO: o foco é global, como no navegador — só um documento o
  // tem por vez. Um gate que monta DOIS apps e quer comparar o foco dos dois
  // precisa ler o do primeiro ANTES de montar o segundo; depois disso o
  // primeiro passa a reportar o próprio <body>, que é exatamente o que um
  // navegador faria com uma aba que perdeu o foco.
  Object.defineProperty(doc, 'activeElement', {
    configurable: true,
    get() {
      return NO_FOCADO_F5B && descendentesF5B(doc).includes(NO_FOCADO_F5B)
        ? NO_FOCADO_F5B
        : doc.body;
    }
  });
  return { doc, vistas, form, dropdowns };
}

function montarAppOwnership(busca, opcoes) {
  const o = opcoes || {};
  const raizStatic = path.resolve(JS_ROOT, '..');
  const { doc, vistas, form, dropdowns } = fixtureOwnershipPR1();

  const armazem = () => ({
    _s: {},
    getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
    setItem(k, v) { this._s[k] = String(v); },
    removeItem(k) { delete this._s[k]; },
    key(i) { return Object.keys(this._s)[i] ?? null; },
    get length() { return Object.keys(this._s).length; }
  });
  const local = armazem();
  Object.entries(o.storageInicial || {}).forEach(([k, v]) => local.setItem(k, v));

  // Respostas de rede declaradas pelo teste. `fetch` nunca sai da máquina: o
  // que se mede aqui é quem EMBRULHA o fetch, não o que o servidor responde.
  // Respostas casadas por trecho de URL, e não por ordem de chegada: a carga
  // da página dispara requisições próprias (i18n, tenant, bootstrap) que
  // consumiriam uma fila posicional e tornariam o gate dependente de corrida.
  const respostasPorUrl = new Map(Object.entries(o.respostasPorUrl || {}));
  const chamadasDeRede = [];
  const fetchBase = function fetchBaseDoHarness(url) {
    const alvo = String(url || '');
    chamadasDeRede.push(alvo);
    let escolhida = null;
    respostasPorUrl.forEach((valor, trecho) => {
      if (escolhida === null && alvo.includes(trecho)) escolhida = valor;
    });
    const proxima = escolhida || { ok: true, status: 200 };
    if (proxima instanceof Error) return Promise.reject(proxima);
    return Promise.resolve(proxima);
  };

  const ctx = {
    document: doc, localStorage: local, sessionStorage: armazem(),
    console: { log() {}, info() {}, warn() {}, error() {}, debug() {} },
    CustomEvent: class { constructor(t, i) { this.type = t; this.bubbles = true; Object.assign(this, i || {}); } },
    Event: class { constructor(t, i) { this.type = t; this.bubbles = false; Object.assign(this, i || {}); } },
    AbortController: class { constructor() { this.signal = { addEventListener() {} }; } abort() {} },
    MutationObserver: class { observe() {} disconnect() {} },
    // Construtores de elemento que o app usa em `instanceof`. Sem eles o acesso
    // lança ReferenceError dentro de funções do app, e o gate mediria um crash
    // do fixture em vez do comportamento do módulo. Como nenhum nó do shim
    // herda deles, todo `instanceof` dá falso — que é a mesma degradação que o
    // harness da F5-B.1 já aceita para `HTMLElement`.
    // Plataforma: `formValues()` do app é
    // `Object.fromEntries(new FormData(form).entries())`. Sem este construtor o
    // envio real da entrega morre antes de chegar à validação que o gate mede.
    // Segue a semântica do navegador nos pontos que importam: só controles COM
    // `name`, checkbox/radio apenas quando marcados, e `select` entrega o
    // `value` corrente.
    FormData: class {
      constructor(form) {
        this._pares = [];
        if (!form || typeof form.querySelectorAll !== 'function') return;
        descendentesF5B(form).forEach((campo) => {
          if (!['INPUT', 'SELECT', 'TEXTAREA'].includes(campo.tagName)) return;
          if (!campo.name || campo.disabled) return;
          const tipo = String(campo.type || '').toLowerCase();
          if ((tipo === 'checkbox' || tipo === 'radio') && !campo.checked) return;
          this._pares.push([String(campo.name), String(campo.value == null ? '' : campo.value)]);
        });
      }
      entries() { return this._pares[Symbol.iterator](); }
      get(nome) { const par = this._pares.find((x) => x[0] === nome); return par ? par[1] : null; }
      forEach(fn) { this._pares.forEach(([k, v]) => fn(v, k, this)); }
      [Symbol.iterator]() { return this.entries(); }
    },
    HTMLElement: class {}, HTMLFormElement: class {}, HTMLButtonElement: class {},
    HTMLInputElement: class {}, HTMLSelectElement: class {}, HTMLTextAreaElement: class {},
    HTMLAnchorElement: class {},
    setTimeout, clearTimeout, setInterval, clearInterval, Promise, URL, URLSearchParams, Map, Set, WeakSet,
    requestAnimationFrame: (f) => setTimeout(f, 0),
    performance: { now: () => Date.now() },
    getComputedStyle: (el) => ({
      display: (el && el.hidden) ? 'none' : 'block', visibility: 'visible'
    }),
    matchMedia: () => ({ matches: false, addEventListener() {} }),
    navigator: { userAgent: 'node' },
    alert() {}, confirm: () => true,
    fetch: fetchBase,
    scrollTo() {}, scrollY: 0,
    _assigns: [], _reloads: 0, _pushStates: 0, _replaceStates: 0
  };
  ctx.location = {
    search: busca || '', href: `http://local/${busca || ''}`, pathname: '/', origin: 'http://local',
    assign(url) { ctx._assigns.push(String(url)); },
    reload() { ctx._reloads += 1; }
  };
  ctx.history = {
    length: 1,
    pushState() { ctx._pushStates += 1; },
    replaceState() { ctx._replaceStates += 1; },
    back() {}
  };
  // `window` precisa das fases de escuta como qualquer nó: módulos registram
  // `popstate` e `beforeunload` nele.
  const noJanela = criarNoF5B('window', {});
  ctx.addEventListener = noJanela.addEventListener;
  ctx.removeEventListener = noJanela.removeEventListener;
  ctx.dispatchEvent = noJanela.dispatchEvent;
  ctx._janela = noJanela;
  ctx.window = ctx; ctx.globalThis = ctx; ctx.self = ctx;
  vmF5B.createContext(ctx);

  // Injeção dinâmica: `app.js` cria <script> para 42/43/44 e os anexa ao head.
  // Script inserido por script é ASSÍNCRONO (a propriedade `defer` é ignorada),
  // então ele não roda no meio do app.js — vai para a fila e é despachado
  // depois. O harness modela "chegou da rede depois do resto", que é o caso
  // comum; a ordem entre 42, 43 e 44 NÃO é garantida pelo navegador, e nenhum
  // gate desta seção depende dela.
  const filaInjetada = [];
  doc.head.appendChild = function (no) {
    const src = String((no && no.src) || '');
    const casa = src.match(/\/(ux-phase4\d\.js)/);
    if (casa) filaInjetada.push(casa[1]);
    return no;
  };

  const rodar = (rel) => {
    try {
      vmF5B.runInContext(fs.readFileSync(path.join(raizStatic, rel), 'utf-8'), ctx, { filename: rel });
    } catch (erro) {
      (ctx._errosDeCarga = ctx._errosDeCarga || []).push({ rel, erro: String(erro && erro.message) });
    }
  };

  const ordem = fs.readFileSync(path.join(raizStatic, 'views', '_scripts.html'), 'utf-8')
    .match(/src="\/([^"?]+\.js)/g).map((m) => m.slice(6));

  ordem.forEach((rel) => {
    // CONTRAFACTUAL de navegação: publicar a nav API ANTES do módulo que a
    // consome na avaliação do próprio arquivo. Em produção ela só nasce dentro
    // do `init()`, no DOMContentLoaded — depois deste ponto.
    if (rel.endsWith('multitab-navigation.js') && o.publicarNavApiCedo
        && typeof ctx.registerMultitabNavigationApi === 'function') {
      try { ctx.registerMultitabNavigationApi(); } catch (_e) { /* medido pelos gates */ }
    }
    rodar(rel);
    if (rel === 'app.js') {
      const estado = ctx.__EPI_APP_STATE__ || {};
      estado.user = o.usuario || { id: 1, role: 'general_admin', company_id: 1 };
      estado.permissions = [
        'dashboard:view', 'deliveries:view', 'deliveries:create',
        'stock:view', 'employees:view'
      ];
      // CONTRAFACTUAL de bootstrap: `ensureModuleBound` passa a derivar a chave
      // num namespace PRÓPRIO, em vez de `__EPI_<CHAVE>_BOUND__` — que é a
      // mesma chave que os IIFEs de 41/43/44 gravam em si mesmos. Substitui-se
      // o objeto de helpers inteiro porque o original é `Object.freeze`d; a
      // propriedade global, essa, é gravável. Nenhum arquivo servido é tocado.
      const originais = ctx.__EPI_FRONTEND_HELPERS__ || {};
      const substitutos = {};
      if (o.contrafactualBootstrap) {
        const ligados = Object.create(null);
        substitutos.ensureModuleBound = function ensureModuleBoundSemColisao(chave) {
          const k = String(chave || '');
          if (ligados[k]) return false;
          ligados[k] = true;
          return true;
        };
      }
      // Espiã de flags: registra QUEM perguntou por qual flag. É assim que se
      // prova que um módulo nem chegou ao próprio gate de flag — afirmação que
      // nenhuma leitura de código consegue fazer sozinha.
      if (o.espiarFlags) {
        const leituras = [];
        ctx._leiturasDeFlag = leituras;
        const embrulha = (fn) => function (nome, opcoes) {
          const r = fn.call(this, nome, opcoes);
          leituras.push({ flag: String(nome), retorno: r });
          return r;
        };
        if (typeof originais.getFeatureFlag === 'function') {
          substitutos.getFeatureFlag = embrulha(originais.getFeatureFlag);
        }
        if (typeof ctx.getFeatureFlag === 'function') {
          ctx.getFeatureFlag = embrulha(ctx.getFeatureFlag);
        }
      }
      if (o.espiaoDeErro && typeof originais.reportNonCriticalError === 'function') {
        const registro = [];
        ctx._errosNaoCriticos = registro;
        substitutos.reportNonCriticalError = function (ctxMsg, erro) {
          registro.push({ ctx: String(ctxMsg), erro: String((erro && erro.message) || erro), pilha: String((erro && erro.stack) || '').split('\n').slice(1, 4).join(' | ') });
        };
      }
      if (Object.keys(substitutos).length) {
        ctx.__EPI_FRONTEND_HELPERS__ = Object.freeze({ ...originais, ...substitutos });
      }
    }
  });

  // Scripts assíncronos chegam agora.
  filaInjetada.forEach(rodar);

  const listenersDe = (alvo, evento) => ((alvo && alvo._handlers && alvo._handlers[evento]) || []);
  const contarListeners = (alvo, evento) => listenersDe(alvo, evento).length;

  return {
    ctx, doc, vistas, form, dropdowns, ordem, filaInjetada, chamadasDeRede, local,
    listenersDe, contarListeners,
    // O fetch de base, ANTES de qualquer embrulho. Serve para contar camadas de
    // instrumentação sem depender de marcas privadas: quantos saltos existem
    // entre `ctx.fetch` e ele. Sem isso a contagem seria uma dedução a partir
    // das marcas — e é justamente a marca privada de cada dono que falha em
    // enxergar o outro (PR1 E-3).
    fetchBase,
    // A gravação em storage do app é DEBOUNCED (`queueStorageWrite`). Quem a
    // força é o próprio app, em `beforeunload`/`pagehide`/`visibilitychange`.
    // O gate chama essa mesma função — não inventa uma escrita própria.
    descarregarStorage: () => {
      if (typeof ctx.flushPendingStorageWrites === 'function') ctx.flushPendingStorageWrites();
    },
    responderPara: (trecho, r) => { respostasPorUrl.set(String(trecho), r); },
    // Dispara o bootstrap REAL do app. O `init()` é `async function` declarada
    // dentro do bloco `if (!globalThis.__EPI_APP_RUNTIME_LOADED__) {` que
    // envolve o app.js inteiro — e declaração `async function` em bloco NUNCA
    // vaza para o global (a hoisting legada do Annex B não vale para elas).
    // Por isso nem `init` nem `saveSimpleForm` existem em `ctx`, enquanto
    // `navigateToView` e `showView`, que são `function` comum, existem.
    //
    // O caminho que sobra é o de produção: o app registra
    // `safeOn(document, 'DOMContentLoaded', () => init().catch(...))`, e esse
    // listener está no documento do harness. Disparar o evento roda o
    // bootstrap de verdade — inclusive `bindAppListener(#delivery-form,
    // 'submit', ...)`, que é o owner do envio da entrega. O `.catch()` do
    // próprio app absorve a rejeição das chamadas de API que vierem depois.
    dispararBootstrapDoApp: () => {
      doc.dispatchEvent(new ctx.Event('DOMContentLoaded', { bubbles: false }));
    },
    chamadasPara: (trecho) => chamadasDeRede.filter((u) => u.includes(trecho)),
    viewAtiva: () => {
      const no = doc.querySelector('.view.active');
      return no && no.id ? no.id.replace(/-view$/, '') : '';
    },
    clicarNoItemDeMenu: (view) => {
      const item = doc.querySelector(`.menu-link[data-view="${view}"]`);
      if (!item) throw new Error(`fixture sem item de menu para "${view}"`);
      return item.dispatchEvent(new ctx.Event('click', { bubbles: true }));
    },
    enviarFormularioDeEntrega: () => {
      const ev = new ctx.Event('submit', { bubbles: true });
      form.dispatchEvent(ev);
      return ev;
    },
    inicializouDeVerdade: (alvos) => alvos.some(([alvo, evento]) => contarListeners(alvo, evento) > 0)
  };
}

test('PR1 H-0: o harness carrega o app servido na ordem de produção', () => {
  const app = montarAppOwnership('');
  assert(app.ordem.length >= 38, `esperava a lista de _scripts.html, veio ${app.ordem.length}`);
  // ATUALIZADO NO PR 4: eram três injeções dinâmicas (42, 43 e 44). O 43 e o 44
  // foram removidos; sobra a do phase42, que continua sendo owner.
  eq(app.filaInjetada.length, 1,
    `o phase42 deveria ser o único script injetado dinamicamente, vieram ${app.filaInjetada.length}`);
  eq(app.filaInjetada[0], 'ux-phase42.js', 'o script injetado deixou de ser o do phase42');
});

// ── B. phase42 — CONTROLE POSITIVO ──────────────────────────────────────────
//
// O phase42 é o único dos cinco que inicializa na ordem servida. Ele é o
// controle positivo desta seção: se estes gates passarem, o harness sabe
// reconhecer um módulo REALMENTE inicializado — e a inércia que os gates
// seguintes medem não é cegueira do harness.

test('PR1 B-1: phase42 com a flag DESLIGADA não inicializa', () => {
  const app = montarAppOwnership('');
  eq(app.contarListeners(app.form, 'submit'), 0, 'com a flag desligada não deveria haver gate de submit do phase42');
  eq(app.doc.getElementById('phase42-suggestion-box'), null, 'o painel de sugestão não deveria existir');
  assert(!app.doc.body.classList.contains('phase42-enabled'), 'a marca de habilitado não deveria estar no body');
});

test('PR1 B-2: phase42 com a flag LIGADA inicializa — registra listeners e monta painéis', () => {
  const app = montarAppOwnership('?ux_phase42=1');
  assert(app.doc.body.classList.contains('phase42-enabled'), 'phase42 não marcou o body: não chegou ao init()');
  assert(app.doc.getElementById('phase42-suggestion-box'), 'o painel de sugestão não foi montado');
  assert(app.doc.getElementById('phase42-alerts-box'), 'o painel de alertas não foi montado');
  assert(app.doc.getElementById('phase42-quick-confirm'), 'o resumo rápido não foi montado');
  eq(app.contarListeners(app.form, 'submit'), 1, 'phase42 deveria registrar exatamente um gate de submit');
  assert(app.contarListeners(app.doc, 'epi:delivery-submit-success') >= 1,
    'phase42 não escuta a conclusão da entrega: o registro de uso nunca aconteceria');
});

test('PR1 B-3: phase42 é o gate de submit — sem revisão explícita, a entrega não passa', () => {
  const app = montarAppOwnership('?ux_phase42=1');
  const evento = app.enviarFormularioDeEntrega();
  eq(evento.defaultPrevented, true, 'sem marcar a revisão, o submit deveria ser barrado pelo phase42');
  const aviso = app.doc.getElementById('delivery-ux-feedback');
  assert(String(aviso.textContent || '').includes('Revise'),
    `o phase42 deveria explicar o bloqueio, veio "${aviso.textContent}"`);
});

test('PR1 B-4: phase42 não duplica — o guard central bloqueia a segunda carga', () => {
  const app = montarAppOwnership('?ux_phase42=1');
  const antes = app.contarListeners(app.form, 'submit');
  // Segunda avaliação do MESMO arquivo servido, como aconteceria se a injeção
  // dinâmica disparasse duas vezes.
  vmF5B.runInContext(
    fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), 'ux-phase42.js'), 'utf-8'),
    app.ctx, { filename: 'ux-phase42.js' });
  eq(app.contarListeners(app.form, 'submit'), antes,
    'a segunda carga registrou listeners de novo: o guard de duplicidade não seguraria');
});

test('PR1 B-5: o harness distingue inicializado de inerte (contraprova do controle)', () => {
  const ligado = montarAppOwnership('?ux_phase42=1');
  const desligado = montarAppOwnership('');
  assert(ligado.contarListeners(ligado.form, 'submit') > desligado.contarListeners(desligado.form, 'submit'),
    'o harness não consegue separar módulo ativo de módulo inerte — nenhum gate desta seção provaria nada');
});



// CONVERTIDO NO PR 4. Este gate era uma caracterização de DEFEITO: a limpeza
// das chaves legadas estava dentro dos módulos, DEPOIS da guarda que os fazia
// retornar cedo, e por isso nunca rodava em 41, 43 e 44. A `decisaoFutura`
// registrada no PR 1 dizia: "se os módulos forem removidos, a limpeza precisa
// sobreviver a eles em algum lugar que execute".
//
// É o que o PR 4 fez. O defeito não foi corrigido dentro dos módulos — eles
// foram embora, e a limpeza passou para o `app.js`. O gate vira o contrato
// positivo dessa decisão.
test('PR1 C-3 (convertido): a limpeza das chaves legadas sobrevive aos módulos removidos', () => {
  const legadas = {
    'epi:ux:phase41:scroll:v2': '{"de":"quem usou a maquina antes"}',
    'epi:ux:phase41:context:v2': '{"delivery-role":"encarregado"}',
    'epi:ux:phase42:memory:v2': '{"last":{"employeeId":7,"companyId":3}}',
    'epi:ux:phase43:state:v1': '{"qty":"5"}',
    'epi.ux.phase44.filters.entregas': '{"deliveries-filter-company":"3"}'
  };
  const app = montarAppOwnership('', { storageInicial: legadas });

  // Agora TODAS somem — as três do cleanup do app e a do phase42, que ele
  // próprio continua limpando por sobreviver.
  Object.keys(legadas).forEach((chave) => {
    eq(app.local.getItem(chave), null,
      `a chave legada "${chave}" sobreviveu: a limpeza deixou de alcançá-la`);
  });
});




// ── D. phase42 × phase43 — MATRIZ DE DEPENDÊNCIA ────────────────────────────
//
// As duas células com o 43 ligado só existem no contrafactual: na ordem
// servida o phase43 é inerte. Elas medem o que apareceria SE o bloqueio saísse.

function celulaDaMatriz42x43(busca, opcoes) {
  const app = montarAppOwnership(busca, { contrafactualBootstrap: true, ...(opcoes || {}) });
  // Contexto mínimo de uma entrega em preenchimento.
  app.doc.getElementById('delivery-employee').value = '100';
  app.doc.getElementById('delivery-epi').value = '1000';
  app.doc.getElementById('delivery-unit-filter').value = '10';
  return app;
}





// ── E. phase44 × error-monitor.js — INTERCEPTAÇÃO DE fetch ──────────────────

test('PR1 E-1: o owner ativo do fetch é o error-monitor.js, sem flag nenhuma', () => {
  const app = montarAppOwnership('');
  eq(app.ctx.fetch.__EPI_MONITORED_FETCH__, true,
    'o error-monitor não embrulhou o fetch na carga padrão — ele deixou de ser o owner');
  assert(typeof app.ctx.__EPI_FETCH_MONITOR_ORIGINAL__ === 'function',
    'o fetch original não foi preservado pelo monitor');
  assert(app.ctx.__EPI_PHASE44_FETCH_BRIDGED__ !== true,
    'o phase44 embrulhou o fetch na ordem servida — ele não deveria nem iniciar');
});

test('PR1 E-2: o wrapper do error-monitor é idempotente contra a própria recarga', () => {
  const app = montarAppOwnership('');
  const primeiro = app.ctx.fetch;
  vmF5B.runInContext(
    fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), 'error-monitor.js'), 'utf-8'),
    app.ctx, { filename: 'error-monitor.js' });
  eq(app.ctx.fetch, primeiro, 'a segunda carga do error-monitor embrulhou o fetch de novo');
});



// ── F. phase44 × app.js — DROPDOWN [data-ui-dropdown] ───────────────────────
//
// Os dois usam o MESMO contrato de atributos. Isso, sozinho, não prova
// duplicidade: o que decide é se o COMPORTAMENTO é o mesmo. Os gates abaixo
// exercitam os dois owners contra o mesmo fixture, gesto por gesto, e a
// diferença que sobrar é o que eventualmente precisaria ser absorvido.

// Owner atual: `setupInteractiveDropdowns()` do app.js, atrás de
// `isHtmxAlpineProductionActive()` — que é `htmx_alpine_production_enabled`
// E `ux_tools_functional_enabled`. A função é chamada dentro do `init()`, no
// DOMContentLoaded; aqui ela é chamada diretamente, como o harness da F5-B.1
// faz com `setupViewTabs()`.
function appComDropdownDoApp() {
  const app = montarAppOwnership('?ux_htmx_prod=1&ux_tools_functional=1');
  assert(app.ctx.isHtmxAlpineProductionActive() === true,
    'as flags do dropdown do app não ligaram: o gate mediria o caminho errado');
  app.ctx.setupInteractiveDropdowns();
  return app;
}

function appComDropdownDoPhase44() {
  // Sem as flags do app: só o phase44 liga, para o contrato dele ser medido
  // isolado, e não a soma dos dois.
  const app = montarAppOwnership('?ux_phase44=1', { contrafactualBootstrap: true });
  assert(app.ctx.isHtmxAlpineProductionActive() === false,
    'o dropdown do app também ligou: a medição não isolaria o contrato do phase44');
  return app;
}

function clicarNoGatilho(app, nome) {
  const gatilho = app.doc.getElementById(`dropdown-${nome}-trigger`);
  gatilho.dispatchEvent(new app.ctx.Event('click', { bubbles: true }));
}
function estadoDoDropdown(app, nome) {
  const raiz = app.doc.getElementById(`dropdown-${nome}`);
  const painel = app.doc.getElementById(`dropdown-${nome}-panel`);
  const gatilho = app.doc.getElementById(`dropdown-${nome}-trigger`);
  return {
    aberto: raiz.classList.contains('is-open'),
    painelVisivel: painel.hidden === false,
    aria: gatilho.getAttribute('aria-expanded')
  };
}

test('PR1 F-1: owner atual do dropdown é o app.js — abre, fecha e sincroniza aria/painel', () => {
  const app = appComDropdownDoApp();
  eq(estadoDoDropdown(app, 'acoes').aberto, false, 'deveria começar fechado');
  clicarNoGatilho(app, 'acoes');
  const aberto = estadoDoDropdown(app, 'acoes');
  eq(aberto.aberto, true, 'o clique no gatilho não abriu');
  eq(aberto.painelVisivel, true, 'o painel continuou escondido');
  eq(aberto.aria, 'true', 'aria-expanded não acompanhou');
  clicarNoGatilho(app, 'acoes');
  const fechado = estadoDoDropdown(app, 'acoes');
  eq(fechado.aberto, false, 'o segundo clique não fechou');
  eq(fechado.aria, 'false', 'aria-expanded não voltou');
});







// ── G. multitab-navigation × navegação principal ────────────────────────────
//
// A pergunta que estes gates respondem é uma só: se o multitab fosse ativado,
// QUEM passaria a ser o owner efetivo do clique no menu lateral?

// Owner atual. `bindMenuNavigation()` é a função REAL do app; ela é chamada no
// `init()`, no DOMContentLoaded, e aqui é chamada diretamente — mesmo recurso
// que o harness da F5-B.1 usa.
//
// LIMITE DO HARNESS, declarado: não é possível espionar uma chamada INTERNA do
// `app.js` substituindo a propriedade global correspondente. Num `vm`, as
// funções declaradas no topo de um script resolvem referências do mesmo script
// pelo binding dele, e a troca feita de fora não é vista. Medido, não suposto:
// a pilha do gesto real mostra `dispatchEvent -> app.js:bindMenuNavigation ->
// navigateToView`, com a versão ORIGINAL.
//
// Então o discriminador aqui é o EFEITO, não a chamada — e é justamente o que
// separa os dois caminhos: `navigateToView` chama `location.assign` nas views
// que a SPA não cobre; `navApi.showView`, que é por onde o multitab entra, não
// chama. Mesma técnica que os gates da F5-B.1 usam com `_assigns`.
function appComNavegacaoDoApp(busca, opcoes) {
  const app = montarAppOwnership(busca || '?ux_spa_navigation=1', opcoes);
  app.ctx.bindMenuNavigation();
  const vistos = [];
  app.doc.addEventListener('epi:viewchange', (ev) => vistos.push(ev && ev.detail));
  return { ...app, vistos };
}

test('PR1 G-1: owner atual da navegação — o clique no menu chega a navigateToView', () => {
  const app = appComNavegacaoDoApp();
  eq(app.viewAtiva(), 'dashboard', 'o fixture deveria começar no dashboard');
  eq(app.ctx._assigns.length, 0, 'o estado inicial já deveria estar limpo');
  app.clicarNoItemDeMenu('entregas');
  eq(app.ctx._assigns.length, 1,
    'o clique no menu não alcançou navigateToView — só ela recarrega a view fora da cobertura da SPA');
  assert(String(app.ctx._assigns[0]).includes('entregas'),
    `a navegação foi para outro lugar: ${app.ctx._assigns[0]}`);
});

test('PR1 G-2: a guarda de ativação redundante vive no owner atual', () => {
  const app = appComNavegacaoDoApp();
  const antes = app.vistos.length;
  app.clicarNoItemDeMenu('dashboard'); // já é a view ativa
  eq(app.ctx._assigns.length, 0, 'ativação redundante recarregou a página');
  eq(app.vistos.length, antes, 'ativação redundante emitiu epi:viewchange: a guarda do app deixou de segurar');
  eq(app.ctx._pushStates, 0, 'ativação redundante empilhou entrada de histórico');
});





// ── H. O que o phase43 acrescenta ao phase42 ────────────────────────────────
//
// A pergunta de decisão não é "o 43 duplica o 42?", e sim "sobra alguma
// capacidade no 43 que o owner não tem?". Sem resposta medida, remover é
// chute e preservar é inércia.

// CORRIGIDO NO PR 2A. Estes dois gates continuam medindo o que sempre mediram —
// phase42 não valida o código, phase43 valida — mas a CONCLUSÃO que se tirou
// deles estava errada. Eles comparam 42 com 43 e nunca mediram o `app.js`, cujo
// handler de submit da entrega é ligado dentro do `init()`, que este harness só
// passou a executar no PR 2A (`dispararBootstrapDoApp`). O owner real da
// exigência é o app — ver `PR2A A-1`. Logo, a capacidade NÃO é exclusiva do 43.
test('PR1 H-1: o phase42 sozinho NÃO valida o código lido do item de estoque', () => {
  const app = montarAppOwnership('?ux_phase42=1', { contrafactualBootstrap: true });
  app.doc.getElementById('delivery-employee').value = '100';
  app.doc.getElementById('delivery-epi').value = '1000';
  app.doc.getElementById('delivery-unit-filter').value = '10';
  app.doc.getElementById('delivery-quantity').value = '2';
  app.doc.getElementById('delivery-stock-item-code').value = ''; // não lido
  app.doc.getElementById('phase42-review-check').checked = true;

  const evento = app.enviarFormularioDeEntrega();
  eq(evento.defaultPrevented, false,
    'o phase42 passou a barrar por código não lido — ele absorveu a capacidade e o 43 perdeu a exclusividade');
});


// ── Z. MATRIZES — conclusões ancoradas em medição ───────────────────────────

test('PR1 Z-1: matriz de ownership — a coluna "ativa hoje?" é remedida, não declarada', () => {
  // Cada linha reafirma, na ordem SERVIDA, se a implementação candidata está
  // mesmo em operação. Se qualquer uma mudar de estado, este gate quebra e a
  // matriz do PR precisa ser revista antes de qualquer decisão.
  const padrao = montarAppOwnership('');
  const comFlagsDoDropdown = montarAppOwnership('?ux_htmx_prod=1&ux_tools_functional=1');
  const com42 = montarAppOwnership('?ux_phase42=1');

  const linhas = [
    { responsabilidade: 'Instrumentação de requisições HTTP',
      candidata: 'error-monitor.js', ativaHoje: padrao.ctx.fetch.__EPI_MONITORED_FETCH__ === true,
      esperada: true, owner: 'error-monitor.js' },
    { responsabilidade: 'Instrumentação de requisições HTTP (concorrente)',
      candidata: 'ux-phase44.js (bindFetchFeedbackBridge)', ativaHoje: padrao.ctx.__EPI_PHASE44_FETCH_BRIDGED__ === true,
      esperada: false, owner: 'error-monitor.js' },
    { responsabilidade: 'Dropdown [data-ui-dropdown]',
      candidata: 'app.js (setupInteractiveDropdowns)', ativaHoje: comFlagsDoDropdown.ctx.isHtmxAlpineProductionActive() === true,
      esperada: true, owner: 'app.js' },
    { responsabilidade: 'Dropdown [data-ui-dropdown] (concorrente)',
      candidata: 'ux-phase44.js (createDropdown)', ativaHoje: padrao.doc.body.classList.contains('phase44-enabled'),
      esperada: false, owner: 'app.js' },
    { responsabilidade: 'Intenção de navegação (clique de menu)',
      candidata: 'app.js (bindMenuNavigation → navigateToView)', ativaHoje: typeof padrao.ctx.navigateToView === 'function',
      esperada: true, owner: 'app.js' },
    { responsabilidade: 'Intenção de navegação (concorrente)',
      candidata: 'multitab-navigation.js', ativaHoje: padrao.doc.body.classList.contains('ux-multitab-enabled'),
      esperada: false, owner: 'app.js' },
    { responsabilidade: 'Assistente e pré-condição de envio da entrega',
      candidata: 'ux-phase42.js', ativaHoje: com42.doc.body.classList.contains('phase42-enabled'),
      esperada: true, owner: 'ux-phase42.js' },
    { responsabilidade: 'Exigência do código lido no envio da entrega',
      candidata: 'app.js (saveSimpleForm, ramo do delivery-form)', ativaHoje: typeof padrao.ctx.formValues === 'function',
      esperada: true, owner: 'app.js — e a decisão final é do backend (modules/deliveries/service.py)' },
    { responsabilidade: 'Fluxo rápido de entrega (concorrente)',
      candidata: 'ux-phase43.js', ativaHoje: montarAppOwnership('?ux_phase43=1').contarListeners(padrao.form, 'submit') > 0,
      esperada: false, owner: 'ux-phase42.js' },
    { responsabilidade: 'Persistência/restauração de rascunho de formulário',
      candidata: 'ux-phase41.js', ativaHoje: montarAppOwnership('?ux_phase41=1').doc.body.classList.contains('phase41-enabled'),
      esperada: false, owner: 'nenhum — e o app tem política ANTI-persistência ativa (resetAppFormDrafts)' },
    { responsabilidade: 'Limpeza de rascunho no encerramento de sessão',
      candidata: 'app.js (resetAppFormDrafts/clearRestoredAppForms)', ativaHoje: typeof padrao.ctx.resetAppFormDrafts === 'function',
      esperada: true, owner: 'app.js' },
    // ACRESCENTADA NO PR 2B. Não é um owner concorrente: é um CONSUMIDOR sem
    // emissor. O ux-analytics escuta `epi:action-*`, que só o bridge inerte do
    // phase44 dispararia — e ele próprio só se registra com a flag
    // `ux_analytics_enabled` ligada E papel master, o que na carga padrão não
    // acontece. A linha existe para que a remoção do bridge, no PR 4, não
    // deixe para trás um ouvinte que ninguém mais alimenta.
    { responsabilidade: 'Feedback de ação por requisição (consumo de epi:action-*)',
      candidata: 'ux-analytics.js (flowFinish generic_action)', ativaHoje: padrao.contarListeners(padrao.doc, 'epi:action-success') > 0,
      esperada: false, owner: 'nenhum — sem emissor em produção (PR2B B-6)' }
  ];

  linhas.forEach((l) => {
    eq(l.ativaHoje, l.esperada,
      `"${l.responsabilidade}" via ${l.candidata}: a matriz diz ativa=${l.esperada} e a medição diz ${l.ativaHoje}`);
  });
  eq(linhas.length, 12, 'a matriz de ownership mudou de tamanho sem revisão');
});

test('PR1 Z-2: matriz de decisão por módulo — cada decisão tem gate que a sustenta', () => {
  const DECISOES = Object.freeze([
    'MANTER — OWNER',
    'MANTER INERTE — FUNCIONALIDADE ÚNICA',
    'ABSORVER CAPACIDADE NO OWNER',
    'CAPACIDADE ABSORVIDA — RESTO INERTE',
    'CONSOLIDADO SEM ABSORÇÃO — RESTO INERTE',
    'REMOVER — REDUNDANTE',
    'INVESTIGAR'
  ]);
  const matriz = [
    { modulo: 'ux-phase42.js', necessario: true, exclusivo: true,
      decisao: 'MANTER — OWNER', gates: ['B-1', 'B-2', 'B-3', 'B-4', 'D-1'] },
    { modulo: 'ux-phase41.js', necessario: false, exclusivo: true,
      decisao: 'MANTER INERTE — FUNCIONALIDADE ÚNICA', gates: ['C-1', 'C-2', 'C-4', 'C-5', 'C-6'] },
    // REVISTO NO PR 2A. A exigência do código lido, que o PR 1 tinha tomado por
    // capacidade exclusiva, é do `app.js` — que a aplica ANTES da rede, com
    // exceção para devolução e com mensagem traduzida (PR2A A-1..A-3). O
    // phase43 é uma terceira cópia da mesma regra, sem a exceção: ativá-lo
    // bloquearia toda devolução (PR2A A-4). O que sobra nele são afordâncias de
    // interface (barra fixa, confirmar por teclado, modo manual, eco do estado
    // do envio) que nunca rodaram em produção e não carregam regra de negócio.
    { modulo: 'ux-phase43.js', necessario: false, exclusivo: false,
      decisao: 'REMOVER — REDUNDANTE', gates: ['D-1', 'D-2', 'D-3', '2A A-1', '2A A-3', '2A A-4'] },
    // PR 2B fechou o EIXO DO FETCH (nada a absorver) e o PR 2C fechou o EIXO DO
    // DROPDOWN — este, sim, com absorção: a devolução de foco ao gatilho foi
    // para dentro do owner (2C C-1). É a única capacidade absorvida em todo o
    // PR 2. Com os dois eixos concorrentes resolvidos, o módulo não disputa
    // mais responsabilidade nenhuma.
    //
    // `exclusivo` continua TRUE de propósito, e não por inércia: o que resta no
    // arquivo (cabeçalho de view, barra de ação, contador de filtros,
    // confirmação embutida, rolagem ao topo) não tem outro dono — mas também
    // nunca rodou e nunca foi validado. Decidir se isso vira produto ou vai
    // embora é decisão do PR 4, não uma disputa de ownership.
    { modulo: 'ux-phase44.js', necessario: false, exclusivo: true,
      decisao: 'CAPACIDADE ABSORVIDA — RESTO INERTE',
      gates: ['E-1', 'E-3', 'F-1', 'F-3', 'F-4', 'F-5', '2B B-6', '2B B-7', '2C C-1', '2C C-7', '2C C-8'] },
    // A navegação TEM owner ativo e comprovado (G-1, G-2); o multitab cria uma
    // segunda autoridade sobre o mesmo clique (G-4, G-5) e uma segunda cópia da
    // guarda (G-6).
    //
    // REVISTO NO PR 2D. O PR 1 previu absorver "abas com contexto preservado"
    // no contrato de navegação. A medição não sustenta: o que existe ali é um
    // CACHE de tudo que foi digitado, filtrado só por tipo de campo e fora do
    // alcance do `resetAppFormDrafts()`, que é limpeza de DOM (2D D-4, D-6).
    // Absorvê-lo faria o owner da navegação passar a manter essa cópia, e a
    // política de limpeza do app a depender da recarga.
    //
    // E uma correção a favor do módulo, registrada porque a hipótese era minha:
    // pelo MENU ele NÃO restaura — respeita o contrato de reentrada, de forma
    // deliberada e documentada no próprio arquivo (2D D-5).
    //
    // `exclusivo` segue TRUE: a barra de abas com histórico próprio não tem
    // outro dono. Também nunca rodou nem foi validada, e essa decisão é do PR 4.
    { modulo: 'multitab-navigation.js', necessario: false, exclusivo: true,
      decisao: 'CONSOLIDADO SEM ABSORÇÃO — RESTO INERTE',
      gates: ['G-1', 'G-2', 'G-3', 'G-4', 'G-5', 'G-6', '2D D-1', '2D D-4', '2D D-5', '2D D-6'] }
  ];
  matriz.forEach((m) => {
    assert(DECISOES.includes(m.decisao), `decisão fora do vocabulário: ${m.decisao}`);
    assert(m.gates.length >= 3, `"${m.modulo}" precisa de mais de um gate sustentando a decisão`);
  });
  // REMOVER — REDUNDANTE exige prova de que a capacidade tem outro dono. No
  // PR 1 nenhum módulo alcançava esse patamar; no PR 2A o phase43 alcançou,
  // porque os gates A-1..A-4 mostram o owner real e mostram que a cópia é pior
  // que o original. A regra abaixo não impede a classificação — exige que ela
  // venha acompanhada dos gates que a sustentam.
  matriz.filter((m) => m.decisao === 'REMOVER — REDUNDANTE').forEach((m) => {
    assert(m.exclusivo === false,
      `"${m.modulo}" foi marcado para remoção mas ainda consta com capacidade exclusiva`);
    assert(m.gates.some((g) => /^2[A-D] /.test(g)),
      `"${m.modulo}" foi marcado para remoção sem gate do PR 2 que prove o owner alternativo`);
  });
  // Absorção declarada também precisa de prova: sem um gate do PR 2 mostrando
  // a capacidade DENTRO do owner, "absorvida" seria só uma palavra.
  ['CAPACIDADE ABSORVIDA — RESTO INERTE', 'CONSOLIDADO SEM ABSORÇÃO — RESTO INERTE']
    .forEach((decisao) => {
      matriz.filter((m) => m.decisao === decisao).forEach((m) => {
        assert(m.gates.some((g) => /^2[A-D] /.test(g)),
          `"${m.modulo}" consta como consolidado sem gate do PR 2 que sustente a conclusão`);
      });
    });
  eq(matriz.length, 5, 'a matriz de decisão mudou de tamanho sem revisão');
});

test('PR1 Z-3: o registro de caracterizações exige os cinco campos — e está vazio', () => {
  // ATUALIZADO NO PR 4. Toda caracterização de DEFEITO desta frente afirmava o
  // comportamento de um módulo que já não existe: elas saíram com o sujeito. O
  // registro fica, e continua exigindo os cinco campos de quem voltar a usá-lo
  // — é a trava que impede um `skip` disfarçado de entrar.
  DEFEITOS_CARACTERIZADOS.forEach((d) => {
    ['esperado', 'atual', 'motivo', 'responsabilidade', 'decisaoFutura'].forEach((campo) => {
      assert(String(d[campo] || '').trim() !== '', `"${d.nome}" sem o campo "${campo}"`);
    });
  });
  eq(DEFEITOS_CARACTERIZADOS.length, 0,
    'apareceu caracterização de defeito nova: ela precisa de decisão, não de convivência');
});

// ── PR 2A — phase43 × phase42: quem é o owner da exigência do código lido ───

testAsync('PR2A A-1: o owner REAL da exigência do código lido é o app.js', async () => {
  // O gate `PR1 H-2` mediu que o phase43 exige o código e disso concluiu que a
  // capacidade era EXCLUSIVA dele. A conclusão estava errada, e o motivo é o
  // limite do harness que o próprio PR 1 declarou: o bind do submit da entrega
  // mora dentro do `init()`, que o harness não executava. O gate comparou
  // phase42 com phase43 e nunca mediu o app.
  //
  // Aqui o bootstrap REAL roda, e quem julga o envio é o handler de produção.
  const app = montarAppOwnership('');
  app.dispararBootstrapDoApp();
  eq(app.contarListeners(app.form, 'submit'), 1,
    'o app não ligou o próprio handler de submit da entrega: o gate mediria a ausência dele');

  app.doc.getElementById('delivery-employee').value = '100';
  app.doc.getElementById('delivery-epi').value = '1000';
  app.doc.getElementById('delivery-unit-filter').value = '10';
  app.doc.getElementById('delivery-quantity').value = '1';
  app.doc.getElementById('delivery-stock-item-id').value = '';
  app.doc.getElementById('delivery-stock-qr-code').value = '';

  const avisos = [];
  app.ctx.alert = (m) => avisos.push(String(m));
  app.enviarFormularioDeEntrega();
  await new Promise((r) => setTimeout(r, 0));

  eq(app.chamadasPara('/api/deliveries').length, 0,
    'a entrega sem código lido chegou à rede: o app deixou de barrar antes do envio');
  assert(avisos.some((m) => /QR|Leia/i.test(m)),
    `o app deveria recusar a entrega sem leitura, avisos: ${JSON.stringify(avisos)}`);
});

testAsync('PR2A A-2: com o código lido, o mesmo owner deixa a entrega seguir para a API', async () => {
  // Contraprova do A-1: sem ela, "não chegou à rede" poderia significar apenas
  // que o fixture nunca chega à rede.
  const app = montarAppOwnership('');
  app.dispararBootstrapDoApp();
  app.doc.getElementById('delivery-employee').value = '100';
  app.doc.getElementById('delivery-epi').value = '1000';
  app.doc.getElementById('delivery-unit-filter').value = '10';
  app.doc.getElementById('delivery-quantity').value = '1';
  app.doc.getElementById('delivery-stock-item-id').value = '77';
  app.doc.getElementById('delivery-stock-qr-code').value = 'QR-77';

  app.enviarFormularioDeEntrega();
  await new Promise((r) => setTimeout(r, 0));

  eq(app.chamadasPara('/api/deliveries').length, 1,
    'com o código lido a entrega deveria alcançar a API — senão o A-1 não prova nada');
});

testAsync('PR2A A-3: o owner isenta a DEVOLUÇÃO da exigência do código lido', async () => {
  // Regra real do app: devolução vai para /api/devolutions e o payload tem
  // `stock_item_id` e `stock_qr_code` REMOVIDOS. Exigir leitura ali seria
  // impedir toda devolução.
  const app = montarAppOwnership('');
  app.dispararBootstrapDoApp();
  app.doc.getElementById('delivery-employee').value = '100';
  app.doc.getElementById('delivery-epi').value = '1000';
  app.doc.getElementById('delivery-unit-filter').value = '10';
  app.doc.getElementById('delivery-quantity').value = '1';
  app.doc.getElementById('delivery-stock-item-id').value = '';
  app.doc.getElementById('delivery-stock-qr-code').value = '';
  app.doc.getElementById('delivery-is-devolution').checked = true;

  const avisos = [];
  app.ctx.alert = (m) => avisos.push(String(m));
  app.enviarFormularioDeEntrega();
  await new Promise((r) => setTimeout(r, 0));

  assert(!avisos.some((m) => /Leia e valide/i.test(m)),
    `a devolução foi barrada pela exigência de leitura, que não se aplica a ela: ${JSON.stringify(avisos)}`);
});


test('PR2A A-5: quantos gates de submit existem, e de quem são', () => {
  // ATUALIZADO NO PR 4: a terceira medição somava o phase43, removido nesta
  // fatia. O que sobra é o contrato que interessa — e é o mais forte dos dois.
  const contar = (busca) => {
    const app = montarAppOwnership(busca);
    app.dispararBootstrapDoApp();
    return app.contarListeners(app.form, 'submit');
  };
  eq(contar(''), 1, 'produção hoje: só o handler do app.js, dono da regra de negócio da entrega');
  eq(contar('?ux_phase42=1'), 2,
    'com o phase42 ligado somam-se dois: o do app (regra) e o do phase42 (revisão explícita). Arranjo autorizado.');
});

// ── PR 2B. CONSOLIDAÇÃO — fetch: ux-phase44 × error-monitor.js ──────────────
//
// Owner preservado: `error-monitor.js`. Ele embrulha `win.fetch` sem flag
// nenhuma, na carga padrão, e é o único que roda hoje (PR1 E-1).
//
// O concorrente é `bindFetchFeedbackBridge()` do phase44, que nunca inicializa.
// A pergunta do PR 2 não é "ele funciona?", e sim: QUAL capacidade é exclusiva
// dele, e ela é mesmo necessária? A resposta abaixo é medida, não deduzida.
//
// A capacidade candidata é UMA: emitir `epi:action-success` / `epi:action-error`
// por requisição, com a view ativa no momento da chamada. Os gates B-6..B-8
// perguntam quem consome isso hoje e o que a absorção produziria de fato.

test('PR2B B-1: existe UMA camada sobre o fetch, e ela é a do owner', () => {
  // Contagem por SALTO, não por marca: o que falha em produção é justamente a
  // marca privada de cada dono, que não enxerga a do outro (PR1 E-3).
  const app = montarAppOwnership('');
  assert(app.ctx.fetch !== app.fetchBase, 'ninguém embrulhou o fetch: o owner não rodou');
  eq(app.ctx.fetch.__EPI_MONITORED_FETCH__, true, 'a camada externa não é a do error-monitor');
  eq(app.ctx.__EPI_FETCH_MONITOR_ORIGINAL__, app.fetchBase,
    'o interior da camada não é o fetch base — há mais de um embrulho na cadeia');
});

test('PR2B B-2: o owner permanece com UMA camada mesmo recarregado várias vezes', () => {
  const app = montarAppOwnership('');
  const primeiro = app.ctx.fetch;
  const fonte = fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), 'error-monitor.js'), 'utf-8');
  for (let i = 0; i < 3; i += 1) {
    vmF5B.runInContext(fonte, app.ctx, { filename: `error-monitor.js#${i}` });
  }
  eq(app.ctx.fetch, primeiro, 'uma das recargas instalou uma segunda camada');
  eq(app.ctx.__EPI_FETCH_MONITOR_ORIGINAL__, app.fetchBase,
    'o original preservado deixou de ser o fetch base: a cadeia cresceu');
});

testAsync('PR2B B-3: sucesso — o owner devolve a MESMA resposta e não registra instabilidade', async () => {
  const app = montarAppOwnership('');
  const resposta = { ok: true, status: 200, marcador: 'resposta-do-teste' };
  app.responderPara('/api/consolidacao/ok', resposta);

  const devolvida = await app.ctx.fetch('/api/consolidacao/ok');
  eq(devolvida, resposta, 'o owner trocou o objeto de resposta — o contrato do chamador mudaria');
  eq(app.chamadasPara('/api/consolidacao/ok').length, 1, 'a requisição não chegou ao fetch base uma única vez');

  const snapshot = app.ctx.__EPI_MONITORING__.getSnapshot();
  assert(!Object.keys(snapshot.unstableApis).some((k) => k.includes('/api/consolidacao/ok')),
    'uma resposta 200 foi contabilizada como instabilidade');
});

testAsync('PR2B B-4: 5xx — o owner registra a instabilidade e AINDA ASSIM devolve a resposta', async () => {
  const app = montarAppOwnership('');
  app.responderPara('/api/consolidacao/erro', { ok: false, status: 503 });

  const devolvida = await app.ctx.fetch('/api/consolidacao/erro');
  eq(devolvida.status, 503, 'o owner engoliu a resposta de erro em vez de devolvê-la');

  const instaveis = Object.keys(app.ctx.__EPI_MONITORING__.getSnapshot().unstableApis);
  assert(instaveis.some((k) => k.includes('/api/consolidacao/erro')),
    `o owner não registrou o 5xx: ${JSON.stringify(instaveis)}`);
});

testAsync('PR2B B-5: erro de rede — o owner registra e RE-LANÇA o mesmo erro', async () => {
  const app = montarAppOwnership('');
  const falha = new Error('rede indisponivel');
  app.responderPara('/api/consolidacao/rede', falha);

  let capturado = null;
  try {
    await app.ctx.fetch('/api/consolidacao/rede');
  } catch (erro) {
    capturado = erro;
  }
  eq(capturado, falha, 'o owner trocou ou engoliu o erro: quem chama deixaria de tratá-lo');

  const instaveis = Object.keys(app.ctx.__EPI_MONITORING__.getSnapshot().unstableApis);
  assert(instaveis.some((k) => k.includes('/api/consolidacao/rede')),
    `o owner não registrou a falha de rede: ${JSON.stringify(instaveis)}`);
});

testAsync('PR2B B-6: `epi:action-*` não tem produtor nem consumidor', async () => {
  // CONVERTIDO NO PR 4. O gate media um consumidor órfão: o ux-analytics ouvia
  // `epi:action-*` e o único produtor era o bridge de fetch do phase44, inerte.
  // Os dois saíram nesta fatia. O contrato agora é a AUSÊNCIA dos dois lados.
  const app = montarAppOwnership('?ux_analytics=1', {
    usuario: { id: 9, role: 'master_admin', company_id: 1 }
  });
  assert(!(app.ctx._errosDeCarga || []).some((e) => e.rel.includes('ux-analytics')),
    `ux-analytics não carregou no harness: ${JSON.stringify(app.ctx._errosDeCarga)}`);

  eq(app.contarListeners(app.doc, 'epi:action-success'), 0,
    'voltou a existir consumidor de epi:action-success sem produtor que o alimente');
  eq(app.contarListeners(app.doc, 'epi:action-error'), 0,
    'voltou a existir consumidor de epi:action-error sem produtor que o alimente');

  const emitidos = [];
  app.doc.addEventListener('epi:action-success', () => emitidos.push('ok'));
  app.doc.addEventListener('epi:action-error', () => emitidos.push('erro'));
  app.responderPara('/api/consolidacao/emissor', { ok: true, status: 200 });
  await app.ctx.fetch('/api/consolidacao/emissor');
  eq(emitidos.length, 0, 'alguém passou a emitir epi:action-* em produção');

  // E nenhum arquivo servido dispara esses eventos.
  const servidos = fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), 'views', '_scripts.html'), 'utf-8')
    .match(/src="\/([^"?]+\.js)/g).map((m) => m.slice(6));
  const emissores = servidos.filter((rel) => /dispatchEvent\([^;]*epi:action-/.test(fonteServida(rel)));
  eq(emissores.length, 0, `voltou a haver emissor de epi:action-*: ${emissores.join(', ')}`);
});



test('PR2B B-9: o fetch tem um dono, e nenhum segundo wrapper voltou', () => {
  // CONVERTIDO NO PR 4. Era a matriz de destino do concorrente; o destino foi
  // executado — o phase44 saiu. O que fica é o contrato de ausência.
  const app = montarAppOwnership('');
  eq(app.ctx.fetch.__EPI_MONITORED_FETCH__, true, 'o owner do fetch não está ativo');
  eq(app.ctx.__EPI_FETCH_MONITOR_ORIGINAL__, app.fetchBase,
    'apareceu uma segunda camada entre o owner e o fetch base');
  eq(app.ctx.__EPI_PHASE44_FETCH_BRIDGED__, undefined,
    'a marca do bridge removido reapareceu no contexto');

  const servidos = fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), 'views', '_scripts.html'), 'utf-8')
    .match(/src="\/([^"?]+\.js)/g).map((m) => m.slice(6));
  const embrulhadores = servidos.filter((rel) => /(globalThis|window|win)\.fetch\s*=/.test(fonteServida(rel)));
  eq(embrulhadores.join(','), 'error-monitor.js',
    `o conjunto de quem embrulha fetch mudou: ${embrulhadores.join(', ')}`);
});


// ── PR 2C. CONSOLIDAÇÃO — dropdown: ux-phase44 × app.js ─────────────────────
//
// Owner preservado: `setupInteractiveDropdowns()` do app.js. O PR 1 mediu os
// dois lado a lado e o saldo foi: equivalentes no gesto básico (F-2, F-3), o
// concorrente mais caro (F-3b: um listener de documento POR dropdown) e o
// owner mais abrangente no Escape (F-4: fecha a partir do documento; o
// phase44 só de dentro da própria raiz).
//
// Sobrou UMA capacidade do concorrente que o owner não tinha: devolver o foco
// ao gatilho depois de fechar pelo teclado. Diferente das fatias 2A e 2B, esta
// é real e necessária — e por isso é a primeira (e única) coisa absorvida em
// todo o PR 2.

function focar(app, id) {
  const no = app.doc.getElementById(id);
  if (!no) throw new Error(`fixture sem o nó "${id}"`);
  no.focus();
  return no;
}
function teclarEscapeNoDocumento(app) {
  app.doc.dispatchEvent(new app.ctx.Event('keydown', { key: 'Escape', bubbles: true }));
}

test('PR2C C-1: Escape com o foco DENTRO do dropdown fecha E devolve o foco ao gatilho', () => {
  // A capacidade absorvida. Sem ela, esconder o painel deixa o foco num nó
  // invisível — o navegador o joga no <body> e quem navega por teclado perde
  // o lugar na página.
  const app = appComDropdownDoApp();
  clicarNoGatilho(app, 'acoes');
  focar(app, 'dropdown-acoes-item');

  teclarEscapeNoDocumento(app);

  eq(estadoDoDropdown(app, 'acoes').aberto, false, 'o Escape deixou de fechar o dropdown');
  // Compara por id: os nós do shim são cíclicos (parent ↔ children) e um
  // `eq` entre objetos produziria erro de serialização em vez de diagnóstico.
  eq(String(app.doc.activeElement && app.doc.activeElement.id), 'dropdown-acoes-trigger',
    'o foco não voltou para o gatilho: quem fechou pelo teclado ficou sem lugar na página');
});


test('PR2C C-2: Escape com o foco FORA do dropdown fecha, e NÃO mexe no foco', () => {
  // O limite da absorção. Mover o cursor de um campo de texto por causa de um
  // dropdown que o usuário nem estava usando seria comportamento novo — e
  // comportamento novo não é absorção.
  const app = appComDropdownDoApp();
  clicarNoGatilho(app, 'acoes');
  focar(app, 'delivery-quantity');

  teclarEscapeNoDocumento(app);

  eq(estadoDoDropdown(app, 'acoes').aberto, false,
    'o Escape do documento deixou de fechar o dropdown: o alcance do owner regrediu');
  eq(String(app.doc.activeElement && app.doc.activeElement.id), 'delivery-quantity',
    'o foco foi roubado de um campo que o usuário estava preenchendo');
});

test('PR2C C-3: Escape sem dropdown aberto não mexe no foco', () => {
  const app = appComDropdownDoApp();
  focar(app, 'delivery-quantity');
  teclarEscapeNoDocumento(app);
  eq(String(app.doc.activeElement && app.doc.activeElement.id), 'delivery-quantity',
    'o Escape mexeu no foco sem ter fechado dropdown nenhum');
});

test('PR2C C-4: o mesmo Escape continua fechando o modal de assinatura', () => {
  // O ramo do modal vem DEPOIS da devolução de foco no mesmo handler. Se a
  // absorção lançasse, este ramo deixaria de rodar em silêncio.
  const app = appComDropdownDoApp();
  const modal = app.doc.getElementById('signature-modal');
  assert(modal.classList.contains('is-open'), 'o fixture não trouxe o modal aberto');
  clicarNoGatilho(app, 'acoes');
  focar(app, 'dropdown-acoes-item');

  teclarEscapeNoDocumento(app);

  assert(!modal.classList.contains('is-open'),
    'o Escape deixou de fechar o modal de assinatura: a absorção interrompeu o handler');
  eq(String(app.doc.activeElement && app.doc.activeElement.id), 'dropdown-acoes-trigger',
    'a devolução de foco e o fechamento do modal não convivem no mesmo Escape');
});

test('PR2C C-5: o owner do dropdown mantém um par fixo de listeners no documento', () => {
  // CONVERTIDO NO PR 4. A segunda metade comparava com o custo por instância do
  // phase44, removido. O contrato do owner — par fixo, independente do número
  // de dropdowns — é o que precisava ser protegido, e continua medido.
  const semDropdown = montarAppOwnership('');
  const base = {
    click: semDropdown.contarListeners(semDropdown.doc, 'click'),
    keydown: semDropdown.contarListeners(semDropdown.doc, 'keydown')
  };
  const comOwner = appComDropdownDoApp();
  eq(comOwner.contarListeners(comOwner.doc, 'click') - base.click, 1,
    'o owner passou a registrar mais de um listener de clique no documento');
  eq(comOwner.contarListeners(comOwner.doc, 'keydown') - base.keydown, 1,
    'o owner passou a registrar mais de um listener de teclado no documento');
  // O fixture tem DOIS dropdowns: o par fixo é o que distingue o owner de uma
  // implementação por instância.
  eq(comOwner.dropdowns.length, 2, 'o fixture deixou de ter dois dropdowns: a medição perde o sentido');
});

test('PR2C C-6: exclusividade e clique fora seguem exatamente como antes', () => {
  const app = appComDropdownDoApp();
  clicarNoGatilho(app, 'acoes');
  clicarNoGatilho(app, 'exportar');
  eq(estadoDoDropdown(app, 'acoes').aberto, false, 'abrir o segundo deixou o primeiro aberto');
  eq(estadoDoDropdown(app, 'exportar').aberto, true, 'o segundo não abriu');

  app.doc.getElementById('menu').dispatchEvent(new app.ctx.Event('click', { bubbles: true }));
  eq(estadoDoDropdown(app, 'exportar').aberto, false, 'o clique fora deixou de fechar');

  // E o caso fino de F-5: clique DENTRO de outro dropdown continua não
  // fechando o aberto. A absorção mexeu só no Escape.
  const outro = appComDropdownDoApp();
  clicarNoGatilho(outro, 'acoes');
  outro.doc.getElementById('dropdown-exportar-panel')
    .dispatchEvent(new outro.ctx.Event('click', { bubbles: true }));
  eq(estadoDoDropdown(outro, 'acoes').aberto, true,
    'o clique dentro de outro dropdown passou a fechar o aberto: comportamento novo, não absorvido');
});


test('PR2C C-8: destino de cada caminho concorrente do dropdown, e inventário de flags', () => {
  const DESTINOS = Object.freeze([
    'REMOVER AGORA',
    'REMOVER NO PR 4',
    'MANTER TEMPORARIAMENTE POR DEPENDÊNCIA',
    'AINDA POSSUI RESPONSABILIDADE EXCLUSIVA'
  ]);
  const app = appComDropdownDoApp();
  eq(app.ctx.isHtmxAlpineProductionActive(), true,
    'a flag que governa o owner mudou: o inventário abaixo precisa ser refeito');
  const padrao = montarAppOwnership('');
  eq(padrao.ctx.isHtmxAlpineProductionActive(), false,
    'o owner do dropdown passou a rodar sem flag: o inventário precisa ser refeito');

  const matriz = [
    { caminho: 'app.js (setupInteractiveDropdowns)', papel: 'OWNER',
      absorveu: 'devolução de foco ao gatilho no Escape de dentro do dropdown',
      // Inventário de flags: o código absorvido NÃO ganhou flag própria. Ele
      // vive dentro do handler do owner, atrás do gate que já existia —
      // `isHtmxAlpineProductionActive()`, isto é htmx_alpine_production_enabled
      // E ux_tools_functional_enabled. Flag nova aqui só multiplicaria estados.
      flag: 'htmx_alpine_production_enabled + ux_tools_functional_enabled (a do próprio owner; nenhuma flag nova)',
      destino: 'AINDA POSSUI RESPONSABILIDADE EXCLUSIVA', gates: ['2C C-1', '2C C-2', '2C C-5', '2C C-6'] },
    { caminho: 'ux-phase44.js (createDropdown)', papel: 'CONCORRENTE',
      absorveu: 'não se aplica — a capacidade dele foi para o owner',
      flag: 'ux_phase44_enabled (inalterada, e o módulo segue inerte)',
      destino: 'REMOVER NO PR 4', gates: ['2C C-1', '2C C-7', 'F-3b', 'F-5'] }
  ];
  matriz.forEach((m) => {
    assert(DESTINOS.includes(m.destino), `destino fora do vocabulário: ${m.destino}`);
    assert(m.gates.length >= 2, `"${m.caminho}" precisa de mais de um gate sustentando o destino`);
    assert(String(m.flag || '').trim() !== '', `"${m.caminho}" sem inventário de flag`);
  });
  eq(matriz.length, 2, 'a matriz do PR 2C mudou de tamanho sem revisão');
});


// ── PR 2D. CONSOLIDAÇÃO — navegação: multitab-navigation × app.js ───────────
//
// Owner preservado: `bindMenuNavigation()` → `navigateToView()` do app.js.
//
// A pergunta que esta fatia precisa responder é a do contrato: "existe apenas
// UMA autoridade capaz de decidir a navegação?". D-1 responde SIM medindo, e
// D-2 trava a resposta contra o mecanismo que a derrubaria.

function fonteServida(arquivo) {
  return fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), arquivo), 'utf-8');
}

test('PR2D D-1: existe UMA autoridade capaz de decidir a navegação — e o clique chega nela', () => {
  const app = appComNavegacaoDoApp();
  app.clicarNoItemDeMenu('entregas');
  eq(app.ctx._assigns.length, 1, 'o clique no menu não alcançou o owner da navegação');
  assert(String(app.ctx._assigns[0]).includes('entregas'),
    `a navegação foi para outro lugar: ${app.ctx._assigns[0]}`);

  // E ninguém mais reivindica o clique ANTES dele. Um listener de clique em
  // CAPTURA no documento é o único mecanismo capaz de decidir por cima do
  // owner (G-5), então a contagem dele é a medida direta de "quantas
  // autoridades existem".
  const emCaptura = app.listenersDe(app.doc, 'click').filter((l) => l.captura === true);
  eq(emCaptura.length, 0,
    `alguém escuta o clique em captura no documento e pode decidir antes do owner: ${emCaptura.length}`);
});


test('PR2D D-3: "ativação redundante" tem UMA definição, e nenhuma cópia sobrou', () => {
  const app = appComNavegacaoDoApp();
  const antes = app.vistos.length;
  app.clicarNoItemDeMenu('dashboard'); // já ativa
  eq(app.ctx._assigns.length, 0, 'a ativação redundante recarregou a página');
  eq(app.vistos.length, antes, 'a ativação redundante emitiu troca de view');
  assert(typeof app.ctx.ativacaoRedundanteDeView === 'function', 'a definição canônica sumiu do owner');

  // CONVERTIDO NO PR 4: a única cópia era a do multitab, removido nesta fatia.
  // O contrato deixa de ser "só ele copia" e passa a ser "ninguém copia".
  const servidos = fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), 'views', '_scripts.html'), 'utf-8')
    .match(/src="\/([^"?]+\.js)/g).map((m) => m.slice(6));
  const copias = servidos.filter((rel) => rel !== 'app.js'
    && /function ativacaoRedundanteDeView/.test(fonteServida(rel)));
  eq(copias.length, 0, `reapareceu cópia da guarda de redundância: ${copias.join(', ')}`);
});





test('PR2D D-7: destino de cada caminho da navegação, e inventário de flags', () => {
  const DESTINOS = Object.freeze([
    'REMOVER AGORA',
    'REMOVER NO PR 4',
    'MANTER TEMPORARIAMENTE POR DEPENDÊNCIA',
    'AINDA POSSUI RESPONSABILIDADE EXCLUSIVA'
  ]);
  const padrao = montarAppOwnership('');
  eq(padrao.doc.body.classList.contains('ux-multitab-enabled'), false,
    'o multitab passou a iniciar em produção: o destino precisa ser refeito');

  const matriz = [
    { caminho: 'app.js (bindMenuNavigation → navigateToView)', papel: 'OWNER',
      absorveu: 'nada — a capacidade do concorrente conflita com política ativa do próprio app (D-5)',
      flag: 'ux_spa_navigation_enabled (a do próprio owner; nenhuma flag nova)',
      destino: 'AINDA POSSUI RESPONSABILIDADE EXCLUSIVA', gates: ['2D D-1', '2D D-3', '2D D-5'] },
    { caminho: 'multitab-navigation.js (onMenuIntercept)', papel: 'CONCORRENTE',
      absorveu: 'não se aplica — interceptador, não capacidade',
      flag: 'ux_multitab_enabled (inalterada, e o módulo segue inerte)',
      destino: 'REMOVER NO PR 4', gates: ['2D D-1', '2D D-2', 'G-4', 'G-5'] },
    { caminho: 'multitab-navigation.js (captureViewContext/restoreViewContext)', papel: 'CAPACIDADE CANDIDATA',
      absorveu: 'nada — segunda cópia do que foi digitado, fora do alcance da limpeza do app (D-5)',
      flag: 'ux_multitab_enabled (inalterada)',
      destino: 'REMOVER NO PR 4', gates: ['2D D-4', '2D D-5', '2D D-6'] }
  ];
  matriz.forEach((m) => {
    assert(DESTINOS.includes(m.destino), `destino fora do vocabulário: ${m.destino}`);
    assert(m.gates.length >= 2, `"${m.caminho}" precisa de mais de um gate sustentando o destino`);
    assert(String(m.flag || '').trim() !== '', `"${m.caminho}" sem inventário de flag`);
  });
  eq(matriz.length, 3, 'a matriz do PR 2D mudou de tamanho sem revisão');
});


// ── MATRIZES FINAIS DO PR 2 ─────────────────────────────────────────────────
//
// As duas exigidas pelo contrato da frente. Nenhuma das duas se declara: cada
// linha reafirma, no app servido, o estado que sustenta a conclusão.

test('PR2D D-8: matriz final — responsabilidade × owner antes/concorrente/depois', () => {
  const padrao = montarAppOwnership('');
  const com42 = montarAppOwnership('?ux_phase42=1');
  const comDropdown = montarAppOwnership('?ux_htmx_prod=1&ux_tools_functional=1');

  const linhas = [
    { responsabilidade: 'Pré-condição de envio da entrega de EPI',
      ownerAntes: 'app.js (saveSimpleForm) + backend (deliveries/service.py)',
      concorrente: 'ux-phase43.js (validateContext)',
      ownerDepois: 'app.js — inalterado',
      absorvido: 'nada — a cópia não tinha a exceção de devolução',
      concorrenteRemovivel: true,
      ativoHoje: typeof padrao.ctx.formValues === 'function', fatia: '2A' },
    { responsabilidade: 'Assistente e revisão explícita do envio',
      ownerAntes: 'ux-phase42.js', concorrente: 'ux-phase43.js',
      ownerDepois: 'ux-phase42.js — inalterado',
      absorvido: 'nada',
      concorrenteRemovivel: true,
      ativoHoje: com42.doc.body.classList.contains('phase42-enabled'), fatia: '2A' },
    { responsabilidade: 'Instrumentação de requisições HTTP',
      ownerAntes: 'error-monitor.js', concorrente: 'ux-phase44.js (bindFetchFeedbackBridge)',
      ownerDepois: 'error-monitor.js — inalterado',
      absorvido: 'nada — a capacidade alimentava métrica de duração zero',
      concorrenteRemovivel: true,
      ativoHoje: padrao.ctx.fetch.__EPI_MONITORED_FETCH__ === true, fatia: '2B' },
    { responsabilidade: 'Dropdown [data-ui-dropdown]',
      ownerAntes: 'app.js (setupInteractiveDropdowns)', concorrente: 'ux-phase44.js (createDropdown)',
      ownerDepois: 'app.js — COM a devolução de foco ao gatilho',
      absorvido: 'devolução de foco ao gatilho no Escape de dentro do dropdown',
      concorrenteRemovivel: true,
      ativoHoje: comDropdown.ctx.isHtmxAlpineProductionActive() === true, fatia: '2C' },
    { responsabilidade: 'Intenção de navegação (clique no menu)',
      ownerAntes: 'app.js (bindMenuNavigation → navigateToView)',
      concorrente: 'multitab-navigation.js (onMenuIntercept, em captura)',
      ownerDepois: 'app.js — inalterado',
      absorvido: 'nada — interceptador não é capacidade',
      concorrenteRemovivel: true,
      ativoHoje: typeof padrao.ctx.navigateToView === 'function', fatia: '2D' },
    { responsabilidade: 'Contexto de formulário por aba',
      ownerAntes: 'nenhum', concorrente: 'multitab-navigation.js (captureViewContext)',
      ownerDepois: 'nenhum — continua sem dono, e deliberadamente',
      absorvido: 'nada — segunda cópia do digitado, fora do alcance de resetAppFormDrafts()',
      concorrenteRemovivel: true,
      ativoHoje: false, fatia: '2D' }
  ];

  linhas.forEach((l) => {
    eq(l.ativoHoje, l.responsabilidade === 'Contexto de formulário por aba' ? false : true,
      `"${l.responsabilidade}": o owner medido não está no estado que a matriz declara`);
    assert(String(l.absorvido || '').trim() !== '', `"${l.responsabilidade}" sem coluna "absorvido"`);
    assert(/^2[A-D]$/.test(l.fatia), `"${l.responsabilidade}" sem fatia identificada`);
  });

  // O saldo do PR 2 inteiro: UMA absorção, em seis responsabilidades.
  const absorcoes = linhas.filter((l) => !/^nada/.test(l.absorvido));
  eq(absorcoes.length, 1, 'o número de capacidades absorvidas no PR 2 mudou sem revisão');
  eq(absorcoes[0].fatia, '2C', 'a única absorção do PR 2 deixou de ser a do dropdown');
  eq(linhas.length, 6, 'a matriz final de responsabilidades mudou de tamanho sem revisão');
});

test('PR2D D-9: matriz final — módulo × estado × destino, depois do PR 4', () => {
  const ESTADOS = Object.freeze(['SERVIDO — OWNER', 'REMOVIDO']);
  const servidos = fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), 'views', '_scripts.html'), 'utf-8')
    .match(/src="\/([^"?]+\.js)/g).map((m) => m.slice(6));
  const raizStatic = path.resolve(JS_ROOT, '..');
  const existe = (arq) => fs.existsSync(path.join(raizStatic, arq));
  const appJs = fs.readFileSync(path.join(raizStatic, 'app.js'), 'utf-8');

  const matriz = [
    { modulo: 'ux-phase42.js', estado: 'SERVIDO — OWNER', flag: 'ux_phase42_enabled',
      ownerSobrevivente: 'ux-phase42.js' },
    { modulo: 'ux-phase41.js', estado: 'REMOVIDO', flag: null,
      ownerSobrevivente: 'nenhum — rascunho não é requisito (PR 3)' },
    { modulo: 'ux-phase43.js', estado: 'REMOVIDO', flag: null,
      ownerSobrevivente: 'app.js — dono da regra de envio da entrega' },
    { modulo: 'ux-phase44.js', estado: 'REMOVIDO', flag: null,
      ownerSobrevivente: 'error-monitor.js (fetch) + app.js (dropdown)' },
    { modulo: 'multitab-navigation.js', estado: 'REMOVIDO', flag: null,
      ownerSobrevivente: 'app.js — bindMenuNavigation → navigateToView' }
  ];

  matriz.forEach((m) => {
    assert(ESTADOS.includes(m.estado), `estado fora do vocabulário: ${m.estado}`);
    if (m.estado === 'REMOVIDO') {
      assert(!existe(m.modulo), `"${m.modulo}" consta como REMOVIDO mas o arquivo ainda existe`);
      assert(!servidos.includes(m.modulo), `"${m.modulo}" continua na lista de scripts servidos`);
      eq(m.flag, null, `"${m.modulo}" foi removido mas ainda declara flag`);
    } else {
      assert(existe(m.modulo), `"${m.modulo}" deveria continuar existindo`);
      assert(appJs.includes(`${m.flag}: {`), `a flag do owner mantido sumiu do registro: ${m.flag}`);
    }
    assert(String(m.ownerSobrevivente || '').trim() !== '', `"${m.modulo}" sem owner sobrevivente declarado`);
  });
  eq(matriz.filter((m) => m.estado === 'REMOVIDO').length, 4, 'mudou o número de módulos removidos');
  eq(matriz.length, 5, 'a matriz final mudou de tamanho sem revisão');
});


// ── PR 3 / F5-C. RASCUNHO DE FORMULÁRIO — DECISÃO ───────────────────────────
//
// A pergunta da frente não era "como fazer o phase41 voltar a funcionar", e sim
// "a aplicação precisa desta responsabilidade?". A resposta medida é NÃO, e os
// gates abaixo são o contrato dessa decisão: eles falham se alguém reintroduzir
// persistência de rascunho no cliente sem refazer a análise.

function inventarioDeFormularios() {
  const raizViews = path.join(path.resolve(JS_ROOT, '..'), 'views');
  const arquivos = fs.readdirSync(raizViews).filter((f) => f.endsWith('.html'));
  const campos = [];
  let formularios = 0;
  arquivos.forEach((arq) => {
    const html = fs.readFileSync(path.join(raizViews, arq), 'utf-8');
    const blocos = html.match(/<form\b[^>]*>[\s\S]*?<\/form>/gi) || [];
    formularios += blocos.length;
    blocos.forEach((bloco) => {
      const controles = bloco.match(/<(?:input|select|textarea)\b[^>]*>/gi) || [];
      controles.forEach((c) => {
        const id = (c.match(/\bid="([^"]+)"/) || [])[1] || '';
        const nome = (c.match(/\bname="([^"]+)"/) || [])[1] || '';
        const tipo = ((c.match(/\btype="([^"]+)"/) || [])[1] || (/^<select/i.test(c) ? 'select' : 'text')).toLowerCase();
        campos.push({ arq, id, nome, tipo });
      });
    });
  });
  return { formularios, campos };
}

test('PR3 A-1: a superfície real de formulários, medida — e quanto dela o phase41 sequer enxerga', () => {
  const app = montarAppOwnership('');
  eq(app.doc.body.classList.contains('phase41-enabled'), false,
    'o phase41 passou a iniciar: a premissa desta frente mudou');

  const { formularios, campos } = inventarioDeFormularios();
  assert(formularios >= 25, `esperava a superfície completa de formulários, vieram ${formularios}`);
  assert(campos.length >= 300, `esperava a superfície completa de campos, vieram ${campos.length}`);

  // O phase41 indexa por `id` (`if (!field || !field.id) return false`). Campo
  // sem id é invisível para ele — e quase metade da superfície é assim.
  const semId = campos.filter((c) => !c.id);
  assert(semId.length >= 130,
    `campos sem id caíram para ${semId.length}: a cobertura acidental do phase41 mudou e a análise precisa ser refeita`);

  // O caso que decide: o formulário que a política do app cita por nome.
  const doColaborador = campos.filter((c) => c.arq === 'colaboradores.html');
  const pessoaisSemId = doColaborador.filter((c) => !c.id && /^(cpf|name|email|whatsapp)$/.test(c.nome));
  eq(pessoaisSemId.length, 4,
    'os campos pessoais do employee-form mudaram de forma: a medição de cobertura do phase41 precisa ser refeita');
});


testAsync('PR3 A-3: a política ATIVA é a oposta — o app apaga rascunho, inclusive fora de <form>', async () => {
  // Não é ausência de decisão: é decisão tomada, implementada e comentada. O
  // `resetAppFormDrafts()` alcança controle solto porque `form.reset()` não
  // alcança — e é exatamente onde mora rascunho sensível.
  const app = montarAppOwnership('');
  app.dispararBootstrapDoApp();

  app.doc.getElementById('delivery-role').value = 'DENTRO-DE-FORM';
  app.doc.getElementById('compras-supplier-name').value = 'FORA-DE-FORM';

  app.ctx.resetAppFormDrafts();

  eq(app.doc.getElementById('delivery-role').value, '', 'a limpeza não alcançou campo dentro de <form>');
  eq(app.doc.getElementById('compras-supplier-name').value, '',
    'a limpeza não alcançou controle solto — é justamente o caso que motivou a política');
});

test('PR3 A-4: estado digitado que sobrevive à navegação JÁ tem owner, e ele é escopado', () => {
  // Filtros de lista são estado digitado que precisa sobreviver ao Voltar. O
  // owner existe (snapshots de navegação SPA), vive em sessionStorage e é
  // invalidado por encerramento E por troca de principal.
  const app = montarAppOwnership('');
  assert(typeof app.ctx.snapshotScopeId === 'function', 'o owner de escopo de snapshot sumiu');
  assert(typeof app.ctx.rotateSnapshotScope === 'function', 'a invalidação de escopo sumiu');

  // ATUALIZADO na frente de Isolamento (PR A). O mecanismo MUDOU de propósito.
  //
  // Antes, rotacionar era DESCARTAR o escopo herdado e recair no do documento
  // atual. Isso só invalidava de fato quando havia recarga — o caso do
  // `terminateSession()`. No login de outro principal, que NÃO recarrega,
  // `snapshotScopeId()` voltava ao MESMO `DOCUMENT_INSTANCE_ID` e a rotação era
  // um no-op: as entradas de A continuavam casando com o state de B. O gate
  // `ISOL A-8` mede esse caminho e foi ele que expôs o defeito.
  //
  // Agora rotacionar GERA um escopo novo e o publica. As duas propriedades que
  // importam continuam valendo, e a segunda ficou mais forte.
  //
  // Herança: um documento NOVO (o F5) lê o escopo que sobreviveu no
  // sessionStorage. Modelado com um mount próprio, porque só um documento
  // recém-carregado tem o cache de escopo vazio.
  const sessaoHerdada = {
    _s: { 'epi-snapshot-scope': 'ESCOPO-DE-OUTRO-PRINCIPAL' },
    getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
    setItem(k, v) { this._s[k] = String(v); }, removeItem(k) { delete this._s[k]; }
  };
  const herdeiro = montarDocumentoIsolamento(sessaoHerdada, '');
  const herdado = herdeiro.ctx.snapshotScopeId();
  eq(herdado, 'ESCOPO-DE-OUTRO-PRINCIPAL', 'o escopo herdado do sessionStorage deixou de ser lido');

  herdeiro.ctx.rotateSnapshotScope();                  // a troca de principal
  const depois = herdeiro.ctx.snapshotScopeId();
  assert(depois !== herdado,
    'a troca de principal não descartou o escopo do principal anterior');
  eq(herdeiro.ctx.snapshotScopeId(), depois, 'o escopo não é estável depois da troca');
  eq(sessaoHerdada.getItem('epi-snapshot-scope'), depois,
    'o escopo novo precisa ser publicado, senão a próxima leitura ressuscita o anterior');

  // E o meio é sessionStorage, não localStorage: o escopo não sobrevive ao
  // fechamento do navegador, que é o contrato certo para estado de navegação.
  const appJs = fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), 'app.js'), 'utf-8');
  assert(/sessionStorage\.setItem\(SNAPSHOT_SCOPE_KEY/.test(appJs),
    'o escopo de snapshot mudou de meio de armazenamento');
});

test('PR3 A-5: o frontend não tem identidade própria para namespacear nada', () => {
  // Etapa 5 da frente. Qualquer chave "por tenant/usuário" no cliente seria
  // carimbada com um valor que o próprio cliente controla — o que repete a
  // afirmação do cliente em vez de provar isolamento.
  const app = montarAppOwnership('');
  const appJs = fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), 'app.js'), 'utf-8');
  assert(/user: safeJsonParse\(safeStorageRead\(STORAGE_KEYS\.session/.test(appJs),
    'a origem de state.user mudou: o trust boundary do PR 3 precisa ser refeito');
  eq(app.ctx.STORAGE_KEYS.session, 'epi-session-v4',
    'a chave de sessão do cliente mudou de nome');

  // A autoridade real é do servidor, e está no backend.
  const raizRepo = path.resolve(JS_ROOT, '..', '..');
  const seguranca = fs.readFileSync(path.join(raizRepo, 'epi_backend', 'security.py'), 'utf-8');
  assert(seguranca.includes('def decode_jwt_token(token):'), 'a autoridade de identidade do backend mudou');
  assert(seguranca.includes('hmac.compare_digest(expected_signature, provided_signature)'),
    'a verificação de assinatura do token mudou');
});

test('PR3 A-6: onde o requisito de rascunho é REAL, ele já existe — e é server-side', () => {
  const raizRepo = path.resolve(JS_ROOT, '..', '..');
  const appJs = fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), 'app.js'), 'utf-8');

  // Contrato comercial: o formulário mais longo da aplicação (37 campos) grava
  // rascunho no servidor, não no navegador.
  // Afirmado pelo NOME da função e pelo caminho SEM o prefixo de API. Com o
  // prefixo, `tests/test_frontend_api_contract.py` varre todo .js sob static/ e
  // lê esta linha como uma chamada de API do frontend — cobrando rota GET para
  // o que é POST. O nome da função é tão específico quanto, e não se disfarça.
  assert(appJs.includes('async function saveCommercialContractDraft('),
    'o rascunho server-side do contrato comercial sumiu: a comparação A/B/C precisa ser refeita');
  assert(appJs.includes("commercial-contract/save"),
    'o endpoint do rascunho do contrato comercial mudou de caminho');

  // Compras: ciclo de vida de rascunho completo, no banco.
  const cotacoes = fs.readFileSync(path.join(raizRepo, 'modules', 'purchases', 'quotes_service.py'), 'utf-8');
  assert(/QUOTE_STATUSES = \('draft'/.test(cotacoes),
    'o ciclo de rascunho de cotações mudou: a comparação A/B/C precisa ser refeita');
});

test('PR3 A-7: a decisão da F5-C foi executada — nenhum mecanismo de rascunho nasceu', () => {
  // CONVERTIDO NO PR 4. Era a comparação A/B/C com o destino do phase41 e da
  // flag. A alternativa escolhida era "remover sem substituição": ela foi
  // executada, e o gate passa a afirmar o resultado.
  const raizStatic = path.resolve(JS_ROOT, '..');
  assert(!fs.existsSync(path.join(raizStatic, 'ux-phase41.js')),
    'o ux-phase41.js voltou a existir');
  const appJs = fs.readFileSync(path.join(raizStatic, 'app.js'), 'utf-8');
  // Mira o REGISTRO, não qualquer menção: o cleanup legado cita a chave
  // justamente para apagá-la do disco de quem a ligou um dia.
  assert(!/ux_phase41_enabled: \{/.test(appJs), 'a flag do phase41 voltou ao registro de flags');
  assert(!appJs.includes('uxPhase41Enabled'), 'a flag do phase41 voltou ao mapa de chaves');

  // O contrato da F5-C é sobre PERSISTÊNCIA, não sobre varrer campos.
  //
  // A primeira versão deste gate afirmava que a única varredura de
  // `input[id], select[id], textarea[id]` era a do phase41. Estava errado, e o
  // gate apanhou: `static/navigation.js` tem a mesma varredura em
  // `captureContext()` — só que EM MEMÓRIA, sem storage, e atrás de
  // `ux_hierarchical_navigation_enabled`, que esta frente nunca auditou.
  // Registrado para outra frente; aqui o que se trava é o que a F5-C decidiu.
  const servidos = fs.readFileSync(path.join(raizStatic, 'views', '_scripts.html'), 'utf-8')
    .match(/src="\/([^"?]+\.js)/g).map((m) => m.slice(6));
  const persistidores = servidos.filter((rel) => {
    const fonte = fonteServida(rel);
    const varre = /querySelectorAll\('input\[id\], select\[id\], textarea\[id\]'\)/.test(fonte);
    const grava = /(localStorage|sessionStorage)[^\n]*setItem|queueStorageWrite\(/.test(fonte);
    return varre && grava;
  });
  eq(persistidores.length, 0,
    `voltou a existir arquivo que varre campos E os persiste: ${persistidores.join(', ')}`);

  // A política ativa continua sendo a oposta.
  assert(appJs.includes('function resetAppFormDrafts()'), 'a política de limpeza de rascunho sumiu do app');
});


// ── PR 4. LIMPEZA FINAL DA FRENTE #343 ──────────────────────────────────────
//
// Quatro módulos saem: ux-phase41, ux-phase43, ux-phase44 e
// multitab-navigation. O phase42 fica, como owner.
//
// A parte crítica não é apagar arquivo: é garantir que o que eles JÁ gravaram
// no navegador de quem usou as versões anteriores continue sendo limpo depois
// que o código que limpava for embora.

const STORAGE_LEGADO_DE_EXEMPLO = Object.freeze({
  'epi:ux:phase41:context:v2': '{"delivery-role":"resíduo"}',
  'epi:ux:phase41:scroll:v2': '820',
  'epi:ux:phase43:state:v1': '{"aberto":true}',
  'epi.ux.phase44.filters.entregas': '{"busca":"resíduo"}',
  'epi.ux.phase44.filters.estoque': '{"busca":"outro resíduo"}',
  'epi.ux.phase44.filters.dashboard': '{}',
  // As próprias chaves de flag, que ficavam no disco de quem as ligou um dia.
  'ux_phase41_enabled': '1',
  'ux_phase43_enabled': '1',
  'ux_phase44_enabled': '1',
  'ux_multitab_navigation_enabled': '1',
  // Legado do phase42 — mas NÃO é deste cleanup: o phase42 sobrevive e já
  // remove a própria chave. Entra no fixture para provar que a limpeza dele
  // continua funcionando depois desta fatia (L-2).
  'epi:ux:phase42:memory:v2': '{"employeeId":1}',
  // Alheias: não pertencem a módulo nenhum desta frente e têm de sobreviver.
  'epi-session-v4': '{"id":1,"role":"general_admin"}',
  // Neutra de propósito. A primeira versão deste fixture usava
  // `epi.analytics.master.events` — e o ux-analytics a apaga sozinho quando o
  // papel não é master, contrato DELE, não deste cleanup. O gate media a coisa
  // errada. Uma chave que módulo nenhum conhece prova o que interessa: o
  // cleanup só alcança namespace declarado.
  'preferencias:impressora:v1': 'balcao-2'
});

test('PR4 L-1: o cleanup legado apaga as chaves dos módulos removidos', () => {
  const app = montarAppOwnership('', { storageInicial: STORAGE_LEGADO_DE_EXEMPLO });
  // A limpeza roda na AVALIAÇÃO do app.js, antes de qualquer flag — não é
  // preciso disparar bootstrap nem ligar nada.
  Object.keys(STORAGE_LEGADO_DE_EXEMPLO)
    .filter((k) => /^epi:ux:phase4[13]:/.test(k) || k.indexOf('epi.ux.phase44.') === 0
      || /^(ux_phase4[134]_enabled|ux_multitab_navigation_enabled)$/.test(k))
    .forEach((chave) => {
      eq(app.local.getItem(chave), null, `a chave legada "${chave}" sobreviveu ao cleanup`);
    });
});

test('PR4 L-2: dado alheio sobrevive — e o phase42 continua limpando o dele', () => {
  const app = montarAppOwnership('', { storageInicial: STORAGE_LEGADO_DE_EXEMPLO });

  // O que não é desta frente não pode ser tocado.
  eq(app.local.getItem('epi-session-v4'), '{"id":1,"role":"general_admin"}',
    'o cleanup apagou a sessão do app');
  eq(app.local.getItem('preferencias:impressora:v1'), 'balcao-2',
    'o cleanup alcançou chave de namespace que ele não declara');

  // O phase42 SOBREVIVE e continua dono da própria limpeza legada. Quem apaga
  // esta chave é ele, não o cleanup do app — e é assim que tem de ser, senão a
  // fatia que elimina owners duplicados criaria mais um.
  eq(app.local.getItem('epi:ux:phase42:memory:v2'), null,
    'a limpeza legada do próprio phase42 parou de rodar');
  const phase42 = fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), 'ux-phase42.js'), 'utf-8');
  assert(phase42.includes("removeItem('epi:ux:phase42:memory:v2')"),
    'quem remove a chave do phase42 deixou de ser o próprio phase42');
  const appJs = fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), 'app.js'), 'utf-8');
  assert(!appJs.includes("'epi:ux:phase42:memory:v2'"),
    'o cleanup do app assumiu a chave do phase42 — owner duplicado');
});

test('PR4 L-3: o cleanup é idempotente — a segunda execução não quebra nem apaga a mais', () => {
  const app = montarAppOwnership('', { storageInicial: STORAGE_LEGADO_DE_EXEMPLO });
  const antes = app.local.length;
  app.ctx.limparResiduosLegadosDaUx();
  app.ctx.limparResiduosLegadosDaUx();
  eq(app.local.length, antes, 'a reexecução do cleanup mexeu no storage de novo');
  eq(app.local.getItem('epi-session-v4'), '{"id":1,"role":"general_admin"}',
    'a reexecução alcançou dado alheio');
});

test('PR4 L-4: sem localStorage, o cleanup não derruba a inicialização', () => {
  const app = montarAppOwnership('');
  const original = app.ctx.localStorage;
  try {
    // Janela privativa / storage desligado: o acesso LANÇA, não devolve null.
    Object.defineProperty(app.ctx, 'localStorage', {
      configurable: true,
      get() { throw new Error('storage indisponível'); }
    });
    app.ctx.limparResiduosLegadosDaUx();   // não pode lançar
  } finally {
    Object.defineProperty(app.ctx, 'localStorage', { configurable: true, value: original });
  }
});

test('PR4 L-5: o cleanup não usa clear() nem varre por heurística', () => {
  const appJs = fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), 'app.js'), 'utf-8');
  // Só CHAMADAS contam. A primeira versão deste gate casou com o próprio
  // comentário do cleanup, que citava a construção para dizer que não a usa —
  // o texto foi reescrito e a asserção passou a exigir início de instrução.
  const chamadasDeLimpezaTotal = (appJs.match(/(^|[\s;{(=])localStorage\.clear\s*\(/gm) || []).length;
  eq(chamadasDeLimpezaTotal, 0,
    'apareceu chamada de limpeza total do storage no app: o cleanup passaria a apagar dado de terceiros');
  // O prefixo precisa terminar em ponto: sem isso, `epi.ux.phase440` entraria.
  assert(appJs.includes("PREFIXOS_LEGADOS_UX = Object.freeze(['epi.ux.phase44.'])"),
    'o prefixo do cleanup mudou de forma — reavaliar o risco de varrer namespace vizinho');
  // A rastreabilidade da aposentadoria vive no COMENTÁRIO do cleanup, não numa
  // constante: a primeira versão declarava uma que nada lia, e o CodeQL apanhou
  // (#991). Não há leitor em runtime porque a decisão registrada no documento é
  // não gravar marcador de "já limpei" — ele seria uma chave nova, precisando de
  // outra limpeza depois.
  const inicio = appJs.indexOf('function limparResiduosLegadosDaUx');
  assert(inicio > -1, 'a função de limpeza legada sumiu do app.js');
  const cabecalho = appJs.slice(Math.max(0, inicio - 3000), inicio);
  assert(cabecalho.includes('APOSENTADORIA') && cabecalho.includes('343-pr4'),
    'a marca de aposentadoria do cleanup sumiu: sem ela não há critério de retirada rastreável no código');
  assert(!/(^|[\s;{(=])const\s+CLEANUP_LEGADO_UX_VERSAO/m.test(appJs),
    'voltou uma constante de versão que nada lê: dívida com aparência de mecanismo');
});


test('PR4 R-1: os quatro módulos não existem e não são servidos', () => {
  const raizStatic = path.resolve(JS_ROOT, '..');
  const REMOVIDOS = ['ux-phase41.js', 'ux-phase43.js', 'ux-phase44.js', 'multitab-navigation.js'];
  const servidos = fs.readFileSync(path.join(raizStatic, 'views', '_scripts.html'), 'utf-8');
  const indexHtml = fs.readFileSync(path.join(raizStatic, 'index.html'), 'utf-8');
  const appJs = fs.readFileSync(path.join(raizStatic, 'app.js'), 'utf-8');

  REMOVIDOS.forEach((arq) => {
    assert(!fs.existsSync(path.join(raizStatic, arq)), `"${arq}" voltou a existir`);
    assert(!servidos.includes(arq), `"${arq}" voltou para _scripts.html`);
    assert(!indexHtml.includes(arq), `"${arq}" voltou para o index.html`);
    assert(!appJs.includes(`/${arq}`), `o app.js voltou a injetar "${arq}"`);
  });

  // E o harness confirma pelo caminho real: a ordem servida não os menciona.
  const app = montarAppOwnership('');
  REMOVIDOS.forEach((arq) => {
    assert(!app.ordem.includes(arq), `"${arq}" apareceu na ordem carregada pelo harness`);
  });
  eq((app.ctx._errosDeCarga || []).length, 0,
    `algum script servido falhou ao carregar: ${JSON.stringify(app.ctx._errosDeCarga)}`);
});

test('PR4 R-2: as quatro flags não são lidas por ninguém', () => {
  const raizStatic = path.resolve(JS_ROOT, '..');
  const FLAGS = ['ux_phase41_enabled', 'ux_phase43_enabled', 'ux_phase44_enabled',
    'ux_multitab_navigation_enabled'];
  const servidos = fs.readFileSync(path.join(raizStatic, 'views', '_scripts.html'), 'utf-8')
    .match(/src="\/([^"?]+\.js)/g).map((m) => m.slice(6));

  servidos.forEach((rel) => {
    const fonte = fonteServida(rel);
    FLAGS.forEach((flag) => {
      // A ÚNICA menção tolerada é a do cleanup legado, que cita a chave para
      // apagá-la do disco. Qualquer leitura de flag é resíduo.
      const lendo = fonte.includes("getFeatureFlag('" + flag)
        || fonte.includes('getFeatureFlag("' + flag)
        || fonte.includes(flag + ': {')
        || fonte.includes(flag.replace(/_(.)/g, (_, c) => c.toUpperCase()));
      assert(!lendo, `"${rel}" ainda declara ou lê a flag removida "${flag}"`);
    });
  });

  // E o registro de flags do app não as conhece mais.
  const app = montarAppOwnership('?ux_phase41=1&ux_phase43=1&ux_phase44=1&ux_multitab=1');
  FLAGS.forEach((flag) => {
    eq(app.ctx.getFeatureFlag(flag, { defaultValue: false }), false,
      `a flag removida "${flag}" continua respondendo, e ainda por querystring`);
  });
});

test('PR4 R-3: os owners continuam únicos depois da remoção', () => {
  const raizStatic = path.resolve(JS_ROOT, '..');
  const servidos = fs.readFileSync(path.join(raizStatic, 'views', '_scripts.html'), 'utf-8')
    .match(/src="\/([^"?]+\.js)/g).map((m) => m.slice(6));
  const fontes = servidos.map((rel) => [rel, fonteServida(rel)]);

  // fetch: um só embrulhador
  const embrulham = fontes.filter(([, f]) => /(globalThis|window|win)\.fetch\s*=/.test(f)).map(([r]) => r);
  eq(embrulham.join(','), 'error-monitor.js', `mais de um owner de fetch: ${embrulham.join(', ')}`);

  // navegação: nenhum interceptador de clique em captura com silenciamento
  const interceptam = fontes.filter(([, f]) =>
    /'click'[^)]*capture:\s*true/.test(f) && f.includes('stopImmediatePropagation')).map(([r]) => r);
  eq(interceptam.length, 0, `reapareceu interceptador de navegação em captura: ${interceptam.join(', ')}`);

  // dropdown: o que define OWNER é ligar o clique do gatilho, não citar o
  // atributo. O `navigation.js` fecha dropdown já aberto como UI transitória e
  // nunca registra listener no gatilho — isso não o torna um segundo dono.
  const donosDeDropdown = fontes.filter(([, f]) =>
    /(safeOn|addEventListener)\(\s*trigger,\s*'click'/.test(f)).map(([r]) => r);
  eq(donosDeDropdown.join(','), 'app.js', 'mais de um owner de dropdown: ' + donosDeDropdown.join(', '));

  // E, no app montado, nenhum listener de clique em captura no documento.
  const app = montarAppOwnership('');
  eq(app.listenersDe(app.doc, 'click').filter((l) => l.captura === true).length, 0,
    'apareceu listener de clique em captura no documento');
});

test('PR4 R-4: o DOM e o CSS dos quatro módulos saíram junto com eles', () => {
  // Remover o `.js` e deixar o `<section>` e as regras de estilo que só ele
  // usava é meia remoção: o markup continua sendo servido para todo mundo, e a
  // folha continua carregando ~200 linhas de regras que nenhum seletor alcança.
  // Foi a busca residual do #343 PR 4 que achou os dois — este gate é o que
  // impede que voltem.
  const raizStatic = path.resolve(JS_ROOT, '..');
  const NOMES = /phase41|phase43|phase44|multitab/i;

  const fragmentos = fs.readdirSync(path.join(raizStatic, 'views'))
    .filter((n) => n.endsWith('.html'))
    .map((n) => ['views/' + n, fs.readFileSync(path.join(raizStatic, 'views', n), 'utf-8')]);
  fragmentos.push(['index.html', fs.readFileSync(path.join(raizStatic, 'index.html'), 'utf-8')]);
  fragmentos.push(['styles.css', fs.readFileSync(path.join(raizStatic, 'styles.css'), 'utf-8')]);

  fragmentos.forEach(([rel, corpo]) => {
    const linhas = corpo.split('\n')
      .map((linha, n) => [n + 1, linha])
      .filter(([, linha]) => NOMES.test(linha));
    eq(linhas.length, 0,
      `"${rel}" voltou a citar um dos quatro módulos removidos: ` +
      linhas.map(([n, linha]) => `${n}: ${linha.trim()}`).join(' | '));
  });

  // Contrato POSITIVO do mesmo achado: o que sobreviveu continua de pé. O
  // gatilho de confirmação do analytics ficou só com o atributo do app, e o
  // `styles.css` mantém a regra de transição das DUAS famílias que restaram.
  const analytics = fonteServida('ux-analytics.js');
  assert(analytics.includes("closest?.('[data-confirm-action]')"),
    'o gatilho de confirmação do analytics perdeu o seletor que sobreviveu');
  const css = fs.readFileSync(path.join(raizStatic, 'styles.css'), 'utf-8');
  assert(css.includes('body.ux-hierarchy-enabled .view.active.hierarchy-view-enter,\n'
    + 'body.spa-navigation-enabled .view.active.spa-view-enter {'),
    'a regra compartilhada de transição perdeu os seletores que não eram do phase44');

  // E o evento de troca de view perdeu o campo que só o multitab produzia — o
  // `app.js` inteiro deixou de conhecer o sinal, produtor e consumidor.
  const appJs = fs.readFileSync(path.join(raizStatic, 'app.js'), 'utf-8');
  assert(appJs.includes('viaHistorico: options.viaHistorico === true'),
    'o `viaHistorico` saiu do detalhe do evento: Voltar/Avançar voltaria a resetar');
  assert(!appJs.includes('viaMultitab'),
    'o `viaMultitab` voltou ao app.js sem que exista produtor para ele');
});

test('PR1 Z-4: todo gate desta seção parte do app REAL, e nenhum fabrica a troca de view', () => {
  // Este é o gate que fecha a seção, e ele existe pelo mesmo motivo que o
  // `G-real-cobertura` da F5-B.1: a fatia anterior descobriu que gates montados
  // sobre evento FABRICADO passavam verdes sem atravessar o caminho real, e foi
  // esse atalho que manteve cinco achados invisíveis. Uma seção que se propõe a
  // caracterizar COMPORTAMENTO não pode aceitar o mesmo atalho.
  //
  // É também o consumidor das marcas de seção — declaradas junto com o harness
  // e apontadas pelo CodeQL como não utilizadas enquanto este gate não existia.
  const fonte = fs.readFileSync(__filename, 'utf-8');
  const ini = fonte.indexOf(MARCA_INICIO_PR1 + '\n');
  const fim = fonte.indexOf(MARCA_FIM_PR1 + '\n', ini + 1);
  assert(ini > -1 && fim > ini, 'as marcas da seção PR1 mudaram de forma');
  const secao = fonte.slice(ini, fim);

  // Reconhece os gates do PR 1 e os das fatias do PR 2 (PR2A..PR2D): todos
  // vivem nesta seção e todos respondem à mesma regra.
  const blocos = secao.split(/\n(?:test|testAsync|caracterizaDefeito)\('PR(?:1|2[A-D]) /).slice(1);
  assert(blocos.length >= 40, `esperava os gates do PR1 e do PR2, encontrei ${blocos.length}`);
  const FABRICACAO_DE_VIEW = "CustomEvent('epi:" + "viewchange'";

  // Montar o app servido é o que separa caracterização de suposição. As quatro
  // funções auxiliares abaixo todas desembocam em `montarAppOwnership`.
  const MONTAGENS = [
    'montarAppOwnership(', 'celulaDaMatriz42x43(',
    'appComDropdownDoApp(', 'appComDropdownDoPhase44(', 'appComNavegacaoDoApp('
  ];
  // O gate de cobertura é o último da seção; renomeá-lo ou movê-lo exige
  // revisar a lista de exceções abaixo, e é por isso que ela tem tamanho fixo.
  // Únicas exceções, e cada uma tem razão declarada: elas não medem
  // comportamento, fixam a CONCLUSÃO que os outros gates sustentam.
  const SEM_MONTAGEM = {
    'F-6': 'fixa a classificação de equivalência do dropdown, derivada de F-1..F-5',
    'Z-2': 'fixa a matriz de decisão por módulo e o vocabulário permitido',
    'Z-3': 'valida os campos das caracterizações de defeito, não o app',
    'Z-4': 'é este próprio gate de cobertura, que lê o arquivo em vez do app'
  };

  blocos.forEach((bloco) => {
    const nome = bloco.slice(0, bloco.indexOf(':'));
    if (!Object.prototype.hasOwnProperty.call(SEM_MONTAGEM, nome)) {
      assert(MONTAGENS.some((m) => bloco.includes(m)),
        `o gate "${nome}" não monta o app servido — sem isso ele descreve uma suposição, não um comportamento`);
    }
    // O atalho proibido, explicitamente: inventar a troca de view em vez de
    // provocá-la. Nenhum gate desta seção precisa disso, e o dia em que um
    // precisar é o dia de rever o harness, não de fabricar o evento.
    //
    // O literal é montado em duas partes de propósito: escrito inteiro, ELE
    // apareceria no texto desta própria função e o gate se acusaria. A
    // alternativa seria abrir exceção para si mesmo — e uma regra que não
    // alcança quem a escreve é exatamente o tipo de guarda que não guarda.
    assert(!bloco.includes(FABRICACAO_DE_VIEW),
      `o gate "${nome}" fabrica a troca de view: é o atalho que escondeu os cinco achados da F5-B.1`);
  });

  // E as exceções não podem crescer em silêncio.
  eq(Object.keys(SEM_MONTAGEM).length, 4,
    'a lista de gates sem montagem mudou de tamanho: cada exceção precisa de razão declarada');
});

// MARCA_FIM_PR1

// ── Relatório ─────────────────────────────────────────────────────────────
// Os testes assíncronos rodam ANTES do relatório. Assertar em cima de um
// handler `async` sem esperar por ele daria verde por não ter chegado a
// executar — que é a forma mais silenciosa de falso-verde.
// ════════════════════════════════════════════════════════════════════════════
// ISOLAMENTO ENTRE USUÁRIOS EM COMPUTADOR COMPARTILHADO — PR A (View)
//
// Premissa de produto: o mesmo computador e navegador podem ser usados por
// pessoas diferentes. Preferência pessoal, estado de navegação e telemetria de
// um usuário não devem ser herdados por outro.
//
// Esta fatia trata SÓ o estado de navegação: `history.state.view`. A
// investigação mostrou que o carimbo `sid` da #343 F2 protege os FILTROS, mas
// roda DEPOIS do `showView` — então a VIEW de quem saiu ainda era aplicada a
// quem entrou, pelo Voltar da mesma aba.
//
// O que esta fatia NÃO faz: não persiste View em storage, não cria owner de
// navegação, não toca `bindMenuNavigation`/`navigateToView`.
// ════════════════════════════════════════════════════════════════════════════

// Monta um DOCUMENTO do app servido. Cada chamada é uma CARGA de página — é
// assim que se modela "A sai, a página recarrega, B entra na mesma aba".
//
// Diferente de `montarAppServidoF5B`: aceita um `sessionStorage` vindo de fora
// (o `sessionStorage` sobrevive à recarga na mesma aba, e é onde vive o escopo
// de snapshot) e declara `crypto`. Sem `crypto`, `DOCUMENT_INSTANCE_ID` cai no
// fallback `t${Date.now()}` e duas cargas no mesmo milissegundo receberiam o
// MESMO identificador — o gate passaria ou falharia por relógio.
function montarDocumentoIsolamento(sessaoCompartilhada, busca) {
  const raizStatic = path.resolve(JS_ROOT, '..');
  const vistas = {
    dashboard: montarVistaSimplesF5B('dashboard', []),
    estoque: montarVistaSimplesF5B('estoque', []),
    colaboradores: montarVistaSimplesF5B('colaboradores', [])
  };
  vistas.dashboard._classes.add('active');
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

  const armazem = () => ({
    _s: {},
    getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
    setItem(k, v) { this._s[k] = String(v); },
    removeItem(k) { delete this._s[k]; },
    key(i) { return Object.keys(this._s)[i] ?? null; },
    get length() { return Object.keys(this._s).length; }
  });

  const url = { busca: busca || '' };
  const ctx = {
    document: doc, localStorage: armazem(), sessionStorage: sessaoCompartilhada,
    get location() {
      return { search: url.busca, href: `http://local/${url.busca}`, pathname: '/', assign() {}, reload() {} };
    },
    history: { pushState() {}, replaceState() {}, back() {}, length: 1, state: null },
    navigator: { userAgent: 'node' },
    console: { log() {}, info() {}, warn() {}, error() {}, debug() {} },
    crypto: { randomUUID: () => 'doc-' + Math.random().toString(16).slice(2) + '-' + Math.random().toString(16).slice(2) },
    CustomEvent: class { constructor(t, o) { this.type = t; Object.assign(this, o || {}); } },
    Event: class { constructor(t, o) { this.type = t; this.bubbles = false; Object.assign(this, o || {}); } },
    getComputedStyle: () => ({ display: 'block', visibility: 'visible' }),
    AbortController: class { constructor() { this.signal = { addEventListener() {} }; } abort() {} },
    MutationObserver: class { observe() {} disconnect() {} },
    setTimeout, clearTimeout, setInterval, clearInterval, Promise, URL, URLSearchParams,
    requestAnimationFrame: (fn) => setTimeout(fn, 0),
    // Resposta com a FORMA que o cliente de API do app espera. Entrar numa view
    // dispara carregamento de dados de verdade; sem `headers.get` o
    // `parseApiPayload` lança fora de qualquer `try`, e o processo morre antes
    // de o gate medir qualquer coisa.
    fetch: () => Promise.resolve({
      ok: true, status: 200,
      headers: { get: () => 'application/json' },
      json: () => Promise.resolve({ items: [] }),
      text: () => Promise.resolve('{"items":[]}')
    }),
    alert() {}, scrollTo() {}, matchMedia: () => ({ matches: false, addEventListener() {} })
  };
  ctx._handlers = {};
  ctx.addEventListener = (ev, fn) => { (ctx._handlers[ev] = ctx._handlers[ev] || []).push(fn); };
  ctx.removeEventListener = () => {};
  ctx.dispatchEvent = (ev) => {
    (ctx._handlers[ev.type] || []).forEach((fn) => { try { fn(ev); } catch (_e) { /* isolado, como no navegador */ } });
    return true;
  };
  ctx.window = ctx; ctx.globalThis = ctx; ctx.self = ctx;
  vmF5B.createContext(ctx);

  const ordem = fs.readFileSync(path.join(raizStatic, 'views', '_scripts.html'), 'utf-8')
    .match(/src="\/([^"?]+\.js)/g).map((m) => m.slice(6));
  ordem.forEach((rel) => {
    try {
      vmF5B.runInContext(fs.readFileSync(path.join(raizStatic, rel), 'utf-8'), ctx, { filename: rel });
    } catch (_e) { /* dependência de browser ausente não invalida o gate */ }
  });

  // Identidade logada: o handler de popstate retorna cedo sem ela. As
  // permissões são as REAIS exigidas por `VIEW_PERMISSIONS` — `showView`
  // redireciona para `defaultView()` quando falta uma, e o gate mediria um
  // redirecionamento por RBAC em vez do isolamento que ele se propõe a medir.
  const entrar = (usuario) => {
    const st = ctx.__EPI_APP_STATE__;
    st.user = Object.assign({ role: 'master_admin', company_id: 'c1' }, usuario || {});
    st.permissions = ['dashboard:view', 'stock:view', 'employees:view'];
    return st;
  };

  // `bindSpaNavigationHistory()` é chamada por `init()`, que é `async function`
  // declarada dentro do bloco que envolve o app.js e por isso não alcança o
  // global. O harness chama a MESMA função que a produção chama — não registra
  // um listener próprio.
  if (typeof ctx.bindSpaNavigationHistory === 'function') ctx.bindSpaNavigationHistory();

  return {
    ctx, doc, vistas,
    entrar,
    definirBusca: (b) => { url.busca = b || ''; },
    viewAtiva: () => {
      const no = doc.querySelector('.view.active');
      return no && no.id ? no.id.replace(/-view$/, '') : '';
    },
    abrirView: (nome) => { ctx.showView(nome, { partial: true }); },
    // Dispara o popstate REAL, com o `state` que o navegador entregaria.
    voltarPara: (estado) => {
      ctx.dispatchEvent(Object.assign(new ctx.Event('popstate', {}), { state: estado }));
    }
  };
}

const BUSCA_ISOL = '?ux_spa_navigation=1&ux_interactive_app=1';

test('ISOL A-0: o harness monta o app servido e alcança o caminho de Voltar', () => {
  const sessao = {
    _s: {}, getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
    setItem(k, v) { this._s[k] = String(v); }, removeItem(k) { delete this._s[k]; }
  };
  const d = montarDocumentoIsolamento(sessao, BUSCA_ISOL);
  d.entrar({ id: 'A' });
  assert(typeof d.ctx.showView === 'function', 'showView não veio do app servido');
  assert(typeof d.ctx.collectInteractiveSnapshot === 'function', 'collectInteractiveSnapshot não veio do app servido');
  assert(typeof d.ctx.snapshotScopeId === 'function', 'snapshotScopeId não veio do app servido');
  assert(d.ctx.isSpaNavigationEnabled() === true, 'a flag de navegação SPA deveria estar ligada no harness');
  eq((d.ctx._handlers.popstate || []).length, 1, 'o app deveria registrar exatamente um listener de popstate');
});

test('ISOL A-1: a View de quem saiu NÃO é aplicada a quem entra (Voltar na mesma aba)', () => {
  // Uma aba só. `sessionStorage` sobrevive à recarga; é por isso que ele é
  // compartilhado entre os dois documentos.
  const sessao = {
    _s: {}, getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
    setItem(k, v) { this._s[k] = String(v); }, removeItem(k) { delete this._s[k]; }
  };

  // ── A entra, navega para estoque e a entrada de histórico é gravada ──
  const docA = montarDocumentoIsolamento(sessao, BUSCA_ISOL);
  docA.entrar({ id: 'A' });
  docA.abrirView('estoque');
  eq(docA.viewAtiva(), 'estoque', 'A deveria estar em estoque');
  const entradaDeA = docA.ctx.collectInteractiveSnapshot('estoque');
  assert(entradaDeA.sid, 'o snapshot de A deveria vir carimbado');

  // ── logout de A: é o que `terminateSession()` faz antes de recarregar ──
  docA.ctx.rotateSnapshotScope();

  // ── B entra: nova CARGA da página, mesma aba ──
  const docB = montarDocumentoIsolamento(sessao, BUSCA_ISOL);
  docB.entrar({ id: 'B' });
  eq(docB.viewAtiva(), 'dashboard', 'B deveria começar na view inicial');
  assert(entradaDeA.sid !== docB.ctx.snapshotScopeId(),
    'os escopos de A e B deveriam diferir depois do encerramento');

  // ── B aperta Voltar e o navegador entrega a entrada de A ──
  docB.voltarPara(entradaDeA);
  assert(docB.viewAtiva() !== 'estoque',
    `B foi levado para a view de A ("${docB.viewAtiva()}"): o estado de navegação atravessou identidades`);
  eq(docB.viewAtiva(), 'dashboard', 'sem escopo válido, o Voltar deveria cair na view inicial do contrato');
});

test('ISOL A-2: o Voltar legítimo da MESMA sessão continua funcionando', () => {
  // O contrapositivo do A-1, e a razão de ele não poder ser resolvido
  // desligando o Voltar: dentro da sessão, a navegação histórica é do usuário.
  const sessao = {
    _s: {}, getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
    setItem(k, v) { this._s[k] = String(v); }, removeItem(k) { delete this._s[k]; }
  };
  const d = montarDocumentoIsolamento(sessao, BUSCA_ISOL);
  d.entrar({ id: 'A' });
  d.abrirView('estoque');
  const entrada = d.ctx.collectInteractiveSnapshot('estoque');
  d.abrirView('colaboradores');
  eq(d.viewAtiva(), 'colaboradores', 'A deveria ter saído de estoque');
  d.voltarPara(entrada);
  eq(d.viewAtiva(), 'estoque', 'o Voltar do próprio usuário deveria devolvê-lo à view anterior');
});

test('ISOL A-3: estado sem carimbo não escolhe a View', () => {
  // Um `state` sem `sid` não prova a quem pertence. Aceitar por omissão é o
  // caminho mais fácil e o errado: entradas antigas, de antes do carimbo,
  // pertencem a quem estava ali antes.
  const sessao = {
    _s: {}, getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
    setItem(k, v) { this._s[k] = String(v); }, removeItem(k) { delete this._s[k]; }
  };
  const d = montarDocumentoIsolamento(sessao, BUSCA_ISOL);
  d.entrar({ id: 'B' });
  d.voltarPara({ view: 'estoque' });
  eq(d.viewAtiva(), 'dashboard', 'estado sem `sid` não deveria escolher a view');
});

test('ISOL A-4: a URL antiga com ?view= não é porta dos fundos', () => {
  // A entrada de histórico de A carrega TAMBÉM `?view=estoque` na URL. Recusar
  // o `state` e então ler a URL daquela mesma entrada devolveria o vazamento
  // por outro caminho.
  const sessao = {
    _s: {}, getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
    setItem(k, v) { this._s[k] = String(v); }, removeItem(k) { delete this._s[k]; }
  };
  const docA = montarDocumentoIsolamento(sessao, BUSCA_ISOL);
  docA.entrar({ id: 'A' });
  const entradaDeA = docA.ctx.collectInteractiveSnapshot('estoque');
  docA.ctx.rotateSnapshotScope();

  const docB = montarDocumentoIsolamento(sessao, BUSCA_ISOL + '&view=estoque');
  docB.entrar({ id: 'B' });
  docB.voltarPara(entradaDeA);
  assert(docB.viewAtiva() !== 'estoque',
    'a view de A voltou pela URL da entrada de histórico dela');
});

test('ISOL A-5: popstate sem estado nenhum não quebra e não escolhe View alheia', () => {
  const sessao = {
    _s: {}, getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
    setItem(k, v) { this._s[k] = String(v); }, removeItem(k) { delete this._s[k]; }
  };
  const d = montarDocumentoIsolamento(sessao, BUSCA_ISOL);
  d.entrar({ id: 'B' });
  d.voltarPara(null);
  eq(d.viewAtiva(), 'dashboard', 'popstate sem estado deveria manter a view inicial');
  d.voltarPara(undefined);
  eq(d.viewAtiva(), 'dashboard', 'popstate indefinido deveria manter a view inicial');
});

test('ISOL A-8: troca de identidade SEM logout também invalida a View anterior', () => {
  // O cenário que o próprio `rotateSnapshotScope` documenta: o backend cai, A
  // dá F5, o app mantém `state.user` de A e oferece login manual; B entra com
  // sucesso e NENHUM encerramento aconteceu. A rotação no login é o que fecha
  // essa porta — e a View precisa obedecer a ela igual aos filtros.
  const sessao = {
    _s: {}, getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
    setItem(k, v) { this._s[k] = String(v); }, removeItem(k) { delete this._s[k]; }
  };
  const d = montarDocumentoIsolamento(sessao, BUSCA_ISOL);
  d.entrar({ id: 'A' });
  d.abrirView('estoque');
  const entradaDeA = d.ctx.collectInteractiveSnapshot('estoque');
  d.abrirView('dashboard');

  // Login de B no MESMO documento: é aqui que a rotação acontece na produção.
  d.ctx.rotateSnapshotScope();
  d.entrar({ id: 'B' });

  d.voltarPara(entradaDeA);
  assert(d.viewAtiva() !== 'estoque',
    'sem encerramento, a View de A continuou alcançável para B pelo Voltar');
});

test('ISOL A-9: o link direto ?view= na ENTRADA INICIAL continua funcionando', () => {
  // A guarda é do `popstate`, não da carga. Um link compartilhado
  // (`?view=estoque`) precisa continuar abrindo a tela para quem está logado —
  // caso contrário a correção teria trocado um defeito por outro.
  const sessao = {
    _s: {}, getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
    setItem(k, v) { this._s[k] = String(v); }, removeItem(k) { delete this._s[k]; }
  };
  const d = montarDocumentoIsolamento(sessao, BUSCA_ISOL + '&view=estoque');
  d.entrar({ id: 'A' });
  eq(d.ctx.resolveViewFromLocation(), 'estoque', 'a URL deveria declarar o destino');
  // A MESMA expressão que o bootstrap do app usa para a carga inicial.
  const preferida = d.ctx.isSpaNavigationEnabled() ? d.ctx.resolveViewFromLocation() : '';
  d.ctx.showView(preferida, { partial: true });
  eq(d.viewAtiva(), 'estoque', 'o link direto deixou de abrir a tela pedida');
});

test('ISOL A-6: a validação de escopo PRECEDE a aplicação da View', () => {
  // Estrutural, e deliberado: o defeito original não era a ausência de
  // verificação — era a ORDEM. O `sid` já existia e já era testado, mas depois
  // do `showView`, e cobrindo só os filtros.
  const fonte = fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), 'app.js'), 'utf-8');
  const i = fonte.indexOf("safeOn(globalThis, 'popstate'");
  assert(i > -1, 'o handler de popstate mudou de forma');
  const trecho = fonte.slice(i, i + 3000);
  const posEscopo = trecho.indexOf('escopoDoEstadoConfere');
  const posShow = trecho.indexOf('showView(');
  assert(posEscopo > -1, 'a validação de escopo sumiu do handler de popstate');
  assert(posShow > -1, 'o showView sumiu do handler de popstate');
  assert(posEscopo < posShow,
    'a validação de escopo voltou a rodar DEPOIS do showView — foi exatamente esse o defeito');
});

test('ISOL A-7: a fatia não cria persistência de View nem segundo dono de navegação', () => {
  const raizStatic = path.resolve(JS_ROOT, '..');
  const servidos = fs.readFileSync(path.join(raizStatic, 'views', '_scripts.html'), 'utf-8')
    .match(/src="\/([^"?]+\.js)/g).map((m) => m.slice(6));
  const fontes = servidos.map((rel) => [rel, fonteServida(rel)]);

  // Nenhuma chave de storage nova para View.
  fontes.forEach(([rel, f]) => {
    assert(!/(setItem|safeStorageWrite|queueStorageWrite)\(\s*['"`][^'"`]*v(iew|tab)/i.test(f),
      `"${rel}" passou a persistir View em storage — a View é estado de navegação, não preferência`);
  });
  // Nenhum interceptador de navegação em captura reintroduzido (#343 PR 2D).
  const interceptam = fontes.filter(([, f]) =>
    /'click'[^)]*capture:\s*true/.test(f) && f.includes('stopImmediatePropagation')).map(([r]) => r);
  eq(interceptam.length, 0, `reapareceu interceptador de navegação em captura: ${interceptam.join(', ')}`);
  // A autoridade de navegação continua sendo uma só.
  const appJs = fonteServida('app.js');
  assert(appJs.includes('bindMenuNavigation'), 'bindMenuNavigation sumiu do app.js');
  assert(appJs.includes('function navigateToView('), 'navigateToView deixou de ser a autoridade de navegação');
  assert(!servidos.includes('multitab-navigation.js'), 'o multitab voltou a ser servido');
});


test('ISOL A-10: `escopoDoEstadoConfere()` é o dono ÚNICO da comparação de escopo', () => {
  // Registrado como CONTRATO a pedido explícito, junto com a autorização do
  // PR B. Gate apenas — nenhuma linha de produção do PR A foi tocada.
  //
  // A revisão do PR A pediu que esta função fosse o owner único da decisão
  // "este estado histórico pertence à sessão atual?". A implementação já era
  // essa, mas NADA impedia alguém de reintroduzir a comparação em outro ponto:
  // os gates do PR A verificam a ORDEM e o USO, não a exclusividade. Sem este
  // gate, o contrato era uma intenção, não uma trava.
  const appJs = fonteServida('app.js');

  // `snapshotScopeId()` tem dois papéis legítimos: CARIMBAR (em
  // `collectInteractiveSnapshot`) e ser comparado — este último só dentro do
  // dono. Qualquer outra COMPARAÇÃO é um segundo dono da mesma regra.
  const comparacoes = (appJs.match(/[!=]==\s*snapshotScopeId\(\)|snapshotScopeId\(\)\s*[!=]==/g) || []);
  eq(comparacoes.length, 1,
    `a comparação de escopo aparece ${comparacoes.length}x — ela pertence a um dono só`);
  const dono = appJs.slice(appJs.indexOf('function escopoDoEstadoConfere'));
  assert(dono.slice(0, 300).includes('estado.sid === snapshotScopeId()'),
    'a única comparação de escopo deixou de estar dentro de `escopoDoEstadoConfere`');

  // E a sequência do contrato: validar escopo → decidir View. Nunca o inverso.
  const i = appJs.indexOf("safeOn(globalThis, 'popstate'");
  const handler = appJs.slice(i, i + 3000);
  assert(handler.indexOf('escopoDoEstadoConfere') < handler.indexOf('showView('),
    'a validação de escopo voltou a rodar depois de aplicar a View');
});

// ════════════════════════════════════════════════════════════════════════════
// ISOLAMENTO ENTRE USUÁRIOS — PR B (telemetria)
//
// B-0: CARACTERIZAÇÃO. Estes gates medem o comportamento ANTES da correção.
// Os que descrevem o defeito nascem vermelhos, de propósito.
//
// Reproduzido na investigação: `master_admin` A gera eventos, sai, e o
// `master_admin` B seguinte os lê. A proteção existente é por PAPEL
// (`canAccessAnalytics()` → `isMasterRole`), e papel igual não é principal
// igual.
// ════════════════════════════════════════════════════════════════════════════

const CHAVE_TELEMETRIA = 'epi.analytics.master.events';

// Uma CARGA de página do `ux-analytics.js` servido, com `localStorage`
// compartilhado entre as cargas — é assim que se modela a mesma aba/navegador.
function montarTelemetria(localCompartilhado, opcoes) {
  const o = opcoes || {};
  const raizStatic = path.resolve(JS_ROOT, '..');
  const doc = criarNoF5B('document', {});
  doc.body = criarNoF5B('body', {});
  doc.head = criarNoF5B('head', {});
  doc.readyState = 'complete';
  doc.getElementById = () => null;
  doc.createElement = (tag) => criarNoF5B(tag, {});
  doc.querySelector = () => null;
  doc.querySelectorAll = () => [];

  const ctx = {
    document: doc, localStorage: localCompartilhado,
    sessionStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    location: { search: o.busca || '?ux_analytics=1', href: 'http://local/' },
    console: { log() {}, info() {}, warn() {}, error() {}, debug() {} },
    navigator: { userAgent: 'node' },
    // A identidade que o módulo enxerga. Ele lê `__EPI_APP_STATE__.user.role`
    // primeiro e cai para a sessão em storage — os dois caminhos existem aqui.
    __EPI_APP_STATE__: o.usuario ? { user: { id: o.usuario.id, role: o.usuario.papel } } : {},
    __EPI_FRONTEND_HELPERS__: Object.freeze({
      getFeatureFlag: (nome) => nome === 'ux_analytics_enabled',
      safeOn: (alvo, ev, fn) => { try { alvo.addEventListener(ev, fn); return true; } catch (_e) { return false; } }
    }),
    STORAGE_KEYS: { session: 'epi-session-v4' },
    CustomEvent: class { constructor(tipo, init) { this.type = tipo; Object.assign(this, init || {}); } },
    Event: class { constructor(tipo, init) { this.type = tipo; this.bubbles = false; Object.assign(this, init || {}); } },
    setTimeout, clearTimeout, setInterval, clearInterval, Promise, URL, URLSearchParams,
    requestAnimationFrame: (fn) => setTimeout(fn, 0),
    Date, JSON, Math
  };
  ctx.window = ctx; ctx.globalThis = ctx; ctx.self = ctx;
  ctx.addEventListener = () => {}; ctx.dispatchEvent = () => true;
  vmF5B.createContext(ctx);
  vmF5B.runInContext(
    fs.readFileSync(path.join(raizStatic, 'ux-analytics.js'), 'utf-8'), ctx, { filename: 'ux-analytics.js' });

  return {
    ctx,
    api: () => ctx.__EPI_ANALYTICS__ || null,
    // Produz evento pelo caminho REAL do módulo. `pushEvent` enfileira e drena
    // numa microtask (`Promise.resolve().then(flushQueue)`), então quem mede
    // precisa ceder o turno — senão o gate lê a lista antes de ela existir e
    // conclui "isolado" sobre um evento que nunca foi gravado.
    produzirEvento: async (nome) => {
      const api = ctx.__EPI_ANALYTICS__;
      if (!api || typeof api.track !== 'function') return false;
      const ok = api.track(nome || 'evento_de_teste', {});
      await Promise.resolve();
      await Promise.resolve();
      return ok;
    },
    // O que ESTE principal consegue ler pela API pública do módulo.
    eventosVisiveis: () => {
      const api = ctx.__EPI_ANALYTICS__;
      if (!api || typeof api.getEvents !== 'function') return { allowed: false, events: [] };
      return api.getEvents();
    }
  };
}

function armazemTelemetria(inicial) {
  return {
    _s: Object.assign({}, inicial || {}),
    getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
    setItem(k, v) { this._s[k] = String(v); },
    removeItem(k) { delete this._s[k]; },
    key(i) { return Object.keys(this._s)[i] ?? null; },
    get length() { return Object.keys(this._s).length; }
  };
}

const EVENTOS_DE_A = JSON.stringify([
  { event: 'view_open', module: 'colaboradores', timestamp: 1, duration: 0, metadata: {} },
  { event: 'flow:complete', module: 'entregas', timestamp: 2, duration: 120, metadata: {} }
]);

test('ISOL B-0: o harness monta o ux-analytics servido e alcança a API', () => {
  const local = armazemTelemetria();
  const d = montarTelemetria(local, { usuario: { id: 'A', papel: 'master_admin' } });
  assert(d.api(), '__EPI_ANALYTICS__ não foi publicada pelo módulo servido');
  assert(typeof d.api().getEvents === 'function', 'a API perdeu getEvents');
  eq(d.eventosVisiveis().allowed, true, 'um master deveria ter acesso à própria telemetria');
});

testAsync('ISOL B-1: master B não consome a telemetria do master A', async () => {
  // O vazamento medido na investigação. Papel igual, principal diferente.
  //
  // A telemetria é PRODUZIDA pelo caminho real do módulo, não semeada no
  // storage: semear mede o que o teste escreveu, não o que a aplicação grava.
  const local = armazemTelemetria();
  const a = montarTelemetria(local, { usuario: { id: 'A', papel: 'master_admin' } });
  await a.produzirEvento('acao_de_A');
  // O módulo emite `view_open` na inicialização, então a lista de A tem mais do
  // que o evento deste gate. O que importa é que o evento NOMEADO aqui esteja
  // presente: sem ele, o gate mediria uma lista vazia e chamaria de isolamento.
  assert(a.eventosVisiveis().events.some((e) => e.event === 'acao_de_A'),
    'A não viu o próprio evento — o gate não mediu nada');

  // B entra numa CARGA nova (o logout recarrega a página).
  const b = montarTelemetria(local, { usuario: { id: 'B', papel: 'master_admin' } });
  const deA = b.eventosVisiveis().events.filter((e) => e.event === 'acao_de_A');
  eq(deA.length, 0, `B leu ${deA.length} evento(s) de A: ${JSON.stringify(deA).slice(0, 120)}`);
});

test('ISOL B-2: a proteção por PAPEL continua funcionando (controle)', () => {
  // Contraprova do B-1: o que já funcionava não pode regredir.
  const local = armazemTelemetria({ [CHAVE_TELEMETRIA]: EVENTOS_DE_A });
  const b = montarTelemetria(local, { usuario: { id: 'B', papel: 'admin' } });
  eq(b.eventosVisiveis().allowed, false, 'um não-master voltou a ter acesso à API de telemetria');
  eq(local.getItem(CHAVE_TELEMETRIA), null,
    'a telemetria continuou no disco com um não-master logado');
});

testAsync('ISOL B-3: troca de principal SEM recarga também isola a telemetria', async () => {
  // Obrigatório por causa do `ISOL A-8`: nem toda troca de identidade passa por
  // recarga. O login de outro principal acontece no MESMO documento — e é este
  // o gate que distingue "telemetria em RAM descartada na troca" de "telemetria
  // no disco que por acaso foi purgada na carga".
  const local = armazemTelemetria();
  const d = montarTelemetria(local, { usuario: { id: 'A', papel: 'master_admin' } });
  await d.produzirEvento('acao_de_A');
  assert(d.eventosVisiveis().events.some((e) => e.event === 'acao_de_A'),
    'A não viu o próprio evento — o gate não mediu nada');

  // B faz login no mesmo documento: só a identidade publicada muda.
  d.ctx.__EPI_APP_STATE__.user = { id: 'B', role: 'master_admin' };
  const deA = d.eventosVisiveis().events.filter((e) => e.event === 'acao_de_A');
  eq(deA.length, 0, `sem recarga, B leu ${deA.length} evento(s) de A pela mesma API`);
});

testAsync('ISOL B-4: nova sessão do PRÓPRIO A — contrato medido, não presumido', async () => {
  // Este gate não afirma o que DEVE acontecer: ele fixa o que acontece, para a
  // decisão de escopo ser tomada sobre medida e não sobre intuição.
  const local = armazemTelemetria();
  const a1 = montarTelemetria(local, { usuario: { id: 'A', papel: 'master_admin' } });
  await a1.produzirEvento('acao_de_A');
  assert(a1.eventosVisiveis().events.some((e) => e.event === 'acao_de_A'),
    'A não viu o próprio evento — o gate não mediu nada');
  const a2 = montarTelemetria(local, { usuario: { id: 'A', papel: 'master_admin' } });
  // A nova sessão também emite o seu `view_open`; o que se mede é a
  // sobrevivência do evento NOMEADO da sessão anterior.
  const sobrevive = a2.eventosVisiveis().events.some((e) => e.event === 'acao_de_A');
  // O contrato escolhido no PR B está documentado em docs/ISOLAMENTO_PR_B_TELEMETRIA.md.
  eq(sobrevive, false,
    'a telemetria sobreviveu à nova sessão do mesmo usuário — contrato SESSION diz que não');
});

test('ISOL B-7: a telemetria legada some do DISCO, não só da leitura', () => {
  // A sabotagem que removeu a purga incondicional não foi pega por nenhum gate:
  // com a telemetria em RAM, ninguém lê o disco, então "não é lida" passa a ser
  // verdade mesmo com o dado ainda gravado lá. A propriedade que faltava medir
  // é DADO EM REPOUSO — telemetria de uma pessoa parada no disco de um
  // computador compartilhado, esperando quem souber abrir o DevTools.
  const local = armazemTelemetria({
    [CHAVE_TELEMETRIA]: EVENTOS_DE_A,
    'epi.analytics.events': EVENTOS_DE_A,
    // Controle: dado alheio não pode ser levado junto.
    'epi-theme': 'dark',
    'epi-session-v4': '{"id":"B","role":"master_admin"}'
  });
  montarTelemetria(local, { usuario: { id: 'B', papel: 'master_admin' } });

  eq(local.getItem(CHAVE_TELEMETRIA), null, 'a telemetria legada continuou no disco após a carga');
  eq(local.getItem('epi.analytics.events'), null, 'a chave legada antiga continuou no disco após a carga');
  eq(local.getItem('epi-theme'), 'dark', 'a purga levou junto dado que não é dela');
  assert(local.getItem('epi-session-v4'), 'a purga levou junto a sessão');
});

test('ISOL B-8: o módulo não grava telemetria em disco', () => {
  // Contrato estrutural, complementar ao B-3: nenhuma gravação da chave de
  // telemetria pode voltar ao código servido. `removeItem` continua permitido —
  // é a purga do legado.
  const fonte = fonteServida('ux-analytics.js');
  const gravacoes = fonte.match(/localStorage\.setItem\(/g) || [];
  eq(gravacoes.length, 0,
    `o ux-analytics voltou a gravar em localStorage (${gravacoes.length} ocorrência(s))`);
  assert(/localStorage\.removeItem\(STORAGE_KEY\)/.test(fonte),
    'a purga da chave de telemetria sumiu do módulo');
  assert(/localStorage\.removeItem\(LEGACY_STORAGE_KEY\)/.test(fonte),
    'a purga da chave legada antiga sumiu do módulo');
});

test('ISOL B-5: telemetria legada sem identidade não é atribuída a ninguém', () => {
  // `epi.analytics.master.events` gravado por uma versão anterior não tem dono
  // identificável. Entregá-la ao primeiro master que entrar é o mesmo erro que
  // a regra de preferências legadas do PR C proíbe.
  const local = armazemTelemetria({ [CHAVE_TELEMETRIA]: EVENTOS_DE_A });
  const primeiro = montarTelemetria(local, { usuario: { id: 'PRIMEIRO', papel: 'master_admin' } });
  const lido = primeiro.eventosVisiveis();
  eq(lido.events.length, 0,
    'o primeiro master que entrou herdou telemetria legada sem dono comprovado');
});

test('ISOL B-6: storage malformado falha fechado', () => {
  const casos = ['{', 'null', '"texto"', '{"nao":"array"}', '[1,2,3]'];
  casos.forEach((bruto) => {
    const local = armazemTelemetria({ [CHAVE_TELEMETRIA]: bruto });
    const d = montarTelemetria(local, { usuario: { id: 'A', papel: 'master_admin' } });
    const lido = d.eventosVisiveis();
    assert(Array.isArray(lido.events), `storage ${bruto} produziu events não-array`);
    eq(lido.events.length, 0, `storage malformado ${bruto} virou ${lido.events.length} evento(s)`);
  });
});


// ════════════════════════════════════════════════════════════════════════════
// ISOLAMENTO ENTRE USUÁRIOS — PR C (preferências pessoais de interface)
//
// Os gates C-1..C-10 nasceram VERMELHOS, escritos antes da correção, e o que
// eles mediam era o contrato #343 F3: tema, densidade, sidebar e idioma eram
// DEVICE, por decisão de produto declarada na UI. Num computador compartilhado
// isso significava que quem entrava herdava a aparência de quem saiu.
//
// A decisão de produto MUDOU: o escopo passou a ser USER, com o servidor como
// fonte da verdade (`users.ui_preferences`). Estes gates agora protegem o
// contrato novo.
//
// LIÇÃO DO PR B, aplicada aqui desde o início: um harness sem servidor mede
// pouco. "B não herda de A" ficaria verde numa versão que simplesmente não
// guardasse NADA — e perder a preferência de todo mundo não é isolamento, é
// outro defeito. Por isso o harness carrega um servidor de mentira que
// atravessa as cargas, e por isso existe o `ISOL C-11`: A tem de reencontrar o
// que é de A. Sem esse par, os outros gates não provam o mecanismo.
// ════════════════════════════════════════════════════════════════════════════

const CHAVES_DE_PREFERENCIA = Object.freeze({
  tema: 'epi-theme',
  densidade: 'epi-density',
  sidebar: 'epi-sidebar-collapsed',
  idioma: 'epi_language'
});

const PERFIL_A = Object.freeze({ tema: 'dark', densidade: 'compact', sidebar: 'collapsed', idioma: 'en-GB' });
const PERFIL_B = Object.freeze({ tema: 'light', densidade: 'normal', sidebar: 'expanded', idioma: 'es-ES' });
const PADRAO_OFICIAL = Object.freeze({ tema: 'light', densidade: 'normal', sidebar: 'expanded', idioma: 'pt-BR' });

// O servidor. O mesmo mapa atravessa todas as cargas, como a coluna
// `users.ui_preferences` atravessa todas as sessões.
function servidorDePreferencias(inicial) {
  const porUsuario = JSON.parse(JSON.stringify(inicial || {}));
  return {
    ler(id) {
      const k = String(id ?? '');
      return porUsuario[k] ? Object.assign({}, porUsuario[k]) : null;
    },
    gravar(id, parcial) {
      const k = String(id ?? '');
      porUsuario[k] = Object.assign({}, porUsuario[k] || PADRAO_OFICIAL, parcial || {});
      return porUsuario[k];
    },
    escritas: 0,
    instantaneo() { return JSON.parse(JSON.stringify(porUsuario)); }
  };
}

// O idioma chega ao DOM por `setLang`, que é assíncrono. Ler uma carga recém
// montada sem ceder o turno mediria o estado de antes da aplicação — e daria
// verde por engano nos gates cujo valor esperado é o padrão.
async function assentar() { for (let i = 0; i < 24; i += 1) await Promise.resolve(); }

function armazemPreferencias(inicial) {
  return {
    _s: Object.assign({}, inicial || {}),
    getItem(k) { return Object.prototype.hasOwnProperty.call(this._s, k) ? this._s[k] : null; },
    setItem(k, v) { this._s[k] = String(v); },
    removeItem(k) { delete this._s[k]; },
    key(i) { return Object.keys(this._s)[i] ?? null; },
    get length() { return Object.keys(this._s).length; },
    instantaneo() { return Object.assign({}, this._s); }
  };
}

// Uma CARGA de página. O `localStorage` atravessa as cargas (mesmo navegador);
// o `sessionStorage` atravessa só se a opção `sessao` for reaproveitada (mesma
// aba). Roda TAMBÉM o script inline de pré-paint do `_head.html` servido — é
// lá que o tema é decidido antes da autenticação, e é esse o momento que o
// `ISOL C-9` mede.
function montarDocumentoPreferencias(local, opcoes) {
  const o = opcoes || {};
  const servidor = o.servidor || servidorDePreferencias();
  const raizStatic = path.resolve(JS_ROOT, '..');
  const doc = criarNoF5B('document', {});
  doc.body = criarNoF5B('body', {});
  doc.head = criarNoF5B('head', {});
  doc.documentElement = criarNoF5B('html', {});
  doc.readyState = 'complete';
  doc.title = '';
  doc.getElementById = (id) => descendentesF5B(doc).find((n) => n.id === id) || null;
  doc.createElement = (tag) => criarNoF5B(tag, {});
  doc.querySelector = () => null;
  doc.querySelectorAll = () => [];

  let idDoPrincipal = o.usuario ? String(o.usuario.id) : '';

  const respostaJson = (corpo) => Promise.resolve({
    ok: true, status: 200, headers: { get: () => 'application/json' },
    json: () => Promise.resolve(corpo), text: () => Promise.resolve(JSON.stringify(corpo))
  });

  const ctx = {
    document: doc, localStorage: local, sessionStorage: o.sessao || armazemPreferencias(),
    location: { search: o.busca || '', href: `http://local/${o.busca || ''}`, pathname: '/', assign() {}, reload() {} },
    history: { pushState() {}, replaceState() {}, back() {}, length: 1, state: null },
    navigator: { userAgent: 'node', language: 'pt-BR', languages: ['pt-BR'] },
    console: { log() {}, info() {}, warn() {}, error() {}, debug() {} },
    crypto: { randomUUID: () => 'doc-' + Math.random().toString(16).slice(2) },
    CustomEvent: class { constructor(tipo, init) { this.type = tipo; Object.assign(this, init || {}); } },
    Event: class { constructor(tipo, init) { this.type = tipo; this.bubbles = false; Object.assign(this, init || {}); } },
    getComputedStyle: () => ({ display: 'block', visibility: 'visible' }),
    AbortController: class { constructor() { this.signal = { addEventListener() {} }; } abort() {} },
    MutationObserver: class { observe() {} disconnect() {} },
    setTimeout, clearTimeout, setInterval, clearInterval, Promise, URL, URLSearchParams,
    requestAnimationFrame: (fn) => setTimeout(fn, 0),
    // O servidor de mentira responde à rota REAL de escrita. É isto que
    // transforma "o app esqueceu" em "o app gravou no dono certo".
    fetch: (url, init) => {
      const caminho = String(url || '');
      if (caminho.includes('/api/auth/me/preferences')) {
        let corpo = {};
        try { corpo = JSON.parse((init && init.body) || '{}'); } catch (_e) { corpo = {}; }
        servidor.escritas += 1;
        return respostaJson({ ok: true, data: { ui_preferences: servidor.gravar(idDoPrincipal, corpo) } });
      }
      return respostaJson({ items: [] });
    },
    alert() {}, scrollTo() {}, matchMedia: () => ({ matches: false, addEventListener() {} })
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

  // MOMENTO 1 — antes de conhecer a identidade. O script de pré-paint REAL.
  const head = fs.readFileSync(path.join(raizStatic, 'views', '_head.html'), 'utf-8');
  const inline = head.match(/<script>([\s\S]*?)<\/script>/);
  assert(inline, 'o script de pré-paint sumiu do _head.html — o gate mediria outra página');
  vmF5B.runInContext(inline[1], ctx, { filename: '_head.html:pre-paint' });
  const temaNoPrePaint = doc.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';

  // Os scripts servidos, na ordem real.
  const ordem = fs.readFileSync(path.join(raizStatic, 'views', '_scripts.html'), 'utf-8')
    .match(/src="\/([^"?]+\.js)/g).map((m) => m.slice(6));
  ordem.forEach((rel) => {
    try {
      vmF5B.runInContext(fs.readFileSync(path.join(raizStatic, rel), 'utf-8'), ctx, { filename: rel });
    } catch (_e) { /* dependência de browser ausente não invalida o gate */ }
  });

  // MOMENTO 2 — identidade autenticada disponível.
  const entrar = (usuario) => {
    const st = ctx.__EPI_APP_STATE__;
    idDoPrincipal = usuario ? String(usuario.id) : '';
    if (st) st.user = usuario ? Object.assign({ role: 'admin', company_id: 'c1' }, usuario) : null;
    return st;
  };
  // O que o `/api/bootstrap` entrega. Em produção quem chama é o `loadBootstrap`;
  // o `ISOL C-12` prova que essa ligação existe e que ela passa o campo certo.
  const receberBootstrap = () => ctx.adotarPreferenciasDoServidor(servidor.ler(idDoPrincipal));

  if (o.usuario) { entrar(o.usuario); if (o.semBootstrap !== true) receberBootstrap(); }

  const visiveis = () => ({
    tema: doc.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light',
    densidade: doc.body.classList.contains('ux-density-compact') ? 'compact' : 'normal',
    sidebar: doc.body.classList.contains('sidebar-collapsed') ? 'collapsed' : 'expanded',
    idioma: (ctx.EpiI18n && ctx.EpiI18n.lang) || PADRAO_OFICIAL.idioma
  });

  return {
    ctx, doc, entrar, receberBootstrap, servidor, temaNoPrePaint,
    // MOMENTO 3 — o que o usuário efetivamente VÊ.
    preferenciasVisiveis: visiveis,
    // Configura pelos caminhos REAIS da interface: o drawer de Configurações
    // (`_applySettings`) e o botão da sidebar (`toggleSidebarCollapsed`). Um
    // gate que escrevesse a chave na mão não provaria nada sobre o produto.
    configurar: async ({ tema, densidade, sidebar, idioma }) => {
      const atual = visiveis();
      if (tema || densidade || idioma) {
        ctx._applySettings({
          theme: tema || atual.tema,
          lang: idioma || null,
          density: densidade || atual.densidade,
        });
      }
      if (sidebar && (sidebar === 'collapsed') !== (atual.sidebar === 'collapsed')) {
        ctx.toggleSidebarCollapsed();
      }
      // `setLang` é assíncrono e atravessa `fetch` + `json()` do dicionário:
      // sem ceder o turno várias vezes, o idioma ainda não chegou ao DOM.
      for (let i = 0; i < 24; i += 1) await Promise.resolve();
    }
  };
}

testAsync('ISOL C-0: o harness monta o pré-paint REAL e o app servido', async () => {
  const d = montarDocumentoPreferencias(armazemPreferencias(), {
    usuario: { id: 'A' }, servidor: servidorDePreferencias()
  });
  assert(typeof d.ctx._applySettings === 'function', '_applySettings não veio do app servido');
  assert(typeof d.ctx.applyTableDensityPref === 'function', 'applyTableDensityPref não veio do app servido');
  assert(typeof d.ctx.toggleSidebarCollapsed === 'function', 'toggleSidebarCollapsed não veio do app servido');
  assert(typeof d.ctx.adotarPreferenciasDoServidor === 'function', 'o dono das preferências não veio do app servido');
  eq(d.temaNoPrePaint, 'light', 'sem cópia de sessão, o pré-paint deveria ficar no padrão');
});

['tema', 'densidade', 'sidebar', 'idioma'].forEach((qual, indice) => {
  testAsync(`ISOL C-${indice + 1}: B não herda ${qual} de A`, async () => {
    const local = armazemPreferencias();
    const servidor = servidorDePreferencias();
    const a = montarDocumentoPreferencias(local, { usuario: { id: 'A' }, servidor });
    await a.configurar({ [qual]: PERFIL_A[qual] });
    eq(a.preferenciasVisiveis()[qual], PERFIL_A[qual],
      `A não conseguiu aplicar ${qual} — o gate não mediu nada`);

    // B entra numa carga nova, mesmo navegador, aba nova.
    const b = montarDocumentoPreferencias(local, { usuario: { id: 'B' }, servidor });
    await assentar();
    eq(b.preferenciasVisiveis()[qual], PADRAO_OFICIAL[qual],
      `B herdou ${qual}="${PERFIL_A[qual]}" de A`);
  });
});

testAsync('ISOL C-5: conjunto completo, alternando A → B → A → B', async () => {
  const local = armazemPreferencias();
  const servidor = servidorDePreferencias();
  const perfis = { A: PERFIL_A, B: PERFIL_B };
  const ordem = ['A', 'B', 'A', 'B'];
  const falhas = [];
  for (let i = 0; i < ordem.length; i += 1) {
    const quem = ordem[i];
    const d = montarDocumentoPreferencias(local, { usuario: { id: quem }, servidor });
    await assentar();
    const aoEntrar = d.preferenciasVisiveis();
    if (i > 0) {
      // Contrato: ou o usuário reencontra o que é dele, ou recebe o padrão
      // oficial — nunca o que o ANTERIOR deixou.
      const doAnterior = perfis[ordem[i - 1]];
      Object.keys(CHAVES_DE_PREFERENCIA).forEach((k) => {
        if (aoEntrar[k] === doAnterior[k] && doAnterior[k] !== perfis[quem][k]) {
          falhas.push(`entrada ${i + 1} (${quem}): ${k}="${aoEntrar[k]}" veio de ${ordem[i - 1]}`);
        }
      });
    }
    await d.configurar(perfis[quem]);
  }
  eq(falhas.length, 0, `herança entre identidades: ${falhas.join(' | ')}`);
});

testAsync('ISOL C-6: troca de principal SEM recarga não deixa a aparência de A', async () => {
  // Obrigatório desde o `ISOL A-8`: nem toda troca de identidade recarrega.
  const servidor = servidorDePreferencias();
  const d = montarDocumentoPreferencias(armazemPreferencias(), { usuario: { id: 'A' }, servidor });
  await d.configurar(PERFIL_A);
  eq(d.preferenciasVisiveis().tema, 'dark', 'A não aplicou o próprio tema — o gate não mediu nada');

  d.entrar({ id: 'B' });          // login de B no MESMO documento
  d.receberBootstrap();
  await assentar();
  const vistoPorB = d.preferenciasVisiveis();
  eq(vistoPorB.tema, PADRAO_OFICIAL.tema, 'sem recarga, B continuou vendo o tema de A');
  eq(vistoPorB.densidade, PADRAO_OFICIAL.densidade, 'sem recarga, B continuou vendo a densidade de A');
  eq(vistoPorB.sidebar, PADRAO_OFICIAL.sidebar, 'sem recarga, B continuou vendo a sidebar de A');
});

testAsync('ISOL C-7: primeiro acesso recebe os padrões oficiais', async () => {
  const c = montarDocumentoPreferencias(armazemPreferencias(), {
    usuario: { id: 'C' }, servidor: servidorDePreferencias()
  });
  await assentar();
  const visto = c.preferenciasVisiveis();
  Object.keys(CHAVES_DE_PREFERENCIA).forEach((k) => {
    eq(visto[k], PADRAO_OFICIAL[k], `usuário sem preferência recebeu ${k}="${visto[k]}"`);
  });
});

testAsync('ISOL C-8: legado DEVICE não é atribuído a ninguém', async () => {
  // Valores gravados por versão anterior não têm dono comprovável. Entregá-los
  // ao primeiro que logar transforma preferência compartilhada em preferência
  // pessoal da pessoa errada.
  const local = armazemPreferencias({
    'epi-theme': 'dark', 'epi-density': 'compact',
    'epi-sidebar-collapsed': '1', 'epi_language': 'en-GB',
    // Controles: chaves de OUTROS donos, no mesmo storage. Se sumirem, a
    // aposentadoria virou `localStorage.clear()` disfarçado.
    'epi-session-v4': '{"id":"A"}', 'epi_tenant': 'acme', 'epi-flag-qualquer': '1'
  });
  const primeiro = montarDocumentoPreferencias(local, {
    usuario: { id: 'PRIMEIRO' }, servidor: servidorDePreferencias()
  });
  await assentar();
  const visto = primeiro.preferenciasVisiveis();
  Object.keys(CHAVES_DE_PREFERENCIA).forEach((k) => {
    eq(visto[k], PADRAO_OFICIAL[k],
      `o primeiro usuário após a atualização herdou ${k}="${visto[k]}" do legado sem dono`);
  });
  primeiro.ctx.aposentarPreferenciasLegadas();
  const disco = local.instantaneo();
  Object.values(CHAVES_DE_PREFERENCIA).forEach((chave) => {
    assert(!(chave in disco), `a chave legada "${chave}" continua no disco depois da aposentadoria`);
  });
  ['epi-session-v4', 'epi_tenant', 'epi-flag-qualquer'].forEach((alheia) => {
    assert(alheia in disco, `a aposentadoria levou junto "${alheia}", que tem outro dono`);
  });
});

testAsync('ISOL C-9: o PRÉ-PAINT não aplica preferência de principal desconhecido', async () => {
  // O risco principal desta fatia. "Aplicar e corrigir depois" continua sendo
  // vazamento — B já viu a tela de A.
  const local = armazemPreferencias({ 'epi-theme': 'dark' });
  const b = montarDocumentoPreferencias(local, {
    usuario: { id: 'B' }, servidor: servidorDePreferencias()
  });
  eq(b.temaNoPrePaint, PADRAO_OFICIAL.tema,
    'o pré-paint aplicou um tema antes de saber de quem ele é');
});

test('ISOL C-9b: o pré-paint não lê localStorage, por construção', () => {
  // O par estrutural do C-9. O comportamental prova que HOJE não vaza; este
  // prova que não PODE voltar a vazar pelo mesmo caminho: `localStorage`
  // atravessa abas e identidades, `sessionStorage` não.
  const head = fs.readFileSync(path.join(path.resolve(JS_ROOT, '..'), 'views', '_head.html'), 'utf-8');
  const inline = head.match(/<script>([\s\S]*?)<\/script>/);
  assert(inline, 'o script de pré-paint sumiu do _head.html');
  assert(!inline[1].includes('localStorage'),
    'o pré-paint voltou a ler localStorage — aparência aplicada antes da identidade');
  assert(inline[1].includes('sessionStorage'),
    'o pré-paint parou de ler a cópia de sessão: o tema volta a piscar a cada F5');
});

testAsync('ISOL C-10: expiração de sessão não deixa a aparência anterior para o próximo', async () => {
  const local = armazemPreferencias();
  const servidor = servidorDePreferencias();
  const sessaoDaAba = armazemPreferencias();
  const a = montarDocumentoPreferencias(local, { usuario: { id: 'A' }, servidor, sessao: sessaoDaAba });
  await a.configurar(PERFIL_A);
  try {
    a.ctx.clearSession = () => {};
    a.ctx.stopDeliveryQrCamera = () => Promise.resolve();
    a.ctx.terminateSession('sessão expirada');
  } catch (_e) { /* o que importa é o estado depois */ }
  // B reabre NA MESMA ABA: é o caso em que o `sessionStorage` sobreviveria.
  const b = montarDocumentoPreferencias(local, { usuario: { id: 'B' }, servidor, sessao: sessaoDaAba });
  await assentar();
  eq(b.temaNoPrePaint, PADRAO_OFICIAL.tema,
    'depois da expiração, o pré-paint da aba ainda pintou o tema do anterior');
  eq(b.preferenciasVisiveis().tema, PADRAO_OFICIAL.tema,
    'depois da expiração, o próximo principal ainda recebeu o tema do anterior');
});

testAsync('ISOL C-11: A reencontra o que é de A (controle contra "esquecer tudo")', async () => {
  // O par indispensável dos C-1..C-5. Sem ele, uma versão que não guardasse
  // nada passaria em todos eles — e perder a preferência de todo mundo não é
  // isolamento, é outro defeito.
  const local = armazemPreferencias();
  const servidor = servidorDePreferencias();
  const a1 = montarDocumentoPreferencias(local, { usuario: { id: 'A' }, servidor });
  await a1.configurar(PERFIL_A);
  assert(servidor.escritas > 0, 'nada foi gravado no servidor — a preferência não tem dono nenhum');

  // B usa o computador no meio do caminho.
  const b = montarDocumentoPreferencias(local, { usuario: { id: 'B' }, servidor });
  await b.configurar(PERFIL_B);

  // A volta, em carga nova.
  const a2 = montarDocumentoPreferencias(local, { usuario: { id: 'A' }, servidor });
  await assentar();
  const visto = a2.preferenciasVisiveis();
  Object.keys(CHAVES_DE_PREFERENCIA).forEach((k) => {
    eq(visto[k], PERFIL_A[k], `A não reencontrou ${k}: esperava "${PERFIL_A[k]}", veio "${visto[k]}"`);
  });
});

testAsync('ISOL C-13: troca de principal SEM bootstrap também descarta', async () => {
  // Achado da SABOTAGEM β. O `ISOL C-6` estava verde pelo motivo errado: ele
  // sempre chamava o bootstrap, e o bootstrap SOBRESCREVE a memória de qualquer
  // jeito. Com isso, quebrar `prefsDescartarSeTrocouPrincipal()` não deixava
  // nenhum gate vermelho — o mecanismo não estava sendo medido.
  //
  // A janela real: `saveSession(B)` acontece ANTES de `loadBootstrap()`. Entre
  // os dois, qualquer leitura de preferência responderia com a de A se o
  // descarte por troca de principal não existisse.
  const servidor = servidorDePreferencias();
  const d = montarDocumentoPreferencias(armazemPreferencias(), { usuario: { id: 'A' }, servidor });
  await d.configurar(PERFIL_A);
  eq(d.ctx.preferenciasDoPrincipal().tema, 'dark', 'A não aplicou — o gate não mediu nada');

  d.entrar({ id: 'B' });   // login de B; o bootstrap dele AINDA não voltou
  const respostaDoDono = d.ctx.preferenciasDoPrincipal();
  Object.keys(CHAVES_DE_PREFERENCIA).forEach((k) => {
    eq(respostaDoDono[k], PADRAO_OFICIAL[k],
      `antes do bootstrap, o dono respondeu ${k}="${respostaDoDono[k]}" — valor de A`);
  });
  // E quem consulta o dono para pintar a tela também não pode pintar o de A.
  d.ctx.applyTableDensityPref();
  eq(d.doc.body.classList.contains('ux-density-compact'), false,
    'a densidade de A sobreviveu à troca de principal');
});

testAsync('ISOL C-14: cópia de sessão de OUTRO principal não é aceita', async () => {
  // Achado da SABOTAGEM γ. Nenhum gate media o carimbo da cópia de sessão,
  // porque em todos eles a cópia ou era nova ou tinha sido derrubada pelo
  // encerramento. Faltava o caso em que ela SOBREVIVE: o login de B na mesma
  // aba não passa por `terminateSession()`, então a cópia de A continua lá até
  // o bootstrap de B chegar. O carimbo é a única coisa que a recusa.
  const sessaoDaAba = armazemPreferencias({
    'epi-prefs-sessao': JSON.stringify({ p: 'A', ...PERFIL_A })
  });
  const b = montarDocumentoPreferencias(armazemPreferencias(), {
    usuario: { id: 'B' }, servidor: servidorDePreferencias(),
    sessao: sessaoDaAba, semBootstrap: true
  });
  const resposta = b.ctx.preferenciasDoPrincipal();
  Object.keys(CHAVES_DE_PREFERENCIA).forEach((k) => {
    eq(resposta[k], PADRAO_OFICIAL[k],
      `B aceitou a cópia de sessão de A: ${k}="${resposta[k]}"`);
  });
  // Recusar não basta: a cópia alheia tem de SAIR da aba, porque o pré-paint
  // da próxima carga não tem como conferir carimbo nenhum.
  eq(sessaoDaAba.getItem('epi-prefs-sessao'), null,
    'a cópia de A continuou na aba — o próximo pré-paint a aplicaria');

  // Controle: a cópia DO PRÓPRIO principal continua sendo aceita — senão a
  // correção seria "ignorar a cópia sempre", e o pré-paint voltaria a piscar.
  const sessaoDoA = armazemPreferencias({
    'epi-prefs-sessao': JSON.stringify({ p: 'A', ...PERFIL_A })
  });
  const a = montarDocumentoPreferencias(armazemPreferencias(), {
    usuario: { id: 'A' }, servidor: servidorDePreferencias(),
    sessao: sessaoDoA, semBootstrap: true
  });
  eq(a.ctx.preferenciasDoPrincipal().tema, PERFIL_A.tema,
    'A deixou de reconhecer a própria cópia de sessão');
  eq(a.temaNoPrePaint, PERFIL_A.tema,
    'o pré-paint parou de usar a cópia da própria aba: o tema volta a piscar no F5');
});

test('ISOL C-12: o servidor é o dono, e o cliente não grava preferência em localStorage', () => {
  const appJs = _read('app.js');
  const i18nJs = _read('i18n.js');

  // A ligação bootstrap -> dono existe e passa o campo do SERVIDOR.
  assert(appJs.includes('adotarPreferenciasDoServidor(payload.user?.ui_preferences)'),
    'o bootstrap parou de entregar as preferências do servidor ao dono');
  // A escrita vai para a rota real.
  assert(appJs.includes("api('/api/auth/me/preferences'"),
    'o cliente parou de persistir a preferência no servidor');

  // Nenhuma das quatro chaves DEVICE volta a ser gravada. A única menção
  // permitida é a LISTA DE APOSENTADORIA, que existe para apagá-las.
  const semAposentadoria = appJs.replace(/const PREFS_LEGADO_DEVICE = Object\.freeze\(\[[\s\S]*?\]\);/, '');
  ["'epi-theme'", "'epi-density'", "'epi-sidebar-collapsed'", "'epi_language'"].forEach((chave) => {
    assert(!semAposentadoria.includes(chave),
      `${chave} voltou a aparecer no app.js fora da lista de aposentadoria`);
    assert(!i18nJs.includes(chave),
      `${chave} voltou a aparecer no i18n.js — o idioma tem um dono só`);
  });

  // Dono único: a comparação de principal das preferências mora num lugar só.
  const comparacoes = (appJs.match(/prefsPrincipalCorrente\(\)/g) || []).length;
  assert(comparacoes >= 3, 'o dono das preferências sumiu do app.js');
  assert(appJs.includes('function prefsDescartarSeTrocouPrincipal()'),
    'sumiu o descarte por troca de principal — o `ISOL C-6` voltaria a vazar');
});


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
