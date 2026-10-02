---
node_id: 17f1b3b2-def6-5a71-80f2-d72df4e27e44
slug: rapid-peak-4236
title: 'ot11 R1 walk round 11 published: r12-convex-sym valid, 0/10, travels on three legs, W10 fails under a gait on steel feet; C1 ledgers 18 runs/24 evals; r13 training'
created_at: '2026-10-01T07:14:09+00:00'
parents:
- forest-stone-4700
summary: ''
---
## What

Walk round 11 (`r12-convex-sym`, session 4's first run) published on `ot11-quad-1` under session 3's validity checks; both C1 ledgers and REPORT.md regenerated (commit `d2fda4f7`).

- `docs/probes/ot11/retained/p4-quad-1-r12-evaluation.json` (receipt: trainer digests per checkpoint, spec-block check, per-foot table, W10 worst foot per seed, reward terms per step).
- `docs/probes/ot11/README.md` § "Walk round 11: `r12-convex-sym` travels on three legs"; two filmstrip PNGs (199 KB, 230 KB) on the dark floor.
- `retained/ot11-runs.json` (18 runs, 17 attempts, 28,074.47 s; `r13-hovercost-margin` in progress), `retained/ot11-evaluations.json` (24 evaluations).
- REPORT.md: run row 18, evaluation row 24, revision row `r12-convex-sym`, failure counts (20 of 24), and Remaining defects (W10 under a gait now measured, rows 13–24). `cli/tests/test_ot11_report.py` counts moved with it.

## Why

The critic named this unit: publish each finished session-4 round under session 3's validity checks, then regenerate both ledgers and REPORT.md. r12 is the only session-4 round finished in this iteration. R1 (smooth-fountain-9832) is the open behaviour and C1 (golden-bay-4173) holds the ledgers. The critic's second ask, to rerun `cli/tests/test_walk.py` in full, is conditional on the supervisor having exited with the GPU idle. Neither held: the agent registered r13 at 07:09:48Z and it is training. I ran no JAX or GPU test, as the critic asked. No round passed 10/10, so there was no confirmation evaluation to pre-register.

## Method

- Waited on the loop ledger. r12 `train_ended` finished (800 it, 2,105.98 s supervised, policy `3179aa38…`). The agent evaluated it into `evaluations/ca8310e9d841-3179aa38a75d/`.
- Revision check: `diff` of script_history 0063 (`9f5e8bb8`, registered) against 0065 (`ca8310e9`, evaluated) shows only the `assembly.policy` line. 0064 is the same text.
- Spec block: the block from `HIP_MM =` to the end of `walk_spec` in 0065, tokenized with comments and whitespace dropped, against `retained/walk-spec-block.txt`. 379 tokens each. The one difference is WEIGHT_N's value. HIP_MM 96.7006 equals the rig's 96.7006 (4 dp). WEIGHT_N 5.05069617762 equals the rig's 5.050696177620001 (11 dp). Valid.
- Model `5e28d393` matches r11's (byte-identical). Task trained = task evaluated (`c46f65af`). Checkpoints 100–700, best and final all record trainer `97bc1d9a`, which is the current `training/cadex_train.py`.
- Ledgers: `run_ledger.py` and `eval_ledger.py` over the five ot11 projects in the existing order. r11's evaluation row changed only `written_at`. The agent re-ran `evaluate` on r11 at 06:18Z, the start of session 4, and the stored result is unchanged.
- Tests: `test_ot11_report.py`, `test_ot11_contract.py` and `test_ot11_rounds.py` gave 36 passed (no JAX). I did not rerun the full suites. Only docs and that test file changed, and a full `cli/tests` run would put JAX on the GPU r13 holds.

## Result

- **Round 11 is valid and fails 0 of 10.** It is the first steel-foot policy that travels: W3 0.65–0.81 (passes 5 of 10), drift 414–741 mm. Both front feet step (FL 6–10, FR 7–11). RL is held up on every seed (W8-low 0.00, 0 steps). RR drags (duty 0.91–0.96, slip 0.85–0.98). Tilt is 23–28°, and W10 fails.
- **W10 under a gait on the steel feet is now measured, and it fails:** −0.154 to −0.074 hip heights (7–15 mm). The worst foot is always a stepping front foot (FL on 7 seeds, FR on 3). The dragged RR stays at −0.027 to −0.018. REPORT's remaining-defects item now says this instead of "unmeasured".
- Read from the reward: the held-up RL costs 0.14/step (the hover cost only), against 0.49/step of slip for the dragged RR, so holding a foot up stayed the cheapest answer. The agent's r13 registration gives the same diagnosis.
- **r13-hovercost-margin is training** (fresh, seed 137, 800 it, 2,400 s, registered 07:09:48Z, revision `8563f7f5`). It raises the hover cost 0.15 → 0.6 and rescales swing pay to /80, sets tilt −40 and alive 6, and makes **one mechanism change: a 3 mm foot-sphere contact margin**. The mechanism rule allows a contact setting on the agent's own bodies. **Concern for the next iteration:** a MuJoCo margin can raise the foot's resting height as well as stiffen its landing, and W10 measures that height. Publishing r13 must compare each foot's standing rest height with round 11's before a W10 pass is read as a fix. It must also re-check that HIP_MM and WEIGHT_N still equal the rig: the margin should change neither, and the engine refuses a mismatched scale (ADR-468).
- **cli/tests is still unverified for `test_walk.py`'s tail** (from `test_the_same_walk_handles_a_linear_carriage`, 12 tests), as forest-stone-4700 recorded. Rerun it only after the session-4 supervisor (rounds.py pid 2042431) exits and the GPU is idle. Do not fold golden-bay-4173 as green before that record exists.
- Session 4 so far: 1 run of at most 3, 2,105.98 s. R1 stands at 0/10 on rows 13–24.
- Tail: 2 unreconciled records after this one (forest-stone-4700 and this), under the reconcile threshold of 3.

Dispatch closed: 1 unit — walk round 11 (r12-convex-sym) published valid at 0/10 (travels on three legs; W10 fails under a gait on steel feet); ledgers 18 runs / 24 evaluations; REPORT.md moved; test_walk.py tail still owed with the GPU busy (r13 training)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: d2fda4f7af522c2a063d19ecb1ea099081ab3c3c

## State Impact

- target: smooth-fountain-9832 — walk round 11 (r12-convex-sym, session 4 run 1) valid and 0/10: first steel-foot policy to travel (W3 0.65-0.81, 5 of 10) with front feet stepping, RL held up on every seed, RR dragging (slip 0.85-0.98), W10 failing under a gait (-0.154 to -0.074 HH); r13-hovercost-margin (adds a 3 mm foot contact margin) training; R1 still 0/10
- target: golden-bay-4173 — ledgers regenerated to 18 runs (17 attempts, 28,074.47 s) and 24 evaluations with REPORT.md moved; the remaining defect 'W10 under a gait unmeasured' is now measured as failing; cli/tests still unverified for test_walk.py's last 12 tests until rerun with the GPU idle
