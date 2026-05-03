"""和集合の存在 — クラスベース API による記述例"""
from zfc_leanpy import Prop, Theorem, Axiom
from zfc_leanpy.dsl.tactic_objects import intro, sorry_

# ZFC 和集合公理
class UnionAxiom(Axiom):
    prop = Prop("∀ A B, ∃ C, ∀ x, x ∈ C ↔ x ∈ A ∨ x ∈ B")

# 定理: 和集合の交換
class UnionComm(Theorem):
    prop = Prop("∀ A B, A ∪ B = B ∪ A")
    tactics = [intro("A"), intro("B"), sorry_()]
