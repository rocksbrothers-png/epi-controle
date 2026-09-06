"""Gates da #332 contra PostgreSQL real — memo positivo de catálogo.

O que só o banco pode responder: se o memo mantém a coerência dentro de um
mesmo bootstrap, se ele sobrevive a uma alteração feita por OUTRA conexão, e
se a validação pós-`ALTER` de `_safe_add_column` continua consultando o banco
em vez de confirmar o próprio memo.

Esse último ponto é o que separa o desenho adotado — invalidar a entrada da
tabela depois do `ALTER` — da alternativa óbvia de remendar o memo com a coluna
nova. Remendar faria a validação passar sozinha, e ela deixaria de valer.

A concorrência não é cenário de laboratório: `db.init_lock_not_acquired` deixa
dois bootstraps correrem em paralelo contra o mesmo banco, e é exatamente aí
que um cache que respondesse "não existe" mandaria alterar schema com
informação envelhecida.
"""

import os
import sys
from contextlib import closing

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import schema
from core.database import get_connection
from epi_backend import db as epi_db

pytestmark = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL', '').startswith('postgres'),
    reason='Exige DATABASE_URL apontando para PostgreSQL real.',
)

PREFIXO = 't332_'


class ContaAlter:
    """Proxy que conta `ALTER TABLE` e delega o resto à conexão real.

    Contar é a única forma de distinguir "não emitiu o ALTER" de "emitiu e o
    banco recusou": `_safe_add_column` engole o erro de coluna duplicada e
    volta em silêncio, então a ausência de exceção não prova nada.
    """

    def __init__(self, real, engolir_alter=False):
        object.__setattr__(self, '_real', real)
        object.__setattr__(self, '_alters', [])
        object.__setattr__(self, '_engolir', engolir_alter)

    @property
    def alters(self):
        return object.__getattribute__(self, '_alters')

    def execute(self, sql, params=None):
        real = object.__getattribute__(self, '_real')
        if 'ALTER TABLE' in str(sql).upper() and 'ADD COLUMN' in str(sql).upper():
            object.__getattribute__(self, '_alters').append(str(sql))
            if object.__getattribute__(self, '_engolir'):
                return real.execute('SELECT 1')
        return real.execute(sql, params) if params is not None else real.execute(sql)

    def __getattr__(self, nome):
        return getattr(object.__getattribute__(self, '_real'), nome)


def _limpar(conexao):
    linhas = conexao.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = current_schema() AND table_name LIKE ?",
        (PREFIXO + '%',),
    ).fetchall()
    for linha in linhas:
        nome = linha['table_name'] if hasattr(linha, 'keys') else linha[0]
        conexao.execute(f'DROP TABLE IF EXISTS {nome} CASCADE')
    conexao.commit()


@pytest.fixture()
def conexao():
    with closing(get_connection()) as con:
        _limpar(con)
        try:
            yield con
        finally:
            _limpar(con)


def _colunas_reais(conexao, tabela):
    linhas = conexao.execute(
        'SELECT column_name FROM information_schema.columns WHERE table_name = ?',
        (tabela,),
    ).fetchall()
    return {(l['column_name'] if hasattr(l, 'keys') else l[0]) for l in linhas}


# ── Gate 2 ───────────────────────────────────────────────────────────────────

def test_gate_2_coluna_criada_no_bootstrap_entra_no_memo_por_leitura_viva(conexao):
    conexao.execute(f'CREATE TABLE {PREFIXO}alvo (id INTEGER)')
    conexao.commit()

    epi_db.abrir_memo_catalogo(conexao)
    try:
        schema._safe_add_column(conexao, f'{PREFIXO}alvo', 'nova', 'TEXT')

        assert 'nova' in _colunas_reais(conexao, f'{PREFIXO}alvo')
        assert epi_db.column_exists(conexao, f'{PREFIXO}alvo', 'nova') is True

        # A entrada foi invalidada logo após o ALTER; conter 'nova' agora só é
        # possível se a validação pós-migração releu o catálogo de verdade.
        memo = epi_db._catalogo_memo(conexao)
        assert 'nova' in memo[f'{PREFIXO}alvo']
    finally:
        epi_db.fechar_memo_catalogo(conexao)


# ── Gate 3 ───────────────────────────────────────────────────────────────────

def test_gate_3_tabela_criada_no_bootstrap_nao_deixa_snapshot_obsoleto(conexao):
    epi_db.abrir_memo_catalogo(conexao)
    try:
        assert epi_db.table_exists(conexao, f'{PREFIXO}tardia') is False
        assert epi_db.table_columns(conexao, f'{PREFIXO}tardia') == set()

        conexao.execute(f'CREATE TABLE {PREFIXO}tardia (id INTEGER, nome TEXT)')
        conexao.commit()

        assert epi_db.table_exists(conexao, f'{PREFIXO}tardia') is True
        assert epi_db.column_exists(conexao, f'{PREFIXO}tardia', 'nome') is True
    finally:
        epi_db.fechar_memo_catalogo(conexao)


# ── Gates 12 e 14 ────────────────────────────────────────────────────────────

def test_gate_14_coluna_criada_por_outra_conexao_nao_gera_alter_duplicado(conexao):
    conexao.execute(f'CREATE TABLE {PREFIXO}conc (id INTEGER, ja_existia TEXT)')
    conexao.commit()

    contador = ContaAlter(conexao)
    epi_db.abrir_memo_catalogo(contador)
    try:
        # Memoriza a tabela pelo caminho normal do bootstrap.
        schema._safe_add_column(contador, f'{PREFIXO}conc', 'ja_existia', 'TEXT')
        assert contador.alters == []

        # Outro bootstrap, em paralelo, adiciona uma coluna que o memo não viu.
        with closing(get_connection()) as outra:
            outra.execute(f'ALTER TABLE {PREFIXO}conc ADD COLUMN externa TEXT')
            outra.commit()

        schema._safe_add_column(contador, f'{PREFIXO}conc', 'externa', 'TEXT')
        assert contador.alters == [], (
            'a coluna já existia no banco: o memo respondeu por um retrato '
            'velho e mandou emitir ALTER'
        )
    finally:
        epi_db.fechar_memo_catalogo(contador)


# ── Gate 15 ──────────────────────────────────────────────────────────────────

def test_gate_15_postcondition_falha_quando_o_alter_nao_teve_efeito(conexao):
    conexao.execute(f'CREATE TABLE {PREFIXO}post (id INTEGER)')
    conexao.commit()

    engole = ContaAlter(conexao, engolir_alter=True)
    epi_db.abrir_memo_catalogo(engole)
    try:
        with pytest.raises(schema.SchemaMigrationError) as erro:
            schema._safe_add_column(engole, f'{PREFIXO}post', 'fantasma', 'TEXT')
        # A asserção é sobre a MENSAGEM, não sobre `kind`: o `raise` interno da
        # validação pós-migração é reembrulhado pelo `except Exception` de
        # `_safe_add_column`, então `kind` chega como `driver_unexpected` e o
        # valor `column_missing_after_migration` é inalcançável. Isso é
        # comportamento PRÉ-EXISTENTE, verificado em `origin/main`, e não se
        # corrige aqui: mexer nele alteraria o contrato de erro que a #307
        # trata.
        assert 'não encontrada após ALTER TABLE' in str(erro.value)
        assert erro.value.context['table'] == f'{PREFIXO}post'
        assert engole.alters, 'o ALTER precisa ter sido tentado'
    finally:
        epi_db.fechar_memo_catalogo(engole)


def test_gate_15_sabotagem_remendar_o_memo_engana_a_postcondition(conexao, monkeypatch):
    """A alternativa REJEITADA no contrato: em vez de invalidar, gravar a coluna
    no memo depois do ALTER. Se ela passasse, a validação pós-migração estaria
    confirmando o próprio memo em vez do banco."""
    conexao.execute(f'CREATE TABLE {PREFIXO}sab (id INTEGER)')
    conexao.commit()

    def _remendar(connection, table):
        memo = epi_db._catalogo_memo(connection)
        if memo is not None:
            memo[str(table)] = frozenset(memo.get(str(table), set()) | {'fantasma'})

    monkeypatch.setattr(schema, '_invalidar_memo_catalogo', _remendar)

    engole = ContaAlter(conexao, engolir_alter=True)
    epi_db.abrir_memo_catalogo(engole)
    try:
        schema._safe_add_column(engole, f'{PREFIXO}sab', 'fantasma', 'TEXT')
    finally:
        epi_db.fechar_memo_catalogo(engole)

    assert 'fantasma' not in _colunas_reais(conexao, f'{PREFIXO}sab'), (
        'a sabotagem precisa deixar o banco SEM a coluna e ainda assim passar — '
        'é isso que prova que invalidar, e não remendar, é o que mantém a '
        'postcondition honesta'
    )


# ── Gate 9 ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize('com_memo', [False, True])
def test_gate_9_contrato_de_erro_de_migracao_intacto(conexao, com_memo):
    if com_memo:
        epi_db.abrir_memo_catalogo(conexao)
    try:
        with pytest.raises(schema.SchemaMigrationError) as erro:
            schema._safe_add_column(conexao, f'{PREFIXO}nao_existe', 'x', 'TEXT')
        assert erro.value.kind == 'schema_missing_table'
        assert erro.value.context['table'] == f'{PREFIXO}nao_existe'
        assert erro.value.context['phase'] == 'migration'
    finally:
        if com_memo:
            epi_db.fechar_memo_catalogo(conexao)


# ── Gate 1 ───────────────────────────────────────────────────────────────────

def test_gate_1_bootstrap_completo_produz_o_mesmo_schema_com_e_sem_memo(monkeypatch):
    """`init_db()` inteiro, duas vezes, comparando o catálogo resultante.

    É o gate que responde "o memo mudou alguma coisa?" da única forma que
    interessa: pelo schema que o banco fica tendo. Roda o caminho de produção
    (memo ligado) e depois o mesmo bootstrap com o memo recusado, e exige
    igualdade exata de tabelas e colunas.
    """
    from core import bootstrap as core_bootstrap

    def _fotografar():
        with closing(get_connection()) as con:
            linhas = con.execute(
                'SELECT table_name, column_name FROM information_schema.columns '
                'WHERE table_schema = current_schema()'
            ).fetchall()
            return {
                (
                    (l['table_name'] if hasattr(l, 'keys') else l[0]),
                    (l['column_name'] if hasattr(l, 'keys') else l[1]),
                )
                for l in linhas
            }

    core_bootstrap.init_db()
    com_memo = _fotografar()

    monkeypatch.setattr(epi_db, 'abrir_memo_catalogo', lambda conexao: False)
    core_bootstrap.init_db()
    sem_memo = _fotografar()

    assert com_memo == sem_memo
    assert len(com_memo) > 100, 'fotografia vazia tornaria a comparação vacuosa'
