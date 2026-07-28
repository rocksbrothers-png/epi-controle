"""Chave de idempotência da entrega (plano §11).

A fila offline do app reenvia a operação quando a resposta se perde — timeout,
queda de rede, app fechado no meio. O reenvio é da **mesma** entrega.

Sem a chave, esse reenvio batia no bloqueio do item etiquetado
("item já baixado, entregue, descartado ou inválido") e **falhava para
sempre**: a fila nunca drenava e o operador via erro numa entrega que, no
servidor, tinha dado certo.

Vale registrar o que a chave **não** conserta, para não superestimá-la: a baixa
dupla de estoque já era impossível, porque cada entrega exige uma unidade
etiquetada e o claim `WHERE status = 'in_stock'` só deixa uma passar. O que a
chave traz é a resposta correta para quem repete — o id da entrega original, em
vez de um erro.
"""

import sqlite3

from core.schema import ensure_delivery_handover_columns
from modules.deliveries.service import find_delivery_by_idempotency_key

EMPRESA, OUTRA_EMPRESA = 1, 2
CHAVE = 'entrega-6f1b2c-2026-07-28'


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            employee_id INTEGER,
            epi_id INTEGER,
            quantity INTEGER
        );
        """
    )
    ensure_delivery_handover_columns(conn)
    conn.commit()
    return conn


def _entrega(conn, company_id=EMPRESA, chave=''):
    cursor = conn.execute(
        'INSERT INTO deliveries (company_id, employee_id, epi_id, quantity, idempotency_key) '
        'VALUES (?, ?, ?, ?, ?)',
        (company_id, 7, 99, 1, chave),
    )
    conn.commit()
    return int(cursor.lastrowid)


def test_reenvio_encontra_a_entrega_original():
    conn = _conn()
    original = _entrega(conn, chave=CHAVE)
    assert find_delivery_by_idempotency_key(conn, company_id=EMPRESA, key=CHAVE) == original


def test_chave_vazia_nao_encontra_nada():
    """Todo o histórico anterior à coluna está com string vazia.

    Se a busca casasse com vazio, a primeira entrega antiga seria devolvida
    como se fosse a de agora — e nenhuma entrega nova seria registrada.
    """
    conn = _conn()
    _entrega(conn, chave='')
    _entrega(conn, chave='')
    for vazio in ('', '   ', None):
        assert find_delivery_by_idempotency_key(conn, company_id=EMPRESA, key=vazio) is None


def test_chave_e_escopada_por_empresa():
    """Chave é gerada pelo cliente; colisão entre tenants não pode vazar."""
    conn = _conn()
    _entrega(conn, company_id=OUTRA_EMPRESA, chave=CHAVE)
    assert find_delivery_by_idempotency_key(conn, company_id=EMPRESA, key=CHAVE) is None


def test_espacos_nas_bordas_nao_criam_chave_diferente():
    conn = _conn()
    original = _entrega(conn, chave=CHAVE)
    assert find_delivery_by_idempotency_key(conn, company_id=EMPRESA, key=f'  {CHAVE} ') == original


def test_chave_desconhecida_deixa_a_entrega_seguir():
    conn = _conn()
    _entrega(conn, chave=CHAVE)
    assert find_delivery_by_idempotency_key(conn, company_id=EMPRESA, key='outra-chave') is None


def test_schema_sem_a_coluna_nao_quebra():
    """Janela de migração: base antiga continua registrando entregas."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript('CREATE TABLE deliveries (id INTEGER PRIMARY KEY, company_id INTEGER);')
    assert find_delivery_by_idempotency_key(conn, company_id=EMPRESA, key=CHAVE) is None


def test_banco_recusa_duas_entregas_com_a_mesma_chave():
    """A garantia final é do índice, não da consulta.

    Duas requisições simultâneas podem passar juntas pela busca; é o índice
    único que impede as duas de gravarem.
    """
    conn = _conn()
    _entrega(conn, chave=CHAVE)
    try:
        _entrega(conn, chave=CHAVE)
    except sqlite3.IntegrityError:
        return
    raise AssertionError('índice único de idempotência não está protegendo a gravação')


def test_entregas_sem_chave_nao_colidem_entre_si():
    """O índice é parcial de propósito: vazio não é uma chave."""
    conn = _conn()
    _entrega(conn, chave='')
    _entrega(conn, chave='')
    total = conn.execute('SELECT COUNT(*) AS t FROM deliveries').fetchone()['t']
    assert total == 2
