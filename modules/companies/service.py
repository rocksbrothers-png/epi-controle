import json
import re
import secrets
import unicodedata
from datetime import date, datetime

from core.roles import BILLABLE_ROLES
from epi_backend.db import row_to_dict
from modules.commercial.service import (
    count_company_users,
    get_commercial_settings,
    validate_cnpj,
    validate_logo_payload,
    normalize_plan_key,
    only_digits,
)

_SUPPORTED_LANGUAGES = {'pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO'}
_COLOR_RE = re.compile(r'^#[0-9A-Fa-f]{3}([0-9A-Fa-f]{3})?$')

# Identidade visual e dados cadastrais da tenant: propriedade do Administrador
# Geral da empresa contratante. O Administrador Master não os altera pela rota
# operacional (PUT /api/companies/{id}); alterações excepcionais passam pelo
# suporte auditado (POST /api/companies/{id}/support-update).
MASTER_PROTECTED_COMPANY_FIELDS: tuple[str, ...] = (
    'name', 'legal_name', 'cnpj', 'logo_type', 'login_logo_type', 'favicon_type',
    'primary_color', 'secondary_color', 'accent_color', 'slug', 'subdomain',
    'custom_domain', 'default_language', 'institutional_message',
    'contact_email', 'contact_phone', 'website', 'theme_json',
)

SQL_UPDATE_COMPANY = (
    "UPDATE companies SET "
    "name = ?, legal_name = ?, cnpj = ?, logo_type = ?, "
    "plan_name = ?, user_limit = ?, license_status = ?, active = ?, "
    "commercial_notes = ?, contract_start = ?, contract_end = ?, "
    "monthly_value = ?, addendum_enabled = ?, "
    "slug = ?, subdomain = ?, custom_domain = ?, login_logo_type = ?, "
    "primary_color = ?, secondary_color = ?, accent_color = ?, "
    "default_language = ?, favicon_type = ?, institutional_message = ?, "
    "contact_email = ?, contact_phone = ?, website = ?, theme_json = ? "
    "WHERE id = ?"
)


def _validate_color(value: str, default: str) -> str:
    v = str(value or '').strip()
    if not v:
        return default
    if not _COLOR_RE.match(v):
        raise ValueError(f"Cor inválida: '{v}'. Use formato hexadecimal (#RGB ou #RRGGBB).")
    return v


def _validate_language(value: str) -> str:
    v = str(value or 'pt-BR').strip()
    if v not in _SUPPORTED_LANGUAGES:
        return 'pt-BR'
    return v


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


def company_billable_user_counts(connection, company_id=None):
    """Mapa {company_id: nº de usuários ativos faturáveis} em uma única query.

    Evita N+1 ao enriquecer a lista de empresas com `user_count` (mesma
    semântica de commercial.count_company_users: ativos em BILLABLE_ROLES).
    """
    placeholders = ','.join(['?'] * len(BILLABLE_ROLES))
    sql = f"SELECT company_id, COUNT(*) AS n FROM users WHERE active = 1 AND role IN ({placeholders})"
    params = list(BILLABLE_ROLES)
    if company_id:
        sql += ' AND company_id = ?'
        params.append(company_id)
    sql += ' GROUP BY company_id'
    try:
        rows = connection.execute(sql, tuple(params)).fetchall()
    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass
        return {}
    counts = {}
    for row in rows:
        item = row_to_dict(row)
        cid = item.get('company_id')
        if cid is not None:
            counts[int(cid)] = int(item.get('n') or 0)
    return counts


def apply_company_usage_flags(company):
    """Define limit_reached / near_limit a partir de user_count vs user_limit.

    O frontend comercial (badges de risco, alertas, resumo) consome esses
    campos, mas eles nunca eram calculados — os alertas falhavam em silêncio.
    near_limit: >= 80% do limite e ainda abaixo dele.
    """
    count = int(company.get('user_count') or 0)
    limit = int(company.get('user_limit') or 0)
    company['limit_reached'] = 1 if limit > 0 and count >= limit else 0
    company['near_limit'] = 1 if limit > 0 and company['limit_reached'] == 0 and count >= 0.8 * limit else 0
    return company


def fetch_companies(connection, company_id=None):
    _full = (
        'SELECT id, name, legal_name, cnpj, active, logo_type, plan_name, user_limit, '
        'license_status, contract_start, contract_end, monthly_value, addendum_enabled, '
        'commercial_notes, slug, subdomain, custom_domain, login_logo_type, '
        'primary_color, secondary_color, accent_color, default_language, '
        'favicon_type, institutional_message, contact_email, contact_phone, website '
        'FROM companies'
    )
    _minimal = 'SELECT id, name, legal_name, cnpj, active FROM companies'
    for sql in (_full, _minimal):
        try:
            if company_id:
                rows = connection.execute(sql + ' WHERE id = ?', (company_id,)).fetchall()
            else:
                rows = connection.execute(sql + ' ORDER BY name').fetchall()
            companies = [row_to_dict(row) for row in rows]
            counts = company_billable_user_counts(connection, company_id)
            for company in companies:
                company['user_count'] = int(counts.get(int(company['id']), 0))
                apply_company_usage_flags(company)
            return companies
        except Exception:
            # Roll back the aborted transaction before the fallback query,
            # otherwise PostgreSQL rejects it with "transaction is aborted".
            try:
                connection.rollback()
            except Exception:
                pass
            if sql is _minimal:
                raise
            # Some column missing — retry with minimal set


def company_action_label(action_type):
    return {
        'create': 'Criação',
        'update': 'Atualização',
        'suspend': 'Suspensão',
        'reactivate': 'Reativação',
        'self_update': 'Configuração pela empresa',
        'support_update': 'Suporte excepcional (Master)',
        'onboarding_complete': 'Implantação concluída',
        'provision': 'Liberação da tenant',
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


def register_company_audit(connection, company_id, actor, action_type, summary, details=None,
                           *, legal_entity_id=None):
    """Trilha de auditoria da empresa.

    ``legal_entity_id`` registra o CNPJ afetado pela ação (efeito fiscal /
    trabalhista). Só entra no INSERT quando a coluna existe, preservando
    compatibilidade durante a janela de migração.
    """
    from epi_backend.db import table_columns

    columns = ['company_id', 'actor_user_id', 'actor_name', 'action_type', 'summary',
               'details_json', 'created_at']
    values = [
        company_id,
        actor['id'],
        actor['full_name'],
        action_type,
        summary,
        json.dumps(details or [], ensure_ascii=False),
        datetime.now().isoformat(timespec='seconds'),
    ]
    if legal_entity_id not in (None, '', 0, '0') and 'legal_entity_id' in table_columns(connection, 'company_audit_logs'):
        columns.append('legal_entity_id')
        values.append(int(legal_entity_id))
    placeholders = ', '.join(['?'] * len(values))
    connection.execute(
        f"INSERT INTO company_audit_logs ({', '.join(columns)}) VALUES ({placeholders})",  # noqa: S608
        tuple(values),
    )


def ensure_unique_company_cnpj(connection, cnpj, exclude_company_id=None):
    normalized = only_digits(cnpj)
    try:
        rows = connection.execute('SELECT id, cnpj FROM companies').fetchall()
    except Exception:
        return
    for row in rows:
        if exclude_company_id and int(row['id']) == int(exclude_company_id):
            continue
        if only_digits(row['cnpj']) == normalized:
            raise ValueError('Já existe uma empresa cadastrada com este CNPJ.')


def validate_company_whitelabel_payload(payload, company_id=None):
    """Valida e normaliza os campos white-label da empresa."""
    from modules.tenant.service import validate_slug, ensure_slug_unique
    slug_raw = str(payload.get('slug') or '').strip()
    if slug_raw:
        payload['slug'] = validate_slug(slug_raw)
    else:
        payload['slug'] = None

    payload['subdomain'] = str(payload.get('subdomain') or '').strip().lower() or None
    payload['custom_domain'] = str(payload.get('custom_domain') or '').strip().lower() or None
    from modules.commercial.service import validate_login_logo_payload
    payload['login_logo_type'] = validate_login_logo_payload(payload.get('login_logo_type', ''))
    payload['primary_color'] = _validate_color(payload.get('primary_color', ''), '#1565C0')
    payload['secondary_color'] = _validate_color(payload.get('secondary_color', ''), '#42A5F5')
    payload['accent_color'] = _validate_color(payload.get('accent_color', ''), '#FF6F00')
    payload['default_language'] = _validate_language(payload.get('default_language', ''))
    payload['favicon_type'] = str(payload.get('favicon_type') or '').strip()
    payload['institutional_message'] = str(payload.get('institutional_message') or '').strip()
    payload['contact_email'] = str(payload.get('contact_email') or '').strip()
    payload['contact_phone'] = str(payload.get('contact_phone') or '').strip()
    payload['website'] = str(payload.get('website') or '').strip()
    theme_raw = payload.get('theme_json') or '{}'
    if isinstance(theme_raw, dict):
        import json as _json
        payload['theme_json'] = _json.dumps(theme_raw, ensure_ascii=False)
    else:
        try:
            import json as _json
            _json.loads(str(theme_raw))
            payload['theme_json'] = str(theme_raw)
        except Exception:
            payload['theme_json'] = '{}'
    return payload


def validate_company_payload(connection, payload, company_id=None):
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
    # validar campos white-label se presentes
    try:
        validate_company_whitelabel_payload(payload, company_id)
    except Exception:
        pass
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


# ── Company write operations ──────────────────────────────────────────────────

def create_company(connection, payload):
    cursor = connection.execute(
        (
            'INSERT INTO companies ('
            'name, legal_name, cnpj, logo_type, plan_name, user_limit, license_status, active, '
            'commercial_notes, contract_start, contract_end, monthly_value, addendum_enabled, '
            'slug, subdomain, custom_domain, login_logo_type, '
            'primary_color, secondary_color, accent_color, default_language, '
            'favicon_type, institutional_message, contact_email, contact_phone, website, theme_json'
            ') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        ),
        (
            payload['name'], payload['legal_name'], payload['cnpj'],
            payload.get('logo_type', ''),
            payload['plan_name'], payload['user_limit'],
            payload['license_status'], int(payload.get('active', 1)),
            payload.get('commercial_notes', ''), payload.get('contract_start', ''),
            payload.get('contract_end', ''),
            payload.get('monthly_value', 0), payload.get('addendum_enabled', 0),
            payload.get('slug'), payload.get('subdomain'), payload.get('custom_domain'),
            payload.get('login_logo_type', ''),
            payload.get('primary_color', '#1565C0'),
            payload.get('secondary_color', '#42A5F5'),
            payload.get('accent_color', '#FF6F00'),
            payload.get('default_language', 'pt-BR'),
            payload.get('favicon_type', ''),
            payload.get('institutional_message', ''),
            payload.get('contact_email', ''),
            payload.get('contact_phone', ''),
            payload.get('website', ''),
            payload.get('theme_json', '{}'),
        )
    )
    return int(cursor.lastrowid)


def get_company_full(connection, company_id):
    row = connection.execute('SELECT * FROM companies WHERE id = ?', (company_id,)).fetchone()
    return row_to_dict(row) if row else None


def update_company(connection, company_id, payload):
    connection.execute(
        SQL_UPDATE_COMPANY,
        (
            payload['name'], payload['legal_name'], payload['cnpj'],
            payload.get('logo_type', ''),
            payload['plan_name'], payload['user_limit'],
            payload['license_status'], int(payload.get('active', 1)),
            payload.get('commercial_notes', ''), payload.get('contract_start', ''),
            payload.get('contract_end', ''),
            payload.get('monthly_value', 0), payload.get('addendum_enabled', 0),
            payload.get('slug'), payload.get('subdomain'), payload.get('custom_domain'),
            payload.get('login_logo_type', ''),
            payload.get('primary_color', '#1565C0'),
            payload.get('secondary_color', '#42A5F5'),
            payload.get('accent_color', '#FF6F00'),
            payload.get('default_language', 'pt-BR'),
            payload.get('favicon_type', ''),
            payload.get('institutional_message', ''),
            payload.get('contact_email', ''),
            payload.get('contact_phone', ''),
            payload.get('website', ''),
            payload.get('theme_json', '{}'),
            company_id,
        )
    )


def suspend_company(connection, company_id):
    connection.execute(
        "UPDATE companies SET license_status = 'suspended' WHERE id = ?",
        (company_id,)
    )


# ── Provisionamento inicial da tenant (liberação pelo Administrador Master) ───

def generate_tenant_slug(connection, name, exclude_company_id=None):
    """Gera um slug/subdomínio temporário único a partir do nome da empresa."""
    normalized = unicodedata.normalize('NFKD', str(name or ''))
    ascii_name = normalized.encode('ascii', 'ignore').decode('ascii').lower()
    base = re.sub(r'[^a-z0-9]+', '-', ascii_name).strip('-')
    if len(base) < 3:
        base = f'empresa-{base}'.strip('-')
    base = base[:60].strip('-')
    candidate = base
    suffix = 2
    while True:
        query = 'SELECT id FROM companies WHERE (slug = ? OR subdomain = ?)'
        params = [candidate, candidate]
        if exclude_company_id:
            query += ' AND id != ?'
            params.append(int(exclude_company_id))
        if not connection.execute(query, params).fetchone():
            return candidate
        candidate = f'{base}-{suffix}'
        suffix += 1


def mark_company_onboarding_pending(connection, company_id):
    """Nova tenant começa com o assistente de implantação pendente."""
    connection.execute(
        "UPDATE companies SET onboarding_completed = 0, onboarding_completed_at = '' WHERE id = ?",
        (int(company_id),),
    )


def provision_tenant_structure(connection, company_id, payload):
    """Cria a estrutura inicial da tenant na liberação pelo Administrador Master.

    - unidade matriz inicial;
    - usuário Administrador Geral (Owner), quando informado o e-mail;
    - subdomínio temporário (se ainda não definido);
    - assistente de implantação marcado como pendente.

    Retorna detalhes auditáveis da operação. A identidade visual permanece com
    o tema padrão da plataforma até o Administrador Geral configurá-la.
    """
    from core.security import hash_password
    from modules.units.service import create_unit

    details = []

    company = get_company_full(connection, company_id) or {}
    if not (company.get('slug') or company.get('subdomain')):
        slug = generate_tenant_slug(connection, company.get('name'), company_id)
        connection.execute(
            'UPDATE companies SET slug = ?, subdomain = ? WHERE id = ?',
            (slug, slug, int(company_id)),
        )
        details.append({'field': 'Subdomínio temporário', 'before': '', 'after': slug})

    # LegalEntity padrão (matriz) da empresa — âncora jurídica/fiscal do modelo
    # Multi-CNPJ. Criada a partir do CNPJ/razão social da própria empresa quando
    # o schema Multi-CNPJ já está provisionado.
    from modules.legal_entities.service import ensure_default_legal_entity, legal_entities_ready
    legal_entity_id = None
    if legal_entities_ready(connection):
        legal_entity_id = ensure_default_legal_entity(connection, int(company_id))
        details.append({'field': 'CNPJ matriz (LegalEntity)', 'before': '', 'after': f'id {legal_entity_id}'})

    unit_id = create_unit(
        connection, int(company_id), 'Matriz', 'base', '',
        'Unidade matriz criada automaticamente na liberação da tenant.',
    )
    # Vincula a unidade matriz ao CNPJ matriz (best-effort; coluna nullable).
    if legal_entity_id is not None:
        try:
            connection.execute(
                'UPDATE units SET legal_entity_id = ? WHERE id = ? AND legal_entity_id IS NULL',
                (legal_entity_id, int(unit_id)),
            )
        except Exception:
            # Vínculo unidade↔CNPJ é conveniência não-crítica: se a coluna ainda
            # não existir (janela de migração), o provisionamento não deve falhar.
            pass
    details.append({'field': 'Unidade matriz', 'before': '', 'after': f'Matriz (id {unit_id})'})

    general_admin_email = str(payload.get('general_admin_email') or '').strip().lower()
    if general_admin_email:
        if '@' not in general_admin_email or ' ' in general_admin_email:
            raise ValueError('E-mail do Administrador Geral inválido.')
        existing = connection.execute(
            'SELECT id FROM users WHERE LOWER(username) = ?', (general_admin_email,)
        ).fetchone()
        if existing:
            raise ValueError('Já existe um usuário com o e-mail informado para o Administrador Geral.')
        full_name = str(payload.get('general_admin_name') or '').strip() or 'Administrador Geral'
        # Senha aleatória não divulgada: o primeiro acesso ocorre via convite /
        # recuperação de senha, nunca com credencial conhecida pelo Master.
        password = hash_password(secrets.token_urlsafe(24))
        cursor = connection.execute(
            'INSERT INTO users (username, password, full_name, role, company_id, active) '
            "VALUES (?, ?, ?, 'general_admin', ?, 1)",
            (general_admin_email, password, full_name, int(company_id)),
        )
        owner_user_id = int(cursor.lastrowid)
        try:
            connection.execute(
                'UPDATE users SET email = ? WHERE id = ?', (general_admin_email, owner_user_id)
            )
        except Exception:
            try:
                connection.rollback()
            except Exception:
                pass
        invite_status = send_owner_invite(connection, owner_user_id, general_admin_email, company.get('name') or '')
        details.append({
            'field': 'Administrador Geral',
            'before': '',
            'after': f'{general_admin_email} (id {owner_user_id}, convite: {invite_status})',
        })

    mark_company_onboarding_pending(connection, company_id)
    details.append({'field': 'Assistente de implantação', 'before': '', 'after': 'pendente (primeiro acesso)'})
    return details


def send_owner_invite(connection, owner_user_id, owner_email, company_name):
    """Gera o token de primeiro acesso e envia o convite por e-mail (best-effort).

    Reaproveita o mecanismo de recuperação de senha (token de uso único com
    validade de 24h). Uma falha de SMTP não impede a criação da tenant — o
    Master pode reemitir o token pela tela de usuários.
    Retorna um rótulo auditável do resultado.
    """
    import os

    from epi_backend.http_utils import structured_log
    from modules.auth.service import generate_user_recovery_token

    token = generate_user_recovery_token(connection, owner_user_id)
    try:
        from epi_backend.mailer import send_email

        login_url = (
            os.environ.get('WEB_APP_URL', '').strip()
            or os.environ.get('PUBLIC_BASE_URL', '').strip()
        ).rstrip('/')
        access_line = f'Acesse: {login_url}\n\n' if login_url else ''
        body = (
            f'Olá,\n\n'
            f'Você foi convidado como Administrador Geral da empresa "{company_name}" '
            f'no EPI Controle.\n\n'
            f'{access_line}'
            f'Para o primeiro acesso:\n'
            f'  1. Na tela de login, use "Esqueci minha senha".\n'
            f'  2. Informe seu usuário ({owner_email}), a nova senha e a chave abaixo.\n\n'
            f'Chave de primeiro acesso (válida por 24 horas):\n\n'
            f'  {token}\n\n'
            f'Após entrar, o assistente de implantação vai guiá-lo na configuração '
            f'dos dados, identidade visual e domínio da sua empresa.\n\n'
            f'Atenciosamente,\nEPI Controle'
        )
        send_email(owner_email, f'Convite — Administrador Geral de {company_name} no EPI Controle', body)
        structured_log('info', 'company.owner_invite_sent', owner_user_id=owner_user_id)
        return 'enviado por e-mail'
    except Exception as exc:
        structured_log('warning', 'company.owner_invite_failed',
                       owner_user_id=owner_user_id, error=str(exc))
        return 'falha no envio (reemita o token pela tela de usuários)'


# ── Authorized suppliers ──────────────────────────────────────────────────────

def upsert_authorized_supplier(connection, company_id, actor_id, name, cnpj, category, contact_email, notes, now):
    existing = connection.execute(
        'SELECT id FROM authorized_suppliers WHERE company_id = ? AND LOWER(TRIM(name)) = ?',
        (company_id, name.lower())
    ).fetchone()
    if existing:
        connection.execute(
            'UPDATE authorized_suppliers SET cnpj = ?, category = ?, contact_email = ?, notes = ?, active = 1, updated_at = ? WHERE id = ?',
            (cnpj, category, contact_email, notes, now, int(existing['id']))
        )
        return int(existing['id'])
    cur = connection.execute(
        'INSERT INTO authorized_suppliers (company_id, name, cnpj, category, contact_email, notes, active, source, created_by_user_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)',
        (company_id, name, cnpj, category, contact_email, notes, 'manual', int(actor_id), now, now)
    )
    return int(cur.lastrowid)


def upsert_authorized_supplier_upload_row(connection, company_id, actor_id, name, cnpj, category, contact_email, notes, now):
    existing = connection.execute(
        "SELECT id FROM authorized_suppliers WHERE company_id = ? AND (LOWER(TRIM(name)) = ? OR (cnpj != '' AND cnpj = ?))",
        (company_id, name.lower(), cnpj)
    ).fetchone()
    if existing:
        connection.execute(
            'UPDATE authorized_suppliers SET name = ?, cnpj = ?, category = ?, contact_email = ?, notes = ?, active = 1, source = ?, updated_at = ? WHERE id = ?',
            (name, cnpj, category, contact_email, notes, 'upload', now, int(existing['id']))
        )
        return False
    connection.execute(
        'INSERT INTO authorized_suppliers (company_id, name, cnpj, category, contact_email, notes, active, source, created_by_user_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)',
        (company_id, name, cnpj, category, contact_email, notes, 'upload', int(actor_id), now, now)
    )
    return True


def toggle_authorized_supplier(connection, supplier_id, company_id, now):
    supplier = connection.execute(
        'SELECT * FROM authorized_suppliers WHERE id = ? AND company_id = ?',
        (supplier_id, company_id)
    ).fetchone()
    if not supplier:
        return None, None
    new_active = 0 if int(supplier['active']) == 1 else 1
    connection.execute(
        'UPDATE authorized_suppliers SET active = ?, updated_at = ? WHERE id = ?',
        (new_active, now, supplier_id)
    )
    return row_to_dict(supplier), new_active
