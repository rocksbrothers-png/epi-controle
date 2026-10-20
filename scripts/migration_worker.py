"""Worker da fila de migração assíncrona (MIG-DATA-FIX-V1 — Fase 3).

Processa, num processo separado, os jobs enfileirados pelo Centro de Migração,
reutilizando ``run_migration`` (sem segundo motor). DESLIGADO por padrão: só
roda com ``MIGRATION_ASYNC_ENABLED`` ligado, em PostgreSQL (nunca SQLite), com o
schema da fila presente, ``MIGRATION_INPUT_KEY`` válido e um DSN com afinidade de
sessão (o pooler de transação, porta 6543, é incompatível com advisory de sessão).

Uso:
  python scripts/migration_worker.py            # loop contínuo
  python scripts/migration_worker.py --once     # processa no máximo 1 job e sai

Logs expõem apenas identificadores/timing/códigos seguros (nunca payload,
credencial ou texto cru de exceção).
"""
import os
import signal
import socket
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LEASE_SECONDS = int(os.environ.get('MIGRATION_WORKER_LEASE_SECONDS', '120'))
POLL_SECONDS = float(os.environ.get('MIGRATION_WORKER_POLL_SECONDS', '2'))
MAX_RUNTIME_SECONDS = int(os.environ.get('MIGRATION_WORKER_MAX_RUNTIME', '0'))  # 0 = sem limite


def _truthy(name):
    return str(os.environ.get(name, '')).strip().lower() in ('1', 'true', 'yes', 'on')


def preflight():
    """Retorna (ok, motivo). Bloqueia ativação insegura (condição #13 da revisão)."""
    from epi_backend.config import DATABASE_URL
    if not _truthy('MIGRATION_ASYNC_ENABLED'):
        return False, 'MIGRATION_ASYNC_ENABLED desligado (feature OFF por padrão).'
    if not DATABASE_URL or not str(DATABASE_URL).startswith('postgres'):
        return False, 'Worker exige PostgreSQL (nunca SQLite).'
    if ':6543' in str(DATABASE_URL):
        return False, 'DSN parece pooler de transação (porta 6543); advisory de sessão exige DSN direto/session-pooling.'
    key = str(os.environ.get('MIGRATION_INPUT_KEY', '')).strip()
    if not key:
        return False, 'MIGRATION_INPUT_KEY ausente (chave Fernet do payload).'
    try:
        from cryptography.fernet import Fernet
        Fernet(key.encode())
    except Exception:
        return False, 'MIGRATION_INPUT_KEY inválida.'
    from core.database import get_connection
    connection = get_connection()
    try:
        row = connection.execute("SELECT to_regclass('public.migration_async_jobs') AS t").fetchone()
        if not row or row['t'] is None:
            return False, 'Schema da fila ausente (aplique a migração 035_migration_async_jobs).'
    finally:
        connection.close()
    return True, 'ok'


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    once = '--once' in argv
    from epi_backend.http_utils import structured_log

    ok, reason = preflight()
    if not ok:
        # Recusa segura: não é erro de processo, é a feature desligada/incompatível.
        structured_log('warning', 'migration_worker.refused', reason=reason)
        return 0

    from core.database import get_connection
    from modules.data_migration import async_jobs

    owner = f'{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}'
    stop = {'flag': False}

    def _graceful(_signum, _frame):
        stop['flag'] = True

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, _graceful)
        except Exception:
            pass

    started = time.monotonic()
    processed = 0
    structured_log('info', 'migration_worker.started', owner=owner, once=once, lease=LEASE_SECONDS)
    while not stop['flag']:
        try:
            result = async_jobs.run_once(owner, lease_seconds=LEASE_SECONDS, connection_factory=get_connection)
        except Exception as exc:
            # Nunca logar o texto cru da exceção — só o tipo.
            structured_log('warning', 'migration_worker.iteration_error', error=type(exc).__name__)
            result = None
        if result is not None:
            processed += 1
            structured_log('info', 'migration_worker.processed',
                           job_id=result.get('id'), status=result.get('status'))
            if once:
                break
            continue  # há trabalho: tenta o próximo imediatamente
        if once:
            break
        if MAX_RUNTIME_SECONDS and (time.monotonic() - started) >= MAX_RUNTIME_SECONDS:
            break
        time.sleep(POLL_SECONDS)
    structured_log('info', 'migration_worker.stopped', owner=owner, processed=processed)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
