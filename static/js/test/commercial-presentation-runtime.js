'use strict';
// UBX Comercial, fatia C1 — caracterização da apresentação comercial pura.
//
// As 13 funções (planEntries, planLabel, planOptionMarkup, planHintText,
// commercialRiskMeta, commercialActions, commercialAlertTone,
// renderCommercialSummaryCard, renderCommercialAlertCard,
// renderCommercialExpiringCard, formatCommercialAuditDetails,
// renderCommercialHistoryItem, formatCommercialDetails) rodam num contexto
// isolado com as dependências REAIS da página:
//   - tr: o motor do static/i18n.js (_resolve/_message/_interpolate/t/trEpi),
//     com os cinco catálogos de static/i18n/ e pt-BR como fallback;
//   - escapeHtml/formatDate: static/js/views/view-helpers.js;
//   - formatCurrency: static/js/modules/shared/business/value-format.js;
//   - companyLogoMarkup: static/js/modules/shared/ui/company-logo.js, com o
//     DEFAULT_COMPANY_LOGO de static/js/core/constants.js.
// Só hasPermission e getCommercialSettings (estado da sessão) são controlados
// pelo teste.
//
// A referência "antes" é a cópia literal do app.js
// (fixtures/app-before-ubx-commercial-c1.js.txt). A implementação "atual" é
// comparada com ela entrada a entrada, nos cinco idiomas, inclusive exceções.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const STATIC = path.resolve(__dirname, '..', '..');
const LOCALES = ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO'];
const NAMES = ['planEntries', 'planLabel', 'planOptionMarkup', 'planHintText', 'commercialRiskMeta', 'commercialActions',
  'commercialAlertTone', 'renderCommercialSummaryCard', 'renderCommercialAlertCard', 'renderCommercialExpiringCard',
  'formatCommercialAuditDetails', 'renderCommercialHistoryItem', 'formatCommercialDetails'];

const read = (rel) => fs.readFileSync(path.join(STATIC, rel), 'utf8');

// Extrai `function nome(...) { ... }` do código-fonte contando chaves.
function extractFunction(source, name) {
  const start = source.indexOf(`function ${name}(`);
  if (start < 0) { throw new Error(`função ${name} não encontrada`); }
  let depth = 0;
  for (let i = source.indexOf('{', start); i < source.length; i += 1) {
    if (source[i] === '{') { depth += 1; }
    if (source[i] === '}') { depth -= 1; if (depth === 0) { return source.slice(start, i + 1); } }
  }
  throw new Error(`função ${name} sem fim`);
}

const CATALOGS = Object.fromEntries(LOCALES.map((l) => [l, JSON.parse(read(`i18n/${l}.json`))]));

// Contexto com as dependências reais; `lang` escolhe o catálogo ativo.
function buildContext(lang, { canUpdate = true, settings = null } = {}) {
  const ctx = { String, Number, Object, Array, JSON, Intl, Date, Symbol, RegExp, Error, encodeURIComponent };
  ctx.globalThis = ctx;
  ctx.EpiI18n = { lang };
  ctx.__CATALOG_ACTIVE__ = CATALOGS[lang];
  ctx.__CATALOG_FALLBACK__ = CATALOGS['pt-BR'];
  vm.createContext(ctx);
  vm.runInContext(read('js/core/constants.js'), ctx);
  vm.runInContext(read('js/modules/shared/business/value-format.js'), ctx);
  vm.runInContext(read('js/modules/shared/ui/company-logo.js'), ctx);
  const i18n = read('i18n.js');
  const helpers = read('js/views/view-helpers.js');
  vm.runInContext([
    "const FALLBACK = 'pt-BR'; const _pluralCount = Symbol('numeric plural count');",
    `let _active = __CATALOG_ACTIVE__; let _fallback = __CATALOG_FALLBACK__; let _lang = ${JSON.stringify(lang)};`,
    ...['_resolve', '_interpolate', '_message', 't', 'trEpi'].map((n) => extractFunction(i18n, n)),
    'var tr = trEpi;',
    ...['escapeHtml', 'displayLocale', 'formatDate'].map((n) => extractFunction(helpers, n)),
    'this.escapeHtml = escapeHtml; this.formatDate = formatDate;'
  ].join('\n'), ctx);
  ctx.hasPermission = (perm) => (perm === 'companies:update' ? canUpdate : false);
  ctx.getCommercialSettings = () => settings || ctx.DEFAULT_SETTINGS;
  ctx.DEFAULT_SETTINGS = {
    unit_price: 42,
    plans: {
      individual: { label: 'Individual', min_users: 1, max_users: 1 },
      start: { label: 'Start', min_users: 1, max_users: 10 },
      business: { label: 'Business', min_users: 11, max_users: 25 },
      corporate: { label: 'Corporate', min_users: 26, max_users: 100 },
      enterprise: { label: 'Enterprise', min_users: 101, max_users: null }
    }
  };
  return ctx;
}

// "Antes": cópia literal do app.js. Declarações de função no contexto viram
// globais, como no app.js (Annex B).
function loadOriginal(lang, options) {
  const ctx = buildContext(lang, options);
  vm.runInContext(read('js/test/fixtures/app-before-ubx-commercial-c1.js.txt'), ctx);
  return ctx;
}

// "Atual": as mesmas 13 funções lidas do static/app.js de hoje.
function loadCurrent(lang, options) {
  const ctx = buildContext(lang, options);
  const app = read('app.js');
  vm.runInContext(NAMES.map((n) => extractFunction(app, n)).join('\n\n'), ctx);
  return ctx;
}

function outcome(fn) {
  try { return { ok: JSON.stringify(fn()) }; } catch (error) { return { error: `${error.name}: ${error.message}` }; }
}

const COMPANIES = (() => {
  const out = [];
  const base = { id: 7, name: 'ACME', user_count: 4, user_limit: 10, monthly_value: 168, projected_monthly_value: 420, plan_name: 'start', contract_end: '2026-12-31' };
  for (const active of [1, 0, '1', '0', undefined]) {
    for (const license_status of ['active', 'trial', 'expired', 'suspended', undefined]) {
      for (const limit_reached of [1, 0, '1']) {
        for (const near_limit of [true, false]) {
          out.push({ ...base, active, license_status, limit_reached, near_limit, license_status_label: license_status ? `Rótulo ${license_status}` : undefined });
        }
      }
    }
  }
  out.push({ ...base, id: '9" onclick="x', name: 'Ação & Cia <b>"x"</b> \'y\'', plan_name: 'enterprise', active: 1, license_status: 'active', limit_reached: 0, near_limit: false });
  out.push({ ...base, name: '<img src=x onerror=alert(1)>', plan_name: '<script>', monthly_value: 0, projected_monthly_value: null, user_count: '<i>', user_limit: 0, active: 1 });
  out.push({ ...base, plan_name: 'inexistente', monthly_value: 1234567.891, active: 1, logo_type: 'data:image/png;base64,AAA=' });
  out.push({ ...base, plan_name: undefined, monthly_value: undefined, contract_end: 'invalid', active: 1 });
  return out;
})();

const DETAILS = [undefined, null, [], [{ field: 'Plano', before: 'Start', after: 'Business' }],
  [{ field: '<b>campo</b>', before: '', after: null }, { field: 'Valor', before: '"1"', after: "'2'" }]];

const HISTORY = [
  { company_name: 'ACME', action_label: 'Contrato atualizado', actor_name: 'Ana', summary: 'Resumo', created_at: '2026-10-01T12:34:00Z', details: DETAILS[3] },
  { company_name: '<b>X</b>', action_label: '<i>a</i>', actor_name: '"Bob"', summary: '<script>', created_at: '2026-01-02', details: DETAILS[4] },
  { company_name: 'Sem data', action_label: 'Evento', actor_name: 'Ana', summary: '', created_at: 'não é data', details: null }
];

const SETTINGS = [null,
  { unit_price: 10, plans: { start: { label: 'Start <b>', min_users: 1, max_users: 10 }, enterprise: { label: 'Ent', min_users: 1, max_users: null }, '"quote': { label: 'Q', min_users: 1, max_users: 2 } } },
  { unit_price: 10, plans: {} },
  { unit_price: 10 }];

// Executa todas as entradas numa implementação e devolve a lista de resultados.
function runMatrix(load, lang) {
  const results = [];
  for (const canUpdate of [true, false]) {
    for (const settings of SETTINGS) {
      const ctx = load(lang, { canUpdate, settings });
      results.push(outcome(() => ctx.planEntries()));
      for (const key of ['start', 'enterprise', 'individual', 'inexistente', '', undefined, '"quote']) {
        results.push(outcome(() => ctx.planLabel(key)));
        results.push(outcome(() => ctx.planOptionMarkup(key)));
        for (const addendum of [false, true, 'sim', 0]) { results.push(outcome(() => ctx.planHintText(key, addendum))); }
      }
      results.push(outcome(() => ctx.planOptionMarkup()));
      results.push(outcome(() => ctx.planHintText('start')));
      // Os cartões só leem os parâmetros pelo planLabel: dois cenários bastam.
      if (settings !== null && settings !== SETTINGS[1]) { continue; }
      for (const company of COMPANIES) {
        results.push(outcome(() => ctx.commercialRiskMeta(company)));
        results.push(outcome(() => ctx.commercialActions(company)));
        results.push(outcome(() => ctx.commercialAlertTone(company)));
        results.push(outcome(() => ctx.renderCommercialSummaryCard(company)));
        results.push(outcome(() => ctx.renderCommercialAlertCard(company)));
        for (const days of [0, 3, 7, 8, 30]) { results.push(outcome(() => ctx.renderCommercialExpiringCard({ item: company, days }))); }
      }
      for (const details of DETAILS) {
        results.push(outcome(() => ctx.formatCommercialAuditDetails(details)));
        results.push(outcome(() => ctx.formatCommercialDetails(details)));
        results.push(outcome(() => ctx.formatCommercialDetails(details, ' | ')));
      }
      for (const item of HISTORY) { results.push(outcome(() => ctx.renderCommercialHistoryItem(item))); }
      results.push(outcome(() => ctx.commercialRiskMeta(undefined)));
      results.push(outcome(() => ctx.renderCommercialExpiringCard({})));
    }
  }
  return results;
}

module.exports = function ({ test, assert, eq }) {
  test('UBX Comercial C1: a fixture é cópia literal das 13 funções do app.js de antes da extração', () => {
    const fixture = read('js/test/fixtures/app-before-ubx-commercial-c1.js.txt');
    const found = [...fixture.matchAll(/^function ([A-Za-z_$][\w$]*)\(/gm)].map((m) => m[1]);
    eq(JSON.stringify(found), JSON.stringify(NAMES), 'as 13 funções, na ordem do app.js');
    const app = read('app.js');
    for (const name of NAMES) {
      eq(extractFunction(fixture, name), extractFunction(app, name), `${name}: texto idêntico ao do app.js`);
    }
  });

  test('UBX Comercial C1: valores de referência em pt-BR (comportamento atual fixado)', () => {
    const ctx = loadCurrent('pt-BR', { canUpdate: true });
    eq(JSON.stringify(ctx.commercialRiskMeta({ active: 0 })), JSON.stringify({ label: 'Empresa inativa', tone: 'inactive' }), 'risco: inativa');
    eq(JSON.stringify(ctx.commercialRiskMeta({ active: 1, license_status: 'active', limit_reached: 0, near_limit: true })),
      JSON.stringify({ label: 'Próxima do limite', tone: 'warning' }), 'risco: próxima do limite');
    eq(ctx.commercialAlertTone({ limit_reached: 1 }), 'danger', 'tom: limite');
    eq(ctx.commercialAlertTone({ license_status: 'suspended' }), 'warning', 'tom: suspensa');
    eq(loadCurrent('pt-BR', { canUpdate: false }).commercialActions({ id: 1 }), '', 'sem companies:update não há ações');
    assert(ctx.commercialActions({ id: 1, active: 1, license_status: 'active' }).includes('data-commercial-mode="suspend"'), 'ação suspender');
    assert(ctx.commercialActions({ id: 1, active: 0 }).includes('data-commercial-mode="reactivate"'), 'ação reativar');
    eq(ctx.planLabel('enterprise'), 'Enterprise', 'rótulo do plano');
    eq(ctx.planLabel('desconhecido'), 'desconhecido', 'plano desconhecido devolve a chave');
    eq(ctx.planHintText('inexistente'), '', 'dica de plano inexistente');
    eq(ctx.formatCommercialAuditDetails([]), '', 'sem detalhes');
    eq(ctx.formatCommercialDetails([{ field: 'a', before: '', after: 'b' }]), 'a: - -> b', 'detalhes em texto');
    const card = ctx.renderCommercialSummaryCard({ id: 1, name: '<b>X</b>', user_count: 1, user_limit: 2, plan_name: 'start', active: 1 });
    assert(card.includes('&lt;b&gt;X&lt;/b&gt;') && !card.includes('<b>X</b>'), 'nome da empresa escapado no cartão');
  });

  test('UBX Comercial C1: implementação atual × app.js de antes, entrada a entrada, nos cinco idiomas', () => {
    let compared = 0;
    for (const lang of LOCALES) {
      const before = runMatrix(loadOriginal, lang);
      const after = runMatrix(loadCurrent, lang);
      eq(after.length, before.length, `${lang}: mesmo número de casos`);
      for (let i = 0; i < before.length; i += 1) {
        eq(JSON.stringify(after[i]), JSON.stringify(before[i]), `${lang}: caso ${i}`);
        compared += 1;
      }
    }
    assert(compared >= 10000, `cobertura da comparação: ${compared}`);
  });

  test('UBX Comercial C1: a apresentação muda com o idioma (os cinco catálogos são usados de fato)', () => {
    const company = { id: 1, name: 'ACME', active: 0, plan_name: 'start' };
    const labels = LOCALES.map((lang) => loadCurrent(lang).commercialRiskMeta(company).label);
    eq(new Set(labels).size, LOCALES.length, `rótulos distintos por idioma: ${labels.join(' | ')}`);
    for (const lang of LOCALES) {
      const html = loadCurrent(lang).renderCommercialExpiringCard({ item: company, days: 3 });
      assert(!/commercial\.[a-zA-Z]/.test(html), `${lang}: nenhuma chave crua no cartão`);
    }
  });
};
