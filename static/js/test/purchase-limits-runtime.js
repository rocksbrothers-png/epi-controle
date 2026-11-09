'use strict';
// CO-1 — cartão de limite de alçada (modules/purchases/{business,integrations,ui}/purchase-limits-*).
//
// Executável sozinho (node static/js/test/purchase-limits-runtime.js) e pelo
// pytest (tests/test_co1_purchase_limits_web.py). Carrega os módulos REAIS num
// contexto vm com DOM falso e cliente HTTP espião. Fixa: dinheiro como texto
// (sem float), separadores por idioma, cartão oculto sem permissão, leitura e
// gravação pelo cliente único, versão otimista, 409 recarrega, entrada inválida
// não chama a API, remoção pede confirmação e resposta obsoleta é descartada.
const fs = require('fs'), path = require('path'), vm = require('vm'), assert = require('assert');

const JS_ROOT = path.resolve(__dirname, '..');
const MODULES = [
  'modules/purchases/business/purchase-limits-rules.js',
  'modules/purchases/integrations/purchase-limits-api.js',
  'modules/purchases/ui/purchase-limits-view.js'
];
const IDS = ['purchase-limit-config-card', 'purchase-limit-company', 'purchase-limit-current', 'purchase-limit-meta',
  'purchase-limit-input', 'purchase-limit-save-btn', 'purchase-limit-remove-btn', 'purchase-limit-feedback'];

function makeEnv({ permissions = ['purchase_limits:manage'], lang = 'pt-BR', confirm = true } = {}) {
  const listeners = {};
  const nodes = Object.fromEntries(IDS.map((id) => [id, {
    id, hidden: false, disabled: false, value: '', textContent: '', dataset: {},
    listeners: {}, addEventListener(type, fn) { this.listeners[type] = fn; },
    closest: () => (id === 'purchase-limit-config-card' ? null : null)
  }]));
  const calls = [];
  const env = {
    nodes, calls, responses: [],
    state: { user: { id: 1, role: 'general_admin', company_id: 1 }, permissions, companies: [{ id: 1, name: 'ACME' }] }
  };
  const sandbox = {
    Promise, JSON, Object, Array, String, Number, Error, Intl, Date, encodeURIComponent,
    __EPI_APP_STATE__: env.state,
    __EPI_SHARED_DIALOGS__: { confirmDestructive: async () => confirm },
    trEpi: (key, fallback, vars) => String(fallback).replace(/\{(\w+)\}/g, (m, k) => (vars && k in vars ? vars[k] : m)),
    api: (url, opts) => {
      calls.push([url, opts ? opts.method : 'GET', opts && opts.body ? JSON.parse(opts.body) : null]);
      const next = env.responses.shift();
      if (!next) { return Promise.reject(new Error('sem resposta configurada')); }
      return next.error ? Promise.reject(next.error) : Promise.resolve(next.data);
    },
    document: {
      readyState: 'complete',
      documentElement: { lang },
      getElementById: (id) => nodes[id] || null,
      addEventListener: (type, fn) => { listeners[type] = fn; }
    }
  };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  for (const rel of MODULES) {
    vm.runInContext(fs.readFileSync(path.join(JS_ROOT, rel), 'utf-8'), sandbox, { filename: rel });
  }
  env.sandbox = sandbox;
  env.rules = sandbox.__EPI_PURCHASE_LIMITS_RULES__;
  env.view = sandbox.__EPI_PURCHASE_LIMITS_VIEW__;
  env.fire = (type, detail) => listeners[type] && listeners[type]({ detail });
  return env;
}

const DATA = (over = {}) => ({ po_approval_threshold: '15000.00', currency: 'BRL', configured: true, version: 3,
  updated_at: '2026-11-09T12:00:00+00:00', updated_by_name: 'Admin Geral', can_manage: true, company_id: 1, ...over });

const tests = [];
const test = (name, fn) => tests.push([name, fn]);

test('regras: entrada vira texto canônico, sem float', () => {
  const { rules } = makeEnv();
  const ok = (raw, value) => assert.deepStrictEqual(JSON.parse(JSON.stringify(rules.normalizeLimitInput(raw))), { ok: true, value });
  ok('15000', '15000.00'); ok('15000,5', '15000.50'); ok('15000.55', '15000.55'); ok(' 0,01 ', '0.01');
  ok('000123', '123.00'); ok('999999999999.99', '999999999999.99');
  for (const bad of ['0', '0,00', '-1', '1.500,00', '1,500.00', '1.555', 'abc', '1e3', ',5', '5,']) {
    assert.strictEqual(rules.normalizeLimitInput(bad).ok, false, bad);
  }
  assert.strictEqual(rules.normalizeLimitInput('').code, 'EMPTY');
  assert.strictEqual(rules.normalizeLimitInput('1000000000000').code, 'TOO_LARGE');
});

test('regras: formatação por idioma preserva os centavos exatos', () => {
  const { rules } = makeEnv();
  assert.strictEqual(rules.formatLimit('1234567.05', { group: '.', decimal: ',' }), '1.234.567,05');
  assert.strictEqual(rules.formatLimit('1234567.05', { group: ',', decimal: '.' }), '1,234,567.05');
  assert.strictEqual(rules.formatLimit('0.10', { group: ' ', decimal: ',' }), '0,10');
  assert.strictEqual(rules.formatLimit('lixo'), '');
  const d = rules.describeLimits({ po_approval_threshold: null, version: 0 });
  assert.strictEqual(d.configured, false);
  assert.strictEqual(rules.describeLimits({ po_approval_threshold: '10.5' }).configured, false);
});

test('sem purchase_limits:manage o cartão fica oculto e nada é pedido ao servidor', async () => {
  const env = makeEnv({ permissions: ['finance:view'] });
  await env.view.load();
  assert.strictEqual(env.nodes['purchase-limit-config-card'].hidden, true);
  assert.strictEqual(env.calls.length, 0);
});

test('carrega o limite da sessão e mostra valor, empresa e última alteração', async () => {
  const env = makeEnv();
  env.responses.push({ data: DATA() });
  env.fire('epi:viewchange', { view: 'configuracao' });
  await new Promise((r) => setImmediate(r));
  assert.deepStrictEqual(env.calls[0], ['/api/purchase-limits?actor_user_id=1', 'GET', null]);
  assert.strictEqual(env.nodes['purchase-limit-config-card'].hidden, false);
  assert.strictEqual(env.nodes['purchase-limit-current'].textContent, 'BRL 15.000,00');
  assert.strictEqual(env.nodes['purchase-limit-company'].textContent, 'ACME');
  assert.ok(env.nodes['purchase-limit-meta'].textContent.includes('Admin Geral'));
  assert.strictEqual(env.nodes['purchase-limit-remove-btn'].hidden, false);
  assert.strictEqual(env.nodes['purchase-limit-save-btn'].disabled, false);
});

test('sem limite configurado informa e esconde a remoção', async () => {
  const env = makeEnv({ lang: 'en-GB' });
  env.responses.push({ data: DATA({ po_approval_threshold: null, configured: false, version: 0, updated_at: null }) });
  await env.view.load();
  assert.ok(env.nodes['purchase-limit-current'].textContent.startsWith('Sem limite configurado'));
  assert.strictEqual(env.nodes['purchase-limit-remove-btn'].hidden, true);
});

test('can_manage falso no servidor bloqueia edição mesmo com o cartão visível', async () => {
  const env = makeEnv();
  env.responses.push({ data: DATA({ can_manage: false }) });
  await env.view.load();
  assert.strictEqual(env.nodes['purchase-limit-input'].disabled, true);
  assert.strictEqual(env.nodes['purchase-limit-save-btn'].disabled, true);
});

test('salvar envia texto canônico com a versão vista', async () => {
  const env = makeEnv();
  env.responses.push({ data: DATA() });
  await env.view.load();
  env.nodes['purchase-limit-input'].value = '20000,5';
  env.responses.push({ data: DATA({ po_approval_threshold: '20000.50', version: 4 }) });
  await env.view.onSave();
  await new Promise((r) => setImmediate(r));
  assert.deepStrictEqual(env.calls[1], ['/api/purchase-limits', 'POST', { actor_user_id: 1, value: '20000.50', expected_version: 3 }]);
  assert.strictEqual(env.nodes['purchase-limit-feedback'].textContent, 'Limite de alçada salvo.');
  assert.strictEqual(env.nodes['purchase-limit-current'].textContent, 'BRL 20.000,50');
  assert.strictEqual(env.nodes['purchase-limit-input'].value, '');
});

test('entrada inválida não chama a API', async () => {
  const env = makeEnv();
  env.responses.push({ data: DATA() });
  await env.view.load();
  for (const bad of ['0', '-5', '1.500,00', '']) {
    env.nodes['purchase-limit-input'].value = bad;
    await env.view.onSave();
  }
  assert.strictEqual(env.calls.length, 1);
  assert.ok(env.nodes['purchase-limit-feedback'].textContent.startsWith('Informe um valor maior que zero'));
});

test('409: mostra a mensagem do servidor e recarrega o valor vigente', async () => {
  const env = makeEnv();
  env.responses.push({ data: DATA() });
  await env.view.load();
  const conflict = Object.assign(new Error('O limite de alçada foi alterado por outro usuário. Recarregue e tente novamente.'), { status: 409 });
  env.responses.push({ error: conflict });
  env.responses.push({ data: DATA({ po_approval_threshold: '9999.00', version: 4 }) });
  env.nodes['purchase-limit-input'].value = '1';
  await env.view.onSave();
  await new Promise((r) => setImmediate(r));
  assert.strictEqual(env.calls.length, 3);
  assert.strictEqual(env.calls[2][1], 'GET');
  assert.strictEqual(env.nodes['purchase-limit-current'].textContent, 'BRL 9.999,00');
  assert.ok(env.nodes['purchase-limit-feedback'].textContent.includes('alterado por outro usuário'));
});

test('remoção exige confirmação e envia value null', async () => {
  const declined = makeEnv({ confirm: false });
  declined.responses.push({ data: DATA() });
  await declined.view.load();
  await declined.view.onRemove();
  assert.strictEqual(declined.calls.length, 1);

  const env = makeEnv();
  env.responses.push({ data: DATA() });
  await env.view.load();
  env.responses.push({ data: DATA({ po_approval_threshold: null, configured: false, version: 4 }) });
  await env.view.onRemove();
  await new Promise((r) => setImmediate(r));
  assert.deepStrictEqual(env.calls[1][2], { actor_user_id: 1, value: null, expected_version: 3 });
  assert.strictEqual(env.nodes['purchase-limit-feedback'].textContent, 'Limite de alçada removido.');
});

test('resposta obsoleta de carga anterior é descartada', async () => {
  const env = makeEnv();
  let resolveFirst;
  const first = new Promise((r) => { resolveFirst = r; });
  env.sandbox.api = (url) => { env.calls.push([url]); return env.calls.length === 1 ? first : Promise.resolve(DATA({ po_approval_threshold: '2.00' })); };
  const a = env.view.load();
  const b = env.view.load();
  await b;
  resolveFirst(DATA({ po_approval_threshold: '1.00' }));
  await a;
  assert.strictEqual(env.nodes['purchase-limit-current'].textContent, 'BRL 2,00');
});

(async () => {
  let failed = 0;
  for (const [name, fn] of tests) {
    try { await fn(); console.log(`ok - ${name}`); } catch (err) { failed += 1; console.error(`FALHA - ${name}: ${err.message}`); }
  }
  console.log(`${tests.length - failed}/${tests.length} testes da alçada (web) passaram`);
  process.exit(failed ? 1 : 0);
})();
