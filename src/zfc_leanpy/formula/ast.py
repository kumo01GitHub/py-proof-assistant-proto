"""Formula AST node definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Union


@dataclass(frozen=True)
class FVar:
    name: str


@dataclass(frozen=True)
class FImpl:
    l: "_F"
    r: "_F"


@dataclass(frozen=True)
class FAnd:
    l: "_F"
    r: "_F"


@dataclass(frozen=True)
class FOr:
    l: "_F"
    r: "_F"


@dataclass(frozen=True)
class FNot:
    x: "_F"


@dataclass(frozen=True)
class FIff:
    l: "_F"
    r: "_F"


@dataclass(frozen=True)
class FAll:
    var: str
    body: "_F"


@dataclass(frozen=True)
class FEx:
    var: str
    body: "_F"


@dataclass(frozen=True)
class FEq:
    l: str
    r: str


@dataclass(frozen=True)
class FApp:
    fn: str
    args: List[str]


@dataclass(frozen=True)
class FTrue:
    pass


@dataclass(frozen=True)
class FFalse:
    pass


_F = Union[FVar, FImpl, FAnd, FOr, FNot, FIff, FAll, FEx, FEq, FApp, FTrue, FFalse]
