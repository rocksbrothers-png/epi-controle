"""Serviços de fichas EPI."""
from datetime import datetime, timedelta, timezone

from epi_backend.db import row_to_dict
from epi_backend.http_utils import structured_log
from core.auth import ensure_resource_company
from modules.settings.service import get_ficha_config

UTC = timezone.utc


def period_days_from_schedule(schedule_type):
    raw = str(schedule_type or '').strip().lower()
    if '14x14' in raw:
        return 14
    if '28x28' in raw:
        return 28
    if '30' in raw:
        return 30
    if '31' in raw:
        return 31
    return 30


def resolve_delivery_period(delivery_date, schedule_type):
    from datetime import date as _date
    start = datetime.strptime(str(delivery_date), '%Y-%m-%d').date()
    days = period_days_from_schedule(schedule_type)
    end = start + timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


def _is_sqlite_connection(connection):
    module_name = str(getattr(type(connection), '__module__', '')).lower()
    class_name = str(getattr(type(connection), '__name__', '')).lower()
    return 'sqlite' in module_name or 'sqlite' in class_name


def _table_exists(connection, table):
    table_name = str(table or '').strip()
    if not table_name:
        return False
    try:
        if _is_sqlite_connection(connection):
            row = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
                (table_name,),
            ).fetchone()
            return row is not None
        row = connection.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = ? LIMIT 1",
            (table_name,),
        ).fetchone()
        return row is not None
    except Exception:
        return False


def ensure_ficha_for_delivery(connection, delivery_row):
    delivery_date = str(delivery_row['delivery_date'])
    schedule_type = str(delivery_row.get('schedule_type') or '')
    unit_id = int(delivery_row['unit_id'])
    now = datetime.now(UTC).isoformat()
    ficha = None
    try:
        ficha = connection.execute(
            '''
            SELECT id, period_start, period_end, status
            FROM epi_ficha_periods
            WHERE employee_id = ? AND unit_id = ? AND schedule_type = ? AND status = 'open'
            ORDER BY id DESC
            LIMIT 1
            ''',
            (delivery_row['employee_id'], unit_id, schedule_type)
        ).fetchone()
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    if ficha:
        ficha_id = int(ficha['id'])
        current_start = str(ficha.get('period_start') or delivery_date)
        current_end = str(ficha.get('period_end') or delivery_date)
        next_start = min(current_start, delivery_date)
        next_end = max(current_end, delivery_date)
        try:
            connection.execute(
                'UPDATE epi_ficha_periods SET period_start = ?, period_end = ?, status = ?, updated_at = ? WHERE id = ?',
                (next_start, next_end, 'open', now, ficha_id)
            )
        except Exception as _e:
            structured_log('warning', 'db.col_skip', error=str(_e))
    else:
        period_start, period_end = resolve_delivery_period(delivery_date, schedule_type)
        sequence_row = connection.execute(
            'SELECT COALESCE(MAX(ficha_sequence), 0) AS max_sequence FROM epi_ficha_periods WHERE employee_id = ? AND period_start = ? AND period_end = ?',
            (delivery_row['employee_id'], period_start, period_end),
        ).fetchone()
        next_sequence = int((row_to_dict(sequence_row) if sequence_row else {}).get('max_sequence') or 0) + 1
        cursor = None
        try:
            cursor = connection.execute(
                '''
                INSERT INTO epi_ficha_periods (
                    company_id, employee_id, unit_id, schedule_type, period_start, period_end, ficha_sequence,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)
                ''',
                (
                    delivery_row['company_id'],
                    delivery_row['employee_id'],
                    unit_id,
                    schedule_type,
                    period_start,
                    period_end,
                    next_sequence,
                    now,
                    now
                )
            )
        except Exception as _e:
            structured_log('warning', 'db.col_skip', error=str(_e))
            raise
        if not cursor:
            raise ValueError('Falha ao criar período da ficha para entrega.')
        ficha_id = int(cursor.lastrowid)
    try:
        connection.execute(
            '''
            INSERT INTO epi_ficha_items (
                ficha_period_id, delivery_id, company_id, employee_id, unit_id, epi_id, quantity,
                item_signature_name, item_signature_data, item_signature_ip, item_signature_at, item_signature_comment, signed_mode,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (delivery_id) DO NOTHING
            ''',
            (
                ficha_id,
                delivery_row['id'],
                delivery_row['company_id'],
                delivery_row['employee_id'],
                delivery_row['unit_id'],
                delivery_row['epi_id'],
                delivery_row['quantity'],
                str(delivery_row.get('signature_name') or ''),
                str(delivery_row.get('signature_data') or ''),
                str(delivery_row.get('signature_ip') or ''),
                str(delivery_row.get('signature_at') or ''),
                str(delivery_row.get('signature_comment') or ''),
                'delivery' if str(delivery_row.get('signature_data') or '').strip() else '',
                now,
                now
            )
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    return ficha_id


def ensure_ficha_for_devolution(connection, devolution_row):
    returned_date = str(devolution_row['returned_date'])
    now = datetime.now(UTC).isoformat()
    employee_id = int(devolution_row['employee_id'])
    company_id = int(devolution_row['company_id'])
    unit_id = int(devolution_row['unit_id'])
    schedule_type = str(devolution_row.get('schedule_type') or '')
    exact_period = connection.execute(
        '''
        SELECT id, period_start, period_end, status
        FROM epi_ficha_periods
        WHERE employee_id = ?
          AND period_start <= ?
          AND period_end >= ?
        ORDER BY CASE WHEN status = 'open' THEN 0 ELSE 1 END, id DESC
        LIMIT 1
        ''',
        (employee_id, returned_date, returned_date),
    ).fetchone()
    if exact_period:
        ficha_id = int(exact_period['id'])
    else:
        open_period = connection.execute(
            '''
            SELECT id, period_start, period_end, status
            FROM epi_ficha_periods
            WHERE employee_id = ? AND status <> 'closed'
            ORDER BY id DESC
            LIMIT 1
            ''',
            (employee_id,),
        ).fetchone()
        if open_period:
            ficha_id = int(open_period['id'])
            next_start = min(str(open_period.get('period_start') or returned_date), returned_date)
            next_end = max(str(open_period.get('period_end') or returned_date), returned_date)
            next_status = 'open' if str(open_period.get('status') or '').lower() in {'open', 'signed'} else str(open_period.get('status') or 'open')
            connection.execute(
                'UPDATE epi_ficha_periods SET period_start = ?, period_end = ?, status = ?, updated_at = ? WHERE id = ?',
                (next_start, next_end, next_status, now, ficha_id),
            )
        else:
            _dev_seq_row = connection.execute(
                'SELECT COALESCE(MAX(ficha_sequence), 0) AS max_sequence FROM epi_ficha_periods WHERE employee_id = ? AND period_start = ? AND period_end = ?',
                (employee_id, returned_date, returned_date),
            ).fetchone()
            _dev_next_sequence = int((row_to_dict(_dev_seq_row) if _dev_seq_row else {}).get('max_sequence') or 0) + 1
            cursor = connection.execute(
                '''
                INSERT INTO epi_ficha_periods (
                    company_id, employee_id, unit_id, schedule_type, period_start, period_end, ficha_sequence,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)
                ''',
                (
                    company_id,
                    employee_id,
                    unit_id,
                    schedule_type,
                    returned_date,
                    returned_date,
                    _dev_next_sequence,
                    now,
                    now,
                ),
            )
            ficha_id = int(cursor.lastrowid)
            delivery_row = connection.execute(
                (
                    'SELECT d.id, d.company_id, d.employee_id, d.unit_id, d.epi_id, d.quantity '
                    'FROM deliveries d '
                    'JOIN epi_devolutions dev ON dev.delivery_id = d.id '
                    'WHERE dev.id = ?'
                ),
                (int(devolution_row['id']),),
            ).fetchone()
            if delivery_row and _table_exists(connection, 'epi_ficha_items'):
                delivery_data = row_to_dict(delivery_row)
                connection.execute(
                    '''
                    INSERT INTO epi_ficha_items (
                        ficha_period_id, delivery_id, company_id, employee_id, unit_id, epi_id, quantity,
                        item_signature_name, item_signature_data, item_signature_ip, item_signature_at, item_signature_comment, signed_mode,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, '', '', '', '', '', '', ?, ?)
                    ON CONFLICT (delivery_id) DO NOTHING
                    ''',
                    (
                        ficha_id,
                        int(delivery_data['id']),
                        int(delivery_data['company_id']),
                        int(delivery_data['employee_id']),
                        int(delivery_data['unit_id']),
                        int(delivery_data['epi_id']),
                        int(delivery_data.get('quantity') or 0),
                        now,
                        now,
                    ),
                )
    connection.execute(
        'UPDATE epi_devolutions SET ficha_period_id = ? WHERE id = ?',
        (ficha_id, int(devolution_row['id'])),
    )
    return ficha_id


def render_ficha_epi_html_document(*, employee, company, unit, deliveries, devolutions, config, period_label=''):
    """Renderiza o HTML da ficha com dados já resolvidos (sem consultas implícitas)."""
    logo_data = str(company.get('logo_type') or '')
    rows_html = ''
    for item in deliveries:
        sig_html = ''
        if item.get('signature_data') and str(item['signature_data']).startswith('data:image'):
            sig_html = f'<img src="{item["signature_data"]}" style="max-height:28px;max-width:80px;">'
        qty = str(item.get('quantity') or 1)
        unid = str(item.get('unit_measure') or 'UNIDADE').upper()
        epi_name = str(item.get('epi_name') or '')
        ca = str(item.get('ca') or '')
        fab = str(item.get('manufacture_date') or '')
        validade = str(item.get('next_replacement_date') or item.get('epi_validity_date') or '')
        recebido = str(item.get('delivery_date') or '')
        devolvido = str(item.get('returned_date') or '')
        rows_html += f"""
        <tr>
          <td style="text-align:center">{qty}</td>
          <td style="text-align:center">{unid}</td>
          <td>{epi_name}</td>
          <td style="text-align:center">{ca}</td>
          <td style="text-align:center">{fab}</td>
          <td style="text-align:center">{validade}</td>
          <td style="text-align:center">{recebido}</td>
          <td style="text-align:center">{devolvido}</td>
          <td style="text-align:center">{sig_html}</td>
        </tr>"""

    for _ in range(max(0, 20 - len(deliveries))):
        rows_html += """
        <tr>
          <td>&nbsp;</td><td></td><td></td><td></td>
          <td></td><td></td><td></td><td></td><td></td>
        </tr>"""

    if logo_data.startswith('data:image'):
        logo_html = f'<img src="{logo_data}" style="max-height:60px;max-width:180px;">'
    else:
        logo_html = f'<div style="font-size:18px;font-weight:bold;">{company.get("name","")}</div>'

    declaracao_html = str(config.get('declaracao', '')).replace('\n', '<br>')
    observacoes_html = str(config.get('observacoes', '')).replace('\n', '<br>')
    unit_name = str(unit.get('name') or '')

    condition_labels = {
        'usable': 'Reutilizável', 'damaged': 'Danificado', 'discarded': 'Descartado',
        'maintenance': 'Em manutenção', 'quarantine': 'Em quarentena', 'hygiene': 'Para higienização'
    }
    destination_labels = {
        'stock': 'Retornou ao estoque', 'discard': 'Descartado',
        'maintenance': 'Manutenção', 'hygiene': 'Higienização', 'quarantine': 'Quarentena'
    }
    devol_rows_html = ''
    for dv in devolutions:
        devol_rows_html += (
            f'<tr>'
            f'<td>{dv.get("epi_name","")}</td>'
            f'<td style="text-align:center">{dv.get("qty_entregue","")}</td>'
            f'<td style="text-align:center">{dv.get("delivery_date","")}</td>'
            f'<td style="text-align:center">{dv.get("returned_date","")}</td>'
            f'<td style="text-align:center">{condition_labels.get(dv.get("condition",""),dv.get("condition",""))}</td>'
            f'<td style="text-align:center">{destination_labels.get(dv.get("destination",""),dv.get("destination",""))}</td>'
            f'<td style="text-align:center">{dv.get("received_by_name","")}</td>'
            f'<td style="text-align:center">{dv.get("signature_name","") or ("Pendente no fechamento" if not dv.get("signature_at","") else "")}</td>'
            f'<td>{dv.get("reason","") or dv.get("notes","")}</td>'
            f'</tr>'
        )

    devol_section_html = ''
    if devolutions:
        devol_section_html = f"""
        <div class="secao" style="margin-top:24px">
          <h3 style="font-size:11pt;font-weight:bold;border-bottom:2px solid #333;padding-bottom:4px;margin-bottom:8px">
            Histórico de Devoluções de EPI
          </h3>
          <table style="width:100%;border-collapse:collapse;font-size:9pt">
            <thead>
              <tr style="background:#f0f0f0">
                <th style="border:1px solid #ccc;padding:4px 6px;text-align:left">EPI</th>
                <th style="border:1px solid #ccc;padding:4px 6px;text-align:center">Qtd</th>
                <th style="border:1px solid #ccc;padding:4px 6px;text-align:center">Data Entrega</th>
                <th style="border:1px solid #ccc;padding:4px 6px;text-align:center">Data Devolução</th>
                <th style="border:1px solid #ccc;padding:4px 6px;text-align:center">Condição</th>
                <th style="border:1px solid #ccc;padding:4px 6px;text-align:center">Destino</th>
                <th style="border:1px solid #ccc;padding:4px 6px;text-align:center">Recebido por</th>
                <th style="border:1px solid #ccc;padding:4px 6px;text-align:center">Assinatura</th>
                <th style="border:1px solid #ccc;padding:4px 6px;text-align:left">Motivo</th>
              </tr>
            </thead>
            <tbody>
              {devol_rows_html}
            </tbody>
          </table>
        </div>
        """

    period_row = ''
    if str(period_label or '').strip():
        period_row = f"""
  <div class="dados-linha">
    <div class="campo"><span class="campo-label">PERÍODO:</span> <span>{period_label}</span></div>
  </div>"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Ficha EPI - {employee.get("name","")}</title>
<style>
  @page {{ margin: 12mm 15mm; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Arial, Helvetica, sans-serif; font-size: 9pt; color: #111; background: #fff; }}
  .header {{ display: flex; align-items: center; margin-bottom: 10px; padding-bottom: 6px; border-bottom: 1px solid #333; }}
  .logo {{ margin-right: 20px; }}
  .titulo {{ text-align: center; font-size: 10pt; font-weight: bold; margin-bottom: 10px; }}
  .dados-colaborador {{ margin-bottom: 8px; border-bottom: 1px solid #ccc; padding-bottom: 6px; }}
  .dados-linha {{ display: flex; gap: 30px; margin-bottom: 2px; }}
  .campo {{ display: flex; gap: 6px; }}
  .campo-label {{ font-weight: bold; white-space: nowrap; }}
  .declaracao {{ font-size: 8pt; margin-bottom: 8px; text-align: justify; line-height: 1.4; border: 1px solid #ccc; padding: 6px; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 6px; font-size: 8pt; }}
  th {{ background: #f0f0f0; border: 1px solid #333; padding: 4px 3px; text-align: center; font-size: 7.5pt; font-weight: bold; }}
  td {{ border: 1px solid #555; padding: 3px 3px; height: 18px; font-size: 8pt; }}
  .th-quant {{ width: 5%; }} .th-unid {{ width: 7%; }} .th-epi {{ width: 28%; }} .th-ca {{ width: 6%; }}
  .th-fab {{ width: 8%; }} .th-vida {{ width: 8%; }} .th-receb {{ width: 8%; }} .th-devol {{ width: 8%; }} .th-assina {{ width: 12%; }}
  .observacoes {{ font-size: 8pt; margin-top: 4px; font-weight: bold; line-height: 1.4; }}
  .rodape {{ margin-top: 8px; padding-top: 4px; border-top: 1px solid #ccc; text-align: center; font-size: 7pt; color: #555; }}
</style>
</head>
<body>
<div class="header"><div class="logo">{logo_html}</div></div>
<div class="titulo">{config['titulo']}</div>
<div class="dados-colaborador">
  <div class="dados-linha"><div class="campo"><span class="campo-label">NOME:</span> <span>{employee.get('name','')}</span></div></div>
  <div class="dados-linha"><div class="campo"><span class="campo-label">FUNÇÃO:</span> <span>{employee.get('role_name','')}</span></div></div>
  <div class="dados-linha">
    <div class="campo"><span class="campo-label">SETOR:</span> <span>{employee.get('sector','')}</span></div>
    <div class="campo" style="margin-left:auto"><span class="campo-label">UNIDADE:</span> <span>{unit_name}</span></div>
  </div>{period_row}
</div>
<div class="declaracao">{declaracao_html}</div>
<table><thead><tr>
<th class="th-quant">QUANT</th><th class="th-unid">UNID</th><th class="th-epi">EPI</th>
<th class="th-ca">CA</th><th class="th-fab">FABRICAÇÃO</th><th class="th-vida">VIDA ÚTIL</th>
<th class="th-receb">RECEBIDO</th><th class="th-devol">DEVOLVIDO</th><th class="th-assina">ASSINATURA</th>
</tr></thead><tbody>{rows_html}</tbody></table>
<div class="observacoes">{observacoes_html}</div>
{devol_section_html}
<div class="rodape">{config['rastreabilidade']}</div>
</body>
</html>"""


def build_ficha_epi_html(connection, employee_id, actor, *, get_employee_fn=None, ensure_actor_scope_fn=None):
    employee = get_employee_fn(connection, int(employee_id)) if get_employee_fn is not None else None
    if not employee:
        raise ValueError('Colaborador não encontrado.')
    ensure_resource_company(actor, employee, 'Colaborador')
    if ensure_actor_scope_fn is not None:
        ensure_actor_scope_fn(connection, actor, employee)

    company = connection.execute('SELECT id, name, logo_type FROM companies WHERE id = ?', (int(employee['company_id']),)).fetchone()
    unit = connection.execute('SELECT id, name, unit_type FROM units WHERE id = ?', (int(employee['unit_id']),)).fetchone()
    has_stock_items_table = _table_exists(connection, 'epi_stock_items')
    manufacture_expr = "COALESCE(NULLIF(esi.manufacture_date, ''), e.manufacture_date)" if has_stock_items_table else 'e.manufacture_date'
    join_stock_items = 'LEFT JOIN epi_stock_items esi ON esi.delivery_id = d.id' if has_stock_items_table else ''
    deliveries = connection.execute(
        f"""
        SELECT d.id, d.quantity, d.delivery_date, d.next_replacement_date,
               d.signature_data, d.signature_name, d.returned_date,
               e.name AS epi_name, e.ca, e.unit_measure,
               {manufacture_expr} AS manufacture_date, e.epi_validity_date
        FROM deliveries d
        JOIN epis e ON e.id = d.epi_id
        {join_stock_items}
        WHERE d.employee_id = ?
        ORDER BY d.delivery_date DESC, d.id DESC
        """,
        (int(employee_id),)
    ).fetchall()
    devolutions = connection.execute(
        """
        SELECT dev.returned_date, dev.condition, dev.destination, dev.notes, dev.reason,
               dev.signature_name, dev.signature_at,
               dev.received_by_name, dev.quantity,
               e.name AS epi_name, e.ca, e.unit_measure,
               d.delivery_date, d.quantity AS qty_entregue
          FROM epi_devolutions dev
          JOIN epis e ON e.id = dev.epi_id
          JOIN deliveries d ON d.id = dev.delivery_id
         WHERE dev.employee_id = ?
           AND dev.company_id = ?
         ORDER BY dev.returned_date DESC, dev.id DESC
        """,
        (int(employee_id), int(employee['company_id']))
    ).fetchall()
    return render_ficha_epi_html_document(
        employee=employee,
        company=row_to_dict(company) if company else {},
        unit=row_to_dict(unit) if unit else {},
        deliveries=[row_to_dict(item) for item in deliveries],
        devolutions=[row_to_dict(item) for item in devolutions],
        config=get_ficha_config(connection, int(employee['company_id'])),
    )


def build_ficha_epi_html_by_period(connection, ficha_period_id, actor, *, get_employee_fn=None, actor_unit_id_fn=None):
    ficha = connection.execute(
        'SELECT fp.id, fp.company_id, fp.employee_id, fp.unit_id, fp.period_start, fp.period_end FROM epi_ficha_periods fp WHERE fp.id = ?',
        (int(ficha_period_id),),
    ).fetchone()
    if not ficha:
        raise ValueError('Período da ficha não encontrado.')
    ficha = row_to_dict(ficha)
    employee = get_employee_fn(connection, int(ficha['employee_id'])) if get_employee_fn is not None else None
    if not employee:
        raise ValueError('Colaborador não encontrado para o período informado.')
    ensure_resource_company(actor, employee, 'Colaborador')
    scope_unit_id = actor_unit_id_fn(connection, actor) if actor_unit_id_fn is not None else None
    if scope_unit_id and int(employee['unit_id']) != int(scope_unit_id):
        raise PermissionError('Seu perfil só pode acessar fichas da própria unidade operacional.')

    company = connection.execute('SELECT id, name, logo_type FROM companies WHERE id = ?', (int(employee['company_id']),)).fetchone()
    unit = connection.execute('SELECT id, name, unit_type FROM units WHERE id = ?', (int(employee['unit_id']),)).fetchone()
    has_stock_items_table = _table_exists(connection, 'epi_stock_items')
    manufacture_expr = "COALESCE(NULLIF(esi.manufacture_date, ''), e.manufacture_date)" if has_stock_items_table else 'e.manufacture_date'
    join_stock_items = 'LEFT JOIN epi_stock_items esi ON esi.delivery_id = d.id ' if has_stock_items_table else ''
    deliveries = connection.execute(
        (
            'SELECT d.id, fi.quantity, d.delivery_date, d.next_replacement_date, '
            'fi.item_signature_data AS signature_data, fi.item_signature_name AS signature_name, d.returned_date, '
            f'e.name AS epi_name, e.ca, e.unit_measure, {manufacture_expr} AS manufacture_date, e.epi_validity_date '
            'FROM epi_ficha_items fi '
            'JOIN deliveries d ON d.id = fi.delivery_id '
            'JOIN epis e ON e.id = fi.epi_id '
            f'{join_stock_items}'
            'WHERE fi.ficha_period_id = ? '
            'ORDER BY d.delivery_date DESC, d.id DESC'
        ),
        (int(ficha_period_id),),
    ).fetchall()
    devolutions = connection.execute(
        (
            'SELECT dev.returned_date, dev.condition, dev.destination, dev.notes, dev.reason, '
            'dev.signature_name, dev.signature_at, dev.received_by_name, dev.quantity, '
            'e.name AS epi_name, e.ca, e.unit_measure, d.delivery_date, d.quantity AS qty_entregue '
            'FROM epi_devolutions dev '
            'JOIN epis e ON e.id = dev.epi_id '
            'JOIN deliveries d ON d.id = dev.delivery_id '
            'WHERE dev.ficha_period_id = ? '
            'ORDER BY dev.returned_date DESC, dev.id DESC'
        ),
        (int(ficha_period_id),),
    ).fetchall()
    return render_ficha_epi_html_document(
        employee=employee,
        company=row_to_dict(company) if company else {},
        unit=row_to_dict(unit) if unit else {},
        deliveries=[row_to_dict(item) for item in deliveries],
        devolutions=[row_to_dict(item) for item in devolutions],
        config=get_ficha_config(connection, int(employee['company_id'])),
        period_label=f"{ficha.get('period_start', '')} a {ficha.get('period_end', '')}",
    )


# ── Estado e fechamento de períodos de ficha ──────────────────────────────────

def compute_ficha_period_signature_state(connection, ficha_period_id):
    row = connection.execute(
        (
            "SELECT fp.id, fp.batch_signature_name, fp.batch_signature_data, fp.batch_signature_at, "
            "COUNT(fi.id) AS total_items, "
            "SUM(CASE WHEN fi.id IS NOT NULL AND COALESCE(fi.item_signature_at, '') <> '' THEN 1 ELSE 0 END) AS signed_items, "
            "SUM(CASE WHEN fi.id IS NOT NULL AND COALESCE(fi.item_signature_at, '') = '' THEN 1 ELSE 0 END) AS pending_items "
            "FROM epi_ficha_periods fp "
            "LEFT JOIN epi_ficha_items fi ON fi.ficha_period_id = fp.id "
            "WHERE fp.id = ? "
            "GROUP BY fp.id, fp.batch_signature_name, fp.batch_signature_data, fp.batch_signature_at"
        ),
        (int(ficha_period_id),),
    ).fetchone()
    if not row:
        raise ValueError('Período de ficha não encontrado.')
    data = row_to_dict(row)
    total_items = int(data.get('total_items') or 0)
    signed_items = int(data.get('signed_items') or 0)
    pending_items = int(data.get('pending_items') or 0)
    has_batch_signature = bool(
        str(data.get('batch_signature_name') or '').strip()
        and str(data.get('batch_signature_data') or '').strip()
        and str(data.get('batch_signature_at') or '').strip()
    )
    can_close = total_items > 0 and pending_items == 0 and signed_items == total_items and has_batch_signature
    return {
        'total_items': total_items,
        'signed_items': signed_items,
        'pending_items': pending_items,
        'has_batch_signature': has_batch_signature,
        'can_close': can_close,
    }


def get_ficha_period_close_requirements(state):
    missing = []
    if int(state.get('total_items') or 0) <= 0:
        missing.append('total_items')
    if int(state.get('pending_items') or 0) > 0:
        missing.append('pending_items')
    if int(state.get('signed_items') or 0) != int(state.get('total_items') or 0):
        missing.append('signed_items')
    if not bool(state.get('has_batch_signature')):
        missing.append('batch_signature')
    return missing


def is_valid_ficha_period_state(state):
    return int(state.get('total_items') or 0) > 0


def assert_ficha_period_can_close(connection, ficha_period_id):
    state = compute_ficha_period_signature_state(connection, ficha_period_id)
    if not state['can_close']:
        missing_requirements = get_ficha_period_close_requirements(state)
        if 'pending_items' in missing_requirements or 'signed_items' in missing_requirements:
            raise ValueError('Não é possível fechar o período: existem assinaturas pendentes.')
        if 'batch_signature' in missing_requirements:
            raise ValueError('Não é possível fechar o período: assinatura em lote ausente ou incompleta.')
        if 'total_items' in missing_requirements:
            raise ValueError('Não é possível fechar o período: não há itens no período.')
        raise ValueError('Não é possível fechar o período: requisitos de fechamento não atendidos.')
    return state


def resolve_ficha_period_effective_status(connection, ficha_period):
    period = dict(ficha_period or {})
    state = compute_ficha_period_signature_state(connection, int(period.get('id') or 0))
    effective_status = 'closed' if state['can_close'] else ('pending_signature' if state['pending_items'] > 0 else 'open')
    period['status_effective'] = effective_status
    period['pending_items'] = state['pending_items']
    period['total_items'] = state['total_items']
    period['signed_items'] = state['signed_items']
    period['has_batch_signature'] = state['has_batch_signature']
    if str(period.get('status') or '').strip().lower() == 'closed' and effective_status != 'closed':
        now = datetime.now(UTC).isoformat()
        connection.execute(
            'UPDATE epi_ficha_periods SET status = ?, updated_at = ? WHERE id = ?',
            (effective_status, now, int(period['id']))
        )
        period['status'] = effective_status
    return period


# ── Auditoria e retenção de snapshots ─────────────────────────────────────────

def fetch_ficha_epi_audit_logs(connection, actor, filters=None):
    from core.repository import actor_operational_unit_id
    filters = filters or {}
    clauses = []
    params = []
    if actor.get('role') != 'master_admin':
        clauses.append('l.company_id = ?')
        params.append(int(actor['company_id']))
    scope_unit_id = actor_operational_unit_id(connection, actor)
    if scope_unit_id:
        clauses.append('l.unit_id = ?')
        params.append(int(scope_unit_id))
    if filters.get('employee_id'):
        clauses.append('l.employee_id = ?')
        params.append(int(filters['employee_id']))
    if filters.get('actor_user_id'):
        clauses.append('l.actor_user_id = ?')
        params.append(int(filters['actor_user_id']))
    if filters.get('action'):
        clauses.append('l.action = ?')
        params.append(str(filters['action']).strip().lower())
    if filters.get('date_from'):
        clauses.append('l.accessed_at >= ?')
        params.append(f"{str(filters['date_from']).strip()}T00:00:00")
    if filters.get('date_to'):
        clauses.append('l.accessed_at <= ?')
        params.append(f"{str(filters['date_to']).strip()}T23:59:59")
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ''
    rows = connection.execute(
        (
            'SELECT l.*, units.name AS unit_name '
            'FROM ficha_epi_audit_log l '
            'LEFT JOIN units ON units.id = l.unit_id '
            f'{where_sql} '
            'ORDER BY l.accessed_at DESC, l.id DESC LIMIT 1000'
        ),
        tuple(params),
    ).fetchall()
    return [row_to_dict(item) for item in rows]


def apply_snapshot_retention(connection, company_id, policy):
    now_iso = datetime.now(UTC).isoformat()
    params = [now_iso]
    where_clause = ''
    if company_id:
        where_clause = ' AND company_id = ?'
        params.append(int(company_id))
    connection.execute(
        f"UPDATE ficha_epi_snapshots SET status = 'expired', expired_at = ? WHERE status = 'archived' AND expires_at <= ?{where_clause}",
        tuple([now_iso, now_iso, *params[1:]]) if company_id else (now_iso, now_iso),
    )
    if policy.get('purge_enabled'):
        if company_id:
            connection.execute(
                "UPDATE ficha_epi_snapshots SET status = 'purged', purged_at = ?, html_content = '', snapshot_payload = '{}' "
                "WHERE status = 'expired' AND company_id = ?",
                (now_iso, int(company_id)),
            )
        else:
            connection.execute(
                "UPDATE ficha_epi_snapshots SET status = 'purged', purged_at = ?, html_content = '', snapshot_payload = '{}' "
                "WHERE status = 'expired'",
                (now_iso,),
            )
    connection.commit()
