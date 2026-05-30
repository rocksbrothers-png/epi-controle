"""Repositório central: funções de DB e autorização compartilhadas entre módulos."""

from datetime import date

from core.auth import ensure_company_access, ensure_permission
from core.roles import normalize_role_name
from epi_backend.db import row_to_dict

# ── Contagem de usuários ──────────────────────────────────────────────────────

_BILLABLE_ROLES = (
    'general_admin',
    'registry_admin',
    'manager',
    'safety_tech',
    'buyer',
    'approver',
    'admin',
    'user',
)


def count_company_users(connection, company_id):
    placeholders = ','.join(['%s'] * len(_BILLABLE_ROLES))
    return connection.execute(
        f"SELECT COUNT(*) FROM users WHERE company_id = %s AND active = 1 AND role IN ({placeholders})",
        (company_id, *_BILLABLE_ROLES),
    ).fetchone()[0]


# ── Lookups simples ───────────────────────────────────────────────────────────

def get_company_by_id(connection, company_id):
    row = connection.execute(
        'SELECT id, name, user_limit, license_status, active, contract_end, addendum_enabled '
        'FROM companies WHERE id = %s',
        (company_id,),
    ).fetchone()
    return row_to_dict(row) if row else None


def get_employee_by_id(connection, employee_id):
    row = connection.execute(
        'SELECT id, company_id, unit_id, employee_id_code, cpf, name, email, whatsapp, '
        'preferred_contact_channel, sector, role_name, admission_date, schedule_type, '
        'tipo_vinculo, empresa_origem FROM employees WHERE id = %s',
        (int(employee_id),),
    ).fetchone()
    return row_to_dict(row) if row else None


def get_unit_by_id(connection, unit_id):
    row = connection.execute(
        'SELECT id, company_id, name, unit_type, city, notes FROM units WHERE id = %s',
        (int(unit_id),),
    ).fetchone()
    return row_to_dict(row) if row else None


def get_epi_by_id(connection, epi_id):
    row = connection.execute(
        'SELECT id, company_id, unit_id, name, purchase_code, ca, active FROM epis WHERE id = %s',
        (int(epi_id),),
    ).fetchone()
    return row_to_dict(row) if row else None


def get_unit_active_jv_name(connection, unit_id):
    if not unit_id:
        return ''
    row = connection.execute(
        'SELECT joint_venture_name FROM unit_joint_venture_periods '
        'WHERE unit_id = %s AND ended_at IS NULL '
        'ORDER BY started_at DESC LIMIT 1',
        (int(unit_id),),
    ).fetchone()
    if not row:
        return ''
    return str(dict(row).get('joint_venture_name') or '').strip()


# ── Unidade operacional do ator ───────────────────────────────────────────────

def get_employee_current_unit(connection, employee_id):
    employee = get_employee_by_id(connection, int(employee_id))
    if not employee:
        return None
    today_iso = date.today().isoformat()
    movement = connection.execute(
        '''
        SELECT target_unit_id
        FROM employee_unit_movements
        WHERE employee_id = %s
          AND movement_type = 'temporary'
          AND start_date <= %s
          AND COALESCE(NULLIF(end_date, ''), '9999-12-31') >= %s
        ORDER BY start_date DESC, id DESC
        LIMIT 1
        ''',
        (int(employee_id), today_iso, today_iso),
    ).fetchone()
    return int(movement['target_unit_id']) if movement else int(employee['unit_id'])


def actor_operational_unit_id(connection, actor):
    if not actor or actor.get('role') not in ('admin', 'user'):
        return None
    linked_employee_id = actor.get('linked_employee_id')
    if not linked_employee_id:
        return None
    return get_employee_current_unit(connection, int(linked_employee_id))


# ── Bloqueio comercial ────────────────────────────────────────────────────────

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
                'UPDATE companies SET license_status = %s WHERE id = %s',
                ('expired', company_id),
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

    dedup = []
    for r in reasons:
        if r not in dedup:
            dedup.append(r)

    return {
        'company_id': int(company_id),
        'blocked': bool(dedup),
        'reasons': dedup,
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
    reason = status['reasons'][0]
    if reason == 'company_inactive':
        raise PermissionError('Acesso bloqueado: empresa inativa.')
    if reason in ('license_suspended', 'license_expired_by_contract'):
        raise PermissionError('Acesso bloqueado: licença suspensa ou expirada.')
    if reason == 'usage_exceeds_contract':
        raise PermissionError('Acesso bloqueado: uso acima do limite contratado.')
    raise PermissionError('Acesso bloqueado por política comercial.')


# ── Usuários e autorização ────────────────────────────────────────────────────

def get_user_by_id(connection, user_id):
    row = connection.execute(
        'SELECT users.id, users.username, users.password, users.full_name, users.role, '
        'users.company_id, users.active, users.linked_employee_id, '
        'users.employee_access_token, users.employee_access_expires_at, '
        'companies.name AS company_name, companies.cnpj AS company_cnpj, '
        'companies.logo_type '
        'FROM users LEFT JOIN companies ON companies.id = users.company_id '
        'WHERE users.id = %s',
        (user_id,),
    ).fetchone()
    if not row:
        return None
    item = row_to_dict(row)
    item['role'] = normalize_role_name(item.get('role'))
    operational_unit_id = actor_operational_unit_id(connection, item)
    if operational_unit_id:
        item['operational_unit_id'] = operational_unit_id
    return item


def require_actor(connection, actor_user_id):
    actor = get_user_by_id(connection, int(actor_user_id))
    if not actor or not int(actor['active']):
        raise PermissionError('Usuário executor inválido.')
    actor['role'] = normalize_role_name(actor.get('role'))
    if actor.get('role') != 'master_admin' and actor.get('company_id'):
        enforce_company_block_rules(connection, int(actor['company_id']))
    return actor


def authorize_action(connection, actor_user_id, action, company_id=None):
    actor = require_actor(connection, actor_user_id)
    ensure_permission(actor, action)
    if company_id is not None:
        ensure_company_access(actor, company_id)
    return actor
