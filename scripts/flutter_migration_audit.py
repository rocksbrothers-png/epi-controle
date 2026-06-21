#!/usr/bin/env python3
"""Auditoria estática da execução do roadmap Flutter/multi-tenant.

O script não altera lógica de produção. Ele valida os guardrails mínimos das
sete fases do roadmap para impedir regressões enquanto a migração por módulos
continua incremental.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ROADMAP_MODULES = {
    "employees": ROOT / "modules/employees/routes.py",
    "stock": ROOT / "modules/stock/routes.py",
    "deliveries": ROOT / "modules/deliveries/routes.py",
    "purchases": ROOT / "modules/purchases/routes.py",
    "reports": ROOT / "modules/reports/routes.py",
}

FLUTTER_FEATURE_ROOT = ROOT / "flutter/apps/epi_admin/lib/features"
SESSION_CONTEXT = ROOT / "flutter/apps/epi_admin/lib/core/session/session_context.dart"
ROUTE_PERMISSIONS = ROOT / "flutter/apps/epi_admin/lib/core/router/route_permissions.dart"
APP_ROUTER = ROOT / "flutter/apps/epi_admin/lib/core/router/app_router.dart"


@dataclass(frozen=True)
class Check:
    phase: str
    target: str
    status: str
    evidence: str


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def has_all(text: str, tokens: list[str]) -> bool:
    return all(token in text for token in tokens)


def audit_foundation() -> list[Check]:
    session = read(SESSION_CONTEXT)
    routes = read(ROUTE_PERMISSIONS)
    router = read(APP_ROUTER)
    return [
        Check(
            "1-fundacao",
            "SessionContext",
            "ok" if has_all(session, ["userId", "companyId", "unitId", "role", "permissions", "tenantName", "companySettings"]) else "fail",
            str(SESSION_CONTEXT.relative_to(ROOT)),
        ),
        Check(
            "1-fundacao",
            "rotas-publicas",
            "ok" if has_all(routes, ["Routes.qr", "Routes.portal"]) and "isPublicRoute" in router else "fail",
            f"{ROUTE_PERMISSIONS.relative_to(ROOT)} + {APP_ROUTER.relative_to(ROOT)}",
        ),
        Check(
            "1-fundacao",
            "guard-permissoes",
            "ok" if "!permissions.value.contains(required)" in router else "fail",
            str(APP_ROUTER.relative_to(ROOT)),
        ),
    ]


def audit_backend_tenant_scope() -> list[Check]:
    checks: list[Check] = []
    for module, path in ROADMAP_MODULES.items():
        text = read(path)
        has_auth = "authorize_action" in text or "require_actor" in text
        has_scope = any(
            token in text
            for token in (
                "company_id",
                "ensure_resource_company",
                "ensure_actor_employee_scope",
                "company_filter",
                "canary_evaluate_visibility_dataset",
            )
        )
        checks.append(
            Check(
                "2-multi-tenant",
                module,
                "ok" if has_auth and has_scope else "partial",
                str(path.relative_to(ROOT)),
            )
        )
    return checks


def audit_flutter_target_architecture() -> list[Check]:
    checks: list[Check] = []
    for module in ROADMAP_MODULES:
        base = FLUTTER_FEATURE_ROOT / module
        required = [
            base / "presentation",
            base / "domain",
            base / "data",
            base / "ARCHITECTURE.md",
        ]
        if module == "employees":
            required.extend(
                [
                    base / "presentation/cubits/employees_cubit.dart",
                    base / "domain/repositories/employees_repository.dart",
                    base / "domain/usecases/fetch_employees_usecase.dart",
                    base / "data/datasources/employees_remote_datasource.dart",
                    base / "data/repository_impl/employees_repository_impl.dart",
                ]
            )
        checks.append(
            Check(
                f"3-7-{module}",
                "estrutura-alvo",
                "ok" if all(path.exists() for path in required) else "fail",
                str(base.relative_to(ROOT)),
            )
        )
    return checks


def run_audit() -> list[Check]:
    return [
        *audit_foundation(),
        *audit_backend_tenant_scope(),
        *audit_flutter_target_architecture(),
    ]


def main() -> int:
    checks = run_audit()
    print(
        json.dumps(
            [asdict(check) for check in checks],
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if all(check.status == "ok" for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
