"""Tests for the Pillow rendering step and the public API."""

from pathlib import Path

import pytest
from PIL import Image, ImageColor

import flowcharts
from flowcharts import (
    Language,
    LanguageError,
    ParseError,
    Theme,
    ThemeError,
    UnsupportedSyntaxError,
    register_language,
    register_theme,
    render,
    render_file,
)
from flowcharts.themes import get_theme

from helpers import scene_for, shapes

ALL_CORNERS = [(0, 0), (-1, 0), (0, -1), (-1, -1)]


def background_rgb(theme_name: str) -> tuple[int, int, int]:
    return ImageColor.getrgb(get_theme(theme_name).background)


def corners_are_background(image: Image.Image, expected) -> bool:
    width, height = image.size
    return all(
        image.getpixel((x if x >= 0 else width + x, y if y >= 0 else height + y))
        == expected
        for x, y in ALL_CORNERS
    )


def test_returns_an_rgb_pillow_image():
    image = render('"Step 1"')
    assert isinstance(image, Image.Image)
    assert image.mode == "RGB"
    assert image.width > 100
    assert image.height > 100


@pytest.mark.parametrize("theme", ["default", "dracula", "solarized"])
def test_builtin_themes_set_the_background(theme):
    image = render('"Step 1"', theme=theme)
    assert corners_are_background(image, background_rgb(theme))


def test_metadata_theme_is_used_when_no_override():
    image = render('"""\nTheme: dracula\n"""\n"Step"')
    assert corners_are_background(image, background_rgb("dracula"))


def test_explicit_arguments_override_metadata():
    image = render('"""\nTheme: dracula\n"""\n"Step"', theme="solarized")
    assert corners_are_background(image, background_rgb("solarized"))


def test_title_is_drawn_above_the_chart():
    with_title = render('"""\nTitle: A Very Special Title\n"""\n"Step"')
    without_title = render('"Step"')
    assert with_title.height > without_title.height

    background = with_title.getpixel((0, 0))
    band = [
        with_title.getpixel((x, y))
        for y in range(0, 60)
        for x in range(0, with_title.width, 2)
    ]
    assert any(pixel != background for pixel in band)


def test_language_changes_the_drawn_strings():
    english = render('"Step"')
    italian = render('"Step"', language="it")
    assert english.size == italian.size
    assert english.tobytes() != italian.tobytes()


def test_language_selects_start_and_end_strings():
    scene = scene_for('"Step"', language="it")
    assert [shape.text for shape in shapes(scene, "terminator")] == ["Inizio", "Fine"]


def test_metadata_language_is_used():
    scene = scene_for('"""\nLanguage: it\n"""\n"Step"')
    assert [shape.text for shape in shapes(scene, "terminator")] == ["Inizio", "Fine"]


def test_unknown_theme_raises():
    with pytest.raises(ThemeError):
        render('"Step"', theme="no-such-theme")
    with pytest.raises(ThemeError):
        render('"""\nTheme: no-such-theme\n"""\n"Step"')


def test_unknown_language_raises():
    with pytest.raises(LanguageError):
        render('"Step"', language="no-such-language")
    with pytest.raises(LanguageError):
        render('"""\nLanguage: no-such-language\n"""\n"Step"')


def test_invalid_pseudocode_raises_parse_error():
    with pytest.raises(ParseError):
        render("if broken(")


def test_unsupported_syntax_raises():
    with pytest.raises(UnsupportedSyntaxError):
        render("for i in items:\n    process(i)")


def test_custom_theme_can_be_registered_and_used():
    theme = Theme(
        name="unit-test-theme",
        background="#010203",
        fill="#040506",
        terminator_fill="#070809",
        outline="#0a0b0c",
        text="#0d0e0f",
        arrow="#101112",
        label="#131415",
        title="#161718",
    )
    register_theme(theme, replace=True)
    image = render('"Step"', theme="unit-test-theme")
    assert corners_are_background(image, (1, 2, 3))


def test_custom_language_can_be_registered_and_used():
    language = Language(name="unit-test-lang", start="GO", end="STOP", yes="Y", no="N")
    register_language(language, replace=True)
    scene = scene_for('"Step"', language="unit-test-lang")
    assert [shape.text for shape in shapes(scene, "terminator")] == ["GO", "STOP"]


def test_render_file_reads_the_file(tmp_path: Path):
    source = tmp_path / "chart.py"
    source.write_text('"Step 1"\n"Step 2"', encoding="utf-8")
    from_file = render_file(source)
    from_string = render(source.read_text(encoding="utf-8"))
    assert from_file.size == from_string.size
    assert from_file.tobytes() == from_string.tobytes()


def test_image_can_be_saved_as_png(tmp_path: Path):
    image = render('"Step"')
    destination = tmp_path / "chart.png"
    image.save(destination)
    reloaded = Image.open(destination)
    assert reloaded.size == image.size
    assert reloaded.mode == "RGB"


def test_long_words_and_multiline_text_render():
    long_word = "w" * 400
    image = render(f'"{long_word}"\n"first\\nsecond"')
    assert image.width > 100
    assert image.height > 100


def test_empty_pseudocode_renders_start_and_end():
    image = render("")
    assert image.width > 0 and image.height > 0
    scene = scene_for("")
    assert [shape.text for shape in shapes(scene, "terminator")] == ["Start", "End"]


def test_version_is_exposed():
    assert isinstance(flowcharts.__version__, str)
