"""Rotas da Ficha 360° de EPI.

F1: ``GET /api/employees/{id}/ppe-360/summary`` — identificação, responsáveis
da unidade/empresa e indicadores operacionais, numa resposta só.

Autenticação é a de sempre (``resolve_actor_user_id`` + ``require_actor``; sem
sessão → 401 pelo despacho). Daí em diante tudo passa pelo contrato da F0:
papel bloqueado e permissão antes de qualquer leitura, 404 indistinto para
inexistente/outra empresa/fora do escopo, envelope único. Toda tentativa —
concedida ou negada — é auditada (DF-7).
"""

from __future__ import annotations

from contextlib import closing

from core.database import get_connection
from core.repository import require_actor
from core.security import resolve_actor_user_id
from epi_backend.http_utils import send_json
from modules.employee_ppe_360.audit import record_denied, record_granted
from modules.employee_ppe_360.contract import (
    ContractError,
    error_envelope,
    resolve_authorized_employee,
    success_envelope,
)
from modules.employee_ppe_360.summary import build_employee_summary, is_deleted

SUMMARY_PATH = r'^/api/employees/(\d+)/ppe-360/summary$'


def _requested_id(raw) -> int:
    text = str(raw or '')
    return int(text) if text.isdigit() and len(text) <= 12 else 0


def handle_get_summary(handler, parsed, payload, match):
    raw_id = match.group(1)
    with closing(get_connection()) as connection:
        actor = require_actor(connection, resolve_actor_user_id(handler, parsed))
        try:
            employee = resolve_authorized_employee(connection, actor, raw_id)
            if is_deleted(connection, employee):
                raise ContractError('EMPLOYEE_NOT_FOUND')
        except ContractError as exc:
            connection.rollback()
            record_denied(connection, handler, actor, requested_employee_id=_requested_id(raw_id), code=exc.code)
            status, body = error_envelope(exc)
            send_json(handler, status, body)
            return
        data = build_employee_summary(connection, actor, employee)
        record_granted(connection, handler, actor, employee, unit_id=data['employee']['unit']['id'])
        send_json(handler, 200, success_envelope(data))


def register_routes(router):
    from modules.employee_ppe_360.in_use_routes import IN_USE_PATH, handle_get_in_use

    router.register('GET', SUMMARY_PATH, handle_get_summary, regex=True)
    router.register('GET', IN_USE_PATH, handle_get_in_use, regex=True)
