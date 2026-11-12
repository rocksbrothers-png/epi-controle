"""F2.1 pure contract and adversarial parser tests (in addition to real PG)."""
import sqlite3

import pytest

from modules.deliveries.visibility import active_delivery_sql
from modules.employee_ppe_360.contract import ContractError
from modules.employee_ppe_360.in_use import (
    InUseError,
    parse_query,
    require_permissions,
    valid_date,
)


@pytest.mark.parametrize('raw,expected', [
    ('2024-02-29', '2024-02-29'), ('2000-02-29', '2000-02-29'),
    ('1900-02-29', None), ('2026-02-30', None), ('0000-01-01', None),
    ('9999-12-31', '9999-12-31'), ('0001-01-01', '0001-01-01'),
    (None, None), ('', None), ('2026-1-01', None), ('2026-01-01T12:00:00', None),
    (' 2026-01-01 ', '2026-01-01'), ('\t2026-01-01\n', '2026-01-01'),
])
def test_calendar(raw, expected):
    assert valid_date(raw) == expected


@pytest.mark.parametrize('value', ['9' * 5000, '²', '١', '1e2', '+1', '1.0'])
def test_adversarial_limits(value):
    with pytest.raises(ContractError) as exc:
        parse_query({'limit': [value]})
    assert exc.value.code == 'INVALID_PAGINATION'


def test_defaults_and_unknown_parameters():
    assert parse_query({}) == {'limit': 20, 'cursor': None}
    assert parse_query({'limit': [''], 'cursor': ['']}) == {'limit': 20, 'cursor': None}
    with pytest.raises(InUseError):
        parse_query({'unit_id': ['1']})


def test_master_blocked_even_with_all_permissions():
    with pytest.raises(ContractError) as exc:
        require_permissions({'role': 'master_admin', 'company_id': 1})
    assert exc.value.code == 'FORBIDDEN'


def test_official_reversal_predicate_legacy_schema():
    # Characterizes the official compatibility branch; does not replace PG tests.
    with sqlite3.connect(':memory:') as c:
        c.execute('CREATE TABLE deliveries (id INTEGER)')
        assert active_delivery_sql(c, 'd') == ''
        c.execute('ALTER TABLE deliveries ADD COLUMN migration_reverted_at TEXT')
        assert 'migration_reverted_at' in active_delivery_sql(c, 'd')
