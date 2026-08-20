"""Resumo do Dashboard calculado no SERVIDOR (fatia 1.1D-B).

Hoje o Dashboard não tem rota. O `DashboardCubit` baixa `/api/bootstrap`
inteiro — colaboradores, entregas, EPIs, usuários, empresas, logs de auditoria
— e recomputa os quatro KPIs em Dart, refazendo no cliente o recorte por
CNPJ/Unidade/Setor. O Web Legado faz o mesmo em `dashboard.js`, com outro
código. São duas reimplementações da mesma regra, e elas já divergiram.

O problema não é só duplicação. Três consequências concretas:

1. **`criticalStock` era corporativo.** O Cubit conta `Epi.isCriticalStock`, ou
   seja `stockQuantity <= minimumStock` — saldo da EMPRESA contra o mínimo da
   EMPRESA. Nenhum dos dois é da Unidade que o operador está olhando.
2. **`locked` era deduzido no cliente** (`role == 'admin' || role == 'user'`).
   Autorização espelhada em Dart e em JS envelhece separada do servidor.
3. **Os setores eram derivados varrendo `bootstrap.employees`** — o cliente
   baixava a lista inteira de pessoas para preencher um dropdown.

Esta fatia move os quatro KPIs, o escopo e as fontes do filtro para o servidor.
Ela **não migra nenhum consumidor**: `DashboardCubit` e `dashboard.js` seguem
lendo o bootstrap, e nenhum campo é removido de lá. A troca dos clientes é a
fatia 1.1D-C.

Equivalência
------------
`deliveries_today`, `expiring_epis` e `pending_purchases` reproduzem o
comportamento atual e são provados equivalentes por teste.

`critical_stock` **muda de propósito**, e não se tenta casar com o número
antigo: passa a ser `unit_stock_quantity <= unit_minimum_stock` (fonte da fatia
1.1D-B0). O KPI antigo respondia "o total da empresa está baixo?"; o novo
responde "falta EPI NESTA Unidade?" — que é a pergunta que o operador faz
olhando para o Dashboard dela.

`alerts` e `compliance` são repassados sem tocar na regra. A regra de `alerts`
ainda cruza saldo local com mínimo corporativo e está errada — a correção está
rastreada e deliberadamente fora desta fatia.
"""

from datetime import date, datetime, timedelta, timezone

from core.repository import (
    get_unit_active_jv_name,
    resolve_unit_scope,
)
from epi_backend.epi_scope import get_epi_effective_jv_name, is_epi_visible_for_unit
from modules.stock.service import (
    STATUS_CRITICAL,
    STATUS_NEAR_MINIMUM,
    classify_unit_epi_stock,
)

UTC = timezone.utc

# Mesma janela do cliente: `Epi._dateStatus` marca 'expiring' quando a data
# ainda não passou e cai dentro dos próximos 30 dias. Reproduzida aqui em vez de
# reaproveitar MANUFACTURER_VALIDITY_WARNING_DAYS porque são coisas diferentes —
# aquela constante rege o aviso de recebimento de compra, e alinhá-las por
# parecerem iguais mudaria o KPI em silêncio.
EXPIRING_WINDOW_DAYS = 30


def _as_date(valor):
    """Data de uma string ISO, ou None. Aceita 'YYYY-MM-DD' e datetime ISO.

    `DateTime.tryParse` no Dart devolve null para lixo em vez de lançar; aqui a
    mesma tolerância, porque um campo malformado numa linha não pode derrubar o
    Dashboard inteiro.
    """
    texto = str(valor or '').strip()
    if not texto:
        return None
    try:
        return datetime.fromisoformat(texto.replace('Z', '+00:00')).date()
    except ValueError:
        pass
    try:
        return date.fromisoformat(texto[:10])
    except ValueError:
        return None


def _is_expiring(valor, hoje):
    """True quando a data ainda não passou e cai na janela de atenção.

    Espelha `Epi._dateStatus(...) == 'expiring'`: 'expired' (já passou) NÃO
    conta. O KPI é "vence em breve", não "vencido" — vencidos aparecem em
    `compliance`, que tem categoria própria.
    """
    quando = _as_date(valor)
    if quando is None:
        return False
    return hoje <= quando < hoje + timedelta(days=EXPIRING_WINDOW_DAYS)


def build_dashboard_summary(
    connection,
    actor,
    *,
    requested_unit_id=None,
    requested_legal_entity_id=None,
    requested_sector=None,
    permissions=(),
    fetch_units,
    fetch_employees,
    fetch_epis,
    fetch_deliveries,
    fetch_legal_entities,
    compute_alerts,
    compute_stock_compliance,
    count_pending_purchases,
):
    """Resumo do Dashboard já recortado e calculado.

    As dependências entram por parâmetro (mesmo padrão de `compute_alerts` e
    `fetch_low_stock_items`) para não importar `modules.*` a partir daqui: é o
    que mantém o módulo fora do ciclo de imports fechado pela issue #148.
    """
    escopo = resolve_unit_scope(
        connection, actor, requested_unit_id,
        denial_message='Perfil sem unidade operacional ativa para consultar o painel.',
    )

    unidades = fetch_units(connection, actor)
    cnpjs = fetch_legal_entities(connection, actor)

    # Perfil travado não escolhe CNPJ: ele deriva da Unidade do ator, como no
    # backend (`resolve_actor_legal_entity_ids`) e no `lockedLegalEntityId` do
    # cliente. Aceitar o CNPJ do payload aqui deixaria o perfil travado abrir a
    # cascata por um caminho lateral.
    if escopo.locked:
        cnpj_id = _cnpj_da_unidade(unidades, escopo.unit_id)
    else:
        cnpj_id = _int_ou_none(requested_legal_entity_id)

    unidades_no_escopo = _unidades_no_escopo(unidades, escopo, cnpj_id)
    setor = str(requested_sector or '').strip() or None

    colaboradores = fetch_employees(connection, actor)
    entregas = fetch_deliveries(connection, actor)
    epis = fetch_epis(connection, actor, escopo.unit_id)

    hoje = date.today()

    return {
        'scope': {
            'unit_id': escopo.unit_id,
            'unit_scope_source': escopo.source,
            'locked': escopo.locked,
            'company_id': _int_ou_none(actor.get('company_id')),
            'legal_entity_id': cnpj_id,
            'sector': setor,
        },
        'kpis': {
            'deliveries_today': _entregas_de_hoje(entregas, unidades_no_escopo, setor, hoje),
            'expiring_epis': _epis_a_vencer(epis, unidades_no_escopo, hoje),
            'critical_stock': _contagem_por_status(
                connection, actor, epis, escopo, STATUS_CRITICAL),
            'near_minimum_stock': _contagem_por_status(
                connection, actor, epis, escopo, STATUS_NEAR_MINIMUM),
            'pending_purchases': count_pending_purchases(),
        },
        'filters': {
            'legal_entities': [
                {'id': _int_ou_none(c.get('id')), 'name': _rotulo_cnpj(c)}
                for c in cnpjs
            ],
            'units': [
                {
                    'id': _int_ou_none(u.get('id')),
                    'name': str(u.get('name') or ''),
                    'legal_entity_id': _int_ou_none(u.get('legal_entity_id')),
                }
                for u in unidades
                if not escopo.locked or _int_ou_none(u.get('id')) == escopo.unit_id
            ],
            'sectors': _setores(colaboradores, unidades_no_escopo),
        },
        'alerts': compute_alerts(connection, actor),
        'compliance': _conformidade(connection, actor, escopo, compute_stock_compliance),
    }


# ── recorte ──────────────────────────────────────────────────────────────────

def _int_ou_none(valor):
    try:
        convertido = int(valor)
    except (TypeError, ValueError):
        return None
    return convertido or None


def _cnpj_da_unidade(unidades, unit_id):
    for unidade in unidades:
        if _int_ou_none(unidade.get('id')) == unit_id:
            return _int_ou_none(unidade.get('legal_entity_id'))
    return None


def _unidades_no_escopo(unidades, escopo, cnpj_id):
    """Ids das Unidades no recorte, ou `None` para "sem restrição".

    `None` e conjunto vazio são coisas DIFERENTES e a distinção é o que
    mantém o fail-closed: vazio significa "nenhuma Unidade casa" e zera os
    indicadores; `None` significa "sem restrição" e abre para a empresa. Trocar
    um pelo outro é como um perfil travado sem Unidade acabaria vendo a empresa
    inteira.
    """
    if escopo.locked:
        return {escopo.unit_id}
    if escopo.unit_id:
        return {escopo.unit_id}
    if cnpj_id is None:
        return None
    return {
        _int_ou_none(u.get('id'))
        for u in unidades
        if _int_ou_none(u.get('legal_entity_id')) == cnpj_id
    }


def _no_escopo(unidades_no_escopo, valor):
    if unidades_no_escopo is None:
        return True
    return _int_ou_none(valor) in unidades_no_escopo


# ── KPIs ─────────────────────────────────────────────────────────────────────

def _entregas_de_hoje(entregas, unidades_no_escopo, setor, hoje):
    total = 0
    for entrega in entregas:
        if not _no_escopo(unidades_no_escopo, entrega.get('unit_id')):
            continue
        if setor is not None and str(entrega.get('sector') or '') != setor:
            continue
        # `delivery_date` primeiro, `created_at` como reserva — mesma ordem do
        # cliente. Não é fallback por truthiness entre grandezas: os dois campos
        # datam o MESMO evento, e o segundo só existe porque entregas
        # importadas podem não ter a data operacional preenchida.
        quando = _as_date(entrega.get('delivery_date')) or _as_date(entrega.get('created_at'))
        if quando == hoje:
            total += 1
    return total


def _epis_a_vencer(epis, unidades_no_escopo, hoje):
    """CA ou validade do fabricante vencendo na janela de atenção.

    EPI de nível empresa (`unit_id` nulo) conta em QUALQUER recorte: ele não
    pertence a uma Unidade específica, e escondê-lo ao filtrar por Unidade faria
    sumir do painel um CA prestes a vencer que afeta todas elas. Regra atual do
    cliente, preservada de propósito.
    """
    total = 0
    for epi in epis:
        unidade = epi.get('unit_id')
        if unidade is not None and not _no_escopo(unidades_no_escopo, unidade):
            continue
        vencendo = (
            _is_expiring(epi.get('ca_expiry') or epi.get('ca_expiry_date'), hoje)
            or _is_expiring(
                epi.get('epi_validity_date') or epi.get('manufacturer_validity_date'), hoje
            )
        )
        if vencendo:
            total += 1
    return total


def _contagem_por_status(connection, actor, epis, escopo, status_alvo):
    """Conta EPIs da Unidade cujo `stock_status` é `status_alvo` (#271).

    Três estados distintos, e a diferença entre os dois primeiros é o ponto:

    - `None` — não há Unidade resolvida (perfil livre sem seleção). Não é
      "nada crítico": é "a pergunta não se aplica". Devolver 0 aqui afirmaria
      que está tudo em ordem numa Unidade que ninguém escolheu.
    - `0` — Unidade resolvida e nenhum EPI crítico nela.
    - `> 0` — quantidade real de EPIs críticos naquela Unidade.

    Deliberadamente NÃO equivale ao KPI antigo, que era
    `stockQuantity <= minimumStock` (saldo da empresa contra mínimo da empresa).

    Conta por `stock_status`, não por `underlying_status`: um EPI com o
    monitoramento desligado sai dos DOIS KPIs (crítico e atenção), porque a
    Unidade decidiu não ser alertada sobre ele. Continua visível no Controle de
    Estoque com os números reais e o rótulo de monitoramento desabilitado — o
    que ele nunca vira é "normal".
    """
    if not escopo.unit_id:
        return None

    unit_id = int(escopo.unit_id)
    jv_da_unidade = get_unit_active_jv_name(connection, unit_id)
    total = 0
    for epi in epis:
        company_id = _int_ou_none(epi.get('company_id'))
        if not company_id:
            continue
        # Mesma checagem de visibilidade GLOBAL/JV do resto do sistema. Sem ela
        # o KPI contaria EPI que a Unidade nem enxerga na tela de estoque.
        if not is_epi_visible_for_unit(
            epi_unit_id=epi.get('unit_id'),
            epi_joint_venture_name=get_epi_effective_jv_name(
                epi, lambda uid: get_unit_active_jv_name(connection, uid)
            ),
            target_unit_id=unit_id,
            target_unit_joint_venture_name=jv_da_unidade,
        ):
            continue
        epi_id = _int_ou_none(epi.get('id'))
        if not epi_id:
            continue
        classificacao = classify_unit_epi_stock(
            connection, company_id, unit_id, epi_id,
            unit_stock=_saldo_da_unidade(connection, company_id, unit_id, epi_id),
        )
        if classificacao.stock_status == status_alvo:
            total += 1
    return total


def _saldo_da_unidade(connection, company_id, unit_id, epi_id):
    """Saldo do EPI na Unidade. Sem linha em `unit_epi_stock` a Unidade tem
    zero, não "sem dado" — e zero contra um mínimo positivo é crítico, que é
    exatamente o caso que precisa aparecer no painel."""
    linha = connection.execute(
        'SELECT quantity FROM unit_epi_stock '
        'WHERE company_id = ? AND unit_id = ? AND epi_id = ?',
        (company_id, unit_id, epi_id),
    ).fetchone()
    if linha is None:
        return 0
    from epi_backend.db import row_to_dict
    return int(row_to_dict(linha).get('quantity') or 0)


# ── fontes do filtro ─────────────────────────────────────────────────────────

def _setores(colaboradores, unidades_no_escopo):
    setores = set()
    for colaborador in colaboradores:
        if not _no_escopo(unidades_no_escopo, colaborador.get('unit_id')):
            continue
        setor = str(colaborador.get('sector') or '').strip()
        if setor:
            setores.add(setor)
    return sorted(setores)


def _rotulo_cnpj(cnpj):
    """Rótulo exibível de um CNPJ, na ordem em que o usuário o reconhece."""
    for chave in ('trade_name', 'legal_name', 'name', 'cnpj'):
        rotulo = str(cnpj.get(chave) or '').strip()
        if rotulo:
            return rotulo
    return ''


def _conformidade(connection, actor, escopo, compute_stock_compliance):
    """Repassa `/api/stock/compliance` sem tocar na regra.

    Sem empresa resolvida devolve `{}` em vez de levantar: a conformidade é uma
    seção do painel, e o `master_admin` sem empresa selecionada tem um painel
    legítimo — só não tem essa seção.
    """
    company_id = _int_ou_none(actor.get('company_id'))
    if not company_id:
        return {}
    return compute_stock_compliance(connection, company_id, escopo.unit_id)
