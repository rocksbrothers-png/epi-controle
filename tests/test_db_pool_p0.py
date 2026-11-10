"""P0 — pool PostgreSQL: teto rígido, espera limitada, devolução limpa.

Sem banco: as conexões são falsas e determinísticas, para que cada invariante
seja provado isoladamente. A prova contra PostgreSQL real (HTTP, JWT, carga,
isolamento entre empresas) está em
``tests_postgres/test_db_pool_p0_postgres.py``.
"""

import random
import threading
import time

import pytest

from core.db_pool import BoundedConnectionPool, PoolError, PoolSaturatedError

IDLE, ACTIVE, INTRANS, INERROR, UNKNOWN = 0, 1, 2, 3, 4


class FakeCursor:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql):
        if self._conn.ping_fails:
            raise RuntimeError('server closed the connection unexpectedly')
        self._conn.pings += 1
        self._conn.status = INTRANS

    def fetchone(self):
        return (1,)

    def close(self):
        pass


class FakeConn:
    _seq = 0

    def __init__(self):
        FakeConn._seq += 1
        self.serial = FakeConn._seq
        self.closed = 0
        self.status = IDLE
        self.rollbacks = 0
        self.pings = 0
        self.ping_fails = False
        self.rollback_fails = False

        conn = self

        class _Info:
            @property
            def transaction_status(self):
                return conn.status
        self.info = _Info()

    def cursor(self):
        return FakeCursor(self)

    def rollback(self):
        if self.rollback_fails:
            raise RuntimeError('rollback failed')
        self.rollbacks += 1
        self.status = IDLE

    def close(self):
        self.closed = 1


class Factory:
    def __init__(self, delay=0.0, fail=False):
        self.delay = delay
        self.fail = fail
        self.lock = threading.Lock()
        self.open_now = 0
        self.created = []

    def __call__(self):
        if self.delay:
            time.sleep(self.delay)  # o connect real libera o GIL: é aqui que a corrida acontecia
        if self.fail:
            raise ConnectionError('could not connect to server')
        conn = FakeConn()
        with self.lock:
            self.created.append(conn)
        return conn

    def alive(self):
        return sum(1 for c in self.created if not c.closed)


def make_pool(factory=None, **kw):
    kw.setdefault('minconn', 0)
    kw.setdefault('maxconn', 10)
    kw.setdefault('acquire_timeout', 1.0)
    kw.setdefault('ping_idle_seconds', 3600)
    return BoundedConnectionPool(factory or Factory(), **kw)


# ── O defeito do pool antigo (evidência que motivou a troca) ─────────────────

def test_simple_connection_pool_ultrapassa_maxconn_sob_threads(monkeypatch):
    """Caracteriza o defeito: ``SimpleConnectionPool`` (psycopg2) com maxconn=10
    abre uma conexão por thread quando o connect demora. É o comportamento que
    o servidor tinha em produção (uma thread por requisição)."""
    from psycopg2 import pool as pg_pool
    factory = Factory(delay=0.02)
    monkeypatch.setattr(pg_pool.psycopg2, 'connect', lambda *a, **k: factory())
    pool = pg_pool.SimpleConnectionPool(1, 10, 'dsn')
    got = []

    def worker():
        try:
            got.append(pool.getconn())
        except pg_pool.PoolError:
            return  # esgotamento também é um resultado possível do pool antigo
    threads = [threading.Thread(target=worker) for _ in range(30)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert factory.alive() > 10, 'se o psycopg2 passou a travar, este teste deve ser revisto'


# ── Teto rígido ──────────────────────────────────────────────────────────────

def test_teto_respeitado_com_connect_lento_e_30_threads():
    factory = Factory(delay=0.02)
    pool = make_pool(factory, maxconn=10, acquire_timeout=0.3)
    got, saturated = [], []
    lock = threading.Lock()

    def worker():
        try:
            conn = pool.getconn()
            with lock:
                got.append(conn)
        except PoolSaturatedError:
            with lock:
                saturated.append(1)
    threads = [threading.Thread(target=worker) for _ in range(30)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(got) == 10
    assert len(saturated) == 20
    assert factory.alive() == 10
    status = pool.status()
    assert status['in_use'] == 10 and status['peak_in_use'] == 10
    assert status['timeouts_total'] == 20


def test_estresse_sem_conexao_compartilhada_nem_vazamento():
    factory = Factory()
    pool = make_pool(factory, maxconn=5, max_idle=5, acquire_timeout=5)
    holders = {}
    errors = []
    lock = threading.Lock()

    def worker(seed):
        rnd = random.Random(seed)
        for _ in range(300):
            conn = pool.getconn()
            with lock:
                if holders.get(conn.serial):
                    errors.append('mesma conexão em duas threads')
                holders[conn.serial] = True
            if rnd.random() < 0.3:
                conn.status = INTRANS  # transação esquecida aberta
            if rnd.random() < 0.05:
                conn.status = INERROR
            with lock:
                holders[conn.serial] = False
            pool.putconn(conn)
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    status = pool.status()
    assert errors == []
    assert status['in_use'] == 0 and status['opening'] == 0
    assert status['peak_in_use'] <= 5
    assert factory.alive() <= 5
    assert all(c.status == IDLE for c in factory.created if not c.closed)


# ── Saturação, espera e recuperação ──────────────────────────────────────────

def test_saturado_falha_controlada_no_prazo():
    pool = make_pool(maxconn=2, acquire_timeout=0.2)
    a, b = pool.getconn(), pool.getconn()
    started = time.monotonic()
    with pytest.raises(PoolSaturatedError) as info:
        pool.getconn()
    elapsed = time.monotonic() - started
    assert 0.18 <= elapsed < 1.0
    assert isinstance(info.value, PoolError)
    assert 'saturated' in str(info.value)
    pool.putconn(a)
    pool.putconn(b)
    assert pool.getconn() is not None  # recupera depois da saturação


def test_espera_e_recebe_conexao_devolvida():
    pool = make_pool(maxconn=1, max_idle=1, acquire_timeout=2)
    first = pool.getconn()
    result = {}

    def waiter():
        result['conn'] = pool.getconn()
    t = threading.Thread(target=waiter)
    t.start()
    time.sleep(0.1)
    assert pool.status()['waiting'] == 1
    pool.putconn(first)
    t.join(2)
    assert result['conn'] is first
    status = pool.status()
    assert status['waited_total'] == 1 and status['max_wait_ms'] >= 50


def test_acquire_timeout_zero_e_falha_imediata():
    pool = make_pool(maxconn=1, acquire_timeout=0)
    pool.getconn()
    started = time.monotonic()
    with pytest.raises(PoolSaturatedError):
        pool.getconn()
    assert time.monotonic() - started < 0.05


def test_falha_de_connect_libera_a_vaga():
    factory = Factory(fail=True)
    pool = make_pool(factory, maxconn=1, acquire_timeout=0.1)
    for _ in range(3):
        with pytest.raises(ConnectionError):
            pool.getconn()
    assert pool.status()['opening'] == 0
    factory.fail = False
    assert pool.getconn() is not None


def test_closeall_acorda_quem_espera():
    pool = make_pool(maxconn=1, acquire_timeout=5)
    pool.getconn()
    errors = []

    def waiter():
        try:
            pool.getconn()
        except PoolSaturatedError:
            errors.append('saturated')
        except PoolError as exc:
            errors.append(str(exc))
    t = threading.Thread(target=waiter)
    t.start()
    time.sleep(0.05)
    pool.closeall()
    t.join(1)
    assert errors == ['connection pool is closed']


# ── Devolução limpa (invariante: nada de transação de outra requisição) ──────

@pytest.mark.parametrize('status', [INTRANS, INERROR, ACTIVE])
def test_transacao_aberta_ou_abortada_e_desfeita_na_devolucao(status):
    pool = make_pool(max_idle=1)
    conn = pool.getconn()
    conn.status = status
    pool.putconn(conn)
    assert conn.rollbacks == 1 and conn.status == IDLE and not conn.closed
    assert pool.getconn() is conn


def test_conexao_ociosa_nao_sofre_rollback_extra():
    pool = make_pool(max_idle=1)
    conn = pool.getconn()
    pool.putconn(conn)
    assert conn.rollbacks == 0


def test_rollback_que_falha_descarta_a_conexao():
    pool = make_pool(max_idle=1)
    conn = pool.getconn()
    conn.status = INERROR
    conn.rollback_fails = True
    pool.putconn(conn)
    assert conn.closed
    assert pool.status()['discarded_total'] == 1
    assert pool.getconn() is not conn


@pytest.mark.parametrize('broken', ['closed', 'unknown'])
def test_conexao_quebrada_e_descartada(broken):
    pool = make_pool(max_idle=1)
    conn = pool.getconn()
    if broken == 'closed':
        conn.closed = 2
    else:
        conn.status = UNKNOWN
    pool.putconn(conn)
    assert pool.status()['available'] == 0
    assert pool.getconn() is not conn


def test_discard_fecha_mesmo_saudavel():
    pool = make_pool(max_idle=1)
    conn = pool.getconn()
    pool.putconn(conn, discard=True)
    assert conn.closed and pool.status()['available'] == 0


def test_max_idle_preserva_o_comportamento_antigo():
    """Padrão = minconn: como o SimpleConnectionPool, devolução acima de
    max_idle fecha a conexão em vez de guardá-la."""
    pool = make_pool(minconn=1, maxconn=5)
    assert pool.max_idle == 1
    conns = [pool.getconn() for _ in range(3)]
    for conn in conns:
        pool.putconn(conn)
    assert pool.status()['available'] == 1
    assert sum(1 for c in conns if c.closed) == 2


def test_devolucao_dupla_ou_alheia_nao_quebra_nem_guarda():
    pool = make_pool(max_idle=2)
    conn = pool.getconn()
    pool.putconn(conn)
    pool.putconn(conn)  # dupla
    foreign = FakeConn()
    pool.putconn(foreign)
    assert foreign.closed
    assert pool.status()['available'] == 1


# ── Conexão derrubada pelo servidor enquanto ociosa ──────────────────────────

def test_ociosa_fechada_e_trocada_antes_da_entrega():
    pool = make_pool(max_idle=1)
    conn = pool.getconn()
    pool.putconn(conn)
    conn.closed = 2  # servidor reiniciou
    fresh = pool.getconn()
    assert fresh is not conn
    assert pool.status()['discarded_total'] == 1


def test_ping_de_ociosa_antiga_e_recuperacao_quando_falha():
    clock = {'t': 0.0}
    pool = make_pool(max_idle=1, ping_idle_seconds=30, clock=lambda: clock['t'])
    conn = pool.getconn()
    pool.putconn(conn)
    clock['t'] = 10
    assert pool.getconn() is conn and conn.pings == 0  # recente: sem ping
    pool.putconn(conn)
    clock['t'] = 100
    assert pool.getconn() is conn and conn.pings == 1  # antiga: ping
    assert conn.status == IDLE  # o ping não deixa transação aberta
    pool.putconn(conn)
    clock['t'] = 200
    conn.ping_fails = True
    fresh = pool.getconn()
    assert fresh is not conn and conn.closed


# ── Integração com core.database, HTTP e pontos de estado de sessão ──────────

def test_wrapper_discard_chega_ao_pool(monkeypatch):
    import core.database as cdb
    calls = []
    monkeypatch.setattr(cdb, 'release_connection', lambda raw, discard=False: calls.append(discard))
    wrapper = cdb.PostgresConnectionWrapper(object(), release_hook=cdb.release_connection)
    wrapper.discard()
    wrapper.close()  # já liberada: no-op
    assert calls == [True]
    wrapper = cdb.PostgresConnectionWrapper(object(), release_hook=cdb.release_connection)
    wrapper.close()
    assert calls == [True, False]


def test_db_pool_status_expoe_metricas_sem_dados_sensiveis(monkeypatch):
    import core.database as cdb
    pool = make_pool(maxconn=3)
    monkeypatch.setattr(cdb, '_CONNECTION_POOL', pool)
    data = cdb.db_pool_status()
    for key in ('maxconn', 'in_use', 'available', 'waiting', 'timeouts_total',
                'discarded_total', 'peak_in_use', 'acquire_timeout_seconds'):
        assert key in data
    assert all(isinstance(v, (int, float, bool)) for v in data.values())


class _FakeHandler:
    def __init__(self):
        self.path = '/api/employees?token=segredo'
        self.command = 'GET'
        self.status = None
        self.headers = {}
        self.body = b''

        handler = self

        class _W:
            def write(self, data):
                handler.body += data
        self.wfile = _W()

    def send_response(self, status):
        self.status = status

    def send_header(self, name, value):
        self.headers[name] = value

    def end_headers(self):
        pass


def test_saturacao_vira_503_com_retry_after():
    import json

    from epi_backend.http_utils import send_db_pool_saturated
    handler = _FakeHandler()
    send_db_pool_saturated(handler, 'GET', handler.path)
    assert handler.status == 503
    assert handler.headers['Retry-After'] == '1'
    payload = json.loads(handler.body)
    assert payload == {'ok': False, 'error': {
        'code': 'DB_POOL_SATURATED',
        'message': 'Servidor ocupado no momento. Tente novamente em instantes.'}}


def test_todos_os_metodos_http_tratam_saturacao_antes_do_500():
    import inspect

    import app
    for method in ('do_GET', 'do_POST', 'do_PUT', 'do_DELETE'):
        source = inspect.getsource(getattr(app.EpiHandler, method))
        assert 'except PoolSaturatedError' in source, method
        assert source.index('except PoolSaturatedError') < source.index("'http.unhandled_error'"), method


def test_servidor_http_com_fila_maior_que_5():
    import app
    assert app.EpiHTTPServer.request_queue_size >= 128
    assert app.EpiHTTPServer.daemon_threads is True


def test_smtp_com_timeout(monkeypatch):
    import epi_backend.config as config
    from epi_backend import mailer
    seen = {}

    class _SMTP:
        def __init__(self, host, port, timeout=None):
            seen['timeout'] = timeout

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def ehlo(self):
            pass

        def starttls(self):
            pass

        def login(self, *a):
            pass

        def sendmail(self, *a):
            pass
    monkeypatch.setattr(config, 'SMTP_HOST', 'smtp.example.com')
    monkeypatch.setattr(config, 'SMTP_USER', 'u')
    monkeypatch.setattr(mailer.smtplib, 'SMTP', _SMTP)
    mailer.send_email('a@example.com', 'x', 'y')
    assert seen['timeout'] == mailer.SMTP_TIMEOUT_SECONDS and seen['timeout'] > 0


def _falhar(mensagem):
    raise RuntimeError(mensagem)


class _SessionConn:
    def __init__(self, unlock_fails=False):
        self.closed_called = 0
        self.discarded = 0
        self.unlock_fails = unlock_fails

    def close(self):
        self.closed_called += 1

    def discard(self):
        self.discarded += 1


@pytest.mark.parametrize('pendente,descarta', [(True, True), (False, False)])
def test_bootstrap_descarta_conexao_com_advisory_lock_preso(pendente, descarta):
    from core.bootstrap import _conexao_do_bootstrap
    conn = _SessionConn()
    with pytest.raises(RuntimeError):
        with _conexao_do_bootstrap(conn, {'advisory_lock_pendente': pendente}):
            _falhar('falha no meio do bootstrap')
    assert (conn.discarded, conn.closed_called) == ((1, 0) if descarta else (0, 1))


def test_job_assincrono_descarta_conexao_quando_unlock_falha(monkeypatch):
    from modules.data_migration import async_jobs
    monkeypatch.setenv('MIGRATION_ASYNC_ENABLED', '1')
    monkeypatch.setattr(async_jobs, '_async_enabled', lambda: True)

    class _Result:
        def __init__(self, row):
            self._row = row

        def fetchone(self):
            return self._row

    class _JobConn(_SessionConn):
        def execute(self, sql, params=None):
            if 'pg_try_advisory_lock' in sql:
                return _Result({'ok': True})
            if 'pg_advisory_unlock' in sql:
                raise RuntimeError('connection lost')
            return _Result(None)  # job inexistente

        def rollback(self):
            pass

        def commit(self):
            pass
    conn = _JobConn()
    with pytest.raises(LookupError):
        async_jobs.execute_claim(1, 'w', 1, connection_factory=lambda: conn)
    assert (conn.discarded, conn.closed_called) == (1, 0)


def test_configuracao_fora_da_faixa_e_saneada():
    pool = make_pool(minconn=-3, maxconn=0)
    assert (pool.minconn, pool.maxconn) == (0, 1)
    pool = make_pool(minconn=50, maxconn=4)
    assert (pool.minconn, pool.maxconn, pool.max_idle) == (4, 4, 4)
