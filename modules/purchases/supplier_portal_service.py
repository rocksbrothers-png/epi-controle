"""Fase F2 do módulo de Compras — Portal do Fornecedor (Nível 2).

Acesso externo por link tokenizado, no padrão do portal do colaborador:
token forte com hash armazenado (nunca o token em claro), expiração,
revogação, escopo de 1 entidade (cotação OU PO) por link e auditoria em
supplier_portal_audit_logs + purchase_events.

O fornecedor pode: ver a RFQ, responder preço/prazo/frete por item, anexar
proposta, confirmar o pedido e atualizar o status da entrega. Nada além do
escopo do token é acessível; nenhuma regra interna muda (a resposta usa o
mesmo answer_quote/register_po_confirmation do Nível 1).
"""

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from epi_backend.db import row_to_dict

from modules.purchases.quotes_service import (
    answer_quote,
    fetch_quote_items,
    get_quote_by_id,
    get_supplier_by_id,
    register_po_confirmation,
    _po_items,
)
from modules.purchases.service import (
    _record_purchase_event,
    get_purchase_order_by_id,
    get_purchase_request_by_id,
)

UTC = timezone.utc

LINK_ENTITY_TYPES = ('quote', 'purchase_order')
DEFAULT_EXPIRES_DAYS = 14
MAX_EXPIRES_DAYS = 60
MAX_PROPOSAL_BYTES = 5 * 1024 * 1024
ALLOWED_PROPOSAL_TYPES = {'application/pdf', 'image/jpeg', 'image/png'}


def _now_dt():
    return datetime.now(UTC)


def _now():
    return _now_dt().isoformat()


def _hash_token(token):
    return hashlib.sha256(str(token).encode('utf-8')).hexdigest()


def _portal_actor(supplier, link):
    """Ator sintético para auditoria em purchase_events (sem usuário interno)."""
    return {
        'id': None,
        'full_name': f"Fornecedor {supplier.get('name') or ''} (portal)".strip(),
        'role': 'supplier_portal',
        'company_id': int(link['company_id']),
    }


def register_portal_audit(connection, company_id, supplier_id, link_id, action, detail='', ip_address='', user_agent=''):
    connection.execute(
        'INSERT INTO supplier_portal_audit_logs (company_id, supplier_id, link_id, action, detail, '
        'ip_address, user_agent, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (
            int(company_id), supplier_id, link_id, str(action),
            str(detail or '')[:500], str(ip_address or '')[:64], str(user_agent or '')[:200], _now(),
        )
    )


# ── Ciclo de vida do link ─────────────────────────────────────────────────────

def create_supplier_portal_link(connection, actor, entity_type, entity_id, expires_days=None):
    """Cria link tokenizado para 1 cotação ou 1 PO. Retorna (link, token).

    O token só existe no retorno (vai no e-mail) — o banco guarda o hash.
    """
    entity_type = str(entity_type or '').strip()
    if entity_type not in LINK_ENTITY_TYPES:
        raise ValueError('Tipo de entidade do portal inválido (quote ou purchase_order).')
    if entity_type == 'quote':
        entity = get_quote_by_id(connection, int(entity_id))
        if not entity:
            raise ValueError('Cotação não encontrada.')
        supplier_id = int(entity['supplier_id'])
    else:
        entity = get_purchase_order_by_id(connection, int(entity_id))
        if not entity:
            raise ValueError('PO não encontrada.')
        supplier_cnpj = ''.join(ch for ch in str(entity.get('supplier_cnpj') or '') if ch.isdigit())
        row = connection.execute(
            'SELECT id FROM authorized_suppliers WHERE company_id = ? AND cnpj = ?',
            (int(entity['company_id']), supplier_cnpj)
        ).fetchone() if supplier_cnpj else None
        if not row:
            raise ValueError('PO sem fornecedor cadastrado — cadastre o fornecedor (CNPJ) antes de gerar o link.')
        supplier_id = int(row['id'])
    company_id = int(entity['company_id'])
    days = int(expires_days or DEFAULT_EXPIRES_DAYS)
    if days < 1 or days > MAX_EXPIRES_DAYS:
        raise ValueError(f'Expiração deve estar entre 1 e {MAX_EXPIRES_DAYS} dias.')
    # revoga links abertos anteriores da mesma entidade (1 link ativo por entidade)
    connection.execute(
        "UPDATE supplier_portal_links SET revoked_at = ? WHERE company_id = ? AND entity_type = ? "
        "AND entity_id = ? AND revoked_at = ''",
        (_now(), company_id, entity_type, int(entity_id))
    )
    token = secrets.token_urlsafe(32)
    expires_at = (_now_dt() + timedelta(days=days)).isoformat()
    cursor = connection.execute(
        'INSERT INTO supplier_portal_links (company_id, supplier_id, entity_type, entity_id, token_hash, '
        'expires_at, created_by_user_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (company_id, supplier_id, entity_type, int(entity_id), _hash_token(token),
         expires_at, actor.get('id'), _now())
    )
    link_id = int(cursor.lastrowid)
    register_portal_audit(connection, company_id, supplier_id, link_id, 'link_created',
                          f'{entity_type}#{entity_id}, expira {expires_at[:10]}')
    row = connection.execute('SELECT * FROM supplier_portal_links WHERE id = ?', (link_id,)).fetchone()
    return row_to_dict(row), token


def revoke_supplier_portal_link(connection, actor, company_id, link_id):
    row = connection.execute(
        'SELECT * FROM supplier_portal_links WHERE id = ? AND company_id = ?',
        (int(link_id), int(company_id))
    ).fetchone()
    if not row:
        return False
    link = row_to_dict(row)
    if not link.get('revoked_at'):
        connection.execute(
            'UPDATE supplier_portal_links SET revoked_at = ? WHERE id = ?',
            (_now(), int(link_id))
        )
        register_portal_audit(connection, company_id, link.get('supplier_id'), int(link_id), 'link_revoked',
                              f"por {actor.get('full_name') or actor.get('id')}")
    return True


def fetch_supplier_portal_links(connection, company_id, entity_type=None, entity_id=None):
    clauses, params = ['company_id = ?'], [int(company_id)]
    if entity_type:
        clauses.append('entity_type = ?')
        params.append(str(entity_type))
    if entity_id:
        clauses.append('entity_id = ?')
        params.append(int(entity_id))
    rows = connection.execute(
        f"SELECT * FROM supplier_portal_links WHERE {' AND '.join(clauses)} ORDER BY id DESC",
        tuple(params)
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def resolve_portal_token(connection, token, ip_address='', user_agent=''):
    """Resolve token → link válido. Levanta PermissionError sem vazar detalhes."""
    token = str(token or '').strip()
    if not token or len(token) < 16:
        raise PermissionError('Link do portal inválido ou expirado.')
    row = connection.execute(
        'SELECT * FROM supplier_portal_links WHERE token_hash = ?',
        (_hash_token(token),)
    ).fetchone()
    if not row:
        raise PermissionError('Link do portal inválido ou expirado.')
    link = row_to_dict(row)
    denial = ''
    if link.get('revoked_at'):
        denial = 'revoked'
    elif link.get('expires_at') and str(link['expires_at']) < _now():
        denial = 'expired'
    if denial:
        register_portal_audit(connection, link['company_id'], link.get('supplier_id'), link['id'],
                              'access_denied', denial, ip_address, user_agent)
        raise PermissionError('Link do portal inválido ou expirado.')
    connection.execute(
        'UPDATE supplier_portal_links SET last_access_at = ?, access_attempts = access_attempts + 1 WHERE id = ?',
        (_now(), int(link['id']))
    )
    return link


# ── Payload do portal (escopo mínimo do token) ───────────────────────────────

def fetch_quote_files(connection, quote_id, include_data=False):
    columns = '*' if include_data else 'id, company_id, quote_id, file_name, file_type, uploaded_by, source, created_at'
    rows = connection.execute(
        f'SELECT {columns} FROM purchase_quote_files WHERE quote_id = ? ORDER BY id DESC',
        (int(quote_id),)
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def get_portal_payload(connection, link):
    """Dados exibidos ao fornecedor — apenas a entidade do token, sem dados internos."""
    company = connection.execute(
        'SELECT name FROM companies WHERE id = ?', (int(link['company_id']),)
    ).fetchone()
    supplier = get_supplier_by_id(connection, int(link['company_id']), int(link['supplier_id']))
    base = {
        'entity_type': link['entity_type'],
        'company_name': str(company['name']) if company else '',
        'supplier_name': (supplier or {}).get('name') or '',
        'expires_at': link.get('expires_at') or '',
    }
    if link['entity_type'] == 'quote':
        quote = get_quote_by_id(connection, int(link['entity_id']))
        if not quote:
            raise ValueError('Cotação do link não encontrada.')
        items = fetch_quote_items(connection, quote['id'])
        base['quote'] = {
            'id': quote['id'],
            'status': quote['status'],
            'valid_until': quote.get('valid_until') or '',
            'notes': quote.get('notes') or '',
            'freight_value': float(quote.get('freight_value') or 0),
            'payment_terms': quote.get('payment_terms') or '',
            'items': [
                {
                    'quote_item_id': i['id'],
                    'epi_name': i.get('epi_name') or '',
                    'ca': i.get('ca') or '',
                    'unit_measure': i.get('unit_measure') or 'un',
                    'glove_size': i.get('glove_size') or 'N/A',
                    'size': i.get('size') or 'N/A',
                    'uniform_size': i.get('uniform_size') or 'N/A',
                    'quantity_requested': i.get('quantity_requested') or 0,
                    'unit_price': float(i.get('unit_price') or 0),
                    'lead_time_days': int(i.get('lead_time_days') or 0),
                    'declined': bool(i.get('declined')),
                }
                for i in items
            ],
            'files': fetch_quote_files(connection, quote['id']),
        }
    else:
        po = get_purchase_order_by_id(connection, int(link['entity_id']))
        if not po:
            raise ValueError('PO do link não encontrada.')
        items = _po_items(connection, po['id'])
        confirmations = connection.execute(
            'SELECT status, delivery_forecast, carrier, tracking_code, comment, source, created_at '
            'FROM purchase_order_confirmations WHERE purchase_order_id = ? ORDER BY id DESC',
            (int(po['id']),)
        ).fetchall()
        base['purchase_order'] = {
            'id': po['id'],
            'po_number': po.get('po_number') or '',
            'expected_delivery_date': po.get('expected_delivery_date') or '',
            'supplier_confirmation_status': po.get('supplier_confirmation_status') or '',
            'items': [
                {
                    'epi_name': i.get('epi_name') or '',
                    'ca': i.get('ca') or '',
                    'quantity': int(i.get('quantity_approved') or i.get('quantity') or 0),
                    'unit_price': float(i.get('unit_price') or 0),
                }
                for i in items
            ],
            'confirmations': [row_to_dict(row) for row in confirmations],
        }
    return base


# ── Ações do fornecedor via portal ───────────────────────────────────────────

def _validate_proposal(proposal):
    """Valida a proposta anexada e retorna (file_name, file_type, base64)."""
    file_name = str(proposal.get('file_name') or '').strip()
    file_type = str(proposal.get('file_type') or '').strip().lower()
    raw_base64 = str(proposal.get('content_base64') or '').strip()
    if not file_name or not raw_base64:
        raise ValueError('Proposta anexada sem nome ou conteúdo.')
    if file_type not in ALLOWED_PROPOSAL_TYPES:
        raise ValueError('Tipo de arquivo da proposta inválido (PDF, JPEG ou PNG).')
    if ',' in raw_base64 and raw_base64.lower().startswith('data:'):
        raw_base64 = raw_base64.split(',', 1)[1]
    try:
        file_bytes = base64.b64decode(raw_base64, validate=True)
    except Exception as exc:
        raise ValueError('Conteúdo do arquivo da proposta inválido.') from exc
    if len(file_bytes) > MAX_PROPOSAL_BYTES:
        raise ValueError('Proposta excede o limite de 5 MB.')
    return file_name[:200], file_type, raw_base64


def _store_proposal_file(connection, link, validated, uploaded_by):
    file_name, file_type, raw_base64 = validated
    connection.execute(
        'INSERT INTO purchase_quote_files (company_id, quote_id, file_name, file_type, file_data, '
        "uploaded_by, source, created_at) VALUES (?, ?, ?, ?, ?, ?, 'supplier_portal', ?)",
        (int(link['company_id']), int(link['entity_id']), file_name, file_type, raw_base64,
         str(uploaded_by or '')[:120], _now())
    )


def portal_answer_quote(connection, link, payload, ip_address='', user_agent=''):
    """Fornecedor responde a cotação pelo portal (com anexo opcional)."""
    if link['entity_type'] != 'quote':
        raise PermissionError('Este link não permite responder cotação.')
    supplier = get_supplier_by_id(connection, int(link['company_id']), int(link['supplier_id']))
    if not supplier:
        raise ValueError('Fornecedor do link não encontrado.')
    proposal = (payload or {}).get('proposal')
    validated_proposal = _validate_proposal(proposal) if proposal else None
    actor = _portal_actor(supplier, link)
    answer_payload = dict(payload or {})
    answer_payload['source'] = 'portal'
    quote = answer_quote(connection, actor, int(link['entity_id']), answer_payload, ip_address)
    connection.execute(
        "UPDATE purchase_quotes SET channel = 'portal' WHERE id = ?", (int(link['entity_id']),)
    )
    if validated_proposal:
        _store_proposal_file(connection, link, validated_proposal, uploaded_by=supplier.get('name') or 'fornecedor')
    register_portal_audit(connection, link['company_id'], link['supplier_id'], link['id'],
                          'quote_answered', f"cotação #{link['entity_id']}"
                          + (', com proposta anexada' if proposal else ''),
                          ip_address, user_agent)
    return quote


def portal_confirm_po(connection, link, payload, ip_address='', user_agent=''):
    """Fornecedor confirma/recusa o pedido ou atualiza o status da entrega."""
    if link['entity_type'] != 'purchase_order':
        raise PermissionError('Este link não permite confirmar pedido.')
    supplier = get_supplier_by_id(connection, int(link['company_id']), int(link['supplier_id']))
    if not supplier:
        raise ValueError('Fornecedor do link não encontrado.')
    actor = _portal_actor(supplier, link)
    po = register_po_confirmation(
        connection, actor, int(link['entity_id']), payload or {}, ip_address, source='portal'
    )
    register_portal_audit(connection, link['company_id'], link['supplier_id'], link['id'],
                          f"po_{str((payload or {}).get('status') or '')}",
                          f"PO #{link['entity_id']}", ip_address, user_agent)
    return po


# ── Envio do link por e-mail (integra com o Nível 1) ─────────────────────────

def portal_link_url(base_url, token):
    base = str(base_url or '').strip().rstrip('/')
    return f'{base}/fornecedor/{token}'


def send_portal_link_email(connection, actor, entity_type, entity_id, expires_days=None,
                            base_url='', send_email_fn=None):
    """Cria o link e envia ao fornecedor por e-mail. Retorna o link (sem token).

    Para cotações, também marca a RFQ como enviada (canal portal) — o envio
    pelo portal substitui o envio por e-mail simples do Nível 1.
    """
    entity_type = str(entity_type or '').strip()
    if entity_type == 'quote':
        quote = get_quote_by_id(connection, int(entity_id))
        if quote and quote['status'] not in ('draft', 'sent'):
            raise ValueError(f"Cotação com status \"{quote['status']}\" não pode ser enviada ao portal.")
    elif entity_type == 'purchase_order':
        from modules.purchases.quotes_service import PO_SENDABLE_STATUSES
        po = get_purchase_order_by_id(connection, int(entity_id))
        if po and str(po.get('status') or '') not in PO_SENDABLE_STATUSES:
            raise ValueError('Apenas POs aprovadas podem ser enviadas ao fornecedor.')
    link, token = create_supplier_portal_link(connection, actor, entity_type, entity_id, expires_days)
    supplier = get_supplier_by_id(connection, int(link['company_id']), int(link['supplier_id']))
    contact_email = str((supplier or {}).get('contact_email') or '').strip()
    if not contact_email:
        raise ValueError('Fornecedor sem e-mail de contato cadastrado.')
    if not base_url:
        from epi_backend.config import WEB_BASE_URL
        base_url = WEB_BASE_URL
    if not base_url:
        raise ValueError('WEB_BASE_URL não configurada para gerar o link do portal.')
    url = portal_link_url(base_url, token)
    if entity_type == 'quote':
        subject = f'Solicitação de Cotação #{entity_id} — Portal do Fornecedor'
        action_text = 'responder a cotação (preço, prazo e frete por item) e anexar sua proposta'
    else:
        po = get_purchase_order_by_id(connection, int(entity_id))
        subject = f"Pedido de Compra {(po or {}).get('po_number') or entity_id} — Portal do Fornecedor"
        action_text = 'confirmar o pedido e atualizar o status da entrega'
    body = (
        f"Prezado fornecedor {(supplier or {}).get('name') or ''},\n\n"
        f'Acesse o Portal do Fornecedor para {action_text}:\n\n'
        f'  {url}\n\n'
        f"O link é pessoal e expira em {str(link.get('expires_at') or '')[:10]}.\n"
        f'Não compartilhe este link.\n\n'
        f'Atenciosamente,\nEPI Controle — Compras'
    )
    if send_email_fn is None:
        from epi_backend.mailer import send_email as send_email_fn
    send_email_fn(contact_email, subject, body)
    now = _now()
    if entity_type == 'quote':
        connection.execute(
            "UPDATE purchase_quotes SET status = CASE WHEN status = 'draft' THEN 'sent' ELSE status END, "
            "channel = 'portal', sent_at = CASE WHEN sent_at = '' THEN ? ELSE sent_at END, updated_at = ? WHERE id = ?",
            (now, now, int(entity_id))
        )
        _record_purchase_event(
            connection, int(link['company_id']), 'quote', int(entity_id), 'quote_sent', '', 'sent',
            f'Link do Portal do Fornecedor enviado para {contact_email}.',
            actor.get('id'), actor.get('full_name') or '', ip_address='',
            actor_role=str(actor.get('role') or ''), destination=contact_email,
        )
    else:
        connection.execute(
            "UPDATE purchase_orders SET sent_to_supplier_at = ?, sent_channel = 'portal', updated_at = ? WHERE id = ?",
            (now, now, int(entity_id))
        )
        po = get_purchase_order_by_id(connection, int(entity_id))
        _record_purchase_event(
            connection, int(link['company_id']), 'purchase_order', int(entity_id), 'po_sent_to_supplier',
            str((po or {}).get('status') or ''), str((po or {}).get('status') or ''),
            f'Link do Portal do Fornecedor enviado para {contact_email}.',
            actor.get('id'), actor.get('full_name') or '', ip_address='',
            actor_role=str(actor.get('role') or ''), destination=contact_email,
        )
    register_portal_audit(connection, link['company_id'], link['supplier_id'], link['id'],
                          'link_emailed', contact_email)
    return link
