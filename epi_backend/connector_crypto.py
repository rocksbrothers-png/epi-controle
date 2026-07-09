"""Cifra das credenciais de conectores (supplier_integrations.config_encrypted).

Fernet (AES-128-CBC + HMAC, biblioteca `cryptography`) com chave derivada por
tenant: SHA-256(segredo-base || company_id) — vazamento de um registro não
expõe outros tenants. O segredo-base vem de CONNECTOR_SECRET_KEY (ou, em
fallback, do JWT_SECRET já obrigatório em produção). Config em claro nunca é
persistida nem logada.
"""

import base64
import hashlib
import json
import os


def _base_secret():
    secret = os.environ.get('CONNECTOR_SECRET_KEY', '').strip()
    if not secret:
        from epi_backend.config import JWT_SECRET
        secret = JWT_SECRET
    return secret


def _fernet(company_id):
    from cryptography.fernet import Fernet
    digest = hashlib.sha256(
        f'{_base_secret()}::connector::{int(company_id)}'.encode('utf-8')
    ).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_connector_config(company_id, config):
    """Serializa e cifra o dict de config. Retorna token Fernet (str)."""
    payload = json.dumps(dict(config or {}), ensure_ascii=False).encode('utf-8')
    return _fernet(company_id).encrypt(payload).decode('ascii')


def decrypt_connector_config(company_id, token):
    """Decifra o token de config. Levanta ValueError para token inválido."""
    if not str(token or '').strip():
        return {}
    from cryptography.fernet import InvalidToken
    try:
        payload = _fernet(company_id).decrypt(str(token).encode('ascii'))
    except InvalidToken as exc:
        raise ValueError('Configuração da integração inválida ou de outro ambiente.') from exc
    return json.loads(payload.decode('utf-8'))
