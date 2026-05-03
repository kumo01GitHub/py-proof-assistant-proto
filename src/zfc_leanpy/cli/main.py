"""Command-line entrypoint wiring."""

from __future__ import annotations

import argparse

from ..parser import convert_file, python_file_to_lean
from .runner import interpret_file, step_file


def main() -> None:
    parser = argparse.ArgumentParser(description="zfc_leanpy command line")
    parser.add_argument("filepath", nargs="?", help=".lean or .py file")
    parser.add_argument("theorem", nargs="?", help="theorem name for --step")
    parser.add_argument("--step", action="store_true", help="step tactic execution")
    parser.add_argument("--convert", action="store_true", help="convert Lean to Python DSL")
    parser.add_argument("--to-lean", action="store_true", help="convert Python DSL to Lean")
    parser.add_argument("--output", "-o", help="output file path")
    args = parser.parse_args()

    if args.convert:
        if not args.filepath:
            parser.error("--convert requires filepath")
        convert_file(args.filepath, args.output)
        return

    if args.to_lean:
        if not args.filepath:
            parser.error("--to-lean requires filepath")
        python_file_to_lean(args.filepath, args.output)
        return

    if not args.filepath:
        parser.error("filepath is required unless --convert/--to-lean")

    if args.step:
        step_file(args.filepath, args.theorem)
    else:
        interpret_file(args.filepath)
