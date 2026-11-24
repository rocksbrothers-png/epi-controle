"""UBX Fornecedores F1 — Chromium: SPA real + API sintética interceptada; nunca abre banco.

Equivalência, no navegador real e nos 5 idiomas, da importação de fornecedores
(importSuppliersCSV no app.js, com _parseSuppliersRows e _loadSheetJS extraídos para
modules/purchases/business/supplier-import-rules.js e
modules/purchases/integrations/supplier-import-loader.js) com o comportamento de ANTES
da F1.

O "antes" é uma referência gravada (static/js/test/fixtures/ubx-supplier-import-browser.json),
produzida rodando ESTE MESMO roteiro contra o static/ da main anterior à F1
(`--record --static <worktree da main>/static`). Para cada idioma, pelo campo de
arquivo real da aba Fornecedores (#compras-suppliers-csv) e com a API sintética:

1. CSV com ';', BOM, linhas vazias, aspas e cabeçalhos em português;
2. CSV com ',' e cabeçalhos em inglês, valores com espaços e numéricos;
3. CSV só com cabeçalho (arquivo vazio) e CSV sem coluna de nome (nenhuma linha válida);
4. XLS/XLSX: o script do CDN do SheetJS é servido por um stub determinístico (a URL e o
   CDN não mudam; o stub só evita depender da rede), com cabeçalhos alternativos,
   traduzidos, números e linhas vazias;
5. XLS com falha ao carregar o script (mensagem traduzida);
6. sem arquivo selecionado e erro do servidor no upload.

Registra o corpo enviado a POST /api/authorized-suppliers/upload, o feedback mostrado e
os scripts do SheetJS injetados, e compara com a referência. Exige nenhum erro de
página e nenhuma marcação executada.

python scripts/browser/ubx_supplier_import.py --output /tmp/ubx-supplier-import
python scripts/browser/ubx_supplier_import.py --record --static /caminho/da/main/static
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
GOLDEN = ROOT / 'static/js/test/fixtures/ubx-supplier-import-browser.json'
FIXED_NOW = '2026-11-23T12:00:00'
CDN = 'https://cdn.jsdelivr.net/npm/xlsx/dist/xlsx.full.min.js'
XSS = '<img src=x onerror=window.__xss=(window.__xss||0)+1>'
# Stub do SheetJS: read() devolve um workbook com uma planilha; sheet_to_json devolve as
# linhas que o teste deixou em window.__xlsxRows (registra as opções recebidas).
XLSX_STUB = """window.XLSX = {
  read: function (buf, opts) { window.__xlsxCalls = (window.__xlsxCalls || []).concat([['read', buf && buf.byteLength, opts && opts.type]]);
    return { SheetNames: ['Fornecedores', 'Outra'], Sheets: { Fornecedores: { id: 'ws1' }, Outra: { id: 'ws2' } } }; },
  utils: { sheet_to_json: function (ws, opts) { window.__xlsxCalls = window.__xlsxCalls.concat([['sheet_to_json', ws.id, JSON.stringify(opts)]]);
    return JSON.parse(JSON.stringify(window.__xlsxRows || [])); } }
};"""
XLSX_ROWS = [
    {'Nome': 'XLS Um', 'CNPJ': 11222333000181, 'Email': 'um@x.test'},
    {'Name': 'XLS Two', 'cnpj': '', 'contact_email': 'two@x.test'},
    {'Nombre': 'XLS Tres', 'CNPJ': '', 'Email': ''},
    {'Navn': 'XLS Fire', 'Nom': 'XLS Quatre'},
    {'Nome': '', 'CNPJ': 123, 'Email': ''},
    {'Nome': '   ', 'CNPJ': '', 'Email': ''},
    {'Nome': 4567, 'CNPJ': 0, 'Email': True},
    {'Nome': XSS, 'CNPJ': '"1"', 'Email': "o'neil@x.test"},
]
CSV_PT = '﻿Nome;CNPJ;Contato\r\n"Fornecedor A";12.345.678/0001-90;a@x.test\r\n\r\n  Fornecedor B ; 98765432000110 ;  b@x.test \r\n;123;sem@nome\r\nSó nome\r\n' + XSS + ';1;x\r\n'
CSV_EN = 'name,cnpj,email\nSupplier One,1,one@x.test\n   \nSupplier Two,,\n0,0,0\n"Quoted, comma",2,q@x.test\n'
CSV_EMPTY = 'Nome;CNPJ;Contato\r\n\r\n   \r\n'
CSV_NO_NAME = 'empresa,documento\nAcme,1\nBeta,2\n'
SNAPSHOT = """() => ({
  feedback: document.getElementById('compras-suppliers-csv-feedback')?.textContent ?? null,
  scripts: [...document.querySelectorAll('script')].map((s) => s.src).filter((src) => src.includes('xlsx')).length,
  xlsxCalls: window.__xlsxCalls || null,
  xss: window.__xss || 0
})"""


def run_import(f, uploads, name, content, mime):
    page = f.page
    uploads.clear()
    page.evaluate("() => { const fb = document.getElementById('compras-suppliers-csv-feedback'); if (fb) fb.textContent = ''; window.__xlsxCalls = null; }")
    if name is None:
        page.set_input_files('#compras-suppliers-csv', [])
    else:
        data = content if isinstance(content, bytes) else content.encode('utf-8')
        page.set_input_files('#compras-suppliers-csv', files=[{'name': name, 'mimeType': mime, 'buffer': data}])
    page.evaluate('async () => { await globalThis.importSuppliersCSV(); }')
    page.wait_for_timeout(150)
    snap = page.evaluate(SNAPSHOT)
    snap['uploads'] = [json.loads(json.dumps(body)) for body in uploads]
    return snap


def actions(f):
    page = f.page
    uploads = []
    state = {'upload_status': 200, 'cdn': 'ok'}

    def upload(route):
        body = json.loads(route.request.post_data or '{}')
        body.pop('actor_user_id', None)
        uploads.append(body)
        if state['upload_status'] != 200:
            return route.fulfill(status=state['upload_status'], json={'error': 'Falha QA no upload.'})
        return route.fulfill(json={'inserted': len(body.get('rows') or []), 'updated': 1})

    def cdn(route):
        if state['cdn'] == 'fail':
            return route.abort()
        return route.fulfill(status=200, content_type='application/javascript', body=XLSX_STUB)

    page.route('**/api/authorized-suppliers/upload', upload)
    page.route('**/api/authorized-suppliers', lambda route: route.fulfill(json={'items': []}))
    page.route(CDN, cdn)
    page.evaluate('async()=>{await loadBootstrap()}')
    steps = []
    steps.append({'label': 'sem arquivo', 'result': run_import(f, uploads, None, None, None)})
    steps.append({'label': 'csv pt ;', 'result': run_import(f, uploads, 'fornecedores.csv', CSV_PT, 'text/csv')})
    steps.append({'label': 'csv en ,', 'result': run_import(f, uploads, 'suppliers.CSV', CSV_EN, 'text/csv')})
    steps.append({'label': 'csv vazio', 'result': run_import(f, uploads, 'vazio.csv', CSV_EMPTY, 'text/csv')})
    steps.append({'label': 'csv sem nome', 'result': run_import(f, uploads, 'sem-nome.csv', CSV_NO_NAME, 'text/csv')})
    state['cdn'] = 'fail'
    page.evaluate('() => { delete window.XLSX; }')
    steps.append({'label': 'xls sem CDN', 'result': run_import(f, uploads, 'planilha.xls', b'\xd0\xcf\x11\xe0QA', 'application/vnd.ms-excel')})
    state['cdn'] = 'ok'
    page.evaluate('(rows) => { delete window.XLSX; window.__xlsxRows = rows; }', XLSX_ROWS)
    steps.append({'label': 'xlsx', 'result': run_import(f, uploads, 'planilha.xlsx', b'PK\x03\x04QA', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')})
    steps.append({'label': 'xls (SheetJS já carregado)', 'result': run_import(f, uploads, 'outra.xls', b'\xd0\xcf\x11\xe0QA2', 'application/vnd.ms-excel')})
    state['upload_status'] = 500
    steps.append({'label': 'upload com erro', 'result': run_import(f, uploads, 'erro.csv', CSV_EN, 'text/csv')})
    state['upload_status'] = 200
    other = 'fr-FR' if f.locale != 'fr-FR' else 'nb-NO'
    page.evaluate('(l)=>EpiI18n.setLang(l,{persist:false})', other)
    page.wait_for_function('(l)=>EpiI18n.lang===l', arg=other)
    page.evaluate('() => { delete window.XLSX; }')
    state['cdn'] = 'fail'
    steps.append({'label': f'troca de idioma ({other}) xls sem CDN', 'result': run_import(f, uploads, 'p.xlsx', b'PK', 'application/octet-stream')})
    state['cdn'] = 'ok'
    steps.append({'label': f'troca de idioma ({other}) csv', 'result': run_import(f, uploads, 'f.csv', CSV_PT, 'text/csv')})
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
    parser.add_argument('--output', type=Path, default=Path('/tmp/ubx-supplier-import'))
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
