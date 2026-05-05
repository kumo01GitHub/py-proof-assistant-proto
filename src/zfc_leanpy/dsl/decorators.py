"""Decorator implementations for axiom/theorem/lemma/def_."""

from typing import Any, Callable, Dict, List, Optional

from ..logger import get_logger
from .registry import register_entry, state_to_status
from .runner import replay_proof, run_function_proof, run_tactics

logger = get_logger(__name__)


def axiom(name: str, statement: str) -> Callable[[Callable], Callable]:
    def decorator(fn: Callable) -> Callable:
        register_entry(name, {
            "kind": "axiom",
            "name": name,
            "statement": statement,
            "status": "axiom",
            "tactics": [],
        })
        return fn

    return decorator


def _log_proof_status(kind: str, name: str, status: str, trusted_steps: List[Dict[str, Any]]) -> None:
    """Log the proof registration outcome with explicit status markers."""
    if status == "proved":
        logger.info("[%s] %s — [PROVED ✓] kernel-verified", kind, name)
    elif status == "sorry":
        logger.warning(
            "[%s] %s — [SORRY ✗] proof admitted with sorry",
            kind, name,
        )
    elif status == "trusted":
        unverified_count = len(trusted_steps)
        logger.warning(
            "[%s] %s — [TRUSTED ⚠] %d unverified step(s)"
            " (use get_proof_summary() for step details)",
            kind, name, unverified_count,
        )
    else:
        logger.warning(
            "[%s] %s — [INCOMPLETE ✗] %s",
            kind, name, status,
        )


def _register_with_proof(
    kind: str,
    name: str,
    statement: str,
    fn: Callable,
    tactics: Optional[List[str]],
) -> Callable:
    if tactics is not None:
        state = run_tactics(statement, tactics)
        replay_source = list(tactics)
    else:
        state = run_function_proof(statement, fn)
        replay_source = list(state.tactic_trace)

    replay_ok = replay_proof(statement, replay_source)
    status = state_to_status(
        state.admitted,
        state.closed,
        len(state.goals),
        len(state.trusted_steps),
        replay_ok,
    )

    register_entry(name, {
        "kind": kind,
        "name": name,
        "statement": statement,
        "status": status,
        "trusted_steps": [dict(s) for s in state.trusted_steps],
        "tactics": replay_source,
        "replay_ok": replay_ok,
    })

    _log_proof_status(kind, name, status, list(state.trusted_steps))
    return fn


def theorem(name: str, statement: str, tactics: Optional[List[str]] = None) -> Callable[[Callable], Callable]:
    def decorator(fn: Callable) -> Callable:
        return _register_with_proof("theorem", name, statement, fn, tactics)

    return decorator


def lemma(name: str, statement: str, tactics: Optional[List[str]] = None) -> Callable[[Callable], Callable]:
    def decorator(fn: Callable) -> Callable:
        return _register_with_proof("lemma", name, statement, fn, tactics)

    return decorator


def def_(name: str, body: str) -> None:
    register_entry(name, {
        "kind": "def",
        "name": name,
        "body": body,
        "status": "defined",
        "tactics": [],
    })
