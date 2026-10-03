# DASHBOARD.md — The dashboard, Cadex's only UI

Verified against source: 2026-10-03. [Cadex-new]

This is the design specification for the dashboard: the page `cadex review`
serves (`cli/cadex_cli/review_server.py` and `review_static/`, ADR-286), the
second of Cadex's three parts (ADR-500) and its only UI since the Blender
shell was deleted (ADR-498). It replaces `docs/REVIEW-DESIGN.md`, the ot6 review-page spec (ADR-501),
whose rules it carries unchanged: the hierarchy (§2), the one type scale
(§3), the one dark palette shared by chrome and viewport (§4), and the dark
prototype floor every image is drawn on (§10, §16). It is the contract the
page is held to by `cli/tests/test_review_design.py`: the page follows the
spec, and when the page has to change, the spec changes in the same commit.
What the page *shows* — the reader, the routes, the permitted-paths rule —
is `docs/CLI.md`; this document is about how it is laid out, typed and
coloured, and why.

The dashboard stays light (charter A2): a standard-library Python server,
vanilla JS and the vendored three.js — no npm, no bundler, no build step,
no front-end framework. The project directory is the truth (A3): the page
reads it, and any write it gains goes through the code paths the CLI uses,
never a second one.

The spec was first written under the ot6 charter (ADR-328), whose first
criterion was that the review page become one designed page: academic but
modern, one type scale and one palette across chrome and viewport, a clear
hierarchy, readable on a phone and orbitable by touch. §7 records what the
page looked like before the spec, measured, and §8 what it looked like
following it (ADR-329), measured the same way; both are kept as the
measured baseline the tests still check. §12 is the desk frame that
replaced the two-column desk layout at the owner's direction (ADR-342): a
thin top bar, two resizable sidebars and a stage that holds the model.

## 1. Purpose

The page answers one question for one person: **what is the state of this
project's design and training right now, and what did the runs before it look
like?** The reader is the operator of an unattended loop, on a desk browser
between iterations or on a phone away from the desk. They watch, and step in
only lightly; they never model by hand (VISION's non-goals). Today every
control on the page is a *view* control (select a run, orbit the model, play
a video, open a document): the server answers `GET` and `HEAD` only. It is served for one project
(`cadex review`, at `/`) or for a directory of them (`cadex app` and a bare
`cadex`, ADR-502): an index of the projects at `/`, sharing this page's
tokens, and each project's page under `/p/<name>/`. The
steering controls the orun2 charter's D2 adds — a prompt, a slider, a
comment, accept and restore — will each write through the CLI's own code
path, and in every case the page holds no project state of its own: it polls
the server and redraws.

Three consequences shape everything below:

- **The model is the subject.** The viewport is the largest region on every
  width, and it is the thing the videos, the curves and the identities are
  *about*. At desk it *is* the centre of the page — the stage — and
  everything that describes it sits in the sidebars either side (§12).
  Nothing sits beside it at phone width.
- **Identity before interpretation.** What is shown is named (run, revision,
  digest, relation to the accepted state, what the viewer is rendering) before
  any number about it, because a historical run must never read as the
  current design.
- **Reading, not scanning.** Section headings read as an academic paper's —
  sentence case, ruled — and the body is prose-sized. Controls read
  as a modern application's — flat, rounded, generous tap targets — so that a
  phone can drive them.

## 2. Hierarchy

Top to bottom, in reading order, below the desk breakpoint. The order *is*
the charter's "project and current run, model, curves, videos, history". At
desk the same regions are distributed across the frame — the column says
where (§12) — and the element ids do not change with the width.

| # | Region | Element hooks (stable) | What it is for | Desk frame |
|---|---|---|---|---|
| 0 | **Masthead** | `#top`, `#project-name`, `#accepted-line`, `#freshness` | The project's name, the accepted identity now (revision, digest, updated, run count), and whether the page is live or stale. One row on desk, two on phone. | top bar |
| 1 | **Run selection** | `#sidebar`, `#runs`, `#runs-summary`, `#current-run`, `#views li[data-run]` | Which view is shown: *Accepted now*, then every recorded run with its relation (current/historical) and status. The current run is marked. A sidebar at desk width; a collapsible run list under the masthead on phone (§6). | left sidebar |
| 2 | **Identity** | `#identity`, `#view-kind`, `#view-relation`, `#view-status`, `#view-revision`, `#view-digest`, `#view-identity-source`, `#view-recorded`, `#policy-origin`, `#view-note`, `#view-policy-store` | What the rest of the page is about. Kind and relation as chips, then the key/value block. | right sidebar |
| 2a | **Concept** | `#concept`, `#concept-status[data-state]`, `#concept-figure`, `#concept-sheet`, `#concept-caption`, `#concept-hero` | The design as presented: the concept sheet the last render drew (§14) — studio hero, name, key numbers, palette and line views — with the revision it was drawn from and its relation to the accepted one. Leads the page when there is one. | stage, *Concept* tab, first; the stage opens on it |
| 3 | **Model** | `#model`, `#model-status[data-showing]`, `#viewer`, `#model-fit`, `#show-collision`, `#collision-note`, `#model-components` | The accepted revision's tessellated solids in the shared environment (§4), orbit by pointer or touch, fit control, and the labelled **show collision geometry** toggle, off by default (§11). The status line ends with what is showing. | stage, *Model* tab; toggle and component list in the right sidebar's *Model settings* (`#model-settings`) |
| 4 | **Curves** | `#curves`, `#telemetry`, `[data-metric]`, `[data-history]`, `#checkpoint-source`, `#checkpoints` | Training telemetry: the five metrics as a stat row, the three histories (reward per step, loss, episode length) as curves side by side on desk and stacked on phone, then checkpoint provenance. | stage, *Curves* tab |
| 5 | **Videos** | `#videos-region`, `#videos`, `#videos li[data-video][data-showing]` | The run's recorded clips, playable inline and downloadable, each captioned with its identity strip (revision, style, policy, seed, and what it shows — recordings made before that was recorded say so). | stage, *Videos* tab |
| 5a | **Evaluation** | `#evaluation`, `#evaluation-status[data-state]`, `#evaluation-dot`, `#evaluation-list button[data-evaluation]`, `#evaluation-predicates tr[data-predicate]`, `#evaluation-seeds tr[data-seed][data-filmed]`, `#evaluation-metrics tr[data-metric-row]`, `#evaluation-reward tr[data-term]`, `#evaluation-film li[data-film-seed] [data-film]`, `#evaluation-download` | A policy held to its task's success spec on every frozen seed (§17): the verdict, each predicate's tally, each seed's verdict, ending and values, the behaviour metrics, the reward by term, and the film drawn from the seeds. | stage, *Evaluation* tab |
| 6 | **Record** | `#record`, `#training`, `#params`, `#params-note`, `#params-write`, `#artifacts`, `#problems`, `#disk`, `#docs`, `#decisions`, `#doc-view` | The appendix: training request and receipt, parameters and specs, retained artifacts and disk use, document snapshots and decisions. Full tables at desk width; on phone each table scrolls inside its own card, never the page. | right sidebar: *Training and rollout* (`#record`), *Parameters and specs* (`#params-panel`), *Artifacts* (`#artifacts-panel`); left sidebar: *Documents and decisions* (`#docs-panel`); an opened document on the stage's *Document* tab (`#doc-panel`) |

The element ids and `data-*` attributes above are the hooks the CLI suite
(`cli/tests/test_review_server.py`, `test_review_lifecycle.py`,
`test_review_history_scale.py`) already pins. The redesign moves and restyles
them; it does not rename them, so every ot5 browser test keeps its meaning.

Region 6 is the only one that may be collapsed by default, and only on phone.
Regions 0–5 are always open. At desk every sidebar section folds under its
heading at the reader's hand, never by default.

## 3. Type scale

One family, one scale, one line height.

| Token | Size | Weight | Use |
|---|---|---|---|
| `--fs-0` | 12 px | 400 | captions, chips, monospace identities, table footers |
| `--fs-1` | 14 px | 400 | body, table cells, controls |
| `--fs-2` | 17 px | 600 | section headings (`h2`): sentence case, a hairline rule beneath; the page title in the desk top bar |
| `--fs-3` | 22 px | 600 | the page title (`h1`): the project name |

At desk the frame steps the two headings down one rung of the same scale:
the title in the 44 px top bar is `--fs-2`, and a sidebar section's heading
is `--fs-1` at 600 with no rule, because a ruled 17 px heading every few
lines is what makes a 264 px sidebar read as a form (§12).

- **Family**: `--font: system-ui, "Segoe UI", "Helvetica Neue", Arial, sans-serif`;
  identities in `--mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace`
  at `--fs-0`. No web font is loaded: the page must render on a private network
  with no outbound fetch.
- **Line height** 1.45 throughout. Numbers use `font-variant-numeric:
  tabular-nums` so stat rows and tables align.
- **Headings are sentence case, never uppercase.** The current page's
  small-caps grey `h2` is what made it read as a settings panel rather than a
  document. Section headings no longer carry a number (ADR-342): once the
  regions sit in three columns at desk there is no single reading order for
  a number to state. The chip vocabulary (CURRENT, HISTORICAL, RUN, ACCEPTED NOW) stays
  uppercase because those are labels, not headings.
- The scale is the same at both breakpoints. Phone readability comes from
  layout (§6), not from shrinking the type: nothing on the page is smaller than
  12 px at any width, and the viewport meta stays `width=device-width,
  initial-scale=1` so the phone renders CSS pixels 1:1 and never zooms out to
  fit.

## 4. Palette

**Dark only.** The light theme is removed from the environment module
(ADR-331, under D3 of ADR-328), not kept behind a switch. The chrome tokens below are chosen so
that the page background *is* the scene background: the viewport is a window
onto the same near-black place the videos are captured in, not a light card
inside a dark frame.

The base is the greyscale of the `neural-whoop` reference studio (its `:root`
dark set) and of the one `PALETTE` in
`cli/cadex_cli/review_static/environment.js`, which carries the reference's
dark tile and scene values and nothing else (ADR-331).

| Token | Value | Used for | Equals |
|---|---|---|---|
| `--bg` | `#141414` | page background | `PALETTE.scene.bg` (`0x141414`) — chrome and viewport share it |
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

The stylesheet declares exactly these tokens on `:root`, and the design test
pins the table above to the environment module's dark scene background *and*
reads every token back from the rendered page (`getComputedStyle`) at both
charter sizes, so a palette drift is a failing test rather than a slow
surprise. The chrome is at these values now (§8), and so is the viewport
(§10): the environment module has one palette, the videos are captured in
the same scene, and the viewport's sky *is* `--bg`.

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
  and iteration span as an `--fs-0` caption. The three sit in a
  `repeat(auto-fit, minmax(240px, 1fr))` grid below the desk breakpoint —
  abreast while the column is wide enough, then two, then one, stacked on
  phone — and stacked one per row, up to 1040 px wide, on the desk stage's
  *Curves* tab, where they have the whole centre to themselves. The five metrics above them are a stat row of tiles whose text
  stays `key: value`, which is what the other suites read.
- **The viewport** fills the stage at desk (§12), keeps a 16:9 box (up to
  620 px tall) on a tablet and 4:3 on phone, always the full width of its
  column, with
  `touch-action: none` so a one-finger drag orbits instead of scrolling the
  page. The canvas backing store follows the box, so the model is never
  stretched. **Orbit is by pointer events** (ADR-330): one pointer — mouse
  or finger — orbits, two fingers pinch-zoom, the wheel zooms, and the
  canvas captures the pointer so a drag that leaves it still orbits. The
  Fit button restores the framing, framing the model's bounding sphere in
  the narrower field of view: a canvas at least as wide as it is tall frames
  by the vertical one exactly as before (so a 512 × 512 capture is
  unchanged), a portrait stage between two wide sidebars by the horizontal.
- **Video** elements are the full width of their card with the same radius as
  the viewport (on the desk stage, a grid of 360 px minimum cells, each clip
  no taller than the stage); the caption sits beneath, never overlaid, and leads with a
  **Play / Pause control of the page's own** (`[data-video-play]`, a
  `--control`-height button) because the native controls' tap targets differ
  from phone to phone; the native controls stay for scrubbing. The download
  link is the caption's last item.

## 6. Breakpoints

Two, chosen from the two widths the charter measures against and the one in
between where a sidebar stops paying for itself.

| Range | Layout |
|---|---|
| **≥ 1000 px** (desk; 1400 is the reference width) | The frame (§12): a 44 px top bar; a left sidebar (264 px by default), the stage, a right sidebar (340 px by default); each sidebar resizable and foldable by its inner edge. The page never scrolls; each sidebar and each stage panel scrolls on its own. Curves stacked on the stage. |
| **600–999 px, landscape, ≤ 560 px tall** (a phone held sideways) | The frame, with its sidebars as drawers over a full-width model (§13). |
| **600–999 px** (tablet, a half-width desk window) | One column. Run selection becomes a horizontal strip of run chips under the masthead, scrolling within itself. Curves two abreast, then one. |
| **< 600 px** (phone; 400 × 850 is the reference size) | One column with `--s3` gutters. Run selection is a `<details>` disclosure showing "Runs · current: *name* · *n* recorded", closed by default, opening to the same list. Identity key/value pairs stack (key above value). The viewport, the curves and the videos are the full width. Tables in region 6 scroll horizontally inside their card. |

Invariants at every width, and the ones the design test asserts on the
rendered page at 1400 × 900 and at 400 × 850 with touch emulation (§7 is the
measured record of the page before it followed the spec, §8 after):

1. **No horizontal page overflow**: `document.documentElement.scrollWidth <=
   innerWidth`. Achieved by `min-width: 0` on grid children and per-table
   scroll wrappers, never by `overflow-x: hidden` on the body, which would
   only hide the sliver.
2. **The layout viewport is the device width**: `innerWidth === 400` at phone
   size. §7 shows what happens when it is not.
3. **The viewport fills its column**: at desk the canvas fills the stage
   below its tab row (≥ 98 % of its width), the sidebars meet the window
   edges and the page does not scroll vertically; on phone ≥ 90 % of
   `innerWidth − 2·gutter`.
4. **The palette tokens of §4 are the computed values** on the rendered page.
5. **Type never drops below 12 px**, and `h1`/`h2`/body compute to §3.

## 7. Before: the page as ot5 left it

Measured on the persistent operator dashboard on 2026-09-13, serving
`ot5-lark-copy85` with `lark109-engine2` selected, live, model loaded, by
`docs/probes/ot6/design/capture_page.py` with the label `before` (receipt:
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

## 8. After: the page under the spec

Measured the same way, on the same persistent operator dashboard, on
2026-09-13 after the stylesheet, markup and rendering script were brought to
§2–§6 (ADR-329), still serving `ot5-lark-copy85` with `lark109-engine2`
selected, live, model loaded (receipt: `docs/probes/ot6/design/after.json`;
originals in the operator's `cadex-projects/ot6-design/`).

| | 1400 × 900 | 400 × 850, mobile emulation | 400 × 850, plain window |
|---|---|---|---|
| Screenshot | [after-1400.png](review-design/after-1400.png) | [after-400x850.png](review-design/after-400x850.png) | not committed |
| Layout viewport | 1400 px | **400 px** | 400 px |
| Horizontal overflow | 0 | **0** | **0** |
| Sidebar | 280 px, beside the detail | 376 px wide, a closed disclosure above it | 361 px (a scrollbar takes the rest) |
| Model canvas | 999 × 562 (16:9) | **350 × 263** (4:3) | 335 × 251 |
| Page height | 3 829 px | 6 463 px | 6 790 px |
| Type | 14 / 22 / 17 / 12 (body / h1 / h2 / chip) | same | same |

What changed, against §7:

- **At 1400 px** the chrome is one greyscale: `--bg` page, `--surface` masthead,
  sidebar and cards, `--rule` hairlines under numbered sentence-case headings
  (*1 Runs* … *6 Record*), status as coloured ink on tinted chips. The
  sidebar is sticky beside the detail; the identity block leads, the model
  is the largest region, the curves are a stat row over three histories
  abreast, the videos have a region of their own, and the record — training,
  parameters, artifacts, documents — is the appendix. The viewport inside
  that chrome was still the light scene when this was measured; §10 records
  the dark viewport that replaced it the same day.
- **At 400 × 850** the layout viewport is the device width. The runs are a
  one-line disclosure — *Runs · current: lark109-engine2 · 15 recorded* —
  closed until tapped; the identity pairs stack key over value; the canvas is
  the full width inside 12 px gutters; the curves stack; the parameter and
  artifact tables scroll inside their card. Page height fell from 28 772 px
  to 6 463 px because nothing wraps one word per line any more.

The rendered-page half of `cli/tests/test_review_design.py` asserts §6's five
invariants at both sizes on a fixture project, and pins the receipt above to
this table.

### 8a. The phone, region by region, and by touch

Captured the same day on the same operator URL, same project and run, by
the same script with the label `phone` (receipt:
`docs/probes/ot6/design/phone.json`), after the viewer moved to pointer
events. Under touch emulation at 400 × 850 the script dragged one finger
120 × 50 px across the model, then tapped Fit:

| | before | after the drag | after Fit |
|---|---|---|---|
| yaw / pitch | 0.8 / 0.5 | **−0.4 / 1.0** | 0.8 / 0.5 |
| distance | 1 339.46 mm | 1 339.46 mm | 1 339.46 mm |
| page scroll during the drag | | **0 px** | |

Then it clipped each region of §2 to a screenshot at most one phone screen
tall (the quantised copies are beside this document):

| # | Region | Height at 400 px | Screenshot |
|---|---|---|---|
| 0 | Masthead | 151 px | [phone-top.png](review-design/phone-top.png) |
| 1 | Run selection (closed disclosure) | 62 px | [phone-sidebar.png](review-design/phone-sidebar.png) |
| 2 | Identity | 641 px | [phone-identity.png](review-design/phone-identity.png) |
| 3 | Model | 791 px | [phone-model.png](review-design/phone-model.png) |
| 4 | Curves | 845 px | [phone-curves.png](review-design/phone-curves.png) |
| 5 | Videos | 88 px (this run recorded none) | [phone-videos-region.png](review-design/phone-videos-region.png) |
| 6 | Record | 3 708 px, first 850 shown | [phone-record.png](review-design/phone-record.png) |

The masthead is the full 400 px; every other region is 376 px inside the
12 px gutters. `test_phone_receipt_records_touch_orbit_and_every_region_on_the_operator_url`
pins the receipt and the PNG sizes to this table.

## 9. Evidence for D1 and D2

**D1** has this document; the before and after screenshots at the two sizes
beside it (§7, §8); `test_rendered_page_follows_the_spec`, which reads §4's
tokens, §3's type scale and §6's invariants back from the rendered page at
both sizes; and the operator URL receipts showing the design on the active
project and run (§8). The viewport's half of "one palette" is §10: the light
scene is removed (ADR-331) and the viewport's background is the page's.

**D2** has two halves, both in `cli/tests/test_review_design.py`, both at
400 × 850 with `Emulation.setDeviceMetricsOverride(mobile: true)` and touch
emulation, both skipping without a Chromium:

- *Layout* — `test_rendered_page_follows_the_spec[phone]`: the layout
  viewport is 400 px, nothing overflows it, nothing is below 12 px, the
  run list is a closed disclosure that opens on a tap, the canvas fills the
  width, the three curves stack at ≥ 90 % of their card. §8's receipt shows
  the same on the operator URL.
- *Interaction* — `test_phone_touch_orbits_pinches_plays_and_downloads`, on a
  fixture run with a real FFmpeg-encoded video (skips without FFmpeg): a
  one-finger drag dispatched as `Input.dispatchTouchEvent` orbits the model
  (yaw and pitch change, distance does not) and the page does not scroll; a
  two-finger spread zooms in without disturbing the orbit; a tap on the
  40 px Fit control restores the camera; each curve fills its width with a
  caption of at least 12 px; a tap on the Play control starts playback
  (the control reads Pause, `currentTime` advances); a tap on the download
  link fetches the file whole, with the recorded SHA-256. §8a's receipt
  shows the orbit and the Fit tap on the operator URL, and the region
  screenshots are §8a's table.

What the evidence is not: a physical phone. Headless Chromium's touch
emulation and its gesture recogniser are what is measured, and one of that
recogniser's behaviours is recorded in the capture script — a tap landing
within a few hundred milliseconds of a drag's end is dropped, on a device as
under emulation, so the script lets a second pass before tapping Fit.

Every receipt ships under `docs/probes/ot6/` within the charter's caps
(16 KB per receipt, 200 KB per image), which the same test file enforces.

## 10. The viewport: dark only, shared with the capture

The environment module behind the viewport and the video capturer has one
palette, the reference's dark one (ADR-331); the light palette and its theme
setter are gone from the code rather than parked behind a switch. Its scene
background is `--bg`, so the model sits in the same near-black place the
page is, and the videos are captured in it. Measured on the persistent
operator dashboard on 2026-09-13, serving `ot5-lark-copy85` with
`lark98-final` re-rendered in the dark look: viewport and capture page
byte-identical at the same pose and camera; the decoded first frame within
1.1 of 255 of the viewport; the reference's own unmodified scene modules,
dark theme, over the same solids at the same cameras, equal in mean
luminance to 0.1. The frames, the numbers and the written assessment —
floor and grid, horizon and fog, palette, lighting and shadows, materials,
framing, camera — are `docs/probes/ot6/look/README.md`, with the composite
[side-by-side.png](probes/ot6/look/side-by-side.png).

**The grid is anchored to the world (ADR-343).** The mat's major lines sit
on whole multiples of the pitch in world metres, with a block corner on the
origin, whatever the floor's size. The floor grows with the fog as the camera
pulls back, and until 2026-09-14 its texture was laid from the plane's corner.
Zooming out past a 24 m floor slid the grid under the model, by 0.26 of a
2 m block at twice the fit distance and 0.51 at four times, so a *1 METER*
line was not where a metre is. A size change now rescales the plane and
re-offsets the texture without repainting it. Only a change of pitch or minor
mesh repaints. The minor mesh still steps with the framing (5 → 10 → 20 cm,
then none) by design, and the major lines never move.

**The follow camera and the timer (ADR-332).** A recording's camera is the
reference's follow rig, computed by the shared scene module (`follow`) from
the subject's centre at every sampled solved pose and recorded into the
video's `framing`: the subject's standing height — its vertical extent at the
first solved pose — fills a declared **0.22** of the frame height, so the
standoff is one number for the whole clip and apparent size is fixed by
construction; the camera keeps the viewer's yaw and pitch (the horizon never
moves) and translates with a Hann-smoothed copy of the track, half-window
0.4 s, the subject resting 0.06 of the half-frame below centre for headroom;
the subject may lead that anchor by 0.26 of the half-frame in either screen
axis before an `l·tanh(d/l)` limiter pulls the anchor after it, so a whip
cannot carry it out of frame. The viewport's default fit is unchanged: it is
an inspection fit, and the same `follow` is available to it for a shot.

The timer is the reference's caption pill: panel `rgba(20,22,26,.72)`, line
`rgba(244,245,247,.22)`, ink `--ink`, the page's `--font` at 3.2 % of the
frame height and never below `--fs-0`, tabular numerals letter-spaced 0.12 em,
4.2 % of the height in from the bottom-left corner. It is drawn inside the
WebGL frame after the stage, so the capture's PNG and the viewport bake the
same pixels; it shows simulation seconds, and it is hidden while the viewport
is at rest. Measured on the persistent dashboard with `lark98-final`
re-rendered: the viewport at the recording's camera, pose and clock is within
1.24 of 255 of every decoded frame checked and byte-identical to the capture
page; the rig's apparent size is 0.2198–0.2201 across the clip; the frames
and the assessment are the second half of
[docs/probes/ot6/look/README.md](probes/ot6/look/README.md), composite
[follow-side-by-side.png](probes/ot6/look/follow-side-by-side.png).

## 11. What the viewport shows, and the collision toggle

The viewport draws the **tessellated solids** of the view's identity and
nothing else by default, and the model status line says so: it ends
`· showing: tessellated solids` (`#model-status[data-showing="solids"]`).
The simulation's **collision proxies** — the boxes, capsules, spheres,
cylinders and hulls the dynamics actually collide with — are offered by the
manifest's `collision` block, read from the MJCF the view already retains
at its own identity (ADR-333), and drawn only while the checkbox labelled
**show collision geometry** in the model controls is on. They are drawn as
outlines in `--warn` (§4), with the depth test off so they read through the
solid they belong to, parented to that solid so a pose moves both; the
status line then ends `… with collision proxies (n outlines from <source>)`
(`data-showing="solids+proxies"`), and each component's line in the list
says what it has (`collision: 1 box`, `none declared`, `not retained`).
When no export is retained the toggle is disabled and the note beside it
says why. The reader's choice survives selecting another run; a reload
starts with it off. The checkbox is 18 px inside a `--control`-high label,
so it is a finger target on a phone (§5).

A **recording** never contains proxies: the renderer hands the capture the
solids alone and refuses to publish if the capture reports anything else.
Each new video records `showing` and how many proxies were *not* drawn, and
the identity strip under the clip (§2, region 5) ends `· showing …`; a
recording made before that was recorded says `showing not recorded`.

Measured on the fixture project whose proxies differ from its solids
(`test_browser_shows_solids_by_default_and_proxies_only_under_the_labelled_toggle`,
`test_video_shows_the_solids_never_the_proxies_and_says_so`): off by
default; on, the drawn pixel box grows on every side; the decoded first
frame of the video is within the codec tolerance of the shared scene with
the proxies hidden and not with them shown. The real biped's screenshot with
the toggle on waits for D5's project, whose proxies will differ from its
printable parts; Lark's are boxes the size of its box parts.

## 12. The desk frame: two sidebars and a stage

At the owner's direction on 2026-09-14 (ADR-342) the desk layout stopped
being a document with a run list beside it and became an application frame.
Below 1000 px nothing in this section applies, except on a phone held
landscape (§13): the frame's containers are `display: contents`, and the
regions read as the one column of §2 and §6.

**Shape.** A **top bar** 44 px tall — toggle, project name, accepted
identity (one line, ellipsised), freshness, toggle. Beneath it a **left
sidebar**, the **stage** and a **right sidebar**. Bar and sidebars are one
`--surface` with no rule between them; the stage is a `--bg` sheet with a
12 px radius and a 1 px `--rule` border, set 6 px (`--frame`) into that
surface. So where a sidebar meets the bar, the corner the eye sees is the
stage's rounded one, and the viewport's sky is the stage's own background.

**Sidebars, organised by type.** The left sidebar is *what to look at*:
*Runs*, then *Documents and decisions*. The right sidebar is *what it is*:
*Identity*, *Model settings* (the collision toggle and the component list),
*Training and rollout*, *Parameters and specs*, *Artifacts*. Sections are
ruled, not carded, and each folds under its heading. A new information,
setting or parameter module belongs in the sidebar of its type, never on the
stage.

**Resizing and folding.** Each sidebar's inner edge is a 10 px
`role="separator"` handle centred on the gap. Dragging it sets the width
(never under 200 px, never so wide that the stage falls under 360 px); the
edge stays where it was grabbed rather than jumping to the pointer. Dragged
under 120 px, the sidebar folds to nothing and the stage takes the room;
dragged back out past that point it opens under the pointer. A drag that
ends folded keeps the width from before it. Double-clicking a handle, Enter
on it, or the top bar's toggle folds or opens that side; arrow keys move the
edge 16 px (64 with Shift). Widths animate over 180 ms except while dragging.
The canvas redraws when its box changes, so the model is never stretched
during a drag.

**The stage** always holds one panel: the **Concept** sheet when the project has one (§14), otherwise the **Model**. In the Model panel the canvas
fills it, the model status floats top-left and the orbit hint and *Fit*
bottom-right, both as translucent `--bg` pills. Its tabs are **Concept**, **Model**,
**Curves** (a dot in the telemetry state's colour), **Videos** (the count of
playable clips), **Evaluation** (a dot in the verdict's colour, §17) and,
while one is open, **Document** — a document opened
from the left sidebar comes onto the stage and leaves it when the view
changes or its tab is closed. Inactive panels are `visibility: hidden`, not
removed, so the canvas keeps its size and videos keep loading. Future
centre content — plots, comparisons — is another tab, not another region.

**What is remembered.** The two widths, whether each side is open, and which
sections are folded, in this browser's `localStorage`, and nothing else. It
is the reader's layout, not project state; a private window simply starts at
the defaults.

**Held by** `test_rendered_page_follows_the_spec[desk]` (bar height, the
three columns edge to edge, the canvas filling the stage, no page scroll)
and `test_desk_sidebars_drag_fold_and_the_stage_changes_what_it_shows`, which
drags a handle with a real mouse (width and backing store follow), folds
it shut by dragging, reopens it from the bar at its previous width, folds a
section, switches the stage to *Curves*, opens a document onto the stage and
watches the view change take it off, and reloads to find the layout kept.
§7 and §8 remain the measured record of the two-column page this replaced.

## 13. A phone held landscape

A phone turned sideways is 600–999 px wide and no more than 560 px tall. At
that size the one column of §6 gives the model a strip of a few hundred pixels
and makes everything else a long scroll. So there the page uses the desk frame
of §12 instead (ADR-344), sized for a short screen:

- The top bar is 40 px and the frame inset 4 px. The model and its tabs take
  the whole width, and the page does not scroll.
- **The sidebars are drawers.** Both start closed. The bar's toggles slide one
  in over the model, a `--surface` sheet with a 12 px inner radius and a
  shadow, at its §12 width capped to leave 72 px of model beside it. Opening
  one closes the other. A tap on the dimmed model beside it closes it. Its
  inner edge still drags to resize it, and dragging it under 120 px closes it.
  The model is never narrowed, so opening a drawer never re-frames the view.
- Which drawer is open is not remembered: turning the phone or reloading
  starts with the model alone. Widths and folded sections are shared with the
  desk layout.
- To fit the short stage, the orbit hint is dropped, the model status is held
  to two lines, and clips sit in 260 px cells no taller than the stage.

Portrait is unchanged. A phone upright reads the column of §6, and a tablet
or desk window taller than 560 px keeps its own layout.

**Held by** `test_landscape_phone_gets_the_frame_with_drawers_over_the_model`,
at 844 × 390 under touch emulation. It checks the frame, the full-width model
and no page scroll with both drawers closed and off screen. It then taps
drawers open and verifies that the model's width is unchanged, that only one
drawer is open at a time, that a tap on the model closes a drawer, and that
one finger still orbits without moving the page.

## 14. The concept sheet leads the page (ADR-430)

Under the ot10 charter (A6) a project is presented before it is inspected.
`cadex render` draws a **concept sheet** beside the studio hero
(`docs/CLI.md`, *The concept sheet*): one 1536×1024 PNG with the hero on
the left and, on the right, the project's name, its revision, three key
numbers (mass, servo count, size), a swatch per appearance role, the
`front`, `right` and `top` views as line drawings, and A1's proxies. It is
drawn on the dark scene (ADR-444, §16): paper is the viewport's `#141414`,
ink the page's `--ink`, labels `--ink-2` and rules `--rule`, and the hero on
its left stands on the prototype mat. It was a light sheet until ot10 A8.

**Where it sits.** The stage's first tab is **Concept**. When
`/api/project` carries `presentation.available`, the stage opens on it once,
on the first poll that finds one; after that the reader's choice of tab
stands, and polls never pull the stage back. The panel shows the sheet
scaled to the stage (never above its own size), a status line naming the
revision it was drawn from — *the accepted design* when `relation` is
`current`, otherwise the relation in words, so an earlier design never
reads as this one — and a caption with the name and the three numbers, a
link to the hero at full size, and a download. Clicking the sheet opens it
at full size. Without a sheet the tab stays, and says what makes one;
the stage opens on the model as before.

**On a phone** the Concept card comes before the Model card in the column
(same `order`, earlier in the source), the sheet at the column's width.

**Held by** `test_the_page_leads_with_the_concept_sheet_when_the_project_has_one`
at both charter sizes (the stage opens on *Concept* at desk with no page
scroll; the card precedes the model on the phone with no horizontal
overflow; the image is the served sheet at its natural 1536 px; the caption
reads the numbers), and by `cli/tests/test_sheet.py` for the sheet's shape,
identity, numbers and routes.

## 15. Policy videos are drawn in the studio look (ADR-431)

Under ot10's W1, a run's video is drawn by default in the design's studio
look (`python -m cadex_cli.video --project P --run R`, `--style studio`).
It uses the hero view and the design's own materials, on the dark prototype
mat (§16) with a contact shadow, and has a timer at the bottom left. It is
drawn on the CPU with no browser. The Videos tab (region 5) plays it
exactly as it plays a scene-style clip. The identity strip names the style
(`studio`, or the scene's `cadex-prototype-dark-v1`), so a reader can tell
the two apart. The dark viewport and its capture (§10) are unchanged, and
`--style scene` still records in them. Since ADR-444 a studio clip stands on
the same floor as the viewport, so its grid is anchored at the world origin
and the robot's stride and any foot slip read against it.

A studio clip stands on the design's floor (ADR-432). When the render
summary names an environment, that environment is not drawn, and the shadow
falls on its top face. So a robot whose solids sink through the floor
(the rollout collides on proxies) is drawn sinking, rather than floating
above a shadow at the lowest reach. The clip draws the rollout's own solids
within a triangle budget, and says how many it read and drew.

**Held by** `test_dashboard_serves_the_studio_video_it_lists` (listed with
its style, served byte for byte as `video/webm`) and the studio tests
beside it in `cli/tests/test_video.py`.

## 16. One scene for every image (ADR-444)

Under ot10's A8, every image Cadex presents is drawn in the viewport's dark
scene: the studio hero, the four review views, `look`, the concept sheet
(§14) and the studio video (§15). The floor is the prototype mat §10 draws —
`PALETTE.scene.bg` `#141414`, tiles `#1c1c1c` / `#232323` and the `#3a3a3a`
major line — and the sheet's chrome is this page's `--ink`, `--ink-2` and
`--rule`.

**One source.** The engine's `CadexStudio.PALETTE` (ADR-445) is the table
every image is drawn with, in the CLI and in the shell. A browser cannot
import Python, so `review_static/environment.js` (`PALETTE`) and
`review_static/review.css` (`:root`) carry the same colours, and
`cli/tests/test_scene_palette.py` fails when either drifts from the engine.
Change a colour in the engine and in both files together; no CLI module
carries a scene colour of its own.

**The floor.** The CPU renderer (`CadexStudio._floor`) intersects each
orthographic ray with the floor plane: a checker one pitch square, the
major line on every multiple of the pitch anchored at the world origin, the
pitch chosen by `floor.js`'s own `chooseGridPitch` ladder for the framed
span, and each line's pixel coverage computed from the floor footprint of
the pixel, which antialiases it. The mat fades into the background between
0.75× and 1.9× the framed extent from the point under the image centre. A
level view (`front`, `right`) sees no floor and draws the background. No
minor lines and no baked labels: at a hero's framing they are noise.

**The shadow** is the measured contact shadow (§15, ADR-432), deepened for a
dark floor — it may take a tile to 20 % of its brightness (was 45 %). On
`ot10-quadruped-3`'s hero the tiles at its feet fall from 28–35 to 6.

**Not changed.** The judge: A1's frozen procedure keeps its rubric, and no
probe is re-scored (ADR-444). The viewport and its capture (§10) are the
source, not a consumer, and are unchanged.

**Held by** `cli/tests/test_scene_palette.py` (the renderer's palette is the
viewport's, parsed independently, and the charter's values; the ladder and
line width are `floor.js`'s; no image module carries a scene colour; the
hero stands on the mat and fades; a changed viewport palette changes the
drawn image; the studio video's identity covers the palette source), with
the shadow held by `test_contact_shadow_darkens_the_floor_under_the_design_only`.
Before/after: `docs/probes/ot10/a8-*.png`.

## 17. The evaluation: a verdict, its tables and its film (ADR-459)

Under the ot11 charter (P2) the page shows what `cadex evaluate` wrote
(`docs/CLI.md`, *Evaluating a policy against its success spec*): one policy
held to its task's success spec on every frozen seed. It answers a question
the curves cannot: **did the policy do the behaviour, and if not, which
measurement says so?** A reward curve is not on this panel's first screen,
and the reward table says in words that no predicate reads it.

**Where it sits.** The stage's fifth tab is **Evaluation**, after *Videos*;
on a phone it is the card after the videos in the column (region 5a). Its
tab carries a dot in the verdict's colour — `--ok` for pass, `--bad` for
fail, none when the project has no evaluation — so the verdict is read
without opening it. The stage never opens on it by itself.

**Which one is shown.** `/api/project` lists the project's evaluations as
summaries; the panel shows one, fetched whole from
`/api/evaluation/<name>`. It is the reader's pick if they made one; else
the newest evaluation of the selected run's policy; else the newest at the
accepted revision; else the newest. With more than one, a row of buttons
under the status line names each by revision, policy, verdict and relation,
newest first, the shown one pressed.

**Reading order**, top to bottom:

1. **The status line** (`#evaluation-status`): the verdict and the seed
   tally in the verdict's colour, the policy and task, the revision and
   whether it is the accepted design — *historical: not the accepted
   design* when it is not, so an old evaluation never reads as this design's
   — when it was evaluated, and what failed, worst first. Without an
   evaluation it says what makes one.
2. **Predicates**: one row each — id, metric, bound, seeds passing, and the
   lowest, median and highest value over the seeds. The tally is `--ok`
   only when every seed passed it.
3. **Seeds**: one row each — seed, verdict, how and when the episode ended
   (`tipped at 6.26 s`, `horizon at 10 s`), then one column per predicate
   holding that seed's value, coloured by whether it met the bound, the
   reason in its tooltip. A filmed seed's number is underlined and jumps to
   its film.
4. **Behaviour metrics**: every metric the evaluation measured, a row each,
   a column a seed.
5. **Reward by term**: a row a term and the total, a column a seed, under
   one muted line: what the policy was paid, not what it is judged by.
6. **Film**: for each filmed seed, the overview sheet, the detail sheet and,
   for the first, the video, each captioned with its frame count, time span
   and view. A sheet opens at full size in a new tab. The note above says
   the film stands on the dark prototype floor and where the materials came
   from, or why there is no film.
7. A link that downloads `evaluation.json`.

**Type, colour and shape.** Sub-headings are `h3` at `--fs-1`, 600, with no
rule: the panel's own `h2` is the only ruled heading, and it is hidden at
desk as every stage panel's is. Tables are the page's `table.grid` with
cells at `--fs-0`, set not to wrap, each inside a `.scroll` wrapper: a
ten-seed, eleven-predicate table scrolls inside its card and never widens
the page. Pass and fail are text in `--ok` and `--bad` on the panel's
surface, never a filled cell. Numbers are five significant figures with no
trailing zeros. The sheets and the video are drawn on the scene's `#141414`
with the page's 1.5 px `--rule` border and 10 px radius, at the column's
width on a phone and never above their own size at desk. Nothing is
smaller than 12 px.

**Poll cost.** The list is a summary of each report, parsed once per file
identity on the server; the panel redraws only when the list's names,
stamps or relations change, or the shown one does.

**Held by** `cli/tests/test_review_evaluation.py` at both charter sizes,
with ot10's `w2-2` shuffle as the failing fixture: the status line, all
eleven predicates' tallies, ten seed rows with their endings and
per-predicate values, the metric and reward tables, the film's images and
video, the tab's dot, no page scroll at desk, the seed table scrolling
inside its card on the phone with no horizontal overflow, and nothing under
12 px; the reader's pick holding across a poll; and a project with no
evaluation saying what makes one. `test_rendered_page_follows_the_spec`
holds the heading and the reading order.

## 18. Steering: the parameter slider (ADR-503)

The page's first write. On the accepted view, every declared number with a
finite `min` below its `max` is a range input in the *value* column of
`#params`, stepped by the declaration's `step`; a parameter never set reads
at its default and says `(default)`. A run's parameters are a record and
stay text: only the project as it stands now can be changed. Dragging moves
the number beside the slider and nothing else; **releasing** it is one
write — `POST api/params` with `{"values": {name: value}}` — so a drag is
one `cadex params --set`, never one per pixel. While it runs every slider
is disabled and `#params-write` says the command being run; it then says
the accepted revision and two times, the child's and release-to-drawn, in
the page's ok colour, or the CLI's own refusal in its bad colour. The poll
that follows the reply reloads the model, because the accepted revision
moved; the table is never rebuilt under a write in flight, so a poll does
not snatch a slider from the hand moving it.

The server has no write path of its own (charter A3): the POST runs
`cadex params --project <root> --set NAME=VALUE --json` as a child, as
`cadex walk` runs a leg, without `--wait`, so a project held by another run
is refused (409) rather than queued, and the `PROGRESS.md` row and the
project commit are the CLI's. Every POST, under `/` and `/p/<name>/`,
needs the per-launch token the server writes into the
`<meta name="cadex-write-token">` of the page it serves, sent as
`X-Cadex-Token`; a browser's `Origin`, when sent, must be the server's own
`Host`. Both checks run before routing, so an unknown path is refused, not
found. The server binds 127.0.0.1; another device reaches it through
`tailscale serve` in front of it.

Measured on 2026-10-03, a one-box plate on the dev tree, headless
Chromium, n=20: slider release to the rebuilt model drawn, p50 548 ms,
p95 556 ms; the `cadex params` child alone, p50 0.534 s, p95 0.542 s.
Beside it, `cadexd_latency_integration.py` on the same machine: warm
`set_params` median 0.382 s, with display 0.482 s, against its 0.65 s bar.
The cold child costs about 50 ms over a warm engine on this model, which
is why the server keeps none; a heavier project is where that would be
measured again.

## Operator run status (ADR-387)

The operator deployment adds a compact bottom-right status strip with run name,
iteration, loop state and project name. It uses the dark chrome palette and
12 px text, and reloads the page on project changes so prior-project videos,
documents and camera state do not carry across. When the configured run has no
dispatched project, show a waiting message instead of the previous model. This
strip belongs to the operator launcher; ordinary single-project review keeps
its existing layout. See `OPERATOR-REVIEW.md` for the selection contract.
