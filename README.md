# Python 証明支援系

**Python クラス**で命題論理の定理・公理を記述し、自然演繹カーネルで証明を検査するシステムです。

| 機能 | 概要 |
|---|---|
| **Python ライブラリ** | `Prop` / `Theorem` / `Lemma` / `Axiom` クラスで証明を記述する |
| **タクティク群** | `intro` / `exact` / `ring` / `omega` など、Lean 4 互換のタクティクを提供する |
| **証明カーネル** | 自然演繹に基づく `type_check()` で全ステップの健全性を保証する |
| **パーサ** | `.lean` ファイルと Python DSL を相互変換する |
| **CLI** | ファイル実行・ステップ実行・変換をコマンドラインから行う |

---

## セットアップ

```sh
python3 -m venv .venv
./.venv/bin/pip install -e ".[dev]"
```

`[dev]` extras に `pytest` が含まれます。ランタイム依存はありません（全て stdlib）。

---

## Python ライブラリ

`src/zfc_leanpy/dsl/` 以下に実装された証明記述ライブラリです。

### Prop — 命題オブジェクト

`Prop(name)` で命題変数を作り、Python 演算子で結合します。

| 演算子 | 論理記号 | 例 |
|---|---|---|
| `P & Q` | ∧（連言） | `P & Q` |
| `P \| Q` | ∨（選言） | `P \| Q` |
| `P >> Q` | →（含意） | `P >> Q` |
| `~P` | ¬（否定） | `~P` |
| `P.iff(Q)` | ↔（同値） | `P.iff(Q)` |

量化子には `ForAll` / `Exists` を使います。

```python
from zfc_leanpy import Prop, ForAll, Exists

P, Q = Prop("P"), Prop("Q")

phi = ForAll("x", Prop("P(x)") >> Prop("Q(x)"))  # ∀ x, P(x) → Q(x)
psi = Exists("x", Prop("P(x)"))                   # ∃ x, P(x)
```

`prop` 属性には `Prop` オブジェクトのほか、文字列も渡せます（文字列はパーサが解析します）。

### Theorem / Lemma / Axiom クラス

クラスを定義するだけで証明が自動登録されます。

```python
from zfc_leanpy import Prop, Theorem, Lemma, Axiom, ForAll
from zfc_leanpy.dsl.tactic_objects import intro, constructor, exact, left, ring, norm_num

P, Q = Prop("P"), Prop("Q")

# 定理（カーネル検査・証明書発行あり）
class AndComm(Theorem):
    prop    = (P & Q) >> (Q & P)
    tactics = [intro("h"), constructor(), exact("h.2"), exact("h.1")]

# 補題
class OrIntro(Lemma):
    prop    = P >> (P | Q)
    tactics = [intro("h"), left(), exact("h")]

# 公理（タクティク不要）
class ExcludedMiddle(Axiom):
    prop = P | ~P

# 登録名を明示する場合は name 属性を追加
class _Impl(Lemma):
    name    = "impl_self"
    prop    = P >> P
    tactics = [intro("h"), exact("h")]
```

クラス名（または `name` 属性）がレジストリのキーになります。

#### レジストリと証明書

```python
from zfc_leanpy.dsl import get_status, get_registry

get_status("AndComm")   # "proved" | "trusted" | "sorry"
get_registry()          # 全登録エントリの immutable view（MappingProxyType）
```

`status = "proved"` のときのみ HMAC-SHA256 署名付き `ProofCertificate` が発行されます。

| ステータス | 条件 |
|---|---|
| `proved` | 全ステップが `type_check()` を通過し、リプレイが成功した |
| `trusted` | 一部ステップが `type_check()` を通らず無検査で受け入れられた |
| `sorry` | `sorry_()` タクティクを含む |

### デコレータ API（後方互換）

文字列ベースのデコレータ形式も引き続きサポートしています。

```python
from zfc_leanpy import theorem, axiom

@theorem("and_comm", "P ∧ Q → Q ∧ P",
         tactics=["intro h", "constructor", "exact h.2", "exact h.1"])
def _(): pass

@axiom("em", "P ∨ ¬P")
def _(): pass
```

### ZFC 公理（オプション）

ZFC 公理はコアシステムには含まれません。必要な場合のみインポートします。

```python
from zfc_leanpy.axioms import ALL_AXIOMS, get_axiom
```

`Axiom` クラスで独自の公理を宣言することもできます。

```python
class EmptySet(Axiom):
    prop = Prop("∃ x, ∀ y, y ∉ x")
```

---

## タクティク群

`src/zfc_leanpy/tactics/` に実装されたタクティクエンジンです。

`tactics` リストにはタクティクオブジェクト（推奨）または文字列を渡せます。

```python
from zfc_leanpy.dsl.tactic_objects import intro, constructor, exact

# オブジェクト形式（推奨）
tactics = [intro("h"), constructor(), exact("h.1")]

# 文字列形式（後方互換）
tactics = ["intro h", "constructor", "exact h.1"]
```

### fully sound タクティク（カーネル検査済み）

| タクティク | 役割 | 証明項 |
|---|---|---|
| `intro(name)` | 前件を仮説として導入 | PLam |
| `intros(*names)` | 複数の前件を一括導入 | PLam（繰り返し） |
| `exact(expr)` | 仮説・式でゴールを閉じる | PVar(h) |
| `exact("h.1")` / `exact("h.2")` | ∧ の射影 | PAndE1 / PAndE2 |
| `assumption()` | 仮説から自動照合 | PVar(matching) |
| `rfl()` | 等式の反射律 | PRefl(t) |
| `trivial()` | True / rfl / assumption を自動試行 | PTrueI / PVar / PRefl |
| `constructor()` / `split()` | ∧ / ↔ のゴールを2つに分割 | ゴール構造検査 |
| `left()` / `right()` | ∨ の左右を選択 | ゴール構造検査 |
| `use(term)` | ∃ の証人を指定 | ゴール構造検査 |

### 決定手続きタクティク（fully sound）

成功すれば `status = "proved"`、失敗時のみ `trusted` にフォールバックします。

| タクティク | 決定手続き | 証明項 |
|---|---|---|
| `ring()` | 多項式正規化（変数を含む等式） | PRing(lhs, rhs) |
| `simp()` | 命題真理値表（2ⁿ 割り当て） | PSimp(goal_str) |
| `omega()` | Fourier-Motzkin 消去（線形算術） | POmega(goal_str) |
| `norm_num()` | 定数算術評価 | PNormNum(lhs, rhs) |

```python
class DiffSquares(Theorem):
    prop    = "(a+b)*(a-b) = a^2-b^2"
    tactics = [ring()]    # status = "proved"

class LinearFact(Theorem):
    prop    = "n + 1 > 0"
    tactics = [omega()]   # n >= 0 が仮説にあれば proved
```

### trusted タクティク（型を追いきれないため無検査）

`apply_()` / `cases()` / `rcases()` / `have()` / `rw()`

### admitted

`sorry_()` — 証明の穴。`status = "sorry"` となり証明書は発行されない。

---

## 証明カーネル

`src/zfc_leanpy/kernel/` および `src/zfc_leanpy/formula/` に実装された信頼カーネルです。

### 自然演繹

各証明ステップには対応する推論規則があり、ゴールを閉じる操作は必ず `type_check(ctx, term) → proposition` を通します。

```
推論規則                    タクティク         証明項
────────────────────────────────────────────────────
Γ, h:A ⊢ B                 intro h           PLam(h, A, body)
─────────────  →-I
Γ ⊢ A → B

h:A ∈ Γ                    exact h           PVar(h)
─────────────  Var          assumption        PVar(matching)
Γ ⊢ A

Γ ⊢ A    Γ ⊢ B              constructor       ゴール分割
─────────────  ∧-I          + exact ...       PAndI(pl, pr)
Γ ⊢ A ∧ B

Γ ⊢ A ∧ B                   exact h.1         PAndE1(PVar(h))
─────────────  ∧-E₁
Γ ⊢ A

t = t                        rfl               PRefl(t)
─────────────  Refl
Γ ⊢ t = t
```

### LCF スタイルとの対応

| LCF の概念 | このシステム |
|---|---|
| `thm` 型（カーネル外で構築不可能） | `close_with(term)` — 唯一の sound なクローズ経路 |
| 型検査器 | `formula.type_check()` |
| 証明項 | `PTerm`（PVar / PAndI / PRefl / PRing / POmega / PSimp / PNormNum ...） |
| タクティク | `tactics/engine.py`（`close_with` 経由でカーネルを呼ぶ） |

---

## パーサ

`src/zfc_leanpy/parser/` に実装された Lean 4 ↔ Python DSL 変換器です。

**Lean 4 ランタイムは不要**です。`.lean` ファイルを Python で直接解析します。

### Lean 4 → Python DSL

```python
from zfc_leanpy.parser import parse_lean_file, lean_to_python

entries = parse_lean_file("example/logic.lean")
# [{"kind": "theorem", "name": "and_comm", "statement": "...", "tactics": [...]}, ...]

py_src = lean_to_python(entries)
```

### Python DSL → Lean 4

```python
from zfc_leanpy.parser import registry_to_lean

lean_src = registry_to_lean()   # 登録済み定理を全て Lean 4 形式で出力
```

---

## CLI

`python -m zfc_leanpy` で起動します。

### ファイル実行

```sh
python -m zfc_leanpy example/logic.lean
```

```
[theorem] and_comm : P ∧ Q → Q ∧ P
  [ok] proof complete ✓
```

### ステップ実行

タクティクごとにゴール状態を表示します。

```sh
python -m zfc_leanpy --step example/logic.lean
python -m zfc_leanpy --step example/logic.lean and_comm   # 特定の定理のみ
```

### Lean 4 → Python 変換

```sh
python -m zfc_leanpy --convert example/logic.lean
```

### Python → Lean 4 変換

```sh
python -m zfc_leanpy --to-lean my_proof.py
```

---

## ディレクトリ構成

```
zfc_leanpy/
├── pyproject.toml
├── example/
│   ├── logic.lean              ← 命題論理サンプル
│   └── empty_set.lean          ← 集合論サンプル（ZFC 公理使用）
├── src/zfc_leanpy/
│   ├── kernel/                 ← 証明カーネル
│   │   ├── proof_state.py      ←   ProofState クラス
│   │   └── errors.py           ←   TacticError クラス
│   ├── formula/                ← 命題 AST + 証明項 + type_check
│   │   ├── ast.py              ←   FVar / FAnd / FImpl / FEq ...
│   │   ├── parser.py           ←   fparse / fstr / feq / fsubst
│   │   ├── proof_terms.py      ←   PTerm（PVar / PRing / POmega ...）
│   │   ├── typecheck.py        ←   type_check（信頼カーネル）
│   │   ├── ring.py             ←   多項式正規化（ring 決定手続き）
│   │   ├── prop_simp.py        ←   真理値表（simp 決定手続き）
│   │   └── linear_arith.py     ←   Fourier-Motzkin（omega 決定手続き）
│   ├── tactics/                ← タクティク群
│   │   ├── engine.py           ←   apply_tactic（メインディスパッチャ）
│   │   └── primitives.py       ←   do_intro / do_apply / trusted_close ...
│   ├── dsl/                    ← Python ライブラリ
│   │   ├── prop.py             ←   Prop / ForAll / Exists
│   │   ├── tactic_objects.py   ←   タクティクオブジェクト群
│   │   ├── class_api.py        ←   Theorem / Lemma / Axiom メタクラス
│   │   ├── decorators.py       ←   @theorem / @lemma / @axiom
│   │   ├── registry.py         ←   証明レジストリ管理
│   │   ├── runner.py           ←   run_tactics / replay_proof
│   │   ├── helpers.py          ←   ProofState 関数ヘルパ
│   │   └── certificate.py      ←   ProofCertificate（HMAC-SHA256）
│   ├── parser/                 ← パーサ
│   │   ├── lean_parser.py      ←   Lean 4 ファイルパーサ
│   │   ├── lean_to_py.py       ←   Lean → Python 変換
│   │   └── py_to_lean.py       ←   Python → Lean 変換
│   ├── cli/                    ← CLI
│   │   ├── main.py
│   │   └── runner.py
│   ├── axioms.py               ← ZFC 公理（オプション）
│   └── proof_engine.py         ← 命題論理デモ
└── tests/
    ├── test_kernel.py          ← ProofState / ゴール操作
    ├── test_formula.py         ← AST / type_check / 証明項
    ├── test_tactics.py         ← 各タクティクの挙動
    ├── test_dsl.py             ← デコレータ / ステータス / 証明書
    ├── test_class_api.py       ← Prop / Theorem / Lemma / Axiom
    ├── test_decision_procedures.py  ← ring / simp / omega / norm_num
    ├── test_lean_parser.py     ← Lean 4 パーサ
    ├── test_converters.py      ← Lean ↔ Python 変換
    ├── test_cli.py             ← CLI 実行
    ├── test_axioms.py          ← ZFC 公理登録
    ├── test_proof_engine.py    ← デモ定理
    └── test_examples_runtime.py  ← Lean サンプルファイル実行
```

---

## テスト

```sh
# 全テスト
./.venv/bin/python -m pytest -q

# モジュール単位
./.venv/bin/python -m pytest tests/test_class_api.py -q
./.venv/bin/python -m pytest tests/test_decision_procedures.py -q
./.venv/bin/python -m pytest tests/test_tactics.py -q
```
