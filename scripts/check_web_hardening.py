#!/usr/bin/env python3
"""Static hardening checks for the legacy website + Flutter Web gateway.

This check is intentionally lightweight so it can run in CI without Flutter or a
live database. It verifies controls that should remain true before deployment:
README text is valid, legacy CDN dependencies are explicitly version-pinned and
protected by SRI while still external, the Flutter Web SPA has a history fallback,
and the server emits a CSP report-only header compatible with the current legacy
website.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "static" / "index.html"
I18N_PATH = ROOT / "static" / "i18n.js"
I18N_HELPER_PATH = ROOT / "static" / "i18n-helper.js"
APP_PATH = ROOT / "app.py"
ENV_EXAMPLE_PATH = ROOT / "env.example"
DOCKERFILE_PATH = ROOT / "Dockerfile"
MELOS_PATH = ROOT / "flutter" / "melos.yaml"

ALLOWED_PINNED_CDN_SCRIPTS = {
    "https://unpkg.com/htmx.org@1.9.12",
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


def require_count(path: Path, needle: str, expected: int, label: str) -> None:
    text = path.read_text(encoding="utf-8", errors="ignore")
    actual = text.count(needle)
    if actual != expected:
        fail(f"{label}: expected {expected} occurrence(s) of {needle!r} in {path.relative_to(ROOT)}, found {actual}")


def require_not_contains(path: Path, needle: str, label: str) -> None:
    text = path.read_text(encoding="utf-8", errors="ignore")
    if needle in text:
        fail(f"{label}: unexpected {needle!r} in {path.relative_to(ROOT)}")


def script_sources(index_html: str) -> list[str]:
    return re.findall(r"<script\b[^>]*\bsrc=[\"']([^\"']+)[\"']", index_html, flags=re.IGNORECASE)


def origin(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def local_script_paths(index_html: str) -> list[Path]:
    paths: list[Path] = []
    for src in script_sources(index_html):
        if src.startswith(("http://", "https://", "//")):
            continue
        parsed = urlparse(src)
        relative = parsed.path.lstrip("/")
        if relative:
            paths.append(ROOT / "static" / relative)
    return paths


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
    missing_local_scripts = [path.relative_to(ROOT) for path in local_script_paths(index) if not path.exists()]
    if missing_local_scripts:
        fail("static/index.html references missing local scripts: " + ", ".join(map(str, missing_local_scripts)))

    unexpected = sorted(set(external_scripts) - ALLOWED_PINNED_CDN_SCRIPTS)
    if unexpected:
        fail("static/index.html has unapproved or unpinned external scripts: " + ", ".join(unexpected))
    missing = sorted(ALLOWED_PINNED_CDN_SCRIPTS - set(external_scripts))
    if missing:
        fail("static/index.html is missing expected pinned CDN scripts: " + ", ".join(missing))

    sri_pattern = re.compile(r"<script\b[^>]*\bsrc=[\"']([^\"']+)[\"'][^>]*>", flags=re.IGNORECASE)
    missing_sri = []
    for match in sri_pattern.finditer(index):
        tag = match.group(0)
        src = match.group(1)
        if src.startswith(("http://", "https://")) and (" integrity=" not in tag or " crossorigin=" not in tag):
            missing_sri.append(src)
    if missing_sri:
        fail("external scripts must declare integrity and crossorigin: " + ", ".join(sorted(missing_sri)))

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
    if "https://unpkg.com" not in script_src:
        fail("CSP script-src must keep the pinned legacy CDN origin while HTMX remains external")
    require_contains(APP_PATH, "def _resolve_static_fallback_path", "centralized static fallback resolver")
    require_contains(APP_PATH, "path.startswith('/app/')", "official Flutter Web /app deep-link fallback")
    require_contains(APP_PATH, "return '/app/index.html'", "official Flutter Web /app SPA fallback")
    require_contains(APP_PATH, "def _legacy_flutter_web_redirect", "legacy /flutter_web redirect helper")
    require_contains(APP_PATH, "target = '/app/'", "legacy /flutter_web redirect target")
    require_contains(MELOS_PATH, "--base-href /app/", "Flutter Web official base href")
    require_contains(DOCKERFILE_PATH, "./static/app/", "Docker copies Flutter Web build to official /app directory")
    if not {"'self'", "'unsafe-inline'", "https://unpkg.com"}.issubset(script_src):
        fail("CSP script-src must keep self, legacy inline compatibility and the pinned HTMX CDN origin")
    require_contains(APP_PATH, "request_path == '/flutter_web' or request_path.startswith('/flutter_web/')", "legacy /flutter_web static detection")
    require_contains(APP_PATH, "self.send_response(308)", "legacy /flutter_web permanent redirect")
    require_contains(I18N_PATH, "window.trEpi = trEpi", "safe dynamic i18n helper exposure")
    require_contains(I18N_PATH, "trEpi,", "safe dynamic i18n helper public API")
    require_contains(INDEX_PATH, "/i18n-helper.js?v=", "shared i18n helper script load")
    require_contains(I18N_HELPER_PATH, "function resolveLegacyTranslator()", "shared legacy i18n fallback resolver")
    require_contains(I18N_HELPER_PATH, "if (typeof existingTranslator !== 'function') global.trEpi = translator;", "shared i18n fallback avoids overriding i18n.js")
    require_count(ROOT / "static" / "app.js", "globalThis.EpiI18nHelper.resolveLegacyTranslator()", 1, "single legacy i18n helper delegation")
    require_contains(ROOT / "static" / "app.js", "if (typeof globalThis.trEpi !== 'function') globalThis.trEpi = tr;", "legacy i18n fallback avoids overriding i18n.js")
    require_not_contains(ROOT / "static" / "app.js", "\nglobalThis.trEpi = tr;", "legacy app must not overwrite the i18n.js helper")

    print("Web hardening checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
