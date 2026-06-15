"""Rotas de gestão de empresas, fornecedores e vínculos."""

import re
from contextlib import closing
from datetime import datetime, timezone

from core.auth import ensure_resource_company
from core.database import get_connection
from core.permissions import PERM_SUPPLIERS_MANAGE, PERM_UNIT_LINKS_MANAGE
from core.repository import authorize_action, require_master_actor
from core.security import resolve_actor_user_id
from epi_backend.db import row_to_dict
from epi_backend.http_utils import require_fields, send_json, structured_log
from modules.commercial.service import save_platform_brand
from modules.companies.service import (
    company_billable_user_counts,
    create_company,
    evaluate_company_block_status,
    fetch_companies,
    get_company_by_id,
    get_company_full,
    register_company_audit,
    summarize_company_changes,
    suspend_company,
    toggle_authorized_supplier,
    update_company,
    upsert_authorized_supplier,
    upsert_authorized_supplier_upload_row,
    validate_company_payload,
)

UTC = timezone.utc


# ── GET /api/companies ────────────────────────────────────────────────────────

def handle_get_companies(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'companies:view')
        scope = None if actor['role'] == 'master_admin' else actor['company_id']
        return send_json(handler, 200, {'companies': fetch_companies(connection, scope)})


def handle_get_company(handler, parsed, payload, match):
    company_id = int(match.group(1))
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'companies:view')
        if actor['role'] != 'master_admin' and int(actor['company_id']) != company_id:
            raise PermissionError('Acesso permitido apenas para a própria empresa.')
        company = get_company_full(connection, company_id)
        if not company:
            return send_json(handler, 404, {'error': 'Empresa não encontrada.'})
        counts = company_billable_user_counts(connection, company_id)
        company['user_count'] = int(counts.get(company_id, 0))
        return send_json(handler, 200, {'company': company})


# ── POST /api/companies ───────────────────────────────────────────────────────

def handle_post_companies(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'name', 'legal_name', 'cnpj', 'plan_name', 'user_limit', 'license_status', 'active'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'companies:create')
        validated_payload = validate_company_payload(connection, payload, None)
        company_id = create_company(connection, validated_payload)
        summary, details = summarize_company_changes({}, validated_payload)
        register_company_audit(connection, company_id, actor, 'create', summary, details)
        connection.commit()
        return send_json(handler, 201, {'ok': True, 'id': company_id})


# ── POST /api/companies/{id}/block-status ─────────────────────────────────────

def handle_post_company_block_status(handler, parsed, payload, match):
    company_id = int(match.group(1))
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'companies:license')
        company = get_company_by_id(connection, company_id)
        if not company:
            raise ValueError('Empresa não encontrada.')
        mark_payment_overdue = str(payload.get('mark_payment_overdue', '')).lower() in ('1', 'true', 'yes', 'on')
        if mark_payment_overdue and company.get('license_status') != 'suspended':
            suspend_company(connection, company_id)
            register_company_audit(
                connection,
                company_id,
                actor,
                'suspend',
                'Licença suspensa automaticamente por atraso de pagamento.',
                [{
                    'field': 'Status da licença',
                    'before': str(company.get('license_status') or 'active'),
                    'after': 'suspended'
                }]
            )
            connection.commit()
        status = evaluate_company_block_status(connection, company_id, persist_expiration=True)
        return send_json(handler, 200, status)


# ── POST /api/platform-brand ──────────────────────────────────────────────────

def handle_post_platform_brand(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor = require_master_actor(connection, resolve_actor_user_id(handler, parsed, payload))
        brand = save_platform_brand(connection, payload)
        connection.commit()
        structured_log('info', 'platform_brand.updated', actor_user_id=actor['id'])
        return send_json(handler, 200, {'ok': True, 'brand': brand})


# ── PUT /api/companies/{id} ───────────────────────────────────────────────────

def handle_put_company(handler, parsed, payload, match):
    company_id = int(match.group(1))
    require_fields(payload, ['actor_user_id', 'name', 'legal_name', 'cnpj', 'plan_name', 'user_limit', 'license_status', 'active'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'companies:update')
        previous = get_company_full(connection, company_id)
        if not previous:
            raise ValueError('Empresa não encontrada.')
        validated_payload = validate_company_payload(connection, payload, company_id)
        update_company(connection, company_id, validated_payload)
        action_type = 'update'
        if previous.get('license_status') != 'suspended' and validated_payload.get('license_status') == 'suspended':
            action_type = 'suspend'
        elif (
            (previous.get('license_status') in ('suspended', 'expired') or int(previous.get('active', 1)) == 0)
            and validated_payload.get('license_status') == 'active'
            and int(validated_payload.get('active', 1)) == 1
        ):
            action_type = 'reactivate'
        summary, details = summarize_company_changes(previous, validated_payload)
        register_company_audit(connection, company_id, actor, action_type, summary, details)
        connection.commit()
        return send_json(handler, 200, {'ok': True})


# ── POST /api/authorized-suppliers ───────────────────────────────────────────

def handle_post_authorized_suppliers(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'name'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_SUPPLIERS_MANAGE)
        company_id = int(actor['company_id'])
        now = datetime.now(UTC).isoformat()
        name = str(payload['name']).strip()
        cnpj = ''.join(ch for ch in str(payload.get('cnpj') or '') if ch.isdigit())
        category = str(payload.get('category') or '').strip()
        contact_email = str(payload.get('contact_email') or '').strip().lower()
        notes = str(payload.get('notes') or '').strip()
        sup_id = upsert_authorized_supplier(connection, company_id, int(actor['id']), name, cnpj, category, contact_email, notes, now)
        connection.commit()
        return send_json(handler, 201, {'ok': True, 'id': sup_id})


# ── POST /api/authorized-suppliers/upload ────────────────────────────────────

def handle_post_authorized_suppliers_upload(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'rows'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_SUPPLIERS_MANAGE)
        company_id = int(actor['company_id'])
        rows = payload.get('rows') or []
        if not rows:
            raise ValueError('Nenhum item para importar.')
        now = datetime.now(UTC).isoformat()
        inserted, updated = 0, 0
        for row in rows:
            name = str(row.get('name') or row.get('Nome') or row.get('nome') or '').strip()
            if not name:
                continue
            cnpj = ''.join(ch for ch in str(row.get('cnpj') or row.get('CNPJ') or '') if ch.isdigit())
            category = str(row.get('category') or row.get('categoria') or row.get('Categoria') or '').strip()
            contact_email = str(row.get('email') or row.get('Email') or '').strip().lower()
            notes = str(row.get('notes') or row.get('obs') or row.get('Obs') or '').strip()
            was_inserted = upsert_authorized_supplier_upload_row(
                connection, company_id, int(actor['id']), name, cnpj, category, contact_email, notes, now
            )
            if was_inserted:
                inserted += 1
            else:
                updated += 1
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'inserted': inserted, 'updated': updated, 'total': inserted + updated})


# ── POST /api/authorized-suppliers/{id}/toggle ───────────────────────────────

def handle_post_authorized_supplier_toggle(handler, parsed, payload, match):
    supplier_id = int(match.group(1))
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_SUPPLIERS_MANAGE)
        company_id = int(actor['company_id'])
        now = datetime.now(UTC).isoformat()
        supplier, new_active = toggle_authorized_supplier(connection, supplier_id, company_id, now)
        if supplier is None:
            return send_json(handler, 404, {'error': 'Fornecedor não encontrado.'})
        connection.commit()
        action_label = 'reativado' if new_active == 1 else 'suspenso'
        return send_json(handler, 200, {'ok': True, 'active': new_active, 'message': f'Fornecedor {action_label} com sucesso.'})


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    # GET
    router.register('GET', '/api/companies',                                       handle_get_companies)
    router.register('GET', r'^/api/companies/(\d+)$',                             handle_get_company, regex=True)
    # POST
    router.register('POST', '/api/companies',                                      handle_post_companies)
    router.register('POST', r'^/api/companies/(\d+)/block-status$',               handle_post_company_block_status, regex=True)
    router.register('POST', '/api/platform-brand',                                 handle_post_platform_brand)
    router.register('POST', '/api/authorized-suppliers',                           handle_post_authorized_suppliers)
    router.register('POST', '/api/authorized-suppliers/upload',                    handle_post_authorized_suppliers_upload)
    router.register('POST', r'^/api/authorized-suppliers/(\d+)/toggle$',          handle_post_authorized_supplier_toggle, regex=True)
    # PUT
    router.register('PUT',  r'^/api/companies/(\d+)$',                            handle_put_company, regex=True)
