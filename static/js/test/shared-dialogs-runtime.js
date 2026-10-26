'use strict';
// UBX-V4, Etapa A — caracterização de modules/shared/ui/dialogs.js
// (confirmDestructive e os helpers de modal).
//
// O MESMO roteiro roda sobre as funções ORIGINAIS do app.js (geração das
// tabelas, `main` antes da extração, dentro de um bloco com os WeakMaps do
// app.js) e sobre o módulo, com DOM falso que registra foco, blur, hidden,
// inert, classes e o handler de teclado. Ficam fixados: contrato de retorno do
// confirmDestructive (dsConfirm × confirm nativo, mesmo objeto de opções),
// seleção de focáveis, abertura (foco no primeiro focável), fechamento
// (blur, devolução de foco só se o elemento anterior ainda existe), Escape,
// ciclo de Tab/Shift+Tab e registro único do handler por modal.
const fs = require('fs'), path = require('path'), vm = require('vm');
const JS_ROOT = path.resolve(__dirname, '..');
const NAMES = ['confirmDestructive', 'getFocusableElements', 'openModal', 'closeModal', 'bindModalKeyboard'];

function makeEnv() {
  const log = [];
  const doc = { activeElement: null };
  class FakeEl {
    constructor(id, extra = {}) {
      Object.assign(this, { id, hidden: false, disabled: false, isConnected: true, children: [], attrs: {}, classes: new Set() }, extra);
      const el = this;
      this.classList = { add(c) { el.classes.add(c); log.push(['class+', id, c]); }, remove(c) { el.classes.delete(c); log.push(['class-', id, c]); } };
    }
    getAttribute(k) { return Object.prototype.hasOwnProperty.call(this.attrs, k) ? this.attrs[k] : null; }
    querySelectorAll(sel) { log.push(['qsa', this.id, sel]); return this.children; }
    contains(node) { return node === this || this.children.includes(node); }
    focus() { doc.activeElement = this; log.push(['focus', this.id]); }
    blur() { log.push(['blur', this.id]); doc.activeElement = null; }
  }
  const env = {
    log, doc, FakeEl, handlers: [],
    globals: {
      Array, Object, Promise, WeakMap, Error, String,
      HTMLElement: FakeEl,
      document: doc,
      safeOn: (target, name, handler) => { log.push(['safeOn', target.id, name]); env.handlers.push([target, name, handler]); },
      confirm: (m) => { log.push(['confirm', m]); return env.nativeAnswer; }
    }
  };
  return env;
}

function contextFor(env) {
  const ctx = vm.createContext({ ...env.globals });
  ctx.globalThis = ctx;
  return ctx;
}

function modalWith(env, ...kids) {
  const modal = new env.FakeEl('modal', { hidden: true });
  modal.children = kids;
  return modal;
}

async function scenario(run) {
  const out = {};
  const go = async (prep, act) => {
    const env = makeEnv(); prep(env); const f = run(env);
    let r;
    try { r = await act(f, env); } catch (error) { r = { thrown: `${error.name}: ${error.message}` }; }
    const modal = env.modal;
    return { r, log: env.log, active: env.doc.activeElement && env.doc.activeElement.id,
      modal: modal ? [modal.hidden, 'inert' in modal ? modal.inert : '-', [...modal.classes]] : null };
  };
  const none = () => {};

  const opts = { title: 'T', message: 'M', confirmLabel: 'OK', variant: 'danger' };
  out.confirmComDs = await go(none, async (f, env) => {
    let seen;
    f.globalThis.dsConfirm = async (o) => { seen = o; env.log.push(['ds', o.title]); return 'resp-ds'; };
    const r = await f.confirmDestructive(opts);
    return [r, seen === opts];
  });
  out.confirmNativo = await go((env) => { env.nativeAnswer = true; }, (f) => f.confirmDestructive(opts));
  out.confirmNativoRecusa = await go((env) => { env.nativeAnswer = false; }, (f) => f.confirmDestructive({}));
  out.confirmSemOpcoes = await go((env) => { env.nativeAnswer = 0; }, (f) => f.confirmDestructive());
  out.confirmDsNaoFuncao = await go((env) => { env.nativeAnswer = 'x'; }, (f) => { f.globalThis.dsConfirm = 'nope'; return f.confirmDestructive({ message: 'Q' }); });
  out.confirmEhPromessa = await go((env) => { env.nativeAnswer = true; }, (f) => f.confirmDestructive({ message: 'P' }) instanceof f.Promise);

  out.focaveisNulo = await go(none, (f) => f.getFocusableElements(null).length);
  out.focaveis = await go(none, (f, env) => {
    const kids = [new env.FakeEl('a'), new env.FakeEl('b', { disabled: true }), new env.FakeEl('c', { hidden: true }),
      new env.FakeEl('d', { attrs: { 'aria-hidden': 'true' } }), new env.FakeEl('e', { attrs: { 'aria-hidden': 'false' } })];
    return f.getFocusableElements(modalWith(env, ...kids)).map((el) => el.id);
  });

  out.abrirNulo = await go(none, (f) => f.openModal(null));
  out.abrir = await go(none, (f, env) => {
    const before = new env.FakeEl('before'); before.focus();
    env.modal = modalWith(env, new env.FakeEl('x', { disabled: true }), new env.FakeEl('first'), new env.FakeEl('second'));
    env.modal.inert = true;
    f.openModal(env.modal);
  });
  out.abrirSemFocaveis = await go(none, (f, env) => { env.modal = modalWith(env); f.openModal(env.modal); });
  out.abrirSemInert = await go(none, (f, env) => { env.modal = modalWith(env, new env.FakeEl('only')); delete env.modal.inert; f.openModal(env.modal); });
  out.abrirFocoNaoElemento = await go(none, (f, env) => {
    env.doc.activeElement = { id: 'texto' };
    env.modal = modalWith(env, new env.FakeEl('first'));
    f.openModal(env.modal); f.closeModal(env.modal);
  });

  out.fecharNulo = await go(none, (f) => f.closeModal(undefined));
  out.abrirFechar = await go(none, (f, env) => {
    const before = new env.FakeEl('before'); before.focus();
    env.modal = modalWith(env, new env.FakeEl('first')); env.modal.inert = false;
    f.openModal(env.modal); f.closeModal(env.modal);
  });
  out.fecharFocoForaDoModal = await go(none, (f, env) => {
    const before = new env.FakeEl('before'); before.focus();
    env.modal = modalWith(env, new env.FakeEl('first')); env.modal.inert = false;
    f.openModal(env.modal); new env.FakeEl('outside').focus(); f.closeModal(env.modal);
  });
  out.fecharAnteriorDesconectado = await go(none, (f, env) => {
    const before = new env.FakeEl('before'); before.focus();
    env.modal = modalWith(env, new env.FakeEl('first')); env.modal.inert = false;
    f.openModal(env.modal); before.isConnected = false; f.closeModal(env.modal);
  });
  out.fecharSemAbrir = await go(none, (f, env) => { env.modal = modalWith(env); env.modal.hidden = false; f.closeModal(env.modal); });

  const key = (k, shift = false) => {
    const ev = { key: k, shiftKey: shift, prevented: false, preventDefault() { this.prevented = true; } };
    return ev;
  };
  out.tecladoNulo = await go(none, (f) => f.bindModalKeyboard(null, () => {}));
  out.teclado = await go(none, (f, env) => {
    const a = new env.FakeEl('a'), b = new env.FakeEl('b'), c = new env.FakeEl('c');
    env.modal = modalWith(env, a, b, c);
    let closes = 0;
    f.bindModalKeyboard(env.modal, () => { closes++; env.log.push(['onClose']); });
    f.bindModalKeyboard(env.modal, () => { env.log.push(['segundo']); });
    const h = env.handlers[0][2];
    const res = [];
    const press = (ev) => { h(ev); res.push([ev.key, ev.shiftKey, ev.prevented, env.doc.activeElement && env.doc.activeElement.id]); };
    press(key('Escape'));
    c.focus(); press(key('Tab'));
    a.focus(); press(key('Tab', true));
    b.focus(); press(key('Tab')); press(key('Tab', true));
    press(key('Enter'));
    return [env.handlers.length, closes, res];
  });
  out.tecladoSemOnClose = await go(none, (f, env) => {
    env.modal = modalWith(env);
    f.bindModalKeyboard(env.modal);
    const ev = key('Escape'); env.handlers[0][2](ev);
    const tab = key('Tab'); env.handlers[0][2](tab);
    return [ev.prevented, tab.prevented];
  });
  return out;
}

const EXPECTED = {
  confirmComDs: { r: ['resp-ds', true], log: [['ds', 'T']], active: null, modal: null },
  confirmNativo: { r: true, log: [['confirm', 'M']], active: null, modal: null },
  confirmNativoRecusa: { r: false, log: [['confirm', '']], active: null, modal: null },
  confirmSemOpcoes: { r: 0, log: [['confirm', '']], active: null, modal: null },
  confirmDsNaoFuncao: { r: 'x', log: [['confirm', 'Q']], active: null, modal: null },
  confirmEhPromessa: { r: false, log: [['confirm', 'P']], active: null, modal: null },
  focaveisNulo: { r: 0, log: [], active: null, modal: null },
  focaveis: { r: ['a', 'e'], log: [['qsa', 'modal', 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])']], active: null, modal: null },
  abrirNulo: { log: [], active: null, modal: null },
  abrir: { log: [['focus', 'before'], ['class+', 'modal', 'is-open'], ['qsa', 'modal', 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'], ['focus', 'first']], active: 'first', modal: [false, false, ['is-open']] },
  abrirSemFocaveis: { log: [['class+', 'modal', 'is-open'], ['qsa', 'modal', 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'], ['focus', 'modal']], active: 'modal', modal: [false, '-', ['is-open']] },
  abrirSemInert: { log: [['class+', 'modal', 'is-open'], ['qsa', 'modal', 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'], ['focus', 'only']], active: 'only', modal: [false, '-', ['is-open']] },
  abrirFocoNaoElemento: { log: [['class+', 'modal', 'is-open'], ['qsa', 'modal', 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'], ['focus', 'first'], ['blur', 'first'], ['class-', 'modal', 'is-open']], active: null, modal: [true, '-', []] },
  fecharNulo: { log: [], active: null, modal: null },
  abrirFechar: { log: [['focus', 'before'], ['class+', 'modal', 'is-open'], ['qsa', 'modal', 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'], ['focus', 'first'], ['blur', 'first'], ['class-', 'modal', 'is-open'], ['focus', 'before']], active: 'before', modal: [true, true, []] },
  fecharFocoForaDoModal: { log: [['focus', 'before'], ['class+', 'modal', 'is-open'], ['qsa', 'modal', 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'], ['focus', 'first'], ['focus', 'outside'], ['class-', 'modal', 'is-open'], ['focus', 'before']], active: 'before', modal: [true, true, []] },
  fecharAnteriorDesconectado: { log: [['focus', 'before'], ['class+', 'modal', 'is-open'], ['qsa', 'modal', 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'], ['focus', 'first'], ['blur', 'first'], ['class-', 'modal', 'is-open']], active: null, modal: [true, true, []] },
  fecharSemAbrir: { log: [['class-', 'modal', 'is-open']], active: null, modal: [true, '-', []] },
  tecladoNulo: { log: [], active: null, modal: null },
  teclado: { r: [1, 1, [['Escape', false, true, null], ['Tab', false, true, 'a'], ['Tab', true, true, 'c'], ['Tab', false, false, 'b'], ['Tab', true, false, 'b'], ['Enter', false, false, 'b']]], log: [['safeOn', 'modal', 'keydown'], ['onClose'], ['focus', 'c'], ['qsa', 'modal', 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'], ['focus', 'a'], ['focus', 'a'], ['qsa', 'modal', 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'], ['focus', 'c'], ['focus', 'b'], ['qsa', 'modal', 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'], ['qsa', 'modal', 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])']], active: 'b', modal: [true, '-', []] },
  tecladoSemOnClose: { r: [true, false], log: [['safeOn', 'modal', 'keydown'], ['qsa', 'modal', 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])']], active: null, modal: [true, '-', []] }
};

function loadModule(env) {
  const ctx = contextFor(env);
  vm.runInContext(fs.readFileSync(path.join(JS_ROOT, 'modules', 'shared', 'ui', 'dialogs.js'), 'utf8'), ctx);
  return ctx;
}

module.exports = function ({ testAsync, test, assert, eq }) {
  testAsync('UBX-V4 diálogos: o módulo reproduz confirmDestructive e os helpers de modal originais', async () => {
    const actual = await scenario(loadModule);
    for (const key of Object.keys(EXPECTED)) {
      eq(JSON.stringify(actual[key]), JSON.stringify(EXPECTED[key]), key);
    }
    eq(Object.keys(actual).sort().join(','), Object.keys(EXPECTED).sort().join(','));
  });

  test('UBX-V4 diálogos: globais, namespace congelado, estado privado e ordem de carga', () => {
    const ctx = loadModule(makeEnv());
    for (const name of NAMES) { eq(typeof ctx[name], 'function', name); }
    assert(Object.isFrozen(ctx.__EPI_SHARED_DIALOGS__), 'namespace congelado');
    assert(!('modalFocusState' in ctx) && !('modalKeydownState' in ctx), 'WeakMaps continuam privados');
    const scripts = fs.readFileSync(path.resolve(JS_ROOT, '..', 'views', '_scripts.html'), 'utf8');
    const order = [...scripts.matchAll(/<script[^>]+src="([^"?]+)/g)].map((m) => m[1]);
    const idx = order.indexOf('/js/modules/shared/ui/dialogs.js');
    assert(idx >= 0 && idx < order.indexOf('/app.js') && idx < order.indexOf('/js/views/devolution.js'), 'antes do app.js e das views');
    const app = fs.readFileSync(path.resolve(JS_ROOT, '..', 'app.js'), 'utf8');
    for (const name of NAMES) {
      assert(!new RegExp(`^(?:async\\s+)?function\\s+${name}\\(`, 'm').test(app), `${name} voltou ao app.js`);
    }
    assert(!/^const modal(Focus|Keydown)State/m.test(app), 'WeakMaps de modal saíram do app.js');
  });
};

module.exports.scenario = scenario;
module.exports.contextFor = contextFor;
