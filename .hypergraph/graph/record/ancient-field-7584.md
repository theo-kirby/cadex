---
node_id: 80183d28-4879-54aa-b0c5-1d69f3275aad
slug: ancient-field-7584
title: 'Review dashboard design spec: measured before at 1400 and 400x850, receipt caps enforced (D1 started)'
created_at: '2026-09-13T21:35:27+00:00'
parents:
- brisk-ledge-9638
summary: ''
artifacts:
- docs/REVIEW-DESIGN.md
- docs/review-design/before-1400.png
- docs/review-design/before-400x850.png
- docs/probes/ot6/design/before.json
- docs/probes/ot6/design/capture_before.py
---
## What

The review dashboard's design specification, `docs/REVIEW-DESIGN.md`: purpose, the six-region hierarchy with its stable element hooks, one type scale (12/14/17/22 px, one family, no web font), the dark-only palette whose page background is the environment module's dark scene background, spacing and shape, two breakpoints with five test-asserted invariants, and a measured "before" of the page as ot5 left it. Beside it, the before screenshots at 1400×900 and 400×850 (`docs/review-design/before-1400.png`, `before-400x850.png`, quantised under 200 KB), the capture script and its receipt (`docs/probes/ot6/design/`), and `cli/tests/test_review_design.py` pinning the spec's sections, the `--bg` = `THEME_PALETTES.dark.scene.bg` tie, the receipt-to-spec numbers, the PNG sizes, and the charter's evidence caps (16 KB per receipt, 200 KB per image, no private address or this machine's hostname). Doc index rows in `AGENTS.md` and `docs/CLI.md`.

## Why

The critic's message named this unit: start D1 (`floral-marsh-2830`) with the spec and the before screenshots, verify the operator URL, and record without claiming D1 closed. The charter's dashboard-first ladder (rung 0) supersedes the stale clearance and section bets in the plan, and no planner is running, so those bets were not taken. This does exactly what was asked; the one addition is the receipt-cap test, which the charter requires ("A test enforces the size caps") and which is cheapest to add with the first receipt.

## Method

1. Read `docs/VISION.md`, the page (`index.html`, `review.css`, `review.js`), the environment module and the read-only `neural-whoop` reference studio's `:root` dark token set (commit `31caeb28…`).
2. Captured the persistent operator page over the private address (passed as an argument, never committed) with the existing DevTools-pipe driver: 1400×900; 400×850 with `Emulation.setDeviceMetricsOverride(mobile:true)` and touch emulation; and a plain 400-wide window. Each capture waits for `cadexReview.ready`, a model state, and a non-loading freshness, then reads back layout and computed type sizes and the `:root` tokens.
   ```
   PYTHONPATH=cli:cli/tests pixi run python docs/probes/ot6/design/capture_before.py "http://<private-address>:8765/" ~/cadex-projects/ot6-design before
   ```
   Originals (SHA-256): `before-1400.png` `79cf693fe9de…`, `before-400x850.png` `fca8429d9a57…`, `before-400-desktop.png` `a189faf7bda9…`, in `~/cadex-projects/ot6-design/`. Committed copies are 256-colour quantised (280 480 → 107 812 bytes; 85 919 → 29 759 bytes).
3. Wrote the spec from the measurements and the reference tokens; computed the contrast ratios cited in §4 (ink/bg 15.7:1, ink-2/surface 6.1:1, status colours on surface-2 ≥ 7.8:1).
4. Wrote the test; ran it plus `test_review_server.py`, `test_review_style_evidence.py`, `test_project_docs.py`.

## Result

Measured on `ot5-lark-copy85` with `lark109-engine2` selected (the newest run), live, model loaded — the operator URL still serves the active project and run:

| | 1400×900 | 400×850 mobile | 400 plain |
|---|---|---|---|
| layout viewport | 1400 | **868** | 400 |
| horizontal overflow | 0 | 0 (of 868) | **468 px** |
| model canvas width | 1019 | **34** | **19** |
| page height | 3 993 | 28 772 | 29 053 |

The "sliver" has a mechanism: the 280 px fixed sidebar plus the detail column's min-content width (seven-column params table, artifacts table, unbroken identity strings) widen the layout viewport to 868 px, so a phone sees the sidebar and one word-per-line of the identity chips; the canvas is 34 px wide. At 1400 the chrome is blue-grey around a light viewport with uppercase grey headings and six equal cards — two palettes, no hierarchy. Both are in §7 of the spec and pinned by the test against the receipt.

Tests: `cli/tests/test_review_design.py` 10 passed; `test_review_server.py` + `test_review_style_evidence.py` + `test_project_docs.py` 106 passed, 1 skipped (pre-existing skip). No product code changed this unit; the page still looks as §7 describes, and nothing in D1 is claimed closed — what remains is applying the spec (ladder rung 1: tokens, type scale, region layout; light theme deletion belongs to D3), the responsive layout and phone test (rung 2), the after screenshots, and the rendered-page half of the design test (tokens via `getComputedStyle`, overflow at both widths). The spec says plainly which of its assertions the test makes today and which it makes once the page follows it.

Assumptions recorded: the before screenshots live beside the spec in `docs/review-design/` (the charter says "beside the spec") and the receipts under `docs/probes/ot6/`; both directories are under the cap test. Palette tokens are named `--surface/--rule/--ink` rather than the current `--panel/--line/--fg`, so the applying unit renames them in `review.css` and the capture page in one commit. Status hues are the reference's; the eight part colours in `review_scene.js` are kept because they identify parts in the videos. No new dependency: the capture uses the existing DevTools-pipe driver and Pillow (already in the pixi environment) only for quantising committed copies.

Dispatch closed: 1 unit — the review dashboard's design spec with measured before screenshots at 1400 and 400×850, the receipt-cap test, and the operator URL verified on the active project and run.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot6
- commit: 29a95448f33d652036fa186be547078b4fe2abd8

## State Impact

- target: floral-marsh-2830 — D1 started: docs/REVIEW-DESIGN.md exists (purpose, hierarchy, type scale, dark palette tied to the environment's dark scene bg, spacing, breakpoints) with before screenshots at 1400×900 and 400×850 and a receipt pinning the sliver (layout viewport 868 px, canvas 34 px at phone width); the page itself is unchanged, so the after screenshots, the rendered-page token/overflow test and the operator URL in the new design remain open
- target: western-journey-2108 — the phone failure is measured and its mechanism named (fixed 280 px sidebar + min-content tables widen the layout viewport to 868 px); the spec's §6 sets the phone layout and the invariants the D2 browser test will assert; no phone test yet
- target: chilly-union-8972 — cli/tests/test_review_design.py enforces the ot6 charter's evidence caps (16 KB receipts, 200 KB images, no private address or hostname) over docs/probes/ot6 and docs/review-design
