"""Rotas de contratos e configurações comerciais."""

from contextlib import closing

from core.database import get_connection
from core.permissions import PERM_COMMERCIAL_VIEW, PERM_COMPANIES_VIEW
from core.repository import authorize_action, require_master_actor
from core.security import resolve_actor_user_id
from epi_backend.http_utils import require_fields, send_bytes, send_json
from modules.commercial.service import (
    build_commercial_contract_pdf,
    generate_commercial_contract_pdf,
    get_or_create_commercial_contract,
    save_commercial_contract,
    save_commercial_settings as _save_commercial_settings_impl,
    send_commercial_contract_email,
    sign_commercial_contract,
    upload_signed_contract_file,
)

import base64
from urllib.parse import parse_qs

from epi_backend.http_utils import structured_log as _structured_log


# ── GET ───────────────────────────────────────────────────────────────────────

def handle_get_commercial_contract(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_COMPANIES_VIEW)
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_COMMERCIAL_VIEW)
        query = parse_qs(parsed.query)
        company_id = int(query.get('company_id', ['0'])[0] or 0)
        if not company_id:
            raise ValueError('company_id é obrigatório.')
        contract = get_or_create_commercial_contract(connection, actor, company_id)
        connection.commit()
        return send_json(handler, 200, {'contract': contract})


def handle_get_commercial_contract_pdf(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_COMPANIES_VIEW)
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_COMMERCIAL_VIEW)
        query = parse_qs(parsed.query)
        company_id = int(query.get('company_id', ['0'])[0] or 0)
        if not company_id:
            raise ValueError('company_id é obrigatório.')
        contract = get_or_create_commercial_contract(connection, actor, company_id)
        base64_payload = contract.get('signed_pdf_base64') or contract.get('generated_pdf_base64')
        pdf_bytes = (
            base64.b64decode(str(base64_payload).encode('ascii'))
            if base64_payload
            else build_commercial_contract_pdf(connection, actor, company_id)
        )
        return send_bytes(handler, 200, 'application/pdf', pdf_bytes)


def handle_get_commercial_contract_file(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_COMMERCIAL_VIEW)
        query = parse_qs(parsed.query)
        company_id = int(query.get('company_id', ['0'])[0] or 0)
        if not company_id:
            raise ValueError('company_id é obrigatório.')
        file_kind = str(query.get('kind', ['generated'])[0] or 'generated').strip().lower()
        contract = get_or_create_commercial_contract(connection, actor, company_id)
        base64_payload = (
            contract.get('signed_pdf_base64')
            if file_kind == 'signed'
            else contract.get('generated_pdf_base64')
        )
        if not base64_payload:
            raise ValueError('Arquivo não disponível para este contrato.')
        binary = base64.b64decode(str(base64_payload).encode('ascii'))
        filename = (
            contract.get('signed_file_name')
            if file_kind == 'signed'
            else f"contrato-{company_id}-gerado.pdf"
        )
        content_type = (
            contract.get('signed_file_mime')
            if file_kind == 'signed'
            else 'application/pdf'
        )
        return send_bytes(handler, 200, content_type or 'application/pdf', binary, filename or 'contrato.pdf')


# ── POST ──────────────────────────────────────────────────────────────────────

def handle_post_commercial_contract_save(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        require_fields(payload, ['actor_user_id', 'company_id'])
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_COMMERCIAL_VIEW)
        contract = save_commercial_contract(connection, actor, payload)
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'contract': contract})


def handle_post_commercial_contract_generate(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        require_fields(payload, ['actor_user_id', 'company_id'])
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_COMMERCIAL_VIEW)
        save_commercial_contract(connection, actor, payload)
        contract = generate_commercial_contract_pdf(connection, actor, int(payload.get('company_id')))
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'contract': contract})


def handle_post_commercial_contract_sign(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        require_fields(payload, ['actor_user_id', 'company_id', 'signature_name', 'signature_data'])
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_COMMERCIAL_VIEW)
        contract = sign_commercial_contract(connection, actor, payload)
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'contract': contract})


def handle_post_commercial_contract_upload_signed(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        require_fields(payload, ['actor_user_id', 'company_id', 'file_name', 'file_base64'])
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_COMMERCIAL_VIEW)
        contract = upload_signed_contract_file(connection, actor, payload)
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'contract': contract})


def handle_post_commercial_contract_send_email(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        require_fields(payload, ['actor_user_id', 'company_id', 'email_to'])
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_COMMERCIAL_VIEW)
        contract = send_commercial_contract_email(connection, actor, payload)
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'contract': contract})


# ── POST /api/commercial-settings ─────────────────────────────────────────────

def handle_post_commercial_settings(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'unit_price', 'plans'])
    with closing(get_connection()) as connection:
        actor_user_id = resolve_actor_user_id(handler, parsed, payload)
        actor, settings, details = _save_commercial_settings_impl(connection, payload, require_master_actor_fn=require_master_actor)
        if actor['role'] != 'master_admin' or int(actor['id']) != int(actor_user_id):
            raise PermissionError('Apenas o Administrador Master pode alterar parâmetros comerciais.')
        connection.commit()
        _structured_log(
            'info',
            'commercial_settings.updated',
            actor_user_id=actor['id'],
            details=details
        )
        return send_json(handler, 200, {'ok': True, 'commercial_settings': settings})


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    # GET
    router.register('GET', '/api/commercial-contract',              handle_get_commercial_contract)
    router.register('GET', '/api/commercial-contract.pdf',          handle_get_commercial_contract_pdf)
    router.register('GET', '/api/commercial-contract/file',         handle_get_commercial_contract_file)
    # POST
    router.register('POST', '/api/commercial-contract/save',        handle_post_commercial_contract_save)
    router.register('POST', '/api/commercial-contract/generate',    handle_post_commercial_contract_generate)
    router.register('POST', '/api/commercial-contract/sign',        handle_post_commercial_contract_sign)
    router.register('POST', '/api/commercial-contract/upload-signed', handle_post_commercial_contract_upload_signed)
    router.register('POST', '/api/commercial-contract/send-email',  handle_post_commercial_contract_send_email)
    router.register('POST', '/api/commercial-settings',             handle_post_commercial_settings)
