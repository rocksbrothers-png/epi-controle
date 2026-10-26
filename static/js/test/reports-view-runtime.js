'use strict';
// UBX-V3, Etapa 4 — caracterização de Relatórios
// (modules/reports/{business,integrations,ui}).
//
// O MESMO roteiro roda sobre as funções ORIGINAIS do app.js (geração das
// tabelas, commit da Etapa 3, antes da extração) e sobre os módulos: DOM
// falso, espiões de api/permissão/alert/open e o estado compartilhado. Ficam
// fixados filtros coletados (inclusive a ordem das mensagens de erro), as
// requisições, o HTML gerado, a paginação, os caminhos de permissão e 403,
// os combos de unidade/colaborador por perfil e a URL do PDF.
const fs = require('fs'), path = require('path'), vm = require('vm');
const JS_ROOT = path.resolve(__dirname, '..');
const MODULES = ['modules/reports/business/report-filters.js', 'modules/reports/integrations/reports-api.js',
  'modules/reports/ui/reports-view.js'];
const NAMES = ['syncReportOptions', 'collectReportFilters', 'renderReports', 'retentionStatusBadge', 'renderArchiveTable',
  'loadArchiveReports', 'exportReportPdf'];

function makeEnv() {
  const log = [];
  const el = (id) => ({ id, value: '', innerHTML: '', textContent: '', disabled: false, style: {} });
  const nodes = Object.fromEntries(['report-company', 'report-unit', 'report-employee', 'report-unit-hint',
    'report-legal-entity', 'report-sector', 'report-tipo-vinculo', 'report-epi', 'report-ficha-status',
    'report-tipo-vinculo-summary', 'start_date', 'end_date'].map((id) => [id, el(id)]));
  const form = {
    querySelector: (sel) => {
      const m = /^#([\w-]+)$/.exec(sel) || /^input\[name="(\w+)"\]$/.exec(sel);
      return m ? nodes[m[1]] || null : null;
    }
  };
  const document = {
    getElementById: (id) => (id === 'report-filter-form' ? (env.noForm ? null : form) : nodes[id] || null)
  };
  const refs = Object.fromEntries(['reportSummary', 'reportUnits', 'reportSectors', 'reportEmployeeFichas',
    'reportArchiveTable', 'reportArchivePagination'].map((k) => [k, el(k)]));
  const state = {
    user: { id: 7, company_id: 901, operational_unit_id: '' },
    units: [{ id: 1, company_id: 901, name: 'Base A' }, { id: 2, company_id: 901, name: 'Base B' },
      { id: 3, company_id: 902, name: 'Outra' }],
    employees: [{ id: 11, company_id: 901, current_unit_id: 1, employee_id_code: 'E1', name: 'Ana' },
      { id: 12, company_id: 901, unit_id: 2, employee_id_code: 'E2', name: 'Bia' },
      { id: 13, company_id: 902, unit_id: 3, employee_id_code: 'E3', name: 'Cris' }],
    reportArchivePage: 2, reportArchivePageSize: 25, fichaRetentionPolicy: { keep: 'old' }
  };
  const replies = [];
  const env = {
    log, nodes, refs, state, replies, perms: new Set(['reports:view']), operational: false, noForm: false,
    globals: {
      document, Promise, JSON, Object, Array, String, Number, URLSearchParams, Error, RegExp,
      hasPermission: (p) => { log.push(['hasPermission', p]); return env.perms.has(p); },
      requirePermission: (p) => { log.push(['requirePermission', p]); return env.perms.has(p); },
      recordOptionalBootstrapSectionSkipped: (...args) => log.push(['skipped', ...args]),
      reportNonCriticalError: (msg, err) => log.push(['nonCritical', msg, err && err.message]),
      isOperationalProfile: () => env.operational,
      filterByUserCompany: (items) => (items || []).filter((i) => i.company_id === state.user.company_id),
      formatUnitOption: (u) => `<option value="${u.id}">${u.name}</option>`,
      syncReportLegalEntityOptions: () => log.push(['syncLegalEntity']),
      tr: (_k, fallback) => fallback,
      formatDate: (d) => `D(${d})`,
      formatDateTime: (d) => `DT(${d})`,
      renderBadge: (type, value, label) => `[${type}|${value}|${label}]`,
      dsTableState: (o) => `<tr><td colspan="${o.colspan}">${o.message}</td></tr>`,
      alert: (m) => log.push(['alert', m]),
      open: (url, target) => log.push(['open', url, target]),
      api: async (url) => {
        log.push(['api', url]);
        const next = replies.shift();
        if (next instanceof Error) { throw next; }
        return next;
      }
    }
  };
  return env;
}

function contextFor(env) {
  const ctx = vm.createContext({ ...env.globals, state: env.state, refs: env.refs,
    __EPI_APP_STATE__: env.state, __EPI_REFS__: env.refs });
  ctx.globalThis = ctx;
  return ctx;
}

function httpError(status, message) { const e = new Error(message); e.status = status; return e; }

function snapshot(env) {
  const pick = (o) => Object.fromEntries(Object.entries(o).map(([k, n]) => [k, [n.value, n.innerHTML, n.textContent, n.disabled, n.style.display]]));
  return { nodes: pick(env.nodes), refs: pick(env.refs), log: env.log.splice(0), reports: env.state.reports,
    archive: [env.state.reportArchiveItems, env.state.reportArchiveTotal, env.state.fichaRetentionPolicy] };
}

// Mesmo roteiro para as originais e para os módulos. `run(env)` devolve o
// contexto já com as funções carregadas.
async function scenario(run) {
  const out = {};
  const fill = (env, values) => { for (const [k, v] of Object.entries(values)) { env.nodes[k].value = v; } };
  const collect = (values, extra = {}) => {
    const env = makeEnv(); Object.assign(env, extra); const fns = run(env); fill(env, values);
    try { return fns.collectReportFilters(); } catch (error) { return { erro: error.message }; }
  };
  out.collect = [
    collect({}),
    collect({ 'report-company': ' 901 ', 'report-unit': '1', 'report-sector': ' Obras ', start_date: '2026-01-01', end_date: '2026-12-31' }),
    collect({ 'report-company': '9a', start_date: '01/01/2026' }),
    collect({ 'report-unit': 'x', 'report-epi': 'y' }),
    collect({ start_date: '2026-1-1' }),
    collect({ 'report-tipo-vinculo': 'CLT', 'report-ficha-status': 'aberta', 'report-legal-entity': '5', 'report-employee': '12' }),
    collect({}, { noForm: true })
  ];
  // Cascata: o campo i e todos os seguintes inválidos → o erro tem de nomear o
  // campo i. Fixa a ordem completa de validação (a primeira falha vence).
  const invalid = { 'report-company': 'a', 'report-legal-entity': 'b', 'report-unit': 'c', 'report-employee': 'd',
    'report-epi': 'e', start_date: '1/1/2026', end_date: '2/2/2026' };
  const keys = Object.keys(invalid);
  out.collectOrdem = keys.map((_, i) => collect(Object.fromEntries(keys.slice(i).map((k) => [k, invalid[k]]))));

  const reportPayload = { deliveries: [1, 2, 3], total_quantity: 9, by_unit: { 'Base A': 2 }, by_sector: {},
    by_tipo_vinculo: { CLT: 3 }, employee_fichas: [{ employee_name: 'Ana', employee_id_code: 'E1', period_start: '2026-01-01',
      period_end: '2026-01-31', status: 'aberta', unit_name: '', total_items: 2, total_quantity: 4 }] };
  const archivePayload = { items: [{ id: 5, generated_at: 'G', employee_name: 'Ana', employee_id_code: 'E1', company_name: 'C',
    unit_name: '', status: 'expired', html_sha256: 'abcdef0123456789zz' }], total: 1, retention_policy: { keep: 'new' } };

  const render = async (prep) => {
    const env = makeEnv(); const fns = run(env); await prep(env, fns); return snapshot(env);
  };
  out.renderOk = await render(async (env, fns) => {
    env.replies.push(reportPayload, archivePayload);
    await fns.renderReports({ company_id: '901', start_date: '2026-01-01', end_date: '2026-02-01', sector: 'Obras' });
  });
  out.renderFromForm = await render(async (env, fns) => {
    fill(env, { 'report-unit': '2', end_date: '2026-03-01' });
    env.replies.push({ ...reportPayload, employee_fichas: [], by_tipo_vinculo: undefined }, { items: [], total: 0 });
    await fns.renderReports();
  });
  out.renderSemPermissao = await render(async (env, fns) => { env.perms.clear(); await fns.renderReports({}); });
  out.render403 = await render(async (env, fns) => { env.replies.push(httpError(403, 'proibido')); await fns.renderReports({}); });
  out.render500 = await render(async (env, fns) => { env.replies.push(httpError(500, 'quebrou')); await fns.renderReports({}); });
  out.renderSemFichasRef = await render(async (env, fns) => {
    delete env.refs.reportEmployeeFichas; env.replies.push(reportPayload); await fns.renderReports({});
  });
  out.archive403 = await render(async (env, fns) => { env.replies.push(httpError(403, 'x')); await fns.loadArchiveReports({ unit_id: '1' }); });
  out.archiveErro = await render(async (env, fns) => { env.replies.push(httpError(502, 'gateway')); await fns.loadArchiveReports({}); });
  out.archiveSemPermissao = await render(async (env, fns) => { env.perms.clear(); await fns.loadArchiveReports({}); });
  out.archiveSemTabela = await render(async (env, fns) => {
    delete env.refs.reportArchiveTable; env.state.reportArchiveItems = [{}]; fns.renderArchiveTable();
  });
  out.badges = (() => { const fns = run(makeEnv()); return ['active', 'expired', 'archived', 'purged', '', undefined, 'outro'].map((s) => fns.retentionStatusBadge(s)); })();

  const sync = (prep) => { const env = makeEnv(); const fns = run(env); prep(env); fns.syncReportOptions(); return snapshot(env); };
  out.syncLivre = sync((env) => { env.nodes['report-company'].value = '901'; env.nodes['report-unit'].value = '2'; env.nodes['report-employee'].value = '12'; });
  out.syncTrocaUnidade = sync((env) => { env.nodes['report-unit'].value = '1'; env.nodes['report-employee'].value = '12'; });
  out.syncOperacional = sync((env) => { env.operational = true; env.state.user.operational_unit_id = '2'; });
  out.syncOperacionalSemUnidade = sync((env) => { env.operational = true; });
  out.syncSemCampos = sync((env) => { delete env.nodes['report-employee']; });

  const pdf = (prep) => { const env = makeEnv(); const fns = run(env); prep(env); fns.exportReportPdf(); return snapshot(env).log; };
  out.pdfOk = pdf((env) => { env.nodes['report-company'].value = '901'; env.nodes.start_date.value = '2026-01-01'; });
  out.pdfInvalido = pdf((env) => { env.nodes['report-company'].value = 'abc'; });
  out.pdfSemPermissao = pdf((env) => { env.perms.clear(); });
  return out;
}

const EXPECTED = {
  collect: [{  }, { company_id: '901', unit_id: '1', sector: 'Obras', start_date: '2026-01-01', end_date: '2026-12-31' }, { erro: 'Filtro inv\u00e1lido: company_id deve ser num\u00e9rico.' }, { erro: 'Filtro inv\u00e1lido: unit_id deve ser num\u00e9rico.' }, { erro: 'Filtro inv\u00e1lido: start_date deve estar no formato AAAA-MM-DD.' }, { legal_entity_id: '5', employee_id: '12', tipo_vinculo: 'CLT', status: 'aberta' }, {  }],
  collectOrdem: [{ erro: 'Filtro inv\u00e1lido: company_id deve ser num\u00e9rico.' }, { erro: 'Filtro inv\u00e1lido: legal_entity_id deve ser num\u00e9rico.' }, { erro: 'Filtro inv\u00e1lido: unit_id deve ser num\u00e9rico.' }, { erro: 'Filtro inv\u00e1lido: employee_id deve ser num\u00e9rico.' }, { erro: 'Filtro inv\u00e1lido: epi_id deve ser num\u00e9rico.' }, { erro: 'Filtro inv\u00e1lido: start_date deve estar no formato AAAA-MM-DD.' }, { erro: 'Filtro inv\u00e1lido: end_date deve estar no formato AAAA-MM-DD.' }],
  renderOk: { nodes: { 'report-company': ['', '', '', false, null], 'report-unit': ['', '', '', false, null], 'report-employee': ['', '', '', false, null], 'report-unit-hint': ['', '', '', false, null], 'report-legal-entity': ['', '', '', false, null], 'report-sector': ['', '', '', false, null], 'report-tipo-vinculo': ['', '', '', false, null], 'report-epi': ['', '', '', false, null], 'report-ficha-status': ['', '', '', false, null], 'report-tipo-vinculo-summary': ['', '<div class="report-row"><strong>CLT</strong> 3</div>', '', false, null], start_date: ['', '', '', false, null], end_date: ['', '', '', false, null] }, refs: { reportSummary: ['', '<div class="summary-item"><strong>Entregas:</strong> 3</div><div class="summary-item"><strong>Total entregue:</strong> 9</div>', '', false, null], reportUnits: ['', '<div class="report-row"><strong>Base A</strong> 2</div>', '', false, null], reportSectors: ['', '<div class="summary-item">Sem dados.</div>', '', false, null], reportEmployeeFichas: ['', '<div class="summary-item"><strong>Ana (E1)</strong><div>Per\u00edodo: D(2026-01-01) a D(2026-01-31) | Status: aberta</div><div>Unidade: - | Itens: 2 | Quantidade total: 4</div></div>', '', false, null], reportArchiveTable: ['', '\u000a    <tr>\u000a      <td>DT(G)</td>\u000a      <td>Ana (E1)</td>\u000a      <td>C</td>\u000a      <td>-</td>\u000a      <td>[status|warning|expirada]</td>\u000a      <td><code>abcdef012345...</code></td>\u000a      <td>\u000a        <div class="action-group">\u000a          <button class="ghost" data-archive-view="5">Visualizar</button>\u000a          <button class="ghost" data-archive-print="5">Imprimir</button>\u000a          <button class="ghost" data-archive-export="5">Exportar</button>\u000a        </div>\u000a      </td>\u000a    </tr>\u000a  ', '', false, null], reportArchivePagination: ['', '', 'Registros: 1 | P\u00e1gina 2', false, null] }, log: [['hasPermission', 'reports:view'], ['api', '/api/reports?company_id=901&start_date=2026-01-01&end_date=2026-02-01&sector=Obras&actor_user_id=7'], ['hasPermission', 'reports:view'], ['api', '/api/ficha-archive?company_id=901&unit_id=&employee_id=&sector=Obras&status=&date_from=2026-01-01&date_to=2026-02-01&page=2&page_size=25&actor_user_id=7']], reports: { deliveries: [1, 2, 3], total_quantity: 9, by_unit: { 'Base A': 2 }, by_sector: {  }, by_tipo_vinculo: { CLT: 3 }, employee_fichas: [{ employee_name: 'Ana', employee_id_code: 'E1', period_start: '2026-01-01', period_end: '2026-01-31', status: 'aberta', unit_name: '', total_items: 2, total_quantity: 4 }] }, archive: [[{ id: 5, generated_at: 'G', employee_name: 'Ana', employee_id_code: 'E1', company_name: 'C', unit_name: '', status: 'expired', html_sha256: 'abcdef0123456789zz' }], 1, { keep: 'new' }] },
  renderFromForm: { nodes: { 'report-company': ['', '', '', false, null], 'report-unit': ['2', '', '', false, null], 'report-employee': ['', '', '', false, null], 'report-unit-hint': ['', '', '', false, null], 'report-legal-entity': ['', '', '', false, null], 'report-sector': ['', '', '', false, null], 'report-tipo-vinculo': ['', '', '', false, null], 'report-epi': ['', '', '', false, null], 'report-ficha-status': ['', '', '', false, null], 'report-tipo-vinculo-summary': ['', '<div class="summary-item">Sem dados.</div>', '', false, null], start_date: ['', '', '', false, null], end_date: ['2026-03-01', '', '', false, null] }, refs: { reportSummary: ['', '<div class="summary-item"><strong>Entregas:</strong> 3</div><div class="summary-item"><strong>Total entregue:</strong> 9</div>', '', false, null], reportUnits: ['', '<div class="report-row"><strong>Base A</strong> 2</div>', '', false, null], reportSectors: ['', '<div class="summary-item">Sem dados.</div>', '', false, null], reportEmployeeFichas: ['', '<div class="summary-item">Selecione um colaborador para visualizar as fichas de EPI.</div>', '', false, null], reportArchiveTable: ['', '<tr><td colspan="7">Sem fichas arquivadas para os filtros informados.</td></tr>', '', false, null], reportArchivePagination: ['', '', 'Registros: 0 | P\u00e1gina 2', false, null] }, log: [['hasPermission', 'reports:view'], ['api', '/api/reports?unit_id=2&end_date=2026-03-01&actor_user_id=7'], ['hasPermission', 'reports:view'], ['api', '/api/ficha-archive?company_id=&unit_id=2&employee_id=&sector=&status=&date_from=&date_to=2026-03-01&page=2&page_size=25&actor_user_id=7']], reports: { deliveries: [1, 2, 3], total_quantity: 9, by_unit: { 'Base A': 2 }, by_sector: {  }, employee_fichas: [] }, archive: [[], 0, { keep: 'old' }] },
  renderSemPermissao: { nodes: { 'report-company': ['', '', '', false, null], 'report-unit': ['', '', '', false, null], 'report-employee': ['', '', '', false, null], 'report-unit-hint': ['', '', '', false, null], 'report-legal-entity': ['', '', '', false, null], 'report-sector': ['', '', '', false, null], 'report-tipo-vinculo': ['', '', '', false, null], 'report-epi': ['', '', '', false, null], 'report-ficha-status': ['', '', '', false, null], 'report-tipo-vinculo-summary': ['', '', '', false, null], start_date: ['', '', '', false, null], end_date: ['', '', '', false, null] }, refs: { reportSummary: ['', '', '', false, null], reportUnits: ['', '', '', false, null], reportSectors: ['', '', '', false, null], reportEmployeeFichas: ['', '', '', false, null], reportArchiveTable: ['', '', '', false, null], reportArchivePagination: ['', '', '', false, null] }, log: [['hasPermission', 'reports:view'], ['skipped', 'reports', 'missing_permission', { permission: 'reports:view' }]], archive: [null, null, { keep: 'old' }] },
  render403: { nodes: { 'report-company': ['', '', '', false, null], 'report-unit': ['', '', '', false, null], 'report-employee': ['', '', '', false, null], 'report-unit-hint': ['', '', '', false, null], 'report-legal-entity': ['', '', '', false, null], 'report-sector': ['', '', '', false, null], 'report-tipo-vinculo': ['', '', '', false, null], 'report-epi': ['', '', '', false, null], 'report-ficha-status': ['', '', '', false, null], 'report-tipo-vinculo-summary': ['', '', '', false, null], start_date: ['', '', '', false, null], end_date: ['', '', '', false, null] }, refs: { reportSummary: ['', '', '', false, null], reportUnits: ['', '', '', false, null], reportSectors: ['', '', '', false, null], reportEmployeeFichas: ['', '', '', false, null], reportArchiveTable: ['', '', '', false, null], reportArchivePagination: ['', '', '', false, null] }, log: [['hasPermission', 'reports:view'], ['api', '/api/reports?actor_user_id=7'], ['skipped', 'reports', 'forbidden', { status: 403, permission: 'reports:view' }]], archive: [null, null, { keep: 'old' }] },
  render500: { nodes: { 'report-company': ['', '', '', false, null], 'report-unit': ['', '', '', false, null], 'report-employee': ['', '', '', false, null], 'report-unit-hint': ['', '', '', false, null], 'report-legal-entity': ['', '', '', false, null], 'report-sector': ['', '', '', false, null], 'report-tipo-vinculo': ['', '', '', false, null], 'report-epi': ['', '', '', false, null], 'report-ficha-status': ['', '', '', false, null], 'report-tipo-vinculo-summary': ['', '', '', false, null], start_date: ['', '', '', false, null], end_date: ['', '', '', false, null] }, refs: { reportSummary: ['', '<div class="summary-item hint">N\u00e3o foi poss\u00edvel carregar os relat\u00f3rios agora. Tente novamente.</div>', '', false, null], reportUnits: ['', '', '', false, null], reportSectors: ['', '', '', false, null], reportEmployeeFichas: ['', '', '', false, null], reportArchiveTable: ['', '', '', false, null], reportArchivePagination: ['', '', '', false, null] }, log: [['hasPermission', 'reports:view'], ['api', '/api/reports?actor_user_id=7'], ['nonCritical', '[renderReports] falha ao carregar relat\u00f3rio', 'quebrou']], archive: [null, null, { keep: 'old' }] },
  renderSemFichasRef: { nodes: { 'report-company': ['', '', '', false, null], 'report-unit': ['', '', '', false, null], 'report-employee': ['', '', '', false, null], 'report-unit-hint': ['', '', '', false, null], 'report-legal-entity': ['', '', '', false, null], 'report-sector': ['', '', '', false, null], 'report-tipo-vinculo': ['', '', '', false, null], 'report-epi': ['', '', '', false, null], 'report-ficha-status': ['', '', '', false, null], 'report-tipo-vinculo-summary': ['', '<div class="report-row"><strong>CLT</strong> 3</div>', '', false, null], start_date: ['', '', '', false, null], end_date: ['', '', '', false, null] }, refs: { reportSummary: ['', '<div class="summary-item"><strong>Entregas:</strong> 3</div><div class="summary-item"><strong>Total entregue:</strong> 9</div>', '', false, null], reportUnits: ['', '<div class="report-row"><strong>Base A</strong> 2</div>', '', false, null], reportSectors: ['', '<div class="summary-item">Sem dados.</div>', '', false, null], reportArchiveTable: ['', '', '', false, null], reportArchivePagination: ['', '', '', false, null] }, log: [['hasPermission', 'reports:view'], ['api', '/api/reports?actor_user_id=7']], reports: { deliveries: [1, 2, 3], total_quantity: 9, by_unit: { 'Base A': 2 }, by_sector: {  }, by_tipo_vinculo: { CLT: 3 }, employee_fichas: [{ employee_name: 'Ana', employee_id_code: 'E1', period_start: '2026-01-01', period_end: '2026-01-31', status: 'aberta', unit_name: '', total_items: 2, total_quantity: 4 }] }, archive: [null, null, { keep: 'old' }] },
  archive403: { nodes: { 'report-company': ['', '', '', false, null], 'report-unit': ['', '', '', false, null], 'report-employee': ['', '', '', false, null], 'report-unit-hint': ['', '', '', false, null], 'report-legal-entity': ['', '', '', false, null], 'report-sector': ['', '', '', false, null], 'report-tipo-vinculo': ['', '', '', false, null], 'report-epi': ['', '', '', false, null], 'report-ficha-status': ['', '', '', false, null], 'report-tipo-vinculo-summary': ['', '', '', false, null], start_date: ['', '', '', false, null], end_date: ['', '', '', false, null] }, refs: { reportSummary: ['', '', '', false, null], reportUnits: ['', '', '', false, null], reportSectors: ['', '', '', false, null], reportEmployeeFichas: ['', '', '', false, null], reportArchiveTable: ['', '', '', false, null], reportArchivePagination: ['', '', '', false, null] }, log: [['hasPermission', 'reports:view'], ['api', '/api/ficha-archive?unit_id=1&page=2&page_size=25&actor_user_id=7'], ['skipped', 'report_archive', 'forbidden', { status: 403, permission: 'reports:view' }]], archive: [null, null, { keep: 'old' }] },
  archiveErro: { nodes: { 'report-company': ['', '', '', false, null], 'report-unit': ['', '', '', false, null], 'report-employee': ['', '', '', false, null], 'report-unit-hint': ['', '', '', false, null], 'report-legal-entity': ['', '', '', false, null], 'report-sector': ['', '', '', false, null], 'report-tipo-vinculo': ['', '', '', false, null], 'report-epi': ['', '', '', false, null], 'report-ficha-status': ['', '', '', false, null], 'report-tipo-vinculo-summary': ['', '', '', false, null], start_date: ['', '', '', false, null], end_date: ['', '', '', false, null] }, refs: { reportSummary: ['', '', '', false, null], reportUnits: ['', '', '', false, null], reportSectors: ['', '', '', false, null], reportEmployeeFichas: ['', '', '', false, null], reportArchiveTable: ['', '<tr><td colspan="7">Sem fichas arquivadas para os filtros informados.</td></tr>', '', false, null], reportArchivePagination: ['', '', 'Registros: 0 | P\u00e1gina 2', false, null] }, log: [['hasPermission', 'reports:view'], ['api', '/api/ficha-archive?page=2&page_size=25&actor_user_id=7'], ['nonCritical', '[loadArchiveReports] falha ao carregar arquivo', 'gateway']], archive: [[], 0, { keep: 'old' }] },
  archiveSemPermissao: { nodes: { 'report-company': ['', '', '', false, null], 'report-unit': ['', '', '', false, null], 'report-employee': ['', '', '', false, null], 'report-unit-hint': ['', '', '', false, null], 'report-legal-entity': ['', '', '', false, null], 'report-sector': ['', '', '', false, null], 'report-tipo-vinculo': ['', '', '', false, null], 'report-epi': ['', '', '', false, null], 'report-ficha-status': ['', '', '', false, null], 'report-tipo-vinculo-summary': ['', '', '', false, null], start_date: ['', '', '', false, null], end_date: ['', '', '', false, null] }, refs: { reportSummary: ['', '', '', false, null], reportUnits: ['', '', '', false, null], reportSectors: ['', '', '', false, null], reportEmployeeFichas: ['', '', '', false, null], reportArchiveTable: ['', '', '', false, null], reportArchivePagination: ['', '', '', false, null] }, log: [['hasPermission', 'reports:view'], ['skipped', 'report_archive', 'missing_permission', { permission: 'reports:view' }]], archive: [null, null, { keep: 'old' }] },
  archiveSemTabela: { nodes: { 'report-company': ['', '', '', false, null], 'report-unit': ['', '', '', false, null], 'report-employee': ['', '', '', false, null], 'report-unit-hint': ['', '', '', false, null], 'report-legal-entity': ['', '', '', false, null], 'report-sector': ['', '', '', false, null], 'report-tipo-vinculo': ['', '', '', false, null], 'report-epi': ['', '', '', false, null], 'report-ficha-status': ['', '', '', false, null], 'report-tipo-vinculo-summary': ['', '', '', false, null], start_date: ['', '', '', false, null], end_date: ['', '', '', false, null] }, refs: { reportSummary: ['', '', '', false, null], reportUnits: ['', '', '', false, null], reportSectors: ['', '', '', false, null], reportEmployeeFichas: ['', '', '', false, null], reportArchivePagination: ['', '', '', false, null] }, log: [], archive: [[{  }], null, { keep: 'old' }] },
  badges: ['[status|active|arquivada]', '[status|warning|expirada]', '[status|active|arquivada]', '[status|inactive|purgada]', '[status|active|arquivada]', '[status|active|arquivada]', '[status|active|arquivada]'],
  syncLivre: { nodes: { 'report-company': ['901', '', '', false, null], 'report-unit': ['2', '<option value="">Todas</option><option value="1">Base A</option><option value="2">Base B</option>', '', false, null], 'report-employee': ['12', '<option value="">Todos os colaboradores</option><option value="12">E2 - Bia</option>', '', false, null], 'report-unit-hint': ['', '', '', false, 'none'], 'report-legal-entity': ['', '', '', false, null], 'report-sector': ['', '', '', false, null], 'report-tipo-vinculo': ['', '', '', false, null], 'report-epi': ['', '', '', false, null], 'report-ficha-status': ['', '', '', false, null], 'report-tipo-vinculo-summary': ['', '', '', false, null], start_date: ['', '', '', false, null], end_date: ['', '', '', false, null] }, refs: { reportSummary: ['', '', '', false, null], reportUnits: ['', '', '', false, null], reportSectors: ['', '', '', false, null], reportEmployeeFichas: ['', '', '', false, null], reportArchiveTable: ['', '', '', false, null], reportArchivePagination: ['', '', '', false, null] }, log: [['syncLegalEntity']], archive: [null, null, { keep: 'old' }] },
  syncTrocaUnidade: { nodes: { 'report-company': ['', '', '', false, null], 'report-unit': ['1', '<option value="">Todas</option><option value="1">Base A</option><option value="2">Base B</option>', '', false, null], 'report-employee': ['', '<option value="">Todos os colaboradores</option><option value="11">E1 - Ana</option>', '', false, null], 'report-unit-hint': ['', '', '', false, 'none'], 'report-legal-entity': ['', '', '', false, null], 'report-sector': ['', '', '', false, null], 'report-tipo-vinculo': ['', '', '', false, null], 'report-epi': ['', '', '', false, null], 'report-ficha-status': ['', '', '', false, null], 'report-tipo-vinculo-summary': ['', '', '', false, null], start_date: ['', '', '', false, null], end_date: ['', '', '', false, null] }, refs: { reportSummary: ['', '', '', false, null], reportUnits: ['', '', '', false, null], reportSectors: ['', '', '', false, null], reportEmployeeFichas: ['', '', '', false, null], reportArchiveTable: ['', '', '', false, null], reportArchivePagination: ['', '', '', false, null] }, log: [['syncLegalEntity']], archive: [null, null, { keep: 'old' }] },
  syncOperacional: { nodes: { 'report-company': ['901', '', '', true, null], 'report-unit': ['2', '<option value="2">Base B</option>', '', true, null], 'report-employee': ['', '<option value="">Todos os colaboradores</option><option value="12">E2 - Bia</option>', '', false, null], 'report-unit-hint': ['', '', '', false, 'block'], 'report-legal-entity': ['', '', '', false, null], 'report-sector': ['', '', '', false, null], 'report-tipo-vinculo': ['', '', '', false, null], 'report-epi': ['', '', '', false, null], 'report-ficha-status': ['', '', '', false, null], 'report-tipo-vinculo-summary': ['', '', '', false, null], start_date: ['', '', '', false, null], end_date: ['', '', '', false, null] }, refs: { reportSummary: ['', '', '', false, null], reportUnits: ['', '', '', false, null], reportSectors: ['', '', '', false, null], reportEmployeeFichas: ['', '', '', false, null], reportArchiveTable: ['', '', '', false, null], reportArchivePagination: ['', '', '', false, null] }, log: [['syncLegalEntity']], archive: [null, null, { keep: 'old' }] },
  syncOperacionalSemUnidade: { nodes: { 'report-company': ['901', '', '', true, null], 'report-unit': ['', '<option value="">Sem unidade operacional ativa</option>', '', true, null], 'report-employee': ['', '<option value="">Todos os colaboradores</option><option value="11">E1 - Ana</option><option value="12">E2 - Bia</option>', '', false, null], 'report-unit-hint': ['', '', '', false, 'block'], 'report-legal-entity': ['', '', '', false, null], 'report-sector': ['', '', '', false, null], 'report-tipo-vinculo': ['', '', '', false, null], 'report-epi': ['', '', '', false, null], 'report-ficha-status': ['', '', '', false, null], 'report-tipo-vinculo-summary': ['', '', '', false, null], start_date: ['', '', '', false, null], end_date: ['', '', '', false, null] }, refs: { reportSummary: ['', '', '', false, null], reportUnits: ['', '', '', false, null], reportSectors: ['', '', '', false, null], reportEmployeeFichas: ['', '', '', false, null], reportArchiveTable: ['', '', '', false, null], reportArchivePagination: ['', '', '', false, null] }, log: [['syncLegalEntity']], archive: [null, null, { keep: 'old' }] },
  syncSemCampos: { nodes: { 'report-company': ['', '', '', false, null], 'report-unit': ['', '', '', false, null], 'report-unit-hint': ['', '', '', false, null], 'report-legal-entity': ['', '', '', false, null], 'report-sector': ['', '', '', false, null], 'report-tipo-vinculo': ['', '', '', false, null], 'report-epi': ['', '', '', false, null], 'report-ficha-status': ['', '', '', false, null], 'report-tipo-vinculo-summary': ['', '', '', false, null], start_date: ['', '', '', false, null], end_date: ['', '', '', false, null] }, refs: { reportSummary: ['', '', '', false, null], reportUnits: ['', '', '', false, null], reportSectors: ['', '', '', false, null], reportEmployeeFichas: ['', '', '', false, null], reportArchiveTable: ['', '', '', false, null], reportArchivePagination: ['', '', '', false, null] }, log: [['syncLegalEntity']], archive: [null, null, { keep: 'old' }] },
  pdfOk: [['requirePermission', 'reports:view'], ['open', '/api/reports.pdf?actor_user_id=7&company_id=901&start_date=2026-01-01', '_blank']],
  pdfInvalido: [['requirePermission', 'reports:view'], ['alert', 'Filtro inv\u00e1lido: company_id deve ser num\u00e9rico.']],
  pdfSemPermissao: [['requirePermission', 'reports:view']]
};

function loadModules(env) {
  const ctx = contextFor(env);
  for (const rel of MODULES) { vm.runInContext(fs.readFileSync(path.join(JS_ROOT, rel), 'utf8'), ctx); }
  return ctx;
}

module.exports = function ({ testAsync, test, assert, eq }) {
  testAsync('UBX-V3 relatórios: os módulos reproduzem as funções originais do app.js', async () => {
    const actual = await scenario(loadModules);
    for (const key of Object.keys(EXPECTED)) {
      eq(JSON.stringify(actual[key]), JSON.stringify(EXPECTED[key]), key);
    }
    eq(Object.keys(actual).sort().join(','), Object.keys(EXPECTED).sort().join(','));
  });

  test('UBX-V3 relatórios: camadas, namespaces e ordem de carga', () => {
    const ctx = loadModules(makeEnv());
    for (const name of NAMES) { eq(typeof ctx[name], 'function', name); }
    assert(Object.isFrozen(ctx.__EPI_REPORTS_VIEW__) && Object.isFrozen(ctx.__EPI_REPORTS_API__)
      && Object.isFrozen(ctx.__EPI_REPORTS_BUSINESS__), 'namespaces congelados');
    for (const ns of ['normalizeReportFilterValues', 'archiveFiltersFromReportFilters']) {
      assert(!(ns in ctx), `${ns} fica só no namespace de negócio (sem global novo)`);
    }
    const scripts = fs.readFileSync(path.resolve(JS_ROOT, '..', 'views', '_scripts.html'), 'utf8');
    const order = [...scripts.matchAll(/<script[^>]+src="([^"?]+)/g)].map((m) => m[1]);
    const idx = MODULES.map((m) => order.indexOf(`/js/${m}`));
    assert(idx.every((i) => i >= 0), 'módulos listados');
    assert(idx[0] < idx[1] && idx[1] < idx[2], 'business → integrations → ui');
    assert(idx[2] < order.indexOf('/app.js'), 'antes do app.js');
    const app = fs.readFileSync(path.resolve(JS_ROOT, '..', 'app.js'), 'utf8');
    for (const name of NAMES) {
      assert(!new RegExp(`^(?:async\\s+)?function\\s+${name}\\(`, 'm').test(app), `${name} voltou ao app.js`);
    }
    for (const endpoint of ['/api/reports?', '/api/ficha-archive?', '/api/reports.pdf?']) {
      assert(!app.includes(endpoint), `${endpoint} saiu do app.js`);
    }
  });
};

module.exports.scenario = scenario;
module.exports.makeEnv = makeEnv;
module.exports.contextFor = contextFor;
