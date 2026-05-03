"""Formula parser/printer/equality/substitution helpers."""

from __future__ import annotations

from typing import List, Optional

from .ast import FAll, FAnd, FEq, FEx, FFalse, FIff, FImpl, FNot, FOr, FTrue, FVar, FApp, _F


def _strip_outer_parens(s: str) -> str:
    s = s.strip()
    while s.startswith("(") and s.endswith(")"):
        depth = 0
        ok = True
        for i, ch in enumerate(s):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0 and i < len(s) - 1:
                    ok = False
                    break
        if ok and depth == 0:
            s = s[1:-1].strip()
        else:
            break
    return s


def _split_top_level(s: str, op: str) -> Optional[List[str]]:
    depth = 0
    i = 0
    while i <= len(s) - len(op):
        ch = s[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if depth == 0 and s[i : i + len(op)] == op:
            return [s[:i].strip(), s[i + len(op) :].strip()]
        i += 1
    return None


def fparse(text: str) -> Optional[_F]:
    if text is None:
        return None

    s = _strip_outer_parens(text.strip())
    if not s:
        return None

    if s == "True":
        return FTrue()
    if s == "False":
        return FFalse()

    if s.startswith("∀") or s.startswith("∃"):
        q = s[0]
        rest = s[1:].strip()
        if "," in rest:
            head, body = rest.split(",", 1)
            fb = fparse(body.strip())
            if fb is None:
                return None
            vars_ = [v for v in head.strip().split() if v]
            if not vars_:
                return None
            out = fb
            for var in reversed(vars_):
                if q == "∀":
                    out = FAll(var, out)
                else:
                    out = FEx(var, out)
            return out

    for op, cls in (("↔", FIff), ("->", FImpl), ("→", FImpl), ("∨", FOr), ("∧", FAnd)):
        parts = _split_top_level(s, op)
        if parts:
            l = fparse(parts[0])
            r = fparse(parts[1])
            if l is None or r is None:
                return None
            return cls(l, r)

    if s.startswith("¬"):
        x = fparse(s[1:].strip())
        return FNot(x) if x is not None else None

    eq = _split_top_level(s, "=")
    if eq:
        return FEq(eq[0], eq[1])

    return FVar(s)


def fstr(f: _F) -> str:
    if isinstance(f, FVar):
        return f.name
    if isinstance(f, FTrue):
        return "True"
    if isinstance(f, FFalse):
        return "False"
    if isinstance(f, FImpl):
        return f"({fstr(f.l)} → {fstr(f.r)})"
    if isinstance(f, FAnd):
        return f"({fstr(f.l)} ∧ {fstr(f.r)})"
    if isinstance(f, FOr):
        return f"({fstr(f.l)} ∨ {fstr(f.r)})"
    if isinstance(f, FIff):
        return f"({fstr(f.l)} ↔ {fstr(f.r)})"
    if isinstance(f, FNot):
        return f"¬{fstr(f.x)}"
    if isinstance(f, FAll):
        return f"∀ {f.var}, {fstr(f.body)}"
    if isinstance(f, FEx):
        return f"∃ {f.var}, {fstr(f.body)}"
    if isinstance(f, FEq):
        return f"{f.l} = {f.r}"
    if isinstance(f, FApp):
        return f"{f.fn}({', '.join(f.args)})"
    return str(f)


def feq(a: _F, b: _F) -> bool:
    return a == b


def fsubst(f: _F, var: str, replacement: str) -> _F:
    if isinstance(f, FVar):
        return FVar(replacement if f.name == var else f.name)
    if isinstance(f, FImpl):
        return FImpl(fsubst(f.l, var, replacement), fsubst(f.r, var, replacement))
    if isinstance(f, FAnd):
        return FAnd(fsubst(f.l, var, replacement), fsubst(f.r, var, replacement))
    if isinstance(f, FOr):
        return FOr(fsubst(f.l, var, replacement), fsubst(f.r, var, replacement))
    if isinstance(f, FIff):
        return FIff(fsubst(f.l, var, replacement), fsubst(f.r, var, replacement))
    if isinstance(f, FNot):
        return FNot(fsubst(f.x, var, replacement))
    if isinstance(f, FAll):
        if f.var == var:
            return f
        return FAll(f.var, fsubst(f.body, var, replacement))
    if isinstance(f, FEx):
        if f.var == var:
            return f
        return FEx(f.var, fsubst(f.body, var, replacement))
    if isinstance(f, FEq):
        l = replacement if f.l == var else f.l
        r = replacement if f.r == var else f.r
        return FEq(l, r)
    return f
