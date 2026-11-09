'use strict';

// Ficha 360° de EPI — ciclo de vida e orquestração (F0, camada UI).
//
// Contrato: mountEmployeePpe360(options) / refreshEmployeePpe360() /
// unmountEmployeePpe360(reason). A F1 abre a Ficha a partir do módulo
// Colaboradores (modules/employees/ui) e fornece:
//   - container: elemento que a Ficha possui por inteiro;
//   - sections: { nome: loader({ employeeId, page }) → Promise<envelope> } —
//     os loaders vêm de modules/employee-ppe-360/integrations/ (F1+). ESTE
//     arquivo não faz HTTP (guarda de domínio);
//   - render({ section, state, result, employeeId }): desenha uma seção.
//
// Garantias (testadas em static/js/test/employee-ppe-360-lifecycle-runtime.js):
//  1. Uma Ficha ativa por vez: montar outra desmonta a anterior (sem listeners
//     duplicados).
//  2. Resposta obsoleta nunca é desenhada: cada carga leva a "geração" e a chave
//     de contexto (usuário + perfil + empresa + unidade + colaborador) vigentes;
//     se qualquer uma mudou quando a resposta chega, ela é descartada.
//  3. Mudança de identidade/escopo (logout, troca de usuário na mesma aba ou em
//     outra aba, troca de empresa ou de unidade) DESMONTA a Ficha e limpa o
//     contêiner — dado de um contexto não sobrevive no seguinte.
//  4. Navegar para outra tela (epi:viewchange) ou sair da página (pagehide)
//     desmonta. Todos os listeners são registrados com AbortSignal e saem juntos.
//  5. Estado só em memória, no fechamento do controlador; nada em storage.
(function () {
  if (globalThis.__EPI_MODULE_EMPLOYEE_PPE_360_LIFECYCLE_LOADED__) { return; }
  globalThis.__EPI_MODULE_EMPLOYEE_PPE_360_LIFECYCLE_LOADED__ = true;

  const DEFAULT_HOST_VIEW = 'colaboradores';

  function business() { return globalThis.__EPI_EMPLOYEE_PPE_360_BUSINESS__; }

  function reportError(error, where) {
    const helpers = globalThis.__EPI_FRONTEND_HELPERS__ || {};
    if (typeof helpers.reportNonCriticalError === 'function') {
      helpers.reportNonCriticalError(error, { module: 'employee-ppe-360', where });
    }
  }

  // Contexto vigente lido do estado oficial da sessão. Só identificadores —
  // nunca token ou permissões copiados para dentro da Ficha.
  function readAppContext() {
    const user = (globalThis.__EPI_APP_STATE__ || {}).user;
    if (!user) { return null; }
    return {
      userId: user.id,
      role: user.role,
      companyId: user.company_id,
      unitId: user.operational_unit_id
    };
  }

  function isSessionStorageKey(key) {
    // key null = storage.clear() em outra aba.
    return key === null || /token|session|permission|user/i.test(String(key));
  }

  function createController(options) {
    const opts = options || {};
    const b = business();
    if (!b) { throw new Error('employee-ppe-360: camada business não carregada.'); }
    const container = opts.container;
    if (!container) { throw new Error('employee-ppe-360: container obrigatório.'); }
    if (typeof opts.render !== 'function') { throw new Error('employee-ppe-360: render obrigatório.'); }
    const sections = Object.freeze({ ...(opts.sections || {}) });
    for (const [name, loader] of Object.entries(sections)) {
      if (typeof loader !== 'function') { throw new Error(`employee-ppe-360: loader inválido (${name}).`); }
    }
    const render = opts.render;
    const readContext = typeof opts.readContext === 'function' ? opts.readContext : readAppContext;
    const hostView = opts.hostView || DEFAULT_HOST_VIEW;
    const doc = opts.document || globalThis.document;
    const win = opts.window || globalThis;
    const onUnmount = typeof opts.onUnmount === 'function' ? opts.onUnmount : null;

    let mounted = false;
    let generation = 0;
    let employeeId = null;
    let contextKey = null;
    let listeners = null;
    const sectionStates = new Map();

    function keyFor(id) {
      const ctx = readContext();
      return ctx ? b.buildContextKey({ ...ctx, employeeId: id }) : null;
    }

    function contextStillValid() {
      return mounted && contextKey !== null && keyFor(employeeId) === contextKey;
    }

    function clearContainer() {
      if (typeof container.replaceChildren === 'function') {
        container.replaceChildren();
      } else {
        container.textContent = '';
      }
    }

    function teardown(reason) {
      mounted = false;
      generation += 1;
      if (listeners) { listeners.abort(); listeners = null; }
      sectionStates.clear();
      employeeId = null;
      contextKey = null;
      clearContainer();
      if (onUnmount) {
        try { onUnmount(reason); } catch (err) { reportError(err, 'onUnmount'); }
      }
    }

    function bindListeners() {
      listeners = new AbortController();
      const signal = listeners.signal;
      if (doc && typeof doc.addEventListener === 'function') {
        doc.addEventListener('epi:viewchange', (event) => {
          const view = event && event.detail ? event.detail.view : null;
          if (view !== hostView) { teardown('viewchange'); }
        }, { signal });
      }
      if (win && typeof win.addEventListener === 'function') {
        win.addEventListener('pagehide', () => teardown('pagehide'), { signal });
        win.addEventListener('storage', (event) => {
          if (isSessionStorageKey(event ? event.key : null)) { teardown('session-changed'); }
        }, { signal });
      }
    }

    function safeRender(payload) {
      try {
        render(payload);
      } catch (err) {
        reportError(err, `render:${payload.section}`);
      }
    }

    async function loadSection(name, gen, page) {
      const loader = sections[name];
      sectionStates.set(name, b.SECTION_STATES.LOADING);
      safeRender({ section: name, state: b.SECTION_STATES.LOADING, result: null, employeeId });
      const requestedFor = employeeId;
      let body;
      try {
        body = await loader({ employeeId: requestedFor, page: page || null });
      } catch (err) {
        body = { ok: false, error: { code: (err && typeof err.code === 'string') ? err.code : 'REQUEST_FAILED' } };
      }
      // Descartes: geração nova (troca de colaborador/refresh/desmontagem) ou
      // contexto diferente (logout, outro usuário, outra empresa/unidade).
      if (gen !== generation || !mounted) { return { section: name, stale: true }; }
      if (!contextStillValid()) {
        teardown('context-changed');
        return { section: name, stale: true };
      }
      const result = b.readEnvelope(body);
      const state = b.sectionStateFor(result);
      sectionStates.set(name, state);
      safeRender({ section: name, state, result, employeeId: requestedFor });
      return { section: name, stale: false, state };
    }

    function refresh() {
      if (!mounted) { return Promise.resolve({ ok: false, reason: 'NOT_MOUNTED' }); }
      if (!contextStillValid()) {
        teardown('context-changed');
        return Promise.resolve({ ok: false, reason: 'CONTEXT_CHANGED' });
      }
      generation += 1;
      const gen = generation;
      return Promise.all(Object.keys(sections).map((name) => loadSection(name, gen)))
        .then((results) => ({ ok: true, results }));
    }

    function mount(rawEmployeeId) {
      const id = b.normalizeEmployeeId(rawEmployeeId);
      if (!id) { return Promise.resolve({ ok: false, reason: 'INVALID_EMPLOYEE_ID' }); }
      const key = keyFor(id);
      if (!key) { return Promise.resolve({ ok: false, reason: 'NO_CONTEXT' }); }
      if (mounted) { teardown('switch-employee'); } else { clearContainer(); }
      mounted = true;
      employeeId = id;
      contextKey = key;
      bindListeners();
      return refresh();
    }

    function loadMore(name, cursor) {
      if (!mounted || !sections[name]) { return Promise.resolve({ ok: false, reason: 'NOT_MOUNTED' }); }
      const page = b.normalizePageRequest({ cursor });
      if (!page) { return Promise.resolve({ ok: false, reason: 'INVALID_PAGINATION' }); }
      return loadSection(name, generation, page);
    }

    function unmount(reason) {
      if (!mounted) { return false; }
      teardown(reason || 'unmount');
      return true;
    }

    function getState() {
      return Object.freeze({
        mounted,
        employeeId,
        sections: Object.freeze(Object.fromEntries(sectionStates))
      });
    }

    return Object.freeze({ mount, switchEmployee: mount, refresh, loadMore, unmount, getState });
  }

  // Fachada com uma Ficha ativa por vez.
  let active = null;

  function mountEmployeePpe360(options) {
    if (active) { active.unmount('replaced'); }
    active = createController(options);
    return active.mount((options || {}).employeeId);
  }

  function refreshEmployeePpe360() {
    return active ? active.refresh() : Promise.resolve({ ok: false, reason: 'NOT_MOUNTED' });
  }

  function unmountEmployeePpe360(reason) {
    if (!active) { return false; }
    const done = active.unmount(reason);
    active = null;
    return done;
  }

  function getEmployeePpe360State() {
    return active ? active.getState() : Object.freeze({ mounted: false, employeeId: null, sections: Object.freeze({}) });
  }

  globalThis.__EPI_EMPLOYEE_PPE_360_LIFECYCLE__ = Object.freeze({
    createController,
    mountEmployeePpe360,
    refreshEmployeePpe360,
    unmountEmployeePpe360,
    getEmployeePpe360State
  });
})();
