"""I18N-FULL-V1 (Comercial) — Chromium: SPA real + API sintética interceptada; nunca abre banco.

Mesmo harness de scripts/browser/ubx_companies.py (Administrador Master com
empresas no bootstrap). Para cada um dos 5 idiomas confere, na tela Comercial:

1. KPIs, cards, alertas, vencimentos, histórico e situação do contrato no idioma
   ativo, com BRL formatado no idioma (sem conversão de moeda).
2. Nenhum texto em português sobra nos painéis quando o idioma não é pt-BR.
3. Trocar o idioma sem recarregar retraduz os painéis e a situação do contrato
   SEM nova requisição de negócio e SEM alterar o formulário digitado.
4. Nome de empresa/ator com marcação continua inerte (escapado).
5. O contrato HTTP do Comercial (PUT /api/companies/<id>) não muda.
6. Login: credenciais vazias mostram o aviso no idioma ativo, sem POST.
7. Mensagem de acesso do novo usuário (e-mail/WhatsApp) no idioma ativo, sem o
   mojibake que existia no pt-BR, com nome/usuário/senha intactos.
8. Leitor de QR em Entregas: status (modo USB, sessão sem QR válido) no idioma
   ativo, sem gravação.
9. Erros do backend (Compras) pelo api() real: mensagem traduzida na
   apresentação; status, code e payload intactos; mensagem preservada por
   contrato continua idêntica.

python scripts/browser/i18n_commercial.py --output /tmp/i18n-commercial
CHROMIUM_EXECUTABLE=/usr/bin/chromium seleciona um navegador já instalado.
"""
import argparse
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fix_colab_terc as base
import ubx_companies as ubx

ROOT = base.ROOT
LOCALES = base.LOCALES
XSS = '<img src=x onerror=window.__xss=1>'
AUDIT_LOGS = [
    {'id': 1, 'company_id': 901, 'company_name': 'Empresa QA ' + XSS, 'action_label': 'Atualização',
     'actor_name': 'Ana QA ' + XSS, 'created_at': '2026-10-30T14:05:00', 'summary': 'Plano alterado',
     'details': [{'field': 'plan_name', 'before': 'start', 'after': 'pro'}]},
]
CONTRACT = {'company_id': 901, 'status': 'pending_signature', 'contract_number': 'CT-901', 'events': [
    {'event_type': 'generated', 'created_at': '2026-10-30T10:00:00'}]}
# Chaves cujo texto pt-BR não pode sobrar nos painéis quando o idioma alvo o traduz
# de outra forma (es-ES/nb-NO usam legitimamente "Abrir contrato"/"Suspender").
PT_LEFTOVER_KEYS = ['commercial.panel.statMonthlyRevenue', 'commercial.panel.statActive', 'commercial.panel.openContract',
                    'commercial.panel.suspend', 'commercial.panel.reactivate', 'commercial.contractStatusLabels.pending_signature',
                    'commercial.risk.healthy', 'commercial.risk.nearLimit', 'commercial.currentLabel', 'commercial.projectedLabel',
                    'commercial.urgentBadge']
PT_LEFTOVER_FRAGMENTS = {'commercial.panel.historyBy': ' por Ana QA', 'commercial.panel.contractStatus': 'Status do contrato',
                         'commercial.expiresOn': 'Vence em', 'commercial.daysRemaining': 'dia(s) restantes',
                         'commercial.usersCount': ' Usuários'}
PANELS = ['#commercial-stats', '#commercial-summary', '#commercial-alerts', '#commercial-expiring', '#commercial-history']


def catalog(locale):
    return json.loads((ROOT / 'static/i18n' / f'{locale}.json').read_text(encoding='utf-8'))


def leaf(data, key):
    for part in key.split('.'):
        data = data[part]
    return data


class Fixture(ubx.Fixture):
    def __init__(self, *args):
        super().__init__(*args)
        self.permissions.extend(p for p in ('commercial:view',) if p not in self.permissions)
        self.company_list[1]['name'] = 'Cliente Dois ' + XSS

    def route(self, route):
        request = route.request
        path = urlsplit(request.url).path
        if path == '/api/bootstrap':
            original = route.fulfill

            def fulfill(**kwargs):
                payload = kwargs.get('json') or {}
                payload.update(company_audit_logs=AUDIT_LOGS)
                kwargs['json'] = payload
                return original(**kwargs)
            route.fulfill = fulfill
            return super().route(route)
        if path == '/api/commercial-contract' and request.method == 'GET':
            self.calls.append({'method': 'GET', 'path': path, 'query': urlsplit(request.url).query, 'body': None})
            return route.fulfill(json={'contract': CONTRACT})
        return super().route(route)


def panels_text(f):
    return '\n'.join(f.page.locator(sel).text_content() for sel in PANELS)


def commercial(f):
    # Vence em 5 dias: aparece em "vencimentos" com o selo Urgente.
    f.company_list[0]['contract_end'] = (datetime.now(UTC).date() + timedelta(days=5)).isoformat()
    f.page.evaluate('async()=>{await loadBootstrap()}')
    f.view('comercial')
    f.tab('comercial', 'contratos')
    f.page.evaluate("fillCommercialForm(901)")
    f.page.wait_for_function("document.getElementById('commercial-contract-status')?.textContent.length>0")
    check_locale(f, f.locale)

    # Formulário digitado não pode ser recriado pela troca de idioma.
    notes = f.page.locator('#commercial-form [name="commercial_notes"]')
    notes.fill('Rascunho não salvo')
    other = 'fr-FR' if f.locale != 'fr-FR' else 'nb-NO'
    before = len(f.calls)
    f.page.evaluate('(l)=>EpiI18n.setLang(l,{persist:false})', other)
    f.page.wait_for_function('(l)=>EpiI18n.lang===l', arg=other)
    f.page.wait_for_timeout(200)
    check_locale(f, other)
    business = [c for c in f.calls[before:] if not c['path'].startswith('/api/i18n/')]
    assert business == [], f'troca de idioma disparou requisições: {business}'
    expect(notes).to_have_value('Rascunho não salvo')
    f.page.evaluate('(l)=>EpiI18n.setLang(l,{persist:false})', f.locale)
    f.page.wait_for_timeout(200)
    check_locale(f, f.locale)

    # Contrato HTTP inalterado: Suspender envia a empresa inteira com active=0.
    before = len(f.calls)
    f.page.locator('#commercial-summary [data-commercial-toggle="901"]').click()
    f.page.wait_for_function('__EPI_APP_STATE__.companies.find(c=>c.id===901).active===0')
    sent = ubx.writes(f, before)
    assert [(c['method'], c['path']) for c in sent] == [('PUT', '/api/companies/901')], sent
    body = sent[0]['body']
    assert body['active'] == 0 and body['license_status'] == 'suspended' and body['name'] == 'Empresa QA', body
    assert f.page.evaluate('window.__xss || 0') == 0, 'marcação executada'


def check_locale(f, locale):
    cat = catalog(locale)
    lang = f.page.evaluate('EpiI18n.lang')
    assert lang == locale, (lang, locale)
    text = panels_text(f)
    for key in ('statMonthlyRevenue', 'statActive', 'openContract', 'suspend'):
        assert leaf(cat, 'commercial.panel.' + key) in text, (locale, key, text[:400])
    assert leaf(cat, 'commercial.urgentBadge') in text, (locale, 'urgentBadge')
    by = leaf(cat, 'commercial.panel.historyBy').replace('{action}', 'Atualização').replace('{actor}', 'Ana QA ' + XSS)
    assert by in text, (locale, by, text[-400:])
    # BRL formatado no idioma ativo, sem conversão.
    expected_total = f.page.evaluate(
        "(l)=>new Intl.NumberFormat(l,{style:'currency',currency:'BRL'}).format(__EPI_APP_STATE__.companies.reduce((t,c)=>t+Number(c.monthly_value||0),0))",
        locale)
    assert expected_total in text, (locale, expected_total)
    status = f.page.locator('#commercial-contract-status').text_content()
    expected_status = leaf(cat, 'commercial.panel.contractStatus').replace(
        '{status}', leaf(cat, 'commercial.contractStatusLabels.pending_signature'))
    assert status == expected_status, (locale, status, expected_status)
    if locale != 'pt-BR':
        pt = catalog('pt-BR')
        leftovers = [leaf(pt, k) for k in PT_LEFTOVER_KEYS
                     if leaf(pt, k) != leaf(cat, k) and leaf(pt, k) not in leaf(cat, k) and leaf(pt, k) in text + status]
        leftovers += [frag for k, frag in PT_LEFTOVER_FRAGMENTS.items()
                      if leaf(pt, k) != leaf(cat, k) and frag.strip() not in leaf(cat, k) and frag in text + status]
        assert not leftovers, (locale, leftovers)
    # Nomes com marcação continuam texto.
    assert f.page.locator('#commercial-summary img:not(.company-logo), #commercial-history img').count() == 0
    assert XSS in text


def login_message(f):
    """Tela de login (sem sessão): credenciais vazias mostram o aviso no idioma ativo."""
    f.page.goto(f.origin + '/', wait_until='load')
    f.page.wait_for_function('!!globalThis.EpiI18n')
    f.page.evaluate('(l)=>EpiI18n.setLang(l,{persist:false})', f.locale)
    f.page.wait_for_function('(l)=>EpiI18n.lang===l', arg=f.locale)
    f.page.locator('#login-username').fill('')
    before = len(f.calls)
    f.page.locator('#login-form').evaluate('(form)=>form.requestSubmit()')
    expected = leaf(catalog(f.locale), 'login.messages.enterCredentials')
    expect(f.page.locator('#login-message')).to_have_text(expected)
    posts = [c for c in f.calls[before:] if c['method'] == 'POST']
    assert posts == [], f'credenciais vazias não podem chegar ao backend: {posts}'


def access_message(f):
    """Mensagem de acesso do novo usuário: idioma ativo, sem mojibake, dados intactos."""
    cat = catalog(f.locale)
    target = {'full_name': 'Ana <b>QA</b>', 'username': 'ana.qa', 'company_name': 'Empresa QA'}
    for channel in ('email', 'whatsapp'):
        text = f.page.evaluate('([t,c])=>buildUserAccessMessage(t,"Prov!s0ria#1",c)', [target, channel])
        assert 'Ã' not in text and '\u00ad' not in text, (channel, text)
        assert leaf(cat, 'user.accessMessage.username').replace('{username}', 'ana.qa') in text, text
        assert leaf(cat, 'user.accessMessage.password').replace('{password}', 'Prov!s0ria#1') in text, text
        assert 'Ana <b>QA</b>' in text and 'Empresa QA' in text, text
        key = 'firstAccess' if channel == 'email' else 'firstAccessShort'
        assert leaf(cat, 'user.accessMessage.' + key) in text, (channel, text)


def delivery_qr_messages(f):
    """Leitor de QR em Entregas: mensagens de status no idioma ativo, sem requisição nova."""
    cat = catalog(f.locale)
    f.view('entregas')
    before = len(f.calls)
    f.page.locator('#delivery-qr-reader').evaluate('(b)=>b.click()')
    expect(f.page.locator('#delivery-qr-status')).to_have_text(leaf(cat, 'delivery.qr.usbMode'))
    # Concluir sem nenhum QR lido: aviso local, sem chamada ao backend.
    f.page.locator('#delivery-qr-finish').evaluate('(b)=>b.click()')
    expect(f.page.locator('#delivery-qr-status')).to_have_text(leaf(cat, 'delivery.qr.noneValid'))
    posts = [c for c in f.calls[before:] if c['method'] != 'GET']
    assert posts == [], f'mensagens de status não podem gravar nada: {posts}'


def ppe_tests_view(f):
    """Avaliações / EPI em teste: a tela abre nos 5 idiomas sem erro de página nem gravação."""
    if 'epi_evaluation:view' not in f.permissions:
        f.permissions.append('epi_evaluation:view')
        f.page.evaluate('async()=>{await loadBootstrap()}')
    before = len(f.calls)
    f.view('avaliacoes')
    f.page.wait_for_timeout(300)
    writes = [c for c in f.calls[before:] if c['method'] != 'GET']
    assert writes == [], f'abrir a tela não pode gravar: {writes}'


BACKEND_ERRORS = [
    # (texto pt-BR exato do backend, chave do catálogo ou None se preservado por contrato)
    ('A requisição precisa ter pelo menos um item.', 'apiErrors.messages.m_' + __import__('hashlib').sha256(
        'A requisição precisa ter pelo menos um item.'.encode()).hexdigest()[:12]),
    ('Linha 3 da cotação: assinatura do arquivo inválida.', 'apiErrors.messages.m_' + __import__('hashlib').sha256(
        'Linha {line} da cotação: assinatura do arquivo inválida.'.encode()).hexdigest()[:12]),
]


def backend_error_presentation(f):
    """Erro 400 de Compras pelo api() real: só a apresentação muda; status, code e payload ficam."""
    cat = catalog(f.locale)
    for source, key in BACKEND_ERRORS:
        body = {'error': source, 'code': 'X_PROBE', 'validation': {'line': 3}}
        def reply(route, _body=body):
            route.fulfill(status=400, json=_body)
        f.page.route('**/api/__i18n_probe', lambda route: reply(route))
        got = f.page.evaluate('''async()=>{try{await api('/api/__i18n_probe',{method:'POST',body:'{}'});return null}
          catch(e){return {message:e.message,status:e.status,code:e.code,payload:e.payload}}}''')
        f.page.unroute('**/api/__i18n_probe')
        assert got and got['status'] == 400 and got['code'] == 'X_PROBE', got
        assert got['payload'] == body, ('payload alterado', got['payload'])
        expected = leaf(cat, key).replace('{line}', '3')
        assert got['message'] == expected, (f.locale, got['message'], expected)
    # Preservada por contrato (comparação textual em handleDeliveryQrScan): continua idêntica.
    kept = 'QR não encontrado com correspondência exata no estoque da unidade.'
    f.page.route('**/api/__i18n_probe', lambda route: route.fulfill(status=400, json={'error': kept}))
    got = f.page.evaluate('''async()=>{try{await api('/api/__i18n_probe');return null}catch(e){return e.message}}''')
    f.page.unroute('**/api/__i18n_probe')
    assert got == kept, (f.locale, got)


login_message.needs_session = False
SCENARIOS = [commercial, login_message, access_message, delivery_qr_messages, ppe_tests_view, backend_error_presentation]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/i18n-commercial-browser'))
    parser.add_argument('--locales', nargs='+', default=LOCALES)
    parser.add_argument('--scenarios', nargs='+', default=[s.__name__ for s in SCENARIOS])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(base.QuietHandler, directory=str(ROOT / 'static')))
    Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    results = []
    with sync_playwright() as playwright:
        options = {'headless': True, 'args': ['--no-sandbox']}
        if os.environ.get('CHROMIUM_EXECUTABLE'):
            options['executable_path'] = os.environ['CHROMIUM_EXECUTABLE']
        browser = playwright.chromium.launch(**options)
        for locale in args.locales:
            for scenario in [s for s in SCENARIOS if s.__name__ in args.scenarios]:
                context = browser.new_context(viewport={'width': 1440, 'height': 1000}, service_workers='block', locale=locale)
                page = context.new_page()
                page.set_default_timeout(5000)
                fixture = Fixture(page, origin, locale)
                result = {'locale': locale, 'scenario': scenario.__name__, 'status': 'passed'}
                try:
                    if getattr(scenario, 'needs_session', True):
                        fixture.open()
                    scenario(fixture)
                    assert not fixture.errors, f'page errors: {fixture.errors}'
                except Exception as error:  # noqa: BLE001 — registra a falha do cenário e segue
                    result.update(status='failed', error=str(error))
                finally:
                    result.update(calls=fixture.calls, dialogs=fixture.dialogs, page_errors=fixture.errors,
                                  blocked_external_requests=fixture.external)
                    page.screenshot(path=str(args.output / f'{locale}-{scenario.__name__}.png'), full_page=False)
                    results.append(result)
                    print(f"{locale} {scenario.__name__}: {result['status']} {result.get('error', '')[:300]}", flush=True)
                    context.close()
        browser.close()
    server.shutdown()
    (args.output / 'results.json').write_text(json.dumps(results, indent=2, ensure_ascii=False) + '\n')
    return int(any(result['status'] != 'passed' for result in results))


if __name__ == '__main__':
    raise SystemExit(main())
