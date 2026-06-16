import base64
import hashlib
import hmac
import json
from datetime import datetime
from urllib.parse import parse_qs

from epi_backend.config import (
    BCRYPT_AVAILABLE,
    JWT_EXP_SECONDS,
    JWT_REFRESH_EXP_SECONDS,
    JWT_SECRET,
    UTC,
)

try:
    import bcrypt
except ModuleNotFoundError:
    bcrypt = None


def validate_password_strength(password):
    raw = str(password or '').strip()
    if len(raw) < 6:
        raise ValueError('A senha deve ter pelo menos 6 caracteres.')
    return raw


def _jwt_b64encode(data_bytes):
    return base64.urlsafe_b64encode(data_bytes).decode('utf-8').rstrip('=')


def _jwt_b64decode(data):
    raw = str(data or '')
    padding = '=' * (-len(raw) % 4)
    return base64.urlsafe_b64decode((raw + padding).encode('utf-8'))


def _encode_jwt(payload):
    header_segment = _jwt_b64encode(json.dumps({'alg': 'HS256', 'typ': 'JWT'}, separators=(',', ':')).encode('utf-8'))
    payload_segment = _jwt_b64encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
    signing_input = f'{header_segment}.{payload_segment}'.encode('utf-8')
    signature = hmac.new(JWT_SECRET.encode('utf-8'), signing_input, hashlib.sha256).digest()
    signature_segment = _jwt_b64encode(signature)
    return f'{header_segment}.{payload_segment}.{signature_segment}'


def create_jwt_token(user_row):
    now_ts = int(datetime.now(UTC).timestamp())
    return _encode_jwt({
        'sub': int(user_row['id']),
        'role': user_row['role'],
        'company_id': user_row['company_id'],
        'type': 'access',
        'iat': now_ts,
        'exp': now_ts + JWT_EXP_SECONDS,
    })


def create_refresh_token(user_row):
    """Token de vida longa, com claims mínimas, para reemitir o access token."""
    now_ts = int(datetime.now(UTC).timestamp())
    return _encode_jwt({
        'sub': int(user_row['id']),
        'type': 'refresh',
        'iat': now_ts,
        'exp': now_ts + JWT_REFRESH_EXP_SECONDS,
    })


def parse_bearer_token(handler):
    auth_header = str(handler.headers.get('Authorization', '')).strip()
    if not auth_header:
        return ''
    if not auth_header.lower().startswith('bearer '):
        raise PermissionError('Formato de Authorization inválido.')
    return auth_header.split(' ', 1)[1].strip()


def decode_jwt_token(token, msg_token_absent='Token ausente.', msg_token_invalid='Token inválido.'):
    raw = str(token or '').strip()
    if not raw:
        raise PermissionError(msg_token_absent)
    parts = raw.split('.')
    if len(parts) != 3:
        raise PermissionError(msg_token_invalid)
    header_segment, payload_segment, signature_segment = parts
    signing_input = f'{header_segment}.{payload_segment}'.encode('utf-8')
    expected_signature = hmac.new(JWT_SECRET.encode('utf-8'), signing_input, hashlib.sha256).digest()
    provided_signature = _jwt_b64decode(signature_segment)
    if not hmac.compare_digest(expected_signature, provided_signature):
        raise PermissionError(msg_token_invalid)
    try:
        payload = json.loads(_jwt_b64decode(payload_segment).decode('utf-8'))
    except json.JSONDecodeError:
        raise PermissionError(msg_token_invalid)
    if int(payload.get('exp', 0)) < int(datetime.now(UTC).timestamp()):
        raise PermissionError('Sessão expirada. Faça login novamente.')
    return payload


def decode_token_of_type(token, expected_type, *, msg_token_invalid='Token inválido.'):
    """Decodifica e valida que o token é do tipo esperado ('access' | 'refresh').

    Tokens emitidos antes da introdução do claim `type` são tratados como
    'access' (compatibilidade retroativa).
    """
    payload = decode_jwt_token(token, msg_token_invalid=msg_token_invalid)
    token_type = str(payload.get('type') or 'access')
    if token_type != expected_type:
        raise PermissionError(msg_token_invalid)
    return payload


def resolve_actor_user_id(handler, parsed, payload=None):
    payload = payload or {}
    query_actor = parse_qs(parsed.query).get('actor_user_id', [''])[0]
    body_actor = str(payload.get('actor_user_id', '')).strip()
    token = parse_bearer_token(handler)
    token_actor = ''
    if token:
        claims = decode_jwt_token(token)
        token_actor = str(claims.get('sub', '')).strip()
    actor_candidates = [item for item in (body_actor, query_actor, token_actor) if str(item).strip()]
    if not actor_candidates:
        raise PermissionError('Sessão inválida: usuário não informado.')
    actor_user_id = actor_candidates[0]
    for candidate in actor_candidates[1:]:
        if str(candidate) != str(actor_user_id):
            raise PermissionError('Dados de autenticação inconsistentes.')
    return int(actor_user_id)


def is_bcrypt_hash(value):
    raw = str(value or '')
    return raw.startswith('$2a$') or raw.startswith('$2b$') or raw.startswith('$2y$')


def hash_password(password):
    raw = validate_password_strength(password)
    if not BCRYPT_AVAILABLE:
        return raw
    return bcrypt.hashpw(raw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(stored_password, provided_password):
    stored = str(stored_password or '')
    provided = str(provided_password or '')
    if is_bcrypt_hash(stored):
        if not BCRYPT_AVAILABLE:
            return False
        return bcrypt.checkpw(provided.encode('utf-8'), stored.encode('utf-8'))
    return stored == provided
