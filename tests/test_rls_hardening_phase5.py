"""RLS Hardening Phase 5 (migration 019).

Supabase Security Advisor sinalizou 17 tabelas sem a policy
`block_direct_api_access`: algumas com RLS habilitado sem policy (projeto
SaaS, `wlneevhqklboctghvdeo`, severidade INFO), outras com RLS nunca
habilitado (projeto corporativo, `kkmskwmkhyssrxqbsrqv`, severidade ERROR/
CRITICAL — ambos os casos são a mesma lacuna: as tabelas foram criadas pelo
bootstrap Python (core/schema.py) fora do pipeline supabase/migrations/, e
nunca passaram pelas fases de RLS hardening 1-4/010/011.

Este teste garante que a migration 019 está registrada no runner e que sua
SQL cobre exatamente as 17 tabelas sinalizadas.
"""

from pathlib import Path

from core.schema import _discover_migration_modules, _load_migration_module

FLAGGED_TABLES = {
    'legal_entities',
    'user_legal_entities',
    'employee_legal_entity_movements',
    'outsourced_companies',
    'service_contracts',
    'epi_reimbursements',
    'delivery_evidence',
    'stock_reservations',
    'stock_replenishment_needs',
    'ppe_test_plans',
    'ppe_test_candidates',
    'ppe_test_participants',
    'ppe_test_distributions',
    'ppe_test_evaluations',
    'ppe_test_events',
    'ppe_test_incidents',
    'ppe_test_suggestions',
}


def _sql_path():
    return (
        Path(__file__).resolve().parent.parent
        / 'supabase' / 'migrations' / '20260730000000_rls_hardening_phase5.sql'
    )


def test_migration_019_registered_and_valid():
    discovered = {module_name.rsplit('.', 1)[-1]: path for path, module_name in _discover_migration_modules()}
    assert '019_rls_hardening_phase5' in discovered
    path = discovered['019_rls_hardening_phase5']
    module = _load_migration_module(path, 'epi_backend.migrations.019_rls_hardening_phase5')
    assert module.MIGRATION_ID == '019_rls_hardening_phase5'
    assert callable(module.run)


def test_migration_019_sql_covers_all_flagged_tables():
    sql = _sql_path().read_text(encoding='utf-8')
    for table in sorted(FLAGGED_TABLES):
        assert f"'{table}'" in sql, f'{table} fora da migration RLS phase 5'
    assert 'ENABLE ROW LEVEL SECURITY' in sql
    assert 'block_direct_api_access' in sql


def test_migration_019_is_idempotent_and_skips_missing_tables():
    """Mesmo padrão das fases anteriores: CONTINUE WHEN NOT EXISTS pula
    tabelas ausentes (ex.: projeto sem o módulo PPE Test provisionado ainda),
    e o IF NOT EXISTS em pg_policies evita erro de policy duplicada ao rodar
    a migration mais de uma vez (o runner já marca como aplicada, mas o SQL
    em si também precisa ser seguro sozinho)."""
    sql = _sql_path().read_text(encoding='utf-8')
    assert 'CONTINUE WHEN NOT EXISTS' in sql
    assert 'IF NOT EXISTS' in sql
    assert 'AS RESTRICTIVE FOR ALL TO anon, authenticated USING (false)' in sql


def test_migration_019_does_not_duplicate_earlier_phase_tables():
    """As fases anteriores (1-4, 010, 011) já cobriram outro conjunto de
    tabelas — este teste evita que a phase 5 relist e por engano tente
    recriar a policy numa tabela já coberta (o CREATE POLICY IF NOT EXISTS já
    protegeria, mas listar de novo indicaria confusão sobre o que falta)."""
    earlier_tables = {'users', 'employee_portal_links', 'epi_evaluation_summary', 'report_requests'}
    sql = _sql_path().read_text(encoding='utf-8')
    for table in earlier_tables:
        assert f"'{table}'" not in sql
