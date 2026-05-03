"""Proof-term AST definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from .ast import _F


class ProofTypeError(Exception):
    pass


@dataclass(frozen=True)
class PVar:
    name: str


@dataclass(frozen=True)
class PAndE1:
    inner: "PTerm"


@dataclass(frozen=True)
class PAndE2:
    inner: "PTerm"


@dataclass(frozen=True)
class PAndI:
    left: "PTerm"
    right: "PTerm"


@dataclass(frozen=True)
class POrIL:
    pf: "PTerm"
    right_type: _F


@dataclass(frozen=True)
class POrIR:
    left_type: _F
    pf: "PTerm"


@dataclass(frozen=True)
class PLam:
    var: str
    dom: _F
    body: "PTerm"


@dataclass(frozen=True)
class PApp:
    fn: "PTerm"
    arg: "PTerm"


@dataclass(frozen=True)
class PRefl:
    term: str


@dataclass(frozen=True)
class PTrueI:
    pass


# ── 決定手続き証明項 ──────────────────────────────────────────────

@dataclass(frozen=True)
class PRing:
    """環の等式 lhs = rhs を多項式正規化で証明する証明項。"""
    lhs: str
    rhs: str


@dataclass(frozen=True)
class PSimp:
    """命題論理の真理値表によりゴールを証明する証明項。
    goal_str: fstr で表現されたゴール式。
    """
    goal_str: str


@dataclass(frozen=True)
class POmega:
    """線形算術の Fourier-Motzkin 消去によりゴールを証明する証明項。
    goal_str: 線形算術制約文字列（例: "n + 1 > 0"）。
    """
    goal_str: str


@dataclass(frozen=True)
class PNormNum:
    """定数式の算術評価により等式を証明する証明項（norm_num 用）。"""
    lhs: str
    rhs: str


PTerm = Union[
    PVar, PAndE1, PAndE2, PAndI, POrIL, POrIR, PLam, PApp, PRefl, PTrueI,
    PRing, PSimp, POmega, PNormNum,
]
