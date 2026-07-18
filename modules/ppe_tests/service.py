"""Serviços do fluxo de Avaliação e Homologação de EPI em Teste.

Fluxo separado do módulo de avaliações de EPIs já aprovados (modules/feedback):
aqui o produto ainda NÃO faz parte do banco oficial (`epis`). Ele vive como
cadastro provisório em `ppe_test_candidates` até a decisão formal; só a
homologação transacional cria o registro oficial, aplica o escopo
(GLOBAL / JOINT_VENTURE / UNIT / UNIQUE) e preserva o vínculo com o teste.
"""

import json as _json
from datetime import datetime, timezone

from core.auth import ensure_permission, ensure_resource_company
from core.permissions import (
    PERM_PPE_TEST_DECIDE,
    PERM_PPE_TEST_EVALUATE,
    PERM_PPE_TEST_HOMOLOGATE,
    PERM_PPE_TEST_MANAGE,
    PERM_PPE_TEST_SUGGEST,
    PERM_PPE_TEST_TECH_REVIEW,
    PERM_PPE_TEST_TRIAGE,
)
from epi_backend.db import row_to_dict
from epi_backend.epi_scope import (
    SCOPE_GLOBAL,
    SCOPE_JOINT_VENTURE,
    SCOPE_UNIT,
)

UTC = timezone.utc

SCOPE_UNIQUE = 'UNIQUE'
VALID_APPROVAL_SCOPES = {SCOPE_GLOBAL, SCOPE_JOINT_VENTURE, SCOPE_UNIT, SCOPE_UNIQUE}

SUGGESTION_SOURCE_TYPES = {
    'colaborador', 'empresa', 'representante', 'seguranca_trabalho',
    'fornecedor', 'gestor_unidade', 'comissao_interna', 'joint_venture', 'outro',
}

SUGGESTION_STATUSES = {
    'recebida': 'Recebida',
    'em_triagem': 'Em Triagem',
    'aprovada_para_analise': 'Aprovada para Análise Técnica',
    'info_solicitada': 'Solicitada Mais Informação',
    'duplicada': 'Duplicada',
    'inviavel': 'Inviável para Teste',
    'rejeitada': 'Rejeitada na Triagem',
    'convertida': 'Convertida em Cadastro Provisório',
}

TRIAGE_RESULTS = {
    'aprovado_analise_tecnica', 'solicitar_informacoes', 'duplicado',
    'inviavel', 'rejeitado',
}

CANDIDATE_STATUSES = {
    'rascunho': 'Rascunho',
    'em_triagem': 'Em Triagem',
    'em_analise_tecnica': 'Em Análise Técnica',
    'aprovado_para_teste': 'Aprovado para Teste',
    'em_teste': 'Em Teste',
    'teste_suspenso': 'Teste Suspenso',
    'teste_concluido': 'Teste Concluído',
    'em_decisao': 'Em Decisão',
    'aprovado': 'Aprovado',
    'reprovado': 'Reprovado',
    'homologado': 'Homologado',
    'arquivado': 'Arquivado',
}

TECH_REVIEW_RESULTS = {
    'aprovar_para_teste', 'solicitar_correcao', 'solicitar_documento',
    'rejeitar', 'encaminhar_aprovacao_superior',
}

PARTICIPANT_STATUSES = {
    'convidado', 'confirmado', 'em_teste', 'afastado',
    'substituido', 'desistente', 'concluido',
}

DISTRIBUTION_MOVEMENTS = {'recebimento', 'entrega', 'devolucao', 'descarte'}

EVALUATION_STAGES = {'inicial', 'intermediaria', 'final'}

INCIDENT_TYPES = {
    'desconforto', 'irritacao', 'falha', 'ruptura', 'incompatibilidade',
    'tamanho_inadequado', 'perda', 'dano', 'incidente', 'quase_acidente',
    'interrupcao_uso', 'substituicao', 'recusa', 'treinamento_adicional',
}

INCIDENT_SEVERITIES = {'leve', 'moderada', 'grave', 'critica'}

DECISIONS = {
    'aprovar', 'aprovar_com_restricao', 'prorrogar_teste', 'nova_rodada',
    'solicitar_ajuste_fornecedor', 'rejeitar', 'arquivar',
}

# Critérios padronizados da avaliação (escala 1–5)
EVALUATION_CRITERIA = {
    'inicial': ['expectativa', 'adaptacao_inicial', 'facilidade_colocacao', 'tamanho', 'ajuste', 'conforto_inicial'],
    'intermediaria': ['conforto', 'ergonomia', 'mobilidade', 'resistencia', 'aderencia', 'estabilidade',
                      'calor', 'peso', 'irritacao', 'interferencia_atividade', 'compatibilidade_epis',
                      'facilidade_limpeza', 'desgaste', 'aceitacao'],
    'final': ['satisfacao_geral', 'seguranca_percebida', 'durabilidade', 'adequacao_funcao',
              'facilidade_uso', 'protecao_percebida'],
}


def _now():
    return datetime.now(UTC).isoformat()


def _record_event(connection, company_id, action, previous_status, new_status, actor,
                  notes='', reason='', candidate_id=None, suggestion_id=None):
    connection.execute(
        'INSERT INTO ppe_test_events (candidate_id, suggestion_id, company_id, action, previous_status, '
        'new_status, actor_user_id, actor_name, actor_role, notes, reason, created_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            int(candidate_id) if candidate_id else None,
            int(suggestion_id) if suggestion_id else None,
            int(company_id),
            str(action),
            str(previous_status or ''),
            str(new_status or ''),
            int(actor['id']) if actor else None,
            str(actor.get('full_name') or '') if actor else '',
            str(actor.get('role') or '') if actor else '',
            str(notes or ''),
            str(reason or ''),
            _now(),
        )
    )


def _actor_company_id(actor, payload=None):
    if actor.get('role') == 'master_admin' and payload and payload.get('company_id'):
        return int(payload['company_id'])
    return int(actor['company_id'])


def _get_suggestion(connection, suggestion_id, actor):
    row = connection.execute('SELECT * FROM ppe_test_suggestions WHERE id = ?', (int(suggestion_id),)).fetchone()
    if not row:
        raise ValueError('Sugestão de EPI em teste não encontrada.')
    suggestion = row_to_dict(row)
    ensure_resource_company(actor, suggestion, 'Sugestão')
    return suggestion


def _get_candidate(connection, candidate_id, actor):
    row = connection.execute('SELECT * FROM ppe_test_candidates WHERE id = ?', (int(candidate_id),)).fetchone()
    if not row:
        raise ValueError('EPI em teste não encontrado.')
    candidate = row_to_dict(row)
    ensure_resource_company(actor, candidate, 'EPI em teste')
    return candidate


def _require_status(candidate, allowed, action_label):
    status = str(candidate.get('status') or '')
    if status not in allowed:
        raise ValueError(
            f'Ação "{action_label}" não permitida no status atual '
            f'({CANDIDATE_STATUSES.get(status, status)}).'
        )


# ── Sugestões (origem do novo EPI) ────────────────────────────────────────────

def create_suggestion(connection, actor, payload):
    ensure_permission(actor, PERM_PPE_TEST_SUGGEST)
    company_id = _actor_company_id(actor, payload)
    source_type = str(payload.get('source_type') or 'colaborador').strip().lower()
    if source_type not in SUGGESTION_SOURCE_TYPES:
        raise ValueError('Origem da sugestão inválida.')
    suggested_name = str(payload.get('suggested_name') or '').strip()
    requester_name = str(payload.get('requester_name') or actor.get('full_name') or '').strip()
    reason = str(payload.get('reason') or '').strip()
    if not suggested_name:
        raise ValueError('Nome do EPI sugerido é obrigatório.')
    if not requester_name:
        raise ValueError('Nome do solicitante é obrigatório.')
    if not reason:
        raise ValueError('Motivo da sugestão é obrigatório.')
    employee_id = payload.get('employee_id')
    if source_type == 'colaborador' and employee_id:
        emp = connection.execute(
            'SELECT id, company_id FROM employees WHERE id = ?', (int(employee_id),)
        ).fetchone()
        if not emp or int(emp['company_id']) != company_id:
            raise ValueError('Colaborador não encontrado nesta empresa.')
    unit_id = payload.get('unit_id')
    if unit_id:
        unit = connection.execute('SELECT id, company_id FROM units WHERE id = ?', (int(unit_id),)).fetchone()
        if not unit or int(unit['company_id']) != company_id:
            raise ValueError('Unidade não encontrada nesta empresa.')
    attachments = payload.get('attachments') or []
    if not isinstance(attachments, list):
        attachments = []
    now = _now()
    cursor = connection.execute(
        '''INSERT INTO ppe_test_suggestions
           (company_id, unit_id, source_type, requester_name, requester_profile, employee_id,
            employee_registration, employee_role, employee_sector, current_epi_id, current_epi_issue,
            practical_experience, suggested_name, reason, problem_identified, expected_benefit,
            related_activity, risks, notes, attachments_json, suggestion_date, status,
            source_feedback_id, created_by_user_id, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'recebida', ?, ?, ?, ?)''',
        (
            company_id,
            int(unit_id) if unit_id else None,
            source_type,
            requester_name,
            str(payload.get('requester_profile') or actor.get('role') or '').strip(),
            int(employee_id) if employee_id else None,
            str(payload.get('employee_registration') or '').strip(),
            str(payload.get('employee_role') or '').strip(),
            str(payload.get('employee_sector') or '').strip(),
            int(payload['current_epi_id']) if payload.get('current_epi_id') else None,
            str(payload.get('current_epi_issue') or '').strip(),
            str(payload.get('practical_experience') or '').strip(),
            suggested_name,
            reason,
            str(payload.get('problem_identified') or '').strip(),
            str(payload.get('expected_benefit') or '').strip(),
            str(payload.get('related_activity') or '').strip(),
            str(payload.get('risks') or '').strip(),
            str(payload.get('notes') or '').strip(),
            _json.dumps(attachments, ensure_ascii=False),
            str(payload.get('suggestion_date') or now[:10]),
            int(payload['source_feedback_id']) if payload.get('source_feedback_id') else None,
            int(actor['id']),
            now, now,
        )
    )
    suggestion_id = cursor.lastrowid
    _record_event(connection, company_id, 'suggestion_created', '', 'recebida', actor,
                  notes=suggested_name, suggestion_id=suggestion_id)
    return {'ok': True, 'id': suggestion_id, 'status': 'recebida'}


def create_suggestion_from_feedback(connection, actor, feedback_id, payload):
    """Promove uma sugestão do portal do colaborador (epi_feedbacks) para o fluxo de teste."""
    ensure_permission(actor, PERM_PPE_TEST_TRIAGE)
    row = connection.execute(
        '''SELECT f.*, e.name AS employee_name, e.employee_id_code, e.role_name AS employee_role_name,
                  e.sector AS employee_sector_name
           FROM epi_feedbacks f JOIN employees e ON e.id = f.employee_id
           WHERE f.id = ?''',
        (int(feedback_id),)
    ).fetchone()
    if not row:
        raise ValueError('Sugestão do portal não encontrada.')
    fb = row_to_dict(row)
    ensure_resource_company(actor, fb, 'Sugestão')
    suggested_name = str(fb.get('suggested_new_epi_name') or '').strip()
    if not suggested_name:
        raise ValueError('O feedback selecionado não possui sugestão de novo EPI.')
    existing = connection.execute(
        'SELECT id FROM ppe_test_suggestions WHERE source_feedback_id = ?', (int(feedback_id),)
    ).fetchone()
    if existing:
        raise ValueError('Este feedback já foi promovido para o fluxo de EPI em teste.')
    merged = {
        'source_type': 'colaborador',
        'suggested_name': suggested_name,
        'requester_name': str(fb.get('employee_name') or ''),
        'requester_profile': 'colaborador',
        'employee_id': fb.get('employee_id'),
        'employee_registration': str(fb.get('employee_id_code') or ''),
        'employee_role': str(fb.get('employee_role_name') or ''),
        'employee_sector': str(fb.get('employee_sector_name') or ''),
        'unit_id': fb.get('unit_id'),
        'current_epi_id': fb.get('epi_id'),
        'current_epi_issue': str(fb.get('comments') or ''),
        'reason': str(fb.get('suggested_new_epi_notes') or fb.get('improvement_suggestion') or 'Sugestão do colaborador via portal'),
        'source_feedback_id': int(feedback_id),
        'company_id': fb.get('company_id'),
    }
    merged.update({k: v for k, v in (payload or {}).items() if v not in (None, '')})
    return create_suggestion(connection, actor, merged)


def fetch_suggestions(connection, actor, filters=None):
    filters = filters or {}
    clauses, params = [], []
    if actor.get('role') != 'master_admin':
        clauses.append('s.company_id = ?')
        params.append(int(actor['company_id']))
    if filters.get('status'):
        clauses.append('s.status = ?')
        params.append(str(filters['status']))
    where_sql = ('WHERE ' + ' AND '.join(clauses)) if clauses else ''
    rows = connection.execute(
        f'''SELECT s.*, companies.name AS company_name, units.name AS unit_name,
                   employees.name AS employee_name
            FROM ppe_test_suggestions s
            JOIN companies ON companies.id = s.company_id
            LEFT JOIN units ON units.id = s.unit_id
            LEFT JOIN employees ON employees.id = s.employee_id
            {where_sql}
            ORDER BY s.created_at DESC, s.id DESC''',
        tuple(params)
    ).fetchall()
    return [row_to_dict(r) for r in rows]


def fetch_suggestion_detail(connection, actor, suggestion_id):
    suggestion = _get_suggestion(connection, suggestion_id, actor)
    events = connection.execute(
        'SELECT * FROM ppe_test_events WHERE suggestion_id = ? ORDER BY created_at ASC, id ASC',
        (int(suggestion_id),)
    ).fetchall()
    suggestion['events'] = [row_to_dict(e) for e in events]
    return suggestion


def apply_suggestion_triage(connection, actor, suggestion_id, payload):
    """Triagem inicial da sugestão (seção 4). Rejeições exigem justificativa."""
    ensure_permission(actor, PERM_PPE_TEST_TRIAGE)
    suggestion = _get_suggestion(connection, suggestion_id, actor)
    if str(suggestion.get('status')) in ('convertida', 'rejeitada', 'inviavel', 'duplicada'):
        raise ValueError('Sugestão já triada de forma terminal.')
    result = str(payload.get('result') or '').strip()
    if result not in TRIAGE_RESULTS:
        raise ValueError('Resultado de triagem inválido.')
    notes = str(payload.get('notes') or '').strip()
    if result in ('rejeitado', 'inviavel', 'duplicado') and not notes:
        raise ValueError('Justificativa é obrigatória para rejeição, inviabilidade ou duplicidade.')
    checklist = payload.get('checklist') or {}
    if not isinstance(checklist, dict):
        checklist = {}
    status_map = {
        'aprovado_analise_tecnica': 'aprovada_para_analise',
        'solicitar_informacoes': 'info_solicitada',
        'duplicado': 'duplicada',
        'inviavel': 'inviavel',
        'rejeitado': 'rejeitada',
    }
    new_status = status_map[result]
    now = _now()
    connection.execute(
        '''UPDATE ppe_test_suggestions SET status=?, triage_result=?, triage_checklist_json=?,
           triage_notes=?, triage_by_user_id=?, triage_by_name=?, triage_at=?, updated_at=?
           WHERE id=?''',
        (new_status, result, _json.dumps(checklist, ensure_ascii=False), notes,
         int(actor['id']), actor['full_name'], now, now, int(suggestion_id))
    )
    _record_event(connection, suggestion['company_id'], 'suggestion_triage',
                  str(suggestion.get('status') or ''), new_status, actor,
                  notes=notes, reason=result, suggestion_id=suggestion_id)
    return {'ok': True, 'status': new_status, 'result': result}


# ── Cadastro provisório (candidato a EPI) ─────────────────────────────────────

def create_candidate(connection, actor, payload):
    """Cria o cadastro provisório do EPI em teste — fora do banco oficial."""
    ensure_permission(actor, PERM_PPE_TEST_MANAGE)
    company_id = _actor_company_id(actor, payload)
    name = str(payload.get('name') or '').strip()
    if not name:
        raise ValueError('Nome provisório do EPI é obrigatório.')
    suggestion_id = payload.get('suggestion_id')
    suggestion = None
    if suggestion_id:
        suggestion = _get_suggestion(connection, suggestion_id, actor)
        if int(suggestion['company_id']) != company_id:
            raise ValueError('Sugestão pertence a outra empresa.')
        if str(suggestion.get('status')) != 'aprovada_para_analise':
            raise ValueError('A sugestão precisa estar aprovada na triagem antes do cadastro provisório.')
        if suggestion.get('candidate_id'):
            raise ValueError('Esta sugestão já possui cadastro provisório vinculado.')
    unit_id = payload.get('unit_id')
    if unit_id:
        unit = connection.execute('SELECT id, company_id FROM units WHERE id = ?', (int(unit_id),)).fetchone()
        if not unit or int(unit['company_id']) != company_id:
            raise ValueError('Unidade não encontrada nesta empresa.')
    now = _now()
    cursor = connection.execute(
        '''INSERT INTO ppe_test_candidates
           (company_id, unit_id, suggestion_id, name, category, protection_type, manufacturer,
            model_reference, supplier, ca, ca_expiry, size, color, material, tech_sheet,
            certifications, test_batch, quantity_available, unit_measure, estimated_value,
            test_cost, image_data, manual_ref, technical_doc, risks_covered, activities,
            restrictions, notes, status, created_by_user_id, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'em_analise_tecnica', ?, ?, ?)''',
        (
            company_id,
            int(unit_id) if unit_id else None,
            int(suggestion_id) if suggestion_id else None,
            name,
            str(payload.get('category') or '').strip(),
            str(payload.get('protection_type') or '').strip(),
            str(payload.get('manufacturer') or '').strip(),
            str(payload.get('model_reference') or '').strip(),
            str(payload.get('supplier') or '').strip(),
            str(payload.get('ca') or '').strip(),
            str(payload.get('ca_expiry') or '').strip(),
            str(payload.get('size') or '').strip(),
            str(payload.get('color') or '').strip(),
            str(payload.get('material') or '').strip(),
            str(payload.get('tech_sheet') or '').strip(),
            str(payload.get('certifications') or '').strip(),
            str(payload.get('test_batch') or '').strip(),
            int(payload.get('quantity_available') or 0),
            str(payload.get('unit_measure') or 'un').strip(),
            str(payload.get('estimated_value') or '').strip(),
            str(payload.get('test_cost') or '').strip(),
            payload.get('image_data'),
            str(payload.get('manual_ref') or '').strip(),
            str(payload.get('technical_doc') or '').strip(),
            str(payload.get('risks_covered') or '').strip(),
            str(payload.get('activities') or '').strip(),
            str(payload.get('restrictions') or '').strip(),
            str(payload.get('notes') or '').strip(),
            int(actor['id']),
            now, now,
        )
    )
    candidate_id = cursor.lastrowid
    if suggestion_id:
        connection.execute(
            "UPDATE ppe_test_suggestions SET candidate_id=?, status='convertida', updated_at=? WHERE id=?",
            (candidate_id, now, int(suggestion_id))
        )
        _record_event(connection, company_id, 'suggestion_converted', 'aprovada_para_analise',
                      'convertida', actor, suggestion_id=suggestion_id)
    _record_event(connection, company_id, 'candidate_created', '', 'em_analise_tecnica', actor,
                  notes=name, candidate_id=candidate_id)
    return {'ok': True, 'id': candidate_id, 'status': 'em_analise_tecnica'}


def update_candidate(connection, actor, candidate_id, payload):
    ensure_permission(actor, PERM_PPE_TEST_MANAGE)
    candidate = _get_candidate(connection, candidate_id, actor)
    _require_status(candidate, {'rascunho', 'em_triagem', 'em_analise_tecnica', 'aprovado_para_teste'},
                    'editar cadastro provisório')
    editable = [
        'name', 'category', 'protection_type', 'manufacturer', 'model_reference', 'supplier',
        'ca', 'ca_expiry', 'size', 'color', 'material', 'tech_sheet', 'certifications',
        'test_batch', 'quantity_available', 'unit_measure', 'estimated_value', 'test_cost',
        'image_data', 'manual_ref', 'technical_doc', 'risks_covered', 'activities',
        'restrictions', 'notes',
    ]
    sets, params = [], []
    for field in editable:
        if field in payload:
            sets.append(f'{field}=?')
            if field == 'quantity_available':
                params.append(int(payload.get(field) or 0))
            elif field == 'image_data':
                params.append(payload.get(field))
            else:
                params.append(str(payload.get(field) or '').strip())
    if not sets:
        return {'ok': True, 'id': int(candidate_id)}
    sets.append('updated_at=?')
    params.append(_now())
    params.append(int(candidate_id))
    connection.execute(f"UPDATE ppe_test_candidates SET {', '.join(sets)} WHERE id=?", tuple(params))
    _record_event(connection, candidate['company_id'], 'candidate_updated',
                  candidate['status'], candidate['status'], actor, candidate_id=candidate_id)
    return {'ok': True, 'id': int(candidate_id)}


def fetch_candidates(connection, actor, filters=None):
    filters = filters or {}
    clauses, params = [], []
    if actor.get('role') != 'master_admin':
        clauses.append('c.company_id = ?')
        params.append(int(actor['company_id']))
    if filters.get('status'):
        clauses.append('c.status = ?')
        params.append(str(filters['status']))
    where_sql = ('WHERE ' + ' AND '.join(clauses)) if clauses else ''
    rows = connection.execute(
        f'''SELECT c.*, companies.name AS company_name, units.name AS unit_name,
                   p.start_date AS plan_start_date, p.end_date AS plan_end_date,
                   p.min_participants AS plan_min_participants,
                   (SELECT COUNT(*) FROM ppe_test_participants tp WHERE tp.candidate_id = c.id) AS participants_count,
                   (SELECT COUNT(*) FROM ppe_test_evaluations te WHERE te.candidate_id = c.id) AS evaluations_count,
                   (SELECT COUNT(*) FROM ppe_test_incidents ti WHERE ti.candidate_id = c.id AND ti.status != 'resolvida') AS open_incidents_count
            FROM ppe_test_candidates c
            JOIN companies ON companies.id = c.company_id
            LEFT JOIN units ON units.id = c.unit_id
            LEFT JOIN ppe_test_plans p ON p.candidate_id = c.id
            {where_sql}
            ORDER BY c.created_at DESC, c.id DESC''',
        tuple(params)
    ).fetchall()
    return [row_to_dict(r) for r in rows]


def fetch_candidate_detail(connection, actor, candidate_id):
    candidate = _get_candidate(connection, candidate_id, actor)
    cid = int(candidate_id)
    plan = connection.execute('SELECT * FROM ppe_test_plans WHERE candidate_id = ?', (cid,)).fetchone()
    candidate['plan'] = row_to_dict(plan) if plan else None
    participants = connection.execute(
        '''SELECT tp.*, employees.name AS employee_name, units.name AS unit_name
           FROM ppe_test_participants tp
           JOIN employees ON employees.id = tp.employee_id
           LEFT JOIN units ON units.id = tp.unit_id
           WHERE tp.candidate_id = ? ORDER BY tp.id ASC''', (cid,)
    ).fetchall()
    candidate['participants'] = [row_to_dict(p) for p in participants]
    distributions = connection.execute(
        'SELECT * FROM ppe_test_distributions WHERE candidate_id = ? ORDER BY created_at ASC, id ASC', (cid,)
    ).fetchall()
    candidate['distributions'] = [row_to_dict(d) for d in distributions]
    evaluations = connection.execute(
        'SELECT * FROM ppe_test_evaluations WHERE candidate_id = ? ORDER BY created_at ASC, id ASC', (cid,)
    ).fetchall()
    candidate['evaluations'] = [row_to_dict(e) for e in evaluations]
    incidents = connection.execute(
        'SELECT * FROM ppe_test_incidents WHERE candidate_id = ? ORDER BY created_at ASC, id ASC', (cid,)
    ).fetchall()
    candidate['incidents'] = [row_to_dict(i) for i in incidents]
    events = connection.execute(
        'SELECT * FROM ppe_test_events WHERE candidate_id = ? ORDER BY created_at ASC, id ASC', (cid,)
    ).fetchall()
    candidate['events'] = [row_to_dict(e) for e in events]
    candidate['results'] = compute_test_results(connection, actor, candidate_id, _candidate=candidate)
    return candidate


# ── Análise técnica e documental ──────────────────────────────────────────────

def apply_technical_review(connection, actor, candidate_id, payload):
    ensure_permission(actor, PERM_PPE_TEST_TECH_REVIEW)
    candidate = _get_candidate(connection, candidate_id, actor)
    _require_status(candidate, {'em_analise_tecnica'}, 'análise técnica')
    result = str(payload.get('result') or '').strip()
    if result not in TECH_REVIEW_RESULTS:
        raise ValueError('Resultado de análise técnica inválido.')
    notes = str(payload.get('notes') or '').strip()
    if result == 'rejeitar' and not notes:
        raise ValueError('Justificativa é obrigatória para rejeitar na análise técnica.')
    checklist = payload.get('checklist') or {}
    if not isinstance(checklist, dict):
        checklist = {}
    status_map = {
        'aprovar_para_teste': 'aprovado_para_teste',
        'solicitar_correcao': 'em_analise_tecnica',
        'solicitar_documento': 'em_analise_tecnica',
        'rejeitar': 'reprovado',
        'encaminhar_aprovacao_superior': 'em_analise_tecnica',
    }
    new_status = status_map[result]
    now = _now()
    connection.execute(
        '''UPDATE ppe_test_candidates SET status=?, technical_checklist_json=?,
           technical_review_result=?, technical_review_notes=?, technical_review_by_user_id=?,
           technical_review_by_name=?, technical_review_at=?, updated_at=? WHERE id=?''',
        (new_status, _json.dumps(checklist, ensure_ascii=False), result, notes,
         int(actor['id']), actor['full_name'], now, now, int(candidate_id))
    )
    _record_event(connection, candidate['company_id'], 'technical_review',
                  candidate['status'], new_status, actor, notes=notes, reason=result,
                  candidate_id=candidate_id)
    return {'ok': True, 'status': new_status, 'result': result}


# ── Plano de teste ────────────────────────────────────────────────────────────

def save_test_plan(connection, actor, candidate_id, payload):
    ensure_permission(actor, PERM_PPE_TEST_MANAGE)
    candidate = _get_candidate(connection, candidate_id, actor)
    _require_status(candidate, {'em_analise_tecnica', 'aprovado_para_teste'}, 'definir plano de teste')
    start_date = str(payload.get('start_date') or '').strip()
    end_date = str(payload.get('end_date') or '').strip()
    if not start_date or not end_date:
        raise ValueError('Datas inicial e final do teste são obrigatórias.')
    if end_date < start_date:
        raise ValueError('Data final do teste não pode ser anterior à inicial.')
    pilot_unit_id = payload.get('pilot_unit_id') or candidate.get('unit_id')
    if pilot_unit_id:
        unit = connection.execute('SELECT id, company_id FROM units WHERE id = ?', (int(pilot_unit_id),)).fetchone()
        if not unit or int(unit['company_id']) != int(candidate['company_id']):
            raise ValueError('Unidade piloto não encontrada nesta empresa.')
    current_epi_id = payload.get('current_epi_id')
    if current_epi_id:
        epi = connection.execute('SELECT id, company_id FROM epis WHERE id = ?', (int(current_epi_id),)).fetchone()
        if not epi or int(epi['company_id']) != int(candidate['company_id']):
            raise ValueError('EPI comparativo atual não encontrado nesta empresa.')
    try:
        duration_days = (datetime.fromisoformat(end_date) - datetime.fromisoformat(start_date)).days
    except ValueError:
        duration_days = int(payload.get('duration_days') or 0)
    now = _now()
    values = (
        int(candidate_id), int(candidate['company_id']),
        str(payload.get('objective') or '').strip(),
        str(payload.get('hypothesis') or '').strip(),
        str(payload.get('problem') or '').strip(),
        str(payload.get('risks') or '').strip(),
        start_date, end_date, max(duration_days, 0),
        int(pilot_unit_id) if pilot_unit_id else None,
        str(payload.get('sector') or '').strip(),
        str(payload.get('activity') or '').strip(),
        str(payload.get('role_name') or '').strip(),
        int(payload.get('participants_target') or 0),
        int(payload.get('epis_quantity') or 0),
        int(current_epi_id) if current_epi_id else None,
        str(payload.get('approval_criteria') or '').strip(),
        str(payload.get('rejection_criteria') or '').strip(),
        str(payload.get('evaluation_frequency') or '').strip(),
        str(payload.get('technical_manager') or '').strip(),
        str(payload.get('operational_manager') or '').strip(),
        1 if payload.get('training_required') else 0,
        str(payload.get('contingency_plan') or '').strip(),
        str(payload.get('interruption_condition') or '').strip(),
        int(payload.get('min_participants') or 0),
        int(payload.get('min_response_rate') or 0),
        now, now,
    )
    connection.execute(
        '''INSERT INTO ppe_test_plans
           (candidate_id, company_id, objective, hypothesis, problem, risks, start_date, end_date,
            duration_days, pilot_unit_id, sector, activity, role_name, participants_target,
            epis_quantity, current_epi_id, approval_criteria, rejection_criteria,
            evaluation_frequency, technical_manager, operational_manager, training_required,
            contingency_plan, interruption_condition, min_participants, min_response_rate,
            created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(candidate_id) DO UPDATE SET
             objective=excluded.objective, hypothesis=excluded.hypothesis, problem=excluded.problem,
             risks=excluded.risks, start_date=excluded.start_date, end_date=excluded.end_date,
             duration_days=excluded.duration_days, pilot_unit_id=excluded.pilot_unit_id,
             sector=excluded.sector, activity=excluded.activity, role_name=excluded.role_name,
             participants_target=excluded.participants_target, epis_quantity=excluded.epis_quantity,
             current_epi_id=excluded.current_epi_id, approval_criteria=excluded.approval_criteria,
             rejection_criteria=excluded.rejection_criteria,
             evaluation_frequency=excluded.evaluation_frequency,
             technical_manager=excluded.technical_manager,
             operational_manager=excluded.operational_manager,
             training_required=excluded.training_required,
             contingency_plan=excluded.contingency_plan,
             interruption_condition=excluded.interruption_condition,
             min_participants=excluded.min_participants,
             min_response_rate=excluded.min_response_rate,
             updated_at=excluded.updated_at''',
        values
    )
    _record_event(connection, candidate['company_id'], 'plan_saved',
                  candidate['status'], candidate['status'], actor, candidate_id=candidate_id)
    return {'ok': True}


# ── Participantes ─────────────────────────────────────────────────────────────

def add_participant(connection, actor, candidate_id, payload):
    ensure_permission(actor, PERM_PPE_TEST_MANAGE)
    candidate = _get_candidate(connection, candidate_id, actor)
    _require_status(candidate, {'aprovado_para_teste', 'em_teste'}, 'adicionar participante')
    employee_id = payload.get('employee_id')
    if not employee_id:
        raise ValueError('Colaborador é obrigatório.')
    emp = connection.execute(
        'SELECT id, company_id, unit_id, role_name FROM employees WHERE id = ?', (int(employee_id),)
    ).fetchone()
    if not emp or int(emp['company_id']) != int(candidate['company_id']):
        raise ValueError('Colaborador não encontrado nesta empresa.')
    # Pré-checagem agnóstica de dialeto: a constraint UNIQUE(candidate_id,
    # employee_id) é o guard real, mas o texto da exceção difere entre SQLite
    # ("UNIQUE constraint failed") e PostgreSQL ("duplicate key ... unique
    # constraint"). Checar antes evita depender do texto para a mensagem amigável.
    already = connection.execute(
        'SELECT 1 FROM ppe_test_participants WHERE candidate_id = ? AND employee_id = ? LIMIT 1',
        (int(candidate_id), int(employee_id))
    ).fetchone()
    if already:
        raise ValueError('Este colaborador já participa deste teste.')
    now = _now()
    try:
        cursor = connection.execute(
            '''INSERT INTO ppe_test_participants
               (candidate_id, company_id, unit_id, employee_id, role_name, current_epi_id, size,
                orientation_confirmed, signature_name, status, notes, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                int(candidate_id), int(candidate['company_id']),
                int(payload.get('unit_id') or emp['unit_id'] or 0) or None,
                int(employee_id),
                str(payload.get('role_name') or emp['role_name'] or '').strip(),
                int(payload['current_epi_id']) if payload.get('current_epi_id') else None,
                str(payload.get('size') or '').strip(),
                1 if payload.get('orientation_confirmed') else 0,
                str(payload.get('signature_name') or '').strip(),
                str(payload.get('status') or 'convidado').strip(),
                str(payload.get('notes') or '').strip(),
                now, now,
            )
        )
    except Exception as exc:
        # Backstop para corrida entre a pré-checagem e o INSERT — cobre o texto
        # de ambos os dialetos (SQLite: "UNIQUE"; PostgreSQL: "unique"/"duplicate").
        msg = str(exc).lower()
        if 'unique' in msg or 'duplicate' in msg:
            raise ValueError('Este colaborador já participa deste teste.')
        raise
    _record_event(connection, candidate['company_id'], 'participant_added',
                  candidate['status'], candidate['status'], actor,
                  notes=f'employee_id={employee_id}', candidate_id=candidate_id)
    return {'ok': True, 'id': cursor.lastrowid}


def update_participant_status(connection, actor, candidate_id, participant_id, payload):
    ensure_permission(actor, PERM_PPE_TEST_MANAGE)
    candidate = _get_candidate(connection, candidate_id, actor)
    row = connection.execute(
        'SELECT * FROM ppe_test_participants WHERE id = ? AND candidate_id = ?',
        (int(participant_id), int(candidate_id))
    ).fetchone()
    if not row:
        raise ValueError('Participante não encontrado neste teste.')
    participant = row_to_dict(row)
    new_status = str(payload.get('status') or '').strip()
    if new_status not in PARTICIPANT_STATUSES:
        raise ValueError('Status de participante inválido.')
    now = _now()
    connection.execute(
        '''UPDATE ppe_test_participants SET status=?, size=COALESCE(NULLIF(?, ''), size),
           orientation_confirmed=CASE WHEN ?=1 THEN 1 ELSE orientation_confirmed END,
           signature_name=COALESCE(NULLIF(?, ''), signature_name),
           delivered_at=COALESCE(NULLIF(?, ''), delivered_at),
           notes=COALESCE(NULLIF(?, ''), notes), updated_at=? WHERE id=?''',
        (new_status, str(payload.get('size') or ''),
         1 if payload.get('orientation_confirmed') else 0,
         str(payload.get('signature_name') or ''),
         str(payload.get('delivered_at') or ''),
         str(payload.get('notes') or ''), now, int(participant_id))
    )
    _record_event(connection, candidate['company_id'], 'participant_status',
                  participant['status'], new_status, actor,
                  notes=f'participant_id={participant_id}', candidate_id=candidate_id)
    return {'ok': True, 'status': new_status}


# ── Distribuição controlada ───────────────────────────────────────────────────

def register_distribution(connection, actor, candidate_id, payload):
    ensure_permission(actor, PERM_PPE_TEST_MANAGE)
    candidate = _get_candidate(connection, candidate_id, actor)
    movement_type = str(payload.get('movement_type') or 'entrega').strip()
    if movement_type not in DISTRIBUTION_MOVEMENTS:
        raise ValueError('Tipo de movimento de distribuição inválido.')
    if movement_type == 'entrega':
        _require_status(candidate, {'em_teste'}, 'entregar EPI de teste')
    else:
        _require_status(candidate, {'aprovado_para_teste', 'em_teste', 'teste_suspenso',
                                    'teste_concluido', 'em_decisao', 'reprovado'},
                        'movimentar EPI de teste')
    quantity = int(payload.get('quantity') or 1)
    if quantity <= 0:
        raise ValueError('Quantidade deve ser positiva.')
    participant_id = payload.get('participant_id')
    if movement_type == 'entrega':
        if not participant_id:
            raise ValueError('Entrega de EPI em teste exige participante.')
        prow = connection.execute(
            'SELECT * FROM ppe_test_participants WHERE id = ? AND candidate_id = ?',
            (int(participant_id), int(candidate_id))
        ).fetchone()
        if not prow:
            raise ValueError('Participante não encontrado neste teste.')
        balance = compute_distribution_balance(connection, candidate_id)
        if quantity > balance['saldo']:
            raise ValueError(f'Saldo insuficiente do lote de teste (saldo atual: {balance["saldo"]}).')
    now = _now()
    cursor = connection.execute(
        '''INSERT INTO ppe_test_distributions
           (candidate_id, company_id, participant_id, movement_type, quantity, batch, supplier,
            storage_location, responsible_name, signature_name, expected_return, disposal_required,
            notes, created_by_user_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (
            int(candidate_id), int(candidate['company_id']),
            int(participant_id) if participant_id else None,
            movement_type, quantity,
            str(payload.get('batch') or '').strip(),
            str(payload.get('supplier') or '').strip(),
            str(payload.get('storage_location') or '').strip(),
            str(payload.get('responsible_name') or actor.get('full_name') or '').strip(),
            str(payload.get('signature_name') or '').strip(),
            str(payload.get('expected_return') or '').strip(),
            1 if payload.get('disposal_required') else 0,
            str(payload.get('notes') or '').strip(),
            int(actor['id']), now,
        )
    )
    if movement_type == 'entrega' and participant_id:
        connection.execute(
            "UPDATE ppe_test_participants SET status='em_teste', delivered_at=?, updated_at=? "
            "WHERE id=? AND status IN ('convidado', 'confirmado')",
            (now, now, int(participant_id))
        )
    _record_event(connection, candidate['company_id'], f'distribution_{movement_type}',
                  candidate['status'], candidate['status'], actor,
                  notes=f'qtd={quantity}', candidate_id=candidate_id)
    return {'ok': True, 'id': cursor.lastrowid}


def compute_distribution_balance(connection, candidate_id):
    rows = connection.execute(
        'SELECT movement_type, SUM(quantity) AS total FROM ppe_test_distributions '
        'WHERE candidate_id = ? GROUP BY movement_type',
        (int(candidate_id),)
    ).fetchall()
    totals = {str(r['movement_type']): int(r['total'] or 0) for r in rows}
    recebido = totals.get('recebimento', 0)
    entregue = totals.get('entrega', 0)
    devolvido = totals.get('devolucao', 0)
    descartado = totals.get('descarte', 0)
    return {
        'recebido': recebido,
        'entregue': entregue,
        'devolvido': devolvido,
        'descartado': descartado,
        'saldo': recebido - entregue + devolvido - descartado,
    }


# ── Ciclo de vida do teste ────────────────────────────────────────────────────

def start_test(connection, actor, candidate_id, payload):
    ensure_permission(actor, PERM_PPE_TEST_MANAGE)
    candidate = _get_candidate(connection, candidate_id, actor)
    _require_status(candidate, {'aprovado_para_teste'}, 'iniciar teste')
    plan = connection.execute(
        'SELECT * FROM ppe_test_plans WHERE candidate_id = ?', (int(candidate_id),)
    ).fetchone()
    if not plan:
        raise ValueError('Defina o plano de teste antes de iniciar o período de avaliação.')
    participants = connection.execute(
        "SELECT COUNT(*) AS n FROM ppe_test_participants WHERE candidate_id = ? "
        "AND status NOT IN ('desistente', 'substituido')",
        (int(candidate_id),)
    ).fetchone()
    if int(participants['n'] or 0) == 0:
        raise ValueError('Selecione ao menos um participante antes de iniciar o teste.')
    now = _now()
    connection.execute(
        "UPDATE ppe_test_candidates SET status='em_teste', updated_at=? WHERE id=?",
        (now, int(candidate_id))
    )
    _record_event(connection, candidate['company_id'], 'test_started',
                  candidate['status'], 'em_teste', actor,
                  notes=str(payload.get('notes') or ''), candidate_id=candidate_id)
    return {'ok': True, 'status': 'em_teste'}


def suspend_test(connection, actor, candidate_id, payload):
    ensure_permission(actor, PERM_PPE_TEST_MANAGE)
    candidate = _get_candidate(connection, candidate_id, actor)
    _require_status(candidate, {'em_teste'}, 'suspender teste')
    reason = str(payload.get('reason') or '').strip()
    if not reason:
        raise ValueError('Justificativa é obrigatória para suspender o teste.')
    now = _now()
    connection.execute(
        "UPDATE ppe_test_candidates SET status='teste_suspenso', updated_at=? WHERE id=?",
        (now, int(candidate_id))
    )
    _record_event(connection, candidate['company_id'], 'test_suspended',
                  'em_teste', 'teste_suspenso', actor, reason=reason, candidate_id=candidate_id)
    return {'ok': True, 'status': 'teste_suspenso'}


def resume_test(connection, actor, candidate_id, payload):
    ensure_permission(actor, PERM_PPE_TEST_MANAGE)
    candidate = _get_candidate(connection, candidate_id, actor)
    _require_status(candidate, {'teste_suspenso'}, 'retomar teste')
    critical_open = connection.execute(
        "SELECT COUNT(*) AS n FROM ppe_test_incidents WHERE candidate_id = ? "
        "AND severity = 'critica' AND status != 'resolvida'",
        (int(candidate_id),)
    ).fetchone()
    if int(critical_open['n'] or 0) > 0:
        raise ValueError('Não é possível retomar: há ocorrência crítica não resolvida.')
    now = _now()
    connection.execute(
        "UPDATE ppe_test_candidates SET status='em_teste', updated_at=? WHERE id=?",
        (now, int(candidate_id))
    )
    _record_event(connection, candidate['company_id'], 'test_resumed',
                  'teste_suspenso', 'em_teste', actor,
                  notes=str(payload.get('notes') or ''), candidate_id=candidate_id)
    return {'ok': True, 'status': 'em_teste'}


def complete_test(connection, actor, candidate_id, payload):
    ensure_permission(actor, PERM_PPE_TEST_MANAGE)
    candidate = _get_candidate(connection, candidate_id, actor)
    _require_status(candidate, {'em_teste', 'teste_suspenso'}, 'concluir teste')
    now = _now()
    connection.execute(
        "UPDATE ppe_test_candidates SET status='teste_concluido', updated_at=? WHERE id=?",
        (now, int(candidate_id))
    )
    connection.execute(
        "UPDATE ppe_test_participants SET status='concluido', updated_at=? "
        "WHERE candidate_id=? AND status='em_teste'",
        (now, int(candidate_id))
    )
    _record_event(connection, candidate['company_id'], 'test_completed',
                  candidate['status'], 'teste_concluido', actor,
                  notes=str(payload.get('notes') or ''), candidate_id=candidate_id)
    return {'ok': True, 'status': 'teste_concluido'}


# ── Avaliações (inicial / intermediárias / final) ─────────────────────────────

def register_evaluation(connection, actor, candidate_id, payload):
    ensure_permission(actor, PERM_PPE_TEST_EVALUATE)
    candidate = _get_candidate(connection, candidate_id, actor)
    _require_status(candidate, {'em_teste', 'teste_concluido'}, 'registrar avaliação')
    stage = str(payload.get('stage') or 'inicial').strip()
    if stage not in EVALUATION_STAGES:
        raise ValueError('Momento de avaliação inválido (inicial, intermediaria ou final).')
    participant_id = payload.get('participant_id')
    if not participant_id:
        raise ValueError('Participante é obrigatório.')
    prow = connection.execute(
        'SELECT * FROM ppe_test_participants WHERE id = ? AND candidate_id = ?',
        (int(participant_id), int(candidate_id))
    ).fetchone()
    if not prow:
        raise ValueError('Participante não encontrado neste teste.')
    ratings = payload.get('ratings') or {}
    if not isinstance(ratings, dict) or not ratings:
        raise ValueError('Informe ao menos um critério avaliado (escala 1 a 5).')
    for key, value in ratings.items():
        try:
            v = int(value)
        except (TypeError, ValueError):
            raise ValueError(f'Nota inválida para o critério {key}.')
        if v < 1 or v > 5:
            raise ValueError(f'Nota do critério {key} deve estar entre 1 e 5.')
    current_ratings = payload.get('current_epi_ratings') or {}
    if not isinstance(current_ratings, dict):
        current_ratings = {}
    now = _now()
    cursor = connection.execute(
        '''INSERT INTO ppe_test_evaluations
           (candidate_id, company_id, participant_id, stage, ratings_json,
            current_epi_ratings_json, comments, positive_points, negative_points,
            preference, recommend, issues, continue_intent, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (
            int(candidate_id), int(candidate['company_id']), int(participant_id), stage,
            _json.dumps(ratings, ensure_ascii=False),
            _json.dumps(current_ratings, ensure_ascii=False),
            str(payload.get('comments') or '').strip(),
            str(payload.get('positive_points') or '').strip(),
            str(payload.get('negative_points') or '').strip(),
            str(payload.get('preference') or '').strip(),
            1 if payload.get('recommend') else 0,
            str(payload.get('issues') or '').strip(),
            1 if payload.get('continue_intent') else 0,
            now,
        )
    )
    _record_event(connection, candidate['company_id'], f'evaluation_{stage}',
                  candidate['status'], candidate['status'], actor,
                  notes=f'participant_id={participant_id}', candidate_id=candidate_id)
    return {'ok': True, 'id': cursor.lastrowid}


# ── Ocorrências ───────────────────────────────────────────────────────────────

def register_incident(connection, actor, candidate_id, payload):
    ensure_permission(actor, PERM_PPE_TEST_EVALUATE)
    candidate = _get_candidate(connection, candidate_id, actor)
    _require_status(candidate, {'em_teste', 'teste_suspenso', 'teste_concluido'}, 'registrar ocorrência')
    incident_type = str(payload.get('incident_type') or 'desconforto').strip()
    if incident_type not in INCIDENT_TYPES:
        raise ValueError('Tipo de ocorrência inválido.')
    severity = str(payload.get('severity') or 'leve').strip()
    if severity not in INCIDENT_SEVERITIES:
        raise ValueError('Gravidade inválida.')
    description = str(payload.get('description') or '').strip()
    if not description:
        raise ValueError('Descrição da ocorrência é obrigatória.')
    participant_id = payload.get('participant_id')
    if participant_id:
        prow = connection.execute(
            'SELECT id FROM ppe_test_participants WHERE id = ? AND candidate_id = ?',
            (int(participant_id), int(candidate_id))
        ).fetchone()
        if not prow:
            raise ValueError('Participante não encontrado neste teste.')
    suspend = bool(payload.get('suspend_test')) and severity == 'critica'
    now = _now()
    cursor = connection.execute(
        '''INSERT INTO ppe_test_incidents
           (candidate_id, company_id, participant_id, incident_type, severity, description,
            evidence, photo_data, action_taken, responsible_name, status, suspended_test,
            created_by_user_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'aberta', ?, ?, ?)''',
        (
            int(candidate_id), int(candidate['company_id']),
            int(participant_id) if participant_id else None,
            incident_type, severity, description,
            str(payload.get('evidence') or '').strip(),
            payload.get('photo_data'),
            str(payload.get('action_taken') or '').strip(),
            str(payload.get('responsible_name') or actor.get('full_name') or '').strip(),
            1 if suspend else 0,
            int(actor['id']), now,
        )
    )
    incident_id = cursor.lastrowid
    _record_event(connection, candidate['company_id'], 'incident_registered',
                  candidate['status'], candidate['status'], actor,
                  notes=description[:200], reason=f'{incident_type}/{severity}',
                  candidate_id=candidate_id)
    if suspend and str(candidate['status']) == 'em_teste':
        connection.execute(
            "UPDATE ppe_test_candidates SET status='teste_suspenso', updated_at=? WHERE id=?",
            (now, int(candidate_id))
        )
        _record_event(connection, candidate['company_id'], 'test_suspended',
                      'em_teste', 'teste_suspenso', actor,
                      reason=f'Ocorrência crítica #{incident_id}', candidate_id=candidate_id)
    return {'ok': True, 'id': incident_id, 'suspended': suspend}


def resolve_incident(connection, actor, candidate_id, incident_id, payload):
    ensure_permission(actor, PERM_PPE_TEST_MANAGE)
    candidate = _get_candidate(connection, candidate_id, actor)
    row = connection.execute(
        'SELECT * FROM ppe_test_incidents WHERE id = ? AND candidate_id = ?',
        (int(incident_id), int(candidate_id))
    ).fetchone()
    if not row:
        raise ValueError('Ocorrência não encontrada neste teste.')
    conclusion = str(payload.get('conclusion_notes') or '').strip()
    if not conclusion:
        raise ValueError('Conclusão do tratamento é obrigatória.')
    now = _now()
    connection.execute(
        '''UPDATE ppe_test_incidents SET status='resolvida', conclusion_notes=?,
           action_taken=COALESCE(NULLIF(?, ''), action_taken), resolved_at=? WHERE id=?''',
        (conclusion, str(payload.get('action_taken') or ''), now, int(incident_id))
    )
    _record_event(connection, candidate['company_id'], 'incident_resolved',
                  candidate['status'], candidate['status'], actor,
                  notes=conclusion[:200], candidate_id=candidate_id)
    return {'ok': True}


# ── Consolidação dos resultados ───────────────────────────────────────────────

def compute_test_results(connection, actor, candidate_id, _candidate=None):
    candidate = _candidate or _get_candidate(connection, candidate_id, actor)
    cid = int(candidate_id)
    plan = connection.execute('SELECT * FROM ppe_test_plans WHERE candidate_id = ?', (cid,)).fetchone()
    plan = row_to_dict(plan) if plan else {}
    participants = connection.execute(
        'SELECT status FROM ppe_test_participants WHERE candidate_id = ?', (cid,)
    ).fetchall()
    total_participants = len(participants)
    active = len([p for p in participants if str(p['status']) in ('confirmado', 'em_teste', 'concluido')])
    dropouts = len([p for p in participants if str(p['status']) in ('desistente', 'afastado', 'substituido')])
    evaluations = connection.execute(
        'SELECT stage, participant_id, ratings_json, current_epi_ratings_json, preference, recommend '
        'FROM ppe_test_evaluations WHERE candidate_id = ?', (cid,)
    ).fetchall()
    stage_counts = {'inicial': 0, 'intermediaria': 0, 'final': 0}
    criteria_totals: dict = {}
    current_totals: dict = {}
    preferences = {'novo': 0, 'atual': 0, 'indiferente': 0}
    recommend_count = 0
    final_respondents = set()
    for ev in evaluations:
        stage = str(ev['stage'])
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
        if stage == 'final':
            final_respondents.add(int(ev['participant_id']))
            if int(ev['recommend'] or 0):
                recommend_count += 1
            pref = str(ev['preference'] or '')
            if pref in preferences:
                preferences[pref] += 1
        try:
            ratings = _json.loads(ev['ratings_json'] or '{}')
        except ValueError:
            ratings = {}
        for key, value in (ratings or {}).items():
            bucket = criteria_totals.setdefault(key, [0, 0])
            bucket[0] += int(value)
            bucket[1] += 1
        try:
            current = _json.loads(ev['current_epi_ratings_json'] or '{}')
        except ValueError:
            current = {}
        for key, value in (current or {}).items():
            bucket = current_totals.setdefault(key, [0, 0])
            bucket[0] += int(value)
            bucket[1] += 1
    criteria_avgs = {k: round(v[0] / v[1], 2) for k, v in criteria_totals.items() if v[1]}
    current_avgs = {k: round(v[0] / v[1], 2) for k, v in current_totals.items() if v[1]}
    comparison = []
    for key, new_avg in criteria_avgs.items():
        cur_avg = current_avgs.get(key)
        delta_pct = None
        if cur_avg:
            delta_pct = round((new_avg - cur_avg) / cur_avg * 100, 1)
        comparison.append({'criterion': key, 'novo': new_avg, 'atual': cur_avg, 'delta_pct': delta_pct})
    incidents = connection.execute(
        'SELECT severity, status FROM ppe_test_incidents WHERE candidate_id = ?', (cid,)
    ).fetchall()
    open_incidents = len([i for i in incidents if str(i['status']) != 'resolvida'])
    critical_open = len([i for i in incidents if str(i['status']) != 'resolvida' and str(i['severity']) == 'critica'])
    total_finals = len(final_respondents)
    response_rate = round(total_finals / total_participants * 100, 1) if total_participants else 0.0
    min_participants = int(plan.get('min_participants') or 0)
    min_response_rate = int(plan.get('min_response_rate') or 0)
    balance = compute_distribution_balance(connection, candidate_id)
    days_elapsed = days_remaining = None
    if plan.get('start_date'):
        try:
            start = datetime.fromisoformat(str(plan['start_date']))
            today = datetime.now(UTC).replace(tzinfo=None)
            days_elapsed = max((today - start).days, 0)
            if plan.get('end_date'):
                end = datetime.fromisoformat(str(plan['end_date']))
                days_remaining = max((end - today).days, 0)
        except ValueError:
            pass
    requirements = {
        'min_participants_ok': total_participants >= min_participants if min_participants else True,
        'min_response_rate_ok': response_rate >= min_response_rate if min_response_rate else True,
        'critical_incidents_ok': critical_open == 0,
        'has_final_evaluations': total_finals > 0,
    }
    overall_avg = round(sum(criteria_avgs.values()) / len(criteria_avgs), 2) if criteria_avgs else None
    return {
        'participants_total': total_participants,
        'participants_active': active,
        'dropouts': dropouts,
        'evaluations_by_stage': stage_counts,
        'final_response_rate': response_rate,
        'criteria_averages': criteria_avgs,
        'current_epi_averages': current_avgs,
        'comparison': comparison,
        'overall_average': overall_avg,
        'preferences': preferences,
        'recommend_count': recommend_count,
        'recommend_rate': round(recommend_count / total_finals * 100, 1) if total_finals else 0.0,
        'incidents_total': len(incidents),
        'incidents_open': open_incidents,
        'incidents_critical_open': critical_open,
        'distribution': balance,
        'days_elapsed': days_elapsed,
        'days_remaining': days_remaining,
        'requirements': requirements,
    }


# ── Escopo de aprovação (Global / JV / Unidade / Única) ───────────────────────

def resolve_approval_scope(connection, company_id, requested_scope, scope_unit_id=None,
                           scope_joint_venture=''):
    """Valida e resolve o escopo seguindo a regra existente do sistema.

    Regra de visibilidade C1+D1+E3 (epi_backend/epi_scope.py — confirmada):
    o escopo NÃO é um campo livre; ele é derivado do registro do EPI:
      - JV ativa na unidade  → JOINT_VENTURE (fonte de verdade:
        unit_joint_venture_periods, período com ended_at IS NULL);
      - unit_id preenchido   → UNIT;
      - nenhum dos dois      → GLOBAL.
    Visibilidade: fora de JV a unidade vê GLOBAL + UNIT própria; unidade em
    JV X vê UNIT própria + EPIs da JV X (GLOBAL fica oculto).

    Única x Única: quando a empresa possui uma única unidade ativa, o EPI é
    de uso exclusivo daquela estrutura — nasce vinculado à unidade (semântica
    UNIT da regra existente), sem criar regra artificial de Global nem de
    Joint Venture. O rótulo UNIQUE é apenas metadado de auditoria do teste;
    a visibilidade continua sendo resolvida pelo engine existente.

    Nunca confia no escopo enviado pelo frontend: valida a estrutura da
    tenant (empresa/unidades/períodos de JV) antes de aplicar.
    """
    company_id = int(company_id)
    requested_scope = str(requested_scope or '').strip().upper()
    scope_joint_venture = str(scope_joint_venture or '').strip()
    units = connection.execute(
        "SELECT id, name FROM units WHERE company_id = ? AND COALESCE(status, 'active') = 'active'",
        (company_id,)
    ).fetchall()
    active_units = [row_to_dict(u) for u in units]
    if not active_units:
        raise ValueError('A empresa não possui unidade ativa para receber o EPI homologado.')

    def _active_jv_name(unit_id):
        period = connection.execute(
            'SELECT joint_venture_name FROM unit_joint_venture_periods '
            'WHERE unit_id = ? AND ended_at IS NULL ORDER BY started_at DESC, id DESC LIMIT 1',
            (int(unit_id),)
        ).fetchone()
        return str(period['joint_venture_name']).strip() if period else ''

    # Única x Única: uma única empresa com uma única unidade → uso exclusivo
    # daquela estrutura, resolvido pela própria regra UNIT do engine.
    if len(active_units) == 1:
        only_unit = active_units[0]
        return {
            'scope_type': SCOPE_UNIQUE,
            'company_ids': [company_id],
            'unit_ids': [int(only_unit['id'])],
            'unit_id': int(only_unit['id']),
            'joint_venture': '',
        }
    if requested_scope == SCOPE_UNIQUE:
        raise ValueError('Escopo UNIQUE só se aplica quando a empresa possui uma única unidade.')
    if requested_scope not in VALID_APPROVAL_SCOPES:
        raise ValueError('Escopo de aprovação inválido. Use GLOBAL, JOINT_VENTURE ou UNIT.')
    if requested_scope == SCOPE_GLOBAL:
        # GLOBAL na regra existente = EPI sem unit_id e sem JV. Visível para
        # todas as unidades fora de JV; unidades em JV não o enxergam (E3).
        return {
            'scope_type': SCOPE_GLOBAL,
            'company_ids': [company_id],
            'unit_ids': [int(u['id']) for u in active_units],
            'unit_id': None,
            'joint_venture': '',
        }
    if requested_scope == SCOPE_UNIT:
        if not scope_unit_id:
            raise ValueError('Escopo por unidade exige a seleção da unidade.')
        unit = next((u for u in active_units if int(u['id']) == int(scope_unit_id)), None)
        if not unit:
            raise ValueError('Unidade do escopo não encontrada nesta empresa.')
        return {
            'scope_type': SCOPE_UNIT,
            'company_ids': [company_id],
            'unit_ids': [int(unit['id'])],
            'unit_id': int(unit['id']),
            'joint_venture': '',
        }
    # JOINT_VENTURE — a fonte de verdade é o período ativo da unidade em
    # unit_joint_venture_periods; o EPI fica vinculado a uma unidade
    # participante e todas as unidades com a mesma JV ativa o enxergam.
    if not scope_joint_venture:
        raise ValueError('Escopo Joint Venture exige o nome da operação compartilhada.')
    jv_norm = scope_joint_venture.lower()
    participating = [
        u for u in active_units
        if _active_jv_name(u['id']).lower() == jv_norm
    ]
    if not participating:
        raise ValueError(
            'Nenhuma unidade desta empresa possui período ativo nesta Joint Venture. '
            'Vincule a JV à unidade antes de homologar com este escopo.'
        )
    if scope_unit_id:
        jv_unit = next((u for u in participating if int(u['id']) == int(scope_unit_id)), None)
        if not jv_unit:
            raise ValueError('A unidade selecionada não participa desta Joint Venture.')
    else:
        jv_unit = participating[0]
    return {
        'scope_type': SCOPE_JOINT_VENTURE,
        'company_ids': [company_id],
        'unit_ids': [int(u['id']) for u in participating],
        'unit_id': int(jv_unit['id']),
        'joint_venture': scope_joint_venture,
    }


# ── Decisão final ─────────────────────────────────────────────────────────────

def apply_decision(connection, actor, candidate_id, payload):
    """Decisão técnica formal (seção 15). Não homologa — apenas decide."""
    ensure_permission(actor, PERM_PPE_TEST_DECIDE)
    candidate = _get_candidate(connection, candidate_id, actor)
    _require_status(candidate, {'teste_concluido', 'em_decisao'}, 'registrar decisão')
    decision = str(payload.get('decision') or '').strip()
    if decision not in DECISIONS:
        raise ValueError('Decisão inválida.')
    reason = str(payload.get('reason') or '').strip()
    if not reason:
        raise ValueError('Justificativa da decisão é obrigatória.')
    technical_opinion = str(payload.get('technical_opinion') or '').strip()
    results = compute_test_results(connection, actor, candidate_id, _candidate=candidate)
    if decision in ('aprovar', 'aprovar_com_restricao'):
        if not technical_opinion:
            raise ValueError('Parecer técnico é obrigatório para aprovação.')
        if not results['requirements']['critical_incidents_ok']:
            raise ValueError('Há ocorrências críticas sem tratamento. Resolva-as antes de aprovar.')
        override = bool(payload.get('override_minimums'))
        minimums_ok = (results['requirements']['min_participants_ok']
                       and results['requirements']['min_response_rate_ok']
                       and results['requirements']['has_final_evaluations'])
        if not minimums_ok and not override:
            raise ValueError(
                'Critérios mínimos não atendidos (participantes, taxa de resposta ou '
                'avaliações finais). Use a exceção justificada se necessário.'
            )
        if not minimums_ok and override and len(reason) < 10:
            raise ValueError('A exceção aos critérios mínimos exige justificativa detalhada.')
    status_map = {
        'aprovar': 'aprovado',
        'aprovar_com_restricao': 'aprovado',
        'prorrogar_teste': 'em_teste',
        'nova_rodada': 'aprovado_para_teste',
        'solicitar_ajuste_fornecedor': 'em_decisao',
        'rejeitar': 'reprovado',
        'arquivar': 'arquivado',
    }
    new_status = status_map[decision]
    now = _now()
    if decision == 'prorrogar_teste':
        new_end = str(payload.get('new_end_date') or '').strip()
        if not new_end:
            raise ValueError('Prorrogação exige nova data final do teste.')
        connection.execute(
            'UPDATE ppe_test_plans SET end_date=?, updated_at=? WHERE candidate_id=?',
            (new_end, now, int(candidate_id))
        )
    connection.execute(
        '''UPDATE ppe_test_candidates SET status=?, decision=?, decision_reason=?,
           decision_by_user_id=?, decision_by_name=?, decision_at=?,
           technical_opinion=?, operational_opinion=?, purchasing_opinion=?,
           decision_restrictions=?, decision_conditions=?, approval_validity=?, updated_at=?
           WHERE id=?''',
        (
            new_status, decision, reason, int(actor['id']), actor['full_name'], now,
            technical_opinion,
            str(payload.get('operational_opinion') or '').strip(),
            str(payload.get('purchasing_opinion') or '').strip(),
            str(payload.get('restrictions') or '').strip(),
            str(payload.get('conditions') or '').strip(),
            str(payload.get('approval_validity') or '').strip(),
            now, int(candidate_id),
        )
    )
    _record_event(connection, candidate['company_id'], f'decision_{decision}',
                  candidate['status'], new_status, actor, reason=reason,
                  candidate_id=candidate_id)
    return {'ok': True, 'status': new_status, 'decision': decision}


# ── Homologação (entrada no banco oficial) ────────────────────────────────────

def homologate_candidate(connection, actor, candidate_id, payload):
    """Homologação transacional: cria o EPI oficial, aplica escopo e preserva vínculo.

    Executa na mesma transação da conexão (commit é responsabilidade da rota):
    qualquer falha de validação aborta sem efeitos parciais. Idempotência:
    um candidato já homologado (approved_epi_id preenchido) não pode ser
    homologado de novo — impede duplicidade no banco oficial.
    """
    ensure_permission(actor, PERM_PPE_TEST_HOMOLOGATE)
    candidate = _get_candidate(connection, candidate_id, actor)
    _require_status(candidate, {'aprovado'}, 'homologar')
    if candidate.get('approved_epi_id'):
        raise ValueError('Este teste já foi homologado — EPI oficial já criado.')
    if str(candidate.get('decision') or '') not in ('aprovar', 'aprovar_com_restricao'):
        raise ValueError('Homologação exige decisão formal de aprovação.')
    company_id = int(candidate['company_id'])
    scope = resolve_approval_scope(
        connection, company_id,
        payload.get('scope_type'),
        payload.get('scope_unit_id'),
        payload.get('scope_joint_venture'),
    )
    now = _now()
    purchase_code = str(payload.get('purchase_code') or '').strip() or f'EPI-TESTE-{int(candidate_id):05d}'
    ca = str(candidate.get('ca') or '').strip()
    duplicate = connection.execute(
        'SELECT id FROM epis WHERE company_id = ? AND (purchase_code = ? OR (ca != \'\' AND ca = ?))',
        (company_id, purchase_code, ca)
    ).fetchone()
    if duplicate:
        raise ValueError(
            f'Já existe EPI oficial com o mesmo código de compra ou CA (id {duplicate["id"]}). '
            'Homologação bloqueada para impedir duplicidade.'
        )
    jv_name = scope['joint_venture']
    cursor = connection.execute(
        '''INSERT INTO epis
           (company_id, unit_id, name, purchase_code, ca, sector, stock, unit_measure,
            ca_expiry, epi_validity_date, manufacture_date, validity_days,
            manufacturer, model_reference, supplier_company, manufacturer_recommendations,
            epi_photo_data, size, active_joinventure, active,
            origin_test_candidate_id, approval_scope_type, homologated_at)
           VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)''',
        (
            company_id,
            scope['unit_id'],
            str(payload.get('official_name') or candidate['name']).strip(),
            purchase_code,
            ca,
            str(candidate.get('category') or 'Geral').strip() or 'Geral',
            str(candidate.get('unit_measure') or 'un'),
            str(candidate.get('ca_expiry') or ''),
            str(payload.get('epi_validity_date') or ''),
            str(payload.get('manufacture_date') or ''),
            int(payload.get('validity_days') or 0),
            str(candidate.get('manufacturer') or ''),
            str(candidate.get('model_reference') or ''),
            str(candidate.get('supplier') or ''),
            str(candidate.get('restrictions') or ''),
            candidate.get('image_data'),
            str(candidate.get('size') or '') or None,
            jv_name or None,
            int(candidate_id),
            scope['scope_type'],
            now,
        )
    )
    epi_id = cursor.lastrowid
    connection.execute(
        '''UPDATE ppe_test_candidates SET status='homologado', scope_type=?, scope_unit_id=?,
           scope_joint_venture=?, approved_epi_id=?, homologated_at=?, homologated_by_user_id=?,
           homologated_by_name=?, updated_at=? WHERE id=?''',
        (scope['scope_type'], scope['unit_id'], jv_name, epi_id, now,
         int(actor['id']), actor['full_name'], now, int(candidate_id))
    )
    _record_event(connection, company_id, 'homologated', 'aprovado', 'homologado', actor,
                  notes=f'epi_id={epi_id} scope={scope["scope_type"]}',
                  reason=str(payload.get('notes') or ''), candidate_id=candidate_id)
    return {
        'ok': True,
        'status': 'homologado',
        'epi_id': epi_id,
        'scope': {
            'scope_type': scope['scope_type'],
            'company_ids': [str(c) for c in scope['company_ids']],
            'unit_ids': [str(u) for u in scope['unit_ids']],
            'joint_venture_id': jv_name or None,
        },
    }


def reject_candidate(connection, actor, candidate_id, payload):
    """Reprovação (seção 19): bloqueia distribuições e registra destino dos itens."""
    ensure_permission(actor, PERM_PPE_TEST_DECIDE)
    candidate = _get_candidate(connection, candidate_id, actor)
    _require_status(candidate, {'teste_concluido', 'em_decisao', 'aprovado'}, 'reprovar')
    reason = str(payload.get('reason') or '').strip()
    if not reason:
        raise ValueError('Justificativa da reprovação é obrigatória.')
    now = _now()
    connection.execute(
        '''UPDATE ppe_test_candidates SET status='reprovado', decision='rejeitar',
           decision_reason=?, decision_by_user_id=?, decision_by_name=?, decision_at=?, updated_at=?
           WHERE id=?''',
        (reason, int(actor['id']), actor['full_name'], now, now, int(candidate_id))
    )
    disposal = str(payload.get('items_destination') or '').strip()
    if disposal:
        connection.execute(
            '''INSERT INTO ppe_test_distributions
               (candidate_id, company_id, movement_type, quantity, responsible_name,
                disposal_required, notes, created_by_user_id, created_at)
               VALUES (?, ?, 'descarte', 0, ?, 1, ?, ?, ?)''',
            (int(candidate_id), int(candidate['company_id']), actor['full_name'],
             f'Destino pós-reprovação: {disposal}', int(actor['id']), now)
        )
    _record_event(connection, candidate['company_id'], 'rejected',
                  candidate['status'], 'reprovado', actor, reason=reason,
                  candidate_id=candidate_id)
    return {'ok': True, 'status': 'reprovado'}
