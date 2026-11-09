'use strict';
// F0 — Ficha 360° de EPI: contrato de apresentação e ciclo de vida.
//
// Carrega os módulos REAIS (business + ui/lifecycle) num contexto vm isolado,
// com documento/janela falsos que respeitam AbortSignal. Prova: montagem,
// atualização, desmontagem, troca de colaborador, logout, troca de usuário na
// mesma aba e em outra aba, troca de empresa e de unidade, descarte de
// respostas obsoletas, ausência de listeners duplicados e de estado vazado.
const fs = require('fs'), path = require('path'), vm = require('vm');

const JS_ROOT = path.resolve(__dirname, '..');
const MODULES = [
  'modules/employee-ppe-360/business/employee-ppe-360-contract.js',
  'modules/employee-ppe-360/ui/employee-ppe-360-lifecycle.js'
];

function fakeTarget() {
  const listeners = new Map();
  return {
    addEventListener(type, fn, opts) {
      const signal = opts && opts.signal;
      if (signal && signal.aborted) { return; }
      const entry = { fn };
      if (!listeners.has(type)) { listeners.set(type, new Set()); }
      listeners.get(type).add(entry);
      if (signal) { signal.addEventListener('abort', () => listeners.get(type).delete(entry)); }
    },
    dispatch(type, event) { [...(listeners.get(type) || [])].forEach((e) => e.fn(event)); },
    count() { return [...listeners.values()].reduce((n, set) => n + set.size, 0); }
  };
}

function deferred() {
  let resolve, reject;
  const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

function makeEnv() {
  const doc = fakeTarget();
  const win = fakeTarget();
  const reported = [];
  const state = { user: { id: 7, role: 'admin', company_id: 1, operational_unit_id: 10 } };
  const sandbox = {
    Promise, JSON, Object, Array, String, Number, Error, Map, Set, Boolean, AbortController,
    console,
    __EPI_APP_STATE__: state,
    __EPI_FRONTEND_HELPERS__: { reportNonCriticalError: (err, meta) => reported.push([String(err && err.message), meta]) }
  };
  sandbox.globalThis = sandbox;
  sandbox.document = doc;
  vm.createContext(sandbox);
  for (const rel of MODULES) {
    vm.runInContext(fs.readFileSync(path.join(JS_ROOT, rel), 'utf-8'), sandbox, { filename: rel });
  }
  const container = { children: ['old'], replaceChildren() { this.children = []; } };
  const renders = [];
  return {
    sandbox, doc, win, state, reported, container, renders,
    b: sandbox.__EPI_EMPLOYEE_PPE_360_BUSINESS__,
    life: sandbox.__EPI_EMPLOYEE_PPE_360_LIFECYCLE__,
    controller(sections, extra = {}) {
      return sandbox.__EPI_EMPLOYEE_PPE_360_LIFECYCLE__.createController({
        container, sections, document: doc, window: win,
        render: (payload) => renders.push(payload),
        ...extra
      });
    }
  };
}

const ok = (data, page) => (page ? { ok: true, data, page } : { ok: true, data });

module.exports = function register({ test, testAsync, assert, eq }) {
  // ── business ──────────────────────────────────────────────────────────────
  test('ficha360 F0: namespaces publicados e congelados', () => {
    const env = makeEnv();
    assert(Object.isFrozen(env.b) && Object.isFrozen(env.life), 'namespaces precisam ser congelados');
    const own = Object.keys(env.sandbox).filter((k) => k.startsWith('__EPI_') && /PPE_360/.test(k)).sort();
    eq(JSON.stringify(own), JSON.stringify([
      '__EPI_EMPLOYEE_PPE_360_BUSINESS__', '__EPI_EMPLOYEE_PPE_360_LIFECYCLE__',
      '__EPI_MODULE_EMPLOYEE_PPE_360_BUSINESS_LOADED__', '__EPI_MODULE_EMPLOYEE_PPE_360_LIFECYCLE_LOADED__'
    ]));
  });

  test('ficha360 F0: id de colaborador só aceita inteiro positivo', () => {
    const { b } = makeEnv();
    eq(b.normalizeEmployeeId('42'), 42);
    eq(b.normalizeEmployeeId(7), 7);
    for (const bad of [0, -1, '1.5', '1e3', 'abc', '', null, undefined, true, '9999999999999']) {
      eq(b.normalizeEmployeeId(bad), null, `deveria recusar ${String(bad)}`);
    }
  });

  test('ficha360 F0: chave de contexto exige usuário, perfil, empresa e colaborador', () => {
    const { b } = makeEnv();
    const base = { userId: 7, role: 'admin', companyId: 1, unitId: 10, employeeId: 5 };
    assert(b.buildContextKey(base), 'contexto completo é válido');
    eq(b.buildContextKey({ ...base, userId: '' }), null);
    eq(b.buildContextKey({ ...base, role: '' }), null);
    eq(b.buildContextKey({ ...base, companyId: null }), null);
    eq(b.buildContextKey({ ...base, employeeId: 'x' }), null);
    assert(b.buildContextKey({ ...base, role: 'master_admin', companyId: null }), 'master_admin não tem empresa própria');
    const variations = [{ userId: 8 }, { role: 'user' }, { companyId: 2 }, { unitId: 11 }, { employeeId: 6 }];
    for (const change of variations) {
      assert(b.buildContextKey({ ...base, ...change }) !== b.buildContextKey(base), `mudança ${JSON.stringify(change)} deve mudar a chave`);
    }
  });

  test('ficha360 F0: paginação do cliente segue os limites do servidor', () => {
    const { b } = makeEnv();
    eq(JSON.stringify(b.normalizePageRequest({})), JSON.stringify({ limit: 20, cursor: null }));
    eq(b.normalizePageRequest({ limit: 100 }).limit, 100);
    for (const bad of [{ limit: 0 }, { limit: 101 }, { limit: '1.5' }, { cursor: 'a/b' }, { cursor: 'x'.repeat(201) }]) {
      eq(b.normalizePageRequest(bad), null, JSON.stringify(bad));
    }
  });

  test('ficha360 F0: envelope malformado é erro, nunca vazio', () => {
    const { b } = makeEnv();
    const S = b.SECTION_STATES;
    eq(b.sectionStateFor(b.readEnvelope(ok([1]))), S.READY);
    eq(b.sectionStateFor(b.readEnvelope(ok([]))), S.EMPTY);
    eq(b.readEnvelope(ok([], { limit: 20, next_cursor: 'abc' })).page.nextCursor, 'abc');
    for (const bad of [null, 'x', {}, { ok: true }, { ok: false }, ok([], { limit: 0, next_cursor: null }), ok([], { limit: 20, next_cursor: '../x' })]) {
      eq(b.readEnvelope(bad).state, S.ERROR, JSON.stringify(bad));
    }
    eq(b.readEnvelope({ ok: false, error: { code: 'EMPLOYEE_NOT_FOUND' } }).state, S.FORBIDDEN);
    eq(b.readEnvelope({ ok: false, error: { code: 'FORBIDDEN' } }).state, S.FORBIDDEN);
    eq(b.readEnvelope({ ok: false, error: { code: 'DESCONHECIDO' } }).state, S.ERROR);
  });

  // ── ciclo de vida ─────────────────────────────────────────────────────────
  testAsync('ficha360 F0: montagem recusa id inválido e ausência de sessão', async () => {
    const env = makeEnv();
    const c = env.controller({ resumo: async () => ok([1]) });
    eq((await c.mount('abc')).reason, 'INVALID_EMPLOYEE_ID');
    env.state.user = null;
    eq((await c.mount(5)).reason, 'NO_CONTEXT');
    eq(env.doc.count() + env.win.count(), 0, 'nada registrado sem montagem');
    eq(env.renders.length, 0);
  });

  testAsync('ficha360 F0: monta, desenha seções e desmonta limpando tudo', async () => {
    const env = makeEnv();
    const unmounts = [];
    const c = env.controller({ resumo: async ({ employeeId }) => ok({ id: employeeId }), entregas: async () => ok([]) },
      { onUnmount: (reason) => unmounts.push(reason) });
    const result = await c.mount(5);
    assert(result.ok, 'montagem deveria funcionar');
    eq(env.container.children.length, 0, 'conteúdo anterior do contêiner é descartado');
    eq(JSON.stringify(c.getState().sections), JSON.stringify({ resumo: 'ready', entregas: 'empty' }));
    eq(env.renders.filter((r) => r.state === 'loading').length, 2);
    eq(env.doc.count(), 1);
    eq(env.win.count(), 2);
    assert(c.unmount('fechar'), 'desmontagem');
    eq(env.doc.count() + env.win.count(), 0, 'listeners removidos');
    eq(c.getState().mounted, false);
    eq(JSON.stringify(unmounts), JSON.stringify(['fechar']));
    eq(c.unmount('de novo'), false, 'desmontar duas vezes é inócuo');
  });

  testAsync('ficha360 F0: troca de colaborador descarta a resposta atrasada do anterior', async () => {
    const env = makeEnv();
    const pending = {};
    const c = env.controller({ resumo: ({ employeeId }) => { pending[employeeId] = deferred(); return pending[employeeId].promise; } });
    const first = c.mount(5);
    const second = c.switchEmployee(6);
    pending[6].resolve(ok({ nome: 'B' }));
    pending[5].resolve(ok({ nome: 'A' }));
    await Promise.all([first, second]);
    const ready = env.renders.filter((r) => r.state === 'ready');
    eq(ready.length, 1);
    eq(ready[0].employeeId, 6);
    eq(env.doc.count() + env.win.count(), 3, 'troca não duplica listeners');
  });

  testAsync('ficha360 F0: logout durante a carga descarta a resposta e limpa o contêiner', async () => {
    const env = makeEnv();
    const d = deferred();
    const unmounts = [];
    const c = env.controller({ resumo: () => d.promise }, { onUnmount: (r) => unmounts.push(r) });
    const p = c.mount(5);
    env.state.user = null; // clearSession()
    env.container.children = ['dado do usuário anterior'];
    d.resolve(ok({ segredo: 1 }));
    await p;
    eq(env.renders.filter((r) => r.state === 'ready').length, 0, 'nada desenhado após logout');
    eq(env.container.children.length, 0);
    eq(JSON.stringify(unmounts), JSON.stringify(['context-changed']));
    eq(env.doc.count() + env.win.count(), 0);
  });

  for (const [label, change] of [
    ['troca de usuário na mesma aba', (s) => { s.user = { ...s.user, id: 8 }; }],
    ['troca de empresa', (s) => { s.user = { ...s.user, company_id: 2 }; }],
    ['troca de unidade', (s) => { s.user = { ...s.user, operational_unit_id: 11 }; }],
    ['troca de perfil', (s) => { s.user = { ...s.user, role: 'user' }; }]
  ]) {
    testAsync(`ficha360 F0: ${label} invalida respostas em voo e o refresh`, async () => {
      const env = makeEnv();
      const d = deferred();
      const c = env.controller({ resumo: () => d.promise });
      const p = c.mount(5);
      change(env.state);
      d.resolve(ok({ x: 1 }));
      await p;
      eq(env.renders.filter((r) => r.state === 'ready').length, 0);
      eq(c.getState().mounted, false);

      const env2 = makeEnv();
      const c2 = env2.controller({ resumo: async () => ok({ x: 1 }) });
      await c2.mount(5);
      change(env2.state);
      eq((await c2.refresh()).reason, 'CONTEXT_CHANGED');
      eq(c2.getState().mounted, false);
      eq(env2.doc.count() + env2.win.count(), 0);
    });
  }

  testAsync('ficha360 F0: navegação, saída da página e sessão de outra aba desmontam', async () => {
    const env = makeEnv();
    const c = env.controller({ resumo: async () => ok([1]) });
    await c.mount(5);
    env.doc.dispatch('epi:viewchange', { detail: { view: 'colaboradores' } });
    eq(c.getState().mounted, true, 'redesenho da própria tela não desmonta');
    env.win.dispatch('storage', { key: 'tema' });
    eq(c.getState().mounted, true, 'chave não relacionada à sessão não desmonta');
    env.doc.dispatch('epi:viewchange', { detail: { view: 'epis' } });
    eq(c.getState().mounted, false);

    await c.mount(5);
    env.win.dispatch('pagehide', {});
    eq(c.getState().mounted, false);

    await c.mount(5);
    env.win.dispatch('storage', { key: 'epi_token' });
    eq(c.getState().mounted, false, 'logout/login em outra aba');
    await c.mount(5);
    env.win.dispatch('storage', { key: null });
    eq(c.getState().mounted, false, 'storage.clear() em outra aba');
    eq(env.doc.count() + env.win.count(), 0);
  });

  testAsync('ficha360 F0: fachada mantém uma Ficha ativa por vez', async () => {
    const env = makeEnv();
    const opts = { container: env.container, document: env.doc, window: env.win, render: () => {}, sections: { resumo: async () => ok([1]) } };
    await env.life.mountEmployeePpe360({ ...opts, employeeId: 5 });
    await env.life.mountEmployeePpe360({ ...opts, employeeId: 6 });
    eq(env.doc.count() + env.win.count(), 3, 'a montagem anterior saiu inteira');
    eq(env.life.getEmployeePpe360State().employeeId, 6);
    assert((await env.life.refreshEmployeePpe360()).ok);
    assert(env.life.unmountEmployeePpe360('fim'));
    eq(env.life.unmountEmployeePpe360('fim'), false);
    eq((await env.life.refreshEmployeePpe360()).reason, 'NOT_MOUNTED');
    eq(env.doc.count() + env.win.count(), 0);
  });

  testAsync('ficha360 F0: falha de loader vira estado de erro; falha de render é reportada', async () => {
    const env = makeEnv();
    const c = env.controller({
      falha: async () => { const e = new Error('rede'); e.code = 'NETWORK'; throw e; },
      proibido: async () => ({ ok: false, error: { code: 'FORBIDDEN', message: 'x' } })
    });
    await c.mount(5);
    eq(JSON.stringify(c.getState().sections), JSON.stringify({ falha: 'error', proibido: 'forbidden' }));

    const env2 = makeEnv();
    const c2 = env2.sandbox.__EPI_EMPLOYEE_PPE_360_LIFECYCLE__.createController({
      container: env2.container, document: env2.doc, window: env2.win, sections: { resumo: async () => ok([1]) },
      render: () => { throw new Error('quebrou'); }
    });
    assert((await c2.mount(5)).ok, 'falha de render não derruba a Ficha');
    assert(env2.reported.length >= 1 && env2.reported[0][1].module === 'employee-ppe-360');
  });

  testAsync('ficha360 F0: estado exposto não carrega dados e paginação inválida é recusada', async () => {
    const env = makeEnv();
    const c = env.controller({ entregas: async () => ok([{ cpf: '123' }], { limit: 20, next_cursor: 'abc' }) });
    await c.mount(5);
    const exposed = JSON.stringify(c.getState());
    assert(!exposed.includes('123'), 'getState não expõe dados de colaborador');
    eq((await c.loadMore('entregas', '../etc')).reason, 'INVALID_PAGINATION');
    eq((await c.loadMore('inexistente', 'abc')).reason, 'NOT_MOUNTED');
    const more = await c.loadMore('entregas', 'abc');
    eq(more.stale, false);
  });

  test('ficha360 F0: guarda de domínio passa na árvore versionada', () => {
    const { check } = require('./employee-ppe-360-boundary');
    const { errors } = check();
    eq(errors.length, 0, errors.join('\n'));
  });
};
