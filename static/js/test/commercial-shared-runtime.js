'use strict';
// UBX Comercial, fatia C4 — caracterização das funções compartilhadas.
//
// formatCompanyCurrency (Empresas), fileToBase64 (leitura de arquivo) e
// renderMyCompanyDomains (Minha Empresa) rodam num contexto isolado com as
// dependências REAIS da página: o motor de tradução do static/i18n.js com os
// cinco catálogos (pt-BR de fallback), formatCurrency de
// modules/shared/business/value-format.js, escapeHtml de views/view-helpers.js e
// domainStatusLabel de modules/my-company (o mesmo nos dois lados). Só o que é do
// navegador é simulado: FileReader (registra a leitura e devolve o data URL ou o
// erro do cenário) e document.getElementById (elementos que guardam o innerHTML).
//
// A referência "antes" é a cópia literal do app.js
// (fixtures/app-before-ubx-commercial-c4.js.txt); a "atual" é o que a página
// carrega hoje. Cada entrada roda nas duas e o resultado (valor, exceção, HTML
// escrito, leituras de arquivo) tem de ser idêntico, nos cinco idiomas e também
// sem o motor de idioma, com idioma inválido e com idioma não suportado.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const STATIC = path.resolve(__dirname, '..', '..');
const LOCALES = ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO'];
const NAMES = ['formatCompanyCurrency', 'fileToBase64', 'renderMyCompanyDomains'];
const read = (rel) => fs.readFileSync(path.join(STATIC, rel), 'utf8');
const CATALOGS = Object.fromEntries(LOCALES.map((l) => [l, JSON.parse(read(`i18n/${l}.json`))]));
const FIXTURE = 'js/test/fixtures/app-before-ubx-commercial-c4.js.txt';

function extractFunction(source, name) {
  const match = new RegExp(`^[ \\t]*(?:async\\s+)?function ${name}\\(`, 'm').exec(source);
  if (!match) { throw new Error(`função ${name} não encontrada`); }
  let depth = 0;
  for (let i = source.indexOf(') {', match.index) + 2; i < source.length; i += 1) {
    if (source[i] === '{') { depth += 1; }
    if (source[i] === '}') { depth -= 1; if (depth === 0) { return source.slice(match.index, i + 1); } }
  }
  throw new Error(`função ${name} sem fim`);
}

// Elementos que registram o innerHTML escrito (cada escrita, na ordem).
function element(id, log) {
  let html = '';
  return {
    id,
    get innerHTML() { return html; },
    set innerHTML(value) { html = String(value); log.push(['innerHTML', id, html]); }
  };
}

function buildContext(lang, impl) {
  const env = { log: [], nodes: {}, reader: {} };
  const ctx = { JSON, Number, String, Object, Array, Promise, Symbol, Error, TypeError, RangeError, Math, Intl, Date, RegExp, Set, Map, isNaN };
  ctx.globalThis = ctx;
  ctx.__CATALOG_ACTIVE__ = CATALOGS[lang] || CATALOGS['pt-BR'];
  ctx.__CATALOG_FALLBACK__ = CATALOGS['pt-BR'];
  vm.createContext(ctx);
  const i18n = read('i18n.js');
  vm.runInContext([
    "const FALLBACK = 'pt-BR'; const _pluralCount = Symbol('numeric plural count');",
    `let _active = __CATALOG_ACTIVE__; let _fallback = __CATALOG_FALLBACK__; let _lang = ${JSON.stringify(LOCALES.includes(lang) ? lang : 'pt-BR')};`,
    ...['_resolve', '_interpolate', '_message', 't', 'trEpi'].map((n) => extractFunction(i18n, n)),
    'var tr = trEpi;'
  ].join('\n'), ctx);
  for (const rel of ['js/modules/shared/business/value-format.js', 'js/views/view-helpers.js', 'js/modules/my-company/business/my-company-rules.js',
    'js/modules/my-company/ui/my-company-view.js', 'js/modules/shared/ui/file-data-url.js', 'js/modules/companies/ui/companies-view.js']) {
    vm.runInContext(read(rel), ctx);
  }
  ctx.document = { getElementById: (id) => env.nodes[id] || null };
  ctx.FileReader = function FileReader() {
    const reader = this;
    reader.readAsDataURL = (file) => {
      env.log.push(['readAsDataURL', file?.name ?? null]);
      Promise.resolve().then(() => {
        if (env.reader.fail) { reader.onerror?.(new Error('io')); return; }
        reader.result = env.reader.result;
        reader.onload?.();
      });
    };
  };
  if (impl === 'original') {
    // As três funções da cópia literal sobrescrevem as globais (como o app.js fazia).
    vm.runInContext(read(FIXTURE), ctx);
  }
  // "Atual": as funções publicadas pelos módulos carregados acima (companies-view,
  // my-company-view e shared/ui/file-data-url).
  env.ctx = ctx;
  env.reset = (opts = {}) => {
    env.log = [];
    env.reader = opts.reader || {};
    env.nodes = {};
    if (!opts.noTable) { env.nodes['my-company-domains-table'] = element('my-company-domains-table', env.log); }
    if (!opts.noInstructions) { env.nodes['my-company-domain-instructions'] = element('my-company-domain-instructions', env.log); }
    if (opts.i18n === 'none') { delete ctx.EpiI18n; } else { ctx.EpiI18n = { lang: opts.i18n ?? lang }; }
    return env;
  };
  return env;
}

const CACHE = new Map();
function load(impl, lang) {
  const key = `${impl}:${lang}`;
  if (!CACHE.has(key)) { CACHE.set(key, buildContext(lang, impl)); }
  return CACHE.get(key);
}

const VALUES = [0, -0, 1, -1, 0.004, 0.005, 0.015, 1.005, 12.345, -12.345, 1234.5, 1234567.891, -9876543.21, 1e15, 1e21, Number.MAX_SAFE_INTEGER,
  Number.EPSILON, NaN, Infinity, -Infinity, null, undefined, '', ' ', '0', '42', '42.5', '42,5', '1e3', '-7', 'abc', '1.234,56', '١٢٣', true, false,
  [], [5], {}, { valueOf: () => 9 }, ' ', 'R$ 10'];
const I18N_VARIANTS = [undefined, 'none', '', 'xx-INVALID', 'en-US', 'pt', 'zz'];
const DOMAINS = [
  [],
  [{ id: 1, full_host: 'app.empresa.test', type_label: 'Subdomínio', domain_type: 'platform_subdomain', verification_status: 'verified', ssl_status: 'active', is_primary: 1 }],
  [{ id: 2, full_host: 'epi.cliente.test', type_label: 'Próprio', domain_type: 'custom_domain', verification_status: 'pending', ssl_status: 'pending',
    is_primary: 0, cname_target: 'cname.<b>x</b>', txt_record: '_epi.cliente.test', verification_token: 'tok "1"' },
  { id: 3, full_host: 'b.test', type_label: 'Próprio', domain_type: 'custom_domain', verification_status: 'verified', ssl_status: 'failed', is_primary: '0' },
  { id: 4, full_host: '<img src=x onerror=alert(1)>', type_label: '<i>t</i>', domain_type: 'custom_domain', verification_status: 'failed', ssl_status: '',
    is_primary: '1', cname_target: '$&$1', txt_record: "a'b", verification_token: '\u0000host\u0000' }],
  [{ id: 5, domain_type: 'platform_subdomain', verification_status: 'pending' }, { id: 6, verification_status: 'unknown_status', ssl_status: null, is_primary: null }],
  [{}],
  // Subdomínio da plataforma pendente ANTES de um domínio próprio pendente: só o segundo ganha instruções.
  [{ id: 7, full_host: 'sub.plataforma.test', domain_type: 'platform_subdomain', verification_status: 'pending', cname_target: 'plat', txt_record: 'p', verification_token: 'p' },
    { id: 8, full_host: 'proprio.test', domain_type: 'custom_domain', verification_status: 'pending', cname_target: 'own', txt_record: 'o', verification_token: 'o' }],
  // Valores DNS com padrões especiais de String.prototype.replace ($&, $1, $$, $`, $').
  [{ id: 9, full_host: '$&.test', domain_type: 'custom_domain', verification_status: 'pending', cname_target: '$&$1$$', txt_record: "$`x$'", verification_token: '$<n>' }],
  null,
  [null]
];
const FILES = [
  [{ name: 'contrato.pdf' }, { result: 'data:application/pdf;base64,JVBERi0=' }],
  [{ name: 'sem-virgula' }, { result: 'cru-sem-prefixo' }],
  [{ name: 'duas,virgulas' }, { result: 'data:text/plain;base64,QQ==,extra' }],
  [{ name: 'vazio' }, { result: '' }],
  [{ name: 'nulo' }, { result: null }],
  [{ name: 'objeto' }, { result: { toString: () => 'data:x,Y' } }],
  [{ name: 'falha <b>' }, { fail: true }],
  [undefined, { result: 'data:,Z' }]
];

const flush = () => new Promise((resolve) => setImmediate(resolve));
const safe = (value) => {
  if (value === undefined) { return ['undefined']; }
  if (typeof value === 'number' && !Number.isFinite(value)) { return ['number', String(value)]; }
  try { return JSON.parse(JSON.stringify(value)); } catch { return ['unserializable', String(value)]; }
};

async function invoke(env, name, args) {
  let outcome;
  try {
    const value = env.ctx[name](...args);
    if (value && typeof value.then === 'function') {
      outcome = await value.then((v) => ['resolved', safe(v)], (e) => ['rejected', e?.name, String(e?.message ?? e)]);
    } else {
      outcome = ['returned', safe(value)];
    }
  } catch (error) {
    outcome = ['threw', error?.name, String(error?.message ?? error)];
  }
  await flush();
  return [outcome, env.log, Object.fromEntries(Object.entries(env.nodes).map(([k, n]) => [k, n.innerHTML]))];
}

async function compareAll() {
  let compared = 0;
  const check = async (lang, opts, name, args, label) => {
    const before = await invoke(load('original', lang).reset(opts), name, args);
    const after = await invoke(load('current', lang).reset(opts), name, args);
    const a = JSON.stringify(after);
    const b = JSON.stringify(before);
    if (a !== b) { throw new Error(`${label}: antes ${b.slice(0, 600)} × atual ${a.slice(0, 600)}`); }
    compared += 1;
  };
  for (const lang of LOCALES) {
    for (const i18n of I18N_VARIANTS) {
      for (const value of VALUES) {
        await check(lang, { i18n }, 'formatCompanyCurrency', [value], `${lang} i18n=${i18n} formatCompanyCurrency(${String(value)})`);
      }
      await check(lang, { i18n }, 'formatCompanyCurrency', [], `${lang} i18n=${i18n} formatCompanyCurrency()`);
      await check(lang, { i18n }, 'formatCompanyCurrency', [5, 'extra'], `${lang} i18n=${i18n} formatCompanyCurrency(5, extra)`);
    }
    for (const [index, domains] of DOMAINS.entries()) {
      for (const opts of [{}, { noInstructions: true }, { noTable: true }, { i18n: 'none' }]) {
        await check(lang, opts, 'renderMyCompanyDomains', [domains], `${lang} domínios #${index} ${JSON.stringify(opts)}`);
      }
    }
    await check(lang, {}, 'renderMyCompanyDomains', [], `${lang} domínios sem argumento`);
    for (const [file, reader] of FILES) {
      await check(lang, { reader }, 'fileToBase64', [file], `${lang} arquivo ${file?.name}`);
    }
    // Duas leituras simultâneas: cada uma resolve com o próprio leitor.
    for (const impl of ['original', 'current']) {
      const env = load(impl, lang).reset({ reader: { result: 'data:a;base64,AAA' } });
      const results = await Promise.all([env.ctx.fileToBase64({ name: 'a' }), env.ctx.fileToBase64({ name: 'b' })]);
      env.log.push(['paralelo', results]);
      (impl === 'original' ? (load.lastBefore = JSON.stringify(env.log)) : (load.lastAfter = JSON.stringify(env.log)));
    }
    if (load.lastBefore !== load.lastAfter) { throw new Error(`${lang}: leituras simultâneas divergem`); }
    compared += 1;
  }
  return compared;
}

module.exports = function ({ testAsync, test, assert, eq }) {
  test('UBX Comercial C4: a fixture é cópia literal das 3 funções compartilhadas', () => {
    const fixture = read(FIXTURE);
    const found = [...fixture.matchAll(/^(?:async )?function ([A-Za-z_$][\w$]*)\(/gm)].map((m) => m[1]);
    eq(JSON.stringify(found), JSON.stringify(NAMES), 'as 3 funções, na ordem do app.js');
  });

  testAsync('UBX Comercial C4: funções atuais × app.js de antes — mesmo valor, exceção, HTML e leituras, nos cinco idiomas', async () => {
    const compared = await compareAll();
    assert(compared >= 1600, `cobertura da comparação: ${compared}`);
    console.log(`    C4: ${compared} comparações`);
  });

  testAsync('UBX Comercial C4: valores de referência (moeda BRL no idioma ativo, escape, base64)', async () => {
    const pt = await invoke(load('current', 'pt-BR').reset(), 'formatCompanyCurrency', [1234.5]);
    eq(pt[0][1], 'R$ 1.234,50', 'pt-BR');
    const en = await invoke(load('current', 'en-GB').reset(), 'formatCompanyCurrency', [null]);
    eq(en[0][1], 'R$0.00', 'en-GB com null');
    const html = await invoke(load('current', 'pt-BR').reset(), 'renderMyCompanyDomains', [DOMAINS[2]]);
    assert(html[2]['my-company-domains-table'].includes('&lt;img src=x'), 'host escapado');
    assert(html[2]['my-company-domain-instructions'].includes('<code>cname.&lt;b&gt;x&lt;/b&gt;</code>'), 'valor DNS escapado');
    const file = await invoke(load('current', 'pt-BR').reset({ reader: { result: 'data:application/pdf;base64,JVBERi0=' } }), 'fileToBase64', [{ name: 'x' }]);
    eq(JSON.stringify(file[0]), JSON.stringify(['resolved', 'JVBERi0=']), 'base64 sem o prefixo');
  });

  test('UBX Comercial C4: cada função vive no seu módulo dono, publicada com o mesmo nome, uma vez e antes do app.js', () => {
    const owners = { formatCompanyCurrency: ['js/modules/companies/ui/companies-view.js', '__EPI_COMPANIES_UI__'],
      renderMyCompanyDomains: ['js/modules/my-company/ui/my-company-view.js', '__EPI_MY_COMPANY_UI__'],
      fileToBase64: ['js/modules/shared/ui/file-data-url.js', '__EPI_SHARED_FILE_DATA_URL__'] };
    const ctx = { Object, Set, Map, JSON, Promise };
    ctx.globalThis = ctx;
    vm.createContext(ctx);
    for (const [name, [rel, ns]] of Object.entries(owners)) {
      vm.runInContext(read(rel), ctx);
      eq(typeof ctx[name], 'function', `${name} global`);
      assert(Object.isFrozen(ctx[ns]) && ctx[ns][name] === ctx[name], `${name}: ${ns}.${name} === global`);
      for (const [other] of Object.values(owners).filter(([r]) => r !== rel)) {
        assert(!new RegExp(`function ${name}\\(`).test(read(other)), `${name} não está duplicada em ${other}`);
      }
    }
    const app = read('app.js');
    for (const name of NAMES) { assert(!new RegExp(`^\\s*(?:async\\s+)?function ${name}\\(`, 'm').test(app), `${name} saiu do app.js`); }
    const order = [...read('views/_scripts.html').matchAll(/<script[^>]+src="([^"?]+)/g)].map((m) => m[1]);
    for (const [rel] of Object.values(owners)) {
      const i = order.indexOf(`/${rel}`);
      assert(i >= 0 && i < order.indexOf('/app.js'), `${rel} carregado antes do app.js`);
      eq(order.filter((src) => src === `/${rel}`).length, 1, `${rel} carregado uma vez`);
    }
    assert(order.indexOf('/js/modules/shared/ui/file-data-url.js') < order.indexOf('/js/modules/commercial/ui/commercial-contract-view.js'),
      'leitura de arquivo antes do contrato comercial que a usa');
    assert(order.indexOf('/js/modules/shared/business/value-format.js') < order.indexOf('/js/modules/companies/ui/companies-view.js'),
      'formatCurrency antes de Empresas');
    // Sem HTTP, estado nem armazenamento nos trechos movidos.
    for (const name of NAMES) {
      const src = extractFunction(read(owners[name][0]), name);
      assert(!/\bapi\(|fetch\(|__EPI_APP_STATE__|localStorage|sessionStorage/.test(src), `${name}: sem HTTP, estado ou armazenamento`);
    }
  });
};
