"""Rotas de gestão de EPIs."""

import re
from contextlib import closing

from core.auth import ensure_resource_company, require_structural_admin
from core.database import get_connection
from core.repository import authorize_action, get_epi_by_id
from core.security import resolve_actor_user_id
from epi_backend.http_utils import require_fields, send_json
from modules.epis.service import create_epi as create_epi_service, update_epi as update_epi_service


def _get_server():
    import server_postgres as _sp
    return _sp


# ── POST ──────────────────────────────────────────────────────────────────────

def handle_post_epis(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'company_id', 'name', 'purchase_code', 'ca', 'sector', 'epi_section', 'model_reference', 'manufacturer', 'supplier_company', 'unit_measure', 'ca_expiry', 'epi_validity_date', 'manufacturer_validity_months'])
    sp = _get_server()
    with closing(get_connection()) as connection:
        epi_id = create_epi_service(
            connection,
            payload,
            authorize_action=authorize_action,
            resolve_actor_user_id=lambda: resolve_actor_user_id(handler, parsed, payload),
            require_structural_admin=require_structural_admin,
            next_company_qr_sequence=sp.next_company_qr_sequence,
            build_master_epi_qr=sp.build_master_epi_qr,
            parse_epi_joinventures=sp.parse_epi_joinventures,
            normalize_active_joinventure_name=sp.normalize_active_joinventure_name,
            resolve_epi_scope_unit=sp.resolve_epi_scope_unit,
            resolve_epi_scope_metadata=sp.resolve_epi_scope_metadata,
            validate_epi_uniqueness=sp.validate_epi_uniqueness,
            parse_int_flexible=sp.parse_int_flexible,
            upsert_unit_stock=sp.upsert_unit_stock,
        )
        return send_json(handler, 201, {'ok': True, 'id': epi_id})


# ── PUT ───────────────────────────────────────────────────────────────────────

def handle_put_epi(handler, parsed, payload, match):
    epi_id = int(match.group(1))
    require_fields(payload, ['actor_user_id', 'company_id', 'name', 'purchase_code', 'ca', 'sector', 'epi_section', 'model_reference', 'manufacturer', 'supplier_company', 'unit_measure', 'ca_expiry', 'epi_validity_date', 'manufacturer_validity_months'])
    sp = _get_server()
    with closing(get_connection()) as connection:
        update_epi_service(
            connection,
            epi_id,
            payload,
            authorize_action=authorize_action,
            resolve_actor_user_id=lambda: resolve_actor_user_id(handler, parsed, payload),
            require_structural_admin=require_structural_admin,
            get_epi_by_id=get_epi_by_id,
            ensure_resource_company=ensure_resource_company,
            generate_epi_qr_code=sp.generate_epi_qr_code,
            parse_epi_joinventures=sp.parse_epi_joinventures,
            normalize_active_joinventure_name=sp.normalize_active_joinventure_name,
            resolve_epi_scope_unit=sp.resolve_epi_scope_unit,
            resolve_epi_scope_metadata=sp.resolve_epi_scope_metadata,
            validate_epi_uniqueness=sp.validate_epi_uniqueness,
            parse_int_flexible=sp.parse_int_flexible,
            sync_epi_scope_stock_unit=sp.sync_epi_scope_stock_unit,
        )
        return send_json(handler, 200, {'ok': True})


# ── DELETE ────────────────────────────────────────────────────────────────────

def handle_delete_epi(handler, parsed, payload, match):
    epi_id = int(match.group(1))
    sp = _get_server()
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'epis:delete')
        require_structural_admin(actor)
        epi = get_epi_by_id(connection, epi_id)
        if not epi:
            raise ValueError('EPI não encontrado.')
        ensure_resource_company(actor, epi, 'EPI')
        sp.delete_epi_dependencies(connection, epi_id)
        connection.commit()
        return send_json(handler, 200, {'ok': True})


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    router.register('POST',   '/api/epis',          handle_post_epis)
    router.register('PUT',    r'/api/epis/(\d+)',   handle_put_epi,    regex=True)
    router.register('DELETE', r'/api/epis/(\d+)',   handle_delete_epi, regex=True)
