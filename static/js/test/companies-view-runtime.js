'use strict';
// UBX-V5, Etapa 2 (Empresas) — caracterização de modules/companies.
//
// Os MESMOS cenários rodam contra os módulos e contra as funções ORIGINAIS do
// app.js (fixtures/app-before-ubx-v5-companies.js.txt, main a2358206), no mesmo
// ambiente, e os resultados têm de ser idênticos. Cada cenário registra
// chamadas (API com método/corpo, prompt, alert, console.error, loadBootstrap,
// listeners, clique no seletor de arquivo, scroll), o formulário, o estado
// (empresa em edição/selecionada) e o HTML do resumo, dos detalhes e da tabela.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const JS_ROOT = path.resolve(__dirname, '..');
const FROZEN_FILE = path.join(__dirname, 'fixtures', 'app-before-ubx-v5-companies.js.txt');
const MODULES = ['modules/companies/business/company-rules.js', 'modules/companies/integrations/companies-api.js',
  'modules/companies/ui/companies-view.js'];
const NAMES = ['getCompanyFormField', 'setCompanyFieldValue', 'readCompanyFieldValue', 'renderCompaniesSummary', 'companyStatusBadges',
  'companyUsageText', 'renderCompanyDetails', 'companyRowActions', 'formatCompanyRow', 'renderCompanies', 'resetCompanyForm',
  'startEditCompany', 'openCompanyLogoEditor', 'saveCompany', 'toggleCompany'];

const COMPANIES = [
  { id: 901, name: 'Empresa <QA>', legal_name: 'Empresa QA Ltda', cnpj: '11222333000181', active: 1, license_status: 'active',
    license_status_label: 'Ativa', plan_name: 'pro', user_limit: 50, user_count: 12, available_slots: 38, monthly_value: 1200,
    projected_monthly_value: 1500, unit_price: 25, contract_start: '2026-01-01', contract_end: '2026-12-31', addendum_enabled: 1,
    commercial_notes: 'VIP', logo_type: 'data:image/png;base64,AA', near_limit: false, limit_reached: 0 },
  { id: 902, name: 'Teste', legal_name: '', cnpj: '22', active: 0, license_status: 'trial', plan_name: '', user_limit: 10,
    user_count: 9, available_slots: 1, near_limit: true, limit_reached: 0 },
  { id: 903, name: 'Bloqueada', cnpj: '33', active: '1', license_status: 'suspended', license_status_label: 'Suspensa', user_limit: 5,
    user_count: 5, limit_reached: 1, near_limit: true, monthly_value: 0 },
  { id: 904, name: 'Expirada', cnpj: '44', active: 1, license_status: 'expired', user_limit: null, user_count: null }
];
const FORM_FIELDS = ['id', 'name', 'legal_name', 'cnpj', 'active', 'general_admin_email', 'general_admin_name'];

function makeEnv(opts = {}) {
  const log = [];
  const node = (id) => ({ id, value: '', innerHTML: '' });
  const elements = {};
  for (const name of FORM_FIELDS) { if (!(opts.missingFields || []).includes(name)) { elements[name] = node(`company-form:${name}`); } }
  const companyForm = {
    elements: { namedItem: (name) => elements[name] || null },
    reset() { log.push(['reset']); for (const el of Object.values(elements)) { el.value = ''; } },
    scrollIntoView(o) { log.push(['scrollIntoView', JSON.stringify(o)]); }
  };
  const refs = { companiesSummary: node('summary'), companyDetails: node('details'), companiesTable: node('table'), companyForm };
  for (const n of opts.missingRefs || []) { refs[n] = null; }
  const state = {
    user: opts.noUser ? null : { id: 7, role: opts.role || 'master_admin', company_id: 901 },
    companies: JSON.parse(JSON.stringify(opts.companies || COMPANIES)),
    selectedCompanyId: opts.selectedCompanyId ?? null,
    editingCompanyId: opts.editingCompanyId ?? null
  };
  const perms = new Set(opts.perms || ['companies:create', 'companies:update']);
  const prompts = [...(opts.prompts || [])];
  const listeners = [];
  const ctx = {
    state, refs, __EPI_APP_STATE__: state, __EPI_REFS__: refs,
    tr: (key, fallback) => `${key}|${fallback}`,
    renderBadge: (type, value, label) => `[${type}:${value}:${label}]`,
    formatDate: (v) => `D(${v})`,
    planLabel: (p) => (p ? `P(${p})` : ''),
    canAccessCommercialArea: () => opts.commercial !== false,
    companyLogoMarkup: (c, cls) => `<img class="${cls}" data-logo="${c?.logo_type || ''}">`,
    formatCompanyCurrency: (v) => `R$${v || 0}`,
    formatCompanyAvailabilityText: (c) => `AV(${c.available_slots || 0},${c.limit_reached})`,
    formatCnpj: (v) => `CNPJ(${v})`,
    fileToJpegDataUrl: async (file) => { log.push(['fileToJpeg', file.type]); return `data:${file.type};x`; },
    bindAppListener: (target, event, handler) => { log.push(['listen', event]); listeners.push(handler); },
    loadBootstrap: async (o) => { log.push(['loadBootstrap', JSON.stringify(o ?? null)]); },
    hasPermission: (p) => perms.has(p),
    requirePermission: (p) => { const ok = perms.has(p); log.push(['requirePermission', p, ok]); return ok; },
    filterByUserCompany: (items) => { log.push(['filterByUserCompany', (items || []).length]); return (items || []).filter((c) => opts.visible === undefined || opts.visible.includes(c.id)); },
    dsTableState: (o) => `EMPTY(${o.colspan},${o.message})`,
    alert: (m) => log.push(['alert', String(m)]),
    console: { error: (m) => log.push(['console.error', m]), warn: () => {}, log: () => {} },
    document: { createElement: (tag) => { const input = { tag, files: opts.files || null, click: () => log.push(['click', input.type, input.accept]) }; return input; } },
    api: async (url, o) => { log.push(['api', url, JSON.stringify(o ?? null)]); await Promise.resolve(); if (opts.apiFails) { throw new Error(opts.apiFails); } return {}; },
    Promise, JSON, Object, Array, Number, String, Set, Map, Error, RegExp, Boolean
  };
  ctx.window = { prompt: (m) => { const r = prompts.length ? prompts.shift() : null; log.push(['prompt', m, r]); return r; } };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  return { ctx, log, state, refs, elements, listeners };
}

function loadModules(env) {
  for (const rel of MODULES) { vm.runInContext(fs.readFileSync(path.join(JS_ROOT, rel), 'utf8'), env.ctx); }
  return env.ctx;
}

function loadFrozen(env) {
  vm.runInContext(fs.readFileSync(FROZEN_FILE, 'utf8'), env.ctx);
  return env.ctx;
}

async function run(load, opts, fn) {
  const env = makeEnv(opts);
  const ctx = load(env);
  let result;
  let thrown = null;
  try { result = await fn(ctx, env); } catch (error) { thrown = String(error && error.message); }
  return JSON.parse(JSON.stringify({ thrown, result: result === undefined ? null : result, log: env.log,
    form: Object.fromEntries(Object.entries(env.elements).map(([k, el]) => [k, el.value])),
    html: Object.fromEntries(['companiesSummary', 'companyDetails', 'companiesTable'].map((k) => [k, env.refs[k] ? env.refs[k].innerHTML : null])),
    state: [env.state.selectedCompanyId, env.state.editingCompanyId] }));
}

const submitEvent = (log) => ({ preventDefault: () => log.push(['preventDefault']) });

async function scenario(load) {
  const out = {};
  // Resumo, lista e detalhes.
  for (const [name, opts] of [['master', {}], ['soCriar', { perms: ['companies:create'] }], ['semGestao', { perms: [] }],
    ['semComercial', { commercial: false }], ['umaVisivel', { visible: [902] }], ['nenhumaVisivel', { visible: [] }],
    ['selecionada', { selectedCompanyId: 903 }], ['selecionadaInvisivel', { selectedCompanyId: 903, visible: [901, 902] }]]) {
    out[`render:${name}`] = await run(load, opts, (ctx) => { ctx.renderCompaniesSummary(); ctx.renderCompanies(); ctx.renderCompanyDetails(); });
  }
  out['render:detalhesPorId'] = await run(load, {}, (ctx) => { ctx.renderCompanyDetails(904); ctx.renderCompanyDetails('902'); });
  out['render:semElementos'] = await run(load, { missingRefs: ['companiesSummary', 'companyDetails', 'companiesTable'] },
    (ctx) => { ctx.renderCompaniesSummary(); ctx.renderCompanies(); ctx.renderCompanyDetails(); });
  out['puros'] = await run(load, {}, (ctx) => [
    ...COMPANIES.flatMap((c) => [ctx.companyStatusBadges(c), ctx.companyUsageText(c), ctx.companyRowActions(c, true), ctx.companyRowActions(c, false),
      ctx.formatCompanyRow(c, String(c.id)), ctx.formatCompanyRow(c, '0')]),
    ctx.companyStatusBadges({ active: 1, license_status: 'cancelled' })
  ]);
  // Campos do formulário.
  out['campos'] = await run(load, {}, (ctx) => {
    ctx.setCompanyFieldValue('name', 'X'); ctx.setCompanyFieldValue('cnpj'); ctx.setCompanyFieldValue('legal_name', null);
    return [ctx.readCompanyFieldValue('name'), ctx.readCompanyFieldValue('cnpj', 'fb'), ctx.getCompanyFormField('id') !== null];
  });
  out['campos:ausentes'] = await run(load, { missingFields: ['name', 'general_admin_email'] }, (ctx) => {
    ctx.setCompanyFieldValue('name', 'X'); ctx.setCompanyFieldValue('general_admin_email', 'a@b', { optional: true });
    return [ctx.readCompanyFieldValue('name', 'fb'), ctx.readCompanyFieldValue('general_admin_email', 'fb2', { optional: true }), ctx.getCompanyFormField('name')];
  });
  out['campos:semForm'] = await run(load, { missingRefs: ['companyForm'] }, (ctx) => [ctx.readCompanyFieldValue('name', 'fb'), ctx.getCompanyFormField('id')]);
  // Reset e edição.
  out['reset'] = await run(load, { editingCompanyId: 902 }, (ctx, env) => { env.elements.name.value = 'sujo'; ctx.resetCompanyForm(); });
  out['reset:semOpcionais'] = await run(load, { missingFields: ['general_admin_email', 'general_admin_name'] }, (ctx) => ctx.resetCompanyForm());
  out['reset:semForm'] = await run(load, { missingRefs: ['companyForm'] }, (ctx) => ctx.resetCompanyForm());
  for (const [name, id, opts] of [['ok', 901, {}], ['inativa', 902, {}], ['ativaTexto', 903, {}], ['semPermissao', 901, { perms: ['companies:create'] }],
    ['inexistente', 77, {}], ['semForm', 901, { missingRefs: ['companyForm'] }]]) {
    out[`editar:${name}`] = await run(load, opts, (ctx) => ctx.startEditCompany(id));
  }
  // Gravação.
  const fill = (env, values) => { for (const [k, v] of Object.entries(values)) { env.elements[k].value = v; } };
  for (const [name, opts, values] of [
    ['criar', {}, { name: 'Nova', legal_name: 'Nova Ltda', cnpj: '55', active: '1', general_admin_email: ' adm@x.test ', general_admin_name: ' Adm ' }],
    ['criarSemOpcionais', { missingFields: ['general_admin_email', 'general_admin_name'] }, { name: 'Nova', legal_name: '', cnpj: '55', active: '0' }],
    ['editar', { editingCompanyId: 901 }, { name: 'Renomeada', legal_name: 'L', cnpj: '11', active: '1', general_admin_email: 'nao@vai' }],
    ['editarIncompleta', { editingCompanyId: 904 }, { name: '', legal_name: '', cnpj: '', active: '' }],
    ['editarSemCampos', { editingCompanyId: 902, missingFields: ['name', 'cnpj'] }, { legal_name: 'X', active: '1' }],
    ['semPermissaoCriar', { perms: ['companies:update'] }, { name: 'N' }],
    ['semPermissaoEditar', { perms: ['companies:create'], editingCompanyId: 901 }, { name: 'N' }],
    ['falhaApi', { apiFails: 'CNPJ duplicado' }, { name: 'N', cnpj: '1', active: '1', general_admin_email: '', general_admin_name: '' }],
    ['semUsuario', { noUser: true, perms: ['companies:create'] }, { name: 'N' }],
    // Sem sessão E com campos ausentes: o ator é lido antes do formulário (sem console.error).
    ['semUsuarioSemCampos', { noUser: true, perms: ['companies:create'], missingFields: ['name', 'cnpj'] }, {}],
    // Empresa inativa sem o campo de status: o padrão vem de `active ?? 1` (0 é mantido).
    ['editarInativaSemStatus', { editingCompanyId: 902, missingFields: ['active'] }, { name: 'N', legal_name: '', cnpj: '2' }]]) {
    out[`salvar:${name}`] = await run(load, opts, (ctx, env) => { fill(env, values); return ctx.saveCompany(submitEvent(env.log)); });
  }
  // Ativar/inativar.
  for (const [name, id, active, opts] of [['inativar', 901, 0, {}], ['ativar', 902, 1, {}], ['parcial', 904, 1, {}], ['semPermissao', 901, 0, { perms: ['companies:create'] }],
    ['inexistente', 77, 1, {}], ['falhaApi', 901, 0, { apiFails: 'negado' }], ['semUsuario', 901, 0, { noUser: true }]]) {
    out[`ativacao:${name}`] = await run(load, opts, (ctx) => ctx.toggleCompany(id, active));
  }
  // Logotipo por suporte auditado.
  const fire = async (env) => { for (const handler of env.listeners) { await handler(); } };
  for (const [name, opts] of [
    ['ok', { prompts: ['  justificativa de suporte  '], files: [{ type: 'image/png' }] }],
    ['svg', { prompts: ['justificativa ok!!'], files: [{ type: 'image/svg+xml' }] }],
    ['tipoInvalido', { prompts: ['justificativa ok!!'], files: [{ type: 'image/gif' }] }],
    ['semArquivo', { prompts: ['justificativa ok!!'], files: [] }],
    ['falhaApi', { prompts: ['justificativa ok!!'], files: [{ type: 'image/jpeg' }], apiFails: 'auditoria indisponível' }],
    ['curta', { prompts: ['  curta    '] }], ['cancelada', { prompts: [null] }], ['naoMaster', { role: 'general_admin', prompts: ['justificativa ok!!'] }],
    ['dezExatos', { prompts: ['0123456789'], files: [{ type: 'image/png' }] }],
    // Justificativa vazia (não é cancelamento): cai na regra do mínimo.
    ['vazia', { prompts: [''] }],
    // Vários arquivos: vale o primeiro.
    ['variosArquivos', { prompts: ['justificativa ok!!'], files: [{ type: 'image/gif' }, { type: 'image/png' }] }]]) {
    out[`logo:${name}`] = await run(load, opts, async (ctx, env) => { ctx.openCompanyLogoEditor(901); await fire(env); });
  }
  out['logo:inexistente'] = await run(load, { prompts: ['justificativa ok!!'] }, (ctx) => ctx.openCompanyLogoEditor(77));
  return out;
}

module.exports = function ({ testAsync, test, assert, eq }) {
  testAsync('UBX-V5 Empresas: os módulos reproduzem as funções originais do app.js', async () => {
    const expected = await scenario(loadFrozen);
    const actual = await scenario(loadModules);
    assert(Object.keys(expected).length >= 40, 'cenários de caracterização');
    const crashed = Object.keys(expected).filter((k) => expected[k].thrown);
    assert(!crashed.length, `referência quebrou (ambiente incompleto): ${crashed.slice(0, 5).join(', ')}`);
    eq(Object.keys(actual).sort().join(','), Object.keys(expected).sort().join(','), 'mesmos cenários');
    const diverge = Object.keys(expected).filter((k) => JSON.stringify(actual[k]) !== JSON.stringify(expected[k]));
    assert(!diverge.length, `cenários divergentes: ${diverge.slice(0, 8).join(', ')}${diverge.length > 8 ? ` (+${diverge.length - 8})` : ''}`
      + (diverge.length ? `\n  esperado: ${JSON.stringify(expected[diverge[0]]).slice(0, 600)}\n  obtido:   ${JSON.stringify(actual[diverge[0]]).slice(0, 600)}` : ''));
  });

  test('UBX-V5 Empresas: contrato dos módulos (globais, namespaces congelados, carga antes do app.js, nada volta ao monólito)', () => {
    const env = makeEnv();
    const ctx = loadModules(env);
    for (const name of NAMES) { eq(typeof ctx[name], 'function', name); }
    for (const ns of ['__EPI_COMPANIES_BUSINESS__', '__EPI_COMPANIES_API__', '__EPI_COMPANIES_UI__']) {
      assert(ctx[ns] && Object.isFrozen(ctx[ns]), `${ns} publicado e congelado`);
    }
    const scripts = fs.readFileSync(path.resolve(JS_ROOT, '..', 'views', '_scripts.html'), 'utf8');
    const order = [...scripts.matchAll(/<script[^>]+src="([^"?]+)/g)].map((m) => m[1]);
    const idx = MODULES.map((m) => order.indexOf(`/js/${m}`));
    assert(idx.every((i) => i >= 0), 'módulos registrados em _scripts.html');
    assert(idx[0] < idx[1] && idx[1] < idx[2], 'business → integrations → ui');
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
