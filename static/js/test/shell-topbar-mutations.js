'use strict';
const assert=require('assert');const runtime=require('./shell-topbar-runtime');
const mutants=[
  ['topbar-view.js','retorno sem elemento','if (!badge) {return;}','if (false) {return;}'],
  ['topbar-view.js','fallback de unidade','state.user?.unit_name || state.user?.current_unit_name','state.user?.unit_name'],
  ['topbar-view.js','escape de empresa/unidade','escapeHtml(label)','label'],
  ['topbar-view.js','badge acesso geral oculto','badge.hidden = false;','badge.hidden = true;'],
  ['topbar-view.js','classe geral residual',"badge.classList.remove('topbar-company-badge--general');",''],
  ['topbar-view.js','contexto de empresa obsoleto','const company = state.user?.company_name;',"const company = 'Empresa fixa';"],
  ['topbar-view.js','ícone de tema invertido',"dark ? '☀️' : '🌙'","dark ? '🌙' : '☀️'"],
  ['topbar-view.js','aria-pressed incorreto',"dark ? 'true' : 'false'","dark ? 'false' : 'true'"],
  ['topbar-view.js','toggle deixa de alternar',"dark ? 'light' : 'dark'","dark ? 'dark' : 'dark'"],
  ['topbar-view.js','dupla persistência',"definirPreferencias({ tema: dark ? 'light' : 'dark' });","definirPreferencias({ tema: dark ? 'light' : 'dark' }); definirPreferencias({ tema: 'light' });"],
  ['shell-view.js','menu não fecha',"document.body?.classList.remove('mobile-menu-open');",''],
  ['shell-view.js','ARIA ao abrir',"setAttribute('aria-expanded', 'true')","setAttribute('aria-expanded', 'false')"],
  ['shell-view.js','mobile não fecha ao desativar','if (!enabled) {closeMobileMenu();}','if (false) {closeMobileMenu();}'],
  ['shell-view.js','flag mobile invertida',"toggle('ux-mobile-enabled', enabled)","toggle('ux-mobile-enabled', !enabled)"],
  ['shell-view.js','mini-rail no mobile','!isUxMobileEnabled() && isSidebarCollapsedPref()','isSidebarCollapsedPref()'],
  ['shell-view.js','sidebar prefere estado fixo',"return preferenciasDoPrincipal().sidebar === 'collapsed';",'return false;'],
  ['shell-view.js','persistência sidebar invertida',"isSidebarCollapsedPref() ? 'expanded' : 'collapsed'","isSidebarCollapsedPref() ? 'collapsed' : 'expanded'"],
  ['shell-view.js','grupo mostra itens ocultos',"node.style.display !== 'none'",'true'],
  ['settings-drawer.js','densidade invertida',"preferenciasDoPrincipal().densidade === 'compact'","preferenciasDoPrincipal().densidade !== 'compact'"],
  ['settings-drawer.js','botão avançado sem permissão','const advanced = hasConfigurationAccess()','const advanced = true'],
  ['settings-drawer.js','footer sem salvar','id="settings-save"','id="settings-wrong"'],
  ['settings-drawer.js','fallback ignora autorização','if (hasConfigurationAccess())','if (true)'],
  ['settings-drawer.js','histórico SPA alterado',"isSpaNavigationEnabled() ? 'push' : null","'push'"],
  ['settings-drawer.js','cancelar persiste',"bindAppListener(root.querySelector('#settings-cancel'), 'click', () => globalThis.dsCloseDrawer());","bindAppListener(root.querySelector('#settings-cancel'), 'click', () => { _applySettings({theme:'dark',density:'compact'}); globalThis.dsCloseDrawer(); });"],
  ['settings-drawer.js','salvar densidade ignora campo',"density: val('#settings-density', 'normal')","density: 'normal'"],
  ['settings-drawer.js','restaurar grava em vez de só alterar campos','// Reseta os campos para o padrão; o usuário confirma em Salvar.',"_applySettings({theme:'light',density:'normal'});"],
  ['settings-drawer.js','ordem fecha antes de salvar','    _applySettings({','    globalThis.dsCloseDrawer();\n      _applySettings({']
];
const contracts=[
  ['topbar-view.js','guarda de carga','if (globalThis.__EPI_MODULE_TOPBAR_VIEW_LOADED__) { return; }',''],
  ['settings-drawer.js','fachada congelada','Object.freeze({ ...exports })','Object.seal({ ...exports })']
];
(async()=>{
 let detected=0;
 for(const [file,label,from,to]of [...mutants,...contracts]){
  let killed=false;
  try{const m={file,from,to};if(contracts.some(x=>x[1]===label)){runtime.contracts(m);}else{await runtime.compareAll(m);}}
  catch(error){if(error.message.startsWith('mutação sem alvo:')){throw error;}assert(error instanceof assert.AssertionError,'erro do harness: '+label+' '+error.message);killed=true;}
  assert(killed,'mutação sobrevivente: '+label);detected++;
 }
 console.log('UBX Shell/Topbar: '+detected+'/'+(mutants.length+contracts.length)+' mutações detectadas');
})().catch(error=>{console.error(error);process.exitCode=1;});
