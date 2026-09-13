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
measured, and §8 what it looks like following it (ADR-329), measured the same
way on the same operator URL.

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
| 1 | **Run selection** | `#sidebar`, `#runs`, `#runs-summary`, `#current-run`, `#views li[data-run]` | Which view is shown: *Accepted now*, then every recorded run with its relation (current/historical) and status. The current run is marked. A sidebar at desk width; a collapsible run list under the masthead on phone (§6). |
| 2 | **Identity** | `#identity`, `#view-kind`, `#view-relation`, `#view-status`, `#view-revision`, `#view-digest`, `#view-identity-source`, `#view-recorded`, `#policy-origin`, `#view-note`, `#view-policy-store` | What the rest of the page is about. Kind and relation as chips, then the key/value block. |
| 3 | **Model** | `#model`, `#model-status`, `#viewer`, `#model-fit`, `#model-components` | The accepted revision's tessellated solids in the shared environment (§4), orbit by pointer or touch, fit control, and — once D4 lands — the labelled collision-proxy toggle, off by default. |
| 4 | **Curves** | `#curves`, `#telemetry`, `[data-metric]`, `[data-history]`, `#checkpoint-source`, `#checkpoints` | Training telemetry: the five metrics as a stat row, the three histories (reward per step, loss, episode length) as curves side by side on desk and stacked on phone, then checkpoint provenance. |
| 5 | **Videos** | `#videos-region`, `#videos`, `#videos li[data-video]` | The run's recorded clips, playable inline and downloadable, each captioned with its identity strip (revision, style, policy, seed) and — once D4 lands — what it shows. |
| 6 | **Record** | `#record`, `#training`, `#params`, `#params-note`, `#artifacts`, `#problems`, `#disk`, `#docs`, `#decisions`, `#doc-view` | The appendix: training request and receipt, parameters and specs, retained artifacts and disk use, document snapshots and decisions. Full tables at desk width; on phone each table scrolls inside its own card, never the page. |

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
  `repeat(auto-fit, minmax(240px, 1fr))` grid: abreast at the 1400 px
  reference width, two then one as the column narrows (a 1000 px window has
  a 616 px column, where three 240 px minima would overflow), stacked on
  phone. The five metrics above them are a stat row of tiles whose text
  stays `key: value`, which is what the other suites read.
- **The viewport** keeps a 16:9 box at desk (`aspect-ratio: 16 / 9`, up to
  620 px tall) and 4:3 on phone, always the full width of its column, with
  `touch-action: none` so a one-finger drag orbits instead of scrolling the
  page. The canvas backing store follows the box, so the model is never
  stretched. **Orbit is by pointer events** (ADR-330): one pointer — mouse
  or finger — orbits, two fingers pinch-zoom, the wheel zooms, and the
  canvas captures the pointer so a drag that leaves it still orbits. The
  Fit button restores the framing.
- **Video** elements are the full width of their card with the same radius as
  the viewport; the caption sits beneath, never overlaid, and leads with a
  **Play / Pause control of the page's own** (`[data-video-play]`, a
  `--control`-height button) because the native controls' tap targets differ
  from phone to phone; the native controls stay for scrubbing. The download
  link is the caption's last item.

## 6. Breakpoints

Two, chosen from the two widths the charter measures against and the one in
between where a sidebar stops paying for itself.

| Range | Layout |
|---|---|
| **≥ 1000 px** (desk; 1400 is the reference width) | Two columns: run selection as a 280 px sidebar, sticky under the masthead; regions 2–6 in the detail column. Curves three abreast. Masthead on one row. |
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
3. **The viewport fills its column**: canvas width ≥ 90 % of the detail
   column at desk and ≥ 90 % of `innerWidth − 2·gutter` on phone.
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
