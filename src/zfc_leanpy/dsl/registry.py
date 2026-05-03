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
