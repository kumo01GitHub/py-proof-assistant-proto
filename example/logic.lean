-- 命題論理の基本定理 (Lean 4形式)

-- 恒等関数
theorem id_prop : P → P := by
  intro h
  exact h

-- 連言の交換
theorem and_comm : P ∧ Q → Q ∧ P := by
  intro h
  constructor
  · exact h.2
  · exact h.1

-- 選言の導入 (左)
theorem or_intro_l : P → P ∨ Q := by
  intro h
  left
  exact h

-- 連言の結合
theorem and_assoc : (P ∧ Q) ∧ R → P ∧ (Q ∧ R) := by
  intro h
  constructor
  · exact h.1.1
  · constructor
    · exact h.1.2
    · exact h.2

-- 対偶
theorem contrapos : (P → Q) → ¬Q → ¬P := by
  intro hpq hnq hp
  apply hnq
  apply hpq
  exact hp

-- 存在の導入
theorem exists_self : ∀ x, ∃ y, y = x := by
  intro x
  use x
  rfl
