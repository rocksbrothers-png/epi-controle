"""SECURITY-CSP-V1 — Chromium no fluxo REAL: SPA servida pelo app.py (com a CSP aplicada) + banco local.

Diferente de security_csp_v1.py (API sintética), aqui o cabeçalho vem do próprio app.py
e o login, o bootstrap e as telas falam com o servidor de verdade.

Pré-requisitos (não roda no CI; é a evidência da demanda):
  * app.py servindo em --base, fora de produção (CSP_MODE padrão = enforce), apontando para
    um PostgreSQL LOCAL e descartável — o script só aceita --base em localhost/127.0.0.1;
  * um usuário Master criado pelo bootstrap do próprio app (INITIAL_MASTER_USERNAME/PASSWORD).

Por idioma (5): confere os cabeçalhos por superfície, faz login pelo formulário real,
navega por todas as telas disponíveis ao perfil e falha se houver violação de CSP,
erro de página ligado à CSP ou envio nativo do formulário (senha na URL).

python scripts/browser/security_csp_v1_realflow.py --base http://127.0.0.1:18081 \
    --username master.teste --password 'Master#Teste1' --output /tmp/security-csp-v1-realflow
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

LOCALES = ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO']
VIEWS = ['dashboard', 'colaboradores', 'gestao-colaborador', 'unidades', 'epis', 'estoque', 'entregas', 'fichas',
         'relatorios', 'compras', 'usuarios', 'terceirizados', 'empresas', 'configuracao', 'biblioteca-seguranca',
         'avaliacoes', 'migracao', 'comercial', 'cnpjs']
EXPECTED = {
    '/': 'Content-Security-Policy',
    '/index.html': 'Content-Security-Policy',
    '/app/': 'Content-Security-Policy-Report-Only',
    '/pagamento': 'Content-Security-Policy-Report-Only',
    '/fornecedor/token-qa': 'Content-Security-Policy',
}
RECORDER = """
window.__csp = [];
document.addEventListener('securitypolicyviolation', (e) => {
  window.__csp.push({directive: e.effectiveDirective || e.violatedDirective, blocked: e.blockedURI,
                     sample: (e.sample || '').slice(0, 60)});
}, true);
"""


def headers(base):
    found = {}
    for path, expected in EXPECTED.items():
        try:
            response = urllib.request.urlopen(base + path)  # noqa: S310 — base local verificada
            items = response.headers.items()
        except urllib.error.HTTPError as error:  # /app/ sem build do Flutter responde 404, com cabeçalho
            items = error.headers.items()
        csp = [(name, value) for name, value in items if name.lower().startswith('content-security-policy')]
        found[path] = dict(ok=len(csp) == 1 and csp[0][0] == expected, headers=[n for n, _ in csp])
    spa = dict(urllib.request.urlopen(base + '/').headers.items()).get('Content-Security-Policy', '')  # noqa: S310
    script_src = next((part.split()[1:] for part in spa.split(';') if part.split()[:1] == ['script-src']), [])
    found['spa_script_src_strict'] = dict(ok="'unsafe-inline'" not in script_src and "'unsafe-eval'" not in script_src,
                                          script_src=script_src)
    return found


def run_locale(browser, base, locale, username, password):
    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, service_workers='block', locale=locale)
    context.add_init_script(RECORDER)
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    try:
        page.goto(base + '/', wait_until='load')
        page.fill('#login-username', username)
        page.fill('#login-password', password)
        page.locator('#login-form button[type="submit"]').click()
        page.wait_for_function('() => !!(globalThis.__EPI_APP_STATE__ && __EPI_APP_STATE__.user)', timeout=20000)
        page.wait_for_load_state('networkidle')
        page.evaluate('(locale) => EpiI18n.setLang(locale)', locale)
        page.wait_for_timeout(300)
        visited = []
        for view in VIEWS:
            if not page.evaluate(f'!!document.getElementById("{view}-view")'):
                continue
            page.evaluate('(view) => { try { showView(view, {partial: false}); } catch (e) { /* perfil */ } }', view)
            page.wait_for_timeout(250)
            tabs = page.locator(f'nav[data-vtabs="{view}"] [data-vtab]')
            for index in range(tabs.count()):
                if tabs.nth(index).is_visible():
                    tabs.nth(index).click()
                    page.wait_for_timeout(150)
            visited.append(view)
        page.wait_for_load_state('networkidle')
        violations = page.evaluate('window.__csp')
        csp_errors = [e for e in errors if 'Content Security Policy' in e]
        no_password_in_url = 'password' not in page.url and password not in page.url
        ok = not violations and not csp_errors and no_password_in_url and len(visited) >= 10
        return dict(locale=locale, status='passed' if ok else 'failed', visited=visited, violations=violations,
                    csp_errors=csp_errors, lang=page.evaluate('EpiI18n.lang'))
    finally:
        context.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--base', required=True)
    parser.add_argument('--username', required=True)
    parser.add_argument('--password', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--locales', nargs='+', default=LOCALES)
    args = parser.parse_args()
    if urlparse(args.base).hostname not in ('127.0.0.1', 'localhost'):
        raise SystemExit('Recusado: use só um app.py local, apontando para banco descartável.')
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    result = dict(headers=headers(args.base), locales=[])
    failed = not all(item['ok'] for item in result['headers'].values())
    print('cabeçalhos', {k: v['ok'] for k, v in result['headers'].items()})
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE') or None)
        for locale in args.locales:
            item = run_locale(browser, args.base, locale, args.username, args.password)
            failed |= item['status'] != 'passed'
            result['locales'].append(item)
            print(locale, item['status'], 'telas=', len(item['visited']), 'violações=', len(item['violations']),
                  'idioma=', item['lang'])
        browser.close()
    (out / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding='utf-8')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
