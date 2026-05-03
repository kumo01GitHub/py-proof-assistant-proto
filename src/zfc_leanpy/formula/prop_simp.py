"""Propositional simplification decision procedure.

命題論理の真理値表によって、コンテキスト（仮説）の下でゴールが
恒真かどうかを判定する。

アプローチ:
  - 命題変数（原子命題）を列挙
  - 全ての真理値割り当てを生成
  - 全ての仮説が True になる割り当てでゴールも True なら証明可能
"""

from __future__ import annotations

from typing import Dict, Iterator, List, Set

from .ast import FAnd, FEq, FEx, FAll, FApp, FFalse, FIff, FImpl, FNot, FOr, FTrue, FVar, _F


# ── 原子命題の収集 ─────────────────────────────────────────────────

def _collect_atoms(f: _F, out: Set[_F]) -> None:
    """論理結合子以外の葉ノードを収集する。"""
    if isinstance(f, (FVar, FEq, FApp)):
        out.add(f)
    elif isinstance(f, FImpl):
        _collect_atoms(f.l, out)
        _collect_atoms(f.r, out)
    elif isinstance(f, FAnd):
        _collect_atoms(f.l, out)
        _collect_atoms(f.r, out)
    elif isinstance(f, FOr):
        _collect_atoms(f.l, out)
        _collect_atoms(f.r, out)
    elif isinstance(f, FNot):
        _collect_atoms(f.x, out)
    elif isinstance(f, FIff):
        _collect_atoms(f.l, out)
        _collect_atoms(f.r, out)
    elif isinstance(f, (FAll, FEx)):
        _collect_atoms(f.body, out)
    # FTrue, FFalse はリテラルなので収集不要


def _all_assignments(atoms: List[_F]) -> Iterator[Dict[int, bool]]:
    """原子命題インデックス → bool の全割り当てを列挙する。"""
    n = len(atoms)
    for bits in range(1 << n):
        yield {i: bool((bits >> i) & 1) for i in range(n)}


# ── 評価器 ────────────────────────────────────────────────────────

def _eval(f: _F, assign: Dict[int, bool], atom_idx: Dict[_F, int]) -> bool:
    if isinstance(f, FTrue):
        return True
    if isinstance(f, FFalse):
        return False
    if f in atom_idx:
        return assign[atom_idx[f]]
    if isinstance(f, FImpl):
        return (not _eval(f.l, assign, atom_idx)) or _eval(f.r, assign, atom_idx)
    if isinstance(f, FAnd):
        return _eval(f.l, assign, atom_idx) and _eval(f.r, assign, atom_idx)
    if isinstance(f, FOr):
        return _eval(f.l, assign, atom_idx) or _eval(f.r, assign, atom_idx)
    if isinstance(f, FNot):
        return not _eval(f.x, assign, atom_idx)
    if isinstance(f, FIff):
        return _eval(f.l, assign, atom_idx) == _eval(f.r, assign, atom_idx)
    if isinstance(f, (FAll, FEx)):
        # 量化子は命題変数として扱う（閉じていない場合）
        return assign.get(atom_idx.get(f, -1), True)
    return True  # 未知のノードは True として扱う


# ── 公開 API ──────────────────────────────────────────────────────

_MAX_ATOMS = 20  # 2^20 = 1M 行: 安全上限


def simp_proves(hypotheses: Dict[str, _F], goal: _F) -> bool:
    """
    仮説が全て成立するすべての割り当てでゴールが成立するか判定する。

    原子命題が MAX_ATOMS を超える場合は False を返す（安全側に倒す）。
    """
    # 原子命題を収集
    atoms_set: Set[_F] = set()
    for h in hypotheses.values():
        _collect_atoms(h, atoms_set)
    _collect_atoms(goal, atoms_set)

    atoms = list(atoms_set)
    if len(atoms) > _MAX_ATOMS:
        return False

    atom_idx = {a: i for i, a in enumerate(atoms)}

    for assign in _all_assignments(atoms):
        # 全仮説が True の割り当てのみチェック
        hyps_hold = all(_eval(h, assign, atom_idx) for h in hypotheses.values())
        if not hyps_hold:
            continue
        if not _eval(goal, assign, atom_idx):
            return False

    return True
