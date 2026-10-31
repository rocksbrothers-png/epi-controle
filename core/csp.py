"""Content Security Policy das respostas HTTP (SECURITY-CSP-V1).

Três superfícies, cada uma com a sua política:

* **SPA legada** (``/``, ``index.html`` e todo o resto servido pelo app): política estrita.
  Sem ``'unsafe-inline'`` nem ``'unsafe-eval'`` em ``script-src``; scripts só da própria
  origem e das quatro bibliotecas externas que o app carrega, cada uma pelo caminho exato
  (não o host inteiro, que permitiria carregar qualquer pacote do CDN).
* **Flutter Web** (``/app/``, ``/flutter_web/``): sempre Report-Only. O build do Flutter não
  roda neste repositório de testes; a política aplicada depende de validar o build real.
* **Pagamento** (``/pagamento.html``, ``/pagamento``, ``/checkout``): sempre Report-Only. O SDK do Mercado Pago carrega
  scripts, frames e conexões de vários domínios que só dá para validar com o SDK real.

Modo da política da SPA (``CSP_MODE``): ``enforce`` aplica (``Content-Security-Policy``);
``report-only`` só reporta. Padrão: ``enforce`` fora de produção e ``report-only`` em
produção — a política estrita é a mesma nos dois modos, então produção passa a reportar
exatamente o que seria bloqueado; ligar ``CSP_MODE=enforce`` em produção é uma decisão de
implantação, depois de conferir os relatórios.

``style-src`` mantém ``'unsafe-inline'``: o HTML e os templates têm centenas de atributos
``style=``, que nonce/hash não cobrem. Injeção de CSS não executa script; o risco residual
está documentado em ``docs/SECURITY_CSP_V1.md``.
"""

from __future__ import annotations

SPA_EXTERNAL_SCRIPTS = (
    # index.html (views/_scripts.html), com SRI.
    'https://unpkg.com/htmx.org@1.9.12',
    # Leitura de QR/código de barras (app.js, carregados sob demanda).
    'https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js',
    'https://unpkg.com/@zxing/browser@0.1.5/umd/index.min.js',
    # Importação de planilhas (app.js, sob demanda).
    'https://cdn.jsdelivr.net/npm/xlsx/dist/xlsx.full.min.js',
)

SPA_DIRECTIVES = (
    ('default-src', ("'self'",)),
    ('script-src', ("'self'",) + SPA_EXTERNAL_SCRIPTS),
    ('style-src', ("'self'", "'unsafe-inline'", 'https://fonts.googleapis.com')),
    # Logotipos, fotos de EPI e assinaturas são data: URLs; QR codes vêm do api.qrserver.com.
    ('img-src', ("'self'", 'data:', 'blob:', 'https://api.qrserver.com')),
    ('font-src', ("'self'", 'data:', 'https://fonts.gstatic.com')),
    ('connect-src', ("'self'",)),
    # Câmera (leitura de QR) e workers das bibliotecas de leitura.
    ('media-src', ("'self'", 'blob:')),
    ('worker-src', ("'self'", 'blob:')),
    ('frame-src', ("'self'",)),
    ('object-src', ("'none'",)),
    ('base-uri', ("'self'",)),
    ('form-action', ("'self'",)),
    ('frame-ancestors', ("'self'",)),
)

FLUTTER_DIRECTIVES = (
    ('default-src', ("'self'",)),
    # flutter_bootstrap.js + CanvasKit (wasm) servido pelo gstatic quando não é empacotado.
    ('script-src', ("'self'", "'wasm-unsafe-eval'", 'https://www.gstatic.com')),
    ('style-src', ("'self'", "'unsafe-inline'")),
    ('img-src', ("'self'", 'data:', 'blob:', 'https:')),
    ('font-src', ("'self'", 'data:', 'https://fonts.gstatic.com')),
    # API em outra origem (API_BASE_URL) e Firebase: a lista exata sai do build validado.
    ('connect-src', ("'self'", 'https:')),
    ('object-src', ("'none'",)),
    ('base-uri', ("'self'",)),
    ('frame-ancestors', ("'self'",)),
)

PAYMENT_DIRECTIVES = (
    ('default-src', ("'self'",)),
    ('script-src', ("'self'", 'https://sdk.mercadopago.com', 'https://http2.mlstatic.com')),
    ('style-src', ("'self'", "'unsafe-inline'", 'https://http2.mlstatic.com')),
    ('img-src', ("'self'", 'data:', 'https:')),
    ('font-src', ("'self'", 'data:', 'https://http2.mlstatic.com')),
    ('connect-src', ("'self'", 'https://api.mercadopago.com', 'https://api.mercadolibre.com',
                     'https://events.mercadopago.com')),
    ('frame-src', ('https://*.mercadopago.com', 'https://*.mercadolibre.com', 'https://*.mercadolivre.com')),
    ('object-src', ("'none'",)),
    ('base-uri', ("'self'",)),
    ('form-action', ("'self'",)),
    ('frame-ancestors', ("'self'",)),
)

ENFORCE = 'enforce'
REPORT_ONLY = 'report-only'


def serialize(directives):
    return '; '.join(f"{name} {' '.join(values)}" for name, values in directives)


def spa_mode(env_value, is_production):
    """Modo da política da SPA a partir de ``CSP_MODE`` (valor inválido cai no padrão)."""
    value = str(env_value or '').strip().lower()
    if value in (ENFORCE, REPORT_ONLY):
        return value
    return REPORT_ONLY if is_production else ENFORCE


def surface_for_path(path):
    path = str(path or '')
    if path in ('/app', '/flutter_web') or path.startswith(('/app/', '/flutter_web/')):
        return 'flutter'
    if path in ('/pagamento.html', '/pagamento', '/checkout'):
        return 'payment'
    return 'spa'


def policy_for_path(path, *, mode, report_uri=''):
    """(nome do cabeçalho, valor) da CSP para ``path``."""
    surface = surface_for_path(path)
    if surface == 'flutter':
        header, directives = 'Content-Security-Policy-Report-Only', FLUTTER_DIRECTIVES
    elif surface == 'payment':
        header, directives = 'Content-Security-Policy-Report-Only', PAYMENT_DIRECTIVES
    else:
        header = 'Content-Security-Policy' if mode == ENFORCE else 'Content-Security-Policy-Report-Only'
        directives = SPA_DIRECTIVES
    value = serialize(directives)
    if report_uri:
        value = f'{value}; report-uri {report_uri}'
    return header, value
