import os
import re
from pathlib import Path

import pytest

from epi_backend.manufacture_date_ocr import choose_best_date, configure_tesseract, extract_date_candidates, get_ocr_runtime_status

ROOT = Path(__file__).resolve().parents[1]
OCR_MODULE_PATH = ROOT / "epi_backend" / "manufacture_date_ocr.py"


def test_extract_date_candidates_accepts_supported_formats():
    text = "Fab 14/03/2026 lote x val 2026-03-20 ref 14-03-26"
    candidates = extract_date_candidates(text)
    normalized = {item["normalized"] for item in candidates}
    assert "2026-03-14" in normalized
    assert "2026-03-20" in normalized


def test_extract_date_candidates_rejects_invalid_or_implausible():
    text = "datas 32/13/2025 e 01/01/1980"
    candidates = extract_date_candidates(text)
    assert candidates == []


def test_choose_best_date_prefers_most_frequent():
    candidates = [
        {"token": "14/03/2026", "normalized": "2026-03-14"},
        {"token": "2026-03-14", "normalized": "2026-03-14"},
        {"token": "13/03/2026", "normalized": "2026-03-13"},
    ]
    assert choose_best_date(candidates) == "2026-03-14"


def test_extract_date_candidates_supports_two_digit_year():
    text = "FAB: 14/03/26"
    candidates = extract_date_candidates(text)
    normalized = {item["normalized"] for item in candidates}
    assert "2026-03-14" in normalized


def test_tesseract_resolver_block_has_no_dangling_for_statement():
    source = OCR_MODULE_PATH.read_text(encoding="utf-8")
    assert "for path in (" not in source
    assert "for path in ('/usr/bin/tesseract'" not in source


def test_tesseract_resolver_block_uses_explicit_fallback_paths():
    source = OCR_MODULE_PATH.read_text(encoding="utf-8")
    assert "if Path('/usr/bin/tesseract').exists():" in source
    assert "if Path('/usr/local/bin/tesseract').exists():" in source


def test_module_is_syntax_valid_python():
    source = OCR_MODULE_PATH.read_text(encoding="utf-8")
    compile(source, "epi_backend/manufacture_date_ocr.py", "exec")


def test_server_can_import_ocr_functions():
    from epi_backend.manufacture_date_ocr import detect_manufacture_date

    assert callable(detect_manufacture_date)
    assert callable(get_ocr_runtime_status)


def test_configure_tesseract_returns_status_dict():
    config = configure_tesseract()
    assert config["status"] in {"ok", "not_found"}
    assert "path" in config


def test_runtime_status_without_tesseract_is_controlled_warning(monkeypatch):
    monkeypatch.setenv("TESSERACT_CMD", "/path/that/does/not/exist")
    monkeypatch.delenv("OCR_REQUIRED", raising=False)
    status = get_ocr_runtime_status()
    assert status["status"] in {"ok", "warning", "error"}
    if not status.get("ready"):
        assert "message" in status


def test_windows_fallback_has_no_hardcoded_user_profile_path():
    source = OCR_MODULE_PATH.read_text(encoding="utf-8")
    assert not re.search(r"[A-Za-z]:\\+Users\\+", source)


def test_windows_paths_use_localappdata_first(monkeypatch):
    from epi_backend import manufacture_date_ocr as engine

    monkeypatch.setenv("LOCALAPPDATA", "/fake/localappdata")
    paths = engine._windows_tesseract_paths()

    assert paths[0] == os.path.join("/fake/localappdata", "Programs", "Tesseract-OCR", "tesseract.exe")
    assert paths[1:] == engine.WINDOWS_TESSERACT_PATHS


def test_windows_paths_without_localappdata_keep_program_files(monkeypatch):
    from epi_backend import manufacture_date_ocr as engine

    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    assert engine._windows_tesseract_paths() == engine.WINDOWS_TESSERACT_PATHS


@pytest.mark.skipif(
    any(Path(p).exists() for p in ("/usr/bin/tesseract", "/usr/local/bin/tesseract")),
    reason="Tesseract do sistema tem precedência sobre o fallback do Windows",
)
def test_resolver_finds_per_user_install_via_localappdata(monkeypatch, tmp_path):
    from epi_backend import manufacture_date_ocr as engine

    exe = tmp_path.joinpath("Programs", "Tesseract-OCR", "tesseract.exe")
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"")
    monkeypatch.delenv("TESSERACT_CMD", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(engine.shutil, "which", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(engine, "_is_windows", lambda: True)

    assert engine._resolve_tesseract_cmd() == str(exe)
