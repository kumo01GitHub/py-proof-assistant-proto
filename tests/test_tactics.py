import pytest

from zfc_leanpy.kernel import ProofState, TacticError
from zfc_leanpy.tactics import apply_tactic


def test_intro_and_exact_closes_goal():
    s = ProofState("P → P")
    s = apply_tactic(s, "intro h")
    s = apply_tactic(s, "exact h")
    assert s.closed


def test_constructor_for_conjunction():
    s = ProofState("P ∧ Q", {"hp": "P", "hq": "Q"})
    s = apply_tactic(s, "constructor")
    s = apply_tactic(s, "exact hp")
    s = apply_tactic(s, "exact hq")
    assert s.closed


def test_split_for_iff():
    s = ProofState("(P → Q) ↔ (P → Q)", {"h": "P → Q"})
    s = apply_tactic(s, "split")
    assert len(s.goals) == 2


def test_left_and_right_for_disjunction():
    s = ProofState("P ∨ Q", {"hp": "P"})
    s = apply_tactic(s, "left")
    s = apply_tactic(s, "exact hp")
    assert s.closed


def test_rfl_checks_reflexivity():
    s = ProofState("x = x")
    s = apply_tactic(s, "rfl")
    assert s.closed


def test_assumption_finds_matching_hypothesis():
    s = ProofState("P", {"h": "P"})
    s = apply_tactic(s, "assumption")
    assert s.closed


def test_sorry_marks_admitted():
    s = ProofState("P")
    s = apply_tactic(s, "sorry")
    assert s.admitted


def test_unknown_tactic_raises():
    with pytest.raises(TacticError):
        apply_tactic(ProofState("P"), "foobar")
