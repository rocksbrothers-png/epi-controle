import sqlite3

import pytest

from epi_backend.purchase_workflow import resolve_purchase_transition, validate_purchase_transition_payload
from server_postgres import apply_purchase_request_workflow_action


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
