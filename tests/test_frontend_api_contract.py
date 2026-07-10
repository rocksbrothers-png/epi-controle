"""Teste de contrato front↔back (recomendação da auditoria pré-produção).

Confronta cada chamada `api('/api/...')` do frontend legado (static/) com as
rotas realmente registradas no router. Pega a classe de bug de F-01
(chamada com método/rota que o backend não expõe → 404 silencioso) e de
F-02 (endpoint inexistente). É intencionalmente conservador: só falha em
divergências de caminho estático inequívocas, ignorando trechos com
interpolação dinâmica que não dá para resolver estaticamente.
"""

import glob
import os
import re

import pytest

import app  # noqa: F401 — registra as rotas no router
from app import router

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, 'static')

# Caminhos com segmentos dinâmicos que não conseguimos resolver estaticamente
# (o normalizador troca ${...} por '1', mas interpolações aninhadas ficam de fora).
_UNRESOLVABLE = ('${', '%7B')


def _compiled_routes():
    compiled = []
    for method, path, pattern, _handler in router._routes:
        is_regex = any(ch in path for ch in '(^$[')
        compiled.append((method, re.compile(path if is_regex else '^' + re.escape(path) + '$')))
    return compiled


def _backend_has(compiled, method, path):
    return any(m == method and pat.match(path) for m, pat in compiled)


def _extract_calls():
    calls = set()
    for f in glob.glob(os.path.join(STATIC, '**', '*.js'), recursive=True):
        src = open(f, encoding='utf-8').read()
        for m in re.finditer(
            r"""\bapi\(\s*[`'"](/api/[^`'"]*)[`'"]\s*(?:,\s*\{(.{0,160}?)(?:body|\}))?""",
            src, re.S,
        ):
            raw, opts = m.group(1), (m.group(2) or '')
            method = (re.search(r"method:\s*['\"](\w+)['\"]", opts) or [None, 'GET'])[1].upper()
            calls.add((method, raw, os.path.basename(f)))
    return calls


def _normalize(raw):
    # Parâmetros de segmento de caminho: /${id} → /1
    path = re.sub(r'/\$\{[^}]*\}', '/1', raw)
    # Querystring: um ? literal ou um ${...} "colado" (não iniciando um segmento)
    # marca o fim do caminho — ex.: `/api/purchase-orders${qs}`.
    path = re.split(r'\?|(?<!/)\$\{', path)[0]
    return path


def test_frontend_api_calls_have_backend_routes():
    compiled = _compiled_routes()
    problems = []
    for method, raw, fname in sorted(_extract_calls()):
        path = _normalize(raw)
        if any(tok in path for tok in _UNRESOLVABLE):
            continue  # interpolação não resolvível estaticamente
        if not _backend_has(compiled, method, path):
            problems.append(f'{method} {raw}  ({fname})')
    assert not problems, (
        'Chamadas de API do frontend sem rota correspondente no backend '
        '(regressão tipo F-01/F-02):\n  ' + '\n  '.join(problems)
    )
