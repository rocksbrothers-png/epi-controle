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
globalThis.location = { search: '' };
globalThis.document = { querySelector() { return null; }, createElement() { return {}; } };

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
  'modules/auth.js'
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
  if (!cond) throw new Error(msg || 'assertion failed');
}
function eq(a, b, msg) {
  if (a !== b) throw new Error((msg || 'eq') + ` — esperado ${JSON.stringify(b)}, obtido ${JSON.stringify(a)}`);
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

// ── Relatório ─────────────────────────────────────────────────────────────
if (failures.length) {
  console.error(`\nFALHAS (${failures.length}):`);
  failures.forEach((f) => console.error(`  ✗ ${f.name}: ${f.message}`));
  console.error(`\n${passed} passaram, ${failures.length} falharam`);
  process.exit(1);
}
console.log(`${passed} testes JS passaram`);
process.exit(0);
