import os
import sqlite3
import tempfile
import threading
from datetime import date

from modules.deliveries.service import create_delivery_service


def mk_conn(path):
    conn = sqlite3.connect(path, check_same_thread=False, timeout=2.0, isolation_level='DEFERRED')
    conn.row_factory = sqlite3.Row
    return conn


def setup_db(conn):
    conn.executescript('''
    PRAGMA journal_mode=WAL;
    CREATE TABLE employees (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT, schedule_type TEXT);
    CREATE TABLE epis (id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, unit_measure TEXT);
    CREATE TABLE deliveries (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      company_id INTEGER, employee_id INTEGER, epi_id INTEGER, quantity INTEGER,
      quantity_label TEXT, sector TEXT, role_name TEXT, delivery_date TEXT,
      next_replacement_date TEXT, notes TEXT, signature_name TEXT, signature_ip TEXT,
      signature_at TEXT, signature_data TEXT, signature_comment TEXT, unit_id INTEGER,
      stock_movement_id INTEGER
    );
    CREATE TABLE epi_stock_items (
      id INTEGER PRIMARY KEY,
      company_id INTEGER,
      unit_id INTEGER,
      epi_id INTEGER,
      status TEXT,
      qr_code_value TEXT,
      delivery_id INTEGER,
      delivered_at TEXT,
      updated_at TEXT
    );
    CREATE TABLE stock_movements (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      company_id INTEGER, unit_id INTEGER, epi_id INTEGER, movement_type TEXT,
      quantity INTEGER, previous_stock INTEGER, new_stock INTEGER, source_type TEXT,
      source_id INTEGER, notes TEXT, actor_user_id INTEGER, actor_name TEXT, created_at TEXT
    );
    CREATE TABLE unit_epi_stock (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      company_id INTEGER, unit_id INTEGER, epi_id INTEGER, quantity INTEGER
    );
    ''')
    conn.execute("INSERT INTO employees VALUES (1,1,'Emp','mensal')")
    conn.execute("INSERT INTO epis VALUES (1,1,1,'unidade')")
    conn.execute("INSERT INTO epi_stock_items VALUES (10,1,1,1,'in_stock','QR-10',NULL,'','')")
    conn.execute("INSERT INTO unit_epi_stock(company_id,unit_id,epi_id,quantity) VALUES (1,1,1,1)")
    conn.commit()


def stubs(actor_id):
    def authorize_action(connection, _actor_id, permission, company_id=None):
        return {'id': actor_id, 'full_name': f'User {actor_id}', 'role': 'admin', 'company_id': 1}

    return {
        'authorize_action': authorize_action,
        'resolve_actor_user_id': lambda: actor_id,
        'get_employee_by_id': lambda c, i: dict(c.execute('SELECT * FROM employees WHERE id=?', (i,)).fetchone()),
        'get_epi_by_id': lambda c, i: dict(c.execute('SELECT * FROM epis WHERE id=?', (i,)).fetchone()),
        'ensure_resource_company': lambda *args, **kwargs: None,
        'get_employee_current_unit': lambda c, _eid: 1,
        'actor_operational_unit_id': lambda c, actor: 1,
        'get_unit_stock': lambda c, company_id, unit_id, epi_id: (
            dict(c.execute('SELECT id, quantity FROM unit_epi_stock WHERE company_id=? AND unit_id=? AND epi_id=?', (company_id, unit_id, epi_id)).fetchone())
        ),
        'upsert_unit_stock': lambda c, company_id, unit_id, epi_id, quantity: c.execute(
            'UPDATE unit_epi_stock SET quantity=? WHERE company_id=? AND unit_id=? AND epi_id=?',
            (quantity, company_id, unit_id, epi_id)
        ),
        'ensure_ficha_for_delivery': lambda *args, **kwargs: None,
    }


def run_one(path, actor_id, results):
    conn = mk_conn(path)
    payload = {
        'actor_user_id': actor_id,
        'company_id': 1,
        'employee_id': 1,
        'epi_id': 1,
        'quantity': 1,
        'sector': 'Ops',
        'role_name': 'Worker',
        'delivery_date': str(date.today()),
        'next_replacement_date': str(date.today()),
        'stock_item_id': 10,
        'stock_qr_code': 'QR-10',
        'notes': ''
    }
    try:
        delivery_id = create_delivery_service(conn, payload, **stubs(actor_id))
        results.append(('ok', delivery_id))
    except Exception as exc:
        results.append(('err', str(exc)))
    finally:
        conn.close()


if __name__ == '__main__':
    fd, path = tempfile.mkstemp(prefix='epi-smoke-', suffix='.sqlite3')
    os.close(fd)
    try:
        conn = mk_conn(path)
        setup_db(conn)
        conn.close()

        results = []
        t1 = threading.Thread(target=run_one, args=(path, 101, results))
        t2 = threading.Thread(target=run_one, args=(path, 202, results))
        t1.start(); t2.start(); t1.join(); t2.join()

        ok = [r for r in results if r[0] == 'ok']
        err = [r for r in results if r[0] == 'err']
        print('results=', results)
        if len(ok) != 1 or len(err) != 1:
            raise SystemExit('FAILED: expected exactly one success and one failure')
        print('PASS: only one concurrent delivery succeeded')
    finally:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
