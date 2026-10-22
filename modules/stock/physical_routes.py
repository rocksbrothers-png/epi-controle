"""Conferência de dados físicos e saída por destinação na unidade autorizada."""
from contextlib import closing, contextmanager
from urllib.parse import parse_qs

from core.database import get_connection
from core.repository import authorize_action
from core.security import resolve_actor_user_id
from epi_backend.http_utils import send_json
from modules.employees.service import actor_operational_unit_id
from modules.stock.disposition import ACTIONS, dispose_item, disposition_history
from modules.stock.physical_metadata import correct_item_metadata, incomplete_items
from modules.stock.service import lookup_stock_item_by_qr


@contextmanager
def _connection():
    with closing(get_connection()) as connection:
        try:
            yield connection
        finally:
            # A conexão volta ao pool sem transação parcial ou snapshot de leitura.
            connection.rollback()


def _scope(connection, actor, values):
    company = actor['company_id'] if actor['role'] != 'master_admin' else int(values.get('company_id') or 0)
    if not company:
        raise ValueError('Selecione a empresa do estoque.')
    unit = actor_operational_unit_id(connection, actor)
    if actor.get('role') in ('admin', 'user') and not unit:
        raise PermissionError('Perfil sem unidade operacional ativa para operar estoque.')
    requested = int(values.get('unit_id') or 0)
    if unit and requested and int(unit) != requested:
        raise PermissionError('Operação fora da sua unidade operacional.')
    return int(company), int(unit or requested or 0)


def handle_get_physical_records(handler, parsed, payload, match):
    with _connection() as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'stock:view')
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        company, unit = _scope(connection, actor, query)
        if parsed.path.endswith('/dispositions'):
            items = disposition_history(connection, company, unit)
            send_json(handler, 200, {'items': items, 'actions': ACTIONS})
            return
        send_json(handler, 200, {'items': incomplete_items(connection, company, unit)})


def handle_post_physical_item(handler, parsed, payload, match):
    disposition = parsed.path.endswith('/disposition')
    permission = 'stock:adjust' if disposition else 'stock:regularize_validity'
    with _connection() as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), permission)
        company, unit = _scope(connection, actor, payload)
        item_id = payload.get('stock_item_id')
        if type(item_id) is not int or item_id <= 0:
            raise ValueError('Selecione a peça pelo QR físico.')
        item = lookup_stock_item_by_qr(connection, company, unit, stock_item_id=item_id)
        if not item or payload.get('qr_code') != item['qr_code_value']:
            raise PermissionError('QR fora da empresa/unidade autorizada ou diferente da peça selecionada.')
        actor = dict(actor, company_id=company)
        if disposition:
            result = dispose_item(connection, actor, item, payload)
        else:
            result = correct_item_metadata(connection, actor, item, payload)
        connection.commit()
        send_json(handler, 200, result)


def register_physical_routes(router):
    router.register('GET', '/api/stock/dispositions', handle_get_physical_records)
    router.register('GET', '/api/stock/incomplete-items', handle_get_physical_records)
    router.register('POST', '/api/stock/items/disposition', handle_post_physical_item)
    router.register('POST', '/api/stock/items/physical-metadata', handle_post_physical_item)
