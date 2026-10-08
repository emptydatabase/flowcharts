"""Shared helpers for the test suite."""

from __future__ import annotations

import math
import pathlib

import flowcharts
from flowcharts import languages, parser, themes
from flowcharts.fonts import FontSet
from flowcharts.layout import BBox, Scene, layout

EXAMPLES_DIR = pathlib.Path(__file__).resolve().parents[1] / "examples" / "pseudocode"
EPS = 1e-6

# The first string of pseudocode is always the metadata header, so test
# sources that need no metadata start with an empty one.
META_HEADER = '"""\n"""\n'


def with_meta(body: str) -> str:
    """Prefix ``body`` with an empty metadata header."""
    return META_HEADER + body


def read_example(name: str) -> str:
    return (EXAMPLES_DIR / name).read_text(encoding="utf-8")


def scene_for(
    source: str, theme: str | None = None, language: str | None = None
) -> Scene:
    """Parse and lay out ``source`` the same way :func:`flowcharts.render` does."""
    flowchart = parser.parse(source)
    resolved_theme = themes.get_theme(
        theme or flowchart.metadata.theme or "default"
    )
    resolved_language = languages.get_language(
        language or flowchart.metadata.language or "en"
    )
    return layout(flowchart, resolved_theme, resolved_language, FontSet(resolved_theme))


def shapes(scene: Scene, kind: str):
    return [shape for shape in scene.shapes if shape.kind == kind]


def shape_with_text(scene: Scene, text: str):
    matches = [shape for shape in scene.shapes if shape.text == text]
    assert matches, f"no shape with text {text!r}"
    return matches[0]


def circles(scene: Scene):
    return list(scene.circles)


def close(a: float, b: float, tol: float = 0.5) -> bool:
    return abs(a - b) <= tol


def point_close(a: tuple[float, float], b: tuple[float, float], tol: float = 0.5) -> bool:
    return close(a[0], b[0], tol) and close(a[1], b[1], tol)


def starts_at(connector, x: float, y: float, tol: float = 0.5) -> bool:
    return point_close(connector.points[0], (x, y), tol)


def ends_at(connector, x: float, y: float, tol: float = 0.5) -> bool:
    return point_close(connector.points[-1], (x, y), tol)


def connector_between_points(connector, x: float, y: float, tol: float = 0.5):
    return any(point_close(point, (x, y), tol) for point in connector.points)


def boxes_disjoint(a: BBox, b: BBox) -> bool:
    return (
        a.x1 <= b.x0 + EPS
        or b.x1 <= a.x0 + EPS
        or a.y1 <= b.y0 + EPS
        or b.y1 <= a.y0 + EPS
    )


def assert_shapes_do_not_overlap(scene: Scene) -> None:
    boxes = [shape.bbox for shape in scene.shapes]
    for i, first in enumerate(boxes):
        for second in boxes[i + 1 :]:
            assert boxes_disjoint(first, second), f"shapes overlap: {first} vs {second}"


def point_on_shape_boundary(scene: Scene, x: float, y: float, tol: float = 0.5) -> bool:
    for shape in scene.shapes:
        box = shape.bbox
        if not (box.x0 - tol <= x <= box.x1 + tol and box.y0 - tol <= y <= box.y1 + tol):
            continue
        if (
            close(x, box.x0, tol)
            or close(x, box.x1, tol)
            or close(y, box.y0, tol)
            or close(y, box.y1, tol)
        ):
            return True
    return False


def point_on_circle_edge(scene: Scene, x: float, y: float, tol: float = 0.5) -> bool:
    for circle in scene.circles:
        distance = math.hypot(x - circle.cx, y - circle.cy)
        if abs(distance - circle.r) <= tol:
            return True
    return False


def assert_arrow_tips_land_on_shapes(scene: Scene) -> None:
    for connector in scene.connectors:
        if not connector.arrow:
            continue
        x, y = connector.points[-1]
        assert point_on_shape_boundary(scene, x, y) or point_on_circle_edge(
            scene, x, y
        ), f"arrow tip {x, y} lands nowhere near a shape or circle"


def example_sources() -> list[pathlib.Path]:
    return sorted(EXAMPLES_DIR.glob("*.py"))
