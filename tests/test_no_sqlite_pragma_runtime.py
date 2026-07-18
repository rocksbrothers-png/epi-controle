"""Guard: nenhum `PRAGMA` (sintaxe exclusiva do SQLite) deve ser EXECUTADO em
caminhos de runtime sob modules/. PRAGMA quebra no PostgreSQL/Supabase com
'syntax error at or near "PRAGMA"'.

Regressão real: ensure_stock_movement_size_columns (modules/deliveries/service.py)
executava `PRAGMA table_info(stock_movements)`, derrubando a conferência de
recebimento de PO (POST /api/purchase-requests/{id}/status -> 500) em produção.
Os testes não pegaram porque rodam em SQLite, onde PRAGMA funciona.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


# Diretórios de runtime que rodam tanto em SQLite quanto em PostgreSQL.
# core/ e a introspecção agnóstica (core.schema._safe_add_column) ficam de fora
# porque usam PRAGMA legitimamente sob `if _is_sqlite_connection(...)`; o wrapper
# Postgres (epi_backend/db.py) traduz o SQL. epi_backend/ é incluído porque foi a
# lacuna real: ppe_test_schema.py executava PRAGMA table_info fora de qualquer
# guard de dialeto, derrubando o boot no Postgres (503 em /api/bootstrap).
_RUNTIME_DIRS = ("modules", "epi_backend")
_PRAGMA_ALLOWLIST = {"epi_backend/db.py"}


def _runtime_py_files():
    for base in _RUNTIME_DIRS:
        for path in (ROOT / base).rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            if str(path.relative_to(ROOT)) in _PRAGMA_ALLOWLIST:
                continue
            yield path


_STRING_LITERAL = re.compile(
    r"\"\"\".*?\"\"\"|'''.*?'''|\"[^\"\n]*\"|'[^'\n]*'", re.DOTALL
)


def _sql_strings(source: str) -> list:
    # Extrai os literais de string do código (removendo comentários antes). Um
    # PRAGMA só é EXECUTADO quando está DENTRO de uma string passada a
    # execute()/executescript() — logo é dentro das strings que precisamos
    # procurar. A versão antiga fazia o inverso (removia as strings e depois
    # procurava PRAGMA), o que nunca encontrava um offender real: o keyword
    # sempre vive dentro do literal SQL. Foi essa cegueira que deixou passar o
    # `PRAGMA table_info(epis)` em epi_backend/ppe_test_schema.py.
    no_comments = re.sub(r"#.*", "", source)
    return _STRING_LITERAL.findall(no_comments)


def _pragma_offenders():
    offenders = []
    for path in _runtime_py_files():
        for literal in _sql_strings(path.read_text(encoding="utf-8")):
            if re.search(r"\bPRAGMA\b", literal, flags=re.IGNORECASE):
                offenders.append(str(path.relative_to(ROOT)))
                break
    return offenders


def test_no_pragma_executed_in_modules_runtime():
    offenders = _pragma_offenders()
    assert not offenders, (
        "PRAGMA (SQLite) executado em runtime — quebra no PostgreSQL. "
        f"Use introspecção agnóstica (core.schema._safe_add_column). Arquivos: {offenders}"
    )


def test_ensure_stock_movement_size_columns_delegates_to_canonical():
    src = (ROOT / "modules" / "deliveries" / "service.py").read_text(encoding="utf-8")
    fn = src[src.index("def ensure_stock_movement_size_columns"):]
    fn = fn[: fn.index("\n\n\n")] if "\n\n\n" in fn else fn
    assert not any(re.search(r"\bPRAGMA\b", s, re.I) for s in _sql_strings(fn))
    assert "from core.schema import ensure_stock_movement_size_columns" in fn
