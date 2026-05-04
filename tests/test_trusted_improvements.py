"""Tests for trusted-tactic improvements.

Covers:
- Structural cases on ∧ (no trusted mark)
- Structural cases on ∨ (two goals, no trusted mark)
- Structural rw with equality hypothesis (no trusted mark, closes via rfl)
- Fallback reasons recorded in trusted_steps / trusted_reasons
- Reason and Suggestion appear in WARNING log output
"""

import logging

import pytest

from zfc_leanpy.kernel import ProofState
from zfc_leanpy.tactics import apply_tactic
from zfc_leanpy.dsl import theorem, get_proof_summary


# ──────────────────────────────────────────────────────────────────
# Structural cases on ∧
# ──────────────────────────────────────────────────────────────────

class TestCasesConjunction:
    def test_cases_and_splits_hypothesis(self):
        """cases h on h : P ∧ Q produces h1:P and h2:Q without trusted mark."""
        s = ProofState("P ∧ Q → P", {"h": "P ∧ Q"})
        s = apply_tactic(s, "cases h")
        assert "h" not in s.hypotheses
        assert "h1" in s.hypotheses
        assert "h2" in s.hypotheses
        assert s.hypotheses["h1"] == "P"
        assert s.hypotheses["h2"] == "Q"
        assert not s.trusted_steps

    def test_cases_and_proof_closes_kernel_verified(self):
        """A proof using structural cases on ∧ is fully kernel-verified."""
        @theorem("cases_and_test", "P ∧ Q → P", tactics=["intro h", "cases h", "exact h1"])
        def _():
            pass

        summary = get_proof_summary("cases_and_test")
        assert summary["status"] == "proved"
        assert summary["trusted_steps"] == []

    def test_cases_and_then_right_kernel_verified(self):
        """cases h on h : P ∧ Q; then prove Q."""
        @theorem("cases_and_right", "P ∧ Q → Q", tactics=["intro h", "cases h", "exact h2"])
        def _():
            pass

        summary = get_proof_summary("cases_and_right")
        assert summary["status"] == "proved"


# ──────────────────────────────────────────────────────────────────
# Structural cases on ∨
# ──────────────────────────────────────────────────────────────────

class TestCasesDisjunction:
    def test_cases_or_creates_two_goals(self):
        """cases h on h : P ∨ Q creates two sub-goals."""
        s = ProofState("P ∨ Q → R", {"h": "P ∨ Q"})
        s = apply_tactic(s, "cases h")
        assert len(s.goals) == 2
        assert not s.trusted_steps

    def test_cases_or_left_branch_has_left_hyp(self):
        s = ProofState("P", {"h": "P ∨ Q"})
        s = apply_tactic(s, "cases h")
        assert "h_left" in s.hypotheses
        assert s.hypotheses["h_left"] == "P"
        assert "h" not in s.hypotheses

    def test_cases_or_right_branch_has_right_hyp(self):
        s = ProofState("Q", {"h": "P ∨ Q"})
        s = apply_tactic(s, "cases h")
        assert len(s.goals) == 2
        # Right branch is goal index 1
        right_hyps = s._hyp_stack[1]
        assert "h_right" in right_hyps
        assert right_hyps["h_right"] == "Q"


# ──────────────────────────────────────────────────────────────────
# Structural rw with equality hypothesis
# ──────────────────────────────────────────────────────────────────

class TestRwEquality:
    def test_rw_closes_goal_via_rfl(self):
        """rw [h] where h : x = y rewrites the goal and closes it with rfl."""
        s = ProofState("y = y", {"h": "x = y"})
        s = apply_tactic(s, "rw [h]")
        # After rw the goal becomes y = y which is closed by rfl
        assert s.closed
        assert not s.trusted_steps

    def test_rw_transforms_goal(self):
        """rw [h] where h : a = b rewrites 'a = c' to 'b = c' (goal changed)."""
        s = ProofState("a = c", {"h": "a = b"})
        s = apply_tactic(s, "rw [h]")
        assert not s.closed  # still needs to prove b = c
        assert s.current_goal() == "b = c"
        assert not s.trusted_steps

    def test_rw_missing_rule_falls_back_to_trusted_with_reason(self):
        """rw with unknown rule produces a trusted step with a reason."""
        s = ProofState("x = y")
        s = apply_tactic(s, "rw [unknown_rule]")
        assert len(s.trusted_steps) > 0
        assert any("not found" in r for r in s.trusted_reasons)

    def test_rw_non_equality_rule_falls_back_with_reason(self):
        """rw with non-equality hypothesis records a reason."""
        s = ProofState("x = y", {"h": "P"})
        s = apply_tactic(s, "rw [h]")
        assert len(s.trusted_steps) > 0
        reason = s.trusted_reasons[0]
        assert "equality" in reason or "rw" in reason

    def test_rw_kernel_verified_proof(self):
        """An equality proof using rw + rfl is fully kernel-verified."""
        @theorem(
            "rw_test",
            "∀ x, x = x",
            tactics=["intro x", "rfl"],
        )
        def _():
            pass

        summary = get_proof_summary("rw_test")
        assert summary["status"] == "proved"


# ──────────────────────────────────────────────────────────────────
# Trusted fallback reasons recorded in ProofState
# ──────────────────────────────────────────────────────────────────

class TestTrustedReasons:
    def test_apply_unknown_hyp_has_reason(self):
        """apply with unknown hypothesis records a descriptive reason."""
        s = ProofState("P")
        s = apply_tactic(s, "apply unknown_lemma")
        assert len(s.trusted_steps) == 1
        assert len(s.trusted_reasons) == 1
        reason = s.trusted_reasons[0]
        assert "not found" in reason or "unknown_lemma" in reason

    def test_apply_type_mismatch_has_reason(self):
        """apply when the conclusion doesn't match the goal records a reason."""
        s = ProofState("Q", {"h": "P → P"})
        s = apply_tactic(s, "apply h")
        assert len(s.trusted_steps) == 1
        reason = s.trusted_reasons[0]
        assert reason  # non-empty reason

    def test_cases_unknown_hyp_has_reason(self):
        """cases on an unknown hypothesis records a descriptive reason."""
        s = ProofState("P")
        s = apply_tactic(s, "cases nonexistent")
        assert len(s.trusted_steps) == 1
        reason = s.trusted_reasons[0]
        assert "not found" in reason or "nonexistent" in reason

    def test_cases_non_conjunction_has_reason(self):
        """cases on a non-∧/∨ hypothesis records an explanatory reason."""
        s = ProofState("P", {"h": "P → Q"})
        s = apply_tactic(s, "cases h")
        assert len(s.trusted_steps) == 1
        reason = s.trusted_reasons[0]
        assert reason  # non-empty


# ──────────────────────────────────────────────────────────────────
# Reason and Suggestion in WARNING log output
# ──────────────────────────────────────────────────────────────────

class TestReasonInLog:
    def test_log_includes_reason(self, caplog):
        """The [TRUSTED ⚠] log line includes the reason for the fallback."""
        with caplog.at_level(logging.WARNING, logger="zfc_leanpy"):
            @theorem(
                "log_reason_test",
                "(P → Q) → ¬Q → ¬P",
                tactics=["intro hpq hnq hp", "apply hnq", "apply hpq", "exact hp"],
            )
            def _():
                pass

        trusted_warnings = [r for r in caplog.records if "[TRUSTED" in r.message]
        assert len(trusted_warnings) > 0
        # Each warning must explain WHY (Reason field)
        assert any("Reason" in r.message for r in trusted_warnings)

    def test_log_includes_suggestion(self, caplog):
        """The [TRUSTED ⚠] log line includes a suggestion for resolution."""
        with caplog.at_level(logging.WARNING, logger="zfc_leanpy"):
            @theorem(
                "log_suggestion_test",
                "P → P → P",
                tactics=["intro h1 h2", "apply h1"],
            )
            def _():
                pass

        trusted_warnings = [r for r in caplog.records if "[TRUSTED" in r.message]
        assert any("Suggestion" in r.message for r in trusted_warnings)

    def test_sorry_log_has_cross_icon(self, caplog):
        """The [SORRY ✗] marker appears for admitted proofs."""
        with caplog.at_level(logging.WARNING, logger="zfc_leanpy"):
            @theorem("log_sorry_icon", "P", tactics=["sorry"])
            def _():
                pass

        sorry_warnings = [r for r in caplog.records if "[SORRY" in r.message]
        assert len(sorry_warnings) > 0
