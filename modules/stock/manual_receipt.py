"""Comprovação de validade por lote na entrada manual, sem dados do catálogo."""

from epi_backend.db import table_columns, table_exists
from modules.stock.lifecycle import physical_date


def validate_manual_lot(connection, payload):
    """Valida tudo antes de criar movimento, alterar saldo ou emitir QR.

    Clientes legados sem os novos campos ainda recebem como desconhecido.
    Informações parciais/conflitantes nunca são descartadas silenciosamente.
    """
    expiry = physical_date(payload.get('physical_expiry_date'), 'Validade física')
    source = str(payload.get('expiry_source') or '').strip()
    evidence = str(payload.get('expiry_evidence') or '').strip()
    lot_code = str(payload.get('lot_code') or '').strip()
    unknown = payload.get('physical_validity_unknown', False)
    if not isinstance(unknown, bool):
        raise ValueError('A indicação de validade desconhecida deve ser booleana.')
    if unknown and (expiry or source or evidence):
        raise ValueError('Validade desconhecida não pode conter data ou comprovação.')
    if expiry is None:
        if source or evidence:
            raise ValueError('Informe a validade física correspondente à comprovação do lote.')
        return {'physical_expiry_date': None, 'expiry_source': 'unknown',
                'expiry_evidence': None, 'lot_code': lot_code}
    if not lot_code:
        raise ValueError('Identifique o lote da validade física comprovada.')
    if source not in ('label', 'manufacturer_document'):
        raise ValueError('Comprove a validade pela embalagem/etiqueta ou documento do fabricante.')
    if not evidence:
        raise ValueError('Informe a evidência verificável da validade deste lote.')
    manufactured = physical_date(payload.get('manufacture_date'), 'Fabricação do lote')
    if manufactured is not None and expiry < manufactured:
        raise ValueError('Validade física anterior à fabricação do lote.')
    required = {'physical_expiry_date', 'physical_manufacture_date', 'expiry_source', 'expiry_evidence'}
    if (not required.issubset(table_columns(connection, 'epi_stock_items'))
            or not table_exists(connection, 'epi_stock_events')):
        raise ValueError('Modelo físico de validade indisponível neste ambiente.')
    return {'physical_expiry_date': expiry.isoformat(), 'expiry_source': source,
            'expiry_evidence': evidence, 'lot_code': lot_code,
            'physical_manufacture_date': manufactured.isoformat() if manufactured else None}


def record_manual_lot_piece(connection, stock_item_id, lot, actor, now):
    """Materializa a comprovação apenas na peça recém-criada e audita o recebimento.

    Classificação e bloqueio de lote vencido reutilizam o serviço já existente.
    O chamador mantém tudo na transação do movimento/saldo/QR.
    """
    if lot['physical_expiry_date'] is None:
        return
    from modules.stock.service import _append_stock_event, record_received_item_physical

    record_received_item_physical(
        connection, stock_item_id, lot['physical_expiry_date'], int(actor['id']), now,
        evidence=lot['expiry_evidence'],
    )
    connection.execute(
        'UPDATE epi_stock_items SET expiry_source=?, physical_manufacture_date=? WHERE id=?',
        (lot['expiry_source'], lot['physical_manufacture_date'], int(stock_item_id)),
    )
    item = connection.execute(
        'SELECT company_id, unit_id, epi_id, status FROM epi_stock_items WHERE id=?',
        (int(stock_item_id),),
    ).fetchone()
    _append_stock_event(
        connection, company_id=item['company_id'], epi_id=item['epi_id'],
        stock_item_id=stock_item_id, event_type='receipt', reason_code='manual_receipt',
        justification='Recebimento manual com validade comprovada do lote ' + lot['lot_code'],
        actor_user_id=actor['id'], actor_name=actor.get('full_name', ''),
        actor_role=actor.get('role', ''), now=now, origin_unit_id=item['unit_id'],
        before_values={}, after_values={**lot, 'status': item['status']},
    )
