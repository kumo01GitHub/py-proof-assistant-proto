"""
proof_engine.py — 命題論理の例題定理デモ

Python DSL 形式で定理を登録・証明する例。
ZFC 公理は含まない。axioms.py を import すれば ZFC 公理を追加できる。

実行:
    python -m zfc_leanpy.proof_engine
"""

import sys

from .dsl import theorem, get_registry, ProofState
from .logger import get_logger
from .tactics import apply_tactic


logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# ANSI color helpers (terminal-only)
# ---------------------------------------------------------------------------

def _color(code: str, text: str) -> str:
    """Wrap *text* in an ANSI escape sequence when stdout is a real TTY."""
    if sys.stdout.isatty():
        return f"\033[{code}m{text}\033[0m"
    return text


_GREEN  = "32"
_YELLOW = "33"
_RED    = "31"
_BOLD   = "1"


# ---------------------------------------------------------------------------
# 例題定理（タクティクリスト形式）
# ---------------------------------------------------------------------------

@theorem("p_implies_p", "P → P", tactics=["intro h", "exact h"])
def _(): pass


@theorem(
    "or_intro_left", "P → P ∨ Q",
    tactics=["intro h", "left", "exact h"]
)
def _(): pass


@theorem(
    "and_comm", "P ∧ Q → Q ∧ P",
    tactics=["intro h", "constructor", "exact h.2", "exact h.1"]
)
def _(): pass


@theorem(
    "and_assoc", "(P ∧ Q) ∧ R → P ∧ (Q ∧ R)",
    tactics=["intro h", "constructor", "exact h.1.1",
             "constructor", "exact h.1.2", "exact h.2"]
)
def _(): pass


@theorem(
    "iff_intro", "(P → Q) → (Q → P) → (P ↔ Q)",
    tactics=["intro hpq", "intro hqp", "split", "exact hpq", "exact hqp"]
)
def _(): pass


@theorem(
    "double_neg", "¬¬P → P",
    tactics=["sorry"]
)
def _(): pass


@theorem(
    "exists_refl", "∃ x, x = x",
    tactics=["use x", "rfl"]
)
def _(): pass


# ---------------------------------------------------------------------------
# 関数スタイル証明
# ---------------------------------------------------------------------------

@theorem("trivial_conj", "P → Q → P ∧ Q")
def proof_trivial_conj(state: ProofState) -> ProofState:
    state = apply_tactic(state, "intro hp")
    state = apply_tactic(state, "intro hq")
    state = apply_tactic(state, "constructor")
    state = apply_tactic(state, "exact hp")
    state = apply_tactic(state, "exact hq")
    return state


# ---------------------------------------------------------------------------
# デモ出力
# ---------------------------------------------------------------------------

def main():
    registry = get_registry()
    theorems = {k: v for k, v in registry.items() if v["kind"] in ("theorem", "lemma")}

    logger.info("%s", "=" * 60)
    logger.info("  leanpy — 命題論理証明チェッカー (Lean 4 構文互換)")
    logger.info("%s", "=" * 60)
    logger.info("\n[定理 (%d)]", len(theorems))
    for name, entry in theorems.items():
        status = entry["status"]
        ts = entry.get("trusted_steps", [])
        if status == "proved":
            icon = _color(_GREEN, "✓")
            tag  = _color(_GREEN, "[fully sound]")
        elif status == "trusted":
            icon = _color(_YELLOW, "⚠")
            step_summary = ", ".join(ts) if ts else "unknown"
            tag = _color(_YELLOW, f"[trusted ⚠: {step_summary}]")
        elif status == "sorry":
            icon = _color(_RED, "✗")
            tag  = _color(_RED, "[sorry — no certificate]")
        else:
            icon = _color(_RED, "✗")
            tag  = _color(_RED, f"[{status}]")
        logger.info("  %s %-24s %s", icon, name, tag)
        logger.info("      : %s", entry["statement"])

        # Emit per-step trusted details so developers see exactly which tactics
        # fell back to the unverified path and why.
        if status == "trusted" and ts:
            reasons = entry.get("trusted_reasons", [])
            for i, step in enumerate(ts):
                reason = reasons[i] if i < len(reasons) else ""
                reason_text = f" — {reason}" if reason else ""
                logger.info(
                    "        %s unverified step: '%s'%s",
                    _color(_YELLOW, "·"),
                    step,
                    reason_text,
                )

    logger.info("\n%s", "=" * 60)


if __name__ == "__main__":
    main()


