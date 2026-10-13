"""Serviços de alertas operacionais."""

from datetime import date

from modules.stock.service import (
    STATUS_CRITICAL,
    STATUS_NEAR_MINIMUM,
)

from modules.stock.eligibility import physical_summary_map

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
    scope_unit_id = actor_operational_unit_id(connection, actor)
    if actor and actor.get('role') in ('admin', 'user') and not scope_unit_id:
        return alerts
    low_stock_items = fetch_low_stock_items(connection, actor)
    for item in low_stock_items:
        stock = int(item['stock'])
        minimum = int(item['minimum_stock'])
        # Severidade derivada de `stock_status`, que vem da fonte única (#271).
        # Antes daqui saía uma comparação própria (`stock < minimum`) sobre o
        # saldo da Unidade e o mínimo da EMPRESA — segunda implementação da
        # mesma regra, e com o operando errado.
        #
        # `disabled` nunca chega aqui: `fetch_low_stock_items` já o descarta.
        # O rótulo textual continua distinguindo saldo negativo/zerado, que é
        # informação útil ao operador e não é uma classificação concorrente —
        # os três casos são todos `critical`.
        status = item.get('stock_status') or STATUS_CRITICAL
        if status == STATUS_NEAR_MINIMUM:
            type_label = 'warning'
            prefix = 'Estoque próximo do mínimo'
        elif stock < 0:
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
            'category': 'stock',
            'title': f"{prefix}: {item['epi_name']}",
            'description': f"{item['company_name']} / {item['unit_name']} - saldo atual de {stock} {item['unit_measure']}(s), mínimo {minimum}.{size_info}",
            'company_id': item.get('company_id'),
            'unit_id': item.get('unit_id'),
            'epi_id': item.get('epi_id'),
            'epi_name': item.get('epi_name'),
            'size_balances': size_balances,
        })

    # EST-V3.5 (G02): a validade do fabricante que rege o alerta é a FÍSICA do
    # lote em estoque (a mais próxima de vencer, FEFO), não o catálogo — que
    # permanece um atributo cadastral separado. O resumo físico mantém lotes
    # desconhecidos e vencidos, sem usar o catálogo como substituto.
    phys_validity = physical_summary_map(connection, None, scope_unit_id)
    for epi in fetch_epis(connection, actor, scope_unit_id):
        if int(epi.get('active', 1) or 0) != 1:
            continue
        # Validade do CA: relevante para a aquisição/compra do EPI (NT 146/2015).
        ca_days = days_until(epi.get('ca_expiry'), today)
        if ca_days is not None and ca_days <= 30:
            alerts.append({
                'type': 'danger' if ca_days <= 7 else 'warning',
                'category': 'ca',
                'title': f"CA próximo do vencimento: {epi['name']}",
                'description': f"{epi['company_name']} - vence em {epi['ca_expiry']}.",
                'company_id': epi.get('company_id'),
                'unit_id': epi.get('unit_id'),
                'epi_id': epi.get('id'),
                'epi_name': epi.get('name'),
            })
        # Validade do fabricante: rege o uso/entrega do EPI (NT 146/2015). EPIs
        # com validade mais próxima devem sair primeiro do estoque (PEPS) e os já
        # vencidos devem ser retirados do estoque, pois não podem ser entregues.
        # EST-V3.5 (G02): usa a validade FÍSICA do lote mais próximo de vencer em
        # estoque; o catálogo nunca substitui uma data física ausente.
        physical = phys_validity.get(int(epi.get('id') or 0), {})
        effective_mv = physical.get('nearest_known_expiry')
        reference = date.fromisoformat(physical['as_of_date']) if physical else today
        mv_days = days_until(effective_mv, reference)
        if mv_days is not None and mv_days <= physical.get('warning_days', MANUFACTURER_VALIDITY_WARNING_DAYS):
            stock = int(epi.get('stock') or 0)
            unit_measure = str(epi.get('unit_measure') or 'unidade')
            if mv_days < 0:
                alerts.append({
                    'type': 'danger',
                    'category': 'manufacturer',
                    'title': f"Validade do fabricante vencida: {epi['name']}",
                    'description': (
                        f"{epi['company_name']} - validade do fabricante venceu em "
                        f"{effective_mv}. Retire do estoque ({stock} {unit_measure}(s)): "
                        f"EPI vencido não pode ser entregue ao trabalhador."
                    ),
                    'company_id': epi.get('company_id'),
                    'unit_id': epi.get('unit_id'),
                    'epi_id': epi.get('id'),
                    'epi_name': epi.get('name'),
                })
            else:
                alerts.append({
                    'type': 'danger' if mv_days <= 7 else 'warning',
                    'category': 'manufacturer',
                    'title': f"Validade do fabricante próxima: {epi['name']}",
                    'description': (
                        f"{epi['company_name']} - validade do fabricante vence em "
                        f"{effective_mv} (em {mv_days} dia(s)). Priorize a entrega "
                        f"deste lote ({stock} {unit_measure}(s) em estoque) antes do vencimento (PEPS)."
                    ),
                    'company_id': epi.get('company_id'),
                    'unit_id': epi.get('unit_id'),
                    'epi_id': epi.get('id'),
                    'epi_name': epi.get('name'),
                })
        for category, count in [('physical_unknown', physical.get('unknown', 0)),
                                ('physical_expiring', physical.get('expiring', 0) if mv_days is not None and mv_days < 0 else 0)]:
            if count:
                alerts.append({'type': 'warning', 'category': category,
                    'title': 'Validade física desconhecida' if category == 'physical_unknown' else 'Lotes próximos do vencimento',
                    'description': f"{epi['name']}: {count} peça(s) física(s).",
                    'company_id': epi.get('company_id'), 'unit_id': scope_unit_id,
                    'epi_id': epi.get('id'), 'epi_name': epi.get('name')})

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
        # `include_near_minimum=True`: a faixa laranja existe justamente para
        # gerar alerta preventivo. `/api/stock/low` segue com o padrão False,
        # porque lá o card do Web Legado conta a lista como "Estoque crítico".
        fetch_low_stock_items=lambda conn, act: _fetch_ls(
            conn, act,
            actor_operational_unit_id=_op_unit,
            get_unit_active_jv_name=_jv_name,
            is_epi_visible_for_unit=_vis,
            include_near_minimum=True,
        ),
        actor_operational_unit_id=_op_unit,
        fetch_epis=_fetch_epis,
    )
