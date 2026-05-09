import sqlite3

import pytest

from epi_backend.purchase_workflow import resolve_purchase_transition, validate_purchase_transition_payload
from server_postgres import apply_purchase_request_workflow_action, approved_purchase_request_items_for_po


def _conn():
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.executescript(
        '''
        CREATE TABLE purchase_requests (
            id INTEGER PRIMARY KEY,
            company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE purchase_request_items (
            id INTEGER PRIMARY KEY,
            purchase_request_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL DEFAULT 1,
            unit_id INTEGER NOT NULL DEFAULT 7,
            epi_id INTEGER NOT NULL DEFAULT 501,
            epi_name TEXT NOT NULL DEFAULT 'Luva Nitrílica',
            ca TEXT NOT NULL DEFAULT '12345',
            supplier TEXT NOT NULL DEFAULT 'Fornecedor A',
            employee_name TEXT NOT NULL DEFAULT 'Colaborador A',
            quantity_requested INTEGER NOT NULL DEFAULT 1,
            quantity_approved INTEGER NOT NULL DEFAULT 0,
            unit_price REAL NOT NULL DEFAULT 10,
            total_price REAL NOT NULL DEFAULT 10,
            status TEXT NOT NULL DEFAULT 'included_in_request',
            notes TEXT NOT NULL DEFAULT '',
            rejection_reason TEXT NOT NULL DEFAULT '',
            rejection_comment TEXT NOT NULL DEFAULT '',
            approval_decided_by_user_id INTEGER,
            approval_decided_by_name TEXT NOT NULL DEFAULT '',
            approval_decided_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE epis (id INTEGER PRIMARY KEY, name TEXT NOT NULL DEFAULT 'Luva Nitrílica', ca TEXT NOT NULL DEFAULT '12345');
        CREATE TABLE units (id INTEGER PRIMARY KEY, name TEXT NOT NULL DEFAULT 'Unidade 7');
        INSERT INTO epis (id, name, ca) VALUES (501, 'Luva Nitrílica', '12345'), (502, 'Capacete', '98765'), (503, 'Bota', '45678');
        INSERT INTO units (id, name) VALUES (7, 'Unidade 7'), (8, 'Unidade 8');
        CREATE TABLE purchase_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            status_from TEXT NOT NULL DEFAULT '',
            status_to TEXT NOT NULL DEFAULT '',
            comment TEXT NOT NULL DEFAULT '',
            actor_user_id INTEGER,
            actor_name TEXT NOT NULL DEFAULT '',
            actor_role TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL DEFAULT '',
            destination TEXT NOT NULL DEFAULT '',
            ip_address TEXT NOT NULL DEFAULT '',
            session_ref TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE TABLE user_unit_links (user_id INTEGER NOT NULL, unit_id INTEGER NOT NULL);
        CREATE TABLE purchase_role_unit_links (employee_id INTEGER NOT NULL, role_type TEXT NOT NULL, unit_id INTEGER NOT NULL);
        '''
    )
    return connection


def _actor(role='approver', user_id=10, company_id=1):
    return {'id': user_id, 'role': role, 'company_id': company_id, 'full_name': f'{role} User'}


def _insert_request(connection, status='pending_approval', unit_id=7):
    connection.execute(
        'INSERT INTO purchase_requests (id, company_id, unit_id, status) VALUES (1, 1, ?, ?)',
        (unit_id, status),
    )


def _link_unit(connection, user_id=10, unit_id=7):
    connection.execute('INSERT INTO user_unit_links (user_id, unit_id) VALUES (?, ?)', (user_id, unit_id))


def test_status_machine_rejects_invalid_transition():
    with pytest.raises(ValueError):
        resolve_purchase_transition('open', 'approve')


def test_review_actions_require_reason_and_comment():
    transition = resolve_purchase_transition('pending_approval', 'return_to_buyer')
    with pytest.raises(ValueError, match='motivo'):
        validate_purchase_transition_payload(transition, reason='', comment='Corrigir preço')
    with pytest.raises(ValueError, match='observação'):
        validate_purchase_transition_payload(transition, reason='Valor acima do esperado', comment='')


def test_approver_returns_purchase_request_to_buyer_with_history():
    connection = _conn()
    _insert_request(connection)
    _link_unit(connection)

    result = apply_purchase_request_workflow_action(
        connection,
        _actor('approver'),
        1,
        {'action': 'return_to_buyer', 'reason': 'Cotação incompleta', 'comment': 'Falta fornecedor alternativo.'},
    )

    assert result['status'] == 'waiting_buyer_correction'
    assert connection.execute('SELECT status FROM purchase_requests WHERE id = 1').fetchone()['status'] == 'waiting_buyer_correction'
    event = connection.execute('SELECT * FROM purchase_events WHERE entity_id = 1').fetchone()
    assert event['action'] == 'return_to_buyer'
    assert event['destination'] == 'buyer'
    assert event['reason'] == 'Cotação incompleta'
    assert event['actor_role'] == 'approver'


def test_approver_returns_purchase_request_to_requester_with_history():
    connection = _conn()
    _insert_request(connection)
    _link_unit(connection)

    result = apply_purchase_request_workflow_action(
        connection,
        _actor('approver'),
        1,
        {
            'action': 'return_to_requester',
            'reason': 'Revisar quantidade',
            'comment': 'Confirmar a quantidade solicitada.',
            'requested_changes': ['Revisar quantidade'],
        },
    )

    assert result['status'] == 'waiting_requester_correction'
    event = connection.execute('SELECT * FROM purchase_events WHERE entity_id = 1').fetchone()
    assert event['destination'] == 'requester'
    assert 'Revisar quantidade' in event['comment']


def test_buyer_returns_purchase_request_to_requester():
    connection = _conn()
    _insert_request(connection, status='quoted')
    _link_unit(connection, user_id=11)

    result = apply_purchase_request_workflow_action(
        connection,
        _actor('buyer', user_id=11),
        1,
        {'action': 'buyer_return_to_requester', 'reason': 'Acrescentar novos itens', 'comment': 'Adicionar EPI complementar.'},
    )

    assert result['status'] == 'waiting_requester_correction'
    event = connection.execute('SELECT * FROM purchase_events WHERE entity_id = 1').fetchone()
    assert event['action'] == 'buyer_return_to_requester'
    assert event['destination'] == 'requester'


def test_buyer_can_resubmit_after_approver_returned_quote_for_correction():
    connection = _conn()
    _insert_request(connection, status='waiting_buyer_correction')
    _link_unit(connection, user_id=11)

    result = apply_purchase_request_workflow_action(
        connection,
        _actor('buyer', user_id=11),
        1,
        {'action': 'buyer_resubmit', 'comment': 'Cotação corrigida.'},
    )

    assert result['status'] == 'pending_approval'
    event = connection.execute('SELECT * FROM purchase_events WHERE entity_id = 1').fetchone()
    assert event['action'] == 'buyer_resubmit'
    assert event['destination'] == 'approver'


def test_requester_resubmit_returns_to_approval_when_review_origin_was_approval():
    connection = _conn()
    _insert_request(connection, status='waiting_requester_correction')
    connection.execute(
        "INSERT INTO purchase_events (company_id, entity_type, entity_id, action, status_from, status_to, actor_name, destination, created_at) VALUES (1, 'purchase_request', 1, 'return_to_requester', 'pending_approval', 'waiting_requester_correction', 'Approver', 'requester', '2026-05-08T00:00:00')"
    )

    result = apply_purchase_request_workflow_action(
        connection,
        _actor('admin', user_id=12),
        1,
        {'action': 'requester_resubmit', 'comment': 'Itens revisados.'},
    )

    assert result['status'] == 'pending_approval'


def test_requester_resubmit_returns_to_buyer_when_review_origin_was_quote():
    connection = _conn()
    _insert_request(connection, status='waiting_requester_correction')
    connection.execute(
        "INSERT INTO purchase_events (company_id, entity_type, entity_id, action, status_from, status_to, actor_name, destination, created_at) VALUES (1, 'purchase_request', 1, 'buyer_return_to_requester', 'quoted', 'waiting_requester_correction', 'Buyer', 'requester', '2026-05-08T00:00:00')"
    )

    result = apply_purchase_request_workflow_action(
        connection,
        _actor('admin', user_id=12),
        1,
        {'action': 'requester_resubmit', 'comment': 'Itens revisados.'},
    )

    assert result['status'] == 'sent_to_buyer'



def test_local_admin_requester_cannot_approve_purchase_request():
    connection = _conn()
    _insert_request(connection)
    _link_unit(connection, user_id=12)

    with pytest.raises(PermissionError, match='Perfil sem permissão'):
        apply_purchase_request_workflow_action(
            connection,
            _actor('admin', user_id=12),
            1,
            {'action': 'approve'},
        )


def test_approver_can_partially_approve_items_with_history():
    connection = _conn()
    _insert_request(connection)
    _link_unit(connection)
    connection.execute("INSERT INTO purchase_request_items (id, purchase_request_id, quantity_requested) VALUES (101, 1, 2)")
    connection.execute("INSERT INTO purchase_request_items (id, purchase_request_id, quantity_requested) VALUES (102, 1, 1)")

    result = apply_purchase_request_workflow_action(
        connection,
        _actor('approver'),
        1,
        {'action': 'approve', 'approved_item_ids': [101], 'rejected_item_ids': [102], 'reason': 'Item não necessário', 'comment': 'Item sem necessidade.'},
    )

    assert result['status'] == 'partially_approved'
    approved = connection.execute('SELECT status, quantity_approved FROM purchase_request_items WHERE id = 101').fetchone()
    rejected = connection.execute('SELECT status, quantity_approved, notes FROM purchase_request_items WHERE id = 102').fetchone()
    assert dict(approved) == {'status': 'approved', 'quantity_approved': 2}
    assert rejected['status'] == 'rejected'
    assert rejected['quantity_approved'] == 0
    assert 'Item sem necessidade' in rejected['notes']
    event = connection.execute('SELECT * FROM purchase_events WHERE entity_id = 1').fetchone()
    assert event['status_to'] == 'partially_approved'
    assert 'Decisão por item' in event['comment']

def test_approver_cannot_act_outside_linked_unit():
    connection = _conn()
    _insert_request(connection, unit_id=8)
    _link_unit(connection, unit_id=7)

    with pytest.raises(PermissionError, match='unidades de compras'):
        apply_purchase_request_workflow_action(
            connection,
            _actor('approver'),
            1,
            {'action': 'approve'},
        )


def test_user_without_purchase_permission_cannot_execute_workflow_action():
    connection = _conn()
    _insert_request(connection)

    with pytest.raises(PermissionError):
        apply_purchase_request_workflow_action(
            connection,
            _actor('user'),
            1,
            {'action': 'approve'},
        )


def _insert_item(connection, item_id, *, epi_id=501, qty=1, unit_price=10, unit_id=7, status='included_in_request'):
    connection.execute(
        'INSERT INTO purchase_request_items (id, purchase_request_id, company_id, unit_id, epi_id, epi_name, ca, supplier, employee_name, quantity_requested, unit_price, total_price, status) VALUES (?, 1, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (item_id, unit_id, epi_id, f'EPI {epi_id}', f'CA-{epi_id}', 'Fornecedor A', f'Colab {item_id}', qty, unit_price, qty * unit_price, status),
    )


def test_approver_approves_all_items_and_recalculates_totals():
    connection = _conn()
    _insert_request(connection)
    _link_unit(connection)
    _insert_item(connection, 101, qty=2, unit_price=15)
    _insert_item(connection, 102, epi_id=502, qty=1, unit_price=20)

    result = apply_purchase_request_workflow_action(
        connection,
        _actor('approver'),
        1,
        {'action': 'approve', 'decisions': [{'item_id': 101, 'approved': True}, {'item_id': 102, 'approved': True}]},
    )

    assert result['status'] == 'approved'
    assert result['totals']['approved_total'] == 50
    assert result['totals']['rejected_total'] == 0
    assert result['totals']['approved_quantity'] == 3
    statuses = [row['status'] for row in connection.execute('SELECT status FROM purchase_request_items ORDER BY id').fetchall()]
    assert statuses == ['approved', 'approved']


def test_approver_partially_approves_items_with_per_item_reason_history_and_totals():
    connection = _conn()
    _insert_request(connection)
    _link_unit(connection)
    _insert_item(connection, 101, qty=2, unit_price=15)
    _insert_item(connection, 102, epi_id=502, qty=1, unit_price=20)

    result = apply_purchase_request_workflow_action(
        connection,
        _actor('approver'),
        1,
        {
            'action': 'approve',
            'decisions': [
                {'item_id': 101, 'approved': True},
                {'item_id': 102, 'approved': False, 'rejection_reason': 'Valor acima do esperado', 'rejection_comment': 'Acima do orçamento.'},
            ],
        },
    )

    assert result['status'] == 'partially_approved'
    assert result['totals']['approved_total'] == 30
    assert result['totals']['rejected_total'] == 20
    rejected = connection.execute('SELECT status, rejection_reason, rejection_comment, quantity_approved FROM purchase_request_items WHERE id = 102').fetchone()
    assert rejected['status'] == 'rejected'
    assert rejected['rejection_reason'] == 'Valor acima do esperado'
    assert rejected['rejection_comment'] == 'Acima do orçamento.'
    assert rejected['quantity_approved'] == 0
    item_event = connection.execute("SELECT * FROM purchase_events WHERE entity_type = 'purchase_request_item' AND entity_id = 102").fetchone()
    assert item_event['status_to'] == 'rejected'
    assert item_event['reason'] == 'Valor acima do esperado'
    assert 'Total item: 20.00' in item_event['comment']


def test_approver_rejects_all_items_with_required_reasons():
    connection = _conn()
    _insert_request(connection)
    _link_unit(connection)
    _insert_item(connection, 101)
    _insert_item(connection, 102, epi_id=502)

    result = apply_purchase_request_workflow_action(
        connection,
        _actor('approver'),
        1,
        {
            'action': 'approve',
            'decisions': [
                {'item_id': 101, 'approved': False, 'rejection_reason': 'Item não necessário'},
                {'item_id': 102, 'approved': False, 'rejection_reason': 'Fornecedor inadequado'},
            ],
        },
    )

    assert result['status'] == 'rejected'
    assert connection.execute('SELECT status FROM purchase_requests WHERE id = 1').fetchone()['status'] == 'rejected'
    assert result['totals']['approved_count'] == 0
    assert result['totals']['rejected_count'] == 2


def test_rejected_item_without_reason_fails():
    connection = _conn()
    _insert_request(connection)
    _link_unit(connection)
    _insert_item(connection, 101)

    with pytest.raises(ValueError, match='motivo'):
        apply_purchase_request_workflow_action(
            connection,
            _actor('approver'),
            1,
            {'action': 'approve', 'decisions': [{'item_id': 101, 'approved': False}]},
        )


def test_rejected_item_other_reason_requires_comment():
    connection = _conn()
    _insert_request(connection)
    _link_unit(connection)
    _insert_item(connection, 101)

    with pytest.raises(ValueError, match='Outro'):
        apply_purchase_request_workflow_action(
            connection,
            _actor('approver'),
            1,
            {'action': 'approve', 'decisions': [{'item_id': 101, 'approved': False, 'rejection_reason': 'Outro'}]},
        )


def test_legacy_partial_payload_requires_all_items_decided():
    connection = _conn()
    _insert_request(connection)
    _link_unit(connection)
    _insert_item(connection, 101)
    _insert_item(connection, 102)

    with pytest.raises(ValueError, match='todos os itens'):
        apply_purchase_request_workflow_action(
            connection,
            _actor('approver'),
            1,
            {'action': 'approve', 'approved_item_ids': [101]},
        )


def test_po_generation_accepts_only_approved_items_from_partially_approved_request():
    connection = _conn()
    _insert_request(connection, status='partially_approved')
    _insert_item(connection, 101, status='approved')
    _insert_item(connection, 102, epi_id=502, status='rejected')

    approved = approved_purchase_request_items_for_po(
        connection,
        1,
        [{'purchase_request_item_id': 101, 'epi_id': 501, 'quantity': 1, 'unit_price': 10}],
    )

    assert sorted(approved) == [101]
    with pytest.raises(ValueError, match='Somente itens aprovados'):
        approved_purchase_request_items_for_po(
            connection,
            1,
            [{'purchase_request_item_id': 102, 'epi_id': 502, 'quantity': 1, 'unit_price': 10}],
        )
