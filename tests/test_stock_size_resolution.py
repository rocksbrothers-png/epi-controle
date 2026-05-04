import server_postgres


def test_resolve_item_size_accepts_glove_only():
    resolved = server_postgres.resolve_item_size('G (9)', 'N/A', 'N/A')
    assert resolved['selected_size'] == 'G (9)'
    assert resolved['size'] == 'G (9)'


def test_resolve_item_size_accepts_size_only():
    resolved = server_postgres.resolve_item_size('N/A', 'M', 'N/A')
    assert resolved['selected_size'] == 'M'
    assert resolved['size'] == 'M'


def test_resolve_item_size_accepts_uniform_only():
    resolved = server_postgres.resolve_item_size('N/A', '', 'GG')
    assert resolved['selected_size'] == 'GG'
    assert resolved['size'] == 'GG'


def test_resolve_item_size_rejects_all_empty_equivalents():
    resolved = server_postgres.resolve_item_size('N/A', 'Selecione', 'undefined')
    assert resolved['selected_size'] == ''
    assert resolved['size'] == 'N/A'


def test_resolve_item_size_accepts_when_one_field_valid():
    resolved = server_postgres.resolve_item_size('N/A', 'N/A', '42')
    assert resolved['selected_size'] == '42'
    assert resolved['size'] == '42'

