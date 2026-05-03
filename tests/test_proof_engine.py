import importlib

from zfc_leanpy import dsl


def test_proof_engine_registers_demo_theorems():
    dsl.reset_registry()
    mod = importlib.import_module("zfc_leanpy.proof_engine")
    importlib.reload(mod)
    reg = dsl.get_registry()
    assert "and_comm" in reg
    assert reg["and_comm"]["status"] == "proved"
