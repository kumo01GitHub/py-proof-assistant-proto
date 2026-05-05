"""Proof execution helpers used by theorem/lemma decorators."""

import inspect
from typing import Any, Callable, Dict, List

from ..kernel import ProofState, TacticError
from ..logger import get_logger
from ..tactics import apply_tactic


logger = get_logger(__name__)


def _log_tactic_result(
    tac: str,
    tactic_index: int,
    before_trusted: int,
    state: ProofState,
) -> None:
    """Log the verification outcome of a single tactic application.

    When a tactic falls back to a trusted (unverified) step, the log includes
    the step number, current goal, reason why the kernel could not verify it
    and a suggestion on how to resolve the gap.
    """
    if state.admitted:
        logger.warning(
            "    [SORRY ✗] step %d '%s' — proof admitted (sorry)", tactic_index, tac
        )
    elif len(state.trusted_steps) > before_trusted:
        new_entries: List[Dict[str, Any]] = state.trusted_steps[before_trusted:]
        suggestion = _suggest_for_tactic(tac)
        # Enrich each new trusted step with its tactic index and suggestion.
        for entry in new_entries:
            entry["index"] = tactic_index
            if not entry.get("suggestion"):
                entry["suggestion"] = suggestion
        unverified_count = len(new_entries)
        reason_detail = (
            "; ".join(e["reason"] for e in new_entries if e.get("reason"))
            or "type cannot be tracked"
        )
        goal_detail = new_entries[0].get("goal", "") if new_entries else ""
        logger.warning(
            "    [TRUSTED ⚠] step %d '%s' — bypassed kernel type-checker "
            "(%d unverified step(s))\n"
            "      Goal      : %s\n"
            "      Reason    : %s\n"
            "      Suggestion: %s",
            tactic_index,
            tac,
            unverified_count,
            goal_detail,
            reason_detail,
            suggestion,
        )
    else:
        logger.debug(
            "    [kernel ✓] step %d '%s' — kernel-verified", tactic_index, tac
        )


def _suggest_for_tactic(tac: str) -> str:
    """Return a human-readable suggestion for resolving a trusted tactic."""
    tac_lower = tac.strip().split()[0] if tac.strip() else ""
    suggestions = {
        "apply": (
            "ensure the hypothesis has type 'A → B' where B matches the goal; "
            "or use 'exact' with a fully-applied proof term"
        ),
        "cases": (
            "use 'cases h' only when h : A ∧ B or h : A ∨ B; "
            "for other types consider 'intro' or 'obtain'"
        ),
        "rcases": (
            "use 'rcases h' only when h : A ∧ B or h : A ∨ B; "
            "for other types consider 'intro' or 'obtain'"
        ),
        "have": (
            "replace 'have h : T := proof' with a 'have h : T' sub-goal "
            "so the sub-proof is kernel-verified separately"
        ),
        "rw": (
            "ensure the rewrite rule is an equality hypothesis (h : a = b) "
            "that has been introduced into the context"
        ),
        "exact": (
            "use a hypothesis name directly, or a projection like 'h.1'/'h.2'; "
            "complex proof terms are not yet supported by the kernel"
        ),
        "contradiction": (
            "introduce a hypothesis that is False or directly contradicts another; "
            "the kernel checks for False or matching negations"
        ),
        "ring": (
            "ensure the goal is an equality between ring expressions; "
            "for numeric goals try 'norm_num' or 'omega'"
        ),
        "norm_num": (
            "ensure the goal is an equality between numeric literals; "
            "for symbolic goals try 'ring'"
        ),
        "omega": (
            "ensure the goal is a linear arithmetic proposition over integers/naturals; "
            "omega cannot handle non-linear or symbolic goals"
        ),
        "simp": (
            "break the goal into smaller pieces with 'constructor'/'cases' "
            "before applying simp, or use 'ring'/'omega' for arithmetic goals"
        ),
    }
    return suggestions.get(tac_lower, "inspect the proof context and goal for type mismatches")


def run_tactics(statement: str, tactics: List[str]) -> ProofState:
    state = ProofState(statement)
    for tactic_index, tac in enumerate(tactics, start=1):
        if state.closed:
            break
        before_trusted = len(state.trusted_steps)
        try:
            state = apply_tactic(state, tac)
        except TacticError as e:
            logger.error("  [dsl error] %s", e)
            break
        _log_tactic_result(tac, tactic_index, before_trusted, state)
    return state


def run_function_proof(statement: str, proof_fn: Callable) -> ProofState:
    sig = inspect.signature(proof_fn)
    state = ProofState(statement)
    try:
        if list(sig.parameters):
            result = proof_fn(state)
            if isinstance(result, ProofState):
                return result
            logger.error("  [proof error] function-style proof must return ProofState")
            state.admitted = True
        else:
            # No-arg function cannot construct a kernel-checkable proof trace.
            logger.error("  [dsl error] no-arg proof function is treated as sorry")
            proof_fn()
            state.admitted = True
    except TacticError as e:
        logger.error("  [dsl error] %s", e)
    except Exception as e:  # pragma: no cover
        logger.error("  [proof error] %s", e)
    return state


def replay_proof(statement: str, tactics: List[str]) -> bool:
    """Replay all tactics and require a fully kernel-verified closure."""
    if not tactics:
        return False

    replay_state = ProofState(statement)
    for tac in tactics:
        if replay_state.closed:
            break
        try:
            replay_state = apply_tactic(replay_state, tac)
        except TacticError:
            return False

    return replay_state.closed and not replay_state.admitted and not replay_state.trusted_steps
