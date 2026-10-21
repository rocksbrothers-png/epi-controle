"""Planos físicos da conferência de PO, sem recapturar dados por peça."""
from epi_backend.db import row_to_dict
from modules.purchases.receipt_capture import validate_capture_budget
from modules.stock.eligibility import lock_stock_scope


def prepare_po_receipt(connection, po, flags):
    from modules.purchases.service import _resolve_receipt_piece_plan

    rows = [row_to_dict(r) for r in connection.execute(
        'SELECT * FROM purchase_order_items WHERE purchase_order_id=? ORDER BY id', (po['id'],)).fetchall()]
    if not isinstance(flags, list) or any(not isinstance(flag, dict) for flag in flags):
        raise ValueError('Linhas de conferência da PO inválidas.')
    valid_ids = {int(row['id']) for row in rows}
    by_id = {}
    for flag in flags:
        if type(flag.get('id')) is not int or flag['id'] not in valid_ids or flag['id'] in by_id:
            raise ValueError('Item duplicado ou fora da PO na conferência.')
        if flag.get('received') is False:
            raise ValueError('Ajuste a quantidade recebida antes de conferir a PO.')
        lots = flag.get('lots') or []
        if not isinstance(lots, list) or any(not isinstance(lot, dict) for lot in lots):
            raise ValueError('Lotes da PO inválidos.')
        by_id[flag['id']] = flag
    validate_capture_budget(flags)
    plans = {}
    for row in rows:
        quantity = int(row.get('quantity_received') or 0)
        if quantity <= 0:
            continue
        flag = by_id.get(int(row['id']), {})
        if flags and not flag:
            raise ValueError('Confira todos os itens efetivamente recebidos da PO.')
        plans[int(row['id'])] = _resolve_receipt_piece_plan(flag.get('lots') or [], quantity,
            legacy_validity=str(flag.get('manufacturer_validity_date') or row.get('manufacturer_validity_date') or '').strip(),
            legacy_evidence=str(flag.get('evidence') or 'Conferência de PO ' + str(po['id'])))
    for epi_id, unit_id in sorted({(int(row['epi_id']), int(row['unit_id'])) for row in rows if int(row['id']) in plans}):
        lock_stock_scope(connection, po['company_id'], unit_id, epi_id)
    return plans
