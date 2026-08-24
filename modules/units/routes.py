"""Rotas de unidades operacionais."""
import re
from contextlib import closing
from datetime import datetime, timezone
from urllib.parse import parse_qs

from core.auth import ensure_resource_company, require_structural_admin
from core.database import get_connection
from core.repository import (
    authorize_action,
    get_unit_active_jv_name,
    get_unit_by_id,
    resolve_purchase_unit_scope,
    selectable_units,
)
from core.security import resolve_actor_user_id
from epi_backend.http_utils import require_fields, send_json
from modules.units.service import (
    UNIT_MIN_RETENTION_YEARS,
    archive_unit,
    cancel_unit_purge,
    confirm_unit_purge,
    create_unit,
    end_unit_jv,
    fetch_archived_units,
    fetch_units,
    get_company_retention_years,
    get_unit_by_id as get_unit_with_lifecycle,
    normalize_unit_type,
    request_unit_purge,
    restore_unit,
    set_company_retention_years,
    set_unit_legal_hold,
    set_unit_operational_status,
    start_unit_jv,
    summarize_unit_history,
    update_unit,
)

_UNIT_ID_RE = re.compile(r'^/api/units/(\d+)$')


def _client_ip(handler):
    return str(getattr(handler, 'client_address', ('',))[0] or '')


def _require_deletion_admin(actor):
    if actor.get('role') not in ('general_admin', 'registry_admin'):
        raise PermissionError(
            'Apenas Administrador Geral ou Administrador de Registro podem gerenciar a exclusão definitiva.'
        )


def handle_get_units(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'units:view')
        units = fetch_units(connection, actor)
        return send_json(handler, 200, {'units': units})


def handle_get_selectable_units(handler, parsed, payload, match):
    """As Unidades que o ator pode ESCOLHER, mais o contexto do seletor.

    Por que não basta `GET /api/units`: aquela rota recorta por TENANT e mais
    nada. Um `admin`/`user` travado recebe dela todas as Unidades da empresa, e
    cada tela ficava encarregada de estreitar a lista por conta própria — o que
    significa a interface reconstruindo autorização. Hoje quatro telas do
    Flutter consomem `bootstrap.units` e só uma estreita, no cliente.

    Aqui o servidor decide e o cliente desenha. A regra é a mesma de Compras
    (`resolve_purchase_unit_scope`) porque É a mesma regra — perfil travado só
    a própria, Comprador/Aprovador só a carteira, demais perfis todas do
    tenant. Não há segunda implementação, e o recorte final sai de
    `selectable_units`, compartilhado com o filtro do Dashboard.

    O contrato devolve estado explícito em vez de deixar o cliente inferir:

    - `locked` + `unit_id`: perfil travado e qual é a Unidade dele;
    - `allows_all_units`: se a opção "Todas" pode ser oferecida. **Só o
      backend decide isso**;
    - `blocks_everything`: carteira existente e VAZIA. Sem este campo, lista
      vazia seria ambígua entre "você não tem Unidade atribuída" e "a empresa
      não tem Unidades" — mensagens diferentes para o operador.

    `units:view` é a mesma permissão de `GET /api/units`: a lista aqui é um
    subconjunto daquela, nunca um superconjunto.
    """
    from modules.purchases.service import get_actor_purchase_unit_scope

    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'units:view')
        # A carteira entra por injeção: `core.repository` não pode importar
        # `modules.purchases` sem reabrir o ciclo fechado pela issue #148.
        selecao = resolve_purchase_unit_scope(
            connection, actor,
            purchase_units_loader=get_actor_purchase_unit_scope,
            denial_message='Perfil sem unidade operacional ativa para selecionar Unidade.',
        )
        unidades = selectable_units(fetch_units(connection, actor), selecao)
        return send_json(handler, 200, {
            'units': [
                {
                    'id': int(u.get('id')),
                    'name': str(u.get('name') or ''),
                    'legal_entity_id': u.get('legal_entity_id'),
                }
                for u in unidades
            ],
            'locked': bool(selecao.locked),
            'unit_id': selecao.unit_id,
            'source': selecao.source,
            'allows_all_units': bool(selecao.allows_all_units),
            'blocks_everything': bool(selecao.blocks_everything),
        })


def handle_get_archived_units(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'units:view')
        units = fetch_archived_units(connection, actor)
        return send_json(handler, 200, {'units': units})


def handle_get_unit(handler, parsed, payload, match):
    unit_id = int(match.group(1))
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'units:view')
        unit = get_unit_with_lifecycle(connection, unit_id)
        ensure_resource_company(actor, unit, 'Unidade')
        return send_json(handler, 200, {'unit': unit})


def handle_post_units(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'company_id', 'name', 'unit_type', 'city'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'units:create', int(payload['company_id']))
        require_structural_admin(actor)
        unit_type = normalize_unit_type(payload.get('unit_type'))
        unit_id = create_unit(connection, payload['company_id'], payload['name'], unit_type, payload['city'], payload.get('notes', ''), legal_entity_id=payload.get('legal_entity_id'))
        connection.commit()
        return send_json(handler, 201, {'ok': True, 'id': unit_id})


def handle_put_unit(handler, parsed, payload, match):
    unit_id = int(match.group(1))
    require_fields(payload, ['actor_user_id', 'company_id', 'name', 'unit_type', 'city'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'units:update', int(payload['company_id']))
        require_structural_admin(actor)
        current = get_unit_by_id(connection, unit_id)
        ensure_resource_company(actor, current, 'Unidade')
        unit_type = normalize_unit_type(payload.get('unit_type'))
        update_unit(connection, unit_id, payload['company_id'], payload['name'], unit_type, payload['city'], payload.get('notes', ''), legal_entity_id=payload.get('legal_entity_id'))
        connection.commit()
        return send_json(handler, 200, {'ok': True})


def handle_delete_unit(handler, parsed, payload, match):
    """Política de retenção: DELETE não remove — arquiva (soft delete).

    O histórico operacional, documental e de auditoria permanece íntegro pelo
    período mínimo de retenção configurado por tenant (>= 5 anos).
    """
    unit_id = int(match.group(1))
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'units:delete')
        require_structural_admin(actor)
        current = get_unit_with_lifecycle(connection, unit_id)
        if not current:
            raise ValueError('Unidade não encontrada.')
        ensure_resource_company(actor, current, 'Unidade')
        query = parse_qs(parsed.query)
        reason = str(query.get('reason', [''])[0] or '')
        result = archive_unit(connection, current, actor, reason=reason, ip=_client_ip(handler))
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'archived': True, **result})


# ── Arquivamento e ciclo de vida ─────────────────────────────────────────────

def _load_unit_for_lifecycle(connection, handler, parsed, payload, match, permission):
    actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), permission)
    unit = get_unit_with_lifecycle(connection, int(match.group(1)))
    if not unit:
        raise ValueError('Unidade não encontrada.')
    ensure_resource_company(actor, unit, 'Unidade')
    return actor, unit


def handle_post_unit_archive(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor, unit = _load_unit_for_lifecycle(connection, handler, parsed, payload, match, 'units:delete')
        require_structural_admin(actor)
        result = archive_unit(connection, unit, actor, reason=str((payload or {}).get('reason') or ''), ip=_client_ip(handler))
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'archived': True, **result})


def handle_post_unit_restore(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor, unit = _load_unit_for_lifecycle(connection, handler, parsed, payload, match, 'units:update')
        require_structural_admin(actor)
        restore_unit(connection, unit, actor, ip=_client_ip(handler))
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'status': 'active'})


def handle_post_unit_status(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'status'])
    with closing(get_connection()) as connection:
        actor, unit = _load_unit_for_lifecycle(connection, handler, parsed, payload, match, 'units:update')
        require_structural_admin(actor)
        set_unit_operational_status(connection, unit, actor, str(payload['status']).strip().lower(), ip=_client_ip(handler))
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'status': str(payload['status']).strip().lower()})


def handle_post_unit_legal_hold(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor, unit = _load_unit_for_lifecycle(connection, handler, parsed, payload, match, 'units:update')
        _require_deletion_admin(actor)
        hold = bool(payload.get('legal_hold'))
        set_unit_legal_hold(connection, unit, actor, hold, reason=str(payload.get('reason') or ''), ip=_client_ip(handler))
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'legal_hold': 1 if hold else 0})


def handle_get_unit_deletion_summary(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor, unit = _load_unit_for_lifecycle(connection, handler, parsed, payload, match, 'units:view')
        summary = summarize_unit_history(connection, int(unit['id']))
        return send_json(handler, 200, {
            'unit': {
                'id': unit['id'],
                'name': unit['name'],
                'status': unit.get('status'),
                'archived_at': unit.get('archived_at'),
                'retention_until': unit.get('retention_until'),
                'legal_hold': int(unit.get('legal_hold') or 0),
            },
            'records': summary,
        })


def handle_post_unit_purge_request(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor, unit = _load_unit_for_lifecycle(connection, handler, parsed, payload, match, 'units:delete')
        _require_deletion_admin(actor)
        summary = request_unit_purge(connection, unit, actor, ip=_client_ip(handler))
        connection.commit()
        return send_json(handler, 200, {
            'ok': True,
            'status': 'pending_deletion',
            'records': summary,
            'next_step': 'Confirme a exclusão definitiva com justificativa e o nome exato da unidade.',
        })


def handle_post_unit_purge_cancel(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor, unit = _load_unit_for_lifecycle(connection, handler, parsed, payload, match, 'units:delete')
        _require_deletion_admin(actor)
        cancel_unit_purge(connection, unit, actor, ip=_client_ip(handler))
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'status': 'archived'})


def handle_post_unit_purge_confirm(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'justification', 'confirm_name'])
    with closing(get_connection()) as connection:
        actor, unit = _load_unit_for_lifecycle(connection, handler, parsed, payload, match, 'units:delete')
        _require_deletion_admin(actor)
        summary = confirm_unit_purge(
            connection, unit, actor,
            justification=payload.get('justification'),
            confirm_name=payload.get('confirm_name'),
            ip=_client_ip(handler),
        )
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'status': 'deleted', 'records_removed': summary})


# ── Política de retenção por tenant ──────────────────────────────────────────

def _resolve_policy_company_id(actor, raw_company_id):
    company_id = int(raw_company_id or 0)
    if not company_id:
        company_id = int(actor.get('company_id') or 0)
    if not company_id:
        raise ValueError('company_id é obrigatório.')
    return company_id


def handle_get_unit_retention_policy(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'units:view')
        query = parse_qs(parsed.query)
        company_id = _resolve_policy_company_id(actor, query.get('company_id', ['0'])[0])
        if actor['role'] != 'master_admin' and int(actor.get('company_id') or 0) != company_id:
            raise PermissionError('Acesso permitido apenas para registros da própria empresa.')
        return send_json(handler, 200, {
            'company_id': company_id,
            'retention_years': get_company_retention_years(connection, company_id),
            'min_retention_years': UNIT_MIN_RETENTION_YEARS,
        })


def handle_put_unit_retention_policy(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'retention_years'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'units:update')
        _require_deletion_admin(actor)
        company_id = _resolve_policy_company_id(actor, payload.get('company_id'))
        if actor['role'] != 'master_admin' and int(actor.get('company_id') or 0) != company_id:
            raise PermissionError('Acesso permitido apenas para registros da própria empresa.')
        years = set_company_retention_years(connection, company_id, payload['retention_years'])
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'company_id': company_id, 'retention_years': years})


# ── POST /api/unit-jv/start ───────────────────────────────────────────────────

def handle_post_unit_jv_start(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'units:edit')
        unit_id = int(payload.get('unit_id') or 0)
        jv_name = str(payload.get('joint_venture_name') or '').strip()
        if not unit_id or not jv_name:
            raise ValueError('unit_id e joint_venture_name são obrigatórios.')
        unit = get_unit_by_id(connection, unit_id)
        ensure_resource_company(actor, unit, 'Unidade')
        existing = get_unit_active_jv_name(connection, unit_id)
        if existing:
            raise ValueError(f'Unidade já está em JV ativa: "{existing}". Encerre antes de iniciar outra.')
        start_unit_jv(connection, unit['company_id'], unit_id, jv_name, datetime.now(timezone.utc).isoformat(), actor.get('id') or '')
        connection.commit()
        return send_json(handler, 201, {'unit_id': unit_id, 'active_jv_name': jv_name, 'started': True})


# ── POST /api/unit-jv/end ─────────────────────────────────────────────────────

def handle_post_unit_jv_end(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'units:edit')
        unit_id = int(payload.get('unit_id') or 0)
        if not unit_id:
            raise ValueError('unit_id é obrigatório.')
        unit = get_unit_by_id(connection, unit_id)
        ensure_resource_company(actor, unit, 'Unidade')
        existing = get_unit_active_jv_name(connection, unit_id)
        if not existing:
            raise ValueError('Unidade não possui JV ativa para encerrar.')
        end_unit_jv(connection, unit_id, datetime.now(timezone.utc).isoformat())
        connection.commit()
        return send_json(handler, 200, {'unit_id': unit_id, 'ended_jv_name': existing, 'ended': True})


def handle_get_unit_jv_active(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'units:view')
        query = parse_qs(parsed.query)
        unit_id = int(query.get('unit_id', ['0'])[0] or 0)
        if not unit_id:
            raise ValueError('unit_id é obrigatório.')
        unit = get_unit_by_id(connection, unit_id)
        ensure_resource_company(actor, unit, 'Unidade')
        name = get_unit_active_jv_name(connection, unit_id)
        return send_json(handler, 200, {'unit_id': unit_id, 'active_jv_name': name, 'in_jv': bool(name)})


def register_routes(router):
    router.register('GET',    '/api/unit-jv/active',           handle_get_unit_jv_active)
    router.register('GET',    '/api/units',                    handle_get_units)
    router.register('GET',    '/api/units/archived',           handle_get_archived_units)
    router.register('GET',    '/api/units/selectable',          handle_get_selectable_units)
    router.register('GET',    '/api/units/retention-policy',   handle_get_unit_retention_policy)
    router.register('PUT',    '/api/units/retention-policy',   handle_put_unit_retention_policy)
    router.register('GET',    r'/api/units/(\d+)$',            handle_get_unit,                  regex=True)
    router.register('GET',    r'/api/units/(\d+)/deletion-summary$', handle_get_unit_deletion_summary, regex=True)
    router.register('POST',   '/api/units',                    handle_post_units)
    router.register('POST',   r'/api/units/(\d+)/archive$',    handle_post_unit_archive,         regex=True)
    router.register('POST',   r'/api/units/(\d+)/restore$',    handle_post_unit_restore,         regex=True)
    router.register('POST',   r'/api/units/(\d+)/status$',     handle_post_unit_status,          regex=True)
    router.register('POST',   r'/api/units/(\d+)/legal-hold$', handle_post_unit_legal_hold,      regex=True)
    router.register('POST',   r'/api/units/(\d+)/purge-request$', handle_post_unit_purge_request, regex=True)
    router.register('POST',   r'/api/units/(\d+)/purge-cancel$',  handle_post_unit_purge_cancel,  regex=True)
    router.register('POST',   r'/api/units/(\d+)/purge-confirm$', handle_post_unit_purge_confirm, regex=True)
    router.register('POST',   '/api/unit-jv/start',            handle_post_unit_jv_start)
    router.register('POST',   '/api/unit-jv/end',              handle_post_unit_jv_end)
    router.register('PUT',    r'/api/units/(\d+)',             handle_put_unit,                  regex=True)
    router.register('DELETE', r'/api/units/(\d+)',             handle_delete_unit,               regex=True)
