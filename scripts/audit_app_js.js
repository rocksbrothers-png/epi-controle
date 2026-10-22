#!/usr/bin/env node
'use strict';
/**
 * Auditoria estrutural de static/app.js (Refatoração UBX — Etapa A).
 *
 * Lê o monólito via AST (acorn, dependência transitiva do eslint — `npm ci`) e produz um inventário JSON com: declarações de nível superior,
 * tamanho, dependências internas, efeitos (DOM, HTTP, estado, storage,
 * listeners, RBAC), domínio inferido, ciclos (SCC) e candidatos a extração
 * (funções puras — sem DOM, HTTP, estado nem storage, cujas dependências
 * internas também são puras).
 *
 * Uso:
 *   node scripts/audit_app_js.js [static/app.js] [--json saida.json] [--summary]
 *
 * Não altera nenhum arquivo do app. Ferramenta de leitura apenas.
 */
const fs = require('fs');
const path = require('path');

function loadAcorn() {
  const candidates = [
    'acorn',
    path.join(__dirname, '..', 'node_modules', 'acorn'),
    '/opt/node-tools/node_modules/acorn'
  ];
  for (const c of candidates) {
    try { return require(c); } catch (_e) { /* tenta o próximo */ }
  }
  throw new Error('acorn não encontrado — rode `npm ci` (vem com eslint).');
}
const acorn = loadAcorn();
// Caminhada genérica pela AST (dispensa acorn-walk, que não vem com o eslint).
function walkFull(node, visit) {
  if (!node || typeof node.type !== 'string') { return; }
  visit(node);
  for (const key of Object.keys(node)) {
    if (key === 'loc') { continue; }
    const child = node[key];
    if (Array.isArray(child)) {
      for (const c of child) { if (c && typeof c.type === 'string') { walkFull(c, visit); } }
    } else if (child && typeof child.type === 'string') {
      walkFull(child, visit);
    }
  }
}

// Domínios funcionais reais (mapeados a partir das VIEW_PERMISSIONS e dos
// prefixos de nomes encontrados no app.js). A ordem importa: o primeiro
// padrão que casa vence.
const DOMAIN_RULES = [
  ['migracao', /migration|migracao/i],
  ['auth', /login|logout|session|token|password|auth|credential|bootstrap/i],
  ['permissions', /permission|role|rbac|canAccess|canManage|isAdmin|hasPerm|allowed/i],
  ['portal', /portal|selfService/i],
  ['compras', /purchase|procurement|quotation|supplier|buyer|approver|finance|order/i],
  ['estoque', /stock|estoque|lot|inventory|balance|movement|validity|minimum/i],
  ['entregas', /deliver|entrega|handover|signature|devolution|return/i],
  ['fichas', /ficha|receipt|comprovante|document/i],
  ['epis', /\bepi|Epi|ppe|catalog|archive|ca[A-Z]/],
  ['colaboradores', /employee|colab|outsourced|terceir|worker|transfer/i],
  ['empresas', /company|companies|tenant|legalEntit|cnpj|unit|unidade|commercial|license|brand|logo/i],
  ['usuarios', /user/i],
  ['relatorios', /report|relatorio|export|csv|pdf|chart|dashboard|alert/i],
  ['biblioteca', /safety|library|biblioteca/i],
  ['feedback', /feedback|evaluation|avalia|test/i],
  ['configuracao', /config|setting|flag|feature|module|visibility/i],
  ['navegacao', /view|nav|route|menu|tab|modal|render|refresh/i],
  ['i18n', /\btr\b|i18n|translat/i],
  ['shared', /.*/]
];

function inferDomain(name) {
  for (const [domain, re] of DOMAIN_RULES) { if (re.test(name)) { return domain; } }
  return 'shared';
}

function declNames(stmt) {
  if (stmt.type === 'FunctionDeclaration' && stmt.id) { return [stmt.id.name]; }
  if (stmt.type === 'VariableDeclaration') {
    const out = [];
    for (const d of stmt.declarations) {
      if (d.id.type === 'Identifier') { out.push(d.id.name); }
    }
    return out;
  }
  return [];
}

function analyze(file) {
  const src = fs.readFileSync(file, 'utf8');
  const ast = acorn.parse(src, { ecmaVersion: 'latest', sourceType: 'script', locations: true });
  // app.js é envolto em `if (!globalThis.__EPI_APP_RUNTIME_LOADED__) { ... }`.
  let body = ast.body;
  let guarded = false;
  if (body.length === 1 && body[0].type === 'IfStatement' && body[0].consequent.type === 'BlockStatement') {
    body = body[0].consequent.body;
    guarded = true;
  }

  const decls = [];
  const byName = new Map();
  const topLevelSideEffects = [];
  for (const stmt of body) {
    const names = declNames(stmt);
    if (!names.length) {
      topLevelSideEffects.push({ type: stmt.type, line: stmt.loc.start.line, endLine: stmt.loc.end.line });
      continue;
    }
    for (const name of names) {
      const d = {
        name,
        kind: stmt.type === 'FunctionDeclaration' ? (stmt.async ? 'async function' : 'function') : stmt.kind,
        line: stmt.loc.start.line,
        endLine: stmt.loc.end.line,
        lines: stmt.loc.end.line - stmt.loc.start.line + 1,
        node: stmt
      };
      decls.push(d);
      byName.set(name, d);
    }
  }

  const exportedToGlobal = new Set();
  // globalThis.X = X / window.X = X em qualquer ponto do arquivo.
  walkFull(ast, (n) => {
    if (n.type === 'AssignmentExpression' && n.left.type === 'MemberExpression'
      && n.left.object.type === 'Identifier' && ['globalThis', 'window'].includes(n.left.object.name)
      && !n.left.computed && n.left.property.type === 'Identifier') {
      exportedToGlobal.add(n.left.property.name);
    }
  });

  for (const d of decls) {
    const deps = new Set();
    const fx = { dom: 0, http: 0, state: 0, storage: 0, listeners: 0, rbac: 0, globalWrites: 0, throws: 0, tryCatch: 0 };
    walkFull(d.node, (n) => {
      if (n.type === 'Identifier' && byName.has(n.name) && n.name !== d.name) { deps.add(n.name); }
      if (n.type === 'MemberExpression' && n.object.type === 'Identifier') {
        const o = n.object.name;
        const p = n.property && (n.property.name || n.property.value);
        if (o === 'document' || o === 'refs') { fx.dom++; }
        if (o === 'state') { fx.state++; }
        if (o === 'localStorage' || o === 'sessionStorage') { fx.storage++; }
        if ((o === 'globalThis' || o === 'window') && p === '__EPI_APP_STATE__') { fx.state++; }
      }
      if (n.type === 'MemberExpression' && !n.computed && n.property.type === 'Identifier') {
        if (['innerHTML', 'textContent', 'classList', 'querySelector', 'querySelectorAll', 'appendChild', 'setAttribute', 'hidden', 'disabled'].includes(n.property.name)) { fx.dom++; }
        if (n.property.name === 'addEventListener') { fx.listeners++; }
      }
      if (n.type === 'CallExpression' && n.callee.type === 'Identifier') {
        const c = n.callee.name;
        if (/^(api|apiFetch|apiWithBootstrapRetry|apiOptional|apiFetchWithRetry|apiFetchOptional|fetch)$/.test(c)) { fx.http++; }
        if (/^(hasPermission|hasAnyPermission|canAccessView|currentRole|isMasterAdmin)$/.test(c)) { fx.rbac++; }
      }
      if (n.type === 'AssignmentExpression' && n.left.type === 'MemberExpression'
        && n.left.object.type === 'Identifier' && ['globalThis', 'window'].includes(n.left.object.name)) { fx.globalWrites++; }
      if (n.type === 'ThrowStatement') { fx.throws++; }
      if (n.type === 'TryStatement') { fx.tryCatch++; }
    });
    d.deps = [...deps].sort();
    d.effects = fx;
    d.domain = inferDomain(d.name);
    d.exportedToGlobal = exportedToGlobal.has(d.name);
  }

  // Dependentes (fan-in).
  for (const d of decls) { d.dependents = []; }
  for (const d of decls) { for (const dep of d.deps) { byName.get(dep).dependents.push(d.name); } }

  // SCC (Tarjan) para ciclos.
  let index = 0; const stack = []; const idx = new Map(); const low = new Map(); const on = new Set(); const sccs = [];
  function strong(v) {
    idx.set(v, index); low.set(v, index); index++; stack.push(v); on.add(v);
    for (const w of byName.get(v).deps) {
      if (!idx.has(w)) { strong(w); low.set(v, Math.min(low.get(v), low.get(w))); } else if (on.has(w)) { low.set(v, Math.min(low.get(v), idx.get(w))); }
    }
    if (low.get(v) === idx.get(v)) {
      const comp = []; let w;
      do { w = stack.pop(); on.delete(w); comp.push(w); } while (w !== v);
      if (comp.length > 1) { sccs.push(comp.sort()); }
    }
  }
  for (const d of decls) { if (!idx.has(d.name)) { strong(d.name); } }

  // Pureza (ponto fixo): sem efeitos e só depende de puras / constantes.
  const impure = (d) => d.effects.dom || d.effects.http || d.effects.state || d.effects.storage || d.effects.listeners || d.effects.globalWrites;
  const pure = new Set(decls.filter((d) => !impure(d)).map((d) => d.name));
  let changed = true;
  while (changed) {
    changed = false;
    for (const n of [...pure]) {
      if (byName.get(n).deps.some((dep) => !pure.has(dep))) { pure.delete(n); changed = true; }
    }
  }
  for (const d of decls) { d.pure = pure.has(d.name); }

  return { file, totalLines: src.split('\n').length, guarded, decls, topLevelSideEffects, sccs, exportedToGlobal: [...exportedToGlobal].sort() };
}

function summarize(r) {
  const byKind = {}; const byDomain = {};
  for (const d of r.decls) {
    byKind[d.kind] = (byKind[d.kind] || 0) + 1;
    const b = byDomain[d.domain] || (byDomain[d.domain] = { decls: 0, lines: 0, http: 0, dom: 0, pure: 0 });
    b.decls++; b.lines += d.lines; b.http += d.effects.http ? 1 : 0; b.dom += d.effects.dom ? 1 : 0; b.pure += d.pure ? 1 : 0;
  }
  const totals = r.decls.reduce((a, d) => {
    for (const k of Object.keys(d.effects)) { a[k] = (a[k] || 0) + (d.effects[k] ? 1 : 0); }
    return a;
  }, {});
  const biggest = [...r.decls].sort((a, b) => b.lines - a.lines).slice(0, 25).map((d) => `${d.name} (${d.lines}l, L${d.line})`);
  const hubs = [...r.decls].sort((a, b) => b.dependents.length - a.dependents.length).slice(0, 25).map((d) => `${d.name} (fan-in ${d.dependents.length})`);
  const fanOut = [...r.decls].sort((a, b) => b.deps.length - a.deps.length).slice(0, 15).map((d) => `${d.name} (fan-out ${d.deps.length})`);
  return {
    file: r.file,
    totalLines: r.totalLines,
    guardedByRuntimeFlag: r.guarded,
    declarations: r.decls.length,
    byKind,
    byDomain,
    functionsWithEffect: totals,
    topLevelSideEffectStatements: r.topLevelSideEffects.length,
    globalExports: r.exportedToGlobal.length,
    cycles: r.sccs.length,
    largestCycle: r.sccs.reduce((m, c) => Math.max(m, c.length), 0),
    pureCandidates: r.decls.filter((d) => d.pure && d.kind.includes('function')).length,
    biggest,
    hubs,
    fanOut
  };
}

if (require.main === module) {
  const args = process.argv.slice(2);
  const file = args.find((a) => !a.startsWith('--') && !a.endsWith('.json')) || path.join(__dirname, '..', 'static', 'app.js');
  const r = analyze(file);
  const jsonIdx = args.indexOf('--json');
  if (jsonIdx >= 0 && args[jsonIdx + 1]) {
    const out = {
      summary: summarize(r),
      cycles: r.sccs,
      topLevelSideEffects: r.topLevelSideEffects,
      declarations: r.decls.map(({ node, ...rest }) => rest)
    };
    fs.writeFileSync(args[jsonIdx + 1], JSON.stringify(out, null, 2));
  }
  console.log(JSON.stringify(summarize(r), null, 2));
}

module.exports = { analyze, summarize, inferDomain };
