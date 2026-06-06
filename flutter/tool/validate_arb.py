#!/usr/bin/env python3
"""Validação de consistência dos ARBs (epi_i18n) — independente do Flutter SDK.

Regras (falha com exit 1 se violadas):
  1. Todo ARB completo deve ter EXATAMENTE o mesmo conjunto de chaves do template
     (app_pt_BR.arb). Reporta chaves faltando e chaves órfãs.
  2. Nenhum ARB completo pode estar vazio (sem chaves de tradução).
  3. JSON inválido falha.
  4. Toda chave parametrizada (valor com '{placeholder}') precisa de metadata
     @chave com 'placeholders' em TODOS os locales.
  5. Um .arb que não seja alias declarado e esteja vazio falha.

ARBs "alias" (apenas chaves @@... e um comentário de alias, ex.: app_en.arb que
aponta para app_en_US.arb) são reconhecidos e ignorados nas regras 1–2.

Uso: python3 tool/validate_arb.py   (a partir de flutter/)
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

ARB_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "packages", "epi_i18n", "lib", "l10n",
)
TEMPLATE = "app_pt_BR.arb"
FULL_LOCALES = ["app_pt_BR.arb", "app_en_US.arb", "app_es_ES.arb",
                "app_fr_FR.arb", "app_no_NO.arb"]

PLACEHOLDER = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}")


def load(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def real_keys(arb: dict) -> set[str]:
    return {k for k in arb if not k.startswith("@")}


def is_alias(arb: dict) -> bool:
    """Alias: só chaves de metadata @@... e um comentário sinalizando alias."""
    if real_keys(arb):
        return False
    comment = str(arb.get("@@comment", "")).lower()
    return "alias" in comment


def main() -> int:
    errors: list[str] = []
    arb_files = sorted(glob.glob(os.path.join(ARB_DIR, "app_*.arb")))
    if not arb_files:
        print(f"❌ Nenhum ARB encontrado em {ARB_DIR}")
        return 1

    parsed: dict[str, dict] = {}
    for path in arb_files:
        name = os.path.basename(path)
        try:
            parsed[name] = load(path)
        except json.JSONDecodeError as exc:
            errors.append(f"{name}: JSON inválido — {exc}")

    # Regra 5: arquivos vazios não-alias
    for name, arb in parsed.items():
        if not real_keys(arb) and not is_alias(arb):
            errors.append(f"{name}: ARB vazio (sem chaves) e não é alias declarado.")

    # Template
    template = parsed.get(TEMPLATE)
    if template is None:
        errors.append(f"Template {TEMPLATE} ausente.")
        _report(errors)
        return 1 if errors else 0
    ref_keys = real_keys(template)
    if not ref_keys:
        errors.append(f"{TEMPLATE}: template não pode estar vazio.")

    # Regras 1–2: locales completos
    for name in FULL_LOCALES:
        arb = parsed.get(name)
        if arb is None:
            errors.append(f"{name}: locale completo ausente.")
            continue
        keys = real_keys(arb)
        if not keys:
            errors.append(f"{name}: locale completo está vazio.")
            continue
        missing = ref_keys - keys
        extra = keys - ref_keys
        if missing:
            errors.append(f"{name}: faltando {len(missing)} chave(s): "
                          f"{sorted(missing)}")
        if extra:
            errors.append(f"{name}: {len(extra)} chave(s) órfã(s): "
                          f"{sorted(extra)}")

    # Regra 4: metadata de placeholders
    for name in FULL_LOCALES:
        arb = parsed.get(name)
        if not arb:
            continue
        for key in real_keys(arb):
            value = arb[key]
            if isinstance(value, str) and PLACEHOLDER.search(value):
                meta = arb.get(f"@{key}")
                if not (isinstance(meta, dict) and meta.get("placeholders")):
                    errors.append(
                        f"{name}: chave parametrizada '{key}' sem metadata "
                        f"@{key}.placeholders")

    _report(errors)
    return 1 if errors else 0


def _report(errors: list[str]) -> None:
    if errors:
        print("❌ Validação de ARB falhou:")
        for err in errors:
            print(f"   • {err}")
    else:
        print("✅ ARBs consistentes: mesmas chaves, sem vazios, metadata OK.")


if __name__ == "__main__":
    sys.exit(main())
