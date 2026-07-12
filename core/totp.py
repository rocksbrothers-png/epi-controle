"""TOTP (RFC 6238) em stdlib puro — autenticação em duas etapas.

Sem dependências externas: HMAC-SHA1 + base32, códigos de 6 dígitos com
janela de 30 segundos, compatível com Google Authenticator/Authy/1Password
via URI otpauth://.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

TOTP_PERIOD_SECONDS = 30
TOTP_DIGITS = 6


def generate_totp_secret() -> str:
    """Segredo base32 de 160 bits (padrão dos autenticadores)."""
    return base64.b32encode(secrets.token_bytes(20)).decode('ascii')


def _hotp(secret_base32: str, counter: int) -> str:
    key = base64.b32decode(secret_base32.upper() + '=' * (-len(secret_base32) % 8))
    digest = hmac.new(key, struct.pack('>Q', counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(code % (10 ** TOTP_DIGITS)).zfill(TOTP_DIGITS)


def totp_code(secret_base32: str, timestamp: float | None = None) -> str:
    now = time.time() if timestamp is None else timestamp
    return _hotp(secret_base32, int(now // TOTP_PERIOD_SECONDS))


def verify_totp(secret_base32: str, code: str, window: int = 1, timestamp: float | None = None) -> bool:
    """Valida o código aceitando ±window períodos (tolerância de relógio)."""
    provided = str(code or '').strip().replace(' ', '')
    if not provided or not provided.isdigit() or len(provided) != TOTP_DIGITS:
        return False
    if not secret_base32:
        return False
    now = time.time() if timestamp is None else timestamp
    counter = int(now // TOTP_PERIOD_SECONDS)
    for offset in range(-window, window + 1):
        try:
            candidate = _hotp(secret_base32, counter + offset)
        except Exception:
            return False
        if hmac.compare_digest(candidate, provided):
            return True
    return False


def otpauth_uri(secret_base32: str, account: str, issuer: str = 'EPI Controle') -> str:
    """URI otpauth:// para importação no app autenticador (QR ou manual)."""
    label = f'{quote(issuer)}:{quote(str(account or ""))}'
    return (
        f'otpauth://totp/{label}?secret={secret_base32}'
        f'&issuer={quote(issuer)}&algorithm=SHA1&digits={TOTP_DIGITS}&period={TOTP_PERIOD_SECONDS}'
    )
