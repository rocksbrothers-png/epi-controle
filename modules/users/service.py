"""Serviços de gestão de usuários sem DI."""

import secrets as _secrets
from datetime import datetime, timedelta

from core.auth import ensure_company_access, ensure_resource_company
from core.repository import authorize_action, get_employee_by_id, get_user_by_id
from core.roles import (
    BILLABLE_ROLES,
    CERTIFICATION_READONLY_ROLE,
    ROLE_WEIGHT,
    normalize_role_name,
)
from core.security import hash_password, is_bcrypt_hash
from epi_backend.config import UTC
from epi_backend.http_utils import require_fields
from modules.companies.service import ensure_company_user_limit

# Senha provisionada por administrador (definida ou gerada) é temporária: o
# usuário deve trocá-la no 1º acesso e ela expira após esta janela.
TEMP_PASSWORD_TTL_DAYS = 7


def temp_password_expiry_iso(now=None):
    base = now or datetime.now(UTC)
    return (base + timedelta(days=TEMP_PASSWORD_TTL_DAYS)).isoformat()


def mark_temp_password(connection, user_id, expires_at):
    """Marca a senha como temporária (troca obrigatória + expiração).

    Tolerante a bases pré-migração (colunas ausentes): a falha é silenciosa e
    apenas desliga a política para aquele registro, sem quebrar a criação.
    """
    try:
        connection.execute(
            'UPDATE users SET must_change_password = 1, password_expires_at = ? WHERE id = ?',
            (str(expires_at or ''), int(user_id)),
        )
    except Exception:
        try:
            connection.rollback()
        except Exception:
            # Se o próprio rollback falha, a conexão já está inutilizável e não
            # há o que desfazer. Levantar aqui trocaria a falha original — a
            # coluna ausente, que é informativa — por uma secundária que não
            # diz nada. A criação do usuário segue: sem a política, não sem o
            # usuário.
            pass


SQL_UPDATE_USER = (
    "UPDATE users SET "
    "username = ?, password = ?, full_name = ?, role = ?, company_id = ?, active = ?, "
    "linked_employee_id = ? "
    "WHERE id = ?"
)


def authorize_user_management(connection, actor_user_id, operation='create', target_role=None, target_user_id=None, target_company_id=None):
    action = {'create': 'users:create', 'update': 'users:update', 'delete': 'users:delete'}[operation]
    actor = authorize_action(connection, actor_user_id, action)
    target_role = normalize_role_name(target_role)
    target = get_user_by_id(connection, target_user_id) if target_user_id else None

    if target_user_id and not target:
        raise ValueError('Usuário alvo não encontrado.')

    if actor['role'] == 'master_admin':
        if target_role == 'master_admin' and target_user_id is None:
            raise ValueError('Não é permitido criar outro Administrador Master por esta tela.')
        if target and target['role'] == 'master_admin':
            if target['id'] == actor['id']:
                if operation == 'delete':
                    raise ValueError('Não é permitido excluir o próprio usuário logado.')
                if target_role and ROLE_WEIGHT.get(target_role, 0) < ROLE_WEIGHT['master_admin']:
                    raise ValueError('Administrador Master não pode remover a própria administração.')
            else:
                raise ValueError('Administrador Master só pode ser gerenciado pelo bootstrap inicial do sistema.')
        return actor

    if actor['role'] in ('general_admin', 'registry_admin'):
        if target_role and target_role not in ('registry_admin', 'admin', 'user', 'employee', 'buyer', 'approver'):
            raise ValueError('Perfil pode gerenciar apenas Administrador de Registro, Administrador Local, Comprador, Aprovador, Gestor de EPI e Funcionário da própria empresa.')
        if target:
            if target['role'] not in ('registry_admin', 'admin', 'user', 'employee', 'buyer', 'approver'):
                raise ValueError('Perfil pode alterar apenas Administrador de Registro, Administrador Local, Comprador, Aprovador, Gestor de EPI e Funcionário.')
            ensure_company_access(actor, target.get('company_id'))
        if target_company_id:
            ensure_company_access(actor, target_company_id)
        return actor

    if actor['role'] == 'admin':
        raise PermissionError('Administrador Local não pode cadastrar/editar usuários da base principal.')

    raise PermissionError('Somente perfis administrativos podem gerenciar usuários.')


def resolve_target_company_id(actor, payload_company_id, payload_role, linked_employee_id=None):
    role = normalize_role_name(payload_role)
    company_id = payload_company_id
    if actor['role'] in ('general_admin', 'registry_admin', 'admin') and not company_id:
        company_id = actor.get('company_id')
    has_linked_employee = linked_employee_id not in (None, '', 'null')
    if role in BILLABLE_ROLES and not company_id and not has_linked_employee:
        raise ValueError('Perfil com empresa exige uma empresa vinculada.')
    if role == CERTIFICATION_READONLY_ROLE:
        # A identidade de certificação (#313) fica FORA de `BILLABLE_ROLES` —
        # é automação, não assento de pessoa. O efeito colateral é que a
        # exigência acima deixa de valer justamente para o único papel que não
        # pode existir sem tenant: sem `company_id` o escopo enumerado sai
        # vazio e o isolamento passaria a depender de ninguém olhar. Por isso a
        # regra é reafirmada aqui, explícita, e não herdada de uma lista de
        # cobrança que pode mudar por motivo comercial.
        if has_linked_employee:
            raise ValueError(
                'A identidade de certificação não pode ser vinculada a um colaborador.'
            )
        if not company_id:
            raise ValueError('A identidade de certificação exige empresa vinculada.')
    return int(company_id) if company_id not in (None, '', 'null') else None


def ensure_operational_role_link(connection, role, linked_employee_id, company_id):
    if role not in ('admin', 'user'):
        return
    if linked_employee_id in (None, '', 'null'):
        raise ValueError('Administrador Local e Gestor de EPI devem estar vinculados a um colaborador com unidade.')
    employee = get_employee_by_id(connection, int(linked_employee_id))
    if not employee:
        raise ValueError('Colaborador vinculado não encontrado para o perfil operacional.')
    if company_id and str(employee.get('company_id')) != str(company_id):
        raise ValueError('Colaborador vinculado precisa pertencer à mesma empresa do usuário.')
    if not employee.get('unit_id'):
        raise ValueError('Colaborador vinculado precisa possuir unidade principal definida.')


def resolve_user_employee_link(connection, actor, payload, company_id, allow_manual_create=False):
    if normalize_role_name(payload.get('role', '')) == CERTIFICATION_READONLY_ROLE:
        # Identidade técnica da certificação (#313): não é pessoa, não tem
        # colaborador, e não pode disparar a criação de um.
        #
        # Sem esta saída o papel é INALCANÇÁVEL pela API de usuários, e as duas
        # portas se fecham uma contra a outra: com `linked_employee_id`,
        # `resolve_target_company_id` recusa o vínculo; sem ele, o ramo de
        # criação manual abaixo exige os seis campos `employee_*` e criaria um
        # colaborador — exatamente o dado fictício em produção que o contrato
        # da #313 proíbe.
        #
        # Alcance medido, não suposto: este arquivo diverge entre os dois
        # repositórios. No `epi-controle-app`, `_resolve_optional_employee_link`
        # já dispensa colaborador para perfis administrativos, então lá esta
        # saída cobre só o caso em que campos `employee_*` chegam junto com a
        # identidade técnica. Ou seja, ela NÃO explica a conta do SaaS ter
        # nascido `registry_admin` — naquele código o papel já era criável.
        #
        # Mesmo formato de `ensure_operational_role_link`, que também sai cedo
        # para papéis que não são operacionais. `company_id` segue obrigatório —
        # quem o exige é `resolve_target_company_id`, e este retorno o preserva.
        return None, company_id

    linked_employee_id = payload.get('linked_employee_id')
    if linked_employee_id not in (None, '', 'null'):
        employee = get_employee_by_id(connection, int(linked_employee_id))
        if not employee:
            raise ValueError('Colaborador vinculado não encontrado.')
        ensure_company_access(actor, employee['company_id'])
        return int(employee['id']), int(employee['company_id'])

    if not allow_manual_create:
        raise ValueError('Selecione um colaborador em "Vincular colaborador".')

    employee_id_code = str(payload.get('employee_id_code', '')).strip()
    employee_role_name = str(payload.get('employee_role_name', '')).strip()
    employee_sector = str(payload.get('employee_sector', '')).strip()
    employee_schedule_type = str(payload.get('employee_schedule_type', '')).strip()
    employee_admission_date = str(payload.get('employee_admission_date', '')).strip()
    employee_unit_id = str(payload.get('employee_unit_id', '')).strip()
    employee_name = str(payload.get('employee_name') or payload.get('full_name') or '').strip()

    require_fields(
        {
            'employee_id_code': employee_id_code,
            'employee_role_name': employee_role_name,
            'employee_sector': employee_sector,
            'employee_schedule_type': employee_schedule_type,
            'employee_admission_date': employee_admission_date,
            'employee_name': employee_name
        },
        ['employee_id_code', 'employee_role_name', 'employee_sector', 'employee_schedule_type', 'employee_admission_date', 'employee_name']
    )

    datetime.strptime(employee_admission_date, '%Y-%m-%d')
    if not company_id:
        raise ValueError('Empresa obrigatória para criar colaborador Sem vínculo.')

    ensure_company_access(actor, company_id)

    from core.repository import get_unit_by_id
    if employee_unit_id:
        unit = get_unit_by_id(connection, int(employee_unit_id))
        ensure_resource_company(actor, unit, 'Unidade')
        if int(unit['company_id']) != int(company_id):
            raise ValueError('A unidade selecionada precisa pertencer à empresa do usuário.')
        unit_id = int(unit['id'])
    else:
        default_unit = connection.execute('SELECT id FROM units WHERE company_id = ? ORDER BY id LIMIT 1', (company_id,)).fetchone()
        if not default_unit:
            raise ValueError('Empresa sem unidade cadastrada para criar colaborador.')
        unit_id = int(default_unit['id'])

    # Escopo por tenant, igual a ensure_employee_identity_unique e ao índice de
    # upsert da importação. Sem o company_id este caminho recusava matrícula que
    # o banco aceita — e a recusa revelava a existência de um colaborador de
    # OUTRO tenant (issue #168).
    existing_code = connection.execute(
        'SELECT id FROM employees WHERE company_id = ? AND employee_id_code = ?',
        (int(company_id), employee_id_code),
    ).fetchone()
    if existing_code:
        raise ValueError('ID do colaborador já cadastrado nesta empresa.')

    cursor = connection.execute(
        '''
        INSERT INTO employees (company_id, unit_id, employee_id_code, name, sector, role_name, admission_date, schedule_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            int(company_id),
            unit_id,
            employee_id_code,
            employee_name,
            employee_sector,
            employee_role_name,
            employee_admission_date,
            employee_schedule_type
        )
    )
    return int(cursor.lastrowid), int(company_id)


def create_user(connection, payload):
    from core.security import resolve_actor_user_id as _resolve
    actor_user_id = int(str(payload.get('actor_user_id', '')).strip())
    actor = authorize_user_management(connection, actor_user_id, 'create', payload.get('role'), None, payload.get('company_id'))

    role = normalize_role_name(payload.get('role', ''))
    if role not in ROLE_WEIGHT:
        raise ValueError('Perfil de usuário inválido.')
    if role == 'employee' and actor['role'] not in ('master_admin', 'general_admin', 'registry_admin'):
        raise PermissionError('Somente Master, Geral e Registro podem criar perfil Funcionário.')

    raw_password = str(payload.get('password') or '').strip()
    password = hash_password(raw_password if raw_password else _secrets.token_urlsafe(16))
    company_id = resolve_target_company_id(actor, payload.get('company_id'), role, payload.get('linked_employee_id'))
    allow_manual_link = actor['role'] in ('master_admin', 'general_admin')
    linked_employee_id, company_id = resolve_user_employee_link(
        connection, actor, payload, company_id,
        allow_manual_create=allow_manual_link and str(payload.get('linked_employee_id', '')).strip() == ''
    )
    ensure_operational_role_link(connection, role, linked_employee_id, company_id)
    if company_id and int(payload.get('active', 1)) == 1:
        ensure_company_user_limit(connection, company_id)

    cursor = connection.execute(
        'INSERT INTO users (username, password, full_name, role, company_id, active, linked_employee_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (str(payload.get('username', '')).strip(), password, str(payload.get('full_name', '')).strip(), role, company_id, int(payload.get('active', 1) or 1), linked_employee_id)
    )
    # Toda senha provisionada por admin (definida OU gerada) é temporária:
    # exige troca no 1º acesso e expira. Só novos usuários são afetados.
    new_user_id = int(cursor.lastrowid)
    mark_temp_password(connection, new_user_id, temp_password_expiry_iso())
    connection.commit()


def update_user(connection, user_id, payload):
    actor = authorize_user_management(connection, int(str(payload.get('actor_user_id', '')).strip()), 'update', payload.get('role'), user_id, payload.get('company_id'))
    current = get_user_by_id(connection, user_id)
    if not current:
        raise ValueError('Usuário não encontrado.')
    incoming_password = str(payload.get('password') or '').strip()
    if incoming_password:
        password = hash_password(incoming_password)
    elif is_bcrypt_hash(current['password']):
        password = current['password']
    else:
        password = hash_password(current['password'])
    role = normalize_role_name(payload.get('role', ''))
    if role not in ROLE_WEIGHT:
        raise ValueError('Perfil de usuário inválido.')
    if role == 'employee' and actor['role'] not in ('master_admin', 'general_admin', 'registry_admin'):
        raise PermissionError('Somente Master, Geral e Registro podem criar perfil Funcionário.')
    allow_manual_link = actor['role'] in ('master_admin', 'general_admin')
    linked_value = payload.get('linked_employee_id', current.get('linked_employee_id'))
    company_id = resolve_target_company_id(actor, payload.get('company_id'), role, linked_value)
    payload_for_link = {**payload, 'linked_employee_id': linked_value}
    linked_employee_id, company_id = resolve_user_employee_link(connection, actor, payload_for_link, company_id,
        allow_manual_create=allow_manual_link and str(linked_value or '').strip() == '')
    ensure_operational_role_link(connection, role, linked_employee_id, company_id)
    if company_id and int(payload.get('active', 1)) == 1:
        ensure_company_user_limit(connection, int(company_id), ignore_user_id=user_id)
    connection.execute(SQL_UPDATE_USER, (str(payload.get('username', '')).strip(), password, str(payload.get('full_name', '')).strip(), role, company_id, int(payload.get('active', 1)), linked_employee_id, user_id))
    # Reset de senha por admin também gera credencial temporária (troca no
    # próximo acesso + expiração). Sem nova senha, a política fica intacta.
    if incoming_password:
        mark_temp_password(connection, user_id, temp_password_expiry_iso())
    connection.commit()


def delete_user(connection, user_id, actor_user_id):
    authorize_user_management(connection, actor_user_id, 'delete', None, user_id, None)
    if actor_user_id == user_id:
        raise ValueError('Não é permitido excluir o próprio usuário logado.')
    connection.execute('DELETE FROM users WHERE id = ?', (user_id,))
    connection.commit()
