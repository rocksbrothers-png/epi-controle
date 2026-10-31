from pathlib import Path
import io, json, sys
from urllib.parse import urlparse
from PIL import Image
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

sys.path.insert(0,str(ROOT))
from modules.safety_library.preview import render_preview
buffer=io.BytesIO();Image.new('RGB',(40,40),'white').save(buffer,format='PNG')
manifest,pages=render_preview(buffer.getvalue(),'fixture.png','image/png')
manifest['warnings']=['Pré-visualização gerada: fontes e paginação podem diferir do aplicativo Office original.']
page_bytes=pages[0][2] if isinstance(pages,list) else next(iter(pages.values()))
# render_preview returns tuples (part, page, bytes), never a live tenant document.
results=[]
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path=args.browser,headless=True,args=['--no-sandbox'])
 for locale in ['pt-BR','en-GB','es-ES','fr-FR','nb-NO']:
  page=browser.new_page(viewport={'width':1280,'height':1000});errors=[];calls=[];writes=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  epi={'id':9,'name':'Aprovado <img src=x onerror=window.__xss=1>','manufacturer':'Fabricante original','model_reference':'<img src=x onerror=window.__xss=1>','ca':'123','ca_expiry':'2026-12-31','manufacturer_validity_months':12,'sector':'Proteção original','epi_section':'Seção original','has_photo':False}
  document={'id':7,'document_id':70,'title':'Documento Aprovado','version_label':'v1 original','revision':1,'category':'epi_matrix','category_label':'Matriz de Aplicação de EPIs','state':'draft','state_label':'Rascunho','effective_date':'2026-05-02','all_units':True,'unit_ids':[11],'epi_ids':[9]}
  def route(request):
   req=request.request;path=urlparse(req.url).path
   if path.startswith('/api/i18n/'):
    lang=path.rsplit('/',1)[1];request.fulfill(json={'locale':lang,'fallback':False,'translations':json.loads((ROOT/'static/i18n'/f'{lang}.json').read_text())});return
   if path.startswith('/api/'):
    action=path.rsplit('/',1)[1];body=req.post_data_json or {};calls.append({'action':action,'keys':sorted(body),'document_id':body.get('document_id'),'version_id':body.get('version_id')})
    if action not in ['options','documents','approved-epis','manifest','page']:
     writes.append(action);request.fulfill(status=403,json={'error':'Operation blocked by test fixture'});return
    if action=='options':data={'units':[{'id':11,'name':'Unidade original'}],'epis':[epi],'allow_admin_original_download':False}
    elif action=='documents':data={'items':[document],'context':{'unit_name':'Unidade original','unit_id':11}}
    elif action=='approved-epis':data={'items':[epi]}
    elif action=='manifest':data={'document':document,'preview':manifest}
    else:request.fulfill(body=page_bytes,content_type='image/png');return
    request.fulfill(json=data);return
   if path=='/':request.fulfill(content_type='text/html',body='<html><body><div id="admin" class="card"></div><div id="approved" class="card"></div><div id="library" class="card"></div></body></html>');return
   source=ROOT/'static'/path.lstrip('/')
   if source.is_file():request.fulfill(body=source.read_text(),content_type='text/css' if source.suffix=='.css' else 'application/javascript')
   else:request.fulfill(status=404)
  page.route('**/*',route);page.goto('http://127.0.0.1:41337/')
  page.add_style_tag(url='http://127.0.0.1:41337/styles.css')
  page.add_style_tag(url='http://127.0.0.1:41337/styles/safety-library.css')
  page.add_script_tag(content=(ROOT/'static/i18n.js').read_text())
  page.evaluate("window.requestApiResponse=(path,options)=>fetch(path,{...options,headers:{'Content-Type':'application/json'}})")
  page.add_script_tag(content=(ROOT/'static/js/views/safety-library.js').read_text())
  page.evaluate('(locale)=>EpiI18n.setLang(locale,{persist:false})',locale)
  page.evaluate("async()=>{await SafetyLibrary.admin(document.querySelector('#admin'));await SafetyLibrary.portal(document.querySelector('#approved'),document.querySelector('#library'),{token:'synthetic-fixture',cpfLast3:'123'});}")
  page.locator('#admin input[name=title]').fill('Título original Aprovado')
  page.locator('#admin select[name=category]').select_option('glove_matrix')
  page.locator('#admin select[name=unit_ids]').select_option('11')
  page.locator('#approved input[data-epi-filter=name]').fill('Aprovado')
  other='fr-FR' if locale!='fr-FR' else 'en-GB'
  page.evaluate('(locale)=>EpiI18n.setLang(locale,{persist:false})',other)
  assert page.locator('#admin input[name=title]').input_value()=='Título original Aprovado'
  assert page.locator('#admin select[name=category]').input_value()=='glove_matrix'
  assert page.locator('#admin select[name=unit_ids]').input_value()=='11'
  assert page.locator('#approved input[data-epi-filter=name]').input_value()=='Aprovado'
  expected=json.loads((ROOT/'static/i18n'/f'{other}.json').read_text())
  assert page.locator('#admin select[name=category] option[value=glove_matrix]').inner_text()==expected['safetyLibrary']['category']['glove_matrix']
  assert page.locator('#approved .safety-mobile h3').first.inner_text()==epi['name']
  assert not page.evaluate('window.__xss || 0')
  assert page.locator('#approved img').count()==0
  page.locator('#admin [data-preview="7"]').click()
  page.wait_for_selector('dialog img[data-page]:not([hidden])')
  assert page.locator('dialog [data-part] option').inner_text()==expected['safetyLibrary']['preview']['image']
  page.evaluate('(locale)=>EpiI18n.setLang(locale,{persist:false})',locale)
  expected=json.loads((ROOT/'static/i18n'/f'{locale}.json').read_text())
  assert page.locator('dialog [data-part] option').inner_text()==expected['safetyLibrary']['preview']['image']
  page.locator('dialog').evaluate('(dialog)=>dialog.close()')
  page.set_viewport_size({'width':390,'height':844})
  if not page.evaluate('document.documentElement.scrollWidth <= innerWidth'):
   print(page.evaluate("[...document.querySelectorAll('*')].filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>({tag:e.tagName,id:e.id,cls:e.className,width:e.getBoundingClientRect().width,overflow:getComputedStyle(e).overflowX})).slice(0,20)"))
   page.screenshot(path=str(OUT/'library-mobile-overflow.png'),full_page=True)
   raise AssertionError('Mobile overflow')
  page.screenshot(path=str(OUT/f'library-mobile-{locale}.png'),full_page=True)
  assert not writes,writes
  assert not errors,errors
  results.append({'locale':locale,'forms_preserved':True,'category_value':'glove_matrix','unit_id':11,'original_names_preserved':True,'xss_executed':False,'preview_loaded':True,'mobile_overflow':False,'page_errors':errors,'writes':writes,'read_requests':calls})
  page.close()
 browser.close()
(OUT/'library-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print('PASS',len(results),'locales; admin, portal, live labels, preview, immutable fields, escaping, mobile; no writes')

print("Evidence:",OUT)
