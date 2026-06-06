#!/usr/bin/env python3
"""Static hardening checks for the legacy website + Flutter Web gateway.

This check is intentionally lightweight so it can run in CI without Flutter or a
live database. It verifies controls that should remain true before deployment:
README text is valid, legacy CDN dependencies are explicitly version-pinned while
still external, the Flutter Web SPA has a history fallback, and the server emits
a CSP report-only header compatible with the current legacy website.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "static" / "index.html"
APP_PATH = ROOT / "app.py"

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


def main() -> int:
    readme_bytes = (ROOT / "README.md").read_bytes()
    if b"\x00" in readme_bytes:
        fail("README.md still contains NUL bytes")

    index = INDEX_PATH.read_text(encoding="utf-8")
    for marker in FORBIDDEN_CDN_HOSTS:
        if marker in index:
            fail(f"static/index.html uses an unapproved CDN host: {marker}")

    external_scripts = [src for src in script_sources(index) if src.startswith("http://") or src.startswith("https://")]
    unexpected = sorted(set(external_scripts) - ALLOWED_PINNED_CDN_SCRIPTS)
    if unexpected:
        fail("static/index.html has unapproved or unpinned external scripts: " + ", ".join(unexpected))
    missing = sorted(ALLOWED_PINNED_CDN_SCRIPTS - set(external_scripts))
    if missing:
        fail("static/index.html is missing expected pinned CDN scripts: " + ", ".join(missing))

    require_contains(APP_PATH, "Content-Security-Policy-Report-Only", "CSP report-only")
    require_contains(APP_PATH, "script-src 'self' 'unsafe-inline' https://unpkg.com;", "CSP legacy CDN allowlist")
    require_contains(APP_PATH, "parsed.path.startswith('/flutter_web/')", "Flutter Web deep-link fallback")
    require_contains(APP_PATH, "self.path = '/flutter_web/index.html'", "Flutter Web SPA fallback")

    print("Web hardening checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
