'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');
const ROOT = path.resolve(__dirname, '..', '..');
const read = rel => fs.readFileSync(path.join(ROOT, rel), 'utf8');
const MODULES = {
  'shell-view.js': ['closeMobileMenu','openMobileMenu','applyMobileUxVisibility','isSidebarCollapsedPref','applySidebarCollapsed','toggleSidebarCollapsed','applyMenuGroupVisibility'],
  'topbar-view.js': ['updateTopbarCompanyBadge','applyThemeToggleUI','setupThemeToggle'],
  'settings-drawer.js': ['applyTableDensityPref','_settingsDrawerBodyHtml','_settingsDrawerFooterHtml','openSettingsDrawer']
};
const NAMES = Object.values(MODULES).flat();
const FIXTURE = 'js/test/fixtures/app-before-ubx-shell-topbar.js.txt';
const LOCALES = ['pt-BR','en-GB','es-ES','fr-FR','nb-NO'];
const OWNER = ['prefsPrincipalCorrente','prefsCarimboDoPrincipal','prefsNormalizar','prefsDescartarSeTrocouPrincipal',
  'prefsLerCopiaDeSessao','prefsGravarCopiaDeSessao','preferenciasDoPrincipal','adotarPreferenciasDoServidor',
  'prefsEnviarAoServidor','definirPreferencias','aplicarPreferenciasNaTela','_applySettings'];
const clone = x => JSON.parse(JSON.stringify(x));
function extract(source, name) {
  const m = new RegExp(`^([ \\t]*)(?:async )?function ${name}\\(`, 'm').exec(source);
  if (!m) {throw new Error('função ausente: ' + name);}
  const end = new RegExp(`^${m[1]}\\}\\s*$`, 'm').exec(source.slice(m.index));
  return source.slice(m.index, m.index + end.index + end[0].trimEnd().length);
}

function environment(original, locale, mutation) {
  const env = {log: [], nodes: {}, listeners: [], fail: null, mobile: false, allowed: true, prefs: {}, storage: new Map()};
  const fail = label => {if (env.fail === label) {throw new Error('QA ' + label);}};
  function node(id) {
    const attrs = {}, classes = new Set();
    const n = {id, attrs, classes, children: [], value: '', style: {}};
    for (const field of ['innerHTML','textContent','hidden','title']) {
      let value = field === 'hidden' ? false : '';
      Object.defineProperty(n, field, {enumerable:true, get:()=>value, set(v) {fail(field);value=v;env.log.push([field,id,v]);}});
    }
    let display='';Object.defineProperty(n.style,'display',{enumerable:true,get:()=>display,set(v){display=v;env.log.push(['display',id,v]);}});
    n.classList = {
      add(...items) {fail('classList');items.forEach(v=>classes.add(v));env.log.push(['add',id,...items]);},
      remove(...items) {fail('classList');items.forEach(v=>classes.delete(v));env.log.push(['remove',id,...items]);},
      contains(value) {return classes.has(value);},
      toggle(value, force) {fail('classList');const on=force===undefined?!classes.has(value):!!force;if(on){classes.add(value);}else{classes.delete(value);}env.log.push(['toggle',id,value,on]);return on;}
    };
    n.setAttribute=(key,value)=>{fail('setAttribute');attrs[key]=String(value);env.log.push(['attribute',id,key,String(value)]);};
    n.removeAttribute=key=>{fail('removeAttribute');delete attrs[key];env.log.push(['removeAttribute',id,key]);};
    n.getAttribute=key=>attrs[key]??null;
    n.querySelector=selector=>env.missing.includes(selector.slice(1))?null:env.nodes[selector.slice(1)]||null;
    n.matches=selector=>selector==='[data-menu-group]'&&id.startsWith('group');
    return n;
  }
  const ctx = {console:{warn(){},error(){}},Object,Array,String,Number,Math,Intl,Date,JSON,Promise,Error,Set,Map,WeakMap,
    __EPI_APP_STATE__:{user:null},__EPI_REFS__:{},__CATALOGS__:Object.fromEntries(LOCALES.map(l=>[l,JSON.parse(read('i18n/'+l+'.json'))]))};
  ctx.window=ctx;ctx.globalThis=ctx;
  Object.defineProperty(ctx,'state',{get:()=>ctx.__EPI_APP_STATE__});
  Object.defineProperty(ctx,'refs',{get:()=>ctx.__EPI_REFS__});
  vm.createContext(ctx);
  const i18n=read('i18n.js');
  vm.runInContext("const FALLBACK='pt-BR';const _pluralCount=Symbol('numeric plural count');let _active=__CATALOGS__['"+locale+"'];let _fallback=__CATALOGS__['pt-BR'];let _lang='"+locale+"';\n"
    +['_resolve','_interpolate','_message','t','trEpi'].map(n=>extract(i18n,n)).join('\n')
    +'\nvar tr=trEpi;globalThis.__testLang=l=>{_active=__CATALOGS__[l];_lang=l;};',ctx);
  vm.runInContext(read('js/core/constants.js'),ctx);
  vm.runInContext(read('js/views/view-helpers.js'),ctx);
  ctx.document = {body:null,documentElement:null,getElementById:id=>{fail('getElementById');return env.missing.includes(id)?null:env.nodes[id]||null;}};
  ctx.isUxMobileEnabled=()=>{env.log.push(['isMobile',env.mobile]);return env.mobile;};
  ctx.hasConfigurationAccess=()=>{env.log.push(['hasConfig',env.allowed]);return env.allowed;};
  ctx.isSpaNavigationEnabled=()=>env.spa;
  ctx.navigateToView=(...args)=>{env.log.push(['navigate',...clone(args)]);fail('navigate');};
  ctx.bindAppListener=(target,event,handler)=>{env.log.push(['bind',target?.id||null,event]);fail('bind');if(target){env.listeners.push({target,event,handler});}return !!target;};
  ctx.reportNonCriticalError=(label,error)=>env.log.push(['reported',label,error.message]);
  ctx.api=(...args)=>{env.log.push(['api',...clone(args)]);if(env.network==='throw'){throw new Error('QA rede');}return env.network==='reject'?Promise.reject(new Error('QA rede')):Promise.resolve({});};
  ctx.sessionStorage={getItem:k=>{env.log.push(['getStorage',k]);return env.storage.get(k)||null;},setItem:(k,v)=>{fail('storage');env.storage.set(k,v);env.log.push(['setStorage',k,v]);},removeItem:k=>{env.storage.delete(k);env.log.push(['removeStorage',k]);}};
  const app=read('app.js');
  const constants=['PREFS_PADRAO','PREFS_VALORES'].map(n=>new RegExp('^const '+n+' = Object.freeze\\(\\{[\\s\\S]*?^\\}\\);','m').exec(app)[0]);
  vm.runInContext(constants.join('\n')+"\nconst PREFS_SESSAO_KEY='epi-prefs-sessao';let _prefsEmMemoria=null;let _prefsPrincipal;\n"+OWNER.map(n=>extract(app,n)).join('\n'),ctx);
  const served=fs.existsSync(path.join(ROOT,'js/modules/shell/ui/topbar-view.js'));
  if(original||!served){vm.runInContext(NAMES.map(n=>extract(original?read(FIXTURE):app,n)).join('\n'),ctx);}
  else {for(const file of Object.keys(MODULES)){
    let src=read('js/modules/shell/ui/'+file);
    if(mutation?.file===file){if(!src.includes(mutation.from)){throw new Error('mutação sem alvo: '+mutation.from);}src=src.replace(mutation.from,mutation.to);}
    vm.runInContext(src,ctx);
  }}
  env.ctx=ctx;
  env.reset=(o={})=>{
    env.log=[];env.listeners=[];env.nodes={};env.missing=o.missing||[];env.fail=null;
    env.mobile=!!o.mobile;env.allowed=o.allowed!==false;env.spa=o.spa!==false;env.network=o.network||'';env.storage=new Map();
    ctx.__EPI_APP_STATE__={user:Object.hasOwn(o,'user')?clone(o.user):{id:7,role:'master_admin',company_name:'Empresa & Cia',unit_name:'Base <QA>'}};
    ctx.__EPI_REFS__={};
    for(const id of ['body','html','topbar-company-badge','theme-toggle','mobile-menu-toggle','menu','ds-drawer-root',
      'settings-theme','settings-language','settings-density','settings-save','settings-cancel','settings-restore','settings-advanced','group-a','link-a','group-b','link-b']){env.nodes[id]=node(id);}
    env.nodes['link-a'].classes.add('menu-link');env.nodes['link-b'].classes.add('menu-link');
    env.nodes['link-a'].style.display=o.linkHidden?'none':'';env.nodes['link-b'].style.display='none';
    env.nodes.menu.children=['group-a','link-a','group-b','link-b'].map(id=>env.nodes[id]);
    ctx.document.body=o.body===false?null:env.nodes.body;ctx.document.documentElement=env.nodes.html;
    ctx.__EPI_REFS__.mobileMenuToggle=env.missing.includes('mobile-menu-toggle')?null:env.nodes['mobile-menu-toggle'];
    const prefs={tema:'light',densidade:'normal',sidebar:'expanded',idioma:locale,...o.prefs};
    if(prefs.tema==='dark'){env.nodes.html.setAttribute('data-theme','dark');}
    env.nodes['settings-theme'].value=o.draftTheme||'dark';env.nodes['settings-language'].value=o.draftLang||locale;env.nodes['settings-density'].value=o.draftDensity||'compact';
    ctx.__preset=prefs;vm.runInContext('_prefsEmMemoria=prefsNormalizar(__preset);_prefsPrincipal=prefsPrincipalCorrente();',ctx);
    ctx.__testLang(locale);
    ctx.EpiI18n={lang:locale,setLang:(l,options)=>{env.log.push(['setLang',l,options||null]);ctx.EpiI18n.lang=l;ctx.__testLang(l);return Promise.resolve();}};
    if(o.binding!=='missing'){
      ctx.EpiI18n.textFor=(n,key,fallback)=>{env.log.push(['textFor',n.id,key,fallback]);return o.binding==='null'?null:ctx.tr(key,fallback);};
      ctx.EpiI18n.attributeFor=(n,attr,key,fallback)=>{env.log.push(['attributeFor',n.id,attr,key,fallback]);return o.binding==='null'?null:ctx.tr(key,fallback);};
    }
    if(o.engine===false){delete ctx.EpiI18n;}
    if(!env.allowed){delete env.nodes['settings-advanced'];}
    ctx.dsOpenDrawer=options=>{env.log.push(['openDrawer',clone(options)]);fail('drawer');};
    if(o.drawer===false){delete ctx.dsOpenDrawer;}
    ctx.dsCloseDrawer=()=>{env.log.push(['closeDrawer']);fail('closeDrawer');};
    env.fail=o.fail||null;env.log=[];
    return env;
  };
  env.click=(id)=>{for(const l of [...env.listeners]){if(l.target===env.nodes[id]&&l.event==='click'){l.handler();}}};
  env.snapshot=result=>clone({result,log:env.log,storage:[...env.storage],user:ctx.__EPI_APP_STATE__.user,
    nodes:Object.fromEntries(Object.entries(env.nodes).map(([id,n])=>[id,{attrs:n.attrs,classes:[...n.classes],html:n.innerHTML,text:n.textContent,hidden:n.hidden,title:n.title,value:n.value,display:n.style.display}])),lang:ctx.EpiI18n?.lang||null,listeners:env.listeners.map(l=>[l.target.id,l.event])});
  return env.reset();
}

async function invoke(env,name,args=[],drive) {
  let result;
  try {const value=env.ctx[name](...args);if(drive){drive(env);}result=value===undefined?['undefined']:value;}
  catch(error){result=['error',error.name,error.message];}
  await Promise.resolve();await Promise.resolve();return env.snapshot(result);
}
async function compareAll(mutation) {
  let count=0;
  for(const locale of LOCALES){
    const before=environment(true,locale),after=environment(false,locale,mutation);
    const check=async(name,options={},args=[],drive)=>{
      const a=await invoke(before.reset(options),name,args,drive),b=await invoke(after.reset(options),name,args,drive);
      assert.deepStrictEqual(b,a,locale+' '+name+' '+JSON.stringify(options));count++;
    };
    for(const user of [null,{}, {id:8,role:'employee'}, {id:7,company_name:'',unit_name:'U'},
      {id:7,company_name:'A & <img src=x onerror=x>',unit_name:'<b>U</b>'}, {id:9,company_name:'B',current_unit_name:'Outra'},
      {id:9,company_name:'B',unit_name:'Preferida',current_unit_name:'Ignorar'}]){
      for(const binding of ['present','missing','null']){await check('updateTopbarCompanyBadge',{user,binding});}
    }
    await check('updateTopbarCompanyBadge',{missing:['topbar-company-badge']});
    await check('updateTopbarCompanyBadge',{},[],e=>{
      e.ctx.__EPI_APP_STATE__.user={id:99,tenant_id:2,company_name:'Nova',current_unit_name:'Nova unidade'};e.ctx.updateTopbarCompanyBadge();
      e.ctx.__EPI_APP_STATE__.user=null;e.ctx.updateTopbarCompanyBadge();
    });
    for(const tema of ['light','dark']){for(const binding of ['present','missing','null']){
      await check('applyThemeToggleUI',{prefs:{tema},binding});
      await check('setupThemeToggle',{prefs:{tema},binding},[],e=>{e.click('theme-toggle');e.click('theme-toggle');});
    }}
    for(const name of ['applyThemeToggleUI','setupThemeToggle']){await check(name,{missing:['theme-toggle']});}
    await check('setupThemeToggle',{},[],e=>{e.ctx.setupThemeToggle();e.click('theme-toggle');});
    for(const mobile of [false,true]){for(const sidebar of ['expanded','collapsed']){for(const missing of [[],['mobile-menu-toggle']]){
      const o={mobile,prefs:{sidebar},missing};for(const n of ['closeMobileMenu','openMobileMenu','applyMobileUxVisibility','isSidebarCollapsedPref','applySidebarCollapsed','toggleSidebarCollapsed']){await check(n,o);}
    }}}
    for(const n of ['closeMobileMenu','openMobileMenu','applyMobileUxVisibility','applySidebarCollapsed','applyTableDensityPref']){await check(n,{body:false});}
    for(const densidade of ['normal','compact']){await check('applyTableDensityPref',{prefs:{densidade}});}
    for(const allowed of [false,true]){for(const tema of ['light','dark']){for(const densidade of ['normal','compact']){
      await check('_settingsDrawerBodyHtml',{allowed,prefs:{tema,densidade}});
    }}}
    await check('_settingsDrawerBodyHtml',{engine:false});await check('_settingsDrawerFooterHtml');
    for(const allowed of [false,true]){for(const spa of [false,true]){
      await check('openSettingsDrawer',{allowed,spa,drawer:false});
      for(const action of ['settings-save','settings-cancel','settings-restore','settings-advanced']){
        await check('openSettingsDrawer',{allowed,spa},[],e=>e.click(action));
      }
    }}
    await check('openSettingsDrawer',{missing:['ds-drawer-root']});
    for(const id of ['settings-theme','settings-language','settings-density','settings-save','settings-cancel','settings-restore','settings-advanced']){
      await check('openSettingsDrawer',{missing:[id]},[],e=>{e.click('settings-restore');e.click('settings-save');});
    }
    await check('openSettingsDrawer',{draftTheme:'',draftLang:'',draftDensity:''},[],e=>e.click('settings-save'));
    for(const network of ['throw','reject']){await check('openSettingsDrawer',{network},[],e=>e.click('settings-save'));}
    for(const linkHidden of [false,true]){await check('applyMenuGroupVisibility',{linkHidden});}
    await check('applyMenuGroupVisibility',{missing:['menu']});
    for(const [name,fail] of [['updateTopbarCompanyBadge','getElementById'],['updateTopbarCompanyBadge','innerHTML'],['applyThemeToggleUI','setAttribute'],
      ['openSettingsDrawer','drawer'],['openSettingsDrawer','bind'],['toggleSidebarCollapsed','storage'],['applySidebarCollapsed','classList']]){await check(name,{fail});}
    await check('toggleSidebarCollapsed',{},[],e=>{
      e.ctx.__EPI_APP_STATE__.user={id:80,tenant_id:2,role:'admin'};e.ctx.toggleSidebarCollapsed();
      e.ctx.adotarPreferenciasDoServidor({tema:'dark',sidebar:'expanded',densidade:'compact',idioma:locale});
      e.ctx.__EPI_APP_STATE__.user=null;e.ctx.toggleSidebarCollapsed();
    });
  }
  return count;
}

async function protocol(){
  const e=environment(false,'en-GB');
  e.ctx.updateTopbarCompanyBadge();assert(e.nodes['topbar-company-badge'].innerHTML.includes('Empresa &amp; Cia'));
  e.ctx.__EPI_APP_STATE__.user=null;e.ctx.updateTopbarCompanyBadge();assert(e.nodes['topbar-company-badge'].classes.has('topbar-company-badge--general'));
  e.reset();e.ctx.openSettingsDrawer();e.click('settings-cancel');assert(!e.log.some(l=>l[0]==='api'),'Cancelar não persiste');
  e.reset();e.ctx.openSettingsDrawer();e.click('settings-save');await Promise.resolve();
  assert.strictEqual(e.log.filter(l=>l[0]==='api').length,1,'um clique, uma gravação de tema/densidade pelo dono');
  assert(e.log.findIndex(l=>l[0]==='api')<e.log.findIndex(l=>l[0]==='closeDrawer'));
  e.reset({drawer:false,allowed:false});e.ctx.openSettingsDrawer();assert(!e.log.some(l=>l[0]==='navigate'));
}
function contracts(mutation){
  const exists=fs.existsSync(path.join(ROOT,'js/modules/shell/ui/topbar-view.js'));
  if(!exists){for(const name of NAMES){assert.strictEqual(extract(read('app.js'),name),extract(read(FIXTURE),name));}return;}
  const e=environment(false,'pt-BR',mutation);const fns=NAMES.map(n=>e.ctx[n]);
  for(const file of Object.keys(MODULES)){let src=read('js/modules/shell/ui/'+file);if(mutation?.file===file){if(!src.includes(mutation.from)){throw new Error('mutação sem alvo: '+mutation.from);}src=src.replace(mutation.from,mutation.to);}vm.runInContext(src,e.ctx);}
  NAMES.forEach((n,i)=>assert.strictEqual(e.ctx[n],fns[i],'carga idempotente: '+n));
  for(const ns of ['__EPI_SHELL_UI__','__EPI_TOPBAR_UI__','__EPI_SETTINGS_DRAWER_UI__']){assert(Object.isFrozen(e.ctx[ns]));}
  const scripts=[...read('views/_scripts.html').matchAll(/src="([^"?]+)/g)].map(m=>m[1]);
  for(const file of Object.keys(MODULES)){
    const rel='/js/modules/shell/ui/'+file;assert.strictEqual(scripts.filter(s=>s===rel).length,1);assert(scripts.indexOf(rel)<scripts.indexOf('/app.js'));
    const src=read(rel.slice(1));assert(!/\b(?:sessionStorage|localStorage|fetch|XMLHttpRequest)\b|\bapi\s*\(/.test(src));
  }
  for(const n of NAMES){assert(!new RegExp('^function '+n+'\\(','m').test(read('app.js')));}
}
module.exports=({test,testAsync})=>{
  testAsync('UBX Shell/Topbar: equivalência de UI, eventos, contexto e dono real das preferências',async()=>{console.log('    Shell/Topbar: '+await compareAll()+' comparações, zero divergências');});
  testAsync('UBX Shell/Topbar: escapes, cancelamento, persistência e autorização canônicas',protocol);
  test('UBX Shell/Topbar: globais, carga idempotente, namespaces e ordem dos scripts',contracts);
};
module.exports.compareAll=compareAll;module.exports.protocol=protocol;module.exports.contracts=contracts;
if(require.main===module){(async()=>{contracts();await protocol();console.log('UBX Shell/Topbar OK: '+await compareAll()+' comparações');})().catch(e=>{console.error(e);process.exitCode=1;});}
