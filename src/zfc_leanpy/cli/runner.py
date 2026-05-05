"""Runtime helpers for interpreting and stepping Lean-like files."""

from __future__ import annotations

import importlib.util
import os
from typing import Any, Dict, List

from .. import dsl
from ..kernel import ProofState, TacticError
from ..logger import get_logger
from ..parser import parse_lean_file
from ..tactics import apply_tactic


logger = get_logger(__name__)


def print_status_entry(
    name: str,
    statement: str,
    status: str,
    trusted_steps: List[Dict[str, Any]],
) -> None:
    logger.info("[theorem] %s : %s", name, statement)
    if status == "proved":
        logger.info("  [PROVED ✓] proof complete — kernel-verified")
    elif status == "trusted":
        unverified_count = len(trusted_steps)
        logger.warning(
            "  [TRUSTED ⚠] proof complete but %d UNVERIFIED step(s):",
            unverified_count,
        )
        for s in trusted_steps:
            idx = s.get("index", -1)
            tac = s.get("tactic", "?")
            goal = s.get("goal", "")
            reason = s.get("reason", "")
            suggestion = s.get("suggestion", "")
            idx_str = f"step {idx}" if idx >= 0 else "step ?"
            logger.warning(
                "    [%s] tactic '%s' — goal: %s\n"
                "      Reason    : %s\n"
                "      Suggestion: %s",
                idx_str, tac, goal, reason, suggestion,
            )
    elif status == "sorry":
        logger.warning("  [SORRY ✗] proof admitted (sorry)")
    else:
        logger.warning("  [INCOMPLETE ✗] %s", status)


def _load_py_file(filepath: str) -> None:
    """`.py` ファイルをモジュールとしてロードし、クラス定義・デコレータを実行させる。"""
    abs_path = os.path.abspath(filepath)
    spec = importlib.util.spec_from_file_location("_zfc_user_module", abs_path)
    if spec is None or spec.loader is None:
        logger.error("Cannot load module from %s", filepath)
        return
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


def interpret_file(filepath: str) -> Dict[str, Dict]:
    dsl.reset_registry()
    logger.info("=== %s ===", filepath)

    if filepath.endswith(".py"):
        _load_py_file(filepath)
        registry = dsl.get_registry()
        for name, entry in registry.items():
            kind = entry["kind"]
            if kind == "axiom":
                logger.info("[axiom] %s : %s", name, entry["statement"])
            elif kind in ("theorem", "lemma"):
                print_status_entry(
                    name,
                    entry["statement"],
                    entry["status"],
                    list(entry.get("trusted_steps", [])),
                )
            elif kind == "def":
                logger.info("[def] %s", name)
        logger.info("=== Done ===")
        return dict(registry)

    items = parse_lean_file(filepath)

    for item in items:
        kind = item["kind"]
        name = item["name"]

        if kind == "axiom":
            stmt = item["statement"]
            dsl.axiom(name, stmt)(lambda: None)
            logger.info("[axiom] %s : %s", name, stmt)
            continue

        if kind in ("theorem", "lemma"):
            stmt = item["statement"]
            tacs: List[str] = item.get("tactics", [])
            dec = dsl.theorem if kind == "theorem" else dsl.lemma
            dec(name, stmt, tactics=tacs)(lambda: None)
            entry = dsl.get_registry()[name]
            print_status_entry(
                name,
                stmt,
                entry["status"],
                list(entry.get("trusted_steps", [])),
            )
            continue

        if kind == "def":
            dsl.def_(name, item.get("body", ""))
            logger.info("[def] %s", name)

    logger.info("=== Done ===")
    return dict(dsl.get_registry())


def step_file(filepath: str, theorem_name: str | None = None) -> None:
    if filepath.endswith(".py"):
        dsl.reset_registry()
        _load_py_file(filepath)
        registry = dsl.get_registry()
        items = [
            {"name": name, "statement": entry["statement"], "tactics": list(entry.get("tactics", []))}
            for name, entry in registry.items()
            if entry["kind"] in ("theorem", "lemma")
        ]
    else:
        items = [x for x in parse_lean_file(filepath) if x["kind"] in ("theorem", "lemma")]

    if theorem_name:
        items = [x for x in items if x["name"] == theorem_name]

    for item in items:
        logger.info("\n--- %s : %s ---", item["name"], item["statement"])
        state = ProofState(item["statement"])
        state.display()
        for i, tac in enumerate(item.get("tactics", []), start=1):
            logger.info("\n[%d] %s", i, tac)
            before_trusted = len(state.trusted_steps)
            try:
                state = apply_tactic(state, tac)
            except TacticError as e:
                logger.error("  [error] %s", e)
                break
            # Report any trusted steps added by this tactic immediately.
            new_trusted = state.trusted_steps[before_trusted:]
            for ts in new_trusted:
                ts_goal = ts.get("goal", "")
                ts_reason = ts.get("reason", "")
                ts_suggestion = ts.get("suggestion", "")
                logger.warning(
                    "  [TRUSTED ⚠] step %d '%s' — goal: %s\n"
                    "    Reason    : %s\n"
                    "    Suggestion: %s",
                    i, ts.get("tactic", tac), ts_goal, ts_reason, ts_suggestion,
                )
            state.display()
