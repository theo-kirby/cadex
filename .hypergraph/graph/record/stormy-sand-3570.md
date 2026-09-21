---
node_id: fccde3ee-fb4a-5ae1-a690-fef6b549c257
slug: stormy-sand-3570
title: 'G4: the balancer''s failed smoke is a measured control requirement, not a design defect'
created_at: '2026-09-21T01:16:23+00:00'
parents:
- winter-creek-7660
summary: ''
---
## What

G4's diagnosis, measured and closed without dispatching a prompt or spending a
slot. `ot8-robin` is an independent mechanical copy of `ot7-robin-c`
(`evidence/`, `agent.json` and `.cadex-cli.lock` left behind), validated
against `docs/probes/ot8/baselines.json` by the collector and taken up with
`--turns 0`, so it wrote the seeded "before" measurement and dispatched
nothing. The balancer's ordinary `cadex smoke` failure is separated into its
three candidate causes by measurement, and the answer is the third:
**a missing feedback control**, with the exact missing contract recorded.

Landed as `a1d12093` (ADR-402): the diagnosis tool
`docs/probes/ot8/runner/balance_diagnosis.py`, its regression
`cli/tests/test_balance_diagnosis.py` (11 tests), the retained receipt
`docs/probes/ot8/retained/g4-robin-diagnosis.json` (14,249 bytes), and the
README rows that index both.

## Why

The critic named G4 as the next unit — the last open measurement, with G5 and
G6 bookkeeping on top of it — and ordered it cheapest-first: prepare the copy,
validate it, reproduce the holding smoke, read the per-check breakdown, then
separate the three causes against the MJCF/task contract. That is what was
done, in that order. The per-check numbers the critic quoted were reproduced
exactly: `support` 102.2°, `termination` 0.660 s, four penetrations all
against `environment/floor`.

No deviation. One judgement inside the charter's question policy: the
diagnosis was made reproducible by committing the measurement as a tool with
a test, following the `mjcf_agreement.py` + `test_mjcf_agreement.py`
precedent, rather than leaving the numbers as assertions in a receipt.

## Method

Prepared the copy, validated the pin (script `f805fdc2…`, accepted revision
`0b438561…`, accepted digest `b933d905…`), and ran the ot7/ot8 collector with
`--turns 0`. Then three measurements:

1. **Export.** `mjcf_agreement.py` on the accepted attempt's export against
   its own `result.json`: **28 of 28 bodies**, worst position error
   `1.35e-29` mm, worst orientation error `0.0°`. The model the smoke ran
   (`933b1ac6…`) is byte-identical to that export, and the smoke's own
   exact-BREP check passes on **378 pairs across 51 sampled MuJoCo poses**
   with `initial_pose_agrees` true. Ruled out.
2. **Mechanism.** From the model's own mass properties at the accepted pose,
   with the support set found from MuJoCo's contacts rather than from any part
   name: **two** floor contacts 96 mm apart — a *line*, so no static margin
   about that axis at any mass distribution. Whole-body mass 187.93 g, centre
   of mass **0.365 mm** off the line and **52.40 mm** above it, inertia about
   it `7.187e-4` kg·m². Holding the accepted pose costs **0.672 N·mm** against
   the **184.365 N·mm** the design's own two motors declare about the same
   axis: a **274×** margin, static authority out to **89.6°** of tilt. Ruled
   out.
3. **Free response.** Unstable eigenvalue **11.59 /s** (time constant
   **86.3 ms**). Replaying the smoke's own zero-command rollout reproduces the
   published fall to the receipt's digits — final tilt 102.2339672° against
   the receipt's 102.2339671°, and all four penetration rows bit-identical —
   with a fitted exponential growth of **9.53 /s**. Both actuators are
   commanded **0.0**, because `cli/cadex_cli/smoke_runner.py:163` holds
   position servos only and a torque motor has no pose to hold.

The four penetrations are not a fifth finding: two are post-fall ground
impacts at 0.740 s (board 7.676 mm, chassis 5.312 mm) and two are the standing
contact compression — wheels exactly tangent at t = 0, peaking 0.601 mm at
0.06 s, settling at 0.576 mm against a 0.5 mm tolerance. Under scaled load it
follows the load (0.212 mm at ¼, 1.645 mm at 4×, every sample within 0.35° of
the same pose), so it is the engine's contact spring
(`CadexDynamics.CONTACT_TIMECONST_S = 0.02 s`, not script-declarable)
compressed, not geometry intersecting the floor; and the design already sits
at the stiffest contact its surface allows, since restitution 0 maps to a
critically damped `solref` dampratio of 1.0, the maximum.

Verified: `pixi run python -m pytest src/Mod/cadex/cadex_tests` — **2196
passed, 53 skipped**; `pixi run python -m pytest cli/tests` — **903 passed, 1
skipped** (the suite run before the doc edits; the doc-reading tests
`test_project_docs.py`, `test_lifecycle_report.py`, `test_ot7_report.py`,
`test_ot8_prompts.py`, `test_ot8_runner.py` plus the new file re-run green
after them, 91 passed). The new test fails on the absent tool and is not a
fix's regression but a measurement's.

## Result

**G4 has its actionable measured diagnosis, and it ends that experiment.** The
failure is a control requirement, not a defect: `resolve.prompt.txt` was
**not** dispatched, because the ot8 freeze sends it only if the actor's own
no-slot diagnosis finds an actionable design defect. `ot8-robin` is paused
with all four prompts unspent, zero slots spent, its seed unchanged and
`ot7-robin-c` untouched.

The missing control contract, stated from the design's own task bundle: read
the **20 channels** already exported as nine sensors (chassis quaternion,
angular velocity and position, both wheel velocities, subtree centre of mass
and its velocity, both actuator forces); command **two wheel torques at
±92.18 N·mm** at **50 Hz** — **4.3 samples per e-fold**, **1.26×** of tilt
growth per control interval; hold `chassis_pos_z ≥ 75.25 mm`, which is
**45.573°** of tilt since the chassis origin stands 107.5 mm above the contact
line, and stay inside the smoke's 30° support limit, for the declared 8 s
episode, from resets that already vary tilt to 3° and height by 3–5 mm.
Supplying it needs a trained policy or a hand-authored feedback controller,
and this charter forbids both. Nothing was grounded, supported, suppressed,
weakened or shortened.

For the next iteration:

- **G1–G4 all have evidence now; G5 (the regression floor) is the next unit**
  — both suites and the packaged lifecycle gate at the final revision, plus
  reopening the retained ot6/ot7 designs this run used and checking their pins.
  The two suites are already green at `a1d12093`; the packaged gate
  (`CADEX_ENGINE_ROOT=<payload> … test_cadexd_lifecycle.py`) is not, because
  no build or stage was run this iteration. No engine code changed, so a build
  is not required by the change itself — but G5 asks for the gate at the final
  revision, so it has to be run rather than reasoned about.
- **G6 is the closing report**, written last, and it now has a G4 row to
  carry: the three ruled-out/confirmed causes, the "no prompt dispatched" slot
  accounting, and the control contract as the outcome rather than a failure.
- **Assumption taken, reversible:** the standing 0.576 mm wheel compression is
  reported as a secondary, non-blocking observation rather than an actionable
  defect, on the measured grounds above and because repairing it could not
  change a verdict that fails on support and termination regardless. If a
  later reader disagrees, the receipt carries the load sweep to argue from.
- No new dependency. `mujoco` is already in the pixi environment and is what
  the smoke itself runs on; the new test skips without it.
- One unreconciled record now: this one. `honest-ash-4208`,
  `sunny-quill-9617` and `winter-creek-7660` are all at or behind the
  high-water mark. The tail is thin.

Dispatch closed: 1 unit — G4 diagnosed and closed on a measured out-of-scope
control requirement, no prompt dispatched, no slot spent, ADR-402.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot8
- commit: a1d12093b29d5ba723d86769308418a5ca4d9b8a

## State Impact

- target: scarlet-hill-8037 — G4 is measured and closed: on the independent copy ot8-robin the ordinary cadex smoke's failure is separated into its three causes by measurement. Not a geometry or export mismatch (28/28 bodies agree to 1.35e-29 mm; the smoke's exact-BREP check passes on 378 pairs across 51 poses with its first-frame gate satisfied; the smoked model is the accepted export byte for byte). Not a design defect (a two-point contact line 96 mm apart, centre of mass 0.365 mm off it and 52.40 mm above it, holding torque 0.672 N.mm against a declared 184.365 N.mm -- a 274x margin and static authority to 89.6 degrees). A missing feedback control (unstable eigenvalue 11.59 /s, 86.3 ms; both torque motors commanded zero because the smoke holds position servos only; the replayed free response reproduces the published 102.2339672 degree fall). The four penetrations are two post-fall impacts and two standing contact compressions that follow the load, so the engine's fixed 20 ms contact spring rather than geometry. resolve.prompt.txt was therefore NOT dispatched, per the freeze: ot8-robin is paused, four prompts unspent, zero slots, seed unchanged, ot7-robin-c untouched. The exact missing control contract is recorded (20 declared channels, two torques at +-92.18 N.mm at 50 Hz, 4.3 samples per e-fold, hold 45.573 degrees of tilt for the declared 8 s, from 3 degree/3-5 mm resets); supplying it needs training or a hand-authored controller, both forbidden here. ADR-402, commit a1d12093, receipt docs/probes/ot8/retained/g4-robin-diagnosis.json, tool docs/probes/ot8/runner/balance_diagnosis.py pinned by cli/tests/test_balance_diagnosis.py.
- target: ancient-vine-9908 — ot8's four measured criteria now all have evidence: G1 frozen, G2 and G3 closed on completed turns, and G4 closed on a measured out-of-scope control requirement that spent no slot. G5 (the regression floor, including the packaged lifecycle gate at the final revision and reopening the retained ot6/ot7 designs) is the next unit, and G6 the closing report after it.
