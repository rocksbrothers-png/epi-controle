"""Serviços de LegalEntity (CNPJs da empresa) — arquitetura Multi-CNPJ / JV.

Uma empresa contratante (tenant, tabela ``companies``) pode possuir uma ou
várias LegalEntity: matriz, filiais, subsidiárias, SPEs e empresas sócias de
Joint Venture. Cada LegalEntity carrega a identidade jurídica/fiscal completa
(CNPJ, razão social, inscrições, CNAE, endereço, situação cadastral) e é a
âncora de rastreabilidade abaixo da empresa e acima de unidade/colaborador.

O modelo preserva a arquitetura SaaS Multi-Tenant: ``companies`` continua sendo
a fronteira de faturamento/assinatura; LegalEntity não altera a cobrança.
"""

from __future__ import annotations

from datetime import datetime, timezone

from epi_backend.db import row_to_dict
from modules.commercial.service import only_digits, validate_cnpj

UTC = timezone.utc

# Tipos de pessoa jurídica suportados. `matriz`/`filial` cobrem o caso comum;
# os demais habilitam holdings, grupos e Joint Ventures sem novas tabelas.
ENTITY_TYPES: tuple[str, ...] = (
    'matriz', 'filial', 'subsidiaria', 'spe', 'jv_partner', 'consorciada', 'outro',
)

# Estruturas organizacionais oferecidas no onboarding.
ORG_STRUCTURE_TYPES: tuple[str, ...] = (
    'single_cnpj', 'multi_cnpj', 'holding', 'group', 'joint_venture', 'consortium', 'other',
)

# Escopo de controle de estoque configurável por empresa.
STOCK_CONTROL_SCOPES: tuple[str, ...] = ('company', 'legal_entity', 'unit')

_UF_SET = {
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG',
    'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
}

_SELECT_COLUMNS = (
    'id, company_id, cnpj, legal_name, trade_name, entity_type, parent_entity_id, '
    'state_registration, municipal_registration, cnae, address, municipality, uf, cep, '
    'opening_date, registration_status, is_headquarters, active, notes, created_at, updated_at'
)


def legal_entities_ready(connection) -> bool:
    """Indica se o schema Multi-CNPJ já está provisionado (tabela + coluna de
    vínculo em employees). Durante a janela de migração — e em fixtures de
    schema parcial — o vínculo é ignorado silenciosamente, preservando total
    retrocompatibilidade com o fluxo de CNPJ único."""
    from epi_backend.db import table_columns, table_exists
    return (
        table_exists(connection, 'legal_entities')
        and 'legal_entity_id' in table_columns(connection, 'employees')
    )


# Papéis que enxergam todos os CNPJs da própria empresa (gestão estrutural).
_FULL_SCOPE_ROLES: frozenset[str] = frozenset({'master_admin', 'general_admin', 'registry_admin'})


def resolve_actor_legal_entity_ids(connection, actor):
    """CNPJs que o ator pode enxergar. ``None`` = sem restrição.

    Regras (conformidade jurídica):
      - Administrador Master / Geral / de Registro → todos (``None``);
      - Administrador Local (``admin``) → apenas os CNPJs autorizados em
        ``user_legal_entities``. **Lista vazia = sem restrição**, para não
        quebrar os administradores locais já existentes, que nunca tiveram
        autorização explícita;
      - Usuário (``user``) → apenas o CNPJ do colaborador vinculado, derivado de
        ``users.linked_employee_id`` (sem dado redundante).
    """
    if not actor:
        return None
    role = str(actor.get('role') or '')
    if role in _FULL_SCOPE_ROLES:
        return None
    if not legal_entities_ready(connection):
        return None

    if role == 'user':
        employee_id = actor.get('linked_employee_id')
        if not employee_id:
            return []
        row = connection.execute(
            'SELECT legal_entity_id FROM employees WHERE id = ?', (int(employee_id),)
        ).fetchone()
        entity_id = (row['legal_entity_id'] if hasattr(row, 'keys') else row[0]) if row else None
        return [int(entity_id)] if entity_id else []

    # Administrador Local: autorização explícita por CNPJ.
    from epi_backend.db import table_exists
    if not table_exists(connection, 'user_legal_entities'):
        return None
    rows = connection.execute(
        'SELECT legal_entity_id FROM user_legal_entities WHERE user_id = ?',
        (int(actor.get('id') or 0),),
    ).fetchall()
    allowed = [int(r['legal_entity_id'] if hasattr(r, 'keys') else r[0]) for r in rows]
    return allowed or None


def ensure_legal_entity_access(connection, actor, legal_entity_id):
    """Bloqueia o acesso a um CNPJ fora do escopo autorizado do ator."""
    if legal_entity_id in (None, '', 0, '0'):
        return
    allowed = resolve_actor_legal_entity_ids(connection, actor)
    if allowed is None:
        return
    if int(legal_entity_id) not in allowed:
        raise PermissionError('Acesso permitido apenas para os CNPJs autorizados ao seu perfil.')


def employee_legal_entity_sql(connection, *, employee_alias='employees', prefix='legal_entity'):
    """Fragmentos SQL para enriquecer consultas que já fazem JOIN com
    ``employees``, derivando o CNPJ do colaborador.

    Retorna ``(select_fragment, join_fragment)`` — ambos vazios quando o schema
    Multi-CNPJ ainda não está provisionado, de modo que a consulta original
    continua válida. Centraliza o gating para não duplicar a checagem em cada
    módulo (entregas, colaboradores, portal, relatórios).
    """
    if not legal_entities_ready(connection):
        return '', ''
    select_fragment = (
        f', {employee_alias}.legal_entity_id'
        f', legal_entities.cnpj AS {prefix}_cnpj'
        f', legal_entities.legal_name AS {prefix}_name'
        f', legal_entities.trade_name AS {prefix}_trade_name'
    )
    join_fragment = (
        f' LEFT JOIN legal_entities ON legal_entities.id = {employee_alias}.legal_entity_id'
    )
    return select_fragment, join_fragment


def get_stock_control_scope(connection, company_id) -> str:
    """Escopo de controle de estoque configurado para a empresa.

    Cai para ``unit`` (comportamento histórico) quando a coluna ainda não existe.
    """
    from epi_backend.db import table_columns
    if 'stock_control_scope' not in table_columns(connection, 'companies'):
        return 'unit'
    row = connection.execute(
        'SELECT stock_control_scope FROM companies WHERE id = ?', (int(company_id),)
    ).fetchone()
    if not row:
        return 'unit'
    value = row['stock_control_scope'] if hasattr(row, 'keys') else row[0]
    return normalize_stock_control_scope(value)


def resolve_stock_pool_unit_ids(connection, company_id, unit_id):
    """Unidades que compartilham o mesmo pool de estoque da ``unit_id``.

    O estoque físico continua registrado por unidade — é onde o item de fato
    está. O escopo configurado define apenas a **fronteira de compartilhamento**
    do saldo:

      - ``unit``          → só a própria unidade (comportamento histórico);
      - ``legal_entity``  → todas as unidades do mesmo CNPJ (estoque por CNPJ);
      - ``company``       → todas as unidades da empresa (estoque compartilhado).

    Como cada unidade já carrega ``legal_entity_id``, o pool por CNPJ é derivado
    sem re-chavear a tabela de estoque nem migrar dados.
    """
    unit_id = int(unit_id)
    scope = get_stock_control_scope(connection, company_id)
    if scope == 'unit':
        return [unit_id]
    if scope == 'company':
        rows = connection.execute(
            'SELECT id FROM units WHERE company_id = ?', (int(company_id),)
        ).fetchall()
        return sorted({int(r['id'] if hasattr(r, 'keys') else r[0]) for r in rows} | {unit_id})
    # scope == 'legal_entity'
    from epi_backend.db import table_columns
    if 'legal_entity_id' not in table_columns(connection, 'units'):
        return [unit_id]
    row = connection.execute(
        'SELECT legal_entity_id FROM units WHERE id = ?', (unit_id,)
    ).fetchone()
    entity_id = (row['legal_entity_id'] if hasattr(row, 'keys') else row[0]) if row else None
    if not entity_id:
        return [unit_id]
    rows = connection.execute(
        'SELECT id FROM units WHERE company_id = ? AND legal_entity_id = ?',
        (int(company_id), int(entity_id)),
    ).fetchall()
    return sorted({int(r['id'] if hasattr(r, 'keys') else r[0]) for r in rows} | {unit_id})


def normalize_entity_type(value) -> str:
    v = str(value or 'matriz').strip().lower()
    return v if v in ENTITY_TYPES else 'matriz'


def normalize_org_structure_type(value) -> str:
    v = str(value or 'single_cnpj').strip().lower()
    return v if v in ORG_STRUCTURE_TYPES else 'single_cnpj'


def normalize_stock_control_scope(value) -> str:
    v = str(value or 'company').strip().lower()
    return v if v in STOCK_CONTROL_SCOPES else 'company'


def _normalize_uf(value) -> str:
    v = str(value or '').strip().upper()
    if v and v not in _UF_SET:
        raise ValueError(f"UF inválida: '{v}'.")
    return v


def validate_legal_entity_payload(connection, payload, company_id, entity_id=None):
    """Valida e normaliza o payload de uma LegalEntity.

    Regras: CNPJ válido e único dentro da empresa; razão social obrigatória;
    tipo/UF normalizados; ``parent_entity_id`` (quando informado) precisa
    pertencer à mesma empresa e não pode ser a própria entidade.
    """
    payload = payload or {}
    cnpj = validate_cnpj(payload.get('cnpj'))
    cnpj_digits = only_digits(cnpj)

    legal_name = str(payload.get('legal_name') or '').strip()
    if not legal_name:
        raise ValueError('Razão social é obrigatória.')

    duplicate = connection.execute(
        'SELECT id FROM legal_entities WHERE company_id = ? AND '
        "REPLACE(REPLACE(REPLACE(cnpj, '.', ''), '/', ''), '-', '') = ? "
        + ('AND id <> ? ' if entity_id else '')
        + 'LIMIT 1',
        (company_id, cnpj_digits, entity_id) if entity_id else (company_id, cnpj_digits),
    ).fetchone()
    if duplicate:
        raise ValueError('Já existe um CNPJ com este número nesta empresa.')

    parent_entity_id = payload.get('parent_entity_id')
    if parent_entity_id in (None, '', 0, '0'):
        parent_entity_id = None
    else:
        parent_entity_id = int(parent_entity_id)
        if entity_id and parent_entity_id == int(entity_id):
            raise ValueError('Uma pessoa jurídica não pode ser controladora de si mesma.')
        parent = connection.execute(
            'SELECT id FROM legal_entities WHERE id = ? AND company_id = ? LIMIT 1',
            (parent_entity_id, company_id),
        ).fetchone()
        if not parent:
            raise ValueError('Controladora (parent_entity) não encontrada nesta empresa.')

    entity_type = normalize_entity_type(payload.get('entity_type'))
    is_headquarters = 1 if entity_type == 'matriz' else int(bool(payload.get('is_headquarters', 0)))

    return {
        'company_id': int(company_id),
        'cnpj': cnpj,
        'legal_name': legal_name,
        'trade_name': str(payload.get('trade_name') or '').strip(),
        'entity_type': entity_type,
        'parent_entity_id': parent_entity_id,
        'state_registration': str(payload.get('state_registration') or '').strip(),
        'municipal_registration': str(payload.get('municipal_registration') or '').strip(),
        'cnae': str(payload.get('cnae') or '').strip(),
        'address': str(payload.get('address') or '').strip(),
        'municipality': str(payload.get('municipality') or '').strip(),
        'uf': _normalize_uf(payload.get('uf')),
        'cep': only_digits(payload.get('cep')),
        'opening_date': str(payload.get('opening_date') or '').strip(),
        'registration_status': str(payload.get('registration_status') or 'ativa').strip() or 'ativa',
        'is_headquarters': is_headquarters,
        'active': int(bool(payload.get('active', 1))),
        'notes': str(payload.get('notes') or '').strip(),
    }


def create_legal_entity(connection, payload, company_id):
    validated = validate_legal_entity_payload(connection, payload, company_id)
    now_iso = datetime.now(UTC).isoformat()
    cursor = connection.execute(
        'INSERT INTO legal_entities (company_id, cnpj, legal_name, trade_name, entity_type, '
        'parent_entity_id, state_registration, municipal_registration, cnae, address, '
        'municipality, uf, cep, opening_date, registration_status, is_headquarters, active, '
        'notes, created_at, updated_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            validated['company_id'], validated['cnpj'], validated['legal_name'],
            validated['trade_name'], validated['entity_type'], validated['parent_entity_id'],
            validated['state_registration'], validated['municipal_registration'],
            validated['cnae'], validated['address'], validated['municipality'],
            validated['uf'], validated['cep'], validated['opening_date'],
            validated['registration_status'], validated['is_headquarters'],
            validated['active'], validated['notes'], now_iso, now_iso,
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def update_legal_entity(connection, entity_id, payload, company_id):
    validated = validate_legal_entity_payload(connection, payload, company_id, entity_id=entity_id)
    now_iso = datetime.now(UTC).isoformat()
    connection.execute(
        'UPDATE legal_entities SET cnpj = ?, legal_name = ?, trade_name = ?, entity_type = ?, '
        'parent_entity_id = ?, state_registration = ?, municipal_registration = ?, cnae = ?, '
        'address = ?, municipality = ?, uf = ?, cep = ?, opening_date = ?, registration_status = ?, '
        'is_headquarters = ?, active = ?, notes = ?, updated_at = ? '
        'WHERE id = ? AND company_id = ?',
        (
            validated['cnpj'], validated['legal_name'], validated['trade_name'],
            validated['entity_type'], validated['parent_entity_id'],
            validated['state_registration'], validated['municipal_registration'],
            validated['cnae'], validated['address'], validated['municipality'],
            validated['uf'], validated['cep'], validated['opening_date'],
            validated['registration_status'], validated['is_headquarters'],
            validated['active'], validated['notes'], now_iso, int(entity_id), int(company_id),
        ),
    )
    connection.commit()


def fetch_legal_entities(connection, actor=None, company_id=None):
    """Lista CNPJs escopados pelo ator. Master vê todos (ou filtra por empresa);
    demais papéis veem apenas os da própria empresa."""
    where = []
    params: list = []
    if actor and actor.get('role') != 'master_admin':
        where.append('company_id = ?')
        params.append(actor['company_id'])
    elif company_id is not None:
        where.append('company_id = ?')
        params.append(int(company_id))
    # Escopo por CNPJ: Administrador Local restrito aos autorizados; Usuário
    # restrito ao CNPJ do seu colaborador.
    allowed = resolve_actor_legal_entity_ids(connection, actor) if actor else None
    if allowed is not None:
        if not allowed:
            return []
        placeholders = ', '.join(['?'] * len(allowed))
        where.append(f'id IN ({placeholders})')
        params.extend(allowed)
    sql = f'SELECT {_SELECT_COLUMNS} FROM legal_entities'
    if where:
        sql += ' WHERE ' + ' AND '.join(where)
    sql += ' ORDER BY company_id, is_headquarters DESC, legal_name'
    rows = connection.execute(sql, tuple(params)).fetchall()
    return [row_to_dict(row) for row in rows]


def get_legal_entity_by_id(connection, entity_id):
    row = connection.execute(
        f'SELECT {_SELECT_COLUMNS} FROM legal_entities WHERE id = ?',
        (int(entity_id),),
    ).fetchone()
    return row_to_dict(row) if row else None


def get_default_legal_entity_id(connection, company_id):
    """Retorna o id da matriz padrão da empresa (menor id / matriz). ``None`` se
    a empresa ainda não tiver nenhuma LegalEntity."""
    row = connection.execute(
        'SELECT id FROM legal_entities WHERE company_id = ? '
        'ORDER BY is_headquarters DESC, id LIMIT 1',
        (int(company_id),),
    ).fetchone()
    if not row:
        return None
    return int(row['id'] if hasattr(row, 'keys') else row[0])


def ensure_default_legal_entity(connection, company_id):
    """Garante que a empresa tenha ao menos uma LegalEntity (matriz), criando-a a
    partir do CNPJ/razão social da empresa quando ausente. Idempotente."""
    existing = get_default_legal_entity_id(connection, company_id)
    if existing:
        return existing
    company = connection.execute(
        'SELECT id, name, legal_name, cnpj FROM companies WHERE id = ?',
        (int(company_id),),
    ).fetchone()
    if not company:
        raise ValueError('Empresa não encontrada.')
    data = row_to_dict(company)
    now_iso = datetime.now(UTC).isoformat()
    cursor = connection.execute(
        'INSERT INTO legal_entities (company_id, cnpj, legal_name, trade_name, entity_type, '
        'is_headquarters, active, created_at, updated_at) '
        "VALUES (?, ?, ?, ?, 'matriz', 1, 1, ?, ?)",
        (
            int(company_id),
            str(data.get('cnpj') or ''),
            str(data.get('legal_name') or data.get('name') or ''),
            str(data.get('name') or ''),
            now_iso, now_iso,
        ),
    )
    return int(cursor.lastrowid)


def count_active_legal_entities(connection, company_id) -> int:
    row = connection.execute(
        'SELECT COUNT(*) AS total FROM legal_entities WHERE company_id = ? AND active = 1',
        (int(company_id),),
    ).fetchone()
    if not row:
        return 0
    return int(row['total'] if hasattr(row, 'keys') else row[0])


def deactivate_legal_entity(connection, entity_id, company_id):
    """Inativa um CNPJ (exclusão nunca é física).

    O histórico jurídico/fiscal precisa ser preservado, então DELETE vira
    inativação auditada. Bloqueia quando:
      - é o último CNPJ ativo da empresa (deixaria a empresa sem pessoa jurídica);
      - existem colaboradores ativos vinculados (exige realocação antes).
    """
    entity = get_legal_entity_by_id(connection, entity_id)
    if not entity or int(entity['company_id']) != int(company_id):
        raise ValueError('CNPJ não encontrado nesta empresa.')
    if not int(entity.get('active', 1)):
        return  # já inativo: idempotente
    if count_active_legal_entities(connection, company_id) <= 1:
        raise ValueError('Não é possível inativar o único CNPJ ativo da empresa.')
    linked = connection.execute(
        'SELECT COUNT(*) AS total FROM employees WHERE legal_entity_id = ?',
        (int(entity_id),),
    ).fetchone()
    linked_total = int(linked['total'] if hasattr(linked, 'keys') else linked[0]) if linked else 0
    if linked_total:
        raise ValueError(
            f'Existem {linked_total} colaborador(es) vinculados a este CNPJ. '
            'Realoque-os para outro CNPJ antes de inativar.'
        )
    connection.execute(
        'UPDATE legal_entities SET active = 0, updated_at = ? WHERE id = ? AND company_id = ?',
        (datetime.now(UTC).isoformat(), int(entity_id), int(company_id)),
    )
    connection.commit()


def fetch_user_legal_entities(connection, user_id):
    """CNPJs explicitamente autorizados a um usuário."""
    from epi_backend.db import table_exists
    if not table_exists(connection, 'user_legal_entities'):
        return []
    rows = connection.execute(
        'SELECT legal_entity_id FROM user_legal_entities WHERE user_id = ? ORDER BY legal_entity_id',
        (int(user_id),),
    ).fetchall()
    return [int(r['legal_entity_id'] if hasattr(r, 'keys') else r[0]) for r in rows]


def set_user_legal_entities(connection, user_id, company_id, legal_entity_ids):
    """Define a autorização de CNPJs de um usuário (substitui a lista inteira).

    Lista vazia remove a restrição (usuário volta a enxergar todos os CNPJs da
    empresa), coerente com o padrão retrocompatível de ``resolve_actor_legal_entity_ids``.
    """
    ids = []
    for raw in legal_entity_ids or []:
        if raw in (None, '', 0, '0'):
            continue
        entity = get_legal_entity_by_id(connection, int(raw))
        if not entity or int(entity['company_id']) != int(company_id):
            raise ValueError('CNPJ informado não pertence a esta empresa.')
        ids.append(int(raw))
    connection.execute('DELETE FROM user_legal_entities WHERE user_id = ?', (int(user_id),))
    now_iso = datetime.now(UTC).isoformat()
    for entity_id in sorted(set(ids)):
        connection.execute(
            'INSERT INTO user_legal_entities (user_id, legal_entity_id, company_id, created_at) '
            'VALUES (?, ?, ?, ?)',
            (int(user_id), entity_id, int(company_id), now_iso),
        )
    connection.commit()
    return sorted(set(ids))


def resolve_employee_legal_entity_id(connection, company_id, requested_id):
    """Resolve o CNPJ de um colaborador: usa o informado (validando que pertence
    à empresa) ou cai para a matriz padrão. Mantém retrocompatibilidade com
    clientes que ainda não enviam ``legal_entity_id``."""
    if requested_id not in (None, '', 0, '0'):
        entity = get_legal_entity_by_id(connection, int(requested_id))
        if not entity or int(entity['company_id']) != int(company_id):
            raise ValueError('CNPJ informado não pertence a esta empresa.')
        if not int(entity.get('active', 1)):
            raise ValueError('CNPJ informado está inativo.')
        return int(requested_id)
    # Empresa com mais de um CNPJ ativo: o vínculo jurídico do colaborador é
    # obrigatório — escolher a matriz por omissão poderia registrar o vínculo
    # trabalhista/previdenciário na pessoa jurídica errada. Empresa de CNPJ
    # único mantém o fallback automático (retrocompatível).
    if count_active_legal_entities(connection, company_id) > 1:
        raise ValueError(
            'Informe o CNPJ ao qual este colaborador pertence '
            '(a empresa possui mais de um CNPJ ativo).'
        )
    return ensure_default_legal_entity(connection, company_id)
