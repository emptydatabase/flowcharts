"""Exception hierarchy for the flowcharts library."""

from __future__ import annotations


class FlowchartError(Exception):
    """Base class for all flowcharts errors."""


class ParseError(FlowchartError):
    """The pseudocode could not be parsed."""


class MetadataError(FlowchartError):
    """The metadata header of the pseudocode is invalid."""


class ThemeError(FlowchartError):
    """The requested theme is not registered."""


class LanguageError(FlowchartError):
    """The requested language is not registered."""


class UnsupportedSyntaxError(FlowchartError):
    """The pseudocode uses a construct that cannot be rendered."""

    def __init__(self, message: str, lineno: int | None = None) -> None:
        self.lineno = lineno
        if lineno is not None:
            message = f"line {lineno}: {message}"
        super().__init__(message)
