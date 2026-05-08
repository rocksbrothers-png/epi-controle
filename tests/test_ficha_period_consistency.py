import sqlite3

import pytest

from server_postgres import (
    assert_ficha_period_can_close,
    compute_ficha_period_signature_state,
    resolve_ficha_period_effective_status,
)


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE epi_ficha_periods (id INTEGER PRIMARY KEY, status TEXT, batch_signature_name TEXT, batch_signature_data TEXT, batch_signature_at TEXT, updated_at TEXT)"
    )
    conn.execute(
        "CREATE TABLE epi_ficha_items (id INTEGER PRIMARY KEY, ficha_period_id INTEGER, item_signature_at TEXT)"
    )
    return conn


def test_period_with_pending_items_cannot_close():
    conn = _conn()
    conn.execute("INSERT INTO epi_ficha_periods VALUES (1,'pending_signature','Nome','sig','2026-05-01T00:00:00+00:00','')")
    conn.execute("INSERT INTO epi_ficha_items VALUES (1,1,'')")
    state = compute_ficha_period_signature_state(conn, 1)
    assert state['pending_items'] == 1
    assert state['can_close'] is False
    with pytest.raises(ValueError, match='assinaturas pendentes'):
        assert_ficha_period_can_close(conn, 1)


def test_period_with_all_items_signed_and_batch_signature_can_close():
    conn = _conn()
    conn.execute("INSERT INTO epi_ficha_periods VALUES (2,'pending_signature','Nome','sig','2026-05-01T00:00:00+00:00','')")
    conn.execute("INSERT INTO epi_ficha_items VALUES (1,2,'2026-05-01T00:00:00+00:00')")
    conn.execute("INSERT INTO epi_ficha_items VALUES (2,2,'2026-05-01T00:00:00+00:00')")
    state = assert_ficha_period_can_close(conn, 2)
    assert state['pending_items'] == 0
    assert state['can_close'] is True


def test_closed_period_with_pending_items_is_reopened_to_pending_signature():
    conn = _conn()
    conn.execute("INSERT INTO epi_ficha_periods VALUES (3,'closed','','','', '')")
    conn.execute("INSERT INTO epi_ficha_items VALUES (1,3,'')")
    period = resolve_ficha_period_effective_status(conn, {'id': 3, 'status': 'closed'})
    assert period['status_effective'] == 'pending_signature'
    row = conn.execute('SELECT status FROM epi_ficha_periods WHERE id = 3').fetchone()
    assert row['status'] == 'pending_signature'


def test_closed_period_without_batch_signature_becomes_open_even_with_no_pending_items():
    conn = _conn()
    conn.execute("INSERT INTO epi_ficha_periods VALUES (4,'closed','','','', '')")
    conn.execute("INSERT INTO epi_ficha_items VALUES (1,4,'2026-05-01T00:00:00+00:00')")
    period = resolve_ficha_period_effective_status(conn, {'id': 4, 'status': 'closed'})
    assert period['status_effective'] == 'open'


def test_consistent_closed_period_remains_closed():
    conn = _conn()
    conn.execute("INSERT INTO epi_ficha_periods VALUES (5,'closed','Nome','sig','2026-05-01T00:00:00+00:00','')")
    conn.execute("INSERT INTO epi_ficha_items VALUES (1,5,'2026-05-01T00:00:00+00:00')")
    period = resolve_ficha_period_effective_status(conn, {'id': 5, 'status': 'closed'})
    assert period['status_effective'] == 'closed'
    row = conn.execute('SELECT status FROM epi_ficha_periods WHERE id = 5').fetchone()
    assert row['status'] == 'closed'


def test_period_without_items_has_zero_pending_and_cannot_close():
    conn = _conn()
    conn.execute("INSERT INTO epi_ficha_periods VALUES (6,'pending_signature','Nome','sig','2026-05-01T00:00:00+00:00','')")
    state = compute_ficha_period_signature_state(conn, 6)
    assert state['total_items'] == 0
    assert state['signed_items'] == 0
    assert state['pending_items'] == 0
    assert state['can_close'] is False


def test_admin_and_portal_effective_status_are_consistent_for_same_period():
    conn = _conn()
    conn.execute("INSERT INTO epi_ficha_periods VALUES (7,'pending_signature','Nome','sig','2026-05-01T00:00:00+00:00','')")
    conn.execute("INSERT INTO epi_ficha_items VALUES (1,7,'2026-05-01T00:00:00+00:00')")
    period_from_admin = resolve_ficha_period_effective_status(conn, {'id': 7, 'status': 'pending_signature'})
    period_from_portal = resolve_ficha_period_effective_status(conn, {'id': 7, 'status': 'pending_signature'})
    assert period_from_admin['status_effective'] == period_from_portal['status_effective'] == 'closed'
