# DESIGN.md — py-proof-assistant-proto システム設計書

> 本ドキュメントは、システム全体を再構築できるレベルの詳細設計を記述します。
> プロトタイプから本格実装へ昇格させる際に、差し替え・改修箇所を分析するための基準文書です。

---

## 1. システム概要

### 1.1 目的

Python stdlib のみを使用し、命題論理の形式証明を対話的に記述・検査できる軽量証明支援系。
Lean 4 の構文・タクティク体系を参考にしつつ、Python ユーザーが追加ツールなしで利用できる。

### 1.2 設計方針

| 方針 | 内容 |
|---|---|
| **カーネル分離** | 証明の健全性を保証する `type_check()` を `formula/typecheck.py` に集約し、他のコードから独立させる |
| **段階的健全性** | `proved` / `trusted` / `sorry` の三段階で証明の完全性を追跡。すべて偽ではなく、到達可能な状態を段階的に記録する |
| **stdlib のみ** | 外部ライブラリに依存しない。`hmac` / `json` / `logging` / `re` / `fractions` などの stdlib を活用する |
| **後方互換 API** | デコレータ形式（`@theorem`）とクラス形式（`class AndComm(Theorem):`）を共存させる |
| **ランタイムガード** | 動的型付けの弱点を `util.guards` の事前型チェックで補完する |

---

## 2. アーキテクチャ全体

### 2.1 モジュール依存関係

```
┌─────────────────────────────────────────────────────────────────┐
│  ユーザーコード / Lean ファイル                                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
          ┌──────────────▼──────────────┐
          │         cli/                │  コマンドラインエントリポイント
          │  main.py  runner.py         │
          └──────────────┬──────────────┘
                         │
          ┌──────────────▼──────────────┐
          │         dsl/                │  Python ライブラリ（公開 API）
          │  prop.py  class_api.py      │
          │  decorators.py  registry.py │
          │  runner.py  helpers.py      │
          │  tactic_objects.py          │
          │  certificate.py             │
          └──────┬───────────────┬──────┘
                 │               │
    ┌────────────▼───┐   ┌───────▼────────┐
    │   tactics/     │   │   parser/      │  Lean 4 ↔ Python 変換
    │  engine.py     │   │  lean_parser   │
    │  primitives.py │   │  lean_to_py    │
    └────────┬───────┘   │  py_to_lean    │
             │           └────────────────┘
    ┌────────▼───────────────────────────┐
    │           kernel/                   │  証明状態管理（信頼境界の入口）
    │  proof_state.py  errors.py          │
    └────────┬───────────────────────────┘
             │
    ┌────────▼───────────────────────────┐
    │           formula/                  │  信頼カーネル（AST・証明項・型検査）
    │  ast.py  proof_terms.py            │
    │  typecheck.py  parser.py           │
    │  ring.py  prop_simp.py             │
    │  linear_arith.py                   │
    └────────────────────────────────────┘

    ┌─────────────────────────────────────┐
    │  util/  (横断的関心事)               │
    │  guards.py  log_fmt.py             │
    └─────────────────────────────────────┘
    ┌─────────────────────────────────────┐
    │  logger.py  (横断的関心事)           │
    └─────────────────────────────────────┘
```

### 2.2 信頼境界（Trust Boundary）

```
信頼境界の外（untrusted zone）:
  dsl/ / tactics/ / parser/ / cli/
  → ここのコードがバグっても健全性は破れない

信頼境界（trusted kernel）:
  formula/typecheck.py  ← type_check()
  kernel/proof_state.py ← close_with()  ← typecheck を必ず経由する唯一のゴール閉鎖経路

信頼境界のコントラクト:
  close_with(term) は必ず type_check(ctx, term) を呼ぶ。
  type_check が ProofTypeError を投げれば close_with は TacticError を再送出して失敗する。
  trusted_close() は後方互換のため残るが、タクティク実装では原則使用しない。
  暗黙の trusted fallback は廃止: 検証不能なケースは TacticError で停止する。
```

---

## 3. モジュール詳細設計

### 3.1 `formula/` — 信頼カーネル

証明の健全性を保証するコアモジュール。ここを正しく保つことがシステム全体の正しさの根拠になる。

#### 3.1.1 `formula/ast.py` — 論理式 AST

命題論理の論理式を表す不変データクラス群。Python の `dataclass(frozen=True)` で実装。

| クラス | 対応論理記号 | フィールド |
|---|---|---|
| `FVar(name)` | 命題変数 P | `name: str` |
| `FImpl(l, r)` | P → Q | `l, r: _F` |
| `FAnd(l, r)` | P ∧ Q | `l, r: _F` |
| `FOr(l, r)` | P ∨ Q | `l, r: _F` |
| `FNot(x)` | ¬P | `x: _F` |
| `FIff(l, r)` | P ↔ Q | `l, r: _F` |
| `FAll(var, body)` | ∀x, P(x) | `var: str, body: _F` |
| `FEx(var, body)` | ∃x, P(x) | `var: str, body: _F` |
| `FEq(l, r)` | l = r | `l, r: str`（項文字列） |
| `FApp(fn, args)` | f(x, y) | `fn: str, args: List[str]` |
| `FTrue` | True | なし |
| `FFalse` | False | なし |

型エイリアス: `_F = Union[FVar, FImpl, FAnd, FOr, FNot, FIff, FAll, FEx, FEq, FApp, FTrue, FFalse]`

**設計上の注意点**:
- `FEq` の `l`, `r` は `str`（項文字列）であり、論理式 AST ではない。ring/omega の決定手続きが文字列として処理するため。
- すべて `frozen=True` なので hashable かつ不変。

#### 3.1.2 `formula/proof_terms.py` — 証明項

証明の「なぜ正しいか」を記録する証明項。自然演繹の推論規則に対応。

| 証明項 | 対応推論規則 | フィールド |
|---|---|---|
| `PVar(name)` | 変数規則（仮説参照） | `name: str` |
| `PLam(var, dom, body)` | →-Introduction | `var: str, dom: _F, body: PTerm` |
| `PApp(fn, arg)` | →-Elimination | `fn, arg: PTerm` |
| `PAndI(left, right)` | ∧-Introduction | `left, right: PTerm` |
| `PAndE1(inner)` | ∧-Elimination left | `inner: PTerm` |
| `PAndE2(inner)` | ∧-Elimination right | `inner: PTerm` |
| `POrIL(pf, right_type)` | ∨-Introduction left | `pf: PTerm, right_type: _F` |
| `POrIR(left_type, pf)` | ∨-Introduction right | `left_type: _F, pf: PTerm` |
| `PRefl(term)` | 等式反射律 | `term: str` |
| `PTrueI` | True-Introduction | なし |
| `PRing(lhs, rhs)` | ring 決定手続き | `lhs, rhs: str` |
| `PSimp(goal_str)` | simp 決定手続き | `goal_str: str` |
| `POmega(goal_str)` | omega 決定手続き | `goal_str: str` |
| `PNormNum(lhs, rhs)` | norm_num 決定手続き | `lhs, rhs: str` |

型エイリアス: `PTerm = Union[PVar, PAndE1, ..., PNormNum]`

**設計上の注意点**:
- `PLam` / `PApp` は高階論理の証明項に相当するが、現実装では `intro` と関数適用のみ対応。
- 決定手続き証明項（`PRing` / `POmega` / `PSimp` / `PNormNum`）は `type_check()` 内部でアルゴリズムを呼び出して検証する。

#### 3.1.3 `formula/typecheck.py` — 型検査器（信頼カーネルの核心）

`type_check(ctx: Dict[str, _F], term: PTerm) -> _F`

コンテキスト `ctx`（変数名 → 型の写像）と証明項 `term` を受け取り、証明項が証明する命題を返す。
型エラーは `ProofTypeError` を送出する。

**型検査ルール（抜粋）**:

```
PVar(h)        : ctx[h] が型
PLam(h, A, B) : Γ, h:A ⊢ B  →  Γ ⊢ A → B
PApp(f, a)    : Γ ⊢ A → B, Γ ⊢ A  →  Γ ⊢ B
PAndE1(p)     : Γ ⊢ A ∧ B  →  Γ ⊢ A
PAndE2(p)     : Γ ⊢ A ∧ B  →  Γ ⊢ B
PRefl(t)      : Γ ⊢ t = t
PTrueI        : Γ ⊢ True
PRing(l, r)   : ring_equal(l, r) が成立  →  Γ ⊢ l = r
PSimp(g)      : simp_proves(ctx, g) が成立  →  Γ ⊢ g
POmega(g)     : omega_proves(hyp_strs, g) が成立  →  Γ ⊢ g
PNormNum(l,r) : _eval_const(l) == _eval_const(r)  →  Γ ⊢ l = r
```

#### 3.1.4 `formula/parser.py` — 論理式パーサ・ユーティリティ

- `fparse(s: str) -> Optional[_F]`: 文字列を論理式 AST に変換。`None` は解析失敗。
- `fstr(f: _F) -> str`: 論理式を文字列に変換（`fparse` の逆）。
- `feq(a: _F, b: _F) -> bool`: 論理式の構造的等値比較。
- `fsubst(f: _F, from_: str, to: str) -> _F`: 論理式中の項文字列を置換（`rw` で使用）。

**`fparse` の対応構文**（優先度低い順）:

```
↔  :  P.iff(Q)  / P ↔ Q
→  :  P >> Q    / P → Q  / P ⊃ Q
∨  :  P | Q     / P ∨ Q
∧  :  P & Q     / P ∧ Q
¬  :  ~P        / ¬P
量化子: ∀ x, P  / ∃ x, P  / ForAll / Exists
等式:  l = r
関数適用: f(x, y)
True / False / 変数名
```

#### 3.1.5 `formula/ring.py` — 多項式正規化（ring 決定手続き）

`ring_equal(lhs: str, rhs: str) -> bool`

項文字列を多項式に変換し、正規化した係数辞書を比較することで等式を判定する。
変数を含む等式（例: `(a+b)*(a-b) = a^2 - b^2`）に対応。

実装: `normalize_ring(expr) -> Dict[Tuple[str, ...], Fraction]`
- キー: 変数のソート済みタプル（モノミアル）
- 値: 有理数係数（`Fraction`）

**制約**: 乗算・加減算のみ対応。除算・冪乗は `^` 演算子をサポート（整数指数のみ）。

#### 3.1.6 `formula/prop_simp.py` — 命題簡約（simp 決定手続き）

`simp_proves(ctx: Dict[str, _F], goal: _F) -> bool`

コンテキスト中の仮説を考慮した命題論理の真理値表評価。
変数に `True` / `False` を割り当てる全 2^n 通りのモデルを試す（n はゴール中の変数数）。
コンテキスト中の仮説も同時に評価し、仮説を満たすモデルでのみゴールが成立するかを確認する。

**制約**: 変数の数が多いとき（n > ~15）は指数的に遅くなる。プロトタイプ向け実装。

#### 3.1.7 `formula/linear_arith.py` — 線形算術（omega 決定手続き）

`omega_proves(hyp_strs: List[str], goal_str: str) -> bool`

Fourier-Motzkin 消去法で線形算術の命題（整数・自然数の不等式・等式）を判定する。
コンテキスト中の線形算術仮説と合わせてゴールを検証する。

**制約**: 非線形項（乗算・冪乗が変数に含まれる）は非対応。

---

### 3.2 `kernel/` — 証明状態管理

#### 3.2.1 `kernel/proof_state.py` — ProofState

証明の可変状態を管理するクラス。LCF スタイルの証明器における「証明状態」に対応。

**主要フィールド**:

| フィールド | 型 | 役割 |
|---|---|---|
| `goals` | `List[str]` | 残留ゴール文字列のリスト（先頭が現在のゴール） |
| `_hyp_stack` | `List[Dict[str, str]]` | ゴールごとの仮説辞書スタック（ゴールと並列） |
| `admitted` | `bool` | `sorry` が適用された場合 `True` |
| `closed` | `bool` | 全ゴールが閉じられた場合 `True` |
| `trusted_steps` | `List[str]` | カーネル未検証で受け入れたタクティク名のリスト |
| `trusted_reasons` | `List[str]` | 各 trusted_step に対応する理由（parallel） |
| `trusted_suggestions` | `List[str]` | 各 trusted_step に対応する改善提案（parallel） |
| `tactic_trace` | `List[str]` | 適用されたタクティク文字列の順序リスト |

**主要メソッド**:

| メソッド | 役割 |
|---|---|
| `close_with(term)` | **唯一の sound なゴール閉鎖経路**。`type_check()` を通過した場合のみゴールを閉じる |
| `pop_goal()` | 現在のゴールとその仮説スタックを取り除く（`trusted_close` が内部で使用） |
| `replace_goal(new_goal)` | 現在のゴールを別のゴールで置き換える（`apply_` の後退適用など） |
| `push_goal(goal)` | 新しいゴールをスタック先頭に追加（`constructor` のサブゴール生成） |
| `split_have(sub_goal, name, typ)` | `have h : T` のサブゴールと継続ゴールを生成 |
| `snapshot()` | 現在状態の深いコピーを返す（リプレイ検証用） |
| `is_fully_sound` | `admitted` なし、`trusted_steps` 空のとき `True` |

**`close_with(term)` の処理フロー**:

```
1. 現在のゴール文字列を fparse で _F に変換
2. 仮説辞書を {name: fparse(typ_str)} の ctx に変換
3. type_check(ctx, term) を呼ぶ
   ├── ProofTypeError → TacticError を再送出（ゴールは閉じない）
   └── 成功 → proved: _F を返す
4. feq(proved, goal_type) で型が一致するか確認
   ├── 不一致 → TacticError
   └── 一致 → pop_goal() でゴールを閉じる
```

#### 3.2.2 `kernel/errors.py` — TacticError

タクティク適用の失敗を表す例外。`TacticError(message: str)` のみ定義。
`Exception` を継承するシンプルな例外クラス。

---

### 3.3 `tactics/` — タクティクエンジン

タクティク文字列を受け取り `ProofState` を更新するディスパッチャ層。
`formula/` / `kernel/` に依存するが、`dsl/` には依存しない。

#### 3.3.1 `tactics/engine.py` — apply_tactic（メインディスパッチャ）

`apply_tactic(state: ProofState, tactic: str) -> ProofState`

タクティク文字列を受け取り、パターンマッチで各ハンドラへ振り分ける。

**ディスパッチテーブル**（実装上の `if` チェーン）:

| タクティク文字列パターン | 振り先 | 健全性 |
|---|---|---|
| `"admit"` / `"sorry"` | `state.admitted = True` | sorry |
| `"intro ..."` / `"intros ..."` | `do_intro()` | sound |
| `"exact ..."` | `parse_proof_term()` → `close_with()` | sound（失敗時は TacticError） |
| `"assumption"` | 仮説スキャン → `close_with(PVar)` | sound |
| `"rfl"` | `FEq` 確認 → `close_with(PRefl)` | sound |
| `"trivial"` | `FTrue` / `FEq` / 仮説照合 → `close_with` | sound |
| `"constructor"` / `"split"` | `FAnd` / `FIff` のゴール分割 | sound |
| `"left"` / `"right"` | `FOr` のゴール選択 | sound |
| `"use ..."` | `FEx` のゴール具体化 | sound |
| `"apply ..."` | `do_apply()` | sound（失敗時は TacticError） |
| `"have ..."` | サブゴール生成 or 即時導入 | sound / trusted（`have h := expr` のみ明示的 trusted） |
| `"contradiction"` | `try_kernel_close_simple()` → TacticError | sound（失敗時は TacticError） |
| `"ring"` | `PRing` → `close_with` → TacticError | sound（失敗時は TacticError） |
| `"norm_num"` | `PNormNum` → `close_with` → TacticError | sound（失敗時は TacticError） |
| `"omega"` | `POmega` → `close_with` → TacticError | sound（失敗時は TacticError） |
| `"simp ..."` | `PSimp` → `close_with` → TacticError | sound（失敗時は TacticError） |
| `"rw ..."` | `do_rw()` | sound（失敗時は TacticError） |
| `"cases ..."` / `"rcases ..."` | `do_cases()` | sound（失敗時は TacticError） |
| その他 | `TacticError("unknown tactic")` | — |

エントリポイントで `require_proof_state` / `require_tactic_string` を呼ぶ（ガード）。

#### 3.3.2 `tactics/primitives.py` — 原始操作

`apply_tactic` から呼ばれる各タクティクの実装本体。

**`do_intro(state, name)`**:
```
goal が FImpl(A, B) → hypotheses[name] = A, replace_goal(B)
goal が FAll(x, P) → replace_goal(P)（変数は消える）
goal が FNot(P)    → hypotheses[name] = P, replace_goal("False")
それ以外           → TacticError
```

**`do_apply(state, arg)`**:
```
arg が仮説にない       → TacticError（not in context）
仮説型 = FImpl(A, B):
  feq(term_type, goal) → close_with(PVar(arg))  ← sound
  feq(B, goal)         → replace_goal(A)         ← sound（後退適用）
  FNot(P) and False   → replace_goal(P)          ← sound（否定除去）
  それ以外            → TacticError（結論がゴールに合わない）
```

**`do_cases(state, arg)`**:
```
hyp が FAnd(A, B) → h1:A, h2:B を仮説に追加（∧除去、sound）
hyp が FOr(A, B)  → 2サブゴール生成（left/right 仮説、sound）
それ以外          → TacticError（∧/∨ 以外は対応不可）
```

**`do_rw(state, rules_text)`**:
```
"[h1, h2, ...]" を解析
各ルール h:
  hypotheses[h] が FEq(a, b) → fsubst でゴール中の a を b に置換（sound）
  そうでない                 → TacticError（等式仮説でない）
置換後、try_kernel_close_simple() で自動閉鎖を試みる
```

**`trusted_close(state, tag, reason)`**:
カーネル検証なしにゴールを閉じる。`trusted_steps` / `trusted_reasons` に記録。
`pop_goal()` を直接呼ぶため `type_check()` は経由しない（非 sound）。
**注意**: タクティク実装での暗黙的呼び出しは廃止。現在は `have h := expr` が
内部で同様の操作を行う唯一の明示的 trusted ステップ。

**`try_kernel_close_simple(state)`**:
```
FTrue → close_with(PTrueI)
FEq で l == r → close_with(PRefl)
仮説に goal と feq なものがある → close_with(PVar)
```

---

### 3.4 `dsl/` — Python ライブラリ（公開 API）

ユーザーが直接触れる層。証明の記述・登録・照会を担う。

#### 3.4.1 `dsl/prop.py` — Prop / ForAll / Exists

`Prop(name)` は Python 演算子でオーバーロードされた命題変数ラッパー。
`str(prop)` で `fparse` が解析できる命題文字列を返す。

| Python 式 | `str()` 出力 | 論理記号 |
|---|---|---|
| `P & Q` | `"P ∧ Q"` | ∧ |
| `P \| Q` | `"P ∨ Q"` | ∨ |
| `P >> Q` | `"P → Q"` | → |
| `~P` | `"¬P"` | ¬ |
| `P.iff(Q)` | `"P ↔ Q"` | ↔ |
| `ForAll("x", P)` | `"∀ x, P"` | ∀ |
| `Exists("x", P)` | `"∃ x, P"` | ∃ |

#### 3.4.2 `dsl/tactic_objects.py` — タクティクオブジェクト

クラスベース API で使用するタクティクオブジェクト群。
すべて `Tactic` 基底クラスを継承し、`__str__()` でタクティク文字列を返す。

クラス一覧: `intro`, `intros`, `exact`, `assumption`, `rfl`, `trivial`,
`constructor`, `split`, `left`, `right`, `use`,
`apply_`, `have`, `rw`, `simp`, `ring`, `omega`, `norm_num`,
`sorry_`, `contradiction`

#### 3.4.3 `dsl/class_api.py` — Theorem / Lemma / Axiom メタクラス

クラス定義時に自動登録するメタクラス機構。

**`_TheoremMeta.__new__`** の処理:
```
1. 直接の親が _TheoremMeta でなければスキップ（基底クラス自身）
2. namespace に prop がなければスキップ
3. str(prop) で statement を取得
4. tactics を str リストに変換
5. name 属性またはクラス名を entry_name に
6. _register_with_proof(kind, entry_name, statement, ..., tactics_str) を呼ぶ
```

`Theorem._default_kind = "theorem"`, `Lemma._default_kind = "lemma"`。

**`_AxiomMeta.__new__`** は `register_entry` を直接呼ぶ（タクティク実行なし）。

#### 3.4.4 `dsl/decorators.py` — @theorem / @lemma / @axiom

デコレータ形式 API の実装。内部では `_register_with_proof()` を呼ぶ。

**`_register_with_proof(kind, name, statement, fn, tactics)`** の処理:
```
1. tactics が指定されていれば run_tactics(statement, tactics)
   なければ run_function_proof(statement, fn)（証明関数形式）
2. replay_proof(statement, ...) でリプレイ検証
3. state_to_status(...) でステータスを決定
4. status == "proved" のみ issue_certificate() を呼ぶ
5. register_entry(name, {...}) でレジストリに登録
6. _log_proof_status() でログ出力
```

#### 3.4.5 `dsl/registry.py` — 証明レジストリ

`_REGISTRY: Dict[str, Dict]` がモジュールレベルのシングルトン辞書。

**登録エントリのスキーマ**:

```python
{
  "kind":               "theorem" | "lemma" | "axiom" | "def",
  "name":               str,
  "statement":          str,       # fparse で解析可能な命題文字列
  "status":             "proved" | "trusted" | "sorry" | "axiom" | "defined" | "incomplete (...)",
  "trusted_steps":      List[str], # カーネル未検証のタクティク名
  "trusted_reasons":    List[str], # 各 trusted_step の理由（parallel）
  "trusted_suggestions":List[str], # 各 trusted_step の改善提案（parallel）
  "tactics":            List[str], # 適用されたタクティク文字列
  "certificate":        Optional[Dict],  # ProofCertificate.to_dict() or None
  "replay_ok":          bool,
}
```

**`state_to_status(admitted, closed, goals_count, trusted_steps_count, replay_ok) -> str`**:

```
admitted == True        → "sorry"
closed and trusted == 0 and replay_ok → "proved"
closed                  → "trusted"
else                    → "incomplete (N goal(s) remaining)"
```

**`revalidate_proof(name, new_tactics)`**:
- `trusted` / `sorry` のエントリに改良版タクティクを再実行
- `proved` になれば証明書を発行してレジストリを更新
- `proved` / `axiom` / `defined` には何もしない

**`get_proof_summary(name) -> Optional[Dict]`** の返却スキーマ:

```python
{
  "name":                str,
  "kind":                str,
  "status":              str,
  "can_issue_certificate": bool,   # status == "proved" のとき True
  "trusted_steps":       List[str],
  "trusted_reasons":     List[str],
  "trusted_suggestions": List[str],
  "replay_ok":           bool,
  "error_message":       Optional[str],
}
```

#### 3.4.6 `dsl/runner.py` — run_tactics / replay_proof

**`run_tactics(statement, tactics) -> ProofState`**:
- `ProofState(statement)` を初期化
- `apply_tactic(state, tac)` を順に呼ぶ
- `TacticError` が発生したらログを出してループを抜ける
- 各タクティク後に `_log_tactic_result()` でログ出力

**`replay_proof(statement, tactics) -> bool`**:
- `run_tactics` と同じ手順を再実行
- `state.closed and not state.admitted and not state.trusted_steps` を返す
- プロトコルの健全性確認（trusted fallback なしで完全閉鎖できるか）

**`run_function_proof(statement, proof_fn) -> ProofState`**:
- 引数ありの関数を `proof_fn(state)` として呼ぶ（関数スタイル証明向け）
- `tactic_trace` を `replay_source` として使う

#### 3.4.7 `dsl/certificate.py` — ProofCertificate

`status == "proved"` の証明に発行される HMAC-SHA256 署名証明書。

**スキーマ**:
```python
@dataclass(frozen=True)
class ProofCertificate:
    statement: str
    tactics:   List[str]
    replay_ok: bool
    signature: str      # HMAC-SHA256 の hex digest
```

**署名対象**:
```json
{"replay_ok": true, "statement": "...", "tactics": ["..."]}
```
（JSON の `sort_keys=True` で決定論的に） → HMAC-SHA256 → hex

**シークレット**: 環境変数 `ZFC_LEANPY_CERT_SECRET`（未設定時は `"zfc-leanpy-dev-secret"`）

**`issue_certificate(statement, tactics, replay_ok) -> Optional[ProofCertificate]`**:
- `replay_ok == False` なら `None`を返す
- 署名を生成し `verify()` で自己検証

#### 3.4.8 `dsl/helpers.py` — ProofState 関数ヘルパ

関数スタイル証明（`proof_fn(state)` 形式）で使えるヘルパ関数群。
内部では `apply_tactic(state, "tactic_string")` を呼ぶラッパー。

---

### 3.5 `parser/` — Lean 4 ↔ Python 変換

Lean 4 ランタイムに依存せず、`.lean` ファイルをテキストとして解析する。

#### 3.5.1 `parser/lean_parser.py` — Lean 4 パーサ

`parse_lean_file(path: str) -> List[Dict]`

`.lean` ファイルを行単位でスキャンし、`theorem` / `axiom` 定義を抽出する。
正規表現ベースのシンプルなパーサ。

**エントリスキーマ**（パーサ出力）:
```python
{
  "kind":      "theorem" | "axiom",
  "name":      str,
  "statement": str,
  "tactics":   List[str],   # "by ..." ブロックの行ごとタクティク
}
```

#### 3.5.2 `parser/lean_to_py.py` — Lean → Python 変換

`lean_to_python(entries: List[Dict]) -> str`

パーサ出力を Python DSL コードの文字列に変換する。
`Theorem` / `Axiom` クラス形式のコードを生成する。

#### 3.5.3 `parser/py_to_lean.py` — Python → Lean 変換

`registry_to_lean() -> str` / `python_file_to_lean(path, output)` など

レジストリに登録された定理を Lean 4 構文で出力する。

---

### 3.6 `cli/` — CLI エントリポイント

`python -m zfc_leanpy` で起動する。

#### 3.6.1 `cli/main.py` — 引数パーサ

`argparse` でサブコマンドを切り替える:

| オプション | 処理 |
|---|---|
| なし（ファイルのみ） | `interpret_file(path)` |
| `--step [theorem]` | `step_file(path, theorem)` |
| `--convert` | `convert_file(path, output)` |
| `--to-lean` | `python_file_to_lean(path, output)` |

#### 3.6.2 `cli/runner.py` — ファイル実行

**`interpret_file(path)`**:
- `.lean` ファイルなら `parse_lean_file` → `run_tactics` の組み合わせで実行
- `.py` ファイルなら `exec` で実行（DSL 登録が走る）
- 結果を `format_proof_status_tag` でログ出力

**`step_file(path, theorem_name)`**:
- タクティクごとに `ProofState.display()` を呼んでゴール状態を表示

---

### 3.7 `util/` — ユーティリティ

横断的関心事（型安全・ログ整形）を一元管理するモジュール。

#### 3.7.1 `util/guards.py` — 型ガード

動的型付けの弱点を補う入口検証。

- `require_proof_state(obj, context) -> ProofState`: 型不一致なら `TacticError`
- `require_tactic_string(obj, context) -> str`: 型不一致なら `TacticError`

`apply_tactic()` の冒頭で必ず呼ばれる。

#### 3.7.2 `util/log_fmt.py` — ログ整形

ANSI カラー付きのステータス表示ユーティリティ。

- `format_proof_status_tag(status, trusted_steps) -> Tuple[str, str]`: `(icon, tag)` を返す
- `format_trusted_step_detail(step, reason) -> str`: `"· unverified step: ..."` 行を返す
- `ANSI` クラス: TTY 判定付きのカラー出力ヘルパ

---

### 3.8 `logger.py` — 共通ロギング設定

ライブラリとして `"zfc_leanpy"` ロガーに `NullHandler` のみを登録する。
アプリ・CLI 側でハンドラを追加することでログ出力を有効化できる。

`get_logger(name: str) -> logging.Logger` は `logging.getLogger(name)` のラッパー。

---

### 3.9 `axioms.py` — ZFC 公理（オプション）

ZFC 公理系を `@axiom` デコレータで定義したオプションモジュール。
コアシステムには含まれず、明示的に `import` した場合のみ登録される。

`ALL_AXIOMS: List[str]` — 公理名のリスト
`get_axiom(name: str) -> Optional[Dict]` — レジストリからの取得ヘルパ

---

### 3.10 `proof_engine.py` — 命題論理デモ

命題論理の標準的な定理を `@theorem` デコレータで定義したデモモジュール。
コアシステムとは独立したサンプルスクリプト。

---

## 4. データフロー

### 4.1 クラスベース API での証明登録フロー

```
class AndComm(Theorem):
    prop    = (P & Q) >> (Q & P)
    tactics = [intro("h"), constructor(), exact("h.2"), exact("h.1")]

         │（Pythonクラス定義時）
         ▼
_TheoremMeta.__new__()
  ├─ str(prop) → statement = "P ∧ Q → Q ∧ P"
  ├─ [str(t) for t in tactics] → ["intro h", "constructor", "exact h.2", "exact h.1"]
  └─ _register_with_proof("theorem", "AndComm", statement, ..., tactics_str)
              │
              ▼
       run_tactics(statement, tactics)
              │
              ├─ ProofState("P ∧ Q → Q ∧ P")
              ├─ apply_tactic(state, "intro h")  → do_intro() → hypotheses["h"] = "P ∧ Q", goal = "Q ∧ P"
              ├─ apply_tactic(state, "constructor") → push_goal("Q"), replace_goal("P")... 実際は Q∧P を split
              ├─ apply_tactic(state, "exact h.2") → parse_proof_term("h.2") = PAndE2(PVar("h"))
              │                                      close_with(PAndE2(PVar("h")))
              │                                        └─ type_check({h: FAnd(FVar(P), FVar(Q))}, PAndE2(PVar("h")))
              │                                           → FAnd.r = FVar(Q) ✓
              └─ apply_tactic(state, "exact h.1") → close_with(PAndE1(PVar("h"))) → FAnd.l = FVar(P) ✓
              │
              ▼
       state.closed == True, trusted_steps == []
              │
              ▼
       replay_proof() → True
              │
              ▼
       state_to_status() → "proved"
              │
              ▼
       issue_certificate() → ProofCertificate(signature=...)
              │
              ▼
       register_entry("AndComm", {status: "proved", certificate: {...}, ...})
```

### 4.2 tactic 失敗フロー（旧 trusted fallback フロー）

```
apply_tactic(state, "apply h")
        │
        ▼
do_apply(state, "h")
        │
        ├─ h in hypotheses? No → TacticError("apply: hypothesis 'h' not found …")
        │                               ↳ run_tactics がキャッチしてログ出力・ループ中断
        │
        └─ h in hypotheses? Yes, type = "A → B"
                  ├─ feq(type, goal)? Yes → close_with(PVar(h))  ← sound
                  ├─ isinstance(FImpl) and feq(B, goal)? → replace_goal(A)  ← sound
                  └─ それ以外 → TacticError("apply: '…' conclusion does not match goal …")
                                  ↳ proof は incomplete で停止
```

**設計方針**: タクティクが検証不能なケースを検出した場合、暗黙に `trusted_close`
で前進することを廃止した。代わりに `TacticError` を投げ、`run_tactics` が
ログに記録してループを中断する。結果として証明は **incomplete** 状態になり、
ユーザーは明示的に修正するか `sorry` を使う必要がある。

---

## 5. 証明ステータス遷移

```
                 ┌──────────────┐
                 │  登録直後    │
                 └──────┬───────┘
                        │ run_tactics 実行後
          ┌─────────────┼──────────────────┐
          ▼             ▼                  ▼
       sorry          trusted          incomplete
     (admitted)  (have h := expr など  (TacticError で
                  明示的 trusted ステップ)  途中停止)
          │             │
          └──────┬───────┘
                 │ revalidate_proof(name, new_tactics)
                 ▼                    ▼
             proved（昇格成功時）  incomplete（失敗時）

  axiom / defined: 遷移なし（証明が不要）
  proved: run_tactics が全ゴールを TacticError なしで閉鎖し replay_ok=True
```

**trusted ステータスになる条件（明示的操作のみ）**:
- `have h : T := expr` — 証明項を検証しない即時仮説導入
- `sorry` / `admit` — → sorry ステータス（admitted=True）

**暗黙的 trusted fallback は廃止**: タクティクが検証不能なケースは
`TacticError` を投げ、証明は **incomplete** 状態で停止する。

---

## 6. 型システムと健全性保証

### 6.1 健全性の根拠

1. **唯一の閉鎖経路**: `ProofState.close_with(term)` のみが `pop_goal()` を呼べる公式経路
2. **型検査必須**: `close_with` は `type_check(ctx, term)` を必ず呼ぶ
3. **型検査の完全性**: `type_check` は `formula/typecheck.py` に集中しており、決定手続き証明項も内部でアルゴリズムを実行して検証する
4. **replay 検証**: `replay_proof` で全タクティクを再実行し、trusted_steps なしで閉じられることを確認してから `proved` にする
5. **暗黙的 trusted fallback の廃止**: 検証不能なケースは `TacticError` で停止し、暗黙に証明が前進しない

### 6.2 非健全箇所（known limitations）

| 箇所 | 理由 | 影響 |
|---|---|---|
| `have h := expr` | 証明項を検証しない即時仮説導入（明示的 trusted） | `trusted` ステータス（証明書なし） |
| `fparse` の曖昧性 | 優先度解析が完全でない場合がある | 解析失敗時は `None` を返す |
| `FEq` の項文字列 | 項を AST 化していないため項の等値性は文字列比較 | `ring` / `omega` に依存 |
| `simp` の指数爆発 | 2^n 真理値表 | 変数が多い命題は遅い |

---

## 7. 拡張ポイント（プロトから昇格させる際の差し替え候補）

### 7.1 パーサの強化

**現状**: 正規表現ベースの単純パーサ（`formula/parser.py`）  
**課題**: 複雑な括弧・結合優先度で解析失敗することがある  
**差し替え**: PEG パーサ（`lark` / `parsimonious`）または手書き再帰下降パーサへの置き換え  
**影響範囲**: `formula/parser.py` のみ（インターフェース `fparse/fstr` は変えない）

### 7.2 証明項の永続化

**現状**: `ProofCertificate` は HMAC 署名のみ（証明木は含まない）  
**課題**: 外部ツール（Lean / Coq）への移植時に証明項が失われる  
**差し替え**: 証明木全体を JSON でシリアライズして `certificate` に含める  
**影響範囲**: `formula/proof_terms.py`, `dsl/certificate.py`, `kernel/proof_state.py`

### 7.3 量化子の完全対応

**現状**: `FAll` / `FEx` は `intro` / `use` でゴール変換するが、型追跡が不完全  
**課題**: `∀ x, P(x)` の `apply` で trusted fallback になることがある  
**差し替え**: 証明項に `PForAllI` / `PExI` / `PForAllE` / `PExE` を追加し `type_check` を拡張  
**影響範囲**: `formula/ast.py`, `formula/proof_terms.py`, `formula/typecheck.py`, `tactics/primitives.py`

### 7.4 レジストリの永続化

**現状**: `_REGISTRY` はモジュールレベルのインメモリ辞書（プロセス終了で消える）  
**課題**: 大規模な定理ライブラリの管理・共有ができない  
**差し替え**: SQLite / JSON ファイルへの永続化、またはサーバーサイド API  
**影響範囲**: `dsl/registry.py`（インターフェースは変えない）

### 7.5 型推論

**現状**: `intro` 時に仮説名を指定しなければ `h1` / `h2` ... が自動生成される  
**課題**: 名前の衝突や、量化子変数の追跡が不完全  
**差し替え**: de Bruijn インデックスへの内部表現の移行、または名前解決レイヤーの追加  
**影響範囲**: `formula/ast.py`, `formula/parser.py`, `tactics/primitives.py`

### 7.6 証明書のシークレット管理

**現状**: `ZFC_LEANPY_CERT_SECRET` 環境変数（未設定時は固定文字列）  
**課題**: 本番環境でのシークレットローテーションができない  
**差し替え**: KMS / Vault 連携、または非対称署名（Ed25519）への移行  
**影響範囲**: `dsl/certificate.py` のみ

---

## 8. テスト戦略

| テストファイル | カバー領域 |
|---|---|
| `test_kernel.py` | `ProofState` の状態遷移・ゴール操作 |
| `test_formula.py` | AST・`fparse`・`type_check`・証明項 |
| `test_tactics.py` | 各タクティクの sound / trusted 挙動 |
| `test_dsl.py` | デコレータ・ステータス・証明書発行 |
| `test_class_api.py` | `Theorem` / `Lemma` / `Axiom` クラス API |
| `test_decision_procedures.py` | `ring` / `simp` / `omega` / `norm_num` の正否 |
| `test_lean_parser.py` | `.lean` ファイル解析 |
| `test_converters.py` | Lean ↔ Python 変換 |
| `test_cli.py` | CLI の引数処理・出力 |
| `test_axioms.py` | ZFC 公理の登録・取得 |
| `test_proof_engine.py` | デモ定理の健全性 |
| `test_examples_runtime.py` | `example/` ディレクトリの Lean ファイル実行 |
| `test_proof_status.py` | ステータス遷移・証明書検証 |
| `test_revalidation.py` | `revalidate_proof` による `trusted → proved` 昇格 |
| `test_trusted_improvements.py` | trusted タクティクの改善動作（kernel-verified ケース） |

テスト実行: `./.venv/bin/python -m pytest -q`

`conftest.py` には `clear_registry` autouse フィクスチャがあり、各テスト前後に `dsl.reset_registry()` を呼ぶ。

---
