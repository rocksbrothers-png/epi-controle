'use strict';
// Mutações em memória na fatia UBX Fornecedores F1: os arquivos servidos ficam intactos.
// Cada mutante tem de ser apanhado pela caracterização (antes × atual nos 5 idiomas)
// ou pelo isolamento dos módulos.
//
// Mutante equivalente conhecido (não listado): tirar `|| k('CNPJ')` de cnpj. O k('cnpj')
// já consulta r['CNPJ'] pela variante em maiúsculas, então a saída não muda.
const runtime = require('./suppliers-import-runtime');

const mutations = [
  ['rules', 'rótulo traduzido ignorado', 'k(translatedNameLabel)', "k('Nome')"],
  ['rules', 'trim removido', "|| '').trim();", "|| '');"],
  ['rules', 'variante minúscula removida', 'r[key?.toLowerCase?.()] || ', ''],
  ['rules', 'linhas sem nome mantidas', '.filter(Boolean);', ';'],
  ['rules', 'linha sem nome vira objeto', 'if (!name) {return null;}', 'if (!name) {return { name };}'],
  ['rules', 'ordem do e-mail', "k('contato') || k('email')", "k('email') || k('contato')"],
  ['rules', 'e-mail perde contact_email', " || k('contact_email') || ''", " || ''"],
  ['loader', 'URL do SheetJS', 'xlsx.full.min.js', 'xlsx.mini.min.js'],
  ['loader', 'carga deixa de ser única', 'if (deps.getXLSX()) {return deps.getXLSX();}', ''],
  ['loader', 'onload sem o SheetJS', 'resolve(deps.getXLSX())', 'resolve()'],
  ['loader', 'mensagem de erro fixa', 'new Error(deps.loadErrorMessage())', "new Error('erro')"],
  ['loader', 'script não anexado', 'deps.appendScript(s);', ''],
  ['loader', 'erro de carga vira sucesso', 's.onerror = () => reject(', 's.onerror = () => resolve('],
  // A chave inexistente é derivada da real: o código-fonte não carrega um uso de chave que o
  // scanner de i18n (tests/test_i18n_files_integrity.py) leria como real.
  ['app', 'XLS: chave do rótulo', "_parseSuppliersRows(data, tr('signature.name', 'Nome', {}))",
    "_parseSuppliersRows(data, tr('signature.name', 'Nome', {}))".replace('signature.name', 'signature.nome')],
  ['app', 'CSV: rótulo fixo em pt-BR', "_parseSuppliersRows(objRows, tr('signature.name', 'Nome', {}))", "_parseSuppliersRows(objRows, 'Nome')"],
  ['app', 'mensagem de carga: chave trocada', 'verifique_sua_conexao_a34fe1', 'verifique_sua_conexao_000000'],
  ['app', 'getXLSX ignora a página', 'getXLSX: () => window.XLSX,', 'getXLSX: () => undefined,'],
  ['app', 'elemento errado', "createScript: () => document.createElement('script')", "createScript: () => document.createElement('link')"],
  ['app', 'anexa no body', 'appendScript: (s) => document.head.appendChild(s)', 'appendScript: (s) => document.body.appendChild(s)']
];

// Se o event loop esvaziar no meio (promessa pendurada), o executor não pode sair com 0.
let finished = false;
process.on('exit', () => { if (!finished) { console.error('executor de mutações não terminou'); process.exitCode = 1; } });

(async () => {
  let detected = 0;
  for (const [file, label, from, to] of mutations) {
    let divergence = false;
    try {
      await runtime.compareAll([file, from, to]);
      await runtime.isolation([file, from, to]);
    } catch (error) {
      if (String(error && error.message).startsWith('mutação sem alvo:')) { throw error; }
      divergence = true;
    }
    console.log(`${divergence ? 'detectada ' : 'SOBREVIVEU'}  [${file}] ${label}`);
    if (divergence) { detected += 1; }
  }
  console.log(`UBX Fornecedores F1: ${detected}/${mutations.length} mutações detectadas`);
  finished = true;
  process.exitCode = detected === mutations.length ? 0 : 1;
})().catch((error) => { console.error(error); process.exitCode = 1; });
