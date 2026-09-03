"""#315 — `ADD CONSTRAINT` protegido por SAVEPOINT, contra PostgreSQL real.

Vive fora de ``tests/`` pela mesma razão de
``test_returning_id_transaction_isolation_postgres.py``: o defeito depende de
semântica de transação abortada que o SQLite não replica.

## O que estes gates provam

Duas propriedades DIFERENTES, e é preciso as duas — provar só uma deixa passar
uma das duas falsas soluções:

1. **Trabalho anterior sobrevive.** Trabalho válido pendente → SAVEPOINT →
   falha no `ADD CONSTRAINT` → `ROLLBACK TO SAVEPOINT` → o pendente continua
   lá **e** a transação segue utilizável. Um `connection.rollback()` global
   recupera a conexão e REPROVA aqui, porque descarta o trabalho junto.
2. **Segunda execução normal.** Constraint já existe → não se tenta
   `ADD CONSTRAINT` → nenhuma exceção → o índice continua existindo. Engolir a
   exceção passaria na primeira propriedade e REPROVA aqui, por continuar
   produzindo sucesso falso.

Medido em PostgreSQL 16.13 antes de escrever a correção:

    estratégia                     statement seguinte   trabalho pendente
    engolir sem nada (o defeito)   falha                PERDIDO
    connection.rollback() global   executa              PERDIDO
    SAVEPOINT + ROLLBACK TO        executa              preservado

Esta suíte NÃO exige que a ausência da FK derrube o bootstrap: essa é uma
decisão de disponibilidade, anterior à #315 e tratada na #327. O que ela exige
é que uma criação realmente fracassada nunca passe como sucesso.
"""
import os
from contextlib import closing

import pytest

from core import schema
from core.database import get_connection

pytestmark = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL', '').startswith('postgres'),
    reason='Exige DATABASE_URL apontando para PostgreSQL real.',
)

PAI = 't315_pai'
FILHO = 't315_filho'
FK = 'fk_t315_filho_pai'
MARCADOR = 'MARCADOR-315'
DDL = (f'ALTER TABLE {FILHO} ADD CONSTRAINT {FK} '
       f'FOREIGN KEY (pai_id) REFERENCES {PAI}(id) ON DELETE SET NULL')


@pytest.fixture
def cenario_com_orfao():
    """Órfão em `pai_id` faz o `ADD CONSTRAINT` falhar DETERMINISTICAMENTE.

    A falha da produção ("constraint já existe") não serve aqui: a correção
    passa a detectá-la na pré-checagem e nem chega ao savepoint. Para exercitar
    o caminho protegido é preciso uma falha que a pré-checagem não prevê.
    """
    with closing(get_connection()) as conexao:
        conexao.execute(f'DROP TABLE IF EXISTS {FILHO}')
        conexao.execute(f'DROP TABLE IF EXISTS {PAI}')
        conexao.execute(f'CREATE TABLE {PAI} (id integer PRIMARY KEY)')
        conexao.execute(
            f'CREATE TABLE {FILHO} (id serial PRIMARY KEY, pai_id integer, marcador text)')
        conexao.execute(f'INSERT INTO {FILHO} (pai_id, marcador) VALUES (99999, %s)',
                        ('orfao',))
        conexao.commit()
    yield
    with closing(get_connection()) as conexao:
        conexao.execute(f'DROP TABLE IF EXISTS {FILHO}')
        conexao.execute(f'DROP TABLE IF EXISTS {PAI}')
        conexao.commit()


class _Espiao:
    """Delegador que registra o SQL emitido, sem alterar comportamento."""

    def __init__(self, conexao):
        self._conexao = conexao
        self.sql = []

    def execute(self, query, params=None):
        self.sql.append(str(query))
        return self._conexao.execute(query, params) if params is not None \
            else self._conexao.execute(query)

    def __getattr__(self, nome):
        return getattr(self._conexao, nome)


def _marcadores():
    with closing(get_connection()) as conexao:
        linha = conexao.execute(
            f'SELECT count(*) FROM {FILHO} WHERE marcador = %s', (MARCADOR,)).fetchone()
    return linha[0]


def _rodar_cenario(estrategia):
    """Trabalho válido pendente, depois a falha. Devolve (seguinte, sobreviveu)."""
    seguinte = 'executou'
    with closing(get_connection()) as conexao:
        conexao.execute(f'INSERT INTO {FILHO} (pai_id, marcador) VALUES (NULL, %s)',
                        (MARCADOR,))
        estrategia(conexao)
        try:
            conexao.execute(f'CREATE INDEX IF NOT EXISTS idx_t315 ON {FILHO} (pai_id)')
        except Exception as erro:  # noqa: BLE001 - medir a falha É o teste
            seguinte = f'FALHOU: {str(erro).strip()[:60]}'
        try:
            conexao.commit()
        except Exception:  # noqa: BLE001,S110 - a estratégia ANTIGA deixa a transação abortada
            pass
    return seguinte, _marcadores() == 1


def _estrategia_atual(conexao):
    """O defeito da #315: engole e não desfaz nada."""
    try:
        conexao.execute(DDL)
        conexao.commit()
    except Exception:  # noqa: BLE001,S110 - reproduz o defeito de propósito
        pass


def _estrategia_rollback_global(conexao):
    """A falsa solução: recupera a conexão e descarta trabalho válido junto."""
    try:
        conexao.execute(DDL)
        conexao.commit()
    except Exception:  # noqa: BLE001 - reproduz a falsa solução de propósito
        conexao.rollback()


def _estrategia_corrigida(conexao):
    assert schema._add_constraint_protegido(conexao, FILHO, FK, DDL) is False


# ═══════════════════════════════════════════════════════════════════════════
# Propriedade 1 — trabalho anterior sobrevive E a transação segue utilizável
# ═══════════════════════════════════════════════════════════════════════════

def test_savepoint_preserva_trabalho_anterior(cenario_com_orfao):
    seguinte, sobreviveu = _rodar_cenario(_estrategia_corrigida)
    assert seguinte == 'executou', \
        f'a transação ficou inutilizável depois da falha: {seguinte}'
    assert sobreviveu, \
        ('o trabalho válido pendente foi descartado — é exatamente o que o '
         '`connection.commit()` do runner faz com transação abortada, em '
         'silêncio, e o que o SAVEPOINT existe para impedir')


def test_as_tres_estrategias_sao_distinguiveis(cenario_com_orfao):
    """Sem isto, um `rollback()` global passaria por correção."""
    atual = _rodar_cenario(_estrategia_atual)
    assert atual == ('executou', True) or atual[0] != 'executou', 'cenário inválido'
    assert not atual[1], \
        ('a implementação ANTIGA preservou o trabalho — o cenário não reproduz '
         'mais o defeito e os gates abaixo não provam nada')
    assert atual[0] != 'executou', \
        'a implementação ANTIGA deixou a transação utilizável; cenário inválido'

    global_ = _rodar_cenario(_estrategia_rollback_global)
    assert global_[0] == 'executou', 'rollback global deveria recuperar a conexão'
    assert not global_[1], \
        ('o `rollback()` global preservou o trabalho pendente — se isso fosse '
         'verdade, ele seria correção suficiente e o SAVEPOINT seria supérfluo')

    corrigida = _rodar_cenario(_estrategia_corrigida)
    assert corrigida == ('executou', True), \
        f'a correção não entrega as duas propriedades: {corrigida}'


# ═══════════════════════════════════════════════════════════════════════════
# Observabilidade — falha real não pode passar como pulo benigno
# ═══════════════════════════════════════════════════════════════════════════

def test_falha_real_e_registrada_de_forma_inequivoca(cenario_com_orfao, monkeypatch):
    eventos = []
    monkeypatch.setattr(schema, 'structured_log',
                        lambda nivel, evento, **c: eventos.append((nivel, evento)))
    with closing(get_connection()) as conexao:
        assert schema._add_constraint_protegido(conexao, FILHO, FK, DDL) is False
        conexao.execute(f'SELECT 1 FROM {FILHO} LIMIT 1').fetchone()  # segue utilizável
        conexao.commit()

    nomes = [e for _, e in eventos]
    assert ('error', 'db.constraint_create_failed') in eventos, \
        f'falha real não saiu em `error`: {eventos}'
    assert 'db.constraint_created' not in nomes and \
           'db.constraint_already_present' not in nomes, \
        'uma criação fracassada foi reportada como sucesso'


# ═══════════════════════════════════════════════════════════════════════════
# Propriedade 2 — segunda passagem do bootstrap real
# ═══════════════════════════════════════════════════════════════════════════

def test_segunda_passagem_nao_tenta_add_constraint_e_mantem_o_indice():
    with closing(get_connection()) as conexao:
        assert schema._table_exists(conexao, 'deliveries'), \
            'banco não provisionado: este gate exige o schema real'

        schema.ensure_delivery_migration_origin_columns(conexao)
        conexao.commit()

        espiao = _Espiao(conexao)
        schema.ensure_delivery_migration_origin_columns(espiao)
        conexao.commit()

        tentou = [s for s in espiao.sql if 'ADD CONSTRAINT' in s.upper()]
        assert not tentou, \
            (f'a segunda passagem tentou criar a constraint de novo: {tentou}. '
             f'Em banco provisionado isso falha SEMPRE e abortava a transação.')

        indice = conexao.execute(
            "SELECT 1 FROM pg_indexes WHERE indexname = 'idx_deliveries_migrated'"
        ).fetchone()
        assert indice, \
            ('idx_deliveries_migrated não existe após a segunda passagem: o '
             'statement seguinte ao ADD CONSTRAINT voltou a ser descartado')


def test_a_pre_checagem_nao_aborta_transacao_com_tabela_ausente():
    """`_constraint_exists` sobre tabela inexistente NÃO pode envenenar nada.

    Com `'tabela'::regclass` a consulta levantaria `UndefinedTable` e abortaria
    justamente a transação que a checagem existe para proteger — trocando o
    defeito de lugar em vez de corrigi-lo.
    """
    with closing(get_connection()) as conexao:
        assert schema._constraint_exists(conexao, 't315_inexistente', 'fk_qualquer') is False

        # transação continua utilizável — é o que o regclass quebraria
        assert conexao.execute('SELECT 1').fetchone()[0] == 1
        conexao.commit()


@pytest.fixture
def cenario_limpo():
    """Sem órfãos: o `ADD CONSTRAINT` SUCEDE. Serve à pós-condição."""
    with closing(get_connection()) as conexao:
        conexao.execute(f'DROP TABLE IF EXISTS {FILHO}')
        conexao.execute(f'DROP TABLE IF EXISTS {PAI}')
        conexao.execute(f'CREATE TABLE {PAI} (id integer PRIMARY KEY)')
        conexao.execute(
            f'CREATE TABLE {FILHO} (id serial PRIMARY KEY, pai_id integer, marcador text)')
        conexao.commit()
    yield
    with closing(get_connection()) as conexao:
        conexao.execute(f'DROP TABLE IF EXISTS {FILHO}')
        conexao.execute(f'DROP TABLE IF EXISTS {PAI}')
        conexao.commit()


def test_pos_condicao_reprova_criacao_que_nao_deixou_a_constraint(cenario_limpo, monkeypatch):
    """Invariante 7: idempotência só se dá por satisfeita com existência COMPROVADA.

    O `ALTER TABLE` sucede de verdade aqui. Forçando a verificação a não achar
    a constraint, a função tem de devolver `False` e dizer isso — nunca aceitar
    "não levantou exceção" como prova de que o objeto existe. É a mesma regra
    que `_safe_add_column` aplica com `_col_exists` depois do `ALTER`.
    """
    eventos = []
    monkeypatch.setattr(schema, 'structured_log',
                        lambda nivel, evento, **c: eventos.append((nivel, evento)))
    monkeypatch.setattr(schema, '_constraint_exists', lambda *a, **k: False)

    with closing(get_connection()) as conexao:
        resultado = schema._add_constraint_protegido(conexao, FILHO, FK, DDL)
        conexao.commit()

    assert resultado is False, \
        'sucesso do ALTER foi aceito como prova de existência da constraint'
    assert ('error', 'db.constraint_missing_after_create') in eventos, \
        f'a pós-condição falhou em silêncio: {eventos}'
