"""Rotas de feedback de EPIs e avaliações."""

import re
from contextlib import closing
from urllib.parse import parse_qs

from core.database import get_connection
from core.permissions import (
    PERM_EPI_EVALUATION_DECIDE,
    PERM_EPI_EVALUATION_VIEW,
    PERM_EPI_FEEDBACK_ADMIN_APPROVE,
    PERM_EPI_FEEDBACK_CLOSE,
    PERM_EPI_FEEDBACK_HSEQ_REVIEW,
    PERM_EPI_FEEDBACK_MANAGER_EVAL,
    PERM_EPI_FEEDBACK_TRIAGE,
    PERM_EPI_FEEDBACK_VIEW,
    PERM_EPI_SUGGESTION_ACCEPT,
)
from core.repository import authorize_action
from core.security import resolve_actor_user_id
from epi_backend.http_utils import require_fields, send_json
from modules.feedback.service import (
    apply_accept_suggestion_as_epi,
    apply_admin_pre_evaluate,
    apply_admin_technical_evaluate,
    apply_feedback_admin_decision,
    apply_feedback_close,
    apply_feedback_forward_admin,
    apply_feedback_hseq_review,
    apply_feedback_manager_reject,
    apply_feedback_manager_validate,
    apply_feedback_triage,
    apply_set_reassessment,
    compute_epi_evaluation_status,
    fetch_avaliacoes_ranking,
    fetch_avaliacoes_summary,
    fetch_feedback_detail,
    fetch_feedbacks_for_manager,
    fetch_suggestion_ranking,
)


# ── GET ───────────────────────────────────────────────────────────────────────

def handle_get_feedbacks(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_EPI_FEEDBACK_VIEW)
        query = parse_qs(parsed.query)
        status_filter = str(query.get('status', [''])[0] or '').strip()
        type_filter = str(query.get('type', [''])[0] or '').strip()
        unit_filter = query.get('unit_id', [''])[0] or ''
        items = fetch_feedbacks_for_manager(connection, actor)
        if status_filter:
            items = [f for f in items if str(f.get('employee_portal_status') or '') == status_filter]
        if type_filter:
            items = [f for f in items if str(f.get('type') or '') == type_filter]
        if unit_filter:
            items = [f for f in items if str(f.get('unit_id') or '') == str(unit_filter)]
        return send_json(handler, 200, {'items': items})


def handle_get_feedback_detail(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_EPI_FEEDBACK_VIEW)
        fb_id = int(match.group(1))
        feedback = fetch_feedback_detail(connection, fb_id, actor)
        return send_json(handler, 200, {'item': feedback})


def handle_get_avaliacoes_summary(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_EPI_EVALUATION_VIEW)
        return send_json(handler, 200, fetch_avaliacoes_summary(connection, actor))


def handle_get_avaliacoes_ranking(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_EPI_EVALUATION_VIEW)
        return send_json(handler, 200, {'items': fetch_avaliacoes_ranking(connection, actor)})


def handle_get_avaliacoes_ranking_sugestoes(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_EPI_EVALUATION_VIEW)
        return send_json(handler, 200, {'items': fetch_suggestion_ranking(connection, actor)})


# ── POST ──────────────────────────────────────────────────────────────────────

def handle_post_feedbacks_triage(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        require_fields(payload, ['actor_user_id', 'feedback_id'])
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_EPI_FEEDBACK_TRIAGE)
        result = apply_feedback_triage(connection, actor, int(payload['feedback_id']), payload)
        connection.commit()
        return send_json(handler, 200, result)


def handle_post_feedbacks_hseq_review(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        require_fields(payload, ['actor_user_id', 'feedback_id', 'hseq_opinion'])
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_EPI_FEEDBACK_HSEQ_REVIEW)
        result = apply_feedback_hseq_review(connection, actor, int(payload['feedback_id']), payload)
        connection.commit()
        return send_json(handler, 200, result)


def handle_post_feedbacks_forward_admin(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        require_fields(payload, ['actor_user_id', 'feedback_id'])
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_EPI_FEEDBACK_TRIAGE)
        result = apply_feedback_forward_admin(connection, actor, int(payload['feedback_id']), payload)
        connection.commit()
        return send_json(handler, 200, result)


def handle_post_feedbacks_admin_decision(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        require_fields(payload, ['actor_user_id', 'feedback_id', 'decision', 'justification'])
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_EPI_FEEDBACK_ADMIN_APPROVE)
        result = apply_feedback_admin_decision(connection, actor, int(payload['feedback_id']), payload)
        connection.commit()
        return send_json(handler, 200, result)


def handle_post_feedbacks_close(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        require_fields(payload, ['actor_user_id', 'feedback_id'])
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_EPI_FEEDBACK_CLOSE)
        result = apply_feedback_close(connection, actor, int(payload['feedback_id']), payload)
        connection.commit()
        return send_json(handler, 200, result)


def handle_post_feedbacks_manager_validate(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        require_fields(payload, ['actor_user_id', 'feedback_id'])
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_EPI_FEEDBACK_MANAGER_EVAL)
        result = apply_feedback_manager_validate(connection, actor, int(payload['feedback_id']), payload)
        connection.commit()
        return send_json(handler, 200, result)


def handle_post_feedbacks_manager_reject(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        require_fields(payload, ['actor_user_id', 'feedback_id', 'rejection_reason'])
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_EPI_FEEDBACK_MANAGER_EVAL)
        result = apply_feedback_manager_reject(connection, actor, int(payload['feedback_id']), payload)
        connection.commit()
        return send_json(handler, 200, result)


def handle_post_avaliacoes_set_reassessment(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        require_fields(payload, ['actor_user_id', 'feedback_id', 'period'])
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_EPI_EVALUATION_DECIDE)
        result = apply_set_reassessment(connection, actor, int(payload['feedback_id']), payload)
        connection.commit()
        return send_json(handler, 200, result)


def handle_post_avaliacoes_compute_status(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        require_fields(payload, ['actor_user_id'])
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_EPI_EVALUATION_DECIDE)
        result = compute_epi_evaluation_status(connection, actor)
        connection.commit()
        return send_json(handler, 200, result)


def handle_post_avaliacoes_accept_suggestion(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        require_fields(payload, ['actor_user_id', 'feedback_id'])
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_EPI_SUGGESTION_ACCEPT)
        result = apply_accept_suggestion_as_epi(connection, actor, int(payload['feedback_id']), payload)
        connection.commit()
        return send_json(handler, 200, result)


def handle_post_avaliacoes_admin_evaluate(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        require_fields(payload, ['actor_user_id', 'feedback_id', 'tech_decision'])
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_EPI_EVALUATION_DECIDE)
        result = apply_admin_technical_evaluate(connection, actor, int(payload['feedback_id']), payload)
        connection.commit()
        return send_json(handler, 200, result)


def handle_post_avaliacoes_pre_evaluate(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        require_fields(payload, ['actor_user_id', 'feedback_id'])
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_EPI_EVALUATION_DECIDE)
        if actor.get('role') not in ('master_admin', 'general_admin'):
            raise PermissionError('Avaliação prévia é restrita a Administrador Master e Administrador Geral.')
        result = apply_admin_pre_evaluate(connection, actor, int(payload['feedback_id']), payload)
        connection.commit()
        return send_json(handler, 200, result)


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    # GET
    router.register('GET', '/api/feedbacks',                     handle_get_feedbacks)
    router.register('GET', r'^/api/feedbacks/(\d+)$',            handle_get_feedback_detail, regex=True)
    router.register('GET', '/api/avaliacoes/summary',            handle_get_avaliacoes_summary)
    router.register('GET', '/api/avaliacoes/ranking',            handle_get_avaliacoes_ranking)
    router.register('GET', '/api/avaliacoes/ranking-sugestoes',  handle_get_avaliacoes_ranking_sugestoes)
    # POST
    router.register('POST', '/api/feedbacks/triage',             handle_post_feedbacks_triage)
    router.register('POST', '/api/feedbacks/hseq-review',        handle_post_feedbacks_hseq_review)
    router.register('POST', '/api/feedbacks/forward-admin',      handle_post_feedbacks_forward_admin)
    router.register('POST', '/api/feedbacks/admin-decision',     handle_post_feedbacks_admin_decision)
    router.register('POST', '/api/feedbacks/close',              handle_post_feedbacks_close)
    router.register('POST', '/api/feedbacks/manager-validate',   handle_post_feedbacks_manager_validate)
    router.register('POST', '/api/feedbacks/manager-reject',     handle_post_feedbacks_manager_reject)
    router.register('POST', '/api/avaliacoes/set-reassessment',  handle_post_avaliacoes_set_reassessment)
    router.register('POST', '/api/avaliacoes/compute-status',    handle_post_avaliacoes_compute_status)
    router.register('POST', '/api/avaliacoes/accept-suggestion', handle_post_avaliacoes_accept_suggestion)
    router.register('POST', '/api/avaliacoes/admin-evaluate',    handle_post_avaliacoes_admin_evaluate)
    router.register('POST', '/api/avaliacoes/pre-evaluate',      handle_post_avaliacoes_pre_evaluate)
