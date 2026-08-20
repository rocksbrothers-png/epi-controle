"""Rotas de gestão de estoque de EPIs."""

from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from urllib.parse import parse_qs

from core.auth import ensure_resource_company
from core.database import get_connection
from core.repository import (
    authorize_action,
    get_epi_by_id,
    get_unit_by_id,
    get_unit_active_jv_name,
    resolve_unit_scope,
)
from modules.employees.service import actor_has_no_operational_unit, actor_operational_unit_id
from modules.units.service import ensure_unit_operational
from core.security import resolve_actor_user_id
from epi_backend.db import row_to_dict
from epi_backend.epi_scope import get_epi_effective_jv_name, is_epi_visible_for_unit
from epi_backend.http_utils import require_fields, send_json, structured_log
from epi_backend.manufacture_date_ocr import detect_manufacture_date, get_ocr_runtime_status
from modules.epis.validity import MANUFACTURER_VALIDITY_WARNING_DAYS
from modules.purchases.service import actor_has_no_purchase_unit_scope, get_actor_purchase_unit_scope
from modules.settings.service import canary_evaluate_visibility_dataset
from modules.stock.service import (
    BLOCKED_STOCK_STATUSES,
    build_low_stock,
    build_stock_item_qr,
    create_stock_item,
    compute_stock_compliance,
    create_stock_item_reprint,
    create_stock_movement,
    fetch_available_stock_items,
    fetch_blocked_stock_items,
    fetch_validity_overview,
    set_stock_item_status,
    fetch_epi_size_balance,
    is_stock_critical,
    fetch_stock_movements,
    get_stock_item_for_reprint,
    get_unit_stock,
    lookup_stock_item_by_qr,
    next_company_qr_sequence,
    parse_int_flexible,
    parse_stock_qr_lookup_value,
    resolve_item_size,
    resolve_minimum_stock,
    resolve_unit_minimum_stock,
    set_unit_epi_minimum_stock,
    upsert_unit_stock,
)
from core.rate_limit import get_client_ip
from core.schema import ensure_stock_movement_size_columns

UTC = timezone.utc


def _user_agent(handler):
    try:
        return str(handler.headers.get('User-Agent', '') or '')
    except Exception:  # noqa: BLE001 - metadado de auditoria, nunca derruba a operação
        return ''


# ── GET ───────────────────────────────────────────────────────────────────────

def handle_get_stock_low(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'stock:view')
        result = build_low_stock(
            connection,
            actor,
            actor_operational_unit_id=actor_operational_unit_id,
            get_unit_active_jv_name=get_unit_active_jv_name,
            is_epi_visible_for_unit=is_epi_visible_for_unit,
        )
        return send_json(handler, 200, result)


def handle_get_stock_lookup_qr(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'stock:view')
        query = parse_qs(parsed.query)
        qr_code = str(query.get('qr_code', [''])[0]).strip()
        if not qr_code:
            raise ValueError('QR informado é obrigatório.')
        parsed_qr = parse_stock_qr_lookup_value(qr_code)
        query_stock_item_id = parse_int_flexible(query.get('stock_item_id', [''])[0], 0) or parsed_qr.get('stock_item_id') or 0
        company_filter = actor['company_id'] if actor['role'] != 'master_admin' else query.get('company_id', [''])[0]
        scope_unit_id = actor_operational_unit_id(connection, actor)
        if actor.get('role') in ('admin', 'user') and not scope_unit_id:
            raise PermissionError('Perfil sem unidade operacional ativa para consultar estoque.')
        unit_filter = scope_unit_id or query.get('unit_id', [''])[0]
        if not unit_filter:
            raise ValueError('Unidade é obrigatória para validar o QR.')
        company_scope_id = int(company_filter or 0)
        if not company_scope_id:
            unit_row = get_unit_by_id(connection, int(unit_filter))
            company_scope_id = int(unit_row['company_id']) if unit_row else 0
        requested_qr_code = str(parsed_qr.get('qr_code_value') or '').strip()
        stock_item = lookup_stock_item_by_qr(connection, company_scope_id, unit_filter, requested_qr_code, query_stock_item_id)
        if not stock_item:
            raise ValueError('QR não encontrado com correspondência exata no estoque da unidade.')
        return send_json(handler, 200, {'stock_item': row_to_dict(stock_item)})


def handle_get_stock_available_items(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'stock:view')
        query = parse_qs(parsed.query)
        epi_id = parse_int_flexible(query.get('epi_id', [''])[0], 0)
        if epi_id <= 0:
            raise ValueError('EPI é obrigatório para listar QRs disponíveis.')
        company_filter = actor['company_id'] if actor['role'] != 'master_admin' else query.get('company_id', [''])[0]
        scope_unit_id = actor_operational_unit_id(connection, actor)
        if actor.get('role') in ('admin', 'user') and not scope_unit_id:
            raise PermissionError('Perfil sem unidade operacional ativa para consultar estoque.')
        unit_filter = scope_unit_id or query.get('unit_id', [''])[0]
        if not unit_filter:
            raise ValueError('Unidade é obrigatória para listar QRs disponíveis.')
        company_scope_id = int(company_filter or 0)
        if not company_scope_id:
            unit_row = get_unit_by_id(connection, int(unit_filter))
            company_scope_id = int(unit_row['company_id']) if unit_row else 0
        raw_rows = fetch_available_stock_items(connection, company_scope_id, unit_filter, epi_id)
        items = [row_to_dict(item) for item in raw_rows]
        items = canary_evaluate_visibility_dataset(
            connection, actor, endpoint_name='/api/stock/available-items', dataset_name='stock_items', legacy_items=items
        )
        return send_json(handler, 200, {'items': items})


def handle_get_stock_blocked_items(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'stock:view')
        query = parse_qs(parsed.query)
        company_filter = actor['company_id'] if actor['role'] != 'master_admin' else query.get('company_id', [''])[0]
        company_scope_id = int(company_filter or 0)
        if not company_scope_id:
            raise ValueError('Empresa é obrigatória para listar o estoque bloqueado.')
        scope_unit_id = actor_operational_unit_id(connection, actor)
        if actor.get('role') in ('admin', 'user') and not scope_unit_id:
            raise PermissionError('Perfil sem unidade operacional ativa para consultar estoque.')
        unit_filter = scope_unit_id or query.get('unit_id', [''])[0] or None
        rows = fetch_blocked_stock_items(connection, company_scope_id, unit_filter)
        return send_json(handler, 200, {
            'items': [row_to_dict(r) for r in rows],
            'statuses': BLOCKED_STOCK_STATUSES,
        })


def handle_post_stock_item_status(handler, parsed, payload, match):
    # unit_id é opcional: o item é localizado pelo QR/código dentro da empresa e a
    # unidade é derivada do próprio item. Perfis com unidade operacional fixa
    # ('admin'/'user') têm a busca restrita à sua unidade e a trava reaplicada
    # sobre o item encontrado.
    require_fields(payload, ['actor_user_id', 'new_status'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'stock:adjust')
        company_id = actor['company_id'] if actor['role'] != 'master_admin' else int(payload.get('company_id') or 0)
        if not company_id:
            raise ValueError('Empresa é obrigatória.')
        qr_code = str(payload.get('qr_code') or '').strip()
        stock_item_id = int(payload.get('stock_item_id') or 0)
        if not qr_code and stock_item_id <= 0:
            raise ValueError('Informe o QR/código do item ou selecione um item.')
        scope_unit_id = actor_operational_unit_id(connection, actor)
        if actor.get('role') in ('admin', 'user') and not scope_unit_id:
            raise PermissionError('Perfil sem unidade operacional ativa para ajustar estoque.')
        # Restringe a busca à unidade operacional (se houver); senão usa a unidade
        # informada (opcional) ou busca em toda a empresa.
        lookup_unit = int(scope_unit_id) if scope_unit_id else int(payload.get('unit_id') or 0)
        item = lookup_stock_item_by_qr(
            connection, company_id, lookup_unit, qr_code=qr_code, stock_item_id=stock_item_id,
        )
        if not item:
            raise ValueError('Item de estoque não encontrado. Verifique o código e a empresa selecionada.')
        ensure_resource_company(actor, item, 'Item de estoque')
        if scope_unit_id and int(item['unit_id']) != int(scope_unit_id):
            raise PermissionError('Item fora da sua unidade operacional.')
        unit_id = int(item['unit_id'])
        now = datetime.now(timezone.utc).isoformat()
        new_status = set_stock_item_status(
            connection, item, payload['new_status'], payload.get('reason', ''),
            int(actor['id']), str(actor.get('full_name') or ''), now,
        )
        connection.commit()
        structured_log(
            'info', 'stock.item_status_change',
            stock_item_id=int(item['id']), company_id=int(company_id), unit_id=unit_id,
            actor_id=int(actor['id']), new_status=new_status,
        )
        return send_json(handler, 200, {'ok': True, 'status': new_status})


def handle_get_stock_validity_overview(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'stock:view')
        query = parse_qs(parsed.query)
        company_filter = actor['company_id'] if actor['role'] != 'master_admin' else query.get('company_id', [''])[0]
        company_scope_id = int(company_filter or 0)
        if not company_scope_id:
            raise ValueError('Empresa é obrigatória para a gestão de validade.')
        scope_unit_id = actor_operational_unit_id(connection, actor)
        if actor.get('role') in ('admin', 'user') and not scope_unit_id:
            raise PermissionError('Perfil sem unidade operacional ativa para consultar estoque.')
        unit_filter = scope_unit_id or query.get('unit_id', [''])[0] or None
        overview = fetch_validity_overview(connection, company_scope_id, unit_filter)
        return send_json(handler, 200, overview)


def handle_get_stock_compliance(handler, parsed, payload, match):
    """Fonte ÚNICA de conformidade (item 2): Dashboard e Validade e Bloqueios.

    Retorna, por categoria (ca_expired, ca_expiring, product_expired,
    product_expiring, missing_manufacture, missing_lot, admin_blocked), a
    contagem e os registros calculados — o card do Dashboard mostra o mesmo
    total da tela e o clique abre exatamente esses itens (deep-link).
    """
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'stock:view')
        query = parse_qs(parsed.query)
        company_filter = actor['company_id'] if actor['role'] != 'master_admin' else query.get('company_id', [''])[0]
        company_scope_id = int(company_filter or 0)
        if not company_scope_id:
            raise ValueError('Empresa é obrigatória para a conformidade de estoque.')
        scope_unit_id = actor_operational_unit_id(connection, actor)
        if actor.get('role') in ('admin', 'user') and not scope_unit_id:
            raise PermissionError('Perfil sem unidade operacional ativa para consultar estoque.')
        unit_filter = scope_unit_id or query.get('unit_id', [''])[0] or None
        return send_json(handler, 200, compute_stock_compliance(connection, company_scope_id, unit_filter))


def handle_get_stock_movements_report(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'stock:view')
        query = parse_qs(parsed.query)
        company_filter = actor['company_id'] if actor['role'] != 'master_admin' else query.get('company_id', [''])[0]
        scope_unit_id = actor_operational_unit_id(connection, actor)
        purchase_scope = get_actor_purchase_unit_scope(connection, actor)
        if actor_has_no_purchase_unit_scope(actor, scope_unit_id, purchase_scope) or actor_has_no_operational_unit(actor, scope_unit_id):
            return send_json(handler, 200, {'items': []})
        clauses, params = [], []
        if company_filter:
            clauses.append('sm.company_id = ?')
            params.append(int(company_filter))
        if scope_unit_id:
            clauses.append('sm.unit_id = ?')
            params.append(int(scope_unit_id))
        elif purchase_scope:
            ph = ','.join(['?'] * len(purchase_scope))
            clauses.append(f'sm.unit_id IN ({ph})')
            params.extend(purchase_scope)
        year_filter = query.get('year', [''])[0].strip()
        month_filter = query.get('month', [''])[0].strip()
        epi_filter = query.get('epi_id', [''])[0].strip()
        movement_type_filter = query.get('movement_type', [''])[0].strip()
        source_type_filter = query.get('source_type', [''])[0].strip()
        unit_filter_q = query.get('unit_id', [''])[0].strip()
        if year_filter:
            clauses.append("substr(sm.created_at, 1, 4) = ?")
            params.append(year_filter)
        if month_filter:
            clauses.append("substr(sm.created_at, 6, 2) = ?")
            params.append(month_filter.zfill(2))
        if epi_filter:
            clauses.append('sm.epi_id = ?')
            params.append(int(epi_filter))
        if movement_type_filter:
            clauses.append('sm.movement_type = ?')
            params.append(movement_type_filter)
        if source_type_filter:
            clauses.append('sm.source_type = ?')
            params.append(source_type_filter)
        if unit_filter_q and not scope_unit_id:
            clauses.append('sm.unit_id = ?')
            params.append(int(unit_filter_q))
        # Filtros de conformidade (NT 146/2015): CA vencido e validade do
        # fabricante (próxima do vencimento / vencida).
        ca_status_filter = query.get('ca_status', [''])[0].strip().lower()
        manufacturer_validity_filter = query.get('manufacturer_validity', [''])[0].strip().lower()
        today_str = date.today().isoformat()
        if ca_status_filter == 'expired':
            clauses.append("COALESCE(e.ca_expiry, '') <> '' AND e.ca_expiry < ?")
            params.append(today_str)
        if manufacturer_validity_filter == 'expired':
            clauses.append("COALESCE(e.epi_validity_date, '') <> '' AND e.epi_validity_date < ?")
            params.append(today_str)
        elif manufacturer_validity_filter in ('expiring', 'expiring_soon', 'near'):
            threshold_str = (date.today() + timedelta(days=MANUFACTURER_VALIDITY_WARNING_DAYS)).isoformat()
            clauses.append("COALESCE(e.epi_validity_date, '') <> '' AND e.epi_validity_date >= ? AND e.epi_validity_date <= ?")
            params.append(today_str)
            params.append(threshold_str)
        rows = fetch_stock_movements(connection, clauses, params)
        items = [row_to_dict(r) for r in rows]
        items = canary_evaluate_visibility_dataset(
            connection, actor, endpoint_name='/api/stock/movements/report', dataset_name='stock_movements', legacy_items=items
        )
        return send_json(handler, 200, {'items': items})


# ── POST /api/stock/minimum ───────────────────────────────────────────────────

def handle_post_stock_minimum(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'epi_id', 'minimum_stock'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'stock:adjust')
        if actor.get('role') not in ('admin', 'user'):
            raise PermissionError('Apenas Administrador Local e Gestor de EPI podem definir estoque mínimo.')
        epi = get_epi_by_id(connection, int(payload['epi_id']))
        ensure_resource_company(actor, epi, 'EPI')
        # Perfil travado: a Unidade é a do ator, e o `unit_id` que o cliente
        # eventualmente mande é descartado (1.1D-A). Fail-closed sem Unidade.
        scope_unit_id = resolve_unit_scope(
            connection, actor,
            denial_message='Perfil sem unidade operacional ativa para editar estoque mínimo.',
        ).unit_id
        # Mesma checagem de visibilidade já usada por GET /api/stock/epis e
        # pelos alertas de estoque baixo (fetch_low_stock_items) — não a
        # comparação ingênua epi.unit_id == scope_unit_id, que só é
        # verdadeira para EPI de escopo UNIT. Um EPI GLOBAL (unit_id nulo,
        # visível em toda unidade fora de JV) ou de Joint Venture nunca teria
        # epi.unit_id == scope_unit_id mesmo quando o ator está, de fato,
        # dentro da própria unidade — bloqueando indevidamente Administrador
        # Local/Gestor de EPI de editar o estoque mínimo de um item que eles
        # legitimamente veem e operam na tela de Controle de Estoque.
        scope_unit_jv_name = get_unit_active_jv_name(connection, scope_unit_id)
        epi_jv_name = get_epi_effective_jv_name(epi, lambda uid: get_unit_active_jv_name(connection, uid))
        if not is_epi_visible_for_unit(
            epi_unit_id=epi.get('unit_id'),
            epi_joint_venture_name=epi_jv_name,
            target_unit_id=scope_unit_id,
            target_unit_joint_venture_name=scope_unit_jv_name,
        ):
            raise PermissionError('Perfil só pode editar estoque mínimo de EPIs visíveis na unidade operacional ativa.')
        # O mínimo é DAQUELA Unidade (1.1D-B0). Antes daqui saía
        # `UPDATE epis SET minimum_stock`, numa rota que já resolvia e validava
        # a Unidade do ator: o Gestor da Unidade A reescrevia, em silêncio, o
        # parâmetro das Unidades B e C, e o operador delas passava a ser
        # alertado por um número que não configurou. A escrita agora é isolada
        # pela chave (company_id, unit_id, epi_id) e fica auditada.
        minimo = set_unit_epi_minimum_stock(
            connection, int(epi['company_id']), int(scope_unit_id), int(payload['epi_id']),
            payload.get('minimum_stock'),
            actor=actor,
            ip_address=get_client_ip(handler),
            user_agent=_user_agent(handler),
        )
        connection.commit()
        return send_json(handler, 200, {
            'ok': True,
            'minimum_stock': minimo.value,
            'unit_id': int(scope_unit_id),
            'minimum_stock_source': minimo.source,
        })


# ── POST /api/stock/movements ─────────────────────────────────────────────────

def handle_post_stock_movements(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'company_id', 'unit_id', 'epi_id', 'movement_type', 'quantity', 'label_measure', 'label_printer_name', 'label_print_format', 'manufacture_date'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'stock:adjust', int(payload['company_id']))
        scope_unit_id = actor_operational_unit_id(connection, actor)
        if actor.get('role') in ('admin', 'user') and not scope_unit_id:
            raise PermissionError('Perfil sem unidade operacional ativa para movimentar estoque.')
        if scope_unit_id and int(payload.get('unit_id') or 0) != int(scope_unit_id):
            raise PermissionError('Perfil só pode movimentar estoque da unidade operacional ativa.')
        movement_type = str(payload.get('movement_type', '')).strip()
        if movement_type not in ('in', 'out'):
            raise ValueError('Tipo de movimentação inválido.')
        if movement_type == 'out':
            raise ValueError('Saída manual bloqueada: utilize o fluxo de Entrega de EPI para manter rastreabilidade.')
        epi = get_epi_by_id(connection, int(payload['epi_id']))
        unit = get_unit_by_id(connection, int(payload['unit_id']))
        ensure_resource_company(actor, epi, 'EPI')
        ensure_resource_company(actor, unit, 'Unidade')
        ensure_unit_operational(connection, unit['id'], 'movimentações de estoque')
        from modules.epis.service import ensure_epi_operational
        ensure_epi_operational(connection, epi['id'], 'movimentações de estoque')
        quantity = int(payload.get('quantity') or 0)
        if quantity <= 0:
            raise ValueError('Quantidade deve ser maior que zero.')
        resolved_size = resolve_item_size(
            payload.get('glove_size'),
            payload.get('size'),
            payload.get('uniform_size'),
        )
        if not resolved_size['selected_size']:
            raise ValueError('Tamanho é obrigatório para entrada em estoque. Informe Tamanho-Luvas, Tamanho ou Tamanho Uniforme.')
        glove_size = resolved_size['glove_size']
        size = resolved_size['size']
        uniform_size = resolved_size['uniform_size']
        label_measure = str(payload.get('label_measure') or '').strip().lower()
        if not label_measure:
            raise ValueError('Medida da etiqueta é obrigatória.')
        label_printer_name = str(payload.get('label_printer_name') or '').strip()
        if not label_printer_name:
            raise ValueError('Impressora da etiqueta é obrigatória.')
        label_print_format = str(payload.get('label_print_format') or '').strip()
        if not label_print_format:
            raise ValueError('Formato de impressão da etiqueta é obrigatório.')
        lot_code = str(payload.get('lot_code') or '').strip()
        manufacture_date = str(payload.get('manufacture_date') or '').strip()
        if not manufacture_date:
            raise ValueError('Data de fabricação é obrigatória para entrada de estoque.')
        stock_row = get_unit_stock(connection, int(payload['company_id']), int(payload['unit_id']), int(payload['epi_id']))
        previous_stock = int((stock_row or {}).get('quantity') or 0)
        delta = quantity if movement_type == 'in' else -quantity
        new_stock = previous_stock + delta
        if new_stock < 0:
            raise ValueError('Saída deixa estoque negativo.')
        ensure_stock_movement_size_columns(connection)
        movement_id = create_stock_movement(
            connection,
            company_id=int(payload['company_id']),
            unit_id=int(payload['unit_id']),
            epi_id=int(payload['epi_id']),
            movement_type=movement_type,
            quantity=quantity,
            previous_stock=previous_stock,
            new_stock=new_stock,
            source_type='manual',
            source_id=None,
            notes=str(payload.get('notes', '')).strip(),
            actor_user_id=actor['id'],
            actor_name=actor['full_name'],
            created_at=datetime.now(UTC).isoformat(),
            glove_size=glove_size,
            size=size,
            uniform_size=uniform_size,
        )
        upsert_unit_stock(connection, int(payload['company_id']), int(payload['unit_id']), int(payload['epi_id']), new_stock)
        qr_labels = []
        if movement_type == 'in':
            now = datetime.now(UTC).isoformat()
            for _ in range(quantity):
                seq_value = next_company_qr_sequence(connection, int(payload['company_id']))
                qr_value = build_stock_item_qr(int(payload['company_id']), int(payload['unit_id']), seq_value)
                stock_item_id = create_stock_item(
                    connection,
                    company_id=int(payload['company_id']),
                    unit_id=int(payload['unit_id']),
                    epi_id=int(payload['epi_id']),
                    glove_size=glove_size,
                    size=size,
                    uniform_size=uniform_size,
                    seq_value=seq_value,
                    qr_value=qr_value,
                    movement_id=movement_id,
                    lot_code=lot_code,
                    manufacture_date=manufacture_date,
                    label_measure=label_measure,
                    label_printer_name=label_printer_name,
                    label_print_format=label_print_format,
                    generated_by_user_id=int(actor['id']),
                    now=now,
                )
                qr_labels.append({
                    'qr_code_value': qr_value,
                    'epi_name': epi['name'],
                    'glove_size': glove_size,
                    'size': size,
                    'uniform_size': uniform_size,
                    'stock_item_id': stock_item_id,
                    'manufacture_date': manufacture_date,
                    'unit_name': unit['name'],
                    'label_measure': label_measure,
                    'label_printer_name': label_printer_name,
                    'label_print_format': label_print_format,
                    'reprint_count': 0
                })
        connection.commit()
        return send_json(handler, 201, {'ok': True, 'movement_id': movement_id, 'new_stock': new_stock, 'qr_labels': qr_labels})


# ── POST /api/stock/manufacture-date-ocr ──────────────────────────────────────

def handle_post_stock_manufacture_date_ocr(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'image_data'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'stock:adjust')
        image_data = str(payload.get('image_data') or '').strip()
        runtime = get_ocr_runtime_status()
        if not runtime.get('ready'):
            status_code = 503 if runtime.get('ocr_required') else 200
            error_event_level = 'error' if runtime.get('ocr_required') else 'warning'
            user_message = (
                'OCR não disponível neste ambiente (somente em produção).'
                if not runtime.get('ocr_required')
                else str(runtime.get('error') or 'OCR indisponível no servidor.')
            )
            structured_log(
                error_event_level,
                'stock.manufacture_date_ocr.runtime_unavailable',
                actor_user_id=int(actor['id']),
                detail=runtime.get('error'),
                message=user_message,
                tesseract_cmd=runtime.get('tesseract_cmd'),
            )
            return send_json(
                handler,
                status_code,
                {'error': user_message, 'runtime': runtime, 'manufacture_date': '', 'confidence': 0.0},
            )
        result = detect_manufacture_date(image_data)
        structured_log(
            'info',
            'stock.manufacture_date_ocr',
            actor_user_id=int(actor['id']),
            has_date=bool(result.get('manufacture_date')),
            confidence=result.get('confidence'),
            candidates=len(result.get('candidates') or []),
        )
        return send_json(handler, 200, result)


# ── POST /api/stock/labels/reprint ────────────────────────────────────────────

def handle_post_stock_labels_reprint(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'company_id', 'stock_item_id', 'reason_code'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'stock:adjust', int(payload['company_id']))
        reason_code = str(payload.get('reason_code') or '').strip().lower()
        if reason_code not in {'perdeu', 'rasgou'}:
            raise ValueError('Justificativa inválida. Opções: Perdeu ou Rasgou.')
        reason_note = str(payload.get('reason_note') or '').strip()
        stock_item = get_stock_item_for_reprint(connection, int(payload['stock_item_id']))
        if not stock_item:
            raise ValueError('Etiqueta não encontrada para reimpressão.')
        ensure_resource_company(actor, stock_item, 'Etiqueta')
        scope_unit_id = actor_operational_unit_id(connection, actor)
        if actor.get('role') in ('admin', 'user') and (not scope_unit_id or int(stock_item['unit_id']) != int(scope_unit_id)):
            raise PermissionError('Etiqueta fora da unidade operacional do usuário.')
        now = datetime.now(UTC).isoformat()
        new_reprint_count = create_stock_item_reprint(
            connection,
            stock_item_id=int(stock_item['id']),
            company_id=int(stock_item['company_id']),
            reason_code=reason_code,
            reason_note=reason_note,
            actor_user_id=int(actor['id']),
            actor_name=str(actor.get('full_name') or ''),
            now=now,
        )
        connection.commit()
        label_payload = row_to_dict(stock_item)
        label_payload['stock_item_id'] = int(stock_item['id'])
        label_payload['reprint_count'] = new_reprint_count
        return send_json(handler, 200, {'ok': True, 'label': label_payload})


def handle_get_ocr_runtime_status(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        authorize_action(connection, resolve_actor_user_id(handler, parsed), 'stock:view')
        return send_json(handler, 200, get_ocr_runtime_status())


def handle_get_stock_epis(handler, parsed, payload, match):
    from modules.settings.service import canary_evaluate_visibility_dataset
    from modules.epis.service import fetch_epis
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'stock:view')
        query = parse_qs(parsed.query)
        company_filter = actor['company_id'] if actor['role'] != 'master_admin' else query.get('company_id', [''])[0]
        # Resolução de Unidade centralizada (1.1D-A). Antes daqui saía
        # `actor_operational_unit_id(...) or query.get('unit_id')`: o `or`
        # escolhia a origem, e o `unit_id` do cliente entrava sem NENHUMA
        # validação de tenant. Não vazava — `company_filter` recortava a lista
        # depois — mas o isolamento dependia da composição incidental de dois
        # filtros, e o saldo por unidade era lido da unidade pedida antes desse
        # recorte. Agora a Unidade é validada na origem, contra a empresa do
        # ator, e sai daqui já garantida.
        unit_scope = resolve_unit_scope(
            connection, actor, query.get('unit_id', [''])[0],
            denial_message='Perfil sem unidade operacional ativa para consultar estoque.',
        )
        unit_filter = unit_scope.unit_id
        company_scope_id = int(company_filter or 0)
        if unit_filter and not company_scope_id:
            unit_row = get_unit_by_id(connection, int(unit_filter))
            company_scope_id = int(unit_row['company_id']) if unit_row else 0
        name = str(query.get('name', [''])[0]).strip().lower() or None
        section = str(query.get('section', [''])[0]).strip().lower() or None
        manufacturer = str(query.get('manufacturer', [''])[0]).strip().lower() or None
        ca = str(query.get('ca', [''])[0]).strip().lower() or None
        protection = str(query.get('protection', [''])[0]).strip().lower() or None
        epis = fetch_epis(
            connection, actor if actor['role'] != 'master_admin' else None, None,
            name=name, section=section, manufacturer=manufacturer, ca=ca, protection=protection,
        )
        target_unit_jv_name = get_unit_active_jv_name(connection, unit_filter) if unit_filter else ''
        items = []
        for epi in epis:
            if company_filter and str(epi.get('company_id')) != str(company_filter):
                continue
            if unit_filter and not is_epi_visible_for_unit(
                epi_unit_id=epi.get('unit_id'),
                epi_joint_venture_name=get_epi_effective_jv_name(
                    epi, lambda uid: get_unit_active_jv_name(connection, uid)
                ),
                target_unit_id=unit_filter,
                target_unit_joint_venture_name=target_unit_jv_name,
            ):
                continue
            item = dict(epi)
            # ── Estoque corporativo × estoque da unidade ─────────────────────
            # São grandezas DIFERENTES e ficam em campos diferentes. Antes havia
            # aqui um fallback por truthiness:
            #
            #   item['stock'] = (stock_row or {}).get('quantity') or item['stock']
            #
            # que devolvia o saldo da unidade — exceto quando ele era 0, porque
            # zero é falsy e caía no total da empresa. Uma unidade sem estoque
            # exibia o número da empresa inteira, e o mesmo campo mudava de
            # significado conforme o valor. Nunca reintroduzir esse padrão.
            #
            # `stock` (legado) segue com o valor CORPORATIVO, igual a
            # `company_stock_quantity`, até os consumidores migrarem.
            company_stock = int(item.get('stock') or 0)

            stock_unit_id = int(unit_filter or 0)
            if stock_unit_id:
                stock_row = get_unit_stock(
                    connection, int(epi['company_id']), stock_unit_id, int(epi['id'])
                )
                # Sem linha em unit_epi_stock a unidade tem zero, não "sem dado":
                # o EPI é visível para ela e o saldo é conhecido.
                unit_stock = int((stock_row or {}).get('quantity') or 0)
                size_rows = fetch_epi_size_balance(
                    connection, int(epi['company_id']), stock_unit_id, int(epi['id'])
                )
                unit_minimum = resolve_unit_minimum_stock(
                    connection, int(epi['company_id']), stock_unit_id, int(epi['id'])
                )
            else:
                # Nenhuma unidade resolvida (master_admin/general_admin sem
                # seleção): `None`, não 0. Zero afirmaria "esta unidade não tem
                # estoque"; None diz "não há unidade".
                unit_stock = None
                size_rows = []
                unit_minimum = None

            minimum_stock = resolve_minimum_stock(item.get('minimum_stock'))
            item['minimum_stock'] = minimum_stock
            item['company_stock_quantity'] = company_stock
            item['unit_stock_quantity'] = unit_stock
            item['unit_scope_id'] = stock_unit_id or None
            # ── Criticidade OPERACIONAL: da Unidade, contra o mínimo DELA ────
            # `minimum_stock` (acima) é o padrão da EMPRESA e não decide mais a
            # criticidade de nenhuma Unidade: comparar o saldo local contra ele
            # marcava como crítica toda Unidade de uma empresa cujo estoque
            # esteja distribuído — mínimo 100 com 30/30/40 em três Unidades
            # gerava três alertas falsos.
            #
            # `minimum_stock_source` diz se o número é decisão da Unidade
            # (`unit_configured`) ou herança do padrão (`company_default`), para
            # o cliente não ter que deduzir isso comparando valores.
            #
            # Os três campos são `None` JUNTOS quando não há Unidade resolvida —
            # nunca 0/False isolados, pelo mesmo motivo de `unit_stock_quantity`.
            item['unit_minimum_stock'] = unit_minimum.value if unit_minimum else None
            item['minimum_stock_source'] = unit_minimum.source if unit_minimum else None
            item['is_unit_stock_critical'] = (
                is_stock_critical(unit_stock, unit_minimum.value) if unit_minimum else None
            )
            # Leitura CORPORATIVA do catálogo, mantida com o mesmo valor de
            # sempre até os consumidores migrarem (prevista para a 1.1E).
            item['is_company_stock_critical'] = is_stock_critical(company_stock, minimum_stock)
            item['stock'] = company_stock
            item['size_balances'] = size_rows
            items.append(item)
        items = canary_evaluate_visibility_dataset(connection, actor, endpoint_name='/api/stock/epis', dataset_name='epis', legacy_items=items)
        return send_json(handler, 200, {'items': items})


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    router.register('GET',  '/api/ocr/runtime-status',           handle_get_ocr_runtime_status)
    router.register('GET',  '/api/stock/epis',                   handle_get_stock_epis)
    router.register('GET',  '/api/stock/low',                    handle_get_stock_low)
    router.register('GET',  '/api/stock/lookup-qr',              handle_get_stock_lookup_qr)
    router.register('GET',  '/api/stock/available-items',        handle_get_stock_available_items)
    router.register('GET',  '/api/stock/blocked-items',          handle_get_stock_blocked_items)
    router.register('GET',  '/api/stock/validity-overview',      handle_get_stock_validity_overview)
    router.register('GET',  '/api/stock/compliance',             handle_get_stock_compliance)
    router.register('POST', '/api/stock/items/status',           handle_post_stock_item_status)
    router.register('GET',  '/api/stock/movements/report',       handle_get_stock_movements_report)
    router.register('POST', '/api/stock/minimum',                handle_post_stock_minimum)
    router.register('POST', '/api/stock/movements',              handle_post_stock_movements)
    router.register('POST', '/api/stock/manufacture-date-ocr',   handle_post_stock_manufacture_date_ocr)
    router.register('POST', '/api/stock/labels/reprint',         handle_post_stock_labels_reprint)
