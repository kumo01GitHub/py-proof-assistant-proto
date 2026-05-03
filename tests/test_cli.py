from pathlib import Path

from zfc_leanpy.cli import interpret_file


def test_interpret_file_registers_theorems(tmp_path: Path):
    lean = tmp_path / "logic.lean"
    lean.write_text(
        """
theorem idp : P → P := by
  intro h
  exact h
""".strip(),
        encoding="utf-8",
    )

    reg = interpret_file(str(lean))
    assert "idp" in reg
    assert reg["idp"]["status"] == "proved"
