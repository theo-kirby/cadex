---
node_id: 0f0e7c05-aecc-5a6b-99a8-9e851dc88aa0
slug: weathered-river-6058
title: 'ot11 R1: r17-discount-bodyrate published (row 29), valid, walks every seed, passes 1 of 10; session 5 closed'
created_at: '2026-10-01T12:18:47+00:00'
parents:
- civic-bluff-7621
summary: ''
---
## What

Published walk session 5's third and last round, `r17-discount-bodyrate`, as run row 23 and evaluation row 29 of `docs/probes/ot11/REPORT.md`. The receipt is `retained/p5-quad-1-r17-evaluation.json`, plus the seed-1101 filmstrip (177 KB) and detail sheet (223 KB), both on the dark floor. It is **valid** and **passes 1 of 10**. Seed 1108 is the first walk seed in ot11 to pass every predicate. I also added a revision row for r17 (motivated by row 28, answered by row 29), a failure bullet, and updated the R1 and W10 lines under "Remaining defects" (commit `b3bcdeb7`).

## Why

R1 (`smooth-fountain-9832`) is the open criterion. The critic named this unit: when r17 finishes, publish it the way r15 and r16 were published, wait inside the iteration, start no GPU job, and don't tune the reward or task. Then check two things: whether tips come before or after the shove, and whether any foot steps 4 times. Also say whether this is the first W10 measurement under a sustained stepping load. I did all of it. The critic also wrote that "the current bet is banned". The same message names this unit as next, and it serves R1 (a charter criterion), so I followed the named unit. I wrote no bet, because writing bets belongs to the planner.

## Method

- **Waited inside the iteration.** Training ran from 07:08 to 07:42 local: 760 iterations, finished, policy `63cbf224`. The agent's own `evaluate` tool wrote `evaluations/50b2a42caf1c-63cbf22407c0` at about 07:48. I published that stored evaluation and re-ran nothing.
- **Validity checks:**
  - `contact_offsets` is `[]` and no seed is void.
  - Revision 0090 `50b2a42c` is byte-identical to 0089. 0089 differs from the registered 0088 `66372fc3` only in the policy line (walk_r16 → walk_r17, with its sha256).
  - The model sha `6cecfa2d` equals the trainer receipt's. The task sha `c1a3ad33` equals both the trainer receipt's and the registration's.
  - The spec block (script lines 354–383) equals the frozen `walk-spec-block.txt` (sha `487416af`) except WEIGHT_N 5.05069617762, which equals the rig.
- **Ledgers.** Regenerated with `run_ledger.py` and `eval_ledger.py` over the same project order: 23 runs, 22 attempts, 38,743.05 s (walk 17, 33,395.07 s); 29 evaluations, 12 judge scores. Nothing was in progress.
- **Diagnosis.** Read the per-seed metrics, the per-foot step counts, terminations, shove times and reward per step from `evaluation.json`. The agent's own closing summary was read from the session 5 transcript (outside the repo).
- **Tests.** Bumped the counts in `cli/tests/test_ot11_report.py`. Ran the full `cli/tests` with `CUDA_VISIBLE_DEVICES="" JAX_PLATFORMS=cpu`.
- **Correction.** The previous discount was the trainer default, 0.97, not the "~0.99" in the agent's reason. The revision row says 0.97 → 0.995.

## Result

What is true now:
- **r17 walks.** All ten seeds run the 10 s horizon. **No seed tips, before or after its shove** (shoves at 3.39–6.53 s). Tilt is 12.4–17.2° (W2 ≤ 30) and speed_ratio 0.90–0.98.
- **The two failures that persisted across rounds are gone.** On W5-steps, every foot steps 5–14 times on every seed (min 4), where r16's maximum was 1. W1/W2 tipping passes 10 of 10, where r16 tipped on 8.
- W3, W4, W6 (clearance 0.15–0.22 HH), W8 (duty 0.48–0.61) and W10 pass on every seed.
- **Seed 1108 passes all 13 predicates.** The other nine fail on:
  - **W7 slip**, on 8 seeds: 0.154–0.208 against 0.15. Several seeds are just over the line (0.154–0.162).
  - **W9 leg balance**, on 8 seeds: 1.4–2.4 against 1.5. The rear feet take 10–14 steps to the front feet's 5–11.
  - **W5-share**, on 2 seeds (1101 at 0.69, 1109 at 0.57, against 0.70). These are the two seeds with the fewest front steps (5).
- **W10 under a sustained stepping load is measured for the first time on a policy trained on the no-margin 0.004 s model.** Every foot steps 5–14 times, and the deepest foot point is −0.0172 to −0.0129 HH (1.25–1.66 mm under) against −0.05. W10 holds 10 of 10.
- **Session 5 is closed at its three-run limit** (rows 27–29). No confirmation is registered, because no round passed every seed. The agent's turn ended and its declared policy is r17. The agent's stated next revision is a warm start from r17 with `slip_w` 1.5 → 2.0 and a bounded cost on diagonal touchdown-rate mismatch, aimed at W7/W9/W5-share. That is the agent's design, not mine. Running it needs a session 6 pre-registration (actor work: prompt, driver args, limits), and that is the natural next unit.
- **Suites.** `cli/tests`: 1271 passed, 1 skipped (CPU-only, at `b3bcdeb7`). `test-engine` was not re-run because nothing under `src/Mod/cadex` changed. No GPU job is running.
- **Tail.** Two unreconciled records (civic-bluff-7621 and this one).

Dispatch closed: 1 unit — r17-discount-bodyrate published as row 29: valid, no tips, every foot steps 5–14 times, 1 of 10 seeds pass (1108), nine fail on W7 slip and W9 rear-heavy stepping; W10 holds under sustained stepping; session 5 closed.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: b3bcdeb7f11d818048bbd439e2568807a3c104c9

## State Impact

- target: smooth-fountain-9832 — walk session 5 round 3 (r17-discount-bodyrate, row 29) is valid (contact_offsets empty) and passes 1 of 10 (seed 1108, the first walk seed to pass): no seed tips, every foot steps 5-14 times, W3/W6/W8/W10 pass on all ten; nine seeds fail W7 slip (0.154-0.208) and W9 rear-heavy stepping (1.4-2.4), two W5-share; W10 holds under a sustained stepping load (-0.0172..-0.0129 HH); session 5 closed at its three-run limit with no confirmation registered
- target: golden-bay-4173 — REPORT.md at 23 runs (22 attempts, 38,743.05 s) and 29 evaluations; cli/tests 1271 passed / 1 skipped at b3bcdeb7 (CPU-only)
