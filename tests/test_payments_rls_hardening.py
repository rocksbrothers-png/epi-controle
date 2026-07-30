"""RLS hardening da tabela de pagamentos/assinaturas (Supabase Security
Advisor: `rls_enabled_no_policy` em `payments`, `payment_plans`,
`subscriptions`, `invoices`, `subscription_audit_logs`).

`modules.payments.service._enable_rls` já habilitava RLS nessas 5 tabelas
desde a criação (resolvendo `rls_disabled_in_public`), mas nunca criava
nenhuma policy — o Advisor sinaliza esse estado ambíguo como
`rls_enabled_no_policy`. Estes testes garantem que a policy
`block_direct_api_access` (mesmo padrão das fases de RLS hardening em
supabase/migrations/) também é aplicada, de forma idempotente.
"""

from modules.payments.service import _enable_rls, ensure_payment_tables, ensure_subscription_tables


class _RecordingConnection:
    """Registra todo SQL executado; simula Postgres o suficiente para o
    caminho de `_enable_rls` (não executa de verdade — só grava)."""

    def __init__(self):
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append(sql)
        return self

    def executescript(self, sql):
        self.executed.append(sql)

    def commit(self):
        pass

    def rollback(self):
        pass


def test_enable_rls_alters_table_and_creates_policy_for_each_table():
    conn = _RecordingConnection()
    _enable_rls(conn, 'payments', 'payment_plans')

    alters = [sql for sql in conn.executed if 'ENABLE ROW LEVEL SECURITY' in sql]
    policies = [sql for sql in conn.executed if 'block_direct_api_access' in sql]

    assert any('ALTER TABLE payments ENABLE ROW LEVEL SECURITY' in sql for sql in alters)
    assert any('ALTER TABLE payment_plans ENABLE ROW LEVEL SECURITY' in sql for sql in alters)
    assert any("CREATE POLICY block_direct_api_access ON payments " in sql for sql in policies)
    assert any("CREATE POLICY block_direct_api_access ON payment_plans " in sql for sql in policies)


def test_enable_rls_policy_is_restrictive_and_denies_anon_authenticated():
    conn = _RecordingConnection()
    _enable_rls(conn, 'subscriptions')
    policy_sql = next(sql for sql in conn.executed if 'block_direct_api_access' in sql)
    assert 'AS RESTRICTIVE FOR ALL TO anon, authenticated USING (false)' in policy_sql


def test_enable_rls_policy_creation_is_guarded_by_existence_check():
    """CREATE POLICY não suporta IF NOT EXISTS no Postgres — a idempotência
    vem do DO $$ ... IF NOT EXISTS (SELECT ... pg_policies) ... $$ em volta,
    mesmo padrão das fases de RLS hardening em supabase/migrations/."""
    conn = _RecordingConnection()
    _enable_rls(conn, 'invoices')
    policy_sql = next(sql for sql in conn.executed if 'block_direct_api_access' in sql)
    assert 'DO $$' in policy_sql
    assert 'IF NOT EXISTS' in policy_sql
    assert 'pg_policies' in policy_sql


def test_enable_rls_swallows_errors_for_sqlite_backed_tests():
    """SQLite não entende ALTER TABLE ... ENABLE ROW LEVEL SECURITY nem
    DO $$ ... $$ — precisa falhar em silêncio, não quebrar o bootstrap."""
    class _FailingConnection:
        def execute(self, sql, params=None):
            raise Exception('sqlite syntax error')

        def rollback(self):
            pass

    _enable_rls(_FailingConnection(), 'payments')  # não deve levantar


def test_ensure_payment_tables_and_subscription_tables_cover_all_five_flagged_tables():
    """As 5 tabelas sinalizadas pelo Advisor (payments, payment_plans,
    subscriptions, invoices, subscription_audit_logs) precisam continuar
    cobertas pelas chamadas de _enable_rls em ensure_payment_tables/
    ensure_subscription_tables — regressão contra alguém remover a chamada
    ao mexer nessas funções no futuro."""
    import inspect

    payment_source = inspect.getsource(ensure_payment_tables)
    subscription_source = inspect.getsource(ensure_subscription_tables)

    assert "_enable_rls(connection, 'payments', 'payment_plans')" in payment_source
    assert (
        "_enable_rls(connection, 'subscriptions', 'invoices', 'subscription_audit_logs')"
        in subscription_source
    )
