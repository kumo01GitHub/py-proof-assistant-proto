"""Primitive helpers for tactic evaluation."""

from __future__ import annotations

from typing import Optional

from ..formula import (
    FAll,
    FEq,
    FFalse,
    FImpl,
    FNot,
    FTrue,
    PAndE1,
    PAndE2,
    PRefl,
    PTrueI,
    PVar,
    feq,
    fparse,
    fstr,
)
from ..kernel import ProofState, TacticError


def next_hyp_name(state: ProofState) -> str:
    i = 1
    while f"h{i}" in state.hypotheses:
        i += 1
    return f"h{i}"


def normalize_tactic_text(text: str) -> str:
    t = text.strip().rstrip(",")
    if t.startswith("·"):
        t = t[1:].strip()
    return t


def parse_proof_term(expr: str) -> Optional[object]:
    parts = expr.split(".")
    if not parts:
        return None
    base = parts[0].strip()
    if not base:
        return None
    term: object = PVar(base)
    for p in parts[1:]:
        pp = p.strip()
        if pp == "1":
            term = PAndE1(term)
        elif pp == "2":
            term = PAndE2(term)
        else:
            return None
    return term


def trusted_close(state: ProofState, tag: str) -> ProofState:
    state.trusted_steps.append(tag)
    state.pop_goal()
    return state


def try_kernel_close_simple(state: ProofState) -> bool:
    goal = fparse(state.current_goal() or "")
    if goal is None:
        return False
    if isinstance(goal, FTrue):
        state.close_with(PTrueI())
        return True
    if isinstance(goal, FEq) and goal.l == goal.r:
        state.close_with(PRefl(goal.l))
        return True
    for name, typ in state.hypotheses.items():
        hf = fparse(typ)
        if hf is not None and feq(hf, goal):
            state.close_with(PVar(name))
            return True
    return False


def do_intro(state: ProofState, name: Optional[str]) -> ProofState:
    goal = state.current_goal()
    gf = fparse(goal or "")
    if gf is None:
        raise TacticError(f"intro: cannot parse goal '{goal}'")

    hyp_name = name.strip() if name else next_hyp_name(state)

    if isinstance(gf, FImpl):
        state.hypotheses[hyp_name] = fstr(gf.l)
        state.replace_goal(fstr(gf.r))
        return state

    if isinstance(gf, FAll):
        state.replace_goal(fstr(gf.body))
        return state

    if isinstance(gf, FNot):
        state.hypotheses[hyp_name] = fstr(gf.x)
        state.replace_goal("False")
        return state

    raise TacticError(f"intro: goal is not implication/forall/not, got '{goal}'")


def do_apply(state: ProofState, arg: str) -> ProofState:
    term_type_str = state.hypotheses.get(arg)
    if term_type_str is None:
        return trusted_close(state, f"apply {arg}")

    term_type = fparse(term_type_str)
    goal = fparse(state.current_goal() or "")
    if term_type is None or goal is None:
        return trusted_close(state, f"apply {arg}")

    if isinstance(term_type, FImpl) and feq(term_type.r, goal):
        state.trusted_steps.append(f"apply {arg}")
        state.replace_goal(fstr(term_type.l))
        return state

    if isinstance(term_type, FNot) and isinstance(goal, FFalse):
        state.trusted_steps.append(f"apply {arg}")
        state.replace_goal(fstr(term_type.x))
        return state

    return trusted_close(state, f"apply {arg}")
