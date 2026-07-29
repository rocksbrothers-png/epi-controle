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
      - Administrador Master / Geral / de Registro → todos (``None``). São os
        únicos perfis que administram CNPJ (docs/PAPEIS_E_ATRIBUICOES.md #2/#3);
      - Administrador Local (``admin``) → não administra CNPJ e não escolhe um.
        O CNPJ é resolvido automaticamente a partir da única unidade que ele
        administra (``units.legal_entity_id``) — nunca de uma carteira própria.
        Ausência de unidade operacional ou de CNPJ na unidade devolve ``[]``
        (nenhum CNPJ), nunca "sem restrição";
      - Gestor de EPI (``user``) → apenas o CNPJ do colaborador vinculado,
        derivado de ``users.linked_employee_id`` (sem dado redundante).
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

    if role == 'admin':
        from modules.employees.service import actor_operational_unit_id
        unit_id = actor_operational_unit_id(connection, actor)
        if not unit_id:
            return []
        row = connection.execute(
            'SELECT legal_entity_id FROM units WHERE id = ?', (int(unit_id),)
        ).fetchone()
        entity_id = (row['legal_entity_id'] if hasattr(row, 'keys') else row[0]) if row else None
        return [int(entity_id)] if entity_id else []

    return []


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
    """Escopo de **consolidação de saldos** configurado para a empresa.

    Apesar do nome histórico da coluna, este valor governa apenas até onde os
    saldos são agregados **na leitura** (ADR-0001 §15). Ele nunca define unidade
    de saída, origem de baixa, estoque usado na entrega, origem de reserva, de
    ajuste, de devolução ou unidade de recebimento — essas continuam presas à
    unidade da operação.

    Cai para ``unit`` (o recorte mais restrito) quando a coluna ainda não existe.
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


def resolve_stock_consolidation_unit_ids(connection, company_id, unit_id, authorized_unit_ids=None):
    """Unidades cujos saldos são **consolidados na leitura** junto com ``unit_id``.

    Fronteira de CONSOLIDAÇÃO, nunca de saída (ADR-0001 §15). O estoque pertence
    exclusivamente a uma unidade: nenhuma operação física ou lógica — entrega,
    reserva, baixa, ajuste, devolução, recebimento — pode escolher a unidade de
    origem a partir daqui. Este resultado só alimenta visão agregada.

      - ``unit``          → só a própria unidade;
      - ``legal_entity``  → todas as unidades do mesmo CNPJ;
      - ``company``       → todas as unidades da empresa.

    Como cada unidade já carrega ``legal_entity_id``, a consolidação por CNPJ é
    derivada sem re-chavear a tabela de estoque nem migrar dados.

    ``authorized_unit_ids`` recorta o resultado pelas unidades que o ator pode
    ver: o saldo exibido é a interseção entre o escopo configurado e a carteira
    do usuário. ``None`` significa "sem restrição" — diferente de lista vazia,
    que significa "nenhuma unidade autorizada" e devolve nada. Confundir os dois
    mostraria a empresa inteira a quem não tem acesso a unidade alguma.
    """
    unit_id = int(unit_id)
    scope = get_stock_control_scope(connection, company_id)
    if scope == 'unit':
        candidates = {unit_id}
    elif scope == 'company':
        rows = connection.execute(
            'SELECT id FROM units WHERE company_id = ?', (int(company_id),)
        ).fetchall()
        candidates = {int(r['id'] if hasattr(r, 'keys') else r[0]) for r in rows} | {unit_id}
    else:  # scope == 'legal_entity'
        from epi_backend.db import table_columns
        if 'legal_entity_id' not in table_columns(connection, 'units'):
            candidates = {unit_id}
        else:
            row = connection.execute(
                'SELECT legal_entity_id FROM units WHERE id = ?', (unit_id,)
            ).fetchone()
            entity_id = (row['legal_entity_id'] if hasattr(row, 'keys') else row[0]) if row else None
            if not entity_id:
                candidates = {unit_id}
            else:
                rows = connection.execute(
                    'SELECT id FROM units WHERE company_id = ? AND legal_entity_id = ?',
                    (int(company_id), int(entity_id)),
                ).fetchall()
                candidates = {int(r['id'] if hasattr(r, 'keys') else r[0]) for r in rows} | {unit_id}
    if authorized_unit_ids is None:
        return sorted(candidates)
    return sorted(candidates & {int(item) for item in authorized_unit_ids})


# Nome anterior. A palavra "pool" carregava a leitura de estoque compartilhado
# que a decisão da §15 rejeita; mantido como alias para não quebrar chamadores.
resolve_stock_pool_unit_ids = resolve_stock_consolidation_unit_ids


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


# Cabeçalhos aceitos na importação de planilha de CNPJs. Cada campo do modelo
# aceita variações em português (com e sem acento) e o nome técnico em inglês —
# planilhas de clientes raramente seguem um padrão único.
_IMPORT_HEADER_ALIASES: dict[str, tuple[str, ...]] = {
    'cnpj': ('cnpj', 'c.n.p.j', 'cnpj_numero'),
    'legal_name': ('legal_name', 'razao_social', 'razaosocial', 'razao'),
    'trade_name': ('trade_name', 'nome_fantasia', 'nomefantasia', 'fantasia', 'nome'),
    'entity_type': ('entity_type', 'tipo', 'tipo_entidade', 'natureza'),
    'state_registration': ('state_registration', 'inscricao_estadual', 'ie'),
    'municipal_registration': ('municipal_registration', 'inscricao_municipal', 'im'),
    'cnae': ('cnae', 'cnae_principal'),
    'address': ('address', 'endereco', 'logradouro'),
    'municipality': ('municipality', 'municipio', 'cidade'),
    'uf': ('uf', 'estado'),
    'cep': ('cep', 'codigo_postal'),
    'opening_date': ('opening_date', 'data_abertura', 'dataabertura', 'abertura'),
    'registration_status': ('registration_status', 'situacao', 'situacao_cadastral'),
    'notes': ('notes', 'observacoes', 'observacao', 'obs'),
    'active': ('active', 'ativo'),
    'is_headquarters': ('is_headquarters', 'matriz', 'matriz_filial'),
}

_TRUTHY = {'1', 'true', 'sim', 's', 'yes', 'y', 'ativo', 'ativa', 'matriz'}
_FALSY = {'0', 'false', 'nao', 'não', 'n', 'no', 'inativo', 'inativa', 'filial'}

# Rótulos de planilha para os tipos de pessoa jurídica.
_ENTITY_TYPE_ALIASES: dict[str, str] = {
    'matriz': 'matriz', 'sede': 'matriz', 'headquarters': 'matriz',
    'filial': 'filial', 'branch': 'filial',
    'subsidiaria': 'subsidiaria', 'subsidiária': 'subsidiaria', 'subsidiary': 'subsidiaria',
    'spe': 'spe',
    'jv': 'jv_partner', 'jv_partner': 'jv_partner', 'joint_venture': 'jv_partner',
    'socia': 'jv_partner', 'sócia': 'jv_partner',
    'consorciada': 'consorciada', 'consorcio': 'consorciada',
}


def _normalize_header(value) -> str:
    """Cabeçalho comparável: minúsculo, sem acento e com separadores unificados."""
    import unicodedata
    text = unicodedata.normalize('NFKD', str(value or '')).encode('ascii', 'ignore').decode('ascii')
    text = text.strip().lower()
    for ch in (' ', '-', '/', '.'):
        text = text.replace(ch, '_')
    while '__' in text:
        text = text.replace('__', '_')
    return text.strip('_')


def _parse_bool_cell(value, default=None):
    text = _normalize_header(value)
    if not text:
        return default
    if text in _TRUTHY:
        return True
    if text in _FALSY:
        return False
    return default


def normalize_import_row(row) -> dict:
    """Converte uma linha de planilha no payload de LegalEntity.

    Aceita cabeçalhos em português (com/sem acento) e em inglês. Campos
    desconhecidos são ignorados — planilhas de clientes costumam trazer colunas
    extras irrelevantes.
    """
    normalized_row = {_normalize_header(key): value for key, value in dict(row or {}).items()}
    payload: dict = {}
    for field, aliases in _IMPORT_HEADER_ALIASES.items():
        for alias in aliases:
            if alias in normalized_row and str(normalized_row[alias] or '').strip():
                payload[field] = normalized_row[alias]
                break

    if 'entity_type' in payload:
        payload['entity_type'] = _ENTITY_TYPE_ALIASES.get(
            _normalize_header(payload['entity_type']), 'filial'
        )
    active = _parse_bool_cell(payload.get('active'), default=True)
    payload['active'] = 1 if active else 0
    headquarters = _parse_bool_cell(payload.get('is_headquarters'), default=None)
    if headquarters is not None:
        payload['is_headquarters'] = 1 if headquarters else 0
    return payload


def import_legal_entities_rows(connection, company_id, rows):
    """Importa CNPJs a partir de linhas de planilha já convertidas em dicts.

    CNPJ já existente na empresa é **atualizado**; novo é criado. Erros são
    reportados por índice de linha (1-based, como o usuário vê na planilha) sem
    abortar a importação inteira — o operador corrige apenas as linhas com
    problema e reenvia.
    """
    created, updated, errors = [], [], []
    for index, raw_row in enumerate(rows or [], start=1):
        try:
            payload = normalize_import_row(raw_row)
            if not payload.get('cnpj'):
                continue  # linha vazia / separador da planilha
            cnpj_digits = only_digits(payload['cnpj'])
            existing = connection.execute(
                'SELECT id FROM legal_entities WHERE company_id = ? AND '
                "REPLACE(REPLACE(REPLACE(cnpj, '.', ''), '/', ''), '-', '') = ? LIMIT 1",
                (int(company_id), cnpj_digits),
            ).fetchone()
            if existing:
                entity_id = int(existing['id'] if hasattr(existing, 'keys') else existing[0])
                update_legal_entity(connection, entity_id, payload, int(company_id))
                updated.append(entity_id)
            else:
                created.append(create_legal_entity(connection, payload, int(company_id)))
        except (ValueError, PermissionError) as exc:
            errors.append({'row': index, 'error': str(exc)})
    return {'created_ids': created, 'updated_ids': updated, 'errors': errors}


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
