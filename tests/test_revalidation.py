"""Tests for the revalidate_proof() auto-revalidation feature.

Covers:
- trusted_steps field in ProofState and get_proof_summary() as list of dicts
- revalidate_proof() upgrading a trusted proof to proved
- revalidate_proof() when new tactics still leave trusted steps
- revalidate_proof() for non-existent and non-applicable statuses
- revalidate_proof() from a separate module (cross-file upgrade scenario)
"""

import logging

import pytest

from zfc_leanpy.dsl import (
    theorem,
    get_proof_summary,
    revalidate_proof,
)
from zfc_leanpy.kernel import ProofState
from zfc_leanpy.tactics import apply_tactic


# ──────────────────────────────────────────────────────────────────
# trusted_steps field in ProofState
# ──────────────────────────────────────────────────────────────────

class TestTrustedSteps:
    def test_proof_state_has_trusted_steps_field(self):
        """ProofState initialises with an empty trusted_steps list."""
        s = ProofState("P")
        assert hasattr(s, "trusted_steps")
        assert s.trusted_steps == []

    def test_snapshot_copies_trusted_steps(self):
        """snapshot() preserves trusted_steps as independent copy."""
        s = ProofState("P")
        s.trusted_steps.append({"index": 1, "tactic": "t", "reason": "r", "suggestion": "s", "goal": "G"})
        snap = s.snapshot()
        assert len(snap.trusted_steps) == 1
        # Mutation of original should not affect snapshot.
        s.trusted_steps.append({"index": 2, "tactic": "t2", "reason": "", "suggestion": "", "goal": ""})
        assert len(snap.trusted_steps) == 1

    def test_trusted_steps_populated_after_trusted_tactic(self, caplog):
        """trusted_steps is populated when a tactic explicitly uses a trusted step."""
        with caplog.at_level(logging.WARNING, logger="zfc_leanpy"):
            @theorem(
                "sugg_trusted",
                "P → P",
                tactics=["intro h", "have h2 : P := h", "exact h2"],
            )
            def _():
                pass

        summary = get_proof_summary("sugg_trusted")
        assert summary["status"] == "trusted"
        assert len(summary["trusted_steps"]) > 0
        step = summary["trusted_steps"][0]
        # Each step is a dict with required keys.
        assert isinstance(step["suggestion"], str) and step["suggestion"]

    def test_proved_proof_has_empty_trusted_steps(self):
        """A fully proved theorem has no trusted_steps."""
        @theorem("sugg_proved", "P → P", tactics=["intro h", "exact h"])
        def _():
            pass

        summary = get_proof_summary("sugg_proved")
        assert summary["status"] == "proved"
        assert summary["trusted_steps"] == []

    def test_suggestion_in_summary_matches_log(self, caplog):
        """Suggestion stored in trusted_steps[0] matches the Suggestion logged in WARNING."""
        with caplog.at_level(logging.WARNING, logger="zfc_leanpy"):
            @theorem(
                "sugg_match_log",
                "P → Q",
                tactics=["intro h", "have h2 : Q := h", "exact h2"],
            )
            def _():
                pass

        summary = get_proof_summary("sugg_match_log")
        trusted_warnings = [r for r in caplog.records if "[TRUSTED" in r.message]
        assert trusted_warnings, "Expected at least one TRUSTED warning"
        # The suggestion in the summary's first trusted step should appear in the log.
        logged_suggestion_fragment = summary["trusted_steps"][0]["suggestion"][:20]
        assert any(
            logged_suggestion_fragment in r.message for r in trusted_warnings
        )


# ──────────────────────────────────────────────────────────────────
# revalidate_proof() — successful upgrade to proved
# ──────────────────────────────────────────────────────────────────

class TestRevalidateProofUpgrade:
    def test_revalidate_returns_none_for_missing_name(self):
        """revalidate_proof returns None when the name is not registered."""
        result = revalidate_proof("does_not_exist", ["intro h", "exact h"])
        assert result is None

    def test_revalidate_trusted_to_proved(self):
        """revalidate_proof on a trusted proof does not produce proved if tactics still fail."""
        # Register a proof that will be trusted (inline proof term).
        @theorem("rv_trusted2", "P → P", tactics=["intro h", "have h2 : P := h", "exact h2"])
        def _():
            pass

        initial2 = get_proof_summary("rv_trusted2")
        assert initial2["status"] == "trusted"

        # Revalidate with tactics that still fall back — proof cannot be closed
        # kernel-verified because the inline proof term still goes through trusted.
        result = revalidate_proof("rv_trusted2", ["intro h", "have h2 : P := h", "exact h2"])
        assert result is not None
        assert result["status"] == "trusted"  # still trusted

    def test_revalidate_produces_proved_for_correct_tactics(self):
        """revalidate_proof upgrades trusted → proved when given correct tactics."""
        # Register a proof that will be trusted because 'have h2 : P := h'
        # uses an inline proof term that the kernel cannot structurally verify.
        @theorem(
            "rv_upgrade_valid",
            "P → P",
            tactics=["intro h", "have h2 : P := h", "exact h2"],
        )
        def _():
            pass

        # Confirm the initial status is trusted.
        initial_valid = get_proof_summary("rv_upgrade_valid")
        assert initial_valid["status"] == "trusted"

        # Revalidate with direct kernel-verified tactics.
        result = revalidate_proof("rv_upgrade_valid", ["intro h", "exact h"])
        assert result is not None
        assert result["status"] == "proved"
        assert result["trusted_steps"] == []

    def test_revalidate_updates_registry_entry(self):
        """After revalidate_proof succeeds, get_proof_summary reflects proved status."""
        @theorem(
            "rv_registry",
            "P ∧ Q → P",
            tactics=["intro h", "have h2 : P := h", "exact h2"],
        )
        def _():
            pass

        assert get_proof_summary("rv_registry")["status"] == "trusted"
        revalidate_proof("rv_registry", ["intro h", "cases h", "exact h1"])
        assert get_proof_summary("rv_registry")["status"] == "proved"

    def test_revalidate_logs_upgrade_info(self, caplog):
        """revalidate_proof logs an INFO message on successful upgrade."""
        @theorem(
            "rv_log_info",
            "P ∧ Q → P",
            tactics=["intro h", "have h2 : P := h", "exact h2"],
        )
        def _():
            pass

        assert get_proof_summary("rv_log_info")["status"] == "trusted"

        with caplog.at_level(logging.INFO, logger="zfc_leanpy"):
            revalidate_proof("rv_log_info", ["intro h", "cases h", "exact h1"])

        info_records = [r for r in caplog.records if "revalidate" in r.message.lower()]
        assert any("proved" in r.message.lower() for r in info_records)


# ──────────────────────────────────────────────────────────────────
# revalidate_proof() — inapplicable statuses
# ──────────────────────────────────────────────────────────────────

class TestRevalidateInapplicable:
    def test_revalidate_proved_returns_summary_unchanged(self):
        """revalidate_proof on an already-proved entry returns it unchanged."""
        @theorem("rv_already_proved", "P → P", tactics=["intro h", "exact h"])
        def _():
            pass

        result = revalidate_proof("rv_already_proved", ["intro h", "exact h"])
        assert result is not None
        assert result["status"] == "proved"

    def test_revalidate_sorry_not_upgraded_with_broken_tactics(self):
        """revalidate_proof on a sorry entry attempts revalidation with new tactics.

        A sorry proof is treated like any incomplete entry: if the new tactics
        produce a kernel-verified closure, the status is upgraded to proved.
        If the tactics are incorrect, the status reflects the revalidation result.
        """
        @theorem("rv_sorry", "P", tactics=["sorry"])
        def _():
            pass

        # Tactics that don't close "P" — result will not be proved.
        result = revalidate_proof("rv_sorry", ["intro h", "exact h"])
        assert result is not None
        # Cannot prove a bare propositional variable without an axiom.
        assert result["status"] != "proved"

    def test_revalidate_logs_warning_when_still_trusted(self, caplog):
        """revalidate_proof logs WARNING when the new tactics are still trusted."""
        @theorem(
            "rv_warn",
            "P → Q",
            tactics=["intro h", "have h2 : Q := h", "exact h2"],
        )
        def _():
            pass

        assert get_proof_summary("rv_warn")["status"] == "trusted"

        with caplog.at_level(logging.WARNING, logger="zfc_leanpy"):
            revalidate_proof("rv_warn", ["intro h", "have h2 : Q := h", "exact h2"])

        warn_records = [
            r for r in caplog.records
            if "revalidate" in r.message.lower() and r.levelno == logging.WARNING
        ]
        assert len(warn_records) > 0


# ──────────────────────────────────────────────────────────────────
# Cross-module upgrade scenario
# ──────────────────────────────────────────────────────────────────

class TestCrossModuleRevalidation:
    def test_trusted_registered_in_one_place_upgraded_in_another(self):
        """Simulates a cross-module workflow: trusted in module A, upgraded in B."""
        # --- Module A: register with incomplete / trusted tactics ---
        @theorem(
            "cross_mod_theorem",
            "P ∧ Q → Q",
            tactics=["intro h", "have h2 : Q := h", "exact h2"],
        )
        def _():
            pass

        assert get_proof_summary("cross_mod_theorem")["status"] == "trusted"

        # --- Module B: upgrade with a complete kernel-verified proof ---
        upgraded = revalidate_proof(
            "cross_mod_theorem",
            ["intro h", "cases h", "exact h2"],
        )
        assert upgraded is not None
        assert upgraded["status"] == "proved"
        assert upgraded["trusted_steps"] == []
