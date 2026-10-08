"""Render flowcharts from Python-like pseudocode as Pillow images.

Quickstart::

    import flowcharts

    image = flowcharts.render('""\n"Step 1"\n"Step 2"')
    image.save("chart.png")
"""

from __future__ import annotations

from .errors import (
    FlowchartError,
    LanguageError,
    MetadataError,
    ParseError,
    ThemeError,
    UnsupportedSyntaxError,
)
from .languages import Language, get_language, language_names, register_language
from .metadata import Metadata, parse_metadata
from .model import Block, Flowchart, If, Input, Output, Process, While
from .parser import parse
from .render import render, render_file, render_flowchart
from .themes import Theme, get_theme, register_theme, theme_names

__version__ = "0.1.0"

__all__ = [
    "Block",
    "Flowchart",
    "FlowchartError",
    "If",
    "Input",
    "Language",
    "LanguageError",
    "Metadata",
    "MetadataError",
    "Output",
    "ParseError",
    "Process",
    "Theme",
    "ThemeError",
    "UnsupportedSyntaxError",
    "While",
    "__version__",
    "get_language",
    "get_theme",
    "language_names",
    "parse",
    "parse_metadata",
    "register_language",
    "register_theme",
    "render",
    "render_file",
    "render_flowchart",
    "theme_names",
]
