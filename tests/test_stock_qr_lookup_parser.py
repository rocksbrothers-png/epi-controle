from server_postgres import parse_stock_qr_lookup_value


def test_parse_stock_qr_lookup_value_handles_epi_item_label_format():
    parsed = parse_stock_qr_lookup_value('EPI-ITEM-0002-0005-00000078')
    assert parsed['format'] == 'stock-label'
    assert parsed['stock_item_id'] is None
    assert parsed['qr_code_value'] == 'EPI-ITEM-0002-0005-00000078'


def test_parse_stock_qr_lookup_value_handles_simple_format():
    parsed = parse_stock_qr_lookup_value('EPIITEM:123')
    assert parsed['format'] == 'simple'
    assert parsed['stock_item_id'] == 123
    assert parsed['qr_code_value'] is None


def test_parse_stock_qr_lookup_value_preserves_json_code_case():
    parsed = parse_stock_qr_lookup_value('{"type":"stock_item","id":99,"code":"EPI-ITEM-0002-0005-00000059"}')
    assert parsed['format'] == 'json'
    assert parsed['stock_item_id'] == 99
    assert parsed['qr_code_value'] == 'EPI-ITEM-0002-0005-00000059'
