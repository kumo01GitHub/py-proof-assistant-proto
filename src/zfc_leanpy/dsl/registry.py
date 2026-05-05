"""Registry storage and metadata helpers for DSL declarations."""

from copy import deepcopy
from types import MappingProxyType
from typing import Dict, List, Mapping, Optional

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
      - ``can_issue_certificate``: True only when status is "proved"
      - ``trusted_steps``: list of tactic names that were accepted without kernel verification
      - ``trusted_reasons``: list of reasons (parallel to trusted_steps) explaining each fallback
      - ``trusted_suggestions``: list of suggestions (parallel to trusted_steps) for resolving each fallback
      - ``replay_ok``: whether the full proof replayed without trusted steps
      - ``error_message``: human-readable explanation when the proof is not fully verified
    """
    entry = _REGISTRY.get(name)
    if entry is None:
        return None

    entry = deepcopy(entry)
    status = entry["status"]
    trusted_steps: List[str] = entry.get("trusted_steps", [])
    trusted_reasons: List[str] = entry.get("trusted_reasons", [])
    trusted_suggestions: List[str] = entry.get("trusted_suggestions", [])
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
        "trusted_reasons": trusted_reasons,
        "trusted_suggestions": trusted_suggestions,
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
    registry entry's status to ``"proved"`` and issues a
    :class:`~zfc_leanpy.dsl.certificate.ProofCertificate`.

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
    from .certificate import issue_certificate

    statement: str = entry.get("statement", "")

    # Run the new tactics (this populates trusted_suggestions via the runner).
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
        cert_obj = issue_certificate(statement, new_tactics, replay_ok)
        certificate = cert_obj.to_dict() if cert_obj is not None else None
        _REGISTRY[name] = deepcopy({
            **entry,
            "status": "proved",
            "trusted_steps": [],
            "trusted_reasons": [],
            "trusted_suggestions": [],
            "tactics": list(new_tactics),
            "certificate": certificate,
            "replay_ok": True,
        })
        logger.info(
            "[revalidate] '%s' upgraded trusted → proved — certificate issued",
            name,
        )
    else:
        # Revalidation attempt did not fully verify; update with new attempt's data.
        _REGISTRY[name] = deepcopy({
            **entry,
            "status": new_status,
            "trusted_steps": list(state.trusted_steps),
            "trusted_reasons": list(state.trusted_reasons),
            "trusted_suggestions": list(state.trusted_suggestions),
            "tactics": list(new_tactics),
            "certificate": None,
            "replay_ok": replay_ok,
        })
        logger.warning(
            "[revalidate] '%s' revalidation result: %s (%d unverified step(s))",
            name,
            new_status,
            len(state.trusted_steps),
        )

    return get_proof_summary(name)
