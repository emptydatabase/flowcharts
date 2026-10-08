# flowcharts

Turn Python-like pseudocode into a flowchart image with Pillow.

```python
import flowcharts

image = flowcharts.render_file("examples/pseudocode/02_if.py")
image.save("chart.png")
```

- `if` / `elif` / `else` become decision diamonds with branches leaving
  from the right and left sides and rejoining at a small connection circle.
- `while` becomes a decision whose body hangs below it and loops back up
  the left side.
- `input()` / `print()` become parallelograms leaning in opposite directions.
- Start/end terminators and the title header are drawn automatically.
- Themes (colors/fonts) and languages (start/end/yes/no strings) are
  selectable from the pseudocode itself.

## Installation

Requires Python 3.10+ and [Pillow](https://python-pillow.org/) (installed
automatically). From a checkout:

```bash
pip install -e .
```

## Quickstart

Pseudocode is ordinary Python. Its **first string is the metadata
header**; every statement after it becomes a flowchart shape.

```python
import flowcharts

lines = [
    '"""',                     # the first string is the metadata header
    "Title: Guess the Number",
    "Theme: dracula",
    '"""',
    'input("Guess")',
    'if "Correct":',
    '    print("You win")',
    'else:',
    '    print("Try again")',
]
image = flowcharts.render("\n".join(lines))
image.save("guess.png")
```

## The pseudocode format

### Metadata header

The first string of the file carries metadata, one `key: value` pair per
line. Keys are case-insensitive; unknown keys are ignored.

```python
"""
Title: Example 02 - If
Theme: dracula
Language: en
"""
```

| Key        | Meaning                                    | Default   |
|------------|--------------------------------------------|-----------|
| `Title`    | Heading drawn above the chart. The key is optional: a line without `key:` sets the title. | none |
| `Theme`    | Name of a registered theme.                | `default` |
| `Language` | Name of a registered language.             | `en`     |

An unknown theme or language raises `ThemeError` / `LanguageError`.

Because the header is *always* the first string, pseudocode without
metadata simply starts with an empty string:

```python
""
"Step 1"
"Step 2"
```

### Statements

| Pseudocode                                | Flowchart shape |
|-------------------------------------------|-----------------|
| `"Step"`                                  | process rectangle |
| `input("Prompt")`                         | input parallelogram (leaning right) |
| `print("Result")`                         | output parallelogram (leaning left) |
| `if` / `elif` / `else`                    | decision diamond + connection circle |
| `while`                                   | decision diamond with a loop-back |
| anything else simple (`x = 1`, `f()`, `pass`) | process rectangle |
| start / end                               | rounded terminators, added automatically |

The condition of an `if`/`while` is unwrapped: `if "Condition 1"` shows
`Condition 1`, and `while not "W"` shows `W` (the yes/no labels are
swapped so they describe the displayed condition).

Not supported (raises `UnsupportedSyntaxError`): `for`, `with`, `try`,
`def`, `class`, `import`, `return`, `break`, `continue`, `raise`,
`assert`, `del`, `global`, `nonlocal`, and `while ... else`.

### Layout rules

**`if`** — the condition becomes a decision. The *yes* branch leaves
from the right side, the *no* branch from the left side. Both branches
run down and enter the left and right sides of a small connection
circle; an arrow leaving the bottom of the circle continues to the rest
of the flowchart.

```
                         ╱ Condition 1 ╲
                No ◄─────┤               ├─────► Yes
                         │               │       │
                         ▼               │       ▼
                    [  else  ]           │  [  true  ]
                         │               │       │
                         └───────►○◄──────┴───────┘
                                     │
                                     ▼
                                [  next…  ]
```

**`elif`** — drawn exactly like a nested `if` inside the *no* branch.
The nested decision gets its own connection circle, and the arrow
leaving the bottom of that circle feeds the left side of the outer
circle. Chains of `elif` nest the same way.

**`while`** — the condition becomes a decision:

- an arrow leaves the **bottom** of the decision and points at the body;
- at the end of the body the line swings left and runs **up the left
  side** back into the decision;
- another arrow leaves the **right** side of the decision, runs **down
  the right side** past the body, returns to the middle and continues to
  the rest of the chart.

**Input/output** — both are parallelograms, but they lean in opposite
directions so inputs and outputs are easy to tell apart.

## Themes

| Name        | Look |
|-------------|------|
| `default`   | light, blue outlines |
| `dracula`   | dark, Dracula palette |
| `solarized` | Solarized Light |

```python
from flowcharts import Theme, register_theme

register_theme(
    Theme(
        name="mono",
        background="#ffffff",
        fill="#f2f2f2",
        terminator_fill="#e4e4e4",
        outline="#000000",
        text="#000000",
        arrow="#000000",
        label="#000000",
        title="#000000",
    )
)
image = flowcharts.render(source, theme="mono")
# ...or set "Theme: mono" in the metadata header
```

A theme also controls line width, font sizes and, optionally, a
`font_path` pointing at a TrueType font (by default Pillow's bundled
font is used).

## Languages

| Name | Start | End | Yes | No |
|------|-------|-----|-----|----|
| `en` | Start | End | Yes | No |
| `it` | Inizio | Fine | Sì | No |

```python
from flowcharts import Language, register_language

register_language(Language(name="de", start="Start", end="Ende", yes="Ja", no="Nein"))
```

## API

```python
def render(pseudocode: str, *, theme=None, language=None) -> PIL.Image.Image
def render_file(path, *, theme=None, language=None) -> PIL.Image.Image
```

`theme` / `language` accept a name or an object. Precedence: explicit
argument → metadata header → built-in default.

Also exported: `render_flowchart`, `parse`, `Metadata`, `Theme`,
`Language`, `register_theme`, `register_language`, `get_theme`,
`get_language`, `theme_names`, `language_names`, and the exceptions
`FlowchartError`, `ParseError`, `MetadataError`, `ThemeError`,
`LanguageError`, `UnsupportedSyntaxError`.

## Examples

Four examples live in [`examples/pseudocode`](examples/pseudocode):
a plain process, an `if`/`elif`/`else` chain, `while` loops in Italian
with the solarized theme, and input/output shapes.

Render all of them to `examples/images/`:

```bash
python examples/create_flowcharts.py
```

## Development

```bash
python -m pytest
```

The tests assert layout geometry (branch sides, connection circles,
loop-back lanes, shape overlap) rather than pixel-exact golden images,
so they are robust across Pillow versions. See `AGENTS.md` for the
internals.

## License

GPL-3.0 — see [LICENSE](LICENSE).
