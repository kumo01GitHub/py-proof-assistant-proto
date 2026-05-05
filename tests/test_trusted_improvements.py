"""Tests for tactic verification behavior.

Covers:
- Structural cases on ∧ (no trusted mark)
- Structural cases on ∨ (two goals, no trusted mark)
- Structural rw with equality hypothesis (no trusted mark, closes via rfl)
- Failed tactics raise TacticError (no implicit trusted fallback)
- Reason and Suggestion appear in WARNING log output for explicit trusted steps
"""

import logging

import pytest

from zfc_leanpy.kernel import ProofState, TacticError
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

    def test_rw_missing_rule_raises_tactic_error(self):
        """rw with unknown rule raises TacticError (no longer a trusted fallback)."""
        with pytest.raises(TacticError, match="not found"):
            apply_tactic(ProofState("x = y"), "rw [unknown_rule]")

    def test_rw_non_equality_rule_raises_tactic_error(self):
        """rw with non-equality hypothesis raises TacticError (no longer a trusted fallback)."""
        with pytest.raises(TacticError, match="equality"):
            apply_tactic(ProofState("x = y", {"h": "P"}), "rw [h]")

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
# Tactic errors — failed tactics raise TacticError (no trusted fallback)
# ──────────────────────────────────────────────────────────────────

class TestTacticErrors:
    def test_apply_unknown_hyp_raises_tactic_error(self):
        """apply with unknown hypothesis raises TacticError."""
        with pytest.raises(TacticError, match="not found"):
            apply_tactic(ProofState("P"), "apply unknown_lemma")

    def test_apply_type_mismatch_raises_tactic_error(self):
        """apply when the conclusion doesn't match the goal raises TacticError."""
        with pytest.raises(TacticError, match="conclusion does not match"):
            apply_tactic(ProofState("Q", {"h": "P → P"}), "apply h")

    def test_cases_unknown_hyp_raises_tactic_error(self):
        """cases on an unknown hypothesis raises TacticError."""
        with pytest.raises(TacticError, match="not found"):
            apply_tactic(ProofState("P"), "cases nonexistent")

    def test_cases_non_conjunction_raises_tactic_error(self):
        """cases on a non-∧/∨ hypothesis raises TacticError."""
        with pytest.raises(TacticError, match="requires ∧ or ∨"):
            apply_tactic(ProofState("P", {"h": "P → Q"}), "cases h")


# ──────────────────────────────────────────────────────────────────
# Reason and Suggestion in WARNING log output
# ──────────────────────────────────────────────────────────────────

class TestReasonInLog:
    def test_log_includes_reason(self, caplog):
        """The [TRUSTED ⚠] log line includes the reason for the fallback."""
        # `have h2 : Q := h` is an inline proof term — explicit trusted step with reason.
        with caplog.at_level(logging.WARNING, logger="zfc_leanpy"):
            @theorem(
                "log_reason_test",
                "P → Q",
                tactics=["intro h", "have h2 : Q := h", "exact h2"],
            )
            def _():
                pass

        trusted_warnings = [r for r in caplog.records if "[TRUSTED" in r.message]
        assert len(trusted_warnings) > 0
        # Each warning must explain WHY (Reason field)
        assert any("Reason" in r.message for r in trusted_warnings)

    def test_log_includes_suggestion(self, caplog):
        """The [TRUSTED ⚠] log line includes a suggestion for resolution."""
        # `have h2 : Q := h` — inline proof term → trusted fallback with suggestion.
        with caplog.at_level(logging.WARNING, logger="zfc_leanpy"):
            @theorem(
                "log_suggestion_test",
                "P → Q",
                tactics=["intro h", "have h2 : Q := h", "exact h2"],
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


# ──────────────────────────────────────────────────────────────────
# Trusted reduction — apply now kernel-verifies backward application
# ──────────────────────────────────────────────────────────────────

class TestApplyTrustedReduction:
    def test_apply_impl_no_trusted_mark(self):
        """apply h where h : A → B and goal B reduces goal to A without trusted."""
        s = ProofState("Q", {"h": "P → Q"})
        s = apply_tactic(s, "apply h")
        assert not s.trusted_steps
        assert not s.closed
        assert s.current_goal() == "P"

    def test_apply_not_false_no_trusted_mark(self):
        """apply h where h : ¬P and goal False reduces goal to P without trusted."""
        s = ProofState("False", {"h": "¬P"})
        s = apply_tactic(s, "apply h")
        assert not s.trusted_steps
        assert not s.closed
        assert s.current_goal() == "P"

    def test_apply_exact_match_closes_kernel_verified(self):
        """apply h where h : P and goal P closes the proof kernel-verified."""
        s = ProofState("P", {"h": "P"})
        s = apply_tactic(s, "apply h")
        assert s.closed
        assert not s.trusted_steps

    def test_modus_tollens_is_now_proved(self):
        """(P → Q) → ¬Q → ¬P is now fully kernel-verified (no trusted steps)."""
        @theorem(
            "modus_tollens",
            "(P → Q) → ¬Q → ¬P",
            tactics=["intro hpq hnq hp", "apply hnq", "apply hpq", "exact hp"],
        )
        def _():
            pass

        summary = get_proof_summary("modus_tollens")
        assert summary["status"] == "proved"
        assert summary["trusted_steps"] == []

    def test_apply_mismatch_raises_tactic_error(self):
        """apply h where conclusion does not match goal raises TacticError."""
        with pytest.raises(TacticError):
            apply_tactic(ProofState("Q", {"h": "P → P"}), "apply h")

    def test_apply_exact_match_p_to_p_to_p(self):
        """P → P → P with 'intro h1 h2, apply h1' is now proved."""
        @theorem(
            "apply_exact_match",
            "P → P → P",
            tactics=["intro h1 h2", "apply h1"],
        )
        def _():
            pass

        summary = get_proof_summary("apply_exact_match")
        assert summary["status"] == "proved"
        assert summary["trusted_steps"] == []


# ──────────────────────────────────────────────────────────────────
# Type guards — require_proof_state / require_tactic_string
# ──────────────────────────────────────────────────────────────────

class TestTypeGuards:
    def test_apply_tactic_rejects_non_proof_state(self):
        """apply_tactic raises TacticError when state is not ProofState."""
        with pytest.raises(TacticError, match="type guard failed"):
            apply_tactic("not a state", "intro h")  # type: ignore[arg-type]

    def test_apply_tactic_rejects_non_string_tactic(self):
        """apply_tactic raises TacticError when tactic is not a string."""
        with pytest.raises(TacticError, match="type guard failed"):
            apply_tactic(ProofState("P"), 42)  # type: ignore[arg-type]

    def test_require_proof_state_passes_for_valid(self):
        """require_proof_state returns the state unchanged when valid."""
        from zfc_leanpy.util.guards import require_proof_state
        s = ProofState("P")
        assert require_proof_state(s) is s

    def test_require_tactic_string_passes_for_valid(self):
        """require_tactic_string returns the string unchanged when valid."""
        from zfc_leanpy.util.guards import require_tactic_string
        assert require_tactic_string("intro h") == "intro h"

    def test_require_proof_state_includes_context_in_error(self):
        """require_proof_state error message includes the context label."""
        from zfc_leanpy.util.guards import require_proof_state
        with pytest.raises(TacticError, match=r"my_context"):
            require_proof_state(None, context="my_context")
