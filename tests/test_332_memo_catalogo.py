"""Gates da #332 — memo positivo de catálogo do bootstrap.

O bootstrap corporativo levou 164,02 s medidos em produção, e a decomposição
mostrou que o tempo não está em nenhuma migration cara: está em ~558 consultas
a `information_schema` por partida — duas por coluna verificada, 279 colunas —
que em regime estacionário não produzem DDL nenhum, porque o schema já está
correto.

O memo corta essas repetições. Estes gates existem porque a otimização óbvia
seria também a perigosa: um cache que responde "essa coluna não existe" a
partir de um retrato tirado segundos antes mandaria emitir
`ALTER TABLE ADD COLUMN` com informação envelhecida — e isso não é hipotético,
porque `db.init_lock_not_acquired` deixa dois bootstraps correrem em paralelo
contra o mesmo banco.

Daí a regra assimétrica que estes gates travam: **só a presença conhecida
encurta caminho; só a consulta viva pode dizer `False`.**

Os gates de comportamento contra PostgreSQL real — coerência intra-bootstrap,
concorrência com segunda conexão e a postcondition do `ALTER` — vivem em
`tests_postgres/test_332_memo_catalogo_postgres.py`: a propriedade deles é o
que o banco faz, e isso se mede consultando.
"""

import ast
import os
import pathlib
import re
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import schema
from core.bootstrap import _memo_catalogo_do_bootstrap
from epi_backend import db as epi_db

RAIZ = pathlib.Path(__file__).resolve().parent.parent
TETO_DE_CONSULTAS = 60


# ── Portadores de mentira ────────────────────────────────────────────────────

class _Resultado:
    def __init__(self, linhas):
        self._linhas = list(linhas)

    def fetchall(self):
        return list(self._linhas)

    def fetchone(self):
        return self._linhas[0] if self._linhas else None


class ConexaoFalsa:
    """Conta consultas ao catálogo e simula um schema mutável.

    Deliberadamente sem 'sqlite' no nome do módulo nem da classe:
    `_is_sqlite_connection` decide por essa string, e o caminho que interessa
    medir é o do PostgreSQL.
    """

    def __init__(self, schema_simulado=None):
        self.schema = {t: set(c) for t, c in (schema_simulado or {}).items()}
        self.consultas_tabelas = 0
        self.consultas_colunas = 0
        self.alters = []

    @property
    def consultas_catalogo(self):
        return self.consultas_tabelas + self.consultas_colunas

    def execute(self, sql, params=None):
        texto = ' '.join(str(sql).split())
        if 'information_schema.tables' in texto:
            self.consultas_tabelas += 1
            nome = (params or ('',))[0]
            return _Resultado([{'um': 1}] if nome in self.schema else [])
        if 'information_schema.columns' in texto:
            self.consultas_colunas += 1
            nome = (params or ('',))[0]
            return _Resultado(
                [{'column_name': coluna} for coluna in sorted(self.schema.get(nome, ()))]
            )
        partes = texto.split()
        if len(partes) >= 6 and partes[0].upper() == 'ALTER' and partes[3].upper() == 'ADD':
            self.alters.append((partes[2], partes[5]))
            self.schema.setdefault(partes[2], set()).add(partes[5])
            return _Resultado([])
        return _Resultado([])

    def commit(self):
        pass

    def rollback(self):
        pass


class ConexaoRigida:
    """Portador que RECUSA atributos, como `sqlite3.Connection` faz.

    Medido, não suposto: `sqlite3.Connection` não aceita atributo nem
    referência fraca. Esta classe reproduz essa restrição com `__slots__` para
    que o fallback seja exercido sem depender de um banco.
    """

    __slots__ = ('_interna',)

    def __init__(self, schema_simulado=None):
        object.__setattr__(self, '_interna', ConexaoFalsa(schema_simulado))

    def execute(self, sql, params=None):
        return self._interna.execute(sql, params)

    def commit(self):
        self._interna.commit()

    def rollback(self):
        self._interna.rollback()

    @property
    def consultas_catalogo(self):
        return self._interna.consultas_catalogo

    @property
    def alters(self):
        return self._interna.alters


# ── A carga real do bootstrap, extraída do próprio código ────────────────────

def _funcoes_com_safe_add_column(arvore):
    return [
        no for no in ast.walk(arvore)
        if isinstance(no, ast.FunctionDef)
        and any(
            isinstance(f, ast.Call) and isinstance(f.func, ast.Name)
            and f.func.id == '_safe_add_column'
            for f in ast.walk(no)
        )
    ]


def carga_real_do_bootstrap():
    """`(tabela, coluna)` de cada invocação de `_safe_add_column` por partida.

    A DISTRIBUIÇÃO POR TABELA é real, extraída de `core/schema.py` com os laços
    expandidos — é ela que determina o número de idas ao catálogo. Os nomes de
    coluna são sintéticos e únicos: o gate mede round-trips, não identificadores,
    e sintetizar evita depender de resolver desempacotamento de tuplas.

    Extrair do código, em vez de fixar uma lista, mantém o gate medindo a carga
    real quando ela mudar.
    """
    arvore = ast.parse((RAIZ / 'core' / 'schema.py').read_text(encoding='utf-8'))
    carga = []
    for funcao in [no for no in ast.walk(arvore) if isinstance(no, ast.FunctionDef)]:
        pai = {}
        for no in ast.walk(funcao):
            for filho in ast.iter_child_nodes(no):
                pai[filho] = no

        # Listas resolvidas POR FUNÇÃO: `migrations` existe em várias delas com
        # tamanhos diferentes, e um dicionário global faria uma sobrescrever a
        # outra — medindo uma carga que não é a de ninguém.
        listas = {}
        for no in ast.walk(funcao):
            if isinstance(no, ast.Assign) and isinstance(no.value, (ast.List, ast.Tuple)):
                for alvo in no.targets:
                    if isinstance(alvo, ast.Name):
                        listas[alvo.id] = len(no.value.elts)

        def _tamanho(laco, _listas=listas):
            if isinstance(laco.iter, (ast.List, ast.Tuple)):
                return len(laco.iter.elts)
            if isinstance(laco.iter, ast.Name) and laco.iter.id in _listas:
                return _listas[laco.iter.id]
            return None

        for no in ast.walk(funcao):
            if not (isinstance(no, ast.Call) and isinstance(no.func, ast.Name)
                    and no.func.id == '_safe_add_column' and len(no.args) >= 2):
                continue
            arg = no.args[1]

            # A tabela pode ser literal ou vir de `for <t> in (lit, lit)`.
            tabelas = [arg.value] if isinstance(arg, ast.Constant) else []
            laco_da_tabela = None
            if isinstance(arg, ast.Name):
                atual = pai.get(no)
                while atual is not None:
                    if (isinstance(atual, ast.For) and isinstance(atual.target, ast.Name)
                            and atual.target.id == arg.id
                            and isinstance(atual.iter, (ast.Tuple, ast.List))
                            and all(isinstance(e, ast.Constant) for e in atual.iter.elts)):
                        tabelas = [e.value for e in atual.iter.elts]
                        laco_da_tabela = atual
                        break
                    atual = pai.get(atual)
            assert tabelas, (
                f'{funcao.name}: tabela de _safe_add_column não resolvida estaticamente'
            )

            # Os DEMAIS laços em volta multiplicam as invocações — é
            # `for col, defn in migrations:` que faz `ensure_company_columns`
            # valer 33 idas ao catálogo e não uma. Sem expandir, o gate mediria
            # uma carga menor que a real e o teto seria fácil demais.
            multiplicador = 1
            atual = pai.get(no)
            while atual is not None:
                if isinstance(atual, ast.For) and atual is not laco_da_tabela:
                    tamanho = _tamanho(atual)
                    assert tamanho is not None, (
                        f'{funcao.name}: laço de tamanho desconhecido em volta de '
                        f'_safe_add_column — a carga real não pode ser inferida'
                    )
                    multiplicador *= tamanho
                atual = pai.get(atual)

            for tabela in tabelas:
                for _ in range(multiplicador):
                    carga.append((tabela, f'coluna_{len(carga)}'))
    return carga


def _schema_de(carga):
    simulado = {}
    for tabela, coluna in carga:
        simulado.setdefault(tabela, set()).add(coluna)
    return simulado


def _rodar_carga(conexao, carga):
    for tabela, coluna in carga:
        schema._safe_add_column(conexao, tabela, coluna, 'TEXT')


# ── Gate 4 ───────────────────────────────────────────────────────────────────

def test_gate_4_memo_nunca_transforma_desconhecido_em_existe():
    conexao = ConexaoFalsa({'companies': {'id'}})
    epi_db.abrir_memo_catalogo(conexao)
    try:
        assert epi_db.table_exists(conexao, 'tabela_que_nao_existe') is False
        assert conexao.consultas_tabelas >= 1, 'negativa tem de vir de consulta viva'

        assert epi_db.column_exists(conexao, 'companies', 'coluna_que_nao_existe') is False
        antes = conexao.consultas_colunas
        assert antes >= 1

        # Repetir a pergunta negativa NÃO pode passar a ser respondida pelo memo.
        assert epi_db.column_exists(conexao, 'companies', 'coluna_que_nao_existe') is False
        assert conexao.consultas_colunas > antes, 'ausência foi memoizada como negativa'
    finally:
        epi_db.fechar_memo_catalogo(conexao)


def test_gate_4_ausencia_de_tabela_nunca_e_gravada():
    conexao = ConexaoFalsa({})
    epi_db.abrir_memo_catalogo(conexao)
    try:
        assert epi_db.table_columns(conexao, 'inexistente') == set()
        assert epi_db._catalogo_memo(conexao) == {}, 'conjunto vazio não é conhecimento'
    finally:
        epi_db.fechar_memo_catalogo(conexao)


# ── Gate 5 ───────────────────────────────────────────────────────────────────

def test_gate_5_fallback_quando_o_portador_recusa_o_memo():
    carga = carga_real_do_bootstrap()
    simulado = _schema_de(carga)

    rigida = ConexaoRigida(simulado)
    assert epi_db.abrir_memo_catalogo(rigida) is False
    assert epi_db._catalogo_memo(rigida) is None
    _rodar_carga(rigida, carga)

    solta = ConexaoFalsa(simulado)
    _rodar_carga(solta, carga)

    assert rigida.consultas_catalogo == solta.consultas_catalogo
    assert rigida.alters == [] and solta.alters == []


# ── Gate 6 e Gate 7 ──────────────────────────────────────────────────────────

def test_gate_6_memo_reduz_consultas_de_catalogo():
    carga = carga_real_do_bootstrap()
    simulado = _schema_de(carga)
    tabelas = {tabela for tabela, _ in carga}

    sem_memo = ConexaoFalsa(simulado)
    _rodar_carga(sem_memo, carga)

    com_memo = ConexaoFalsa(simulado)
    epi_db.abrir_memo_catalogo(com_memo)
    try:
        _rodar_carga(com_memo, carga)
    finally:
        epi_db.fechar_memo_catalogo(com_memo)

    # Regime estacionário: o schema já está correto, nenhum ALTER é emitido.
    assert sem_memo.alters == []
    assert com_memo.alters == []

    # Hoje: duas consultas por invocação. Com memo: duas por tabela distinta.
    assert sem_memo.consultas_catalogo == 2 * len(carga)
    assert com_memo.consultas_catalogo == 2 * len(tabelas)
    assert com_memo.consultas_catalogo <= TETO_DE_CONSULTAS


def test_gate_7_sabotagem_memo_desativado_derruba_o_gate_6(monkeypatch):
    monkeypatch.setattr(epi_db, 'abrir_memo_catalogo', lambda conexao: False)
    carga = carga_real_do_bootstrap()
    conexao = ConexaoFalsa(_schema_de(carga))
    epi_db.abrir_memo_catalogo(conexao)
    _rodar_carga(conexao, carga)

    assert conexao.consultas_catalogo == 2 * len(carga)
    assert conexao.consultas_catalogo > TETO_DE_CONSULTAS, (
        'sem o memo o teto do gate 6 tem de ser violado — caso contrário aquele '
        'gate passaria mesmo sem a otimização, e não provaria nada'
    )


# ── Gate 8 ───────────────────────────────────────────────────────────────────

def test_gate_8_sqlite_permanece_no_comportamento_atual():
    conexao = sqlite3.connect(':memory:')
    try:
        conexao.execute('CREATE TABLE t (id INTEGER, nome TEXT)')
        assert epi_db.abrir_memo_catalogo(conexao) is False
        assert epi_db._catalogo_memo(conexao) is None

        assert epi_db.table_exists(conexao, 't') is True
        assert epi_db.table_exists(conexao, 'ausente') is False
        assert epi_db.table_columns(conexao, 't') == {'id', 'nome'}
        assert epi_db.column_exists(conexao, 't', 'nome') is True
        assert epi_db.column_exists(conexao, 't', 'ausente') is False

        epi_db.fechar_memo_catalogo(conexao)  # não pode levantar
        epi_db.invalidar_memo_catalogo(conexao, 't')  # idem
    finally:
        conexao.close()


# ── Gate 10 ──────────────────────────────────────────────────────────────────

def test_gate_10_deadline_da_certificacao_intacto():
    fonte = (RAIZ / 'scripts' / 'certificar_deployment.py').read_text(encoding='utf-8')
    assert re.search(r'^PREFLIGHT_DEADLINE = 180$', fonte, re.MULTILINE)
    assert re.search(r'^TIMEOUT = 20$', fonte, re.MULTILINE)


# ── Gate 11 ──────────────────────────────────────────────────────────────────

def test_gate_11_memo_nao_sobrevive_ao_bootstrap_em_sucesso():
    conexao = ConexaoFalsa({})
    with _memo_catalogo_do_bootstrap(conexao):
        assert epi_db._catalogo_memo(conexao) is not None
    assert epi_db._catalogo_memo(conexao) is None, (
        'a conexão volta ao pool carregando um retrato do schema'
    )


def test_gate_11_memo_nao_sobrevive_a_excecao_no_bootstrap():
    conexao = ConexaoFalsa({})
    with pytest.raises(RuntimeError), _memo_catalogo_do_bootstrap(conexao):
        assert epi_db._catalogo_memo(conexao) is not None
        raise RuntimeError('migração falhou no meio do bootstrap')
    assert epi_db._catalogo_memo(conexao) is None


# ── Gate 12/14 na suíte rápida, e a sabotagem do Gate 13 ─────────────────────

def _predicado_sabotado(connection, table, column):
    """Versão ERRADA de propósito: deixa a ausência no memo responder `False`."""
    memo = epi_db._catalogo_memo(connection)
    nome_tabela = str(table or '').strip()
    nome_coluna = str(column or '').strip()
    if memo is not None:
        conhecidas = memo.get(nome_tabela)
        if conhecidas is not None:
            return nome_coluna in conhecidas
    return nome_coluna in epi_db.table_columns(connection, nome_tabela)


def _cenario_de_alteracao_externa(conexao):
    """Memoriza a tabela, alguém adiciona uma coluna por fora, tenta migrar."""
    epi_db.abrir_memo_catalogo(conexao)
    schema._safe_add_column(conexao, 'companies', 'ja_existia', 'TEXT')
    conexao.schema['companies'].add('nova_por_fora')  # outro bootstrap em paralelo
    schema._safe_add_column(conexao, 'companies', 'nova_por_fora', 'TEXT')


def test_gate_12_ausencia_no_memo_e_reconferida_no_catalogo():
    conexao = ConexaoFalsa({'companies': {'id', 'ja_existia'}})
    try:
        _cenario_de_alteracao_externa(conexao)
    finally:
        epi_db.fechar_memo_catalogo(conexao)
    assert conexao.alters == [], (
        'a coluna já existia no banco; o memo estava velho e mandou alterar'
    )


def test_gate_13_sabotagem_short_circuit_negativo_emite_alter_duplicado(monkeypatch):
    monkeypatch.setattr(epi_db, 'column_exists', _predicado_sabotado)
    conexao = ConexaoFalsa({'companies': {'id', 'ja_existia'}})
    try:
        _cenario_de_alteracao_externa(conexao)
    finally:
        epi_db.fechar_memo_catalogo(conexao)
    assert conexao.alters == [('companies', 'nova_por_fora')], (
        'a sabotagem precisa produzir o ALTER indevido — se não produzir, o '
        'gate 12 passaria mesmo com caching negativo e seria vacuoso'
    )


# ── Gate 16 ──────────────────────────────────────────────────────────────────

def test_gate_16_nenhum_objeto_removido_no_bootstrap_e_alvo_de_safe_add_column():
    """Fecha o risco residual do memo: uma entrada POSITIVA só envelhece se o
    objeto for removido. Hoje os únicos `DROP` do bootstrap atingem objetos que
    `_safe_add_column` nunca toca — este gate reprova no dia em que a combinação
    for introduzida, em vez de depender de alguém lembrar."""
    fonte = (RAIZ / 'core' / 'schema.py').read_text(encoding='utf-8')
    removidos = set()
    for padrao in (r'DROP\s+COLUMN\s+(?:IF\s+EXISTS\s+)?([A-Za-z_][A-Za-z0-9_]*)',
                   r'DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?([A-Za-z_][A-Za-z0-9_]*)'):
        removidos.update(m.group(1) for m in re.finditer(padrao, fonte, re.IGNORECASE))
    assert removidos, 'nenhum DROP encontrado — o gate ficaria vacuoso'

    arvore = ast.parse(fonte)
    nomes_tocados = set()
    for funcao in _funcoes_com_safe_add_column(arvore):
        for no in ast.walk(funcao):
            if isinstance(no, ast.Constant) and isinstance(no.value, str):
                nomes_tocados.add(no.value)

    colisao = removidos & nomes_tocados
    assert not colisao, (
        f'objeto removido no bootstrap também aparece em função que chama '
        f'_safe_add_column: {sorted(colisao)}. Uma entrada positiva do memo '
        f'poderia envelhecer.'
    )
