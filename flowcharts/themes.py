"""Themes: colors, line weights and font sizes used when drawing.

A theme is a plain dataclass.  Use :func:`register_theme` to make a
custom theme selectable by name from the pseudocode metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, replace as _replace

from .errors import ThemeError


@dataclass(frozen=True)
class Theme:
    """Visual style of a flowchart."""

    name: str
    background: str
    fill: str
    terminator_fill: str
    outline: str
    text: str
    arrow: str
    label: str
    title: str
    line_width: float = 2.0
    title_size: int = 28
    body_size: int = 16
    label_size: int = 14
    font_path: str | None = None

    def with_overrides(self, **kwargs: object) -> "Theme":
        """Return a copy of this theme with some fields replaced."""
        return _replace(self, **kwargs)  # type: ignore[arg-type]


_THEMES: dict[str, Theme] = {}


def register_theme(theme: Theme, *, replace: bool = False) -> Theme:
    """Register a theme so it can be selected by name."""
    key = theme.name.lower()
    if key in _THEMES and not replace:
        raise ThemeError(f"theme already registered: {theme.name!r}")
    _THEMES[key] = theme
    return theme


def get_theme(name: str) -> Theme:
    """Look up a registered theme by name."""
    try:
        return _THEMES[name.lower()]
    except KeyError:
        available = ", ".join(sorted(_THEMES))
        raise ThemeError(
            f"unknown theme {name!r} (available: {available})"
        ) from None


def theme_names() -> list[str]:
    return sorted(_THEMES)


def coerce_theme(value: Theme | str | None) -> Theme | None:
    """Accept a theme name or instance; ``None`` passes through."""
    if value is None or isinstance(value, Theme):
        return value
    if isinstance(value, str):
        return get_theme(value)
    raise ThemeError(f"expected a theme name or Theme, got {type(value).__name__}")


register_theme(
    Theme(
        name="default",
        background="#ffffff",
        fill="#e8f1ff",
        terminator_fill="#dbe7ff",
        outline="#4a6fa5",
        text="#1f2933",
        arrow="#4a6fa5",
        label="#2e7d32",
        title="#1f2933",
    )
)

register_theme(
    Theme(
        name="dracula",
        background="#282a36",
        fill="#44475a",
        terminator_fill="#4d5270",
        outline="#bd93f9",
        text="#f8f8f2",
        arrow="#f8f8f2",
        label="#50fa7b",
        title="#bd93f9",
    )
)

register_theme(
    Theme(
        name="solarized",
        background="#fdf6e3",
        fill="#eee8d5",
        terminator_fill="#e4ddc7",
        outline="#657b83",
        text="#586e75",
        arrow="#586e75",
        label="#b58900",
        title="#cb4b16",
    )
)
