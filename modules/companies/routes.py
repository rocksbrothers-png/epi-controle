"""Rotas de gestão de empresas, fornecedores e vínculos."""

import re
from contextlib import closing
from datetime import datetime, timezone

from core.auth import ensure_resource_company
from core.database import get_connection
from core.permissions import PERM_SUPPLIERS_MANAGE, PERM_UNIT_LINKS_MANAGE
from core.repository import authorize_action
from core.security import resolve_actor_user_id
from epi_backend.db import row_to_dict
from epi_backend.http_utils import require_fields, send_json, structured_log

UTC = timezone.utc


def _get_server():
    import server_postgres as _sp
    return _sp


# ── POST /api/companies ───────────────────────────────────────────────────────

def handle_post_companies(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'name', 'legal_name', 'cnpj', 'plan_name', 'user_limit', 'license_status', 'active'])
    sp = _get_server()
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'companies:create')
        validated_payload = sp.validate_company_payload(connection, payload, None)
        cursor = connection.execute(
            (
                'INSERT INTO companies ('
                'name, legal_name, cnpj, logo_type, plan_name, user_limit, license_status, active, '
                'commercial_notes, contract_start, contract_end, monthly_value, addendum_enabled'
                ') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
            ),
            (
                validated_payload['name'], validated_payload['legal_name'], validated_payload['cnpj'],
                validated_payload.get('logo_type', ''),
                validated_payload['plan_name'], validated_payload['user_limit'],
                validated_payload['license_status'], int(validated_payload['active']),
                validated_payload.get('commercial_notes', ''), validated_payload.get('contract_start', ''),
                validated_payload.get('contract_end', ''),
                validated_payload.get('monthly_value', 0), validated_payload.get('addendum_enabled', 0)
            )
        )
        summary, details = sp.summarize_company_changes({}, validated_payload)
        sp.register_company_audit(connection, int(cursor.lastrowid), actor, 'create', summary, details)
        connection.commit()
        return send_json(handler, 201, {'ok': True, 'id': cursor.lastrowid})


# ── POST /api/companies/{id}/block-status ─────────────────────────────────────

def handle_post_company_block_status(handler, parsed, payload, match):
    company_id = int(match.group(1))
    sp = _get_server()
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'companies:license')
        company = sp.get_company_by_id(connection, company_id)
        if not company:
            raise ValueError('Empresa não encontrada.')
        mark_payment_overdue = str(payload.get('mark_payment_overdue', '')).lower() in ('1', 'true', 'yes', 'on')
        if mark_payment_overdue and company.get('license_status') != 'suspended':
            connection.execute(
                "UPDATE companies SET license_status = 'suspended' WHERE id = ?",
                (company_id,)
            )
            sp.register_company_audit(
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
        status = sp.evaluate_company_block_status(connection, company_id, persist_expiration=True)
        return send_json(handler, 200, status)


# ── POST /api/platform-brand ──────────────────────────────────────────────────

def handle_post_platform_brand(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    sp = _get_server()
    with closing(get_connection()) as connection:
        actor = sp.require_master_actor(connection, resolve_actor_user_id(handler, parsed, payload))
        brand = sp.save_platform_brand(connection, payload)
        connection.commit()
        structured_log('info', 'platform_brand.updated', actor_user_id=actor['id'])
        return send_json(handler, 200, {'ok': True, 'brand': brand})


# ── PUT /api/companies/{id} ───────────────────────────────────────────────────

def handle_put_company(handler, parsed, payload, match):
    company_id = int(match.group(1))
    require_fields(payload, ['actor_user_id', 'name', 'legal_name', 'cnpj', 'plan_name', 'user_limit', 'license_status', 'active'])
    sp = _get_server()
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'companies:update')
        current = connection.execute('SELECT * FROM companies WHERE id = ?', (company_id,)).fetchone()
        if not current:
            raise ValueError('Empresa não encontrada.')
        previous = row_to_dict(current)
        validated_payload = sp.validate_company_payload(connection, payload, company_id)
        connection.execute(
            sp.SQL_UPDATE_COMPANY,
            (
                validated_payload['name'], validated_payload['legal_name'], validated_payload['cnpj'],
                validated_payload.get('logo_type', ''),
                validated_payload['plan_name'], validated_payload['user_limit'],
                validated_payload['license_status'], int(validated_payload['active']),
                validated_payload.get('commercial_notes', ''), validated_payload.get('contract_start', ''),
                validated_payload.get('contract_end', ''),
                validated_payload.get('monthly_value', 0), validated_payload.get('addendum_enabled', 0),
                company_id
            )
        )
        action_type = 'update'
        if previous.get('license_status') != 'suspended' and validated_payload.get('license_status') == 'suspended':
            action_type = 'suspend'
        elif (
            (previous.get('license_status') in ('suspended', 'expired') or int(previous.get('active', 1)) == 0)
            and validated_payload.get('license_status') == 'active'
            and int(validated_payload.get('active', 1)) == 1
        ):
            action_type = 'reactivate'
        summary, details = sp.summarize_company_changes(previous, validated_payload)
        sp.register_company_audit(connection, company_id, actor, action_type, summary, details)
        connection.commit()
        return send_json(handler, 200, {'ok': True})


# ── POST /api/user-unit-links ─────────────────────────────────────────────────

def handle_post_user_unit_links(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'target_user_id', 'unit_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_UNIT_LINKS_MANAGE)
        company_id = int(actor['company_id'])
        target_user_id = int(payload['target_user_id'])
        unit_id = int(payload['unit_id'])
        target = connection.execute('SELECT id, role, company_id FROM users WHERE id = ?', (target_user_id,)).fetchone()
        if not target:
            raise ValueError('Usuário não encontrado.')
        if int(target['company_id']) != company_id:
            raise PermissionError('Usuário pertence a outra empresa.')
        if str(target['role']) not in ('buyer', 'approver'):
            raise ValueError('Vínculos de unidade só se aplicam a compradores e aprovadores.')
        unit = connection.execute('SELECT id FROM units WHERE id = ? AND company_id = ?', (unit_id, company_id)).fetchone()
        if not unit:
            raise ValueError('Unidade não encontrada ou pertence a outra empresa.')
        now = datetime.now(UTC).isoformat()
        try:
            cur = connection.execute(
                'INSERT INTO user_unit_links (company_id, user_id, unit_id, created_by_user_id, created_at) VALUES (?, ?, ?, ?, ?)',
                (company_id, target_user_id, unit_id, int(actor['id']), now)
            )
            link_id = int(cur.lastrowid)
            connection.commit()
        except Exception:
            raise ValueError('Este vínculo já existe.')
        return send_json(handler, 201, {'ok': True, 'id': link_id})


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
        existing = connection.execute('SELECT id FROM authorized_suppliers WHERE company_id = ? AND LOWER(TRIM(name)) = ?', (company_id, name.lower())).fetchone()
        if existing:
            connection.execute('UPDATE authorized_suppliers SET cnpj = ?, category = ?, contact_email = ?, notes = ?, active = 1, updated_at = ? WHERE id = ?', (cnpj, category, contact_email, notes, now, int(existing['id'])))
            sup_id = int(existing['id'])
        else:
            cur = connection.execute('INSERT INTO authorized_suppliers (company_id, name, cnpj, category, contact_email, notes, active, source, created_by_user_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)', (company_id, name, cnpj, category, contact_email, notes, 'manual', int(actor['id']), now, now))
            sup_id = int(cur.lastrowid)
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
            existing = connection.execute("SELECT id FROM authorized_suppliers WHERE company_id = ? AND (LOWER(TRIM(name)) = ? OR (cnpj != '' AND cnpj = ?))", (company_id, name.lower(), cnpj)).fetchone()
            if existing:
                connection.execute('UPDATE authorized_suppliers SET name = ?, cnpj = ?, category = ?, contact_email = ?, notes = ?, active = 1, source = ?, updated_at = ? WHERE id = ?', (name, cnpj, category, contact_email, notes, 'upload', now, int(existing['id'])))
                updated += 1
            else:
                connection.execute('INSERT INTO authorized_suppliers (company_id, name, cnpj, category, contact_email, notes, active, source, created_by_user_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)', (company_id, name, cnpj, category, contact_email, notes, 'upload', int(actor['id']), now, now))
                inserted += 1
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
        supplier = connection.execute('SELECT * FROM authorized_suppliers WHERE id = ? AND company_id = ?', (supplier_id, company_id)).fetchone()
        if not supplier:
            return send_json(handler, 404, {'error': 'Fornecedor não encontrado.'})
        new_active = 0 if int(supplier['active']) == 1 else 1
        connection.execute('UPDATE authorized_suppliers SET active = ?, updated_at = ? WHERE id = ?', (new_active, now, supplier_id))
        connection.commit()
        action_label = 'reativado' if new_active == 1 else 'suspenso'
        return send_json(handler, 200, {'ok': True, 'active': new_active, 'message': f'Fornecedor {action_label} com sucesso.'})


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    # POST
    router.register('POST', '/api/companies',                                      handle_post_companies)
    router.register('POST', r'^/api/companies/(\d+)/block-status$',               handle_post_company_block_status, regex=True)
    router.register('POST', '/api/platform-brand',                                 handle_post_platform_brand)
    router.register('POST', '/api/user-unit-links',                                handle_post_user_unit_links)
    router.register('POST', '/api/authorized-suppliers',                           handle_post_authorized_suppliers)
    router.register('POST', '/api/authorized-suppliers/upload',                    handle_post_authorized_suppliers_upload)
    router.register('POST', r'^/api/authorized-suppliers/(\d+)/toggle$',          handle_post_authorized_supplier_toggle, regex=True)
    # PUT
    router.register('PUT',  r'^/api/companies/(\d+)$',                            handle_put_company, regex=True)
