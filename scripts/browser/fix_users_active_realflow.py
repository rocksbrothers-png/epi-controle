"""FIX-USERS-ACTIVE-V1 — Chromium no fluxo REAL: SPA + app.py + PostgreSQL local descartável.

Diferente dos outros harnesses (API sintética), este fala com o servidor de verdade,
porque o defeito estava na combinação formulário → PUT /api/users/{id} → banco.

Pré-requisitos (nada disso roda no CI; é a evidência da demanda):
  * PostgreSQL LOCAL e descartável, com os dados fictícios de `--seed` (ver abaixo);
  * app.py servindo em --base, apontando para o MESMO banco;
  * DATABASE_URL só é aceito em localhost/127.0.0.1 — o script recusa qualquer outro host
    para nunca escrever em banco compartilhado.

Dados fictícios esperados (criados pelo próprio app via API pelo operador):
  Empresa A: geral.a (Adm. Geral), gestor.ativo.a (Gestor de EPI, ativo), gestor.inativo.a (inativo)
  Empresa B: geral.b (Adm. Geral)
  Senha de todos: --password.

Cenários por idioma (5):
  1. Adm. Geral edita o nome do usuário INATIVO pelo formulário → continua inativo;
  2. edita um usuário ATIVO → continua ativo;
  3. reativa pelo botão "Ativar Usuário" → ativo, com registro na trilha; desativa de novo;
  4. perfil sem permissão (Gestor de EPI) não reativa (PUT recusado);
  5. Adm. Geral de outra empresa não reativa (PUT recusado);
  6. cada resultado é conferido de novo após recarregar a página.
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
LOCALES = ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO']


def labels(locale):
    user = json.loads((ROOT / 'static/i18n' / f'{locale}.json').read_text(encoding='utf-8'))['user']
    return {'active': user['active'], 'inactive': user['inactive']}


class Db:
    def __init__(self, url):
        host = urlparse(url).hostname
        if host not in ('localhost', '127.0.0.1'):
            raise SystemExit(f'Recusado: DATABASE_URL aponta para {host!r}; use só banco local descartável.')
        self.url = url

    def one(self, sql):
        return subprocess.check_output(['psql', self.url, '-Atc', sql], text=True).strip()

    def user(self, username):
        row = self.one(f"select id, active, coalesce(linked_employee_id::text, ''), company_id from users where username = '{username}'")
        uid, active, linked, company = row.split('|')
        return {'id': uid, 'active': int(active), 'linked': linked, 'company_id': company}

    def audit_count(self, company_id, action):
        return int(self.one(f"select count(*) from company_audit_logs where company_id = {company_id} and action_type = '{action}'"))


def api_put(base, token, user_id, body):
    req = urllib.request.Request(f'{base}/api/users/{user_id}', method='PUT', data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'})
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status
    except urllib.error.HTTPError as err:
        return err.code


def api_set_language(base, username, password, locale):
    # O idioma pertence à identidade (preferências do usuário), não ao navegador.
    token = api_login(base, username, password)['token']
    req = urllib.request.Request(f'{base}/api/auth/me/preferences', method='PUT', data=json.dumps({'idioma': locale}).encode(),
                                 headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'})
    with urllib.request.urlopen(req) as resp:
        return resp.status


_TOKENS = {}


def api_login(base, username, password):
    # Um login por usuário na execução inteira: o servidor limita tentativas (HTTP 429).
    if username in _TOKENS:
        return _TOKENS[username]
    req = urllib.request.Request(f'{base}/api/login', method='POST', data=json.dumps({'username': username, 'password': password}).encode(),
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as resp:
        _TOKENS[username] = json.loads(resp.read())
    return _TOKENS[username]


class Ui:
    def __init__(self, browser, base, locale, password):
        self.context = browser.new_context(viewport={'width': 1440, 'height': 1000}, locale=locale, service_workers='block')
        self.page = self.context.new_page()
        self.base, self.password, self.locale = base, password, locale
        self.dialogs = []
        self.page.on('dialog', lambda d: (self.dialogs.append(d.message), d.accept()))
        self.puts = []
        self.page.on('request', lambda r: self.puts.append(json.loads(r.post_data or '{}'))
                     if r.method == 'PUT' and '/api/users/' in r.url else None)

    def login(self, username):
        p = self.page
        p.goto(self.base + '/')
        p.fill('#login-username', username)
        p.fill('#login-password', self.password)
        p.click('#login-form button[type=submit]')
        p.wait_for_selector('[data-view="usuarios"], [data-view="dashboard"]', state='visible', timeout=20000)
        self.close_onboarding()

    def close_onboarding(self):
        # Empresa de teste recém-criada: o assistente de implantação abre sozinho.
        self.page.wait_for_timeout(1200)
        if self.page.locator('#onboarding-wizard-modal.is-open').count():
            self.page.click('#onboarding-later')
            self.page.wait_for_selector('#onboarding-wizard-modal.is-open', state='detached', timeout=10000)

    def users_list(self):
        self.page.click('[data-view="usuarios"]')
        self.page.click('[data-vtabs="usuarios"] [data-vtab="lista"]')

    def status_cell(self, uid):
        self.page.wait_for_selector(f'#users-table tr:has([data-user-edit="{uid}"])', state='visible', timeout=20000)
        return self.page.locator(f'#users-table tr:has([data-user-edit="{uid}"]) td').nth(2).inner_text().strip()

    def reload_status(self, uid):
        self.page.reload()
        self.page.wait_for_selector('[data-view="usuarios"]', state='visible', timeout=20000)
        self.close_onboarding()
        self.users_list()
        return self.status_cell(uid)

    def edit_name(self, uid, name):
        p = self.page
        p.locator(f'[data-user-edit="{uid}"]').click()
        p.wait_for_function("document.querySelector('#user-form [name=full_name]').value !== ''")
        shown_link = p.eval_on_selector('#user-form [name=linked_employee_id]', 'e => e.value')
        p.fill('#user-form [name=full_name]', name)
        self.puts.clear()
        with p.expect_response(lambda r: r.request.method == 'PUT' and '/api/users/' in r.url, timeout=15000) as info:
            p.click('#user-form button[type=submit]')
        p.wait_for_timeout(800)
        return shown_link, info.value.status, dict(self.puts[-1]) if self.puts else {}

    def toggle(self, uid):
        with self.page.expect_response(lambda r: r.request.method == 'PUT' and '/api/users/' in r.url, timeout=15000) as info:
            self.page.locator(f'[data-user-toggle="{uid}"]').click()
        self.page.wait_for_timeout(800)
        return info.value.status

    def close(self):
        self.context.close()


def check(cond, message):
    if not cond:
        raise AssertionError(message)


def run_locale(browser, args, db, locale):
    lab = labels(locale)
    inativo, ativo = db.user('gestor.inativo.a'), db.user('gestor.ativo.a')
    db.one(f"update users set active = 0 where id = {inativo['id']}; update users set active = 1 where id = {ativo['id']}")
    steps = {}
    api_set_language(args.base, 'geral.a', args.password, locale)
    ui = Ui(browser, args.base, locale, args.password)
    try:
        ui.login('geral.a')
        check(ui.page.evaluate('EpiI18n.lang') == locale, f'idioma ativo {ui.page.evaluate("EpiI18n.lang")}')
        ui.users_list()
        check(ui.status_cell(inativo['id']) == lab['inactive'], 'lista inicial: inativo')
        # 1 + 6
        shown, status, body = ui.edit_name(inativo['id'], f'Gestor Inativo A ({locale})')
        check(status == 200, f'salvar edição do inativo: HTTP {status}')
        check('active' not in body, f'corpo da edição traz active: {body.get("active")!r}')
        check(shown == inativo['linked'], f'formulário mostra o vínculo {shown!r} (esperado {inativo["linked"]!r})')
        check(db.user('gestor.inativo.a')['active'] == 0, 'banco: inativo continuou inativo')
        check(ui.reload_status(inativo['id']) == lab['inactive'], 'após recarregar: inativo')
        steps['1_editar_inativo'] = 'inativo mantido (banco e tela após recarregar)'
        # 2 + 6
        shown, status, body = ui.edit_name(ativo['id'], f'Gestor Ativo A ({locale})')
        check(status == 200 and 'active' not in body, 'salvar edição do ativo')
        check(db.user('gestor.ativo.a')['active'] == 1, 'banco: ativo continuou ativo')
        check(ui.reload_status(ativo['id']) == lab['active'], 'após recarregar: ativo')
        steps['2_editar_ativo'] = 'ativo mantido'
        # 3 + 6
        before = db.audit_count(inativo['company_id'], 'user_reactivate')
        check(ui.toggle(inativo['id']) == 200, 'reativar pelo botão')
        check(db.user('gestor.inativo.a')['active'] == 1, 'banco: reativado pelo botão')
        check(db.audit_count(inativo['company_id'], 'user_reactivate') == before + 1, 'trilha: reativação registrada')
        check(ui.reload_status(inativo['id']) == lab['active'], 'após recarregar: reativado')
        check(ui.toggle(inativo['id']) == 200 and db.user('gestor.inativo.a')['active'] == 0, 'desativar de novo pelo botão')
        check(ui.reload_status(inativo['id']) == lab['inactive'], 'após recarregar: desativado')
        steps['3_reativar_explicito'] = 'reativado e desativado pelo botão, com trilha'
    finally:
        ui.close()
    body = {'actor_user_id': 0, 'username': 'gestor.inativo.a', 'full_name': 'X', 'password': '', 'role': 'user',
            'company_id': int(inativo['company_id']), 'linked_employee_id': int(inativo['linked']), 'active': 1}
    # 4
    sem_perm = api_login(args.base, 'gestor.ativo.a', args.password)
    status = api_put(args.base, sem_perm['token'], inativo['id'], {**body, 'actor_user_id': sem_perm['user']['id']})
    check(status in (400, 401, 403) and db.user('gestor.inativo.a')['active'] == 0, f'perfil sem permissão: HTTP {status}')
    steps['4_sem_permissao'] = f'recusado (HTTP {status}), continua inativo'
    # 5
    outra = api_login(args.base, 'geral.b', args.password)
    status = api_put(args.base, outra['token'], inativo['id'], {**body, 'actor_user_id': outra['user']['id']})
    check(status in (400, 401, 403) and db.user('gestor.inativo.a')['active'] == 0, f'outra empresa: HTTP {status}')
    steps['5_outra_empresa'] = f'recusado (HTTP {status}), continua inativo'
    return steps


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--base', default='http://127.0.0.1:18080')
    parser.add_argument('--password', required=True)
    parser.add_argument('--locales', nargs='+', default=LOCALES)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    db = Db(os.environ.get('DATABASE_URL', ''))
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    results, failed = [], False
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE') or None)
        for locale in args.locales:
            result = {'locale': locale}
            try:
                result.update(status='passed', steps=run_locale(browser, args, db, locale))
            except Exception as exc:  # noqa: BLE001 — relatório por idioma
                failed = True
                result.update(status='failed', error=str(exc).splitlines()[0])
            results.append(result)
            print(locale, result['status'], result.get('error', ''))
        browser.close()
    (out / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding='utf-8')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
