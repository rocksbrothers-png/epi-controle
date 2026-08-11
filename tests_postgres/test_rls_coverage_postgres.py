"""Toda tabela em `public` precisa de RLS e da policy de bloqueio (issue #205).

Por que este arquivo existe: houve SETE fases de RLS hardening (002, 003, 004,
005, 010, 011, 019), cada uma reagindo ao Supabase Security Advisor **depois**
de o problema chegar em produção. O teste da fase 5 valida uma lista fixa das
17 tabelas então conhecidas — prova o que já se sabia, e não detecta tabela
nova. Foi assim que as três tabelas do Centro de Migração (ADR-0003) ficaram
sem RLS até o Advisor apontar.

Este teste inverte a lógica: descobre as tabelas do catálogo do PostgreSQL e
exige cobertura de cada uma. Tabela nova sem RLS quebra o CI no PR que a cria,
em vez de virar ERROR no Advisor semanas depois.

Depende de o ambiente ter os roles `anon`/`authenticated` (o workflow os cria)
— sem eles as migrations de RLS nem chegam a rodar.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytestmark = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL', '').startswith('postgres'),
    reason='Cobertura de RLS só faz sentido contra PostgreSQL real.',
)

POLICY_NAME = 'block_direct_api_access'

# Tabelas que o PostgREST não expõe e que, portanto, não precisam da policy.
# Manter vazio é o objetivo: cada entrada aqui é uma exceção que alguém
# precisou justificar por escrito.
EXEMPT: frozenset[str] = frozenset()


@pytest.fixture(scope='module')
def connection():
    from core.bootstrap import init_db
    from core.database import get_connection
    init_db()
    return get_connection()


def _rows(connection, sql):
    from epi_backend.db import row_to_dict
    return [row_to_dict(r) for r in connection.execute(sql).fetchall()]


def _roles_present(connection):
    found = _rows(
        connection,
        "SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')",
    )
    return {r['rolname'] for r in found} == {'anon', 'authenticated'}


def test_the_supabase_roles_exist_so_the_rls_migrations_actually_run(connection):
    """Sem `anon`/`authenticated`, a migration 002 falha e o runner PARA.

    O efeito não é só a RLS: nenhuma migration posterior roda. Este teste
    existe para que a causa apareça nomeada, em vez de as demais falharem por
    consequência.
    """
    assert _roles_present(connection), (
        'Os roles `anon` e `authenticated` não existem neste banco. As '
        'migrations de RLS falham e o runner para na 002 — o schema fica sem '
        'nenhuma migration aplicada. Crie os roles antes de rodar a suíte '
        '(o workflow faz isso num passo próprio).'
    )


def test_every_public_table_has_rls_enabled(connection):
    missing = [
        row['relname']
        for row in _rows(
            connection,
            """
            SELECT c.relname
              FROM pg_class c
              JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE n.nspname = 'public' AND c.relkind = 'r'
               AND NOT c.relrowsecurity
             ORDER BY 1
            """,
        )
        if row['relname'] not in EXEMPT
    ]
    assert not missing, (
        'Tabelas em `public` sem RLS habilitada: ' + ', '.join(missing) + '. '
        'Toda tabela nova precisa entrar numa migration de RLS hardening — o '
        'schema public é exposto ao PostgREST no Supabase.'
    )


def test_every_public_table_has_the_blocking_policy(connection):
    """RLS habilitada sem policy bloqueia por padrão, mas de forma implícita.

    O projeto usa uma policy RESTRICTIVE explícita para que a intenção fique
    legível no catálogo — e é isso que o Advisor cobra como `rls_enabled_no_policy`.
    """
    missing = [
        row['relname']
        for row in _rows(
            connection,
            f"""
            SELECT c.relname
              FROM pg_class c
              JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE n.nspname = 'public' AND c.relkind = 'r'
               AND NOT EXISTS (
                     SELECT 1 FROM pg_policies p
                      WHERE p.schemaname = 'public'
                        AND p.tablename = c.relname
                        AND p.policyname = '{POLICY_NAME}'
                   )
             ORDER BY 1
            """,
        )
        if row['relname'] not in EXEMPT
    ]
    assert not missing, (
        f'Tabelas em `public` sem a policy `{POLICY_NAME}`: '
        + ', '.join(missing)
        + '. Acrescente-as à migration de RLS hardening mais recente.'
    )


def test_the_migration_center_tables_are_covered(connection):
    """O caso concreto que originou a #205, travado explicitamente.

    `migration_job_records` guarda o payload das linhas importadas — dados
    pessoais, incluindo CPF. Estava sem RLS no projeto corporativo.
    """
    for table in ('migration_jobs', 'migration_job_records', 'migration_field_mappings'):
        row = _rows(
            connection,
            f"""
            SELECT c.relrowsecurity AS rls,
                   (SELECT count(*) FROM pg_policies p
                     WHERE p.schemaname = 'public' AND p.tablename = '{table}'
                       AND p.policyname = '{POLICY_NAME}') AS policies
              FROM pg_class c
              JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE n.nspname = 'public' AND c.relname = '{table}'
            """,
        )
        assert row, f'{table} não existe no schema'
        assert row[0]['rls'], f'{table} está sem RLS habilitada'
        assert row[0]['policies'] == 1, f'{table} está sem a policy {POLICY_NAME}'
