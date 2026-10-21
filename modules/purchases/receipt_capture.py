"""Comprovação física na conferência: lote, datas e foto registrados uma vez."""
from datetime import datetime, timezone

from modules.stock.lifecycle import physical_date
from modules.stock.lot_evidence import (
    create_physical_lot,
    proof_reference,
    save_lot_file,
    validate_evidence_file,
)


def prepare_receipt_capture(lot):
    enhanced = lot.get('capture_version') == 1 or any(lot.get(k) for k in (
        'manufacture_date', 'expiry_source', 'evidence_file', 'physical_lot_confirmed'))
    if not enhanced:
        return None
    manufactured = physical_date(lot.get('manufacture_date'), 'Fabricação do lote')
    expiry = physical_date(lot.get('manufacturer_validity_date'), 'Validade do lote')
    if not manufactured and not expiry and not lot.get('evidence_file'):
        return None  # ausência permanece desconhecida e bloqueada
    if manufactured and manufactured > datetime.now(timezone.utc).date():
        raise ValueError('Fabricação do lote não pode estar no futuro.')
    if manufactured and expiry and expiry < manufactured:
        raise ValueError('Validade física anterior à fabricação do lote.')
    code, source = str(lot.get('lot_code') or '').strip(), lot.get('expiry_source')
    evidence = str(lot.get('evidence') or '').strip()
    if not code or source not in ('label', 'manufacturer_document') or not evidence:
        raise ValueError('Informe lote real, origem e referência da comprovação física.')
    if lot.get('physical_lot_confirmed') is not True:
        raise ValueError('Confira e confirme as datas e o lote na foto/documento.')
    file = validate_evidence_file(lot.get('evidence_file'), required=True)
    return {'lot_code': code, 'physical_manufacture_date': manufactured.isoformat() if manufactured else None,
            'physical_expiry_date': expiry.isoformat() if expiry else None,
            'expiry_source': source if expiry else 'unknown', 'manufacture_source': source,
            'expiry_evidence': proof_reference(evidence, file), 'file': file,
            'quantity': lot.get('quantity')}


def validate_capture_budget(flags):
    files, pieces, total = 0, 0, 0
    for flag in flags:
        if flag.get('received') is False:
            continue
        for lot in flag.get('lots') or []:
            proof = prepare_receipt_capture(lot)
            if proof is None:
                continue
            files += 1
            qty = lot.get('quantity')
            if type(qty) is not int or qty < 1:
                raise ValueError('Quantidade do lote comprovado deve ser um inteiro positivo.')
            pieces += qty
            total += proof['file']['size']
    if files > 10 or pieces > 500 or total > 12 * 1024 * 1024:
        raise ValueError('Um envio aceita até 10 lotes comprovados, 500 peças e 12 MiB em anexos.')


def record_receipt_capture(connection, item_id, proof, actor, unit_id, epi_id, now, source, source_id, cache):
    """O chamador mantém movimento, peças, lote e anexo na mesma transação."""
    from modules.stock.service import _append_stock_event

    key = id(proof)  # a expansão do lote compartilha a mesma prova entre suas peças
    if key not in cache:
        lot_id = create_physical_lot(connection, actor, unit_id, epi_id, proof, proof['quantity'], now, source=source)
        connection.execute('UPDATE epi_stock_lots SET receipt_source_id=? WHERE id=?', (source_id, lot_id))
        cache[key] = lot_id
        save_lot_file(connection, actor, lot_id, item_id, proof['file'],
                      'Conferência física do lote ' + proof['lot_code'], now, event_type='receipt')
    lot_id = cache[key]
    connection.execute('UPDATE epi_stock_items SET lot_id=?, manufacture_date=?, physical_manufacture_date=?, '
                       'expiry_source=?, expiry_evidence=? WHERE id=?',
                       (lot_id, proof['physical_manufacture_date'] or '', proof['physical_manufacture_date'],
                        proof['expiry_source'], proof['expiry_evidence'], item_id))
    _append_stock_event(connection, company_id=actor['company_id'], epi_id=epi_id, stock_item_id=item_id,
                        event_type='receipt', reason_code='purchase_receipt',
                        justification='Conferência física do lote ' + proof['lot_code'],
                        actor_user_id=actor['id'], actor_name=actor.get('full_name', ''), actor_role=actor.get('role', ''),
                        now=now, origin_unit_id=unit_id, before_values={},
                        after_values={k: v for k, v in proof.items() if k != 'file'})
    return lot_id
