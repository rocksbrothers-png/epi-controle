"""UBX Comercial, fatia C4 — Chromium: SPA real + API sintética interceptada; nunca abre banco.

Equivalência, no navegador real (ICU do Chromium) e nos 5 idiomas, das funções
compartilhadas depois da extração — formatCompanyCurrency
(modules/companies/ui/companies-view.js), renderMyCompanyDomains
(modules/my-company/ui/my-company-view.js) e fileToBase64
(modules/shared/ui/file-data-url.js) — com o comportamento de ANTES da C4.

O "antes" é uma referência gravada (static/js/test/fixtures/ubx-commercial-c4-browser.json),
produzida rodando ESTE MESMO roteiro contra o static/ da main anterior à C4
(`--record --static <worktree da main>/static`). Para cada idioma, com o relógio
do navegador fixo:

1. formatCompanyCurrency com valores de borda (zero, negativos, meio-centavo,
   grandes, inválidos, null/undefined, strings) e a tela de Empresas
   renderizada (resumo, tabela e detalhes, que usam o valor mensal/projetado);
2. renderMyCompanyDomains com domínios verificados, pendentes, subdomínio da
   plataforma, marcação e padrões de replace — tabela e instruções DNS;
3. fileToBase64 com arquivos reais (File) — PDF, texto, vazio e binário;
4. troca de idioma sem recarregar e nova renderização.

Compara tudo com a referência e exige nenhum erro de página e nenhuma marcação
executada.

python scripts/browser/ubx_commercial_shared.py --output /tmp/ubx-c4
python scripts/browser/ubx_commercial_shared.py --record --static /caminho/da/main/static
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

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fix_colab_terc as base
import i18n_commercial as commercial

ROOT = base.ROOT
LOCALES = base.LOCALES
GOLDEN = ROOT / 'static/js/test/fixtures/ubx-commercial-c4-browser.json'
FIXED_NOW = '2026-11-15T12:00:00'
XSS = '<img src=x onerror=window.__xss=(window.__xss||0)+1>'
VALUES = "[0, -0, 1, -1, 0.005, 0.015, 1.005, 12.345, -12.345, 1234.5, 1234567.891, -9876543.21, 1e15, 1e21, NaN, Infinity, " \
         "-Infinity, null, undefined, '', '0', '42.5', '42,5', '1e3', 'abc', true, false, [], [5], {}]"
DOMAINS = [
    {'id': 1, 'full_host': 'app.empresa.test', 'type_label': 'Subdomínio', 'domain_type': 'platform_subdomain',
     'verification_status': 'verified', 'ssl_status': 'active', 'is_primary': 1},
    {'id': 7, 'full_host': 'sub.plataforma.test', 'domain_type': 'platform_subdomain', 'verification_status': 'pending',
     'cname_target': 'plat', 'txt_record': 'p', 'verification_token': 'p'},
    {'id': 2, 'full_host': 'epi.cliente.test', 'type_label': 'Próprio', 'domain_type': 'custom_domain',
     'verification_status': 'pending', 'ssl_status': 'pending', 'is_primary': 0, 'cname_target': 'cname.<b>x</b> $&$1',
     'txt_record': "_epi$'", 'verification_token': 'tok "1" $$'},
    {'id': 3, 'full_host': 'b.test', 'type_label': 'Próprio', 'domain_type': 'custom_domain', 'verification_status': 'verified',
     'ssl_status': 'failed', 'is_primary': '0'},
    {'id': 4, 'full_host': XSS, 'type_label': '<i>t</i>', 'domain_type': 'custom_domain', 'verification_status': 'failed',
     'ssl_status': '', 'is_primary': '1'},
]
SNAPSHOT = """() => ({
  summary: document.getElementById('companies-summary')?.innerHTML ?? null,
  table: document.getElementById('companies-table')?.innerHTML ?? null,
  details: document.getElementById('company-details')?.innerHTML ?? null,
  domains: document.getElementById('my-company-domains-table')?.innerHTML ?? null,
  instructions: document.getElementById('my-company-domain-instructions')?.innerHTML ?? null,
  xss: window.__xss || 0
})"""
EXERCISE = """async ([values, domainSets]) => {
  const out = {};
  out.currency = values.map((v) => { try { return ['ok', formatCompanyCurrency(v)]; } catch (e) { return ['threw', String(e)]; } });
  out.currencyNoArg = formatCompanyCurrency();
  out.domains = domainSets.map((domains) => {
    try { renderMyCompanyDomains(domains); } catch (e) { return ['threw', String(e)]; }
    return [document.getElementById('my-company-domains-table')?.innerHTML ?? null,
      document.getElementById('my-company-domain-instructions')?.innerHTML ?? null];
  });
  const files = [
    new File(['%PDF-1.4\\n%QA\\n'], 'contrato.pdf', { type: 'application/pdf' }),
    new File(['Olá, mundo "çã" <b>'], 'texto.txt', { type: 'text/plain' }),
    new File([], 'vazio.bin', { type: '' }),
    new File([new Uint8Array([0, 1, 2, 250, 251, 252, 253, 254, 255])], 'bin.dat', { type: 'application/octet-stream' })
  ];
  out.base64 = [];
  for (const file of files) {
    try { out.base64.push(['ok', await fileToBase64(file)]); } catch (e) { out.base64.push(['threw', String(e)]); }
  }
  return out;
}"""


def actions(f):
    page = f.page
    f.company_list[0]['monthly_value'] = 1234567.891
    f.company_list[0]['projected_monthly_value'] = -12.345
    f.company_list[0]['unit_price'] = 0.005
    page.evaluate('async()=>{await loadBootstrap()}')
    f.view('empresas')
    page.evaluate("renderCompanyDetails(901)")
    page.wait_for_timeout(200)
    steps = [{'label': 'Empresas', 'snapshot': page.evaluate(SNAPSHOT)}]
    domain_sets = [[], DOMAINS, DOMAINS[1:3], [{}], [DOMAINS[4]]]
    exercise = f'(d) => ({EXERCISE})([{VALUES}, d])'
    steps.append({'label': 'funções', 'result': page.evaluate(exercise, domain_sets)})
    other = 'fr-FR' if f.locale != 'fr-FR' else 'nb-NO'
    page.evaluate('(l)=>EpiI18n.setLang(l,{persist:false})', other)
    page.wait_for_function('(l)=>EpiI18n.lang===l', arg=other)
    page.evaluate("renderCompanies(); renderCompanyDetails(901)")
    page.wait_for_timeout(200)
    steps.append({'label': f'troca de idioma ({other})', 'snapshot': page.evaluate(SNAPSHOT),
                  'result': page.evaluate(exercise, domain_sets)})
    return steps


def run_locale(origin, browser, locale):
    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, service_workers='block', locale=locale)
    page = context.new_page()
    page.clock.set_fixed_time(FIXED_NOW)
    page.set_default_timeout(8000)
    f = commercial.Fixture(page, origin, locale)
    try:
        f.open()
        steps = actions(f)
        assert not f.errors, f'page errors: {f.errors}'
        xss = page.evaluate('window.__xss || 0')
        assert xss == 0, f'marcação executada {xss} vez(es)'
        return {'steps': steps}
    finally:
        context.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/ubx-commercial-shared'))
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
                if args.record:
                    golden[locale] = observed
                else:
                    for i, (now, before) in enumerate(zip(observed['steps'], golden[locale]['steps'], strict=True)):
                        if now != before:
                            raise AssertionError(f'passo {i} ({now["label"]}) difere da referência: '
                                                 f'atual {json.dumps(now, ensure_ascii=False)[:700]} '
                                                 f'antes {json.dumps(before, ensure_ascii=False)[:700]}')
                result.update(steps=len(observed['steps']))
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
