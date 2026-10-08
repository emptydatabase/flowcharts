"""Parsing of the metadata header.

The first string of the pseudocode (its module docstring) holds
metadata, one ``key: value`` pair per line.  A line that is not a
``key: value`` pair sets the title, so the key may be omitted::

    \"\"\"
    Example 03 - Loop
    Theme: solarized
    Language: it
    \"\"\"
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .errors import MetadataError

_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$")

_KNOWN_KEYS = {"title", "theme", "language"}


@dataclass(frozen=True)
class Metadata:
    """Metadata extracted from the pseudocode header."""

    title: str | None = None
    theme: str | None = None
    language: str | None = None


def parse_metadata(docstring: str | None) -> Metadata:
    """Parse a metadata docstring. ``None`` yields default metadata."""
    title: str | None = None
    theme: str | None = None
    language: str | None = None

    if docstring:
        for raw_line in docstring.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            match = _KEY_RE.match(line)
            if match is None:
                # Bare line: the title (its key is optional).
                title = line if title is None else f"{title} {line}"
                continue
            key, value = match.group(1).lower(), match.group(2).strip()
            if not value:
                raise MetadataError(f"metadata key {key!r} has no value")
            if key in _KNOWN_KEYS:
                if key == "title":
                    title = value
                elif key == "theme":
                    theme = value
                else:
                    language = value
            # Unknown keys are ignored so pseudocode can carry comments.

    return Metadata(title=title, theme=theme, language=language)
