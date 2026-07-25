"""Rotas de gestão de LegalEntity (CNPJs da empresa) — Multi-CNPJ / JV.

Endpoints:
  GET  /api/legal-entities                     → lista escopada pelo ator
  GET  /api/legal-entities/{id}                → item único (própria empresa)
  GET  /api/companies/{id}/legal-entities      → CNPJs de uma empresa
  POST /api/legal-entities                     → cadastra um CNPJ
  POST /api/legal-entities/batch               → cadastro em lote (múltiplos CNPJs)
  PUT  /api/legal-entities/{id}                → atualiza um CNPJ

Todas as escritas exigem que o ator pertença à empresa alvo (ou seja Master) e
tenham a permissão legal_entities:*. Nenhuma altera a assinatura SaaS da tenant.
"""

from contextlib import closing

from core.auth import ensure_company_access
from core.database import get_connection
from core.permissions import (
    PERM_LEGAL_ENTITIES_CREATE,
    PERM_LEGAL_ENTITIES_UPDATE,
    PERM_LEGAL_ENTITIES_VIEW,
)
from core.repository import authorize_action
from core.security import resolve_actor_user_id
from epi_backend.http_utils import require_fields, send_json, structured_log
from modules.legal_entities.service import (
    create_legal_entity,
    fetch_legal_entities,
    get_legal_entity_by_id,
    update_legal_entity,
)


def _audit(connection, company_id, actor, action_type, summary, details=None):
    """Registra a alteração de CNPJ na trilha de auditoria da empresa.

    Alterações de pessoa jurídica têm efeito fiscal/trabalhista, logo precisam
    ser auditáveis. Falha de auditoria não desfaz a operação já validada — é
    registrada como aviso estruturado.
    """
    try:
        from modules.companies.service import register_company_audit
        register_company_audit(connection, int(company_id), actor, action_type, summary, details or [])
    except Exception as exc:
        structured_log('warning', 'legal_entity.audit_failed', company_id=company_id, error=str(exc))


def _resolve_company_id(actor, payload):
    """CNPJ é sempre cadastrado sob uma empresa. Master informa company_id no
    payload; os demais papéis operam sempre sob a própria empresa."""
    if actor['role'] == 'master_admin':
        company_id = payload.get('company_id')
        if company_id in (None, ''):
            raise ValueError('Campo obrigatório: company_id')
        return int(company_id)
    return int(actor['company_id'])


# ── GET ───────────────────────────────────────────────────────────────────────

def handle_get_legal_entities(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_LEGAL_ENTITIES_VIEW)
        data = fetch_legal_entities(connection, actor)
        return send_json(handler, 200, {'legal_entities': data, 'items': data})


def handle_get_legal_entity(handler, parsed, payload, match):
    entity_id = int(match.group(1))
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_LEGAL_ENTITIES_VIEW)
        entity = get_legal_entity_by_id(connection, entity_id)
        if not entity:
            return send_json(handler, 404, {'error': 'CNPJ não encontrado.'})
        ensure_company_access(actor, entity['company_id'])
        return send_json(handler, 200, {'legal_entity': entity})


def handle_get_company_legal_entities(handler, parsed, payload, match):
    company_id = int(match.group(1))
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_LEGAL_ENTITIES_VIEW)
        ensure_company_access(actor, company_id)
        data = fetch_legal_entities(connection, None, company_id=company_id)
        return send_json(handler, 200, {'legal_entities': data, 'items': data})


# ── POST ──────────────────────────────────────────────────────────────────────

def handle_post_legal_entities(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'cnpj', 'legal_name'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_LEGAL_ENTITIES_CREATE)
        company_id = _resolve_company_id(actor, payload)
        ensure_company_access(actor, company_id)
        entity_id = create_legal_entity(connection, payload, company_id)
        _audit(
            connection, company_id, actor, 'legal_entity_create',
            f"CNPJ cadastrado: {payload.get('cnpj')} ({payload.get('legal_name')}).",
            [{'field': 'CNPJ', 'before': '', 'after': str(payload.get('cnpj') or '')}],
        )
        connection.commit()
        structured_log('info', 'legal_entity.created', legal_entity_id=entity_id, company_id=company_id, actor_user_id=actor['id'])
        return send_json(handler, 201, {'ok': True, 'id': entity_id})


def handle_post_legal_entities_batch(handler, parsed, payload, match):
    """Cadastro em lote — o onboarding de empresas com múltiplos CNPJs / JV envia
    a lista completa de uma vez. Erros são reportados por índice; entradas
    válidas anteriores permanecem gravadas (commit por item no service)."""
    require_fields(payload, ['actor_user_id'])
    items = payload.get('legal_entities') or payload.get('items') or []
    if not isinstance(items, list) or not items:
        return send_json(handler, 400, {'error': 'Envie uma lista não vazia em "legal_entities".'})
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_LEGAL_ENTITIES_CREATE)
        created, errors = [], []
        for index, item in enumerate(items):
            item = dict(item or {})
            try:
                company_id = _resolve_company_id(actor, item if actor['role'] == 'master_admin' else {})
                ensure_company_access(actor, company_id)
                created.append(create_legal_entity(connection, item, company_id))
            except (ValueError, PermissionError) as exc:
                errors.append({'index': index, 'error': str(exc)})
        structured_log('info', 'legal_entity.batch_created', created=len(created), errors=len(errors), actor_user_id=actor['id'])
        status = 201 if created and not errors else (207 if created else 400)
        return send_json(handler, status, {'ok': not errors, 'created_ids': created, 'errors': errors})


# ── PUT ───────────────────────────────────────────────────────────────────────

def handle_put_legal_entity(handler, parsed, payload, match):
    entity_id = int(match.group(1))
    require_fields(payload, ['actor_user_id', 'cnpj', 'legal_name'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_LEGAL_ENTITIES_UPDATE)
        current = get_legal_entity_by_id(connection, entity_id)
        if not current:
            return send_json(handler, 404, {'error': 'CNPJ não encontrado.'})
        ensure_company_access(actor, current['company_id'])
        update_legal_entity(connection, entity_id, payload, int(current['company_id']))
        changes = [
            {'field': field, 'before': str(current.get(field) or ''), 'after': str(payload.get(field) or '')}
            for field in ('cnpj', 'legal_name', 'trade_name', 'entity_type', 'active')
            if str(payload.get(field) or '') != str(current.get(field) or '')
        ]
        _audit(
            connection, current['company_id'], actor, 'legal_entity_update',
            f"CNPJ atualizado: {current.get('cnpj')}.", changes,
        )
        connection.commit()
        structured_log('info', 'legal_entity.updated', legal_entity_id=entity_id, actor_user_id=actor['id'])
        return send_json(handler, 200, {'ok': True, 'id': entity_id})


def register_routes(router):
    router.register('GET',  '/api/legal-entities',                         handle_get_legal_entities)
    router.register('GET',  r'^/api/legal-entities/(\d+)$',                 handle_get_legal_entity, regex=True)
    router.register('GET',  r'^/api/companies/(\d+)/legal-entities$',       handle_get_company_legal_entities, regex=True)
    router.register('POST', '/api/legal-entities',                         handle_post_legal_entities)
    router.register('POST', '/api/legal-entities/batch',                   handle_post_legal_entities_batch)
    router.register('PUT',  r'^/api/legal-entities/(\d+)$',                 handle_put_legal_entity, regex=True)
