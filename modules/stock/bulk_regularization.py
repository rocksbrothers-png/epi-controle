"""Um envio atômico de lotes explícitos, cada um com comprovação própria."""
from modules.stock.eligibility import lock_stock_scope
from modules.stock.lot_evidence import regularize_selected_lot, validate_evidence_file


def regularize_multiple_lots(connection, actor, unit_id, payload):
    lots = payload.get('lots')
    if not isinstance(lots, list) or not 1 <= len(lots) <= 10:
        raise ValueError('Selecione de 1 a 10 lotes para regularizar em um envio.')
    seen, epi_ids, file_bytes = set(), set(), 0
    for lot in lots:
        if not isinstance(lot, dict) or not isinstance(lot.get('items'), list) or not lot['items']:
            raise ValueError('Identifique as peças de cada lote selecionado.')
        try:
            other_company = lot.get('company_id') and int(lot['company_id']) != int(actor['company_id'])
            other_unit = lot.get('unit_id') and int(lot['unit_id']) != int(unit_id)
        except (TypeError, ValueError):
            raise ValueError('Empresa/unidade do lote inválida.') from None
        if other_company or other_unit:
            raise PermissionError('Lote fora da empresa/unidade autorizada.')
        for item in lot['items']:
            if not isinstance(item, dict) or type(item.get('stock_item_id')) is not int:
                raise ValueError('Seleção de peça inválida.')
            item_id = item['stock_item_id']
            if item_id in seen:
                raise ValueError('A mesma peça não pode pertencer a dois lotes do envio.')
            seen.add(item_id)
        if len(seen) > 500:
            raise ValueError('Selecione no máximo 500 peças por envio.')
        file_bytes += validate_evidence_file(lot.get('evidence_file'), required=True)['size']
        if file_bytes > 12 * 1024 * 1024:
            raise ValueError('Os anexos do envio devem somar no máximo 12 MiB.')
        first = connection.execute('SELECT epi_id FROM epi_stock_items WHERE id=? AND company_id=? AND unit_id=?',
                                   (lot['items'][0]['stock_item_id'], actor['company_id'], unit_id)).fetchone()
        if first is None:
            raise PermissionError('Peça fora da empresa/unidade autorizada.')
        epi_ids.add(int(first['epi_id']))
    # Ordenação comum antes de qualquer escrita evita deadlock entre envios
    # sobre os mesmos EPIs em ordens opostas. Cada serviço mantém seus gates.
    for epi_id in sorted(epi_ids):
        lock_stock_scope(connection, actor['company_id'], unit_id, epi_id)
    results = [regularize_selected_lot(connection, actor, unit_id, lot) for lot in lots]
    return {'ok': True, 'lots': results, 'count': sum(r['count'] for r in results),
            'idempotent': all(r['idempotent'] for r in results)}
