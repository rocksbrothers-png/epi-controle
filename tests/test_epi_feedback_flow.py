"""Tests for the EPI feedback (Avaliações e Sugestões) workflow."""

import sqlite3
import pytest

from modules.feedback.service import (
    apply_feedback_triage,
    apply_feedback_hseq_review,
    apply_feedback_forward_admin,
    apply_feedback_admin_decision,
    apply_feedback_close,
    fetch_feedback_detail,
    fetch_feedbacks_for_manager,
)
from core.permissions import (
    PERM_EPI_FEEDBACK_VIEW,
    PERM_EPI_FEEDBACK_TRIAGE,
    PERM_EPI_FEEDBACK_HSEQ_REVIEW,
    PERM_EPI_FEEDBACK_ADMIN_APPROVE,
    PERM_EPI_FEEDBACK_CLOSE,
    PERMISSIONS,
)


def _conn():
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.executescript(
        '''
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT NOT NULL DEFAULT 'Empresa A');
        CREATE TABLE units (id INTEGER PRIMARY KEY, name TEXT NOT NULL DEFAULT 'Unidade 1');
        CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT NOT NULL DEFAULT 'Colaborador A', unit_id INTEGER NOT NULL DEFAULT 1, company_id INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE users (id INTEGER PRIMARY KEY, full_name TEXT NOT NULL DEFAULT 'User', role TEXT NOT NULL DEFAULT 'user', company_id INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE epis (id INTEGER PRIMARY KEY, name TEXT NOT NULL DEFAULT 'EPI A', company_id INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE epi_feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL DEFAULT 1,
            unit_id INTEGER NOT NULL DEFAULT 1,
            employee_id INTEGER NOT NULL DEFAULT 1,
            epi_id INTEGER,
            comfort_rating INTEGER NOT NULL DEFAULT 0,
            quality_rating INTEGER NOT NULL DEFAULT 0,
            adequacy_rating INTEGER NOT NULL DEFAULT 0,
            performance_rating INTEGER NOT NULL DEFAULT 0,
            comments TEXT NOT NULL DEFAULT '',
            improvement_suggestion TEXT NOT NULL DEFAULT '',
            suggested_new_epi_name TEXT NOT NULL DEFAULT '',
            suggested_new_epi_notes TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pendente',
            request_token TEXT NOT NULL DEFAULT '',
            reviewer_user_id INTEGER,
            reviewer_name TEXT NOT NULL DEFAULT '',
            reviewed_at TEXT NOT NULL DEFAULT '',
            type TEXT NOT NULL DEFAULT 'avaliacao',
            category TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            priority TEXT NOT NULL DEFAULT 'normal',
            created_by_user_id INTEGER,
            assigned_epi_manager_id INTEGER,
            hseq_required INTEGER NOT NULL DEFAULT 0,
            hseq_user_id INTEGER,
            hseq_opinion TEXT NOT NULL DEFAULT '',
            hseq_analyzed_at TEXT NOT NULL DEFAULT '',
            admin_decision TEXT NOT NULL DEFAULT '',
            admin_decision_by_user_id INTEGER,
            admin_decision_by_name TEXT NOT NULL DEFAULT '',
            admin_decision_at TEXT NOT NULL DEFAULT '',
            final_justification TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT '2026-05-01T00:00:00',
            updated_at TEXT NOT NULL DEFAULT '2026-05-01T00:00:00'
        );
        CREATE TABLE epi_feedback_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feedback_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            actor_user_id INTEGER,
            actor_name TEXT NOT NULL DEFAULT '',
            actor_role TEXT NOT NULL DEFAULT '',
            action TEXT NOT NULL DEFAULT '',
            previous_status TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT '2026-05-01T00:00:00'
        );
        INSERT INTO companies (id, name) VALUES (1, 'Empresa A');
        INSERT INTO units (id, name) VALUES (1, 'Unidade 1');
        INSERT INTO employees (id, name, unit_id, company_id) VALUES (1, 'Colaborador A', 1, 1);
        INSERT INTO epis (id, name, company_id) VALUES (10, 'EPI A', 1);
        '''
    )
    return connection


def _actor(role='user', user_id=10, company_id=1):
    return {'id': user_id, 'role': role, 'company_id': company_id, 'full_name': f'{role} User'}


def _insert_feedback(connection, status='pendente', fb_type='avaliacao'):
    cursor = connection.execute(
        "INSERT INTO epi_feedbacks (company_id, unit_id, employee_id, epi_id, status, type, created_at, updated_at) "
        "VALUES (1, 1, 1, 10, ?, ?, '2026-05-01T00:00:00', '2026-05-01T00:00:00')",
        (status, fb_type)
    )
    return cursor.lastrowid


# ── Permission checks ─────────────────────────────────────────────────────────

def test_gestor_de_epi_has_triage_permission():
    assert PERM_EPI_FEEDBACK_TRIAGE in PERMISSIONS.get('user', set())


def test_gestor_de_epi_has_hseq_review_permission():
    assert PERM_EPI_FEEDBACK_HSEQ_REVIEW in PERMISSIONS.get('user', set())


def test_general_admin_has_admin_approve_permission():
    assert PERM_EPI_FEEDBACK_ADMIN_APPROVE in PERMISSIONS.get('general_admin', set())


def test_registry_admin_has_admin_approve_permission():
    assert PERM_EPI_FEEDBACK_ADMIN_APPROVE in PERMISSIONS.get('registry_admin', set())


def test_user_role_has_view_permission():
    assert PERM_EPI_FEEDBACK_VIEW in PERMISSIONS.get('user', set())


def test_employee_has_no_feedback_view():
    assert PERM_EPI_FEEDBACK_VIEW not in PERMISSIONS.get('employee', set())


# ── Triage ────────────────────────────────────────────────────────────────────

def test_gestor_can_triage_feedback():
    connection = _conn()
    fb_id = _insert_feedback(connection)
    actor = _actor('user')
    result = apply_feedback_triage(connection, actor, fb_id, {
        'type': 'reclamacao',
        'category': 'Qualidade',
        'priority': 'alta',
        'hseq_required': False,
        'notes': 'Verificar urgência',
    })
    assert result['ok'] is True
    assert result['status'] == 'em_analise_gestor'
    row = connection.execute('SELECT * FROM epi_feedbacks WHERE id = ?', (fb_id,)).fetchone()
    assert row['type'] == 'reclamacao'
    assert row['priority'] == 'alta'
    assert row['status'] == 'em_analise_gestor'


def test_triage_with_hseq_required_sets_status_aguardando_hseq():
    connection = _conn()
    fb_id = _insert_feedback(connection)
    actor = _actor('user')
    result = apply_feedback_triage(connection, actor, fb_id, {
        'type': 'sugestao',
        'priority': 'normal',
        'hseq_required': True,
    })
    assert result['status'] == 'aguardando_hseq'
    row = connection.execute('SELECT hseq_required, status FROM epi_feedbacks WHERE id = ?', (fb_id,)).fetchone()
    assert row['hseq_required'] == 1
    assert row['status'] == 'aguardando_hseq'


def test_triage_records_history():
    connection = _conn()
    fb_id = _insert_feedback(connection)
    actor = _actor('user')
    apply_feedback_triage(connection, actor, fb_id, {'type': 'elogio', 'priority': 'baixa'})
    history = connection.execute('SELECT * FROM epi_feedback_history WHERE feedback_id = ?', (fb_id,)).fetchall()
    assert len(history) == 1
    h = dict(history[0])
    assert h['action'] == 'triage'
    assert h['previous_status'] == 'pendente'
    assert h['status'] == 'em_analise_gestor'


def test_triage_invalid_priority_fails():
    connection = _conn()
    fb_id = _insert_feedback(connection)
    actor = _actor('user')
    with pytest.raises(ValueError, match='Prioridade'):
        apply_feedback_triage(connection, actor, fb_id, {'type': 'avaliacao', 'priority': 'maxima'})


def test_user_without_triage_permission_cannot_triage():
    connection = _conn()
    fb_id = _insert_feedback(connection)
    actor = _actor('buyer')
    with pytest.raises(PermissionError):
        apply_feedback_triage(connection, actor, fb_id, {'type': 'avaliacao', 'priority': 'normal'})


# ── HSEQ Review ───────────────────────────────────────────────────────────────

def test_hseq_can_register_opinion():
    connection = _conn()
    fb_id = _insert_feedback(connection, status='aguardando_hseq')
    actor = _actor('user')
    result = apply_feedback_hseq_review(connection, actor, fb_id, {
        'hseq_opinion': 'EPI compatível. Substituição recomendada em 6 meses.',
        'notes': 'Verificado no campo.',
    })
    assert result['ok'] is True
    assert result['status'] == 'analise_hseq_concluida'
    row = connection.execute('SELECT hseq_opinion, status FROM epi_feedbacks WHERE id = ?', (fb_id,)).fetchone()
    assert 'Substituição' in row['hseq_opinion']
    assert row['status'] == 'analise_hseq_concluida'


def test_hseq_opinion_required():
    connection = _conn()
    fb_id = _insert_feedback(connection, status='aguardando_hseq')
    actor = _actor('user')
    with pytest.raises(ValueError, match='Parecer HSEQ'):
        apply_feedback_hseq_review(connection, actor, fb_id, {'hseq_opinion': ''})


def test_actor_without_hseq_permission_cannot_review():
    connection = _conn()
    fb_id = _insert_feedback(connection, status='aguardando_hseq')
    actor = _actor('buyer')
    with pytest.raises(PermissionError):
        apply_feedback_hseq_review(connection, actor, fb_id, {'hseq_opinion': 'OK'})


# ── Forward to Admin ──────────────────────────────────────────────────────────

def test_gestor_can_forward_to_admin():
    connection = _conn()
    fb_id = _insert_feedback(connection, status='em_analise_gestor')
    actor = _actor('user')
    result = apply_feedback_forward_admin(connection, actor, fb_id, {'notes': 'Para aprovação.'})
    assert result['ok'] is True
    assert result['status'] == 'aguardando_aprovacao_admin'


# ── Admin Decision ────────────────────────────────────────────────────────────

def test_admin_can_approve_suggestion():
    connection = _conn()
    fb_id = _insert_feedback(connection, status='aguardando_aprovacao_admin', fb_type='sugestao')
    actor = _actor('general_admin')
    result = apply_feedback_admin_decision(connection, actor, fb_id, {
        'decision': 'aprovar_sugestao',
        'justification': 'Sugestão válida e alinhada à política de segurança.',
    })
    assert result['ok'] is True
    assert result['status'] == 'aprovado'
    assert result['decision'] == 'aprovar_sugestao'
    row = connection.execute('SELECT admin_decision, status, final_justification FROM epi_feedbacks WHERE id = ?', (fb_id,)).fetchone()
    assert row['admin_decision'] == 'aprovar_sugestao'
    assert row['status'] == 'aprovado'
    assert 'política de segurança' in row['final_justification']


def test_admin_can_reject_suggestion():
    connection = _conn()
    fb_id = _insert_feedback(connection, status='aguardando_aprovacao_admin', fb_type='sugestao')
    actor = _actor('registry_admin')
    result = apply_feedback_admin_decision(connection, actor, fb_id, {
        'decision': 'reprovar_sugestao',
        'justification': 'Fora do escopo do contrato atual.',
    })
    assert result['status'] == 'reprovado'


def test_admin_decision_requires_justification():
    connection = _conn()
    fb_id = _insert_feedback(connection, status='aguardando_aprovacao_admin', fb_type='sugestao')
    actor = _actor('general_admin')
    with pytest.raises(ValueError, match='Justificativa'):
        apply_feedback_admin_decision(connection, actor, fb_id, {
            'decision': 'aprovar_sugestao',
            'justification': '',
        })


def test_admin_decision_requires_valid_decision():
    connection = _conn()
    fb_id = _insert_feedback(connection, status='aguardando_aprovacao_admin', fb_type='sugestao')
    actor = _actor('general_admin')
    with pytest.raises(ValueError, match='decisão'):
        apply_feedback_admin_decision(connection, actor, fb_id, {
            'decision': '',
            'justification': 'Justificativa',
        })


def test_admin_can_open_corrective_action_for_reclamacao():
    connection = _conn()
    fb_id = _insert_feedback(connection, status='aguardando_aprovacao_admin', fb_type='reclamacao')
    actor = _actor('general_admin')
    result = apply_feedback_admin_decision(connection, actor, fb_id, {
        'decision': 'abrir_acao_corretiva',
        'justification': 'Reclamação recorrente — ação necessária.',
    })
    assert result['status'] == 'acao_corretiva_aberta'


def test_admin_decision_records_history():
    connection = _conn()
    fb_id = _insert_feedback(connection, status='aguardando_aprovacao_admin', fb_type='sugestao')
    actor = _actor('general_admin')
    apply_feedback_admin_decision(connection, actor, fb_id, {
        'decision': 'aprovar_sugestao',
        'justification': 'Sugestão pertinente.',
    })
    history = connection.execute(
        "SELECT * FROM epi_feedback_history WHERE feedback_id = ? ORDER BY id DESC LIMIT 1",
        (fb_id,)
    ).fetchone()
    assert history is not None
    assert dict(history)['action'] == 'aprovar_sugestao'
    assert 'pertinente' in dict(history)['reason']


def test_user_without_admin_approve_cannot_decide():
    connection = _conn()
    fb_id = _insert_feedback(connection, status='aguardando_aprovacao_admin', fb_type='sugestao')
    actor = _actor('admin')
    with pytest.raises(PermissionError):
        apply_feedback_admin_decision(connection, actor, fb_id, {
            'decision': 'aprovar_sugestao',
            'justification': 'Decisão não autorizada.',
        })


# ── Close ─────────────────────────────────────────────────────────────────────

def test_admin_can_close_feedback():
    connection = _conn()
    fb_id = _insert_feedback(connection, status='em_analise_gestor')
    actor = _actor('general_admin')
    result = apply_feedback_close(connection, actor, fb_id, {'notes': 'Encerrado após verificação.'})
    assert result['ok'] is True
    assert result['status'] == 'encerrado'
    row = connection.execute('SELECT status FROM epi_feedbacks WHERE id = ?', (fb_id,)).fetchone()
    assert row['status'] == 'encerrado'


def test_user_without_close_permission_cannot_close():
    connection = _conn()
    fb_id = _insert_feedback(connection, status='em_analise_gestor')
    actor = _actor('buyer')
    with pytest.raises(PermissionError):
        apply_feedback_close(connection, actor, fb_id, {})


# ── List and Detail ───────────────────────────────────────────────────────────

def test_fetch_feedbacks_for_manager_scopes_by_company():
    connection = _conn()
    _insert_feedback(connection)
    _insert_feedback(connection)
    actor = _actor('user', company_id=1)
    items = fetch_feedbacks_for_manager(connection, actor)
    assert len(items) == 2
    for item in items:
        assert item['company_id'] == 1


def test_fetch_feedback_detail_includes_history():
    connection = _conn()
    fb_id = _insert_feedback(connection)
    actor = _actor('user')
    apply_feedback_triage(connection, actor, fb_id, {'type': 'avaliacao', 'priority': 'normal'})
    detail = fetch_feedback_detail(connection, fb_id, actor)
    assert 'history' in detail
    assert len(detail['history']) == 1


def test_fetch_feedback_detail_wrong_company_raises():
    connection = _conn()
    fb_id = _insert_feedback(connection)
    actor = {'id': 99, 'role': 'user', 'company_id': 2, 'full_name': 'Other Company User'}
    with pytest.raises(PermissionError):
        fetch_feedback_detail(connection, fb_id, actor)
