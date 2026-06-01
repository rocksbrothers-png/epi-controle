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
from epi_backend.http_utils import require_fields, send_json, structured_log
from modules.employees.service import normalize_preferred_contact_channel
from modules.ficha.service import (
    apply_snapshot_retention,
    build_ficha_epi_html,
    compute_ficha_period_signature_state,
    ensure_ficha_snapshot_for_period,
    fetch_ficha_archive_snapshots,
    fetch_ficha_epi_audit_logs,
    get_ficha_archive_snapshot_by_id,
    is_valid_ficha_period_state,
    register_ficha_epi_audit,
    resolve_ficha_period_effective_status,
)
from modules.portal.service import (
    EMPLOYEE_PORTAL_SECRET_KEY,
    build_portal_link_from_cpf,
)
from modules.settings.service import (
    canary_evaluate_visibility_dataset,
    get_ficha_retention_policy,
    save_ficha_config,
    save_ficha_retention_policy,
)

UTC = timezone.utc


def _get_server():
    import server_postgres as _sp
    return _sp


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
        final_where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
        periods = connection.execute(
            (
                'SELECT fp.*, employees.name AS employee_name, employees.employee_id_code, units.name AS unit_name, '
                '(SELECT COUNT(*) FROM epi_ficha_items fi WHERE fi.ficha_period_id = fp.id) AS total_items, '
                "(SELECT COUNT(*) FROM epi_ficha_items fi WHERE fi.ficha_period_id = fp.id AND COALESCE(fi.item_signature_at, '') = '') AS pending_items "
                'FROM epi_ficha_periods fp '
                'JOIN employees ON employees.id = fp.employee_id '
                'JOIN units ON units.id = fp.unit_id '
                f'{final_where} '
                'ORDER BY fp.period_start DESC, fp.id DESC'
            ),
            tuple(params)
        ).fetchall()
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
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ''
        rows = connection.execute(
            f'SELECT s.id, s.ficha_period_id, s.company_id, s.unit_id, s.employee_id, '
            f's.generated_at, s.expires_at, '
            f'employees.name AS employee_name, units.name AS unit_name '
            f'FROM ficha_epi_snapshots s '
            f'JOIN employees ON employees.id = s.employee_id '
            f'JOIN units ON units.id = s.unit_id '
            f'{where_sql} '
            f'ORDER BY s.generated_at DESC, s.id DESC LIMIT 500',
            tuple(params),
        ).fetchall()
        return send_json(handler, 200, {'items': [row_to_dict(item) for item in rows]})


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
    sp = _get_server()
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'fichas:view')
        structured_log('info', 'ficha.finalize.authorization_done', ficha_period_id=finalize_payload_period_id, actor_user_id=int(actor.get('id') or 0), elapsed_ms=round((time.perf_counter() - finalize_started_at) * 1000, 2))
        ficha = connection.execute(
            'SELECT id, company_id, unit_id, employee_id, status, batch_signature_name, batch_signature_data, batch_signature_at FROM epi_ficha_periods WHERE id = ?',
            (int(payload['ficha_period_id']),)
        ).fetchone()
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
            period = connection.execute(
                'SELECT period_start, period_end FROM epi_ficha_periods WHERE id = ?',
                (int(ficha['id']),),
            ).fetchone()
            period_data = row_to_dict(period) if period else {}
            period_start = str(period_data.get('period_start') or '').strip()
            period_end = str(period_data.get('period_end') or '').strip()
            if period_start and period_end:
                now_sync = datetime.now(UTC).isoformat()
                connection.execute(
                    (
                        'INSERT INTO epi_ficha_items ('
                        'ficha_period_id, delivery_id, company_id, employee_id, unit_id, epi_id, quantity, '
                        'item_signature_name, item_signature_data, item_signature_ip, item_signature_at, item_signature_comment, signed_mode, '
                        'created_at, updated_at'
                        ') '
                        'SELECT ?, d.id, d.company_id, d.employee_id, d.unit_id, d.epi_id, COALESCE(d.quantity, 1), '
                        "COALESCE(d.signature_name, ''), COALESCE(d.signature_data, ''), COALESCE(d.signature_ip, ''), "
                        "COALESCE(d.signature_at, ''), COALESCE(d.signature_comment, ''), "
                        "CASE WHEN COALESCE(d.signature_data, '') <> '' THEN 'delivery' ELSE '' END, ?, ? "
                        'FROM deliveries d '
                        'WHERE d.company_id = ? '
                        'AND d.employee_id = ? '
                        'AND date(d.delivery_date) >= date(?) '
                        'AND date(d.delivery_date) <= date(?) '
                        'ON CONFLICT (delivery_id) DO NOTHING'
                    ),
                    (
                        int(ficha['id']),
                        now_sync,
                        now_sync,
                        int(ficha['company_id']),
                        int(ficha['employee_id']),
                        period_start,
                        period_end,
                    ),
                )
                totals_data = compute_ficha_period_signature_state(connection, int(ficha['id']))
                total_items = int(totals_data.get('total_items') or 0)
        if total_items <= 0:
            raise ValueError('Não é possível finalizar período sem itens de entrega.')
        employee = get_employee_by_id(connection, int(ficha['employee_id']))
        if not employee:
            raise ValueError('Colaborador da ficha não encontrado.')
        sp.ensure_actor_employee_scope(connection, actor, employee)
        manager_email = ''
        linked_employee_id = actor.get('linked_employee_id')
        if linked_employee_id not in (None, '', 'null'):
            manager_employee = get_employee_by_id(connection, int(linked_employee_id))
            manager_email = str((manager_employee or {}).get('email') or '').strip().lower()
        channel = normalize_preferred_contact_channel(payload.get('channel') or employee.get('preferred_contact_channel') or 'whatsapp')
        link_data = build_portal_link_from_cpf(
            sp.request_base_url(handler),
            employee.get('cpf'),
            EMPLOYEE_PORTAL_SECRET_KEY
        )
        token = link_data['token']
        access_link = link_data['access_link']
        structured_log('info', 'ficha.finalize.link_generated', ficha_period_id=int(ficha['id']), employee_id=int(employee['id']), channel=channel, elapsed_ms=round((time.perf_counter() - finalize_started_at) * 1000, 2))
        now = datetime.now(UTC).isoformat()
        expires_at = link_data['expires_at']
        existing_link = connection.execute(
            'SELECT id FROM employee_portal_links WHERE employee_id = ?',
            (int(employee['id']),)
        ).fetchone()
        if existing_link:
            connection.execute(
                (
                    'UPDATE employee_portal_links '
                    'SET token = ?, qr_code_value = ?, active = 1, expires_at = ?, updated_at = ? '
                    'WHERE employee_id = ?'
                ),
                (token, access_link, expires_at, now, int(employee['id']))
            )
        else:
            connection.execute(
                (
                    'INSERT INTO employee_portal_links ('
                    'company_id, employee_id, token, qr_code_value, active, expires_at, created_by_user_id, created_at, updated_at'
                    ') VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)'
                ),
                (int(employee['company_id']), int(employee['id']), token, access_link, expires_at, int(actor['id']), now, now)
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
        connection.execute(
            "UPDATE epi_ficha_periods SET status = 'pending_signature', updated_at = ? WHERE id = ?",
            (now, int(ficha['id']))
        )
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
        rows = connection.execute(
            "SELECT id, status FROM epi_ficha_periods WHERE status = 'closed' ORDER BY id ASC"
        ).fetchall()
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
        period = connection.execute('SELECT employee_id FROM epi_ficha_periods WHERE id = ?', (ficha_period_id,)).fetchone()
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
        body = str(snapshot.get('html_content') or '').encode('utf-8')
        handler.send_response(200)
        handler.send_header('Content-Type', 'text/html; charset=utf-8')
        handler.send_header('Content-Length', str(len(body)))
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

