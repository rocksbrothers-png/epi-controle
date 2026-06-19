"""Rotas de fichas de EPI."""

import time
from contextlib import closing
from datetime import datetime, timezone
from urllib.parse import parse_qs, quote

from core.auth import ensure_resource_company, require_configuration_admin
from core.database import get_connection
from core.permissions import PERM_SETTINGS_UPDATE, PERM_SETTINGS_VIEW
from core.repository import authorize_action, get_employee_by_id
from modules.employees.service import actor_operational_unit_id, ensure_actor_employee_scope
from core.security import resolve_actor_user_id
from epi_backend.db import row_to_dict
from epi_backend.http_utils import require_fields, request_base_url, send_json, structured_log
from modules.employees.service import normalize_preferred_contact_channel
from modules.ficha.service import (
    apply_snapshot_retention,
    build_ficha_epi_html,
    compute_ficha_period_signature_state,
    ensure_ficha_snapshot_for_period,
    fetch_closed_ficha_periods,
    fetch_ficha_archive_snapshots,
    fetch_ficha_epi_audit_logs,
    fetch_ficha_epi_snapshots_list,
    fetch_ficha_periods,
    get_ficha_archive_snapshot_by_id,
    get_ficha_period_employee,
    get_ficha_period_full,
    is_valid_ficha_period_state,
    register_ficha_epi_audit,
    resolve_ficha_period_effective_status,
    set_ficha_period_pending_signature,
    sync_deliveries_to_ficha_period,
)
from modules.portal.service import (
    EMPLOYEE_PORTAL_SECRET_KEY,
    build_portal_link_from_cpf,
    upsert_employee_portal_link,
)
from modules.settings.service import (
    canary_evaluate_visibility_dataset,
    get_ficha_retention_policy,
    save_ficha_config,
    save_ficha_retention_policy,
)

UTC = timezone.utc


# ── GET ───────────────────────────────────────────────────────────────────────

def handle_get_fichas(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(
            connection,
            resolve_actor_user_id(handler, parsed),
            'fichas:view'
        )
        clauses = []
        params = []
        if actor['role'] != 'master_admin':
            clauses.append('fp.company_id = ?')
            params.append(actor['company_id'])
        scope_unit_id = actor_operational_unit_id(connection, actor)
        if scope_unit_id:
            clauses.append('fp.unit_id = ?')
            params.append(int(scope_unit_id))
        employee_id = parse_qs(parsed.query).get('employee_id', [''])[0]
        if employee_id:
            clauses.append('fp.employee_id = ?')
            params.append(int(employee_id))
        periods = fetch_ficha_periods(connection, clauses, params)
        period_items = [resolve_ficha_period_effective_status(connection, row_to_dict(item)) for item in periods]
        period_items = [item for item in period_items if is_valid_ficha_period_state(item)]
        period_items = canary_evaluate_visibility_dataset(
            connection, actor, endpoint_name='/api/fichas', dataset_name='fichas', legacy_items=period_items
        )
        connection.commit()
        return send_json(handler, 200, {'items': period_items})


def handle_get_ficha_epi_snapshots(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'reports:view')
        query = parse_qs(parsed.query)
        clauses, params = [], []
        if actor.get('role') != 'master_admin':
            clauses.append('s.company_id = %s')
            params.append(int(actor['company_id']))
        scope_unit_id = actor_operational_unit_id(connection, actor)
        if scope_unit_id:
            clauses.append('s.unit_id = %s')
            params.append(int(scope_unit_id))
        if query.get('employee_id'):
            clauses.append('s.employee_id = %s')
            params.append(int(query['employee_id'][0]))
        items = fetch_ficha_epi_snapshots_list(connection, clauses, params)
        items = canary_evaluate_visibility_dataset(
            connection, actor, endpoint_name='/api/ficha-epi-snapshots', dataset_name='ficha_snapshots', legacy_items=items
        )
        return send_json(handler, 200, {'items': items})


def handle_get_ficha_epi_audit(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_SETTINGS_VIEW)
        query = parse_qs(parsed.query)
        filters = {
            'employee_id': str(query.get('employee_id', [''])[0] or '').strip(),
            'actor_user_id': str(query.get('actor_user_id', [''])[0] or '').strip(),
            'action': str(query.get('action', [''])[0] or '').strip(),
            'date_from': str(query.get('date_from', [''])[0] or '').strip(),
            'date_to': str(query.get('date_to', [''])[0] or '').strip(),
        }
        filters = {k: v for k, v in filters.items() if v}
        try:
            items = fetch_ficha_epi_audit_logs(connection, actor, filters)
        except Exception as error:
            structured_log(
                'warning',
                'ficha.audit.fetch_failed',
                actor_user_id=actor.get('id'),
                error=str(error),
            )
            return send_json(
                handler,
                503,
                {
                    'error': 'Histórico temporariamente indisponível. Tente novamente.',
                    'code': 'FICHA_AUDIT_UNAVAILABLE',
                },
            )
        items = canary_evaluate_visibility_dataset(
            connection, actor, endpoint_name='/api/ficha-epi-audit', dataset_name='ficha_audit', legacy_items=items
        )
        return send_json(handler, 200, {'items': items})


# ── PUT ───────────────────────────────────────────────────────────────────────

def handle_put_ficha_config(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_SETTINGS_UPDATE)
        save_ficha_config(connection, actor['company_id'], payload)
        return send_json(handler, 200, {'ok': True})


def handle_put_ficha_retention_policy(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_SETTINGS_UPDATE)
        require_configuration_admin(actor)
        policy = save_ficha_retention_policy(connection, actor.get('company_id'), payload)
        return send_json(handler, 200, policy)


def handle_put_ficha_archive_purge(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_SETTINGS_UPDATE)
        require_configuration_admin(actor)
        policy = get_ficha_retention_policy(connection, actor.get('company_id'))
        apply_snapshot_retention(
            connection,
            actor.get('company_id') if actor.get('role') != 'master_admin' else None,
            policy,
        )
        return send_json(handler, 200, {'ok': True, 'policy': policy})


# ── POST /api/fichas/finalize ─────────────────────────────────────────────────

def handle_post_fichas_finalize(handler, parsed, payload, match):
    finalize_started_at = time.perf_counter()
    finalize_payload_period_id = int(payload.get('ficha_period_id') or 0)
    structured_log('info', 'ficha.finalize.start', ficha_period_id=finalize_payload_period_id)
    require_fields(payload, ['actor_user_id', 'ficha_period_id'])
    structured_log('info', 'ficha.finalize.user_validation_done', ficha_period_id=finalize_payload_period_id, elapsed_ms=round((time.perf_counter() - finalize_started_at) * 1000, 2))
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'fichas:view')
        structured_log('info', 'ficha.finalize.authorization_done', ficha_period_id=finalize_payload_period_id, actor_user_id=int(actor.get('id') or 0), elapsed_ms=round((time.perf_counter() - finalize_started_at) * 1000, 2))
        ficha = get_ficha_period_full(connection, int(payload['ficha_period_id']))
        if not ficha:
            raise ValueError('Período de ficha não encontrado.')
        structured_log('info', 'ficha.finalize.period_loaded', ficha_period_id=int(ficha['id']), elapsed_ms=round((time.perf_counter() - finalize_started_at) * 1000, 2))
        ensure_resource_company(actor, ficha, 'Ficha de EPI')
        scope_unit_id = actor_operational_unit_id(connection, actor)
        if scope_unit_id and int(ficha['unit_id']) != int(scope_unit_id):
            raise PermissionError('Seu perfil só pode finalizar ficha da própria unidade operacional.')
        preview_only = bool(payload.get('preview_only'))
        totals_data = compute_ficha_period_signature_state(connection, int(ficha['id']))
        pending_items = int(totals_data.get('pending_items') or 0)
        closed_period_with_batch_signature = (
            str(ficha.get('status') or '').lower() == 'closed'
            and str(ficha.get('batch_signature_at') or '').strip()
            and (not preview_only)
            and pending_items == 0
        )
        total_items = int(totals_data.get('total_items') or 0)
        if total_items <= 0:
            period_start = str(ficha.get('period_start') or '').strip()
            period_end = str(ficha.get('period_end') or '').strip()
            if period_start and period_end:
                now_sync = datetime.now(UTC).isoformat()
                sync_deliveries_to_ficha_period(
                    connection, int(ficha['id']), int(ficha['company_id']),
                    int(ficha['employee_id']), period_start, period_end, now_sync,
                )
                totals_data = compute_ficha_period_signature_state(connection, int(ficha['id']))
                total_items = int(totals_data.get('total_items') or 0)
        if total_items <= 0:
            raise ValueError('Não é possível finalizar período sem itens de entrega.')
        employee = get_employee_by_id(connection, int(ficha['employee_id']))
        if not employee:
            raise ValueError('Colaborador da ficha não encontrado.')
        ensure_actor_employee_scope(connection, actor, employee)
        manager_email = ''
        linked_employee_id = actor.get('linked_employee_id')
        if linked_employee_id not in (None, '', 'null'):
            manager_employee = get_employee_by_id(connection, int(linked_employee_id))
            manager_email = str((manager_employee or {}).get('email') or '').strip().lower()
        channel = normalize_preferred_contact_channel(payload.get('channel') or employee.get('preferred_contact_channel') or 'whatsapp')
        link_data = build_portal_link_from_cpf(
            request_base_url(handler),
            employee.get('cpf'),
            EMPLOYEE_PORTAL_SECRET_KEY
        )
        token = link_data['token']
        access_link = link_data['access_link']
        structured_log('info', 'ficha.finalize.link_generated', ficha_period_id=int(ficha['id']), employee_id=int(employee['id']), channel=channel, elapsed_ms=round((time.perf_counter() - finalize_started_at) * 1000, 2))
        now = datetime.now(UTC).isoformat()
        expires_at = link_data['expires_at']
        upsert_employee_portal_link(
            connection,
            employee_id=int(employee['id']),
            company_id=int(employee['company_id']),
            token=token,
            qr_code_value=access_link,
            expires_at=expires_at,
            actor_id=int(actor['id']),
            now=now,
        )
        employee_name = str(employee.get('name') or 'Colaborador')
        message = (
            f"Olá {employee_name}! 👷\n"
            f"Seu link da Ficha de EPI (48h):\n{access_link}\n"
            "Assine o período, solicite EPIs e registre sua avaliação."
        )
        launch_url = ''
        if channel == 'whatsapp':
            phone = ''.join(ch for ch in str(employee.get('whatsapp') or '') if ch.isdigit())
            if not phone:
                raise ValueError('Colaborador sem WhatsApp cadastrado.')
            launch_url = f"https://wa.me/{phone}?text={quote(message)}"
        else:
            email = str(employee.get('email') or '').strip().lower()
            if not email:
                raise ValueError('Colaborador sem e-mail cadastrado.')
            subject = quote(f'Assinatura da Ficha de EPI - {employee_name}')
            launch_url = f"mailto:{email}?subject={subject}&body={quote(message)}"
        if preview_only:
            connection.commit()
            structured_log('info', 'ficha.finalize.db_saved', ficha_period_id=int(ficha['id']), status=str(ficha.get('status') or 'open'), preview_only=True, elapsed_ms=round((time.perf_counter() - finalize_started_at) * 1000, 2))
            structured_log('info', 'ficha.finalize.response_sent', ficha_period_id=int(ficha['id']), status=str(ficha.get('status') or 'open'), elapsed_ms=round((time.perf_counter() - finalize_started_at) * 1000, 2), duration_ms=round((time.perf_counter() - finalize_started_at) * 1000, 2))
            return send_json(handler, 200, {'ok': True, 'status': str(ficha.get('status') or 'open'), 'channel': channel, 'message': message, 'launch_url': launch_url, 'access_link': access_link, 'expires_at': expires_at, 'ficha_period_id': int(ficha['id']), 'period_id': int(ficha['id']), 'employee_id': int(employee['id']), 'token': token, 'manager_email': manager_email})
        if closed_period_with_batch_signature:
            connection.commit()
            structured_log('info', 'ficha.finalize.db_saved', ficha_period_id=int(ficha['id']), status='closed', preview_only=False, elapsed_ms=round((time.perf_counter() - finalize_started_at) * 1000, 2))
            structured_log('info', 'ficha.finalize.response_sent', ficha_period_id=int(ficha['id']), status='closed', elapsed_ms=round((time.perf_counter() - finalize_started_at) * 1000, 2), duration_ms=round((time.perf_counter() - finalize_started_at) * 1000, 2))
            return send_json(handler, 200, {'ok': True, 'status': 'closed', 'channel': channel, 'message': message, 'launch_url': launch_url, 'access_link': access_link, 'expires_at': expires_at, 'ficha_period_id': int(ficha['id']), 'period_id': int(ficha['id']), 'employee_id': int(employee['id']), 'token': token, 'manager_email': manager_email})
        now = datetime.now(UTC).isoformat()
        pending_items = int(totals_data.get('pending_items') or 0)
        set_ficha_period_pending_signature(connection, int(ficha['id']), now)
        connection.commit()
        structured_log('info', 'ficha.finalize.db_saved', ficha_period_id=int(ficha['id']), status='pending_signature', preview_only=False, elapsed_ms=round((time.perf_counter() - finalize_started_at) * 1000, 2))
        actual_status = 'pending_signature'
        structured_log('info', 'ficha.finalize.response_sent', ficha_period_id=int(ficha['id']), status=actual_status, elapsed_ms=round((time.perf_counter() - finalize_started_at) * 1000, 2), duration_ms=round((time.perf_counter() - finalize_started_at) * 1000, 2))
        return send_json(handler, 200, {'ok': True, 'status': actual_status, 'channel': channel, 'message': message, 'launch_url': launch_url, 'access_link': access_link, 'expires_at': expires_at, 'ficha_period_id': int(ficha['id']), 'period_id': int(ficha['id']), 'employee_id': int(employee['id']), 'token': token, 'manager_email': manager_email})


# ── POST /api/fichas/repair-status ────────────────────────────────────────────

def handle_post_fichas_repair_status(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'fichas:view')
        rows = fetch_closed_ficha_periods(connection)
        repaired_ids = []
        for row in rows:
            period = resolve_ficha_period_effective_status(connection, row_to_dict(row))
            if str(period.get('status') or '') != 'closed':
                repaired_ids.append(int(period['id']))
        connection.commit()
        structured_log('info', 'ficha.repair_status.executed', actor_user_id=int(actor['id']), repaired_count=len(repaired_ids))
        return send_json(handler, 200, {'ok': True, 'repaired_ids': repaired_ids, 'total_checked': len(rows)})


# ── POST /api/ficha-archive/purge-expired ─────────────────────────────────────

def handle_post_ficha_archive_purge_expired(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_SETTINGS_UPDATE)
        require_configuration_admin(actor)
        policy = get_ficha_retention_policy(connection, actor.get('company_id'))
        apply_snapshot_retention(
            connection,
            actor.get('company_id') if actor.get('role') != 'master_admin' else None,
            policy,
        )
        return send_json(handler, 200, {'ok': True, 'policy': policy})


def handle_get_ficha_html(handler, parsed, payload, match):
    employee_id = int(match.group(1))
    query = parse_qs(parsed.query)
    action = str(query.get('action', ['view'])[0] or 'view').strip().lower()
    action = action if action in {'view', 'print'} else 'view'
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'fichas:view')
        employee = get_employee_by_id(connection, employee_id)
        if not employee:
            raise ValueError('Colaborador não encontrado.')
        try:
            ensure_actor_employee_scope(connection, actor, employee)
        except PermissionError:
            register_ficha_epi_audit(
                connection, actor=actor, employee=employee, action='denied',
                ip_address=str(getattr(handler, 'client_address', ('',))[0] or ''),
                user_agent=handler.headers.get('User-Agent', ''),
            )
            connection.commit()
            raise
        html_content = build_ficha_epi_html(
            connection, employee_id, actor,
            get_employee_fn=get_employee_by_id,
            ensure_actor_scope_fn=None,
        )
        register_ficha_epi_audit(
            connection, actor=actor, employee=employee, action=action,
            ip_address=str(getattr(handler, 'client_address', ('',))[0] or ''),
            user_agent=handler.headers.get('User-Agent', ''),
        )
        connection.commit()
        body = html_content.encode('utf-8')
        handler.send_response(200)
        handler.send_header('Content-Type', 'text/html; charset=utf-8')
        handler.send_header('Content-Length', str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)


def handle_get_ficha_period_html(handler, parsed, payload, match):
    ficha_period_id = int(match.group(1))
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'fichas:view')
        snapshot = ensure_ficha_snapshot_for_period(connection, ficha_period_id, actor)
        period = get_ficha_period_employee(connection, ficha_period_id)
        employee = get_employee_by_id(connection, int(period['employee_id'])) if period else None
        if employee:
            register_ficha_epi_audit(
                connection, actor=actor, employee=employee, action='snapshot_view',
                ip_address=str(getattr(handler, 'client_address', ('',))[0] or ''),
                user_agent=handler.headers.get('User-Agent', ''),
            )
        connection.commit()
        body = str(snapshot.get('html_content') or '').encode('utf-8')
        handler.send_response(200)
        handler.send_header('Content-Type', 'text/html; charset=utf-8')
        handler.send_header('Content-Length', str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)


def handle_get_ficha_archive(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'reports:view')
        query = parse_qs(parsed.query)
        filters = {
            'company_id': str(query.get('company_id', [''])[0] or '').strip(),
            'unit_id': str(query.get('unit_id', [''])[0] or '').strip(),
            'employee_id': str(query.get('employee_id', [''])[0] or '').strip(),
            'status': str(query.get('status', [''])[0] or '').strip(),
            'sector': str(query.get('sector', [''])[0] or '').strip(),
            'date_from': str(query.get('date_from', [''])[0] or '').strip(),
            'date_to': str(query.get('date_to', [''])[0] or '').strip(),
            'page': str(query.get('page', ['1'])[0] or '1').strip(),
            'page_size': str(query.get('page_size', ['50'])[0] or '50').strip(),
        }
        return send_json(handler, 200, fetch_ficha_archive_snapshots(connection, actor, filters))


def handle_get_ficha_archive_html(handler, parsed, payload, match):
    snapshot_id = int(match.group(1))
    query = parse_qs(parsed.query)
    action = str(query.get('action', ['snapshot_view'])[0] or 'snapshot_view').strip().lower()
    if action not in {'snapshot_view', 'snapshot_print', 'snapshot_export'}:
        action = 'snapshot_view'
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'reports:view')
        snapshot = get_ficha_archive_snapshot_by_id(connection, actor, snapshot_id)
        register_ficha_epi_audit(
            connection, actor=actor,
            employee={
                'id': snapshot['employee_id'],
                'name': snapshot.get('employee_name') or '',
                'unit_id': snapshot['unit_id'],
                'company_id': snapshot['company_id'],
            },
            action=action,
            ip_address=str(getattr(handler, 'client_address', ('',))[0] or ''),
            user_agent=handler.headers.get('User-Agent', ''),
        )
        connection.commit()
        html = str(snapshot.get('html_content') or '')
        if action == 'snapshot_print':
            print_script = (
                '<script>window.addEventListener("load",function(){'
                'setTimeout(function(){try{window.focus();window.print();}catch(e){}},300);});</script>'
            )
            if '</body>' in html:
                html = html.replace('</body>', print_script + '</body>', 1)
            else:
                html += print_script
        body = html.encode('utf-8')
        handler.send_response(200)
        handler.send_header('Content-Type', 'text/html; charset=utf-8')
        if action == 'snapshot_export':
            employee_label = str(snapshot.get('employee_name') or f'ficha-{snapshot_id}')
            safe_name = ''.join(ch if ch.isalnum() else '-' for ch in employee_label).strip('-') or f'ficha-{snapshot_id}'
            filename = f'ficha-epi-{safe_name}-{snapshot_id}.html'
            handler.send_header('Content-Disposition', f"attachment; filename=\"{filename}\"; filename*=UTF-8''{quote(filename)}")
        handler.send_header('Content-Length', str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    router.register('GET',  r'/api/ficha-epi/(\d+)\.html',        handle_get_ficha_html,         regex=True)
    router.register('GET',  r'/api/ficha-epi-period/(\d+)\.html', handle_get_ficha_period_html,  regex=True)
    router.register('GET',  '/api/ficha-archive',                  handle_get_ficha_archive)
    router.register('GET',  r'/api/ficha-archive/(\d+)\.html',    handle_get_ficha_archive_html, regex=True)
    router.register('GET',  '/api/fichas',                         handle_get_fichas)
    router.register('GET',  '/api/ficha-epi-snapshots',          handle_get_ficha_epi_snapshots)
    router.register('GET',  '/api/ficha-epi-audit',              handle_get_ficha_epi_audit)
    router.register('PUT',  '/api/ficha-config',                 handle_put_ficha_config)
    router.register('PUT',  '/api/ficha-retention-policy',       handle_put_ficha_retention_policy)
    router.register('PUT',  '/api/ficha-archive/purge-expired',  handle_put_ficha_archive_purge)
    router.register('POST', '/api/fichas/finalize',              handle_post_fichas_finalize)
    router.register('POST', '/api/fichas/repair-status',         handle_post_fichas_repair_status)
    router.register('POST', '/api/ficha-archive/purge-expired',  handle_post_ficha_archive_purge_expired)

