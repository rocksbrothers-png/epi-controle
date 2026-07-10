"""Rotas do portal de colaboradores."""

from contextlib import closing
from datetime import datetime, timezone
from urllib.parse import parse_qs, quote, urlparse

from core.auth import ensure_resource_company
from core.database import get_connection
from core.repository import (
    authorize_action,
    get_employee_by_id,
    get_epi_by_id,
    get_unit_active_jv_name,
)
from core.security import resolve_actor_user_id
from epi_backend.db import row_to_dict
from epi_backend.epi_scope import get_epi_effective_jv_name, is_epi_visible_for_unit
from epi_backend.http_utils import require_fields, request_base_url, send_bytes, send_json, structured_log
from modules.employees.service import ensure_actor_employee_scope, normalize_preferred_contact_channel
from modules.ficha.service import (
    assert_ficha_period_can_close,
    compute_ficha_period_signature_state,
    get_ficha_period_close_requirements,
    is_valid_ficha_period_state,
    refresh_ficha_snapshot_for_period_if_exists,
    resolve_ficha_period_effective_status,
)
from modules.portal.service import (
    EMPLOYEE_PORTAL_SECRET_KEY,
    EmployeePortalAccessDenied,
    build_employee_ficha_pdf,
    build_portal_link_from_cpf,
    close_ficha_period,
    count_ficha_period_items,
    create_employee_feedback,
    create_portal_epi_request,
    get_active_portal_link,
    get_delivery_for_employee,
    get_ficha_period_for_close,
    get_ficha_period_for_signing,
    get_persisted_batch_signature,
    get_portal_available_epis,
    get_portal_employee_deliveries,
    get_portal_employee_feedbacks,
    get_portal_employee_fichas,
    get_portal_employee_requests,
    lookup_employee_by_qr_or_token,
    parse_int_flexible,
    parse_iso_datetime_utc,
    register_employee_portal_audit,
    resolve_external_employee_context,
    revoke_employee_portal_link,
    sign_delivery,
    sign_ficha_items_batch,
    sign_ficha_items_by_delivery,
    sign_ficha_period_batch,
    sign_unsigned_deliveries_for_period,
    sign_unsigned_devolutions_for_period,
    upsert_employee_portal_link,
)
from modules.stock.service import resolve_item_size

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
        deliveries = get_portal_employee_deliveries(connection, employee_id)
        fichas = get_portal_employee_fichas(connection, employee_id)
        requests = get_portal_employee_requests(connection, employee_id)
        feedbacks = get_portal_employee_feedbacks(connection, employee_id)
        _epis_rows = get_portal_available_epis(connection, int(employee_user['company_id']))
        _emp_unit_id = int(employee_user.get('unit_id') or 0)
        _emp_unit_jv = get_unit_active_jv_name(connection, _emp_unit_id) if _emp_unit_id else ''
        available_epis = []
        for _epi_row in _epis_rows:
            _epi = row_to_dict(_epi_row)
            if is_epi_visible_for_unit(
                epi_unit_id=_epi.get('unit_id'),
                epi_joint_venture_name=get_epi_effective_jv_name(
                    _epi, lambda uid: get_unit_active_jv_name(connection, uid)
                ),
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
                epi_joint_venture_name=get_epi_effective_jv_name(
                    target_epi, lambda uid: get_unit_active_jv_name(connection, uid)
                ),
                target_unit_id=_fb_unit_id,
                target_unit_joint_venture_name=_fb_unit_jv,
            ):
                raise PermissionError('EPI inválido para avaliação.')
        ratings = {}
        for field in ('comfort_rating', 'quality_rating', 'adequacy_rating', 'performance_rating'):
            raw = int(payload.get(field) or 0)
            ratings[field] = min(5, max(0, raw))
        now = datetime.now(UTC).isoformat()
        feedback_id = create_employee_feedback(
            connection,
            company_id=int(portal['company_id']),
            unit_id=int(get_employee_by_id(connection, int(portal['employee_id']))['unit_id']),
            employee_id=int(portal['employee_id']),
            epi_id=epi_id,
            fb_type=fb_type,
            ratings=ratings,
            comments=payload.get('comments', ''),
            improvement_suggestion=payload.get('improvement_suggestion', ''),
            suggested_new_epi_name=payload.get('suggested_new_epi_name', ''),
            suggested_new_epi_notes=payload.get('suggested_new_epi_notes', ''),
            suggested_new_epi_link=payload.get('suggested_new_epi_link', ''),
            request_token=str(payload.get('token', '')).strip(),
            now=now,
        )
        register_employee_portal_audit(
            connection,
            portal,
            'create_epi_feedback',
            ip_address=ip,
            user_agent=ua,
            payload={'feedback_id': feedback_id}
        )
        connection.commit()
        return send_json(handler, 201, {'ok': True, 'id': feedback_id})


# ── POST /api/employee-sign ───────────────────────────────────────────────────

def handle_post_employee_sign(handler, parsed, payload, match):
    require_fields(payload, ['token', 'delivery_id'])
    token = str(payload.get('token', '')).strip()
    with_name = str(payload.get('signature_name', '')).strip()
    with_data = str(payload.get('signature_data', '')).strip()
    with_comment = str(payload.get('signature_comment', '')).strip()
    if not with_name and not with_data:
        raise ValueError('Informe o nome da assinatura ou desenhe no canvas.')
    ip = str(getattr(handler, 'client_address', ('',))[0] or '')
    ua = handler.headers.get('User-Agent', '')
    with closing(get_connection()) as connection:
        employee_user = resolve_external_employee_context(
            connection, token,
            cpf_last3=payload.get('cpf_last3'),
            ip_address=ip,
            user_agent=ua,
        )
        if not employee_user:
            raise PermissionError('Token de acesso inválido ou expirado.')
        delivery = get_delivery_for_employee(connection, int(payload.get('delivery_id')))
        if not delivery:
            raise ValueError('Entrega não encontrada.')
        if int(delivery['employee_id']) != int(employee_user['employee_id']):
            raise PermissionError('Entrega não pertence ao funcionário informado.')
        name = with_name or employee_user.get('employee_name') or 'Assinado digitalmente'
        now = datetime.now(UTC).isoformat()
        sign_delivery(connection, int(payload.get('delivery_id')), name, with_data, ip, now, with_comment)
        sign_ficha_items_by_delivery(connection, int(payload.get('delivery_id')), name, with_data, ip, now, with_comment)
        register_employee_portal_audit(
            connection, employee_user, 'sign_delivery_item',
            ip_address=ip, user_agent=ua,
            payload={'delivery_id': int(payload.get('delivery_id'))}
        )
        connection.commit()
        return send_json(handler, 200, {'ok': True})


# ── POST /api/employee-lookup ─────────────────────────────────────────────────

def handle_post_employee_lookup(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'employee_qr_code'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'deliveries:create')
        qr_value = str(payload.get('employee_qr_code', '')).strip()
        lookup_token = ''
        if qr_value.startswith('http://') or qr_value.startswith('https://'):
            parsed_link = urlparse(qr_value)
            from urllib.parse import parse_qs as _pqs
            query_values = _pqs(parsed_link.query or '')
            lookup_token = str((query_values.get('employee_token') or query_values.get('token') or [''])[0]).strip()
        elif len(qr_value) > 20 and '-' in qr_value:
            lookup_token = qr_value
        row = lookup_employee_by_qr_or_token(connection, qr_value, lookup_token)
        if not row:
            raise ValueError('Link do funcionário não encontrado.')
        ensure_resource_company(actor, row, 'Colaborador')
        return send_json(handler, 200, {'employee': row_to_dict(row)})


# ── POST /api/employee-portal-link ───────────────────────────────────────────

def handle_post_employee_portal_link(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'employee_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'deliveries:create')
        employee = get_employee_by_id(connection, int(payload['employee_id']))
        if not employee:
            raise ValueError('Colaborador não encontrado.')
        ensure_actor_employee_scope(connection, actor, employee)
        link_data = build_portal_link_from_cpf(
            base_url=request_base_url(handler),
            funcionario_cpf=employee.get('cpf'),
            secret_key=EMPLOYEE_PORTAL_SECRET_KEY
        )
        token = link_data['token']
        access_link = link_data['access_link']
        qr_code_value = access_link
        now = datetime.now(UTC).isoformat()
        expires_at = link_data['expires_at']
        upsert_employee_portal_link(
            connection,
            employee_id=int(employee['id']),
            company_id=int(employee['company_id']),
            token=token,
            qr_code_value=qr_code_value,
            expires_at=expires_at,
            actor_id=int(actor['id']),
            now=now,
        )
        connection.commit()
        structured_log(
            'info', 'employee.access_link.generate',
            employee_id=int(employee['id']),
            company_id=int(employee['company_id']),
            actor_id=int(actor['id']),
            expires_at=str(expires_at or ''),
        )
        return send_json(handler, 200, {'ok': True, 'token': token, 'qr_code_value': qr_code_value, 'access_link': access_link, 'expires_at': expires_at})


# ── POST /api/employee-contact-launch ────────────────────────────────────────

def handle_post_employee_contact_launch(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'employee_id', 'channel'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'deliveries:create')
        employee = get_employee_by_id(connection, int(payload['employee_id']))
        if not employee:
            raise ValueError('Colaborador não encontrado.')
        ensure_actor_employee_scope(connection, actor, employee)
        channel = normalize_preferred_contact_channel(payload.get('channel'))
        access_link = str(payload.get('access_link') or '').strip()
        if not access_link:
            active_link = get_active_portal_link(connection, int(employee['id']))
            active_link_expires_at = parse_iso_datetime_utc(str((active_link or {}).get('expires_at') or ''))
            if active_link and active_link_expires_at and active_link_expires_at > datetime.now(UTC):
                access_link = f"{request_base_url(handler)}/?employee_token={active_link['token']}"
            else:
                link_data = build_portal_link_from_cpf(request_base_url(handler), employee.get('cpf'), EMPLOYEE_PORTAL_SECRET_KEY)
                access_link = link_data['access_link']
        employee_name = str(employee.get('name') or 'Colaborador')
        message = (
            f"Olá {employee_name}! 👷\n"
            f"Seu link rápido da Ficha de EPI (48h):\n{access_link}\n"
            "No portal você consegue: Assinar Ficha, Solicitar EPI e Avaliar EPI."
        )
        if channel == 'whatsapp':
            phone = ''.join(ch for ch in str(employee.get('whatsapp') or '') if ch.isdigit())
            if not phone:
                raise ValueError('Colaborador sem WhatsApp cadastrado.')
            launch_url = f"https://wa.me/{phone}?text={quote(message)}"
        else:
            email = str(employee.get('email') or '').strip().lower()
            if not email:
                raise ValueError('Colaborador sem e-mail cadastrado.')
            subject = quote(f'Acesso rápido - Ficha de EPI - {employee_name}')
            launch_url = f"mailto:{email}?subject={subject}&body={quote(message)}"
        structured_log(
            'info', 'employee.access_link.send',
            employee_id=int(employee['id']),
            company_id=int(employee.get('company_id') or 0),
            actor_id=int(actor['id']),
            channel=channel,
        )
        return send_json(handler, 200, {'ok': True, 'channel': channel, 'message': message, 'launch_url': launch_url, 'access_link': access_link})


# ── POST /api/employee-portal-link/revoke ────────────────────────────────────

def handle_post_employee_portal_link_revoke(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'employee_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'deliveries:create')
        employee = get_employee_by_id(connection, int(payload['employee_id']))
        if not employee:
            raise ValueError('Colaborador não encontrado.')
        ensure_actor_employee_scope(connection, actor, employee)
        revoke_employee_portal_link(connection, int(employee['id']), datetime.now(UTC).isoformat())
        connection.commit()
        return send_json(handler, 200, {'ok': True})


# ── POST /api/employee-sign-batch ─────────────────────────────────────────────

def handle_post_employee_sign_batch(handler, parsed, payload, match):
    require_fields(payload, ['token', 'ficha_period_id'])
    token = str(payload.get('token', '')).strip()
    signature_name = str(payload.get('signature_name', '')).strip()
    signature_data = str(payload.get('signature_data', '')).strip()
    signature_comment = str(payload.get('signature_comment', '')).strip()
    if not signature_name or not signature_data:
        raise ValueError('Assinatura obrigatória.')
    ip = str(getattr(handler, 'client_address', ('',))[0] or '')
    ua = handler.headers.get('User-Agent', '')
    with closing(get_connection()) as connection:
        employee_user = resolve_external_employee_context(
            connection, token,
            cpf_last3=payload.get('cpf_last3'),
            ip_address=ip,
            user_agent=ua,
        )
        if not employee_user:
            raise PermissionError('Token de acesso inválido ou expirado.')
        employee_id = int(employee_user['employee_id'])
        requested_ficha_period_id = int(payload['ficha_period_id'])
        ficha = get_ficha_period_for_signing(connection, requested_ficha_period_id)
        if not ficha or int(ficha['employee_id']) != employee_id:
            raise PermissionError('Ficha não pertence ao funcionário.')
        total_items = count_ficha_period_items(connection, int(ficha['id']))
        structured_log(
            'info', 'employee.sign_batch.start',
            employee_id=employee_id,
            requested_ficha_period_id=requested_ficha_period_id,
            resolved_ficha_period_id=int(ficha['id']),
            selected_period_start=str(ficha['period_start'] or ''),
            selected_period_end=str(ficha['period_end'] or ''),
            total_items=total_items,
        )
        if total_items <= 0:
            raise ValueError('Período sem itens vinculados; não é possível assinar.')
        now = datetime.now(UTC).isoformat()
        client_ip = ip
        if not signature_data:
            raise ValueError('Assinatura em lote inválida: batch_signature_data não pode estar vazio.')
        try:
            period_rowcount = sign_ficha_period_batch(
                connection, int(ficha['id']),
                signature_name or 'Assinado digitalmente', signature_data, client_ip, now, signature_comment
            )
            if period_rowcount != 1:
                connection.rollback()
                raise RuntimeError('Falha ao salvar assinatura em lote no período.')
            items_rowcount = sign_ficha_items_batch(
                connection, int(ficha['id']),
                signature_name or 'Assinado digitalmente', signature_data, client_ip, now, signature_comment
            )
            if items_rowcount <= 0:
                connection.rollback()
                raise RuntimeError('Nenhum item da ficha foi assinado.')
            sign_unsigned_deliveries_for_period(
                connection, int(ficha['id']),
                signature_name or 'Assinado digitalmente', signature_data, client_ip, now, signature_comment
            )
            sign_unsigned_devolutions_for_period(
                connection, int(ficha['id']),
                signature_name or 'Assinado digitalmente', signature_data, client_ip, now, signature_comment
            )
        except Exception:
            connection.rollback()
            raise
        register_employee_portal_audit(
            connection, employee_user, 'sign_batch_period',
            ip_address=client_ip, user_agent=ua,
            payload={'ficha_period_id': int(ficha['id'])}
        )
        refresh_ficha_snapshot_for_period_if_exists(
            connection,
            int(ficha['id']),
            {
                'id': int(employee_user.get('portal_link_id') or 0),
                'role': 'general_admin',
                'company_id': int(employee_user.get('company_id') or 0),
            },
        )
        state = compute_ficha_period_signature_state(connection, int(ficha['id']))
        structured_log(
            'info', 'employee.sign_batch.done',
            employee_id=employee_id,
            ficha_period_id=int(ficha['id']),
            period_rowcount=period_rowcount,
            items_rowcount=items_rowcount,
            items_update_rowcount=items_rowcount,
            affected_items=items_rowcount,
            batch_signature_saved=bool(state['has_batch_signature']),
            total_items=int(state['total_items']),
            signed_items=int(state['signed_items']),
            pending_items=int(state['pending_items']),
            has_batch_signature=bool(state['has_batch_signature']),
            can_close=bool(state['can_close']),
        )
        connection.commit()
        persisted_signature = get_persisted_batch_signature(connection, int(ficha['id']))
        persisted_signature_data = row_to_dict(persisted_signature) if persisted_signature else {}
        persisted_ok = bool(
            str(persisted_signature_data.get('batch_signature_name') or '').strip()
            and str(persisted_signature_data.get('batch_signature_data') or '').strip()
            and str(persisted_signature_data.get('batch_signature_at') or '').strip()
        )
        if not persisted_ok:
            raise RuntimeError('Erro crítico: assinatura em lote não persistiu no período.')
        return send_json(
            handler,
            200,
            {
                'ok': True,
                'period_id': int(ficha['id']),
                'signature_state': {
                    'total_items': int(state['total_items']),
                    'signed_items': int(state['signed_items']),
                    'pending_items': int(state['pending_items']),
                    'has_batch_signature': bool(state['has_batch_signature']),
                    'can_close': bool(state['can_close']),
                },
            },
        )


# ── POST /api/employee-close-period ──────────────────────────────────────────

def handle_post_employee_close_period(handler, parsed, payload, match):
    require_fields(payload, ['token', 'ficha_period_id'])
    ip = str(getattr(handler, 'client_address', ('',))[0] or '')
    ua = handler.headers.get('User-Agent', '')
    with closing(get_connection()) as connection:
        employee_user = resolve_external_employee_context(
            connection,
            str(payload.get('token', '')).strip(),
            cpf_last3=payload.get('cpf_last3'),
            ip_address=ip,
            user_agent=ua,
        )
        if not employee_user:
            raise PermissionError('Token de acesso inválido ou expirado.')
        ficha = get_ficha_period_for_close(connection, int(payload['ficha_period_id']))
        if not ficha or int(ficha['employee_id']) != int(employee_user['employee_id']):
            raise PermissionError('Ficha não pertence ao funcionário.')
        structured_log(
            'info', 'employee.close_period.start',
            employee_id=int(employee_user['employee_id']),
            ficha_period_id=int(ficha['id']),
        )
        state = compute_ficha_period_signature_state(connection, int(ficha['id']))
        structured_log(
            'info', 'employee.close_period.state',
            employee_id=int(employee_user['employee_id']),
            ficha_period_id=int(ficha['id']),
            total_items=int(state['total_items']),
            signed_items=int(state['signed_items']),
            pending_items=int(state['pending_items']),
            has_batch_signature=bool(state['has_batch_signature']),
            can_close=bool(state['can_close']),
        )
        if not state['can_close']:
            missing_requirements = get_ficha_period_close_requirements(state)
            error_message = 'Não é possível fechar o período: requisitos de fechamento não atendidos.'
            if 'pending_items' in missing_requirements or 'signed_items' in missing_requirements:
                error_message = 'Não é possível fechar o período: existem assinaturas pendentes.'
            elif 'batch_signature' in missing_requirements:
                error_message = 'Não é possível fechar o período: assinatura em lote ausente ou incompleta.'
            elif 'total_items' in missing_requirements:
                error_message = 'Não é possível fechar o período: não há itens no período.'
            structured_log(
                'warning', 'employee.close_period.denied',
                employee_id=int(employee_user['employee_id']),
                ficha_period_id=int(ficha['id']),
                total_items=int(state['total_items']),
                signed_items=int(state['signed_items']),
                pending_items=int(state['pending_items']),
                has_batch_signature=bool(state['has_batch_signature']),
                can_close=False,
                missing_requirements=missing_requirements,
            )
            return send_json(
                handler,
                400,
                {
                    'ok': False,
                    'error': error_message,
                    'total_items': int(state['total_items']),
                    'signed_items': int(state['signed_items']),
                    'pending_items': int(state['pending_items']),
                    'has_batch_signature': bool(state['has_batch_signature']),
                    'can_close': False,
                    'missing_requirements': missing_requirements,
                }
            )
        assert_ficha_period_can_close(connection, int(ficha['id']))
        now = datetime.now(UTC).isoformat()
        close_ficha_period(connection, int(ficha['id']), now)
        refresh_ficha_snapshot_for_period_if_exists(
            connection,
            int(ficha['id']),
            {
                'id': int(employee_user.get('portal_link_id') or 0),
                'role': 'general_admin',
                'company_id': int(employee_user.get('company_id') or 0),
            },
        )
        register_employee_portal_audit(
            connection, employee_user, 'close_period',
            ip_address=ip, user_agent=ua,
            payload={'ficha_period_id': int(ficha['id'])}
        )
        structured_log(
            'info', 'employee.close_period.closed',
            employee_id=int(employee_user['employee_id']),
            ficha_period_id=int(ficha['id']),
            total_items=int(state['total_items']),
            signed_items=int(state['signed_items']),
            pending_items=int(state['pending_items']),
            has_batch_signature=bool(state['has_batch_signature']),
            can_close=True,
        )
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'status': 'closed', 'ficha_period_id': int(ficha['id'])})


# ── POST /api/requests (portal EPI request creation) ─────────────────────────

def handle_post_portal_requests(handler, parsed, payload, match):
    require_fields(payload, ['token', 'epi_id', 'quantity'])
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
            raise PermissionError('Link de solicitação inválido.')
        employee = get_employee_by_id(connection, int(portal['employee_id']))
        if not employee:
            raise ValueError('Colaborador não encontrado.')
        target_epi = get_epi_by_id(connection, int(payload['epi_id']))
        if not target_epi:
            raise ValueError('EPI não encontrado.')
        if int(target_epi['company_id']) != int(portal['company_id']):
            raise PermissionError('EPI fora do escopo da empresa do colaborador.')
        resolved_size = resolve_item_size(
            payload.get('glove_size'),
            payload.get('size'),
            payload.get('uniform_size'),
        )
        if not resolved_size['selected_size']:
            raise ValueError('Tamanho é obrigatório na solicitação de EPI.')
        glove_size = resolved_size['glove_size']
        size = resolved_size['size']
        uniform_size = resolved_size['uniform_size']
        now = datetime.now(UTC).isoformat()
        request_id = create_portal_epi_request(
            connection,
            company_id=int(portal['company_id']),
            unit_id=int(employee['unit_id']),
            employee_id=int(portal['employee_id']),
            epi_id=int(payload['epi_id']),
            quantity=int(payload.get('quantity') or 1),
            glove_size=glove_size,
            size=size,
            uniform_size=uniform_size,
            request_token=str(payload.get('token', '')).strip(),
            justification=str(payload.get('justification', '')).strip(),
            now=now,
        )
        register_employee_portal_audit(
            connection, portal, 'create_epi_request',
            ip_address=ip, user_agent=ua,
            payload={'request_id': request_id, 'epi_id': int(payload['epi_id'])}
        )
        connection.commit()
        return send_json(handler, 201, {'ok': True, 'id': request_id})


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    router.register('GET',  '/api/employee-access',             handle_get_employee_access)
    router.register('GET',  '/api/employee-access/pdf',         handle_get_employee_access_pdf)
    router.register('POST', '/api/employee-feedback',           handle_post_employee_feedback)
    router.register('POST', '/api/employee-sign',               handle_post_employee_sign)
    router.register('POST', '/api/employee-lookup',             handle_post_employee_lookup)
    router.register('POST', '/api/employee-portal-link/revoke', handle_post_employee_portal_link_revoke)
    router.register('POST', '/api/employee-portal-link',        handle_post_employee_portal_link)
    router.register('POST', '/api/employee-contact-launch',     handle_post_employee_contact_launch)
    router.register('POST', '/api/employee-sign-batch',         handle_post_employee_sign_batch)
    router.register('POST', '/api/employee-close-period',       handle_post_employee_close_period)
    router.register('POST', '/api/requests',                    handle_post_portal_requests)
