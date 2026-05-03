from zfc_leanpy.axioms import ALL_AXIOMS, get_axiom, list_zfc_axioms


def test_axioms_module_exposes_helpers():
    names = list_zfc_axioms()
    assert "empty_set" in names
    assert get_axiom("pairing") == ALL_AXIOMS["pairing"]
