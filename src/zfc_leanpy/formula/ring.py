"""Ring arithmetic decision procedure.

多項式正規化によって等式 lhs = rhs を判定する。
変数を含む記号式に対応: a^2 - b^2 = (a+b)*(a-b) など。
"""

from __future__ import annotations

import re
from fractions import Fraction
from typing import Dict, List, Optional, Tuple

# 単項式: ソート済みの (変数名, 指数) タプル
Monomial = Tuple[Tuple[str, int], ...]
# 多項式: 単項式 → 係数
Polynomial = Dict[Monomial, Fraction]


# ── 多項式演算 ────────────────────────────────────────────────────

def _mon_mul(a: Monomial, b: Monomial) -> Monomial:
    d: Dict[str, int] = {}
    for var, exp in a:
        d[var] = d.get(var, 0) + exp
    for var, exp in b:
        d[var] = d.get(var, 0) + exp
    return tuple(sorted((v, e) for v, e in d.items() if e != 0))


def _add(a: Polynomial, b: Polynomial) -> Polynomial:
    r = dict(a)
    for m, c in b.items():
        r[m] = r.get(m, Fraction(0)) + c
    return {m: c for m, c in r.items() if c != 0}


def _neg(a: Polynomial) -> Polynomial:
    return {m: -c for m, c in a.items()}


def _mul(a: Polynomial, b: Polynomial) -> Polynomial:
    r: Polynomial = {}
    for ma, ca in a.items():
        for mb, cb in b.items():
            m = _mon_mul(ma, mb)
            r[m] = r.get(m, Fraction(0)) + ca * cb
    return {m: c for m, c in r.items() if c != 0}


def _pow(base: Polynomial, exp: int) -> Polynomial:
    if exp < 0:
        raise ValueError("Negative exponents not supported")
    result: Polynomial = {(): Fraction(1)}
    for _ in range(exp):
        result = _mul(result, base)
    return result


# ── トークナイザ / 再帰下降パーサ ────────────────────────────────

_TOKEN = re.compile(r'\d+|[A-Za-z_]\w*|[+\-*/^()]')


class _Tok:
    def __init__(self, text: str) -> None:
        self._ts: List[str] = _TOKEN.findall(text.replace(' ', '').replace('\t', ''))
        self._i = 0

    def peek(self) -> Optional[str]:
        return self._ts[self._i] if self._i < len(self._ts) else None

    def consume(self) -> str:
        t = self._ts[self._i]
        self._i += 1
        return t

    def done(self) -> bool:
        return self._i >= len(self._ts)


def _expr(tok: _Tok) -> Polynomial:
    return _add_expr(tok)


def _add_expr(tok: _Tok) -> Polynomial:
    left = _mul_expr(tok)
    while tok.peek() in ('+', '-'):
        op = tok.consume()
        right = _mul_expr(tok)
        left = _add(left, _neg(right) if op == '-' else right)
    return left


def _mul_expr(tok: _Tok) -> Polynomial:
    left = _pow_expr(tok)
    while tok.peek() == '*':
        tok.consume()
        right = _pow_expr(tok)
        left = _mul(left, right)
    return left


def _pow_expr(tok: _Tok) -> Polynomial:
    base = _unary(tok)
    if tok.peek() == '^':
        tok.consume()
        t = tok.consume()
        if not re.fullmatch(r'\d+', t):
            raise ValueError(f"Expected integer exponent, got {t!r}")
        return _pow(base, int(t))
    return base


def _unary(tok: _Tok) -> Polynomial:
    if tok.peek() == '-':
        tok.consume()
        return _neg(_atom(tok))
    return _atom(tok)


def _atom(tok: _Tok) -> Polynomial:
    t = tok.peek()
    if t is None:
        raise ValueError("Unexpected end of expression")
    if t == '(':
        tok.consume()
        r = _expr(tok)
        if tok.peek() != ')':
            raise ValueError("Expected ')'")
        tok.consume()
        return r
    t = tok.consume()
    if re.fullmatch(r'\d+', t):
        return {(): Fraction(int(t))}
    if re.fullmatch(r'[A-Za-z_]\w*', t):
        return {((t, 1),): Fraction(1)}
    raise ValueError(f"Unexpected token: {t!r}")


# ── 公開 API ──────────────────────────────────────────────────────

def normalize_ring(expr: str) -> Polynomial:
    """式文字列を正規化した多項式として返す。"""
    tok = _Tok(expr)
    poly = _expr(tok)
    if not tok.done():
        raise ValueError(f"Trailing token: {tok.peek()!r}")
    return poly


def ring_equal(lhs: str, rhs: str) -> bool:
    """lhs と rhs が環の等式として等しいか判定する。"""
    try:
        diff = _add(normalize_ring(lhs), _neg(normalize_ring(rhs)))
        return len(diff) == 0
    except Exception:
        return False
