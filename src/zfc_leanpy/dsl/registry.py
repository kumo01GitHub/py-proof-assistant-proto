"""Registry storage and metadata helpers for DSL declarations."""

from copy import deepcopy
from types import MappingProxyType
from typing import Dict, List, Mapping, Optional

_REGISTRY: Dict[str, Dict] = {}


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
      - ``can_issue_certificate``: True only when status is "proved"
      - ``trusted_steps``: list of tactic names that were accepted without kernel verification
      - ``replay_ok``: whether the full proof replayed without trusted steps
      - ``error_message``: human-readable explanation when the proof is not fully verified
    """
    entry = _REGISTRY.get(name)
    if entry is None:
        return None

    entry = deepcopy(entry)
    status = entry["status"]
    trusted_steps: List[str] = entry.get("trusted_steps", [])
    replay_ok: bool = bool(entry.get("replay_ok", False))

    can_issue_certificate = status == "proved"

    if status == "proved":
        error_message = None
    elif status == "sorry":
        error_message = (
            f"[SORRY] '{name}' contains admitted (sorry) steps — proof is incomplete. "
            "No certificate will be issued."
        )
    elif status == "trusted":
        step_list = ", ".join(trusted_steps) if trusted_steps else "unknown"
        error_message = (
            f"[TRUSTED] '{name}' has unverified tactic steps: {step_list}. "
            "These steps bypassed the kernel type-checker. "
            "No certificate will be issued."
        )
    elif status == "axiom":
        error_message = None
    elif status == "defined":
        error_message = None
    else:
        # incomplete
        error_message = (
            f"[INCOMPLETE] '{name}' proof is incomplete ({status}). "
            "No certificate will be issued."
        )

    return {
        "name": name,
        "kind": entry.get("kind", "unknown"),
        "status": status,
        "can_issue_certificate": can_issue_certificate,
        "trusted_steps": trusted_steps,
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
