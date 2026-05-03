-- ZFC 空集合の公理と一意性定理 (Lean 4形式)

-- 公理: 空集合の存在
axiom empty_set : ∃ x, ∀ y, y ∉ x

-- 補題: 空集合は一意
theorem empty_set_unique : ∀ x y, (∀ z, z ∉ x) → (∀ z, z ∉ y) → x = y := by
  intro x y hx hy
  apply extensionality
  intro z
  constructor
  intro hz
  exact absurd hz (hx z)
  intro hz
  exact absurd hz (hy z)

-- 補題: 自分自身を含まない (正則性から)
theorem empty_not_in_empty : ∀ x, x ∉ ∅ := by
  intro x
  sorry
