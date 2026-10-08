"""Tests for the layout engine: geometry of the produced scenes."""

import pytest

from flowcharts.fonts import FontSet
from flowcharts.layout import CIRCLE_R, usable_width
from flowcharts.themes import get_theme

from helpers import (
    EPS,
    assert_arrow_tips_land_on_shapes,
    assert_shapes_do_not_overlap,
    close,
    ends_at,
    example_sources,
    read_example,
    scene_for,
    shape_with_text,
    shapes,
    starts_at,
    with_meta,
)

SOURCES = [
    read_example(path.name) for path in example_sources()
] + [
    with_meta('"Step 1"\n"Step 2"\n"Step 3"'),
    with_meta('"a"\nif "C":\n    "T"\n"b"'),
    with_meta('"a"\nif "C":\n    "T"\nelse:\n    "E"\n"b"'),
    with_meta(
        'if "C1":\n    "T1"\nelif "C2":\n    "T2"\nelif "C3":\n    "T3"\nelse:\n    "E"'
    ),
    with_meta('while "W":\n    "Body"'),
    with_meta('while not "W":\n    "Body"'),
    with_meta('"a"\nwhile "W":\n    if "C":\n        "T"\n    else:\n        "E"\n"b"'),
    with_meta('if "C":\n    while "W":\n        "X"\n"after"'),
    with_meta('if "C":\n    while "W":\n        "X"\nelse:\n    "E"'),
    with_meta('while "W":\n    while "V":\n        "Deep"'),
    with_meta('input("in")\nprint("out")'),
    with_meta('"only"'),
    with_meta(""),
]


@pytest.mark.parametrize("source", SOURCES, ids=range(len(SOURCES)))
def test_shapes_never_overlap(source):
    assert_shapes_do_not_overlap(scene_for(source))


@pytest.mark.parametrize("source", SOURCES, ids=range(len(SOURCES)))
def test_arrow_tips_land_on_shapes_or_circles(source):
    assert_arrow_tips_land_on_shapes(scene_for(source))


@pytest.mark.parametrize("source", SOURCES, ids=range(len(SOURCES)))
def test_chart_is_wrapped_in_start_and_end_terminators(source):
    scene = scene_for(source)
    terminators = shapes(scene, "terminator")
    assert terminators[0].text in {"Start", "Inizio"}
    assert terminators[1].text in {"End", "Fine"}
    assert terminators[0].bbox.y0 == 0
    assert terminators[1].bbox.y1 > terminators[0].bbox.y1


def test_sequence_flows_straight_down_the_axis():
    scene = scene_for(with_meta('"a"\n"b"'))
    first = shape_with_text(scene, "a")
    second = shape_with_text(scene, "b")
    connectors = [
        c
        for c in scene.connectors
        if starts_at(c, first.bbox.cx, first.bbox.y1)
        and ends_at(c, second.bbox.cx, second.bbox.y0)
        and c.arrow
    ]
    assert len(connectors) == 1
    assert connectors[0].points == [
        (first.bbox.cx, first.bbox.y1),
        (second.bbox.cx, second.bbox.y0),
    ]


def test_if_branches_leave_from_the_right_and_left():
    scene = scene_for(with_meta('"a"\nif "C":\n    "T"\nelse:\n    "E"\n"b"'))
    diamond = shape_with_text(scene, "C")
    yes_body = shape_with_text(scene, "T")
    no_body = shape_with_text(scene, "E")

    assert yes_body.bbox.x0 > diamond.bbox.x1
    assert no_body.bbox.x1 < diamond.bbox.x0
    assert yes_body.bbox.x0 - diamond.bbox.x1 >= 30  # clearance for the lane

    cy = diamond.bbox.cy
    right = [c for c in scene.connectors if starts_at(c, diamond.bbox.x1, cy)]
    left = [c for c in scene.connectors if starts_at(c, diamond.bbox.x0, cy)]
    assert right and right[0].label == "Yes"
    assert left and left[0].label == "No"
    assert right[0].arrow and left[0].arrow


def test_if_branches_meet_a_connection_circle_and_flow_on():
    scene = scene_for(with_meta('"a"\nif "C":\n    "T"\nelse:\n    "E"\n"b"'))
    diamond = shape_with_text(scene, "C")
    yes_body = shape_with_text(scene, "T")
    no_body = shape_with_text(scene, "E")
    after = shape_with_text(scene, "b")

    circles = scene.circles
    assert len(circles) == 1
    circle = circles[0]
    assert circle.r == CIRCLE_R

    # The circle sits below both branches.
    assert circle.cy > yes_body.bbox.y1
    assert circle.cy > no_body.bbox.y1
    assert close(circle.cx, diamond.bbox.cx)

    # Branch bottoms connect to the sides of the circle.
    right_in = [c for c in scene.connectors if ends_at(c, circle.cx + circle.r, circle.cy)]
    left_in = [c for c in scene.connectors if ends_at(c, circle.cx - circle.r, circle.cy)]
    assert right_in and right_in[0].arrow
    assert left_in and left_in[0].arrow
    assert starts_at(right_in[0], yes_body.bbox.cx, yes_body.bbox.y1)
    assert starts_at(left_in[0], no_body.bbox.cx, no_body.bbox.y1)

    # The bottom of the circle continues to the rest of the flowchart.
    bottom = [c for c in scene.connectors if starts_at(c, circle.cx, circle.cy + circle.r)]
    assert bottom and bottom[0].arrow
    assert ends_at(bottom[0], after.bbox.cx, after.bbox.y0)


def test_if_without_else_sends_the_no_branch_around_to_the_circle():
    scene = scene_for(with_meta('"a"\nif "C":\n    "T"\n"b"'))
    diamond = shape_with_text(scene, "C")
    circle = scene.circles[0]

    lane = [
        c
        for c in scene.connectors
        if ends_at(c, circle.cx - circle.r, circle.cy) and c.label == "No"
    ]
    assert lane and lane[0].arrow
    connector = lane[0]
    assert starts_at(connector, diamond.bbox.x0, diamond.bbox.cy)
    assert any(x < diamond.bbox.x0 for x, _ in connector.points)


def test_elif_is_a_nested_decision_with_its_own_circle():
    scene = scene_for(read_example("02_if.py"))
    outer_decision = shape_with_text(scene, "Condition 1")
    inner_decision = shape_with_text(scene, "Condition 2")
    assert inner_decision.bbox.x1 < outer_decision.bbox.x0

    circles = scene.circles
    assert len(circles) == 2
    inner = min(circles, key=lambda c: c.cx)
    outer = max(circles, key=lambda c: c.cx)
    assert inner.cy < outer.cy

    # The nested decision's circle feeds the outer circle's left side.
    nested_to_outer = [
        c
        for c in scene.connectors
        if starts_at(c, inner.cx, inner.cy + inner.r)
        and ends_at(c, outer.cx - outer.r, outer.cy)
    ]
    assert nested_to_outer and nested_to_outer[0].arrow

    # The outer circle continues to the rest of the chart.
    after = shape_with_text(scene, "Step 3")
    continuation = [
        c
        for c in scene.connectors
        if starts_at(c, outer.cx, outer.cy + outer.r)
        and ends_at(c, after.bbox.cx, after.bbox.y0)
    ]
    assert continuation and continuation[0].arrow


def test_long_elif_chain_links_circles():
    scene = scene_for(
        'if "C1":\n    "T1"\nelif "C2":\n    "T2"\nelif "C3":\n    "T3"\nelse:\n    "E"'
    )
    circles = scene.circles
    assert len(circles) == 3
    links = 0
    for connector in scene.connectors:
        for source in circles:
            if starts_at(connector, source.cx, source.cy + source.r):
                for target in circles:
                    if ends_at(connector, target.cx - target.r, target.cy):
                        links += 1
    assert links == 2  # inner -> middle -> outer


def test_while_body_is_below_the_decision_with_a_bottom_arrow():
    scene = scene_for(with_meta('"a"\nwhile "W":\n    "Body"\n"b"'))
    diamond = shape_with_text(scene, "W")
    body = shape_with_text(scene, "Body")
    assert body.bbox.y0 > diamond.bbox.y1

    entry = [
        c for c in scene.connectors if starts_at(c, diamond.bbox.cx, diamond.bbox.y1)
    ]
    assert entry and entry[0].arrow
    assert entry[0].label == "Yes"
    assert ends_at(entry[0], body.bbox.cx, body.bbox.y0)


def test_while_body_loops_back_up_the_left_side():
    scene = scene_for(with_meta('"a"\nwhile "W":\n    "Body"\n"b"'))
    diamond = shape_with_text(scene, "W")
    body = shape_with_text(scene, "Body")
    cy = diamond.bbox.cy

    back = [
        c
        for c in scene.connectors
        if c.arrow and ends_at(c, diamond.bbox.x0, cy)
    ]
    assert back, "no back edge into the left vertex of the decision"
    points = back[0].points
    # Runs up the left side of both the decision and the body.
    assert any(x < diamond.bbox.x0 and x < body.bbox.x0 for x, _ in points)
    assert points[-3][1] > points[-2][1]  # arrives up the left lane
    assert starts_at(back[0], body.bbox.cx, body.bbox.y1)


def test_while_exits_from_the_right_side_towards_the_rest():
    scene = scene_for(with_meta('"a"\nwhile "W":\n    "Body"\n"b"'))
    diamond = shape_with_text(scene, "W")
    body = shape_with_text(scene, "Body")
    after = shape_with_text(scene, "b")
    cy = diamond.bbox.cy

    exits = [c for c in scene.connectors if starts_at(c, diamond.bbox.x1, cy)]
    assert exits, "no exit from the right vertex"
    exit_connector = exits[0]
    assert exit_connector.label == "No"
    assert not exit_connector.arrow  # continues into the next connector
    points = exit_connector.points
    assert any(x > diamond.bbox.x1 for x, _ in points)  # goes right...
    assert points[-1][1] > body.bbox.y1  # ...down past the body...
    assert close(points[-1][0], diamond.bbox.cx)  # ...and back to the axis

    continuation = [
        c
        for c in scene.connectors
        if c.arrow
        and starts_at(c, points[-1][0], points[-1][1])
        and ends_at(c, after.bbox.cx, after.bbox.y0)
    ]
    assert continuation


def test_negated_conditions_swap_the_yes_no_labels():
    if_scene = scene_for('if not "C":\n    "T"\nelse:\n    "E"')
    diamond = shape_with_text(if_scene, "C")
    right = [
        c
        for c in if_scene.connectors
        if starts_at(c, diamond.bbox.x1, diamond.bbox.cy)
    ]
    left = [
        c
        for c in if_scene.connectors
        if starts_at(c, diamond.bbox.x0, diamond.bbox.cy)
    ]
    assert right[0].label == "No"
    assert left[0].label == "Yes"

    while_scene = scene_for('while not "W":\n    "Body"')
    w_diamond = shape_with_text(while_scene, "W")
    entry = [
        c
        for c in while_scene.connectors
        if starts_at(c, w_diamond.bbox.cx, w_diamond.bbox.y1)
    ]
    exit_connector = [
        c
        for c in while_scene.connectors
        if starts_at(c, w_diamond.bbox.x1, w_diamond.bbox.cy)
    ]
    assert entry[0].label == "No"  # body runs when the condition is false
    assert exit_connector[0].label == "Yes"


def test_input_and_output_parallelograms_lean_opposite_ways():
    scene = scene_for('input("in")\nprint("out")')
    input_shape = shapes(scene, "input")[0]
    output_shape = shapes(scene, "output")[0]
    assert input_shape.points is not None and output_shape.points is not None

    def lean(shape):
        return shape.points[0][0] - shape.points[3][0]

    input_lean = lean(input_shape)
    output_lean = lean(output_shape)
    assert input_lean > 0
    assert output_lean < 0
    assert input_lean == pytest.approx(-output_lean)


def test_title_is_carried_into_the_scene():
    scene = scene_for(read_example("02_if.py"))
    assert scene.title == "Example 02 - If"
    assert scene_for(with_meta('"a"')).title is None


def test_connection_circle_is_small():
    scene = scene_for(read_example("02_if.py"))
    node_height = min(shape.bbox.height for shape in scene.shapes)
    for circle in scene.circles:
        assert circle.r <= 12
        assert circle.r * 4 < node_height


@pytest.mark.parametrize("source", SOURCES, ids=range(len(SOURCES)))
def test_wrapped_text_fits_inside_shapes(source):
    fonts = FontSet(get_theme("default"))
    scene = scene_for(source)
    for shape in scene.shapes:
        for line in fonts.wrap(
            shape.text, usable_width(shape.kind), fonts.body, fonts.body_size
        ):
            assert fonts.width(fonts.body, line) <= usable_width(shape.kind) + EPS


def test_very_long_words_are_hard_split():
    scene = scene_for(with_meta('"' + "x" * 300 + '"'))
    fonts = FontSet(get_theme("default"))
    shape = scene.shapes[1]
    lines = fonts.wrap(shape.text, usable_width(shape.kind), fonts.body, fonts.body_size)
    assert len(lines) > 1
    for line in lines:
        assert fonts.width(fonts.body, line) <= usable_width(shape.kind) + EPS


def test_multiline_text_is_preserved():
    scene = scene_for(with_meta('"first\\nsecond"'))
    shape = scene.shapes[1]
    fonts = FontSet(get_theme("default"))
    lines = fonts.wrap(shape.text, usable_width(shape.kind), fonts.body, fonts.body_size)
    assert lines == ["first", "second"]
