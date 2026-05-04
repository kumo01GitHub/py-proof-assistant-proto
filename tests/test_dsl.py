from zfc_leanpy.dsl import (
    ProofState,
    axiom,
    def_,
    exact,
    get_registry,
    get_status,
    intro,
    lemma,
    list_axioms,
    list_theorems,
    theorem,
)
from zfc_leanpy.dsl.certificate import ProofCertificate


def test_axiom_registration():
    @axiom("ax1", "P")
    def _():
        pass

    assert "ax1" in list_axioms()
    assert get_status("ax1") == "axiom"


def test_theorem_registration_with_tactics():
    @theorem("idp", "P → P", tactics=["intro h", "exact h"])
    def _():
        pass

    reg = get_registry()["idp"]
    assert reg["kind"] == "theorem"
    assert reg["status"] == "proved"
    assert reg["certificate"] is not None
    assert reg["replay_ok"] is True
    cert = reg["certificate"]
    cert_obj = ProofCertificate(
        statement=cert["statement"],
        tactics=list(cert["tactics"]),
        replay_ok=bool(cert["replay_ok"]),
        signature=cert["signature"],
    )
    assert cert_obj.verify() is True


def test_registry_snapshot_is_not_directly_mutable():
    @theorem("immut", "P → P", tactics=["intro h", "exact h"])
    def _():
        pass

    reg = get_registry()
    entry = reg["immut"]
    entry["status"] = "hacked"
    reg2 = get_registry()
    assert reg2["immut"]["status"] == "proved"


def test_lemma_registration_with_function_style():
    @lemma("idq", "Q → Q")
    def proof(state: ProofState):
        state = intro(state, "h")
        state = exact(state, "h")
        return state

    assert get_status("idq") == "proved"


def test_noarg_function_style_is_treated_as_sorry():
    @theorem("noarg", "P")
    def proof_without_state():
        return None

    reg = get_registry()["noarg"]
    assert reg["status"] == "sorry"
    assert reg["certificate"] is None


def test_trusted_status_is_separate_from_proved():
    # `have h2 : Q := h` is an inline proof term — always a trusted step.
    @theorem("trusted_apply", "P → Q", tactics=["intro h", "have h2 : Q := h", "exact h2"])
    def _():
        pass

    reg = get_registry()["trusted_apply"]
    assert reg["status"] == "trusted"
    assert reg["certificate"] is None


def test_def_registration():
    def_("two", "1 + 1")
    assert get_registry()["two"]["status"] == "defined"


def test_list_theorems_includes_theorem_and_lemma():
    @theorem("th", "P", tactics=["sorry"])
    def _():
        pass

    @lemma("lm", "Q", tactics=["sorry"])
    def _2():
        pass

    names = set(list_theorems())
    assert {"th", "lm"}.issubset(names)
