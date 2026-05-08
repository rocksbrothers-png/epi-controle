import io
import sqlite3
from contextlib import redirect_stdout
from datetime import datetime

from server_postgres import ensure_ficha_for_delivery


def dict_factory(cur, row):
    return {c[0]: row[i] for i, c in enumerate(cur.description)}


def setup_db():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = dict_factory
    conn.execute('''CREATE TABLE epi_ficha_periods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        employee_id INTEGER,
        unit_id INTEGER,
        schedule_type TEXT,
        period_start TEXT,
        period_end TEXT,
        status TEXT DEFAULT 'open',
        batch_signature_name TEXT DEFAULT '',
        batch_signature_data TEXT DEFAULT '',
        batch_signature_ip TEXT DEFAULT '',
        batch_signature_at TEXT DEFAULT '',
        batch_signature_comment TEXT DEFAULT '',
        ficha_sequence INTEGER NOT NULL DEFAULT 1,
        created_at TEXT,
        updated_at TEXT,
        UNIQUE(employee_id, period_start, period_end, ficha_sequence)
    )''')
    conn.execute('''CREATE TABLE epi_ficha_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ficha_period_id INTEGER,
        delivery_id INTEGER UNIQUE,
        company_id INTEGER,
        employee_id INTEGER,
        unit_id INTEGER,
        epi_id INTEGER,
        quantity INTEGER,
        item_signature_name TEXT DEFAULT '',
        item_signature_data TEXT DEFAULT '',
        item_signature_ip TEXT DEFAULT '',
        item_signature_at TEXT DEFAULT '',
        item_signature_comment TEXT DEFAULT '',
        signed_mode TEXT DEFAULT '',
        created_at TEXT,
        updated_at TEXT
    )''')
    return conn


def mk_payload(delivery_id, day):
    return {
        'id': delivery_id,
        'company_id': 1,
        'employee_id': 10,
        'unit_id': 20,
        'epi_id': 30,
        'quantity': 1,
        'delivery_date': day,
        'signature_name': '',
        'signature_data': '',
        'signature_ip': '',
        'signature_at': '',
        'signature_comment': '',
        'schedule_type': '14x14',
    }


def periods(conn):
    return conn.execute('SELECT id, status, period_start, period_end, ficha_sequence FROM epi_ficha_periods ORDER BY id').fetchall()


def run():
    conn = setup_db()
    out = io.StringIO()
    results = {}
    with redirect_stdout(out):
        ensure_ficha_for_delivery(conn, mk_payload(100, '2026-05-01'))
        p1 = periods(conn)
        results[1] = len(p1) == 1 and p1[0]['status'] == 'open'

        ensure_ficha_for_delivery(conn, mk_payload(101, '2026-05-03'))
        p2 = periods(conn)
        results[2] = len(p2) == 1 and p2[0]['id'] == p1[0]['id']

        conn.execute("UPDATE epi_ficha_periods SET status='signed' WHERE id=?", (p2[0]['id'],))
        ensure_ficha_for_delivery(conn, mk_payload(102, '2026-05-04'))
        p3 = periods(conn)
        results[3] = len(p3) == 2 and p3[-1]['id'] != p2[0]['id']

        conn.execute("UPDATE epi_ficha_periods SET status='closed' WHERE id=?", (p3[-1]['id'],))
        ensure_ficha_for_delivery(conn, mk_payload(103, '2026-05-05'))
        p4 = periods(conn)
        results[4] = len(p4) == 3 and p4[-1]['id'] != p3[-1]['id']

        conn.execute("UPDATE epi_ficha_periods SET status='closed' WHERE id=?", (p4[-1]['id'],))
        now = datetime.utcnow().isoformat()
        conn.execute(
            "INSERT INTO epi_ficha_periods (company_id, employee_id, unit_id, schedule_type, period_start, period_end, status, ficha_sequence, created_at, updated_at) VALUES (1,10,20,'14x14','2026-06-01','2026-06-14','closed',1,?,?)",
            (now, now),
        )
        ensure_ficha_for_delivery(conn, mk_payload(104, '2026-06-01'))
        p5 = periods(conn)
        results[5] = any(r['period_start'] == '2026-06-01' and r['period_end'] == '2026-06-14' and r['ficha_sequence'] == 2 for r in p5)
        results[6] = results[5]

    warnings = out.getvalue()
    no_mismatch_warning = '14 values for 15 columns' not in warnings
    items_count = conn.execute('SELECT COUNT(*) AS c FROM epi_ficha_items').fetchone()['c']

    assert results[1], 'cenario 1 falhou'
    assert results[2], 'cenario 2 falhou'
    assert results[3], 'cenario 3 falhou'
    assert results[4], 'cenario 4 falhou'
    assert results[5], 'cenario 5 falhou'
    assert results[6], 'cenario 6 falhou'
    assert no_mismatch_warning, 'warning 14 values for 15 columns detectado'
    assert items_count >= 5, 'itens de ficha nao foram inseridos corretamente'

    print('PASS cenario_1:', results[1])
    print('PASS cenario_2:', results[2])
    print('PASS cenario_3:', results[3])
    print('PASS cenario_4:', results[4])
    print('PASS cenario_5:', results[5])
    print('PASS cenario_6:', results[6])
    print('PASS sem_warning_14_15:', no_mismatch_warning)
    print('PASS itens_ficha_inseridos:', items_count)


if __name__ == '__main__':
    run()
