'use strict';

// Executa as funções reais de navegação, vínculo e consulta do app.js em VM.
// Só transporte e DOM são substituídos; não reimplementa o fluxo sob teste.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const source = fs.readFileSync(path.resolve(__dirname, '../../app.js'), 'utf8');

function functionSource(name) {
  const start = new RegExp('^(?:async )?function ' + name + '\\(', 'm').exec(source);
  if (!start) throw new Error('Função ausente: ' + name);
  const end = source.slice(start.index + start[0].length).search(/^}/m);
  if (end < 0) throw new Error('Função sem fechamento: ' + name);
  return source.slice(start.index, start.index + start[0].length + end + 1);
}

const panels = [
  { name: 'pendências', loader: 'loadPendingRegularization', button: 'pending-reg-refresh', status: 'pending-reg-count', empty: 'pending-reg-empty', content: 'pending-reg-tbody' },
  { name: 'bloqueios', loader: 'loadBlockedStock', button: 'blocked-stock-refresh', status: 'blocked-stock-load-status', empty: 'blocked-stock-empty', content: 'blocked-stock-tbody' },
  { name: 'validade', loader: 'loadValidityOverview', button: 'validity-mgmt-refresh', status: 'validity-mgmt-value', empty: 'validity-mgmt-empty', content: 'validity-mgmt-kpis' }
];
const tick = () => new Promise((resolve) => setImmediate(resolve));
const payload = (label = 'Luva de teste') => ({
  count: 1, items: [{ id: 1, unit_id: 5, epi_name: label, unit_name: 'Unidade', qr_code_value: label, status: 'quarantine' }],
  statuses: { quarantine: 'Quarentena' }, summary: { at_risk_total: 1, product_expiring: 1, value_at_risk: 25 },
  by_manufacturer: [{ label, count: 1, days_remaining: 3, value: 25 }]
});

function harness({ spa = false, transport = async () => payload(), stockFails = false } = {}) {
  const nodes = new Map();
  const requests = [];
  const node = (id) => {
    if (!nodes.has(id)) nodes.set(id, {
      id, value: '', innerHTML: '', textContent: '', style: {}, listeners: {},
      classList: { add() {}, remove() {}, toggle() {} },
      addEventListener(event, callback) { (this.listeners[event] ||= []).push(callback); }
    });
    return nodes.get(id);
  };
  node('stock-company').value = '2';
  node('stock-unit').value = '5';
  const context = {
    console, URLSearchParams, Map, Date,
    CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options?.detail; } },
    document: { getElementById: node, querySelector: (s) => s === '.view.active' ? { id: 'dashboard-view' } : null, dispatchEvent() {} },
    refs: { viewNodes: [], menuLinks: [] }, state: { user: { id: 999, company_id: 2 } },
    VIEW_PERMISSIONS: {}, VIEW_PERMISSION_ALTERNATIVES: {}, VIEW_EYEBROW: {}, SPA_NAV_SUPPORTED_VIEWS: ['estoque'],
    defaultView: () => 'dashboard', canAccessView: () => true, hasPermission: () => true,
    isSpaNavigationEnabled: () => spa, isPhase3ModernUiEnabled: () => false, isUxPerformanceHardeningEnabled: () => false,
    updateBootstrapDegradedUi() {}, trackInteractiveViewHistory() {}, trackNavBackHistory() {}, stopDeliveryQrCamera: async () => {},
    reportNonCriticalError() {}, setSpaNavigationLoading() {}, showToast() {},
    loadStockEpis: async () => { if (stockFails) throw new Error('Lista indisponível'); },
    loadStockLotEvidence: async () => {},
    syncStockOptions() {}, scheduleStockMovementSearchLoad() {},
    bindAppListener: (target, event, callback) => target?.addEventListener(event, callback),
    tr: (_key, fallback) => fallback, esc: (value) => String(value ?? ''), formatCurrency: (value) => String(value),
    apiWithBootstrapRetry: async (url) => { requests.push(url); return transport(url); },
    spaNavigationInflightByView: new Map(), spaNavigationLastRunByView: new Map()
  };
  vm.createContext(context);
  const declarations = ['_blockedStockStatuses', '_stockPanelRequests', 'VALIDITY_MGMT_INDICATORS'].map((name) => {
    const expression = new RegExp('^(?:let|const) ' + name + ' = [\\s\\S]*?;', 'm').exec(source);
    if (!expression) throw new Error('Declaração ausente: ' + name);
    return expression[0];
  });
  const names = ['_blockedStockContext', '_stockPanelLoadMessage', '_startStockPanelLoad', '_stockPanelLoadError',
    '_renderBlockedStatusOptions', 'loadBlockedStock', 'bindBlockedStockUi', '_validityDaysLabel', '_renderValidityKpis',
    '_renderValidityBreakdown', 'loadValidityOverview', 'bindValidityMgmtUi', 'loadPendingRegularization',
    'resolveRefreshHandlers', 'runSpaPartialNavigation', 'showView'];
  const hook = source.match(/^globalThis\.__EPI_REFRESH_ESTOQUE_LISTA__ = async \(\) => \{[\s\S]*?^};/m);
  if (!hook) throw new Error('Atualização do estoque ausente');
  // Inclui os próprios callbacks de troca de escopo, sem chamar o restante
  // do boot (que também vincula câmeras, formulários e outros módulos).
  const scopeBindings = ['stock-company', 'stock-unit'].map((id) => {
    const line = source.split('\n').find((s) => s.includes("bindAppListener(document.getElementById('" + id + "'), 'change'"));
    if (!line) throw new Error('Listener de escopo ausente: ' + id);
    return line;
  });
  vm.runInContext([...declarations, ...names.map(functionSource), hook[0], ...scopeBindings].join('\n'), context);
  return {
    node, requests,
    run: (code) => vm.runInContext(code, context),
    fire: async (id, event = 'click') => { for (const callback of node(id).listeners[event] || []) await callback({}); await tick(); }
  };
}

module.exports = ({ testAsync, assert, eq }) => {
  for (const [name, options, showOptions] of [
    ['clássica', {}, '{}'], ['SPA', { spa: true }, '{}'], ['SPA com partial:false', { spa: true }, '{ partial: false }']
  ]) {
    testAsync('Estoque: navegação ' + name + ' inicializa os três painéis uma vez', async () => {
      const h = harness(options);
      h.run("showView('estoque', " + showOptions + ')');
      await tick();
      eq(h.requests.length, 3);
      for (const panel of panels) {
        assert(h.node(panel.content).innerHTML.includes('<'), 'Painel não renderizado: ' + panel.name);
        eq(h.node(panel.button).listeners.click.length, 1);
      }
      // Reentrada não multiplica os callbacks de Atualizar.
      h.run("showView('estoque', " + showOptions + ')');
      await tick();
      for (const panel of panels) eq(h.node(panel.button).listeners.click.length, 1);
    });
  }

  testAsync('Estoque: falha na lista de EPIs não impede os três painéis', async () => {
    const h = harness({ stockFails: true });
    h.run("showView('estoque')");
    await tick();
    eq(h.requests.length, 3);
    assert(h.node('pending-reg-tbody').innerHTML.includes('Luva de teste'));
  });

  for (const panel of panels) {
    testAsync('Estoque: botão Atualizar de ' + panel.name + ' refaz a consulta', async () => {
      let label = 'Primeira consulta';
      const h = harness({ transport: async () => payload(label) });
      h.run("showView('estoque')"); await tick();
      label = 'Segunda consulta';
      await h.fire(panel.button);
      eq(h.requests.length, 4);
      if (panel.loader !== 'loadValidityOverview') assert(h.node(panel.content).innerHTML.includes(label));
      else assert(h.node('validity-by-manufacturer').innerHTML.includes(label));
    });

    testAsync('Estoque: ' + panel.name + ' mostra carregamento, erro e recuperação sem falso vazio', async () => {
      let finish;
      const h = harness({ transport: () => new Promise((resolve, reject) => { finish = { resolve, reject }; }) });
      const first = h.run(panel.loader + '()');
      eq(h.node(panel.status).textContent, 'Carregando...');
      eq(h.node(panel.empty).style.display, 'none');
      finish.reject(new Error('HTTP 503')); await first;
      assert(h.node(panel.status).textContent.includes('Não foi possível carregar'));
      eq(h.node(panel.empty).style.display, 'none');
      eq(h.node(panel.content).innerHTML, '');
      const retry = h.run(panel.loader + '()');
      finish.resolve({ items: [], count: 0, summary: {} }); await retry;
      eq(h.node(panel.empty).style.display, '');
      assert(!h.node(panel.status).textContent.includes('Não foi possível carregar'));
      eq(h.node(panel.status).style.color, '');
    });

    for (const staleFails of [false, true]) {
      testAsync('Estoque: ' + panel.name + ' ignora ' + (staleFails ? 'erro' : 'resposta') + ' de unidade anterior', async () => {
        const pending = [];
        const h = harness({ transport: () => new Promise((resolve, reject) => pending.push({ resolve, reject })) });
        const previous = h.run(panel.loader + '()');
        h.node('stock-unit').value = '6';
        const current = h.run(panel.loader + '()');
        assert(h.requests[0].includes('unit_id=5'));
        assert(h.requests[1].includes('unit_id=6'));
        pending[1].resolve(payload('Unidade nova')); await current;
        const status = h.node(panel.status).textContent;
        const content = h.node(panel.content).innerHTML;
        if (staleFails) pending[0].reject(new Error('Resposta antiga falhou'));
        else pending[0].resolve({ items: [], count: 0, summary: {} });
        await previous;
        eq(h.node(panel.status).textContent, status);
        eq(h.node(panel.content).innerHTML, content);
        eq(h.node(panel.empty).style.display, 'none');
      });
    }
  }

  for (const id of ['stock-company', 'stock-unit']) {
    testAsync('Estoque: troca de ' + id + ' atualiza todos os painéis no escopo novo', async () => {
      const h = harness();
      h.node(id).value = '7';
      await h.fire(id, 'change');
      eq(h.requests.length, 3);
      const param = id === 'stock-company' ? 'company_id=7' : 'unit_id=7';
      assert(h.requests.every((url) => url.includes(param)));
    });
  }
};
