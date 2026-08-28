#!/usr/bin/env python3
"""Relatório bloqueante do CI de migrations — #275, etapa 3.

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

## Etapa 3: o relatório passou a reprovar

O `continue-on-error: true` saiu do passo. O exit code deste script — real
desde a etapa 1, justamente para que a etapa 3 fosse remover uma linha e não
descobrir na hora que ele nunca existiu — passa a segurar o job.

Cinco conjuntos reprovam, e `_problemas_de_cobertura` é a fonte única deles:

    missing_rls                 tabela declarada, RLS desligada
    missing_policy              tabela declarada, RLS ligada, zero policies
    unexpected_policy           policy que nenhuma declaração explica
    known_bootstrap_rls_tables  RLS fora de migration versionada (#309)
    tables_without_rls          tabela do schema vivo sem RLS

Os três últimos eram DIAGNÓSTICO na etapa 2: impressos, contados, sem efeito no
exit code. O ramo "não bloqueia agora" deixou de existir.

## `ERROR:` impresso exige reprovação

Toda a saída passa por `_Tee`, que registra as linhas com `ERROR:`. Se alguma
foi impressa e `problemas` está vazio, a própria ausência vira problema. A
invariante é verificada em execução, não afirmada por leitura do código — e
por isso vale para um `print` que ainda não existe.

Ela cobre o que ESTE script imprime. Não cobre erro de PostgreSQL capturado e
engolido dentro do bootstrap: esses nascem no servidor, morrem num `except` em
Python e só aparecem no log do container, fora do alcance deste processo.
Medi-los é a #315, não a #275.

## O observador não compartilha maquinário com o observado

As consultas de verificação usam `psycopg2` direto, não o wrapper da aplicação.
Um observador que passa pelo mesmo código que audita herda os defeitos que
deveria encontrar.
"""

from __future__ import annotations

import ast
import contextlib
import io
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

#: `ERROR:` como o `psql` o emite. Nenhuma linha assim pode chegar ao relatório
#: sem problema bloqueante correspondente — ver `_erro_sem_reprovacao`.
_LINHA_DE_ERRO = re.compile(r'ERROR:')


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

    `tables_without_rls` não é derivado de nada: é o schema vivo menos as
    tabelas com RLS. Ele existe porque os outros quatro conjuntos têm um
    buraco em comum — todos falam de tabelas que alguém DECLAROU. Apagar a
    declaração E a proteção faz a tabela sumir dos quatro ao mesmo tempo, com
    o CI verde. Foi o que a auditoria da #309 encontrou: remover as chamadas a
    `_enable_rls` sem acrescentar a migration zeraria `known_bootstrap`,
    `missing_rls`, `missing_policy` e `unexpected_policy` de uma vez, deixando
    cinco tabelas desprotegidas. Aqui apagar proteção ACENDE um conjunto em vez
    de apagar quatro.

    NA ETAPA 3 o gate bloqueante exige os CINCO vazios: `missing_rls`,
    `missing_policy`, `unexpected_policy`, `known_bootstrap_rls_tables` e
    `tables_without_rls`. A quarta acopla a #309 ao gate final; a quinta
    impede que a #309 seja "resolvida" apagando o que ela deveria versionar.
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
        'tables_without_rls': presentes - ligadas,
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


def _problemas_de_cobertura(cobertura: dict) -> list:
    """Os CINCO conjuntos que reprovam. Fonte única do veredito e do exit code.

    Antes eram dois lugares: dois `if` soltos no corpo do relatório para
    `missing_rls` e `missing_policy`, e `_diagnosticos()` para os outros três —
    que imprimiam e não reprovavam. Etapa 3 junta os cinco aqui.

    Fonte única porque o gate precisa exercitar cada condição SOZINHA, e gate
    que lê texto é exatamente o defeito que a #275 existe para matar. Pura pelo
    mesmo motivo: as cinco combinações rodam sem PostgreSQL.

    Por que os três últimos deixaram de ser diagnóstico:

    · `unexpected_policy` — a sabotagem end-to-end da etapa 2 plantou uma
      policy que ninguém declara, o relatório a listou corretamente, e o
      veredito imprimiu "Nenhum problema" dez linhas abaixo.
    · `known_bootstrap_rls_tables` — sem ele o CI ficaria verde mantendo RLS
      fora do versionamento, que é a #309 inteira.
    · `tables_without_rls` — sem ele a #309 poderia ser "resolvida" apagando o
      que deveria versionar: os outros quatro só falam de tabelas DECLARADAS, e
      apagar declaração e proteção junto some de todos ao mesmo tempo. A
      sabotagem da #309 mediu os quatro em zero com cinco tabelas nuas.

    Cada linha nomeia o conjunto do relatório, para quem lê o veredito saber
    onde olhar em vez de recontar.
    """
    achados = []
    if cobertura['missing_rls']:
        achados.append(
            f"{len(cobertura['missing_rls'])} tabela(s) declarada(s) sem RLS "
            f'habilitada — ver `missing_rls`')
    if cobertura['missing_policy']:
        achados.append(
            f"{len(cobertura['missing_policy'])} tabela(s) declarada(s) sem "
            f'policy — ver `missing_policy`')
    if cobertura['unexpected_policy']:
        achados.append(
            f"{len(cobertura['unexpected_policy'])} policy(s) que nenhuma "
            f'migration e nenhum `_enable_rls` declaram — ver '
            f'`unexpected_policy`')
    if cobertura['known_bootstrap_rls_tables']:
        achados.append(
            f"{len(cobertura['known_bootstrap_rls_tables'])} tabela(s) com RLS "
            f'criada pelo bootstrap fora de migration versionada (#309) — ver '
            f'`known_bootstrap_rls_tables`')
    if cobertura['tables_without_rls']:
        achados.append(
            f"{len(cobertura['tables_without_rls'])} tabela(s) do schema vivo "
            f'SEM RLS habilitada — ver `tables_without_rls`. Nenhum dos outros '
            f'quatro pega este caso.')
    return achados


class _Tee(io.TextIOBase):
    """Escreve no stdout real e REGISTRA as linhas que carregam `ERROR:`.

    O veredito consulta o registro; não relê o próprio stdout. É o que faz a
    invariante valer para qualquer `print` do relatório — inclusive um que
    ainda não existe — em vez de valer para os pontos que eu conferi à mão.
    """

    def __init__(self, destino):
        self._destino = destino
        self.com_erro = []

    def write(self, texto: str) -> int:
        for linha in texto.splitlines():
            if _LINHA_DE_ERRO.search(linha):
                self.com_erro.append(linha.strip())
        return self._destino.write(texto)

    def flush(self) -> None:
        self._destino.flush()


def _erro_sem_reprovacao(linhas_com_erro: list, problemas: list) -> list:
    """Invariante da etapa 3: `ERROR:` impresso exige exit code != 0.

    Hoje o único emissor é `_aplicar_sql`, e ele já alimenta `problemas` pelo
    mesmo caminho. Esta função existe para o caso que ainda não aconteceu: um
    `print` novo que mostra o erro e deixa o job verde. Foi assim, uma camada
    acima, que a etapa 1 quase passou — `$?` ecoado no log e `cat … || true`.

    NÃO cobre erro de PostgreSQL capturado e engolido dentro do bootstrap: ver
    #315. Esses não passam por este processo e afirmar o contrário seria vender
    cobertura que não existe.
    """
    if problemas or not linhas_com_erro:
        return []
    return [(f'{len(linhas_com_erro)} linha(s) `ERROR:` impressa(s) sem '
             f'problema bloqueante correspondente — o relatório sairia 0 '
             f'mostrando erro')]


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
    """Instala o `_Tee` e roda o relatório dentro dele.

    A captura precisa envolver o corpo INTEIRO e terminar antes do veredito:
    conferir depois de imprimir "Nenhum problema" seria descobrir a
    contradição tarde demais para não publicá-la.
    """
    saida = _Tee(sys.stdout)
    with contextlib.redirect_stdout(saida):
        return _relatorio(saida)


def _relatorio(saida: _Tee) -> int:
    problemas = []

    _titulo('RELATÓRIO DE MIGRATIONS — #275 etapa 3 (bloqueante)')

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
    print('     de expected_rls_tables. Desde a etapa 3, VAZIO é obrigatório.')
    print()
    _conjunto('tables_with_rls_enabled', ligadas)
    _conjunto('tables_with_policies', com_policy)
    print()
    _conjunto('missing_rls', missing_rls)
    _conjunto('missing_policy', missing_policy)
    _conjunto('unexpected_policy', cobertura['unexpected_policy'])
    _conjunto('tables_without_rls', cobertura['tables_without_rls'])
    print('   ↑ o schema vivo menos as tabelas com RLS. Os outros conjuntos só')
    print('     falam de tabelas DECLARADAS; este fala das que existem. Apagar')
    print('     proteção acende aqui em vez de sumir de lá.')

    # `relrowsecurity` e `pg_policies` são dimensões separadas de propósito:
    # tabela com RLS ligada e NENHUMA policy bloqueia tudo em silêncio, que é
    # pior do que nenhuma das duas. Contar só policies não distingue os casos.
    problemas.extend(_problemas_de_cobertura(cobertura))
    problemas.extend(_erro_sem_reprovacao(saida.com_erro, problemas))

    # ── veredito ────────────────────────────────────────────────────────────
    _titulo('VEREDITO')
    if not problemas:
        print('Nenhum problema. As duas trilhas rodam, são idempotentes, e a RLS')
        print('está efetivamente presente no banco.')
        return 0
    for problema in problemas:
        print(f'  · {problema}')
    print()
    print('O passo de migrations BLOQUEIA desde a etapa 3 da #275. Sem')
    print('`continue-on-error`, este código de saída reprova o job.')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
