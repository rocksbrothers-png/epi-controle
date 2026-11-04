"""Independent runtime supplier-portal CSP/SRI audit; synthetic intercepted APIs only.

Reads product files without editing them. Run with --root REPO --output DIR.
The runtime HTML/header are imported ONCE before adversarial response tampering.
"""
import argparse
import base64
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

LOCALES = ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO']
EXPECTED_SCRIPTS = ['/i18n.js', '/js/modules/purchases/integrations/supplier-portal-api.js', '/js/views/supplier-portal.js']
ORIGIN = 'http://127.0.0.1:42831'

class Scripts(HTMLParser):
    def __init__(self):
        super().__init__(); self.tags=[]
    def handle_starttag(self, tag, attrs):
        if tag == 'script': self.tags.append(dict(attrs))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--browser',default=os.environ.get('CHROMIUM_EXECUTABLE'))
    args=p.parse_args();root=args.root.resolve();output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    spec=importlib.util.spec_from_file_location('audit_runtime_supplier_portal',root/'modules/purchases/supplier_portal_page.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    html,policy=module.PORTAL_PAGE_HTML,module.PORTAL_PAGE_CSP
    parsed=Scripts();parsed.feed(html);tags=parsed.tags
    sources={path:(root/'static'/path.lstrip('/')).read_bytes() for path in EXPECTED_SCRIPTS}
    script_sources=next(x.strip().split()[1:] for x in policy.split(';') if x.strip().startswith('script-src '))
    independently_hashed=['sha256-'+base64.b64encode(hashlib.sha256(sources[path]).digest()).decode() for path in EXPECTED_SCRIPTS]
    checks={'exact_three_paths_in_order':[urlsplit(t.get('src','')).path for t in tags]==EXPECTED_SCRIPTS,
            'sri_matches_independent_asset_bytes':[t.get('integrity') for t in tags]==independently_hashed,
            'policy_exact_asset_hashes':script_sources==["'"+h+"'" for h in independently_hashed],
            'policy_has_no_self_inline_eval':not any(x in script_sources for x in ["'self'","'unsafe-inline'","'unsafe-eval'","'strict-dynamic'"]),
            'no_inline_scripts':len(tags)==3 and all(t.get('src') for t in tags)}
    assert all(checks.values()), checks
    # No further module imports or policy/hash recalculation occur below.
    cases=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=args.browser,headless=True)
        for locale in LOCALES:
            for mode in ['legitimate','extra_same_origin','approved_without_integrity','modified_approved_bytes']:
                page=browser.new_page(viewport={'width':390,'height':844});calls=[];js_errors=[];console_errors=[];tampered=[]
                page.on('pageerror',lambda exc:js_errors.append(str(exc)))
                page.on('console',lambda msg:console_errors.append(msg.text) if msg.type=='error' else None)
                page.add_init_script("""globalThis.__auditCsp=[];globalThis.__auditScriptErrors=[];
                  document.addEventListener('securitypolicyviolation',e=>__auditCsp.push({directive:e.effectiveDirective,blocked:e.blockedURI}));
                  addEventListener('error',e=>{if(e.target?.tagName==='SCRIPT')__auditScriptErrors.push(e.target.src)},true);""")
                served_html=html
                if mode=='approved_without_integrity':served_html=html.replace(' integrity="'+tags[0]['integrity']+'"','',1)
                def intercept(route):
                    request=route.request;url=urlsplit(request.url);path=url.path
                    calls.append({'method':request.method,'path':path})
                    assert url.netloc==urlsplit(ORIGIN).netloc, 'External request attempted'
                    assert request.method=='GET','Unexpected API write'
                    if path.startswith('/fornecedor/'):
                        route.fulfill(content_type='text/html',body=served_html,headers={'Content-Security-Policy':policy});return
                    if path.startswith('/api/i18n/'):
                        lang=path.rsplit('/',1)[1];route.fulfill(json={'locale':lang,'fallback':False,'translations':json.loads((root/'static/i18n'/f'{lang}.json').read_text())});return
                    if path=='/api/portal/supplier/audit-synthetic':
                        route.fulfill(json={'item':{'entity_type':'quote','company_name':'Audit Company','supplier_name':'Audit Supplier','quote':{'id':71,'status':'sent','items':[{'quote_item_id':91,'epi_name':'Audit PPE literal <img>','ca':'12345','quantity_requested':2,'unit_measure':'par','unit_price':None,'lead_time_days':None,'declined':False}],'freight_value':0,'payment_terms':'Original terms','notes':'Original notes'}}});return
                    if path in sources:
                        body=sources[path]
                        if mode=='modified_approved_bytes' and path=='/i18n.js':
                            body=b'globalThis.__auditTamperedExecuted=1;\n'+body;tampered.append(path)
                        route.fulfill(content_type='application/javascript',body=body);return
                    if path=='/audit-unapproved.js':route.fulfill(content_type='application/javascript',body='globalThis.__auditExtraExecuted=1;');return
                    raise AssertionError('Unexpected path: '+path)
                page.route('**/*',intercept)
                page.goto(ORIGIN+'/fornecedor/audit-synthetic?lang='+locale,wait_until='load')
                if mode in ['legitimate','extra_same_origin']:
                    page.wait_for_selector('#conteudo',state='visible')
                    page.wait_for_function('(lang)=>EpiI18n.lang===lang',arg=locale)
                    if mode=='extra_same_origin':
                        page.evaluate("""()=>{const script=document.createElement('script');script.src='/audit-unapproved.js';document.body.append(script)}""")
                page.wait_for_timeout(150)
                observed=page.evaluate("""()=>({csp:globalThis.__auditCsp,scriptErrors:globalThis.__auditScriptErrors,
                    i18n:typeof globalThis.EpiI18n==='object',transport:typeof globalThis.__EPI_SUPPLIER_PORTAL_API__==='object',
                    contentVisible:document.getElementById('conteudo')?.style.display==='block',
                    extraExecuted:globalThis.__auditExtraExecuted||0,tamperedExecuted:globalThis.__auditTamperedExecuted||0,
                    locale:globalThis.EpiI18n?.lang,head:document.querySelector('h1')?.textContent,
                    ppeText:document.getElementById('conteudo')?.textContent.includes('Audit PPE literal <img>')})""")
                if mode=='legitimate':
                    translated=json.loads((root/'static/i18n'/f'{locale}.json').read_text())['supplierPortal']['title']
                    ok=observed['i18n'] and observed['transport'] and observed['contentVisible'] and observed['locale']==locale and observed['head']==translated and observed['ppeText'] and not observed['csp'] and not observed['scriptErrors'] and not js_errors
                    page.screenshot(path=str(output/(locale+'.png')),full_page=True)
                elif mode=='extra_same_origin':
                    ok=not observed['extraExecuted'] and any(e['blocked']==ORIGIN+'/audit-unapproved.js' for e in observed['csp']) and not any(c['path']=='/audit-unapproved.js' for c in calls)
                elif mode=='approved_without_integrity':
                    ok=not observed['i18n'] and any(urlsplit(e['blocked']).path=='/i18n.js' for e in observed['csp']) and not any(c['path']=='/i18n.js' for c in calls)
                else:
                    integrity_error=any('integrity' in error.lower() or 'digest' in error.lower() for error in console_errors)
                    ok=not observed['i18n'] and not observed['tamperedExecuted'] and tampered==['/i18n.js'] and any(urlsplit(path).path=='/i18n.js' for path in observed['scriptErrors']) and integrity_error
                cases.append({'locale':locale,'mode':mode,'passed':bool(ok),'observed':observed,'calls':calls,'javascript_error_count':len(js_errors),'integrity_console_error':any('integrity' in s.lower() or 'digest' in s.lower() for s in console_errors),'runtime_policy_and_integrity_frozen':True})
                page.close()
        browser.close()
    report={'product':root.name,'synthetic_api_only':True,'static_checks':checks,'cases':cases,'passed':sum(c['passed'] for c in cases),'failed':sum(not c['passed'] for c in cases)}
    (output/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({'product':root.name,'passed':report['passed'],'failed':report['failed'],'failed_cases':[{'locale':c['locale'],'mode':c['mode']} for c in cases if not c['passed']]}))
    raise SystemExit(bool(report['failed']))
if __name__=='__main__':main()
