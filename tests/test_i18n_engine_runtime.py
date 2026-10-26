"""Runtime contracts for asynchronous, identity-owned language changes."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def run_scenario(scenario):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node.js unavailable')
    script = r'''
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const writes = [], events = [], pending = {};
const dictionaries = {
  'pt-BR': {label:'Português', greeting:'Olá, {name}', action:'Salvar', note:'Existente', summary:'Configuração {note}'},
  'en-GB': {label:'English', greeting:'Hello, {name}', action:'Save', note:'Existing', summary:'Configuration {note}'},
  'fr-FR': {label:'Français', greeting:'Bonjour, {name}', action:'Enregistrer', note:'Existant', summary:'Configuration {note}'},
};
function element(attrs = {}) {
  return {nodeType:1, firstElementChild:null, textContent:'',
    attrs:{...attrs}, querySelectorAll(){return []},
    hasAttribute(k){return Object.hasOwn(this.attrs,k)}, removeAttribute(k){delete this.attrs[k]},
    getAttribute(k){return this.attrs[k] ?? null}, setAttribute(k,v){this.attrs[k]=String(v)}
  };
}
const doc = {documentElement:element(), querySelectorAll(){return []}};
const sandbox = {document:doc, navigator:{language:'pt-BR'},
  CustomEvent:class {constructor(type, init){this.type=type;this.detail=init?.detail}},
  Node:{TEXT_NODE:3}, console,
  __EPI_PREFS__:{ler(){return {idioma:'fr-FR'}}, definir(value){writes.push(value)}},
  fetch:async(url)=>{
    const locale=decodeURIComponent(url.split('/').pop());
    if (pending[locale]) return pending[locale];
    return {ok:true,json:async()=>({ok:true,locale,fallback:false,translations:dictionaries[locale]})};
  }, dispatchEvent(e){events.push(e)},
};
sandbox.window=sandbox; sandbox.globalThis=sandbox;
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);
const api=sandbox.EpiI18n;
const response=(locale, translations=dictionaries[locale], fallback=false)=>({ok:true,json:async()=>({locale,translations,fallback})});
(async()=>{
''' + scenario + '\n})().catch(error=>{console.error(error);process.exitCode=1});'
    subprocess.run([node, '-e', script, str(ROOT / 'static/i18n.js')], check=True,
                   capture_output=True, text=True, timeout=20)


def test_last_language_request_wins_without_persisting_stale_response():
    run_scenario('''
await api.setLang('pt-BR', {persist:false});
let complete;
pending['en-GB']=new Promise(resolve=>{complete=resolve});
const first=api.setLang('en-GB');
await Promise.resolve();
await api.setLang('fr-FR');
complete(response('en-GB'));
await first;
assert.equal(api.lang,'fr-FR');
assert.equal(sandbox.t('label'),'Français');
assert.equal(doc.documentElement.lang,'fr-fr');
assert.equal(writes.length,1); assert.equal(writes[0].idioma,'fr-FR');
''')


def test_failed_or_wrong_locale_keeps_effective_language_and_preference():
    run_scenario('''
await api.setLang('en-GB');
pending['fr-FR']=Promise.resolve(response('pt-BR', dictionaries['pt-BR'], true));
assert.equal(await api.setLang('fr-FR'),'en-GB');
assert.equal(sandbox.t('label'),'English');
assert.equal(writes.length,1);
assert.equal(api.loadError.requested,'fr-FR');
assert.equal(api.loadError.effective,'en-GB');
assert.equal(events.filter(e=>e.type==='epi:localeerror').length,1);
assert.equal(api.getStoredLang(),'fr-FR');
''')


def test_live_bindings_refresh_state_and_translated_parameters_keep_user_content():
    run_scenario('''
await api.setLang('en-GB');
const node=element({'data-i18n':'label'});
node.textContent=api.textFor(node,'greeting','Olá, {name}',{name:'Salvar <b>Ana</b>'});
assert.equal(node.textContent,'Hello, Salvar <b>Ana</b>');
await api.setLang('fr-FR'); api.translateDOM(node);
assert.equal(node.textContent,'Bonjour, Salvar <b>Ana</b>');
node.textContent=api.textFor(node,'summary','Configuração {note}',{note:'Existing'},{note:'note'});
api.translateDOM(node); assert.equal(node.textContent,'Configuration Existant');
await api.setLang('en-GB'); api.translateDOM(node);
assert.equal(node.textContent,'Configuration Existing');
const markup=api.bindText('greeting',{name:'<img src=x onerror="alert(1)">'},'');
assert(!markup.includes('<img')); assert(markup.includes('&lt;img'));
assert.equal(sandbox.trEpi('missing','Value: {name}',{name:'Ana'}),'Value: Ana');
const html=element({'data-i18n-html':'greeting','data-i18n-vars':JSON.stringify({name:'<script>bad</script>'})});
api.translateDOM(html); assert.equal(html.innerHTML,'Hello, &lt;script&gt;bad&lt;/script&gt;');
''')


def test_reused_feedback_does_not_restore_old_success_over_error_or_empty_state():
    run_scenario('''
await api.setLang('en-GB');
for (const current of ['', 'API: supplier unavailable']) {
 const feedback=element();
 feedback.textContent=api.textFor(feedback,'action','Salvar');
 feedback.textContent=current;
 await api.setLang('fr-FR'); api.translateDOM(feedback);
 assert.equal(feedback.textContent,current);
 assert.equal(feedback.hasAttribute('data-i18n'),false);
 await api.setLang('en-GB');
}
''')


def test_plural_rules_and_number_formatting_preserve_values():
    run_scenario('''
dictionaries['en-GB'].items={one:'{count} item',other:'{count} items'};
dictionaries['fr-FR'].items={one:'{count} article',other:'{count} articles'};
await api.setLang('en-GB');
assert.equal(sandbox.t('items',{count:1}),'1 item');
assert.equal(sandbox.t('items',{count:2}),'2 items');
assert.equal(sandbox.t('items',{count:0}),'0 items');
await api.setLang('fr-FR');
assert.equal(sandbox.t('items',{count:0}),'0 article');
assert.equal(sandbox.t('items',{count:2}),'2 articles');
''')


def test_purchase_translation_does_not_change_matching_or_signed_row_data():
    run_scenario('''
const path=require('node:path'), staticRoot=path.dirname(process.argv[1]);
vm.runInNewContext(fs.readFileSync(path.join(staticRoot,'js/modules/purchases/business/purchase-import-matching.js'),'utf8'), sandbox);
vm.runInNewContext(fs.readFileSync(path.join(staticRoot,'js/modules/purchases/ui/import-review-labels.js'),'utf8'), sandbox);
const rows=[{epi:'Helmet',ca:'123',qtd:'1',valor_unitario:'1.234,56',quote_sig:'opaque-signed-data'}, {epi:'Gloves',ca:'999'}];
const items=[{id:7,epi_name:'Helmet',ca:'123'}, {id:9,epi_name:'Gloves',ca:'777'}];
const baseline=sandbox.evaluatePurchaseImportCandidates(rows,items);
const identity=value=>JSON.stringify(value.map(r=>({row:r.row,suggested:r.suggestedItemId,candidates:r.candidates.map(c=>({id:c.itemId,eligible:c.eligible,blocked:c.blocked,strong:c.strong,matches:c.matches}))})));
const before=JSON.stringify(rows);
for(const locale of ['pt-BR','en-GB','es-ES','fr-FR','nb-NO']){
 dictionaries[locale]=JSON.parse(fs.readFileSync(path.join(staticRoot,'i18n',locale+'.json'),'utf8'));
 await api.setLang(locale);
 const translated=sandbox.evaluatePurchaseImportCandidates(rows,items,sandbox.trEpi);
 assert.equal(identity(translated),identity(baseline));
 assert.equal(JSON.stringify(rows),before);
 const blocked=translated[1].candidates.find(c=>c.itemId===9);
 assert(blocked.blockReason.includes('999')); assert(blocked.blockReason.includes('777'));
 if(locale!=='pt-BR') assert(!blocked.blockReason.includes('divergente'));
 const error=sandbox.validatePurchaseImportDecisions(translated,['','ignore'],sandbox.trEpi)[0];
 assert(!error.includes('purchase.importReview.'));
 if(locale!=='pt-BR') assert(!error.includes('escolha o item'));
 assert.equal(baseline[0].candidates[0].matches.includes('descrição'),true);
 const labels=sandbox.__EPI_PURCHASE_IMPORT_LABELS__.matches(baseline[0].candidates[0].matches);
 if(locale==='en-GB') assert(labels.includes('description'));
}
''')


def test_pending_language_from_previous_identity_cannot_change_new_session():
    run_scenario('''
let owner='A'; sandbox.__EPI_PREFS__.identidade=()=>owner;
await api.setLang('pt-BR',{persist:false});
let complete;
pending['en-GB']=new Promise(resolve=>{complete=resolve});
const request=api.setLang('en-GB'); await Promise.resolve();
owner='B';
complete(response('en-GB')); await request;
assert.equal(api.lang,'pt-BR');
assert.equal(writes.length,0);
assert.equal(sandbox.t('label'),'Português');
''')


def test_late_tenant_initialisation_does_not_override_user_choice():
    run_scenario('''
let complete;
pending['en-GB']=new Promise(resolve=>{complete=resolve});
const chosen=api.setLang('en-GB');
await api.setLang('pt-BR',{persist:false,initial:true});
complete(response('en-GB'));await chosen;
assert.equal(api.lang,'en-GB');
assert.equal(writes.length,1);assert.equal(writes[0].idioma,'en-GB');
''')
