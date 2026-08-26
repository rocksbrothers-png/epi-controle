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

import ast
import os
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

MIGRACOES_SQL = RAIZ / 'supabase' / 'migrations'
MODULOS = RAIZ / 'modules'

#: Formas em que uma migration declara um alvo de RLS. As QUATRO existem no
#: repositório e nenhuma pode ficar de fora: derivar só do `FOREACH` deixaria
#: `tenant_domains` e `rule_engine_shadow_log` fora do conjunto esperado, e o
#: relatório acusaria cobertura completa sem cobrir as duas.
#:
#: O `_ESCALAR` entrou na etapa 2. Sem ele, oito tabelas declaradas com
#: `DECLARE tbl text := 'nome'` — um bloco por tabela, molde de
#: `20260812000000_employee_unit_links.sql` — apareciam como
#: `unexpected_policy`, ou seja: o relatório acusava como intrusa uma policy
#: que a própria migration ao lado declarava.
_ARRAY = re.compile(r"tbls?\s+text\[\]\s*:=\s*ARRAY\s*\[(.*?)\]", re.S)
_ESCALAR = re.compile(r"\btbls?\s+text\s*:=\s*'([a-z_]+)'", re.I)
_NOME = re.compile(r"'([a-z_]+)'")
_ENABLE_LITERAL = re.compile(
    r"ALTER\s+TABLE\s+(?:public\.)?([a-z_]+)\s+ENABLE\s+ROW\s+LEVEL\s+SECURITY", re.I)
_POLICY_LITERAL = re.compile(
    r"CREATE\s+POLICY\s+[a-z_]+\s+ON\s+(?:public\.)?([a-z_]+)", re.I)
_TEM_RLS = re.compile(r'ENABLE ROW LEVEL SECURITY|CREATE POLICY', re.I)

#: `psql:/caminho/absoluto/arquivo.sql:32: ERROR: …` — o caminho consome o
#: corte de 120 e a mensagem some antes no repositório de nome mais longo.
#: Truncar a MENSAGEM, não a linha, faz os dois relatórios coincidirem.
_PREFIXO_PSQL = re.compile(r'^psql:.*?:(\d+):\s*')


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


def _tabelas_de_rls(texto: str) -> set:
    """Alvos de RLS declarados em UM arquivo de migration. Função pura.

    Pura de propósito. É o que permite ao gate exercitar os quatro moldes com
    fonte sintética — inclusive o negativo — em vez de ler o repositório e
    concluir "deu o número que eu esperava", que não distingue derivação certa
    de derivação sortuda.

    O `_TEM_RLS` não é filtro de estilo: sem ele, uma migration de `drop` que
    guarda um bloco com `tbl text := 'x'` entraria no conjunto esperado e
    viraria `missing_rls` eterno — um defeito inventado pelo relatório.
    """
    if not _TEM_RLS.search(texto):
        return set()
    alvos = set()
    for bloco in _ARRAY.findall(texto):
        alvos |= set(_NOME.findall(bloco))
    alvos |= set(_ESCALAR.findall(texto))
    for nome in _ENABLE_LITERAL.findall(texto) + _POLICY_LITERAL.findall(texto):
        if nome != 'public':
            alvos.add(nome)
    return alvos


def _rls_esperada() -> set:
    """Alvos de RLS derivados das PRÓPRIAS migrations — nunca um número fixo.

    Um número fixo envelhece na migration seguinte e vira exatamente o falso
    verde que a #275 combate: o relatório continuaria dizendo "cobertura
    completa" sobre um alvo que ninguém atualizou.
    """
    esperada = set()
    for caminho in sorted(MIGRACOES_SQL.glob('*.sql')):
        esperada |= _tabelas_de_rls(caminho.read_text(encoding='utf-8'))
    return esperada


def _tabelas_de_enable_rls(fonte: str) -> set:
    """Tabelas passadas literalmente a `_enable_rls(...)`. Função pura.

    AST e não regex, e o motivo importa: o primeiro argumento é a conexão (um
    `Name`), então só `ast.Constant` de string entra, sem lista de exclusão.

    Argumento que não seja literal NÃO é derivado. Isso é intencional: a
    tabela então cai em `unexpected_policy`, que é a direção barulhenta. Toda
    falha desta derivação — nome da função trocado, argumento virando
    variável, mecanismo novo — torna o relatório mais RUIDOSO, nunca mais
    silencioso. A direção oposta é que seria perigosa.
    """
    alvos = set()
    for no in ast.walk(ast.parse(fonte)):
        if not isinstance(no, ast.Call):
            continue
        chamada = no.func
        nome = chamada.id if isinstance(chamada, ast.Name) else getattr(chamada, 'attr', '')
        if nome != '_enable_rls':
            continue
        for argumento in no.args:
            if isinstance(argumento, ast.Constant) and isinstance(argumento.value, str):
                alvos.add(argumento.value)
    return alvos


def _rls_por_bootstrap() -> set:
    """Tabelas cuja RLS o BOOTSTRAP cria, fora de migration versionada — #309.

    `ensure_payment_tables` e `ensure_subscription_tables` estão na lista
    `_ensure_fns` de `core/bootstrap.py`, então rodam em todo boot: não é
    fluxo sob demanda, e a RLS delas existe em produção. O defeito é de
    RASTREABILIDADE — o DDL não é migration, não entra em `app_migrations`, e
    é invisível a qualquer gate derivado de migrations.

    Derivado, nunca lista fixa: uma lista literal aqui envelheceria e
    esconderia a próxima tabela que alguém acrescentasse ao mesmo padrão.
    """
    alvos = set()
    for caminho in sorted(MODULOS.rglob('*.py')):
        alvos |= _tabelas_de_enable_rls(caminho.read_text(encoding='utf-8'))
    return alvos


def _classificar_cobertura(declaradas, por_bootstrap, ligadas, com_policy, presentes) -> dict:
    """As origens de cobertura de RLS, separadas. Função pura.

    `known_bootstrap` NÃO é dobrado dentro de `expected`. Uma tabela que só
    tem RLS porque o bootstrap a criou fora de migration continua sendo
    dívida (#309); fundir os dois a faria sumir do relatório com o CI verde.
    Ela sai de `unexpected_policy` — leitura correta, não é policy intrusa —
    e passa a viver num conjunto próprio, nomeado e contado.

    A interseção com `presentes` não é detalhe: `user_unit_links` é alvo de
    RLS numa migration antiga e DROPADO por outra depois. Sem ela apareceria
    como `missing_rls` para sempre.

    NA ETAPA 3 o gate bloqueante exige `known_bootstrap_rls_tables` VAZIO,
    além de `missing_rls`, `missing_policy` e `unexpected_policy` zerados.
    Sem essa quarta condição o CI ficaria totalmente verde mantendo cinco
    tabelas cuja RLS segue fora do versionamento — exatamente o verde
    incompleto que a #275 existe para eliminar.
    """
    esperadas = declaradas & presentes
    bootstrap = (por_bootstrap & presentes) - esperadas
    cobertas = esperadas | bootstrap
    return {
        'expected_rls_tables': esperadas,
        'known_bootstrap_rls_tables': bootstrap,
        'missing_rls': cobertas - ligadas,
        'missing_policy': cobertas - com_policy,
        'unexpected_policy': com_policy - cobertas,
    }


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


def _diagnosticos(bootstrap_fora_de_migration, policies_nao_declaradas) -> list:
    """Achados que NÃO bloqueiam na etapa 2 — e que mesmo assim são ditos.

    Diagnóstico ≠ problema: nada aqui muda o exit code, e é isso que a etapa 2
    combinou. Mas o veredito precisa NOMEÁ-LOS, senão "Nenhum problema"
    aparece sobre achado aberto. Detector que mede certo e resume errado é o
    mesmo falso verde, mudado para o rodapé.

    Não é hipótese: a sabotagem end-to-end da etapa 2 plantou uma policy que
    ninguém declara, o relatório a listou corretamente em `unexpected_policy`,
    e o veredito imprimiu "Nenhum problema" dez linhas abaixo.

    Pura para que o gate exercite as quatro combinações sem PostgreSQL. Uma
    versão anterior deste gate cobria só o CONSUMO da lista, e esvaziá-la na
    origem passava com todos os testes verdes.
    """
    achados = []
    if bootstrap_fora_de_migration:
        achados.append(
            f'{len(bootstrap_fora_de_migration)} tabela(s) com RLS criada pelo '
            f'bootstrap fora de migration versionada (#309) — ver '
            f'`known_bootstrap_rls_tables`')
    if policies_nao_declaradas:
        achados.append(
            f'{len(policies_nao_declaradas)} policy(s) que nenhuma migration e '
            f'nenhum `_enable_rls` declaram — ver `unexpected_policy`')
    return achados


def _mensagem_de_falha(stderr: str) -> str:
    """A primeira linha de ERROR, sem o caminho e já truncada. Função pura.

    O truncamento mora AQUI e em nenhum outro lugar. Era `linha[:120]` no
    ponto de impressão, e como a linha do `psql` começa com o caminho
    absoluto do arquivo, o repositório de nome mais longo cortava a mensagem
    mais cedo: dois relatórios divergindo pelo nome do diretório, não pelo
    conteúdo.
    """
    linhas = stderr.strip().splitlines()
    primeira = next(
        (linha for linha in linhas if 'ERROR' in linha),
        linhas[0] if linhas else '?',
    )
    return _PREFIXO_PSQL.sub(r'linha \1: ', primeira.strip())[:120]


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
            mensagem = _mensagem_de_falha(resultado.stderr)
            falhas.append((caminho.name, mensagem))
            print(f'   FALHA {caminho.name}')
            print(f'         {mensagem}')
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
    ligadas = _rls_ligada(conexao)
    com_policy = _com_policy(conexao)

    cobertura = _classificar_cobertura(
        _rls_esperada(), _rls_por_bootstrap(), ligadas, com_policy, presentes)
    bootstrap_fora_de_migration = cobertura['known_bootstrap_rls_tables']
    missing_rls = cobertura['missing_rls']
    missing_policy = cobertura['missing_policy']

    _conjunto('expected_rls_tables', cobertura['expected_rls_tables'])
    print()
    _conjunto('known_bootstrap_rls_tables', bootstrap_fora_de_migration)
    print('   ↑ RLS criada pelo BOOTSTRAP, fora de migration versionada (#309).')
    print('     Não é policy intrusa — e também não é cobertura legítima: é')
    print('     dívida. Fica aqui, contada e nomeada, em vez de sumir dentro')
    print('     de expected_rls_tables. A etapa 3 exige este conjunto VAZIO.')
    print()
    _conjunto('tables_with_rls_enabled', ligadas)
    _conjunto('tables_with_policies', com_policy)
    print()
    _conjunto('missing_rls', missing_rls)
    _conjunto('missing_policy', missing_policy)
    _conjunto('unexpected_policy', cobertura['unexpected_policy'])

    # `relrowsecurity` e `pg_policies` são dimensões separadas de propósito:
    # tabela com RLS ligada e NENHUMA policy bloqueia tudo em silêncio, que é
    # pior do que nenhuma das duas. Contar só policies não distingue os casos.
    if missing_rls:
        problemas.append(f'{len(missing_rls)} tabela(s) sem RLS habilitada')
    if missing_policy:
        problemas.append(f'{len(missing_policy)} tabela(s) sem policy')

    diagnosticos = _diagnosticos(
        bootstrap_fora_de_migration, cobertura['unexpected_policy'])

    # ── veredito ────────────────────────────────────────────────────────────
    _titulo('VEREDITO')
    if not problemas:
        if not diagnosticos:
            print('Nenhum problema. As duas trilhas rodam, são idempotentes, e a RLS')
            print('está efetivamente presente no banco.')
            return 0
        print('As verificações BLOQUEANTES da etapa 2 passaram: as duas trilhas')
        print('rodam, são idempotentes, e não há tabela sem RLS ou sem policy.')
        print()
        print('Mas há DIAGNÓSTICO aberto. Não bloqueia agora; bloqueia na etapa 3:')
        for diagnostico in diagnosticos:
            print(f'  · {diagnostico}')
        print()
        print('O gate bloqueante da etapa 3 exigirá QUATRO conjuntos vazios:')
        print('missing_rls, missing_policy, unexpected_policy e')
        print('known_bootstrap_rls_tables. É a quarta que acopla a #309 ao gate')
        print('final — sem ela o CI ficaria verde com RLS fora do versionamento.')
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
