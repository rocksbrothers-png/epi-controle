
import json
import os
import sqlite3
from contextlib import closing
from datetime import date, datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get('EPI_DB_PATH', str(BASE_DIR / 'epi_control_v4.db'))) 
ROLE_WEIGHT = {'user': 1, 'admin': 2, 'general_admin': 3}
PERMISSIONS = {
    'general_admin': {'dashboard:view', 'users:view', 'users:create', 'users:update', 'users:delete', 'units:view', 'units:create', 'units:update', 'units:delete', 'employees:view', 'employees:create', 'employees:update', 'employees:delete', 'epis:view', 'epis:create', 'epis:update', 'epis:delete', 'deliveries:view', 'deliveries:create', 'fichas:view', 'reports:view', 'alerts:view', 'companies:view'},
    'admin': {'dashboard:view', 'users:view', 'users:create', 'users:update', 'users:delete', 'units:view', 'units:create', 'units:update', 'units:delete', 'employees:view', 'employees:create', 'employees:update', 'employees:delete', 'epis:view', 'epis:create', 'epis:update', 'epis:delete', 'deliveries:view', 'deliveries:create', 'fichas:view', 'reports:view', 'alerts:view', 'companies:view'},
    'user': {'dashboard:view', 'deliveries:view', 'deliveries:create', 'fichas:view', 'alerts:view', 'companies:view', 'units:view', 'employees:view', 'epis:view'}
}


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    return connection


def row_to_dict(row):
    return {key: row[key] for key in row.keys()}


def send_json(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.send_header('Content-Length', str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def parse_json(handler):
    length = int(handler.headers.get('Content-Length', '0'))
    raw = handler.rfile.read(length) if length else b'{}'
    return json.loads(raw.decode('utf-8'))


def require_fields(payload, fields):
    for field in fields:
        if payload.get(field) in (None, ''):
            raise ValueError(f'Campo obrigatorio: {field}')


def bad_request(handler, message):
    send_json(handler, 400, {'error': message})


def forbidden(handler, message):
    send_json(handler, 403, {'error': message})


def not_found(handler):
    send_json(handler, 404, {'error': 'Rota nao encontrada.'})


INITIAL_GENERAL_ADMIN = {'username': 'admin', 'password': 'admin123', 'full_name': 'Administrador Geral'}


def get_meta(connection, key):
    row = connection.execute('SELECT value FROM app_meta WHERE key = ?', (key,)).fetchone()
    return row['value'] if row else None


def set_meta(connection, key, value):
    connection.execute('INSERT INTO app_meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value', (key, value))


def ensure_initial_general_admin(connection):
    existing_general_admin = connection.execute("SELECT id, username FROM users WHERE role = 'general_admin' AND active = 1 ORDER BY id LIMIT 1").fetchone()
    if existing_general_admin:
        if not get_meta(connection, 'initial_general_admin_bootstrapped'):
            set_meta(connection, 'initial_general_admin_bootstrapped', str(existing_general_admin['id']))
        return None

    admin_user = connection.execute("SELECT id, username, full_name FROM users WHERE username = ? LIMIT 1", (INITIAL_GENERAL_ADMIN['username'],)).fetchone()
    if admin_user:
        connection.execute("UPDATE users SET password = ?, full_name = ?, role = 'general_admin', company_id = NULL, active = 1 WHERE id = ?", (INITIAL_GENERAL_ADMIN['password'], INITIAL_GENERAL_ADMIN['full_name'], admin_user['id']))
        set_meta(connection, 'initial_general_admin_bootstrapped', str(admin_user['id']))
        return {'id': admin_user['id'], **INITIAL_GENERAL_ADMIN}

    bootstrapped = get_meta(connection, 'initial_general_admin_bootstrapped')
    if bootstrapped:
        return None

    cursor = connection.execute('INSERT INTO users (username, password, full_name, role, company_id, active) VALUES (?, ?, ?, ?, ?, ?)', (INITIAL_GENERAL_ADMIN['username'], INITIAL_GENERAL_ADMIN['password'], INITIAL_GENERAL_ADMIN['full_name'], 'general_admin', None, 1))
    set_meta(connection, 'initial_general_admin_bootstrapped', str(cursor.lastrowid))
    return {'id': cursor.lastrowid, **INITIAL_GENERAL_ADMIN}


def init_db():
    with closing(get_connection()) as connection:
        connection.executescript(
            '''
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                cnpj TEXT NOT NULL UNIQUE,
                logo_type TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS app_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL,
                company_id INTEGER,
                active INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE SET NULL
            );
            CREATE TABLE IF NOT EXISTS units (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                unit_type TEXT NOT NULL,
                city TEXT NOT NULL,
                notes TEXT DEFAULT '',
                UNIQUE(company_id, name),
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE RESTRICT
            );
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                unit_id INTEGER NOT NULL,
                employee_id_code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                sector TEXT NOT NULL,
                role_name TEXT NOT NULL,
                admission_date TEXT NOT NULL,
                schedule_type TEXT NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE RESTRICT,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT
            );
            CREATE TABLE IF NOT EXISTS epis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                purchase_code TEXT NOT NULL,
                ca TEXT NOT NULL,
                sector TEXT NOT NULL,
                stock INTEGER NOT NULL DEFAULT 0,
                unit_measure TEXT NOT NULL,
                ca_expiry TEXT NOT NULL,
                epi_validity_date TEXT NOT NULL,
                manufacture_date TEXT NOT NULL,
                validity_days INTEGER NOT NULL,
                UNIQUE(company_id, purchase_code),
                UNIQUE(company_id, ca),
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE RESTRICT
            );
            CREATE TABLE IF NOT EXISTS deliveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                epi_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                quantity_label TEXT NOT NULL,
                sector TEXT NOT NULL,
                role_name TEXT NOT NULL,
                delivery_date TEXT NOT NULL,
                next_replacement_date TEXT NOT NULL,
                notes TEXT DEFAULT '',
                signature_name TEXT NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE RESTRICT,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE RESTRICT,
                FOREIGN KEY (epi_id) REFERENCES epis(id) ON DELETE RESTRICT
            );
            '''
        )
        if connection.execute('SELECT COUNT(*) FROM companies').fetchone()[0] == 0:
            connection.executemany('INSERT INTO companies (name, cnpj, logo_type) VALUES (?, ?, ?)', [('DOF Brasil', '00.000.000/0001-91', 'DOF'), ('Norskan Offshore', '00.000.000/0002-72', 'NORSKAN')])
        companies = {row['name']: row['id'] for row in connection.execute('SELECT id, name FROM companies').fetchall()}
        existing_usernames = {row['username'] for row in connection.execute('SELECT username FROM users').fetchall()}
        users_to_insert = []
        if 'dof.admin' not in existing_usernames:
            users_to_insert.append(('dof.admin', 'dofadmin123', 'Administrador DOF Brasil', 'admin', companies['DOF Brasil']))
        if 'dof.user' not in existing_usernames:
            users_to_insert.append(('dof.user', 'dof123', 'Usuario DOF Brasil', 'user', companies['DOF Brasil']))
        if 'norskan.admin' not in existing_usernames:
            users_to_insert.append(('norskan.admin', 'norskanadmin123', 'Administrador Norskan', 'admin', companies['Norskan Offshore']))
        if 'norskan.user' not in existing_usernames:
            users_to_insert.append(('norskan.user', 'norskan123', 'Usuario Norskan Offshore', 'user', companies['Norskan Offshore']))
        if users_to_insert:
            connection.executemany('INSERT INTO users (username, password, full_name, role, company_id) VALUES (?, ?, ?, ?, ?)', users_to_insert)
        bootstrap_admin = ensure_initial_general_admin(connection)
        if connection.execute('SELECT COUNT(*) FROM units').fetchone()[0] == 0:
            connection.executemany('INSERT INTO units (company_id, name, unit_type, city, notes) VALUES (?, ?, ?, ?, ?)', [(companies['DOF Brasil'], 'Base Macae', 'base', 'Macae', 'Base onshore'), (companies['DOF Brasil'], 'Navio Skandi', 'navio', 'Bacia de Campos', 'Navio offshore'), (companies['Norskan Offshore'], 'Base Rio Capital', 'base', 'Rio de Janeiro', 'Base onshore'), (companies['Norskan Offshore'], 'Navio Norskan Alpha', 'navio', 'Bacia de Santos', 'Navio offshore')])
        if connection.execute('SELECT COUNT(*) FROM employees').fetchone()[0] == 0:
            dof_base = connection.execute("SELECT id FROM units WHERE name = 'Base Macae'").fetchone()['id']
            norskan_ship = connection.execute("SELECT id FROM units WHERE name = 'Navio Norskan Alpha'").fetchone()['id']
            connection.executemany('INSERT INTO employees (company_id, unit_id, employee_id_code, name, sector, role_name, admission_date, schedule_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', [(companies['DOF Brasil'], dof_base, '1001', 'Carlos Souza', 'Producao', 'Operador', '2025-01-10', '14x14'), (companies['Norskan Offshore'], norskan_ship, '2001', 'Fernanda Lima', 'SSMA', 'Tecnica de Seguranca', '2024-11-20', '28x28')])
        if connection.execute('SELECT COUNT(*) FROM epis').fetchone()[0] == 0:
            connection.executemany('INSERT INTO epis (company_id, name, purchase_code, ca, sector, stock, unit_measure, ca_expiry, epi_validity_date, manufacture_date, validity_days) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', [(companies['DOF Brasil'], 'Capacete Classe B', 'COD-001', '12345', 'Producao', 18, 'unidade', '2026-04-25', '2026-10-25', '2025-10-25', 180), (companies['DOF Brasil'], 'Bota de Seguranca', 'COD-002', '12346', 'Producao', 12, 'par', '2026-08-01', '2027-02-01', '2025-08-01', 180), (companies['Norskan Offshore'], 'Luva Nitrilica', 'COD-101', '67890', 'SSMA', 7, 'par', '2026-03-28', '2026-09-28', '2025-09-28', 60)])
        connection.commit()
        return bootstrap_admin


def fetch_companies(connection, company_id=None):
    if company_id:
        rows = connection.execute('SELECT id, name, cnpj, logo_type FROM companies WHERE id = ? ORDER BY name', (company_id,)).fetchall()
    else:
        rows = connection.execute('SELECT id, name, cnpj, logo_type FROM companies ORDER BY name').fetchall()
    return [row_to_dict(row) for row in rows]


def fetch_users(connection, actor=None):
    if actor and actor['role'] == 'user':
        return []
    sql = '''SELECT users.id, users.username, users.full_name, users.role, users.company_id, users.active, companies.name AS company_name, companies.cnpj AS company_cnpj, companies.logo_type FROM users LEFT JOIN companies ON companies.id = users.company_id'''
    if actor and actor['role'] == 'admin':
        rows = connection.execute(sql + " WHERE users.company_id = ? OR users.id = ? ORDER BY CASE users.role WHEN 'general_admin' THEN 3 WHEN 'admin' THEN 2 ELSE 1 END DESC, users.full_name", (actor['company_id'], actor['id'])).fetchall()
    else:
        rows = connection.execute(sql + " ORDER BY CASE users.role WHEN 'general_admin' THEN 3 WHEN 'admin' THEN 2 ELSE 1 END DESC, users.full_name").fetchall()
    return [row_to_dict(row) for row in rows]

def fetch_units(connection, actor=None):
    sql = '''SELECT units.id, units.company_id, units.name, units.unit_type, units.city, units.notes, companies.name AS company_name, companies.cnpj AS company_cnpj, companies.logo_type FROM units JOIN companies ON companies.id = units.company_id'''
    if actor and actor['role'] != 'general_admin':
        rows = connection.execute(sql + ' WHERE units.company_id = ? ORDER BY companies.name, units.name', (actor['company_id'],)).fetchall()
    else:
        rows = connection.execute(sql + ' ORDER BY companies.name, units.name').fetchall()
    return [row_to_dict(row) for row in rows]


def fetch_employees(connection, actor=None):
    sql = '''SELECT employees.id, employees.company_id, employees.unit_id, employees.employee_id_code, employees.name, employees.sector, employees.role_name, employees.admission_date, employees.schedule_type, companies.name AS company_name, companies.cnpj AS company_cnpj, companies.logo_type, units.name AS unit_name, units.unit_type, units.city AS unit_city FROM employees JOIN companies ON companies.id = employees.company_id JOIN units ON units.id = employees.unit_id'''
    if actor and actor['role'] != 'general_admin':
        rows = connection.execute(sql + ' WHERE employees.company_id = ? ORDER BY employees.name', (actor['company_id'],)).fetchall()
    else:
        rows = connection.execute(sql + ' ORDER BY employees.name').fetchall()
    return [row_to_dict(row) for row in rows]


def fetch_epis(connection, actor=None):
    sql = '''SELECT epis.id, epis.company_id, epis.name, epis.purchase_code, epis.ca, epis.sector, epis.stock, epis.unit_measure, epis.ca_expiry, epis.epi_validity_date, epis.manufacture_date, epis.validity_days, companies.name AS company_name, companies.cnpj AS company_cnpj, companies.logo_type FROM epis JOIN companies ON companies.id = epis.company_id'''
    if actor and actor['role'] != 'general_admin':
        rows = connection.execute(sql + ' WHERE epis.company_id = ? ORDER BY companies.name, epis.name', (actor['company_id'],)).fetchall()
    else:
        rows = connection.execute(sql + ' ORDER BY companies.name, epis.name').fetchall()
    return [row_to_dict(row) for row in rows]


def fetch_deliveries(connection, actor=None, where_clause='', params=()):
    clauses = []
    query_params = list(params)
    if actor and actor['role'] != 'general_admin':
        clauses.append('deliveries.company_id = ?')
        query_params.append(actor['company_id'])
    if where_clause:
        clean = where_clause.strip()
        clauses.append(clean[6:] if clean.upper().startswith('WHERE ') else clean)
    final_where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
    rows = connection.execute(f'''SELECT deliveries.id, deliveries.company_id, deliveries.employee_id, deliveries.epi_id, deliveries.quantity, deliveries.quantity_label, deliveries.sector, deliveries.role_name, deliveries.delivery_date, deliveries.next_replacement_date, deliveries.notes, deliveries.signature_name, companies.name AS company_name, companies.cnpj AS company_cnpj, companies.logo_type, employees.employee_id_code, employees.name AS employee_name, employees.schedule_type, units.name AS unit_name, units.unit_type, epis.name AS epi_name, epis.purchase_code, epis.ca, epis.unit_measure, epis.epi_validity_date, epis.manufacture_date FROM deliveries JOIN companies ON companies.id = deliveries.company_id JOIN employees ON employees.id = deliveries.employee_id JOIN units ON units.id = employees.unit_id JOIN epis ON epis.id = deliveries.epi_id {final_where} ORDER BY deliveries.delivery_date DESC, deliveries.id DESC''', tuple(query_params)).fetchall()
    return [row_to_dict(row) for row in rows]


def compute_alerts(connection, actor=None):
    alerts = []
    today = date.today()
    for epi in fetch_epis(connection, actor):
        days = (datetime.strptime(epi['ca_expiry'], '%Y-%m-%d').date() - today).days
        stock = int(epi['stock'])
        if stock <= 10:
            alerts.append({'type': 'danger' if stock <= 5 else 'warning', 'title': f"Estoque baixo: {epi['name']}", 'description': f"{epi['company_name']} - saldo atual de {stock} {epi['unit_measure']}(s)."})
        if days <= 30:
            alerts.append({'type': 'danger' if days <= 7 else 'warning', 'title': f"CA proximo do vencimento: {epi['name']}", 'description': f"{epi['company_name']} - vence em {epi['ca_expiry']}."})
    return alerts


def get_user_by_id(connection, user_id):
    row = connection.execute('SELECT users.id, users.username, users.password, users.full_name, users.role, users.company_id, users.active, companies.name AS company_name, companies.cnpj AS company_cnpj, companies.logo_type FROM users LEFT JOIN companies ON companies.id = users.company_id WHERE users.id = ?', (user_id,)).fetchone()
    return row_to_dict(row) if row else None


def get_unit_by_id(connection, unit_id):
    row = connection.execute('SELECT id, company_id, name, unit_type, city, notes FROM units WHERE id = ?', (unit_id,)).fetchone()
    return row_to_dict(row) if row else None


def get_employee_by_id(connection, employee_id):
    row = connection.execute('SELECT id, company_id, unit_id, employee_id_code, name, sector, role_name, admission_date, schedule_type FROM employees WHERE id = ?', (employee_id,)).fetchone()
    return row_to_dict(row) if row else None


def get_epi_by_id(connection, epi_id):
    row = connection.execute('SELECT id, company_id, name, purchase_code, ca, sector, stock, unit_measure, ca_expiry, epi_validity_date, manufacture_date, validity_days FROM epis WHERE id = ?', (epi_id,)).fetchone()
    return row_to_dict(row) if row else None


def require_actor(connection, actor_user_id):
    actor = get_user_by_id(connection, int(actor_user_id))
    if not actor or not int(actor['active']):
        raise PermissionError('Usuário executor inválido.')
    return actor


def ensure_permission(actor, action):
    if action not in PERMISSIONS.get(actor['role'], set()):
        raise PermissionError('Perfil sem permissão para esta ação.')


def ensure_company_access(actor, company_id):
    if actor['role'] == 'general_admin':
        return
    if str(actor.get('company_id') or '') != str(company_id or ''):
        raise PermissionError('Acesso permitido apenas para registros da propria empresa.')


def ensure_resource_company(actor, resource, label='Registro'):
    if not resource:
        raise ValueError(f'{label} nao encontrado.')
    ensure_company_access(actor, resource.get('company_id'))


def authorize_action(connection, actor_user_id, action, company_id=None):
    actor = require_actor(connection, actor_user_id)
    ensure_permission(actor, action)
    if company_id is not None:
        ensure_company_access(actor, company_id)
    return actor


def authorize_user_management(connection, actor_user_id, target_role=None, target_user_id=None, target_company_id=None):
    actor = authorize_action(connection, actor_user_id, 'users:update' if target_user_id else 'users:create')
    if actor['role'] == 'general_admin':
        if target_role == 'general_admin' and target_user_id is None:
            raise ValueError('Nao e permitido criar outro Administrador Geral por esta tela.')
        if target_user_id and target_user_id == actor['id'] and target_role and ROLE_WEIGHT.get(target_role, 0) < ROLE_WEIGHT['general_admin']:
            raise ValueError('Administrador Geral nao pode remover a propria administracao.')
        return actor
    if actor['role'] == 'admin':
        if target_role and target_role != 'user':
            raise ValueError('Administrador pode gerenciar apenas usuarios comuns.')
        if target_user_id:
            target = get_user_by_id(connection, target_user_id)
            if not target:
                raise ValueError('Usuário alvo nao encontrado.')
            if target['role'] != 'user':
                raise ValueError('Administrador pode alterar ou remover apenas usuarios.')
            ensure_company_access(actor, target.get('company_id'))
        if target_company_id:
            ensure_company_access(actor, target_company_id)
        return actor
    raise PermissionError('Somente Administradores podem gerenciar usuarios.')


def parse_actor_user_id_from_query(parsed):
    return int(parse_qs(parsed.query).get('actor_user_id', ['0'])[0])


def build_reports(connection, actor, filters):
    clauses, params = [], []
    if filters.get('company_id'):
        ensure_company_access(actor, int(filters['company_id']))
        clauses.append('deliveries.company_id = ?')
        params.append(filters['company_id'])
    if filters.get('unit_id'):
        unit = get_unit_by_id(connection, int(filters['unit_id']))
        ensure_resource_company(actor, unit, 'Unidade')
        clauses.append('employees.unit_id = ?')
        params.append(filters['unit_id'])
    if filters.get('sector'):
        clauses.append('deliveries.sector = ?')
        params.append(filters['sector'])
    if filters.get('epi_id'):
        epi = get_epi_by_id(connection, int(filters['epi_id']))
        ensure_resource_company(actor, epi, 'EPI')
        clauses.append('deliveries.epi_id = ?')
        params.append(filters['epi_id'])
    if filters.get('start_date'):
        clauses.append('deliveries.delivery_date >= ?')
        params.append(filters['start_date'])
    if filters.get('end_date'):
        clauses.append('deliveries.delivery_date <= ?')
        params.append(filters['end_date'])
    where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ''
    deliveries = fetch_deliveries(connection, actor, where_clause, tuple(params))
    by_unit, by_sector, by_epi = {}, {}, {}
    for item in deliveries:
        by_unit[item['unit_name']] = by_unit.get(item['unit_name'], 0) + int(item['quantity'])
        by_sector[item['sector']] = by_sector.get(item['sector'], 0) + int(item['quantity'])
        by_epi[item['epi_name']] = by_epi.get(item['epi_name'], 0) + int(item['quantity'])
    return {'deliveries': deliveries, 'by_unit': by_unit, 'by_sector': by_sector, 'by_epi': by_epi, 'total_quantity': sum(int(item['quantity']) for item in deliveries)}


def build_bootstrap(connection, actor):
    return {'companies': fetch_companies(connection, None if actor['role'] == 'general_admin' else actor['company_id']), 'users': fetch_users(connection, actor), 'units': fetch_units(connection, actor), 'employees': fetch_employees(connection, actor), 'epis': fetch_epis(connection, actor), 'deliveries': fetch_deliveries(connection, actor), 'alerts': compute_alerts(connection, actor), 'permissions': sorted(PERMISSIONS.get(actor['role'], set()))}

class EpiHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        try:
            if parsed.path == '/api/bootstrap':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, parse_actor_user_id_from_query(parsed), 'dashboard:view')
                    return send_json(self, 200, build_bootstrap(connection, actor))
            if parsed.path == '/api/reports':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, parse_actor_user_id_from_query(parsed), 'reports:view')
                    filters = {key: values[0] for key, values in parse_qs(parsed.query).items() if key != 'actor_user_id'}
                    return send_json(self, 200, build_reports(connection, actor, filters))
            if parsed.path == '/health':
                return send_json(self, 200, {'status': 'ok'})
            if parsed.path == '/':
                self.path = '/index.html'
            return super().do_GET()
        except PermissionError as exc:
            return forbidden(self, str(exc))
        except ValueError as exc:
            return bad_request(self, str(exc))

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            payload = parse_json(self)
        except json.JSONDecodeError:
            return bad_request(self, 'JSON invalido.')
        try:
            if parsed.path == '/api/login':
                require_fields(payload, ['username', 'password'])
                with closing(get_connection()) as connection:
                    row = connection.execute('SELECT users.id, users.username, users.full_name, users.role, users.company_id, companies.name AS company_name, companies.cnpj AS company_cnpj, companies.logo_type FROM users LEFT JOIN companies ON companies.id = users.company_id WHERE users.username = ? AND users.password = ? AND users.active = 1', (payload['username'], payload['password'])).fetchone()
                    if not row:
                        return send_json(self, 401, {'error': 'Usuario ou senha invalidos.'})
                    return send_json(self, 200, {'user': row_to_dict(row), 'permissions': sorted(PERMISSIONS.get(row['role'], set()))})
            with closing(get_connection()) as connection:
                if parsed.path == '/api/users':
                    require_fields(payload, ['actor_user_id', 'username', 'password', 'full_name', 'role'])
                    actor = authorize_user_management(connection, int(payload['actor_user_id']), payload['role'], None, payload.get('company_id'))
                    company_id = payload.get('company_id') or None
                    if payload['role'] in ('admin', 'user') and not company_id:
                        raise ValueError('Perfil com empresa exige uma empresa vinculada.')
                    cursor = connection.execute('INSERT INTO users (username, password, full_name, role, company_id, active) VALUES (?, ?, ?, ?, ?, ?)', (payload['username'], payload['password'], payload['full_name'], payload['role'], company_id, 1))
                    connection.commit()
                    return send_json(self, 201, {'id': cursor.lastrowid, 'actor_role': actor['role']})
                if parsed.path == '/api/units':
                    require_fields(payload, ['actor_user_id', 'company_id', 'name', 'unit_type', 'city'])
                    authorize_action(connection, int(payload['actor_user_id']), 'units:create', int(payload['company_id']))
                    cursor = connection.execute('INSERT INTO units (company_id, name, unit_type, city, notes) VALUES (?, ?, ?, ?, ?)', (payload['company_id'], payload['name'], payload['unit_type'], payload['city'], payload.get('notes', '')))
                    connection.commit()
                    return send_json(self, 201, {'id': cursor.lastrowid})
                if parsed.path == '/api/employees':
                    require_fields(payload, ['actor_user_id', 'company_id', 'unit_id', 'employee_id_code', 'name', 'sector', 'role_name', 'admission_date', 'schedule_type'])
                    actor = authorize_action(connection, int(payload['actor_user_id']), 'employees:create', int(payload['company_id']))
                    unit = get_unit_by_id(connection, int(payload['unit_id']))
                    ensure_resource_company(actor, unit, 'Unidade')
                    if str(unit['company_id']) != str(payload['company_id']):
                        raise ValueError('Unidade e empresa do colaborador precisam ser compativeis.')
                    cursor = connection.execute('INSERT INTO employees (company_id, unit_id, employee_id_code, name, sector, role_name, admission_date, schedule_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (payload['company_id'], payload['unit_id'], payload['employee_id_code'], payload['name'], payload['sector'], payload['role_name'], payload['admission_date'], payload['schedule_type']))
                    connection.commit()
                    return send_json(self, 201, {'id': cursor.lastrowid})
                if parsed.path == '/api/epis':
                    require_fields(payload, ['actor_user_id', 'company_id', 'name', 'purchase_code', 'ca', 'sector', 'stock', 'unit_measure', 'ca_expiry', 'epi_validity_date', 'manufacture_date', 'validity_days'])
                    authorize_action(connection, int(payload['actor_user_id']), 'epis:create', int(payload['company_id']))
                    cursor = connection.execute('INSERT INTO epis (company_id, name, purchase_code, ca, sector, stock, unit_measure, ca_expiry, epi_validity_date, manufacture_date, validity_days) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (payload['company_id'], payload['name'], payload['purchase_code'], payload['ca'], payload['sector'], int(payload['stock']), payload['unit_measure'], payload['ca_expiry'], payload['epi_validity_date'], payload['manufacture_date'], int(payload['validity_days'])))
                    connection.commit()
                    return send_json(self, 201, {'id': cursor.lastrowid})
                if parsed.path == '/api/deliveries':
                    require_fields(payload, ['actor_user_id', 'company_id', 'employee_id', 'epi_id', 'quantity', 'delivery_date', 'next_replacement_date', 'signature_name'])
                    actor = authorize_action(connection, int(payload['actor_user_id']), 'deliveries:create', int(payload['company_id']))
                    epi = get_epi_by_id(connection, int(payload['epi_id']))
                    employee = get_employee_by_id(connection, int(payload['employee_id']))
                    ensure_resource_company(actor, epi, 'EPI')
                    ensure_resource_company(actor, employee, 'Colaborador')
                    if str(epi['company_id']) != str(payload['company_id']) or str(employee['company_id']) != str(payload['company_id']):
                        raise ValueError('Empresa, colaborador e EPI precisam pertencer a mesma empresa.')
                    quantity = int(payload['quantity'])
                    if int(epi['stock']) < quantity:
                        raise ValueError('Estoque insuficiente para esta entrega.')
                    cursor = connection.execute('INSERT INTO deliveries (company_id, employee_id, epi_id, quantity, quantity_label, sector, role_name, delivery_date, next_replacement_date, notes, signature_name) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (payload['company_id'], payload['employee_id'], payload['epi_id'], quantity, epi['unit_measure'], employee['sector'], employee['role_name'], payload['delivery_date'], payload['next_replacement_date'], payload.get('notes', ''), payload['signature_name']))
                    connection.execute('UPDATE epis SET stock = stock - ? WHERE id = ?', (quantity, payload['epi_id']))
                    connection.commit()
                    return send_json(self, 201, {'id': cursor.lastrowid})
            return not_found(self)
        except PermissionError as exc:
            return forbidden(self, str(exc))
        except ValueError as exc:
            return bad_request(self, str(exc))
        except sqlite3.IntegrityError as exc:
            return bad_request(self, f'Erro de integridade: {exc}')

    def do_PUT(self):
        parsed = urlparse(self.path)
        try:
            payload = parse_json(self)
            with closing(get_connection()) as connection:
                if parsed.path.startswith('/api/users/'):
                    user_id = int(parsed.path.rsplit('/', 1)[-1])
                    require_fields(payload, ['actor_user_id', 'username', 'full_name', 'role'])
                    authorize_user_management(connection, int(payload['actor_user_id']), payload['role'], user_id, payload.get('company_id'))
                    current = get_user_by_id(connection, user_id)
                    if not current:
                        raise ValueError('Usuário nao encontrado.')
                    password = payload.get('password') or current['password']
                    company_id = payload.get('company_id') or None
                    if payload['role'] in ('admin', 'user') and not company_id:
                        raise ValueError('Perfil com empresa exige uma empresa vinculada.')
                    connection.execute('UPDATE users SET username = ?, password = ?, full_name = ?, role = ?, company_id = ?, active = ? WHERE id = ?', (payload['username'], password, payload['full_name'], payload['role'], company_id, int(payload.get('active', 1)), user_id))
                    connection.commit()
                    return send_json(self, 200, {'ok': True})
                if parsed.path.startswith('/api/units/'):
                    unit_id = int(parsed.path.rsplit('/', 1)[-1])
                    require_fields(payload, ['actor_user_id', 'company_id', 'name', 'unit_type', 'city'])
                    actor = authorize_action(connection, int(payload['actor_user_id']), 'units:update', int(payload['company_id']))
                    current = get_unit_by_id(connection, unit_id)
                    ensure_resource_company(actor, current, 'Unidade')
                    connection.execute('UPDATE units SET company_id = ?, name = ?, unit_type = ?, city = ?, notes = ? WHERE id = ?', (payload['company_id'], payload['name'], payload['unit_type'], payload['city'], payload.get('notes', ''), unit_id))
                    connection.commit()
                    return send_json(self, 200, {'ok': True})
                if parsed.path.startswith('/api/employees/'):
                    employee_id = int(parsed.path.rsplit('/', 1)[-1])
                    require_fields(payload, ['actor_user_id', 'company_id', 'unit_id', 'employee_id_code', 'name', 'sector', 'role_name', 'admission_date', 'schedule_type'])
                    actor = authorize_action(connection, int(payload['actor_user_id']), 'employees:update', int(payload['company_id']))
                    current = get_employee_by_id(connection, employee_id)
                    ensure_resource_company(actor, current, 'Colaborador')
                    unit = get_unit_by_id(connection, int(payload['unit_id']))
                    ensure_resource_company(actor, unit, 'Unidade')
                    if str(unit['company_id']) != str(payload['company_id']):
                        raise ValueError('Unidade e empresa do colaborador precisam ser compativeis.')
                    connection.execute('UPDATE employees SET company_id = ?, unit_id = ?, employee_id_code = ?, name = ?, sector = ?, role_name = ?, admission_date = ?, schedule_type = ? WHERE id = ?', (payload['company_id'], payload['unit_id'], payload['employee_id_code'], payload['name'], payload['sector'], payload['role_name'], payload['admission_date'], payload['schedule_type'], employee_id))
                    connection.commit()
                    return send_json(self, 200, {'ok': True})
                if parsed.path.startswith('/api/epis/'):
                    epi_id = int(parsed.path.rsplit('/', 1)[-1])
                    require_fields(payload, ['actor_user_id', 'company_id', 'name', 'purchase_code', 'ca', 'sector', 'stock', 'unit_measure', 'ca_expiry', 'epi_validity_date', 'manufacture_date', 'validity_days'])
                    actor = authorize_action(connection, int(payload['actor_user_id']), 'epis:update', int(payload['company_id']))
                    current = get_epi_by_id(connection, epi_id)
                    ensure_resource_company(actor, current, 'EPI')
                    connection.execute('UPDATE epis SET company_id = ?, name = ?, purchase_code = ?, ca = ?, sector = ?, stock = ?, unit_measure = ?, ca_expiry = ?, epi_validity_date = ?, manufacture_date = ?, validity_days = ? WHERE id = ?', (payload['company_id'], payload['name'], payload['purchase_code'], payload['ca'], payload['sector'], int(payload['stock']), payload['unit_measure'], payload['ca_expiry'], payload['epi_validity_date'], payload['manufacture_date'], int(payload['validity_days']), epi_id))
                    connection.commit()
                    return send_json(self, 200, {'ok': True})
            return not_found(self)
        except PermissionError as exc:
            return forbidden(self, str(exc))
        except ValueError as exc:
            return bad_request(self, str(exc))
        except sqlite3.IntegrityError as exc:
            return bad_request(self, f'Erro de integridade: {exc}')

    def do_DELETE(self):
        parsed = urlparse(self.path)
        try:
            with closing(get_connection()) as connection:
                if parsed.path.startswith('/api/users/'):
                    user_id = int(parsed.path.rsplit('/', 1)[-1].split('?')[0])
                    actor_user_id = parse_actor_user_id_from_query(parsed)
                    authorize_user_management(connection, actor_user_id, None, user_id, None)
                    if actor_user_id == user_id:
                        raise ValueError('Nao e permitido excluir o proprio usuario logado.')
                    connection.execute('DELETE FROM users WHERE id = ?', (user_id,))
                    connection.commit()
                    return send_json(self, 200, {'ok': True})
                if parsed.path.startswith('/api/units/'):
                    unit_id = int(parsed.path.rsplit('/', 1)[-1].split('?')[0])
                    actor = authorize_action(connection, parse_actor_user_id_from_query(parsed), 'units:delete')
                    unit = get_unit_by_id(connection, unit_id)
                    ensure_resource_company(actor, unit, 'Unidade')
                    if connection.execute('SELECT COUNT(*) FROM employees WHERE unit_id = ?', (unit_id,)).fetchone()[0]:
                        raise ValueError('Nao e possivel excluir unidade com colaboradores vinculados.')
                    connection.execute('DELETE FROM units WHERE id = ?', (unit_id,))
                    connection.commit()
                    return send_json(self, 200, {'ok': True})
                if parsed.path.startswith('/api/employees/'):
                    employee_id = int(parsed.path.rsplit('/', 1)[-1].split('?')[0])
                    actor = authorize_action(connection, parse_actor_user_id_from_query(parsed), 'employees:delete')
                    employee = get_employee_by_id(connection, employee_id)
                    ensure_resource_company(actor, employee, 'Colaborador')
                    if connection.execute('SELECT COUNT(*) FROM deliveries WHERE employee_id = ?', (employee_id,)).fetchone()[0]:
                        raise ValueError('Nao e possivel excluir colaborador com ficha registrada.')
                    connection.execute('DELETE FROM employees WHERE id = ?', (employee_id,))
                    connection.commit()
                    return send_json(self, 200, {'ok': True})
                if parsed.path.startswith('/api/epis/'):
                    epi_id = int(parsed.path.rsplit('/', 1)[-1].split('?')[0])
                    actor = authorize_action(connection, parse_actor_user_id_from_query(parsed), 'epis:delete')
                    epi = get_epi_by_id(connection, epi_id)
                    ensure_resource_company(actor, epi, 'EPI')
                    if connection.execute('SELECT COUNT(*) FROM deliveries WHERE epi_id = ?', (epi_id,)).fetchone()[0]:
                        raise ValueError('Nao e possivel excluir EPI com ficha registrada.')
                    connection.execute('DELETE FROM epis WHERE id = ?', (epi_id,))
                    connection.commit()
                    return send_json(self, 200, {'ok': True})
            return not_found(self)
        except PermissionError as exc:
            return forbidden(self, str(exc))
        except ValueError as exc:
            return bad_request(self, str(exc))


if __name__ == '__main__':
    bootstrap_admin = init_db()
    port = int(os.environ.get('PORT', 8000))
    server = ThreadingHTTPServer(('0.0.0.0', port), EpiHandler)
    if bootstrap_admin:
        print('Bootstrap inicial executado com sucesso.')
        print(f"Administrador Geral inicial: {bootstrap_admin['username']} / {bootstrap_admin['password']}")
    print(f'Controle de EPI disponível em http://0.0.0.0:{port}')
    server.serve_forever()


