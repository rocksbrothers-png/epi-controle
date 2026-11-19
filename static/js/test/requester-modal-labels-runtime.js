'use strict';
// UBX Compras — rótulos de status no modal do requisitante (openRequesterReviewModal,
// static/js/views/purchases.js).
//
// O modal lia globalThis.ITEM_STATUS_LABELS, que nunca existiu (o mapa era de bloco no
// app.js e, desde a UBX Compras P1, vive só no namespace congelado
// __EPI_PURCHASE_STATUS_UI__). Resultado: os itens bloqueados mostravam o código interno
// ("approved", "closed"...). O teste carrega, num contexto isolado, as peças REAIS da
// página — motor de tradução de static/i18n.js com os cinco catálogos, views/view-helpers.js
// (escapeHtml), modules/purchases/ui/purchase-status-view.js e views/purchases.js — com um
// DOM mínimo simulado, abre o modal de verdade e confere:
//   - o rótulo de cada status bloqueado é o do catálogo oficial no idioma ativo
//     (pt-BR, en-GB, es-ES, fr-FR, nb-NO), calculado de forma independente a partir do
//     mapa declarado no módulo e dos JSON dos catálogos;
//   - o código interno não aparece no lugar do rótulo e o payload do item não muda;
//   - itens editáveis e bloqueados continuam separados como antes;
//   - marcação no nome do EPI continua escapada;
//   - cancelar e clicar fora fecham o modal e resolvem null.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const STATIC = path.resolve(__dirname, '..', '..');
const LOCALES = ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO'];
const read = (rel) => fs.readFileSync(path.join(STATIC, rel), 'utf8');
const CATALOGS = Object.fromEntries(LOCALES.map((l) => [l, JSON.parse(read(`i18n/${l}.json`))]));
const LOCKED = ['approved', 'ordered', 'received', 'closed'];
const XSS = '<img src=x onerror=globalThis.__xss=1>';

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

// Expectativa independente: chave e texto padrão de cada status no mapa declarado no módulo.
function declaredItemLabels() {
  const src = read('js/modules/purchases/ui/purchase-status-view.js');
  const start = src.indexOf('const ITEM_STATUS_LABELS = {');
  if (start < 0) { throw new Error('ITEM_STATUS_LABELS ausente no módulo'); }
  const block = src.slice(start, balanced(src, start));
  const out = {};
  for (const m of block.matchAll(/get (\w+)\(\) \{ return \(tr\('([^']+)', '([^']+)'/g)) { out[m[1]] = { key: m[2], fallback: m[3] }; }
  return out;
}

function leaf(catalog, key) {
  let d = catalog;
  for (const part of key.split('.')) { if (!d || typeof d !== 'object' || !(part in d)) { return undefined; } d = d[part]; }
  return typeof d === 'string' ? d : undefined;
}

function element(tag) {
  const handlers = {};
  return {
    tag, style: {}, dataset: {}, value: '', removed: false, children: [], handlers,
    innerHTML: '',
    addEventListener(name, fn) { (handlers[name] = handlers[name] || []).push(fn); },
    appendChild(child) { this.children.push(child); return child; },
    remove() { this.removed = true; },
    closest() { return null; },
    querySelector(selector) {
      this.queried = this.queried || {};
      if (!this.queried[selector]) { this.queried[selector] = element(selector); }
      return this.queried[selector];
    },
    querySelectorAll() { return []; },
    fire(name, event = {}) { for (const fn of handlers[name] || []) { fn({ target: this, ...event }); } }
  };
}

function buildContext(lang) {
  const created = [];
  const document = {
    body: element('body'),
    createElement(tag) { const el = element(tag); created.push(el); return el; },
    getElementById() { return null; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    addEventListener() {}
  };
  const ctx = { JSON, Number, String, Object, Array, Promise, Symbol, Error, TypeError, Math, Intl, Date, RegExp, Set, Map, isNaN, console, document };
  ctx.globalThis = ctx;
  ctx.window = ctx;
  ctx.__CATALOGS__ = CATALOGS;
  vm.createContext(ctx);
  const i18n = read('i18n.js');
  vm.runInContext([
    "const FALLBACK = 'pt-BR'; const _pluralCount = Symbol('numeric plural count');",
    `let _lang = ${JSON.stringify(lang)}; let _active = __CATALOGS__[_lang]; let _fallback = __CATALOGS__['pt-BR'];`,
    ...['_resolve', '_interpolate', '_message', 't', 'trEpi'].map((n) => extractFunction(i18n, n)),
    'var tr = trEpi;'
  ].join('\n'), ctx);
  ctx.__EPI_APP_STATE__ = { user: { id: 1, role: 'master_admin' }, epis: [{ id: 5, name: 'Luva', company_id: 9 }] };
  for (const rel of ['js/views/view-helpers.js', 'js/modules/purchases/business/purchase-status-rules.js',
    'js/modules/purchases/ui/purchase-status-view.js', 'js/views/purchases.js']) {
    vm.runInContext(read(rel), ctx);
  }
  return { ctx, created };
}

function openModal(lang, items) {
  const { ctx, created } = buildContext(lang);
  const pr = { id: 77, company_id: 9, notes: '' };
  const promise = ctx.openRequesterReviewModal(pr, items);
  const overlay = created.find((el) => el.tag === 'div');
  if (!overlay) { throw new Error('modal não foi criado'); }
  return { ctx, overlay, promise };
}

async function run(assert) {
  const labels = declaredItemLabels();
  for (const status of LOCKED) { assert(labels[status], `status bloqueado ${status} sem rótulo declarado no catálogo oficial`); }
  let checks = 0;
  for (const lang of LOCALES) {
    const items = [
      ...LOCKED.map((status, i) => ({ id: 100 + i, status, epi_name: `EPI ${status}`, quantity_requested: i + 1 })),
      { id: 200, status: 'open', epi_name: XSS, quantity_requested: 2 }
    ];
    const snapshot = JSON.stringify(items);
    const { ctx, overlay, promise } = openModal(lang, items);
    const html = overlay.innerHTML;
    for (const status of LOCKED) {
      const { key, fallback } = labels[status];
      const expected = ctx.escapeHtml(leaf(CATALOGS[lang], key) ?? leaf(CATALOGS['pt-BR'], key) ?? fallback);
      assert(leaf(CATALOGS[lang], key) !== undefined, `${lang}: tradução ausente para ${key}`);
      assert(html.includes(`EPI ${status} <small style="color:var(--color-text-muted);">(${expected})</small>`),
        `${lang}: rótulo de ${status} deveria ser "${expected}"`);
      assert(!html.includes(`(${status})</small>`), `${lang}: código interno ${status} exibido no lugar do rótulo`);
      checks += 1;
    }
    // Item editável: segue nas linhas editáveis (sem rótulo de status) e o nome continua escapado.
    assert(html.includes('data-rr-row="200"'), `${lang}: item editável fora da tabela editável`);
    assert(!html.includes(XSS) && html.includes(ctx.escapeHtml(XSS)), `${lang}: nome do EPI deveria continuar escapado`);
    assert.strictEqual(JSON.stringify(items), snapshot, `${lang}: o modal não pode alterar os itens (códigos preservados)`);
    // Fechamento: cancelar resolve null e remove o modal.
    overlay.querySelector('#rr-cancel').fire('click');
    assert.strictEqual(await promise, null, `${lang}: cancelar deveria resolver null`);
    assert(overlay.removed, `${lang}: cancelar deveria remover o modal`);
    // Clique fora do cartão também fecha.
    const second = openModal(lang, items);
    second.overlay.fire('click', { target: second.overlay });
    assert.strictEqual(await second.promise, null, `${lang}: clique fora deveria resolver null`);
    assert(second.overlay.removed, `${lang}: clique fora deveria remover o modal`);
    assert.strictEqual(second.ctx.__xss, undefined, `${lang}: marcação executada`);
    checks += 3;
  }
  // A correção não cria global nova: o mapa segue só no namespace.
  const { ctx } = buildContext('pt-BR');
  assert.strictEqual(ctx.ITEM_STATUS_LABELS, undefined, 'ITEM_STATUS_LABELS não pode virar global');
  assert(!/=\s*globalThis\.ITEM_STATUS_LABELS\b/.test(read('js/views/purchases.js')), 'views/purchases.js ainda lê a global inexistente');
  return checks;
}

module.exports = function register({ testAsync }) {
  testAsync('UBX Compras: modal do requisitante mostra os rótulos oficiais nos 5 idiomas', async () => {
    const checks = await run(require('assert'));
    console.log(`    Modal do requisitante: ${checks} verificações (rótulos, códigos, escape, fechamento)`);
  });
};
module.exports.run = run;
