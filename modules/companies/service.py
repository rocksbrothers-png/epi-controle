import json
from datetime import date, datetime

from epi_backend.db import row_to_dict
from modules.commercial.service import count_company_users


def get_company_by_id(connection, company_id):
    row = connection.execute(
        'SELECT id, name, user_limit, license_status, active, contract_end, addendum_enabled '
        'FROM companies WHERE id = ?',
        (company_id,),
    ).fetchone()
    return row_to_dict(row) if row else None


def evaluate_company_block_status(connection, company_id, persist_expiration=True):
    company = get_company_by_id(connection, company_id)
    if not company:
        raise ValueError('Empresa vinculada não encontrada.')
    reasons = []
    today_iso = date.today().isoformat()
    contract_end = str(company.get('contract_end') or '').strip()
    license_status = str(company.get('license_status') or 'active').strip() or 'active'
    if contract_end and contract_end < today_iso:
        reasons.append('license_expired_by_contract')
        if persist_expiration and license_status != 'expired':
            connection.execute(
                'UPDATE companies SET license_status = ? WHERE id = ?', ('expired', company_id)
            )
            connection.commit()
            license_status = 'expired'
    if int(company.get('active') or 0) != 1:
        reasons.append('company_inactive')
    if license_status == 'suspended':
        reasons.append('license_suspended')
    if license_status == 'expired':
        reasons.append('license_expired_by_contract')
    active_users = count_company_users(connection, company_id)
    user_limit = int(company.get('user_limit') or 0)
    addendum_enabled = int(company.get('addendum_enabled') or 0) == 1
    if user_limit > 0 and active_users > user_limit and not addendum_enabled:
        reasons.append('usage_exceeds_contract')
    dedup_reasons = []
    for reason in reasons:
        if reason not in dedup_reasons:
            dedup_reasons.append(reason)
    return {
        'company_id': int(company_id),
        'blocked': bool(dedup_reasons),
        'reasons': dedup_reasons,
        'license_status': license_status,
        'active_users': active_users,
        'user_limit': user_limit,
        'addendum_enabled': addendum_enabled,
        'contract_end': contract_end,
    }


def enforce_company_block_rules(connection, company_id):
    status = evaluate_company_block_status(connection, company_id, persist_expiration=True)
    if not status['blocked']:
        return
    reason_priority = status['reasons'][0]
    if reason_priority == 'company_inactive':
        raise PermissionError('Acesso bloqueado: empresa inativa.')
    if reason_priority in ('license_suspended', 'license_expired_by_contract'):
        raise PermissionError('Acesso bloqueado: licença suspensa ou expirada.')
    if reason_priority == 'usage_exceeds_contract':
        raise PermissionError('Acesso bloqueado: uso acima do limite contratado.')
    raise PermissionError('Acesso bloqueado por política comercial.')


def ensure_company_user_limit(connection, company_id, ignore_user_id=None):
    company = get_company_by_id(connection, company_id)
    if not company:
        return
    user_limit = int(company.get('user_limit') or 0)
    addendum_enabled = int(company.get('addendum_enabled') or 0) == 1
    if user_limit <= 0 or addendum_enabled:
        return
    active_users = count_company_users(connection, company_id)
    if ignore_user_id:
        row = connection.execute(
            "SELECT active FROM users WHERE id = ?", (int(ignore_user_id),)
        ).fetchone()
        if row and int(row['active'] or 0) == 1:
            active_users = max(0, active_users - 1)
    if active_users >= user_limit:
        raise PermissionError(
            f'Limite de {user_limit} usuário(s) atingido para esta empresa.'
        )


def fetch_companies(connection, company_id=None):
    sql = (
        'SELECT id, name, legal_name, cnpj, active, logo_type, plan_name, user_limit, '
        'license_status, contract_start, contract_end, monthly_value, addendum_enabled, '
        'commercial_notes '
        'FROM companies'
    )
    if company_id:
        rows = connection.execute(sql + ' WHERE id = ?', (company_id,)).fetchall()
    else:
        rows = connection.execute(sql + ' ORDER BY name').fetchall()
    return [row_to_dict(row) for row in rows]


def company_action_label(action_type):
    return {
        'create': 'Criação',
        'update': 'Atualização',
        'suspend': 'Suspensão',
        'reactivate': 'Reativação',
    }.get(action_type, action_type)


def summarize_company_changes(previous, payload):
    tracked_fields = {
        'plan_name': 'Plano',
        'user_limit': 'Limite de usuários',
        'license_status': 'Status da licença',
        'active': 'Status da empresa',
        'contract_start': 'Início do contrato',
        'contract_end': 'Fim do contrato',
        'monthly_value': 'Valor mensal atual',
        'addendum_enabled': 'Aditivo contratual',
        'commercial_notes': 'Observrazão',
    }
    if not previous:
        details = [
            {'field': tracked_fields[field], 'before': '', 'after': str(payload.get(field, ''))}
            for field in tracked_fields
        ]
        return (
            f"Empresa criada com plano {payload['plan_name']} e limite de {payload['user_limit']} usuários.",
            details,
        )
    changes = []
    details = []
    for field, label in tracked_fields.items():
        previous_value = str(previous.get(field, ''))
        current_value = str(payload.get(field, ''))
        if previous_value != current_value:
            changes.append(label.lower())
            details.append({'field': label, 'before': previous_value, 'after': current_value})
    summary = (
        'Alteração em ' + ', '.join(changes) + '.'
        if changes
        else 'Dados comerciais revisados sem mudança crítica.'
    )
    return summary, details


def register_company_audit(connection, company_id, actor, action_type, summary, details=None):
    connection.execute(
        'INSERT INTO company_audit_logs '
        '(company_id, actor_user_id, actor_name, action_type, summary, details_json, created_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?)',
        (
            company_id,
            actor['id'],
            actor['full_name'],
            action_type,
            summary,
            json.dumps(details or [], ensure_ascii=False),
            datetime.now().isoformat(timespec='seconds'),
        ),
    )


def validate_company_payload(
    connection,
    payload,
    company_id=None,
    *,
    get_commercial_settings,
    validate_cnpj,
    ensure_unique_company_cnpj,
    validate_logo_payload,
    normalize_plan_key,
    count_company_users,
):
    settings = get_commercial_settings(connection)
    payload['name'] = str(payload.get('name', '')).strip()
    payload['legal_name'] = str(payload.get('legal_name', '')).strip()
    payload['cnpj'] = validate_cnpj(payload.get('cnpj', ''))
    ensure_unique_company_cnpj(connection, payload['cnpj'], company_id)
    payload['logo_type'] = validate_logo_payload(payload.get('logo_type', ''))
    payload['plan_name'] = normalize_plan_key(payload.get('plan_name') or 'start')
    if payload['plan_name'] not in settings['plans']:
        raise ValueError('Plano comercial invalido.')
    payload['commercial_notes'] = str(payload.get('commercial_notes', '')).strip()
    payload['user_limit'] = int(payload.get('user_limit', 0))
    if payload['user_limit'] < 1:
        raise ValueError('O limite de usuarios deve ser maior que zero.')
    payload['addendum_enabled'] = (
        1
        if str(payload.get('addendum_enabled', '0')).lower() in ('1', 'true', 'on', 'yes')
        else 0
    )
    plan = settings['plans'][payload['plan_name']]
    if payload['user_limit'] < plan['min_users']:
        raise ValueError(
            f"O plano {plan['label']} exige no minimo {plan['min_users']} usuario(s)."
        )
    if plan['max_users'] is not None and payload['user_limit'] > plan['max_users'] and not payload['addendum_enabled']:
        raise ValueError(
            f"O plano {plan['label']} permite ate {plan['max_users']} usuarios sem aditivo contratual."
        )
    active_users = count_company_users(connection, company_id) if company_id else 0
    if active_users > payload['user_limit']:
        raise ValueError(
            'O limite contratado nao pode ficar abaixo da quantidade atual de usuarios ativos.'
        )
    payload['monthly_value'] = round(active_users * float(settings['unit_price']), 2)
    payload['contract_start'] = str(payload.get('contract_start', '')).strip()
    payload['contract_end'] = str(payload.get('contract_end', '')).strip()
    if payload['contract_start']:
        datetime.strptime(payload['contract_start'], '%Y-%m-%d')
    if payload['contract_end']:
        datetime.strptime(payload['contract_end'], '%Y-%m-%d')
    if (
        payload['contract_start']
        and payload['contract_end']
        and payload['contract_end'] < payload['contract_start']
    ):
        raise ValueError('A data final do contrato deve ser maior ou igual a data inicial.')
    payload['license_status'] = str(payload.get('license_status', 'active')).strip() or 'active'
    payload['unit_price'] = float(settings['unit_price'])
    payload['projected_monthly_value'] = round(payload['user_limit'] * payload['unit_price'], 2)
    return payload


def fetch_company_audit_logs(connection, actor=None):
    sql = (
        'SELECT company_audit_logs.*, companies.name AS company_name '
        'FROM company_audit_logs '
        'JOIN companies ON companies.id = company_audit_logs.company_id'
    )
    if actor and actor['role'] != 'master_admin':
        rows = connection.execute(
            sql + ' WHERE company_audit_logs.company_id = ? ORDER BY company_audit_logs.created_at DESC',
            (actor['company_id'],),
        ).fetchall()
    else:
        rows = connection.execute(
            sql + ' ORDER BY company_audit_logs.created_at DESC'
        ).fetchall()
    return [row_to_dict(row) for row in rows]
