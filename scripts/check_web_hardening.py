#!/usr/bin/env python3
"""Static hardening checks for the legacy website + Flutter Web gateway.

This check is intentionally lightweight so it can run in CI without Flutter or a
live database. It verifies controls that should remain true before deployment:
README text is valid, legacy CDN dependencies are explicitly version-pinned while
still external, the Flutter Web SPA has a history fallback, and the server emits
a CSP report-only header compatible with the current legacy website.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "static" / "index.html"
APP_PATH = ROOT / "app.py"
ENV_EXAMPLE_PATH = ROOT / "env.example"

ALLOWED_PINNED_CDN_SCRIPTS = {
    "https://unpkg.com/htmx.org@1.9.12",
    "https://unpkg.com/alpinejs@3.14.9/dist/cdn.min.js",
}
FORBIDDEN_CDN_HOSTS = (
    "https://cdn.jsdelivr.net",
    "https://cdnjs.cloudflare.com",
)


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    raise SystemExit(1)


def require_contains(path: Path, needle: str, label: str) -> None:
    text = path.read_text(encoding="utf-8", errors="ignore")
    if needle not in text:
        fail(f"{label}: missing {needle!r} in {path.relative_to(ROOT)}")


def script_sources(index_html: str) -> list[str]:
    return re.findall(r"<script\b[^>]*\bsrc=[\"']([^\"']+)[\"']", index_html, flags=re.IGNORECASE)


def origin(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def eval_csp_literal(node: ast.AST, constants: dict[str, object]) -> object:
    if isinstance(node, ast.Name) and node.id in constants:
        return constants[node.id]
    if isinstance(node, ast.Tuple):
        return tuple(eval_csp_literal(item, constants) for item in node.elts)
    return ast.literal_eval(node)


def load_app_constants() -> dict[str, object]:
    tree = ast.parse(APP_PATH.read_text(encoding="utf-8"))
    constants: dict[str, object] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.startswith("CSP_"):
                    try:
                        constants[target.id] = eval_csp_literal(node.value, constants)
                    except (ValueError, SyntaxError, KeyError):
                        pass
    return constants


def directive_sources(constants: dict[str, object], directive_name: str) -> set[str]:
    directives = constants.get("CSP_REPORT_ONLY_DIRECTIVES")
    if not isinstance(directives, tuple):
        fail("app.py CSP_REPORT_ONLY_DIRECTIVES must be a literal tuple")
    for item in directives:
        if not isinstance(item, tuple) or len(item) != 2:
            continue
        name, values = item
        if name == directive_name and isinstance(values, tuple):
            return {str(value) for value in values}
    fail(f"app.py CSP_REPORT_ONLY_DIRECTIVES is missing {directive_name}")


def main() -> int:
    readme_bytes = (ROOT / "README.md").read_bytes()
    if b"\x00" in readme_bytes:
        fail("README.md still contains NUL bytes")

    index = INDEX_PATH.read_text(encoding="utf-8")
    for marker in FORBIDDEN_CDN_HOSTS:
        if marker in index:
            fail(f"static/index.html uses an unapproved CDN host: {marker}")

    external_scripts = [src for src in script_sources(index) if src.startswith(("http://", "https://"))]
    unexpected = sorted(set(external_scripts) - ALLOWED_PINNED_CDN_SCRIPTS)
    if unexpected:
        fail("static/index.html has unapproved or unpinned external scripts: " + ", ".join(unexpected))
    missing = sorted(ALLOWED_PINNED_CDN_SCRIPTS - set(external_scripts))
    if missing:
        fail("static/index.html is missing expected pinned CDN scripts: " + ", ".join(missing))

    constants = load_app_constants()
    script_src = directive_sources(constants, "script-src")
    missing_csp_origins = sorted({origin(src) for src in external_scripts} - script_src)
    if missing_csp_origins:
        fail("CSP script-src is missing external script origins: " + ", ".join(missing_csp_origins))

    require_contains(APP_PATH, "Content-Security-Policy-Report-Only", "CSP report-only")
    require_contains(APP_PATH, "CSP_REPORT_URI", "CSP report endpoint option")
    require_contains(APP_PATH, "APP_ENV not in ('prod', 'production') and csp_report_uri.startswith('http://')", "CSP report endpoint production HTTPS guard")
    require_contains(APP_PATH, "def _handle_csp_report", "local CSP report endpoint")
    require_contains(APP_PATH, "security.csp_report", "CSP report structured log")
    require_contains(APP_PATH, "parsed.path == '/api/csp-report'", "CSP report endpoint route")
    require_contains(ENV_EXAMPLE_PATH, "CSP_REPORT_URI=/api/csp-report", "CSP report endpoint documentation")
    require_contains(APP_PATH, "parsed.path.startswith('/flutter_web/')", "Flutter Web deep-link fallback")
    require_contains(APP_PATH, "self.path = '/flutter_web/index.html'", "Flutter Web SPA fallback")

    print("Web hardening checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
