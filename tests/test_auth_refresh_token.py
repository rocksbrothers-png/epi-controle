"""Refresh token (segurança incremental) — emissão, tipo e reemissão de access.

Aditivo e retrocompatível: tokens antigos sem claim `type` valem como 'access'.
"""

import sqlite3

import pytest

from core.security import (
    create_jwt_token,
    create_refresh_token,
    decode_jwt_token,
    decode_token_of_type,
)
import modules.auth.service as auth_service


USER = {'id': 9, 'role': 'general_admin', 'company_id': 1, 'active': 1}


# ── tipos de token ────────────────────────────────────────────────────────────

def test_access_token_has_type_access():
    payload = decode_jwt_token(create_jwt_token(USER))
    assert payload['type'] == 'access'
    assert payload['sub'] == 9 and payload['role'] == 'general_admin'


def test_refresh_token_has_type_refresh_and_minimal_claims():
    payload = decode_jwt_token(create_refresh_token(USER))
    assert payload['type'] == 'refresh'
    assert payload['sub'] == 9
    assert 'role' not in payload  # claims mínimas no refresh


def test_refresh_token_lives_longer_than_access():
    acc = decode_jwt_token(create_jwt_token(USER))
    ref = decode_jwt_token(create_refresh_token(USER))
    assert ref['exp'] > acc['exp']


# ── decode_token_of_type ──────────────────────────────────────────────────────

def test_decode_of_type_accepts_matching():
    assert decode_token_of_type(create_refresh_token(USER), 'refresh')['sub'] == 9
    assert decode_token_of_type(create_jwt_token(USER), 'access')['sub'] == 9


def test_decode_of_type_rejects_access_used_as_refresh():
    with pytest.raises(PermissionError):
        decode_token_of_type(create_jwt_token(USER), 'refresh')


def test_decode_of_type_rejects_refresh_used_as_access():
    with pytest.raises(PermissionError):
        decode_token_of_type(create_refresh_token(USER), 'access')


def test_legacy_token_without_type_is_access():
    # token sem claim `type` (formato anterior) deve valer como access
    from core.security import _encode_jwt
    from datetime import datetime, timezone
    now = int(datetime.now(timezone.utc).timestamp())
    legacy = _encode_jwt({'sub': 9, 'role': 'admin', 'company_id': 1, 'iat': now, 'exp': now + 3600})
    assert decode_token_of_type(legacy, 'access')['sub'] == 9


# ── login inclui refresh_token ────────────────────────────────────────────────

def _dict_factory(cursor, row):
    # authenticate_login usa row.get(...) (compatível com DictRow do Postgres);
    # sqlite3.Row não tem .get, então devolvemos dicts.
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = _dict_factory
    conn.executescript("""
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT, cnpj TEXT, logo_type TEXT DEFAULT '',
            active INTEGER DEFAULT 1, license_status TEXT DEFAULT 'active', user_limit INTEGER DEFAULT 25,
            contract_end TEXT DEFAULT '', addendum_enabled INTEGER DEFAULT 0);
        CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, full_name TEXT,
            role TEXT, company_id INTEGER, active INTEGER DEFAULT 1, linked_employee_id INTEGER);
        INSERT INTO companies (id, name, cnpj) VALUES (1, 'ACME', '1');
        -- master_admin (company_id NULL) evita o caminho enforce_company_block_rules,
        -- que vive em core.repository com placeholders %s (somente Postgres).
        INSERT INTO users (id, username, password, full_name, role, company_id, active)
            VALUES (9, 'jeff', 'segredo123', 'Jeff', 'master_admin', NULL, 1);
    """)
    conn.commit()
    return conn


def test_login_response_includes_refresh_token():
    conn = _conn()
    response, status, error = auth_service.authenticate_login(conn, 'jeff', 'segredo123')
    assert status == 200 and error is None
    assert 'refresh_token' in response and response['refresh_token']
    assert decode_jwt_token(response['refresh_token'])['type'] == 'refresh'
    assert response['refresh_expires_in'] > response['token_expires_in']


def test_login_response_includes_top_level_permissions():
    """Contrato consumido pelo Flutter (LoginResponse): `permissions` vem no
    TOPO da resposta (não dentro de `user`). O cliente Flutter lia
    `user['permissions']` (inexistente) e rodava o RBAC sem permissões — esta
    asserção trava o contrato do lado backend para essa correção (Sprint 1)."""
    conn = _conn()
    response, status, error = auth_service.authenticate_login(conn, 'jeff', 'segredo123')
    assert status == 200 and error is None
    assert isinstance(response.get('permissions'), list)
    assert response['permissions'], 'permissions não pode ser vazio para master_admin'
    assert 'dashboard:view' in response['permissions']
    # Não deve estar aninhado em user (origem do bug RBAC no Flutter).
    assert 'permissions' not in response['user']
    # Lista ordenada e sem senha vazando.
    assert response['permissions'] == sorted(response['permissions'])
    assert 'password' not in response['user']


# ── refresh_access_token reemite access ───────────────────────────────────────

def test_refresh_access_token_issues_new_access():
    conn = _conn()
    refresh = create_refresh_token({'id': 9})  # usuário master_admin no seed
    response, status, error = auth_service.refresh_access_token(conn, refresh)
    assert status == 200 and error is None
    assert decode_jwt_token(response['token'])['type'] == 'access'
    assert decode_jwt_token(response['token'])['sub'] == 9
    # rotaciona o refresh
    assert decode_jwt_token(response['refresh_token'])['type'] == 'refresh'


def test_refresh_rejects_access_token():
    conn = _conn()
    with pytest.raises(PermissionError):
        auth_service.refresh_access_token(conn, create_jwt_token(USER))


def test_refresh_rejects_inactive_user():
    conn = _conn()
    conn.execute('UPDATE users SET active = 0 WHERE id = 9')
    conn.commit()
    response, status, error = auth_service.refresh_access_token(conn, create_refresh_token({'id': 9}))
    assert status == 401 and error['code'] == 'INVALID_REFRESH_TOKEN'
