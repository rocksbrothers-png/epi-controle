"""Migration helpers for unit JV periods (Entrega 1, not auto-wired yet)."""

from __future__ import annotations

from epi_backend.unit_jv_lifecycle import (
    ensure_unit_joint_venture_periods_table,
    import_active_joinventures_from_epis,
)


MIGRATION_ID = '001_unit_jv_periods'


def run(connection) -> dict[str, int | str]:
    """Create `unit_joint_venture_periods` and import active JV states.

    This function is idempotent and can be safely called multiple times.
    """

    ensure_unit_joint_venture_periods_table(connection)
    imported_rows = import_active_joinventures_from_epis(connection)
    return {
        'migration_id': MIGRATION_ID,
        'imported_rows': int(imported_rows),
    }
