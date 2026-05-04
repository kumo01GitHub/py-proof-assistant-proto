"""ProofState - mutable proof state with per-goal hypothesis scopes."""

from typing import Dict, List, Optional

from ..logger import get_logger
from .errors import TacticError

logger = get_logger(__name__)


class ProofState:
    """Mutable proof state with per-goal hypothesis scopes."""

    def __init__(self, goal: str, hypotheses: Optional[Dict[str, str]] = None):
        self.goals: List[str] = [goal]
        self._hyp_stack: List[Dict[str, str]] = [dict(hypotheses or {})]
        self.admitted: bool = False
        self.closed: bool = False
        self.trusted_steps: List[str] = []
        self.trusted_reasons: List[str] = []
        self.tactic_trace: List[str] = []

    @property
    def hypotheses(self) -> Dict[str, str]:
        return self._hyp_stack[0] if self._hyp_stack else {}

    @hypotheses.setter
    def hypotheses(self, value: Dict[str, str]) -> None:
        if self._hyp_stack:
            self._hyp_stack[0] = value
        else:
            self._hyp_stack = [value]

    def close_with(self, term: "PTerm") -> None:  # type: ignore[name-defined]
        from ..formula import ProofTypeError, feq, fparse, fstr, type_check

        goal_str = self.current_goal() or ""
        goal_type = fparse(goal_str)
        if goal_type is None:
            raise TacticError(f"close_with: goal parse failed: '{goal_str}'")

        ctx = {}
        for name, typ_str in self.hypotheses.items():
            tf = fparse(typ_str)
            if tf is not None:
                ctx[name] = tf

        try:
            proved = type_check(ctx, term)
        except ProofTypeError as e:
            raise TacticError(str(e))

        if not feq(proved, goal_type):
            raise TacticError(
                "close_with: proof type mismatch\n"
                f"  proved: {fstr(proved)}\n"
                f"  goal:   {goal_str}"
            )

        self.pop_goal()

    @property
    def is_fully_sound(self) -> bool:
        return not self.admitted and not self.trusted_steps

    def current_goal(self) -> Optional[str]:
        return self.goals[0] if self.goals else None

    def pop_goal(self) -> None:
        if self.goals:
            self.goals.pop(0)
            self._hyp_stack.pop(0)
        if not self.goals:
            self.closed = True

    def replace_goal(self, new_goal: str) -> None:
        if self.goals:
            self.goals[0] = new_goal

    def push_goal(self, goal: str) -> None:
        hyps = dict(self._hyp_stack[0]) if self._hyp_stack else {}
        self.goals.insert(0, goal)
        self._hyp_stack.insert(0, hyps)

    def split_have(self, sub_goal: str, hyp_name: str, hyp_type: str) -> None:
        if not self.goals:
            return

        original_goal = self.goals[0]
        original_hyps = dict(self._hyp_stack[0]) if self._hyp_stack else {}

        continuation_hyps = dict(original_hyps)
        continuation_hyps[hyp_name] = hyp_type

        self.goals.insert(1, original_goal)
        self._hyp_stack.insert(1, continuation_hyps)

        self.goals[0] = sub_goal
        self._hyp_stack[0] = original_hyps

    def display(self, indent: str = "  ") -> None:
        if self.closed:
            logger.info("%sGoals: (none - proof closed)", indent)
            return

        hyps = self.hypotheses
        if hyps:
            for name, typ in hyps.items():
                logger.info("%s%s : %s", indent, name, typ)
            logger.info("%s%s", indent, "-" * 40)

        if not self.goals:
            logger.info("%s(no goals)", indent)
            return

        for i, goal in enumerate(self.goals):
            prefix = "|-" if i == 0 else f"  [{i+1}]|-"
            logger.info("%s%s %s", indent, prefix, goal)

    def snapshot(self) -> "ProofState":
        s = ProofState.__new__(ProofState)
        s.goals = list(self.goals)
        s._hyp_stack = [dict(h) for h in self._hyp_stack]
        s.admitted = self.admitted
        s.closed = self.closed
        s.trusted_steps = list(self.trusted_steps)
        s.trusted_reasons = list(self.trusted_reasons)
        s.tactic_trace = list(self.tactic_trace)
        return s
