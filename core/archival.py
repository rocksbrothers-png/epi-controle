"""Ciclo de vida de arquivamento (soft delete) genérico por entidade.

Mesma política aplicada às Unidades, reutilizada por Colaboradores e EPIs:

- arquivar  → registro desativado para novas operações, histórico 100% preservado;
- desarquivar → registro volta ao status ativo;
- exclusão definitiva → habilitada somente após o período de retenção do
  tenant (mínimo 5 anos), em duas etapas com justificativa, mantendo o
  registro como tombstone (status='deleted') e a trilha permanente em
  company_audit_logs.
"""

import json
from datetime import datetime, timezone

from core.schema import _col_exists, _table_exists
from epi_backend.db import row_to_dict

STATUS_ACTIVE = 'active'
STATUS_INACTIVE = 'inactive'
STATUS_ARCHIVED = 'archived'
STATUS_PENDING_DELETION = 'pending_deletion'
STATUS_DELETED = 'deleted'
NON_OPERATIONAL_STATUSES = (STATUS_ARCHIVED, STATUS_PENDING_DELETION, STATUS_DELETED)

MIN_RETENTION_YEARS = 5

# Colunas de ciclo de vida compartilhadas por units/employees/epis.
LIFECYCLE_COLUMNS = (
    ('status', "TEXT NOT NULL DEFAULT 'active'"),
    ('archived_at', 'TEXT'),
    ('archived_by', 'INTEGER'),
    ('archive_reason', "TEXT NOT NULL DEFAULT ''"),
    ('retention_until', 'TEXT'),
    ('legal_hold', 'INTEGER NOT NULL DEFAULT 0'),
    ('legal_hold_reason', "TEXT NOT NULL DEFAULT ''"),
    ('deleted_at', 'TEXT'),
    ('deleted_by', 'INTEGER'),
    ('delete_reason', "TEXT NOT NULL DEFAULT ''"),
)
LIFECYCLE_FIELD_NAMES = tuple(name for name, _ in LIFECYCLE_COLUMNS)


def _now_utc():
    return datetime.now(timezone.utc)


def _now_iso():
    return _now_utc().isoformat(timespec='seconds')


def _add_years(moment, years):
    try:
        return moment.replace(year=moment.year + int(years))
    except ValueError:  # 29/fev em ano não bissexto
        return moment.replace(year=moment.year + int(years), day=28)


def lifecycle_enabled(connection, table):
    """Indica se a tabela já tem as colunas de ciclo de vida (bancos legados)."""
    return _col_exists(connection, table, 'status')


def get_record_status(connection, table, record_id):
    if not lifecycle_enabled(connection, table):
        return STATUS_ACTIVE
    row = connection.execute(
        f'SELECT status FROM {table} WHERE id = ?', (int(record_id),)
    ).fetchone()
    if not row:
        return None
    return str(dict(row).get('status') or STATUS_ACTIVE)


def ensure_record_operational(connection, table, record_id, entity_label, operation='esta operação'):
    """Bloqueia novas operações em registros arquivados/em exclusão.

    Consultas, relatórios e auditorias não passam por aqui — apenas fluxos de
    escrita operacional.
    """
    if not record_id:
        return
    status = get_record_status(connection, table, int(record_id))
    if status in NON_OPERATIONAL_STATUSES:
        raise ValueError(
            f'{entity_label} arquivado(a): não é permitido registrar {operation}. '
            'O histórico permanece disponível apenas para consulta, relatórios e auditoria.'
        )


# Parâmetro de retenção por entidade (configurável por tenant na aba
# Configurações → Regras → Arquivamento). A Ficha de EPI NÃO entra aqui: sua
# retenção de 5 anos (NR-6) tem regra própria e permanece inalterada.
RETENTION_COLUMNS = {
    'units': 'unit_retention_years',
    'epis': 'epi_retention_years',
    'employees': 'employee_retention_years',
    'outsourced_companies': 'outsourced_company_retention_years',
}


def get_company_retention_years(connection, company_id, table='units'):
    """Retenção por tenant e por entidade, nunca abaixo do mínimo legal (5 anos)."""
    column = RETENTION_COLUMNS.get(table, 'unit_retention_years')
    if _col_exists(connection, 'companies', column):
        row = connection.execute(
            f'SELECT {column} FROM companies WHERE id = ?',
            (int(company_id),),
        ).fetchone()
        if row:
            configured = int(dict(row).get(column) or 0)
            if configured >= MIN_RETENTION_YEARS:
                return configured
    return MIN_RETENTION_YEARS


def set_company_retention_years(connection, company_id, table, years):
    column = RETENTION_COLUMNS.get(table)
    if not column:
        raise ValueError('Entidade inválida para política de arquivamento.')
    years = int(years)
    if years < MIN_RETENTION_YEARS:
        raise ValueError(
            f'O período de retenção não pode ser inferior a {MIN_RETENTION_YEARS} anos.'
        )
    if not _col_exists(connection, 'companies', column):
        raise ValueError('Banco de dados ainda não migrado para a política de arquivamento.')
    connection.execute(
        f'UPDATE companies SET {column} = ? WHERE id = ?',
        (years, int(company_id)),
    )
    return years


def register_archival_audit(connection, company_id, actor, action_type, summary, details=None):
    """Trilha permanente em company_audit_logs — sobrevive à exclusão definitiva."""
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


def retention_days_remaining(retention_until, now=None):
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


def archive_record(connection, table, record, actor, *, entity_label, audit_prefix,
                   record_label, reason='', ip=''):
    """Arquiva o registro preservando todo o histórico (soft delete)."""
    status = str(record.get('status') or STATUS_ACTIVE)
    if status in NON_OPERATIONAL_STATUSES:
        raise ValueError(f'{entity_label} já está arquivado(a) ou em processo de exclusão.')
    retention_years = get_company_retention_years(connection, record['company_id'], table)
    now = _now_utc()
    retention_until = _add_years(now, retention_years)
    reason = str(reason or '').strip() or 'Arquivamento solicitado pelo usuário (substitui exclusão).'
    connection.execute(
        f'UPDATE {table} SET status = ?, archived_at = ?, archived_by = ?, archive_reason = ?, retention_until = ? '
        'WHERE id = ?',
        (
            STATUS_ARCHIVED,
            now.isoformat(timespec='seconds'),
            int(actor['id']),
            reason,
            retention_until.isoformat(timespec='seconds'),
            int(record['id']),
        ),
    )
    register_archival_audit(
        connection, record['company_id'], actor, f'{audit_prefix}_archived',
        f'{entity_label} "{record_label}" arquivado(a). '
        f'Histórico preservado até {retention_until.date().isoformat()}.',
        {
            f'{audit_prefix}_id': int(record['id']),
            'name': record_label,
            'reason': reason,
            'retention_years': retention_years,
            'retention_until': retention_until.isoformat(timespec='seconds'),
            'ip': str(ip or ''),
        },
    )
    return {
        'status': STATUS_ARCHIVED,
        'archived_at': now.isoformat(timespec='seconds'),
        'retention_years': retention_years,
        'retention_until': retention_until.isoformat(timespec='seconds'),
    }


def restore_record(connection, table, record, actor, *, entity_label, audit_prefix,
                   record_label, ip=''):
    """Desarquiva: o registro volta ao status ativo; histórico permanece intacto."""
    status = str(record.get('status') or STATUS_ACTIVE)
    if status not in (STATUS_ARCHIVED, STATUS_PENDING_DELETION):
        raise ValueError(f'Apenas registros arquivados podem ser desarquivados ({entity_label}).')
    connection.execute(
        f"UPDATE {table} SET status = ?, archived_at = NULL, archived_by = NULL, "
        "archive_reason = '', retention_until = NULL WHERE id = ?",
        (STATUS_ACTIVE, int(record['id'])),
    )
    register_archival_audit(
        connection, record['company_id'], actor, f'{audit_prefix}_restored',
        f'{entity_label} "{record_label}" desarquivado(a) e reativado(a).',
        {f'{audit_prefix}_id': int(record['id']), 'name': record_label, 'ip': str(ip or '')},
    )


def ensure_purge_allowed(record, actor, entity_label):
    if actor.get('role') not in ('master_admin', 'general_admin'):
        raise PermissionError(
            'Apenas Administrador Geral ou Administrador Master podem excluir definitivamente.'
        )
    status = str(record.get('status') or STATUS_ACTIVE)
    if status not in (STATUS_ARCHIVED, STATUS_PENDING_DELETION):
        raise ValueError(f'{entity_label} precisa estar arquivado(a) antes da exclusão definitiva.')
    if int(record.get('legal_hold') or 0):
        raise ValueError(
            'Exclusão bloqueada: existe bloqueio jurídico/auditoria em andamento '
            f"({str(record.get('legal_hold_reason') or '').strip() or 'sem motivo registrado'})."
        )
    days = retention_days_remaining(record.get('retention_until'))
    if days > 0:
        raise ValueError(
            f'Período de retenção ainda vigente: faltam {days} dia(s). '
            'A exclusão definitiva só é permitida após o término da retenção; '
            'até lá o registro permanece arquivado.'
        )


def request_purge(connection, table, record, actor, *, entity_label, audit_prefix,
                  record_label, summary, ip=''):
    """Etapa 1/2 da exclusão definitiva: valida elegibilidade e registra o resumo."""
    ensure_purge_allowed(record, actor, entity_label)
    connection.execute(
        f'UPDATE {table} SET status = ? WHERE id = ?',
        (STATUS_PENDING_DELETION, int(record['id'])),
    )
    register_archival_audit(
        connection, record['company_id'], actor, f'{audit_prefix}_purge_requested',
        f'Exclusão definitiva de {entity_label.lower()} "{record_label}" iniciada '
        '(etapa 1/2, aguardando confirmação).',
        {f'{audit_prefix}_id': int(record['id']), 'name': record_label,
         'records': summary, 'ip': str(ip or '')},
    )
    return summary


def cancel_purge(connection, table, record, actor, *, entity_label, audit_prefix,
                 record_label, ip=''):
    if str(record.get('status') or '') != STATUS_PENDING_DELETION:
        raise ValueError(f'{entity_label} não está em processo de exclusão.')
    connection.execute(
        f'UPDATE {table} SET status = ? WHERE id = ?',
        (STATUS_ARCHIVED, int(record['id'])),
    )
    register_archival_audit(
        connection, record['company_id'], actor, f'{audit_prefix}_purge_cancelled',
        f'Processo de exclusão definitiva de {entity_label.lower()} "{record_label}" '
        'cancelado; registro permanece arquivado.',
        {f'{audit_prefix}_id': int(record['id']), 'ip': str(ip or '')},
    )


def confirm_purge(connection, table, record, actor, *, entity_label, audit_prefix,
                  record_label, justification, confirm_name, summary, purge_history,
                  ip=''):
    """Etapa 2/2 da exclusão definitiva: expurga o histórico e mantém tombstone.

    `purge_history` é o callback específico da entidade que remove os dados
    operacionais dependentes; o registro em si nunca sai do banco.
    """
    ensure_purge_allowed(record, actor, entity_label)
    if str(record.get('status') or '') != STATUS_PENDING_DELETION:
        raise ValueError('Inicie o processo de exclusão (etapa 1) antes de confirmar.')
    justification = str(justification or '').strip()
    if len(justification) < 10:
        raise ValueError('Justificativa obrigatória (mínimo de 10 caracteres) para exclusão definitiva.')
    if str(confirm_name or '').strip() != str(record_label).strip():
        raise ValueError(
            f'Confirmação inválida: digite o identificador exato ("{record_label}") '
            'para confirmar a exclusão.'
        )
    purge_history(connection, int(record['id']))
    now_iso = _now_iso()
    connection.execute(
        f'UPDATE {table} SET status = ?, deleted_at = ?, deleted_by = ?, delete_reason = ? WHERE id = ?',
        (STATUS_DELETED, now_iso, int(actor['id']), justification, int(record['id'])),
    )
    register_archival_audit(
        connection, record['company_id'], actor, f'{audit_prefix}_purged',
        f'{entity_label} "{record_label}" excluído(a) definitivamente após o período de retenção.',
        {
            f'{audit_prefix}_id': int(record['id']),
            'name': record_label,
            'justification': justification,
            'records_removed': summary,
            'archived_at': str(record.get('archived_at') or ''),
            'retention_until': str(record.get('retention_until') or ''),
            'deleted_at': now_iso,
            'ip': str(ip or ''),
        },
    )
    return summary


def count_where(connection, table, where, params):
    if not _table_exists(connection, table):
        return 0
    row = connection.execute(f'SELECT COUNT(*) AS total FROM {table} WHERE {where}', params).fetchone()
    if row is None:
        return 0
    data = dict(row)
    return int(data.get('total') or next(iter(data.values()), 0) or 0)


def delete_where(connection, table, where, params):
    """DELETE tolerante a tabelas ausentes (schemas legados/testes)."""
    if _table_exists(connection, table):
        connection.execute(f'DELETE FROM {table} WHERE {where}', params)
