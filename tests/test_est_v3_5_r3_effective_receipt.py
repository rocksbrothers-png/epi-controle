"""Receipt quantity refusals and persisted-piece success contract (SQLite)."""
import pytest

from test_purchase_conference_qr_labels import _actor, _conn, _seed_received_pr
from modules.purchases.service import _effective_receive_quantity, update_purchase_request_status


@pytest.mark.parametrize('value', [0, None, -2, 'invalid', 1.5])
def test_linked_po_invalid_quantity_never_uses_requested(value):
    c = _conn()
    _seed_received_pr(c, quantity=5)
    c.execute('INSERT INTO purchase_order_items (id, purchase_request_item_id, quantity_received) VALUES (1,1,?)', (value,))
    c.commit()
    try:
        assert _effective_receive_quantity(c, {'id': 1, 'quantity_requested': 5}) <= 0
        with pytest.raises(ValueError, match='Quantidade efetivamente recebida'):
            update_purchase_request_status(c, _actor(), {'id': 1, 'company_id': 1, 'status': 'received'},
                                           'checked', '', '', [{'id': 1, 'received': True}], '')
        c.rollback()
        assert c.execute('SELECT status FROM purchase_requests WHERE id=1').fetchone()['status'] == 'received'
        assert c.execute('SELECT COUNT(*) FROM epi_stock_items').fetchone()[0] == 0
        assert c.execute('SELECT COUNT(*) FROM stock_movements').fetchone()[0] == 0
    finally:
        c.close()


def test_partial_quantity_success_is_exactly_persisted_pieces():
    c = _conn()
    _seed_received_pr(c, quantity=5)
    c.execute('INSERT INTO purchase_order_items (id, purchase_request_item_id, quantity_received) VALUES (1,1,2)')
    result = update_purchase_request_status(c, _actor(), {'id': 1, 'company_id': 1, 'status': 'received'},
                                           'checked', 'partial', '', [{'id': 1, 'received': True}], '')
    c.commit()
    assert result['stock_entries'] == 2
    assert len(result['qr_labels']) == c.execute('SELECT COUNT(*) FROM epi_stock_items').fetchone()[0] == 2
    assert c.execute('SELECT quantity FROM unit_epi_stock').fetchone()[0] == 2
    c.close()


def test_no_selected_piece_cannot_report_stock_success():
    c = _conn()
    _seed_received_pr(c, quantity=5)
    result = update_purchase_request_status(c, _actor(), {'id': 1, 'company_id': 1, 'status': 'received'},
                                           'checked', 'not received', '', [{'id': 1, 'received': False}], '')
    c.commit()
    assert result['stock_entries'] == 0 and result['qr_labels'] == []
    assert c.execute('SELECT COUNT(*) FROM epi_stock_items').fetchone()[0] == 0
    c.close()


def test_selected_foreign_item_cannot_report_empty_success():
    c = _conn()
    _seed_received_pr(c, quantity=5)
    with pytest.raises(ValueError, match='Nenhuma peça efetivamente registrada'):
        update_purchase_request_status(c, _actor(), {'id': 1, 'company_id': 1, 'status': 'received'},
                                       'checked', '', '', [{'id': 999, 'received': True}], '')
    c.rollback()
    assert c.execute('SELECT status FROM purchase_requests WHERE id=1').fetchone()[0] == 'received'
    c.close()


def test_missing_persisted_piece_refuses_despite_generated_labels(monkeypatch):
    import modules.stock.service as stock_service
    original = stock_service.record_received_item_physical

    def lose_piece(connection, item_id, *args, **kwargs):
        original(connection, item_id, *args, **kwargs)
        connection.execute('DELETE FROM epi_stock_items WHERE id=?', (item_id,))

    monkeypatch.setattr(stock_service, 'record_received_item_physical', lose_piece)
    c = _conn()
    _seed_received_pr(c, quantity=2)
    with pytest.raises(ValueError, match='Nenhuma peça efetivamente registrada'):
        update_purchase_request_status(c, _actor(), {'id': 1, 'company_id': 1, 'status': 'received'},
                                       'checked', '', '', [{'id': 1, 'received': True}], '')
    c.rollback()
    assert c.execute('SELECT COUNT(*) FROM stock_movements').fetchone()[0] == 0
    assert c.execute('SELECT COUNT(*) FROM epi_stock_items').fetchone()[0] == 0
    c.close()
