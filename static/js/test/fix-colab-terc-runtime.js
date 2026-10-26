'use strict';
// FIX-COLAB-TERC-V1: exercise the production save/archive functions. Real HTML
// named-property and hidden-input reset semantics are covered by Chromium too.
const fs = require('fs'), path = require('path'), vm = require('vm');
const source = fs.readFileSync(path.resolve(__dirname, '../../app.js'), 'utf8');
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
    ARCHIVAL_ENTITIES: { outsourcedCompany: { path: '/api/outsourced-companies', stateList: 'outsourcedCompanies',
      updatePermission: 'employees:update', deletePermission: 'employees:update', labelFallback: 'QA', i18nPrefix: 'outsourcedCompany' } },
    document: { getElementById: () => null, querySelector: () => null },
    requirePermission: () => true, formValues: () => ({ id: id.value, name: 'QA', company_id: '901' }),
    api: async (url, options) => { calls.push(['api', url, options.method]); return {}; },
    loadBootstrap: async (options) => calls.push(['bootstrap', options]),
    loadOutsourcedCompanies: async () => calls.push(['companies']),
    loadArchivedRecords: async (kind) => calls.push(['archived', kind]),
    setFormSubmitLabel: () => {}, setOutsourcedCompanyFormMode: () => {}, syncOutsourcedCompanyUnitOptions: () => {},
    applyOutsourcedCompanyCorporateLock: () => {}, setEmployeeLegalEntityLock: () => {}, syncEmpresaOrigemVisibility: () => {},
    setOutsourcedEmployeeFormMode: () => {}, syncOutsourcedEmployeeUnitOptions: () => {}, renderOutsourcedEmployees: () => calls.push(['employees']),
    tr: (_key, fallback) => fallback, confirmDestructive: async () => true, prompt: () => '',
    showToast: () => {}, alert: (message) => { throw new Error(message); }
  });
  ctx.globalThis = ctx;
  vm.runInContext([slice('saveSimpleForm'), slice('handleFormReset'), slice('archiveEntityRecord'), slice('restoreArchivedRecord')].join('\n'), ctx);
  return { ctx, form, calls };
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
};
