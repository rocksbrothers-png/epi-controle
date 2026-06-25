"""Serviços de alertas operacionais."""

from datetime import date

from modules.epis.validity import (
    MANUFACTURER_VALIDITY_WARNING_DAYS,
    days_until,
)


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
        # Validade do CA: relevante para a aquisição/compra do EPI (NT 146/2015).
        ca_days = days_until(epi.get('ca_expiry'), today)
        if ca_days is not None and ca_days <= 30:
            alerts.append({
                'type': 'danger' if ca_days <= 7 else 'warning',
                'title': f"CA próximo do vencimento: {epi['name']}",
                'description': f"{epi['company_name']} - vence em {epi['ca_expiry']}.",
                'company_id': epi.get('company_id'),
                'unit_id': epi.get('unit_id'),
                'epi_id': epi.get('id'),
            })
        # Validade do fabricante: rege o uso/entrega do EPI (NT 146/2015). EPIs
        # com validade mais próxima devem sair primeiro do estoque (PEPS) e os já
        # vencidos devem ser retirados do estoque, pois não podem ser entregues.
        mv_days = days_until(epi.get('epi_validity_date'), today)
        if mv_days is not None and mv_days <= MANUFACTURER_VALIDITY_WARNING_DAYS:
            stock = int(epi.get('stock') or 0)
            unit_measure = str(epi.get('unit_measure') or 'unidade')
            if mv_days < 0:
                alerts.append({
                    'type': 'danger',
                    'title': f"Validade do fabricante vencida: {epi['name']}",
                    'description': (
                        f"{epi['company_name']} - validade do fabricante venceu em "
                        f"{epi['epi_validity_date']}. Retire do estoque ({stock} {unit_measure}(s)): "
                        f"EPI vencido não pode ser entregue ao trabalhador."
                    ),
                    'company_id': epi.get('company_id'),
                    'unit_id': epi.get('unit_id'),
                    'epi_id': epi.get('id'),
                })
            else:
                alerts.append({
                    'type': 'danger' if mv_days <= 7 else 'warning',
                    'title': f"Validade do fabricante próxima: {epi['name']}",
                    'description': (
                        f"{epi['company_name']} - validade do fabricante vence em "
                        f"{epi['epi_validity_date']} (em {mv_days} dia(s)). Priorize a entrega "
                        f"deste lote ({stock} {unit_measure}(s) em estoque) antes do vencimento (PEPS)."
                    ),
                    'company_id': epi.get('company_id'),
                    'unit_id': epi.get('unit_id'),
                    'epi_id': epi.get('id'),
                })
    return alerts


def compute_alerts_wired(connection, actor=None):
    from modules.stock.service import fetch_low_stock_items as _fetch_ls
    from modules.employees.service import actor_operational_unit_id as _op_unit
    from modules.units.service import get_unit_active_jv_name as _jv_name
    from epi_backend.epi_scope import is_epi_visible_for_unit as _vis
    from modules.epis.service import fetch_epis as _fetch_epis
    return compute_alerts(
        connection,
        actor,
        fetch_low_stock_items=lambda conn, act: _fetch_ls(
            conn, act,
            actor_operational_unit_id=_op_unit,
            get_unit_active_jv_name=_jv_name,
            is_epi_visible_for_unit=_vis,
        ),
        actor_operational_unit_id=_op_unit,
        fetch_epis=_fetch_epis,
    )
