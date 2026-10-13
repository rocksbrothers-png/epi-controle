"""EST-V3.5-R3 — validade física POR LOTE no recebimento (conferência de requisição).

Exercita o fluxo REAL de recebimento (`update_purchase_request_status` →
`_auto_add_received_items_to_stock`) em PostgreSQL isolado, provando os
requisitos do R3: múltiplos lotes com validade/evidência próprias, exceção
individual, evidência obrigatória, vencida → bloqueada, desconhecida → unknown
(fail-closed), integridade (soma dos lotes = qtd), rastreabilidade (lot_code +
evidência por peça), idempotência (reenvio) e concorrência (duas conexões).

Reutiliza os contratos existentes (nenhum segundo mecanismo de estoque):
`record_received_item_physical` (validade física por peça), `classify_physical`
(vigente/próxima/vencida/unknown) e `eligible_piece` (unknown/vencida = fora do
disponível). NUNCA usa catálogo/CA nem inventa data.
"""
import os
import threading
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL', '').startswith('postgres'),
    reason='EST-V3.5-R3 exige PostgreSQL real.',
)

TODAY = date.today()
PAST = (TODAY - timedelta(days=10)).isoformat()
NEAR = (TODAY + timedelta(days=5)).isoformat()      # dentro da janela de alerta (30d) → "expiring"
FUTURE = (TODAY + timedelta(days=365)).isoformat()
FUTURE2 = (TODAY + timedelta(days=400)).isoformat()


@pytest.fixture(scope='module')
def conn():
    from core.bootstrap import init_db
    from core.database import get_connection
    init_db()
    c = get_connection()
    yield c
    c.close()


@pytest.fixture
def seed(conn):
    c = conn
    c.execute('SAVEPOINT r3')
    sfx = uuid4().hex
    company = c.execute('INSERT INTO companies(name,cnpj,logo_type) VALUES (?,?,?)',
                        ('R3 ' + sfx, sfx, 'text')).lastrowid
    c.execute("UPDATE companies SET timezone='UTC' WHERE id=?", (company,))
    unit = c.execute('INSERT INTO units(company_id,name,unit_type,city) VALUES (?,?,?,?)',
                     (company, 'U', 'base', 'T')).lastrowid
    # catálogo EM DIA (FUTURE) de propósito: qualquer bloqueio tem de vir do LOTE físico.
    epi = c.execute('INSERT INTO epis(company_id,unit_id,name,purchase_code,ca,sector,unit_measure,'
                    'ca_expiry,epi_validity_date,manufacture_date,validity_days) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                    (company, unit, 'EPI', sfx, 'CA', 'S', 'un', '2030-01-01', FUTURE, '2020-01-01', 0)).lastrowid
    actor = dict(id=c.execute('INSERT INTO users(username,password,full_name,role,company_id) VALUES (?,?,?,?,?)',
                              ('la_' + sfx, 'x', 'Local', 'admin', company)).lastrowid,
                 full_name='Local', role='admin', company_id=company)

    def make_pr(qty):
        pr = c.execute("INSERT INTO purchase_requests (company_id, unit_id, status, title, "
                       "created_by_user_id, created_by_name, created_at, updated_at) "
                       "VALUES (?,?,'received','Req',?,?,?,?)",
                       (company, unit, actor['id'], 'Local', '2024-01-01', '2024-01-01')).lastrowid
        pri = c.execute("INSERT INTO purchase_request_items (purchase_request_id, company_id, unit_id, epi_id, "
                        "epi_name, quantity_requested, status, created_at, updated_at) "
                        "VALUES (?,?,?,?,?,?, 'received', ?, ?)",
                        (pr, company, unit, epi, 'EPI', int(qty), '2024-01-01', '2024-01-01')).lastrowid
        return pr, pri

    def receive(pr, pri, lots):
        from modules.purchases.service import update_purchase_request_status
        return update_purchase_request_status(
            c, actor, {'id': pr, 'company_id': company, 'status': 'received'},
            'checked', '', '', [{'id': pri, 'received': True, 'lots': lots}], '')

    def pieces():
        from epi_backend.db import row_to_dict
        return [row_to_dict(r) for r in c.execute(
            'SELECT id, lot_code, CAST(physical_expiry_date AS TEXT) AS physical_expiry_date, '
            'expiry_source, expiry_evidence, status '
            'FROM epi_stock_items WHERE company_id=? AND epi_id=? ORDER BY id', (company, epi)).fetchall()]

    yield dict(c=c, company=company, unit=unit, epi=epi, actor=actor,
               make_pr=make_pr, receive=receive, pieces=pieces)
    c.execute('ROLLBACK TO SAVEPOINT r3')
    c.execute('RELEASE SAVEPOINT r3')
    c.rollback()


def _eligible(s):
    from modules.stock.eligibility import eligible_quantity
    return eligible_quantity(s['c'], s['company'], s['unit'], s['epi'])


# 1 — um lote com 50 peças e mesma validade
def test_single_lot_50_pieces_same_validity(seed):
    s = seed
    pr, pri = s['make_pr'](50)
    r = s['receive'](pr, pri, [{'quantity': 50, 'lot_code': 'LOTE-A',
                                'manufacturer_validity_date': FUTURE, 'evidence': 'Etiqueta do lote A'}])
    assert r['stock_entries'] == 50
    rows = s['pieces']()
    assert len(rows) == 50
    assert all(p['lot_code'] == 'LOTE-A' and p['physical_expiry_date'] == FUTURE for p in rows)
    assert all(p['status'] == 'in_stock' and p['expiry_source'] == 'manufacturer_document' for p in rows)
    assert _eligible(s) == 50


# 2 — dois lotes do MESMO EPI com validades diferentes
def test_two_lots_different_validities(seed):
    s = seed
    pr, pri = s['make_pr'](50)
    s['receive'](pr, pri, [
        {'quantity': 30, 'lot_code': 'L1', 'manufacturer_validity_date': FUTURE, 'evidence': 'Etiqueta L1'},
        {'quantity': 20, 'lot_code': 'L2', 'manufacturer_validity_date': FUTURE2, 'evidence': 'Documento L2'},
    ])
    rows = s['pieces']()
    l1 = [p for p in rows if p['lot_code'] == 'L1']
    l2 = [p for p in rows if p['lot_code'] == 'L2']
    assert len(l1) == 30 and all(p['physical_expiry_date'] == FUTURE for p in l1)
    assert len(l2) == 20 and all(p['physical_expiry_date'] == FUTURE2 for p in l2)
    assert _eligible(s) == 50


# 3 — exceção de validade em peça individual (lote de quantidade 1)
def test_individual_exception_as_qty1_lot(seed):
    s = seed
    pr, pri = s['make_pr'](10)
    s['receive'](pr, pri, [
        {'quantity': 9, 'lot_code': 'L1', 'manufacturer_validity_date': FUTURE, 'evidence': 'Etiqueta L1'},
        {'quantity': 1, 'lot_code': 'L1', 'manufacturer_validity_date': NEAR, 'evidence': 'Peça avariada na caixa'},
    ])
    rows = s['pieces']()
    assert sorted(p['physical_expiry_date'] for p in rows) == sorted([FUTURE] * 9 + [NEAR])
    assert len(rows) == 10


# 4 — recebimento SEM evidência (com validade) é recusado; nada entra em estoque
def test_receipt_without_evidence_rejected(seed):
    s = seed
    pr, pri = s['make_pr'](5)
    with pytest.raises(ValueError):
        s['receive'](pr, pri, [{'quantity': 5, 'lot_code': 'L1',
                                'manufacturer_validity_date': FUTURE, 'evidence': '   '}])
    assert s['pieces']() == []


# 5 — recebimento com validade VENCIDA: peça entra bloqueada (blocked_expired), fora do disponível
def test_expired_lot_enters_blocked(seed):
    s = seed
    pr, pri = s['make_pr'](4)
    s['receive'](pr, pri, [{'quantity': 4, 'lot_code': 'L1',
                            'manufacturer_validity_date': PAST, 'evidence': 'Etiqueta vencida'}])
    rows = s['pieces']()
    assert len(rows) == 4 and all(p['status'] == 'blocked_expired' for p in rows)
    assert all(p['physical_expiry_date'] == PAST for p in rows)
    assert _eligible(s) == 0


# 6 — recebimento com validade DESCONHECIDA: peça unknown, fail-closed (inelegível p/ entrega e reserva)
def test_unknown_validity_blocks_until_regularization(seed):
    s = seed
    pr, pri = s['make_pr'](3)
    s['receive'](pr, pri, [{'quantity': 3, 'lot_code': 'L1',
                            'manufacturer_validity_date': '', 'evidence': ''}])
    rows = s['pieces']()
    assert len(rows) == 3
    assert all((p['physical_expiry_date'] in (None, '')) for p in rows)   # sem data física
    assert _eligible(s) == 0                                              # fail-closed
    from modules.stock.service import pending_regularization_count
    assert pending_regularization_count(s['c'], s['company'], s['unit']) == 3


# 7 — integridade: soma das quantidades dos lotes != quantidade recebida → recusa
def test_lot_quantity_mismatch_rejected(seed):
    s = seed
    pr, pri = s['make_pr'](10)
    with pytest.raises(ValueError):
        s['receive'](pr, pri, [
            {'quantity': 3, 'lot_code': 'L1', 'manufacturer_validity_date': FUTURE, 'evidence': 'x'},
            {'quantity': 3, 'lot_code': 'L2', 'manufacturer_validity_date': FUTURE, 'evidence': 'x'},
        ])
    assert s['pieces']() == []


# 8 — rastreabilidade: lot_code + evidência persistidos POR PEÇA
def test_traceability_lot_and_evidence_persisted(seed):
    s = seed
    pr, pri = s['make_pr'](2)
    s['receive'](pr, pri, [{'quantity': 2, 'lot_code': 'LOTE-RASTRO',
                            'manufacturer_validity_date': FUTURE, 'evidence': 'Laudo fabricante nº 42'}])
    rows = s['pieces']()
    assert all(p['lot_code'] == 'LOTE-RASTRO' and p['expiry_evidence'] == 'Laudo fabricante nº 42' for p in rows)


# 9 — idempotência (reenvio): 2ª conferência não duplica peças (status já avançou sob trava)
def test_resend_is_idempotent(seed):
    s = seed
    pr, pri = s['make_pr'](5)
    lots = [{'quantity': 5, 'lot_code': 'L1', 'manufacturer_validity_date': FUTURE, 'evidence': 'Etiqueta'}]
    r1 = s['receive'](pr, pri, lots)
    r2 = s['receive'](pr, pri, lots)   # reenvio
    assert r1['stock_entries'] == 5 and r2['stock_entries'] == 0
    assert len(s['pieces']()) == 5     # sem duplicação


# 10 — FEFO: as peças elegíveis são oferecidas na entrega pela MENOR validade primeiro
def test_fefo_order_on_available_items(seed):
    from modules.stock.service import fetch_available_stock_items
    s = seed
    pr, pri = s['make_pr'](2)
    s['receive'](pr, pri, [
        {'quantity': 1, 'lot_code': 'LONGE', 'manufacturer_validity_date': FUTURE2, 'evidence': 'x'},
        {'quantity': 1, 'lot_code': 'PERTO', 'manufacturer_validity_date': FUTURE, 'evidence': 'x'},
    ])
    avail = fetch_available_stock_items(s['c'], s['company'], s['unit'], s['epi'])
    expiries = [a.get('physical_expiry_date') or a.get('effective_expiry_date') for a in avail]
    non_null = [e for e in expiries if e]
    assert non_null == sorted(non_null), f'FEFO: esperado ordem crescente de validade, veio {expiries}'


# 11 — concorrência real: duas conexões conferem a MESMA requisição → 1 conjunto de peças
def test_concurrent_receipt_no_duplicate():
    from core.bootstrap import init_db
    from core.database import get_connection
    from modules.purchases.service import update_purchase_request_status
    init_db()
    setup = get_connection()
    sfx = uuid4().hex
    company = setup.execute('INSERT INTO companies(name,cnpj,logo_type) VALUES (?,?,?)',
                            ('R3C ' + sfx, sfx, 'text')).lastrowid
    setup.execute("UPDATE companies SET timezone='UTC' WHERE id=?", (company,))
    unit = setup.execute('INSERT INTO units(company_id,name,unit_type,city) VALUES (?,?,?,?)',
                         (company, 'U', 'base', 'T')).lastrowid
    epi = setup.execute('INSERT INTO epis(company_id,unit_id,name,purchase_code,ca,sector,unit_measure,'
                        'ca_expiry,epi_validity_date,manufacture_date,validity_days) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                        (company, unit, 'EPI', sfx, 'CA', 'S', 'un', '2030-01-01', FUTURE, '2020-01-01', 0)).lastrowid
    actor = dict(id=setup.execute('INSERT INTO users(username,password,full_name,role,company_id) VALUES (?,?,?,?,?)',
                                  ('la_' + sfx, 'x', 'Local', 'admin', company)).lastrowid,
                 full_name='Local', role='admin', company_id=company)
    pr = setup.execute("INSERT INTO purchase_requests (company_id, unit_id, status, title, "
                       "created_by_user_id, created_by_name, created_at, updated_at) "
                       "VALUES (?,?,'received','Req',?,?,?,?)",
                       (company, unit, actor['id'], 'Local', '2024-01-01', '2024-01-01')).lastrowid
    pri = setup.execute("INSERT INTO purchase_request_items (purchase_request_id, company_id, unit_id, epi_id, "
                        "epi_name, quantity_requested, status, created_at, updated_at) "
                        "VALUES (?,?,?,?,?,?, 'received', ?, ?)",
                        (pr, company, unit, epi, 'EPI', 6, '2024-01-01', '2024-01-01')).lastrowid
    setup.commit()
    lots = [{'quantity': 6, 'lot_code': 'L1', 'manufacturer_validity_date': FUTURE, 'evidence': 'Etiqueta'}]
    barrier = threading.Barrier(2)
    errors = []

    def worker():
        c = get_connection()
        try:
            barrier.wait(timeout=10)
            update_purchase_request_status(
                c, actor, {'id': pr, 'company_id': company, 'status': 'received'},
                'checked', '', '', [{'id': pri, 'received': True, 'lots': lots}], '')
            c.commit()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)
            try:
                c.rollback()
            except Exception:  # noqa: BLE001
                pass
        finally:
            c.close()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)
    try:
        n = int(setup.execute('SELECT COUNT(*) AS n FROM epi_stock_items WHERE company_id=? AND epi_id=?',
                              (company, epi)).fetchone()['n'])
        assert n == 6, f'esperado 6 peças (uma conferência), veio {n}; erros={errors}'
    finally:
        setup.execute('DELETE FROM epi_stock_items WHERE company_id=?', (company,))
        setup.execute('DELETE FROM stock_movements WHERE company_id=?', (company,))
        setup.execute('DELETE FROM unit_epi_stock WHERE company_id=?', (company,))
        setup.execute('DELETE FROM purchase_request_items WHERE company_id=?', (company,))
        setup.execute('DELETE FROM purchase_requests WHERE company_id=?', (company,))
        setup.execute('DELETE FROM purchase_events WHERE company_id=?', (company,))
        setup.execute('DELETE FROM epis WHERE company_id=?', (company,))
        setup.execute('DELETE FROM users WHERE company_id=?', (company,))
        setup.execute('DELETE FROM units WHERE company_id=?', (company,))
        setup.execute('DELETE FROM companies WHERE id=?', (company,))
        setup.commit()
        setup.close()
