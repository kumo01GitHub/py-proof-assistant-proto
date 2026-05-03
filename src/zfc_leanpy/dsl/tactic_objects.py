"""タクティクオブジェクト — str() でタクティク文字列に変換できる。

クラスベース API での使用例:
    class AndComm(Theorem):
        prop = (P & Q) >> (Q & P)
        tactics = [intro("h"), constructor(), exact("h.2"), exact("h.1")]
"""


class Tactic:
    """タクティクオブジェクトの基底クラス。"""

    def __str__(self) -> str:  # pragma: no cover
        raise NotImplementedError


# ── 基本タクティク ────────────────────────────────────────────────

class intro(Tactic):
    def __init__(self, name: str = None) -> None:
        self.name = name

    def __str__(self) -> str:
        return f"intro {self.name}" if self.name else "intro"


class intros(Tactic):
    def __init__(self, *names: str) -> None:
        self.names = names

    def __str__(self) -> str:
        return ("intros " + " ".join(self.names)) if self.names else "intros"


class exact(Tactic):
    def __init__(self, term: str) -> None:
        self.term = term

    def __str__(self) -> str:
        return f"exact {self.term}"


class assumption(Tactic):
    def __str__(self) -> str:
        return "assumption"


class rfl(Tactic):
    def __str__(self) -> str:
        return "rfl"


class trivial(Tactic):
    def __str__(self) -> str:
        return "trivial"


# ── 論理結合子タクティク ──────────────────────────────────────────

class constructor(Tactic):
    def __str__(self) -> str:
        return "constructor"


class split(Tactic):
    def __str__(self) -> str:
        return "split"


class left(Tactic):
    def __str__(self) -> str:
        return "left"


class right(Tactic):
    def __str__(self) -> str:
        return "right"


class use(Tactic):
    def __init__(self, term: str) -> None:
        self.term = term

    def __str__(self) -> str:
        return f"use {self.term}"


# ── 仮説・適用タクティク ─────────────────────────────────────────

class apply_(Tactic):
    def __init__(self, term: str) -> None:
        self.term = term

    def __str__(self) -> str:
        return f"apply {self.term}"


class have(Tactic):
    def __init__(self, name: str, typ: str) -> None:
        self.name = name
        self.typ = typ

    def __str__(self) -> str:
        return f"have {self.name} : {self.typ}"


# ── 書き換え・自動化タクティク ───────────────────────────────────

class rw(Tactic):
    def __init__(self, *rules: str) -> None:
        self.rules = rules

    def __str__(self) -> str:
        return f"rw [{', '.join(self.rules)}]"


class simp(Tactic):
    def __init__(self, *lemmas: str) -> None:
        self.lemmas = lemmas

    def __str__(self) -> str:
        if self.lemmas:
            return f"simp [{', '.join(self.lemmas)}]"
        return "simp"


class ring(Tactic):
    def __str__(self) -> str:
        return "ring"


class omega(Tactic):
    def __str__(self) -> str:
        return "omega"


class norm_num(Tactic):
    def __str__(self) -> str:
        return "norm_num"


# ── その他 ───────────────────────────────────────────────────────

class sorry_(Tactic):
    def __str__(self) -> str:
        return "sorry"


class contradiction(Tactic):
    def __str__(self) -> str:
        return "contradiction"
