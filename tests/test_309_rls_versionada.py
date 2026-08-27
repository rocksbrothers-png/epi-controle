"""A RLS mora em migration versionada, e em nenhum outro lugar — #309.

Cinco tabelas de billing recebiam `ENABLE ROW LEVEL SECURITY` e a policy
`block_direct_api_access` de `modules/payments/service.py`, pelo helper
`_enable_rls`. As duas funções que o chamavam estão em `_ensure_fns`
(`core/bootstrap.py`), então rodavam em todo boot: a proteção existia em
produção e o defeito nunca foi ausência de RLS.

O defeito era de RASTREABILIDADE. Aquele DDL não entrava em `app_migrations`,
não tinha ordem declarada, e era invisível a qualquer gate derivado de
migrations — o relatório da #275 acusava as cinco como `unexpected_policy`, o
CI chamando de intrusa uma policy que o próprio bootstrap criava.

Estes gates impedem a volta. Leitura sempre por `_codigo`: o comentário que
explica a mudança em `modules/payments/service.py` cita as duas expressões
proibidas, e um gate que lesse prosa reprovaria a própria documentação da
correção — além de poder ser satisfeito por comentário, que é o defeito que a
Fase 1 da #271 corrigiu em três gates.

SUCESSOR de `tests/test_payments_rls_hardening.py`, removido nesta issue.
Aquele arquivo existia inteiramente para exercitar `_enable_rls` — cinco
testes sobre um helper que deixou de existir. As propriedades que ele
guardava continuam guardadas aqui, uma a uma:

    alterava a tabela e criava policy    → test_a_migration_declara_as_cinco…
                                            + test_o_enable_e_a_policy_ficam…
    policy RESTRICTIVE negando anon      → test_a_policy_e_restritiva_e_nega…
    criação guardada por pg_policies     → test_a_migration_e_idempotente…
    cobria as cinco tabelas              → test_a_migration_declara_as_cinco…
    engolia erro sob SQLite              → test_a_migration_nao_engole_erro,
                                            com o sinal INVERTIDO de propósito

A última mudou de sentido, e é a única que muda: o helper PRECISAVA engolir
exceção porque rodava sob SQLite. A migration não roda sob SQLite
(`run_pending_migrations` devolve `skipped_sqlite`), então engolir deixou de
ser necessário — e passou a ser proibido.
"""

import ast
import io
import pathlib
import tokenize

RAIZ = pathlib.Path(__file__).resolve().parent.parent

#: Onde DDL de RLS é PROIBIDO. As migrations ficam de fora de propósito: é lá
#: que ele deve morar.
TERRITORIO_PROIBIDO = ('modules', 'core')
ARQUIVOS_PROIBIDOS = ('app.py',)

#: As duas expressões que criam ou habilitam RLS. Não há terceira forma em
#: PostgreSQL: RLS se liga com `ALTER TABLE … ENABLE ROW LEVEL SECURITY` e
#: policy se cria com `CREATE POLICY`.
DDL_DE_RLS = ('ENABLE ROW LEVEL SECURITY', 'CREATE POLICY')

MIGRACAO_SQL = RAIZ / 'supabase' / 'migrations' / '20260827000000_billing_rls.sql'
MIGRACAO_PY = RAIZ / 'epi_backend' / 'migrations' / '028_billing_rls.py'

TABELAS_DE_BILLING = (
    'payments', 'payment_plans', 'subscriptions',
    'invoices', 'subscription_audit_logs',
)


def _codigo(fonte: str) -> str:
    """Fonte Python sem comentários **e sem docstrings**, via `ast` + `tokenize`.

    (Mesmo helper de `test_275_ci_de_migrations.py`, seguindo o idioma do
    repositório. A convergência num módulo compartilhado é dívida em #948.)
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


def _sql_sem_comentarios(fonte: str) -> str:
    """`.sql` sem as linhas `--`.

    O cabeçalho da migration explica por que o `ENABLE` e a policy ficam no
    mesmo `DO $$`, e para explicar precisa CITAR as duas expressões. Um gate
    que lesse o arquivo cru contaria a citação como se fosse código — foi
    exatamente o que aconteceu na primeira execução deste teste.
    """
    return '\n'.join(
        linha.split('--')[0] if not linha.lstrip().startswith('--') else ''
        for linha in fonte.split('\n')
    )


def _sql() -> str:
    return _sql_sem_comentarios(MIGRACAO_SQL.read_text(encoding='utf-8'))


def _fontes_de_aplicacao():
    """Todo `.py` de aplicação, fora das migrations."""
    for base in TERRITORIO_PROIBIDO:
        for caminho in sorted((RAIZ / base).rglob('*.py')):
            if '__pycache__' in caminho.parts:
                continue
            yield caminho
    for nome in ARQUIVOS_PROIBIDOS:
        caminho = RAIZ / nome
        if caminho.exists():
            yield caminho


# ═══════════════════════════════════════════════════════════════════════════
# O gate estático — nenhum DDL de RLS fora de migrations/
# ═══════════════════════════════════════════════════════════════════════════

def test_nenhum_ddl_de_rls_em_modules_core_ou_app():
    """RLS aplicada por código de aplicação é invisível a gate de schema.

    Não é hipótese: era assim que as cinco tabelas de billing ficavam de fora
    da derivação da #275, e a única saída era um conjunto próprio para elas
    (`known_bootstrap_rls_tables`). Com este gate, a classe inteira morre —
    não há mais como acrescentar a sexta.
    """
    infratores = []
    for caminho in _fontes_de_aplicacao():
        codigo = _codigo(caminho.read_text(encoding='utf-8'))
        for expressao in DDL_DE_RLS:
            if expressao in codigo:
                infratores.append(f'{caminho.relative_to(RAIZ)} → {expressao}')
    assert infratores == [], (
        'DDL de RLS fora de `migrations/` — isto é invisível a qualquer gate '
        f'derivado de migrations (#309): {infratores}'
    )


def test_o_helper_enable_rls_nao_voltou():
    """`_enable_rls` era o mecanismo, e o gate acima pega o DDL dentro dele.

    Este pega o mecanismo mesmo que alguém o reescreva chamando o DDL de outro
    jeito — por concatenação, por exemplo, que escaparia da busca por
    expressão literal.
    """
    infratores = [
        str(caminho.relative_to(RAIZ))
        for caminho in _fontes_de_aplicacao()
        if '_enable_rls' in _codigo(caminho.read_text(encoding='utf-8'))
    ]
    assert infratores == [], \
        f'`_enable_rls` voltou ao código de aplicação (#309): {infratores}'


# ═══════════════════════════════════════════════════════════════════════════
# A migration que substituiu o bootstrap
# ═══════════════════════════════════════════════════════════════════════════

def test_a_migration_declara_as_cinco_tabelas():
    """Remover o bootstrap sem a migration deixaria as cinco desprotegidas."""
    sql = _sql()
    for tabela in TABELAS_DE_BILLING:
        assert f"'{tabela}'" in sql, \
            f'`{tabela}` saiu da migration de RLS — a tabela fica sem proteção'


def test_o_enable_e_a_policy_ficam_no_mesmo_bloco_do():
    """O que torna "RLS ligada sem policy" INALCANÇÁVEL nesta migration.

    `20260712120000_tenant_domains_owner_2fa.sql` faz `ALTER TABLE … ENABLE`
    na linha 52 e `CREATE POLICY` na 54 — duas instruções soltas. Quando a
    segunda falhou, o autocommit já tinha gravado a primeira e a tabela ficou
    com RLS ligada e zero policy, que nega tudo em silêncio. Foi assim que a
    etapa 1 da #275 encontrou o caso.

    Dentro de um `DO $$` o conjunto é UMA instrução: se a policy falha, o
    bloco inteiro reverte e o `ENABLE` vai junto.
    """
    sql = _sql()
    corpo = sql[sql.index('DO $$'):sql.index('END $$;')]
    for expressao in DDL_DE_RLS:
        assert expressao in corpo, \
            (f'`{expressao}` saiu do bloco `DO $$` — fora dele o autocommit '
             'pode deixar RLS ligada sem policy')
    assert sql.count('DO $$') == 1, \
        'mais de um bloco `DO $$`: a atomicidade deixa de valer entre eles'


def test_a_policy_e_restritiva_e_nega_anon_e_authenticated():
    """A cláusula, não só o nome da policy.

    O Supabase Security Advisor sinaliza `rls_enabled_no_policy`: RLS ligada
    sem policy fica num estado ambíguo, e a policy formaliza a intenção. O
    backend conecta como dono (`postgres`) e ignora RLS sem `FORCE`, então
    negar `anon`/`authenticated` não afeta a aplicação — afeta o PostgREST,
    que é exatamente quem não deve ler estas tabelas.
    """
    sql = _sql()
    assert 'AS RESTRICTIVE FOR ALL TO anon, authenticated USING (false)' in sql, \
        ('a policy deixou de ser RESTRICTIVE negando anon/authenticated — '
         'uma policy PERMISSIVE aqui LIBERARIA o que deveria bloquear')
    assert 'block_direct_api_access' in sql, \
        'o nome da policy mudou; o guarda por pg_policies deixa de casar'


def test_a_migration_nao_engole_erro():
    """O helper antigo engolia exceção; a migration não pode herdar isso.

    `_enable_rls` envolvia cada `execute` em `try/except Exception` com
    rollback silencioso, porque o SQLite dos testes não suporta RLS. O efeito
    colateral era que uma falha REAL de `CREATE POLICY` em PostgreSQL passava
    despercebida no boot.

    Como migration, o problema desaparece na origem:
    `run_pending_migrations` devolve `skipped_sqlite` e nem chega a rodar sob
    SQLite. Não há mais motivo para engolir nada — e engolir voltaria a
    esconder falha de RLS em produção.
    """
    modulo = _codigo(MIGRACAO_PY.read_text(encoding='utf-8'))
    assert 'except' not in modulo, \
        ('o par Python passou a engolir exceção — falha de RLS volta a '
         'passar despercebida, que era o defeito do `_enable_rls`')


def test_a_migration_e_idempotente_por_construcao():
    """Upgrade sobre banco provisionado precisa ser no-op, não erro."""
    sql = _sql()
    assert 'CONTINUE WHEN NOT EXISTS' in sql, \
        'a migration deixou de tolerar tabela ainda inexistente'
    assert 'IF NOT EXISTS (' in sql and 'pg_policies' in sql, \
        'a migration deixou de guardar a criação da policy por pg_policies'


def test_o_par_python_aponta_para_o_sql():
    """A trilha operacional aplica o MESMO arquivo — ADR-0005, sem segunda fonte."""
    modulo = _codigo(MIGRACAO_PY.read_text(encoding='utf-8'))
    assert "MIGRATION_ID = '028_billing_rls'" in modulo
    assert MIGRACAO_SQL.name in modulo, \
        'o módulo Python deixou de apontar para o .sql pareado'
    assert 'CREATE POLICY' not in modulo, \
        'o módulo Python passou a ter DDL próprio em vez de aplicar o .sql'
