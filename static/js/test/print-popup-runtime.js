'use strict';
// Fixture literal × função servida; relógio determinístico, DOM e bordas de popup simulados.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');
const STATIC = path.resolve(__dirname, '..', '..');
const MODULE = 'js/modules/shared/ui/print-popup.js';
const FIXTURE = 'js/test/fixtures/app-before-ubx-print-popup.js.txt';
const read = p => fs.readFileSync(path.join(STATIC, p), 'utf8');

function extract(source) {
  const m = /^function openAndPrintPopup\(.*?^}/ms.exec(source);
  if (!m) { throw new Error('openAndPrintPopup ausente no app.js'); }
  return m[0];
}

function exercise(original, scenario, mutation) {
  const log = [], timers = [], listeners = [];
  let now = 0, sequence = 0;
  const fail = name => {
    if (scenario.failure === name) { throw new Error('QA ' + name); }
  };
  const document = {
    open() { log.push(['document.open']); fail('document.open'); },
    write(html) { log.push(['document.write', html]); fail('document.write'); },
    close() { log.push(['document.close']); fail('document.close'); },
    get readyState() { log.push(['readyState']); fail('readyState'); return scenario.ready; }
  };
  const popup = {
    document,
    focus() { log.push(['focus', now]); fail('focus'); },
    print() { log.push(['print', now]); fail('print'); }
  };
  const ctx = {
    String, Object, Error,
    console: { warn: (...args) => log.push(['warn', ...args.map(v => v instanceof Error ? [v.name, v.message] : v)]) },
    open: (...args) => {
      log.push(['open', ...args.map(v => v === undefined ? ['undefined'] : v && typeof v === 'object' ? ['object'] : v)]);
      fail('open'); return scenario.blocked ? null : popup;
    },
    safeOn: (target, event, listener, options) => {
      log.push(['safeOn', target === popup, event, {...options}]); fail('safeOn');
      listeners.push({event, listener, once: options?.once, used: false});
    },
    setTimeout: (callback, delay) => {
      log.push(['setTimeout', delay, now]); fail('setTimeout');
      timers.push({at: now + delay, sequence: sequence++, callback});
      return sequence;
    }
  };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  let source = original ? read(FIXTURE) : fs.existsSync(path.join(STATIC, MODULE)) ? read(MODULE) : extract(read('app.js'));
  if (mutation && !original) {
    const [from, to] = mutation;
    if (!source.includes(from)) { throw new Error('mutação sem alvo: ' + from); }
    source = source.replace(from, to);
  }
  vm.runInContext(source, ctx);
  let html = scenario.html;
  if (html === 'object') {
    html = {toString() { log.push(['toString']); return '  <p>Objeto</p>  '; }};
  } else if (html === 'throwing-object') {
    html = {toString() { log.push(['toString']); throw new Error('QA toString'); }};
  }
  let result;
  try {
    const value = scenario.noArgs ? ctx.openAndPrintPopup() : ctx.openAndPrintPopup(html, scenario.features);
    result = value === popup ? 'popup' : value === null ? 'null' : ['other', typeof value];
  } catch (error) { result = ['threw', error.name, error.message]; }
  // Eventos reais podem anteceder ou suceder o fallback de 500 ms. Não deduplicar impressão legada.
  for (const at of scenario.loads || []) {
    timers.push({at, sequence: sequence++, callback: () => {
      for (const listener of listeners) {
        if (listener.event === 'load' && !(listener.once && listener.used)) {
          listener.used = true; listener.listener();
        }
      }
    }});
  }
  while (timers.length) {
    timers.sort((a, b) => a.at - b.at || a.sequence - b.sequence);
    const next = timers.shift(); now = next.at;
    try { next.callback(); } catch (error) { log.push(['asyncError', error.name, error.message]); }
  }
  return {result, log};
}

function scenarios() {
  const out = [];
  for (const html of [undefined, null, '', ' \n\t ', false, 0, NaN, '0', '\n<p>Olá & €</p>\n', '<style>p{color:red}</style>', 'object', 'throwing-object']) {
    for (const features of [undefined, null, '', 'width=520,height=700', {}]) {
      for (const ready of ['complete', 'loading', 'interactive']) {
        for (const loads of [[], [0], [40, 200], [600]]) { out.push({html, features, ready, loads}); }
      }
    }
  }
  for (const failure of ['open', 'document.open', 'document.write', 'document.close', 'readyState', 'safeOn', 'setTimeout', 'focus', 'print']) {
    for (const ready of ['complete', 'loading']) {
      out.push({html: '<p>QA</p>', ready, loads: [40, 200], failure});
    }
  }
  out.push({blocked: true, html: '<p>QA</p>', ready: 'loading'});
  out.push({noArgs: true, ready: 'complete'});
  return out;
}

function compareAll(mutation) {
  let count = 0;
  for (const scenario of scenarios()) {
    const before = exercise(true, scenario), current = exercise(false, scenario, mutation);
    assert.deepStrictEqual(current, before, 'cenário: ' + JSON.stringify(scenario)); count++;
  }
  return count;
}

function protocol() {
  const blocked = exercise(false, {blocked: true, html: '<p>x</p>'});
  assert.strictEqual(blocked.result, 'null');
  assert.deepStrictEqual(blocked.log, [['open', '', '_blank', 'width=1100,height=800']]);
  const empty = exercise(false, {html: ' \n ', ready: 'complete'});
  assert.strictEqual(empty.result, 'popup');
  assert.strictEqual(empty.log.length, 1);
  const complete = exercise(false, {html: '  <p>x</p>  ', ready: 'complete'});
  assert.deepStrictEqual(complete.log, [['open', '', '_blank', 'width=1100,height=800'], ['document.open'],
    ['document.write', '<p>x</p>'], ['document.close'], ['readyState'], ['setTimeout', 80, 0], ['focus', 80], ['print', 80]]);
  const pending = exercise(false, {html: '<p>x</p>', ready: 'loading', loads: [40, 200]});
  assert.deepStrictEqual(pending.log.filter(l => l[0] === 'print'), [['print', 120], ['print', 500]]);
  assert.deepStrictEqual(pending.log.find(l => l[0] === 'safeOn'), ['safeOn', true, 'load', {once: true}]);
  const closed = exercise(false, {html: '<p>x</p>', ready: 'complete', failure: 'focus'});
  assert.strictEqual(closed.result, 'popup');
  assert.strictEqual(closed.log.filter(l => l[0] === 'warn').length, 1);
  assert.strictEqual(closed.log.filter(l => l[0] === 'print').length, 0);
}

function contracts() {
  const app = read('app.js');
  if (!fs.existsSync(path.join(STATIC, MODULE))) {
    assert.strictEqual(extract(app), read(FIXTURE).trimEnd());
    return;
  }
  assert(!/^function openAndPrintPopup\(/m.test(app), 'função saiu do monólito');
  const ctx = {Object}; ctx.globalThis = ctx;
  vm.createContext(ctx); vm.runInContext(read(MODULE), ctx);
  assert(Object.isFrozen(ctx.__EPI_SHARED_PRINT_POPUP__));
  assert.strictEqual(ctx.openAndPrintPopup, ctx.__EPI_SHARED_PRINT_POPUP__.openAndPrintPopup);
  const first = ctx.openAndPrintPopup;
  vm.runInContext(read(MODULE), ctx);
  assert.strictEqual(first, ctx.openAndPrintPopup, 'carga idempotente');
  const scripts = [...read('views/_scripts.html').matchAll(/src="([^"?]+)/g)].map(m => m[1]);
  assert.strictEqual(scripts.filter(s => s === '/' + MODULE).length, 1);
  for (const consumer of ['/app.js', '/js/modules/commercial/ui/commercial-view.js', '/js/modules/employees/ui/employees-view.js']) {
    assert(scripts.indexOf('/' + MODULE) < scripts.indexOf(consumer), 'helper antes de ' + consumer);
  }
  assert(!/\b(?:state|refs|api|fetch|localStorage|sessionStorage)\b/.test(read(MODULE)), 'sem estado, HTTP ou armazenamento');
}

module.exports = ({test}) => {
  test('UBX impressão: equivalência de retorno, erros, ordem, eventos e timers', () => {
    console.log('    Impressão: ' + compareAll() + ' comparações, zero divergências');
  });
  test('UBX impressão: popup bloqueada/vazia, foco antes de imprimir, load once e fallback', protocol);
  test('UBX impressão: global legado, namespace congelado, ordem e carga única', contracts);
};
module.exports.compareAll = compareAll;
module.exports.protocol = protocol;
module.exports.contracts = contracts;
if (require.main === module) {
  contracts(); protocol(); console.log('UBX impressão OK: ' + compareAll() + ' comparações');
}
