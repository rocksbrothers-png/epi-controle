import base64
from decimal import Decimal

import pytest

import epi_backend.purchase_import as purchase_import
from epi_backend.purchase_import import parse_money_decimal, parse_purchase_quote_file


def _redirect_import_debug(monkeypatch, tmp_path):
    monkeypatch.setattr(purchase_import, 'IMPORT_DEBUG_DIR', tmp_path / 'tmp_import_debug')
    monkeypatch.setattr(purchase_import, 'IMPORT_LOG_DIR', tmp_path / 'logs_imports')


def test_parse_money_decimal_accepts_supported_brazilian_and_dot_formats():
    assert parse_money_decimal('89.90') == Decimal('89.90')
    assert parse_money_decimal('89,90') == Decimal('89.90')
    assert parse_money_decimal('R$ 89,90') == Decimal('89.90')
    assert parse_money_decimal('R$89.90') == Decimal('89.90')
    assert parse_money_decimal('R$ 1.234,565') == Decimal('1234.57')


def test_parse_purchase_quote_csv_with_pandas_sep_detection(tmp_path, monkeypatch):
    _redirect_import_debug(monkeypatch, tmp_path)
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
    assert rows[0] == {
        'line': 2,
        'item_id': '',
        'requisicao': '',
        'unidade': '',
        'epi': 'Luva',
        'ca': '39733',
        'fabricante': 'DANNY',
        'fornecedor': 'DANNY',
        'colaborador': '',
        'setor': '',
        'origem': '',
        'tamanho': 'T:Nº34',
        'tamanho_luva': '',
        'tamanho_uniforme': '',
        'qtd': '2',
        'valor_unitario': '89.90',
        'total': '179.80',
        'status_item': '',
    }


def test_parse_purchase_quote_xlsx_with_openpyxl_engine(tmp_path, monkeypatch):
    _redirect_import_debug(monkeypatch, tmp_path)
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


def test_parse_purchase_quote_file_accepts_base64_payload_shape(tmp_path, monkeypatch):
    _redirect_import_debug(monkeypatch, tmp_path)
    pytest.importorskip('pandas')
    csv_path = tmp_path / 'arquivo.csv'
    csv_path.write_text('epi,ca,qtd,valor_unitario\nLuva,39733,2,89.90\n', encoding='utf-8-sig')
    encoded = base64.b64encode(csv_path.read_bytes())

    rows = parse_purchase_quote_file(base64.b64decode(encoded), csv_path.name)
    assert rows[0]['valor_unitario'] == '89.90'


def test_parse_purchase_quote_preserves_same_ca_for_multiple_collaborators(tmp_path, monkeypatch):
    _redirect_import_debug(monkeypatch, tmp_path)
    pytest.importorskip('pandas')
    csv_path = tmp_path / 'duplicados.csv'
    csv_path.write_text(
        'Item ID;Unidade;EPI;CA;Fornecedor;Colaborador;Origem;Tamanho;Qtd;Vlr Unit. (R$)\n'
        '10;Matriz;Luva nitrilica;39733;Fornecedor A;Ana;Colaborador;P;1;89,90\n'
        '11;Filial;Luva nitrilica;39733;Fornecedor A;Bruno;Colaborador;M;2;90,10\n'
        '12;Matriz;Luva nitrilica;39733;Fornecedor B;Carla;Colaborador;G;3;R$ 91,20\n',
        encoding='utf-8',
    )

    rows = parse_purchase_quote_file(csv_path.read_bytes(), csv_path.name)
    assert [row['item_id'] for row in rows] == ['10', '11', '12']
    assert [row['colaborador'] for row in rows] == ['Ana', 'Bruno', 'Carla']
    assert [row['ca'] for row in rows] == ['39733', '39733', '39733']
    assert [row['valor_unitario'] for row in rows] == ['89.90', '90.10', '91.20']
    assert [row['total'] for row in rows] == ['89.90', '180.20', '273.60']


@pytest.mark.parametrize('encoding', ['utf-8', 'latin-1', 'cp1252'])
def test_parse_purchase_quote_csv_encoding_fallbacks(tmp_path, monkeypatch, encoding):
    _redirect_import_debug(monkeypatch, tmp_path)
    pytest.importorskip('pandas')
    csv_path = tmp_path / f'{encoding}.csv'
    csv_path.write_text(
        'epi;ca;fornecedor;colaborador;qtd;valor_unitario\n'
        'Óculos;123;São José;João;1;R$ 89,90\n',
        encoding=encoding,
    )

    rows = parse_purchase_quote_file(csv_path.read_bytes(), csv_path.name)
    assert rows[0]['epi'] == 'Óculos'
    assert rows[0]['fornecedor'] == 'São José'
    assert rows[0]['colaborador'] == 'João'
    assert rows[0]['valor_unitario'] == '89.90'


def test_parse_purchase_quote_logs_partially_invalid_rows_without_suppressing_valid_duplicates(tmp_path, monkeypatch):
    _redirect_import_debug(monkeypatch, tmp_path)
    pytest.importorskip('pandas')
    csv_path = tmp_path / 'parcialmente_invalidas.csv'
    csv_path.write_text(
        'epi;ca;colaborador;qtd;valor_unitario\n'
        'Luva;39733;Ana;1;89,90\n'
        'Luva;39733;Bruno;2;valor inválido\n'
        'Luva;39733;Carla;3;91,20\n',
        encoding='utf-8',
    )

    rows = parse_purchase_quote_file(csv_path.read_bytes(), csv_path.name)
    assert [row['colaborador'] for row in rows] == ['Ana', 'Carla']
    assert [row['valor_unitario'] for row in rows] == ['89.90', '91.20']


def test_parse_purchase_quote_skips_only_invalid_or_blank_rows_without_dropping_duplicates(tmp_path, monkeypatch):
    _redirect_import_debug(monkeypatch, tmp_path)
    pytest.importorskip('pandas')
    csv_path = tmp_path / 'metadados.csv'
    csv_path.write_text(
        'Requisição #55;Unidade: Matriz;Data: 2026-05-08\n'
        'epi;ca;colaborador;tamanho;qtd;valor_unitario\n'
        'Luva;39733;Ana;P;1;89.90\n'
        '; ; ; ; ;\n'
        'Luva;39733;Bruno;M;2;89,90\n',
        encoding='utf-8-sig',
    )

    rows = parse_purchase_quote_file(csv_path.read_bytes(), csv_path.name)
    assert [row['colaborador'] for row in rows] == ['Ana', 'Bruno']
    assert [row['tamanho'] for row in rows] == ['P', 'M']
    assert len(rows) == 2
