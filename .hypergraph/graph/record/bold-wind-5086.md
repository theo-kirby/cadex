---
node_id: 2f1e6bad-8218-56d1-86e2-49445d5dc760
slug: bold-wind-5086
title: 'P1 circle-7: warm from centring by ADR-597 goes round 3-4 laps on 8/8 at 12-17 mm; no channel carries time for a phase reward'
created_at: '2026-10-08T03:08:36+00:00'
parents:
- flat-hawk-9763
summary: ''
---
## What

Ran P1 circle-7 on `orun5-ball-plate`. It is the circle task, warm-started from the passing centring policy (`centre-vel.cxpolicy`, sha 9cb0a64c) through ADR-597's curriculum step, the first run to use that step. Evaluated it on frozen seeds 9101–9108. Also checked whether the critic's top-ranked direction, a phase-tracking reward, can be written in xscript: it cannot. Recorded that gap and the design for closing it as REPORT defect 12. Updated REPORT §6, the P1 status row, defects 1 and 11, the done-claim tail and ledger rows W5/W7. Commit `7232131a`.

## Why

The critic asked for four things: fold flat-hawk-9763; try the phase-tracking reward, warm from the centring policy via ADR-597, on seeds 9101–9108; record the gap if xscript has no time or phase observation; then reconcile and restate the done claim.

- **Fold and reconcile: not done.** This dispatch's rules forbid a work iteration from reconciling (no hypergraph-reconcile, no `hypergraph update`). The tail is now flat-hawk-9763 plus this record, and the next reconcile pass must fold both before the done claim is judged. REPORT's done-claim paragraph now says so.
- **Phase reward: not runnable.** No channel carries time, so I recorded the gap.
- **Instead,** I ran the rest of the critic's experiment unchanged: the existing circle reward, warm from centring by ADR-597, on the same frozen seeds. It tests whether a competent controller's mean can circulate where circle-6's could not, and it is the first use of ADR-597 (REPORT defect 1 said no run had used it).

## Method

- **The gap, from source:**
  - `_OBSERVATION_KINDS` (`cadex_assembly_api.py:1025`) has no time kind.
  - Only control formulas may name `time` (`_CONTROL_NAMES`, line 1189).
  - Reward and termination formulas name declared channels only.
  - `value`/`speed`/`point` goals hold a uniform draw per segment (`draw_goals`, `cadex_train.py:978`; `goal_values`, `CadexDynamics.py:9640`).
  - The trainer's own comment says an observation "carries no clock" (ADR-136, `cadex_train.py` around line 331).
  - The trainer's reset does not rewind `data.time` (`cadex_train.py:1727`), so a MuJoCo `clock` sensor row would read time across episodes.
- **Checked the curriculum preconditions:** the centre-vel policy header's task digest 828f41bf equals `runs/centre-vel/task_centre-task.json`, and its model digest 2db9bc99 equals the circle task's model.
- **Launched circle-7** with `cadex_cli.loop.register` + `launch` (the `train_start` path):
  - `task_circle`, 1000 it × 256 envs, seed 15, budget 570 s;
  - `init_from=assets/centre-vel.cxpolicy`, `init_from_parent_task=runs/centre-vel/task_centre-task.json`, and `init_from_task_change` given;
  - σ carried from the policy (0.268).
  - Waited in the foreground until `finished`.
- **Stored and evaluated:** `cadex asset --put` as `circle-7.cxpolicy` (sha 5fc19986…); `policy_circle` pointed at it with `cadex script --set`; then `cadex evaluate --policy policy_circle --film none`.

## Result

The trainer accepted the curriculum step: `curriculum  the task changed in ['disturbance', 'episode', 'label', 'reward', 'success']`. That is ADR-597 working on a real run. Training: exit 0, 456 s, witness error 1.0e-7. Reward/step was 0.70 at it 0, 1.04 by it 195, then flat to 1.11 at the end (best 1.15 at it 993), below circle-5's 1.32.

Evaluation `32a0a13bbde1-5fc199867250` passed **0 of 8 seeds**:
- `completed` 1 on 8/8;
- `laps` **3–4 on 8/8** (turns +3.56 to +4.74), passing the laps bound on every seed;
- `mean_distance_mm` 12.0–17.2 against a 30–50 bound, failing 8/8;
- `final_distance_mm` 1.2–11.8.

So warming from centring gives the first circle policy whose deterministic mean goes round on every frozen seed, run to the horizon. circle-6's mean only rocked. It fails on radius only, tighter than circle-5's (28–29 mm), consistent with the centring prior pulling the ball in. **The circle task is still not trained to a pass.** P1 stays on the charter's *otherwise* branch, which already has its evidence.

Gap (REPORT defect 12): a phase reward needs a goal kind, e.g. `"phase"`:
- a declared period and a per-episode start phase;
- channels `name_sin` and `name_cos` computed from the episode step counter;
- built in `_GOAL_KINDS`, `GOAL_KINDS`/`goal_values`, and the trainer's `draw_goals`/`goals_at`, with the pin test holding the two halves together.

It is a command from the controller's timer, so A1 is untouched and no tool changes (A5). The reward is then `(b_x*c + b_y*s)/r`, which the existing formula functions can already express. Not built this unit.

Concerns and state:
- The scratch project's accepted script now names `policy_circle` → `circle-7.cxpolicy`. circle-5 and circle-6 remain in `assets/`. No policy, trace or checkpoint was committed.
- Gates: docs only. `test_licensing_compliance.py` gives 11 passed, 1 skipped. The suites were not rerun because no code changed.
- **The tail is two unreconciled records** (flat-hawk-9763 and this one). The next iteration should reconcile, then restate the done claim.
- Ranked next for the circle pass:
  - (a) build the `phase` goal (a capability unit with an ADR), then train the phase reward warm from circle-7;
  - (b) with no new code, warm from circle-7 with the off-radius weight raised, since its mean already circulates.

Dispatch closed: 1 unit — circle-7 (circle task warm from the centring policy by ADR-597, its first use): 3–4 laps on 8/8 frozen seeds but 12–17 mm radius, 0/8 pass; the phase reward cannot be written (no channel carries time), gap and design recorded as REPORT defect 12

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun5
- commit: 7232131a856a915b99307128da7b4b29736d0271

## State Impact

- target: peaceful-orchard-2220 — circle-7 (warm from centre-vel via ADR-597 curriculum step, first use; 1000 it, seed 15, commit 7232131a): 0/8 pass, laps 3-4 on 8/8, mean radius 12.0-17.2 mm (bound 30-50); a circulating deterministic mean is reachable from centring, radius is not under this reward; phase reward not expressible: no channel carries time (REPORT defect 12, design: a 'phase' goal kind)
- target: grand-otter-5246 — REPORT §6, status row, defects 1, 11, new 12 and done-claim tail updated; ledger W5/W7 updated with circle-7
