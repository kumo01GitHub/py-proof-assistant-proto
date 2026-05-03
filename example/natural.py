"""自然数の存在（ペアノ公理風） — クラスベース API による記述例"""
from zfc_leanpy import Prop, Theorem, Axiom
from zfc_leanpy.dsl.tactic_objects import intro, constructor, exact, sorry_

# 公理
class NatZero(Axiom):
    prop = Prop("∃ n, n = 0")

class NatSucc(Axiom):
    prop = Prop("∀ n, ∃ m, m = n + 1")

# 定理: 0 の一意性
class ZeroUnique(Theorem):
    prop = Prop("∀ n m, n = 0 ∧ m = 0 → n = m")
    tactics = [intro("n"), intro("m"), intro("h"), sorry_()]
