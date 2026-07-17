"""Serviços do domínio de avaliações e sugestões de EPI."""

import json as _json
from datetime import datetime, timezone

from core.auth import ensure_permission, ensure_resource_company
from core.permissions import (
    PERM_EPI_EVALUATION_DECIDE,
    PERM_EPI_EVALUATION_VIEW,
    PERM_EPI_FEEDBACK_ADMIN_APPROVE,
    PERM_EPI_FEEDBACK_CLOSE,
    PERM_EPI_FEEDBACK_HSEQ_REVIEW,
    PERM_EPI_FEEDBACK_MANAGER_EVAL,
    PERM_EPI_FEEDBACK_TRIAGE,
    PERM_EPI_SUGGESTION_ACCEPT,
)
from epi_backend.db import row_to_dict

UTC = timezone.utc

EPI_FEEDBACK_STATUSES = {
    'recebido': 'Recebido',
    'em_analise_gestor': 'Em Análise pelo Gestor de EPI',
    'aguardando_hseq': 'Aguardando HSEQ',
    'analise_hseq_concluida': 'Análise HSEQ Concluída',
    'encaminhado_administracao': 'Encaminhado para Administração',
    'aguardando_aprovacao_admin': 'Aguardando Aprovação Administrativa',
    'aprovado': 'Aprovado',
    'reprovado': 'Reprovado',
    'acao_corretiva_aberta': 'Ação Corretiva Aberta',
    'encerrado': 'Encerrado',
    'solicitada_mais_informacao': 'Solicitada Mais Informação',
    # legado
    'pendente': 'Pendente',
    'em análise': 'Em Análise',
    'aprovada': 'Aprovada',
    'rejeitada': 'Reprovada',
    'arquivada': 'Arquivada',
}

EPI_FEEDBACK_TYPES = {'avaliacao', 'sugestao', 'reclamacao', 'elogio'}
EPI_FEEDBACK_PRIORITIES = {'baixa', 'normal', 'alta', 'urgente'}

EPI_FEEDBACK_ADMIN_ACTIONS_SUGGESTION = {
    'aprovar_sugestao', 'reprovar_sugestao', 'solicitar_mais_informacoes',
    'solicitar_analise_hseq', 'transformar_em_cadastro', 'encerrar',
}
EPI_FEEDBACK_ADMIN_ACTIONS_AVALIACAO = {
    'registrar_acao', 'abrir_acao_corretiva', 'encerrar_como_informacao',
    'encaminhar_fornecedor', 'registrar_elogio', 'solicitar_substituicao_epi', 'encerrar',
}

EMPLOYEE_PORTAL_STATUS_LABELS = {
    '': 'Enviada',
    'enviado_gestor': 'Em Análise',
    'enviado_admin': 'Encaminh. Admin',
    'aceito': 'Aceito',
    'recusado': 'Recusado',
    'bem_avaliado': 'Bem Avaliado',
    'mal_avaliado': 'Mal Avaliado',
    'em_reavaliacao_3m': 'Reavaliação 3m',
    'em_reavaliacao_6m': 'Reavaliação 6m',
}

REJECTION_REASON_LABELS = {
    'sem_ca': 'Sem CA aprovado pelo Brasil',
    'fornecedor_nao_aprovado': 'Fornecedor não aprovado',
    'outro': 'Outro motivo',
}

RISK_LEVEL_LABELS = {
    'nenhum': 'Nenhum',
    'baixo': 'Baixo',
    'medio': 'Médio',
    'alto': 'Alto',
}

EPI_RANK_LABELS = {
    'excelente': 'Excelente',
    'otimo': 'Ótimo',
    'muito_bom': 'Muito Bom',
    'ruim': 'Ruim',
    'muito_ruim': 'Muito Ruim',
    'pessimo': 'Péssimo',
    'excelente_sug': 'Excelente Sugestão',
    'otima_sug': 'Ótima Sugestão',
    'muito_boa_sug': 'Muito Boa Sugestão',
    'pessima_sug': 'Péssima Sugestão',
    'muito_ruim_sug': 'Muito Ruim a Sugestão',
    'ruim_sug': 'Ruim a Sugestão',
}


def _record_feedback_history(connection, feedback_id, company_id, action, previous_status, new_status, actor, notes='', reason=''):
    now = datetime.now(UTC).isoformat()
    connection.execute(
        'INSERT INTO epi_feedback_history (feedback_id, company_id, status, notes, actor_user_id, actor_name, actor_role, action, previous_status, reason, created_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            int(feedback_id),
            int(company_id),
            str(new_status),
            str(notes or ''),
            int(actor['id']) if actor else None,
            str(actor.get('full_name') or '') if actor else '',
            str(actor.get('role') or '') if actor else '',
            str(action),
            str(previous_status),
            str(reason or ''),
            now,
        )
    )


def fetch_feedbacks(connection, actor=None):
    clauses = []
    params = []
    if actor and actor['role'] != 'master_admin':
        clauses.append('f.company_id = ?')
        params.append(actor['company_id'])
    final_where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
    rows = connection.execute(
        f'''
        SELECT f.id, f.company_id, f.unit_id, f.employee_id, f.epi_id, f.comfort_rating, f.quality_rating, f.adequacy_rating,
               f.performance_rating, f.comments, f.improvement_suggestion, f.suggested_new_epi_name, f.suggested_new_epi_notes,
               f.status, f.type, f.feedback_subtype, f.reviewer_user_id, f.reviewer_name, f.reviewed_at, f.created_at, f.updated_at,
               companies.name AS company_name, units.name AS unit_name, employees.name AS employee_name,
               epis.name AS epi_name, epis.purchase_code
        FROM epi_feedbacks f
        JOIN companies ON companies.id = f.company_id
        JOIN units ON units.id = f.unit_id
        JOIN employees ON employees.id = f.employee_id
        LEFT JOIN epis ON epis.id = f.epi_id
        {final_where}
        ORDER BY f.created_at DESC, f.id DESC
        ''',
        tuple(params)
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def fetch_feedback_detail(connection, feedback_id, actor):
    row = connection.execute(
        '''
        SELECT f.*, companies.name AS company_name, units.name AS unit_name,
               employees.name AS employee_name, epis.name AS epi_name
        FROM epi_feedbacks f
        JOIN companies ON companies.id = f.company_id
        JOIN units ON units.id = f.unit_id
        JOIN employees ON employees.id = f.employee_id
        LEFT JOIN epis ON epis.id = f.epi_id
        WHERE f.id = ?
        ''',
        (int(feedback_id),)
    ).fetchone()
    if not row:
        raise ValueError('Avaliação/Sugestão não encontrada.')
    feedback = row_to_dict(row)
    ensure_resource_company(actor, feedback, 'Avaliação')
    history = connection.execute(
        'SELECT * FROM epi_feedback_history WHERE feedback_id = ? ORDER BY created_at ASC, id ASC',
        (int(feedback_id),)
    ).fetchall()
    feedback['history'] = [row_to_dict(h) for h in history]
    return feedback


def apply_feedback_triage(connection, actor, feedback_id, payload):
    ensure_permission(actor, PERM_EPI_FEEDBACK_TRIAGE)
    feedback = connection.execute('SELECT * FROM epi_feedbacks WHERE id = ?', (int(feedback_id),)).fetchone()
    if not feedback:
        raise ValueError('Avaliação/Sugestão não encontrada.')
    fb = row_to_dict(feedback)
    ensure_resource_company(actor, fb, 'Avaliação')
    fb_type = str(payload.get('type') or fb.get('type') or 'avaliacao').strip().lower()
    if fb_type not in EPI_FEEDBACK_TYPES:
        raise ValueError('Tipo de feedback inválido.')
    category = str(payload.get('category') or '').strip()
    priority = str(payload.get('priority') or 'normal').strip().lower()
    if priority not in EPI_FEEDBACK_PRIORITIES:
        raise ValueError('Prioridade inválida.')
    hseq_required = bool(payload.get('hseq_required'))
    hseq_user_id = payload.get('hseq_user_id')
    notes = str(payload.get('notes') or '').strip()
    previous_status = str(fb.get('status') or 'pendente')
    new_status = 'aguardando_hseq' if hseq_required else 'em_analise_gestor'
    now = datetime.now(UTC).isoformat()
    connection.execute(
        '''
        UPDATE epi_feedbacks SET type=?, category=?, priority=?, hseq_required=?, hseq_user_id=?,
            assigned_epi_manager_id=?, status=?, reviewer_user_id=?, reviewer_name=?, reviewed_at=?, updated_at=?
        WHERE id=?
        ''',
        (
            fb_type, category, priority, int(hseq_required),
            int(hseq_user_id) if hseq_user_id else None,
            int(actor['id']),
            new_status, int(actor['id']), actor['full_name'], now, now,
            int(feedback_id),
        )
    )
    _record_feedback_history(connection, feedback_id, fb['company_id'], 'triage', previous_status, new_status, actor, notes)
    return {'ok': True, 'status': new_status}


def apply_feedback_hseq_review(connection, actor, feedback_id, payload):
    ensure_permission(actor, PERM_EPI_FEEDBACK_HSEQ_REVIEW)
    feedback = connection.execute('SELECT * FROM epi_feedbacks WHERE id = ?', (int(feedback_id),)).fetchone()
    if not feedback:
        raise ValueError('Avaliação/Sugestão não encontrada.')
    fb = row_to_dict(feedback)
    ensure_resource_company(actor, fb, 'Avaliação')
    hseq_opinion = str(payload.get('hseq_opinion') or '').strip()
    if not hseq_opinion:
        raise ValueError('Parecer HSEQ é obrigatório.')
    notes = str(payload.get('notes') or '').strip()
    previous_status = str(fb.get('status') or '')
    new_status = 'analise_hseq_concluida'
    now = datetime.now(UTC).isoformat()
    connection.execute(
        'UPDATE epi_feedbacks SET hseq_user_id=?, hseq_opinion=?, hseq_analyzed_at=?, status=?, updated_at=? WHERE id=?',
        (int(actor['id']), hseq_opinion, now, new_status, now, int(feedback_id))
    )
    _record_feedback_history(connection, feedback_id, fb['company_id'], 'hseq_review', previous_status, new_status, actor, notes)
    return {'ok': True, 'status': new_status}


def apply_feedback_forward_admin(connection, actor, feedback_id, payload):
    ensure_permission(actor, PERM_EPI_FEEDBACK_TRIAGE)
    feedback = connection.execute('SELECT * FROM epi_feedbacks WHERE id = ?', (int(feedback_id),)).fetchone()
    if not feedback:
        raise ValueError('Avaliação/Sugestão não encontrada.')
    fb = row_to_dict(feedback)
    ensure_resource_company(actor, fb, 'Avaliação')
    notes = str(payload.get('notes') or '').strip()
    previous_status = str(fb.get('status') or '')
    new_status = 'aguardando_aprovacao_admin'
    now = datetime.now(UTC).isoformat()
    connection.execute(
        "UPDATE epi_feedbacks SET status=?, updated_at=? WHERE id=?",
        (new_status, now, int(feedback_id))
    )
    _record_feedback_history(connection, feedback_id, fb['company_id'], 'forward_admin', previous_status, new_status, actor, notes)
    return {'ok': True, 'status': new_status}


def apply_feedback_admin_decision(connection, actor, feedback_id, payload):
    ensure_permission(actor, PERM_EPI_FEEDBACK_ADMIN_APPROVE)
    feedback = connection.execute('SELECT * FROM epi_feedbacks WHERE id = ?', (int(feedback_id),)).fetchone()
    if not feedback:
        raise ValueError('Avaliação/Sugestão não encontrada.')
    fb = row_to_dict(feedback)
    ensure_resource_company(actor, fb, 'Avaliação')
    fb_type = str(fb.get('type') or 'avaliacao').strip()
    decision = str(payload.get('decision') or '').strip()
    if fb_type == 'sugestao':
        valid_decisions = EPI_FEEDBACK_ADMIN_ACTIONS_SUGGESTION
    else:
        valid_decisions = EPI_FEEDBACK_ADMIN_ACTIONS_AVALIACAO
    if not decision:
        raise ValueError('A decisão administrativa é obrigatória.')
    if decision not in valid_decisions:
        raise ValueError('Decisão administrativa inválida para este tipo de feedback.')
    justification = str(payload.get('justification') or '').strip()
    if not justification:
        raise ValueError('Justificativa é obrigatória para decisão administrativa.')
    notes = str(payload.get('notes') or '').strip()
    previous_status = str(fb.get('status') or '')
    status_map = {
        'aprovar_sugestao': 'aprovado',
        'reprovar_sugestao': 'reprovado',
        'abrir_acao_corretiva': 'acao_corretiva_aberta',
        'encerrar': 'encerrado',
        'encerrar_como_informacao': 'encerrado',
        'solicitar_mais_informacoes': 'solicitada_mais_informacao',
        'solicitar_analise_hseq': 'aguardando_hseq',
    }
    new_status = status_map.get(decision, 'encerrado')
    now = datetime.now(UTC).isoformat()
    connection.execute(
        '''
        UPDATE epi_feedbacks SET admin_decision=?, admin_decision_by_user_id=?, admin_decision_by_name=?,
            admin_decision_at=?, final_justification=?, status=?, updated_at=?
        WHERE id=?
        ''',
        (decision, int(actor['id']), actor['full_name'], now, justification, new_status, now, int(feedback_id))
    )
    _record_feedback_history(connection, feedback_id, fb['company_id'], decision, previous_status, new_status, actor, notes, reason=justification)
    return {'ok': True, 'status': new_status, 'decision': decision}


def apply_feedback_close(connection, actor, feedback_id, payload):
    ensure_permission(actor, PERM_EPI_FEEDBACK_CLOSE)
    feedback = connection.execute('SELECT * FROM epi_feedbacks WHERE id = ?', (int(feedback_id),)).fetchone()
    if not feedback:
        raise ValueError('Avaliação/Sugestão não encontrada.')
    fb = row_to_dict(feedback)
    ensure_resource_company(actor, fb, 'Avaliação')
    notes = str(payload.get('notes') or '').strip()
    previous_status = str(fb.get('status') or '')
    now = datetime.now(UTC).isoformat()
    connection.execute(
        "UPDATE epi_feedbacks SET status='encerrado', updated_at=? WHERE id=?",
        (now, int(feedback_id))
    )
    _record_feedback_history(connection, feedback_id, fb['company_id'], 'close', previous_status, 'encerrado', actor, notes)
    return {'ok': True, 'status': 'encerrado'}


def fetch_feedbacks_for_manager(connection, actor):
    """Return feedbacks scoped to actor's role and company."""
    clauses = []
    params = []
    role = str(actor.get('role') or '')
    if role != 'master_admin':
        clauses.append('f.company_id = ?')
        params.append(int(actor['company_id']))
    if role in ('epi_manager', 'user'):
        clauses.append("f.status NOT IN ('encerrado', 'reprovado')")
    where_sql = ('WHERE ' + ' AND '.join(clauses)) if clauses else ''
    rows = connection.execute(
        f'''
        SELECT f.*, companies.name AS company_name, units.name AS unit_name,
               employees.name AS employee_name, epis.name AS epi_name
        FROM epi_feedbacks f
        JOIN companies ON companies.id = f.company_id
        JOIN units ON units.id = f.unit_id
        JOIN employees ON employees.id = f.employee_id
        LEFT JOIN epis ON epis.id = f.epi_id
        {where_sql}
        ORDER BY f.created_at DESC, f.id DESC
        ''',
        tuple(params)
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def apply_feedback_manager_validate(connection, actor, feedback_id, payload):
    ensure_permission(actor, PERM_EPI_FEEDBACK_MANAGER_EVAL)
    feedback = connection.execute('SELECT * FROM epi_feedbacks WHERE id = ?', (int(feedback_id),)).fetchone()
    if not feedback:
        raise ValueError('Avaliação não encontrada.')
    fb = row_to_dict(feedback)
    ensure_resource_company(actor, fb, 'Avaliação')
    notes = str(payload.get('notes') or '').strip()
    feedback_subtype = str(payload.get('feedback_subtype') or fb.get('feedback_subtype') or '').strip()
    risk_level = str(payload.get('risk_level') or 'nenhum').strip()
    epi_rank = str(payload.get('epi_rank') or '').strip()
    if epi_rank and epi_rank not in EPI_RANK_LABELS:
        epi_rank = ''
    previous_status = str(fb.get('status') or 'pendente')
    new_status = 'aguardando_aprovacao_admin'
    portal_status = 'enviado_admin'
    portal_message = 'Sua avaliação foi validada pelo Gestor de EPI e encaminhada ao responsável para análise.'
    now = datetime.now(UTC).isoformat()
    connection.execute(
        '''UPDATE epi_feedbacks SET manager_eval_status=?, manager_eval_notes=?, manager_eval_at=?,
           feedback_subtype=?, risk_level=?, epi_rank=?, employee_portal_status=?, employee_portal_message=?,
           status=?, reviewer_user_id=?, reviewer_name=?, reviewed_at=?, updated_at=?
           WHERE id=?''',
        ('validado', notes, now, feedback_subtype, risk_level, epi_rank, portal_status, portal_message,
         new_status, int(actor['id']), actor['full_name'], now, now, int(feedback_id))
    )
    _record_feedback_history(connection, feedback_id, fb['company_id'], 'manager_validate', previous_status, new_status, actor, notes)
    return {'ok': True, 'status': new_status}


def apply_feedback_manager_reject(connection, actor, feedback_id, payload):
    ensure_permission(actor, PERM_EPI_FEEDBACK_MANAGER_EVAL)
    feedback = connection.execute('SELECT * FROM epi_feedbacks WHERE id = ?', (int(feedback_id),)).fetchone()
    if not feedback:
        raise ValueError('Avaliação não encontrada.')
    fb = row_to_dict(feedback)
    ensure_resource_company(actor, fb, 'Avaliação')
    rejection_reason = str(payload.get('rejection_reason') or 'outro').strip()
    if rejection_reason not in ('sem_ca', 'fornecedor_nao_aprovado', 'outro'):
        rejection_reason = 'outro'
    supplier_eval_requested = bool(payload.get('supplier_eval_requested'))
    notes = str(payload.get('notes') or '').strip()
    previous_status = str(fb.get('status') or 'pendente')
    new_status = 'encerrado'
    reason_label = REJECTION_REASON_LABELS.get(rejection_reason, rejection_reason)
    portal_message = f'Sua avaliação foi analisada pelo Gestor de EPI. Motivo: {reason_label}.'
    if supplier_eval_requested:
        portal_message += ' Uma avaliação de fornecedor foi solicitada.'
    now = datetime.now(UTC).isoformat()
    connection.execute(
        '''UPDATE epi_feedbacks SET manager_eval_status=?, manager_eval_notes=?, manager_eval_at=?,
           rejection_reason=?, supplier_eval_requested=?, employee_portal_status=?, employee_portal_message=?,
           status=?, reviewer_user_id=?, reviewer_name=?, reviewed_at=?, updated_at=?
           WHERE id=?''',
        ('rejeitado_gestor', notes, now, rejection_reason, int(supplier_eval_requested),
         'recusado', portal_message,
         new_status, int(actor['id']), actor['full_name'], now, now, int(feedback_id))
    )
    _record_feedback_history(connection, feedback_id, fb['company_id'], 'manager_reject', previous_status, new_status, actor, notes, reason=rejection_reason)
    return {'ok': True, 'status': new_status}


def apply_set_reassessment(connection, actor, feedback_id, payload):
    ensure_permission(actor, PERM_EPI_EVALUATION_DECIDE)
    feedback = connection.execute('SELECT * FROM epi_feedbacks WHERE id = ?', (int(feedback_id),)).fetchone()
    if not feedback:
        raise ValueError('Avaliação não encontrada.')
    fb = row_to_dict(feedback)
    ensure_resource_company(actor, fb, 'Avaliação')
    period = str(payload.get('period') or '').strip()
    if period not in ('3_meses', '6_meses'):
        raise ValueError('Período de reavaliação inválido. Use 3_meses ou 6_meses.')
    portal_status = 'em_reavaliacao_3m' if period == '3_meses' else 'em_reavaliacao_6m'
    months = '3' if period == '3_meses' else '6'
    portal_message = f'Sua avaliação foi registrada. Uma nova solução de EPI será analisada em {months} meses.'
    notes = str(payload.get('notes') or '').strip()
    previous_status = str(fb.get('status') or '')
    now = datetime.now(UTC).isoformat()
    connection.execute(
        '''UPDATE epi_feedbacks SET reassessment_period=?, employee_portal_status=?, employee_portal_message=?,
           status=?, updated_at=? WHERE id=?''',
        (period, portal_status, portal_message, 'acao_corretiva_aberta', now, int(feedback_id))
    )
    _record_feedback_history(connection, feedback_id, fb['company_id'], 'set_reassessment', previous_status, 'acao_corretiva_aberta', actor, notes, reason=period)
    return {'ok': True, 'period': period, 'portal_status': portal_status}


def apply_accept_suggestion_as_epi(connection, actor, feedback_id, payload):
    """Aceita a sugestão do colaborador encaminhando-a ao fluxo único de EPI em teste.

    Fluxo unificado: a sugestão aceita NÃO cria mais EPI direto no banco
    oficial. Ela entra no fluxo de Novos EPIs em Teste (triagem → análise
    técnica → teste controlado → decisão formal → homologação) e só chega ao
    banco oficial pela homologação transacional (modules/ppe_tests).
    """
    ensure_permission(actor, PERM_EPI_SUGGESTION_ACCEPT)
    feedback = connection.execute('SELECT * FROM epi_feedbacks WHERE id = ?', (int(feedback_id),)).fetchone()
    if not feedback:
        raise ValueError('Sugestão não encontrada.')
    fb = row_to_dict(feedback)
    ensure_resource_company(actor, fb, 'Sugestão')
    suggested_name = str(fb.get('suggested_new_epi_name') or '').strip()
    if not suggested_name:
        raise ValueError('Esta avaliação não possui sugestão de novo EPI.')
    notes = str(payload.get('notes') or '').strip()
    now = datetime.now(UTC).isoformat()
    from modules.ppe_tests.service import create_suggestion_from_feedback
    test_suggestion = create_suggestion_from_feedback(connection, actor, feedback_id, {
        'notes': notes,
        'risks': str(payload.get('sector') or fb.get('category') or ''),
    })
    connection.execute(
        '''UPDATE epi_feedbacks SET admin_decision='aprovar_sugestao', admin_decision_by_user_id=?,
           admin_decision_by_name=?, admin_decision_at=?, final_justification=?,
           employee_portal_status=?, employee_portal_message=?, status=?, updated_at=? WHERE id=?''',
        (int(actor['id']), actor['full_name'], now, notes,
         'aceito', 'Parabéns! Sua sugestão de EPI foi aceita e entrou no fluxo de teste de novo EPI. '
                   'Após triagem, teste controlado e decisão técnica, ela poderá ser homologada no catálogo oficial.',
         'aprovado', now, int(feedback_id))
    )
    _record_feedback_history(connection, feedback_id, fb['company_id'], 'accept_suggestion', str(fb.get('status') or ''), 'aprovado', actor, notes)
    return {'ok': True, 'new_epi_id': None, 'test_suggestion_id': test_suggestion.get('id')}


def compute_epi_evaluation_status(connection, actor):
    ensure_permission(actor, PERM_EPI_EVALUATION_DECIDE)
    company_id = int(actor['company_id']) if actor.get('role') != 'master_admin' else None
    base_where = 'f.company_id = ? AND' if company_id else ''
    params_base = [company_id] if company_id else []
    rows = connection.execute(
        f'''
        SELECT f.epi_id, e.name as epi_name, e.company_id,
               COUNT(*) as total,
               SUM(CASE WHEN f.feedback_subtype = 'reclamacao' OR f.type = 'reclamacao' THEN 1 ELSE 0 END) as reclamacoes,
               SUM(CASE WHEN f.feedback_subtype = 'elogio' OR f.type = 'elogio' THEN 1 ELSE 0 END) as elogios,
               SUM(CASE WHEN f.feedback_subtype = 'sugestao_nova' OR f.type = 'sugestao' THEN 1 ELSE 0 END) as sugestoes,
               SUM(CASE WHEN f.epi_rank = 'excelente' THEN 1 ELSE 0 END) as rank_excelente,
               SUM(CASE WHEN f.epi_rank = 'otimo' THEN 1 ELSE 0 END) as rank_otimo,
               SUM(CASE WHEN f.epi_rank = 'muito_bom' THEN 1 ELSE 0 END) as rank_muito_bom,
               SUM(CASE WHEN f.epi_rank = 'ruim' THEN 1 ELSE 0 END) as rank_ruim,
               SUM(CASE WHEN f.epi_rank = 'muito_ruim' THEN 1 ELSE 0 END) as rank_muito_ruim,
               SUM(CASE WHEN f.epi_rank = 'pessimo' THEN 1 ELSE 0 END) as rank_pessimo,
               SUM(CASE WHEN f.epi_rank = 'excelente_sug' THEN 1 ELSE 0 END) as rank_excelente_sug,
               SUM(CASE WHEN f.epi_rank = 'otima_sug' THEN 1 ELSE 0 END) as rank_otima_sug,
               SUM(CASE WHEN f.epi_rank = 'muito_boa_sug' THEN 1 ELSE 0 END) as rank_muito_boa_sug,
               SUM(CASE WHEN f.epi_rank = 'pessima_sug' THEN 1 ELSE 0 END) as rank_pessima_sug,
               SUM(CASE WHEN f.epi_rank = 'muito_ruim_sug' THEN 1 ELSE 0 END) as rank_muito_ruim_sug,
               SUM(CASE WHEN f.epi_rank = 'ruim_sug' THEN 1 ELSE 0 END) as rank_ruim_sug,
               AVG(COALESCE(NULLIF(f.comfort_rating, 0), NULL)) as avg_comfort,
               AVG(COALESCE(NULLIF(f.quality_rating, 0), NULL)) as avg_quality,
               AVG(COALESCE(NULLIF(f.adequacy_rating, 0), NULL)) as avg_adequacy,
               AVG(COALESCE(NULLIF(f.performance_rating, 0), NULL)) as avg_performance
        FROM epi_feedbacks f
        JOIN epis e ON e.id = f.epi_id
        WHERE {base_where} f.epi_id IS NOT NULL
          AND f.manager_eval_status = 'validado'
          AND f.status NOT IN ('pendente', 'rejeitado_gestor')
        GROUP BY f.epi_id
        ''',
        tuple(params_base)
    ).fetchall()
    now = datetime.now(UTC).isoformat()
    results = []
    for row in rows:
        data = row_to_dict(row)
        epi_id = data['epi_id']
        epi_company_id = int(data.get('company_id') or (company_id or 0))
        reclamacoes = int(data.get('reclamacoes') or 0)
        elogios = int(data.get('elogios') or 0)
        total = int(data.get('total') or 0)
        score = (elogios - reclamacoes) / max(total, 1) * 100
        if reclamacoes >= 5 or (total > 0 and reclamacoes / total >= 0.6):
            eval_status = 'super_mal_avaliado'
        elif elogios >= 5 or (total > 0 and elogios / total >= 0.6):
            eval_status = 'super_bem_avaliado'
        else:
            eval_status = 'normal'
        connection.execute(
            '''INSERT INTO epi_evaluation_summary
               (company_id, epi_id, epi_name, total_avaliacoes, total_reclamacoes, total_elogios, total_sugestoes,
                avg_comfort, avg_quality, avg_adequacy, avg_performance, score, evaluation_status,
                rank_excelente, rank_otimo, rank_muito_bom, rank_ruim, rank_muito_ruim, rank_pessimo,
                rank_excelente_sug, rank_otima_sug, rank_muito_boa_sug, rank_pessima_sug, rank_muito_ruim_sug, rank_ruim_sug,
                last_computed_at, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(company_id, epi_id) DO UPDATE SET
               epi_name=excluded.epi_name, total_avaliacoes=excluded.total_avaliacoes,
               total_reclamacoes=excluded.total_reclamacoes, total_elogios=excluded.total_elogios,
               total_sugestoes=excluded.total_sugestoes, avg_comfort=excluded.avg_comfort,
               avg_quality=excluded.avg_quality, avg_adequacy=excluded.avg_adequacy,
               avg_performance=excluded.avg_performance, score=excluded.score,
               evaluation_status=excluded.evaluation_status,
               rank_excelente=excluded.rank_excelente, rank_otimo=excluded.rank_otimo,
               rank_muito_bom=excluded.rank_muito_bom, rank_ruim=excluded.rank_ruim,
               rank_muito_ruim=excluded.rank_muito_ruim, rank_pessimo=excluded.rank_pessimo,
               rank_excelente_sug=excluded.rank_excelente_sug, rank_otima_sug=excluded.rank_otima_sug,
               rank_muito_boa_sug=excluded.rank_muito_boa_sug, rank_pessima_sug=excluded.rank_pessima_sug,
               rank_muito_ruim_sug=excluded.rank_muito_ruim_sug, rank_ruim_sug=excluded.rank_ruim_sug,
               last_computed_at=excluded.last_computed_at, updated_at=excluded.updated_at''',
            (epi_company_id, epi_id, data['epi_name'],
             total, reclamacoes, elogios, int(data.get('sugestoes') or 0),
             float(data.get('avg_comfort') or 0), float(data.get('avg_quality') or 0),
             float(data.get('avg_adequacy') or 0), float(data.get('avg_performance') or 0),
             score, eval_status,
             int(data.get('rank_excelente') or 0), int(data.get('rank_otimo') or 0),
             int(data.get('rank_muito_bom') or 0), int(data.get('rank_ruim') or 0),
             int(data.get('rank_muito_ruim') or 0), int(data.get('rank_pessimo') or 0),
             int(data.get('rank_excelente_sug') or 0), int(data.get('rank_otima_sug') or 0),
             int(data.get('rank_muito_boa_sug') or 0), int(data.get('rank_pessima_sug') or 0),
             int(data.get('rank_muito_ruim_sug') or 0), int(data.get('rank_ruim_sug') or 0),
             now, now, now)
        )
        connection.execute(
            "UPDATE epis SET evaluation_status=?, updated_at=? WHERE id=?",
            (eval_status, now, epi_id)
        )
        rank_pos_parts = []
        for k, label in [('rank_excelente', 'Excelente'), ('rank_otimo', 'Ótimo'), ('rank_muito_bom', 'Muito Bom')]:
            v = int(data.get(k) or 0)
            if v > 0:
                rank_pos_parts.append(f'{v}× {label}')
        rank_neg_parts = []
        for k, label in [('rank_pessimo', 'Péssimo'), ('rank_muito_ruim', 'Muito Ruim'), ('rank_ruim', 'Ruim')]:
            v = int(data.get(k) or 0)
            if v > 0:
                rank_neg_parts.append(f'{v}× {label}')
        if eval_status == 'super_bem_avaliado':
            rank_detail = (f' Ranks recebidos: {", ".join(rank_pos_parts)}.' if rank_pos_parts else '')
            bem_msg = f'⭐ EPI Super Bem Avaliado! Score: +{round(score, 1)}.{rank_detail} Obrigado pelo seu feedback — ele ajuda a manter os melhores equipamentos em uso!'
            connection.execute(
                "UPDATE epi_feedbacks SET employee_portal_status='bem_avaliado', employee_portal_message=?"
                " WHERE epi_id=? AND (feedback_subtype='elogio' OR type='elogio')"
                " AND employee_portal_status NOT IN ('aceito', 'recusado')",
                (bem_msg, epi_id)
            )
        elif eval_status == 'super_mal_avaliado':
            rank_detail = (f' Ranks registrados: {", ".join(rank_neg_parts)}.' if rank_neg_parts else '')
            mal_msg = f'⚠ EPI Super Mal Avaliado. Score: {round(score, 1)}.{rank_detail} Suas reclamações foram registradas e o EPI entrará em processo de reavaliação.'
            connection.execute(
                "UPDATE epi_feedbacks SET employee_portal_status='mal_avaliado', employee_portal_message=?"
                " WHERE epi_id=? AND (feedback_subtype='reclamacao' OR type='reclamacao')"
                " AND employee_portal_status NOT IN ('aceito', 'recusado', 'em_reavaliacao_3m', 'em_reavaliacao_6m')",
                (mal_msg, epi_id)
            )
        data['score'] = round(score, 1)
        data['evaluation_status'] = eval_status
        results.append(data)
    return {'ok': True, 'items': results}


def apply_admin_pre_evaluate(connection, actor, feedback_id, payload):
    ensure_permission(actor, PERM_EPI_EVALUATION_DECIDE)
    feedback = connection.execute('SELECT * FROM epi_feedbacks WHERE id = ?', (int(feedback_id),)).fetchone()
    if not feedback:
        raise ValueError('Avaliação não encontrada.')
    fb = row_to_dict(feedback)
    ensure_resource_company(actor, fb, 'Avaliação')
    atende_nr = str(payload.get('atende_nr') or '').strip()
    reduz_risco = str(payload.get('reduz_risco') or '').strip()
    problemas = payload.get('problemas_observados') or []
    if not isinstance(problemas, list):
        problemas = []
    problemas_json = _json.dumps(problemas, ensure_ascii=False)
    custo_estimado = str(payload.get('custo_estimado') or '').strip()
    durabilidade_esperada = str(payload.get('durabilidade_esperada') or '').strip()
    disponibilidade_mercado = str(payload.get('disponibilidade_mercado') or '').strip()
    admin_tech_notes = str(payload.get('admin_tech_notes') or '').strip()
    marca_modelo = str(payload.get('marca_modelo_sugerido') or '').strip()
    pre_recommendation = str(payload.get('pre_recommendation') or 'avaliacao_previa').strip()
    notes = str(payload.get('notes') or '').strip()
    now = datetime.now(UTC).isoformat()
    connection.execute(
        '''
        UPDATE epi_feedbacks SET
            atende_nr=?, reduz_risco=?, problemas_observados=?,
            custo_estimado=?, durabilidade_esperada=?, disponibilidade_mercado=?,
            admin_tech_notes=?, marca_modelo_sugerido=?,
            admin_tech_decision=?,
            employee_portal_status=?,
            updated_at=?, admin_tech_eval_at=?
        WHERE id=?
        ''',
        (atende_nr, reduz_risco, problemas_json,
         custo_estimado, durabilidade_esperada, disponibilidade_mercado,
         admin_tech_notes, marca_modelo,
         pre_recommendation,
         'avaliacao_previa',
         now, now, int(feedback_id))
    )
    _record_feedback_history(connection, feedback_id, fb['company_id'],
                             'admin_pre_evaluate', str(fb.get('status') or ''),
                             'avaliacao_previa', actor, notes)
    return {'ok': True}


def apply_admin_technical_evaluate(connection, actor, feedback_id, payload):
    ensure_permission(actor, PERM_EPI_EVALUATION_DECIDE)
    if str(actor.get('role') or '') != 'general_admin':
        raise PermissionError('Apenas o Administrador Geral pode realizar a Avaliação Final.')
    feedback = connection.execute('SELECT * FROM epi_feedbacks WHERE id = ?', (int(feedback_id),)).fetchone()
    if not feedback:
        raise ValueError('Avaliação não encontrada.')
    fb = row_to_dict(feedback)
    ensure_resource_company(actor, fb, 'Avaliação')
    tech_decision = str(payload.get('tech_decision') or '').strip()
    if tech_decision not in ('aceito', 'recusado'):
        raise ValueError('Decisão técnica obrigatória: aceito ou recusado.')
    atende_nr = str(payload.get('atende_nr') or '').strip()
    reduz_risco = str(payload.get('reduz_risco') or '').strip()
    problemas = payload.get('problemas_observados') or []
    if not isinstance(problemas, list):
        problemas = []
    problemas_json = _json.dumps(problemas, ensure_ascii=False)
    custo_estimado = str(payload.get('custo_estimado') or '').strip()
    durabilidade_esperada = str(payload.get('durabilidade_esperada') or '').strip()
    disponibilidade_mercado = str(payload.get('disponibilidade_mercado') or '').strip()
    admin_tech_notes = str(payload.get('admin_tech_notes') or '').strip()
    marca_modelo = str(payload.get('marca_modelo_sugerido') or '').strip()
    notes = str(payload.get('notes') or '').strip()
    now = datetime.now(UTC).isoformat()
    portal_status = tech_decision
    justification = admin_tech_notes or notes or ''
    if tech_decision == 'aceito':
        portal_message = 'Avaliação técnica concluída — EPI aprovado e registrado.'
        if justification:
            portal_message += f' Justificativa: {justification}'
    else:
        portal_message = 'Avaliação técnica concluída — EPI não aprovado após critérios técnicos.'
        if justification:
            portal_message += f' Justificativa: {justification}'
    connection.execute(
        '''
        UPDATE epi_feedbacks SET
            admin_tech_decision=?, atende_nr=?, reduz_risco=?, problemas_observados=?,
            custo_estimado=?, durabilidade_esperada=?, disponibilidade_mercado=?,
            admin_tech_notes=?, marca_modelo_sugerido=?,
            status=?, employee_portal_status=?, employee_portal_message=?,
            updated_at=?, admin_tech_eval_at=?
        WHERE id=?
        ''',
        (tech_decision, atende_nr, reduz_risco, problemas_json,
         custo_estimado, durabilidade_esperada, disponibilidade_mercado,
         admin_tech_notes, marca_modelo,
         tech_decision, portal_status, portal_message,
         now, now, int(feedback_id))
    )
    _record_feedback_history(connection, feedback_id, fb['company_id'],
                             'admin_technical_evaluate', str(fb.get('status') or ''),
                             tech_decision, actor, notes)
    return {'ok': True}


def fetch_avaliacoes_summary(connection, actor):
    ensure_permission(actor, PERM_EPI_EVALUATION_VIEW)
    company_id = int(actor['company_id']) if actor.get('role') != 'master_admin' else None
    where_clauses = []
    params = []
    if company_id:
        where_clauses.append('f.company_id = ?')
        params.append(company_id)
    where_sql = ('WHERE ' + ' AND '.join(where_clauses)) if where_clauses else ''
    rows = connection.execute(
        f'''
        SELECT f.*, e.name as epi_name, emp.name as employee_name, u.name as unit_name
        FROM epi_feedbacks f
        LEFT JOIN epis e ON e.id = f.epi_id
        JOIN employees emp ON emp.id = f.employee_id
        JOIN units u ON u.id = f.unit_id
        {where_sql}
        ORDER BY f.created_at DESC
        ''',
        tuple(params)
    ).fetchall()
    items = [row_to_dict(r) for r in rows]
    reclamacoes = [i for i in items if i.get('feedback_subtype') == 'reclamacao' or i.get('type') == 'reclamacao']
    elogios = [i for i in items if i.get('feedback_subtype') == 'elogio' or i.get('type') == 'elogio']
    sugestoes = [i for i in items if i.get('feedback_subtype') == 'sugestao_nova' or i.get('type') == 'sugestao']
    risk_counts = {}
    for item in reclamacoes:
        rl = str(item.get('risk_level') or 'nenhum')
        risk_counts[rl] = risk_counts.get(rl, 0) + 1
    epi_complaint_counts = {}
    for item in reclamacoes:
        epi = str(item.get('epi_name') or item.get('epi_id') or 'N/A')
        epi_complaint_counts[epi] = epi_complaint_counts.get(epi, 0) + 1
    epi_elogio_counts = {}
    for item in elogios:
        epi = str(item.get('epi_name') or item.get('epi_id') or 'N/A')
        epi_elogio_counts[epi] = epi_elogio_counts.get(epi, 0) + 1
    top_reclamados = sorted(epi_complaint_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    top_elogiados = sorted(epi_elogio_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    role = str(actor.get('role') or '')
    if role == 'general_admin':
        pendentes_count = len([i for i in items if str(i.get('employee_portal_status') or '') in ('enviado_admin', 'avaliacao_previa')])
    elif role == 'registry_admin':
        pendentes_count = len([i for i in items if str(i.get('employee_portal_status') or '') == 'enviado_admin'])
    else:
        pendentes_count = len([i for i in items if str(i.get('manager_eval_status') or 'pendente') == 'pendente'])
    return {
        'total': len(items),
        'reclamacoes': len(reclamacoes),
        'elogios': len(elogios),
        'sugestoes': len(sugestoes),
        'pendentes': pendentes_count,
        'actor_role': role,
        'risk_breakdown': risk_counts,
        'epi_complaint_counts': epi_complaint_counts,
        'epi_elogio_counts': epi_elogio_counts,
        'top_reclamados': [{'epi_name': k, 'count': v} for k, v in top_reclamados],
        'top_elogiados': [{'epi_name': k, 'count': v} for k, v in top_elogiados],
        'items': items,
        'reclamacao_items': reclamacoes,
        'elogio_items': elogios,
        'sugestao_items': sugestoes,
    }


def fetch_avaliacoes_ranking(connection, actor):
    ensure_permission(actor, PERM_EPI_EVALUATION_VIEW)
    company_id = int(actor['company_id']) if actor.get('role') != 'master_admin' else None
    where_clauses = ['1=1']
    params = []
    if company_id:
        where_clauses.append('s.company_id = ?')
        params.append(company_id)
    where_sql = 'WHERE ' + ' AND '.join(where_clauses)
    rows = connection.execute(
        f'''SELECT s.*, e.ca, e.manufacturer, e.sector
            FROM epi_evaluation_summary s
            JOIN epis e ON e.id = s.epi_id
            {where_sql}
            ORDER BY s.score DESC, s.total_avaliacoes DESC''',
        tuple(params)
    ).fetchall()
    return [row_to_dict(r) for r in rows]


def fetch_suggestion_ranking(connection, actor):
    ensure_permission(actor, PERM_EPI_EVALUATION_VIEW)
    company_id = int(actor['company_id']) if actor.get('role') != 'master_admin' else None
    where_clauses = ["(f.feedback_subtype = 'sugestao_nova' OR f.type = 'sugestao')",
                     "f.epi_rank != ''", "f.manager_eval_status = 'validado'"]
    params = []
    if company_id:
        where_clauses.append('f.company_id = ?')
        params.append(company_id)
    where_sql = 'WHERE ' + ' AND '.join(where_clauses)
    rank_order = ['excelente_sug', 'otima_sug', 'muito_boa_sug', 'pessima_sug', 'muito_ruim_sug', 'ruim_sug']
    rank_score_sql = ' + '.join(
        f"SUM(CASE WHEN f.epi_rank='{r}' THEN {5 - i} ELSE 0 END)"
        for i, r in enumerate(rank_order)
    )
    rows = connection.execute(
        f'''
        SELECT f.suggested_new_epi_name as sugestao_nome,
               f.epi_name as epi_referencia,
               COUNT(*) as total_avaliacoes,
               {rank_score_sql} as score_sugestao,
               SUM(CASE WHEN f.epi_rank='excelente_sug' THEN 1 ELSE 0 END) as rank_excelente_sug,
               SUM(CASE WHEN f.epi_rank='otima_sug' THEN 1 ELSE 0 END) as rank_otima_sug,
               SUM(CASE WHEN f.epi_rank='muito_boa_sug' THEN 1 ELSE 0 END) as rank_muito_boa_sug,
               SUM(CASE WHEN f.epi_rank='pessima_sug' THEN 1 ELSE 0 END) as rank_pessima_sug,
               SUM(CASE WHEN f.epi_rank='muito_ruim_sug' THEN 1 ELSE 0 END) as rank_muito_ruim_sug,
               SUM(CASE WHEN f.epi_rank='ruim_sug' THEN 1 ELSE 0 END) as rank_ruim_sug,
               MIN(f.created_at) as primeira_sugestao,
               MAX(f.employee_portal_status) as portal_status
        FROM epi_feedbacks f
        {where_sql}
        GROUP BY LOWER(TRIM(f.suggested_new_epi_name))
        ORDER BY score_sugestao DESC, total_avaliacoes DESC
        ''',
        tuple(params)
    ).fetchall()
    return [row_to_dict(r) for r in rows]
