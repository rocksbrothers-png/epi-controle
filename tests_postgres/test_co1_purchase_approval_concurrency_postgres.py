"""CO-1 — governança e concorrência de Compras em PostgreSQL real, via HTTP/JWT.

Cada requisição HTTP é atendida por uma thread do servidor com a sua própria
conexão do pool: transações independentes de verdade. Prova, no dialeto de
produção (``SELECT … FOR UPDATE``):

* duas aprovações simultâneas do mesmo PO → uma 200 e uma 409, uma única linha
  em ``purchase_approvals``;
* aprovação e rejeição simultâneas → um único resultado persistido;
* autoaprovação → 403 com código estável, e a tentativa fica auditada (a
  auditoria é gravada em transação própria, depois do rollback da tentativa);
* duas alterações simultâneas do limite com a mesma versão → uma vence, a outra
  recebe 409, sem sobrescrita silenciosa;
* GET de configuração de Compras não lê outra empresa.
"""
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from test_est_v3_5_postmerge_receipt import server as _server_fixture
from test_est_v3_5_r3_lot_receipt_http import _fresh
from test_stock_lot_evidence_http import call

server = _server_fixture

pytestmark = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL', '').startswith('postgres'),
    reason='Concorrência de aprovação exige PostgreSQL isolado.',
)
STAMP = '2026-11-09T10:00:00+00:00'


@pytest.fixture(autouse=True)
def enforce(monkeypatch):
    monkeypatch.setenv('JWT_ENFORCEMENT_MODE', 'enforce')


def _user(c, company, role, name):
    uid = c.execute('INSERT INTO users(username,password,full_name,role,company_id) VALUES (?,?,?,?,?)',
                    ('co1_' + uuid4().hex, 'x', name, role, company)).lastrowid
    return dict(id=uid, role=role, company_id=company, full_name=name)


def _seed():
    sfx = uuid4().hex
    with _fresh() as c:
        company = c.execute('INSERT INTO companies(name,cnpj,logo_type) VALUES (?,?,?)',
                            ('CO1 ' + sfx, sfx[:14], 'text')).lastrowid
        unit = c.execute('INSERT INTO units(company_id,name,unit_type,city) VALUES (?,?,?,?)',
                         (company, 'U', 'base', 'T')).lastrowid
        epi = c.execute('INSERT INTO epis(company_id,unit_id,name,purchase_code,ca,sector,unit_measure,'
                        'ca_expiry,epi_validity_date,manufacture_date,validity_days) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                        (company, unit, 'Luva', sfx, '123', 'S', 'un', '2030-01-01', '2030-01-01', '2020-01-01', 0)).lastrowid
        users = {
            'creator': _user(c, company, 'general_admin', 'Criador'),
            'a': _user(c, company, 'general_admin', 'Aprovador A'),
            'b': _user(c, company, 'general_admin', 'Aprovador B'),
        }
        c.commit()
    return dict(company=company, unit=unit, epi=epi, users=users)


def _po(s, *, creator='creator', total='30'):
    with _fresh() as c:
        po = c.execute(
            'INSERT INTO purchase_orders (company_id, unit_id, status, po_number, total_value, created_by_user_id, '
            "created_by_name, created_at, updated_at) VALUES (?,?,'pending_approval',?,?,?,?,?,?)",
            (s['company'], s['unit'], 'PO-' + uuid4().hex[:8], total, s['users'][creator]['id'], 'Criador', STAMP, STAMP),
        ).lastrowid
        c.execute(
            'INSERT INTO purchase_order_items (purchase_order_id, company_id, unit_id, epi_id, epi_name, quantity, '
            "unit_price, total_price, status, created_at, updated_at) VALUES (?,?,?,?,?,3,10,30,'open',?,?)",
            (po, s['company'], s['unit'], s['epi'], 'Luva', STAMP, STAMP),
        )
        c.commit()
    return po


def _as(s, who):
    return {'actor': s['users'][who]}


def _approve(server, s, po, who, decision='approved', comment=''):
    return call(server, _as(s, who), f'/api/purchase-orders/{po}/approve',
                {'actor_user_id': s['users'][who]['id'], 'decision': decision, 'comment': comment})


def _parallel(*calls):
    barrier = threading.Barrier(len(calls))

    def run(fn):
        barrier.wait()
        return fn()

    with ThreadPoolExecutor(max_workers=len(calls)) as pool:
        return [f.result(timeout=60) for f in [pool.submit(run, fn) for fn in calls]]


def _scalar(sql, params):
    with _fresh() as c:
        row = c.execute(sql, params).fetchone()
        return row[0] if not isinstance(row, dict) else next(iter(row.values()))


def test_duas_aprovacoes_simultaneas_um_unico_resultado(server):
    s = _seed()
    po = _po(s)
    results = _parallel(lambda: _approve(server, s, po, 'a'), lambda: _approve(server, s, po, 'b'))
    assert sorted(status for status, _ in results) == [200, 409], results
    conflict = next(body for status, body in results if status == 409)
    assert conflict['code'] == 'PURCHASE_ORDER_STATE_CHANGED' and conflict['details']['status'] == 'approved'
    assert _scalar('SELECT COUNT(*) AS n FROM purchase_approvals WHERE purchase_order_id = ?', (po,)) == 1
    assert _scalar("SELECT status FROM purchase_orders WHERE id = ?", (po,)) == 'approved'
    assert _scalar("SELECT COUNT(*) AS n FROM purchase_events WHERE entity_id = ? AND action = 'approval_conflict'", (po,)) == 1


def test_aprovacao_e_rejeicao_simultaneas(server):
    s = _seed()
    po = _po(s)
    results = _parallel(lambda: _approve(server, s, po, 'a'),
                        lambda: _approve(server, s, po, 'b', 'rejected', 'fora do orçamento'))
    assert sorted(status for status, _ in results) == [200, 409], results
    winner = next(body for status, body in results if status == 200)
    assert _scalar('SELECT status FROM purchase_orders WHERE id = ?', (po,)) == winner['status']
    assert _scalar('SELECT COUNT(*) AS n FROM purchase_approvals WHERE purchase_order_id = ?', (po,)) == 1


def test_reenvio_concorrente_da_mesma_aprovacao(server):
    s = _seed()
    po = _po(s)
    results = _parallel(*[(lambda: _approve(server, s, po, 'a')) for _ in range(3)])
    assert sorted(status for status, _ in results) == [200, 409, 409], results
    assert _scalar('SELECT COUNT(*) AS n FROM purchase_approvals WHERE purchase_order_id = ?', (po,)) == 1


def test_autoaprovacao_403_e_tentativa_auditada(server):
    s = _seed()
    po = _po(s, creator='a')
    status, body = _approve(server, s, po, 'a')
    assert status == 403 and body['code'] == 'PURCHASE_SELF_APPROVAL_FORBIDDEN', body
    assert _scalar('SELECT status FROM purchase_orders WHERE id = ?', (po,)) == 'pending_approval'
    assert _scalar('SELECT COUNT(*) AS n FROM purchase_approvals WHERE purchase_order_id = ?', (po,)) == 0
    assert _scalar("SELECT COUNT(*) AS n FROM purchase_events WHERE entity_id = ? AND action = 'approval_denied' "
                   'AND actor_user_id = ?', (po, s['users']['a']['id'])) == 1
    status, body = _approve(server, s, po, 'b')
    assert status == 200 and body['status'] == 'approved'


def test_dois_niveis_com_limite_configurado_e_segregacao(server):
    s = _seed()
    status, body = call(server, _as(s, 'creator'), '/api/purchase-limits',
                        {'actor_user_id': s['users']['creator']['id'], 'value': '30.00', 'expected_version': 0})
    assert status == 200 and body['data']['po_approval_threshold'] == '30.00', body
    po = _po(s, creator='creator', total='30')
    status, body = _approve(server, s, po, 'a')
    assert status == 200 and body['pending_next_level'] is True
    status, body = _approve(server, s, po, 'a')
    assert status == 403 and body['code'] == 'PURCHASE_SECOND_LEVEL_SAME_PERSON', body
    status, body = _approve(server, s, po, 'b')
    assert status == 200 and body['status'] == 'approved'
    assert _scalar('SELECT COUNT(*) AS n FROM purchase_approvals WHERE purchase_order_id = ?', (po,)) == 2


def test_alteracoes_simultaneas_do_limite(server):
    s = _seed()

    def change(value):
        return call(server, _as(s, 'creator'), '/api/purchase-limits',
                    {'actor_user_id': s['users']['creator']['id'], 'value': value, 'expected_version': 0})

    results = _parallel(lambda: change('100.00'), lambda: change('200.00'))
    assert sorted(status for status, _ in results) == [200, 409], results
    winner = next(body for status, body in results if status == 200)['data']['po_approval_threshold']
    status, body = call(server, _as(s, 'creator'), f"/api/purchase-limits?actor_user_id={s['users']['creator']['id']}")
    assert status == 200 and body['data']['po_approval_threshold'] == winner and body['data']['version'] == 1
    assert _scalar("SELECT COUNT(*) AS n FROM purchase_events WHERE company_id = ? AND action = 'purchase_limit_created'",
                   (s['company'],)) == 1


def test_configuracao_de_compras_isolada_por_empresa(server):
    s, other = _seed(), _seed()
    actor = s['users']['a']
    status, _ = call(server, _as(s, 'a'),
                     f"/api/company-purchase-config?actor_user_id={actor['id']}&company_id={other['company']}")
    assert status == 403
    status, _ = call(server, _as(s, 'a'),
                     f"/api/company-purchase-config?actor_user_id={actor['id']}&company_id={s['company']}")
    assert status == 200
