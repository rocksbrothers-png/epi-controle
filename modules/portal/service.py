"""Serviços do portal do funcionário."""
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone

from epi_backend.config import JWT_SECRET
from epi_backend.db import row_to_dict
from core.pdf import build_pdf_document

UTC = timezone.utc

EMPLOYEE_PORTAL_LINK_HOURS = 48
EMPLOYEE_PORTAL_SECRET_KEY = str(
    __import__('os').environ.get('EMPLOYEE_PORTAL_SECRET_KEY') or JWT_SECRET or 'employee-portal-secret'
).strip()

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


def register_employee_portal_audit(connection, portal_context, action, ip_address='', user_agent='', payload=None):
    if not portal_context:
        return
    now = datetime.now(UTC).isoformat()
    # Rastreabilidade jurídica: o log carrega também o CNPJ (LegalEntity) e a
    # unidade do colaborador, sem exigir migração da tabela de auditoria.
    audit_payload = dict(payload or {})
    if portal_context.get('legal_entity_id'):
        audit_payload.setdefault('legal_entity_id', portal_context.get('legal_entity_id'))
        audit_payload.setdefault('company_tax_id', portal_context.get('legal_entity_cnpj'))
    if portal_context.get('unit_id'):
        audit_payload.setdefault('unit_id', portal_context.get('unit_id'))
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
            json.dumps(audit_payload, ensure_ascii=False),
            now
        )
    )


def get_employee_portal_context_by_token(connection, token):
    if not token:
        return None
    # Portal do colaborador exibe Empresa / CNPJ / Unidade — o CNPJ vem do
    # vínculo jurídico do colaborador (LegalEntity), não da empresa contratante.
    from modules.legal_entities.service import employee_legal_entity_sql
    legal_entity_select, legal_entity_join = employee_legal_entity_sql(connection)
    row = connection.execute(
        f'''
        SELECT employee_portal_links.id AS portal_link_id, employee_portal_links.company_id, employee_portal_links.employee_id,
               employee_portal_links.token, employee_portal_links.active, employee_portal_links.expires_at,
               employee_portal_links.cpf_attempts, employee_portal_links.last_cpf_attempt_at, employee_portal_links.blocked_at,
               employees.name AS employee_name, employees.employee_id_code, employees.role_name, employees.sector,
               employees.schedule_type, employees.unit_id, units.name AS unit_name, companies.name AS company_name{legal_entity_select}
        FROM employee_portal_links
        JOIN employees ON employees.id = employee_portal_links.employee_id
        JOIN units ON units.id = employees.unit_id
        JOIN companies ON companies.id = employee_portal_links.company_id{legal_entity_join}
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
    context = get_employee_portal_context_by_token(connection, token)
    if not context:
        raise EmployeePortalAccessDenied('TOKEN_NOT_FOUND', MSG_TOKEN_EXPIRED_ACCESS)
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
    # Entrega revertida por rollback lógico (#211) sai do PDF da ficha: o
    # colaborador não pode receber um documento afirmando que recebeu um EPI
    # cuja importação foi desfeita.
    from modules.deliveries.visibility import active_delivery_sql
    reversal = active_delivery_sql(connection, 'deliveries')
    deliveries = connection.execute(
        f'''
        SELECT deliveries.delivery_date, deliveries.quantity, deliveries.quantity_label, deliveries.signature_name,
               deliveries.signature_at, epis.name AS epi_name, epis.purchase_code
        FROM deliveries
        JOIN epis ON epis.id = deliveries.epi_id
        WHERE deliveries.employee_id = ?{reversal}
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


def build_portal_link_from_cpf(base_url, funcionario_cpf, secret_key):
    cpf_digits = normalize_cpf(funcionario_cpf)
    now = datetime.now(UTC)
    expires_at_dt = now + timedelta(hours=EMPLOYEE_PORTAL_LINK_HOURS)
    exp_unix = int(expires_at_dt.timestamp())
    nonce = secrets.token_hex(8)
    payload = f'{cpf_digits}:{exp_unix}:{nonce}'
    signature = hmac.new(str(secret_key).encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest()
    token = f'{exp_unix}.{nonce}.{signature}'
    return {
        'token': token,
        'expires_at': expires_at_dt.isoformat(),
        'access_link': f"{str(base_url).rstrip('/')}/?employee_token={token}"
    }


# ── Portal data queries ───────────────────────────────────────────────────────

def get_portal_employee_deliveries(connection, employee_id):
    # Entrega revertida por rollback lógico (#211) não aparece no portal
    # do colaborador: ela deixou de valer como entrega.
    from modules.deliveries.visibility import active_delivery_sql
    return connection.execute(
        (
            'SELECT deliveries.id, deliveries.delivery_date, deliveries.next_replacement_date, deliveries.quantity, deliveries.quantity_label, '
            'deliveries.signature_name, deliveries.signature_at, deliveries.signature_ip, deliveries.signature_comment, '
            'deliveries.handover_confirmed_at, deliveries.returned_date, deliveries.returned_condition, '
            'fi.ficha_period_id, fi.item_signature_name, fi.item_signature_at, '
            'epis.name AS epi_name, epis.purchase_code, epis.ca, epis.epi_validity_date '
            'FROM deliveries '
            'LEFT JOIN epi_ficha_items fi ON fi.delivery_id = deliveries.id '
            'JOIN epis ON epis.id = deliveries.epi_id '
            'WHERE deliveries.employee_id = ? '
            + active_delivery_sql(connection, 'deliveries') + ' '
            'ORDER BY deliveries.delivery_date DESC, deliveries.id DESC'
        ),
        (int(employee_id),)
    ).fetchall()


def get_portal_employee_fichas(connection, employee_id):
    return connection.execute(
        (
            'SELECT fp.id, fp.period_start, fp.period_end, fp.status, fp.batch_signature_name, fp.batch_signature_at, '
            '(SELECT COUNT(*) FROM epi_ficha_items fi WHERE fi.ficha_period_id = fp.id) AS total_items, '
            "(SELECT COUNT(*) FROM epi_ficha_items fi WHERE fi.ficha_period_id = fp.id AND COALESCE(fi.item_signature_at, '') = '') AS pending_items "
            'FROM epi_ficha_periods fp '
            'WHERE fp.employee_id = ? '
            'ORDER BY fp.period_start DESC'
        ),
        (int(employee_id),)
    ).fetchall()


def get_portal_employee_requests(connection, employee_id):
    return connection.execute(
        (
            'SELECT r.id, r.epi_id, r.quantity, r.glove_size, r.size, r.uniform_size, r.status, r.justification, r.requested_at, r.last_updated_at, '
            'r.rejection_reason, r.postponed_until, r.approver_name, r.approved_at, '
            'epis.name AS epi_name, epis.purchase_code '
            'FROM epi_requests r '
            'JOIN epis ON epis.id = r.epi_id '
            'WHERE r.employee_id = ? '
            'ORDER BY r.requested_at DESC, r.id DESC'
        ),
        (int(employee_id),)
    ).fetchall()


def get_portal_employee_feedbacks(connection, employee_id):
    return connection.execute(
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
        (int(employee_id),)
    ).fetchall()


def get_portal_available_epis(connection, company_id):
    return connection.execute(
        (
            'SELECT id, name, purchase_code, ca, unit_measure, glove_size, size, uniform_size, '
            'unit_id, active_joinventure '
            'FROM epis '
            'WHERE company_id = ? AND active = 1 '
            'ORDER BY name ASC'
        ),
        (int(company_id),)
    ).fetchall()


# ── Feedback ──────────────────────────────────────────────────────────────────

def create_employee_feedback(connection, company_id, unit_id, employee_id, epi_id, fb_type, ratings,
                              comments, improvement_suggestion, suggested_new_epi_name,
                              suggested_new_epi_notes, suggested_new_epi_link, request_token, now):
    cursor = connection.execute(
        (
            'INSERT INTO epi_feedbacks ('
            'company_id, unit_id, employee_id, epi_id, type, comfort_rating, quality_rating, adequacy_rating, performance_rating, '
            'comments, improvement_suggestion, suggested_new_epi_name, suggested_new_epi_notes, suggested_new_epi_link, '
            "status, request_token, created_at, updated_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pendente', ?, ?, ?)"
        ),
        (
            int(company_id), int(unit_id), int(employee_id),
            int(epi_id) if epi_id else None,
            fb_type,
            ratings['comfort_rating'], ratings['quality_rating'],
            ratings['adequacy_rating'], ratings['performance_rating'],
            str(comments or '').strip(), str(improvement_suggestion or '').strip(),
            str(suggested_new_epi_name or '').strip(), str(suggested_new_epi_notes or '').strip(),
            str(suggested_new_epi_link or '').strip(),
            request_token, now, now,
        )
    )
    feedback_id = int(cursor.lastrowid)
    connection.execute(
        (
            "INSERT INTO epi_feedback_history (feedback_id, company_id, status, notes, actor_name, created_at) "
            "VALUES (?, ?, 'pendente', ?, 'Funcionário', ?)"
        ),
        (feedback_id, int(company_id), str(comments or '').strip(), now)
    )
    return feedback_id


# ── Item signing ──────────────────────────────────────────────────────────────

def get_delivery_for_employee(connection, delivery_id):
    return connection.execute(
        'SELECT id, employee_id FROM deliveries WHERE id = ?',
        (int(delivery_id),)
    ).fetchone()


def sign_delivery(connection, delivery_id, name, data, ip, signed_at, comment):
    connection.execute(
        (
            'UPDATE deliveries '
            'SET signature_name = ?, signature_data = ?, signature_at = ?, signature_ip = ?, signature_comment = ? '
            'WHERE id = ?'
        ),
        (name, data, signed_at, ip, comment, int(delivery_id))
    )


def sign_ficha_items_by_delivery(connection, delivery_id, name, data, ip, signed_at, comment):
    connection.execute(
        (
            "UPDATE epi_ficha_items "
            "SET item_signature_name = ?, item_signature_data = ?, item_signature_ip = ?, item_signature_at = ?, item_signature_comment = ?, signed_mode = 'item', updated_at = ? "
            "WHERE delivery_id = ?"
        ),
        (name, data, ip, signed_at, comment, signed_at, int(delivery_id))
    )


# ── Employee lookup ───────────────────────────────────────────────────────────

def lookup_employee_by_qr_or_token(connection, qr_value, lookup_token=''):
    params = [qr_value]
    token_clause = ''
    if lookup_token:
        params.append(lookup_token)
        token_clause = ' OR employee_portal_links.token = ?'
    return connection.execute(
        (
            'SELECT employees.id, employees.company_id, employees.unit_id, employees.employee_id_code, employees.name, '
            'employees.sector, employees.role_name, employees.schedule_type, '
            'employee_portal_links.qr_code_value, employee_portal_links.token '
            'FROM employee_portal_links '
            'JOIN employees ON employees.id = employee_portal_links.employee_id '
            'WHERE employee_portal_links.active = 1 '
            f'AND (employee_portal_links.qr_code_value = ?{token_clause})'
        ),
        tuple(params)
    ).fetchone()


# ── Portal link management ────────────────────────────────────────────────────

def upsert_employee_portal_link(connection, employee_id, company_id, token, qr_code_value, expires_at, actor_id, now):
    existing = connection.execute(
        'SELECT id FROM employee_portal_links WHERE employee_id = ?',
        (int(employee_id),)
    ).fetchone()
    if existing:
        connection.execute(
            (
                'UPDATE employee_portal_links '
                'SET token = ?, qr_code_value = ?, active = 1, expires_at = ?, updated_at = ? '
                'WHERE employee_id = ?'
            ),
            (token, qr_code_value, expires_at, now, int(employee_id))
        )
    else:
        connection.execute(
            (
                'INSERT INTO employee_portal_links ('
                'company_id, employee_id, token, qr_code_value, active, expires_at, '
                'created_by_user_id, created_at, updated_at'
                ') VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)'
            ),
            (int(company_id), int(employee_id), token, qr_code_value, expires_at, int(actor_id), now, now)
        )


def get_active_portal_link(connection, employee_id):
    return connection.execute(
        (
            'SELECT token, expires_at '
            'FROM employee_portal_links '
            'WHERE employee_id = ? AND active = 1 '
            'ORDER BY id DESC LIMIT 1'
        ),
        (int(employee_id),)
    ).fetchone()


def revoke_employee_portal_link(connection, employee_id, revoked_at):
    connection.execute(
        "UPDATE employee_portal_links SET active = 0, updated_at = ? WHERE employee_id = ?",
        (revoked_at, int(employee_id))
    )


# ── Batch signing ─────────────────────────────────────────────────────────────

def get_ficha_period_for_signing(connection, ficha_period_id):
    return connection.execute(
        'SELECT id, employee_id, period_start, period_end FROM epi_ficha_periods WHERE id = ?',
        (int(ficha_period_id),),
    ).fetchone()


def count_ficha_period_items(connection, ficha_period_id):
    row = connection.execute(
        'SELECT COUNT(*) AS total FROM epi_ficha_items WHERE ficha_period_id = ?',
        (int(ficha_period_id),),
    ).fetchone()
    return int((row or {'total': 0})['total'] or 0)


def sign_ficha_period_batch(connection, ficha_id, name, data, ip, signed_at, comment):
    cursor = connection.execute(
        (
            "UPDATE epi_ficha_periods "
            "SET status = 'pending_signature', batch_signature_name = ?, batch_signature_data = ?, batch_signature_ip = ?, batch_signature_at = ?, batch_signature_comment = ?, updated_at = ? "
            "WHERE id = ?"
        ),
        (name, data, ip, signed_at, comment, signed_at, int(ficha_id))
    )
    return int(cursor.rowcount or 0)


def sign_ficha_items_batch(connection, ficha_id, name, data, ip, signed_at, comment):
    cursor = connection.execute(
        (
            "UPDATE epi_ficha_items "
            "SET item_signature_name = ?, item_signature_data = ?, item_signature_ip = ?, item_signature_at = ?, item_signature_comment = ?, signed_mode = 'batch', updated_at = ? "
            "WHERE ficha_period_id = ?"
        ),
        (name, data, ip, signed_at, comment, signed_at, int(ficha_id))
    )
    return int(cursor.rowcount or 0)


def sign_unsigned_deliveries_for_period(connection, ficha_id, name, data, ip, signed_at, comment):
    connection.execute(
        (
            "UPDATE deliveries "
            "SET signature_name = ?, signature_data = ?, signature_ip = ?, signature_at = ?, signature_comment = ? "
            "WHERE id IN (SELECT delivery_id FROM epi_ficha_items WHERE ficha_period_id = ?) "
            "AND COALESCE(signature_at, '') = ''"
        ),
        (name, data, ip, signed_at, comment, int(ficha_id))
    )


def sign_unsigned_devolutions_for_period(connection, ficha_id, name, data, ip, signed_at, comment):
    connection.execute(
        (
            "UPDATE epi_devolutions "
            "SET signature_name = ?, signature_data = ?, signature_ip = ?, signature_at = ?, signature_comment = ? "
            "WHERE ficha_period_id = ? "
            "AND COALESCE(signature_at, '') = ''"
        ),
        (name, data, ip, signed_at, comment, int(ficha_id),)
    )


def get_persisted_batch_signature(connection, ficha_id):
    return connection.execute(
        'SELECT batch_signature_name, batch_signature_data, batch_signature_at FROM epi_ficha_periods WHERE id = ?',
        (int(ficha_id),),
    ).fetchone()


# ── Close period ──────────────────────────────────────────────────────────────

def get_ficha_period_for_close(connection, ficha_period_id):
    return connection.execute(
        'SELECT id, employee_id, status FROM epi_ficha_periods WHERE id = ?',
        (int(ficha_period_id),)
    ).fetchone()


def close_ficha_period(connection, ficha_id, closed_at):
    connection.execute(
        "UPDATE epi_ficha_periods SET status = 'closed', updated_at = ? WHERE id = ?",
        (closed_at, int(ficha_id))
    )


# ── EPI requests ──────────────────────────────────────────────────────────────

def create_portal_epi_request(connection, company_id, unit_id, employee_id, epi_id,
                               quantity, glove_size, size, uniform_size,
                               request_token, justification, now):
    from modules.units.service import ensure_unit_operational
    ensure_unit_operational(connection, unit_id, 'requisições de EPI')
    from modules.employees.service import ensure_employee_operational
    ensure_employee_operational(connection, employee_id, 'requisições de EPI')
    from modules.epis.service import ensure_epi_operational
    ensure_epi_operational(connection, epi_id, 'requisições de EPI')
    cursor = connection.execute(
        (
            'INSERT INTO epi_requests ('
            'company_id, unit_id, employee_id, epi_id, quantity, glove_size, size, uniform_size, request_token, status, '
            'justification, requested_at, requested_by, last_updated_at'
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'solicitado', ?, ?, 'employee', ?)"
        ),
        (
            int(company_id), int(unit_id), int(employee_id), int(epi_id),
            int(quantity or 1), glove_size, size, uniform_size,
            str(request_token or '').strip(), str(justification or '').strip(),
            now, now,
        )
    )
    request_id = int(cursor.lastrowid)
    connection.execute(
        'INSERT INTO epi_request_history (request_id, company_id, status, notes, actor_name, created_at) VALUES (?, ?, ?, ?, ?, ?)',
        (request_id, int(company_id), 'solicitado', str(justification or '').strip(), 'Funcionário', now)
    )
    return request_id
