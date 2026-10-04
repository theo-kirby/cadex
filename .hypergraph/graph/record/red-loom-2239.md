---
node_id: 5af267ed-6e50-5e00-8848-2407f09c754a
slug: red-loom-2239
title: 'orun2 W1: walk steps 1-6 on a copy of ot11-quad-1, each seen in the dashboard; pre-ADR-469 trained projects cannot open'
created_at: '2026-10-04T01:47:14+00:00'
parents:
- crimson-stone-9344
summary: ''
---
## What

W1's walk, steps 1–6, ran on `orun2-w1-quad`, a whole copy of `ot11-quad-1`, and every step was seen in the dashboard. The steps were prompt, accepted design, params sweep, `look` and render, STEP/STL export, and MJCF export. The driver is `docs/probes/orun2/w1/walk_dashboard.py`, the measurements are in `walk-steps.json`, and five screenshots (≤122 KB each) sit beside them, all in commit `9d487b65`. On the way it found a defect: a robot project trained before ADR-469 cannot be opened at all.

## Why

The critic named W1's walk, steps 1–6, as this unit. W1 (`shady-clover-5534`) is the highest-ranked open criterion with work left.

**Deviation:** the critic also asked for a reconcile first. I did not run it. This iteration's dispatch instructions forbid the hypergraph-reconcile skill, `hypergraph update` and state-node writes in a work iteration, with no exceptions. The tail is now 3 records (`amber-moon-9415`, `crimson-stone-9344`, this one), which meets the charter's three-record trigger, so the next housekeeping pass should fold it.

## Method

1. **First copy, abandoned.** I copied `ot11-robin-1` to `~/cadex-projects/orun2-w1-robin`. `cadex -p` failed at `open_project` with `CADEXD_RESTORE_FAILED` before any tokens were spent. I probed the engine directly on a scratch copy. The restore pass refuses the declared policy (`policy_task_mismatch`): the task bundle digest went from `ca60b4ce…` to `d50e953b…`. The only difference in the MJCF is `solref="0.004"` on every contact geom. That comes from ADR-469 (`22d30e7e`, 2026-10-01), which changed `CONTACT_TIMECONST_S` from 0.02 to 0.004. Retrying with the accepted source fails the same way, so the project is locked.
2. **Second copy.** I copied `ot11-quad-1` (policy trained after ADR-469; 10/10 on 2026-10-01) to `orun2-w1-quad`.
3. **Step 1, prompt (CLI).** The turn added two cable-tie slots through the hood and set `policy_on` to 0, because the mass changed. It exited 0 in 335 s. Tools used: `inspect`×5, `look`×1, `edit_script`, `set_params`, `rebuild`. Accepted `a7d487ae`, digest `25984e70`. It wrote two DECISION lines, one saying r24 must be retrained.
4. **Steps 2–6, dashboard.** `cadex app` served `~/cadex-projects` (about 280 projects) on 127.0.0.1 with a random port, driven in headless Chromium:
   - the index row and the CLI-turn row;
   - **Accept**;
   - the `shin` slider at 52, 58 and 55;
   - `cadex render`, then the Concept tab;
   - **Export STEP + STL**, then downloading a `.step`, a `.stl` and the MJCF `.xml`.
5. I ran the CLI suite's `test_project_docs.py` and the engine suite's `test_licensing_compliance.py`: 50 passed, 1 skipped. The full suites were not run, because no code under `cli/` or `src/` changed; the commit adds only `docs/probes/orun2/w1/`.

## Result

**True now: W1 walk steps 1–6 hold on a real robot, each seen in the dashboard.**

| Step | Result |
|---|---|
| 1. Prompt | The index lists `orun2-w1-quad` at `a7d487ae` and the turn under CLI agent turns. |
| 2. Accepted design | Model `loaded`, 62 components; page and index agree on the revision; verdict `accepted`. |
| 3. Params sweep | 3/3 ok at 115.96, 117.02 and 116.46 s; 3 project commits; the model reloaded at each new revision; 55 mm returns to digest `25984e70`. |
| 4. Render | `cadex render` exit 0 in 155.0 s. The Concept tab shows "the accepted design, drawn from revision 27150b476953", 0.51 kg, 8 servos, 178×151×123 mm. |
| 5. STEP/STL | The page's Export finished `done` in 116.8 s and offers 62 `.step` and 62 `.stl`. The STEP starts `ISO-10303-21;`. |
| 6. MJCF | `model-model.xml` (24,828 bytes, `<mujoco`, 8 actuators) and `walk_task-task.json` are offered and downloaded. |

`PROGRESS.md` has one row for each step: prompt, three params rows, render, export.

**Not yet evidenced for W1:** step 7 (a short training run on the 5090) and step 8 (`evaluate`), both on `orun2-w1-quad`. Its stored `policy_on` is 0, so train, re-declare and evaluate. Also outstanding: the row-by-row ledger audit, and both full suites plus the packaged gate at the end. **Concern:** `nvidia-smi` could not reach the driver this iteration, so check the GPU before step 7.

**Defects found:**
- **Broken: a project trained before ADR-469 cannot be opened.** Every command fails at `open_project`, including a design turn that would set `policy_on` to 0. Refusing the stale policy is right; locking the whole project is not. This affects every robot project trained before 2026-10-01 (for example `ot11-robin-1`, `ot9-robin`, `ot6`/`ot5` copies) and counts against W1's "nothing lost". A likely fix in the engine zone is to let the restore pass accept with the policy output reported stale rather than fail the open. That needs its own unit, ADR and tests. `~/cadex-projects/orun2-w1-robin` is kept as the reproduction.
- **The Model tab opens with the robot as a speck.** A 178 mm quad sits in the middle of the metre grid until **Fit** is pressed, and is drawn in per-component debug colours.
- **A CLI turn's transcript and its `look` images are not on the project page.** They appear only when the turn was started from the page.

Dispatch closed: 1 unit — W1 walk steps 1–6 on orun2-w1-quad, each seen in the dashboard; pre-ADR-469 trained projects found unopenable

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 9d487b65676222213db3101383ec3e5be1025b60

## State Impact

- target: shady-clover-5534 — W1 walk steps 1-6 evidenced on orun2-w1-quad (copy of ot11-quad-1) through the dashboard in headless Chromium: prompt 335 s accepted a7d487ae; Accept verdict; shin slider sweep 3/3 at ~116 s; render 155 s shown on the Concept tab; page Export 62 STEP + 62 STL + MJCF (8 actuators) + task JSON in 116.8 s (docs/probes/orun2/w1/, commit 9d487b65). Steps 7-8 (train on the 5090, evaluate) remain; also the ledger audit and the final full suites + packaged gate.
- target: NEW stale-policy-locks-project — broken: a robot project whose policy was trained before ADR-469 (contact solref 0.02 to 0.004, 2026-10-01) cannot be opened: the restore pass refuses the declared policy (policy_task_mismatch), the accepted-source retry fails the same way, open_project returns CADEXD_RESTORE_FAILED, so no command (not even a design turn setting policy_on 0) can run. Reproduction: ~/cadex-projects/orun2-w1-robin (copy of ot11-robin-1). A lost headless capability under W1.
