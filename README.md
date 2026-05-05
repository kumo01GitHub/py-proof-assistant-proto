# Python 証明支援系（py-proof-assistant-proto）

> **Pythonで形式証明のハードルを下げる**、軽量・実験的な証明支援システムのプロトタイプです。

## プロジェクトの目的と新規性

### なぜ Pythonで証明支援系を作るのか？

Lean 4 / Coq / Agda といった既存の定理証明支援系は、強力な型システムと高い健全性を持つ一方で、
**学習コストが高く**、専用言語・専用環境のセットアップが必要です。

本プロジェクトは、**日常的に Python を使う開発者・研究者が、追加ツールなしで形式証明を試せる**
環境を提供することを目的としています。

### 既存ツールとの違い

| ツール | 特徴 | 本プロジェクトとの違い |
|---|---|---|
| Lean 4 / Coq | カーネルレベルの完全型安全・強力な型システム | 学習コストが高い・専用言語が必要 |
| TinyLean | Lean の教育的簡略版 | 静的型付け・カーネル検証が前提 |
| Coq.py 等 | Pythonラッパー（外部カーネルに依存） | 外部ランタイムが必要 |
| **本プロジェクト** | **Pythonのみ・stdlib のみ・動的型付け** | **すぐに試せる・ランタイム検証・プロトタイピング向け** |

### 独自性のポイント

- **Pythonクラス定義だけで定理・補題・公理を記述** — Lean風DSLを`@theorem`デコレータやクラスAPIで提供
- **`trusted` / `proved` / `sorry` の三段階ステータス** — 証明の完全性を段階的に追跡・可視化
- **決定手続きタクティク**（`ring` / `omega` / `simp`）を内蔵し、`proved` 証明書を発行
- **動的型のリスクをランタイムガードで補完** — `util.guards` による事前型チェックで型安全性を確保
- **stdlib のみ** — 依存ライブラリゼロで `pip install` 後すぐ動作

---

**Python クラス**で命題論理の定理・公理を記述し、自然演繹カーネルで証明を検査するシステムです。

| 機能 | 概要 |
|---|---|
| **Python ライブラリ** | `Prop` / `Theorem` / `Lemma` / `Axiom` クラスで証明を記述する |
| **タクティク群** | `intro` / `exact` / `ring` / `omega` など、Lean 4 互換のタクティクを提供する |
| **証明カーネル** | 自然演繹に基づく `type_check()` で全ステップの健全性を保証する |
| **パーサ** | `.lean` ファイルと Python DSL を相互変換する |
| **CLI** | ファイル実行・ステップ実行・変換をコマンドラインから行う |
| **util モジュール** | エラーハンドリング・ログ整形を一元化し、型安全性を補完する |

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
from zfc_leanpy.dsl import get_status, get_registry, get_proof_summary, revalidate_proof

get_status("AndComm")   # "proved" | "trusted" | "sorry"
get_registry()          # 全登録エントリの immutable view（MappingProxyType）
```

`status = "proved"` のときのみ HMAC-SHA256 署名付き `ProofCertificate` が発行されます。

| ステータス | 条件 |
|---|---|
| `proved` | 全ステップが `type_check()` を通過し、リプレイが成功した |
| `trusted` | `have h := expr` など**明示的な** trusted ステップを含む |
| `sorry` | `sorry_()` タクティクを含む |
| `incomplete` | タクティクが `TacticError` で停止し、ゴールが残っている |

`incomplete` 状態のときは、タクティクのエラーメッセージを確認して修正してください。
証明をとりあえずスキップしたい場合は、`sorry` を明示的に使用することで `sorry` ステータスにできます。

`revalidate_proof(name, new_tactics)` を使うと、`trusted` / `sorry` 状態の証明に改良版のタクティクを再適用し、カーネル検証が通れば `proved` へ昇格できます。

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

成功すれば `status = "proved"`、検証不能なゴールには `TacticError` で停止します（trusted フォールバックしません）。

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

### タクティクと検証動作

`apply_()` / `cases()` / `rcases()` / `rw()` / `contradiction()` / `ring()` / `norm_num()` / `omega()` / `simp()`

これらのタクティクは、検証不能なケース（仮説が存在しない、型が合わない、等式でないなど）では **`TacticError` を投げて停止します**。
暗黙の trusted フォールバックは行いません。証明を一時的にスキップしたい場合は `sorry` を明示的に使用してください。

**`trusted` ステータスになる唯一の明示的タクティク**:
- `have h : T := expr` — 証明項を検証しない即時仮説導入

```python
from zfc_leanpy.dsl import get_proof_summary

summary = get_proof_summary("MyTheorem")
# {
#   'name': 'MyTheorem',
#   'kind': 'theorem',
#   'status': 'trusted',
#   'can_issue_certificate': False,
#   'trusted_steps': ['have :='],
#   'trusted_reasons': ['proof term is not kernel-verified ...'],
#   'trusted_suggestions': ['replace with a have : T sub-goal ...'],
#   'replay_ok': False,
#   'error_message': "[TRUSTED] 'MyTheorem' has unverified tactic steps: have :=. ..."
# }
```

`apply_()` は以下の3ケースではカーネル検証済みとなり `trusted` マークが付きません：

| ケース | 条件 | 証明項 |
|---|---|---|
| 完全一致 | 仮説の型がゴールと同じ | PVar(h) |
| 含意後退 | 仮説が `A → Goal` の形 | replace\_goal(A) |
| 否定除去 | ゴールが `¬P` で `False` が利用可能 | replace\_goal(negand) |

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

## util モジュール — エラーハンドリングとログ整形

`src/zfc_leanpy/util/` に一元化されたユーティリティモジュールです。

### 型安全ガード（`util.guards`）

Pythonの動的型付けの弱点を補うため、タクティク適用の入口で型検証を行います。

```python
from zfc_leanpy.util import require_proof_state, require_tactic_string

def apply_tactic(state, tactic_str):
    state = require_proof_state(state, context="apply_tactic")   # ProofState でなければ TacticError
    tactic_str = require_tactic_string(tactic_str, context="apply_tactic")
    ...
```

型チェックに失敗すると、実際の型を含む詳細なエラーメッセージが `TacticError` として送出されます。

### ログ整形（`util.log_fmt`）

証明ステータスの表示を一元管理し、ANSI カラーで視認性を高めます。

```python
from zfc_leanpy.util import format_proof_status_tag, format_trusted_step_detail

icon, tag = format_proof_status_tag("proved", [])
# icon = "✓"（緑）, tag = "[fully sound]"（緑）

icon, tag = format_proof_status_tag("trusted", ["apply_"])
# icon = "⚠"（黄）, tag = "[trusted ⚠: 1 unverified step(s)]"（黄）

detail = format_trusted_step_detail("apply_", "unknown hyp type")
# "· unverified step: 'apply_' — unknown hyp type"
```

| ステータス | アイコン | タグ |
|---|---|---|
| `proved` | ✓（緑） | `[fully sound]` |
| `trusted` | ⚠（黄） | `[trusted ⚠: N unverified step(s)]` |
| `sorry` | ✗（赤） | `[sorry — no certificate]` |

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
│   ├── logger.py               ← 共通ロギング設定（NullHandler）
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
│   │   ├── registry.py         ←   証明レジストリ管理・revalidate_proof
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
│   ├── util/                   ← ユーティリティ（エラー処理・ログ整形）
│   │   ├── guards.py           ←   require_proof_state / require_tactic_string
│   │   └── log_fmt.py          ←   ANSI カラー / format_proof_status_tag
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
    ├── test_examples_runtime.py  ← Lean サンプルファイル実行
    ├── test_proof_status.py    ← ステータス遷移・証明書検証
    ├── test_revalidation.py    ← revalidate_proof による昇格
    └── test_trusted_improvements.py  ← trusted タクティクの改善動作
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

---

## 今後の展望

本プロジェクトは実験的なプロトタイプとして始まりましたが、以下の方向での発展を検討しています。

### VS Code 拡張

- `@theorem` / `Theorem` クラスの定義をリアルタイムで認識し、証明ステータス（`proved` / `trusted` / `sorry`）をエディタ内でインライン表示することを予定している。
- タクティクの補完・ホバー説明を提供し、Lean 4 拡張に近い開発体験を Python ユーザーへ届けることを目指す。

### 分散証明処理

- 大規模な定理群を並列処理するため、証明タスクを分散ワーカーへ送信する機構の導入。
- `ProofCertificate`（HMAC-SHA256）を活用した分散環境での証明書検証。

### AI 連携（証明生成支援）

- LLM（大規模言語モデル）を活用し、未証明ゴール（`sorry_()` 箇所）に対するタクティク候補を自動提案する。
- `trusted` ステップを AI が補完・検証し、証明の完全性を段階的に高めるワークフローの構築。

### 証明ツリーの可視化

- 証明過程を有向グラフ（証明ツリー）として出力し、`trusted` 箇所をハイライト表示する。
- JSON / DOT 形式での証明書エクスポートにより、他ツール（Lean / Coq）へのインポートを可能にする。

### 静的型チェックの強化

- `mypy` / `pyright` との統合により、動的型の弱点をさらに補う。
- 型スタブの整備で、IDE での型推論補助を充実させる。

