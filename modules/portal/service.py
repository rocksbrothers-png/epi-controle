"""Serviços do portal do funcionário."""
import hashlib
import json
from datetime import datetime, timezone

from epi_backend.db import row_to_dict
from core.pdf import build_pdf_document

UTC = timezone.utc

MSG_TOKEN_ABSENT = 'Token ausente.'
MSG_TOKEN_EXPIRED_ACCESS = 'Token de acesso inválido ou expirado.'


class EmployeePortalAccessDenied(PermissionError):
    def __init__(self, code, message, *, portal_context=None):
        super().__init__(message)
        self.code = str(code or 'TOKEN_EXPIRED')
        self.message = str(message or MSG_TOKEN_EXPIRED_ACCESS)
        self.portal_context = portal_context or {}


def normalize_cpf(value):
    digits = ''.join(ch for ch in str(value or '') if ch.isdigit())
    if len(digits) != 11:
        raise ValueError('CPF do colaborador deve conter 11 dígitos.')
    return digits


def parse_iso_datetime_utc(value):
    raw = str(value or '').strip()
    if not raw:
        return None
    normalized = raw[:-1] + '+00:00' if raw.endswith('Z') else raw
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def hash_portal_token(token):
    return hashlib.sha256(str(token or '').encode('utf-8')).hexdigest()


def parse_int_flexible(value, default=0):
    raw = str(value or '').strip()
    if not raw:
        return int(default)
    digits = ''.join(ch for ch in raw if ch.isdigit() or ch == '-')
    if not digits:
        return int(default)
    try:
        return int(digits)
    except ValueError:
        return int(default)


def _get_employee_by_id(connection, employee_id):
    row = connection.execute(
        'SELECT id, company_id, unit_id, employee_id_code, cpf, name, email, whatsapp, preferred_contact_channel, sector, role_name, admission_date, schedule_type, tipo_vinculo, empresa_origem FROM employees WHERE id = ?',
        (employee_id,)
    ).fetchone()
    return row_to_dict(row) if row else None


def get_employee_user_by_token(connection, token):
    if not token:
        return None
    row = connection.execute(
        '''
        SELECT users.id, users.full_name, users.username, users.role, users.company_id, users.active, users.linked_employee_id,
               users.employee_access_token, users.employee_access_expires_at,
               companies.name AS company_name, companies.cnpj AS company_cnpj,
               employees.name AS employee_name, employees.employee_id_code, employees.role_name, employees.sector, employees.schedule_type
        FROM users
        JOIN employees ON employees.id = users.linked_employee_id
        LEFT JOIN companies ON companies.id = users.company_id
        WHERE users.employee_access_token = ? AND users.role = 'employee'
        LIMIT 1
        ''',
        (token,)
    ).fetchone()
    if not row:
        return None
    item = row_to_dict(row)
    expires_at = str(item.get('employee_access_expires_at') or '').strip()
    expires_at_dt = parse_iso_datetime_utc(expires_at)
    if expires_at_dt and expires_at_dt <= datetime.now(UTC):
        return None
    if int(item.get('active') or 0) != 1:
        return None
    return item


def register_employee_portal_audit(connection, portal_context, action, ip_address='', user_agent='', payload=None):
    if not portal_context:
        return
    now = datetime.now(UTC).isoformat()
    connection.execute(
        '''
        INSERT INTO employee_portal_audit_logs (
            company_id, employee_id, portal_link_id, token_hash, action, ip_address, user_agent, payload, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            int(portal_context['company_id']),
            int(portal_context['employee_id']),
            int(portal_context['portal_link_id']) if portal_context.get('portal_link_id') else None,
            hash_portal_token(portal_context.get('token')),
            str(action or '').strip() or 'unknown',
            str(ip_address or '').strip(),
            str(user_agent or '').strip(),
            json.dumps(payload or {}, ensure_ascii=False),
            now
        )
    )


def get_employee_portal_context_by_token(connection, token):
    if not token:
        return None
    row = connection.execute(
        '''
        SELECT employee_portal_links.id AS portal_link_id, employee_portal_links.company_id, employee_portal_links.employee_id,
               employee_portal_links.token, employee_portal_links.active, employee_portal_links.expires_at,
               employee_portal_links.cpf_attempts, employee_portal_links.last_cpf_attempt_at, employee_portal_links.blocked_at,
               employees.name AS employee_name, employees.employee_id_code, employees.role_name, employees.sector,
               employees.schedule_type, employees.unit_id, units.name AS unit_name, companies.name AS company_name
        FROM employee_portal_links
        JOIN employees ON employees.id = employee_portal_links.employee_id
        JOIN units ON units.id = employees.unit_id
        JOIN companies ON companies.id = employee_portal_links.company_id
        WHERE employee_portal_links.token = ?
        LIMIT 1
        ''',
        (token,)
    ).fetchone()
    if not row:
        return None
    return row_to_dict(row)


def ensure_employee_last3_cpf(connection, employee_id, cpf_last3):
    digits = ''.join(ch for ch in str(cpf_last3 or '') if ch.isdigit())
    if len(digits) != 3:
        raise PermissionError('Informe os 3 últimos dígitos do CPF para acessar.')
    employee = _get_employee_by_id(connection, int(employee_id))
    if not employee:
        raise PermissionError('Colaborador não encontrado para validação do CPF.')
    cpf_digits = normalize_cpf(employee.get('cpf'))
    if cpf_digits[-3:] != digits:
        raise PermissionError('Os 3 últimos dígitos do CPF não conferem.')


def validate_portal_cpf_with_attempts(connection, portal_context, cpf_last3, *, ip_address='', user_agent=''):
    if not portal_context:
        raise EmployeePortalAccessDenied('TOKEN_NOT_FOUND', MSG_TOKEN_EXPIRED_ACCESS)
    if int(portal_context.get('active') or 0) != 1:
        raise EmployeePortalAccessDenied('TOKEN_REVOKED', MSG_TOKEN_EXPIRED_ACCESS, portal_context=portal_context)
    if str(portal_context.get('blocked_at') or '').strip():
        raise EmployeePortalAccessDenied('LINK_BLOCKED', 'Este link foi bloqueado por tentativas inválidas de CPF. Solicite um novo token.', portal_context=portal_context)

    expires_at = str(portal_context.get('expires_at') or '').strip()
    expires_at_dt = parse_iso_datetime_utc(expires_at)
    if expires_at_dt and expires_at_dt <= datetime.now(UTC):
        raise EmployeePortalAccessDenied('TOKEN_EXPIRED', MSG_TOKEN_EXPIRED_ACCESS, portal_context=portal_context)

    digits = ''.join(ch for ch in str(cpf_last3 or '') if ch.isdigit())
    if len(digits) != 3:
        raise EmployeePortalAccessDenied('CPF_LAST3_INVALID', 'Informe os 3 últimos dígitos do CPF para acessar.', portal_context=portal_context)

    employee = _get_employee_by_id(connection, int(portal_context['employee_id']))
    if not employee:
        raise PermissionError('Colaborador não encontrado para validação do CPF.')
    cpf_digits = normalize_cpf(employee.get('cpf'))
    attempts = int(portal_context.get('cpf_attempts') or 0)
    now = datetime.now(UTC).isoformat()

    if cpf_digits[-3:] == digits:
        if attempts > 0:
            connection.execute(
                "UPDATE employee_portal_links SET cpf_attempts = 0, last_cpf_attempt_at = '', updated_at = ? WHERE id = ?",
                (now, int(portal_context['portal_link_id'])),
            )
        register_employee_portal_audit(
            connection,
            portal_context,
            'cpf_validation_success',
            ip_address=ip_address,
            user_agent=user_agent,
            payload={'attempts_before_success': attempts},
        )
        return

    attempts += 1
    remaining = max(0, 3 - attempts)
    if attempts >= 3:
        connection.execute(
            "UPDATE employee_portal_links SET cpf_attempts = ?, last_cpf_attempt_at = ?, blocked_at = ?, active = 0, updated_at = ? WHERE id = ?",
            (attempts, now, now, now, int(portal_context['portal_link_id'])),
        )
        register_employee_portal_audit(
            connection,
            portal_context,
            'cpf_validation_blocked',
            ip_address=ip_address,
            user_agent=user_agent,
            payload={'attempts': attempts},
        )
        raise EmployeePortalAccessDenied('LINK_BLOCKED', 'CPF inválido. Token bloqueado após 3 tentativas. Solicite um novo link.', portal_context=portal_context)

    connection.execute(
        "UPDATE employee_portal_links SET cpf_attempts = ?, last_cpf_attempt_at = ?, updated_at = ? WHERE id = ?",
        (attempts, now, now, int(portal_context['portal_link_id'])),
    )
    register_employee_portal_audit(
        connection,
        portal_context,
        'cpf_validation_failed',
        ip_address=ip_address,
        user_agent=user_agent,
        payload={'attempts': attempts, 'remaining_attempts': remaining},
    )
    raise EmployeePortalAccessDenied('CPF_MISMATCH', f'CPF inválido. Tentativas restantes: {remaining}.', portal_context=portal_context)


def resolve_external_employee_context(connection, token, cpf_last3=None, *, ip_address='', user_agent=''):
    if not str(token or '').strip():
        raise EmployeePortalAccessDenied('TOKEN_MISSING', MSG_TOKEN_ABSENT)
    employee_user = get_employee_user_by_token(connection, token)
    if employee_user:
        # Compatibilidade: tokens legados de users.employee_access_token não dependem de employee_portal_links.
        # Mantemos esse fluxo estável e validamos apenas os 3 últimos dígitos do CPF.
        context = {
            'company_id': int(employee_user['company_id']),
            'employee_id': int(employee_user['linked_employee_id']),
            'employee_name': employee_user.get('employee_name') or employee_user.get('full_name'),
            'employee_id_code': employee_user.get('employee_id_code'),
            'role_name': employee_user.get('role_name', ''),
            'sector': employee_user.get('sector', ''),
            'schedule_type': employee_user.get('schedule_type', ''),
            'company_name': employee_user.get('company_name', ''),
            'unit_id': None,
            'unit_name': '',
            'portal_link_id': None,
            'token': token
        }
        if cpf_last3 is not None:
            ensure_employee_last3_cpf(connection, context['employee_id'], cpf_last3)
        return context
    context = get_employee_portal_context_by_token(connection, token)
    if not context:
        raise EmployeePortalAccessDenied('TOKEN_NOT_FOUND', MSG_TOKEN_EXPIRED_ACCESS)
    if context:
        validate_portal_cpf_with_attempts(
            connection,
            context,
            cpf_last3,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    return context


def build_employee_ficha_pdf(connection, employee_user):
    employee_id = int(employee_user['linked_employee_id'])
    deliveries = connection.execute(
        '''
        SELECT deliveries.delivery_date, deliveries.quantity, deliveries.quantity_label, deliveries.signature_name,
               deliveries.signature_at, epis.name AS epi_name, epis.purchase_code
        FROM deliveries
        JOIN epis ON epis.id = deliveries.epi_id
        WHERE deliveries.employee_id = ?
        ORDER BY deliveries.delivery_date DESC, deliveries.id DESC
        ''',
        (employee_id,)
    ).fetchall()

    lines = []
    lines.append({'text': f"Ficha EPI - {employee_user.get('employee_name')}", 'bold': True, 'size': 14, 'x': 50, 'y': 760})
    lines.append({'text': f"Empresa: {employee_user.get('company_name') or '-'}", 'x': 50, 'y': 738})
    lines.append({'text': f"Matricula: {employee_user.get('employee_id_code') or '-'}", 'x': 50, 'y': 720})
    lines.append({'text': f"Setor: {employee_user.get('sector') or '-'}", 'x': 50, 'y': 702})
    lines.append({'text': f"Funcao: {employee_user.get('role_name') or '-'}", 'x': 50, 'y': 684})
    lines.append({'text': ' ', 'x': 50, 'y': 666})
    if deliveries:
        y = 648
        for item in deliveries:
            lines.append({
                'text': f"{item['delivery_date']} | {item['epi_name']} ({item['purchase_code']}) | {item['quantity']} {item['quantity_label']} | assinatura: {item['signature_name']} {item['signature_at'] or ''}",
                'x': 50,
                'y': y,
                'size': 10
            })
            y -= 16
            if y < 60:
                break
    else:
        lines.append({'text': 'Nenhuma entrega encontrada.', 'x': 50, 'y': 648})
    return build_pdf_document([lines], None)
