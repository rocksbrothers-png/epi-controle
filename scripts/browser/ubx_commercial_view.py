"""UBX Comercial, fatia C3 — Chromium: SPA real + API sintética interceptada; nunca abre banco.

Equivalência, no navegador real e nos 5 idiomas, da interface comercial depois
da extração (static/js/modules/commercial/ui/commercial-view.js e
commercial-contract-view.js) com o comportamento de ANTES da C3.

O "antes" é uma referência gravada (static/js/test/fixtures/ubx-commercial-c3-browser.json),
produzida rodando ESTE MESMO roteiro contra o static/ da main anterior à C3
(`--record --static <worktree da main>/static`). Tudo pela interface real (os
mesmos listeners do produto), com o relógio do navegador fixo (vencimentos e
datas não dependem do dia em que o teste roda):

  abrir o Comercial e o contrato pelo cartão da empresa; alternar as abas;
  filtrar por situação, responsável e período e limpar; trocar de empresa no
  seletor; trocar plano, limite e aditivo (prévia); salvar a empresa e os
  parâmetros; salvar rascunho, gerar, assinar, enviar PDF assinado, registrar
  e-mail, abrir PDF, visualizar e baixar; exportar CSV e Excel e imprimir;
  suspender pelo cartão; repetir gravações com a API negando (403); sair para
  outra tela e voltar; abrir pelo botão da tela Empresas; trocar o idioma sem
  recarregar; trocar de tenant (outra carteira de empresas) e de usuário (perfil
  sem acesso ao Comercial) sem recarregar a página.

Depois de cada passo fotografa a tela Comercial: o HTML inteiro de
#comercial-view e o valor/marcação/estado de cada campo. Compara com a
referência, idioma a idioma:
1. as fotografias, passo a passo (hash SHA-256 de cada uma; o --output guarda as
   fotografias completas para diagnóstico);
2. as requisições comerciais (/api/commercial*, /api/companies*), na mesma ordem
   (método, caminho, query e corpo JSON), e as recargas em segundo plano como
   conjunto (correm em paralelo e mudam de ordem até na mesma versão);
3. abas abertas, conteúdo impresso, arquivos baixados e diálogos;
4. as requisições externas (bloqueadas pelo harness);
e exige nenhum erro de página e nenhuma marcação executada. Cada fotografia só é
tirada com a rede parada (nenhuma requisição /api em voo), para não depender do
tempo de resposta.

python scripts/browser/ubx_commercial_view.py --output /tmp/ubx-c3
python scripts/browser/ubx_commercial_view.py --record --static /caminho/da/main/static
CHROMIUM_EXECUTABLE=/usr/bin/chromium seleciona um navegador já instalado.
"""
import argparse
import hashlib
import json
import os
import sys
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fix_colab_terc as base
import i18n_commercial as commercial
import ubx_commercial_integrations as c2

ROOT = base.ROOT
LOCALES = base.LOCALES
GOLDEN = ROOT / 'static/js/test/fixtures/ubx-commercial-c3-browser.json'
FIXED_NOW = '2026-11-15T12:00:00'
XSS = commercial.XSS
LOGS = [
    {'id': 2, 'company_id': 902, 'company_name': 'Cliente Dois', 'action_label': 'Suspensão', 'actor_name': 'Bruno',
     'created_at': '2026-09-01T08:00:00', 'summary': 'Suspensa', 'details': []},
    {'id': 3, 'company_id': 901, 'company_name': 'Empresa QA', 'action_label': 'Criação', 'actor_name': 'Bruno',
     'created_at': '2026-11-02T23:59:59', 'summary': 'Criada; "nova"',
     'details': [{'field': 'user_limit', 'before': '', 'after': '10'}]},
]
EXTRA_COMPANY = {'id': 903, 'name': 'Terceira & Cia', 'legal_name': 'Terceira Ltda', 'cnpj': '33444555000166', 'active': 0,
                 'license_status': 'expired', 'plan_name': 'enterprise', 'user_limit': 300, 'user_count': 12,
                 'monthly_value': 9000.5, 'contract_start': '2025-01-01', 'contract_end': '2026-11-12'}
# Popup de impressão e abas: registrados (nada abre de verdade).
INIT = """
window.__opens = []; window.__printed = [];
window.open = function (url, target, features) {
  window.__opens.push([String(url), String(target), String(features || '')]);
  if (String(url) !== '') { return null; }
  const doc = { readyState: 'complete', html: '', open() {}, write(h) { this.html += h; }, close() { window.__printed.push(this.html); } };
  return { document: doc, focus() {}, print() {}, addEventListener() {} };
};
"""
SNAPSHOT = """() => {
  const root = document.getElementById('comercial-view');
  const fields = [...root.querySelectorAll('input, select, textarea')].map((el) => ({
    key: el.id || el.name || el.outerHTML.slice(0, 60),
    value: el.type === 'file' ? (el.files ? el.files.length : 0) : (el.type === 'checkbox' || el.type === 'radio') ? el.checked : el.value,
    disabled: el.disabled,
    options: el.tagName === 'SELECT' ? el.innerHTML : null
  }));
  return { active: root.classList.contains('active'), html: root.innerHTML, fields, xss: window.__xss || 0 };
}"""


class Fixture(c2.Fixture):
    def __init__(self, *args):
        super().__init__(*args)
        self.company_list[0]['contract_end'] = '2026-11-20'  # vence em 5 dias no relógio fixo
        self.company_list.append(dict(EXTRA_COMPANY))
        self.downloads = []
        # Requisições /api em voo: a fotografia só é tirada com a rede parada (sem corrida de tempo).
        self.pending = set()
        is_api = lambda r: urlsplit(r.url).path.startswith(('/api/', '/health'))
        self.page.on('request', lambda r: self.pending.add(r) if is_api(r) else None)
        self.page.on('requestfinished', lambda r: self.pending.discard(r))
        self.page.on('requestfailed', lambda r: self.pending.discard(r))

    def route(self, route):
        request = route.request
        path = urlsplit(request.url).path
        if request.method == 'POST' and path.startswith('/api/commercial-contract/') and not self.fail_mutation:
            # Cada ação devolve um contrato diferente: troca de ordem entre gravar o estado e renderizar aparece.
            action = path.rsplit('/', 1)[1]
            self.calls.append({'method': 'POST', 'path': path, 'query': urlsplit(request.url).query,
                               'body': json.loads(request.post_data or '{}')})
            return route.fulfill(json={'ok': True, 'contract': dict(c2.CONTRACT, contract_number=f'CT-901-{action}', status=action,
                                                                  events=[{'event_type': action, 'created_at': '2026-11-15T10:00:00'}])})
        if path == '/api/bootstrap':
            original = route.fulfill

            def fulfill(**kwargs):
                payload = kwargs.get('json') or {}
                payload['company_audit_logs'] = list(payload.get('company_audit_logs') or []) + LOGS
                kwargs['json'] = payload
                return original(**kwargs)
            route.fulfill = fulfill
        return super().route(route)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()


class Recorder:
    def __init__(self, f):
        self.f, self.steps = f, []

    def shot(self, label, wait=300):
        self.f.page.wait_for_timeout(wait)
        quiet = 0
        for _ in range(100):  # até ~5 s: rede parada por 3 leituras seguidas, depois a renderização
            quiet = quiet + 1 if not self.f.pending else 0
            if quiet >= 3:
                break
            self.f.page.wait_for_timeout(50)
        assert not self.f.pending, f'{label}: requisições ainda em voo: {[r.url for r in self.f.pending]}'
        self.f.page.wait_for_timeout(100)
        self.steps.append({'label': label, 'snapshot': self.f.page.evaluate(SNAPSHOT)})


def click(f, selector, wait=250):
    f.page.evaluate('(s) => document.querySelector(s).click()', selector)
    f.page.wait_for_timeout(wait)


def change(f, selector, value):
    f.page.evaluate("""([s, v]) => { const el = document.querySelector(s); el.value = v;
      el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); }""", [selector, value])
    f.page.wait_for_timeout(200)


def download(f, selector):
    with f.page.expect_download() as info:
        f.page.evaluate('(s) => document.querySelector(s).click()', selector)
    item = info.value
    f.downloads.append({'name': item.suggested_filename, 'content': Path(item.path()).read_text(encoding='utf-8')})


def contract_actions(f, rec, suffix):
    click(f, '#commercial-save-contract-management')
    rec.shot(f'salvar rascunho{suffix}')
    click(f, '#commercial-generate-contract')
    rec.shot(f'gerar{suffix}')
    f.page.evaluate("""() => {
      document.getElementById('commercial-signature-name').value = 'Ana "QA" <b>';
      document.getElementById('commercial-signature-data').value = 'data:image/png;base64,QUJD';
    }""")
    click(f, '#commercial-sign-contract')
    rec.shot(f'assinar{suffix}')
    f.page.set_input_files('#commercial-signed-file', files=[{'name': 'assinado <1>.pdf', 'mimeType': 'application/pdf',
                                                            'buffer': b'%PDF-1.4\n%QA\n'}])
    click(f, '#commercial-upload-signed')
    rec.shot(f'enviar PDF assinado{suffix}')
    f.page.evaluate("""() => {
      document.getElementById('commercial-email-to').value = 'cliente@exemplo.test';
      document.getElementById('commercial-email-subject').value = 'Contrato & aditivo';
      document.getElementById('commercial-email-body').value = 'Linha 1\\nLinha "2"';
    }""")
    click(f, '#commercial-send-contract-email')
    rec.shot(f'registrar e-mail{suffix}')


def actions(f, rec):
    page = f.page
    page.evaluate('async()=>{await loadBootstrap()}')
    f.view('comercial')
    f.tab('comercial', 'contratos')
    rec.shot('abrir o Comercial')
    click(f, '#commercial-summary [data-company-commercial="901"]')
    page.wait_for_function("document.getElementById('commercial-contract-status')?.textContent.length>0")
    rec.shot('abrir contrato pelo cartão')
    f.tab('comercial', 'config')
    rec.shot('aba Marca & Planos')
    f.tab('comercial', 'contratos')
    rec.shot('aba Contratos & Consumo')

    change(f, '#commercial-filter-status', 'suspended')
    rec.shot('filtro: suspensas')
    change(f, '#commercial-filter-actor', 'Bruno')
    change(f, '#commercial-filter-date-from', '2026-09-01')
    change(f, '#commercial-filter-date-to', '2026-10-31')
    rec.shot('filtro: responsável e período')
    for sel in ('#commercial-filter-status', '#commercial-filter-actor', '#commercial-filter-date-from', '#commercial-filter-date-to'):
        change(f, sel, '')
    rec.shot('filtros limpos')

    change(f, '#commercial-company', '902')
    rec.shot('trocar empresa no seletor')
    change(f, '#commercial-company', '901')
    change(f, '#commercial-form [name="plan_name"]', 'enterprise')
    change(f, '#commercial-form [name="user_limit"]', '250')
    click(f, '#commercial-form [name="addendum_enabled"]')
    rec.shot('prévia: plano, limite e aditivo')
    page.evaluate("document.getElementById('commercial-form').requestSubmit()")
    rec.shot('salvar empresa', wait=500)
    change(f, '#commercial-settings-form [name="unit_price"]', '50')
    page.evaluate("document.getElementById('commercial-settings-form').requestSubmit()")
    rec.shot('salvar parâmetros', wait=500)

    contract_actions(f, rec, '')
    for selector in ('#commercial-contract-pdf', '#commercial-view-contract', '#commercial-download-contract'):
        click(f, selector)
    rec.shot('abrir, visualizar e baixar o contrato')
    download(f, '#commercial-export')
    download(f, '#commercial-export-excel')
    click(f, '#commercial-print')
    rec.shot('exportar CSV/Excel e imprimir')
    click(f, '#commercial-summary [data-commercial-toggle="901"]', wait=400)
    rec.shot('suspender pelo cartão', wait=400)

    f.fail_mutation = True
    contract_actions(f, rec, ' (403)')
    page.evaluate("document.getElementById('commercial-form').requestSubmit()")
    rec.shot('salvar empresa (403)', wait=400)
    page.evaluate("document.getElementById('commercial-settings-form').requestSubmit()")
    rec.shot('salvar parâmetros (403)', wait=400)
    f.fail_mutation = False

    click(f, '.menu-link[data-view="dashboard"]', wait=400)
    click(f, '.menu-link[data-view="comercial"]', wait=400)
    f.tab('comercial', 'contratos')
    rec.shot('sair para o Dashboard e voltar', wait=400)
    f.view('empresas')
    click(f, '#empresas-view [data-company-commercial="902"]', wait=400)
    rec.shot('abrir pelo botão da tela Empresas', wait=400)

    other = 'fr-FR' if f.locale != 'fr-FR' else 'nb-NO'
    page.evaluate('(l)=>EpiI18n.setLang(l,{persist:false})', other)
    page.wait_for_function('(l)=>EpiI18n.lang===l', arg=other)
    rec.shot('trocar o idioma sem recarregar')
    page.evaluate('(l)=>EpiI18n.setLang(l,{persist:false})', f.locale)
    page.wait_for_function('(l)=>EpiI18n.lang===l', arg=f.locale)
    rec.shot('voltar ao idioma')

    f.company_list[:] = [dict(EXTRA_COMPANY, id=911, name='Tenant B — Alfa'), dict(EXTRA_COMPANY, id=912, name='Tenant B <i>Beta</i>',
                                                                                  active=1, license_status='active', contract_end='2026-12-01')]
    page.evaluate('async()=>{await loadBootstrap()}')
    rec.shot('trocar de tenant sem recarregar', wait=500)
    f.actor.update(role='general_admin', company_id=911)
    page.evaluate('async()=>{await loadBootstrap()}')
    rec.shot('trocar para usuário sem acesso ao Comercial', wait=500)


def run_locale(origin, browser, locale):
    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, service_workers='block', locale=locale, accept_downloads=True)
    context.add_init_script(INIT)
    page = context.new_page()
    page.clock.set_fixed_time(FIXED_NOW)
    page.set_default_timeout(8000)
    f = Fixture(page, origin, locale)
    f.fail_mutation = False
    rec = Recorder(f)
    try:
        f.open()
        start_calls, start_dialogs = len(f.calls), len(f.dialogs)
        actions(f, rec)
        observed = {
            'steps': rec.steps,
            'calls': [c for c in f.calls[start_calls:] if not c['path'].startswith('/api/i18n/')],
            'opens': page.evaluate('window.__opens'),
            'printed': page.evaluate('window.__printed'),
            'downloads': f.downloads,
            'dialogs': [d['message'] for d in f.dialogs[start_dialogs:]],
            'external': sorted(set(f.external)),
        }
        assert not f.errors, f'page errors: {f.errors}'
        assert all(step['snapshot']['xss'] == 0 for step in rec.steps), 'marcação executada'
        return observed
    finally:
        context.close()


def split(observed):
    """Fotografias: hash por passo, na ordem. Chamadas comerciais: ordem estrita.
    Recargas em segundo plano (fichas, estoque, regras, /health...) disparadas pelo
    loadBootstrap: conjunto com multiplicidade."""
    prefixes = c2.COMMERCIAL_PREFIXES
    return {
        'steps': [[s['label'], digest(s['snapshot'])] for s in observed['steps']],
        'commercial_calls': [c for c in observed['calls'] if c['path'].startswith(prefixes)],
        'background_calls': sorted(json.dumps(c, sort_keys=True, ensure_ascii=False) for c in observed['calls']
                                   if not c['path'].startswith(prefixes)),
        'opens': observed['opens'], 'printed': [digest(p) for p in observed['printed']],
        'downloads': [[d['name'], digest(d['content'])] for d in observed['downloads']],
        'dialogs': observed['dialogs'], 'external': observed['external'],
    }


def check_coverage(observed):
    seen = {(c['method'], c['path']) for c in observed['calls']}
    expected = {('GET', '/api/commercial-contract'), ('POST', '/api/commercial-contract/save'),
                ('POST', '/api/commercial-contract/generate'), ('POST', '/api/commercial-contract/sign'),
                ('POST', '/api/commercial-contract/upload-signed'), ('POST', '/api/commercial-contract/send-email'),
                ('POST', '/api/commercial-settings'), ('PUT', '/api/companies/901')}
    assert not expected - seen, f'endpoints não exercitados: {sorted(expected - seen)}'
    assert len(observed['printed']) == 1 and len(observed['downloads']) == 2, (len(observed['printed']), observed['downloads'])
    # Um clique, uma requisição: nenhum listener duplicado.
    generates = [c for c in observed['calls'] if c['path'] == '/api/commercial-contract/generate']
    assert len(generates) == 2, f'gerar: {len(generates)} requisições para 2 cliques'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/ubx-commercial-view'))
    parser.add_argument('--locales', nargs='+', default=LOCALES)
    parser.add_argument('--static', type=Path, default=ROOT / 'static', help='pasta static/ servida (padrão: a desta branch)')
    parser.add_argument('--record', action='store_true', help='grava a referência a partir de --static em vez de comparar')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(base.QuietHandler, directory=str(args.static)))
    Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    golden = {} if args.record else json.loads(GOLDEN.read_text(encoding='utf-8'))
    results = []
    with sync_playwright() as playwright:
        options = {'headless': True, 'args': ['--no-sandbox']}
        if os.environ.get('CHROMIUM_EXECUTABLE'):
            options['executable_path'] = os.environ['CHROMIUM_EXECUTABLE']
        browser = playwright.chromium.launch(**options)
        for locale in args.locales:
            result = {'locale': locale, 'scenario': 'equivalence', 'status': 'passed'}
            try:
                observed = run_locale(origin, browser, locale)
                (args.output / f'{locale}-observed.json').write_text(json.dumps(observed, indent=1, ensure_ascii=False) + '\n')
                check_coverage(observed)
                current = split(observed)
                if args.record:
                    golden[locale] = current
                else:
                    for key in current:
                        if current[key] != golden[locale][key]:
                            diffs = [i for i, (a, b) in enumerate(zip(current[key], golden[locale][key])) if a != b]
                            raise AssertionError(f'{key} difere da referência (posições {diffs[:5]}, tamanhos {len(current[key])}/'
                                                 f'{len(golden[locale][key])}): atual {json.dumps(current[key][diffs[0]] if diffs else current[key], ensure_ascii=False)[:700]} '
                                                 f'antes {json.dumps(golden[locale][key][diffs[0]] if diffs else golden[locale][key], ensure_ascii=False)[:700]}')
                result.update(steps=len(observed['steps']), calls=len(observed['calls']), dialogs=len(observed['dialogs']))
            except Exception as error:  # noqa: BLE001 — registra a falha do cenário e segue
                result.update(status='failed', error=str(error))
            results.append(result)
            print(f"{locale} equivalence: {result['status']} {result.get('error', '')[:900]}", flush=True)
        browser.close()
    server.shutdown()
    if args.record and all(r['status'] == 'passed' for r in results):
        GOLDEN.write_text(json.dumps(golden, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (args.output / 'results.json').write_text(json.dumps(results, indent=2, ensure_ascii=False) + '\n')
    return int(any(result['status'] != 'passed' for result in results))


if __name__ == '__main__':
    raise SystemExit(main())
