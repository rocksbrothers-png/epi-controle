"""Política de cache HTTP (core/http_cache) — Fase 1 + resíduo da Fase 3.

Garante que os assets versionados do Flutter Web (/app/...) sejam imutáveis,
enquanto shells de SPA, arquivos de versão e o legado permanecem no-store.
"""

from core.http_cache import IMMUTABLE, NO_STORE, is_no_store, resolve_cache_control


# ── no-store: APIs, health, shells, arquivos de versão, legado ────────────────

def test_api_is_no_store():
    assert resolve_cache_control('/api/bootstrap') == NO_STORE
    assert resolve_cache_control('/health') == NO_STORE
    assert resolve_cache_control('/ready') == NO_STORE


def test_legacy_shell_is_no_store():
    for p in ('/', '/index.html', '/app.js', '/styles.css'):
        assert resolve_cache_control(p) == NO_STORE, p


def test_flutter_shell_and_versioned_files_are_no_store():
    for p in ('/app', '/app/', '/app/index.html', '/app/flutter_service_worker.js',
              '/app/version.json', '/app/manifest.json', '/app/flutter_bootstrap.js'):
        assert resolve_cache_control(p) == NO_STORE, p


def test_legacy_js_css_is_no_store():
    assert resolve_cache_control('/i18n.js') == NO_STORE
    assert resolve_cache_control('/some/theme.css') == NO_STORE


# ── immutable: assets reais do Flutter sob /app/ ──────────────────────────────

def test_flutter_assets_are_immutable():
    for p in ('/app/main.dart.js', '/app/flutter.js', '/app/assets/fonts/MaterialIcons.otf',
              '/app/canvaskit/canvaskit.wasm', '/app/assets/AssetManifest.json'):
        assert resolve_cache_control(p) == IMMUTABLE, p


def test_flutter_asset_takes_precedence_over_js_suffix():
    # /app/main.dart.js termina em .js mas deve ser imutável (não no-store)
    assert resolve_cache_control('/app/main.dart.js') == IMMUTABLE


# ── sem header para caminhos não classificados (comportamento preservado) ─────

def test_unclassified_path_has_no_cache_header():
    assert resolve_cache_control('/images/logo.png') == ''
    assert resolve_cache_control('/favicon.ico') == ''
    assert resolve_cache_control('') == ''


# ── is_no_store helper ────────────────────────────────────────────────────────

def test_is_no_store_helper():
    assert is_no_store(NO_STORE) is True
    assert is_no_store(IMMUTABLE) is False
    assert is_no_store('') is False
