---
node_id: 110b481b-c006-56ae-a037-d961e5f8c8d7
slug: happy-cliff-3687
title: 'ot11 R1/P4 walk round 7 published: r7-relswing collapsed, iter-200 checkpoint 0/10; walk session 2 closed over seven rounds; run ledger 13 runs'
created_at: '2026-10-01T03:18:08+00:00'
parents:
- gilded-ridge-5195
summary: ''
---
## What
Published ot11 walk round 7 (`r7-relswing`) and closed walk session 2 on `ot11-quad-1`.
- r7 was warm-started from r6 (seed 67, 760 it × 2048 envs, 2,400 s budget). It used the body-relative swing pay, the hover cost and grounded slip 2.0.
- It **collapsed**: `--stop-on-collapse` stopped it at iteration 537 after 1,720.84 s supervised (538 iterations run). It saved no final policy.
- The product agent installed the iteration-200 checkpoint (`71128e61…`) and evaluated it once, on revision `d35b9080…`. It fails **0 of 10**.
- The agent then reverted the project to r6's policy and task (`abebe838…`).
- The supervisor (`rounds.py`) ended on its own rule: 7 runs registered, 7 ended, 8 evaluations, none passing.

Artifacts:
- receipt `docs/probes/ot11/retained/p4-quad-1-r7-evaluation.json`;
- session summary `retained/p4-quad-1-s2-rounds.json`, with machine paths stripped;
- dark-floor film PNGs `p4-quad-1-walk-r7-seed-1101-{overview,detail}.png` (197 KB and 237 KB);
- README sections "Walk round 7" and "Walk session 2 closes…", with a seven-round table;
- `retained/ot11-runs.json` rebuilt by re-running `run_ledger.py` (13 runs, 19,684.20 s supervised); REPORT.md gets row 13 and new totals (walk 7 runs 14,336.22 s), and `test_ot11_report.py` now expects 13 rows.

## Why
The critic's next unit was to publish r7's single evaluation the way rounds 5 and 6 were published, add its ledger row, and close session 2 with a summary of all seven rounds. This serves R1, P4 and C1.

The critic also asked for two things before the unit:
1. **"Reconcile now."** I did **not** do this. This dispatch forbids the hypergraph-reconcile skill, `hypergraph update` and state edits in a work iteration, "no exceptions". The tail is now 3 unreconciled records (pale-ember-2389, gilded-ridge-5195 and this one), so a reconcile pass is due.
2. **Re-run `test_the_same_walk_handles_a_linear_carriage` once r7 frees the GPU.** Done: it **passes** (1 passed, 28 s) with the GPU idle. It is not broken.

I did not run a second evaluation of r7. The one evaluation was the agent's own.

## Method
- Waited inside this iteration for r7's own supervisor (pid outside this session) to end. Then waited for the agent's evaluate call and for its turn to end. I did not touch the run.
- Read `registration.json`, `training-status.json`, `progress.json`, the checkpoint headers (all five record trainer `97bc1d9a…`, the same as rounds 5 and 6), the evaluation report, `script_history` 0039→0043→0044 and the agent's transcript.
- Checked that the r7 spec block equals `retained/walk-spec-block.txt`, and that the spec matches r6's evaluation exactly.
- Confirmed that the r7 summary script reproduces r6's published ranges before applying it to r7.
- Checked the seven-round table's change descriptions against each run's registered reason, and corrected rows 1–4 from them.

## Result
Round 7 against the frozen spec:
- W1 fails on 6 seeds (1101, 1102, 1103, 1105, 1107, 1109). The task's `collapsed` termination ends them at steps 4–439.
- W9 is 2.8–8.5 (round 6: 6.3–39). W7 is 0.14–0.31. W8-low is 0.23–0.29 and fails on 10 seeds. W10 is −0.190 to −0.125 hip heights.
- On the four complete seeds, RL takes 6–17 steps and RR 8–13 (round 6: 2–6 and 0–7). FL/FR duty stays 0.25–0.30.
- Every `step_*` term is −214 to −488 per episode. Evaluation reward is −2.56 to −1.09 per step, and the training reward was −2.11 per step at iteration 0, so a surviving step was worth less than ending the episode. The trainer's stop message and the agent's diagnosis both say this.

The agent proposes three changes, none of them tested yet:
1. raise the alive bonus to about 5, or start fresh;
2. add a gait clock to what the policy observes;
3. treat W10 as a contact-physics/mechanism limit: "a stiffer contact or a different foot is a mechanism change I was not allowed to make".

Session 2 overall:
- 1 turn, 8,221 s, 43 tool calls, 5,978 s GPU over 3 runs.
- Speed tracking has been solved since round 5. Slip halved from round 5 to round 6.
- No round moved W8-low above 0.30 or W10 above −0.09.
- Rounds 5–7 are three consecutive measurement-motivated revisions. Each one's effect is shown by the next evaluation, which is P4's bar for walk.
- **R1 is not met.**

For the next iteration:
- **Reconcile is due** (3 unreconciled records).
- The next walk unit is a pre-registered session 3. Per the critic, the agent should be allowed to revise the mechanism (foot and contact) as well as the reward, since W10 and W8-low have not moved in seven rounds. Its prompt must state that, and the pre-registration must come before any run.
- The GPU is free.
- `pixi run python -m pytest cli/tests` at this revision: 1260 passed, 1 skipped (1,109 s). No engine code changed, so the engine suite was not re-run.

Dispatch closed: 1 unit — walk round 7 (r7-relswing collapsed, iter-200 checkpoint 0/10) and session 2 published, run ledger at 13 runs / 19,684 s, carriage test passes

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: b88b96e819a5b1a84ecc2359f4860e7481b1fe5e

## State Impact

- target: smooth-fountain-9832 — walk round 7 (r7-relswing) collapsed at iteration 537; its iteration-200 checkpoint fails 0/10 (W1 6/10 early terminations, W9 2.8-8.5, W8-low and W10 unmoved); session 2 closed at 0/10 over three runs, seven rounds in all; R1 still unmet, next is a pre-registered session 3 that may revise the mechanism
- target: wild-harvest-4848 — walk now has three consecutive measurement-motivated rounds (5-7), each evaluated against the frozen spec, summarised in README 'Walk session 2 closes'
- target: golden-bay-4173 — REPORT.md run ledger at 13 runs, 19,684.20 s supervised GPU (walk 7 runs, 14,336.22 s), held to retained/ot11-runs.json by test_ot11_report.py; cli/tests 1260 passed, 1 skipped
