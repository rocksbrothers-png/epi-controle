'use strict';
// FIX-COLAB-TERC-V1: exercise the production save/archive functions. Real HTML
// named-property and hidden-input reset semantics are covered by Chromium too.
const fs = require('fs'), path = require('path'), vm = require('vm');
const source = fs.readFileSync(path.resolve(__dirname, '../../app.js'), 'utf8');
// FIX-NAV-REFRESH-V1: o fluxo gravar → atualizar vem do módulo real (shared/ui).
const mutationFlow = fs.readFileSync(path.resolve(__dirname, '../modules/shared/ui/mutation-flow.js'), 'utf8');
// UBX-V5 Etapa 1: arquivar/desarquivar/excluir saíram do app.js para os módulos
// reais de modules/archival/ (configuração, integração e UI).
const ARCHIVAL_MODULES = ['business/archival-rules.js', 'integrations/archival-api.js', 'ui/archival-view.js']
  .map((rel) => fs.readFileSync(path.resolve(__dirname, '../modules/archival', rel), 'utf8'));
function loadArchival(ctx) {
  ctx.__EPI_APP_STATE__ = ctx.state;
  ctx.__EPI_REFS__ = {};
  for (const code of [mutationFlow, ...ARCHIVAL_MODULES]) { vm.runInContext(code, ctx); }
}
// A lista de arquivados é recarregada pelo GET real de loadArchivedRecords.
function archivedReload(url) {
  const match = /^\/api\/(employees|epis|outsourced-companies)\/archived\?actor_user_id=7(&outsourced_only=1)?$/.exec(url);
  if (!match) { return null; }
  return { 'employees': match[2] ? 'outsourcedEmployee' : 'employee', 'epis': 'epi', 'outsourced-companies': 'outsourcedCompany' }[match[1]];
}
function slice(name) {
  const lines = source.split('\n');
  const start = lines.findIndex((line) => new RegExp(`^(?:async )?function ${name}\\(`).test(line));
  if (start < 0) { throw new Error(`missing ${name}`); }
  let end = start;
  while (!/^}/.test(lines[end])) { end++; }
  return lines.slice(start, end + 1).join('\n');
}
function environment(formId, editingId = '') {
  const calls = [];
  const id = { value: editingId };
  const form = {
    id, // HTMLFormElement LegacyOverrideBuiltIns, deliberately NOT formId
    getAttribute: (name) => name === 'id' ? formId : null,
    elements: { id }, dataset: {},
    querySelector: () => null,
    reset: () => calls.push(['reset']) // hidden input value survives reset
  };
  const ctx = vm.createContext({
    state: { user: { id: 7, role: 'registry_admin', company_id: 901 }, outsourcedCompanies: [{ id: 11, name: 'QA' }] },
    document: { getElementById: () => null, querySelector: () => null },
    requirePermission: () => true, hasPermission: () => true, actorQuery: () => 'actor_user_id=7',
    formValues: () => ({ id: id.value, name: 'QA', company_id: '901' }),
    api: async (url, options) => {
      const kind = archivedReload(url);
      calls.push(kind ? ['archived', kind] : ['api', url, (options || {}).method]);
      return {};
    },
    loadBootstrap: async (options) => calls.push(['bootstrap', options]),
    loadOutsourcedCompanies: async () => calls.push(['companies']),
    setFormSubmitLabel: () => {}, setOutsourcedCompanyFormMode: () => {}, syncOutsourcedCompanyUnitOptions: () => {},
    applyOutsourcedCompanyCorporateLock: () => {}, setEmployeeLegalEntityLock: () => {}, syncEmpresaOrigemVisibility: () => {},
    setOutsourcedEmployeeFormMode: () => {}, syncOutsourcedEmployeeUnitOptions: () => {}, renderOutsourcedEmployees: () => calls.push(['employees']),
    tr: (_key, fallback) => fallback, confirmDestructive: async () => true, prompt: () => '',
    showToast: () => {}, alert: (message) => { throw new Error(message); }
  });
  ctx.globalThis = ctx;
  loadArchival(ctx);
  vm.runInContext([slice('saveSimpleForm'), slice('handleFormReset')].join('\n'), ctx);
  return { ctx, form, calls };
}
// Configuração REAL de ARCHIVAL_ENTITIES: arquivar/desarquivar/excluir
// definitivamente nos cadastros de Colaboradores/Terceirizados atualiza as
// listas sem tirar o usuário da tela; EPI mantém a navegação anterior.
function archivalEnvironment() {
  const calls = [];
  const archived = { id: 32, name: 'QA', legal_name: 'QA' };
  const ctx = vm.createContext({
    state: { user: { id: 7, role: 'registry_admin', company_id: 901 }, employees: [{ id: 32, name: 'QA' }],
      epis: [{ id: 32, name: 'QA' }], outsourcedCompanies: [{ id: 32, legal_name: 'QA' }],
      archivedEmployees: [archived], archivedEpis: [archived], archivedOutsourcedCompanies: [archived],
      archivedOutsourcedEmployees: [archived] },
    requirePermission: () => true, hasPermission: () => true, actorQuery: () => 'actor_user_id=7', reportNonCriticalError: () => {},
    api: async (url, options) => {
      const kind = archivedReload(url);
      calls.push(kind ? ['archived', kind] : ['api', url, (options || {}).method || 'GET']);
      return { records: {} };
    },
    loadBootstrap: async (options) => calls.push(['bootstrap', options || null]),
    loadOutsourcedCompanies: async () => calls.push(['companies']),
    tr: (_key, fallback) => fallback, confirmDestructive: async () => true, prompt: () => 'QA justificativa',
    showToast: () => {}, alert: () => {}
  });
  ctx.globalThis = ctx;
  loadArchival(ctx);
  return { ctx, calls };
}
module.exports = function ({ testAsync, eq, assert }) {
  for (const editingId of ['', '11']) {
    testAsync(`FIX-COLAB-TERC company ${editingId ? 'update' : 'create'} refreshes with named id control`, async () => {
      const { ctx, form, calls } = environment('outsourced-company-form', editingId);
      await ctx.saveSimpleForm({ target: form, preventDefault() {} }, '/api/outsourced-companies', 'employees:create');
      assert(calls.some(([name]) => name === 'companies'), 'separate opt-in loader must run');
      eq(form.elements.id.value, '', 'clear hidden identity explicitly');
      eq(calls.find(([name]) => name === 'api')[2], editingId ? 'PUT' : 'POST');
      eq(form.dataset.submitting, '0');
    });
  }
  for (const formId of ['employee-form', 'outsourced-company-form', 'outsourced-employee-form']) {
    testAsync(`FIX-COLAB-TERC ${formId} reset disarms hidden edit id`, async () => {
      const { ctx, form } = environment(formId, '31');
      ctx.handleFormReset(form);
      eq(form.elements.id.value, '');
    });
  }
  for (const name of ['archiveEntityRecord', 'restoreArchivedRecord']) {
    testAsync(`FIX-COLAB-TERC ${name} refreshes opt-in company list`, async () => {
      const { ctx, calls } = environment('outsourced-company-form');
      await ctx[name]('outsourcedCompany', 11);
      assert(calls.some(([call]) => call === 'companies'), 'corporate company list stale');
      assert(calls.some(([call, kind]) => call === 'archived' && kind === 'outsourcedCompany'));
    });
  }
  // FIX-NAV-REFRESH-V1: EPI passou a manter a tela, como os cadastros de Colaboradores.
  const keepsView = { employee: true, outsourcedCompany: true, outsourcedEmployee: true, epi: true };
  for (const name of ['archiveEntityRecord', 'restoreArchivedRecord', 'purgeArchivedRecord']) {
    for (const [kind, preserve] of Object.entries(keepsView)) {
      testAsync(`FIX-COLAB-TERC ${name}(${kind}) mantém a tela atual`, async () => {
        const { ctx, calls } = archivalEnvironment();
        await ctx[name](kind, 32);
        const mutation = calls.filter(([call, , method]) => call === 'api' && method === 'POST').pop();
        assert(mutation && /\/(archive|restore|purge-confirm)$/.test(mutation[1]), `${kind}: mutação não enviada`);
        const bootstrap = calls.find(([call]) => call === 'bootstrap');
        assert(bootstrap, `${kind}: bootstrap não recarregado`);
        eq(Boolean(bootstrap[1] && bootstrap[1].preserveView), preserve, `${kind}: preserveView`);
        assert(calls.some(([call, k]) => call === 'archived' && k === kind), `${kind}: lista de arquivados não recarregada`);
      });
    }
  }
};
