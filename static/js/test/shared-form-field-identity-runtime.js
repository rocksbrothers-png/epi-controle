'use strict';
// UBX-V3, Etapa 1 — caracterização de modules/shared/ui/form-field-identity.js.
//
// As tabelas foram GERADAS executando as funções ORIGINAIS do app.js (main
// 8c63ea00, fatiadas por nome) sobre o mesmo DOM falso abaixo, antes da
// extração. As funções que varrem o documento inteiro (ensure/normalize/
// audit/setup) foram comparadas também no Chromium real, original × módulo
// (docs/UBX_APPJS_AUDITORIA.md §11). Mudar um valor aqui é mudar regra.
const fs = require('fs'), path = require('path'), vm = require('vm');
const JS_ROOT = path.resolve(__dirname, '..');
const MODULE = 'modules/shared/ui/form-field-identity.js';
const NAMES = ['isViewActive', 'resolveFormFieldAutocomplete', 'describeFieldNode', 'getElementIdAttribute', 'isValidDomId',
  'toSafeId', 'setElementIdAttribute', 'normalizeInvalidDomIds', 'ensureFormFieldAttributes', 'auditFormFieldIssues',
  'setupFormFieldHardening'];

// DOM falso mínimo: só o que as funções puras de identificação usam.
function makeFakeDom() {
  class HTMLElement {
    constructor(tagName, attrs = {}, parent = null) {
      this.tagName = tagName.toUpperCase();
      this.attrs = { ...attrs };
      this.parent = parent;
      this.className = attrs.class || '';
    }
    get id() { return this.attrs.id || ''; }
    get name() { return this.attrs.name || ''; }
    getAttribute(n) { return Object.prototype.hasOwnProperty.call(this.attrs, n) ? this.attrs[n] : null; }
    setAttribute(n, v) { this.attrs[n] = String(v); }
    hasAttribute(n) { return Object.prototype.hasOwnProperty.call(this.attrs, n); }
    closest(sel) {
      let node = this;
      while (node) { if (node.tagName.toLowerCase() === sel) { return node; } node = node.parent; }
      return null;
    }
    get outerHTML() {
      const a = Object.entries(this.attrs).map(([k, v]) => ` ${k}="${v}"`).join('');
      return `<${this.tagName.toLowerCase()}${a}>   </${this.tagName.toLowerCase()}>`;
    }
  }
  const views = { '#ativa': { classList: { contains: (c) => c === 'active' } }, '#inativa': { classList: { contains: () => false } } };
  const document = { querySelector: (s) => views[s] || null };
  const form = new HTMLElement('form', { id: 'f1', class: 'card  grid extra' });
  const el = (tag, attrs, parent = form) => new HTMLElement(tag, attrs, parent);
  const nodes = {
    username: el('input', { id: 'login-username' }),
    password: el('input', { type: 'password', id: 'login-password' }),
    newPassword: el('input', { type: 'password', id: 'new-password' }),
    recovery: el('input', { type: 'password', name: 'recovery_code' }),
    email: el('input', { id: 'user-email' }),
    phone: el('input', { name: 'whatsapp' }),
    tel: el('input', { name: 'tel_fixo' }),
    name: el('input', { name: 'name' }),
    fullName: el('input', { id: 'full-name' }),
    search: el('input', { type: 'search', id: 'q' }),
    date: el('input', { type: 'date' }),
    hidden: el('input', { type: 'hidden', id: 'h' }),
    checkbox: el('input', { type: 'checkbox' }),
    select: el('select', { id: 's' }),
    textarea: el('textarea', {}),
    plain: el('input', { id: '  pad  ', placeholder: 'Digite', class: 'a b c' }),
    orphan: el('input', { id: 'orphan' }, null),
    form
  };
  return { HTMLElement, document, nodes, console: { warn() {} } };
}

const EXPECTED = {
  autocomplete: [
    ['username', 'username'],
    ['password', 'current-password'],
    ['newPassword', 'new-password'],
    ['recovery', 'new-password'],
    ['email', 'username'],
    ['phone', 'tel'],
    ['tel', 'tel'],
    ['name', 'name'],
    ['fullName', 'name'],
    ['search', 'off'],
    ['date', 'off'],
    ['hidden', null],
    ['checkbox', null],
    ['select', 'off'],
    ['textarea', 'off'],
    ['plain', 'off'],
    ['orphan', 'off'],
    ['form', 'off']
  ],
  autocompleteInvalid: [
    null,
    null,
    null,
    null
  ],
  getId: [
    ['username', 'login-username'],
    ['password', 'login-password'],
    ['newPassword', 'new-password'],
    ['recovery', ''],
    ['email', 'user-email'],
    ['phone', ''],
    ['tel', ''],
    ['name', ''],
    ['fullName', 'full-name'],
    ['search', 'q'],
    ['date', ''],
    ['hidden', 'h'],
    ['checkbox', ''],
    ['select', 's'],
    ['textarea', ''],
    ['plain', 'pad'],
    ['orphan', 'orphan'],
    ['form', 'f1'],
    ['null', '']
  ],
  describe: [
    ['plain', { id: 'pad', rawDomIdProperty: '  pad  ', tagName: 'input', name: '', type: '', placeholder: 'Digite', nearestFormId: 'f1', formId: 'f1', outerHTML: '<input id=" pad " placeholder="Digite" class="a b c"> </input>', selector: 'input#pad.a.b' }],
    ['orphan', { id: 'orphan', rawDomIdProperty: 'orphan', tagName: 'input', name: '', type: '', placeholder: '', nearestFormId: '', formId: '', outerHTML: '<input id="orphan"> </input>', selector: 'input#orphan' }],
    ['select', { id: 's', rawDomIdProperty: 's', tagName: 'select', name: '', type: '', placeholder: '', nearestFormId: 'f1', formId: 'f1', outerHTML: '<select id="s"> </select>', selector: 'select#s' }],
    ['nao-elemento', null]
  ],
  validId: [
    false,
    false,
    true,
    true,
    false,
    false,
    false,
    false,
    false,
    false,
    false,
    true,
    false,
    false,
    false
  ],
  safeId: [
    ['cadastro-de-epi', 'cadastro-de-epi'],
    ['fb', 'form'],
    ['fb', 'form'],
    ['x', 'x'],
    ['fb', 'form'],
    ['ok_1-2', 'ok_1-2'],
    ['fb', 'form'],
    ['fb', 'form']
  ],
  views: [
    true,
    false,
    false,
    false,
    false
  ],
  setId: [
    [true, 'novo-id'],
    [true, 'pad'],
    [false, 'pad'],
    [false, 'pad'],
    [false, 'pad'],
    [false, 'pad'],
    [false, 'pad'],
    [false, 'pad']
  ],
  setInvalidNode: [
    false,
    false
  ],
  emptyRoots: [
    [],
    null,
    { missingIdOrName: 0, missingAutocomplete: 0, duplicateIds: [], brokenLabels: [] }
  ]
};

function load(fake) {
  const ctx = vm.createContext({ HTMLElement: fake.HTMLElement, document: fake.document, console: fake.console });
  ctx.globalThis = ctx;
  vm.runInContext(fs.readFileSync(path.join(JS_ROOT, MODULE), 'utf8'), ctx);
  return ctx;
}

// Mesmo roteiro usado para gerar EXPECTED a partir das funções originais.
function scenario(fns, fake) {
  const out = {};
  const keys = Object.keys(fake.nodes);
  out.autocomplete = keys.map((k) => [k, fns.resolveFormFieldAutocomplete(fake.nodes[k])]);
  out.autocompleteInvalid = [null, undefined, {}, 'x'].map((v) => fns.resolveFormFieldAutocomplete(v));
  out.getId = keys.map((k) => [k, fns.getElementIdAttribute(fake.nodes[k])]).concat([['null', fns.getElementIdAttribute(null)]]);
  out.describe = ['plain', 'orphan', 'select'].map((k) => [k, fns.describeFieldNode(fake.nodes[k])]).concat([['nao-elemento', fns.describeFieldNode({})]]);
  out.validId = ['', '  ', 'ok', ' ok ', '[object X]', 'a<b', 'a"b', "a'b", 'null', 'NaN', 'UNDEFINED', 'a b', 123, null, undefined]
    .map((v) => fns.isValidDomId(v));
  out.safeId = ['Cadastro de EPI!', '  ', '', '--x--', 'ÁÉ', 'ok_1-2', 42, null].map((v) => [fns.toSafeId(v, 'fb'), fns.toSafeId(v)]);
  out.views = ['#ativa', '#inativa', '#nenhuma', '', null].map((s) => fns.isViewActive(s));
  const probe = new fake.HTMLElement('input');
  out.setId = ['novo-id', '  pad  ', '', 42, probe, '[object Y]', 'null', 'a"b'].map((v) => [fns.setElementIdAttribute(probe, v, 'probe'), probe.getAttribute('id')]);
  out.setInvalidNode = [fns.setElementIdAttribute(null, 'x'), fns.setElementIdAttribute({}, 'x')];
  out.emptyRoots = [fns.normalizeInvalidDomIds(null), fns.ensureFormFieldAttributes(null), fns.auditFormFieldIssues(null)];
  return out;
}

module.exports = function ({ test, assert, eq }) {
  test('UBX-V3 form-field-identity: publica os 11 nomes legados e o namespace congelado', () => {
    const ctx = load(makeFakeDom());
    for (const name of NAMES) { eq(typeof ctx[name], 'function', name); }
    const ns = ctx.__EPI_SHARED_FORM_FIELD_IDENTITY__;
    assert(Object.isFrozen(ns), 'namespace congelado');
    eq(Object.keys(ns).sort().join(','), [...NAMES].sort().join(','));
    for (const name of NAMES) { assert(ns[name] === ctx[name], `${name} é a mesma função no namespace`); }
  });

  for (const key of Object.keys(EXPECTED)) {
    test(`UBX-V3 form-field-identity: ${key} reproduz o app.js original`, () => {
      const fake = makeFakeDom();
      const actual = scenario(load(fake), fake)[key];
      eq(JSON.stringify(actual), JSON.stringify(EXPECTED[key]), key);
    });
  }

  test('UBX-V3 form-field-identity: carrega depois de utils/dom.js e antes do app.js e dos scripts legados', () => {
    // utils/dom.js publica uma getElementIdAttribute DIFERENTE (lê node.id);
    // a do app.js — agora deste módulo — precisa continuar vencendo.
    const scripts = fs.readFileSync(path.resolve(JS_ROOT, '..', 'views', '_scripts.html'), 'utf8');
    const order = [...scripts.matchAll(/<script[^>]+src="([^"?]+)/g)].map((m) => m[1]);
    const mod = order.indexOf(`/js/${MODULE}`);
    assert(mod >= 0, 'módulo listado em _scripts.html');
    assert(order.indexOf('/js/utils/dom.js') >= 0 && order.indexOf('/js/utils/dom.js') < mod, 'depois de utils/dom.js');
    assert(mod < order.indexOf('/app.js'), 'antes do app.js');
    for (const legacy of ['/estoque.js', '/colab-list.js', '/gestao-colab.js']) {
      const idx = order.indexOf(legacy);
      assert(idx < 0 || mod < idx, `antes de ${legacy} (usa isViewActive)`);
    }
    const app = fs.readFileSync(path.resolve(JS_ROOT, '..', 'app.js'), 'utf8');
    for (const name of NAMES) {
      assert(!new RegExp(`^(?:async\\s+)?function\\s+${name}\\(`, 'm').test(app), `${name} voltou ao app.js`);
    }
  });

  test('UBX-V3 form-field-identity: getElementIdAttribute lê o atributo, não a propriedade (≠ utils/dom.js)', () => {
    const fake = makeFakeDom();
    const ctx = load(fake);
    // <form id="fx"><input name="id"></form>: form.id devolve o <input>.
    const tricky = { getAttribute: (n) => (n === 'id' ? 'fx' : null), id: { tagName: 'INPUT' } };
    eq(ctx.getElementIdAttribute(tricky), 'fx');
  });
};

module.exports.makeFakeDom = makeFakeDom;
module.exports.scenario = scenario;
