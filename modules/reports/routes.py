"""Rotas de relatórios."""

from contextlib import closing
from datetime import datetime, timezone
from urllib.parse import parse_qs

from core.database import get_connection
from core.permissions import PERM_STOCK_VIEW
from core.repository import authorize_action
from modules.employees.service import actor_operational_unit_id
from core.security import resolve_actor_user_id
from epi_backend.http_utils import require_fields, send_bytes, send_json
from modules.purchases.service import get_actor_purchase_unit_scope, purchase_listing_scope
from modules.reports.service import (
    build_report_pdf,
    create_report_request,
    fetch_report_requests,
    mark_report_request_done,
)
from modules.settings.service import canary_evaluate_visibility_dataset

UTC = timezone.utc


# ── GET ───────────────────────────────────────────────────────────────────────

def handle_get_reports(handler, parsed, payload, match):
    from modules.reports.service import build_reports
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'reports:view')
        filters = {key: values[0] for key, values in parse_qs(parsed.query).items() if key != 'actor_user_id'}
        return send_json(handler, 200, build_reports(connection, actor, filters))


def handle_get_reports_pdf(handler, parsed, payload, match):
    from modules.reports.service import build_reports
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'reports:view')
        filters = {key: values[0] for key, values in parse_qs(parsed.query).items() if key != 'actor_user_id'}
        report = build_reports(connection, actor, filters)
        meta = {
            'generated_at': datetime.now(UTC).isoformat(timespec='seconds'),
            'filters': filters,
        }
        pdf_bytes = build_report_pdf(report, meta)
        return send_bytes(handler, 200, 'application/pdf', pdf_bytes, filename='relatorio-epi.pdf')


def handle_get_report_requests(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_STOCK_VIEW)
        company_id = int(actor['company_id'])
        escopo = purchase_listing_scope(
            connection, actor, parse_qs(parsed.query).get('unit_id', [''])[0],
            actor_operational_unit_id=actor_operational_unit_id,
            purchase_units_loader=get_actor_purchase_unit_scope,
        )
        if escopo is None:
            return send_json(handler, 200, {'items': []})
        clauses = ['rr.company_id = %s']
        params = [company_id]
        if escopo.unit_id:
            clauses.append('rr.unit_id = %s')
            params.append(int(escopo.unit_id))
        elif escopo.allowed_unit_ids is not None:
            # `is not None`, não truthiness: carteira vazia já devolveu lista
            # vazia acima, mas se um dia deixar de devolver, `if carteira`
            # aqui abriria a empresa inteira em silêncio.
            ph = ','.join(['%s'] * len(escopo.allowed_unit_ids))
            clauses.append(f'rr.unit_id IN ({ph})')
            params.extend(escopo.allowed_unit_ids)
        items = fetch_report_requests(connection, clauses, params)
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
        if actor.get('role') == 'approver':
            if not unit_id or not purchase_scope or int(unit_id) not in purchase_scope:
                raise PermissionError('Aprovador só pode solicitar relatório para unidades que administra.')
        if unit_id:
            unit_id = int(unit_id)
        now = datetime.now(UTC).isoformat()
        create_report_request(
            connection, company_id, unit_id, actor['id'], actor['full_name'],
            payload.get('period_year'), payload.get('period_month'),
            str(payload.get('notes') or '').strip(), now
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
        mark_report_request_done(connection, rr_id, actor['company_id'], actor['id'], actor['full_name'], now)
        connection.commit()
        return send_json(handler, 200, {'ok': True})


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    router.register('GET',  '/api/reports.pdf',                                  handle_get_reports_pdf)
    router.register('GET',  '/api/reports',                                      handle_get_reports)
    router.register('GET',  '/api/report-requests',                              handle_get_report_requests)
    router.register('POST', '/api/report-requests',                              handle_post_report_requests)
    router.register('POST', r'^/api/report-requests/(\d+)/mark-done$',          handle_post_report_request_mark_done, regex=True)
