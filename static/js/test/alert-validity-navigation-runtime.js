'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const moduleSource = fs.readFileSync(path.resolve(__dirname, '../modules/stock/ui/pending-validity-navigation.js'), 'utf8');
const dashboardSource = fs.readFileSync(path.resolve(__dirname, '../views/dashboard.js'), 'utf8');
function harness({ role = 'general_admin', permission = true, operationalUnit = 11 } = {}) {
  const listeners = {}, nodes = new Map(), calls = [];
  function node(id) {
    if (!nodes.has(id)) { nodes.set(id, { id, value: '', textContent: '', innerHTML: '', hidden: false, dataset: {}, listeners: {},
      classList: { contains: (name) => id === 'estoque-view' && name === 'active' },
      addEventListener(type, fn) { this.listeners[type] = fn; }, focus() { calls.push('focus'); },
      scrollIntoView() { calls.push('scroll'); } }); }
    return nodes.get(id);
  }
  node('stock-company').value = '1'; node('stock-unit').value = '10';
  node('pending-reg-filter').value = 'old-group';
  const state = { user: { id: 9, company_id: 1, role, operational_unit_id: operationalUnit },
    companies: [{ id: 1, name: 'Company A' }, { id: 2, name: 'Company B' }],
    units: [{ id: 10, company_id: 1, name: 'Empty unit' }, { id: 11, company_id: 1, name: 'Unit A' },
      { id: 12, company_id: 1, name: 'Unit B' }, { id: 20, company_id: 2, name: 'Foreign' }],
    alerts: [], dashboardFilters: { query: '' } };
  const ctx = { console, Event, setTimeout, __EPI_APP_STATE__: state, __EPI_REFS__: { alertsList: node('alerts') },
    currentUserHasPermission: () => permission, trEpi: (_key, fallback) => fallback,
    syncStockOptions: () => { calls.push('sync'); node('stock-unit').value = '10'; },
    __EPI_REFRESH_ESTOQUE_LISTA__: async () => { calls.push('read-refresh'); },
    document: { getElementById: (id) => id === 'dashboard-critical-banner' ? null : node(id),
      querySelector: (selector) => selector.includes('menu-link') ? { click: () => calls.push('navigate') }
        : { click: () => calls.push('validade-tab') },
      addEventListener: (type, fn) => { listeners[type] = fn; } } };
  vm.createContext(ctx); vm.runInContext(moduleSource, ctx);
  ctx.__EPI_PENDING_VALIDITY_NAVIGATION__.configure({ getState: () => state,
    hasPermission: ctx.currentUserHasPermission, syncOptions: ctx.syncStockOptions,
    translate: ctx.trEpi, refresh: ctx.__EPI_REFRESH_ESTOQUE_LISTA__ });
  vm.runInContext(dashboardSource, ctx);
  return { state, node, calls, listeners, nav: ctx.__EPI_PENDING_VALIDITY_NAVIGATION__, dashboard: ctx.__EPI_DASHBOARD__ };
}
module.exports = ({ test, assert, eq }) => {
  test('Alert validity: same action style, descriptive label and exact IDs; other alerts retained', () => {
    const h = harness();
    h.state.alerts = [
      { category: 'physical_unknown', company_id: 1, unit_id: 11, epi_id: 7, epi_name: 'Glove', title: 'Unknown', description: '2 pieces' },
      { category: 'stock', epi_name: 'Boot', title: 'Low', description: '1' },
      { category: 'manufacturer', epi_name: 'Helmet', title: 'Expiry', description: '1' },
    ];
    h.dashboard.renderAlerts();
    const html = h.node('alerts').innerHTML;
    eq((html.match(/class="alert-action"/g) || []).length, 3);
    assert(html.includes('Regularizar Validade') && html.includes('aria-label="Regularizar Validade: Glove"'));
    assert(html.includes('data-epi-id="7"') && html.includes('data-unit-id="11"'));
    eq((html.match(/>Ver Estoque<\/button>/g) || []).length, 2);
    const attrs = { 'data-company-id': '1', 'data-unit-id': '11', 'data-epi-id': '7', 'data-epi-name': 'Glove' };
    h.node('alerts').listeners.click({ target: { closest: () => ({ hasAttribute: () => true, getAttribute: (key) => attrs[key] }) } });
    assert(h.calls.includes('validade-tab') && h.calls.includes('read-refresh'));
  });
  test('Alert validity: company alert retains all units and lots, filters exact EPI rather than name', () => {
    const h = harness();
    assert(h.nav.open({ company_id: 1, epi_id: 7, epi_name: 'Glove' }));
    eq(h.nav.requestContext({ companyId: '1', unitId: '10' }).unitId, '');
    const response = h.nav.filterResponse({ count: 4, items: [
      { id: 1, epi_id: 7, unit_id: 11, lot_id: 101 }, { id: 2, epi_id: 7, unit_id: 12, lot_id: 102 },
      { id: 3, epi_id: 8, unit_id: 11, epi_name: 'Glove' }, { id: 4, epi_id: 7, unit_id: 12, lot_id: 103 },
    ] });
    eq(response.count, 3); eq(response.items.map((i) => i.id).join(','), '1,2,4');
    assert(h.node('pending-reg-alert-label').textContent.includes('Todas as Unidades'));
    eq(h.node('pending-reg-filter').value, '');
  });
  for (const role of ['admin', 'user']) {
    test('Alert validity: operational profile ' + role + ' preserves its unit and rejects crossed scope', () => {
      const h = harness({ role });
      assert(!h.nav.open({ company_id: 2, unit_id: 20, epi_id: 7 }));
      assert(!h.nav.open({ company_id: 1, unit_id: 12, epi_id: 7 }));
      assert(h.nav.open({ company_id: 1, unit_id: 11, epi_id: 7 }));
      eq(h.node('stock-unit').value, '11');
      eq(h.nav.requestContext({}).unitId, '11');
      eq(h.nav.filterResponse({ items: [{ epi_id: 7, unit_id: 11 }, { epi_id: 7, unit_id: 12 }] }).count, 1);
    });
  }
  test('Alert validity: read authorization is required, regularization authorization is not', () => {
    const blocked = harness({ permission: false });
    blocked.state.alerts = [{ category: 'physical_unknown', epi_name: 'Glove', epi_id: 7 }];
    blocked.dashboard.renderAlerts();
    assert(!blocked.node('alerts').innerHTML.includes('alert-action'));
    assert(!blocked.nav.open({ company_id: 1, epi_id: 7 })); eq(blocked.calls.length, 0);
    const reader = harness({ role: 'general_admin' });
    assert(reader.nav.open({ company_id: 1, epi_id: 7 }));
    assert(reader.calls.includes('read-refresh'));
  });
  test('Alert validity: scope change, leaving view and session change clear the alert filter', () => {
    const h = harness();
    const original = { count: 2, items: [{ epi_id: 7 }, { epi_id: 8 }] };
    h.nav.open({ company_id: 1, epi_id: 7 });
    h.node('stock-unit').value = '12';
    eq(h.nav.filterResponse(original).count, 2); assert(h.node('pending-reg-alert-context').hidden);
    h.nav.open({ company_id: 1, epi_id: 7 });
    h.listeners['epi:viewchange']({ detail: { view: 'dashboard' } });
    eq(h.nav.filterResponse(original).count, 2);
    h.nav.open({ company_id: 1, epi_id: 7 }); h.state.user.id = 99;
    eq(h.nav.filterResponse(original).count, 2);
  });
};
