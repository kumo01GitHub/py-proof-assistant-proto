from zfc_leanpy.kernel import ProofState
from zfc_leanpy.formula import PVar


def test_initial_state_has_single_goal():
    s = ProofState("P")
    assert s.current_goal() == "P"
    assert s.hypotheses == {}


def test_push_and_pop_goal_syncs_hyp_stack():
    s = ProofState("P", {"h": "P"})
    s.push_goal("Q")
    assert s.current_goal() == "Q"
    assert s.hypotheses == {"h": "P"}
    s.pop_goal()
    assert s.current_goal() == "P"


def test_split_have_adds_hyp_only_on_continuation():
    s = ProofState("G", {"a": "A"})
    s.split_have("T", "h", "T")
    assert s.current_goal() == "T"
    assert "h" not in s.hypotheses
    s.pop_goal()
    assert s.current_goal() == "G"
    assert s.hypotheses["h"] == "T"


def test_close_with_marks_fully_sound_proof():
    s = ProofState("P", {"h": "P"})
    s.close_with(PVar("h"))
    assert s.closed
    assert s.is_fully_sound


def test_snapshot_is_deep_copy():
    s = ProofState("P", {"h": "P"})
    snap = s.snapshot()
    s.hypotheses["k"] = "Q"
    assert "k" not in snap.hypotheses
