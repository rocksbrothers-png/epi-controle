"""Valid sources retain all scalar values, Unicode and input order."""
import io
import json
import pytest
from modules.data_migration.sources import read_source

ROWS = [{'name':'São João & Filhos', 'city':'Macaé'}, {'name':'第二 unidade', 'city':'Vitória'}]


def payload(kind):
    if kind in ('csv', 'txt'):
        import csv
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=['name','city'], delimiter='\t' if kind == 'txt' else ',')
        writer.writeheader()
        writer.writerows(ROWS)
        return stream.getvalue().encode()
    if kind == 'json':
        return json.dumps({'data':ROWS}, ensure_ascii=False).encode()
    if kind == 'xml':
        return '<rows><row><name>São João &amp; Filhos</name><city>Macaé</city></row><row><name>第二 unidade</name><city>Vitória</city></row></rows>'.encode()
    import pandas as pd
    stream = io.BytesIO()
    pd.DataFrame(ROWS).to_excel(stream, index=False, engine='odf' if kind == 'ods' else 'openpyxl')
    return stream.getvalue()


@pytest.mark.parametrize('kind', ['csv', 'txt', 'json', 'xml', 'xlsx', 'ods'])
def test_valid_source_preserves_rows_columns_and_unicode(kind):
    dataset = read_source(kind, payload(kind))
    assert dataset.columns == ['name','city']
    assert dataset.rows == ROWS
    assert dataset.total_rows == 2
    assert not any(d.get('severity',d.get('level')) == 'error' for d in dataset.diagnostics)
