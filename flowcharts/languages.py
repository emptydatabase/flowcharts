"""Languages: the fixed strings drawn on the flowchart.

A language only controls the terminator labels (start/end) and the
yes/no labels of decision arrows.
"""

from __future__ import annotations

from dataclasses import dataclass

from .errors import LanguageError


@dataclass(frozen=True)
class Language:
    """Fixed display strings for one language."""

    name: str
    start: str
    end: str
    yes: str
    no: str


_LANGUAGES: dict[str, Language] = {}


def register_language(language: Language, *, replace: bool = False) -> Language:
    """Register a language so it can be selected by name."""
    key = language.name.lower()
    if key in _LANGUAGES and not replace:
        raise LanguageError(f"language already registered: {language.name!r}")
    _LANGUAGES[key] = language
    return language


def get_language(name: str) -> Language:
    """Look up a registered language by name."""
    try:
        return _LANGUAGES[name.lower()]
    except KeyError:
        available = ", ".join(sorted(_LANGUAGES))
        raise LanguageError(
            f"unknown language {name!r} (available: {available})"
        ) from None


def language_names() -> list[str]:
    return sorted(_LANGUAGES)


def coerce_language(value: Language | str | None) -> Language | None:
    """Accept a language name or instance; ``None`` passes through."""
    if value is None or isinstance(value, Language):
        return value
    if isinstance(value, str):
        return get_language(value)
    raise LanguageError(
        f"expected a language name or Language, got {type(value).__name__}"
    )


register_language(Language(name="en", start="Start", end="End", yes="Yes", no="No"))
register_language(
    Language(name="it", start="Inizio", end="Fine", yes="Sì", no="No")
)
