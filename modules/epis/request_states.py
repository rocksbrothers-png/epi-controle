"""Máquina de estados da solicitação de EPI do colaborador.

Antes disto o sistema tinha um *conjunto* de status válidos, não uma máquina:
validava o destino e ignorava a origem, então `solicitado → entregue` passava.
Aqui as transições passam a ser explícitas.

**Os nomes em português são preservados.** São os valores já gravados em
`epi_requests.status`; renomeá-los exigiria migrar dados e quebraria clientes.
O mapa `SPEC_CODE` traduz cada um para o código canônico do processo
(`SUBMITTED`, `RESERVED`, …), que é o que a API e as telas expõem.

Duas decisões que valem registro:

1. **`assinado` deixa de ser estado próprio.** A assinatura válida *conclui* a
   entrega — não há confirmação posterior. Linhas antigas com `assinado`
   continuam sendo lidas como `entregue`; nada novo é gravado com esse valor.
2. **A conclusão sem passar por reserva ainda é possível**, porque o fluxo de
   reserva ainda não existe. É um atalho explícito e nomeado
   (`LEGACY_DIRECT_DELIVERY`), não um buraco na máquina: quando a reserva
   entrar, ele sai daqui e a transição passa a exigir a cadeia completa.
"""

# ── Estados ──────────────────────────────────────────────────────────────────

SUBMITTED = 'solicitado'
UNDER_REVIEW = 'em análise'
APPROVED = 'aprovado'
WAITING_STOCK = 'aguardando estoque'
RESERVED = 'reservado'
PICKING = 'separando'
READY_FOR_DELIVERY = 'separado'
DELIVERY_COMPLETED = 'entregue'
DELIVERY_REFUSED = 'entrega recusada'
REJECTED = 'rejeitado'
POSTPONED = 'prorrogado'
CANCELLED = 'cancelado'

#: Valor histórico. A assinatura conclui a entrega, então ele colapsa em
#: ``entregue`` na leitura e nunca é gravado de novo.
LEGACY_SIGNED = 'assinado'

ALL_STATUSES = (
    SUBMITTED, UNDER_REVIEW, APPROVED, WAITING_STOCK, RESERVED, PICKING,
    READY_FOR_DELIVERY, DELIVERY_COMPLETED, DELIVERY_REFUSED, REJECTED,
    POSTPONED, CANCELLED,
)

#: Estados a partir dos quais nada mais acontece.
TERMINAL_STATUSES = frozenset({DELIVERY_COMPLETED, REJECTED, CANCELLED})

#: Código canônico do processo, exposto na API e nas telas.
SPEC_CODE = {
    SUBMITTED: 'SUBMITTED',
    UNDER_REVIEW: 'UNDER_REVIEW',
    APPROVED: 'APPROVED',
    WAITING_STOCK: 'WAITING_STOCK',
    RESERVED: 'RESERVED',
    PICKING: 'PICKING',
    READY_FOR_DELIVERY: 'READY_FOR_DELIVERY',
    DELIVERY_COMPLETED: 'DELIVERY_COMPLETED',
    DELIVERY_REFUSED: 'DELIVERY_REFUSED',
    REJECTED: 'REJECTED',
    POSTPONED: 'POSTPONED',
    CANCELLED: 'CANCELLED',
}

# ── Transições ───────────────────────────────────────────────────────────────

#: Atalho preservado enquanto o fluxo de reserva não existe: a entrega direta
#: (sem solicitação passando por reserva/separação) conclui a solicitação.
#: Sai daqui quando a reserva entrar.
LEGACY_DIRECT_DELIVERY = frozenset({SUBMITTED, UNDER_REVIEW, APPROVED})

_TRANSITIONS = {
    # `APPROVED` direto de `SUBMITTED` é comportamento existente: o gestor pode
    # aprovar sem passar por "em análise". O §16 lista transições MÍNIMAS;
    # remover esta seria regressão, não rigor.
    SUBMITTED: {UNDER_REVIEW, APPROVED, REJECTED, CANCELLED, POSTPONED},
    UNDER_REVIEW: {APPROVED, REJECTED, WAITING_STOCK, RESERVED, CANCELLED, POSTPONED},
    APPROVED: {WAITING_STOCK, RESERVED, CANCELLED, REJECTED},
    WAITING_STOCK: {RESERVED, CANCELLED, REJECTED},
    RESERVED: {PICKING, WAITING_STOCK, CANCELLED},
    PICKING: {READY_FOR_DELIVERY, RESERVED, CANCELLED},
    READY_FOR_DELIVERY: {DELIVERY_COMPLETED, DELIVERY_REFUSED, CANCELLED},
    # A recusa não encerra: o gestor decide entre nova tentativa e cancelamento.
    DELIVERY_REFUSED: {READY_FOR_DELIVERY, RESERVED, CANCELLED},
    POSTPONED: {UNDER_REVIEW, RESERVED, WAITING_STOCK, REJECTED, CANCELLED},
    DELIVERY_COMPLETED: set(),
    REJECTED: set(),
    CANCELLED: set(),
}

# O atalho legado é somado ao mapa até a reserva existir.
for _origin in LEGACY_DIRECT_DELIVERY:
    _TRANSITIONS[_origin] = _TRANSITIONS[_origin] | {DELIVERY_COMPLETED}
del _origin


class InvalidStatusTransition(ValueError):
    """Transição recusada pela máquina de estados."""


def normalize_status(value) -> str:
    """Valor gravado → estado canônico.

    Colapsa o ``assinado`` histórico em ``entregue`` e tolera caixa/espaços.
    Devolve string vazia para valor desconhecido, deixando a decisão de recusar
    para quem chamou.
    """
    text = str(value or '').strip().lower()
    if not text:
        return ''
    if text == LEGACY_SIGNED:
        return DELIVERY_COMPLETED
    return text if text in ALL_STATUSES else ''


def _origin_or_initial(value) -> str:
    """Estado de origem, com linha sem status caindo para o inicial.

    Linha antiga com ``status`` nulo ou vazio é defeito de dado, não motivo
    para travar o operador: assume-se ``solicitado``, o estado vivo mais
    restrito. Valor **preenchido** e desconhecido continua sendo recusado — aí
    a correção precisa ser explícita.
    """
    if str(value or '').strip() == '':
        return SUBMITTED
    return normalize_status(value)


def spec_code(value) -> str:
    """Código canônico do processo para a API e as telas."""
    return SPEC_CODE.get(normalize_status(value), '')


def allowed_transitions(current) -> frozenset:
    """Destinos válidos a partir do estado atual."""
    return frozenset(_TRANSITIONS.get(_origin_or_initial(current), set()))


def can_transition(current, target) -> bool:
    return normalize_status(target) in allowed_transitions(current)


def assert_transition(current, target) -> str:
    """Valida e devolve o estado de destino normalizado.

    Origem desconhecida (dado legado fora do vocabulário) **não** libera geral:
    recusa, para que a correção seja explícita em vez de silenciosa.
    """
    origin = _origin_or_initial(current)
    destination = normalize_status(target)
    if not destination:
        raise InvalidStatusTransition(f'Status inválido: {target!r}.')
    if not origin:
        raise InvalidStatusTransition(
            f'Status de origem desconhecido: {current!r}.'
        )
    if origin == destination:
        return destination
    if destination not in allowed_transitions(origin):
        raise InvalidStatusTransition(
            f'Transição não permitida: {SPEC_CODE[origin]} → {SPEC_CODE[destination]}.'
        )
    return destination


def is_terminal(value) -> bool:
    return normalize_status(value) in TERMINAL_STATUSES
