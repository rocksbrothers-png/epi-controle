"""EST-V3.5-R3 — recebimento por lote via API HTTP real (conferência).

Exercita o handler REAL ``handle_post_purchase_request_status`` (POST
``/api/purchase-requests/{id}/status``) com ``JWT_ENFORCEMENT_MODE=enforce``,
provando que o payload de lotes trafega da borda HTTP até a persistência por
peça e que RBAC + isolamento por empresa fecham o recebimento (fail-closed).

Reutiliza o MESMO backend de lotes do R3-B (nenhum segundo mecanismo de
estoque): o sink HTTP em memória substitui apenas o transporte. A verificação
confere lot_code, validade física, evidência, classificação (vigente/vencida/
desconhecida) e elegibilidade por peça — nunca catálogo/CA, nunca data inventada.
"""
import io
import json
import os
from contextlib import contextmanager
from datetime import date, timedelta
from urllib.parse import urlparse
from uuid import uuid4

import pytest

from core.security import create_jwt_token
from epi_backend.db import row_to_dict
from modules.purchases.routes import handle_post_purchase_request_status

pytestmark = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL', '').startswith('postgres'),
    reason='EST-V3.5-R3 HTTP exige PostgreSQL real.',
)

TODAY = date.today()
PAST = (TODAY - timedelta(days=10)).isoformat()
NEAR = (TODAY + timedelta(days=5)).isoformat()
FUTURE = (TODAY + timedelta(days=365)).isoformat()
FUTURE2 = (TODAY + timedelta(days=400)).isoformat()


class ResponseSink:
    """Transporte HTTP em memória — não mocka serviço, RBAC nem persistência."""

    def __init__(self, path, actor, command='POST'):
        self.path, self.command, self.client_address = path, command, ('127.0.0.1', 0)
        self.headers = {'Authorization': 'Bearer ' + create_jwt_token(actor)}
        self.wfile = io.BytesIO()
        self.status = None

    def send_response(self, status):
        self.status = status

    def send_header(self, *args):
        pass

    def end_headers(self):
        pass

    @property
    def body(self):
        return json.loads(self.wfile.getvalue()) if self.wfile.getvalue() else None


class _Match:
    def __init__(self, pr_id):
        self._pr_id = pr_id

    def group(self, _index):
        return str(self._pr_id)


@pytest.fixture(scope='module', autouse=True)
def _init_schema():
    from core.bootstrap import init_db
    init_db()


@pytest.fixture(autouse=True)
def _enforce_jwt(monkeypatch):
    monkeypatch.setenv('JWT_ENFORCEMENT_MODE', 'enforce')
    yield
    # Isola os testes mesmo quando um handler levanta no meio da transação: o
    # pool de core.database NÃO faz rollback no putconn, então zeramos o pool
    # ao fim de cada teste (connections recriadas sob demanda, sem herdar
    # transação abortada).
    import core.database as _cdb
    pool = getattr(_cdb, '_CONNECTION_POOL', None)
    if pool is not None:
        try:
            pool.closeall()
        except Exception:
            # Pool já encerrado ou sem conexões abertas — descarte best-effort.
            pass
        _cdb._CONNECTION_POOL = None


def _conn():
    import core.database as _cdb
    return _cdb.get_connection()


@contextmanager
def _fresh():
    """Conexão limpa: rollback antes de usar (descarta transação abortada que
    um handler com exceção possa ter deixado na conexão do pool)."""
    c = _conn()
    try:
        c.rollback()
        yield c
    finally:
        c.close()


def _seed(*, role='general_admin', qty=1):
    """Empresa/unidade/EPI/ator(role)/PR(received)/pri(received), COMITADO — o
    handler abre a própria conexão do pool e só enxerga dados comitados."""
    sfx = uuid4().hex
    with _fresh() as c:
        company = c.execute('INSERT INTO companies(name,cnpj,logo_type) VALUES (?,?,?)',
                            ('R3H ' + sfx, sfx, 'text')).lastrowid
        c.execute("UPDATE companies SET timezone='UTC' WHERE id=?", (company,))
        unit = c.execute('INSERT INTO units(company_id,name,unit_type,city) VALUES (?,?,?,?)',
                         (company, 'U', 'base', 'T')).lastrowid
        # catálogo EM DIA (FUTURE) de propósito: qualquer bloqueio vem do LOTE físico.
        epi = c.execute('INSERT INTO epis(company_id,unit_id,name,purchase_code,ca,sector,unit_measure,'
                        'ca_expiry,epi_validity_date,manufacture_date,validity_days) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                        (company, unit, 'EPI', sfx, 'CA', 'S', 'un', '2030-01-01', FUTURE, '2020-01-01', 0)).lastrowid
        actor_id = c.execute('INSERT INTO users(username,password,full_name,role,company_id) VALUES (?,?,?,?,?)',
                             ('u_' + sfx, 'x', 'Ator', role, company)).lastrowid
        pr = c.execute("INSERT INTO purchase_requests (company_id, unit_id, status, title, "
                       "created_by_user_id, created_by_name, created_at, updated_at) "
                       "VALUES (?,?,'received','Req',?,?,?,?)",
                       (company, unit, actor_id, 'Ator', '2024-01-01', '2024-01-01')).lastrowid
        pri = c.execute("INSERT INTO purchase_request_items (purchase_request_id, company_id, unit_id, epi_id, "
                        "epi_name, quantity_requested, status, created_at, updated_at) "
                        "VALUES (?,?,?,?,?,?, 'received', ?, ?)",
                        (pr, company, unit, epi, 'EPI', int(qty), '2024-01-01', '2024-01-01')).lastrowid
        c.commit()
    actor = dict(id=actor_id, role=role, company_id=company, full_name='Ator')
    return dict(company=company, unit=unit, epi=epi, actor=actor, pr=pr, pri=pri)


def _post(actor, pr_id, received_items, comment=''):
    handler = ResponseSink(f'/api/purchase-requests/{pr_id}/status', actor, 'POST')
    payload = {'actor_user_id': actor['id'], 'status': 'checked',
               'received_items': received_items, 'comment': comment}
    handle_post_purchase_request_status(handler, urlparse(handler.path), payload, _Match(pr_id))
    return handler


def _pieces(company, epi):
    with _fresh() as c:
        return [row_to_dict(r) for r in c.execute(
            'SELECT id, lot_code, CAST(physical_expiry_date AS TEXT) AS physical_expiry_date, '
            'expiry_source, expiry_evidence, status FROM epi_stock_items '
            'WHERE company_id=? AND epi_id=? ORDER BY id', (company, epi)).fetchall()]


def _eligible(company, unit, epi):
    from modules.stock.eligibility import eligible_quantity
    with _fresh() as c:
        return eligible_quantity(c, company, unit, epi)


# 1 — lote único via HTTP: N peças com a mesma validade comprovada entram em estoque
def test_http_single_lot_persists_per_piece():
    s = _seed(role='general_admin', qty=5)
    h = _post(s['actor'], s['pr'], [{'id': s['pri'], 'received': True,
              'lots': [{'quantity': 5, 'lot_code': 'LOTE-A',
                        'manufacturer_validity_date': FUTURE, 'evidence': 'Etiqueta do lote A'}]}])
    assert h.status == 200
    assert h.body.get('stock_entries') == 5
    rows = _pieces(s['company'], s['epi'])
    assert len(rows) == 5
    assert all(p['lot_code'] == 'LOTE-A' and p['physical_expiry_date'] == FUTURE for p in rows)
    assert all(p['status'] == 'in_stock' and p['expiry_source'] == 'manufacturer_document' for p in rows)
    assert _eligible(s['company'], s['unit'], s['epi']) == 5


# 2 — dois lotes do mesmo EPI com validades diferentes, via HTTP
def test_http_two_lots_different_validities():
    s = _seed(qty=50)
    _post(s['actor'], s['pr'], [{'id': s['pri'], 'received': True, 'lots': [
        {'quantity': 30, 'lot_code': 'L1', 'manufacturer_validity_date': FUTURE, 'evidence': 'Etiqueta L1'},
        {'quantity': 20, 'lot_code': 'L2', 'manufacturer_validity_date': FUTURE2, 'evidence': 'Documento L2'},
    ]}])
    rows = _pieces(s['company'], s['epi'])
    l1 = [p for p in rows if p['lot_code'] == 'L1']
    l2 = [p for p in rows if p['lot_code'] == 'L2']
    assert len(l1) == 30 and all(p['physical_expiry_date'] == FUTURE for p in l1)
    assert len(l2) == 20 and all(p['physical_expiry_date'] == FUTURE2 for p in l2)


# 3 — exceção individual via HTTP = lote de quantidade 1 com validade própria
def test_http_individual_exception_qty1():
    s = _seed(qty=10)
    _post(s['actor'], s['pr'], [{'id': s['pri'], 'received': True, 'lots': [
        {'quantity': 9, 'lot_code': 'L1', 'manufacturer_validity_date': FUTURE, 'evidence': 'Etiqueta L1'},
        {'quantity': 1, 'lot_code': 'L1', 'manufacturer_validity_date': NEAR, 'evidence': 'Peça avariada'},
    ]}])
    rows = _pieces(s['company'], s['epi'])
    assert sorted(p['physical_expiry_date'] for p in rows) == sorted([FUTURE] * 9 + [NEAR])


# 4 — validade sem evidência via HTTP é recusada; nada entra em estoque (fail-closed)
def test_http_validity_without_evidence_rejected():
    s = _seed(qty=5)
    h = _post(s['actor'], s['pr'], [{'id': s['pri'], 'received': True,
          'lots': [{'quantity': 5, 'manufacturer_validity_date': FUTURE, 'evidence': '   '}]}])
    assert h.status == 400 and h.body['validation']['code'] == 'INVALID_RECEIPT_LOTS'
    assert _pieces(s['company'], s['epi']) == []


# 5 — validade desconhecida via HTTP: peça entra unknown/bloqueada (R3 #9)
def test_http_unknown_validity_enters_blocked():
    s = _seed(qty=3)
    _post(s['actor'], s['pr'], [{'id': s['pri'], 'received': True,
          'lots': [{'quantity': 3, 'manufacturer_validity_date': '', 'evidence': ''}]}])
    rows = _pieces(s['company'], s['epi'])
    assert len(rows) == 3
    assert all((p['physical_expiry_date'] in (None, '')) for p in rows)
    assert _eligible(s['company'], s['unit'], s['epi']) == 0


# 6 — validade vencida via HTTP: peça entra bloqueada (blocked_expired), fora do disponível
def test_http_expired_enters_blocked():
    s = _seed(qty=4)
    _post(s['actor'], s['pr'], [{'id': s['pri'], 'received': True,
          'lots': [{'quantity': 4, 'manufacturer_validity_date': PAST, 'evidence': 'Etiqueta vencida'}]}])
    rows = _pieces(s['company'], s['epi'])
    assert len(rows) == 4 and all(p['status'] == 'blocked_expired' for p in rows)
    assert _eligible(s['company'], s['unit'], s['epi']) == 0


# 7 — integridade via HTTP: soma dos lotes != quantidade recebida → recusa, nada entra
def test_http_lot_sum_mismatch_rejected():
    s = _seed(qty=10)
    h = _post(s['actor'], s['pr'], [{'id': s['pri'], 'received': True, 'lots': [
        {'quantity': 3, 'lot_code': 'L1', 'manufacturer_validity_date': FUTURE, 'evidence': 'x'},
        {'quantity': 3, 'lot_code': 'L2', 'manufacturer_validity_date': FUTURE, 'evidence': 'x'},
    ]}])
    assert h.status == 400 and h.body['validation']['code'] == 'INVALID_RECEIPT_LOTS'
    assert _pieces(s['company'], s['epi']) == []


# 8 — RBAC: papel sem purchase_requests:update é NEGADO na borda (fail-closed)
def test_http_rbac_denies_role_without_update():
    s = _seed(role='employee', qty=2)
    with pytest.raises(PermissionError):
        _post(s['actor'], s['pr'], [{'id': s['pri'], 'received': True,
              'lots': [{'quantity': 2, 'manufacturer_validity_date': FUTURE, 'evidence': 'etq'}]}])
    assert _pieces(s['company'], s['epi']) == []


# 9 — isolamento por empresa: ator da empresa A não confere PR da empresa B
def test_http_company_isolation_fail_closed():
    a = _seed(role='general_admin', qty=2)
    b = _seed(role='general_admin', qty=2)
    with pytest.raises((PermissionError, ValueError)):
        _post(a['actor'], b['pr'], [{'id': b['pri'], 'received': True,
              'lots': [{'quantity': 2, 'manufacturer_validity_date': FUTURE, 'evidence': 'etq'}]}])
    assert _pieces(b['company'], b['epi']) == []
