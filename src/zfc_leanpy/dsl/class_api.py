"""クラスベース API — Theorem / Lemma / Axiom 基底クラス。

使用例:
    from zfc_leanpy import Prop, Theorem, Axiom
    from zfc_leanpy.dsl.tactic_objects import intro, constructor, exact

    P, Q = Prop("P"), Prop("Q")

    class AndComm(Theorem):
        prop = (P & Q) >> (Q & P)
        tactics = [intro("h"), constructor(), exact("h.2"), exact("h.1")]

    class EmptySet(Axiom):
        prop = Prop("∃ x, ∀ y, y ∉ x")
"""

from .decorators import _register_with_proof
from .registry import register_entry


def _tactics_to_str(tactics: list) -> list:
    """タクティクオブジェクトまたは文字列を文字列リストに変換する。"""
    return [str(t) for t in tactics]


# ── Theorem / Lemma ────────────────────────────────────────────────

class _TheoremMeta(type):
    def __new__(mcs, name: str, bases: tuple, namespace: dict) -> "_TheoremMeta":
        cls = super().__new__(mcs, name, bases, namespace)

        # 直接の親に _TheoremMeta を持つクラスがなければ基底クラス自身なのでスキップ
        meta_bases = [b for b in bases if isinstance(b, _TheoremMeta)]
        if not meta_bases:
            return cls

        prop = namespace.get("prop")
        if prop is None:
            return cls

        stmt = str(prop)
        tactics_raw = namespace.get("tactics", [])
        tactics_str = _tactics_to_str(tactics_raw)
        entry_name = namespace.get("name", name)

        # 基底クラス (Theorem / Lemma) から kind を決定
        kind = "theorem"
        for base in meta_bases:
            if hasattr(base, "_default_kind"):
                kind = base._default_kind
                break

        _register_with_proof(kind, entry_name, stmt, lambda: None, tactics_str)
        return cls


class Theorem(metaclass=_TheoremMeta):
    """定理の基底クラス。サブクラス定義時に自動登録される。

    Attributes:
        prop:    Prop オブジェクトで記述した命題
        tactics: タクティクオブジェクトまたは文字列のリスト
        name:    登録名（省略時はクラス名）
    """
    _default_kind = "theorem"


class Lemma(metaclass=_TheoremMeta):
    """補題の基底クラス。Theorem と同じ動作だが kind="lemma"。"""
    _default_kind = "lemma"


# ── Axiom ─────────────────────────────────────────────────────────

class _AxiomMeta(type):
    def __new__(mcs, name: str, bases: tuple, namespace: dict) -> "_AxiomMeta":
        cls = super().__new__(mcs, name, bases, namespace)

        meta_bases = [b for b in bases if isinstance(b, _AxiomMeta)]
        if not meta_bases:
            return cls

        prop = namespace.get("prop")
        if prop is None:
            return cls

        stmt = str(prop)
        entry_name = namespace.get("name", name)

        register_entry(entry_name, {
            "kind": "axiom",
            "name": entry_name,
            "statement": stmt,
            "status": "axiom",
            "tactics": [],
        })
        return cls


class Axiom(metaclass=_AxiomMeta):
    """公理の基底クラス。サブクラス定義時に自動登録される。

    Attributes:
        prop: Prop オブジェクトで記述した命題
        name: 登録名（省略時はクラス名）
    """
