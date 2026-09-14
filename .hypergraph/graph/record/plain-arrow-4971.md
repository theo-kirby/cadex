---
node_id: b9d12c43-3afb-5388-9b5c-01b6e084839a
slug: plain-arrow-4971
title: 'Phone interaction on the review page (ADR-330): touch orbit, pinch, Play control, phone test and region receipts; retroactive record for ad4e08e1 with the CLI suite result'
created_at: '2026-09-13T22:20:25+00:00'
parents:
- royal-road-2298
summary: ''
---
## What

The retroactive record for the product half of commit `ad4e08e1` ("ouroboros #4"), whose record `royal-road-2298` described only iteration 3's layout work. Iteration 4 also changed the page for D2 (ADR-330): `review_scene.js` moved from mouse handlers to pointer events (one pointer orbits, two fingers pinch-zoom, the wheel zooms, the canvas captures the pointer); each video's caption leads with a Play / Pause control of the page's own (`[data-video-play]`, a 40 px target under a coarse pointer) because native controls' tap targets differ from phone to phone; the DevTools-pipe driver `cli/cadex_cli/browser.py` gained `touch`, `touch_drag`, `pinch`, `tap`, a `by_touch` download and a `clip` on `screenshot`; `cli/tests/test_review_design.py` gained `test_phone_touch_orbits_pinches_plays_and_downloads` (400×850, touch emulation, a real FFmpeg-encoded fixture video: orbit without page scroll, pinch, Fit by tap, legible curves, playback from a tap, download by tap with the recorded SHA-256) and `test_phone_receipt_records_touch_orbit_and_every_region_on_the_operator_url`; `docs/probes/ot6/design/capture_page.py` drives the operator page by touch and clips each region; the receipt `phone.json` and seven `docs/review-design/phone-*.png` region screenshots were committed; `docs/REVIEW-DESIGN.md` §5, §8a and §9 say which test shows what; `docs/CLI.md` points at them; ADR-330 records the decision.

## Why

The critic's message for iteration 5 asked for this first: record ad4e08e1's D2 changes separately, and finish the full CLI suite — which iteration 4 did not run — and record its result honestly. This is bookkeeping the loop owes, not a unit; the unit follows in the next record.

## Method

Written by iteration 5 from `git show ad4e08e1` and by running the suite, not from memory. The full CLI suite was run on that exact tree: a detached `git worktree` at `ad4e08e1` with the checkout's `build/` symlinked in so the engine resolved from the dev tree (`Engine(... source='dev-tree')`), `python -m pytest cli/tests -q`. A first run in the working tree was abandoned because iteration 5's own edits landed mid-run and would have contaminated it; the worktree was removed afterwards.

## Result

What is true now, verified:

- **CLI suite at `ad4e08e1`: 494 passed, 15 skipped, 0 failed, 360.7 s, exit 0.** The skip reasons were not captured (the run was `-q` without `-rs`), and the worktree was driven by the pixi environment's interpreter directly rather than `pixi run`, so 14 of the 15 are probably environment-gated tests that `pixi run` satisfies: the same suite on iteration 5's final tree under `pixi run` gives 521 passed, 1 skipped (the private-address test, which wants `CADEX_REVIEW_HOST`), with iteration 5 adding 13 tests. No test in the D2 files skipped in either run — a Chromium and FFmpeg were present, so the phone interaction test ran.
- D2's charter list — readable without zoom, sidebar collapses, model fills the width and orbits by touch, curves legible, videos play and download at 400×850 with touch emulation, screenshots of each region at that width — each has a test or a committed screenshot named in `docs/REVIEW-DESIGN.md` §8a and §9. What it is not: a physical phone; headless Chromium's touch emulation and gesture recogniser are what is measured, and one recogniser behaviour (a tap within a few hundred milliseconds of a drag's end is dropped) is recorded in the capture script rather than worked around in the page.
- D1's remaining gap at that commit — the viewport still light inside a dark chrome — was unchanged by iteration 4 and is taken by the next record.

No engine, protocol, payload, shell or dependency change in `ad4e08e1`. Concern for the reconcile pass: this brings the unreconciled tail to three records, four with the unit that follows; reconcile is forbidden inside a work iteration, so the next iteration's unit is the reconcile pass unless the critic says otherwise.

Dispatch closed: 0 units — bookkeeping: iteration 4's D2 product changes recorded with the full CLI suite result (494 passed, 15 skipped) on that tree.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot6
- commit: ad4e08e1fa7b63301883082c1daf91d76886a523

## State Impact

- target: western-journey-2108 — D2's interaction half exists at ad4e08e1: pointer-event orbit and pinch, a Play/Pause control per video, the phone browser test (orbit without scroll, pinch, Fit by tap, legible curves, playback and download by tap) and seven region screenshots with the phone receipt on the operator URL; the full CLI suite on that tree is 494 passed, 15 skipped; evidence is headless emulation, not a device
- target: chilly-union-8972 — the DevTools-pipe driver drives pages by touch (touch, touch_drag, pinch, tap, by_touch download, clipped screenshots), so tests and probes can measure the phone; CLI suite 494 passed, 15 skipped at ad4e08e1
