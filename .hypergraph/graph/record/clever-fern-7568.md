---
node_id: c3f7b72c-8a1a-50de-9cf5-22e9d42983b3
slug: clever-fern-7568
title: Prove Reed copy isolation through real retraining and browser reopen
created_at: '2026-09-12T20:06:23+00:00'
parents:
- forest-ledge-2219
summary: ''
artifacts:
- docs/probes/reed-copy/evidence.json
---
## What

Completed Reed's real D7 stopped-project copy lifecycle: copied every retained file, applied a single 90→100 mm foot parameter revision, retrained once on the local GPU, recorded a verified final video, and proved engine reopen plus three-design browser review with the original directory unavailable. Added a reusable isolation probe, extended the existing history probe to explicit run/length pairs, committed compact evidence and documented the operation and outcomes (ADR-294).

## Why

Advances cold-vale-4232 / D7, following the critic's requested unit. A product-agent prompt attempted the review-driven revision but was refused on session quota before authoring. The copy's ADR-006 and design specs disclose the actor's public walk --set fallback. This follows the critic's fallback instruction; no product-agent revision or D9 authorship claim. The 9/10 foot90 falls motivate a support-area hypothesis with greater foot mass/inertia; this experiment measures copy independence rather than claiming gait improvement. No charter, state node or generated view was edited.

## Method

With no source authoring, training or renderer running, hashed and cp -R copied the entire ot5-biped into external ot5-biped-copy29. All 1,206 files initially matched, including .git. Retained inventory is evidence/copy29-before.json; its canonical SHA-256 is a0f42ce87329a1f290cb660f3ed82dbcf83d220a39bddb0421f8106fe2f90a36. Full CLI receipts, screenshots, video, logs and checkpoint remain outside the checkout in the copy.

Ran systemd-run --user --scope --unit=cadex-copy29 -p MemoryMax=20G env XLA_PYTHON_CLIENT_MEM_FRACTION=0.45 timeout --signal=TERM --kill-after=20s 2100 ./cadex walk --project "$COPY" --out "$COPY/runs/copy100" --set foot_len=100 --name copy100.cxpolicy --iterations 240 --envs 1024 --seed 0 --timeout 1800 --leg-timeout 2000 --json. Exit 0; trainer reports GPU, 324.882 seconds (training leg 418.39 s), 32 witness samples, maximum error 9.154e-08 versus 0.0001. Sampled cgroup MemoryPeak 5,070,766,080 bytes under 21,474,836,480-byte cap; no whole-run GPU-memory peak claim. Only foot_len changes among effective parameters; task JSON differs only in model metadata. Fresh training, no warm start.

The private-address live browser loaded the actual swept model at revision 5876642f4d61… with iteration 32 and 33 points in reward/loss/episode histories. Final rendering used PYTHONPATH=cli pixi run python -m cadex_cli.video --project "$COPY" --run copy100. PYTHONPATH=cli:cli/tests pixi run python docs/probes/reed-copy/verify.py "$SOURCE" "$COPY" temporarily renamed the source, exported/reopened the copy through the real public CLI with accepted identity unchanged, then launched a new private-address dashboard and Chromium. Three models (70/90/100 mm feet) matched retained STL bytes, params and exact saved specs; each supplied 240-point curves, orbit/zoom, pixels, playable video and hash-matching download. Earlier views displayed HISTORICAL. A separate decode/playback test checked new video policy, revision, seed and simulation-time labels, eight distinct-endpoint 512-square frames at 10 fps, 0.8 encoded seconds and 0.62 simulation seconds. Original restored in finally; all 1,206 source files and 322 inherited run/asset files still match.

## Result

Ticks D7 with real artifacts and same-machine private-address headless browser evidence, not a second-device test. Copy accepted identity 25d9b6ab7472…; final policy 9e1674abf4dd…; video 2308fe3baa4d…. Seed-0 rollout falls at 0.62 s with +188.402 mm observed torso displacement. This is not a ten-seed comparison, repeatable walking or improvement claim. D9 product-agent revision authorship remains unproven after the refusal. Compact exact identities and browser evidence: docs/probes/reed-copy/evidence.json; reproducible commands: docs/HEADLESS-BIPED-REVIEW.md.

Focused validation: lifecycle browser suite 2 passed (9.83 s); review server/record/video suites 57 passed, 1 skipped (57.96 s); commands suite 23 passed (10.53 s). An early full CLI suite was stopped to prevent its CPU toy training from overlapping the GPU run; The interrupted run displayed one command-test F without a completed failure report; SIGINT did not stop pytest promptly, so SIGTERM stopped it. Its failure cause was not established. The isolated command rerun passed. The full suite was restarted only after the biped trainer exited. No new dependency, product implementation, engine/shell/protocol/payload change or full build. Copying live writers and external symlinks remain outside the documented contract. No reconciliation performed.

Final full CLI suite: 363 passed, 1 skipped in 305.12 s. Final source-unavailable probe rerun also passed after adding post-reopen inherited-file hash assertions. Probe compilation and git diff --check passed. Engine suite/build and packaged/shell gates were not rerun because this unit changes only documentation and probes.

Dispatch closed: 1 unit — prove Reed copy isolation through revision, bounded retraining, video and source-unavailable engine/browser reopen

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 00c7ebbec6c5b18cb155f99e66ab233e7e0aecf8

## State Impact

- target: cold-vale-4232 — D7 now has real Reed copy/edit/GPU-retraining evidence: source-unavailable engine reopen and three-design browser model/spec/curves/video checks pass; all 1206 original files and 322 inherited run/asset hashes unchanged.
- target: silent-river-6649 — Independent copy completes another physical edit and bounded fresh training/video lifecycle. Product-agent revision again refused on session quota; actor fallback disclosed, no authorship or gait-improvement claim.
