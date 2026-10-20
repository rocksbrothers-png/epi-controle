"""Lotes físicos explicitamente conferidos e anexos no histórico imutável.

O arquivo é guardado uma vez por lote no evento append-only existente. Não há
URL pública, escrita em disco ou inferência de lotes por texto de catálogo.
"""
import base64
import hashlib
import json
import re
from datetime import datetime, timezone
from uuid import uuid4

from epi_backend.db import row_to_dict
from modules.stock.eligibility import lock_stock_scope
from modules.stock.manual_receipt import validate_manual_lot

MAX_FILE_BYTES = 3 * 1024 * 1024


def validate_evidence_file(value, *, required=False):
    if value is None:
        if required:
            raise ValueError('Anexe foto da embalagem/etiqueta ou documento do fabricante.')
        return None
    if not isinstance(value, dict):
        raise ValueError('Anexo inválido.')
    name, mime, encoded = value.get('filename'), value.get('mime'), value.get('content_base64')
    if (not isinstance(name, str) or not name.strip() or len(name) > 180
            or any(c in name for c in ('/', '\\')) or any(ord(c) < 32 for c in name)):
        raise ValueError('Nome de arquivo inválido.')
    extensions = {'application/pdf': ('.pdf',), 'image/png': ('.png',), 'image/jpeg': ('.jpg', '.jpeg')}
    if not isinstance(mime, str) or mime not in extensions or not name.lower().endswith(extensions[mime]):
        raise ValueError('Nome e formato do anexo devem corresponder a PDF, PNG ou JPEG.')
    if not isinstance(encoded, str) or len(encoded) > 4 * ((MAX_FILE_BYTES + 2) // 3):
        raise ValueError('O anexo deve ter no máximo 3 MiB.')
    try:
        content = base64.b64decode(encoded, validate=True)
    except (ValueError, base64.binascii.Error):
        raise ValueError('Conteúdo do anexo inválido.') from None
    signatures = {
        'application/pdf': content.startswith(b'%PDF-'),
        'image/png': content.startswith(b'\x89PNG\r\n\x1a\n'),
        'image/jpeg': content.startswith(b'\xff\xd8\xff'),
    }
    if not content or len(content) > MAX_FILE_BYTES or not signatures.get(mime, False):
        raise ValueError('Envie PDF, PNG ou JPEG válido com até 3 MiB.')
    return {'filename': name, 'mime': mime, 'size': len(content),
            'sha256': hashlib.sha256(content).hexdigest(), 'content_base64': encoded}


def proof_reference(evidence, file):
    return (str(evidence or '').strip() +
            (f" | Anexo: {file['filename']} | SHA-256: {file['sha256']}" if file else ''))


def create_physical_lot(connection, actor, unit_id, epi_id, lot, quantity, now, *, source='manual', receipt_key=None):
    return int(connection.execute(
        'INSERT INTO epi_stock_lots (company_id,epi_id,receipt_unit_id,receipt_key,receipt_source,'
        'lot_code,manufacture_date,physical_expiry_date,expiry_source,expiry_evidence,'
        'received_quantity,received_by_user_id,received_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (actor['company_id'], epi_id, unit_id, receipt_key or source + '-' + uuid4().hex, source,
         lot['lot_code'], lot.get('physical_manufacture_date'), lot['physical_expiry_date'],
         lot['expiry_source'], lot['expiry_evidence'], quantity, actor['id'], now),
    ).lastrowid)


def link_piece_to_lot(connection, item_id, lot_id, lot_code):
    connection.execute('UPDATE epi_stock_items SET lot_id=?,lot_code=? WHERE id=?',
                       (lot_id, lot_code, item_id))


def save_lot_file(connection, actor, lot_id, item_id, file, justification, now, before=None, event_type=None):
    if file is None:
        return
    lot = row_to_dict(connection.execute('SELECT * FROM epi_stock_lots WHERE id=?', (lot_id,)).fetchone())
    connection.execute(
        'INSERT INTO epi_stock_events (company_id,epi_id,stock_item_id,lot_id,quantity,event_type,'
        'origin_unit_id,reason_code,justification,actor_user_id,actor_name_snapshot,actor_role_snapshot,'
        'created_at,before_values,after_values) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (lot['company_id'], lot['epi_id'], item_id, lot_id, lot['received_quantity'],
         event_type or ('receipt' if lot['receipt_source'] == 'manual' else 'expiry_regularization'),
         lot['receipt_unit_id'], 'lot_evidence', justification, actor['id'],
         actor.get('full_name', ''), actor.get('role', ''), now, json.dumps(before or {}),
         json.dumps({'evidence_file': file, 'lot_code': lot['lot_code'],
                     'expiry_source': lot['expiry_source'],
                     'physical_expiry_date': str(lot['physical_expiry_date']),
                     'evidence': lot['expiry_evidence']}, ensure_ascii=False)),
    )


def regularize_selected_lot(connection, actor, unit_id, payload):
    from modules.stock.service import regularize_item_physical_validity

    selections = payload.get('items')
    if payload.get('physical_lot_confirmed') is not True:
        raise ValueError('Confirme a conferência física das peças e do lote informado.')
    if not isinstance(selections, list) or not 1 <= len(selections) <= 500:
        raise ValueError('Selecione entre 1 e 500 peças do mesmo lote físico.')
    file = validate_evidence_file(payload.get('evidence_file'), required=True)
    justification = str(payload.get('justification') or '').strip()
    if not justification:
        raise ValueError('Informe a justificativa da conferência deste lote.')
    lot = validate_manual_lot(connection, {**payload, 'expiry_evidence': payload.get('evidence')})
    if lot['physical_expiry_date'] is None:
        raise ValueError('Informe a validade física comprovada do lote.')
    lot['expiry_evidence'] = proof_reference(lot['expiry_evidence'], file)
    ids = []
    for selection in selections:
        if not isinstance(selection, dict) or type(selection.get('stock_item_id')) is not int:
            raise ValueError('Seleção de peça inválida.')
        ids.append(selection['stock_item_id'])
    if len(set(ids)) != len(ids):
        raise ValueError('Peça repetida na seleção.')
    first = connection.execute('SELECT epi_id FROM epi_stock_items WHERE id=? AND company_id=? AND unit_id=?',
                               (ids[0], actor['company_id'], unit_id)).fetchone()
    if first is None:
        raise PermissionError('Peça fora da empresa/unidade autorizada.')
    lock_stock_scope(connection, actor['company_id'], unit_id, first['epi_id'])
    items = []
    for selection in selections:
        row = connection.execute('SELECT * FROM epi_stock_items WHERE id=? AND company_id=? AND unit_id=? AND epi_id=?',
                                 (selection['stock_item_id'], actor['company_id'], unit_id, first['epi_id'])).fetchone()
        if row is None:
            raise PermissionError('Todas as peças devem pertencer ao mesmo EPI e unidade autorizada.')
        item = row_to_dict(row)
        if not selection.get('qr_code') or selection['qr_code'] != item['qr_code_value']:
            raise ValueError('O QR deve identificar exatamente a peça selecionada.')
        if item.get('lot_code') and item['lot_code'] != lot['lot_code']:
            raise ValueError('Peça identificada com outro lote; confira a seleção física.')
        if item['status'] not in ('in_stock', 'available', 'blocked_expired'):
            raise ValueError('Peça fora dos estados permitidos para regularização.')
        items.append(item)
    # Reenvio idêntico não duplica lote/anexo nem eventos. Outra data ou prova
    # em peça já regularizada exige o fluxo individual de correção auditada.
    known = [item for item in items if item.get('physical_expiry_date')]
    if known:
        old_lot = connection.execute('SELECT expiry_source,lot_code FROM epi_stock_lots WHERE id=?',
                                     (items[0].get('lot_id') or 0,)).fetchone()
        if len(known) == len(items) and len({i.get('lot_id') for i in items}) == 1 and all(
                str(i['physical_expiry_date']) == lot['physical_expiry_date']
                and i.get('expiry_evidence') == lot['expiry_evidence'] and i.get('lot_id') for i in items
                ) and old_lot and old_lot['expiry_source'] == lot['expiry_source']:
            return {'ok': True, 'lot_id': items[0]['lot_id'], 'count': len(items), 'idempotent': True}
        raise ValueError('Selecione apenas peças com validade desconhecida para comprovar um novo lote.')
    now = datetime.now(timezone.utc).isoformat()
    # O serviço físico valida fabricação/validade e registra cada peça; qualquer
    # recusa desfaz também a criação do lote, vínculos e anexo desta transação.
    lot_id = create_physical_lot(connection, actor, unit_id, first['epi_id'], lot, len(items), now,
                                 source='regularization')
    results = []
    for item in items:
        result = regularize_item_physical_validity(
            connection, item, lot['physical_expiry_date'], lot['expiry_evidence'], justification,
            actor['id'], actor.get('full_name', ''), actor.get('role', ''), now,
        )
        link_piece_to_lot(connection, item['id'], lot_id, lot['lot_code'])
        results.append({'id': item['id'], **result})
    save_lot_file(connection, actor, lot_id, items[0]['id'], file, justification, now,
                  before={'items': [{k: str(i.get(k) or '') for k in
                          ('id', 'qr_code_value', 'lot_code', 'lot_id', 'physical_expiry_date', 'status')}
                          for i in items]})
    return {'ok': True, 'lot_id': lot_id, 'count': len(items), 'items': results, 'idempotent': False}


def lot_evidence_list(connection, company_id, unit_id=None):
    params = [company_id]
    clause = ''
    if unit_id:
        clause = ' AND l.receipt_unit_id=?'
        params.append(unit_id)
    rows = connection.execute(
        'SELECT l.id,l.lot_code,l.epi_id,l.receipt_unit_id,l.physical_expiry_date,l.expiry_source,'
        'l.expiry_evidence,l.received_quantity,l.received_at,e.name AS epi_name,u.name AS unit_name,'
        "COALESCE((SELECT v.actor_name_snapshot FROM epi_stock_events v WHERE v.company_id=l.company_id "
        "AND v.lot_id=l.id AND v.reason_code='lot_evidence' ORDER BY v.id LIMIT 1),a.full_name) AS actor_name,"
        "EXISTS(SELECT 1 FROM epi_stock_events v WHERE v.company_id=l.company_id AND v.lot_id=l.id AND v.reason_code='lot_evidence') AS has_file "
        'FROM epi_stock_lots l JOIN epis e ON e.id=l.epi_id JOIN units u ON u.id=l.receipt_unit_id '
        'JOIN users a ON a.id=l.received_by_user_id WHERE l.company_id=?' + clause +
        ' ORDER BY l.id DESC LIMIT 200', tuple(params),
    ).fetchall()
    return [{**row_to_dict(r), 'physical_expiry_date': str(r['physical_expiry_date'] or ''),
             'received_at': str(r['received_at'] or '')} for r in rows]


def reconcile_untracked_lot(connection, actor, unit_id, payload):
    """Individualiza saldo existente, explicitamente contado, sem aumentar saldo.

    O delta vem da mesma fonte conservadora das reservas/entregas. A chave de
    idempotência impede que um reenvio consuma novamente o restante do delta.
    """
    from modules.epis.service import ensure_epi_operational
    from modules.units.service import ensure_unit_operational
    from modules.stock.reservations import unit_balance
    from modules.stock.service import (
        _append_stock_event, build_stock_item_qr, create_stock_item, next_company_qr_sequence,
        record_received_item_physical, resolve_item_size,
    )
    key = payload.get('idempotency_key')
    if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,100}', key):
        raise ValueError('Chave de idempotência da conciliação inválida.')
    quantity, epi_id = payload.get('quantity'), payload.get('epi_id')
    if type(quantity) is not int or not 1 <= quantity <= 100 or type(epi_id) is not int:
        raise ValueError('Informe o EPI e de 1 a 100 peças fisicamente contadas deste lote.')
    if payload.get('physical_lot_confirmed') is not True:
        raise ValueError('Confirme a contagem física e a comprovação do lote.')
    file = validate_evidence_file(payload.get('evidence_file'), required=True)
    lot = validate_manual_lot(connection, {**payload, 'expiry_evidence': payload.get('evidence')})
    justification = str(payload.get('justification') or '').strip()
    size = resolve_item_size(payload.get('glove_size'), payload.get('size'), payload.get('uniform_size'))
    if not lot['physical_expiry_date'] or not justification or not size['selected_size']:
        raise ValueError('Informe validade comprovada, justificativa e tamanho fisicamente conferido.')
    lot['expiry_evidence'] = proof_reference(lot['expiry_evidence'], file)
    lock_stock_scope(connection, actor['company_id'], unit_id, epi_id)
    ensure_unit_operational(connection, unit_id, 'conciliação de peças sem QR')
    ensure_epi_operational(connection, epi_id, 'conciliação de peças sem QR')
    existing = connection.execute('SELECT * FROM epi_stock_lots WHERE company_id=? AND receipt_key=?',
                                  (actor['company_id'], 'reconcile-' + key)).fetchone()
    if existing:
        original = connection.execute('SELECT glove_size,size,uniform_size FROM epi_stock_items WHERE lot_id=? LIMIT 1',
                                       (existing['id'],)).fetchone()
        if (int(existing['epi_id']) != epi_id or int(existing['receipt_unit_id']) != unit_id
                or int(existing['received_quantity']) != quantity or existing['lot_code'] != lot['lot_code']
                or str(existing['physical_expiry_date']) != lot['physical_expiry_date']
                or existing['expiry_source'] != lot['expiry_source']
                or existing['expiry_evidence'] != lot['expiry_evidence']
                or str(existing['manufacture_date'] or '') != str(lot.get('physical_manufacture_date') or '')
                or not original or any(str(original[k]) != str(size[k]) for k in ('glove_size', 'size', 'uniform_size'))):
            raise ValueError('Chave de conciliação reutilizada com dados diferentes.')
        return {'ok': True, 'lot_id': int(existing['id']), 'count': quantity, 'idempotent': True,
                'qr_labels': reconciled_labels(connection, existing['id'])}
    balance = unit_balance(connection, actor['company_id'], unit_id, epi_id)
    if quantity > balance['reconciliation_delta']:
        raise ValueError('Quantidade excede o saldo sem peças/QR; concilie apenas o que falta individualizar.')
    now = datetime.now(timezone.utc).isoformat()
    lot_id = create_physical_lot(connection, actor, unit_id, epi_id, lot, quantity, now,
                                 source='regularization', receipt_key='reconcile-' + key)
    labels = []
    for _ in range(quantity):
        sequence = next_company_qr_sequence(connection, actor['company_id'])
        qr = build_stock_item_qr(actor['company_id'], unit_id, sequence)
        item_id = create_stock_item(connection, actor['company_id'], unit_id, epi_id,
                                    size['glove_size'], size['size'], size['uniform_size'],
                                    sequence, qr, None, lot['lot_code'], payload.get('manufacture_date') or '',
                                    'unidade', '', '', actor['id'], now)
        record_received_item_physical(connection, item_id, lot['physical_expiry_date'], actor['id'], now,
                                       evidence=lot['expiry_evidence'])
        connection.execute('UPDATE epi_stock_items SET expiry_source=?,physical_manufacture_date=? WHERE id=?',
                           (lot['expiry_source'], lot.get('physical_manufacture_date'), item_id))
        link_piece_to_lot(connection, item_id, lot_id, lot['lot_code'])
        _append_stock_event(connection, company_id=actor['company_id'], epi_id=epi_id,
                            stock_item_id=item_id, event_type='reconcile', reason_code='missing_qr',
                            justification=justification, actor_user_id=actor['id'],
                            actor_name=actor.get('full_name', ''), actor_role=actor.get('role', ''),
                            now=now, origin_unit_id=unit_id, before_values=balance,
                            after_values={**lot, 'lot_id': lot_id, 'qr_code_value': qr})
        labels.append({'stock_item_id': item_id, 'qr_code_value': qr, 'lot_code': lot['lot_code'],
                       'physical_expiry_date': lot['physical_expiry_date'], **size})
    save_lot_file(connection, actor, lot_id, labels[0]['stock_item_id'], file, justification, now,
                  before=balance, event_type='reconcile')
    return {'ok': True, 'lot_id': lot_id, 'count': quantity, 'idempotent': False,
            'physical_stock': balance['physical'], 'qr_labels': reconciled_labels(connection, lot_id)}


def reconciled_labels(connection, lot_id):
    rows = connection.execute(
        'SELECT i.id AS stock_item_id,i.qr_code_value,i.glove_size,i.size,i.uniform_size,i.lot_code,'
        'i.physical_expiry_date,i.manufacture_date,i.label_measure,i.label_printer_name,i.label_print_format,'
        'e.name AS epi_name,u.name AS unit_name FROM epi_stock_items i JOIN epis e ON e.id=i.epi_id '
        'JOIN units u ON u.id=i.unit_id WHERE i.lot_id=? ORDER BY i.id', (lot_id,),
    ).fetchall()
    return [{**row_to_dict(r), 'physical_expiry_date': str(r['physical_expiry_date'] or '')} for r in rows]


def lot_evidence_file(connection, company_id, unit_id, lot_id):
    lot = connection.execute('SELECT receipt_unit_id FROM epi_stock_lots WHERE id=? AND company_id=?',
                             (lot_id, company_id)).fetchone()
    if lot is None or (unit_id and int(lot['receipt_unit_id']) != int(unit_id)):
        raise PermissionError('Lote fora da empresa/unidade autorizada.')
    row = connection.execute("SELECT after_values FROM epi_stock_events WHERE company_id=? AND lot_id=? "
                             "AND reason_code='lot_evidence' ORDER BY id LIMIT 1", (company_id, lot_id)).fetchone()
    if row is None:
        raise ValueError('Este lote ainda não possui anexo.')
    data = row['after_values']
    data = json.loads(data) if isinstance(data, str) else data
    file = data['evidence_file']
    verified = validate_evidence_file(file, required=True)
    if verified['sha256'] != file['sha256']:
        raise ValueError('Falha de integridade do anexo.')
    return verified
