"""Intermediate representation of parsed pseudocode."""

from __future__ import annotations

from dataclasses import dataclass, field

from .metadata import Metadata


class Node:
    """Base class for every statement node."""


@dataclass
class Block:
    """An ordered sequence of nodes."""

    nodes: list[Node] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.nodes)


@dataclass
class Process(Node):
    """A plain process box."""

    text: str


@dataclass
class Input(Node):
    """An input parallelogram."""

    text: str


@dataclass
class Output(Node):
    """An output parallelogram."""

    text: str


@dataclass
class If(Node):
    """A decision with a yes/no split.

    ``test`` is the *displayed* condition; ``negated`` records that the
    pseudocode used ``not``, which only swaps the drawn yes/no labels.
    ``orelse`` holds the else branch, or a single nested :class:`If`
    for an ``elif``.
    """

    test: str
    negated: bool
    body: Block
    orelse: Block

    @property
    def nested(self) -> "If | None":
        """The nested ``elif`` decision, if any."""
        if len(self.orelse.nodes) == 1 and isinstance(self.orelse.nodes[0], If):
            return self.orelse.nodes[0]
        return None


@dataclass
class While(Node):
    """A loop: decision with the body below it."""

    test: str
    negated: bool
    body: Block


@dataclass
class Flowchart:
    """A whole parsed document."""

    metadata: Metadata
    block: Block
