"""Testes do fluxo de Avaliação e Homologação de EPI em Teste.

Cobre: sugestão → triagem → cadastro provisório → análise técnica → plano →
participantes → distribuição controlada → avaliações → ocorrências (com
suspensão) → consolidação → decisão formal → homologação transacional com
escopos GLOBAL / JOINT_VENTURE / UNIT e a regra Única x Única (UNIQUE),
além de isolamento entre empresas, bloqueio pós-reprovação e permissões.
"""

import sqlite3

import pytest

from epi_backend.ppe_test_schema import ensure_ppe_test_tables
from epi_backend.epi_scope import is_epi_visible_for_unit
from core.permissions import (
    PERM_PPE_TEST_DECIDE,
    PERM_PPE_TEST_HOMOLOGATE,
    PERM_PPE_TEST_MANAGE,
    PERM_PPE_TEST_SUGGEST,
    PERM_PPE_TEST_TECH_REVIEW,
    PERM_PPE_TEST_TRIAGE,
    PERM_PPE_TEST_VIEW,
    PERMISSIONS,
)
from modules.ppe_tests import service


def _conn():
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.executescript(
        '''
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL,
            name TEXT, status TEXT DEFAULT 'active');
        CREATE TABLE users (id INTEGER PRIMARY KEY, full_name TEXT, role TEXT,
            company_id INTEGER);
        CREATE TABLE employees (id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL,
            unit_id INTEGER, name TEXT, role_name TEXT DEFAULT 'Operador',
            employee_id_code TEXT DEFAULT 'M-1', sector TEXT DEFAULT 'Manutenção');
        CREATE TABLE epis (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            unit_id INTEGER, name TEXT, purchase_code TEXT DEFAULT '', ca TEXT DEFAULT '',
            sector TEXT DEFAULT '', stock INTEGER DEFAULT 0, unit_measure TEXT DEFAULT 'un',
            ca_expiry TEXT DEFAULT '', epi_validity_date TEXT DEFAULT '',
            manufacture_date TEXT DEFAULT '', validity_days INTEGER DEFAULT 0,
            manufacturer TEXT DEFAULT '', model_reference TEXT DEFAULT '',
            supplier_company TEXT DEFAULT '', manufacturer_recommendations TEXT DEFAULT '',
            epi_photo_data TEXT, size TEXT, active_joinventure TEXT, active INTEGER DEFAULT 1);
        CREATE TABLE epi_feedbacks (id INTEGER PRIMARY KEY, company_id INTEGER,
            unit_id INTEGER, employee_id INTEGER, epi_id INTEGER, comments TEXT DEFAULT '',
            suggested_new_epi_name TEXT DEFAULT '', suggested_new_epi_notes TEXT DEFAULT '',
            improvement_suggestion TEXT DEFAULT '', category TEXT DEFAULT '',
            status TEXT DEFAULT 'pendente', admin_decision TEXT DEFAULT '',
            admin_decision_by_user_id INTEGER, admin_decision_by_name TEXT DEFAULT '',
            admin_decision_at TEXT DEFAULT '', final_justification TEXT DEFAULT '',
            employee_portal_status TEXT DEFAULT '', employee_portal_message TEXT DEFAULT '',
            updated_at TEXT DEFAULT '');
        CREATE TABLE epi_feedback_history (id INTEGER PRIMARY KEY AUTOINCREMENT,
            feedback_id INTEGER, company_id INTEGER, status TEXT DEFAULT '',
            notes TEXT DEFAULT '', actor_user_id INTEGER, actor_name TEXT DEFAULT '',
            actor_role TEXT DEFAULT '', action TEXT DEFAULT '', previous_status TEXT DEFAULT '',
            reason TEXT DEFAULT '', created_at TEXT DEFAULT '');
        CREATE TABLE unit_joint_venture_periods (id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER, unit_id INTEGER, joint_venture_name TEXT,
            started_at TEXT, ended_at TEXT, created_by TEXT DEFAULT '',
            created_at TEXT DEFAULT '');
        '''
    )
    ensure_ppe_test_tables(connection)
    connection.executescript(
        '''
        INSERT INTO companies VALUES (1, 'Empresa A'), (2, 'Empresa B');
        INSERT INTO units (id, company_id, name) VALUES
            (1, 1, 'Unidade Macaé'), (2, 1, 'Unidade Rio'), (3, 2, 'Unidade Solo');
        INSERT INTO users VALUES
            (10, 'Admin Geral A', 'general_admin', 1),
            (20, 'Admin Geral B', 'general_admin', 2);
        INSERT INTO employees (id, company_id, unit_id, name) VALUES
            (100, 1, 1, 'Colab 1'), (101, 1, 1, 'Colab 2'), (200, 2, 3, 'Colab B');
        '''
    )
    return connection


GA = {'id': 10, 'full_name': 'Admin Geral A', 'role': 'general_admin', 'company_id': 1}
GB = {'id': 20, 'full_name': 'Admin Geral B', 'role': 'general_admin', 'company_id': 2}
LOCAL = {'id': 11, 'full_name': 'Admin Local', 'role': 'user', 'company_id': 1}


def _candidate_ready_for_test(connection, actor=GA, name='Luva Teste', ca='12345'):
    cid = service.create_candidate(connection, actor, {'name': name, 'ca': ca})['id']
    service.apply_technical_review(connection, actor, cid, {'result': 'aprovar_para_teste'})
    service.save_test_plan(connection, actor, cid, {
        'start_date': '2026-07-01', 'end_date': '2026-08-30',
        'min_participants': 1, 'min_response_rate': 50,
    })
    return cid


def _run_until_decision(connection, cid, actor=GA, employee_id=100):
    pid = service.add_participant(connection, actor, cid, {'employee_id': employee_id})['id']
    service.register_distribution(connection, actor, cid, {'movement_type': 'recebimento', 'quantity': 10})
    service.start_test(connection, actor, cid, {})
    service.register_distribution(connection, actor, cid, {
        'movement_type': 'entrega', 'quantity': 1, 'participant_id': pid})
    service.register_evaluation(connection, actor, cid, {
        'participant_id': pid, 'stage': 'final',
        'ratings': {'satisfacao_geral': 5}, 'recommend': True})
    service.complete_test(connection, actor, cid, {})
    return pid


# ── Sugestão e triagem ────────────────────────────────────────────────────────

def test_suggestion_requires_core_fields():
    connection = _conn()
    with pytest.raises(ValueError):
        service.create_suggestion(connection, GA, {'suggested_name': '', 'reason': 'x'})
    with pytest.raises(ValueError):
        service.create_suggestion(connection, GA, {'suggested_name': 'Luva', 'reason': ''})


def test_suggestion_triage_rejection_requires_justification():
    connection = _conn()
    sid = service.create_suggestion(connection, GA, {
        'source_type': 'colaborador', 'suggested_name': 'Luva Nova',
        'requester_name': 'Colab 1', 'reason': 'Luva atual rasga'})['id']
    with pytest.raises(ValueError):
        service.apply_suggestion_triage(connection, GA, sid, {'result': 'rejeitado', 'notes': ''})
    result = service.apply_suggestion_triage(connection, GA, sid, {
        'result': 'rejeitado', 'notes': 'Sem CA válido'})
    assert result['status'] == 'rejeitada'


def test_candidate_requires_triaged_suggestion():
    connection = _conn()
    sid = service.create_suggestion(connection, GA, {
        'source_type': 'empresa', 'suggested_name': 'Capacete X',
        'requester_name': 'RH', 'reason': 'Modernização'})['id']
    with pytest.raises(ValueError):
        service.create_candidate(connection, GA, {'suggestion_id': sid, 'name': 'Capacete X'})
    service.apply_suggestion_triage(connection, GA, sid, {'result': 'aprovado_analise_tecnica'})
    cid = service.create_candidate(connection, GA, {'suggestion_id': sid, 'name': 'Capacete X'})['id']
    suggestion = service.fetch_suggestion_detail(connection, GA, sid)
    assert suggestion['status'] == 'convertida'
    assert int(suggestion['candidate_id']) == cid
    # A mesma sugestão não pode gerar dois cadastros provisórios
    with pytest.raises(ValueError):
        service.create_candidate(connection, GA, {'suggestion_id': sid, 'name': 'Capacete X2'})


def test_accept_suggestion_uses_single_flow_no_direct_epi():
    """Fluxo único: aceitar sugestão do portal NÃO cria EPI direto no banco
    oficial — encaminha ao fluxo de EPI em teste até a homologação."""
    from modules.feedback.service import apply_accept_suggestion_as_epi
    connection = _conn()
    connection.execute(
        "INSERT INTO epi_feedbacks (id, company_id, unit_id, employee_id, suggested_new_epi_name, "
        "suggested_new_epi_notes) VALUES (901, 1, 1, 100, 'Luva Anticorte Y', 'Mais resistente')")
    result = apply_accept_suggestion_as_epi(connection, GA, 901, {'notes': 'Aceita para teste'})
    assert result['new_epi_id'] is None
    assert result['test_suggestion_id']
    # Nenhum EPI criado direto no banco oficial
    assert connection.execute('SELECT COUNT(*) FROM epis').fetchone()[0] == 0
    row = connection.execute(
        'SELECT * FROM ppe_test_suggestions WHERE id = ?', (result['test_suggestion_id'],)).fetchone()
    assert row['source_feedback_id'] == 901
    assert row['suggested_name'] == 'Luva Anticorte Y'
    fb = connection.execute('SELECT * FROM epi_feedbacks WHERE id = 901').fetchone()
    assert fb['status'] == 'aprovado'
    assert 'fluxo de teste' in fb['employee_portal_message']


def test_suggestion_promoted_from_portal_feedback():
    connection = _conn()
    connection.execute(
        "INSERT INTO epi_feedbacks (id, company_id, unit_id, employee_id, suggested_new_epi_name, "
        "suggested_new_epi_notes) VALUES (900, 1, 1, 100, 'Bota Impermeável', 'Melhor para maré')")
    result = service.create_suggestion_from_feedback(connection, GA, 900, {})
    assert result['ok']
    with pytest.raises(ValueError):
        service.create_suggestion_from_feedback(connection, GA, 900, {})


# ── Cadastro provisório fora do banco oficial ─────────────────────────────────

def test_candidate_not_in_official_epis_table():
    connection = _conn()
    cid = _candidate_ready_for_test(connection)
    assert connection.execute('SELECT COUNT(*) FROM epis').fetchone()[0] == 0
    candidate = service.fetch_candidate_detail(connection, GA, cid)
    assert candidate['status'] == 'aprovado_para_teste'


# ── Ciclo de vida do teste ────────────────────────────────────────────────────

def test_start_requires_plan_and_participants():
    connection = _conn()
    cid = service.create_candidate(connection, GA, {'name': 'Luva Y'})['id']
    service.apply_technical_review(connection, GA, cid, {'result': 'aprovar_para_teste'})
    with pytest.raises(ValueError):
        service.start_test(connection, GA, cid, {})
    service.save_test_plan(connection, GA, cid, {'start_date': '2026-07-01', 'end_date': '2026-07-31'})
    with pytest.raises(ValueError):
        service.start_test(connection, GA, cid, {})
    service.add_participant(connection, GA, cid, {'employee_id': 100})
    assert service.start_test(connection, GA, cid, {})['status'] == 'em_teste'


def test_delivery_requires_batch_balance():
    connection = _conn()
    cid = _candidate_ready_for_test(connection)
    pid = service.add_participant(connection, GA, cid, {'employee_id': 100})['id']
    service.register_distribution(connection, GA, cid, {'movement_type': 'recebimento', 'quantity': 2})
    service.start_test(connection, GA, cid, {})
    service.register_distribution(connection, GA, cid, {
        'movement_type': 'entrega', 'quantity': 2, 'participant_id': pid})
    with pytest.raises(ValueError):
        service.register_distribution(connection, GA, cid, {
            'movement_type': 'entrega', 'quantity': 1, 'participant_id': pid})
    balance = service.compute_distribution_balance(connection, cid)
    assert balance['saldo'] == 0


def test_critical_incident_suspends_and_blocks_resume():
    connection = _conn()
    cid = _candidate_ready_for_test(connection)
    pid = service.add_participant(connection, GA, cid, {'employee_id': 100})['id']
    service.register_distribution(connection, GA, cid, {'movement_type': 'recebimento', 'quantity': 5})
    service.start_test(connection, GA, cid, {})
    incident = service.register_incident(connection, GA, cid, {
        'incident_type': 'falha', 'severity': 'critica',
        'description': 'Ruptura da costura', 'suspend_test': True, 'participant_id': pid})
    assert incident['suspended'] is True
    with pytest.raises(ValueError):
        service.resume_test(connection, GA, cid, {})
    service.resolve_incident(connection, GA, cid, incident['id'], {'conclusion_notes': 'Lote trocado'})
    assert service.resume_test(connection, GA, cid, {})['status'] == 'em_teste'


def test_evaluation_scale_must_be_1_to_5():
    connection = _conn()
    cid = _candidate_ready_for_test(connection)
    pid = service.add_participant(connection, GA, cid, {'employee_id': 100})['id']
    service.register_distribution(connection, GA, cid, {'movement_type': 'recebimento', 'quantity': 5})
    service.start_test(connection, GA, cid, {})
    with pytest.raises(ValueError):
        service.register_evaluation(connection, GA, cid, {
            'participant_id': pid, 'stage': 'inicial', 'ratings': {'conforto': 6}})
    with pytest.raises(ValueError):
        service.register_evaluation(connection, GA, cid, {
            'participant_id': pid, 'stage': 'errada', 'ratings': {'conforto': 4}})


# ── Decisão formal ────────────────────────────────────────────────────────────

def test_decision_requires_justification_and_technical_opinion():
    connection = _conn()
    cid = _candidate_ready_for_test(connection)
    _run_until_decision(connection, cid)
    with pytest.raises(ValueError):
        service.apply_decision(connection, GA, cid, {'decision': 'aprovar', 'reason': ''})
    with pytest.raises(ValueError):
        service.apply_decision(connection, GA, cid, {
            'decision': 'aprovar', 'reason': 'Bom resultado', 'technical_opinion': ''})


def test_decision_blocks_without_minimums_unless_override():
    connection = _conn()
    cid = service.create_candidate(connection, GA, {'name': 'Luva Z'})['id']
    service.apply_technical_review(connection, GA, cid, {'result': 'aprovar_para_teste'})
    service.save_test_plan(connection, GA, cid, {
        'start_date': '2026-07-01', 'end_date': '2026-08-30',
        'min_participants': 5, 'min_response_rate': 80})
    service.add_participant(connection, GA, cid, {'employee_id': 100})
    service.register_distribution(connection, GA, cid, {'movement_type': 'recebimento', 'quantity': 5})
    service.start_test(connection, GA, cid, {})
    service.complete_test(connection, GA, cid, {})
    with pytest.raises(ValueError):
        service.apply_decision(connection, GA, cid, {
            'decision': 'aprovar', 'reason': 'Aprovando sem base',
            'technical_opinion': 'ok'})
    result = service.apply_decision(connection, GA, cid, {
        'decision': 'aprovar', 'reason': 'Exceção justificada: piloto reduzido validado em campo',
        'technical_opinion': 'ok', 'override_minimums': True})
    assert result['status'] == 'aprovado'


def test_decision_blocks_with_open_critical_incident():
    connection = _conn()
    cid = _candidate_ready_for_test(connection)
    pid = _run_until_decision(connection, cid)
    service.register_incident(connection, GA, cid, {
        'incident_type': 'incidente', 'severity': 'critica',
        'description': 'Quase acidente', 'participant_id': pid})
    with pytest.raises(ValueError):
        service.apply_decision(connection, GA, cid, {
            'decision': 'aprovar', 'reason': 'ok', 'technical_opinion': 'ok'})


def test_extend_test_requires_new_end_date():
    connection = _conn()
    cid = _candidate_ready_for_test(connection)
    _run_until_decision(connection, cid)
    with pytest.raises(ValueError):
        service.apply_decision(connection, GA, cid, {
            'decision': 'prorrogar_teste', 'reason': 'Mais tempo'})
    result = service.apply_decision(connection, GA, cid, {
        'decision': 'prorrogar_teste', 'reason': 'Mais tempo', 'new_end_date': '2026-09-30'})
    assert result['status'] == 'em_teste'


# ── Homologação e escopos ─────────────────────────────────────────────────────

def _approved_candidate(connection, actor=GA, employee_id=100, ca='777'):
    cid = _candidate_ready_for_test(connection, actor=actor, ca=ca)
    _run_until_decision(connection, cid, actor=actor, employee_id=employee_id)
    service.apply_decision(connection, actor, cid, {
        'decision': 'aprovar', 'reason': 'Aprovado no piloto', 'technical_opinion': 'ok'})
    return cid


def test_homologation_creates_official_epi_with_unit_scope():
    connection = _conn()
    cid = _approved_candidate(connection)
    result = service.homologate_candidate(connection, GA, cid, {
        'scope_type': 'UNIT', 'scope_unit_id': 1})
    assert result['scope']['scope_type'] == 'UNIT'
    epi = connection.execute('SELECT * FROM epis WHERE id = ?', (result['epi_id'],)).fetchone()
    assert int(epi['unit_id']) == 1
    assert not epi['active_joinventure']
    assert int(epi['origin_test_candidate_id']) == cid
    # Regra C1+D1+E3: visível na unidade própria, invisível em outra unidade
    assert is_epi_visible_for_unit(epi['unit_id'], epi['active_joinventure'], 1, None) is True
    assert is_epi_visible_for_unit(epi['unit_id'], epi['active_joinventure'], 2, None) is False
    candidate = service.fetch_candidate_detail(connection, GA, cid)
    assert candidate['status'] == 'homologado'
    assert int(candidate['approved_epi_id']) == int(result['epi_id'])


def test_homologation_global_scope_follows_engine_rule():
    connection = _conn()
    cid = _approved_candidate(connection)
    result = service.homologate_candidate(connection, GA, cid, {'scope_type': 'GLOBAL'})
    epi = connection.execute('SELECT * FROM epis WHERE id = ?', (result['epi_id'],)).fetchone()
    assert epi['unit_id'] is None
    # GLOBAL: visível fora de JV, oculto para unidade em JV (E3)
    assert is_epi_visible_for_unit(epi['unit_id'], epi['active_joinventure'], 1, None) is True
    assert is_epi_visible_for_unit(epi['unit_id'], epi['active_joinventure'], 1, 'JV Alpha') is False


def test_homologation_joint_venture_requires_active_period():
    connection = _conn()
    cid = _approved_candidate(connection)
    with pytest.raises(ValueError):
        service.homologate_candidate(connection, GA, cid, {
            'scope_type': 'JOINT_VENTURE', 'scope_joint_venture': 'JV Alpha'})
    connection.execute(
        "INSERT INTO unit_joint_venture_periods (company_id, unit_id, joint_venture_name, started_at) "
        "VALUES (1, 1, 'JV Alpha', '2026-01-01T00:00:00+00:00')")
    result = service.homologate_candidate(connection, GA, cid, {
        'scope_type': 'JOINT_VENTURE', 'scope_joint_venture': 'JV Alpha'})
    epi = connection.execute('SELECT * FROM epis WHERE id = ?', (result['epi_id'],)).fetchone()
    assert epi['active_joinventure'] == 'JV Alpha'
    assert int(epi['unit_id']) == 1
    # Visível apenas para unidades na mesma JV
    assert is_epi_visible_for_unit(epi['unit_id'], epi['active_joinventure'], 2, 'JV Alpha') is True
    assert is_epi_visible_for_unit(epi['unit_id'], epi['active_joinventure'], 2, None) is False


def test_unique_rule_single_company_single_unit():
    """Única x Única: 1 empresa × 1 unidade → UNIQUE automático, sem regra artificial."""
    connection = _conn()
    cid = _approved_candidate(connection, actor=GB, employee_id=200, ca='888')
    # Mesmo pedindo GLOBAL, o servidor reconhece o cenário e aplica UNIQUE
    result = service.homologate_candidate(connection, GB, cid, {'scope_type': 'GLOBAL'})
    assert result['scope']['scope_type'] == 'UNIQUE'
    assert result['scope']['unit_ids'] == ['3']
    epi = connection.execute('SELECT * FROM epis WHERE id = ?', (result['epi_id'],)).fetchone()
    # O EPI oficial segue a lógica existente: vinculado à única unidade, sem JV
    assert int(epi['unit_id']) == 3
    assert not epi['active_joinventure']
    assert is_epi_visible_for_unit(epi['unit_id'], epi['active_joinventure'], 3, None) is True


def test_unique_scope_rejected_for_multi_unit_company():
    connection = _conn()
    cid = _approved_candidate(connection)
    with pytest.raises(ValueError):
        service.homologate_candidate(connection, GA, cid, {'scope_type': 'UNIQUE'})


def test_homologation_is_idempotent_and_blocks_duplicates():
    connection = _conn()
    cid = _approved_candidate(connection)
    service.homologate_candidate(connection, GA, cid, {'scope_type': 'UNIT', 'scope_unit_id': 1})
    with pytest.raises(ValueError):
        service.homologate_candidate(connection, GA, cid, {'scope_type': 'UNIT', 'scope_unit_id': 1})
    assert connection.execute('SELECT COUNT(*) FROM epis').fetchone()[0] == 1


def test_homologation_blocks_duplicate_ca_in_official_bank():
    connection = _conn()
    connection.execute(
        "INSERT INTO epis (company_id, name, purchase_code, ca) VALUES (1, 'Existente', 'PC-1', '777')")
    cid = _approved_candidate(connection, ca='777')
    with pytest.raises(ValueError):
        service.homologate_candidate(connection, GA, cid, {'scope_type': 'UNIT', 'scope_unit_id': 1})


def test_homologation_requires_formal_approval():
    connection = _conn()
    cid = _candidate_ready_for_test(connection)
    _run_until_decision(connection, cid)
    with pytest.raises(ValueError):
        service.homologate_candidate(connection, GA, cid, {'scope_type': 'UNIT', 'scope_unit_id': 1})


def test_provisional_record_preserved_after_homologation():
    connection = _conn()
    cid = _approved_candidate(connection)
    service.homologate_candidate(connection, GA, cid, {'scope_type': 'UNIT', 'scope_unit_id': 1})
    row = connection.execute('SELECT * FROM ppe_test_candidates WHERE id = ?', (cid,)).fetchone()
    assert row is not None
    assert row['status'] == 'homologado'
    events = connection.execute(
        "SELECT action FROM ppe_test_events WHERE candidate_id = ? ORDER BY id", (cid,)).fetchall()
    actions = [e['action'] for e in events]
    assert 'homologated' in actions and 'test_started' in actions


# ── Reprovação ────────────────────────────────────────────────────────────────

def test_rejection_blocks_new_distributions_and_keeps_history():
    connection = _conn()
    cid = _candidate_ready_for_test(connection)
    pid = _run_until_decision(connection, cid)
    service.reject_candidate(connection, GA, cid, {
        'reason': 'Durabilidade insuficiente', 'items_destination': 'Devolução ao fornecedor'})
    candidate = service.fetch_candidate_detail(connection, GA, cid)
    assert candidate['status'] == 'reprovado'
    with pytest.raises(ValueError):
        service.register_distribution(connection, GA, cid, {
            'movement_type': 'entrega', 'quantity': 1, 'participant_id': pid})
    # Devolução/descarte continuam permitidos para recolher itens
    service.register_distribution(connection, GA, cid, {'movement_type': 'devolucao', 'quantity': 1})
    with pytest.raises(ValueError):
        service.homologate_candidate(connection, GA, cid, {'scope_type': 'UNIT', 'scope_unit_id': 1})
    assert connection.execute('SELECT COUNT(*) FROM epis').fetchone()[0] == 0


# ── Multi-tenant e permissões ─────────────────────────────────────────────────

def test_tenant_isolation_on_reads_and_writes():
    connection = _conn()
    cid = _candidate_ready_for_test(connection)
    with pytest.raises(PermissionError):
        service.fetch_candidate_detail(connection, GB, cid)
    with pytest.raises(PermissionError):
        service.apply_technical_review(connection, GB, cid, {'result': 'rejeitar', 'notes': 'x'})
    items_b = service.fetch_candidates(connection, GB)
    assert items_b == []


def test_cross_company_employee_rejected():
    connection = _conn()
    cid = _candidate_ready_for_test(connection)
    with pytest.raises(ValueError):
        service.add_participant(connection, GA, cid, {'employee_id': 200})


def test_update_participant_status_orientation_is_dialect_agnostic():
    """update_participant_status não pode usar MAX(col, ?) escalar (SQLite-only,
    quebra no PostgreSQL). A confirmação de orientação é monotônica: 0→1 sobe,
    e um update posterior sem reconfirmar não desconfirma."""
    connection = _conn()
    cid = _candidate_ready_for_test(connection)
    pid = service.add_participant(connection, GA, cid, {'employee_id': 100})['id']
    service.update_participant_status(connection, GA, cid, pid, {
        'status': 'confirmado', 'orientation_confirmed': True})
    row = connection.execute(
        'SELECT orientation_confirmed FROM ppe_test_participants WHERE id = ?', (pid,)).fetchone()
    assert row['orientation_confirmed'] == 1
    # Update posterior sem o flag mantém a confirmação (não desconfirma)
    service.update_participant_status(connection, GA, cid, pid, {'status': 'em_teste'})
    row = connection.execute(
        'SELECT orientation_confirmed FROM ppe_test_participants WHERE id = ?', (pid,)).fetchone()
    assert row['orientation_confirmed'] == 1


def test_duplicate_participant_friendly_error_dialect_agnostic():
    """Guard de participante duplicado não pode depender do texto da exceção
    (difere entre SQLite e PostgreSQL) — deve dar ValueError amigável sempre."""
    connection = _conn()
    cid = _candidate_ready_for_test(connection)
    service.add_participant(connection, GA, cid, {'employee_id': 100})
    with pytest.raises(ValueError, match='já participa'):
        service.add_participant(connection, GA, cid, {'employee_id': 100})


def test_local_admin_cannot_decide_nor_homologate():
    connection = _conn()
    cid = _candidate_ready_for_test(connection)
    _run_until_decision(connection, cid)
    with pytest.raises(PermissionError):
        service.apply_decision(connection, LOCAL, cid, {
            'decision': 'aprovar', 'reason': 'ok', 'technical_opinion': 'ok'})
    with pytest.raises(PermissionError):
        service.homologate_candidate(connection, LOCAL, cid, {'scope_type': 'UNIT', 'scope_unit_id': 1})


def test_permission_matrix():
    assert PERM_PPE_TEST_HOMOLOGATE in PERMISSIONS['general_admin']
    assert PERM_PPE_TEST_DECIDE in PERMISSIONS['general_admin']
    assert PERM_PPE_TEST_HOMOLOGATE not in PERMISSIONS['registry_admin']
    assert PERM_PPE_TEST_HOMOLOGATE not in PERMISSIONS['user']
    assert PERM_PPE_TEST_DECIDE not in PERMISSIONS['user']
    assert PERM_PPE_TEST_MANAGE in PERMISSIONS['user']
    # 'epi_manager' é apelido de 'user' (ROLE_ALIASES em core/roles.py) — o
    # Gestor de EPI é quem faz a triagem e a análise técnica.
    assert PERM_PPE_TEST_TECH_REVIEW in PERMISSIONS['user']
    assert PERM_PPE_TEST_TRIAGE in PERMISSIONS['user']
    # Administrador Master: somente suporte auditado (view), nunca decide/homologa
    assert PERM_PPE_TEST_VIEW in PERMISSIONS['master_admin']
    assert PERM_PPE_TEST_DECIDE not in PERMISSIONS['master_admin']
    assert PERM_PPE_TEST_HOMOLOGATE not in PERMISSIONS['master_admin']
    assert PERM_PPE_TEST_SUGGEST in PERMISSIONS['admin']


def test_events_audit_trail_records_actor():
    connection = _conn()
    sid = service.create_suggestion(connection, GA, {
        'source_type': 'fornecedor', 'suggested_name': 'Protetor Auricular W',
        'requester_name': 'Fornecedor X', 'reason': 'Novo modelo'})['id']
    suggestion = service.fetch_suggestion_detail(connection, GA, sid)
    assert suggestion['events']
    assert suggestion['events'][0]['actor_name'] == 'Admin Geral A'
    assert suggestion['events'][0]['actor_role'] == 'general_admin'
