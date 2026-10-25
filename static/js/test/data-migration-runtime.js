'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const source = fs.readFileSync(path.resolve(__dirname, '../../app.js'), 'utf8');
function functionSource(name) {
  const match = new RegExp('^(?:async )?function ' + name + '\\(', 'm').exec(source);
  if (!match) {throw new Error('Missing function: ' + name);}
  const end = source.slice(match.index + match[0].length).search(/^}/m);
  return source.slice(match.index, match.index + match[0].length + end + 1);
}
function harness() {
  const draft = { busy: false, entity: 'unidades', sourceKind: 'csv', mapping: {},
    preview: { blocking: false, preview_token: 'reviewed', total_rows: 1, diagnostics: [] }, jobs: [] };
  const apply = { disabled: false };
  const calls = [];
  let resolve;
  const pending = new Promise((done) => { resolve = done; });
  const ctx = {
    state: { user: { id: 7 } }, refs: { migracaoApply: apply, migracaoStrategy: { value: 'insert_only' }, migracaoJobsTable: {} },
    migracaoState: () => draft, dataMigrationHelpers: () => ({ canRevert: () => false }),
    document: { getElementById: () => ({}) },
    renderDataMigrationSteps() {}, showToast() {}, loadDataMigrationJobs: async () => {}, focusViewTab() {},
    api: (url, options) => { calls.push({ url, body: JSON.parse(options.body) }); return pending; },
    tr: (_key, fallback) => fallback, escapeHtml: (text) => text, formatDateTime: () => '',
    confirm: () => true, migracaoErrorMessage: (error) => error.message,
  };
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.resolve(__dirname, '../modules/data-migration/integrations/job-decisions.js'), 'utf8'), ctx);
  vm.runInContext(['renderDataMigrationPreview', 'runDataMigration', 'renderDataMigrationJobs', 'revertDataMigrationJob']
    .map(functionSource).join('\n'), ctx);
  return { draft, calls, apply, ctx, resolve };
}
module.exports = ({ test, testAsync, assert, eq }) => {
  testAsync('Migration: double click sends one request and disables confirmation in flight', async () => {
    const h = harness();
    const first = h.ctx.runDataMigration('insert_only');
    assert(h.apply.disabled, 'confirmation must disable before the response');
    await h.ctx.runDataMigration('insert_only');
    eq(h.calls.length, 1);
    eq(h.calls[0].body.preview_token, 'reviewed');
    h.resolve({ job_id: 1, status: 'completed', totals: { inserted: 1 },
      preview: { total_rows: 1, diagnostics: [], actual_totals: { total: 1, failed: 0, inserted: 1 } } });
    await first;
    await h.ctx.runDataMigration('insert_only');
    eq(h.calls.length, 1, 'completed preview cannot be resubmitted');
    assert(h.apply.disabled);
  });
  test('Migration: history offers homologation only for completed unreviewed jobs', () => {
    const h = harness();
    h.draft.jobs = [{ id: 1, status: 'completed' }, { id: 2, status: 'failed' },
      { id: 3, status: 'completed', homologated_at: '2026-01-01' },
      { id: 4, status: 'completed', reverted_at: '2026-01-01' }];
    h.ctx.renderDataMigrationJobs();
    const html = h.ctx.refs.migracaoJobsTable.innerHTML;
    assert(html.includes('data-migracao-homologate="1"'));
    [2, 3, 4].forEach((id) => assert(!html.includes('data-migracao-homologate="' + id + '"')));
  });
  testAsync('Migration: homologation action calls the API once with the actor', async () => {
    const h = harness();
    const action = h.ctx.revertDataMigrationJob(17, 'homologate');
    await h.ctx.revertDataMigrationJob(17, 'homologate');
    eq(h.calls.length, 1);
    eq(h.calls[0].url, '/api/data-migration/jobs/17/homologate');
    eq(h.calls[0].body.actor_user_id, 7);
    h.resolve({ homologated: true });
    await action;
    assert(!h.draft.busy);
  });
};
