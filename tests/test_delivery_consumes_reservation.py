"""A entrega abate a reserva — o par que precisa ser indivisível (plano §11).

Sem isto a reserva ficava `active` para sempre: o estoque físico caía na
entrega e a promessa continuava de pé, então **a mesma peça era subtraída duas
vezes** do saldo livre. Depois de algumas entregas a unidade parecia sem
estoque tendo prateleira cheia.

O consumo é parcial por natureza: a entrega é sempre de **uma** unidade
etiquetada, então uma solicitação de 3 gera 3 entregas contra a mesma reserva.
"""

import sqlite3

import pytest

from core.schema import ensure_stock_reservations
from modules.deliveries.service import consume_request_reservation
from modules.stock.reservations import (
    ACTIVE,
    CONSUMED,
    InsufficientFreeStock,
    ReservationNotActive,
    consume_reservation,
    create_reservation,
    get_reservation,
    remaining_quantity,
    reserved_quantity,
    unit_balance,
)

EMPRESA, UNIDADE, OUTRA_UNIDADE, EPI, OUTRO_EPI = 1, 10, 20, 99, 88


def _conn(fisico=10):
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT);
        CREATE TABLE epis (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE epi_requests (id INTEGER PRIMARY KEY, company_id INTEGER, status TEXT);
        CREATE TABLE unit_epi_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, unit_id INTEGER,
            epi_id INTEGER, quantity INTEGER DEFAULT 0
        );
        INSERT INTO companies (id, name) VALUES (1, 'ACME');
        INSERT INTO units (id, company_id, name) VALUES (10, 1, 'Base'), (20, 1, 'Outra');
        INSERT INTO epis (id, name) VALUES (99, 'Capacete'), (88, 'Luva');
        """
    )
    for unidade in (UNIDADE, OUTRA_UNIDADE):
        for epi in (EPI, OUTRO_EPI):
            conn.execute(
                'INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity) VALUES (?, ?, ?, ?)',
                (EMPRESA, unidade, epi, fisico),
            )
    ensure_stock_reservations(conn)
    conn.commit()
    return conn


def _reserva(conn, quantidade=3, request_id=500, unit_id=UNIDADE, epi_id=EPI):
    conn.execute(
        'INSERT OR IGNORE INTO epi_requests (id, company_id, status) VALUES (?, ?, ?)',
        (request_id, EMPRESA, 'reservado'),
    )
    return create_reservation(
        conn,
        company_id=EMPRESA, unit_id=unit_id, epi_id=epi_id,
        quantity=quantidade, request_id=request_id,
    )


def _baixa_fisica(conn, quantidade=1, unit_id=UNIDADE, epi_id=EPI):
    """Simula o efeito da entrega no estoque físico."""
    conn.execute(
        'UPDATE unit_epi_stock SET quantity = quantity - ? '
        'WHERE company_id = ? AND unit_id = ? AND epi_id = ?',
        (quantidade, EMPRESA, unit_id, epi_id),
    )


# ── o vazamento que motivou o bloco ──────────────────────────────────────────

def test_entregar_sem_abater_a_reserva_subtrairia_a_peca_duas_vezes():
    """Fixa o defeito: é o cenário que existia antes desta correção."""
    conn = _conn(fisico=10)
    _reserva(conn, quantidade=3)
    assert unit_balance(conn, EMPRESA, UNIDADE, EPI)['free'] == 7

    _baixa_fisica(conn)  # entrega acontece, reserva intocada
    # 9 físico − 3 reservado = 6, quando o correto seria 7: a peça entregue
    # saiu do físico e continuou prometida.
    assert unit_balance(conn, EMPRESA, UNIDADE, EPI)['free'] == 6


def test_entrega_abate_a_reserva_e_o_saldo_livre_se_mantem():
    conn = _conn(fisico=10)
    reserva = _reserva(conn, quantidade=3)
    livre_antes = unit_balance(conn, EMPRESA, UNIDADE, EPI)['free']

    _baixa_fisica(conn)
    consume_request_reservation(
        conn, request_id=500, company_id=EMPRESA, unit_id=UNIDADE,
        epi_id=EPI, quantity=1, delivery_id=777,
    )

    assert unit_balance(conn, EMPRESA, UNIDADE, EPI)['free'] == livre_antes
    assert remaining_quantity(get_reservation(conn, reserva['id'])) == 2


# ── consumo parcial: 3 entregas contra uma reserva de 3 ──────────────────────

def test_reserva_so_fecha_quando_o_ultimo_item_sai():
    conn = _conn(fisico=10)
    reserva = _reserva(conn, quantidade=3)

    for esperado_restante in (2, 1, 0):
        _baixa_fisica(conn)
        consume_request_reservation(
            conn, request_id=500, company_id=EMPRESA, unit_id=UNIDADE,
            epi_id=EPI, quantity=1, delivery_id=777,
        )
        atual = get_reservation(conn, reserva['id'])
        assert remaining_quantity(atual) == esperado_restante

    # Só agora a promessa acabou.
    assert get_reservation(conn, reserva['id'])['status'] == CONSUMED
    assert reserved_quantity(conn, EMPRESA, UNIDADE, EPI) == 0
    assert unit_balance(conn, EMPRESA, UNIDADE, EPI)['free'] == 7


def test_reserva_continua_ativa_enquanto_falta_entregar():
    """Fechar cedo liberaria peças ainda prometidas a quem solicitou."""
    conn = _conn(fisico=10)
    reserva = _reserva(conn, quantidade=3)
    _baixa_fisica(conn)
    consume_request_reservation(
        conn, request_id=500, company_id=EMPRESA, unit_id=UNIDADE,
        epi_id=EPI, quantity=1, delivery_id=777,
    )
    assert get_reservation(conn, reserva['id'])['status'] == ACTIVE
    assert reserved_quantity(conn, EMPRESA, UNIDADE, EPI) == 2


# ── o que não pode ser abatido ───────────────────────────────────────────────

def test_nao_abate_reserva_de_outra_unidade():
    """Devolver saldo livre a quem não entregou nada é pior que não abater."""
    conn = _conn(fisico=10)
    _reserva(conn, quantidade=3, unit_id=OUTRA_UNIDADE)

    resultado = consume_request_reservation(
        conn, request_id=500, company_id=EMPRESA, unit_id=UNIDADE,
        epi_id=EPI, quantity=1, delivery_id=777,
    )
    assert resultado is None
    assert reserved_quantity(conn, EMPRESA, OUTRA_UNIDADE, EPI) == 3


def test_nao_abate_reserva_de_outro_epi():
    conn = _conn(fisico=10)
    _reserva(conn, quantidade=3, epi_id=OUTRO_EPI)

    assert consume_request_reservation(
        conn, request_id=500, company_id=EMPRESA, unit_id=UNIDADE,
        epi_id=EPI, quantity=1, delivery_id=777,
    ) is None
    assert reserved_quantity(conn, EMPRESA, UNIDADE, OUTRO_EPI) == 3


def test_entrega_sem_solicitacao_nao_quebra():
    """Entrega direta de estoque é caminho legítimo — não há o que abater."""
    conn = _conn(fisico=10)
    assert consume_request_reservation(
        conn, request_id=999, company_id=EMPRESA, unit_id=UNIDADE,
        epi_id=EPI, quantity=1, delivery_id=777,
    ) is None


def test_schema_sem_reservas_nao_quebra_a_entrega():
    """Janela de migração: sem a tabela, a entrega segue normalmente."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    assert consume_request_reservation(
        conn, request_id=1, company_id=EMPRESA, unit_id=UNIDADE,
        epi_id=EPI, quantity=1, delivery_id=1,
    ) is None


# ── concorrência e limites ───────────────────────────────────────────────────

def test_nao_consome_mais_do_que_resta():
    conn = _conn(fisico=10)
    reserva = _reserva(conn, quantidade=2)
    with pytest.raises(InsufficientFreeStock):
        consume_reservation(conn, reserva['id'], quantity=3)
    assert remaining_quantity(get_reservation(conn, reserva['id'])) == 2


def test_reserva_ja_fechada_nao_consome_de_novo():
    conn = _conn(fisico=10)
    reserva = _reserva(conn, quantidade=1)
    consume_reservation(conn, reserva['id'], quantity=1)
    with pytest.raises(ReservationNotActive):
        consume_reservation(conn, reserva['id'], quantity=1)


def test_corrida_entre_duas_entregas_do_mesmo_item_nao_abate_duas_vezes():
    """A segunda entrega do último item encontra a reserva já fechada.

    A entrega em si não é recusada — ela é real e o estoque já caiu; o que não
    pode é abater a mesma promessa duas vezes.
    """
    conn = _conn(fisico=10)
    reserva = _reserva(conn, quantidade=1)
    primeira = consume_request_reservation(
        conn, request_id=500, company_id=EMPRESA, unit_id=UNIDADE,
        epi_id=EPI, quantity=1, delivery_id=777,
    )
    segunda = consume_request_reservation(
        conn, request_id=500, company_id=EMPRESA, unit_id=UNIDADE,
        epi_id=EPI, quantity=1, delivery_id=778,
    )
    assert primeira is not None
    assert segunda is None
    assert int(get_reservation(conn, reserva['id'])['consumed_quantity']) == 1


def test_consumo_sem_quantidade_abate_o_restante():
    conn = _conn(fisico=10)
    reserva = _reserva(conn, quantidade=4)
    consume_reservation(conn, reserva['id'], quantity=1)
    consume_reservation(conn, reserva['id'])
    fechada = get_reservation(conn, reserva['id'])
    assert fechada['status'] == CONSUMED
    assert remaining_quantity(fechada) == 0
