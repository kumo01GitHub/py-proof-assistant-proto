"""Tests for proof status logging and get_proof_summary.

Covers the short/medium-term improvements:
- get_proof_summary returns detailed categorization for proved/trusted/sorry/incomplete
- Per-tactic [TRUSTED] / [SORRY] warnings are emitted during proof execution
- @theorem decorator logs the proof outcome with explicit status markers
- trusted_steps is a list of dicts with keys: index, tactic, reason, suggestion, goal
- get_proof_summary exposes first_trusted_step_index and first_trusted_goal
"""

import logging

import pytest

from zfc_leanpy.dsl import (
    get_proof_summary,
    get_registry,
    get_status,
    lemma,
    theorem,
)


# ──────────────────────────────────────────────────────────────────
# get_proof_summary — proved
# ──────────────────────────────────────────────────────────────────

class TestGetProofSummaryProved:
    def test_proved_status(self):
        @theorem("ps_proved", "P → P", tactics=["intro h", "exact h"])
        def _():
            pass

        summary = get_proof_summary("ps_proved")
        assert summary is not None
        assert summary["kind"] == "theorem"
        assert summary["status"] == "proved"
        assert summary["error_message"] is None

    def test_proved_trusted_steps_empty(self):
        @theorem("ps_proved_ts", "P → P", tactics=["intro h", "exact h"])
        def _():
            pass

        summary = get_proof_summary("ps_proved_ts")
        assert summary["trusted_steps"] == []

    def test_proved_replay_ok(self):
        @theorem("ps_proved_replay", "P → P", tactics=["intro h", "exact h"])
        def _():
            pass

        summary = get_proof_summary("ps_proved_replay")
        assert summary["replay_ok"] is True

    def test_proved_first_trusted_step_index_is_none(self):
        @theorem("ps_proved_fts", "P → P", tactics=["intro h", "exact h"])
        def _():
            pass

        summary = get_proof_summary("ps_proved_fts")
        assert summary["first_trusted_step_index"] is None
        assert summary["first_trusted_goal"] is None


# ──────────────────────────────────────────────────────────────────
# get_proof_summary — sorry
# ──────────────────────────────────────────────────────────────────

class TestGetProofSummarySorry:
    def test_sorry_status(self):
        @theorem("ps_sorry", "P", tactics=["sorry"])
        def _():
            pass

        summary = get_proof_summary("ps_sorry")
        assert summary is not None
        assert summary["kind"] == "theorem"
        assert summary["status"] == "sorry"

    def test_sorry_error_message_contains_sorry_tag(self):
        @theorem("ps_sorry_msg", "P", tactics=["sorry"])
        def _():
            pass

        summary = get_proof_summary("ps_sorry_msg")
        assert summary["error_message"] is not None
        assert "[SORRY]" in summary["error_message"]

    def test_sorry_registry_has_empty_trusted_steps(self):
        @theorem("ps_sorry_cert", "P", tactics=["sorry"])
        def _():
            pass

        reg = get_registry()["ps_sorry_cert"]
        assert reg["trusted_steps"] == []


# ──────────────────────────────────────────────────────────────────
# get_proof_summary — trusted
# ──────────────────────────────────────────────────────────────────

class TestGetProofSummaryTrusted:
    def test_trusted_status(self):
        # `have h2 : Q := h` is an inline proof term — always a trusted step.
        @theorem(
            "ps_trusted",
            "P → Q",
            tactics=["intro h", "have h2 : Q := h", "exact h2"],
        )
        def _():
            pass

        summary = get_proof_summary("ps_trusted")
        assert summary is not None
        assert summary["kind"] == "theorem"
        assert summary["status"] == "trusted"

    def test_trusted_error_message_contains_trusted_tag(self):
        @theorem(
            "ps_trusted_msg",
            "P → Q",
            tactics=["intro h", "have h2 : Q := h", "exact h2"],
        )
        def _():
            pass

        summary = get_proof_summary("ps_trusted_msg")
        assert summary["error_message"] is not None
        assert "[TRUSTED]" in summary["error_message"]

    def test_trusted_steps_are_listed_as_dicts(self):
        @theorem(
            "ps_trusted_steps",
            "P → Q",
            tactics=["intro h", "have h2 : Q := h", "exact h2"],
        )
        def _():
            pass

        summary = get_proof_summary("ps_trusted_steps")
        assert len(summary["trusted_steps"]) > 0
        step = summary["trusted_steps"][0]
        assert "index" in step
        assert "tactic" in step
        assert "reason" in step
        assert "suggestion" in step
        assert "goal" in step

    def test_trusted_step_index_is_1based(self):
        @theorem(
            "ps_trusted_idx",
            "P → Q",
            tactics=["intro h", "have h2 : Q := h", "exact h2"],
        )
        def _():
            pass

        summary = get_proof_summary("ps_trusted_idx")
        step = summary["trusted_steps"][0]
        # "have h2 : Q := h" is the 2nd tactic (1-based index 2)
        assert step["index"] == 2

    def test_first_trusted_step_index(self):
        @theorem(
            "ps_first_trusted",
            "P → Q",
            tactics=["intro h", "have h2 : Q := h", "exact h2"],
        )
        def _():
            pass

        summary = get_proof_summary("ps_first_trusted")
        assert summary["first_trusted_step_index"] == 2

    def test_first_trusted_goal(self):
        @theorem(
            "ps_first_trusted_goal",
            "P → Q",
            tactics=["intro h", "have h2 : Q := h", "exact h2"],
        )
        def _():
            pass

        summary = get_proof_summary("ps_first_trusted_goal")
        # At the time of 'have h2 : Q := h', the current goal is "Q"
        assert summary["first_trusted_goal"] == "Q"

    def test_trusted_registry_has_nonempty_trusted_steps(self):
        @theorem(
            "ps_trusted_cert",
            "P → Q",
            tactics=["intro h", "have h2 : Q := h", "exact h2"],
        )
        def _():
            pass

        reg = get_registry()["ps_trusted_cert"]
        assert len(reg["trusted_steps"]) > 0


# ──────────────────────────────────────────────────────────────────
# get_proof_summary — unknown name
# ──────────────────────────────────────────────────────────────────

class TestGetProofSummaryUnknown:
    def test_unknown_name_returns_none(self):
        assert get_proof_summary("nonexistent_theorem_xyz") is None


# ──────────────────────────────────────────────────────────────────
# Per-tactic logging — [TRUSTED] warning emitted for trusted steps
# ──────────────────────────────────────────────────────────────────

class TestTacticLevelLogging:
    def test_trusted_tactic_emits_warning(self, caplog):
        # `have h2 : Q := h` is an inline proof term — always emits TRUSTED warning.
        with caplog.at_level(logging.WARNING, logger="zfc_leanpy"):
            @theorem(
                "log_trusted",
                "P → Q",
                tactics=["intro h", "have h2 : Q := h", "exact h2"],
            )
            def _():
                pass

        trusted_warnings = [r for r in caplog.records if "[TRUSTED" in r.message]
        assert len(trusted_warnings) > 0
        # Log contains count, not raw step names (to avoid taint flow to logging sinks)
        assert any("unverified step" in r.message for r in trusted_warnings)

    def test_sorry_tactic_emits_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger="zfc_leanpy"):
            @theorem("log_sorry", "P", tactics=["sorry"])
            def _():
                pass

        sorry_warnings = [r for r in caplog.records if "[SORRY" in r.message]
        assert len(sorry_warnings) > 0

    def test_proved_tactic_no_trusted_warning(self, caplog):
        # Proved theorems only emit INFO-level logs; no WARNING-level trusted markers
        with caplog.at_level(logging.INFO, logger="zfc_leanpy"):
            @theorem("log_proved", "P → P", tactics=["intro h", "exact h"])
            def _():
                pass

        trusted_warnings = [r for r in caplog.records if "[TRUSTED" in r.message]
        assert len(trusted_warnings) == 0


# ──────────────────────────────────────────────────────────────────
# Decorator-level logging — status markers in log output
# ──────────────────────────────────────────────────────────────────

class TestDecoratorStatusLogging:
    def test_proved_decorator_logs_proved_marker(self, caplog):
        with caplog.at_level(logging.INFO, logger="zfc_leanpy"):
            @theorem("dl_proved", "P → P", tactics=["intro h", "exact h"])
            def _():
                pass

        proved_logs = [r for r in caplog.records if "[PROVED" in r.message]
        assert len(proved_logs) > 0
        # Verify log level is INFO
        assert all(r.levelno == logging.INFO for r in proved_logs)
        assert any("✓" in r.message for r in proved_logs)

    def test_sorry_decorator_logs_sorry_marker(self, caplog):
        with caplog.at_level(logging.WARNING, logger="zfc_leanpy"):
            @theorem("dl_sorry", "P", tactics=["sorry"])
            def _():
                pass

        sorry_logs = [r for r in caplog.records if "[SORRY" in r.message]
        assert len(sorry_logs) > 0

    def test_trusted_decorator_logs_trusted_marker(self, caplog):
        # `have h2 : Q := h` is an inline proof term — always a trusted step.
        with caplog.at_level(logging.WARNING, logger="zfc_leanpy"):
            @theorem(
                "dl_trusted",
                "P → Q",
                tactics=["intro h", "have h2 : Q := h", "exact h2"],
            )
            def _():
                pass

        trusted_logs = [r for r in caplog.records if "[TRUSTED" in r.message]
        assert len(trusted_logs) > 0


# ──────────────────────────────────────────────────────────────────
# Lemma — same status / summary behavior
# ──────────────────────────────────────────────────────────────────

class TestLemmaStatus:
    def test_lemma_proved_summary(self):
        @lemma("lm_proved", "P → P", tactics=["intro h", "exact h"])
        def _():
            pass

        summary = get_proof_summary("lm_proved")
        assert summary["status"] == "proved"
        assert summary["kind"] == "lemma"

    def test_lemma_sorry_status(self):
        @lemma("lm_sorry", "P", tactics=["sorry"])
        def _():
            pass

        summary = get_proof_summary("lm_sorry")
        assert summary["status"] == "sorry"
        assert get_registry()["lm_sorry"]["trusted_steps"] == []
