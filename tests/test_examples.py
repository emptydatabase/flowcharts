"""The bundled examples must render, and the examples script must work."""

import runpy
from pathlib import Path

import pytest
from PIL import Image, ImageColor

import flowcharts
from flowcharts.themes import get_theme

from helpers import EXAMPLES_DIR, example_sources

EXPECTED = {
    "01_process.py": {
        "title": "Example 01 - Process",
        "theme": "default",
        "language": "en",
    },
    "02_if.py": {
        "title": "Example 02 - If",
        "theme": "dracula",
        "language": "en",
    },
    "03_loop.py": {
        "title": "Example 03 - Loop",
        "theme": "solarized",
        "language": "it",
    },
    "04_io.py": {
        "title": "Example 04 - Input/Output",
        "theme": "default",
        "language": "en",
    },
}


def test_every_example_file_is_covered():
    assert {path.name for path in example_sources()} == set(EXPECTED)


@pytest.mark.parametrize("name,expected", sorted(EXPECTED.items()))
def test_example_metadata(name, expected):
    flowchart = flowcharts.parse((EXAMPLES_DIR / name).read_text(encoding="utf-8"))
    metadata = flowchart.metadata
    assert metadata.title == expected["title"]
    assert (metadata.theme or "default") == expected["theme"]
    assert (metadata.language or "en") == expected["language"]


@pytest.mark.parametrize("path", example_sources(), ids=lambda path: path.name)
def test_examples_render_to_plausible_images(path: Path):
    image = flowcharts.render_file(path)
    assert isinstance(image, Image.Image)
    assert image.mode == "RGB"
    assert image.width >= 250
    assert image.height >= 250


@pytest.mark.parametrize("path", example_sources(), ids=lambda path: path.name)
def test_examples_use_the_expected_theme_background(path: Path):
    image = flowcharts.render_file(path)
    theme_name = EXPECTED[path.name]["theme"]
    expected = ImageColor.getrgb(get_theme(theme_name).background)
    width, height = image.size
    for point in [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)]:
        assert image.getpixel(point) == expected


def test_examples_are_distinct_images():
    images = [flowcharts.render_file(path).tobytes() for path in example_sources()]
    assert len(set(images)) == len(images)


def test_create_flowcharts_script_writes_pngs(tmp_path: Path):
    script = EXAMPLES_DIR.parent / "create_flowcharts.py"
    module = runpy.run_path(str(script), run_name="create_flowcharts_module")
    written = module["main"](tmp_path)

    assert len(written) == len(EXPECTED)
    for path in written:
        assert path.exists()
        with Image.open(path) as image:
            assert image.format == "PNG"
            assert image.size[0] > 0 and image.size[1] > 0
    assert {path.name for path in written} == {
        f"{Path(name).stem}.png" for name in EXPECTED
    }
