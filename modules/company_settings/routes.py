"""Rotas de "Minha Empresa" (Administrador Geral) e suporte excepcional (Master).

- GET/PUT /api/my-company: o Administrador Geral consulta e configura a
  própria empresa. O company_id NUNCA vem do frontend: é sempre derivado do
  vínculo do usuário autenticado (proteção contra troca manual de tenant).
- POST /api/my-company/onboarding-complete: conclui o assistente de implantação.
- POST /api/companies/{id}/support-update: alteração excepcional pelo
  Administrador Master, exigindo justificativa e registrada em auditoria.
"""

from contextlib import closing

from core.database import get_connection
from core.permissions import (
    PERM_COMPANIES_SUPPORT,
    PERM_COMPANY_SETTINGS_UPDATE,
    PERM_COMPANY_SETTINGS_VIEW,
)
from core.repository import authorize_action
from core.security import resolve_actor_user_id
from epi_backend.http_utils import send_json, structured_log
from modules.companies.service import get_company_full, register_company_audit
from modules.company_settings.service import (
    complete_onboarding,
    get_my_company_profile,
    summarize_profile_changes,
    update_my_company,
    validate_my_company_payload,
)
from modules.tenant.domains_service import (
    delete_company_domain,
    list_company_domains,
    register_company_domain,
    set_primary_company_domain,
    verify_company_domain,
)

_MIN_SUPPORT_REASON_LENGTH = 10


def _require_own_company_id(actor) -> int:
    company_id = actor.get('company_id')
    if not company_id:
        raise ValueError('Usuário autenticado não possui empresa vinculada.')
    return int(company_id)


# ── GET /api/my-company ───────────────────────────────────────────────────────

def handle_get_my_company(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(
            connection, resolve_actor_user_id(handler, parsed), PERM_COMPANY_SETTINGS_VIEW
        )
        company_id = _require_own_company_id(actor)
        profile = get_my_company_profile(connection, company_id)
        return send_json(handler, 200, {'ok': True, 'company': profile})


# ── PUT /api/my-company ───────────────────────────────────────────────────────

def handle_put_my_company(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(
            connection, resolve_actor_user_id(handler, parsed, payload), PERM_COMPANY_SETTINGS_UPDATE
        )
        company_id = _require_own_company_id(actor)
        previous = get_company_full(connection, company_id)
        if not previous:
            return send_json(handler, 404, {'error': 'Empresa não encontrada.'})
        fields = validate_my_company_payload(connection, payload or {}, company_id, previous)
        if not fields:
            return send_json(handler, 400, {'error': 'Nenhum campo editável informado.'})
        update_my_company(connection, company_id, fields)
        summary, details = summarize_profile_changes(previous, fields)
        register_company_audit(connection, company_id, actor, 'self_update', summary, details)
        connection.commit()
        structured_log(
            'info', 'company_settings.updated',
            company_id=company_id, actor_user_id=actor['id'], fields=sorted(fields.keys()),
        )
        profile = get_my_company_profile(connection, company_id)
        return send_json(handler, 200, {'ok': True, 'company': profile})


# ── POST /api/my-company/onboarding-complete ─────────────────────────────────

def handle_post_onboarding_complete(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(
            connection, resolve_actor_user_id(handler, parsed, payload), PERM_COMPANY_SETTINGS_UPDATE
        )
        company_id = _require_own_company_id(actor)
        completed_at = complete_onboarding(connection, company_id)
        register_company_audit(
            connection, company_id, actor, 'onboarding_complete',
            'Assistente de implantação concluído pelo Administrador Geral.',
            [{'field': 'Implantação', 'before': 'pendente', 'after': f'concluída em {completed_at}'}],
        )
        connection.commit()
        structured_log(
            'info', 'company_settings.onboarding_completed',
            company_id=company_id, actor_user_id=actor['id'],
        )
        return send_json(handler, 200, {'ok': True, 'onboarding_completed_at': completed_at})


# ── Domínios da tenant (tenant_domains) ──────────────────────────────────────

def handle_get_my_company_domains(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(
            connection, resolve_actor_user_id(handler, parsed), PERM_COMPANY_SETTINGS_VIEW
        )
        company_id = _require_own_company_id(actor)
        return send_json(handler, 200, {'ok': True, 'domains': list_company_domains(connection, company_id)})


def handle_post_my_company_domains(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(
            connection, resolve_actor_user_id(handler, parsed, payload), PERM_COMPANY_SETTINGS_UPDATE
        )
        company_id = _require_own_company_id(actor)
        payload = payload or {}
        record = register_company_domain(
            connection, company_id, payload.get('domain'), payload.get('domain_type')
        )
        register_company_audit(
            connection, company_id, actor, 'self_update',
            f"Domínio registrado: {record['full_host']} ({record['type_label']}).",
            [{'field': 'Domínio', 'before': '', 'after': f"{record['full_host']} [{record['verification_status']}]"}],
        )
        connection.commit()
        return send_json(handler, 201, {'ok': True, 'domain': record})


def handle_post_my_company_domain_verify(handler, parsed, payload, match):
    domain_id = int(match.group(1))
    with closing(get_connection()) as connection:
        actor = authorize_action(
            connection, resolve_actor_user_id(handler, parsed, payload), PERM_COMPANY_SETTINGS_UPDATE
        )
        company_id = _require_own_company_id(actor)
        record = verify_company_domain(connection, company_id, domain_id)
        register_company_audit(
            connection, company_id, actor, 'self_update',
            f"Domínio verificado: {record['full_host']} (SSL: {record['ssl_status']}).",
            [{'field': 'Domínio', 'before': 'pending', 'after': f"verified (SSL {record['ssl_status']})"}],
        )
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'domain': record})


def handle_post_my_company_domain_primary(handler, parsed, payload, match):
    domain_id = int(match.group(1))
    with closing(get_connection()) as connection:
        actor = authorize_action(
            connection, resolve_actor_user_id(handler, parsed, payload), PERM_COMPANY_SETTINGS_UPDATE
        )
        company_id = _require_own_company_id(actor)
        record = set_primary_company_domain(connection, company_id, domain_id)
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'domain': record})


def handle_delete_my_company_domain(handler, parsed, payload, match):
    domain_id = int(match.group(1))
    with closing(get_connection()) as connection:
        actor = authorize_action(
            connection, resolve_actor_user_id(handler, parsed, payload), PERM_COMPANY_SETTINGS_UPDATE
        )
        company_id = _require_own_company_id(actor)
        record = delete_company_domain(connection, company_id, domain_id)
        register_company_audit(
            connection, company_id, actor, 'self_update',
            f"Domínio removido: {record['full_host']}.",
            [{'field': 'Domínio', 'before': record['full_host'], 'after': ''}],
        )
        connection.commit()
        return send_json(handler, 200, {'ok': True})


# ── POST /api/companies/{id}/support-update ──────────────────────────────────

def handle_post_company_support_update(handler, parsed, payload, match):
    company_id = int(match.group(1))
    with closing(get_connection()) as connection:
        actor = authorize_action(
            connection, resolve_actor_user_id(handler, parsed, payload), PERM_COMPANIES_SUPPORT
        )
        if actor.get('role') != 'master_admin':
            raise PermissionError('Apenas o Administrador Master pode executar suporte excepcional.')
        reason = str((payload or {}).get('support_reason') or '').strip()
        if len(reason) < _MIN_SUPPORT_REASON_LENGTH:
            raise ValueError(
                'Informe a justificativa do suporte (support_reason) com pelo menos '
                f'{_MIN_SUPPORT_REASON_LENGTH} caracteres.'
            )
        previous = get_company_full(connection, company_id)
        if not previous:
            return send_json(handler, 404, {'error': 'Empresa não encontrada.'})
        fields = validate_my_company_payload(connection, payload or {}, company_id, previous)
        if not fields:
            return send_json(handler, 400, {'error': 'Nenhum campo editável informado.'})
        update_my_company(connection, company_id, fields)
        summary, details = summarize_profile_changes(previous, fields)
        register_company_audit(
            connection, company_id, actor, 'support_update',
            f'[SUPORTE] {summary} Justificativa: {reason}', details,
        )
        connection.commit()
        structured_log(
            'warning', 'company_settings.support_update',
            company_id=company_id, actor_user_id=actor['id'],
            reason=reason, fields=sorted(fields.keys()),
        )
        return send_json(handler, 200, {'ok': True})


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    router.register('GET',  '/api/my-company',                       handle_get_my_company)
    router.register('PUT',  '/api/my-company',                       handle_put_my_company)
    router.register('POST', '/api/my-company/onboarding-complete',   handle_post_onboarding_complete)
    router.register('GET',  '/api/my-company/domains',               handle_get_my_company_domains)
    router.register('POST', '/api/my-company/domains',               handle_post_my_company_domains)
    router.register('POST', r'^/api/my-company/domains/(\d+)/verify$',  handle_post_my_company_domain_verify, regex=True)
    router.register('POST', r'^/api/my-company/domains/(\d+)/primary$', handle_post_my_company_domain_primary, regex=True)
    router.register('DELETE', r'^/api/my-company/domains/(\d+)$',       handle_delete_my_company_domain, regex=True)
    router.register('POST', r'^/api/companies/(\d+)/support-update$', handle_post_company_support_update, regex=True)
