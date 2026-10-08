"""Tests for the pseudocode parser."""

import pytest

from flowcharts import (
    If,
    Input,
    Output,
    ParseError,
    Process,
    UnsupportedSyntaxError,
    While,
    parse,
)

# The first string of pseudocode is always the metadata header.
META_HEADER = '"""\n"""\n'


def texts(block) -> list[str]:
    return [node.text for node in block.nodes]


def test_string_statements_become_processes():
    flowchart = parse(META_HEADER + '"Step 1"\n"Step 2"\n"Step 3"')
    assert texts(flowchart.block) == ["Step 1", "Step 2", "Step 3"]
    assert all(isinstance(node, Process) for node in flowchart.block.nodes)


def test_input_and_output_calls():
    flowchart = parse('input("Prompt")\nprint("Result")')
    assert isinstance(flowchart.block.nodes[0], Input)
    assert isinstance(flowchart.block.nodes[1], Output)
    assert texts(flowchart.block) == ["Prompt", "Result"]


def test_input_without_literal_argument():
    flowchart = parse("input(variable)")
    assert flowchart.block.nodes[0].text == "variable"


def test_print_without_arguments():
    flowchart = parse("print()")
    assert isinstance(flowchart.block.nodes[0], Output)
    assert flowchart.block.nodes[0].text == ""


def test_generic_statements_become_processes_with_source_text():
    flowchart = parse("x = 1\nx += 2\nfoo(3)")
    assert texts(flowchart.block) == ["x = 1", "x += 2", "foo(3)"]


def test_if_else_structure():
    flowchart = parse('if "C":\n    "T"\nelse:\n    "E"')
    node = flowchart.block.nodes[0]
    assert isinstance(node, If)
    assert node.test == "C"
    assert node.negated is False
    assert texts(node.body) == ["T"]
    assert texts(node.orelse) == ["E"]
    assert node.nested is None


def test_string_condition_has_quotes_removed():
    flowchart = parse('if "Condition 1":\n    "T"')
    assert flowchart.block.nodes[0].test == "Condition 1"


def test_negated_condition_is_stripped_and_flagged():
    flowchart = parse('if not "Condition 2":\n    "T"')
    node = flowchart.block.nodes[0]
    assert node.test == "Condition 2"
    assert node.negated is True


def test_double_negation():
    flowchart = parse('if not not "C":\n    "T"')
    node = flowchart.block.nodes[0]
    assert node.test == "C"
    assert node.negated is False


def test_non_literal_condition_uses_source_text():
    flowchart = parse("if x > 1:\n    pass")
    assert flowchart.block.nodes[0].test == "x > 1"


def test_elif_becomes_nested_if():
    flowchart = parse(
        'if "C1":\n    "T1"\nelif not "C2":\n    "T2"\nelse:\n    "E"'
    )
    outer = flowchart.block.nodes[0]
    assert isinstance(outer, If)
    assert outer.test == "C1"
    inner = outer.nested
    assert isinstance(inner, If)
    assert inner.test == "C2"
    assert inner.negated is True
    assert texts(inner.body) == ["T2"]
    assert texts(inner.orelse) == ["E"]
    assert inner.nested is None


def test_elif_chain_without_else():
    flowchart = parse('if "C1":\n    "T1"\nelif "C2":\n    "T2"')
    outer = flowchart.block.nodes[0]
    inner = outer.nested
    assert isinstance(inner, If)
    assert inner.orelse.nodes == []
    assert inner.nested is None


def test_while_structure():
    flowchart = parse('while "W":\n    "Body"')
    node = flowchart.block.nodes[0]
    assert isinstance(node, While)
    assert node.test == "W"
    assert node.negated is False
    assert texts(node.body) == ["Body"]


def test_negated_while():
    flowchart = parse('while not "W":\n    "Body"')
    node = flowchart.block.nodes[0]
    assert node.test == "W"
    assert node.negated is True


def test_nested_blocks():
    flowchart = parse('if "C":\n    while "W":\n        "Body"\n    "After"')
    node = flowchart.block.nodes[0]
    assert isinstance(node.body.nodes[0], While)
    assert [type(n).__name__ for n in node.body.nodes] == ["While", "Process"]


def test_pass_statement():
    flowchart = parse("if 'C':\n    pass\nelse:\n    pass")
    node = flowchart.block.nodes[0]
    assert texts(node.body) == ["pass"]
    assert texts(node.orelse) == ["pass"]


def test_while_else_is_rejected():
    with pytest.raises(UnsupportedSyntaxError):
        parse('while "W":\n    "B"\nelse:\n    "E"')


@pytest.mark.parametrize(
    "source,keyword",
    [
        ('for i in x:\n    "a"', "for"),
        ('with open("f"):\n    "a"', "with"),
        ('def f():\n    "a"', "def"),
        ('class C:\n    pass', "class"),
        ('import os', "import"),
        ('"a"\nassert x', "assert"),
        ('"a"\nraise ValueError()', "raise"),
        ('"a"\ndel x', "delete"),
    ],
)
def test_unsupported_syntax_is_reported_with_line_number(source, keyword):
    with pytest.raises(UnsupportedSyntaxError) as excinfo:
        parse(source)
    assert keyword in str(excinfo.value)
    assert "line" in str(excinfo.value)


def test_unsupported_syntax_inside_block_reports_its_line():
    with pytest.raises(UnsupportedSyntaxError) as excinfo:
        parse('"ok"\nif "C":\n    for i in x:\n        "a"')
    assert excinfo.value.lineno == 3


def test_syntax_error_raises_parse_error():
    with pytest.raises(ParseError):
        parse("if broken(")


def test_metadata_reaches_flowchart():
    flowchart = parse('"""\nTitle: T\nTheme: dracula\nLanguage: it\n"""\n"A"')
    assert flowchart.metadata.title == "T"
    assert flowchart.metadata.theme == "dracula"
    assert flowchart.metadata.language == "it"
    assert texts(flowchart.block) == ["A"]
