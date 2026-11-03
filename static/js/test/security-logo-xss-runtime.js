'use strict';
// SECURITY-LOGO-XSS-V1 — os pontos do frontend que inserem o logotipo via
// innerHTML (companyLogoSrc/companyLogoMarkup, hoje em
// js/modules/shared/ui/company-logo.js, e applyBranding da tela de login
// pública em tenant-init.js) não aceitam valores que fechem o atributo src, e
// continuam exibindo logotipos legítimos.
//
// UBX-V5 (fatia do logotipo): as mesmas verificações rodam sobre o módulo e
// sobre a cópia literal do app.js de antes da extração (fixture), e as duas
// implementações são comparadas entrada a entrada.
//
// As funções são lidas do código-fonte real e avaliadas num contexto isolado.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const STATIC = path.resolve(__dirname, '..', '..');
const PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';
const LEGIT = [PNG, 'data:image/jpeg;base64,/9j/4AAQSkZJRg+abc=', 'data:image/jpg;base64,AAA=', 'data:image/svg+xml;base64,PHN2Zz48L3N2Zz4='];
const MALICIOUS = [
  'data:image/png;base64,AAA" onerror="alert(1)',
  "data:image/png;base64,AAA' onerror='alert(1)",
  'data:image/png;base64,AAA"><script>alert(1)</script>',
  'data:image/png;base64,AAA onerror=alert(1)',
  'data:image/svg+xml;utf8,<svg onload="alert(1)"></svg>',
  'data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==',
  'data:image/gif;base64,R0lGODlhAQABAAAAACw=',
  'data:image/png;base64,',
  'javascript:alert(1)',
  'https://evil.test/x.png'
];

// Extrai `function nome(...) { ... }` do código-fonte contando chaves.
function extractFunction(source, name) {
  const start = source.indexOf(`function ${name}(`);
  if (start < 0) { throw new Error(`função ${name} não encontrada`); }
  let depth = 0;
  for (let i = source.indexOf('{', start); i < source.length; i += 1) {
    if (source[i] === '{') { depth += 1; }
    if (source[i] === '}') { depth -= 1; if (depth === 0) { return source.slice(start, i + 1); } }
  }
  throw new Error(`função ${name} sem fim`);
}

const TEST_DEFAULT_LOGO = 'data:image/svg+xml;utf8,%3Csvg%3E%3C%2Fsvg%3E';

// Original: cópia literal do app.js de antes da extração. Lá DEFAULT_COMPANY_LOGO
// era a `const` de bloco do próprio app.js.
function loadOriginalLogo() {
  const app = fs.readFileSync(path.join(STATIC, 'js', 'test', 'fixtures', 'app-before-ubx-v5-company-logo.js.txt'), 'utf8');
  const ctx = { DEFAULT_COMPANY_LOGO: TEST_DEFAULT_LOGO, String, RegExp };
  vm.createContext(ctx);
  vm.runInContext(`${extractFunction(app, 'companyLogoSrc')}\n${extractFunction(app, 'companyLogoMarkup')}\n`
    + 'this.companyLogoSrc = companyLogoSrc; this.companyLogoMarkup = companyLogoMarkup;', ctx);
  return ctx;
}

// Módulo: o arquivo real carregado como na página; DEFAULT_COMPANY_LOGO vem de
// globalThis. Com `realConstants`, js/core/constants.js roda antes (como na
// página); sem ele, o padrão de teste é semeado para comparar com a fixture.
function loadModuleLogo({ realConstants = false } = {}) {
  const src = fs.readFileSync(path.join(STATIC, 'js', 'modules', 'shared', 'ui', 'company-logo.js'), 'utf8');
  const ctx = realConstants ? { String, RegExp, Object, encodeURIComponent } : { DEFAULT_COMPANY_LOGO: TEST_DEFAULT_LOGO, String, RegExp, Object };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  if (realConstants) { vm.runInContext(fs.readFileSync(path.join(STATIC, 'js', 'core', 'constants.js'), 'utf8'), ctx); }
  vm.runInContext(src, ctx);
  return ctx;
}

const IMPLEMENTATIONS = [['app.js antes da UBX', loadOriginalLogo], ['shared/ui/company-logo.js', loadModuleLogo]];

function loadApplyBranding() {
  const src = fs.readFileSync(path.join(STATIC, 'tenant-init.js'), 'utf8');
  const logoEl = { innerHTML: '' };
  const ctx = {
    String, RegExp,
    document: { documentElement: { style: { setProperty() {} } }, getElementById: (id) => (id === 'login-brand-logo' ? logoEl : null), title: '' }
  };
  vm.createContext(ctx);
  vm.runInContext(`${extractFunction(src, 'escHtml')}\n${extractFunction(src, 'applyBranding')}\nthis.applyBranding = applyBranding;`, ctx);
  return { applyBranding: ctx.applyBranding, logoEl };
}

// Atributos de cada <img> numa string HTML (parser mínimo para atributos entre aspas duplas).
function imgAttributes(html) {
  return [...html.matchAll(/<img\b([^>]*)>/g)].map((m) => [...m[1].matchAll(/\s([^\s=]+)=("[^"]*"|'[^']*'|[^\s>]+)/g)].map((a) => a[1]));
}

module.exports = function ({ test, assert, eq }) {
  for (const [label, load] of IMPLEMENTATIONS) {
    test(`SECURITY-LOGO-XSS-V1: companyLogoSrc só aceita data URL base64 de PNG/JPEG/SVG (${label})`, () => {
      const ctx = load();
      for (const value of LEGIT) { eq(ctx.companyLogoSrc(value), value, `legítimo: ${value.slice(0, 30)}`); }
      for (const value of [...MALICIOUS, '', null, undefined]) {
        eq(ctx.companyLogoSrc(value), ctx.DEFAULT_COMPANY_LOGO, `malicioso vira o padrão: ${String(value).slice(0, 40)}`);
      }
    });

    test(`SECURITY-LOGO-XSS-V1: companyLogoMarkup não injeta atributos (logotipo nem nome da empresa) (${label})`, () => {
      const ctx = load();
      for (const value of MALICIOUS) {
        const html = ctx.companyLogoMarkup({ name: 'ACME', logo_type: value }, 'company-logo');
        eq(JSON.stringify(imgAttributes(html)), JSON.stringify([['class', 'src', 'alt']]), `atributos com ${value.slice(0, 40)}`);
        assert(!/onerror|onload|<script/i.test(html), `sem handler/script: ${html}`);
      }
      const evilName = ctx.companyLogoMarkup({ name: 'ACME" onload="alert(1)', logo_type: PNG }, 'company-logo');
      eq(JSON.stringify(imgAttributes(evilName)), JSON.stringify([['class', 'src', 'alt']]), 'nome com aspas');
      assert(evilName.includes('alt="Logotipo de ACME&quot; onload=&quot;alert(1)"'), evilName);
      // Legítimo: saída idêntica à anterior.
      eq(ctx.companyLogoMarkup({ name: 'ACME', logo_type: PNG }, 'company-logo company-logo-sm'),
        `<img class="company-logo company-logo-sm" src="${PNG}" alt="Logotipo de ACME">`, 'legítimo inalterado');
      eq(ctx.companyLogoMarkup({}, 'company-logo'), `<img class="company-logo" src="${ctx.DEFAULT_COMPANY_LOGO}" alt="Logotipo de Empresa">`, 'padrão');
    });
  }

  test('UBX-V5: company-logo.js é equivalente ao app.js de antes da extração', () => {
    const before = loadOriginalLogo();
    const after = loadModuleLogo();
    const values = [...LEGIT, ...MALICIOUS, '', null, undefined, 0, 1, false, true, {}, [], ' data:image/png;base64,AAA=',
      'DATA:IMAGE/PNG;BASE64,AAA=', 'data:image/png;base64,AAA==', 'data:image/png;base64,AAA===', 'data:image/webp;base64,AAA='];
    const companies = [undefined, null, {}, { name: '' }, { name: 0 }, { name: 'ACME' }, { name: 'Ação & Cia <b>"x"</b> \'y\'' }];
    const classes = [undefined, 'company-logo', 'company-logo company-logo-sm', 'x" onclick="y', '', null, 0];
    let checked = 0;
    for (const value of values) {
      eq(after.companyLogoSrc(value), before.companyLogoSrc(value), `src: ${String(value).slice(0, 40)}`);
      for (const company of companies) {
        const item = company && typeof company === 'object' ? { ...company, logo_type: value } : company;
        for (const cls of classes) {
          const args = cls === undefined ? [item] : [item, cls];
          eq(after.companyLogoMarkup(...args), before.companyLogoMarkup(...args), `markup: ${JSON.stringify(args).slice(0, 80)}`);
          checked += 1;
        }
      }
    }
    assert(checked >= 1000, `cobertura da comparação: ${checked}`);
    // Contrato publicado: nomes globais, namespace congelado e carga idempotente.
    eq(typeof after.__EPI_SHARED_COMPANY_LOGO__, 'object', 'namespace publicado');
    assert(Object.isFrozen(after.__EPI_SHARED_COMPANY_LOGO__), 'namespace congelado');
    eq(after.__EPI_SHARED_COMPANY_LOGO__.companyLogoMarkup, after.companyLogoMarkup, 'mesma função no namespace');
    const first = after.companyLogoSrc;
    vm.runInContext(fs.readFileSync(path.join(STATIC, 'js', 'modules', 'shared', 'ui', 'company-logo.js'), 'utf8'), after);
    eq(after.companyLogoSrc, first, 'segunda carga não republica');
  });

  test('UBX-V5: DEFAULT_COMPANY_LOGO de core/constants.js é idêntico ao que o app.js usava', () => {
    const ctx = {};
    ctx.globalThis = ctx;
    vm.createContext(ctx);
    vm.runInContext(fs.readFileSync(path.join(STATIC, 'js', 'core', 'constants.js'), 'utf8'), ctx);
    const app = fs.readFileSync(path.join(STATIC, 'app.js'), 'utf8');
    const line = app.split('\n').find((l) => l.startsWith('const DEFAULT_COMPANY_LOGO = '));
    assert(line, 'DEFAULT_COMPANY_LOGO no app.js');
    const appValue = vm.runInNewContext(line.replace('const DEFAULT_COMPANY_LOGO = ', '').replace(/;\s*$/, ''), { encodeURIComponent });
    eq(ctx.DEFAULT_COMPANY_LOGO, appValue, 'mesmo logotipo padrão');
    // Página real: constants.js + módulo; valor inválido cai no padrão do app.js.
    const real = loadModuleLogo({ realConstants: true });
    eq(real.companyLogoSrc('javascript:alert(1)'), appValue, 'módulo com constants.js reais usa o padrão do app.js');
    eq(real.companyLogoMarkup({ name: 'ACME' }), `<img class="company-logo" src="${appValue.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;')}" alt="Logotipo de ACME">`, 'markup com o padrão real');
    const scripts = fs.readFileSync(path.join(STATIC, 'views', '_scripts.html'), 'utf8');
    const order = [...scripts.matchAll(/<script[^>]+src="([^"?]+)/g)].map((m) => m[1]);
    const iConst = order.indexOf('/js/core/constants.js');
    const iLogo = order.indexOf('/js/modules/shared/ui/company-logo.js');
    const iApp = order.indexOf('/app.js');
    assert(iConst >= 0 && iLogo > iConst && iApp > iLogo, `ordem de carga: constants ${iConst}, company-logo ${iLogo}, app ${iApp}`);
    for (const consumer of ['/js/modules/companies/ui/companies-view.js', '/js/modules/my-company/ui/my-company-view.js', '/js/views/fichas.js']) {
      assert(order.indexOf(consumer) > iLogo, `${consumer} carrega depois de company-logo.js`);
    }
  });

  test('SECURITY-LOGO-XSS-V1: tela de login pública (tenant-init) ignora logotipo malicioso e mostra o legítimo', () => {
    for (const value of MALICIOUS) {
      const { applyBranding, logoEl } = loadApplyBranding();
      applyBranding({ login_logo_type: value }, 'ACME');
      eq(logoEl.innerHTML, '', `não renderiza: ${value.slice(0, 40)}`);
    }
    for (const value of LEGIT) {
      const { applyBranding, logoEl } = loadApplyBranding();
      applyBranding({ login_logo_type: '', logo_type: value }, 'ACME "QA"');
      eq(logoEl.innerHTML, `<img src="${value}" alt="ACME &quot;QA&quot;" class="tenant-login-logo">`, `legítimo: ${value.slice(0, 30)}`);
    }
  });
};
