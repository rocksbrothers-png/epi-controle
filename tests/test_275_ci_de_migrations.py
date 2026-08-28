"""O CI de migrations prova as duas trilhas, e agora REPROVA — #275, etapa 3.

O job `PostgreSQL Schema & Multi-Tenant` aplicava os 32 `.sql` contra um banco
vazio e ficava verde. Estes gates travam o que a etapa 1 estabeleceu, e o
primeiro deles é o que a auditoria mais custou a enxergar: **18 das 32
migrations passavam sem fazer nada**, porque guardam cada bloco com
`CONTINUE WHEN NOT EXISTS (information_schema.tables)`. Contra banco vazio elas
pulam tudo com sucesso — e são justamente as de RLS.

Daí a forma das asserções aqui: nenhuma delas mede ausência de erro. Todas
medem presença — que o bootstrap real é chamado, que as duas trilhas rodam,
que a RLS é consultada nas duas dimensões, que o esperado é derivado e não
fixado.

Leitura sempre por `_codigo`: o diff da etapa 1 é denso em comentário, e
comentário que satisfaz asserção foi o defeito que a Fase 1 da #271 corrigiu
em três gates desta mesma frente.

## Etapa 3

O `continue-on-error: true` saiu do passo de migrations e o exit code do
relatório passou a segurar o job. Os gates que a etapa 3 acrescenta seguem a
mesma regra do resto do arquivo — medir comportamento, não texto:

- `_problemas_de_cobertura` é exercitada com os cinco conjuntos, um por vez;
- cada conjunto tem uma MUTAÇÃO que prova que o gate acima o enxerga, e o
  agregador tem a sua, com controle contra o original;
- o `pipefail` é sabotado DE VERDADE: o `run:` extraído do workflow roda com
  um relatório que sai 1, e o controle sem `pipefail` precisa sair 0.

Presença textual de `set -euo pipefail` continua sendo verificada, mas como
complemento. Sozinha ela prova que a linha existe, não que ela funciona — e a
etapa 1 já reportou `success` num passo cujo script saiu 1.
"""

import ast
import importlib.util
import io
import pathlib
import re
import subprocess
import tokenize

RAIZ = pathlib.Path(__file__).resolve().parent.parent
WORKFLOW = RAIZ / '.github' / 'workflows' / 'backend-ci.yml'
SCRIPT = RAIZ / 'scripts' / 'ci_migrations_report.py'
MIGRACOES = RAIZ / 'supabase' / 'migrations'


def _codigo(fonte: str) -> str:
    """Fonte Python sem comentários **e sem docstrings**, via `ast` + `tokenize`.

    (Duplicado de `test_unit_minimum_stock.py` seguindo o idioma do
    repositório. A convergência num helper compartilhado é dívida em #948.)
    """
    linhas = fonte.split('\n')
    apagar = set()
    for no in ast.walk(ast.parse(fonte)):
        if not isinstance(no, (ast.Module, ast.ClassDef,
                               ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        corpo = getattr(no, 'body', None)
        if not corpo:
            continue
        primeiro = corpo[0]
        if (isinstance(primeiro, ast.Expr)
                and isinstance(primeiro.value, ast.Constant)
                and isinstance(primeiro.value.value, str)):
            fim = primeiro.end_lineno or primeiro.lineno
            apagar.update(range(primeiro.lineno, fim + 1))
    cortes = {}
    for tok in tokenize.generate_tokens(io.StringIO(fonte).readline):
        if tok.type == tokenize.COMMENT:
            linha, coluna = tok.start
            cortes[linha] = min(cortes.get(linha, coluna), coluna)
    return '\n'.join(
        '' if i in apagar else (linha[:cortes[i]] if i in cortes else linha)
        for i, linha in enumerate(linhas, 1)
    )


def _yaml_sem_comentarios(fonte: str) -> str:
    """YAML sem `#`. O diff da etapa 1 explica muito, e explicação não é prova."""
    return '\n'.join(
        linha.split('#')[0] if not linha.lstrip().startswith('#') else ''
        for linha in fonte.split('\n')
    )


def _script() -> str:
    return _codigo(SCRIPT.read_text(encoding='utf-8'))


def _modulo():
    """Carrega o relatório como módulo, para exercitar a derivação de verdade.

    Ler o código-fonte prova que uma linha existe; chamar a função prova que
    ela faz o que diz. Os gates de derivação abaixo são funcionais por isso —
    a etapa 1 desta issue nasceu de três asserções que liam texto e passavam
    por causa de um comentário.

    O import é seguro: o `psycopg2` só é carregado dentro de
    `_conexao_de_observacao`, e nada no nível do módulo abre conexão.
    """
    spec = importlib.util.spec_from_file_location('ci_migrations_report', SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _workflow() -> str:
    return _yaml_sem_comentarios(WORKFLOW.read_text(encoding='utf-8'))


#: O passo mudou de nome na etapa 3 — de "relatório observacional" para
#: "as duas trilhas, bloqueante". As âncoras vivem aqui para que renomear
#: quebre um lugar só, e com mensagem em vez de `ValueError`.
_ANCORA_MIGRATIONS = 'Migrations — as duas trilhas, bloqueante'
_ANCORA_RUFF = 'Ruff check'


def _passo(ancora: str) -> str:
    """O bloco YAML de um passo, delimitado por INDENTAÇÃO.

    A etapa 3 precisa afirmar em qual passo o `continue-on-error` sobrevive, e
    a versão anterior fatiava por "até o nome do próximo passo". Isso funciona
    para um passo do meio e falha para o último do job — o do Ruff é o último,
    e a fatia vazaria para dentro do job seguinte. Um `continue-on-error`
    acrescentado ao job de PostgreSQL apareceria como sendo do Ruff.
    """
    linhas = _workflow().split('\n')
    for i, linha in enumerate(linhas):
        if ancora not in linha or not linha.lstrip().startswith('- name:'):
            continue
        recuo = len(linha) - len(linha.lstrip())
        corpo = [linha]
        for seguinte in linhas[i + 1:]:
            if seguinte.strip() and len(seguinte) - len(seguinte.lstrip()) <= recuo:
                break
            corpo.append(seguinte)
        return '\n'.join(corpo)
    raise AssertionError(
        f'passo {ancora!r} não encontrado no workflow — se foi renomeado, '
        f'atualize a âncora: todos os gates do passo dependem dela')


def _passo_de_migrations() -> str:
    """Só o passo da #275 — o job tem outros, e o Ruff tem `continue-on-error`."""
    return _passo(_ANCORA_MIGRATIONS)


def _passo_do_ruff() -> str:
    """Só o passo do Ruff — território da #948, intocado pela etapa 3."""
    return _passo(_ANCORA_RUFF)


def _run_do_passo() -> str:
    """O `run:` do passo de migrations, dedentado e executável.

    Extrair do workflow em vez de reescrever à mão é o que faz a sabotagem do
    `pipefail` medir o passo REAL. Um script copiado no teste provaria que a
    cópia funciona.
    """
    passo = _passo_de_migrations()
    corpo = passo[passo.index('run: |') + len('run: |'):]
    linhas = [linha for linha in corpo.split('\n') if linha.strip()]
    assert linhas, 'o `run:` do passo de migrations ficou vazio'
    recuo = min(len(linha) - len(linha.lstrip()) for linha in linhas)
    return '\n'.join(linha[recuo:] for linha in linhas)


def _modulo_mutado(velho: str, novo: str):
    """Carrega o relatório com uma mutação aplicada — e PROVA que ela pegou.

    Sem a asserção de aplicação, uma mutação que não casa com o texto vira
    "gate passou" quando na verdade nada foi testado. Já aconteceu nesta
    frente: três gates da etapa 1 passavam por comentário.
    """
    fonte = SCRIPT.read_text(encoding='utf-8')
    assert velho in fonte, f'MUTACAO NAO APLICOU: {velho!r} não está no script'
    mutada = fonte.replace(velho, novo, 1)
    assert mutada != fonte, 'MUTACAO NAO APLICOU: texto idêntico após a troca'
    espaco = {'__name__': 'ci_migrations_report_mutado', '__file__': str(SCRIPT)}
    exec(compile(mutada, str(SCRIPT), 'exec'), espaco)  # noqa: S102 - mutação controlada
    return espaco


#: Os cinco conjuntos que a etapa 3 exige vazios, e o que basta para sujar
#: cada um sozinho. `_classificar_cobertura` devolve estes nomes.
_CINCO = ('missing_rls', 'missing_policy', 'unexpected_policy',
          'known_bootstrap_rls_tables', 'tables_without_rls')


def _cobertura(**sujos) -> dict:
    """Uma cobertura limpa, com só os conjuntos nomeados não-vazios."""
    base = {nome: set() for nome in _CINCO}
    base['expected_rls_tables'] = set()
    for nome, valor in sujos.items():
        base[nome] = valor
    return base


# ═══════════════════════════════════════════════════════════════════════════
# Os roles que as migrations exigem — pré-condição da plataforma
# ═══════════════════════════════════════════════════════════════════════════

def _passo_de_roles() -> str:
    """Só o passo dos roles — o job tem vários `psql`."""
    texto = _workflow()
    assert 'Pré-condições do Supabase' in texto, \
        ('o passo que cria `anon`/`authenticated` sumiu do workflow — sem ele '
         'todo CREATE POLICY volta a falhar e o CI mede o ambiente, não as '
         'migrations')
    inicio = texto.index('Pré-condições do Supabase')
    fim = texto.index('- name: Validate Multi-Tenant invariants', inicio)
    return texto[inicio:fim]


def test_o_ci_cria_os_dois_roles_que_as_migrations_exigem():
    """16 das 32 migrations criam policies `TO anon, authenticated`.

    Sem os roles, medido: 16/32 `.sql` falham, 1 de 28 migrations Python
    aplicam, 72 tabelas ficam sem RLS. Com eles: 0, 28/28, 0. Nenhuma linha de
    migration muda entre os dois números — o defeito era do ambiente do CI.

    Leitura por `_yaml_sem_comentarios`: o comentário acima do passo cita os
    dois roles várias vezes, e comentário que satisfaz asserção é exatamente o
    defeito que a Fase 1 da #271 corrigiu em três gates.
    """
    passo = _passo_de_roles()
    for role in ('anon', 'authenticated'):
        assert f'CREATE ROLE {role} NOLOGIN' in passo, \
            f'o passo deixou de criar `{role}` como NOLOGIN'


def test_os_roles_nao_ganham_privilegio_nenhum():
    """`NOLOGIN` sem `GRANT` é a fronteira do que este CI afirma provar.

    Com isto, o CI prova que as policies foram CRIADAS. Não prova que elas
    ISOLAM — para isso é preciso conectar como `anon` e ver a leitura ser
    negada, o que é frente própria. Um `GRANT` aqui mudaria em silêncio o que
    o job mede; quem precisar dele que troque este gate de propósito.
    """
    passo = _passo_de_roles()
    assert 'GRANT' not in passo.upper(), \
        ('o passo passou a conceder privilégio aos roles — isso muda o que o '
         'CI mede e o gate precisa ser revisto junto')


def test_o_ci_nao_cria_service_role():
    """Nenhuma migration referencia `service_role`. Criar por precaução é ruído."""
    assert 'service_role' not in _workflow(), \
        'o workflow passou a criar `service_role`, que nenhuma migration usa'


def test_os_roles_existem_antes_de_qualquer_migration():
    """Depois do bootstrap não adianta: o `CREATE POLICY` já teria falhado."""
    texto = _workflow()
    assert texto.index('Pré-condições do Supabase') \
        < texto.index(_ANCORA_MIGRATIONS), \
        'o passo dos roles foi parar depois do relatório'


def test_a_criacao_de_roles_nao_engole_erro():
    """Um `CREATE ROLE` que falha em silêncio devolve o CI ao estado anterior.

    Sem `ON_ERROR_STOP`, o `psql` sai 0 mesmo com o bloco `DO` reprovando, e o
    relatório seguinte voltaria a medir a ausência dos roles sem que nada
    ficasse vermelho.

    A asserção é por CHAMADA, não pelo token: a primeira versão deste gate
    procurava `ON_ERROR_STOP=1` no passo inteiro e passava com a guarda
    removida do `psql` que cria os roles, porque o segundo `psql` — o que só
    confere — ainda a tinha.
    """
    passo = _passo_de_roles()
    assert 'set -euo pipefail' in passo, \
        'o passo dos roles deixou de propagar falha do shell'
    chamadas = [l for l in passo.split('\n') if l.strip().startswith('psql ')]
    assert chamadas, 'o passo dos roles não chama mais o psql'
    sem_guarda = [l.strip() for l in chamadas if 'ON_ERROR_STOP=1' not in l]
    assert sem_guarda == [], \
        f'psql sem ON_ERROR_STOP no passo dos roles: {sem_guarda}'


# ═══════════════════════════════════════════════════════════════════════════
# O job usa o bootstrap real, e não declara schema
# ═══════════════════════════════════════════════════════════════════════════

def test_o_job_usa_o_bootstrap_real():
    """O schema-base vem dos `ensure_*`, executados pelo bootstrap da aplicação."""
    script = _script()
    assert 'from core.bootstrap import init_db' in script, \
        'o relatório deixou de usar o bootstrap real da aplicação'
    assert 'init_db()' in script, 'o bootstrap é importado mas não é executado'


def test_o_job_nao_declara_schema_proprio():
    """Um schema-base mantido à parte divergiria em silêncio — o defeito da #238.

    A regra que impede esta issue de virar a próxima: acrescentar uma tabela
    via `ensure_*` deve fazer o CI passar a exercitá-la **sem que ninguém
    edite o workflow**.
    """
    for rotulo, fonte in (('script', _script()), ('workflow', _workflow())):
        assert not re.search(r'CREATE\s+TABLE', fonte, re.I), \
            f'{rotulo} passou a declarar schema em vez de usar os ensure_*'
        assert 'base_schema' not in fonte, \
            f'{rotulo} aponta para um schema-base paralelo'


# ═══════════════════════════════════════════════════════════════════════════
# As duas trilhas
# ═══════════════════════════════════════════════════════════════════════════

def test_a_trilha_operacional_python_e_exercitada():
    """Os 28 módulos são o que roda em produção — e não eram validados por nada."""
    script = _script()
    assert 'app_migrations' in script, \
        'o relatório deixou de observar a trilha operacional'
    assert '_migration_ids' in script


def test_a_idempotencia_operacional_compara_ids_e_nao_so_a_contagem():
    """Contagem sozinha não prova.

    Remover uma migration e acrescentar outra manteria o total e passaria. O
    conjunto de IDs é o que fecha essa porta, e a lista (não o conjunto) é o
    que permite ver duplicata.
    """
    script = _script()
    assert 'set(ids_1) == set(ids_2)' in script, \
        'a idempotência da trilha Python voltou a ser provada só por contagem'
    assert 'duplicadas' in script, 'o relatório deixou de checar IDs duplicados'
    assert 'novas' in script and 'sumidas' in script, \
        'o relatório deixou de nomear o que entrou e o que sumiu'


def test_a_trilha_declarativa_roda_duas_vezes():
    """Idempotência dos `.sql`: todas as 32 afirmam ser, nenhuma jamais provou."""
    script = _script()
    assert '_aplicar_sql(1)' in script and '_aplicar_sql(2)' in script, \
        'a segunda passagem dos .sql sumiu — a idempotência deixou de ser provada'
    assert 'ON_ERROR_STOP' in script, \
        'sem ON_ERROR_STOP o primeiro erro de um arquivo deixa de abortá-lo'


# ═══════════════════════════════════════════════════════════════════════════
# A derivação — etapa 2. Funcional, com fonte sintética e caso negativo.
# ═══════════════════════════════════════════════════════════════════════════

_MOLDES = {
    'array': """
        DO $$ DECLARE tbl text[] := ARRAY['tabela_array', 'outra_array'];
        BEGIN EXECUTE 'ALTER TABLE x ENABLE ROW LEVEL SECURITY'; END $$;
    """,
    'escalar': """
        DO $$
        DECLARE
          tbl text := 'tabela_escalar';
        BEGIN
          EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', tbl);
        END $$;
    """,
    'alter_literal': 'ALTER TABLE public.tabela_alter ENABLE ROW LEVEL SECURITY;',
    'policy_literal': (
        'ALTER TABLE tabela_policy ENABLE ROW LEVEL SECURITY;\n'
        'CREATE POLICY p ON public.tabela_policy FOR ALL TO anon USING (false);'
    ),
}


def test_a_derivacao_cobre_os_quatro_moldes():
    """Os quatro existem no repositório, e o escalar faltava até a etapa 2.

    Sem ele, oito tabelas declaradas com `DECLARE tbl text := 'nome'` eram
    acusadas de `unexpected_policy` — o relatório chamando de intrusa uma
    policy que a migration ao lado declarava.

    Fonte sintética e não o repositório: ler os arquivos reais e conferir o
    total prova que o número bateu, não que a derivação está certa.
    """
    derivar = _modulo()._tabelas_de_rls
    assert 'tabela_array' in derivar(_MOLDES['array'])
    assert 'outra_array' in derivar(_MOLDES['array'])
    assert 'tabela_escalar' in derivar(_MOLDES['escalar'])
    assert 'tabela_alter' in derivar(_MOLDES['alter_literal'])
    assert 'tabela_policy' in derivar(_MOLDES['policy_literal'])


def test_a_derivacao_nao_captura_arquivo_sem_rls():
    """O caso negativo é o que impede a correção de virar sobre-captura.

    Uma migration de `drop` que guarda um bloco com `tbl text := 'x'` e não
    menciona RLS não pode entrar no conjunto esperado: entraria como
    `missing_rls` para sempre, um defeito inventado pelo próprio relatório.
    """
    sem_rls = """
        DO $$
        DECLARE
          tbl text := 'tabela_dropada';
        BEGIN
          EXECUTE format('DROP TABLE IF EXISTS public.%I', tbl);
        END $$;
    """
    assert _modulo()._tabelas_de_rls(sem_rls) == set(), \
        'a derivação passou a capturar arquivo que não declara RLS nenhuma'


def test_o_conjunto_de_bootstrap_e_derivado_do_codigo():
    """`known_bootstrap` sai do AST das chamadas, nunca de lista fixa.

    Uma lista literal aqui envelheceria na primeira tabela que alguém
    acrescentasse ao mesmo padrão — e envelheceria em silêncio, que é o modo
    de falhar que esta issue existe para eliminar.
    """
    derivar = _modulo()._tabelas_de_enable_rls
    assert derivar("_enable_rls(conn, 'a', 'b')") == {'a', 'b'}, \
        'a derivação deixou de ler os literais das chamadas a _enable_rls'
    assert derivar("outra_funcao(conn, 'c')") == set(), \
        'a derivação passou a capturar chamada que não é _enable_rls'
    assert derivar("_enable_rls(conn, nome_variavel)") == set(), \
        'argumento não-literal foi derivado — o correto é ele cair em unexpected'


def test_o_script_nao_lista_as_tabelas_de_billing_a_mao():
    """Território da #309. Congelar os nomes aqui esconderia a sexta."""
    script = _script()
    for tabela in ('payment_plans', 'subscription_audit_logs'):
        assert tabela not in script, \
            f'`{tabela}` foi fixada no relatório em vez de derivada do código'


# ═══════════════════════════════════════════════════════════════════════════
# A classificação em três origens — o coração da etapa 2
# ═══════════════════════════════════════════════════════════════════════════

def test_as_tres_origens_de_cobertura_sao_separadas():
    """Declarada, conhecida do bootstrap, e realmente inesperada.

    Os três casos que a etapa 2 precisa provar, sem tocar no PostgreSQL:

    - tabela declarada por migration NÃO é inesperada;
    - tabela conhecida do bootstrap NÃO é inesperada — e também não é
      dobrada dentro de `expected`, senão a dívida da #309 sumiria do
      relatório com o CI verde;
    - uma terceira policy, que ninguém declarou, APARECE em
      `unexpected_policy`.
    """
    classificar = _modulo()._classificar_cobertura
    resultado = classificar(
        declaradas={'declarada'},
        por_bootstrap={'do_bootstrap'},
        ligadas={'declarada', 'do_bootstrap', 'intrusa'},
        com_policy={'declarada', 'do_bootstrap', 'intrusa'},
        presentes={'declarada', 'do_bootstrap', 'intrusa'},
    )
    assert resultado['expected_rls_tables'] == {'declarada'}
    assert resultado['known_bootstrap_rls_tables'] == {'do_bootstrap'}, \
        'a tabela do bootstrap foi dobrada dentro de expected e sumiu como dívida'
    assert resultado['unexpected_policy'] == {'intrusa'}, \
        'a policy não declarada deixou de aparecer como unexpected_policy'
    assert resultado['missing_rls'] == set()
    assert resultado['missing_policy'] == set()


def test_o_quinto_conjunto_pega_o_que_os_outros_quatro_perdem():
    """Apagar declaração E proteção some dos quatro conjuntos de uma vez.

    Os outros quatro só falam de tabelas DECLARADAS. Uma tabela que existe,
    não é declarada por migration nenhuma, não é citada por `_enable_rls` e
    não tem policy não aparece em `expected`, nem em `known_bootstrap`, nem em
    `unexpected` — e como `missing_*` correm sobre `cobertas`, também não
    aparece neles.

    Não é hipótese: a sabotagem da #309 apagou o par de migration e as quatro
    condições da etapa 3 ficaram verdes com cinco tabelas desprotegidas.
    `tables_without_rls` é o único que acende.
    """
    resultado = _modulo()._classificar_cobertura(
        declaradas=set(), por_bootstrap=set(),
        ligadas=set(), com_policy=set(),
        presentes={'orfa'},
    )
    assert resultado['expected_rls_tables'] == set()
    assert resultado['known_bootstrap_rls_tables'] == set()
    assert resultado['unexpected_policy'] == set()
    assert resultado['missing_rls'] == set()
    assert resultado['missing_policy'] == set()
    assert resultado['tables_without_rls'] == {'orfa'}, \
        ('o quinto conjunto deixou de pegar tabela sem RLS — os outros quatro '
         'não pegam este caso, e o gate da etapa 3 volta a ter o buraco')


def test_o_quinto_conjunto_nao_acusa_tabela_protegida():
    """Sem o complemento, o gate da etapa 3 nunca ficaria verde."""
    resultado = _modulo()._classificar_cobertura(
        declaradas={'ok'}, por_bootstrap=set(),
        ligadas={'ok'}, com_policy={'ok'}, presentes={'ok'},
    )
    assert resultado['tables_without_rls'] == set()


def test_a_divida_do_bootstrap_nao_vira_cobertura_legitima():
    """Se `known_bootstrap` fosse dobrado em `expected`, a etapa 3 ficaria cega.

    O gate final exige `known_bootstrap_rls_tables` VAZIO justamente para que
    a #309 seja pré-requisito. Fundir os conjuntos zeraria esse gate sem
    resolver nada — o CI verde com cinco tabelas fora do versionamento, que é
    o verde incompleto que a #275 existe para eliminar.
    """
    resultado = _modulo()._classificar_cobertura(
        declaradas=set(), por_bootstrap={'so_no_bootstrap'},
        ligadas={'so_no_bootstrap'}, com_policy={'so_no_bootstrap'},
        presentes={'so_no_bootstrap'},
    )
    assert resultado['expected_rls_tables'] == set(), \
        'tabela sem migration entrou em expected_rls_tables'
    assert resultado['known_bootstrap_rls_tables'] == {'so_no_bootstrap'}


def test_os_cinco_conjuntos_sao_bloqueantes():
    """O coração da etapa 3: cada conjunto SOZINHO reprova.

    Funcional, não textual — `_problemas_de_cobertura` é pura justamente para
    isto. Um por vez porque juntos escondem o que falta: com os cinco sujos,
    quatro condições vivas e uma morta dão a mesma lista não-vazia.

    Três destes eram diagnóstico na etapa 2, e cada um tem uma sabotagem por
    trás: `unexpected_policy` foi listada corretamente sob um "Nenhum
    problema"; `known_bootstrap_rls_tables` é a #309; `tables_without_rls`
    apareceu quando os outros quatro mediram zero com cinco tabelas nuas.
    """
    reprovar = _modulo()._problemas_de_cobertura

    assert reprovar(_cobertura()) == [], 'problema inventado sobre cobertura limpa'

    for nome in _CINCO:
        achados = reprovar(_cobertura(**{nome: {'x'}}))
        assert len(achados) == 1, \
            f'`{nome}` sozinho produziu {len(achados)} achados, esperado 1'
        assert nome in achados[0], \
            f'o achado de `{nome}` não nomeia o conjunto — quem lê o veredito ' \
            f'não sabe onde olhar'

    todos = reprovar(_cobertura(**{nome: {'x'} for nome in _CINCO}))
    assert len(todos) == len(_CINCO), \
        'os cinco sujos deixaram de ser reportados separadamente'


def test_o_gate_dos_cinco_pega_cada_conjunto_neutralizado():
    """MUTAÇÃO, um conjunto por vez: o gate acima está cego?

    Para cada um dos cinco, a condição é neutralizada no script e o gate
    precisa deixar de ver o achado. Um conjunto que continua "reprovando" com
    a condição morta significa que outra condição o está pegando por acidente
    — e que remover a certa passaria despercebida.
    """
    for nome in _CINCO:
        espaco = _modulo_mutado(f"if cobertura['{nome}']:",
                                f"if False and cobertura['{nome}']:")
        achados = espaco['_problemas_de_cobertura'](_cobertura(**{nome: {'x'}}))
        assert achados == [], \
            (f'com a condição de `{nome}` morta o agregador ainda reprovou: '
             f'`{achados}` — o gate dos cinco não está medindo `{nome}`')


def test_o_gate_dos_cinco_pega_o_agregador_neutralizado():
    """MUTAÇÃO do agregador inteiro: `return []` com conjunto sujo.

    As cinco mutações acima matam uma condição cada. Esta mata a função. Sem
    ela, um refactor que troque o corpo por uma lista vazia — ou que devolva
    cedo — passaria pelos cinco gates individuais sem nenhum deles reclamar do
    caso que interessa: cobertura suja e veredito limpo.
    """
    espaco = _modulo_mutado('    return achados', '    return []')
    for nome in _CINCO:
        achados = espaco['_problemas_de_cobertura'](_cobertura(**{nome: {'x'}}))
        assert achados == [], \
            'MUTACAO NAO APLICOU: o agregador sabotado ainda devolve achados'

    intacto = _modulo()._problemas_de_cobertura
    assert intacto(_cobertura(missing_rls={'x'})) != [], \
        ('o agregador ÍNTEGRO devolveu lista vazia com conjunto sujo — a '
         'sabotagem e o original são indistinguíveis e este gate não prova nada')


def test_nenhum_conjunto_de_defeito_fica_so_no_relatorio():
    """Todo conjunto classificado, menos o de cobertura legítima, reprova.

    Lê as CHAVES que `_problemas_de_cobertura` consome, por AST — não o texto,
    que docstring e comentário satisfariam. Um sexto conjunto acrescentado a
    `_classificar_cobertura` passa a exigir decisão explícita: ou ele bloqueia,
    ou alguém escreve aqui por que não. É a porta pela qual `tables_without_rls`
    quase não entrou.
    """
    modulo = _modulo()
    classificados = set(
        modulo._classificar_cobertura(set(), set(), set(), set(), set()))
    fonte = SCRIPT.read_text(encoding='utf-8')
    alvo = next(no for no in ast.parse(fonte).body
                if isinstance(no, ast.FunctionDef)
                and no.name == '_problemas_de_cobertura')
    consumidas = {
        no.slice.value for no in ast.walk(alvo)
        if isinstance(no, ast.Subscript) and isinstance(no.slice, ast.Constant)
        and isinstance(no.slice.value, str)
    }
    esquecidas = classificados - consumidas - {'expected_rls_tables'}
    assert not esquecidas, \
        (f'{sorted(esquecidas)} são classificados e publicados no relatório mas '
         f'não reprovam: conjunto medido que não bloqueia é o falso verde da '
         f'etapa 2 sobrevivendo à etapa 3')
    assert set(_CINCO) <= consumidas, \
        f'o agregador deixou de consumir {sorted(set(_CINCO) - consumidas)}'


def test_o_veredito_limpo_exige_problemas_vazio():
    """"Nenhum problema" não pode aparecer sobre achado aberto.

    Na etapa 2 a frase vivia dentro de `if not diagnosticos:`, porque havia
    achado que não bloqueava. Esse ramo acabou: os cinco conjuntos reprovam, e
    a única condição da frase limpa é `problemas` vazio.

    Duas correções nasceram deste gate, as duas de evidência: uma mutação
    `if False:` silenciou o bloco com todos os testes verdes, e a sabotagem
    end-to-end imprimiu "Nenhum problema" dez linhas abaixo de uma policy
    intrusa listada corretamente.
    """
    script = _script()
    assert 'diagnostico' not in script.lower(), \
        ('o vocabulário de diagnóstico não-bloqueante voltou ao relatório — na '
         'etapa 3 medir e não reprovar é exatamente o que não pode existir')
    sucesso = script[script.index('if not problemas:'):]
    limpo = sucesso[:sucesso.index('return 0')]
    assert 'Nenhum problema' in limpo, \
        'a frase limpa saiu de dentro do ramo que exige `problemas` vazio'
    assert 'return 1' in sucesso, \
        'o veredito deixou de reprovar quando há problema'


def test_erro_impresso_sem_reprovacao_vira_problema():
    """Invariante da etapa 3: `ERROR:` impresso exige exit code != 0.

    Pura e exercitada nas quatro combinações. O único emissor de hoje já
    alimenta `problemas` pelo mesmo caminho — esta função existe para o `print`
    que ainda não foi escrito.
    """
    invariante = _modulo()._erro_sem_reprovacao
    assert invariante([], []) == [], 'problema inventado sem erro impresso'
    assert invariante([], ['algo']) == [], 'problema inventado sem erro impresso'
    assert invariante(['psql: ERROR: x'], ['algo']) == [], \
        'erro COM problema correspondente foi contado duas vezes'
    solto = invariante(['psql: ERROR: x'], [])
    assert len(solto) == 1 and 'ERROR:' in solto[0], \
        ('`ERROR:` impresso sem problema bloqueante deixou de reprovar — o '
         'relatório sairia 0 mostrando erro na tela')


def test_a_saida_do_relatorio_registra_o_que_imprime():
    """O `_Tee` precisa repassar tudo e reter só as linhas com `ERROR:`.

    Se ele não repassasse, o `| tee` do workflow gravaria um log vazio. Se não
    retivesse, a invariante acima nunca teria insumo e passaria sempre.
    """
    modulo = _modulo()
    destino = io.StringIO()
    saida = modulo._Tee(destino)
    saida.write('linha limpa\n')
    saida.write('psql:arquivo.sql:12: ERROR: relation does not exist\n')
    saida.flush()

    assert 'linha limpa' in destino.getvalue(), \
        'o `_Tee` deixou de repassar para o stdout real: o log do CI ficaria vazio'
    assert 'ERROR' in destino.getvalue(), 'o `_Tee` engoliu a linha de erro'
    assert len(saida.com_erro) == 1, \
        f'o `_Tee` registrou {len(saida.com_erro)} linhas com `ERROR:`, esperado 1'
    assert 'relation does not exist' in saida.com_erro[0]


def test_o_relatorio_instala_o_tee_antes_do_veredito():
    """A captura tem de envolver o corpo e terminar ANTES do veredito.

    Conferir depois de imprimir "Nenhum problema" seria descobrir a contradição
    tarde demais para não publicá-la — mede certo, resume errado, que é o falso
    verde mudado para o rodapé.
    """
    script = _script()
    assert 'redirect_stdout' in script, \
        'o relatório deixou de capturar a própria saída'
    corpo = script[script.index('def _relatorio'):]
    posicao_invariante = corpo.index('_erro_sem_reprovacao')
    posicao_veredito = corpo.index("_titulo('VEREDITO')")
    assert posicao_invariante < posicao_veredito, \
        ('a invariante de `ERROR:` passou a ser conferida depois do veredito — '
         'o relatório imprimiria "Nenhum problema" e sairia 1 embaixo')


def test_o_esperado_e_o_bootstrap_sao_intersectados_com_o_schema_vivo():
    """`user_unit_links` é alvo de RLS numa migration antiga e DROPADO depois.

    Sem a interseção ele apareceria como `missing_rls` para sempre — um
    defeito inventado pelo próprio relatório.

    SUCESSOR de `test_o_esperado_e_intersectado_com_o_schema_vivo`, removido
    na etapa 2. Aquele procurava a string `_rls_esperada() & presentes` na
    fonte; a interseção mudou de lugar (foi para `_classificar_cobertura`) e
    ele passou a reprovar por endereço, não por comportamento. Este exercita
    a função e cobre também o conjunto do bootstrap, que o anterior ignorava.
    """
    resultado = _modulo()._classificar_cobertura(
        declaradas={'existe', 'foi_dropada'}, por_bootstrap={'sumiu_tambem'},
        ligadas={'existe'}, com_policy={'existe'}, presentes={'existe'},
    )
    assert resultado['expected_rls_tables'] == {'existe'}
    assert resultado['known_bootstrap_rls_tables'] == set()
    assert resultado['missing_rls'] == set(), \
        'tabela inexistente virou missing_rls — defeito inventado pelo relatório'


def test_a_mensagem_de_erro_nao_depende_do_comprimento_do_caminho():
    """Em `epi-controle-app` o caminho é mais longo e cortava antes."""
    montar = _modulo()._mensagem_de_falha
    longo = ('psql:/um/caminho/bem/longo/supabase/migrations/x.sql:42: '
             'ERROR:  role "anon" does not exist')
    curto = 'psql:/x.sql:42: ERROR:  role "anon" does not exist'
    assert montar(longo) == montar(curto), \
        'o comprimento do caminho ainda muda a mensagem'
    assert 'linha 42' in montar(longo)
    assert 'role "anon" does not exist' in montar(longo)


def test_o_truncamento_mora_so_na_funcao_pura():
    """Gate do PONTO DE USO, não da ferramenta.

    A primeira versão deste gate exercitava só `_PREFIXO_PSQL.sub` e passava
    com o ponto de impressão revertido para `primeira.strip()[:120]`: a regex
    certa, ignorada. É o mesmo defeito do gate de `ON_ERROR_STOP` da etapa
    anterior — provar que a ferramenta existe não prova que ela é usada.
    """
    script = _script()
    corpo = script[script.index('def _aplicar_sql'):script.index('def main(')]
    assert '_mensagem_de_falha(' in corpo, \
        'o passo deixou de montar a mensagem pela função pura'
    assert '[:120]' not in corpo, \
        'voltou a truncar no ponto de impressão, onde o caminho ainda conta'


# ═══════════════════════════════════════════════════════════════════════════
# RLS de verdade — a asserção que dá sentido à issue
# ═══════════════════════════════════════════════════════════════════════════

def test_a_rls_e_medida_nas_duas_dimensoes():
    """`relrowsecurity` e `pg_policies` são coisas diferentes.

    Tabela com RLS habilitada e NENHUMA policy bloqueia tudo em silêncio — é
    pior do que nenhuma das duas. Contar só policies não distingue os casos.

    As âncoras são a FORMA DA CONSULTA (`c.relrowsecurity`, `FROM pg_policies`)
    e não o token solto: a primeira versão deste gate procurava
    `'relrowsecurity'` e passava por causa do rótulo
    `_titulo('… pg_class.relrowsecurity …')`. Comentário e docstring o
    `_codigo` remove; string literal não pode remover, porque as consultas SQL
    são strings. Contra prosa dentro de string, a defesa é a precisão da
    asserção.
    """
    script = _script()
    assert 'c.relrowsecurity' in script, \
        'o relatório deixou de verificar se a RLS está habilitada'
    assert 'FROM pg_policies' in script, \
        'o relatório deixou de verificar se existem policies'


def test_o_relatorio_publica_conjuntos_e_diferencas():
    """"68/73" não serve para a etapa 2. "quais cinco" serve.

    A âncora é a CHAMADA `_conjunto('chave'`, não o token: `missing_policy`
    também é nome de variável e aparece em mais três linhas, então procurar a
    palavra aprovava um relatório que só imprimisse `len(missing_policy)`.
    """
    script = _script()
    for chave in ('expected_rls_tables', 'known_bootstrap_rls_tables',
                  'tables_with_rls_enabled', 'tables_with_policies',
                  'missing_rls', 'missing_policy', 'unexpected_policy',
                  'tables_without_rls'):
        assert f"_conjunto('{chave}'" in script, \
            f'o relatório deixou de PUBLICAR `{chave}` como conjunto — a etapa '


def test_a_cobertura_de_rls_nao_tem_numero_fixo():
    """Um número fixo envelhece na migration seguinte e vira o mesmo falso verde."""
    script = _script()
    assert '_rls_esperada()' in script, \
        'o conjunto esperado deixou de ser derivado das migrations'
    corpo = script[script.index('def _rls_esperada'):script.index('def _rls_ligada')]
    assert not re.search(r'\b(73|75|7[0-9])\b', corpo), \
        'a cobertura de RLS foi fixada num número em vez de derivada'


# ═══════════════════════════════════════════════════════════════════════════
# A etapa 1 é observacional — e este par de gates diz isso em voz alta
# ═══════════════════════════════════════════════════════════════════════════

def test_o_passo_de_migrations_bloqueia():
    """O simétrico que o gate transitório da etapa 1 encomendou.

    Ele afirmava `continue-on-error: true` PRESENTE, para que ninguém
    adiantasse a etapa 3 antes de a etapa 2 zerar os defeitos reais. Zeraram;
    a #309 fechou a última; o gate inverte.

    Afirmar ausência aqui é seguro porque a fatia é do passo, não do arquivo:
    `_passo` delimita por indentação, e o `continue-on-error` do Ruff — que
    permanece — vive fora dela.
    """
    assert 'continue-on-error' not in _passo_de_migrations(), \
        ('o passo de migrations voltou a ser não-bloqueante: a etapa 3 da #275 '
         'existe para remover exatamente esta linha')


def test_o_script_tem_exit_code_real_desde_a_etapa_1():
    """Quem segura o job é o workflow, não uma mentira dentro do script.

    O passo antigo saía `0` sempre — o `$?` de cada `psql` era só ecoado no
    log e o script terminava em `cat … || true`. Era por isso que remover o
    `continue-on-error` sozinho não teria consertado nada. Aqui o código de
    saída é real desde já, e a etapa 3 vira literalmente remover uma linha.
    """
    script = _script()
    assert 'return 1' in script and 'return 0' in script, \
        'o relatório deixou de distinguir sucesso de falha no código de saída'
    assert 'SystemExit(main())' in script, \
        'o código de saída do relatório deixou de chegar ao processo'


def test_o_passo_declara_euo_pipefail():
    """Leitura do texto. Sozinha não prova nada — ver o gate seguinte.

    A versão da etapa 1 era condicional (`if '|' in passo`). Passo sem pipe
    passava sem asserção nenhuma, o que é uma forma silenciosa de gate
    desligado. Aqui é incondicional: o passo TEM pipe e precisa do `pipefail`.
    """
    passo = _passo_de_migrations()
    assert '| tee' in passo, \
        'o passo deixou de canalizar a saída — este gate perdeu o objeto'
    assert 'set -euo pipefail' in passo, \
        ('o passo canaliza a saída sem `set -euo pipefail`: o exit code do '
         'relatório é descartado e remover o `continue-on-error` não teria '
         'efeito nenhum')


def test_o_pipe_do_passo_preserva_exit_code_de_verdade(tmp_path):
    """SABOTAGEM REAL: roda a pipeline do passo com um relatório que sai 1.

    Presença textual de `set -euo pipefail` prova que a linha existe, não que
    ela funciona. Este gate executa o `run:` EXTRAÍDO DO WORKFLOW, trocando só
    a chamada do relatório por um processo que sai 1, e exige que o passo
    inteiro saia diferente de zero.

    O controle é a metade que importa: sem `pipefail`, o mesmo script precisa
    sair 0. Se saísse != 0 nos dois casos, o gate estaria medindo outra coisa e
    aprovaria um passo sem `pipefail`.

    Foi este defeito, uma camada acima, que quase passou na etapa 1: a primeira
    execução reportou `success` num passo cujo script saiu 1.
    """
    original = _run_do_passo()
    reprovando = original.replace(
        'python scripts/ci_migrations_report.py',
        "python3 -c 'import sys; print(\"reprovando\"); sys.exit(1)'")
    assert reprovando != original, \
        'MUTACAO NAO APLICOU: a chamada do relatório mudou de forma no workflow'
    reprovando = reprovando.replace('/tmp/mig-logs', str(tmp_path / 'logs'))

    com = subprocess.run(['bash', '-c', reprovando],
                         capture_output=True, text=True)
    assert com.returncode != 0, \
        (f'o passo saiu {com.returncode} com o relatório reprovando: o `tee` '
         f'está engolindo o exit code e o job ficaria verde')

    sem = reprovando.replace('set -euo pipefail', 'set -eu')
    assert sem != reprovando, 'MUTACAO NAO APLICOU: `set -euo pipefail` mudou de forma'
    controle = subprocess.run(['bash', '-c', sem], capture_output=True, text=True)
    assert controle.returncode == 0, \
        (f'sem `pipefail` o passo saiu {controle.returncode}, não 0: a '
         f'sabotagem não distingue os dois casos e este gate não prova nada')


def test_o_continue_on_error_do_ruff_nao_foi_tocado():
    """Território da #948. Sobrou UM, e o gate diz ONDE — não quantos.

    Contagem sozinha aprova a troca: remover o do Ruff e devolver o das
    migrations mantém o total em 1 e desfaz a etapa 3 inteira. É a mesma lição
    de medir o ponto de chamada em vez da existência da ferramenta, que já
    custou dois gates cegos nesta frente.
    """
    workflow = _workflow()
    assert workflow.count('continue-on-error: true') == 1, \
        ('o número de `continue-on-error` no workflow mudou — a etapa 3 deixa '
         'exatamente um, o do Ruff')
    assert 'continue-on-error: true' in _passo_do_ruff(), \
        ('o `continue-on-error` sobrevivente não é o do Ruff — ele é da fase 2 '
         'da #948 e não pode ser trocado pelo das migrations')
