'use strict';
// UBX-V5, Etapa 2 (Unidades e CNPJ) — caracterização de modules/legal-entities e modules/units.
//
// Os MESMOS cenários rodam contra os módulos e contra as funções ORIGINAIS do
// app.js (fixtures/app-before-ubx-v5-units-legal-entities.js.txt, main 4aca4ada),
// no mesmo ambiente, e os resultados têm de ser idênticos. As regras puras REAIS
// de js/views/legal-entity-fields.js e js/views/legal-entities-view.js são
// carregadas (e, num grupo de cenários, omitidas para cobrir os fallbacks). Cada
// cenário registra chamadas (API, confirm, alert, bootstrap, rótulo do botão,
// navegação, populateSelect, renderTables), o estado dos campos/formulários e o
// HTML das tabelas.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const JS_ROOT = path.resolve(__dirname, '..');
const FROZEN_FILE = path.join(__dirname, 'fixtures', 'app-before-ubx-v5-units-legal-entities.js.txt');
const RULES = ['views/legal-entity-fields.js', 'views/legal-entities-view.js'];
const MODULES = ['modules/legal-entities/integrations/legal-entities-api.js', 'modules/legal-entities/ui/legal-entities-view.js',
  'modules/units/business/unit-rules.js', 'modules/units/ui/units-view.js'];
const NAMES = ['legalEntityHelpers', 'legalEntitiesForCompany', 'unitLegalEntityLabel', 'legalEntityOptionsHtml', 'legalEntitiesViewHelpers',
  'renderLegalEntities', 'formatLegalEntityRow', 'syncLegalEntitiesFilters', 'syncLegalEntityCompanyField', 'setLegalEntityFormMode',
  'resetLegalEntityForm', 'startEditLegalEntity', 'deactivateLegalEntity', 'syncUnitLegalEntityOptions', 'syncReportLegalEntityOptions',
  'unitsForSearchByCompany', 'syncUnitsSearchFilters', 'applyUnitsFilters', 'formatUnitTableRow', 'formatUnitOption', 'startEditUnit'];

const LEGAL_ENTITIES = [
  { id: 1, company_id: 901, cnpj: '11.222.333/0001-81', legal_name: 'Matriz <SA>', trade_name: 'Mtz', entity_type: 'matriz', active: 1,
    state_registration: 'IE1', municipal_registration: 'IM1', cnae: '1234', opening_date: '2020-01-01', address: 'Rua A', municipality: 'Macaé',
    uf: 'RJ', cep: '27900', notes: 'n1' },
  { id: 2, company_id: 901, cnpj: '11.222.333/0002-62', legal_name: 'Filial', trade_name: '', entity_type: 'filial', active: 0 },
  { id: 3, company_id: 901, cnpj: '11.222.333/0003-43', legal_name: 'SPE "x"', entity_type: 'spe', active: true },
  { id: 4, company_id: 902, cnpj: '99.888.777/0001-00', legal_name: 'Outra', entity_type: 'outro', active: '1' }
];
const UNITS = [
  { id: 5, company_id: 901, company_name: 'Empresa QA', name: 'Base Norte', unit_type: 'base', city: 'Macaé', notes: 'obs',
    legal_entity_id: 1, legal_entity_cnpj: '11.222.333/0001-81', legal_entity_name: 'Matriz' },
  { id: 6, company_id: 901, company_name: 'Empresa QA', name: 'Navio <1>', unit_type: 'navio', city: 'Rio', legal_entity_id: null },
  { id: 7, company_id: 902, company_name: 'Outra', name: 'Plataforma', unit_type: 'plataforma', city: 'Vitória' },
  // Tipo em maiúsculas: o filtro compara o tipo sem normalizar o do registro.
  { id: 8, company_id: 901, company_name: 'Empresa QA', name: 'FPSO Sul', unit_type: 'FPSO', city: 'Macaé' }
];

function makeEnv(opts = {}) {
  const log = [];
  // Como num <select> real, reescrever as opções (innerHTML) limpa o valor escolhido.
  const node = (id, extra = {}) => ({
    id, value: '', _html: '', hidden: false, disabled: false, required: false, checked: false, children: [],
    get innerHTML() { return this._html; },
    set innerHTML(html) { this._html = html; this.value = ''; },
    get firstChild() { return this.children[0] || null; },
    insertBefore(child, ref) { log.push(['insertBefore', id, child.text, child.value, ref ? ref.text : null]); this.children.unshift(child); },
    replaceChildren(...kids) { log.push(['replaceChildren', id, kids.map((k) => [k.text, k.value])]); this.children = kids; },
    ...extra
  });
  const form = (id, names) => {
    const elements = Object.fromEntries(names.map((n) => [n, node(`${id}:${n}`)]));
    return { id, elements, reset() { log.push(['reset', id]); for (const el of Object.values(elements)) { el.value = el.defaultValue || ''; } } };
  };
  const nodes = {};
  for (const id of ['unit-legal-entity', 'unit-legal-entity-field', 'unit-company', 'report-legal-entity', 'report-legal-entity-field', 'report-company',
    'legal-entity-company', 'legal-entity-company-field', 'legal-entity-company-hint', 'legal-entity-cancel-edit']) { nodes[id] = node(id); }
  nodes['legal-entity-form'] = form('legal-entity-form', ['id', 'company_id', 'cnpj', 'legal_name', 'trade_name', 'entity_type', 'state_registration',
    'municipal_registration', 'cnae', 'opening_date', 'address', 'municipality', 'uf', 'cep', 'notes', 'active']);
  nodes['legal-entity-form'].elements.active.defaultValue = '1';
  nodes['unit-form'] = form('unit-form', ['id', 'company_id', 'name', 'unit_type', 'city', 'notes', 'legal_entity_id']);
  for (const id of opts.missing || []) { delete nodes[id]; }
  if (opts.noUnitLegalField) { delete nodes['unit-form'].elements.legal_entity_id; }
  if (opts.noCompanyField) { delete nodes['legal-entity-form'].elements.company_id; }
  const refs = {};
  for (const n of ['legalEntitiesTable', 'legalEntitiesFilterSearch', 'legalEntitiesFilterType', 'legalEntitiesShowInactive', 'unitsFilterCompany',
    'unitsFilterName', 'unitsFilterType', 'unitsFilterCity']) { refs[n] = node(n); }
  for (const n of opts.missingRefs || []) { refs[n] = null; }
  const state = {
    user: { id: 9, role: opts.role || 'general_admin', company_id: 901, company_name: opts.companyName ?? 'Empresa QA' },
    companies: [{ id: 901, name: 'Empresa QA', cnpj: '11' }, { id: 902, name: 'Outra', cnpj: '99' }],
    legalEntities: JSON.parse(JSON.stringify(LEGAL_ENTITIES)),
    legalEntitiesFilters: { search: '', type: '', showInactive: false },
    units: JSON.parse(JSON.stringify(UNITS)),
    unitsFilters: { company_id: '', name: '', type: '', city: '' }
  };
  const perms = new Set(opts.perms || ['legal_entities:update', 'legal_entities:delete']);
  const confirms = [...(opts.confirms || [])];
  const ctx = {
    state, refs, __EPI_APP_STATE__: state, __EPI_REFS__: refs,
    document: { getElementById: (id) => nodes[id] || null },
    Option: function Option(text, value) { this.text = text; this.value = value; },
    tr: (key, fallback) => `${key}|${fallback}`,
    escapeHtml: (v) => String(v ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'),
    unitTypeLabel: (t) => `T(${t})`,
    filterByUserCompany: (items) => { log.push(['filterByUserCompany', (items || []).length]); return (items || []).filter((i) => i.company_id === 901); },
    hasPermission: (p) => perms.has(p),
    requirePermission: (p) => { const ok = perms.has(p); log.push(['requirePermission', p, ok]); return ok; },
    actorQuery: () => 'actor_user_id=9',
    populateSelect: (id, items, label) => { log.push(['populateSelect', id, items.map(label)]); nodes[id].innerHTML = items.map(label).join('|'); nodes[id].children = []; },
    setFormSubmitLabel: (id, text) => log.push(['submitLabel', id, text]),
    showView: (v) => log.push(['showView', v]),
    focusRegistrationTab: (v) => log.push(['focusTab', v]),
    renderTables: () => log.push(['renderTables']),
    loadBootstrap: async (o) => { log.push(['loadBootstrap', JSON.stringify(o ?? null)]); if (opts.bootstrapFails) { throw new Error('boot'); } },
    dsTableState: (o) => `EMPTY(${o.colspan},${o.message})`,
    confirm: (m) => { const r = confirms.length ? confirms.shift() : true; log.push(['confirm', m, r]); return r; },
    alert: (m) => log.push(['alert', String(m)]),
    api: async (url, o) => { log.push(['api', url, JSON.stringify(o ?? null)]); await Promise.resolve(); if (opts.apiFails) { throw new Error(opts.apiFails); } return {}; },
    console: { warn: () => {}, error: () => {}, log: () => {} },
    Promise, JSON, Object, Array, Number, String, Set, Map, Error, RegExp, Boolean
  };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  if (!opts.noRules) {
    for (const rel of RULES) { vm.runInContext(fs.readFileSync(path.join(JS_ROOT, rel), 'utf8'), ctx); }
  }
  return { ctx, log, state, refs, nodes };
}

function loadModules(env) {
  for (const rel of MODULES) { vm.runInContext(fs.readFileSync(path.join(JS_ROOT, rel), 'utf8'), env.ctx); }
  return env.ctx;
}

function loadFrozen(env) {
  vm.runInContext(fs.readFileSync(FROZEN_FILE, 'utf8'), env.ctx);
  return env.ctx;
}

function snapshot(env) {
  const pick = (n) => (n ? [n.value, n.innerHTML, n.hidden, n.disabled, n.required, n.children.map((c) => [c.text, c.value])] : null);
  const nodes = {};
  for (const [k, n] of Object.entries(env.nodes)) {
    nodes[k] = n.elements ? Object.fromEntries(Object.entries(n.elements).map(([e, el]) => [e, el.value])) : pick(n);
  }
  return { log: env.log, nodes, refs: Object.fromEntries(Object.entries(env.refs).map(([k, n]) => [k, n ? n.innerHTML : null])),
    filters: [env.state.legalEntitiesFilters, env.state.unitsFilters] };
}

async function run(load, opts, fn) {
  const env = makeEnv(opts);
  const ctx = load(env);
  let result;
  let thrown = null;
  try { result = await fn(ctx, env); } catch (error) { thrown = String(error && error.message); }
  return JSON.parse(JSON.stringify({ thrown, result: result === undefined ? null : result, ...snapshot(env) }));
}

async function scenario(load) {
  const out = {};
  for (const noRules of [false, true]) {
    const tag = noRules ? 'semRegras' : 'regras';
    // Seletores de vínculo jurídico.
    out[`${tag}:helpers`] = await run(load, { noRules }, (ctx) => [
      ctx.legalEntitiesForCompany(901), ctx.legalEntitiesForCompany(901, { activeOnly: false }).map((e) => e.id),
      ctx.legalEntitiesForCompany('', { activeOnly: false }).map((e) => e.id), ctx.legalEntitiesForCompany(902).map((e) => e.id),
      ctx.unitLegalEntityLabel(UNITS[0]), ctx.unitLegalEntityLabel(UNITS[1]), ctx.unitLegalEntityLabel(null),
      ctx.legalEntityOptionsHtml(LEGAL_ENTITIES), ctx.legalEntityOptionsHtml([]),
      Object.keys(ctx.legalEntityHelpers()).sort(), Object.keys(ctx.legalEntitiesViewHelpers()).sort()
    ]);
    for (const [name, prep] of [['empresaDoCampo', (env) => { env.nodes['unit-company'].value = '902'; env.nodes['report-company'].value = '902'; }],
      ['empresaDoUsuario', () => {}],
      ['mantemAnterior', (env) => { env.nodes['unit-legal-entity'].value = '3'; env.nodes['report-legal-entity'].value = '2'; }],
      ['descartaAnterior', (env) => { env.nodes['unit-legal-entity'].value = '4'; env.nodes['report-legal-entity'].value = '77'; }],
      ['semEmpresa', (env) => { env.state.user.company_id = ''; }]]) {
      out[`${tag}:syncOptions:${name}`] = await run(load, { noRules }, (ctx, env) => { prep(env); ctx.syncUnitLegalEntityOptions(); ctx.syncReportLegalEntityOptions(); });
    }
    out[`${tag}:syncOptions:semCampos`] = await run(load, { noRules, missing: ['unit-legal-entity-field', 'report-legal-entity'] },
      (ctx) => { ctx.syncUnitLegalEntityOptions(); ctx.syncReportLegalEntityOptions(); });
    // Tela de CNPJs.
    for (const [name, opts, filters] of [['completo', {}, {}], ['soEditar', { perms: ['legal_entities:update'] }, {}],
      ['soInativar', { perms: ['legal_entities:delete'] }, {}], ['semPermissao', { perms: [] }, {}],
      ['comInativos', {}, { showInactive: true }], ['busca', {}, { search: 'filial', showInactive: true }], ['tipo', {}, { type: 'spe' }]]) {
      out[`${tag}:render:${name}`] = await run(load, { ...opts, noRules }, (ctx, env) => { Object.assign(env.state.legalEntitiesFilters, filters); ctx.renderLegalEntities(); });
    }
    out[`${tag}:render:vazio`] = await run(load, { noRules }, (ctx, env) => { env.state.legalEntities = []; ctx.renderLegalEntities(); });
    out[`${tag}:render:soUmAtivo`] = await run(load, { noRules }, (ctx, env) => { env.state.legalEntities = env.state.legalEntities.slice(0, 2); ctx.renderLegalEntities(); });
    out[`${tag}:render:semTabela`] = await run(load, { noRules, missingRefs: ['legalEntitiesTable'] }, (ctx) => ctx.renderLegalEntities());
    out[`${tag}:filtros`] = await run(load, { noRules }, (ctx, env) => {
      env.refs.legalEntitiesFilterSearch.value = '  Matriz '; env.refs.legalEntitiesFilterType.value = ' matriz '; env.refs.legalEntitiesShowInactive.checked = 1;
      ctx.syncLegalEntitiesFilters();
    });
    out[`${tag}:filtros:semCampos`] = await run(load, { noRules, missingRefs: ['legalEntitiesFilterSearch', 'legalEntitiesFilterType', 'legalEntitiesShowInactive'] },
      (ctx) => ctx.syncLegalEntitiesFilters());
    // Formulário.
    for (const [name, opts] of [['master', { role: 'master_admin' }], ['geral', {}], ['semNome', { companyName: '  ' }],
      ['semHint', { missing: ['legal-entity-company-hint'] }], ['semCampo', { missing: ['legal-entity-company-field'] }]]) {
      out[`${tag}:campoEmpresa:${name}`] = await run(load, { ...opts, noRules }, (ctx, env) => { env.nodes['legal-entity-company'] && (env.nodes['legal-entity-company'].value = '902'); ctx.syncLegalEntityCompanyField(); });
    }
    out[`${tag}:modo`] = await run(load, { noRules }, (ctx, env) => {
      ctx.setLegalEntityFormMode('edit'); const a = env.nodes['legal-entity-cancel-edit'].hidden; ctx.setLegalEntityFormMode('create'); return a;
    });
    out[`${tag}:modo:semBotao`] = await run(load, { noRules, missing: ['legal-entity-cancel-edit'] }, (ctx) => ctx.setLegalEntityFormMode('edit'));
    out[`${tag}:reset`] = await run(load, { noRules }, (ctx, env) => { env.nodes['legal-entity-form'].elements.id.value = '3'; ctx.resetLegalEntityForm(); });
    out[`${tag}:reset:semForm`] = await run(load, { noRules, missing: ['legal-entity-form'] }, (ctx) => ctx.resetLegalEntityForm());
    for (const [name, id, opts] of [['ativo', 1, {}], ['inativo', 2, {}], ['parcial', 3, { role: 'master_admin' }], ['semCampoEmpresa', 1, { noCompanyField: true }],
      ['inexistente', 77, {}], ['semForm', 1, { missing: ['legal-entity-form'] }]]) {
      out[`${tag}:editar:${name}`] = await run(load, { ...opts, noRules }, (ctx) => ctx.startEditLegalEntity(id));
    }
    for (const [name, id, opts] of [['ok', 2, {}], ['cancela', 2, { confirms: [false] }], ['semPermissao', 2, { perms: [] }], ['inexistente', 77, {}],
      ['falhaApi', 2, { apiFails: 'último CNPJ ativo' }], ['falhaBootstrap', 2, { bootstrapFails: true }]]) {
      out[`${tag}:inativar:${name}`] = await run(load, { ...opts, noRules }, (ctx) => ctx.deactivateLegalEntity(id));
    }
    // Unidades.
    out[`${tag}:unidades:busca`] = await run(load, { noRules }, (ctx) => [ctx.unitsForSearchByCompany().map((u) => u.id),
      ctx.unitsForSearchByCompany('901').map((u) => u.id), ctx.unitsForSearchByCompany(902).map((u) => u.id)]);
    out[`${tag}:unidades:sync`] = await run(load, { noRules }, (ctx, env) => {
      env.refs.unitsFilterCompany.value = ' 901 '; env.refs.unitsFilterName.value = ' NORTE '; env.refs.unitsFilterType.value = 'BASE'; env.refs.unitsFilterCity.value = 'Mac';
      ctx.syncUnitsSearchFilters();
    });
    out[`${tag}:unidades:sync:semCampos`] = await run(load, { noRules, missingRefs: ['unitsFilterCompany', 'unitsFilterName', 'unitsFilterType', 'unitsFilterCity'] },
      (ctx) => ctx.syncUnitsSearchFilters());
    const filterSets = [{}, { company_id: '901' }, { company_id: 902 }, { type: 'navio' }, { type: 'NAVIO' }, { name: 'navio' }, { city: 'rio' },
      { name: 'base', city: 'macaé', type: 'base', company_id: '901' }, { type: 'fpso' }, { type: 'FPSO' }];
    out[`${tag}:unidades:filtros`] = await run(load, { noRules }, (ctx, env) => filterSets.map((f) => {
      Object.assign(env.state.unitsFilters, { company_id: '', name: '', type: '', city: '' }, f);
      return ctx.applyUnitsFilters(env.state.units).map((u) => u.id);
    }));
    out[`${tag}:unidades:linhas`] = await run(load, { noRules }, (ctx) => UNITS.flatMap((u) => [ctx.formatUnitTableRow(u, true), ctx.formatUnitTableRow(u, false), ctx.formatUnitOption(u)]));
    for (const [name, id, opts] of [['comCnpj', 5, {}], ['semCnpj', 6, {}], ['semCampoCnpj', 5, { noUnitLegalField: true }], ['inexistente', 77, {}],
      ['semForm', 5, { missing: ['unit-form'] }]]) {
      out[`${tag}:unidades:editar:${name}`] = await run(load, { ...opts, noRules }, (ctx) => ctx.startEditUnit(id));
    }
  }
  return out;
}

module.exports = function ({ testAsync, test, assert, eq }) {
  testAsync('UBX-V5 Unidades e CNPJ: os módulos reproduzem as funções originais do app.js', async () => {
    const expected = await scenario(loadFrozen);
    const actual = await scenario(loadModules);
    assert(Object.keys(expected).length >= 90, 'cenários de caracterização');
    const crashed = Object.keys(expected).filter((k) => expected[k].thrown);
    assert(!crashed.length, `referência quebrou (ambiente incompleto): ${crashed.slice(0, 5).join(', ')}`);
    eq(Object.keys(actual).sort().join(','), Object.keys(expected).sort().join(','), 'mesmos cenários');
    const diverge = Object.keys(expected).filter((k) => JSON.stringify(actual[k]) !== JSON.stringify(expected[k]));
    assert(!diverge.length, `cenários divergentes: ${diverge.slice(0, 8).join(', ')}${diverge.length > 8 ? ` (+${diverge.length - 8})` : ''}`
      + (diverge.length ? `\n  esperado: ${JSON.stringify(expected[diverge[0]]).slice(0, 600)}\n  obtido:   ${JSON.stringify(actual[diverge[0]]).slice(0, 600)}` : ''));
  });

  test('UBX-V5 Unidades e CNPJ: contrato dos módulos (globais, namespaces congelados, carga antes do app.js, nada volta ao monólito)', () => {
    const env = makeEnv();
    const ctx = loadModules(env);
    for (const name of NAMES) { eq(typeof ctx[name], 'function', name); }
    for (const ns of ['__EPI_LEGAL_ENTITIES_API__', '__EPI_LEGAL_ENTITIES_UI__', '__EPI_UNITS_BUSINESS__', '__EPI_UNITS_UI__']) {
      assert(ctx[ns] && Object.isFrozen(ctx[ns]), `${ns} publicado e congelado`);
    }
    const scripts = fs.readFileSync(path.resolve(JS_ROOT, '..', 'views', '_scripts.html'), 'utf8');
    const order = [...scripts.matchAll(/<script[^>]+src="([^"?]+)/g)].map((m) => m[1]);
    const idx = MODULES.map((m) => order.indexOf(`/js/${m}`));
    assert(idx.every((i) => i >= 0), 'módulos registrados em _scripts.html');
    assert(idx[0] < idx[1] && idx[2] < idx[3], 'integração/negócio antes da UI');
    assert(Math.max(...idx) < order.indexOf('/app.js'), 'antes do app.js');
    const app = fs.readFileSync(path.resolve(JS_ROOT, '..', 'app.js'), 'utf8');
    for (const name of NAMES) {
      assert(!new RegExp(`^(?:async\\s+)?function\\s+${name}\\(`, 'm').test(app), `${name} voltou ao app.js`);
    }
  });
};

module.exports.scenario = scenario;
module.exports.loadFrozen = loadFrozen;
module.exports.loadModules = loadModules;
