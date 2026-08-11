"""Registry de fontes do Centro de Migração (ADR-0003 §2.2).

Toda fonte — XLSX, CSV, ODS, JSON, XML, TXT e (fases 5/6) banco, API REST,
GraphQL e exports de ERP — devolve a MESMA estrutura ``SourceDataset``. O
resto do pipeline (mapeamento, validação, escrita, rollback) não sabe de
onde o dado veio. É isso que torna barato adicionar fonte nova depois.

A etapa 3 do assistente ("leitura automática") vive aqui: detectar
codificação, separador, planilha, colunas, tipos e quantidade de registros.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

# Limites de segurança (ADR-0003 §7). Um arquivo maior que isso é recusado
# antes de qualquer parsing — não adianta validar depois de já ter alocado.
MAX_SOURCE_BYTES = 25 * 1024 * 1024
MAX_SOURCE_ROWS = 200_000

# Acima deste volume a importação não deve rodar de forma síncrona
# (ADR-0003 §8). Na Fase 1 o job é marcado e reportado; o executor em
# background entra na Fase 4.
BACKGROUND_THRESHOLD_ROWS = 100_000

FILE_SOURCE_KINDS = ('xlsx', 'csv', 'ods', 'json', 'xml', 'txt')

# Fontes declaradas no catálogo comercial mas ainda não implementadas
# (ADR-0003 §9, fases 5 e 6). Listadas para a UI poder exibi-las como
# "em breve" em vez de simplesmente não existirem.
ROADMAP_SOURCE_KINDS = (
    'sqlserver', 'mysql', 'postgresql', 'sqlite', 'oracle',
    'rest', 'graphql', 'sap', 'totvs', 'senior', 'benner', 'dominio',
)

# Sistema de origem gravado no registro importado (issue #211).
#
# É DERIVADO do `source_kind`, não pedido ao usuário: a alternativa seria um
# campo novo na API que alguém preencheria errado, ou não preencheria. Aqui,
# uma fonte nova só precisa entrar neste mapa uma vez e todo registro que ela
# produzir nasce carimbado corretamente.
#
# Distinto de `origin`: `origin` responde "veio de fora?" e tem duas respostas
# estáveis; `source_system` responde "de fora a partir de quê?" e o inventário
# cresce a cada integração. Misturar os dois obrigaria a mexer na semântica de
# `origin` toda vez que um ERP novo entrasse.
_SOURCE_SYSTEM_BY_KIND = {
    'sap': 'sap',
    'totvs': 'totvs',
    'senior': 'senior',
    'benner': 'benner',
    'dominio': 'dominio',
    'rest': 'api',
    'graphql': 'api',
    'sqlserver': 'banco',
    'mysql': 'banco',
    'postgresql': 'banco',
    'sqlite': 'banco',
    'oracle': 'banco',
}


def source_system_for(source_kind: str) -> str:
    """Sistema de origem correspondente a um ``source_kind``.

    Arquivo (xlsx/csv/ods/json/xml/txt) é sempre ``'planilha'`` — do ponto de
    vista da auditoria, o que importa é que um humano exportou e enviou um
    arquivo, não qual extensão ele tinha.

    Um `source_kind` desconhecido devolve o próprio valor normalizado em vez de
    string vazia: registro carimbado com uma fonte estranha é diagnosticável;
    registro sem carimbo nenhum é indistinguível de um bug.
    """
    kind = str(source_kind or '').strip().lower()
    if not kind:
        return ''
    if kind in FILE_SOURCE_KINDS:
        return 'planilha'
    return _SOURCE_SYSTEM_BY_KIND.get(kind, kind)


_ENCODING_CANDIDATES = ('utf-8-sig', 'utf-8', 'latin-1', 'cp1252')
_DELIMITER_CANDIDATES = (';', ',', '\t', '|')


@dataclass
class SourceDataset:
    columns: list[str]
    rows: list[dict]
    diagnostics: list[dict] = field(default_factory=list)
    detected: dict = field(default_factory=dict)

    @property
    def total_rows(self) -> int:
        return len(self.rows)

    def signature(self) -> str:
        """Assinatura do layout de origem: mesma ordem de colunas = mesma
        assinatura. É a chave do mapeamento salvo (ADR-0003 §2.3) — o que
        faz a segunda importação do mesmo relatório legado já vir mapeada."""
        joined = '|'.join(_normalize_header(column) for column in self.columns)
        return hashlib.sha256(joined.encode('utf-8')).hexdigest()[:32]

    def sample(self, limit: int = 10) -> list[dict]:
        return self.rows[:limit]


def _normalize_header(value: object) -> str:
    text = str(value or '').strip().lower()
    for accented, plain in (
        ('á', 'a'), ('à', 'a'), ('ã', 'a'), ('â', 'a'), ('ä', 'a'),
        ('é', 'e'), ('ê', 'e'), ('è', 'e'), ('ë', 'e'),
        ('í', 'i'), ('î', 'i'), ('ì', 'i'), ('ï', 'i'),
        ('ó', 'o'), ('ô', 'o'), ('õ', 'o'), ('ò', 'o'), ('ö', 'o'),
        ('ú', 'u'), ('û', 'u'), ('ù', 'u'), ('ü', 'u'),
        ('ç', 'c'), ('ñ', 'n'),
    ):
        text = text.replace(accented, plain)
    return re.sub(r'[^a-z0-9]+', ' ', text).strip()


def detect_encoding(raw: bytes) -> str:
    for candidate in _ENCODING_CANDIDATES:
        try:
            raw.decode(candidate)
            return candidate
        except (UnicodeDecodeError, LookupError):
            continue
    return 'latin-1'


def detect_delimiter(text: str) -> str:
    head = '\n'.join(text.splitlines()[:20])
    if not head:
        return ','
    try:
        return csv.Sniffer().sniff(head, delimiters=''.join(_DELIMITER_CANDIDATES)).delimiter
    except csv.Error:
        # Sniffer falha com frequência em export de ERP (aspas irregulares,
        # linhas de cabeçalho decorativas). Fallback determinístico: o
        # candidato mais frequente na primeira linha.
        first = head.splitlines()[0]
        counts = {candidate: first.count(candidate) for candidate in _DELIMITER_CANDIDATES}
        best = max(counts, key=lambda key: counts[key])
        return best if counts[best] else ','


def infer_column_types(rows: list[dict], columns: list[str]) -> dict[str, str]:
    """Tipo aparente por coluna, só para exibir no preview — a validação
    real é do descritor da entidade (catalog.py), não daqui."""
    types: dict[str, str] = {}
    for column in columns:
        values = [str(row.get(column) or '').strip() for row in rows[:200]]
        values = [value for value in values if value]
        if not values:
            types[column] = 'vazio'
            continue
        if all(re.fullmatch(r'-?\d+', value) for value in values):
            types[column] = 'inteiro'
        elif all(re.fullmatch(r'-?\d+[.,]\d+', value) for value in values):
            types[column] = 'decimal'
        elif all(re.fullmatch(r'\d{2}[/-]\d{2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}.*', value) for value in values):
            types[column] = 'data'
        else:
            types[column] = 'texto'
    return types


def _finalize(columns: list[str], rows: list[dict], detected: dict) -> SourceDataset:
    columns = [str(column).strip() for column in columns if str(column).strip()]
    if not columns:
        raise ValueError('Não foi possível identificar as colunas do arquivo.')
    if len(rows) > MAX_SOURCE_ROWS:
        raise ValueError(
            f'Arquivo com {len(rows)} registros excede o limite de {MAX_SOURCE_ROWS} por importação.'
        )
    detected = dict(detected)
    detected.update({
        'total_rows': len(rows),
        'column_count': len(columns),
        'column_types': infer_column_types(rows, columns),
        'requires_background': len(rows) >= BACKGROUND_THRESHOLD_ROWS,
    })
    diagnostics = []
    if detected['requires_background']:
        diagnostics.append({
            'level': 'warning',
            'code': 'requires_background',
            'message': (
                f'{len(rows)} registros: acima de {BACKGROUND_THRESHOLD_ROWS} a importação '
                'deve rodar em segundo plano (disponível na fase 4).'
            ),
        })
    return SourceDataset(columns=columns, rows=rows, diagnostics=diagnostics, detected=detected)


def _read_delimited(raw: bytes, *, kind: str) -> SourceDataset:
    encoding = detect_encoding(raw)
    text = raw.decode(encoding, errors='replace')
    delimiter = detect_delimiter(text)
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    columns = [str(name).strip() for name in (reader.fieldnames or [])]
    rows = [{key: row.get(key) for key in columns} for row in reader]
    return _finalize(columns, rows, {'encoding': encoding, 'delimiter': delimiter, 'kind': kind})


def _read_spreadsheet(raw: bytes, *, kind: str, sheet: str | None = None) -> SourceDataset:
    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover - dependência já é do projeto
        raise ValueError('Leitura de planilha indisponível: pandas não instalado.') from exc
    engine = 'odf' if kind == 'ods' else 'openpyxl'
    try:
        book = pd.read_excel(io.BytesIO(raw), sheet_name=None, engine=engine, dtype=str)
    except Exception as exc:
        raise ValueError(f'Não foi possível ler a planilha: {exc}') from exc
    if not book:
        raise ValueError('A planilha não possui nenhuma aba legível.')
    sheet_names = list(book.keys())
    chosen = sheet if sheet in book else sheet_names[0]
    frame = book[chosen].fillna('')
    columns = [str(column).strip() for column in frame.columns]
    rows = frame.to_dict(orient='records')
    rows = [{str(key).strip(): value for key, value in row.items()} for row in rows]
    return _finalize(columns, rows, {'kind': kind, 'sheet': chosen, 'sheets': sheet_names})


def _read_json(raw: bytes) -> SourceDataset:
    encoding = detect_encoding(raw)
    try:
        payload = json.loads(raw.decode(encoding, errors='replace'))
    except json.JSONDecodeError as exc:
        raise ValueError(f'JSON inválido: {exc}') from exc
    if isinstance(payload, dict):
        # Export de API costuma vir embrulhado: {"data": [...]} / {"items": [...]}.
        for key in ('data', 'items', 'records', 'rows', 'results'):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
        else:
            payload = [payload]
    if not isinstance(payload, list):
        raise ValueError('JSON precisa conter uma lista de registros.')
    rows = [row for row in payload if isinstance(row, dict)]
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(str(key))
    return _finalize(columns, rows, {'encoding': encoding, 'kind': 'json'})


def _read_xml(raw: bytes) -> SourceDataset:
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError(f'XML inválido: {exc}') from exc
    records = list(root)
    rows: list[dict] = []
    columns: list[str] = []
    for record in records:
        row: dict = {}
        # Atributo e elemento-filho são tratados igual: export de ERP usa os
        # dois formatos de forma intercambiável.
        row.update({str(key): value for key, value in record.attrib.items()})
        for child in record:
            row[str(child.tag)] = (child.text or '').strip()
        if not row:
            continue
        rows.append(row)
        for key in row:
            if key not in columns:
                columns.append(key)
    return _finalize(columns, rows, {'kind': 'xml', 'root': root.tag})


def read_source(kind: str, raw: bytes, *, sheet: str | None = None) -> SourceDataset:
    """Ponto único de entrada de qualquer fonte de arquivo."""
    kind = str(kind or '').strip().lower()
    if not isinstance(raw, (bytes, bytearray)):
        raise ValueError('Conteúdo do arquivo ausente.')
    if len(raw) > MAX_SOURCE_BYTES:
        raise ValueError(
            f'Arquivo de {len(raw)} bytes excede o limite de {MAX_SOURCE_BYTES} bytes.'
        )
    if not raw:
        raise ValueError('Arquivo vazio.')
    if kind in ROADMAP_SOURCE_KINDS:
        raise ValueError(
            f'A origem "{kind}" ainda não está disponível '
            '(prevista para as fases 5/6 do Centro de Migração).'
        )
    if kind in ('csv', 'txt'):
        return _read_delimited(bytes(raw), kind=kind)
    if kind in ('xlsx', 'ods'):
        return _read_spreadsheet(bytes(raw), kind=kind, sheet=sheet)
    if kind == 'json':
        return _read_json(bytes(raw))
    if kind == 'xml':
        return _read_xml(bytes(raw))
    raise ValueError(f'Origem de dados não suportada: {kind!r}.')


def source_hash(raw: bytes) -> str:
    """Hash do arquivo — auditoria (ADR-0003 §6) e detecção de reimportação
    acidental do mesmo arquivo."""
    return hashlib.sha256(bytes(raw)).hexdigest()


def list_sources() -> list[dict]:
    return (
        [{'kind': kind, 'enabled': True, 'phase': '1'} for kind in FILE_SOURCE_KINDS]
        + [{'kind': kind, 'enabled': False, 'phase': '5/6'} for kind in ROADMAP_SOURCE_KINDS]
    )
