from pathlib import Path

from zfc_leanpy.parser import parse_lean_file, remove_comments


def test_remove_comments_handles_line_and_block_comments():
    src = """-- line\n/- block -/\ntheorem t : P := by\n  exact h\n"""
    cleaned = remove_comments(src)
    assert "line" not in cleaned
    assert "block" not in cleaned


def test_parse_lean_file_extracts_items(tmp_path: Path):
    p = tmp_path / "sample.lean"
    p.write_text(
        """
axiom a1 : P

theorem idp : P → P := by
  intro h
  exact h

def val := 42
""".strip(),
        encoding="utf-8",
    )

    items = parse_lean_file(str(p))
    kinds = [x["kind"] for x in items]
    assert kinds == ["axiom", "theorem", "def"]
    assert items[1]["tactics"] == ["intro h", "exact h"]


def test_parse_theorem_begin_end_block(tmp_path: Path):
        p = tmp_path / "begin_style.lean"
        p.write_text(
                """
theorem t : P → P :=
begin
    intro h,
    exact h,
end
""".strip(),
                encoding="utf-8",
        )

        items = parse_lean_file(str(p))
        assert len(items) == 1
        assert items[0]["kind"] == "theorem"
        assert items[0]["name"] == "t"
        assert items[0]["tactics"] == ["intro h,", "exact h,"]
