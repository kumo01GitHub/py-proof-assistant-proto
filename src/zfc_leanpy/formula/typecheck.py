"""Proof-term type checker (kernel trust anchor)."""

from __future__ import annotations

from fractions import Fraction
from typing import Dict

from .ast import FAnd, FEq, FImpl, FOr, FTrue, _F
from .linear_arith import omega_proves
from .parser import feq, fparse, fstr
from .proof_terms import (
    PAndE1, PAndE2, PAndI, PApp, PLam, PNormNum, POmega, POrIL, POrIR,
    PRing, PRefl, PSimp, PTerm, PTrueI, PVar, ProofTypeError,
)
from .prop_simp import simp_proves
from .ring import ring_equal


def type_check(ctx: Dict[str, _F], term: PTerm) -> _F:
    if isinstance(term, PVar):
        if term.name not in ctx:
            raise ProofTypeError(f"unbound proof variable: {term.name}")
        return ctx[term.name]

    if isinstance(term, PAndE1):
        t = type_check(ctx, term.inner)
        if not isinstance(t, FAnd):
            raise ProofTypeError("and elimination .1 expects conjunction")
        return t.l

    if isinstance(term, PAndE2):
        t = type_check(ctx, term.inner)
        if not isinstance(t, FAnd):
            raise ProofTypeError("and elimination .2 expects conjunction")
        return t.r

    if isinstance(term, PAndI):
        return FAnd(type_check(ctx, term.left), type_check(ctx, term.right))

    if isinstance(term, POrIL):
        return FOr(type_check(ctx, term.pf), term.right_type)

    if isinstance(term, POrIR):
        return FOr(term.left_type, type_check(ctx, term.pf))

    if isinstance(term, PLam):
        inner_ctx = dict(ctx)
        inner_ctx[term.var] = term.dom
        return FImpl(term.dom, type_check(inner_ctx, term.body))

    if isinstance(term, PApp):
        fn_t = type_check(ctx, term.fn)
        arg_t = type_check(ctx, term.arg)
        if not isinstance(fn_t, FImpl):
            raise ProofTypeError("application expects implication/function type")
        if not feq(fn_t.l, arg_t):
            raise ProofTypeError(f"argument type mismatch: expected {fstr(fn_t.l)}, got {fstr(arg_t)}")
        return fn_t.r

    if isinstance(term, PRefl):
        return FEq(term.term, term.term)

    if isinstance(term, PTrueI):
        return FTrue()

    # ── 決定手続き証明項 ──────────────────────────────────────────

    if isinstance(term, PRing):
        if not ring_equal(term.lhs, term.rhs):
            raise ProofTypeError(
                f"ring: cannot prove {term.lhs!r} = {term.rhs!r} by polynomial normalization"
            )
        return FEq(term.lhs, term.rhs)

    if isinstance(term, PSimp):
        goal = fparse(term.goal_str)
        if goal is None:
            raise ProofTypeError(f"simp: cannot parse goal {term.goal_str!r}")
        if not simp_proves(ctx, goal):
            raise ProofTypeError(f"simp: goal {term.goal_str!r} not provable by propositional simplification")
        return goal

    if isinstance(term, POmega):
        # コンテキスト中の仮説型を文字列として渡す（線形算術っぽいもの）
        hyp_strs = [fstr(h) for h in ctx.values()]
        if not omega_proves(hyp_strs, term.goal_str):
            raise ProofTypeError(
                f"omega: goal {term.goal_str!r} not provable by linear arithmetic"
            )
        goal = fparse(term.goal_str)
        if goal is None:
            raise ProofTypeError(f"omega: cannot parse goal {term.goal_str!r}")
        return goal

    if isinstance(term, PNormNum):
        # 定数式を Python の Fraction で評価する（加減乗算のみ）
        def _eval_const(expr: str) -> Fraction:
            # 安全な算術評価: 変数を含まない定数式のみ
            import re as _re
            if _re.search(r'[A-Za-z_]', expr):
                raise ProofTypeError(f"norm_num: non-numeric expression {expr!r}")
            # eval を使わず fractions で評価
            from .ring import normalize_ring
            poly = normalize_ring(expr)
            # 変数項がなければ定数項を返す
            non_const = {m: c for m, c in poly.items() if m != ()}
            if non_const:
                raise ProofTypeError(f"norm_num: symbolic expression {expr!r}")
            return poly.get((), Fraction(0))

        try:
            lval = _eval_const(term.lhs)
            rval = _eval_const(term.rhs)
        except (ValueError, ZeroDivisionError) as e:
            raise ProofTypeError(f"norm_num: evaluation error: {e}") from e
        if lval != rval:
            raise ProofTypeError(
                f"norm_num: {term.lhs!r} evaluates to {lval} ≠ {rval} ({term.rhs!r})"
            )
        return FEq(term.lhs, term.rhs)

    raise ProofTypeError(f"unknown proof term: {term}")

