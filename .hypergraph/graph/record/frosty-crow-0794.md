---
node_id: 78ce0e55-f799-5d8d-b4cf-a021905451d7
slug: frosty-crow-0794
title: 'ot11 R1: walk session 8 pre-registered (34e55adf) and launched; prompt gives warm-start measurements, agent picks the revision'
created_at: '2026-10-01T17:13:43+00:00'
parents:
- humble-canyon-4360
summary: ''
---
## What
I pre-registered walk session 8 on `ot11-quad-1`, committed the registration before launch (`34e55adf`), and launched the session.

- **Pre-registration** `docs/probes/ot11/retained/p4-quad-1-s8-preregistration.json`, registered at 17:13:03Z:
  - project head `17a31c4`, accepted revision `e3b6fb20` (script_history 0111, byte-identical to r19's 0098), digest `c3fc2f53`;
  - model `6cecfa2d`, task `db670704`, declared policy r19 `de546ddd`;
  - scale: HIP 96.7006 mm, WEIGHT 5.05069617762 N;
  - trainer `ddc6688f` (ADR-471) and driver `1708a2e5` (refused starts are not counted);
  - limits: at most 3 runs of at most **3,600 s** each (10,800 s GPU at most), 3 turns, `--stop-on-collapse`;
  - seed: the agent's choice, and `train_start` refuses 1101–1110;
  - stop rule: an evaluation passes all ten seeds, or 3 session runs are ended and evaluated, or 3 turns have ended.
- **Prompts** `walk.s8.loop.prompt.txt` (f0b86cae) and `walk.s8.continue.prompt.txt` (a08847fd). The loop prompt:
  - states ADR-471, and that neither the critic nor the optimiser state is carried and there is no critic warm-up;
  - gives the operator's reward-per-step and σ readings from the training logs of r17 to r22. These are measurements with no remedy, and the agent picks the revision.
- **Launched** at 17:13:15Z under `setsid` (rounds.py pid 3721302). Its output is in `~/cadex-projects/ot11-notes/quad-1-s8/`, and its registration shows `runs_ended_before: 23`.
- `REPORT.md` notes session 8 and links its pre-registration.

## Why
The critic named this unit: pre-register walk session 8 and commit it before launch, give the agent the warm-start finding, let it pick, and do not hand-tune. It serves **R1** (`smooth-fountain-9832`), the only unmet ot11 criterion that an actor can move. The banned plan bet (moving clearance) was not touched.

I did not build the critic warm-up that the previous handoff ranked first. The critic said to take that on only if the agent's own revision needs it, and then only with an ADR and a test that fails first. The prompt tells the agent plainly that no warm-up exists.

## Method
- Read the `train.log` of r17 to r22. Reward per step at iterations 0, 5, 30 and the last, with the run's length:
  - r17, fresh, 760 iterations: −1.18, +0.26, +2.32, +5.20. Its best was at iteration 751.
  - r18, warm from r17 at σ 0.30: +0.16, +1.13, +1.20, +4.26.
  - r19, warm from r18 at σ 0.30: +1.65, +2.05, +2.51, +4.47.
  - r20: +1.97, +2.04, +1.07, +3.56.
  - r21b: +2.19, +2.22, +1.31, +3.65.
  - r22, at σ 0.12: +3.86, +4.36, +1.34, +3.43.
- **New fact:** r19 was itself a warm start (r17 → r18 → r19, each reset to σ 0.30), and it did not fall. So "every warm start loses the gait" holds only for warm starts *from r19*. The prompt gives this as a measurement, and notes that reward per step is not comparable across tasks with different terms.
- Confirmed that the project script is byte-identical to 0098 (`cmp`), and that the model and task hashes come from the accepted attempt's outputs.
- `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests/test_ot11_report.py cli/tests/test_ot11_rounds.py`: 24 passed.

## Result
- Session 8 is live and supervised, and it outlives this actor. The GPU belongs to it: one job at a time. Nothing under `src/Mod/cadex`, `cli/cadex_cli`, `training/` or `build/` may change while it runs.
- **Assumption:** raising the per-run budget from 2,400 s to 3,600 s is an operator budget choice, not a reward or spec change. The reason is recorded in the registration: r17 was still at its best reward at iteration 751 of 760.
- No code changed, so the full suites were not re-run. The next publication should run them CPU-only.
- **Handoff.** What I tried: this pre-registration and launch. What to do next:
  1. As each round ends (`loop-ledger.jsonl` train_ended plus evaluated), publish it the way r22 was published:
     - validity: contact_offsets empty, model and task sha, spec block under mechanism_rule;
     - the receipt;
     - both ledgers, via `run_ledger.py` and `eval_ledger.py`;
     - a filmstrip of 300 KB or less;
     - REPORT rows, and the counts in `test_ot11_report.py`.
  2. If a round passes 10 of 10, pre-register and commit the R1 confirmation evaluation, with the judge bar, before running it.
  3. If the agent asks for a critic warm-up, build it with an ADR and a test that fails first.
- The tail is now 1 unreconciled record. No new dependency.

Dispatch closed: 1 unit — walk session 8 pre-registered (34e55adf) and launched from r19 under setsid; the prompt carries the warm-start measurements and no remedy

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 34e55adf436d3c3437e139be569bce084b48f63a

## State Impact

- target: smooth-fountain-9832 — walk session 8 pre-registered (retained/p4-quad-1-s8-preregistration.json, commit 34e55adf) from r19 (9 of 10) and launched under setsid at 17:13:15Z: at most 3 runs of at most 3600 s, 3 turns, stop-on-collapse; the prompt states ADR-471, that the critic is not carried, and the r17-r22 reward-per-step readings (r19 itself was a warm start that did not fall; only warm starts from r19 fell), and names no remedy
