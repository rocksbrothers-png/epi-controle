'use strict';
// UBX Comercial, fatia C2 — caracterização das integrações comerciais.
//
// As 12 funções do app.js que chamam os endpoints comerciais
// (loadCommercialContract, toggleCommercialStatus, downloadCommercialContractPdf,
// saveCommercialContractDraft, generateCommercialContract,
// viewGeneratedCommercialContract, downloadGeneratedCommercialContract,
// signCommercialContractAction, uploadSignedCommercialContract,
// sendCommercialContractByEmail, saveCommercial, saveCommercialSettings) rodam
// num contexto isolado em que TUDO o que é observável vira um evento de log, na
// ordem em que acontece: cada chamada ao cliente oficial `api` (caminho, número
// de argumentos e opções serializadas), cada `globalThis.open`, o valor de
// state.commercialContract a cada renderização, recarga do bootstrap,
// preenchimento de formulário, alerta (texto traduzido no idioma ativo) e
// console.warn. Exceções que escapam também são registradas.
//
// A referência "antes" é a cópia literal do app.js
// (fixtures/app-before-ubx-commercial-c2.js.txt); a "atual" é o que o app.js de
// hoje carrega. Cada cenário roda nas duas e os logs têm de ser idênticos, nos
// cinco idiomas: respostas válidas, vazias e nulas; 401, 403, 404 e 5xx; falha
// de rede e timeout; concorrência com respostas fora de ordem; chamadas
// duplicadas; troca de usuário, de empresa e de perfil; ausência de permissão,
// de empresa selecionada e de arquivo.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const STATIC = path.resolve(__dirname, '..', '..');
const LOCALES = ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO'];
const NAMES = ['loadCommercialContract', 'toggleCommercialStatus', 'downloadCommercialContractPdf', 'saveCommercialContractDraft',
  'generateCommercialContract', 'viewGeneratedCommercialContract', 'downloadGeneratedCommercialContract',
  'signCommercialContractAction', 'uploadSignedCommercialContract', 'sendCommercialContractByEmail', 'saveCommercial',
  'saveCommercialSettings'];
const read = (rel) => fs.readFileSync(path.join(STATIC, rel), 'utf8');
const CATALOGS = Object.fromEntries(LOCALES.map((l) => [l, JSON.parse(read(`i18n/${l}.json`))]));

function extractFunction(source, name) {
  const match = new RegExp(`^[ \\t]*(?:async\\s+)?function ${name}\\(`, 'm').exec(source);
  if (!match) { throw new Error(`função ${name} não encontrada`); }
  let depth = 0;
  for (let i = source.indexOf('{', match.index); i < source.length; i += 1) {
    if (source[i] === '{') { depth += 1; }
    if (source[i] === '}') { depth -= 1; if (depth === 0) { return source.slice(match.index, i + 1); } }
  }
  throw new Error(`função ${name} sem fim`);
}

const COMPANIES = [
  { id: 901, name: 'Empresa QA <b>', legal_name: 'Empresa QA Ltda', cnpj: '11.222.333/0001-81', logo_type: '', plan_name: 'start',
    user_limit: 10, contract_start: '2026-01-01', contract_end: '2026-12-31', monthly_value: 420, addendum_enabled: 1,
    license_status: 'active', active: 1, commercial_notes: 'nota "x"' },
  { id: 902, name: 'Cliente Dois', legal_name: null, cnpj: '', plan_name: 'business', user_limit: 20, monthly_value: 0,
    license_status: 'suspended', active: 0 }
];

// Erros como o cliente oficial os produz (status/código), mais rede e timeout.
function makeError(kind) {
  if (kind === 'network') { return new TypeError('Failed to fetch'); }
  if (kind === 'timeout') { const e = new Error('The operation was aborted.'); e.name = 'AbortError'; return e; }
  const status = Number(kind.replace('http', ''));
  const e = new Error(`erro ${status}`);
  e.status = status;
  e.payload = { error: `erro ${status}` };
  return e;
}

// Contexto isolado com registro de eventos. `respond(path, options)` decide a
// resposta de cada chamada: { value } ou { error } ou { deferred: true }.
// O contexto (motor de tradução + funções) é montado uma vez por implementação e
// idioma; `reset(opts)` recria estado, refs, log e respostas a cada cenário.
function buildContext(lang) {
  const env = { log: [], deferred: [], opts: {} };
  const ctx = { JSON, Number, String, Object, Array, Promise, URLSearchParams, Symbol, Error, TypeError, Math };
  env.ctx = ctx;
  ctx.globalThis = ctx;
  ctx.EpiI18n = { lang };
  ctx.__CATALOG_ACTIVE__ = CATALOGS[lang];
  ctx.__CATALOG_FALLBACK__ = CATALOGS['pt-BR'];
  vm.createContext(ctx);
  const i18n = read('i18n.js');
  vm.runInContext([
    "const FALLBACK = 'pt-BR'; const _pluralCount = Symbol('numeric plural count');",
    `let _active = __CATALOG_ACTIVE__; let _fallback = __CATALOG_FALLBACK__; let _lang = ${JSON.stringify(lang)};`,
    ...['_resolve', '_interpolate', '_message', 't', 'trEpi'].map((n) => extractFunction(i18n, n)),
    'var tr = trEpi;'
  ].join('\n'), ctx);
  const snapshot = (value) => JSON.parse(JSON.stringify(value === undefined ? null : value));
  const field = (value) => ({ value });
  env.reset = (opts) => {
    env.opts = opts;
    env.log = [];
    env.deferred = [];
    ctx.state = { user: { id: opts.userId ?? 7, role: opts.role ?? 'master_admin' }, companies: snapshot(COMPANIES), commercialContract: 'antes' };
    ctx.refs = {
      commercialCompany: field(opts.companyId ?? '901'),
      commercialForm: { elements: { addendum_enabled: { checked: opts.addendum ?? true } } },
      commercialSignatureName: field('Ana "QA"'),
      commercialSignatureData: field('data:image/png;base64,QUJD'),
      commercialSignedFile: { files: opts.noFile ? [] : [{ name: 'assinado <1>.pdf', type: opts.fileType ?? 'application/pdf' }] },
      commercialEmailTo: field('cliente@exemplo.test'),
      commercialEmailSubject: field('Contrato & aditivo'),
      commercialEmailBody: field('Linha 1\nLinha "2"'),
      commercialSettingsForm: { elements: { unit_price: field(opts.unitPrice ?? '42.5'), individual_max: field('1'), start_max: field(opts.startMax ?? '12'),
        business_max: field(''), corporate_max: field('90'), enterprise_min: field('91') } }
    };
    return env;
  };
  ctx.api = function api(apiPath, options) {
    env.log.push(['api', apiPath, arguments.length, options === undefined ? 'undefined' : JSON.stringify(options)]);
    const answer = env.opts.respond(apiPath, options);
    if (answer.deferred) { return new Promise((resolve, reject) => env.deferred.push({ apiPath, resolve, reject })); }
    if (answer.error) { return Promise.reject(makeError(answer.error)); }
    return Promise.resolve(answer.value);
  };
  ctx.open = (url, target) => { env.log.push(['open', url, target]); return null; };
  ctx.alert = (message) => { env.log.push(['alert', String(message)]); };
  ctx.console = { warn: (...args) => env.log.push(['warn', String(args[0]), args[1]?.status ?? args[1]?.name ?? null]) };
  ctx.loadBootstrap = async () => { env.log.push(['loadBootstrap']); };
  ctx.fillCommercialForm = (id) => env.log.push(['fillCommercialForm', id === undefined ? 'undefined' : id]);
  ctx.fillCommercialSettingsForm = () => env.log.push(['fillCommercialSettingsForm']);
  ctx.renderCommercialContractPanel = () => env.log.push(['render', snapshot(ctx.state.commercialContract)]);
  ctx.resetCommercialContractForm = (o) => env.log.push(['reset', snapshot(o)]);
  ctx.buildCommercialContractPayload = () => ({ actor_user_id: ctx.state.user.id, company_id: Number(ctx.refs.commercialCompany.value || 0),
    clauses: ['Cláusula 1', 'Cláusula "2"'] });
  ctx.canAccessCommercialArea = () => env.opts.canAccess ?? true;
  ctx.hasPermission = (p) => { env.log.push(['hasPermission', p]); return env.opts.permitted ?? true; };
  ctx.requirePermission = (p) => { env.log.push(['requirePermission', p]); return env.opts.permitted ?? true; };
  ctx.formValues = () => ({ plan_name: 'start', user_limit: '10', license_status: 'active', active: '1', company_id: '901' });
  ctx.fileToBase64 = async (file) => { env.log.push(['fileToBase64', file.name]); return 'UERGLWJhc2U2NA=='; };
  return env;
}

// "Antes": cópia literal do app.js. "Atual": o que o app.js de hoje carrega
// (as mesmas funções do app.js + os módulos de integração de que dependem).
const CURRENT_MODULES = ['js/modules/companies/integrations/companies-api.js', 'js/modules/commercial/integrations/commercial-api.js'];
const CACHE = new Map();
function cached(kind, lang, setup) {
  const key = `${kind}:${lang}`;
  if (!CACHE.has(key)) { const env = buildContext(lang); setup(env.ctx); CACHE.set(key, env); }
  return CACHE.get(key);
}
function loadOriginal(lang, opts) {
  return cached('original', lang, (ctx) => vm.runInContext(read('js/test/fixtures/app-before-ubx-commercial-c2.js.txt'), ctx)).reset(opts);
}
// UBX Comercial C3: os 12 chamadores moram agora em modules/commercial/ui/commercial-view.js e
// commercial-contract-view.js.
// Cada um é extraído de lá e roda sozinho neste contexto (as funções vizinhas
// continuam controladas pelo teste); `state` e `refs` chegam pelos mesmos
// globais que o módulo lê na página (__EPI_APP_STATE__ e __EPI_REFS__).
const CURRENT_CALLERS = ['js/modules/commercial/ui/commercial-contract-view.js', 'js/modules/commercial/ui/commercial-view.js'];
function loadCurrent(lang, opts) {
  return cached('current', lang, (ctx) => {
    for (const rel of CURRENT_MODULES) { vm.runInContext(read(rel), ctx); }
    Object.defineProperty(ctx, '__EPI_APP_STATE__', { get: () => ctx.state, configurable: true });
    Object.defineProperty(ctx, '__EPI_REFS__', { get: () => ctx.refs, configurable: true });
    const view = CURRENT_CALLERS.map(read).join('\n');
    vm.runInContext(NAMES.map((n) => extractFunction(view, n)).join('\n\n'), ctx);
  }).reset(opts);
}

const flush = () => new Promise((resolve) => setImmediate(resolve));

// Executa um passo (chamada de função) e registra exceção síncrona/assíncrona que escape.
async function step(env, fn, args) {
  try {
    await env.ctx[fn](...args);
    env.log.push(['done', fn]);
  } catch (error) {
    env.log.push(['threw', fn, error?.name || 'Error', String(error?.message || error), error?.status ?? null]);
  }
  await flush();
}

const RESPONSES = {
  contract: { value: { contract: { id: 5, status: 'generated', contract_number: 'CT-5' } } },
  empty: { value: {} },
  nullBody: { value: null },
  http401: { error: 'http401' },
  http403: { error: 'http403' },
  http404: { error: 'http404' },
  http500: { error: 'http500' },
  http502: { error: 'http502' },
  network: { error: 'network' },
  timeout: { error: 'timeout' }
};

const VARIANTS = [
  {},
  { userId: 8, role: 'general_admin' },
  { companyId: '902' },
  { companyId: '' },
  { permitted: false },
  { canAccess: false },
  { noFile: true, fileType: '' },
  { addendum: false, startMax: '', unitPrice: '' }
];

// Chamadas com os argumentos que os chamadores reais do app.js usam.
const CALLS = [
  ['loadCommercialContract', () => [901]],
  ['loadCommercialContract', () => [undefined]],
  ['toggleCommercialStatus', () => [901, 'reactivate']],
  ['toggleCommercialStatus', () => ['902', 'suspend']],
  ['toggleCommercialStatus', () => [999, 'suspend']],
  ['downloadCommercialContractPdf', () => []],
  ['saveCommercialContractDraft', () => [true]],
  ['saveCommercialContractDraft', () => []],
  ['generateCommercialContract', () => []],
  ['viewGeneratedCommercialContract', () => []],
  ['downloadGeneratedCommercialContract', () => []],
  ['signCommercialContractAction', () => []],
  ['uploadSignedCommercialContract', () => []],
  ['sendCommercialContractByEmail', () => []],
  ['saveCommercial', (log) => [{ preventDefault: () => log.push(['preventDefault']) }]],
  ['saveCommercialSettings', (log) => [{ preventDefault: () => log.push(['preventDefault']) }]]
];

async function runScenario(load, lang, variant, responseKey, call) {
  const env = load(lang, { ...variant, respond: () => RESPONSES[responseKey] });
  const [fn, args] = call;
  await step(env, fn, args(env.log));
  env.log.push(['state.commercialContract', JSON.parse(JSON.stringify(env.ctx.state.commercialContract ?? null))]);
  return env.log;
}

// Concorrência: duas cargas de contrato com respostas resolvidas fora de ordem,
// e a mesma ação disparada duas vezes antes de a primeira terminar.
async function runConcurrency(load, lang) {
  const out = [];
  {
    const env = load(lang, { respond: () => ({ deferred: true }) });
    const first = env.ctx.loadCommercialContract(901);
    const second = env.ctx.loadCommercialContract(902);
    await flush();
    env.deferred[1].resolve({ contract: { id: 2, company_id: 902 } });
    await flush();
    env.deferred[0].resolve({ contract: { id: 1, company_id: 901 } });
    await Promise.all([first, second]);
    await flush();
    env.log.push(['final', env.ctx.state.commercialContract]);
    out.push(env.log);
  }
  for (const fn of ['generateCommercialContract', 'saveCommercialContractDraft', 'signCommercialContractAction', 'sendCommercialContractByEmail']) {
    const env = load(lang, { respond: () => ({ deferred: true }) });
    const a = env.ctx[fn]();
    const b = env.ctx[fn]();
    await flush();
    env.deferred[0].reject(makeError('http500'));
    env.deferred[1].resolve({ contract: { id: 9, status: fn } });
    await Promise.allSettled([a, b]);
    await flush();
    env.log.push(['final', env.ctx.state.commercialContract]);
    out.push(env.log);
  }
  return out;
}


// Chamadas literais de antes, uma por endpoint, para comparar com o módulo.
const ORIGINAL_LITERALS = {
  getContract: (api, a, c) => api(`/api/commercial-contract?actor_user_id=${a}&company_id=${c}`),
  saveContractDraft: (api, p) => api('/api/commercial-contract/save', { method: 'POST', body: JSON.stringify(p) }),
  generateContract: (api, p) => api('/api/commercial-contract/generate', { method: 'POST', body: JSON.stringify(p) }),
  signContract: (api, p) => api('/api/commercial-contract/sign', { method: 'POST', body: JSON.stringify(p) }),
  uploadSignedContract: (api, p) => api('/api/commercial-contract/upload-signed', { method: 'POST', body: JSON.stringify(p) }),
  sendContractEmail: (api, p) => api('/api/commercial-contract/send-email', { method: 'POST', body: JSON.stringify(p) }),
  saveCommercialSettings: (api, p) => api('/api/commercial-settings', { method: 'POST', body: JSON.stringify(p) })
};

function loadModuleAlone() {
  const calls = [];
  const ctx = { JSON, URLSearchParams, Object, Promise };
  ctx.globalThis = ctx;
  ctx.api = function api(...args) { calls.push(JSON.stringify([args.length, ...args])); return Promise.resolve({ ok: true }); };
  vm.createContext(ctx);
  const before = Object.keys(ctx).sort();
  vm.runInContext(read('js/modules/commercial/integrations/commercial-api.js'), ctx);
  return { ctx, calls, before };
}

module.exports = function ({ testAsync, test, assert, eq }) {
  test('UBX Comercial C2: a fixture é cópia literal das 12 funções chamadoras', () => {
    const fixture = read('js/test/fixtures/app-before-ubx-commercial-c2.js.txt');
    const found = [...fixture.matchAll(/^(?:async )?function ([A-Za-z_$][\w$]*)\(/gm)].map((m) => m[1]);
    eq(JSON.stringify(found), JSON.stringify(NAMES), 'as 12 funções, na ordem do app.js');
  });

  testAsync('UBX Comercial C2: chamadores atuais × app.js de antes — mesmos efeitos observáveis em todos os cenários e nos cinco idiomas', async () => {
    let compared = 0;
    for (const lang of LOCALES) {
      for (const variant of VARIANTS) {
        for (const responseKey of Object.keys(RESPONSES)) {
          for (const call of CALLS) {
            const before = await runScenario(loadOriginal, lang, variant, responseKey, call);
            const after = await runScenario(loadCurrent, lang, variant, responseKey, call);
            eq(JSON.stringify(after), JSON.stringify(before), `${lang} ${JSON.stringify(variant)} ${responseKey} ${call[0]}`);
            compared += 1;
          }
        }
      }
      const before = await runConcurrency(loadOriginal, lang);
      const after = await runConcurrency(loadCurrent, lang);
      eq(JSON.stringify(after), JSON.stringify(before), `${lang}: concorrência e chamadas duplicadas`);
    }
    assert(compared >= 6000, `cobertura da comparação: ${compared}`);
  });

  testAsync('UBX Comercial C2: valores de referência (contrato HTTP fixado)', async () => {
    const env = loadCurrent('pt-BR', { respond: () => RESPONSES.contract });
    await step(env, 'loadCommercialContract', [901]);
    eq(JSON.stringify(env.log[0]), JSON.stringify(['api', '/api/commercial-contract?actor_user_id=7&company_id=901', 1, 'undefined']), 'GET do contrato');
    const posts = loadCurrent('pt-BR', { respond: () => RESPONSES.contract });
    await step(posts, 'saveCommercialSettings', [{ preventDefault() {} }]);
    const settings = posts.log.find((e) => e[0] === 'api');
    eq(settings[1], '/api/commercial-settings', 'POST dos parâmetros');
    eq(JSON.parse(settings[3]).method, 'POST', 'método');
    const toggle = loadCurrent('pt-BR', { respond: () => RESPONSES.contract });
    await step(toggle, 'toggleCommercialStatus', [901, 'suspend']);
    const put = toggle.log.find((e) => e[0] === 'api');
    eq(put[1], '/api/companies/901', 'PUT da empresa');
    eq(JSON.parse(JSON.parse(put[3]).body).license_status, 'suspended', 'corpo do PUT');
    const files = loadCurrent('pt-BR', { respond: () => RESPONSES.contract });
    await step(files, 'downloadGeneratedCommercialContract', []);
    eq(JSON.stringify(files.log[0]), JSON.stringify(['open', '/api/commercial-contract/file?actor_user_id=7&company_id=901&kind=generated', '_blank']), 'arquivo gerado');
  });

  test('UBX Comercial C2: cada função do módulo faz exatamente a chamada literal de antes (9 endpoints)', () => {
    const { ctx, calls } = loadModuleAlone();
    const ns = ctx.__EPI_COMMERCIAL_API__;
    const actors = [7, 8, '9', 0, undefined, null];
    const companies = [901, '902', '', 0, undefined, 'a b&c=d?e#f', 'ç/ü'];
    const payloads = [{}, { actor_user_id: 7, company_id: 901, x: 'á "b" <c>' }, { nested: { a: [1, null, 'x'] } }, null, 'texto', 0];
    let checked = 0;
    for (const a of actors) {
      for (const c of companies) {
        const expected = [];
        ORIGINAL_LITERALS.getContract((...args) => { expected.push(JSON.stringify([args.length, ...args])); }, a, c);
        calls.length = 0;
        ns.getContract(a, c);
        eq(calls[0], expected[0], `getContract(${a}, ${c})`);
        for (const extra of [{}, { kind: 'generated' }]) {
          const query = { actor_user_id: a, company_id: c, ...extra };
          eq(ns.contractPdfUrl(query), `/api/commercial-contract.pdf?${new URLSearchParams(query).toString()}`, 'URL do PDF');
          eq(ns.contractFileUrl(query), `/api/commercial-contract/file?${new URLSearchParams(query).toString()}`, 'URL do arquivo');
          // Botão "ver contrato" dos detalhes da Empresa: company_id como String.
          const fromCompanies = { actor_user_id: a, company_id: String(c) };
          eq(ns.contractPdfUrl(fromCompanies), `/api/commercial-contract.pdf?${new URLSearchParams(fromCompanies).toString()}`, 'URL do PDF (Empresas)');
          checked += 3;
        }
        checked += 1;
      }
    }
    for (const name of Object.keys(ORIGINAL_LITERALS).filter((n) => n !== 'getContract')) {
      for (const payload of payloads) {
        const expected = [];
        ORIGINAL_LITERALS[name]((...args) => { expected.push(JSON.stringify([args.length, ...args])); }, payload);
        calls.length = 0;
        ns[name](payload);
        eq(calls[0], expected[0], `${name}(${JSON.stringify(payload)})`);
        checked += 1;
      }
    }
    assert(checked >= 200, `cobertura: ${checked}`);
  });

  test('UBX Comercial C2: o módulo só publica o namespace congelado, carrega uma vez e respeita a ordem de carga', () => {
    const { ctx, before } = loadModuleAlone();
    const added = Object.keys(ctx).sort().filter((k) => !before.includes(k));
    eq(JSON.stringify(added), JSON.stringify(['__EPI_COMMERCIAL_API__', '__EPI_MODULE_COMMERCIAL_INTEGRATIONS_LOADED__']), 'globais publicados');
    assert(Object.isFrozen(ctx.__EPI_COMMERCIAL_API__), 'namespace congelado');
    eq(JSON.stringify(Object.keys(ctx.__EPI_COMMERCIAL_API__)), JSON.stringify(['getContract', 'contractPdfUrl', 'contractFileUrl', 'saveContractDraft',
      'generateContract', 'signContract', 'uploadSignedContract', 'sendContractEmail', 'saveCommercialSettings']), 'funções publicadas');
    const first = ctx.__EPI_COMMERCIAL_API__;
    vm.runInContext(read('js/modules/commercial/integrations/commercial-api.js'), ctx);
    eq(ctx.__EPI_COMMERCIAL_API__, first, 'segunda carga não republica');
    const module = read('js/modules/commercial/integrations/commercial-api.js');
    assert(!/\bdocument\b|\.innerHTML|\bwindow\.open\b|globalThis\.open|\bstate\.|\brefs\./.test(module), 'sem DOM, abertura de aba ou estado do app');
    const order = [...read('views/_scripts.html').matchAll(/<script[^>]+src="([^"?]+)/g)].map((m) => m[1]);
    const i = (src) => order.indexOf(src);
    const iMod = i('/js/modules/commercial/integrations/commercial-api.js');
    assert(iMod >= 0 && i('/js/modules/api-client.js') < iMod && i('/js/modules/companies/integrations/companies-api.js') < i('/app.js')
      && iMod < i('/app.js'), `ordem de carga: api-client ${i('/js/modules/api-client.js')}, commercial-api ${iMod}, app ${i('/app.js')}`);
    eq(order.filter((src) => src === '/js/modules/commercial/integrations/commercial-api.js').length, 1, 'carregado uma vez');
    const app = read('app.js');
    const view = CURRENT_CALLERS.map(read).join('\n');
    eq((app.match(/\/api\/commercial/g) || []).length, 0, 'nenhum endpoint comercial no app.js');
    eq((view.match(/\/api\/commercial/g) || []).length, 0, 'nenhum endpoint comercial na interface comercial');
    // UBX Comercial C3: os 10 chamadores foram para a interface comercial; no app.js fica o botão "ver contrato" de Empresas.
    eq((app.match(/__EPI_COMMERCIAL_API__\./g) || []).length, 1, 'um uso da integração no app.js (botão "ver contrato" de Empresas)');
    eq((view.match(/__EPI_COMMERCIAL_API__\./g) || []).length, 10, 'dez usos da integração na interface comercial (10 chamadores)');
    eq(((app + view).match(/__EPI_COMPANIES_API__\.updateCompany\(/g) || []).length, 2, 'PUT de empresa reaproveitado de Empresas (2 chamadores)');
    eq((view.match(/__EPI_COMPANIES_API__\.updateCompany\(/g) || []).length, 2, 'os 2 chamadores do PUT estão na interface comercial');
  });
};
