---
node_id: 291d3251-1c3e-555a-b9ff-7d5c514657f0
slug: scarlet-hill-8037
title: G4. The balancer's failed smoke has an actionable measured diagnosis
created_at: '2026-09-20T18:48:22+00:00'
parents:
- ancient-vine-9908
summary: ''
---
Status: working

## Current

**Met in its evidence, pending the owner's tick: the balancer's failed smoke is diagnosed as a missing feedback control, not a design defect and not an export mismatch [rec: stormy-sand-3570].** Measured on `ot8-robin`, an independent mechanical copy of `ot7-robin-c` validated against `baselines.json` and taken up with `--turns 0` — no prompt dispatched, no slot spent (ADR-402, commit `a1d12093`) [rec: stormy-sand-3570]. The ordinary holding smoke reproduces the published numbers exactly: `support` 102.2°, `termination` 0.660 s, four penetrations all against `environment/floor` [rec: stormy-sand-3570].

The three candidate causes, separated by measurement [rec: stormy-sand-3570]:

- **Geometry/export mismatch — ruled out.** 28 of 28 bodies agree with `result.json` (worst 1.35e-29 mm, 0.0°); the smoked model is the accepted export byte for byte; the smoke's exact-BREP check passes on 378 pairs across 51 poses with `initial_pose_agrees` true. [rec: stormy-sand-3570]
- **Design defect — ruled out.** Two floor contacts 96 mm apart form a support *line*; centre of mass 0.365 mm off it and 52.40 mm above it (187.93 g). Holding the pose costs 0.672 N·mm against the 184.365 N·mm the design's own motors declare — a 274× margin, static authority to 89.6° of tilt. [rec: stormy-sand-3570]
- **Missing feedback control — confirmed.** Unstable eigenvalue 11.59 /s (86.3 ms); both torque motors are commanded 0.0 because the smoke holds position servos only (`smoke_runner.py:163`); replaying the zero-command rollout reproduces the published fall to the receipt's digits (102.2339672°). [rec: stormy-sand-3570]

The four penetrations are not a fifth finding: two are post-fall impacts, two are standing contact compression (0.576 mm vs a 0.5 mm tolerance) that scales with load, i.e. the engine's fixed 20 ms contact spring rather than geometry. Treated as a secondary, non-blocking observation — a reversible assumption the receipt's load sweep lets a reader argue with [rec: stormy-sand-3570].

**The missing control contract, recorded and the experiment stopped** [rec: stormy-sand-3570]: read the 20 channels already exported as nine sensors; command two wheel torques at ±92.18 N·mm at 50 Hz (4.3 samples per e-fold); hold `chassis_pos_z ≥ 75.25 mm` (45.573° of tilt) inside the smoke's 30° support limit for the declared 8 s episode, from resets varying tilt to 3° and height by 3–5 mm. Supplying it needs training or a hand-authored controller, both forbidden by the charter. `resolve.prompt.txt` was therefore not dispatched; `ot8-robin` is paused with all four prompts unspent and `ot7-robin-c` untouched. Nothing was grounded, supported, suppressed, weakened or shortened. **This is a control-blocked outcome, not a design success** [rec: stormy-sand-3570] [rec: rough-ridge-4729].

Artifacts: `docs/probes/ot8/runner/balance_diagnosis.py`, pinned by `cli/tests/test_balance_diagnosis.py` (11 tests), receipt `docs/probes/ot8/retained/g4-robin-diagnosis.json` [rec: stormy-sand-3570].

*Reconcile judgement*: `Status: working` means the **criterion** (an actionable measured diagnosis) has its evidence, matching G2/G3's convention; it does not mean the balancer works. The design outcome is control-blocked and is carried as negative knowledge below [rec: stormy-sand-3570] [rec: rough-ridge-4729].

## Negative knowledge

- [scope: ot7-robin-c / ot8-robin under ordinary `cadex smoke` hold mode, which commands torque motors zero | confidence: high | evidence: stormy-sand-3570] A no-feedback holding smoke cannot pass this balancer as designed: the measured unstable eigenvalue is 11.59 /s and the zero-command fall reproduces to the receipt's digits. Geometry changes or re-export will not change the verdict; only a feedback controller or trained policy would, both outside ot8's charter.

## Provenance

- keen-stone-1720 — the criterion as the ot8 charter declares it, including the bars on hiding the failure
- humble-fox-6370 — the balancer's failed holding smoke as an ot7 outcome carried forward
- stormy-sand-3570 — G4 measured: export and design ruled out, missing feedback confirmed, control contract recorded, no slot spent (ADR-402)
- rough-ridge-4729 — the closing report carries G4 as control-blocked, not a design success
