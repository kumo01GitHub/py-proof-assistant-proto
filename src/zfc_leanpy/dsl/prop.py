"""Prop — Python オブジェクトとして命題を構築するクラス。"""

from typing import Union

from ..formula import FAnd, FAll, FEx, FIff, FImpl, FNot, FOr, FVar, fparse, fstr
from ..formula.ast import _F


class Prop:
    """命題を表すオブジェクト。演算子で結合できる。

    Examples:
        P = Prop("P")
        Q = Prop("Q")
        goal = (P & Q) >> (Q & P)   # P ∧ Q → Q ∧ P
    """

    def __init__(self, expr: "Union[str, _F]") -> None:
        if isinstance(expr, str):
            parsed = fparse(expr)
            # パース失敗なら命題変数として扱う
            self._f: _F = parsed if parsed is not None else FVar(expr)
        else:
            # すでに _F オブジェクト（内部用）
            self._f = expr

    # ── 演算子オーバーロード ──────────────────────────────────────

    def __and__(self, other: "Prop") -> "Prop":
        """P & Q  →  P ∧ Q"""
        return Prop(FAnd(self._f, other._f))

    def __or__(self, other: "Prop") -> "Prop":
        """P | Q  →  P ∨ Q"""
        return Prop(FOr(self._f, other._f))

    def __rshift__(self, other: "Prop") -> "Prop":
        """P >> Q  →  P → Q"""
        return Prop(FImpl(self._f, other._f))

    def __invert__(self) -> "Prop":
        """~P  →  ¬P"""
        return Prop(FNot(self._f))

    def iff(self, other: "Prop") -> "Prop":
        """P.iff(Q)  →  P ↔ Q"""
        return Prop(FIff(self._f, other._f))

    # ── 文字列変換 ───────────────────────────────────────────────

    def __str__(self) -> str:
        return fstr(self._f) if self._f is not None else ""

    def __repr__(self) -> str:
        return f"Prop({str(self)!r})"


def ForAll(var: str, body: Prop) -> Prop:
    """∀ var, body"""
    return Prop(FAll(var, body._f))


def Exists(var: str, body: Prop) -> Prop:
    """∃ var, body"""
    return Prop(FEx(var, body._f))
