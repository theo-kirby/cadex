---
node_id: c5345474-8920-50f5-855f-a98a32d47ade
slug: plain-harbor-3410
title: A8. Everything is drawn on the dark prototype floor
created_at: '2026-09-29T06:45:37+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run ot10, **added by the owner mid-run: A8. Everything is drawn on the dark prototype floor** [rec: snowy-quill-0006]. The studio hero, the concept sheet, `look`, the rollout video and every other presented image use the dashboard's dark scene: the `PALETTE.scene` background `#141414` plus the prototype mat — tiles `#1c1c1c` / `#232323` with a `#3a3a3a` major grid line. One palette source, tests pinning it to the viewport's, shadow and lighting readable on the dark floor, and before/after images of one A5 design plus the W2 video at 300 KB or less each [rec: snowy-quill-0006]. A presentation change only: it does not re-score A5 or A7 [rec: snowy-quill-0006].

**Met pending the owner's tick** (ADR-444, commit `badcf987`) [rec: keen-comet-6140]. The human owns the checkbox.

- **One palette source.** `cli/cadex_cli/scene.py` parses the viewport's own files — `PALETTE` in `review_static/environment.js` and `--ink`/`--ink-2`/`--rule` in `review_static/review.css`. No other file copies a scene colour; the light `BACKDROP_*` gradient, the sheet's light colours and the SVG `#f6f7fa` are deleted, not switched off [rec: keen-comet-6140].
- **What it covers.** The studio hero (floor drawn as the mat through `render._floor`, antialiased grid on `floor.js`'s pitch ladder, fading into `#141414` between 0.75× and 1.9× framed extent), the four review views, `look`, the concept sheet and the studio rollout video; `video.studio_digest` now hashes `scene.py` and both palette files. Contact-shadow minimum deepened to 0.2 (was 0.45); at the feet the floor falls from tile 28–35 to 6 of 255 [rec: keen-comet-6140].
- **Tests.** `cli/tests/test_scene_palette.py` (8 tests) pins the renderer's palette to the viewport's and to the charter's four hex values, checks the drift path and the refusal on an unreadable `PALETTE`; `test_look.py` and `test_sheet.py` updated where they encoded the light look. Full CLI 1085 passed / 1 skipped; engine 2282 passed / 53 skipped. `cli/` only, so the packaged gate did not apply [rec: keen-comet-6140].
- **Evidence images** under `docs/probes/ot10/`: `a8-quadruped-3-hero-dark.png` (195 KB), `a8-quadruped-3-sheet-dark.png` (227 KB), `a8-w2-2-rollout-dark.png` (174 KB), against the existing light "before" images of the same design, views and frames [rec: keen-comet-6140].
- **Budgets.** Four views plus 1024 px hero in 15.2 s (A2's 60 s bar); proxies unchanged (hardware 0.0 %, sharp edges 11.6 %, 3 materials). The w2-2 studio video took 189.0 s for 101 frames (300 s bound), about 23 % over the light backdrop's 153.9 s [rec: keen-comet-6140].
- **Dashboard playback verified.** The dashboard's Chromium playback check passes on the dark w2-2 webm: SHA prefix `3fb52b44…`, 512², 10.1 s, still playing after three polls, download byte-exact (438,625 bytes); decoded corners `#161616`/`#181818`, the `#141414` scene after VP9 [rec: glad-ridge-1079].
- **Nothing re-scored.** The frozen A1 rubric's T-anchor still says "seamless backdrop"; a future judged probe would see dark renders and needs a recorded re-scoring decision first [rec: keen-comet-6140].

## Negative knowledge

- [scope: cli/tests cube and post fixtures | confidence: high | evidence: keen-comet-6140] The contact shadow on tiny box fixtures reads weak on the dark floor (0.74–0.77 of tile brightness) because a box's foot is hidden under itself; real designs measure 0.2. Not a defect in the designs, a limit of the fixtures.

## Provenance

- snowy-quill-0006 — operator directive adds A8 (dark prototype floor) mid-run and makes it ot10's last product work
- keen-comet-6140 — A8 landed (ADR-444): scene.py single palette source, dark hero/look/sheet/video, test_scene_palette, before/after images, suites green
- glad-ridge-1079 — dark w2-2 webm plays and downloads byte-exact in the dashboard's Chromium check
