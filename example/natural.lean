-- 自然数の存在（ペアノの公理風）
axiom nat_zero : ∃n, n = 0
axiom nat_succ : ∀n, ∃m, m = n + 1

theorem zero_unique : ∀n m, n = 0 ∧ m = 0 → n = m :=
begin
  intros n m h,
  -- 0の一意性
  admit
end
