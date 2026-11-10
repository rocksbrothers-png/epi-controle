'use strict';
// F1 — Ficha 360° de EPI: regras de apresentação do resumo e integração HTTP.
//
// Carrega os módulos REAIS (business/summary e integrations/api) num contexto
// vm isolado. A interface (DOM) é coberta no navegador real por
// scripts/browser/ubx_employee_ppe_360.py, nos 5 idiomas.
const fs = require('fs'), path = require('path'), vm = require('vm');

const JS_ROOT = path.resolve(__dirname, '..');
const MODULES = [
  'modules/employee-ppe-360/business/employee-ppe-360-summary.js',
  'modules/employee-ppe-360/integrations/employee-ppe-360-api.js'
];

function load(api) {
  const sandbox = { Promise, JSON, Object, Array, String, Number, Error, Map, Set, Boolean, encodeURIComponent };
  sandbox.globalThis = sandbox;
  sandbox.api = api || (async () => ({}));
  vm.createContext(sandbox);
  for (const rel of MODULES) {
    vm.runInContext(fs.readFileSync(path.join(JS_ROOT, rel), 'utf-8'), sandbox, { filename: rel });
  }
  return sandbox;
}

module.exports = function register({ test, testAsync, assert, eq }) {
  const s = load().__EPI_EMPLOYEE_PPE_360_SUMMARY__;

  test('F1 Ficha 360: Admin Master e perfis sem employees:view não veem a entrada (DF-3)', () => {
    assert(s.canOpen({ role: 'general_admin' }, ['employees:view']), 'Admin Geral abre');
    assert(s.canOpen({ role: 'user' }, ['employees:view']), 'Gestor de EPI abre');
    assert(!s.canOpen({ role: 'master_admin' }, ['employees:view']), 'Admin Master bloqueado');
    assert(!s.canOpen({ role: 'buyer' }, ['deliveries:view']), 'sem employees:view');
    assert(!s.canOpen(null, ['employees:view']), 'sem usuário');
  });

  test('F1 Ficha 360: custos só aparecem com finance:view', () => {
    assert(s.canSeeFinance(['finance:view']));
    assert(!s.canSeeFinance(['employees:view']));
    eq(s.futureBlocks('complementary', []).map((b) => b.id).includes('consumption'), false);
    eq(s.futureBlocks('complementary', ['finance:view']).map((b) => b.id).includes('consumption'), true);
    eq(s.futureBlocks('central', []).map((b) => b.id).join(','), 'active-epis,requests,deliveries');
  });

  test('F1 Ficha 360: pendências por estado, na ordem da máquina, sem somar o que não veio', () => {
    const view = s.pendingView({ total: 5, by_status: [
      { code: 'WAITING_STOCK', count: 1 }, { code: 'SUBMITTED', count: 3 }, { code: 'XYZ', count: 1 },
      { code: 'APPROVED', count: 0 }, { code: 'UNDER_REVIEW', count: 'x' }
    ] });
    eq(JSON.stringify(view.items), JSON.stringify([
      { code: 'SUBMITTED', count: 3 }, { code: 'WAITING_STOCK', count: 1 }, { code: 'UNKNOWN', count: 1 }
    ]));
    eq(view.total, 5);
    eq(view.consistent, true);
    eq(view.empty, false);
    const empty = s.pendingView({ total: 0, by_status: [] });
    eq(empty.empty, true);
    eq(s.pendingView({ total: 9, by_status: [{ code: 'SUBMITTED', count: 1 }] }).consistent, false);
  });

  test('F1 Ficha 360: próxima troca usa a data gravada e marca vencida', () => {
    const view = s.nextReplacementView({ date: '2026-01-15', epi_name: 'Luva', overdue_count: 2 }, '2026-03-01');
    eq(view.empty, false); eq(view.isOverdue, true); eq(view.overdueCount, 2); eq(view.epiName, 'Luva');
    eq(s.nextReplacementView({ date: '2026-12-01', overdue_count: 0 }, '2026-03-01').isOverdue, false);
    eq(s.nextReplacementView(null, '2026-03-01').empty, true);
    eq(s.nextReplacementView({ date: '15/01/2026' }, '2026-03-01').empty, true, 'data fora do ISO não vira data');
  });

  test('F1 Ficha 360: em uso e vazio explícito', () => {
    const view = s.inUseView({ units: 4, products: 3, categories: 2, uncategorized_products: 1 });
    eq(view.units, 4); eq(view.uncategorized, 1); eq(view.empty, false);
    eq(s.inUseView({}).empty, true);
  });

  test('F1 Ficha 360: responsáveis — só papéis previstos e nomes não vazios (DF-1)', () => {
    const groups = s.responsibleGroups({
      unit: [{ role: 'admin', name: 'Lucas' }, { role: 'buyer', name: 'Comprador' }, { role: 'user', name: '  ' }],
      company: [{ role: 'general_admin', name: 'Gabi' }, { role: 'master_admin', name: 'Mestre' }]
    });
    eq(JSON.stringify(groups.unit), JSON.stringify([{ role: 'admin', name: 'Lucas' }]));
    eq(JSON.stringify(groups.company), JSON.stringify([{ role: 'general_admin', name: 'Gabi' }]));
    eq(s.responsibleGroups(null).empty, true);
  });

  test('F1 Ficha 360: terceirizado — empresa, CNPJ e contrato quando existem', () => {
    eq(s.contractedView(null), null);
    const view = s.contractedView({ outsourced_company: { name: 'Terceira', cnpj: '44' },
      contract: { ref: 'CT-7', start_date: '2026-01-01', end_date: '2026-12-31' } });
    eq(view.companyName, 'Terceira'); eq(view.contractRef, 'CT-7'); eq(view.contractEnd, '2026-12-31'); eq(view.hasContract, true);
    eq(s.contractedView({ outsourced_company: null, contract: null, origin_name: 'Origem' }).hasContract, false);
  });

  testAsync('F1 Ficha 360: integração — uma rota, envelope de sucesso e de erro', async () => {
    const calls = [];
    let mode = 'ok';
    const sandbox = load(async (url) => {
      calls.push(url);
      if (mode === 'ok') { return { employee: { id: 31 } }; }
      if (mode === 'coded') { const e = new Error('x'); e.code = 'EMPLOYEE_NOT_FOUND'; throw e; }
      throw new Error('rede');
    });
    const api = sandbox.__EPI_EMPLOYEE_PPE_360_API__;
    eq(JSON.stringify(await api.loadSummary(31, 7)), JSON.stringify({ ok: true, data: { employee: { id: 31 } } }));
    eq(calls[0], '/api/employees/31/ppe-360/summary?actor_user_id=7');
    mode = 'coded';
    eq(JSON.stringify(await api.loadSummary(31, 7)), JSON.stringify({ ok: false, error: { code: 'EMPLOYEE_NOT_FOUND' } }));
    mode = 'network';
    eq(JSON.stringify(await api.loadSummary(31, 7)), JSON.stringify({ ok: false, error: { code: 'REQUEST_FAILED' } }));
    eq(calls.length, 3);
  });
};
