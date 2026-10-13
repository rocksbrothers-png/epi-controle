"""EST-V3.5-R2 (F4) — regularização da validade física: contrato em PostgreSQL REAL.

Exercita o schema real (CHECKs/FKs/triggers EST-V2) provando a regra de segurança
(fail-closed, sem catálogo), a classificação pelo backend, a trilha IMUTÁVEL em
``epi_stock_events`` (antes/depois, append-only), RBAC/isolamento, estados
incompatíveis, idempotência e concorrência. Roda só em PostgreSQL isolado.
"""
import os
import threading
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL', '').startswith('postgres'),
    reason='EST-V3.5-R2 exige PostgreSQL real.',
)

TODAY = date.today()
PAST = (TODAY - timedelta(days=10)).isoformat()
FUTURE = (TODAY + timedelta(days=365)).isoformat()
NOW = datetime.now(timezone.utc).isoformat()


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
    c.execute('SAVEPOINT r2')
    sfx = uuid4().hex
    company = c.execute('INSERT INTO companies(name,cnpj,logo_type) VALUES (?,?,?)',
                        ('R2 ' + sfx, sfx, 'text')).lastrowid
    unit = c.execute('INSERT INTO units(company_id,name,unit_type,city) VALUES (?,?,?,?)',
                     (company, 'U', 'base', 'T')).lastrowid
    # catálogo propositalmente EM DIA (FUTURE): qualquer bloqueio tem de vir do lote físico.
    epi = c.execute('INSERT INTO epis(company_id,unit_id,name,purchase_code,ca,sector,unit_measure,'
                    'ca_expiry,epi_validity_date,manufacture_date,validity_days) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                    (company, unit, 'EPI', sfx, 'CA', 'S', 'un', '2030-01-01', FUTURE, '2020-01-01', 0)).lastrowid
    actor = c.execute('INSERT INTO users(username,password,full_name,role,company_id) VALUES (?,?,?,?,?)',
                      ('ga_' + sfx, 'x', 'Geral', 'general_admin', company)).lastrowid

    def piece(status=None):
        from modules.stock.service import (create_stock_item, next_company_qr_sequence,
                                           get_unit_stock, upsert_unit_stock)
        seqv = next_company_qr_sequence(c, company)
        iid = create_stock_item(c, company, unit, epi, 'N/A', 'M', 'N/A', seqv, 'QR-' + uuid4().hex,
                                None, '', '', 'unit', '', '', actor, NOW)  # validade DESCONHECIDA
        if status:
            c.execute('UPDATE epi_stock_items SET status=? WHERE id=?', (status, iid))
        cur = get_unit_stock(c, company, unit, epi)   # reflete o agregado físico (o recebimento real faz isto)
        upsert_unit_stock(c, company, unit, epi, (int(cur['quantity']) if cur else 0) + 1)
        return iid

    def item(iid):
        from epi_backend.db import row_to_dict
        return row_to_dict(c.execute('SELECT * FROM epi_stock_items WHERE id=?', (iid,)).fetchone())

    yield dict(c=c, company=company, unit=unit, epi=epi, actor=actor, piece=piece, item=item)
    c.execute('ROLLBACK TO SAVEPOINT r2')
    c.execute('RELEASE SAVEPOINT r2')
    c.rollback()


def _events(c, iid):
    return int(c.execute("SELECT COUNT(*) AS n FROM epi_stock_events WHERE stock_item_id=? "
                         "AND event_type='expiry_regularization'", (iid,)).fetchone()['n'])


def _reg(s, iid, expiry, evidence='Laudo do fabricante nº 123', justification='Captura de validade do lote'):
    from modules.stock.service import regularize_item_physical_validity
    return regularize_item_physical_validity(s['c'], s['item'](iid), expiry, evidence, justification,
                                             s['actor'], 'Geral', 'general_admin', NOW)


# 1 — unknown → válida: fica operacional, elegível, com evento registrado
def test_unknown_to_valid_becomes_eligible(seed):
    from modules.stock.service import fetch_available_stock_items
    from modules.stock.eligibility import eligible_quantity
    s = seed
    iid = s['piece']()
    assert eligible_quantity(s['c'], s['company'], s['unit'], s['epi']) == 0   # desconhecida = inelegível
    r = _reg(s, iid, FUTURE)
    assert r['status'] == 'in_stock' and r['eligible'] is True and r['validity_status'] == 'valid'
    assert s['item'](iid)['expiry_source'] == 'regularization'
    assert eligible_quantity(s['c'], s['company'], s['unit'], s['epi']) == 1
    assert iid in [it['id'] for it in fetch_available_stock_items(s['c'], s['company'], s['unit'], s['epi'])]
    assert _events(s['c'], iid) == 1


# 2 — unknown → vencida: vira blocked_expired, indisponível
def test_unknown_to_expired_blocks(seed):
    from modules.stock.service import fetch_available_stock_items
    s = seed
    iid = s['piece']()
    r = _reg(s, iid, PAST)
    assert r['status'] == 'blocked_expired' and r['eligible'] is False and r['blocked_expired'] is True
    assert s['item'](iid)['status'] == 'blocked_expired'
    assert iid not in [it['id'] for it in fetch_available_stock_items(s['c'], s['company'], s['unit'], s['epi'])]
    assert _events(s['c'], iid) == 1


# 3 — sem evidência: recusado, sem escrita e sem evento
def test_no_evidence_rejected(seed):
    s = seed
    iid = s['piece']()
    with pytest.raises(ValueError):
        _reg(s, iid, FUTURE, evidence='   ')
    assert s['item'](iid)['expiry_source'] == 'unknown'
    assert _events(s['c'], iid) == 0


# 4 — data inválida/inconsistente: recusada
def test_invalid_or_inconsistent_date_rejected(seed):
    s = seed
    iid = s['piece']()
    with pytest.raises(ValueError):
        _reg(s, iid, 'not-a-date')
    with pytest.raises(ValueError):
        _reg(s, iid, '2026-13-40')
    assert _events(s['c'], iid) == 0


# 5 — RBAC: permissão própria só nos perfis operacionais; negada aos demais
def test_rbac_permission_matrix_and_denial(seed):
    from core.permissions import PERMISSIONS, PERM_STOCK_REGULARIZE_VALIDITY as P
    assert P in PERMISSIONS['general_admin'] and P in PERMISSIONS['admin']
    assert P not in PERMISSIONS['buyer'] and P not in PERMISSIONS['approver']
    assert P not in PERMISSIONS['master_admin']   # Master não executa operação
    from core.repository import authorize_action
    s = seed
    buyer = s['c'].execute('INSERT INTO users(username,password,full_name,role,company_id) VALUES (?,?,?,?,?)',
                           ('buyer_' + uuid4().hex, 'x', 'Comprador', 'buyer', s['company'])).lastrowid
    with pytest.raises(Exception):
        authorize_action(s['c'], buyer, P, s['company'])
    assert authorize_action(s['c'], s['actor'], P, s['company'])['role'] == 'general_admin'


# 6 — isolamento: item de outra empresa/unidade/EPI é recusado
def test_cross_tenant_rejected(seed):
    from modules.stock.service import regularize_item_physical_validity
    s = seed
    iid = s['piece']()
    forged = dict(s['item'](iid))
    forged['company_id'] = int(s['company']) + 100000   # empresa que não é a do item
    with pytest.raises(ValueError):
        regularize_item_physical_validity(s['c'], forged, FUTURE, 'Laudo', 'x',
                                          s['actor'], 'Geral', 'general_admin', NOW)
    assert _events(s['c'], iid) == 0


# 7 — estados incompatíveis (entregue/descartado) são recusados
@pytest.mark.parametrize('status', ['delivered', 'discarded', 'reserved'])
def test_incompatible_states_rejected(seed, status):
    s = seed
    iid = s['piece'](status=status)
    with pytest.raises(ValueError):
        _reg(s, iid, FUTURE)
    assert _events(s['c'], iid) == 0


# 9 — idempotência: reenvio do MESMO valor não duplica evento
def test_idempotent_same_value(seed):
    s = seed
    iid = s['piece']()
    r1 = _reg(s, iid, FUTURE)
    assert r1['idempotent'] is False
    r2 = _reg(s, iid, FUTURE)
    assert r2['idempotent'] is True
    assert _events(s['c'], iid) == 1   # sem duplicação


# 10 — histórico preservado (append-only) e IMUTÁVEL
def test_history_append_only_and_immutable(seed):
    s = seed
    iid = s['piece']()
    _reg(s, iid, FUTURE)                              # evento 1 (válida)
    _reg(s, iid, PAST)                                # evento 2 (vencida) — valor diferente
    assert _events(s['c'], iid) == 2                  # ambos preservados
    row = s['c'].execute("SELECT id FROM epi_stock_events WHERE stock_item_id=? "
                         "AND event_type='expiry_regularization' ORDER BY id LIMIT 1", (iid,)).fetchone()
    eid = int(row['id'])
    s['c'].execute('SAVEPOINT imm')
    with pytest.raises(Exception):                    # UPDATE barrado pelo trigger de imutabilidade
        s['c'].execute("UPDATE epi_stock_events SET justification='alterado' WHERE id=?", (eid,))
    s['c'].execute('ROLLBACK TO SAVEPOINT imm')
    s['c'].execute('SAVEPOINT imm2')
    with pytest.raises(Exception):                    # DELETE também barrado
        s['c'].execute('DELETE FROM epi_stock_events WHERE id=?', (eid,))
    s['c'].execute('ROLLBACK TO SAVEPOINT imm2')
    assert _events(s['c'], iid) == 2


# 11 — reserva/disponibilidade refletem a regularização; pendentes de regularização contam
def test_balance_and_pending_after_regularization(seed):
    from modules.stock.reservations import unit_balance
    from modules.stock.service import pending_regularization_count
    s = seed
    a, b = s['piece'](), s['piece']()                 # 2 desconhecidas
    assert pending_regularization_count(s['c'], s['company'], s['unit']) == 2
    assert unit_balance(s['c'], s['company'], s['unit'], s['epi'])['eligible'] == 0
    _reg(s, a, FUTURE)                                # a → válida
    _reg(s, b, PAST)                                  # b → vencida (blocked_expired)
    assert unit_balance(s['c'], s['company'], s['unit'], s['epi'])['eligible'] == 1   # só a
    assert pending_regularization_count(s['c'], s['company'], s['unit']) == 0         # nenhuma desconhecida


# 8 — concorrência real: duas conexões regularizam a MESMA peça → 1 evento, estado consistente
def test_concurrent_regularization_no_duplicate():
    from core.bootstrap import init_db
    from core.database import get_connection
    from epi_backend.db import row_to_dict
    from modules.stock.service import regularize_item_physical_validity, create_stock_item, next_company_qr_sequence
    init_db()
    setup = get_connection()
    sfx = uuid4().hex
    company = setup.execute('INSERT INTO companies(name,cnpj,logo_type) VALUES (?,?,?)',
                            ('R2C ' + sfx, sfx, 'text')).lastrowid
    unit = setup.execute('INSERT INTO units(company_id,name,unit_type,city) VALUES (?,?,?,?)',
                         (company, 'U', 'base', 'T')).lastrowid
    epi = setup.execute('INSERT INTO epis(company_id,unit_id,name,purchase_code,ca,sector,unit_measure,'
                        'ca_expiry,epi_validity_date,manufacture_date,validity_days) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                        (company, unit, 'EPI', sfx, 'CA', 'S', 'un', '2030-01-01', FUTURE, '2020-01-01', 0)).lastrowid
    actor = setup.execute('INSERT INTO users(username,password,full_name,role,company_id) VALUES (?,?,?,?,?)',
                         ('ga_' + sfx, 'x', 'Geral', 'general_admin', company)).lastrowid
    seqv = next_company_qr_sequence(setup, company)
    iid = create_stock_item(setup, company, unit, epi, 'N/A', 'M', 'N/A', seqv, 'QR-' + uuid4().hex,
                            None, '', '', 'unit', '', '', actor, NOW)
    setup.commit()   # visível às demais conexões
    item = row_to_dict(setup.execute('SELECT * FROM epi_stock_items WHERE id=?', (iid,)).fetchone())

    barrier = threading.Barrier(2)
    errors = []

    def worker():
        c = get_connection()
        try:
            barrier.wait(timeout=10)
            regularize_item_physical_validity(c, item, FUTURE, 'Laudo', 'concorrência', actor, 'Geral', 'general_admin', NOW)
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
        n = int(setup.execute("SELECT COUNT(*) AS n FROM epi_stock_events WHERE stock_item_id=? "
                              "AND event_type='expiry_regularization'", (iid,)).fetchone()['n'])
        final = row_to_dict(setup.execute('SELECT status, expiry_source FROM epi_stock_items WHERE id=?', (iid,)).fetchone())
        assert n == 1, f'esperado 1 evento (lock + idempotência), veio {n}; erros={errors}'
        assert final['status'] == 'in_stock' and final['expiry_source'] == 'regularization'
    finally:
        # epi_stock_events é imutável por trigger (append-only); para limpar o banco
        # descartável do teste, o trigger é desabilitado SÓ durante o teardown.
        try:
            setup.execute('ALTER TABLE epi_stock_events DISABLE TRIGGER stock_events_immutable')
        except Exception:  # noqa: BLE001
            pass
        setup.execute('DELETE FROM epi_stock_events WHERE company_id=?', (company,))
        setup.execute('DELETE FROM epi_stock_items WHERE company_id=?', (company,))
        setup.execute('DELETE FROM stock_movements WHERE company_id=?', (company,))
        setup.execute('DELETE FROM unit_epi_stock WHERE company_id=?', (company,))
        setup.execute('DELETE FROM epis WHERE company_id=?', (company,))
        setup.execute('DELETE FROM users WHERE company_id=?', (company,))
        setup.execute('DELETE FROM units WHERE company_id=?', (company,))
        setup.execute('DELETE FROM companies WHERE id=?', (company,))
        try:
            setup.execute('ALTER TABLE epi_stock_events ENABLE TRIGGER stock_events_immutable')
        except Exception:  # noqa: BLE001
            pass
        setup.commit()
        setup.close()
