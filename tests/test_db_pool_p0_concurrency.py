"""P0.1 — revisão adversarial do BoundedConnectionPool.

Cenários concorrentes DETERMINÍSTICOS: cada entrelaçamento é forçado com
eventos entre threads (nada de ``sleep`` esperando a corrida acontecer).
"""

import threading

import pytest

from core.db_pool import BoundedConnectionPool, PoolError

IDLE, INTRANS = 0, 2
TIMEOUT = 5


class GatedConn:
    """Conexão falsa cujo rollback e ping podem ser retidos por um evento."""

    def __init__(self):
        self.closed = 0
        self.status = IDLE
        self.rollbacks = 0
        self.closes = 0
        self.in_rollback = threading.Event()
        self.release_rollback = None      # threading.Event quando o rollback deve bloquear
        self.in_ping = threading.Event()
        self.release_ping = None
        self.concurrent_rollbacks = 0
        self._active = 0
        self._lock = threading.Lock()
        conn = self

        class _Info:
            @property
            def transaction_status(self):
                return conn.status
        self.info = _Info()

    def rollback(self):
        with self._lock:
            self._active += 1
            if self._active > 1:
                self.concurrent_rollbacks += 1
        self.in_rollback.set()
        try:
            if self.release_rollback is not None:
                assert self.release_rollback.wait(TIMEOUT)
            self.rollbacks += 1
            self.status = IDLE
        finally:
            with self._lock:
                self._active -= 1

    def cursor(self):
        conn = self

        class _Cursor:
            def execute(self, sql):
                conn.in_ping.set()
                if conn.release_ping is not None:
                    assert conn.release_ping.wait(TIMEOUT)
                conn.status = INTRANS

            def fetchone(self):
                return (1,)

            def close(self):
                pass
        return _Cursor()

    def close(self):
        self.closes += 1
        self.closed = 1


class GatedFactory:
    def __init__(self):
        self.created = []
        self.in_connect = threading.Event()
        self.release_connect = None
        self.fail_after = None

    def __call__(self):
        self.in_connect.set()
        if self.release_connect is not None:
            assert self.release_connect.wait(TIMEOUT)
        if self.fail_after is not None and len(self.created) >= self.fail_after:
            raise ConnectionError('could not connect to server')
        conn = GatedConn()
        self.created.append(conn)
        return conn


def make_pool(factory, **kw):
    kw.setdefault('minconn', 0)
    kw.setdefault('maxconn', 4)
    kw.setdefault('max_idle', 4)
    kw.setdefault('acquire_timeout', 1)
    kw.setdefault('ping_idle_seconds', 3600)
    return BoundedConnectionPool(factory, **kw)


def run(target):
    box = {}

    def wrapper():
        try:
            box['value'] = target()
        except BaseException as exc:  # noqa: BLE001 — o teste inspeciona a exceção
            box['error'] = exc
    thread = threading.Thread(target=wrapper, daemon=True)
    thread.start()
    return thread, box


def join(thread):
    thread.join(TIMEOUT)
    assert not thread.is_alive(), 'thread travada'


# ── 1. Encerramento concorrente ──────────────────────────────────────────────

def test_closeall_durante_abertura_nao_entrega_conexao():
    """getconn está DENTRO do connect (fora da trava) quando closeall roda."""
    factory = GatedFactory()
    pool = make_pool(factory)
    factory.release_connect = threading.Event()
    thread, box = run(pool.getconn)
    assert factory.in_connect.wait(TIMEOUT)
    assert pool.status()['opening'] == 1
    pool.closeall()                      # pool encerrado com uma abertura em curso
    factory.release_connect.set()        # o connect termina DEPOIS do encerramento
    join(thread)
    assert isinstance(box.get('error'), PoolError), box   # não entrega conexão nova
    assert len(factory.created) == 1 and factory.created[0].closed == 1   # nem a deixa aberta
    status = pool.status()
    assert (status['in_use'], status['opening'], status['available']) == (0, 0, 0)


def test_closeall_durante_ping_de_ociosa_nao_entrega_conexao():
    """A conexão já saiu da lista de ociosas e está no ping quando closeall roda."""
    factory = GatedFactory()
    pool = make_pool(factory, ping_idle_seconds=0)
    conn = pool.getconn()
    pool.putconn(conn)
    conn.release_ping = threading.Event()
    thread, box = run(pool.getconn)
    assert conn.in_ping.wait(TIMEOUT)
    pool.closeall()
    conn.release_ping.set()
    join(thread)
    assert isinstance(box.get('error'), PoolError), box
    assert conn.closed == 1
    status = pool.status()
    assert (status['in_use'], status['opening'], status['available']) == (0, 0, 0)


def test_closeall_fecha_ociosas_e_devolucao_posterior_fecha_a_em_uso():
    factory = GatedFactory()
    pool = make_pool(factory)
    a, b = pool.getconn(), pool.getconn()
    pool.putconn(a)
    pool.closeall()
    pool.closeall()                      # idempotente
    assert a.closed == 1 and b.closed == 0   # a em uso não é arrancada de quem a usa
    with pytest.raises(PoolError):
        pool.getconn()
    pool.putconn(b)                      # devolução depois do encerramento
    assert b.closed == 1
    status = pool.status()
    assert (status['in_use'], status['opening'], status['available']) == (0, 0, 0)


def test_falha_no_meio_da_abertura_inicial_nao_deixa_conexao_aberta():
    factory = GatedFactory()
    factory.fail_after = 2
    with pytest.raises(ConnectionError):
        make_pool(factory, minconn=3)
    assert len(factory.created) == 2
    assert all(conn.closed == 1 for conn in factory.created)


# ── 2. Devolução concorrente ─────────────────────────────────────────────────

def test_duas_devolucoes_simultaneas_da_mesma_conexao():
    """A 2ª devolução chega enquanto a 1ª está no rollback (fora da trava)."""
    factory = GatedFactory()
    pool = make_pool(factory)
    conn = pool.getconn()
    conn.status = INTRANS
    conn.release_rollback = threading.Event()
    first, box1 = run(lambda: pool.putconn(conn))
    assert conn.in_rollback.wait(TIMEOUT)            # 1ª devolução dentro do rollback
    second, box2 = run(lambda: pool.putconn(conn))   # 2ª devolução da MESMA conexão
    join(second)                                     # não pode ficar esperando a 1ª…
    assert conn.closed == 0, 'a 2ª devolução fechou a conexão que a 1ª está limpando'
    conn.release_rollback.set()
    join(first)
    assert 'error' not in box1 and 'error' not in box2
    assert conn.rollbacks == 1 and conn.concurrent_rollbacks == 0   # limpeza exclusiva
    assert conn.closed == 0
    status = pool.status()
    assert (status['in_use'], status['available']) == (0, 1)        # guardada UMA vez
    x, y = pool.getconn(), pool.getconn()
    assert x is not y, 'a mesma conexão foi entregue a dois donos'


def test_devolucao_dupla_sequencial_nao_duplica_nem_fecha_a_ociosa():
    factory = GatedFactory()
    pool = make_pool(factory)
    conn = pool.getconn()
    pool.putconn(conn)
    pool.putconn(conn)
    assert conn.closed == 0
    assert pool.status()['available'] == 1
    x, y = pool.getconn(), pool.getconn()
    assert x is conn and y is not conn


def test_conexao_em_limpeza_conta_no_teto():
    """Enquanto a devolução está no rollback a conexão segue aberta no banco:
    não pode liberar vaga para abrir outra além do teto."""
    factory = GatedFactory()
    pool = make_pool(factory, maxconn=1, acquire_timeout=0.2)
    conn = pool.getconn()
    conn.status = INTRANS
    conn.release_rollback = threading.Event()
    returning, _ = run(lambda: pool.putconn(conn))
    assert conn.in_rollback.wait(TIMEOUT)
    with pytest.raises(PoolError):
        pool.getconn()                   # teto 1: nada de 2ª conexão durante a limpeza
    assert len(factory.created) == 1
    conn.release_rollback.set()
    join(returning)
    assert pool.getconn() is conn


def test_estresse_devolucao_dupla_concorrente():
    """Complemento não determinístico: 8 threads devolvendo cada conexão 2×."""
    factory = GatedFactory()
    pool = make_pool(factory, maxconn=4, acquire_timeout=5)
    errors = []
    holders = {}
    lock = threading.Lock()

    def worker():
        for _ in range(200):
            conn = pool.getconn()
            with lock:
                if holders.get(id(conn)):
                    errors.append('duas threads com a mesma conexão')
                holders[id(conn)] = True
            conn.status = INTRANS
            with lock:
                holders[id(conn)] = False
            a = threading.Thread(target=pool.putconn, args=(conn,))
            b = threading.Thread(target=pool.putconn, args=(conn,))
            a.start(); b.start(); a.join(); b.join()
    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(60)
    status = pool.status()
    assert errors == []
    assert status['in_use'] == 0 and status['available'] <= 4
    assert all(c.concurrent_rollbacks == 0 for c in factory.created)


# ── 3. Advisory lock de sessão: toda saída descarta quando há dúvida ─────────

class _Row(dict):
    pass


class LockConn:
    """Conexão falsa que registra close/discard e roteia o SQL do lock."""

    def __init__(self, acquire=True, release=True):
        self.acquire = acquire        # valor devolvido, ou exceção a levantar
        self.release = release
        self.closed_called = 0
        self.discarded = 0
        self.sql = []

    def execute(self, sql, params=None):
        self.sql.append(sql)
        outcome = None
        if 'pg_try_advisory_lock' in sql:
            outcome = self.acquire
        elif 'pg_advisory_unlock' in sql:
            outcome = self.release
        if isinstance(outcome, BaseException):
            raise outcome
        row = None if outcome is None else _Row(value=outcome)

        class _Cursor:
            def fetchone(self):
                return row
        return _Cursor()

    def rollback(self):
        pass

    def commit(self):
        pass

    def close(self):
        self.closed_called += 1

    def discard(self):
        self.discarded += 1


def _lock(conn):
    from core.session_locks import SessionAdvisoryLock
    return SessionAdvisoryLock(conn, acquire_sql='SELECT pg_try_advisory_lock(%s) AS ok',
                               release_sql='SELECT pg_advisory_unlock(%s) AS released', params=(1,))


def test_lock_adquirido_e_liberado_devolve_ao_pool():
    conn = LockConn()
    lock = _lock(conn)
    assert lock.try_acquire() is True and lock.must_discard     # preso: descartaria
    assert lock.release() is True and not lock.must_discard
    lock.finish()
    assert (conn.discarded, conn.closed_called) == (0, 1)


def test_lock_nao_concedido_devolve_ao_pool():
    conn = LockConn(acquire=False)
    lock = _lock(conn)
    assert lock.try_acquire() is False and not lock.must_discard
    lock.finish()
    assert (conn.discarded, conn.closed_called) == (0, 1)


def test_saida_com_lock_preso_descarta():
    conn = LockConn()
    lock = _lock(conn)
    lock.try_acquire()
    lock.finish()                         # saída sem unlock (exceção no meio do fluxo)
    assert (conn.discarded, conn.closed_called) == (1, 0)


def test_tentativa_que_levanta_excecao_deixa_estado_incerto():
    conn = LockConn(acquire=RuntimeError('connection reset'))
    lock = _lock(conn)
    with pytest.raises(RuntimeError):
        lock.try_acquire()
    assert lock.must_discard              # o servidor pode ter concedido antes do erro
    lock.finish()
    assert (conn.discarded, conn.closed_called) == (1, 0)


@pytest.mark.parametrize('release', [False, None, RuntimeError('connection lost')])
def test_unlock_nao_confirmado_descarta(release):
    conn = LockConn(release=release)
    lock = _lock(conn)
    lock.try_acquire()
    if isinstance(release, BaseException):
        with pytest.raises(RuntimeError):
            lock.release()
    else:
        assert lock.release() is False
    lock.finish()
    assert (conn.discarded, conn.closed_called) == (1, 0)


def test_duvida_nao_e_desfeita_por_unlock_posterior():
    """Reentrante: 1ª tentativa falhou (pode ter sido concedida), 2ª concedida,
    um unlock confirmado — pode restar um nível preso."""
    conn = LockConn(acquire=RuntimeError('timeout'))
    lock = _lock(conn)
    with pytest.raises(RuntimeError):
        lock.try_acquire()
    conn.acquire = True
    assert lock.try_acquire() is True
    assert lock.release() is True
    assert lock.must_discard
    lock.finish()
    assert (conn.discarded, conn.closed_called) == (1, 0)


def _run_job(conn, monkeypatch):
    from modules.data_migration import async_jobs
    monkeypatch.setattr(async_jobs, '_async_enabled', lambda: True)
    return async_jobs.execute_claim(1, 'w', 1, connection_factory=lambda: conn)


def test_job_tentativa_de_lock_com_excecao_descarta(monkeypatch):
    conn = LockConn(acquire=RuntimeError('connection reset'))
    with pytest.raises(RuntimeError):
        _run_job(conn, monkeypatch)
    assert (conn.discarded, conn.closed_called) == (1, 0)


def test_job_outro_worker_detem_o_lock_devolve_ao_pool(monkeypatch):
    conn = LockConn(acquire=False)
    with pytest.raises(PermissionError):
        _run_job(conn, monkeypatch)
    assert (conn.discarded, conn.closed_called) == (0, 1)


@pytest.mark.parametrize('release,descarta', [(True, False), (False, True), (RuntimeError('lost'), True)])
def test_job_saida_por_excecao_depois_do_lock(monkeypatch, release, descarta):
    conn = LockConn(release=release)     # job inexistente → LookupError com o lock preso
    with pytest.raises(LookupError):
        _run_job(conn, monkeypatch)
    assert any('pg_advisory_unlock' in sql for sql in conn.sql)
    assert (conn.discarded, conn.closed_called) == ((1, 0) if descarta else (0, 1))


def test_bootstrap_usa_o_estado_do_lock_em_toda_saida():
    from core.bootstrap import _conexao_do_bootstrap
    for prepare, descarta in (
        (lambda lock: None, False),                               # lock nunca tentado
        (lambda lock: lock.try_acquire(), True),                  # preso e exceção no meio
        (lambda lock: (lock.try_acquire(), lock.release()), False),
    ):
        conn = LockConn()
        lock = _lock(conn)
        with pytest.raises(RuntimeError):
            with _conexao_do_bootstrap(conn, {'advisory_lock_pendente': False, 'lock': lock}):
                prepare(lock)
                _falha()
        assert (conn.discarded, conn.closed_called) == ((1, 0) if descarta else (0, 1))
    conn = LockConn(release=False)                                # unlock não confirmado, saída normal
    lock = _lock(conn)
    with _conexao_do_bootstrap(conn, {'advisory_lock_pendente': False, 'lock': lock}):
        lock.try_acquire()
        lock.release()
    assert (conn.discarded, conn.closed_called) == (1, 0)


def _falha():
    raise RuntimeError('falha no meio do bootstrap')


def test_bootstrap_e_job_nao_chamam_advisory_fora_do_acompanhamento():
    """Guarda: nenhum pg_try_advisory_lock/pg_advisory_unlock de SESSÃO solto no
    código de produção — todos passam por SessionAdvisoryLock."""
    import pathlib
    import re
    root = pathlib.Path(__file__).resolve().parents[1]
    offenders = []
    for folder in ('core', 'modules', 'epi_backend'):
        for path in (root / folder).rglob('*.py'):
            for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                if not re.search(r'pg_(try_)?advisory_(lock|unlock)\(', line) or line.lstrip().startswith('#'):
                    continue
                if 'acquire_sql=' in line or 'release_sql=' in line:
                    continue
                offenders.append(f'{path.relative_to(root)}:{number}')
    assert offenders == [], offenders
