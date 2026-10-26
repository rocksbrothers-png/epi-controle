'use strict';
// FIX-NAV-REFRESH-V1 — regressões do fluxo "gravar → atualizar a tela":
//   1. arquivar/desarquivar/excluir EPI e Unidade e transferir colaborador
//      recarregam o bootstrap mantendo a tela (preserveView);
//   2. a mesma lista pedida duas vezes na mesma atualização vira uma requisição,
//      mas nunca reaproveita uma requisição iniciada antes da gravação;
//   3. gravação concluída + atualização com falha: aviso verdadeiro, nenhuma
//      mensagem de falha da gravação, nenhuma segunda gravação; clique duplo
//      grava uma vez.
// Exercita as funções REAIS do app.js (fatiadas) e o módulo real
// modules/shared/ui/mutation-flow.js.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const source = fs.readFileSync(path.resolve(__dirname, '../../app.js'), 'utf8');
const flowSource = fs.readFileSync(path.resolve(__dirname, '../modules/shared/ui/mutation-flow.js'), 'utf8');

function slice(name) {
  const lines = source.split('\n');
  const start = lines.findIndex((line) => new RegExp(`^(?:async )?function ${name}\\(`).test(line));
  if (start < 0) { throw new Error(`missing ${name}`); }
  let end = start;
  while (!/^}/.test(lines[end])) { end++; }
  return lines.slice(start, end + 1).join('\n');
}

function sliceConst(name) {
  const lines = source.split('\n');
  const start = lines.findIndex((line) => line.startsWith(`const ${name} = {`));
  let end = start;
  while (!/^};/.test(lines[end])) { end++; }
  return lines.slice(start, end + 1).join('\n').replace(/^const /, 'var ');
}

const REFRESH_FAILED = 'mutation.refreshFailed';

function environment({ failBootstrap = false, failMutation = false } = {}) {
  const calls = [];
  const record = { id: 6, name: 'QA', legal_name: 'QA' };
  const ctx = vm.createContext({
    state: {
      user: { id: 7, role: 'registry_admin', company_id: 901 },
      units: [record], archivedUnits: [record], epis: [record], archivedEpis: [record],
      employees: [record], archivedEmployees: [record], outsourcedCompanies: [record],
      archivedOutsourcedCompanies: [record], archivedOutsourcedEmployees: [record]
    },
    UNIT_PURGE_RECORD_LABELS: { deliveries: 'Entregas' },
    requirePermission: () => true, hasPermission: () => true, actorQuery: () => 'actor_user_id=7',
    reportNonCriticalError: () => calls.push(['reportNonCritical']),
    api: async (url, options) => {
      const method = (options || {}).method || 'GET';
      calls.push(['api', method, url]);
      await Promise.resolve();
      if (failMutation && method === 'POST' && /\/(archive|restore|purge-confirm)$|movements$/.test(url)) {
        throw new Error('QA gravação recusada');
      }
      return { records: {}, units: [], epis: [] };
    },
    loadBootstrap: async (options) => {
      calls.push(['bootstrap', options || null]);
      await Promise.resolve();
      if (failBootstrap) { throw new Error('QA bootstrap 500'); }
    },
    loadOutsourcedCompanies: async () => calls.push(['companies']),
    renderArchivedUnits: () => calls.push(['renderUnits']),
    renderArchivedRecords: (kind) => calls.push(['renderArchived', kind]),
    formValues: () => ({ employee_id: '31', target_unit_id: '6' }),
    tr: (key, fallback) => (key === REFRESH_FAILED ? REFRESH_FAILED : fallback),
    confirmDestructive: async () => true, prompt: () => 'QA justificativa',
    showToast: (message, type) => calls.push(['toast', type, message]),
    alert: (message) => calls.push(['alert', message])
  });
  ctx.globalThis = ctx;
  vm.runInContext(flowSource, ctx);
  vm.runInContext([sliceConst('ARCHIVAL_ENTITIES'), slice('_epiArchivalPreflight'), slice('archiveEntityRecord'),
    slice('restoreArchivedRecord'), slice('purgeArchivedRecord'), slice('loadArchivedRecords'),
    slice('archiveUnit'), slice('restoreArchivedUnit'), slice('purgeArchivedUnit'), slice('loadArchivedUnits'),
    slice('saveEmployeeMovement')].join('\n'), ctx);
  return { ctx, calls };
}

const OPERATIONS = [
  ['archiveEntityRecord', ['epi', 6], '/api/epis/6/archive'],
  ['restoreArchivedRecord', ['epi', 6], '/api/epis/6/restore'],
  ['purgeArchivedRecord', ['epi', 6], '/api/epis/6/purge-confirm'],
  ['archiveUnit', [6], '/api/units/6/archive'],
  ['restoreArchivedUnit', [6], '/api/units/6/restore'],
  ['purgeArchivedUnit', [6], '/api/units/6/purge-confirm'],
  ['archiveEntityRecord', ['employee', 6], '/api/employees/6/archive'],
  ['restoreArchivedRecord', ['outsourcedEmployee', 6], '/api/employees/6/restore']
];

function form() {
  return { reset() {}, dataset: {} };
}

module.exports = function ({ testAsync, test, assert, eq }) {
  test('FIX-NAV-REFRESH mutation-flow publica as três funções e o namespace congelado', () => {
    const { ctx } = environment();
    for (const name of ['runExclusiveMutation', 'coalesceLoad', 'refreshAfterMutation']) {
      eq(typeof ctx[name], 'function', name);
    }
    assert(Object.isFrozen(ctx.__EPI_MUTATION_FLOW__), 'namespace congelado');
  });

  testAsync('FIX-NAV-REFRESH runExclusiveMutation: execução única por chave e liberação após erro', async () => {
    const { ctx } = environment();
    let runs = 0;
    let release;
    const first = ctx.runExclusiveMutation('k', () => new Promise((resolve) => { runs++; release = resolve; }));
    eq(await ctx.runExclusiveMutation('k', async () => { runs++; }), undefined, 'segunda chamada ignorada');
    release('ok');
    eq(await first, 'ok');
    let threw = false;
    try { await ctx.runExclusiveMutation('k', async () => { runs++; throw new Error('x'); }); } catch { threw = true; }
    assert(threw, 'erro propaga');
    await ctx.runExclusiveMutation('k', async () => { runs++; });
    eq(runs, 3, 'chave liberada depois de sucesso e de erro');
  });

  testAsync('FIX-NAV-REFRESH coalesceLoad: transparente fora da atualização, uma requisição dentro dela', async () => {
    const { ctx } = environment();
    let loads = 0;
    const load = async () => { loads++; };
    await Promise.all([ctx.coalesceLoad('a', load), ctx.coalesceLoad('a', load)]);
    eq(loads, 2, 'fora da janela não coalesce (requisição antiga nunca é reaproveitada)');
    loads = 0;
    await ctx.refreshAfterMutation(async () => {
      const first = ctx.coalesceLoad('a', load);
      await Promise.all([first, ctx.coalesceLoad('a', load), ctx.coalesceLoad('b', load)]);
    });
    eq(loads, 2, 'dentro da janela: uma por chave');
    loads = 0;
    await ctx.coalesceLoad('a', load);
    eq(loads, 1, 'janela fechada ao terminar');
  });

  testAsync('FIX-NAV-REFRESH refreshAfterMutation: falha vira aviso verdadeiro; 401/403 não duplicam aviso', async () => {
    const { ctx, calls } = environment();
    eq(await ctx.refreshAfterMutation(async () => { throw new Error('500'); }), false);
    assert(calls.some(([c, type, msg]) => c === 'toast' && type === 'warning' && msg === REFRESH_FAILED), 'aviso de atualização');
    calls.length = 0;
    const denied = Object.assign(new Error('forbidden'), { status: 403 });
    eq(await ctx.refreshAfterMutation(async () => { throw denied; }), false);
    assert(!calls.some(([c]) => c === 'toast'), 'sessão encerrada pelo bootstrap: sem aviso extra');
    eq(await ctx.refreshAfterMutation(async () => {}), true);
  });

  for (const [name, args, postPath] of OPERATIONS) {
    testAsync(`FIX-NAV-REFRESH ${name}(${args.join(',')}) mantém a tela e pede a lista uma vez`, async () => {
      const { ctx, calls } = environment();
      await ctx[name](...args);
      const posts = calls.filter(([c, method, url]) => c === 'api' && method === 'POST' && url === postPath);
      eq(posts.length, 1, 'uma gravação');
      const boot = calls.find(([c]) => c === 'bootstrap');
      assert(boot && boot[1] && boot[1].preserveView === true, 'bootstrap com preserveView');
      const listPath = name.includes('Unit') ? '/api/units/archived' : '/archived?';
      const listGets = calls.filter(([c, method, url]) => c === 'api' && method === 'GET' && url.includes(listPath));
      eq(listGets.length, 1, 'lista de arquivados pedida uma vez');
    });

    testAsync(`FIX-NAV-REFRESH ${name}(${args.join(',')}): gravação ok + atualização falha → aviso verdadeiro`, async () => {
      const { ctx, calls } = environment({ failBootstrap: true });
      await ctx[name](...args);
      eq(calls.filter(([c, method, url]) => c === 'api' && method === 'POST' && url === postPath).length, 1, 'sem repetir a gravação');
      assert(calls.some(([c, type, msg]) => c === 'toast' && type === 'warning' && msg === REFRESH_FAILED), 'aviso de atualização');
      assert(!calls.some(([c, type]) => c === 'toast' && type === 'error'), 'nenhum toast de erro');
      assert(!calls.some(([c, msg]) => c === 'alert' && /QA bootstrap/.test(msg)), 'erro cru da recarga não exibido');
    });

    testAsync(`FIX-NAV-REFRESH ${name}(${args.join(',')}): gravação recusada → erro, sem atualização`, async () => {
      const { ctx, calls } = environment({ failMutation: true });
      await ctx[name](...args);
      assert(calls.some(([c, a, b]) => (c === 'alert' && /QA gravação/.test(a)) || (c === 'toast' && a === 'error' && /QA gravação/.test(b))),
        'erro da gravação exibido');
      assert(!calls.some(([c]) => c === 'bootstrap'), 'sem bootstrap');
      assert(!calls.some(([c, type, msg]) => c === 'toast' && msg === REFRESH_FAILED), 'sem aviso de atualização');
    });

    testAsync(`FIX-NAV-REFRESH ${name}(${args.join(',')}): clique duplo grava uma vez`, async () => {
      const { ctx, calls } = environment();
      await Promise.all([ctx[name](...args), ctx[name](...args)]);
      eq(calls.filter(([c, method, url]) => c === 'api' && method === 'POST' && url === postPath).length, 1);
    });
  }

  testAsync('FIX-NAV-REFRESH saveEmployeeMovement: mantém a tela, aviso verdadeiro e envio único', async () => {
    let env = environment();
    await Promise.all([env.ctx.saveEmployeeMovement({ preventDefault() {}, target: form() }),
      env.ctx.saveEmployeeMovement({ preventDefault() {}, target: form() })]);
    eq(env.calls.filter(([c, m, u]) => c === 'api' && m === 'POST' && u === '/api/employee-unit-movements').length, 1, 'envio único');
    const boot = env.calls.find(([c]) => c === 'bootstrap');
    assert(boot && boot[1] && boot[1].preserveView === true, 'transferência mantém a tela');
    env = environment({ failBootstrap: true });
    await env.ctx.saveEmployeeMovement({ preventDefault() {}, target: form() });
    assert(env.calls.some(([c, type, msg]) => c === 'toast' && type === 'warning' && msg === REFRESH_FAILED), 'aviso verdadeiro');
    assert(!env.calls.some(([c]) => c === 'alert'), 'sem alert de falha');
  });
};
