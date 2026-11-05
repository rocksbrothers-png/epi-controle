"""UBX Comercial, fatia C2 — Chromium: SPA real + API sintética interceptada; nunca abre banco.

Equivalência, no navegador real e nos 5 idiomas, das integrações comerciais
depois da extração (static/js/modules/commercial/integrations/commercial-api.js)
com o comportamento de ANTES da C2.

O "antes" é uma referência gravada (static/js/test/fixtures/ubx-commercial-c2-browser.json),
produzida rodando ESTE MESMO roteiro contra o static/ da main anterior à C2
(`--record --static <worktree da main>/static`). Os chamadores comerciais do
app.js são `async function` de bloco (sem Annex B: não são globais), então o
roteiro aciona tudo pela interface real — os mesmos listeners do produto:

  abrir o contrato da empresa (GET), salvar rascunho, gerar, assinar, enviar o
  PDF assinado (arquivo real no <input type=file>), registrar envio por e-mail,
  abrir o PDF, visualizar e baixar o arquivo gerado, suspender a empresa pelo
  cartão, salvar o formulário do contrato, salvar os parâmetros comerciais e o
  botão "ver contrato" dos detalhes da Empresa — e depois tudo de novo com a API
  negando as gravações (403).

Compara com a referência, idioma a idioma:
1. as requisições comerciais (/api/commercial*, /api/companies*), na mesma ordem
   (método, caminho, query e corpo JSON), e as recargas em segundo plano do
   bootstrap como conjunto (correm em paralelo e mudam de ordem até na mesma versão);
2. as abas abertas (URL e alvo);
3. os diálogos (textos no idioma ativo), inclusive nos erros;
4. as mesmas requisições externas (bloqueadas pelo harness);
e exige nenhum erro de página.

python scripts/browser/ubx_commercial_integrations.py --output /tmp/ubx-c2
python scripts/browser/ubx_commercial_integrations.py --record --static /caminho/da/main/static
CHROMIUM_EXECUTABLE=/usr/bin/chromium seleciona um navegador já instalado.
"""
import argparse
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

ROOT = base.ROOT
LOCALES = base.LOCALES
GOLDEN = ROOT / 'static/js/test/fixtures/ubx-commercial-c2-browser.json'
CONTRACT = {'company_id': 901, 'status': 'generated', 'contract_number': 'CT-901', 'events': []}
INIT = "window.__opens=[];window.open=function(u,t){window.__opens.push([String(u),String(t)]);return null;};"


class Fixture(commercial.Fixture):
    def route(self, route):
        request = route.request
        path = urlsplit(request.url).path
        if request.method == 'POST' and (path.startswith('/api/commercial-contract/') or path == '/api/commercial-settings'):
            body = json.loads(request.post_data or '{}')
            self.calls.append({'method': 'POST', 'path': path, 'query': urlsplit(request.url).query, 'body': body})
            if self.fail_mutation:
                return route.fulfill(status=403, json={'error': 'QA forbidden', 'message': 'QA forbidden'})
            return route.fulfill(json={'ok': True, 'contract': dict(CONTRACT, last=path.rsplit('/', 1)[1])})
        return super().route(route)


def click(f, element_id):
    f.page.evaluate('(id) => document.getElementById(id).click()', element_id)
    f.page.wait_for_timeout(250)


def submit(f, form_id):
    f.page.evaluate('(id) => document.getElementById(id).requestSubmit()', form_id)
    f.page.wait_for_timeout(350)


def actions(f):
    """A sequência de ações, pela interface real (os listeners do produto)."""
    page = f.page
    page.evaluate('fillCommercialForm(901)')  # dispara o GET do contrato
    page.wait_for_timeout(300)
    click(f, 'commercial-save-contract-management')
    click(f, 'commercial-generate-contract')
    page.evaluate("""() => {
      document.getElementById('commercial-signature-name').value = 'Ana "QA" <b>';
      document.getElementById('commercial-signature-data').value = 'data:image/png;base64,QUJD';
    }""")
    click(f, 'commercial-sign-contract')
    page.set_input_files('#commercial-signed-file', files=[{'name': 'assinado <1>.pdf', 'mimeType': 'application/pdf',
                                                            'buffer': b'%PDF-1.4\n%QA\n'}])
    click(f, 'commercial-upload-signed')
    page.evaluate("""() => {
      document.getElementById('commercial-email-to').value = 'cliente@exemplo.test';
      document.getElementById('commercial-email-subject').value = 'Contrato & aditivo';
      document.getElementById('commercial-email-body').value = 'Linha 1\\nLinha "2"';
    }""")
    click(f, 'commercial-send-contract-email')
    click(f, 'commercial-contract-pdf')
    click(f, 'commercial-view-contract')
    click(f, 'commercial-download-contract')
    page.evaluate("""() => document.querySelector('#commercial-summary [data-commercial-toggle="901"]').click()""")
    page.wait_for_timeout(350)
    page.evaluate('fillCommercialForm(901)')
    page.wait_for_timeout(300)
    submit(f, 'commercial-form')
    submit(f, 'commercial-settings-form')
    page.evaluate("""() => {
      const button = document.createElement('button');
      button.dataset.companyViewContract = '901';
      document.getElementById('company-details').appendChild(button);
      button.click();
      button.remove();
    }""")
    page.wait_for_timeout(150)


def run_locale(origin, browser, locale):
    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, service_workers='block', locale=locale)
    context.add_init_script(INIT)
    page = context.new_page()
    page.set_default_timeout(8000)
    f = Fixture(page, origin, locale)
    f.fail_mutation = False
    try:
        f.open()
        f.page.evaluate('async()=>{await loadBootstrap()}')
        f.view('comercial')
        f.tab('comercial', 'contratos')
        f.page.evaluate('fillCommercialForm(901)')
        f.page.wait_for_function("document.getElementById('commercial-contract-status')?.textContent.length>0")
        start_calls, start_dialogs = len(f.calls), len(f.dialogs)
        f.page.evaluate('window.__opens = []')
        actions(f)
        f.fail_mutation = True
        actions(f)
        f.fail_mutation = False
        observed = {
            'calls': [c for c in f.calls[start_calls:] if not c['path'].startswith('/api/i18n/')],
            'opens': f.page.evaluate('window.__opens'),
            'dialogs': [d['message'] for d in f.dialogs[start_dialogs:]],
        }
        # Requisições externas são bloqueadas pelo harness (htmx do unpkg já era
        # pedido antes da C2); entram na comparação com a referência.
        observed['external'] = sorted(set(f.external))
        assert not f.errors, f'page errors: {f.errors}'
        return observed
    finally:
        context.close()


def check_coverage(observed):
    seen = {(c['method'], c['path']) for c in observed['calls']}
    expected = {('GET', '/api/commercial-contract'), ('POST', '/api/commercial-contract/save'),
                ('POST', '/api/commercial-contract/generate'), ('POST', '/api/commercial-contract/sign'),
                ('POST', '/api/commercial-contract/upload-signed'), ('POST', '/api/commercial-contract/send-email'),
                ('POST', '/api/commercial-settings'), ('PUT', '/api/companies/901')}
    missing = expected - seen
    assert not missing, f'endpoints não exercitados: {sorted(missing)}'
    opened = {urlsplit(u).path for u, _ in observed['opens']}
    assert opened == {'/api/commercial-contract.pdf', '/api/commercial-contract/file'}, opened
    assert observed['dialogs'], 'nenhum diálogo registrado'


COMMERCIAL_PREFIXES = ('/api/commercial', '/api/companies')


def split(observed):
    """Chamadas comerciais: ordem estrita. Recargas em segundo plano disparadas pelo
    loadBootstrap (fichas, estoque, regras, /health...) correm em paralelo e mudam
    de ordem entre execuções da MESMA versão; comparadas como conjunto com
    multiplicidade (mesmos pedidos, mesmas vezes)."""
    commercial = [c for c in observed['calls'] if c['path'].startswith(COMMERCIAL_PREFIXES)]
    background = sorted(json.dumps(c, sort_keys=True, ensure_ascii=False) for c in observed['calls']
                        if not c['path'].startswith(COMMERCIAL_PREFIXES))
    return {'commercial_calls': commercial, 'background_calls': background, 'opens': observed['opens'],
            'dialogs': observed['dialogs'], 'external': observed['external']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/ubx-commercial-integrations'))
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
                if args.record:
                    golden[locale] = observed
                else:
                    for key in ('commercial_calls', 'background_calls', 'opens', 'dialogs', 'external'):
                        assert split(observed)[key] == split(golden[locale])[key], (
                            f'{key} difere da referência:\natual: {json.dumps(split(observed)[key], ensure_ascii=False)[:1500]}\n'
                            f'antes: {json.dumps(split(golden[locale])[key], ensure_ascii=False)[:1500]}')
                result.update(calls=len(observed['calls']), opens=len(observed['opens']), dialogs=len(observed['dialogs']))
            except Exception as error:  # noqa: BLE001 — registra a falha do cenário e segue
                result.update(status='failed', error=str(error))
            results.append(result)
            print(f"{locale} equivalence: {result['status']} {result.get('error', '')[:600]}", flush=True)
        browser.close()
    server.shutdown()
    if args.record and all(r['status'] == 'passed' for r in results):
        GOLDEN.write_text(json.dumps(golden, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    (args.output / 'results.json').write_text(json.dumps(results, indent=2, ensure_ascii=False) + '\n')
    return int(any(result['status'] != 'passed' for result in results))


if __name__ == '__main__':
    raise SystemExit(main())
