#!/usr/bin/env python3
"""
Verifica cobertura básica de rotas entre front-end (static/*.js) e backend modular.

O backend atual registra rotas via router.register() em modules/**/routes.py; este
check mantém uma validação conservadora para detectar endpoints evidentemente sem
handler, tratando segmentos dinâmicos do front-end como correspondência por prefixo.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_FILES = sorted((ROOT / "static").glob("*.js"))
BACKEND_ROUTE_FILES = sorted((ROOT / "modules").glob("*/routes.py")) + [ROOT / "app.py"]


def normalize_path(path: str) -> str:
    cleaned = (path or "").strip().strip('"\'`')
    if "?" in cleaned:
        cleaned = cleaned.split("?", 1)[0]
    if "${" in cleaned:
        cleaned = cleaned.split("${", 1)[0].rstrip("/") or "/"
    return cleaned.rstrip("/") or "/"


def collect_frontend_paths(source: str) -> set[str]:
    paths = set()
    call_pattern = r"(?:api|apiOptional|apiWithBootstrapRetry)\(\s*([\"'`])(?P<path>/api[^\"'`?]*)"
    for pattern in (call_pattern, r"fetch\(\s*([\"'`])(?P<path>/api[^\"'`?]*)"):
        for match in re.finditer(pattern, source):
            paths.add(normalize_path(match.group("path")))
    return paths


def regex_route_prefix(route: str) -> str:
    cleaned = route.strip().lstrip('^').rstrip('$')
    cleaned = cleaned.replace('\\/', '/')
    dynamic_at = len(cleaned)
    for marker in ('(', '[', '\\d', '?P<'):
        idx = cleaned.find(marker)
        if idx >= 0:
            dynamic_at = min(dynamic_at, idx)
    return normalize_path(cleaned[:dynamic_at].rstrip('/'))


def collect_backend_paths(source: str) -> set[str]:
    paths = set()

    # Rotas registradas: router.register('GET', '/api/foo', handler)
    route_pattern = re.compile(
        r"router\.register\(\s*['\"](?:GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)['\"]\s*,\s*"
        r"(?P<prefix>r|R)?(?P<quote>['\"])(?P<path>/api.*?)(?P=quote)",
        re.DOTALL,
    )
    for match in route_pattern.finditer(source):
        path = match.group('path')
        if match.group('prefix'):
            paths.add(regex_route_prefix(path))
        else:
            paths.add(normalize_path(path))

    # Gateways/fallbacks ainda escritos diretamente no handler HTTP.
    for match in re.finditer(r"parsed\.path\s*==\s*['\"](?P<path>/api[^'\"]*)['\"]", source):
        paths.add(normalize_path(match.group("path")))
    for match in re.finditer(r"parsed\.path\.startswith\(['\"](?P<path>/api[^'\"]*)['\"]\)", source):
        paths.add(normalize_path(match.group("path")).rstrip("/"))

    return {p for p in paths if p.startswith('/api')}


def is_covered(frontend_path: str, backend_paths: set[str]) -> bool:
    path = normalize_path(frontend_path)
    if path in backend_paths:
        return True
    return any(path.startswith(f"{prefix}/") or prefix.startswith(f"{path}/") for prefix in backend_paths if prefix != '/api')


def main() -> int:
    frontend_paths: set[str] = set()
    for file_path in FRONTEND_FILES:
        frontend_paths.update(collect_frontend_paths(file_path.read_text(encoding="utf-8")))

    backend_paths: set[str] = set()
    for file_path in BACKEND_ROUTE_FILES:
        backend_paths.update(collect_backend_paths(file_path.read_text(encoding="utf-8")))

    missing = [path for path in sorted(frontend_paths) if not is_covered(path, backend_paths)]

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
