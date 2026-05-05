"""Registry storage and metadata helpers for DSL declarations."""

from copy import deepcopy
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional

from ..logger import get_logger

_REGISTRY: Dict[str, Dict] = {}
logger = get_logger(__name__)


def reset_registry() -> None:
    _REGISTRY.clear()


def register_entry(name: str, entry: Dict) -> None:
    _REGISTRY[name] = deepcopy(entry)


def get_entry(name: str) -> Optional[Dict]:
    entry = _REGISTRY.get(name)
    if entry is None:
        return None
    return deepcopy(entry)


def get_registry() -> Mapping[str, Dict]:
    snapshot = {k: deepcopy(v) for k, v in _REGISTRY.items()}
    return MappingProxyType(snapshot)


def list_axioms() -> List[str]:
    return [k for k, v in _REGISTRY.items() if v["kind"] == "axiom"]


def list_theorems() -> List[str]:
    return [k for k, v in _REGISTRY.items() if v["kind"] in ("theorem", "lemma")]


def get_status(name: str) -> Optional[str]:
    entry = _REGISTRY.get(name)
    return entry["status"] if entry else None


def get_proof_summary(name: str) -> Optional[Dict]:
    """Return a detailed summary of a proof entry's verification state.

    Returns a dict with the following fields:
      - ``name``: entry name
      - ``kind``: "theorem", "lemma", or "axiom"
      - ``status``: "proved" | "trusted" | "sorry" | "axiom" | "defined" | incomplete string
      - ``trusted_steps``: list of dicts, each with keys
          ``index`` (1-based tactic index), ``tactic``, ``reason``,
          ``suggestion``, and ``goal`` (goal string at time of trusted step)
      - ``first_trusted_step_index``: index of the first trusted step (1-based), or None
      - ``first_trusted_goal``: goal string at the first trusted step, or None
      - ``replay_ok``: whether the full proof replayed without trusted steps
      - ``error_message``: human-readable explanation when the proof is not fully verified
    """
    entry = _REGISTRY.get(name)
    if entry is None:
        return None

    entry = deepcopy(entry)
    status = entry["status"]
    trusted_steps: List[Dict[str, Any]] = entry.get("trusted_steps", [])
    replay_ok: bool = bool(entry.get("replay_ok", False))

    first_trusted_step_index: Optional[int] = None
    first_trusted_goal: Optional[str] = None
    if trusted_steps:
        first = trusted_steps[0]
        idx = first.get("index", -1)
        first_trusted_step_index = idx if idx >= 0 else None
        first_trusted_goal = first.get("goal") or None

    if status == "proved":
        error_message = None
    elif status == "sorry":
        error_message = (
            f"[SORRY] '{name}' contains admitted (sorry) steps — proof is incomplete."
        )
    elif status == "trusted":
        step_descs = []
        for s in trusted_steps:
            idx = s.get("index", -1)
            tac = s.get("tactic", "unknown")
            step_descs.append(f"step {idx}: {tac}" if idx >= 0 else tac)
        step_list = ", ".join(step_descs) if step_descs else "unknown"
        error_message = (
            f"[TRUSTED] '{name}' has unverified tactic steps: {step_list}. "
            "These steps bypassed the kernel type-checker."
        )
    elif status == "axiom":
        error_message = None
    elif status == "defined":
        error_message = None
    else:
        # incomplete
        error_message = (
            f"[INCOMPLETE] '{name}' proof is incomplete ({status})."
        )

    return {
        "name": name,
        "kind": entry.get("kind", "unknown"),
        "status": status,
        "trusted_steps": trusted_steps,
        "first_trusted_step_index": first_trusted_step_index,
        "first_trusted_goal": first_trusted_goal,
        "replay_ok": replay_ok,
        "error_message": error_message,
    }


def state_to_status(
    admitted: bool,
    closed: bool,
    goals_count: int,
    trusted_steps_count: int,
    replay_ok: bool,
) -> str:
    if admitted:
        return "sorry"
    if closed and trusted_steps_count == 0 and replay_ok:
        return "proved"
    if closed:
        return "trusted"
    return f"incomplete ({goals_count} goal(s) remaining)"


def revalidate_proof(name: str, new_tactics: List[str]) -> Optional[Dict]:
    """Attempt to upgrade a proof entry to ``proved`` by replaying new tactics.

    Reruns *new_tactics* against the proof's statement and, if they produce a
    fully kernel-verified closure (no admitted or trusted steps), updates the
    registry entry's status to ``"proved"``.

    This implements the *auto-revalidation* gate: a ``trusted`` or ``sorry``
    proof can be upgraded at any point — including from a separate module — by
    supplying a complete, kernel-verifiable tactic list.

    Args:
        name: Registry name of the proof entry to revalidate.
        new_tactics: Complete list of tactics that are expected to close the
            proof without any trusted fallbacks.

    Returns:
        Updated :func:`get_proof_summary` dict on success or when the entry
        already has status ``"proved"``.  Returns ``None`` when *name* is not
        found in the registry.  Returns the existing summary unchanged when the
        entry's status is ``"axiom"`` or ``"defined"`` (revalidation does not
        apply to those).

    Logs:
        ``INFO``  — when the proof is successfully upgraded to ``"proved"``.
        ``WARNING`` — when revalidation still results in trusted/incomplete steps.
    """
    entry = _REGISTRY.get(name)
    if entry is None:
        return None

    status = entry.get("status", "")

    # Nothing to do for non-trusted statuses.
    if status in ("proved", "axiom", "defined"):
        return get_proof_summary(name)

    # Import here to avoid circular imports at module level.
    from .runner import replay_proof, run_tactics

    statement: str = entry.get("statement", "")

    # Run the new tactics.
    state = run_tactics(statement, new_tactics)
    replay_ok = replay_proof(statement, new_tactics)

    new_status = state_to_status(
        state.admitted,
        state.closed,
        len(state.goals),
        len(state.trusted_steps),
        replay_ok,
    )

    if new_status == "proved":
        _REGISTRY[name] = deepcopy({
            **entry,
            "status": "proved",
            "trusted_steps": [],
            "tactics": list(new_tactics),
            "replay_ok": True,
        })
        logger.info(
            "[revalidate] '%s' upgraded trusted → proved",
            name,
        )
    else:
        # Revalidation attempt did not fully verify; update with new attempt's data.
        _REGISTRY[name] = deepcopy({
            **entry,
            "status": new_status,
            "trusted_steps": [dict(s) for s in state.trusted_steps],
            "tactics": list(new_tactics),
            "replay_ok": replay_ok,
        })
        logger.warning(
            "[revalidate] '%s' revalidation result: %s (%d unverified step(s))",
            name,
            new_status,
            len(state.trusted_steps),
        )

    return get_proof_summary(name)
