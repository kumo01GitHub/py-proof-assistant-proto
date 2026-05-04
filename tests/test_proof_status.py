"""Tests for proof status logging, get_proof_summary, and certificate blocking.

Covers the short/medium-term improvements:
- get_proof_summary returns detailed categorization for proved/trusted/sorry/incomplete
- Certificates are blocked for trusted and sorry proofs
- Per-tactic [TRUSTED] / [SORRY] warnings are emitted during proof execution
- @theorem decorator logs the proof outcome with explicit status markers
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
from zfc_leanpy.dsl.certificate import ProofCertificate


# ──────────────────────────────────────────────────────────────────
# get_proof_summary — proved
# ──────────────────────────────────────────────────────────────────

class TestGetProofSummaryProved:
    def test_proved_can_issue_certificate(self):
        @theorem("ps_proved", "P → P", tactics=["intro h", "exact h"])
        def _():
            pass

        summary = get_proof_summary("ps_proved")
        assert summary is not None
        assert summary["kind"] == "theorem"
        assert summary["status"] == "proved"
        assert summary["can_issue_certificate"] is True
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


# ──────────────────────────────────────────────────────────────────
# get_proof_summary — sorry
# ──────────────────────────────────────────────────────────────────

class TestGetProofSummarySorry:
    def test_sorry_cannot_issue_certificate(self):
        @theorem("ps_sorry", "P", tactics=["sorry"])
        def _():
            pass

        summary = get_proof_summary("ps_sorry")
        assert summary is not None
        assert summary["kind"] == "theorem"
        assert summary["status"] == "sorry"
        assert summary["can_issue_certificate"] is False

    def test_sorry_error_message_contains_sorry_tag(self):
        @theorem("ps_sorry_msg", "P", tactics=["sorry"])
        def _():
            pass

        summary = get_proof_summary("ps_sorry_msg")
        assert summary["error_message"] is not None
        assert "[SORRY]" in summary["error_message"]

    def test_sorry_certificate_in_registry_is_none(self):
        @theorem("ps_sorry_cert", "P", tactics=["sorry"])
        def _():
            pass

        reg = get_registry()["ps_sorry_cert"]
        assert reg["certificate"] is None


# ──────────────────────────────────────────────────────────────────
# get_proof_summary — trusted
# ──────────────────────────────────────────────────────────────────

class TestGetProofSummaryTrusted:
    def test_trusted_cannot_issue_certificate(self):
        @theorem(
            "ps_trusted",
            "(P → Q) → ¬Q → ¬P",
            tactics=["intro hpq hnq hp", "apply hnq", "apply hpq", "exact hp"],
        )
        def _():
            pass

        summary = get_proof_summary("ps_trusted")
        assert summary is not None
        assert summary["kind"] == "theorem"
        assert summary["status"] == "trusted"
        assert summary["can_issue_certificate"] is False

    def test_trusted_error_message_contains_trusted_tag(self):
        @theorem(
            "ps_trusted_msg",
            "(P → Q) → ¬Q → ¬P",
            tactics=["intro hpq hnq hp", "apply hnq", "apply hpq", "exact hp"],
        )
        def _():
            pass

        summary = get_proof_summary("ps_trusted_msg")
        assert summary["error_message"] is not None
        assert "[TRUSTED]" in summary["error_message"]

    def test_trusted_steps_are_listed(self):
        @theorem(
            "ps_trusted_steps",
            "(P → Q) → ¬Q → ¬P",
            tactics=["intro hpq hnq hp", "apply hnq", "apply hpq", "exact hp"],
        )
        def _():
            pass

        summary = get_proof_summary("ps_trusted_steps")
        assert len(summary["trusted_steps"]) > 0

    def test_trusted_certificate_in_registry_is_none(self):
        @theorem(
            "ps_trusted_cert",
            "(P → Q) → ¬Q → ¬P",
            tactics=["intro hpq hnq hp", "apply hnq", "apply hpq", "exact hp"],
        )
        def _():
            pass

        reg = get_registry()["ps_trusted_cert"]
        assert reg["certificate"] is None


# ──────────────────────────────────────────────────────────────────
# get_proof_summary — unknown name
# ──────────────────────────────────────────────────────────────────

class TestGetProofSummaryUnknown:
    def test_unknown_name_returns_none(self):
        assert get_proof_summary("nonexistent_theorem_xyz") is None


# ──────────────────────────────────────────────────────────────────
# Certificate blocking — proved is the only issuing state
# ──────────────────────────────────────────────────────────────────

class TestCertificateBlocking:
    def test_proved_certificate_verifies(self):
        @theorem("cb_proved", "P → P", tactics=["intro h", "exact h"])
        def _():
            pass

        reg = get_registry()["cb_proved"]
        assert reg["certificate"] is not None
        cert = reg["certificate"]
        cert_obj = ProofCertificate(
            statement=cert["statement"],
            tactics=list(cert["tactics"]),
            replay_ok=bool(cert["replay_ok"]),
            signature=cert["signature"],
        )
        assert cert_obj.verify() is True

    def test_sorry_no_certificate(self):
        @theorem("cb_sorry", "P", tactics=["sorry"])
        def _():
            pass

        reg = get_registry()["cb_sorry"]
        assert reg["certificate"] is None

    def test_trusted_no_certificate(self):
        @theorem(
            "cb_trusted",
            "(P → Q) → ¬Q → ¬P",
            tactics=["intro hpq hnq hp", "apply hnq", "apply hpq", "exact hp"],
        )
        def _():
            pass

        reg = get_registry()["cb_trusted"]
        assert reg["certificate"] is None


# ──────────────────────────────────────────────────────────────────
# Per-tactic logging — [TRUSTED] warning emitted for trusted steps
# ──────────────────────────────────────────────────────────────────

class TestTacticLevelLogging:
    def test_trusted_tactic_emits_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger="zfc_leanpy"):
            @theorem(
                "log_trusted",
                "(P → Q) → ¬Q → ¬P",
                tactics=["intro hpq hnq hp", "apply hnq", "apply hpq", "exact hp"],
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
        # Verify log level is INFO and message includes key indicators
        assert all(r.levelno == logging.INFO for r in proved_logs)
        assert any("✓" in r.message and "certificate issued" in r.message for r in proved_logs)

    def test_sorry_decorator_logs_sorry_marker(self, caplog):
        with caplog.at_level(logging.WARNING, logger="zfc_leanpy"):
            @theorem("dl_sorry", "P", tactics=["sorry"])
            def _():
                pass

        sorry_logs = [r for r in caplog.records if "[SORRY" in r.message]
        assert len(sorry_logs) > 0

    def test_trusted_decorator_logs_trusted_marker(self, caplog):
        with caplog.at_level(logging.WARNING, logger="zfc_leanpy"):
            @theorem(
                "dl_trusted",
                "(P → Q) → ¬Q → ¬P",
                tactics=["intro hpq hnq hp", "apply hnq", "apply hpq", "exact hp"],
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
        assert summary["can_issue_certificate"] is True
        assert summary["kind"] == "lemma"

    def test_lemma_sorry_no_certificate(self):
        @lemma("lm_sorry", "P", tactics=["sorry"])
        def _():
            pass

        summary = get_proof_summary("lm_sorry")
        assert summary["status"] == "sorry"
        assert summary["can_issue_certificate"] is False
        assert get_registry()["lm_sorry"]["certificate"] is None
