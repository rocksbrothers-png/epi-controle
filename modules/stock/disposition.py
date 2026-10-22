"""Saída física de peças bloqueadas, decidida e registrada pela unidade."""
import json
from datetime import datetime, timezone

from epi_backend.db import row_to_dict
from modules.stock.eligibility import (
    AVAILABLE_STATUSES,
    classify_physical,
    lock_stock_scope,
    validity_policy,
)

ACTIONS = {'donation': 'Doação', 'supplier_return': 'Devolução à empresa / fornecedor', 'discard': 'Descarte'}
FINAL_STATUSES = {'donation': 'donated', 'supplier_return': 'supplier_returned', 'discard': 'discarded'}


def disposition_history(connection, company_id, unit_id=None):
    params = [int(company_id)]
    clause = ''
    if unit_id:
        clause = ' AND ev.origin_unit_id=?'
        params.append(int(unit_id))
    rows = connection.execute(
        'SELECT ev.id,ev.stock_item_id,ev.event_type,ev.justification,ev.actor_name_snapshot,ev.created_at,'
        'ev.after_values,i.qr_code_value,i.lot_code,e.name AS epi_name,u.name AS unit_name '
        'FROM epi_stock_events ev JOIN epi_stock_items i ON i.id=ev.stock_item_id AND i.company_id=ev.company_id '
        'JOIN epis e ON e.id=ev.epi_id JOIN units u ON u.id=ev.origin_unit_id '
        "WHERE ev.company_id=? AND ev.reason_code='unit_disposition'" + clause + ' ORDER BY ev.id DESC LIMIT 200',
        tuple(params),
    ).fetchall()
    result = []
    for raw in rows:
        record = row_to_dict(raw)
        details = record.pop('after_values')
        details = json.loads(details) if isinstance(details, str) else details
        record.update(action=details['action'], recipient=details['recipient'],
                      recipient_reference=details.get('recipient_reference', ''), shipment_reference=details['shipment_reference'])
        result.append(record)
    from epi_backend.http_utils import _json_safe
    return _json_safe(result)


def dispose_item(connection, actor, item, payload):
    from modules.stock.service import (
        _append_stock_event,
        create_stock_movement,
        get_unit_stock,
        upsert_unit_stock,
    )

    action = payload.get('action')
    if not isinstance(action, str) or action not in ACTIONS:
        raise ValueError('Selecione doação, devolução ou descarte.')
    values = {}
    for key, label, limit in [('recipient', 'Destinatário sugerido pela unidade', 240),
                              ('recipient_reference', 'Identificação do destinatário', 240),
                              ('shipment_reference', 'Comprovante/referência de envio', 240),
                              ('justification', 'Motivo da destinação', 2000)]:
        raw = payload.get(key, '')
        if not isinstance(raw, str) or len(raw.strip()) > limit:
            raise ValueError(label + ' inválido.')
        values[key] = raw.strip()
        if key != 'recipient_reference' and not values[key]:
            raise ValueError(label + ' é obrigatório.')
    if payload.get('shipment_confirmed') is not True:
        raise ValueError('Confirme a retirada física e o envio para o destinatário informado.')
    lock_stock_scope(connection, item['company_id'], item['unit_id'], item['epi_id'])
    current = connection.execute('SELECT * FROM epi_stock_items WHERE id=?', (item['id'],)).fetchone()
    current = row_to_dict(current) if current else {}
    if any(int(current.get(k) or 0) != int(item[k]) for k in ('company_id', 'unit_id', 'epi_id')):
        raise PermissionError('Peça fora da empresa/unidade autorizada.')
    after = dict(values, action=action, status=FINAL_STATUSES[action])
    old_status = str(current['status']).lower()
    if old_status in FINAL_STATUSES.values():
        event = connection.execute(
            "SELECT after_values FROM epi_stock_events WHERE stock_item_id=? AND company_id=? "
            "AND reason_code='unit_disposition' ORDER BY id DESC LIMIT 1", (item['id'], item['company_id']),
        ).fetchone()
        if event:
            old = event['after_values']
            old = json.loads(old) if isinstance(old, str) else old
            if old == after:
                return {'ok': True, 'status': old_status, 'idempotent': True}
        raise ValueError('Peça já destinada; não é possível repetir ou alterar a baixa.')
    expired = classify_physical(current.get('physical_expiry_date'), validity_policy(connection, item['company_id']))['status'] == 'expired'
    if not (old_status.startswith('blocked') or old_status in ('quarantine', 'discard_pending')
            or (old_status in AVAILABLE_STATUSES and expired)):
        raise ValueError('Destinação exige peça bloqueada, sem reserva ou entrega em andamento.')
    balance = get_unit_stock(connection, item['company_id'], item['unit_id'], item['epi_id'])
    previous = int((balance or {}).get('quantity') or 0)
    if previous < 1:
        raise ValueError('Saldo físico insuficiente; confira o estoque antes da destinação.')
    now = datetime.now(timezone.utc).isoformat()
    movement_id = create_stock_movement(
        connection, item['company_id'], item['unit_id'], item['epi_id'], 'out', 1, previous, previous - 1,
        'stock_disposition', item['id'], f"{ACTIONS[action]} → {values['recipient']}. {values['shipment_reference']}. {values['justification']}",
        actor['id'], actor.get('full_name', ''), now,
        current.get('glove_size') or 'N/A', current.get('size') or 'N/A', current.get('uniform_size') or 'N/A',
    )
    upsert_unit_stock(connection, item['company_id'], item['unit_id'], item['epi_id'], previous - 1)
    connection.execute('UPDATE epi_stock_items SET status=?,updated_at=?,row_version=row_version+1 WHERE id=?',
                       (FINAL_STATUSES[action], now, item['id']))
    _append_stock_event(
        connection, company_id=item['company_id'], epi_id=item['epi_id'], stock_item_id=item['id'],
        event_type=action, reason_code='unit_disposition', justification=values['justification'],
        actor_user_id=actor['id'], actor_name=actor.get('full_name', ''), actor_role=actor.get('role', ''),
        now=now, origin_unit_id=item['unit_id'], before_values={'status': old_status, 'physical_stock': previous},
        after_values=after,
    )
    return {'ok': True, 'status': FINAL_STATUSES[action], 'movement_id': movement_id,
            'new_stock': previous - 1, 'idempotent': False}
