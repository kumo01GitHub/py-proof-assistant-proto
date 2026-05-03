"""
leanpy — Lean 4 構文互換・命題論理証明チェッカー

モジュール構成:
  kernel       ProofState, TacticError, close_with (カーネルゲート)
  formula      命題 AST + パーサ + 証明項 (PTerm) + type_check
  tactics      タクティク実行エンジン
  dsl          Python DSL ライブラリ (@theorem / @axiom / ...)
  parser       Lean 4 ファイルパーサ + Lean↔Python 変換機
  cli          CLI エントリポイント群

ZFC 公理が必要な場合は axioms.py を明示的に import してください:
  from zfc_leanpy.axioms import ALL_AXIOMS
"""

# -- カーネル --
from .kernel import ProofState, TacticError

# -- 論理式 + 証明項 --
from .formula import (
    fparse, feq, fsubst, fstr,
    FVar, FImpl, FAnd, FOr, FNot, FIff, FAll, FEx, FEq, FApp,
    PTerm, PVar, PAndE1, PAndE2, PAndI, POrIL, POrIR,
    PLam, PApp, PRefl, PTrueI,
    type_check, ProofTypeError,
)

# -- タクティク --
from .tactics import apply_tactic

# -- Python DSL --
from .dsl import (
    axiom, theorem, lemma, def_,
    get_registry, list_axioms, list_theorems, get_status,
    intro, intros, exact, apply_, have, rw, simp,
    constructor, use, left, right, sorry_,
    assumption, trivial, contradiction, ring, omega, norm_num,
    # クラスベース API
    Prop, ForAll, Exists,
    Theorem, Lemma, Axiom,
    tactic_objects,
)

# -- Lean パーサ + 変換機 --
from .parser import (
    parse_lean_file,
    lean_to_python, convert_file,
    registry_to_lean, python_to_lean, python_file_to_lean,
)

# -- CLI --
from .cli import interpret_file, step_file


