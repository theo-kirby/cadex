---
node_id: 47b1922f-afa8-560f-a82e-784166ce5ad6
slug: cold-summit-2811
title: 'ot11 R2/P4 reach round 5 on ot11-heron-1: warm start from r4 passes 10 of 10 seeds (1106 Q2 7.92 -> 3.33 mm); iteration 22''s warm-start fix recorded'
created_at: '2026-09-30T21:01:36+00:00'
parents:
- silver-harvest-8970
summary: ''
---
## What

Reach round 5 on `ot11-heron-1`, run exactly as pre-registered in
`c758ffeb`. It was one warm-started run by the product agent
(`claude-opus-5-5`, no fallback), and its policy passes the frozen reach spec
on **10 of 10** evaluation seeds. Seed 1106's Q2 went from 7.92 mm to 3.33 mm.
This record also covers **the warm-start fix from iteration 22**
(commit `b4c527d0`, "ouroboros #22: no record"), which never got a record of
its own. `loop.run_view` now carries `task_bundle` and a `warm_start` line,
the `train_status` listing gives each run's bundle path, and a missing
`init_from_parent_task` is refused with every run's bundle named. Its
regression test is
`test_a_run_names_its_task_bundle_so_a_warm_start_can_be_registered`, and
the ADR is the amendment "a run names its task bundle" in `docs/DECISIONS.md`.
Evidence commit: `e99adb36`.

## Why

The critic named this unit: run round 5 as pre-registered, evaluate it on
the frozen seeds, and report 1106's Q2. The critic also asked that the
iteration-22 fix be recorded along with it, and it is.

**Deviation:** I did not launch the session. When this iteration began, the
session had already been launched under `setsid` at 20:36:18Z, by the
previous iteration, which ended without a record or a final message. It
had also finished: training ended 20:55:42Z and the evaluation was written
20:58:27Z, one minute before this iteration looked. Launching again would
have been a second session on the same pre-registration, which is fishing.
So this unit verified that the session matched its pre-registration and
recorded it. The run is not counted as an attempt of mine.

## Method

1. Checked that the prompt, continuation prompt, driver and held-out target
   hashes equal the pre-registration (`fc99f2fc…`, `970d16e7…`,
   `a6a2a5b1…`, `8bb702af…`). The session's `registration.json` shows
   `max_runs 5`, `max_turns 2`, and model `claude-opus-5-5` with a null
   fallback.
2. Read the run's own registration (`runs/reach-r5/registration.json`):
   - seed 41, not one of 1101–1110;
   - 800 iterations × 1024 envs, entropy 0, checkpoint every 25;
   - a budget of 890 s, which is ≤ 900;
   - `--stop-on-collapse` is in the command;
   - `--init-from` is reach-r4 checkpoint 475, and `--init-from-parent-task`
     is reach-r4's bundle;
   - `--init-from-task-change` reads "reward only: reach_scale 20->10 mm,
     fine_w 2->3; observations, actions, goals and terminations unchanged".
3. The run ended at the budget, at iteration 422, after 890.5 s, and did
   not collapse.
4. Checked the evaluation (`evaluations/13f9c63c93c9-6bb5a403c4af/`):
   - The spec block's canonical sha256 is `61b25b02…`, as registered. All
     five reach evaluations on the project hold the same spec.
   - The model is `183fabff…`.
   - The drawn targets from every seed's trace equal the receipt to within
     4.9e-05 mm, and no seed was void.
   - The policy `6bb5a403…` is the sha256 of reach-r5's checkpoint 000400.
5. Compared r4 and r5 per seed and per reward term, from the two
   evaluation files. Counted the tool calls in the transcript: 16, with no
   errors.
6. Published the receipt `retained/p4-heron-1-r5-rounds.json` with its
   machine paths stripped, the seed-1106 filmstrips (63 KB and 128 KB), and
   a README section.

## Result

- **The round passes the frozen reach spec on 10 of 10 seeds.**
  - Worst Q2: 0.014–0.032 arm lengths (limit 0.05).
  - Worst Q3: 0.46 s, on seed 1106 (limit 2.0 s).
  - Worst Q4: 0.153, on seed 1105 (limit 0.20).
  - Every episode ran to its 8 s horizon.
- **Seed 1106, Q2 in particular: 7.92 mm → 3.33 mm** (0.055 → 0.023), and
  it now reaches the target in 0.46 s.
- **What it cost:** none of r4's nine passing seeds failed, but the easy
  seeds got worse.
  - Median final error: 3.24 → 3.98 mm (seed 1101: 1.36 → 4.54 mm).
  - Median overshoot: 0.034 → 0.082.
  - Median `control_cost` −26.1 → −68.3 and `settle_cost` −21.1 → −55.3, at
    unchanged weights.
- **The iteration-22 fix works in the field.** `train_start` took the warm
  start on its first call; the earlier session had seven refusals.
- **The agent mislabelled one term.** Its closing report says the
  "tip-speed cost" rose, but the term that rose is `settle_cost`, and
  `tip_speed_cost` reads 0. This is a mislabel in its prose, not in the
  measurement.
- **Budget:** 890.5 s of GPU time for this round, so the reach total is
  4,447 s. The turn took 22.4 min and cost $1.27.

R2 is **not** met. This was a loop round, and the pre-registration says R2
is judged on a separately pre-registered confirmation evaluation.

**Next unit:** pre-register the R2 confirmation evaluation. It should cover:
- policy `6bb5a403…` at accepted revision `13f9c63c…`;
- spec `61b25b02…`;
- the same held-out target receipt;
- the frozen seeds 1101–1110;
- the blind judge's bar on its judged seeds, as R3's confirmation did.

Then run it once. The judge has not yet seen reach.

The tail is now one record plus this one since the last reconcile.

Dispatch closed: 1 unit — reach round 5 (run by the previous iteration as pre-registered) verified and recorded: 10 of 10 seeds, 1106's Q2 7.92 → 3.33 mm; iteration 22's warm-start fix recorded with it

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: e99adb365629ff053f06911dda0b9232eba54572

## State Impact

- target: sunny-garden-4245 — reach round 5 (policy 6bb5a403, reach-r5 ckpt 400, warm-started from r4) passes the frozen reach spec on 10 of 10 seeds, seed 1106 Q2 7.92 -> 3.33 mm; not yet R2 -- a pre-registered confirmation evaluation and the judge's bar remain
- target: chilly-union-8972 — train_status names each run's task_bundle and a warm_start line, and a missing init_from_parent_task is refused with every bundle named (DECISIONS amendment 'a run names its task bundle', commit b4c527d0); the agent's first warm-start train_start succeeded
