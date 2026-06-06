#!/usr/bin/env python3
"""Patch helper: insere novas chaves i18n nos ARBs e nos arquivos Dart gerados.

Por que existe: o ambiente de CI/dev usado para esta migração não tem o Flutter
SDK disponível para rodar `flutter gen-l10n`. Este script replica exatamente o
formato gerado pela ferramenta, garantindo que ARBs e Dart fiquem consistentes.

Quando o Flutter estiver disponível, a fonte de verdade volta a ser os ARBs +
`flutter gen-l10n`; este script é apenas uma ponte determinística.

Uso: python3 tool/_gen_i18n_keys.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARB_DIR = ROOT / "packages/epi_i18n/lib/l10n"
GEN_DIR = ROOT / "apps/epi_admin/lib/core/i18n/generated"

LOCALES = ["pt_BR", "en_US", "es_ES", "fr_FR", "no_NO"]

# Mapeia locale -> (arquivo regional Dart, sufixos de classe base e regional)
REGIONAL = {
    "pt_BR": ("app_localizations_pt.dart", "Pt", "PtBr"),
    "en_US": ("app_localizations_en.dart", "En", "EnUs"),
    "es_ES": ("app_localizations_es.dart", "Es", "EsEs"),
    "fr_FR": ("app_localizations_fr.dart", "Fr", "FrFr"),
    "no_NO": ("app_localizations_no.dart", "No", "NoNo"),
}

# Cada chave: name, params (lista de (nome, tipo_dart, tipo_arb)) e traduções.
# params vazio = getter simples.
KEYS = [
    # ── Busca / campos comuns ────────────────────────────────────────────────
    ("searchEmployeeHint", [], {
        "pt_BR": "Buscar colaborador...", "en_US": "Search employee...",
        "es_ES": "Buscar colaborador...", "fr_FR": "Rechercher un employé...",
        "no_NO": "Søk etter ansatt...",
    }),
    ("searchEpiHint", [], {
        "pt_BR": "Buscar EPI...", "en_US": "Search PPE...",
        "es_ES": "Buscar EPP...", "fr_FR": "Rechercher un EPI...",
        "no_NO": "Søk etter PVU...",
    }),
    ("fieldQuantity", [], {
        "pt_BR": "Quantidade", "en_US": "Quantity", "es_ES": "Cantidad",
        "fr_FR": "Quantité", "no_NO": "Antall",
    }),
    ("filterAll", [], {
        "pt_BR": "Todos", "en_US": "All", "es_ES": "Todos",
        "fr_FR": "Tous", "no_NO": "Alle",
    }),
    # ── Entregas ─────────────────────────────────────────────────────────────
    ("deliveryStockAvailable", [("qty", "int", "int")], {
        "pt_BR": "Estoque: {qty}", "en_US": "Stock: {qty}", "es_ES": "Stock: {qty}",
        "fr_FR": "Stock : {qty}", "no_NO": "Lager: {qty}",
    }),
    ("deliveryDateLabel", [], {
        "pt_BR": "Data da entrega", "en_US": "Delivery date", "es_ES": "Fecha de entrega",
        "fr_FR": "Date de remise", "no_NO": "Leveringsdato",
    }),
    ("deliveryNextReplacement", [], {
        "pt_BR": "Próxima substituição", "en_US": "Next replacement",
        "es_ES": "Próxima sustitución", "fr_FR": "Prochain remplacement",
        "no_NO": "Neste utskifting",
    }),
    ("deliveryDateValue", [("date", "String", "String")], {
        "pt_BR": "Data: {date}", "en_US": "Date: {date}", "es_ES": "Fecha: {date}",
        "fr_FR": "Date : {date}", "no_NO": "Dato: {date}",
    }),
    # ── Devoluções ───────────────────────────────────────────────────────────
    ("returnSelectDelivery", [], {
        "pt_BR": "Selecionar entrega para devolver", "en_US": "Select delivery to return",
        "es_ES": "Seleccionar entrega a devolver", "fr_FR": "Sélectionner la remise à retourner",
        "no_NO": "Velg levering som skal returneres",
    }),
    ("returnDeliveredInfo", [("date", "String", "String"), ("qty", "int", "int")], {
        "pt_BR": "Entregue em {date} · Qtd: {qty}", "en_US": "Delivered on {date} · Qty: {qty}",
        "es_ES": "Entregado el {date} · Cant.: {qty}", "fr_FR": "Remis le {date} · Qté : {qty}",
        "no_NO": "Levert {date} · Antall: {qty}",
    }),
    ("returnConditionTitle", [], {
        "pt_BR": "Condição do EPI", "en_US": "PPE condition", "es_ES": "Condición del EPP",
        "fr_FR": "État de l'EPI", "no_NO": "PVU-tilstand",
    }),
    ("returnDestinationTitle", [], {
        "pt_BR": "Destino", "en_US": "Destination", "es_ES": "Destino",
        "fr_FR": "Destination", "no_NO": "Destinasjon",
    }),
    ("returnDestDiscard", [], {
        "pt_BR": "Descarte", "en_US": "Discard", "es_ES": "Desecho",
        "fr_FR": "Mise au rebut", "no_NO": "Kassering",
    }),
    ("returnDestRepair", [], {
        "pt_BR": "Manutenção", "en_US": "Maintenance", "es_ES": "Mantenimiento",
        "fr_FR": "Maintenance", "no_NO": "Vedlikehold",
    }),
    ("returnDestStock", [], {
        "pt_BR": "Retornar ao estoque", "en_US": "Return to stock", "es_ES": "Devolver al stock",
        "fr_FR": "Retour au stock", "no_NO": "Tilbake til lager",
    }),
    ("returnSubmit", [], {
        "pt_BR": "Registrar Devolução", "en_US": "Register return", "es_ES": "Registrar devolución",
        "fr_FR": "Enregistrer le retour", "no_NO": "Registrer retur",
    }),
    ("returnDeliveryDateInfo", [("date", "String", "String")], {
        "pt_BR": "Entrega: {date}", "en_US": "Delivery: {date}", "es_ES": "Entrega: {date}",
        "fr_FR": "Remise : {date}", "no_NO": "Levering: {date}",
    }),
    ("returnQuantityInfo", [("qty", "int", "int")], {
        "pt_BR": "Quantidade: {qty}", "en_US": "Quantity: {qty}", "es_ES": "Cantidad: {qty}",
        "fr_FR": "Quantité : {qty}", "no_NO": "Antall: {qty}",
    }),
    # ── Compras ──────────────────────────────────────────────────────────────
    ("purchaseTitleLabel", [], {
        "pt_BR": "Título da requisição", "en_US": "Request title",
        "es_ES": "Título de la solicitud", "fr_FR": "Titre de la demande",
        "no_NO": "Tittel på forespørsel",
    }),
    ("purchaseSelectUnit", [], {
        "pt_BR": "Selecione uma unidade", "en_US": "Select a unit", "es_ES": "Seleccione una unidad",
        "fr_FR": "Sélectionnez une unité", "no_NO": "Velg en enhet",
    }),
    ("purchaseItemsTitle", [], {
        "pt_BR": "Itens da requisição", "en_US": "Request items",
        "es_ES": "Artículos de la solicitud", "fr_FR": "Articles de la demande",
        "no_NO": "Forespørselens varer",
    }),
    ("purchaseAddEpi", [], {
        "pt_BR": "Adicionar EPI", "en_US": "Add PPE", "es_ES": "Agregar EPP",
        "fr_FR": "Ajouter un EPI", "no_NO": "Legg til PVU",
    }),
    ("purchaseNoItems", [], {
        "pt_BR": "Nenhum item adicionado", "en_US": "No items added",
        "es_ES": "Ningún artículo agregado", "fr_FR": "Aucun article ajouté",
        "no_NO": "Ingen varer lagt til",
    }),
    ("purchaseCreate", [], {
        "pt_BR": "Criar Requisição", "en_US": "Create request", "es_ES": "Crear solicitud",
        "fr_FR": "Créer la demande", "no_NO": "Opprett forespørsel",
    }),
    ("purchaseAddAtLeastOne", [], {
        "pt_BR": "Adicione pelo menos um item", "en_US": "Add at least one item",
        "es_ES": "Agregue al menos un artículo", "fr_FR": "Ajoutez au moins un article",
        "no_NO": "Legg til minst én vare",
    }),
    ("purchaseQuantityColon", [], {
        "pt_BR": "Quantidade:", "en_US": "Quantity:", "es_ES": "Cantidad:",
        "fr_FR": "Quantité :", "no_NO": "Antall:",
    }),
    ("purchaseItemsCount", [("count", "int", "int")], {
        "pt_BR": "{count} itens", "en_US": "{count} items", "es_ES": "{count} artículos",
        "fr_FR": "{count} articles", "no_NO": "{count} varer",
    }),
    ("purchaseStatusAwaiting", [], {
        "pt_BR": "Aguardando", "en_US": "Awaiting", "es_ES": "En espera",
        "fr_FR": "En attente", "no_NO": "Venter",
    }),
    ("purchaseStatusCorrection", [], {
        "pt_BR": "Correção solicitada", "en_US": "Correction requested",
        "es_ES": "Corrección solicitada", "fr_FR": "Correction demandée",
        "no_NO": "Korrigering forespurt",
    }),
    ("purchaseStatusAwaitingReceipt", [], {
        "pt_BR": "Aguardando recebimento", "en_US": "Awaiting receipt",
        "es_ES": "Esperando recepción", "fr_FR": "En attente de réception",
        "no_NO": "Venter på mottak",
    }),
    ("purchaseStatusCompleted", [], {
        "pt_BR": "Concluído", "en_US": "Completed", "es_ES": "Completado",
        "fr_FR": "Terminé", "no_NO": "Fullført",
    }),
    ("purchaseStatusCancelled", [], {
        "pt_BR": "Cancelado", "en_US": "Cancelled", "es_ES": "Cancelado",
        "fr_FR": "Annulé", "no_NO": "Kansellert",
    }),
]


def dart_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'").replace("$", "\\$")


def to_dart_template(value: str, params) -> str:
    """Converte '{x}' -> '${x}' e escapa o resto para string Dart single-quote."""
    # Protege os placeholders enquanto escapa o texto literal.
    tokens = re.split(r"(\{[a-zA-Z_][a-zA-Z0-9_]*\})", value)
    out = []
    for tok in tokens:
        m = re.fullmatch(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", tok)
        if m:
            out.append("${" + m.group(1) + "}")
        else:
            out.append(dart_escape(tok))
    return "".join(out)


# ── 1. Patch ARBs ────────────────────────────────────────────────────────────

def patch_arb(locale: str):
    path = ARB_DIR / f"app_{locale}.arb"
    text = path.read_text(encoding="utf-8")
    # Remove a última chave '}' para reabrir o objeto.
    idx = text.rstrip().rfind("}")
    head = text[:idx].rstrip()
    if not head.endswith(","):
        head += ","
    lines = []
    for name, params, tr in KEYS:
        value = tr[locale]
        lines.append(f'  "{name}": {json.dumps(value, ensure_ascii=False)},')
        # Metadata de placeholders em TODOS os locales (convenção do projeto) p/
        # chaves parametrizadas — necessário p/ flutter gen-l10n e p/ os testes.
        if params:
            ph = ", ".join(
                f'"{p}": {{ "type": "{arb_t}" }}' for (p, _dart, arb_t) in params
            )
            lines.append(f'  "@{name}": {{ "placeholders": {{ {ph} }} }},')
    # remove trailing comma da última linha
    block = "\n".join(lines)
    block = block.rstrip().rstrip(",")
    path.write_text(head + "\n" + block + "\n}\n", encoding="utf-8")


# ── 2. Patch arquivo abstrato ────────────────────────────────────────────────

def abstract_decl(name, params) -> str:
    pt = next(tr for n, _p, tr in KEYS if n == name)["pt_BR"]
    doc = (
        f"  /// No description provided for @{name}.\n"
        f"  ///\n"
        f"  /// In pt_BR, this message translates to:\n"
        f"  /// **'{pt}'**\n"
    )
    if params:
        sig = ", ".join(f"{dart_t} {p}" for (p, dart_t, _a) in params)
        return doc + f"  String {name}({sig});\n"
    return doc + f"  String get {name};\n"


def patch_abstract():
    path = GEN_DIR / "app_localizations.dart"
    text = path.read_text(encoding="utf-8")
    marker = "  String get syncDone;\n"
    assert marker in text, "marcador syncDone não encontrado no abstrato"
    block = "\n" + "\n".join(abstract_decl(n, p) for n, p, _t in KEYS)
    text = text.replace(marker, marker + block, 1)
    path.write_text(text, encoding="utf-8")


# ── 3. Patch arquivos regionais ──────────────────────────────────────────────

def regional_impl(name, params, value) -> str:
    if params:
        sig = ", ".join(f"{dart_t} {p}" for (p, dart_t, _a) in params)
        body = to_dart_template(value, params)
        return (
            f"\n  @override\n"
            f"  String {name}({sig}) {{\n"
            f"    return '{body}';\n"
            f"  }}\n"
        )
    body = to_dart_template(value, params)
    return f"\n  @override\n  String get {name} => '{body}';\n"


def patch_regional(locale: str):
    fname, _base, _reg = REGIONAL[locale]
    path = GEN_DIR / fname
    text = path.read_text(encoding="utf-8")
    block = "".join(regional_impl(n, p, t[locale]) for n, p, t in KEYS)
    # syncDone aparece 2x (classe base e classe regional) com valores diferentes
    # em locales não-PT (base usa fallback pt_BR). Usamos re.sub para capturar
    # a linha completa independentemente do valor, e inserimos o bloco após cada
    # ocorrência. Usamos lambda para evitar problemas com backslashes no bloco.
    assert "String get syncDone =>" in text, \
        f"syncDone não encontrado em {fname}"
    escaped_block = block  # sem backslashes problemáticos para re.sub
    text = re.sub(
        r'(  String get syncDone => [^\n]+;\n)',
        lambda m: m.group(0) + escaped_block,
        text,
    )
    path.write_text(text, encoding="utf-8")


def main():
    for loc in LOCALES:
        patch_arb(loc)
        patch_regional(loc)
    patch_abstract()
    print(f"OK: {len(KEYS)} chaves inseridas em {len(LOCALES)} locales + abstrato.")


if __name__ == "__main__":
    main()
