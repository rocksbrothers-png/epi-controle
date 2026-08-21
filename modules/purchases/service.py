"""Serviços do domínio de compras e requisições de EPI."""

from datetime import datetime, timedelta, timezone

from core.auth import ensure_permission, ensure_resource_company
from core.permissions import PERM_PO_APPROVE, PERM_PURCHASE_REQUESTS_UPDATE
from modules.units.service import get_unit_by_id
from modules.epis.validity import is_expired
from core.roles import normalize_role_name
from epi_backend.db import row_to_dict
from epi_backend.http_utils import structured_log
from epi_backend.purchase_workflow import (
    PURCHASE_STATUS_LABELS as PURCHASE_WORKFLOW_STATUS_LABELS,
    PURCHASE_APPROVAL_REJECTION_REASONS,
    latest_requester_review_origin,
    normalize_purchase_item_approval_decisions,
    resolve_purchase_transition,
    serialize_purchase_event_comment,
    validate_purchase_transition_payload,
)
from epi_backend.purchase_order_workflow import (
    assert_approval_allowed,
    assert_receive_allowed,
    assert_resubmit_allowed,
    assert_review_allowed,
    resolve_approval_outcome,
)
from core.permissions import PERM_FINANCE_VIEW
from modules.stock.service import (
    STATUS_CRITICAL,
    classify_unit_epi_stock,
    fetch_epi_size_balance,
    get_unit_stock,
    upsert_unit_stock,
    next_company_qr_sequence,
    build_stock_item_qr,
)

UTC = timezone.utc

PURCHASE_FUNCTION_TYPES = {'buyer', 'approver'}
PURCHASE_FUNCTION_LABELS = {'buyer': 'Comprador', 'approver': 'Aprovador'}


def normalize_purchase_function_type(value):
    normalized = normalize_role_name(value)
    if normalized not in PURCHASE_FUNCTION_TYPES:
        raise ValueError('Função de compras deve ser comprador ou aprovador.')
    return normalized


def get_actor_purchase_unit_scope(connection, actor):
    """Retorna unit_ids para vínculos de Compras via purchase_role_unit_links.

    ``None`` = ator fora do universo de Compras (não é `None` == "sem
    restrição" para Comprador/Aprovador). Quem decide se `None`/lista vazia
    vira "toda a empresa" ou "nada" é o chamador — ver
    ``actor_has_no_purchase_unit_scope`` para Comprador/Aprovador, cujo
    escopo precisa ser fail-closed (vínculo ausente = zero acesso).

    **Só Comprador e Aprovador têm carteira.** Antes a lista de papéis incluía
    `admin`, `registry_admin` e `general_admin`, e consultava com
    `role_type = 'buyer'` para os três, porque nenhum deles é uma função de
    compras. O efeito era silencioso e ao contrário do desejado: um
    Administrador Geral que por acaso tivesse vínculo de comprador passava a
    ser RESTRINGIDO àquelas Unidades, embora a regra seja que ele enxerga a
    empresa inteira e escolhe a Unidade no seletor. Perfil travado, por sua
    vez, já é limitado por `actor_operational_unit_id` — carteira ali seria
    uma segunda fonte para a mesma decisão.
    """
    if not actor:
        return None
    actor_role = actor.get('role')
    linked_employee_id = actor.get('linked_employee_id')
    if not linked_employee_id or actor_role not in PURCHASE_FUNCTION_TYPES:
        return None
    function_rows = connection.execute(
        'SELECT unit_id FROM purchase_role_unit_links WHERE employee_id = ? AND role_type = ?',
        (int(linked_employee_id), actor_role)
    ).fetchall()
    unit_ids = [int(r['unit_id']) for r in function_rows]
    return sorted(set(unit_ids)) if unit_ids else None


def resolve_purchase_scope(connection, actor, requested_unit_id=None, *, denial_message=None):
    """Escopo de Compras do ator — fachada com a carteira já ligada.

    Existe para que nenhum chamador precise lembrar de injetar
    `get_actor_purchase_unit_scope`. Esquecer a injeção seria fail-OPEN
    (carteira `None` = sem restrição), então a injeção não pode ser
    responsabilidade de quem chama.
    """
    from core.repository import resolve_purchase_unit_scope
    return resolve_purchase_unit_scope(
        connection, actor, requested_unit_id,
        purchase_units_loader=get_actor_purchase_unit_scope,
        denial_message=denial_message,
    )


def purchase_listing_scope(
    connection, actor, requested_unit_id=None, *, actor_operational_unit_id, purchase_units_loader,
):
    """Escopo de uma LISTAGEM de Compras. `None` significa "lista vazia".

    Substitui o par `scope_unit_id` + `purchase_scope_units` que cada rota
    montava à mão, junto das duas guardas de fail-closed. Montar isso sete
    vezes é como as três variantes de escopo apareceram no backend.

    Devolve `None` — e o chamador responde `200 {'items': []}` — nas duas
    situações que **não são erro**, apenas ausência de dado:

    - perfil travado sem unidade operacional ativa;
    - Comprador/Aprovador sem nenhuma Unidade na carteira.

    O que É erro continua subindo, e com o código certo: Unidade fora da
    carteira é `PermissionError` (403) e identificador inválido ou de outro
    tenant é `ValueError` (400). Engolir esses dois em lista vazia esconderia
    de quem pediu a diferença entre "não há nada" e "você não pode".

    O resultado alimenta `fetch_*(company_id, escopo.unit_id,
    escopo.allowed_unit_ids)` sem tradução: `unit_id` preenchido recorta numa
    Unidade; `allowed_unit_ids` recorta na carteira ("Todas as minhas
    Unidades"); os dois nulos são a visão corporativa.

    As duas dependências entram por parâmetro OBRIGATÓRIO. Não é cerimônia:
    são as fronteiras que as rotas expõem e os testes de fail-closed
    substituem para simular ator sem unidade e carteira vazia. Resolvê-las
    por dentro esconderia essas fronteiras e deixaria os testes passando sem
    exercitar nada. Obrigatórias porque esquecer uma delas precisa ser
    `TypeError`, nunca um escopo silenciosamente mais amplo.
    """
    if actor.get('role') in ('admin', 'user') and not actor_operational_unit_id(connection, actor):
        return None
    from core.repository import resolve_purchase_unit_scope
    escopo = resolve_purchase_unit_scope(
        connection, actor, requested_unit_id,
        purchase_units_loader=purchase_units_loader,
        operational_unit_loader=actor_operational_unit_id,
    )
    return None if escopo.blocks_everything else escopo


def narrow_purchase_unit_to_selection(scope_unit_id, selected_unit_id, purchase_scope_units):
    """Unidade que uma consulta de Compras deve usar, dada a seleção do usuário.

    `scope_unit_id` é o que o ator impõe (perfil travado tem uma; os demais,
    `None`). `selected_unit_id` é o que ele escolheu no seletor.

    A seleção só prevalece se estiver na carteira. Quem valida a Unidade
    antes daqui (`resolve_unit_scope`) confere existência e tenant, mas **não
    conhece carteira** — sem esta função, um Comprador vinculado a A+B pediria
    `unit_id=C` e receberia números de C: o seletor esconde C, a API não.

    Fora da carteira o pedido é DESCARTADO, não recusado — mesmo tratamento
    que o perfil travado já recebe para um `unit_id` que não é o dele. Recusar
    aqui transformaria cliente desatualizado em erro; descartar mantém a
    autorização no servidor.

    `purchase_scope_units` a `None` significa "sem carteira, sem restrição" —
    e tupla/lista vazia significa "não enxerga nada". A distinção é por
    `is None`, nunca por truthiness.
    """
    if selected_unit_id in (None, '', 0):
        return scope_unit_id
    selecionada = int(selected_unit_id)
    if purchase_scope_units is None:
        return selecionada
    if selecionada in {int(u) for u in purchase_scope_units}:
        return selecionada
    return scope_unit_id


def build_purchase_scope_payload(connection, actor, escopo, *, fetch_units_fn):
    """Contrato de escopo + lista do seletor, para QUALQUER frontend.

    O cliente desenha o seletor a partir daqui e devolve a escolha em
    `unit_id`. Ele não filtra, não deduz e não reconstrói a lista — hoje o
    Web Legado monta as opções de Unidade a partir do bootstrap e as recorta
    no navegador, e o Flutter nem recorta.

    `available_units` já vem recortado pelo direito do ator:
    Comprador/Aprovador recebem só a carteira; perfil travado, só a própria
    Unidade; os demais, as Unidades do tenant.
    """
    unidades = fetch_units_fn(connection, actor)
    empresa = actor.get('company_id')
    disponiveis = []
    for u in unidades:
        uid = u.get('id')
        if uid is None:
            continue
        uid = int(uid)
        if not escopo.permits(uid):
            continue
        # `master_admin` não tem empresa própria; para ele o recorte de tenant
        # é feito por quem escolheu a empresa, não aqui.
        if empresa and str(u.get('company_id') or '') != str(empresa):
            continue
        disponiveis.append({
            'id': uid,
            'name': str(u.get('name') or ''),
            'legal_entity_id': u.get('legal_entity_id'),
        })
    return {
        'scope': {
            'company_id': int(empresa) if empresa else None,
            'unit_id': escopo.unit_id,
            'unit_scope_source': escopo.source,
            'locked': escopo.locked,
        },
        'available_units': disponiveis,
        'allows_all_units': escopo.allows_all_units,
    }


def actor_has_no_purchase_unit_scope(actor, scope_unit_id, purchase_scope_units):
    """True quando o ator é Comprador/Aprovador sem nenhuma unidade vinculada.

    Comprador e Aprovador só enxergam as unidades de
    ``purchase_role_unit_links`` (docs/PAPEIS_E_ATRIBUICOES.md #6/#7): sem
    vínculo cadastrado, a listagem deve devolver vazio — nunca a empresa
    inteira. Antes desta correção, vários endpoints de listagem tratavam
    "sem vínculo" como "sem restrição" (o mesmo antipadrão do escopo de CNPJ
    do Administrador Local), embora a AÇÃO sobre um registro específico
    (aprovar/rejeitar) já bloqueasse corretamente
    (``ensure_purchase_request_action_scope``).
    """
    return actor.get('role') in ('buyer', 'approver') and not scope_unit_id and not purchase_scope_units


def actor_company_id_or_query(connection, actor, query):
    if actor.get('role') != 'master_admin':
        return int(actor['company_id'])
    requested = str(query.get('company_id', [''])[0] or '').strip()
    if requested:
        return int(requested)
    first_company = connection.execute('SELECT id FROM companies ORDER BY id ASC LIMIT 1').fetchone()
    if not first_company:
        raise ValueError('Nenhuma empresa cadastrada para consulta.')
    return int(first_company['id'])


def require_purchase_function_admin(actor):
    if actor.get('role') not in ('general_admin', 'registry_admin'):
        raise PermissionError('Somente Administrador Geral ou Administrador de Registro pode gerenciar funções de compras.')


def fetch_purchase_function_links(connection, company_id):
    """Retorna vínculos de função de compra (comprador/aprovador) por unidade.

    Inclui flag has_system_user indicando se o colaborador possui conta de usuário
    ativa com o perfil correspondente.
    """
    rows = connection.execute(
        'SELECT prul.*, employees.name AS employee_name, employees.employee_id_code, '
        'employees.sector AS employee_sector, employees.role_name AS employee_role, '
        'units.name AS unit_name '
        'FROM purchase_role_unit_links prul '
        'JOIN employees ON employees.id = prul.employee_id '
        'JOIN units ON units.id = prul.unit_id '
        'WHERE prul.company_id = ? '
        'ORDER BY employees.name, prul.role_type, units.name',
        (int(company_id),)
    ).fetchall()
    items = []
    for row in rows:
        item = row_to_dict(row)
        item['role_label'] = PURCHASE_FUNCTION_LABELS.get(item.get('role_type'), item.get('role_type'))
        user_check = connection.execute(
            'SELECT id, username FROM users WHERE linked_employee_id = ? AND role = ? AND active = 1 LIMIT 1',
            (item['employee_id'], item.get('role_type'))
        ).fetchone()
        item['has_system_user'] = bool(user_check)
        item['system_user_login'] = str(user_check['username']) if user_check else ''
        items.append(item)
    return items


def fetch_purchase_demands(connection, company_id, scope_unit_id=None):
    """Retorna demandas pendentes para virar requisição de compra.

    Regra de negócio:
      - Solicitações de colaboradores entram na aba "Aprovações" primeiro (status
        'solicitado'/'prorrogado'); só DEPOIS de aprovadas pelo Administrador Local
        (status 'aprovado') é que viram demanda de compra. Por isso aqui filtramos
        apenas 'aprovado' — antes incluía 'solicitado', fazendo a mesma solicitação
        aparecer simultaneamente em Aprovações e em Demandas.
      - EPIs no nível mínimo ou abaixo entram direto como demanda (ver `<=` abaixo).
    """
    demands = []
    req_clauses = ["r.status = 'aprovado'"]
    req_params = []
    if company_id is not None:
        req_clauses.insert(0, 'r.company_id = ?')
        req_params.append(company_id)
    if scope_unit_id:
        req_clauses.append('r.unit_id = ?')
        req_params.append(int(scope_unit_id))
    req_rows = connection.execute(
        f'SELECT r.id, r.company_id, r.unit_id, r.employee_id, r.epi_id, r.quantity, '
        f'r.glove_size, r.size, r.uniform_size, r.requested_at, r.status, '
        f'emp.name AS employee_name, emp.sector AS employee_sector, emp.role_name AS employee_role, '
        f'ep.name AS epi_name, ep.ca, ep.unit_measure, ep.manufacturer, ep.supplier_company AS supplier, '
        f'u.name AS unit_name, c.name AS company_name '
        f'FROM epi_requests r '
        f'JOIN employees emp ON emp.id = r.employee_id '
        f'JOIN epis ep ON ep.id = r.epi_id '
        f'JOIN units u ON u.id = r.unit_id '
        f'JOIN companies c ON c.id = r.company_id '
        f"WHERE {' AND '.join(req_clauses)} "
        f'ORDER BY r.status DESC, r.requested_at ASC',
        tuple(req_params)
    ).fetchall()
    for row in req_rows:
        d = dict(row)
        d['demand_type'] = 'employee_request'
        demands.append(d)
    # A REGRA DE MÍNIMO SAIU DO SQL (#271).
    #
    # Aqui havia `ues.quantity <= ep.minimum_stock` — saldo da Unidade contra o
    # mínimo da EMPRESA, copiado para SQL de propósito para "coincidir com o
    # card do dashboard". A regra errada foi propagada deliberadamente, e o
    # mínimo não era só o gatilho: ele também dimensiona a reposição
    # (`quantity_requested` e `suggested_quantity`). Trocar só o operando do
    # WHERE deixaria a demanda sendo disparada por um número e dimensionada por
    # outro.
    #
    # A consulta agora traz os CANDIDATOS da Unidade e a decisão é do
    # classificador único, em Python. Um LEFT JOIN com COALESCE resolveria em
    # SQL, mas reescreveria a cadeia de fallback (unidade -> empresa -> default)
    # num segundo lugar — exatamente a duplicação que esta fatia elimina.
    # O custo é aceitável: o recorte já é o catálogo com saldo naquela Unidade.
    stock_clauses = ['ep.active = 1']
    stock_params = []
    if company_id is not None:
        stock_clauses.insert(0, 'ues.company_id = ?')
        stock_params.append(company_id)
    if scope_unit_id:
        stock_clauses.append('ues.unit_id = ?')
        stock_params.append(int(scope_unit_id))
    stock_rows = connection.execute(
        # `ep.minimum_stock` saiu do SELECT junto com o ORDER BY: era morto por
        # sobrescrita (`d['minimum_stock']` recebe o mínimo efetivo da Unidade
        # logo abaixo) e só servia de convite para alguém voltar a lê-lo.
        f'SELECT ues.company_id, ues.unit_id, ues.epi_id, ues.quantity AS current_stock, '
        f'ep.name AS epi_name, ep.ca, ep.unit_measure, ep.manufacturer, ep.supplier_company AS supplier, '
        f'ep.sector AS employee_sector, ep.glove_size, ep.size, ep.uniform_size, '
        f'u.name AS unit_name, c.name AS company_name '
        f'FROM unit_epi_stock ues '
        f'JOIN epis ep ON ep.id = ues.epi_id '
        f'JOIN units u ON u.id = ues.unit_id '
        f'JOIN companies c ON c.id = ues.company_id '
        f"WHERE {' AND '.join(stock_clauses)} "
        # A PRIORIDADE TAMBÉM SAIU DO SQL (P5).
        #
        # Aqui havia `ORDER BY (ep.minimum_stock - ues.quantity) DESC`: o
        # tamanho do buraco medido contra o mínimo da EMPRESA. Era o último
        # operando de mínimo corporativo sobrevivente neste caminho — a #271
        # tirou o irmão dele do WHERE pelo mesmo motivo e deixou este para
        # trás. Ele não decidia se a demanda existia, mas decidia o que o
        # Administrador Local via primeiro; com mínimo por Unidade
        # configurado, a lista chegava ordenada por um número que não governa
        # nada.
        #
        # O SQL agora só devolve os candidatos em ordem estável, e a
        # prioridade é calculada depois da classificação, junto do resto.
        f'ORDER BY ues.unit_id, ues.epi_id',
        tuple(stock_params)
    ).fetchall()
    baixo_estoque = []
    for row in stock_rows:
        d = dict(row)
        # Só `critical` gera reposição automática. `near_minimum` é atenção
        # preventiva e não vira demanda de compra; `disabled` não gera nada.
        # Compra MANUAL por usuário autorizado segue independente disto.
        classificacao = classify_unit_epi_stock(
            connection, int(d['company_id']), int(d['unit_id']), int(d['epi_id']),
            unit_stock=int(d['current_stock'] or 0),
        )
        if classificacao.stock_status != STATUS_CRITICAL:
            continue
        # O alvo da reposição é o mínimo EFETIVO daquela Unidade — nunca o
        # limite da faixa de atenção. A faixa laranja antecipa a atenção; não
        # aumenta artificialmente o estoque-alvo.
        d['minimum_stock'] = classificacao.effective_minimum_stock
        d['minimum_stock_source'] = classificacao.minimum_stock_source
        d['stock_status'] = classificacao.stock_status
        d['demand_type'] = 'low_stock'
        d['quantity_requested'] = max(1, classificacao.effective_minimum_stock - int(row['current_stock']))
        d['employee_name'] = ''
        d['employee_role'] = ''
        d['employee_sector'] = d.get('employee_sector') or 'Estoque baixo'
        d['sector'] = d['employee_sector']
        d['glove_size'] = d.get('glove_size') or 'N/A'
        d['size'] = d.get('size') or 'N/A'
        d['uniform_size'] = d.get('uniform_size') or 'N/A'
        d['status'] = 'low_stock'
        balances = fetch_epi_size_balance(connection, int(d['company_id']), int(d['unit_id']), int(d['epi_id']))
        d['size_balances'] = balances
        d['size_demands'] = _build_low_stock_size_demands(d, balances)
        baixo_estoque.append(d)
    # Prioridade = tamanho do buraco NAQUELA Unidade: mínimo efetivo dela menos
    # o saldo dela. Mesma fonte que já dimensiona a reposição
    # (`quantity_requested`), então a ordem e o número que o Administrador
    # Local lê passam a concordar. Empates saem por (unidade, EPI) para a
    # listagem não trocar de ordem entre duas chamadas iguais.
    baixo_estoque.sort(key=lambda item: (
        -(int(item['minimum_stock']) - int(item['current_stock'] or 0)),
        int(item['unit_id']),
        int(item['epi_id']),
    ))
    demands.extend(baixo_estoque)
    return demands


def _build_low_stock_size_demands(demand, balances):
    """Para uma demanda de estoque mínimo, lista TODOS os tamanhos cadastrados/em
    rastreio do EPI com saldo atual, mínimo e sugestão de reposição (mínimo −
    atual). O Administrador Local pode ajustar/remover/ignorar tamanhos ao criar
    a requisição. Adapta a regra existente (size_balances + estoque agregado).
    """
    minimum = int(demand.get('minimum_stock') or 0)
    rows = []
    if balances:
        combos = {}
        order = []
        for b in balances:
            key = (b.get('glove_size') or 'N/A', b.get('size') or 'N/A', b.get('uniform_size') or 'N/A')
            if key not in combos:
                order.append(key)
            combos[key] = int(b.get('quantity') or 0)
        # Garante o tamanho cadastrado do próprio EPI mesmo sem saldo em estoque.
        epi_key = (demand.get('glove_size') or 'N/A', demand.get('size') or 'N/A', demand.get('uniform_size') or 'N/A')
        if epi_key not in combos:
            order.append(epi_key)
            combos[epi_key] = 0
        for key in order:
            gs, sz, us = key
            current = combos[key]
            rows.append({
                'glove_size': gs, 'size': sz, 'uniform_size': us,
                'current_stock': current, 'minimum_stock': minimum,
                'suggested_quantity': max(0, minimum - current),
            })
    else:
        current = int(demand.get('current_stock') or 0)
        rows.append({
            'glove_size': demand.get('glove_size') or 'N/A',
            'size': demand.get('size') or 'N/A',
            'uniform_size': demand.get('uniform_size') or 'N/A',
            'current_stock': current, 'minimum_stock': minimum,
            'suggested_quantity': max(1, minimum - current),
        })
    return rows


def _record_purchase_event(connection, company_id, entity_type, entity_id, action, status_from, status_to, comment, actor_user_id, actor_name, ip_address='', actor_role='', reason='', destination=''):
    now = datetime.now(UTC).isoformat()
    connection.execute(
        'INSERT INTO purchase_events (company_id, entity_type, entity_id, action, status_from, status_to, comment, actor_user_id, actor_name, actor_role, reason, destination, ip_address, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (company_id, entity_type, entity_id, action, status_from, status_to, comment, actor_user_id, actor_name, actor_role, reason, destination, ip_address, now)
    )


def ensure_purchase_request_action_scope(connection, actor, purchase_request, *, actor_operational_unit_id=None):
    ensure_resource_company(actor, purchase_request, 'Requisição')
    if actor.get('role') == 'master_admin':
        return
    scope_unit_id = actor_operational_unit_id(connection, actor) if actor_operational_unit_id is not None else None
    if actor_operational_unit_id is not None and actor.get('role') in ('admin', 'user'):
        if not scope_unit_id:
            raise PermissionError('Seu perfil não possui unidade operacional ativa.')
        if int(purchase_request['unit_id']) != int(scope_unit_id):
            raise PermissionError('Requisição fora da unidade operacional do usuário.')
    purchase_scope_units = get_actor_purchase_unit_scope(connection, actor)
    if actor.get('role') in ('buyer', 'approver'):
        if not purchase_scope_units:
            raise PermissionError('Usuário sem unidade de compras vinculada.')
        if int(purchase_request['unit_id']) not in set(int(uid) for uid in purchase_scope_units):
            raise PermissionError('Requisição fora das unidades de compras vinculadas ao usuário.')


def purchase_creation_unit_scope_violation(
    connection, actor, unit_id, *, actor_operational_unit_id=None, locked_profile_message='',
):
    """Motivo pelo qual o ator NÃO pode CRIAR na Unidade alvo; `''` se pode.

    As duas irmãs (`ensure_purchase_request_action_scope` e
    `ensure_purchase_order_action_scope`) validam um registro que já existe. Na
    criação não existe registro ainda: o que precisa ser validado é a Unidade
    que o payload está pedindo. Sem esta checagem, Comprador e Aprovador
    criavam PR/PO para qualquer Unidade da empresa e só eram barrados na ação
    seguinte — o registro já nascia na Unidade errada, e um recebimento
    creditaria o estoque dela.

    Comprador e Aprovador atuam na CARTEIRA de Unidades de
    `purchase_role_unit_links`, que pode ser múltipla. Múltipla é a carteira,
    não a transação: cada PR/PO nasce em UMA Unidade, e ela precisa estar na
    carteira de quem cria. Vínculo em A, B e C não soma nada entre A, B e C —
    só diz onde a pessoa pode agir.

    Devolve mensagem em vez de levantar porque as rotas de criação respondem
    403 com o envelope `UNIT_SCOPE_VIOLATION`, já existente; as irmãs levantam
    `PermissionError` e caem no 403 genérico. Manter cada caminho no seu
    formato evita mudar o envelope que os clientes já tratam.
    """
    if actor.get('role') == 'master_admin':
        return ''
    unit_id = int(unit_id)
    scope_unit_id = actor_operational_unit_id(connection, actor) if actor_operational_unit_id is not None else None
    if actor.get('role') in ('admin', 'user'):
        if not scope_unit_id or unit_id != int(scope_unit_id):
            return locked_profile_message
        return ''
    if actor.get('role') in ('buyer', 'approver'):
        purchase_scope_units = get_actor_purchase_unit_scope(connection, actor)
        if not purchase_scope_units:
            return 'Usuário sem unidade de compras vinculada.'
        if unit_id not in {int(uid) for uid in purchase_scope_units}:
            return 'Unidade fora das unidades de compras vinculadas ao usuário.'
    return ''


def ensure_purchase_workflow_permission(actor, permission_group):
    if permission_group == 'approve':
        ensure_permission(actor, PERM_PO_APPROVE)
        return
    ensure_permission(actor, PERM_PURCHASE_REQUESTS_UPDATE)


def _format_purchase_item_decision_comment(item, decision, totals=None):
    quantity = int(item.get('quantity_requested') or item.get('quantity') or 1)
    unit_price = float(item.get('unit_price') or 0)
    total_price = float(item.get('total_price') or (unit_price * quantity))
    parts = [
        f"Item #{item.get('id')}",
        f"EPI: {item.get('epi_name') or item.get('epi_display_name') or ''}",
        f"CA: {item.get('ca') or item.get('epi_ca') or ''}",
        f"Qtd: {quantity}",
        f"Valor unitário: {unit_price:.2f}",
        f"Total item: {total_price:.2f}",
        f"Decisão: {'Aprovado' if decision.get('approved') else 'Reprovado'}",
    ]
    if not decision.get('approved'):
        parts.append(f"Motivo: {decision.get('reason') or ''}")
        if decision.get('comment'):
            parts.append(f"Observação: {decision.get('comment')}")
    if totals:
        parts.extend([
            f"Total aprovado: {float(totals.get('approved_total') or 0):.2f}",
            f"Total reprovado: {float(totals.get('rejected_total') or 0):.2f}",
            f"Total geral: {float(totals.get('grand_total') or 0):.2f}",
        ])
    return ' | '.join(parts)


def apply_purchase_request_item_approval(connection, actor, pr_id, payload, ip_address='', transition=None, *, actor_operational_unit_id=None):
    purchase_request = connection.execute('SELECT * FROM purchase_requests WHERE id = ?', (int(pr_id),)).fetchone()
    if not purchase_request:
        raise ValueError('Requisição não encontrada.')
    pr = row_to_dict(purchase_request)
    ensure_purchase_request_action_scope(connection, actor, pr, actor_operational_unit_id=actor_operational_unit_id)
    if transition is None:
        transition = resolve_purchase_transition(pr.get('status'), 'approve')
    ensure_purchase_workflow_permission(actor, transition.get('permission'))
    item_rows = connection.execute(
        'SELECT pri.*, e.name AS epi_display_name, e.ca AS epi_ca, u.name AS unit_name '
        'FROM purchase_request_items pri '
        'JOIN epis e ON e.id = pri.epi_id '
        'JOIN units u ON u.id = pri.unit_id '
        'WHERE pri.purchase_request_id = ? ORDER BY pri.id',
        (int(pr_id),)
    ).fetchall()
    items = [row_to_dict(row) for row in item_rows]
    decisions, status_to, totals = normalize_purchase_item_approval_decisions(items, payload)
    now = datetime.now(UTC).isoformat()
    summary_parts = []
    for decision in decisions:
        item = decision['item']
        item_id = int(decision['item_id'])
        previous_status = str(item.get('status') or '')
        new_status = 'approved' if decision.get('approved') else 'rejected'
        comment = _format_purchase_item_decision_comment(item, decision)
        if decision.get('approved'):
            connection.execute(
                """
                UPDATE purchase_request_items
                SET status = 'approved', quantity_approved = quantity_requested,
                    rejection_reason = '', rejection_comment = '',
                    approval_decided_by_user_id = ?, approval_decided_by_name = ?, approval_decided_at = ?,
                    updated_at = ?
                WHERE purchase_request_id = ? AND id = ?
                """,
                (int(actor['id']), actor['full_name'], now, now, int(pr_id), item_id),
            )
        else:
            note_suffix = f"Reprovado: {decision.get('reason') or ''}"
            if decision.get('comment'):
                note_suffix += f" — {decision.get('comment')}"
            connection.execute(
                """
                UPDATE purchase_request_items
                SET status = 'rejected', quantity_approved = 0,
                    rejection_reason = ?, rejection_comment = ?,
                    approval_decided_by_user_id = ?, approval_decided_by_name = ?, approval_decided_at = ?,
                    notes = trim(COALESCE(NULLIF(notes, ''), '') || CASE WHEN COALESCE(NULLIF(notes, ''), '') = '' THEN '' ELSE ' | ' END || ?),
                    updated_at = ?
                WHERE purchase_request_id = ? AND id = ?
                """,
                (decision.get('reason') or '', decision.get('comment') or '', int(actor['id']), actor['full_name'], now, note_suffix, now, int(pr_id), item_id),
            )
        _record_purchase_event(
            connection,
            int(pr['company_id']),
            'purchase_request_item',
            item_id,
            'item_approval_decision',
            previous_status,
            new_status,
            comment,
            int(actor['id']),
            actor['full_name'],
            ip_address,
            actor.get('role') or '',
            decision.get('reason') or '',
            'closed' if decision.get('approved') else 'rejected',
        )
        summary_parts.append(_format_purchase_item_decision_comment(item, decision))
    connection.execute(
        'UPDATE purchase_requests SET status = ?, updated_at = ? WHERE id = ?',
        (status_to, now, int(pr_id))
    )
    request_comment = 'Decisão por item | Resumo da aprovação por item: ' + ' || '.join(summary_parts)
    request_comment += (
        f" || Totais: aprovado {totals['approved_total']:.2f} ({totals['approved_quantity']} un.), "
        f"reprovado {totals['rejected_total']:.2f} ({totals['rejected_quantity']} un.), "
        f"geral {totals['grand_total']:.2f}"
    )
    _record_purchase_event(
        connection,
        int(pr['company_id']),
        'purchase_request',
        int(pr_id),
        'approve',
        transition['status_from'],
        status_to,
        request_comment,
        int(actor['id']),
        actor['full_name'],
        ip_address,
        actor.get('role') or '',
        '',
        'closed',
    )
    structured_log(
        'info',
        'purchase.workflow.item_approval_completed',
        purchase_request_id=int(pr_id),
        status_from=transition['status_from'],
        status_to=status_to,
        actor_user_id=int(actor['id']),
        actor_role=actor.get('role'),
        approved_count=totals['approved_count'],
        rejected_count=totals['rejected_count'],
        approved_total=totals['approved_total'],
        rejected_total=totals['rejected_total'],
    )
    return {
        'ok': True,
        'id': int(pr_id),
        'status': status_to,
        'status_label': PURCHASE_WORKFLOW_STATUS_LABELS.get(status_to, status_to),
        'action': 'approve',
        'totals': totals,
        'decisions': [
            {
                'item_id': int(decision['item_id']),
                'status': 'approved' if decision.get('approved') else 'rejected',
                'reason': decision.get('reason') or '',
                'comment': decision.get('comment') or '',
            }
            for decision in decisions
        ],
    }


def apply_purchase_request_workflow_action(connection, actor, pr_id, payload, ip_address='', *, actor_operational_unit_id=None):
    purchase_request = connection.execute('SELECT * FROM purchase_requests WHERE id = ?', (int(pr_id),)).fetchone()
    if not purchase_request:
        raise ValueError('Requisição não encontrada.')
    pr = row_to_dict(purchase_request)
    ensure_purchase_request_action_scope(connection, actor, pr, actor_operational_unit_id=actor_operational_unit_id)
    events = [row_to_dict(row) for row in connection.execute(
        'SELECT * FROM purchase_events WHERE entity_type = ? AND entity_id = ? ORDER BY created_at DESC, id DESC',
        ('purchase_request', int(pr_id))
    ).fetchall()]
    transition = resolve_purchase_transition(
        pr.get('status'),
        payload.get('action'),
        requester_review_origin=latest_requester_review_origin(events),
    )
    ensure_purchase_workflow_permission(actor, transition.get('permission'))
    reason, comment = validate_purchase_transition_payload(
        transition,
        reason=payload.get('reason'),
        comment=payload.get('comment'),
    )
    requested_changes = payload.get('requested_changes') or []
    if isinstance(requested_changes, str):
        requested_changes = [requested_changes]
    affected_item_ids = [int(item_id) for item_id in (payload.get('item_ids') or []) if str(item_id).isdigit()]
    if affected_item_ids:
        requested_changes.append('Itens afetados: ' + ', '.join(str(item_id) for item_id in affected_item_ids))
    event_comment = serialize_purchase_event_comment(reason, comment, requested_changes)
    now = datetime.now(UTC).isoformat()
    status_to = transition['status_to']
    if transition['action'] == 'approve':
        return apply_purchase_request_item_approval(
            connection, actor, pr_id, payload, ip_address, transition,
            actor_operational_unit_id=actor_operational_unit_id,
        )
    connection.execute(
        'UPDATE purchase_requests SET status = ?, updated_at = ? WHERE id = ?',
        (status_to, now, int(pr_id))
    )
    _record_purchase_event(
        connection,
        int(pr['company_id']),
        'purchase_request',
        int(pr_id),
        transition['action'],
        transition['status_from'],
        status_to,
        event_comment,
        int(actor['id']),
        actor['full_name'],
        ip_address,
        actor.get('role') or '',
        reason,
        transition.get('destination') or '',
    )
    structured_log(
        'info',
        'purchase.workflow.transition',
        purchase_request_id=int(pr_id),
        action=transition['action'],
        status_from=transition['status_from'],
        status_to=transition['status_to'],
        actor_user_id=int(actor['id']),
        actor_role=actor.get('role'),
        destination=transition.get('destination') or '',
    )
    if transition.get('destination') == 'buyer':
        structured_log('info', 'purchase.workflow.notify_buyer', purchase_request_id=int(pr_id), reason=reason)
    elif transition.get('destination') == 'requester':
        structured_log('info', 'purchase.workflow.notify_requester', purchase_request_id=int(pr_id), reason=reason)
    elif transition.get('destination') == 'approver':
        structured_log('info', 'purchase.workflow.notify_approver', purchase_request_id=int(pr_id))
    return {
        'ok': True,
        'id': int(pr_id),
        'status': status_to,
        'status_label': PURCHASE_WORKFLOW_STATUS_LABELS.get(status_to, status_to),
        'action': transition['action'],
    }


def approved_purchase_request_items_for_po(connection, pr_id, items):
    approved_rows = connection.execute(
        "SELECT * FROM purchase_request_items WHERE purchase_request_id = ? AND status = 'approved'",
        (int(pr_id),),
    ).fetchall()
    approved_items = {int(row['id']): row_to_dict(row) for row in approved_rows}
    if not approved_items:
        raise ValueError('Requisição sem itens aprovados para gerar PO.')
    for item in items or []:
        pr_item_id = int(item['purchase_request_item_id']) if item.get('purchase_request_item_id') else 0
        if not pr_item_id:
            raise ValueError('PO vinculada a requisição aprovada deve informar o item aprovado da requisição.')
        if pr_item_id not in approved_items:
            raise ValueError('Somente itens aprovados podem ser incluídos na PO.')
    return approved_items


def _purchase_request_items_signature(items):
    normalized = []
    for item in items or []:
        normalized.append((
            int(item.get('epi_id') or 0),
            int(item.get('quantity_requested') or item.get('quantity') or 1),
            int(item.get('employee_id') or 0),
            str(item.get('origin') or 'stock_minimum'),
            str(item.get('glove_size') or 'N/A'),
            str(item.get('size') or 'N/A'),
            str(item.get('uniform_size') or 'N/A'),
        ))
    return sorted(normalized)


def find_recent_duplicate_purchase_request(connection, actor, unit_id, title, items, now):
    cutoff = (datetime.fromisoformat(now) - timedelta(seconds=60)).isoformat()
    expected_signature = _purchase_request_items_signature(items)
    candidates = connection.execute(
        "SELECT * FROM purchase_requests WHERE company_id = ? AND unit_id = ? AND created_by_user_id = ? AND title = ? AND created_at >= ? ORDER BY id DESC LIMIT 5",
        (int(actor['company_id']), int(unit_id), int(actor['id']), title, cutoff),
    ).fetchall()
    for candidate in candidates:
        rows = connection.execute(
            'SELECT epi_id, quantity_requested, employee_id, origin, glove_size, size, uniform_size '
            'FROM purchase_request_items WHERE purchase_request_id = ?',
            (int(candidate['id']),)
        ).fetchall()
        existing = [row_to_dict(row) for row in rows]
        if _purchase_request_items_signature(existing) == expected_signature:
            return int(candidate['id'])
    return None


def generate_po_number(connection, company_id):
    year = datetime.now(UTC).year
    prefix = f'PO-{year}-'
    row = connection.execute(
        "SELECT MAX(CAST(SUBSTR(po_number, ?) AS INTEGER)) AS last_seq FROM purchase_orders WHERE company_id = ? AND po_number LIKE ?",
        (len(prefix) + 1, company_id, f'{prefix}%')
    ).fetchone()
    last_seq = int(row['last_seq'] or 0) if row else 0
    return f'{prefix}{last_seq + 1:04d}'


def _auto_add_received_items_to_stock(connection, pr_id, received_item_flags, actor_id, actor_name, now):
    """Adds received EPI items to stock automatically after conferência.

    Returns ``(total_units, qr_labels)`` where ``qr_labels`` mirrors the label
    shape produced by the manual stock entry (modules/stock/routes.py), so the
    conference screen can offer "Imprimir QR Codes" reusing printStockLabels.
    """
    from modules.deliveries.service import ensure_stock_movement_size_columns
    if received_item_flags:
        received_ids = {int(f['id']) for f in received_item_flags if f.get('received')}
    else:
        rows = connection.execute(
            "SELECT id FROM purchase_request_items WHERE purchase_request_id = ? AND status = 'received'",
            (pr_id,)
        ).fetchall()
        received_ids = {int(r['id']) for r in rows}
    if not received_ids:
        return 0, []
    placeholders = ','.join('?' for _ in received_ids)
    pr_items = [row_to_dict(r) for r in connection.execute(
        f'SELECT * FROM purchase_request_items WHERE purchase_request_id = ? AND id IN ({placeholders})',
        (pr_id, *received_ids)
    ).fetchall()]
    # Datas de validade do fabricante informadas na conferência (NT 146/2015):
    # nenhum item deve entrar em estoque sem essa data. A captura é por lote — a
    # primeira data lida de um mesmo EPI serve para todas as demais unidades
    # daquele EPI (fallback abaixo), mesmo que a UI envie em apenas um item.
    validity_by_item = {}
    for flag in (received_item_flags or []):
        fid = int(str(flag.get('id') or '').strip() or '0')
        fdate = str(flag.get('manufacturer_validity_date') or '').strip()
        if fid and fdate:
            validity_by_item[fid] = fdate
    validity_by_epi = {}
    for it in pr_items:
        d = validity_by_item.get(int(it['id']))
        if d and int(it['epi_id']) not in validity_by_epi:
            validity_by_epi[int(it['epi_id'])] = d
    total_units = 0
    qr_labels = []
    ensure_stock_movement_size_columns(connection)
    for item in pr_items:
        epi_id = int(item['epi_id'])
        unit_id = int(item['unit_id'])
        company_id = int(item['company_id'])
        pri_id = int(item['id'])
        po_item = connection.execute(
            'SELECT * FROM purchase_order_items WHERE purchase_request_item_id = ? ORDER BY id DESC LIMIT 1',
            (pri_id,)
        ).fetchone()
        if po_item:
            quantity = int(po_item.get('quantity_received') or 0)
        else:
            quantity = int(item.get('quantity_requested') or 0)
        if quantity <= 0:
            continue
        manufacturer_validity = str(
            validity_by_item.get(pri_id) or validity_by_epi.get(epi_id) or ''
        ).strip()
        if manufacturer_validity:
            # Persiste a validade do fabricante no EPI (fonte usada pelas regras
            # de alerta/relatório/bloqueio de entrega — NT 146/2015), garantindo
            # que o item não entre em estoque sem data de vencimento.
            connection.execute(
                'UPDATE epis SET epi_validity_date = ? WHERE id = ?',
                (manufacturer_validity, epi_id)
            )
        glove_size = str(item.get('glove_size') or 'N/A')
        size = str(item.get('size') or 'N/A')
        uniform_size = str(item.get('uniform_size') or 'N/A')
        epi_row = connection.execute('SELECT name FROM epis WHERE id = ?', (epi_id,)).fetchone()
        epi_name = str((epi_row['name'] if epi_row else None) or item.get('epi_name') or '')
        unit_row = connection.execute('SELECT name FROM units WHERE id = ?', (unit_id,)).fetchone()
        unit_name = str((unit_row['name'] if unit_row else None) or '')
        stock_row = get_unit_stock(connection, company_id, unit_id, epi_id)
        previous_stock = int((stock_row or {}).get('quantity') or 0)
        new_stock = previous_stock + quantity
        movement_cursor = connection.execute(
            'INSERT INTO stock_movements ('
            'company_id, unit_id, epi_id, movement_type, quantity, previous_stock, new_stock, '
            'source_type, source_id, notes, actor_user_id, actor_name, created_at, glove_size, size, uniform_size'
            ') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                company_id, unit_id, epi_id, 'in', quantity, previous_stock, new_stock,
                'purchase_request', pri_id,
                f'Entrada automática — Conferência Requisição #{pr_id}',
                actor_id, actor_name, now, glove_size, size, uniform_size
            )
        )
        movement_id = int(movement_cursor.lastrowid)
        upsert_unit_stock(connection, company_id, unit_id, epi_id, new_stock)
        for _ in range(quantity):
            seq_value = next_company_qr_sequence(connection, company_id)
            qr_value = build_stock_item_qr(company_id, unit_id, seq_value)
            item_cursor = connection.execute(
                'INSERT INTO epi_stock_items ('
                'company_id, unit_id, epi_id, glove_size, size, uniform_size, qr_sequence, qr_code_value, status, '
                'stock_movement_id, lot_code, manufacture_date, label_measure, label_printer_name, label_print_format, '
                'generated_by_user_id, created_at, updated_at'
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'in_stock', ?, '', '', 'unidade', '', '', ?, ?, ?)",
                (
                    company_id, unit_id, epi_id, glove_size, size, uniform_size,
                    seq_value, qr_value, movement_id,
                    actor_id, now, now
                )
            )
            qr_labels.append({
                'qr_code_value': qr_value,
                'epi_name': epi_name,
                'glove_size': glove_size,
                'size': size,
                'uniform_size': uniform_size,
                'stock_item_id': int(item_cursor.lastrowid),
                'manufacture_date': '',
                'manufacturer_validity_date': manufacturer_validity,
                'unit_name': unit_name,
                'label_measure': 'unidade',
                'label_printer_name': '',
                'label_print_format': '',
                'reprint_count': 0,
            })
        total_units += quantity
        epi_req_id = item.get('epi_request_id')
        if epi_req_id:
            connection.execute(
                "UPDATE epi_requests SET status = 'separado', last_updated_at = ? "
                "WHERE id = ? AND status NOT IN ('entregue', 'cancelado', 'rejeitado')",
                (now, int(epi_req_id))
            )
    return total_units, qr_labels


def _record_partial_receipt_pendencies(connection, pr, received_item_flags, actor_id, actor_name, now, ip_address=''):
    """Recebimento parcial: registra pendência por item recebido a menor / não
    recebido e dispara um alerta automático ao comprador (purchase_event com
    destination='buyer'). Retorna a lista de pendências criadas.

    Adapta o fluxo existente: a conferência já marca itens 'received'/'not_received';
    aqui persistimos a falta de forma estruturada e avisamos o comprador, sem criar
    um fluxo paralelo.
    """
    if not received_item_flags:
        return []
    pr_id = int(pr['id'])
    company_id = int(pr['company_id'])
    short_item_ids = {int(f['id']) for f in received_item_flags if f.get('id') and not f.get('received')}
    if not short_item_ids:
        return []
    placeholders = ','.join('?' for _ in short_item_ids)
    rows = [row_to_dict(r) for r in connection.execute(
        f'SELECT * FROM purchase_request_items WHERE purchase_request_id = ? AND id IN ({placeholders})',
        (pr_id, *short_item_ids)
    ).fetchall()]
    pendencies = []
    for item in rows:
        pri_id = int(item['id'])
        po_item = connection.execute(
            'SELECT quantity_received FROM purchase_order_items WHERE purchase_request_item_id = ? ORDER BY id DESC LIMIT 1',
            (pri_id,)
        ).fetchone()
        quantity_ordered = int(item.get('quantity_requested') or 0)
        quantity_received = int(po_item['quantity_received']) if po_item and po_item['quantity_received'] is not None else 0
        quantity_short = max(0, quantity_ordered - quantity_received)
        if quantity_short <= 0:
            continue
        epi_name = str(item.get('epi_name') or '')
        cursor = connection.execute(
            'INSERT INTO purchase_pendencies ('
            'company_id, unit_id, purchase_request_id, purchase_request_item_id, epi_id, epi_name, '
            'glove_size, size, uniform_size, quantity_ordered, quantity_received, quantity_short, '
            'reason, status, created_by_user_id, created_by_name, created_at, updated_at'
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?)",
            (
                company_id, item.get('unit_id'), pr_id, pri_id, item.get('epi_id'), epi_name,
                str(item.get('glove_size') or 'N/A'), str(item.get('size') or 'N/A'), str(item.get('uniform_size') or 'N/A'),
                quantity_ordered, quantity_received, quantity_short,
                'Recebimento parcial — item recebido a menor na conferência.',
                actor_id, actor_name, now, now,
            )
        )
        pendencies.append({
            'id': int(cursor.lastrowid), 'epi_name': epi_name,
            'quantity_ordered': quantity_ordered, 'quantity_received': quantity_received,
            'quantity_short': quantity_short,
        })
    if pendencies:
        summary = '; '.join(
            f"{p['epi_name']}: faltam {p['quantity_short']} (pedido {p['quantity_ordered']}, recebido {p['quantity_received']})"
            for p in pendencies
        )
        _record_purchase_event(
            connection, company_id, 'purchase_request', pr_id, 'partial_receipt_pendency',
            str(pr.get('status') or ''), 'pendency_open',
            f'Recebimento parcial — pendência(s) para o comprador: {summary}',
            actor_id, actor_name, ip_address, destination='buyer',
        )
    return pendencies


def fetch_purchase_pendencies(connection, company_id, scope_unit_id=None, status='open', purchase_scope_units=None):
    """Lista pendências de recebimento parcial para o comprador acompanhar."""
    clauses, params = [], []
    if company_id is not None:
        clauses.append('p.company_id = ?')
        params.append(company_id)
    if scope_unit_id:
        clauses.append('p.unit_id = ?')
        params.append(int(scope_unit_id))
    elif purchase_scope_units:
        placeholders = ','.join(['?'] * len(purchase_scope_units))
        clauses.append(f'p.unit_id IN ({placeholders})')
        params.extend(purchase_scope_units)
    if status:
        clauses.append('p.status = ?')
        params.append(status)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ''
    rows = connection.execute(
        'SELECT p.*, u.name AS unit_name, pr.title AS request_title '
        'FROM purchase_pendencies p '
        'LEFT JOIN units u ON u.id = p.unit_id '
        'LEFT JOIN purchase_requests pr ON pr.id = p.purchase_request_id '
        f'{where_sql} ORDER BY p.created_at DESC, p.id DESC',
        tuple(params)
    ).fetchall()
    return [row_to_dict(r) for r in rows]


def resolve_purchase_pendency(connection, actor, pendency_id, now=None):
    """Marca uma pendência como resolvida pelo comprador."""
    now = now or datetime.now(UTC).isoformat()
    row = connection.execute('SELECT * FROM purchase_pendencies WHERE id = ?', (int(pendency_id),)).fetchone()
    if not row:
        raise ValueError('Pendência não encontrada.')
    pendency = row_to_dict(row)
    ensure_resource_company(actor, pendency, 'Pendência')
    connection.execute(
        "UPDATE purchase_pendencies SET status = 'resolved', resolved_by_user_id = ?, "
        'resolved_by_name = ?, resolved_at = ?, updated_at = ? WHERE id = ?',
        (int(actor['id']), actor.get('full_name') or '', now, now, int(pendency_id))
    )
    return {'ok': True, 'id': int(pendency_id), 'status': 'resolved'}


def fetch_purchase_request_stock_labels(connection, pr_id):
    """Returns the QR labels of the stock items auto-generated from a PR's
    conferência, so the conference screen can re-print/re-issue them later.

    Mirrors the label shape consumed by printStockLabels in the frontend.
    """
    rows = connection.execute(
        'SELECT esi.id AS stock_item_id, esi.qr_code_value, esi.glove_size, esi.size, '
        'esi.uniform_size, esi.manufacture_date, esi.label_measure, esi.label_printer_name, '
        'esi.label_print_format, COALESCE(esi.reprint_count, 0) AS reprint_count, '
        'e.name AS epi_name, u.name AS unit_name '
        'FROM epi_stock_items esi '
        'JOIN stock_movements sm ON sm.id = esi.stock_movement_id '
        'JOIN purchase_request_items pri ON pri.id = sm.source_id '
        'JOIN epis e ON e.id = esi.epi_id '
        'JOIN units u ON u.id = esi.unit_id '
        "WHERE sm.source_type = 'purchase_request' AND pri.purchase_request_id = ? "
        'ORDER BY esi.id',
        (int(pr_id),)
    ).fetchall()
    return [row_to_dict(r) for r in rows]


# ── Query / fetch functions ────────────────────────────────────────────────────

def fetch_epi_requests(connection, company_filter, scope_unit_id, purchase_scope):
    from modules.legal_entities.service import employee_legal_entity_sql
    # Requisição registra Empresa / CNPJ / Unidade / Solicitante — o CNPJ é
    # derivado do vínculo jurídico do solicitante (mesma fonte única das
    # entregas), evitando divergência com o cadastro do colaborador.
    legal_entity_select, legal_entity_join = employee_legal_entity_sql(connection)
    clauses, params = [], []
    if company_filter:
        clauses.append('r.company_id = ?')
        params.append(int(company_filter))
    if scope_unit_id:
        clauses.append('r.unit_id = ?')
        params.append(int(scope_unit_id))
    elif purchase_scope:
        placeholders = ','.join(['?'] * len(purchase_scope))
        clauses.append(f'r.unit_id IN ({placeholders})')
        params.extend(purchase_scope)
    final_where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
    rows = connection.execute(
        'SELECT r.*, employees.name AS employee_name, employees.employee_id_code, '
        'employees.sector AS employee_sector, employees.role_name AS employee_role, '
        'units.name AS unit_name, '
        f'epis.name AS epi_name, epis.ca, epis.unit_measure{legal_entity_select} '
        'FROM epi_requests r '
        'JOIN employees ON employees.id = r.employee_id '
        'JOIN units ON units.id = r.unit_id '
        f'JOIN epis ON epis.id = r.epi_id{legal_entity_join} '
        f'{final_where} '
        'ORDER BY r.requested_at DESC, r.id DESC',
        tuple(params),
    ).fetchall()
    return [row_to_dict(r) for r in rows]


def fetch_purchase_requests(connection, company_id, scope_unit_id, purchase_scope_units, status_filter=None):
    clauses, params = ['pr.company_id = ?'], [company_id]
    if scope_unit_id:
        clauses.append('pr.unit_id = ?')
        params.append(int(scope_unit_id))
    elif purchase_scope_units:
        placeholders = ','.join(['?'] * len(purchase_scope_units))
        clauses.append(f'pr.unit_id IN ({placeholders})')
        params.extend(purchase_scope_units)
    if status_filter:
        clauses.append('pr.status = ?')
        params.append(status_filter)
    where_sql = f"WHERE {' AND '.join(clauses)}"
    rows = connection.execute(
        f'SELECT pr.*, u.name AS unit_name, '
        f'(SELECT COUNT(*) FROM purchase_request_items pri WHERE pri.purchase_request_id = pr.id) AS items_count '
        f'FROM purchase_requests pr JOIN units u ON u.id = pr.unit_id {where_sql} ORDER BY pr.created_at DESC',
        tuple(params),
    ).fetchall()
    return [row_to_dict(r) for r in rows]


# Estados terminais de uma requisição de compra (não contam como "pendente").
_PURCHASE_REQUEST_TERMINAL_STATUSES = ('rejected', 'cancelled', 'closed', 'checked', 'received')


def count_pending_purchase_requests(connection, company_id, scope_unit_id=None, purchase_scope_units=None):
    """Conta requisições de compra em estado **não terminal** (pendentes de
    ação), no mesmo escopo de [fetch_purchase_requests]. Usado no KPI do
    dashboard (`pending_purchases` do bootstrap)."""
    clauses, params = ['pr.company_id = ?'], [company_id]
    if scope_unit_id:
        clauses.append('pr.unit_id = ?')
        params.append(int(scope_unit_id))
    elif purchase_scope_units:
        placeholders = ','.join(['?'] * len(purchase_scope_units))
        clauses.append(f'pr.unit_id IN ({placeholders})')
        params.extend(purchase_scope_units)
    terminal_placeholders = ','.join(['?'] * len(_PURCHASE_REQUEST_TERMINAL_STATUSES))
    clauses.append(f'pr.status NOT IN ({terminal_placeholders})')
    params.extend(_PURCHASE_REQUEST_TERMINAL_STATUSES)
    row = connection.execute(
        f"SELECT COUNT(*) AS n FROM purchase_requests pr WHERE {' AND '.join(clauses)}",
        tuple(params),
    ).fetchone()
    if not row:
        return 0
    data = row if isinstance(row, dict) else row_to_dict(row)
    return int(data['n'])


def get_purchase_request_detail(connection, pr_id):
    """Returns (pr_dict, items, events) or (None, [], []) if not found."""
    pr = connection.execute(
        'SELECT pr.*, u.name AS unit_name FROM purchase_requests pr '
        'JOIN units u ON u.id = pr.unit_id WHERE pr.id = ?',
        (pr_id,),
    ).fetchone()
    if not pr:
        return None, [], []
    items = connection.execute(
        'SELECT pri.*, e.name AS epi_display_name, e.ca AS epi_ca, u.name AS unit_name '
        'FROM purchase_request_items pri '
        'JOIN epis e ON e.id = pri.epi_id '
        'JOIN units u ON u.id = pri.unit_id '
        'WHERE pri.purchase_request_id = ? ORDER BY pri.id',
        (pr_id,),
    ).fetchall()
    events = connection.execute(
        'SELECT * FROM purchase_events WHERE entity_type = ? AND entity_id = ? ORDER BY created_at DESC, id DESC',
        ('purchase_request', pr_id),
    ).fetchall()
    return row_to_dict(pr), [row_to_dict(i) for i in items], [row_to_dict(e) for e in events]


def fetch_purchase_orders(connection, company_id, scope_unit_id, purchase_scope_units, status_filter=None):
    clauses, params = ['po.company_id = ?'], [company_id]
    if scope_unit_id:
        clauses.append('po.unit_id = ?')
        params.append(int(scope_unit_id))
    elif purchase_scope_units:
        placeholders = ','.join(['?'] * len(purchase_scope_units))
        clauses.append(f'po.unit_id IN ({placeholders})')
        params.extend(purchase_scope_units)
    if status_filter:
        clauses.append('po.status = ?')
        params.append(status_filter)
    where_sql = f"WHERE {' AND '.join(clauses)}"
    rows = connection.execute(
        f'SELECT po.*, u.name AS unit_name, '
        f'(SELECT COUNT(*) FROM purchase_order_items poi WHERE poi.purchase_order_id = po.id) AS items_count '
        f'FROM purchase_orders po JOIN units u ON u.id = po.unit_id {where_sql} ORDER BY po.created_at DESC',
        tuple(params),
    ).fetchall()
    return [row_to_dict(r) for r in rows]


def get_purchase_order_detail(connection, po_id):
    """Returns (po_dict, items, files, events) or (None, [], [], []) if not found."""
    po = connection.execute(
        'SELECT po.*, u.name AS unit_name FROM purchase_orders po '
        'JOIN units u ON u.id = po.unit_id WHERE po.id = ?',
        (po_id,),
    ).fetchone()
    if not po:
        return None, [], [], []
    items = connection.execute(
        'SELECT poi.* FROM purchase_order_items poi WHERE poi.purchase_order_id = ?', (po_id,)
    ).fetchall()
    files = connection.execute(
        'SELECT id, file_name, file_type, uploaded_by_name, created_at '
        'FROM purchase_order_files WHERE purchase_order_id = ?',
        (po_id,),
    ).fetchall()
    events = connection.execute(
        'SELECT * FROM purchase_events WHERE entity_type = ? AND entity_id = ? ORDER BY created_at DESC',
        ('purchase_order', po_id),
    ).fetchall()
    return row_to_dict(po), [row_to_dict(i) for i in items], [row_to_dict(f) for f in files], [row_to_dict(e) for e in events]


def fetch_purchase_events(connection, company_id, entity_type=None, entity_id=None):
    clauses, params = ['company_id = ?'], [company_id]
    if entity_type:
        clauses.append('entity_type = ?')
        params.append(entity_type)
    if entity_id:
        clauses.append('entity_id = ?')
        params.append(int(entity_id))
    where_sql = f"WHERE {' AND '.join(clauses)}"
    rows = connection.execute(
        f'SELECT * FROM purchase_events {where_sql} ORDER BY created_at DESC LIMIT 200',
        tuple(params),
    ).fetchall()
    return [row_to_dict(r) for r in rows]


def fetch_authorized_suppliers(connection, company_id):
    rows = connection.execute(
        'SELECT * FROM authorized_suppliers WHERE company_id = ? ORDER BY name ASC',
        (int(company_id),),
    ).fetchall()
    return [row_to_dict(r) for r in rows]


def fetch_supplier_purchase_orders(connection, company_id, supplier_id):
    """Returns (supplier_dict, po_list) or (None, None) if supplier not found."""
    supplier = connection.execute(
        'SELECT * FROM authorized_suppliers WHERE id = ? AND company_id = ?',
        (supplier_id, company_id),
    ).fetchone()
    if not supplier:
        return None, None
    sup = row_to_dict(supplier)
    clauses = ['po.company_id = ?']
    params = [company_id]
    if sup.get('cnpj'):
        clauses.append('(po.supplier_cnpj = ? OR LOWER(TRIM(po.supplier)) = ?)')
        params.extend([sup['cnpj'], sup['name'].lower()])
    else:
        clauses.append('LOWER(TRIM(po.supplier)) = ?')
        params.append(sup['name'].lower())
    where_sql = f"WHERE {' AND '.join(clauses)}"
    rows = connection.execute(
        f'SELECT po.*, u.name AS unit_name, '
        f'(SELECT COUNT(*) FROM purchase_order_items poi WHERE poi.purchase_order_id = po.id) AS items_count '
        f'FROM purchase_orders po JOIN units u ON u.id = po.unit_id {where_sql} ORDER BY po.created_at DESC',
        tuple(params),
    ).fetchall()
    return sup, [row_to_dict(r) for r in rows]


def get_company_purchase_config(connection, company_id):
    import json as _json
    row = connection.execute(
        'SELECT value FROM app_meta WHERE key = ?',
        (f'purchase_config_{int(company_id)}',),
    ).fetchone()
    return _json.loads(row['value']) if row else {}


def set_company_purchase_config(connection, actor, company_id, require_admin_review):
    """Persiste a configuração de compras da empresa (app_meta). Retorna a config.

    PATCH, não substituição. A chave `purchase_config_{company_id}` guarda MAIS
    de um parâmetro — hoje `require_admin_review` e `po_approval_threshold`, que
    é lido por `_po_company_approval_threshold` para decidir se a PO precisa de
    segundo nível de aprovação. Escrever o JSON inteiro a partir de um único
    campo apagava silenciosamente os demais: bastava alternar a revisão do
    Admin para o limite de aprovação virar 0 e o multi-nível desligar sem que
    nada no fluxo acusasse. Só este caminho escreve a chave, então o dado
    perdido não voltava.

    Um valor guardado que não seja objeto JSON é tratado como ausente — não há
    o que preservar nele, e propagá-lo faria o merge estourar.
    """
    import json as _json
    from core.meta import set_meta
    stored = get_company_purchase_config(connection, int(company_id))
    config = dict(stored) if isinstance(stored, dict) else {}
    config['require_admin_review'] = bool(require_admin_review)
    set_meta(connection, f'purchase_config_{int(company_id)}', _json.dumps(config))
    _record_purchase_event(
        connection, int(company_id), 'company', int(company_id), 'purchase_config_updated', '', '',
        f'Revisão do Admin: {"exigida" if config["require_admin_review"] else "dispensada"}.',
        int(actor['id']), actor.get('full_name') or '', '', actor.get('role') or '',
    )
    return config


def create_purchase_function_links(connection, actor, company_id, employee_id, role_type, unit_ids):
    """Vincula um colaborador (comprador/aprovador) a unidades. Idempotente.

    Substitui o antigo user_unit_links (Fase 26). Retorna a lista de vínculos
    atuais do colaborador para aquela função.
    """
    role = normalize_purchase_function_type(role_type)
    employee_id = int(employee_id)
    employee = connection.execute(
        'SELECT id, company_id FROM employees WHERE id = ?', (employee_id,)
    ).fetchone()
    if not employee or int(employee['company_id']) != int(company_id):
        raise ValueError('Colaborador não encontrado nesta empresa.')
    normalized_unit_ids = sorted({int(u) for u in (unit_ids or []) if str(u).strip()})
    if not normalized_unit_ids:
        raise ValueError('Selecione ao menos uma unidade.')
    valid_units = {
        int(r['id']) for r in connection.execute(
            'SELECT id FROM units WHERE company_id = ?', (int(company_id),)
        ).fetchall()
    }
    invalid = [u for u in normalized_unit_ids if u not in valid_units]
    if invalid:
        raise ValueError('Unidade(s) fora da empresa: ' + ', '.join(str(u) for u in invalid))
    now = datetime.now(UTC).isoformat()
    created = 0
    for unit_id in normalized_unit_ids:
        exists = connection.execute(
            'SELECT id FROM purchase_role_unit_links WHERE employee_id = ? AND role_type = ? AND unit_id = ?',
            (employee_id, role, unit_id)
        ).fetchone()
        if exists:
            continue
        connection.execute(
            'INSERT INTO purchase_role_unit_links (company_id, employee_id, role_type, unit_id, '
            'created_by_user_id, created_at) VALUES (?, ?, ?, ?, ?, ?)',
            (int(company_id), employee_id, role, unit_id, int(actor['id']), now)
        )
        created += 1
    if created:
        _record_purchase_event(
            connection, int(company_id), 'purchase_function', employee_id, 'function_links_created', '', '',
            f'{created} vínculo(s) de {PURCHASE_FUNCTION_LABELS.get(role, role)} criado(s).',
            int(actor['id']), actor.get('full_name') or '', '', actor.get('role') or '',
        )
    return created


def fetch_user_unit_links(connection, company_id, target_user_id, linked_employee_id=None, is_self=False):
    """Returns unit links for a buyer/approver from purchase_role_unit_links.

    Admin path (is_self=False) returns empty — user_unit_links was dropped in Phase 26.
    """
    if is_self and linked_employee_id:
        rows = connection.execute(
            'SELECT prul.unit_id, u.name AS unit_name FROM purchase_role_unit_links prul '
            'JOIN units u ON u.id = prul.unit_id '
            'WHERE prul.employee_id = ? AND prul.company_id = ? ORDER BY u.name',
            (int(linked_employee_id), company_id),
        ).fetchall()
        return [
            {'unit_id': r['unit_id'], 'unit_name': r['unit_name'],
             'user_id': target_user_id, 'company_id': company_id}
            for r in rows
        ]
    return []


# ── Mutation functions ─────────────────────────────────────────────────────────

def assert_epi_ca_valid_for_purchase(epi):
    """Bloqueia a aquisição de EPI com CA vencido.

    Base legal: NT 146/2015/CGNOR/DSST/SIT (itens 14 a 16) — na compra/aquisição,
    a validade do CA deve ser observada; é vedado adquirir EPI com CA vencido.
    A validação é tolerante a dados ausentes: só bloqueia quando há ``ca_expiry``
    preenchida e já vencida.
    """
    if epi and is_expired(epi.get('ca_expiry')):
        nome = str(epi.get('name') or epi.get('epi_name') or '').strip()
        raise ValueError(
            f"Compra bloqueada: o CA do EPI '{nome}' está vencido em "
            f"{epi.get('ca_expiry')}. Não é permitido adquirir EPI com CA vencido (NT 146/2015)."
        )


def create_purchase_request(connection, actor, unit_id, items, title, notes, ip_address, *, get_epi_by_id_fn):
    """Inserts a new purchase request with items. Returns {ok, id} or {ok, id, duplicate: True}."""
    company_id = int(actor['company_id'])
    now = datetime.now(UTC).isoformat()
    duplicate_id = find_recent_duplicate_purchase_request(connection, actor, unit_id, title, items, now)
    if duplicate_id:
        structured_log('info', 'purchase.request.duplicate_recent_reused', purchase_request_id=duplicate_id, actor_user_id=int(actor['id']))
        return {'ok': True, 'id': duplicate_id, 'duplicate': True}
    cursor = connection.execute(
        "INSERT INTO purchase_requests (company_id, unit_id, status, title, notes, created_by_user_id, created_by_name, created_at, updated_at) VALUES (?, ?, 'open', ?, ?, ?, ?, ?, ?)",
        (company_id, unit_id, title, notes, int(actor['id']), actor['full_name'], now, now)
    )
    pr_id = cursor.lastrowid
    epi_request_ids_to_lock = []
    for item in items:
        epi = get_epi_by_id_fn(connection, int(item['epi_id']))
        if not epi:
            raise ValueError(f"EPI {item['epi_id']} não encontrado.")
        assert_epi_ca_valid_for_purchase(epi)
        connection.execute(
            'INSERT INTO purchase_request_items '
            '(purchase_request_id, company_id, unit_id, epi_id, epi_name, ca, unit_measure, '
            'manufacturer, supplier, glove_size, size, uniform_size, quantity_requested, origin, '
            'employee_id, employee_name, employee_sector, employee_role, epi_request_id, status, notes, created_at, updated_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                pr_id, company_id, unit_id, int(item['epi_id']), epi['name'], epi['ca'], epi['unit_measure'],
                str(item.get('manufacturer') or epi.get('manufacturer') or ''),
                str(item.get('supplier') or epi.get('supplier_company') or ''),
                str(item.get('glove_size') or 'N/A'), str(item.get('size') or 'N/A'), str(item.get('uniform_size') or 'N/A'),
                int(item.get('quantity_requested') or 1), str(item.get('origin') or 'stock_minimum'),
                int(item['employee_id']) if item.get('employee_id') else None,
                str(item.get('employee_name') or ''), str(item.get('employee_sector') or ''), str(item.get('employee_role') or ''),
                int(item['epi_request_id']) if item.get('epi_request_id') else None,
                'included_in_request', str(item.get('notes') or ''), now, now,
            )
        )
        if item.get('epi_request_id'):
            epi_request_ids_to_lock.append(int(item['epi_request_id']))
    for epi_req_id in epi_request_ids_to_lock:
        connection.execute("UPDATE epi_requests SET status = 'em análise', last_updated_at = ? WHERE id = ?", (now, epi_req_id))
    _record_purchase_event(connection, company_id, 'purchase_request', pr_id, 'created', '', 'open', '', int(actor['id']), actor['full_name'], ip_address)
    return {'ok': True, 'id': pr_id}


def review_purchase_request_items(connection, actor, pr, updates, remove_ids, add_items, notes, reason, ip_address, *, get_epi_by_id_fn):
    """Applies requester corrections to PR items. Returns list of affected item ids."""
    pr_id = int(pr['id'])
    now = datetime.now(UTC).isoformat()
    affected = []
    for item in updates or []:
        item_id = int(item.get('id') or 0)
        qty = int(item.get('quantity_requested') or 1)
        if item_id <= 0 or qty <= 0:
            continue
        connection.execute(
            "UPDATE purchase_request_items SET quantity_requested = ?, notes = ?, updated_at = ? "
            "WHERE id = ? AND purchase_request_id = ? AND status NOT IN ('approved', 'ordered', 'received', 'closed')",
            (qty, str(item.get('notes') or '').strip(), now, item_id, pr_id)
        )
        affected.append(item_id)
    if remove_ids:
        placeholders = ','.join('?' for _ in remove_ids)
        connection.execute(
            f"DELETE FROM purchase_request_items WHERE purchase_request_id = ? AND id IN ({placeholders}) "
            f"AND status NOT IN ('approved', 'ordered', 'received', 'closed')",
            (pr_id, *remove_ids)
        )
        affected.extend(remove_ids)
    for item in add_items or []:
        epi = get_epi_by_id_fn(connection, int(item.get('epi_id') or 0))
        if not epi:
            raise ValueError(f"EPI {item.get('epi_id')} não encontrado.")
        assert_epi_ca_valid_for_purchase(epi)
        qty = int(item.get('quantity_requested') or 1)
        if qty <= 0:
            raise ValueError('Quantidade inválida.')
        cursor = connection.execute(
            'INSERT INTO purchase_request_items '
            '(purchase_request_id, company_id, unit_id, epi_id, epi_name, ca, unit_measure, '
            'manufacturer, supplier, glove_size, size, uniform_size, quantity_requested, origin, '
            'employee_id, employee_name, employee_sector, employee_role, epi_request_id, status, notes, created_at, updated_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                pr_id, int(pr['company_id']), int(pr['unit_id']), int(epi['id']), epi['name'], epi['ca'], epi['unit_measure'],
                str(item.get('manufacturer') or epi.get('manufacturer') or ''),
                str(item.get('supplier') or epi.get('supplier_company') or ''),
                str(item.get('glove_size') or 'N/A'), str(item.get('size') or 'N/A'), str(item.get('uniform_size') or 'N/A'),
                qty, str(item.get('origin') or 'manual'),
                int(item['employee_id']) if item.get('employee_id') else None,
                str(item.get('employee_name') or ''), str(item.get('employee_sector') or ''), str(item.get('employee_role') or ''),
                int(item['epi_request_id']) if item.get('epi_request_id') else None,
                'included_in_request', str(item.get('notes') or ''), now, now,
            )
        )
        affected.append(int(cursor.lastrowid))
    connection.execute(
        "UPDATE purchase_requests SET notes = COALESCE(NULLIF(?, ''), notes), updated_at = ? WHERE id = ?",
        (notes, now, pr_id)
    )
    _record_purchase_event(
        connection, int(pr['company_id']), 'purchase_request', pr_id, 'requester_review_saved',
        str(pr['status']), str(pr['status']),
        'Itens afetados: ' + ', '.join(str(iid) for iid in affected),
        int(actor['id']), actor['full_name'], ip_address,
        actor.get('role') or '', reason, 'requester',
    )
    return affected


_PRICES_LOCKED_ITEM_STATUSES = ('approved', 'ordered', 'received', 'closed')
_PRICES_LOCKED_PR_STATUSES = {
    'approved', 'partially_approved', 'po_generated', 'received', 'checked', 'closed', 'cancelled',
}


def save_purchase_request_prices(connection, actor, pr, price_updates, ip_address):
    """Salva preços/quantidades cotados nos itens da requisição, sem gerar PO.

    Move a requisição para 'quoted' (Cotada). Preserva a regra R1: itens já
    aprovados/pedidos/recebidos/fechados não são alterados. Retorna
    (itens_afetados, novo_status).
    """
    pr_id = int(pr['id'])
    if str(pr['status']) in _PRICES_LOCKED_PR_STATUSES:
        raise ValueError('Requisição já avançou além da cotação; não é possível salvar preços.')
    now = datetime.now(UTC).isoformat()
    locked = ', '.join(f"'{s}'" for s in _PRICES_LOCKED_ITEM_STATUSES)
    affected = []
    for raw in price_updates or []:
        item_id = int(raw.get('item_id') or 0)
        if item_id <= 0:
            continue
        unit_price = float(raw.get('unit_price') or 0)
        if unit_price < 0:
            raise ValueError('Preço unitário inválido.')
        current = connection.execute(
            'SELECT id, quantity_requested, status FROM purchase_request_items '
            'WHERE id = ? AND purchase_request_id = ?',
            (item_id, pr_id)
        ).fetchone()
        if not current:
            continue
        if str(current['status']) in _PRICES_LOCKED_ITEM_STATUSES:
            continue  # R1: item aprovado é imutável
        if raw.get('quantity') is not None and str(raw.get('quantity')).strip() != '':
            quantity = int(raw.get('quantity'))
            if quantity <= 0:
                raise ValueError('Quantidade inválida.')
        else:
            quantity = int(current['quantity_requested'] or 1)
        total_price = round(unit_price * quantity, 2)
        connection.execute(
            'UPDATE purchase_request_items SET unit_price = ?, total_price = ?, quantity_requested = ?, '
            f"updated_at = ? WHERE id = ? AND purchase_request_id = ? AND status NOT IN ({locked})",
            (unit_price, total_price, quantity, now, item_id, pr_id)
        )
        affected.append(item_id)
    if not affected:
        raise ValueError('Nenhum item elegível para atualização de preços.')
    new_status = 'quoted'
    connection.execute(
        'UPDATE purchase_requests SET status = ?, updated_at = ? WHERE id = ?',
        (new_status, now, pr_id)
    )
    _record_purchase_event(
        connection, int(pr['company_id']), 'purchase_request', pr_id, 'prices_saved',
        str(pr['status']), new_status,
        f'Preços salvos em {len(affected)} item(ns) via importação de cotação.',
        int(actor['id']), actor['full_name'], ip_address,
        actor.get('role') or '', '', 'buyer',
    )
    return affected, new_status


_PURCHASE_REQUEST_VALID_STATUSES = {
    'draft', 'open', 'sent_to_buyer', 'quoted', 'pending_approval', 'partially_approved',
    'approved', 'rejected', 'returned_to_buyer', 'waiting_buyer_correction', 'buyer_resubmitted',
    'waiting_requester_correction', 'requester_resubmitted', 'postponed', 'po_generated',
    'received', 'checked', 'closed', 'cancelled',
}


def update_purchase_request_status(connection, actor, pr, new_status, comment, postponed_until, received_items_payload, ip_address):
    """Updates PR status with optional item-level logic.

    Returns ``{'stock_entries': int, 'qr_labels': list, 'pendencies': list}``:
    the count of units auto-added to stock, the QR labels generated for them and
    the partial-receipt pendencies opened for the buyer (all empty unless the
    transition received -> checked actually feeds stock / has shortfalls).
    """
    if new_status not in _PURCHASE_REQUEST_VALID_STATUSES:
        raise ValueError('Status inválido para requisição de compra.')
    pr_id = int(pr['id'])
    old_status = str(pr['status'])
    now = datetime.now(UTC).isoformat()
    extra = {}
    if new_status == 'sent_to_buyer':
        extra['sent_to_buyer_at'] = now
    elif new_status in ('closed', 'cancelled'):
        extra['closed_at'] = now
    elif new_status == 'postponed' and postponed_until:
        extra['postponed_until'] = postponed_until
    set_clause = ', '.join([f'{k} = ?' for k in ['status', 'updated_at', *extra.keys()]])
    connection.execute(
        f'UPDATE purchase_requests SET {set_clause} WHERE id = ?',
        [new_status, now, *extra.values(), pr_id]
    )
    stock_entries = 0
    qr_labels = []
    pendencies = []
    if new_status == 'closed':
        connection.execute(
            "UPDATE purchase_request_items SET status = 'closed', updated_at = ? WHERE purchase_request_id = ?",
            (now, pr_id)
        )
    elif new_status == 'checked':
        if received_items_payload:
            for item_data in received_items_payload:
                item_id = int(str(item_data.get('id') or '').strip() or '0')
                if not item_id:
                    continue
                item_status = 'received' if item_data.get('received') else 'not_received'
                connection.execute(
                    'UPDATE purchase_request_items SET status = ?, updated_at = ? WHERE id = ? AND purchase_request_id = ?',
                    (item_status, now, item_id, pr_id)
                )
        else:
            connection.execute(
                "UPDATE purchase_request_items SET status = 'checked', updated_at = ? "
                "WHERE purchase_request_id = ? AND status NOT IN ('not_received', 'closed')",
                (now, pr_id)
            )
        if old_status == 'received':
            stock_entries, qr_labels = _auto_add_received_items_to_stock(
                connection, pr_id, received_items_payload, int(actor['id']), actor['full_name'], now
            )
            pendencies = _record_partial_receipt_pendencies(
                connection, pr, received_items_payload, int(actor['id']), actor['full_name'], now, ip_address
            )
    elif new_status == 'received':
        connection.execute(
            "UPDATE purchase_request_items SET status = 'received', updated_at = ? "
            "WHERE purchase_request_id = ? AND status = 'included_in_request'",
            (now, pr_id)
        )
    _record_purchase_event(
        connection, int(pr['company_id']), 'purchase_request', pr_id, 'status_changed',
        old_status, new_status, comment, int(actor['id']), actor['full_name'], ip_address
    )
    return {'stock_entries': stock_entries, 'qr_labels': qr_labels, 'pendencies': pendencies}


# O vocabulário e as transições vivem em modules/epis/request_states.py. Aqui
# ficava um *conjunto*: validava o destino e ignorava a origem, então
# `solicitado → entregue` passava.
from modules.epis.request_states import (  # noqa: E402
    InvalidStatusTransition as _InvalidStatusTransition,
    assert_transition as _assert_epi_request_transition,
)


def update_epi_request_status(connection, actor, req, new_status, postponed_until, rejection_reason, notes):
    """Updates a single epi_request status and inserts a history record."""
    try:
        new_status = _assert_epi_request_transition(req.get('status'), new_status)
    except _InvalidStatusTransition as exc:
        raise ValueError(str(exc)) from exc
    if new_status == 'prorrogado' and not postponed_until:
        raise ValueError('Data de prorrogação obrigatória.')
    now = datetime.now(UTC).isoformat()
    connection.execute(
        "UPDATE epi_requests "
        "SET status = ?, approver_user_id = ?, approver_name = ?, "
        "approved_at = CASE WHEN ? IN ('aprovado','rejeitado','prorrogado') THEN ? ELSE approved_at END, "
        "rejection_reason = CASE WHEN ? = 'rejeitado' THEN ? ELSE rejection_reason END, "
        "postponed_until = CASE WHEN ? = 'prorrogado' THEN ? ELSE postponed_until END, "
        "last_updated_at = ? WHERE id = ?",
        (
            new_status, int(actor['id']), actor['full_name'],
            new_status, now,
            new_status, rejection_reason,
            new_status, postponed_until,
            now, int(req['id']),
        )
    )
    connection.execute(
        'INSERT INTO epi_request_history (request_id, company_id, status, notes, actor_user_id, actor_name, created_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?)',
        (int(req['id']), int(req['company_id']), new_status, notes, int(actor['id']), actor['full_name'], now)
    )


def bulk_update_epi_request_statuses(connection, actor, updates, *, actor_operational_unit_id=None):
    """Bulk-updates epi_request statuses, skipping missing or invalid records."""
    now = datetime.now(UTC).isoformat()
    scope_unit_id = actor_operational_unit_id(connection, actor) if actor_operational_unit_id is not None else None
    for upd in updates or []:
        _req = connection.execute('SELECT * FROM epi_requests WHERE id = ?', (int(upd['request_id']),)).fetchone()
        if not _req:
            continue
        req = row_to_dict(_req)
        ensure_resource_company(actor, req, 'Solicitação')
        if actor_operational_unit_id is not None and actor.get('role') in ('admin', 'user') and (not scope_unit_id or int(req['unit_id']) != int(scope_unit_id)):
            raise PermissionError('Solicitação fora da unidade operacional do usuário.')
        # O bulk pula item inválido em vez de abortar o lote — contrato
        # existente, agora aplicado também à transição, não só ao destino.
        try:
            new_status = _assert_epi_request_transition(
                req.get('status'), upd.get('status', ''),
            )
        except _InvalidStatusTransition:
            continue
        postponed_until = str(upd.get('postponed_until') or '').strip()
        rejection_reason = str(upd.get('rejection_reason') or '').strip()
        connection.execute(
            "UPDATE epi_requests "
            "SET status = ?, approver_user_id = ?, approver_name = ?, "
            "approved_at = CASE WHEN ? IN ('aprovado','rejeitado','prorrogado') THEN ? ELSE approved_at END, "
            "rejection_reason = CASE WHEN ? = 'rejeitado' THEN ? ELSE rejection_reason END, "
            "postponed_until = CASE WHEN ? = 'prorrogado' THEN ? ELSE postponed_until END, "
            "last_updated_at = ? WHERE id = ?",
            (
                new_status, int(actor['id']), actor['full_name'],
                new_status, now,
                new_status, rejection_reason,
                new_status, postponed_until,
                now, int(req['id']),
            )
        )
        connection.execute(
            'INSERT INTO epi_request_history (request_id, company_id, status, notes, actor_user_id, actor_name, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?)',
            (int(req['id']), int(req['company_id']), new_status, str(upd.get('notes') or '').strip(), int(actor['id']), actor['full_name'], now)
        )


def update_feedback_status(connection, actor, feedback, status, notes):
    """Updates epi_feedback status and inserts a history record."""
    valid_status = {'pendente', 'em análise', 'aprovada', 'rejeitada', 'arquivada'}
    if status not in valid_status:
        raise ValueError('Status inválido para avaliação.')
    now = datetime.now(UTC).isoformat()
    connection.execute(
        'UPDATE epi_feedbacks '
        'SET status = ?, reviewer_user_id = ?, reviewer_name = ?, reviewed_at = ?, updated_at = ? '
        'WHERE id = ?',
        (status, int(actor['id']), actor['full_name'], now, now, int(feedback['id']))
    )
    connection.execute(
        'INSERT INTO epi_feedback_history (feedback_id, company_id, status, notes, actor_user_id, actor_name, created_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?)',
        (int(feedback['id']), int(feedback['company_id']), status, notes, int(actor['id']), actor['full_name'], now)
    )


def upsert_authorized_supplier(connection, company_id, supplier_id, name, cnpj, category, contact_email, notes):
    """Updates authorized supplier fields. Returns False if not found, True on success."""
    existing = connection.execute(
        'SELECT id FROM authorized_suppliers WHERE id = ? AND company_id = ?',
        (supplier_id, company_id)
    ).fetchone()
    if not existing:
        return False
    now = datetime.now(UTC).isoformat()
    connection.execute(
        'UPDATE authorized_suppliers SET name = ?, cnpj = ?, category = ?, contact_email = ?, notes = ?, updated_at = ? WHERE id = ?',
        (name, cnpj, category, contact_email, notes, now, supplier_id)
    )
    return True


def delete_purchase_function_link(connection, company_id, link_id):
    """Deletes a purchase_role_unit_link. Raises ValueError/PermissionError on failure."""
    link = connection.execute('SELECT * FROM purchase_role_unit_links WHERE id = ?', (link_id,)).fetchone()
    if not link:
        raise ValueError('Vínculo de compras não encontrado.')
    if int(link['company_id']) != company_id:
        raise PermissionError('Vínculo pertence a outra empresa.')
    connection.execute('DELETE FROM purchase_role_unit_links WHERE id = ?', (link_id,))


def delete_user_unit_link(connection, company_id, link_id):
    """Deprecated: user_unit_links was removed in Phase 26. Raises ValueError."""
    raise ValueError('user_unit_links foi removida. Use purchase_role_unit_links.')


# ── Route-level SQL extractions ───────────────────────────────────────────────

def get_purchase_request_by_id(connection, pr_id):
    row = connection.execute('SELECT * FROM purchase_requests WHERE id = ?', (int(pr_id),)).fetchone()
    return dict(row) if row else None


def get_epi_request_by_id(connection, request_id):
    row = connection.execute('SELECT * FROM epi_requests WHERE id = ?', (int(request_id),)).fetchone()
    return dict(row) if row else None


def get_epi_feedback_by_id(connection, feedback_id):
    row = connection.execute('SELECT * FROM epi_feedbacks WHERE id = ?', (int(feedback_id),)).fetchone()
    return dict(row) if row else None


# ── Ordens de Compra (PO): leitura e mutações ─────────────────────────────────

def get_purchase_order_by_id(connection, po_id):
    row = connection.execute('SELECT * FROM purchase_orders WHERE id = ?', (int(po_id),)).fetchone()
    return row_to_dict(row) if row else None


def ensure_purchase_order_action_scope(connection, actor, po, *, actor_operational_unit_id=None):
    """Garante que o ator pode agir sobre a PO (empresa + unidade de compras)."""
    ensure_resource_company(actor, po, 'PO')
    if actor.get('role') == 'master_admin':
        return
    scope_unit_id = actor_operational_unit_id(connection, actor) if actor_operational_unit_id is not None else None
    if actor_operational_unit_id is not None and actor.get('role') in ('admin', 'user'):
        if not scope_unit_id:
            raise PermissionError('Seu perfil não possui unidade operacional ativa.')
        if int(po['unit_id']) != int(scope_unit_id):
            raise PermissionError('PO fora da unidade operacional do usuário.')
    if actor.get('role') in ('buyer', 'approver'):
        purchase_scope_units = get_actor_purchase_unit_scope(connection, actor)
        if not purchase_scope_units:
            raise PermissionError('Usuário sem unidade de compras vinculada.')
        if int(po['unit_id']) not in {int(uid) for uid in purchase_scope_units}:
            raise PermissionError('PO fora das unidades de compras vinculadas ao usuário.')


def _po_company_approval_threshold(connection, company_id):
    config = get_company_purchase_config(connection, int(company_id))
    raw = config.get('po_approval_threshold') if isinstance(config, dict) else 0
    try:
        return float(raw or 0)
    except (TypeError, ValueError):
        return 0.0


def _resolve_order_legal_entity(connection, company_id, payload):
    """CNPJ emissor do pedido de compra.

    Ausente ⇒ ``None`` (pedido da empresa, comportamento histórico). Quando
    informado, precisa existir, pertencer à empresa e estar ativo. Devolve
    ``None`` também enquanto o schema Multi-CNPJ não estiver provisionado.
    """
    requested = (payload or {}).get('legal_entity_id')
    if requested in (None, '', 0, '0'):
        return None
    from epi_backend.db import table_columns
    from modules.legal_entities.service import get_legal_entity_by_id, legal_entities_ready
    if not legal_entities_ready(connection):
        return None
    if 'legal_entity_id' not in table_columns(connection, 'purchase_orders'):
        return None
    entity = get_legal_entity_by_id(connection, int(requested))
    if not entity or int(entity['company_id']) != int(company_id):
        raise ValueError('CNPJ informado não pertence a esta empresa.')
    if not int(entity.get('active', 1)):
        raise ValueError('CNPJ informado está inativo.')
    return int(requested)


def create_purchase_order(connection, actor, payload, ip_address, *, get_epi_by_id_fn=None):
    unit_id = int(payload.get('unit_id') or 0)
    if not unit_id:
        raise ValueError('Unidade é obrigatória para criar a PO.')
    unit = get_unit_by_id(connection, unit_id)
    if not unit:
        raise ValueError('Unidade não encontrada.')
    ensure_resource_company(actor, unit, 'Unidade')
    items = payload.get('items') or []
    if not items:
        raise ValueError('A PO precisa ter pelo menos um item.')

    company_id = int(actor['company_id']) if actor.get('role') != 'master_admin' else int(unit['company_id'])
    pr_id = int(payload['purchase_request_id']) if payload.get('purchase_request_id') else 0
    if pr_id:
        pr = get_purchase_request_by_id(connection, pr_id)
        if not pr:
            raise ValueError('Requisição vinculada não encontrada.')
        ensure_resource_company(actor, pr, 'Requisição')
        approved_purchase_request_items_for_po(connection, pr_id, items)

    now = datetime.now(UTC).isoformat()
    po_number = str(payload.get('po_number') or '').strip() or generate_po_number(connection, company_id)
    supplier = str(payload.get('supplier') or '').strip()
    supplier_cnpj = ''.join(ch for ch in str(payload.get('supplier_cnpj') or '') if ch.isdigit())
    notes = str(payload.get('notes') or '').strip()
    expected_delivery = str(payload.get('expected_delivery_date') or '').strip()

    total_value = 0.0
    normalized_items = []
    for raw in items:
        epi_id = int(raw.get('epi_id') or 0)
        if not epi_id:
            raise ValueError('Item da PO sem EPI válido.')
        if get_epi_by_id_fn:
            assert_epi_ca_valid_for_purchase(get_epi_by_id_fn(connection, epi_id))
        quantity = int(raw.get('quantity') or raw.get('quantity_requested') or 1)
        unit_price = float(raw.get('unit_price') or 0)
        total_price = round(unit_price * quantity, 2)
        total_value += total_price
        normalized_items.append({
            'purchase_request_item_id': int(raw['purchase_request_item_id']) if raw.get('purchase_request_item_id') else None,
            'epi_id': epi_id,
            'epi_name': str(raw.get('epi_name') or raw.get('epi_display_name') or '').strip(),
            'ca': str(raw.get('ca') or '').strip(),
            'unit_measure': str(raw.get('unit_measure') or '').strip(),
            'manufacturer': str(raw.get('manufacturer') or '').strip(),
            'supplier': str(raw.get('supplier') or supplier).strip(),
            'glove_size': str(raw.get('glove_size') or 'N/A'),
            'size': str(raw.get('size') or 'N/A'),
            'uniform_size': str(raw.get('uniform_size') or 'N/A'),
            'quantity': quantity,
            'unit_price': unit_price,
            'total_price': total_price,
            'origin': str(raw.get('origin') or 'stock_minimum'),
            'employee_name': str(raw.get('employee_name') or '').strip(),
            'employee_sector': str(raw.get('employee_sector') or '').strip(),
            'employee_role': str(raw.get('employee_role') or '').strip(),
        })

    # CNPJ emissor do pedido: escolha explícita no momento da emissão (não é
    # derivável como nas entregas). Ausente = pedido da empresa (histórico).
    po_columns = [
        'purchase_request_id', 'company_id', 'unit_id', 'po_number', 'supplier', 'supplier_cnpj',
        'expected_delivery_date', 'notes', 'total_value', 'created_by_user_id', 'created_by_name',
        'created_at', 'updated_at',
    ]
    po_values = [
        pr_id or None, company_id, unit_id, po_number, supplier, supplier_cnpj,
        expected_delivery, notes, round(total_value, 2),
        int(actor['id']), actor.get('full_name') or '', now, now,
    ]
    order_legal_entity_id = _resolve_order_legal_entity(connection, company_id, payload)
    if order_legal_entity_id is not None:
        po_columns.append('legal_entity_id')
        po_values.append(order_legal_entity_id)
    placeholders = ', '.join(['?'] * len(po_values))
    cursor = connection.execute(
        f"INSERT INTO purchase_orders (status, {', '.join(po_columns)}) "  # noqa: S608
        f"VALUES ('waiting_admin_review', {placeholders})",
        tuple(po_values)
    )
    po_id = int(cursor.lastrowid)
    for item in normalized_items:
        connection.execute(
            'INSERT INTO purchase_order_items ('
            'purchase_order_id, purchase_request_item_id, company_id, unit_id, epi_id, epi_name, ca, '
            'unit_measure, manufacturer, supplier, glove_size, size, uniform_size, quantity, quantity_approved, '
            'unit_price, total_price, origin, employee_name, employee_sector, employee_role, status, created_at, updated_at'
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, 'open', ?, ?)",
            (
                po_id, item['purchase_request_item_id'], company_id, unit_id, item['epi_id'], item['epi_name'],
                item['ca'], item['unit_measure'], item['manufacturer'], item['supplier'], item['glove_size'],
                item['size'], item['uniform_size'], item['quantity'], item['unit_price'], item['total_price'],
                item['origin'], item['employee_name'], item['employee_sector'], item['employee_role'], now, now,
            )
        )

    if pr_id:
        connection.execute(
            'UPDATE purchase_requests SET linked_po_id = ?, linked_po_number = ?, status = ?, updated_at = ? WHERE id = ?',
            (po_id, po_number, 'po_generated', now, pr_id)
        )

    _record_purchase_event(
        connection, company_id, 'purchase_order', po_id, 'created', '', 'waiting_admin_review',
        notes, int(actor['id']), actor.get('full_name') or '', ip_address, actor.get('role') or '',
    )
    return {'ok': True, 'id': po_id, 'po_number': po_number, 'status': 'waiting_admin_review'}


def review_purchase_order(connection, actor, po, decision, comment, ip_address):
    next_status = assert_review_allowed(po['status'], decision)
    now = datetime.now(UTC).isoformat()
    comment = str(comment or '').strip()
    if decision == 'returned_with_suggestions' and not comment:
        raise ValueError('Informe as sugestões para devolver ao comprador.')
    company_id = int(po['company_id'])
    if decision == 'returned_with_suggestions':
        connection.execute(
            'UPDATE purchase_orders SET status = ?, buyer_suggestions = ?, admin_review_by_user_id = ?, '
            'admin_review_by_name = ?, admin_review_at = ?, admin_review_comment = ?, updated_at = ? WHERE id = ?',
            (next_status, comment, int(actor['id']), actor.get('full_name') or '', now, comment, now, int(po['id']))
        )
    else:
        connection.execute(
            'UPDATE purchase_orders SET status = ?, admin_review_by_user_id = ?, admin_review_by_name = ?, '
            'admin_review_at = ?, admin_review_comment = ?, updated_at = ? WHERE id = ?',
            (next_status, int(actor['id']), actor.get('full_name') or '', now, comment, now, int(po['id']))
        )
    _record_purchase_event(
        connection, company_id, 'purchase_order', int(po['id']), 'admin_review', po['status'], next_status,
        comment, int(actor['id']), actor.get('full_name') or '', ip_address, actor.get('role') or '',
        destination='buyer' if decision == 'returned_with_suggestions' else 'approver',
    )
    return {'ok': True, 'status': next_status}


def resubmit_purchase_order(connection, actor, po, notes, ip_address):
    next_status = assert_resubmit_allowed(po['status'])
    now = datetime.now(UTC).isoformat()
    connection.execute(
        'UPDATE purchase_orders SET status = ?, updated_at = ? WHERE id = ?',
        (next_status, now, int(po['id']))
    )
    _record_purchase_event(
        connection, int(po['company_id']), 'purchase_order', int(po['id']), 'buyer_resubmit',
        po['status'], next_status, str(notes or '').strip(), int(actor['id']), actor.get('full_name') or '',
        ip_address, actor.get('role') or '', destination='admin',
    )
    return {'ok': True, 'status': next_status}


def _apply_po_item_approval_decisions(connection, po_id, decisions, now):
    """Aplica decisões por item (quantity_approved + status). Retorna contadores."""
    rows = connection.execute(
        'SELECT id, quantity FROM purchase_order_items WHERE purchase_order_id = ?', (int(po_id),)
    ).fetchall()
    item_map = {int(r['id']): int(r['quantity'] or 0) for r in rows}
    if not decisions:
        # Aprovação total: todos os itens com quantidade integral.
        for item_id, qty in item_map.items():
            connection.execute(
                "UPDATE purchase_order_items SET quantity_approved = ?, status = 'approved', updated_at = ? WHERE id = ?",
                (qty, now, item_id)
            )
        return len(item_map), 0
    approved_count = 0
    rejected_count = 0
    for decision in decisions:
        item_id = int(decision.get('item_id') or decision.get('id') or 0)
        if item_id not in item_map:
            raise ValueError(f'Item {item_id} não pertence à PO.')
        approved = bool(decision.get('approved'))
        if approved:
            connection.execute(
                "UPDATE purchase_order_items SET quantity_approved = ?, status = 'approved', updated_at = ? WHERE id = ?",
                (item_map[item_id], now, item_id)
            )
            approved_count += 1
        else:
            reason = str(decision.get('rejection_reason') or decision.get('reason') or '').strip()
            if not reason:
                raise ValueError('Selecione o motivo para cada item reprovado.')
            if reason not in PURCHASE_APPROVAL_REJECTION_REASONS:
                raise ValueError('Motivo de reprovação do item inválido.')
            connection.execute(
                "UPDATE purchase_order_items SET quantity_approved = 0, status = 'rejected', updated_at = ? WHERE id = ?",
                (now, item_id)
            )
            rejected_count += 1
    return approved_count, rejected_count


def approve_purchase_order(connection, actor, po, decision, comment, decisions, postponed_until, ip_address):
    assert_approval_allowed(po['status'], decision)
    decision = str(decision or '').strip()
    comment = str(comment or '').strip()
    now = datetime.now(UTC).isoformat()
    company_id = int(po['company_id'])
    po_id = int(po['id'])

    if decision == 'rejected' and not comment:
        raise ValueError('Comentário obrigatório para rejeição.')
    if decision == 'postponed':
        postponed_until = str(postponed_until or '').strip()
        if not postponed_until:
            raise ValueError('Data de prorrogação obrigatória.')

    prior_approver_ids = {
        int(r['actor_user_id']) for r in connection.execute(
            "SELECT actor_user_id FROM purchase_approvals "
            "WHERE purchase_order_id = ? AND decision IN ('approved', 'partially_approved')",
            (po_id,)
        ).fetchall()
    }
    prior_approvals = len(prior_approver_ids)

    # Segundo nível (acima do limite): exige permissão financeira e segregação
    # de funções — o aprovador final deve ser diferente do primeiro nível.
    if decision in ('approved', 'partially_approved') and prior_approvals >= 1:
        ensure_permission(actor, PERM_FINANCE_VIEW)
        if int(actor['id']) in prior_approver_ids:
            raise PermissionError('O segundo nível de aprovação exige um aprovador diferente do primeiro.')

    threshold = _po_company_approval_threshold(connection, company_id)
    next_status, finalizes = resolve_approval_outcome(
        decision, prior_approvals=prior_approvals, total_value=po.get('total_value'), threshold=threshold,
    )

    if decision in ('approved', 'partially_approved') and finalizes:
        _apply_po_item_approval_decisions(connection, po_id, decisions if decision == 'partially_approved' else None, now)

    # Registra a decisão de nível na tabela de aprovações (auditoria multi-nível).
    connection.execute(
        'INSERT INTO purchase_approvals (purchase_order_id, company_id, decision, comment, actor_user_id, actor_name, created_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?)',
        (po_id, company_id, decision, comment, int(actor['id']), actor.get('full_name') or '', now)
    )

    if decision in ('approved', 'partially_approved') and finalizes:
        connection.execute(
            'UPDATE purchase_orders SET status = ?, approved_by_user_id = ?, approved_by_name = ?, '
            'approved_at = ?, approval_comment = ?, updated_at = ? WHERE id = ?',
            (next_status, int(actor['id']), actor.get('full_name') or '', now, comment, now, po_id)
        )
    elif decision == 'postponed':
        connection.execute(
            'UPDATE purchase_orders SET status = ?, postponed_until = ?, updated_at = ? WHERE id = ?',
            (next_status, postponed_until, now, po_id)
        )
    else:
        connection.execute(
            'UPDATE purchase_orders SET status = ?, approval_comment = ?, updated_at = ? WHERE id = ?',
            (next_status, comment, now, po_id)
        )

    _record_purchase_event(
        connection, company_id, 'purchase_order', po_id, decision, po['status'], next_status,
        comment, int(actor['id']), actor.get('full_name') or '', ip_address, actor.get('role') or '',
        destination='buyer' if next_status in ('approved', 'partially_approved') else 'closed',
    )
    pending_next_level = (decision in ('approved', 'partially_approved') and not finalizes)
    return {'ok': True, 'status': next_status, 'pending_next_level': pending_next_level}


def _add_po_received_items_to_stock(connection, po, actor, now):
    """Lança no estoque os itens recebidos da PO (na conferência)."""
    from modules.deliveries.service import ensure_stock_movement_size_columns
    po_id = int(po['id'])
    rows = [row_to_dict(r) for r in connection.execute(
        'SELECT * FROM purchase_order_items WHERE purchase_order_id = ?', (po_id,)
    ).fetchall()]
    ensure_stock_movement_size_columns(connection)
    total_units = 0
    for item in rows:
        quantity = int(item.get('quantity_received') or 0)
        if quantity <= 0:
            continue
        epi_id = int(item['epi_id'])
        unit_id = int(item['unit_id'])
        company_id = int(item['company_id'])
        glove_size = str(item.get('glove_size') or 'N/A')
        size = str(item.get('size') or 'N/A')
        uniform_size = str(item.get('uniform_size') or 'N/A')
        stock_row = get_unit_stock(connection, company_id, unit_id, epi_id)
        previous_stock = int((stock_row or {}).get('quantity') or 0)
        new_stock = previous_stock + quantity
        movement_cursor = connection.execute(
            'INSERT INTO stock_movements ('
            'company_id, unit_id, epi_id, movement_type, quantity, previous_stock, new_stock, '
            'source_type, source_id, notes, actor_user_id, actor_name, created_at, glove_size, size, uniform_size'
            ') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                company_id, unit_id, epi_id, 'in', quantity, previous_stock, new_stock,
                'purchase_order', po_id,
                f'Entrada automática — Conferência PO {po.get("po_number") or po_id}',
                int(actor['id']), actor.get('full_name') or '', now, glove_size, size, uniform_size
            )
        )
        movement_id = int(movement_cursor.lastrowid)
        upsert_unit_stock(connection, company_id, unit_id, epi_id, new_stock)
        for _ in range(quantity):
            seq_value = next_company_qr_sequence(connection, company_id)
            qr_value = build_stock_item_qr(company_id, unit_id, seq_value)
            connection.execute(
                'INSERT INTO epi_stock_items ('
                'company_id, unit_id, epi_id, glove_size, size, uniform_size, qr_sequence, qr_code_value, status, '
                'stock_movement_id, lot_code, manufacture_date, label_measure, label_printer_name, label_print_format, '
                'generated_by_user_id, created_at, updated_at'
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'in_stock', ?, '', '', 'unidade', '', '', ?, ?, ?)",
                (
                    company_id, unit_id, epi_id, glove_size, size, uniform_size,
                    seq_value, qr_value, movement_id, int(actor['id']), now, now
                )
            )
        total_units += quantity
    return total_units


def receive_purchase_order(connection, actor, po, action, items, notes, ip_address):
    action = assert_receive_allowed(po['status'], action)
    now = datetime.now(UTC).isoformat()
    company_id = int(po['company_id'])
    po_id = int(po['id'])
    notes = str(notes or '').strip()
    stock_units = 0

    if action in ('received', 'received_partial'):
        po_items_by_id = {int(r['id']): row_to_dict(r) for r in connection.execute(
            'SELECT id, epi_id FROM purchase_order_items WHERE purchase_order_id = ?', (po_id,)
        ).fetchall()}
        valid_ids = set(po_items_by_id.keys())
        # Validade do fabricante por lote (NT 146/2015): a primeira data de um
        # mesmo EPI vale para os demais itens daquele EPI. Persistimos no EPI já
        # no recebimento para que nenhum item entre em estoque sem essa data.
        validity_by_item = {}
        for entry in items or []:
            eid = int(entry.get('id') or 0)
            d = str(entry.get('manufacturer_validity_date') or '').strip()
            if eid and d:
                validity_by_item[eid] = d
        validity_by_epi = {}
        for iid, row in po_items_by_id.items():
            d = validity_by_item.get(iid)
            if d and int(row['epi_id']) not in validity_by_epi:
                validity_by_epi[int(row['epi_id'])] = d
        for entry in items or []:
            item_id = int(entry.get('id') or 0)
            if item_id not in valid_ids:
                raise ValueError(f'Item {item_id} não pertence à PO.')
            qty = max(0, int(entry.get('quantity_received') or 0))
            connection.execute(
                "UPDATE purchase_order_items SET quantity_received = ?, status = 'received', updated_at = ? WHERE id = ?",
                (qty, now, item_id)
            )
            epi_id_for_item = int(po_items_by_id[item_id]['epi_id'])
            manufacturer_validity = str(
                validity_by_item.get(item_id) or validity_by_epi.get(epi_id_for_item) or ''
            ).strip()
            if manufacturer_validity and qty > 0:
                connection.execute(
                    'UPDATE epis SET epi_validity_date = ? WHERE id = ?',
                    (manufacturer_validity, epi_id_for_item)
                )
        connection.execute(
            'UPDATE purchase_orders SET status = ?, received_by_user_id = ?, received_by_name = ?, '
            'received_at = ?, updated_at = ? WHERE id = ?',
            (action, int(actor['id']), actor.get('full_name') or '', now, now, po_id)
        )
        new_status = action
    elif action == 'checked':
        stock_units = _add_po_received_items_to_stock(connection, po, actor, now)
        connection.execute(
            'UPDATE purchase_orders SET status = ?, checked_at = ?, updated_at = ? WHERE id = ?',
            ('checked', now, now, po_id)
        )
        new_status = 'checked'
    else:  # closed
        connection.execute(
            'UPDATE purchase_orders SET status = ?, closed_at = ?, updated_at = ? WHERE id = ?',
            ('closed', now, now, po_id)
        )
        new_status = 'closed'

    _record_purchase_event(
        connection, company_id, 'purchase_order', po_id, action, po['status'], new_status,
        notes, int(actor['id']), actor.get('full_name') or '', ip_address, actor.get('role') or '',
    )
    return {'ok': True, 'status': new_status, 'stock_units': stock_units}


def add_purchase_order_file(connection, actor, po, file_name, file_type, file_data, ip_address):
    now = datetime.now(UTC).isoformat()
    company_id = int(po['company_id'])
    cursor = connection.execute(
        'INSERT INTO purchase_order_files ('
        'purchase_order_id, company_id, file_name, file_type, file_data, uploaded_by_user_id, uploaded_by_name, created_at'
        ') VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (
            int(po['id']), company_id, str(file_name or '').strip(), str(file_type or '').strip(),
            str(file_data or ''), int(actor['id']), actor.get('full_name') or '', now,
        )
    )
    _record_purchase_event(
        connection, company_id, 'purchase_order', int(po['id']), 'file_uploaded', po['status'], po['status'],
        str(file_name or ''), int(actor['id']), actor.get('full_name') or '', ip_address, actor.get('role') or '',
    )
    return {'ok': True, 'id': int(cursor.lastrowid)}
