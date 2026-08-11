"""Serviços de entregas."""

import secrets
from datetime import datetime

from epi_backend.db import row_to_dict
from modules.deliveries.evidence import (
    QR_HANDOVER,
    SIGNATURE_HANDWRITTEN,
    record_evidence,
)
from modules.epis.validity import is_expired
from modules.stock.service import apply_effective_size_fields


def generate_handover_token():
    """Token OPACO da entrega (item 4). Não carrega dado pessoal: é só uma
    referência que, escaneada por quem tem sessão+permissão, resolve a projeção
    segura da entrega. Prefixo legível + entropia forte (url-safe)."""
    return f'ENTREGA-{secrets.token_urlsafe(18)}'


UTC = getattr(__import__('datetime'), 'UTC', None)
if UTC is None:
    from datetime import timezone
    UTC = timezone.utc

MSG_SIGNED_DIGITALLY = 'Assinado digitalmente'


def _normalize_history_date(value: object, field_label: str) -> str:
    """Data de planilha → ISO ``YYYY-MM-DD``.

    Export legado traz data em qualquer coisa: ``31/12/2024``, ``2024-12-31``,
    ``31-12-2024``, às vezes com hora colada. Gravar o texto cru quebraria toda
    comparação de período da ficha de EPI, que usa ``date(d.delivery_date)``.

    Formato ambíguo é ERRO, nunca um chute. ``03/04/2024`` pode ser 3 de abril
    ou 4 de março; num histórico de entrega de EPI, errar o mês desloca a
    entrega de período de ficha e pode fazê-la cair fora da vigência do CA.
    Este sistema é brasileiro e assume dia/mês — o que precisa estar escrito,
    não implícito.
    """
    raw = str(value or '').strip()
    if not raw:
        return ''
    raw = raw.split('T')[0].split(' ')[0]
    if len(raw) == 10 and raw[4] == '-' and raw[7] == '-':
        candidate = raw
    else:
        separator = '/' if '/' in raw else ('-' if '-' in raw else '')
        parts = raw.split(separator) if separator else []
        if len(parts) != 3:
            raise ValueError(
                f'{field_label} em formato não reconhecido: "{value}". '
                'Use DD/MM/AAAA ou AAAA-MM-DD.'
            )
        day, month, year = parts
        if len(year) == 2:
            # Janela de 2 dígitos: histórico de EPI é passado, e um "50" aqui é
            # 1950, não 2050. Fixar o corte evita que a interpretação mude com
            # o relógio da máquina.
            year = f'19{year}' if int(year) > 50 else f'20{year}'
        candidate = f'{int(year):04d}-{int(month):02d}-{int(day):02d}'
    try:
        datetime.strptime(candidate, '%Y-%m-%d')
    except ValueError as exc:
        raise ValueError(f'{field_label} inválida: "{value}".') from exc
    return candidate


def normalize_delivery_history_fields(payload: dict) -> dict:
    """Normalização de domínio do HISTÓRICO importado (issue #211).

    Deliberadamente **não** é a regra do cadastro manual. `create_delivery_service`
    exige leitura de QR, item de estoque, unidade operacional atual e quantidade
    unitária — tudo aplicável a uma entrega acontecendo agora, e nenhum deles
    verificável numa entrega de 2019 que o cliente está trazendo de outro
    sistema. Reaproveitá-lo obrigaria a inventar um item de estoque para cada
    linha do histórico, que é exatamente o que a #211 proíbe.

    O que continua valendo, e é o que esta função garante:

    - datas em ISO, para que os períodos da ficha continuem comparáveis;
    - quantidade inteira e positiva;
    - `signature_name` preservado mesmo sem imagem de assinatura. No fluxo
      manual, `signature_name` sem `signature_data` é zerado — porque lá o nome
      só existe se houve assinatura na tela. No histórico é o contrário: o nome
      de quem recebeu é o único registro que sobreviveu à migração, e apagá-lo
      destruiria a informação que dá valor ao dado importado;
    - `signature_data`/`signature_at` ficam VAZIOS. Uma entrega importada não
      tem assinatura coletada por este sistema, e preenchê-los afirmaria uma
      prova que não existe.

    Devolve um novo dicionário. Levanta ``ValueError`` com mensagem de negócio
    — que é o que o preview transforma em diagnóstico de linha, antes de
    qualquer gravação.
    """
    normalized = dict(payload)

    normalized['delivery_date'] = _normalize_history_date(
        normalized.get('delivery_date'), 'Data da entrega'
    )
    if not normalized['delivery_date']:
        raise ValueError('Data da entrega é obrigatória no histórico importado.')

    if str(normalized.get('returned_date') or '').strip():
        normalized['returned_date'] = _normalize_history_date(
            normalized.get('returned_date'), 'Data de devolução'
        )
        if normalized['returned_date'] < normalized['delivery_date']:
            raise ValueError(
                'Data de devolução anterior à data da entrega '
                f"({normalized['returned_date']} < {normalized['delivery_date']})."
            )

    raw_quantity = str(normalized.get('quantity') or '').strip()
    if raw_quantity:
        try:
            quantity = int(float(raw_quantity.replace(',', '.')))
        except ValueError as exc:
            raise ValueError(f'Quantidade inválida: "{normalized.get("quantity")}".') from exc
        if quantity < 1:
            raise ValueError('Quantidade da entrega precisa ser pelo menos 1.')
        normalized['quantity'] = quantity

    normalized['signature_name'] = ' '.join(
        str(normalized.get('signature_name') or '').split()
    )

    # A entrega importada não traz prova coletada por este sistema.
    normalized['signature_data'] = ''
    normalized['signature_at'] = ''
    normalized['signature_ip'] = ''
    return normalized

def ensure_stock_movement_size_columns(connection):
    # Delega para a versão canônica e agnóstica de banco (SQLite + PostgreSQL).
    # A implementação anterior usava `PRAGMA table_info(stock_movements)` — sintaxe
    # exclusiva do SQLite — que no PostgreSQL/Supabase quebrava a conferência de
    # recebimento de PO com 'syntax error at or near "PRAGMA"' (HTTP 500 em
    # POST /api/purchase-requests/{id}/status). A versão de core.schema usa
    # introspecção via information_schema no Postgres e só adiciona colunas
    # ausentes (no-op quando já existem).
    from core.schema import ensure_stock_movement_size_columns as _ensure_canonical
    _ensure_canonical(connection)


def create_delivery_service(
    connection,
    payload,
    *,
    client_ip='',
    authorize_action,
    resolve_actor_user_id,
    get_employee_by_id,
    get_epi_by_id,
    ensure_resource_company,
    get_employee_current_unit,
    actor_operational_unit_id,
    get_unit_stock,
    upsert_unit_stock,
    ensure_ficha_for_delivery,
):
    actor = authorize_action(connection, resolve_actor_user_id(), 'deliveries:create', int(payload['company_id']))
    # Antes de qualquer escrita: se esta entrega já foi registrada, devolve a
    # original. Reenvio da fila offline é reenvio da mesma entrega, não de uma
    # nova — e o operador precisa receber sucesso, não um erro sobre um item
    # que ele mesmo acabou de entregar.
    existing_id = find_delivery_by_idempotency_key(
        connection, company_id=int(payload['company_id']), key=payload.get('idempotency_key')
    )
    if existing_id is not None:
        return existing_id
    employee = get_employee_by_id(connection, int(payload['employee_id']))
    epi = get_epi_by_id(connection, int(payload['epi_id']))
    ensure_resource_company(actor, employee, 'Colaborador')
    ensure_resource_company(actor, epi, 'EPI')
    if str(employee['company_id']) != str(payload['company_id']) or str(epi['company_id']) != str(payload['company_id']):
        raise ValueError('Empresa incompatível para entrega.')
    # Empresa terceirizada/prestadora arquivada (ADR-0002 §10.4): bloqueia
    # novas entregas para colaboradores já vinculados a ela — o vínculo em si
    # não é desfeito, só novas operações contra a empresa arquivada.
    if employee.get('outsourced_company_id'):
        from core.archival import ensure_record_operational
        ensure_record_operational(
            connection, 'outsourced_companies', employee['outsourced_company_id'],
            'Empresa terceirizada', 'novas entregas',
        )
    # Regra NT 146/2015: após a aquisição (com CA válido), o uso/entrega do EPI
    # não fica proibido pelo vencimento do CA — passa a valer a validade do
    # produto informada pelo fabricante. Portanto, bloqueia-se a entrega quando a
    # validade do fabricante está vencida; o CA vencido NÃO bloqueia a entrega.
    if is_expired(epi.get('epi_validity_date')):
        raise ValueError(
            'Entrega bloqueada: validade do fabricante do EPI vencida em '
            f"{epi.get('epi_validity_date')}. Retire o item do estoque (NT 146/2015)."
        )
    quantity = int(payload['quantity'])
    if quantity != 1:
        raise ValueError('Entrega por leitura exige quantidade unitária (1).')
    stock_item_id = int(payload.get('stock_item_id') or 0)
    stock_qr_code = str(payload.get('stock_qr_code') or '').strip()
    if not stock_item_id or not stock_qr_code:
        raise ValueError('Leitura do código da unidade é obrigatória.')
    signature_data = str(payload.get('signature_data', '')).strip()
    signature_name = str(payload.get('signature_name') or '').strip()
    signature_comment = str(payload.get('signature_comment') or '').strip()
    signature_at = str(payload.get('signature_at') or '').strip()
    if signature_data:
        signature_name = signature_name or str(employee.get('name') or MSG_SIGNED_DIGITALLY)
        signature_at = signature_at or datetime.now(UTC).isoformat()
    else:
        signature_name = ''
        signature_comment = ''
        signature_at = ''
    if signature_data:
        signature_name = str(payload.get('signature_name') or actor.get('full_name') or 'Assinatura digital').strip() or 'Assinatura digital'
        signature_comment = str(payload.get('signature_comment') or '').strip()
        signature_at = str(payload.get('signature_at') or datetime.now(UTC).isoformat()).strip()
    employee_current_unit_id = get_employee_current_unit(connection, int(employee['id']))
    requested_unit_id = int(payload.get('unit_id') or 0)
    delivery_unit_id = int(requested_unit_id or employee_current_unit_id)
    if int(employee_current_unit_id) != int(delivery_unit_id):
        raise ValueError('Entrega só pode ocorrer na unidade operacional atual do colaborador.')
    actor_scope_unit_id = actor_operational_unit_id(connection, actor)
    if actor.get('role') in ('admin', 'user') and not actor_scope_unit_id:
        raise PermissionError('Seu perfil não possui unidade operacional ativa para registrar entregas.')
    if actor_scope_unit_id and int(delivery_unit_id) != int(actor_scope_unit_id):
        raise PermissionError('Seu perfil só pode registrar entregas na própria unidade operacional.')
    if epi.get('unit_id') and int(epi['unit_id']) != int(delivery_unit_id):
        raise ValueError('EPI vinculado a outra unidade operacional.')
    from modules.units.service import ensure_unit_operational
    ensure_unit_operational(connection, delivery_unit_id, 'entregas de EPI')
    from modules.employees.service import ensure_employee_operational
    ensure_employee_operational(connection, employee['id'], 'entregas de EPI')
    from modules.epis.service import ensure_epi_operational
    ensure_epi_operational(connection, epi['id'], 'entregas de EPI')
    stock_item = connection.execute(
        (
            'SELECT id, company_id, unit_id, epi_id, status, qr_code_value, glove_size, size, uniform_size '
            'FROM epi_stock_items '
            'WHERE id = ?'
        ),
        (stock_item_id,)
    ).fetchone()
    if not stock_item:
        raise ValueError('Unidade etiquetada não encontrada.')
    if str(stock_item['company_id']) != str(payload['company_id']) or int(stock_item['unit_id']) != int(delivery_unit_id):
        raise ValueError('Unidade etiquetada incompatível com empresa/unidade da entrega.')
    if int(stock_item['epi_id']) != int(payload['epi_id']):
        raise ValueError('Código lido não corresponde ao EPI selecionado.')
    if str(stock_item['qr_code_value']).strip().lower() != stock_qr_code.lower():
        raise ValueError('Código lido não confere com a unidade informada.')
    if str(stock_item['status']) != 'in_stock':
        raise ValueError('Entrega bloqueada: item já baixado, entregue, descartado ou inválido.')
    stock_row = get_unit_stock(connection, int(payload['company_id']), delivery_unit_id, int(epi['id']))
    current_stock = int((stock_row or {}).get('quantity') or 0)
    if current_stock < quantity:
        raise ValueError('Estoque insuficiente para realizar a entrega.')
    claim_cursor = connection.execute(
        (
            "UPDATE epi_stock_items "
            "SET status = 'delivering', updated_at = ? "
            "WHERE id = ? AND status = 'in_stock'"
        ),
        (datetime.now(UTC).isoformat(), stock_item_id)
    )
    if int(getattr(claim_cursor, 'rowcount', 0) or 0) != 1:
        raise ValueError('Entrega bloqueada: item já foi processado em outra operação. Atualize e tente novamente.')
    # Snapshot histórico do vínculo com empresa terceirizada/prestadora
    # (ADR-0002, PR 4) — congelado agora, nunca recalculado depois. Vazio
    # para colaborador CLT (exceto tipo_vinculo, sempre conhecido).
    from modules.outsourced_companies.service import (
        outsourced_companies_ready, resolve_delivery_outsourced_snapshot,
    )
    if outsourced_companies_ready(connection):
        snapshot = resolve_delivery_outsourced_snapshot(connection, employee, payload['company_id'])
    else:
        snapshot = {
            'snapshot_tipo_vinculo': str(employee.get('tipo_vinculo') or 'CLT').strip() or 'CLT',
            'snapshot_outsourced_company_name': '', 'snapshot_outsourced_company_cnpj': '',
            'snapshot_contracting_company_id': None, 'snapshot_contract_ref': '',
            'snapshot_epi_responsibility': '',
        }
    cursor = connection.execute(
        (
            'INSERT INTO deliveries (company_id, employee_id, epi_id, quantity, quantity_label, sector, role_name, '
            'delivery_date, next_replacement_date, notes, signature_name, signature_ip, signature_at, signature_data, signature_comment, '
            'glove_size, size, uniform_size, idempotency_key, snapshot_tipo_vinculo, '
            'snapshot_outsourced_company_name, snapshot_outsourced_company_cnpj, '
            'snapshot_contracting_company_id, snapshot_contract_ref, snapshot_epi_responsibility) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        ),
        (
            payload['company_id'], payload['employee_id'], payload['epi_id'], quantity,
            str(epi.get('unit_measure') or 'unidade'), payload['sector'], payload['role_name'], payload['delivery_date'],
            payload['next_replacement_date'], payload.get('notes', ''), signature_name,
            str(client_ip or ''), signature_at, signature_data, signature_comment,
            str(stock_item.get('glove_size') or 'N/A'), str(stock_item.get('size') or 'N/A'), str(stock_item.get('uniform_size') or 'N/A'),
            str(payload.get('idempotency_key') or '').strip(),
            snapshot['snapshot_tipo_vinculo'], snapshot['snapshot_outsourced_company_name'],
            snapshot['snapshot_outsourced_company_cnpj'], snapshot['snapshot_contracting_company_id'],
            snapshot['snapshot_contract_ref'], snapshot['snapshot_epi_responsibility'],
        )
    )
    new_stock = current_stock - quantity
    upsert_unit_stock(connection, int(payload['company_id']), delivery_unit_id, int(epi['id']), new_stock)
    ensure_stock_movement_size_columns(connection)
    stock_cursor = connection.execute(
        (
            'INSERT INTO stock_movements ('
            'company_id, unit_id, epi_id, movement_type, quantity, previous_stock, new_stock, '
            'source_type, source_id, notes, actor_user_id, actor_name, created_at, glove_size, size, uniform_size'
            ') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        ),
        (
            payload['company_id'], delivery_unit_id, epi['id'], 'out', quantity, current_stock, new_stock,
            'delivery', int(cursor.lastrowid), str(payload.get('notes', '')).strip(),
            actor['id'], actor['full_name'], datetime.now(UTC).isoformat(),
            str(stock_item.get('glove_size') or 'N/A'), str(stock_item.get('size') or 'N/A'), str(stock_item.get('uniform_size') or 'N/A')
        )
    )
    # Item 4: gera o token opaco da entrega (QR da entrega). O QR do colaborador
    # (employee_portal_links) segue válido para identificação institucional.
    handover_token = generate_handover_token()
    connection.execute(
        'UPDATE deliveries SET unit_id = ?, stock_movement_id = ?, handover_token = ? WHERE id = ?',
        (delivery_unit_id, int(stock_cursor.lastrowid), handover_token, int(cursor.lastrowid))
    )
    connection.execute(
        "UPDATE epi_stock_items SET status = 'delivered', delivery_id = ?, updated_at = ? WHERE id = ?",
        (int(cursor.lastrowid), datetime.now(UTC).isoformat(), stock_item_id)
    )
    ensure_ficha_for_delivery(
        connection,
        {
            'id': int(cursor.lastrowid),
            'company_id': int(payload['company_id']),
            'employee_id': int(payload['employee_id']),
            'unit_id': delivery_unit_id,
            'epi_id': int(payload['epi_id']),
            'quantity': quantity,
            'delivery_date': payload['delivery_date'],
            'schedule_type': employee.get('schedule_type'),
            'signature_name': signature_name,
            'signature_data': signature_data,
            'signature_ip': str(client_ip or ''),
            'signature_at': signature_at,
            'signature_comment': signature_comment
        }
    )
    if signature_data:
        # A assinatura passa a existir também como evidência: a coluna
        # continua sendo a fonte do conteúdo, e aqui fica o registro
        # auditável de quem assinou, quando e de onde.
        record_evidence(
            connection,
            company_id=int(payload['company_id']),
            delivery_id=int(cursor.lastrowid),
            kind=SIGNATURE_HANDWRITTEN,
            content=signature_data,
            content_ref='deliveries.signature_data',
            provider='app',
            actor_user_id=int(actor['id']),
            actor_name=str(actor.get('full_name') or ''),
            subject_name=signature_name,
            client_ip=str(client_ip or ''),
            notes=signature_comment,
            collected_at=signature_at,
        )
    if str(payload.get('request_id', '')).strip():
        consume_request_reservation(
            connection,
            request_id=int(payload['request_id']),
            company_id=int(payload['company_id']),
            unit_id=delivery_unit_id,
            epi_id=int(epi['id']),
            quantity=quantity,
            delivery_id=int(cursor.lastrowid),
        )
        connection.execute(
            "UPDATE epi_requests SET status = 'entregue', delivery_id = ?, last_updated_at = ? WHERE id = ?",
            (int(cursor.lastrowid), datetime.now(UTC).isoformat(), int(payload['request_id']))
        )
    connection.commit()
    return int(cursor.lastrowid)


def find_delivery_by_idempotency_key(connection, *, company_id, key):
    """Entrega já registrada com esta chave nesta empresa, se houver.

    Escopada por empresa de propósito: a chave é gerada pelo cliente, e uma
    colisão entre tenants não pode fazer uma empresa enxergar a entrega de
    outra. Chave vazia significa "sem idempotência" — todo o histórico anterior
    a esta coluna está assim, e essas entregas não podem colidir entre si.
    """
    from epi_backend.db import table_columns

    normalized = str(key or '').strip()
    if not normalized:
        return None
    if 'idempotency_key' not in table_columns(connection, 'deliveries'):
        return None
    row = connection.execute(
        'SELECT id FROM deliveries WHERE company_id = ? AND idempotency_key = ? LIMIT 1',
        (int(company_id), normalized),
    ).fetchone()
    if not row:
        return None
    return int(row['id'] if hasattr(row, 'keys') else row[0])


def consume_request_reservation(
    connection, *, request_id, company_id, unit_id, epi_id, quantity, delivery_id
):
    """Abate da reserva o que acabou de sair fisicamente.

    Sem isto a reserva ficava ``active`` para sempre: o estoque físico caía na
    entrega e a promessa continuava de pé, então **a mesma peça era subtraída
    duas vezes** do saldo livre. Depois de algumas entregas a unidade parecia
    sem estoque tendo prateleira cheia.

    Roda na mesma transação da baixa de propósito: reserva consumida sem
    entrega (ou o contrário) deixa o saldo errado, e é justamente o par que
    precisa ser indivisível.

    Silencioso quando não há reserva — entrega direta de estoque, sem
    solicitação prévia, é caminho legítimo e não tem o que abater.
    """
    from modules.stock.reservations import (
        ReservationNotActive,
        consume_reservation,
        reservation_for_request,
        reservations_ready,
    )

    if not reservations_ready(connection):
        return None
    reservation = reservation_for_request(connection, request_id)
    if not reservation:
        return None
    # A reserva pertence a uma unidade e a um EPI. Abater a reserva errada
    # devolveria saldo livre a quem não entregou nada — pior que não abater.
    if (
        int(reservation.get('company_id') or 0) != int(company_id)
        or int(reservation.get('unit_id') or 0) != int(unit_id)
        or int(reservation.get('epi_id') or 0) != int(epi_id)
    ):
        return None
    try:
        return consume_reservation(
            connection, int(reservation['id']), quantity=int(quantity), delivery_id=delivery_id
        )
    except ReservationNotActive:
        # Corrida com outra entrega da mesma solicitação: a peça já saiu e já
        # foi abatida. Recusar a entrega aqui seria pior — ela é real.
        return None


def _safe_split_name(full_name):
    """Divide o nome completo em (primeiro, sobrenome) para a projeção segura.
    Não expõe o nome inteiro concatenado com outros dados sensíveis."""
    parts = str(full_name or '').strip().split()
    if not parts:
        return '', ''
    return parts[0], (' '.join(parts[1:]) if len(parts) > 1 else '')


def lookup_delivery_by_handover_token(connection, token, actor):
    """Projeção SEGURA da entrega a partir do token opaco (item 4).

    Retorna nome+sobrenome, matrícula, EPI, tamanho, lote, solicitação e
    unidade — NUNCA CPF ou dado pessoal sensível. Respeita empresa do ator
    (multi-tenant); master vê todas as empresas.
    """
    token = str(token or '').strip()
    if not token:
        raise ValueError('Código da entrega é obrigatório.')
    row = connection.execute(
        'SELECT d.id, d.company_id, d.unit_id, d.epi_id, d.employee_id, d.quantity, d.quantity_label, '
        'd.delivery_date, d.glove_size, d.size, d.uniform_size, '
        'd.signature_at, d.handover_confirmed_at, d.handover_confirmed_name, '
        'e.name AS employee_name, e.employee_id_code, e.sector, e.role_name, '
        'epis.name AS epi_name, epis.purchase_code, epis.ca, '
        'esi.lot_code, esi.qr_code_value AS stock_qr, esi.id AS stock_item_id, '
        'u.name AS unit_name '
        'FROM deliveries d '
        'JOIN employees e ON e.id = d.employee_id '
        'JOIN epis ON epis.id = d.epi_id '
        'LEFT JOIN units u ON u.id = d.unit_id '
        'LEFT JOIN epi_stock_items esi ON esi.delivery_id = d.id '
        'WHERE d.handover_token = ?',
        (token,)
    ).fetchone()
    if not row:
        raise ValueError('Entrega não encontrada para o código informado.')
    row = row_to_dict(row)
    if actor and actor.get('role') != 'master_admin' and str(row.get('company_id')) != str(actor.get('company_id')):
        raise PermissionError('Entrega de outra empresa.')
    first, last = _safe_split_name(row.get('employee_name'))
    req = connection.execute(
        'SELECT id, status, quantity FROM epi_requests WHERE delivery_id = ? ORDER BY id DESC LIMIT 1',
        (int(row['id']),)
    ).fetchone()
    req = row_to_dict(req) if req else None
    return {
        'delivery_id': int(row['id']),
        'company_id': int(row['company_id']),
        'unit_id': int(row.get('unit_id') or 0),
        'unit_name': row.get('unit_name') or '',
        'employee_first_name': first,
        'employee_last_name': last,
        'employee_registration': row.get('employee_id_code') or '',
        'sector': row.get('sector') or '',
        'role_name': row.get('role_name') or '',
        'epi_name': row.get('epi_name') or '',
        'epi_code': row.get('purchase_code') or '',
        'ca': row.get('ca') or '',
        'glove_size': row.get('glove_size') or '',
        'size': row.get('size') or '',
        'uniform_size': row.get('uniform_size') or '',
        'lot_code': row.get('lot_code') or '',
        'stock_qr': row.get('stock_qr') or '',
        'quantity': int(row.get('quantity') or 0),
        'quantity_label': row.get('quantity_label') or '',
        'delivery_date': row.get('delivery_date') or '',
        'request_id': int(req['id']) if req else 0,
        'request_status': (req or {}).get('status') or '',
        'already_confirmed': bool(str(row.get('handover_confirmed_at') or '').strip()),
        'confirmed_at': row.get('handover_confirmed_at') or '',
        'confirmed_name': row.get('handover_confirmed_name') or '',
        'signed': bool(str(row.get('signature_at') or '').strip()),
    }


def confirm_delivery_handover(connection, token, actor, *, signature_name='', signature_data='',
                              signature_comment='', client_ip='', now=None):
    """Fecha o ciclo da entrega pelo QR da entrega (item 4). IDEMPOTENTE: uma
    segunda confirmação não duplica entrega/movimentação. Marca
    handover_confirmed_*, assina a entrega se ainda não assinada e garante a
    solicitação vinculada como 'entregue' — o portal passa a exibir 'EPI
    entregue'."""
    token = str(token or '').strip()
    if not token:
        raise ValueError('Código da entrega é obrigatório.')
    now = now or datetime.now(UTC).isoformat()
    row = connection.execute(
        'SELECT id, company_id, unit_id, signature_at, handover_confirmed_at '
        'FROM deliveries WHERE handover_token = ?',
        (token,)
    ).fetchone()
    if not row:
        raise ValueError('Entrega não encontrada para o código informado.')
    row = row_to_dict(row)
    if actor and actor.get('role') != 'master_admin' and str(row.get('company_id')) != str(actor.get('company_id')):
        raise PermissionError('Entrega de outra empresa.')
    delivery_id = int(row['id'])
    if str(row.get('handover_confirmed_at') or '').strip():
        return {'delivery_id': delivery_id, 'confirmed': True, 'already_confirmed': True,
                'confirmed_at': row.get('handover_confirmed_at')}
    confirmer = str(signature_name or (actor.get('full_name') if actor else '') or '').strip()
    connection.execute(
        'UPDATE deliveries SET handover_confirmed_at = ?, handover_confirmed_by = ?, handover_confirmed_name = ? WHERE id = ?',
        (now, int(actor['id']) if actor else None, confirmer, delivery_id)
    )
    signature_data = str(signature_data or '').strip()
    if signature_data and not str(row.get('signature_at') or '').strip():
        connection.execute(
            'UPDATE deliveries SET signature_name = ?, signature_data = ?, signature_ip = ?, '
            'signature_at = ?, signature_comment = ? WHERE id = ?',
            (confirmer or MSG_SIGNED_DIGITALLY, signature_data, str(client_ip or ''), now,
             str(signature_comment or ''), delivery_id)
        )
    # A conferência pelo QR é uma segunda evidência da mesma entrega — o motivo
    # de existir uma tabela em vez de mais colunas: assinatura no ato e
    # conferência depois coexistem, cada uma com seu momento e seu responsável.
    record_evidence(
        connection,
        company_id=int(row['company_id']),
        delivery_id=delivery_id,
        kind=QR_HANDOVER,
        content=signature_data or token,
        content_ref='deliveries.handover_token',
        provider='qr',
        actor_user_id=int(actor['id']) if actor else None,
        actor_name=str((actor or {}).get('full_name') or ''),
        subject_name=confirmer,
        client_ip=str(client_ip or ''),
        notes=str(signature_comment or ''),
        collected_at=now,
    )
    connection.execute(
        "UPDATE epi_requests SET status = 'entregue', last_updated_at = ? "
        "WHERE delivery_id = ? AND LOWER(COALESCE(status, '')) <> 'entregue'",
        (now, delivery_id)
    )
    connection.commit()
    return {'delivery_id': delivery_id, 'confirmed': True, 'already_confirmed': False, 'confirmed_at': now}


def fetch_deliveries(connection, actor=None, where_clause='', params=()):
    from epi_backend.db import table_columns
    from modules.legal_entities.service import employee_legal_entity_sql
    # Rastreabilidade jurídica: QR → Entrega → Colaborador → CNPJ → Empresa.
    # A entrega não guarda o CNPJ redundantemente; ele é derivado do vínculo do
    # colaborador, mantendo uma única fonte de verdade.
    legal_entity_select, legal_entity_join = employee_legal_entity_sql(connection)
    # Snapshot histórico do vínculo com empresa terceirizada/prestadora
    # (ADR-0002) — ao contrário do CNPJ acima, é gravado direto na entrega,
    # porque é congelado no momento da entrega e não deve mudar se o
    # cadastro vivo da empresa/contrato mudar depois (ver PR 4).
    snapshot_select = (
        ', deliveries.snapshot_tipo_vinculo, deliveries.snapshot_outsourced_company_name, '
        'deliveries.snapshot_outsourced_company_cnpj, deliveries.snapshot_contract_ref, '
        'deliveries.snapshot_epi_responsibility'
    ) if 'snapshot_tipo_vinculo' in table_columns(connection, 'deliveries') else ''
    clauses = []
    query_params = list(params)
    if actor and actor['role'] != 'master_admin':
        clauses.append('deliveries.company_id = ?')
        query_params.append(actor['company_id'])
    if where_clause:
        clean = where_clause.strip()
        clauses.append(clean[6:] if clean.upper().startswith('WHERE ') else clean)
    # Entrega revertida por rollback lógico (#211) sai de toda leitura
    # operacional: continua no banco para auditoria, mas não conta como posse
    # ativa de EPI nem pode ser devolvida.
    from modules.deliveries.visibility import active_delivery_sql
    reversal = active_delivery_sql(connection, 'deliveries', prefix='')
    if reversal:
        clauses.append(reversal)
    final_where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
    rows = connection.execute(
        f'''SELECT deliveries.id, deliveries.company_id, deliveries.employee_id, deliveries.epi_id, deliveries.quantity, deliveries.quantity_label, deliveries.sector, deliveries.role_name, deliveries.delivery_date, deliveries.next_replacement_date, deliveries.notes, deliveries.signature_name, deliveries.signature_data, deliveries.signature_at, deliveries.signature_comment, deliveries.unit_id, deliveries.stock_movement_id, deliveries.glove_size, deliveries.size, deliveries.uniform_size, deliveries.returned_date, deliveries.returned_condition, deliveries.returned_notes, deliveries.return_movement_id,
                          companies.name AS company_name, companies.cnpj AS company_cnpj, companies.logo_type,
                          employees.employee_id_code, employees.name AS employee_name, employees.schedule_type, employees.tipo_vinculo,
                          units.name AS unit_name, units.unit_type, epis.name AS epi_name, epis.purchase_code, epis.ca, epis.unit_measure, epis.epi_validity_date, epis.manufacture_date, epis.qr_code_value,
                          esi.glove_size AS stock_item_glove_size, esi.size AS stock_item_size, esi.uniform_size AS stock_item_uniform_size{legal_entity_select}{snapshot_select},
                          CASE WHEN COALESCE(deliveries.returned_date, '') != '' THEN 0
                               WHEN EXISTS (
                                   SELECT 1 FROM epi_ficha_items fi
                                   JOIN epi_ficha_periods fp ON fp.id = fi.ficha_period_id
                                   WHERE fi.delivery_id = deliveries.id
                                     AND fp.status = 'closed'
                               ) THEN 0
                               WHEN NOT EXISTS (
                                   SELECT 1 FROM epi_ficha_items fi WHERE fi.delivery_id = deliveries.id
                               ) AND EXISTS (
                                   SELECT 1 FROM epi_ficha_periods fp
                                   WHERE fp.employee_id = deliveries.employee_id
                                     AND fp.period_start <= deliveries.delivery_date
                                     AND fp.period_end   >= deliveries.delivery_date
                                     AND fp.status = 'closed'
                               ) THEN 0
                               ELSE 1 END AS devolution_available
                   FROM deliveries
                   JOIN companies ON companies.id = deliveries.company_id
                   JOIN employees ON employees.id = deliveries.employee_id
                   LEFT JOIN units ON units.id = deliveries.unit_id
                   JOIN epis ON epis.id = deliveries.epi_id
                   LEFT JOIN epi_stock_items esi ON esi.delivery_id = deliveries.id AND esi.id = (SELECT MAX(esi_latest.id) FROM epi_stock_items esi_latest WHERE esi_latest.delivery_id = deliveries.id){legal_entity_join}
                   {final_where}
                   ORDER BY deliveries.delivery_date DESC, deliveries.id DESC''',
        tuple(query_params),
    ).fetchall()
    items = []
    for row in rows:
        item = row_to_dict(row)
        apply_effective_size_fields(item, item, item, fallback_prefix='stock_item_')
        items.append(item)
    return items
