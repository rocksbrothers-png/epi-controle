from __future__ import annotations

from datetime import datetime, timezone

MIGRATION_CREATED_BY = 'migration:epis.active_joinventure'


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_name(name: object) -> str:
    return str(name or '').strip()


def ensure_unit_joint_venture_periods_table(connection) -> None:
    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS unit_joint_venture_periods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL,
            joint_venture_name TEXT NOT NULL,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            created_by TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE CASCADE,
            UNIQUE(unit_id, started_at)
        )
        '''
    )
    connection.execute(
        'CREATE INDEX IF NOT EXISTS idx_unit_jv_periods_active ON unit_joint_venture_periods (unit_id, ended_at)'
    )


def get_current_unit_joint_venture(connection, unit_id: int):
    return connection.execute(
        '''
        SELECT id, company_id, unit_id, joint_venture_name, started_at, ended_at, created_by, created_at
        FROM unit_joint_venture_periods
        WHERE unit_id = ? AND ended_at IS NULL
        ORDER BY started_at DESC, id DESC
        LIMIT 1
        ''',
        (int(unit_id),),
    ).fetchone()


def end_unit_joint_venture_period(connection, unit_id: int, *, ended_at: str | None = None):
    ended_at = ended_at or _now_iso()
    current = get_current_unit_joint_venture(connection, unit_id)
    if not current:
        return None
    connection.execute(
        'UPDATE unit_joint_venture_periods SET ended_at = ? WHERE id = ?',
        (ended_at, int(current['id'])),
    )
    return {**dict(current), 'ended_at': ended_at}


def start_unit_joint_venture_period(
    connection,
    unit_id: int,
    joint_venture_name: str,
    *,
    created_by: str,
    started_at: str | None = None,
):
    normalized_name = _normalize_name(joint_venture_name)
    if not normalized_name:
        raise ValueError('joint_venture_name é obrigatório.')

    started_at = started_at or _now_iso()
    unit = connection.execute('SELECT id, company_id FROM units WHERE id = ?', (int(unit_id),)).fetchone()
    if not unit:
        raise ValueError('Unidade não encontrada.')

    end_unit_joint_venture_period(connection, unit_id, ended_at=started_at)

    created_at = _now_iso()
    connection.execute(
        '''
        INSERT INTO unit_joint_venture_periods
            (company_id, unit_id, joint_venture_name, started_at, ended_at, created_by, created_at)
        VALUES (?, ?, ?, ?, NULL, ?, ?)
        ''',
        (int(unit['company_id']), int(unit_id), normalized_name, started_at, str(created_by or '').strip(), created_at),
    )
    return get_current_unit_joint_venture(connection, unit_id)


def import_active_joinventures_from_epis(connection, *, created_by: str = MIGRATION_CREATED_BY) -> int:
    """Import active epis.active_joinventure as current JV periods (idempotent)."""
    rows = connection.execute(
        '''
        SELECT e.company_id, e.unit_id, TRIM(e.active_joinventure) AS joint_venture_name
        FROM epis e
        WHERE COALESCE(TRIM(e.active_joinventure), '') <> ''
          AND e.unit_id IS NOT NULL
        GROUP BY e.company_id, e.unit_id, TRIM(e.active_joinventure)
        ORDER BY e.unit_id ASC, joint_venture_name ASC
        '''
    ).fetchall()

    inserted = 0
    for row in rows:
        unit_id = int(row['unit_id'])
        name = _normalize_name(row['joint_venture_name'])
        if not name:
            continue

        current = get_current_unit_joint_venture(connection, unit_id)
        if current and _normalize_name(current['joint_venture_name']).lower() == name.lower():
            continue

        start_unit_joint_venture_period(
            connection,
            unit_id,
            name,
            created_by=created_by,
            started_at='1970-01-01T00:00:00+00:00',
        )
        inserted += 1

    return inserted
