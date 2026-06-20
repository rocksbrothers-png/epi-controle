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


def _runtime_py_files():
    for path in (ROOT / "modules").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def _strip_comments_and_strings(source: str) -> str:
    # Remove comentários de linha e literais de string para não acusar menções
    # em comentários/mensagens de erro.
    no_comments = re.sub(r"#.*", "", source)
    no_strings = re.sub(r"(\"\"\".*?\"\"\"|'''.*?'''|\"[^\"\n]*\"|'[^'\n]*')", "", no_comments, flags=re.DOTALL)
    return no_strings


def test_no_pragma_executed_in_modules_runtime():
    offenders = []
    for path in _runtime_py_files():
        code = _strip_comments_and_strings(path.read_text(encoding="utf-8"))
        if re.search(r"\bPRAGMA\b", code, flags=re.IGNORECASE):
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, (
        "PRAGMA (SQLite) executado em runtime — quebra no PostgreSQL. "
        f"Use introspecção agnóstica (core.schema._table_columns / _safe_add_column). Arquivos: {offenders}"
    )


def test_ensure_stock_movement_size_columns_delegates_to_canonical():
    src = (ROOT / "modules" / "deliveries" / "service.py").read_text(encoding="utf-8")
    fn = src[src.index("def ensure_stock_movement_size_columns"):]
    fn = fn[: fn.index("\n\n\n")] if "\n\n\n" in fn else fn
    assert "PRAGMA" not in _strip_comments_and_strings(fn)
    assert "from core.schema import ensure_stock_movement_size_columns" in fn
