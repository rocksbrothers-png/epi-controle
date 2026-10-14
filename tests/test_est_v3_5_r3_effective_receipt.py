"""Receipt quantity refusals and persisted-piece success contract (SQLite)."""
import pytest

from test_purchase_conference_qr_labels import _actor, _conn, _seed_received_pr
from modules.purchases.service import _effective_receive_quantity, update_purchase_request_status


@pytest.mark.parametrize('value', [0, None, -2, 'invalid', 1.5, 'true'])
@pytest.mark.parametrize('received', [True, False])
def test_linked_po_invalid_quantity_never_uses_requested(value, received):
    c = _conn()
    _seed_received_pr(c, quantity=5)
    c.execute('INSERT INTO purchase_order_items (id, purchase_request_item_id, quantity_received) VALUES (1,1,?)', (value,))
    c.commit()
    try:
        assert _effective_receive_quantity(c, {'id': 1, 'quantity_requested': 5}) <= 0
        with pytest.raises(ValueError, match='Quantidade efetivamente recebida'):
            update_purchase_request_status(c, _actor(), {'id': 1, 'company_id': 1, 'status': 'received'},
                                           'checked', '', '', [{'id': 1, 'received': received}], '')
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


@pytest.mark.parametrize('value', [0, None, -2, 'invalid', 1.5, 'true'])
@pytest.mark.parametrize('received', [True, False])
def test_mixed_receipt_prevalidates_every_line_before_any_write(value, received, monkeypatch):
    import modules.purchases.service as service
    c = _conn()
    _seed_received_pr(c, quantity=5)
    c.execute('INSERT INTO purchase_order_items (id, purchase_request_item_id, quantity_received) VALUES (1,1,2)')
    c.execute("INSERT INTO purchase_request_items (id,purchase_request_id,company_id,unit_id,epi_id,epi_name,quantity_requested,status) VALUES (2,1,1,1,100,'Linha ruim',5,'received')")
    c.execute('INSERT INTO purchase_order_items (id,purchase_request_item_id,quantity_received) VALUES (2,2,?)', (value,))
    c.commit()

    def forbidden_stock_write(*args, **kwargs):
        pytest.fail('Stock processing began before all receipt lines were validated')

    monkeypatch.setattr(service, '_auto_add_received_items_to_stock', forbidden_stock_write)
    with pytest.raises(service.ReceiptValidationError) as caught:
        service.update_purchase_request_status(c, _actor(), {'id':1,'company_id':1,'status':'received'},
            'checked', 'partial', '', [{'id':1,'received':True},{'id':2,'received':received}], '')
    assert caught.value.details['line_index'] == 2
    assert caught.value.details['item_id'] == 2
    assert 'Linha 2' in str(caught.value) and 'Linha ruim' in str(caught.value)
    c.commit() # A caller cannot accidentally commit partial state after refusal.
    assert c.execute('SELECT status FROM purchase_requests WHERE id=1').fetchone()[0] == 'received'
    for table in ['epi_stock_items','stock_movements','purchase_events']:
        assert c.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] == 0
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
