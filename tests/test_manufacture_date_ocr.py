from epi_backend.manufacture_date_ocr import choose_best_date, extract_date_candidates


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
