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

from core.permissions import (
    PERM_COMPANIES_VIEW,
    PERM_DASHBOARD_VIEW,
    PERM_DELIVERIES_VIEW,
    PERM_EMPLOYEES_CREATE,
    PERM_EMPLOYEES_CREATE_SIMPLIFIED,
    PERM_FICHAS_VIEW,
    PERM_LEGAL_ENTITIES_VIEW,
    PERM_PO_VIEW,
    PERM_PURCHASE_REQUESTS_VIEW,
    PERM_REPORTS_VIEW,
    PERM_SETTINGS_VIEW,
    PERM_STOCK_VIEW,
    PERM_USERS_VIEW,
    PERMISSIONS,
)

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

# Módulos estruturais reconhecidos pela política de acesso (menus, rotas,
# deep links). Mesmo conjunto usado pelo Flutter (NavigationPolicy) e pelo
# web legado (canAccessView) — qualquer módulo novo entra aqui primeiro.
MODULE_KEYS = (
    "dashboard",
    "compras",
    "estoque",
    "entregas",
    "solicitacoes",
    "fichas",
    "relatorios",
    "administracao",
    "configuracoes",
    "terceirizados",
    "terceirizados_colaboradores",
)

# Piso técnico de cada módulo: o ator só pode enxergá-lo se tiver ao menos
# uma destas permissões (ADMIN_CONFIGURATION_ROLES/regra de negócio decide o
# "pode", isto decide o "existe tecnicamente"). É o teto que a configuração
# administrativa (module_visibility) nunca pode ultrapassar.
MODULE_REQUIRED_PERMISSIONS: dict[str, frozenset[str]] = {
    "dashboard": frozenset({PERM_DASHBOARD_VIEW}),
    "compras": frozenset({PERM_PURCHASE_REQUESTS_VIEW, PERM_PO_VIEW}),
    "estoque": frozenset({PERM_STOCK_VIEW}),
    "entregas": frozenset({PERM_DELIVERIES_VIEW}),
    "solicitacoes": frozenset({PERM_PURCHASE_REQUESTS_VIEW}),
    "fichas": frozenset({PERM_FICHAS_VIEW}),
    "relatorios": frozenset({PERM_REPORTS_VIEW}),
    # Empresas/Usuários/CNPJs (administração de tenant). Unidades fica de
    # fora de propósito: é cadastro operacional (route_permissions.dart já a
    # gateia por units:view, amplamente concedido) e não "Administração".
    "administracao": frozenset({PERM_USERS_VIEW, PERM_COMPANIES_VIEW, PERM_LEGAL_ENTITIES_VIEW}),
    "configuracoes": frozenset({PERM_SETTINGS_VIEW}),
    # Cadastro Simplificado de Terceirizados e Prestadores (ADR-014). Piso
    # técnico igual ao de criar colaborador: quem já pode `employees:create`
    # (master_admin/general_admin/registry_admin) pode, em tese, operar esta
    # subpasta — mas ver _OPT_IN_MODULES abaixo: ela nasce oculta para todos,
    # inclusive esses papéis, até o Administrador Geral ligá-la por tenant.
    "terceirizados": frozenset({PERM_EMPLOYEES_CREATE}),
    # Aba "Cadastro de Colaboradores" simplificado (ADR-0002 §10) — piso
    # próprio (não reaproveita PERM_EMPLOYEES_CREATE): dá ao Administrador
    # Local/Gestor de EPI só o cadastro simplificado de terceirizado/
    # prestador, nunca o cadastro completo de CLT.
    "terceirizados_colaboradores": frozenset({PERM_EMPLOYEES_CREATE_SIMPLIFIED}),
}

# Comprador e Aprovador enxergam stock:view/deliveries:view apenas como
# apoio à decisão de compra (ex.: nível de estoque no card do pedido), mas
# não devem ter acesso estrutural às telas operacionais completas de
# Estoque, Entregas e Fichas de EPI por padrão (docs/PAPEIS_E_ATRIBUICOES.md).
_STRUCTURALLY_HIDDEN_BY_DEFAULT: dict[str, frozenset[str]] = {
    "buyer": frozenset({"estoque", "entregas", "fichas"}),
    "approver": frozenset({"estoque", "entregas", "fichas"}),
}

# Módulos "opt-in": diferente do padrão (visível sse a permissão técnica
# existe), estes nascem OCULTOS para todo papel — mesmo quem tem a
# permissão técnica — até o Administrador Geral ligá-los explicitamente na
# configuração por tenant (module_visibility). "terceirizados" (ADR-014,
# condição de aprovação: subpasta oculta por padrão) e
# "terceirizados_colaboradores" (ADR-0002 §10, mesma regra).
_OPT_IN_MODULES: frozenset[str] = frozenset({"terceirizados", "terceirizados_colaboradores"})

# Módulos que suportam restrição adicional por Unidade (ADR-0002 §10.3) —
# além de perfil/tenant, o Administrador Geral pode restringir a um
# subconjunto de unidades. Vazio/ausente em module_unit_scope (o padrão
# para todo módulo fora desta lista) significa "sem restrição de unidade" —
# nenhum módulo existente muda de comportamento com esta extensão.
_UNIT_SCOPABLE_MODULES: frozenset[str] = frozenset({"terceirizados", "terceirizados_colaboradores"})


def _default_module_visibility() -> dict[str, dict[str, bool]]:
    """Visibilidade padrão do sistema: módulo visível sse o perfil tem ao
    menos uma permissão técnica exigida, menos as restrições estruturais
    explícitas acima, menos os módulos opt-in (sempre ocultos por padrão).
    É o ponto de partida que a configuração do Administrador Geral (por
    tenant) pode restringir ou liberar — sempre reclampada pela permissão
    técnica em resolve_module_visibility().
    """
    hidden_by_role = _STRUCTURALLY_HIDDEN_BY_DEFAULT
    visibility: dict[str, dict[str, bool]] = {}
    for role, granted in PERMISSIONS.items():
        hidden = hidden_by_role.get(role, frozenset()) | _OPT_IN_MODULES
        visibility[role] = {
            module: bool(required & granted) and module not in hidden
            for module, required in MODULE_REQUIRED_PERMISSIONS.items()
        }
    return visibility


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
        "module_visibility": _default_module_visibility(),
        # Restrição adicional por Unidade (ADR-0002 §10.3), só para módulos
        # em _UNIT_SCOPABLE_MODULES — {module: [unit_id, ...]}. Vazio/ausente
        # é o padrão de todo módulo: sem restrição de unidade.
        "module_unit_scope": {},
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
        # Cadastro Simplificado de Terceirizados e Prestadores (ADR-0002):
        # limiar em dias, editável por tenant, para o alerta de sugestão de
        # migração Simplificado -> Padrão. Nunca hardcoded no fluxo — ver
        # modules.outsourced_companies.service.get_simplified_duration_threshold_days.
        "outsourced_simplified_duration_threshold_days": 30,
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

    valid_module_roles = set(PERMISSIONS.keys())
    cleaned_module_visibility: dict[str, dict[str, bool]] = {}
    for role, modules in (payload.get("module_visibility", {}) or {}).items():
        role_name = str(role or "").strip()
        if role_name not in valid_module_roles or not isinstance(modules, dict):
            continue
        cleaned_module_visibility[role_name] = {
            module: bool(modules[module]) for module in MODULE_KEYS if module in modules
        }
    payload["module_visibility"] = _merge(_default_module_visibility(), cleaned_module_visibility)

    # Restrição por Unidade (ADR-0002 §10.3) — só módulos declarados
    # unit-scopable aceitam entrada; ids não numéricos/duplicados são
    # descartados. Validação de que a unidade pertence ao tenant é
    # responsabilidade do chamador (modules.settings.service.
    # save_module_unit_scope), que tem o company_id — esta função é pura e
    # não consulta o banco.
    cleaned_module_unit_scope: dict[str, list[int]] = {}
    for module, unit_ids in (payload.get("module_unit_scope", {}) or {}).items():
        module_name = str(module or "").strip()
        if module_name not in _UNIT_SCOPABLE_MODULES or not isinstance(unit_ids, list):
            continue
        cleaned_module_unit_scope[module_name] = sorted({
            int(item) for item in unit_ids if str(item).strip().isdigit() and int(item) > 0
        })
    payload["module_unit_scope"] = cleaned_module_unit_scope

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
    legacy_is_source_of_truth = not (targeted and mode == "enforced")
    return {
        "mode": mode,
        "targeted": targeted,
        "rollout_percentage": rollout_percentage,
        "rollout_bucket": bucket,
        "evaluate_in_background": evaluate_in_background,
        "allow_new_engine_response": allow_new_engine_response,
        "legacy_is_source_of_truth": legacy_is_source_of_truth,
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


def resolve_module_visibility(context: RuleContext, framework: dict[str, Any], actor_permissions: set[str] | frozenset[str]) -> dict[str, bool]:
    """Visibilidade estrutural efetiva de cada módulo para o ator.

    Combinação: configuração (padrão do sistema + override do tenant, já
    mesclados em `framework["module_visibility"]` por normalize_framework_payload)
    AND permissão técnica (piso que a configuração nunca ultrapassa) AND,
    para módulos em `_UNIT_SCOPABLE_MODULES` com lista configurada em
    `framework["module_unit_scope"]`, a unidade operacional do ator
    (Administrador Local/Gestor de EPI — únicos papéis escopados por
    unidade, `context.unit_id`) precisa estar na lista autorizada
    (ADR-0002 §10.3). `general_admin`/`registry_admin`/`master_admin` não
    são escopados por unidade em nenhum outro fluxo do sistema e não são
    afetados por esta checagem. O backend segue sendo a autoridade final:
    este resultado só orienta menu/rotas/deep links no Flutter e no web
    legado — nenhuma rota de dados passa a confiar nele para autorizar
    leitura/escrita.
    """
    role_config = framework.get("module_visibility", {}).get(context.role, {})
    unit_scope = framework.get("module_unit_scope", {}) or {}
    granted = set(actor_permissions or [])
    resolved: dict[str, bool] = {}
    for module, required in MODULE_REQUIRED_PERMISSIONS.items():
        has_technical_permission = bool(required & granted)
        configured = bool(role_config.get(module, False))
        unit_ok = True
        if module in _UNIT_SCOPABLE_MODULES and context.role in ("admin", "user"):
            allowed_units = unit_scope.get(module) or []
            if allowed_units:
                unit_ok = context.unit_id is not None and int(context.unit_id) in set(allowed_units)
        resolved[module] = configured and has_technical_permission and unit_ok
    return resolved


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
