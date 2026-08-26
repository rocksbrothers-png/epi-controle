"""O CI de migrations prova as duas trilhas — #275, etapa 1.

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
"""

import ast
import importlib.util
import io
import pathlib
import re
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


def _passo_de_migrations() -> str:
    """Só o passo da #275 — o job tem outros, e outro `continue-on-error`."""
    texto = _workflow()
    inicio = texto.index('Migrations — relatório observacional')
    fim = texto.index('- name: Upload migration log', inicio)
    return texto[inicio:fim]


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
        < texto.index('Migrations — relatório observacional'), \
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


def test_o_diagnostico_nomeia_os_dois_achados_nao_bloqueantes():
    """A lista de diagnósticos, exercitada nas quatro combinações.

    Gate da POPULAÇÃO, não do consumo. A versão anterior só verificava que a
    frase limpa vivia dentro de `if not diagnosticos:` — e esvaziar a lista
    na origem tornava essa condição trivialmente verdadeira, com os 27 testes
    passando. Duas mutações escaparam exatamente assim.
    """
    montar = _modulo()._diagnosticos
    assert montar(set(), set()) == [], 'diagnóstico inventado sem achado nenhum'

    so_bootstrap = montar({'a'}, set())
    assert len(so_bootstrap) == 1
    assert 'known_bootstrap_rls_tables' in so_bootstrap[0], \
        'o achado de RLS fora de migration deixou de ser nomeado'

    so_intrusa = montar(set(), {'b'})
    assert len(so_intrusa) == 1
    assert 'unexpected_policy' in so_intrusa[0], \
        'a policy não declarada deixou de ser nomeada no diagnóstico'

    assert len(montar({'a'}, {'b'})) == 2, \
        'os dois achados juntos deixaram de ser reportados separadamente'


def test_o_veredito_de_sucesso_nao_engole_a_divida():
    """"Nenhum problema" não pode ser a última palavra havendo achado aberto.

    O `_conjunto` já é gatilhado, mas imprime no meio de um relatório de 800
    linhas. Quem lê só o fim sai com "tudo certo" — e a etapa 3 depende de
    alguém lembrar que a dívida existe.

    Duas correções nasceram aqui, e as duas de evidência, não de revisão:

    1. Uma mutação escapou: trocar a condição por `if False:` silenciava o
       bloco com os 26 testes passando.
    2. A sabotagem end-to-end plantou uma policy que ninguém declara. O
       relatório a listou corretamente em `unexpected_policy` e o veredito
       imprimiu "Nenhum problema" dez linhas abaixo. Medir certo e resumir
       errado é o mesmo falso verde, mudado de lugar.

    Por isso a frase limpa agora vive DENTRO do ramo `if not diagnosticos:`,
    e o exit code continua 0 — diagnóstico não bloqueia na etapa 2.
    """
    script = _script()
    sucesso = script[script.index('if not problemas:'):]
    assert 'if not diagnosticos:' in sucesso, \
        ('a frase limpa do veredito deixou de ser condicionada aos '
         'diagnósticos — ela pode voltar a aparecer sobre achado aberto')
    limpo = sucesso[sucesso.index('if not diagnosticos:'):]
    limpo = limpo[:limpo.index('return 0')]
    assert 'Nenhum problema' in limpo, \
        'a frase limpa saiu de dentro do ramo que exige diagnóstico vazio'
    assert 'known_bootstrap_rls_tables' in sucesso, \
        'o veredito deixou de nomear o conjunto onde a dívida está listada'
    assert 'unexpected_policy' in sucesso, \
        'o veredito deixou de nomear as policies não declaradas'


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
                  'missing_rls', 'missing_policy', 'unexpected_policy'):
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

def test_a_etapa_1_ainda_nao_bloqueia():
    """Gate TRANSITÓRIO da etapa observacional da #275.

    DEVE SER SUBSTITUÍDO NA ETAPA 3 pelo simétrico — o que exige o
    `continue-on-error` **ausente**. Ele existe para que ninguém adiante a
    etapa 3 antes de a etapa 2 zerar os defeitos reais, e não para registrar
    o `continue-on-error` como requisito permanente.

    QUANDO A ETAPA 3 CHEGAR, o gate bloqueante exige QUATRO condições:

        missing_rls                = 0
        missing_policy             = 0
        unexpected_policy          = 0
        known_bootstrap_rls_tables = 0   ← não esquecer esta

    A quarta é o que acopla a #309 ao gate final. Sem ela o CI ficaria
    totalmente verde mantendo cinco tabelas cuja RLS segue fora do
    versionamento de migrations — exatamente o verde incompleto que a #275
    existe para eliminar. Ela não some do relatório na etapa 2: aparece em
    conjunto próprio e é repetida no VEREDITO, marcada como diagnóstico.
    """
    assert 'continue-on-error: true' in _passo_de_migrations(), \
        ('o passo de migrations passou a bloquear antes da etapa 2 — se isto '
         'é intencional, é a etapa 3, e este gate deve ser invertido')


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


def test_o_exit_code_do_relatorio_sobrevive_ao_pipe():
    """O `| tee` do passo devolveria 0 mesmo com o relatório reprovando.

    O shell padrão do Actions é `bash -e {0}`, e numa pipeline o status é o do
    ÚLTIMO comando. Sem `set -o pipefail`, o `tee` mascara o código de saída —
    e a etapa 3 removeria o `continue-on-error` para descobrir que o job
    continua verde. É o defeito do passo antigo (`$?` ecoado, `cat … || true`)
    reproduzido uma camada acima, e foi assim que ele apareceu: a primeira
    execução da etapa 1 reportou `success` num passo cujo script saiu 1.
    """
    passo = _passo_de_migrations()
    if '|' in passo:
        assert 'set -o pipefail' in passo, \
            ('o passo canaliza a saída sem `pipefail`: o exit code do '
             'relatório é descartado e a etapa 3 não teria efeito')


def test_o_continue_on_error_do_ruff_nao_foi_tocado():
    """Território da #948. Uma busca por `continue-on-error` acha os dois."""
    workflow = _workflow()
    assert workflow.count('continue-on-error: true') == 2, \
        ('o número de `continue-on-error` mudou — o do Ruff é da fase 2 da '
         '#948 e não deve ser removido junto com o das migrations')
