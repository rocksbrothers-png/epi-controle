import base64
from decimal import Decimal

import pytest

from epi_backend.purchase_import import parse_money_decimal, parse_purchase_quote_file


def test_parse_money_decimal_accepts_supported_brazilian_and_dot_formats():
    assert parse_money_decimal('89.90') == Decimal('89.90')
    assert parse_money_decimal('89,90') == Decimal('89.90')
    assert parse_money_decimal('R$ 89,90') == Decimal('89.90')
    assert parse_money_decimal('R$89.90') == Decimal('89.90')
    assert parse_money_decimal('R$ 1.234,565') == Decimal('1234.57')


def test_parse_purchase_quote_csv_with_pandas_sep_detection(tmp_path):
    pd = pytest.importorskip('pandas')
    csv_path = tmp_path / 'arquivo.csv'
    csv_path.write_text(
        'epi;ca;fabricante;fornecedor;tamanho;qtd;valor_unitario\n'
        'Luva;39733;DANNY;DANNY;T:Nº34;2;R$ 89,90\n',
        encoding='utf-8-sig',
    )

    df_csv = pd.read_csv(csv_path, sep=None, engine='python', encoding='utf-8-sig')
    assert list(df_csv.columns) == ['epi', 'ca', 'fabricante', 'fornecedor', 'tamanho', 'qtd', 'valor_unitario']

    rows = parse_purchase_quote_file(csv_path.read_bytes(), csv_path.name)
    assert rows == [{
        'epi': 'Luva',
        'ca': '39733',
        'fabricante': 'DANNY',
        'fornecedor': 'DANNY',
        'tamanho': 'T:Nº34',
        'tamanho_luva': '',
        'tamanho_uniforme': '',
        'qtd': '2',
        'valor_unitario': '89.90',
    }]


def test_parse_purchase_quote_xlsx_with_openpyxl_engine(tmp_path):
    pytest.importorskip('openpyxl')
    pd = pytest.importorskip('pandas')
    xlsx_path = tmp_path / 'arquivo.xlsx'
    frame = pd.DataFrame([{
        'epi': 'Capacete',
        'ca': '498',
        'fabricante': 'MSA',
        'fornecedor': 'MSA DO BRASIL',
        'tamanho': 'T:Nº60',
        'qtd': 1,
        'valor_unitario': 'R$89.90',
    }])
    frame.to_excel(xlsx_path, index=False, engine='openpyxl')

    df_xlsx = pd.read_excel(xlsx_path, engine='openpyxl')
    assert df_xlsx.iloc[0]['epi'] == 'Capacete'

    rows = parse_purchase_quote_file(xlsx_path.read_bytes(), xlsx_path.name)
    assert rows[0]['valor_unitario'] == '89.90'
    assert rows[0]['qtd'] == '1'


def test_parse_purchase_quote_file_accepts_base64_payload_shape(tmp_path):
    pytest.importorskip('pandas')
    csv_path = tmp_path / 'arquivo.csv'
    csv_path.write_text('epi,ca,qtd,valor_unitario\nLuva,39733,2,89.90\n', encoding='utf-8-sig')
    encoded = base64.b64encode(csv_path.read_bytes())

    rows = parse_purchase_quote_file(base64.b64decode(encoded), csv_path.name)
    assert rows[0]['valor_unitario'] == '89.90'
