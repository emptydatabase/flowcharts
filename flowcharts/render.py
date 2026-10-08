"""Draw a :class:`~flowcharts.layout.Scene` onto a Pillow image."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

from . import layout as lay
from .fonts import FontSet
from .languages import Language, coerce_language, get_language
from .model import Flowchart
from .parser import parse
from .themes import Theme, coerce_theme, get_theme

MARGIN = 40
TITLE_GAP = 14
ARROW_LEN = 11.0
ARROW_HALF = 6.0


def render(
    pseudocode: str,
    *,
    theme: Theme | str | None = None,
    language: Language | str | None = None,
) -> Image.Image:
    """Render pseudocode and return a Pillow image."""
    return render_flowchart(parse(pseudocode), theme=theme, language=language)


def render_file(
    path: str | Path,
    *,
    theme: Theme | str | None = None,
    language: Language | str | None = None,
) -> Image.Image:
    """Read pseudocode from ``path`` and return a Pillow image."""
    return render(Path(path).read_text(encoding="utf-8"), theme=theme, language=language)


def render_flowchart(
    flowchart: Flowchart,
    *,
    theme: Theme | str | None = None,
    language: Language | str | None = None,
) -> Image.Image:
    """Render an already parsed flowchart."""
    resolved_theme = (
        coerce_theme(theme)
        or (get_theme(flowchart.metadata.theme) if flowchart.metadata.theme else None)
        or get_theme("default")
    )
    resolved_language = (
        coerce_language(language)
        or (
            get_language(flowchart.metadata.language)
            if flowchart.metadata.language
            else None
        )
        or get_language("en")
    )
    fonts = FontSet(resolved_theme)
    scene = lay.layout(flowchart, resolved_theme, resolved_language, fonts)
    return _draw(scene, resolved_theme, fonts)


# --- drawing --------------------------------------------------------------


def _text_box(font, text: str) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = font.getbbox(text)
    return float(x0), float(y0), float(x1), float(y1)


def _centered_box(font, text: str, cx: float, cy: float) -> lay.BBox:
    x0, y0, x1, y1 = _text_box(font, text)
    return lay.BBox(
        cx - (x0 + x1) / 2,
        cy - (y0 + y1) / 2,
        cx - (x0 + x1) / 2 + (x1 - x0),
        cy - (y0 + y1) / 2 + (y1 - y0),
    )


def _draw_centered(
    draw: ImageDraw.ImageDraw, font, text: str, cx: float, cy: float, fill: str
) -> None:
    box = _text_box(font, text)
    draw.text(
        (cx - (box[0] + box[2]) / 2, cy - (box[1] + box[3]) / 2),
        text,
        font=font,
        fill=fill,
    )


def _union(boxes: list[lay.BBox]) -> lay.BBox:
    box = boxes[0]
    for other in boxes[1:]:
        box = box.union(other)
    return box


def _arrow_points(
    tip: tuple[float, float], prev: tuple[float, float]
) -> list[tuple[float, float]]:
    dx, dy = tip[0] - prev[0], tip[1] - prev[1]
    norm = math.hypot(dx, dy) or 1.0
    ux, uy = dx / norm, dy / norm
    px, py = -uy, ux
    base = (tip[0] - ux * ARROW_LEN, tip[1] - uy * ARROW_LEN)
    return [
        tip,
        (base[0] + px * ARROW_HALF, base[1] + py * ARROW_HALF),
        (base[0] - px * ARROW_HALF, base[1] - py * ARROW_HALF),
    ]


def _draw(scene: lay.Scene, theme: Theme, fonts: FontSet) -> Image.Image:
    line_width = max(1, int(round(theme.line_width)))

    boxes = (
        [scene.geometry_bbox()]
        if scene.shapes or scene.connectors or scene.circles
        else []
    )
    for connector in scene.connectors:
        if connector.label and connector.label_pos:
            cx, cy = connector.label_pos
            boxes.append(_centered_box(fonts.label, connector.label, cx, cy))

    title_box = None
    if scene.title:
        x0, y0, x1, y1 = _text_box(fonts.title, scene.title)
        title_box = (x1 - x0, y1 - y0)

    chart = _union(boxes) if boxes else lay.BBox(0.0, 0.0, 0.0, 0.0)
    content_w = chart.width
    if title_box:
        content_w = max(content_w, title_box[0])
    title_h = (title_box[1] + TITLE_GAP) if title_box else 0.0

    width = int(math.ceil(content_w + 2 * MARGIN))
    height = int(math.ceil(chart.height + 2 * MARGIN + title_h))
    offset_x = MARGIN + (content_w - chart.width) / 2 - chart.x0
    offset_y = MARGIN + title_h - chart.y0

    image = Image.new("RGB", (width, height), theme.background)
    draw = ImageDraw.Draw(image)

    def tx(x: float) -> float:
        return x + offset_x

    def ty(y: float) -> float:
        return y + offset_y

    # 1. Connectors (underneath the shapes).
    for connector in scene.connectors:
        points = [(tx(x), ty(y)) for x, y in connector.points]
        if len(points) >= 2:
            draw.line(points, fill=theme.arrow, width=line_width, joint="curve")

    # 2. Shapes.
    for shape in scene.shapes:
        box = lay.BBox(tx(shape.bbox.x0), ty(shape.bbox.y0), tx(shape.bbox.x1), ty(shape.bbox.y1))
        if shape.points is not None:
            points = [(tx(x), ty(y)) for x, y in shape.points]
            draw.polygon(points, fill=theme.fill, outline=theme.outline)
            closed = points + [points[0]]
            draw.line(closed, fill=theme.outline, width=line_width, joint="curve")
        elif shape.kind == "terminator":
            draw.rounded_rectangle(
                ((box.x0, box.y0), (box.x1, box.y1)),
                radius=box.height / 2,
                fill=theme.terminator_fill,
                outline=theme.outline,
                width=line_width,
            )
        else:
            draw.rectangle(
                ((box.x0, box.y0), (box.x1, box.y1)),
                fill=theme.fill,
                outline=theme.outline,
                width=line_width,
            )

    # 3. Connection circles.
    for circle in scene.circles:
        cx, cy, r = tx(circle.cx), ty(circle.cy), circle.r
        draw.ellipse(
            (cx - r, cy - r, cx + r, cy + r),
            fill=theme.background,
            outline=theme.arrow,
            width=line_width,
        )

    # 4. Arrowheads (on top of everything they point at).
    for connector in scene.connectors:
        if not connector.arrow or len(connector.points) < 2:
            continue
        tip = connector.points[-1]
        prev = connector.points[-2]
        tip_xy = (tx(tip[0]), ty(tip[1]))
        prev_xy = (tx(prev[0]), ty(prev[1]))
        draw.polygon(_arrow_points(tip_xy, prev_xy), fill=theme.arrow)

    # 5. Text inside shapes.
    for shape in scene.shapes:
        font, size = fonts.body, fonts.body_size
        lines = fonts.wrap(shape.text, lay.usable_width(shape.kind), font, size)
        line_h = fonts.line_height(size)
        cx, cy = tx(shape.bbox.cx), ty(shape.bbox.cy)
        total = len(lines) * line_h
        for index, line in enumerate(lines):
            _draw_centered(draw, font, line, cx, cy - total / 2 + (index + 0.5) * line_h, theme.text)

    # 6. Decision labels (yes/no).
    for connector in scene.connectors:
        if connector.label and connector.label_pos:
            cx, cy = connector.label_pos
            _draw_centered(draw, fonts.label, connector.label, tx(cx), ty(cy), theme.label)

    # 7. Title.
    if scene.title:
        _draw_centered(draw, fonts.title, scene.title, width / 2, MARGIN + title_box[1] / 2, theme.title)

    return image
