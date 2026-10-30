'use strict';
// UBX-V5, Etapa 2 (Minha Empresa) — caracterização de modules/my-company.
//
// Os MESMOS cenários rodam contra os módulos e contra as funções ORIGINAIS do
// app.js (fixtures/app-before-ubx-v5-my-company.js.txt, main c1c9ac6f), no mesmo
// ambiente, e os resultados têm de ser idênticos. Cada cenário registra chamadas
// (API com método/corpo, alert, confirm, console.warn, loadBootstrap,
// renderMyCompanyDomains, listeners com o nome do handler, conversões de imagem),
// o instante em que a função devolve ('resolved'), os campos do
// formulário, as prévias, os textos de retorno e state.myCompany.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const JS_ROOT = path.resolve(__dirname, '..');
const FROZEN_FILE = path.join(__dirname, 'fixtures', 'app-before-ubx-v5-my-company.js.txt');
const MODULES = ['modules/my-company/business/my-company-rules.js', 'modules/my-company/integrations/my-company-api.js',
  'modules/my-company/ui/my-company-view.js'];
const NAMES = ['myCompanyThemeMode', 'fillMyCompanyFields', 'renderMyCompanyImagePreview', 'collectMyCompanyFields',
  'wireMyCompanyImageInputs', 'loadMyCompany', 'renderMyCompanyReadonly', 'loadMyCompanyCard', 'saveMyCompany',
  'loadMyCompanyDomains', 'domainStatusLabel', 'addMyCompanyDomain', 'handleMyCompanyDomainAction'];

const COMPANY = { id: 901, display_name: '  Empresa QA ', primary_color: '#abc', secondary_color: 'azul', accent_color: '',
  theme_json: '{"mode":"dark"}', logo_type: 'data:image/png;x', favicon_type: '', login_logo_type: null, support_email: 'a@b',
  plan_name: 'pro', user_limit: 50, license_status: 'active' };
const FIELDS = [['display_name', 'text'], ['support_email', 'email'], ['primary_color', 'color'], ['secondary_color', 'color'],
  ['accent_color', 'color'], ['theme_mode', 'select'], ['logo_type', 'hidden'], ['favicon_type', 'hidden'], ['login_logo_type', 'hidden']];
const IMAGES = ['logo_type', 'favicon_type', 'login_logo_type', 'banner_type'];

function makeEnv(opts = {}) {
  const log = [];
  const handlers = [];
  const fields = FIELDS.filter(([n]) => !(opts.missingFields || []).includes(n))
    .map(([name, type]) => ({ type, value: '', dataset: { mcField: name } }));
  const previews = ['logo_type', 'favicon_type', 'login_logo_type'].map((name) => ({ dataset: { mcPreview: name }, innerHTML: '' }));
  const images = IMAGES.map((name) => ({ dataset: { mcImage: name }, files: null, value: 'C:\\fake' }));
  const form = {
    dataset: {},
    querySelectorAll: (sel) => ({ '[data-mc-field]': fields, '[data-mc-preview]': previews, '[data-mc-image]': images }[sel] || []),
    querySelector: (sel) => {
      const m = /^\[data-mc-(field|preview)="([^"]*)"\]$/.exec(sel);
      if (!m) { return null; }
      return (m[1] === 'field' ? fields.find((f) => f.dataset.mcField === m[2]) : previews.find((p) => p.dataset.mcPreview === m[2])) || null;
    }
  };
  const node = (id) => ({ id, value: '', textContent: '', innerHTML: '' });
  const nodes = { 'my-company-form': form, 'my-company-readonly': node('readonly'), 'my-company-feedback': node('feedback'),
    'my-company-domain-feedback': node('domainFeedback'), 'my-company-domain-input': node('domainInput'),
    'my-company-domain-type': node('domainType'), 'my-company-domains-table': node('domainsTable'), 'my-company-domain-add': node('domainAdd') };
  for (const id of opts.missing || []) { delete nodes[id]; }
  const state = { user: opts.noUser ? null : { id: 7, role: 'general_admin' }, myCompany: opts.cached ? { id: 1, cached: true } : null };
  const replies = opts.replies || {};
  const confirms = [...(opts.confirms || [])];
  const ctx = {
    state, __EPI_APP_STATE__: state,
    document: { getElementById: (id) => nodes[id] || null },
    canConfigureMyCompany: () => opts.canConfigure !== false,
    actorQuery: () => 'actor_user_id=7',
    normalizeHexColor: (v, fb) => (/^#[0-9a-f]{3,6}$/i.test(String(v || '')) ? String(v) : fb),
    companyLogoMarkup: (c, cls) => `<img class="${cls}" data-logo="${c.logo_type}" alt="${c.name}">`,
    fileToJpegDataUrl: async (f) => { log.push(['jpeg', f.type]); if (opts.convertFails) { throw new Error('falha conv'); } return `jpeg:${f.type}`; },
    fileToDataUrl: async (f) => { log.push(['dataUrl', f.type]); if (opts.convertFails) { throw new Error('falha conv'); } return `data:${f.type}`; },
    bindAppListener: (target, event, handler) => { log.push(['listen', target ? (target.id || 'form/input') : null, event, handler && handler.name]); handlers.push([target, event, handler]); },
    loadBootstrap: async (o) => { log.push(['loadBootstrap', JSON.stringify(o ?? null)]); if (opts.bootstrapFails) { throw new Error('bootstrap fora do ar'); } },
    renderMyCompanyDomains: (domains) => log.push(['renderDomains', JSON.stringify(domains)]),
    alert: (m) => log.push(['alert', String(m)]),
    confirm: (m) => { const r = confirms.length ? confirms.shift() : true; log.push(['confirm', m, r]); return r; },
    console: { warn: (m, e) => log.push(['console.warn', m, e && e.message]), error: () => {}, log: () => {} },
    api: async (url, o) => {
      log.push(['api', url, JSON.stringify(o ?? null)]);
      await Promise.resolve();
      const key = Object.keys(replies).find((k) => url.startsWith(k));
      const reply = key ? replies[key] : {};
      if (reply instanceof Error) { throw reply; }
      return reply;
    },
    Promise, JSON, Object, Array, Number, String, Set, Map, Error, RegExp, Boolean
  };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  return { ctx, log, state, nodes, fields, previews, images, handlers };
}

function loadModules(env) {
  for (const rel of MODULES) { vm.runInContext(fs.readFileSync(path.join(JS_ROOT, rel), 'utf8'), env.ctx); }
  return env.ctx;
}

function loadFrozen(env) {
  vm.runInContext(fs.readFileSync(FROZEN_FILE, 'utf8'), env.ctx);
  return env.ctx;
}

const settle = () => new Promise((resolve) => setImmediate(resolve));

async function run(load, opts, fn) {
  const env = makeEnv(opts);
  const ctx = load(env);
  let result;
  let thrown = null;
  try { result = await fn(ctx, env); } catch (error) { thrown = String(error && error.message); }
  env.log.push(['resolved']);
  await settle(); await settle();
  const pick = (n) => (n ? [n.value, n.textContent, n.innerHTML] : null);
  return JSON.parse(JSON.stringify({ thrown, result: result === undefined ? null : result, log: env.log,
    fields: env.fields.map((f) => [f.dataset.mcField, f.value]), previews: env.previews.map((p) => p.innerHTML),
    images: env.images.map((i) => [i.value, i.dataset.mcWired || null]), formWired: env.nodes['my-company-form']?.dataset.mcWired || null,
    nodes: Object.fromEntries(Object.entries(env.nodes).filter(([k]) => k !== 'my-company-form').map(([k, n]) => [k, pick(n)])),
    myCompany: env.state.myCompany }));
}

async function fireImage(env, name, files) {
  const input = env.images.find((i) => i.dataset.mcImage === name);
  input.files = files;
  for (const [target, event, handler] of env.handlers) { if (target === input && event === 'change') { await handler(); } }
}

async function scenario(load) {
  const out = {};
  // Preencher, coletar, prévia e leitura.
  for (const [name, company, opts] of [['completa', COMPANY, {}], ['temaInvalido', { ...COMPANY, theme_json: '{oops' }, {}],
    ['semTema', { ...COMPANY, theme_json: '', primary_color: '#123456' }, {}], ['semModo', { ...COMPANY, theme_json: '{"x":1}' }, {}],
    ['camposAusentes', COMPANY, { missingFields: ['theme_mode', 'logo_type'] }], ['nula', null, {}]]) {
    out[`preencher:${name}`] = await run(load, opts, (ctx, env) => {
      ctx.fillMyCompanyFields(env.nodes['my-company-form'], company);
      return [ctx.collectMyCompanyFields(env.nodes['my-company-form']), ctx.myCompanyThemeMode(company)];
    });
  }
  out['preencher:semContainer'] = await run(load, {}, (ctx) => [ctx.fillMyCompanyFields(null, COMPANY) ?? null, ctx.collectMyCompanyFields(null)]);
  out['coletar:espacos'] = await run(load, {}, (ctx, env) => {
    for (const f of env.fields) { f.value = f.dataset.mcField === 'theme_mode' ? '' : `  ${f.dataset.mcField}  `; }
    return ctx.collectMyCompanyFields(env.nodes['my-company-form']);
  });
  out['previa:semPreview'] = await run(load, {}, (ctx, env) => ctx.renderMyCompanyImagePreview(env.nodes['my-company-form'], 'inexistente'));
  out['leitura'] = await run(load, {}, (ctx) => { ctx.renderMyCompanyReadonly(COMPANY); ctx.renderMyCompanyReadonly({}); ctx.renderMyCompanyReadonly(null); });
  out['leitura:semCaixa'] = await run(load, { missing: ['my-company-readonly'] }, (ctx) => ctx.renderMyCompanyReadonly(COMPANY));
  out['rotulos'] = await run(load, {}, (ctx) => ['pending', 'verified', 'failed', 'active', 'outro', '', null, undefined].map((s) => ctx.domainStatusLabel(s)));
  // Carga.
  for (const [name, opts, force] of [['ok', { replies: { '/api/my-company?': { company: COMPANY } } }, false],
    ['semEmpresa', { replies: { '/api/my-company?': {} } }, false], ['cache', { cached: true }, false], ['forcada', { cached: true, replies: { '/api/my-company?': { company: COMPANY } } }, true],
    ['semPermissao', { canConfigure: false }, false], ['falha', { replies: { '/api/my-company?': new Error('503') } }, false]]) {
    out[`carregar:${name}`] = await run(load, opts, (ctx) => ctx.loadMyCompany(force));
  }
  for (const [name, opts] of [['ok', { replies: { '/api/my-company?': { company: COMPANY }, '/api/my-company/domains?': { domains: [{ id: 1 }] } } }],
    ['semEmpresa', { replies: { '/api/my-company?': {} } }], ['semForm', { missing: ['my-company-form'] }], ['semPermissao', { canConfigure: false }],
    ['falha', { replies: { '/api/my-company?': new Error('fora do ar') } }],
    ['semBotoesDominio', { missing: ['my-company-domain-add', 'my-company-domains-table'], replies: { '/api/my-company?': { company: COMPANY } } }]]) {
    out[`cartao:${name}`] = await run(load, opts, (ctx) => ctx.loadMyCompanyCard());
  }
  out['cartao:duasVezes'] = await run(load, { replies: { '/api/my-company?': { company: COMPANY }, '/api/my-company/domains?': { domains: 'x' } } },
    async (ctx) => { await ctx.loadMyCompanyCard(); await ctx.loadMyCompanyCard(true); });
  // Imagens.
  for (const [name, image, files, opts] of [['logo', 'logo_type', [{ type: 'image/jpeg' }], {}], ['favicon', 'favicon_type', [{ type: 'image/svg+xml' }], {}],
    ['tipoInvalido', 'favicon_type', [{ type: 'image/jpeg' }], {}], ['semArquivo', 'logo_type', [], {}], ['campoDesconhecido', 'banner_type', [{ type: 'image/png' }], {}],
    ['falhaConversao', 'login_logo_type', [{ type: 'image/png' }], { convertFails: true }], ['semCampoOculto', 'logo_type', [{ type: 'image/png' }], { missingFields: ['logo_type'] }],
    ['variosArquivos', 'logo_type', [{ type: 'image/png' }, { type: 'image/gif' }], {}]]) {
    out[`imagem:${name}`] = await run(load, opts, async (ctx, env) => {
      ctx.wireMyCompanyImageInputs(env.nodes['my-company-form']);
      ctx.wireMyCompanyImageInputs(env.nodes['my-company-form']);
      await fireImage(env, image, files);
    });
  }
  out['imagem:semContainer'] = await run(load, {}, (ctx) => ctx.wireMyCompanyImageInputs(null));
  // Gravação.
  const ev = (env) => ({ preventDefault: () => env.log.push(['preventDefault']) });
  for (const [name, opts] of [['ok', { replies: { '/api/my-company': { company: { id: 901, saved: true } } } }], ['semEmpresaNaResposta', { cached: true, replies: { '/api/my-company': {} } }],
    ['falha', { replies: { '/api/my-company': new Error('cor inválida') } }], ['falhaSemFeedback', { missing: ['my-company-feedback'], replies: { '/api/my-company': new Error('x') } }],
    ['semPermissao', { canConfigure: false }], ['semForm', { missing: ['my-company-form'] }], ['semUsuario', { noUser: true }],
    ['falhaBootstrap', { bootstrapFails: true, replies: { '/api/my-company': { company: { id: 901 } } } }]]) {
    out[`salvar:${name}`] = await run(load, opts, (ctx, env) => { ctx.fillMyCompanyFields(env.nodes['my-company-form'], COMPANY); return ctx.saveMyCompany(ev(env)); });
  }
  // Domínios.
  for (const [name, opts] of [['ok', { replies: { '/api/my-company/domains?': { domains: [{ id: 3, full_host: 'a.b' }] } } }], ['naoLista', { replies: { '/api/my-company/domains?': { domains: {} } } }],
    ['respostaNula', { replies: { '/api/my-company/domains?': null } }], ['falha', { replies: { '/api/my-company/domains?': new Error('dns') } }],
    ['semTabela', { missing: ['my-company-domains-table'] }], ['semPermissao', { canConfigure: false }]]) {
    out[`dominios:${name}`] = await run(load, opts, (ctx) => ctx.loadMyCompanyDomains());
  }
  for (const [name, opts, input, type] of [['ok', {}, '  epi.cliente.com.br ', 'subdomain'], ['tipoPadrao', {}, 'x.com', ''], ['vazio', {}, '   ', ''],
    ['falha', { replies: { '/api/my-company/domains': new Error('duplicado') } }, 'x.com', ''], ['falhaSemFeedback', { missing: ['my-company-domain-feedback'] }, '', ''],
    ['semCampos', { missing: ['my-company-domain-input', 'my-company-domain-type'] }, '', ''], ['semUsuario', { noUser: true }, 'x.com', '']]) {
    out[`dominio:adicionar:${name}`] = await run(load, opts, (ctx, env) => {
      if (env.nodes['my-company-domain-input']) { env.nodes['my-company-domain-input'].value = input; }
      if (env.nodes['my-company-domain-type']) { env.nodes['my-company-domain-type'].value = type; }
      return ctx.addMyCompanyDomain();
    });
  }
  for (const [name, dataset, opts] of [['verificar', { domainVerify: '4' }, {}], ['principal', { domainPrimary: '5' }, {}], ['remover', { domainDelete: '6' }, {}],
    ['removerCancelado', { domainDelete: '6' }, { confirms: [false] }], ['nenhuma', {}, {}],
    ['falha', { domainVerify: '4' }, { replies: { '/api/my-company/domains/4': new Error('TXT ausente') } }],
    ['falhaSemFeedback', { domainPrimary: '5' }, { missing: ['my-company-domain-feedback'], replies: { '/api/my-company/domains/5': new Error('y') } }],
    ['semUsuario', { domainDelete: '6' }, { noUser: true }],
    ['falhaRecarrega', { domainVerify: '4' }, { replies: { '/api/my-company/domains/4': new Error('TXT ausente'), '/api/my-company/domains?': { domains: [{ id: 4 }] } } }]]) {
    out[`dominio:acao:${name}`] = await run(load, opts, (ctx) => ctx.handleMyCompanyDomainAction({ target: { dataset } }));
  }
  return out;
}

module.exports = function ({ testAsync, test, assert, eq }) {
  testAsync('UBX-V5 Minha Empresa: os módulos reproduzem as funções originais do app.js', async () => {
    const expected = await scenario(loadFrozen);
    const actual = await scenario(loadModules);
    assert(Object.keys(expected).length >= 50, 'cenários de caracterização');
    const crashed = Object.keys(expected).filter((k) => expected[k].thrown && !/^carregar:falha$/.test(k));
    assert(!crashed.length, `referência quebrou (ambiente incompleto): ${crashed.slice(0, 5).join(', ')}`);
    eq(Object.keys(actual).sort().join(','), Object.keys(expected).sort().join(','), 'mesmos cenários');
    const diverge = Object.keys(expected).filter((k) => JSON.stringify(actual[k]) !== JSON.stringify(expected[k]));
    assert(!diverge.length, `cenários divergentes: ${diverge.slice(0, 8).join(', ')}${diverge.length > 8 ? ` (+${diverge.length - 8})` : ''}`
      + (diverge.length ? `\n  esperado: ${JSON.stringify(expected[diverge[0]]).slice(0, 600)}\n  obtido:   ${JSON.stringify(actual[diverge[0]]).slice(0, 600)}` : ''));
  });

  test('UBX-V5 Minha Empresa: contrato dos módulos (globais, namespaces congelados, carga antes do app.js, nada volta ao monólito)', () => {
    const env = makeEnv();
    const ctx = loadModules(env);
    for (const name of NAMES) { eq(typeof ctx[name], 'function', name); }
    for (const ns of ['__EPI_MY_COMPANY_BUSINESS__', '__EPI_MY_COMPANY_API__', '__EPI_MY_COMPANY_UI__']) {
      assert(ctx[ns] && Object.isFrozen(ctx[ns]), `${ns} publicado e congelado`);
    }
    const scripts = fs.readFileSync(path.resolve(JS_ROOT, '..', 'views', '_scripts.html'), 'utf8');
    const order = [...scripts.matchAll(/<script[^>]+src="([^"?]+)/g)].map((m) => m[1]);
    const idx = MODULES.map((m) => order.indexOf(`/js/${m}`));
    assert(idx.every((i) => i >= 0), 'módulos registrados em _scripts.html');
    assert(idx[0] < idx[1] && idx[1] < idx[2], 'business → integrations → ui');
    assert(Math.max(...idx) < order.indexOf('/app.js'), 'antes do app.js');
    const app = fs.readFileSync(path.resolve(JS_ROOT, '..', 'app.js'), 'utf8');
    for (const name of [...NAMES, 'MY_COMPANY_IMAGE_TYPES', 'MY_COMPANY_COLOR_DEFAULTS']) {
      assert(!new RegExp(`^\\s*(?:async\\s+)?(?:function|const|let|var)\\s+${name}\\b`, 'm').test(app), `${name} voltou ao app.js`);
    }
    assert(/^function renderMyCompanyDomains\(/m.test(app), 'renderMyCompanyDomains segue no app.js (alterada pelo PR pendente I18N-FULL-V1)');
  });
};

module.exports.scenario = scenario;
module.exports.loadFrozen = loadFrozen;
module.exports.loadModules = loadModules;
