"""Central rule-engine foundation for incremental hardening.

This module is intentionally non-invasive: it does not change legacy behavior by default.
It only standardizes contracts so endpoints can progressively adopt centralized rule checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import copy
import hashlib
import os

ADMIN_CONFIGURATION_ROLES = ("master_admin", "general_admin", "registry_admin")
SUPPORTED_REPORT_TYPES = (
    "stock_by_unit",
    "delivery_by_employee",
    "movement",
    "epi_ficha",
    "alerts",
)
SUPPORTED_CONTEXTS = ("outside_jv", "inside_jv")
SUPPORTED_EXECUTION_MODES = ("off", "shadow", "canary", "enforced")


@dataclass(frozen=True)
class RuleContext:
    company_id: int
    user_id: int
    role: str
    endpoint: str = ""
    unit_id: int | None = None
    jv_context: str = "outside_jv"


def default_framework_payload() -> dict[str, Any]:
    return {
        "version": 1,
        "feature_flags": {
            "enable_new_rules_engine": False,
            "execution_mode": "off",
            "allow_new_engine_response": False,
            "enabled_profiles": [],
            "enabled_user_ids": [],
            "enabled_company_ids": [],
            "enabled_endpoints": [],
            "enabled_environments": [],
            "rollout_percentage": 0,
        },
        "hierarchy": {
            "role_priority": [
                "master_admin",
                "general_admin",
                "registry_admin",
                "admin",
                "user",
                "employee",
            ],
            "who_can_view_what": {
                "master_admin": {"units": "all", "epis": "all", "employees": "all"},
                "general_admin": {"units": "company", "epis": "company", "employees": "company"},
                "registry_admin": {"units": "company", "epis": "company", "employees": "company"},
                "admin": {"units": "operational", "epis": "operational", "employees": "operational"},
                "user": {"units": "operational", "epis": "operational", "employees": "operational"},
            },
        },
        "visibility_rules": [],
        "report_scopes": {
            report_type: {
                "enabled": True,
                "allowed_profiles": ["master_admin", "general_admin", "registry_admin", "admin", "user"],
                "enforce_unit_scope": True,
                "enforce_visibility_rules": False,
            }
            for report_type in SUPPORTED_REPORT_TYPES
        },
        "observability": {
            "audit_decisions": False,
            "debug_visibility": False,
        },
    }


def _merge(base: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in (candidate or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def normalize_framework_payload(candidate: dict[str, Any] | None) -> dict[str, Any]:
    payload = _merge(default_framework_payload(), candidate or {})
    payload["feature_flags"]["enable_new_rules_engine"] = bool(
        payload.get("feature_flags", {}).get("enable_new_rules_engine", False)
    )
    payload["feature_flags"]["enabled_profiles"] = [str(item) for item in payload["feature_flags"].get("enabled_profiles", []) if str(item).strip()]
    payload["feature_flags"]["enabled_user_ids"] = [int(item) for item in payload["feature_flags"].get("enabled_user_ids", []) if str(item).strip().isdigit()]
    payload["feature_flags"]["enabled_company_ids"] = [int(item) for item in payload["feature_flags"].get("enabled_company_ids", []) if str(item).strip().isdigit()]
    payload["feature_flags"]["enabled_endpoints"] = [str(item) for item in payload["feature_flags"].get("enabled_endpoints", []) if str(item).strip()]
    payload["feature_flags"]["enabled_environments"] = [str(item).lower() for item in payload["feature_flags"].get("enabled_environments", []) if str(item).strip()]
    payload["feature_flags"]["execution_mode"] = str(payload["feature_flags"].get("execution_mode", "off")).lower()
    if payload["feature_flags"]["execution_mode"] not in SUPPORTED_EXECUTION_MODES:
        payload["feature_flags"]["execution_mode"] = "off"
    payload["feature_flags"]["allow_new_engine_response"] = bool(payload["feature_flags"].get("allow_new_engine_response", False))
    rollout = int(payload["feature_flags"].get("rollout_percentage", 0) or 0)
    payload["feature_flags"]["rollout_percentage"] = min(100, max(0, rollout))

    normalized_rules: list[dict[str, Any]] = []
    for rule in payload.get("visibility_rules", []):
        if not isinstance(rule, dict):
            continue
        normalized_rules.append(
            {
                "id": str(rule.get("id") or ""),
                "role": str(rule.get("role") or "").strip(),
                "unit_id": int(rule.get("unit_id") or 0),
                "unit_context": "inside_jv" if str(rule.get("unit_context") or "") == "inside_jv" else "outside_jv",
                "can_view_unit": bool(rule.get("can_view_unit", True)),
                "can_view_epis": bool(rule.get("can_view_epis", True)),
                "can_view_employees": bool(rule.get("can_view_employees", True)),
            }
        )
    payload["visibility_rules"] = normalized_rules

    valid_roles = set(default_framework_payload()["hierarchy"]["role_priority"])
    cleaned_hierarchy = {}
    for role, scope in (payload.get("hierarchy", {}).get("who_can_view_what", {}) or {}).items():
        role_name = str(role or "").strip()
        if role_name not in valid_roles:
            continue
        cleaned_hierarchy[role_name] = {
            "units": str((scope or {}).get("units") or "operational"),
            "epis": str((scope or {}).get("epis") or "operational"),
            "employees": str((scope or {}).get("employees") or "operational"),
        }
    payload["hierarchy"]["who_can_view_what"] = _merge(default_framework_payload()["hierarchy"]["who_can_view_what"], cleaned_hierarchy)

    for report_type in SUPPORTED_REPORT_TYPES:
        scope = payload["report_scopes"].setdefault(report_type, {})
        scope["enabled"] = bool(scope.get("enabled", True))
        scope["allowed_profiles"] = [str(item) for item in scope.get("allowed_profiles", []) if str(item).strip() in valid_roles]
        scope["enforce_unit_scope"] = bool(scope.get("enforce_unit_scope", True))
        scope["enforce_visibility_rules"] = bool(scope.get("enforce_visibility_rules", False))
    return payload


def build_context(actor: dict[str, Any], *, endpoint: str = "", unit_id: int | None = None, jv_context: str = "outside_jv") -> RuleContext:
    return RuleContext(
        company_id=int(actor.get("company_id") or 0),
        user_id=int(actor.get("id") or 0),
        role=str(actor.get("role") or ""),
        endpoint=str(endpoint or ""),
        unit_id=int(unit_id) if unit_id not in (None, "", 0, "0") else None,
        jv_context="inside_jv" if str(jv_context) == "inside_jv" else "outside_jv",
    )


def should_enable_new_engine(context: RuleContext, framework: dict[str, Any]) -> bool:
    flags = framework.get("feature_flags", {})
    if not bool(flags.get("enable_new_rules_engine", False)):
        return False

    enabled_profiles = set(flags.get("enabled_profiles", []))
    enabled_users = set(flags.get("enabled_user_ids", []))
    enabled_companies = set(flags.get("enabled_company_ids", []))
    enabled_endpoints = set(flags.get("enabled_endpoints", []))
    enabled_envs = set(flags.get("enabled_environments", []))
    environment = str(os.environ.get("APP_ENV", "")).strip().lower()

    checks = []
    if enabled_profiles:
        checks.append(context.role in enabled_profiles)
    if enabled_users:
        checks.append(context.user_id in enabled_users)
    if enabled_companies:
        checks.append(context.company_id in enabled_companies)
    if enabled_endpoints:
        checks.append(context.endpoint in enabled_endpoints)
    if enabled_envs:
        checks.append(environment in enabled_envs)

    if not checks:
        return True
    return any(checks)


def _rollout_bucket(context: RuleContext) -> int:
    raw = f"{context.company_id}:{context.user_id}:{context.endpoint}:{context.role}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return int(digest[:8], 16) % 100


def resolve_execution_plan(context: RuleContext, framework: dict[str, Any]) -> dict[str, Any]:
    flags = framework.get("feature_flags", {})
    engine_targeted = should_enable_new_engine(context, framework)
    mode = str(flags.get("execution_mode", "off")).lower()
    if mode not in SUPPORTED_EXECUTION_MODES:
        mode = "off"
    rollout_percentage = int(flags.get("rollout_percentage", 0) or 0)
    bucket = _rollout_bucket(context)
    rollout_hit = bucket < rollout_percentage if rollout_percentage > 0 else False
    targeted = engine_targeted and (rollout_percentage == 0 or rollout_hit)
    evaluate_in_background = targeted and mode in ("shadow", "canary", "enforced")
    allow_new_engine_response = bool(flags.get("allow_new_engine_response", False))
    return {
        "mode": mode,
        "targeted": targeted,
        "rollout_percentage": rollout_percentage,
        "rollout_bucket": bucket,
        "evaluate_in_background": evaluate_in_background,
        "allow_new_engine_response": allow_new_engine_response,
        "legacy_is_source_of_truth": True,
    }


def compute_visibility_diff(legacy_ids: list[str], candidate_ids: list[str]) -> dict[str, Any]:
    legacy_set = set(legacy_ids)
    candidate_set = set(candidate_ids)
    only_legacy = sorted(legacy_set - candidate_set)
    only_candidate = sorted(candidate_set - legacy_set)
    return {
        "has_diff": bool(only_legacy or only_candidate),
        "legacy_only": only_legacy,
        "new_only": only_candidate,
    }


def resolve_visibility_filters(context: RuleContext, framework: dict[str, Any]) -> dict[str, Any]:
    """Returns normalized filters for future endpoint enforcement.

    No enforcement side-effect is executed here.
    """
    enabled = should_enable_new_engine(context, framework)
    matching_rules = [
        rule
        for rule in framework.get("visibility_rules", [])
        if rule.get("role") == context.role
        and int(rule.get("unit_id") or 0) == int(context.unit_id or 0)
        and rule.get("unit_context") == context.jv_context
    ]
    last_rule = matching_rules[-1] if matching_rules else None
    return {
        "enabled": enabled,
        "fallback_mode": not enabled,
        "allow_unit": True if not last_rule else bool(last_rule.get("can_view_unit", True)),
        "allow_epis": True if not last_rule else bool(last_rule.get("can_view_epis", True)),
        "allow_employees": True if not last_rule else bool(last_rule.get("can_view_employees", True)),
        "matched_rule_id": (last_rule or {}).get("id", ""),
    }


def resolve_report_scope(report_type: str, context: RuleContext, framework: dict[str, Any]) -> dict[str, Any]:
    report_type = str(report_type or "").strip()
    scope = framework.get("report_scopes", {}).get(report_type, {})
    return {
        "report_type": report_type,
        "supported": report_type in SUPPORTED_REPORT_TYPES,
        "enabled": bool(scope.get("enabled", True)),
        "allowed_profiles": scope.get("allowed_profiles", []),
        "profile_allowed": context.role in set(scope.get("allowed_profiles", [])),
        "enforce_unit_scope": bool(scope.get("enforce_unit_scope", True)),
        "enforce_visibility_rules": bool(scope.get("enforce_visibility_rules", False)),
    }


def evaluate_rule_decision(context: RuleContext, framework: dict[str, Any], *, report_type: str = "") -> dict[str, Any]:
    visibility = resolve_visibility_filters(context, framework)
    report_scope = resolve_report_scope(report_type, context, framework) if report_type else None
    return {
        "context": {
            "company_id": context.company_id,
            "user_id": context.user_id,
            "role": context.role,
            "endpoint": context.endpoint,
            "unit_id": context.unit_id,
            "jv_context": context.jv_context,
        },
        "visibility": visibility,
        "report_scope": report_scope,
    }
