"""Regressão: dispatch deve sinalizar 'handled' mesmo quando o handler retorna None.

Bug de produção: handlers terminam em `return send_json(...)`, que retorna None.
do_GET/do_POST tratavam None como 'rota não encontrada' e caíam no fallback
(servir arquivo estático / not_found), gerando uma segunda resposta espúria no
mesmo socket → 404/500 + BrokenPipe nos logs do Render para /api/ficha-archive
e demais GETs de API.
"""

from core.router import Router, HANDLED


def _noop_handler_returning_none(handler_obj, parsed, payload, match):
    # Simula um handler que já escreveu a resposta (send_json) e retorna None.
    return None


def _handler_returning_value(handler_obj, parsed, payload, match):
    return 'explicit-value'


def test_dispatch_returns_handled_sentinel_when_handler_returns_none():
    r = Router()
    r.register('GET', '/api/ficha-archive', _noop_handler_returning_none)
    result = r.dispatch('GET', '/api/ficha-archive', None, None)
    assert result is HANDLED
    assert result is not None  # do_GET: `if result is not None` -> não cai no fallback


def test_dispatch_preserves_explicit_truthy_return():
    r = Router()
    r.register('GET', '/api/x', _handler_returning_value)
    assert r.dispatch('GET', '/api/x', None, None) == 'explicit-value'


def test_dispatch_returns_none_when_no_route_matches():
    r = Router()
    r.register('GET', '/api/x', _noop_handler_returning_none)
    # Caminho não registrado -> None -> chamador segue para fallback (estático/404).
    assert r.dispatch('GET', '/api/nao-existe', None, None) is None


def test_dispatch_regex_route_returns_handled_when_none():
    r = Router()
    r.register('GET', r'/api/ficha-archive/(\d+)\.html', _noop_handler_returning_none, regex=True)
    result = r.dispatch('GET', '/api/ficha-archive/1.html', None, None)
    assert result is HANDLED


def test_dispatch_method_mismatch_returns_none():
    r = Router()
    r.register('POST', '/api/x', _noop_handler_returning_none)
    assert r.dispatch('GET', '/api/x', None, None) is None
