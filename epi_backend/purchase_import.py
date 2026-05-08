import csv
import hashlib
import io
import json
import logging
import re
import unicodedata
from datetime import datetime, UTC
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


MONEY_CENTS = Decimal('0.01')
CSV_ENCODINGS = ('utf-8', 'utf-8-sig', 'cp1252', 'latin-1')
CSV_DELIMITERS = (';', ',', '\t')
IMPORT_DEBUG_DIR = Path('/tmp/import_debug')
IMPORT_LOG_DIR = Path('logs/imports')
LOGGER = logging.getLogger(__name__)

QUOTE_COLUMN_ALIASES = {
    'item_id': ['item_id', 'id_item', 'purchase_request_item_id', 'id_item_requisicao', 'id_requisicao_item'],
    'requisicao': ['requisicao', 'requisicao_demanda', 'demanda', 'request_id', 'purchase_request_id'],
    'unidade': ['unidade', 'unit', 'unit_name', 'nome_unidade'],
    'epi': ['epi', 'nome_epi', 'descricao', 'item'],
    'ca': ['ca', 'certificado', 'ca_numero'],
    'fabricante': ['fabricante', 'manufacturer', 'marca'],
    'fornecedor': ['fornecedor', 'supplier', 'empresa_fornecedora'],
    'colaborador': ['colaborador', 'employee', 'employee_name', 'funcionario', 'nome_colaborador'],
    'setor': ['setor', 'employee_sector', 'sector'],
    'origem': ['origem', 'origin'],
    'tamanho': ['tamanho', 'tam', 'size'],
    'tamanho_luva': ['tamanho_luva', 'luva', 'glove_size'],
    'tamanho_uniforme': ['tamanho_uniforme', 'uniforme', 'uniform_size'],
    'qtd': ['qtd', 'quantidade', 'qty', 'quantity'],
    # vlr_unit_r = normalized form of "Vlr Unit. (R$)" exported by this system
    'valor_unitario': ['valor_unitario', 'vlr_unit_r', 'vl_unit', 'preco_unitario', 'unit_price', 'valor', 'preco', 'price'],
    'total': ['total', 'total_r', 'valor_total', 'total_price'],
    'status_item': ['status_item', 'status'],
}
_ALIAS_LOOKUP = {alias: key for key, aliases in QUOTE_COLUMN_ALIASES.items() for alias in aliases}


def normalize_quote_header(value):
    text = str(value or '').replace('\ufeff', '').strip().lower()
    text = unicodedata.normalize('NFD', text)
    text = ''.join(ch for ch in text if unicodedata.category(ch) != 'Mn')
    text = re.sub(r'[^a-z0-9]+', '_', text)
    return text.strip('_')


def clean_quote_cell(value):
    if value is None:
        return ''
    text = str(value).replace('\ufeff', '').strip()
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

    original_text = text
    text = text.replace('\xa0', ' ')
    text = re.sub(r'(?i)\br\$\b|r\$', '', text)
    text = re.sub(r'\s+', '', text)
    text = re.sub(r'[^0-9,\.\-]', '', text)
    if not text or text in {'-', ',', '.', '-,', '-.'}:
        if re.search(r'\d', original_text):
            return Decimal('0.00')
        raise ValueError(f'Valor monetário inválido: {value}')

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


def _safe_debug_path(directory, filename, digest, suffix):
    directory.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r'[^A-Za-z0-9_.-]+', '_', Path(str(filename or 'import')).name)[:80] or 'import'
    return directory / f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_{digest[:12]}_{safe_name}{suffix}"


def _write_debug_artifacts(file_bytes, filename, diagnostics):
    digest = hashlib.sha256(file_bytes).hexdigest()
    copied_paths = []
    for directory in (IMPORT_DEBUG_DIR, IMPORT_LOG_DIR):
        try:
            copied = _safe_debug_path(directory, filename, digest, '.copy')
            copied.write_bytes(file_bytes)
            copied_paths.append(str(copied))
        except OSError as exc:
            diagnostics.setdefault('debug_errors', []).append(str(exc))
    diagnostics['debug_copies'] = copied_paths
    try:
        meta_path = _safe_debug_path(IMPORT_LOG_DIR, filename, digest, '.json')
        meta_path.write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2), encoding='utf-8')
        diagnostics['debug_metadata'] = str(meta_path)
    except OSError as exc:
        diagnostics.setdefault('debug_errors', []).append(str(exc))


def _structured_import_log(event, **payload):
    LOGGER.info('%s %s', event, json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _try_read_csv(file_bytes, filename, diagnostics):
    import pandas as pd

    attempts = []
    last_error = None
    for enc in CSV_ENCODINGS:
        try:
            decoded = file_bytes.decode(enc)
        except UnicodeDecodeError as exc:
            last_error = exc
            attempts.append({'encoding': enc, 'error': str(exc), 'accepted': False})
            continue

        for sep in CSV_DELIMITERS:
            try:
                preview_rows = list(csv.reader(io.StringIO(decoded), delimiter=sep))
                max_columns = max((len(row) for row in preview_rows), default=0)
                if max_columns <= 1 and sep != CSV_DELIMITERS[-1]:
                    attempts.append({'encoding': enc, 'delimiter': sep, 'columns': int(max_columns), 'accepted': False})
                    continue

                frame = pd.read_csv(
                    io.BytesIO(file_bytes),
                    sep=sep,
                    engine='python',
                    encoding=enc,
                    dtype=str,
                    keep_default_na=False,
                    header=None,
                    names=list(range(max_columns)) if max_columns else None,
                )
                diagnostics.update({'encoding': enc, 'delimiter': sep, 'raw_rows': int(frame.shape[0]), 'raw_columns': int(frame.shape[1])})
                attempts.append({'encoding': enc, 'delimiter': sep, 'columns': int(frame.shape[1]), 'accepted': True})
                diagnostics['attempts'] = attempts
                return frame
            except (UnicodeDecodeError, pd.errors.ParserError, csv.Error, ValueError) as exc:
                last_error = exc
                attempts.append({'encoding': enc, 'delimiter': sep, 'error': str(exc), 'accepted': False})
    diagnostics['attempts'] = attempts
    raise ValueError(f'Não foi possível ler o arquivo CSV. Último erro: {last_error}')


def _read_quote_dataframe(file_bytes, filename, diagnostics):
    import pandas as pd

    suffix = Path(str(filename or '')).suffix.lower()
    if file_bytes.startswith(b'\xef\xbb\xbf'):
        diagnostics['bom'] = 'utf-8-sig'
    if suffix == '.csv':
        return _try_read_csv(file_bytes, filename, diagnostics)
    if suffix == '.xlsx':
        frame = pd.read_excel(io.BytesIO(file_bytes), engine='openpyxl', dtype=str, keep_default_na=False, header=None)
        diagnostics.update({'encoding': 'xlsx', 'delimiter': 'xlsx', 'raw_rows': int(frame.shape[0]), 'raw_columns': int(frame.shape[1])})
        return frame
    raise ValueError('Formato não suportado. Envie um arquivo CSV ou XLSX.')


def _build_column_map(normalized_columns):
    column_map = {}
    for index, normalized in enumerate(normalized_columns):
        key = _ALIAS_LOOKUP.get(normalized)
        if key and key not in column_map:
            column_map[key] = index
    return column_map


def _header_match_count(values):
    return sum(1 for value in values if normalize_quote_header(value) in _ALIAS_LOOKUP)


def _promote_detected_header(dataframe, diagnostics):
    if dataframe.empty:
        diagnostics.update({'headers': [], 'header_row_index': None, 'metadata_rows': 0})
        return dataframe, []

    best_index = None
    best_score = 0
    max_scan = min(len(dataframe), 25)
    for index in range(max_scan):
        values = list(dataframe.iloc[index])
        score = _header_match_count(values)
        if score > best_score:
            best_index = index
            best_score = score
        if score >= 2:
            break

    if best_index is None or best_score == 0:
        headers = [str(col) for col in dataframe.iloc[0]]
        metadata_rows = 0
        data = dataframe.iloc[1:].reset_index(drop=True)
    else:
        headers = [str(col) for col in dataframe.iloc[best_index]]
        metadata_rows = int(best_index)
        data = dataframe.iloc[best_index + 1:].reset_index(drop=True)
    data.columns = headers
    normalized_columns = [normalize_quote_header(col) for col in data.columns]
    diagnostics.update({'headers': headers, 'normalized_headers': normalized_columns, 'header_row_index': best_index, 'metadata_rows': metadata_rows})
    return data, normalized_columns


def parse_purchase_quote_file(file_bytes, filename):
    diagnostics = {
        'filename': str(filename or ''),
        'started_at': datetime.now(UTC).isoformat(),
        'bom': '',
        'ignored_rows': [],
        'row_errors': [],
    }
    _structured_import_log('import.started', filename=diagnostics['filename'], bytes=len(file_bytes))
    _write_debug_artifacts(file_bytes, filename, diagnostics)

    dataframe = _read_quote_dataframe(file_bytes, filename, diagnostics)
    dataframe, normalized_columns = _promote_detected_header(dataframe, diagnostics)
    column_map = _build_column_map(normalized_columns)
    diagnostics['column_map'] = column_map

    rows = []
    for row_index, values in enumerate(dataframe.itertuples(index=False, name=None), start=1 + int(diagnostics.get('metadata_rows') or 0) + 1):
        def get_value(key):
            index = column_map.get(key)
            return clean_quote_cell(values[index]) if index is not None and index < len(values) else ''

        raw_epi = get_value('epi')
        raw_ca = get_value('ca')
        if not raw_epi and not raw_ca:
            diagnostics['ignored_rows'].append({'line': row_index, 'reason': 'blank_or_without_epi_ca'})
            continue

        try:
            quantity = parse_quantity(get_value('qtd'))
            unit_price = parse_money_decimal(get_value('valor_unitario'))
            parsed_total = parse_money_decimal(get_value('total')) if get_value('total') else (unit_price * quantity).quantize(MONEY_CENTS, rounding=ROUND_HALF_UP)
            row = {
                'line': row_index,
                'item_id': get_value('item_id'),
                'requisicao': get_value('requisicao'),
                'unidade': get_value('unidade'),
                'epi': raw_epi,
                'ca': raw_ca,
                'fabricante': get_value('fabricante'),
                'fornecedor': get_value('fornecedor'),
                'colaborador': get_value('colaborador'),
                'setor': get_value('setor'),
                'origem': get_value('origem'),
                'tamanho': get_value('tamanho'),
                'tamanho_luva': get_value('tamanho_luva'),
                'tamanho_uniforme': get_value('tamanho_uniforme'),
                'qtd': str(quantity),
                'valor_unitario': f'{unit_price:.2f}',
                'total': f'{parsed_total:.2f}',
                'status_item': get_value('status_item'),
            }
            rows.append(row)
            _structured_import_log(
                'import.row_parsed',
                line=row_index,
                colaborador=row['colaborador'],
                ca=row['ca'],
                epi=row['epi'],
                valor_unitario=row['valor_unitario'],
                total=row['total'],
            )
        except Exception as exc:
            diagnostics['row_errors'].append({'line': row_index, 'reason': str(exc)})
            _structured_import_log('import.row_failed', line=row_index, colaborador=get_value('colaborador'), ca=raw_ca, epi=raw_epi, reason=str(exc))

    diagnostics.update({'completed_at': datetime.now(UTC).isoformat(), 'parsed_rows': len(rows), 'ignored_count': len(diagnostics['ignored_rows']), 'error_count': len(diagnostics['row_errors'])})
    _write_debug_artifacts(file_bytes, filename, diagnostics)
    _structured_import_log('import.completed', filename=diagnostics['filename'], rows=len(rows), ignored=diagnostics['ignored_count'], errors=diagnostics['error_count'], encoding=diagnostics.get('encoding'), delimiter=diagnostics.get('delimiter'))
    return rows
