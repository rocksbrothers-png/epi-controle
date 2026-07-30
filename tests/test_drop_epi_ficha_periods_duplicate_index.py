"""Migration 020: drop do índice UNIQUE duplicado em epi_ficha_periods
(Supabase Performance Advisor: "Duplicate Index").

`_ensure_ficha_periods_sequence_unique` (core/schema.py) cria o índice
`uq_epi_ficha_periods_employee_window_sequence` e tenta limpar a constraint
UNIQUE legada (auto-nomeada pelo Postgres) que cobria as mesmas colunas.
Como a função retorna cedo assim que o índice atual já existe (guarda de
idempotência no topo), a limpeza da legada nunca roda de novo em bancos
onde ela sobreviveu a uma execução anterior — daí o índice duplicado em
produção. Esta migration cobre esse gap uma única vez, fora daquela função.
"""

from pathlib import Path

from core.schema import _discover_migration_modules, _load_migration_module


def _sql_path():
    return (
        Path(__file__).resolve().parent.parent
        / 'supabase' / 'migrations' / '20260730000001_drop_epi_ficha_periods_duplicate_index.sql'
    )


def test_migration_020_registered_and_valid():
    discovered = {module_name.rsplit('.', 1)[-1]: path for path, module_name in _discover_migration_modules()}
    assert '020_drop_epi_ficha_periods_duplicate_index' in discovered
    path = discovered['020_drop_epi_ficha_periods_duplicate_index']
    module = _load_migration_module(path, 'epi_backend.migrations.020_drop_epi_ficha_periods_duplicate_index')
    assert module.MIGRATION_ID == '020_drop_epi_ficha_periods_duplicate_index'
    assert callable(module.run)


def test_migration_020_sql_preserves_the_canonical_index_and_targets_duplicates():
    sql = _sql_path().read_text(encoding='utf-8')
    # O índice atual (com nome próprio, usado pelo resto do código) nunca
    # pode ser candidato a exclusão — só o que diverge dele.
    assert "indexname <> 'uq_epi_ficha_periods_employee_window_sequence'" in sql
    # Só considera índices que cobrem exatamente as mesmas 4 colunas do
    # índice atual — não um índice qualquer da tabela.
    assert '(employee_id, period_start, period_end, ficha_sequence)' in sql
    assert 'DROP CONSTRAINT IF EXISTS' in sql
    assert 'DROP INDEX IF EXISTS' in sql


def test_migration_020_is_idempotent_and_skips_missing_table():
    sql = _sql_path().read_text(encoding='utf-8')
    assert "IF NOT EXISTS" in sql
    assert 'RETURN' in sql
