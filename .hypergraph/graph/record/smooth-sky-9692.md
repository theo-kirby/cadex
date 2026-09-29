---
node_id: d8cbdc9e-eb98-55c0-a793-d3c40e6dd174
slug: smooth-sky-9692
title: 'ot10: ADR-426 sweep pair budget counts moving pairs; hexapod-6 hips 770, knees 332; replay 0/12 -> 12/12 in 97.9 s'
created_at: '2026-09-28T09:22:54+00:00'
parents:
- true-rose-1584
summary: ''
---
## What

Changed the swept fit's pair budget to count only the pairs a joint moves, which are the only pairs the sweep measures (ADR-426, commit `c8e02559`). First I measured, read-only, how many moving pairs each joint of `ot10-hexapod-6` has. The limit stays 2,000, and the refusal reason now names the count. A real-kernel regression test fails on the old source. Replaying the accepted revision on a second `/tmp` copy took its sweep from **0/12 to 12/12 complete at 5° in 97.9 s**.

## Why

The critic named this unit. First, measure each joint's moving pairs on `/tmp/ot10-hexapod-6`, read-only. If the numbers confirmed the diagnosis, change the pair budget to count only the pairs the sweep measures, with a regression test that fails on the old source and an ADR, keeping 2,000. This serves A5 (`loyal-fountain-8709`): the budget is what failed hexapod attempt 6's swept-fit coverage. I did it as asked. The static floor-contact rows are the critic's next unit and were not touched here.

## Method

1. **Measurement (read-only).**
   - Read `/tmp/ot10-hexapod-6`'s accepted-revision `result.json` (`3cb2b1d0`, attempt `…934885`).
   - Rebuilt each joint's moving subtree with `CadexDynamics.extract_tree`, the same way `_sweep_joint` builds it.
   - Result: 87 components and 3,741 pairs, with no closures, couplings or static joints. Each of the 6 hips moves 10 components, **770 moving pairs**. Each of the 6 knees moves 4, **332 moving pairs**. This confirms the prior diagnosis exactly.
2. **Change** (`cadex_assembly_worker.py`, `_sweep_joint`).
   - The budget check moved after the moving set is computed.
   - It now counts baseline rows whose two sides straddle the moving set, and raises `pair budget exceeded: N moving pairs, more than 2000`.
   - `_SWEEP_MAX_PAIRS` stays 2,000, now with a comment.
3. **Regression** (`test_joint_fit_sweep.py::test_known_angle_…`).
   - The existing hinge driver gets a `crowded` case: 64 far grounded 2 mm blocks, giving 2,145 pairs, 65 of them moving.
   - The test asserts: coverage `complete`, 65 `relative_motion` rows, 2,145 rows, and the hinge's own row identical to the two-component run. The existing `pair_cap` case (2,001 moving rows) must still refuse, with the count in its reason.
   - On the old source it fails at `assert 'incomplete' == 'complete'`; on the new source the file gives 12 passed.
4. **Replay.**
   - `pixi run build-engine` (the Python install only).
   - `cp -a /tmp/ot10-hexapod-6 /tmp/ot10-hexapod-6-replay`, then `./cadex params --project /tmp/ot10-hexapod-6-replay --set fasteners=1 --json` (4 min 32 s). This rebuilt the same revision `3cb2b1d0`.
   - Read `outputs[259].clearance_sweep` and ran the CLI's `sweep_summary` on it.
5. **Docs.** `docs/XSCRIPT.md` now says "2,000 moving pairs", and ADR-426 is appended to `docs/DECISIONS.md`.

## Result

- **What is true now.**
  - A joint's sweep is refused on pair count only when the pairs it moves exceed 2,000.
  - On the accepted hexapod-6 request, every joint now sweeps. Hips took 6.1–7.5 s and knees 9.0–10.0 s, with 22–31 exactly measured moving rows each; the total was 97.9 s of the unchanged 180 s.
  - `sweep_summary` reads the result as **pass**: coverage complete, 12/12 joints, 0 failing pairs. It also lists 12 world-geometry rows (six feet at 196.9 mm³ and six shins at 101.0 mm³ through `c_floor` at knee extremes), which are advisory under ADR-420.
  - Servo-to-horn rows read 0.0 mm with zero volume and do not fail.
- **Not a pass for attempt 6.**
  - The accepted project and its published verdict are unchanged. The replay ran on a `/tmp` copy.
  - The accepted static pass still reports six feet `below clearance` on `c_floor` at 0.0 mm. That is the critic's next unit: a recorded decision, consistent with ADR-420, on world-geometry contact in the static pass.
- **Suites.**
  - `pixi run test-engine`: 2,239 passed, 53 skipped.
  - Packaged lifecycle gate on the restaged payload (`stage-engine`, the worker diffed equal): 23 passed.
  - `pytest cli/tests`: 1,008 passed, 1 skipped (11 min 29 s).
- **Tail.** 3 unreconciled records once this one lands. The critic asked for a reconcile once the third record lands.
- **No new dependency.**

Dispatch closed: 1 unit — measured ot10-hexapod-6's moving pairs (hips 770, knees 332, against 3,741 in the assembly), then made the sweep's pair budget count moving pairs only, keeping the 2,000 limit (ADR-426, c8e02559), with a regression test that fails on the old source. A /tmp replay of the accepted revision went from 0/12 to 12/12 complete and passing in 97.9 s. The static floor-contact rows remain, as the next unit.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: c8e02559a0851ed58a28a072c9afee2b740143a3

## State Impact

- target: loyal-fountain-8709 — ADR-426 (c8e02559): the swept fit's 2,000-pair budget now counts only the pairs a joint moves (the only ones measured); on ot10-hexapod-6 (87 components, 3,741 pairs) hips move 770 and knees 332, and a /tmp replay of the accepted revision 3cb2b1d0 went from 0/12 (pair budget exceeded) to 12/12 complete, pass, in 97.9 s (12 advisory c_floor rows). Attempt 6's accepted project and verdict are unchanged; its static pass still reports six feet below clearance on c_floor, the next unit
