"""Tests for the metadata header."""

import pytest

from flowcharts import Metadata, MetadataError, parse, parse_metadata


def test_no_metadata_gives_defaults():
    assert parse_metadata(None) == Metadata()
    assert parse_metadata("") == Metadata()
    assert parse_metadata("\n  \n") == Metadata()


def test_bare_line_sets_title():
    meta = parse_metadata("Example 03 - Loop")
    assert meta.title == "Example 03 - Loop"
    assert meta.theme is None
    assert meta.language is None


def test_title_key_is_optional_but_allowed():
    assert parse_metadata("Title: Hello").title == "Hello"
    assert parse_metadata("Hello").title == "Hello"


def test_all_keys():
    meta = parse_metadata("Title: My Chart\nTheme: dracula\nLanguage: it")
    assert meta == Metadata(title="My Chart", theme="dracula", language="it")


def test_keys_are_case_insensitive():
    meta = parse_metadata("title: T\nTHEME: dracula\nlanguage: en")
    assert meta == Metadata(title="T", theme="dracula", language="en")


def test_bare_title_mixed_with_keys():
    meta = parse_metadata("Example 03 - Loop\nTheme: solarized\nLanguage: it")
    assert meta.title == "Example 03 - Loop"
    assert meta.theme == "solarized"
    assert meta.language == "it"


def test_unknown_keys_are_ignored():
    meta = parse_metadata("Author: Somebody\nTheme: dracula")
    assert meta.theme == "dracula"
    assert meta.title is None


def test_key_without_value_raises():
    with pytest.raises(MetadataError):
        parse_metadata("Theme:")


def test_value_is_stripped():
    assert parse_metadata("  Title:   spaced out  ").title == "spaced out"


def test_docstring_of_pseudocode_is_metadata_not_a_step():
    flowchart = parse('"""My Title"""\n"Step"')
    assert flowchart.metadata.title == "My Title"
    assert [node.text for node in flowchart.block.nodes] == ["Step"]


def test_leading_bare_string_is_consumed_even_without_keys():
    flowchart = parse('"just a title"\n"Step 1"')
    assert flowchart.metadata.title == "just a title"
    assert [node.text for node in flowchart.block.nodes] == ["Step 1"]
