"""Serviços de gestão de colaboradores."""

from epi_backend.http_utils import structured_log
from epi_backend.db import row_to_dict
from core.auth import ensure_resource_company
from core.repository import actor_operational_unit_id  # noqa: F401 - reexportado (ver nota abaixo)


def normalize_cpf(value):
    digits = ''.join(ch for ch in str(value or '') if ch.isdigit())
    if len(digits) != 11:
        raise ValueError('CPF do colaborador deve conter 11 dígitos.')
    return digits


def normalize_preferred_contact_channel(value):
    normalized = str(value or '').strip().lower()
    return normalized if normalized in ('whatsapp', 'email') else 'whatsapp'


def ensure_employee_identity_unique(connection, company_id, employee_id_code, cpf, exclude_id=None):
    try:
        code_row = connection.execute(
            f"SELECT id FROM employees WHERE company_id = ? AND employee_id_code = ? {'AND id <> ?' if exclude_id else ''} LIMIT 1",
            (int(company_id), str(employee_id_code).strip(), int(exclude_id)) if exclude_id else (int(company_id), str(employee_id_code).strip())
        ).fetchone()
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
        code_row = None
    if code_row:
        raise ValueError('ID do colaborador já cadastrado nesta empresa.')
    try:
        cpf_row = connection.execute(
            f"SELECT id FROM employees WHERE company_id = ? AND cpf = ? {'AND id <> ?' if exclude_id else ''} LIMIT 1",
            (int(company_id), normalize_cpf(cpf), int(exclude_id)) if exclude_id else (int(company_id), normalize_cpf(cpf))
        ).fetchone()
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
        cpf_row = None
    if cpf_row:
        raise ValueError('CPF do colaborador já cadastrado nesta empresa.')


def create_employee(connection, payload, *, actor):
    from core.auth import ensure_resource_company
    from core.repository import get_unit_by_id

    if str(payload.get('unit_id', '')).strip():
        unit = get_unit_by_id(connection, int(payload['unit_id']))
    else:
        unit = connection.execute(
            'SELECT id, company_id, name, unit_type, city, notes FROM units WHERE company_id = ? ORDER BY id LIMIT 1',
            (int(payload['company_id']),)
        ).fetchone()
        if not unit:
            default_unit_name = f"Unidade Padrão {int(payload['company_id'])}"
            unit_cursor = connection.execute(
                'INSERT INTO units (company_id, name, unit_type, city, notes) VALUES (?, ?, ?, ?, ?)',
                (int(payload['company_id']), default_unit_name, 'base', 'Não informado', 'Unidade criada automaticamente no cadastro do colaborador.')
            )
            unit = connection.execute(
                'SELECT id, company_id, name, unit_type, city, notes FROM units WHERE id = ?',
                (int(unit_cursor.lastrowid),)
            ).fetchone()
    ensure_resource_company(actor, unit, 'Unidade')
    from modules.units.service import ensure_unit_operational
    ensure_unit_operational(connection, unit['id'], 'novos colaboradores')
    if str(unit['company_id']) != str(payload['company_id']):
        raise ValueError('Unidade e empresa do colaborador precisam ser compatíveis.')
    cpf_digits = normalize_cpf(payload.get('cpf'))
    ensure_employee_identity_unique(connection, int(payload['company_id']), payload['employee_id_code'], cpf_digits)
    preferred_channel = normalize_preferred_contact_channel(payload.get('preferred_contact_channel'))
    tipo_vinculo = str(payload.get('tipo_vinculo') or 'CLT').strip() or 'CLT'
    empresa_origem = str(payload.get('empresa_origem') or '').strip() if tipo_vinculo != 'CLT' else ''
    columns = [
        'company_id', 'unit_id', 'employee_id_code', 'cpf', 'name', 'email', 'whatsapp',
        'preferred_contact_channel', 'sector', 'role_name', 'admission_date', 'schedule_type',
        'tipo_vinculo', 'empresa_origem',
    ]
    values = [
        payload['company_id'],
        unit['id'],
        payload['employee_id_code'],
        cpf_digits,
        payload['name'],
        str(payload.get('email') or '').strip().lower(),
        ''.join(ch for ch in str(payload.get('whatsapp') or '') if ch.isdigit()),
        preferred_channel,
        payload['sector'],
        payload['role_name'],
        payload['admission_date'],
        payload['schedule_type'],
        tipo_vinculo,
        empresa_origem,
    ]
    # CNPJ (LegalEntity) ao qual o colaborador pertence. Se o cliente não enviar
    # (retrocompatibilidade), cai para a matriz padrão da empresa. Só é gravado
    # quando o schema Multi-CNPJ já está provisionado.
    from modules.legal_entities.service import legal_entities_ready, resolve_employee_legal_entity_id
    if legal_entities_ready(connection):
        columns.append('legal_entity_id')
        values.append(resolve_employee_legal_entity_id(
            connection, int(payload['company_id']), payload.get('legal_entity_id')
        ))
    # Vínculo opcional com empresa terceirizada/prestadora — Cadastro
    # Simplificado (ADR-0002). Ausente (None) para todo colaborador CLT,
    # exatamente como legal_entity_id acima é ausente sem schema Multi-CNPJ.
    from modules.outsourced_companies.service import (
        outsourced_companies_ready, validate_employee_outsourced_reference,
    )
    if outsourced_companies_ready(connection):
        outsourced_company_id, service_contract_id, epi_override, epi_override_reason = (
            validate_employee_outsourced_reference(connection, payload, int(payload['company_id']))
        )
        columns.extend([
            'outsourced_company_id', 'service_contract_id',
            'epi_responsibility_override', 'epi_responsibility_override_reason',
        ])
        values.extend([outsourced_company_id, service_contract_id, epi_override, epi_override_reason])
    placeholders = ', '.join(['?'] * len(values))
    cursor = connection.execute(
        f"INSERT INTO employees ({', '.join(columns)}) VALUES ({placeholders})",
        tuple(values),
    )
    connection.commit()
    return int(cursor.lastrowid)


def update_employee(connection, employee_id, payload, *, actor):
    from core.auth import ensure_resource_company
    from core.repository import get_employee_by_id, get_unit_by_id

    current = get_employee_by_id(connection, employee_id)
    ensure_resource_company(actor, current, 'Colaborador')
    unit = get_unit_by_id(connection, int(payload['unit_id']))
    ensure_resource_company(actor, unit, 'Unidade')
    if int(unit['id']) != int(current.get('unit_id') or 0):
        # Só bloqueia transferência PARA unidade arquivada; editar cadastro de
        # colaborador que já está em unidade arquivada continua permitido.
        from modules.units.service import ensure_unit_operational
        ensure_unit_operational(connection, unit['id'], 'transferência de colaboradores')
    if str(unit['company_id']) != str(payload['company_id']):
        raise ValueError('Unidade e empresa do colaborador precisam ser compatíveis.')
    cpf_digits = normalize_cpf(payload.get('cpf'))
    ensure_employee_identity_unique(connection, int(payload['company_id']), payload['employee_id_code'], cpf_digits, exclude_id=employee_id)
    preferred_channel = normalize_preferred_contact_channel(payload.get('preferred_contact_channel'))
    tipo_vinculo = str(payload.get('tipo_vinculo') or 'CLT').strip() or 'CLT'
    empresa_origem = str(payload.get('empresa_origem') or '').strip() if tipo_vinculo != 'CLT' else ''
    whatsapp = ''.join(ch for ch in str(payload.get('whatsapp') or '') if ch.isdigit())
    email = str(payload.get('email') or '').strip().lower()
    set_columns = [
        'company_id', 'unit_id', 'employee_id_code', 'cpf', 'name', 'email', 'whatsapp',
        'preferred_contact_channel', 'sector', 'role_name', 'admission_date', 'schedule_type',
        'tipo_vinculo', 'empresa_origem',
    ]
    values = [
        payload['company_id'], payload['unit_id'], payload['employee_id_code'], cpf_digits,
        payload['name'], email, whatsapp, preferred_channel, payload['sector'],
        payload['role_name'], payload['admission_date'], payload['schedule_type'],
        tipo_vinculo, empresa_origem,
    ]
    # O CNPJ é o vínculo jurídico do contrato de trabalho: IMUTÁVEL na edição
    # comum do cadastro. Um legal_entity_id enviado no payload é ignorado — a
    # mudança só ocorre pelo processo administrativo auditado
    # (transfer_employee_legal_entity). Colaborador legado sem vínculo recebe o
    # backfill na primeira edição.
    from modules.legal_entities.service import legal_entities_ready, resolve_employee_legal_entity_id
    if legal_entities_ready(connection):
        legal_entity_id = current.get('legal_entity_id') or resolve_employee_legal_entity_id(
            connection, int(payload['company_id']), None
        )
        set_columns.append('legal_entity_id')
        values.append(legal_entity_id)
    # Vínculo com empresa terceirizada/prestadora é mutável na edição comum
    # (não tem a semântica jurídica de legal_entity_id — é só a referência
    # comercial vigente). Cadastro Simplificado (ADR-0002).
    from modules.outsourced_companies.service import (
        outsourced_companies_ready, validate_employee_outsourced_reference,
    )
    if outsourced_companies_ready(connection):
        outsourced_company_id, service_contract_id, epi_override, epi_override_reason = (
            validate_employee_outsourced_reference(connection, payload, int(payload['company_id']))
        )
        set_columns.extend([
            'outsourced_company_id', 'service_contract_id',
            'epi_responsibility_override', 'epi_responsibility_override_reason',
        ])
        values.extend([outsourced_company_id, service_contract_id, epi_override, epi_override_reason])
    values.append(employee_id)
    sql = f"UPDATE employees SET {', '.join(f'{c} = ?' for c in set_columns)} WHERE id = ?"
    connection.execute(sql, tuple(values))
    connection.commit()


# ── Cadastro de Colaboradores simplificado (ADR-0002 §10.2) ────────────────
# Escreve na MESMA tabela employees, nunca cria uma base paralela. Só cobre
# terceirizado/prestador — CLT continua exclusivamente por create_employee/
# update_employee. Campos que não fazem parte do formulário simplificado
# (sector, schedule_type, email, whatsapp) ficam em branco; employee_id_code
# é gerado automaticamente (não é um campo do formulário).

def _generate_simplified_employee_code(connection, company_id):
    import secrets
    for _ in range(5):
        candidate = f"TERC-{int(company_id)}-{secrets.token_hex(4).upper()}"
        exists = connection.execute(
            'SELECT id FROM employees WHERE employee_id_code = ? LIMIT 1', (candidate,),
        ).fetchone()
        if not exists:
            return candidate
    raise RuntimeError('Não foi possível gerar um código único para o colaborador.')


def ensure_actor_unit_scope_for_target(connection, actor, unit_id):
    """Mesma regra de ensure_actor_employee_scope, mas para um unit_id-alvo
    que ainda não tem colaborador (ex.: criação) — Administrador Local/
    Gestor de EPI só podem operar dentro da própria unidade operacional."""
    if actor.get('role') not in ('admin', 'user'):
        return
    scope_unit_id = actor_operational_unit_id(connection, actor)
    if not scope_unit_id:
        raise PermissionError('Seu perfil não possui unidade operacional ativa.')
    if int(unit_id) != int(scope_unit_id):
        raise PermissionError('Operação permitida somente para a sua unidade operacional.')


def validate_employee_outsourced_simplified_payload(payload):
    """Campos obrigatórios/opcionais do Cadastro de Colaboradores (ADR-0002
    §10.2, prompt do produto) — nunca aceita tipo_vinculo == 'CLT'."""
    payload = payload or {}
    name = str(payload.get('name') or '').strip()
    if not name:
        raise ValueError('Nome completo é obrigatório.')
    tipo_vinculo = str(payload.get('tipo_vinculo') or '').strip()
    if not tipo_vinculo:
        raise ValueError('Tipo de vínculo é obrigatório.')
    if tipo_vinculo == 'CLT':
        raise ValueError(
            'Cadastro de Colaboradores simplificado não aceita vínculo CLT — use o cadastro completo.'
        )
    role_name = str(payload.get('role_name') or '').strip()
    if not role_name:
        raise ValueError('Função é obrigatória.')
    admission_date = str(payload.get('admission_date') or '').strip()
    if not admission_date:
        raise ValueError('Data de início é obrigatória.')
    if payload.get('outsourced_company_id') in (None, '', 0, '0'):
        raise ValueError('Empresa terceirizada/prestadora é obrigatória.')
    if payload.get('unit_id') in (None, '', 0, '0'):
        raise ValueError('Unidade é obrigatória.')
    return {
        'name': name,
        'tipo_vinculo': tipo_vinculo,
        'role_name': role_name,
        'admission_date': admission_date,
        'origin_company_registration': str(payload.get('origin_company_registration') or '').strip(),
        'badge_number': str(payload.get('badge_number') or '').strip(),
        'notes': str(payload.get('notes') or '').strip(),
    }


def create_employee_outsourced_simplified(connection, payload, *, actor):
    from core.archival import ensure_record_operational
    from core.repository import get_unit_by_id
    from modules.outsourced_companies.service import (
        get_outsourced_company_by_id, validate_employee_outsourced_reference,
    )
    from modules.units.service import ensure_unit_operational

    company_id = int(payload.get('company_id') or actor.get('company_id') or 0)
    if not company_id:
        raise ValueError('Empresa é obrigatória.')

    validated = validate_employee_outsourced_simplified_payload(payload)
    unit_id = int(payload['unit_id'])
    unit = get_unit_by_id(connection, unit_id)
    ensure_resource_company(actor, unit, 'Unidade')
    if str(unit['company_id']) != str(company_id):
        raise ValueError('Unidade e empresa do colaborador precisam ser compatíveis.')
    ensure_unit_operational(connection, unit_id, 'novos colaboradores')
    ensure_actor_unit_scope_for_target(connection, actor, unit_id)

    outsourced_company_id, service_contract_id, epi_override, epi_override_reason = (
        validate_employee_outsourced_reference(connection, payload, company_id)
    )
    if not outsourced_company_id:
        raise ValueError('Empresa terceirizada/prestadora é obrigatória.')
    ensure_record_operational(
        connection, 'outsourced_companies', outsourced_company_id,
        'Empresa terceirizada', 'novos colaboradores',
    )
    outsourced_company = get_outsourced_company_by_id(connection, outsourced_company_id)
    empresa_origem = str((outsourced_company or {}).get('trade_name') or (outsourced_company or {}).get('legal_name') or '')

    cpf_digits = normalize_cpf(payload.get('cpf'))
    employee_id_code = _generate_simplified_employee_code(connection, company_id)
    ensure_employee_identity_unique(connection, company_id, employee_id_code, cpf_digits)

    columns = [
        'company_id', 'unit_id', 'employee_id_code', 'cpf', 'name', 'sector', 'role_name',
        'admission_date', 'schedule_type', 'tipo_vinculo', 'empresa_origem',
        'outsourced_company_id', 'service_contract_id',
        'epi_responsibility_override', 'epi_responsibility_override_reason',
        'origin_company_registration', 'badge_number', 'notes',
    ]
    values = [
        company_id, unit_id, employee_id_code, cpf_digits, validated['name'], '', validated['role_name'],
        validated['admission_date'], '', validated['tipo_vinculo'], empresa_origem,
        outsourced_company_id, service_contract_id, epi_override, epi_override_reason,
        validated['origin_company_registration'], validated['badge_number'], validated['notes'],
    ]
    from modules.legal_entities.service import legal_entities_ready, resolve_employee_legal_entity_id
    if legal_entities_ready(connection):
        columns.append('legal_entity_id')
        values.append(resolve_employee_legal_entity_id(connection, company_id, payload.get('legal_entity_id')))

    placeholders = ', '.join(['?'] * len(values))
    cursor = connection.execute(
        f"INSERT INTO employees ({', '.join(columns)}) VALUES ({placeholders})",
        tuple(values),
    )
    connection.commit()
    return int(cursor.lastrowid)


def update_employee_outsourced_simplified(connection, employee_id, payload, *, actor):
    from core.archival import ensure_record_operational
    from core.repository import get_employee_by_id as _get_employee_by_id, get_unit_by_id
    from modules.outsourced_companies.service import (
        get_outsourced_company_by_id, validate_employee_outsourced_reference,
    )
    from modules.units.service import ensure_unit_operational

    current = _get_employee_by_id(connection, employee_id)
    if not current:
        raise ValueError('Colaborador não encontrado.')
    ensure_resource_company(actor, current, 'Colaborador')
    if str(current.get('tipo_vinculo') or '') == 'CLT' or not current.get('outsourced_company_id'):
        raise PermissionError(
            'Este colaborador não pertence ao Cadastro de Colaboradores simplificado — use o cadastro completo.'
        )

    company_id = int(payload.get('company_id') or current['company_id'])
    if str(company_id) != str(current['company_id']):
        raise ValueError('Empresa do colaborador é imutável nesta edição.')

    validated = validate_employee_outsourced_simplified_payload(payload)
    unit_id = int(payload['unit_id'])
    unit = get_unit_by_id(connection, unit_id)
    ensure_resource_company(actor, unit, 'Unidade')
    if str(unit['company_id']) != str(company_id):
        raise ValueError('Unidade e empresa do colaborador precisam ser compatíveis.')
    if int(unit_id) != int(current.get('unit_id') or 0):
        ensure_unit_operational(connection, unit_id, 'transferência de colaboradores')
    # Escopo por unidade do ator: precisa poder operar tanto na unidade atual
    # do colaborador quanto na unidade-destino (evita transferir para fora,
    # ou editar de fora, da própria carteira de unidade).
    ensure_actor_employee_scope(connection, actor, current)
    ensure_actor_unit_scope_for_target(connection, actor, unit_id)

    outsourced_company_id, service_contract_id, epi_override, epi_override_reason = (
        validate_employee_outsourced_reference(connection, payload, company_id)
    )
    if not outsourced_company_id:
        raise ValueError('Empresa terceirizada/prestadora é obrigatória.')
    ensure_record_operational(
        connection, 'outsourced_companies', outsourced_company_id,
        'Empresa terceirizada', 'edição de colaboradores',
    )
    outsourced_company = get_outsourced_company_by_id(connection, outsourced_company_id)
    empresa_origem = str((outsourced_company or {}).get('trade_name') or (outsourced_company or {}).get('legal_name') or '')

    cpf_digits = normalize_cpf(payload.get('cpf'))
    ensure_employee_identity_unique(
        connection, company_id, current['employee_id_code'], cpf_digits, exclude_id=employee_id,
    )

    set_columns = [
        'unit_id', 'cpf', 'name', 'role_name', 'admission_date', 'tipo_vinculo', 'empresa_origem',
        'outsourced_company_id', 'service_contract_id',
        'epi_responsibility_override', 'epi_responsibility_override_reason',
        'origin_company_registration', 'badge_number', 'notes',
    ]
    values = [
        unit_id, cpf_digits, validated['name'], validated['role_name'], validated['admission_date'],
        validated['tipo_vinculo'], empresa_origem,
        outsourced_company_id, service_contract_id, epi_override, epi_override_reason,
        validated['origin_company_registration'], validated['badge_number'], validated['notes'],
    ]
    values.append(employee_id)
    sql = f"UPDATE employees SET {', '.join(f'{c} = ?' for c in set_columns)} WHERE id = ?"
    connection.execute(sql, tuple(values))
    connection.commit()


def get_employee_by_id(connection, employee_id):
    from epi_backend.db import table_columns
    cols = table_columns(connection, 'employees')
    legal_entity_col = ', legal_entity_id' if 'legal_entity_id' in cols else ''
    outsourced_cols = (
        ', outsourced_company_id, service_contract_id, epi_responsibility_override, '
        'epi_responsibility_override_reason'
    ) if 'outsourced_company_id' in cols else ''
    # Cadastro de Colaboradores simplificado (ADR-0002 §10.2).
    simplified_cols = (
        ', origin_company_registration, badge_number, notes'
    ) if 'origin_company_registration' in cols else ''
    row = connection.execute(
        'SELECT id, company_id, unit_id, employee_id_code, cpf, name, email, whatsapp, '
        'preferred_contact_channel, sector, role_name, admission_date, schedule_type, '
        f'tipo_vinculo, empresa_origem{legal_entity_col}{outsourced_cols}{simplified_cols} FROM employees WHERE id = ?',
        (employee_id,),
    ).fetchone()
    return row_to_dict(row) if row else None


def get_employee_current_unit(connection, employee_id):
    from datetime import date
    employee = get_employee_by_id(connection, int(employee_id))
    if not employee:
        return None
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
        (int(employee_id), today_iso, today_iso),
    ).fetchone()
    return int(movement['target_unit_id']) if movement else int(employee['unit_id'])


# actor_operational_unit_id vive em core.repository (não aqui) e é
# reexportado no topo deste arquivo: core.repository não importa nenhum
# módulo de domínio, então módulos como legal_entities/units podem resolver
# a unidade operacional do ator sem importar modules.employees.service de
# volta — a causa raiz do ciclo employees<->units<->legal_entities (issue
# #148). Os ~15 chamadores existentes (`from modules.employees.service
# import actor_operational_unit_id`) continuam funcionando sem alteração.


def actor_has_no_operational_unit(actor, scope_unit_id):
    """True quando Administrador Local/Gestor de EPI não tem unidade ativa.

    Administrador Local e Gestor de EPI só enxergam a própria unidade
    (vínculo único, nunca uma carteira — docs/PAPEIS_E_ATRIBUICOES.md #4/#5):
    sem colaborador vinculado ou sem unidade atual, a listagem/ação deve
    negar ou devolver vazio — nunca cair para "sem restrição" (empresa
    inteira). Mesmo antipadrão do escopo de CNPJ do Administrador Local e do
    escopo de Comprador/Aprovador (ver actor_has_no_purchase_unit_scope).
    """
    return actor.get('role') in ('admin', 'user') and not scope_unit_id


def ensure_actor_employee_scope(connection, actor, employee):
    ensure_resource_company(actor, employee, 'Colaborador')
    scope_unit_id = actor_operational_unit_id(connection, actor)
    if actor.get('role') in ('admin', 'user') and not scope_unit_id:
        raise PermissionError('Seu perfil não possui unidade operacional ativa.')
    if scope_unit_id:
        employee_unit_id = get_employee_current_unit(connection, int(employee['id']))
        if int(employee_unit_id) != int(scope_unit_id):
            raise PermissionError('Operação permitida somente para colaboradores da sua unidade operacional.')


def active_temporary_unit_allocations(connection, today_iso=None):
    """Mapa {employee_id: {'unit_id', 'unit_name'}} das movimentações temporárias
    ativas hoje, numa única query (evita N+1 ao enriquecer listas)."""
    from datetime import date
    today_iso = today_iso or date.today().isoformat()
    rows = connection.execute(
        'SELECT m.employee_id, m.target_unit_id, u.name AS target_unit_name '
        'FROM employee_unit_movements m JOIN units u ON u.id = m.target_unit_id '
        "WHERE m.movement_type = 'temporary' AND m.start_date <= ? "
        "AND COALESCE(NULLIF(m.end_date, ''), '9999-12-31') >= ? "
        'ORDER BY m.start_date DESC, m.id DESC',
        (today_iso, today_iso),
    ).fetchall()
    allocations = {}
    for row in rows:
        item = row_to_dict(row)
        eid = int(item['employee_id'])
        if eid not in allocations:  # ordenado DESC -> primeiro é o mais recente
            allocations[eid] = {
                'unit_id': int(item['target_unit_id']),
                'unit_name': item.get('target_unit_name'),
            }
    return allocations


def apply_current_unit_allocation(connection, employees):
    """Acrescenta current_unit_id / current_unit_name / unit_allocation_type
    a cada colaborador, refletindo movimentações temporárias ativas.

    Corrige a tabela de colaboradores, que lia esses campos mas nunca os recebia
    do bootstrap — exibindo a unidade-base mesmo durante transferências."""
    allocations = active_temporary_unit_allocations(connection)
    for emp in employees or []:
        alloc = allocations.get(int(emp['id']))
        if alloc:
            emp['current_unit_id'] = alloc['unit_id']
            emp['current_unit_name'] = alloc['unit_name']
            emp['unit_allocation_type'] = 'temporary'
        else:
            emp['current_unit_id'] = int(emp['unit_id']) if emp.get('unit_id') is not None else None
            emp['current_unit_name'] = emp.get('unit_name')
            emp['unit_allocation_type'] = 'definitive'
    return employees


def fetch_employees(connection, actor=None):
    from core.archival import NON_OPERATIONAL_STATUSES, lifecycle_enabled
    from epi_backend.db import table_columns
    from modules.legal_entities.service import employee_legal_entity_sql
    lifecycle = lifecycle_enabled(connection, 'employees')
    status_field = ', employees.status' if lifecycle else ''
    # O vínculo com CNPJ (LegalEntity) é opcional durante a janela de migração e
    # em fixtures de schema parcial — o helper devolve fragmentos vazios nesse
    # caso, preservando retrocompatibilidade.
    legal_entity_select, legal_entity_join = employee_legal_entity_sql(connection)
    # Vínculo com empresa terceirizada/prestadora (ADR-0002), mesma janela de
    # migração/retrocompatibilidade que legal_entity_id acima.
    outsourced_select = (
        ', employees.outsourced_company_id, employees.service_contract_id, '
        'employees.epi_responsibility_override, employees.epi_responsibility_override_reason'
    ) if 'outsourced_company_id' in table_columns(connection, 'employees') else ''
    sql = (
        'SELECT employees.id, employees.company_id, employees.unit_id, '
        'employees.employee_id_code, employees.cpf, employees.name, employees.email, '
        'employees.whatsapp, employees.preferred_contact_channel, employees.sector, '
        'employees.role_name, employees.admission_date, employees.schedule_type, '
        f'employees.tipo_vinculo, employees.empresa_origem{legal_entity_select}{outsourced_select}{status_field}, '
        'companies.name AS company_name, companies.cnpj AS company_cnpj, '
        'companies.logo_type, units.name AS unit_name, units.unit_type, '
        'units.city AS unit_city '
        'FROM employees '
        'JOIN companies ON companies.id = employees.company_id '
        'JOIN units ON units.id = employees.unit_id'
        + legal_entity_join
    )
    where = []
    params = []
    if lifecycle:
        placeholders = ', '.join(['?'] * len(NON_OPERATIONAL_STATUSES))
        where.append(f'employees.status NOT IN ({placeholders})')
        params.extend(NON_OPERATIONAL_STATUSES)
    if actor and actor['role'] != 'master_admin':
        where.append('employees.company_id = ?')
        params.append(actor['company_id'])
    if where:
        sql += ' WHERE ' + ' AND '.join(where)
    rows = connection.execute(sql + ' ORDER BY employees.name', tuple(params)).fetchall()
    employees = [row_to_dict(row) for row in rows]
    return apply_current_unit_allocation(connection, employees)


def fetch_employee_movements(connection, actor=None):
    sql = (
        'SELECT employee_unit_movements.*, '
        'employees.name AS employee_name, employees.employee_id_code, '
        'units.name AS unit_name, companies.name AS company_name '
        'FROM employee_unit_movements '
        'JOIN employees ON employees.id = employee_unit_movements.employee_id '
        'JOIN units ON units.id = employee_unit_movements.target_unit_id '
        'JOIN companies ON companies.id = employees.company_id'
    )
    if actor and actor['role'] != 'master_admin':
        rows = connection.execute(
            sql + ' WHERE employees.company_id = ? ORDER BY employee_unit_movements.start_date DESC',
            (actor['company_id'],),
        ).fetchall()
    else:
        rows = connection.execute(
            sql + ' ORDER BY employee_unit_movements.start_date DESC'
        ).fetchall()
    return [row_to_dict(row) for row in rows]


# ── Route-level SQL extractions ───────────────────────────────────────────────

def delete_employee(connection, employee_id):
    connection.execute('DELETE FROM employees WHERE id = ?', (int(employee_id),))


def close_temporary_unit_movements(connection, employee_id, start_date):
    connection.execute(
        "UPDATE employee_unit_movements SET end_date = ? WHERE employee_id = ? AND movement_type = 'temporary' AND COALESCE(NULLIF(end_date, ''), '9999-12-31') >= ?",
        (start_date, employee_id, start_date)
    )


def create_employee_unit_movement(connection, employee_id, company_id, source_unit_id, target_unit_id,
                                   movement_type, start_date, end_date, notes, actor_user_id, actor_name, created_at):
    connection.execute(
        (
            'INSERT INTO employee_unit_movements ('
            'employee_id, company_id, source_unit_id, target_unit_id, '
            'movement_type, start_date, end_date, notes, '
            'actor_user_id, actor_name, created_at'
            ') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        ),
        (employee_id, company_id, source_unit_id, target_unit_id,
         movement_type, start_date, end_date, notes, actor_user_id, actor_name, created_at)
    )


def update_employee_unit(connection, employee_id, unit_id):
    # Lotação operacional apenas. NUNCA altera legal_entity_id: transferência de
    # unidade não muda o vínculo jurídico do contrato de trabalho.
    connection.execute(
        'UPDATE employees SET unit_id = ? WHERE id = ?',
        (int(unit_id), int(employee_id))
    )


def transfer_employee_legal_entity(connection, employee_id, target_legal_entity_id, *,
                                   actor, reason, effective_date=''):
    """Processo administrativo de mudança de CNPJ do colaborador.

    O CNPJ representa o vínculo jurídico do contrato de trabalho e é imutável na
    edição comum do cadastro. Esta é a única via de alteração, e exige:

      - justificativa obrigatória (rastreabilidade trabalhista);
      - CNPJ de destino da mesma empresa e ativo;
      - registro em ``employee_legal_entity_movements`` (histórico preservado);
      - auditoria em ``company_audit_logs`` com o CNPJ afetado.

    A lotação operacional (unidade) não é tocada — ela segue seus próprios
    fluxos de transferência.
    """
    from datetime import date, datetime, timezone

    from core.audit import register_company_audit
    from modules.legal_entities.service import get_legal_entity_by_id

    justification = str(reason or '').strip()
    if not justification:
        raise ValueError('Justificativa é obrigatória para alterar o CNPJ do colaborador.')

    employee = get_employee_by_id(connection, int(employee_id))
    if not employee:
        raise ValueError('Colaborador não encontrado.')
    company_id = int(employee['company_id'])

    target = get_legal_entity_by_id(connection, int(target_legal_entity_id))
    if not target or int(target['company_id']) != company_id:
        raise ValueError('CNPJ de destino não pertence à empresa do colaborador.')
    if not int(target.get('active', 1)):
        raise ValueError('CNPJ de destino está inativo.')

    source_id = employee.get('legal_entity_id')
    if source_id and int(source_id) == int(target_legal_entity_id):
        raise ValueError('O colaborador já pertence a este CNPJ.')

    now_iso = datetime.now(timezone.utc).isoformat()
    effective = str(effective_date or '').strip() or date.today().isoformat()
    connection.execute(
        'INSERT INTO employee_legal_entity_movements ('
        'employee_id, company_id, source_legal_entity_id, target_legal_entity_id, '
        'reason, effective_date, actor_user_id, actor_name, created_at'
        ') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            int(employee_id), company_id,
            int(source_id) if source_id else None, int(target_legal_entity_id),
            justification, effective,
            int(actor['id']), str(actor.get('full_name') or ''), now_iso,
        ),
    )
    connection.execute(
        'UPDATE employees SET legal_entity_id = ? WHERE id = ?',
        (int(target_legal_entity_id), int(employee_id)),
    )
    source = get_legal_entity_by_id(connection, int(source_id)) if source_id else None
    register_company_audit(
        connection, company_id, actor, 'employee_legal_entity_transfer',
        f"Vínculo jurídico de {employee.get('name')} alterado para o CNPJ {target.get('cnpj')}.",
        [
            {'field': 'CNPJ do colaborador',
             'before': str((source or {}).get('cnpj') or ''),
             'after': str(target.get('cnpj') or '')},
            {'field': 'Justificativa', 'before': '', 'after': justification},
            {'field': 'Vigência', 'before': '', 'after': effective},
        ],
        legal_entity_id=int(target_legal_entity_id),
    )
    connection.commit()
    return {
        'employee_id': int(employee_id),
        'source_legal_entity_id': int(source_id) if source_id else None,
        'target_legal_entity_id': int(target_legal_entity_id),
        'effective_date': effective,
    }


def fetch_employee_legal_entity_movements(connection, employee_id):
    """Histórico de vínculo jurídico do colaborador (mais recente primeiro)."""
    from epi_backend.db import table_exists
    if not table_exists(connection, 'employee_legal_entity_movements'):
        return []
    rows = connection.execute(
        'SELECT m.*, src.cnpj AS source_cnpj, tgt.cnpj AS target_cnpj, '
        'tgt.legal_name AS target_legal_name '
        'FROM employee_legal_entity_movements m '
        'LEFT JOIN legal_entities src ON src.id = m.source_legal_entity_id '
        'LEFT JOIN legal_entities tgt ON tgt.id = m.target_legal_entity_id '
        'WHERE m.employee_id = ? ORDER BY m.created_at DESC, m.id DESC',
        (int(employee_id),),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


# ── Arquivamento (Soft Delete) com retenção — mesma política das Unidades ────

def get_employee_lifecycle(connection, employee_id):
    """Colaborador com os campos de ciclo de vida (para fluxos de arquivo)."""
    from core.archival import LIFECYCLE_FIELD_NAMES, lifecycle_enabled
    extra = (', ' + ', '.join(LIFECYCLE_FIELD_NAMES)) if lifecycle_enabled(connection, 'employees') else ''
    row = connection.execute(
        f'SELECT id, company_id, unit_id, employee_id_code, cpf, name{extra} '
        'FROM employees WHERE id = ?',
        (int(employee_id),),
    ).fetchone()
    return row_to_dict(row) if row else None


def ensure_employee_operational(connection, employee_id, operation='esta operação'):
    from core.archival import ensure_record_operational
    ensure_record_operational(connection, 'employees', employee_id, 'Colaborador', operation)


def fetch_archived_employees(connection, actor, *, outsourced_only=False):
    """Colaboradores arquivados do tenant, com dados de retenção para a UI.

    `outsourced_only` (ADR-0002 §10.4): filtra só terceirizado/prestador
    (tipo_vinculo != 'CLT') — usado pela aba "Colaboradores Arquivados" do
    Cadastro de Colaboradores. Nenhuma rota nova: mesmo fetch_archived_employees
    já usado pela tela geral de Colaboradores, só com um filtro a mais.
    """
    from core.archival import STATUS_ARCHIVED, STATUS_PENDING_DELETION, retention_days_remaining
    from epi_backend.db import table_columns
    outsourced_cols = (
        ', employees.tipo_vinculo, employees.outsourced_company_id, '
        'outsourced_companies.legal_name AS outsourced_company_name'
    ) if 'outsourced_company_id' in table_columns(connection, 'employees') else ''
    outsourced_join = (
        ' LEFT JOIN outsourced_companies ON outsourced_companies.id = employees.outsourced_company_id'
    ) if outsourced_cols else ''
    sql = (
        'SELECT employees.id, employees.company_id, employees.unit_id, '
        'employees.employee_id_code, employees.name, employees.sector, employees.role_name, '
        'employees.status, employees.archived_at, employees.archived_by, '
        'employees.archive_reason, employees.retention_until, employees.legal_hold, '
        f'companies.name AS company_name, units.name AS unit_name, '
        f'users.full_name AS archived_by_name{outsourced_cols} '
        'FROM employees '
        'JOIN companies ON companies.id = employees.company_id '
        'LEFT JOIN units ON units.id = employees.unit_id '
        'LEFT JOIN users ON users.id = employees.archived_by'
        f'{outsourced_join} '
        'WHERE employees.status IN (?, ?)'
    )
    params = [STATUS_ARCHIVED, STATUS_PENDING_DELETION]
    if actor and actor['role'] != 'master_admin':
        sql += ' AND employees.company_id = ?'
        params.append(actor['company_id'])
    if outsourced_only and outsourced_cols:
        sql += " AND employees.tipo_vinculo != 'CLT'"
    rows = connection.execute(sql + ' ORDER BY employees.archived_at DESC', tuple(params)).fetchall()
    result = []
    for row in rows:
        item = row_to_dict(row)
        item['retention_days_remaining'] = retention_days_remaining(item.get('retention_until'))
        result.append(item)
    return result


def summarize_employee_history(connection, employee_id):
    """Resumo do que será removido na exclusão definitiva do colaborador."""
    from core.archival import count_where
    employee_id = int(employee_id)
    return {
        'deliveries': count_where(connection, 'deliveries', 'employee_id = ?', (employee_id,)),
        'devolutions': count_where(connection, 'epi_devolutions', 'employee_id = ?', (employee_id,)),
        'epi_requests': count_where(connection, 'epi_requests', 'employee_id = ?', (employee_id,)),
        'feedbacks': count_where(connection, 'epi_feedbacks', 'employee_id = ?', (employee_id,)),
        'ficha_periods': count_where(connection, 'epi_ficha_periods', 'employee_id = ?', (employee_id,)),
        'ficha_items': count_where(connection, 'epi_ficha_items', 'employee_id = ?', (employee_id,)),
        'unit_movements': count_where(connection, 'employee_unit_movements', 'employee_id = ?', (employee_id,)),
        'portal_links': count_where(connection, 'employee_portal_links', 'employee_id = ?', (employee_id,)),
        'portal_audit_logs': count_where(connection, 'employee_portal_audit_logs', 'employee_id = ?', (employee_id,)),
    }


def purge_employee_history(connection, employee_id):
    """Expurga os dados operacionais do colaborador (tombstone permanece).

    Chamado apenas pela etapa 2 da exclusão definitiva, após a retenção.
    """
    from core.archival import delete_where
    employee_id = int(employee_id)
    request_ids = [
        int(row['id'])
        for row in connection.execute(
            'SELECT id FROM epi_requests WHERE employee_id = ?', (employee_id,)
        ).fetchall()
    ]
    if request_ids:
        placeholders = ','.join(['?'] * len(request_ids))
        delete_where(connection, 'epi_request_history', f'request_id IN ({placeholders})', tuple(request_ids))
    feedback_ids = [
        int(row['id'])
        for row in connection.execute(
            'SELECT id FROM epi_feedbacks WHERE employee_id = ?', (employee_id,)
        ).fetchall()
    ]
    if feedback_ids:
        placeholders = ','.join(['?'] * len(feedback_ids))
        delete_where(connection, 'epi_feedback_history', f'feedback_id IN ({placeholders})', tuple(feedback_ids))
    for table in (
        'epi_requests', 'epi_feedbacks', 'epi_devolutions', 'deliveries',
        'epi_ficha_items', 'epi_ficha_periods', 'ficha_epi_snapshots',
        'ficha_epi_audit_log', 'employee_unit_movements',
        'employee_portal_audit_logs', 'employee_portal_links',
        'purchase_role_unit_links',
    ):
        delete_where(connection, table, 'employee_id = ?', (employee_id,))
    delete_where(connection, 'users', 'linked_employee_id = ?', (employee_id,))
