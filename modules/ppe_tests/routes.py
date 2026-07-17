"""Rotas do fluxo de Avaliação e Homologação de EPI em Teste.

Observação: o servidor HTTP legado atende GET/POST/PUT/DELETE (sem PATCH);
as atualizações usam POST em sub-rotas explícitas (/update, /decision, ...).
"""

from contextlib import closing
from urllib.parse import parse_qs

from core.database import get_connection
from core.permissions import (
    PERM_PPE_TEST_DECIDE,
    PERM_PPE_TEST_EVALUATE,
    PERM_PPE_TEST_HOMOLOGATE,
    PERM_PPE_TEST_MANAGE,
    PERM_PPE_TEST_SUGGEST,
    PERM_PPE_TEST_TECH_REVIEW,
    PERM_PPE_TEST_TRIAGE,
    PERM_PPE_TEST_VIEW,
)
from core.repository import authorize_action
from core.security import resolve_actor_user_id
from epi_backend.http_utils import require_fields, send_json
from modules.ppe_tests.service import (
    add_participant,
    apply_decision,
    apply_suggestion_triage,
    apply_technical_review,
    complete_test,
    compute_test_results,
    create_candidate,
    create_suggestion,
    create_suggestion_from_feedback,
    fetch_candidate_detail,
    fetch_candidates,
    fetch_suggestion_detail,
    fetch_suggestions,
    homologate_candidate,
    register_distribution,
    register_evaluation,
    register_incident,
    reject_candidate,
    resolve_incident,
    resume_test,
    save_test_plan,
    start_test,
    suspend_test,
    update_candidate,
    update_participant_status,
)


def _query_filters(parsed):
    query = parse_qs(parsed.query)
    return {'status': str(query.get('status', [''])[0] or '').strip()}


# ── Sugestões ─────────────────────────────────────────────────────────────────

def handle_get_suggestions(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_PPE_TEST_VIEW)
        items = fetch_suggestions(connection, actor, _query_filters(parsed))
        return send_json(handler, 200, {'items': items})


def handle_get_suggestion_detail(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_PPE_TEST_VIEW)
        item = fetch_suggestion_detail(connection, actor, int(match.group(1)))
        return send_json(handler, 200, {'item': item})


def handle_post_suggestions(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        require_fields(payload, ['actor_user_id', 'suggested_name'])
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_PPE_TEST_SUGGEST)
        result = create_suggestion(connection, actor, payload)
        connection.commit()
        return send_json(handler, 200, result)


def handle_post_suggestion_from_feedback(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        require_fields(payload, ['actor_user_id', 'feedback_id'])
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_PPE_TEST_TRIAGE)
        result = create_suggestion_from_feedback(connection, actor, int(payload['feedback_id']), payload)
        connection.commit()
        return send_json(handler, 200, result)


def handle_post_suggestion_triage(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        require_fields(payload, ['actor_user_id', 'result'])
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_PPE_TEST_TRIAGE)
        result = apply_suggestion_triage(connection, actor, int(match.group(1)), payload)
        connection.commit()
        return send_json(handler, 200, result)


# ── Testes (cadastro provisório + ciclo de vida) ──────────────────────────────

def handle_get_tests(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_PPE_TEST_VIEW)
        items = fetch_candidates(connection, actor, _query_filters(parsed))
        return send_json(handler, 200, {'items': items})


def handle_get_test_detail(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_PPE_TEST_VIEW)
        item = fetch_candidate_detail(connection, actor, int(match.group(1)))
        return send_json(handler, 200, {'item': item})


def handle_get_test_results(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_PPE_TEST_VIEW)
        results = compute_test_results(connection, actor, int(match.group(1)))
        return send_json(handler, 200, {'results': results})


def handle_post_tests(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        require_fields(payload, ['actor_user_id', 'name'])
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_PPE_TEST_MANAGE)
        result = create_candidate(connection, actor, payload)
        connection.commit()
        return send_json(handler, 200, result)


def _make_candidate_action(service_fn, permission, required=('actor_user_id',)):
    def _handler(handler, parsed, payload, match):
        with closing(get_connection()) as connection:
            require_fields(payload, list(required))
            actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), permission)
            result = service_fn(connection, actor, int(match.group(1)), payload)
            connection.commit()
            return send_json(handler, 200, result)
    return _handler


handle_post_test_update = _make_candidate_action(update_candidate, PERM_PPE_TEST_MANAGE)
handle_post_test_technical_review = _make_candidate_action(
    apply_technical_review, PERM_PPE_TEST_TECH_REVIEW, ('actor_user_id', 'result'))
handle_post_test_plan = _make_candidate_action(
    save_test_plan, PERM_PPE_TEST_MANAGE, ('actor_user_id', 'start_date', 'end_date'))
handle_post_test_start = _make_candidate_action(start_test, PERM_PPE_TEST_MANAGE)
handle_post_test_suspend = _make_candidate_action(
    suspend_test, PERM_PPE_TEST_MANAGE, ('actor_user_id', 'reason'))
handle_post_test_resume = _make_candidate_action(resume_test, PERM_PPE_TEST_MANAGE)
handle_post_test_complete = _make_candidate_action(complete_test, PERM_PPE_TEST_MANAGE)
handle_post_test_participants = _make_candidate_action(
    add_participant, PERM_PPE_TEST_MANAGE, ('actor_user_id', 'employee_id'))
handle_post_test_distributions = _make_candidate_action(
    register_distribution, PERM_PPE_TEST_MANAGE, ('actor_user_id', 'movement_type'))
handle_post_test_evaluations = _make_candidate_action(
    register_evaluation, PERM_PPE_TEST_EVALUATE, ('actor_user_id', 'participant_id', 'stage', 'ratings'))
handle_post_test_incidents = _make_candidate_action(
    register_incident, PERM_PPE_TEST_EVALUATE, ('actor_user_id', 'incident_type', 'description'))
handle_post_test_decision = _make_candidate_action(
    apply_decision, PERM_PPE_TEST_DECIDE, ('actor_user_id', 'decision', 'reason'))
handle_post_test_homologate = _make_candidate_action(
    homologate_candidate, PERM_PPE_TEST_HOMOLOGATE)
handle_post_test_reject = _make_candidate_action(
    reject_candidate, PERM_PPE_TEST_DECIDE, ('actor_user_id', 'reason'))


def handle_post_participant_status(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        require_fields(payload, ['actor_user_id', 'status'])
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_PPE_TEST_MANAGE)
        result = update_participant_status(
            connection, actor, int(match.group(1)), int(match.group(2)), payload)
        connection.commit()
        return send_json(handler, 200, result)


def handle_post_incident_resolve(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        require_fields(payload, ['actor_user_id', 'conclusion_notes'])
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_PPE_TEST_MANAGE)
        result = resolve_incident(
            connection, actor, int(match.group(1)), int(match.group(2)), payload)
        connection.commit()
        return send_json(handler, 200, result)


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    # GET
    router.register('GET', '/api/ppe-test-suggestions',                    handle_get_suggestions)
    router.register('GET', r'^/api/ppe-test-suggestions/(\d+)$',           handle_get_suggestion_detail, regex=True)
    router.register('GET', '/api/ppe-tests',                               handle_get_tests)
    router.register('GET', r'^/api/ppe-tests/(\d+)$',                      handle_get_test_detail, regex=True)
    router.register('GET', r'^/api/ppe-tests/(\d+)/results$',              handle_get_test_results, regex=True)
    # POST — sugestões
    router.register('POST', '/api/ppe-test-suggestions',                   handle_post_suggestions)
    router.register('POST', '/api/ppe-test-suggestions/from-feedback',     handle_post_suggestion_from_feedback)
    router.register('POST', r'^/api/ppe-test-suggestions/(\d+)/triage$',   handle_post_suggestion_triage, regex=True)
    # POST — testes
    router.register('POST', '/api/ppe-tests',                              handle_post_tests)
    router.register('POST', r'^/api/ppe-tests/(\d+)/update$',              handle_post_test_update, regex=True)
    router.register('POST', r'^/api/ppe-tests/(\d+)/technical-review$',    handle_post_test_technical_review, regex=True)
    router.register('POST', r'^/api/ppe-tests/(\d+)/plan$',                handle_post_test_plan, regex=True)
    router.register('POST', r'^/api/ppe-tests/(\d+)/start$',               handle_post_test_start, regex=True)
    router.register('POST', r'^/api/ppe-tests/(\d+)/suspend$',             handle_post_test_suspend, regex=True)
    router.register('POST', r'^/api/ppe-tests/(\d+)/resume$',              handle_post_test_resume, regex=True)
    router.register('POST', r'^/api/ppe-tests/(\d+)/complete$',            handle_post_test_complete, regex=True)
    router.register('POST', r'^/api/ppe-tests/(\d+)/participants$',        handle_post_test_participants, regex=True)
    router.register('POST', r'^/api/ppe-tests/(\d+)/participants/(\d+)/status$', handle_post_participant_status, regex=True)
    router.register('POST', r'^/api/ppe-tests/(\d+)/distributions$',       handle_post_test_distributions, regex=True)
    router.register('POST', r'^/api/ppe-tests/(\d+)/evaluations$',         handle_post_test_evaluations, regex=True)
    router.register('POST', r'^/api/ppe-tests/(\d+)/incidents$',           handle_post_test_incidents, regex=True)
    router.register('POST', r'^/api/ppe-tests/(\d+)/incidents/(\d+)/resolve$', handle_post_incident_resolve, regex=True)
    router.register('POST', r'^/api/ppe-tests/(\d+)/decision$',            handle_post_test_decision, regex=True)
    router.register('POST', r'^/api/ppe-tests/(\d+)/homologate$',          handle_post_test_homologate, regex=True)
    router.register('POST', r'^/api/ppe-tests/(\d+)/reject$',              handle_post_test_reject, regex=True)
