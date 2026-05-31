import pytest
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


def _enforced_framework(rollout=100, enabled_companies=None):
    fw = default_framework_payload()
    fw['feature_flags'].update({
        'enable_new_rules_engine': True,
        'execution_mode': 'enforced',
        'rollout_percentage': rollout,
    })
    if enabled_companies is not None:
        fw['feature_flags']['enabled_company_ids'] = enabled_companies
    return normalize_framework_payload(fw)


def test_enforced_mode_sets_legacy_is_source_of_truth_false():
    fw = _enforced_framework()
    ctx = build_context({'company_id': 1, 'id': 99, 'role': 'admin'}, endpoint='/api/bootstrap')
    plan = resolve_execution_plan(ctx, fw)
    assert plan['mode'] == 'enforced'
    assert plan['targeted'] is True
    assert plan['evaluate_in_background'] is True
    assert plan['legacy_is_source_of_truth'] is False


def test_canary_mode_keeps_legacy_as_source_of_truth():
    fw = default_framework_payload()
    fw['feature_flags'].update({
        'enable_new_rules_engine': True,
        'execution_mode': 'canary',
        'rollout_percentage': 100,
    })
    fw = normalize_framework_payload(fw)
    ctx = build_context({'company_id': 1, 'id': 99, 'role': 'admin'}, endpoint='/api/bootstrap')
    plan = resolve_execution_plan(ctx, fw)
    assert plan['mode'] == 'canary'
    assert plan['targeted'] is True
    assert plan['evaluate_in_background'] is True
    assert plan['legacy_is_source_of_truth'] is True


def test_shadow_mode_keeps_legacy_as_source_of_truth():
    fw = default_framework_payload()
    fw['feature_flags'].update({
        'enable_new_rules_engine': True,
        'execution_mode': 'shadow',
        'rollout_percentage': 100,
    })
    fw = normalize_framework_payload(fw)
    ctx = build_context({'company_id': 1, 'id': 99, 'role': 'admin'}, endpoint='/api/bootstrap')
    plan = resolve_execution_plan(ctx, fw)
    assert plan['legacy_is_source_of_truth'] is True


def test_enforced_mode_rollout_miss_keeps_legacy():
    """A company/user whose rollout bucket >= rollout_percentage stays on legacy even in enforced mode."""
    from epi_backend.rule_engine import _rollout_bucket
    fw = default_framework_payload()
    fw['feature_flags'].update({
        'enable_new_rules_engine': True,
        'execution_mode': 'enforced',
        'rollout_percentage': 1,  # very low — most buckets will miss
    })
    fw = normalize_framework_payload(fw)
    # Find a context that misses the rollout bucket
    for uid in range(1, 200):
        ctx = build_context({'company_id': 1, 'id': uid, 'role': 'admin'}, endpoint='/api/bootstrap')
        if _rollout_bucket(ctx) >= 1:
            plan = resolve_execution_plan(ctx, fw)
            assert plan['targeted'] is False
            assert plan['legacy_is_source_of_truth'] is True
            return
    pytest.skip("Could not find a user that misses rollout bucket=1")


def test_enforced_mode_not_enabled_keeps_legacy():
    fw = normalize_framework_payload({})
    ctx = build_context({'company_id': 1, 'id': 1, 'role': 'admin'}, endpoint='/api/bootstrap')
    plan = resolve_execution_plan(ctx, fw)
    assert plan['mode'] == 'off'
    assert plan['legacy_is_source_of_truth'] is True


def test_visibility_diff_no_diff():
    diff = compute_visibility_diff(['1', '2', '3'], ['1', '2', '3'])
    assert diff['has_diff'] is False
    assert diff['legacy_only'] == []
    assert diff['new_only'] == []
