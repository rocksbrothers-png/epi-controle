import json,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(sys.argv[1]);out=Path(sys.argv[2]);results=[]
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
 page=browser.new_page();calls=[]
 def route(r):
  from urllib.parse import urlsplit
  p=urlsplit(r.request.url).path;calls.append({'path':p,'method':r.request.method})
  if p.startswith('/api/i18n/'):
   locale=p.rsplit('/',1)[1];r.fulfill(json={'locale':locale,'translations':json.loads((root/'static/i18n'/f'{locale}.json').read_text())})
  elif p=='/':r.fulfill(content_type='text/html',body='<html><body></body></html>')
  else:raise AssertionError(p)
 page.route('**/*',route);page.goto('http://127.0.0.1:42379/');page.add_script_tag(content=(root/'static/i18n.js').read_text())
 result=page.evaluate('''async()=>{
 const locales=['pt-BR','en-GB','es-ES','fr-FR','nb-NO'];const checks=[];
 for(const locale of locales){
  await EpiI18n.setLang(locale,{persist:false});
  const cause='Loja respondeu HTTP 429 em /orders/ref.with.dot/status.';
  const payload={error:'Falha ao criar o pedido na loja: '+cause,validation:{supplier_id:23,line:4}},snapshot=JSON.stringify(payload);
  const d=EpiI18n.describeApiError(payload),node=document.createElement('div');document.body.append(node);node.textContent=EpiI18n.textFor(node,d.key,d.text,d.vars,d.refs);
  const base=d.refs.cause;checks.push({locale,name:'known_cause_refs_path_payload',passed:base.vars.path==='/orders/ref.with.dot/status'&&base.vars.status==='429'&&snapshot===JSON.stringify(payload)});
  for(const next of locales){await EpiI18n.setLang(next,{persist:false});checks.push({locale,next,name:'live_nested_binding',passed:node.textContent===EpiI18n.apiMessage(payload)})}
  node.remove();await EpiI18n.setLang(locale,{persist:false});
  const opaque='Remote <img src=x onerror=globalThis.__xss=1> {cause}: Integração exige base_url HTTPS.';
  const n=EpiI18n.describeApiError({error:'Teste da integração falhou: '+opaque});checks.push({locale,name:'unknown_cause_opaque',passed:n.vars.cause===opaque&&!n.refs.cause&&n.text.endsWith(opaque)});
  const raw=EpiI18n.describeApiError({error:'Falha de comunicação com a loja em /catalog: Integração exige base_url HTTPS.'});checks.push({locale,name:'network_cause_not_recursive',passed:raw.vars.detail==='/catalog: Integração exige base_url HTTPS.'&&!raw.refs.cause&&raw.text.endsWith('/catalog: Integração exige base_url HTTPS.')});
  const special='/orders/REF: v2/status';const message='Falha de comunicação com a loja em '+special+': remote error';const detail=EpiI18n.describeApiError({error:message});checks.push({locale,name:'colon_path_parameter_preserved',passed:detail.vars.detail===special+': remote error'&&detail.text.endsWith(special+': remote error'),detail:detail.vars.detail,text:detail.text});
  const ns=['apiErrors.wrappers.__proto__.x','apiErrors.messages.constructor.name','purchase.connectors.demo'];for(const key of ns){const e=EpiI18n.describeApiError({error:'opaque exact',i18n:{key,params:{cause:'known'}}});checks.push({locale,name:'invalid_namespace_'+key,passed:e.text==='opaque exact'&&e.key===null})}
 }
 return checks;
}''')
 results.extend(result);browser.close()
report={'product':root.name,'checks':results,'passed':sum(x['passed'] for x in results),'failed':sum(not x['passed'] for x in results),'non_get_calls':[x for x in calls if x['method']!='GET']};out.write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='checks'}))
