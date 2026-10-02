---
node_id: 896c36d9-0353-55c5-8b8a-f3aed9621294
slug: northern-eagle-1465
title: ot11 R1 walk round 4 evaluated -- 0/10, stands still, train/eval gap closed on the ADR-465 trainer; trainer_sha256 hashed at import (ADR-466); walk session 2 pre-registered and launched
created_at: '2026-10-01T01:11:11+00:00'
parents:
- windy-nest-5080
summary: ''
---
## What
- Published walk round 4 (`r4-anglesonly`) on `ot11-quad-1`. It is the
  first walk round trained on the ADR-465 trainer. It fails the frozen walk
  spec on 0 of 10 seeds: the policy **stands still**.
- Fixed the trainer's save-time `trainer_sha256` (ADR-466), with a
  regression test that fails on the old code.
- Pre-registered walk session 2, whose prompt states ADR-465, and launched
  it.
- Commit `e4500356`.

## Why
The critic's message, item by item:
- Check round 4's supervisor. If it ended, evaluate the best checkpoint
  once and publish it.
- Fix the digest with a failing-first test.
- If round 4 fails, pre-register the next walk session with a prompt that
  tells the agent about ADR-465.

R1 is the last open behaviour, and these were the critic's three items.
**Two deviations:**
- **I did not run the evaluation.** The product agent did, as in rounds
  1–3: the session's own turn stores, declares and evaluates. Running a
  second evaluation of the same policy would be fishing. I published the
  agent's single evaluation.
- **The evaluated policy is the final one (iteration 780), not `best`
  (iteration 777).** The run finished every iteration, and the agent
  declared the final policy.

I waited about 30 minutes for the run to end before touching
`cadex_train.py`. An edit while round 4 ran would have stamped its saves
with the wrong digest, which is the defect itself.

## Method
- Watched `runs/r4-anglesonly` (progress, supervisor, ledger) until
  `train_ended` (00:28:01Z, finished, 2,183.25 s) and `evaluated`
  (00:32:19Z).
- Built the receipt in round 3's schema with a scratch script outside the
  repo. Checked it first by reproducing round 3's receipt numbers.
- Parsed every checkpoint header. All nine, including the final policy,
  record `abae5da0…`.
- Checked spec validity: script history 0029 → 0031 differ only in the
  declared policy digest, and the retained spec block is contained verbatim
  in all three.
- Copied the seed-1101 overview and detail filmstrips (dark floor; 229 KB
  and 148 KB) and the session's `rounds.json`.
- Read the agent's closing report from the turn transcript.
- Trainer fix:
  - `TRAINER_SHA256` is computed at import, and `policy_header` writes it.
  - New test
    `test_a_policy_names_the_trainer_that_ran_not_the_file_on_disk_when_it_saved`
    in `test_dynamics_goal_trainer.py`. It loads a temp copy of the
    trainer, rewrites the copy and builds a header. It **failed before the
    fix** (`abae5da0…` ≠ `79d6e1fd…`) and passes after it.
- Tests:
  - pixi: the goal_trainer, policy_trainer and `training/` suites, 62
    passed and 12 skipped.
  - The training venv (scratch `/tmp/trainer-test-venv` layered with
    pytest, `JAX_PLATFORMS=cpu`): goal_trainer, policy_trainer,
    mjx_forcelimit and purity_guardrails, **74 passed**.
  - The ot11 cli tests and licensing: 78 passed, 1 skipped.
  - Full suites: see Result.
- Pre-registration: `retained/p4-quad-1-s2-preregistration.json` was
  written and committed before launch. The prompt is
  `prompts/walk.s2.loop.prompt.txt` (`545f36cd…`), with the driver
  unchanged (`a6a2a5b1…`).
- Launched with `setsid` `rounds.py --max-runs 7 --max-turns 2 --out
  ot11-notes/quad-1-s2`. Its registration was written at 00:39:40Z, in its
  own process session.

## Result
**Round 4: 0 of 10 seeds. It stands still.**
- Policy `d2dcaf39…`, the final policy at iteration 780. The report is
  `evaluations/ce8d19639f13-d2dcaf39ba21`, and the receipt is
  `docs/probes/ot11/retained/p4-quad-1-r4-evaluation.json`.
- Failing predicates:
  - W3: speed ratio −0.004 to 0.088.
  - W5-steps, W5-share, W6 and W9: zero steps on every foot.
  - W7: 0.82–1.06.
  - W8-high: duty factor 1.00.
  - W10: −0.131 to −0.085 hip heights.
  - W1 and W2 on seed 1101 only, which tips 0.5 s after its shove.
- W4 passes on every seed.
- **The training/evaluation gap is closed.** Training reached −0.53 per
  step at its best; the engine measures −0.67 to −0.14. Rounds 1–3 trained
  at +1.2 to +2.5 and evaluated at −3.1 to −1.2. The knee joint-speed cost
  fell from −323 to −2.4.
- The dominant reward terms are now `sink` (−937) and `speed_error` (−379)
  against an alive total of 1,500. Standing still is the local optimum.

**The agent's report credits the closed gap to the wrong cause.** It
credits removing the joint-rate and gyro inputs. Round 4 also moved to the
ADR-465 trainer, so the two causes are confounded. Session 1's prompt
predates ADR-465, so the agent could not have known. Session 1 total: four
runs, 0 of 10 each, 8,357 s of GPU time, one turn of 11,137 s.

**Trainer:** `training.trainer_sha256` now names the code the process
loaded (ADR-466). Policies already saved keep their old field; `r3`'s is
wrong from checkpoint 300 on, as already recorded.

**Session 2 is live.**
- At most 3 more runs, 2,400 s each, `--stop-on-collapse`, over 2 turns.
- At record time the agent had registered `r5-swing` (780 iterations;
  ledger row 5) and it was past iteration 355.
- The next iteration publishes each round as it lands.
- **Known conflict:** the shared continue prompt says "four runs in total".
  A second turn may stop at once. If it does, that is the driver's limit,
  not the agent's choice.

**Evaluation-trust flag, for the next unit (it outranks the behaviours):**
- **W10 fails on a robot standing still.** The feet sit 8.2–12.7 mm below
  the floor on 7.5 mm-radius feet, on all ten seeds. W10 takes its minimum
  over every frame, including the 5–10 mm reset drop. The agent
  hypothesises the drop plus static sink, and calls W10 possibly
  unreachable.
- Unmeasured. The next unit: locate each foot's lowest frame in r4's
  traces (reset drop or steady stance?), and measure a passive standing
  rollout. Any change to W10 would be a recorded decision that
  re-evaluates every earlier policy, never a quiet loosening.
- **W7 can exceed 1.0** on a foot that rocks in place (1104, 1109). Slip
  is measured on the contact point and travel on the foot centre. This
  does not affect the verdict.

**Other:**
- Full suites at `e4500356`:
  - `pixi run test-engine`: **2,509 passed, 60 skipped**.
  - `cli/tests`: **1 failed, 1,255 passed, 1 skipped**. The failure is
    `test_walk.py::test_the_same_walk_handles_a_linear_carriage`, run
    while session 2's product turn and its training run held the machine.
    Re-run alone at the same revision, it passed (28.6 s). Its failure
    output was not captured (tail only). No `cli/` file changed in this
    unit. Treat it as a load-sensitive test to watch, not as fixed: if it
    fails again, capture the traceback.
- No new dependency. pytest lives only in a `/tmp` venv.
- Unreconciled tail: 2 records (`windy-nest-5080` and this one).

Dispatch closed: 1 unit — walk round 4 published (0/10, stands still, transfer gap closed on the ADR-465 trainer), trainer_sha256 hashed at import (ADR-466, failing-first test), walk session 2 pre-registered with ADR-465 in its prompt and launched

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: e4500356890161d07f015b7195070754cabe048a

## State Impact

- target: smooth-fountain-9832 — walk round 4 r4-anglesonly (first on the ADR-465 trainer) fails 0/10 standing still (W5-steps 0, W8-high 1.0, W3 -0.004..0.088) with training reward now inside the engine's range; session 1 closed at 4 runs 0/10, 8,357 GPU-s; session 2 (<=3 runs, prompt states ADR-465) pre-registered and running; open trust question: W10 fails at rest (feet -8.2..-12.7 mm), unmeasured cause
- target: late-pond-2851 — fixed: trainer_sha256 is hashed once at import (ADR-466), regression test fails on the save-time hash; venv 74 passed
