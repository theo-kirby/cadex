---
node_id: d44bfbdd-32ae-52c9-8aa9-3ae1fd2d33a5
slug: western-journey-2108
title: D2. The dashboard works on a phone
created_at: '2026-09-13T21:25:09+00:00'
parents:
- round-sun-8398
summary: ''
---
Status: working

## Current

**D2 has its layout half and its interaction half, both measured at 400×850 under headless touch emulation, on the fixture project and on the operator URL.** The phone failure was first measured and its mechanism named: a fixed 280 px sidebar plus min-content tables (the seven-column params table, the artifacts table, unbroken identity strings) widened the layout viewport to 868 px and left a 34 px canvas; §6 of `docs/REVIEW-DESIGN.md` sets the phone layout and the invariants the browser test asserts [rec: ancient-field-7584]. Layout (ADR-329): at 400×850 the layout viewport is the device width with zero overflow, the run list is a closed `<details>` disclosure that opens on a click, the canvas fills the width (350×263 at 4:3), the curves stack — folded by the media query alone, with no element id or `data-*` hook changed [rec: royal-road-2298]. Interaction (ADR-330, commit `ad4e08e1`, recorded retroactively): `review_scene.js` moved from mouse handlers to pointer events — one pointer orbits, two fingers pinch-zoom, the wheel zooms, the canvas captures the pointer under `touch-action: none` — and each video's caption leads with a 40 px Play / Pause control of the page's own (`[data-video-play]`), because native controls' tap targets differ from phone to phone. `cli/tests/test_review_design.py` gained the phone test (orbit without page scroll, pinch, Fit by tap, legible curves, playback from a tap, download by tap with the recorded SHA-256, on a real FFmpeg-encoded fixture video) and a receipt test; `docs/probes/ot6/design/capture_page.py` drives the operator page by touch and clips each region; seven `docs/review-design/phone-*.png` region screenshots and `phone.json` are committed. Full CLI suite at that tree: 494 passed, 15 skipped, 0 failed, and no D2 test skipped — a Chromium and FFmpeg were present [rec: plain-arrow-4971].

**The owner ticked D2 on 2026-09-14 with the evidence unchanged** [rec: nimble-wing-3050]. The phone layout is the owner's own work from here (ADR-341); one owner-directed change has landed since the tick, ADR-344 (commit `d93183ba` on main): a phone held **landscape** — 600–999 px wide, no more than 560 px tall — now gets the desk frame of ADR-342 instead of the portrait column, with a 40 px top bar, the model spanning the full width, the sidebars as drawers over the model (one at a time, closed by default, not remembered, a tap on the scrim closing them) and no page scroll. Before, 844×390 showed the portrait column: 6 410 px of scroll with the model as a strip. The frame media query in `review.css` widened to `(min-width: 1000px), (min-width: 600px) and (max-height: 560px) and (orientation: landscape)`, mirrored in `review.js` as a `FRAME`/`COMPACT` pair; `docs/REVIEW-DESIGN.md` §13 specifies it; a new touch test at 844×390 covers it; the portrait phone layout at 400×850 is unchanged. Review, video and style suites 231 passed, 1 skipped [rec: crimson-gate-0087].

Charter criterion: **D2. The dashboard works on a phone.** At 400x850 with touch emulation: the page is readable without zoom, the sidebar collapses, the model view fills the width and orbits by touch, curves are legible, videos play and download. Evidence: a headless browser test with a mobile viewport and touch events, and screenshots of each region at that width. Declared target `gap-d2-dashboard-works-phone-400x850`; the human owns the checkbox edit [rec: brisk-ledge-9638].

Reconcile judgement: `working` — each item on the charter's list has a test or a committed screenshot named in `docs/REVIEW-DESIGN.md` §8a and §9, and the owner's tick is in the charter. ADR-344 is owner work outside any charter, recorded so the node describes the page as it is. What the evidence is not: a physical phone. Headless Chromium's touch emulation and gesture recogniser are what is measured [rec: plain-arrow-4971].

## Negative knowledge

- [scope: headless Chromium's touch emulation on the review page | confidence: high | evidence: plain-arrow-4971] A tap within a few hundred milliseconds of a drag's end is dropped by the emulated gesture recogniser. The capture script records and waits out that behaviour rather than the page working around it; a real device may differ, and nothing on this node is device evidence.
- [scope: editing a multi-line CSS comment in `review.css` | confidence: high | evidence: crimson-gate-0087] Editing only the first line of a multi-line comment left the rest outside it; the orphaned text swallowed the entire frame `@media` block, which vanished from `document.styleSheets` and silently fell back to the column. Caught by listing the stylesheet's `cssRules` in the browser.

## Provenance

- brisk-ledge-9638 — the ot6 directive (ADR-328) declared this criterion as gap `gap-d2-dashboard-works-phone-400x850`
- ancient-field-7584 — the phone failure measured (layout viewport 868 px, canvas 34 px) and its mechanism; the spec's §6 phone layout and invariants
- royal-road-2298 — ADR-329: the layout half at 400×850 — device-width viewport, no overflow, closed disclosure, full-width canvas, stacked curves; touch orbit named as not yet implemented
- plain-arrow-4971 — ADR-330: pointer-event orbit and pinch, the Play/Pause control, the phone browser test, seven region screenshots and the phone receipt on the operator URL; CLI suite 494 passed / 15 skipped at ad4e08e1
- nimble-wing-3050 — the owner ticked D2 on 2026-09-14; evidence unchanged
- crimson-gate-0087 — ADR-344 (owner-directed, after the tick): landscape phones get the frame with drawer sidebars over a full-width model; portrait unchanged
