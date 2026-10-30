'use strict';
// SECURITY-LOGO-XSS-V1 — os pontos do frontend que inserem o logotipo via
// innerHTML (companyLogoSrc/companyLogoMarkup no app.js e applyBranding da tela
// de login pública em tenant-init.js) não aceitam valores que fechem o
// atributo src, e continuam exibindo logotipos legítimos.
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

function loadAppLogo() {
  const app = fs.readFileSync(path.join(STATIC, 'app.js'), 'utf8');
  const ctx = { DEFAULT_COMPANY_LOGO: 'data:image/svg+xml;utf8,%3Csvg%3E%3C%2Fsvg%3E', String, RegExp };
  vm.createContext(ctx);
  vm.runInContext(`${extractFunction(app, 'companyLogoSrc')}\n${extractFunction(app, 'companyLogoMarkup')}\n`
    + 'this.companyLogoSrc = companyLogoSrc; this.companyLogoMarkup = companyLogoMarkup;', ctx);
  return ctx;
}

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
  test('SECURITY-LOGO-XSS-V1: companyLogoSrc só aceita data URL base64 de PNG/JPEG/SVG', () => {
    const ctx = loadAppLogo();
    for (const value of LEGIT) { eq(ctx.companyLogoSrc(value), value, `legítimo: ${value.slice(0, 30)}`); }
    for (const value of [...MALICIOUS, '', null, undefined]) {
      eq(ctx.companyLogoSrc(value), ctx.DEFAULT_COMPANY_LOGO, `malicioso vira o padrão: ${String(value).slice(0, 40)}`);
    }
  });

  test('SECURITY-LOGO-XSS-V1: companyLogoMarkup não injeta atributos (logotipo nem nome da empresa)', () => {
    const ctx = loadAppLogo();
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
