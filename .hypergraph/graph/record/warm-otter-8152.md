---
node_id: a6c9bebc-037f-5e8c-bd5e-2f193cb0657c
slug: warm-otter-8152
title: 'ADR-582: smoke reuses a pair''s volume while its relative pose holds'
created_at: '2026-10-07T01:28:12+00:00'
parents:
- solemn-moon-8508
summary: ''
---
## What

ADR-582, commit `666b436b`. `cadex smoke`'s exact-geometry child (`cli/cadex_cli/smoke_geometry.py`) now does two things differently:
- **Reuses a pair's volume while its relative pose holds.** A common volume does not change when both shapes move rigidly together. So a pair whose relative placement matches, within 1e-9 per matrix entry, the pose at which it was last measured keeps that volume. Otherwise the boolean runs again.
- **Computes each part's exact box once at frame 0.** Before, it computed both boxes again for every culled pair.

`smoke-geometry.json` now carries `booleans: {run, reused}`.

Result: smoke blocker (c) is fixed. On the 66-component fresh-session biped, the full command took 300.11 s and was refused. It now takes 186.66 s and writes a complete receipt.

## Why

The critic named blocker (c), the per-frame cost on 66 components, and asked me to try ADR-436's rule first.
- **What I did instead.** I measured that rule and did not adopt it. Over frames 1–3, the shell distance that would prove a pair apart cost 13.6 s, against 15.1 s for all the booleans. Only 166 of the 433 box-overlapping pairs were apart, so the rule cannot pay for itself here.
- **The cheaper rule, also exact.** The relative-pose rule is exact by rigid-motion invariance and costs one matrix comparison per pair.
- **What I kept.** I followed the rest of the critic's message:
  - a before and after on the orun4-fresh-legged-2 copy, against the 300 s bound;
  - no slow test;
  - the suite under 480 s.

## Method

1. Copied `~/cadex-projects/orun4-fresh-legged-2` to `/tmp/o4s`. Ran the full `cadex smoke`: 300.11 s, `exact smoke geometry exceeded the shared wall-time bound`.
2. Re-ran with `--timeout 40` to keep a trace. Built standalone child plans for 1, 6 and 101 frames.
3. Profiled frames 1–3 with FreeCADCmd. Per frame:
   - placement and the AABB cull took under 0.4 s;
   - the booleans took about 5.0 s;
   - shell distance and per-pair exact boxes each cost as much as the booleans or more.
4. Measured relative-pose stability over all 101 frames:
   - 527 of the 2,080 pairs are rigid, and their relative matrices differ by at most 8.6e-19;
   - every moving pair differs by more than 1e-6.
5. Implemented both savings and compared against the old child on 6 frames:
   - all 2,080 worst volumes agree within 3.7e-11 mm³;
   - the same 33 pairs fail;
   - the only difference is the reported worst-frame time of 25 rigid pairs. The old child picked the frame where boolean noise of about 1e-14 mm³ peaked; the new one reports the first.
6. Extended the nested-sphere test to three frames: a rigid carry, which reuses, then a 1 mm nudge, which runs again. It asserts `booleans == {run: 2, reused: 1}` and fails on the old child.

## Result

What is true now:
- Full `cadex smoke` on the copy: **186.66 s, complete receipt, verdict `fail`**. It was refused at 300.11 s.
- The geometry child alone:
  - frame 0 went from 64.7 s to 12.2 s;
  - the 101-frame run takes 185.7 s, about 1.7 s for each later frame;
  - 4,845 booleans ran and 9,797 were reused.
- Updated: ADR-582 in `docs/DECISIONS.md`, the smoke section of `docs/CLI.md`, and the orun4 `REPORT.md` (§7 defect 2 and the ADR table).
- Gates at `666b436b`, both run in the foreground:
  - the CLI suite as one command with the GPU hidden: 1212 passed, 1 skipped, in 474.17 s (still under 480 s);
  - `pixi run test-engine`: 2611 passed, 59 skipped, in 345.69 s.
- Nothing under `src/` or the payload changed, so no engine rebuild or packaged gate was needed.

Still open:
- **Blocker (b).** The 33 failing pairs are all bolts threaded into their parts, at 4.5–10.3 mm³. The per-frame check ignores the static row's fit intent. This is the next unit.
- A design with many moving, box-overlapping pairs still pays one boolean per pair per frame.
- The reconcile tail is two records.

Dispatch closed: 1 unit — smoke's exact-geometry stage completes inside the 300 s bound on 66 components (ADR-582)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: 666b436bdc96b2e8c138a78c3874a0afe4fbbb98

## State Impact

- target: salty-isle-4063 — cadex smoke's exact-geometry stage reuses a pair's common volume while its relative pose holds and boxes each part once (ADR-582): the 66-component fresh-session biped's smoke completes in 186.66 s where it was refused at the 300 s bound. Still open: threaded bolts counted as overlap (33 pairs)
