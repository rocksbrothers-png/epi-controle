"""Fase 3 — provas adversariais em PostgreSQL real (complementam os 9 testes
congelados em test_migration_phase3_postgres.py, sem alterá-los).

Exercita fencing (owner/attempt), reclaim de lease expirado, serialização por
advisory lock de sessão, cancelamento durante execução, preview_token obsoleto
fail-closed, payload adulterado e a flag OFF por padrão.
"""
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Reusa as fixtures e helpers do contrato congelado, sem modificá-los.
from tests_postgres.test_migration_phase3_postgres import ctx as ctx  # noqa: PLC0414
from tests_postgres.test_migration_phase3_postgres import queue as queue  # noqa: PLC0414
from tests_postgres.test_migration_phase3_postgres import schema as schema  # noqa: PLC0414
from tests_postgres.test_migration_phase3_postgres import scalar, submit


@pytest.fixture(autouse=True)
def _clean_async_table(schema):
    # claim() é um poller GLOBAL; isola cada teste esvaziando a fila antes dele
    # (banco descartável, apenas jobs sintéticos).
    from core.database import get_connection
    connection = get_connection()
    try:
        connection.execute('TRUNCATE TABLE migration_async_jobs RESTART IDENTITY')
        connection.commit()
    finally:
        connection.close()


def _units(queue):
    return scalar(queue['conn'], 'SELECT count(*) FROM units WHERE company_id=%s', (queue['company_id'],))


def test_stale_attempt_fence_is_rejected(queue):
    from core.database import get_connection
    job = submit(queue)
    claim = queue['api'].claim(queue['conn'], owner='worker-a', lease_seconds=30)
    assert claim and claim['attempt'] == 1
    # Tentativa com attempt divergente é recusada e não executa nada.
    with pytest.raises((ValueError, PermissionError, LookupError)):
        queue['api'].execute_claim(job['id'], 'worker-a', claim['attempt'] + 1,
                                   connection_factory=get_connection)
    assert _units(queue) == 0
    assert queue['api'].get(queue['conn'], job['id'], queue['actor'])['status'] == 'claimed'


def test_expired_lease_reclaim_bumps_attempt_and_old_owner_is_fenced(queue):
    from core.database import get_connection
    job = submit(queue)
    first = queue['api'].claim(queue['conn'], owner='worker-a', lease_seconds=0)
    assert first and first['attempt'] == 1
    second = queue['api'].claim(queue['conn'], owner='worker-b', lease_seconds=30)
    assert second and second['id'] == job['id']
    assert second['attempt'] == 2 and second['owner'] == 'worker-b'
    # O dono antigo (attempt 1) não pode mais executar → sem dupla execução.
    with pytest.raises((ValueError, PermissionError, LookupError)):
        queue['api'].execute_claim(job['id'], 'worker-a', 1, connection_factory=get_connection)
    assert _units(queue) == 0


def test_execution_is_serialized_by_session_advisory_lock(queue):
    from core.database import get_connection
    from modules.data_migration import async_jobs
    job = submit(queue)
    claim = queue['api'].claim(queue['conn'], owner='worker-a', lease_seconds=30)
    blocker = get_connection()
    try:
        # Simula um worker vivo segurando o advisory de sessão do job.
        blocker.execute('SELECT pg_advisory_lock(%s, %s)', (async_jobs._ADVISORY_NS, int(job['id'])))
        with pytest.raises((ValueError, PermissionError, LookupError)):
            queue['api'].execute_claim(job['id'], 'worker-a', claim['attempt'],
                                       connection_factory=get_connection)
        assert _units(queue) == 0
    finally:
        blocker.execute('SELECT pg_advisory_unlock(%s, %s)', (async_jobs._ADVISORY_NS, int(job['id'])))
        blocker.commit()
        blocker.close()


def test_cancel_requested_while_claimed_aborts_before_any_write(queue):
    from core.database import get_connection
    job = submit(queue)
    claim = queue['api'].claim(queue['conn'], owner='worker-a', lease_seconds=30)
    # Pedido de cancelamento sinalizado enquanto reclamado.
    queue['conn'].execute('UPDATE migration_async_jobs SET cancel_requested=1 WHERE id=%s', (int(job['id']),))
    queue['conn'].commit()
    result = queue['api'].execute_claim(job['id'], 'worker-a', claim['attempt'],
                                        connection_factory=get_connection)
    assert result['status'] == 'cancelled'
    assert _units(queue) == 0
    assert queue['api'].get(queue['conn'], job['id'], queue['actor'])['status'] == 'cancelled'


def test_stale_preview_token_fails_closed_without_writes(queue):
    from core.database import get_connection
    # Token obsoleto: run_migration recomputa o plano e recusa (preview_stale).
    job = queue['api'].submit(
        queue['conn'], actor=queue['actor'], entity='unidades', source_kind='csv',
        raw=queue['raw'], mapping={'name': 'name', 'unit_type': 'unit_type', 'city': 'city'},
        strategy='insert_only', request_key=uuid.uuid4().hex, source_name='stale.csv',
        preview_token='token-obsoleto-invalido')
    queue['submitted'].append(job['id'])
    claim = queue['api'].claim(queue['conn'], owner='worker-a', lease_seconds=30)
    result = queue['api'].execute_claim(job['id'], 'worker-a', claim['attempt'],
                                        connection_factory=get_connection)
    assert result['status'] == 'failed'
    assert _units(queue) == 0


def test_tampered_payload_fails_closed_without_writes(queue):
    from core.database import get_connection
    job = submit(queue)
    # Adultera o ciphertext: decrypt/hash falham → job failed, sem escrita.
    queue['conn'].execute(
        "UPDATE migration_async_jobs SET input_ciphertext=%s WHERE id=%s",
        ('gAAAAABmX-corrompido-invalido', int(job['id'])))
    queue['conn'].commit()
    claim = queue['api'].claim(queue['conn'], owner='worker-a', lease_seconds=30)
    result = queue['api'].execute_claim(job['id'], 'worker-a', claim['attempt'],
                                        connection_factory=get_connection)
    assert result['status'] == 'failed'
    assert _units(queue) == 0


def test_submit_refused_when_feature_disabled(queue, monkeypatch):
    monkeypatch.delenv('MIGRATION_ASYNC_ENABLED', raising=False)
    with pytest.raises(PermissionError):
        submit(queue)


def _worker():
    import importlib.util
    import pathlib
    path = pathlib.Path(__file__).resolve().parents[1] / 'scripts' / 'migration_worker.py'
    spec = importlib.util.spec_from_file_location('migration_worker_mod', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_worker_preflight_refuses_when_disabled(monkeypatch):
    monkeypatch.delenv('MIGRATION_ASYNC_ENABLED', raising=False)
    ok, reason = _worker().preflight()
    assert ok is False and 'MIGRATION_ASYNC_ENABLED' in reason


def test_worker_preflight_ok_when_ready(queue):
    ok, reason = _worker().preflight()
    assert ok is True and reason == 'ok'


def test_worker_run_once_processes_a_queued_job(queue):
    from core.database import get_connection
    from modules.data_migration import async_jobs
    job = submit(queue)
    result = async_jobs.run_once('worker-loop', lease_seconds=30, connection_factory=get_connection)
    assert result and result['id'] == job['id'] and result['status'] == 'completed'
    assert _units(queue) == 1
