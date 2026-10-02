---
node_id: 4fc3f564-af82-53c8-94c2-ed02767c166e
slug: scarlet-cove-2359
title: 'ot11 R1: rounds.py counts runs not evaluations; walk session 7 pre-registered (c2d94a6f) and launched from r19'
created_at: '2026-10-01T14:19:36+00:00'
parents:
- brisk-ember-6734
summary: ''
---
## What
Pre-registered and launched walk session 7 on `ot11-quad-1`, starting from r19-contact-sync (9 of 10). Before that, fixed the driver's stop rule. Commit `c2d94a6f`.

- **Driver fix** (`docs/probes/ot11/runner/rounds.py`, 86a96079 → 72ea8c62). `over()` used to count the ledger's `evaluated` rows against a cumulative `--max-runs`. Session 6 therefore lost its third run when the agent re-evaluated r17. It now counts this session's `train_ended` rows that are settled: their policy has been evaluated, or they ended with no policy. `--max-runs` is now per session, and `registration.json` records `runs_ended_before`. New test `test_a_re_evaluation_does_not_use_up_a_round`: two re-evaluations plus one new run give `settled_this_session == 1`, so the session is not over at max 2. It fails on the old source (the old rule reads 4 evaluations ≥ 2 as over; the new signature also raises TypeError there). The existing stop-rule test was rewritten for the new standing and adds two cases: a policy-less ended run counts as spent, and an ended run with an unevaluated policy does not.
- **Session 7 pre-registration** `docs/probes/ot11/retained/p4-quad-1-s7-preregistration.json` (registered 14:18:40Z, committed before launch):
  - project head `dd046e5b`, accepted revision `35122157`, digest `c3fc2f53`;
  - model `6cecfa2d`, task `db670704`, declared policy r19 `de546ddd`;
  - scale HIP 96.7006 / WEIGHT 5.05069617762;
  - trainer `97bc1d9a` (unchanged);
  - limits: at most 3 runs of at most 2,400 s each (7,200 s GPU at most), 3 turns, `--stop-on-collapse`;
  - seed: the agent's choice, and `train_start` refuses 1101–1110;
  - stop rule: an evaluation passes all ten, or 3 session runs are ended and evaluated, or 3 turns have ended.
- **Prompts** `walk.s7.loop.prompt.txt` (80a76cd3) and `walk.s7.continue.prompt.txt` (01cbb472). They give r19's per-seed commanded speed and W9 value, plus 1109's per-foot step counts, as measurements with no remedy ("These are measurements, not a diagnosis"). They also tell the agent that the driver no longer counts re-evaluations.
- **Launched** at 14:18:52Z under `setsid` (rounds.py pid 3241880). Its output is in `~/cadex-projects/ot11-notes/quad-1-s7/`, and its registration shows `runs_ended_before: 19`.

## Why
The critic named this unit: pre-register session 7 from r19, fix the stop rule first with a test that a re-evaluation does not use up a round, give W9 versus command as a measurement only, and state the budget, the seed and the stop rule. It serves **R1** (`smooth-fountain-9832`), which is a charter criterion and not the banned plan bet (moving clearance). The critic's generic "frontier has not moved" text also asked for a one-line-per-criterion list if every criterion is blocked. None is blocked: R1 is 9/10 and moving; R2, R3 and P1–P4 have their own nodes and are not blocked by this work.

## Method
- Read the project ledger: 19 train_ended rows and 22 evaluated rows. r14 finished but was never evaluated, which is why a "settled" count is session-relative and not cumulative.
- Pulled per-seed commands from `evaluations/35122157a90f-de546ddd91e1/evaluation.json` (`drawn.goal[0].segments[0].values`) and the step counts from the retained r19 receipt.
- `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests -k ot11`: 83 passed. `test_ot11_rounds.py` against the old rounds.py: the 2 changed tests fail; against the new one, 10 pass.

## Result
- Session 7 is live and supervised, and it outlives this actor. The GPU now belongs to it: one job at a time. Nothing under `src/Mod/cadex`, `cli/cadex_cli`, `training/` or `build/` may change while it runs.
- The full cli suite was not re-run: only the ot11 subset changed, and the full suite would collide with the GPU job unless run CPU-only. The next iteration should run it CPU-only at publication time.
- **Handoff (critic asked for one):** what I tried is the r19 → session 7 continuation above. Next, for whoever takes it:
  1. Wait for each session-7 round (`loop-ledger.jsonl` train_ended + evaluated) and publish it like r19: validity (contact_offsets empty, model/task sha, spec block under mechanism_rule), receipt, ledgers via `run_ledger.py`/`eval_ledger.py`, filmstrip ≤300 KB, REPORT rows, test counts in `cli/tests/test_ot11_report.py`.
  2. If a round passes 10/10, pre-register and commit the R1 confirmation evaluation (fresh, never re-run) before running it. It should include the judge's bar.
  3. If session 7 ends without a pass, R2 (reach on Heron, `p4-heron-1-reach-r5` is the latest) and R3 (balance on Robin) are the other open behaviour criteria, and they may be better uses of the next GPU time than session 8.
- The tail is now 2 unreconciled records, with the plan's short bet still stale (the banned clearance item). Next reconcile should replace it with R1/R2/R3 bets.
- No new dependency.

Dispatch closed: 1 unit — rounds.py stop rule counts session runs not evaluations (tested); walk session 7 pre-registered (c2d94a6f) and launched from r19 under setsid

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: c2d94a6ff91bf1200f5ca23a09ff45c63f2e7d7d

## State Impact

- target: smooth-fountain-9832 — walk session 7 pre-registered (retained/p4-quad-1-s7-preregistration.json, commit c2d94a6f) from r19 (9 of 10) and launched under setsid at 14:18:52Z: at most 3 runs of at most 2400 s, 3 turns, stop-on-collapse; the driver now counts this session's ended-and-evaluated runs, so a re-evaluation no longer spends a round (tested)
