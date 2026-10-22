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
 *     DOM, HTTP, storage nem o estado global do app; integrations/ não toca
 *     DOM.
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

// Toda declaração de nível superior do app.js começa na coluna 0 (o arquivo
// inteiro vive dentro de um único bloco `if` sem indentação). A contagem por
// este padrão bate com a da AST (scripts/audit_app_js.js).
const DECL_RE = /^(?:async\s+)?(?:function\*?|const|let|var)\s+([A-Za-z_$][\w$]*)/gm;
const ENDPOINT_RE = /['`](\/api\/[^'`?$\s]*)/g;

const LAYER_RULES = {
  business: [
    [/\bdocument\s*\./, 'DOM (document.*)'],
    [/\.innerHTML\b/, 'DOM (innerHTML)'],
    [/\b(?:fetch|api|apiFetch|apiOptional|apiWithBootstrapRetry)\s*\(/, 'HTTP'],
    [/\b(?:localStorage|sessionStorage)\b/, 'storage'],
    [/__EPI_APP_STATE__/, 'estado global do app']
  ],
  integrations: [
    [/\bdocument\s*\./, 'DOM (document.*)'],
    [/\.innerHTML\b/, 'DOM (innerHTML)']
  ]
};

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
      if (!new RegExp(`function\\s+${name.replace(/\$/g, '\\$')}\\s*\\(`).test(moduleCode)) {
        errors.push(`${name} não é definido em static/${modulePath}.`);
      }
    }
    const idx = scriptOrder.indexOf(`/${modulePath}`);
    if (idx < 0) {
      errors.push(`static/${modulePath} não é carregado em static/views/_scripts.html.`);
    } else if (appIndex >= 0 && idx > appIndex) {
      errors.push(`static/${modulePath} precisa carregar antes de /app.js.`);
    }
  }

  for (const file of walkFiles(MODULES_DIR)) {
    const rel = path.relative(MODULES_DIR, file).split(path.sep);
    const layer = rel.length >= 3 ? rel[rel.length - 2] : null;
    const rules = LAYER_RULES[layer];
    if (!rules) { continue; }
    const body = stripComments(fs.readFileSync(file, 'utf-8'));
    for (const [re, what] of rules) {
      if (re.test(body)) {
        errors.push(`camada ${layer} não pode depender de ${what}: static/js/modules/${rel.join('/')}`);
      }
    }
  }

  return { errors, stats: { declarations: declarations.size, endpoints: endpoints.size } };
}

if (require.main === module) {
  const update = process.argv.includes('--update');
  const { errors, stats } = check({ update });
  if (errors.length) {
    console.error(`Guarda UBX do app.js — ${errors.length} violação(ões):`);
    errors.forEach((e) => console.error(`  ✗ ${e}`));
    process.exit(1);
  }
  console.log(`Guarda UBX do app.js OK — ${stats.declarations} declarações, ${stats.endpoints} endpoints (sem crescimento).`);
}

module.exports = { check, scanAppJs };
