from epi_backend.rule_engine import (
    build_context,
    compute_visibility_diff,
    default_framework_payload,
    normalize_framework_payload,
    resolve_execution_plan,
    resolve_visibility_filters,
)


def test_defaults_are_non_invasive():
    ctx = build_context({'company_id': 10, 'id': 1, 'role': 'admin'}, endpoint='/api/bootstrap')
    framework = normalize_framework_payload({})
    plan = resolve_execution_plan(ctx, framework)
    visibility = resolve_visibility_filters(ctx, framework)
    assert plan['mode'] == 'off'
    assert plan['evaluate_in_background'] is False
    assert visibility['fallback_mode'] is True
    assert visibility['allow_epis'] is True


def test_rollout_can_target_and_shadow_mode_without_enforcement():
    framework = default_framework_payload()
    framework['feature_flags'].update({
        'enable_new_rules_engine': True,
        'execution_mode': 'shadow',
        'enabled_endpoints': ['/api/bootstrap'],
        'rollout_percentage': 100,
    })
    normalized = normalize_framework_payload(framework)
    ctx = build_context({'company_id': 1, 'id': 55, 'role': 'registry_admin'}, endpoint='/api/bootstrap')
    plan = resolve_execution_plan(ctx, normalized)
    assert plan['targeted'] is True
    assert plan['evaluate_in_background'] is True
    assert plan['legacy_is_source_of_truth'] is True


def test_visibility_diff_detects_missing_ids():
    diff = compute_visibility_diff(['1', '2', '3'], ['1', '3', '4'])
    assert diff['has_diff'] is True
    assert diff['legacy_only'] == ['2']
    assert diff['new_only'] == ['4']
