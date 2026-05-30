"""Rotas do portal de colaboradores."""

from contextlib import closing

from core.database import get_connection
from epi_backend.http_utils import send_bytes, send_json, structured_log
from modules.portal.service import (
    EmployeePortalAccessDenied,
    build_employee_ficha_pdf,
    resolve_external_employee_context,
)
from urllib.parse import parse_qs


# ── GET ───────────────────────────────────────────────────────────────────────

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


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    router.register('GET', '/api/employee-access/pdf', handle_get_employee_access_pdf)
