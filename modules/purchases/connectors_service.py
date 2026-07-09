"""Fase F4 do módulo de Compras — Nível 3 (API direta com lojas de EPI).

Orquestra os conectores (epi_backend/supplier_connectors) sobre o MESMO fluxo
interno das fases F1/F2: a cotação via API preenche purchase_quote_items pelo
answer_quote; o pedido via API grava os campos paralelos de envio e registra
purchase_order_confirmations (source='api'). Máquinas de estado intactas.
Credenciais cifradas por tenant (epi_backend/connector_crypto) — a config em
claro só existe em memória durante a chamada.
"""

from datetime import datetime, timezone

from epi_backend.connector_crypto import (
    decrypt_connector_config,
    encrypt_connector_config,
)
from epi_backend.db import row_to_dict
from epi_backend.supplier_connectors import (
    ConnectorError,
    available_connectors,
    get_connector,
)

from modules.purchases.quotes_service import (
    PO_SENDABLE_STATUSES,
    answer_quote,
    fetch_quote_items,
    get_quote_by_id,
    get_supplier_by_id,
    register_po_confirmation,
    upsert_supplier_product,
    _po_items,
)
from modules.purchases.service import (
    _record_purchase_event,
    get_purchase_order_by_id,
)

UTC = timezone.utc


def _now():
    return datetime.now(UTC).isoformat()


# ── Configuração da integração (CRUD cifrado) ────────────────────────────────

def list_available_connectors():
    return available_connectors()


def get_supplier_integration(connection, company_id, supplier_id, include_config=False):
    row = connection.execute(
        'SELECT * FROM supplier_integrations WHERE company_id = ? AND supplier_id = ?',
        (int(company_id), int(supplier_id))
    ).fetchone()
    if not row:
        return None
    integration = row_to_dict(row)
    config_token = integration.pop('config_encrypted', '')
    integration['has_config'] = bool(str(config_token or '').strip())
    if include_config:
        integration['config'] = decrypt_connector_config(company_id, config_token)
    return integration


def upsert_supplier_integration(connection, actor, company_id, supplier_id, payload):
    """Cria/atualiza a integração do fornecedor (1 por fornecedor)."""
    supplier = get_supplier_by_id(connection, company_id, supplier_id)
    if not supplier:
        raise ValueError('Fornecedor não encontrado.')
    connector_key = str(payload.get('connector_key') or '').strip()
    # valida a key contra o registro (levanta ValueError se desconhecida)
    get_connector(connector_key, {})
    active = 1 if payload.get('active') in (1, '1', True, 'true') else 0
    now = _now()
    existing = connection.execute(
        'SELECT id FROM supplier_integrations WHERE company_id = ? AND supplier_id = ?',
        (int(company_id), int(supplier_id))
    ).fetchone()
    config = payload.get('config')
    if existing:
        updates = ['connector_key = ?', 'active = ?', 'updated_at = ?']
        params = [connector_key, active, now]
        if config is not None:
            updates.append('config_encrypted = ?')
            params.append(encrypt_connector_config(company_id, config))
        params.append(int(existing['id']))
        connection.execute(
            f"UPDATE supplier_integrations SET {', '.join(updates)} WHERE id = ?",
            tuple(params)
        )
    else:
        connection.execute(
            'INSERT INTO supplier_integrations (company_id, supplier_id, connector_key, '
            'config_encrypted, active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (int(company_id), int(supplier_id), connector_key,
             encrypt_connector_config(company_id, config or {}), active, now, now)
        )
    if active:
        connection.execute(
            "UPDATE authorized_suppliers SET integration_level = 'api', updated_at = ? WHERE id = ?",
            (now, int(supplier_id))
        )
    _record_purchase_event(
        connection, int(company_id), 'supplier', int(supplier_id), 'integration_configured', '', '',
        f'Integração "{connector_key}" {"ativada" if active else "desativada"}.',
        actor.get('id'), actor.get('full_name') or '',
        actor_role=str(actor.get('role') or ''),
    )
    return get_supplier_integration(connection, company_id, supplier_id)


def _active_connector_for_supplier(connection, company_id, supplier_id):
    integration = get_supplier_integration(
        connection, company_id, supplier_id, include_config=True
    )
    if not integration or not int(integration.get('active') or 0):
        raise ValueError('Fornecedor sem integração de API ativa.')
    connector = get_connector(integration['connector_key'], integration.get('config') or {})
    return connector, integration


def ping_supplier_integration(connection, company_id, supplier_id):
    """Ping de conectividade. Retorna dict {ok, connector_key}."""
    connector, integration = _active_connector_for_supplier(connection, company_id, supplier_id)
    try:
        connector.ping()
    except ConnectorError as exc:
        raise ValueError(f'Teste da integração falhou: {exc}') from exc
    return {'ok': True, 'connector_key': integration['connector_key']}


def _touch_last_sync(connection, integration_id):
    connection.execute(
        'UPDATE supplier_integrations SET last_sync_at = ? WHERE id = ?',
        (_now(), int(integration_id))
    )


# ── Operações do Nível 3 sobre o fluxo existente ─────────────────────────────

def sync_catalog_from_connector(connection, actor, company_id, supplier_id):
    """Importa o catálogo da loja para supplier_products (upsert por SKU)."""
    connector, integration = _active_connector_for_supplier(connection, company_id, supplier_id)
    try:
        catalog = connector.get_catalog()
    except ConnectorError as exc:
        raise ValueError(f'Falha ao consultar o catálogo da loja: {exc}') from exc
    imported = 0
    for product in catalog:
        if not str(product.get('supplier_sku') or '').strip():
            continue
        upsert_supplier_product(connection, actor, company_id, supplier_id, product)
        imported += 1
    _touch_last_sync(connection, integration['id'])
    _record_purchase_event(
        connection, int(company_id), 'supplier', int(supplier_id), 'catalog_synced', '', '',
        f'Catálogo sincronizado via API ({imported} produtos).',
        actor.get('id'), actor.get('full_name') or '',
        actor_role=str(actor.get('role') or ''),
    )
    return {'imported': imported}


def quote_via_connector(connection, actor, quote_id, ip_address=''):
    """Cota preço/estoque/prazo direto na loja e responde a cotação.

    Usa o MESMO answer_quote do Nível 1 (guardas de status preservadas);
    apenas o canal muda para 'api'.
    """
    quote = get_quote_by_id(connection, int(quote_id))
    if not quote:
        raise ValueError('Cotação não encontrada.')
    company_id = int(quote['company_id'])
    connector, integration = _active_connector_for_supplier(
        connection, company_id, int(quote['supplier_id'])
    )
    items = fetch_quote_items(connection, int(quote_id))
    try:
        answers = connector.get_price_and_stock(items)
    except ConnectorError as exc:
        raise ValueError(f'Falha ao cotar na loja: {exc}') from exc
    result = answer_quote(
        connection, actor, int(quote_id),
        {'items': answers, 'source': f"api:{integration['connector_key']}"},
        ip_address,
    )
    now = _now()
    connection.execute(
        "UPDATE purchase_quotes SET channel = 'api', sent_at = CASE WHEN sent_at = '' THEN ? ELSE sent_at END, "
        'updated_at = ? WHERE id = ?',
        (now, now, int(quote_id))
    )
    _touch_last_sync(connection, integration['id'])
    return get_quote_by_id(connection, int(quote_id))


def _po_supplier_id(connection, company_id, po):
    supplier_cnpj = ''.join(ch for ch in str(po.get('supplier_cnpj') or '') if ch.isdigit())
    row = connection.execute(
        'SELECT id FROM authorized_suppliers WHERE company_id = ? AND cnpj = ?',
        (int(company_id), supplier_cnpj)
    ).fetchone() if supplier_cnpj else None
    if not row:
        raise ValueError('PO sem fornecedor cadastrado (CNPJ) para integração de API.')
    return int(row['id'])


def send_po_via_connector(connection, actor, po_id, ip_address=''):
    """Cria o pedido na loja via API; grava campos paralelos, status intacto."""
    po = get_purchase_order_by_id(connection, int(po_id))
    if not po:
        raise ValueError('PO não encontrada.')
    if str(po.get('status') or '') not in PO_SENDABLE_STATUSES:
        raise ValueError('Apenas POs aprovadas podem ser enviadas ao fornecedor.')
    company_id = int(po['company_id'])
    supplier_id = _po_supplier_id(connection, company_id, po)
    connector, integration = _active_connector_for_supplier(connection, company_id, supplier_id)
    items = _po_items(connection, int(po_id))
    try:
        result = connector.create_order(po, items)
    except ConnectorError as exc:
        raise ValueError(f'Falha ao criar o pedido na loja: {exc}') from exc
    now = _now()
    connection.execute(
        "UPDATE purchase_orders SET sent_to_supplier_at = ?, sent_channel = 'api', "
        'supplier_order_ref = ?, updated_at = ? WHERE id = ?',
        (now, str(result.get('supplier_order_ref') or ''), now, int(po_id))
    )
    _record_purchase_event(
        connection, company_id, 'purchase_order', int(po_id), 'po_sent_to_supplier',
        str(po.get('status') or ''), str(po.get('status') or ''),
        f"PO enviada via API ({integration['connector_key']}); "
        f"ref: {result.get('supplier_order_ref') or '-'}.",
        actor.get('id'), actor.get('full_name') or '', ip_address=ip_address,
        actor_role=str(actor.get('role') or ''),
        destination=integration['connector_key'],
    )
    register_po_confirmation(
        connection, actor, int(po_id),
        {
            'status': 'confirmed' if result.get('confirmed') else 'rejected',
            'delivery_forecast': str(result.get('delivery_forecast') or ''),
            'comment': str(result.get('comment') or ''),
        },
        ip_address, source='api',
    )
    _touch_last_sync(connection, integration['id'])
    return get_purchase_order_by_id(connection, int(po_id))


def refresh_po_status_from_connector(connection, actor, po_id, ip_address=''):
    """Consulta o status do pedido na loja e registra na linha do tempo."""
    po = get_purchase_order_by_id(connection, int(po_id))
    if not po:
        raise ValueError('PO não encontrada.')
    order_ref = str(po.get('supplier_order_ref') or '').strip()
    if not order_ref:
        raise ValueError('PO ainda não foi enviada via API (sem referência na loja).')
    company_id = int(po['company_id'])
    supplier_id = _po_supplier_id(connection, company_id, po)
    connector, integration = _active_connector_for_supplier(connection, company_id, supplier_id)
    try:
        status = connector.get_order_status(order_ref)
    except ConnectorError as exc:
        raise ValueError(f'Falha ao consultar o pedido na loja: {exc}') from exc
    register_po_confirmation(
        connection, actor, int(po_id),
        {
            'status': str(status.get('status') or 'delivery_update'),
            'delivery_forecast': str(status.get('delivery_forecast') or ''),
            'carrier': str(status.get('carrier') or ''),
            'tracking_code': str(status.get('tracking_code') or ''),
            'comment': str(status.get('comment') or ''),
        },
        ip_address, source='api',
    )
    _touch_last_sync(connection, integration['id'])
    return get_purchase_order_by_id(connection, int(po_id))
