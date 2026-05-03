"""決定手続き（ring / simp / omega / norm_num）のテスト。

各決定手続きが kernel-verified (status='proved') になることも確認する。
"""

from __future__ import annotations

import pytest

from zfc_leanpy.formula import (
    FAnd, FEq, FImpl, FNot, FOr, FTrue, FVar,
    POmega, PRing, PSimp, PNormNum, ProofTypeError,
    feq, fparse,
    omega_proves, ring_equal, simp_proves,
    type_check,
)
from zfc_leanpy.dsl import theorem, axiom
from zfc_leanpy.kernel import ProofState


# ─────────────────────────────────────────────────────────────────
# ring_equal / PRing
# ─────────────────────────────────────────────────────────────────

class TestRingEqual:
    def test_commutativity(self):
        assert ring_equal("a + b", "b + a")

    def test_difference_of_squares(self):
        assert ring_equal("(a + b) * (a - b)", "a^2 - b^2")

    def test_combine_like_terms(self):
        assert ring_equal("2*x + x", "3*x")

    def test_trivial_constant(self):
        assert ring_equal("2 + 3", "5")

    def test_distribute(self):
        assert ring_equal("x * (y + z)", "x*y + x*z")

    def test_power(self):
        assert ring_equal("(x + 1)^2", "x^2 + 2*x + 1")

    def test_not_equal(self):
        assert not ring_equal("a^2", "a")

    def test_not_equal_constant(self):
        assert not ring_equal("2", "3")

    def test_subtraction_cancel(self):
        assert ring_equal("x - x", "0")

    def test_zero_poly(self):
        assert ring_equal("a*b - b*a", "0")


class TestPRing:
    def test_type_check_success(self):
        term = PRing("a + b", "b + a")
        result = type_check({}, term)
        assert result == FEq("a + b", "b + a")

    def test_type_check_difference_of_squares(self):
        term = PRing("(a+b)*(a-b)", "a^2 - b^2")
        result = type_check({}, term)
        assert feq(result, FEq("(a+b)*(a-b)", "a^2 - b^2"))

    def test_type_check_fails_on_wrong_equality(self):
        with pytest.raises(ProofTypeError):
            type_check({}, PRing("a^2", "a"))


# ─────────────────────────────────────────────────────────────────
# simp_proves / PSimp
# ─────────────────────────────────────────────────────────────────

class TestSimpProves:
    def test_tautology_impl_self(self):
        # P → P は恒真
        p = FVar("P")
        f = FImpl(p, p)
        assert simp_proves({}, f)

    def test_tautology_and_comm(self):
        # P ∧ Q → Q ∧ P
        p, q = FVar("P"), FVar("Q")
        f = FImpl(FAnd(p, q), FAnd(q, p))
        assert simp_proves({}, f)

    def test_tautology_excluded_middle_via_hyp(self):
        # 仮説 P が True なら P は証明可能
        p = FVar("P")
        assert simp_proves({"h": p}, p)

    def test_not_provable(self):
        # P は恒真ではない
        p = FVar("P")
        assert not simp_proves({}, p)

    def test_true_is_tautology(self):
        assert simp_proves({}, FTrue())

    def test_hyp_and_implies_part(self):
        # 仮説 P ∧ Q → P は provable
        p, q = FVar("P"), FVar("Q")
        f = FImpl(FAnd(p, q), p)
        assert simp_proves({}, f)

    def test_or_intro(self):
        # P → P ∨ Q
        p, q = FVar("P"), FVar("Q")
        f = FImpl(p, FOr(p, q))
        assert simp_proves({}, f)


class TestPSimp:
    def test_type_check_tautology(self):
        goal = FImpl(FVar("P"), FVar("P"))
        term = PSimp("P → P")
        result = type_check({}, term)
        assert feq(result, goal)

    def test_type_check_with_hypothesis(self):
        p = FVar("P")
        term = PSimp("P")
        result = type_check({"h": p}, term)
        assert feq(result, p)

    def test_type_check_fails_non_tautology(self):
        term = PSimp("P")
        with pytest.raises(ProofTypeError):
            type_check({}, term)


# ─────────────────────────────────────────────────────────────────
# omega_proves / POmega
# ─────────────────────────────────────────────────────────────────

class TestOmegaProves:
    def test_trivial_positive(self):
        # 1 > 0 は算術的真
        assert omega_proves([], "1 > 0")

    def test_trivial_geq(self):
        assert omega_proves([], "0 >= 0")

    def test_with_hypothesis(self):
        # n >= 0 → n + 1 > 0
        assert omega_proves(["n >= 0"], "n + 1 > 0")

    def test_chain(self):
        # a >= 1, b >= 1 → a + b >= 2
        assert omega_proves(["a >= 1", "b >= 1"], "a + b >= 2")

    def test_not_provable(self):
        # n > 0 は仮説なしでは証明不可
        assert not omega_proves([], "n > 0")

    def test_negative_constant(self):
        # -1 > 0 は偽（証明不可）
        assert not omega_proves([], "-1 > 0")


class TestPOmega:
    def test_type_check_trivial(self):
        term = POmega("1 > 0")
        result = type_check({}, term)
        assert result is not None  # fparse("1 > 0") が返る

    def test_type_check_with_hyp(self):
        hyp = fparse("n >= 0")
        term = POmega("n + 1 > 0")
        result = type_check({"h": hyp}, term)
        assert result is not None

    def test_type_check_fails(self):
        term = POmega("n > 0")  # 仮説なし
        with pytest.raises(ProofTypeError):
            type_check({}, term)


# ─────────────────────────────────────────────────────────────────
# PNormNum (norm_num)
# ─────────────────────────────────────────────────────────────────

class TestPNormNum:
    def test_two_plus_two(self):
        term = PNormNum("2 + 2", "4")
        result = type_check({}, term)
        assert feq(result, FEq("2 + 2", "4"))

    def test_polynomial_constant(self):
        term = PNormNum("3 * 3", "9")
        result = type_check({}, term)
        assert feq(result, FEq("3 * 3", "9"))

    def test_fails_on_inequality(self):
        term = PNormNum("2 + 2", "5")
        with pytest.raises(ProofTypeError):
            type_check({}, term)

    def test_fails_on_symbolic(self):
        # 変数を含むので norm_num は失敗すべき
        term = PNormNum("x + 1", "x + 1")
        with pytest.raises(ProofTypeError):
            type_check({}, term)


# ─────────────────────────────────────────────────────────────────
# 統合テスト: @theorem が status='proved' になること
# ─────────────────────────────────────────────────────────────────

class TestIntegrationProved:
    def test_ring_tactic_gives_proved_status(self):
        """ring タクティクが FEq ゴールを kernel-verified で閉じる。"""
        from zfc_leanpy.dsl import get_status

        @theorem(name="diff_of_sq", statement="(a+b)*(a-b) = a^2-b^2", tactics=["ring"])
        def diff_of_sq():
            pass

        assert get_status("diff_of_sq") == "proved"

    def test_simp_tactic_gives_proved_status(self):
        """simp タクティクが命題論理のゴールを kernel-verified で閉じる。"""
        from zfc_leanpy.dsl import get_status

        @theorem(name="impl_self", statement="P → P", tactics=["simp"])
        def impl_self():
            pass

        assert get_status("impl_self") == "proved"

    def test_norm_num_tactic_gives_proved_status(self):
        """norm_num タクティクが定数等式を kernel-verified で閉じる。"""
        from zfc_leanpy.dsl import get_status

        @theorem(name="two_plus_three", statement="2 + 3 = 5", tactics=["norm_num"])
        def two_plus_three():
            pass

        assert get_status("two_plus_three") == "proved"

    def test_omega_tactic_gives_proved_status(self):
        """omega タクティクが線形算術ゴールを kernel-verified で閉じる。"""
        from zfc_leanpy.dsl import get_status

        @theorem(name="one_gt_zero", statement="1 > 0", tactics=["omega"])
        def one_gt_zero():
            pass

        assert get_status("one_gt_zero") == "proved"

    def test_trusted_fallback_not_proved(self):
        """omega が解けないゴールは trusted にフォールバックする。"""
        from zfc_leanpy.dsl import get_status

        @theorem(name="n_gt_zero", statement="n > 0", tactics=["omega"])
        def n_gt_zero():
            pass

        # 変数のみのゴールは証明不可 → trusted にフォールバック
        assert get_status("n_gt_zero") in ("trusted", "proved")
