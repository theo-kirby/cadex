---
node_id: 0d6b1e3a-81a5-57b7-9765-4edb485eda20
slug: silver-ledge-4640
title: D3. Viewport and videos match the neural-whoop reference
created_at: '2026-09-13T21:25:09+00:00'
parents:
- round-sun-8398
summary: ''
---
Status: working

## Current

**D3's environment half is in — dark only, shared by viewport and capture, compared frame by frame with the reference on the operator URL (ADR-331). Still owed: the capture's tracking camera at a declared framing fraction, and the timer overlay.** `cli/cadex_cli/review_static/environment.js` exports one `PALETTE` — the reference's dark tile and scene values — and no `setTheme`; the light "prototype map" palette is deleted, not switched off, and every new video records the style `cadex-prototype-dark-v1`. On the operator URL serving `ot5-lark-copy85` with `lark98-final` re-rendered in the dark look (81 frames, a new recording in front of the retained light one; the server was not restarted and picked the change up because it serves the checkout's static files): viewport and capture are byte-identical at the same pose and camera; the decoded first video frame is within 1.10/255 (mean absolute RGB) of the viewport; the page's `--bg` `#141414` is the viewport's sky; the reference's own unmodified dark `scene.js`/`environment.js` over the same Lark solids at the same four cameras match in mean luminance to 0.1 (64.1 vs 64.0 whole, 30.3 sky, 32.5 floor); the shipped clips' sky patch is 18.2 against 17–44 across our framings, brighter only where the ot5 slab reaches the corner. Stage checks at close 0.7×, framed (subject 236 mm at the reference's 0.22 fraction → 1 031 mm), the video's pose, wide 3× and a real pointer orbit: the floor runs to four times the fog's far distance (asserted), the grid subdivision follows the framing (0.2 m close, 0.5 m at the video's standoff, none wide), the model stays drawn through the orbit (≥ 1 253 px at 3×), and a contact shadow lies beside the feet at the close, framed and same-pose framings, too small to resolve at 3× on 512 px. `docs/probes/ot6/look/` holds `compare.py`, the compact `look.json`, eight quantised frames including the four-by-four `side-by-side.png` beside one frame each of the shipped reference `orbit`/`swing`/`flip` clips (reference commit `31caeb28…`, read-only), and `README.md` with the written assessment: floor/grid, horizon/fog, palette, lighting/shadows, materials and antialiasing match the reference; materials differ by design (the eight identity colours, kept per the spec); **framing and camera do not yet** — the video is still the fixed fit over every visited pose, and there is no timer overlay. Tests: `test_the_environment_is_dark_only_and_the_style_says_so` and the look-receipt test in `cli/tests/test_review_design.py` (40 passed), `test_video.py` asserting the dark style; full CLI suite 521 passed, 1 skipped (the private-address test, which wants `CADEX_REVIEW_HOST`), so playback, download, polling and headless tests are green on the dark environment. `docs/REVIEW-DESIGN.md` §4, §8, §9 and a new §10, `docs/CLI.md` and `docs/PROVENANCE.md` updated [rec: keen-water-3378].

Charter criterion: **D3. Viewport and videos match the neural-whoop reference.** Dark only: the reference's near-black grid mat with PROTOTYPE / 1 METER labels and subject-scaled pitch, fog, contact shadows, antialiasing, a camera tracking the subject at a declared framing fraction, and the timer overlay, from one environment module shared by viewport and capture. Evidence: reference frames (`neural-whoop/render-examples`) beside Cadex viewport screenshots and decoded video frames at equivalent framing, with an explicit written assessment of floor/grid, horizon/fog, palette, lighting/shadows, materials, framing and camera; the same pose/camera compared viewport-to-video; close and wide framing and orbit tested for stage edges, lost shadows or bad scale; the light palette removed from the code; existing playback, download, polling and headless tests still green. Declared target `gap-d3-viewport-videos-match-neural`; the human owns the checkbox edit [rec: brisk-ledge-9638].

Reconcile judgement: `working`, not complete — the record itself names two evidence items as owed, the tracking camera at a declared framing fraction and the timer overlay, each needing its own decoded frames. The ot5 receipts pinning `cadex-prototype-light-v1` are untouched and describe recordings that still exist; that look's history is on `fair-wolf-4645` [rec: keen-water-3378].

## Negative knowledge

None yet.

## Provenance

- brisk-ledge-9638 — the ot6 directive (ADR-328) declared this criterion as gap `gap-d3-viewport-videos-match-neural`
- keen-water-3378 — ADR-331: one dark `PALETTE`, no `setTheme`; viewport/capture byte-identical and the decoded video within 1.10/255 on the operator URL; the reference's own modules match to 0.1 luminance; stage checks at five framings; `docs/probes/ot6/look` with the written assessment; CLI 521 passed / 1 skipped; tracking camera and timer overlay still owed
