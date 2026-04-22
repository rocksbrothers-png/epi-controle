from server_postgres import parse_stock_qr_lookup_value


def test_parse_stock_qr_lookup_value_handles_epi_item_label_format():
    parsed = parse_stock_qr_lookup_value('EPI-ITEM-0002-0005-00000078')
    assert parsed['format'] == 'stock-label'
    assert parsed['stock_item_id'] == 78
    assert parsed['qr_code_value'] == 'epi-item-0002-0005-00000078'


def test_parse_stock_qr_lookup_value_handles_simple_format():
    parsed = parse_stock_qr_lookup_value('EPIITEM:123')
    assert parsed['format'] == 'simple'
    assert parsed['stock_item_id'] == 123
    assert parsed['qr_code_value'] is None
