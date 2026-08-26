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


def _workflow() -> str:
    return _yaml_sem_comentarios(WORKFLOW.read_text(encoding='utf-8'))


def _passo_de_migrations() -> str:
    """Só o passo da #275 — o job tem outros, e outro `continue-on-error`."""
    texto = _workflow()
    inicio = texto.index('Migrations — relatório observacional')
    fim = texto.index('- name: Upload migration log', inicio)
    return texto[inicio:fim]


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
    for chave in ('expected_rls_tables', 'tables_with_rls_enabled',
                  'tables_with_policies', 'missing_rls', 'missing_policy',
                  'unexpected_policy'):
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


def test_o_esperado_e_intersectado_com_o_schema_vivo():
    """`user_unit_links` é alvo de RLS numa migration antiga e DROPADO por outra.

    Sem a interseção ele apareceria como `missing_rls` para sempre — um
    defeito inventado pelo próprio relatório.
    """
    script = _script()
    assert '_rls_esperada() & presentes' in script, \
        'o conjunto esperado deixou de ser intersectado com as tabelas que existem'


# ═══════════════════════════════════════════════════════════════════════════
# A etapa 1 é observacional — e este par de gates diz isso em voz alta
# ═══════════════════════════════════════════════════════════════════════════

def test_a_etapa_1_ainda_nao_bloqueia():
    """Gate TRANSITÓRIO da etapa observacional da #275.

    DEVE SER SUBSTITUÍDO NA ETAPA 3 pelo simétrico — o que exige o
    `continue-on-error` **ausente**. Ele existe para que ninguém adiante a
    etapa 3 antes de a etapa 2 zerar os defeitos reais, e não para registrar
    o `continue-on-error` como requisito permanente.
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


def test_o_continue_on_error_do_ruff_nao_foi_tocado():
    """Território da #948. Uma busca por `continue-on-error` acha os dois."""
    workflow = _workflow()
    assert workflow.count('continue-on-error: true') == 2, \
        ('o número de `continue-on-error` mudou — o do Ruff é da fase 2 da '
         '#948 e não deve ser removido junto com o das migrations')
