#!/usr/bin/env python3
"""
Verifica cobertura básica de rotas entre front-end (static/app.js) e backend (server_postgres.py).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "static" / "app.js"
SERVER_PY = ROOT / "server_postgres.py"


def normalize_path(path: str) -> str:
    cleaned = (path or "").strip()
    if "?" in cleaned:
        cleaned = cleaned.split("?", 1)[0]
    return cleaned


def collect_frontend_paths(source: str) -> set[str]:
    paths = set()
    for match in re.finditer(r"(?:api|apiOptional)\(\s*([\"'`])(?P<path>/api[^\"'`?]*)", source):
        paths.add(normalize_path(match.group("path")))

    for match in re.finditer(r"fetch\(\s*([\"'`])(?P<path>/api[^\"'`?]*)", source):
        paths.add(normalize_path(match.group("path")))

    for match in re.finditer(r"axios\.(?:get|post|put|patch|delete|request)\(\s*([\"'`])(?P<path>/api[^\"'`?]*)", source):
        paths.add(normalize_path(match.group("path")))

    for match in re.finditer(r"\.open\(\s*[\"'`](?:GET|POST|PUT|PATCH|DELETE)[\"'`]\s*,\s*([\"'`])(?P<path>/api[^\"'`?]*)", source):
        paths.add(normalize_path(match.group("path")))

    return paths


def collect_backend_paths(source: str) -> set[str]:
    paths = set()

    # Rotas exatas: parsed.path == '/api/foo'
    for match in re.finditer(r"parsed\.path\s*==\s*'(?P<path>/api[^']*)'", source):
        paths.add(normalize_path(match.group("path")))

    # Prefixos: parsed.path.startswith('/api/foo/')
    for match in re.finditer(r"parsed\.path\.startswith\('(?P<path>/api[^']*)'\)", source):
        paths.add(normalize_path(match.group("path")).rstrip("/"))

    return paths


def main() -> int:
    app_source = APP_JS.read_text(encoding="utf-8")
    server_source = SERVER_PY.read_text(encoding="utf-8")

    frontend_paths = collect_frontend_paths(app_source)
    backend_paths = collect_backend_paths(server_source)

    missing = []
    for path in sorted(frontend_paths):
        exact_match = path in backend_paths
        prefix_match = any(path.startswith(f"{prefix}/") for prefix in backend_paths)
        if not exact_match and not prefix_match:
            missing.append(path)

    print("== Route coverage check ==")
    print(f"Frontend routes found: {len(frontend_paths)}")
    print(f"Backend route patterns found: {len(backend_paths)}")
    if missing:
        print("\n[ALERTA] Rotas usadas no front-end sem correspondência no backend:")
        for item in missing:
            print(f" - {item}")
        return 1

    print("\n[OK] Rotas do front-end encontradas no backend.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
