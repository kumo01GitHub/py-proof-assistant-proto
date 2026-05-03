"""Decorator implementations for axiom/theorem/lemma/def_."""

from typing import Callable, List, Optional

from .certificate import issue_certificate
from .registry import register_entry, state_to_status
from .runner import replay_proof, run_function_proof, run_tactics


def axiom(name: str, statement: str):
    def decorator(fn: Callable):
        register_entry(name, {
            "kind": "axiom",
            "name": name,
            "statement": statement,
            "status": "axiom",
            "tactics": [],
        })
        return fn

    return decorator


def _register_with_proof(kind: str, name: str, statement: str, fn: Callable, tactics: Optional[List[str]]) -> Callable:
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

    cert_obj = issue_certificate(statement, replay_source, replay_ok if status == "proved" else False)
    certificate = cert_obj.to_dict() if cert_obj is not None else None

    register_entry(name, {
        "kind": kind,
        "name": name,
        "statement": statement,
        "status": status,
        "trusted_steps": list(state.trusted_steps),
        "tactics": replay_source,
        "certificate": certificate,
        "replay_ok": replay_ok,
    })
    return fn


def theorem(name: str, statement: str, tactics: Optional[List[str]] = None):
    def decorator(fn: Callable):
        return _register_with_proof("theorem", name, statement, fn, tactics)

    return decorator


def lemma(name: str, statement: str, tactics: Optional[List[str]] = None):
    def decorator(fn: Callable):
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
