"""RETURNING id automático (core/database.py e epi_backend/db.py,
PostgresConnectionWrapper) podia descartar silenciosamente uma escrita
válida quando uma inserção secundária (ex.: auditoria) falhava por um
motivo DIFERENTE de "tabela sem coluna id" na MESMA transação.
Ver issues #177 (epi-controle-app) / #842 (epi-controle) — complementam
#175, que cobre só o ramo tolerado ("tabela sem coluna id").

Vive fora de ``tests/`` de propósito, mesma convenção de
``tests_postgres/test_migration_journey_postgres.py``: roda só contra
PostgreSQL real -- o bug depende de semântica de transação abortada /
SAVEPOINT que SQLite não replica.
"""
import os
from contextlib import closing

import pytest

from core.database import get_connection

pytestmark = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL', '').startswith('postgres'),
    reason='Exige DATABASE_URL apontando para PostgreSQL real.',
)

MARKER = 'RETURNING-ID-ISOLATION-TEST-MARKER'


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    with closing(get_connection()) as connection:
        connection.execute("DELETE FROM units WHERE name = %s", (MARKER,))
        connection.commit()


def test_swallowed_secondary_insert_failure_does_not_discard_prior_write():
    """Reproduz o padrão de modules/*/routes.py:_audit -- uma escrita
    principal bem-sucedida, seguida por uma inserção secundária (aqui,
    simulando company_audit_logs) que falha por violação de NOT NULL
    (não por "coluna id ausente") e é capturada/engolida, como o código
    de produção faz para não derrubar a operação principal só porque a
    auditoria falhou. commit() não deve descartar a escrita principal
    silenciosamente."""
    with closing(get_connection()) as connection:
        company_row = connection.execute('SELECT id FROM companies LIMIT 1').fetchone()
        assert company_row, 'fixture precisa de pelo menos uma company semeada'
        company_id = company_row['id']

        connection.execute(
            "INSERT INTO units (company_id, name, unit_type, city) VALUES (%s, %s, 'Base', 'Sao Paulo')",
            (company_id, MARKER),
        )

        try:
            connection.execute(
                "INSERT INTO company_audit_logs (company_id, actor_user_id, actor_name, "
                "action_type, summary, details_json, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (None, 1, 'Teste', 'repro_marker', 'x', '[]', '2026-01-01'),  # company_id NOT NULL, omitido de propósito
            )
        except Exception:
            pass  # mesmo comportamento de _audit() em produção

        connection.commit()  # não deve levantar, e não deve mascarar um rollback implícito

    with closing(get_connection()) as connection:
        row = connection.execute('SELECT COUNT(*) AS n FROM units WHERE name = %s', (MARKER,)).fetchone()
        assert row['n'] == 1, (
            'A escrita em units foi descartada silenciosamente por causa da falha '
            'engolida no INSERT de auditoria -- exatamente o bug de #177/#842.'
        )


def test_insert_failure_other_than_missing_id_column_leaves_transaction_usable():
    """Depois de um INSERT falhar por um motivo QUALQUER diferente de
    "tabela sem coluna id" (aqui, NOT NULL), a conexão -- ainda dentro da
    MESMA requisição/transação -- deve continuar utilizável para outras
    queries, sem exigir rollback explícito do chamador."""
    with closing(get_connection()) as connection:
        with pytest.raises(Exception):
            connection.execute(
                "INSERT INTO outsourced_companies (legal_name, registration_mode, registration_status, status) "
                "VALUES ('Sem Tenant', 'simplified', 'incomplete', 'active')"
            )  # company_id NOT NULL, omitido de propósito

        # Qualquer query trivial, sem relação nenhuma com o erro acima --
        # não deveria falhar com "current transaction is aborted".
        row = connection.execute('SELECT 1 AS ok').fetchone()
        assert row['ok'] == 1


def test_insert_into_table_without_id_column_still_persists():
    """Ramo tolerado (já coberto por #175, mantido aqui como regressão
    conjunta): uma tabela sem coluna id (app_migrations) continua
    persistindo corretamente depois da correção -- a mudança de ordem
    (rollback-to-savepoint antes da checagem de tolerância) não pode
    quebrar o caminho já correto."""
    marker_id = f'repro-returning-id-{os.getpid()}'
    with closing(get_connection()) as connection:
        connection.execute("DELETE FROM app_migrations WHERE migration_id = %s", (marker_id,))
        connection.execute(
            "INSERT INTO app_migrations (migration_id, status, applied_at) VALUES (%s, %s, %s)",
            (marker_id, 'applied', '2026-01-01T00:00:00+00:00'),
        )
        connection.commit()

    with closing(get_connection()) as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS n FROM app_migrations WHERE migration_id = %s", (marker_id,),
        ).fetchone()
        assert row['n'] == 1
        connection.execute("DELETE FROM app_migrations WHERE migration_id = %s", (marker_id,))
        connection.commit()
