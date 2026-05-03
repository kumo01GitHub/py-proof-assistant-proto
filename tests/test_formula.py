import pytest

from zfc_leanpy.formula import (
    FAll,
    FAnd,
    FEq,
    FImpl,
    FTrue,
    PAndE1,
    PAndI,
    PApp,
    PLam,
    PRefl,
    PTrueI,
    PVar,
    ProofTypeError,
    feq,
    fparse,
    fstr,
    type_check,
)


def test_parse_and_string_roundtrip_for_implication():
    f = fparse("P → Q")
    assert isinstance(f, FImpl)
    assert "→" in fstr(f)


def test_parse_nested_and():
    f = fparse("(P ∧ Q) ∧ R")
    assert isinstance(f, FAnd)
    assert isinstance(f.l, FAnd)


def test_parse_multi_binder_forall():
    f = fparse("∀x y, P")
    assert isinstance(f, FAll)
    assert f.var == "x"
    assert isinstance(f.body, FAll)
    assert f.body.var == "y"


def test_type_check_var_and_and_elim():
    ctx = {"h": fparse("P ∧ Q")}
    assert fstr(type_check(ctx, PAndE1(PVar("h")))) == "P"


def test_type_check_and_intro():
    ctx = {"hp": fparse("P"), "hq": fparse("Q")}
    got = type_check(ctx, PAndI(PVar("hp"), PVar("hq")))
    assert feq(got, fparse("P ∧ Q"))


def test_type_check_lambda_and_app():
    p = fparse("P")
    q = fparse("Q")
    term = PApp(PLam("x", p, PVar("x")), PVar("a"))
    got = type_check({"a": p}, term)
    assert feq(got, p)


def test_type_check_refl_and_true_intro():
    assert isinstance(type_check({}, PRefl("x")), FEq)
    assert isinstance(type_check({}, PTrueI()), FTrue)


def test_type_check_raises_on_unbound_var():
    with pytest.raises(ProofTypeError):
        type_check({}, PVar("missing"))
