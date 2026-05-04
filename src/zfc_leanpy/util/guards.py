"""Type guard functions for tactic input validation.

These guards enforce runtime type safety at tactic entry points, providing
clear, structured error messages when type invariants are violated.  They
bridge the gap between Python's dynamic typing and the formal proof system's
requirement for type-safe state transitions (Method 1 of "Avoiding Dynamic
Typing Issues").
"""

from __future__ import annotations

from typing import Any

from ..kernel import ProofState, TacticError


def require_proof_state(obj: Any, context: str = "") -> ProofState:
    """Validate that *obj* is a :class:`~zfc_leanpy.kernel.ProofState`.

    Args:
        obj: The value to validate.
        context: Optional label identifying the call-site (e.g.
            ``"apply_tactic"``), included in the error message for clarity.

    Returns:
        *obj* unchanged, typed as ``ProofState``.

    Raises:
        TacticError: When *obj* is not a :class:`ProofState` instance,
            including the actual type in the error message.
    """
    if not isinstance(obj, ProofState):
        ctx = f" [{context}]" if context else ""
        raise TacticError(
            f"type guard failed{ctx}: expected ProofState, "
            f"got {type(obj).__name__!r}"
        )
    return obj


def require_tactic_string(obj: Any, context: str = "") -> str:
    """Validate that *obj* is a :class:`str` tactic.

    Args:
        obj: The value to validate.
        context: Optional label identifying the call-site, included in the
            error message for clarity.

    Returns:
        *obj* unchanged, typed as ``str``.

    Raises:
        TacticError: When *obj* is not a string, including the actual type
            in the error message.
    """
    if not isinstance(obj, str):
        ctx = f" [{context}]" if context else ""
        raise TacticError(
            f"type guard failed{ctx}: expected str tactic, "
            f"got {type(obj).__name__!r}"
        )
    return obj
