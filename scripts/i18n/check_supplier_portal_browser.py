from pathlib import Path
from urllib.parse import urlparse
import ast,base64,json,runpy,subprocess
from playwright.sync_api import sync_playwright
import argparse, tempfile

parser=argparse.ArgumentParser(description='Synthetic, intercepted browser i18n checks; never uses a live API.')
parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
parser.add_argument('--output',type=Path)
parser.add_argument('--baseline',help='Optional git revision for a before screenshot')
parser.add_argument('--browser',help='Optional local Chromium executable; otherwise use Playwright Chromium')
args=parser.parse_args()
ROOT=args.root.resolve()
OUT=args.output or Path(tempfile.mkdtemp(prefix='epi-i18n-'))
OUT.mkdir(parents=True,exist_ok=True)
PORTAL=runpy.run_path(str(ROOT/'modules/purchases/supplier_portal_page.py'))

LOCALES=['pt-BR','en-GB','es-ES','fr-FR','nb-NO']
def html_from(source):
 tree=ast.parse(source)
 return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PORTAL_PAGE_HTML' for t in n.targets))
quote={'id':7,'status':'sent','items':[{'quote_item_id':33,'epi_name':'EPI Aprovado <img src=x onerror=window.__xss=1>','ca':'12345','quantity_requested':7,'unit_measure':'par','unit_price':None,'lead_time_days':None,'declined':False},{'quote_item_id':34,'epi_name':'Original B','ca':'54321','quantity_requested':1,'unit_measure':'unidade','unit_price':None,'lead_time_days':None,'declined':False}],'freight_value':12.34,'payment_terms':'Condição original','notes':'Observação original'}
order={'id':8,'po_number':'PO-ORIGINAL','items':[{'epi_name':quote['items'][0]['epi_name'],'ca':'12345','quantity':7,'unit_price':1234.56}],'expected_delivery_date':'2026-12-31','supplier_confirmation_status':'confirmed','confirmations':[{'created_at':'2026-05-02T12:30:00Z','status':'delivery_update','carrier':'Empresa original','tracking_code':'TRACK-original','comment':'Comentário original'}]}
base={'company_name':'Empresa Aprovado','supplier_name':'Fornecedor original'}
results=[]
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path=args.browser,headless=True,args=['--no-sandbox'])
 for before,locale,kind in ([(True,'fr-FR','quote')] if args.baseline else [])+[(False,l,k) for l in LOCALES for k in ['quote','order','answered','invalid']]:
  page=browser.new_page(viewport={'width':1280,'height':1000});errors=[];posts=[];reads=[];mode={'reply':'error'}
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.add_init_script("window.__portalCsp=[];document.addEventListener('securitypolicyviolation',e=>window.__portalCsp.push({directive:e.effectiveDirective,blocked:e.blockedURI}));")
  def route(request):
   req=request.request;path=urlparse(req.url).path
   if path.startswith('/api/i18n/'):
    lang=path.rsplit('/',1)[1];request.fulfill(json={'locale':lang,'fallback':False,'translations':json.loads((ROOT/'static/i18n'/f'{lang}.json').read_text())});return
   if path.startswith('/fornecedor/'):
    if before:
     source=subprocess.check_output(['git','show',args.baseline+':modules/purchases/supplier_portal_page.py'],cwd=ROOT).decode()
     request.fulfill(content_type='text/html',body=html_from(source))
    else:
     request.fulfill(content_type='text/html',body=PORTAL['PORTAL_PAGE_HTML'],headers={'Content-Security-Policy':PORTAL['PORTAL_PAGE_CSP']})
    return
   if path.startswith('/api/portal/supplier/'):
    assert path.startswith('/api/portal/supplier/synthetic-fixture')
    if req.method=='POST':
     posts.append({'path':path,'body':req.post_data_json,'language':req.headers.get('accept-language')})
     if mode['reply']=='success':request.fulfill(json={'ok':True,'status':'answered'});return
     request.fulfill(status=422,json={'error':'Item "EPI Aprovado": informe preço unitário ou marque como recusado.','validation':{'code':'INVALID_QUOTE_ITEM','line':7,'item_id':33}});return
    reads.append({'path':path,'language':req.headers.get('accept-language')})
    if kind=='invalid':request.fulfill(status=403,json={'error':'Link do portal inválido ou expirado.'});return
    payload={**base,'entity_type':'purchase_order' if kind=='order' else 'quote'}
    if kind=='order':payload['purchase_order']=order
    else:payload['quote']={**quote,'status':'answered' if kind=='answered' else 'sent'}
    request.fulfill(json={'item':payload});return
   source=ROOT/'static'/path.lstrip('/')
   if source.is_file():request.fulfill(body=source.read_text(),content_type='application/javascript' if source.suffix=='.js' else 'text/css')
   else:request.fulfill(status=404)
  page.route('**/*',route);page.goto('http://127.0.0.1:41337/fornecedor/synthetic-fixture?lang='+locale)
  if kind=='invalid':page.wait_for_selector('#painel-erro',state='visible')
  else:page.wait_for_selector('#conteudo',state='visible')
  if before:
   page.screenshot(path=str(OUT/'supplier-before-fr-FR.png'),full_page=True);results.append({'before':True,'locale':locale,'heading':page.locator('h1').inner_text()});page.close();continue
  expected=json.loads((ROOT/'static/i18n'/f'{locale}.json').read_text())
  assert page.evaluate('EpiI18n.lang')==locale
  assert page.locator('h1').inner_text()==expected['supplierPortal']['title']
  assert not page.evaluate('window.__xss||0')
  assert page.locator('img').count()==0
  assert reads[0]['language']==locale
  if kind=='invalid':
   assert page.locator('#texto-erro').inner_text()==expected['supplierPortal']['invalidLink']
   assert not posts
  elif kind=='answered':
   assert page.locator('#enviar').count()==0
   assert page.locator('#preco-0').is_disabled()
   assert page.locator('#observacoes').is_disabled()
   assert not posts
  else:
   if kind=='quote':
    page.locator('#preco-0').fill('1234.56');page.locator('#prazo-0').fill('5');page.locator('#recusa-1').check()
    page.locator('#frete').fill('12.34');page.locator('#pagamento').fill('Condição preservada');page.locator('#observacoes').fill('Observação preservada Aprovado')
    file_bytes=b'%PDF-synthetic-local-fixture'
    page.locator('#proposta').set_input_files({'name':'Aprovado original.pdf','mimeType':'application/pdf','buffer':file_bytes})
    expected_body={'items':[{'quote_item_id':33,'unit_price':1234.56,'lead_time_days':5,'declined':False},{'quote_item_id':34,'unit_price':0,'lead_time_days':0,'declined':True}],'freight_value':12.34,'payment_terms':'Condição preservada','notes':'Observação preservada Aprovado'}
    expected_body['proposal']={'file_name':'Aprovado original.pdf','file_type':'application/pdf','content_base64':'data:application/pdf;base64,'+base64.b64encode(file_bytes).decode()}
    button='#enviar'
   else:
    page.locator('#acao').select_option('delivery_update');page.locator('#previsao').fill('2026-12-31');page.locator('#transportadora').fill('Transportadora original');page.locator('#rastreio').fill('TRACK-original');page.locator('#comentario').fill('Comentário preservado')
    expected_body={'status':'delivery_update','delivery_forecast':'2026-12-31','carrier':'Transportadora original','tracking_code':'TRACK-original','comment':'Comentário preservado'};button='#registrar'
   other='fr-FR' if locale!='fr-FR' else 'en-GB'
   page.locator('#portal-language').select_option(other);page.wait_for_function('(locale)=>EpiI18n.lang===locale',arg=other)
   if kind=='quote':
    assert page.locator('#preco-0').input_value()=='1234.56';assert page.locator('#recusa-1').is_checked();assert page.locator('#observacoes').input_value()=='Observação preservada Aprovado'
    assert 'EPI Aprovado' in page.locator('#preco-0').get_attribute('aria-label')
    assert page.locator('#proposal-name').inner_text()=='Aprovado original.pdf'
    assert page.locator('#proposta').evaluate('(node)=>node.files[0].name')=='Aprovado original.pdf'
   else:
    assert page.locator('#acao').input_value()=='delivery_update';assert page.locator('#comentario').input_value()=='Comentário preservado'
   page.locator(button).click();page.wait_for_selector('#mensagem.erro');assert posts[-1]['body']==expected_body;assert posts[-1]['language']==other
   assert page.locator(button).is_enabled()
   other_error=page.locator('#mensagem').inner_text();assert 'EPI Aprovado' in other_error
   page.locator('#portal-language').select_option(locale);page.wait_for_function('(locale)=>EpiI18n.lang===locale',arg=locale)
   assert page.locator('#mensagem').inner_text()==page.evaluate("EpiI18n.apiMessage({error:'Item \"EPI Aprovado\": informe preço unitário ou marque como recusado.'})")
   page.screenshot(path=str(OUT/f'supplier-{kind}-{locale}.png'),full_page=True)
   mode['reply']='success';page.locator(button).click();page.wait_for_selector('#mensagem.ok')
   assert posts[-1]['body']==expected_body
   assert page.locator('#mensagem').inner_text()==expected['supplierPortal']['quoteSent' if kind=='quote' else 'recorded']
  page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  page.screenshot(path=str(OUT/f'supplier-mobile-{kind}-{locale}.png'),full_page=True)
  assert not errors,errors
  violations=page.evaluate('window.__portalCsp');assert not violations,violations
  results.append({'before':False,'locale':locale,'kind':kind,'forms_preserved':True,'token_context':'synthetic-fixture','canonical_payloads_preserved':True,'mobile_overflow':False,'errors':errors,'csp_violations':violations,'posts':posts,'reads':reads})
  page.close()
 browser.close()
(OUT/'supplier-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print('PASS: five locales × quote/order/answered/invalid, live form preservation, localized specific errors, success, canonical payloads, token scope and mobile; all API traffic intercepted')

print("Evidence:",OUT)
