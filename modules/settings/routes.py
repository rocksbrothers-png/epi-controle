"""Rotas de configurações e regras do sistema."""

from contextlib import closing
from urllib.parse import parse_qs

from core.auth import require_configuration_admin, require_master_admin
from core.database import get_connection
from core.permissions import PERM_SETTINGS_VIEW
from core.repository import authorize_action
from core.security import resolve_actor_user_id
from epi_backend.http_utils import require_fields, send_json
from epi_backend.rule_engine import (
    build_context as build_rule_context,
    evaluate_rule_decision,
    should_enable_new_engine,
)
from modules.settings.service import (
    get_configuration_framework,
    get_configuration_rules,
    get_ficha_config,
    get_ficha_retention_policy,
    save_configuration_framework,
    save_configuration_rules,
    save_ficha_config,
    save_ficha_retention_policy,
)


# ── GET ───────────────────────────────────────────────────────────────────────

def handle_get_ficha_config(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_SETTINGS_VIEW)
        config = get_ficha_config(connection, actor['company_id'])
        return send_json(handler, 200, config)


def handle_get_configuration_rules(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_SETTINGS_VIEW)
        require_configuration_admin(actor)
        rules = get_configuration_rules(connection, actor['company_id'])
        return send_json(handler, 200, {'rules': rules})


def handle_get_configuration_framework(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_SETTINGS_VIEW)
        require_master_admin(actor, 'Somente Administrador Master pode acessar o framework de hardening.')
        framework = get_configuration_framework(connection, actor['company_id'])
        return send_json(handler, 200, {'framework': framework})


def handle_get_rules_engine_shadow_diff(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_SETTINGS_VIEW)
        require_master_admin(actor, 'Somente Administrador Master pode consultar divergências do shadow mode.')
        from urllib.parse import parse_qs as _parse_qs
        query = _parse_qs(parsed.query)
        limit = min(int(query.get('limit', ['200'])[0] or 200), 500)
        rows = connection.execute(
            'SELECT id, company_id, user_id, role, endpoint, dataset, mode, '
            'legacy_count, new_count, has_diff, legacy_only, new_only, created_at '
            'FROM rule_engine_shadow_log '
            'WHERE company_id = ? '
            'ORDER BY id DESC LIMIT ?',
            (int(actor['company_id']), limit),
        ).fetchall()
        import json as _json
        items = []
        for r in rows:
            d = dict(r)
            d['legacy_only'] = _json.loads(d.get('legacy_only') or '[]')
            d['new_only'] = _json.loads(d.get('new_only') or '[]')
            d['has_diff'] = bool(d['has_diff'])
            items.append(d)
        total = len(items)
        diff_count = sum(1 for i in items if i['has_diff'])
        return send_json(handler, 200, {
            'total': total,
            'diff_count': diff_count,
            'no_diff_count': total - diff_count,
            'items': items,
        })


def handle_get_rules_engine_diagnostics(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_SETTINGS_VIEW)
        require_master_admin(actor, 'Somente Administrador Master pode consultar diagnósticos do motor de regras.')
        query = parse_qs(parsed.query)
        endpoint_name = str(query.get('endpoint', [''])[0] or '').strip()
        report_type = str(query.get('report_type', [''])[0] or '').strip()
        unit_id = int(query.get('unit_id', ['0'])[0] or 0)
        jv_context = str(query.get('jv_context', ['outside_jv'])[0] or 'outside_jv')
        framework = get_configuration_framework(connection, actor['company_id'])
        context = build_rule_context(actor, endpoint=endpoint_name, unit_id=unit_id or None, jv_context=jv_context)
        decision = evaluate_rule_decision(context, framework, report_type=report_type)
        return send_json(handler, 200, {
            'enabled': should_enable_new_engine(context, framework),
            'decision': decision,
        })


def handle_get_ficha_retention_policy(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_SETTINGS_VIEW)
        require_configuration_admin(actor)
        policy = get_ficha_retention_policy(connection, actor.get('company_id'))
        return send_json(handler, 200, policy)


# ── POST ──────────────────────────────────────────────────────────────────────

def handle_post_ficha_config(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_SETTINGS_VIEW)
        require_configuration_admin(actor)
        save_ficha_config(connection, actor['company_id'], payload)
        connection.commit()
        return send_json(handler, 200, {'ok': True})


def handle_post_configuration_rules(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_SETTINGS_VIEW)
        require_configuration_admin(actor)
        save_configuration_rules(connection, actor['company_id'], payload.get('rules', []))
        connection.commit()
        return send_json(handler, 200, {'ok': True})


def handle_post_configuration_framework(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_SETTINGS_VIEW)
        require_master_admin(actor, 'Somente Administrador Master pode salvar o framework de hardening.')
        save_configuration_framework(connection, actor['company_id'], payload.get('framework', {}))
        connection.commit()
        return send_json(handler, 200, {'ok': True})


def handle_post_ficha_retention_policy(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_SETTINGS_VIEW)
        require_configuration_admin(actor)
        save_ficha_retention_policy(connection, actor['company_id'], payload)
        connection.commit()
        return send_json(handler, 200, {'ok': True})


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    router.register('GET',  '/api/ficha-config',              handle_get_ficha_config)
    router.register('GET',  '/api/configuration-rules',       handle_get_configuration_rules)
    router.register('GET',  '/api/configuration-framework',   handle_get_configuration_framework)
    router.register('GET',  '/api/rules-engine/diagnostics',  handle_get_rules_engine_diagnostics)
    router.register('GET',  '/api/rules-engine/shadow-diff',  handle_get_rules_engine_shadow_diff)
    router.register('GET',  '/api/ficha-retention-policy',    handle_get_ficha_retention_policy)
    router.register('POST', '/api/ficha-config',              handle_post_ficha_config)
    router.register('POST', '/api/configuration-rules',       handle_post_configuration_rules)
    router.register('POST', '/api/configuration-framework',   handle_post_configuration_framework)
    router.register('POST', '/api/ficha-retention-policy',    handle_post_ficha_retention_policy)
