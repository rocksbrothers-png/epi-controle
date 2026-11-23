'use strict';
// Mutações em memória na UBX Fornecedores F1: módulos, fixture e app.js servidos ficam intactos.
// rules/loader: sabotagens no corpo dos módulos, detectadas pela comparação com a cópia literal.
// app: sabotagens na injeção de dependências de importSuppliersCSV, detectadas pelos contratos.
// Mutante equivalente conhecido (não listado): trocar `|| ''` final do nome por nada — `k()`
// já devolve string e '' é falsy, então `name` só muda de '' para '' e a linha é descartada igual.
const assert = require('assert');
const runtime = require('./supplier-import-runtime');

const ERR = "tr('ui.app.nao_foi_possivel_carregar_suporte_a_xls_verifique_sua_conexao_a34fe1', 'Não foi possível carregar suporte a XLS. Verifique sua conexão.', {})";
const mutations = [
  // Parser (business)
  ['rules', 'cabeçalho nome removido', "k('nome') || k('name')", "k('name')"],
  ['rules', 'ordem de cabeçalhos do nome', "k('nome') || k('name') || k('Name')", "k('Name') || k('name') || k('nome')"],
  ['rules', 'rótulo traduzido ignorado', 'k((resolveNameLabel()))', "k('Nome')"],
  ['rules', 'rótulo avaliado antecipadamente', "const name = k('nome') || k('name') || k('Name') || k((resolveNameLabel())) || '';",
    "const label = resolveNameLabel(); const name = k('nome') || k('name') || k('Name') || k((label)) || '';"],
  ['rules', 'sem trim', "|| '').trim();", "|| '');"],
  ['rules', 'sem variante minúscula', 'r[key] || r[key?.toLowerCase?.()] || ', 'r[key] || '],
  ['rules', 'sem variante maiúscula', ' || r[key?.toUpperCase?.()]', ''],
  ['rules', 'sem coerção String', "String(r[key] || r[key?.toLowerCase?.()] || r[key?.toUpperCase?.()] || '')", "(r[key] || r[key?.toLowerCase?.()] || r[key?.toUpperCase?.()] || '')"],
  ['rules', 'linhas vazias mantidas', '.filter(Boolean);', ';'],
  ['rules', 'linha sem nome vira objeto', 'if (!name) return null;', ''],
  ['rules', 'cnpj minúsculo removido', "k('cnpj') || k('CNPJ')", "k('CNPJ')"],
  ['rules', 'cnpj padrão', "k('CNPJ') || '',", "k('CNPJ') || null,"],
  ['rules', 'prioridade do contato', "k('contato') || k('email')", "k('email') || k('contato')"],
  ['rules', 'contact_email removido', " || k('contact_email')", ''],
  ['rules', 'campo email renomeado', 'email: k(', 'contact: k('],
  // Carregador (integrations)
  ['loader', 'URL do SheetJS', "'https://cdn.jsdelivr.net/npm/xlsx/dist/xlsx.full.min.js'", "'https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js'"],
  ['loader', 'sem atalho XLSX já carregado', 'if (win.XLSX) return win.XLSX;', ''],
  ['loader', 'atalho estrito', 'if (win.XLSX) return win.XLSX;', 'if (win.XLSX !== undefined) return win.XLSX;'],
  ['loader', 'onload resolve o elemento', 's.onload = () => resolve(win.XLSX);', 's.onload = () => resolve(s);'],
  ['loader', 'onerror resolve', 's.onerror = () => reject(new Error((errorMessage())));', 's.onerror = () => resolve(win.XLSX);'],
  ['loader', 'mensagem antecipada', 'return new Promise((resolve, reject) => {', 'const msg = errorMessage(); return new Promise((resolve, reject) => {'],
  ['loader', 'mensagem fixa', 'new Error((errorMessage()))', "new Error('Não foi possível carregar suporte a XLS. Verifique sua conexão.')"],
  ['loader', 'script não anexado', 'doc.head.appendChild(s);', ''],
  ['loader', 'carga única por variável', 'async function _loadSheetJS({ win, doc, errorMessage }) {', 'let cached; async function _loadSheetJS({ win, doc, errorMessage }) { if (cached) return cached; cached = 1;'],
  // Injeção no app.js
  ['app', 'janela errada', 'win: window,', 'win: globalThis.parent,'],
  ['app', 'documento omitido', '        doc: document,\n', ''],
  ['app', 'mensagem pré-calculada', `errorMessage: () => ${ERR},`, `errorMessage: ${ERR},`],
  ['app', 'rótulo pré-calculado (XLS)', "_parseSuppliersRows(data, () => tr('signature.name', 'Nome', {}));", "_parseSuppliersRows(data, tr('signature.name', 'Nome', {}));"],
  ['app', 'rótulo omitido (CSV)', "_parseSuppliersRows(objRows, () => tr('signature.name', 'Nome', {}));", '_parseSuppliersRows(objRows);'],
  ['app', 'chave do rótulo trocada', "_parseSuppliersRows(data, () => tr('signature.name',", "_parseSuppliersRows(data, () => tr('signature.title',"],
  // (montado por partes para o varredor de contrato de API não tomar o teste por chamada real)
  ['app', 'rota do upload trocada', ['api(', "'/api/authorized-suppliers/upload'"].join(''), ['api(', "'/api/authorized-suppliers/import'"].join('')],
  ['app', 'método do upload trocado', "upload', { method: 'POST'", "upload', { method: 'PUT'"]
];

(async () => {
  let detected = 0;
  for (const [file, label, from, to] of mutations) {
    let divergence = false;
    try {
      if (file === 'app') { runtime.contracts([from, to]); } else { await runtime.compareAll([file, from, to]); }
    } catch (error) {
      if (error.message.startsWith('mutação sem alvo:')) { throw error; }
      assert(error instanceof assert.AssertionError, label + ': erro do harness: ' + error.message);
      divergence = true;
    }
    console.log(`${divergence ? 'detectada ' : 'SOBREVIVEU'}  ${label}`);
    if (divergence) { detected++; }
  }
  console.log('UBX Fornecedores F1: ' + detected + '/' + mutations.length + ' mutações detectadas');
  process.exitCode = detected === mutations.length ? 0 : 1;
})().catch((error) => { console.error(error); process.exitCode = 1; });
