import sqlite3

import pytest

from server_postgres import (
    build_ficha_epi_html,
    build_ficha_epi_html_by_period,
    get_employee_portal_context_by_token,
    render_ficha_epi_html_document,
    resolve_external_employee_context,
    validate_portal_cpf_with_attempts,
)


def _base_conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT, cnpj TEXT, logo_type TEXT DEFAULT '')")
    conn.execute("CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT, unit_type TEXT DEFAULT 'base')")
    conn.execute(
        'CREATE TABLE employees ('
        'id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, cpf TEXT, name TEXT, '
        "email TEXT DEFAULT '', whatsapp TEXT DEFAULT '', preferred_contact_channel TEXT DEFAULT '', "
        "admission_date TEXT DEFAULT '', "
        'employee_id_code TEXT, role_name TEXT, sector TEXT, schedule_type TEXT'
        ')'
    )
    conn.execute(
        'CREATE TABLE users ('
        'id INTEGER PRIMARY KEY, username TEXT, password TEXT, full_name TEXT, role TEXT, company_id INTEGER, active INTEGER, '
        'linked_employee_id INTEGER, employee_access_token TEXT, employee_access_expires_at TEXT'
        ')'
    )
    conn.execute('CREATE TABLE ficha_epi_config (id INTEGER PRIMARY KEY, company_id INTEGER, titulo TEXT, declaracao TEXT, observacoes TEXT, rastreabilidade TEXT, created_at TEXT, updated_at TEXT)')
    conn.execute('CREATE TABLE epis (id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, name TEXT, ca TEXT, unit_measure TEXT, manufacture_date TEXT, epi_validity_date TEXT)')
    conn.execute('CREATE TABLE deliveries (id INTEGER PRIMARY KEY, employee_id INTEGER, epi_id INTEGER, quantity INTEGER, delivery_date TEXT, next_replacement_date TEXT, signature_data TEXT, signature_name TEXT, returned_date TEXT)')
    conn.execute('CREATE TABLE epi_ficha_periods (id INTEGER PRIMARY KEY, company_id INTEGER, employee_id INTEGER, unit_id INTEGER, period_start TEXT, period_end TEXT, status TEXT)')
    conn.execute('CREATE TABLE epi_ficha_items (id INTEGER PRIMARY KEY, ficha_period_id INTEGER, delivery_id INTEGER, epi_id INTEGER, quantity INTEGER, item_signature_data TEXT, item_signature_name TEXT)')
    conn.execute('CREATE TABLE epi_devolutions (id INTEGER PRIMARY KEY, ficha_period_id INTEGER, company_id INTEGER, employee_id INTEGER, epi_id INTEGER, delivery_id INTEGER, returned_date TEXT, condition TEXT, destination TEXT, notes TEXT, reason TEXT, signature_name TEXT, signature_at TEXT, received_by_name TEXT, quantity INTEGER)')
    conn.execute(
        'CREATE TABLE employee_portal_links ('
        'id INTEGER PRIMARY KEY, company_id INTEGER, employee_id INTEGER, token TEXT, qr_code_value TEXT, active INTEGER, expires_at TEXT, '
        'created_by_user_id INTEGER, created_at TEXT, updated_at TEXT, cpf_attempts INTEGER DEFAULT 0, '
        "last_cpf_attempt_at TEXT DEFAULT '', blocked_at TEXT DEFAULT ''"
        ')'
    )
    conn.execute(
        'CREATE TABLE employee_portal_audit_logs ('
        'id INTEGER PRIMARY KEY, company_id INTEGER, employee_id INTEGER, portal_link_id INTEGER, token_hash TEXT, '
        'action TEXT, ip_address TEXT, user_agent TEXT, payload TEXT, created_at TEXT'
        ')'
    )
    conn.execute("INSERT INTO companies (id, name, cnpj) VALUES (1, 'ACME', '00000000000100')")
    conn.execute("INSERT INTO units (id, company_id, name) VALUES (10, 1, 'Base')")
    conn.execute(
        "INSERT INTO employees (id, company_id, unit_id, cpf, name, employee_id_code, role_name, sector, schedule_type) "
        "VALUES (100, 1, 10, '12345678901', 'João', 'E100', 'Operador', 'Ops', '14x14')"
    )
    return conn


def test_renderer_shared_structure_for_current_and_period():
    base = dict(
        employee={'name': 'João', 'role_name': 'Operador', 'sector': 'Ops'},
        company={'name': 'ACME', 'logo_type': ''},
        unit={'name': 'Base'},
        deliveries=[{
            'quantity': 1,
            'unit_measure': 'unidade',
            'epi_name': 'Capacete',
            'ca': 'CA-1',
            'manufacture_date': '2026-01-01',
            'next_replacement_date': '2026-12-31',
            'delivery_date': '2026-02-01',
            'returned_date': '',
            'signature_data': '',
        }],
        devolutions=[],
        config={'titulo': 'Ficha EPI', 'declaracao': 'Declaração', 'observacoes': 'Obs', 'rastreabilidade': 'R-1'},
    )
    current_html = render_ficha_epi_html_document(**base)
    period_html = render_ficha_epi_html_document(**base, period_label='2026-01-01 a 2026-01-14')

    assert 'Ficha EPI - João' in current_html
    assert '<th class="th-epi">EPI</th>' in current_html
    assert 'PERÍODO:' not in current_html

    assert 'PERÍODO:' in period_html
    assert '2026-01-01 a 2026-01-14' in period_html
    assert '<th class="th-epi">EPI</th>' in period_html


def test_renderer_includes_print_css_blocks():
    html = render_ficha_epi_html_document(
        employee={'name': 'João', 'role_name': 'Operador', 'sector': 'Ops'},
        company={'name': 'ACME', 'logo_type': ''},
        unit={'name': 'Base'},
        deliveries=[],
        devolutions=[],
        config={'titulo': 'Ficha EPI', 'declaracao': 'Declaração', 'observacoes': 'Obs', 'rastreabilidade': 'R-1'},
    )
    assert '@page' in html
    assert 'th-assina' in html
    assert 'table {' in html


def test_build_ficha_by_period_does_not_mix_items_from_other_periods():
    conn = _base_conn()
    conn.execute("INSERT INTO epis (id, company_id, unit_id, name, ca, unit_measure, manufacture_date, epi_validity_date) VALUES (1,1,10,'Capacete','CA-1','UN','2026-01-01','2026-12-31')")
    conn.execute("INSERT INTO epis (id, company_id, unit_id, name, ca, unit_measure, manufacture_date, epi_validity_date) VALUES (2,1,10,'Luva','CA-2','PAR','2026-01-01','2026-12-31')")
    conn.execute("INSERT INTO deliveries (id, employee_id, epi_id, quantity, delivery_date, next_replacement_date, signature_data, signature_name, returned_date) VALUES (1,100,1,1,'2026-01-02','2026-12-31','','','')")
    conn.execute("INSERT INTO deliveries (id, employee_id, epi_id, quantity, delivery_date, next_replacement_date, signature_data, signature_name, returned_date) VALUES (2,100,2,1,'2026-02-02','2026-12-31','','','')")
    conn.execute("INSERT INTO epi_ficha_periods (id, company_id, employee_id, unit_id, period_start, period_end, status) VALUES (10,1,100,10,'2026-01-01','2026-01-14','closed')")
    conn.execute("INSERT INTO epi_ficha_periods (id, company_id, employee_id, unit_id, period_start, period_end, status) VALUES (11,1,100,10,'2026-02-01','2026-02-14','open')")
    conn.execute("INSERT INTO epi_ficha_items (id, ficha_period_id, delivery_id, epi_id, quantity, item_signature_data, item_signature_name) VALUES (1000,10,1,1,1,'','')")
    conn.execute("INSERT INTO epi_ficha_items (id, ficha_period_id, delivery_id, epi_id, quantity, item_signature_data, item_signature_name) VALUES (1001,11,2,2,1,'','')")
    actor = {'id': 1, 'role': 'general_admin', 'company_id': 1, 'full_name': 'Admin'}

    period_html = build_ficha_epi_html_by_period(conn, 10, actor)
    current_html = build_ficha_epi_html(conn, 100, actor)

    assert 'Capacete' in period_html
    assert 'Luva' not in period_html
    assert 'PERÍODO:' in period_html
    assert 'Luva' in current_html


def test_portal_cpf_attempts_block_on_third_failure():
    conn = _base_conn()
    conn.execute(
        "INSERT INTO employee_portal_links (id, company_id, employee_id, token, qr_code_value, active, expires_at, created_by_user_id, created_at, updated_at, cpf_attempts) "
        "VALUES (1, 1, 100, 'token-1', 'qr', 1, '9999-12-31T00:00:00+00:00', 1, '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00', 0)"
    )

    for expected_attempt in (1, 2):
        ctx = get_employee_portal_context_by_token(conn, 'token-1')
        with pytest.raises(PermissionError) as exc:
            validate_portal_cpf_with_attempts(conn, ctx, '999')
        assert 'Tentativas restantes' in str(exc.value)
        row = conn.execute('SELECT cpf_attempts, active, blocked_at FROM employee_portal_links WHERE id = 1').fetchone()
        assert int(row['cpf_attempts']) == expected_attempt
        assert int(row['active']) == 1
        assert str(row['blocked_at'] or '') == ''

    ctx = get_employee_portal_context_by_token(conn, 'token-1')
    with pytest.raises(PermissionError) as exc:
        validate_portal_cpf_with_attempts(conn, ctx, '999')
    assert 'bloqueado' in str(exc.value).lower()
    row = conn.execute('SELECT cpf_attempts, active, blocked_at FROM employee_portal_links WHERE id = 1').fetchone()
    assert int(row['cpf_attempts']) == 3
    assert int(row['active']) == 0
    assert str(row['blocked_at'] or '').strip() != ''


def test_portal_cpf_success_resets_attempt_counter():
    conn = _base_conn()
    conn.execute(
        "INSERT INTO employee_portal_links (id, company_id, employee_id, token, qr_code_value, active, expires_at, created_by_user_id, created_at, updated_at, cpf_attempts, last_cpf_attempt_at) "
        "VALUES (1, 1, 100, 'token-1', 'qr', 1, '9999-12-31T00:00:00+00:00', 1, '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00', 2, '2026-01-01T01:00:00+00:00')"
    )
    ctx = get_employee_portal_context_by_token(conn, 'token-1')
    validate_portal_cpf_with_attempts(conn, ctx, '901')
    row = conn.execute('SELECT cpf_attempts FROM employee_portal_links WHERE id = 1').fetchone()
    assert int(row['cpf_attempts']) == 0


def test_employee_access_token_compatibility_without_portal_link_state():
    conn = _base_conn()
    conn.execute(
        "INSERT INTO users (id, username, password, full_name, role, company_id, active, linked_employee_id, employee_access_token, employee_access_expires_at) "
        "VALUES (1, 'emp', 'x', 'Funcionário', 'employee', 1, 1, 100, 'user-token', '9999-12-31T00:00:00+00:00')"
    )

    context = resolve_external_employee_context(conn, 'user-token', cpf_last3='901')
    assert int(context['employee_id']) == 100
    assert int(context['company_id']) == 1

    with pytest.raises(PermissionError):
        resolve_external_employee_context(conn, 'user-token', cpf_last3='999')


def test_employee_access_token_wrong_cpf_does_not_trigger_portal_block_policy():
    conn = _base_conn()
    conn.execute(
        "INSERT INTO users (id, username, password, full_name, role, company_id, active, linked_employee_id, employee_access_token, employee_access_expires_at) "
        "VALUES (1, 'emp', 'x', 'Funcionário', 'employee', 1, 1, 100, 'user-token', '9999-12-31T00:00:00+00:00')"
    )
    for _ in range(2):
        with pytest.raises(PermissionError):
            resolve_external_employee_context(conn, 'user-token', cpf_last3='999')
    # Continua compatível: token legado permanece utilizável com CPF correto.
    ctx = resolve_external_employee_context(conn, 'user-token', cpf_last3='901')
    assert int(ctx['employee_id']) == 100
    count_links = conn.execute('SELECT COUNT(*) AS c FROM employee_portal_links').fetchone()['c']
    assert int(count_links) == 0
