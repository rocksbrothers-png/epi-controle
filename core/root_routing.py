"""Roteamento da raiz `/` durante o cutover legado → Flutter Web (Fase 6).

Lógica pura e testável. A virada de `/` para o Flutter é controlada por uma
feature flag de ambiente (default OFF) — assim o rollback é uma troca de config,
sem alterar código:

    FLUTTER_WEB_ROOT_REDIRECT = 1|true|yes|on   → `/` redireciona para `/app/`

Independente da flag, o legado fica sempre acessível em `/legacy/` (saída de
emergência), garantindo o invariante: o login do legado nunca pode quebrar.
"""

import os

# Caminhos de emergência que sempre servem o legado, qualquer que seja a flag.
_LEGACY_PATHS = frozenset({'/legacy', '/legacy/', '/legacy/index.html'})
# Caminhos da raiz que são redirecionados quando o cutover está ligado.
_ROOT_PATHS = frozenset({'/', '/index.html'})

_TRUTHY = frozenset({'1', 'true', 'yes', 'on'})


def is_flutter_root_redirect_enabled(env=None):
    """Lê a flag de ambiente (default OFF)."""
    source = env if env is not None else os.environ
    return str(source.get('FLUTTER_WEB_ROOT_REDIRECT', '') or '').strip().lower() in _TRUTHY


def resolve_root_request(path, *, redirect_enabled):
    """Decide o tratamento da raiz. Retorna (action, target):

    - ('redirect', '/app/')   → 307 para o Flutter Web (cutover ligado).
    - ('legacy', '/index.html') → servir o legado (rota /legacy/ de emergência).
    - ('passthrough', None)   → seguir o fluxo normal de serving (default).
    """
    p = str(path or '')
    if p in _LEGACY_PATHS:
        return ('legacy', '/index.html')
    if redirect_enabled and p in _ROOT_PATHS:
        return ('redirect', '/app/')
    return ('passthrough', None)
