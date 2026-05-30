"""Rotas do portal de colaboradores."""

from contextlib import closing
from datetime import datetime, timezone
from urllib.parse import parse_qs

from core.database import get_connection
from core.repository import get_employee_by_id, get_epi_by_id, get_unit_active_jv_name
from epi_backend.db import row_to_dict
from epi_backend.epi_scope import is_epi_visible_for_unit
from epi_backend.http_utils import send_bytes, send_json, structured_log
from modules.ficha.service import is_valid_ficha_period_state, resolve_ficha_period_effective_status
from modules.portal.service import (
    EmployeePortalAccessDenied,
    build_employee_ficha_pdf,
    register_employee_portal_audit,
    resolve_external_employee_context,
)

UTC = timezone.utc


# ── GET ───────────────────────────────────────────────────────────────────────

def handle_get_employee_access(handler, parsed, payload, match):
    query = parse_qs(parsed.query)
    token = query.get('token', [''])[0].strip()
    cpf_last3 = query.get('cpf_last3', [''])[0].strip()
    ip = str(getattr(handler, 'client_address', ('',))[0] or '')
    ua = handler.headers.get('User-Agent', '')
    with closing(get_connection()) as connection:
        try:
            employee_user = resolve_external_employee_context(
                connection, token, cpf_last3=cpf_last3, ip_address=ip, user_agent=ua,
            )
        except EmployeePortalAccessDenied as exc:
            portal_context = exc.portal_context or {}
            structured_log(
                'warning',
                'employee_portal.access_denied',
                reason=exc.code,
                link_id=portal_context.get('portal_link_id'),
                employee_id=portal_context.get('employee_id'),
                token_prefix=str(token or '')[:12],
                cpf_last3_received=''.join(ch for ch in str(cpf_last3 or '') if ch.isdigit())[:3],
            )
            return send_json(handler, 403, {'ok': False, 'error': {'code': exc.code, 'message': exc.message}})
        employee_id = int(employee_user['employee_id'])
        deliveries = connection.execute(
            (
                'SELECT deliveries.id, deliveries.delivery_date, deliveries.next_replacement_date, deliveries.quantity, deliveries.quantity_label, '
                'deliveries.signature_name, deliveries.signature_at, deliveries.signature_ip, deliveries.signature_comment, '
                'deliveries.returned_date, deliveries.returned_condition, '
                'fi.ficha_period_id, fi.item_signature_name, fi.item_signature_at, '
                'epis.name AS epi_name, epis.purchase_code, epis.ca, epis.epi_validity_date '
                'FROM deliveries '
                'LEFT JOIN epi_ficha_items fi ON fi.delivery_id = deliveries.id '
                'JOIN epis ON epis.id = deliveries.epi_id '
                'WHERE deliveries.employee_id = ? '
                'ORDER BY deliveries.delivery_date DESC, deliveries.id DESC'
            ),
            (employee_id,)
        ).fetchall()
        fichas = connection.execute(
            (
                'SELECT fp.id, fp.period_start, fp.period_end, fp.status, fp.batch_signature_name, fp.batch_signature_at, '
                '(SELECT COUNT(*) FROM epi_ficha_items fi WHERE fi.ficha_period_id = fp.id) AS total_items, '
                "(SELECT COUNT(*) FROM epi_ficha_items fi WHERE fi.ficha_period_id = fp.id AND COALESCE(fi.item_signature_at, '') = '') AS pending_items "
                'FROM epi_ficha_periods fp '
                'WHERE fp.employee_id = ? '
                'ORDER BY fp.period_start DESC'
            ),
            (employee_id,)
        ).fetchall()
        requests = connection.execute(
            (
                'SELECT r.id, r.epi_id, r.quantity, r.glove_size, r.size, r.uniform_size, r.status, r.justification, r.requested_at, r.last_updated_at, '
                'r.rejection_reason, r.postponed_until, r.approver_name, r.approved_at, '
                'epis.name AS epi_name, epis.purchase_code '
                'FROM epi_requests r '
                'JOIN epis ON epis.id = r.epi_id '
                'WHERE r.employee_id = ? '
                'ORDER BY r.requested_at DESC, r.id DESC'
            ),
            (employee_id,)
        ).fetchall()
        feedbacks = connection.execute(
            (
                'SELECT f.id, f.epi_id, f.type, f.comfort_rating, f.quality_rating, f.adequacy_rating, f.performance_rating, '
                'f.comments, f.improvement_suggestion, f.suggested_new_epi_name, f.suggested_new_epi_notes, '
                'f.status, f.employee_portal_status, f.employee_portal_message, f.created_at, f.updated_at, '
                'epis.name AS epi_name, epis.purchase_code '
                'FROM epi_feedbacks f '
                'LEFT JOIN epis ON epis.id = f.epi_id '
                'WHERE f.employee_id = ? '
                'ORDER BY f.created_at DESC, f.id DESC'
            ),
            (employee_id,)
        ).fetchall()
        _epis_rows = connection.execute(
            (
                'SELECT id, name, purchase_code, ca, unit_measure, glove_size, size, uniform_size, '
                'unit_id, active_joinventure '
                'FROM epis '
                'WHERE company_id = ? AND active = 1 '
                'ORDER BY name ASC'
            ),
            (int(employee_user['company_id']),)
        ).fetchall()
        _emp_unit_id = int(employee_user.get('unit_id') or 0)
        _emp_unit_jv = get_unit_active_jv_name(connection, _emp_unit_id) if _emp_unit_id else ''
        available_epis = []
        for _epi_row in _epis_rows:
            _epi = row_to_dict(_epi_row)
            if is_epi_visible_for_unit(
                epi_unit_id=_epi.get('unit_id'),
                epi_joint_venture_name=_epi.get('active_joinventure'),
                target_unit_id=_emp_unit_id,
                target_unit_joint_venture_name=_emp_unit_jv,
            ):
                _epi.pop('unit_id', None)
                _epi.pop('active_joinventure', None)
                available_epis.append(_epi)
        register_employee_portal_audit(
            connection,
            employee_user,
            'portal_access',
            ip_address=ip,
            user_agent=ua,
            payload={'path': parsed.path}
        )
        connection.commit()
        ficha_items = [resolve_ficha_period_effective_status(connection, row_to_dict(item)) for item in fichas]
        ficha_items = [item for item in ficha_items if is_valid_ficha_period_state(item)]
        connection.commit()
        return send_json(
            handler,
            200,
            {
                'employee': employee_user,
                'deliveries': [row_to_dict(item) for item in deliveries],
                'fichas': ficha_items,
                'requests': [row_to_dict(item) for item in requests],
                'feedbacks': [row_to_dict(item) for item in feedbacks],
                'available_epis': available_epis
            }
        )


def handle_get_employee_access_pdf(handler, parsed, payload, match):
    query = parse_qs(parsed.query)
    token = query.get('token', [''])[0].strip()
    cpf_last3 = query.get('cpf_last3', [''])[0].strip()
    ip = str(getattr(handler, 'client_address', ('',))[0] or '')
    ua = handler.headers.get('User-Agent', '')
    with closing(get_connection()) as connection:
        try:
            employee_user = resolve_external_employee_context(
                connection, token, cpf_last3=cpf_last3, ip_address=ip, user_agent=ua,
            )
        except EmployeePortalAccessDenied as exc:
            return send_json(handler, 403, {'ok': False, 'error': {'code': exc.code, 'message': exc.message}})
        if not employee_user:
            raise PermissionError('Token de acesso inválido ou expirado.')
        if not employee_user.get('linked_employee_id'):
            employee_user['linked_employee_id'] = employee_user.get('employee_id')
        pdf_bytes = build_employee_ficha_pdf(connection, employee_user)
        return send_bytes(
            handler, 200, 'application/pdf', pdf_bytes,
            f"ficha-epi-{employee_user['employee_id_code']}.pdf",
        )


# ── POST ──────────────────────────────────────────────────────────────────────

def handle_post_employee_feedback(handler, parsed, payload, match):
    from epi_backend.http_utils import require_fields
    require_fields(payload, ['token'])
    ip = str(getattr(handler, 'client_address', ('',))[0] or '')
    ua = handler.headers.get('User-Agent', '')
    with closing(get_connection()) as connection:
        portal = resolve_external_employee_context(
            connection,
            str(payload.get('token', '')).strip(),
            cpf_last3=payload.get('cpf_last3'),
            ip_address=ip,
            user_agent=ua,
        )
        if not portal:
            raise PermissionError('Link de avaliação inválido.')
        epi_id = payload.get('epi_id')
        fb_type = str(payload.get('type') or '').strip()
        if not fb_type:
            fb_type = 'sugestao' if str(payload.get('suggested_new_epi_name') or '').strip() else 'avaliacao'
        if fb_type not in ('avaliacao', 'elogio', 'reclamacao', 'sugestao'):
            fb_type = 'avaliacao'
        if epi_id:
            target_epi = get_epi_by_id(connection, int(epi_id))
            if not target_epi or int(target_epi['company_id']) != int(portal['company_id']):
                raise PermissionError('EPI inválido para avaliação.')
            _fb_unit_id = int(portal.get('unit_id') or 0)
            _fb_unit_jv = get_unit_active_jv_name(connection, _fb_unit_id) if _fb_unit_id else ''
            if not is_epi_visible_for_unit(
                epi_unit_id=target_epi.get('unit_id'),
                epi_joint_venture_name=target_epi.get('active_joinventure'),
                target_unit_id=_fb_unit_id,
                target_unit_joint_venture_name=_fb_unit_jv,
            ):
                raise PermissionError('EPI inválido para avaliação.')
        ratings = {}
        for field in ('comfort_rating', 'quality_rating', 'adequacy_rating', 'performance_rating'):
            raw = int(payload.get(field) or 0)
            ratings[field] = min(5, max(0, raw))
        now = datetime.now(UTC).isoformat()
        cursor = connection.execute(
            (
                'INSERT INTO epi_feedbacks ('
                'company_id, unit_id, employee_id, epi_id, type, comfort_rating, quality_rating, adequacy_rating, performance_rating, '
                'comments, improvement_suggestion, suggested_new_epi_name, suggested_new_epi_notes, suggested_new_epi_link, '
                "status, request_token, created_at, updated_at"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pendente', ?, ?, ?)"
            ),
            (
                int(portal['company_id']),
                int(get_employee_by_id(connection, int(portal['employee_id']))['unit_id']),
                int(portal['employee_id']),
                int(epi_id) if epi_id else None,
                fb_type,
                ratings['comfort_rating'],
                ratings['quality_rating'],
                ratings['adequacy_rating'],
                ratings['performance_rating'],
                str(payload.get('comments', '')).strip(),
                str(payload.get('improvement_suggestion', '')).strip(),
                str(payload.get('suggested_new_epi_name', '')).strip(),
                str(payload.get('suggested_new_epi_notes', '')).strip(),
                str(payload.get('suggested_new_epi_link', '')).strip(),
                str(payload.get('token', '')).strip(),
                now,
                now
            )
        )
        connection.execute(
            (
                "INSERT INTO epi_feedback_history (feedback_id, company_id, status, notes, actor_name, created_at) "
                "VALUES (?, ?, 'pendente', ?, 'Funcionário', ?)"
            ),
            (int(cursor.lastrowid), int(portal['company_id']), str(payload.get('comments', '')).strip(), now)
        )
        register_employee_portal_audit(
            connection,
            portal,
            'create_epi_feedback',
            ip_address=ip,
            user_agent=ua,
            payload={'feedback_id': int(cursor.lastrowid)}
        )
        connection.commit()
        return send_json(handler, 201, {'ok': True, 'id': cursor.lastrowid})


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    router.register('GET', '/api/employee-access',     handle_get_employee_access)
    router.register('GET', '/api/employee-access/pdf', handle_get_employee_access_pdf)
    router.register('POST', '/api/employee-feedback',  handle_post_employee_feedback)
