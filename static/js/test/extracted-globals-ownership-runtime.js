'use strict';
// UBX-V3 — dono único dos nomes globais extraídos do app.js.
//
// Depois da extração, as chamadas do próprio app.js a esses nomes (e a `api`,
// `apiOptional`, `apiWithBootstrapRetry`) resolvem pelo global na HORA da
// chamada. Se outro script reatribuir um deles (`globalThis.api = …`), passa a
// interceptar o app.js inteiro. Este teste fixa que só o módulo dono publica
// cada nome (auditoria independente da UBX-V3, P2-4).
const fs = require('fs'), path = require('path');
const STATIC = path.resolve(__dirname, '..', '..');

function walk(dir, out = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) { if (!['test', 'vendor', 'i18n'].includes(entry.name)) { walk(full, out); } } else if (entry.name.endsWith('.js')) { out.push(full); }
  }
  return out;
}

module.exports = function ({ test, assert }) {
  test('UBX-V3: só o módulo dono publica cada nome global extraído do app.js', () => {
    const baseline = JSON.parse(fs.readFileSync(path.join(STATIC, 'js', 'test', 'app-js-baseline.json'), 'utf8'));
    const owners = {};
    for (const [modulePath, names] of Object.entries(baseline.extracted)) {
      for (const name of names) { owners[name] = path.join(STATIC, modulePath); }
    }
    for (const name of ['api', 'apiOptional', 'apiWithBootstrapRetry']) { owners[name] = path.join(STATIC, 'js', 'modules', 'api-client.js'); }
    // Duplicação preexistente (docs/UBX_APPJS_AUDITORIA.md §11.6, achado 1): utils/dom.js
    // também publica estes três; o módulo dono carrega DEPOIS e prevalece, como o app.js antes.
    const known = { 'js/utils/dom.js': ['isViewActive', 'resolveFormFieldAutocomplete', 'getElementIdAttribute'] };
    const scripts = fs.readFileSync(path.join(STATIC, 'views', '_scripts.html'), 'utf8');
    const order = [...scripts.matchAll(/<script[^>]+src="([^"?]+)/g)].map((m) => m[1]);
    assert(order.indexOf('/js/utils/dom.js') >= 0
      && order.indexOf('/js/utils/dom.js') < order.indexOf('/js/modules/shared/ui/form-field-identity.js'),
    'utils/dom.js precisa carregar antes de shared/ui/form-field-identity.js');
    const files = walk(STATIC).map((f) => [f, fs.readFileSync(f, 'utf8')]);
    const problems = [];
    for (const [name, owner] of Object.entries(owners)) {
      const re = new RegExp(`(?:globalThis|window|self)\\s*(?:\\.\\s*${name}|\\[\\s*['"\`]${name}['"\`]\\s*\\])\\s*=(?!=)`);
      for (const [file, code] of files) {
        if (file !== owner && !(known[path.relative(STATIC, file)] || []).includes(name) && re.test(code)) { problems.push(`${name} reatribuído em ${path.relative(STATIC, file)}`); }
      }
    }
    assert(problems.length === 0, problems.join('; '));
  });
};
