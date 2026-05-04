"""
lean_parser.py — Lean 4 構文パーサ

Lean 4 ファイル (.lean) をパースして
theorem / lemma / axiom / def の辞書リストを返す。

依存: re のみ（他の zfc_leanpy モジュール不要）
"""

import re
from typing import Dict, List

from ..logger import get_logger


logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 前処理
# ---------------------------------------------------------------------------

def remove_comments(content: str) -> str:
    """-- 行コメントと /- ... -/ ブロックコメントを除去する。"""
    content = re.sub(r"/-.*?-/", "", content, flags=re.DOTALL)
    lines = [re.sub(r"--.*$", "", line) for line in content.splitlines()]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# メインパーサ
# ---------------------------------------------------------------------------

def parse_lean_file(filepath: str) -> List[Dict]:
    """
    Lean 4 ファイルをパースし、各宣言の辞書リストを返す。

    各辞書のキー:
      kind      : "theorem" | "lemma" | "axiom" | "def"
      name      : 宣言名
      statement : 命題文字列（theorem/lemma/axiom）
      body      : 定義本体（def のみ）
      tactics   : タクティクのリスト（theorem/lemma、by ブロック）
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        logger.error("Error: file not found: %s", filepath)
        return []

    content = remove_comments(raw)
    lines = content.splitlines()
    items: List[Dict] = []

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # ---------- axiom ----------
        m = re.match(r"axiom\s+(\w+)\s*(?::[^:=]*)?\s*:\s*(.+)$", stripped)
        if m:
            items.append({
                "kind": "axiom",
                "name": m.group(1),
                "statement": m.group(2).strip(),
                "tactics": [],
            })
            i += 1
            continue

        # ---------- def (一行) ----------
        m = re.match(r"def\s+(\w+)\s*(?::[^=]*)?\s*:=\s*(.+)$", stripped)
        if m:
            items.append({
                "kind": "def",
                "name": m.group(1),
                "body": m.group(2).strip(),
                "tactics": [],
            })
            i += 1
            continue

        # ---------- theorem / lemma (:= by ...) ----------
        m = re.match(r"(theorem|lemma)\s+(\w+)(.*?)\s*:=\s*by\s*(.*)", stripped)
        if m:
            kind = m.group(1)
            name = m.group(2)
            sig  = m.group(3)
            same_line_tactic = m.group(4).strip()

            stmt_m = re.search(r":\s*(.+)$", sig)
            stmt = stmt_m.group(1).strip() if stmt_m else sig.strip()

            tactics: List[str] = []
            if same_line_tactic:
                tactics.append(same_line_tactic)

            i += 1
            if not same_line_tactic:
                # インデント基準を決定する
                base_indent = None
                j = i
                while j < len(lines):
                    ln = lines[j].rstrip()
                    s = ln.strip()
                    if s:
                        base_indent = len(ln) - len(ln.lstrip())
                        break
                    j += 1

                if base_indent is not None:
                    while i < len(lines):
                        ln = lines[i].rstrip()
                        s = ln.strip()
                        if not s:
                            i += 1
                            continue
                        indent = len(ln) - len(ln.lstrip())
                        if indent < base_indent:
                            break
                        tactics.append(s)
                        i += 1

            items.append({
                "kind": kind,
                "name": name,
                "statement": stmt,
                "tactics": tactics,
            })
            continue

        # ---------- theorem / lemma (:= begin ... end) ----------
        m = re.match(r"(theorem|lemma)\s+(\w+)(.*?)\s*:=\s*begin\s*$", stripped)
        if m:
            kind = m.group(1)
            name = m.group(2)
            sig = m.group(3)

            stmt_m = re.search(r":\s*(.+)$", sig)
            stmt = stmt_m.group(1).strip() if stmt_m else sig.strip()

            tactics = []
            i += 1
            while i < len(lines):
                ln = lines[i].rstrip()
                s = ln.strip()
                if not s:
                    i += 1
                    continue
                if s == "end":
                    i += 1
                    break
                tactics.append(s)
                i += 1

            items.append({
                "kind": kind,
                "name": name,
                "statement": stmt,
                "tactics": tactics,
            })
            continue

        # ---------- theorem / lemma (':=' then next line is by/begin) ----------
        m = re.match(r"(theorem|lemma)\s+(\w+)(.*?)\s*:=\s*$", stripped)
        if m:
            kind = m.group(1)
            name = m.group(2)
            sig = m.group(3)

            stmt_m = re.search(r":\s*(.+)$", sig)
            stmt = stmt_m.group(1).strip() if stmt_m else sig.strip()

            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            if i >= len(lines):
                items.append({
                    "kind": kind,
                    "name": name,
                    "statement": stmt,
                    "tactics": [],
                })
                continue

            marker = lines[i].strip()
            if marker == "begin":
                tactics = []
                i += 1
                while i < len(lines):
                    ln = lines[i].rstrip()
                    s = ln.strip()
                    if not s:
                        i += 1
                        continue
                    if s == "end":
                        i += 1
                        break
                    tactics.append(s)
                    i += 1

                items.append({
                    "kind": kind,
                    "name": name,
                    "statement": stmt,
                    "tactics": tactics,
                })
                continue

            if marker.startswith("by"):
                tactics = []
                same_line_tactic = marker[2:].strip()
                if same_line_tactic:
                    tactics.append(same_line_tactic)
                    i += 1
                else:
                    i += 1
                    base_indent = None
                    j = i
                    while j < len(lines):
                        ln = lines[j].rstrip()
                        s = ln.strip()
                        if s:
                            base_indent = len(ln) - len(ln.lstrip())
                            break
                        j += 1

                    if base_indent is not None:
                        while i < len(lines):
                            ln = lines[i].rstrip()
                            s = ln.strip()
                            if not s:
                                i += 1
                                continue
                            indent = len(ln) - len(ln.lstrip())
                            if indent < base_indent:
                                break
                            tactics.append(s)
                            i += 1

                items.append({
                    "kind": kind,
                    "name": name,
                    "statement": stmt,
                    "tactics": tactics,
                })
                continue

            # 未知マーカーの場合は宣言だけ拾って先へ進む
            items.append({
                "kind": kind,
                "name": name,
                "statement": stmt,
                "tactics": [],
            })
            continue

        i += 1

    return items
