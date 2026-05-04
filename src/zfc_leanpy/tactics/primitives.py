"""Primitive helpers for tactic evaluation."""

from __future__ import annotations

import re
from typing import Optional

from ..formula import (
    FAnd,
    FAll,
    FEq,
    FFalse,
    FImpl,
    FNot,
    FOr,
    FTrue,
    PAndE1,
    PAndE2,
    PRefl,
    PTrueI,
    PVar,
    feq,
    fparse,
    fstr,
    fsubst,
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


def trusted_close(state: ProofState, tag: str, reason: str = "") -> ProofState:
    state.trusted_steps.append(tag)
    state.trusted_reasons.append(reason)
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
        return trusted_close(
            state,
            f"apply {arg}",
            f"hypothesis '{arg}' not found in proof context; "
            "introduce it via 'have' or 'intro' before applying",
        )

    term_type = fparse(term_type_str)
    goal = fparse(state.current_goal() or "")
    if term_type is None or goal is None:
        return trusted_close(
            state,
            f"apply {arg}",
            f"cannot parse type of '{arg}' ('{term_type_str}') or current goal — "
            "type tracking is incomplete for this expression",
        )

    if isinstance(term_type, FImpl) and feq(term_type.r, goal):
        state.trusted_steps.append(f"apply {arg}")
        state.trusted_reasons.append(
            f"partial apply: '{arg}' ({term_type_str}) matches goal conclusion, "
            "but proof term is not kernel-constructed"
        )
        state.replace_goal(fstr(term_type.l))
        return state

    if isinstance(term_type, FNot) and isinstance(goal, FFalse):
        state.trusted_steps.append(f"apply {arg}")
        state.trusted_reasons.append(
            f"partial apply: '{arg}' ({term_type_str}) applied to False goal, "
            "but proof term is not kernel-constructed"
        )
        state.replace_goal(fstr(term_type.x))
        return state

    return trusted_close(
        state,
        f"apply {arg}",
        f"'{arg}' has type '{term_type_str}' whose conclusion does not match goal "
        f"'{state.current_goal()}'; "
        "ensure the hypothesis type ends with the current goal",
    )


def do_cases(state: ProofState, arg: str) -> ProofState:
    """Structural case analysis on a conjunction or disjunction hypothesis.

    For ``h : A ∧ B``: replaces ``h`` with ``h1 : A`` and ``h2 : B`` in the
    current goal's context (sound elimination of ∧).

    For ``h : A ∨ B``: creates two sub-goals — one with a fresh hypothesis for
    the left branch (``h_left : A``) and one for the right branch
    (``h_right : B``) — mirroring Lean's ``cases h`` on ``∨``.

    Falls back to a trusted step with an explanatory reason when the hypothesis
    type cannot be parsed or is not a conjunction/disjunction.
    """
    hyp_name = arg.split()[0].strip() if arg.strip() else ""
    if not hyp_name:
        return trusted_close(
            state,
            "cases",
            "no hypothesis name provided; usage: 'cases <hyp>'",
        )

    hyp_type_str = state.hypotheses.get(hyp_name)
    if hyp_type_str is None:
        return trusted_close(
            state,
            f"cases {hyp_name}",
            f"hypothesis '{hyp_name}' not found in proof context; "
            "ensure it is introduced before calling cases",
        )

    hyp_type = fparse(hyp_type_str)
    if hyp_type is None:
        return trusted_close(
            state,
            f"cases {hyp_name}",
            f"cannot parse type of '{hyp_name}': '{hyp_type_str}' — "
            "structural case analysis requires a parseable proposition",
        )

    if isinstance(hyp_type, FAnd):
        # h : A ∧ B  →  h1 : A,  h2 : B  (sound ∧-elimination)
        h1 = f"{hyp_name}1"
        h2 = f"{hyp_name}2"
        hyps = state.hypotheses
        del hyps[hyp_name]
        hyps[h1] = fstr(hyp_type.l)
        hyps[h2] = fstr(hyp_type.r)
        return state

    if isinstance(hyp_type, FOr):
        # h : A ∨ B  →  two goals: [A-branch], [B-branch]
        current_goal = state.current_goal()
        h_left = f"{hyp_name}_left"
        h_right = f"{hyp_name}_right"

        # Build the right-branch hypothesis map (remove h, add h_right)
        right_hyps = dict(state.hypotheses)
        del right_hyps[hyp_name]
        right_hyps[h_right] = fstr(hyp_type.r)

        # Mutate current (left-branch) hypothesis map
        state.hypotheses[h_left] = fstr(hyp_type.l)
        del state.hypotheses[hyp_name]

        # Insert the right-branch goal after the current goal
        state.goals.insert(1, current_goal)
        state._hyp_stack.insert(1, right_hyps)
        return state

    return trusted_close(
        state,
        f"cases {hyp_name}",
        f"'{hyp_name}' has type '{hyp_type_str}' — structural cases requires ∧ or ∨; "
        "for implications use 'intro', for existentials use 'rcases'",
    )


def do_rw(state: ProofState, rules_text: str) -> ProofState:
    """Apply rewrite rules to the current goal using formula-level substitution.

    Parses ``rw [h1, h2, ...]`` syntax.  For each rule ``h`` that is an
    equality hypothesis ``a = b``, replaces every occurrence of ``a`` with
    ``b`` in the current goal (using ``fsubst``).  Prefix the rule with ``←``
    to rewrite in the reverse direction (``b → a``).

    Falls back to a trusted step with an explanatory reason when a rule cannot
    be applied structurally.
    """
    m = re.search(r"\[([^\]]*)\]", rules_text)
    if not m:
        return trusted_close(
            state,
            "rw",
            "cannot parse rewrite rule list — expected syntax: rw [h] or rw [h1, h2]",
        )

    rules = [r.strip() for r in m.group(1).split(",") if r.strip()]
    if not rules:
        return trusted_close(state, "rw", "empty rewrite rule list")

    goal_str = state.current_goal() or ""

    for rule in rules:
        backwards = rule.startswith("←") or rule.startswith("<-")
        rule_name = rule.lstrip("←").lstrip("<-").strip()

        hyp_type_str = state.hypotheses.get(rule_name)
        if hyp_type_str is None:
            return trusted_close(
                state,
                "rw",
                f"rewrite rule '{rule_name}' not found in proof context; "
                "introduce the equality via 'have' or 'intro' first",
            )

        hyp_type = fparse(hyp_type_str)
        if not isinstance(hyp_type, FEq):
            return trusted_close(
                state,
                "rw",
                f"'{rule_name}' has type '{hyp_type_str}' — rw requires an equality (a = b)",
            )

        lhs, rhs = hyp_type.l, hyp_type.r
        if backwards:
            lhs, rhs = rhs, lhs

        goal_f = fparse(goal_str)
        if goal_f is None:
            return trusted_close(
                state,
                "rw",
                f"cannot parse current goal '{goal_str}' for rewriting",
            )

        new_goal_f = fsubst(goal_f, lhs, rhs)
        goal_str = fstr(new_goal_f)
        state.replace_goal(goal_str)

    # After all rewrites, try a trivial kernel close (e.g. rfl after rw)
    if try_kernel_close_simple(state):
        return state

    # Goal was transformed structurally; no trusted mark needed
    return state
