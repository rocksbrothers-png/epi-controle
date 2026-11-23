'use strict';
// UBX Fornecedores F1 — caracterização da importação de fornecedores.
//
// _parseSuppliersRows (modules/purchases/business/supplier-import-rules.js) e _loadSheetJS
// (modules/purchases/integrations/supplier-import-loader.js) rodam num contexto isolado com
// o motor de tradução REAL de static/i18n.js e os cinco catálogos (pt-BR de fallback). Só o
// que é do navegador é simulado: window/document (createElement, head.appendChild) e a
// chegada do script do SheetJS (onload/onerror disparados pelo teste).
//
// A referência "antes" é a cópia literal do app.js (fixtures/app-before-ubx-suppliers-f1.js.txt);
// a "atual" é o que a página carrega hoje (os módulos, ou o próprio app.js enquanto a
// extração não existe). Cada entrada roda nas duas e o resultado (valor, exceção, scripts
// injetados, mensagens) tem de ser idêntico nos cinco idiomas, com catálogos vazios, idioma
// não suportado e sem o motor de idioma.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const STATIC = path.resolve(__dirname, '..', '..');
const LOCALES = ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO'];
const read = (rel) => fs.readFileSync(path.join(STATIC, rel), 'utf8');
const exists = (rel) => fs.existsSync(path.join(STATIC, rel));
const CATALOGS = Object.fromEntries(LOCALES.map((l) => [l, JSON.parse(read(`i18n/${l}.json`))]));
const FIXTURE = 'js/test/fixtures/app-before-ubx-suppliers-f1.js.txt';
const RULES = 'js/modules/purchases/business/supplier-import-rules.js';
const LOADER = 'js/modules/purchases/integrations/supplier-import-loader.js';
const VARIANTS = [...LOCALES, 'xx-XX', 'vazio', null];

function balanced(source, start) {
  let depth = 0;
  for (let i = source.indexOf('{', start); i < source.length; i += 1) {
    if (source[i] === '{') { depth += 1; }
    if (source[i] === '}') { depth -= 1; if (depth === 0) { return i + 1; } }
  }
  throw new Error('bloco sem fim');
}

function extractFunction(source, name) {
  const match = new RegExp(`^[ \\t]*(?:async\\s+)?function ${name}\\(`, 'm').exec(source);
  if (!match) { throw new Error(`função ${name} não encontrada`); }
  return source.slice(match.index, balanced(source, source.indexOf(') {', match.index) + 2));
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

function buildContext(lang, impl, mutation) {
  const env = { appended: [], created: 0 };
  const ctx = { JSON, Number, String, Object, Array, Promise, Symbol, Error, TypeError, Math, isNaN };
  ctx.globalThis = ctx;
  ctx.window = ctx;
  ctx.document = {
    head: { appendChild(node) { env.appended.push(node); return node; } },
    createElement(tag) { env.created += 1; return { tag, src: '', onload: null, onerror: null }; }
  };
  vm.createContext(ctx);
  if (lang !== null) {
    ctx.__CATALOGS__ = lang === 'vazio' ? Object.fromEntries(LOCALES.map((l) => [l, {}])) : CATALOGS;
    const i18n = read('i18n.js');
    vm.runInContext([
      "const FALLBACK = 'pt-BR'; const _pluralCount = Symbol('numeric plural count');",
      `let _lang = ${JSON.stringify(LOCALES.includes(lang) ? lang : 'pt-BR')};`,
      "let _active = __CATALOGS__[_lang]; let _fallback = __CATALOGS__['pt-BR'];",
      ...['_resolve', '_interpolate', '_message', 't', 'trEpi'].map((n) => extractFunction(i18n, n)),
      'var tr = trEpi;'
    ].join('\n'), ctx);
  }
  let api;
  const wrap = (src) => {
    vm.runInContext(`globalThis.__API__ = (function () {\n${src}\nreturn { _loadSheetJS, _parseSuppliersRows };\n})();`, ctx);
    return ctx.__API__;
  };
  if (impl === 'before') {
    api = wrap(read(FIXTURE));
  } else if (!(exists(RULES) && exists(LOADER))) {
    const app = read('app.js');
    api = wrap(['_loadSheetJS', '_parseSuppliersRows'].map((n) => extractFunction(app, n)).join('\n'));
  } else {
    let rules = read(RULES); let loader = read(LOADER);
    if (mutation) {
      const [file, from, to] = mutation;
      const target = file === 'rules' ? rules : loader;
      if (!target.includes(from)) { throw new Error('mutação sem alvo: ' + from); }
      if (file === 'rules') { rules = rules.replace(from, to); } else { loader = loader.replace(from, to); }
    }
    vm.runInContext(rules, ctx);
    vm.runInContext(loader, ctx);
    api = {
      // _parseSuppliersRows era global (Annex B): compara-se pela global legada.
      _parseSuppliersRows: (...a) => ctx._parseSuppliersRows(...a),
      // _loadSheetJS era async de bloco: só no namespace.
      _loadSheetJS: (...a) => ctx.__EPI_SUPPLIER_IMPORT_LOADER__._loadSheetJS(...a)
    };
  }
  return { ctx, env, api };
}

const settle = (fn) => { try { return ['ok', norm(fn())]; } catch (error) { return ['threw', error.name, error.message]; } };

// Linhas como o app.js as entrega: CSV (cabeçalhos minúsculos, valores string) e XLS
// (sheet_to_json com defval '', cabeçalhos como vieram, valores numéricos/booleanos).
function rowSets() {
  const translated = ['Nome', 'Name', 'Nombre', 'Nom', 'Navn', 'NAVN', 'nombre'];
  const sets = [
    [],
    [{ nome: 'Fornecedor A', cnpj: '12.345.678/0001-90', contato: 'a@x.test' }],
    [{ name: 'Supplier B', CNPJ: '98765432000110', email: 'b@x.test' }],
    [{ Name: '  Espaços  ', Email: '  e@x.test ', cnpj: '  1  ' }],
    [{ NOME: 'Maiúsculo', CNPJ: '' }, { Nome: 'Capitalizado' }],
    [{ nome: '' }, { nome: '   ' }, {}, { cnpj: '1', email: 'x' }],
    [{ nome: 0 }, { nome: 123 }, { nome: 12345678000199, cnpj: 12345678000199 }, { nome: true }, { nome: false }],
    [{ nome: null }, { nome: undefined, name: 'Fallback' }, { nome: 'Obj', cnpj: { a: 1 } }, { nome: ['x', 'y'] }],
    [{ contact_name: 'Contato', nome: 'C' }, { contact_email: 'ce@x.test', nome: 'D' }, { Email: 'E@x', nome: 'E' }],
    [{ 'nome ': 'chave com espaço' }, { NoMe: 'misto' }, { Cnpj: '2', nome: 'F' }, { CONTATO: 'up', nome: 'G' }],
    [{ nome: 'Ordem', name: 'segundo', Name: 'terceiro', cnpj: 'c1', CNPJ: 'c2', contato: 'p1', email: 'p2' }],
    [{ nome: '<b>x</b>', cnpj: '"aspas"', email: "o'neil@x" }, { nome: 'Olá ção' }],
    [{ toString: 'x', nome: 'proto' }, { constructor: 'y', name: 'proto2' }],
    translated.map((h, i) => ({ [h]: `Traduzido ${i}` })),
    // Linhas como o caminho CSV monta (cabeçalhos já em minúsculas, colunas faltando viram '').
    [{ nome: 'CSV 1', cnpj: '', contato: '' }, { nome: '', cnpj: '3', contato: 'z' }],
    // sheet_to_json com defval: '' e números.
    [{ Nome: 'XLS', CNPJ: 11222333000181, Email: '' }, { Nome: '', CNPJ: '', Email: '' }]
  ];
  return sets;
}
const BAD_INPUTS = [null, undefined, 'texto', 42, {}, [null], [undefined], [1, 'a']];

function observeParse(api) {
  const out = rowSets().map((rows) => settle(() => api._parseSuppliersRows(rows)));
  out.push(...BAD_INPUTS.map((input) => settle(() => api._parseSuppliersRows(input))));
  out.push(settle(() => api._parseSuppliersRows()));
  return out;
}

// Resultado de uma Promise; 'pending' quando nada a resolve (p. ex. onerror que lança antes de rejeitar).
async function settleAsync(promise) {
  const PENDING = Symbol('pending');
  try {
    const value = await Promise.race([promise, new Promise((r) => setTimeout(() => r(PENDING), 5))]);
    return value === PENDING ? ['pending'] : ['resolved', norm(value)];
  } catch (error) { return ['rejected', error?.name, error?.message]; }
}

// Dispara onload/onerror como o navegador faria; registra se o handler lançou.
function fire(node, event, arg) {
  try { node[event](arg); return ['ok']; } catch (error) { return ['threw', error.name, error.message]; }
}

const MARK = { id: 'XLSX-STUB', utils: {} };

async function observeLoader(lang, impl, mutation) {
  const out = [];
  // 1. SheetJS já carregado: devolve o mesmo objeto sem injetar script.
  {
    const { ctx, env, api } = buildContext(lang, impl, mutation);
    ctx.XLSX = MARK;
    const r = await settleAsync(api._loadSheetJS());
    out.push(['preloaded', r, env.created, env.appended.length]);
  }
  // 2. Valores "falsos" em window.XLSX não contam como carregado.
  for (const falsy of [0, '', null, false]) {
    const { ctx, env, api } = buildContext(lang, impl, mutation);
    ctx.XLSX = falsy;
    const p = api._loadSheetJS();
    const node = env.appended[0];
    ctx.XLSX = MARK; const fired = fire(node, 'onload');
    out.push(['falsy', String(falsy), fired, await settleAsync(p), env.appended.map((n) => [n.tag, n.src])]);
  }
  // 3. Carga com sucesso: script injetado com a URL, resolve com window.XLSX.
  {
    const { ctx, env, api } = buildContext(lang, impl, mutation);
    const p = api._loadSheetJS();
    const node = env.appended[0];
    out.push(['before-load', env.created, env.appended.map((n) => [n.tag, n.src, typeof n.onload, typeof n.onerror])]);
    ctx.XLSX = MARK; const fired = fire(node, 'onload');
    out.push(['loaded', fired, await settleAsync(p)]);
  }
  // 4. Script carregado mas sem window.XLSX: resolve undefined.
  {
    const { env, api } = buildContext(lang, impl, mutation);
    const p = api._loadSheetJS();
    const fired = fire(env.appended[0], 'onload');
    out.push(['loaded-empty', fired, await settleAsync(p)]);
  }
  // 5. Falha de rede: rejeita com a mensagem traduzida.
  {
    const { env, api } = buildContext(lang, impl, mutation);
    const p = api._loadSheetJS();
    const fired = fire(env.appended[0], 'onerror', new Error('rede'));
    out.push(['error', fired, await settleAsync(p)]);
  }
  // 6. Duas chamadas antes de carregar: dois scripts (sem deduplicação), ambas resolvem.
  {
    const { ctx, env, api } = buildContext(lang, impl, mutation);
    const p1 = api._loadSheetJS(); const p2 = api._loadSheetJS();
    ctx.XLSX = MARK; const fired = env.appended.map((n) => fire(n, 'onload'));
    out.push(['concurrent', env.appended.length, fired, await settleAsync(p1), await settleAsync(p2)]);
  }
  // 7. Sem document.head: a exceção acontece dentro da Promise (rejeita).
  {
    const { ctx, api } = buildContext(lang, impl, mutation);
    ctx.document.head = null;
    out.push(['no-head', await settleAsync(api._loadSheetJS())]);
  }
  return out;
}

async function observe(lang, impl, mutation) {
  const { api } = buildContext(lang, impl, mutation);
  return { parse: observeParse(api), loader: await observeLoader(lang, impl, mutation) };
}

// Compara "antes" × "atual" em todas as variantes; devolve [observações, resultados].
async function compareAll(mutation) {
  const assert = require('assert');
  let observations = 0; let results = 0;
  const leaves = (v) => (Array.isArray(v) && ['ok', 'threw', 'resolved', 'rejected', 'pending'].includes(v[0]) ? 1 : Array.isArray(v) ? v.reduce((n, x) => n + leaves(x), 0) : 0);
  for (const lang of VARIANTS) {
    const before = await observe(lang, 'before');
    const now = await observe(lang, 'current', mutation);
    for (const part of ['parse', 'loader']) {
      assert.strictEqual(now[part].length, before[part].length, `${lang}/${part}: quantidade`);
      for (let i = 0; i < before[part].length; i += 1) {
        assert.deepStrictEqual(now[part][i], before[part][i], `${lang}/${part}: observação ${i} difere`);
        observations += 1; results += leaves(norm(before[part][i]));
      }
    }
  }
  return [observations, results];
}

function contracts() {
  const assert = require('assert');
  if (!exists(RULES)) { return; }
  const app = read('app.js');
  for (const name of ['_loadSheetJS', '_parseSuppliersRows']) {
    assert(!new RegExp(`^(async )?function ${name}\\(`, 'm').test(app), `${name} ainda declarada no app.js`);
  }
  // importSuppliersCSV continua no app.js e usa o namespace oficial.
  const body = extractFunction(app, 'importSuppliersCSV');
  assert(body.includes('globalThis.__EPI_SUPPLIER_IMPORT_LOADER__._loadSheetJS()'), 'importSuppliersCSV sem o carregador do namespace');
  assert.strictEqual((body.match(/globalThis\.__EPI_SUPPLIER_IMPORT_RULES__\._parseSuppliersRows\(/g) || []).length, 2,
    'importSuppliersCSV deveria usar o parser do namespace nos caminhos XLS e CSV');
  assert(body.includes("api('/api/authorized-suppliers/upload'"), 'contrato HTTP do upload preservado');
  const { ctx } = buildContext('pt-BR', 'current');
  for (const ns of ['__EPI_SUPPLIER_IMPORT_RULES__', '__EPI_SUPPLIER_IMPORT_LOADER__']) { assert(Object.isFrozen(ctx[ns]), `${ns} congelado`); }
  assert.strictEqual(typeof ctx._parseSuppliersRows, 'function', 'global legada _parseSuppliersRows');
  assert.strictEqual(ctx._parseSuppliersRows, ctx.__EPI_SUPPLIER_IMPORT_RULES__._parseSuppliersRows, 'global e namespace são a mesma função');
  assert.strictEqual(ctx._loadSheetJS, undefined, '_loadSheetJS era de bloco: não pode virar global');
  const scripts = read('views/_scripts.html');
  const pos = (s) => { const i = scripts.indexOf(s); assert(i >= 0, `${s} ausente em _scripts.html`); return i; };
  assert(pos('/js/modules/purchases/business/supplier-import-rules.js') < pos('/app.js?'));
  assert(pos('/js/modules/purchases/integrations/supplier-import-loader.js') < pos('/app.js?'));
}

module.exports = function register({ testAsync, test }) {
  testAsync('UBX Fornecedores F1: importação idêntica à cópia literal nos 5 idiomas', async () => {
    const [observations, results] = await compareAll();
    if (observations < 280 || results < 350) { throw new Error(`cobertura insuficiente: ${observations}/${results}`); }
    console.log(`    Fornecedores F1: ${observations} observações, ${results} resultados comparados, zero divergências`);
  });
  test('UBX Fornecedores F1: contratos dos módulos, globais e ordem de carga', () => contracts());
};
module.exports.compareAll = compareAll;
