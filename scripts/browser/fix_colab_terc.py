"""Chromium regression: real SPA + synthetic intercepted API; never opens a DB.

pip install playwright; playwright install chromium
python scripts/browser/fix_colab_terc.py --output /tmp/fix-colab-terc
CHROMIUM_EXECUTABLE=/usr/bin/chromium selects a preinstalled browser.
A JSON result, request evidence and screenshots are written for each scenario.
"""
import argparse
import copy
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
from threading import Thread
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
LOCALES = ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO']
PERMISSIONS = ['dashboard:view', 'employees:view', 'employees:create', 'employees:update',
               'employees:delete', 'units:view']
ACTOR = dict(id=7, company_id=901, role='registry_admin', full_name='QA Admin')
EMPLOYEE = dict(id=31, company_id=901, company_name='Empresa QA', unit_id=5,
                unit_name='Unidade QA', employee_id_code='QA-31', name='Ana QA',
                cpf='52998224725', email='ana@example.test', whatsapp='5511999999999',
                preferred_contact_channel='email', sector='Operacao', role_name='Tecnica',
                schedule_type='28x28', admission_date='2024-01-02', tipo_vinculo='CLT', legal_entity_id=44)
OUTSOURCED = dict(EMPLOYEE, id=32, name='Tito QA', tipo_vinculo='Terceirizado',
                  outsourced_company_id=11, local_unit_link_status='active')
COMPANY = dict(id=11, company_id=901, legal_name='Terceira QA', trade_name='QA',
               company_kind='outsourced', registration_mode='simplified',
               epi_responsibility='Contratante', origin_unit_id=5)
# Registro arquivado com retenção cumprida: habilita "Excluir definitivamente".
ARCHIVED = dict(retention_days_remaining=0, legal_hold=0, status='archived', archived_at='2020-01-01',
                archive_reason='QA motivo', archived_by_name='QA Admin', company_name='Empresa QA')


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


class Fixture:
    def __init__(self, page, origin, locale):
        self.page, self.origin, self.locale = page, origin, locale
        self.actor, self.permissions = copy.deepcopy(ACTOR), PERMISSIONS[:]
        self.actor['ui_preferences'] = dict(idioma=locale)
        self.employees, self.companies, self.archived = [copy.deepcopy(EMPLOYEE), copy.deepcopy(OUTSOURCED)], [copy.deepcopy(COMPANY)], []
        self.archived_employees = []
        self.calls, self.dialogs, self.errors, self.external = [], [], [], []
        self.fail_mutation = False
        page.on('dialog', self.dialog)
        page.on('pageerror', lambda error: self.errors.append(str(error)))
        page.route('**/*', self.route)

    def dialog(self, dialog):
        self.dialogs.append(dict(type=dialog.type, message=dialog.message))
        if dialog.type == 'prompt':
            dialog.accept('QA motivo')
        else:
            dialog.accept()

    def route(self, route):
        request = route.request
        url = urlsplit(request.url)
        if url.netloc != urlsplit(self.origin).netloc:
            self.external.append(request.url)
            route.abort()
            return
        path = url.path
        if not path.startswith(('/api/', '/health')):
            route.continue_()
            return
        body = json.loads(request.post_data or '{}') if request.method != 'GET' else None
        self.calls.append(dict(method=request.method, path=path, query=url.query, body=body))
        if self.fail_mutation and request.method != 'GET':
            route.fulfill(status=403, json=dict(error='QA forbidden', message='QA forbidden'))
            return
        data = dict(items=[], ok=True, ready=True)
        if path.startswith('/api/i18n/'):
            data = dict(translations=json.loads((ROOT / 'static/i18n' / (path.rsplit('/', 1)[1] + '.json')).read_text()))
        elif path == '/api/auth/me/preferences' and request.method == 'PUT':
            self.actor['ui_preferences'].update(body)
            data = dict(ui_preferences=self.actor['ui_preferences'])
        elif path == '/api/bootstrap':
            data = dict(user=self.actor, permissions=self.permissions,
                        companies=[dict(id=901, name='Empresa QA', license_status='active', user_limit=100)],
                        units=[dict(id=5, company_id=901, name='Unidade QA', unit_type='base')],
                        employees=self.employees, users=[self.actor],
                        legal_entities=[dict(id=44, company_id=901, legal_name='Empresa QA', cnpj='11222333000181', active=1)])
        elif path == '/api/outsourced-companies':
            if request.method == 'POST':
                self.companies.append(dict(COMPANY, **{k:v for k,v in body.items() if k not in ('actor_user_id', 'id')}, id=12))
            data = dict(outsourced_companies=self.companies, available_outsourced_companies=[])
        elif path == '/api/outsourced-companies/archived':
            data = dict(outsourced_companies=self.archived)
        elif re.fullmatch('/api/outsourced-companies/\\d+', path) and request.method == 'PUT':
            self.companies[0].update(body)
        elif re.fullmatch(r'/api/employees/\d+/(archive|restore|purge-confirm)', path):
            record_id, operation = int(path.split('/')[3]), path.rsplit('/', 1)[1]
            source = self.employees if operation == 'archive' else self.archived_employees
            record = next(item for item in source if item['id'] == record_id)
            source.remove(record)
            if operation == 'archive':
                self.archived_employees.append(dict(record, **ARCHIVED))
            elif operation == 'restore':
                self.employees.append(record)
        elif re.fullmatch(r'/api/outsourced-companies/\d+/purge-confirm', path):
            self.archived = [item for item in self.archived if item['id'] != int(path.split('/')[3])]
        elif path.endswith(('/purge-request', '/purge-cancel')):
            data = dict(records={})
        elif path.endswith('/archive') and '/outsourced-companies/' in path:
            self.archived += self.companies[:1]
            self.companies = self.companies[1:]
        elif path.endswith('/restore') and '/outsourced-companies/' in path:
            self.companies += self.archived[:1]
            self.archived = self.archived[1:]
        elif '/outsourced-companies/' in path and '/unit-link/' in path:
            self.companies[0]['local_status'] = 'active' if path.endswith('/activate') else 'inactive'
        elif '/employees/32/' in path and '/unit-link/' in path:
            self.employees[1]['local_unit_link_status'] = 'active' if path.endswith('/activate') else 'inactive'
        elif path == '/api/employees/31' and request.method == 'PUT':
            self.employees[0].update(body)
        elif path == '/api/employees/archived':
            data = dict(employees=self.archived_employees)
        elif path == '/api/outsourced-companies/employees-summary':
            data = dict(items=[])
        route.fulfill(json=data)

    def open(self):
        self.page.goto(self.origin + '/?ux_phase2_colab_list=0', wait_until='load')
        self.page.wait_for_function('!!globalThis.__EPI_APP_STATE__')
        self.page.evaluate('async()=>{await EpiI18n.ready}')
        # Hydrate the same public state bridge the app uses. All loaders below
        # run through the canonical API client and intercepted browser requests.
        self.page.evaluate('(actor)=>{__EPI_APP_STATE__.user=actor;showScreen(true)}', self.actor)
        self.page.evaluate('async()=>{await loadBootstrap()}')
        self.page.wait_for_timeout(150)
        self.page.evaluate('(locale)=>EpiI18n.setLang(locale)', self.locale)
        self.page.wait_for_timeout(150)
        self.page.wait_for_load_state('networkidle')
        assert self.page.evaluate("EpiI18n.lang") == self.locale
        assert self.page.evaluate('(locale)=>EpiI18n.t("edit")', self.locale) == json.loads((ROOT / "static/i18n" / (self.locale + ".json")).read_text())["edit"]

    def view(self, name):
        self.page.evaluate('(view)=>showView(view,{partial:false})', name)
        expect(self.page.locator('#' + name + '-view')).to_have_class(re.compile(r'\bactive\b'))

    def tab(self, group, name):
        self.page.locator(f'nav[data-vtabs="{group}"] [data-vtab="{name}"]').click()

    def mutations(self):
        return [call for call in self.calls if call['method'] != 'GET' and call['path'].startswith(('/api/employees', '/api/outsourced-companies'))]


def links(f):
    f.actor.update(role='admin', operational_unit_id=5)
    f.permissions = ['dashboard:view', 'employees:view', 'employees:create_simplified', 'employees:update_simplified', 'units:view']
    f.page.evaluate('(actor)=>{__EPI_APP_STATE__.user=actor}', f.actor)
    f.page.evaluate('async()=>{await loadBootstrap()}')
    f.view('terceirizados')
    f.page.wait_for_function('__EPI_APP_STATE__.outsourcedCompanies.length===1')
    before = len(f.calls)
    f.page.evaluate('async()=>{await toggleEmployeeUnitLink(32,"deactivate")}')
    assert f.page.evaluate('__EPI_APP_STATE__.employees.find(e=>e.id===32).local_unit_link_status') == 'inactive', 'list stale after deactivation'
    assert any(c['path']=='/api/bootstrap' for c in f.calls[before:]), 'missing canonical bootstrap refresh'
    assert not any('loadEmployees' in d['message'] for d in f.dialogs), 'false success error'
    f.page.evaluate('async()=>{await toggleEmployeeUnitLink(32,"activate")}')
    assert f.page.evaluate('__EPI_APP_STATE__.employees.find(e=>e.id===32).local_unit_link_status') == 'active'
    f.fail_mutation = True
    old_bootstraps = sum(c['path']=='/api/bootstrap' for c in f.calls)
    f.page.evaluate('async()=>{await toggleEmployeeUnitLink(32,"deactivate")}')
    assert sum(c['path']=='/api/bootstrap' for c in f.calls) == old_bootstraps
    assert f.page.evaluate('__EPI_APP_STATE__.employees.find(e=>e.id===32).local_unit_link_status') == 'active'


def company_save(f):
    f.view('terceirizados')
    f.page.wait_for_function('__EPI_APP_STATE__.outsourcedCompanies.length===1')
    form = f.page.locator('#outsourced-company-form')
    form.locator('[name="legal_name"]').fill('Nova QA')
    form.locator('button[type="submit"]').click()
    expect(f.page.locator('#outsourced-companies-table')).to_contain_text('Nova QA', timeout=3000)
    assert f.page.locator('.view.active').get_attribute('id') == 'terceirizados-view', 'save navigated away'
    f.page.evaluate('startEditOutsourcedCompany(11)')
    form.locator('[name="legal_name"]').fill('Alterada QA')
    form.locator('button[type="submit"]').click()
    expect(f.page.locator('#outsourced-companies-table')).to_contain_text('Alterada QA')
    assert form.locator('[name="id"]').input_value() == '', 'old edit id survives save'
    assert f.mutations()[-1]['method'] == 'PUT'


def company_archive(f):
    f.actor.update(role='admin', operational_unit_id=5)
    f.permissions = ['dashboard:view', 'employees:view', 'employees:create_simplified', 'employees:update_simplified', 'units:view']
    f.companies[0]['local_status'] = 'active'
    f.page.evaluate('(actor)=>{__EPI_APP_STATE__.user=actor}', f.actor)
    f.page.evaluate('async()=>{await loadBootstrap()}')
    f.view('terceirizados')
    f.page.wait_for_function('__EPI_APP_STATE__.outsourcedCompanies.length===1')
    f.page.evaluate('async()=>{await toggleOutsourcedCompanyUnitLink(11,false)}')
    expect(f.page.locator('#outsourced-companies-table')).not_to_contain_text('Terceira QA')
    expect(f.page.locator('#outsourced-company-unit-archived-table')).to_contain_text('Terceira QA')
    f.page.evaluate('async()=>{await toggleOutsourcedCompanyUnitLink(11,true)}')
    expect(f.page.locator('#outsourced-companies-table')).to_contain_text('Terceira QA')
    f.actor.update(role='registry_admin')
    f.permissions = PERMISSIONS[:]
    f.companies, f.archived = [], [copy.deepcopy(COMPANY)]
    f.page.evaluate('(actor)=>{__EPI_APP_STATE__.user=actor}', f.actor)
    f.page.evaluate('async()=>{await loadBootstrap()}')
    f.view('terceirizados')
    f.tab('terceirizados', 'arquivados-empresas')
    f.page.locator('[data-archived-restore="outsourcedCompany:11"]').click()
    f.page.locator('.ds-confirm-ok').click()
    expect(f.page.locator('#outsourced-companies-table')).to_contain_text('Terceira QA', timeout=3000)


def active_view(f):
    return f.page.locator('.view.active').get_attribute('id')


def employee_archival(f):
    # Arquivar/desarquivar terceirizado (cadastro global) e colaborador CLT:
    # listas atualizadas sem sair da tela.
    f.view('terceirizados')
    f.page.wait_for_function('__EPI_APP_STATE__.outsourcedCompanies.length===1')
    f.tab('terceirizados', 'colaboradores')
    f.page.locator('[data-outsourced-employee-archive="32"]').click()
    f.page.locator('.ds-confirm-ok').click()
    f.page.wait_for_function('(__EPI_APP_STATE__.archivedOutsourcedEmployees||[]).some(e=>e.id===32)')
    expect(f.page.locator('#outsourced-employees-table')).not_to_contain_text('Tito QA')
    expect(f.page.locator('#archived-outsourced-employees-table')).to_contain_text('Tito QA')
    assert active_view(f) == 'terceirizados-view', 'archive navigated away'
    f.tab('terceirizados', 'arquivados-colaboradores')
    f.page.locator('[data-archived-restore="outsourcedEmployee:32"]').click()
    f.page.locator('.ds-confirm-ok').click()
    f.page.wait_for_function('__EPI_APP_STATE__.employees.some(e=>e.id===32)')
    expect(f.page.locator('#archived-outsourced-employees-table')).not_to_contain_text('Tito QA')
    expect(f.page.locator('#outsourced-employees-table')).to_contain_text('Tito QA')
    assert active_view(f) == 'terceirizados-view', 'restore navigated away'
    f.view('colaboradores')
    f.page.locator('[data-employee-archive="31"]').first.dispatch_event('click')
    f.page.locator('.ds-confirm-ok').click()
    f.page.wait_for_function('!__EPI_APP_STATE__.employees.some(e=>e.id===31)')
    assert active_view(f) == 'colaboradores-view', 'employee archive navigated away'


def purge(f):
    # Exclusão definitiva (retenção cumprida) de empresa e colaborador terceirizados.
    f.companies, f.archived = [], [dict(COMPANY, **ARCHIVED)]
    f.archived_employees = [dict(f.employees.pop(1), **ARCHIVED)]
    f.page.evaluate('async()=>{await loadBootstrap()}')
    f.view('terceirizados')
    for kind, record_id, tab in [('outsourcedCompany', 11, 'arquivados-empresas'), ('outsourcedEmployee', 32, 'arquivados-colaboradores')]:
        f.tab('terceirizados', tab)
        button = f.page.locator(f'[data-archived-purge="{kind}:{record_id}"]')
        button.click()
        f.page.locator('.ds-confirm-ok').click()
        expect(button).to_have_count(0)
        assert any(c['path'].endswith(f'/{record_id}/purge-confirm') for c in f.calls), kind + ' purge not confirmed'
        assert active_view(f) == 'terceirizados-view', kind + ' purge navigated away'


def editor_click(f):
    # Clique real em Editar na Lista; trocar de aba não apaga o rascunho; o PUT
    # leva os valores existentes, nunca campos vazios.
    f.view('colaboradores')
    f.tab('colaboradores', 'lista')
    f.page.locator('[data-employee-edit="31"]').first.click()
    form = f.page.locator('#employee-form')
    expect(form).to_be_visible()
    assert form.locator('[name="id"]').input_value() == '31', 'edit not armed'
    f.tab('colaboradores', 'lista')
    f.tab('colaboradores', 'cadastro')
    for key in ['name', 'cpf', 'employee_id_code', 'sector']:
        expect(form.locator('[name="' + key + '"]')).to_have_value(str(EMPLOYEE[key]))
    form.locator('[name="sector"]').fill('Manutencao QA')
    form.locator('button[type="submit"]').click()
    f.page.wait_for_function('document.getElementById("employee-form").dataset.submitting!=="1"')
    request = f.mutations()[-1]
    assert request['method'] == 'PUT' and request['path'] == '/api/employees/31'
    for key in ['name', 'cpf', 'employee_id_code', 'email', 'whatsapp', 'role_name', 'schedule_type', 'admission_date']:
        assert request['body'][key] == EMPLOYEE[key], key + ' lost on update'
    assert request['body']['sector'] == 'Manutencao QA'
    assert active_view(f) == 'colaboradores-view', 'save navigated away'


def editor(f):
    # Cross-module programmatic entry exercises the F5-B reset after Edit.
    f.view('dashboard')
    f.page.evaluate('startEditEmployee(31)')
    form = f.page.locator('#employee-form')
    for key, value in EMPLOYEE.items():
        field = form.locator('[name="' + key + '"]')
        if field.count():
            expect(field).to_have_value(str(value))
    expect(form.locator('[name="legal_entity_id"]')).to_be_disabled()
    f.page.screenshot(path=str(f.evidence_dir / (f.locale + '-editor-filled.png')))
    assert form.is_visible(), 'edit did not focus registration tab'
    f.page.evaluate('startEditEmployee(31)')  # same-module path too
    form.locator('[name="name"]').fill('Ana Alterada QA')
    form.locator('button[type="submit"]').click()
    f.page.wait_for_function('!document.getElementById("employee-form").dataset.submitting || document.getElementById("employee-form").dataset.submitting==="0"')
    request = f.mutations()[-1]
    assert request['method']=='PUT' and request['path']=='/api/employees/31'
    for key in ['cpf', 'employee_id_code', 'email', 'whatsapp', 'preferred_contact_channel', 'sector', 'role_name', 'schedule_type', 'admission_date']:
        assert request['body'][key] == EMPLOYEE[key], key + ' lost on update'
    assert request['body']['company_id']=='901' and request['body']['unit_id']=='5'
    assert 'legal_entity_id' not in request['body'], 'immutable CNPJ sent'
    assert form.locator('[name="id"]').input_value() == ''
    expect(form.locator('[name="legal_entity_id"]')).to_be_enabled()
    f.view('colaboradores')
    f.page.evaluate('startEditEmployee(31)')
    f.view('dashboard')
    f.view('colaboradores')
    assert form.locator('[name="id"]').input_value() == '', 'stale edit id on reentry'


def access_and_legacy(f):
    form = f.page.locator('#employee-form')
    # Archived home unit is absent from bootstrap options; existing arbitrary
    # schedules and inactive CNPJ still belong to this scoped employee.
    f.employees[0].update(unit_id=9, unit_name='Unidade arquivada QA', schedule_type='7x7')
    f.page.evaluate('async()=>{await loadBootstrap()}')
    f.page.evaluate('()=>{__EPI_APP_STATE__.legalEntities[0].active=0}')
    f.page.evaluate('startEditEmployee(31)')
    expect(form.locator('[name="unit_id"]')).to_have_value('9')
    expect(form.locator('[name="schedule_type"]')).to_have_value('7x7')
    expect(form.locator('[name="legal_entity_id"]')).to_have_value('44')
    expect(form.locator('[name="legal_entity_id"]')).to_be_disabled()
    f.view('dashboard')
    f.view('colaboradores')
    # No foreign company row can arm the editor, even if stale state contains it.
    f.page.evaluate('(record)=>__EPI_APP_STATE__.employees.push(record)', dict(EMPLOYEE, id=99, company_id=902, name='Foreign QA'))
    f.page.evaluate('startEditEmployee(99)')
    assert form.locator('[name="id"]').input_value() == ''
    for role in ['admin', 'user', 'buyer', 'employee']:
        f.page.evaluate('(role)=>{__EPI_APP_STATE__.user.role=role;__EPI_APP_STATE__.permissions=["employees:view","employees:update"]}', role)
        f.page.evaluate('startEditEmployee(31)')
        assert form.locator('[name="id"]').input_value() == '', role + ' armed full editor'
    f.page.evaluate('()=>{__EPI_APP_STATE__.user.role="registry_admin";__EPI_APP_STATE__.permissions=["employees:view"]}')
    f.page.evaluate('startEditEmployee(31)')
    assert form.locator('[name="id"]').input_value() == ''
    f.page.evaluate('async()=>{await toggleEmployeeUnitLink(32,"activate")}')
    assert not f.mutations(), 'permission denied operation reached network'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/fix-colab-terc-browser'))
    parser.add_argument('--locales', nargs='+', default=LOCALES)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT / 'static')))
    Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    results = []
    with sync_playwright() as playwright:
        options = dict(headless=True, args=['--no-sandbox'])
        if os.environ.get('CHROMIUM_EXECUTABLE'):
            options['executable_path'] = os.environ['CHROMIUM_EXECUTABLE']
        browser = playwright.chromium.launch(**options)
        for locale in args.locales:
            for scenario in [links, company_save, company_archive, employee_archival, purge, editor, editor_click,
                             access_and_legacy]:
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
                                  blocked_external_requests=fixture.external)
                    page.screenshot(path=str(args.output / f'{locale}-{scenario.__name__}.png'))
                    results.append(result)
                    print(f"{locale} {scenario.__name__}: {result['status']} {result.get('error','')[:200]}", flush=True)
                    context.close()
        browser.close()
    server.shutdown()
    (args.output / 'results.json').write_text(json.dumps(results, indent=2, ensure_ascii=False) + '\n')
    return int(any(result['status'] != 'passed' for result in results))


if __name__ == '__main__':
    raise SystemExit(main())
