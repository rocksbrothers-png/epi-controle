"""Predicado único de visibilidade da entrega (issue #211).

Módulo folha de propósito: importa só `epi_backend.db`, para que
`ficha`, `portal`, `devolutions` e `deliveries` possam usá-lo sem recriar os
ciclos de import que a issue #148 desfez.

O problema que resolve: depois que uma importação de histórico é **homologada**,
revertê-la não apaga mais as entregas — marca `migration_reverted_at` e as
mantém no banco para auditoria (rollback lógico). Sem um filtro nas leituras,
essa marcação seria puramente decorativa: a entrega revertida continuaria
aparecendo na ficha de EPI, contando como posse ativa e podendo ser devolvida.
Um rollback que não reverte nada é pior do que não ter rollback, porque parece
ter funcionado.

Por que a checagem de coluna em vez de um `AND` fixo: o banco de um tenant pode
estar numa versão de schema anterior à migration 023, e as fixtures de teste
criam `deliveries` com o conjunto mínimo de colunas de cada cenário. Um
predicado incondicional quebraria os dois casos com "no such column" — mesmo
padrão defensivo já usado em `_writable_columns` e `fetch_employees`.
"""

from __future__ import annotations

from epi_backend.db import table_columns

REVERSAL_COLUMN = 'migration_reverted_at'


def has_reversal_column(connection) -> bool:
    try:
        return REVERSAL_COLUMN in set(table_columns(connection, 'deliveries'))
    except Exception:  # noqa: BLE001 - tabela ausente em fixture mínima
        return False


def active_delivery_sql(connection, alias: str = 'deliveries', *, prefix: str = ' AND ') -> str:
    """Trecho de SQL que exclui entregas revertidas logicamente.

    Devolve string vazia quando a coluna não existe — assim o chamador pode
    concatenar sem condicional própria.

    ``alias`` é sempre literal do código chamador, nunca de entrada externa.
    """
    if not has_reversal_column(connection):
        return ''
    return f"{prefix}COALESCE({alias}.{REVERSAL_COLUMN}, '') = ''"
