'use strict';
// Caracterização diferencial: fixture literal da base × scripts servidos.
// Mocks apenas das bordas: DOM, arquivos/imagem/canvas, API e diálogos.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const ROOT = path.resolve(__dirname, '..', '..');
const read = rel => fs.readFileSync(path.join(ROOT, rel), 'utf8');
const FIXTURE = 'js/test/fixtures/app-before-ubx-platform-brand.js.txt';
const UI = 'js/modules/platform-brand/ui/platform-brand-view.js';
const API = 'js/modules/platform-brand/integrations/platform-brand-api.js';
const NAMES = ['renderPlatformLogoPreview', 'renderPlatformLoginLogoPreview', 'handlePlatformLogoUpload',
  'handlePlatformLoginLogoUpload', 'renderPlatformBrand', 'platformBrandDisplayName', 'savePlatformBrand'];
const ASYNC = ['handlePlatformLogoUpload', 'handlePlatformLoginLogoUpload', 'savePlatformBrand'];
const LOCALES = ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO'];
const PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';
const EVIL = 'data:image/png;base64,AAA" onerror="window.__xss=1';
const copy = v => v === undefined ? undefined : JSON.parse(JSON.stringify(v));

function extract(source, name) {
  const m = new RegExp(`^([ \\t]*)(?:async )?function ${name}\\(`, 'm').exec(source);
  if (!m) {throw new Error(`função ausente: ${name}`);}
  const end = new RegExp(`^${m[1]}\\}\\s*$`, 'm').exec(source.slice(m.index));
  if (!end) {throw new Error(`fim ausente: ${name}`);}
  return source.slice(m.index, m.index + end.index + end[0].trimEnd().length);
}

function environment(original, locale, mutations = {}) {
  const env = {log: [], pending: [], response: {brand: {display_name: 'Resposta', logo_type: PNG}}, file: {}, failure: null};
  const state = {user: {id: 7, role: 'master_admin'}, platformBrand: {display_name: 'Inicial', legal_name: 'Inicial SA', logo_type: PNG}};
  const refs = {};
  function node(id) {
    const n = {id, elements: {}};
    for (const prop of ['value', 'innerHTML', 'textContent']) {
      let value = '';
      Object.defineProperty(n, prop, {enumerable: true, get: () => value, set(v) {value = v; env.log.push([prop, id, v]);}});
    }
    return n;
  }
  const ctx = {console, JSON, Object, Array, String, Number, Math, RegExp, Intl, Date, Promise, Error, Set, Map,
    __EPI_APP_STATE__: state, __EPI_REFS__: refs, __CATALOG_ACTIVE__: JSON.parse(read(`i18n/${locale}.json`)),
    __CATALOG_FALLBACK__: JSON.parse(read('i18n/pt-BR.json'))};
  ctx.globalThis = ctx;
  ctx.window = ctx;
  vm.createContext(ctx);
  const i18n = read('i18n.js');
  vm.runInContext(["const FALLBACK = 'pt-BR'; const _pluralCount = Symbol('numeric plural count');",
    `let _active = __CATALOG_ACTIVE__; let _fallback = __CATALOG_FALLBACK__; let _lang = ${JSON.stringify(locale)};`,
    ...['_resolve', '_interpolate', '_message', 't', 'trEpi'].map(n => extract(i18n, n)), 'var tr = trEpi;'].join('\n'), ctx);
  ctx.EpiI18n = {lang: locale, clearBinding: n => env.log.push(['clearBinding', n.id])};
  vm.runInContext(read('js/core/constants.js'), ctx);
  vm.runInContext(read('js/views/view-helpers.js'), ctx);
  vm.runInContext(read('js/modules/shared/business/value-format.js'), ctx);
  vm.runInContext(read('js/modules/shared/ui/company-logo.js'), ctx);
  vm.runInContext(extract(read('app.js'), 'formValues'), ctx);
  ctx.FormData = function (form) {return {entries: () => Object.entries(form.elements).map(([k,n]) => [k,n.value])[Symbol.iterator]()};};
  ctx.alert = message => env.log.push(['alert', message]);
  ctx.api = (...args) => {
    env.log.push(['api', args.length, ...copy(args)]);
    if (env.deferred) {return new Promise((resolve,reject) => env.pending.push({resolve,reject}));}
    return env.failure ? Promise.reject(Object.assign(new Error(env.failure.message), {status: env.failure.status})) : Promise.resolve(copy(env.response));
  };
  ctx.FileReader = function () {
    const reader = this;
    reader.readAsDataURL = file => {
      env.log.push(['readAsDataURL', file?.name]);
      const behavior = {...env.file, ...file?.behavior};
      Promise.resolve().then(() => {
        if (behavior.error) {return reader.onerror?.();}
        reader.result = behavior.result === undefined ? PNG : behavior.result;
        reader.onload?.();
      });
    };
  };
  ctx.Image = function () {
    this.width = 1440; this.height = 1000;
    Object.defineProperty(this,'src',{set: value => {
      env.log.push(['image',value]);
      Promise.resolve().then(() => env.file.imageError ? this.onerror?.() : this.onload?.());
    }});
  };
  ctx.document = {createElement: tag => {
    if (tag !== 'canvas') {throw new Error('elemento inesperado: ' + tag);}
    const context = {fillRect: (...a) => env.log.push(['fillRect',...a]), drawImage: (_image,...a) => env.log.push(['drawImage',...a])};
    return {getContext: () => context, toDataURL: (...a) => {env.log.push(['toDataURL',...a]); return 'data:image/jpeg;base64,QUJD';}};
  }};
  vm.runInContext(read('js/modules/shared/ui/file-data-url.js'), ctx);
  let functions;
  if (original || !fs.existsSync(path.join(ROOT, UI))) {
    const source = original ? read(FIXTURE) : read('app.js');
    const defaults = /^const DEFAULT_PLATFORM_BRAND = .*;$/m.exec(source)[0];
    vm.runInContext(`if (true) { const state = __EPI_APP_STATE__; const refs = __EPI_REFS__;\n${defaults}\n`
      + NAMES.map(n => extract(source,n)).join('\n')
      + `\nglobalThis.__TEST_BRAND__ = {${NAMES.join(',')}, DEFAULT_PLATFORM_BRAND};\n}`, ctx);
    functions = ctx.__TEST_BRAND__;
  } else {
    for (const file of [API, UI]) {
      let source = read(file);
      if (mutations[file]) {
        const [from,to] = mutations[file];
        if (!source.includes(from)) {throw new Error('mutação sem alvo: ' + from);}
        source = source.replace(from,to);
      }
      vm.runInContext(source,ctx);
    }
    functions = ctx.__EPI_PLATFORM_BRAND_UI__;
  }
  env.ctx = ctx; env.state = state; env.refs = refs; env.functions = functions;
  env.reset = (options = {}) => {
    env.log = []; env.pending = []; env.failure = options.failure || null; env.deferred = false; env.file = options.file || {};
    env.response = Object.hasOwn(options,'response') ? options.response : {brand: {display_name: 'Resposta', logo_type: PNG}};
    state.user = Object.hasOwn(options,'user') ? copy(options.user) : {id: 7,role: 'master_admin',company_id: 901};
    state.platformBrand = Object.hasOwn(options,'brand') ? copy(options.brand) : {display_name:'Inicial',legal_name:'Inicial SA',logo_type:PNG};
    for (const k of Object.keys(refs)) {delete refs[k];}
    for (const k of ['platformLogoPreview','platformLoginLogoPreview','platformBrandName','platformBrandLogo','platformLogoFile','platformLoginLogoFile','loginBrandLogo','platformBrandForm']) {refs[k] = node(k);}
    for (const k of ['display_name','legal_name','cnpj','logo_type','login_logo_type']) {
      refs.platformBrandForm.elements[k] = node(k);
      refs.platformBrandForm.elements[k].value = {display_name:'Digitado <b>x</b>',legal_name:'Empresa & Cia',cnpj:'11222333000181',logo_type:PNG,login_logo_type:''}[k];
    }
    refs.loginBrandLogo.innerHTML = '<img data-tenant="preservar">';
    refs.platformLogoFile.value = 'arquivo'; refs.platformLoginLogoFile.value = 'arquivo';
    if (options.tenant) {ctx.__epiTenant = {name:'Tenant'};} else {delete ctx.__epiTenant;}
    for (const k of options.missing || []) {refs[k] = null;}
    env.log = [];
    return env;
  };
  env.snapshot = result => copy({result,log:env.log,state,nodes:Object.fromEntries(Object.entries(refs).map(([k,n]) => [k,n && {
    value:n.value,innerHTML:n.innerHTML,textContent:n.textContent,fields:Object.fromEntries(Object.entries(n.elements).map(([f,v])=>[f,v.value]))}]))});
  return env.reset();
}

async function invoke(env,name,args = []) {
  let result;
  try {result = ['ok',await env.functions[name](...args)];} catch (e) {result = ['error',e.name,e.message];}
  await Promise.resolve();
  return env.snapshot(result);
}

async function compareAll(mutations = {}) {
  let count = 0;
  for (const lang of LOCALES) {
    const before = environment(true,lang), after = environment(false,lang,mutations);
    const check = async (name,options = {},args = []) => {
      const a = await invoke(before.reset(options),name,args.map(a=>typeof a==='function'?a(before):a));
      const b = await invoke(after.reset(options),name,args.map(a=>typeof a==='function'?a(after):a));
      if (JSON.stringify(a)!==JSON.stringify(b)) {throw new Error(`${lang} ${name} ${JSON.stringify(options)}\nantes=${JSON.stringify(a)}\ndepois=${JSON.stringify(b)}`);}
      count++;
    };
    for (const brand of [null,{}, {display_name:''}, {display_name:'Marca <img src=x onerror=x>',logo_type:EVIL,login_logo_type:EVIL},
      {display_name:'Marca B',legal_name:'Legal',cnpj:'123',logo_type:PNG,login_logo_type:PNG}]) {
      for (const tenant of [false,true]) {for (const missing of [[],['platformBrandName'],['platformBrandLogo'],['platformBrandForm'],['platformLogoPreview','platformLoginLogoPreview'],['loginBrandLogo'],['platformLogoFile','platformLoginLogoFile']]) {
        await check('renderPlatformBrand',{brand,tenant,missing});
      }}
      await check('platformBrandDisplayName',{brand});
    }
    for (const name of ['renderPlatformLogoPreview','renderPlatformLoginLogoPreview']) {
      for (const value of [PNG,EVIL,'',null,undefined,'javascript:alert(1)']) {await check(name,{},[value]);}
    }
    const users = [null,{}, {id:7,role:'user'}, {id:9,role:'general_admin'}, {id:3,role:'registry_admin'}, {id:7,role:'master_admin'}, {id:88,role:'master_admin',company_id:902}];
    for (const user of users) {for (const response of [{brand:{display_name:'Nova',logo_type:PNG}}, {brand:{}}, {},null]) {
      await check('savePlatformBrand',{user,response},[env=>({preventDefault:()=>env.log.push(['preventDefault'])})]);
    }}
    for (const status of [401,403,500,0]) {await check('savePlatformBrand',{failure:{status,message:'Falha '+status}},[env=>({preventDefault:()=>env.log.push(['preventDefault'])})]);}
    for (const name of ['handlePlatformLogoUpload','handlePlatformLoginLogoUpload']) {
      for (const type of ['image/png','image/jpeg','image/svg+xml','text/plain','']) {for (const file of [{},{error:true},{imageError:true},{result:''}]) {
        await check(name,{file},[env=>({target:env.refs.platformLogoFile.files ? env.refs.platformLogoFile : Object.assign(env.refs.platformLogoFile,{files:[{name:'logo',type}]})})]);
      }}
      await check(name,{},[env=>({target:Object.assign(env.refs.platformLogoFile,{files:[]})})]);
    }
    // Troca de principal e resposta anterior fora de ordem: preservar inclusive os efeitos legados.
    const race = async (env) => {
      env.reset(); env.deferred=true;
      const event={preventDefault:()=>env.log.push(['preventDefault'])};
      const a=env.functions.savePlatformBrand(event);
      env.state.user={id:99,role:'master_admin',company_id:902}; env.state.platformBrand={display_name:'Sessão B'};
      const b=env.functions.savePlatformBrand(event);
      env.pending[1].resolve({brand:{display_name:'B'}}); await b;
      env.pending[0].resolve({brand:{display_name:'A'}}); await a;
      return env.snapshot(['ok',env.functions.platformBrandDisplayName()]);
    };
    if (JSON.stringify(await race(before))!==JSON.stringify(await race(after))) {throw new Error(lang+' corrida diverge');}
    count++;
    for (const env of [before,after]) {
      env.reset(); env.functions.renderPlatformBrand();
      env.state.platformBrand={display_name:'Bootstrap B',login_logo_type:PNG}; env.state.user={id:99,role:'user',company_id:902};
      env.functions.renderPlatformBrand();
    }
    if(JSON.stringify(before.snapshot())!==JSON.stringify(after.snapshot())) {throw new Error(lang+' bootstrap diverge');}
    count++;
    const parallelFiles = async (env) => {
      env.reset();
      await Promise.all([
        env.functions.handlePlatformLogoUpload({target:{value:'a',files:[{name:'a',type:'image/png',behavior:{result:PNG}}]}}),
        env.functions.handlePlatformLogoUpload({target:{value:'b',files:[{name:'b',type:'image/svg+xml',behavior:{result:'data:image/svg+xml;base64,PHN2Zy8+'}}]}})
      ]);
      return env.snapshot();
    };
    if(JSON.stringify(await parallelFiles(before))!==JSON.stringify(await parallelFiles(after))) {throw new Error(lang+' uploads paralelos divergem');}
    count++;
  }
  return count;
}

function contracts(mutations = {}) {
  const assert = require('assert');
  const app=read('app.js'), fixture=read(FIXTURE);
  if (!fs.existsSync(path.join(ROOT,UI))) {
    for (const n of NAMES) {assert.strictEqual(extract(app,n),extract(fixture,n),'fixture literal: '+n);}
    return;
  }
  const e=environment(false,'pt-BR',mutations), ns=e.ctx.__EPI_PLATFORM_BRAND_UI__;
  assert(Object.isFrozen(ns) && Object.isFrozen(e.ctx.__EPI_PLATFORM_BRAND_API__));
  for(const n of NAMES) {
    assert(!new RegExp(`^(?:async )?function ${n}\\(`,'m').test(app),n+' saiu do app.js');
    assert.strictEqual(typeof ns[n],'function');
    assert.strictEqual(e.ctx[n],ASYNC.includes(n)?undefined:ns[n],n+' publicação preservada');
  }
  const originalDefault=/^const DEFAULT_PLATFORM_BRAND = (.*);$/m.exec(fixture)[1];
  assert(read(UI).includes('const DEFAULT_PLATFORM_BRAND = '+originalDefault+';'),'única definição literal preservada');
  assert(app.includes('const DEFAULT_PLATFORM_BRAND = globalThis.__EPI_PLATFORM_BRAND_UI__.DEFAULT_PLATFORM_BRAND;'));
  vm.runInContext('globalThis.__defaultAlias = (() => { '+/^const DEFAULT_PLATFORM_BRAND = .*;$/m.exec(app)[0]+' return DEFAULT_PLATFORM_BRAND; })()',e.ctx);
  assert.strictEqual(e.ctx.__defaultAlias,ns.DEFAULT_PLATFORM_BRAND,'mesmo objeto, sem cópia');
  const source=read(UI);
  assert(!/\b(?:api|fetch)\s*\(|\/api\//.test(source),'UI sem HTTP');
  assert(!/document\.|__EPI_APP_STATE__|__EPI_REFS__/.test(read(API)),'integração sem DOM/estado');
  const scripts=[...read('views/_scripts.html').matchAll(/src="([^"?]+)/g)].map(m=>m[1]);
  for(const p of [API,UI]) {
    assert.strictEqual(scripts.filter(s=>s==='/'+p).length,1);
    assert(scripts.indexOf('/'+p)<scripts.indexOf('/app.js'));
  }
  assert(scripts.indexOf('/'+API)<scripts.indexOf('/'+UI));
  const stable=ns.savePlatformBrand;
  vm.runInContext(read(UI),e.ctx);
  assert.strictEqual(e.ctx.__EPI_PLATFORM_BRAND_UI__.savePlatformBrand,stable,'carga idempotente');
  for(const n of ASYNC) {assert(app.includes("'"+(n==='savePlatformBrand'?'submit':'change')+"', globalThis.__EPI_PLATFORM_BRAND_UI__."+n),n+' listener no app');}
}

module.exports = ({test,testAsync}) => {
  test('UBX Marca: contrato, definição única, publicação, carga e listeners',contracts);
  testAsync('UBX Marca: fixture original × código servido nos cinco idiomas',async()=>console.log('    Marca: '+await compareAll()+' comparações, zero divergências'));
};
module.exports.compareAll=compareAll;
module.exports.contracts=contracts;
if(require.main===module) {
  contracts(); compareAll().then(n=>console.log('UBX Marca OK: '+n+' comparações')).catch(e=>{console.error(e);process.exitCode=1;});
}
