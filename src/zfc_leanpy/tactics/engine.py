"""Main tactic dispatcher."""

from __future__ import annotations

from ..formula import (
    FAll, FAnd, FEq, FEx, FIff, FImpl, FNot, FOr, FTrue,
    PNormNum, POmega, PRing, PRefl, PSimp, PTrueI, PVar,
    feq, fparse, fstr, fsubst,
)
from ..kernel import ProofState, TacticError
from .primitives import (
    do_apply,
    do_intro,
    normalize_tactic_text,
    parse_proof_term,
    trusted_close,
    try_kernel_close_simple,
)


def apply_tactic(state: ProofState, tactic: str) -> ProofState:
    tac = normalize_tactic_text(tactic)
    if not tac or state.closed:
        return state

    state.tactic_trace.append(tac)

    if tac == "admit" or tac == "sorry":
        state.admitted = True
        state.pop_goal()
        return state

    if tac.startswith("intro"):
        parts = tac.split()
        names = parts[1:]
        if not names:
            return do_intro(state, None)
        for name in names:
            state = do_intro(state, name)
        return state

    if tac.startswith("intros"):
        parts = tac.split()
        names = parts[1:] if len(parts) > 1 else []
        if not names:
            while True:
                goal = fparse(state.current_goal() or "")
                if not isinstance(goal, (FImpl, FAll, FNot)):
                    break
                state = do_intro(state, None)
            return state
        for n in names:
            state = do_intro(state, n)
        return state

    if tac.startswith("exact "):
        expr = tac[len("exact ") :].strip()
        term = parse_proof_term(expr)
        if term is not None:
            state.close_with(term)
            return state
        if expr in state.hypotheses:
            raise TacticError(f"exact: failed to build proof term for '{expr}'")
        return trusted_close(state, f"exact {expr}")

    if tac == "assumption":
        goal = fparse(state.current_goal() or "")
        if goal is None:
            raise TacticError("assumption: cannot parse goal")
        for name, typ in state.hypotheses.items():
            hf = fparse(typ)
            if hf is not None and feq(hf, goal):
                state.close_with(PVar(name))
                return state
        raise TacticError("assumption: no matching hypothesis")

    if tac == "rfl":
        goal = fparse(state.current_goal() or "")
        if not isinstance(goal, FEq):
            raise TacticError("rfl: goal is not equality")
        if goal.l != goal.r:
            raise TacticError("rfl: goal is not reflexive")
        state.close_with(PRefl(goal.l))
        return state

    if tac == "trivial":
        goal = fparse(state.current_goal() or "")
        if isinstance(goal, FTrue):
            state.close_with(PTrueI())
            return state
        if isinstance(goal, FEq) and goal.l == goal.r:
            state.close_with(PRefl(goal.l))
            return state
        for name, typ in state.hypotheses.items():
            hf = fparse(typ)
            if hf is not None and feq(hf, goal):
                state.close_with(PVar(name))
                return state
        raise TacticError("trivial: failed")

    if tac in ("constructor", "split"):
        goal = fparse(state.current_goal() or "")
        if isinstance(goal, FAnd):
            state.replace_goal(fstr(goal.r))
            state.push_goal(fstr(goal.l))
            return state
        if isinstance(goal, FIff):
            left = FImpl(goal.l, goal.r)
            right = FImpl(goal.r, goal.l)
            state.replace_goal(fstr(right))
            state.push_goal(fstr(left))
            return state
        raise TacticError(f"{tac}: goal is not and/iff")

    if tac == "left":
        goal = fparse(state.current_goal() or "")
        if not isinstance(goal, FOr):
            raise TacticError("left: goal is not disjunction")
        state.replace_goal(fstr(goal.l))
        return state

    if tac == "right":
        goal = fparse(state.current_goal() or "")
        if not isinstance(goal, FOr):
            raise TacticError("right: goal is not disjunction")
        state.replace_goal(fstr(goal.r))
        return state

    if tac.startswith("use "):
        term = tac[len("use ") :].strip()
        goal = fparse(state.current_goal() or "")
        if not isinstance(goal, FEx):
            raise TacticError("use: goal is not existential")
        state.replace_goal(fstr(fsubst(goal.body, goal.var, term)))
        return state

    if tac.startswith("apply "):
        return do_apply(state, tac[len("apply ") :].strip())

    if tac.startswith("have "):
        payload = tac[len("have ") :].strip()
        if ":=" in payload:
            lhs, _rhs = payload.split(":=", 1)
            if ":" in lhs:
                n, typ = lhs.split(":", 1)
                state.hypotheses[n.strip()] = typ.strip()
                state.trusted_steps.append("have :=")
                return state
            raise TacticError("have: invalid syntax")
        if ":" in payload:
            n, typ = payload.split(":", 1)
            state.split_have(typ.strip(), n.strip(), typ.strip())
            return state
        raise TacticError("have: invalid syntax")

    if tac == "contradiction":
        if try_kernel_close_simple(state):
            return state
        return trusted_close(state, "contradiction")

    if tac == "ring":
        if try_kernel_close_simple(state):
            return state
        goal = fparse(state.current_goal() or "")
        if isinstance(goal, FEq):
            try:
                state.close_with(PRing(goal.l, goal.r))
                return state
            except TacticError:
                pass
        return trusted_close(state, "ring")

    if tac == "norm_num":
        if try_kernel_close_simple(state):
            return state
        goal = fparse(state.current_goal() or "")
        if isinstance(goal, FEq):
            try:
                state.close_with(PNormNum(goal.l, goal.r))
                return state
            except TacticError:
                pass
        return trusted_close(state, "norm_num")

    if tac == "omega":
        if try_kernel_close_simple(state):
            return state
        goal_str = state.current_goal() or ""
        try:
            state.close_with(POmega(goal_str))
            return state
        except TacticError:
            pass
        return trusted_close(state, "omega")

    if tac.startswith("simp"):
        if try_kernel_close_simple(state):
            return state
        goal_str = state.current_goal() or ""
        try:
            state.close_with(PSimp(goal_str))
            return state
        except TacticError:
            pass
        return trusted_close(state, "simp")

    if tac.startswith("rw") or tac in ("cases", "rcases"):
        if try_kernel_close_simple(state):
            return state
        return trusted_close(state, tac.split()[0])

    raise TacticError(f"unknown tactic: {tac}")
