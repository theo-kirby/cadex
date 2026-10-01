---
node_id: 7d67c525-eb4a-5bd8-aedd-13a7c55adaf7
slug: blue-cloud-1514
title: 'ot11 grip probe: coupled mechanisms export (ADR-473); two blockers to a grip contract measured'
created_at: '2026-10-01T20:22:33+00:00'
parents:
- silver-light-9977
summary: ''
---
## What

I measured the long-term rung's fourth behaviour, a gripper closing on a target pose, before pre-registering anything. The measurement found a product defect: **no gear, belt or screw coupled mechanism could be exported to MJCF**. I fixed it (ADR-473) with a regression test, and the fixed engine then measured two more gaps that block freezing a grip contract.

- `src/Mod/cadex/CadexDynamics.py`: a coupling's `equality/joint` row now starts from `list(equality.data)`, which is MuJoCo's defaults, instead of `[0.0] * 11`.
- `test_dynamics_coupled.py::test_a_coupled_mechanism_exports_as_the_model_it_simulated[gears|belt|screw]`: fails on the old source (3 of 3) and passes on the new.
- `docs/probes/ot11/runner/grip_probe.py` and `retained/grip-probe.json`: a live-cadexd gripper probe. It uses the ten frozen seeds, and its outputs contain no machine paths.
- `docs/DECISIONS.md` ADR-473, and a new section at the end of `docs/probes/ot11/README.md`, "A fourth behaviour, measured before it is pre-registered". No frozen item changed.

## Why

The critic asked for two things:
1. A reconcile pass folding `silver-light-9977`.
2. Then the long-term rung: pre-register a gripper through the same loop with no new code path, measuring first.

**Deviation on (1):** this dispatch's own rules forbid the reconcile skill in a work iteration "no exceptions", so I did not reconcile. The tail is now two records (`silver-light-9977` and this one) and needs the reconcile pass.

**On (2):** the critic said to measure first, and that measurement became the unit. The smallest gripper the vocabulary allows (two hinged jaws, a 1:1 `gears` coupling, one position servo, a `point` goal on one jaw's tip) was refused by the engine at `assembly.mjcf` (`mjcf_field_drift`, eq_data 1.0 relative). A pre-registration over a mechanism class the product cannot export would be a contract over nothing. So the defect was fixed first, under the "a product fix needs a regression test that fails before it" rule.

Three new directions that serve the mission. I can't write the plan node, so they are listed here:
- **(a) Grip through the same loop.** Decide the two gaps below, then freeze a grip contract and run the agent's loop on it. Chosen, and this unit is its first step.
- **(b) Sim-to-real readiness.** Re-evaluate the accepted R1–R3 policies under declared actuator latency and sensor noise, as conditions of a new spec. The frozen contracts stay unchanged.
- **(c) Out-of-sample robustness.** Evaluate the three confirmed policies on 64 fresh seeds that are not frozen, to measure how far the 10/10 results generalise. This is a report only; no verdict moves.

## Method

- Wrote the probe script (palm, two 8×10×80 mm jaws, hinges ±20°, `gears` r1=r2=10, position servo 400 N·mm/°, `point` goal `tip=fa` offset [0,0,−80], reach predicates, seeds 1101–1110, 4 s).
- Ran it through a live cadexd: refused.
- Reproduced the refusal headlessly on the M2 `_gear_train` fixture: drift 0.5 at 2:1, 1.0 at 1:1.
- Diffed the model against the reloaded file:
  - model `eq_data[0]` = [0, −2, 0, 0, 0, 0, 0, 0, 0, 0, **0**]
  - reloaded = [..., **1**]
  - A fresh `MjSpec.add_equality().data` is `[0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1]`, so the XML parser fills `data[10]` (the weld's torquescale) with 1 for every type.
- Fixed it and checked the regression before and after. `build-engine` and `stage-engine` both succeeded.
- Re-ran the probe. For each seed it draws the goals in the engine's evaluation order (`goals.py`), recovers the driven angle from each target, then compares the jaw gap and contacts at the pose the draw used (follower at rest) with the coupled pose (follower = −driven). It also plays one episode at each end of the servo command.

## Result

**What is true now:**
- Gear, belt and screw mechanisms export to MJCF.
- The gripper script is accepted live, and the coupling is live in the dynamics (jaw B = −jaw A, e.g. driven −0.999° / follower +0.999°).
- **The goal draw ignores couplings.** On the frozen seeds, 3 of 20 targets (1102, 1105 and 1110, segment 1) are coupled poses where the jaws overlap by 0.475, 4.19 and 4.335 mm. The draw read 15.8, 13.8 and 13.8 mm gaps there, because it leaves the follower at rest.
- **Gear-coupled jaws never collide.** The builder excludes contact between the two components of every joint, couplings included, so there were 0 contacts at a 4.3 mm overlap.
- No grip contract is frozen. Nothing in `contract.json` or the frozen README sections changed.

**Receipts at this revision:**
- `pixi run test-engine`: 2532 passed, 61 skipped (2529 before, plus 3 new).
- Packaged lifecycle gate against the restaged `build/engine/cadex-engine-0.0.0-linux-x64`: 23 passed.
- `cli/tests`, CPU-only (`CUDA_VISIBLE_DEVICES="" JAX_PLATFORMS=cpu`): 1290 passed, 1 skipped (19 min 43 s).

**Concerns for the next iteration:**
- The tail has two unreconciled records, and a reconcile is due.
- The ADR-473 change moves `eq_data[10]` only on coupled models. No retained ot5–ot11 model has a coupling as far as I know: none was exportable before.
- Not checked: whether MJX in the training venv handles `equality/joint`. A grip run would need that measured before any training.
- Next unit, direction (a): decide whether the goal draw should place coupled followers by the coupling law before reading contacts and the target. It is a change to what a seed draws for coupled models only, with a regression test. Then decide whether a coupling's contact exclusion should be optional (a gripper's jaws must touch), and freeze the grip contract after both are decided.

Dispatch closed: 1 unit — gear/belt/screw MJCF export fixed (ADR-473, regression fails before), and the gripper probe measured two blockers to a grip contract (coupling-blind goal draw, 3 of 20 frozen-seed targets infeasible; coupled jaws never collide)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 47825e9252929f32ddf3855b10cd3fb221db10c0

## State Impact

- target: salty-isle-4063 — Gear, belt and screw coupled mechanisms now export to MJCF (ADR-473, commit e66b70fc): a coupling's equality row starts from MuJoCo's defaults, because the XML parser fills data[10] with 1 and export_mjcf refused every coupled model. A gripper probe on the frozen ot11 seeds measured two open gaps for a grip behaviour: the point-goal draw leaves coupled followers at rest (3 of 20 targets interpenetrate), and coupled jaws never collide because joint-pair contact exclusion covers couplings.
