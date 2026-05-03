from pathlib import Path

from zfc_leanpy import dsl
from zfc_leanpy.parser import lean_to_python, python_to_lean, registry_to_lean


def test_lean_to_python_generates_decorators(tmp_path: Path):
    src = tmp_path / "a.lean"
    src.write_text("theorem idp : P → P := by\n  intro h\n  exact h\n", encoding="utf-8")
    out = lean_to_python(str(src))
    assert "@theorem" in out
    assert "intro h" in out


def test_registry_to_lean_emits_axiom_and_theorem():
    text = registry_to_lean(
        {
            "ax": {"kind": "axiom", "statement": "P"},
            "th": {"kind": "theorem", "statement": "P", "tactics": ["sorry"]},
        }
    )
    assert "axiom ax : P" in text
    assert "theorem th : P := by" in text


def test_python_to_lean_imports_registry(tmp_path: Path):
    dsl.reset_registry()
    py = tmp_path / "proofs.py"
    py.write_text(
        "from zfc_leanpy import theorem\n"
        "@theorem('idp', 'P → P', tactics=['intro h','exact h'])\n"
        "def _():\n"
        "    pass\n",
        encoding="utf-8",
    )
    lean = python_to_lean(str(py))
    assert "theorem idp : P → P := by" in lean
