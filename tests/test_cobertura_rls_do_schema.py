"""Toda tabela criada em `core/schema.py` precisa de uma migration com RLS.

POR QUE ESTE ARQUIVO EXISTE

`tests_postgres/test_rls_coverage_postgres.py` (issue #205) já garante isto, e
garante melhor: ele lê o catálogo do PostgreSQL real e não aceita policy com
nome certo e efeito errado. Mas ele só roda no workflow `PostgreSQL Migration
Journey`, com container de banco. A suíte padrão — a que roda em segundos, a
que se roda antes de commitar — não tinha nada equivalente.

Foi assim que `company_stock_attention_config_audit_logs` (#271-B1b) nasceu:
adicionada ao `executescript` de `core/schema.py` e a mais lugar nenhum. Como o
`executescript` é traduzido e executado também contra PostgreSQL, a tabela
passou a existir no schema `public` SEM RLS e SEM a policy — uma trilha de
auditoria com nome do ator, IP e user agent legível pelo PostgREST com a chave
anon. A suíte local ficou verde; só o job de PostgreSQL apontou.

O QUE ESTE TESTE É E O QUE NÃO É

É um guarda de COBERTURA, textual: verifica que a tabela aparece numa migration
que instala `block_direct_api_access`. Não prova que a policy é RESTRICTIVE,
FOR ALL, USING (false) e cobre `anon` E `authenticated` — isso é papel do teste
de PostgreSQL, que consulta `pg_policies`. Aqui o objetivo é outro: falhar no
minuto em que alguém cria a tabela, e não meia hora depois no CI.
"""

import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parents[1]
ESQUEMA = RAIZ / 'core' / 'schema.py'
MIGRACOES_SQL = RAIZ / 'supabase' / 'migrations'
MIGRACOES_PY = RAIZ / 'epi_backend' / 'migrations'

POLICY = 'block_direct_api_access'

# Cada entrada aqui é uma exceção que alguém precisou justificar por escrito.
# Manter vazio é o objetivo. `app_migrations` não entra: ela é criada pelo
# próprio runner, fora do `executescript`, e o guarda de PostgreSQL a cobre.
ISENTAS: frozenset[str] = frozenset()


def _tabelas_do_schema() -> list[str]:
    fonte = ESQUEMA.read_text(encoding='utf-8')
    achadas = re.findall(r'CREATE TABLE IF NOT EXISTS\s+([a-zA-Z0-9_]+)', fonte)
    return sorted({nome for nome in achadas if nome not in ISENTAS})


def _texto_das_migrations_com_rls() -> str:
    """Só as migrations que de fato instalam a policy.

    Citar a tabela numa migration qualquer não é cobertura: a #271-B1b tinha a
    tabela citada no `core/schema.py` e em nenhuma migration. O filtro pela
    presença da policy é o que dá sentido à busca pelo nome.
    """
    arquivos = sorted(MIGRACOES_SQL.glob('*.sql')) + sorted(MIGRACOES_PY.glob('*.py'))
    return '\n'.join(
        texto
        for texto in (caminho.read_text(encoding='utf-8') for caminho in arquivos)
        if POLICY in texto
    )


def test_toda_tabela_do_schema_aparece_numa_migration_de_rls():
    cobertas = set(re.findall(r'\b([a-zA-Z0-9_]+)\b', _texto_das_migrations_com_rls()))
    descobertas = [nome for nome in _tabelas_do_schema() if nome not in cobertas]
    assert not descobertas, (
        'Tabelas criadas em core/schema.py sem migration de RLS: '
        + ', '.join(descobertas)
        + '. O `executescript` roda também contra PostgreSQL: a tabela vai '
          'existir no schema `public`, que o PostgREST expõe. Crie o par '
          'migration Python + .sql habilitando RLS e a policy '
          f'`{POLICY}`, como faz a 026.'
    )


def test_a_auditoria_do_padrao_corporativo_esta_coberta():
    """O caso concreto que originou este arquivo, travado explicitamente."""
    sql = (MIGRACOES_SQL / '20260822000000_company_stock_attention_audit.sql')
    assert sql.exists(), 'a migration da auditoria corporativa (#271-B1b) sumiu'
    conteudo = sql.read_text(encoding='utf-8')
    assert 'company_stock_attention_config_audit_logs' in conteudo
    assert conteudo.count('ENABLE ROW LEVEL SECURITY') == 1
    assert POLICY in conteudo


def test_o_par_migration_python_sql_existe():
    modulo = MIGRACOES_PY / '027_company_stock_attention_audit.py'
    assert modulo.exists()
    fonte = modulo.read_text(encoding='utf-8')
    assert "MIGRATION_ID = '027_company_stock_attention_audit'" in fonte
    assert '20260822000000_company_stock_attention_audit.sql' in fonte


def test_a_migration_nao_tem_backfill():
    """Auditoria fabricada é pior do que auditoria ausente.

    Uma linha inserida em massa afirmaria que alguém tomou uma decisão que
    ninguém tomou — e é trilha de auditoria, o lugar onde isso menos pode
    acontecer.
    """
    sql = (MIGRACOES_SQL / '20260822000000_company_stock_attention_audit.sql')
    codigo = '\n'.join(
        linha for linha in sql.read_text(encoding='utf-8').split('\n')
        if not linha.lstrip().startswith('--')
    )
    assert 'INSERT INTO company_stock_attention_config_audit_logs' not in codigo
