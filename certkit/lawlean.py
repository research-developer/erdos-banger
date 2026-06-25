"""Translate a flat magma equational law (term = term over one binary op) into a
Lean ∀-quantified Prop over `Fin n`, using the Lean operator name `op`.

Grammar: TERM := VAR | '(' TERM ')' | TERM OP TERM   (OP ∈ {◇,*,·}; VAR ∈ [a-z]).
Fully-parenthesized inputs (the ETP catalogue form) parse unambiguously; bare
chains parse left-associatively.
"""
from __future__ import annotations
from dataclasses import dataclass

OPS = {"◇", "*", "·"}


@dataclass
class Var:
    name: str


@dataclass
class App:
    left: object
    right: object


def _tokenize(s: str) -> list[str]:
    toks: list[str] = []
    for ch in s:
        if ch.isspace():
            continue
        if ch in OPS or ch in "()":
            toks.append(ch)
        elif ch.isalpha() and len(ch) == 1:
            toks.append(ch)
        else:
            raise ValueError(f"bad char {ch!r} in {s!r}")
    return toks


class _Parser:
    def __init__(self, toks: list[str]) -> None:
        self.t = toks
        self.i = 0

    def _peek(self) -> str | None:
        return self.t[self.i] if self.i < len(self.t) else None

    def _next(self) -> str:
        tok = self.t[self.i]
        self.i += 1
        return tok

    def factor(self) -> object:
        tok = self._next()
        if tok == "(":
            inner = self.term()
            assert self._next() == ")", "unbalanced parenthesis"
            return inner
        if tok.isalpha():
            return Var(tok)
        raise ValueError(f"unexpected token {tok!r}")

    def term(self) -> object:
        node = self.factor()
        while self._peek() in OPS:
            self._next()  # consume the operator
            node = App(node, self.factor())  # left-associative
        return node


def parse_term(s: str) -> object:
    p = _Parser(_tokenize(s))
    node = p.term()
    assert p._peek() is None, "trailing tokens"
    return node


def vars_in(t: object, acc: list[str] | None = None) -> list[str]:
    acc = [] if acc is None else acc
    if isinstance(t, Var):
        if t.name not in acc:
            acc.append(t.name)
    else:
        vars_in(t.left, acc)
        vars_in(t.right, acc)
    return acc


def _atom(t: object) -> str:
    return t.name if isinstance(t, Var) else f"({render(t)})"


def render(t: object) -> str:
    if isinstance(t, Var):
        return t.name
    return f"op {_atom(t.left)} {_atom(t.right)}"


def law_to_lean(law: str, n: int) -> str:
    lhs_s, rhs_s = law.split("=")
    lhs, rhs = parse_term(lhs_s), parse_term(rhs_s)
    vs = vars_in(lhs)
    for v in vars_in(rhs):
        if v not in vs:
            vs.append(v)
    binder = " ".join(vs)
    return f"∀ {binder} : Fin {n}, {render(lhs)} = {render(rhs)}"
