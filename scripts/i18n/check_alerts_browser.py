from pathlib import Path
import json, subprocess, sys
from datetime import date, timedelta
from unittest.mock import patch
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
from modules.alerts.service import compute_alerts
today=date.today()
name='Aprovado <img src=x onerror=window.__xss=1>'
low=[{'stock':stock,'minimum_stock':10,'stock_status':status,'epi_name':name,'company_name':'Empresa original','unit_name':'Unidade original','unit_measure':'par','company_id':41,'unit_id':42,'epi_id':43,'size_balances':[{'glove_size':'G','size':'N/A','uniform_size':'N/A','quantity':stock}]} for stock,status in [(-2,'critical'),(0,'critical'),(4,'critical'),(10,'critical'),(11,'near_minimum')]]
physical={43:{'as_of_date':today.isoformat(),'nearest_known_expiry':(today-timedelta(days=1)).isoformat(),'warning_days':30,'unknown':2,'expiring':4}}
epis=[{'id':43,'active':1,'company_id':41,'unit_id':42,'name':name,'company_name':'Empresa original','stock':6,'unit_measure':'par','ca_expiry':(today+timedelta(days=10)).isoformat()}]
with patch('modules.alerts.service.physical_summary_map',return_value=physical):
 alerts=compute_alerts(None,{'role':'admin'},fetch_low_stock_items=lambda *_:low,actor_operational_unit_id=lambda *_:42,fetch_epis=lambda *_:epis)
original=json.dumps(alerts,ensure_ascii=False)
physical[44]={**physical[43],'nearest_known_expiry':(today+timedelta(days=3)).isoformat(),'unknown':1,'expiring':1}
epis.append({**epis[0],'id':44})
with patch('modules.alerts.service.physical_summary_map',return_value=physical):
 alerts=compute_alerts(None,{'role':'admin'},fetch_low_stock_items=lambda *_:low,actor_operational_unit_id=lambda *_:42,fetch_epis=lambda *_:epis)
original=json.dumps(alerts,ensure_ascii=False)
results=[]
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path=args.browser,headless=True,args=['--no-sandbox'])
 for before,locale in ([(True,'fr-FR')] if args.baseline else [])+[(False,l) for l in ['pt-BR','en-GB','es-ES','fr-FR','nb-NO']]:
  page=browser.new_page(viewport={'width':1280,'height':1000});errors=[];writes=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  def route(request):
   req=request.request
   if req.method!='GET':writes.append(req.method);request.abort();return
   locale=req.url.rsplit('/',1)[1]
   request.fulfill(json={'locale':locale,'fallback':False,'translations':json.loads((ROOT/'static/i18n'/f'{locale}.json').read_text())})
  page.route('**/api/i18n/*',route)
  page.route('http://127.0.0.1:41337/',lambda request:request.fulfill(content_type='text/html',body='<html></html>'))
  page.goto('http://127.0.0.1:41337/')
  page.set_content('<main class="card"><h2 data-i18n="dashboard.alerts">Alertas</h2><div id="alerts"></div></main>')
  page.add_style_tag(content=(ROOT/'static/styles.css').read_text())
  page.add_script_tag(content=(ROOT/'static/i18n.js').read_text())
  page.evaluate('(locale)=>EpiI18n.setLang(locale,{persist:false})',locale)
  assert page.evaluate('EpiI18n.lang')==locale
  assert page.evaluate('Object.keys(EpiI18n.translations).length')>0
  page.evaluate('items=>{window.__EPI_APP_STATE__={alerts:items};window.__EPI_REFS__={alertsList:document.querySelector("#alerts")};window.currentUserHasPermission=()=>true;window.__EPI_PENDING_VALIDITY_NAVIGATION__={open:args=>window.__opened=args};window.matchesDashboardQuery=values=>!window.__query||values.some(value=>String(value).includes(window.__query));}',alerts)
  page.add_script_tag(content=(ROOT/'static/js/modules/dashboard/ui/alert-presentation.js').read_text())
  source=subprocess.check_output(['git','show',args.baseline+':static/js/views/dashboard.js'],cwd=ROOT).decode() if before else (ROOT/'static/js/views/dashboard.js').read_text()
  page.add_script_tag(content=source);page.evaluate('renderAlerts()')
  if before:
   # The baseline renderer interpolates raw record values; snapshot uses its original text only.
   page.screenshot(path=str(OUT/'alerts-before-fr-FR.png'),full_page=True)
   results.append({'before':True,'locale':locale,'titles':page.locator('.alert-item strong').all_inner_texts()});page.close();continue
  assert page.locator('.alert-item').count()==len(alerts)
  assert not page.evaluate('window.__xss||0')
  assert page.locator('.alert-item img').count()==0
  titles=page.locator('.alert-item strong').all_inner_texts()
  expected=page.evaluate('items=>items.map(item=>EpiI18n.t(item.presentation.title_key,item.presentation.params))',alerts)
  assert titles==expected,(locale,titles,expected)
  assert '{daysLabel}' not in page.locator('#alerts').inner_text()
  physical_expected=page.evaluate('(locale)=>{const cat=new Intl.PluralRules(locale).select(2);return EpiI18n.translations.operationalAlerts.physicalDescription[cat].replace("{epi}","NAME").replace("{count}","2").replace("NAME",__EPI_APP_STATE__.alerts[0].epi_name)}',locale)
  assert physical_expected in page.locator('#alerts').inner_text()

  assert name in titles[0]
  assert page.evaluate('JSON.stringify(__EPI_APP_STATE__.alerts)')==json.dumps(alerts,ensure_ascii=False,separators=(',',':'))
  page.locator('[data-pending-validity]').first.focus();page.keyboard.press('Enter')
  opened=page.evaluate('window.__opened')
  assert opened=={'company_id':'41','unit_id':'42','epi_id':'43','epi_name':name}
  page.evaluate('window.currentUserHasPermission=()=>false;renderAlerts()')
  assert page.locator('[data-pending-validity]').count()==0
  page.evaluate('window.currentUserHasPermission=()=>true;renderAlerts()')
  other='fr-FR' if locale!='fr-FR' else 'en-GB'
  page.evaluate('(locale)=>EpiI18n.setLang(locale,{persist:false})',other)
  other_expected=page.evaluate('items=>items.map(item=>EpiI18n.t(item.presentation.title_key,item.presentation.params))',alerts)
  assert page.locator('.alert-item strong').all_inner_texts()==other_expected
  assert '{daysLabel}' not in page.locator('#alerts').inner_text()
  other_physical=page.evaluate('(locale)=>{const cat=new Intl.PluralRules(locale).select(2);return EpiI18n.translations.operationalAlerts.physicalDescription[cat].replace("{epi}",__EPI_APP_STATE__.alerts[0].epi_name).replace("{count}","2")}',other)
  assert other_physical in page.locator('#alerts').inner_text()

  page.evaluate('window.__query=EpiI18n.t("operationalAlerts.size.glove",{value:"G"});renderAlerts()')
  assert page.locator('.alert-item').count()==5
  page.evaluate('window.__query="";renderAlerts()')
  page.evaluate('(locale)=>EpiI18n.setLang(locale,{persist:false})',locale)
  page.screenshot(path=str(OUT/f'alerts-after-{locale}.png'),full_page=True)
  page.set_viewport_size({'width':390,'height':844})
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  page.screenshot(path=str(OUT/f'alerts-mobile-{locale}.png'),full_page=True)
  assert not errors,errors
  assert not writes,writes
  results.append({'before':False,'locale':locale,'alerts':len(alerts),'titles':titles,'localized_size_search':True,'keyboard_action':opened,'read_permission_respected':True,'records_preserved':True,'live_switch':True,'page_errors':errors,'writes':writes,'mobile_overflow':False})
  page.close()
 browser.close()
(OUT/'alerts-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
assert json.dumps(alerts,ensure_ascii=False)==original
print('PASS: 5 locales, alert metadata, localized search, keyboard navigation, permissions, escaping, live switching and mobile')

print("Evidence:",OUT)
