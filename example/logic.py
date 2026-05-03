"""命題論理の基本定理 — クラスベース API による記述例"""
from zfc_leanpy import Prop, Theorem
from zfc_leanpy.dsl.tactic_objects import (
    intro, constructor, exact, left, apply_, use, simp
)

P, Q, R = Prop("P"), Prop("Q"), Prop("R")

# 恒等関数
class IdProp(Theorem):
    prop = P >> P
    tactics = [intro("h"), exact("h")]

# 連言の交換
class AndComm(Theorem):
    prop = (P & Q) >> (Q & P)
    tactics = [intro("h"), constructor(), exact("h.2"), exact("h.1")]

# 選言の導入 (左)
class OrIntroL(Theorem):
    prop = P >> (P | Q)
    tactics = [intro("h"), left(), exact("h")]

# 連言の結合
class AndAssoc(Theorem):
    prop = ((P & Q) & R) >> (P & (Q & R))
    tactics = [
        intro("h"),
        constructor(),
        exact("h.1.1"),
        constructor(),
        exact("h.1.2"),
        exact("h.2"),
    ]

# 対偶
class Contrapos(Theorem):
    prop = (P >> Q) >> (~Q >> ~P)
    tactics = [intro("hpq"), intro("hnq"), intro("hp"), apply_("hnq"), apply_("hpq"), exact("hp")]

# 存在の導入
class ExistsSelf(Theorem):
    prop = Prop("∀ x, ∃ y, y = x")
    tactics = [intro("x"), use("x"), simp()]
