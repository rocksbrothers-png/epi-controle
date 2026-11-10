"""P0 — pool PostgreSQL contra banco real, pela API HTTP/JWT.

Prova, no dialeto de produção:

* exceção no meio da transação: rollback na devolução, nada vaza para a
  requisição seguinte que reutiliza a mesma conexão;
* conexão derrubada pelo servidor (``pg_terminate_backend``): recuperação
  controlada, sem 500 na requisição seguinte;
* saturação: 503 ``DB_POOL_SATURATED`` com ``Retry-After`` e recuperação;
* cliente que desiste no meio da requisição: a conexão volta ao pool;
* concorrência progressiva (5, 10, 20, 30, 50) com usuários de duas empresas
  intercalados: nenhum 5xx, nenhuma resposta de outra empresa, nenhuma
  conexão retida, nenhuma sessão ``idle in transaction``, teto respeitado
  também do lado do banco (``pg_stat_activity``).
"""
import os
import socket
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from uuid import uuid4

import pytest
from test_est_v3_5_r3_lot_receipt_http import _fresh

pytestmark = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL', '').startswith('postgres'),
    reason='P0 do pool exige PostgreSQL isolado.',
)

LEVELS = (5, 10, 20, 30, 50)
ROUNDS = 4


@pytest.fixture(autouse=True)
def enforce(monkeypatch):
    monkeypatch.setenv('JWT_ENFORCEMENT_MODE', 'enforce')


@pytest.fixture(scope='module')
def server():
    """O servidor de PRODUÇÃO (``EpiHTTPServer``, fila 128), não o de teste."""
    from core.bootstrap import init_db
    import app

    init_db()
    app._set_bootstrap_state(ready=True, completed_at=datetime.now(timezone.utc).isoformat(),
                             error_code='', error_kind='', error_message='')
    httpd = app.EpiHTTPServer(('127.0.0.1', 0), app.EpiHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{httpd.server_port}'
    httpd.shutdown()
    httpd.server_close()
    thread.join(timeout=5)


@contextmanager
def custom_pool(**kw):
    """Troca o pool global por um com parâmetros do teste; restaura no fim."""
    import core.database as cdb
    from core.db_pool import BoundedConnectionPool

    previous = cdb._CONNECTION_POOL
    kw.setdefault('minconn', 0)
    kw.setdefault('maxconn', 10)
    kw.setdefault('max_idle', kw['maxconn'])
    kw.setdefault('acquire_timeout', 5)
    kw.setdefault('ping_idle_seconds', 30)
    pool = BoundedConnectionPool(cdb._open_raw_connection, on_event=cdb._pool_event, **kw)
    cdb._CONNECTION_POOL = pool
    try:
        yield pool
    finally:
        cdb._CONNECTION_POOL = previous
        pool.closeall()


@contextmanager
def admin_connection():
    import psycopg2
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    conn.autocommit = True
    try:
        yield conn
    finally:
        conn.close()


def backend_sessions():
    """Sessões deste banco, exceto a do próprio observador, por estado."""
    with admin_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT state, count(*) FROM pg_stat_activity "
                    "WHERE datname = current_database() AND pid <> pg_backend_pid() "
                    "AND backend_type = 'client backend' GROUP BY state")
        return {state or 'null': n for state, n in cur.fetchall()}


def _company(c, label):
    sfx = uuid4().hex
    return c.execute('INSERT INTO companies(name,cnpj,logo_type) VALUES (?,?,?)',
                     (f'{label} {sfx[:6]}', sfx[:14], 'text')).lastrowid


@pytest.fixture(scope='module')
def tenants(server):
    return seed_tenants()


def seed_tenants():
    """Duas empresas, cada uma com unidade, 3 colaboradores e 2 Administradores Gerais."""
    world = {}
    with _fresh() as c:
        for label in ('A', 'B'):
            company = _company(c, f'P0 Pool {label}')
            unit = c.execute('INSERT INTO units(company_id,name,unit_type,city) VALUES (?,?,?,?)',
                             (company, f'Base {label}', 'base', 'T')).lastrowid
            employees = [c.execute(
                'INSERT INTO employees (company_id, unit_id, employee_id_code, name, sector, role_name, '
                'admission_date, schedule_type) VALUES (?,?,?,?,?,?,?,?)',
                (company, unit, f'{label}-{i}-{uuid4().hex[:5]}', f'Pessoa {label}{i}', 'S', 'R', '2020-01-01', '8h'),
            ).lastrowid for i in range(3)]
            users = [c.execute(
                'INSERT INTO users(username,password,full_name,role,company_id,active) VALUES (?,?,?,?,?,1)',
                (f'p0_{label}_{i}_{uuid4().hex[:6]}', 'x', f'Admin {label}{i}', 'general_admin', company),
            ).lastrowid for i in range(2)]
            world[label] = {'company': company, 'unit': unit, 'employees': employees,
                            'users': [{'id': u, 'role': 'general_admin', 'company_id': company} for u in users]}
        c.commit()
    return world


def get(server, actor, path, timeout=20):
    from core.security import create_jwt_token
    request = Request(server + path, headers={'Authorization': 'Bearer ' + create_jwt_token(actor)})
    try:
        response = urlopen(request, timeout=timeout)
    except HTTPError as error:
        response = error
    import json
    with response:
        return response.status, dict(response.headers), json.loads(response.read() or b'{}')


def summary(server, actor, employee_id):
    return get(server, actor, f'/api/employees/{employee_id}/ppe-360/summary')


def _handler_falha():
    raise RuntimeError('falha no handler')


# ── Integridade transacional ─────────────────────────────────────────────────

def test_excecao_no_meio_da_transacao_nao_vaza_para_a_proxima(server, tenants):
    """Escrita sem commit + exceção → a conexão volta limpa; quem a reutiliza
    não enxerga nem confirma a escrita alheia."""
    import core.database as cdb
    from contextlib import closing
    marker = 'P0-LEAK-' + uuid4().hex[:8]
    with custom_pool(maxconn=1, max_idle=1):
        with pytest.raises(RuntimeError):
            with closing(cdb.get_connection()) as conn:
                conn.execute('UPDATE companies SET legal_name = ? WHERE id = ?', (marker, tenants['A']['company']))
                first_pid = conn.execute('SELECT pg_backend_pid() AS pid').fetchone()['pid']
                _handler_falha()
        with closing(cdb.get_connection()) as conn:
            assert conn.execute('SELECT pg_backend_pid() AS pid').fetchone()['pid'] == first_pid  # MESMA conexão
            from psycopg2.extensions import TRANSACTION_STATUS_INTRANS
            # a transação aberta agora é a do SELECT acima — a escrita abandonada não está nela
            assert conn.info.transaction_status == TRANSACTION_STATUS_INTRANS
            row = conn.execute('SELECT legal_name FROM companies WHERE id = ?', (tenants['A']['company'],)).fetchone()
            assert row['legal_name'] != marker
            conn.commit()  # um commit legítimo da requisição seguinte não confirma a escrita abandonada
    with _fresh() as c:
        row = c.execute('SELECT legal_name FROM companies WHERE id = ?', (tenants['A']['company'],)).fetchone()
        assert row['legal_name'] != marker


def test_reutilizacao_apos_erro_sql_entrega_conexao_valida(server, tenants):
    import core.database as cdb
    from contextlib import closing
    with custom_pool(maxconn=1, max_idle=1):
        with pytest.raises(Exception):
            with closing(cdb.get_connection()) as conn:
                conn.execute('SELECT * FROM tabela_que_nao_existe')
        status, _, body = summary(server, tenants['A']['users'][0], tenants['A']['employees'][0])
        assert status == 200, body


def test_conexao_derrubada_pelo_servidor_recupera_sem_500(server, tenants):
    import core.database as cdb
    from contextlib import closing
    actor, emp = tenants['A']['users'][0], tenants['A']['employees'][0]
    for ping in (0, -1):  # 0: ping sempre; -1: sem ping (a 1ª falha descarta, a seguinte funciona)
        with custom_pool(maxconn=2, max_idle=2, ping_idle_seconds=ping) as pool:
            assert summary(server, actor, emp)[0] == 200
            with closing(cdb.get_connection()) as conn:
                pid = conn.execute('SELECT pg_backend_pid() AS pid').fetchone()['pid']
                conn.rollback()
            with admin_connection() as admin, admin.cursor() as cur:
                cur.execute('SELECT pg_terminate_backend(%s)', (pid,))
            time.sleep(0.2)
            statuses = [summary(server, actor, emp)[0] for _ in range(3)]
            if ping == 0:
                assert statuses == [200, 200, 200]
            else:
                assert statuses[1:] == [200, 200] and statuses[0] in (200, 500)
            assert pool.status()['in_use'] == 0
            assert pool.status()['discarded_total'] >= 1


# ── Saturação ────────────────────────────────────────────────────────────────

def test_saturacao_responde_503_com_retry_after_e_se_recupera(server, tenants):
    actor, emp = tenants['B']['users'][0], tenants['B']['employees'][0]
    with custom_pool(maxconn=2, acquire_timeout=0.3) as pool:
        held = [pool.getconn(), pool.getconn()]
        started = time.perf_counter()
        status, headers, body = summary(server, actor, emp)
        elapsed = time.perf_counter() - started
        assert status == 503, body
        assert headers.get('Retry-After') == '1'
        assert body['error']['code'] == 'DB_POOL_SATURATED'
        assert 'company' not in str(body).lower()
        assert 0.25 <= elapsed < 3
        for conn in held:
            pool.putconn(conn)
        assert summary(server, actor, emp)[0] == 200
        assert pool.status()['timeouts_total'] == 1


def test_cliente_que_desiste_nao_prende_conexao(server, tenants):
    from core.security import create_jwt_token
    actor, emp = tenants['A']['users'][1], tenants['A']['employees'][1]
    with custom_pool(maxconn=3) as pool:
        host, port = server.replace('http://', '').split(':')
        for _ in range(10):
            sock = socket.create_connection((host, int(port)))
            sock.sendall((f'GET /api/employees/{emp}/ppe-360/summary HTTP/1.1\r\nHost: x\r\n'
                          f'Authorization: Bearer {create_jwt_token(actor)}\r\n\r\n').encode())
            sock.close()  # desiste antes da resposta
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and (pool.status()['in_use'] or pool.status()['opening']):
            time.sleep(0.05)
        assert pool.status()['in_use'] == 0
        assert summary(server, actor, emp)[0] == 200


# ── Concorrência progressiva e isolamento multi-tenant ───────────────────────

def run_level(server, tenants, concurrency, rounds=ROUNDS):
    """``concurrency`` clientes simultâneos, cada um com ``rounds`` requisições,
    alternando empresa A e B e usuários diferentes. Devolve as medições."""
    import core.database as cdb
    jobs = []
    for i in range(concurrency):
        label = 'A' if i % 2 == 0 else 'B'
        t = tenants[label]
        jobs.append((label, t['users'][i % 2], t['employees'][i % 3], t['company']))
    barrier = threading.Barrier(concurrency)
    sessions_peak = {'n': 0}
    stop = threading.Event()

    def sampler():
        while not stop.is_set():
            sessions_peak['n'] = max(sessions_peak['n'], sum(backend_sessions().values()))
            time.sleep(0.02)

    def client(job):
        label, actor, emp, company = job
        out = []
        barrier.wait()
        for _ in range(rounds):
            started = time.perf_counter()
            try:
                status, _, body = summary(server, actor, emp)
            except OSError as exc:
                out.append(('error:' + type(exc).__name__, time.perf_counter() - started, None))
                continue
            got_company = ((body.get('data') or body).get('employee') or {}).get('company', {}) if status == 200 else {}
            leak = status == 200 and int((got_company or {}).get('id') or 0) != int(company)
            out.append((status, time.perf_counter() - started, leak))
        return out

    watcher = threading.Thread(target=sampler, daemon=True)
    watcher.start()
    try:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            results = [r for chunk in pool.map(client, jobs) for r in chunk]
    finally:
        stop.set()
        watcher.join(timeout=5)
    lat = sorted(r[1] for r in results)

    def pct(p):
        return lat[min(len(lat) - 1, int(p * len(lat)))] * 1000
    counts = {}
    for status, _, _ in results:
        counts[status] = counts.get(status, 0) + 1
    return {
        'concurrency': concurrency, 'requests': len(results), 'statuses': counts,
        'leaks': sum(1 for r in results if r[2]), 'p50': pct(.5), 'p95': pct(.95), 'p99': pct(.99),
        'mean': statistics.mean(lat) * 1000, 'pool': cdb.db_pool_status(), 'db_sessions_peak': sessions_peak['n'],
    }


def test_concorrencia_progressiva_sem_vazamento_nem_5xx(server, tenants):
    maxconn = 10
    rows = []
    with custom_pool(maxconn=maxconn, max_idle=maxconn, acquire_timeout=5) as pool:
        for level in LEVELS:
            result = run_level(server, tenants, level)
            rows.append(result)
            settle = time.monotonic() + 5
            while time.monotonic() < settle and pool.status()['in_use']:
                time.sleep(0.05)
            status = pool.status()
            assert result['leaks'] == 0, result                       # nenhuma resposta de outra empresa
            assert result['statuses'] == {200: result['requests']}, result
            assert status['in_use'] == 0 and status['opening'] == 0, status   # nada retido
            assert status['peak_in_use'] <= maxconn, status
            assert result['db_sessions_peak'] <= maxconn + 1, result  # +1: a sessão do bootstrap/fixture
            assert backend_sessions().get('idle in transaction', 0) == 0
            assert backend_sessions().get('idle in transaction (aborted)', 0) == 0
    print('\nP0 concorrência (summary da Ficha 360°, empresas A/B intercaladas, maxconn=10, timeout=5 s)')
    print(' N   req  p50ms  p95ms  p99ms  5xx  vaz  pico_pool  esperas  espera_max_ms  sessões_banco')
    for r in rows:
        p = r['pool']
        five = sum(v for k, v in r['statuses'].items() if isinstance(k, int) and k >= 500)
        print(f"{r['concurrency']:3d} {r['requests']:5d} {r['p50']:6.0f} {r['p95']:6.0f} {r['p99']:6.0f} "
              f"{five:4d} {r['leaks']:4d} {p['peak_in_use']:9d} {p['waited_total']:8d} {p['max_wait_ms']:13.0f} "
              f"{r['db_sessions_peak']:13d}")
