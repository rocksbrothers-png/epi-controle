"""Rotas de relatórios."""

from contextlib import closing
from datetime import datetime, timezone
from urllib.parse import parse_qs

from core.database import get_connection
from core.permissions import PERM_STOCK_VIEW
from core.repository import authorize_action
from modules.employees.service import actor_operational_unit_id
from core.security import resolve_actor_user_id
from epi_backend.db import row_to_dict
from epi_backend.http_utils import require_fields, send_json
from modules.purchases.service import get_actor_purchase_unit_scope
from modules.settings.service import canary_evaluate_visibility_dataset

UTC = timezone.utc


# ── GET ───────────────────────────────────────────────────────────────────────

def handle_get_reports(handler, parsed, payload, match):
    from modules.reports.service import build_reports
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'reports:view')
        filters = {key: values[0] for key, values in parse_qs(parsed.query).items() if key != 'actor_user_id'}
        return send_json(handler, 200, build_reports(connection, actor, filters))


def handle_get_report_requests(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_STOCK_VIEW)
        company_id = int(actor['company_id'])
        scope_unit_id = actor_operational_unit_id(connection, actor)
        purchase_scope = get_actor_purchase_unit_scope(connection, actor)
        clauses = ['rr.company_id = %s']
        params = [company_id]
        if scope_unit_id:
            clauses.append('rr.unit_id = %s')
            params.append(int(scope_unit_id))
        elif purchase_scope:
            ph = ','.join(['%s'] * len(purchase_scope))
            clauses.append(f'rr.unit_id IN ({ph})')
            params.extend(purchase_scope)
        where = f"WHERE {' AND '.join(clauses)}"
        rows = connection.execute(
            f'SELECT rr.*, u.name AS unit_name FROM report_requests rr '
            f'LEFT JOIN units u ON u.id = rr.unit_id '
            f'{where} ORDER BY rr.created_at DESC LIMIT 100',
            tuple(params),
        ).fetchall()
        items = [row_to_dict(r) for r in rows]
        items = canary_evaluate_visibility_dataset(
            connection, actor, endpoint_name='/api/report-requests', dataset_name='report_requests', legacy_items=items
        )
        return send_json(handler, 200, {'items': items})


# ── POST /api/report-requests ─────────────────────────────────────────────────

def handle_post_report_requests(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_STOCK_VIEW)
        if actor.get('role') not in ('approver', 'general_admin', 'registry_admin', 'master_admin'):
            raise PermissionError('Apenas Aprovadores e Administradores podem solicitar relatórios.')
        company_id = int(actor['company_id'])
        purchase_scope = get_actor_purchase_unit_scope(connection, actor)
        unit_id = payload.get('unit_id')
        if unit_id:
            unit_id = int(unit_id)
            if purchase_scope and unit_id not in purchase_scope:
                raise PermissionError('Aprovador só pode solicitar relatório para unidades que administra.')
        now = datetime.now(UTC).isoformat()
        connection.execute(
            'INSERT INTO report_requests (company_id, unit_id, requester_user_id, requester_name, '
            'period_year, period_month, notes, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (company_id, unit_id, int(actor['id']), actor['full_name'],
             payload.get('period_year') or None, payload.get('period_month') or None,
             str(payload.get('notes') or '').strip(), 'pending', now)
        )
        connection.commit()
        return send_json(handler, 201, {'ok': True})


# ── POST /api/report-requests/{id}/mark-done ─────────────────────────────────

def handle_post_report_request_mark_done(handler, parsed, payload, match):
    rr_id = int(match.group(1))
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_STOCK_VIEW)
        if actor.get('role') not in ('admin', 'general_admin', 'registry_admin', 'master_admin'):
            raise PermissionError('Apenas Administradores podem marcar relatório como enviado.')
        now = datetime.now(UTC).isoformat()
        connection.execute(
            "UPDATE report_requests SET status = 'done', handled_by_user_id = ?, handled_by_name = ?, handled_at = ? WHERE id = ? AND company_id = ?",
            (int(actor['id']), actor['full_name'], now, rr_id, int(actor['company_id']))
        )
        connection.commit()
        return send_json(handler, 200, {'ok': True})


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    router.register('GET',  '/api/reports',                                      handle_get_reports)
    router.register('GET',  '/api/report-requests',                              handle_get_report_requests)
    router.register('POST', '/api/report-requests',                              handle_post_report_requests)
    router.register('POST', r'^/api/report-requests/(\d+)/mark-done$',          handle_post_report_request_mark_done, regex=True)
