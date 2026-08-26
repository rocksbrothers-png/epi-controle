#!/usr/bin/env python3
"""Relatório observacional do CI de migrations — #275, etapa 1.

O job `PostgreSQL Schema & Multi-Tenant` aplicava os 32 `.sql` contra um banco
**vazio** e ficava verde de qualquer jeito. Duas coisas se escondiam ali:

- 9 migrations falhavam com `relation … does not exist`, e o erro só ia parar
  no log que ninguém lia;
- **18 passavam sem fazer nada.** Elas guardam cada bloco com
  `CONTINUE WHEN NOT EXISTS (SELECT 1 FROM information_schema.tables …)`, então
  contra banco vazio rodam com sucesso e pulam tudo. São justamente as de RLS.

O segundo é o pior, e é a razão de este relatório existir. Se a correção fosse
só fazer erro reprovar, o job ficaria verde e continuaria não provando **zero**
policies. Por isso a medição decisiva aqui não é ausência de erro — é presença:
o que existe em `pg_policies` e em `pg_class.relrowsecurity` no fim.

## As três trilhas, e por que a ordem importa

    ensure_*                  cria o SCHEMA-BASE          (core/bootstrap.py)
    run_pending_migrations    valida a TRILHA OPERACIONAL (28 módulos Python)
    supabase/migrations/*.sql valida a TRILHA DECLARATIVA (32 arquivos, ADR-0005)

`run_pending_migrations` **não cria schema** — ele roda depois que a base
existe. Acoplar os dois conceitos plantaria no CI a mesma confusão que a #275
existe para desfazer.

## Etapa 1 é observacional — mas o exit code é real

Este script sai com código != 0 quando algo falha, desde já. Quem segura o job
é o `continue-on-error: true` no workflow, não uma mentira aqui dentro. Assim a
etapa 3 é literalmente remover aquela linha — e não descobrir, na hora, que o
exit code nunca existiu (que é exatamente o defeito do passo antigo, onde o
`$?` de cada `psql` só era ecoado no log).

## O observador não compartilha maquinário com o observado

As consultas de verificação usam `psycopg2` direto, não o wrapper da aplicação.
Um observador que passa pelo mesmo código que audita herda os defeitos que
deveria encontrar.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

MIGRACOES_SQL = RAIZ / 'supabase' / 'migrations'

#: Formas em que uma migration declara um alvo de RLS. As três existem no
#: repositório e nenhuma pode ficar de fora: derivar só do `FOREACH` deixaria
#: `tenant_domains` e `rule_engine_shadow_log` fora do conjunto esperado, e o
#: relatório acusaria cobertura completa sem cobrir as duas.
_ARRAY = re.compile(r"tbls?\s+text\[\]\s*:=\s*ARRAY\s*\[(.*?)\]", re.S)
_NOME = re.compile(r"'([a-z_]+)'")
_ENABLE_LITERAL = re.compile(
    r"ALTER\s+TABLE\s+(?:public\.)?([a-z_]+)\s+ENABLE\s+ROW\s+LEVEL\s+SECURITY", re.I)
_POLICY_LITERAL = re.compile(
    r"CREATE\s+POLICY\s+[a-z_]+\s+ON\s+(?:public\.)?([a-z_]+)", re.I)
_TEM_RLS = re.compile(r'ENABLE ROW LEVEL SECURITY|CREATE POLICY', re.I)


def _conexao_de_observacao():
    """Conexão crua, fora do pool e do wrapper da aplicação."""
    import psycopg2
    url = os.environ.get('DATABASE_URL') or ''
    if not url:
        raise SystemExit('DATABASE_URL ausente — este script só roda contra Postgres.')
    conexao = psycopg2.connect(url)
    conexao.autocommit = True
    return conexao


def _consulta(conexao, sql, params=()):
    with conexao.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


def _tabelas(conexao) -> set:
    linhas = _consulta(conexao, """
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    """)
    return {linha[0] for linha in linhas}


def _migration_ids(conexao) -> list:
    """IDs aplicados, em lista — a lista permite ver duplicata, o conjunto não."""
    if 'app_migrations' not in _tabelas(conexao):
        return []
    linhas = _consulta(
        conexao,
        "SELECT migration_id FROM app_migrations WHERE status = 'applied' ORDER BY migration_id",
    )
    return [linha[0] for linha in linhas]


def _rls_esperada() -> set:
    """Alvos de RLS derivados das PRÓPRIAS migrations — nunca um número fixo.

    Um número fixo envelhece na migration seguinte e vira exatamente o falso
    verde que a #275 combate: o relatório continuaria dizendo "cobertura
    completa" sobre um alvo que ninguém atualizou.

    Arquivos sem RLS ficam de fora mesmo que citem nomes de tabela: as
    migrations de `drop` guardam com `table_name = 'x'` e não são alvo.
    """
    esperada = set()
    for caminho in sorted(MIGRACOES_SQL.glob('*.sql')):
        texto = caminho.read_text(encoding='utf-8')
        if not _TEM_RLS.search(texto):
            continue
        for bloco in _ARRAY.findall(texto):
            esperada |= set(_NOME.findall(bloco))
        for nome in _ENABLE_LITERAL.findall(texto) + _POLICY_LITERAL.findall(texto):
            if nome != 'public':
                esperada.add(nome)
    return esperada


def _rls_ligada(conexao) -> set:
    linhas = _consulta(conexao, """
        SELECT c.relname FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relrowsecurity
    """)
    return {linha[0] for linha in linhas}


def _com_policy(conexao) -> set:
    linhas = _consulta(conexao, "SELECT DISTINCT tablename FROM pg_policies WHERE schemaname = 'public'")
    return {linha[0] for linha in linhas}


def _titulo(texto: str) -> None:
    print()
    print('=' * 72)
    print(texto)
    print('=' * 72)


def _conjunto(rotulo: str, valores) -> None:
    ordenado = sorted(valores)
    print(f'{rotulo} ({len(ordenado)}):')
    if not ordenado:
        print('   —')
        return
    for nome in ordenado:
        print(f'   · {nome}')


def _bootstrap() -> None:
    from core.bootstrap import init_db
    init_db()


def _aplicar_sql(passagem: int) -> list:
    """Aplica os 32 `.sql` em ordem e devolve as falhas, nomeadas.

    `ON_ERROR_STOP=1` faz o `psql` abortar o arquivo no primeiro erro e sair
    com código != 0 — isso já funcionava. O que faltava era alguém ler.
    """
    falhas = []
    arquivos = sorted(MIGRACOES_SQL.glob('*.sql'))
    print(f'\n── passagem {passagem}: {len(arquivos)} arquivos')
    for caminho in arquivos:
        resultado = subprocess.run(
            ['psql', '-v', 'ON_ERROR_STOP=1', '-f', str(caminho),
             os.environ['DATABASE_URL']],
            capture_output=True, text=True,
        )
        if resultado.returncode != 0:
            primeira = next(
                (linha for linha in resultado.stderr.splitlines() if 'ERROR' in linha),
                resultado.stderr.strip().splitlines()[0] if resultado.stderr.strip() else '?',
            )
            falhas.append((caminho.name, primeira.strip()))
            print(f'   FALHA {caminho.name}')
            print(f'         {primeira.strip()[:120]}')
        else:
            print(f'   ok    {caminho.name}')
    return falhas


def main() -> int:
    problemas = []

    _titulo('RELATÓRIO DE MIGRATIONS — #275 etapa 1 (observacional)')

    conexao = _conexao_de_observacao()
    antes_de_tudo = _tabelas(conexao)
    print(f'tabelas no schema antes do bootstrap: {len(antes_de_tudo)}')

    # ── 1. schema-base + 2. trilha operacional ──────────────────────────────
    _titulo('1 · ensure_* (schema-base)  +  2 · run_pending_migrations (trilha Python)')
    _bootstrap()
    tabelas_1 = _tabelas(conexao)
    ids_1 = _migration_ids(conexao)
    print(f'tabelas criadas pelos ensure_*: {len(tabelas_1)}')
    print(f'migrations Python aplicadas:    {len(ids_1)}')

    # ── 3. idempotência da trilha operacional ───────────────────────────────
    #
    # Contagem sozinha não prova: remover uma migration e acrescentar outra
    # manteria o total e passaria. O conjunto de IDs é o que fecha essa porta.
    _titulo('3 · idempotência da trilha operacional (segunda execução)')
    _bootstrap()
    ids_2 = _migration_ids(conexao)
    tabelas_2 = _tabelas(conexao)

    novas = sorted(set(ids_2) - set(ids_1))
    sumidas = sorted(set(ids_1) - set(ids_2))
    duplicadas = sorted({i for i in ids_2 if ids_2.count(i) > 1})

    print(f'IDs antes: {len(ids_1)} · IDs depois: {len(ids_2)}')
    print(f'conjuntos idênticos: {set(ids_1) == set(ids_2)}')
    print(f'novas aplicadas na 2ª passagem: {len(novas)} {novas or ""}')
    print(f'IDs que sumiram: {len(sumidas)} {sumidas or ""}')
    print(f'duplicatas: {len(duplicadas)} {duplicadas or ""}')
    print(f'tabelas antes/depois: {len(tabelas_1)}/{len(tabelas_2)}')

    if novas:
        problemas.append(f'a 2ª execução aplicou {len(novas)} migration(s): {novas}')
    if sumidas:
        problemas.append(f'IDs desapareceram entre as execuções: {sumidas}')
    if duplicadas:
        problemas.append(f'IDs duplicados em app_migrations: {duplicadas}')
    if tabelas_1 != tabelas_2:
        problemas.append('o conjunto de tabelas mudou na 2ª execução dos ensure_*')

    # ── 4/5. trilha declarativa, duas passagens ─────────────────────────────
    _titulo('4 e 5 · trilha declarativa (32 .sql, duas passagens)')
    falhas_1 = _aplicar_sql(1)
    falhas_2 = _aplicar_sql(2)
    print(f'\nfalhas na passagem 1: {len(falhas_1)}')
    print(f'falhas na passagem 2: {len(falhas_2)}')
    if falhas_1:
        problemas.append(f'{len(falhas_1)} migration(s) .sql falharam na passagem 1')
    if falhas_2:
        problemas.append(f'{len(falhas_2)} migration(s) .sql falharam na passagem 2 (idempotência)')

    # ── 6. RLS: conjuntos, não contagens ────────────────────────────────────
    _titulo('6 · RLS efetiva — pg_class.relrowsecurity e pg_policies')

    presentes = _tabelas(conexao)
    # Interseção com o schema vivo, e não é detalhe: `user_unit_links` é alvo
    # de RLS numa migration antiga e DROPADO por outra depois. Sem isto ele
    # apareceria como `missing_rls` para sempre — um defeito inventado pelo
    # próprio relatório.
    esperadas = _rls_esperada() & presentes
    ligadas = _rls_ligada(conexao)
    com_policy = _com_policy(conexao)

    missing_rls = esperadas - ligadas
    missing_policy = esperadas - com_policy
    unexpected_policy = com_policy - esperadas

    _conjunto('expected_rls_tables', esperadas)
    _conjunto('tables_with_rls_enabled', ligadas)
    _conjunto('tables_with_policies', com_policy)
    print()
    _conjunto('missing_rls', missing_rls)
    _conjunto('missing_policy', missing_policy)
    _conjunto('unexpected_policy', unexpected_policy)

    # `relrowsecurity` e `pg_policies` são dimensões separadas de propósito:
    # tabela com RLS ligada e NENHUMA policy bloqueia tudo em silêncio, que é
    # pior do que nenhuma das duas. Contar só policies não distingue os casos.
    if missing_rls:
        problemas.append(f'{len(missing_rls)} tabela(s) sem RLS habilitada')
    if missing_policy:
        problemas.append(f'{len(missing_policy)} tabela(s) sem policy')

    # ── veredito ────────────────────────────────────────────────────────────
    _titulo('VEREDITO')
    if not problemas:
        print('Nenhum problema. As duas trilhas rodam, são idempotentes, e a RLS')
        print('está efetivamente presente no banco.')
        return 0
    for problema in problemas:
        print(f'  · {problema}')
    print()
    print('ETAPA 1 É OBSERVACIONAL: o `continue-on-error` do workflow segura o')
    print('job. Estes números são o insumo da etapa 2 — cada falha vira fatia')
    print('própria. Nada é corrigido aqui.')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
