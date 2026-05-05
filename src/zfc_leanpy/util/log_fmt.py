"""Log output formatting utilities for proof status visualization.

Centralises ANSI color helpers and proof-status tag formatting so that
``proof_engine`` and the DSL runner share a single, consistent
representation of proof statuses, minimising log redundancy.
"""

from __future__ import annotations

import sys
from typing import Any, Dict, List, Tuple


class ANSI:
    """ANSI terminal color codes and a TTY-aware color helper."""

    GREEN = "32"
    YELLOW = "33"
    RED = "31"

    @staticmethod
    def color(code: str, text: str) -> str:
        """Wrap *text* in an ANSI escape sequence when stdout is a real TTY."""
        if sys.stdout.isatty():
            return f"\033[{code}m{text}\033[0m"
        return text


def format_proof_status_tag(status: str, trusted_steps: List[Dict[str, Any]]) -> Tuple[str, str]:
    """Return *(icon, tag)* strings for a proof entry's status line.

    To avoid flowing proof-internal step names through logging sinks, the
    ``[trusted ⚠]`` tag reports only the *count* of unverified steps.  Use
    ``get_proof_summary()`` to retrieve the full step list.

    Args:
        status: One of ``"proved"``, ``"trusted"``, ``"sorry"``, or any other
            incomplete/unknown status string.
        trusted_steps: List of trusted step dicts (only the *count* is included
            in the returned tag string).

    Returns:
        A tuple ``(icon, tag)`` of ANSI-colored strings ready for log output.
    """
    if status == "proved":
        return (
            ANSI.color(ANSI.GREEN, "✓"),
            ANSI.color(ANSI.GREEN, "[fully sound]"),
        )
    if status == "trusted":
        step_count = len(trusted_steps)
        return (
            ANSI.color(ANSI.YELLOW, "⚠"),
            ANSI.color(ANSI.YELLOW, f"[trusted ⚠: {step_count} unverified step(s)]"),
        )
    if status == "sorry":
        return (
            ANSI.color(ANSI.RED, "✗"),
            ANSI.color(ANSI.RED, "[sorry]"),
        )
    return (
        ANSI.color(ANSI.RED, "✗"),
        ANSI.color(ANSI.RED, f"[{status}]"),
    )


def format_trusted_step_detail(step: Dict[str, Any]) -> str:
    """Format a single unverified tactic step dict for log output.

    Args:
        step: A trusted step dict with keys ``index``, ``tactic``, ``reason``,
            ``suggestion``, and ``goal``.

    Returns:
        A formatted string with ANSI bullet, step number, tactic, and reason.
    """
    idx = step.get("index", -1)
    tactic = step.get("tactic", "?")
    reason = step.get("reason", "")
    idx_str = f"step {idx}" if idx >= 0 else "step ?"
    reason_text = f" — {reason}" if reason else ""
    marker = ANSI.color(ANSI.YELLOW, "·")
    return f"{marker} [{idx_str}] unverified tactic '{tactic}'{reason_text}"
