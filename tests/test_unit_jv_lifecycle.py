import sqlite3

from epi_backend.epi_scope import filter_epis_for_unit
from epi_backend.unit_jv_lifecycle import (
    end_unit_joint_venture_period,
    ensure_unit_joint_venture_periods_table,
    get_current_unit_joint_venture,
    import_active_joinventures_from_epis,
    start_unit_joint_venture_period,
)


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL)')
    conn.execute('CREATE TABLE epis (id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL, unit_id INTEGER, active_joinventure TEXT)')
    conn.executemany('INSERT INTO units (id, company_id) VALUES (?, ?)', [(1, 1), (2, 1)])
    ensure_unit_joint_venture_periods_table(conn)
    return conn


def test_start_end_and_switch_flow():
    conn = _conn()

    first = start_unit_joint_venture_period(conn, 1, 'JV-X', created_by='qa')
    assert first['joint_venture_name'] == 'JV-X'

    switched = start_unit_joint_venture_period(conn, 1, 'JV-Y', created_by='qa')
    assert switched['joint_venture_name'] == 'JV-Y'

    rows = conn.execute('SELECT * FROM unit_joint_venture_periods WHERE unit_id = 1 ORDER BY id').fetchall()
    assert len(rows) == 2
    assert rows[0]['ended_at'] is not None
    assert rows[1]['ended_at'] is None

    ended = end_unit_joint_venture_period(conn, 1)
    assert ended is not None
    assert get_current_unit_joint_venture(conn, 1) is None


def test_gap_without_jv_is_allowed():
    conn = _conn()
    assert get_current_unit_joint_venture(conn, 1) is None
    assert end_unit_joint_venture_period(conn, 1) is None


def test_import_active_joinventure_idempotent():
    conn = _conn()
    conn.executemany(
        'INSERT INTO epis (id, company_id, unit_id, active_joinventure) VALUES (?, ?, ?, ?)',
        [
            (1, 1, 1, 'JV-X'),
            (2, 1, 1, 'JV-X'),
            (3, 1, 2, 'JV-Z'),
        ],
    )

    assert import_active_joinventures_from_epis(conn) == 2
    assert import_active_joinventures_from_epis(conn) == 0

    active = conn.execute('SELECT * FROM unit_joint_venture_periods WHERE ended_at IS NULL ORDER BY unit_id').fetchall()
    assert [row['joint_venture_name'] for row in active] == ['JV-X', 'JV-Z']


def test_visibility_changes_by_jv_state():
    epis = [
        {'id': 1, 'unit_id': None, 'active_joinventure': ''},
        {'id': 2, 'unit_id': 1, 'active_joinventure': ''},
        {'id': 3, 'unit_id': 1, 'active_joinventure': 'JV-X'},
    ]

    assert [e['id'] for e in filter_epis_for_unit(epis, target_unit_id=1, target_unit_joint_venture_name='')] == [1, 2]
    assert [e['id'] for e in filter_epis_for_unit(epis, target_unit_id=1, target_unit_joint_venture_name='JV-X')] == [3]
