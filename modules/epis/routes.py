"""Rotas de gestão de EPIs."""

import re
from contextlib import closing
from urllib.parse import parse_qs

from core.auth import ensure_resource_company, require_structural_admin
from core.database import get_connection
from core.permissions import PERM_EPIS_VIEW
from core.repository import authorize_action, get_epi_by_id
from core.security import resolve_actor_user_id
from epi_backend.http_utils import require_fields, send_json
from modules.epis.service import (
    create_epi as create_epi_service,
    fetch_archived_epis,
    get_epi_by_id as get_epi_full,
    get_epi_lifecycle,
    get_epi_replacement_days,
    normalize_active_joinventure_name,
    parse_epi_joinventures,
    purge_epi_history,
    resolve_epi_scope_metadata,
    resolve_epi_scope_unit,
    summarize_epi_history,
    update_epi as update_epi_service,
    validate_epi_uniqueness,
)

from core import archival
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

def handle_get_epi(handler, parsed, payload, match):
    """Retorna um EPI completo (para prefill de edição no cliente)."""
    epi_id = int(match.group(1))
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_EPIS_VIEW)
        epi = get_epi_full(connection, epi_id)
        if not epi:
            return send_json(handler, 404, {'error': 'EPI não encontrado.'})
        ensure_resource_company(actor, epi, 'EPI')
        return send_json(handler, 200, {'epi': epi})


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

# ── Arquivamento (Soft Delete) — mesma política das Unidades ─────────────────

_EPI_ARCHIVAL = dict(entity_label='EPI', audit_prefix='epi')


def _client_ip(handler):
    return str(getattr(handler, 'client_address', ('',))[0] or '')


def _require_deletion_admin(actor):
    if actor.get('role') not in ('master_admin', 'general_admin'):
        raise PermissionError(
            'Apenas Administrador Geral ou Administrador Master podem gerenciar a exclusão definitiva.'
        )


def _load_epi_for_lifecycle(connection, handler, parsed, payload, match, permission):
    actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), permission)
    epi = get_epi_lifecycle(connection, int(match.group(1)))
    if not epi:
        raise ValueError('EPI não encontrado.')
    ensure_resource_company(actor, epi, 'EPI')
    return actor, epi


def handle_delete_epi(handler, parsed, payload, match):
    """Política de retenção: DELETE não remove — arquiva (soft delete)."""
    with closing(get_connection()) as connection:
        actor, epi = _load_epi_for_lifecycle(connection, handler, parsed, payload, match, 'epis:delete')
        require_structural_admin(actor)
        reason = str(parse_qs(parsed.query).get('reason', [''])[0] or '')
        result = archival.archive_record(
            connection, 'epis', epi, actor,
            record_label=epi['name'], reason=reason, ip=_client_ip(handler),
            **_EPI_ARCHIVAL,
        )
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'archived': True, **result})


def handle_post_epi_archive(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor, epi = _load_epi_for_lifecycle(connection, handler, parsed, payload, match, 'epis:delete')
        require_structural_admin(actor)
        result = archival.archive_record(
            connection, 'epis', epi, actor,
            record_label=epi['name'],
            reason=str((payload or {}).get('reason') or ''), ip=_client_ip(handler),
            **_EPI_ARCHIVAL,
        )
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'archived': True, **result})


def handle_post_epi_restore(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor, epi = _load_epi_for_lifecycle(connection, handler, parsed, payload, match, 'epis:update')
        require_structural_admin(actor)
        archival.restore_record(
            connection, 'epis', epi, actor,
            record_label=epi['name'], ip=_client_ip(handler), **_EPI_ARCHIVAL,
        )
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'status': 'active'})


def handle_get_archived_epis(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_EPIS_VIEW)
        return send_json(handler, 200, {'epis': fetch_archived_epis(connection, actor)})


def handle_get_epi_deletion_summary(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor, epi = _load_epi_for_lifecycle(connection, handler, parsed, payload, match, PERM_EPIS_VIEW)
        return send_json(handler, 200, {
            'epi': {
                'id': epi['id'],
                'name': epi['name'],
                'status': epi.get('status'),
                'archived_at': epi.get('archived_at'),
                'retention_until': epi.get('retention_until'),
                'legal_hold': int(epi.get('legal_hold') or 0),
            },
            'records': summarize_epi_history(connection, int(epi['id'])),
        })


def handle_post_epi_purge_request(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor, epi = _load_epi_for_lifecycle(connection, handler, parsed, payload, match, 'epis:delete')
        _require_deletion_admin(actor)
        summary = archival.request_purge(
            connection, 'epis', epi, actor,
            record_label=epi['name'],
            summary=summarize_epi_history(connection, int(epi['id'])),
            ip=_client_ip(handler), **_EPI_ARCHIVAL,
        )
        connection.commit()
        return send_json(handler, 200, {
            'ok': True,
            'status': 'pending_deletion',
            'records': summary,
            'next_step': 'Confirme a exclusão definitiva com justificativa e o nome exato do EPI.',
        })


def handle_post_epi_purge_cancel(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor, epi = _load_epi_for_lifecycle(connection, handler, parsed, payload, match, 'epis:delete')
        _require_deletion_admin(actor)
        archival.cancel_purge(
            connection, 'epis', epi, actor,
            record_label=epi['name'], ip=_client_ip(handler), **_EPI_ARCHIVAL,
        )
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'status': 'archived'})


def handle_post_epi_purge_confirm(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'justification', 'confirm_name'])
    with closing(get_connection()) as connection:
        actor, epi = _load_epi_for_lifecycle(connection, handler, parsed, payload, match, 'epis:delete')
        _require_deletion_admin(actor)
        summary = archival.confirm_purge(
            connection, 'epis', epi, actor,
            record_label=epi['name'],
            justification=payload.get('justification'),
            confirm_name=payload.get('confirm_name'),
            summary=summarize_epi_history(connection, int(epi['id'])),
            purge_history=purge_epi_history,
            ip=_client_ip(handler), **_EPI_ARCHIVAL,
        )
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'status': 'deleted', 'records_removed': summary})


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    router.register('GET',    r'/api/epi-replacement-days/(\d+)', handle_get_epi_replacement_days, regex=True)
    router.register('GET',    '/api/epis/archived',               handle_get_archived_epis)
    router.register('GET',    r'/api/epis/(\d+)$',                handle_get_epi,    regex=True)
    router.register('GET',    r'/api/epis/(\d+)/deletion-summary$', handle_get_epi_deletion_summary, regex=True)
    router.register('POST',   '/api/epis',                        handle_post_epis)
    router.register('POST',   r'/api/epis/(\d+)/archive$',        handle_post_epi_archive,       regex=True)
    router.register('POST',   r'/api/epis/(\d+)/restore$',        handle_post_epi_restore,       regex=True)
    router.register('POST',   r'/api/epis/(\d+)/purge-request$',  handle_post_epi_purge_request, regex=True)
    router.register('POST',   r'/api/epis/(\d+)/purge-cancel$',   handle_post_epi_purge_cancel,  regex=True)
    router.register('POST',   r'/api/epis/(\d+)/purge-confirm$',  handle_post_epi_purge_confirm, regex=True)
    router.register('PUT',    r'/api/epis/(\d+)',                 handle_put_epi,    regex=True)
    router.register('DELETE', r'/api/epis/(\d+)',                 handle_delete_epi, regex=True)
