"""CO-1 — concorrência real na aprovação de PO (SQLite em arquivo, conexões independentes).

Cada "usuário" é uma thread com a PRÓPRIA conexão ao mesmo banco em arquivo —
transações independentes de verdade. A aprovação abre ``BEGIN IMMEDIATE`` e relê
o PO sob a trava; o perdedor de cada corrida espera a trava, vê o estado que o
vencedor persistiu e é recusado com conflito, sem gravar nada.

O equivalente em PostgreSQL (``SELECT … FOR UPDATE``, via HTTP) está em
``tests_postgres/test_co1_purchase_approval_concurrency_postgres.py``.
"""

import sqlite3
import threading
import time

import pytest

from modules.purchases import service as purchase_service
from modules.purchases.approval_limits import set_purchase_limit
from modules.purchases.governance import PurchaseConflictError, PurchaseGovernanceError
from modules.purchases.service import approve_purchase_order, get_purchase_order_by_id
from test_co1_purchase_governance import APPROVER, APPROVER_2, FINANCE_2, GENERAL, LOCAL, LOCAL_AS_APPROVER
from test_co1_purchase_governance import _conn as _memory_conn
from test_co1_purchase_governance import _pending_po


@pytest.fixture()
def db(tmp_path):
    path = str(tmp_path / 'co1.sqlite')
    memory = _memory_conn()
    target = sqlite3.connect(path)
    memory.backup(target)
    target.close()
    memory.close()
    return path


def _open(path):
    conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _setup_po(path, *, threshold=None, creator=GENERAL):
    conn = _open(path)
    if threshold is not None:
        set_purchase_limit(conn, GENERAL, value=threshold, expected_version=0)
        conn.commit()
    po_id = _pending_po(conn, creator=creator)
    conn.commit()
    conn.close()
    return po_id


def _race(path, po_id, attempts):
    """Dispara as tentativas ao mesmo tempo, cada uma na sua conexão/transação.

    ``attempts``: lista de (ator, decisão, comentário). O PO entregue a cada
    thread é lido ANTES da corrida (obsoleto para o perdedor, como na rota).
    """
    barrier = threading.Barrier(len(attempts))
    results = [None] * len(attempts)

    def run(index, actor, decision, comment):
        conn = _open(path)
        stale = get_purchase_order_by_id(conn, po_id)
        barrier.wait()
        try:
            out = approve_purchase_order(conn, actor, stale, decision, comment, [], '', '')
            conn.commit()
            results[index] = ('ok', out['status'])
        except (PurchaseConflictError, PurchaseGovernanceError) as exc:
            conn.rollback()
            results[index] = ('refused', exc.code)
        finally:
            conn.close()

    threads = [threading.Thread(target=run, args=(i, *a)) for i, a in enumerate(attempts)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    return results


def _count(path, sql, params=()):
    conn = _open(path)
    try:
        return conn.execute(sql, params).fetchone()[0]
    finally:
        conn.close()


def test_duas_aprovacoes_simultaneas_produzem_uma_unica_aprovacao(db):
    po_id = _setup_po(db)
    results = _race(db, po_id, [(APPROVER, 'approved', ''), (APPROVER_2, 'approved', '')])
    assert sorted(results) == [('ok', 'approved'), ('refused', 'PURCHASE_ORDER_STATE_CHANGED')]
    assert _count(db, 'SELECT COUNT(*) FROM purchase_approvals WHERE purchase_order_id = ?', (po_id,)) == 1
    assert _count(db, "SELECT COUNT(*) FROM purchase_events WHERE entity_id = ? AND action = 'approved'", (po_id,)) == 1


def test_aprovacao_e_rejeicao_simultaneas_tem_um_unico_resultado(db):
    po_id = _setup_po(db)
    results = _race(db, po_id, [(APPROVER, 'approved', ''), (APPROVER_2, 'rejected', 'acima do orçamento')])
    oks = [r for r in results if r[0] == 'ok']
    assert len(oks) == 1 and ('refused', 'PURCHASE_ORDER_STATE_CHANGED') in results
    final = _count(db, 'SELECT status FROM purchase_orders WHERE id = ?', (po_id,))
    assert final == oks[0][1]
    assert _count(db, 'SELECT COUNT(*) FROM purchase_approvals WHERE purchase_order_id = ?', (po_id,)) == 1


def test_mesmo_aprovador_duas_vezes_no_mesmo_nivel_nao_duplica(db):
    po_id = _setup_po(db, threshold='10.00')  # 2 níveis
    results = _race(db, po_id, [(APPROVER, 'approved', ''), (APPROVER, 'approved', '')])
    assert sorted(results) == [('ok', 'pending_approval'), ('refused', 'PURCHASE_SECOND_LEVEL_SAME_PERSON')]
    assert _count(db, 'SELECT COUNT(*) FROM purchase_approvals WHERE purchase_order_id = ?', (po_id,)) == 1


def test_mesma_pessoa_com_duas_contas_em_paralelo_nao_faz_os_dois_niveis(db):
    po_id = _setup_po(db, threshold='10.00')
    results = _race(db, po_id, [(LOCAL_AS_APPROVER, 'approved', ''), (LOCAL, 'approved', '')])
    assert ('refused', 'PURCHASE_SECOND_LEVEL_SAME_PERSON') in results
    assert _count(db, 'SELECT status FROM purchase_orders WHERE id = ?', (po_id,)) == 'pending_approval'
    assert _count(db, 'SELECT COUNT(*) FROM purchase_approvals WHERE purchase_order_id = ?', (po_id,)) == 1


def test_dois_aprovadores_independentes_em_paralelo_completam_os_dois_niveis(db):
    po_id = _setup_po(db, threshold='10.00')
    results = _race(db, po_id, [(APPROVER, 'approved', ''), (FINANCE_2, 'approved', '')])
    assert sorted(r[1] for r in results) == ['approved', 'pending_approval']
    assert _count(db, 'SELECT status FROM purchase_orders WHERE id = ?', (po_id,)) == 'approved'
    assert _count(db, 'SELECT COUNT(*) FROM purchase_approvals WHERE purchase_order_id = ?', (po_id,)) == 2


def test_reenvio_da_mesma_aprovacao_nao_duplica_registros(db):
    po_id = _setup_po(db)
    results = _race(db, po_id, [(APPROVER, 'approved', ''), (APPROVER, 'approved', ''), (APPROVER, 'approved', '')])
    assert sorted(results) == [('ok', 'approved')] + [('refused', 'PURCHASE_ORDER_STATE_CHANGED')] * 2
    assert _count(db, 'SELECT COUNT(*) FROM purchase_approvals WHERE purchase_order_id = ?', (po_id,)) == 1


def test_alteracao_de_limite_durante_a_aprovacao_e_serializada(db):
    """A aprovação espera a alteração de limite em curso e decide com o valor confirmado."""
    po_id = _setup_po(db)  # total 30.00, sem limite
    locked = threading.Event()
    timeline = {}

    def change_limit():
        conn = _open(db)
        set_purchase_limit(conn, GENERAL, value='30.00', expected_version=0)  # trava a configuração
        locked.set()
        time.sleep(0.6)
        timeline['limit_committed'] = time.monotonic()
        conn.commit()
        conn.close()

    def approve():
        locked.wait(10)
        conn = _open(db)
        out = approve_purchase_order(conn, APPROVER, get_purchase_order_by_id(conn, po_id), 'approved', '', [], '', '')
        timeline['approval_done'] = time.monotonic()
        conn.commit()
        conn.close()
        timeline['result'] = out

    a, b = threading.Thread(target=change_limit), threading.Thread(target=approve)
    a.start(); b.start(); a.join(30); b.join(30)
    assert timeline['approval_done'] >= timeline['limit_committed']
    assert timeline['result']['status'] == 'pending_approval' and timeline['result']['pending_next_level'] is True


def test_falha_no_meio_da_aprovacao_desfaz_tudo(db, monkeypatch):
    po_id = _setup_po(db)
    conn = _open(db)
    calls = {'n': 0}
    original = purchase_service._record_purchase_event

    def explode(*args, **kwargs):
        calls['n'] += 1
        raise RuntimeError('falha simulada após gravar status e aprovação')

    monkeypatch.setattr(purchase_service, '_record_purchase_event', explode)
    with pytest.raises(RuntimeError):
        approve_purchase_order(conn, APPROVER, get_purchase_order_by_id(conn, po_id), 'approved', '', [], '', '')
    conn.rollback()
    conn.close()
    monkeypatch.setattr(purchase_service, '_record_purchase_event', original)
    assert calls['n'] == 1
    assert _count(db, 'SELECT status FROM purchase_orders WHERE id = ?', (po_id,)) == 'pending_approval'
    assert _count(db, 'SELECT COUNT(*) FROM purchase_approvals WHERE purchase_order_id = ?', (po_id,)) == 0
    assert _count(db, "SELECT COUNT(*) FROM purchase_order_items WHERE purchase_order_id = ? AND status = 'approved'", (po_id,)) == 0
    # Depois do rollback, a aprovação legítima continua possível.
    conn = _open(db)
    assert approve_purchase_order(conn, APPROVER, get_purchase_order_by_id(conn, po_id), 'approved', '', [], '', '')['status'] == 'approved'
    conn.commit()
    conn.close()


def test_duas_alteracoes_de_limite_simultaneas_uma_vence_e_a_outra_recebe_conflito(db):
    barrier = threading.Barrier(2)
    results = []

    def change(value):
        conn = _open(db)
        barrier.wait()
        try:
            set_purchase_limit(conn, GENERAL, value=value, expected_version=0)
            conn.commit()
            results.append(('ok', value))
        except PurchaseConflictError as exc:
            conn.rollback()
            results.append(('conflict', exc.code))
        finally:
            conn.close()

    threads = [threading.Thread(target=change, args=(v,)) for v in ('100.00', '200.00')]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    assert sorted(r[0] for r in results) == ['conflict', 'ok']
    assert ('conflict', 'PURCHASE_LIMIT_VERSION_CONFLICT') in results
    winner = next(r[1] for r in results if r[0] == 'ok')
    assert _count(db, "SELECT COUNT(*) FROM purchase_events WHERE action = 'purchase_limit_created'") == 1
    from modules.purchases.approval_limits import get_purchase_limits
    conn = _open(db)
    assert get_purchase_limits(conn, 1)['po_approval_threshold'] == winner
    conn.close()
