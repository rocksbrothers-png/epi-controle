"""Cutover da raiz `/` → Flutter Web por feature flag (Fase 6, default OFF)."""

from core.root_routing import is_flutter_root_redirect_enabled, resolve_root_request


# ── flag de ambiente (default OFF) ────────────────────────────────────────────

def test_flag_defaults_off():
    assert is_flutter_root_redirect_enabled(env={}) is False
    assert is_flutter_root_redirect_enabled(env={'FLUTTER_WEB_ROOT_REDIRECT': ''}) is False


def test_flag_truthy_values():
    for v in ('1', 'true', 'TRUE', 'yes', 'on'):
        assert is_flutter_root_redirect_enabled(env={'FLUTTER_WEB_ROOT_REDIRECT': v}) is True


def test_flag_falsey_values():
    for v in ('0', 'false', 'no', 'off', 'qualquer'):
        assert is_flutter_root_redirect_enabled(env={'FLUTTER_WEB_ROOT_REDIRECT': v}) is False


# ── comportamento com cutover DESLIGADO (default) ─────────────────────────────

def test_root_passthrough_when_disabled():
    assert resolve_root_request('/', redirect_enabled=False) == ('passthrough', None)
    assert resolve_root_request('/index.html', redirect_enabled=False) == ('passthrough', None)


# ── comportamento com cutover LIGADO ──────────────────────────────────────────

def test_root_redirects_when_enabled():
    assert resolve_root_request('/', redirect_enabled=True) == ('redirect', '/app/')
    assert resolve_root_request('/index.html', redirect_enabled=True) == ('redirect', '/app/')


def test_non_root_paths_passthrough_even_when_enabled():
    for p in ('/api/bootstrap', '/app/', '/styles.css', '/health'):
        assert resolve_root_request(p, redirect_enabled=True) == ('passthrough', None), p


# ── /legacy/ de emergência: sempre serve o legado ─────────────────────────────

def test_legacy_emergency_always_serves_legacy():
    for enabled in (True, False):
        for p in ('/legacy', '/legacy/', '/legacy/index.html'):
            assert resolve_root_request(p, redirect_enabled=enabled) == ('legacy', '/index.html'), (p, enabled)
