'use strict';
// FIX-EMPRESAS-ACTIVE-V1 — o campo Situação do formulário de Empresas.
//
// Antes: as opções do <select name="active"> usavam data-i18n-value, e o
// i18n.js trocava o value 1/0 pelo texto traduzido ("Active"/"Inativa"); o
// formulário enviava active='' (o backend recusa) e editar não selecionava o
// estado. Além disso startEditCompany usava `company.active || 1`, abrindo uma
// empresa inativa (0) como ativa.
const fs = require('fs');
const path = require('path');
const companies = require('./companies-view-runtime');

const VIEWS = path.resolve(__dirname, '..', '..', 'views');

module.exports = function ({ testAsync, test, assert, eq }) {
  test('FIX-EMPRESAS-ACTIVE-V1: opções do campo Situação mantêm value 1/0 e traduzem só o texto', () => {
    const html = fs.readFileSync(path.join(VIEWS, 'empresas.html'), 'utf8');
    const select = /<select name="active">([\s\S]*?)<\/select>/.exec(html);
    assert(select, 'select name="active" em empresas.html');
    const options = [...select[1].matchAll(/<option([^>]*)>([^<]*)<\/option>/g)].map((m) => m[1].trim());
    eq(JSON.stringify(options), JSON.stringify(['value="1" data-i18n="company.active"', 'value="0" data-i18n="company.inactive"']), 'opções');
  });

  test('FIX-EMPRESAS-ACTIVE-V1: nenhuma <option> das views traduz o value (data-i18n-value troca o valor enviado)', () => {
    for (const file of fs.readdirSync(VIEWS).filter((name) => name.endsWith('.html'))) {
      const html = fs.readFileSync(path.join(VIEWS, file), 'utf8');
      assert(!/<option\b[^>]*data-i18n-value/.test(html), `${file}: <option> com data-i18n-value`);
    }
  });

  test('FIX-EMPRESAS-ACTIVE-V1: formulários de empresa não carregam `active` com `|| 1` (0 viraria 1)', () => {
    const sources = {
      'app.js (fillCommercialForm)': fs.readFileSync(path.resolve(VIEWS, '..', 'app.js'), 'utf8'),
      'companies-view.js': fs.readFileSync(path.resolve(__dirname, '..', 'modules', 'companies', 'ui', 'companies-view.js'), 'utf8')
    };
    for (const [name, source] of Object.entries(sources)) {
      assert(!/(?:selected|company)\.active\s*\|\|\s*1/.test(source), `${name}: active || 1`);
    }
  });

  testAsync('FIX-EMPRESAS-ACTIVE-V1: editar carrega o estado real (inativa abre como 0, ativa como 1)', async () => {
    const out = await companies.scenario(companies.loadModules);
    eq(out['editar:inativa'].form.active, '0', 'empresa inativa');
    eq(out['editar:ok'].form.active, '1', 'empresa ativa');
  });
};
