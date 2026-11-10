"""Pool de conexões PostgreSQL thread-safe, com espera limitada (P0).

Por que existe
--------------
O servidor é um ``ThreadingHTTPServer`` (uma thread por requisição) e usava
``psycopg2.pool.SimpleConnectionPool``, que a própria documentação do psycopg2
declara NÃO ser seguro entre threads. Medido (``tests/test_db_pool_p0.py``):

* o teto não é respeitado: ``_getconn`` testa ``len(_used) == maxconn`` e só
  depois abre a conexão; o ``connect`` libera o GIL, várias threads passam pelo
  teste ao mesmo tempo e, com ``maxconn=10`` e 30 requisições simultâneas, 30
  conexões são abertas no banco. Como o teste é de IGUALDADE, depois de passar
  do teto ele nunca mais dispara;
* a contabilidade corrompe: chaves duplicadas em ``_getkey`` deixam entradas
  órfãs em ``_used`` ("trying to put unkeyed connection", ``KeyError``) e o
  pool passa a se declarar esgotado sem estar;
* esgotado, falha na hora (``PoolError``) — sem nenhuma espera.

O que este pool garante
-----------------------
* teto rígido: conexões em uso + conexões sendo abertas <= ``maxconn``;
* espera limitada por ``acquire_timeout`` e depois ``PoolSaturatedError``;
* devolução sempre limpa: transação aberta ou abortada é desfeita
  (``rollback``) antes de a conexão voltar; conexão quebrada é descartada;
* conexão ociosa há mais de ``ping_idle_seconds`` é testada (``SELECT 1``)
  antes de ser entregue — conexão derrubada pelo servidor não chega à rota;
* I/O de rede (connect, rollback, ping, close) nunca acontece segurando a trava.

Estado de SESSÃO (advisory lock de sessão, ``SET`` sem ``LOCAL``) não é
desfeito por ``rollback``. O código que cria esse estado devolve a conexão com
``discard=True`` quando não consegue desfazê-lo (ver ``core/bootstrap.py`` e
``modules/data_migration/async_jobs.py``). Nenhum caminho da aplicação grava
contexto de empresa/usuário na sessão do banco: o isolamento multi-tenant é
feito em SQL, por requisição.
"""

import threading
import time
from collections import deque

try:
    from psycopg2 import extensions as _ext
    from psycopg2.pool import PoolError
    _STATUS_IDLE = _ext.TRANSACTION_STATUS_IDLE
    _STATUS_UNKNOWN = _ext.TRANSACTION_STATUS_UNKNOWN
except ModuleNotFoundError:  # driver ausente: o pool não é construído, mas o módulo importa
    class PoolError(Exception):
        """Substituto quando o psycopg2 não está instalado."""
    _STATUS_IDLE = 0
    _STATUS_UNKNOWN = 4


class PoolSaturatedError(PoolError):
    """Nenhuma conexão ficou livre dentro do prazo de aquisição.

    Subclasse de ``psycopg2.pool.PoolError`` para que quem já tratava o erro do
    pool continue tratando. A mensagem é fixa e não carrega dado de requisição.
    """

    def __init__(self, timeout_seconds, maxconn):
        super().__init__(
            f'connection pool saturated: no free connection within {timeout_seconds:g}s (maxconn={maxconn})'
        )
        self.timeout_seconds = timeout_seconds
        self.maxconn = maxconn


def _transaction_status(conn):
    info = getattr(conn, 'info', None)
    if info is not None and hasattr(info, 'transaction_status'):
        return info.transaction_status
    return conn.get_transaction_status()


def _close_quietly(conn):
    try:
        conn.close()
    except Exception:  # noqa: BLE001, S110 — descarte: a conexão já é lixo
        pass


class BoundedConnectionPool:
    def __init__(self, connect, *, minconn, maxconn, max_idle=None, acquire_timeout=5.0,
                 ping_idle_seconds=30.0, clock=time.monotonic, on_event=None):
        # Configuração vem de variável de ambiente: valor fora da faixa é
        # saneado em vez de impedir o servidor de subir.
        maxconn = max(1, int(maxconn))
        minconn = min(max(0, int(minconn)), maxconn)
        max_idle = minconn if max_idle is None else int(max_idle)
        self.minconn = minconn
        self.maxconn = maxconn
        self.max_idle = max(minconn, min(max_idle, maxconn))
        self.acquire_timeout = max(0.0, float(acquire_timeout))
        self.ping_idle_seconds = float(ping_idle_seconds)
        self._connect = connect
        self._clock = clock
        self._on_event = on_event or (lambda *_a, **_k: None)
        self._cond = threading.Condition(threading.Lock())
        self._idle = deque()      # (conn, devolvida_em)
        self._in_use = {}         # id(conn) -> conn
        self._returning = set()   # ids em devolução (limpeza fora da trava); ainda contam no teto
        self._opening = 0
        self._waiting = 0
        self.closed = False
        self._stats = {
            'acquired_total': 0, 'created_total': 0, 'discarded_total': 0,
            'timeouts_total': 0, 'waited_total': 0, 'peak_in_use': 0,
            'max_wait_ms': 0.0, 'wait_ms_total': 0.0,
        }
        try:
            for _ in range(minconn):
                self._idle.append((self._connect(), self._clock()))
                self._stats['created_total'] += 1
        except BaseException:
            # Falha no meio da abertura inicial: as já abertas não ficam órfãs.
            for conn, _ in self._idle:
                _close_quietly(conn)
            self._idle.clear()
            raise

    # ── aquisição ────────────────────────────────────────────────────────────
    def getconn(self):
        started = self._clock()
        deadline = started + self.acquire_timeout
        waited = False
        while True:
            with self._cond:
                action = self._reserve(deadline)
                if action == 'wait':
                    waited = True
                    continue_waiting = True
                else:
                    continue_waiting = False
                while continue_waiting:
                    remaining = deadline - self._clock()
                    if remaining <= 0:
                        action = self._reserve(deadline, final=True)
                        break
                    self._waiting += 1
                    try:
                        self._cond.wait(remaining)
                    finally:
                        self._waiting -= 1
                    action = self._reserve(deadline)
                    continue_waiting = action == 'wait'
                if action == 'saturated':
                    self._stats['timeouts_total'] += 1
                    in_use, waiting = len(self._in_use), self._waiting
                elif action == 'reuse':
                    conn, returned_at = self._idle.pop()  # LIFO: a mais recente está "quente"
                    self._in_use[id(conn)] = conn
                    stale = self.ping_idle_seconds >= 0 and (self._clock() - returned_at) >= self.ping_idle_seconds
                else:  # 'open'
                    self._opening += 1

            if action == 'saturated':
                self._on_event('saturated', in_use=in_use, waiting=waiting, maxconn=self.maxconn,
                               timeout_seconds=self.acquire_timeout)
                raise PoolSaturatedError(self.acquire_timeout, self.maxconn)

            if action == 'open':
                try:
                    conn = self._connect()
                except BaseException:
                    with self._cond:
                        self._opening -= 1
                        self._cond.notify()
                    raise
                with self._cond:
                    self._opening -= 1
                    self._stats['created_total'] += 1
                    # closeall() pode ter rodado enquanto o connect estava fora
                    # da trava: pool encerrado não entrega conexão nova.
                    closed = self.closed
                    if closed:
                        self._cond.notify()
                    else:
                        self._in_use[id(conn)] = conn
                        self._record_acquire(started, waited)
                if closed:
                    _close_quietly(conn)
                    raise PoolError('connection pool is closed')
                return conn

            try:
                usable = self._usable(conn, ping=stale)
            except BaseException:
                usable = False
                raise
            finally:
                with self._cond:
                    # mesma janela do connect: o ping roda fora da trava
                    closed = self.closed
                    if usable and not closed:
                        self._record_acquire(started, waited)
                    else:
                        self._in_use.pop(id(conn), None)
                        if not usable:
                            self._stats['discarded_total'] += 1
                        self._cond.notify()
                if not usable or closed:
                    _close_quietly(conn)
            if closed:
                raise PoolError('connection pool is closed')
            if usable:
                return conn
            # conexão ociosa quebrada: descartada; tenta de novo dentro do mesmo prazo
            self._on_event('discarded', reason='broken_idle_connection')

    def _reserve(self, deadline, final=False):
        """Decide (com a trava) o que a aquisição faz agora."""
        if self.closed:
            raise PoolError('connection pool is closed')
        if self._idle:
            return 'reuse'
        if len(self._in_use) + self._opening < self.maxconn:
            return 'open'
        if final or deadline - self._clock() <= 0:
            return 'saturated'
        return 'wait'

    def _record_acquire(self, started, waited):
        # chamado com a trava
        self._stats['acquired_total'] += 1
        self._stats['peak_in_use'] = max(self._stats['peak_in_use'], len(self._in_use))
        if waited:
            wait_ms = (self._clock() - started) * 1000.0
            self._stats['waited_total'] += 1
            self._stats['wait_ms_total'] += wait_ms
            self._stats['max_wait_ms'] = max(self._stats['max_wait_ms'], wait_ms)

    @staticmethod
    def _usable(conn, ping):
        if getattr(conn, 'closed', 0):
            return False
        try:
            if _transaction_status(conn) != _STATUS_IDLE:
                return False
            if ping:
                cursor = conn.cursor()
                try:
                    cursor.execute('SELECT 1')
                    cursor.fetchone()
                finally:
                    cursor.close()
                conn.rollback()
            return True
        except Exception:  # noqa: BLE001 — qualquer falha aqui = conexão inutilizável
            return False

    # ── devolução ────────────────────────────────────────────────────────────
    def putconn(self, conn, discard=False):
        """Devolve ``conn``. Só UMA devolução é dona da conexão.

        A limpeza (rollback) é I/O e roda fora da trava; por isso a posse é
        tomada antes, com a trava: uma segunda devolução simultânea da mesma
        conexão encontra-a "em devolução" e sai sem tocá-la — sem rollback
        concorrente, sem fechar o que a primeira está limpando e sem guardar a
        conexão duas vezes (o que a entregaria a dois donos). Enquanto é limpa,
        a conexão continua contando no teto: ela ainda está aberta no banco.

        O pool não distingue uma devolução atrasada de um dono ANTIGO depois de
        a conexão ter sido reentregue (mesmo objeto); essa garantia é do
        ``PostgresConnectionWrapper``, que só devolve uma vez por aquisição.
        """
        key = id(conn)
        with self._cond:
            if self._in_use.get(key) is conn and key not in self._returning:
                self._returning.add(key)
                outcome = 'owned'
            elif key in self._returning or any(idle is conn for idle, _ in self._idle):
                outcome = 'duplicate'
            else:
                outcome = 'foreign'
        if outcome == 'duplicate':
            # Já devolvida (ou sendo devolvida) por outra chamada: não tocar.
            self._on_event('duplicate_return')
            return
        if outcome == 'foreign':
            # Conexão que o pool não conhece: nunca guardar, nunca derrubar a
            # requisição (o close() roda no __exit__ de closing()).
            self._on_event('foreign_connection_returned')
            _close_quietly(conn)
            return
        keep = False
        try:
            keep = (not discard) and self._reset(conn)
        finally:
            with self._cond:
                self._returning.discard(key)
                self._in_use.pop(key, None)
                stored = keep and not self.closed and len(self._idle) < self.max_idle
                if stored:
                    self._idle.append((conn, self._clock()))
                elif not keep:
                    self._stats['discarded_total'] += 1
                self._cond.notify()
            if not stored:
                _close_quietly(conn)

    @staticmethod
    def _reset(conn):
        """True se a conexão volta ao pool sem transação; False = descartar."""
        if getattr(conn, 'closed', 0):
            return False
        try:
            status = _transaction_status(conn)
            if status == _STATUS_UNKNOWN:
                return False
            if status != _STATUS_IDLE:
                conn.rollback()
                return _transaction_status(conn) == _STATUS_IDLE
            return True
        except Exception:  # noqa: BLE001 — rollback falhou: conexão inutilizável
            return False

    # ── diagnóstico e encerramento ───────────────────────────────────────────
    def status(self):
        with self._cond:
            data = dict(self._stats)
            data.update({
                'minconn': self.minconn,
                'maxconn': self.maxconn,
                'max_idle': self.max_idle,
                'acquire_timeout_seconds': self.acquire_timeout,
                'available': len(self._idle),
                'in_use': len(self._in_use),
                'returning': len(self._returning),
                'opening': self._opening,
                'waiting': self._waiting,
            })
        data['max_wait_ms'] = round(data['max_wait_ms'], 1)
        data['wait_ms_total'] = round(data['wait_ms_total'], 1)
        return data

    def closeall(self):
        """Encerra o pool: fecha as ociosas e recusa novas aquisições.

        Conexões em uso não são arrancadas de quem as usa: são fechadas quando
        devolvidas. Uma abertura ou um ping em curso fora da trava percebe o
        encerramento ao terminar, fecha a conexão e levanta ``PoolError``.
        Idempotente.
        """
        with self._cond:
            self.closed = True
            idle = [conn for conn, _ in self._idle]
            self._idle.clear()
            self._cond.notify_all()
        for conn in idle:
            _close_quietly(conn)
