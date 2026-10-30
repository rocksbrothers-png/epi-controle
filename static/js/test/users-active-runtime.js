'use strict';
// FIX-USERS-ACTIVE-V1 — editar usuário não reativa conta inativa.
//
// Antes: prepareUserFormValues fazia `values.active = Number(values.active || 1)`.
// O formulário de usuário não tem campo de status, então toda edição enviava
// active=1 e reativava a conta. Além disso, populateLinkedEmployeeOptions refazia
// as opções do vínculo e apagava a seleção: ao editar, o colaborador vinculado
// sumia do formulário (e salvar um Gestor/Administrador Local falhava).
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const APP = path.resolve(__dirname, '..', '..', 'app.js');
const VIEWS = path.resolve(__dirname, '..', '..', 'views');

function extractFunction(source, name) {
  const start = source.indexOf(`function ${name}(`);
  if (start < 0) {throw new Error(`função ${name} não encontrada`);}
  let depth = 0;
  for (let i = source.indexOf('{', start); i < source.length; i += 1) {
    if (source[i] === '{') {depth += 1;}
    if (source[i] === '}') {depth -= 1; if (depth === 0) {return source.slice(start, i + 1);}}
  }
  throw new Error(`função ${name} sem fim`);
}

function selectField(initialValue = '') {
  // <select> mínimo: atribuir innerHTML recria as opções e a seleção volta para a primeira.
  const field = {
    options: [],
    _value: initialValue,
    get value() { return this._value; },
    set value(next) { this._value = this.options.some((o) => o.value === String(next)) ? String(next) : (this.options[0]?.value ?? ''); },
    set innerHTML(html) {
      this.options = [...html.matchAll(/<option value="([^"]*)"/g)].map((m) => ({ value: m[1] }));
      this._value = this.options[0]?.value ?? '';
    }
  };
  field.options = [{ value: '' }, { value: String(initialValue) }];
  return field;
}

function runPopulate({ role = 'general_admin', selected = '4', employees }) {
  const field = selectField(selected);
  const context = {
    document: { getElementById: (id) => (id === 'user-linked-employee' ? field : null) },
    state: { user: { role } },
    tr: (_key, fallback) => fallback,
    filteredLinkedEmployees: () => employees,
    renderLinkedEmployeeSearchResults: () => {}
  };
  vm.createContext(context);
  vm.runInContext(`${extractFunction(fs.readFileSync(APP, 'utf8'), 'populateLinkedEmployeeOptions')}; populateLinkedEmployeeOptions();`, context);
  return field.value;
}

module.exports = function ({ test, assert, eq }) {
  const business = () => globalThis.__EPI_USERS_BUSINESS__;
  const actor = { id: 1, role: 'master_admin' };
  const roleLabels = { user: 'Gestor de EPI', buyer: 'Comprador' };
  const prepare = (values) => business().prepareUserFormValues({ company_id: '9', role: 'buyer', ...values }, { actor, roleLabels });

  test('FIX-USERS-ACTIVE-V1: formulário sem status não envia active (servidor mantém o status atual)', () => {
    assert(!('active' in prepare({})), 'sem campo');
    assert(!('active' in prepare({ active: '' })), 'vazio');
    assert(!('active' in prepare({ active: '  ' })), 'só espaços');
  });

  test('FIX-USERS-ACTIVE-V1: status explícito continua sendo enviado como número', () => {
    eq(prepare({ active: '0' }).active, 0, 'inativo');
    eq(prepare({ active: '1' }).active, 1, 'ativo');
  });

  test('FIX-USERS-ACTIVE-V1: botão Ativar/Desativar segue mandando o status explícito', () => {
    const target = { username: 'g', full_name: 'G', role: 'user', company_id: 9, active: 0 };
    eq(business().userAccessUpdatePayload(target, { active: 1 }, 1).active, 1, 'reativar');
    eq(business().userAccessUpdatePayload({ ...target, active: 1 }, { active: 0 }, 1).active, 0, 'desativar');
    eq(business().userAccessUpdatePayload(target, { role: 'admin' }, 1).active, 0, 'promover não reativa');
  });

  test('FIX-USERS-ACTIVE-V1: o formulário de usuário não tem campo de status', () => {
    const html = fs.readFileSync(path.join(VIEWS, 'usuarios.html'), 'utf8');
    const form = /<form id="user-form"[\s\S]*?<\/form>/.exec(html);
    assert(form, 'user-form em usuarios.html');
    assert(!/name="active"/.test(form[0]), 'campo active no formulário de usuário');
  });

  test('FIX-USERS-ACTIVE-V1: refazer as opções de vínculo mantém o colaborador selecionado', () => {
    const employees = [{ id: 3, employee_id_code: 'M3', name: 'Ana' }, { id: 4, employee_id_code: 'M4', name: 'Bia' }];
    eq(runPopulate({ selected: '4', employees }), '4', 'Adm. Geral editando');
    eq(runPopulate({ role: 'registry_admin', selected: '4', employees }), '4', 'Registro editando');
    eq(runPopulate({ selected: '', employees }), '', 'sem vínculo continua sem vínculo');
    eq(runPopulate({ selected: '99', employees }), '', 'vínculo fora das opções (outra empresa) não é mantido');
    eq(runPopulate({ role: 'registry_admin', selected: '99', employees }), '3', 'Registro sem vínculo válido: primeira opção, como antes');
  });
};
