"""Public formula API."""

from .ast import FAll, FAnd, FApp, FEq, FEx, FFalse, FIff, FImpl, FNot, FOr, FTrue, FVar, _F
from .linear_arith import omega_proves
from .parser import feq, fparse, fstr, fsubst
from .proof_terms import (
    PAndE1, PAndE2, PAndI, PApp, PLam, PNormNum, POmega, POrIL, POrIR,
    PRing, PRefl, PSimp, PTerm, PTrueI, PVar, ProofTypeError,
)
from .prop_simp import simp_proves
from .ring import normalize_ring, ring_equal
from .typecheck import type_check

__all__ = [
    "_F",
    "FVar",
    "FImpl",
    "FAnd",
    "FOr",
    "FNot",
    "FIff",
    "FAll",
    "FEx",
    "FEq",
    "FApp",
    "FTrue",
    "FFalse",
    "fparse",
    "fstr",
    "feq",
    "fsubst",
    "ProofTypeError",
    "PVar",
    "PAndE1",
    "PAndE2",
    "PAndI",
    "POrIL",
    "POrIR",
    "PLam",
    "PApp",
    "PRefl",
    "PTrueI",
    "PRing",
    "PSimp",
    "POmega",
    "PNormNum",
    "PTerm",
    "type_check",
    "ring_equal",
    "normalize_ring",
    "simp_proves",
    "omega_proves",
]
