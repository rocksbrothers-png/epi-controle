'use strict';
// UBX-V2 — caracterização de modules/shared/business/value-format.js.
//
// As tabelas abaixo foram GERADAS executando as funções ORIGINAIS do app.js
// (main 1bd22272, fatiadas por nome) antes da extração; `undefined` é
// preservado como { $undefined: true } e caracteres não ASCII como \u, em TZ=UTC e
// TZ=America/Sao_Paulo (resultados idênticos). Elas fixam o comportamento
// atual — inclusive peculiaridades (parseMonthsValue(6.9) === 69,
// formatCurrency('abc') === 'R$ NaN', addDaysFromBaseDate com dias não
// numéricos lança RangeError, formatCnpj × formatCNPJ divergem no fallback).
// Mudar um valor aqui é mudar regra, não estrutura.
const fs = require('fs'), path = require('path'), vm = require('vm');
const JS_ROOT = path.resolve(__dirname, '..');
const MODULE = 'modules/shared/business/value-format.js';
const NAMES = ['formatCurrency', 'fmtBrl', 'parseMonthsValue', 'parsePositiveInteger', 'digitsOnly', 'formatCnpj',
  'formatCNPJ', 'normalizeSearchText', 'parseCsvList', 'parseCsvNumberList', 'parseOptionalJson', 'normalizeHexColor',
  'daysUntil', 'addDaysFromBaseDate'];

const EXPECTED = {
  formatCurrency: [
    [[0], 'R$\u00a00,00'],
    [[null], 'R$\u00a00,00'],
    [[{ $undefined: true }], 'R$\u00a00,00'],
    [[''], 'R$\u00a00,00'],
    [[1234.5], 'R$\u00a01.234,50'],
    [['1234.5'], 'R$\u00a01.234,50'],
    [[-0.005], '-R$\u00a00,01'],
    [['abc'], 'R$\u00a0NaN'],
    [[1e+21], 'R$\u00a01.000.000.000.000.000.000.000,00']
  ],
  fmtBrl: [
    [[0], 'R$\u00a00,00'],
    [[null], 'R$\u00a00,00'],
    [[{ $undefined: true }], 'R$\u00a00,00'],
    [[1234.5], 'R$\u00a01.234,50'],
    [['10'], 'R$\u00a010,00'],
    [[-3.456], '-R$\u00a03,46'],
    [['x'], 'R$\u00a0NaN']
  ],
  parseMonthsValue: [
    [[0], 0],
    [[false], 0],
    [[''], 0],
    [[null], 0],
    [['12'], 12],
    [['12 meses'], 12],
    [['-3'], 0],
    [['0'], 0],
    [['1-2'], 1],
    [['abc'], 0],
    [[6.9], 69],
    [['\uff11\uff12'], 0]
  ],
  parsePositiveInteger: [
    [[0], 0],
    [[false], 0],
    [[''], 0],
    [[{ $undefined: true }], 0],
    [['7'], 7],
    [[' 42 '], 42],
    [['3.9'], 3],
    [['-1'], 0],
    [['0'], 0],
    [['12abc'], 12],
    [['abc12'], 0],
    [[5], 5]
  ],
  digitsOnly: [
    [[0], ''],
    [[false], ''],
    [[''], ''],
    [[null], ''],
    [[{ $undefined: true }], ''],
    [['12.345.678/0001-90'], '12345678000190'],
    [['(11) 98765-4321'], '11987654321'],
    [[12345], '12345'],
    [['abc'], ''],
    [['\u0661\u0662'], '']
  ],
  formatCnpj: [
    [[0], ''],
    [[false], ''],
    [[{ $undefined: true }], ''],
    [['123'], '123'],
    [['12345678000190'], '12.345.678/0001-90'],
    [['12.345.678/0001-90'], '12.345.678/0001-90'],
    [['1234567800019'], '1234567800019'],
    [[''], ''],
    [[null], ''],
    [['abc'], 'abc'],
    [[12345678000190], '12.345.678/0001-90']
  ],
  formatCNPJ: [
    [[0], '\u2014'],
    [[false], '\u2014'],
    [[{ $undefined: true }], '\u2014'],
    [['123'], '123'],
    [['12345678000190'], '12.345.678/0001-90'],
    [['12.345.678/0001-90'], '12.345.678/0001-90'],
    [['1234567800019'], '1234567800019'],
    [[''], '\u2014'],
    [[null], '\u2014'],
    [['abc'], 'abc'],
    [[12345678000190], '12.345.678/0001-90']
  ],
  normalizeSearchText: [
    [[0], ''],
    [[false], ''],
    [['  A\u00e7\u00e3o \u00daNICA  '], 'acao unica'],
    [[null], ''],
    [['Bota de Seguran\u00e7a'], 'bota de seguranca'],
    [['\u00c7\u00c3\u00d5'], 'cao'],
    [['\u0130'], 'i'],
    [[42], '42']
  ],
  parseCsvList: [
    [[0], []],
    [[false], []],
    [[''], []],
    [[null], []],
    [['a, b ,,c'], ['a', 'b', 'c']],
    [[' x '], ['x']],
    [[',,'], []],
    [[12], ['12']]
  ],
  parseCsvNumberList: [
    [[''], []],
    [['1,2,-3,0,x,4.5'], [1, 2, 4.5]],
    [[' 7 , 8 '], [7, 8]],
    [['1e2,Infinity,NaN'], [100]]
  ],
  parseOptionalJson: [
    [[{ $undefined: true }, { $undefined: true }], { $undefined: true }],
    [['', 'FB'], 'FB'],
    [['  ', null], null],
    [['{"a":1}', null], { a: 1 }],
    [['[1,2]', null], [1, 2]],
    [['null', 'FB'], null],
    [[null, 'FB'], 'FB'],
    [['{ruim', null], { throws: 'Error', message: 'JSON inv\u00e1lido na configura\u00e7\u00e3o avan\u00e7ada: ' }]
  ],
  normalizeHexColor: [
    [[0, 'F'], 'F'],
    [[false, 'F'], 'F'],
    [[{ $undefined: true }, { $undefined: true }], { $undefined: true }],
    [['#ABCDEF', 'F'], '#ABCDEF'],
    [['#abc', 'F'], '#aabbcc'],
    [['  #fff  ', 'F'], '#ffffff'],
    [['#12ab', 'F'], 'F'],
    [['fff', 'F'], 'F'],
    [['', 'F'], 'F'],
    [[null, null], null],
    [['#GGGGGG', 'F'], 'F']
  ],
  addDaysFromBaseDate: [
    [['2026-10-22', 1], '2026-10-23'],
    [['2026-12-31', 1], '2027-01-01'],
    [['2024-02-28', 1], '2024-02-29'],
    [['2026-03-01', -1], '2026-02-28'],
    [['2026-10-22', '7'], '2026-10-29'],
    [['2026-10-22', 0], '2026-10-22'],
    [['2026-13-01', 1], ''],
    [['22/10/2026', 1], ''],
    [['', 1], ''],
    [['2026-10-22', 'x'], { throws: 'RangeError', message: 'Invalid time value' }]
  ]
};

function load(context = {}) {
  const ctx = vm.createContext(context);
  ctx.globalThis = ctx;
  vm.runInContext(fs.readFileSync(path.join(JS_ROOT, MODULE), 'utf8'), ctx);
  return ctx;
}

// As tabelas são JSON: `undefined` vem codificado como { $undefined: true }.
const decode = (v) => (v && typeof v === 'object' && v.$undefined === true ? undefined : v);
const show = (v) => (v === undefined ? 'undefined' : JSON.stringify(v));

function outcome(fn, args) {
  try { return fn(...args); } catch (error) { return { throws: error.constructor.name, message: error.message }; }
}

module.exports = function ({ test, assert, eq }) {
  test('UBX-V2 value-format: publica os 14 nomes legados e o namespace congelado', () => {
    const ctx = load();
    for (const name of NAMES) { eq(typeof ctx[name], 'function', name); }
    const ns = ctx.__EPI_SHARED_VALUE_FORMAT__;
    assert(Object.isFrozen(ns), 'namespace congelado');
    eq(Object.keys(ns).sort().join(','), [...NAMES].sort().join(','));
    for (const name of NAMES) { assert(ns[name] === ctx[name], `${name} é a mesma função no namespace`); }
  });

  test('UBX-V2 value-format: carregar duas vezes não redefine as funções', () => {
    const ctx = load();
    const first = ctx.digitsOnly;
    vm.runInContext(fs.readFileSync(path.join(JS_ROOT, MODULE), 'utf8'), ctx);
    assert(ctx.digitsOnly === first, 'guarda de recarga');
  });

  for (const [name, rows] of Object.entries(EXPECTED)) {
    test(`UBX-V2 value-format: ${name} reproduz o app.js original (${rows.length} casos)`, () => {
      const ctx = load();
      // addDaysFromBaseDate usa horário local e toISOString (UTC): em fusos a
      // leste de UTC o dia desloca (defeito preexistente). As tabelas valem
      // para UTC e fusos a oeste (Brasil); a leste só os casos sem data são fixos.
      const eastOfUtc = new Date().getTimezoneOffset() < 0;
      for (const [rawArgs, rawExpected] of rows) {
        const args = rawArgs.map(decode);
        const expected = decode(rawExpected);
        const actual = outcome(ctx[name], args);
        if (name === 'addDaysFromBaseDate' && eastOfUtc && typeof expected === 'string' && expected) { continue; }
        if (expected && expected.throws) {
          eq(actual && actual.throws, expected.throws, `${name}(${args.map(show).join(', ')}) lança`);
          assert(String(actual.message).startsWith(expected.message), `${name}: mensagem ${actual.message}`);
          continue;
        }
        eq(show(actual), show(expected), `${name}(${args.map(show).join(', ')})`);
      }
    });
  }

  test('UBX-V2 value-format: daysUntil conta dias inteiros a partir de hoje (relógio fixo)', () => {
    const RealDate = Date;
    const NOW = new RealDate(2026, 9, 22, 15, 30).getTime();
    class FixedDate extends RealDate {
      constructor(...args) { super(...(args.length ? args : [NOW])); }
      static now() { return NOW; }
    }
    const ctx = load({ Date: FixedDate });
    eq(ctx.daysUntil(''), null);
    eq(ctx.daysUntil(null), null);
    eq(ctx.daysUntil('2026-10-22'), 0);
    eq(ctx.daysUntil('2026-10-23'), 1);
    eq(ctx.daysUntil('2026-10-21'), -1);
    eq(ctx.daysUntil('2026-11-21'), 30);
    eq(ctx.daysUntil('2027-10-22'), 365);
    assert(Number.isNaN(ctx.daysUntil('não é data')), 'data inválida vira NaN, como no original');
  });

  test('UBX-V2 value-format: app.js não declara mais os nomes e o módulo carrega antes dele', () => {
    const app = fs.readFileSync(path.resolve(JS_ROOT, '..', 'app.js'), 'utf8');
    for (const name of NAMES) {
      assert(!new RegExp(`^(?:async\\s+)?function\\s+${name}\\(`, 'm').test(app), `${name} voltou ao app.js`);
    }
    const scripts = fs.readFileSync(path.resolve(JS_ROOT, '..', 'views', '_scripts.html'), 'utf8');
    const order = [...scripts.matchAll(/<script[^>]+src="([^"?]+)/g)].map((m) => m[1]);
    const mod = order.indexOf(`/js/${MODULE}`);
    assert(mod >= 0, 'módulo listado em _scripts.html');
    assert(mod < order.indexOf('/app.js'), 'antes do app.js');
    for (const view of ['/js/views/purchases.js', '/js/views/procurement.js']) {
      assert(mod < order.indexOf(view), `antes de ${view} (lê fmtBrl/formatCNPJ via globalThis)`);
    }
  });
};
