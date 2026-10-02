"""F-01 — gestão de usuários não pode confiar em `actor_user_id` do cliente.

`POST /api/users` e `PUT /api/users/{id}` liam `actor_user_id` direto do corpo
e o tratavam como ator autorizado. O token era ignorado, então:

  A) sem token + actor_user_id de master  → criava/alterava como master;
  B) token de baixo privilégio + actor_user_id de master → escalava;

independentemente do modo de enforcement do JWT (o furo vivia FORA de
`resolve_actor_user_id`, que é onde o contrato token↔ator é imposto).

A correção liga os dois handlers a `resolve_actor_user_id`, como todas as
demais rotas autenticadas. Estes testes travam a propriedade:

    a autoridade usada para autorizar NÃO pode ser escolhida pelo cliente.

Rodam sem banco: nos casos de recusa, `resolve_actor_user_id` levanta ANTES de
`get_connection`; no caso coerente, `get_connection` e o service são
substituídos para capturar qual ator chegou ao service.
"""

import pytest

import core.security as seguranca
import modules.users.routes as routes

AuthenticationError = seguranca.AuthenticationError


class _Handler:
    def __init__(self, auth=''):
        self.headers = {'Authorization': auth} if auth else {}
        self.command = 'POST'
        self.client_address = ('127.0.0.1',)


class _Parsed:
    def __init__(self, query='', path='/api/users'):
        self.query = query
        self.path = path


def _bearer(user_id, role='registry_admin', company_id=1):
    return 'Bearer ' + seguranca.create_jwt_token(
        {'id': user_id, 'role': role, 'company_id': company_id}
    )


_VALID_BODY = {'username': 'novo@x.com', 'full_name': 'Novo', 'role': 'registry_admin'}


@pytest.fixture
def capture_service(monkeypatch):
    """Substitui banco e service: o alvo é QUAL ator a rota entrega ao service."""
    captured = {}

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def close(self):
            pass

    monkeypatch.setattr(routes, 'get_connection', lambda: _Conn())

    def _fake_create(connection, payload, *, actor_user_id):
        captured['actor_user_id'] = actor_user_id

    def _fake_update(connection, user_id, payload, *, actor_user_id):
        captured['actor_user_id'] = actor_user_id

    monkeypatch.setattr(routes, 'create_user', _fake_create)
    monkeypatch.setattr(routes, 'update_user', _fake_update)
    # send_json não pode tocar socket real.
    monkeypatch.setattr(routes, 'send_json', lambda handler, status, payload: status)
    return captured


# ── POST-A / PUT-A: sem token é recusado quando o JWT é exigido ──────────────

def test_post_sem_token_em_enforce_recusa(monkeypatch):
    monkeypatch.setattr(seguranca, 'JWT_ENFORCEMENT_MODE', 'enforce')
    body = {**_VALID_BODY, 'actor_user_id': 1}  # tenta operar como master
    with pytest.raises(AuthenticationError):
        routes.handle_post_users(_Handler(), _Parsed(), body, None)


def test_put_sem_token_em_enforce_recusa(monkeypatch):
    monkeypatch.setattr(seguranca, 'JWT_ENFORCEMENT_MODE', 'enforce')
    body = {**_VALID_BODY, 'actor_user_id': 1}

    class _M:
        def group(self, _):
            return '9'

    with pytest.raises(AuthenticationError):
        routes.handle_put_user(_Handler(), _Parsed(path='/api/users/9'), body, _M())


# ── POST-B/C / PUT-B/C: token válido + ator alheio no corpo é recusado ───────
# Independe do modo: é o contrato de coerência token↔ator (#337), 403.

@pytest.mark.parametrize('mode', ['off', 'shadow', 'enforce'])
def test_post_mismatch_token_baixo_privilegio_vs_master_recusa(monkeypatch, mode):
    monkeypatch.setattr(seguranca, 'JWT_ENFORCEMENT_MODE', mode)
    handler = _Handler(auth=_bearer(5, role='registry_admin'))
    body = {**_VALID_BODY, 'actor_user_id': 1}  # Bearer=5, corpo diz master=1
    with pytest.raises(PermissionError) as exc:
        routes.handle_post_users(handler, _Parsed(), body, None)
    assert not isinstance(exc.value, AuthenticationError)  # 403, não 401


@pytest.mark.parametrize('mode', ['off', 'shadow', 'enforce'])
def test_put_mismatch_token_vs_corpo_recusa(monkeypatch, mode):
    monkeypatch.setattr(seguranca, 'JWT_ENFORCEMENT_MODE', mode)
    handler = _Handler(auth=_bearer(5))
    body = {**_VALID_BODY, 'actor_user_id': 1}

    class _M:
        def group(self, _):
            return '9'

    with pytest.raises(PermissionError) as exc:
        routes.handle_put_user(handler, _Parsed(path='/api/users/9'), body, _M())
    assert not isinstance(exc.value, AuthenticationError)


# ── POST-E / PUT-E: ator coerente chega ao service COMO O DO TOKEN ───────────
# Prova que a autoridade vem do resolver, não do corpo: mesmo com o corpo
# repetindo o id, é o id autenticado (token) que o service recebe.

def test_post_ator_coerente_passa_o_ator_resolvido(capture_service, monkeypatch):
    monkeypatch.setattr(seguranca, 'JWT_ENFORCEMENT_MODE', 'enforce')
    handler = _Handler(auth=_bearer(7))
    body = {**_VALID_BODY, 'actor_user_id': 7}
    routes.handle_post_users(handler, _Parsed(), body, None)
    assert capture_service['actor_user_id'] == 7


def test_put_ator_coerente_passa_o_ator_resolvido(capture_service, monkeypatch):
    monkeypatch.setattr(seguranca, 'JWT_ENFORCEMENT_MODE', 'enforce')
    handler = _Handler(auth=_bearer(7))
    body = {**_VALID_BODY, 'actor_user_id': 7}

    class _M:
        def group(self, _):
            return '9'

    routes.handle_put_user(handler, _Parsed(path='/api/users/9'), body, _M())
    assert capture_service['actor_user_id'] == 7


# ── Contrato de assinatura: o service exige o ator por keyword ───────────────
# Impede a reintrodução de `payload['actor_user_id']` como autoridade: o ator
# é um parâmetro keyword-only, fornecido pela rota já resolvido.

def test_service_exige_actor_user_id_keyword_only():
    import inspect

    import modules.users.service as svc
    for fn in (svc.create_user, svc.update_user):
        p = inspect.signature(fn).parameters
        assert 'actor_user_id' in p, f'{fn.__name__} sem actor_user_id'
        assert p['actor_user_id'].kind is inspect.Parameter.KEYWORD_ONLY, \
            f'{fn.__name__}: actor_user_id precisa ser keyword-only'
        assert p['actor_user_id'].default is inspect.Parameter.empty, \
            f'{fn.__name__}: actor_user_id não pode ter default (forçaria o chamador a resolvê-lo)'
