"""Serviços de unidades operacionais."""

import json
from datetime import datetime, timezone

from core.schema import _col_exists
from epi_backend.db import row_to_dict

# Ciclo de vida da unidade. 'deleted' é o tombstone que permanece após a
# exclusão definitiva: o registro da unidade nunca sai fisicamente do banco,
# apenas seus dados operacionais dependentes são expurgados após a retenção.
UNIT_STATUS_ACTIVE = 'active'
UNIT_STATUS_INACTIVE = 'inactive'
UNIT_STATUS_ARCHIVED = 'archived'
UNIT_STATUS_PENDING_DELETION = 'pending_deletion'
UNIT_STATUS_DELETED = 'deleted'
UNIT_STATUSES = (
    UNIT_STATUS_ACTIVE,
    UNIT_STATUS_INACTIVE,
    UNIT_STATUS_ARCHIVED,
    UNIT_STATUS_PENDING_DELETION,
    UNIT_STATUS_DELETED,
)
# Estados que bloqueiam qualquer nova operação (entregas, estoque, compras,
# requisições e novos colaboradores). Consultas e relatórios seguem liberados.
UNIT_NON_OPERATIONAL_STATUSES = (
    UNIT_STATUS_ARCHIVED,
    UNIT_STATUS_PENDING_DELETION,
    UNIT_STATUS_DELETED,
)

# Retenção mínima legal exigida pela política de arquivamento (anos).
UNIT_MIN_RETENTION_YEARS = 5


def normalize_unit_type(value):
    raw = str(value or '').strip().lower()
    aliases = {
        'navio': 'embarcacao',
        'embarcação': 'embarcacao',
        'embarcacao': 'embarcacao',
        'base': 'base',
        'plataforma': 'plataforma',
    }
    return aliases.get(raw, raw or 'base')


def unit_lifecycle_enabled(connection):
    """Indica se as colunas de ciclo de vida já existem (bancos legados/tests)."""
    return _col_exists(connection, 'units', 'status')


def fetch_units(connection, actor=None, include_archived=False):
    from epi_backend.db import table_columns
    lifecycle = unit_lifecycle_enabled(connection)
    status_fields = ', units.status, units.archived_at, units.retention_until' if lifecycle else ''
    # Vínculo da unidade com o CNPJ: alimenta o filtro em cascata do dashboard
    # (Empresa → CNPJ → Unidade → Setor). Ausente durante a janela de migração.
    legal_entity_field = (
        ', units.legal_entity_id' if 'legal_entity_id' in table_columns(connection, 'units') else ''
    )
    sql = (
        f'SELECT units.id, units.company_id, units.name, units.unit_type, units.city, '
        f'units.notes{legal_entity_field}{status_fields}, '
        'companies.name AS company_name, companies.cnpj AS company_cnpj, companies.logo_type '
        'FROM units JOIN companies ON companies.id = units.company_id'
    )
    where = []
    params = []
    if lifecycle and not include_archived:
        placeholders = ', '.join(['?'] * len(UNIT_NON_OPERATIONAL_STATUSES))
        where.append(f'units.status NOT IN ({placeholders})')
        params.extend(UNIT_NON_OPERATIONAL_STATUSES)
    if actor and actor['role'] != 'master_admin':
        where.append('units.company_id = ?')
        params.append(actor['company_id'])
    if where:
        sql += ' WHERE ' + ' AND '.join(where)
    rows = connection.execute(sql + ' ORDER BY companies.name, units.name', tuple(params)).fetchall()
    return [row_to_dict(row) for row in rows]


def get_unit_by_id(connection, unit_id):
    lifecycle_fields = (
        ', status, archived_at, archived_by, archive_reason, retention_until, '
        'legal_hold, legal_hold_reason, deleted_at, deleted_by, delete_reason'
        if unit_lifecycle_enabled(connection) else ''
    )
    row = connection.execute(
        f'SELECT id, company_id, name, unit_type, city, notes{lifecycle_fields} FROM units WHERE id = ?',
        (unit_id,),
    ).fetchone()
    return row_to_dict(row) if row else None


def get_unit_status(connection, unit_id):
    """Status do ciclo de vida; 'active' quando o schema legado não tem a coluna."""
    if not unit_lifecycle_enabled(connection):
        return UNIT_STATUS_ACTIVE
    row = connection.execute('SELECT status FROM units WHERE id = ?', (int(unit_id),)).fetchone()
    if not row:
        return None
    return str(dict(row).get('status') or UNIT_STATUS_ACTIVE)


def ensure_unit_operational(connection, unit_id, operation='esta operação'):
    """Bloqueia novas operações em unidades arquivadas/em exclusão.

    Consultas, relatórios e auditorias não passam por aqui — apenas os fluxos
    de escrita operacional (colaboradores, entregas, estoque, compras,
    requisições) devem chamar este guard.
    """
    if not unit_id:
        return
    status = get_unit_status(connection, int(unit_id))
    if status in UNIT_NON_OPERATIONAL_STATUSES:
        raise ValueError(
            f'Unidade arquivada: não é permitido registrar {operation}. '
            'O histórico permanece disponível apenas para consulta, relatórios e auditoria.'
        )


def get_unit_active_jv_name(connection, unit_id):
    if not unit_id:
        return ''
    row = connection.execute(
        'SELECT joint_venture_name FROM unit_joint_venture_periods '
        'WHERE unit_id = ? AND ended_at IS NULL '
        'ORDER BY started_at DESC LIMIT 1',
        (int(unit_id),),
    ).fetchone()
    if not row:
        return ''
    return str(dict(row).get('joint_venture_name') or '').strip()


def delete_epi_dependencies(connection, epi_id):
    epi_id = int(epi_id)
    connection.execute(
        'DELETE FROM epi_stock_item_reprints WHERE stock_item_id IN (SELECT id FROM epi_stock_items WHERE epi_id = ?)',
        (epi_id,)
    )
    connection.execute('DELETE FROM epi_stock_items WHERE epi_id = ?', (epi_id,))
    connection.execute('DELETE FROM stock_movements WHERE epi_id = ?', (epi_id,))
    connection.execute('DELETE FROM unit_epi_stock WHERE epi_id = ?', (epi_id,))
    connection.execute('DELETE FROM epi_ficha_items WHERE epi_id = ?', (epi_id,))
    connection.execute('DELETE FROM deliveries WHERE epi_id = ?', (epi_id,))
    request_ids = [
        int(row['id'])
        for row in connection.execute('SELECT id FROM epi_requests WHERE epi_id = ?', (epi_id,)).fetchall()
    ]
    if request_ids:
        connection.execute(
            f"DELETE FROM epi_request_history WHERE request_id IN ({','.join(['?'] * len(request_ids))})",
            tuple(request_ids)
        )
    connection.execute('DELETE FROM epi_requests WHERE epi_id = ?', (epi_id,))
    feedback_ids = [
        int(row['id'])
        for row in connection.execute('SELECT id FROM epi_feedbacks WHERE epi_id = ?', (epi_id,)).fetchall()
    ]
    if feedback_ids:
        connection.execute(
            f"DELETE FROM epi_feedback_history WHERE feedback_id IN ({','.join(['?'] * len(feedback_ids))})",
            tuple(feedback_ids)
        )
    connection.execute('DELETE FROM epi_feedbacks WHERE epi_id = ?', (epi_id,))
    connection.execute('DELETE FROM epis WHERE id = ?', (epi_id,))


def delete_unit_dependencies(connection, unit_id):
    unit_id = int(unit_id)
    scoped_epi_ids = [
        int(row['id'])
        for row in connection.execute('SELECT id FROM epis WHERE unit_id = ?', (unit_id,)).fetchall()
    ]
    for epi_id in scoped_epi_ids:
        delete_epi_dependencies(connection, epi_id)
    connection.execute(
        'DELETE FROM epi_stock_item_reprints WHERE stock_item_id IN (SELECT id FROM epi_stock_items WHERE unit_id = ?)',
        (unit_id,)
    )
    connection.execute('DELETE FROM epi_stock_items WHERE unit_id = ?', (unit_id,))
    connection.execute('DELETE FROM stock_movements WHERE unit_id = ?', (unit_id,))
    connection.execute('DELETE FROM unit_epi_stock WHERE unit_id = ?', (unit_id,))
    request_ids = [
        int(row['id'])
        for row in connection.execute('SELECT id FROM epi_requests WHERE unit_id = ?', (unit_id,)).fetchall()
    ]
    if request_ids:
        connection.execute(
            f"DELETE FROM epi_request_history WHERE request_id IN ({','.join(['?'] * len(request_ids))})",
            tuple(request_ids)
        )
    connection.execute('DELETE FROM epi_requests WHERE unit_id = ?', (unit_id,))
    ficha_item_ids = [
        int(row['id'])
        for row in connection.execute('SELECT id FROM epi_ficha_items WHERE unit_id = ?', (unit_id,)).fetchall()
    ]
    if ficha_item_ids:
        connection.execute('DELETE FROM epi_ficha_items WHERE unit_id = ?', (unit_id,))
    connection.execute('DELETE FROM epi_ficha_periods WHERE unit_id = ?', (unit_id,))
    feedback_ids = [
        int(row['id'])
        for row in connection.execute('SELECT id FROM epi_feedbacks WHERE unit_id = ?', (unit_id,)).fetchall()
    ]
    if feedback_ids:
        connection.execute(
            f"DELETE FROM epi_feedback_history WHERE feedback_id IN ({','.join(['?'] * len(feedback_ids))})",
            tuple(feedback_ids)
        )
    connection.execute('DELETE FROM epi_feedbacks WHERE unit_id = ?', (unit_id,))
    connection.execute('DELETE FROM deliveries WHERE unit_id = ?', (unit_id,))
    connection.execute(
        'DELETE FROM employee_unit_movements WHERE source_unit_id = ? OR target_unit_id = ?',
        (unit_id, unit_id)
    )
    employee_ids = [
        int(row['id'])
        for row in connection.execute('SELECT id FROM employees WHERE unit_id = ?', (unit_id,)).fetchall()
    ]
    if employee_ids:
        # O nome correto da tabela é employee_portal_audit_logs; a referência
        # legada a employee_portal_audit quebrava o DELETE em Postgres.
        from core.schema import _table_exists
        for portal_audit_table in ('employee_portal_audit_logs', 'employee_portal_audit'):
            if _table_exists(connection, portal_audit_table):
                connection.execute(
                    f"DELETE FROM {portal_audit_table} WHERE employee_id IN ({','.join(['?'] * len(employee_ids))})",
                    tuple(employee_ids)
                )
        connection.execute(
            f"DELETE FROM employee_portal_links WHERE employee_id IN ({','.join(['?'] * len(employee_ids))})",
            tuple(employee_ids)
        )
        connection.execute(
            f"DELETE FROM users WHERE linked_employee_id IN ({','.join(['?'] * len(employee_ids))})",
            tuple(employee_ids)
        )
        connection.execute(
            f"DELETE FROM employees WHERE id IN ({','.join(['?'] * len(employee_ids))})",
            tuple(employee_ids)
        )


# ── Route-level SQL extractions ───────────────────────────────────────────────

def _resolve_unit_legal_entity(connection, company_id, legal_entity_id):
    """Valida o CNPJ informado para a unidade. Devolve ``None`` quando o schema
    Multi-CNPJ ainda não existe ou quando nada foi informado — nesses casos a
    coluna simplesmente não entra na escrita (retrocompatível)."""
    if legal_entity_id in (None, '', 0, '0'):
        return None
    from modules.legal_entities.service import get_legal_entity_by_id, legal_entities_ready
    if not legal_entities_ready(connection):
        return None
    entity = get_legal_entity_by_id(connection, int(legal_entity_id))
    if not entity or int(entity['company_id']) != int(company_id):
        raise ValueError('CNPJ informado não pertence a esta empresa.')
    return int(legal_entity_id)


def create_unit(connection, company_id, name, unit_type, city, notes, *, legal_entity_id=None):
    columns = ['company_id', 'name', 'unit_type', 'city', 'notes']
    values = [company_id, name, unit_type, city, notes]
    resolved = _resolve_unit_legal_entity(connection, company_id, legal_entity_id)
    if resolved is not None:
        columns.append('legal_entity_id')
        values.append(resolved)
    placeholders = ', '.join(['?'] * len(values))
    cursor = connection.execute(
        f"INSERT INTO units ({', '.join(columns)}) VALUES ({placeholders})",
        tuple(values)
    )
    return cursor.lastrowid


def update_unit(connection, unit_id, company_id, name, unit_type, city, notes, *, legal_entity_id=None):
    assignments = ['company_id = ?', 'name = ?', 'unit_type = ?', 'city = ?', 'notes = ?']
    values = [company_id, name, unit_type, city, notes]
    resolved = _resolve_unit_legal_entity(connection, company_id, legal_entity_id)
    if resolved is not None:
        assignments.append('legal_entity_id = ?')
        values.append(resolved)
    connection.execute(
        f"UPDATE units SET {', '.join(assignments)} WHERE id = ?",
        tuple(values + [int(unit_id)])
    )


def delete_unit(connection, unit_id):
    connection.execute('DELETE FROM units WHERE id = ?', (int(unit_id),))


def start_unit_jv(connection, company_id, unit_id, jv_name, started_at, actor_id):
    connection.execute(
        'INSERT INTO unit_joint_venture_periods (company_id, unit_id, joint_venture_name, started_at, created_by) '
        'VALUES (?, ?, ?, ?, ?)',
        (int(company_id), int(unit_id), jv_name, started_at, str(actor_id))
    )


def end_unit_jv(connection, unit_id, ended_at):
    connection.execute(
        'UPDATE unit_joint_venture_periods SET ended_at = ? WHERE unit_id = ? AND ended_at IS NULL',
        (ended_at, int(unit_id))
    )


# ── Arquivamento (Soft Delete) e política de retenção ─────────────────────────

def _now_utc():
    return datetime.now(timezone.utc)


def _now_iso():
    return _now_utc().isoformat(timespec='seconds')


def _add_years(moment, years):
    try:
        return moment.replace(year=moment.year + int(years))
    except ValueError:  # 29/fev em ano não bissexto
        return moment.replace(year=moment.year + int(years), day=28)


def get_company_retention_years(connection, company_id):
    """Retenção configurável por tenant, nunca abaixo do mínimo legal (5 anos)."""
    if _col_exists(connection, 'companies', 'unit_retention_years'):
        row = connection.execute(
            'SELECT unit_retention_years FROM companies WHERE id = ?',
            (int(company_id),),
        ).fetchone()
        if row:
            configured = int(dict(row).get('unit_retention_years') or 0)
            if configured >= UNIT_MIN_RETENTION_YEARS:
                return configured
    return UNIT_MIN_RETENTION_YEARS


def set_company_retention_years(connection, company_id, years):
    years = int(years)
    if years < UNIT_MIN_RETENTION_YEARS:
        raise ValueError(
            f'O período de retenção não pode ser inferior a {UNIT_MIN_RETENTION_YEARS} anos.'
        )
    connection.execute(
        'UPDATE companies SET unit_retention_years = ? WHERE id = ?',
        (years, int(company_id)),
    )
    return years


def register_unit_audit(connection, company_id, actor, action_type, summary, details=None):
    """Trilha de auditoria permanente do ciclo de vida da unidade.

    Reutiliza company_audit_logs (mesma trilha exibida em Empresas), que nunca
    é apagada pelo expurgo de unidade — é o registro que sobrevive à exclusão
    definitiva.
    """
    connection.execute(
        'INSERT INTO company_audit_logs '
        '(company_id, actor_user_id, actor_name, action_type, summary, details_json, created_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?)',
        (
            int(company_id),
            int(actor['id']),
            str(actor.get('full_name') or ''),
            action_type,
            summary,
            json.dumps(details or {}, ensure_ascii=False),
            _now_iso(),
        ),
    )


def archive_unit(connection, unit, actor, reason='', ip=''):
    """Arquiva a unidade preservando todo o histórico (soft delete).

    Nenhum registro vinculado é tocado: colaboradores, entregas, estoque,
    compras, requisições, avaliações e logs permanecem íntegros e consultáveis.
    """
    status = str(unit.get('status') or UNIT_STATUS_ACTIVE)
    if status in UNIT_NON_OPERATIONAL_STATUSES:
        raise ValueError('Unidade já está arquivada ou em processo de exclusão.')
    retention_years = get_company_retention_years(connection, unit['company_id'])
    now = _now_utc()
    retention_until = _add_years(now, retention_years)
    reason = str(reason or '').strip() or 'Arquivamento solicitado pelo usuário (substitui exclusão).'
    connection.execute(
        'UPDATE units SET status = ?, archived_at = ?, archived_by = ?, archive_reason = ?, retention_until = ? '
        'WHERE id = ?',
        (
            UNIT_STATUS_ARCHIVED,
            now.isoformat(timespec='seconds'),
            int(actor['id']),
            reason,
            retention_until.isoformat(timespec='seconds'),
            int(unit['id']),
        ),
    )
    register_unit_audit(
        connection, unit['company_id'], actor, 'unit_archived',
        f"Unidade \"{unit['name']}\" arquivada. Histórico preservado até {retention_until.date().isoformat()}.",
        {
            'unit_id': int(unit['id']),
            'unit_name': unit['name'],
            'reason': reason,
            'retention_years': retention_years,
            'retention_until': retention_until.isoformat(timespec='seconds'),
            'ip': str(ip or ''),
        },
    )
    return {
        'status': UNIT_STATUS_ARCHIVED,
        'archived_at': now.isoformat(timespec='seconds'),
        'retention_years': retention_years,
        'retention_until': retention_until.isoformat(timespec='seconds'),
    }


def restore_unit(connection, unit, actor, ip=''):
    status = str(unit.get('status') or UNIT_STATUS_ACTIVE)
    if status not in (UNIT_STATUS_ARCHIVED, UNIT_STATUS_PENDING_DELETION):
        raise ValueError('Apenas unidades arquivadas podem ser restauradas.')
    connection.execute(
        "UPDATE units SET status = ?, archived_at = NULL, archived_by = NULL, archive_reason = '', retention_until = NULL "
        'WHERE id = ?',
        (UNIT_STATUS_ACTIVE, int(unit['id'])),
    )
    register_unit_audit(
        connection, unit['company_id'], actor, 'unit_restored',
        f"Unidade \"{unit['name']}\" restaurada do arquivo e reativada.",
        {'unit_id': int(unit['id']), 'unit_name': unit['name'], 'ip': str(ip or '')},
    )


def set_unit_operational_status(connection, unit, actor, new_status, ip=''):
    """Alterna Ativa/Inativa. Arquivamento e exclusão têm fluxos próprios."""
    if new_status not in (UNIT_STATUS_ACTIVE, UNIT_STATUS_INACTIVE):
        raise ValueError("Status inválido. Use 'active' ou 'inactive'.")
    current = str(unit.get('status') or UNIT_STATUS_ACTIVE)
    if current in UNIT_NON_OPERATIONAL_STATUSES:
        raise ValueError('Unidade arquivada: restaure-a antes de alterar o status operacional.')
    connection.execute('UPDATE units SET status = ? WHERE id = ?', (new_status, int(unit['id'])))
    register_unit_audit(
        connection, unit['company_id'], actor, 'unit_status_changed',
        f"Unidade \"{unit['name']}\" marcada como {'ativa' if new_status == UNIT_STATUS_ACTIVE else 'inativa'}.",
        {'unit_id': int(unit['id']), 'from': current, 'to': new_status, 'ip': str(ip or '')},
    )


def set_unit_legal_hold(connection, unit, actor, hold, reason='', ip=''):
    """Bloqueio jurídico/auditoria: impede exclusão definitiva enquanto ativo."""
    hold = 1 if hold else 0
    reason = str(reason or '').strip()
    if hold and not reason:
        raise ValueError('Informe o motivo do bloqueio jurídico.')
    connection.execute(
        'UPDATE units SET legal_hold = ?, legal_hold_reason = ? WHERE id = ?',
        (hold, reason if hold else '', int(unit['id'])),
    )
    register_unit_audit(
        connection, unit['company_id'], actor,
        'unit_legal_hold_set' if hold else 'unit_legal_hold_cleared',
        f"Bloqueio jurídico {'aplicado' if hold else 'removido'} na unidade \"{unit['name']}\".",
        {'unit_id': int(unit['id']), 'reason': reason, 'ip': str(ip or '')},
    )


def fetch_archived_units(connection, actor):
    """Unidades arquivadas do tenant, com dados de retenção para a UI."""
    sql = (
        'SELECT units.id, units.company_id, units.name, units.unit_type, units.city, units.notes, '
        'units.status, units.archived_at, units.archived_by, units.archive_reason, units.retention_until, '
        'units.legal_hold, units.legal_hold_reason, '
        'companies.name AS company_name, users.full_name AS archived_by_name '
        'FROM units '
        'JOIN companies ON companies.id = units.company_id '
        'LEFT JOIN users ON users.id = units.archived_by '
        'WHERE units.status IN (?, ?)'
    )
    params = [UNIT_STATUS_ARCHIVED, UNIT_STATUS_PENDING_DELETION]
    if actor and actor['role'] != 'master_admin':
        sql += ' AND units.company_id = ?'
        params.append(actor['company_id'])
    rows = connection.execute(sql + ' ORDER BY units.archived_at DESC', tuple(params)).fetchall()
    now = _now_utc()
    units = []
    for row in rows:
        item = row_to_dict(row)
        item['retention_days_remaining'] = _retention_days_remaining(item.get('retention_until'), now)
        units.append(item)
    return units


def _retention_days_remaining(retention_until, now=None):
    raw = str(retention_until or '').strip()
    if not raw:
        return 0
    try:
        until = datetime.fromisoformat(raw)
    except ValueError:
        return 0
    if until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    delta = until - (now or _now_utc())
    return max(0, delta.days)


def _count_where(connection, table, where, params):
    from core.schema import _table_exists
    if not _table_exists(connection, table):
        return 0
    row = connection.execute(f'SELECT COUNT(*) AS total FROM {table} WHERE {where}', params).fetchone()
    if row is None:
        return 0
    data = dict(row)
    return int(data.get('total') or next(iter(data.values()), 0) or 0)


def summarize_unit_history(connection, unit_id):
    """Resumo do que será removido na exclusão definitiva (e do que o arquivo preserva)."""
    unit_id = int(unit_id)
    return {
        'employees': _count_where(connection, 'employees', 'unit_id = ?', (unit_id,)),
        'employee_movements': _count_where(
            connection, 'employee_unit_movements', 'source_unit_id = ? OR target_unit_id = ?', (unit_id, unit_id)
        ),
        'epis': _count_where(connection, 'epis', 'unit_id = ?', (unit_id,)),
        'deliveries': _count_where(connection, 'deliveries', 'unit_id = ?', (unit_id,)),
        'devolutions': _count_where(connection, 'epi_devolutions', 'unit_id = ?', (unit_id,)),
        'stock_movements': _count_where(connection, 'stock_movements', 'unit_id = ?', (unit_id,)),
        'stock_items': _count_where(connection, 'epi_stock_items', 'unit_id = ?', (unit_id,)),
        'epi_requests': _count_where(connection, 'epi_requests', 'unit_id = ?', (unit_id,)),
        'feedbacks': _count_where(connection, 'epi_feedbacks', 'unit_id = ?', (unit_id,)),
        'ficha_periods': _count_where(connection, 'epi_ficha_periods', 'unit_id = ?', (unit_id,)),
        'purchase_requests': _count_where(connection, 'purchase_requests', 'unit_id = ?', (unit_id,)),
        'purchase_orders': _count_where(connection, 'purchase_orders', 'unit_id = ?', (unit_id,)),
    }


def _ensure_purge_allowed(connection, unit, actor):
    if actor.get('role') not in ('master_admin', 'general_admin'):
        raise PermissionError(
            'Apenas Administrador Geral ou Administrador Master podem excluir definitivamente uma unidade.'
        )
    status = str(unit.get('status') or UNIT_STATUS_ACTIVE)
    if status not in (UNIT_STATUS_ARCHIVED, UNIT_STATUS_PENDING_DELETION):
        raise ValueError('A unidade precisa estar arquivada antes da exclusão definitiva.')
    if int(unit.get('legal_hold') or 0):
        raise ValueError(
            'Exclusão bloqueada: existe bloqueio jurídico/auditoria em andamento nesta unidade '
            f"({str(unit.get('legal_hold_reason') or '').strip() or 'sem motivo registrado'})."
        )
    days_remaining = _retention_days_remaining(unit.get('retention_until'))
    if days_remaining > 0:
        raise ValueError(
            f'Período de retenção ainda vigente: faltam {days_remaining} dia(s). '
            'A exclusão definitiva só é permitida após o término da retenção.'
        )


def request_unit_purge(connection, unit, actor, ip=''):
    """Etapa 1/2 da exclusão definitiva: valida elegibilidade e apresenta o resumo."""
    _ensure_purge_allowed(connection, unit, actor)
    summary = summarize_unit_history(connection, int(unit['id']))
    connection.execute(
        'UPDATE units SET status = ? WHERE id = ?',
        (UNIT_STATUS_PENDING_DELETION, int(unit['id'])),
    )
    register_unit_audit(
        connection, unit['company_id'], actor, 'unit_purge_requested',
        f"Exclusão definitiva da unidade \"{unit['name']}\" iniciada (etapa 1/2, aguardando confirmação).",
        {'unit_id': int(unit['id']), 'unit_name': unit['name'], 'records': summary, 'ip': str(ip or '')},
    )
    return summary


def cancel_unit_purge(connection, unit, actor, ip=''):
    if str(unit.get('status') or '') != UNIT_STATUS_PENDING_DELETION:
        raise ValueError('Unidade não está em processo de exclusão.')
    connection.execute(
        'UPDATE units SET status = ? WHERE id = ?',
        (UNIT_STATUS_ARCHIVED, int(unit['id'])),
    )
    register_unit_audit(
        connection, unit['company_id'], actor, 'unit_purge_cancelled',
        f"Processo de exclusão definitiva da unidade \"{unit['name']}\" cancelado; unidade permanece arquivada.",
        {'unit_id': int(unit['id']), 'ip': str(ip or '')},
    )


def _purge_purchase_history(connection, unit_id):
    from core.schema import _table_exists
    order_tables = ('purchase_order_items', 'purchase_order_files', 'purchase_approvals', 'purchase_order_confirmations')
    if _table_exists(connection, 'purchase_orders'):
        for table in order_tables:
            if _table_exists(connection, table):
                connection.execute(
                    f'DELETE FROM {table} WHERE purchase_order_id IN (SELECT id FROM purchase_orders WHERE unit_id = ?)',
                    (unit_id,),
                )
        connection.execute('DELETE FROM purchase_orders WHERE unit_id = ?', (unit_id,))
    if _table_exists(connection, 'purchase_request_items'):
        connection.execute('DELETE FROM purchase_request_items WHERE unit_id = ?', (unit_id,))
    if _table_exists(connection, 'purchase_requests'):
        connection.execute('DELETE FROM purchase_requests WHERE unit_id = ?', (unit_id,))
    for table, column in (
        ('purchase_pendencies', 'unit_id'),
        ('purchase_role_unit_links', 'unit_id'),
    ):
        if _table_exists(connection, table):
            connection.execute(f'DELETE FROM {table} WHERE {column} = ?', (unit_id,))


def confirm_unit_purge(connection, unit, actor, justification, confirm_name, ip=''):
    """Etapa 2/2 da exclusão definitiva: expurga dados e mantém tombstone.

    O registro da unidade nunca é removido fisicamente: vira tombstone com
    status 'deleted', preservando company_id/unit_id e a rastreabilidade das
    referências remanescentes. O resumo do que foi removido fica gravado em
    company_audit_logs de forma permanente.
    """
    _ensure_purge_allowed(connection, unit, actor)
    if str(unit.get('status') or '') != UNIT_STATUS_PENDING_DELETION:
        raise ValueError('Inicie o processo de exclusão (etapa 1) antes de confirmar.')
    justification = str(justification or '').strip()
    if len(justification) < 10:
        raise ValueError('Justificativa obrigatória (mínimo de 10 caracteres) para exclusão definitiva.')
    if str(confirm_name or '').strip() != str(unit['name']).strip():
        raise ValueError('Confirmação inválida: digite o nome exato da unidade para confirmar a exclusão.')
    summary = summarize_unit_history(connection, int(unit['id']))
    unit_id = int(unit['id'])
    from core.schema import _table_exists
    for table in ('ficha_epi_snapshots', 'ficha_epi_audit_log', 'epi_devolutions'):
        if _table_exists(connection, table):
            connection.execute(f'DELETE FROM {table} WHERE unit_id = ?', (unit_id,))
    delete_unit_dependencies(connection, unit_id)
    _purge_purchase_history(connection, unit_id)
    if _table_exists(connection, 'unit_joint_venture_periods'):
        connection.execute('DELETE FROM unit_joint_venture_periods WHERE unit_id = ?', (unit_id,))
    now_iso = _now_iso()
    connection.execute(
        'UPDATE units SET status = ?, deleted_at = ?, deleted_by = ?, delete_reason = ? WHERE id = ?',
        (UNIT_STATUS_DELETED, now_iso, int(actor['id']), justification, unit_id),
    )
    register_unit_audit(
        connection, unit['company_id'], actor, 'unit_purged',
        f"Unidade \"{unit['name']}\" excluída definitivamente após o período de retenção.",
        {
            'unit_id': unit_id,
            'unit_name': unit['name'],
            'justification': justification,
            'records_removed': summary,
            'archived_at': str(unit.get('archived_at') or ''),
            'retention_until': str(unit.get('retention_until') or ''),
            'deleted_at': now_iso,
            'ip': str(ip or ''),
        },
    )
    return summary
