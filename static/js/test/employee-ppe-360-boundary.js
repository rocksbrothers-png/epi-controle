'use strict';

/**
 * Guarda de domínio da Ficha 360° de EPI (fatia F0).
 *
 * Complementa static/js/test/app-js-boundary.js (que já impede o app.js de
 * crescer, ciclos entre scripts, business com DOM/HTTP/estado e módulos acima
 * de 500 linhas) com regras ESPECÍFICAS deste domínio, verificadas pelo
 * conteúdo dos arquivos e pela camada a que pertencem:
 *
 *  1. app.js: nenhuma referência à Ficha (namespace, módulo ou rota). A Ficha
 *     abre a partir do módulo Colaboradores, nunca pelo monólito.
 *  2. Camada UI do domínio: nenhuma chamada HTTP nem caminho /api — integração
 *     só em modules/employee-ppe-360/integrations/.
 *  3. Nenhum cálculo financeiro no frontend do domínio: aritmética sobre campos
 *     monetários, parseFloat e toFixed são proibidos. Valores chegam prontos e
 *     rotulados do backend.
 *  4. Estado global controlado: o domínio só publica os próprios namespaces
 *     (__EPI_EMPLOYEE_PPE_360_*__) e não usa storage nem cookie.
 *  5. Ciclo de vida: todo addEventListener do domínio passa AbortSignal, para
 *     sair junto na desmontagem (sem listener duplicado ou órfão).
 *  6. Acoplamento: o domínio não referencia Compras, e Compras não referencia o
 *     domínio. A leitura de custos (F5) passará pelo backend.
 *
 * Uso: node static/js/test/employee-ppe-360-boundary.js
 * Sem dependências além da stdlib do Node.
 */

const fs = require('fs');
const path = require('path');

const DOMAIN = 'employee-ppe-360';
const NAMESPACE_PREFIX_RE = /^__EPI_(?:MODULE_)?EMPLOYEE_PPE_360_[A-Z0-9_]+__$/;
const APP_JS_FORBIDDEN_RE = /EMPLOYEE_PPE_360|employee-ppe-360|ppe-360|employee360/i;
const HTTP_RES = [
  [/(?<![\w$.])(?:(?:globalThis|window|self)\s*\??\.\s*)?(?:fetch|api|apiFetch|apiOptional|apiWithBootstrapRetry|apiFetchWithRetry|apiFetchOptional)\s*(?:\?\.\s*)?\(/, 'chamada HTTP'],
  [/\b(?:XMLHttpRequest|EventSource|WebSocket)\b|\.sendBeacon\s*\(/, 'chamada HTTP'],
  [/__EPI_API_CLIENT__/, 'cliente HTTP'],
  [/['"`]\/api(?:\/|['"`])/, 'caminho /api']
];
// Identificador monetário inteiro (inclui os nomes curtos: price, cost, amount).
const MONEY_ID = '[\\w$]*(?:price|cost|amount|valor|custo|preco|preço|totalValue|total_value)[\\w$]*';
const MONEY_ARITH_RES = [
  new RegExp(`(?<![\\w$])${MONEY_ID}\\s*(?:\\]|\\))?\\s*(?:[*/%]|\\+(?!\\+)|-(?!-))=?\\s*[\\w$(.]`, 'i'),
  new RegExp(`[\\w$)\\]]\\s*(?:[*/%]|\\+(?!\\+)|-(?!-))=?\\s*(?:[\\w$]+\\.)*(?<![\\w$])${MONEY_ID}`, 'i'),
  /\bparseFloat\s*\(|\.toFixed\s*\(/
];
const STORAGE_RE = /\b(?:localStorage|sessionStorage|indexedDB)\b|document\s*\.\s*cookie/;
const GLOBAL_WRITE_RE = /\b(?:globalThis|window|self)\s*(?:\.\s*([A-Za-z_$][\w$]*)|\[\s*([^\]]+)\s*\])\s*=(?!=)/g;
const PURCHASES_REF_RE = /__EPI_PURCHASE|\/api\/(?:purchase|quotes|company-purchase-config|purchase-limits)|modules\/purchases\//i;
const PPE360_REF_RE = /EMPLOYEE_PPE_360|employee-ppe-360/;

function stripComments(code) {
  return code.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:\\])\/\/.*$/gm, '$1');
}

function walk(dir) {
  if (!fs.existsSync(dir)) { return []; }
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) { out.push(...walk(full)); } else if (entry.name.endsWith('.js')) { out.push(full); }
  }
  return out.sort();
}

// Texto de cada chamada addEventListener(...) com parênteses balanceados.
function listenerCalls(code) {
  const calls = [];
  const re = /\baddEventListener\s*\(/g;
  let m;
  while ((m = re.exec(code)) !== null) {
    let depth = 1;
    let i = re.lastIndex;
    while (i < code.length && depth > 0) {
      if (code[i] === '(') { depth += 1; } else if (code[i] === ')') { depth -= 1; }
      i += 1;
    }
    calls.push(code.slice(m.index, i));
  }
  return calls;
}

function check(root = path.resolve(__dirname, '..', '..', '..')) {
  const errors = [];
  const staticDir = path.join(root, 'static');
  const domainDir = path.join(staticDir, 'js', 'modules', DOMAIN);
  const rel = (file) => path.relative(root, file).split(path.sep).join('/');

  // 1. app.js
  const appJs = path.join(staticDir, 'app.js');
  if (fs.existsSync(appJs) && APP_JS_FORBIDDEN_RE.test(stripComments(fs.readFileSync(appJs, 'utf-8')))) {
    errors.push('static/app.js referencia a Ficha 360°: a abertura e a lógica pertencem a static/js/modules/employee-ppe-360/ (aberta a partir de Colaboradores).');
  }

  const files = walk(domainDir);
  if (!files.length) {
    errors.push('static/js/modules/employee-ppe-360/ não encontrado: a fundação F0 é obrigatória.');
  }
  for (const file of files) {
    const parts = path.relative(domainDir, file).split(path.sep);
    const layer = parts.length >= 2 ? parts[0] : null;
    const body = stripComments(fs.readFileSync(file, 'utf-8'));
    const name = rel(file);
    if (!['business', 'integrations', 'ui'].includes(layer)) {
      errors.push(`${name}: todo arquivo do domínio pertence a business/, integrations/ ou ui/.`);
    }
    // 2. HTTP fora de integrations/.
    if (layer !== 'integrations') {
      for (const [re, what] of HTTP_RES) {
        if (re.test(body)) { errors.push(`${name} (camada ${layer}) não pode conter ${what}: use modules/${DOMAIN}/integrations/.`); }
      }
    }
    // 3. Cálculo financeiro.
    for (const re of MONEY_ARITH_RES) {
      const hit = body.match(re);
      if (hit) { errors.push(`${name}: cálculo financeiro no frontend é proibido ("${hit[0].trim()}"). O backend entrega valores prontos.`); }
    }
    // 4. Estado global e storage.
    if (STORAGE_RE.test(body)) { errors.push(`${name}: o domínio não usa storage nem cookie (estado só em memória).`); }
    for (const m of body.matchAll(GLOBAL_WRITE_RE)) {
      const target = (m[1] || m[2] || '').replace(/['"`\s]/g, '');
      if (!NAMESPACE_PREFIX_RE.test(target)) {
        errors.push(`${name}: escrita em global não controlada (${target || '?'}); publique só __EPI_EMPLOYEE_PPE_360_*__.`);
      }
    }
    // 5. Listeners com AbortSignal.
    for (const call of listenerCalls(body)) {
      if (!/\bsignal\b/.test(call)) {
        errors.push(`${name}: addEventListener sem AbortSignal — o listener não sai na desmontagem: ${call.slice(0, 80)}…`);
      }
    }
    // 6a. Domínio → Compras.
    if (PURCHASES_REF_RE.test(body)) { errors.push(`${name}: a Ficha não referencia Compras; custos chegam pelo backend da Ficha.`); }
  }

  // 6b. Compras → domínio.
  const purchaseFiles = [
    ...walk(path.join(staticDir, 'js', 'modules', 'purchases')),
    ...['purchases.js', 'procurement.js'].map((f) => path.join(staticDir, 'js', 'views', f)).filter((f) => fs.existsSync(f))
  ];
  for (const file of purchaseFiles) {
    if (PPE360_REF_RE.test(stripComments(fs.readFileSync(file, 'utf-8')))) {
      errors.push(`${rel(file)}: Compras não depende da Ficha 360°.`);
    }
  }
  return { errors, files: files.map(rel) };
}

if (require.main === module) {
  const { errors, files } = check();
  if (errors.length) {
    console.error(`Guarda de domínio da Ficha 360° — ${errors.length} violação(ões):`);
    errors.forEach((e) => console.error(`  ✗ ${e}`));
    process.exit(1);
  }
  console.log(`Guarda de domínio da Ficha 360° OK — ${files.length} arquivo(s) verificados.`);
}

module.exports = { check, listenerCalls };
