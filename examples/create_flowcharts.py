"""Render every pseudocode example to a PNG in ``examples/images/``.

Run from anywhere::

    python examples/create_flowcharts.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import flowcharts

PSEUDOCODE_DIR = Path(__file__).resolve().parent / "pseudocode"
OUTPUT_DIR = Path(__file__).resolve().parent / "images"


def main(output_dir: Path | None = None) -> list[Path]:
    """Render each example; return the paths of the written files."""
    target = Path(output_dir) if output_dir else OUTPUT_DIR
    target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for source in sorted(PSEUDOCODE_DIR.glob("*.py")):
        image = flowcharts.render_file(source)
        destination = target / f"{source.stem}.png"
        image.save(destination)
        written.append(destination)
        print(f"{source.name} -> {destination}")
    return written


if __name__ == "__main__":
    main()
