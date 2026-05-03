"""Linear arithmetic decision procedure (Fourier-Motzkin elimination).

omega タクティクで使う整数線形算術の決定手続き。

対応する制約形式（文字列）:
  "x + 2*y ≤ 5"   "n ≥ 0"   "a + b < c"   "x = 3"   "2*n + 1 > 0"

アプローチ:
  1. 仮説とゴールの否定を線形制約として解析
  2. Fourier-Motzkin 消去法で変数を消去
  3. 矛盾（定数のみで不成立な制約）が導出されれば証明可能
"""

from __future__ import annotations

import re
from fractions import Fraction
from typing import Dict, List, Optional, Tuple

# 線形式: 変数名 → 係数。空文字列 "" が定数項
LinearExpr = Dict[str, Fraction]


# ── 線形式演算 ─────────────────────────────────────────────────────

def _le_add(a: LinearExpr, b: LinearExpr) -> LinearExpr:
    r = dict(a)
    for v, c in b.items():
        r[v] = r.get(v, Fraction(0)) + c
    return {v: c for v, c in r.items() if c != 0}


def _le_neg(a: LinearExpr) -> LinearExpr:
    return {v: -c for v, c in a.items()}


def _le_scale(a: LinearExpr, k: Fraction) -> LinearExpr:
    return {v: c * k for v, c in a.items() if c * k != 0}


# ── 制約クラス ────────────────────────────────────────────────────

class _Constraint:
    """expr ≤ 0（strict=False）または expr < 0（strict=True）を表す。"""

    def __init__(self, expr: LinearExpr, strict: bool = False) -> None:
        self.expr = expr
        self.strict = strict

    def is_contradiction(self) -> bool:
        """変数なし定数制約が不成立か判定する。"""
        if any(v != "" for v in self.expr):
            return False
        c = self.expr.get("", Fraction(0))
        return c > 0 if not self.strict else c >= 0


# ── パーサ ───────────────────────────────────────────────────────

_OP_RE = re.compile(r'(?:<=|>=|<|>|=|≤|≥)')
_TERM_RE = re.compile(r'[+\-]?\s*\d*\s*\*?\s*[A-Za-z_]\w*|[+\-]?\s*\d+(?:\.\d+)?')


def _parse_linear(text: str) -> Optional[LinearExpr]:
    """線形式文字列を LinearExpr に変換する。失敗時は None。"""
    text = text.strip().replace(' ', '')
    result: LinearExpr = {}
    # トークン: [sign][coef*]var  または  [sign]const
    for tok in re.findall(r'[+\-]?\d*\*?[A-Za-z_]\w*|[+\-]?\d+', text):
        tok = tok.replace(' ', '')
        if not tok:
            continue
        m = re.fullmatch(r'([+\-]?\d*)\*?([A-Za-z_]\w*)', tok)
        if m:
            cs, var = m.group(1), m.group(2)
            coef = Fraction(1) if cs in ('', '+') else Fraction(-1) if cs == '-' else Fraction(int(cs))
            result[var] = result.get(var, Fraction(0)) + coef
        else:
            m2 = re.fullmatch(r'([+\-]?\d+)', tok)
            if m2:
                result[""] = result.get("", Fraction(0)) + Fraction(m2.group(1))
    if not result:
        return None
    return {v: c for v, c in result.items() if c != 0}


def parse_constraint(text: str) -> Optional[List[_Constraint]]:
    """
    不等式文字列を _Constraint のリストに変換する（等式は2制約）。
    失敗時は None。
    """
    text = text.strip().replace('≤', '<=').replace('≥', '>=')
    m = re.search(r'(<=|>=|<|>|=)', text)
    if not m:
        return None
    op = m.group(1)
    lhs_str = text[:m.start()].strip()
    rhs_str = text[m.end():].strip()

    lhs = _parse_linear(lhs_str)
    rhs = _parse_linear(rhs_str)
    if lhs is None or rhs is None:
        return None

    # lhs op rhs を (lhs - rhs) op 0 に正規化
    diff = _le_add(lhs, _le_neg(rhs))

    if op == '<=':
        return [_Constraint(diff, strict=False)]
    elif op == '>=':
        return [_Constraint(_le_neg(diff), strict=False)]
    elif op == '<':
        return [_Constraint(diff, strict=True)]
    elif op == '>':
        return [_Constraint(_le_neg(diff), strict=True)]
    elif op == '=':
        # A = B  ↔  A-B ≤ 0  ∧  -(A-B) ≤ 0
        return [
            _Constraint(diff, strict=False),
            _Constraint(_le_neg(diff), strict=False),
        ]
    return None


# ── Fourier-Motzkin 消去 ──────────────────────────────────────────

def _fm_step(cs: List[_Constraint], var: str) -> List[_Constraint]:
    """1変数を FM 消去して新しい制約リストを返す。"""
    upper: List[_Constraint] = []   # var の係数 > 0
    lower: List[_Constraint] = []   # var の係数 < 0
    indep: List[_Constraint] = []   # var を含まない

    for c in cs:
        coef = c.expr.get(var, Fraction(0))
        if coef == 0:
            indep.append(c)
        elif coef > 0:
            upper.append(c)
        else:
            lower.append(c)

    new_cs = list(indep)
    for u in upper:
        for l in lower:
            uc = u.expr[var]          # > 0
            lc = l.expr.get(var, Fraction(0))  # < 0
            abs_lc = -lc              # > 0
            # uc * |lc| * var が打ち消し合うように結合
            new_expr = _le_add(_le_scale(u.expr, abs_lc), _le_scale(l.expr, uc))
            new_expr.pop(var, None)
            new_cs.append(_Constraint(new_expr, u.strict or l.strict))

    return new_cs


# ── 公開 API ──────────────────────────────────────────────────────

def omega_proves(hyp_strs: List[str], goal_str: str) -> bool:
    """
    線形算術として、仮説群からゴールが証明できるか判定する。

    手順: ゴールを否定して仮説に追加 → FM消去 → 矛盾導出を確認。
    """
    cs: List[_Constraint] = []

    # 仮説を解析
    for h in hyp_strs:
        parsed = parse_constraint(h)
        if parsed is not None:
            cs.extend(parsed)

    # ゴールを解析
    goal_cs = parse_constraint(goal_str)
    if goal_cs is None:
        return False

    # ゴールの否定を追加
    # goal が expr ≤ 0 の場合、否定は expr > 0 つまり -expr < 0
    # goal が expr < 0 の場合、否定は expr ≥ 0 つまり -expr ≤ 0
    for gc in goal_cs:
        if gc.strict:
            # goal: expr < 0、否定: -expr ≤ 0
            cs.append(_Constraint(_le_neg(gc.expr), strict=False))
        else:
            # goal: expr ≤ 0、否定: -expr < 0
            cs.append(_Constraint(_le_neg(gc.expr), strict=True))

    # 全変数を収集して FM 消去
    current = cs
    all_vars = sorted({v for c in current for v in c.expr if v != ""})

    for var in all_vars:
        current = _fm_step(current, var)
        for c in current:
            if c.is_contradiction():
                return True

    # 残った（変数なし）制約で矛盾を確認
    return any(c.is_contradiction() for c in current)
