'use strict';

/**
 * Guarda arquitetural do monólito static/app.js (Refatoração UBX).
 *
 * Não mede linhas: mede RESPONSABILIDADES. O app.js só pode perder
 * responsabilidades, nunca ganhar:
 *
 *  1. Declarações de nível superior (funções, constantes, estado) — nenhuma
 *     nova além do baseline. Funcionalidade nova vai para
 *     static/js/modules/<domínio>/{ui,business,integrations}/.
 *  2. Endpoints HTTP (`'/api/...'`) — nenhuma integração nova no app.js.
 *  3. Catraca: o baseline não pode listar o que já saiu do app.js (rode com
 *     `--update` depois de uma extração; o modo update só REMOVE itens).
 *  4. Registro de extrações: cada nome extraído não pode voltar ao app.js,
 *     precisa existir no módulo dono e o módulo precisa ser carregado antes
 *     do app.js em static/views/_scripts.html.
 *  5. Regras de camada: arquivos em modules/<domínio>/business/ não tocam
 *     DOM, HTTP, storage nem o estado global do app, e não leem globais
 *     (entrada só por parâmetro); integrations/ não toca DOM.
 *  6. (UBX-V2) Catraca de endpoints na camada UI (static/js/views/,
 *     modules/<domínio>/ui/ e scripts de UI em static/*.js): nenhum endpoint
 *     `/api/` novo — integração nova vai para integrations/. Template literals
 *     contam com a sub-rota (`${id}` vira `{}`) e o prefixo solto '/api' usado
 *     para concatenar também é registrado.
 *  7. (UBX-V2) Dependências entre scripts, pelos namespaces `__EPI_*__` que
 *     cada um publica e consome: nenhum ciclo novo; business/ e
 *     integrations/ não dependem de namespaces publicados pela camada UI.
 *  8. (UBX-V2) Contra um novo monólito: nenhum arquivo em modules/ passa de
 *     MAX_MODULE_LINES linhas.
 *  9. (UBX-V3) Catraca de `fetch(` cru na camada UI: a contagem por arquivo
 *     só diminui — chamada de rede nova passa pelo cliente único
 *     (modules/api-client.js), nunca por um fetch próprio da view.
 *
 * Sem dependências: usa só a stdlib do Node.
 * Uso: node static/js/test/app-js-boundary.js [--update]
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..', '..');
const APP_JS = path.join(ROOT, 'static', 'app.js');
const SCRIPTS_HTML = path.join(ROOT, 'static', 'views', '_scripts.html');
const MODULES_DIR = path.join(ROOT, 'static', 'js', 'modules');
const BASELINE = path.join(__dirname, 'app-js-baseline.json');
const STATIC_DIR = path.join(ROOT, 'static');
const JS_DIR = path.join(STATIC_DIR, 'js');
const VIEWS_DIR = path.join(JS_DIR, 'views');
const MAX_MODULE_LINES = 500;
// Registros compartilhados por desenho (pontes do app, escritos por vários
// scripts) e flags de carga não são arestas de dependência entre módulos.
const SHARED_REGISTRIES = new Set(['__EPI_FRONTEND_HELPERS__', '__EPI_APP_STATE__', '__EPI_REFS__']);
const FLAG_RE = /_(?:LOADED|BOUND|ACTIVE)__$/;
const NAMESPACE_RE = /__EPI_[A-Z0-9_]+__/g;
const PUBLISH_RE = /\b(?:globalThis|window|self)\s*\.\s*(__EPI_[A-Z0-9_]+__)\s*=(?!=)/g;

// Toda declaração de nível superior do app.js começa na coluna 0 (o arquivo
// inteiro vive dentro de um único bloco `if` sem indentação). A contagem por
// este padrão bate com a da AST (scripts/audit_app_js.js).
const DECL_RE = /^(?:async\s+)?(?:function\*?|const|let|var|class)\s+([A-Za-z_$][\w$]*)/gm;
const ENDPOINT_RE = /['"`](\/api\/[^'"`?$\s]*)/g;
// Camada UI: template literal com a sub-rota (`/api/x/${id}/y` → /api/x/{}/y)
// e o prefixo solto ('/api' ou '/api/' sozinho, usado para concatenar).
const UI_TEMPLATE_RE = /`(\/api\/(?:[^`$?\s]|\$\{[^}]*\})*)/g;
const UI_PREFIX_RE = /['"`](\/api\/?)['"`]/g;
const UI_RAW_FETCH_RE = /(?<![\w$.])(?:(?:globalThis|window|self)\s*\.\s*)?fetch\s*\(/g;
// Globais do app.js (Annex B / var) que uma regra de negócio não pode ler.
const APP_GLOBALS_RE = /(?<![\w$.])(?:(?:state|refs)\s*(?:\.|\[|\?\.)|(?:tr|hasPermission|requirePermission|showToast|escapeHtml|esc|actorQuery)\s*\()/;

const LAYER_RULES = {
  business: [
    [/\bdocument\s*\./, 'DOM (document.*)'],
    [/\.innerHTML\b/, 'DOM (innerHTML)'],
    [/\b(?:fetch|api|apiFetch|apiOptional|apiWithBootstrapRetry)\s*\(/, 'HTTP'],
    [/\b(?:XMLHttpRequest|EventSource|WebSocket)\b|\.sendBeacon\s*\(/, 'HTTP'],
    [/\b(?:localStorage|sessionStorage)\b/, 'storage'],
    [/__EPI_APP_STATE__/, 'estado global do app'],
    // Leitura de global (exceto a própria flag de carga). Publicar o contrato
    // (`globalThis.x = ...` / `globalThis[name] = fn`) continua permitido.
    [/\b(?:globalThis|window|self)\s*\.\s*(?!__EPI_MODULE_[A-Z0-9_]+_LOADED__\b)[A-Za-z_$][\w$]*\b(?!\s*=(?!=))/, 'leitura de global (use parâmetros)'],
    [/\b(?:globalThis|window|self)\s*(?:\?\.\s*[\w$]+|\??\.?\s*\[[^\]]*\])(?!\s*=(?!=))/, 'leitura de global (use parâmetros)'],
    [APP_GLOBALS_RE, 'global do app.js (receba por parâmetro)']
  ],
  integrations: [
    [/\bdocument\s*\./, 'DOM (document.*)'],
    [/\.innerHTML\b/, 'DOM (innerHTML)']
  ]
};

function escapeRegExp(text) {
  return String(text).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function stripComments(code) {
  return code.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:\\])\/\/.*$/gm, '$1');
}

function scanAppJs(code) {
  const declarations = new Set();
  for (const m of code.matchAll(DECL_RE)) { declarations.add(m[1]); }
  const endpoints = new Set();
  for (const m of code.matchAll(ENDPOINT_RE)) { endpoints.add(m[1]); }
  return { declarations, endpoints };
}

function walkFiles(dir) {
  if (!fs.existsSync(dir)) { return []; }
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) { out.push(...walkFiles(full)); } else if (entry.name.endsWith('.js')) { out.push(full); }
  }
  return out;
}

function endpointsOf(code) {
  const out = new Set();
  for (const m of code.matchAll(ENDPOINT_RE)) { out.add(m[1]); }
  return out;
}

function uiEndpointsOf(code) {
  const out = endpointsOf(code);
  for (const m of code.matchAll(UI_TEMPLATE_RE)) { out.add(m[1].replace(/\$\{[^}]*\}/g, '{}')); }
  for (const m of code.matchAll(UI_PREFIX_RE)) { out.add(`${m[1]} (prefixo concatenado)`); }
  return out;
}

// Arquivos da camada UI: views/, modules/<domínio>/ui/ e os scripts de UI de
// nível superior em static/*.js (exceto o app.js, que tem regra própria).
function uiFiles() {
  const topLevel = fs.readdirSync(STATIC_DIR, { withFileTypes: true })
    .filter((e) => e.isFile() && e.name.endsWith('.js') && e.name !== 'app.js')
    .map((e) => path.join(STATIC_DIR, e.name));
  const moduleUi = walkFiles(MODULES_DIR).filter((f) => path.relative(MODULES_DIR, f).split(path.sep)[1] === 'ui');
  return [...walkFiles(VIEWS_DIR), ...moduleUi, ...topLevel];
}

function scanUiRawFetch() {
  const result = {};
  for (const file of uiFiles()) {
    const count = (stripComments(fs.readFileSync(file, 'utf-8')).match(UI_RAW_FETCH_RE) || []).length;
    if (count) { result[path.relative(STATIC_DIR, file).split(path.sep).join('/')] = count; }
  }
  return result;
}

function scanUiEndpoints() {
  const result = {};
  for (const file of uiFiles()) {
    const found = uiEndpointsOf(stripComments(fs.readFileSync(file, 'utf-8')));
    if (found.size) { result[path.relative(STATIC_DIR, file).split(path.sep).join('/')] = [...found].sort(); }
  }
  return result;
}

// Grafo arquivo → arquivo: A depende de B quando A lê um namespace que B
// publica (`globalThis.__EPI_X__ = ...`).
function namespaceGraph() {
  const topLevel = fs.readdirSync(STATIC_DIR, { withFileTypes: true })
    .filter((e) => e.isFile() && e.name.endsWith('.js')).map((e) => path.join(STATIC_DIR, e.name));
  const files = [...walkFiles(JS_DIR).filter((f) => !f.includes(`${path.sep}test${path.sep}`)), ...topLevel];
  const rel = (f) => path.relative(path.join(ROOT, 'static'), f).split(path.sep).join('/');
  const bodies = new Map(files.map((f) => [rel(f), stripComments(fs.readFileSync(f, 'utf-8'))]));
  const publisher = new Map();
  for (const [file, body] of bodies) {
    for (const m of body.matchAll(PUBLISH_RE)) {
      const ns = m[1];
      if (SHARED_REGISTRIES.has(ns) || FLAG_RE.test(ns)) { continue; }
      publisher.set(ns, file);
    }
  }
  const edges = new Map();
  for (const [file, body] of bodies) {
    const deps = new Map();
    for (const m of body.matchAll(NAMESPACE_RE)) {
      const owner = publisher.get(m[0]);
      if (owner && owner !== file) { deps.set(owner, m[0]); }
    }
    edges.set(file, deps);
  }
  return edges;
}

function findCycles(edges) {
  // Tarjan: componentes fortemente conexos com mais de um arquivo.
  let index = 0;
  const stack = [], onStack = new Set(), idx = new Map(), low = new Map(), cycles = [];
  const visit = (v) => {
    idx.set(v, index); low.set(v, index); index++; stack.push(v); onStack.add(v);
    for (const w of (edges.get(v) || new Map()).keys()) {
      if (!idx.has(w)) { visit(w); low.set(v, Math.min(low.get(v), low.get(w))); } else if (onStack.has(w)) { low.set(v, Math.min(low.get(v), idx.get(w))); }
    }
    if (low.get(v) === idx.get(v)) {
      const comp = [];
      let w;
      do { w = stack.pop(); onStack.delete(w); comp.push(w); } while (w !== v);
      if (comp.length > 1) { cycles.push(comp.sort().join(' ↔ ')); }
    }
  };
  for (const v of edges.keys()) { if (!idx.has(v)) { visit(v); } }
  return cycles.sort();
}

function layerOf(relFromStatic) {
  const parts = relFromStatic.split('/');
  if (parts.length === 1 || parts[1] === 'views') { return 'ui'; }
  if (parts[1] === 'modules' && parts.length >= 5) { return parts[3]; }
  return null;
}

function check({ update = false } = {}) {
  const errors = [];
  const baseline = JSON.parse(fs.readFileSync(BASELINE, 'utf-8'));
  const code = fs.readFileSync(APP_JS, 'utf-8');
  const { declarations, endpoints } = scanAppJs(code);

  const baseDecls = new Set(baseline.declarations);
  const baseEndpoints = new Set(baseline.endpoints);

  const newDecls = [...declarations].filter((n) => !baseDecls.has(n)).sort();
  if (newDecls.length) {
    errors.push(`app.js ganhou declarações de nível superior: ${newDecls.join(', ')}. `
      + 'Implemente em static/js/modules/<domínio>/{ui,business,integrations}/ (docs/UBX_MIGRATION_PLAN.md).');
  }
  const newEndpoints = [...endpoints].filter((e) => !baseEndpoints.has(e)).sort();
  if (newEndpoints.length) {
    errors.push(`app.js ganhou endpoints HTTP: ${newEndpoints.join(', ')}. `
      + 'Integrações novas vão para modules/<domínio>/integrations/.');
  }

  const goneDecls = baseline.declarations.filter((n) => !declarations.has(n));
  const goneEndpoints = baseline.endpoints.filter((e) => !endpoints.has(e));
  if (update) {
    baseline.declarations = baseline.declarations.filter((n) => declarations.has(n));
    baseline.endpoints = baseline.endpoints.filter((e) => endpoints.has(e));
    fs.writeFileSync(BASELINE, JSON.stringify(baseline, null, 2) + '\n');
  } else if (goneDecls.length || goneEndpoints.length) {
    errors.push(`baseline desatualizado (catraca): saíram do app.js ${[...goneDecls, ...goneEndpoints].join(', ')}. `
      + 'Rode: node static/js/test/app-js-boundary.js --update');
  }

  const scriptsHtml = fs.readFileSync(SCRIPTS_HTML, 'utf-8');
  const scriptOrder = [...scriptsHtml.matchAll(/<script[^>]+src="([^"?]+)/g)].map((m) => m[1]);
  const appIndex = scriptOrder.indexOf('/app.js');
  if (appIndex < 0) {
    errors.push('/app.js não encontrado em static/views/_scripts.html — a ordem de carga não pode ser verificada.');
  }
  for (const [modulePath, names] of Object.entries(baseline.extracted)) {
    const full = path.join(ROOT, 'static', modulePath);
    if (!fs.existsSync(full)) {
      errors.push(`módulo extraído ausente: static/${modulePath}`);
      continue;
    }
    const moduleCode = fs.readFileSync(full, 'utf-8');
    for (const name of names) {
      if (declarations.has(name)) {
        errors.push(`${name} foi extraído para static/${modulePath} e voltou a ser declarado no app.js.`);
      }
      if (!new RegExp(`function\\s+${escapeRegExp(name)}\\s*\\(`).test(moduleCode)) {
        errors.push(`${name} não é definido em static/${modulePath}.`);
      }
    }
    const idx = scriptOrder.indexOf(`/${modulePath}`);
    if (idx < 0) {
      errors.push(`static/${modulePath} não é carregado em static/views/_scripts.html.`);
    } else if (idx > appIndex) {
      errors.push(`static/${modulePath} precisa carregar antes de /app.js.`);
    }
  }

  for (const file of walkFiles(MODULES_DIR)) {
    const rel = path.relative(MODULES_DIR, file).split(path.sep);
    // modules/<domínio>/<camada>/... — subpastas herdam a regra da camada.
    const layer = rel.length >= 3 ? rel[1] : null;
    const rules = LAYER_RULES[layer];
    if (!rules) { continue; }
    const body = stripComments(fs.readFileSync(file, 'utf-8'));
    for (const [re, what] of rules) {
      if (re.test(body)) {
        errors.push(`camada ${layer} não pode depender de ${what}: static/js/modules/${rel.join('/')}`);
      }
    }
  }

  // 6. Catraca de endpoints na camada UI.
  const uiEndpoints = scanUiEndpoints();
  const baseUi = baseline.uiEndpoints || {};
  for (const [file, found] of Object.entries(uiEndpoints)) {
    const allowed = new Set(baseUi[file] || []);
    const added = found.filter((e) => !allowed.has(e));
    if (added.length) {
      errors.push(`static/${file} (camada UI) ganhou endpoints HTTP: ${added.join(', ')}. `
        + 'Chamadas novas vão para static/js/modules/<domínio>/integrations/.');
    }
  }
  const goneUi = Object.entries(baseUi).flatMap(([file, list]) => list
    .filter((e) => !(uiEndpoints[file] || []).includes(e)).map((e) => `${file}:${e}`));

  // 9. Catraca de fetch cru na camada UI.
  const uiRawFetch = scanUiRawFetch();
  const baseFetch = baseline.uiRawFetch || {};
  for (const [file, count] of Object.entries(uiRawFetch)) {
    const allowed = baseFetch[file] || 0;
    if (count > allowed) {
      errors.push(`static/${file} (camada UI) ganhou fetch cru (${allowed} → ${count}). `
        + 'Use o cliente único: globalThis.api / apiFetch (static/js/modules/api-client.js).');
    }
  }
  const lowerFetch = Object.entries(baseFetch).filter(([file, count]) => (uiRawFetch[file] || 0) < count)
    .map(([file, count]) => `${file}:fetch ${count}→${uiRawFetch[file] || 0}`);

  // 7. Dependências entre scripts.
  const edges = namespaceGraph();
  const cycles = findCycles(edges);
  const knownCycles = new Set(baseline.knownCycles || []);
  for (const cycle of cycles) {
    if (!knownCycles.has(cycle)) { errors.push(`dependência circular entre scripts: ${cycle}`); }
  }
  const goneCycles = [...knownCycles].filter((c) => !cycles.includes(c));
  for (const [file, deps] of edges) {
    const layer = layerOf(file);
    if (layer !== 'business' && layer !== 'integrations') { continue; }
    for (const [owner, ns] of deps) {
      if (layerOf(owner) === 'ui') {
        errors.push(`static/${file} (camada ${layer}) não pode depender da camada UI: lê ${ns} de static/${owner}.`);
      }
    }
  }

  // 8. Tamanho máximo dos módulos.
  for (const file of walkFiles(MODULES_DIR)) {
    const lines = fs.readFileSync(file, 'utf-8').trimEnd().split('\n').length;
    if (lines > MAX_MODULE_LINES) {
      errors.push(`static/js/modules/${path.relative(MODULES_DIR, file).split(path.sep).join('/')} tem ${lines} linhas `
        + `(máximo ${MAX_MODULE_LINES}): divida por responsabilidade em vez de criar um novo monólito.`);
    }
  }

  if (update) {
    baseline.uiEndpoints = Object.fromEntries(Object.entries(baseUi)
      .map(([file, list]) => [file, list.filter((e) => (uiEndpoints[file] || []).includes(e))])
      .filter(([, list]) => list.length));
    baseline.knownCycles = [...knownCycles].filter((c) => cycles.includes(c));
    baseline.uiRawFetch = Object.fromEntries(Object.entries(baseFetch)
      .map(([file, count]) => [file, Math.min(count, uiRawFetch[file] || 0)]).filter(([, count]) => count > 0));
    fs.writeFileSync(BASELINE, JSON.stringify(baseline, null, 2) + '\n');
  } else if (goneUi.length || goneCycles.length || lowerFetch.length) {
    errors.push(`baseline desatualizado (catraca): saíram ${[...goneUi, ...goneCycles, ...lowerFetch].join(', ')}. `
      + 'Rode: node static/js/test/app-js-boundary.js --update');
  }

  return {
    errors,
    stats: {
      declarations: declarations.size,
      endpoints: endpoints.size,
      uiEndpoints: Object.values(uiEndpoints).reduce((n, list) => n + list.length, 0),
      cycles: cycles.length,
      uiRawFetch: Object.values(uiRawFetch).reduce((n, c) => n + c, 0)
    }
  };
}

if (require.main === module) {
  const update = process.argv.includes('--update');
  const { errors, stats } = check({ update });
  if (errors.length) {
    console.error(`Guarda UBX do app.js — ${errors.length} violação(ões):`);
    errors.forEach((e) => console.error(`  ✗ ${e}`));
    process.exit(1);
  }
  console.log(`Guarda UBX do app.js OK — ${stats.declarations} declarações, ${stats.endpoints} endpoints (sem crescimento); `
    + `camada UI: ${stats.uiEndpoints} endpoints, ${stats.uiRawFetch} fetch cru; ciclos entre scripts: ${stats.cycles}.`);
}

module.exports = { check, scanAppJs, scanUiEndpoints, scanUiRawFetch, namespaceGraph, findCycles };
