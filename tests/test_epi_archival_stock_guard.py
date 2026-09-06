"""Item 1 da auditoria — arquivamento de EPI com verificação de saldo.

Regra: nunca mover nem ocultar saldo automaticamente. Sem vínculos vivos,
arquiva normalmente. Com saldo, o arquivamento direto é impedido; a opção
autorizada bloqueia o saldo físico disponível (vira 'blocked_archived',
rastreável em Estoque Bloqueado — o item nunca some) e então arquiva, com
motivo e auditoria.
"""

import sqlite3


from modules.epis.service import (
    block_available_stock_for_archival,
    compute_epi_archival_state,
)


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE epis (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE epi_stock_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, unit_id INTEGER, epi_id INTEGER,
            glove_size TEXT DEFAULT 'N/A', size TEXT DEFAULT 'N/A', uniform_size TEXT DEFAULT 'N/A',
            qr_code_value TEXT DEFAULT '', status TEXT DEFAULT 'in_stock', updated_at TEXT DEFAULT ''
        );
        CREATE TABLE stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, unit_id INTEGER, epi_id INTEGER,
            movement_type TEXT, quantity INTEGER, previous_stock INTEGER, new_stock INTEGER,
            source_type TEXT, source_id INTEGER, notes TEXT, actor_user_id INTEGER, actor_name TEXT,
            created_at TEXT, glove_size TEXT, size TEXT, uniform_size TEXT
        );
        CREATE TABLE epi_requests (id INTEGER PRIMARY KEY, epi_id INTEGER, status TEXT DEFAULT 'open');
        CREATE TABLE epi_devolutions (id INTEGER PRIMARY KEY, epi_id INTEGER);
        CREATE TABLE purchase_orders (id INTEGER PRIMARY KEY, status TEXT DEFAULT 'open');
        CREATE TABLE purchase_order_items (id INTEGER PRIMARY KEY, purchase_order_id INTEGER, epi_id INTEGER);
        INSERT INTO epis (id, name) VALUES (7, 'Capacete');
        """
    )
    conn.commit()
    return conn


ACTOR = {'id': 3, 'full_name': 'Admin Geral'}


def test_no_links_allows_archive():
    conn = _conn()
    state = compute_epi_archival_state(conn, 7)
    assert state['has_open_links'] is False
    assert state['available'] == 0 and state['blockable'] == 0


def test_available_stock_flags_open_links():
    conn = _conn()
    conn.executemany(
        "INSERT INTO epi_stock_items (company_id, unit_id, epi_id, qr_code_value, status) VALUES (1,2,7,?, 'in_stock')",
        [('QR-1',), ('QR-2',), ('QR-3',)],
    )
    conn.commit()
    state = compute_epi_archival_state(conn, 7)
    assert state['available'] == 3
    assert state['blockable'] == 3
    assert state['has_open_links'] is True


def test_in_possession_and_pending_flag_links_but_are_not_blockable():
    conn = _conn()
    conn.execute("INSERT INTO epi_stock_items (company_id, unit_id, epi_id, qr_code_value, status) VALUES (1,2,7,'QR-D','delivered')")
    conn.execute("INSERT INTO epi_requests (id, epi_id, status) VALUES (1, 7, 'aprovado')")
    conn.execute("INSERT INTO purchase_orders (id, status) VALUES (5, 'approved')")
    conn.execute("INSERT INTO purchase_order_items (id, purchase_order_id, epi_id) VALUES (1, 5, 7)")
    conn.commit()
    state = compute_epi_archival_state(conn, 7)
    assert state['in_possession'] == 1
    assert state['pending_requests'] == 1
    assert state['pending_purchase'] == 1
    assert state['has_open_links'] is True
    # nada disponível para bloquear — o saldo físico está com o colaborador / em pedido
    assert state['blockable'] == 0


def test_terminal_request_and_received_order_do_not_flag():
    conn = _conn()
    conn.execute("INSERT INTO epi_requests (id, epi_id, status) VALUES (1, 7, 'entregue')")
    conn.execute("INSERT INTO purchase_orders (id, status) VALUES (5, 'received')")
    conn.execute("INSERT INTO purchase_order_items (id, purchase_order_id, epi_id) VALUES (1, 5, 7)")
    conn.execute("INSERT INTO epi_devolutions (id, epi_id) VALUES (1, 7)")
    conn.commit()
    state = compute_epi_archival_state(conn, 7)
    assert state['pending_requests'] == 0
    assert state['pending_purchase'] == 0
    assert state['returns_total'] == 1  # informativo, não impede
    assert state['has_open_links'] is False


def test_block_and_archive_moves_available_to_blocked_archived():
    conn = _conn()
    conn.executemany(
        "INSERT INTO epi_stock_items (company_id, unit_id, epi_id, qr_code_value, status) VALUES (1,2,7,?, 'in_stock')",
        [('QR-1',), ('QR-2',)],
    )
    conn.execute("INSERT INTO epi_stock_items (company_id, unit_id, epi_id, qr_code_value, status) VALUES (1,2,7,'QR-D','delivered')")
    conn.commit()
    blocked = block_available_stock_for_archival(conn, 7, 'EPI descontinuado', ACTOR, '2026-07-18T00:00:00')
    assert blocked == 2
    # os itens disponíveis viraram blocked_archived (rastreáveis, nunca somem)
    statuses = [r['status'] for r in conn.execute("SELECT status FROM epi_stock_items WHERE epi_id=7 ORDER BY id").fetchall()]
    assert statuses == ['blocked_archived', 'blocked_archived', 'delivered']
    # o item entregue (em posse) NÃO é tocado
    # auditoria registrada (stock_movements)
    movs = conn.execute("SELECT COUNT(*) FROM stock_movements WHERE epi_id=7").fetchone()[0]
    assert movs == 2
    # nenhum item físico foi apagado
    total = conn.execute("SELECT COUNT(*) FROM epi_stock_items WHERE epi_id=7").fetchone()[0]
    assert total == 3


def test_blocked_status_registered_in_catalog():
    from modules.stock.service import BLOCKED_STOCK_STATUSES
    assert 'blocked_archived' in BLOCKED_STOCK_STATUSES
