"""
lean_to_py.py — Lean 4 → Python DSL 変換機

Lean 4 形式のファイルをパースし、zfc_leanpy DSL の
Python コードに変換する。

変換規則:
  axiom name : stmt         → @axiom("name", "stmt")
  theorem name : stmt := by → @theorem("name", "stmt", tactics=[...])
  def name := body          → def_("name", "body")
"""

from typing import List, Optional

from ..logger import get_logger
from .lean_parser import parse_lean_file


logger = get_logger(__name__)


def lean_to_python(filepath: str) -> str:
    """
    Lean 4 ファイルを Python DSL コードに変換して文字列で返す。
    """
    items = parse_lean_file(filepath)
    if not items:
        return f"# No items found in {filepath}\n"

    lines: List[str] = [
        '"""',
        f"Auto-generated from {filepath} by lean_to_python().",
        "Edit tactics or proof functions as needed.",
        '"""',
        "",
        "from zfc_leanpy import axiom, theorem, lemma, def_, ProofState, apply_tactic",
        "",
    ]

    for item in items:
        kind = item["kind"]
        name = item["name"]

        if kind == "axiom":
            stmt = item["statement"].replace('"', '\\"')
            lines += [f'@axiom("{name}", "{stmt}")', "def _(): pass", ""]

        elif kind == "def":
            body = item.get("body", "").replace('"', '\\"')
            lines += [f'def_("{name}", "{body}")', ""]

        elif kind in ("theorem", "lemma"):
            stmt = item["statement"].replace('"', '\\"')
            tactics = item.get("tactics", [])
            deco = kind  # "theorem" or "lemma"

            if not tactics:
                lines += [
                    f'@{deco}("{name}", "{stmt}", tactics=["sorry"])',
                    "def _(): pass", "",
                ]
            elif len(tactics) == 1:
                tac = tactics[0].replace('"', '\\"')
                lines += [
                    f'@{deco}("{name}", "{stmt}", tactics=["{tac}"])',
                    "def _(): pass", "",
                ]
            else:
                lines.append(f'@{deco}(')
                lines.append(f'    "{name}",')
                lines.append(f'    "{stmt}",')
                lines.append( '    tactics=[')
                for tac in tactics:
                    lines.append(f'        "{tac.replace(chr(34), chr(92)+chr(34))}",')
                lines += ['    ]', ')', "def _(): pass", ""]

    return "\n".join(lines)


def convert_file(filepath: str, output: Optional[str] = None):
    """Lean 4 ファイルを Python DSL コードに変換して出力する。"""
    code = lean_to_python(filepath)
    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(code)
        logger.info("[convert] Written to %s", output)
    else:
        logger.info("%s", code)
