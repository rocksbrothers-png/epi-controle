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

from epi_backend.db import row_to_dict, table_columns
from modules.data_migration.catalog import get_entity, require_enabled_entity
from modules.data_migration.mapper import apply_mapping, normalize_manual_mapping, suggest_mapping
from modules.data_migration.preview import build_preview, natural_key_of
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


def _migration_idempotency_key(row_number: int, payload: dict) -> str:
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
    digest = hashlib.sha256(f'{parts}|{int(row_number)}'.encode()).hexdigest()
    return f'mig:{digest[:40]}'


# ── Etapas 3 e 4 do assistente: leitura + mapeamento ────────────────────────

def analyze_source(kind: str, raw: bytes, entity: str, *, sheet: str | None = None) -> dict:
    """Lê a origem, detecta layout e já propõe o mapeamento.

    É o que alimenta as etapas 3 (leitura automática) e 4 (mapeamento) do
    assistente numa única chamada — o usuário sobe o arquivo e já vê as
    colunas reconhecidas.
    """
    descriptor = get_entity(entity)
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

def _existing_index(connection, descriptor, company_id: int) -> dict[str, dict]:
    """Mapa ``chave natural -> linha atual`` do tenant.

    Carregado uma vez por job: fazer um SELECT por linha importada seria
    O(n) idas ao banco e inviabilizaria arquivos grandes.
    """
    keys = [key for key in descriptor.natural_keys if key in set(table_columns(connection, descriptor.target_table))]
    if not keys:
        return {}
    columns = ', '.join(['id', *keys])
    rows = connection.execute(
        f'SELECT {columns} FROM {descriptor.target_table} WHERE company_id = %s',  # noqa: S608 - allowlist do catálogo
        (int(company_id),),
    ).fetchall()
    index: dict[str, dict] = {}
    for row in rows:
        record = row_to_dict(row)
        key = natural_key_of(descriptor, record)
        if key:
            index[key] = record
    return index


# ── Job ─────────────────────────────────────────────────────────────────────

def _reference_index(connection, table: str, name_column: str, company_id: int) -> dict[str, list[int]]:
    """Mapa ``nome normalizado -> [ids]`` da tabela, **dentro do tenant**.

    Devolve lista, não id único, para que ambiguidade (duas unidades com o
    mesmo nome na mesma empresa) seja detectável em vez de resolvida em
    silêncio para a primeira que aparecer.

    O filtro por ``company_id`` é o que impede que "Produção" de um tenant
    resolva para a unidade de outro.
    """
    rows = connection.execute(
        f'SELECT id, {name_column} FROM {table} WHERE company_id = %s',  # noqa: S608 - allowlist do catálogo
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


def resolve_references(connection, descriptor, company_id: int, records: list[dict]) -> list[dict]:
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
        spec.name: _reference_index(connection, spec.resolves_to[0], spec.resolves_to[1], company_id)
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
                if int(raw) in known_ids[spec.name]:
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
            updated = normalizer(record)
            updated.pop('__domain_error__', None)
        except ValueError as exc:
            updated = dict(record)
            updated['__domain_error__'] = str(exc)
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
            before, after, error='') -> None:
    """Uma linha por registro tocado. É o insumo do rollback (ADR-0003 §2.4)."""
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


def run_migration(connection, *, company_id, entity, source_kind, raw, mapping, strategy,
                  actor, source_name='', actor_ip='', sheet=None, persist_mapping=True) -> dict:
    """Executa uma importação de ponta a ponta.

    ``strategy='dry_run'`` percorre o pipeline inteiro e devolve o preview
    **sem gravar nada** — é o que o assistente chama antes de confirmar.
    """
    strategy = str(strategy or 'dry_run').strip()
    if strategy not in STRATEGIES:
        raise ValueError(f'Estratégia de importação inválida: {strategy!r}.')

    # Entidade de roadmap nunca chega ao writer, mesmo se a UI deixar passar.
    descriptor = get_entity(entity) if strategy == 'dry_run' else require_enabled_entity(entity)

    dataset = read_source(source_kind, raw, sheet=sheet)
    normalized_mapping = normalize_manual_mapping(descriptor, mapping, dataset.columns)
    records = apply_mapping(normalized_mapping, dataset.rows)
    # Nome → id ANTES do preview: assim "Unidade inexistente" aparece como
    # obrigatório ausente na simulação, não como erro de banco na gravação.
    records = resolve_references(connection, descriptor, company_id, records)
    # Regras de vínculo iguais às do cadastro manual (ADR-0003 §12.2): CPF
    # normalizado para dígitos, empresa de origem exigida/limpa conforme o
    # vínculo. Sem isto a importação gravaria CPF formatado e o upsert nunca
    # reconheceria quem foi cadastrado à mão.
    records = apply_domain_rules(descriptor, records)

    existing = _existing_index(connection, descriptor, company_id)
    preview = build_preview(descriptor, records, existing_keys=existing.keys())
    preview['detected'] = dataset.detected
    preview['signature'] = dataset.signature()

    if strategy == 'dry_run':
        return {'job_id': None, 'strategy': strategy, 'applied': False, 'preview': preview}

    if preview['blocking']:
        raise ValueError(
            'A importação foi bloqueada porque existem erros no arquivo. '
            'Revise o preview, corrija as linhas apontadas e envie novamente.'
        )

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
                        existing=existing, stamp=stamp,
                    )
            except Exception as exc:  # linha ruim não derruba o job inteiro
                # Aqui a transação já voltou ao ponto anterior à linha, então
                # gravar o diagnóstico é seguro.
                totals['failed'] += 1
                _record(connection, job_id=job_id, company_id=company_id, row_number=index,
                        action='error', table=descriptor.target_table, target_id=None,
                        before=None, after=None, error=str(exc)[:500])
                continue
            totals['processed'] += 1
            totals[outcome] += 1

        if persist_mapping:
            save_mapping(connection, company_id, descriptor.key, dataset.signature(), normalized_mapping)
        _finish_job(connection, job_id, status='completed', totals=totals, preview=preview)
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
            actor=actor, actor_ip=actor_ip, totals=totals, error=str(exc)[:500],
        )
        connection.commit()
        raise

    return {'job_id': job_id, 'strategy': strategy, 'applied': True, 'totals': totals, 'preview': preview}


def _apply_row(connection, descriptor, company_id, job_id, index, record, *,
               strategy, writable, defaults, existing, stamp=None) -> str:
    """Grava UMA linha e devolve o contador que ela alimenta.

    Roda inteira dentro do SAVEPOINT aberto por quem chama.
    """
    key = natural_key_of(descriptor, record)
    # Entidade SEM chave natural (issue #211): `natural_key_of` devolve string
    # vazia para toda linha, e sem esta guarda todas colidiriam entre si — a
    # primeira entrega entrava e as demais eram tratadas como "já existente".
    # Sem chave natural não existe registro correspondente por definição: cada
    # linha é um fato novo, e a proteção contra reimportação é a
    # `idempotency_key` computada logo abaixo.
    current = existing.get(key) if key else None
    payload = {
        name: value for name, value in record.items()
        if name in writable and str(value or '').strip()
    }
    if not payload:
        _record(connection, job_id=job_id, company_id=company_id, row_number=index,
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
        computed_key = _migration_idempotency_key(index, payload)
        duplicate = connection.execute(
            f'SELECT id FROM {descriptor.target_table} '  # noqa: S608 - allowlist do catálogo
            'WHERE company_id = %s AND idempotency_key = %s LIMIT 1',
            (int(company_id), computed_key),
        ).fetchone()
        if duplicate:
            _record(connection, job_id=job_id, company_id=company_id, row_number=index,
                    action='skip', table=descriptor.target_table,
                    target_id=int(row_to_dict(duplicate)['id']), before=None, after=None,
                    error='Linha já importada anteriormente (reimportação do mesmo arquivo).')
            return 'skipped'
        payload['idempotency_key'] = computed_key

    if current is None:
        if strategy == 'update_only':
            _record(connection, job_id=job_id, company_id=company_id, row_number=index,
                    action='skip', table=descriptor.target_table, target_id=None,
                    before=None, after=None, error='Registro inexistente (update_only).')
            return 'skipped'
        new_id = _insert(connection, descriptor, company_id, defaults, payload, stamp=stamp)
        if key:
            existing[key] = {'id': new_id, **payload}
        _record(connection, job_id=job_id, company_id=company_id, row_number=index,
                action='insert', table=descriptor.target_table, target_id=new_id,
                before=None, after=payload)
        return 'inserted'

    if strategy in ('insert_only', 'skip_duplicates'):
        _record(connection, job_id=job_id, company_id=company_id, row_number=index,
                action='skip', table=descriptor.target_table,
                target_id=int(current['id']), before=None, after=None,
                error=f'Registro já existente ({strategy}).')
        return 'skipped'

    before = _snapshot(connection, descriptor, int(current['id']), writable)
    _update(connection, descriptor, int(current['id']), company_id, payload)
    _record(connection, job_id=job_id, company_id=company_id, row_number=index,
            action='update', table=descriptor.target_table,
            target_id=int(current['id']), before=before, after=payload)
    return 'updated'


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
    job = get_job(connection, job_id, company_id)
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
    connection.commit()
    return {'job_id': int(job_id), 'homologated': True}


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
    job = get_job(connection, job_id, company_id)
    if not job:
        raise ValueError('Importação não encontrada.')
    # "já revertida" é checado ANTES do status: depois da primeira reversão o
    # status vira 'reverted', e a mensagem genérica de status esconderia o
    # motivo real de uma segunda tentativa.
    if job.get('reverted_at'):
        raise ValueError('Esta importação já foi revertida.')
    if job.get('status') != 'completed':
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

    rows = connection.execute(
        'SELECT id, row_number, action, target_table, target_id, before_json '
        'FROM migration_job_records WHERE job_id = %s AND company_id = %s ORDER BY id DESC',
        (int(job_id), int(company_id)),
    ).fetchall()

    reverted = {'deleted': 0, 'restored': 0, 'skipped': 0, 'marked': 0}

    for raw_row in rows:
        record = row_to_dict(raw_row)
        action = str(record.get('action') or '')
        target_id = record.get('target_id')
        if not target_id or action not in ('insert', 'update'):
            reverted['skipped'] += 1
            continue
        # target_table vem do catálogo (gravado a partir do descritor), nunca
        # de entrada do usuário — mas revalidamos contra o descritor por
        # segurança em profundidade.
        if str(record.get('target_table') or '') != descriptor.target_table:
            reverted['skipped'] += 1
            continue
        if action == 'insert':
            if homologated:
                # Reversão LÓGICA: a linha some das leituras operacionais e
                # continua existindo para a auditoria. `reversal_column` vem do
                # catálogo, nunca do payload.
                connection.execute(
                    f'UPDATE {descriptor.target_table} SET {reversal_column} = %s '  # noqa: S608 - allowlist do catálogo
                    'WHERE id = %s AND company_id = %s',
                    (_now(), int(target_id), int(company_id)),
                )
                reverted['marked'] += 1
            else:
                connection.execute(
                    f'DELETE FROM {descriptor.target_table} WHERE id = %s AND company_id = %s',  # noqa: S608 - allowlist do catálogo
                    (int(target_id), int(company_id)),
                )
                reverted['deleted'] += 1
        else:
            try:
                before = json.loads(record.get('before_json') or '{}')
            except (TypeError, ValueError):
                before = {}
            before.pop('id', None)
            if not before:
                reverted['skipped'] += 1
                continue
            assignments = ', '.join(f'{name} = %s' for name in sorted(before))
            connection.execute(
                f'UPDATE {descriptor.target_table} SET {assignments} WHERE id = %s AND company_id = %s',  # noqa: S608 - allowlist do catálogo
                (*[before[name] for name in sorted(before)], int(target_id), int(company_id)),
            )
            reverted['restored'] += 1

    connection.execute(
        'UPDATE migration_jobs SET status = %s, reverted_at = %s, reverted_by = %s WHERE id = %s',
        ('reverted', _now(), int(actor.get('id') or 0), int(job_id)),
    )
    connection.commit()
    return {'job_id': int(job_id), **reverted}


# ── Consulta ────────────────────────────────────────────────────────────────

def get_job(connection, job_id: int, company_id: int) -> dict | None:
    row = connection.execute(
        'SELECT * FROM migration_jobs WHERE id = %s AND company_id = %s LIMIT 1',
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
        'inserted_rows, updated_rows, skipped_rows, failed_rows, actor_name, '
        'started_at, finished_at, reverted_at, homologated_at, created_at '
        f'FROM migration_jobs WHERE {" AND ".join(clauses)} '  # noqa: S608 - cláusulas fixas
        'ORDER BY id DESC LIMIT %s',
        (*params, int(limit)),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def fetch_job_records(connection, job_id: int, company_id: int, *, limit: int = 500) -> list[dict]:
    rows = connection.execute(
        'SELECT row_number, action, target_table, target_id, error_message '
        'FROM migration_job_records WHERE job_id = %s AND company_id = %s '
        'ORDER BY row_number LIMIT %s',
        (int(job_id), int(company_id), int(limit)),
    ).fetchall()
    return [row_to_dict(row) for row in rows]
