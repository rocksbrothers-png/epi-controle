"""Valores físicos desconhecidos, vencimento e custo: contrato EST-V2."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from modules.stock.lifecycle import (
    manufacturer_expiry,
    nullable_unit_cost,
    physical_date,
    physical_validity,
)

TODAY = date(2026, 10, 12)


@pytest.mark.parametrize('days,status,eligible', [(-1, 'expired', False), (0, 'expiring', True),
                                               (30, 'expiring', True), (31, 'valid', True)])
def test_physical_expiry_boundaries(days, status, eligible):
    result = physical_validity(TODAY + timedelta(days=days), today=TODAY)
    assert result == {'status': status, 'days_remaining': days, 'eligible_by_validity': eligible}


@pytest.mark.parametrize('missing', [None, '', '  '])
def test_unknown_date_is_fail_closed_without_fabricating_a_date(missing):
    assert physical_validity(missing, today=TODAY) == {
        'status': 'unknown', 'days_remaining': None, 'eligible_by_validity': False,
    }


def test_company_alert_window_changes_classification_not_physical_eligibility():
    expiry = TODAY + timedelta(days=45)
    assert physical_validity(expiry, alert_days=15, today=TODAY)['status'] == 'valid'
    assert physical_validity(expiry, alert_days=60, today=TODAY)['status'] == 'expiring'
    assert physical_validity(expiry, alert_days=15, today=TODAY)['eligible_by_validity'] is True
    assert physical_validity(TODAY - timedelta(days=1), alert_days=0, today=TODAY)['eligible_by_validity'] is False


@pytest.mark.parametrize('value', ['2026-02-30', '12/10/2026', '20261012',
                                 '2026-W42-1', '2026-10-12T10:00:00', datetime(2026, 10, 12)])
def test_invalid_or_ambiguous_dates_are_rejected(value):
    with pytest.raises(ValueError):
        physical_date(value)


@pytest.mark.parametrize('days', [-1, True, '30', 3.5])
def test_invalid_alert_windows_are_rejected(days):
    with pytest.raises(ValueError):
        physical_validity(TODAY, alert_days=days, today=TODAY)


def test_ca_expiry_does_not_replace_physical_expiry():
    lot = {'physical_expiry_date': TODAY + timedelta(days=200), 'ca_expiry_snapshot': TODAY - timedelta(days=1)}
    assert physical_validity(lot['physical_expiry_date'], today=TODAY)['status'] == 'valid'
    lot['physical_expiry_date'] = None
    lot['ca_expiry_snapshot'] = TODAY + timedelta(days=200)
    assert physical_validity(lot['physical_expiry_date'], today=TODAY)['eligible_by_validity'] is False


def test_unknown_cost_is_distinct_from_a_known_zero_cost():
    assert nullable_unit_cost(None) is None
    assert nullable_unit_cost('') is None
    assert nullable_unit_cost('0') == Decimal('0.0000')
    assert nullable_unit_cost('12.34565') == Decimal('12.3457')


@pytest.mark.parametrize('manufactured,value,unit,expected', [
    ('2026-01-31', 1, 'months', '2026-02-28'),
    ('2024-01-31', 1, 'months', '2024-02-29'),
    ('2024-02-29', 1, 'years', '2025-02-28'),
    ('2026-01-01', 10, 'days', '2026-01-11'),
])
def test_documented_manufacturer_period_uses_real_calendar(manufactured, value, unit, expected):
    assert manufacturer_expiry(manufactured, value, unit).isoformat() == expected


def test_manufacturer_period_does_not_invent_missing_manufacture_or_life():
    assert manufacturer_expiry(None, 2, 'years') is None
    assert manufacturer_expiry(TODAY) is None


@pytest.mark.parametrize('value,unit', [(0, 'days'), (-1, 'months'), (True, 'days'),
                                      (None, 'years'), (1, None), (1, 'ca'), (10**9, 'years')])
def test_invalid_manufacturer_period_is_rejected(value, unit):
    with pytest.raises(ValueError):
        manufacturer_expiry(TODAY, value, unit)


@pytest.mark.parametrize('cost', ['-0.01', 'NaN', 'Infinity', 'abc', True, '100000000000000'])
def test_invalid_cost_is_rejected(cost):
    with pytest.raises(ValueError):
        nullable_unit_cost(cost)
