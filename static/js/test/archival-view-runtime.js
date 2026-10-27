'use strict';
// UBX-V5, Etapa 1 — caracterização do arquivamento genérico e de Unidades.
//
// Os MESMOS cenários rodam contra os módulos extraídos (modules/archival/*) e
// contra as funções ORIGINAIS do app.js (fixtures/app-before-ubx-v5-archival.js.txt,
// main 63da879f, depois da FIX-NAV-REFRESH-V1), no mesmo ambiente, e os
// resultados têm de ser idênticos. Cada cenário registra, em ordem: chamadas HTTP (método, caminho, corpo), diálogos,
// prompts, alertas, toasts, recargas (bootstrap e listas), o estado final das
// listas/filtros e o HTML das tabelas.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const JS_ROOT = path.resolve(__dirname, '..');
const FROZEN_FILE = path.join(__dirname, 'fixtures', 'app-before-ubx-v5-archival.js.txt');
const MODULES = [
  'modules/shared/ui/mutation-flow.js',
  'modules/archival/business/archival-rules.js',
  'modules/archival/integrations/archival-api.js',
  'modules/archival/ui/archival-view.js',
  'modules/archival/ui/unit-archival-view.js',
  'modules/outsourced/ui/outsourced-employees-view.js'
];
const KINDS = ['employee', 'epi', 'outsourcedCompany', 'outsourcedEmployee'];
const ROLES = ['master_admin', 'general_admin', 'registry_admin', 'admin', 'user', 'viewer'];
const LIST = { employee: 'archivedEmployees', epi: 'archivedEpis', outsourcedCompany: 'archivedOutsourcedCompanies', outsourcedEmployee: 'archivedOutsourcedEmployees' };
const PREFIX = { employee: 'archivedEmployees', epi: 'archivedEpis', outsourcedCompany: 'archivedOutsourcedCompanies', outsourcedEmployee: 'archivedOutsourcedEmployees' };

function sampleArchived() {
  return [
    { id: 61, company_id: 901, company_name: 'Empresa QA', name: 'Ana <b>QA</b>', legal_name: 'Terceira QA', trade_name: 'TQA',
      cnpj: '11222333000181', employee_id_code: 'QA-61', unit_name: 'Base', ca: '12345', archived_at: '2026-10-01T10:00:00',
      archive_reason: 'Encerrado', archived_by_name: 'Maria Silva', retention_days_remaining: 0, legal_hold: 0, status: 'archived' },
    { id: 62, company_id: 901, company_name: 'Empresa QA', name: 'Bruno', legal_name: '', trade_name: 'Só Fantasia',
      archived_at: '2026-09-15T08:00:00', archive_reason: 'Demissão', archived_by_name: 'João', retention_days_remaining: 30,
      legal_hold: 0, status: 'archived' },
    { id: 63, company_id: 901, name: 'Carla', archived_at: '2026-10-02', archive_reason: '', archived_by_name: '',
      retention_days_remaining: -1, legal_hold: 1, status: 'pending_deletion' },
    { id: 64, company_id: 902, company_name: 'Outra', name: 'Daniel', archived_at: '2026-10-03', archive_reason: 'Outro',
      archived_by_name: 'Maria', retention_days_remaining: 0, legal_hold: 0, status: 'archived' }
  ];
}

function makeEnv(opts = {}) {
  const log = [];
  let writeEpoch = 0;
  const table = (name) => ({ name, innerHTML: '' });
  const input = (value) => ({ value });
  const refs = { archivedUnitsTable: table('units'), archivedUnitsFilterCompany: input(''), archivedUnitsFilterDate: input(''),
    archivedUnitsFilterReason: input(''), archivedUnitsFilterUser: input('') };
  for (const kind of KINDS) {
    const p = PREFIX[kind];
    refs[`${p}Table`] = table(kind);
    for (const f of ['Company', 'Date', 'Reason', 'User']) { refs[`${p}Filter${f}`] = input(''); }
  }
  const filters = () => ({ company_id: '', date: '', reason: '', user: '' });
  const state = {
    user: { id: 7, role: opts.role || 'registry_admin', company_id: 901 },
    units: [{ id: 6, name: 'Base Norte' }], employees: [{ id: 61, name: 'Ana Ativa' }], epis: [{ id: 61, name: 'Luva' }],
    outsourcedCompanies: [{ id: 61, name: 'Terceira' }],
    archivedUnits: sampleArchived(), archivedUnitsFilters: filters()
  };
  for (const kind of KINDS) { state[LIST[kind]] = sampleArchived(); state[`${LIST[kind]}Filters`] = filters(); }
  const perms = new Set(opts.perms || ['units:view', 'units:update', 'units:delete', 'employees:view', 'employees:update',
    'employees:delete', 'employees:update_simplified', 'epis:view', 'epis:update', 'epis:delete']);
  const confirms = [...(opts.confirms || [])];
  const prompts = [...(opts.prompts || [])];
  const apiRules = opts.api || [];
  const ctx = {
    state, refs, __EPI_APP_STATE__: state, __EPI_REFS__: refs,
    tr: (key, fallback) => `${key}|${fallback}`,
    formatDate: (value) => `D(${value})`,
    filterByUserCompany: (items) => { log.push(['filterByUserCompany', (items || []).length]); return (items || []).filter((i) => !i.company_id || i.company_id === 901); },
    dsTableState: (o) => `EMPTY(${o.colspan},${o.message})`,
    hasPermission: (p) => String(p).split(/\s+/).some((x) => perms.has(x)),
    requirePermission: (p) => { const ok = String(p).split(/\s+/).some((x) => perms.has(x)); log.push(['requirePermission', p, ok]); return ok; },
    actorQuery: () => 'actor_user_id=7',
    reportNonCriticalError: (msg) => log.push(['reportNonCritical', String(msg)]),
    apiWriteEpoch: () => writeEpoch,
    api: async (url, options) => {
      const method = (options || {}).method || 'GET';
      log.push(['api', method, url, options && options.body, Object.keys(options || {}).join(',')]);
      if (method !== 'GET') { writeEpoch += 1; }
      try {
        await Promise.resolve();
        const rule = apiRules.find(([re, m]) => re.test(url) && (!m || m === method));
        if (rule && rule[2] instanceof Error) { throw rule[2]; }
        if (rule) { return typeof rule[2] === 'function' ? rule[2]() : rule[2]; }
        if (/\/archived\?/.test(url)) { return { units: [{ id: 99, company_id: 901, name: 'Nova' }], employees: [{ id: 98, company_id: 901, name: 'Novo' }], epis: [], outsourced_companies: [] }; }
        if (/purge-request$/.test(url)) { return { records: { deliveries: 3, feedbacks: 1, unit_links: 2 } }; }
        return { ok: true };
      } finally {
        if (method !== 'GET') { writeEpoch += 1; }
      }
    },
    loadBootstrap: async (o) => { log.push(['loadBootstrap', JSON.stringify(o || null)]); if (opts.bootstrapFails) { throw new Error('boot fail'); } },
    loadOutsourcedCompanies: async () => { log.push(['loadOutsourcedCompanies']); },
    loadBlockedStock: () => log.push(['loadBlockedStock']),
    confirmDestructive: async (o) => { log.push(['confirm', JSON.stringify(o)]); return confirms.length ? confirms.shift() : true; },
    prompt: (message, def) => { log.push(['prompt', message, def]); return prompts.length ? prompts.shift() : 'motivo QA'; },
    alert: (message) => log.push(['alert', String(message)]),
    showToast: (message, type) => log.push(['toast', type, String(message)]),
    console: { warn: () => {}, error: () => {}, log: () => {} },
    Promise, JSON, Object, Array, Number, String, Set, Map, Error, RegExp, Math
  };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  return { ctx, log, state, refs };
}

function loadModules(env) {
  for (const rel of MODULES) { vm.runInContext(fs.readFileSync(path.join(JS_ROOT, rel), 'utf8'), env.ctx); }
  return env.ctx;
}

// Referência: o mesmo fluxo e o mesmo módulo de Terceirizados (renderOutsourcedEmployees),
// com as funções originais por cima.
function loadFrozen(env) {
  for (const rel of [MODULES[0], MODULES[5]]) { vm.runInContext(fs.readFileSync(path.join(JS_ROOT, rel), 'utf8'), env.ctx); }
  vm.runInContext(fs.readFileSync(FROZEN_FILE, 'utf8'), env.ctx);
  return env.ctx;
}

function snapshot(env) {
  const tables = {};
  for (const [k, v] of Object.entries(env.refs)) { if (k.endsWith('Table')) { tables[k] = v ? v.innerHTML : null; } }
  const lists = {};
  for (const k of ['archivedUnits', ...KINDS.map((x) => LIST[x])]) { lists[k] = (env.state[k] || []).map((i) => i.id); }
  const filters = {};
  for (const k of ['archivedUnitsFilters', ...KINDS.map((x) => `${LIST[x]}Filters`)]) { filters[k] = env.state[k]; }
  return { log: env.log, tables, lists, filters };
}

async function run(load, opts, fn) {
  const env = makeEnv(opts);
  const ctx = load(env);
  // Chaves de execução única e de leitura coalescida também fazem parte do contrato.
  const { runExclusiveMutation, coalesceLoad } = ctx;
  ctx.runExclusiveMutation = (key, task) => { env.log.push(['mutex', key]); return runExclusiveMutation(key, task); };
  ctx.coalesceLoad = (key, load) => { env.log.push(['coalesce', key]); return coalesceLoad(key, load); };
  let thrown = null;
  try { await fn(ctx, env); } catch (error) { thrown = String(error && error.message); }
  return JSON.parse(JSON.stringify({ thrown, ...snapshot(env) }));
}

async function scenario(load) {
  const out = {};
  const unitFilterSets = [{}, { company_id: '901' }, { date: '2026-10' }, { reason: 'encer' }, { user: 'maria' }];
  // Render: papéis × filtros (genérico e Unidades).
  for (const role of ROLES) {
    for (const [i, f] of unitFilterSets.entries()) {
      out[`render:${role}:${i}`] = await run(load, { role }, (ctx, env) => {
        for (const kind of KINDS) { Object.assign(env.state[`${LIST[kind]}Filters`], f); ctx.renderArchivedRecords(kind); }
        Object.assign(env.state.archivedUnitsFilters, f); ctx.renderArchivedUnits();
      });
    }
  }
  out['render:vazio'] = await run(load, {}, (ctx, env) => {
    for (const kind of KINDS) { env.state[LIST[kind]] = []; ctx.renderArchivedRecords(kind); }
    env.state.archivedUnits = []; ctx.renderArchivedUnits();
  });
  out['render:semTabela'] = await run(load, {}, (ctx, env) => {
    for (const k of Object.keys(env.refs)) { if (k.endsWith('Table')) { env.refs[k] = null; } }
    for (const kind of KINDS) { ctx.renderArchivedRecords(kind); }
    ctx.renderArchivedUnits();
  });
  // Filtros a partir dos campos.
  out['sync'] = await run(load, {}, (ctx, env) => {
    for (const kind of KINDS) {
      const p = PREFIX[kind];
      env.refs[`${p}FilterCompany`].value = ' 901 '; env.refs[`${p}FilterDate`].value = '2026-10';
      env.refs[`${p}FilterReason`].value = ' ENCER '; env.refs[`${p}FilterUser`].value = 'MARIA ';
      ctx.syncArchivedRecordsFilters(kind);
    }
    env.refs.archivedUnitsFilterCompany.value = '901'; env.refs.archivedUnitsFilterDate.value = ' 2026-09 ';
    env.refs.archivedUnitsFilterReason.value = 'DEM'; env.refs.archivedUnitsFilterUser.value = ' João ';
    ctx.syncArchivedUnitsFilters();
  });
  // Carga das listas.
  for (const [name, opts] of [['ok', {}], ['semPermissao', { perms: [] }], ['falha', { api: [[/archived\?/, null, new Error('falhou')]] }],
    ['simplificado', { perms: ['employees:update_simplified', 'employees:view_simplified'] }],
    // Só a 1ª ocorrência de ':update' vira ':view' (comportamento herdado):
    // 'employees:view_simplified' sozinho NÃO libera a lista de terceirizados.
    ['soLeituraSimplificada', { perms: ['employees:view_simplified'] }]]) {
    out[`load:${name}`] = await run(load, opts, async (ctx) => {
      for (const kind of KINDS) { await ctx.loadArchivedRecords(kind); }
      await ctx.loadArchivedUnits();
      await ctx.loadArchivedRecords('desconhecido');
    });
  }
  // Arquivar (genérico).
  const archiveCases = [
    ['ok', {}], ['cancela', { confirms: [false] }], ['semMotivo', { prompts: [''] }], ['promptNulo', { prompts: [null] }],
    ['falhaApi', { api: [[/\/archive$/, 'POST', new Error('recusado')]] }], ['falhaApiSemMsg', { api: [[/\/archive$/, 'POST', new Error('')]] }],
    ['falhaBootstrap', { bootstrapFails: true }], ['semPermissao', { perms: [] }],
    ['preflightFalha', { api: [[/archival-state/, 'GET', new Error('pf')]] }],
    ['preflightVinculos', { api: [[/archival-state/, 'GET', { archival_state: { has_open_links: true, available: 2, in_transit: 1, in_possession: 3, blocked: 0, pending_requests: 1, pending_purchase: 0, blockable: 2 } }],
      [/\/archive$/, 'POST', { blocked_stock_items: 2 }]] }],
    ['preflightSemBloqueavel', { api: [[/archival-state/, 'GET', { archival_state: { has_open_links: true, available: 0, in_transit: 0, in_possession: 1, blocked: 0, pending_requests: 0, pending_purchase: 1, blockable: 0 } }],
      [/\/archive$/, 'POST', { blocked_stock_items: 0 }]] }],
    ['preflightVinculosSemMotivo', { prompts: ['  '], api: [[/archival-state/, 'GET', { archival_state: { has_open_links: true, blockable: 1 } }]] }],
    ['preflightVinculosCancela', { confirms: [false], api: [[/archival-state/, 'GET', { archival_state: { has_open_links: true, blockable: 1 } }]] }]
  ];
  for (const kind of [...KINDS, 'desconhecido']) {
    for (const [name, opts] of archiveCases) {
      if (name.startsWith('preflight') && kind !== 'epi') { continue; }
      out[`archive:${kind}:${name}`] = await run(load, opts, (ctx) => ctx.archiveEntityRecord(kind, 61));
    }
    out[`archive:${kind}:registroAusente`] = await run(load, {}, (ctx) => ctx.archiveEntityRecord(kind, 777));
    out[`archive:${kind}:duplo`] = await run(load, {}, (ctx) => Promise.all([ctx.archiveEntityRecord(kind, 61), ctx.archiveEntityRecord(kind, 61)]));
  }
  out['archive:outsourcedEmployee:atalho'] = await run(load, {}, (ctx) => ctx.archiveOutsourcedEmployee(61));
  // Desarquivar (genérico).
  const restoreCases = [['ok', {}], ['cancela', { confirms: [false] }], ['falhaApi', { api: [[/\/restore$/, 'POST', new Error('recusado')]] }],
    ['falhaBootstrap', { bootstrapFails: true }], ['semPermissao', { perms: [] }]];
  for (const kind of [...KINDS, 'desconhecido']) {
    for (const [name, opts] of restoreCases) {
      out[`restore:${kind}:${name}`] = await run(load, opts, (ctx) => ctx.restoreArchivedRecord(kind, 61));
    }
    out[`restore:${kind}:duplo`] = await run(load, {}, (ctx) => Promise.all([ctx.restoreArchivedRecord(kind, 61), ctx.restoreArchivedRecord(kind, 61)]));
  }
  // Excluir definitivamente (genérico).
  const purgeCases = [['ok', {}], ['cancelaResumo', { confirms: [false] }], ['semJustificativa', { prompts: ['', 'Ana'] }],
    ['semNome', { prompts: ['justificativa longa', ''] }], ['promptsNulos', { prompts: [null, null] }],
    ['falhaRequest', { api: [[/purge-request$/, 'POST', new Error('negado')]] }],
    ['falhaConfirm', { prompts: ['justificativa longa', 'Ana'], api: [[/purge-confirm$/, 'POST', new Error('nome não confere')]] }],
    ['falhaBootstrap', { bootstrapFails: true, prompts: ['justificativa longa', 'Ana'] }], ['semPermissao', { perms: [] }]];
  for (const kind of [...KINDS, 'desconhecido']) {
    for (const [name, opts] of purgeCases) {
      out[`purge:${kind}:${name}`] = await run(load, opts, (ctx) => ctx.purgeArchivedRecord(kind, 61));
    }
    out[`purge:${kind}:nomeFantasia`] = await run(load, { prompts: ['justificativa longa', 'Só Fantasia'] }, (ctx) => ctx.purgeArchivedRecord(kind, 62));
    out[`purge:${kind}:registroAusente`] = await run(load, {}, (ctx) => ctx.purgeArchivedRecord(kind, 777));
    out[`purge:${kind}:duplo`] = await run(load, { prompts: ['j longa', 'Ana', 'j longa', 'Ana'] }, (ctx) => Promise.all([ctx.purgeArchivedRecord(kind, 61), ctx.purgeArchivedRecord(kind, 61)]));
  }
  // Unidades.
  for (const [name, opts] of [['ok', {}], ['cancela', { confirms: [false] }], ['promptNulo', { prompts: [null] }],
    ['falhaApi', { api: [[/\/archive$/, 'POST', new Error('recusado')]] }], ['falhaBootstrap', { bootstrapFails: true }], ['semPermissao', { perms: [] }]]) {
    out[`unit:archive:${name}`] = await run(load, opts, (ctx) => ctx.archiveUnit(6));
  }
  out['unit:archive:inexistente'] = await run(load, {}, (ctx) => ctx.archiveUnit(777));
  out['unit:archive:duplo'] = await run(load, {}, (ctx) => Promise.all([ctx.archiveUnit(6), ctx.archiveUnit(6)]));
  for (const [name, opts] of restoreCases) {
    out[`unit:restore:${name}`] = await run(load, opts, (ctx) => ctx.restoreArchivedUnit(61));
  }
  out['unit:restore:duplo'] = await run(load, {}, (ctx) => Promise.all([ctx.restoreArchivedUnit(61), ctx.restoreArchivedUnit(61)]));
  for (const [name, opts] of purgeCases) {
    out[`unit:purge:${name}`] = await run(load, opts, (ctx) => ctx.purgeArchivedUnit(61));
  }
  // Sessão sem usuário no meio da exclusão: o erro fica dentro do try (alerta + recarga da lista).
  for (const kind of KINDS) {
    out[`purge:${kind}:semUsuario`] = await run(load, {}, (ctx, env) => { env.state.user = null; return ctx.purgeArchivedRecord(kind, 61); });
  }
  out['unit:purge:semUsuario'] = await run(load, {}, (ctx, env) => { env.state.user = null; return ctx.purgeArchivedUnit(61); });
  out['unit:purge:registroAusente'] = await run(load, {}, (ctx) => ctx.purgeArchivedUnit(777));
  out['unit:purge:duplo'] = await run(load, { prompts: ['j longa', 'Ana', 'j longa', 'Ana'] }, (ctx) => Promise.all([ctx.purgeArchivedUnit(61), ctx.purgeArchivedUnit(61)]));
  return out;
}

module.exports = function ({ testAsync, test, assert, eq }) {
  testAsync('UBX-V5 Arquivamento: os módulos reproduzem as funções originais do app.js', async () => {
    const expected = await scenario(loadFrozen);
    const actual = await scenario(loadModules);
    assert(Object.keys(expected).length >= 200, 'cenários de caracterização');
    const crashed = Object.keys(expected).filter((k) => expected[k].thrown);
    assert(!crashed.length, `referência quebrou (ambiente incompleto): ${crashed.slice(0, 5).join(', ')}`);
    eq(Object.keys(actual).sort().join(','), Object.keys(expected).sort().join(','), 'mesmos cenários');
    const diverge = Object.keys(expected).filter((k) => JSON.stringify(actual[k]) !== JSON.stringify(expected[k]));
    assert(!diverge.length, `cenários divergentes: ${diverge.slice(0, 8).join(', ')}${diverge.length > 8 ? ` (+${diverge.length - 8})` : ''}`
      + (diverge.length ? `\n  esperado: ${JSON.stringify(expected[diverge[0]]).slice(0, 600)}\n  obtido:   ${JSON.stringify(actual[diverge[0]]).slice(0, 600)}` : ''));
  });

  test('UBX-V5 Arquivamento: contrato dos módulos (namespaces congelados, carga antes do app.js, nada volta ao monólito)', () => {
    const env = makeEnv();
    const ctx = loadModules(env);
    for (const ns of ['__EPI_ARCHIVAL_RULES__', '__EPI_ARCHIVAL_API__', '__EPI_ARCHIVAL_UI__', '__EPI_UNIT_ARCHIVAL_UI__']) {
      assert(ctx[ns] && Object.isFrozen(ctx[ns]), `${ns} publicado e congelado`);
    }
    const scripts = fs.readFileSync(path.resolve(JS_ROOT, '..', 'views', '_scripts.html'), 'utf8');
    const order = [...scripts.matchAll(/<script[^>]+src="([^"?]+)/g)].map((m) => m[1]);
    const idx = MODULES.slice(1, 5).map((m) => order.indexOf(`/js/${m}`));
    assert(idx.every((i) => i >= 0), 'módulos registrados em _scripts.html');
    assert(idx[0] < idx[1] && idx[1] < idx[2] && idx[1] < idx[3], 'business → integrations → ui');
    assert(Math.max(...idx) < order.indexOf('/app.js'), 'antes do app.js');
    assert(order.indexOf('/js/modules/shared/ui/mutation-flow.js') < idx[2], 'mutation-flow antes da UI');
    const app = fs.readFileSync(path.resolve(JS_ROOT, '..', 'app.js'), 'utf8');
    for (const name of ['ARCHIVAL_ENTITIES', 'UNIT_PURGE_RECORD_LABELS', 'archiveUnit', 'loadArchivedUnits', 'applyArchivedUnitsFilters',
      'formatArchivedUnitRow', 'renderArchivedUnits', 'syncArchivedUnitsFilters', 'restoreArchivedUnit', 'purgeArchivedUnit',
      '_epiArchivalPreflight', 'archiveEntityRecord', 'loadArchivedRecords', 'formatArchivedRecordRow', 'renderArchivedRecords',
      'syncArchivedRecordsFilters', 'restoreArchivedRecord', 'purgeArchivedRecord', 'archiveOutsourcedEmployee', 'deleteRegistryEntity']) {
      assert(!new RegExp(`^(?:async\\s+)?(?:function|const|let|var)\\s+${name}\\b`, 'm').test(app), `${name} voltou ao app.js`);
    }
  });
};

module.exports.scenario = scenario;
module.exports.makeEnv = makeEnv;
module.exports.loadFrozen = loadFrozen;
