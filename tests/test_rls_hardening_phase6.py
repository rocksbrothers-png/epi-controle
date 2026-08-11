"""RLS Hardening Phase 6 (migration 020) — issue #205.

Fecha as seis tabelas que um banco criado do zero deixava sem RLS.

Três são do Centro de Migração (ADR-0003): nasceram em `core/schema.py` depois
da fase 5 e nunca entraram numa fase de hardening. O Supabase Security Advisor
as reporta como ERROR no projeto corporativo (`rls_disabled_in_public`) e INFO
no SaaS (`rls_enabled_no_policy`). `migration_job_records` guarda o payload das
linhas importadas, com dados pessoais.

As outras três já estão protegidas nos dois projetos de produção, mas NÃO num
banco novo — ver `test_phase6_deliberately_relists_three_earlier_tables`.
"""

from pathlib import Path

from core.schema import _discover_migration_modules, _load_migration_module

MIGRATION_CENTER_TABLES = {
    'migration_jobs',
    'migration_job_records',
    'migration_field_mappings',
}

# Cobertas por fases anteriores, mas puladas em banco novo.
RELISTED_TABLES = {
    'epi_evaluation_summary',
    'purchase_pendencies',
    'report_requests',
}

FLAGGED_TABLES = MIGRATION_CENTER_TABLES | RELISTED_TABLES


def _sql_path():
    return (
        Path(__file__).resolve().parent.parent
        / 'supabase' / 'migrations' / '20260811000000_rls_hardening_phase6.sql'
    )


def test_migration_020_registered_and_valid():
    discovered = {module_name.rsplit('.', 1)[-1]: path for path, module_name in _discover_migration_modules()}
    assert '020_rls_hardening_phase6' in discovered
    path = discovered['020_rls_hardening_phase6']
    module = _load_migration_module(path, 'epi_backend.migrations.020_rls_hardening_phase6')
    assert module.MIGRATION_ID == '020_rls_hardening_phase6'
    assert callable(module.run)


def test_migration_020_sql_covers_all_flagged_tables():
    sql = _sql_path().read_text(encoding='utf-8')
    for table in sorted(FLAGGED_TABLES):
        assert f"'{table}'" in sql, f'{table} fora da migration RLS phase 6'
    assert 'ENABLE ROW LEVEL SECURITY' in sql
    assert 'block_direct_api_access' in sql


def test_migration_020_is_idempotent_and_skips_missing_tables():
    sql = _sql_path().read_text(encoding='utf-8')
    assert 'CONTINUE WHEN NOT EXISTS' in sql
    assert 'IF NOT EXISTS' in sql
    assert 'AS RESTRICTIVE FOR ALL TO anon, authenticated USING (false)' in sql


def test_phase6_deliberately_relists_three_earlier_tables():
    """A fase 5 tem um teste proibindo relistar tabela de fase anterior. Aqui
    a relistagem é intencional, e o motivo precisa ficar registrado.

    `epi_evaluation_summary`, `purchase_pendencies` e `report_requests` foram
    cobertas por fases anteriores — mas aquelas fases rodam ANTES de a tabela
    existir, e o `CONTINUE WHEN NOT EXISTS` as pula em silêncio. Em produção
    elas acabaram protegidas (a migration rodou de novo depois da tabela
    existir); num banco criado do zero, não. Verificado contra PostgreSQL 16:
    sem esta fase, as seis ficam descobertas.

    Relistar é inofensivo — o `IF NOT EXISTS` em `pg_policies` evita policy
    duplicada — e é o que torna ambiente novo igual a produção.
    """
    sql = _sql_path().read_text(encoding='utf-8')
    for table in sorted(RELISTED_TABLES):
        assert f"'{table}'" in sql
    # A justificativa precisa estar no próprio arquivo, não só aqui.
    assert 'ausente' in sql.lower() or 'novo' in sql.lower()


def test_migration_center_tables_are_the_reason_this_phase_exists():
    """Trava o caso concreto da #205 contra remoção acidental."""
    sql = _sql_path().read_text(encoding='utf-8')
    for table in sorted(MIGRATION_CENTER_TABLES):
        assert f"'{table}'" in sql, (
            f'{table} é do Centro de Migração e foi o motivo desta fase existir'
        )
