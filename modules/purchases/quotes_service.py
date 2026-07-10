"""Fase F1 do módulo de Compras — Nível 1 (cadastro manual + e-mail).

Fornecedores ampliados, catálogo de produtos por fornecedor, cotações (RFQ)
com resposta manual/CSV, comparação de preços/prazos, envio de RFQ/PO por
e-mail e confirmação manual de pedido.

Regras preservadas (docs/PLANO_TECNICO_MODULO_COMPRAS.md §1):
  - a máquina de estados de purchase_requests/purchase_orders NÃO muda —
    a cotação vencedora apenas PRÉ-PREENCHE a PO, que segue o fluxo de
    aprovação existente (R1–R3);
  - tudo multi-tenant por company_id (R6) e auditado em purchase_events (R7).
"""

from datetime import datetime, timezone

from core.auth import ensure_resource_company
from core.pdf import build_pdf_document, pdf_safe_text
from epi_backend.db import row_to_dict

from modules.purchases.service import (
    _record_purchase_event,
    ensure_purchase_order_action_scope,
    ensure_purchase_request_action_scope,
    get_purchase_order_by_id,
    get_purchase_request_by_id,
)

UTC = timezone.utc

QUOTE_STATUSES = ('draft', 'sent', 'answered', 'expired', 'declined', 'selected', 'discarded')
QUOTE_FINAL_STATUSES = {'selected', 'discarded', 'declined', 'expired'}
QUOTE_ANSWERABLE_STATUSES = {'draft', 'sent'}
QUOTE_CHANNELS = ('email', 'portal', 'api', 'manual')
CONFIRMATION_STATUSES = ('confirmed', 'rejected', 'delivery_update')
PO_SENDABLE_STATUSES = {'approved', 'partially_approved'}


def _now():
    return datetime.now(UTC).isoformat()


# ── Fornecedores (cadastro ampliado) ─────────────────────────────────────────

def get_supplier_by_id(connection, company_id, supplier_id):
    row = connection.execute(
        'SELECT * FROM authorized_suppliers WHERE id = ? AND company_id = ?',
        (int(supplier_id), int(company_id))
    ).fetchone()
    return row_to_dict(row) if row else None


def resolve_supplier_company_id(connection, actor, supplier_id):
    """company_id efetivo para operações sobre um fornecedor.

    Admins de empresa usam a própria empresa; o master_admin (company_id NULL)
    resolve pela empresa do próprio fornecedor — evita int(None) → 500 e mantém
    o isolamento multi-tenant (o master age sobre a empresa dona do recurso).
    """
    if actor.get('role') != 'master_admin' and actor.get('company_id') is not None:
        return int(actor['company_id'])
    row = connection.execute(
        'SELECT company_id FROM authorized_suppliers WHERE id = ?', (int(supplier_id),)
    ).fetchone()
    if not row:
        raise ValueError('Fornecedor não encontrado.')
    return int(row['company_id'])


def resolve_product_company_id(connection, actor, product_id):
    """company_id efetivo para operações sobre um produto de catálogo."""
    if actor.get('role') != 'master_admin' and actor.get('company_id') is not None:
        return int(actor['company_id'])
    row = connection.execute(
        'SELECT company_id FROM supplier_products WHERE id = ?', (int(product_id),)
    ).fetchone()
    if not row:
        raise ValueError('Produto não encontrado.')
    return int(row['company_id'])


def create_authorized_supplier(connection, actor, payload):
    """Cria fornecedor manualmente (Nível 1). Retorna o fornecedor criado."""
    company_id = int(actor['company_id']) if actor.get('role') != 'master_admin' else int(payload.get('company_id') or 0)
    if not company_id:
        raise ValueError('Empresa é obrigatória para cadastrar fornecedor.')
    name = str(payload.get('name') or '').strip()
    if not name:
        raise ValueError('Nome do fornecedor é obrigatório.')
    cnpj = ''.join(ch for ch in str(payload.get('cnpj') or '') if ch.isdigit())
    integration_level = str(payload.get('integration_level') or 'email').strip().lower()
    if integration_level not in ('email', 'portal', 'api'):
        raise ValueError('Nível de integração inválido (email, portal ou api).')
    duplicate = connection.execute(
        'SELECT id FROM authorized_suppliers WHERE company_id = ? AND cnpj = ?',
        (company_id, cnpj)
    ).fetchone()
    if duplicate:
        raise ValueError('Já existe fornecedor com este CNPJ nesta empresa.')
    now = _now()
    cursor = connection.execute(
        'INSERT INTO authorized_suppliers (company_id, name, cnpj, category, contact_email, notes, active, source, '
        'phone, address, payment_terms, integration_level, created_by_user_id, created_at, updated_at) '
        'VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            company_id, name, cnpj,
            str(payload.get('category') or '').strip(),
            str(payload.get('contact_email') or '').strip(),
            str(payload.get('notes') or '').strip(),
            'manual',
            str(payload.get('phone') or '').strip(),
            str(payload.get('address') or '').strip(),
            str(payload.get('payment_terms') or '').strip(),
            integration_level,
            actor.get('id'), now, now,
        )
    )
    supplier_id = cursor.lastrowid
    _record_purchase_event(
        connection, company_id, 'supplier', supplier_id, 'supplier_created', '', 'active',
        f'Fornecedor "{name}" cadastrado manualmente.', actor.get('id'), actor.get('full_name') or '',
        actor_role=str(actor.get('role') or ''),
    )
    return get_supplier_by_id(connection, company_id, supplier_id)


def update_supplier_procurement_fields(connection, company_id, supplier_id, payload):
    """Atualiza apenas os campos NOVOS da F0 (aditivo; upsert legado intacto)."""
    supplier = get_supplier_by_id(connection, company_id, supplier_id)
    if not supplier:
        return False
    updates, params = [], []
    for field in ('phone', 'address', 'payment_terms'):
        if field in payload:
            updates.append(f'{field} = ?')
            params.append(str(payload.get(field) or '').strip())
    if 'integration_level' in payload:
        level = str(payload.get('integration_level') or 'email').strip().lower()
        if level not in ('email', 'portal', 'api'):
            raise ValueError('Nível de integração inválido (email, portal ou api).')
        updates.append('integration_level = ?')
        params.append(level)
    if 'active' in payload:
        updates.append('active = ?')
        params.append(1 if payload.get('active') in (1, '1', True, 'true') else 0)
    if not updates:
        return True
    updates.append('updated_at = ?')
    params.extend([_now(), int(supplier_id)])
    connection.execute(
        f"UPDATE authorized_suppliers SET {', '.join(updates)} WHERE id = ?",
        tuple(params)
    )
    return True


# ── Catálogo de produtos por fornecedor ──────────────────────────────────────

def fetch_supplier_products(connection, company_id, supplier_id, include_inactive=False):
    clauses = ['company_id = ?', 'supplier_id = ?']
    params = [int(company_id), int(supplier_id)]
    if not include_inactive:
        clauses.append('active = 1')
    rows = connection.execute(
        f"SELECT * FROM supplier_products WHERE {' AND '.join(clauses)} ORDER BY description ASC, supplier_sku ASC",
        tuple(params)
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def upsert_supplier_product(connection, actor, company_id, supplier_id, payload):
    """Cria ou atualiza (por SKU) um produto do catálogo do fornecedor."""
    supplier = get_supplier_by_id(connection, company_id, supplier_id)
    if not supplier:
        raise ValueError('Fornecedor não encontrado.')
    sku = str(payload.get('supplier_sku') or '').strip()
    description = str(payload.get('description') or '').strip()
    if not sku and not description:
        raise ValueError('Informe SKU ou descrição do produto.')
    epi_id = int(payload.get('epi_id') or 0) or None
    if epi_id:
        epi = connection.execute(
            'SELECT id, company_id FROM epis WHERE id = ?', (epi_id,)
        ).fetchone()
        if not epi or int(epi['company_id']) != int(company_id):
            raise ValueError('EPI vinculado não encontrado nesta empresa.')
    now = _now()
    last_price = float(payload.get('last_price') or 0)
    ca = str(payload.get('ca') or '').strip()
    manufacturer = str(payload.get('manufacturer') or '').strip()
    unit_measure = str(payload.get('unit_measure') or '').strip()
    last_price_at = now if last_price else ''
    lead_time_days = int(payload.get('lead_time_days') or 0)
    min_order_qty = int(payload.get('min_order_qty') or 0)
    existing = connection.execute(
        'SELECT id FROM supplier_products WHERE company_id = ? AND supplier_id = ? AND supplier_sku = ?',
        (int(company_id), int(supplier_id), sku)
    ).fetchone() if sku else None
    if existing:
        connection.execute(
            'UPDATE supplier_products SET epi_id = ?, description = ?, ca = ?, manufacturer = ?, unit_measure = ?, '
            'last_price = ?, last_price_at = ?, lead_time_days = ?, min_order_qty = ?, updated_at = ?, active = 1 '
            'WHERE id = ?',
            (epi_id, description, ca, manufacturer, unit_measure, last_price, last_price_at,
             lead_time_days, min_order_qty, now, int(existing['id']))
        )
        product_id = int(existing['id'])
        action = 'catalog_product_updated'
    else:
        cursor = connection.execute(
            'INSERT INTO supplier_products (company_id, supplier_id, supplier_sku, epi_id, description, ca, '
            'manufacturer, unit_measure, last_price, last_price_at, lead_time_days, min_order_qty, active, '
            'created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)',
            (int(company_id), int(supplier_id), sku, epi_id, description, ca, manufacturer, unit_measure,
             last_price, last_price_at, lead_time_days, min_order_qty, now, now)
        )
        product_id = cursor.lastrowid
        action = 'catalog_product_created'
    _record_purchase_event(
        connection, int(company_id), 'supplier', int(supplier_id), action, '', '',
        f'Catálogo: {description or sku}', actor.get('id'), actor.get('full_name') or '',
        actor_role=str(actor.get('role') or ''),
    )
    row = connection.execute('SELECT * FROM supplier_products WHERE id = ?', (product_id,)).fetchone()
    return row_to_dict(row)


def deactivate_supplier_product(connection, company_id, product_id):
    row = connection.execute(
        'SELECT id FROM supplier_products WHERE id = ? AND company_id = ?',
        (int(product_id), int(company_id))
    ).fetchone()
    if not row:
        return False
    connection.execute(
        'UPDATE supplier_products SET active = 0, updated_at = ? WHERE id = ?',
        (_now(), int(product_id))
    )
    return True


# ── Cotações (RFQ) ────────────────────────────────────────────────────────────

def get_quote_by_id(connection, quote_id):
    row = connection.execute('SELECT * FROM purchase_quotes WHERE id = ?', (int(quote_id),)).fetchone()
    return row_to_dict(row) if row else None


def fetch_quote_items(connection, quote_id):
    rows = connection.execute(
        'SELECT qi.*, pri.epi_id, pri.epi_name, pri.ca, pri.unit_measure, pri.manufacturer, '
        'pri.glove_size, pri.size, pri.uniform_size, pri.quantity_requested '
        'FROM purchase_quote_items qi '
        'JOIN purchase_request_items pri ON pri.id = qi.purchase_request_item_id '
        'WHERE qi.quote_id = ? ORDER BY qi.id ASC',
        (int(quote_id),)
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def _quotable_request_items(connection, pr_id):
    rows = connection.execute(
        "SELECT * FROM purchase_request_items WHERE purchase_request_id = ? "
        "AND status NOT IN ('rejected', 'closed') ORDER BY id ASC",
        (int(pr_id),)
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def create_quotes_for_request(connection, actor, pr_id, payload, ip_address=''):
    """Cria cotações (uma por fornecedor) para os itens da requisição.

    Não altera a requisição nem seus itens — apenas referencia (R1 intacta).
    """
    pr = get_purchase_request_by_id(connection, int(pr_id))
    if not pr:
        raise ValueError('Requisição não encontrada.')
    supplier_ids = [int(sid) for sid in (payload.get('supplier_ids') or []) if int(sid or 0)]
    if not supplier_ids:
        raise ValueError('Informe ao menos um fornecedor para cotar.')
    company_id = int(pr['company_id'])
    items = _quotable_request_items(connection, pr_id)
    requested_item_ids = {int(i) for i in (payload.get('item_ids') or []) if int(i or 0)}
    if requested_item_ids:
        items = [item for item in items if int(item['id']) in requested_item_ids]
    if not items:
        raise ValueError('A requisição não possui itens cotáveis.')
    valid_until = str(payload.get('valid_until') or '').strip()
    notes = str(payload.get('notes') or '').strip()
    now = _now()
    created = []
    for supplier_id in supplier_ids:
        supplier = get_supplier_by_id(connection, company_id, supplier_id)
        if not supplier:
            raise ValueError(f'Fornecedor {supplier_id} não encontrado nesta empresa.')
        if not int(supplier.get('active') or 0):
            raise ValueError(f"Fornecedor \"{supplier.get('name')}\" está inativo.")
        open_quote = connection.execute(
            "SELECT id FROM purchase_quotes WHERE purchase_request_id = ? AND supplier_id = ? "
            "AND status IN ('draft', 'sent', 'answered')",
            (int(pr_id), supplier_id)
        ).fetchone()
        if open_quote:
            raise ValueError(f"Já existe cotação aberta para o fornecedor \"{supplier.get('name')}\" nesta requisição.")
        channel = str(supplier.get('integration_level') or 'email').strip().lower()
        cursor = connection.execute(
            'INSERT INTO purchase_quotes (company_id, purchase_request_id, supplier_id, status, channel, '
            'valid_until, notes, created_by_user_id, created_by_name, created_at, updated_at) '
            "VALUES (?, ?, ?, 'draft', ?, ?, ?, ?, ?, ?, ?)",
            (company_id, int(pr_id), supplier_id, channel, valid_until, notes,
             actor.get('id'), actor.get('full_name') or '', now, now)
        )
        quote_id = cursor.lastrowid
        for item in items:
            connection.execute(
                'INSERT INTO purchase_quote_items (company_id, quote_id, purchase_request_item_id, '
                'unit_price, quantity_available, lead_time_days, declined, notes, created_at, updated_at) '
                "VALUES (?, ?, ?, 0, 0, 0, 0, '', ?, ?)",
                (company_id, quote_id, int(item['id']), now, now)
            )
        _record_purchase_event(
            connection, company_id, 'quote', quote_id, 'quote_created', '', 'draft',
            f"Cotação criada para o fornecedor \"{supplier.get('name')}\" (requisição #{pr_id}, {len(items)} itens).",
            actor.get('id'), actor.get('full_name') or '', ip_address=ip_address,
            actor_role=str(actor.get('role') or ''),
        )
        created.append(get_quote_by_id(connection, quote_id))
    return created


def fetch_quotes_for_request(connection, pr_id):
    rows = connection.execute(
        'SELECT q.*, s.name AS supplier_name, s.cnpj AS supplier_cnpj, s.contact_email AS supplier_email, '
        's.integration_level AS supplier_integration_level '
        'FROM purchase_quotes q JOIN authorized_suppliers s ON s.id = q.supplier_id '
        'WHERE q.purchase_request_id = ? ORDER BY q.id ASC',
        (int(pr_id),)
    ).fetchall()
    quotes = []
    for row in rows:
        quote = row_to_dict(row)
        quote['items'] = fetch_quote_items(connection, quote['id'])
        quotes.append(quote)
    return quotes


def build_quote_comparison(quotes):
    """Matriz item × fornecedor com melhor preço/prazo. Somente leitura."""
    answered = [q for q in quotes if q.get('status') in ('answered', 'selected')]
    items_index = {}
    for quote in answered:
        for item in quote.get('items') or []:
            pri_id = int(item['purchase_request_item_id'])
            entry = items_index.setdefault(pri_id, {
                'purchase_request_item_id': pri_id,
                'epi_id': item.get('epi_id'),
                'epi_name': item.get('epi_name'),
                'ca': item.get('ca'),
                'quantity_requested': item.get('quantity_requested'),
                'offers': [],
            })
            entry['offers'].append({
                'quote_id': int(quote['id']),
                'supplier_id': int(quote['supplier_id']),
                'supplier_name': quote.get('supplier_name') or '',
                'unit_price': float(item.get('unit_price') or 0),
                'lead_time_days': int(item.get('lead_time_days') or 0),
                'quantity_available': int(item.get('quantity_available') or 0),
                'declined': bool(item.get('declined')),
                'best_price': False,
                'best_lead_time': False,
            })
    for entry in items_index.values():
        valid = [o for o in entry['offers'] if not o['declined'] and o['unit_price'] > 0]
        if valid:
            best_price = min(o['unit_price'] for o in valid)
            for offer in valid:
                offer['best_price'] = offer['unit_price'] == best_price
        with_lead = [o for o in valid if o['lead_time_days'] > 0]
        if with_lead:
            best_lead = min(o['lead_time_days'] for o in with_lead)
            for offer in with_lead:
                offer['best_lead_time'] = offer['lead_time_days'] == best_lead
    suppliers = []
    for quote in answered:
        items = quote.get('items') or []
        total = sum(
            float(i.get('unit_price') or 0) * int(i.get('quantity_requested') or 0)
            for i in items if not i.get('declined')
        )
        suppliers.append({
            'quote_id': int(quote['id']),
            'supplier_id': int(quote['supplier_id']),
            'supplier_name': quote.get('supplier_name') or '',
            'status': quote.get('status'),
            'freight_value': float(quote.get('freight_value') or 0),
            'items_total': round(total, 2),
            'total_with_freight': round(total + float(quote.get('freight_value') or 0), 2),
            'answered_at': quote.get('answered_at') or '',
            'payment_terms': quote.get('payment_terms') or '',
        })
    return {
        'items': sorted(items_index.values(), key=lambda e: e['purchase_request_item_id']),
        'suppliers': sorted(suppliers, key=lambda s: (s['total_with_freight'] or 0)),
    }


def answer_quote(connection, actor, quote_id, payload, ip_address=''):
    """Registra a resposta do fornecedor (manual ou vinda do importador CSV)."""
    quote = get_quote_by_id(connection, quote_id)
    if not quote:
        raise ValueError('Cotação não encontrada.')
    if quote['status'] not in QUOTE_ANSWERABLE_STATUSES:
        raise ValueError(f"Cotação com status \"{quote['status']}\" não pode receber resposta.")
    items_payload = payload.get('items') or []
    if not items_payload:
        raise ValueError('Informe os itens respondidos da cotação.')
    quote_items = fetch_quote_items(connection, quote_id)
    by_quote_item = {int(i['id']): i for i in quote_items}
    by_pr_item = {int(i['purchase_request_item_id']): i for i in quote_items}
    now = _now()
    answered = 0
    for raw in items_payload:
        target = None
        if raw.get('quote_item_id'):
            target = by_quote_item.get(int(raw['quote_item_id']))
        elif raw.get('purchase_request_item_id'):
            # elo com o importador CSV existente (parse_purchase_quote_file →
            # linhas com item_id = purchase_request_item_id)
            target = by_pr_item.get(int(raw['purchase_request_item_id']))
        if not target:
            raise ValueError('Item de cotação não encontrado na cotação informada.')
        declined = 1 if raw.get('declined') in (1, '1', True, 'true') else 0
        unit_price = float(raw.get('unit_price') or raw.get('valor_unitario') or 0)
        if not declined and unit_price <= 0:
            raise ValueError(f"Item \"{target.get('epi_name')}\": informe preço unitário ou marque como recusado.")
        connection.execute(
            'UPDATE purchase_quote_items SET unit_price = ?, quantity_available = ?, lead_time_days = ?, '
            'declined = ?, notes = ?, updated_at = ? WHERE id = ?',
            (
                unit_price,
                int(raw.get('quantity_available') or target.get('quantity_requested') or 0),
                int(raw.get('lead_time_days') or 0),
                declined,
                str(raw.get('notes') or '').strip(),
                now, int(target['id']),
            )
        )
        answered += 1
    connection.execute(
        "UPDATE purchase_quotes SET status = 'answered', answered_at = ?, freight_value = ?, "
        'payment_terms = ?, valid_until = ?, notes = ?, updated_at = ? WHERE id = ?',
        (
            now,
            float(payload.get('freight_value') or 0),
            str(payload.get('payment_terms') or quote.get('payment_terms') or '').strip(),
            str(payload.get('valid_until') or quote.get('valid_until') or '').strip(),
            str(payload.get('notes') or quote.get('notes') or '').strip(),
            now, int(quote_id),
        )
    )
    _record_purchase_event(
        connection, int(quote['company_id']), 'quote', int(quote_id), 'quote_answered',
        quote['status'], 'answered',
        f'Resposta registrada ({answered} itens, origem: {str(payload.get("source") or "manual")}).',
        actor.get('id'), actor.get('full_name') or '', ip_address=ip_address,
        actor_role=str(actor.get('role') or ''),
    )
    return get_quote_by_id(connection, quote_id)


def select_quote(connection, actor, quote_id, ip_address=''):
    """Seleciona a cotação vencedora e devolve o rascunho de PO pré-preenchido.

    NÃO cria a PO — o comprador revisa e usa o POST /api/purchase-orders
    existente; o fluxo de aprovação da PO permanece intacto (R3).
    """
    quote = get_quote_by_id(connection, quote_id)
    if not quote:
        raise ValueError('Cotação não encontrada.')
    if quote['status'] != 'answered':
        raise ValueError('Apenas cotações respondidas podem ser selecionadas.')
    company_id = int(quote['company_id'])
    supplier = get_supplier_by_id(connection, company_id, int(quote['supplier_id']))
    pr = get_purchase_request_by_id(connection, int(quote['purchase_request_id']))
    now = _now()
    connection.execute(
        "UPDATE purchase_quotes SET status = 'selected', updated_at = ? WHERE id = ?",
        (now, int(quote_id))
    )
    siblings = connection.execute(
        "SELECT id, status FROM purchase_quotes WHERE purchase_request_id = ? AND id != ? "
        "AND status IN ('draft', 'sent', 'answered')",
        (int(quote['purchase_request_id']), int(quote_id))
    ).fetchall()
    for sibling in siblings:
        connection.execute(
            "UPDATE purchase_quotes SET status = 'discarded', updated_at = ? WHERE id = ?",
            (now, int(sibling['id']))
        )
        _record_purchase_event(
            connection, company_id, 'quote', int(sibling['id']), 'quote_discarded',
            str(sibling['status']), 'discarded',
            f'Descartada — cotação #{quote_id} selecionada como vencedora.',
            actor.get('id'), actor.get('full_name') or '', ip_address=ip_address,
            actor_role=str(actor.get('role') or ''),
        )
    _record_purchase_event(
        connection, company_id, 'quote', int(quote_id), 'quote_selected', 'answered', 'selected',
        f"Cotação do fornecedor \"{(supplier or {}).get('name')}\" selecionada como vencedora.",
        actor.get('id'), actor.get('full_name') or '', ip_address=ip_address,
        actor_role=str(actor.get('role') or ''),
    )
    items = [i for i in fetch_quote_items(connection, quote_id) if not i.get('declined')]
    po_draft = {
        'purchase_request_id': int(quote['purchase_request_id']),
        'unit_id': int(pr['unit_id']) if pr else None,
        'supplier': (supplier or {}).get('name') or '',
        'supplier_cnpj': (supplier or {}).get('cnpj') or '',
        'notes': f'Gerada a partir da cotação #{quote_id}.',
        'items': [
            {
                'purchase_request_item_id': int(i['purchase_request_item_id']),
                'epi_id': int(i['epi_id']),
                'quantity': int(i.get('quantity_requested') or 1),
                'unit_price': float(i.get('unit_price') or 0),
            }
            for i in items
        ],
    }
    return {'quote': get_quote_by_id(connection, quote_id), 'po_draft': po_draft}


# ── Envio por e-mail (Nível 1) ────────────────────────────────────────────────

def _pdf_lines(title, subtitle, rows):
    lines = [
        {'text': pdf_safe_text(title), 'bold': True, 'size': 14, 'x': 50, 'y': 780},
        {'text': pdf_safe_text(subtitle), 'x': 50, 'y': 758},
        {'text': ' ', 'x': 50, 'y': 744},
    ]
    y = 726
    for row in rows:
        lines.append({'text': pdf_safe_text(row), 'x': 50, 'y': y, 'size': 10})
        y -= 16
        if y < 60:
            break
    return [lines]


def build_rfq_email(connection, quote, supplier, pr, items):
    subject = f"Solicitação de Cotação #{quote['id']} — Requisição #{pr['id']}"
    body_lines = [
        f"Prezado fornecedor {supplier.get('name')},",
        '',
        f"Solicitamos cotação para os itens abaixo (requisição #{pr['id']}):",
        '',
    ]
    pdf_rows = []
    for item in items:
        sizes = '/'.join(
            v for v in (item.get('glove_size'), item.get('size'), item.get('uniform_size'))
            if v and v != 'N/A'
        )
        line = (
            f"- {item.get('epi_name')} (CA {item.get('ca') or '-'}) — "
            f"{item.get('quantity_requested')} {item.get('unit_measure') or 'un'}"
            + (f' — tamanho {sizes}' if sizes else '')
        )
        body_lines.append(line)
        pdf_rows.append(line.lstrip('- '))
    if quote.get('valid_until'):
        body_lines.extend(['', f"Prazo para resposta: {quote['valid_until']}"])
    if quote.get('notes'):
        body_lines.extend(['', f"Observações: {quote['notes']}"])
    body_lines.extend([
        '',
        'Por favor, responda este e-mail informando preço unitário, prazo de',
        'entrega e frete por item, ou anexando sua proposta.',
        '',
        'Atenciosamente,',
        'EPI Controle — Compras',
    ])
    pdf_bytes = build_pdf_document(_pdf_lines(
        f"Solicitação de Cotação #{quote['id']}",
        f"Requisição #{pr['id']} — {len(items)} itens",
        pdf_rows,
    ))
    return subject, '\n'.join(body_lines), [(f"cotacao_{quote['id']}.pdf", pdf_bytes)]


def send_quote_to_supplier(connection, actor, quote_id, ip_address='', send_email_fn=None):
    """Envia a RFQ ao fornecedor por e-mail (canal do Nível 1)."""
    quote = get_quote_by_id(connection, quote_id)
    if not quote:
        raise ValueError('Cotação não encontrada.')
    if quote['status'] not in ('draft', 'sent'):
        raise ValueError(f"Cotação com status \"{quote['status']}\" não pode ser enviada.")
    company_id = int(quote['company_id'])
    supplier = get_supplier_by_id(connection, company_id, int(quote['supplier_id']))
    if not supplier:
        raise ValueError('Fornecedor da cotação não encontrado.')
    contact_email = str(supplier.get('contact_email') or '').strip()
    if not contact_email:
        raise ValueError('Fornecedor sem e-mail de contato cadastrado.')
    pr = get_purchase_request_by_id(connection, int(quote['purchase_request_id']))
    items = fetch_quote_items(connection, quote_id)
    subject, body, attachments = build_rfq_email(connection, quote, supplier, pr, items)
    if send_email_fn is None:
        from epi_backend.mailer import send_email as send_email_fn
    send_email_fn(contact_email, subject, body, attachments=attachments)
    now = _now()
    connection.execute(
        "UPDATE purchase_quotes SET status = 'sent', channel = 'email', sent_at = ?, updated_at = ? WHERE id = ?",
        (now, now, int(quote_id))
    )
    _record_purchase_event(
        connection, company_id, 'quote', int(quote_id), 'quote_sent',
        quote['status'], 'sent', f'RFQ enviada por e-mail para {contact_email}.',
        actor.get('id'), actor.get('full_name') or '', ip_address=ip_address,
        actor_role=str(actor.get('role') or ''), destination=contact_email,
    )
    return get_quote_by_id(connection, quote_id)


def _po_items(connection, po_id):
    rows = connection.execute(
        'SELECT * FROM purchase_order_items WHERE purchase_order_id = ? ORDER BY id ASC',
        (int(po_id),)
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def build_po_email(po, items, supplier_name):
    subject = f"Pedido de Compra {po.get('po_number') or po['id']}"
    body_lines = [
        f'Prezado fornecedor {supplier_name},',
        '',
        f"Segue o pedido de compra {po.get('po_number') or po['id']} aprovado:",
        '',
    ]
    pdf_rows = []
    total = 0.0
    for item in items:
        quantity = int(item.get('quantity_approved') or item.get('quantity') or 0)
        unit_price = float(item.get('unit_price') or 0)
        line_total = round(quantity * unit_price, 2)
        total += line_total
        line = (
            f"- {item.get('epi_name')} (CA {item.get('ca') or '-'}) — "
            f"{quantity} x R$ {unit_price:.2f} = R$ {line_total:.2f}"
        )
        body_lines.append(line)
        pdf_rows.append(line.lstrip('- '))
    body_lines.extend(['', f'Total: R$ {total:.2f}'])
    if po.get('expected_delivery_date'):
        body_lines.append(f"Entrega prevista: {po['expected_delivery_date']}")
    body_lines.extend([
        '',
        'Por favor, confirme o recebimento deste pedido respondendo este e-mail.',
        '',
        'Atenciosamente,',
        'EPI Controle — Compras',
    ])
    pdf_rows.append(f'TOTAL: R$ {total:.2f}')
    pdf_bytes = build_pdf_document(_pdf_lines(
        f"Pedido de Compra {po.get('po_number') or po['id']}",
        f"Fornecedor: {supplier_name}",
        pdf_rows,
    ))
    return subject, '\n'.join(body_lines), [(f"pedido_{po.get('po_number') or po['id']}.pdf", pdf_bytes)]


def send_po_to_supplier(connection, actor, po_id, payload=None, ip_address='', send_email_fn=None):
    """Envia PO aprovada ao fornecedor por e-mail; grava campos de envio.

    Não altera o status da PO (máquina de estados intacta) — o envio é
    registrado nos campos paralelos sent_to_supplier_at/sent_channel.
    """
    payload = payload or {}
    po = get_purchase_order_by_id(connection, int(po_id))
    if not po:
        raise ValueError('PO não encontrada.')
    if str(po.get('status') or '') not in PO_SENDABLE_STATUSES:
        raise ValueError('Apenas POs aprovadas podem ser enviadas ao fornecedor.')
    company_id = int(po['company_id'])
    supplier_name = str(po.get('supplier') or '').strip()
    contact_email = str(payload.get('to_email') or '').strip()
    if not contact_email:
        supplier_cnpj = ''.join(ch for ch in str(po.get('supplier_cnpj') or '') if ch.isdigit())
        supplier_row = None
        if supplier_cnpj:
            supplier_row = connection.execute(
                'SELECT * FROM authorized_suppliers WHERE company_id = ? AND cnpj = ?',
                (company_id, supplier_cnpj)
            ).fetchone()
        if not supplier_row and supplier_name:
            supplier_row = connection.execute(
                'SELECT * FROM authorized_suppliers WHERE company_id = ? AND LOWER(TRIM(name)) = ?',
                (company_id, supplier_name.lower())
            ).fetchone()
        if supplier_row:
            contact_email = str(row_to_dict(supplier_row).get('contact_email') or '').strip()
    if not contact_email:
        raise ValueError('Fornecedor da PO sem e-mail de contato. Informe to_email ou cadastre o fornecedor.')
    items = _po_items(connection, po_id)
    subject, body, attachments = build_po_email(po, items, supplier_name or 'parceiro')
    if send_email_fn is None:
        from epi_backend.mailer import send_email as send_email_fn
    send_email_fn(contact_email, subject, body, attachments=attachments)
    now = _now()
    connection.execute(
        "UPDATE purchase_orders SET sent_to_supplier_at = ?, sent_channel = 'email', updated_at = ? WHERE id = ?",
        (now, now, int(po_id))
    )
    _record_purchase_event(
        connection, company_id, 'purchase_order', int(po_id), 'po_sent_to_supplier',
        str(po.get('status') or ''), str(po.get('status') or ''),
        f'PO enviada por e-mail para {contact_email}.',
        actor.get('id'), actor.get('full_name') or '', ip_address=ip_address,
        actor_role=str(actor.get('role') or ''), destination=contact_email,
    )
    return get_purchase_order_by_id(connection, int(po_id))


# ── Confirmação manual e acompanhamento ──────────────────────────────────────

def register_po_confirmation(connection, actor, po_id, payload, ip_address='', source='email_manual'):
    """Registra confirmação/recusa/atualização de entrega informada pelo fornecedor."""
    po = get_purchase_order_by_id(connection, int(po_id))
    if not po:
        raise ValueError('PO não encontrada.')
    status = str(payload.get('status') or '').strip().lower()
    if status not in CONFIRMATION_STATUSES:
        raise ValueError('Status de confirmação inválido (confirmed, rejected ou delivery_update).')
    company_id = int(po['company_id'])
    now = _now()
    supplier_id = None
    supplier_cnpj = ''.join(ch for ch in str(po.get('supplier_cnpj') or '') if ch.isdigit())
    if supplier_cnpj:
        row = connection.execute(
            'SELECT id FROM authorized_suppliers WHERE company_id = ? AND cnpj = ?',
            (company_id, supplier_cnpj)
        ).fetchone()
        supplier_id = int(row['id']) if row else None
    connection.execute(
        'INSERT INTO purchase_order_confirmations (company_id, purchase_order_id, supplier_id, status, '
        'delivery_forecast, carrier, tracking_code, comment, source, created_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            company_id, int(po_id), supplier_id, status,
            str(payload.get('delivery_forecast') or '').strip(),
            str(payload.get('carrier') or '').strip(),
            str(payload.get('tracking_code') or '').strip(),
            str(payload.get('comment') or '').strip(),
            str(source or 'email_manual'),
            now,
        )
    )
    if status in ('confirmed', 'rejected'):
        connection.execute(
            'UPDATE purchase_orders SET supplier_confirmation_status = ?, updated_at = ? WHERE id = ?',
            (status, now, int(po_id))
        )
    _record_purchase_event(
        connection, company_id, 'purchase_order', int(po_id), f'po_supplier_{status}',
        str(po.get('status') or ''), str(po.get('status') or ''),
        str(payload.get('comment') or '').strip() or f'Registro manual: {status}.',
        actor.get('id'), actor.get('full_name') or '', ip_address=ip_address,
        actor_role=str(actor.get('role') or ''),
    )
    return get_purchase_order_by_id(connection, int(po_id))


def fetch_po_tracking(connection, po_id):
    po = get_purchase_order_by_id(connection, int(po_id))
    if not po:
        return None
    rows = connection.execute(
        'SELECT * FROM purchase_order_confirmations WHERE purchase_order_id = ? ORDER BY created_at DESC, id DESC',
        (int(po_id),)
    ).fetchall()
    return {
        'purchase_order_id': int(po_id),
        'status': po.get('status'),
        'sent_to_supplier_at': po.get('sent_to_supplier_at') or '',
        'sent_channel': po.get('sent_channel') or '',
        'supplier_confirmation_status': po.get('supplier_confirmation_status') or '',
        'confirmations': [row_to_dict(row) for row in rows],
    }


# ── Escopo/autorização compartilhados com o módulo de compras ────────────────

def ensure_quote_scope(connection, actor, quote, *, actor_operational_unit_id=None):
    """Empresa + unidade de compras via a requisição da cotação."""
    ensure_resource_company(actor, quote, 'Cotação')
    pr = get_purchase_request_by_id(connection, int(quote['purchase_request_id']))
    if pr:
        ensure_purchase_request_action_scope(
            connection, actor, pr, actor_operational_unit_id=actor_operational_unit_id
        )


__all__ = [
    'CONFIRMATION_STATUSES',
    'PO_SENDABLE_STATUSES',
    'QUOTE_CHANNELS',
    'QUOTE_STATUSES',
    'answer_quote',
    'build_quote_comparison',
    'build_po_email',
    'build_rfq_email',
    'create_authorized_supplier',
    'create_quotes_for_request',
    'deactivate_supplier_product',
    'ensure_quote_scope',
    'fetch_po_tracking',
    'fetch_quote_items',
    'fetch_quotes_for_request',
    'fetch_supplier_products',
    'get_quote_by_id',
    'get_supplier_by_id',
    'resolve_supplier_company_id',
    'resolve_product_company_id',
    'register_po_confirmation',
    'select_quote',
    'send_po_to_supplier',
    'send_quote_to_supplier',
    'update_supplier_procurement_fields',
    'upsert_supplier_product',
]
