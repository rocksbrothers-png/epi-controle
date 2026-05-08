import io
import re
import unicodedata
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


MONEY_CENTS = Decimal('0.01')

QUOTE_COLUMN_ALIASES = {
    'epi': ['epi', 'nome_epi', 'descricao', 'item'],
    'ca': ['ca', 'certificado', 'ca_numero'],
    'fabricante': ['fabricante', 'manufacturer', 'marca'],
    'fornecedor': ['fornecedor', 'supplier', 'empresa_fornecedora'],
    'tamanho': ['tamanho', 'tam', 'size'],
    'tamanho_luva': ['tamanho_luva', 'luva', 'glove_size'],
    'tamanho_uniforme': ['tamanho_uniforme', 'uniforme', 'uniform_size'],
    'qtd': ['qtd', 'quantidade', 'qty', 'quantity'],
    # vlr_unit_r = normalized form of "Vlr Unit. (R$)" exported by this system
    'valor_unitario': ['valor_unitario', 'vlr_unit_r', 'vl_unit', 'preco_unitario', 'unit_price', 'valor', 'preco', 'price'],
}


def normalize_quote_header(value):
    text = str(value or '').strip().lower()
    text = unicodedata.normalize('NFD', text)
    text = ''.join(ch for ch in text if unicodedata.category(ch) != 'Mn')
    text = re.sub(r'[^a-z0-9]+', '_', text)
    return text.strip('_')


def clean_quote_cell(value):
    if value is None:
        return ''
    text = str(value).strip()
    if text.lower() in {'nan', 'none', 'null'}:
        return ''
    return text.strip('"\' ')


def parse_money_decimal(value):
    if value is None:
        return Decimal('0.00')
    if isinstance(value, Decimal):
        return value.quantize(MONEY_CENTS, rounding=ROUND_HALF_UP)
    text = str(value).strip()
    if not text:
        return Decimal('0.00')

    text = text.replace('\xa0', ' ')
    text = re.sub(r'(?i)\br\$\b|r\$', '', text)
    text = re.sub(r'\s+', '', text)
    text = re.sub(r'[^0-9,\.\-]', '', text)
    if not text or text in {'-', ',', '.', '-,', '-.'}:
        return Decimal('0.00')

    sign = '-' if text.startswith('-') else ''
    text = text.replace('-', '')
    comma_pos = text.rfind(',')
    dot_pos = text.rfind('.')

    if comma_pos >= 0 and dot_pos >= 0:
        decimal_sep = ',' if comma_pos > dot_pos else '.'
    elif comma_pos >= 0:
        decimal_sep = ','
    elif dot_pos >= 0:
        decimal_sep = '.'
    else:
        decimal_sep = ''

    if decimal_sep:
        parts = text.split(decimal_sep)
        fractional = parts[-1]
        integer = ''.join(parts[:-1]).replace(',', '').replace('.', '') or '0'
        normalized = f'{sign}{integer}.{fractional}'
    else:
        normalized = f"{sign}{text.replace(',', '').replace('.', '')}"

    try:
        return Decimal(normalized).quantize(MONEY_CENTS, rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ValueError(f'Valor monetário inválido: {value}') from exc


def parse_quantity(value, default=1):
    text = clean_quote_cell(value)
    if not text:
        return default
    text = text.replace('\xa0', '').replace(' ', '').replace(',', '.')
    try:
        parsed = Decimal(re.sub(r'[^0-9.\-]', '', text) or str(default))
    except InvalidOperation:
        return default
    quantity = int(parsed.to_integral_value(rounding=ROUND_HALF_UP))
    return quantity if quantity > 0 else default


def _read_quote_dataframe(file_bytes, filename):
    import pandas as pd

    suffix = Path(str(filename or '')).suffix.lower()
    buffer = io.BytesIO(file_bytes)
    if suffix == '.csv':
        for enc in ('utf-8-sig', 'cp1252', 'latin-1'):
            try:
                buffer.seek(0)
                return pd.read_csv(buffer, sep=None, engine='python', encoding=enc, dtype=str, keep_default_na=False)
            except UnicodeDecodeError:
                continue
        raise ValueError('Não foi possível decodificar o arquivo CSV. Tente exportar como XLSX.')
    if suffix == '.xlsx':
        return pd.read_excel(buffer, engine='openpyxl', dtype=str, keep_default_na=False)
    raise ValueError('Formato não suportado. Envie um arquivo CSV ou XLSX.')


def _build_column_map(normalized_columns):
    column_map = {}
    for key, aliases in QUOTE_COLUMN_ALIASES.items():
        found = next((alias for alias in aliases if alias in normalized_columns), None)
        if found:
            column_map[key] = normalized_columns.index(found)
    return column_map


def parse_purchase_quote_file(file_bytes, filename):
    dataframe = _read_quote_dataframe(file_bytes, filename)
    normalized_columns = [normalize_quote_header(col) for col in dataframe.columns]
    column_map = _build_column_map(normalized_columns)

    # If no columns matched the first row may be a metadata row (e.g. from our
    # own CSV export which prepends "Requisição #X;Unidade:...;Data:...").
    # Promote the first data row to become the header and retry.
    if not column_map and not dataframe.empty:
        dataframe.columns = [str(v) for v in dataframe.iloc[0]]
        dataframe = dataframe.iloc[1:].reset_index(drop=True)
        normalized_columns = [normalize_quote_header(col) for col in dataframe.columns]
        column_map = _build_column_map(normalized_columns)

    rows = []
    for values in dataframe.itertuples(index=False, name=None):
        def get_value(key):
            index = column_map.get(key)
            return clean_quote_cell(values[index]) if index is not None and index < len(values) else ''

        row = {
            'epi': get_value('epi'),
            'ca': get_value('ca'),
            'fabricante': get_value('fabricante'),
            'fornecedor': get_value('fornecedor'),
            'tamanho': get_value('tamanho'),
            'tamanho_luva': get_value('tamanho_luva'),
            'tamanho_uniforme': get_value('tamanho_uniforme'),
            'qtd': str(parse_quantity(get_value('qtd'))),
            'valor_unitario': f"{parse_money_decimal(get_value('valor_unitario')):.2f}",
        }
        if row['epi'] or row['ca']:
            rows.append(row)
    return rows
