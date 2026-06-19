"""Guarda de integridade dos arquivos de tradução (i18n).

Regressão: os 5 JSON estavam sintaticamente inválidos (vírgulas ausentes, chave
duplicada, `}` extra) e com chaves duplicadas, fazendo a API de i18n retornar
traduções vazias e a UI exibir as chaves cruas (login.title, login.username...).
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
I18N_DIR = ROOT / "static" / "i18n"
LOCALES = ["pt-BR", "en-GB", "es-ES", "fr-FR", "nb-NO"]
BASE = "pt-BR"


def _path(locale):
    return I18N_DIR / f"{locale}.json"


def _flatten(node, prefix=""):
    out = {}
    for key, value in node.items():
        full = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            out.update(_flatten(value, full))
        else:
            out[full] = value
    return out


def _load_with_dup_detection(locale):
    duplicates = []

    def hook(pairs):
        seen = {}
        for key, value in pairs:
            if key in seen:
                duplicates.append(key)
            seen[key] = value
        return seen

    data = json.loads(_path(locale).read_text(encoding="utf-8"), object_pairs_hook=hook)
    return data, duplicates


def test_all_locale_files_are_valid_json():
    for locale in LOCALES:
        # Levanta JSONDecodeError se o arquivo estiver malformado.
        json.loads(_path(locale).read_text(encoding="utf-8"))


def test_no_duplicate_keys_in_any_object():
    for locale in LOCALES:
        _data, duplicates = _load_with_dup_detection(locale)
        assert not duplicates, f"{locale} tem chaves duplicadas: {sorted(set(duplicates))}"


def test_key_parity_across_all_locales():
    base_keys = set(_flatten(json.loads(_path(BASE).read_text(encoding="utf-8"))))
    assert base_keys, "pt-BR não deve estar vazio"
    for locale in LOCALES:
        if locale == BASE:
            continue
        keys = set(_flatten(json.loads(_path(locale).read_text(encoding="utf-8"))))
        missing = base_keys - keys
        extra = keys - base_keys
        assert not missing, f"{locale} faltam chaves: {sorted(missing)[:10]}"
        assert not extra, f"{locale} tem chaves extras: {sorted(extra)[:10]}"


def test_login_keys_present_and_nonempty():
    # As chaves exatas que apareciam cruas no print do bug.
    required = ["title", "username", "password", "usernameHint", "passwordHint",
                "button", "forgotPassword"]
    for locale in LOCALES:
        login = json.loads(_path(locale).read_text(encoding="utf-8")).get("login", {})
        for key in required:
            assert str(login.get(key) or "").strip(), f"{locale} login.{key} vazio/ausente"
