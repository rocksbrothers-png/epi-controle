"""Auditoria F-04 — rollout do JWT Bearer em resolve_actor_user_id.

Hoje o actor_user_id é aceito via body/query sem um Bearer token válido. A flag
JWT_ENFORCEMENT_MODE controla o rollout seguro:
  - off:     comportamento legado silencioso;
  - shadow:  registra a requisição sem JWT mas permite (medição de impacto);
  - enforce: exige o token e bloqueia (403) quando ausente.

Um Bearer token válido sempre é aceito, em qualquer modo. A verificação de
consistência entre body/query/token é independente do modo.
"""

import json
from urllib.parse import urlparse

import pytest

import core.security as security
from core.security import create_jwt_token, resolve_actor_user_id


class _Handler:
    def __init__(self, auth=None, command='POST'):
        self.headers = {'Authorization': auth} if auth else {}
        self.command = command
        self.client_address = ('10.0.0.1', 5555)


def _parsed(query='actor_user_id=5'):
    return urlparse(f'/api/x?{query}')


@pytest.fixture
def mode(monkeypatch):
    def _set(value):
        monkeypatch.setattr(security, 'JWT_ENFORCEMENT_MODE', value)
    return _set


# ── Sem token (body/query) ────────────────────────────────────────────────────

def test_off_allows_without_jwt_and_is_silent(mode, capsys):
    mode('off')
    assert resolve_actor_user_id(_Handler(), _parsed(''), {'actor_user_id': 5}) == 5
    assert capsys.readouterr().out.strip() == ''


def test_shadow_allows_without_jwt_but_logs(mode, capsys):
    mode('shadow')
    assert resolve_actor_user_id(_Handler(), _parsed(''), {'actor_user_id': 5}) == 5
    out = capsys.readouterr().out.strip()
    record = json.loads(out.splitlines()[-1])
    assert record['event'] == 'auth.actor_without_jwt'
    assert record['mode'] == 'shadow' and record['actor_user_id'] == '5'


def test_enforce_blocks_without_jwt(mode):
    mode('enforce')
    with pytest.raises(PermissionError, match='JWT Bearer'):
        resolve_actor_user_id(_Handler(), _parsed(''), {'actor_user_id': 5})


def test_enforce_blocks_query_only_actor(mode):
    mode('enforce')
    with pytest.raises(PermissionError, match='JWT Bearer'):
        resolve_actor_user_id(_Handler(), _parsed('actor_user_id=5'), None)


# ── Com token válido ──────────────────────────────────────────────────────────

def _valid_token():
    return create_jwt_token({'id': 5, 'role': 'admin', 'company_id': 1})


def test_valid_jwt_is_accepted_in_enforce(mode, capsys):
    mode('enforce')
    h = _Handler(auth=f'Bearer {_valid_token()}')
    assert resolve_actor_user_id(h, _parsed(''), {'actor_user_id': 5}) == 5
    # token válido → nenhum aviso de ausência de JWT
    assert 'auth.actor_without_jwt' not in capsys.readouterr().out


def test_valid_jwt_alone_resolves_actor(mode):
    mode('enforce')
    h = _Handler(auth=f'Bearer {_valid_token()}')
    assert resolve_actor_user_id(h, _parsed(''), None) == 5


# ── Consistência (independe do modo) ──────────────────────────────────────────

def test_body_token_mismatch_always_raises(mode):
    mode('shadow')
    h = _Handler(auth=f'Bearer {_valid_token()}')
    with pytest.raises(PermissionError, match='inconsistentes'):
        resolve_actor_user_id(h, _parsed(''), {'actor_user_id': 9})


def test_no_actor_at_all_raises(mode):
    mode('off')
    with pytest.raises(PermissionError, match='usuário não informado'):
        resolve_actor_user_id(_Handler(), _parsed(''), None)
