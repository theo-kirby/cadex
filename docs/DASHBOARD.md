# DASHBOARD.md — The dashboard, Cadex's only UI

Verified against source: 2026-10-04. [Cadex-new]

This is the design specification for the dashboard: the pages `cadex app`
and `cadex review` serve (`cli/cadex_cli/review_server.py` and
`review_static/`, ADR-286), the second of Cadex's three parts (ADR-500) and
its only UI since the Blender shell was deleted (ADR-498). It replaced
`docs/REVIEW-DESIGN.md` (ADR-501). It is the
contract the pages are held to by `cli/tests/test_review_design.py`: the
page follows the spec, and when the page has to change, the spec changes in
the same commit. What the server *reads* — the routes, the permitted-paths
rule — is `docs/CLI.md`; this document is about what the pages show, how
they are laid out, typed and coloured, and why.

The dashboard stays light (charter A2): a standard-library Python server,
vanilla JS and the vendored three.js — no npm, no bundler, no build step,
no front-end framework. The project directory is the truth (A3): the page
reads it and writes nothing (ADR-537). The agent working the project -- any
agent, through the CLI or `cadex mcp` -- changes it, and the page follows.

**The pages are cut to the minimum (ADR-533).** On 2026-10-04 the owner had
every panel removed that watching and steering a design does not need, to be
added back one at a time as the need shows. What is left is two pages: the
index of projects and a project. The server's read routes are unchanged, so
every API the removed panels read — runs, telemetry, videos, evaluations,
comments, notes, exports, sections, drawings, documents — still answers, and
the CLI and the agent still use them; adding a panel back is page work only. The sections the cut emptied are gone from this file and
kept in its history; the ones that remain keep their numbers, so a `§`
reference elsewhere still lands. §7 and §8 are the measured ot6 record of
the page before and after the first spec, kept because the tests check them.

**The project page is the app (ADR-534).** The same day the owner asked for
the page to stop being a dashboard and be the app, in Blender's design
language: the screen is tiled by **areas**, each showing one **editor** —
the 3D viewport and the 2D viewport — and each area can be
resized, moved, split, maximized or closed (§12). There is a light theme
beside the dark one (§4), and the 3D viewport draws shaded by default or as
a hairline diagram (§10). Still no build step: `layout.js` tiles the
screen, `theme.js` picks the theme, and both are plain scripts.

**The settings are a menu bar (ADR-539).** File, Revisions and View sit in the top bar as dropdowns, and the screen is one 3D viewport by default.

**The page is read-only (ADR-537).** The owner's interface is now an agent
of their choice -- Claude Code, Codex, Pi -- driving the engine through the
CLI and `cadex mcp`, with this page beside it as the view. The Chat editor,
the parameter sliders and the revision verdicts are gone, and the server
has no write route (§18).

## 1. Purpose

The app answers one question for one person: **what does the design look
like now?** The reader is the owner, at a desk or on a phone, watching what
the agent produced while it works; they steer it in the agent's own
interface and never model by hand (VISION's non-goals). The page writes
nothing (§18), on a server bound to 127.0.0.1 (§22).

- **The model is the subject.** The 3D viewport is the largest area in the
  default layout and the first tab on a phone.
- **The layout is the reader's.** Every editor lives in an area the reader
  can move and size; the layout is kept in their browser, not the project.
- **Nothing that is not needed.** No identity block, no hashes in the
  chrome. The top bar says which project and which revision.

## 2. Hierarchy

**Index** (`/`, `projects.html`): the top bar, then **Projects**, newest
accepted first, 20 to a page. Each row is the name, linking to its page, and
a muted date; **Newer** and **Older** page through them, and the page number
is kept in the URL (`?page=N`).

**Project** (`/p/<name>/`, or `/` under `cadex review`): the top bar over
the screen (`#screen[data-mode]`), which `layout.js` tiles with areas
(`.area[data-area][data-editor]`, §12). Each editor's markup is parked in
`#editor-shelf`; an area takes its `.editor-tools` into its header and its
`.editor-body` below.

| Editor | `data-editor` | Element hooks (stable) | What it is for |
|---|---|---|---|
| **Top bar** | — | `#top`, `#home`, `#project-name`, `#accepted-line`, `#freshness[data-state]`, `#theme-toggle` | A link home (hidden under `cadex review`), the project's name, the accepted revision's ordinal and date, **live** or **offline**, and a light/dark toggle. |
| **3D viewport** | `view3d` | `#view3d-source`, `#view3d-style button[data-style]`, `#model-fit`, `#model`, `#model-status[data-state]`, `#viewer`, `#playback`, `#play-toggle`, `#play-time`, `#play-clock` | The accepted model or a run's, shaded or hairline (§10); orbit by pointer or touch; **Fit**. A run that kept a rollout trace plays it on the timeline. |
| **2D viewport** | `view2d` | `#view2d-source`, `#view2d-fit`, `#sheet-stage[data-kind]`, `#sheet-empty` | The project's drawings and presentation images (pan, zoom, double-click to fit), its documents (markdown, drawn as text only), and each run's training curves (reward, loss, episode length) as plots. |
| **Menu bar** | — | `#menubar`; `#file-panel` (`#project-select`, `#project-open`, `#project-all`); `#revision-panel` (`#revision-list li[data-revision][data-ordinal][data-current]`, `#revision-empty`); `#view-panel` (`#theme-choice`, `#style-choice`, `#layout-reset`) | File, Revisions and View in the top bar, each a `<details class="menu">` dropdown (ADR-539): open another project; the revision trail, read-only (§18); the theme, the render style and the layout. One opens at a time; a click outside or Escape closes it, and with one open, hovering another opens that one. On a phone the dropdown spans the screen between the gutters. |

The element ids and `data-*` attributes above are the hooks the CLI suite
pins.

## 3. Type scale

One family, one scale, one line height.

| Token | Size | Weight | Use |
|---|---|---|---|
| `--fs-0` | 12 px | 400 | captions, chips, monospace identities, table footers |
| `--fs-1` | 14 px | 400 | body, table cells, controls; section headings (`h2`) at 600 |
| `--fs-2` | 17 px | 600 | the page title (`h1`) in the top bar |
| `--fs-3` | 22 px | 600 | reserved; nothing uses it now |

The top bar title is `--fs-2` at 600 and a menu name `--fs-1` at
400; the scale does not change with the width.

- **Family**: `--font: system-ui, "Segoe UI", "Helvetica Neue", Arial, sans-serif`;
  identities in `--mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace`
  at `--fs-0`. No web font is loaded: the page must render on a private network
  with no outbound fetch.
- **Line height** 1.45 throughout. Numbers use `font-variant-numeric:
  tabular-nums` so stat rows and tables align.
- **Headings are sentence case, never uppercase**, and carry no number.
- The scale is the same at both breakpoints. Phone readability comes from
  layout (§6), not from shrinking the type: nothing on the page is smaller than
  12 px at any width, and the viewport meta stays `width=device-width,
  initial-scale=1` so the phone renders CSS pixels 1:1 and never zooms out to
  fit.

## 4. Palette

**Dark by default, light on request (ADR-534).** The chrome tokens below are
the dark theme, chosen so that the page background *is* the scene background:
the viewport is a window onto the same near-black place the videos are
captured in. The environment module keeps its one dark palette (ADR-331):
the shaded viewport and every capture stay in it whatever the theme, as a
Blender viewport keeps its own colour under a light interface.

The light theme overrides the same token names under
`:root[data-theme="light"]`: `--bg` #cfcfcf, `--surface` #f4f4f4,
`--surface-2` #e6e6e6, `--surface-3` #d9d9d9, `--rule` #c4c4c4,
`--rule-strong` #a8a8a8, `--ink` #1c1c1c, `--ink-2` #5c5c5c, `--accent`
#262626, `--ok` #18794a, `--warn` #8a6100, `--bad` #b42318, `--info`
#0b7285. Two tokens beyond the table follow the theme too: `--select` (a
pressed button, the drop hint) and `--paper` / `--paper-ink` (the hairline
diagram, §10). `theme.js` sets `data-theme` before the first paint from the
browser's stored choice — dark, light or the system's — and every page
loads it.

The base is the greyscale of the `neural-whoop` reference studio (its `:root`
dark set) and of the one `PALETTE` in
`cli/cadex_cli/review_static/environment.js`, which carries the reference's
dark tile and scene values and nothing else (ADR-331).

| Token | Value | Used for | Equals |
|---|---|---|---|
| `--bg` | `#141414` | page background | `PALETTE.scene.bg` (`0x141414`) — chrome and viewport share it |
| `--surface` | `#1b1b1b` | an area's body | reference `--panel` |
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

- Page gutter `--s5` at desk, `--s3` on phone. Sections are separated by a
  `--rule` hairline, not boxed in cards.
- **Shape**: `--radius-sm` 8 px on controls, `--bw` 1.5 px borders.
- **Controls**: minimum 40 × 40 px hit area on touch (`@media (pointer:
  coarse)`), 32 px on desk; `--surface-2` fill, `--rule` border, `--surface-3`
  on hover, `--rule-strong` on focus. No native chrome on buttons.
- **Areas** have a 6 px radius (`--radius-area`) and a 4 px gap (`--gap`)
  between them on `--bg`; an area's header is 32 px on `--surface-2`, its
  controls 24 px.
- **The viewport** fills its area's body, with `touch-action: none`
  so a one-finger drag orbits instead of scrolling the page. The canvas
  backing store follows the box, so the model is never stretched. **Orbit
  is by pointer events** (ADR-330): one pointer orbits, two fingers
  pinch-zoom, the wheel zooms, and the canvas captures the pointer so a drag
  that leaves it still orbits. **Fit** restores the framing, framing the
  design's bounding sphere; a part the engine calls world geometry (a task
  floor, `world=True`) is drawn but sizes nothing (ADR-525).

## 6. Breakpoints

One.

| Range | Layout |
|---|---|
| **≥ 700 px** (desk; 1400 is the reference width) | A 40 px top bar over the screen, tiled by areas (§12). The page never scrolls; each editor scrolls on its own. |
| **< 700 px** (phone; 400 × 850 is the reference size) | One editor fills the screen, the 3D viewport first, and a tab bar at the bottom picks it. `--s3` gutters below 600 px. |

The index and a run's page are one column, at most 760 px wide, at every
width.

Invariants at every width, and the ones the design test asserts on the
rendered page at 1400 × 900 and at 400 × 850 with touch emulation:

1. **No horizontal page overflow**: `document.documentElement.scrollWidth <=
   innerWidth`, achieved by `min-width: 0` and fixed table layout, never by
   `overflow-x: hidden` on the body.
2. **The layout viewport is the device width**: `innerWidth === 400` at phone
   size. §7 shows what happens when it is not.
3. **The screen fills the window**: below the bar to the bottom edge, and the
   page does not scroll. At desk the default layout's four areas tile it
   without overlapping; on a phone the one area is the 3D viewport and the
   canvas is the full `innerWidth`.
4. **The palette tokens of §4 are the computed values** on the rendered page,
   in the default dark theme; the light theme survives a reload.
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

**Render styles (ADR-534).** The 3D viewport draws **shaded** by default —
the lit stage below, the one every capture uses — or **hairline**: a
diagram of silhouettes and creases in `--paper-ink` on flat `--paper`, with
no floor, shadow or fog. The hairline is one screen-space pass in
`review_scene.js` (`setStyle`): the solids' view normals and depth are drawn
offscreen at twice the canvas's resolution (at most 16 Mpx), ink goes
wherever either jumps between neighbouring pixels — depth for silhouettes,
inked on the nearer side only, and a normal turn of more than about 37° for
creases — with a hard threshold, and the canvas takes the mean of each 2×2
block, so a line is one crisp pixel with its stair-steps smoothed. A
tessellated fillet, whose facets turn by less, stays clean. The choice is the
browser's (`cadex.render`); a capture never uses it.

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

## 12. The screen: areas and editors (ADR-534)

After Blender's screen. The screen is a tree: a split (`row` or `col`, with
each child's share) or an area showing one editor. The default is one 3D
viewport over the whole screen (ADR-539); split it to bring in the 2D
viewport. The settings live in the menu bar (§2), not in an editor.

- **Resize**: drag the 4 px gutter between two areas; it moves that boundary
  only, and no area goes below 120 px.
- **Pick the editor**: the dropdown at the left of an area's header. Each
  editor shows at most once, so picking one already shown swaps the two areas.
- **Move**: drag an area's header (its grip or any empty part of it) onto
  another area. A drop on an edge docks it on that side, splitting the target;
  a drop in the middle swaps the two. A hint shows where it will land.
- **Split, maximize, close**: the four buttons at the right of the header.
  A split opens an editor not shown yet beside the area, so with both
  shown there is nothing to split. Maximize (or Ctrl+Space over the area)
  gives the area the whole screen until it is pressed again. The last area
  cannot close.
- **Kept**: the layout is this browser's (`localStorage`
  `cadex.layout.v3`; earlier keys held the Chat and Settings editors); View → Layout → **Reset** in the menu bar returns the
  default. A browser that refuses storage gets the default every visit.

An editor's markup is never rebuilt by a layout change: the area moves the
editor's own elements, so a canvas keeps its WebGL context. Below 700 px there is no tiling (§6).

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
(`cadex render`) and the studio video (§15). The floor is the prototype mat §10 draws —
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

## 18. Read-only: the agent changes the project, the page follows (ADR-537)

The server answers GET and HEAD and nothing else: any other method, on any
route, is 501, and the served page carries no token. The page's 2 s poll of
`api/project` notices when the accepted revision moves -- a `cadex params`,
a `write_script` through `cadex mcp`, a `cadex revision restore` -- and
reloads the model then. The Revisions menu keeps `#revision-list`, the stored trail
newest first, numbered by ordinal, **current** for the accepted one and when
it was accepted for the rest; each row carries `data-revision`,
`data-ordinal` and `data-current`.

What the page once wrote is the CLI's alone now, where an agent reaches it:
`cadex params --set` for the slider (ADR-503), `cadex mcp` or the agent's
own session for the chat (ADR-504), `cadex comment` (ADR-505), `cadex
revision accept|reject|restore` (ADR-506), `cadex export` (ADR-509) and
`cadex section`. The listings those commands leave -- exports, sections,
comments, notes -- still answer under `api/project`.

## 22. Remote viewing: `tailscale serve` in front of 127.0.0.1

The dashboard binds `127.0.0.1` by default (`cadex app`, `cadex review`,
`serve_projects` and `serve` all default to it), so nothing off the machine
reaches it. To watch from a phone or another computer on your
tailnet, leave it on loopback and put Tailscale's HTTPS proxy in front of
it, on the same machine:

```bash
pixi run app                     # 127.0.0.1:8765
tailscale serve --bg 8765        # https://<machine>.<tailnet>.ts.net/ -> 127.0.0.1:8765
tailscale serve status           # what is being served
```

Only devices on your tailnet can open that URL, and Tailscale terminates TLS.
Mount it at the root as shown: the page's URLs are relative to the project page, but
a sub-path mount is not tested. There is nothing to write behind the proxy
(§18), but the page still shows the whole project to whoever opens it. Do not use `tailscale funnel`, which publishes to the internet, and do not
pass `--host 0.0.0.0`.
`--host <tailscale address>` (`docs/CLI.md`) binds the tailnet address
directly without TLS, and is the older path. Cadex's own runs never start
`tailscale serve`. It is a step the owner takes.

**Over a remote link the model is the weight (ADR-535).** An accepted model
is one binary STL per component, 28 MB for a 45-part arm, and each one was
sent uncompressed with `no-store` and rebuilt per request. That request
re-derived the whole model manifest, hashing every BREP of the attempt, so
one load cost about 2 s of server CPU and 28 MB on the wire, every time the
model was opened or moved. Now:
- the manifest is remembered until the project manifest, the attempt's
  `result.json` (both by content) or its tessellation and trace (by stat)
  move;
- each converted mesh is kept by its tessellation's content hash, and that
  hash is its `ETag` (`Cache-Control: no-cache`), so a browser revalidates and
  a part a rebuild did not touch answers 304;
- any JSON, text or STL response of 1 KB or more is gzipped for a client
  that accepts it. That arm is 9.3 MB, and the projects listing 100 KB
  instead of 1.1 MB.

The page aborts a load a newer one supersedes, tries a failed request twice
more, keeps the last model drawn until the next is complete, and retries a
failed load on later polls with a growing wait. A slow model never holds up
the 2 s project poll.

Measured on a link emulated at 30 Mbit/s and 40 ms (Chromium, the 45-part
arm): first load 9.1 s → 3.9 s, reopening the same model 8.2 s → 0.8 s.
