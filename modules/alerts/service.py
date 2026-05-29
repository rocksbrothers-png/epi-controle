"""Serviços de alertas operacionais."""

from datetime import date, datetime


def compute_alerts(
    connection,
    actor=None,
    *,
    fetch_low_stock_items,
    actor_operational_unit_id,
    fetch_epis,
):
    alerts = []
    today = date.today()
    low_stock_items = fetch_low_stock_items(connection, actor)
    for item in low_stock_items:
        stock = int(item['stock'])
        minimum = int(item['minimum_stock'])
        if stock < 0:
            type_label = 'danger'
            prefix = 'Saldo negativo'
        elif stock == 0:
            type_label = 'danger'
            prefix = 'Estoque zerado'
        elif stock < minimum:
            type_label = 'danger'
            prefix = 'Estoque abaixo do mínimo'
        else:
            type_label = 'warning'
            prefix = 'Estoque no limite mínimo'
        size_balances = item.get('size_balances') or []
        size_parts = []
        for sb in size_balances:
            parts = []
            if sb.get('glove_size') and sb['glove_size'] != 'N/A':
                parts.append(f"Luva:{sb['glove_size']}")
            if sb.get('size') and sb['size'] != 'N/A':
                parts.append(f"Tam:{sb['size']}")
            if sb.get('uniform_size') and sb['uniform_size'] != 'N/A':
                parts.append(f"Unif:{sb['uniform_size']}")
            label = ' '.join(parts) or 'S/Tam'
            size_parts.append(f"{label}×{sb.get('quantity', 0)}")
        size_info = f" | Tamanhos em estoque: {', '.join(size_parts)}" if size_parts else ''
        alerts.append({
            'type': type_label,
            'title': f"{prefix}: {item['epi_name']}",
            'description': f"{item['company_name']} / {item['unit_name']} - saldo atual de {stock} {item['unit_measure']}(s), mínimo {minimum}.{size_info}",
            'company_id': item.get('company_id'),
            'unit_id': item.get('unit_id'),
            'epi_id': item.get('epi_id'),
            'size_balances': size_balances,
        })

    scope_unit_id = actor_operational_unit_id(connection, actor)
    for epi in fetch_epis(connection, actor, scope_unit_id):
        if int(epi.get('active', 1) or 0) != 1:
            continue
        ca_expiry = str(epi.get('ca_expiry') or '').strip()
        if not ca_expiry:
            continue
        days = (datetime.strptime(ca_expiry, '%Y-%m-%d').date() - today).days
        if days <= 30:
            alerts.append({
                'type': 'danger' if days <= 7 else 'warning',
                'title': f"CA próximo do vencimento: {epi['name']}",
                'description': f"{epi['company_name']} - vence em {epi['ca_expiry']}.",
                'company_id': epi.get('company_id'),
                'unit_id': epi.get('unit_id'),
                'epi_id': epi.get('id'),
            })
    return alerts
