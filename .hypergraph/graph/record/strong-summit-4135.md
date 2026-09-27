---
node_id: 3d95c731-4a6c-547e-81e8-cb86218b9640
slug: strong-summit-4135
title: 'ot10: the 300 CPU-s cap was mostly thread overhead; workers pinned to 4 CPUs, 15 of 19 hexapod refusals now accept (ADR-418)'
created_at: '2026-09-27T20:46:59+00:00'
parents:
- crimson-aspen-7756
summary: ''
---
## What

I measured where `ot10-hexapod-1`'s 300 CPU-second worker budget went, and I made the dominant cost cheaper without changing the cap (ADR-418, commit `d14f3b32`).

- **The cause.** The pairwise fit's `distToShape` runs OCCT's multithreaded extrema, and OCCT sizes its pool from every CPU it can see. On this 32-CPU host, most of the cap was being charged for thread overhead.
- **The fix.** `cadex_domain_worker._resource_limits` now pins every xscript worker to `WORKER_CPUS = 4` by affinity. Its threads and its sweep child inherit the pin, and which four CPUs rotates with the pid.
- **The effect.** **15 of the turn's 19 CPU refusals are now accepted** under the unchanged 300 CPU-s cap.

## Why

This is the critic's named unit: profile the 300 CPU-s budget on the hexapod's own refused revisions, split the time by phase, and cut the dominant cost with a regression test. Do not raise the limit.

- The critic's fix-first item: A2's 60 s bar now covers drawing only. It is declared below as an impact on `sweet-arbor-1947`, which withdraws soft-spark-6990's whole-command claim. I cannot write state nodes.
- **Deferred to later units, as ordered:**
  - the `joint_cap` retire refusal;
  - the look-views runner;
  - the quadruped and biped probes.

## Method

- **Rebuilding the candidates.** I rebuilt all 51 `write_script`/`edit_script` candidates from the turn's transcript: full sources, plus `replacements` applied to the then-accepted revision from `script_history/`. Every reconstructed accepted candidate equals its history file.
- **Replay setup.**
  - Each candidate was replayed through the pre-fix project worker bundle.
  - It used the accepted attempt's own `request.json` with the source swapped in, run by `FreeCADCmd --safe-mode` under `worker_environment`.
  - Each run recorded its rusage and a cProfile.
- **Phase split.** Wall time, from the cProfile of the accepted revision `7af6db09` (46 components, 1,035 pairs):
  - total 28.7 s;
  - pairwise fit (`_measure_clearance`) 24.3 s, of which `distToShape` is **21.2 s** and `common` is 2.0 s;
  - build 1.7 s;
  - publish (serialise) 2.1 s;
  - display tessellation 1.3 s;
  - sweep 0 s (none declared).
- **Largest refused candidate (15, the first assembly), uncapped on all 32 CPUs.** It used 138 s of wall and **1,346 CPU-s**:
  - `distToShape` 107.2 s;
  - `common` 8.3 s;
  - build 12.3 s;
  - publish 13.1 s;
  - tessellation 1.8 s;
  - sweep 2.4 s.
- **CPU-count grid** (`taskset`, pre-fix code). Each cell is CPU-s over wall s.

  | candidate | 1 CPU | 2 CPUs | 4 CPUs | 32 CPUs |
  |---|---|---|---|---|
  | accepted 51 | 70 / 71 | 111 / 65 | 94 / 31 | 280 / 28 |
  | refused 50 | 101 / 101 | – | 164 / 59 | – |
  | refused 21 | 390 / 390 | 415 / 223 | 450 / 138 | – |
  | refused 15 | – | 692 / 379 | 740 / 236 | 1,346 / 138 |

- **The fix.** Four CPUs keep the wall close to unpinned (+10%). The sweep and every other phase still get parallelism. This follows ADR-250, which pins BLAS: the same four on every host.
- **After the fix.**
  - The accepted revision uses **94.5 CPU-s over 32.1 s**, down from 280 over 28.1, with no `taskset`.
  - Its output digest `ab571337…` is identical before and after.
  - All 19 CPU refusals were replayed on the fixed worker under the real 300 CPU-s cap, in seven lanes of four CPUs.
- **Tests.** There are three regressions in `cadex_tests/test_scripted_process.py`:
  - a mocked 32-CPU host is pinned to four CPUs, rotated by pid;
  - a host with two CPUs keeps both;
  - a real worker process's thread and child both see four CPUs.
  - The first and third fail on the previous source, on this host.

## Result

- **15 of 19 refused candidates are now accepted**, at 86–223 CPU-s and 31–79 s of wall. These are 22, 28, 30, 31, 34, 36, 38, 39, 40, 41, 43, 44, 45, 46 and 50.
  - They include loft-carapace revisions 22 and 28, which ADR-003 of the agent's project says it abandoned for cost.
- **4 are still refused**: 15, 16 and 17 (the first full assemblies) and 21 (a loft revision). Their single-CPU cost is 390 s or more, which is real exact-distance work rather than overhead.
- **What is true now.** The dominant cost of a many-part accept is still exact `distToShape` over every pair. The next lever is cheaper exact distance for far-apart pairs. It changes what `distance_mm` promises (the review table and `smoke_geometry` both read it), so it is a separate decision. I did not take it here.
- **Verification.**
  - `pixi run test-engine`: 2,232 passed, 53 skipped.
  - `pixi run python -m pytest cli/tests`: 993 passed, 1 skipped.
  - Rebuilt and staged `build/engine/cadex-engine-0.0.0-linux-x64`, which carries `WORKER_CPUS`. The packaged gate `test_cadexd_lifecycle.py` passed, 23 of 23.
- **Docs.** `docs/XSCRIPT.md`, `docs/ARCHITECTURE.md` (date bumped) and ADR-418.
- **Concern.** The replays used the dev-tree `FreeCADCmd` and the source-tree bundle, not the payload. The payload's behaviour is covered by the gate, not by the replay numbers.
- **Assumption.** Four is the right count. Two costs more wall for about the same CPU; one is the cheapest in CPU-s but more than doubles the wall. The receipts are in the grid above.
- **Unchanged.** The engine's CPU cap and wall timeout.
- **Next.**
  1. The `joint_cap` retire refusal.
  2. The look-views runner.
  3. Then quadruped and biped attempt 1, or hexapod attempt 2.
- **Tail.** This is the third unreconciled record (soft-spark-6990, crimson-aspen-7756, this one), so a reconcile is due.

Dispatch closed: 1 unit — profiled the hexapod's 300 CPU-s refusals (distToShape = 74–78% of wall, inflated about 3× by 32-CPU OCCT threading); pinned workers to 4 CPUs (ADR-418); 15 of 19 refused candidates now accept, with the digest unchanged

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: d14f3b32065f06ec5c122ee1370b8656f5567a22

## State Impact

- target: loyal-fountain-8709 — The binding constraint on attempt 1 is measured: distToShape over 1,035 pairs was 74-78% of accept wall time, and 32-CPU OCCT threading tripled its CPU-s charge (accepted rev 280 CPU-s → 94 pinned). ADR-418 pins workers to 4 CPUs; 15 of the turn's 19 CPU refusals now accept under the unchanged 300 CPU-s cap; 4 (first full assemblies 15-17, loft rev 21) remain above it on real exact-distance work (≥390 CPU-s single-thread). Quadruped/biped may proceed.
- target: forest-wind-0342 — Every xscript worker is pinned by affinity to WORKER_CPUS=4 (ADR-418, commit d14f3b32), inherited by threads and the sweep child, so RLIMIT_CPU no longer depends on host core count; the accepted digest is unchanged; packaged gate 23/23.
- target: sweet-arbor-1947 — Per the owner's clarified charter, A2's 60 s bar covers drawing once tessellation is acquired, and the rebuild is reported separately. ot10-hexapod-1's drawing (5.9 s, hero 2.1 s) meets it. soft-spark-6990's claim that A2 is incomplete on whole-command time is withdrawn; the rebuild times (29.3 s hexapod, 207 s hex3) stand as separate figures.
