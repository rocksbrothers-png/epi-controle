"""Independent Chromium security regression. Real SPA, synthetic intercepted API only.

python i18n_codeql_regression.py --root /path/to/repo --output /tmp/evidence
Optional --baseline-ref overlays production JS from an earlier Git commit without checkout.
"""
import argparse
import importlib.util
import hashlib
import json
import os
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer
from threading import Thread
import subprocess
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

LOCALES = ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO']
FILES = ['app.js', 'navigation-controls.js', 'entrega-epi.js', 'i18n.js', 'js/modules/auth.js']


def run(root, output, baseline=None):
    spec = importlib.util.spec_from_file_location('security_fixture', root / 'scripts/browser/fix_colab_terc.py')
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    fixture.ROOT = root
    sources = {name: subprocess.check_output(['git', '-C', str(root), 'show', f'{baseline}:static/{name}'], text=True)
               if baseline else (root / 'static' / name).read_text() for name in FILES}
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(fixture.QuietHandler, directory=str(root / 'static')))
    Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    result = dict(root=str(root), head=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'], text=True).strip(),
                  baseline_ref=baseline, synthetic_api_only=True, source_sha256={name:hashlib.sha256(source.encode()).hexdigest() for name,source in sources.items()}, cases=[])
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE'), headless=True)
            for locale in LOCALES:
                context = browser.new_context()
                page = context.new_page()
                page.set_default_timeout(20000)
                f = fixture.Fixture(page, origin, locale)
                if baseline:
                    def overlay(route):
                        path = urlsplit(route.request.url).path.lstrip('/')
                        if path in sources:
                            route.fulfill(body=sources[path], content_type='text/javascript')
                        else:
                            route.fallback()
                    page.route('**/*', overlay)
                f.open()
                start = len(f.calls)
                def case(name, js, arg=None):
                    try:
                        evidence = page.evaluate(js, arg)
                        failed = [key for key, val in evidence.items() if key.startswith('ok_') and not val]
                        result['cases'].append(dict(locale=locale, name=name, passed=not failed, failed=failed, evidence=evidence))
                    except Exception as error:
                        result['cases'].append(dict(locale=locale, name=name, passed=False, error=str(error)))
                case('interactive_tabs_text_and_token', '''()=>{
                  history.replaceState({},'',location.pathname+'?ux_interactive_app=1&ux_nav_controls=1');
                  const label='Dashboard <img data-audit-probe="tabs"> & " raw';
                  const menu=document.querySelector('.menu-link[data-view="dashboard"]');menu.textContent=label;
                  trackInteractiveViewHistory('dashboard');
                  const tabs=document.getElementById('interactive-nav-tabs');
                  const button=tabs.querySelector('[data-nav-tab-view="dashboard"]');
                  return {ok_label:button?.textContent===label,ok_inert:!tabs.querySelector('[data-audit-probe]'),ok_token:button?.dataset.navTabView==='dashboard'};
                }''')
                case('navigation_tree_and_breadcrumb', '''(source)=>{
                  const label='Navigation <img data-audit-probe="nav"> & " raw';
                  const original=globalThis.trEpi;globalThis.trEpi=()=>label;
                  document.querySelectorAll('#ux-operation-panel,#ux-settings-panel').forEach(e=>e.remove());
                  globalThis.__EPI_NAV_CONTROLS_BOUND__=false;
                  (0,eval)(source);
                  document.dispatchEvent(new CustomEvent('epi:viewchange',{detail:{view:'dashboard'}}));
                  const tree=document.getElementById('ux-operation-panel');
                  const crumb=document.getElementById('hierarchy-breadcrumb');
                  const out={ok_tree_label:tree.querySelector('[data-nav-view="dashboard"]')?.textContent===label,
                    ok_crumb_label:Array.from(crumb.querySelectorAll('button')).some(e=>e.textContent===label),
                    ok_tree_inert:!tree.querySelector('[data-audit-probe]'),ok_crumb_inert:!crumb.querySelector('[data-audit-probe]')};
                  globalThis.trEpi=original;return out;
                }''', sources['navigation-controls.js'])
                case('joinventure_labels_tokens_scope', '''()=>{
                  const name='JV <img data-audit-probe="jv"> & " raw';
                  const state=__EPI_APP_STATE__;state.units.find(u=>u.id===5).name='Unit <img data-audit-probe="unit"> & raw';
                  const h=document.getElementById('epi-joinventures'),s=document.getElementById('epi-joinventure-active');
                  h.value=JSON.stringify([{name,unit_id:'5'}]);
                  const token=name+'@@5', o=new Option(name,token);s.replaceChildren(o);s.value=token;
                  renderJoinventureList();
                  const list=document.getElementById('epi-joinventure-list');
                  const button=list.querySelector('button');
                  const out={ok_value:s.value===token,ok_hidden:JSON.parse(h.value)[0].name===name,
                    ok_token:button?.dataset.joinventureRemove===token,ok_label:button?.textContent.includes(name),
                    ok_inert:!list.querySelector('[data-audit-probe]')&&!s.querySelector('[data-audit-probe]')};
                  h.value=JSON.stringify([{name:'foreign',unit_id:'99999'}]);renderJoinventureList();
                  out.ok_foreign_filtered=JSON.parse(h.value).length===0&&s.value==='';return out;
                }''')
                case('rich_text_literals_and_template_emphasis', '''()=>{
                  const name='<img data-audit-probe="rich"><strong>raw</strong>&lt;literal&gt;{literal} & "';
                  EpiI18n.translations.__auditRich='Before <strong>{name}</strong><br><em>after</em>';
                  const e=document.createElement('div');e.dataset.i18nHtml='__auditRich';e.dataset.i18nVars=JSON.stringify({name});document.body.append(e);
                  EpiI18n.translateDOM(e);
                  const out={ok_text:e.textContent==='Before '+name+'after',ok_emphasis:e.querySelectorAll('strong').length===1&&e.querySelector('strong').textContent===name,
                    ok_break:e.querySelectorAll('br').length===1,ok_inert:!e.querySelector('[data-audit-probe]'),ok_italics:e.querySelector('em')?.textContent==='after'};
                  e.remove();return out;
                }''')
                case('rich_catalogue_rejects_tags_and_attributes', '''()=>{
                  const raw='<img data-audit-probe="catalogue"><strong title="attribute">literal</strong><svg data-audit-probe="svg"></svg>';
                  EpiI18n.translations.__auditRestricted=raw+'<em>allowed</em>';
                  const e=document.createElement('div');e.dataset.i18nHtml='__auditRestricted';document.body.append(e);EpiI18n.translateDOM(e);
                  const out={ok_text:e.textContent===raw+'allowed',ok_inert:!e.querySelector('[data-audit-probe]'),
                    ok_no_attributes:!e.querySelector('[title]'),ok_allowed:e.querySelectorAll('em').length===1&&e.querySelector('em').textContent==='allowed'};
                  e.remove();return out;
                }''')
                case('password_change_boolean_storage', '''()=>{
                  const key='epi-session-v4-password-change-required';
                  const outcomes=[true,false,{synthetic:'marker'},null].map(v=>{__EPI_AUTH__.setPasswordChangeRequired(v);return [__EPI_APP_STATE__.requirePasswordChange,localStorage.getItem(key)]});
                  return {ok_contract:JSON.stringify(outcomes)===JSON.stringify([[true,'true'],[false,'false'],[true,'true'],[false,'false']]), outcomes};
                }''')
                case('delivery_review_and_search_text_tokens', '''(source)=>{
                  const original=globalThis.getFeatureFlag;globalThis.getFeatureFlag=(name,opts)=>name==='entrega_epi_htmx_enabled'?true:original(name,opts);
                  globalThis.__EPI_ENTREGA_EPI_BOUND__=false;(0,eval)(source);globalThis.getFeatureFlag=original;
                  const ids=['delivery-company','delivery-unit-filter','delivery-employee','delivery-epi'];
                  const labels=ids.map((id,i)=>'Field'+i+' <img data-audit-probe="delivery'+i+'"> & " raw');
                  ids.forEach((id,i)=>{const s=document.getElementById(id);s.replaceChildren(new Option(labels[i],String(i+1)));s.value=String(i+1)});
                  const form=document.getElementById('delivery-form');
                  const submit=document.getElementById('delivery-ux-guide').closest('form')?.querySelector('button.primary')||Array.from(form.querySelectorAll('button')).find(e=>e.textContent==='Ir para seleção de EPI');
                  submit.click();submit.click();
                  const review=document.getElementById('delivery-ux-review');
                  const input=document.getElementById('delivery-employee-search');input.value='';input.dispatchEvent(new Event('input',{bubbles:true}));
                  const box=input.parentElement.querySelector('.delivery-ux-dropdown');
                  const option=box.querySelector('button[data-value]');
                  return {ok_review_visible:!review.hidden,ok_review_labels:labels.every(t=>review.textContent.includes(t)),
                    ok_review_inert:!review.querySelector('[data-audit-probe]'),ok_search_label:option?.textContent===labels[2],
                    ok_search_inert:!box.querySelector('[data-audit-probe]'),ok_search_value:option?.dataset.value==='3'};
                }''', sources['entrega-epi.js'])
                page.wait_for_timeout(100)
                writes = [c for c in f.calls[start:] if c['method'] != 'GET']
                result['cases'].append(dict(locale=locale,name='no_api_writes_or_js_errors',passed=not writes and not f.errors, writes=writes, errors=f.errors))
                page.screenshot(path=str(output / f'{locale}.png'))
                context.close()
            browser.close()
    finally:
        server.shutdown()
    result['passed']=sum(c['passed'] for c in result['cases']);result['failed']=len(result['cases'])-result['passed']
    (output / 'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(dict(root=str(root),baseline_ref=baseline,passed=result['passed'],failed=result['failed'],failures=[dict(locale=c['locale'],name=c['name'],failed=c.get('failed'),error=c.get('error')) for c in result['cases'] if not c['passed']]),ensure_ascii=False))
    return result['failed']==0

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);p.add_argument('--output',type=Path,required=True);p.add_argument('--baseline-ref')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    raise SystemExit(0 if run(a.root.resolve(),a.output.resolve(),a.baseline_ref) else 1)
