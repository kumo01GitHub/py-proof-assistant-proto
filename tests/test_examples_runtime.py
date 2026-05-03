from zfc_leanpy.cli import interpret_file


def test_natural_example_contains_theorem():
    reg = interpret_file("example/natural.lean")
    assert "zero_unique" in reg


def test_union_example_contains_theorem():
    reg = interpret_file("example/union.lean")
    assert "union_comm" in reg
