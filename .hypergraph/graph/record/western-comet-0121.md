---
node_id: f8d36bb7-69fa-5fca-a60b-c1c12009bd3b
slug: western-comet-0121
title: 'ot10: swept fit now fits a 12-joint robot (ADR-419, hip 287 s -> 7.3 s, 12/12 joints in 112 s); quadruped scored 16/21 but misses A5 on the swept fit'
created_at: '2026-09-27T22:56:58+00:00'
parents:
- quiet-basin-1176
summary: ''
---
## What
Made a 12-joint swept fit fit its budget (ADR-419, commit `f08f336b`). Also scored the A5 quadruped (`ot10-quadruped-2`) on the unchanged engine before the fix landed (commit `98c2564c`).

`_sweep_joint` changes:
- A pair the joint cannot move carries its static solved-pose value and is not measured again.
- A moving pair whose exact-geometry boxes (`optimalBoundingBox(False, True)`) stay more than `_SWEEP_CULL_MM` = 10 mm apart at every sample is published with `culled: true`. Its minimum distance is that box gap, a lower bound; its common volume is 0.0 and its first contact is null.
- Every other moving pair is checked for solved-pose agreement, then measured exactly at every sample, as before.
- `_measure_joint_sweeps` serialises the BREPs once per assembly, not once per joint.

Docs: `docs/XSCRIPT.md`, `docs/INTEGRATION.md` (the new optional `culled` row key) and the ADR-419 entry in `docs/DECISIONS.md`.

## Why
Target: A5 (`loyal-fountain-8709`). Both 63-component attempts miss A5 only because their swept fit is incomplete.

The critic's message:
- **Put the full `cli/tests` result in the record.** Done: at `3a48b1e4` it was 994 passed, 1 skipped, exit 0 (11 min 50 s).
- **Profile one hip joint's sweep on a read-only copy at `996a0b7e`.** Done.
- **Land the cheapest fix, with a regression that fails before it.** Done.
- **Change no engine, build or payload while PID 3670601 lives.** Kept. The quadruped's `cadexd` imports `src/Mod/cadex` directly (`dev-tree` engine), so editing the main tree would have changed the running turn's engine. All source work was done in a separate git worktree (branch `ot10-sweep-fit`, since deleted).
- **Once it exits, score it first, then rebuild and run the packaged gate.** Done in that order.
- **The P2 floor concern needs a recorded re-score decision.** Not slipped in. It is named below as open.

What I did differently: of the three candidate fixes, "serialise each BREP once per sweep" landed but is measured as worth almost nothing (BREP import 0.02 s). The cost was `distToShape`. The critic's "only sweep the pairs a joint moves" was already true of the sample loop. The waste was in the agreement pre-check, which re-measured all 1,953 pairs once per joint.

## Method
**Profile.** I rebuilt a read-only copy of `ot10-hexapod-2` with `cadex params --set sweep_step=15` on the old engine: 12 of 12 joints incomplete, the hip used its whole 90 s, 5 min 28 s wall. An uncommitted worktree-only dump captured each joint's child payload. `cProfile` of the hip child on one CPU:

| measure | value |
|---|---|
| total | 287.0 s |
| `distToShape` | 280.6 s over 4,153 calls: 1,953 from the agreement pre-check, 2,200 from 5 samples × 440 moving pairs |
| `common` | 5.6 s |
| BREP import | 0.02 s |

Per-pair timing: 1,836 of 1,953 pairs have disjoint boxes, and far pairs are the slowest (a hip cap against the opposite tibia, 114 mm apart, 0.8 s).

**Why `optimalBoundingBox`.** A tessellated `BoundBox` sits inside a curved surface (a 10 mm sphere reads -9.994 after `tessellate`), so it cannot bound a distance from below.

**Measured after the fix, one CPU:**

| joint | before | after | measured exactly | culled |
|---|---|---|---|---|
| hip | 287 s | 7.3 s | 19 pairs (114 `distToShape` calls) | 421 of 440 |
| knee | not reached | 19.5 s | 21 pairs | 215 of 236 |

**Real rebuild of a fresh copy, fixed engine:** all 12 joints `complete`, 112.4 s of the 180 s budget (per joint 5.4–15.6 s), 4 min 35 s wall. The client's `sweep_summary` then reads `fail`, on 12 pairs only: each knee drives its tibia (up to 65 mm³) and foot (up to 111 mm³) into `c_floor`.

**Regression.** `test_a_pair_the_motion_cannot_bring_near_is_bounded_not_measured`, real OCCT, fixture with three spheres:
- the near pair stays exact at 0.04 mm;
- the far pair is culled, with a bound above 10 mm and at most the analytic minimum;
- the rigid pair equals its baseline.

It fails on the previous source (no `culled` key) and passes on the fix.

**Quadruped scoring.** The turn ended on its own at 22:32:00Z (43 min 49 s, exit 0, accepted `27ba92c6…`). I ran a copy of pipeline.sh (render, five look views, three blind judge calls), then took P1–P3 from the render summary, the fit from turn.json and the refusals from `refusals.py`, and read each refusal by hand.

**Gates.** `pixi run build-engine` exit 0; `pixi run stage-engine` exit 0. The staged payload carries `_SWEEP_CULL_MM`. Packaged gate: `CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-linux-x64 pytest test_cadexd_lifecycle.py` gave 23 passed.

## Result
- **A 63-component, 12-joint robot's swept fit now completes: 112 s of the 180 s budget, where before 0 of 12 joints completed.**
  - The bound only errs one way. A culled pair can fail a declared floor above 10 mm, but can never pass one wrongly.
  - Static `distance_mm` is unchanged and still exact for every pair.
- **Quadruped (`ot10-quadruped-2`) misses A5 on the swept fit only.**
  - Judged median **16/21**, the best of the run: calls 15, 17 and 16; medians T1 2, T2 3, T3 3, T4 1, T5 2, T6 3, T7 2.
  - P1 **0.004**, P2 **0.238**, P3 **3**.
  - Static fit: 1,953 pairs clear; the only failing row is the floor's advisory world-geometry row.
  - Electronics complete: ESP32, PCA9685, BNO085, D36V50F6, 2S LiPo, 8 × MG90S with horns.
  - The agent turned the sweep off after hitting the budgets (its ADR-009).
  - Weakest trait is T4: the thighs are sharp-edged blocks.
  - None of the four A4 refusal classes recurred (11 refusals; `refusals.py`'s one `horn_style` tag is the drop-outputs guard again).
- **New finding for the next design turns: a complete sweep of a standing legged robot fails on its feet against `c_floor`.** On hexapod-2, every knee sweep drives its foot and tibia into the floor. This is the physical truth for a joint swept with the body held still. Whether a swept limb against the declared floor should count against the swept fit (the static block already treats floor rows as advisory world geometry) is a product decision that has not been made. If it counts, no legged A5 design passes unless its knee range stays off the ground at the stance pose. **Next unit, proposed:** decide and record this with a measured regression, before the next A5 turn. Assumption: I did not make it here, because it changes what the swept verdict means.
- **P2 floor concern, still open:** the inventory's `printed_edges.measured` includes `c_floor` on both attempts. The quadruped's P2 is 0.238 against 0.25, so the concern now matters. It changes a frozen proxy, so it needs a recorded re-score decision (hex3, attempts 1, 2 and the quadruped).
- **Suites at the final revision `f08f336b`:** 
  - `pixi run test-engine`: 2,233 passed, 53 skipped, exit 0.
  - `pytest cli/tests`: 994 passed, 1 skipped, **1 failed**, exit 1. The failure is `test_review_disk_use.py::test_browser_shows_disk_use_for_the_selected_run_and_keeps_history_through_polls`, a headless-browser dashboard test: `page script failed: TypeError: Cannot read properties of null (reading 'click')`.
    - That suite was running at the same time as the engine suite.
    - Rerun alone three times at the same revision, it passed 3 of 3 (about 4 s each).
    - It passed in the full run at `3a48b1e4`, and nothing in this change touches the dashboard.
    - I read it as a load-dependent flake, not a regression. It is named here so the next iteration can watch for it.
- Nothing new is running. There are no dependencies. The tail is now 3 unreconciled records, so a reconcile is due.

Dispatch closed: 1 unit — the swept fit now fits a 12-joint robot (ADR-419: bounded far pairs, no rigid re-measure; hip 287 s → 7.3 s, all 12 hexapod joints complete in 112 s); quadruped scored 16/21 but misses A5 on the swept fit, measured before the fix landed

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: f08f336b85f89556f0546f29c859c7786a398efc

## State Impact

- target: loyal-fountain-8709 — ADR-419 (f08f336b): the joint sweep bounds far moving pairs (>10 mm box gap, culled lower bound) and stops re-measuring rigid pairs; ot10-hexapod-2 now sweeps 12/12 joints in 112 s of the 180 s budget (was 0/12), and the complete sweep fails only on knee foot/tibia vs c_floor, an undecided policy question; quadruped attempt ot10-quadruped-2 (27ba92c6) scored 16/21 median, P1 0.004 P2 0.238 P3 3, static fit clean, swept fit off (budget), so it misses A5
- target: odd-tree-6681 — quadruped transcript: none of the four A4 refusal classes recurred (11 refusals)
