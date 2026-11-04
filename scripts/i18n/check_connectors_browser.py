"""Real procurement modal with intercepted APIs; no tenant or supplier is contacted."""
import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

LOCALES = ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO']
LABELS = {
    'pt-BR': 'API REST/JSON genérica (v1)',
    'en-GB': 'Generic REST/JSON API (v1)',
    'es-ES': 'API REST/JSON genérica (v1)',
    'fr-FR': 'API REST/JSON générique (v1)',
    'nb-NO': 'Generisk REST/JSON-API (v1)',
}
ERRORS = {
    'pt-BR': 'Teste da integração falhou: Loja respondeu HTTP 429 em /catalog.',
    'en-GB': 'Integration test failed: Store returned HTTP 429 at /catalog.',
    'es-ES': 'Falló la prueba de integración: La tienda respondió HTTP 429 en /catalog.',
    'fr-FR': 'Échec du test de connexion : La boutique a renvoyé HTTP 429 sur /catalog.',
    'nb-NO': 'Integrasjonstesten mislyktes: Butikken svarte med HTTP 429 på /catalog.',
}
PREFIXES = {
    'pt-BR': 'Teste da integração falhou: ', 'en-GB': 'Integration test failed: ',
    'es-ES': 'Falló la prueba de integración: ', 'fr-FR': 'Échec du test de connexion : ',
    'nb-NO': 'Integrasjonstesten mislyktes: ',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output', type=Path, default=Path(tempfile.mkdtemp(prefix='i18n-connectors-')))
    parser.add_argument('--baseline', help='Read UI assets from this git revision')
    parser.add_argument('--browser', default=os.environ.get('CHROMIUM_EXECUTABLE'))
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    revision = subprocess.check_output(['git', 'rev-parse', args.baseline], cwd=root).decode().strip() if args.baseline else None

    def asset(path):
        if revision:
            return subprocess.check_output(['git', 'show', f'{revision}:{path}'], cwd=root).decode()
        return (root / path).read_text()

    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=args.browser, args=['--no-sandbox'])
        for locale in LOCALES:
            page = browser.new_page(viewport={'width': 390, 'height': 844})
            javascript_errors, calls, checks = [], [], []
            reply = {'error': ERRORS['pt-BR'], 'connectors': None}
            page.on('pageerror', lambda exc: javascript_errors.append(str(exc)))

            def route(intercept):
                request = intercept.request
                path = urlparse(request.url).path
                if path.startswith('/api/i18n/'):
                    lang = path.rsplit('/', 1)[1]
                    intercept.fulfill(json={'locale': lang, 'fallback': False,
                                            'translations': json.loads(asset(f'static/i18n/{lang}.json'))})
                    return
                if path.startswith('/api/'):
                    calls.append({'path': path, 'method': request.method,
                                  'body': request.post_data_json, 'language': request.headers.get('accept-language'),
                                  'authenticated': request.headers.get('authorization') == 'Bearer synthetic-session'})
                    if path == '/api/supplier-connectors' and request.method == 'GET':
                        intercept.fulfill(json={'items': reply['connectors'] or [
                            {'key': 'http_json_v1', 'label': LABELS['pt-BR']},
                            {'key': 'demo', 'label': 'Loja de demonstração (piloto)'},
                            {'key': 'custom', 'label': 'Loja original <img src=x onerror=window.__xss=1>'},
                        ]})
                    elif path == '/api/authorized-suppliers/41/integration' and request.method == 'GET':
                        intercept.fulfill(json={'item': {'connector_key': 'http_json_v1', 'active': 1, 'has_config': True}})
                    elif path in ['/api/authorized-suppliers/41/integration', '/api/authorized-suppliers/41/integration/test'] and request.method == 'POST':
                        intercept.fulfill(status=400, json={'error': reply['error'], 'code': 'CONNECTOR_FAILURE',
                                                          'validation': {'supplier_id': 41, 'line': 7}})
                    else:
                        raise AssertionError(f'Unexpected API request: {request.method} {path}')
                    return
                if path == '/':
                    intercept.fulfill(content_type='text/html', body='<html><body></body></html>')
                else:
                    raise AssertionError(f'Unexpected network request: {request.url}')

            def check(name, actual, expected):
                checks.append({'name': name, 'passed': actual == expected, 'actual': actual, 'expected': expected})

            page.route('**/*', route)
            page.goto('http://127.0.0.1:41337/')
            page.add_style_tag(content=asset('static/styles.css'))
            page.evaluate("window.__EPI_APP_STATE__={user:{id:7,company_id:23,unit_id:11}};window.authHeaders=()=>({Authorization:'Bearer synthetic-session'});")
            page.add_script_tag(content=asset('static/i18n.js'))
            page.evaluate('(locale)=>EpiI18n.setLang(locale,{persist:false})', locale)
            page.add_script_tag(content=asset('static/js/views/view-helpers.js'))
            page.add_script_tag(content=asset('static/js/views/procurement.js'))
            page.evaluate("openSupplierIntegrationModal(41,'Fornecedor original <img src=x onerror=window.__xss=1>')")
            key = page.locator('[data-integration-key]')
            config = page.locator('[data-integration-config]')
            config.fill('{"base_url":"https://fixture.invalid","note":"Observação original"}')
            check('registered_label', key.locator('option[value=http_json_v1]').inner_text(), LABELS[locale])
            check('unknown_label_opaque', key.locator('option[value=custom]').inner_text(), 'Loja original <img src=x onerror=window.__xss=1>')
            page.locator('[data-integration-test]').click()
            feedback = page.locator('[data-integration-feedback]')
            page.wait_for_function("document.querySelector('[data-integration-feedback]').textContent.length>0")
            check('nested_error', feedback.inner_text(), ERRORS[locale])
            page.screenshot(path=str(output / f'connectors-error-{locale}.png'), full_page=True)
            other = 'fr-FR' if locale != 'fr-FR' else 'en-GB'
            before = len(calls)
            page.evaluate('(locale)=>EpiI18n.setLang(locale,{persist:false})', other)
            check('live_nested_error', feedback.inner_text(), ERRORS[other])
            check('live_registered_label', key.locator('option[value=http_json_v1]').inner_text(), LABELS[other])
            check('selected_key_preserved', key.input_value(), 'http_json_v1')
            check('active_preserved', page.locator('[data-integration-active]').input_value(), '1')
            check('draft_preserved', config.input_value(), '{"base_url":"https://fixture.invalid","note":"Observação original"}')
            check('locale_has_no_business_requests', len(calls), before)
            check('test_contract', calls[-1], {'path': '/api/authorized-suppliers/41/integration/test', 'method': 'POST',
                  'body': {'actor_user_id': 7}, 'language': locale, 'authenticated': True})
            reply['error'] = 'Teste da integração falhou: Diagnóstico externo original <img src=x onerror=window.__xss=1>'
            page.locator('[data-integration-save]').click()
            page.wait_for_function("document.querySelector('[data-integration-feedback]').textContent.includes('Diagnóstico externo original')")
            check('save_contract', calls[-1], {'path': '/api/authorized-suppliers/41/integration', 'method': 'POST',
                  'body': {'actor_user_id': 7, 'connector_key': 'http_json_v1', 'active': True,
                           'config': {'base_url': 'https://fixture.invalid', 'note': 'Observação original'}},
                  'language': other, 'authenticated': True})
            check('opaque_cause_preserved', feedback.inner_text().endswith('Diagnóstico externo original <img src=x onerror=window.__xss=1>'), True)
            check('opaque_cause_translated_wrapper', feedback.inner_text(), PREFIXES[other] + 'Diagnóstico externo original <img src=x onerror=window.__xss=1>')
            before = len(calls)
            page.evaluate('(locale)=>EpiI18n.setLang(locale,{persist:false})', locale)
            check('opaque_cause_live_wrapper', feedback.inner_text(), PREFIXES[locale] + 'Diagnóstico externo original <img src=x onerror=window.__xss=1>')
            check('unknown_cause_live_and_inert', feedback.locator('img,script').count(), 0)
            check('no_markup_executed', page.evaluate('window.__xss || 0'), 0)
            check('no_repeat_submission', len(calls), before)
            check('no_horizontal_overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth'), True)
            check('no_javascript_errors', javascript_errors, [])
            page.screenshot(path=str(output / f'connectors-{locale}.png'), full_page=True)
            # Invalid JSON stays local. Blank config keeps the stored settings;
            # an explicit empty object is still submitted as an empty object.
            before = len(calls)
            config.fill('{invalid')
            page.locator('[data-integration-save]').click()
            page.wait_for_function("document.querySelector('[data-integration-feedback]').hasAttribute('data-i18n')")
            check('invalid_json_has_no_request', len(calls), before)
            check('invalid_json_draft_preserved', config.input_value(), '{invalid')
            for draft, expected_config in [('', {}), ('{}', {'config': {}})]:
                config.fill(draft)
                before = len(calls)
                page.locator('[data-integration-save]').click()
                page.wait_for_function("document.querySelector('[data-integration-feedback]').textContent.includes('Diagnóstico externo original')")
                check('explicit_save_count_' + repr(draft), len(calls), before + 1)
                check('saved_config_' + repr(draft), calls[-1]['body'], {
                    'actor_user_id': 7, 'connector_key': 'http_json_v1', 'active': True, **expected_config})
            for connector in [
                {'key': 'http_json_v1', 'label': 'Custom original'},
                {'key': 'http_json_v1', 'label': LABELS['pt-BR'] + ' '},
                {'key': 'custom', 'label': LABELS['pt-BR']},
                {'key': '__proto__', 'label': LABELS['pt-BR']},
            ]:
                page.locator('[data-integration-cancel]').click()
                reply['connectors'] = [connector]
                page.evaluate("openSupplierIntegrationModal(41,'Fornecedor original')")
                option = page.locator('[data-integration-key] option')
                check('custom_option_opaque_' + repr(connector), option.inner_text(), connector['label'])
                page.evaluate('(locale)=>EpiI18n.setLang(locale,{persist:false})', other)
                check('custom_option_live_opaque_' + repr(connector), option.inner_text(), connector['label'])
                page.evaluate('(locale)=>EpiI18n.setLang(locale,{persist:false})', locale)
            results.append({'locale': locale, 'checks': checks, 'calls': calls})
            page.close()
        browser.close()
    failures = sum(not check['passed'] for result in results for check in result['checks'])
    report = {'baseline': revision, 'isolated_apis': True, 'failures': failures, 'results': results}
    (output / 'connectors-results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(f"{sum(len(r['checks']) for r in results)} checks, {failures} failures; evidence: {output}")
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
