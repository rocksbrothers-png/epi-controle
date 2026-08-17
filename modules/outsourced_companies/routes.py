"""Rotas de Empresa Terceirizada/Prestadora — Cadastro Simplificado (ADR-014)
e compartilhamento por tenant + trava pós-promoção (ADR-0002 §12).

Endpoints:
  GET  /api/outsourced-companies                                  → lista da empresa do ator (linked + available)
  GET  /api/outsourced-companies/search?q=                        → busca por nome/razão social (fluxo de vínculo)
  GET  /api/outsourced-companies/{id}                              → item único
  POST /api/outsourced-companies                                   → cadastro (Simplificado ou Padrão)
  PUT  /api/outsourced-companies/{id}                               → atualização (dados corporativos)
  POST /api/outsourced-companies/{id}/promote                      → migração Simplificado → Padrão
  POST /api/outsourced-companies/{id}/link                         → "Vincular à minha unidade"
  POST /api/outsourced-companies/{id}/unit-link/activate           → ativa o vínculo local da Unidade do ator
  POST /api/outsourced-companies/{id}/unit-link/deactivate         → desativa o vínculo local (nunca arquiva o corporativo)
  POST /api/outsourced-companies/{id}/update-requests               → "Solicitar atualização cadastral"
  GET  /api/outsourced-companies/update-requests?status=            → inbox de solicitações (Geral/Registro)
  POST /api/outsourced-companies/update-requests/{id}/resolve       → resolve/dispensa uma solicitação
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

ADR-0002 §12 (compartilhamento por tenant + trava pós-promoção): o cadastro
corporativo é único por tenant, identificado por CNPJ — a Unidade de
origem (`unit_id`) é só metadado histórico, imutável após a criação. Cada
Unidade cria seu próprio vínculo em `outsourced_company_unit_links` para
usar a empresa (ação "Vincular à minha unidade"); `ensure_actor_
outsourced_company_scope` é quem decide, a partir desse vínculo, se o ator
pode ler/editar/arquivar o registro corporativo — não mais a Unidade de
origem sozinha. Uma vez que a empresa é promovida ao Cadastro Padrão
(`registration_mode == 'standard'`), editar dados corporativos e arquivar/
reativar passam a ser exclusivos de Administrador Geral/de Registro
(`ensure_actor_can_edit_outsourced_company_corporate_fields`) — Master fica
de fora por doutrina já documentada (PAPEIS_E_ATRIBUICOES.md #1). O vínculo
local (ativar/desativar) continua liberado para Administrador Local/Gestor
de EPI independente de `registration_mode`: nunca é tratado como
arquivamento global do CNPJ.

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
from core.repository import actor_operational_unit_id, authorize_action, authorize_action_any
from core.security import resolve_actor_user_id
from epi_backend.http_utils import require_fields, send_json, structured_log
from modules.outsourced_companies.service import (
    DuplicateOutsourcedCompanyError,
    annotate_outsourced_company_visibility,
    create_outsourced_company,
    create_outsourced_company_unit_link,
    create_outsourced_company_update_request,
    create_reimbursement,
    create_service_contract,
    ensure_actor_can_edit_outsourced_company_corporate_fields,
    ensure_actor_outsourced_company_scope,
    fetch_archived_outsourced_companies,
    fetch_migration_suggestions,
    fetch_outsourced_companies,
    fetch_outsourced_company_unit_link,
    fetch_outsourced_company_update_requests,
    fetch_outsourced_employees_summary,
    fetch_reimbursements,
    fetch_service_contracts,
    get_outsourced_company_by_id,
    get_outsourced_company_lifecycle,
    get_outsourced_company_update_request_by_id,
    get_reimbursement_by_id,
    promote_outsourced_company,
    resolve_outsourced_company_unit_id,
    resolve_outsourced_company_update_request,
    search_outsourced_companies_by_name,
    set_outsourced_company_unit_link_status,
    summarize_outsourced_company_history,
    purge_outsourced_company_history,
    update_outsourced_company,
    update_reimbursement_status,
)
from modules.settings.service import ensure_module_enabled_for_unit

from core import archival


def _client_ip(handler):
    return str(getattr(handler, 'client_address', ('',))[0] or '')


def _require_deletion_admin(actor):
    if actor.get('role') not in ('general_admin', 'registry_admin'):
        raise PermissionError(
            'Apenas Administrador Geral ou Administrador de Registro podem gerenciar a exclusão definitiva.'
        )


def _audit(connection, company_id, actor, action_type, summary, details=None):
    try:
        from core.audit import register_company_audit
        register_company_audit(connection, int(company_id), actor, action_type, summary, details or [])
    except Exception as exc:
        structured_log('warning', 'outsourced_company.audit_failed', company_id=company_id, error=str(exc))


def _module_gate_unit_id(connection, actor, entity_unit_id):
    """Unidade usada para checar `ensure_module_enabled_for_unit`: para
    Administrador Local/Gestor de EPI é sempre a PRÓPRIA unidade operacional
    (o gate é sobre quem está agindo, não sobre a Unidade de origem —
    imutável e possivelmente diferente da Unidade do ator desde o
    compartilhamento por tenant, ADR-0002 §12); para os demais perfis, a
    Unidade de origem do registro (``None`` = empresa do tenant)."""
    if actor.get('role') in ('admin', 'user'):
        return actor_operational_unit_id(connection, actor)
    return entity_unit_id


# ── GET ───────────────────────────────────────────────────────────────────────

def handle_get_outsourced_companies(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_EMPLOYEES_VIEW)
        data = fetch_outsourced_companies(connection, int(actor['company_id']), actor=actor)
        return send_json(handler, 200, {
            'outsourced_companies': data['linked'], 'items': data['linked'],
            'available_outsourced_companies': data['available'],
        })


def handle_get_outsourced_company_search(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_EMPLOYEES_VIEW)
        term = (parse_qs(parsed.query).get('q') or [''])[0]
        matches = search_outsourced_companies_by_name(connection, int(actor['company_id']), term)
        if actor.get('role') in ('admin', 'user'):
            scope_unit_id = actor_operational_unit_id(connection, actor)
            matches = annotate_outsourced_company_visibility(connection, matches, scope_unit_id)
        return send_json(handler, 200, {'outsourced_companies': matches, 'items': matches})


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
        # Administrador Local e Gestor de EPI leem só os contratos da própria
        # Unidade (mais os de alcance corporativo). Antes do fluxo de vínculo
        # da #226 isso não aparecia: só a Unidade de origem alcançava a
        # empresa, então não havia uma segunda Unidade para vazar contrato
        # para. Com o vínculo, passa a haver.
        scope_unit_id = (
            actor_operational_unit_id(connection, actor)
            if actor.get('role') in ('admin', 'user') else None
        )
        data = fetch_service_contracts(
            connection, int(actor['company_id']), entity_id, scope_unit_id=scope_unit_id,
        )
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
        # Cadastro Simplificado sem CNPJ ainda: alerta de possível
        # duplicata por nome antes de criar outro registro — o cliente
        # confirma com `confirm_duplicate` para seguir mesmo assim
        # (ADR-0002 §12 item 15). Com CNPJ, a duplicidade é decidida na
        # validação abaixo (DuplicateOutsourcedCompanyError), sempre certa.
        if not str(payload.get('cnpj') or '').strip() and not payload.get('confirm_duplicate'):
            matches = search_outsourced_companies_by_name(connection, company_id, payload.get('legal_name'))
            if matches:
                return send_json(handler, 409, {
                    'error': 'Já existe empresa com nome parecido — confira antes de cadastrar outra.',
                    'code': 'possible_duplicate',
                    'matches': matches,
                })
        try:
            entity_id = create_outsourced_company(
                connection, payload, company_id, actor_user_id=actor['id'], unit_id=unit_id,
            )
        except DuplicateOutsourcedCompanyError as exc:
            return send_json(handler, 409, {
                'error': str(exc), 'code': 'duplicate_cnpj', 'existing_company_id': exc.existing_company_id,
            })
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


# ── Vínculo por Unidade — compartilhamento por tenant (ADR-0002 §12) ──────

def handle_post_outsourced_company_link(handler, parsed, payload, match):
    """"Vincular à minha unidade" — cria (ou reaproveita, se já existir) o
    vínculo local para a Unidade do ator poder usar/gerenciar a empresa,
    sem duplicar o cadastro corporativo."""
    entity_id = int(match.group(1))
    with closing(get_connection()) as connection:
        actor = authorize_action_any(
            connection, resolve_actor_user_id(handler, parsed, payload),
            (PERM_EMPLOYEES_UPDATE, PERM_EMPLOYEES_UPDATE_SIMPLIFIED),
        )
        current = get_outsourced_company_by_id(connection, entity_id)
        if not current:
            return send_json(handler, 404, {'error': 'Empresa terceirizada não encontrada.'})
        ensure_company_access(actor, current['company_id'])
        if actor.get('role') in ('admin', 'user'):
            unit_id = actor_operational_unit_id(connection, actor)
            if not unit_id:
                return send_json(handler, 403, {'error': 'Seu perfil não possui unidade operacional ativa.'})
        else:
            raw = (payload or {}).get('unit_id')
            if not raw:
                return send_json(handler, 400, {'error': 'Informe a Unidade para vincular.'})
            unit_id = int(raw)
        ensure_module_enabled_for_unit(connection, actor, 'terceirizados', unit_id)
        link_id = create_outsourced_company_unit_link(connection, entity_id, int(current['company_id']), unit_id, actor['id'])
        _audit(
            connection, current['company_id'], actor, 'outsourced_company_linked_to_unit',
            f"Empresa terceirizada vinculada à Unidade: {current.get('legal_name')}.",
            [{'field': 'unit_id', 'before': '', 'after': str(unit_id)}],
        )
        connection.commit()
        structured_log('info', 'outsourced_company.linked', outsourced_company_id=entity_id,
                       unit_id=unit_id, actor_user_id=actor['id'])
        return send_json(handler, 201, {'ok': True, 'id': link_id, 'unit_id': unit_id})


def _load_outsourced_company_unit_link(connection, handler, parsed, payload, match):
    entity_id = int(match.group(1))
    actor = authorize_action_any(
        connection, resolve_actor_user_id(handler, parsed, payload),
        (PERM_EMPLOYEES_UPDATE, PERM_EMPLOYEES_UPDATE_SIMPLIFIED),
    )
    current = get_outsourced_company_by_id(connection, entity_id)
    if not current:
        raise ValueError('Empresa terceirizada não encontrada.')
    ensure_company_access(actor, current['company_id'])
    if actor.get('role') in ('admin', 'user'):
        unit_id = actor_operational_unit_id(connection, actor)
    else:
        raw = (payload or {}).get('unit_id')
        unit_id = int(raw) if raw else None
    if not unit_id:
        raise PermissionError('Informe a Unidade do vínculo.')
    link = fetch_outsourced_company_unit_link(connection, entity_id, unit_id)
    if not link:
        raise ValueError('Vínculo não encontrado para esta Unidade — vincule a empresa antes.')
    return actor, current, link


def handle_post_outsourced_company_unit_link_activate(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor, current, link = _load_outsourced_company_unit_link(connection, handler, parsed, payload, match)
        set_outsourced_company_unit_link_status(connection, link['id'], int(current['company_id']), 'active', actor['id'])
        _audit(
            connection, current['company_id'], actor, 'outsourced_company_unit_link_status_changed',
            f"Empresa desarquivada nesta Unidade: {current.get('legal_name')}.",
            [
                {'field': 'local_status', 'before': link.get('local_status') or '', 'after': 'active'},
                {'field': 'unit_id', 'before': '', 'after': str(link.get('unit_id') or '')},
                {'field': 'actor_role', 'before': '', 'after': str(actor.get('role') or '')},
            ],
        )
        connection.commit()
        structured_log('info', 'outsourced_company.unit_link_activated', outsourced_company_id=current['id'], actor_user_id=actor['id'])
        return send_json(handler, 200, {'ok': True, 'local_status': 'active'})


def handle_post_outsourced_company_unit_link_deactivate(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor, current, link = _load_outsourced_company_unit_link(connection, handler, parsed, payload, match)
        reason = str((payload or {}).get('reason') or '')
        set_outsourced_company_unit_link_status(
            connection, link['id'], int(current['company_id']), 'inactive', actor['id'], reason=reason,
        )
        _audit(
            connection, current['company_id'], actor, 'outsourced_company_unit_link_status_changed',
            f"Empresa arquivada nesta Unidade: {current.get('legal_name')}.",
            [
                {'field': 'local_status', 'before': link.get('local_status') or '', 'after': 'inactive'},
                {'field': 'unit_id', 'before': '', 'after': str(link.get('unit_id') or '')},
                {'field': 'actor_role', 'before': '', 'after': str(actor.get('role') or '')},
                {'field': 'reason', 'before': '', 'after': reason},
            ],
        )
        connection.commit()
        structured_log('info', 'outsourced_company.unit_link_deactivated', outsourced_company_id=current['id'], actor_user_id=actor['id'])
        return send_json(handler, 200, {'ok': True, 'local_status': 'inactive'})


# ── "Solicitar atualização cadastral" (ADR-0002 §12) ───────────────────────

def handle_post_outsourced_company_update_requests(handler, parsed, payload, match):
    entity_id = int(match.group(1))
    require_fields(payload, ['actor_user_id', 'message'])
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
        unit_id = _module_gate_unit_id(connection, actor, current.get('unit_id'))
        request_id = create_outsourced_company_update_request(
            connection, entity_id, int(current['company_id']), unit_id, actor, payload.get('message'),
        )
        _audit(
            connection, current['company_id'], actor, 'outsourced_company_update_requested',
            f"Atualização cadastral solicitada: {current.get('legal_name')}.",
            [{'field': 'message', 'before': '', 'after': str(payload.get('message') or '')}],
        )
        connection.commit()
        structured_log('info', 'outsourced_company.update_requested', outsourced_company_id=entity_id, actor_user_id=actor['id'])
        return send_json(handler, 201, {'ok': True, 'id': request_id})


def handle_get_outsourced_company_update_requests(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_EMPLOYEES_UPDATE)
        status = (parse_qs(parsed.query).get('status') or [None])[0]
        data = fetch_outsourced_company_update_requests(connection, int(actor['company_id']), status=status)
        return send_json(handler, 200, {'outsourced_company_update_requests': data, 'items': data})


def handle_post_outsourced_company_update_request_resolve(handler, parsed, payload, match):
    request_id = int(match.group(1))
    require_fields(payload, ['actor_user_id', 'status'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_EMPLOYEES_UPDATE)
        current = get_outsourced_company_update_request_by_id(connection, request_id)
        if not current:
            return send_json(handler, 404, {'error': 'Solicitação não encontrada.'})
        ensure_company_access(actor, current['company_id'])
        status = resolve_outsourced_company_update_request(
            connection, request_id, current['company_id'], actor['id'],
            payload['status'], notes=payload.get('resolution_notes'),
        )
        _audit(
            connection, current['company_id'], actor, 'outsourced_company_update_request_resolved',
            f"Solicitação de atualização cadastral #{request_id} resolvida.",
            [{'field': 'status', 'before': current.get('status') or '', 'after': status}],
        )
        connection.commit()
        structured_log('info', 'outsourced_company.update_request_resolved', request_id=request_id, actor_user_id=actor['id'])
        return send_json(handler, 200, {'ok': True, 'id': request_id, 'status': status})


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
        ensure_actor_can_edit_outsourced_company_corporate_fields(actor, current)
        # Unidade de origem (`unit_id`) é imutável após a criação (ADR-0002
        # §11) — não é mais lida do payload; `_module_gate_unit_id` só
        # decide QUAL unidade checar em ensure_module_enabled_for_unit.
        unit_id = _module_gate_unit_id(connection, actor, current.get('unit_id'))
        ensure_module_enabled_for_unit(connection, actor, 'terceirizados', unit_id)
        try:
            update_outsourced_company(connection, entity_id, payload, int(current['company_id']))
        except DuplicateOutsourcedCompanyError as exc:
            return send_json(handler, 409, {
                'error': str(exc), 'code': 'duplicate_cnpj', 'existing_company_id': exc.existing_company_id,
            })
        changes = [
            {'field': field, 'before': str(current.get(field) or ''), 'after': str(payload.get(field) or '')}
            for field in ('legal_name', 'cnpj', 'company_kind', 'epi_responsibility', 'status')
            if str(payload.get(field) or '') != str(current.get(field) or '')
        ]
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
    ensure_actor_can_edit_outsourced_company_corporate_fields(actor, entity)
    unit_id = _module_gate_unit_id(connection, actor, entity.get('unit_id'))
    ensure_module_enabled_for_unit(connection, actor, 'terceirizados', unit_id)
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


def handle_get_outsourced_company_deletion_summary(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor, entity = _load_outsourced_company_for_lifecycle(
            connection, handler, parsed, payload, match, (PERM_EMPLOYEES_UPDATE, PERM_EMPLOYEES_UPDATE_SIMPLIFIED),
        )
        return send_json(handler, 200, {
            'outsourced_company': {
                'id': entity['id'],
                'legal_name': entity['legal_name'],
                'status': entity.get('status'),
                'archived_at': entity.get('archived_at'),
                'retention_until': entity.get('retention_until'),
                'legal_hold': int(entity.get('legal_hold') or 0),
            },
            'records': summarize_outsourced_company_history(connection, int(entity['id'])),
        })


def handle_post_outsourced_company_purge_request(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor, entity = _load_outsourced_company_for_lifecycle(
            connection, handler, parsed, payload, match, (PERM_EMPLOYEES_UPDATE, PERM_EMPLOYEES_UPDATE_SIMPLIFIED),
        )
        _require_deletion_admin(actor)
        summary = archival.request_purge(
            connection, 'outsourced_companies', entity, actor,
            record_label=entity['legal_name'],
            summary=summarize_outsourced_company_history(connection, int(entity['id'])),
            ip=_client_ip(handler), **_OUTSOURCED_COMPANY_ARCHIVAL,
        )
        connection.commit()
        structured_log('info', 'outsourced_company.purge_requested', outsourced_company_id=entity['id'], actor_user_id=actor['id'])
        return send_json(handler, 200, {
            'ok': True,
            'status': 'pending_deletion',
            'records': summary,
            'next_step': 'Confirme a exclusão definitiva com justificativa e o nome exato da empresa.',
        })


def handle_post_outsourced_company_purge_cancel(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor, entity = _load_outsourced_company_for_lifecycle(
            connection, handler, parsed, payload, match, (PERM_EMPLOYEES_UPDATE, PERM_EMPLOYEES_UPDATE_SIMPLIFIED),
        )
        _require_deletion_admin(actor)
        archival.cancel_purge(
            connection, 'outsourced_companies', entity, actor,
            record_label=entity['legal_name'], ip=_client_ip(handler), **_OUTSOURCED_COMPANY_ARCHIVAL,
        )
        connection.commit()
        structured_log('info', 'outsourced_company.purge_cancelled', outsourced_company_id=entity['id'], actor_user_id=actor['id'])
        return send_json(handler, 200, {'ok': True, 'status': 'archived'})


def handle_post_outsourced_company_purge_confirm(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'justification', 'confirm_name'])
    with closing(get_connection()) as connection:
        actor, entity = _load_outsourced_company_for_lifecycle(
            connection, handler, parsed, payload, match, (PERM_EMPLOYEES_UPDATE, PERM_EMPLOYEES_UPDATE_SIMPLIFIED),
        )
        _require_deletion_admin(actor)
        summary = archival.confirm_purge(
            connection, 'outsourced_companies', entity, actor,
            record_label=entity['legal_name'],
            justification=payload.get('justification'),
            confirm_name=payload.get('confirm_name'),
            summary=summarize_outsourced_company_history(connection, int(entity['id'])),
            purge_history=purge_outsourced_company_history,
            ip=_client_ip(handler), **_OUTSOURCED_COMPANY_ARCHIVAL,
        )
        connection.commit()
        structured_log('info', 'outsourced_company.purged', outsourced_company_id=entity['id'], actor_user_id=actor['id'])
        return send_json(handler, 200, {'ok': True, 'status': 'deleted', 'records_removed': summary})


def register_routes(router):
    router.register('GET',  '/api/outsourced-companies/migration-suggestions',               handle_get_migration_suggestions)
    router.register('GET',  '/api/outsourced-companies/employees-summary',                   handle_get_outsourced_employees_summary)
    router.register('GET',  '/api/outsourced-companies/archived',                            handle_get_archived_outsourced_companies)
    router.register('GET',  '/api/outsourced-companies/search',                              handle_get_outsourced_company_search)
    router.register('GET',  '/api/outsourced-companies/update-requests',                     handle_get_outsourced_company_update_requests)
    router.register('GET',  '/api/outsourced-companies',                                    handle_get_outsourced_companies)
    router.register('GET',  r'^/api/outsourced-companies/(\d+)$',                            handle_get_outsourced_company, regex=True)
    router.register('GET',  r'^/api/outsourced-companies/(\d+)/service-contracts$',          handle_get_service_contracts, regex=True)
    router.register('POST', '/api/outsourced-companies',                                     handle_post_outsourced_companies)
    router.register('POST', r'^/api/outsourced-companies/(\d+)/promote$',                    handle_post_outsourced_company_promote, regex=True)
    router.register('POST', r'^/api/outsourced-companies/(\d+)/link$',                       handle_post_outsourced_company_link, regex=True)
    router.register('POST', r'^/api/outsourced-companies/(\d+)/unit-link/activate$',         handle_post_outsourced_company_unit_link_activate, regex=True)
    router.register('POST', r'^/api/outsourced-companies/(\d+)/unit-link/deactivate$',       handle_post_outsourced_company_unit_link_deactivate, regex=True)
    router.register('POST', r'^/api/outsourced-companies/(\d+)/update-requests$',            handle_post_outsourced_company_update_requests, regex=True)
    router.register('POST', r'^/api/outsourced-companies/update-requests/(\d+)/resolve$',    handle_post_outsourced_company_update_request_resolve, regex=True)
    router.register('POST', r'^/api/outsourced-companies/(\d+)/service-contracts$',          handle_post_service_contracts, regex=True)
    router.register('POST', r'^/api/outsourced-companies/(\d+)/archive$',                    handle_post_outsourced_company_archive, regex=True)
    router.register('POST', r'^/api/outsourced-companies/(\d+)/restore$',                    handle_post_outsourced_company_restore, regex=True)
    router.register('GET',  r'^/api/outsourced-companies/(\d+)/deletion-summary$',           handle_get_outsourced_company_deletion_summary, regex=True)
    router.register('POST', r'^/api/outsourced-companies/(\d+)/purge-request$',              handle_post_outsourced_company_purge_request, regex=True)
    router.register('POST', r'^/api/outsourced-companies/(\d+)/purge-cancel$',               handle_post_outsourced_company_purge_cancel, regex=True)
    router.register('POST', r'^/api/outsourced-companies/(\d+)/purge-confirm$',              handle_post_outsourced_company_purge_confirm, regex=True)
    router.register('PUT',  r'^/api/outsourced-companies/(\d+)$',                            handle_put_outsourced_company, regex=True)
    router.register('DELETE', r'^/api/outsourced-companies/(\d+)$',                          handle_delete_outsourced_company, regex=True)
    router.register('GET',  '/api/epi-reimbursements',                                       handle_get_reimbursements)
    router.register('POST', '/api/epi-reimbursements',                                       handle_post_reimbursements)
    router.register('PUT',  r'^/api/epi-reimbursements/(\d+)/status$',                       handle_put_reimbursement_status, regex=True)
