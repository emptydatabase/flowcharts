"""Parse pseudocode into the intermediate representation."""

from __future__ import annotations

import ast

from .errors import ParseError, UnsupportedSyntaxError
from .metadata import parse_metadata
from .model import Block, Flowchart, If, Input, Node, Output, Process, While

_SUPPORTED = (ast.Expr, ast.Assign, ast.AugAssign, ast.AnnAssign, ast.Pass, ast.If, ast.While)

_UNSUPPORTED_NAMES = {
    ast.For: "for",
    ast.AsyncFor: "async for",
    ast.With: "with",
    ast.AsyncWith: "async with",
    ast.Try: "try",
    ast.FunctionDef: "def",
    ast.AsyncFunctionDef: "async def",
    ast.ClassDef: "class",
    ast.Import: "import",
    ast.ImportFrom: "import",
    ast.Return: "return",
    ast.Break: "break",
    ast.Continue: "continue",
    ast.Raise: "raise",
    ast.Delete: "delete",
    ast.Assert: "assert",
    ast.Global: "global",
    ast.Nonlocal: "nonlocal",
}


def parse(source: str) -> Flowchart:
    """Parse pseudocode source into a :class:`~flowcharts.model.Flowchart`."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ParseError(f"invalid pseudocode: {exc}") from exc

    docstring, body = _split_docstring(tree.body)
    return Flowchart(metadata=parse_metadata(docstring), block=_parse_block(body, source))


def _split_docstring(body: list[ast.stmt]) -> tuple[str | None, list[ast.stmt]]:
    if body:
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            return first.value.value, body[1:]
    return None, body


def _parse_block(body: list[ast.stmt], source: str) -> Block:
    return Block([_parse_stmt(stmt, source) for stmt in body])


def _parse_stmt(stmt: ast.stmt, source: str) -> Node:
    if isinstance(stmt, ast.If):
        return If(
            test=_condition_text(stmt.test),
            negated=_condition_negated(stmt.test),
            body=_parse_block(stmt.body, source),
            orelse=_parse_block(stmt.orelse, source),
        )
    if isinstance(stmt, ast.While):
        if stmt.orelse:
            raise UnsupportedSyntaxError(
                "while ... else is not supported", stmt.lineno
            )
        return While(
            test=_condition_text(stmt.test),
            negated=_condition_negated(stmt.test),
            body=_parse_block(stmt.body, source),
        )
    if isinstance(stmt, ast.Expr):
        value = stmt.value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            return Process(str(value.value))
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
            if value.func.id == "input":
                return Input(_call_text(value, source))
            if value.func.id == "print":
                return Output(_call_text(value, source))
        return Process(_source_text(stmt, source))
    if not isinstance(stmt, _SUPPORTED):
        name = _UNSUPPORTED_NAMES.get(type(stmt), type(stmt).__name__)
        raise UnsupportedSyntaxError(f"unsupported {name!r} statement", stmt.lineno)
    return Process(_source_text(stmt, source))


def _condition_parts(test: ast.expr) -> tuple[ast.expr, bool]:
    """Strip leading ``not`` operators; return (expression, negated)."""
    negated = False
    node = test
    while isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        negated = not negated
        node = node.operand
    return node, negated


def _condition_text(test: ast.expr) -> str:
    node, _ = _condition_parts(test)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return ast.unparse(node)


def _condition_negated(test: ast.expr) -> bool:
    _, negated = _condition_parts(test)
    return negated


def _call_text(call: ast.Call, source: str) -> str:
    if not call.args:
        return ast.unparse(call) if call.keywords else ""
    parts = []
    for arg in call.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            parts.append(arg.value)
        else:
            parts.append(ast.unparse(arg))
    return ", ".join(parts)


def _source_text(stmt: ast.stmt, source: str) -> str:
    segment = ast.get_source_segment(source, stmt)
    if segment is None:
        segment = ast.unparse(stmt)
    return segment.strip()
