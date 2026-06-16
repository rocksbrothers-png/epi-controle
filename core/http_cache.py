"""Política de cache HTTP (pura e testável).

Extraída de app.py (Fase 1 do plano de migração) e corrige o resíduo da Fase 3:
os assets do Flutter Web (sob /app/, com nome versionado pelo build) recebiam
`no-store` junto com todo .js/.css, o que forçava novo download a cada acesso.

Regras:
- APIs / health / ready: sempre `no-store` (resposta dinâmica).
- Shells de SPA (legado `/`, `/index.html`; Flutter `/app/`, `/app/index.html`)
  e arquivos do Flutter que referenciam assets versionados (service worker,
  version.json, manifest, bootstrap): `no-store` — precisam estar sempre frescos.
- Demais arquivos sob `/app/` (assets versionados do Flutter): cache longo e
  imutável.
- `.js`/`.css` do legado (fora de `/app/`, com cache-bust via `?v=`): `no-store`.
- Qualquer outro caminho: sem header de Cache-Control (comportamento anterior).
"""

NO_STORE = 'no-store, max-age=0, must-revalidate'
IMMUTABLE = 'public, max-age=31536000, immutable'

# Caminhos exatos que nunca devem ser cacheados (shells + arquivos de versão).
NO_STORE_EXACT_PATHS = frozenset({
    '/', '/index.html', '/app.js', '/styles.css', '/error-monitor.js',
    '/app', '/app/', '/app/index.html',
    '/app/flutter_service_worker.js', '/app/version.json',
    '/app/manifest.json', '/app/flutter_bootstrap.js',
})


def resolve_cache_control(path):
    """Retorna o valor de Cache-Control para `path`, ou '' quando não se aplica.

    Recebe o caminho já normalizado (sem query string). Função pura.
    """
    p = str(path or '')
    if p.startswith('/api/') or p.startswith('/health') or p.startswith('/ready'):
        return NO_STORE
    if p in NO_STORE_EXACT_PATHS:
        return NO_STORE
    # Assets do Flutter Web (sob /app/) são versionados pelo build → imutáveis.
    # Rotas de cliente do Flutter (ex.: /app/dashboard) são reescritas para
    # /app/index.html antes deste ponto, então só chegam aqui arquivos reais.
    if p.startswith('/app/'):
        return IMMUTABLE
    # JS/CSS do legado usam cache-bust por querystring → sempre revalidar.
    if p.endswith('.js') or p.endswith('.css'):
        return NO_STORE
    return ''


def is_no_store(cache_control_value):
    """Indica se o valor exige também os headers legados Pragma/Expires."""
    return str(cache_control_value or '').startswith('no-store')
