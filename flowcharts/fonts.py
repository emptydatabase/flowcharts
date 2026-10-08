"""Font loading, text measuring and line wrapping."""

from __future__ import annotations

from PIL import ImageFont

from .themes import Theme


class FontSet:
    """The fonts used for one theme (body, labels and title)."""

    def __init__(self, theme: Theme) -> None:
        self.theme = theme
        self.body_size = theme.body_size
        self.label_size = theme.label_size
        self.title_size = theme.title_size
        self.body = self._load(theme.font_path, theme.body_size)
        self.label = self._load(theme.font_path, theme.label_size)
        self.title = self._load(theme.font_path, theme.title_size)

    @staticmethod
    def _load(path: str | None, size: int):
        if path:
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                pass
        try:
            return ImageFont.load_default(size=size)
        except (TypeError, ValueError):
            return ImageFont.load_default()

    def line_height(self, size: int) -> float:
        return round(size * 1.3) + 1

    def width(self, font, text: str) -> float:
        getlength = getattr(font, "getlength", None)
        if getlength is not None:
            return float(getlength(text))
        box = font.getbbox(text)
        return float(box[2] - box[0])

    def box(self, font, text: str) -> tuple[float, float, float, float]:
        """Bounding box of ``text`` relative to its own origin."""
        return tuple(float(v) for v in font.getbbox(text))  # type: ignore[return-value]

    def wrap(self, text: str, max_width: float, font, size: int) -> list[str]:
        """Wrap ``text`` into lines no wider than ``max_width``.

        Existing newlines are respected and words longer than the limit
        are split at character boundaries.
        """
        lines: list[str] = []
        for paragraph in str(text).split("\n"):
            if not paragraph.strip():
                lines.append("")
                continue
            current = ""
            for word in paragraph.split():
                if self.width(font, word) > max_width:
                    if current:
                        lines.append(current)
                        current = ""
                    chunk = ""
                    for char in word:
                        if chunk and self.width(font, chunk + char) > max_width:
                            lines.append(chunk)
                            chunk = char
                        else:
                            chunk += char
                    current = chunk
                    continue
                trial = word if not current else f"{current} {word}"
                if self.width(font, trial) <= max_width:
                    current = trial
                else:
                    lines.append(current)
                    current = word
            lines.append(current)
        return lines or [""]
