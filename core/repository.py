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
        f'tipo_vinculo, empresa_origem{_employee_legal_entity_column(connection)}'
        f'{_employee_outsourced_columns(connection)} FROM employees WHERE id = %s',
        (int(employee_id),),
    ).fetchone()
    return row_to_dict(row) if row else None


def _employee_legal_entity_column(connection) -> str:
    """`, legal_entity_id` quando a coluna Multi-CNPJ existir; vazio caso
    contrário (janela de migração / schema parcial)."""
    from epi_backend.db import table_columns
    return ', legal_entity_id' if 'legal_entity_id' in table_columns(connection, 'employees') else ''


def _employee_outsourced_columns(connection) -> str:
    """Colunas do vínculo com empresa terceirizada/prestadora (ADR-0002)
    quando o schema já está provisionado; vazio caso contrário (janela de
    migração / schema parcial), preservando retrocompatibilidade."""
    from epi_backend.db import table_columns
    if 'outsourced_company_id' not in table_columns(connection, 'employees'):
        return ''
    return (
        ', outsourced_company_id, service_contract_id, epi_responsibility_override, '
        'epi_responsibility_override_reason'
    )


def get_unit_by_id(connection, unit_id):
    row = connection.execute(
        'SELECT id, company_id, name, unit_type, city, notes FROM units WHERE id = %s',
        (int(unit_id),),
    ).fetchone()
    return row_to_dict(row) if row else None


def get_epi_by_id(connection, epi_id):
    row = connection.execute(
        'SELECT id, company_id, unit_id, name, purchase_code, ca, active, '
        'unit_measure, glove_size, size, uniform_size, active_joinventure, scope_type '
        'FROM epis WHERE id = %s',
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
    """Unidade operacional atual do ator (Administrador Local/Gestor de EPI
    têm vínculo único com UMA unidade — nunca uma carteira; ver
    docs/PAPEIS_E_ATRIBUICOES.md). Vive aqui (não em
    modules.employees.service) para que módulos de domínio (legal_entities,
    units, employees) possam resolver o escopo do ator sem importar uns aos
    outros — a causa raiz do ciclo de import fechado por
    modules.legal_entities.service -> modules.employees.service (issue #148).

    Consulta direto com placeholders `?` (como o resto do projeto — o
    wrapper de Postgres os traduz para `%s`; sqlite não entende `%s` sem
    passar por esse wrapper) em vez de reaproveitar get_employee_by_id/
    get_employee_current_unit deste mesmo módulo, que usam `%s` fixo no
    texto da query — inconsistência pré-existente e fora do escopo desta
    correção, que quebraria com conexões sqlite diretas (usadas em vários
    testes) se reaproveitada aqui.
    """
    if not actor or actor.get('role') not in ('admin', 'user'):
        return None
    linked_employee_id = actor.get('linked_employee_id')
    if not linked_employee_id:
        return None
    employee_id = int(linked_employee_id)
    employee_row = connection.execute(
        'SELECT unit_id FROM employees WHERE id = ?', (employee_id,)
    ).fetchone()
    if not employee_row:
        return None
    employee = row_to_dict(employee_row)
    today_iso = date.today().isoformat()
    movement = connection.execute(
        '''
        SELECT target_unit_id
        FROM employee_unit_movements
        WHERE employee_id = ?
          AND movement_type = 'temporary'
          AND start_date <= ?
          AND COALESCE(NULLIF(end_date, ''), '9999-12-31') >= ?
        ORDER BY start_date DESC, id DESC
        LIMIT 1
        ''',
        (employee_id, today_iso, today_iso),
    ).fetchone()
    return int(movement['target_unit_id']) if movement else int(employee['unit_id'])


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
    if item.get('role') in ('admin', 'user') and item.get('linked_employee_id'):
        operational_unit_id = get_employee_current_unit(connection, int(item['linked_employee_id']))
        if operational_unit_id:
            item['operational_unit_id'] = operational_unit_id
    return item


# Política de senha temporária. Vive AQUI, e não em modules.auth.service,
# pelo mesmo motivo de `actor_operational_unit_id`: `require_actor` precisa
# consultá-la, e `core.repository -> modules.auth.service` fecha exatamente o
# ciclo de import da issue #148 (auth.service já importa deste módulo).
def get_user_password_policy(connection, user_id):
    """Estado da política de senha temporária do usuário.

    Retorna {'must_change': bool, 'expired': bool}. Tolerante a bases sem as
    colunas (pré-migração) — nesse caso a política fica inativa (não bloqueia
    ninguém), preservando o login dos usuários existentes.
    """
    from datetime import datetime
    from epi_backend.config import UTC
    try:
        row = connection.execute(
            'SELECT must_change_password, password_expires_at FROM users WHERE id = ?',
            (int(user_id),),
        ).fetchone()
    except Exception:
        try:
            connection.rollback()
        except Exception:
            # Idem: conexão já inutilizável. O `return` abaixo é o que importa —
            # base sem as colunas mantém a política inativa e PRESERVA o login
            # dos usuários existentes, que é o objetivo desta tolerância.
            pass
        return {'must_change': False, 'expired': False}
    if not row:
        return {'must_change': False, 'expired': False}
    data = row_to_dict(row)
    must_change = int(data.get('must_change_password') or 0) == 1
    expires_raw = str(data.get('password_expires_at') or '').strip()
    expired = False
    if expires_raw:
        try:
            exp = datetime.fromisoformat(expires_raw)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=UTC)
            expired = datetime.now(UTC) > exp
        except Exception:
            expired = False
    return {'must_change': must_change, 'expired': expired}


def require_actor(connection, actor_user_id, *, allow_password_change_pending=False):
    """Ator válido para uma operação autenticada.

    `allow_password_change_pending` é a exceção EXPLÍCITA ao bloqueio de senha
    temporária. Fica como parâmetro, e não como lista de rotas permitidas, por
    dois motivos: uma lista de strings envelhece calada quando alguém renomeia
    uma rota, e a exceção precisa estar visível em quem a usa — não num arquivo
    de configuração distante de onde a decisão importa.

    Hoje só `/api/auth/me` a usa: é a rota que informa ao cliente POR QUE ele
    está bloqueado. Negá-la deixaria o app sem meio de descobrir para onde ir
    depois de um restart com token já emitido.
    """
    actor = get_user_by_id(connection, int(actor_user_id))
    if not actor or not int(actor['active']):
        raise PermissionError('Usuário executor inválido.')
    actor['role'] = normalize_role_name(actor.get('role'))
    if actor.get('role') != 'master_admin' and actor.get('company_id'):
        enforce_company_block_rules(connection, int(actor['company_id']))
    if not allow_password_change_pending:
        _deny_while_password_change_pending(connection, actor)
    return actor


def _deny_while_password_change_pending(connection, actor):
    """Bloqueia operações autenticadas enquanto a senha temporária não for trocada.

    Aqui, e não no login: o login PRECISA suceder para o cliente receber o
    token e conseguir chamar `/api/change-password`. O que não pode é o token
    servir para o resto — que era exatamente o furo, já que a obrigatoriedade
    vivia só no redirect da UI e qualquer chamada direta à API passava por
    cima.

    `require_actor` é o ponto certo porque `authorize_action` e
    `authorize_action_any` passam os dois por ele: uma checagem cobre as 242
    chamadas dos 21 módulos, sem marcar rota a rota.

    `/api/change-password` NÃO passa por aqui (usa `get_user_by_id` direto), e
    é por isso que o caminho de saída não se tranca sozinho. Há teste para
    isso — a garantia não pode depender de alguém lembrar.

    Base pré-migração (colunas ausentes) devolve `must_change: False` e não
    bloqueia ninguém: fail-open deliberado, para uma migration não aplicada não
    derrubar o sistema inteiro.
    """
    from core.security import PasswordChangeRequiredError

    if get_user_password_policy(connection, int(actor['id']))['must_change']:
        raise PasswordChangeRequiredError()


def authorize_action(connection, actor_user_id, action, company_id=None):
    actor = require_actor(connection, actor_user_id)
    ensure_permission(actor, action)
    if company_id is not None:
        ensure_company_access(actor, company_id)
    return actor


def authorize_action_any(connection, actor_user_id, actions, company_id=None):
    """Como `authorize_action`, mas aceita qualquer uma das permissões em
    `actions` — usado quando dois perfis distintos alcançam a mesma rota por
    permissões técnicas diferentes (ex.: Administrador Geral via
    employees:create, Administrador Local/Gestor de EPI via
    employees:create_simplified, ambos operando Empresas Terceirizadas
    dentro do próprio escopo). Levanta o erro da última permissão tentada
    quando nenhuma é concedida."""
    actor = require_actor(connection, actor_user_id)
    error = PermissionError('Nenhuma permissão informada.')
    for action in actions:
        try:
            ensure_permission(actor, action)
            break
        except PermissionError as exc:
            error = exc
    else:
        raise error
    if company_id is not None:
        ensure_company_access(actor, company_id)
    return actor


def require_master_actor(connection, actor_user_id):
    actor = authorize_action(connection, actor_user_id, 'commercial:view')
    if actor['role'] != 'master_admin':
        raise PermissionError('Apenas o Administrador Master pode alterar a marca do sistema.')
    return actor
