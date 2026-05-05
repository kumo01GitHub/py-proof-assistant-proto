"""Public DSL API."""

from .registry import (
    reset_registry,
    get_registry,
    get_status,
    get_proof_summary,
    list_axioms,
    list_theorems,
    revalidate_proof,
)
from .decorators import axiom, def_, lemma, theorem
from .helpers import (
    apply_,
    assumption,
    constructor,
    contradiction,
    exact,
    have,
    intro,
    intros,
    left,
    norm_num,
    omega,
    right,
    ring,
    rw,
    simp,
    sorry_,
    trivial,
    use,
)
from ..kernel import ProofState

# クラスベース API
from .prop import Prop, ForAll, Exists
from .class_api import Theorem, Lemma, Axiom
from . import tactic_objects

__all__ = [
    # レジストリ
    "reset_registry",
    "get_registry",
    "list_axioms",
    "list_theorems",
    "get_status",
    "get_proof_summary",
    "revalidate_proof",
    # デコレータ API
    "axiom",
    "theorem",
    "lemma",
    "def_",
    # 関数スタイルの ProofState ヘルパ
    "ProofState",
    "intro",
    "intros",
    "exact",
    "apply_",
    "have",
    "rw",
    "simp",
    "constructor",
    "use",
    "left",
    "right",
    "sorry_",
    "assumption",
    "trivial",
    "contradiction",
    "ring",
    "omega",
    "norm_num",
    # クラスベース API
    "Prop",
    "ForAll",
    "Exists",
    "Theorem",
    "Lemma",
    "Axiom",
    "tactic_objects",
]
