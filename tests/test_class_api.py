"""クラスベース API (Prop / Theorem / Axiom / tactic_objects) のテスト。"""

import pytest
from zfc_leanpy import dsl, Prop, ForAll, Exists, Theorem, Lemma, Axiom, tactic_objects
from zfc_leanpy.dsl.tactic_objects import (
    intro, intros, exact, assumption, rfl, trivial,
    constructor, split, left, right, use,
    apply_, have, rw, simp, ring, omega, sorry_, contradiction,
)


# ── Prop ──────────────────────────────────────────────────────────

class TestProp:
    def test_variable(self):
        P = Prop("P")
        assert str(P) == "P"

    def test_and(self):
        P, Q = Prop("P"), Prop("Q")
        assert str(P & Q) == "(P ∧ Q)"

    def test_or(self):
        P, Q = Prop("P"), Prop("Q")
        assert str(P | Q) == "(P ∨ Q)"

    def test_implies(self):
        P, Q = Prop("P"), Prop("Q")
        assert str(P >> Q) == "(P → Q)"

    def test_not(self):
        P = Prop("P")
        assert str(~P) == "¬P"

    def test_iff(self):
        P, Q = Prop("P"), Prop("Q")
        assert str(P.iff(Q)) == "(P ↔ Q)"

    def test_complex(self):
        P, Q = Prop("P"), Prop("Q")
        goal = (P & Q) >> (Q & P)
        assert "→" in str(goal)
        assert "∧" in str(goal)

    def test_forall(self):
        P = Prop("P")
        result = ForAll("x", P)
        assert "∀" in str(result)

    def test_exists(self):
        P = Prop("P")
        result = Exists("x", P)
        assert "∃" in str(result)

    def test_from_existing_formula(self):
        P, Q = Prop("P ∧ Q"), Prop("Q ∧ P")
        goal = P >> Q
        assert str(goal) != ""


# ── tactic_objects ────────────────────────────────────────────────

class TestTacticObjects:
    def test_intro(self):
        assert str(intro("h")) == "intro h"

    def test_intro_no_arg(self):
        assert str(intro()) == "intro"

    def test_intros(self):
        assert str(intros("h1", "h2")) == "intros h1 h2"

    def test_intros_no_arg(self):
        assert str(intros()) == "intros"

    def test_exact(self):
        assert str(exact("h")) == "exact h"

    def test_exact_projection(self):
        assert str(exact("h.1")) == "exact h.1"

    def test_assumption(self):
        assert str(assumption()) == "assumption"

    def test_rfl(self):
        assert str(rfl()) == "rfl"

    def test_trivial(self):
        assert str(trivial()) == "trivial"

    def test_constructor(self):
        assert str(constructor()) == "constructor"

    def test_split(self):
        assert str(split()) == "split"

    def test_left(self):
        assert str(left()) == "left"

    def test_right(self):
        assert str(right()) == "right"

    def test_use(self):
        assert str(use("t")) == "use t"

    def test_apply_(self):
        assert str(apply_("h")) == "apply h"

    def test_have(self):
        assert str(have("h", "P ∧ Q")) == "have h : P ∧ Q"

    def test_rw(self):
        assert str(rw("h1", "h2")) == "rw [h1, h2]"

    def test_simp_no_arg(self):
        assert str(simp()) == "simp"

    def test_simp_with_lemmas(self):
        assert str(simp("h1", "h2")) == "simp [h1, h2]"

    def test_ring(self):
        assert str(ring()) == "ring"

    def test_omega(self):
        assert str(omega()) == "omega"

    def test_sorry_(self):
        assert str(sorry_()) == "sorry"

    def test_contradiction(self):
        assert str(contradiction()) == "contradiction"


# ── Theorem クラス API ───────────────────────────────────────────

class TestTheoremClassAPI:
    def test_theorem_registers(self, clear_registry):
        P, Q = Prop("P"), Prop("Q")

        class AndComm(Theorem):
            prop = (P & Q) >> (Q & P)
            tactics = [intro("h"), constructor(), exact("h.2"), exact("h.1")]

        entry = dsl.get_registry().get("AndComm")
        assert entry is not None
        assert entry["kind"] == "theorem"
        assert entry["status"] == "proved"

    def test_theorem_custom_name(self, clear_registry):
        P = Prop("P")

        class _MyThm(Theorem):
            name = "my_custom"
            prop = P >> P
            tactics = [intro("h"), exact("h")]

        assert dsl.get_registry().get("my_custom") is not None

    def test_lemma_registers_as_lemma(self, clear_registry):
        P, Q = Prop("P"), Prop("Q")

        class AndCommLemma(Lemma):
            prop = (P & Q) >> (Q & P)
            tactics = [intro("h"), constructor(), exact("h.2"), exact("h.1")]

        entry = dsl.get_registry().get("AndCommLemma")
        assert entry is not None
        assert entry["kind"] == "lemma"

    def test_theorem_with_sorry_is_sorry(self, clear_registry):
        P = Prop("P")

        class SorryThm(Theorem):
            prop = P >> P
            tactics = [sorry_()]

        entry = dsl.get_registry().get("SorryThm")
        assert entry["status"] == "sorry"

    def test_theorem_string_tactics_also_work(self, clear_registry):
        P, Q = Prop("P"), Prop("Q")

        class MixedThm(Theorem):
            prop = (P & Q) >> (Q & P)
            tactics = ["intro h", "constructor", "exact h.2", "exact h.1"]

        entry = dsl.get_registry().get("MixedThm")
        assert entry["status"] == "proved"


# ── Axiom クラス API ─────────────────────────────────────────────

class TestAxiomClassAPI:
    def test_axiom_registers(self, clear_registry):
        class EmptySet(Axiom):
            prop = Prop("∃ x, ∀ y, ¬(y = x)")

        entry = dsl.get_registry().get("EmptySet")
        assert entry is not None
        assert entry["kind"] == "axiom"
        assert entry["status"] == "axiom"

    def test_axiom_custom_name(self, clear_registry):
        class _Ax(Axiom):
            name = "my_axiom"
            prop = Prop("P")

        assert dsl.get_registry().get("my_axiom") is not None
