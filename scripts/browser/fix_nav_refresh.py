"""FIX-NAV-REFRESH-V1 — Chromium: SPA real + API sintética interceptada; nunca abre banco.

Mesmo harness de scripts/browser/fix_colab_terc.py (Fixture), estendido com EPIs,
Unidades e transferência de colaborador:

1. Transferir colaborador, arquivar/desarquivar/excluir EPI e Unidade mantêm a
   tela atual (e a tela é revalidada: sem permissão, volta à tela padrão).
2. Depois de arquivar, cada lista afetada é pedida uma única vez.
3. Gravação concluída + atualização da tela com falha: aviso verdadeiro (não
   "falha ao arquivar") e nenhuma segunda gravação; clique duplo grava uma vez.

pip install playwright; playwright install chromium
python scripts/browser/fix_nav_refresh.py --output /tmp/fix-nav-refresh
CHROMIUM_EXECUTABLE=/usr/bin/chromium seleciona um navegador já instalado.
"""
import argparse
import copy
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

ROOT = base.ROOT
LOCALES = base.LOCALES
PERMISSIONS = base.PERMISSIONS + ['employees:transfer', 'epis:view', 'epis:create', 'epis:update',
                                  'epis:delete', 'units:create', 'units:update', 'units:delete']
EPI = dict(id=61, company_id=901, company_name='Empresa QA', unit_id=5, unit_name='Unidade QA',
           name='Luva QA', ca='12345', protection_type='maos', active=1)
UNIT = dict(id=6, company_id=901, company_name='Empresa QA', name='Base Norte QA', unit_type='base')


class Fixture(base.Fixture):
    def __init__(self, *args):
        super().__init__(*args)
        self.permissions = PERMISSIONS[:]
        self.epis, self.units = [copy.deepcopy(EPI)], [dict(id=5, company_id=901, name='Unidade QA', unit_type='base'),
                                                      copy.deepcopy(UNIT)]
        self.archived_epis, self.archived_units = [], []
        self.fail_refresh = False
        self.hidden_modules = []

    def route(self, route):
        request = route.request
        path = urlsplit(request.url).path
        if self.fail_refresh and path == '/api/bootstrap':
            self.calls.append(dict(method='GET', path=path, query='', body=None))
            return route.fulfill(status=500, json=dict(error='QA refresh failure'))
        body = json.loads(request.post_data or '{}') if request.method != 'GET' else None
        match = re.fullmatch(r'/api/(epis|units)/(\d+)/(archive|restore|purge-request|purge-cancel|purge-confirm)', path)
        handled = None
        if path == '/api/bootstrap':
            # O bootstrap do harness base, acrescido de EPIs/Unidades e da
            # visibilidade de módulos deste cenário.
            original = route.fulfill

            def fulfill(**kwargs):
                payload = kwargs.get('json') or {}
                payload.update(epis=self.epis, units=self.units)
                if self.hidden_modules:
                    payload['module_visibility'] = {name: False for name in self.hidden_modules}
                kwargs['json'] = payload
                return original(**kwargs)
            route.fulfill = fulfill
            return super().route(route)
        if match:
            kind, record_id, operation = match.group(1), int(match.group(2)), match.group(3)
            active, archived = (self.epis, self.archived_epis) if kind == 'epis' else (self.units, self.archived_units)
            source = active if operation == 'archive' else archived
            record = next((item for item in source if item['id'] == record_id), None)
            if operation in ('archive', 'restore') and record is None:
                # Repetição da mesma operação: o backend real recusa.
                self.calls.append(dict(method=request.method, path=path, query='', body=body))
                return route.fulfill(status=409, json=dict(error='QA already done', message='QA already done'))
            if operation == 'archive':
                active.remove(record)
                archived.append(dict(record, **base.ARCHIVED))
            elif operation == 'restore':
                archived.remove(record)
                active.append(record)
            elif operation == 'purge-confirm':
                archived[:] = [item for item in archived if item['id'] != record_id]
            handled = dict(ok=True, records={})
        elif re.fullmatch(r'/api/epis/\d+/archival-state', path):
            handled = dict(archival_state=dict(has_open_links=False))
        elif path == '/api/epis/archived':
            handled = dict(epis=self.archived_epis)
        elif path == '/api/units/archived':
            handled = dict(units=self.archived_units)
        elif path == '/api/employee-unit-movements' and request.method == 'POST':
            self.employees[0]['unit_id'] = int(body['target_unit_id'])
            handled = dict(ok=True)
        if handled is not None:
            self.calls.append(dict(method=request.method, path=path, query=urlsplit(request.url).query, body=body))
            if self.fail_mutation and request.method != 'GET':
                return route.fulfill(status=403, json=dict(error='QA forbidden', message='QA forbidden'))
            return route.fulfill(json=handled)
        return super().route(route)

    def open(self):
        super().open()
        # Registra os toasts exibidos (um #epi-toast por vez) sem trocar showToast.
        self.page.evaluate('''()=>{globalThis.__QA_TOASTS__=[];new MutationObserver((records)=>{for(const r of records)
          for(const n of r.addedNodes) if(n.id==="epi-toast") __QA_TOASTS__.push([n.getAttribute("role"),n.textContent]);
        }).observe(document.body,{childList:true});}''')

    def toasts(self):
        return self.page.evaluate('globalThis.__QA_TOASTS__')

    def gets(self, path, since):
        return [c for c in self.calls[since:] if c['method'] == 'GET' and c['path'] == path]


def active_view(f):
    return f.page.locator('.view.active').get_attribute('id')


def confirm(f):
    f.page.locator('.ds-confirm-ok').click()


def transfer(f):
    f.view('gestao-colaborador')
    form = f.page.locator('#movement-form')
    form.locator('[name="employee_id"]').select_option('31')
    form.locator('[name="target_unit_id"]').select_option('6')
    form.locator('[name="start_date"]').fill('2026-10-27')
    before = len(f.calls)
    form.locator('button[type="submit"]').click()
    f.page.wait_for_function('__EPI_APP_STATE__.employees.find(e=>e.id===31).unit_id===6')
    f.page.wait_for_timeout(200)
    assert sum(c['path'] == '/api/employee-unit-movements' for c in f.calls[before:]) == 1
    assert active_view(f) == 'gestao-colaborador-view', 'transfer navigated away to ' + str(active_view(f))


def epi_archival(f):
    f.view('epis')
    f.tab('epis', 'lista')
    before = len(f.calls)
    f.page.locator('[data-epi-archive="61"]').first.click()
    confirm(f)
    f.page.wait_for_function('(__EPI_APP_STATE__.archivedEpis||[]).some(e=>e.id===61)')
    f.page.wait_for_timeout(600)
    assert active_view(f) == 'epis-view', 'EPI archive navigated away to ' + str(active_view(f))
    archived_gets = len(f.gets('/api/epis/archived', before))
    assert archived_gets == 1, f'archived EPIs requested {archived_gets}x after archive'
    expect(f.page.locator('#archived-epis-table')).to_contain_text('Luva QA')
    f.tab('epis', 'arquivados')
    f.page.locator('[data-archived-restore="epi:61"]').click()
    confirm(f)
    f.page.wait_for_function('__EPI_APP_STATE__.epis.some(e=>e.id===61)')
    f.page.wait_for_timeout(200)
    assert active_view(f) == 'epis-view', 'EPI restore navigated away'
    f.epis.remove(next(item for item in f.epis if item['id'] == 61))
    f.archived_epis.append(dict(EPI, **base.ARCHIVED))
    f.page.evaluate('async()=>{await loadBootstrap({preserveView:true})}')
    f.page.wait_for_function('(__EPI_APP_STATE__.archivedEpis||[]).some(e=>e.id===61)')
    f.page.locator('[data-archived-purge="epi:61"]').click()
    confirm(f)
    expect(f.page.locator('[data-archived-purge="epi:61"]')).to_have_count(0)
    assert active_view(f) == 'epis-view', 'EPI purge navigated away'


def unit_archival(f):
    f.view('unidades')
    f.tab('unidades', 'lista')
    before = len(f.calls)
    f.page.locator('[data-unit-archive="6"]').first.click()
    confirm(f)
    f.page.wait_for_function('(__EPI_APP_STATE__.archivedUnits||[]).some(u=>u.id===6)')
    f.page.wait_for_timeout(600)
    assert active_view(f) == 'unidades-view', 'unit archive navigated away to ' + str(active_view(f))
    archived_gets = len(f.gets('/api/units/archived', before))
    assert archived_gets == 1, f'archived units requested {archived_gets}x after archive'
    f.tab('unidades', 'arquivadas')
    f.page.locator('[data-unit-restore="6"]').click()
    confirm(f)
    f.page.wait_for_function('__EPI_APP_STATE__.units.some(u=>u.id===6)')
    f.page.wait_for_timeout(200)
    assert active_view(f) == 'unidades-view', 'unit restore navigated away'
    f.units.remove(next(item for item in f.units if item['id'] == 6))
    f.archived_units.append(dict(UNIT, **base.ARCHIVED))
    f.page.evaluate('async()=>{await loadBootstrap({preserveView:true})}')
    f.page.wait_for_function('(__EPI_APP_STATE__.archivedUnits||[]).some(u=>u.id===6)')
    f.page.locator('[data-unit-purge="6"]').click()
    confirm(f)
    expect(f.page.locator('[data-unit-purge="6"]')).to_have_count(0)
    assert active_view(f) == 'unidades-view', 'unit purge navigated away'


def lost_access(f):
    # Sem acesso à tela depois da mutação (módulo Terceirizados desligado no
    # tenant): a tela NÃO é mantida — showView revalida e volta à tela padrão.
    f.view('terceirizados')
    f.page.wait_for_function('__EPI_APP_STATE__.outsourcedCompanies.length===1')
    f.tab('terceirizados', 'colaboradores')
    f.hidden_modules = ['terceirizados']
    f.page.locator('[data-outsourced-employee-archive="32"]').click()
    confirm(f)
    f.page.wait_for_function('!__EPI_APP_STATE__.employees.some(e=>e.id===32)')
    f.page.wait_for_function('!document.getElementById("terceirizados-view").classList.contains("active")')
    assert active_view(f) != 'terceirizados-view'


def redundant_reloads(f):
    f.view('colaboradores')
    before = len(f.calls)
    f.page.locator('[data-employee-archive="31"]').first.dispatch_event('click')
    confirm(f)
    f.page.wait_for_function('(__EPI_APP_STATE__.archivedEmployees||[]).some(e=>e.id===31)')
    f.page.wait_for_timeout(600)
    count = len(f.gets('/api/employees/archived', before))
    assert count == 1, f'archived employees requested {count}x after archive'
    f.view('terceirizados')
    f.page.wait_for_function('__EPI_APP_STATE__.outsourcedCompanies.length===1')
    f.page.wait_for_timeout(300)
    f.tab('terceirizados', 'colaboradores')
    before = len(f.calls)
    f.page.locator('[data-outsourced-employee-archive="32"]').click()
    confirm(f)
    f.page.wait_for_function('(__EPI_APP_STATE__.archivedOutsourcedEmployees||[]).some(e=>e.id===32)')
    f.page.wait_for_timeout(600)
    for path in ['/api/employees/archived', '/api/outsourced-companies/archived', '/api/outsourced-companies']:
        count = len(f.gets(path, before))
        assert count <= 1, f'{path} requested {count}x after archive'
    assert active_view(f) == 'terceirizados-view'


def refresh_failed_text(f):
    catalog = json.loads((ROOT / 'static/i18n' / (f.locale + '.json')).read_text())
    return catalog.get('mutation', {}).get('refreshFailed', 'mutation.refreshFailed (ausente)')


def truthful_message(f):
    # Gravação concluída, atualização da tela falha: aviso verdadeiro, sem erro
    # cru da recarga e sem segunda gravação (EPI via toast, Unidade via alert).
    expected = refresh_failed_text(f)
    for view, tab, button, post_path in [('epis', 'lista', '[data-epi-archive="61"]', '/api/epis/61/archive'),
                                         ('unidades', 'lista', '[data-unit-archive="6"]', '/api/units/6/archive')]:
        f.fail_refresh = False
        f.view(view)
        f.tab(view, tab)
        f.fail_refresh = True
        f.page.evaluate('()=>{globalThis.__QA_TOASTS__.length=0}')
        f.page.locator(button).first.click()
        confirm(f)
        f.page.wait_for_function('(expected)=>(globalThis.__QA_TOASTS__||[]).some(([,t])=>t===expected)', arg=expected, timeout=4000)
        toasts = f.toasts()
        assert not any(role == 'alert' for role, _ in toasts), f'error toast after successful save: {toasts}'
        assert not any('QA refresh failure' in d['message'] for d in f.dialogs), f'raw refresh error shown: {f.dialogs}'
        posts = [c for c in f.calls if c['method'] == 'POST' and c['path'] == post_path]
        assert len(posts) == 1, f'{len(posts)} POSTs to {post_path}'


def double_click(f):
    f.view('unidades')
    f.tab('unidades', 'lista')
    # Dois cliques no mesmo tick (duplo clique / clique repetido antes do diálogo abrir).
    f.page.evaluate('()=>{const b=document.querySelector(\'[data-unit-archive="6"]\');b.click();b.click();}')
    for _ in range(3):
        f.page.wait_for_timeout(300)
        ok = f.page.locator('.ds-confirm-ok:visible')
        if ok.count():
            ok.last.click()
    f.page.wait_for_function('(__EPI_APP_STATE__.archivedUnits||[]).some(u=>u.id===6)')
    f.page.wait_for_timeout(400)
    posts = [c for c in f.calls if c['method'] == 'POST' and c['path'] == '/api/units/6/archive']
    assert len(posts) == 1, f'{len(posts)} archive POSTs after double click'


SCENARIOS = [transfer, epi_archival, unit_archival, lost_access, redundant_reloads, truthful_message, double_click]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/fix-nav-refresh-browser'))
    parser.add_argument('--locales', nargs='+', default=LOCALES)
    parser.add_argument('--scenarios', nargs='+', default=[s.__name__ for s in SCENARIOS])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(base.QuietHandler, directory=str(ROOT / 'static')))
    Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    results = []
    with sync_playwright() as playwright:
        options = dict(headless=True, args=['--no-sandbox'])
        if os.environ.get('CHROMIUM_EXECUTABLE'):
            options['executable_path'] = os.environ['CHROMIUM_EXECUTABLE']
        browser = playwright.chromium.launch(**options)
        for locale in args.locales:
            for scenario in [s for s in SCENARIOS if s.__name__ in args.scenarios]:
                context = browser.new_context(viewport=dict(width=1440, height=1000), service_workers='block', locale=locale)
                page = context.new_page()
                page.set_default_timeout(4000)
                fixture = Fixture(page, origin, locale)
                fixture.evidence_dir = args.output
                result = dict(locale=locale, scenario=scenario.__name__, status='passed')
                try:
                    fixture.open()
                    scenario(fixture)
                    assert page.evaluate('EpiI18n.lang') == locale, 'locale changed during scenario'
                except Exception as error:
                    result.update(status='failed', error=str(error))
                finally:
                    result.update(calls=fixture.calls, dialogs=fixture.dialogs, page_errors=fixture.errors,
                                  toasts=fixture.page.evaluate('globalThis.__QA_TOASTS__||[]'),
                                  blocked_external_requests=fixture.external)
                    page.screenshot(path=str(args.output / f'{locale}-{scenario.__name__}.png'))
                    results.append(result)
                    print(f"{locale} {scenario.__name__}: {result['status']} {result.get('error', '')[:200]}", flush=True)
                    context.close()
        browser.close()
    server.shutdown()
    (args.output / 'results.json').write_text(json.dumps(results, indent=2, ensure_ascii=False) + '\n')
    return int(any(result['status'] != 'passed' for result in results))


if __name__ == '__main__':
    raise SystemExit(main())
