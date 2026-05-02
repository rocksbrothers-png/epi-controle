from __future__ import annotations

import importlib
import io
from types import SimpleNamespace

import pytest

from epi_backend.epi_scope import is_epi_visible_for_unit
from epi_backend.http_utils import parse_json


def _build_handler(body: bytes, content_length: str | None = None):
    headers = {"Content-Length": str(len(body)) if content_length is None else content_length}
    return SimpleNamespace(headers=headers, rfile=io.BytesIO(body))


def test_parse_json_rejects_invalid_json_without_unhandled_exception():
    handler = _build_handler(b'{"invalid": ')
    with pytest.raises(ValueError, match="JSON inválido"):
        parse_json(handler)


@pytest.mark.parametrize("bad_unit_id", ["abc", "1.5", "", None])
def test_epi_scope_handles_invalid_target_unit_id_fail_safe(bad_unit_id):
    if bad_unit_id in ("", None):
        assert is_epi_visible_for_unit(1, "", bad_unit_id, "") is True
        return
    assert is_epi_visible_for_unit(1, "", bad_unit_id, "") is False


def test_prod_environment_requires_explicit_jwt_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("PASSWORD_RECOVERY_KEY", raising=False)

    import epi_backend.config as config_module

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        importlib.reload(config_module)

    monkeypatch.setenv("JWT_SECRET", "test-only-secret")
    reloaded = importlib.reload(config_module)
    assert reloaded.JWT_SECRET == "test-only-secret"
    monkeypatch.setenv("APP_ENV", "")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    importlib.reload(config_module)


def test_migration_run_is_transaction_neutral_for_runner_control():
    migration = importlib.import_module("epi_backend.migrations.001_unit_jv_periods")
    source = migration.__loader__.get_source(migration.__name__)  # type: ignore[attr-defined]
    assert "commit(" not in str(source or "")
    assert "rollback(" not in str(source or "")
