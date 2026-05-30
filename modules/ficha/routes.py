"""Rotas de fichas de EPI."""

from contextlib import closing
from urllib.parse import parse_qs

from core.auth import ensure_resource_company, require_configuration_admin
from core.database import get_connection
from core.permissions import PERM_SETTINGS_UPDATE, PERM_SETTINGS_VIEW
from core.repository import actor_operational_unit_id, authorize_action
from core.security import resolve_actor_user_id
from epi_backend.db import row_to_dict
from epi_backend.http_utils import require_fields, send_json, structured_log
from modules.ficha.service import (
    apply_snapshot_retention,
    fetch_ficha_epi_audit_logs,
    is_valid_ficha_period_state,
    resolve_ficha_period_effective_status,
)
from modules.settings.service import (
    get_ficha_retention_policy,
    save_ficha_config,
    save_ficha_retention_policy,
)


# ── GET ───────────────────────────────────────────────────────────────────────

def handle_get_fichas(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(
            connection,
            resolve_actor_user_id(handler, parsed),
            'fichas:view'
        )
        clauses = []
        params = []
        if actor['role'] != 'master_admin':
            clauses.append('fp.company_id = ?')
            params.append(actor['company_id'])
        scope_unit_id = actor_operational_unit_id(connection, actor)
        if scope_unit_id:
            clauses.append('fp.unit_id = ?')
            params.append(int(scope_unit_id))
        employee_id = parse_qs(parsed.query).get('employee_id', [''])[0]
        if employee_id:
            clauses.append('fp.employee_id = ?')
            params.append(int(employee_id))
        final_where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
        periods = connection.execute(
            (
                'SELECT fp.*, employees.name AS employee_name, employees.employee_id_code, units.name AS unit_name, '
                '(SELECT COUNT(*) FROM epi_ficha_items fi WHERE fi.ficha_period_id = fp.id) AS total_items, '
                "(SELECT COUNT(*) FROM epi_ficha_items fi WHERE fi.ficha_period_id = fp.id AND COALESCE(fi.item_signature_at, '') = '') AS pending_items "
                'FROM epi_ficha_periods fp '
                'JOIN employees ON employees.id = fp.employee_id '
                'JOIN units ON units.id = fp.unit_id '
                f'{final_where} '
                'ORDER BY fp.period_start DESC, fp.id DESC'
            ),
            tuple(params)
        ).fetchall()
        period_items = [resolve_ficha_period_effective_status(connection, row_to_dict(item)) for item in periods]
        period_items = [item for item in period_items if is_valid_ficha_period_state(item)]
        connection.commit()
        return send_json(handler, 200, {'items': period_items})


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


def handle_get_ficha_epi_audit(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_SETTINGS_VIEW)
        query = parse_qs(parsed.query)
        filters = {
            'employee_id': str(query.get('employee_id', [''])[0] or '').strip(),
            'actor_user_id': str(query.get('actor_user_id', [''])[0] or '').strip(),
            'action': str(query.get('action', [''])[0] or '').strip(),
            'date_from': str(query.get('date_from', [''])[0] or '').strip(),
            'date_to': str(query.get('date_to', [''])[0] or '').strip(),
        }
        filters = {k: v for k, v in filters.items() if v}
        try:
            items = fetch_ficha_epi_audit_logs(connection, actor, filters)
        except Exception as error:
            structured_log(
                'warning',
                'ficha.audit.fetch_failed',
                actor_user_id=actor.get('id'),
                error=str(error),
            )
            return send_json(
                handler,
                503,
                {
                    'error': 'Histórico temporariamente indisponível. Tente novamente.',
                    'code': 'FICHA_AUDIT_UNAVAILABLE',
                },
            )
        return send_json(handler, 200, {'items': items})


# ── PUT ───────────────────────────────────────────────────────────────────────

def handle_put_ficha_config(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_SETTINGS_UPDATE)
        save_ficha_config(connection, actor['company_id'], payload)
        return send_json(handler, 200, {'ok': True})


def handle_put_ficha_retention_policy(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_SETTINGS_UPDATE)
        require_configuration_admin(actor)
        policy = save_ficha_retention_policy(connection, actor.get('company_id'), payload)
        return send_json(handler, 200, policy)


def handle_put_ficha_archive_purge(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_SETTINGS_UPDATE)
        require_configuration_admin(actor)
        policy = get_ficha_retention_policy(connection, actor.get('company_id'))
        apply_snapshot_retention(
            connection,
            actor.get('company_id') if actor.get('role') != 'master_admin' else None,
            policy,
        )
        return send_json(handler, 200, {'ok': True, 'policy': policy})


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    router.register('GET', '/api/fichas',                     handle_get_fichas)
    router.register('GET', '/api/ficha-epi-snapshots',        handle_get_ficha_epi_snapshots)
    router.register('GET', '/api/ficha-epi-audit',            handle_get_ficha_epi_audit)
    router.register('PUT', '/api/ficha-config',               handle_put_ficha_config)
    router.register('PUT', '/api/ficha-retention-policy',     handle_put_ficha_retention_policy)
    router.register('PUT', '/api/ficha-archive/purge-expired', handle_put_ficha_archive_purge)

