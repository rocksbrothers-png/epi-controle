"""UBX Marca: SPA real, API sintética e referência anterior à extração, em cinco idiomas.

--record --static <base>/static grava a referência do próprio produto.
Não abre banco nem acessa serviços externos.
"""
import argparse
import base64
import json
import os
import sys
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fix_colab_terc as base
import i18n_commercial as commercial

ROOT = base.ROOT
GOLDEN = ROOT / 'static/js/test/fixtures/ubx-platform-brand-browser.json'
PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
SNAPSHOT = """() => ({
  brand: __EPI_APP_STATE__.platformBrand,
  name: platformBrandDisplayName(),
  nodes: Object.fromEntries(['platform-brand-name','platform-brand-logo','platform-logo-preview',
    'platform-login-logo-preview','login-brand-logo'].map(id=>[id,document.getElementById(id)?.innerHTML])),
  fields: Object.fromEntries([...document.getElementById('platform-brand-form').elements].filter(n=>n.name).map(n=>[n.name,n.value])),
  xss: window.__xss || 0
})"""


class Fixture(commercial.Fixture):
    def __init__(self, *args):
        super().__init__(*args)
        self.brand = {'display_name': 'Marca QA', 'legal_name': 'Marca QA SA', 'cnpj': '11222333000181', 'logo_type': PNG, 'login_logo_type': ''}
        self.status = 200

    def route(self, route):
        req = route.request
        path = urlsplit(req.url).path
        if path == '/api/bootstrap':
            original = route.fulfill

            def fulfill(**kwargs):
                payload = kwargs.get('json') or {}
                payload['platform_brand'] = self.brand
                kwargs['json'] = payload
                return original(**kwargs)
            route.fulfill = fulfill
        if path == '/api/platform-brand':
            body = json.loads(req.post_data or '{}')
            self.calls.append({'method': req.method, 'path': path, 'query': urlsplit(req.url).query, 'body': body})
            if self.status != 200:
                return route.fulfill(status=self.status, json={'error': f'QA {self.status}', 'message': f'QA {self.status}'})
            self.brand = {k: v for k, v in body.items() if k != 'actor_user_id'}
            return route.fulfill(json={'ok': True, 'brand': self.brand})
        return super().route(route)


def exercise(f):
    p = f.page
    steps = []

    def capture(label):
        steps.append({'label': label, 'snapshot': p.evaluate(SNAPSHOT), 'dialogs': f.dialogs[:],
                          'writes': [c for c in f.calls if c['path'] == '/api/platform-brand']})
        assert p.evaluate('window.__xss || 0') == 0

    f.view('comercial')
    f.tab('comercial', 'config')
    capture('inicial')
    form = p.locator('#platform-brand-form')
    form.locator('[name="display_name"]').fill('Marca <img src=x onerror=window.__xss=1>')
    form.locator('[name="legal_name"]').fill('Empresa & Cia')
    form.locator('[name="cnpj"]').fill('11222333000181')
    before = len(f.dialogs)
    form.locator('[type="submit"]').click()
    p.wait_for_function('__EPI_APP_STATE__.platformBrand.display_name.includes("<img")')
    assert len([c for c in f.calls if c['path'] == '/api/platform-brand']) == 1, 'submit duplicado'
    assert len(f.dialogs) == before + 1
    capture('salvar')

    for field in ['platform-logo-file', 'platform-login-logo-file']:
        p.locator('#' + field).set_input_files({'name': 'logo.png', 'mimeType': 'image/png', 'buffer': base64.b64decode(PNG.split(',')[1])})
        hidden = 'logo_type' if field == 'platform-logo-file' else 'login_logo_type'
        p.wait_for_function('(name)=>document.querySelector(`#platform-brand-form [name="${name}"]`).value.startsWith("data:image/")', arg=hidden)
        capture('upload ' + field)
        before = len(f.dialogs)
        p.locator('#' + field).set_input_files({'name': 'invalido.txt', 'mimeType': 'text/plain', 'buffer': b'QA'})
        assert len(f.dialogs) == before + 1
        capture('invalido ' + field)
        p.locator('#' + field).set_input_files([])
        expect(form.locator('[name="' + hidden + '"]')).to_have_value('')
        capture('limpar ' + field)

    for status in [401, 403, 500]:
        f.status = status
        before = len(f.dialogs)
        p.evaluate("document.getElementById('platform-brand-form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))")
        p.wait_for_timeout(150)
        assert len(f.dialogs) == before + 1, f'erro {status} sem retorno'
        capture('erro ' + str(status))
    f.status = 200

    # Bloqueio visual: o submit continua cancelado e não grava para não-Master.
    before = len([c for c in f.calls if c['path'] == '/api/platform-brand'])
    p.evaluate("__EPI_APP_STATE__.user={id:99,role:'general_admin',company_id:902};document.getElementById('platform-brand-form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))")
    p.wait_for_timeout(100)
    assert len([c for c in f.calls if c['path'] == '/api/platform-brand']) == before
    capture('principal sem permissão')
    p.evaluate("__EPI_APP_STATE__.user=null;document.getElementById('platform-brand-form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))")
    p.wait_for_timeout(100)
    assert len([c for c in f.calls if c['path'] == '/api/platform-brand']) == before
    capture('sem sessão')
    p.evaluate('(actor)=>{__EPI_APP_STATE__.user=actor}', f.actor)

    # Substituição por bootstrap e precedência da marca do tenant no login.
    f.brand = {'display_name': 'Bootstrap B', 'legal_name': '', 'cnpj': '', 'logo_type': '', 'login_logo_type': ''}
    p.evaluate('async()=>{await loadBootstrap()}')
    p.evaluate("window.__epiTenant={name:'Tenant B'};document.getElementById('login-brand-logo').innerHTML='<span>Tenant B</span>';renderPlatformBrand()")
    assert p.locator('#login-brand-logo').inner_text() == 'Tenant B'
    capture('tenant preservado')
    p.evaluate("delete window.__epiTenant;renderPlatformBrand()")
    assert p.locator('#login-brand-logo').inner_html() == ''
    capture('sem tenant')
    other = 'fr-FR' if f.locale != 'fr-FR' else 'nb-NO'
    p.evaluate('(lang)=>EpiI18n.setLang(lang,{persist:false})', other)
    p.wait_for_function('(lang)=>EpiI18n.lang===lang', arg=other)
    p.wait_for_timeout(150)
    capture('troca de idioma')
    assert not f.errors, f.errors
    return {'steps': steps}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--static', type=Path, default=ROOT / 'static')
    parser.add_argument('--locales', nargs='+', default=base.LOCALES)
    parser.add_argument('--record', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(base.QuietHandler, directory=str(args.static)))
    Thread(target=server.serve_forever, daemon=True).start()
    golden = {} if args.record else json.loads(GOLDEN.read_text())
    results = []
    try:
        with sync_playwright() as pw:
            options = {'headless': True, 'args': ['--no-sandbox']}
            if os.environ.get('CHROMIUM_EXECUTABLE'):
                options['executable_path'] = os.environ['CHROMIUM_EXECUTABLE']
            browser = pw.chromium.launch(**options)
            for locale in args.locales:
                context = browser.new_context(viewport={'width': 1440, 'height': 1000}, service_workers='block', locale=locale)
                page = context.new_page()
                page.clock.set_fixed_time('2026-11-15T12:00:00')
                page.set_default_timeout(8000)
                result = {'locale': locale, 'status': 'passed'}
                try:
                    f = Fixture(page, f'http://127.0.0.1:{server.server_port}', locale)
                    f.open()
                    observed = exercise(f)
                    (args.output / f'{locale}-observed.json').write_text(json.dumps(observed, ensure_ascii=False, indent=1) + '\n')
                    if args.record:
                        golden[locale] = observed
                    elif observed != golden[locale]:
                        changed = [a['label'] for a, b in zip(observed['steps'], golden[locale]['steps'], strict=True) if a != b]
                        raise AssertionError('divergência: ' + ', '.join(changed))
                    result['steps'] = len(observed['steps'])
                except Exception as error:  # noqa: BLE001 — registra o cenário e continua nos demais idiomas
                    result.update(status='failed', error=str(error))
                finally:
                    context.close()
                results.append(result)
                print(json.dumps(result, ensure_ascii=False), flush=True)
            browser.close()
    finally:
        server.shutdown()
    if args.record and all(r['status'] == 'passed' for r in results):
        GOLDEN.write_text(json.dumps(golden, ensure_ascii=False, indent=1) + '\n')
    (args.output / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
    return int(any(r['status'] != 'passed' for r in results))


if __name__ == '__main__':
    raise SystemExit(main())
