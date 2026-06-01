"""Serviços de relatórios."""

from datetime import datetime

from epi_backend.db import row_to_dict
from core.auth import ensure_company_access, ensure_resource_company
from modules.employees.service import get_employee_by_id, actor_operational_unit_id, ensure_actor_employee_scope
from modules.units.service import get_unit_by_id
from modules.epis.service import get_epi_by_id


class InvalidQueryParamError(ValueError):
    def __init__(self, field_name, message, value):
        super().__init__(message)
        self.field_name = field_name
        self.value = value


def normalize_report_filters(raw_filters):
    raw_filters = raw_filters or {}

    def parse_optional_int(field_name):
        raw_value = str(raw_filters.get(field_name, '') or '').strip()
        if not raw_value:
            return ''
        try:
            return int(raw_value)
        except ValueError as exc:
            raise InvalidQueryParamError(field_name, f'Filtro inválido: {field_name} deve ser numérico.', raw_value) from exc

    def parse_optional_date(field_name):
        raw_value = str(raw_filters.get(field_name, '') or '').strip()
        if not raw_value:
            return ''
        try:
            datetime.strptime(raw_value, '%Y-%m-%d')
        except ValueError as exc:
            raise InvalidQueryParamError(field_name, f'Filtro inválido: {field_name} deve estar no formato YYYY-MM-DD.', raw_value) from exc
        return raw_value

    return {
        'company_id': parse_optional_int('company_id'),
        'unit_id': parse_optional_int('unit_id'),
        'employee_id': parse_optional_int('employee_id'),
        'epi_id': parse_optional_int('epi_id'),
        'sector': str(raw_filters.get('sector', '') or '').strip(),
        'start_date': parse_optional_date('start_date'),
        'end_date': parse_optional_date('end_date'),
        'archive_status': str(raw_filters.get('archive_status', raw_filters.get('status', '')) or '').strip().lower(),
        'tipo_vinculo': str(raw_filters.get('tipo_vinculo', '') or '').strip(),
    }


def build_reports(connection, actor, filters):
    from modules.deliveries.service import fetch_deliveries
    filters = normalize_report_filters(filters)
    clauses, params = [], []
    scope_unit_id = actor_operational_unit_id(connection, actor)
    if actor.get('role') in ('admin', 'user') and not scope_unit_id:
        raise PermissionError('Perfil sem unidade operacional ativa para consultar relatórios.')
    selected_company_id = filters.get('company_id')
    if selected_company_id:
        ensure_company_access(actor, int(selected_company_id))
        clauses.append('deliveries.company_id = ?')
        params.append(int(selected_company_id))
    elif actor['role'] != 'master_admin':
        clauses.append('deliveries.company_id = ?')
        params.append(actor['company_id'])
    raw_unit_id = str(filters.get('unit_id') or '').strip()
    if scope_unit_id:
        if raw_unit_id and int(raw_unit_id) != int(scope_unit_id):
            raise PermissionError('Operação permitida somente para sua unidade operacional.')
        clauses.append('deliveries.unit_id = ?')
        params.append(scope_unit_id)
    if filters.get('unit_id'):
        if not scope_unit_id:
            unit = get_unit_by_id(connection, int(filters['unit_id']))
            ensure_resource_company(actor, unit, 'Unidade')
            clauses.append('deliveries.unit_id = ?')
            params.append(int(filters['unit_id']))
    employee_id = str(filters.get('employee_id') or '').strip()
    employee = None
    if employee_id:
        employee = get_employee_by_id(connection, int(employee_id))
        ensure_resource_company(actor, employee, 'Colaborador')
        if scope_unit_id:
            ensure_actor_employee_scope(connection, actor, employee)
        clauses.append('deliveries.employee_id = ?')
        params.append(int(employee_id))
    if filters.get('sector'):
        clauses.append('deliveries.sector = ?')
        params.append(filters['sector'])
    if filters.get('tipo_vinculo'):
        clauses.append('employees.tipo_vinculo = ?')
        params.append(filters['tipo_vinculo'])
    if filters.get('epi_id'):
        epi = get_epi_by_id(connection, int(filters['epi_id']))
        ensure_resource_company(actor, epi, 'EPI')
        clauses.append('deliveries.epi_id = ?')
        params.append(int(filters['epi_id']))
    if filters.get('start_date'):
        clauses.append('deliveries.delivery_date >= ?')
        params.append(filters['start_date'])
    if filters.get('end_date'):
        clauses.append('deliveries.delivery_date <= ?')
        params.append(filters['end_date'])
    where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ''
    deliveries = fetch_deliveries(connection, None, where_clause, tuple(params))
    by_unit, by_sector, by_epi, by_tipo_vinculo = {}, {}, {}, {}
    for item in deliveries:
        by_unit[item['unit_name']] = by_unit.get(item['unit_name'], 0) + int(item['quantity'])
        by_sector[item['sector']] = by_sector.get(item['sector'], 0) + int(item['quantity'])
        by_epi[item['epi_name']] = by_epi.get(item['epi_name'], 0) + int(item['quantity'])
        tv = str(item.get('tipo_vinculo') or 'CLT')
        by_tipo_vinculo[tv] = by_tipo_vinculo.get(tv, 0) + int(item['quantity'])
    employee_fichas = []
    if employee:
        ficha_clauses = ['fp.employee_id = ?']
        ficha_params = [int(employee_id)]
        if actor['role'] != 'master_admin':
            ficha_clauses.append('fp.company_id = ?')
            ficha_params.append(actor['company_id'])
        if scope_unit_id:
            ficha_clauses.append('fp.unit_id = ?')
            ficha_params.append(int(scope_unit_id))
        ficha_where = f"WHERE {' AND '.join(ficha_clauses)}"
        ficha_rows = connection.execute(
            (
                'SELECT fp.id, fp.period_start, fp.period_end, fp.status, fp.company_id, fp.unit_id, '
                'employees.name AS employee_name, employees.employee_id_code, units.name AS unit_name '
                'FROM epi_ficha_periods fp '
                'JOIN employees ON employees.id = fp.employee_id '
                'JOIN units ON units.id = fp.unit_id '
                f'{ficha_where} '
                'ORDER BY fp.period_start DESC, fp.id DESC'
            ),
            tuple(ficha_params)
        ).fetchall()
        for row in ficha_rows:
            parsed = row_to_dict(row)
            totals = connection.execute(
                'SELECT COUNT(*) AS total_items, COALESCE(SUM(quantity), 0) AS total_quantity FROM epi_ficha_items WHERE ficha_period_id = ?',
                (int(parsed['id']),)
            ).fetchone()
            totals_data = row_to_dict(totals) if totals else {}
            parsed['total_items'] = int(totals_data.get('total_items') or 0)
            parsed['total_quantity'] = int(totals_data.get('total_quantity') or 0)
            employee_fichas.append(parsed)
    return {
        'deliveries': deliveries,
        'by_unit': by_unit,
        'by_sector': by_sector,
        'by_epi': by_epi,
        'by_tipo_vinculo': by_tipo_vinculo,
        'total_quantity': sum(int(item['quantity']) for item in deliveries),
        'employee_fichas': employee_fichas,
    }


# ── Route-level SQL extractions ───────────────────────────────────────────────

def fetch_report_requests(connection, clauses, params):
    from epi_backend.db import row_to_dict
    where = f"WHERE {' AND '.join(clauses)}"
    rows = connection.execute(
        f'SELECT rr.*, u.name AS unit_name FROM report_requests rr '
        f'LEFT JOIN units u ON u.id = rr.unit_id '
        f'{where} ORDER BY rr.created_at DESC LIMIT 100',
        tuple(params),
    ).fetchall()
    return [row_to_dict(r) for r in rows]


def create_report_request(connection, company_id, unit_id, requester_user_id, requester_name,
                           period_year, period_month, notes, now):
    connection.execute(
        'INSERT INTO report_requests (company_id, unit_id, requester_user_id, requester_name, '
        'period_year, period_month, notes, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (company_id, unit_id, int(requester_user_id), requester_name,
         period_year or None, period_month or None,
         str(notes or '').strip(), 'pending', now)
    )


def mark_report_request_done(connection, rr_id, company_id, handled_by_user_id, handled_by_name, handled_at):
    connection.execute(
        "UPDATE report_requests SET status = 'done', handled_by_user_id = ?, handled_by_name = ?, handled_at = ? WHERE id = ? AND company_id = ?",
        (int(handled_by_user_id), handled_by_name, handled_at, int(rr_id), int(company_id))
    )
