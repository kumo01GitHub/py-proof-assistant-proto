"""
py_to_lean.py — Python DSL → Lean 4 変換機

dsl._registry の内容（または Python DSL ファイルのインポート結果）を
Lean 4 構文のソースコードに変換する。

変換規則:
  kind=axiom              → axiom name : statement
  kind=def                → def name := body
  kind=theorem/lemma      → theorem name : statement := by\n  tactic...
  kind=theorem, tactics=[]→ theorem name : statement := by\n  sorry
"""

import importlib.util
from typing import Dict, List, Optional

from ..logger import get_logger


logger = get_logger(__name__)


def registry_to_lean(registry: Dict) -> str:
    """
    dsl._registry の辞書を Lean 4 ソースコードに変換する。
    """
    lines: List[str] = [
        "-- Auto-generated from Python DSL by registry_to_lean()",
        "-- Edit as needed.",
        "",
    ]

    for name, entry in registry.items():
        kind = entry["kind"]
        stmt = entry.get("statement", "")
        tactics = entry.get("tactics", [])

        if kind == "axiom":
            lines += [f"axiom {name} : {stmt}", ""]

        elif kind == "def":
            body = entry.get("body", "")
            lines += [f"def {name} := {body}", ""]

        elif kind in ("theorem", "lemma"):
            lines.append(f"{kind} {name} : {stmt} := by")
            if tactics:
                for tac in tactics:
                    lines.append(f"  {tac}")
            else:
                lines.append("  sorry  -- no tactics recorded (function-style proof)")
            lines.append("")

    return "\n".join(lines)


def python_to_lean(filepath: str) -> str:
    """
    Python DSL ファイルをインポートして _registry を読み取り、
    Lean 4 ソースコードを返す。
    """
    from .. import dsl as _dsl

    spec = importlib.util.spec_from_file_location("_lean_import_target", filepath)
    if spec is None or spec.loader is None:
        return f"-- Error: cannot load {filepath}\n"

    # インポート前にレジストリをリセット
    _dsl.reset_registry()

    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        return f"-- Error while importing {filepath}: {e}\n"

    registry = dict(_dsl.get_registry())
    return registry_to_lean(registry)


def python_file_to_lean(filepath: str, output: Optional[str] = None):
    """Python DSL ファイルを Lean 4 形式に変換して出力する。"""
    code = python_to_lean(filepath)
    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(code)
        logger.info("[to-lean] Written to %s", output)
    else:
        logger.info("%s", code)
