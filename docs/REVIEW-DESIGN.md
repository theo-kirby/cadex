# REVIEW-DESIGN.md — The review dashboard as one designed page

Verified against source: 2026-09-13. [Cadex-new]

This is the design specification for the page `cadex review` serves
(`cli/cadex_cli/review_static/`, ADR-286) and for the operator dashboard that
runs it on port 8765 between iterations (ot5 D10). It is the contract the page
is held to by `cli/tests/test_review_design.py`: the page follows the spec, and
when the page has to change, the spec changes in the same commit. What the
page *shows* — the reader, the routes, the permitted-paths rule — is
`docs/CLI.md`; this document is only about how it is laid out, typed and
coloured, and why.

Written under the ot6 charter (ADR-328), whose first criterion is that the
dashboard becomes one designed page: academic but modern, one type scale and
one palette across chrome and viewport, a clear hierarchy, readable on a phone
and orbitable by touch. §7 records what the page looked like before the spec,
measured, so the after can be compared against it.

## 1. Purpose

The page answers one question for one person: **what is the state of this
project's design and training right now, and what did the runs before it look
like?** The reader is the operator of an unattended loop, on a desk browser
between iterations or on a phone away from the desk. They inspect; they never
author. Every control on the page is therefore a *view* control (select a run,
orbit the model, play a video, open a document), and the page holds no project
state of its own — it polls the server and redraws.

Three consequences shape everything below:

- **The model is the subject.** The viewport is the largest region on every
  width, and it is the thing the videos, the curves and the identities are
  *about*. Nothing sits beside it at phone width.
- **Identity before interpretation.** What is shown is named (run, revision,
  digest, relation to the accepted state, what the viewer is rendering) before
  any number about it, because a historical run must never read as the
  current design.
- **Reading, not scanning.** Section headings read as an academic paper's —
  sentence case, numbered, ruled — and the body is prose-sized. Controls read
  as a modern application's — flat, rounded, generous tap targets — so that a
  phone can drive them.

## 2. Hierarchy

Top to bottom, in reading order, on every width. The order *is* the charter's
"project and current run, model, curves, videos, history".

| # | Region | Element hooks (stable) | What it is for |
|---|---|---|---|
| 0 | **Masthead** | `#top`, `#project-name`, `#accepted-line`, `#freshness` | The project's name, the accepted identity now (revision, digest, updated, run count), and whether the page is live or stale. One row on desk, two on phone. |
| 1 | **Run selection** | `#sidebar`, `#current-run`, `#views li[data-run]` | Which view is shown: *Accepted now*, then every recorded run with its relation (current/historical) and status. The current run is marked. A sidebar at desk width; a collapsible run list under the masthead on phone (§6). |
| 2 | **Identity** | `#identity`, `#view-kind`, `#view-relation`, `#view-status`, `#view-revision`, `#view-digest`, `#view-identity-source`, `#view-recorded`, `#policy-origin`, `#view-note`, `#view-policy-store` | What the rest of the page is about. Kind and relation as chips, then the key/value block. |
| 3 | **Model** | `#model-status`, `#viewer`, `#model-fit`, `#model-components` | The accepted revision's tessellated solids in the shared environment (§4), orbit by pointer or touch, fit control, and — once D4 lands — the labelled collision-proxy toggle, off by default. |
| 4 | **Curves** | `#telemetry`, `[data-metric]`, `[data-history]`, `#checkpoint-source`, `#checkpoints` | Training telemetry: the five metrics as a stat row, the three histories (reward per step, loss, episode length) as curves side by side on desk and stacked on phone, then checkpoint provenance. |
| 5 | **Videos** | `#videos`, `#videos li[data-video]` | The run's recorded clips, playable inline and downloadable, each captioned with its identity strip (revision, style, policy, seed) and — once D4 lands — what it shows. |
| 6 | **Record** | `#training`, `#params`, `#params-note`, `#artifacts`, `#problems`, `#disk`, `#docs`, `#decisions`, `#doc-view` | The appendix: training request and receipt, parameters and specs, retained artifacts and disk use, document snapshots and decisions. Full tables at desk width; on phone each table scrolls inside its own card, never the page. |

The element ids and `data-*` attributes above are the hooks the CLI suite
(`cli/tests/test_review_server.py`, `test_review_lifecycle.py`,
`test_review_history_scale.py`) already pins. The redesign moves and restyles
them; it does not rename them, so every ot5 browser test keeps its meaning.

Region 6 is the only one that may be collapsed by default, and only on phone.
Regions 0–5 are always open.

## 3. Type scale

One family, one scale, one line height.

| Token | Size | Weight | Use |
|---|---|---|---|
| `--fs-0` | 12 px | 400 | captions, chips, monospace identities, table footers |
| `--fs-1` | 14 px | 400 | body, table cells, controls |
| `--fs-2` | 17 px | 600 | section headings (`h2`): sentence case, numbered, a hairline rule beneath |
| `--fs-3` | 22 px | 600 | the page title (`h1`): the project name |

- **Family**: `--font: system-ui, "Segoe UI", "Helvetica Neue", Arial, sans-serif`;
  identities in `--mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace`
  at `--fs-0`. No web font is loaded: the page must render on a private network
  with no outbound fetch.
- **Line height** 1.45 throughout. Numbers use `font-variant-numeric:
  tabular-nums` so stat rows and tables align.
- **Headings are sentence case, never uppercase.** The current page's
  small-caps grey `h2` is what made it read as a settings panel rather than a
  document. Section headings carry their number ("3 Model") the way a paper's
  do; the chip vocabulary (CURRENT, HISTORICAL, RUN, ACCEPTED NOW) stays
  uppercase because those are labels, not headings.
- The scale is the same at both breakpoints. Phone readability comes from
  layout (§6), not from shrinking the type: nothing on the page is smaller than
  12 px at any width, and the viewport meta stays `width=device-width,
  initial-scale=1` so the phone renders CSS pixels 1:1 and never zooms out to
  fit.

## 4. Palette

**Dark only.** The light theme is removed from the environment module under
D3 (ADR-328), not kept behind a switch. The chrome tokens below are chosen so
that the page background *is* the scene background: the viewport is a window
onto the same near-black place the videos are captured in, not a light card
inside a dark frame.

The base is the greyscale of the `neural-whoop` reference studio (its `:root`
dark set) and of `THEME_PALETTES.dark` in
`cli/cadex_cli/review_static/environment.js`, which already carries the
reference's tile and scene values.

| Token | Value | Used for | Equals |
|---|---|---|---|
| `--bg` | `#141414` | page background | `THEME_PALETTES.dark.scene.bg` (`0x141414`) — chrome and viewport share it |
| `--surface` | `#1b1b1b` | masthead, sidebar, cards | reference `--panel` |
| `--surface-2` | `#242424` | controls, table heads, code blocks, curve backgrounds | reference `--panel-2`; between the mat's tiles `#1c1c1c` / `#232323` and its major line |
| `--surface-3` | `#2c2c2c` | hover, the selected run | reference `--panel-3` |
| `--rule` | `#3a3a3a` | every border and heading rule | reference `--line`; also the mat's major grid line |
| `--rule-strong` | `#4a4a4a` | focus and the selected run's border | reference `--line-strong` |
| `--ink` | `#ededed` | body text | reference `--fg` |
| `--ink-2` | `#9a9a9a` | captions, labels, secondary text | reference `--muted` |
| `--accent` | `#dcdcdc` | links, the curve stroke, the current-run mark | reference `--accent`. Greyscale: colour is reserved for status. |
| `--ok` | `#8be0b0` | ok / completed / live / retained | reference `--issue-ok` |
| `--warn` | `#ffe08a` | pending / stale / unknown / truncated | reference `--far-fg` |
| `--bad` | `#ff9d9d` | failed / missing / refused / error | reference `--stop-fg` |
| `--info` | `#6ff0f0` | the *current* relation chip and the training-in-progress state | reference `--go-fg` |

Status chips use the status colour as ink on a tinted `--surface-2`
(`color-mix(in srgb, <status> 18%, var(--surface-2))`), never as a solid fill,
so a page full of chips stays quiet. A historical run's chip is `--ink-2` on
`--surface-2`: history is neutral, not a warning. The component swatches in the
model list keep the eight-colour `PALETTE` of `review_scene.js`, because those
colours identify parts and appear in the videos too.

Contrast: `--ink` on `--bg` is 15.7:1, `--ink-2` on `--surface` is 6.1:1,
and every status colour on `--surface-2` is at least 7.8:1, so each text
token clears WCAG AA at `--fs-0`.

The stylesheet declares exactly these tokens on `:root`. Today the design
test pins the table above to the environment module's dark scene background;
when the page follows the spec it also reads the tokens back from the
rendered page (`getComputedStyle`), so a palette drift is a failing test
rather than a slow surprise.

## 5. Spacing and shape

A 4 px base: `--s1` 4, `--s2` 8, `--s3` 12, `--s4` 16, `--s5` 24, `--s6` 32.

- Page gutter `--s5` at desk, `--s3` on phone. Card padding `--s4` at desk,
  `--s3` on phone. Cards are separated by `--s4`; regions by `--s6`.
- **Shape**: `--radius` 10 px on cards and the viewport, `--radius-sm` 8 px on
  controls and chips, `--bw` 1.5 px borders — the reference's deliberately
  not-hairline weight.
- **Controls**: minimum 40 × 40 px hit area on touch (`@media (pointer:
  coarse)`), 32 px on desk; `--surface-2` fill, `--rule` border, `--surface-3`
  on hover, `--rule-strong` on focus. No native chrome on buttons or selects.
- **Curves**: each history is an SVG with `viewBox 0 0 400 100`, `--accent`
  stroke of 1.5 px on a `--surface-2` field with a `--rule` frame, its range
  and iteration span as an `--fs-0` caption. Three abreast at desk width
  (each `minmax(240px, 1fr)`), stacked on phone.
- **The viewport** keeps a 16:9 box at desk (`aspect-ratio: 16 / 9`, up to
  620 px tall) and 4:3 on phone, always the full width of its column, with
  `touch-action: none` so a one-finger drag orbits instead of scrolling the
  page. The canvas backing store follows the box, so the model is never
  stretched.
- **Video** elements are the full width of their card with the same radius as
  the viewport; the caption sits beneath, never overlaid.

## 6. Breakpoints

Two, chosen from the two widths the charter measures against and the one in
between where a sidebar stops paying for itself.

| Range | Layout |
|---|---|
| **≥ 1000 px** (desk; 1400 is the reference width) | Two columns: run selection as a 280 px sidebar, sticky under the masthead; regions 2–6 in the detail column. Curves three abreast. Masthead on one row. |
| **600–999 px** (tablet, a half-width desk window) | One column. Run selection becomes a horizontal strip of run chips under the masthead, scrolling within itself. Curves two abreast, then one. |
| **< 600 px** (phone; 400 × 850 is the reference size) | One column with `--s3` gutters. Run selection is a `<details>` disclosure showing "Runs · current: *name* · *n* recorded", closed by default, opening to the same list. Identity key/value pairs stack (key above value). The viewport, the curves and the videos are the full width. Tables in region 6 scroll horizontally inside their card. |

Invariants at every width, and the ones the design test asserts at 1400 × 900
and at 400 × 850 with touch emulation once the page follows the spec (until
then §7 is the measured record of the page that does not):

1. **No horizontal page overflow**: `document.documentElement.scrollWidth <=
   innerWidth`. Achieved by `min-width: 0` on grid children and per-table
   scroll wrappers, never by `overflow-x: hidden` on the body, which would
   only hide the sliver.
2. **The layout viewport is the device width**: `innerWidth === 400` at phone
   size. §7 shows what happens when it is not.
3. **The viewport fills its column**: canvas width ≥ 90 % of the detail
   column at desk and ≥ 90 % of `innerWidth − 2·gutter` on phone.
4. **The palette tokens of §4 are the computed values** on the rendered page.
5. **Type never drops below 12 px**, and `h1`/`h2`/body compute to §3.

## 7. Before: the page as ot5 left it

Measured on the persistent operator dashboard on 2026-09-13, serving
`ot5-lark-copy85` with `lark109-engine2` selected, live, model loaded, by
`docs/probes/ot6/design/capture_before.py` (receipt:
`docs/probes/ot6/design/before.json`). The screenshots beside this document
are the quantised copies (256 colours, under the 200 KB receipt cap); the
originals stay in the operator's `cadex-projects/ot6-design/` with the
SHA-256 digests in the receipt's companion record.

| | 1400 × 900 | 400 × 850, mobile emulation | 400 × 850, plain window |
|---|---|---|---|
| Screenshot | [before-1400.png](review-design/before-1400.png) | [before-400x850.png](review-design/before-400x850.png) | not committed |
| Layout viewport | 1400 px | **868 px** | 400 px |
| Horizontal overflow | 0 | 0 at the 868 px layout the browser widened to; the phone sees 400 of it | **468 px** |
| Sidebar | 280 px | 280 px | 280 px |
| Model canvas | 1019 × 520 | **34 × 520** | **19 × 520** |
| Page height | 3 993 px | 28 772 px | 29 053 px |
| Type | 14 / 18 / 14 / 12 (body / h1 / h2 / chip) | same | same |

What the pictures show:

- **At 1400 px** the chrome is a dark blue-grey (`--bg #14161a`, `--panel
  #1d2026`) around a *light* viewport: grey tiles, soft-grey fog, dark-on-light
  PROTOTYPE / 1 METER labels. Two palettes on one page, and the lighter one
  is on the region that matters. Headings are uppercase grey labels; identity
  chips, table headers and prose all sit at the same visual weight; the
  identity card, the model, the parameters, the training, the artifacts and
  the documents are six equal cards in a stack, so nothing tells the eye
  where to start.
- **At 400 × 850** the grid's fixed 280 px sidebar plus the detail column's
  minimum content width (the seven-column parameters table, the artifacts
  table, the long identity strings) force the layout viewport to 868 px. A
  phone shows the leftmost 400 of those: the sidebar, and a sliver of the
  identity chips wrapping one word per line. The model canvas is 34 px wide.
  The videos, curves and every table are off the right edge. That is the
  "collapses into a sliver" the charter names.

## 8. Evidence for D1 and D2

D1's evidence is this document, the before screenshots above, the after
screenshots at the same two sizes committed beside them when the page follows
the spec, the design test asserting §6's invariants and §4's tokens on the
rendered page, and the operator URL showing the new design on the active
project. D2's evidence is the same test's phone half: touch emulation at
400 × 850, a touch orbit that changes the camera, curves legible, a video
that plays and downloads. Each ships as a receipt under `docs/probes/ot6/`
within the charter's caps (16 KB per receipt, 200 KB per image), which
`cli/tests/test_review_design.py` enforces.
