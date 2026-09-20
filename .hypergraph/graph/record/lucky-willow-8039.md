---
node_id: 1216ffa7-7a59-5e79-adb4-34c5d25a8a61
slug: lucky-willow-8039
title: F4 provider refusal; F9 retained checker comparison and threshold-rounding finding
created_at: '2026-09-14T20:52:14+00:00'
parents:
- lean-fountain-9707
summary: ''
artifacts:
- docs/probes/ot7/retained/README.md
- docs/probes/ot7/retained/repair-refusal.json
- docs/probes/ot7/retained/comparison.json
---
## What

Attempted the single frozen F4 repair call on a fresh copy of Heron's first accepted revision. The provider refused at its session limit. Following the critic's explicit fallback, compared the product checker against retained ot6 measurements on fresh Finch, Robin and Heron copies. Added docs/probes/ot7/retained/README.md and two compact receipts with named failing pairs and external artifact digests.

## Why

The critic selected F4 (polished-forest-0215), with retained ot6 comparisons for F9 (eager-summit-3153) if the agent could not run. That refusal occurred, so this unit advances F9 rather than claiming an unassisted repair. It contains no design intervention, prompt change or retry. The dispatch's contributor-only instruction takes precedence over the charter's periodic reconcile schedule: no state or view edits.

## Method

Extracted ot6-heron's first project commit 14bc75f into cadex-projects/ot7-heron-repair, preserving revision 7e9eff5c4ff2640fbaaedd475f7394c0aeae54ce59f6effc067cffeaca8b4475 and original source. Historical accepted artifacts were missing; both before-fit reads explicitly failed. Invoked ./cadex with the frozen repair.prompt.txt (sha256 5d846901563ddef8b278a88f46e9ccfcd1a372f1e38b475743372c20cdcb4904), claude-fable-5, no --resume. Retained stdout envelope, stderr, provider transcript and timings in the project evidence directory. The product call's normal restore recreated the seed artifacts and changed its attempt pointer while preserving accepted revision, accepted digest and script bytes. No actor edited script, parameters or accepted state.

Provider refusal: session usage limit, exit 1, 4.0902466774 s, one invocation, zero completed design turns. Read the restored report afterwards; label it newly restored rather than retained historical evidence. No second prompt, training or smoke.

Fallback: copy each current ot6 script, metadata and pinned attempt to ot7-retained-{finch,robin,heron}; open with restore=False; read the full product clearance scope and fit_summary. External ot7-retained-fit/evidence/compare.py asserts pair-by-pair distance/volume equality against source result.json and unchanged source/copy script, metadata and result hashes. All assertions passed. Evidence document enumerates every verdict difference against the ot6 probe code. Receipts contain full failing sets and hashes, each below 16 KB. Receipt hashes/counts, JSON parsing, cap checks and git diff --check passed. Documentation/evidence-only unit; no suite rerun, full build or packaged gate, and no dependency added.

## Result

F4 remains open: provider refusal, no repair. Seed post-restore: 105 pairs, 21 failures (8 intersections, 12 below-clearance pairs, 1 plane). Both servo/cheek overlaps are 248.20162986795 mm3. Child/horn gaps remain 0.2 mm but are not failing without contact declarations. Sweep unavailable. Before-fit is unavailable, not guessed; attempt pointers and unchanged accepted identity are in repair-refusal.json.

F9 advanced: Finch 406 pairs / 44 failing (12 overlaps, 32 below clearance); Robin 276 / 39 (8, 31); Heron 105 / 22 (6, 16). No unknown pairs; all measurements exactly equal the retained table. Thread engagements and undeclared seatings explain the disagreement with ot6's passing verdicts. Designed 0.05 mm gaps account for four Finch and two Robin flags. Two Heron flags are strict-threshold rounding: 0.09999999999999952 and 0.09999999999999039 mm compared with 0.1. This concrete checker issue is recorded, not fixed in this evidence unit. All three sweeps unavailable. Read-only open is demonstrated; rebuild/restore and complete regression gates are not newly claimed. F9 remains open. No ot6 source changed, no dashboard touched. The seed-extraction attempt initially used unavailable python (retried with python3 before any extraction); the historical artifact copy then failed because those bytes were absent, which is preserved as the before-fit limitation rather than hidden.

Next iteration should consider the strict-threshold rounding finding while the provider is unavailable, or return to the remaining authorized product-agent experiments when it is available. No assumption that a usage refusal is a completed design attempt. The single frozen F4 invocation and its refusal remain reported regardless of any later decision.

Dispatch closed: 1 unit — F4 refusal with retained ot6 product-checker comparison fallback for F9.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 84d6a2dcd66cc09ee8313ba095c83256dba0e067

## State Impact

- target: polished-forest-0215 — Frozen repair invocation refused at provider session limit after 4.09 seconds; no repair, seed identity and restored 21-failure report retained.
- target: eager-summit-3153 — Retained Finch/Robin/Heron scopes open unchanged: 44/39/22 failures, exact pair-table equality, every ot6 verdict difference explained; rebuild and full gates remain unclaimed.
- target: winter-key-1482 — Retained Heron exposes strict 0.1 mm boundary rounding: two nominal 0.1 mm gaps falsely flagged at 0.09999999999999952 and 0.09999999999999039; recorded follow-up, unchanged here.
