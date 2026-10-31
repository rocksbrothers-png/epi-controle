"""Runtime contracts for asynchronous, identity-owned language changes."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_extracted_epi_hint_keeps_name_and_unit_lock_across_five_languages():
    run_scenario(r'''
const path = require('node:path');
const staticRoot = path.dirname(process.argv[1]);
const locales = ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO'];
for (const locale of locales) dictionaries[locale] = JSON.parse(fs.readFileSync(path.join(staticRoot, 'i18n', locale + '.json'), 'utf8'));
const hint = element(), unit = {value:'', disabled:false}, active = {value:'opaque-token'};
const name = 'JV original <img src=x>';
doc.getElementById = id => ({'epi-unit':unit, 'epi-joinventure-active':active, 'epi-unit-rule-hint':hint})[id];
doc.querySelectorAll = selector => selector === '[data-i18n]' && hint.hasAttribute('data-i18n') ? [hint] : [];
sandbox.parseActiveJoinventureToken = () => ({name, unit_id:5});
sandbox.tr = sandbox.trEpi;
vm.runInNewContext(fs.readFileSync(path.join(staticRoot, 'js/modules/epis/ui/epi-registration.js'), 'utf8'), sandbox);
await api.setLang('pt-BR', {persist:false});
sandbox.applyEpiJoinventureRules();
for (const locale of locales) {
  await api.setLang(locale, {persist:false});
  assert.equal(hint.textContent, api.t('epi.lockedByJoinventureHint', {name}));
  assert.equal(hint.getAttribute('data-i18n'), 'epi.lockedByJoinventureHint');
  assert.equal(JSON.parse(hint.getAttribute('data-i18n-vars')).name, name);
  assert.equal(unit.value, '5');
  assert.equal(unit.disabled, true);
  assert.equal(active.value, 'opaque-token');
}
assert.equal(writes.length, 0);
''')


def run_scenario(scenario):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node.js unavailable')
    script = r'''
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const writes = [], events = [], pending = {}, listeners = {};
const dictionaries = {
  'pt-BR': {label:'Português', greeting:'Olá, {name}', action:'Salvar', note:'Existente', summary:'Configuração {note}'},
  'en-GB': {label:'English', greeting:'Hello, {name}', action:'Save', note:'Existing', summary:'Configuration {note}'},
  'fr-FR': {label:'Français', greeting:'Bonjour, {name}', action:'Enregistrer', note:'Existant', summary:'Configuration {note}'},
};
function element(attrs = {}) {
  return {nodeType:1, firstElementChild:null, textContent:'',
    attrs:{...attrs}, querySelectorAll(){return []},
    replaceChildren(fragment){this.innerHTML=fragment.childNodes.map(serializeNode).join('');this.textContent=fragment.textContent},
    hasAttribute(k){return Object.hasOwn(this.attrs,k)}, removeAttribute(k){delete this.attrs[k]},
    getAttribute(k){return this.attrs[k] ?? null}, setAttribute(k,v){this.attrs[k]=String(v)}
  };
}
function serializeNode(node) {
  if(node.nodeType===3) return node.textContent.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  const tag=node.nodeName.toLowerCase();
  return '<'+tag+'>'+node.childNodes.map(serializeNode).join('')+(tag==='br'?'':'</'+tag+'>');
}
function treeNode(nodeName) {
  return {nodeName,childNodes:[],appendChild(node){this.childNodes.push(node)},get textContent(){return this.childNodes.map(n=>n.textContent).join('')}};
}
const doc = {documentElement:element(), querySelectorAll(){return []},
  createDocumentFragment(){return treeNode('#document-fragment')},
  createElement(tag){return treeNode(tag.toUpperCase())},
  createTextNode(value){return {nodeType:3,textContent:String(value)}}};
const sandbox = {document:doc, navigator:{language:'pt-BR'},
  CustomEvent:class {constructor(type, init){this.type=type;this.detail=init?.detail}},
  Node:{TEXT_NODE:3}, console,
  __EPI_PREFS__:{ler(){return {idioma:'fr-FR'}}, definir(value){writes.push(value)}},
  fetch:async(url)=>{
    const locale=decodeURIComponent(url.split('/').pop());
    if (pending[locale]) return pending[locale];
    return {ok:true,json:async()=>({ok:true,locale,fallback:false,translations:dictionaries[locale]})};
  }, addEventListener(type, callback){(listeners[type] ||= []).push(callback)},
  dispatchEvent(e){events.push(e);for(const callback of listeners[e.type] || [])callback(e)},
};
sandbox.window=sandbox; sandbox.globalThis=sandbox;
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);
const api=sandbox.EpiI18n;
const response=(locale, translations=dictionaries[locale], fallback=false)=>({ok:true,json:async()=>({locale,translations,fallback})});
(async()=>{
''' + scenario + '\n})().catch(error=>{console.error(error);process.exitCode=1});'
    completed = subprocess.run([node, '-e', script, str(ROOT / 'static/i18n.js')],
                               capture_output=True, text=True, timeout=20)
    assert completed.returncode == 0, completed.stderr


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


def test_rich_translation_keeps_emphasis_and_treats_all_variable_markup_as_text():
    run_scenario(r'''
const locales=['pt-BR','en-GB','es-ES','fr-FR','nb-NO'];
for(const locale of locales) dictionaries[locale]={rich:'<strong>{name}</strong><br><em>'+locale+'</em><img src=x onerror=bad>'};
for(const locale of locales) {
  await api.setLang(locale,{persist:false});
  for(const name of ['<img src=x onerror=bad>','<strong>original</strong>','&lt;literal&gt;','{literal}', '"&\'']) {
    const node=element({'data-i18n-html':'rich','data-i18n-vars':JSON.stringify({name})});
    api.translateDOM(node);
    assert.equal(node.textContent,name+locale+'<img src=x onerror=bad>');
    assert(node.innerHTML.startsWith('<strong>'));
    assert(node.innerHTML.includes('</strong><br><em>'+locale+'</em>'));
    assert(!node.innerHTML.includes('<img'));
    assert.equal((node.innerHTML.match(/<strong>/g)||[]).length,1);
  }
}
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


def test_checkout_uses_five_catalogues_and_keeps_payment_intent_and_payload():
    run_scenario('''
const path=require('node:path'), staticRoot=path.dirname(process.argv[1]);
for(const locale of ['pt-BR','en-GB','es-ES','fr-FR','nb-NO']) {
 dictionaries[locale]=JSON.parse(fs.readFileSync(path.join(staticRoot,'i18n',locale+'.json'),'utf8'));
}
const fields={};
const field=id=>fields[id] ||= Object.assign(element(),{value:'audit@example.invalid',innerHTML:'',appendChild(){},addEventListener(){},querySelector(){return field('radio')}});
doc.getElementById=field;doc.createElement=()=>field('generated');
sandbox.URLSearchParams=URLSearchParams;sandbox.location={search:'?plan=individual&lang=pt-BR&checkout_token=synthetic-fixture'};
let source=fs.readFileSync(path.join(staticRoot,'js/pagamento.js'),'utf8');
assert(source.includes('init().catch((e) => showResult(String(e)));'));
source=source.replace('init().catch((e) => showResult(String(e)));','');
source+=`
 globalThis.checkoutProbe={seed(){plans.monthly={key:'individual',cycle:'monthly',amount:1234.56,currency:'BRL',max_users:1};options=buildOptions();selectOption('pix')},payload:basePayload,intent:()=>typeof checkoutIntentKey==='undefined'?null:checkoutIntentKey,selected:()=>selected.id};`;
vm.runInNewContext(source,sandbox);
sandbox.checkoutProbe.seed();
const original=JSON.stringify(sandbox.checkoutProbe.payload()), nonce=sandbox.checkoutProbe.intent();
for(const locale of ['pt-BR','en-GB','es-ES','fr-FR','nb-NO']) {
 await api.setLang(locale,{persist:false});
 assert.equal(sandbox.checkoutProbe.selected(),'pix');
 assert.equal(sandbox.checkoutProbe.intent(),nonce);
 assert.equal(JSON.stringify(sandbox.checkoutProbe.payload()),original);
 assert.equal(field('payBtn').textContent,dictionaries[locale].checkout.finish_payment);
 assert.equal(field('s-total').textContent,new Intl.NumberFormat(locale,{style:'currency',currency:'BRL'}).format(1234.56));
 if(locale==='en-GB') assert(!field('s-benefits').innerHTML.includes('1 users'));
}
const payload=sandbox.checkoutProbe.payload();
assert.equal(payload.plan_key,'individual');
assert.equal(payload.cycle,'monthly');
assert.equal(payload.payer_email,'audit@example.invalid');
if(nonce!==null) assert.equal(payload.idempotency_key,nonce);
else assert.equal(payload.checkout_token,'synthetic-fixture');
if(nonce!==null) assert.equal(payload.payment_method,'pix');
assert.equal(writes.length,0);
''')


def test_date_and_money_bindings_change_format_without_changing_source_values():
    run_scenario('''
dictionaries['en-GB'].record='{date}: {amount}';
dictionaries['fr-FR'].record='{date} : {amount}';
await api.setLang('en-GB');
const record={date:'2026-05-02',amount:1234.56}, original=JSON.stringify(record);
const node=element(), refs={date:{type:'date',value:record.date},amount:{type:'number',value:record.amount,options:{style:'currency',currency:'BRL'}}};
node.textContent=api.textFor(node,'record','',{...record},refs);
assert(node.textContent.includes('02/05/2026'));
await api.setLang('fr-FR');api.translateDOM(node);
assert(node.textContent.includes(new Intl.NumberFormat('fr-FR',{style:'currency',currency:'BRL'}).format(record.amount)));
assert.equal(JSON.stringify(record),original);
assert.equal(api.formatDate('2026-02-31'),'2026-02-31');
assert.equal(api.formatDate('not-a-date'),'not-a-date');
''')


def test_api_messages_preserve_specific_details_payload_and_live_field_labels():
    run_scenario(r'''
const path=require('node:path'), staticRoot=path.dirname(process.argv[1]);
for(const locale of ['pt-BR','en-GB','es-ES','fr-FR','nb-NO'])dictionaries[locale]=JSON.parse(fs.readFileSync(path.join(staticRoot,'i18n',locale+'.json'),'utf8'));
for(const locale of ['pt-BR','en-GB','es-ES','fr-FR','nb-NO']) {
 await api.setLang(locale,{persist:false});
 for(const [name,template] of Object.entries(dictionaries['pt-BR'].apiErrors.messages)) {
  const original=template.replace(/\{(\w+)\}/g,(_match,name)=>name==='key'?'title':'sample_'+name);
  const payload={error:original,code:'FORBIDDEN',validation:{field:'title',line:7,item_id:99}};
  const before=JSON.stringify(payload), localized=api.describeApiError(payload);
  assert.equal(JSON.stringify(payload),before);
  assert.equal(localized.key,'apiErrors.messages.'+name);
  assert(localized.text);assert(!localized.text.includes('apiErrors.messages.'));
  assert(!/\{\w+\}/.test(localized.text));
 }
}
await api.setLang('en-GB');
const error=api.describeApiError({error:'Campo title inválido.',validation:{code:'SOME_SPECIFIC_CODE',line:7}});
assert(error.text.includes('Title'));
const feedback=element();feedback.textContent=api.textFor(feedback,error.key,error.text,error.vars,error.refs);
await api.setLang('fr-FR');api.translateDOM(feedback);
assert(feedback.textContent.includes('Titre'));
const unknown='Specific unknown rule: PPE ABC / row 7';
assert.equal(api.apiMessage({error:unknown,code:'FORBIDDEN'}),unknown);
assert.equal(api.apiMessage({error:unknown,i18n:{key:'apiErrors.messages.__proto__.constructor.name'}}),unknown);
assert.equal(api.apiMessage({error:unknown,i18n:{key:42}}),unknown);
assert.equal(sandbox.t('constructor.name'),'constructor.name');
const alt=element({'data-i18n-alt':'login.showPassword'});api.translateDOM(alt);
assert.equal(alt.getAttribute('alt'),dictionaries['fr-FR'].login.showPassword);
''')


def test_connector_errors_translate_nested_system_causes_and_keep_external_details():
    run_scenario(r'''
const path=require('node:path'), staticRoot=path.dirname(process.argv[1]);
const locales=['pt-BR','en-GB','es-ES','fr-FR','nb-NO'];
for(const locale of locales)dictionaries[locale]=JSON.parse(fs.readFileSync(path.join(staticRoot,'i18n',locale+'.json'),'utf8'));
const source='Teste da integração falhou: Falha de comunicação com a loja em /orders/ref.v2/status: remote.original <img src=x> {literal}\nnext';
const payload={error:source,code:'CONNECTOR_FAILURE',validation:{supplier_id:41,line:7}};
const before=JSON.stringify(payload);
await api.setLang('en-GB',{persist:false});
const detail=api.describeApiError(payload);
assert.equal(detail.text,'Integration test failed: Could not communicate with the store at /orders/ref.v2/status: remote.original <img src=x> {literal}\nnext');
assert.equal(JSON.stringify(payload),before);
const node=element();node.textContent=api.textFor(node,detail.key,detail.text,detail.vars,detail.refs);
for(const locale of locales){
 await api.setLang(locale,{persist:false});api.translateDOM(node);
 assert.equal(node.textContent,api.apiMessage(payload));
 assert(node.textContent.endsWith('remote.original <img src=x> {literal}\nnext'));
 const dotted=api.describeApiError({error:'Loja respondeu HTTP 429 em /orders/ref.v2/status.'});
 assert.equal(dotted.vars.path,'/orders/ref.v2/status');
 assert(!dotted.text.includes('{path}'));
 const unknownConnector=api.describeApiError({error:"Conector desconhecido: 'vendor.v2'."});
 assert.equal(unknownConnector.vars.connector,"'vendor.v2'");
 const ambiguous='/orders/REF: v2/status: remote: original <img src=x>';
 const network=api.describeApiError({error:'Falha de comunicação com a loja em '+ambiguous});
 assert.equal(network.vars.detail,ambiguous);
 assert(network.text.endsWith(ambiguous));
}
for(const source of ['Remote: Teste da integração falhou: Integração exige base_url HTTPS.',
                    'Remote message Loja respondeu HTTP 400 em /catalog.', 'name.original']){
 assert.equal(api.apiMessage({error:source}),source);
}
await api.setLang('en-GB',{persist:false});
const opaque='Remote: Integração exige base_url HTTPS. <img src=x>';
assert.equal(api.apiMessage({error:'Teste da integração falhou: '+opaque}),'Integration test failed: '+opaque);
assert.equal(api.apiMessage({error:'Falha de comunicação com a loja em /catalog: Integração exige base_url HTTPS.'}),
             'Could not communicate with the store at /catalog: Integração exige base_url HTTPS.');
// A known failure followed by an opaque one must not regain its old binding.
node.textContent='unknown remote detail';await api.setLang('fr-FR',{persist:false});api.translateDOM(node);
assert.equal(node.textContent,'unknown remote detail');assert.equal(node.hasAttribute('data-i18n'),false);
assert.equal(writes.length,0);
''')


def test_connector_cause_recursion_is_bounded_and_live_bindings_agree():
    run_scenario(r'''
const path=require('node:path'), staticRoot=path.dirname(process.argv[1]);
const locales=['pt-BR','en-GB','es-ES','fr-FR','nb-NO'];
for(const locale of locales)dictionaries[locale]=JSON.parse(fs.readFileSync(path.join(staticRoot,'i18n',locale+'.json'),'utf8'));
for(const locale of locales)dictionaries[locale].apiErrors.messages.connectorRepeatedProbe='Repeated {name}; {name}.';
await api.setLang('en-GB',{persist:false});
assert.equal(api.describeApiError('Repeated vendor.v2; vendor.v2.').vars.name,'vendor.v2');
assert.equal(api.describeApiError('Repeated vendor.v2; another.').key,null);
for(const depth of [0,1,4,5,20]){
 const original='Teste da integração falhou: '.repeat(depth)+'Integração exige base_url HTTPS.';
 await api.setLang('en-GB',{persist:false});
 const detail=api.describeApiError({error:original}), node=element();
 assert(detail.key);
 node.textContent=api.textFor(node,detail.key,detail.text,detail.vars,detail.refs);
 for(const locale of locales){
  await api.setLang(locale,{persist:false});api.translateDOM(node);
  assert.equal(node.textContent,api.apiMessage({error:original}));
  assert(node.textContent.includes('base_url'));
 }
}
for(const length of [8192,8193]){
 const prefix='Teste da integração falhou: ', original=prefix+'x'.repeat(length-prefix.length);
 const detail=api.describeApiError({error:original});
 if(length===8193)assert.equal(detail.text,original);
 else assert(detail.text.endsWith('x'.repeat(length-prefix.length)));
}
''')


def test_real_http_connector_exceptions_reach_all_five_operation_translations(monkeypatch):
    import io
    import json
    import urllib.error

    from epi_backend.supplier_connectors import ConnectorError, get_connector
    from epi_backend.supplier_connectors.http_json import HttpJsonConnector

    connector = HttpJsonConnector({'base_url': 'https://fixture.invalid'})
    cases = []

    def capture(call, key):
        with pytest.raises((ConnectorError, ValueError)) as failure:
            call()
        cases.append({'source': str(failure.value), 'key': 'apiErrors.messages.' + key})

    capture(lambda: HttpJsonConnector({'base_url': 'http://fixture.invalid'})._base_url(), 'connectorHttpsRequired')
    capture(lambda: get_connector('vendor.v2', {}), 'connectorUnknown')
    capture(lambda: connector.get_order_status(''), 'connectorOrderReferenceRequired')
    with monkeypatch.context() as patch:
        patch.setattr(connector, '_request', lambda *args: {})
        capture(connector.get_catalog, 'connectorCatalogItemsRequired')
        capture(lambda: connector.get_price_and_stock([]), 'connectorQuoteItemsRequired')

    def http_failure(*args, **kwargs):
        raise urllib.error.HTTPError('https://fixture.invalid/catalog', 429, 'synthetic', {}, None)

    def network_failure(*args, **kwargs):
        raise urllib.error.URLError('remote.original <img src=x>')

    for opener, key in [(http_failure, 'connectorHttpFailure'), (network_failure, 'connectorNetworkFailure'),
                        (lambda *args, **kwargs: io.BytesIO(b'not-json'), 'connectorInvalidJson')]:
        with monkeypatch.context() as patch:
            patch.setattr('urllib.request.urlopen', opener)
            capture(lambda: connector._request('GET', '/orders/ref.v2/status'), key)

    run_scenario('const cases=' + json.dumps(cases) + r''';
const path=require('node:path'), staticRoot=path.dirname(process.argv[1]);
const locales=['pt-BR','en-GB','es-ES','fr-FR','nb-NO'];
for(const locale of locales)dictionaries[locale]=JSON.parse(fs.readFileSync(path.join(staticRoot,'i18n',locale+'.json'),'utf8'));
const operations={connectorTestFailed:'Teste da integração falhou: ',
 connectorCatalogQueryFailed:'Falha ao consultar o catálogo da loja: ',
 connectorQuoteFailed:'Falha ao cotar na loja: ',
 connectorOrderCreationFailed:'Falha ao criar o pedido na loja: ',
 connectorOrderStatusFailed:'Falha ao consultar o pedido na loja: '};
for(const locale of locales){
 await api.setLang(locale,{persist:false});
 for(const example of cases){
  const inner=api.describeApiError({error:example.source});
  assert.equal(inner.key,example.key);
  if(locale==='pt-BR')assert.equal(inner.text,example.source);
  else assert.notEqual(inner.text,example.source);
  for(const [key,prefix] of Object.entries(operations)){
   const payload={error:prefix+example.source,code:'CONNECTOR_FAILURE',validation:{supplier_id:41,line:7}};
   const before=JSON.stringify(payload), detail=api.describeApiError(payload);
   assert.equal(JSON.stringify(payload),before);
   assert.equal(detail.key,'apiErrors.wrappers.'+key);
   assert.equal(detail.refs.cause.key,example.key);
   assert.equal(detail.text,api.t(detail.key,{cause:inner.text}));
  }
 }
}
''')


def test_api_client_keeps_error_contract_and_gateway_fallback():
    run_scenario('''
const path=require('node:path'), staticRoot=path.dirname(process.argv[1]);
for(const locale of ['pt-BR','en-GB','es-ES','fr-FR','nb-NO'])dictionaries[locale]=JSON.parse(fs.readFileSync(path.join(staticRoot,'i18n',locale+'.json'),'utf8'));
sandbox.__EPI_APP_STATE__={token:'synthetic-session'};
vm.runInNewContext(fs.readFileSync(path.join(staticRoot,'js/modules/api-client.js'),'utf8'),sandbox);
const client=sandbox.__EPI_API_CLIENT__;
for(const locale of ['pt-BR','en-GB','es-ES','fr-FR','nb-NO']) {
 await api.setLang(locale,{persist:false});
 const headers=client.buildApiHeaders();
 assert.equal(headers.Authorization,'Bearer synthetic-session');
 assert.equal(headers['Accept-Language'],locale);
 const payload={error:'Campo title inválido.',validation:{code:'INVALID_FIELD',line:7,item_id:99}},before=JSON.stringify(payload);
 let actual;
 try{client.throwIfApiRequestFailed('/api/library',{ok:false,status:422},payload)}catch(error){actual=error}
 assert(actual);assert.equal(actual.message,api.apiMessage(payload));
 assert.equal(actual.payload,payload);assert.equal(JSON.stringify(payload),before);
 assert.equal(actual.status,422);assert.equal(actual.code,'INVALID_FIELD');assert(actual.i18n);
 const gateway={error:{code:'UPSTREAM_FAILURE',message:'<html>private gateway diagnostic</html>'}};
 try{client.throwIfApiRequestFailed('/api/library',{ok:false,status:503},gateway)}catch(error){actual=error}
 assert.equal(actual.message,api.apiMessage({error:'Servidor temporariamente indisponível. Tente novamente em instantes.',code:'UPSTREAM_FAILURE'}));
 assert(!actual.message.includes('private gateway diagnostic'));
 assert.equal(actual.payload,gateway);assert.equal(actual.status,503);
 assert.equal(actual.code,'UPSTREAM_FAILURE');assert.equal(actual.nonFatal,true);
 const unknown={error:'Uncatalogued specific rejection: row 7, PPE 99',code:'FORBIDDEN'};
 try{client.throwIfApiRequestFailed('/api/library',{ok:false,status:403},unknown)}catch(error){actual=error}
 assert.equal(actual.message,unknown.error);assert.equal(actual.payload,unknown);
}
assert.equal(writes.length,0);
''')


def test_accessible_attribute_bindings_follow_state_and_preserve_text_parameters():
    run_scenario('''
dictionaries['en-GB'].show='Show password';dictionaries['en-GB'].hide='Hide password';
dictionaries['fr-FR'].show='Afficher le mot de passe';dictionaries['fr-FR'].hide='Masquer le mot de passe';
await api.setLang('en-GB');
const button=element({'data-i18n-aria-label':'show'});
button.textContent=api.textFor(button,'greeting','',{name:'Ana'});
api.translateDOM(button);
button.setAttribute('aria-label',api.attributeFor(button,'aria-label','hide',''));
await api.setLang('fr-FR');api.translateDOM(button);
assert.equal(button.getAttribute('aria-label'),'Masquer le mot de passe');
assert.equal(button.textContent,'Bonjour, Ana');
button.setAttribute('aria-label','User-provided original label');
await api.setLang('en-GB');api.translateDOM(button);
assert.equal(button.getAttribute('aria-label'),'User-provided original label');
assert.equal(button.hasAttribute('data-i18n-aria-label'),false);
''')


def test_static_parent_labels_ignore_child_control_translations_and_keep_brand_data():
    run_scenario('''
await api.setLang('en-GB');
const label=element({'data-i18n':'action'}), text={nodeType:3,textContent:'Salvar'}, child={nodeType:1,textContent:'Opção'};
label.firstElementChild=child;label.childNodes=[text,child];
Object.defineProperty(label,'textContent',{get(){return text.textContent+child.textContent}});
api.translateDOM(label);assert.equal(text.textContent,' Save');
child.textContent='Translated option';
await api.setLang('fr-FR');api.translateDOM(label);
assert.equal(text.textContent,' Enregistrer');
assert.equal(label.getAttribute('data-i18n'),'action');
assert.equal(child.textContent,'Translated option');
const company=element({'data-i18n':'label'});api.translateDOM(company);
company.textContent='ACME original';
await api.setLang('en-GB');api.translateDOM(company);
assert.equal(company.textContent,'ACME original');assert.equal(company.hasAttribute('data-i18n'),false);
api.textFor(company,'label','');api.clearBinding(company);company.textContent='English';
await api.setLang('fr-FR');api.translateDOM(company);assert.equal(company.textContent,'English');
''')


def test_actual_login_toggle_retains_password_and_translates_both_states():
    run_scenario(r'''
const path=require('node:path'), staticRoot=path.dirname(process.argv[1]);
for(const locale of ['pt-BR','en-GB','es-ES','fr-FR','nb-NO'])dictionaries[locale]=JSON.parse(fs.readFileSync(path.join(staticRoot,'i18n',locale+'.json'),'utf8'));
const app=fs.readFileSync(path.join(staticRoot,'app.js'),'utf8');
const start=app.indexOf('function setLoginPasswordVisibility(isVisible) {');
assert(start>=0);
const end=app.indexOf('\n}\n',start);
assert(end>start);
sandbox.refs={loginPassword:{type:'password',value:'unchanged-password'},loginPasswordToggle:element()};
sandbox.tr=(key,fallback,vars)=>sandbox.trEpi(key,fallback,vars);
vm.runInNewContext(app.slice(start,end+2),sandbox);
for(const locale of ['pt-BR','en-GB','es-ES','fr-FR','nb-NO']) {
 await api.setLang(locale,{persist:false});
 for(const visible of [true,false]) {
  sandbox.setLoginPasswordVisibility(visible);
  const button=sandbox.refs.loginPasswordToggle;
  assert.equal(button.getAttribute('aria-pressed'),String(visible));
  assert.equal(sandbox.refs.loginPassword.type,visible?'text':'password');
  assert.equal(button.getAttribute('aria-label'),dictionaries[locale].login[visible?'hidePassword':'showPassword']);
  assert.equal(sandbox.refs.loginPassword.value,'unchanged-password');
 }
}
assert.equal(writes.length,0);
''')


def test_formatted_plural_counts_keep_numeric_operand_and_nested_message_on_switch():
    run_scenario('''
dictionaries['en-GB'].pieces={one:'{count} physical item',other:'{count} physical items'};
dictionaries['fr-FR'].pieces={one:'{count} pièce physique',other:'{count} pièces physiques'};
dictionaries['en-GB'].days={one:'{count} day',other:'{count} days'};
dictionaries['fr-FR'].days={one:'{count} jour',other:'{count} jours'};
dictionaries['en-GB'].expiry='Expires in {daysLabel}';
dictionaries['fr-FR'].expiry='Expire dans {daysLabel}';
const pieces=element(),expiry=element();
const count=1234,numberRef={type:'number',value:count},nested={daysLabel:{type:'message',key:'days',vars:{count:3},refs:{count:{type:'number',value:3}}}};
await api.setLang('en-GB',{persist:false});
pieces.textContent=api.textFor(pieces,'pieces','',{count},{count:numberRef});
expiry.textContent=api.textFor(expiry,'expiry','',{daysLabel:'fallback'},nested);
assert.equal(pieces.textContent,'1,234 physical items');
assert.equal(expiry.textContent,'Expires in 3 days');
await api.setLang('fr-FR',{persist:false});api.translateDOM(pieces);api.translateDOM(expiry);
assert.equal(pieces.textContent,new Intl.NumberFormat('fr-FR').format(count)+' pièces physiques');
assert.equal(expiry.textContent,'Expire dans 3 jours');
await api.setLang('en-GB',{persist:false});api.translateDOM(pieces);api.translateDOM(expiry);
assert.equal(pieces.textContent,'1,234 physical items');
assert.equal(expiry.textContent,'Expires in 3 days');
for(const value of [0,1,2]) {
 pieces.textContent=api.textFor(pieces,'pieces','',{count:value},{count:{type:'number',value}});
 assert.equal(pieces.textContent,value+' physical '+(value===1?'item':'items'));
}
assert.equal(count,1234);assert.equal(writes.length,0);
''')


def test_procurement_error_port_preserves_auth_payload_details_and_live_feedback():
    run_scenario(r'''
const path=require('node:path'), staticRoot=path.dirname(process.argv[1]);
for(const locale of ['pt-BR','en-GB','es-ES','fr-FR','nb-NO'])dictionaries[locale]=JSON.parse(fs.readFileSync(path.join(staticRoot,'i18n',locale+'.json'),'utf8'));
doc.readyState='complete';doc.getElementById=()=>null;
sandbox.authHeaders=()=>({Authorization:'Bearer synthetic-session'});
let source=fs.readFileSync(path.join(staticRoot,'js/views/procurement.js'),'utf8');
const end=source.lastIndexOf('})();');assert(end>=0);
source=source.slice(0,end)+'globalThis.procurementProbe={api,errorText,errorMarkup};'+source.slice(end);
vm.runInNewContext(source,sandbox);
const originalFetch=sandbox.fetch, requests=[];
let payload={error:'Item "Original <img src=x>": informe preço unitário ou marque como recusado.',validation:{code:'INVALID_QUOTE_ITEM',line:7,item_id:33}};
sandbox.fetch=async(url,options)=>{
 if(url.startsWith('/api/i18n/'))return originalFetch(url,options);
 requests.push({url,options});return {ok:false,status:422,json:async()=>payload};
};
const body=JSON.stringify({actor_user_id:23,items:[{quote_item_id:33,unit_price:1234.56,declined:false}]});
let error;
for(const locale of ['pt-BR','en-GB','es-ES','fr-FR','nb-NO']) {
 await api.setLang(locale,{persist:false});
 try{await sandbox.procurementProbe.api('/api/quotes/7/answer',{method:'POST',body})}catch(actual){error=actual}
 assert(error.i18n);assert.equal(error.status,422);assert.equal(error.code,'INVALID_QUOTE_ITEM');
 assert.equal(error.payload,payload);assert.equal(error.message,api.apiMessage(payload));
 const request=requests.at(-1);
 assert.equal(request.options.headers.Authorization,'Bearer synthetic-session');
 assert.equal(request.options.headers['Accept-Language'],locale);
 assert.equal(request.options.body,body);assert.equal(request.options.method,'POST');
 const markup=sandbox.procurementProbe.errorMarkup(error,()=>{throw Error('specific error discarded')});
 assert(!markup.includes('<img'));assert(markup.includes('&lt;img'));
}
const feedback=element();feedback.textContent=sandbox.procurementProbe.errorText(feedback,error,()=>{throw Error('specific error discarded')});
await api.setLang('fr-FR',{persist:false});api.translateDOM(feedback);
assert.equal(feedback.textContent,api.apiMessage(payload));
let toast;
doc.body={appendChild(node){toast=node}};doc.createElement=()=>Object.assign(element(),{style:{}});sandbox.setTimeout=()=>0;
vm.runInNewContext(fs.readFileSync(path.join(staticRoot,'js/views/ui-helpers.js'),'utf8'),sandbox);
sandbox.showToast(error,'error');
await api.setLang('en-GB',{persist:false});api.translateDOM(toast);
assert.equal(toast.textContent,api.apiMessage(payload));assert.equal(toast.getAttribute('role'),'alert');
const unknown=new Error('Specific uncatalogued failure / row 7');
feedback.textContent=sandbox.procurementProbe.errorText(feedback,unknown,()=>{throw Error('specific error discarded')});
await api.setLang('fr-FR',{persist:false});api.translateDOM(feedback);
assert.equal(feedback.textContent,unknown.message);assert(!feedback.hasAttribute('data-i18n'));
assert.equal(writes.length,0);
''')
