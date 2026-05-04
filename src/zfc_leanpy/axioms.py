"""
axioms.py — ZFC集合論の公理群（Python DSL 形式）

各公理を @axiom デコレータで登録する。
また、文字列辞書 ALL_AXIOMS と補助関数を提供する。

ZFC 8公理:
  extensionality  外延性公理
  empty_set       空集合公理
  pairing         対公理
  union           和集合公理
  power_set       冪集合公理
  infinity        無限公理
  regularity      正則性公理（基礎公理）
  choice          選択公理
"""

from typing import Dict, List, Optional

from .dsl import axiom


# ---------------------------------------------------------------------------
# 公理文字列（プログラム的参照用）
# ---------------------------------------------------------------------------

ALL_AXIOMS: Dict[str, str] = {
    "extensionality": "∀A ∀B (∀x (x∈A ↔ x∈B) → A=B)",
    "empty_set":      "∃x ∀y (y∉x)",
    "pairing":        "∀a ∀b ∃z ∀x (x∈z ↔ x=a ∨ x=b)",
    "union":          "∀F ∃A ∀x (x∈A ↔ ∃B (B∈F ∧ x∈B))",
    "power_set":      "∀x ∃y ∀z (z∈y ↔ z⊆x)",
    "infinity":       "∃x (∅∈x ∧ ∀y (y∈x → y∪{y}∈x))",
    "regularity":     "∀x (x≠∅ → ∃y (y∈x ∧ y∩x=∅))",
    "choice":         "∀F (∅∉F → ∃f ∀A∈F f(A)∈A)",
}


# ---------------------------------------------------------------------------
# 公理登録（Python DSL 形式）
# ---------------------------------------------------------------------------

@axiom("extensionality", ALL_AXIOMS["extensionality"])
def _() -> None: pass  # 外延性公理: 同じ要素を持つ集合は等しい

@axiom("empty_set", ALL_AXIOMS["empty_set"])
def _() -> None: pass  # 空集合公理: 何も要素を持たない集合が存在する

@axiom("pairing", ALL_AXIOMS["pairing"])
def _() -> None: pass  # 対公理: 任意の2集合を要素とする集合が存在する

@axiom("union", ALL_AXIOMS["union"])
def _() -> None: pass  # 和集合公理: 集合族の和集合が存在する

@axiom("power_set", ALL_AXIOMS["power_set"])
def _() -> None: pass  # 冪集合公理: 任意の集合の冪集合が存在する

@axiom("infinity", ALL_AXIOMS["infinity"])
def _() -> None: pass  # 無限公理: 帰納的集合（自然数を含む）が存在する

@axiom("regularity", ALL_AXIOMS["regularity"])
def _() -> None: pass  # 正則性公理: 空でない集合は自身と交わらない要素を持つ

@axiom("choice", ALL_AXIOMS["choice"])
def _() -> None: pass  # 選択公理: 空でない集合族から各要素を選ぶ関数が存在する


# ---------------------------------------------------------------------------
# 補助関数
# ---------------------------------------------------------------------------

def list_zfc_axioms() -> List[str]:
    """ZFC公理名のリストを返す。"""
    return list(ALL_AXIOMS.keys())


def get_axiom(name: str) -> Optional[str]:
    """公理名から文字列を返す。存在しない場合は None。"""
    return ALL_AXIOMS.get(name)
