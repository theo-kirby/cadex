---
node_id: c3a77ce5-0476-5f37-81c5-5c4114bdda8d
slug: keen-water-3378
title: The review environment is dark only and shared by viewport and capture (ADR-331), compared frame by frame with the reference on the operator URL
created_at: '2026-09-13T22:27:22+00:00'
parents:
- plain-arrow-4971
summary: ''
---
## What

The review environment is dark only, shared by the viewport and the video capture, and compared with the neural-whoop reference frame by frame (ADR-331; D3's first unit). `cli/cadex_cli/review_static/environment.js` exports one `PALETTE` — the reference's dark tile and scene values — and no `setTheme`; the light "prototype map" palette is deleted, not switched off. `review_scene.js` names the look `cadex-prototype-dark-v1`, which every new video records. Beside it: `docs/probes/ot6/look/compare.py` (the D3 probe), its compact receipt `look.json`, eight quantised frames including the four-by-four composite `side-by-side.png`, and `README.md` with the written assessment; `test_the_environment_is_dark_only_and_the_style_says_so` and `test_look_receipt_compares_the_dark_viewport_capture_video_and_reference` in `cli/tests/test_review_design.py`; `test_video.py` asserting the dark style; §4, §8, §9 and a new §10 in `docs/REVIEW-DESIGN.md`; `docs/CLI.md` and `docs/PROVENANCE.md` updated; ADR-331.

## Why

The critic named this unit: "the shared dark reference environment for viewport and capture, with decoded comparison frames and the written assessment required by D3" (`silver-ledge-4640`). It also closes D1's last gap (`floral-marsh-2830`): the viewport was the one light region inside the dark chrome ADR-329 built. The two fixes the critic put first are the previous record (`plain-arrow-4971`) and were done before this unit. The reconcile the critic asked for after them was not run: reconcile is forbidden inside a work iteration, and the tail is now four records — it is the next iteration's housekeeping.

## Method

1. Read the module, the viewer, the capturer, the reference's `web/capture/capture.js` and `index.html` (the follow rig and the clock overlay) and ot5's light comparison (`docs/probes/review-style/`).
2. Collapsed `THEME_PALETTES` to `PALETTE`, removed `setTheme`/`paletteFor`, applied the palette once at construction; renamed the style; ran `test_review_design.py` + `test_video.py`: 39 passed.
3. Re-rendered `lark98-final` on the persistent copy in the dark look (`python -m cadex_cli.video`, 81 frames, 13.3 s; its light recording stays retained beneath). The persistent server was not restarted.
4. Ran the probe against the operator URL: decoded frames 0 and 4 s of the dark video and one frame each of the shipped `orbit`/`swing`/`flip` clips (reference commit `31caeb28…`, read-only); drew the persistent viewport at the default fit, the video's pose and camera, close 0.7×, wide 3×, underside, and a **framed** shot at the reference's declared framing fraction (subject height 236 mm at 0.22 of the frame → 1 031 mm); orbited by real pointer input; drew the capture page at the same pose; drew the reference's own unmodified `scene.js`/`environment.js` (dark) over the same Lark solids at the same four cameras in an in-memory harness; measured luminance patches and the stage the environment derived at every camera.
5. Viewed the composite and full-size frames; wrote the assessment; wrote the tests and docs; ran `test_review_design.py` + `test_project_docs.py` (77 passed), the engine suite's licensing and library tests (114 passed, 1 skipped), and the full CLI suite on the final tree.

## Result

What is true now, verified on the operator URL serving `ot5-lark-copy85` with `lark98-final` selected, live:

- **Viewport and capture are the same place**: byte-identical at the same pose and camera; the decoded first video frame is within 1.10 / 255 (mean absolute RGB) of the viewport; the page's `--bg` `#141414` is the viewport's sky.
- **The reference renderer agrees**: its own dark modules over the same solids at the same cameras give frames whose mean luminance equals ours to 0.1 (64.1 vs 64.0 whole, 30.3 sky, 32.5 floor). The shipped clips' sky patch is 18.2; ours 17–44 across the framings compared, brighter only where the ot5 slab reaches the corner.
- **Stage checks**: at close, framed, video, wide 3× and wheeled-out framings the floor runs to four times the fog's far distance (asserted), the grid subdivision follows the framing (0.2 m close, 0.5 m at the video's standoff, none wide), the model stays drawn through the orbit (≥ 1 253 px at 3×), and a contact shadow lies beside the feet at the close, framed and same-pose framings; at 3× it is too small to resolve at 512 px.
- **Assessment** (`docs/probes/ot6/look/README.md`): floor/grid, horizon/fog, palette, lighting/shadows, materials and antialiasing match the reference; materials differ by design (identity colours, kept per the spec); **framing and camera do not yet**: the video is still the fixed fit over every visited pose and there is no timer overlay. Those two are what D3 still owes, each with its own decoded frames.
- **Tests**: full CLI suite on the final tree under `pixi run`: **521 passed, 1 skipped** (the private-address test, which wants `CADEX_REVIEW_HOST`), 499 s, exit 0. `test_review_design.py` 40 passed; engine licensing + library 114 passed, 1 skipped. The ot5 receipts pinning `cadex-prototype-light-v1` are untouched: they describe recordings that still exist with that style.

Assumptions recorded: re-rendering a Lark run's video on the persistent copy is a new recording added in front of the retained one, not a rewrite of history; the operator dashboard picked the dark viewport up without a restart because the server serves the checkout's static files. No engine, protocol, payload, shell or dependency change; Pillow (already in the pixi environment) quantises the committed copies. Removal logged in ADR-331.

Dispatch closed: 1 unit — the review environment is dark only and shared by viewport and capture (ADR-331), compared frame by frame with the reference on the operator URL with the written assessment; D3 still owes the tracking camera and the timer overlay.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot6
- commit: a19ebebed0b3d9eddffe206d71dc81166870ba6d

## State Impact

- target: silver-ledge-4640 — D3 partly evidenced: the environment module has one dark palette (light removed, ADR-331) shared by viewport and capture; on the operator URL the viewport and capture are byte-identical at the same pose, the decoded dark video is within 1.10/255 of the viewport, the reference's own dark modules over the same solids match in luminance to 0.1, the stage outruns the fog at close/framed/wide/orbit framings, and docs/probes/ot6/look holds the frames beside the shipped reference clips with the written assessment (floor/grid, horizon/fog, palette, lighting/shadows, materials, framing, camera); still owed: the capture's tracking camera at a declared framing fraction and the timer overlay
- target: floral-marsh-2830 — D1's last gap closed: the viewport renders the dark scene whose background is the page's --bg, so one palette spans chrome and viewport (REVIEW-DESIGN.md §10); D1's evidence list is now complete pending the owner's tick
- target: chilly-union-8972 — new videos record style cadex-prototype-dark-v1; environment.js exports one PALETTE and no setTheme; lark98-final on the persistent Lark copy has a dark recording in front of its retained light one; full CLI suite 521 passed, 1 skipped
- target: fair-wolf-4645 — the light look that ot5's D11 comparison assessed is retired (ADR-331); its receipts remain valid as history of the cadex-prototype-light-v1 recordings they describe, and the dark comparison supersedes them as the current visual evidence
