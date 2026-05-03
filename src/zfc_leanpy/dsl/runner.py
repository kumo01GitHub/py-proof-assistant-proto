"""Proof execution helpers used by theorem/lemma decorators."""

import inspect
from typing import Callable, List

from ..kernel import ProofState, TacticError
from ..logger import get_logger
from ..tactics import apply_tactic


logger = get_logger(__name__)


def run_tactics(statement: str, tactics: List[str]) -> ProofState:
    state = ProofState(statement)
    for tac in tactics:
        if state.closed:
            break
        try:
            state = apply_tactic(state, tac)
        except TacticError as e:
            logger.error("  [dsl error] %s", e)
            break
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
