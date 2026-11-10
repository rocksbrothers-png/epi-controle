"""Ficha 360° de EPI — F1: identificação, responsáveis e indicadores operacionais.

Somente leitura. Recebe um colaborador JÁ autorizado por
``contract.resolve_authorized_employee`` e monta o resumo da Ficha numa única
resposta (um endpoint, uma conexão): a tela abre com uma requisição só.

O que este módulo faz questão de NÃO fazer:

* **Não inventa gestor.** Não existe "gestor direto do colaborador" no
  cadastro. Os responsáveis são derivados da unidade atual (Administrador
  Local e Gestor de EPI cuja unidade operacional é a do colaborador) e da
  empresa (Administrador Geral e Administrador de Registro). Lista vazia é
  mostrada como vazia (DF-1).
* **Não soma estados diferentes.** "Pendentes" vem com o detalhamento por
  estado canônico da máquina de solicitações; nada de um total sem origem.
* **Não recalcula troca.** A próxima troca é a data gravada na entrega.
* **Não devolve dado pessoal desnecessário.** Sem CPF, e-mail, WhatsApp,
  assinatura ou foto; dos responsáveis, só nome e papel.
* **Não fala de custo.** Custos são da F5.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from core.permissions import PERM_DELIVERIES_VIEW
from core.roles import normalize_role_name
from epi_backend.db import row_to_dict, table_columns, table_exists
from modules.deliveries.visibility import active_delivery_sql
from modules.epis.request_states import (
    ALL_STATUSES,
    SPEC_CODE,
    TERMINAL_STATUSES,
    normalize_status,
)

UNIT_RESPONSIBLE_ROLES = ('admin', 'user')
COMPANY_RESPONSIBLE_ROLES = ('general_admin', 'registry_admin')
_RESPONSIBLE_ROLE_ORDER = {'admin': 0, 'user': 1, 'general_admin': 2, 'registry_admin': 3}
# Grafias gravadas em ``users.role`` que normalizam para um dos papéis acima
# (``core.roles.ROLE_ALIASES``). Filtrar no SQL evita trazer contas de
# colaborador/comprador só para descartá-las em Python.
_RESPONSIBLE_ROLE_SPELLINGS = (
    'admin', 'local_admin', 'admin_local',
    'user', 'epi_manager', 'gestor_epi', 'gestor_de_epi', 'gestor', 'manager',
    'general_admin', 'generaladmin', 'registry_admin', 'registryadmin',
)
UNKNOWN_STATUS_CODE = 'UNKNOWN'


def _text(value) -> str:
    return str(value or '').strip()


def _has_permission(actor, permission) -> bool:
    from core.auth import ensure_permission
    try:
        ensure_permission(actor, permission)
    except PermissionError:
        return False
    return True


def _today() -> str:
    # Mesma data de referência de ``actor_operational_unit_id`` (core.repository):
    # escopo do ator e unidade do colaborador precisam concordar sobre "hoje".
    return date.today().isoformat()  # noqa: DTZ011


def _current_units_by_employee(connection, employee_ids):
    """Unidade operacional atual de cada colaborador (alocação temporária vigente
    vence a unidade base) — mesma regra de ``actor_operational_unit_id``, em lote."""
    ids = sorted({int(i) for i in employee_ids if i})
    if not ids:
        return {}
    placeholders = ','.join('?' for _ in ids)
    base = {
        int(row['id']): int(row['unit_id'] or 0)
        for row in connection.execute(
            f'SELECT id, unit_id FROM employees WHERE id IN ({placeholders})', tuple(ids)
        ).fetchall()
    }
    if table_exists(connection, 'employee_unit_movements'):
        today = _today()
        rows = connection.execute(
            'SELECT employee_id, target_unit_id FROM employee_unit_movements '
            f"WHERE employee_id IN ({placeholders}) AND movement_type = 'temporary' "
            "AND start_date <= ? AND COALESCE(NULLIF(end_date, ''), '9999-12-31') >= ? "
            'ORDER BY employee_id, start_date DESC, id DESC',
            (*ids, today, today),
        ).fetchall()
        seen = set()
        for row in rows:
            employee_id = int(row['employee_id'])
            if employee_id in seen:
                continue
            seen.add(employee_id)
            base[employee_id] = int(row['target_unit_id'] or 0)
    return base


def _lifecycle(connection, employee_id) -> str:
    cols = set(table_columns(connection, 'employees'))
    wanted = [c for c in ('status', 'archived_at', 'deleted_at') if c in cols]
    if not wanted:
        return 'active'
    row = connection.execute(
        f"SELECT {', '.join(wanted)} FROM employees WHERE id = ?", (int(employee_id),)
    ).fetchone()
    item = row_to_dict(row) if row else {}
    if _text(item.get('deleted_at')):
        return 'deleted'
    if _text(item.get('archived_at')) or _text(item.get('status')).lower() == 'archived':
        return 'archived'
    return 'active'


def is_deleted(connection, employee) -> bool:
    """Colaborador excluído (anonimizado) não tem Ficha: a rota responde como
    inexistente, sem revelar que o registro existiu."""
    return _lifecycle(connection, employee['id']) == 'deleted'


def _unit_names(connection, company_id, unit_ids):
    ids = sorted({int(i) for i in unit_ids if i})
    if not ids:
        return {}
    placeholders = ','.join('?' for _ in ids)
    return {
        int(row['id']): _text(row['name'])
        for row in connection.execute(
            f'SELECT id, name FROM units WHERE company_id = ? AND id IN ({placeholders})',
            (int(company_id), *ids),
        ).fetchall()
    }


def _legal_entity(connection, company_id, legal_entity_id):
    if not legal_entity_id or not table_exists(connection, 'legal_entities'):
        return None
    row = connection.execute(
        'SELECT legal_name, trade_name, cnpj FROM legal_entities WHERE id = ? AND company_id = ?',
        (int(legal_entity_id), int(company_id)),
    ).fetchone()
    if not row:
        return None
    item = row_to_dict(row)
    return {
        'name': _text(item.get('trade_name')) or _text(item.get('legal_name')),
        'legal_name': _text(item.get('legal_name')),
        'cnpj': _text(item.get('cnpj')),
    }


def _contracted_workforce(connection, employee):
    """Empresa terceirizada e contrato — só para vínculo contratado e só dentro
    da empresa do colaborador (o vínculo nunca atravessa tenant)."""
    from modules.employees.service import is_contracted_workforce

    tipo = _text(employee.get('tipo_vinculo'))
    if not is_contracted_workforce(tipo):
        return None
    company_id = int(employee['company_id'])
    result = {'outsourced_company': None, 'contract': None, 'origin_name': _text(employee.get('empresa_origem'))}
    outsourced_id = employee.get('outsourced_company_id')
    if outsourced_id and table_exists(connection, 'outsourced_companies'):
        row = connection.execute(
            'SELECT legal_name, trade_name, cnpj FROM outsourced_companies WHERE id = ? AND company_id = ?',
            (int(outsourced_id), company_id),
        ).fetchone()
        if row:
            item = row_to_dict(row)
            result['outsourced_company'] = {
                'name': _text(item.get('trade_name')) or _text(item.get('legal_name')),
                'legal_name': _text(item.get('legal_name')),
                'cnpj': _text(item.get('cnpj')),
            }
            contract_id = employee.get('service_contract_id')
            if contract_id and table_exists(connection, 'service_contracts'):
                crow = connection.execute(
                    'SELECT contract_ref, start_date, end_date, status FROM service_contracts '
                    'WHERE id = ? AND company_id = ? AND outsourced_company_id = ?',
                    (int(contract_id), company_id, int(outsourced_id)),
                ).fetchone()
                if crow:
                    citem = row_to_dict(crow)
                    result['contract'] = {
                        'ref': _text(citem.get('contract_ref')),
                        'start_date': _text(citem.get('start_date')),
                        'end_date': _text(citem.get('end_date')),
                        'status': _text(citem.get('status')),
                    }
    return result


def _responsibles(connection, company_id, current_unit_id):
    """DF-1: responsáveis DERIVADOS — nunca um "gestor direto" inventado."""
    placeholders = ','.join('?' for _ in _RESPONSIBLE_ROLE_SPELLINGS)
    has_link = 'linked_employee_id' in set(table_columns(connection, 'users'))
    link_col = ', linked_employee_id' if has_link else ''
    rows = connection.execute(
        f'SELECT id, full_name, username, role{link_col} FROM users '
        f'WHERE company_id = ? AND COALESCE(active, 1) = 1 AND LOWER(role) IN ({placeholders})',
        (int(company_id), *_RESPONSIBLE_ROLE_SPELLINGS),
    ).fetchall()
    users = []
    for row in rows:
        item = row_to_dict(row)
        role = normalize_role_name(item.get('role'))
        if role not in _RESPONSIBLE_ROLE_ORDER:
            continue
        users.append({**item, 'role': role})
    linked = [u.get('linked_employee_id') for u in users if u['role'] in UNIT_RESPONSIBLE_ROLES]
    units = _current_units_by_employee(connection, linked)
    unit_level, company_level = [], []
    for user in users:
        entry = {'role': user['role'], 'name': _text(user.get('full_name')) or _text(user.get('username'))}
        if user['role'] in UNIT_RESPONSIBLE_ROLES:
            linked_id = user.get('linked_employee_id')
            if current_unit_id and linked_id and units.get(int(linked_id)) == int(current_unit_id):
                unit_level.append(entry)
        elif user['role'] in COMPANY_RESPONSIBLE_ROLES:
            company_level.append(entry)

    def order(entry):
        return (_RESPONSIBLE_ROLE_ORDER[entry['role']], entry['name'].lower())

    return {'unit': sorted(unit_level, key=order), 'company': sorted(company_level, key=order)}


def _pending(connection, employee):
    """Solicitações não concluídas, detalhadas por estado canônico (SPEC_CODE)."""
    if not table_exists(connection, 'epi_requests'):
        return {'total': 0, 'by_status': []}
    rows = connection.execute(
        'SELECT status, COUNT(*) AS total FROM epi_requests '
        'WHERE company_id = ? AND employee_id = ? GROUP BY status',
        (int(employee['company_id']), int(employee['id'])),
    ).fetchall()
    counts = {}
    for row in rows:
        raw = _text(row['status'])
        # Linha sem status é lida como "solicitado" (mesma regra da máquina de
        # estados); valor preenchido e desconhecido é exposto como tal, não
        # escondido nem encaixado num estado conhecido.
        status = normalize_status(raw) if raw else ALL_STATUSES[0]
        if status in TERMINAL_STATUSES:
            continue
        code = SPEC_CODE.get(status, UNKNOWN_STATUS_CODE)
        counts[code] = counts.get(code, 0) + int(row['total'] or 0)
    order = [SPEC_CODE[s] for s in ALL_STATUSES] + [UNKNOWN_STATUS_CODE]
    by_status = [{'code': code, 'count': counts[code]} for code in order if counts.get(code)]
    return {'total': sum(item['count'] for item in by_status), 'by_status': by_status}


def _in_use(connection, employee):
    """Entregas em posse: não devolvidas e não revertidas (rollback lógico)."""
    if not table_exists(connection, 'deliveries'):
        return {'units': 0, 'products': 0, 'categories': 0, 'uncategorized_products': 0}, None
    base_where = (
        'd.company_id = ? AND d.employee_id = ? '
        "AND COALESCE(d.returned_date, '') = ''" + active_delivery_sql(connection, 'd')
    )
    params = (int(employee['company_id']), int(employee['id']))
    agg = row_to_dict(connection.execute(
        'SELECT COALESCE(SUM(COALESCE(d.quantity, 1)), 0) AS units, '
        'COUNT(DISTINCT d.epi_id) AS products, '
        "COUNT(DISTINCT CASE WHEN COALESCE(e.epi_section, '') <> '' THEN e.epi_section END) AS categories, "
        "COUNT(DISTINCT CASE WHEN COALESCE(e.epi_section, '') = '' THEN d.epi_id END) AS uncategorized_products "
        f'FROM deliveries d LEFT JOIN epis e ON e.id = d.epi_id WHERE {base_where}',
        params,
    ).fetchone())
    in_use = {key: int(agg.get(key) or 0) for key in ('units', 'products', 'categories', 'uncategorized_products')}

    today = _today()
    dated = f"{base_where} AND COALESCE(d.next_replacement_date, '') <> ''"
    nxt = connection.execute(
        'SELECT d.next_replacement_date, e.name AS epi_name '
        f'FROM deliveries d LEFT JOIN epis e ON e.id = d.epi_id WHERE {dated} '
        'ORDER BY d.next_replacement_date ASC, d.id ASC LIMIT 1',
        params,
    ).fetchone()
    if not nxt:
        return in_use, None
    overdue = connection.execute(
        f'SELECT COUNT(*) AS total FROM deliveries d WHERE {dated} AND d.next_replacement_date < ?',
        (*params, today),
    ).fetchone()
    item = row_to_dict(nxt)
    return in_use, {
        'date': _text(item.get('next_replacement_date'))[:10],
        'epi_name': _text(item.get('epi_name')),
        'overdue_count': int(overdue['total'] or 0),
    }


def build_employee_summary(connection, actor, employee) -> dict:
    """Resumo da Ficha (F1). ``employee`` já passou pelo contrato da F0."""
    from modules.employees.service import get_employee_current_unit

    company_id = int(employee['company_id'])
    base_unit_id = int(employee.get('unit_id') or 0)
    current_unit_id = int(get_employee_current_unit(connection, int(employee['id'])) or base_unit_id or 0)
    unit_names = _unit_names(connection, company_id, (base_unit_id, current_unit_id))
    company = connection.execute('SELECT id, name FROM companies WHERE id = ?', (company_id,)).fetchone()

    identity = {
        'id': int(employee['id']),
        'name': _text(employee.get('name')),
        'registration': _text(employee.get('employee_id_code')),
        'job_title': _text(employee.get('role_name')),
        'sector': _text(employee.get('sector')),
        'employment_type': _text(employee.get('tipo_vinculo')) or 'CLT',
        'lifecycle': _lifecycle(connection, employee['id']),
        'company': {'id': company_id, 'name': _text(company['name']) if company else ''},
        'unit': {
            'id': current_unit_id or None,
            'name': unit_names.get(current_unit_id, ''),
            'temporary_allocation': bool(base_unit_id and current_unit_id and current_unit_id != base_unit_id),
            'base_unit_name': unit_names.get(base_unit_id, '') if current_unit_id != base_unit_id else '',
        },
        'legal_entity': _legal_entity(connection, company_id, employee.get('legal_entity_id')),
        'contracted_workforce': _contracted_workforce(connection, employee),
    }

    if _has_permission(actor, PERM_DELIVERIES_VIEW):
        in_use, next_replacement = _in_use(connection, employee)
        indicators = {
            'pending_requests': _pending(connection, employee),
            'next_replacement': next_replacement,
            'in_use': in_use,
        }
    else:
        indicators = None  # seção sem permissão: ausente, nunca "0"

    return {
        'employee': identity,
        'responsibles': _responsibles(connection, company_id, current_unit_id),
        'indicators': indicators,
        'generated_at': datetime.now(UTC).isoformat(),
    }


__all__ = ['UNKNOWN_STATUS_CODE', 'build_employee_summary', 'is_deleted']
