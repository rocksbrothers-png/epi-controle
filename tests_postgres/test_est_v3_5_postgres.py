"""EST-V3.5 (G02) contra PostgreSQL REAL — desacoplamento do catálogo por lote.

Prova, no schema PG real (migrations 030/031 EST-V2 + coluna EST-V3.5), que as
consultas por LOTE físico funcionam no banco real — onde physical_expiry_date é
DATE (o CAST/COALESCE/MIN e o filtro por conjunto podem divergir do SQLite) — e
que a coluna purchase_order_items.manufacturer_validity_date foi provisionada
por _safe_add_column (sem migration numerada).
"""

import os
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL', '').startswith('postgres'),
    reason='EST-V3.5 exige PostgreSQL real.',
)

PAST = (date.today() - timedelta(days=10)).isoformat()
FUTURE = (date.today() + timedelta(days=365)).isoformat()


@pytest.fixture(scope='module')
def conn():
    from core.bootstrap import init_db
    from core.database import get_connection
    init_db()  # idempotente: provisiona o schema atual, inclusive a coluna EST-V3.5
    connection = get_connection()
    yield connection
    connection.close()


@pytest.fixture
def seed(conn):
    c = conn
    c.execute('SAVEPOINT est_v3_5')
    now = datetime.now(timezone.utc).isoformat()
    sfx = uuid4().hex
    company = c.execute('INSERT INTO companies(name,cnpj,logo_type) VALUES (?,?,?)',
                        ('V35 ' + sfx, sfx, 'text')).lastrowid
    unit = c.execute('INSERT INTO units(company_id,name,unit_type,city) VALUES (?,?,?,?)',
                     (company, 'Unid', 'base', 'Test')).lastrowid
    # catálogo EM DIA (FUTURE): qualquer "vencido" terá de vir do LOTE físico
    epi = c.execute('INSERT INTO epis(company_id,unit_id,name,purchase_code,ca,sector,unit_measure,'
                    'ca_expiry,epi_validity_date,manufacture_date,validity_days) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                    (company, unit, 'EPI', sfx, 'CA', 'S', 'un', '2030-01-01', FUTURE, '2020-01-01', 0)).lastrowid
    actor = c.execute('INSERT INTO users(username,password,full_name,role,company_id) VALUES (?,?,?,?,?)',
                      (sfx, 'x', 'Actor', 'general_admin', company)).lastrowid

    def item(physical):
        from modules.stock.service import create_stock_item, next_company_qr_sequence, record_received_item_physical
        seqv = next_company_qr_sequence(c, company)
        iid = create_stock_item(c, company, unit, epi, 'N/A', 'M', 'N/A', seqv,
                                'QR-' + uuid4().hex, None, '', '', 'unit', '', '', actor, now)
        if physical:
            record_received_item_physical(c, iid, physical, actor, now)
        return iid

    yield dict(c=c, company=company, unit=unit, epi=epi, actor=actor, now=now, item=item)
    c.execute('ROLLBACK TO SAVEPOINT est_v3_5')
    c.execute('RELEASE SAVEPOINT est_v3_5')
    c.rollback()


def test_compliance_counts_expired_physical_lot_under_valid_catalog(seed):
    from modules.stock.service import compute_stock_compliance
    seed['item'](FUTURE)  # lote válido
    seed['item'](PAST)    # lote físico vencido (catálogo do EPI está em dia)
    r = compute_stock_compliance(seed['c'], seed['company'], seed['unit'])
    # PAST vira blocked_expired no recebimento (G15) → sai do disponível e entra
    # em admin_blocked; o válido não conta. A validade física rege a classificação.
    assert r['summary']['admin_blocked'] == 1
    assert r['summary']['product_expired'] == 0  # o vencido já está bloqueado, não "disponível vencido"


def test_compliance_expired_in_stock_lot_counts_product_expired(seed):
    # Um lote que venceu DEPOIS de entrar (ainda in_stock) deve contar como
    # product_expired pela validade física — mesmo com o catálogo em dia.
    from modules.stock.service import compute_stock_compliance
    iid = seed['item'](FUTURE)
    seed['c'].execute('UPDATE epi_stock_items SET physical_expiry_date = ? WHERE id = ?', (PAST, iid))
    r = compute_stock_compliance(seed['c'], seed['company'], seed['unit'])
    assert r['summary']['product_expired'] == 1
    rec = r['categories']['product_expired'][0]
    assert str(rec['product_validity']) == PAST


def test_physical_validity_map_min_on_pg(seed):
    from modules.stock.service import epi_physical_validity_map
    a = seed['item'](FUTURE)
    seed['c'].execute('UPDATE epi_stock_items SET physical_expiry_date = ? WHERE id = ?', (PAST, a))
    seed['item'](FUTURE)
    m = epi_physical_validity_map(seed['c'], seed['company'], seed['unit'])
    assert str(m.get(seed['epi'])) == PAST  # MIN(CAST(... AS TEXT)) cronológico no PG


def test_validity_filter_ids_on_pg(seed):
    from modules.stock.service import epi_ids_with_manufacturer_validity
    iid = seed['item'](FUTURE)
    seed['c'].execute('UPDATE epi_stock_items SET physical_expiry_date = ? WHERE id = ?', (PAST, iid))
    ids = epi_ids_with_manufacturer_validity(seed['c'], 'expired', company_id=seed['company'], unit_id=seed['unit'])
    assert seed['epi'] in ids


def test_po_item_manufacturer_validity_column_provisioned_on_pg(seed):
    # Migration numerada 032 rodou no PG (via init_db) → a coluna existe.
    # Adversarial de schema: falha se a coluna não foi provisionada.
    row = seed['c'].execute(
        "SELECT COUNT(*) AS n FROM information_schema.columns "
        "WHERE table_name = 'purchase_order_items' AND column_name = 'manufacturer_validity_date'"
    ).fetchone()
    assert int(row['n'] if hasattr(row, 'keys') else row[0]) == 1


def test_migration_032_is_numbered_and_auditable(seed):
    # Ponto 4: a coluna em PostgreSQL vem de uma migration NUMERADA e AUDITÁVEL
    # (registrada em app_migrations), não de _safe_add_column (que é gated a
    # SQLite). Adversarial: falha se a migration não foi aplicada/registrada.
    row = seed['c'].execute(
        "SELECT status FROM app_migrations WHERE migration_id = '032_po_item_manufacturer_validity'"
    ).fetchone()
    assert row is not None
    assert str(row['status'] if hasattr(row, 'keys') else row[0]) == 'applied'
