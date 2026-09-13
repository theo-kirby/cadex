---
node_id: 8ae4ebd3-9922-5bd9-ab70-0eab6503fdd2
slug: fair-garden-6418
title: Guard trainer exclusion and repeat Wren interruption without suite overlap
created_at: '2026-09-13T01:48:26+00:00'
parents:
- small-wind-0172
summary: ''
artifacts:
- docs/probes/wren-fresh/interruption.py
- docs/probes/wren-fresh/test_interruption.py
- docs/probes/wren-fresh/INTERRUPTION.md
- docs/probes/wren-fresh/interruption57-evidence.json
---
## What

Fixed the Wren interruption probe's missing trainer exclusion and repeated the real GPU interruption/retry with the CLI and engine suites strictly separate. Published a new compact receipt, preserving every earlier attempt and receipt. The persistent private port 8765 remains active on ot5-wren-copy54, default wren57-retry.

## Why

Fixes the critic rejection of small-wind-0172: the disclosed CPU test/GPU overlap violated the charter, so documenting it was insufficient. This unit advances D8 (cool-gate-3332), D10 (deep-clover-6012) and reinforces D7 copy isolation (cold-vale-4232). No deviation from the critic request. No reconciliation, state nodes or generated views edited.

## Method

Added a Linux /proc guard directly to docs/probes/wren-fresh/interruption.py (ADR-305). Before each launch it refuses existing Python trainer or pytest processes. Trainer script argv and module invocations count regardless of CPU/GPU selection; pytest is excluded because tests can train in-process. Shell/timeout wrappers do not count. During training a background thread samples at a requested 50 ms interval, including blocking browser calls and process wait, allowing exactly one trainer in the experiment's own systemd scope. Foreign/duplicate trainers or scan errors latch a failure, save a receipt, stop only the experiment scope and mark the attempt failed rather than launch a retry. Receipts retain scan counts, PIDs, maximum trainer count, largest scan gap and violations. Five regression tests exercise CPU/module detection, wrapper filtering, preflight refusal, background overlap latching, own-scope duplicates and unreadable scans with no real training.

Ran the CLI suite to completion, then the engine suite to completion, before the experiment. OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run python -m pytest cli/tests: 397 passed, 1 skipped in 373.40 s; finished 2026-09-13 01:36:24 UTC. Same environment with pixi run test-engine: 2110 passed, 53 skipped in 253.73 s; finished 01:40:38 UTC. Logs and their hashes retained in evidence/guard57 and the new compact receipt. PYTHONPATH=cli:cli/tests pixi run python -m pytest docs/probes/wren-fresh/test_interruption.py -q: 5 passed. No suites ran during either experiment trainer.

Ran PYTHONPATH=cli:cli/tests OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run python docs/probes/wren-fresh/interruption.py "$HOME/cadex-projects/ot5-wren-copy54" "http://$(tailscale ip -4):8765/" wren57. Existing offboard environment, 1024 environments, seed 0, MemoryMax=20G and 900-second timeout per attempt. Public export plus retained assembled model/spec/docs precede each launch; the first receives SIGINT after iteration 5 and browser observations, the second starts only after confirmed exit and historical-video checks. The real persistent browser asserts fresh selections, accepted revision, 110 mm feet and eight components at starts, failed/failed and completed/done terminal state, no substituted new video, historical selection and return-to-current. Eight checks fully decode, play across refreshes and hash-verify downloads of all four retained videos. Independently ran current.py at the prior baseline, both new starts and final completion. Inspected start and terminal screenshots. Final process scan found no trainers or pytest; systemctl reports the unchanged operator service active.

## Result

Uncontaminated repeat: wren57-interrupt started 01:41:24 UTC, exited -2 after SIGINT at iteration 5, failed with KeyboardInterrupt and six samples per curve; 88.740 s launch-to-browser and 4,998,832,128 bytes sampled host peak. Its guard recorded 1,639 scans, one trainer PID, maximum count 1, no violation, largest scan gap 59.33 ms. wren57-retry started 01:43:02 UTC after the first trainer exited, completed with exit 0 at iteration 11 and 12 samples per curve; 150.793 s launch-to-browser and 5,483,139,072 bytes sampled host peak. Its guard recorded 2,789 scans, one trainer PID, maximum count 1, no violation, largest scan gap 58.87 ms. Both report gpu and remain below the enforced 21,474,836,480-byte cap. Retry policy is 49,095 bytes, SHA-256 a232fec18df3ed7621e13f966302adeeab23259039cb0ab4a6ea2d09f09d9814; trainer-local witness check passed. Final reward/step 0.1330547, loss 8.267842 and batch episode estimate 99.9024 are not gait/survival measurements. Known initialization JAX cast warning remained.

The full probe exited 0. All eight old-video checks passed, all 362 prior run files including wren56/wren56b/wren56c attempts and all 963 original Wren non-git files remain byte-identical. Port 8765 remains on ot5-wren-copy54 with wren57-retry, accepted revision 5b61ef31ff134f0f31b079347d9e5d3fd6aec236f12ad9c7b45910640388d7e6 and digest b04439061b0278903fca11079ff0937dac12425a5a8b767e675e24542c7a4ea4. docs/probes/wren-fresh/interruption57-evidence.json and INTERRUPTION.md publish the new result; the old receipt stays unchanged. Full artifacts stay project-local in runs/wren57-* and evidence/wren57; no large artifacts or machine paths committed.

Limits: process exclusion is sampled observation, not a host-wide scheduler lock; a process shorter than the maximum scan gap could escape detection. The operator launched no competing work, and both test suites demonstrably completed before training. No new dependency, engine/protocol/payload/shell/trainer change or build. No new engine verification of the policy, video, visual-style comparison, second-device observation, gait-quality claim or product-agent authorship claim. Python compile and diff whitespace checks pass; hypergraph export/check runs before commit. Earlier contaminated evidence is superseded for exclusion only, never erased.

Dispatch closed: 1 unit — guard CPU/GPU trainer exclusion and publish a clean persistent-dashboard interruption/retry receipt.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 968805ef2b966f67bcd2fbd775af90e99e6b77a3

## State Impact

- target: cool-gate-3332 — Critic-requested clean Wren interruption/retry passes with CPU/GPU and pytest exclusion guard; suites finish before training, both monitors observe at most one trainer and no violation. Earlier attempts remain retained.
- target: deep-clover-6012 — Persistent port 8765 stays on ot5-wren-copy54 and follows wren57-interrupt to completed wren57-retry; start/terminal private-address browser identities and historical playback pass, service remains active.
- target: cold-vale-4232 — Clean working-copy training preserves all 362 prior run files and 963 original Wren non-git files; new retry policy and monitoring artifacts remain copy-local.
