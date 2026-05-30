"""Rotas de fichas de EPI.

Nota: as rotas complexas de ficha (finalize, repair-status, fichas list)
dependem de funções ainda em server_postgres.py e serão extraídas na Fase 6
quando register_ficha_epi_audit, resolve_ficha_period_effective_status e
build_ficha_epi_html forem movidas para este módulo de serviço.
"""

from contextlib import closing
from urllib.parse import parse_qs

from core.auth import ensure_resource_company
from core.database import get_connection
from core.permissions import PERM_SETTINGS_VIEW
from core.repository import actor_operational_unit_id, authorize_action
from core.security import resolve_actor_user_id
from epi_backend.db import row_to_dict
from epi_backend.http_utils import send_json


# ── GET ───────────────────────────────────────────────────────────────────────

def handle_get_ficha_epi_snapshots(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'reports:view')
        query = parse_qs(parsed.query)
        clauses, params = [], []
        if actor.get('role') != 'master_admin':
            clauses.append('s.company_id = %s')
            params.append(int(actor['company_id']))
        scope_unit_id = actor_operational_unit_id(connection, actor)
        if scope_unit_id:
            clauses.append('s.unit_id = %s')
            params.append(int(scope_unit_id))
        if query.get('employee_id'):
            clauses.append('s.employee_id = %s')
            params.append(int(query['employee_id'][0]))
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ''
        rows = connection.execute(
            f'SELECT s.id, s.ficha_period_id, s.company_id, s.unit_id, s.employee_id, '
            f's.generated_at, s.expires_at, '
            f'employees.name AS employee_name, units.name AS unit_name '
            f'FROM ficha_epi_snapshots s '
            f'JOIN employees ON employees.id = s.employee_id '
            f'JOIN units ON units.id = s.unit_id '
            f'{where_sql} '
            f'ORDER BY s.generated_at DESC, s.id DESC LIMIT 500',
            tuple(params),
        ).fetchall()
        return send_json(handler, 200, {'items': [row_to_dict(item) for item in rows]})


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    router.register('GET', '/api/ficha-epi-snapshots', handle_get_ficha_epi_snapshots)
