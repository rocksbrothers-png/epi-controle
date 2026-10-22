"""Dados físicos por peça: fabricação comprovada e tamanho conferido pelo QR."""
from datetime import datetime, timezone

from epi_backend.db import row_to_dict, table_columns, table_exists
from modules.stock.eligibility import (
    ON_HAND_STATUSES,
    lock_stock_scope,
    validity_policy,
)
from modules.stock.lifecycle import physical_date


def physical_metadata(connection, item):
    from modules.stock.service import resolve_item_size
    data = dict(item)
    manufacture = data.get('physical_manufacture_date')
    if not manufacture and data.get('lot_id') and table_exists(connection, 'epi_stock_lots'):
        lot = connection.execute('SELECT manufacture_date FROM epi_stock_lots WHERE id=? AND company_id=? AND epi_id=?',
                                 (data['lot_id'], data['company_id'], data['epi_id'])).fetchone()
        if lot:
            manufacture = lot['manufacture_date']
    manufacture = manufacture or data.get('manufacture_date')
    sizes = resolve_item_size(data.get('glove_size'), data.get('size'), data.get('uniform_size'))
    # O movimento é a origem exata desta peça; catálogo ou peça vizinha não são prova de tamanho.
    if not sizes['selected_size'] and data.get('stock_movement_id') and table_exists(connection, 'stock_movements'):
        columns = table_columns(connection, 'stock_movements')
        if {'glove_size', 'size', 'uniform_size'}.issubset(columns):
            source = connection.execute('SELECT glove_size,size,uniform_size FROM stock_movements WHERE id=? '
                                        'AND company_id=? AND unit_id=? AND epi_id=?',
                                        (data['stock_movement_id'], data['company_id'], data['unit_id'], data['epi_id'])).fetchone()
            if source:
                sizes = resolve_item_size(source['glove_size'], source['size'], source['uniform_size'])
    data.update({key: value for key, value in sizes.items() if key != 'selected_size'})
    data['manufacture_date'] = str(manufacture or '')
    data['metadata_missing'] = [key for key, present in [('manufacture_date', manufacture), ('size', sizes['selected_size'])] if not present]
    from epi_backend.http_utils import _json_safe
    return _json_safe(data)


def incomplete_items(connection, company_id, unit_id=None):
    sql = ('SELECT i.*,e.name AS epi_name,u.name AS unit_name FROM epi_stock_items i '
           'JOIN epis e ON e.id=i.epi_id JOIN units u ON u.id=i.unit_id WHERE i.company_id=?')
    params = [company_id]
    if unit_id:
        sql += ' AND i.unit_id=?'
        params.append(unit_id)
    records = []
    for row in connection.execute(sql + ' ORDER BY i.id', tuple(params)).fetchall():
        item = row_to_dict(row)
        if item['status'] not in ON_HAND_STATUSES:
            continue
        effective = physical_metadata(connection, item)
        # Inclui também dados recuperáveis: a unidade pode materializar a conferência.
        if effective['metadata_missing'] or any(str(item.get(k) or '') != str(effective.get(k) or '')
                                              for k in ('manufacture_date', 'size')):
            records.append(effective)
    return records


def correct_item_metadata(connection, actor, item, payload):
    from modules.stock.service import _append_stock_event, resolve_item_size
    if payload.get('physical_confirmed') is not True:
        raise ValueError('Confirme a conferência física da peça identificada pelo QR.')
    evidence = str(payload.get('evidence') or '').strip()
    justification = str(payload.get('justification') or '').strip()
    if not evidence or not justification or len(evidence) > 2000 or len(justification) > 2000:
        raise ValueError('Informe evidência verificável e justificativa da correção.')
    manufacture = physical_date(payload.get('manufacture_date'), 'Fabricação física')
    if not manufacture:
        raise ValueError('Informe a fabricação comprovada na etiqueta ou documento do lote.')
    policy = validity_policy(connection, item['company_id'])
    if manufacture.isoformat() > policy['as_of_date']:
        raise ValueError('Fabricação física não pode estar no futuro.')
    sizes = resolve_item_size(payload.get('glove_size'), payload.get('size'), payload.get('uniform_size'))
    if not sizes['selected_size']:
        raise ValueError('Informe o tamanho fisicamente conferido desta peça.')
    lock_stock_scope(connection, item['company_id'], item['unit_id'], item['epi_id'])
    current = row_to_dict(connection.execute('SELECT * FROM epi_stock_items WHERE id=?', (item['id'],)).fetchone())
    if any(int(current.get(k) or 0) != int(item[k]) for k in ('company_id', 'unit_id', 'epi_id')):
        raise PermissionError('Peça fora da empresa/unidade autorizada.')
    if current['status'] not in ON_HAND_STATUSES or current['status'] == 'reserved':
        raise ValueError('Peça terminal, entregue ou reservada não pode ser corrigida neste fluxo.')
    expiry = physical_date(current.get('physical_expiry_date'))
    if expiry and manufacture > expiry:
        raise ValueError('Fabricação física posterior à validade comprovada.')
    if current.get('lot_id'):
        lot = connection.execute('SELECT manufacture_date FROM epi_stock_lots WHERE id=? AND company_id=? AND epi_id=?',
                                 (current['lot_id'], item['company_id'], item['epi_id'])).fetchone()
        if lot and lot['manufacture_date'] and str(lot['manufacture_date']) != manufacture.isoformat():
            raise ValueError('Fabricação difere do lote comprovado; confira o QR e a etiqueta do lote.')
    after = {k: sizes[k] for k in ('glove_size', 'size', 'uniform_size')}
    after.update(manufacture_date=manufacture.isoformat(), physical_manufacture_date=manufacture.isoformat())
    before = {key: str(current.get(key) or '') for key in after}
    if before == after:
        return {'ok': True, 'idempotent': True}
    now = datetime.now(timezone.utc).isoformat()
    connection.execute('UPDATE epi_stock_items SET manufacture_date=?,physical_manufacture_date=?,glove_size=?,size=?,'
                       'uniform_size=?,updated_at=?,row_version=row_version+1 WHERE id=?',
                       (manufacture.isoformat(), manufacture.isoformat(), sizes['glove_size'], sizes['size'], sizes['uniform_size'], now, item['id']))
    _append_stock_event(
        connection, company_id=item['company_id'], epi_id=item['epi_id'], stock_item_id=item['id'],
        event_type='expiry_regularization', reason_code='physical_metadata', justification=justification,
        actor_user_id=actor['id'], actor_name=actor.get('full_name', ''), actor_role=actor.get('role', ''),
        now=now, origin_unit_id=item['unit_id'], before_values=before, after_values={**after, 'evidence': evidence},
    )
    return {'ok': True, 'idempotent': False}
