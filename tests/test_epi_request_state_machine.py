"""Máquina de estados da solicitação de EPI (plano §16).

O que existia antes era um *conjunto* de status válidos: validava o destino e
ignorava a origem. Estes testes fixam as transições — e, principalmente, as
**proibições**, que são o motivo de a máquina existir.
"""

import pytest

from modules.epis.request_states import (
    APPROVED,
    CANCELLED,
    DELIVERY_COMPLETED,
    DELIVERY_REFUSED,
    InvalidStatusTransition,
    LEGACY_SIGNED,
    PICKING,
    POSTPONED,
    READY_FOR_DELIVERY,
    REJECTED,
    RESERVED,
    SUBMITTED,
    UNDER_REVIEW,
    WAITING_STOCK,
    allowed_transitions,
    assert_transition,
    can_transition,
    is_terminal,
    normalize_status,
    spec_code,
)


# ── caminho feliz ────────────────────────────────────────────────────────────

def test_full_happy_path_is_walkable():
    """Solicitação → análise → reserva → separação → entrega."""
    chain = [
        SUBMITTED, UNDER_REVIEW, RESERVED, PICKING,
        READY_FOR_DELIVERY, DELIVERY_COMPLETED,
    ]
    for origin, destination in zip(chain, chain[1:]):
        assert assert_transition(origin, destination) == destination


def test_out_of_stock_path_is_walkable():
    """Sem saldo: aguarda estoque, reserva quando chegar, entrega."""
    chain = [
        SUBMITTED, UNDER_REVIEW, WAITING_STOCK, RESERVED, PICKING,
        READY_FOR_DELIVERY, DELIVERY_COMPLETED,
    ]
    for origin, destination in zip(chain, chain[1:]):
        assert assert_transition(origin, destination) == destination


# ── proibições (o motivo da máquina existir) ─────────────────────────────────

def test_waiting_stock_cannot_jump_to_delivered():
    """§16: `WAITING_STOCK → DELIVERY_COMPLETED` é proibido.

    Entregar o que ainda não chegou é o erro que a máquina existe para barrar.
    """
    with pytest.raises(InvalidStatusTransition, match='não permitida'):
        assert_transition(WAITING_STOCK, DELIVERY_COMPLETED)


def test_reserved_cannot_jump_to_delivered_without_picking():
    with pytest.raises(InvalidStatusTransition):
        assert_transition(RESERVED, DELIVERY_COMPLETED)


def test_terminal_states_accept_nothing():
    for terminal in (DELIVERY_COMPLETED, REJECTED, CANCELLED):
        assert allowed_transitions(terminal) == frozenset()
        assert is_terminal(terminal)
        with pytest.raises(InvalidStatusTransition):
            assert_transition(terminal, UNDER_REVIEW)


def test_cannot_resurrect_a_delivered_request():
    with pytest.raises(InvalidStatusTransition):
        assert_transition(DELIVERY_COMPLETED, RESERVED)


def test_unknown_target_is_rejected():
    with pytest.raises(InvalidStatusTransition, match='Status inválido'):
        assert_transition(SUBMITTED, 'inventado')


def test_unknown_origin_does_not_unlock_everything():
    """Dado legado fora do vocabulário recusa, em vez de liberar geral."""
    with pytest.raises(InvalidStatusTransition, match='origem desconhecido'):
        assert_transition('status_que_nao_existe', DELIVERY_COMPLETED)


def test_same_state_is_idempotent():
    """Regravar o mesmo estado não é transição — não deve explodir."""
    assert assert_transition(RESERVED, RESERVED) == RESERVED


# ── recusa da entrega ────────────────────────────────────────────────────────

def test_refusal_does_not_end_the_request():
    """§15.2: recusa não encerra; o gestor decide o destino."""
    assert not is_terminal(DELIVERY_REFUSED)
    assert can_transition(READY_FOR_DELIVERY, DELIVERY_REFUSED)
    assert can_transition(DELIVERY_REFUSED, READY_FOR_DELIVERY)
    assert can_transition(DELIVERY_REFUSED, CANCELLED)


def test_refused_cannot_become_delivered_directly():
    """Nova entrega exige voltar a "pronto para entrega" e assinar de novo."""
    with pytest.raises(InvalidStatusTransition):
        assert_transition(DELIVERY_REFUSED, DELIVERY_COMPLETED)


# ── `assinado` colapsa em `entregue` ─────────────────────────────────────────

def test_legacy_signed_reads_as_delivered():
    """§11.4: a assinatura conclui a entrega; não é um estado à parte."""
    assert normalize_status(LEGACY_SIGNED) == DELIVERY_COMPLETED
    assert spec_code(LEGACY_SIGNED) == 'DELIVERY_COMPLETED'
    assert is_terminal(LEGACY_SIGNED)


def test_legacy_signed_rows_are_treated_as_terminal():
    """Linha antiga com `assinado` não pode ser reaberta."""
    with pytest.raises(InvalidStatusTransition):
        assert_transition(LEGACY_SIGNED, PICKING)


# ── atalho legado, explícito e nomeado ───────────────────────────────────────

def test_direct_delivery_shortcut_is_still_open_before_reservations_exist():
    """Entrega direta (sem reserva) conclui a solicitação — por ora.

    Não é buraco na máquina: é atalho nomeado (`LEGACY_DIRECT_DELIVERY`) que
    sai quando o fluxo de reserva entrar. Sem ele, o caminho de entrega em
    produção quebraria hoje.
    """
    assert can_transition(SUBMITTED, DELIVERY_COMPLETED)
    assert can_transition(UNDER_REVIEW, DELIVERY_COMPLETED)
    assert can_transition(APPROVED, DELIVERY_COMPLETED)


def test_the_shortcut_is_declared_not_incidental():
    from modules.epis.request_states import LEGACY_DIRECT_DELIVERY

    assert LEGACY_DIRECT_DELIVERY == frozenset({SUBMITTED, UNDER_REVIEW, APPROVED})


# ── normalização e códigos ───────────────────────────────────────────────────

def test_normalize_tolerates_case_and_spaces():
    assert normalize_status('  Solicitado ') == SUBMITTED
    assert normalize_status('EM ANÁLISE') == UNDER_REVIEW


def test_normalize_returns_empty_for_garbage():
    for value in (None, '', '   ', 'qualquer coisa'):
        assert normalize_status(value) == ''


def test_every_status_has_a_spec_code():
    from modules.epis.request_states import ALL_STATUSES, SPEC_CODE

    assert set(SPEC_CODE) == set(ALL_STATUSES)
    assert all(code.isupper() for code in SPEC_CODE.values())


def test_spec_codes_cover_the_plan_vocabulary():
    from modules.epis.request_states import SPEC_CODE

    required = {
        'SUBMITTED', 'UNDER_REVIEW', 'WAITING_STOCK', 'RESERVED', 'PICKING',
        'READY_FOR_DELIVERY', 'DELIVERY_COMPLETED', 'DELIVERY_REFUSED',
        'REJECTED', 'CANCELLED',
    }
    assert required <= set(SPEC_CODE.values())


def test_postponed_can_return_to_the_flow():
    """`prorrogado` é estado próprio do projeto, fora do vocabulário do plano."""
    assert can_transition(POSTPONED, UNDER_REVIEW)
    assert can_transition(POSTPONED, RESERVED)
    assert not is_terminal(POSTPONED)


def test_cancellation_is_reachable_from_every_live_state():
    """Cancelar é sempre possível enquanto a solicitação estiver viva."""
    live = [
        SUBMITTED, UNDER_REVIEW, APPROVED, WAITING_STOCK, RESERVED, PICKING,
        READY_FOR_DELIVERY, DELIVERY_REFUSED, POSTPONED,
    ]
    for status in live:
        assert can_transition(status, CANCELLED), status


# ── casos revelados ao ligar a máquina no código existente ───────────────────
#
# Os dois abaixo vieram de falhas reais na suíte. A máquina estava rígida
# demais em pontos que o sistema já praticava; corrigi a máquina, não os testes.

def test_direct_approval_from_submitted_is_preserved():
    """O gestor aprova sem passar por "em análise" — comportamento existente.

    O §16 lista transições **mínimas**, não uma whitelist fechada. Barrar esta
    seria regressão, não rigor.
    """
    assert assert_transition(SUBMITTED, APPROVED) == APPROVED


def test_row_without_status_falls_back_to_the_initial_state():
    """Linha antiga com `status` nulo não pode travar o operador.

    É defeito de dado; assume-se `solicitado`, o estado vivo mais restrito.
    Valor **preenchido** e desconhecido continua recusando.
    """
    assert assert_transition(None, UNDER_REVIEW) == UNDER_REVIEW
    assert assert_transition('', REJECTED) == REJECTED
    assert assert_transition('   ', APPROVED) == APPROVED
    with pytest.raises(InvalidStatusTransition, match='origem desconhecido'):
        assert_transition('lixo', APPROVED)


def test_fallback_origin_does_not_grant_terminal_privileges():
    """Cair para `solicitado` não pode virar porta dos fundos.

    Uma linha sem status continua sujeita às mesmas restrições de `solicitado`.
    """
    with pytest.raises(InvalidStatusTransition):
        assert_transition(None, PICKING)
    with pytest.raises(InvalidStatusTransition):
        assert_transition(None, READY_FOR_DELIVERY)
