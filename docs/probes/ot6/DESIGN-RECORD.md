# The ot6 dashboard design record (2026-09)

> **Historical (moved out of docs/DASHBOARD.md 2026-10-27, ADR-828).** The
> measured record of the page before and after the first design spec
> (ADR-501), formerly DASHBOARD.md §7–§9. Frozen evidence; the page has moved
> on, and docs/DASHBOARD.md is what is true now. Screenshots are in
> `review-design/` beside this file.

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

A design test's rendered-page half asserted §6's
five invariants at both sizes on a fixture project and pinned the receipt
above to this table, until ADR-725 deleted it.

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
12 px gutters.

## 9. Evidence for D1 and D2

**D1** has this document; the before and after screenshots at the two sizes
beside it (§7, §8); and the operator URL receipts showing the design on the
active project and run (§8). The viewport's half of "one palette" is §10:
the light scene is removed (ADR-331) and the viewport's background is the
page's.

**D2** is the phone: §8's and §8a's receipts are the page of the time on the
operator URL at 400 × 850, with the recorded one-finger orbit and Fit tap and
the region screenshots. The browser tests that held both at the time were
deleted by ADR-725.

What the evidence is not: a physical phone. Headless Chromium's touch
emulation and its gesture recogniser are what is measured, and one of that
recogniser's behaviours is recorded in the capture script — a tap landing
within a few hundred milliseconds of a drag's end is dropped, on a device as
under emulation, so the script lets a second pass before tapping Fit.

Every receipt ships under `docs/probes/ot6/` within the charter's caps
(16 KB per receipt, 200 KB per image).

