"""Malformed input must never silently lose or overwrite source values."""
import io
import pytest
from modules.data_migration.sources import read_source


def rejected_or_diagnosed(kind, raw):
    try:
        dataset = read_source(kind, raw)
    except ValueError as exc:
        assert str(exc).strip()
        return
    errors = [d for d in dataset.diagnostics if d.get('severity', d.get('level')) == 'error']
    assert errors, (kind, dataset)
    assert all(d.get('message') and (d.get('row') or d.get('source_row')) for d in errors), errors


@pytest.mark.parametrize('raw', [
    b'[{"name":"first"},7,{"name":"third"}]',
    b'[{"name":"first"},null]',
    b'[{"name":"first"},[1,2]]',
    b'[{"name":{"nested":"lost"}}]',
    b'[{"name":["nested","lost"]}]',
    b'[{"name":"first","name":"lost"}]',
    b'[{" Name ":"first","name":"lost"}]',
])
def test_json_structural_data_loss_is_rejected_or_diagnosed(raw):
    rejected_or_diagnosed('json', raw)


@pytest.mark.parametrize('raw', [
    b'name,name\nfirst,lost\n',
    b' Name ,name\nfirst,lost\n',
    b'name,city\nfirst,Macae,LOST\n',
    b'name,city\nfirst\n',
    b'name,city\nfirst,Macae\nthird\n',
])
def test_csv_structural_data_loss_is_rejected_or_diagnosed(raw):
    rejected_or_diagnosed('csv', raw)


@pytest.mark.parametrize('raw', [
    b'<rows><row><name>first</name><name>lost</name></row></rows>',
    b'<rows><row><name><child>lost</child></name></row></rows>',
    b'<rows><row name="first"><name>lost</name></row></rows>',
    b'<rows><row><name>first</name></row><row>lost scalar</row></rows>',
])
def test_xml_structural_data_loss_is_rejected_or_diagnosed(raw):
    rejected_or_diagnosed('xml', raw)


def test_xlsx_duplicate_headers_rejected_before_library_renames_them():
    from openpyxl import Workbook
    workbook = Workbook()
    workbook.active.append(['name', 'name'])
    workbook.active.append(['first', 'lost'])
    stream = io.BytesIO()
    workbook.save(stream)
    rejected_or_diagnosed('xlsx', stream.getvalue())


def test_csv_malformed_row_position_is_not_renumbered():
    raw = b'name,city\nfirst,Macae\nsecond,Macae,EXTRA\nthird,Macae\n'
    try:
        dataset = read_source('csv', raw)
    except ValueError as exc:
        # Fail-closed parsing is safe; message must identify source location.
        assert '3' in str(exc), str(exc)
        return
    errors = [d for d in dataset.diagnostics if d.get('severity', d.get('level')) == 'error']
    assert errors, dataset
    assert any(d.get('source_row', d.get('row')) == 3 for d in errors), errors
