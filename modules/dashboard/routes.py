"""Rota de resumo do Dashboard (fatia 1.1D-B)."""

from contextlib import closing
from urllib.parse import parse_qs

from core.database import get_connection
from core.permissions import PERMISSIONS
from core.repository import authorize_action, get_unit_active_jv_name
from core.security import resolve_actor_user_id
from epi_backend.epi_scope import is_epi_visible_for_unit
from epi_backend.http_utils import send_json
from modules.dashboard.service import build_dashboard_summary


def handle_get_dashboard_summary(handler, parsed, payload, match):
    """Resumo do Dashboard com escopo, KPIs e fontes do filtro.

    O `DashboardCubit` (Flutter) consome esta rota desde a fatia 1.1D-C2. O
    `dashboard.js` (Web Legado) ainda não — é a 1.1D-C3 — e por isso
    `/api/bootstrap` continua emitindo tudo o que emitia. Remover campo de lá é
    a 1.1E, depois que o último cliente sair.

    Autorização por `dashboard:view`, a mesma permissão que o bootstrap já
    exige para montar o painel.
    """
    from modules.alerts.service import compute_alerts as _compute_alerts
    from modules.deliveries.service import fetch_deliveries
    from modules.employees.service import (
        actor_has_no_operational_unit,
        actor_operational_unit_id,
        fetch_employees,
    )
    from modules.epis.service import fetch_epis
    from modules.legal_entities.service import fetch_legal_entities
    from modules.purchases.service import (
        actor_has_no_purchase_unit_scope,
        count_pending_purchase_requests,
        get_actor_purchase_unit_scope,
        narrow_purchase_unit_to_selection,
    )
    from modules.stock.service import compute_stock_compliance, fetch_low_stock_items
    from modules.units.service import fetch_units

    with closing(get_connection()) as connection:
        actor = authorize_action(
            connection, resolve_actor_user_id(handler, parsed), 'dashboard:view'
        )
        query = parse_qs(parsed.query)

        def compute_alerts(conn, act):
            # Fiação idêntica à do bootstrap, de propósito: `alerts` sai desta
            # fatia com a MESMA regra, inclusive o cruzamento de saldo local com
            # mínimo corporativo que `fetch_low_stock_items` ainda faz. Corrigir
            # aqui e não no bootstrap faria o mesmo painel mostrar números
            # diferentes conforme a fonte, durante toda a janela de migração.
            return _compute_alerts(
                conn, act,
                fetch_low_stock_items=lambda c, a: fetch_low_stock_items(
                    c, a,
                    actor_operational_unit_id=actor_operational_unit_id,
                    get_unit_active_jv_name=get_unit_active_jv_name,
                    is_epi_visible_for_unit=is_epi_visible_for_unit,
                ),
                actor_operational_unit_id=actor_operational_unit_id,
                fetch_epis=fetch_epis,
            )

        carteira_de_compras = get_actor_purchase_unit_scope(connection, actor)

        def count_pending_purchases(unidade_selecionada=None):
            # Mesmas guardas do bootstrap: sem permissão, sem empresa ou sem
            # escopo de compras o KPI é 0 — nunca a contagem da empresa inteira.
            if 'purchase_requests:view' not in PERMISSIONS.get(actor.get('role'), set()):
                return 0
            company_id = actor.get('company_id')
            if not company_id:
                return 0
            scope_unit_id = actor_operational_unit_id(connection, actor)
            if actor_has_no_purchase_unit_scope(
                actor, scope_unit_id, carteira_de_compras
            ) or actor_has_no_operational_unit(actor, scope_unit_id):
                return 0
            # A Unidade escolhida no seletor manda sobre o escopo derivado do
            # ator — e a regra de quando ela manda mora em Compras, testada
            # lá, porque uma decisão dentro desta closure não é exercitável.
            return count_pending_purchase_requests(
                connection, company_id,
                narrow_purchase_unit_to_selection(
                    scope_unit_id, unidade_selecionada, carteira_de_compras),
                carteira_de_compras,
            )

        resumo = build_dashboard_summary(
            connection,
            actor,
            requested_unit_id=query.get('unit_id', [''])[0],
            requested_legal_entity_id=query.get('legal_entity_id', [''])[0],
            requested_sector=query.get('sector', [''])[0],
            purchase_scope_units=carteira_de_compras,
            fetch_units=fetch_units,
            fetch_employees=fetch_employees,
            fetch_epis=fetch_epis,
            fetch_deliveries=fetch_deliveries,
            fetch_legal_entities=fetch_legal_entities,
            compute_alerts=compute_alerts,
            compute_stock_compliance=compute_stock_compliance,
            count_pending_purchases=count_pending_purchases,
        )
        return send_json(handler, 200, resumo)


def register_routes(router):
    router.register('GET', '/api/dashboard/summary', handle_get_dashboard_summary)
