"""Rotas de Empresa Terceirizada/Prestadora — Cadastro Simplificado (ADR-014).

Endpoints:
  GET  /api/outsourced-companies                                  → lista da empresa do ator
  GET  /api/outsourced-companies/{id}                              → item único
  POST /api/outsourced-companies                                   → cadastro (Simplificado ou Padrão)
  PUT  /api/outsourced-companies/{id}                               → atualização
  POST /api/outsourced-companies/{id}/promote                      → migração Simplificado → Padrão
  GET  /api/outsourced-companies/{id}/service-contracts             → contratos da empresa
  POST /api/outsourced-companies/{id}/service-contracts             → cadastro de contrato
  GET  /api/outsourced-companies/migration-suggestions              → alerta de sugestão de migração (PR 6)
  GET  /api/epi-reimbursements                                     → lista de ressarcimentos (PR 6)
  POST /api/epi-reimbursements                                     → registro de ressarcimento (PR 6)
  PUT  /api/epi-reimbursements/{id}/status                          → atualização de status (PR 6)

Reaproveita a mesma permissão de criar/ver colaborador (employees:*) — sem
modelo de permissão novo, por decisão explícita do ADR-014. O piso técnico
do módulo "terceirizados" em module_visibility (MODULE_REQUIRED_PERMISSIONS)
aceita employees:create OU employees:create_simplified. A subpasta nasce
oculta por padrão: mesmo quem tem a permissão técnica só vê a tela depois
que o Administrador Geral liga o módulo em Configuração > Regras >
Visualização — e, para Administrador Local/Gestor de EPI, especificamente
para a própria Unidade (ADR-0002 §10.5). `ensure_module_enabled_for_unit`
é a autoridade real (backend), não só o menu: nenhuma rota de escrita abaixo
confia no estado do menu do cliente — mesmo padrão já usado em
modules/employees/routes.py para "Cadastro de Colaboradores" (PR19).

Ressarcimento é registro de apoio para conferência manual — nenhuma rota
aqui dispara cobrança ou integração de pagamento (ADR-0002 §3.6).
"""

from contextlib import closing
from urllib.parse import parse_qs

from core.auth import ensure_company_access
from core.database import get_connection
from core.permissions import (
    PERM_EMPLOYEES_CREATE,
    PERM_EMPLOYEES_CREATE_SIMPLIFIED,
    PERM_EMPLOYEES_UPDATE,
    PERM_EMPLOYEES_UPDATE_SIMPLIFIED,
    PERM_EMPLOYEES_VIEW,
)
from core.repository import authorize_action, authorize_action_any
from core.security import resolve_actor_user_id
from epi_backend.http_utils import require_fields, send_json, structured_log
from modules.outsourced_companies.service import (
    create_outsourced_company,
    create_reimbursement,
    create_service_contract,
    ensure_actor_outsourced_company_scope,
    fetch_archived_outsourced_companies,
    fetch_migration_suggestions,
    fetch_outsourced_companies,
    fetch_outsourced_employees_summary,
    fetch_reimbursements,
    fetch_service_contracts,
    get_outsourced_company_by_id,
    get_outsourced_company_lifecycle,
    get_reimbursement_by_id,
    promote_outsourced_company,
    resolve_outsourced_company_unit_id,
    update_outsourced_company,
    update_reimbursement_status,
)
from modules.settings.service import ensure_module_enabled_for_unit

from core import archival


def _audit(connection, company_id, actor, action_type, summary, details=None):
    try:
        from core.audit import register_company_audit
        register_company_audit(connection, int(company_id), actor, action_type, summary, details or [])
    except Exception as exc:
        structured_log('warning', 'outsourced_company.audit_failed', company_id=company_id, error=str(exc))


# ── GET ───────────────────────────────────────────────────────────────────────

def handle_get_outsourced_companies(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_EMPLOYEES_VIEW)
        data = fetch_outsourced_companies(connection, int(actor['company_id']), actor=actor)
        return send_json(handler, 200, {'outsourced_companies': data, 'items': data})


def handle_get_outsourced_company(handler, parsed, payload, match):
    entity_id = int(match.group(1))
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_EMPLOYEES_VIEW)
        entity = get_outsourced_company_by_id(connection, entity_id)
        if not entity:
            return send_json(handler, 404, {'error': 'Empresa terceirizada não encontrada.'})
        ensure_company_access(actor, entity['company_id'])
        ensure_actor_outsourced_company_scope(connection, actor, entity)
        return send_json(handler, 200, {'outsourced_company': entity})


def handle_get_service_contracts(handler, parsed, payload, match):
    entity_id = int(match.group(1))
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_EMPLOYEES_VIEW)
        entity = get_outsourced_company_by_id(connection, entity_id)
        if not entity:
            return send_json(handler, 404, {'error': 'Empresa terceirizada não encontrada.'})
        ensure_company_access(actor, entity['company_id'])
        ensure_actor_outsourced_company_scope(connection, actor, entity)
        data = fetch_service_contracts(connection, int(actor['company_id']), entity_id)
        return send_json(handler, 200, {'service_contracts': data, 'items': data})


# ── POST ──────────────────────────────────────────────────────────────────────

def handle_post_outsourced_companies(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'legal_name'])
    with closing(get_connection()) as connection:
        actor = authorize_action_any(
            connection, resolve_actor_user_id(handler, parsed, payload),
            (PERM_EMPLOYEES_CREATE, PERM_EMPLOYEES_CREATE_SIMPLIFIED),
        )
        company_id = int(actor['company_id'])
        unit_id = resolve_outsourced_company_unit_id(connection, actor, payload, company_id)
        ensure_module_enabled_for_unit(connection, actor, 'terceirizados', unit_id)
        entity_id = create_outsourced_company(
            connection, payload, company_id, actor_user_id=actor['id'], unit_id=unit_id,
        )
        _audit(
            connection, company_id, actor, 'outsourced_company_created',
            f"Empresa terceirizada cadastrada: {payload.get('legal_name')}.",
            [
                {'field': 'legal_name', 'before': '', 'after': str(payload.get('legal_name') or '')},
                {'field': 'unit_id', 'before': '', 'after': str(unit_id or '')},
            ],
        )
        connection.commit()
        structured_log('info', 'outsourced_company.created', outsourced_company_id=entity_id,
                       company_id=company_id, unit_id=unit_id, actor_user_id=actor['id'])
        return send_json(handler, 201, {'ok': True, 'id': entity_id})


def handle_post_outsourced_company_promote(handler, parsed, payload, match):
    entity_id = int(match.group(1))
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_EMPLOYEES_UPDATE)
        current = get_outsourced_company_by_id(connection, entity_id)
        if not current:
            return send_json(handler, 404, {'error': 'Empresa terceirizada não encontrada.'})
        ensure_company_access(actor, current['company_id'])
        promote_outsourced_company(connection, entity_id, int(current['company_id']))
        _audit(
            connection, current['company_id'], actor, 'outsourced_company_promoted',
            f"Empresa terceirizada promovida ao Cadastro Padrão: {current.get('legal_name')}.",
            [{'field': 'registration_mode', 'before': 'simplified', 'after': 'standard'}],
        )
        connection.commit()
        structured_log('info', 'outsourced_company.promoted', outsourced_company_id=entity_id, actor_user_id=actor['id'])
        return send_json(handler, 200, {'ok': True, 'id': entity_id})


def handle_post_service_contracts(handler, parsed, payload, match):
    entity_id = int(match.group(1))
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_EMPLOYEES_CREATE)
        current = get_outsourced_company_by_id(connection, entity_id)
        if not current:
            return send_json(handler, 404, {'error': 'Empresa terceirizada não encontrada.'})
        ensure_company_access(actor, current['company_id'])
        company_id = int(current['company_id'])
        contract_id = create_service_contract(connection, payload, company_id, entity_id, actor_user_id=actor['id'])
        _audit(
            connection, company_id, actor, 'service_contract_created',
            f"Contrato cadastrado para {current.get('legal_name')}.",
            [{'field': 'contract_ref', 'before': '', 'after': str(payload.get('contract_ref') or '')}],
        )
        connection.commit()
        structured_log('info', 'service_contract.created', service_contract_id=contract_id,
                       outsourced_company_id=entity_id, actor_user_id=actor['id'])
        return send_json(handler, 201, {'ok': True, 'id': contract_id})


# ── PUT ───────────────────────────────────────────────────────────────────────

def handle_put_outsourced_company(handler, parsed, payload, match):
    entity_id = int(match.group(1))
    require_fields(payload, ['actor_user_id', 'legal_name'])
    with closing(get_connection()) as connection:
        actor = authorize_action_any(
            connection, resolve_actor_user_id(handler, parsed, payload),
            (PERM_EMPLOYEES_UPDATE, PERM_EMPLOYEES_UPDATE_SIMPLIFIED),
        )
        current = get_outsourced_company_by_id(connection, entity_id)
        if not current:
            return send_json(handler, 404, {'error': 'Empresa terceirizada não encontrada.'})
        ensure_company_access(actor, current['company_id'])
        ensure_actor_outsourced_company_scope(connection, actor, current)
        # Administrador Local/Gestor de EPI: sempre forçado à própria Unidade
        # (payload ignorado, igual à criação). Demais perfis: só recalcula se
        # o payload realmente mandou `unit_id` — omitir o campo preserva o
        # valor atual (formulário do Cadastro Padrão não tem seletor de
        # Unidade e nunca deve limpar um valor já gravado).
        if actor.get('role') in ('admin', 'user') or 'unit_id' in (payload or {}):
            unit_id = resolve_outsourced_company_unit_id(connection, actor, payload, int(current['company_id']))
        else:
            unit_id = current.get('unit_id')
        ensure_module_enabled_for_unit(connection, actor, 'terceirizados', unit_id)
        update_outsourced_company(connection, entity_id, payload, int(current['company_id']), unit_id=unit_id)
        changes = [
            {'field': field, 'before': str(current.get(field) or ''), 'after': str(payload.get(field) or '')}
            for field in ('legal_name', 'cnpj', 'company_kind', 'epi_responsibility', 'status')
            if str(payload.get(field) or '') != str(current.get(field) or '')
        ]
        if str(unit_id or '') != str(current.get('unit_id') or ''):
            changes.append({'field': 'unit_id', 'before': str(current.get('unit_id') or ''), 'after': str(unit_id or '')})
        _audit(
            connection, current['company_id'], actor, 'outsourced_company_updated',
            f"Empresa terceirizada atualizada: {current.get('legal_name')}.", changes,
        )
        responsibility_change = next((c for c in changes if c['field'] == 'epi_responsibility'), None)
        if responsibility_change:
            # Entrada dedicada (ADR-0002 §5) além do 'outsourced_company_updated'
            # genérico acima — permite filtrar o histórico só por mudança de
            # responsabilidade pelo EPI, sem varrer todo update de cadastro.
            _audit(
                connection, current['company_id'], actor, 'epi_responsibility_changed',
                f"Responsabilidade pelo fornecimento de EPI de {current.get('legal_name')} alterada: "
                f"{responsibility_change['before']} → {responsibility_change['after']}.",
                [responsibility_change],
            )
        connection.commit()
        structured_log('info', 'outsourced_company.updated', outsourced_company_id=entity_id, actor_user_id=actor['id'])
        return send_json(handler, 200, {'ok': True, 'id': entity_id})


# ── Alerta de sugestão de migração (PR 6) ──────────────────────────────────

def handle_get_migration_suggestions(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_EMPLOYEES_VIEW)
        data = fetch_migration_suggestions(connection, int(actor['company_id']))
        return send_json(handler, 200, {'migration_suggestions': data, 'items': data})


# ── Relatórios (PR 13, ADR-0002 §10) ────────────────────────────────────────

def handle_get_outsourced_employees_summary(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_EMPLOYEES_VIEW)
        data = fetch_outsourced_employees_summary(connection, int(actor['company_id']), actor=actor)
        return send_json(handler, 200, {'outsourced_employees_summary': data, 'items': data})


# ── Ressarcimento (PR 6) ────────────────────────────────────────────────────

def handle_get_reimbursements(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_EMPLOYEES_VIEW)
        query = parse_qs(parsed.query)
        outsourced_company_id = (query.get('outsourced_company_id') or [None])[0]
        status = (query.get('status') or [None])[0]
        data = fetch_reimbursements(
            connection, int(actor['company_id']),
            outsourced_company_id=int(outsourced_company_id) if outsourced_company_id else None,
            status=status,
        )
        return send_json(handler, 200, {'epi_reimbursements': data, 'items': data})


def handle_post_reimbursements(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'delivery_id', 'outsourced_company_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_EMPLOYEES_CREATE)
        company_id = int(actor['company_id'])
        reimbursement_id = create_reimbursement(connection, payload, company_id, actor_user_id=actor['id'])
        _audit(
            connection, company_id, actor, 'epi_reimbursement_recorded',
            f"Ressarcimento registrado para a entrega #{payload.get('delivery_id')}.",
            [{'field': 'total_value', 'before': '', 'after': str(payload.get('total_value') or '')}],
        )
        connection.commit()
        structured_log('info', 'epi_reimbursement.created', reimbursement_id=reimbursement_id,
                       company_id=company_id, actor_user_id=actor['id'])
        return send_json(handler, 201, {'ok': True, 'id': reimbursement_id})


def handle_put_reimbursement_status(handler, parsed, payload, match):
    reimbursement_id = int(match.group(1))
    require_fields(payload, ['actor_user_id', 'status'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_EMPLOYEES_UPDATE)
        current = get_reimbursement_by_id(connection, reimbursement_id)
        if not current:
            return send_json(handler, 404, {'error': 'Ressarcimento não encontrado.'})
        ensure_company_access(actor, current['company_id'])
        new_status = update_reimbursement_status(connection, reimbursement_id, current['company_id'], payload['status'])
        _audit(
            connection, current['company_id'], actor, 'epi_reimbursement_status_changed',
            f"Status de ressarcimento #{reimbursement_id} alterado.",
            [{'field': 'status', 'before': current.get('status') or '', 'after': new_status}],
        )
        connection.commit()
        structured_log('info', 'epi_reimbursement.status_changed', reimbursement_id=reimbursement_id, actor_user_id=actor['id'])
        return send_json(handler, 200, {'ok': True, 'id': reimbursement_id, 'status': new_status})


# ── Arquivamento (Soft Delete) — mesma política de Colaboradores/Unidades ────

_OUTSOURCED_COMPANY_ARCHIVAL = dict(entity_label='Empresa terceirizada', audit_prefix='outsourced_company')


def _load_outsourced_company_for_lifecycle(connection, handler, parsed, payload, match, permissions):
    actor = authorize_action_any(connection, resolve_actor_user_id(handler, parsed, payload), permissions)
    entity = get_outsourced_company_lifecycle(connection, int(match.group(1)))
    if not entity:
        raise ValueError('Empresa terceirizada não encontrada.')
    ensure_company_access(actor, entity['company_id'])
    ensure_actor_outsourced_company_scope(connection, actor, entity)
    ensure_module_enabled_for_unit(connection, actor, 'terceirizados', entity.get('unit_id'))
    return actor, entity


def handle_get_archived_outsourced_companies(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_EMPLOYEES_VIEW)
        data = fetch_archived_outsourced_companies(connection, actor)
        return send_json(handler, 200, {'outsourced_companies': data, 'items': data})


def handle_post_outsourced_company_archive(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor, entity = _load_outsourced_company_for_lifecycle(
            connection, handler, parsed, payload, match, (PERM_EMPLOYEES_UPDATE, PERM_EMPLOYEES_UPDATE_SIMPLIFIED),
        )
        result = archival.archive_record(
            connection, 'outsourced_companies', entity, actor,
            record_label=entity['legal_name'],
            reason=str((payload or {}).get('reason') or ''),
            **_OUTSOURCED_COMPANY_ARCHIVAL,
        )
        connection.commit()
        structured_log('info', 'outsourced_company.archived', outsourced_company_id=entity['id'], actor_user_id=actor['id'])
        return send_json(handler, 200, {'ok': True, 'archived': True, **result})


def handle_post_outsourced_company_restore(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor, entity = _load_outsourced_company_for_lifecycle(
            connection, handler, parsed, payload, match, (PERM_EMPLOYEES_UPDATE, PERM_EMPLOYEES_UPDATE_SIMPLIFIED),
        )
        archival.restore_record(
            connection, 'outsourced_companies', entity, actor,
            record_label=entity['legal_name'],
            **_OUTSOURCED_COMPANY_ARCHIVAL,
        )
        connection.commit()
        structured_log('info', 'outsourced_company.restored', outsourced_company_id=entity['id'], actor_user_id=actor['id'])
        return send_json(handler, 200, {'ok': True, 'status': 'active'})


def handle_delete_outsourced_company(handler, parsed, payload, match):
    """Política de retenção: DELETE não remove — arquiva (soft delete)."""
    with closing(get_connection()) as connection:
        actor, entity = _load_outsourced_company_for_lifecycle(
            connection, handler, parsed, payload, match, (PERM_EMPLOYEES_UPDATE, PERM_EMPLOYEES_UPDATE_SIMPLIFIED),
        )
        reason = str(parse_qs(parsed.query).get('reason', [''])[0] or '')
        result = archival.archive_record(
            connection, 'outsourced_companies', entity, actor,
            record_label=entity['legal_name'], reason=reason,
            **_OUTSOURCED_COMPANY_ARCHIVAL,
        )
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'archived': True, **result})


def register_routes(router):
    router.register('GET',  '/api/outsourced-companies/migration-suggestions',               handle_get_migration_suggestions)
    router.register('GET',  '/api/outsourced-companies/employees-summary',                   handle_get_outsourced_employees_summary)
    router.register('GET',  '/api/outsourced-companies/archived',                            handle_get_archived_outsourced_companies)
    router.register('GET',  '/api/outsourced-companies',                                    handle_get_outsourced_companies)
    router.register('GET',  r'^/api/outsourced-companies/(\d+)$',                            handle_get_outsourced_company, regex=True)
    router.register('GET',  r'^/api/outsourced-companies/(\d+)/service-contracts$',          handle_get_service_contracts, regex=True)
    router.register('POST', '/api/outsourced-companies',                                     handle_post_outsourced_companies)
    router.register('POST', r'^/api/outsourced-companies/(\d+)/promote$',                    handle_post_outsourced_company_promote, regex=True)
    router.register('POST', r'^/api/outsourced-companies/(\d+)/service-contracts$',          handle_post_service_contracts, regex=True)
    router.register('POST', r'^/api/outsourced-companies/(\d+)/archive$',                    handle_post_outsourced_company_archive, regex=True)
    router.register('POST', r'^/api/outsourced-companies/(\d+)/restore$',                    handle_post_outsourced_company_restore, regex=True)
    router.register('PUT',  r'^/api/outsourced-companies/(\d+)$',                            handle_put_outsourced_company, regex=True)
    router.register('DELETE', r'^/api/outsourced-companies/(\d+)$',                          handle_delete_outsourced_company, regex=True)
    router.register('GET',  '/api/epi-reimbursements',                                       handle_get_reimbursements)
    router.register('POST', '/api/epi-reimbursements',                                       handle_post_reimbursements)
    router.register('PUT',  r'^/api/epi-reimbursements/(\d+)/status$',                       handle_put_reimbursement_status, regex=True)
