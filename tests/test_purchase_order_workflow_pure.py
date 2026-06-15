"""Testes puros da máquina de estados das Ordens de Compra (PO)."""

import pytest

from epi_backend.purchase_order_workflow import (
    assert_approval_allowed,
    assert_receive_allowed,
    assert_resubmit_allowed,
    assert_review_allowed,
    po_status_label,
    required_approval_levels,
    resolve_approval_outcome,
)


# ── review ────────────────────────────────────────────────────────────────────

def test_review_approved_goes_to_pending_approval():
    assert assert_review_allowed('waiting_admin_review', 'review_approved') == 'pending_approval'


def test_review_returned_goes_to_quoted():
    assert assert_review_allowed('waiting_admin_review', 'returned_with_suggestions') == 'quoted'


def test_review_blocked_from_wrong_status():
    with pytest.raises(ValueError):
        assert_review_allowed('approved', 'review_approved')


def test_review_invalid_decision():
    with pytest.raises(ValueError):
        assert_review_allowed('waiting_admin_review', 'whatever')


# ── resubmit ──────────────────────────────────────────────────────────────────

def test_resubmit_from_quoted():
    assert assert_resubmit_allowed('quoted') == 'waiting_admin_review'


def test_resubmit_blocked_elsewhere():
    with pytest.raises(ValueError):
        assert_resubmit_allowed('pending_approval')


# ── approval gating ───────────────────────────────────────────────────────────

@pytest.mark.parametrize('status', ['pending_approval', 'postponed'])
def test_approval_allowed_from(status):
    assert_approval_allowed(status, 'approved')  # não levanta


def test_approval_blocked_from_draft():
    with pytest.raises(ValueError):
        assert_approval_allowed('waiting_admin_review', 'approved')


def test_approval_invalid_decision():
    with pytest.raises(ValueError):
        assert_approval_allowed('pending_approval', 'sortof')


# ── receive ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize('current,action', [
    ('approved', 'received'),
    ('approved', 'received_partial'),
    ('received_partial', 'received'),
    ('received', 'checked'),
    ('received_partial', 'checked'),
    ('checked', 'closed'),
])
def test_receive_allowed(current, action):
    assert assert_receive_allowed(current, action) == action


@pytest.mark.parametrize('current,action', [
    ('approved', 'checked'),     # não pode conferir sem receber
    ('approved', 'closed'),      # não pode fechar sem conferir
    ('received', 'closed'),      # idem
    ('pending_approval', 'received'),
])
def test_receive_blocked(current, action):
    with pytest.raises(ValueError):
        assert_receive_allowed(current, action)


def test_receive_invalid_action():
    with pytest.raises(ValueError):
        assert_receive_allowed('approved', 'teleport')


# ── multi-nível ───────────────────────────────────────────────────────────────

def test_required_levels_no_threshold():
    assert required_approval_levels(99999, 0) == 1
    assert required_approval_levels(99999, None) == 1


def test_required_levels_below_threshold():
    assert required_approval_levels(100, 500) == 1


def test_required_levels_at_or_above_threshold():
    assert required_approval_levels(500, 500) == 2
    assert required_approval_levels(900, 500) == 2


def test_outcome_rejected_is_terminal():
    assert resolve_approval_outcome('rejected', prior_approvals=0, total_value=100, threshold=0) == ('rejected', True)


def test_outcome_postponed_not_final():
    assert resolve_approval_outcome('postponed', prior_approvals=0, total_value=100, threshold=0) == ('postponed', False)


def test_outcome_single_level_approves_immediately():
    assert resolve_approval_outcome('approved', prior_approvals=0, total_value=100, threshold=0) == ('approved', True)


def test_outcome_partial_single_level():
    assert resolve_approval_outcome('partially_approved', prior_approvals=0, total_value=100, threshold=0) == ('partially_approved', True)


def test_outcome_multilevel_first_step_pending():
    # total >= threshold -> exige 2 níveis; 1ª aprovação não finaliza
    assert resolve_approval_outcome('approved', prior_approvals=0, total_value=1000, threshold=500) == ('pending_approval', False)


def test_outcome_multilevel_second_step_finalizes():
    assert resolve_approval_outcome('approved', prior_approvals=1, total_value=1000, threshold=500) == ('approved', True)


def test_status_label_fallback():
    assert po_status_label('approved') == 'Aprovada'
    assert po_status_label('zzz') == 'zzz'
