"""Geometry: turn the parsed pseudocode into a scene of shapes.

Coordinates use a top-left origin with *y* growing downwards.  The
flow axis sits at ``x = 0``; each node is laid out around it and the
scene is translated onto the canvas when it is drawn.

Layout rules (see README):

* ``if``  -- decision diamond, *yes* branch leaves from the right, *no*
  branch from the left.  Both branches run down and enter the left and
  right sides of a small connection circle; the arrow leaving the
  bottom of the circle continues to the rest of the chart.  An
  ``elif`` is a nested decision whose own circle feeds the outer
  circle's left side.
* ``while`` -- decision diamond with an arrow from its bottom vertex
  into the body below.  The body's end loops back up the left side to
  the diamond's left vertex, while the diamond's right vertex exits
  down the right side and returns to the axis below the body.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .fonts import FontSet
from .languages import Language
from .model import Block, Flowchart, If, Input, Node, Output, Process, While
from .themes import Theme

# --- geometry constants ---------------------------------------------------

NODE_W = 200.0
NODE_MIN_H = 52.0
NODE_PAD = 14.0
TERM_W = 200.0
TERM_MIN_H = 48.0
TERM_PAD = 10.0
DIA_W = 260.0
DIA_H_MIN = 110.0
DIA_TEXT_W = 150.0
DIA_TEXT_PAD = 70.0
IO_SKEW = 22.0
V_GAP = 50.0
CLEAR = 40.0
LANE_EMPTY = 60.0
LANE_PAD = 40.0
JOIN_DROP = 45.0
BODY_GAP = 60.0
BACK_DROP = 26.0
EXIT_DROP = 52.0
CIRCLE_R = 10.0

SHAPE_KINDS = ("terminator", "process", "decision", "input", "output")


# --- scene primitives -----------------------------------------------------


@dataclass(frozen=True)
class BBox:
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2

    def union(self, other: "BBox") -> "BBox":
        return BBox(
            min(self.x0, other.x0),
            min(self.y0, other.y0),
            max(self.x1, other.x1),
            max(self.y1, other.y1),
        )

    @property
    def corners(self) -> tuple[tuple[float, float], ...]:
        return (
            (self.x0, self.y0),
            (self.x1, self.y0),
            (self.x1, self.y1),
            (self.x0, self.y1),
        )


@dataclass
class Shape:
    kind: str
    bbox: BBox
    text: str
    points: list[tuple[float, float]] | None = None


@dataclass
class Connector:
    """A polyline; the arrowhead (if any) points along the last segment."""

    points: list[tuple[float, float]]
    arrow: bool = True
    label: str | None = None
    label_pos: tuple[float, float] | None = None


@dataclass
class Circle:
    cx: float
    cy: float
    r: float

    @property
    def bbox(self) -> BBox:
        return BBox(self.cx - self.r, self.cy - self.r, self.cx + self.r, self.cy + self.r)


@dataclass
class Scene:
    shapes: list[Shape] = field(default_factory=list)
    connectors: list[Connector] = field(default_factory=list)
    circles: list[Circle] = field(default_factory=list)
    title: str | None = None

    def geometry_bbox(self) -> BBox:
        boxes = [shape.bbox for shape in self.shapes]
        boxes.extend(circle.bbox for circle in self.circles)
        for connector in self.connectors:
            for x, y in connector.points:
                boxes.append(BBox(x, y, x, y))
        if not boxes:
            return BBox(0.0, 0.0, 0.0, 0.0)
        box = boxes[0]
        for other in boxes[1:]:
            box = box.union(other)
        return box


# --- text helpers ---------------------------------------------------------


def usable_width(kind: str) -> float:
    """Width available to text inside a shape of the given kind."""
    if kind == "process":
        return NODE_W - 2 * NODE_PAD
    if kind in ("input", "output"):
        return NODE_W - 2 * (NODE_PAD + IO_SKEW)
    if kind == "terminator":
        return TERM_W - 2 * TERM_PAD
    if kind == "decision":
        return DIA_TEXT_W
    raise ValueError(f"unknown shape kind: {kind!r}")


@dataclass
class _Rel:
    """A node's extent relative to its own axis (x = 0).

    ``height`` is the distance from the node's top to its out point,
    which always sits at ``(0, height)``.
    """

    x0: float = 0.0
    x1: float = 0.0
    height: float = 0.0

    @property
    def width(self) -> float:
        return self.x1 - self.x0


@dataclass
class _Ctx:
    fonts: FontSet
    language: Language
    shapes: list[Shape] = field(default_factory=list)
    connectors: list[Connector] = field(default_factory=list)
    circles: list[Circle] = field(default_factory=list)


# --- measuring ------------------------------------------------------------


def _line_height(ctx: _Ctx) -> float:
    return ctx.fonts.line_height(ctx.fonts.body_size)


def _wrap(ctx: _Ctx, text: str, max_width: float) -> list[str]:
    return ctx.fonts.wrap(text, max_width, ctx.fonts.body, ctx.fonts.body_size)


def _box_size(ctx: _Ctx, text: str, kind: str, min_h: float, pad: float) -> tuple[float, float]:
    lines = _wrap(ctx, text, usable_width(kind))
    height = max(min_h, len(lines) * _line_height(ctx) + 2 * pad)
    if kind in ("input", "output"):
        width = NODE_W
    elif kind == "terminator":
        width = TERM_W
    else:
        width = NODE_W
    return width, height


def _decision_size(ctx: _Ctx, test: str) -> tuple[float, float]:
    lines = _wrap(ctx, test, DIA_TEXT_W)
    height = max(DIA_H_MIN, len(lines) * _line_height(ctx) + DIA_TEXT_PAD)
    return DIA_W, height


def _measure(ctx: _Ctx, node: Node) -> _Rel:
    if isinstance(node, (Process, Input, Output)):
        width, height = _box_size(ctx, node.text, _kind_of(node), NODE_MIN_H, NODE_PAD)
        return _Rel(-width / 2, width / 2, height)
    if isinstance(node, If):
        return _measure_if(ctx, node)
    if isinstance(node, While):
        return _measure_while(ctx, node)
    raise AssertionError(f"cannot measure {type(node).__name__}")


def _kind_of(node: Node) -> str:
    if isinstance(node, Input):
        return "input"
    if isinstance(node, Output):
        return "output"
    return "process"


def _measure_block(ctx: _Ctx, block: Block) -> _Rel:
    rel = _Rel()
    for index, node in enumerate(block.nodes):
        child = _measure(ctx, node)
        rel.x0 = min(rel.x0, child.x0)
        rel.x1 = max(rel.x1, child.x1)
        if index:
            rel.height += V_GAP
        rel.height += child.height
    return rel


def _measure_if(ctx: _Ctx, node: If) -> _Rel:
    dw, dh = _decision_size(ctx, node.test)
    body = _measure_block(ctx, node.body)
    false = _measure_block(ctx, node.orelse) if node.orelse else None
    x1 = dw / 2 + CLEAR + body.width
    if false is not None:
        x0 = -(dw / 2 + CLEAR + false.width)
        false_h = false.height
    else:
        x0 = -(dw / 2 + LANE_EMPTY)
        false_h = 0.0
    height = dh + max(body.height, false_h) + JOIN_DROP + CIRCLE_R
    return _Rel(x0, x1, height)


def _measure_while(ctx: _Ctx, node: While) -> _Rel:
    dw, dh = _decision_size(ctx, node.test)
    body = _measure_block(ctx, node.body)
    lane_l = min(-dw / 2, body.x0) - LANE_PAD
    lane_r = max(dw / 2, body.x1) + LANE_PAD
    height = dh + BODY_GAP + body.height + EXIT_DROP
    return _Rel(lane_l, lane_r, height)


# --- placing --------------------------------------------------------------


def _add_shape(
    ctx: _Ctx,
    kind: str,
    bbox: BBox,
    text: str,
    points: list[tuple[float, float]] | None = None,
) -> None:
    ctx.shapes.append(Shape(kind=kind, bbox=bbox, text=text, points=points))


def _diamond(cx: float, y: float, dw: float, dh: float) -> list[tuple[float, float]]:
    cy = y + dh / 2
    return [(cx, y), (cx + dw / 2, cy), (cx, y + dh), (cx - dw / 2, cy)]


def _parallelogram(bbox: BBox, skew: float, forward: bool) -> list[tuple[float, float]]:
    x0, y0, x1, y1 = bbox.x0, bbox.y0, bbox.x1, bbox.y1
    if forward:
        return [(x0 + skew, y0), (x1, y0), (x1 - skew, y1), (x0, y1)]
    return [(x0, y0), (x1 - skew, y0), (x1, y1), (x0 + skew, y1)]


def _layout_block(ctx: _Ctx, block: Block, cx: float, y: float) -> float:
    current = y
    for index, node in enumerate(block.nodes):
        current = _layout_node(ctx, node, cx, current)
        if index < len(block.nodes) - 1:
            ctx.connectors.append(Connector([(cx, current), (cx, current + V_GAP)]))
            current += V_GAP
    return current


def _layout_node(ctx: _Ctx, node: Node, cx: float, y: float) -> float:
    if isinstance(node, (Process, Input, Output)):
        kind = _kind_of(node)
        width, height = _box_size(ctx, node.text, kind, NODE_MIN_H, NODE_PAD)
        bbox = BBox(cx - width / 2, y, cx + width / 2, y + height)
        points = None
        if kind == "input":
            points = _parallelogram(bbox, IO_SKEW, forward=True)
        elif kind == "output":
            points = _parallelogram(bbox, IO_SKEW, forward=False)
        _add_shape(ctx, kind, bbox, node.text, points)
        return y + height
    if isinstance(node, If):
        return _layout_if(ctx, node, cx, y)
    if isinstance(node, While):
        return _layout_while(ctx, node, cx, y)
    raise AssertionError(f"cannot lay out {type(node).__name__}")


def _labels(ctx: _Ctx, node: If | While) -> tuple[str, str]:
    """Return (port-true label, port-false label) for a decision."""
    yes, no = ctx.language.yes, ctx.language.no
    if node.negated:
        return no, yes
    return yes, no


def _layout_if(ctx: _Ctx, node: If, cx: float, y: float) -> float:
    dw, dh = _decision_size(ctx, node.test)
    cy = y + dh / 2
    _add_shape(
        ctx,
        "decision",
        BBox(cx - dw / 2, y, cx + dw / 2, y + dh),
        node.test,
        _diamond(cx, y, dw, dh),
    )

    true_label, false_label = _labels(ctx, node)
    branch_top = y + dh

    body = _measure_block(ctx, node.body)
    body_cx = cx + dw / 2 + CLEAR - body.x0
    body_bottom = _layout_block(ctx, node.body, body_cx, branch_top)
    ctx.connectors.append(
        Connector(
            [(cx + dw / 2, cy), (body_cx, cy), (body_cx, branch_top)],
            label=true_label,
            label_pos=(cx + dw / 2 + 22, cy - 14),
        )
    )

    has_else = bool(node.orelse)
    false_cx = cx - dw / 2 - LANE_EMPTY
    false_bottom = branch_top
    if has_else:
        false = _measure_block(ctx, node.orelse)
        false_cx = cx - dw / 2 - CLEAR - false.x1
        false_bottom = _layout_block(ctx, node.orelse, false_cx, branch_top)
        ctx.connectors.append(
            Connector(
                [(cx - dw / 2, cy), (false_cx, cy), (false_cx, branch_top)],
                label=false_label,
                label_pos=(cx - dw / 2 - 22, cy - 14),
            )
        )

    true_h = body_bottom - branch_top
    false_h = false_bottom - branch_top if has_else else 0.0
    join_y = branch_top + max(true_h, false_h) + JOIN_DROP
    ctx.circles.append(Circle(cx, join_y, CIRCLE_R))

    # Branch bodies descend into the sides of the connection circle.
    ctx.connectors.append(
        Connector(
            [(body_cx, body_bottom), (body_cx, join_y), (cx + CIRCLE_R, join_y)]
        )
    )
    if has_else:
        ctx.connectors.append(
            Connector(
                [(false_cx, false_bottom), (false_cx, join_y), (cx - CIRCLE_R, join_y)]
            )
        )
    else:
        # No else branch: the no-branch is a bare lane down to the circle.
        ctx.connectors.append(
            Connector(
                [
                    (cx - dw / 2, cy),
                    (false_cx, cy),
                    (false_cx, join_y),
                    (cx - CIRCLE_R, join_y),
                ],
                label=false_label,
                label_pos=(cx - dw / 2 - 22, cy - 14),
            )
        )

    return join_y + CIRCLE_R


def _layout_while(ctx: _Ctx, node: While, cx: float, y: float) -> float:
    dw, dh = _decision_size(ctx, node.test)
    cy = y + dh / 2
    _add_shape(
        ctx,
        "decision",
        BBox(cx - dw / 2, y, cx + dw / 2, y + dh),
        node.test,
        _diamond(cx, y, dw, dh),
    )

    true_label, false_label = _labels(ctx, node)
    body = _measure_block(ctx, node.body)
    body_top = y + dh + BODY_GAP
    body_bottom = _layout_block(ctx, node.body, cx, body_top)

    lane_l = min(cx - dw / 2, cx + body.x0) - LANE_PAD
    lane_r = max(cx + dw / 2, cx + body.x1) + LANE_PAD

    # Condition -> body.
    ctx.connectors.append(
        Connector(
            [(cx, y + dh), (cx, body_top)],
            label=true_label,
            label_pos=(cx + 22, y + dh + 16),
        )
    )
    # End of body -> back up the left side to the decision.
    back_y = body_bottom + BACK_DROP
    ctx.connectors.append(
        Connector(
            [
                (cx, body_bottom),
                (cx, back_y),
                (lane_l, back_y),
                (lane_l, cy),
                (cx - dw / 2, cy),
            ]
        )
    )
    # Right side of the decision -> down towards the rest of the chart.
    exit_y = body_bottom + EXIT_DROP
    ctx.connectors.append(
        Connector(
            [(cx + dw / 2, cy), (lane_r, cy), (lane_r, exit_y), (cx, exit_y)],
            arrow=False,
            label=false_label,
            label_pos=(cx + dw / 2 + 22, cy - 14),
        )
    )
    return exit_y


def _terminator(ctx: _Ctx, text: str, cx: float, y: float) -> float:
    width, height = _box_size(ctx, text, "terminator", TERM_MIN_H, TERM_PAD)
    _add_shape(ctx, "terminator", BBox(cx - width / 2, y, cx + width / 2, y + height), text)
    return y + height


# --- entry point ----------------------------------------------------------


def layout(flowchart: Flowchart, theme: Theme, language: Language, fonts: FontSet) -> Scene:
    """Compute the scene for a parsed flowchart."""
    ctx = _Ctx(fonts=fonts, language=language)

    current = _terminator(ctx, language.start, 0.0, 0.0)
    if flowchart.block.nodes:
        ctx.connectors.append(Connector([(0.0, current), (0.0, current + V_GAP)]))
        current += V_GAP
        current = _layout_block(ctx, flowchart.block, 0.0, current)
    ctx.connectors.append(Connector([(0.0, current), (0.0, current + V_GAP)]))
    current += V_GAP
    _terminator(ctx, language.end, 0.0, current)

    return Scene(
        shapes=ctx.shapes,
        connectors=ctx.connectors,
        circles=ctx.circles,
        title=flowchart.metadata.title,
    )
