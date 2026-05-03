import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from zfc_leanpy.leanpy import axiom, theorem, def_

axiom("empty_set", "∃x, ∀y, y ∉ x")
theorem("empty_set_unique", "∀x y, (∀z, z ∉ x ∧ z ∉ y) → x = y :=")(lambda: None)
