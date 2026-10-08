# AGENTS.md

Working notes for developing the `flowcharts` library (pseudocode →
Pillow image).

## Commands

All commands run from the repo root, using the project venv:

```bash
.venv/bin/python -m pytest -q          # full test suite (expect all green)
.venv/bin/python -m pytest tests/test_layout.py -q
.venv/bin/python examples/create_flowcharts.py   # writes examples/images/*.png
.venv/bin/pip install -e .             # re-install after pyproject changes
```

There is no linter/type-checker configured yet; keep `from __future__
import annotations`, type hints on public functions, and the existing
code style.

## Repository layout

```
pyproject.toml            # packaging; deps: Pillow; pytest in a dev extra
flowcharts/
  __init__.py             # public API re-exports, __version__
  errors.py               # FlowchartError + subclasses
  metadata.py             # parse_metadata: first string → Metadata
  languages.py            # Language (start/end/yes/no), registry
  themes.py               # Theme (colors/sizes/font_path), registry
  parser.py               # source → AST → model (Flowchart/Block/nodes)
  model.py                # Process/Input/Output/If/While/Block/Flowchart
  fonts.py                # FontSet: wrap(), width(), line_height()
  layout.py               # model + theme → Scene (shapes/connectors/circles)
  render.py               # Scene → PIL.Image
examples/
  pseudocode/*.py         # four sample inputs (also used as tests)
  create_flowcharts.py    # renders every sample to examples/images/
  images/*.png            # generated output (gitignored except .gitkeep)
tests/
  helpers.py              # scene_for(), with_meta(), assertion helpers
  test_*.py               # metadata, parser, layout, render, examples
```

## Design

Four stages, each a module with one job:

1. **parse** (`parser.py`): `ast.parse` the source, walk statements into
   `model` nodes. String statements become `Process`, `input()`/`print()`
   become `Input`/`Output`, `if`/`elif`/`else` build `If` (each `elif`
   is an `If.nested` link), `while` builds `While`. Anything else on a
   whitelist becomes a `Process`; everything else raises
   `UnsupportedSyntaxError`.
2. **layout** (`layout.py`): two passes — `_measure*` bottom-up computes
   relative sizes, `_layout*` top-down places absolute coordinates into
   a `Scene` of `Shape`s (rect/diamond/parallelogram with point lists),
   `Connector`s (polyline points + arrowhead flag + optional label) and
   `Circle`s. All geometry constants live at the top of this file.
3. **render** (`render.py`): draw order is connectors → shapes → circles
   → arrowheads → shape text → labels → title. Never computes geometry.
4. **theme/language** (`themes.py`, `languages.py`): plain dataclasses
   plus name registries (`register_*`, `get_*`, `*_names`).

### Hard rules from the spec

- **Metadata**: the first string of the source is *always* the metadata
  header (title/theme/language). Pseudocode that needs no header must
  start with `""`. Tests use `helpers.with_meta()`.
- **if**: yes-branch leaves the decision's right side, no-branch the
  left side; both descend into the left/right sides of a small
  connection circle whose bottom arrow continues to the rest of the
  chart. `elif` = nested decision whose circle feeds the outer
  circle's left side.
- **while**: arrow from the decision's bottom to the body; body end
  loops back up the *left* side (back edge); exit leaves the *right*
  side, runs down past the body and returns to the axis
  (`BACK_DROP`/`EXIT_DROP` lanes keep them apart).
- **negation**: `not` is stripped from the condition text and recorded
  as `negated`; it swaps the yes/no *label text only*, never geometry.
- **input/output parallelograms** lean in opposite directions
  (`IO_SKEW`, `forward` flag).
- Start/end terminators and the title header are always rendered;
  language decides their wording.

### Geometry reference

Constants at the top of `layout.py` (edit there, not inline): node/term
sizes and padding, `DIA_*` (decision width, text wrap width and padding
for the arrow stubs), `V_GAP`, `CLEAR`, `LANE_EMPTY`/`LANE_PAD`,
`JOIN_DROP`, `BODY_GAP`, `BACK_DROP`, `EXIT_DROP`, `CIRCLE_R`.
`usable_width(kind)` subtracts the lane/exit allowances from the image
width when measuring diamonds.

## Testing approach

- **Scene-level, not pixel-level.** Tests build a `Scene` through
  `helpers.scene_for(source)` and assert shape kinds, side geometry
  (e.g. connector endpoints, join sides, lane ordering), non-overlap and
  theme/language text. No golden PNGs — Pillow rendering differs across
  versions/platforms.
- Only a few tests touch pixels (`test_render.py`): image opens, size
  grows with content, colors come from the theme.
- The `SOURCES`-style parametrized loops check invariants across all
  bundled examples. `tests/test_examples.py` mirrors
  `examples/create_flowcharts.py`.
- System TTF fonts are unavailable; `fonts.py` uses
  `ImageFont.load_default(size=...)`. Don't assume `DejaVuSans.ttf`.

## Conventions

- Public API is re-exported from `flowcharts/__init__.py`; add new
  exports to `__all__` too.
- Errors: raise the most specific subclass of `FlowchartError` from
  `errors.py`, with a message that names the offending construct.
- Value objects are frozen dataclasses (`Theme`, `Language`,
  `Metadata`, scene primitives).
- Pseudocode sources in tests: use `helpers.META_HEADER` /
  `with_meta()` when the test isn't about metadata.
- Adding a shape kind touches three places: `model.py` (node),
  `layout.py` (`_kind_of`, measure, place, `usable_width` if it needs
  clearance), `render.py` (`_draw`).
- After any change: run the full pytest suite and the examples script
  before declaring done.
