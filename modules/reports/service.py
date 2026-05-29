"""Serviços de relatórios."""

from datetime import datetime


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
    }
