"""Vocabulário e valores físicos do estoque, independentes do catálogo/CA.

Estados de validade são calculados, nunca uma autorização editável de entrega.
Os comandos transacionais serão integrados nas fases seguintes.
"""

from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

DEFAULT_WARNING_DAYS = 30
VALIDITY_STATES = ('valid', 'expiring', 'expired', 'unknown')
OPERATIONAL_STATES = (
    'in_stock', 'available', 'reserved', 'delivering', 'delivered', 'blocked',
    'blocked_expired', 'blocked_discard', 'blocked_return', 'blocked_analysis',
    'blocked_rejected', 'blocked_archived', 'maintenance', 'hygiene',
    'quarantine', 'returned_base', 'discard_pending', 'discarded', 'supplier_returned', 'donated',
)
BLOCK_REASONS = {
    'expired': 'EPI vencido',
    'damage': 'Avaria',
    'nonconformity': 'Não conformidade',
    'quarantine': 'Quarentena',
    'inspection_pending': 'Inspeção pendente',
    'suspected_defect': 'Suspeita de defeito',
    'recall': 'Recolhimento',
    'other': 'Outros',
}
DISPOSITIONS = ('return_base', 'quarantine', 'supplier_return', 'discard', 'donation')
EXPIRY_SOURCES = ('unknown', 'label', 'manufacturer_document', 'regularization')
EVENT_TYPES = (
    'receipt', 'block', 'unblock', 'transfer', 'delivery', 'return',
    'return_base', 'quarantine', 'discard', 'supplier_return',
    'expiry_regularization', 'reserve', 'reservation_release', 'reconcile',
    'disposition_requested', 'disposition_rejected', 'donation',
)
TERMINAL_STATUSES = frozenset({'discarded', 'supplier_returned', 'donated'})


def physical_date(value, label='Data física'):
    """Ausência permanece desconhecida; data inválida é erro de entrada."""
    if value is None or value == '':
        return None
    if isinstance(value, datetime):
        raise ValueError(f'{label} deve ser uma data YYYY-MM-DD, sem horário.')
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f'{label} inválida; use YYYY-MM-DD.') from exc
    if parsed.isoformat() != text:
        raise ValueError(f'{label} inválida; use YYYY-MM-DD.')
    return parsed


def warning_days(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError('Prazo de alerta deve ser um inteiro não negativo.')
    return value


def manufacturer_expiry(manufactured, life_value=None, life_unit=None):
    """Prazo documentado, com calendário real; ausência não gera vencimento."""
    manufactured = physical_date(manufactured, 'Fabricação física')
    if life_value is None and life_unit is None:
        return None
    if isinstance(life_value, bool) or not isinstance(life_value, int) or life_value <= 0:
        raise ValueError('Prazo do fabricante deve ser inteiro positivo.')
    if life_unit not in ('days', 'months', 'years'):
        raise ValueError('Unidade do prazo do fabricante inválida.')
    if manufactured is None:
        return None
    try:
        if life_unit == 'days':
            return manufactured + timedelta(days=life_value)
        months = life_value * (12 if life_unit == 'years' else 1)
        year, zero_based_month = divmod(manufactured.year * 12 + manufactured.month - 1 + months, 12)
        month = zero_based_month + 1
        return date(year, month, min(manufactured.day, monthrange(year, month)[1]))
    except (ValueError, OverflowError) as exc:
        raise ValueError('Prazo do fabricante excede o intervalo de datas.') from exc


def physical_validity(expiry, *, alert_days=DEFAULT_WARNING_DAYS, today=None):
    """CA não participa da elegibilidade física. Vencimento vale até o dia."""
    alert_days = warning_days(alert_days)
    current = physical_date(today) if today is not None else datetime.now(timezone.utc).date()
    if current is None:
        raise ValueError('Data de referência é obrigatória.')
    target = physical_date(expiry, 'Validade física')
    if target is None:
        return {'status': 'unknown', 'days_remaining': None, 'eligible_by_validity': False}
    remaining = (target - current).days
    status = 'expired' if remaining < 0 else 'expiring' if remaining <= alert_days else 'valid'
    return {'status': status, 'days_remaining': remaining, 'eligible_by_validity': remaining >= 0}


def nullable_unit_cost(value):
    """Custo desconhecido é NULL; zero conhecido continua sendo um custo."""
    if value is None or value == '':
        return None
    if isinstance(value, bool):
        raise ValueError('Custo unitário inválido.')
    try:
        cost = Decimal(str(value))
        if not cost.is_finite() or cost < 0 or cost > Decimal('99999999999999.9999'):
            raise ValueError('Custo unitário inválido.')
        return cost.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError) as exc:
        raise ValueError('Custo unitário inválido.') from exc
