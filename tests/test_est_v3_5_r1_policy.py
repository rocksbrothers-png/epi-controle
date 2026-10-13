"""Tenant calendar, strict unknown validity and physical/catalog separation."""
import sqlite3
from datetime import datetime, timezone

import pytest

from modules.stock.eligibility import classify_physical, validity_policy
from modules.stock.service import effective_delivery_expiry


@pytest.mark.parametrize('value', [None, '', ' ', 'invalid', '2026-02-30', '2026-10-12junk', '2026-10-12T00:00:00'])
def test_unknown_or_invalid_physical_date_is_never_eligible(value):
    result = classify_physical(value, {'as_of_date': '2026-10-12', 'warning_days': 30})
    assert result['status'] == 'unknown' and result['eligible_by_validity'] is False


def test_tenant_timezone_and_configured_window_are_authoritative():
    c = sqlite3.connect(':memory:')
    c.row_factory = sqlite3.Row
    c.executescript('CREATE TABLE companies(id INTEGER PRIMARY KEY, timezone TEXT); '
                    'CREATE TABLE company_stock_validity_config(company_id INTEGER, warning_days INTEGER); '
                    "INSERT INTO companies VALUES(1, 'America/Sao_Paulo'), (2, 'Pacific/Kiritimati'); "
                    'INSERT INTO company_stock_validity_config VALUES(1, 0), (2, 60);')
    instant = datetime(2026, 10, 12, 1, 0, tzinfo=timezone.utc)
    first = validity_policy(c, 1, now=instant)
    second = validity_policy(c, 2, now=instant)
    assert first['as_of_date'] == '2026-10-11' and first['warning_days'] == 0
    assert second['as_of_date'] == '2026-10-12' and second['warning_days'] == 60
    assert classify_physical('2026-10-11', first)['eligible_by_validity'] is True
    assert classify_physical('2026-10-11', second)['eligible_by_validity'] is False
    assert classify_physical('2026-10-12', first)['status'] == 'valid'
    assert classify_physical('2026-12-11', second)['status'] == 'expiring'
    assert classify_physical('2026-12-12', second)['status'] == 'valid'
    c.close()


@pytest.mark.parametrize('catalog', ['2099-01-01', '2000-01-01', None])
def test_no_physical_column_cannot_fall_back_to_catalog(catalog):
    c = sqlite3.connect(':memory:')
    c.row_factory = sqlite3.Row
    c.execute('CREATE TABLE epi_stock_items(id INTEGER PRIMARY KEY)')
    c.execute('INSERT INTO epi_stock_items(id) VALUES(1)')
    expiry = effective_delivery_expiry(c, 1, catalog)
    assert not expiry
    assert classify_physical(expiry, {'as_of_date': '2026-10-12', 'warning_days': 30})['eligible_by_validity'] is False
    c.close()
