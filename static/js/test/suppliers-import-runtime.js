'use strict';
// UBX Fornecedores F1 — caracterização da importação de fornecedores autorizados.
//
// _parseSuppliersRows (modules/purchases/business/supplier-import-rules.js) e
// _loadSheetJS (modules/purchases/integrations/supplier-import-loader.js) rodam
// num contexto isolado, chamados pelo importSuppliersCSV do app.js — que é quem
// injeta as dependências (rótulo traduzido, window.XLSX, criação e anexação do
// <script>, mensagem de erro). O motor de tradução é o static/i18n.js com os
// cinco catálogos reais (pt-BR de fallback).
//
// A referência "antes" é a cópia literal do app.js
// (fixtures/app-before-ubx-suppliers-f1.js.txt); a "atual" é o que a página
// carrega hoje (os módulos + o importSuppliersCSV do app.js, ou as três
// declarações do próprio app.js enquanto a extração não existe). Cada cenário
// roda nas duas — DOM, arquivo, SheetJS e api falsos e determinísticos — e o
// registro completo (textos do feedback, chamadas à api, scripts criados e
// anexados, recarga da lista, retorno/exceção) tem de ser idêntico nos cinco
// idiomas, com idioma não suportado, com catálogos vazios e sem o motor.
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
const EXTRACTED = ['_loadSheetJS', '_parseSuppliersRows'];
const SHEETJS_URL = 'https://cdn.jsdelivr.net/npm/xlsx/dist/xlsx.full.min.js';
const NAME_LABELS = { 'pt-BR': 'Nome', 'en-GB': 'Name', 'es-ES': 'Nombre', 'fr-FR': 'Nom', 'nb-NO': 'Navn' };

function balanced(source, start, open, close) {
  let depth = 0;
  for (let i = source.indexOf(open, start); i < source.length; i += 1) {
    if (source[i] === open) { depth += 1; }
    if (source[i] === close) { depth -= 1; if (depth === 0) { return i + 1; } }
  }
  throw new Error('declaração sem fim');
}

function extractFunction(source, name) {
  const match = new RegExp(`^[ \\t]*(?:async\\s+)?function ${name}\\(`, 'm').exec(source);
  if (!match) { throw new Error(`função ${name} não encontrada`); }
  return source.slice(match.index, balanced(source, source.indexOf(') {', match.index) + 2, '{', '}'));
}

const extracted = () => exists(RULES) && exists(LOADER);

// Ambiente falso da página: DOM mínimo, arquivo, SheetJS e api. Tudo o que o
// código toca fica registrado em `log`, na ordem em que acontece.
function buildContext(lang, impl, scenario, mutation) {
  const log = [];
  const ctx = { JSON, Number, String, Object, Array, Symbol, Error, TypeError, Math, isNaN, Promise, setTimeout, ArrayBuffer, Uint8Array };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  if (lang !== null) {
    ctx.__CATALOGS__ = lang === 'vazio' ? Object.fromEntries(LOCALES.map((l) => [l, {}])) : CATALOGS;
    const i18n = read('i18n.js');
    vm.runInContext([
      "const FALLBACK = 'pt-BR'; const _pluralCount = Symbol('numeric plural count');",
      `let _lang = ${JSON.stringify(LOCALES.includes(lang) ? lang : 'pt-BR')};`,
      "let _active = __CATALOGS__[_lang]; let _fallback = __CATALOGS__['pt-BR'];",
      ...['_resolve', '_interpolate', '_message', 't', 'trEpi'].map((n) => extractFunction(i18n, n)),
      'globalThis.trEpi = trEpi; var tr = trEpi;'
    ].join('\n'), ctx);
  } else {
    // Sem o motor: o tr de fallback do app.js devolve o texto do código.
    vm.runInContext('var tr = function (key, fallback, vars) { return String(fallback !== undefined ? fallback : key).replace(/\\{(\\w+)\\}/g, (m, n) => vars && Object.prototype.hasOwnProperty.call(vars, n) ? String(vars[n]) : m); };', ctx);
  }

  const feedback = scenario.noFeedback ? null : {
    _text: '',
    get textContent() { return this._text; },
    set textContent(v) { this._text = v; log.push(['feedback', v]); }
  };
  const fileInput = scenario.noInput ? null : { files: scenario.files || [] };
  const head = {
    appendChild(el) {
      log.push(['append', el.tagName, el.src, typeof el.onload, typeof el.onerror]);
      const outcome = scenario.script || 'load';
      setTimeout(() => {
        if (outcome === 'load') { ctx.window.XLSX = makeXlsx(scenario, log); el.onload(); } else if (outcome === 'error') { el.onerror(); }
      }, 0);
      return el;
    }
  };
  ctx.document = {
    head,
    getElementById(id) {
      log.push(['getElementById', id]);
      if (id === 'compras-suppliers-csv') { return fileInput; }
      if (id === 'compras-suppliers-csv-feedback') { return feedback; }
      return null;
    },
    createElement(tag) { log.push(['createElement', tag]); return { tagName: String(tag).toUpperCase(), src: '', onload: null, onerror: null }; }
  };
  ctx.window = ctx;
  if (scenario.xlsxPresent) { ctx.XLSX = makeXlsx(scenario, log); }
  ctx.state = scenario.noUser ? {} : { user: { id: 42 } };
  ctx.api = (url, opts) => {
    log.push(['api', url, opts && opts.method, opts && opts.body]);
    if (scenario.apiError !== undefined) { return Promise.reject(new Error(scenario.apiError)); }
    return Promise.resolve(scenario.apiResult === undefined ? { inserted: 2, updated: 1 } : scenario.apiResult);
  };
  ctx.loadAuthorizedSuppliers = () => { log.push(['reload']); };

  let fns;
  const wrap = (code, names) => `globalThis.__F__ = (function () {\n${code}\nreturn { ${names.join(', ')} };\n})();`;
  if (impl === 'before') {
    vm.runInContext(wrap(read(FIXTURE), ['importSuppliersCSV', ...EXTRACTED]), ctx);
    fns = ctx.__F__;
  } else if (!extracted()) {
    const app = read('app.js');
    const code = [...EXTRACTED, 'importSuppliersCSV'].map((n) => extractFunction(app, n)).join('\n\n');
    vm.runInContext(wrap(code, ['importSuppliersCSV', ...EXTRACTED]), ctx);
    fns = ctx.__F__;
  } else {
    let rules = read(RULES); let loader = read(LOADER); let importer = extractFunction(read('app.js'), 'importSuppliersCSV');
    if (mutation) {
      const [file, from, to] = mutation;
      const pick = { rules, loader, app: importer }[file];
      if (pick === undefined) { throw new Error('mutação com arquivo desconhecido: ' + file); }
      if (!pick.includes(from)) { throw new Error('mutação sem alvo: ' + from); }
      if (file === 'rules') { rules = rules.replace(from, to); } else if (file === 'loader') { loader = loader.replace(from, to); } else { importer = importer.replace(from, to); }
    }
    vm.runInContext(rules, ctx);
    vm.runInContext(loader, ctx);
    // O app.js chama os nomes globais publicados pelos módulos.
    vm.runInContext(wrap(importer, ['importSuppliersCSV']), ctx);
    fns = { importSuppliersCSV: ctx.__F__.importSuppliersCSV, _loadSheetJS: ctx._loadSheetJS, _parseSuppliersRows: ctx._parseSuppliersRows };
  }
  return { ctx, fns, log };
}

function makeXlsx(scenario, log) {
  return {
    read(buf, opts) { log.push(['XLSX.read', Object.prototype.toString.call(buf), opts && opts.type]); return { SheetNames: ['Fornecedores', 'Outra'], Sheets: { Fornecedores: { id: 'ws1' }, Outra: { id: 'ws2' } } }; },
    utils: { sheet_to_json(ws, opts) { log.push(['sheet_to_json', ws && ws.id, opts && opts.defval]); return scenario.sheetRows || []; } }
  };
}

const file = (name, content, extra = {}) => ({
  name,
  text: extra.textError !== undefined ? () => Promise.reject(new Error(extra.textError)) : () => Promise.resolve(content),
  arrayBuffer: () => Promise.resolve(new ArrayBuffer(8))
});

// Linhas de planilha (sheet_to_json mantém o cabeçalho original da coluna).
const SHEET_ROWS = [
  { Nome: ' Fornecedor A ', CNPJ: '11.222.333/0001-44', Email: 'a@x.com' },
  { name: 'Fornecedor B', cnpj: '', contact_email: 'b@x.com' },
  { NOME: 'Fornecedor C', contato: 'Fulano' },
  { Nombre: 'Proveedor D', cnpj: 123 },
  { Nom: 'Fournisseur E', contact_name: 'Jean' },
  { Navn: 'Leverandør F', email: 'f@x.no' },
  { Name: 'Supplier G', CNPJ: 0 },
  { Nome: '   ', CNPJ: '99' },
  { cnpj: 'sem nome' },
  { Nome: 0, email: 'zero@x' },
  { Nome: null, name: 'Fallback H' },
  { '': 'vazio', Nome: 'Fornecedor I' }
];

const SCENARIOS = [
  { id: 'sem input', noInput: true },
  { id: 'sem arquivo', files: [] },
  { id: 'sem arquivo e sem feedback', files: [], noFeedback: true },
  { id: 'csv ; com BOM e aspas', files: [file('fornecedores.csv', '﻿Nome;CNPJ;Email\r\n"Fornecedor A";"11.222.333/0001-44";"a@x.com"\r\nFornecedor B;;b@x.com\r\n\r\n;123;\r\n')] },
  { id: 'csv , minúsculas', files: [file('lista.CSV', 'name,cnpj,contact_email\nAlpha,1,alpha@x\nBeta,,\n')] },
  { id: 'csv cabeçalhos traduzidos', files: [file('f.csv', 'Nombre,Nom,Navn,cnpj\nProveedor,,,1\n,Fournisseur,,2\n,,Leverandør,3\n')] },
  { id: 'csv colunas a mais/menos', files: [file('f.txt', 'nome;cnpj\nSó Nome\nCom CNPJ;77;extra;mais\n')] },
  { id: 'csv só cabeçalho', files: [file('f.csv', 'nome;cnpj\n\n   \n')] },
  { id: 'csv vazio', files: [file('f.csv', '')] },
  { id: 'csv sem coluna nome', files: [file('f.csv', 'empresa;cnpj\nX;1\nY;2\n')] },
  { id: 'csv sem extensão', files: [file('arquivo', 'nome\nZeta\n')] },
  { id: 'erro de leitura', files: [file('f.csv', '', { textError: 'disco falhou' })] },
  { id: 'erro de leitura sem mensagem', files: [file('f.csv', '', { textError: '' })] },
  { id: 'api erro', files: [file('f.csv', 'nome\nA\n')], apiError: 'servidor recusou' },
  { id: 'api erro sem mensagem', files: [file('f.csv', 'nome\nA\n')], apiError: '' },
  { id: 'api devolve null', files: [file('f.csv', 'nome\nA\n')], apiResult: null },
  { id: 'api devolve zeros', files: [file('f.csv', 'nome\nA\n')], apiResult: { inserted: 0 } },
  { id: 'sem usuário na sessão', files: [file('f.csv', 'nome\nA\n')], noUser: true },
  { id: 'xlsx já carregado', files: [file('Planilha.xlsx', '')], xlsxPresent: true, sheetRows: SHEET_ROWS },
  { id: 'xls carrega SheetJS', files: [file('planilha.xls', '')], script: 'load', sheetRows: SHEET_ROWS },
  { id: 'xls falha ao carregar SheetJS', files: [file('planilha.XLS', '')], script: 'error' },
  { id: 'xls sem linhas válidas', files: [file('p.xlsx', '')], xlsxPresent: true, sheetRows: [{ cnpj: '1' }] },
  { id: 'xls com várias extensões', files: [file('backup.csv.xlsx', '')], xlsxPresent: true, sheetRows: SHEET_ROWS.slice(0, 3) },
  { id: 'carregamento único (duas importações seguidas)', files: [file('a.xlsx', '')], script: 'load', sheetRows: SHEET_ROWS.slice(0, 2), repeat: 2 },
  { id: 'duas importações simultâneas', files: [file('a.xlsx', '')], script: 'load', sheetRows: SHEET_ROWS.slice(0, 2), concurrent: 2 }
];

// Entradas diretas da regra pura, como o app.js a chama.
const PARSE_INPUTS = [[], SHEET_ROWS, [{}], [{ nome: 'x' }], [{ Nome: 'y', email: 'e', contato: 'c' }], [{ NAME: 'Up', CNPJ: '1' }], [null], ['texto'], [{ Nome: { toString() { return 'obj'; } } }]];

function norm(value) {
  if (Array.isArray(value)) { return Array.from(value, norm); }
  if (value === undefined) { return ['undefined']; }
  if (value === null) { return null; }
  if (typeof value === 'function') { return ['function', value.name]; }
  if (typeof value === 'number' && Number.isNaN(value)) { return ['NaN']; }
  if (typeof value === 'object') { return ['object', Object.keys(value).map((k) => [k, norm(value[k])])]; }
  return value;
}
const flush = () => new Promise((r) => setTimeout(r, 5));
// Promessa que nunca se resolve (ex.: <script> que não chega a ser anexado) vira um
// resultado observável: sem o tempo-limite o Node esvaziaria o event loop e sairia
// com código 0, escondendo o defeito.
const HANG_MS = 1000;
async function settle(fn) {
  let timer;
  const hang = new Promise((resolve) => { timer = setTimeout(() => resolve(['timeout']), HANG_MS); });
  try {
    return await Promise.race([Promise.resolve().then(fn).then((v) => ['ok', norm(v)]), hang]);
  } catch (error) {
    return ['threw', error && error.name, error && error.message];
  } finally {
    clearTimeout(timer);
  }
}

async function observe(lang, impl, scenario, mutation) {
  const { ctx, fns, log } = buildContext(lang, impl, scenario, mutation);
  const out = [];
  if (scenario.concurrent) {
    const runs = Array.from({ length: scenario.concurrent }, () => settle(() => fns.importSuppliersCSV()));
    out.push(await Promise.all(runs));
  } else {
    for (let i = 0; i < (scenario.repeat || 1); i += 1) { out.push(await settle(() => fns.importSuppliersCSV())); await flush(); }
  }
  await flush();
  out.push(norm(log), typeof ctx.XLSX);
  return out;
}

async function compareAll(mutation) {
  const assert = require('assert');
  let comparisons = 0;
  const variants = [...LOCALES, 'xx-XX', 'vazio', null];
  for (const lang of variants) {
    for (const scenario of SCENARIOS) {
      const before = await observe(lang, 'before', scenario);
      const now = await observe(lang, 'current', scenario, mutation);
      assert.deepStrictEqual(now, before, `${lang} / ${scenario.id}: importação difere`);
      comparisons += 1;
    }
    // Regra pura, como o importSuppliersCSV a chama (rótulo traduzido no idioma ativo).
    for (const rows of PARSE_INPUTS) {
      const b = buildContext(lang, 'before', {});
      const c = buildContext(lang, 'current', {}, mutation);
      const before = await settle(() => b.fns._parseSuppliersRows(rows));
      const label = vm.runInContext("tr('signature.name', 'Nome', {})", c.ctx);
      const now = await settle(() => (extracted() ? c.fns._parseSuppliersRows(rows, label) : c.fns._parseSuppliersRows(rows)));
      assert.deepStrictEqual(now, before, `${lang}: _parseSuppliersRows(${JSON.stringify(rows).slice(0, 60)}) difere`);
      comparisons += 1;
    }
  }
  return comparisons;
}

// Módulos sem nenhuma global da página: só o que vem por parâmetro.
async function isolation(mutation) {
  const assert = require('assert');
  if (!extracted()) { return 0; }
  let checks = 0;
  const forbidden = ['document', 'window', 'tr', 'trEpi', 'state', 'api', 'XLSX', 'EpiI18n'];
  const trap = () => {
    const ctx = { JSON, Object, String, Array, Promise, Error, TypeError, setTimeout };
    ctx.globalThis = ctx;
    for (const name of forbidden) {
      Object.defineProperty(ctx, name, { get() { throw new Error(`acesso proibido a ${name}`); }, configurable: true });
    }
    vm.createContext(ctx);
    return ctx;
  };
  let rules = read(RULES); let loader = read(LOADER);
  if (mutation && mutation[0] === 'rules' && rules.includes(mutation[1])) { rules = rules.replace(mutation[1], mutation[2]); }
  if (mutation && mutation[0] === 'loader' && loader.includes(mutation[1])) { loader = loader.replace(mutation[1], mutation[2]); }

  const r = trap();
  vm.runInContext(rules, r);
  for (const [lang, label] of Object.entries(NAME_LABELS)) {
    const got = norm(r._parseSuppliersRows([{ [label]: ` ${label}-fornecedor `, cnpj: '1' }, { [label.toLowerCase()]: 'minúsculo' }, { cnpj: 'sem nome' }], label));
    const want = norm([{ name: `${label}-fornecedor`, cnpj: '1', email: '' }, { name: 'minúsculo', cnpj: '', email: '' }]);
    assert.deepStrictEqual(got, want, `${lang}: regra pura com o rótulo '${label}'`);
    checks += 1;
  }
  assert(Object.isFrozen(r.__EPI_SUPPLIER_IMPORT_RULES__), 'namespace da regra congelado');
  assert.strictEqual(r.__EPI_SUPPLIER_IMPORT_RULES__._parseSuppliersRows, r._parseSuppliersRows, 'namespace e global legada são a mesma função');

  const l = trap();
  vm.runInContext(loader, l);
  const calls = [];
  const loaded = { tag: 'sheetjs' };
  let current;
  const deps = (outcome) => ({
    getXLSX: () => { calls.push('getXLSX'); return current; },
    createScript: () => { calls.push('createScript'); return { src: '', onload: null, onerror: null }; },
    appendScript: (s) => {
      calls.push(['appendScript', s.src, typeof s.onload, typeof s.onerror]);
      setTimeout(() => { if (outcome === 'load') { current = loaded; s.onload(); } else { s.onerror(); } }, 0);
    },
    loadErrorMessage: () => { calls.push('loadErrorMessage'); return 'mensagem traduzida'; }
  });
  const timed = (promise) => Promise.race([promise, new Promise((_, reject) => setTimeout(() => reject(new Error('carga do SheetJS nunca terminou')), HANG_MS))]);
  current = loaded;
  assert.strictEqual(await timed(l._loadSheetJS(deps('load'))), loaded, 'já carregado: devolve o mesmo objeto');
  assert.deepStrictEqual(calls.splice(0), ['getXLSX', 'getXLSX'], 'já carregado: não cria script');
  current = undefined;
  assert.strictEqual(await timed(l._loadSheetJS(deps('load'))), loaded, 'carrega e devolve o SheetJS');
  assert.deepStrictEqual(calls.splice(0), ['getXLSX', 'createScript', ['appendScript', SHEETJS_URL, 'function', 'function'], 'getXLSX'], 'ordem de carga');
  current = undefined;
  await assert.rejects(() => timed(l._loadSheetJS(deps('error'))), (e) => e instanceof l.Error && e.message === 'mensagem traduzida', 'erro de carga');
  assert.deepStrictEqual(calls.splice(0), ['getXLSX', 'createScript', ['appendScript', SHEETJS_URL, 'function', 'function'], 'loadErrorMessage'], 'mensagem só no erro');
  assert(Object.isFrozen(l.__EPI_SUPPLIER_IMPORT_LOADER__), 'namespace do loader congelado');
  assert.strictEqual(l.__EPI_SUPPLIER_IMPORT_LOADER__.SHEETJS_URL, SHEETJS_URL, 'URL do SheetJS inalterada (core/csp.py)');
  checks += 4;
  return checks;
}

function contracts() {
  const assert = require('assert');
  if (!extracted()) { return; }
  const app = read('app.js');
  for (const name of EXTRACTED) {
    assert(!new RegExp(`^(?:async\\s+)?function ${name}\\(`, 'm').test(app), `${name} ainda declarada no app.js`);
  }
  assert(/^async function importSuppliersCSV\(/m.test(app), 'importSuppliersCSV continua no app.js');
  const importer = extractFunction(app, 'importSuppliersCSV');
  assert(importer.includes("_parseSuppliersRows(data, tr('signature.name', 'Nome', {}))"), 'XLS: rótulo injetado pelo app.js');
  assert(importer.includes("_parseSuppliersRows(objRows, tr('signature.name', 'Nome', {}))"), 'CSV: rótulo injetado pelo app.js');
  assert(!app.includes(SHEETJS_URL), 'a URL do SheetJS mora só no loader');
  // Sem comentários, como a guarda UBX: o código, não a documentação, é o que não pode tocar a página.
  const stripComments = (code) => code.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:\\])\/\/.*$/gm, '$1');
  for (const file of [RULES, LOADER]) {
    const body = stripComments(read(file));
    assert(!/\bdocument\s*\./.test(body), `${file}: sem document.*`);
    assert(!/\bwindow\b/.test(body), `${file}: sem window`);
    assert(!/(?<![\w$.])tr\s*\(/.test(body), `${file}: sem tr()`);
  }
  const scripts = read('views/_scripts.html');
  const pos = (s) => { const i = scripts.indexOf(s); assert(i >= 0, `${s} ausente em _scripts.html`); return i; };
  assert(pos('/' + RULES + '?') < pos('/app.js?'), 'regra carrega antes do app.js');
  assert(pos('/' + LOADER + '?') < pos('/app.js?'), 'loader carrega antes do app.js');
  const baseline = JSON.parse(read('js/test/app-js-baseline.json'));
  assert.deepStrictEqual(baseline.extracted[RULES], ['_parseSuppliersRows'], 'registro de extração da regra');
  assert.deepStrictEqual(baseline.extracted[LOADER], ['_loadSheetJS'], 'registro de extração do loader');
}

module.exports = function register({ test, testAsync }) {
  testAsync('UBX Fornecedores F1: importação CSV/XLS idêntica à cópia literal nos 5 idiomas', async () => {
    const n = await compareAll();
    if (n < 250) { throw new Error(`cobertura insuficiente: ${n}`); }
    console.log(`    Fornecedores F1: ${n} comparações (${SCENARIOS.length} cenários × 8 variantes + regra pura), zero divergências`);
  });
  testAsync('UBX Fornecedores F1: módulos puros, só dependências injetadas', async () => {
    const n = await isolation();
    if (extracted() && n < 9) { throw new Error('isolamento não exercitado'); }
  });
  test('UBX Fornecedores F1: contratos, registro de extração e ordem de carga', () => contracts());
};
module.exports.compareAll = compareAll;
module.exports.isolation = isolation;
module.exports.contracts = contracts;
