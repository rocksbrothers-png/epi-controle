"""UBX Shell/Topbar: SPA real, cinco idiomas, desktop/mobile e comparação main × branch.

--record --static <main/static> grava a referência DOM antes de extrair.
--baseline-static compara também screenshots em ambiente/Chromium idênticos.
API sintética interceptada; não abre banco nem serviços externos.
"""
import argparse
import hashlib
import json
import os
import re
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
GOLDEN = ROOT / 'static/js/test/fixtures/ubx-shell-topbar-browser.json'
MOTION = '*{animation:none!important;transition:none!important;caret-color:transparent!important}'
I18N_TASK_TRACKER = """(() => {
  // Observa o debounce real de epi:langchange. Mesmos atrasos, argumentos e this.
  // Nenhum relógio é acelerado, nenhuma tarefa é descartada e nenhum DOM é reescrito.
  const pending = new Set();
  const schedule = window.setTimeout.bind(window), cancel = window.clearTimeout.bind(window);
  window.setTimeout = function (callback, delay, ...args) {
    if (Number(delay) !== 60 || typeof callback !== 'function') return schedule(callback, delay, ...args);
    let id;
    id = schedule(function (...values) {
      try { return Reflect.apply(callback, this, values); } finally { pending.delete(id); }
    }, delay, ...args);
    pending.add(id);
    return id;
  };
  window.clearTimeout = function (id) { pending.delete(id); return cancel(id); };
  window.__qaI18nTaskTracker = Object.freeze({get pending() {return pending.size;}});
})();"""


class Fixture(commercial.Fixture):
    def __init__(self, *args):
        super().__init__(*args)
        self.actor.update(company_name='Empresa A <img src=x onerror=window.__xss=1>', unit_name='Base A & Cia',
                          full_name='Ana QA', tenant_id=101, unit_id=5, company_cnpj='11222333000181')
        self.bootstrap_status = 200
        self.preferences_status = 200
        self.hold_bootstrap = False
        self.pending_route = None
        self.boot_order = 'tenant-after-shell'
        self.boot_gate_active = False
        self.pending_tenant = None
        self.pending_app = None

    def begin_boot(self):
        self.boot_gate_active = True
        self.pending_tenant = None
        self.pending_app = None

    def finish_boot(self):
        if self.boot_order == 'tenant-before-shell':
            self.page.wait_for_function('window.__qaAppHeld === true')
            self.page.locator('#epi-lang-widget').wait_for(state='attached')
            assert self.pending_app is not None
            route, self.pending_app = self.pending_app, None
            self.boot_gate_active = False
            route.continue_()
        else:
            self.page.wait_for_function('globalThis.__EPI_UX_MOBILE_BOUND__ === true && window.__qaTenantHeld === true')
            assert self.pending_tenant is not None
            route, self.pending_tenant = self.pending_tenant, None
            self.boot_gate_active = False
            super().route(route)
        self.page.wait_for_load_state('load')
        ready(self.page)

    def navigate(self, url):
        self.begin_boot()
        self.page.goto(url, wait_until='commit')
        self.finish_boot()

    def route(self, route):
        request = route.request
        path = urlsplit(request.url).path
        # Mesmas respostas da main; apenas a ordem real de duas requisições é controlada.
        if self.boot_gate_active and self.boot_order == 'tenant-before-shell' and path == '/app.js':
            self.pending_app = route
            self.page.evaluate('window.__qaAppHeld = true')
            return None
        if self.boot_gate_active and self.boot_order == 'tenant-after-shell' and path == '/api/tenant/resolve':
            self.pending_tenant = route
            self.page.evaluate('window.__qaTenantHeld = true')
            return None
        if path in ['/api/login', '/api/auth/me']:
            body = json.loads(request.post_data or '{}')
            self.calls.append({'method': request.method, 'path': path, 'query': urlsplit(request.url).query, 'body': body})
            return route.fulfill(json={'user': self.actor, 'permissions': self.permissions, 'token': 'qa-synthetic-session'})
        if path == '/api/auth/me/preferences' and self.preferences_status != 200:
            self.calls.append({'method': request.method, 'path': path, 'query': '', 'body': json.loads(request.post_data or '{}')})
            return route.fulfill(status=self.preferences_status, json={'error': 'QA preferences forbidden', 'message': 'QA preferences forbidden'})
        if path == '/api/bootstrap':
            if self.hold_bootstrap:
                self.pending_route = route
                self.page.evaluate('window.__qaBootstrapHeld = true')
                return None
            if self.bootstrap_status != 200:
                self.calls.append({'method': request.method, 'path': path, 'query': '', 'body': None})
                return route.fulfill(status=self.bootstrap_status, json={'error': 'QA bootstrap failure', 'message': 'QA bootstrap failure'})
            original = route.fulfill

            def fulfill(**kwargs):
                payload = kwargs.get('json') or {}
                company = self.actor.get('company_id', 901)
                unit = self.actor.get('unit_id', 5)
                payload.update(user=self.actor, permissions=self.permissions, users=[self.actor], employees=[],
                               companies=[{'id': company, 'name': self.actor.get('company_name', ''), 'active': 1,
                                               'license_status': 'active', 'user_limit': 100}],
                               units=[{'id': unit, 'company_id': company, 'name': self.actor.get('unit_name') or self.actor.get('current_unit_name', ''), 'unit_type': 'base'}])
                kwargs['json'] = payload
                return original(**kwargs)
            route.fulfill = fulfill
        return super().route(route)


def ready(page):
    page.wait_for_function('!!globalThis.__EPI_APP_STATE__')
    # EpiI18n.ready é uma promessa já resolvida; o widget só existe após tenant-init/setLang.
    page.locator('#epi-lang-widget').wait_for(state='attached')
    page.wait_for_load_state('networkidle')
    settled(page)
    page.add_style_tag(content=MOTION)


def settled(page):
    page.wait_for_function('globalThis.__qaI18nTaskTracker?.pending === 0')


def login(f):
    f.page.locator('#login-username').fill('qa-user')
    f.page.locator('#login-password').fill('qa-synthetic-password')
    f.page.locator('#login-form button[type=submit]').click()
    expect(f.page.locator('#main-screen')).to_have_class(re.compile(r'\bactive\b'))
    f.page.wait_for_function('(id)=>__EPI_APP_STATE__.user?.id===id', arg=f.actor['id'])
    f.page.wait_for_load_state('networkidle')


def exercise(f, browser_context, output):
    page = f.page
    f.navigate(f.origin + '/?ux_phase2_colab_list=0&ux_mobile=0')
    expect(page.locator('#login-screen')).to_have_class(re.compile(r'\bactive\b'))
    page.evaluate('(l)=>EpiI18n.setLang(l,{persist:false})', f.locale)
    steps, visuals = [], []

    def capture(label, visual=False):
        settled(page)
        snapshot = page.evaluate('''() => {
          const st=__EPI_APP_STATE__, ids=['topbar-company-badge','theme-toggle','mobile-menu-toggle','logged-user-identity',
            'profile-label','company-badge','top-config-trigger','master-profile-btn','bootstrap-degraded-banner','bootstrap-degraded-panel'];
          return {topbar:document.querySelector('.topbar')?.outerHTML||'',sidebar:document.querySelector('.sidebar')?.outerHTML||'',
            drawer:document.getElementById('ds-drawer-root')?.outerHTML||'',body:document.body.className,
            theme:document.documentElement.getAttribute('data-theme'),lang:EpiI18n.lang,
            screen:document.querySelector('.screen.active')?.id,view:document.querySelector('.view.active')?.id,
            user:st.user&&{id:st.user.id,role:st.user.role,tenant_id:st.user.tenant_id,company_id:st.user.company_id,unit_id:st.user.unit_id},
            prefs:sessionStorage.getItem('epi-prefs-sessao'),retrying:st.bootstrapRetrying,degraded:st.bootstrapDegraded,
            fields:ids.map(id=>{const n=document.getElementById(id);return {id,exists:!!n,text:id.startsWith('bootstrap-')?n?.querySelector('strong')?.textContent:n?.textContent,hidden:n?.hidden,
              display:n?.style.display,expanded:n?.getAttribute('aria-expanded'),pressed:n?.getAttribute('aria-pressed'),label:n?.getAttribute('aria-label')}}),
            menu:[...document.querySelectorAll('#menu .menu-link')].map(n=>({view:n.dataset.view,display:n.style.display,active:n.classList.contains('active')})),
            xss:window.__xss||0};
        }''')
        assert snapshot['xss'] == 0
        steps.append({'label': label, 'snapshot': snapshot,
                          'calls': [c for c in f.calls if c['path'] in ['/api/login', '/api/auth/me/preferences']]})
        (output / 'observed-partial.json').write_text(json.dumps(steps, ensure_ascii=False, indent=1) + '\n')
        if visual and snapshot['screen'] == 'main-screen':
            for name, selector in [('topbar', '.topbar'), ('drawer', '.ds-drawer.is-open')]:
                target = page.locator(selector)
                if target.count() and target.is_visible():
                    filename = f'{len(steps):02d}-{name}.png'
                    target.screenshot(path=str(output / filename), animations='disabled', caret='hide')
                    (output / (filename + '.geometry.json')).write_text(json.dumps(target.evaluate('(n)=>({rect:n.getBoundingClientRect().toJSON(),scroll:[scrollX,scrollY],dpr:devicePixelRatio})'), indent=2))
                    visuals.append(filename)

    capture('login inicial')
    page.locator('#login-form button[type=submit]').click()
    capture('credenciais vazias')
    login(f)
    capture('login A / shell desktop', True)

    def mutations():
        return len([c for c in f.calls if c['path'] == '/api/auth/me/preferences'])

    count = mutations()
    page.locator('#theme-toggle').click()
    page.wait_for_function("document.documentElement.getAttribute('data-theme')==='dark'")
    assert mutations() == count + 1
    capture('tema escuro A', True)
    # Carga repetida dos scripts reais: nenhuma inicialização/listener adicional.
    scripts = page.evaluate("[...document.scripts].map(s=>s.src).filter(s=>s.includes('/js/modules/shell/ui/'))")
    for src in scripts:
        page.add_script_tag(url=src)
    page.add_script_tag(url=f.origin + '/app.js')
    count = mutations()
    page.locator('#theme-toggle').click()
    page.wait_for_function("document.documentElement.getAttribute('data-theme')!=='dark'")
    assert mutations() == count + 1
    capture('scripts repetidos / um clique de tema')
    page.locator('#mobile-menu-toggle').click()
    assert page.evaluate("document.body.classList.contains('sidebar-collapsed')")
    capture('sidebar desktop recolhida', True)

    page.locator('#top-config-trigger').click()
    expect(page.locator('#settings-save')).to_be_visible()
    capture('drawer aberto', True)
    page.locator('#settings-theme').select_option('dark')
    page.locator('#settings-density').select_option('compact')
    page.locator('#settings-cancel').click()
    capture('drawer cancelar não aplica')
    page.locator('#top-config-trigger').click()
    other = 'en-GB' if f.locale == 'fr-FR' else 'fr-FR'
    page.locator('#settings-theme').select_option('dark')
    page.locator('#settings-density').select_option('compact')
    page.locator('#settings-language').select_option(other)
    page.locator('#settings-save').click()
    page.wait_for_function('(l)=>EpiI18n.lang===l', arg=other)
    page.wait_for_load_state('networkidle')
    capture('drawer salvar / idioma ao vivo', True)
    page.evaluate('(l)=>EpiI18n.setLang(l)', f.locale)
    page.wait_for_load_state('networkidle')
    page.locator('#top-config-trigger').click()
    page.locator('#settings-restore').click()
    capture('restaurar campos sem gravar')
    page.locator('#settings-cancel').click()
    page.locator('#top-config-trigger').click()
    page.locator('#settings-advanced').click()
    expect(page.locator('#configuracao-view')).to_have_class(re.compile(r'\bactive\b'))
    capture('configuração avançada autorizada')

    # Nova aba usa o dono canônico e uma cópia de preferências da própria sessão.
    second = browser_context.new_page()
    second.clock.set_fixed_time('2026-11-15T12:00:00')
    other_fixture = Fixture(second, f.origin, f.locale)
    other_fixture.actor = f.actor
    other_fixture.boot_order = f.boot_order
    other_fixture.navigate(f.origin + '/?ux_phase2_colab_list=0&ux_mobile=0')
    expect(second.locator('#main-screen')).to_have_class(re.compile(r'\bactive\b'))
    second.wait_for_load_state('networkidle')
    main_pref = page.evaluate("sessionStorage.getItem('epi-prefs-sessao')")
    second.locator('#theme-toggle').click()
    second.wait_for_load_state('networkidle')
    assert page.evaluate("sessionStorage.getItem('epi-prefs-sessao')") == main_pref
    assert not other_fixture.errors
    second.close()
    capture('preferências em outra aba não substituem cópia local')

    page.set_viewport_size({'width': 390, 'height': 844})
    f.navigate(f.origin + '/?ux_phase2_colab_list=0&ux_mobile=1')
    expect(page.locator('#main-screen')).to_have_class(re.compile(r'\bactive\b'))
    page.wait_for_load_state('networkidle')
    capture('shell mobile / restauração', True)
    page.locator('#mobile-menu-toggle').click()
    assert page.evaluate("document.body.classList.contains('mobile-menu-open')")
    capture('menu móvel aberto', True)
    page.keyboard.press('Escape')
    assert not page.evaluate("document.body.classList.contains('mobile-menu-open')")
    capture('Escape fecha menu')
    page.locator('#mobile-menu-toggle').click()
    size = page.viewport_size
    x, y = size['width'] - 4, size['height'] - 4
    assert page.evaluate('([x,y])=>!document.elementFromPoint(x,y)?.closest(".sidebar,#mobile-menu-toggle")', [x, y])
    page.mouse.click(x, y)
    assert not page.evaluate("document.body.classList.contains('mobile-menu-open')")
    capture('clique fora fecha menu')
    page.locator('#mobile-menu-toggle').click()
    page.locator('#menu .menu-link[data-view="colaboradores"]').click()
    page.wait_for_load_state('networkidle')
    capture('navegação real fecha menu')

    f.actor.update(company_id=902, company_name='Empresa Contexto & B', unit_id=6, unit_name='Unidade B', tenant_id=202)
    page.evaluate('async()=>{await loadBootstrap();renderAll({preserveView:true})}')
    page.wait_for_load_state('networkidle')
    capture('empresa/unidade/tenant atualizados sem reload', True)
    f.actor.update(unit_name='', current_unit_name='Unidade fallback')
    page.evaluate('async()=>{await loadBootstrap();renderAll({preserveView:true})}')
    page.wait_for_load_state('networkidle')
    capture('unidade fallback atual')
    f.actor.update(id=8, role='buyer', full_name='Bruno QA', company_name='Empresa Pessoa B',
                   ui_preferences={'tema': 'light', 'densidade': 'normal', 'sidebar': 'expanded', 'idioma': f.locale})
    f.permissions = ['dashboard:view', 'purchase_requests:view']
    page.evaluate('async(data)=>{saveSession(data.user,data.permissions,"qa-synthetic-session-B");rotateSnapshotScope();await loadBootstrap();renderAll()}',
                  {'user': f.actor, 'permissions': f.permissions})
    page.wait_for_load_state('networkidle')
    expect(page.locator('#top-config-trigger')).not_to_be_visible()
    assert page.evaluate("document.documentElement.getAttribute('data-theme')!=='dark'")
    assert 'Empresa Pessoa B' in page.locator('#topbar-company-badge').inner_text()
    capture('principal B / papel restrito / sem estado A', True)
    f.preferences_status = 403
    page.locator('#theme-toggle').click()
    page.wait_for_load_state('networkidle')
    capture('erro ao persistir preferência mantém contrato')
    f.preferences_status = 200

    f.hold_bootstrap = True
    page.evaluate('()=>{window.__qaBootstrapHeld=false;setBootstrapDegraded({status:503,code:"DB_BOOTSTRAP_NOT_READY",message:"QA bootstrap pendente"});updateBootstrapDegradedUi()}')
    page.wait_for_function('__EPI_APP_STATE__.bootstrapRetrying===true', timeout=15000)
    page.wait_for_function('window.__qaBootstrapHeld === true')
    assert f.pending_route is not None
    capture('bootstrap em carregamento')
    f.bootstrap_status = 500
    f.hold_bootstrap = False
    route, f.pending_route = f.pending_route, None
    f.route(route)
    page.wait_for_function('__EPI_APP_STATE__.bootstrapRetrying===false')
    page.wait_for_load_state('networkidle')
    capture('erro de bootstrap / estado degradado')
    f.bootstrap_status = 200
    page.evaluate('async()=>{await loadBootstrap()}')
    page.wait_for_load_state('networkidle')
    capture('recuperação de bootstrap')

    page.locator('#mobile-menu-toggle').click()
    f.begin_boot()
    with page.expect_navigation(wait_until='commit'):
        page.locator('#logout-btn').click()
    f.finish_boot()
    expect(page.locator('#login-screen')).to_have_class(re.compile(r'\bactive\b'))
    assert page.evaluate("sessionStorage.getItem('epi-prefs-sessao')") is None
    assert page.evaluate('__EPI_APP_STATE__.user') is None
    capture('logout real / limpeza de principal e preferências')
    f.actor.update(id=9, role='registry_admin', full_name='Clara QA', company_name='Empresa C',
                   ui_preferences={'tema': 'light', 'densidade': 'normal', 'sidebar': 'expanded', 'idioma': f.locale})
    f.permissions = base.PERMISSIONS[:]
    login(f)
    capture('login C após logout / sem contexto anterior', True)
    assert not f.errors, f.errors
    return {'steps': steps, 'visuals': visuals}


def canonical(data, origin):
    if isinstance(data, str):
        return data.replace(origin, 'https://fixture.example.test')
    if isinstance(data, list):
        return [canonical(v, origin) for v in data]
    if isinstance(data, dict):
        return {k: canonical(v, origin) for k, v in data.items()}
    return data


def compact(observed):
    data = json.loads(json.dumps(observed))
    for step in data['steps']:
        for name in ['topbar', 'sidebar', 'drawer']:
            value = step['snapshot'][name]
            step['snapshot'][name] = hashlib.sha256(value.encode()).hexdigest()
    return data


def run(browser, static, locale, output, boot_order):
    output.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(base.QuietHandler, directory=str(static)))
    Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, service_workers='block', locale=locale)
    context.add_init_script(I18N_TASK_TRACKER)
    page = context.new_page()
    page.clock.set_fixed_time('2026-11-15T12:00:00')
    page.set_default_timeout(10000)
    try:
        fixture = Fixture(page, origin, locale)
        fixture.boot_order = boot_order
        observed = exercise(fixture, context, output)
        (output / 'observed.json').write_text(json.dumps(observed, ensure_ascii=False, indent=1) + '\n')
        return canonical(observed, origin)
    except Exception:
        page.screenshot(path=str(output / 'failure.png'))
        raise
    finally:
        context.close()
        server.shutdown()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--static', type=Path, default=ROOT / 'static')
    parser.add_argument('--baseline-static', type=Path)
    parser.add_argument('--locales', nargs='+', default=base.LOCALES)
    parser.add_argument('--record', action='store_true')
    parser.add_argument('--boot-order', choices=['both', 'tenant-before-shell', 'tenant-after-shell'], default='both')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    golden = {} if args.record else json.loads(GOLDEN.read_text())
    results = []
    with sync_playwright() as pw:
        # Partial raster varia bordas AA na própria main (13-topbar); raster completo
        # preserva CSS/DOM e a comparação PNG byte a byte, sem tolerância visual.
        options = {'headless': True, 'args': ['--no-sandbox', '--disable-gpu', '--force-color-profile=srgb', '--disable-skia-runtime-opts', '--disable-partial-raster']}
        if os.environ.get('CHROMIUM_EXECUTABLE'):
            options['executable_path'] = os.environ['CHROMIUM_EXECUTABLE']
        browser = pw.chromium.launch(**options)
        orders = ['tenant-before-shell', 'tenant-after-shell'] if args.boot_order == 'both' else [args.boot_order]
        for locale, boot_order in [(locale, order) for locale in args.locales for order in orders]:
            key = locale + '|' + boot_order
            result = {'locale': locale, 'boot_order': boot_order, 'status': 'passed'}
            try:
                reference = None
                if args.baseline_static:
                    reference = run(browser, args.baseline_static, locale, args.output / locale / boot_order / 'main', boot_order)
                current = run(browser, args.static, locale, args.output / locale / boot_order / 'branch', boot_order)
                actual = compact(current)
                if args.record:
                    golden[key] = actual
                else:
                    assert actual == golden[key], 'DOM/eventos/estado divergem da referência da main'
                images = 0
                if reference is not None:
                    assert compact(reference) == actual, 'main × branch divergem sob condições idênticas'
                    assert reference['visuals'] == current['visuals']
                    for filename in current['visuals']:
                        a = (args.output / locale / boot_order / 'main' / filename).read_bytes()
                        b = (args.output / locale / boot_order / 'branch' / filename).read_bytes()
                        assert a == b, 'PNG da UI diverge: ' + filename
                        images += 1
                result.update(steps=len(current['steps']), screenshots_compared=images)
            except Exception as error:  # noqa: BLE001 — preserva falha e segue nos idiomas
                result.update(status='failed', error=str(error))
            results.append(result)
            print(json.dumps(result, ensure_ascii=False), flush=True)
        browser.close()
    if args.record and all(r['status'] == 'passed' for r in results):
        GOLDEN.write_text(json.dumps(golden, ensure_ascii=False, indent=1) + '\n')
    (args.output / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
    return int(any(r['status'] != 'passed' for r in results))


if __name__ == '__main__':
    raise SystemExit(main())
