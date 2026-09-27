---
node_id: 893a2ced-eeb4-5efd-a02f-e39fbcd98b6a
slug: fresh-timber-5181
title: 'ot10: a swept finding against world geometry is advisory (ADR-420); hexapod-2 replay goes from 12 floor-only failures to a complete sweep pass'
created_at: '2026-09-27T23:24:29+00:00'
parents:
- western-comet-0121
summary: ''
---
## What
Made the swept fit treat findings against world geometry as advisory (ADR-420, commit `9cf27ea6`). A swept finding counts as advisory when one side of the pair is a component the static block names world geometry, such as `c_floor`. This covers an intersection, a closed gap or an unmeasured pair.

`sweep_summary` in `cli/cadex_cli/clearance.py` now publishes such findings:
- under a new `fit.sweep.world_geometry`, with the engine's reason;
- with `world_geometry_count` and a `world_geometry_note`;
- never in `failing`, `failing_count` or the verdict.

A printed or purchased pair still fails. Other changes that go with it:
- The progress line (`bridge._sweep_line`) appends `; N against world geometry (advisory)`.
- The prose report prints each finding marked advisory.
- The overlay says so in one sentence.
- `docs/CLI.md`, `docs/XSCRIPT.md` and ADR-420 changed in the same commit.

## Why
Target: A5 (`loyal-fountain-8709`). The critic asked for this exact unit:
- treat limb-against-`c_floor` swept pairs as advisory, in the same terms as the static block;
- keep printed and hardware pairs failing;
- write an ADR;
- add a regression that fails before the change;
- replay `ot10-hexapod-2`, failing only on floor rows before and passing a complete sweep after.

All of it is done. P2's floor bug is left for its own re-score unit, as asked. The critic also said to run the frozen biped prompt with the sweep on "after that". That is a second unit (a product turn of about 45 minutes), so under the one-unit rule it is the next iteration's work and was not started here.

## Method
**Where the rule lives.** It is a client verdict change only. The engine, the protocol, `OP_ARG_SPECS` and the published measurements are untouched, so no rebuild, stage or packaged gate was needed. The rule reuses the engine's existing world-geometry detection (`_check_fit`: a collision plane on a design body, a surface-only plane, or `world=True`), not a component name. The joint rows' extrema still include the floor, because they are measurements.

**Replay.** I copied `ot10-hexapod-2` to `/tmp/hx2-sweep`; the original stays read-only. I rebuilt the copy with `./cadex params --set sweep_step=15` on the ADR-419 engine: 3 min 27 s wall, exit 0. I read its published `inspect scope=clearance` value and judged it with both versions of `clearance.py`, `HEAD~` and the fix:

| | static | sweep verdict | joints complete | failing | world geometry |
|---|---|---|---|---|---|
| before | fail (1 row: world geometry) | **fail** | 12/12 | 12, all `c_floor ∩ c_{tibia,foot}_*` intersections | — |
| after | fail (1 row: world geometry, unchanged) | **pass** | 12/12 | 0 | 12 |

The measured rows were the same on all six legs:
- tibia 65.309 mm³ on every leg;
- foot 110.972 mm³ on the left legs and 97.098 mm³ on the right;
- knee range [-35°, 35°] at 15°, 6 samples.

After the fix, the progress line reads `sweep pass: 12 joint(s) swept; 12 against world geometry (advisory)`.

**Regressions** in `cli/tests/test_clearance.py`:
- `test_a_leg_swept_into_the_floor_is_reported_not_failed` uses the measured `j_knee_fl` rows.
- `test_only_world_geometry_is_advisory_in_the_sweep` puts a printed intersection, a purchased below-clearance pair and an unmeasured pair beside the floor rows. Each must still fail.

With the previous source stashed, all 4 fail. On the fix, all 4 pass.

**Suites at `9cf27ea6`:**
- `pixi run test-engine`: 2,233 passed, 53 skipped.
- `pytest cli/tests`: 997 passed, 1 skipped, **2 failed**, exit 1. The two failures are:
  - `test_review_lifecycle.py::test_restarting_the_dashboard_keeps_the_review_and_leaves_training_alone`
  - `test_review_lifecycle.py::test_copied_project_reopens_without_source_and_keeps_edits_isolated`

  Both raised `BrokenPipeError` in `cli/cadex_cli/browser.py:115`, the headless browser. Rerun alone three times, they passed 3 of 3. They touch no clearance code. This is the same class of load-dependent headless-browser flake as last iteration's `test_review_disk_use`.

## Result
- **A standing legged robot's complete swept fit can now pass.** Its floor contact is reported by name, marked advisory and kept out of the verdict. Any printed or purchased pair that overlaps or closes during a sweep still fails.
- **The attempts already scored keep their verdicts.** `ot10-hexapod-2` and `ot10-quadruped-2` still miss A5: their accepted revisions were accepted with the sweep turned off, so their swept fit remains incomplete. The replay proves that the geometry of `ot10-hexapod-2` passes the swept fit at 15° on a copy. It is not an accepted A5 design, because the actor may not re-accept product geometry.
- **Not changed:**
  - The static verdict still reads `fail` on the world-geometry row itself, which A5 already reads as advisory.
  - P2 still counts `c_floor` in `printed_edges.measured`. This is a frozen-proxy change that needs its own recorded re-score of hex3 and attempts 1, 2 and the quadruped. It matters for the quadruped: P2 0.238 against a 0.25 bar.
- **Next unit, per the critic:** run the frozen biped cold prompt on a new `ot10-*` project, with the sweep left on. Record the flags, the model and `CADEX_EFFORT`.
- **Flake to watch:** the headless-browser review tests fail under full-suite load (2 of them this time), and pass alone.
- **No new dependency.** The tail is now 1 unreconciled record.

Dispatch closed: 1 unit — swept findings against world geometry (the floor) are advisory (ADR-420); ot10-hexapod-2 replay goes from sweep fail (12 floor rows only) to a complete sweep pass

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 9cf27ea6141cc16fec9e2408a83d7909730058fc

## State Impact

- target: loyal-fountain-8709 — ADR-420 (9cf27ea6): the CLI swept fit reports pairs against world geometry (c_floor) under fit.sweep.world_geometry and never fails on them; printed/purchased pairs still fail. Replay of ot10-hexapod-2 at sweep_step=15: sweep fail (12 knee-vs-floor rows only) -> pass, 12/12 joints, 12 advisory. Scored attempts keep their verdicts (accepted with sweep off). Next: frozen biped prompt with sweep on
