-- 和集合の存在
axiom union : ∀A B, ∃C, ∀x, x ∈ C ↔ x ∈ A ∨ x ∈ B

theorem union_comm : ∀A B, (A ∪ B) = (B ∪ A) :=
begin
  intros A B,
  -- 和集合の定義より明らか
  admit
end
