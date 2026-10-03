"""F-01 — gestão de usuários não pode confiar em `actor_user_id` do cliente.

`POST /api/users` e `PUT /api/users/{id}` liam `actor_user_id` direto do corpo
e o tratavam como ator autorizado. O token era ignorado, então um
`actor_user_id` forjado (ex.: o master do bootstrap) criava/alterava usuários —
inclusive trocando senha — em qualquer empresa.

A correção tem duas camadas, e estes testes travam as DUAS:

1. **Rota** — `POST/PUT /api/users` exigem Bearer SEMPRE (operação
   privilegiada), mesmo com o rollout global do JWT em ``off``/``shadow``, e
   derivam o ator de `resolve_actor_user_id`. Sem token → 401; token + ator
   divergente → 403 (#337). (classe `TestRota`)

2. **Service** — `create_user`/`update_user` autorizam com o `actor_user_id`
   RECEBIDO da rota, nunca com `payload['actor_user_id']`; e
   `authorize_user_management` barra cross-tenant e perfil sem privilégio.
   Estes medem a IDENTIDADE que chega à autorização e a regra de tenant —
   com o service REAL, não um dublê. (classes `TestServiceAtor`,
   `TestServiceTenant`)

Rodam sem banco: a rota levanta antes de `get_connection`; o service é
exercido de verdade, com apenas o SINK de autorização/DB instrumentado para
capturar o ator ou parar a execução no ponto medido.
"""

import inspect

import pytest

import core.security as seguranca
import modules.users.routes as routes
import modules.users.service as svc

AuthenticationError = seguranca.AuthenticationError
MODES = ('off', 'shadow', 'enforce')


# ─────────────────────────────────────────────────────────────────────────────
# Dublês mínimos
# ─────────────────────────────────────────────────────────────────────────────

class _Handler:
    command = 'POST'
    client_address = ('127.0.0.1',)

    def __init__(self, auth=''):
        self.headers = {'Authorization': auth} if auth else {}


class _Parsed:
    def __init__(self, query='', path='/api/users'):
        self.query = query
        self.path = path


class _Match:
    def __init__(self, uid='9'):
        self._uid = uid

    def group(self, _):
        return self._uid


def _bearer(user_id, role='registry_admin', company_id=1):
    return 'Bearer ' + seguranca.create_jwt_token(
        {'id': user_id, 'role': role, 'company_id': company_id}
    )


_VALID_BODY = {'username': 'novo@x.com', 'full_name': 'Novo', 'role': 'registry_admin'}


# ─────────────────────────────────────────────────────────────────────────────
# 1. ROTA — Bearer obrigatório e coerência, nos três modos globais
# ─────────────────────────────────────────────────────────────────────────────

class _ReachedDB(Exception):
    """Sentinela: a rota chegou a `get_connection`. Numa recusa correta isso
    NUNCA acontece (a negativa vem antes). Se uma sabotagem deixar a request
    passar, o teste falha por ESTE sinal — explícito e sem depender de banco —
    em vez de um `RuntimeError: DATABASE_URL` incidental."""


class TestRota:
    @pytest.fixture
    def no_db(self, monkeypatch):
        """Para os testes de RECUSA: qualquer acesso a banco é 'passou indevido'."""
        def _boom():
            raise _ReachedDB
        monkeypatch.setattr(routes, 'get_connection', _boom)

    @pytest.fixture
    def capture_service(self, monkeypatch):
        """Substitui só banco + service: o alvo é QUAL ator a rota entrega."""
        captured = {}

        class _Conn:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def close(self):
                pass

        monkeypatch.setattr(routes, 'get_connection', lambda: _Conn())
        monkeypatch.setattr(routes, 'create_user',
                            lambda connection, payload, *, actor_user_id: captured.__setitem__('actor', actor_user_id))
        monkeypatch.setattr(routes, 'update_user',
                            lambda connection, user_id, payload, *, actor_user_id: captured.__setitem__('actor', actor_user_id))
        monkeypatch.setattr(routes, 'send_json', lambda handler, status, payload: status)
        return captured

    def _call(self, verb, handler, body):
        if verb == 'POST':
            return routes.handle_post_users(handler, _Parsed(), body, None)
        return routes.handle_put_user(handler, _Parsed(path='/api/users/9'), body, _Match())

    # sem token → 401 em TODOS os modos (exigência LOCAL; não só enforce)
    @pytest.mark.parametrize('verb', ['POST', 'PUT'])
    @pytest.mark.parametrize('mode', MODES)
    def test_sem_token_recusa_em_todos_os_modos(self, monkeypatch, no_db, verb, mode):
        monkeypatch.setattr(seguranca, 'JWT_ENFORCEMENT_MODE', mode)
        body = {**_VALID_BODY, 'actor_user_id': 1}  # tenta operar como master
        with pytest.raises(AuthenticationError):
            self._call(verb, _Handler(), body)

    # Bearer malformado → 401
    @pytest.mark.parametrize('verb', ['POST', 'PUT'])
    @pytest.mark.parametrize('mode', MODES)
    def test_bearer_malformado_recusa(self, monkeypatch, no_db, verb, mode):
        monkeypatch.setattr(seguranca, 'JWT_ENFORCEMENT_MODE', mode)
        body = {**_VALID_BODY, 'actor_user_id': 1}
        with pytest.raises(AuthenticationError):
            self._call(verb, _Handler(auth='Token xyz'), body)

    # token válido + ator alheio no corpo → 403 (coerência #337), em todos os modos
    @pytest.mark.parametrize('verb', ['POST', 'PUT'])
    @pytest.mark.parametrize('mode', MODES)
    def test_mismatch_token_vs_corpo_recusa(self, monkeypatch, no_db, verb, mode):
        monkeypatch.setattr(seguranca, 'JWT_ENFORCEMENT_MODE', mode)
        body = {**_VALID_BODY, 'actor_user_id': 1}  # Bearer=5, corpo diz master=1
        with pytest.raises(PermissionError) as exc:
            self._call(verb, _Handler(auth=_bearer(5)), body)
        assert not isinstance(exc.value, AuthenticationError)  # 403, não 401

    # token válido + query actor alheio → 403 (o resolver olha body E query)
    @pytest.mark.parametrize('mode', MODES)
    def test_mismatch_token_vs_query_recusa(self, monkeypatch, no_db, mode):
        monkeypatch.setattr(seguranca, 'JWT_ENFORCEMENT_MODE', mode)
        body = {**_VALID_BODY, 'actor_user_id': 7}
        handler = _Handler(auth=_bearer(7))
        with pytest.raises(PermissionError) as exc:
            routes.handle_post_users(handler, _Parsed(query='actor_user_id=1'), body, None)
        assert not isinstance(exc.value, AuthenticationError)

    # ator coerente → a rota entrega ao service o ator DO TOKEN, em todos os modos
    @pytest.mark.parametrize('verb', ['POST', 'PUT'])
    @pytest.mark.parametrize('mode', MODES)
    def test_ator_coerente_passa_o_ator_resolvido(self, monkeypatch, capture_service, verb, mode):
        monkeypatch.setattr(seguranca, 'JWT_ENFORCEMENT_MODE', mode)
        body = {**_VALID_BODY, 'actor_user_id': 7}
        self._call(verb, _Handler(auth=_bearer(7)), body)
        assert capture_service['actor'] == 7


# ─────────────────────────────────────────────────────────────────────────────
# 2. SERVICE — autoriza com o ator RECEBIDO, nunca com o payload (pega SAB-C)
# ─────────────────────────────────────────────────────────────────────────────

class _StopAtAuthz(Exception):
    """Interrompe create_user/update_user logo após a autorização — o único
    ponto que estes testes medem — sem precisar de banco para o resto."""


class TestServiceAtor:
    @pytest.fixture
    def spy_authz(self, monkeypatch):
        seen = {}

        def _spy(connection, actor_user_id, operation='create', *a, **k):
            seen['actor'] = int(actor_user_id)
            seen['operation'] = operation
            raise _StopAtAuthz

        monkeypatch.setattr(svc, 'authorize_user_management', _spy)
        return seen

    # payload MENTE (999); a rota resolveu 7 → o service tem de autorizar como 7.
    # Sob SAB-C (service relê payload) o capturado seria 999 → este assert quebra,
    # e a falha aponta o ATOR ERRADO, não uma exceção incidental de banco.
    def test_create_user_autoriza_com_ator_recebido(self, spy_authz):
        payload = {**_VALID_BODY, 'actor_user_id': 999, 'company_id': 2}
        with pytest.raises(_StopAtAuthz):
            svc.create_user(object(), payload, actor_user_id=7)
        assert spy_authz['actor'] == 7, 'service autorizou com ator ERRADO (payload?)'
        assert spy_authz['operation'] == 'create'

    def test_update_user_autoriza_com_ator_recebido(self, spy_authz):
        payload = {**_VALID_BODY, 'actor_user_id': 999, 'company_id': 2}
        with pytest.raises(_StopAtAuthz):
            svc.update_user(object(), 20, payload, actor_user_id=7)
        assert spy_authz['actor'] == 7, 'service autorizou com ator ERRADO (payload?)'
        assert spy_authz['operation'] == 'update'

    # Contrato de assinatura: ator keyword-only e sem default (o chamador DEVE
    # resolvê-lo; impede reintroduzir leitura do payload por baixo).
    def test_assinatura_keyword_only_sem_default(self):
        for fn in (svc.create_user, svc.update_user):
            p = inspect.signature(fn).parameters
            assert 'actor_user_id' in p, f'{fn.__name__} sem actor_user_id'
            assert p['actor_user_id'].kind is inspect.Parameter.KEYWORD_ONLY, \
                f'{fn.__name__}: actor_user_id precisa ser keyword-only'
            assert p['actor_user_id'].default is inspect.Parameter.empty, \
                f'{fn.__name__}: actor_user_id não pode ter default'


# ─────────────────────────────────────────────────────────────────────────────
# 3. SERVICE — isolamento de tenant e privilégio (pega SAB-E), com a REGRA real
# ─────────────────────────────────────────────────────────────────────────────

class TestServiceTenant:
    """Exercita `authorize_user_management` de verdade; instrumenta apenas o
    carregamento do ator e do alvo (que, em produção, vêm do banco). A regra
    de tenant (`ensure_company_access`) é a função REAL — se a sabotagem SAB-E
    remover as chamadas dela, estes testes ficam vermelhos.

    NÃO depende do vínculo de colaborador (que no Corporate produziria 403 por
    outro motivo): aqui o ator é administrativo e o 403 só pode vir da regra de
    empresa.
    """

    def _wire(self, monkeypatch, actor, target=None):
        monkeypatch.setattr(svc, 'authorize_action', lambda connection, aid, action, **k: dict(actor))
        monkeypatch.setattr(svc, 'get_user_by_id', lambda connection, uid: (dict(target) if target else None))

    def test_create_cross_tenant_bloqueado(self, monkeypatch):
        # general_admin da empresa 1 tenta criar na empresa 2 (target_company_id=2)
        self._wire(monkeypatch, {'id': 10, 'role': 'general_admin', 'company_id': 1, 'active': 1})
        with pytest.raises(PermissionError):
            svc.authorize_user_management(None, 10, 'create', 'registry_admin', None, 2)

    def test_update_cross_tenant_bloqueado(self, monkeypatch):
        # general_admin da empresa 1 tenta editar usuário da empresa 2
        self._wire(monkeypatch,
                   {'id': 10, 'role': 'general_admin', 'company_id': 1, 'active': 1},
                   {'id': 20, 'role': 'registry_admin', 'company_id': 2})
        with pytest.raises(PermissionError):
            svc.authorize_user_management(None, 10, 'update', 'registry_admin', 20, None)

    def test_mesmo_tenant_permitido(self, monkeypatch):
        # Prova positiva: mesma empresa (1) → autoriza, retornando o ator.
        self._wire(monkeypatch,
                   {'id': 10, 'role': 'general_admin', 'company_id': 1, 'active': 1},
                   {'id': 20, 'role': 'registry_admin', 'company_id': 1})
        actor = svc.authorize_user_management(None, 10, 'update', 'registry_admin', 20, 1)
        assert actor['id'] == 10

    @pytest.mark.parametrize('role', ['admin', 'user', 'buyer'])
    def test_perfil_sem_privilegio_bloqueado(self, monkeypatch, role):
        # Perfil operacional/sem gestão de usuários → PermissionError.
        self._wire(monkeypatch, {'id': 10, 'role': role, 'company_id': 1, 'active': 1})
        with pytest.raises(PermissionError):
            svc.authorize_user_management(None, 10, 'create', 'registry_admin', None, 1)
