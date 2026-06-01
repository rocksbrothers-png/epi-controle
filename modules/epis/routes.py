"""Rotas de gestão de EPIs."""

import re
from contextlib import closing
from urllib.parse import parse_qs

from core.auth import ensure_resource_company, require_structural_admin
from core.database import get_connection
from core.repository import authorize_action, get_epi_by_id
from core.security import resolve_actor_user_id
from epi_backend.http_utils import require_fields, send_json
from modules.epis.service import (
    create_epi as create_epi_service,
    get_epi_replacement_days,
    normalize_active_joinventure_name,
    parse_epi_joinventures,
    resolve_epi_scope_metadata,
    resolve_epi_scope_unit,
    update_epi as update_epi_service,
    validate_epi_uniqueness,
)
from modules.stock.service import (
    build_master_epi_qr,
    generate_epi_qr_code,
    next_company_qr_sequence,
    parse_int_flexible,
    sync_epi_scope_stock_unit,
    upsert_unit_stock,
)
from modules.units.service import delete_epi_dependencies


# ── GET ───────────────────────────────────────────────────────────────────────

def handle_get_epi_replacement_days(handler, parsed, payload, match):
    epi_id = int(match.group(1))
    with closing(get_connection()) as connection:
        row = get_epi_replacement_days(connection, epi_id)
        if not row:
            return send_json(handler, 200, {'days': None})
        days = row['default_replacement_days']
        months = row['manufacturer_validity_months']
        source = None
        if days and int(days) > 0:
            source = 'epi_rule'
        elif months:
            try:
                days = int(float(str(months))) * 30
                source = 'manufacturer_validity'
            except Exception:
                days = None
        return send_json(handler, 200, {'days': days, 'source': source})


# ── POST ──────────────────────────────────────────────────────────────────────

def handle_post_epis(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'company_id', 'name', 'purchase_code', 'ca', 'sector', 'epi_section', 'model_reference', 'manufacturer', 'supplier_company', 'unit_measure', 'ca_expiry', 'epi_validity_date', 'manufacturer_validity_months'])
    with closing(get_connection()) as connection:
        epi_id = create_epi_service(
            connection,
            payload,
            authorize_action=authorize_action,
            resolve_actor_user_id=lambda: resolve_actor_user_id(handler, parsed, payload),
            require_structural_admin=require_structural_admin,
            next_company_qr_sequence=next_company_qr_sequence,
            build_master_epi_qr=build_master_epi_qr,
            parse_epi_joinventures=parse_epi_joinventures,
            normalize_active_joinventure_name=normalize_active_joinventure_name,
            resolve_epi_scope_unit=resolve_epi_scope_unit,
            resolve_epi_scope_metadata=resolve_epi_scope_metadata,
            validate_epi_uniqueness=validate_epi_uniqueness,
            parse_int_flexible=parse_int_flexible,
            upsert_unit_stock=upsert_unit_stock,
        )
        return send_json(handler, 201, {'ok': True, 'id': epi_id})


# ── PUT ───────────────────────────────────────────────────────────────────────

def handle_put_epi(handler, parsed, payload, match):
    epi_id = int(match.group(1))
    require_fields(payload, ['actor_user_id', 'company_id', 'name', 'purchase_code', 'ca', 'sector', 'epi_section', 'model_reference', 'manufacturer', 'supplier_company', 'unit_measure', 'ca_expiry', 'epi_validity_date', 'manufacturer_validity_months'])
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
            generate_epi_qr_code=generate_epi_qr_code,
            parse_epi_joinventures=parse_epi_joinventures,
            normalize_active_joinventure_name=normalize_active_joinventure_name,
            resolve_epi_scope_unit=resolve_epi_scope_unit,
            resolve_epi_scope_metadata=resolve_epi_scope_metadata,
            validate_epi_uniqueness=validate_epi_uniqueness,
            parse_int_flexible=parse_int_flexible,
            sync_epi_scope_stock_unit=sync_epi_scope_stock_unit,
        )
        return send_json(handler, 200, {'ok': True})


# ── DELETE ────────────────────────────────────────────────────────────────────

def handle_delete_epi(handler, parsed, payload, match):
    epi_id = int(match.group(1))
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'epis:delete')
        require_structural_admin(actor)
        epi = get_epi_by_id(connection, epi_id)
        if not epi:
            raise ValueError('EPI não encontrado.')
        ensure_resource_company(actor, epi, 'EPI')
        delete_epi_dependencies(connection, epi_id)
        connection.commit()
        return send_json(handler, 200, {'ok': True})


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    router.register('GET',    r'/api/epi-replacement-days/(\d+)', handle_get_epi_replacement_days, regex=True)
    router.register('POST',   '/api/epis',                        handle_post_epis)
    router.register('PUT',    r'/api/epis/(\d+)',                 handle_put_epi,    regex=True)
    router.register('DELETE', r'/api/epis/(\d+)',                 handle_delete_epi, regex=True)
