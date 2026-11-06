'use strict';
// UBX Comercial, fatia C3 — caracterização da interface comercial.
//
// As 33 funções de interface e interação do Comercial (preenchimento dos
// formulários de empresa, contrato e parâmetros; prévia de valores; painéis de
// KPIs, resumo, alertas, vencimentos e histórico; filtros; exportação CSV/Excel
// e impressão; ações de contrato; suspender/reativar; salvar) rodam num
// contexto isolado com as dependências REAIS da página:
//   - tr: o motor do static/i18n.js com os cinco catálogos (pt-BR de fallback);
//   - escapeHtml/formatDate/formatDateTime/filterByUserCompany: views/view-helpers.js;
//   - formatCurrency/daysUntil: modules/shared/business/value-format.js;
//   - C1 (modules/commercial/{business,ui}) e companyLogoMarkup (shared/ui/company-logo.js);
//   - C2 (modules/commercial/integrations) e companies-api.js sobre um `api` que registra.
// O que é da sessão ou do navegador é controlado e registrado: permissões,
// acesso ao Comercial, recarga do bootstrap, formValues, leitura de arquivo,
// alertas, console.warn, abertura de aba, popup de impressão, Blob/URL e o
// clique do link de download.
//
// Os elementos do DOM são objetos simples (value, innerHTML, textContent,
// checked, files, binding vivo do textFor). Depois de CADA passo o teste tira
// uma fotografia de todos eles e do estado comercial (contrato, modelo de
// cláusulas, filtros, empresas, empresa selecionada); cada cenário é a
// sequência de eventos + fotografias. Nada é normalizado.
//
// A referência "antes" é a cópia literal do app.js
// (fixtures/app-before-ubx-commercial-c3.js.txt); a "atual" é o que a página
// carrega hoje: modules/commercial/ui/commercial-contract-view.js e
// commercial-view.js, chamados pela fachada __EPI_COMMERCIAL_VIEW__ (as chamadas
// internas entre as funções ficam dentro de cada módulo, como ficavam dentro do
// bloco do app.js). Os cenários
// rodam nas duas e precisam ser idênticos, nos cinco idiomas.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const STATIC = path.resolve(__dirname, '..', '..');
const LOCALES = ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO'];
const NAMES = ['filteredCommercialCompanies', 'filteredCommercialLogs', 'fillCommercialSettingsForm', 'refreshCommercialPreview',
  'fillCommercialForm', 'contractStatusLabel', 'renderCommercialContractPanel', 'resetCommercialContractForm', 'loadCommercialContract',
  'buildCommercialContractPayload', 'toggleCommercialStatus', 'renderCommercialStats', 'renderCommercialSummary', 'renderCommercialAlerts',
  'renderCommercialHistory', 'renderCommercialExpiring', 'populateCommercialActors', 'exportCommercialExcel', 'formatCommercialFiltersLabel',
  'printCommercialHistory', 'downloadCommercialContractPdf', 'saveCommercialContractDraft', 'generateCommercialContract',
  'viewGeneratedCommercialContract', 'downloadGeneratedCommercialContract', 'signCommercialContractAction', 'uploadSignedCommercialContract',
  'sendCommercialContractByEmail', 'exportCommercialHistory', 'syncCommercialFilter', 'saveCommercial', 'saveCommercialContractManagement',
  'saveCommercialSettings'];
// Eram `async function` de bloco no app.js: não eram globais (sem Annex B).
const ASYNC_NAMES = ['loadCommercialContract', 'toggleCommercialStatus', 'saveCommercialContractDraft', 'generateCommercialContract',
  'signCommercialContractAction', 'uploadSignedCommercialContract', 'sendCommercialContractByEmail', 'saveCommercial',
  'saveCommercialContractManagement', 'saveCommercialSettings'];
const read = (rel) => fs.readFileSync(path.join(STATIC, rel), 'utf8');
// A interface comercial extraída, na ordem de carga da página.
const VIEW_MODULES = ['js/modules/commercial/ui/commercial-contract-view.js', 'js/modules/commercial/ui/commercial-view.js'];
const CONTRACT_NAMES = ['contractStatusLabel', 'renderCommercialContractPanel', 'resetCommercialContractForm', 'loadCommercialContract',
  'buildCommercialContractPayload', 'downloadCommercialContractPdf', 'saveCommercialContractDraft', 'generateCommercialContract',
  'viewGeneratedCommercialContract', 'downloadGeneratedCommercialContract', 'signCommercialContractAction',
  'uploadSignedCommercialContract', 'sendCommercialContractByEmail', 'saveCommercialContractManagement'];
const CATALOGS = Object.fromEntries(LOCALES.map((l) => [l, JSON.parse(read(`i18n/${l}.json`))]));

function extractFunction(source, name) {
  const match = new RegExp(`^[ \\t]*(?:async\\s+)?function ${name}\\(`, 'm').exec(source);
  if (!match) { throw new Error(`função ${name} não encontrada`); }
  // O corpo começa no `{` depois da lista de parâmetros (que pode ter desestruturação).
  let depth = 0;
  for (let i = source.indexOf(') {', match.index) + 2; i < source.length; i += 1) {
    if (source[i] === '{') { depth += 1; }
    if (source[i] === '}') { depth -= 1; if (depth === 0) { return source.slice(match.index, i + 1); } }
  }
  throw new Error(`função ${name} sem fim`);
}

const DEFAULT_SETTINGS = {
  unit_price: 42,
  plans: {
    individual: { label: 'Individual', min_users: 1, max_users: 1 },
    start: { label: 'Start', min_users: 1, max_users: 10 },
    business: { label: 'Business', min_users: 11, max_users: 25 },
    corporate: { label: 'Corporate', min_users: 26, max_users: 100 },
    enterprise: { label: 'Enterprise', min_users: 101, max_users: null }
  }
};
const XSS = '<img src=x onerror=alert(1)>';
const isoInDays = (days) => { const d = new Date(); d.setDate(d.getDate() + days); return d.toISOString().slice(0, 10); };
const COMPANIES = [
  { id: 901, name: `Empresa QA ${XSS}`, legal_name: 'Empresa QA Ltda', cnpj: '11.222.333/0001-81', logo_type: '', plan_name: 'start',
    user_limit: 10, user_count: 9, near_limit: true, contract_start: '2026-01-01', contract_end: isoInDays(5), monthly_value: 420,
    addendum_enabled: 1, license_status: 'active', active: 1, commercial_notes: 'nota "x"' },
  { id: 902, name: 'Cliente Dois', legal_name: null, cnpj: '', plan_name: 'business', user_limit: 20, user_count: 20, limit_reached: 1,
    monthly_value: 0, license_status: 'suspended', active: 0, contract_end: isoInDays(0) },
  { id: 903, name: 'Terceira & Cia', legal_name: 'Terceira', cnpj: '33', plan_name: 'enterprise', user_limit: 300, user_count: 12,
    monthly_value: 9000.5, license_status: 'expired', active: 1, contract_start: '2025-01-01', contract_end: isoInDays(-3) },
  { id: 904, name: 'Quarta', plan_name: 'corporate', user_limit: 50, user_count: 1, monthly_value: '12.34', license_status: 'active',
    active: '1', contract_end: isoInDays(30) },
  { id: 905, name: 'Quinta', plan_name: 'individual', license_status: 'active', active: 1, contract_end: isoInDays(31) }
];
const LOGS = [
  { id: 1, company_id: 901, company_name: `Empresa QA ${XSS}`, action_label: 'Atualização', actor_name: `Ana ${XSS}`,
    created_at: '2026-10-30T14:05:00', summary: 'Plano "alterado"', details: [{ field: 'plan_name', before: 'start', after: 'pro' }] },
  { id: 2, company_id: 902, company_name: 'Cliente Dois', action_label: 'Suspensão', actor_name: 'Bruno', created_at: '2026-09-01T08:00:00',
    summary: 'Suspensa', details: [] },
  { id: 3, company_id: 901, company_name: 'Empresa QA', action_label: 'Criação', actor_name: 'Bruno', created_at: '2026-11-02T23:59:59',
    summary: '', details: [{ field: 'user_limit', before: '', after: '10' }, { field: 'notes', before: 'a;b', after: null }] },
  { id: 4, company_id: 903, company_name: 'Terceira', action_label: 'Contrato', actor_name: 'Ana', created_at: '2026-10-15T00:00:00',
    summary: 'linha 1\nlinha 2', details: null }
];
// Mais registros que o limite do painel de histórico (12), com datas e atores variados.
const MANY_LOGS = () => Array.from({ length: 15 }, (_, i) => ({ ...clone(LOGS[i % LOGS.length]), id: 100 + i, company_id: 901,
  created_at: `2026-${String(1 + (i % 11)).padStart(2, '0')}-${String(10 + i).padStart(2, '0')}T0${i % 10}:00:00`,
  actor_name: i % 3 ? 'Bruno' : `Ana ${i}` }));
const CONTRACTS = {
  rich: { id: 5, company_id: 901, status: 'pending_signature', contract_number: 'CT-5', issue_date: '2026-11-01', contractor_address: 'Rua <b>',
    contractor_representative: 'Ana', contractor_representative_role: 'Diretora', contractor_email: 'ana@exemplo.test', contractor_phone: '11',
    contractor_witness_1: 'T1', contractor_witness_2: 'T2', provider_name: 'EPI', provider_legal_name: 'EPI Ltda', provider_cnpj: '00',
    provider_address: 'Av', provider_representative: 'Rep', provider_representative_role: 'CEO', provider_email: 'p@x.test', provider_phone: '22',
    provider_witnesses: 'W', clauses_text: 'Cláusula 1\nCláusula "2"', last_email_to: 'dest@x.test', last_email_subject: 'Assunto',
    last_email_body: 'Corpo', events: [{ event_type: `generated ${XSS}`, created_at: '2026-10-30T10:00:00' }, { event_type: 'signed', created_at: 'inválida' }] },
  minimal: { status: 'codigo_novo' },
  noClauses: { status: '', contractor_email: 'so@email.test', events: [] }
};

function makeError(kind) {
  if (kind === 'network') { return new TypeError('Failed to fetch'); }
  if (kind === 'timeout') { const e = new Error('The operation was aborted.'); e.name = 'AbortError'; return e; }
  const status = Number(kind.replace('http', ''));
  const e = new Error(`erro ${status}`);
  e.status = status;
  e.payload = { error: `erro ${status}` };
  return e;
}

const RESPONSES = {
  rich: { value: { ok: true, contract: CONTRACTS.rich } },
  minimal: { value: { contract: CONTRACTS.minimal } },
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

// ── DOM simulado ─────────────────────────────────────────────────────────────
function el(extra = {}) { return { value: '', innerHTML: '', textContent: '', checked: false, disabled: false, ...extra }; }
const CONTRACT_REFS = ['commercialContractNumber', 'commercialContractIssueDate', 'commercialContractorAddress', 'commercialContractorRepresentative',
  'commercialContractorRole', 'commercialContractorEmail', 'commercialContractorPhone', 'commercialContractorW1', 'commercialContractorW2',
  'commercialProviderName', 'commercialProviderLegalName', 'commercialProviderCnpj', 'commercialProviderAddress', 'commercialProviderRepresentative',
  'commercialProviderRole', 'commercialProviderEmail', 'commercialProviderPhone', 'commercialProviderWitnesses', 'commercialContractClauses',
  'commercialSignatureName', 'commercialSignatureData', 'commercialEmailTo', 'commercialEmailSubject', 'commercialEmailBody'];
const PANEL_REFS = ['commercialStats', 'commercialSummary', 'commercialAlerts', 'commercialHistory', 'commercialExpiring', 'commercialContractEvents',
  'commercialContractStatus', 'commercialPlanHint'];
const FORM_FIELDS = ['company_id', 'plan_name', 'user_limit', 'addendum_enabled', 'contract_start', 'contract_end', 'license_status', 'active',
  'commercial_notes', 'unit_price_display', 'monthly_value', 'projected_monthly_value'];
const SETTINGS_FIELDS = ['unit_price', 'individual_max', 'start_max', 'business_max', 'corporate_max', 'enterprise_min'];

function buildRefs(shape, opts = {}) {
  if (shape === 'none') { return {}; }
  const refs = {
    commercialCompany: el(),
    commercialForm: { elements: Object.fromEntries(FORM_FIELDS.map((n) => [n, el({ name: n })])) },
    commercialSettingsForm: { elements: Object.fromEntries(SETTINGS_FIELDS.map((n) => [n, el({ name: n })])) },
    commercialSignedFile: el({ files: [{ name: 'assinado <1>.pdf', type: opts.fileType ?? 'application/pdf' }] }),
    commercialFilterActor: el(), commercialFilterDateFrom: el(), commercialFilterDateTo: el(), commercialFilterStatus: el()
  };
  for (const name of [...CONTRACT_REFS, ...PANEL_REFS]) { refs[name] = el(); }
  if (shape === 'partial') {
    for (const name of ['commercialPlanHint', 'commercialContractEvents', 'commercialContractStatus', 'commercialStats', 'commercialExpiring',
      'commercialProviderWitnesses', 'commercialEmailBody', 'commercialSignedFile', 'commercialFilterActor']) { delete refs[name]; }
  }
  return refs;
}

const clone = (value) => (value === undefined ? undefined : JSON.parse(JSON.stringify(value)));

// Fotografia serializada (string) de todos os elementos e do estado comercial.
function snapshot(ctx) {
  const refs = Object.keys(ctx.refs).sort().map((name) => {
    const node = ctx.refs[name];
    return [name, node?.elements ? { elements: node.elements } : node];
  });
  const s = ctx.state;
  return JSON.stringify({ refs, state: { commercialContract: s.commercialContract ?? null, commercialClauseTemplate: s.commercialClauseTemplate,
    commercialFilters: s.commercialFilters, companies: s.companies, selectedCompanyId: s.selectedCompanyId ?? null } });
}

// Intl com os formatadores memorizados por (locale, opções): mesma saída do Intl
// real (formatadores são puros), só sem reconstruí-los a cada chamada.
function memoIntl() {
  const memo = (Ctor) => {
    const cache = new Map();
    function Memo(locales, options) {
      const key = JSON.stringify([locales, options]);
      if (!cache.has(key)) { cache.set(key, new Ctor(locales, options)); }
      return cache.get(key);
    }
    Memo.supportedLocalesOf = (...args) => Ctor.supportedLocalesOf(...args);
    return Memo;
  };
  return { ...Object.fromEntries(Object.getOwnPropertyNames(Intl).map((k) => [k, Intl[k]])),
    NumberFormat: memo(Intl.NumberFormat), DateTimeFormat: memo(Intl.DateTimeFormat) };
}

// ── Contexto ─────────────────────────────────────────────────────────────────
function buildContext(lang) {
  const env = { log: [], deferred: [], opts: {} };
  const ctx = { JSON, Number, String, Object, Array, Promise, URLSearchParams, Symbol, Error, TypeError, RangeError, Math, Intl: memoIntl(), Date, RegExp,
    Set, Map, encodeURIComponent, isNaN };
  env.ctx = ctx;
  ctx.globalThis = ctx;
  ctx.__CATALOG_ACTIVE__ = CATALOGS[lang];
  ctx.__CATALOG_FALLBACK__ = CATALOGS['pt-BR'];
  Object.defineProperty(ctx, '__EPI_APP_STATE__', { get: () => ctx.state, configurable: true });
  Object.defineProperty(ctx, '__EPI_REFS__', { get: () => ctx.refs, configurable: true });
  vm.createContext(ctx);
  const i18n = read('i18n.js');
  vm.runInContext([
    "const FALLBACK = 'pt-BR'; const _pluralCount = Symbol('numeric plural count');",
    `let _active = __CATALOG_ACTIVE__; let _fallback = __CATALOG_FALLBACK__; let _lang = ${JSON.stringify(lang)};`,
    ...['_resolve', '_interpolate', '_message', 't', 'trEpi'].map((n) => extractFunction(i18n, n)),
    'var tr = trEpi;'
  ].join('\n'), ctx);
  for (const rel of ['js/core/constants.js', 'js/modules/shared/business/value-format.js', 'js/views/view-helpers.js',
    'js/modules/shared/ui/company-logo.js', 'js/modules/commercial/business/commercial-rules.js',
    'js/modules/commercial/ui/commercial-presentation.js', 'js/modules/companies/integrations/companies-api.js',
    'js/modules/commercial/integrations/commercial-api.js']) {
    vm.runInContext(read(rel), ctx);
  }
  const log = (...entry) => env.log.push(entry);
  ctx.api = function api(apiPath, options) {
    log('api', apiPath, arguments.length, options === undefined ? 'undefined' : JSON.stringify(options));
    const method = options?.method || 'GET';
    const answer = env.opts.respond(apiPath, method);
    if (answer.deferred) { return new Promise((resolve, reject) => env.deferred.push({ apiPath, resolve, reject })); }
    if (answer.error) { return Promise.reject(makeError(answer.error)); }
    // Cada gravação devolve um contrato diferente (número com a ação): torna visível
    // qualquer troca de ordem entre gravar o estado e renderizar.
    const value = clone(answer.value);
    if (method !== 'GET' && value?.contract) { value.contract.contract_number = `${value.contract.contract_number || ''}#${apiPath.split('/').pop()}`; }
    return Promise.resolve(value);
  };
  ctx.open = (url, target) => { log('open', url, target); return null; };
  ctx.alert = (message) => { log('alert', String(message)); };
  ctx.console = { warn: (...args) => log('warn', String(args[0]), args[1]?.status ?? args[1]?.name ?? null) };
  // Recarga assíncrona de verdade (termina depois de um ciclo): quem não espera por ela aparece no log.
  ctx.loadBootstrap = async () => {
    log('loadBootstrap');
    await Promise.resolve();
    await Promise.resolve();
    if (env.opts.bootstrapMutates) { ctx.state.companies = ctx.state.companies.map((c) => ({ ...c, user_count: Number(c.user_count || 0) + 1 })); }
    log('loadBootstrap:done');
  };
  ctx.canAccessCommercialArea = () => { log('canAccessCommercialArea'); return ctx.state.__canAccess ?? true; };
  ctx.hasPermission = (p) => { log('hasPermission', p); return env.opts.permitted ?? true; };
  ctx.requirePermission = (p) => { log('requirePermission', p); return env.opts.permitted ?? true; };
  ctx.getCommercialSettings = () => ctx.state.commercialSettings || clone(DEFAULT_SETTINGS);
  ctx.formValues = (form) => {
    log('formValues');
    return Object.fromEntries(Object.values(form.elements).filter((f) => f.name && (f.name !== 'addendum_enabled' || f.checked))
      .map((f) => [f.name, f.name === 'addendum_enabled' ? 'on' : String(f.value ?? '')]));
  };
  ctx.platformBrandDisplayName = () => ctx.state.platformBrand?.display_name || 'Sua Empresa';
  ctx.openAndPrintPopup = (html, features) => { log('print', features, html); return env.opts.popupBlocked ? null : {}; };
  ctx.fileToBase64 = async (file) => {
    log('fileToBase64', file.name);
    if (env.opts.fileReadFails) { throw new Error('Falha ao ler arquivo.'); }
    return 'UERGLWJhc2U2NA==';
  };
  let blobs = 0;
  ctx.Blob = function Blob(parts, options) { this.parts = parts; this.type = options?.type; };
  ctx.URL = {
    createObjectURL: (blob) => { blobs += 1; log('blob', blob.type, blob.parts.join('')); return `blob:${blobs}`; },
    revokeObjectURL: (href) => log('revoke', href)
  };
  ctx.document = {
    createElement: (tag) => ({ tag, href: '', download: '', click() { log('click', this.tag, this.href, this.download); } })
  };
  env.reset = (opts) => {
    env.opts = opts;
    env.log = [];
    env.deferred = [];
    env.lastSnapshot = null;
    blobs = 0;
    ctx.EpiI18n = opts.bareI18n ? { lang } : {
      lang,
      formatNumber: (n) => new Intl.NumberFormat(lang).format(n),
      textFor: (node, key, fallback, params, paramKeys) => {
        node.binding = clone({ key, fallback, params, paramKeys });
        return ctx.tr(key, fallback, params);
      }
    };
    ctx.state = {
      user: { id: opts.userId ?? 7, role: opts.role ?? 'master_admin', company_id: opts.userCompany ?? null },
      companies: opts.noCompanies ? [] : clone(COMPANIES),
      companyAuditLogs: opts.noCompanies ? [] : opts.manyLogs ? MANY_LOGS() : clone(LOGS),
      commercialSettings: opts.settings ? clone(opts.settings) : null,
      commercialContract: null,
      commercialClauseTemplate: '',
      commercialFilters: { status: '', date_from: '', date_to: '', actor_name: '' },
      platformBrand: opts.brand ? { display_name: opts.brand } : null,
      __canAccess: opts.canAccess
    };
    ctx.refs = buildRefs(opts.refs, opts);
    return env;
  };
  return env;
}

// "Antes": a cópia literal do app.js. "Atual": o que a página carrega.
const CACHE = new Map();
function cached(kind, lang, setup) {
  const key = `${kind}:${lang}`;
  if (!CACHE.has(key)) { const env = buildContext(lang); setup(env.ctx); CACHE.set(key, env); }
  return CACHE.get(key);
}
function loadOriginal(lang, opts) {
  const env = cached('original', lang, (ctx) => {
    vm.runInContext(read('js/test/fixtures/app-before-ubx-commercial-c3.js.txt'), ctx);
    ctx.__VIEW__ = Object.fromEntries(NAMES.map((n) => [n, ctx[n]]));
  });
  return env.reset(opts);
}
function loadCurrent(lang, opts) {
  const env = cached('current', lang, (ctx) => {
    for (const rel of VIEW_MODULES) { vm.runInContext(read(rel), ctx); }
    ctx.__VIEW__ = ctx.__EPI_COMMERCIAL_VIEW__;
  });
  return env.reset(opts);
}

const flush = () => new Promise((resolve) => setImmediate(resolve));

// Um passo: chamada de função (com exceção síncrona/assíncrona registrada) ou
// uma ação do usuário (`mutate`), seguida da fotografia.
async function step(env, item) {
  const [kind, name, argsOf] = item;
  if (kind === 'mutate') {
    try { name(env.ctx); env.log.push(['mutate', argsOf]); } catch (error) { env.log.push(['mutate-threw', argsOf, String(error)]); }
  } else {
    try {
      const value = await env.ctx.__VIEW__[name](...(argsOf ? argsOf(env) : []));
      env.log.push(['done', name, value === undefined ? 'undefined' : clone(value)]);
    } catch (error) {
      env.log.push(['threw', name, error?.name || 'Error', String(error?.message || error), error?.status ?? null]);
    }
  }
  await flush();
  // Fotografia completa quando algo mudou; senão, a marca de "nada mudou" (comparada do mesmo jeito).
  const snap = snapshot(env.ctx);
  env.log.push(snap === env.lastSnapshot ? ['unchanged'] : ['snapshot', snap]);
  env.lastSnapshot = snap;
}
const call = (name, argsOf) => ['call', name, argsOf];
const mutate = (fn, label) => ['mutate', fn, label];
const event = (env) => [{ preventDefault: () => env.log.push(['preventDefault']) }];
const setField = (ref, value, field) => mutate((ctx) => {
  const node = field ? ctx.refs[ref]?.elements?.[field] : ctx.refs[ref];
  if (node) { node[field === 'addendum_enabled' ? 'checked' : 'value'] = value; }
}, `${ref}${field ? `.${field}` : ''}=${JSON.stringify(value)}`);

// O trecho do renderAll do app.js que toca o Comercial, na mesma ordem.
const RENDER_ALL = [
  call('fillCommercialSettingsForm'),
  mutate((ctx) => { if (ctx.canAccessCommercialArea()) { ctx.__VIEW__.fillCommercialForm(); } }, 'renderAll: if (canAccessCommercialArea()) fillCommercialForm()'),
  call('populateCommercialActors'), call('renderCommercialStats'), call('renderCommercialSummary'), call('renderCommercialAlerts'),
  call('renderCommercialExpiring'), call('renderCommercialHistory')
];
// Troca de idioma (I18N-FULL-V1): só os painéis.
const LANGCHANGE = [call('renderCommercialStats'), call('renderCommercialSummary'), call('renderCommercialAlerts'),
  call('renderCommercialExpiring'), call('renderCommercialHistory')];
const FILTERS = [setField('commercialFilterStatus', 'suspended'), setField('commercialFilterActor', 'Bruno'),
  // Limites do período exatamente nas datas de registros (09-01 e 11-02): pega < × <= e > × >=.
  setField('commercialFilterDateFrom', '2026-09-01'), setField('commercialFilterDateTo', '2026-11-02'), call('syncCommercialFilter')];

const SEQUENCES = {
  renderAll: RENDER_ALL,
  selectCompany: [...RENDER_ALL, setField('commercialCompany', '902'), call('fillCommercialForm', (env) => [env.ctx.refs.commercialCompany?.value]),
    call('renderCommercialHistory'), call('fillCommercialForm', () => ['999']), call('fillCommercialForm', () => ['']),
    call('fillCommercialForm', () => [903]), call('filteredCommercialLogs'), call('filteredCommercialCompanies')],
  preview: [call('fillCommercialForm', () => [901]), setField('commercialForm', 'enterprise', 'plan_name'), call('refreshCommercialPreview'),
    setField('commercialForm', '250', 'user_limit'), call('refreshCommercialPreview'), setField('commercialForm', false, 'addendum_enabled'),
    call('refreshCommercialPreview'), call('refreshCommercialPreview', (env) => [env.ctx.state.companies[1]]),
    setField('commercialForm', '', 'user_limit'), setField('commercialCompany', ''), call('refreshCommercialPreview')],
  filters: [...RENDER_ALL, ...FILTERS, call('formatCommercialFiltersLabel'), call('populateCommercialActors'), call('filteredCommercialCompanies'),
    setField('commercialFilterStatus', ''), setField('commercialFilterActor', ''), call('syncCommercialFilter'), call('formatCommercialFiltersLabel')],
  exports: [...RENDER_ALL, call('exportCommercialHistory'), call('exportCommercialExcel'), call('printCommercialHistory'), ...FILTERS,
    call('exportCommercialHistory'), call('exportCommercialExcel'), call('printCommercialHistory'), call('formatCommercialFiltersLabel')],
  contractPanel: [call('fillCommercialForm', () => [901]), mutate((ctx) => { ctx.state.commercialContract = clone(CONTRACTS.rich); }, 'contrato rico'),
    call('renderCommercialContractPanel'), setField('commercialContractClauses', 'Digitada'), call('resetCommercialContractForm', () => [{ preserveClauses: true }]),
    mutate((ctx) => { ctx.state.commercialContract = clone(CONTRACTS.noClauses); }, 'contrato sem cláusulas'), call('renderCommercialContractPanel'),
    call('buildCommercialContractPayload'), call('resetCommercialContractForm', () => [{ preserveClauses: false }]), call('resetCommercialContractForm'),
    mutate((ctx) => { ctx.state.commercialContract = clone(CONTRACTS.minimal); }, 'contrato mínimo'), call('renderCommercialContractPanel'),
    call('buildCommercialContractPayload'),
    ...['draft', 'generated', 'sent', 'pending_signature', 'signed', 'active', 'closed', 'archived', 'DRAFT', '', null, undefined, 'outro']
      .map((code) => call('contractStatusLabel', () => [code]))],
  contractActions: [call('fillCommercialForm', () => [901]), call('saveCommercialContractManagement'), call('saveCommercialContractDraft', () => [false]),
    call('generateCommercialContract'), call('signCommercialContractAction'), call('uploadSignedCommercialContract'),
    call('sendCommercialContractByEmail'), call('downloadCommercialContractPdf'), call('viewGeneratedCommercialContract'),
    call('downloadGeneratedCommercialContract'), setField('commercialCompany', ''), call('saveCommercialContractDraft', () => [true]),
    call('downloadCommercialContractPdf'), call('viewGeneratedCommercialContract'), call('downloadGeneratedCommercialContract'),
    call('generateCommercialContract'), call('signCommercialContractAction'), call('sendCommercialContractByEmail'),
    mutate((ctx) => { if (ctx.refs.commercialSignedFile) { ctx.refs.commercialSignedFile.files = []; } }, 'sem arquivo'),
    call('uploadSignedCommercialContract')],
  companyActions: [...RENDER_ALL, call('toggleCommercialStatus', () => [901, 'suspend']), call('toggleCommercialStatus', () => ['902', 'reactivate']),
    call('toggleCommercialStatus', () => [999, 'suspend']), setField('commercialForm', 'corporate', 'plan_name'),
    setField('commercialForm', 'Obs "nova"', 'commercial_notes'), call('saveCommercial', event), setField('commercialSettingsForm', '50', 'unit_price'),
    setField('commercialSettingsForm', '', 'business_max'), call('saveCommercialSettings', event), setField('commercialCompany', '777'),
    call('saveCommercial', event)],
  switchContext: [...RENDER_ALL,
    mutate((ctx) => { ctx.state.user = { id: 8, role: 'general_admin', company_id: 902 }; }, 'troca de usuário: admin da 902'), ...RENDER_ALL,
    call('fillCommercialForm'),
    mutate((ctx) => { ctx.state.companies = clone(COMPANIES).slice(2).map((c) => ({ ...c, name: `${c.name} (tenant B)` }));
      ctx.state.companyAuditLogs = clone(LOGS).slice(3); ctx.state.user = { id: 9, role: 'master_admin', company_id: null }; },
    'troca de tenant: outra carteira, master'), ...RENDER_ALL,
    mutate((ctx) => { ctx.state.__canAccess = false; ctx.state.user = { id: 10, role: 'operator', company_id: 903 }; }, 'perfil sem acesso'),
    ...RENDER_ALL, call('loadCommercialContract', () => [903])],
  navigation: [...RENDER_ALL, ...FILTERS,
    // VIEW_FORM_RESET.comercial e VIEW_FILTER_RESET.comercial (limparCamposDeFiltro + syncCommercialFilter).
    call('fillCommercialForm'),
    mutate((ctx) => { for (const r of ['commercialFilterStatus', 'commercialFilterDateFrom', 'commercialFilterDateTo', 'commercialFilterActor']) {
      if (ctx.refs[r]) { ctx.refs[r].value = ''; } } }, 'limparCamposDeFiltro'),
    call('syncCommercialFilter'), ...LANGCHANGE, call('loadCommercialContract', () => [undefined]), call('loadCommercialContract', () => ['902'])]
};

const VARIANTS = [
  {},
  { role: 'general_admin', userCompany: 901, userId: 8 },
  { noCompanies: true },
  { canAccess: false },
  { permitted: false, bootstrapMutates: true },
  { refs: 'none' },
  { refs: 'partial', bareI18n: true },
  { settings: { unit_price: '19.9', plans: { start: { label: `Start ${XSS}`, max_users: 3 }, enterprise: { label: 'Ent', max_users: null },
    custom: { label: 'Custom & "x"', max_users: 7 } } }, brand: 'Marca <i>' },
  { fileReadFails: true, popupBlocked: true, role: 'registry_admin', userCompany: 902 },
  { manyLogs: true, fileType: '' }
];
const API_SEQUENCES = new Set(['contractActions', 'companyActions', 'switchContext', 'navigation']);
// Leituras do contrato: o contrato e o 403 (limpa o painel). Corpo nulo e 5xx na leitura entram nas sequências com gravação.
const READ_RESPONSES = ['rich', 'http403'];
const READ_RESPONSES_API = ['rich', 'nullBody', 'http403', 'http500'];
// Variantes em que as gravações recebem TODAS as respostas; nas demais, as representativas.
const FULL_RESPONSE_VARIANTS = new Set([0, 1, 4, 6]);
const MUTATION_SUBSET = ['rich', 'nullBody', 'http403', 'http500', 'network'];

async function runScenario(load, lang, variant, sequence, getKey, mutationKey) {
  const env = load(lang, { ...variant, respond: (_path, method) => RESPONSES[method === 'GET' ? getKey : mutationKey] });
  for (const item of SEQUENCES[sequence]) { await step(env, item); }
  return env.log;
}

// Concorrência: troca rápida de empresa com as leituras de contrato voltando fora
// de ordem; ações duplicadas antes de a primeira terminar; suspender duas vezes.
async function runConcurrency(load, lang) {
  const out = [];
  {
    const env = load(lang, { respond: () => ({ deferred: true }) });
    env.ctx.__VIEW__.fillCommercialForm(901);
    env.ctx.__VIEW__.fillCommercialForm(902);
    await flush();
    env.deferred[1].resolve({ contract: { ...CONTRACTS.rich, company_id: 902, contract_number: 'CT-902' } });
    await flush();
    env.deferred[0].resolve({ contract: { ...CONTRACTS.rich, company_id: 901 } });
    await flush();
    env.log.push(['final', snapshot(env.ctx)]);
    out.push(env.log);
  }
  for (const name of ['generateCommercialContract', 'saveCommercialContractManagement', 'signCommercialContractAction',
    'sendCommercialContractByEmail', 'uploadSignedCommercialContract']) {
    const env = load(lang, { respond: () => ({ deferred: true }) });
    const a = env.ctx.__VIEW__[name]();
    const b = env.ctx.__VIEW__[name]();
    await flush();
    await flush();
    env.deferred[0]?.reject(makeError('http500'));
    env.deferred[1]?.resolve({ contract: { ...CONTRACTS.minimal, status: name } });
    await Promise.allSettled([a, b]);
    await flush();
    env.log.push(['final', snapshot(env.ctx)]);
    out.push(env.log);
  }
  {
    const env = load(lang, { respond: () => ({ deferred: true }) });
    const a = env.ctx.__VIEW__.toggleCommercialStatus(901, 'suspend');
    const b = env.ctx.__VIEW__.toggleCommercialStatus(901, 'reactivate');
    await flush();
    env.deferred[1].resolve({ ok: true });
    await flush();
    env.deferred[0].resolve({ ok: true });
    await Promise.allSettled([a, b]);
    for (let i = 0; i < 4; i += 1) { await flush(); }
    env.deferred.slice(2).forEach((d) => d.resolve({ contract: CONTRACTS.minimal }));
    await flush();
    env.log.push(['final', snapshot(env.ctx)]);
    out.push(env.log);
  }
  return out;
}

async function compareAll() {
  let compared = 0;
  for (const lang of LOCALES) {
    for (const [index, variant] of VARIANTS.entries()) {
      for (const sequence of Object.keys(SEQUENCES)) {
        // Leitura do contrato (GET) × gravações (POST/PUT): todas as respostas nas gravações, e as leituras
        // representativas (contrato, corpo nulo, 403 que limpa o painel, 500 que só avisa no console).
        const pairs = [...new Set((API_SEQUENCES.has(sequence)
          ? (FULL_RESPONSE_VARIANTS.has(index) ? Object.keys(RESPONSES) : MUTATION_SUBSET).map((k) => [k === 'minimal' ? k : 'rich', k])
            .concat(READ_RESPONSES_API.map((k) => [k, 'rich']))
          : READ_RESPONSES.map((k) => [k, 'rich'])).map((p) => p.join('|')))].map((p) => p.split('|'));
        for (const [getKey, mutationKey] of pairs) {
          const before = await runScenario(loadOriginal, lang, variant, sequence, getKey, mutationKey);
          const after = await runScenario(loadCurrent, lang, variant, sequence, getKey, mutationKey);
          const a = JSON.stringify(after);
          const b = JSON.stringify(before);
          if (a !== b) {
            let i = 0;
            while (i < a.length && a[i] === b[i]) { i += 1; }
            throw new Error(`${lang} ${JSON.stringify(variant).slice(0, 80)} ${sequence} GET=${getKey} POST=${mutationKey}: diverge em …${b.slice(Math.max(0, i - 160), i + 160)}… × …${a.slice(Math.max(0, i - 160), i + 160)}…`);
          }
          compared += 1;
        }
      }
    }
    const before = await runConcurrency(loadOriginal, lang);
    const after = await runConcurrency(loadCurrent, lang);
    if (JSON.stringify(after) !== JSON.stringify(before)) { throw new Error(`${lang}: concorrência diverge`); }
    compared += before.length;
  }
  return compared;
}

module.exports = function ({ testAsync, test, assert, eq }) {
  test('UBX Comercial C3: a fixture é cópia literal das 33 funções de interface comercial', () => {
    const fixture = read('js/test/fixtures/app-before-ubx-commercial-c3.js.txt');
    const found = [...fixture.matchAll(/^(?:async )?function ([A-Za-z_$][\w$]*)\(/gm)].map((m) => m[1]);
    eq(JSON.stringify(found), JSON.stringify(NAMES), 'as 33 funções, na ordem do app.js');
    const asyncFound = [...fixture.matchAll(/^async function ([A-Za-z_$][\w$]*)\(/gm)].map((m) => m[1]);
    eq(JSON.stringify(asyncFound), JSON.stringify(ASYNC_NAMES), 'as 10 assíncronas');
  });

  testAsync('UBX Comercial C3: interface atual × app.js de antes — mesmo DOM, estado e efeitos após cada passo, nos cinco idiomas', async () => {
    const compared = await compareAll();
    assert(compared >= 2000, `cobertura da comparação: ${compared}`);
    console.log(`    C3: ${compared} cenários comparados`);
  });

  testAsync('UBX Comercial C3: valores de referência (o harness enxerga o que importa)', async () => {
    const env = loadCurrent('pt-BR', { respond: (_p, m) => RESPONSES[m === 'GET' ? 'rich' : 'rich'] });
    for (const item of RENDER_ALL) { await step(env, item); }
    const refs = env.ctx.refs;
    assert(refs.commercialStats.innerHTML.includes('stat-card'), 'KPIs renderizados');
    assert(refs.commercialSummary.innerHTML.includes('&lt;img'), 'nome da empresa escapado no resumo');
    assert(!refs.commercialHistory.innerHTML.includes('<img'), 'ator escapado no histórico');
    eq(refs.commercialContractNumber.value, 'CT-5', 'contrato carregado no painel');
    eq(refs.commercialContractStatus.binding.key, 'commercial.panel.contractStatus', 'binding vivo do status');
    const api = env.log.filter((e) => e[0] === 'api');
    eq(JSON.stringify(api), JSON.stringify([['api', '/api/commercial-contract?actor_user_id=7&company_id=901', 1, 'undefined']]), 'uma leitura de contrato');
  });

  test('UBX Comercial C3: os módulos publicam as 23 síncronas e os namespaces congelados, carregam uma vez e respeitam a ordem de carga', () => {
    const ctx = { Object, Set, Map, JSON };
    ctx.globalThis = ctx;
    vm.createContext(ctx);
    const before = Object.keys(ctx);
    for (const rel of VIEW_MODULES) { vm.runInContext(read(rel), ctx); }
    const added = Object.keys(ctx).filter((k) => !before.includes(k)).sort();
    const sync = NAMES.filter((n) => !ASYNC_NAMES.includes(n));
    eq(JSON.stringify(added), JSON.stringify(['__EPI_COMMERCIAL_CONTRACT_VIEW__', '__EPI_COMMERCIAL_VIEW__', '__EPI_MODULE_COMMERCIAL_CONTRACT_VIEW_LOADED__',
      '__EPI_MODULE_COMMERCIAL_VIEW_LOADED__', ...sync].sort()), 'globais publicados');
    const ns = ctx.__EPI_COMMERCIAL_VIEW__;
    const contract = ctx.__EPI_COMMERCIAL_CONTRACT_VIEW__;
    assert(Object.isFrozen(ns) && Object.isFrozen(contract), 'namespaces congelados');
    eq(JSON.stringify(Object.keys(ns)), JSON.stringify(NAMES), 'fachada: as 33 funções, na ordem do app.js');
    eq(JSON.stringify(Object.keys(contract)), JSON.stringify(CONTRACT_NAMES), 'contrato: as 14 funções');
    for (const name of CONTRACT_NAMES) { assert(ns[name] === contract[name], `${name}: fachada === contrato`); }
    for (const name of sync) { assert(ctx[name] === ns[name], `${name}: global === namespace`); }
    for (const name of ASYNC_NAMES) { assert(!(name in ctx), `${name} continua fora de globalThis (era de bloco)`); }
    for (const rel of VIEW_MODULES) { vm.runInContext(read(rel), ctx); }
    assert(ctx.__EPI_COMMERCIAL_VIEW__ === ns && ctx.__EPI_COMMERCIAL_CONTRACT_VIEW__ === contract, 'segunda carga não republica');

    for (const rel of VIEW_MODULES) {
      const module = read(rel);
      assert(!/(?<![.\w$])api\(|fetch\(|XMLHttpRequest|\/api\//.test(module), `${rel}: sem HTTP direto (só a C2 e o updateCompany de Empresas)`);
      assert(!/addEventListener|bindAppListener|safeOn\(/.test(module), `${rel}: sem listeners (a ligação continua no app.js; nenhum duplicado)`);
      assert(!/\blet\s+(state|refs)\b|__EPI_APP_STATE__\s*=|__EPI_REFS__\s*=/.test(module), `${rel}: sem estado paralelo (state/refs são os do app.js)`);
    }
    assert(!/__EPI_COMMERCIAL_VIEW__|commercial-view\.js/.test(read(VIEW_MODULES[0]).replace(/^\s*\/\/.*$/gm, '')), 'o contrato não depende da tela (sem ciclo)');

    const app = read('app.js');
    for (const name of NAMES) {
      assert(!new RegExp(`^\\s*(?:async\\s+)?function ${name}\\(`, 'm').test(app), `${name} não ficou duplicada no app.js`);
    }
    for (const name of ASYNC_NAMES.filter((n) => !['loadCommercialContract', 'saveCommercialContractDraft'].includes(n))) {
      assert(app.includes(`__EPI_COMMERCIAL_VIEW__.${name}`), `${name}: o app.js liga pelo namespace`);
    }
    const order = [...read('views/_scripts.html').matchAll(/<script[^>]+src="([^"?]+)/g)].map((m) => m[1]);
    const i = (src) => order.indexOf(src);
    const iContract = i('/js/modules/commercial/ui/commercial-contract-view.js');
    const iView = i('/js/modules/commercial/ui/commercial-view.js');
    assert(iContract > i('/js/modules/commercial/integrations/commercial-api.js') && iContract > i('/js/views/view-helpers.js')
      && iView > iContract && iView > i('/js/modules/commercial/ui/commercial-presentation.js') && iView < i('/app.js'),
    `ordem de carga: contrato ${iContract}, comercial ${iView}, app ${i('/app.js')}`);
    for (const rel of VIEW_MODULES) { eq(order.filter((src) => src === `/${rel}`).length, 1, `${rel} carregado uma vez`); }
  });
};
