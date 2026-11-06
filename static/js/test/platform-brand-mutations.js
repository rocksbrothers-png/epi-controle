'use strict';
// Sabotagens exclusivamente em memória. Nenhum módulo/fixture é gravado.
const suite = require('./platform-brand-runtime');
const UI = 'js/modules/platform-brand/ui/platform-brand-view.js';
const API = 'js/modules/platform-brand/integrations/platform-brand-api.js';
const mutations = [
  ['método',API,"method: 'POST'","method: 'PUT'"],
  ['caminho',API,"'/api/platform-brand'","'/api/platform-brand-wrong'"],
  ['ator serializado',API,'JSON.stringify(values)','JSON.stringify({...values,actor_user_id:0})'],
  ['CNPJ omitido',API,'JSON.stringify(values)',"JSON.stringify({...values,cnpj:''})"],
  ['opções extras',API,"method: 'POST', body:","method: 'POST', headers: {}, body:"],
  ['resposta descartada',API,'return globalThis.api','globalThis.api'],
  ['permissão removida',UI,"if (state.user?.role !== 'master_admin') {return;}",'if (false) return;'],
  ['ator incorreto',UI,'values.actor_user_id = state.user.id','values.actor_user_id = 0'],
  ['formatação CNPJ',UI,'values.cnpj = formatCnpj(values.cnpj)','values.cnpj = values.cnpj'],
  ['precedência padrão',UI,'{ ...DEFAULT_PLATFORM_BRAND, ...payload.brand }','{ ...payload.brand, ...DEFAULT_PLATFORM_BRAND }'],
  ['await removido',UI,'await globalThis.__EPI_PLATFORM_BRAND_API__.saveBrand(values)','globalThis.__EPI_PLATFORM_BRAND_API__.saveBrand(values)'],
  ['ordem de renderização',UI,'      renderPlatformBrand();\n      alert(', '      alert("antecipado");\n      renderPlatformBrand();\n      alert('],
  ['preventDefault removido',UI,'event.preventDefault();',''],
  ['estado copiado',UI,'      state.platformBrand = {','      const staleState = {...state}; staleState.platformBrand = {'],
  ['precedência tenant',UI,'else if (!window.__epiTenant)','else if (true)'],
  ['binding vivo',UI,'globalThis.EpiI18n?.clearBinding?.(refs.platformBrandName);',''],
  ['nome como HTML',UI,'refs.platformBrandName.textContent =','refs.platformBrandName.innerHTML ='],
  ['validação MIME',UI,'if (!allowed.includes(file.type))','if (false)'],
  ['conversão JPEG',UI,'await fileToJpegDataUrl(file)','await fileToDataUrl(file)'],
  ['login aceita JPEG',UI,"const allowed = ['image/png', 'image/svg+xml'];","const allowed = ['image/png', 'image/jpeg', 'image/svg+xml'];"],
  ['limpeza sem arquivo',UI,"refs.platformBrandForm.elements.logo_type.value = '';","refs.platformBrandForm.elements.logo_type.value = 'resíduo';"],
  ['mensagem traduzida',UI,"tr('commercial.panel.brandUpdated', 'Marca da sua empresa atualizada.')","'Marca da sua empresa atualizada.'"],
  ['padrão do nome',UI,'state.platformBrand?.display_name || DEFAULT_PLATFORM_BRAND.display_name',"state.platformBrand?.display_name || ''"],
  ['publicação async',UI,'globalThis[name] = functions[name];','globalThis[name] = functions[name]; globalThis.savePlatformBrand = functions.savePlatformBrand;'],
  ['namespace mutável',UI,'Object.freeze({ ...functions, DEFAULT_PLATFORM_BRAND })','({ ...functions, DEFAULT_PLATFORM_BRAND })']
];

async function main() {
  let killed=0;
  for(const [name,file,from,to] of mutations) {
    let detected=false;
    try {
      const changed = {[file]:[from,to]};
      suite.contracts(changed);
      await suite.compareAll(changed);
    } catch(error) {
      if(error.message.includes('mutação sem alvo')) {throw error;}
      detected=true;
    }
    console.log((detected?'DETECTADA ':'SOBREVIVEU ')+name);
    if(detected) {killed++;}
  }
  console.log(`${killed}/${mutations.length} mutações detectadas`);
  if(killed!==mutations.length) {process.exitCode=1;}
}
main().catch(error=>{console.error(error);process.exitCode=1;});
