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
    get_rule_engine_status,
    promote_rule_engine,
    save_configuration_framework,
    save_configuration_rules,
    save_ficha_config,
    save_ficha_retention_policy,
    delete_shadow_log,
    fetch_shadow_log,
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


def handle_get_rules_engine_status(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_SETTINGS_VIEW)
        require_master_admin(actor, 'Somente Administrador Master pode consultar o status do motor de regras.')
        status = get_rule_engine_status(connection, actor['company_id'])
        return send_json(handler, 200, status)


def handle_post_rules_engine_promote(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_SETTINGS_VIEW)
        require_master_admin(actor, 'Somente Administrador Master pode promover o motor de regras.')
        mode = str(payload.get('mode') or 'shadow').strip().lower()
        rollout = int(payload.get('rollout_percentage') or 0)
        enable = bool(payload.get('enable', True))
        framework = promote_rule_engine(connection, actor['company_id'], mode=mode, rollout_percentage=rollout, enable=enable)
        connection.commit()
        return send_json(handler, 200, {
            'ok': True,
            'mode': framework['feature_flags']['execution_mode'],
            'rollout_percentage': framework['feature_flags']['rollout_percentage'],
            'enabled': framework['feature_flags']['enable_new_rules_engine'],
        })


def handle_delete_rules_engine_shadow_diff(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_SETTINGS_VIEW)
        require_master_admin(actor, 'Somente Administrador Master pode limpar o log de shadow diff.')
        delete_shadow_log(connection, actor['company_id'])
        connection.commit()
        return send_json(handler, 200, {'ok': True})


def handle_get_rules_engine_shadow_diff(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_SETTINGS_VIEW)
        require_master_admin(actor, 'Somente Administrador Master pode consultar divergências do shadow mode.')
        query = parse_qs(parsed.query)
        limit = min(int(query.get('limit', ['200'])[0] or 200), 500)
        items = fetch_shadow_log(connection, actor['company_id'], limit)
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
    router.register('GET',  '/api/rules-engine/status',       handle_get_rules_engine_status)
    router.register('GET',  '/api/rules-engine/shadow-diff',  handle_get_rules_engine_shadow_diff)
    router.register('POST', '/api/rules-engine/promote',      handle_post_rules_engine_promote)
    router.register('DELETE', '/api/rules-engine/shadow-diff', handle_delete_rules_engine_shadow_diff)
    router.register('GET',  '/api/ficha-retention-policy',    handle_get_ficha_retention_policy)
    router.register('POST', '/api/ficha-config',              handle_post_ficha_config)
    router.register('POST', '/api/configuration-rules',       handle_post_configuration_rules)
    router.register('POST', '/api/configuration-framework',   handle_post_configuration_framework)
    router.register('POST', '/api/ficha-retention-policy',    handle_post_ficha_retention_policy)
