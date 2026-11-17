'use strict';
// UBX Compras P1 — caracterização da apresentação de status de Compras.
//
// PURCHASE_STATUS_LABELS, ITEM_STATUS_LABELS, PO_STEPPER_STEPS, PO_STEP_INDEX,
// buildPoStepper e purchaseStatusBadge (modules/purchases/ui/purchase-status-view.js)
// e PURCHASE_BUYER_QUOTE_STATUSES / isBuyerQuotationStatus
// (modules/purchases/business/purchase-status-rules.js) rodam num contexto
// isolado com as dependências REAIS da página: o motor de tradução do
// static/i18n.js com os cinco catálogos (pt-BR de fallback) e dsStepper de
// views/ui-helpers.js. Nada de DOM nem de rede: as funções são puras.
//
// A referência "antes" é a cópia literal do app.js
// (fixtures/app-before-ubx-purchases-p1.js.txt); a "atual" é o que a página
// carrega hoje (os módulos, ou o próprio app.js enquanto a extração não existe).
// Cada entrada roda nas duas e o resultado (valor ou exceção) tem de ser
// idêntico nos cinco idiomas, sem o motor de idioma, com idioma não suportado
// e depois de trocar o idioma sem recriar os mapas (os rótulos são getters).
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const STATIC = path.resolve(__dirname, '..', '..');
const LOCALES = ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO'];
const read = (rel) => fs.readFileSync(path.join(STATIC, rel), 'utf8');
const exists = (rel) => fs.existsSync(path.join(STATIC, rel));
const CATALOGS = Object.fromEntries(LOCALES.map((l) => [l, JSON.parse(read(`i18n/${l}.json`))]));
const FIXTURE = 'js/test/fixtures/app-before-ubx-purchases-p1.js.txt';
const VIEW = 'js/modules/purchases/ui/purchase-status-view.js';
const RULES = 'js/modules/purchases/business/purchase-status-rules.js';
const CONSTS = ['PURCHASE_STATUS_LABELS', 'ITEM_STATUS_LABELS', 'PO_STEPPER_STEPS', 'PO_STEP_INDEX', 'PURCHASE_BUYER_QUOTE_STATUSES'];
const FUNCS = ['buildPoStepper', 'isBuyerQuotationStatus', 'purchaseStatusBadge'];
const XSS = '<img src=x onerror=alert(1)>';

function balanced(source, start, open, close) {
  let depth = 0;
  for (let i = source.indexOf(open, start); i < source.length; i += 1) {
    if (source[i] === open) { depth += 1; }
    if (source[i] === close) { depth -= 1; if (depth === 0) { return i + 1; } }
  }
  throw new Error('declaração sem fim');
}

function extractDeclaration(source, name) {
  const fn = new RegExp(`^function ${name}\\(`, 'm').exec(source);
  if (fn) { return source.slice(fn.index, balanced(source, source.indexOf(') {', fn.index) + 2, '{', '}')); }
  const decl = new RegExp(`^const ${name} = ([\\[{])`, 'm').exec(source);
  if (!decl) { throw new Error(`declaração ${name} não encontrada no app.js`); }
  const open = decl[1];
  const end = balanced(source, decl.index + decl[0].length - 1, open, open === '[' ? ']' : '}');
  return source.slice(decl.index, end) + ';';
}

// Fonte "atual": os módulos, se já existem; senão, as declarações vivas do app.js.
function currentSource() {
  if (exists(VIEW) && exists(RULES)) { return null; }
  const app = read('app.js');
  return [...CONSTS, ...FUNCS].map((name) => extractDeclaration(app, name)).join('\n');
}

function buildContext(lang, impl, mutation) {
  const ctx = { JSON, Number, String, Object, Array, Symbol, Error, TypeError, Math, isNaN };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  if (lang !== null) {
    // 'vazio': catálogos sem chaves — o motor devolve o texto de fallback do código.
    ctx.__CATALOGS__ = lang === 'vazio' ? Object.fromEntries(LOCALES.map((l) => [l, {}])) : CATALOGS;
    const i18n = read('i18n.js');
    vm.runInContext([
      "const FALLBACK = 'pt-BR'; const _pluralCount = Symbol('numeric plural count');",
      `let _lang = ${JSON.stringify(LOCALES.includes(lang) ? lang : 'pt-BR')};`,
      "let _active = __CATALOGS__[_lang]; let _fallback = __CATALOGS__['pt-BR'];",
      ...['_resolve', '_interpolate', '_message', 't', 'trEpi'].map((n) => extractFunction(i18n, n)),
      'var tr = trEpi;',
      'globalThis.__setLang = (l) => { _lang = l; _active = __CATALOGS__[l]; };'
    ].join('\n'), ctx);
  }
  vm.runInContext(read('js/views/ui-helpers.js'), ctx);
  let api;
  if (impl === 'before') {
    vm.runInContext(`globalThis.__API__ = (function () {\n${read(FIXTURE)}\nreturn { ${[...CONSTS, ...FUNCS].join(', ')} };\n})();`, ctx);
    api = ctx.__API__;
  } else {
    const legacy = currentSource();
    if (legacy) {
      vm.runInContext(`globalThis.__API__ = (function () {\n${legacy}\nreturn { ${[...CONSTS, ...FUNCS].join(', ')} };\n})();`, ctx);
      api = ctx.__API__;
    } else {
      let rules = read(RULES); let view = read(VIEW);
      if (mutation) {
        const [file, from, to] = mutation;
        const target = file === 'rules' ? rules : view;
        if (!target.includes(from)) { throw new Error('mutação sem alvo: ' + from); }
        if (file === 'rules') { rules = rules.replace(from, to); } else { view = view.replace(from, to); }
      }
      vm.runInContext(rules, ctx);
      vm.runInContext(view, ctx);
      const ui = ctx.__EPI_PURCHASE_STATUS_UI__; const biz = ctx.__EPI_PURCHASE_STATUS_RULES__;
      api = {
        PURCHASE_STATUS_LABELS: ui.PURCHASE_STATUS_LABELS, ITEM_STATUS_LABELS: ui.ITEM_STATUS_LABELS,
        PO_STEPPER_STEPS: ui.PO_STEPPER_STEPS, PO_STEP_INDEX: ui.PO_STEP_INDEX,
        PURCHASE_BUYER_QUOTE_STATUSES: biz.PURCHASE_BUYER_QUOTE_STATUSES,
        // As globais legadas são o que o app.js chama: compara-se por elas.
        buildPoStepper: (...a) => ctx.buildPoStepper(...a),
        isBuyerQuotationStatus: (...a) => ctx.isBuyerQuotationStatus(...a),
        purchaseStatusBadge: (...a) => ctx.purchaseStatusBadge(...a)
      };
    }
  }
  return { ctx, api };
}

function extractFunction(source, name) {
  const match = new RegExp(`^[ \\t]*(?:async\\s+)?function ${name}\\(`, 'm').exec(source);
  if (!match) { throw new Error(`função ${name} não encontrada`); }
  return source.slice(match.index, balanced(source, source.indexOf(') {', match.index) + 2, '{', '}'));
}

// Valores de outro contexto vm têm outros protótipos: normaliza para o realm do Node.
function norm(value) {
  if (Array.isArray(value)) { return Array.from(value, norm); }
  if (value === undefined) { return ['undefined']; }
  if (typeof value === 'function') { return ['function', value.name]; }
  if (typeof value === 'number' && Number.isNaN(value)) { return ['NaN']; }
  if (value && typeof value === 'object') { return ['object', Object.keys(value).map((k) => [k, norm(value[k])])]; }
  return value;
}
const settle = (fn) => { try { return ['ok', norm(fn())]; } catch (error) { return ['threw', error.name, error.message]; } };

function statuses() {
  const keys = new Set();
  const fixture = read(FIXTURE);
  for (const m of fixture.matchAll(/get ([a-z_]+)\(\)/g)) { keys.add(m[1]); }
  for (const m of fixture.matchAll(/\b([a-z_]+): [0-9]/g)) { keys.add(m[1]); }
  for (const m of fixture.matchAll(/'([a-z_]+)'/g)) { keys.add(m[1]); }
  return [...keys, undefined, null, '', 0, 1, false, true, NaN, ' approved', 'APPROVED', 'approved ', 'po_generated', 'ordered',
    '__proto__', 'constructor', 'toString', 'hasOwnProperty', 'valueOf', 'label', 'length', '0', XSS, ['approved'], ['quoted'],
    { toString() { return 'quoted'; } }, 'waiting_requester_correction', 'cancelled', 'unknown_status'];
}
const EXTRAS = ['', 'Até 2026-11-20', XSS, 0, null, undefined, '0', false, 'a — b', '$&'];

function describe(map) {
  if (!map || typeof map !== 'object') { return ['not-object', typeof map]; }
  return Object.keys(map).map((k) => {
    const d = Object.getOwnPropertyDescriptor(map, k);
    return [k, d.get ? 'getter' : 'value', d.enumerable, d.configurable, d.get ? null : JSON.stringify(d.value)];
  });
}

function observe(lang, impl, mutation) {
  const { ctx, api } = buildContext(lang, impl, mutation);
  const out = [];
  const snapshot = (label) => {
    out.push([label, 'shape', CONSTS.map((c) => [c, Array.isArray(api[c]), settle(() => describe(api[c]))])]);
    out.push([label, 'steps', settle(() => api.PO_STEPPER_STEPS.map((s) => s.label))]);
    out.push([label, 'quoteStatuses', settle(() => [...api.PURCHASE_BUYER_QUOTE_STATUSES])]);
    for (const status of statuses()) {
      const key = typeof status === 'object' && status !== null ? ['obj', String(status)] : [typeof status, String(status)];
      out.push([label, key,
        settle(() => api.PURCHASE_STATUS_LABELS[status]),
        settle(() => api.ITEM_STATUS_LABELS[status]),
        settle(() => api.buildPoStepper(status)),
        settle(() => api.isBuyerQuotationStatus(status)),
        settle(() => api.purchaseStatusBadge(status)),
        EXTRAS.map((extra) => settle(() => api.purchaseStatusBadge(status, extra)))]);
    }
    out.push([label, 'noArgs', settle(() => api.buildPoStepper()), settle(() => api.isBuyerQuotationStatus()), settle(() => api.purchaseStatusBadge())]);
  };
  snapshot(String(lang));
  // Os rótulos são getters: a troca de idioma vale sem recriar os mapas.
  if (ctx.__setLang) {
    const other = lang === 'fr-FR' ? 'nb-NO' : 'fr-FR';
    ctx.__setLang(other);
    snapshot(`${lang}→${other}`);
  }
  return out;
}

const VARIANTS = [...LOCALES, 'xx-XX', 'vazio', null];

// Compara "antes" × "atual" em todas as variantes; devolve [observações, resultados].
// Uma observação de status agrupa 15 resultados (2 rótulos, stepper, regra e 11 badges).
function compareAll(mutation) {
  const assert = require('assert');
  let comparisons = 0; let results = 0;
  const leaves = (v) => (Array.isArray(v) && (v[0] === 'ok' || v[0] === 'threw') ? 1 : Array.isArray(v) ? v.reduce((n, x) => n + leaves(x), 0) : 0);
  for (const lang of VARIANTS) {
    const before = observe(lang, 'before');
    const now = observe(lang, 'current', mutation);
    assert.strictEqual(now.length, before.length, `${lang}: quantidade de observações`);
    for (let i = 0; i < before.length; i += 1) {
      assert.deepStrictEqual(norm(now[i]), norm(before[i]), `${lang}: observação ${i} difere`);
      comparisons += 1; results += leaves(norm(before[i]));
    }
  }
  return [comparisons, results];
}

function contracts() {
  const assert = require('assert');
  const app = read('app.js');
  if (!exists(VIEW)) { return; }
  for (const name of FUNCS) {
    assert(!new RegExp(`^function ${name}\\(`, 'm').test(app), `${name} ainda declarada no app.js`);
  }
  for (const name of ['PO_STEPPER_STEPS', 'PO_STEP_INDEX', 'PURCHASE_BUYER_QUOTE_STATUSES']) {
    assert(!new RegExp(`\\b${name}\\b`).test(app), `${name} ainda referenciada no app.js`);
  }
  assert(app.includes('const PURCHASE_STATUS_LABELS = globalThis.__EPI_PURCHASE_STATUS_UI__.PURCHASE_STATUS_LABELS;'), 'alias de PURCHASE_STATUS_LABELS');
  assert(app.includes('const ITEM_STATUS_LABELS = globalThis.__EPI_PURCHASE_STATUS_UI__.ITEM_STATUS_LABELS;'), 'alias de ITEM_STATUS_LABELS');
  const { ctx } = buildContext('pt-BR', 'current');
  for (const ns of ['__EPI_PURCHASE_STATUS_UI__', '__EPI_PURCHASE_STATUS_RULES__']) {
    assert(Object.isFrozen(ctx[ns]), `${ns} congelado`);
  }
  for (const name of FUNCS) { assert.strictEqual(typeof ctx[name], 'function', `global legada ${name}`); }
  // Os mapas eram de bloco no app.js: views/purchases.js lê globalThis.ITEM_STATUS_LABELS
  // e cai no fallback {}. Publicá-los no globalThis mudaria essa tela; não publicar.
  for (const name of CONSTS) { assert.strictEqual(ctx[name], undefined, `${name} não pode virar global`); }
  const scripts = read('views/_scripts.html');
  const pos = (s) => { const i = scripts.indexOf(s); assert(i >= 0, `${s} ausente em _scripts.html`); return i; };
  assert(pos('/js/views/ui-helpers.js') < pos('/js/modules/purchases/ui/purchase-status-view.js'));
  assert(pos('/js/modules/purchases/business/purchase-status-rules.js') < pos('/app.js?'));
  assert(pos('/js/modules/purchases/ui/purchase-status-view.js') < pos('/app.js?'));
}

module.exports = function register({ test, assert }) {
  test('UBX Compras P1: status, stepper e badge idênticos à cópia literal nos 5 idiomas', () => {
    const [observations, results] = compareAll();
    assert(observations > 800 && results > 10000, `cobertura insuficiente: ${observations}/${results}`);
    console.log(`    Compras P1: ${observations} observações, ${results} resultados comparados, zero divergências`);
  });
  test('UBX Compras P1: contratos do módulo, globais legadas e ordem de carga', () => contracts());
};
module.exports.compareAll = compareAll;
