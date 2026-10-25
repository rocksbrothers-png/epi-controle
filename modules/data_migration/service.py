"""Serviço do Centro de Migração de Dados (ADR-0003).

Responsabilidades: ciclo de vida do job, as 6 estratégias de importação, a
aplicação gravando antes/depois por linha, e o rollback.

Nota de segurança que atravessa o arquivo (ADR-0003 §7): **todo** nome de
tabela e de coluna usado em SQL aqui vem do catálogo declarativo
(``catalog.py``), nunca do arquivo importado nem do payload do cliente.
Valores vão sempre por parâmetro. É a allowlist que torna injeção de SQL
estruturalmente impossível neste caminho.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps

from epi_backend import db as db_module
from epi_backend.db import row_to_dict, table_columns
from modules.data_migration.catalog import get_entity, require_enabled_entity
from modules.data_migration.mapper import (
    apply_mapping,
    normalize_manual_mapping,
    suggest_mapping,
)
from modules.data_migration.planning import (
    add_identity,
    identify,
    identity_fields,
    make_plan,
    plan_token,
)
from modules.data_migration.rollback import (
    RollbackConflict,
    evidence,
    lock_suffix,
    preflight,
    read_row,
)
from modules.data_migration.sources import read_source, source_hash

UTC = timezone.utc

STRATEGIES = (
    'dry_run',          # executa tudo sem gravar — é o preview
    'insert_only',      # só registros novos
    'update_only',      # só registros já existentes
    'upsert',           # insere novos e atualiza existentes
    'skip_duplicates',  # insere novos, ignora existentes em silêncio
    'overwrite',        # atualiza existentes sobrescrevendo todos os campos mapeados
)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec='seconds')


def _writable_columns(connection, descriptor) -> set[str]:
    """Interseção entre o descritor e as colunas que a tabela realmente tem.

    Protege contra tenant em versão de schema anterior: um campo novo do
    descritor simplesmente não é escrito, em vez de derrubar a importação
    inteira com "no such column" — mesmo padrão defensivo já usado em
    fetch_employees/get_employee_lifecycle.
    """
    available = set(table_columns(connection, descriptor.target_table))
    # `derived_columns` entram aqui — e só aqui. Elas são graváveis mas não
    # mapeáveis: o normalizador as calcula, a planilha nunca as traz. Ficar de
    # fora significava o valor calculado ser descartado na montagem do payload
    # (issue #169).
    # `computed_columns` seguem a mesma lógica das derivadas: a importação as
    # calcula por linha (hoje, `idempotency_key`) e elas precisam ser graváveis
    # sem serem mapeáveis.
    declared = (
        set(descriptor.field_names())
        | set(descriptor.derived_columns)
        | set(descriptor.computed_columns)
        # `service_columns` são gravadas pelo writer de domínio (não pela
        # planilha): entram aqui para que o snapshot `before` as capture e o
        # rollback as restaure junto da linha-alvo.
        | set(getattr(descriptor, 'service_columns', ()))
    )
    return {name for name in declared if name in available}


# ── Procedência do registro importado (issue #211) ──────────────────────────

#: Colunas de procedência gravadas em toda linha importada de uma entidade com
#: ``stamps_migration_origin``. Nomes ficam aqui, e não espalhados pelo código,
#: porque são a allowlist conferida contra o schema real antes de qualquer
#: INSERT — mesma disciplina do resto do motor (ADR-0003 §7).
ORIGIN_COLUMNS = ('origin', 'source_system', 'migration_job_id')

#: Valor de ``deliveries.origin`` para o que o próprio sistema criou. É o
#: DEFAULT da coluna, então toda linha anterior à migração 023 já nasce com
#: ele — o que é factualmente verdadeiro: nenhuma importação de entregas
#: jamais rodou antes deste lote.
ORIGIN_SYSTEM = 'sistema'
ORIGIN_MIGRATION = 'migracao'


def _origin_stamp(connection, descriptor, job_id: int, source_kind: str) -> dict:
    """Carimbo de procedência a aplicar em cada linha inserida.

    Vazio quando a entidade não declara ``stamps_migration_origin`` — o
    comportamento de todas as entidades dos lotes anteriores fica intacto.

    Colunas ausentes no schema do tenant são silenciosamente omitidas, pelo
    mesmo motivo de ``_writable_columns``: um tenant em versão anterior deve
    importar sem carimbo em vez de falhar inteiro.
    """
    if not getattr(descriptor, 'stamps_migration_origin', False):
        return {}
    from modules.data_migration.sources import source_system_for
    available = set(table_columns(connection, descriptor.target_table))
    stamp = {
        'origin': ORIGIN_MIGRATION,
        'source_system': source_system_for(source_kind),
        'migration_job_id': int(job_id),
    }
    return {name: value for name, value in stamp.items() if name in available}


def _migration_idempotency_key(row_number: int, payload: dict, source_fingerprint='') -> str:
    """Chave determinística que impede reimportação duplicar histórico.

    ``deliveries`` não tem UNIQUE de negócio — e não deveria ter: duas luvas
    para a mesma pessoa, do mesmo EPI, no mesmo dia são legítimas. A
    consequência é que reimportar o mesmo arquivo duplicaria o histórico sem
    que nada no banco reclamasse.

    A chave combina o conteúdo que identifica a entrega (colaborador, EPI,
    data) com a POSIÇÃO na planilha. Duas decisões nisso:

    - **inclui o número da linha** para que duas entregas legitimamente iguais
      dentro do mesmo arquivo continuem entrando as duas;
    - **não recebe o ``job_id``**, de propósito. Incluí-lo faria cada
      reimportação gerar chaves novas — o índice único nunca colidiria e a
      proteção não existiria. Ele fica de fora exatamente para que o segundo
      envio do mesmo arquivo bata no primeiro.

    Cai no índice único parcial já existente
    ``(company_id, idempotency_key) WHERE idempotency_key <> ''``.
    """
    import hashlib
    parts = '|'.join(
        str(payload.get(name) or '')
        for name in ('employee_id', 'epi_id', 'delivery_date', 'quantity')
    )
    if source_fingerprint:
        parts = json.dumps({k:v for k,v in payload.items() if not k.startswith('__')}, sort_keys=True, default=str)
    digest = hashlib.sha256(f'{source_fingerprint}|{parts}|{int(row_number)}'.encode()).hexdigest() if source_fingerprint else hashlib.sha256(f'{parts}|{int(row_number)}'.encode()).hexdigest()
    return f'{"mig2" if source_fingerprint else "mig"}:{digest[:40]}'


# ── Etapas 3 e 4 do assistente: leitura + mapeamento ────────────────────────

def analyze_source(kind: str, raw: bytes, entity: str, *, sheet: str | None = None) -> dict:
    """Lê a origem, detecta layout e já propõe o mapeamento.

    É o que alimenta as etapas 3 (leitura automática) e 4 (mapeamento) do
    assistente numa única chamada — o usuário sobe o arquivo e já vê as
    colunas reconhecidas.
    """
    descriptor = require_enabled_entity(entity)
    dataset = read_source(kind, raw, sheet=sheet)
    suggestion = suggest_mapping(descriptor, dataset.columns)
    return {
        'entity': descriptor.key,
        'entity_label': descriptor.label,
        'entity_enabled': descriptor.enabled,
        'columns': dataset.columns,
        'detected': dataset.detected,
        'diagnostics': dataset.diagnostics,
        'signature': dataset.signature(),
        'sample': dataset.sample(),
        'source_hash': source_hash(raw),
        **suggestion,
    }


def load_saved_mapping(connection, company_id: int, entity: str, signature: str) -> dict:
    """Mapeamento confirmado numa importação anterior do mesmo layout."""
    row = connection.execute(
        'SELECT mapping_json FROM migration_field_mappings '
        'WHERE company_id = %s AND entity = %s AND source_signature = %s LIMIT 1',
        (int(company_id), str(entity), str(signature)),
    ).fetchone()
    if not row:
        return {}
    try:
        return json.loads(row_to_dict(row).get('mapping_json') or '{}')
    except (TypeError, ValueError):
        return {}


def save_mapping(connection, company_id: int, entity: str, signature: str, mapping: dict) -> None:
    """Guarda o mapeamento para reaplicar automaticamente na próxima
    importação do mesmo layout (ADR-0003 §2.3)."""
    existing = connection.execute(
        'SELECT id, usage_count FROM migration_field_mappings '
        'WHERE company_id = %s AND entity = %s AND source_signature = %s LIMIT 1',
        (int(company_id), str(entity), str(signature)),
    ).fetchone()
    payload = json.dumps(mapping, ensure_ascii=False)
    if existing:
        current = row_to_dict(existing)
        connection.execute(
            'UPDATE migration_field_mappings SET mapping_json = %s, usage_count = %s, updated_at = %s '
            'WHERE id = %s',
            (payload, int(current.get('usage_count') or 0) + 1, _now(), int(current['id'])),
        )
    else:
        connection.execute(
            'INSERT INTO migration_field_mappings '
            '(company_id, entity, source_signature, mapping_json, usage_count, created_at, updated_at) '
            'VALUES (%s, %s, %s, %s, 1, %s, %s)',
            (int(company_id), str(entity), str(signature), payload, _now(), _now()),
        )


# ── Identidade dos registros já existentes no tenant ────────────────────────

def _existing_index(connection, descriptor, company_id: int, *, lock=False):
    keys = identity_fields(descriptor)
    if not keys:
        return {}
    extra = ['unit_id'] if descriptor.key == 'fornecedores' else (['quantity'] if descriptor.key == 'estoque' else [])
    columns = ', '.join(['id', *keys, *extra])
    version = '' if db_module._is_sqlite_connection(connection) else ', xmin::text AS __xmin, ctid::text AS __ctid'
    suffix = ' FOR UPDATE' if lock and not db_module._is_sqlite_connection(connection) else ''
    rows = connection.execute(
        f'SELECT {columns}{version} FROM {descriptor.target_table} WHERE company_id = %s ORDER BY id{suffix}',  # noqa: S608
        (int(company_id),),
    ).fetchall()
    index = {}
    for raw in rows:
        record = row_to_dict(raw)
        record['__version__'] = [record.pop('__xmin', ''), record.pop('__ctid', '')]
        add_identity(index, descriptor, record)
    return index


# ── Job ─────────────────────────────────────────────────────────────────────

def _reference_index(connection, table: str, name_column: str, company_id: int, *, lock=False) -> dict[str, list[int]]:
    """Mapa ``nome normalizado -> [ids]`` da tabela, **dentro do tenant**.

    Devolve lista, não id único, para que ambiguidade (duas unidades com o
    mesmo nome na mesma empresa) seja detectável em vez de resolvida em
    silêncio para a primeira que aparecer.

    O filtro por ``company_id`` é o que impede que "Produção" de um tenant
    resolva para a unidade de outro.
    """
    rows = connection.execute(
        f'SELECT id, {name_column} FROM {table} WHERE company_id = %s ORDER BY id'
        + (' FOR SHARE' if lock and not db_module._is_sqlite_connection(connection) else ''),  # noqa: S608 - allowlist do catálogo
        (int(company_id),),
    ).fetchall()
    index: dict[str, list[int]] = {}
    for row in rows:
        data = row_to_dict(row)
        key = normalize_reference(data.get(name_column))
        if key:
            index.setdefault(key, []).append(int(data['id']))
    return index


def normalize_reference(value: object) -> str:
    """Comparação tolerante ao que vem de planilha: caixa, espaços nas pontas,
    espaços internos repetidos e acentuação.

    "  PRODUÇÃO " e "producao" precisam encontrar a mesma unidade — é o caso
    normal de um export legado digitado à mão ao longo dos anos.
    """
    text = ' '.join(str(value or '').strip().lower().split())
    for accented, plain in (
        ('á', 'a'), ('à', 'a'), ('ã', 'a'), ('â', 'a'), ('ä', 'a'),
        ('é', 'e'), ('ê', 'e'), ('è', 'e'), ('ë', 'e'),
        ('í', 'i'), ('î', 'i'), ('ì', 'i'), ('ï', 'i'),
        ('ó', 'o'), ('ô', 'o'), ('õ', 'o'), ('ò', 'o'), ('ö', 'o'),
        ('ú', 'u'), ('û', 'u'), ('ù', 'u'), ('ü', 'u'),
        ('ç', 'c'), ('ñ', 'n'),
    ):
        text = text.replace(accented, plain)
    return text


def resolve_references(connection, descriptor, company_id: int, records: list[dict], *, lock=False) -> list[dict]:
    """Converte nome → id nos campos com ``resolves_to``.

    O arquivo legado traz "Produção", não o id interno. Regras:

    - valor já numérico é aceito como id, mas **só se pertencer ao tenant** —
      um id de outra empresa é tratado como desconhecido;
    - nome que resolve para exatamente um registro vira o id;
    - nome desconhecido ou **ambíguo** deixa o campo vazio e guarda o valor
      original em ``__unresolved__`` para o preview transformar em erro de
      linha, com o texto exato da planilha, antes de qualquer gravação.
    """
    resolvable = [spec for spec in descriptor.fields if spec.resolves_to]
    if not resolvable:
        return records
    indexes = {
        spec.name: _reference_index(connection, spec.resolves_to[0], spec.resolves_to[1], company_id, lock=lock)
        for spec in resolvable
    }
    known_ids = {
        spec.name: {value for ids in indexes[spec.name].values() for value in ids}
        for spec in resolvable
    }
    resolved = []
    for record in records:
        updated = dict(record)
        unresolved: dict[str, dict] = {}
        for spec in resolvable:
            raw = str(updated.get(spec.name) or '').strip()
            if not raw:
                continue
            if raw.isdigit() and spec.accepts_internal_id:
                # Id explícito só vale dentro do tenant (isolamento multi-tenant).
                named = indexes[spec.name].get(normalize_reference(raw), [])
                if named and set(named) != {int(raw)}:
                    updated[spec.name] = ''
                    unresolved[spec.name] = {'value': raw, 'reason': 'ambiguous', 'matches': len(set(named) | {int(raw)})}
                elif int(raw) in known_ids[spec.name]:
                    updated[spec.name] = int(raw)
                else:
                    updated[spec.name] = ''
                    unresolved[spec.name] = {'value': raw, 'reason': 'unknown'}
                continue
            matches = indexes[spec.name].get(normalize_reference(raw), [])
            if len(matches) == 1:
                updated[spec.name] = matches[0]
            else:
                updated[spec.name] = ''
                unresolved[spec.name] = {
                    'value': raw,
                    'reason': 'ambiguous' if len(matches) > 1 else 'unknown',
                    'matches': len(matches),
                }
        if unresolved:
            updated['__unresolved__'] = unresolved
        resolved.append(updated)
    return resolved


def _load_normalizer(descriptor):
    """Resolve o normalizador de domínio declarado no catálogo.

    Import tardio de propósito: o motor de migração não pode depender em
    tempo de import de cada módulo de domínio (evita ciclo e mantém o
    catálogo declarativo).
    """
    reference = getattr(descriptor, 'normalizer', '')
    if not reference:
        return None
    module_name, _, function_name = reference.partition(':')
    from importlib import import_module
    return getattr(import_module(module_name), function_name)


def _load_writer(descriptor):
    """Writer de domínio do descritor (late-ref "módulo:função").

    None = writer genérico (`_insert`/`_update`). Mesmo import tardio do
    normalizador: o motor não depende em tempo de import de cada módulo de
    domínio.
    """
    reference = getattr(descriptor, 'writer', '')
    if not reference:
        return None
    module_name, _, function_name = reference.partition(':')
    from importlib import import_module
    return getattr(import_module(module_name), function_name)


def _load_reverser(descriptor):
    """Reverser dos efeitos secundários do writer/post_write (late-ref), ou None."""
    reference = getattr(descriptor, 'reverser', '')
    if not reference:
        return None
    module_name, _, function_name = reference.partition(':')
    from importlib import import_module
    return getattr(import_module(module_name), function_name)


def _load_post_write(descriptor):
    """Hook de efeito secundário gravado APÓS a escrita genérica da linha-alvo
    (late-ref), ou None. Diferente do writer, não substitui a escrita."""
    reference = getattr(descriptor, 'post_write', '')
    if not reference:
        return None
    module_name, _, function_name = reference.partition(':')
    from importlib import import_module
    return getattr(import_module(module_name), function_name)


def apply_domain_rules(descriptor, records: list[dict]) -> list[dict]:
    """Passa cada linha pelas MESMAS regras do cadastro manual.

    Uma linha recusada não interrompe a análise: o motivo vira
    ``__domain_error__`` e o preview o transforma em erro daquela linha, com
    as outras seguindo normalmente.
    """
    normalizer = _load_normalizer(descriptor)
    if normalizer is None:
        return records
    processed = []
    for record in records:
        try:
            if descriptor.key == 'unidades' and not str(record.get('unit_type') or '').strip():
                error = ValueError('Tipo de unidade é obrigatório; nenhum tipo foi presumido.')
                error.field = 'unit_type'
                raise error
            updated = normalizer(record)
            updated.pop('__domain_error__', None)
        except ValueError as exc:
            updated = dict(record)
            updated['__domain_error__'] = str(exc)
            if getattr(exc, 'field', ''):
                updated['__domain_field__'] = exc.field
        processed.append(updated)
    return processed


@contextmanager
def _row_guard(connection):
    """Isola a gravação de UMA linha da transação do job.

    Sem isto o ``try/except`` por linha abaixo não isola nada no PostgreSQL:
    o primeiro erro aborta a transação inteira, todo comando seguinte falha
    com "current transaction is aborted" — inclusive o INSERT do diagnóstico
    e o UPDATE final do job — e a conexão volta envenenada para o pool,
    derrubando a *próxima* requisição, sem relação com esta. SQLite e
    PostgreSQL suportam SAVEPOINT.
    """
    connection.execute('SAVEPOINT sp_migration_row')
    try:
        yield
    except Exception:
        connection.execute('ROLLBACK TO SAVEPOINT sp_migration_row')
        connection.execute('RELEASE SAVEPOINT sp_migration_row')
        raise
    connection.execute('RELEASE SAVEPOINT sp_migration_row')


def create_job(connection, *, company_id, entity, source_kind, source_name, hash_value,
               strategy, actor, actor_ip='') -> int:
    cursor = connection.execute(
        'INSERT INTO migration_jobs '
        '(company_id, entity, source_kind, source_name, source_hash, strategy, status, '
        ' actor_user_id, actor_name, actor_ip, started_at, created_at) '
        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
        (
            int(company_id), str(entity), str(source_kind), str(source_name or ''), str(hash_value or ''),
            str(strategy), 'running', int(actor.get('id') or 0), str(actor.get('full_name') or ''),
            str(actor_ip or ''), _now(), _now(),
        ),
    )
    return int(cursor.lastrowid)


def _finish_job(connection, job_id: int, *, status: str, totals: dict, preview: dict, error: str = '') -> None:
    connection.execute(
        'UPDATE migration_jobs SET status = %s, total_rows = %s, processed_rows = %s, '
        'inserted_rows = %s, updated_rows = %s, skipped_rows = %s, failed_rows = %s, '
        'diagnostics_json = %s, error_message = %s, finished_at = %s WHERE id = %s',
        (
            status, int(totals.get('total', 0)), int(totals.get('processed', 0)),
            int(totals.get('inserted', 0)), int(totals.get('updated', 0)),
            int(totals.get('skipped', 0)), int(totals.get('failed', 0)),
            json.dumps(preview.get('diagnostics', [])[:500], ensure_ascii=False),
            str(error or ''), _now(), int(job_id),
        ),
    )


def _record(connection, *, job_id, company_id, row_number, action, table, target_id,
            before, after, error='', source_line=None) -> None:
    """Uma linha por registro tocado. É o insumo do rollback (ADR-0003 §2.4)."""
    if source_line is not None:
        after = {**(after or {}), "__source_line__": int(source_line)}
    connection.execute(
        'INSERT INTO migration_job_records '
        '(job_id, company_id, row_number, action, target_table, target_id, before_json, after_json, '
        ' error_message, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
        (
            int(job_id), int(company_id), int(row_number), str(action), str(table),
            int(target_id) if target_id else None,
            json.dumps(before, ensure_ascii=False, default=str) if before is not None else None,
            json.dumps(after, ensure_ascii=False, default=str) if after is not None else None,
            str(error or ''), _now(),
        ),
    )


class MigrationValidationError(ValueError):
    def __init__(self, message, preview):
        super().__init__(message)
        self.preview = preview
        self.diagnostics = preview.get('diagnostics', [])


def _history_duplicates(connection, descriptor, company_id, records, raw_hash):
    if not descriptor.computed_columns:
        return
    rows = connection.execute(
        'SELECT idempotency_key, migration_job_id FROM deliveries WHERE company_id = %s',
        (int(company_id),),
    ).fetchall()
    hashes = {row_to_dict(r)['id']: row_to_dict(r)['source_hash'] for r in connection.execute(
        'SELECT id, source_hash FROM migration_jobs WHERE company_id = %s', (int(company_id),),
    ).fetchall()}
    known = {row_to_dict(r)['idempotency_key']: hashes.get(row_to_dict(r).get('migration_job_id')) for r in rows}
    for number, record in enumerate(records, 1):
        payload = {k:v for k,v in record.items() if not k.startswith('__') and str(v or '').strip()}
        key = _migration_idempotency_key(number, payload, raw_hash)
        legacy = _migration_idempotency_key(number, payload)
        record['__idempotency_key__'] = key
        record['__already_imported__'] = key in known or (legacy in known and known[legacy] == raw_hash)


def _prepare(connection, descriptor, company_id, source_kind, raw, mapping, sheet, strategy, *, lock=False):
    dataset = read_source(source_kind, raw, sheet=sheet)
    try:
        normalized_mapping = normalize_manual_mapping(descriptor, mapping, dataset.columns)
    except ValueError as exc:
        missing = [f for f in descriptor.required_fields() if f not in (mapping or {}).values()] if isinstance(mapping, dict) else []
        preview = {'total_rows': len(dataset.rows), 'valid_rows': 0, 'invalid_rows': len(dataset.rows),
                   'will_insert': 0, 'will_update': 0, 'will_skip': 0, 'will_reject': len(dataset.rows),
                   'requires_mapping': len(dataset.rows), 'blocking': True, 'diagnostics': [{
                   'code': 'mapping_required', 'row': 0, 'field': ','.join(missing), 'entity': descriptor.key,
                   'severity': 'error', 'level': 'error', 'message': str(exc)}]}
        raise MigrationValidationError('Revise o mapeamento e os campos obrigatórios.', preview) from exc
    records = apply_mapping(normalized_mapping, dataset.rows)
    for number, record in enumerate(records):
        record['__source_line__'] = dataset.source_lines[number]
        record['__mapped_fields__'] = list(normalized_mapping.values())
    records = resolve_references(connection, descriptor, company_id, records, lock=lock)
    records = apply_domain_rules(descriptor, records)
    if descriptor.key == 'estoque':
        if lock:
            from modules.stock.eligibility import lock_stock_scope
            scopes = {(int(r['epi_id']), int(r['unit_id'])) for r in records
                      if str(r.get('epi_id', '')).isdigit() and str(r.get('unit_id', '')).isdigit()}
            for epi_id, unit_id in sorted(scopes):
                lock_stock_scope(connection, company_id, unit_id, epi_id)
        tracked_scopes = set()
        if db_module.table_exists(connection, 'epi_stock_items'):
            tracked_scopes = {(int(r['unit_id']), int(r['epi_id'])) for r in (
                row_to_dict(row) for row in connection.execute(
                    'SELECT DISTINCT unit_id, epi_id FROM epi_stock_items WHERE company_id = %s',
                    (int(company_id),),
                ).fetchall())}
        # O contrato agregado não pode descartar rastreabilidade física em
        # silêncio, mesmo se o mapeamento manual tentar ignorar a coluna.
        physical_fields = {
            'lote', 'lot', 'lot code', 'lot number', 'lot id', 'stock lot id', 'codigo lote', 'codigo do lote',
            'fabricacao', 'data fabricacao', 'data de fabricacao', 'manufacture date',
            'manufactured at', 'validade', 'validade fisica', 'data de validade',
            'expiry date', 'expiration date', 'expires at', 'physical expiry', 'physical expiry date',
            'physical validity unknown', 'expiry source', 'expiry evidence', 'traceability status',
        }
        for source, record in zip(dataset.rows, records):
            unsupported = [column for column, value in source.items()
                if normalize_reference(column).replace('_', ' ') in physical_fields
                and str(value if value is not None else '').strip()]
            if unsupported:
                record['__domain_field__'] = ','.join(unsupported)
                record['__domain_error__'] = (
                    'Lotes, fabricação e validade física não são suportados pelo contrato de saldo agregado. '
                    'Use um fluxo com rastreabilidade física antes de importar este arquivo.'
                )
            elif (record.get('unit_id'), record.get('epi_id')) in tracked_scopes:
                record['__domain_field__'] = 'quantity'
                record['__domain_error__'] = (
                    'Este estoque já possui peças rastreadas. Use ajustes por lote para preservar '
                    'fabricação, validade física, reservas e quantidades existentes.'
                )
    existing = _existing_index(connection, descriptor, company_id, lock=lock)
    raw_hash = source_hash(raw)
    _history_duplicates(connection, descriptor, company_id, records, raw_hash)
    preview = make_plan(descriptor, records, existing, strategy)
    if descriptor.key == 'estoque':
        preview['diagnostics'].append({
            'code': 'aggregate_stock_only', 'row': 0, 'field': '', 'entity': 'estoque',
            'level': 'warning', 'severity': 'warning',
            'message': 'Importa somente saldo agregado por movimento de ajuste. Não cria lotes ou peças com '
                       'validade física. Este saldo não se torna elegível para entrega sem conciliação física.',
        })
    for diagnostic in preview['diagnostics']:
        row = diagnostic.get('row', 0)
        if row:
            diagnostic['source_line'] = dataset.source_lines[row - 1]
    preview['diagnostics'].extend({**d, 'entity': descriptor.key} for d in dataset.diagnostics)
    for column in dataset.columns:
        if column not in normalized_mapping:
            preview['diagnostics'].append({'code': 'unmapped_column', 'row': 0, 'field': column,
                'entity': descriptor.key, 'level': 'warning', 'severity': 'warning',
                'message': 'Coluna não importada pelo mapeamento confirmado.'})
    preview.update(detected=dataset.detected, signature=dataset.signature(), requires_mapping=0)
    preview['preview_token'] = plan_token(company_id, descriptor.key, raw_hash, normalized_mapping, strategy, records, preview)
    return dataset, normalized_mapping, records, existing, preview


def _recover_transaction(function):
    @wraps(function)
    def execute(connection, *args, **kwargs):
        try:
            return function(connection, *args, **kwargs)
        except Exception:
            # Covers failures acquiring locks, creating the job and discovering
            # writable columns as well as the writer's structural-error path.
            connection.rollback()
            raise
    return execute


@_recover_transaction
def run_migration(connection, *, company_id, entity, source_kind, raw, mapping, strategy,
                  actor, source_name='', actor_ip='', sheet=None, persist_mapping=True,
                  preview_strategy='upsert', preview_token=None, audit_callback=None) -> dict:
    """Executa uma importação de ponta a ponta.

    ``strategy='dry_run'`` percorre o pipeline inteiro e devolve o preview
    **sem gravar nada** — é o que o assistente chama antes de confirmar.
    """
    strategy = str(strategy or 'dry_run').strip()
    if strategy not in STRATEGIES:
        raise ValueError(f'Estratégia de importação inválida: {strategy!r}.')

    # O mesmo gate vale para análise, prévia e aplicação.
    descriptor = require_enabled_entity(entity)

    apply_strategy = preview_strategy if strategy == 'dry_run' else strategy
    if apply_strategy not in STRATEGIES or apply_strategy == 'dry_run':
        raise ValueError('Estratégia da prévia inválida.')
    if strategy != 'dry_run' and not db_module._is_sqlite_connection(connection):
        # Serialize migration writes per tenant, without a new queue or schema.
        connection.execute('SELECT id FROM companies WHERE id = %s FOR UPDATE', (int(company_id),)).fetchone()
    try:
        dataset, normalized_mapping, records, existing, preview = _prepare(
            connection, descriptor, company_id, source_kind, raw, mapping, sheet, apply_strategy,
            lock=strategy != 'dry_run')
    except Exception:
        connection.rollback()
        raise
    if strategy == 'dry_run':
        return {'job_id': None, 'strategy': strategy, 'applied': False, 'preview': preview}
    if preview['blocking']:
        connection.rollback()
        raise MigrationValidationError('A importação foi bloqueada porque existem erros no arquivo. Revise a prévia.', preview)
    if preview_token is not None and preview_token != preview['preview_token']:
        connection.rollback()
        raise MigrationValidationError('A prévia mudou. Simule novamente e confira o resultado antes de confirmar.',
            {**preview, 'blocking': True, 'diagnostics': [*preview['diagnostics'], {
                'code': 'preview_stale', 'row': 0, 'field': '', 'entity': descriptor.key,
                'severity': 'error', 'level': 'error', 'message': 'Dados, mapeamento ou estratégia mudaram desde a prévia.'}]})

    job_id = create_job(
        connection, company_id=company_id, entity=descriptor.key, source_kind=source_kind,
        source_name=source_name, hash_value=source_hash(raw), strategy=strategy,
        actor=actor, actor_ip=actor_ip,
    )

    writable = _writable_columns(connection, descriptor)
    totals = {'total': len(records), 'processed': 0, 'inserted': 0, 'updated': 0, 'skipped': 0, 'failed': 0}

    # Só aplica defaults de colunas que a tabela realmente tem — mesmo
    # cuidado de _writable_columns com tenant em schema anterior.
    available = set(table_columns(connection, descriptor.target_table))
    defaults = {
        name: value
        for name, value in (getattr(descriptor, 'column_defaults', ()) or ())
        if name in available
    }
    stamp = _origin_stamp(connection, descriptor, job_id, source_kind)

    try:
        for index, record in enumerate(records, start=1):
            outcome = None
            classification = preview['row_classifications'][index - 1]
            try:
                # TODA a gravação da linha — snapshot, INSERT/UPDATE e o
                # próprio registro de auditoria — acontece dentro do mesmo
                # SAVEPOINT. Cobrir só o INSERT não bastava: se o _record
                # falhasse, a transação era abortada do mesmo jeito e o job
                # não conseguia sequer fechar (ADR-0003 §12.1).
                with _row_guard(connection):
                    outcome = _apply_row(
                        connection, descriptor, company_id, job_id, index, record,
                        strategy=strategy, writable=writable, defaults=defaults,
                        existing=existing, stamp=stamp, actor=actor,
                    )
            except Exception:  # linha ruim não derruba o job inteiro
                # Aqui a transação já voltou ao ponto anterior à linha, então
                # gravar o diagnóstico é seguro.
                totals['failed'] += 1
                totals['processed'] += 1
                diagnostic = {'code': 'database_row_rejected', 'row': index,
                    'source_line': record.get('__source_line__', index), 'field': '',
                    'entity': descriptor.key, 'severity': 'error', 'level': 'error',
                    'message': 'Registro rejeitado pelo banco. Revise identidade, referências e regras de domínio.'}
                preview['diagnostics'].append(diagnostic)
                classification.update(action='reject', classification='invalid', reason='database_row_rejected')
                _record(connection, job_id=job_id, company_id=company_id, row_number=index,
                        action='error', table=descriptor.target_table, target_id=None,
                        before=None, after=None, error=json.dumps(diagnostic, ensure_ascii=False))
                continue
            totals['processed'] += 1
            totals[outcome] += 1
            classification['action'] = {'inserted': 'insert', 'updated': 'update', 'skipped': 'skip'}[outcome]

        if persist_mapping:
            save_mapping(connection, company_id, descriptor.key, dataset.signature(), normalized_mapping)
        _reconcile_job(connection, job_id, company_id, totals, descriptor)
        status = ('completed_with_rejections' if totals['failed'] and totals['inserted'] + totals['updated'] + totals['skipped'] else
                  'failed' if totals['failed'] else 'completed')
        preview['actual_totals'] = dict(totals)
        preview['execution_status'] = status
        _finish_job(connection, job_id, status=status, totals=totals, preview=preview)
        if audit_callback:
            audit_callback(connection, {'job_id': job_id, 'strategy': strategy, 'applied': status != 'failed', 'status': status, 'totals': totals})
        connection.commit()
    except Exception as exc:
        # Falha estrutural (não de linha): a transação pode estar abortada, e
        # tentar escrever nela levantaria "current transaction is aborted",
        # mascarando o erro real e devolvendo conexão envenenada ao pool.
        # Desfaz tudo e registra o fracasso numa transação limpa.
        connection.rollback()
        _record_failed_job(
            connection, company_id=company_id, entity=descriptor.key, source_kind=source_kind,
            source_name=source_name, hash_value=source_hash(raw), strategy=strategy,
            actor=actor, actor_ip=actor_ip, totals=totals, error='Falha transacional; nenhuma alteração desta tentativa foi confirmada.',
        )
        connection.commit()
        raise ValueError('Falha transacional; nenhuma alteração desta tentativa foi confirmada.') from exc

    return {'job_id': job_id, 'strategy': strategy, 'applied': status != 'failed', 'status': status,
            'totals': totals, 'preview': preview, 'revalidated': True,
            'preview_matches_result': all(totals[name] == preview[key] for name, key in
                [('inserted', 'will_insert'), ('updated', 'will_update'), ('skipped', 'will_skip'), ('failed', 'will_reject')])}


def _persisted_evidence(connection, descriptor, company_id, target_id, payload, before=None):
    actual = read_row(connection, descriptor.target_table, company_id, target_id)
    if actual is None or any(str(actual['row'].get(name)) != str(value) for name,value in payload.items()):
        raise ValueError('Valores persistidos divergem da origem normalizada.')
    return evidence(payload, actual, before)


def _apply_row(connection, descriptor, company_id, job_id, index, record, *,
               strategy, writable, defaults, existing, stamp=None, actor=None) -> str:
    """Grava UMA linha e devolve o contador que ela alimenta.

    Roda inteira dentro do SAVEPOINT aberto por quem chama.
    """
    writer = _load_writer(descriptor)
    post_write = _load_post_write(descriptor)
    current, conflict = identify(existing, descriptor, record)
    if conflict:
        raise ValueError('Identidade mudou durante a execução.')
    payload = {
        name: value for name, value in record.items()
        if name in writable and (str(value or '').strip() or
            (strategy == 'overwrite' and name in record.get('__mapped_fields__', ())))
    }
    if not payload:
        _record(connection, source_line=record.get('__source_line__', index), job_id=job_id, company_id=company_id, row_number=index,
                action='skip', table=descriptor.target_table, target_id=None,
                before=None, after=None, error='Nenhum campo gravável.')
        return 'skipped'

    # Chave determinística de reimportação (issue #211). Calculada ANTES do
    # INSERT e verificada explicitamente: deixar o índice único estourar
    # contaria a linha como "falha", e uma reimportação inteira apareceria
    # para o usuário como um arquivo cheio de erros em vez de um arquivo já
    # importado. `skipped` é a resposta correta e é o que ele precisa ler.
    if 'idempotency_key' in getattr(descriptor, 'computed_columns', ()) \
            and 'idempotency_key' in writable:
        computed_key = record.get('__idempotency_key__') or _migration_idempotency_key(index, payload)
        duplicate = connection.execute(
            f'SELECT id FROM {descriptor.target_table} '  # noqa: S608 - allowlist do catálogo
            'WHERE company_id = %s AND idempotency_key = %s LIMIT 1',
            (int(company_id), computed_key),
        ).fetchone()
        if duplicate or record.get('__already_imported__'):
            _record(connection, source_line=record.get('__source_line__', index), job_id=job_id, company_id=company_id, row_number=index,
                    action='skip', table=descriptor.target_table,
                    target_id=int(row_to_dict(duplicate)['id']) if duplicate else None, before=None, after=None,
                    error='Linha já importada anteriormente (reimportação do mesmo arquivo).')
            return 'skipped'
        payload['idempotency_key'] = computed_key

    if current is None:
        if strategy == 'update_only':
            _record(connection, source_line=record.get('__source_line__', index), job_id=job_id, company_id=company_id, row_number=index,
                    action='skip', table=descriptor.target_table, target_id=None,
                    before=None, after=None, error='Registro inexistente (update_only).')
            return 'skipped'
        if writer is not None:
            outcome = writer(connection, descriptor=descriptor, company_id=company_id, job_id=job_id,
                             action='insert', record=record, payload=payload, current=None,
                             defaults=defaults, stamp=stamp, actor=actor or {})
            if outcome.get('outcome') == 'skipped':
                _record(connection, source_line=record.get('__source_line__', index), job_id=job_id, company_id=company_id, row_number=index,
                        action='skip', table=descriptor.target_table, target_id=outcome.get('target_id'),
                        before=None, after=None, error=str(outcome.get('reason') or 'Sem alteração.'))
                return 'skipped'
            new_id = int(outcome['target_id'])
        else:
            new_id = _insert(connection, descriptor, company_id, defaults, payload, stamp=stamp)
        secondary = None
        if post_write is not None:
            secondary = post_write(connection, descriptor=descriptor, company_id=company_id, job_id=job_id,
                                   action='insert', target_id=new_id, record=record, payload=payload, actor=actor or {})
        after = _persisted_evidence(connection, descriptor, company_id, new_id, payload)
        if secondary:
            after['__secondary_v1__'] = secondary
        _record(connection, source_line=record.get('__source_line__', index), job_id=job_id, company_id=company_id, row_number=index,
                action='insert', table=descriptor.target_table, target_id=new_id,
                before=None, after=after)
        add_identity(existing, descriptor, {'id': new_id, **payload})
        return 'inserted'

    if strategy in ('insert_only', 'skip_duplicates'):
        _record(connection, source_line=record.get('__source_line__', index), job_id=job_id, company_id=company_id, row_number=index,
                action='skip', table=descriptor.target_table,
                target_id=int(current['id']), before=None, after=None,
                error=f'Registro já existente ({strategy}).')
        return 'skipped'

    prior = read_row(connection, descriptor.target_table, company_id, int(current['id']), lock=True)
    if prior is None:
        raise ValueError('Registro alterado ou removido durante a importação.')
    before = {name: value for name, value in prior['row'].items() if name in writable}
    if identify({key: [prior['row']] for key in existing if any(r['id'] == int(current['id']) for r in existing[key])}, descriptor, record)[1]:
        raise ValueError('Identidade mudou durante a execução.')
    if writer is not None:
        outcome = writer(connection, descriptor=descriptor, company_id=company_id, job_id=job_id,
                         action='update', record=record, payload=payload, current=current,
                         defaults=defaults, stamp=stamp, actor=actor or {})
        if outcome.get('outcome') == 'skipped':
            _record(connection, source_line=record.get('__source_line__', index), job_id=job_id, company_id=company_id, row_number=index,
                    action='skip', table=descriptor.target_table, target_id=int(current['id']),
                    before=None, after=None, error=str(outcome.get('reason') or 'Sem alteração.'))
            return 'skipped'
    else:
        _update(connection, descriptor, int(current['id']), company_id, payload)
    if post_write is not None:
        post_write(connection, descriptor=descriptor, company_id=company_id, job_id=job_id,
                   action='update', target_id=int(current['id']), record=record, payload=payload, actor=actor or {})
    _record(connection, source_line=record.get('__source_line__', index), job_id=job_id, company_id=company_id, row_number=index,
            action='update', table=descriptor.target_table,
            target_id=int(current['id']), before=before,
            after=_persisted_evidence(connection, descriptor, company_id, int(current['id']), payload, prior))
    add_identity(existing, descriptor, {**current, **payload})
    return 'updated'


def _reconcile_job(connection, job_id, company_id, totals, descriptor):
    if not db_module._is_sqlite_connection(connection):
        connection.execute('SET CONSTRAINTS ALL IMMEDIATE')
    rows = connection.execute('SELECT action, target_table, target_id, after_json FROM migration_job_records '
        'WHERE job_id = %s AND company_id = %s ORDER BY id', (int(job_id), int(company_id))).fetchall()
    counts = {'insert': 0, 'update': 0, 'skip': 0, 'error': 0}
    latest = {}
    for raw in rows:
        r = row_to_dict(raw)
        if r['action'] not in counts:
            raise ValueError('Auditoria de execução incompatível.')
        counts[r['action']] += 1
        if r['action'] in ('insert', 'update'):
            if r['target_table'] != descriptor.target_table:
                raise ValueError('Alvo da auditoria incompatível.')
            latest[int(r['target_id'])] = json.loads(r['after_json'])['__rollback_v1__']
    if any(counts[a] != totals[b] for a,b in [('insert','inserted'),('update','updated'),('skip','skipped'),('error','failed')]) or sum(counts.values()) != totals['total']:
        raise ValueError('Contagens não conciliadas.')
    for target_id, proof in latest.items():
        actual = read_row(connection, descriptor.target_table, company_id, target_id)
        if actual is None or actual['row'] != proof['row'] or actual['version'] != proof['version']:
            raise ValueError('Estado persistido não conciliado.')
    if totals['processed'] != totals['total']:
        raise ValueError('Processamento não conciliado.')


def _record_failed_job(connection, *, company_id, entity, source_kind, source_name,
                       hash_value, strategy, actor, actor_ip, totals, error) -> int:
    """Registra o job como falho depois de um rollback total.

    O job original foi desfeito junto com os dados; recriamos a linha de
    histórico para o usuário enxergar a tentativa e o motivo.
    """
    cursor = connection.execute(
        'INSERT INTO migration_jobs '
        '(company_id, entity, source_kind, source_name, source_hash, strategy, status, '
        ' total_rows, processed_rows, inserted_rows, updated_rows, skipped_rows, failed_rows, '
        ' actor_user_id, actor_name, actor_ip, error_message, started_at, finished_at, created_at) '
        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
        (
            int(company_id), str(entity), str(source_kind), str(source_name or ''),
            str(hash_value or ''), str(strategy), 'failed',
            int(totals.get('total', 0)), 0, 0, 0, 0, int(totals.get('total', 0)),
            int(actor.get('id') or 0), str(actor.get('full_name') or ''), str(actor_ip or ''),
            str(error or ''), _now(), _now(), _now(),
        ),
    )
    return int(cursor.lastrowid or 0)


def _snapshot(connection, descriptor, target_id: int, writable: set[str]) -> dict:
    """Estado atual das colunas que serão tocadas — o ``before`` do rollback."""
    columns = ', '.join(sorted(writable))
    row = connection.execute(
        f'SELECT {columns} FROM {descriptor.target_table} WHERE id = %s',  # noqa: S608 - allowlist do catálogo
        (int(target_id),),
    ).fetchone()
    return row_to_dict(row) if row else {}


def _insert(connection, descriptor, company_id: int, defaults: dict, payload: dict,
            *, stamp: dict | None = None) -> int:
    # Defaults DECLARADOS no catálogo (`column_defaults`), não um preenchimento
    # automático de toda coluna NOT NULL: cada um é uma decisão de domínio
    # documentada e coberta pelo teste de contrato (ADR-0003 §12.3).
    payload = {**{name: value for name, value in defaults.items() if name not in payload}, **payload}
    # O carimbo de procedência vem POR ÚLTIMO e sobrescreve: nem a planilha nem
    # o catálogo podem declarar que uma linha importada nasceu no sistema.
    if stamp:
        payload = {**payload, **stamp}
    columns = ['company_id', *sorted(payload)]
    values = [int(company_id), *[payload[name] for name in sorted(payload)]]
    placeholders = ', '.join(['%s'] * len(values))
    cursor = connection.execute(
        f'INSERT INTO {descriptor.target_table} ({", ".join(columns)}) VALUES ({placeholders})',  # noqa: S608 - allowlist do catálogo
        tuple(values),
    )
    return int(cursor.lastrowid)


def _update(connection, descriptor, target_id: int, company_id: int, payload: dict) -> None:
    assignments = ', '.join(f'{name} = %s' for name in sorted(payload))
    values = [payload[name] for name in sorted(payload)]
    connection.execute(
        f'UPDATE {descriptor.target_table} SET {assignments} WHERE id = %s AND company_id = %s',  # noqa: S608 - allowlist do catálogo
        (*values, int(target_id), int(company_id)),
    )


# ── Rollback (ADR-0003 §2.4) ────────────────────────────────────────────────

def _atomic_job_decision(function):
    """Mutation and optional route audit commit together; failed attempts rollback."""
    @wraps(function)
    def execute(connection, job_id, company_id, actor, *, audit_callback=None):
        try:
            result = function(connection, job_id, company_id, actor)
            if audit_callback is not None:
                audit_callback(connection, result)
            connection.commit()
            return result
        except Exception as exc:
            connection.rollback()
            if isinstance(exc, RollbackConflict):
                # Existing per-job audit stores refusal, never overwrites original evidence.
                # The rejected mutation has already been completely rolled back.
                try:
                    _record(connection, job_id=job_id, company_id=company_id, row_number=exc.row,
                            action='rollback_conflict', table='', target_id=exc.target_id,
                            before=None, after=None, error=json.dumps({
                                'code': 'rollback_conflict', 'reason': exc.reason,
                                'actor_user_id': int(actor.get('id') or 0),
                            }, ensure_ascii=False))
                    connection.commit()
                except Exception:
                    connection.rollback()
                    raise
            raise
    return execute


@_atomic_job_decision
def homologate_job(connection, job_id: int, company_id: int, actor) -> dict:
    """Homologa a importação — o cliente conferiu e aceitou o resultado.

    A homologação é a fronteira entre dois regimes de rollback (issue #211):

    - **antes**: a importação ainda está em avaliação, e desfazê-la APAGA o
      que ela inseriu. É o que se quer — são linhas que ninguém validou e que
      podem estar erradas;
    - **depois**: o dado passou a ser o histórico oficial do cliente. Uma
      entrega de EPI homologada é peça de prova em auditoria trabalhista, e
      apagá-la deixa de ser aceitável mesmo quando a importação toda se
      revelou equivocada. O rollback passa a ser lógico.

    Operação de mão única de propósito: não existe "des-homologar". Poder
    voltar o job ao estado apagável reabriria exatamente a porta que a
    homologação fecha, e transformaria a trava numa formalidade.
    """
    job = get_job(connection, job_id, company_id, for_update=True)
    if not job:
        raise ValueError('Importação não encontrada.')
    # "já revertida" ANTES do status, pela mesma razão de `revert_job`: depois
    # da reversão o status vira 'reverted', e a mensagem genérica de status
    # esconderia o motivo real.
    if job.get('reverted_at'):
        raise ValueError('Esta importação foi revertida e não pode ser homologada.')
    if job.get('status') != 'completed':
        raise ValueError('Só é possível homologar uma importação concluída.')
    if job.get('homologated_at'):
        raise ValueError('Esta importação já foi homologada.')

    connection.execute(
        'UPDATE migration_jobs SET homologated_at = %s, homologated_by = %s '
        'WHERE id = %s AND company_id = %s',
        (_now(), int(actor.get('id') or 0), int(job_id), int(company_id)),
    )
    return {'job_id': int(job_id), 'homologated': True}


@_atomic_job_decision
def revert_job(connection, job_id: int, company_id: int, actor) -> dict:
    """Desfaz uma importação.

    Dois regimes, decididos pelo estado de homologação do job (issue #211):

    **Reversão física** (job ainda não homologado): apaga o que foi inserido e
    restaura o ``before_json`` do que foi atualizado, em ordem inversa.

    **Reversão lógica** (job homologado): as linhas inseridas são MARCADAS na
    coluna declarada em ``EntityDescriptor.reversal_column`` e param de contar
    como registro ativo, mas continuam existindo. Auditoria e histórico ficam
    preservados — é o ponto todo de homologar.

    Se o job foi homologado e a entidade não declara ``reversal_column``, a
    reversão é RECUSADA em vez de cair no caminho físico. Apagar histórico
    homologado por falta de suporte a rollback lógico seria escolher o pior
    resultado justamente onde o dado é mais sensível.
    """
    job = get_job(connection, job_id, company_id, for_update=True)
    if not job:
        raise ValueError('Importação não encontrada.')
    # "já revertida" é checado ANTES do status: depois da primeira reversão o
    # status vira 'reverted', e a mensagem genérica de status esconderia o
    # motivo real de uma segunda tentativa.
    if job.get('reverted_at'):
        raise ValueError('Esta importação já foi revertida.')
    if job.get('status') not in ('completed', 'completed_with_rejections'):
        raise ValueError('Só é possível reverter uma importação concluída.')

    descriptor = get_entity(job['entity'])
    homologated = bool(str(job.get('homologated_at') or '').strip())
    reversal_column = str(getattr(descriptor, 'reversal_column', '') or '')
    if homologated and not reversal_column:
        raise ValueError(
            f'Esta importação de "{descriptor.label}" já foi homologada e a '
            'reversão apagaria os registros. Reversão lógica não está '
            'disponível para esta entidade.'
        )
    # Coluna do catálogo, mas conferida contra o schema real: tenant em versão
    # anterior não pode acabar caindo no DELETE por a coluna não existir.
    if homologated and reversal_column not in set(table_columns(connection, descriptor.target_table)):
        raise ValueError(
            'Esta importação já foi homologada e a coluna de reversão lógica '
            f'({reversal_column}) não existe neste banco. Aplique as migrations '
            'pendentes antes de reverter.'
        )

    rows = [row_to_dict(row) for row in connection.execute(
        'SELECT id, row_number, action, target_table, target_id, before_json, after_json '
        'FROM migration_job_records WHERE job_id = %s AND company_id = %s ORDER BY id DESC',
        (int(job_id), int(company_id)),
    ).fetchall()]
    if (sum(row['action'] == 'insert' for row in rows) != int(job['inserted_rows'])
            or sum(row['action'] == 'update' for row in rows) != int(job['updated_rows'])):
        raise RollbackConflict('auditoria incompleta para conciliar a reversão')
    # Efeitos secundários do writer/post_write (movimentos de estoque; vínculos
    # de terceirizada) são desfeitos ANTES do preflight e do rollback genérico:
    # o vínculo tem FK para a empresa, então o preflight recusaria a reversão por
    # "dependências posteriores" se o vínculo ainda existisse. Só no rollback
    # físico — o lógico (pós-homologação) já é recusado acima para entidades sem
    # `reversal_column` (estoque e fornecedores).
    if not homologated:
        reverser = _load_reverser(descriptor)
        if reverser is not None:
            reverser(connection, descriptor=descriptor, company_id=int(company_id), job_id=int(job_id))
    plan = preflight(connection, descriptor, int(company_id), rows)
    reverted = {'deleted': 0, 'restored': 0, 'skipped': len(rows) - len(plan), 'marked': 0}
    for record in plan:
        target_id = int(record['target_id'])
        if record['action'] == 'insert':
            if homologated:
                marked_at = _now()
                cursor = connection.execute(
                    f'UPDATE {descriptor.target_table} SET {reversal_column} = %s '
                    'WHERE id = %s AND company_id = %s',  # noqa: S608 - catalogue only
                    (marked_at, target_id, int(company_id)),
                )
                outcome = 'marked'
            else:
                cursor = connection.execute(
                    f'DELETE FROM {descriptor.target_table} WHERE id = %s AND company_id = %s',  # noqa: S608
                    (target_id, int(company_id)),
                )
                outcome = 'deleted'
        else:
            before = record['before']
            assignments = ', '.join(f'{name} = %s' for name in sorted(before))
            cursor = connection.execute(
                f'UPDATE {descriptor.target_table} SET {assignments} WHERE id = %s AND company_id = %s',  # noqa: S608
                (*[before[name] for name in sorted(before)], target_id, int(company_id)),
            )
            outcome = 'restored'
        if cursor.rowcount != 1:
            raise RollbackConflict('gravação da reversão não conciliada', target_id=target_id)
        persisted = read_row(connection, descriptor.target_table, company_id, target_id)
        expected = record['expected_before']
        if outcome == 'marked':
            expected = {**record['expected_after'], reversal_column: marked_at}
        if (persisted['row'] if persisted else None) != expected:
            raise RollbackConflict('estado persistido da reversão não conciliado', target_id=target_id)
        reverted[outcome] += 1

    connection.execute(
        'UPDATE migration_jobs SET status = %s, reverted_at = %s, reverted_by = %s WHERE id = %s AND company_id = %s',
        ('reverted', _now(), int(actor.get('id') or 0), int(job_id), int(company_id)),
    )
    return {'job_id': int(job_id), **reverted}


# ── Consulta ────────────────────────────────────────────────────────────────

def get_job(connection, job_id: int, company_id: int, *, for_update=False) -> dict | None:
    row = connection.execute(
        'SELECT * FROM migration_jobs WHERE id = %s AND company_id = %s LIMIT 1'
        + (lock_suffix(connection) if for_update else ''),
        (int(job_id), int(company_id)),
    ).fetchone()
    return row_to_dict(row) if row else None


def fetch_jobs(connection, company_id: int, *, entity: str = '', limit: int = 50) -> list[dict]:
    clauses = ['company_id = %s']
    params: list = [int(company_id)]
    if entity:
        clauses.append('entity = %s')
        params.append(str(entity))
    rows = connection.execute(
        'SELECT id, entity, source_kind, source_name, strategy, status, total_rows, '
        'processed_rows, inserted_rows, updated_rows, skipped_rows, failed_rows, actor_name, '
        'started_at, finished_at, reverted_at, homologated_at, created_at '
        f'FROM migration_jobs WHERE {" AND ".join(clauses)} '  # noqa: S608 - cláusulas fixas
        'ORDER BY id DESC LIMIT %s',
        (*params, int(limit)),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def fetch_job_records(connection, job_id: int, company_id: int, *, limit: int = 500, offset: int = 0) -> list[dict]:
    rows = connection.execute(
        'SELECT row_number, action, target_table, target_id, error_message, after_json '
        'FROM migration_job_records WHERE job_id = %s AND company_id = %s '
        'ORDER BY row_number, id LIMIT %s OFFSET %s',
        (int(job_id), int(company_id), max(1, min(int(limit), 500)), max(0, int(offset))),
    ).fetchall()
    result = []
    for raw in rows:
        record = row_to_dict(raw)
        try:
            after = json.loads(record.pop('after_json') or '{}')
            source_line = after.get('__source_line__')
        except (ValueError, TypeError, AttributeError):
            source_line = None
        diagnostic = None
        if record['action'] == 'error':
            try:
                candidate = json.loads(record['error_message'])
                if isinstance(candidate, dict) and candidate.get('code') == 'database_row_rejected':
                    diagnostic = candidate
            except (TypeError, ValueError):
                pass
            # Legacy technical exceptions must never be rendered/exported.
            diagnostic = diagnostic or {'code': 'database_row_rejected', 'row': record['row_number'],
                'field': '', 'severity': 'error', 'message': 'Registro rejeitado pelo banco.'}
            record['error_message'] = diagnostic['message']
        record['source_line'] = source_line or (diagnostic or {}).get('source_line')
        record['diagnostic'] = diagnostic
        result.append(record)
    return result
