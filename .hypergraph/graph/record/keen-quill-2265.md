---
node_id: 3797d0c6-62cf-53ae-91d3-edd73e957c53
slug: keen-quill-2265
title: 'F9: portable retained-fit regression after second F4 provider refusal'
created_at: '2026-09-14T21:22:59+00:00'
parents:
- hidden-lodge-4550
summary: ''
artifacts:
- docs/probes/ot7/retained/README.md
- docs/probes/ot7/retained/repair-refusal-iteration19.json
- docs/probes/ot7/retained/finch.measurements.json
- docs/probes/ot7/retained/robin.measurements.json
- docs/probes/ot7/retained/heron.measurements.json
- cli/tests/test_retained_fit.py
---
## What

Pinned the retained ot6 comparison in a portable CLI regression over all 787 measured component pairs. Added compact, lossless measurement fixtures and documentation. First resumed F4 once with the frozen prompt in a fresh session; the provider refused again, so no design turn completed.

## Why

The critic requested F4 first, then this F9 tooling/test fallback if the provider still refused. This unit follows that direction exactly: no repeated retry, design edits or extra continuation prompt. It advances eager-summit-3153 and records the continued limitation on polished-forest-0215. The explicit contributor-only dispatch prohibits reconcile despite the charter's periodic schedule; no state nodes, STATE.md or PLAN.md changed.

## Method

On the retained ot7-heron-repair seed, read the published clearance scope with restore=False before and after one ./cadex invocation using claude-fable-5, no --resume, and the frozen repair.prompt.txt bytes (sha256 5d846901563ddef8b278a88f46e9ccfcd1a372f1e38b475743372c20cdcb4904). Kept the transcript, envelope, stderr, timings, metadata snapshots and full before/after measurements under that project's evidence/iteration19 directory. The compact repair-refusal-iteration19.json receipt cites their digests. No design was changed by the actor.

Fallback: encoded the original retained clearance reports as component-index rows with exact distances and common volumes, preserving all 406 Finch, 276 Robin and 105 Heron pairs. Verified every row against its external source report, the source hashes, absence of omitted error/intent fields, and the 16 KB cap. Each fixture retains revision, world geometry and sweep availability. cli/tests/test_retained_fit.py invokes the real fit_summary and requires the complete named failing set and numbers from the prior comparison receipt, except exactly two explained Heron threshold corrections. It separately pins seating/gap counts and thread-engagement volumes. Tests need neither operator project directories nor an engine build.

## Result

F4 remains open: session-limit refusal after 4.020468473 seconds, exit 1, zero completed design turns, zero transcript tool calls. Both measured reads report 15 failures: 8 intersections, 6 below-clearance pairs and 1 world plane. The earlier seed receipt had 21; ADR-353 removes six nominal 0.1 mm flags (two bearing gaps and four servo/tab-screw gaps). Script, accepted revision, accepted digest and accepted attempt remain unchanged. Normal product restore updates latest_candidate and updated_at only; the receipt reports the metadata difference instead of claiming byte identity. Sweep remains unavailable; no smoke, training or repair claim.

F9's retained classification now has a portable regression: 44/39/20 failures, every pair and number pinned, no unknowns, no world geometry on the current retained revisions, all sweeps unavailable. This does not certify rebuild/restore or complete F9. The focused tests pass (3); restoring the old strict threshold in memory gives the expected Heron failure on precisely the two additional named pairs (1 failed, 2 deselected), proving the regression detects ADR-353's defect. No production code, protocol, payload, dashboard or dependency changed; no build or packaged gate was needed for this test/documentation unit.

Full CLI verification: 684 passed, 1 skipped in 530.16 seconds. Logs and their digests are retained with the second refusal receipt. Fixture equality/cap checks and git diff --check pass. Next unit remains on the ot7 ladder: F4 when the provider can run, otherwise a bounded unblocked F9 unit; never treat these refusals as completed design turns. No new dependency or scope change.

Dispatch closed: 1 unit — F4 provider refusal with portable retained-fit regression fallback for F9.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 32a383895cea8a72a05f899fbaa465c51355bc5b

## State Impact

- target: eager-summit-3153 — All 787 retained pair measurements replay in a portable regression, pinning 44/39/20 failures and explained differences; CLI 684 passed, 1 skipped. Fresh rebuild and wider F9 evidence remain open.
- target: polished-forest-0215 — Second fresh frozen-prompt invocation refused at provider session limit in 4.02 seconds; zero completed design turns, measured before/after 15 failures, accepted identity unchanged.
