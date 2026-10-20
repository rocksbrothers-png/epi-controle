"""Fila durável de migração assíncrona (MIG-DATA-FIX-V1 — Fase 3).

Jobs de importação persistidos em PostgreSQL, reclamados por um worker CLI
independente e executados reutilizando ``run_migration`` (sem segundo motor).
Garantias preservadas da Fase 2/P0: quantidade inteira, isolamento por tenant,
atomicidade, sem sucesso enganoso. A infraestrutura fica DESLIGADA por padrão
(``MIGRATION_ASYNC_ENABLED``); nenhuma nova entidade de negócio é criada.

Ordem de locks obrigatória (evita o deadlock lease×``companies FOR UPDATE``):
  advisory de sessão por job  →  companies (dentro de run_migration)  →
  refs/targets  →  linha de controle por último (transações curtas).
O cancelamento só toca a linha de controle e nunca espera companies/targets.
Payload do arquivo nunca é gravado em claro: vai cifrado (Fernet) num envelope
autenticado que vincula empresa/ator/hash/tipo.
"""
import base64
import hashlib
import json
import os
from datetime import datetime, timezone

# Namespace fixo (int4) para os advisory locks por job desta fila.
_ADVISORY_NS = 790317

_CLAIMABLE = ('claimed', 'running', 'recovering')
_TERMINAL = ('completed', 'completed_with_rejections', 'failed', 'cancelled')
_STATUSES = ('queued',) + _CLAIMABLE + _TERMINAL


def _now():
    return datetime.now(timezone.utc).isoformat()


def _async_enabled():
    return str(os.environ.get('MIGRATION_ASYNC_ENABLED', '')).strip().lower() in ('1', 'true', 'yes', 'on')


def _product():
    return str(os.environ.get('MIGRATION_PRODUCT', '')).strip() or 'unknown'


def _fernet():
    from cryptography.fernet import Fernet
    key = str(os.environ.get('MIGRATION_INPUT_KEY', '')).strip()
    if not key:
        # Falha fechada: sem chave não se cifra nem decifra payload (nunca efêmera).
        raise RuntimeError('MIGRATION_INPUT_KEY ausente: a migração assíncrona exige uma chave Fernet.')
    return Fernet(key.encode())


def _as_dict(row):
    from epi_backend.db import row_to_dict
    return row_to_dict(row)


def _public(row):
    """Representação segura do job (sem payload cifrado, hash ou fingerprint)."""
    data = _as_dict(row)
    for sensitive in ('input_ciphertext', 'input_hash', 'request_fingerprint'):
        data.pop(sensitive, None)
    lease = data.get('lease_expires_at')
    if lease is not None and not isinstance(lease, str):
        data['lease_expires_at'] = str(lease)
    return data


def _fingerprint(company_id, entity, source_kind, strategy, mapping, sheet, preview_token, input_hash):
    content = [int(company_id), str(entity), str(source_kind), str(strategy), mapping or {},
               sheet, str(preview_token or ''), str(input_hash)]
    return hashlib.sha256(json.dumps(content, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


def install_schema(connection):
    """DDL idempotente da fila. Chamado pela migração 035 e pelos testes."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS migration_async_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            actor_user_id INTEGER NOT NULL,
            entity TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            source_name TEXT NOT NULL DEFAULT '',
            strategy TEXT NOT NULL,
            preview_token TEXT NOT NULL DEFAULT '',
            request_key TEXT NOT NULL,
            request_fingerprint TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'queued'
                CHECK (status IN ('queued','claimed','running','completed',
                                  'completed_with_rejections','failed','cancelled','recovering')),
            owner TEXT,
            attempt INTEGER NOT NULL DEFAULT 0,
            lease_expires_at TIMESTAMPTZ,
            cancel_requested INTEGER NOT NULL DEFAULT 0,
            total_rows INTEGER NOT NULL DEFAULT 0,
            processed_rows INTEGER NOT NULL DEFAULT 0,
            inserted_rows INTEGER NOT NULL DEFAULT 0,
            updated_rows INTEGER NOT NULL DEFAULT 0,
            skipped_rows INTEGER NOT NULL DEFAULT 0,
            failed_rows INTEGER NOT NULL DEFAULT 0,
            result_job_id INTEGER,
            input_ciphertext TEXT NOT NULL DEFAULT '',
            input_hash TEXT NOT NULL DEFAULT '',
            mapping_json TEXT NOT NULL DEFAULT '{}',
            sheet TEXT,
            error_message TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT ''
        )
        """
    )
    # Idempotência: um job por (empresa, ator, request_key).
    connection.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_mig_async_idemp '
        'ON migration_async_jobs (company_id, actor_user_id, request_key)')
    connection.execute(
        'CREATE INDEX IF NOT EXISTS idx_mig_async_claim ON migration_async_jobs (status, id)')
    connection.execute(
        'CREATE INDEX IF NOT EXISTS idx_mig_async_company ON migration_async_jobs (company_id, id)')


def _authorize(connection, actor):
    """Recarrega o ator do banco (ativo + permissão) e confere o tenant alegado."""
    from core.permissions import PERM_DATA_MIGRATION_MANAGE
    from core.repository import authorize_action
    authorized = authorize_action(connection, int(actor['id']), PERM_DATA_MIGRATION_MANAGE)
    company_id = int(authorized['company_id'])
    if 'company_id' in actor and int(actor['company_id']) != company_id:
        # company_id jamais vem do cliente: um valor divergente é recusado.
        raise PermissionError('Empresa do ator não confere com o executor autenticado.')
    return authorized, company_id


def submit(connection, *, actor, entity, source_kind, raw, mapping, strategy, request_key,
           source_name='', preview_token=None, sheet=None):
    """Enfileira um job durável. Não escreve dados de negócio."""
    if not _async_enabled():
        raise PermissionError('Migração assíncrona desabilitada (MIGRATION_ASYNC_ENABLED).')
    from modules.settings.service import ensure_module_enabled_for_unit

    authorized, company_id = _authorize(connection, actor)
    ensure_module_enabled_for_unit(connection, authorized, 'migracao', None)

    raw_bytes = raw if isinstance(raw, (bytes, bytearray)) else str(raw).encode()
    input_hash = hashlib.sha256(raw_bytes).hexdigest()
    mapping = mapping or {}
    key = str(request_key)
    fingerprint = _fingerprint(company_id, entity, source_kind, strategy, mapping, sheet,
                               preview_token, input_hash)

    existing = connection.execute(
        'SELECT * FROM migration_async_jobs WHERE company_id=%s AND actor_user_id=%s AND request_key=%s',
        (company_id, int(authorized['id']), key)).fetchone()
    if existing:
        # Idempotência: mesma chave + mesmo conteúdo ⇒ mesmo job; conteúdo
        # divergente ⇒ recusa (não reabrir importação sob a mesma chave).
        if _as_dict(existing).get('request_fingerprint') != fingerprint:
            raise ValueError('request_key já utilizada para outro arquivo/configuração (conteúdo divergente).')
        return _public(existing)

    envelope = {
        'v': 1, 'company_id': company_id, 'actor_user_id': int(authorized['id']),
        'entity': str(entity), 'kind': str(source_kind), 'strategy': str(strategy),
        'request_key': key, 'input_hash': input_hash, 'product': _product(),
        'raw_b64': base64.b64encode(raw_bytes).decode(),
    }
    ciphertext = _fernet().encrypt(json.dumps(envelope, ensure_ascii=False).encode()).decode()
    now = _now()
    try:
        cursor = connection.execute(
            'INSERT INTO migration_async_jobs (company_id, actor_user_id, entity, source_kind, '
            'source_name, strategy, preview_token, request_key, request_fingerprint, status, '
            'attempt, cancel_requested, input_ciphertext, input_hash, mapping_json, sheet, '
            'created_at, updated_at) VALUES '
            '(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
            (company_id, int(authorized['id']), str(entity), str(source_kind), str(source_name or ''),
             str(strategy), str(preview_token or ''), key, fingerprint, 'queued', 0, 0,
             ciphertext, input_hash, json.dumps(mapping, ensure_ascii=False), sheet, now, now))
        job_id = int(cursor.lastrowid)
        connection.commit()
    except Exception:
        # Corrida de INSERT na chave única: desfaz e devolve o job existente
        # (mesmo conteúdo) ou recusa (divergente). Nunca cria duplicata.
        connection.rollback()
        existing = connection.execute(
            'SELECT * FROM migration_async_jobs WHERE company_id=%s AND actor_user_id=%s AND request_key=%s',
            (company_id, int(authorized['id']), key)).fetchone()
        if not existing:
            raise
        if _as_dict(existing).get('request_fingerprint') != fingerprint:
            raise ValueError('request_key já utilizada para outro arquivo/configuração (conteúdo divergente).')
        return _public(existing)
    return get(connection, job_id, authorized)


def get(connection, job_id, actor):
    """Lê um job, estritamente escopado ao tenant do ator autenticado."""
    _authorized, company_id = _authorize(connection, actor)
    row = connection.execute(
        'SELECT * FROM migration_async_jobs WHERE id=%s AND company_id=%s',
        (int(job_id), company_id)).fetchone()
    if not row:
        raise LookupError('Job de migração não encontrado para esta empresa.')
    return _public(row)


def list_jobs(connection, actor, *, limit=50, offset=0):
    """Lista jobs assíncronos do tenant do ator (sem payload/segredos)."""
    _authorized, company_id = _authorize(connection, actor)
    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))
    rows = connection.execute(
        'SELECT * FROM migration_async_jobs WHERE company_id=%s ORDER BY id DESC LIMIT %s OFFSET %s',
        (company_id, limit, offset)).fetchall()
    return [_public(row) for row in rows]


def request_cancel(connection, job_id, actor):
    """Cancela (ou pede cancelamento) tocando SOMENTE a linha de controle."""
    _authorized, company_id = _authorize(connection, actor)
    row = connection.execute(
        'SELECT * FROM migration_async_jobs WHERE id=%s AND company_id=%s FOR UPDATE',
        (int(job_id), company_id)).fetchone()
    if not row:
        connection.rollback()
        raise LookupError('Job de migração não encontrado para esta empresa.')
    status = _as_dict(row)['status']
    if status == 'cancelled':
        connection.commit()
        return _public(row)
    if status in ('completed', 'completed_with_rejections', 'failed'):
        connection.rollback()
        raise ValueError('Job em estado terminal não pode ser cancelado.')
    now = _now()
    if status == 'queued':
        # Ainda não reclamado: cancela de imediato e torna não-reclamável.
        connection.execute(
            "UPDATE migration_async_jobs SET status='cancelled', cancel_requested=1, updated_at=%s "
            "WHERE id=%s AND company_id=%s AND status='queued'", (now, int(job_id), company_id))
    else:
        # Reclamado/rodando: sinaliza; o worker aborta na próxima verificação.
        connection.execute(
            'UPDATE migration_async_jobs SET cancel_requested=1, updated_at=%s '
            'WHERE id=%s AND company_id=%s', (now, int(job_id), company_id))
    connection.commit()
    updated = connection.execute(
        'SELECT * FROM migration_async_jobs WHERE id=%s AND company_id=%s',
        (int(job_id), company_id)).fetchone()
    return _public(updated)


def claim(connection, *, owner, lease_seconds):
    """Reclama um job enfileirado (ou com lease expirado) para um worker.

    ``FOR UPDATE SKIP LOCKED`` garante no máximo um vencedor concorrente; o
    ``pg_try_advisory_xact_lock`` impede roubar um job com executor vivo.
    """
    if not _async_enabled():
        return None
    row = connection.execute(
        "SELECT id, attempt FROM migration_async_jobs "
        "WHERE cancel_requested=0 AND ("
        "       status='queued' "
        "    OR (status IN ('claimed','running','recovering') "
        "        AND lease_expires_at IS NOT NULL AND lease_expires_at < clock_timestamp())) "
        "ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1").fetchone()
    if not row:
        connection.rollback()
        return None
    candidate = _as_dict(row)
    job_id = int(candidate['id'])
    guard = connection.execute('SELECT pg_try_advisory_xact_lock(%s, %s) AS ok',
                               (_ADVISORY_NS, job_id)).fetchone()
    if not _as_dict(guard)['ok']:
        # Executor vivo detém o advisory de sessão: não roubar.
        connection.rollback()
        return None
    attempt = int(candidate['attempt']) + 1
    connection.execute(
        "UPDATE migration_async_jobs SET status='claimed', owner=%s, attempt=%s, "
        "lease_expires_at = clock_timestamp() + (%s * interval '1 second'), updated_at=%s "
        "WHERE id=%s", (str(owner), attempt, int(lease_seconds), _now(), job_id))
    connection.commit()  # libera o FOR UPDATE e o advisory transacional
    return {'id': job_id, 'owner': str(owner), 'attempt': attempt, 'status': 'claimed'}


def _finalize_failed(connection, job_id, owner, attempt, message):
    connection.execute(
        "UPDATE migration_async_jobs SET status='failed', error_message=%s, updated_at=%s "
        "WHERE id=%s AND owner=%s AND attempt=%s",
        (str(message)[:500], _now(), int(job_id), str(owner), int(attempt)))
    connection.commit()
    return {'id': int(job_id), 'status': 'failed'}


def execute_claim(job_id, owner, attempt, *, connection_factory):
    """Executa um job reclamado numa conexão própria, com fencing e reconciliação."""
    if not _async_enabled():
        raise PermissionError('Migração assíncrona desabilitada (MIGRATION_ASYNC_ENABLED).')
    connection = connection_factory()
    locked = False
    try:
        # Advisory de SESSÃO: sobrevive ao commit interno de run_migration e
        # serializa a execução deste job entre workers. Liberado no finally.
        got = connection.execute('SELECT pg_try_advisory_lock(%s, %s) AS ok',
                                 (_ADVISORY_NS, int(job_id))).fetchone()
        if not _as_dict(got)['ok']:
            connection.rollback()
            raise PermissionError('Outro worker já executa este job.')
        locked = True

        row = connection.execute(
            'SELECT * FROM migration_async_jobs WHERE id=%s FOR UPDATE', (int(job_id),)).fetchone()
        if not row:
            connection.rollback()
            raise LookupError('Job inexistente.')
        job = _as_dict(row)
        if (job['owner'] != str(owner) or int(job['attempt']) != int(attempt)
                or job['status'] not in _CLAIMABLE):
            connection.rollback()
            raise PermissionError('Fence inválido: owner/attempt/estado não conferem.')
        if int(job['cancel_requested']) == 1:
            connection.execute(
                "UPDATE migration_async_jobs SET status='cancelled', updated_at=%s "
                "WHERE id=%s AND owner=%s AND attempt=%s", (_now(), int(job_id), str(owner), int(attempt)))
            connection.commit()
            return {'id': int(job_id), 'status': 'cancelled'}

        company_id = int(job['company_id'])
        actor_user_id = int(job['actor_user_id'])
        connection.execute(
            "UPDATE migration_async_jobs SET status='running', updated_at=%s "
            "WHERE id=%s AND owner=%s AND attempt=%s", (_now(), int(job_id), str(owner), int(attempt)))
        connection.commit()

        # Reautoriza no momento da execução: usuário desativado/sem permissão
        # ou tenant alterado ⇒ falha sem nenhuma escrita de negócio.
        try:
            from core.permissions import PERM_DATA_MIGRATION_MANAGE
            from core.repository import authorize_action
            from modules.settings.service import ensure_module_enabled_for_unit
            authorized = authorize_action(connection, actor_user_id, PERM_DATA_MIGRATION_MANAGE)
            if int(authorized['company_id']) != company_id:
                raise PermissionError('Tenant do ator mudou desde o enfileiramento.')
            ensure_module_enabled_for_unit(connection, authorized, 'migracao', None)
        except Exception:
            connection.rollback()
            return _finalize_failed(connection, job_id, owner, attempt,
                                    'Autorização revogada na execução; nada aplicado.')

        try:
            raw = _decrypt_payload(job, company_id, actor_user_id)
        except Exception:
            connection.rollback()
            return _finalize_failed(connection, job_id, owner, attempt,
                                    'Payload inválido ou adulterado; nada aplicado.')

        from modules.data_migration.service import run_migration
        mapping = json.loads(job.get('mapping_json') or '{}')
        strategy = job['strategy']
        try:
            result = run_migration(
                connection, company_id=company_id, entity=job['entity'],
                source_kind=job['source_kind'], raw=raw, mapping=mapping, strategy=strategy,
                actor=authorized, source_name=job.get('source_name') or '',
                sheet=job.get('sheet'), preview_strategy=strategy,
                preview_token=job.get('preview_token') or None)
        except Exception:
            # run_migration já fez rollback (decorator). Sanitiza (HOLE-1): o
            # erro cru do banco não vaza; o job fica failed sem escrita.
            connection.rollback()
            return _finalize_failed(connection, job_id, owner, attempt,
                                    'Falha transacional na migração; nada aplicado desta tentativa.')

        # run_migration confirmou negócio + job legado. Finaliza o controle por CAS.
        totals = result.get('totals') or {}
        status = result.get('status') or ('completed' if result.get('applied') else 'failed')
        connection.execute(
            'UPDATE migration_async_jobs SET status=%s, result_job_id=%s, total_rows=%s, '
            'processed_rows=%s, inserted_rows=%s, updated_rows=%s, skipped_rows=%s, failed_rows=%s, '
            "updated_at=%s WHERE id=%s AND owner=%s AND attempt=%s AND status='running'",
            (status, result.get('job_id'), int(totals.get('total', 0)), int(totals.get('processed', 0)),
             int(totals.get('inserted', 0)), int(totals.get('updated', 0)), int(totals.get('skipped', 0)),
             int(totals.get('failed', 0)), _now(), int(job_id), str(owner), int(attempt)))
        connection.commit()
        return {'id': int(job_id), 'status': status, 'result_job_id': result.get('job_id')}
    finally:
        if locked:
            try:
                connection.rollback()
                connection.execute('SELECT pg_advisory_unlock(%s, %s)', (_ADVISORY_NS, int(job_id)))
                connection.commit()
            except Exception:
                try:
                    connection.rollback()
                except Exception:
                    pass
        connection.close()


def _decrypt_payload(job, company_id, actor_user_id):
    token = job.get('input_ciphertext') or ''
    if not token:
        raise ValueError('Payload ausente.')
    data = json.loads(_fernet().decrypt(token.encode()).decode())
    if int(data.get('company_id', -1)) != company_id or int(data.get('actor_user_id', -1)) != actor_user_id:
        raise ValueError('Envelope do payload não confere com o job.')
    raw = base64.b64decode(data['raw_b64'])
    if hashlib.sha256(raw).hexdigest() != job.get('input_hash'):
        raise ValueError('Hash do payload diverge; conteúdo adulterado.')
    return raw


def run_once(owner, *, lease_seconds, connection_factory):
    """Reclama e executa no máximo um job. Base do loop do worker CLI."""
    connection = connection_factory()
    try:
        claimed = claim(connection, owner=owner, lease_seconds=lease_seconds)
    finally:
        connection.close()
    if not claimed:
        return None
    return execute_claim(claimed['id'], claimed['owner'], claimed['attempt'],
                         connection_factory=connection_factory)
