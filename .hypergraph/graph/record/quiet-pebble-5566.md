---
node_id: 0e7eb9a5-bc07-51bb-adc3-93278139134a
slug: quiet-pebble-5566
title: Prove Lark encoder-failure isolation during real GPU training on the persistent dashboard and make the observer project-agnostic
created_at: '2026-09-13T10:35:19+00:00'
parents:
- peaceful-walrus-0642
summary: ''
---
## What

Repeated real encoder-failure isolation on Lark (D4), on the persistent port 8765 project `ot5-lark-copy85`: one bounded GPU run `lark98` (240 updates, 1,024 envs, seed 0, `MemoryMax=20G`, 1,800 s timeout) published its checkpoint-20 video during training; that checkpoint was then re-rendered through the ordinary CLI renderer with a temporary `ffmpeg` exiting 73 on that subprocess's PATH only; the persistent page showed `Recorded video render: failed — ValueError: FFmpeg encoding failed` with the CLI retry action beside `Video files: available (1/1 retained)`; the verified recording and the previous design's `lark2-final` still played and downloaded hash-equal; four live updates arrived without reload; the real-encoder retry recovered (`ready`, second WebM retained, 81 decoded frames); the sole trainer kept PID 19886 / start ticks 102341947 and finished exit 0 at update 239; the final policy's video plays and downloads and a fresh visit selects `RUN lark98-final`. Receipt: `docs/probes/lark-fresh/render98-evidence.json`, narrated in `RENDER98.md`, guarded by two new tests in `cli/tests/test_lark_fresh_evidence.py`; ADR-320. The shared observer `docs/probes/wren-fresh/render_failure.py` lost its one Wren name (prior run is now an argument) and gained its own `render-recovery` evidence label. LIFECYCLE.md, the Lark README, the operator README and RENDER-FAILURE.md updated.

## Why

The critic named this unit exactly: the one Lark-only gap `LIFECYCLE.md` still named was D4's encoder-failure isolation resting on Wren. Advances D4 (real render failure leaves training running and reports its own failure), D9 (the Lark lifecycle report now links only Lark receipts) and D10 (the persistent URL tracked `lark98` during training and `lark98-final` afterwards, verified by headless browser on the private address). I did what the critic asked, with one deviation: the observer's final bookkeeping line crashed after every assertion had passed (it read `lark98-checkpoint20-check.json`, a name `check_video.py` stopped writing in iteration 88), so the recovery check overwrote the publication-time check files under the `-recheck` name and the post-recovery trainer sample came from the driver's committed timeline rather than from the observer. Both are stated in the receipt and RENDER98.md; the observer is fixed for the next run rather than the training being repeated.

## Method

1. Parameterised the prior run in `render_failure.py` (`PROJECT TRAINING_RUN URL PRIOR_RUN`), asserted it has a retained video, updated the Wren command line.
2. Launched `docs/probes/lark-fresh/train.py` on the copy as `lark98` and the observer with `lark2-final`, both on the persistent URL; confirmed `default_run` selected `lark98` (running, training) during the run.
3. Read the project-local receipts (`lark98-checkpoint20-render-failure.json`, `-recheck-check.json`, `-publication.json`, `lark98-experiment-result.json`, `-observe.json`, `lark98-final-check.json`, resource bound), checked with `find -newermt` that nothing under `runs/`, `assets/` or `evidence/` outside `lark98*` changed, assembled the compact receipt with hashes and no private address.
4. Fixed the observer's recovery label, wrote RENDER98.md, the tests, doc updates and ADR-320; ran the Lark evidence tests, then the CLI and engine suites sequentially after the trainer exited.

## Result

Numbers: fault after 3.553 s, renderer exit 1; page updates 37–40 with history lengths 38–41; trainer at 34 before the fault, 41 after the checks, 53 at recovery, 239 done; wall 729.568 s; host peak 7,406,166,016 bytes under 21,474,836,480; witness errors 3.38e-08 and 8.85e-08 under 1e-04; first checkpoint video `5c68796a96d9…`, recovered `a2e40b55c0a1…`, final policy `fca598975089…`. The service kept PID 4173669, lists 13 runs, and a fresh visit selects `RUN lark98-final`. Retained-file inventory 1,887; ten earlier run records byte-identical. Concern: the observer defect above means this run's publication-time `-recheck` files are the recovery's, not the publication's — the publication identity survives in `lark98-checkpoint20-publication.json`. Assumption: `lark2-final` (the previous design revision) is the right "older video" to hold during the fault; any run with a retained video would do. No new dependency. Same-machine browser over the private address, no second-device test, no gait claim, no product/protocol/payload change, no build.
Verification, run sequentially after the trainer exited: `pixi run python -m pytest cli/tests/test_lark_fresh_evidence.py -q` 17 passed; `pixi run python -m pytest cli/tests -q` 448 passed, 1 skipped (437.77 s); `pixi run test-engine` 2110 passed, 53 skipped (254.46 s); `git diff --check` clean; every relative link in the touched docs resolves. The unreconciled tail was 0 nodes on arrival, so this record makes 1.
Dispatch closed: 1 unit — Lark D4 encoder-failure isolation during real GPU training, receipt render98-evidence.json, observer made project-agnostic (ADR-320).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 76a631cc41e8240fc99add6980ed5e02f2a2aff6

## State Impact

- target: candid-harvest-2614 — D4 real render-failure isolation is repeated on Lark: lark98's checkpoint-20 re-render failed at encoding through a temporary ffmpeg, the persistent page showed the failure with retry guidance beside the still-available recording, lark2-final kept playing, the sole trainer kept its PID through recovery to 240 updates and a final video; receipt docs/probes/lark-fresh/render98-evidence.json, RENDER98.md, ADR-320
- target: silent-river-6649 — every D1–D11 receipt the Lark lifecycle report links now comes from Lark or its working copy; the D4 dependency on Wren evidence is removed and no Lark-only acceptance gap remains named in LIFECYCLE.md
- target: deep-clover-6012 — persistent port 8765 served ot5-lark-copy85 throughout a third real experiment without restart: fresh visits selected the running lark98 during training and select the completed lark98-final afterwards; 13 runs, service PID unchanged
