"""Convenience tactic helper wrappers for function-style proofs."""

from ..kernel import ProofState
from ..tactics import apply_tactic


def intro(state: ProofState, name: str = None) -> ProofState:
    return apply_tactic(state, f"intro {name}" if name else "intro")


def intros(state: ProofState, *names: str) -> ProofState:
    return apply_tactic(state, ("intros " + " ".join(names)) if names else "intros")


def exact(state: ProofState, term: str) -> ProofState:
    return apply_tactic(state, f"exact {term}")


def apply_(state: ProofState, term: str) -> ProofState:
    return apply_tactic(state, f"apply {term}")


def have(state: ProofState, name: str, typ: str) -> ProofState:
    return apply_tactic(state, f"have {name} : {typ}")


def rw(state: ProofState, *rules: str) -> ProofState:
    return apply_tactic(state, f"rw [{', '.join(rules)}]")


def simp(state: ProofState, *lemmas_: str) -> ProofState:
    if lemmas_:
        return apply_tactic(state, f"simp [{', '.join(lemmas_)}]")
    return apply_tactic(state, "simp")


def constructor(state: ProofState) -> ProofState:
    return apply_tactic(state, "constructor")


def use(state: ProofState, term: str) -> ProofState:
    return apply_tactic(state, f"use {term}")


def left(state: ProofState) -> ProofState:
    return apply_tactic(state, "left")


def right(state: ProofState) -> ProofState:
    return apply_tactic(state, "right")


def sorry_(state: ProofState) -> ProofState:
    return apply_tactic(state, "sorry")


def assumption(state: ProofState) -> ProofState:
    return apply_tactic(state, "assumption")


def trivial(state: ProofState) -> ProofState:
    return apply_tactic(state, "trivial")


def contradiction(state: ProofState) -> ProofState:
    return apply_tactic(state, "contradiction")


def ring(state: ProofState) -> ProofState:
    return apply_tactic(state, "ring")


def omega(state: ProofState) -> ProofState:
    return apply_tactic(state, "omega")


def norm_num(state: ProofState) -> ProofState:
    return apply_tactic(state, "norm_num")
