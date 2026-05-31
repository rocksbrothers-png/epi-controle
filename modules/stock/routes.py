"""Rotas de gestão de estoque de EPIs."""

from contextlib import closing
from datetime import datetime, timezone
from urllib.parse import parse_qs

from core.auth import ensure_resource_company
from core.database import get_connection
from core.repository import authorize_action, get_epi_by_id, get_unit_by_id, get_unit_active_jv_name
from modules.employees.service import actor_operational_unit_id
from core.security import resolve_actor_user_id
from epi_backend.db import row_to_dict
from epi_backend.epi_scope import is_epi_visible_for_unit
from epi_backend.http_utils import require_fields, send_json, structured_log
from epi_backend.manufacture_date_ocr import detect_manufacture_date, get_ocr_runtime_status
from modules.purchases.service import get_actor_purchase_unit_scope
from modules.stock.service import build_low_stock, fetch_epi_size_balance, get_unit_stock, parse_int_flexible, parse_stock_qr_lookup_value

UTC = timezone.utc


def _get_server():
    import server_postgres as _sp
    return _sp


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
        query_sql = (
            'SELECT esi.id, esi.company_id, esi.unit_id, esi.epi_id, esi.glove_size, esi.size, esi.uniform_size, '
            'esi.lot_code, esi.qr_code_value, esi.status, esi.reprint_count, esi.label_measure, '
            'esi.label_printer_name, esi.label_print_format, epis.name AS epi_name, epis.purchase_code, '
            'epis.unit_measure, units.name AS unit_name '
            'FROM epi_stock_items esi '
            'JOIN epis ON epis.id = esi.epi_id '
            'JOIN units ON units.id = esi.unit_id '
            'WHERE esi.company_id = ? AND esi.unit_id = ?'
        )
        query_params = [int(company_scope_id), int(unit_filter)]
        if requested_qr_code:
            query_sql += ' AND esi.qr_code_value = ?'
            query_params.append(requested_qr_code)
        if int(query_stock_item_id) > 0:
            query_sql += ' AND esi.id = ?'
            query_params.append(int(query_stock_item_id))
        query_sql += ' ORDER BY esi.id DESC LIMIT 1'
        stock_item = connection.execute(query_sql, tuple(query_params)).fetchone()
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
        items = connection.execute(
            (
                'SELECT esi.id, esi.qr_code_value, esi.epi_id, epis.name AS epi_name, esi.status, '
                'esi.glove_size, esi.size, esi.uniform_size '
                'FROM epi_stock_items esi '
                'JOIN epis ON epis.id = esi.epi_id '
                'WHERE esi.company_id = ? AND esi.unit_id = ? AND esi.epi_id = ? '
                "AND COALESCE(LOWER(esi.status), 'in_stock') IN ('in_stock', 'available') "
                "AND COALESCE(esi.qr_code_value, '') != '' "
                'ORDER BY esi.id ASC'
            ),
            (int(company_scope_id), int(unit_filter), int(epi_id))
        ).fetchall()
        return send_json(handler, 200, {'items': [row_to_dict(item) for item in items]})


def handle_get_stock_movements_report(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'stock:view')
        query = parse_qs(parsed.query)
        company_filter = actor['company_id'] if actor['role'] != 'master_admin' else query.get('company_id', [''])[0]
        scope_unit_id = actor_operational_unit_id(connection, actor)
        purchase_scope = get_actor_purchase_unit_scope(connection, actor)
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
        final_where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
        rows = connection.execute(
            (
                'SELECT sm.id, sm.company_id, sm.unit_id, sm.epi_id, sm.movement_type, '
                'sm.quantity, sm.previous_stock, sm.new_stock, sm.source_type, sm.source_id, '
                'sm.notes, sm.actor_name, sm.created_at, '
                'sm.glove_size, sm.size, sm.uniform_size, '
                'e.name AS epi_name, e.ca, e.unit_measure, u.name AS unit_name '
                'FROM stock_movements sm '
                'JOIN epis e ON e.id = sm.epi_id '
                'JOIN units u ON u.id = sm.unit_id '
                f'{final_where} '
                'ORDER BY sm.created_at DESC, sm.id DESC '
                'LIMIT 500'
            ),
            tuple(params)
        ).fetchall()
        return send_json(handler, 200, {'items': [row_to_dict(r) for r in rows]})


# ── POST /api/stock/minimum ───────────────────────────────────────────────────

def handle_post_stock_minimum(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'epi_id', 'minimum_stock'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'stock:adjust')
        if actor.get('role') not in ('admin', 'user'):
            raise PermissionError('Apenas Administrador Local e Gestor de EPI podem definir estoque mínimo.')
        epi = get_epi_by_id(connection, int(payload['epi_id']))
        ensure_resource_company(actor, epi, 'EPI')
        scope_unit_id = actor_operational_unit_id(connection, actor)
        if not scope_unit_id:
            raise PermissionError('Perfil sem unidade operacional ativa para editar estoque mínimo.')
        if scope_unit_id and int(epi.get('unit_id') or 0) != int(scope_unit_id):
            raise PermissionError('Perfil só pode editar estoque mínimo da unidade operacional ativa.')
        minimum_stock = max(0, int(payload.get('minimum_stock') or 0))
        connection.execute('UPDATE epis SET minimum_stock = ? WHERE id = ?', (minimum_stock, int(payload['epi_id'])))
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'minimum_stock': minimum_stock})


# ── POST /api/stock/movements ─────────────────────────────────────────────────

def handle_post_stock_movements(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'company_id', 'unit_id', 'epi_id', 'movement_type', 'quantity', 'label_measure', 'label_printer_name', 'label_print_format', 'manufacture_date'])
    sp = _get_server()
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
        quantity = int(payload.get('quantity') or 0)
        if quantity <= 0:
            raise ValueError('Quantidade deve ser maior que zero.')
        resolved_size = sp.resolve_item_size(
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
        stock_row = sp.get_unit_stock(connection, int(payload['company_id']), int(payload['unit_id']), int(payload['epi_id']))
        previous_stock = int((stock_row or {}).get('quantity') or 0)
        delta = quantity if movement_type == 'in' else -quantity
        new_stock = previous_stock + delta
        if new_stock < 0:
            raise ValueError('Saída deixa estoque negativo.')
        sp.ensure_stock_movement_size_columns(connection)
        movement_cursor = connection.execute(
            (
                'INSERT INTO stock_movements ('
                'company_id, unit_id, epi_id, movement_type, quantity, previous_stock, new_stock, '
                'source_type, source_id, notes, actor_user_id, actor_name, created_at, glove_size, size, uniform_size'
                ') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
            ),
            (
                int(payload['company_id']),
                int(payload['unit_id']),
                int(payload['epi_id']),
                movement_type,
                quantity,
                previous_stock,
                new_stock,
                'manual',
                None,
                str(payload.get('notes', '')).strip(),
                actor['id'],
                actor['full_name'],
                datetime.now(UTC).isoformat(),
                glove_size,
                size,
                uniform_size
            )
        )
        sp.upsert_unit_stock(connection, int(payload['company_id']), int(payload['unit_id']), int(payload['epi_id']), new_stock)
        qr_labels = []
        if movement_type == 'in':
            now = datetime.now(UTC).isoformat()
            for _ in range(quantity):
                seq_value = sp.next_company_qr_sequence(connection, int(payload['company_id']))
                qr_value = sp.build_stock_item_qr(int(payload['company_id']), int(payload['unit_id']), seq_value)
                stock_item_cursor = connection.execute(
                    (
                        'INSERT INTO epi_stock_items ('
                        'company_id, unit_id, epi_id, glove_size, size, uniform_size, qr_sequence, qr_code_value, status, '
                        'stock_movement_id, lot_code, manufacture_date, label_measure, label_printer_name, label_print_format, generated_by_user_id, created_at, updated_at'
                        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'in_stock', ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                    ),
                    (
                        int(payload['company_id']),
                        int(payload['unit_id']),
                        int(payload['epi_id']),
                        glove_size,
                        size,
                        uniform_size,
                        seq_value,
                        qr_value,
                        int(movement_cursor.lastrowid),
                        lot_code,
                        manufacture_date,
                        label_measure,
                        label_printer_name,
                        label_print_format,
                        int(actor['id']),
                        now,
                        now
                    )
                )
                qr_labels.append({
                    'qr_code_value': qr_value,
                    'epi_name': epi['name'],
                    'glove_size': glove_size,
                    'size': size,
                    'uniform_size': uniform_size,
                    'stock_item_id': stock_item_cursor.lastrowid,
                    'manufacture_date': manufacture_date,
                    'unit_name': unit['name'],
                    'label_measure': label_measure,
                    'label_printer_name': label_printer_name,
                    'label_print_format': label_print_format,
                    'reprint_count': 0
                })
        connection.commit()
        return send_json(handler, 201, {'ok': True, 'movement_id': movement_cursor.lastrowid, 'new_stock': new_stock, 'qr_labels': qr_labels})


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
        stock_item = connection.execute(
            (
                'SELECT esi.id, esi.company_id, esi.unit_id, esi.epi_id, esi.qr_code_value, esi.status, esi.glove_size, esi.size, '
                'esi.uniform_size, esi.label_measure, esi.label_printer_name, esi.label_print_format, esi.reprint_count, '
                'units.name AS unit_name, epis.name AS epi_name '
                'FROM epi_stock_items esi '
                'JOIN units ON units.id = esi.unit_id '
                'JOIN epis ON epis.id = esi.epi_id '
                'WHERE esi.id = ?'
            ),
            (int(payload['stock_item_id']),)
        ).fetchone()
        if not stock_item:
            raise ValueError('Etiqueta não encontrada para reimpressão.')
        ensure_resource_company(actor, stock_item, 'Etiqueta')
        now = datetime.now(UTC).isoformat()
        connection.execute(
            (
                'INSERT INTO epi_stock_item_reprints (stock_item_id, company_id, reason_code, reason_note, actor_user_id, actor_name, created_at) '
                'VALUES (?, ?, ?, ?, ?, ?, ?)'
            ),
            (
                int(stock_item['id']),
                int(stock_item['company_id']),
                reason_code,
                reason_note,
                int(actor['id']),
                str(actor.get('full_name') or ''),
                now
            )
        )
        connection.execute(
            'UPDATE epi_stock_items SET reprint_count = COALESCE(reprint_count, 0) + 1, updated_at = ? WHERE id = ?',
            (now, int(stock_item['id']))
        )
        updated = connection.execute('SELECT reprint_count FROM epi_stock_items WHERE id = ?', (int(stock_item['id']),)).fetchone()
        connection.commit()
        label_payload = row_to_dict(stock_item)
        label_payload['stock_item_id'] = int(stock_item['id'])
        label_payload['reprint_count'] = int(updated['reprint_count']) if updated else 0
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
        scope_unit_id = actor_operational_unit_id(connection, actor)
        if actor.get('role') in ('admin', 'user') and not scope_unit_id:
            raise PermissionError('Perfil sem unidade operacional ativa para consultar estoque.')
        unit_filter = scope_unit_id or query.get('unit_id', [''])[0]
        company_scope_id = int(company_filter or 0)
        if unit_filter and not company_scope_id:
            unit_row = get_unit_by_id(connection, int(unit_filter))
            company_scope_id = int(unit_row['company_id']) if unit_row else 0
        protection = str(query.get('protection', [''])[0]).strip().lower()
        name = str(query.get('name', [''])[0]).strip().lower()
        section = str(query.get('section', [''])[0]).strip().lower()
        manufacturer = str(query.get('manufacturer', [''])[0]).strip().lower()
        ca = str(query.get('ca', [''])[0]).strip().lower()
        epis = fetch_epis(connection, actor if actor['role'] != 'master_admin' else None, None)
        target_unit_jv_name = get_unit_active_jv_name(connection, unit_filter) if unit_filter else ''
        items = []
        for epi in epis:
            if company_filter and str(epi.get('company_id')) != str(company_filter):
                continue
            if protection and protection not in str(epi.get('sector') or '').lower():
                continue
            if name and name not in str(epi.get('name') or '').lower():
                continue
            if section and section not in str(epi.get('epi_section') or '').lower():
                continue
            if manufacturer and manufacturer not in str(epi.get('manufacturer') or '').lower():
                continue
            if ca and ca not in str(epi.get('ca') or '').lower():
                continue
            if unit_filter and not is_epi_visible_for_unit(
                epi_unit_id=epi.get('unit_id'),
                epi_joint_venture_name=epi.get('active_joinventure'),
                target_unit_id=unit_filter,
                target_unit_joint_venture_name=target_unit_jv_name,
            ):
                continue
            stock_unit_id = int(unit_filter or 0)
            stock_row = get_unit_stock(connection, int(epi['company_id']), stock_unit_id, int(epi['id'])) if stock_unit_id else None
            item = dict(epi)
            item['stock'] = int((stock_row or {}).get('quantity') or (item.get('stock') or 0))
            size_rows = fetch_epi_size_balance(connection, int(epi['company_id']), stock_unit_id, int(epi['id'])) if stock_unit_id else []
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
    router.register('GET',  '/api/stock/movements/report',       handle_get_stock_movements_report)
    router.register('POST', '/api/stock/minimum',                handle_post_stock_minimum)
    router.register('POST', '/api/stock/movements',              handle_post_stock_movements)
    router.register('POST', '/api/stock/manufacture-date-ocr',   handle_post_stock_manufacture_date_ocr)
    router.register('POST', '/api/stock/labels/reprint',         handle_post_stock_labels_reprint)
