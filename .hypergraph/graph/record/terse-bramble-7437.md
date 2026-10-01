---
node_id: a92a4004-4f2a-517f-ba28-49da2d67f173
slug: terse-bramble-7437
title: 'ot11 R1 walk round 10 published: r11-speedpay valid, 0/10, rocks in place to farm speed pay, W10 holds; walk session 3 closed; C1 ledgers 17 runs/23 evals'
created_at: '2026-10-01T06:09:43+00:00'
parents:
- shady-pond-5657
summary: ''
---
## What

Published walk round 10 (`r11-speedpay`) on `ot11-quad-1`, closed walk session 3, and moved C1's ledgers and REPORT.md with them (commit `e8d99999`).

- `docs/probes/ot11/retained/p4-quad-1-r11-evaluation.json`: round receipt (registration, warm-start check, end, checkpoints with recorded trainer sha, curve, spec-block check, evaluation summary, per-foot table, per-term reward over 10 seeds, motion metrics, a per-seed `rocking` reconstruction, train/eval transfer). Filmstrips `p4-quad-1-walk-r11-seed-1101-{overview,detail}.png` (290 KB, 246 KB; dark floor).
- `retained/p4-quad-1-s3-rounds.json`: the session-3 driver summary, paths made project-relative.
- README sections "Walk round 10" and "Walk session 3 closes at 0 of 10 over three runs".
- Regenerated `retained/ot11-runs.json` (17 runs, 16 attempts, 25,968.49 s, none in progress) and `retained/ot11-evaluations.json` (23 evaluations, 12 judge scores; only the r11 row added). REPORT.md: run row 17, walk 11 runs / 20,620.51 s, eval row 23 with a validity bullet, revision row `r11-speedpay`, "Nineteen of 23", 16 attempts in 17 runs, a session-3 failure bullet. `test_ot11_report.py` pins moved (17/23/16/19).

## Why

The critic's message: publish r11 under r10's validity checks (HIP_MM/WEIGHT_N vs rig, spec block tokenized vs the frozen one, revision differing only in the policy line, warm start allowed under P4), regenerate both ledgers and REPORT.md, report W3/W5/W8 per seed plus the per-foot table, and, since r11 is session 3's last run and failed, state what the session measured as a whole before any session 4. The agent had evaluated r11 (`evaluations/bfb59bb5d902-f35fefd6a569`), so I did not evaluate it. Serves R1 (smooth-fountain-9832) and C1 (golden-bay-4173).

## Method

- Revision: script_history 0059 (9bc79371, registered) vs 0061 (bfb59bb5, evaluated; 0060 identical text): `diff` shows only the `assembly.policy` line.
- Warm start: r10 and r11 `model-model.xml` both sha 5e28d393; a structural diff of the two task bundles shows three fields only (speed_track expression width 0.4->0.6 and weight 2->4, speed_error weight -1->-2). The trainer accepted it (it refused r9's across a model change). Allowed.
- Spec block from 0061 tokenized against `retained/walk-spec-block.txt` (comments dropped): one token differs, WEIGHT_N's value. HIP_MM 96.7006 = rig 96.7006 (4 dp); WEIGHT_N 5.05069617762 = rig 5.050696177620001 (11 dp). Valid.
- Checkpoints 100..700 and final record trainer 97bc1d9a (= current `training/cadex_train.py`).
- Rocking: tray x velocity by finite difference of the trace's 50 Hz frames over the seed's command, all ten seeds; reconstructed speed_track pay compared to reported.
- `pixi run python -m pytest` over the ot11/loop/goal/success-spec suites (cli/tests test_ot11_*, test_loop, test_review_evaluation; cadex_tests goal trainer, mjx forcelimit, success spec model): 90 passed. Full suites not rerun (no product code changed; last full cli/tests 1268 passed in shady-pond-5657).

## Result

- **r11 is a valid evaluation and fails 0 of 10.** Per seed: W3 speed_ratio 0.015–0.033 on all ten (limit 0.75–1.25); W5-steps 0 and W5-share 0.00 on all ten; W8-low 0.00 and W8-high 1.00 on all ten. W1, W2 (9.3–11.8°), W4 (heading 9.5–12.4°, up from 0.5–2.8°) and **W10 (−0.043..−0.026 HH) pass on all ten**. Per foot over ten seeds: FL 0–1 steps, duty 0.92–0.97; FR 0 steps, duty ≥0.996, slip 0.77–0.83; RL 0, duty 1.00; RR 0 steps, duty 0.00, held at +6.0..+6.2 mm on every seed.
- **The stronger speed term did not produce steps; it was farmed by rocking.** speed_track pays +1.0..+1.65/step (rest would earn +0.25; r10 earned +0.03). Tray v/command: median −0.04..+0.18, sd 0.47–0.84, 17–36 % of the episode above +0.5 and 16–28 % below −0.5; the tray reconstructs 0.81–1.39 of the reported pay (COM vs tray gap). The agent's closing turn reached the same diagnosis and proposes a convex (squared-error) speed cost and swing pay gated on body progress; untrained.
- **Session 3 as a whole** (r8, r10, r11; r9 refused; 6,284.29 s GPU; 1 turn, 8,807 s, 65 tool calls): the mechanism lever fixed W10 (steel-ball feet pass every seed of both rounds; stance alone did not); no round produced a step (W5 worst foot 0, W8-low 0.00 in all three) whereas session 2's light-foot rounds 5–7 had stepped; each reward found a different stationary optimum (r8 held a diagonal pair up for trot pay, r10 stood on three feet under alive 3.5, r11 rocked for a concave speed Gaussian), each diagnosed from the previous evaluation's reward terms and confirmed by the next. Not measured: whether 10.5 g feet make stepping harder on MG90S legs, and W10 under a real gait on steel feet. R1 stands at 0 of 10 over rows 13–23.
- No session 4 is registered. Ledgers: 17 runs, 16 attempts, 25,968.49 s; 23 evaluations.
- Tail: 3 unreconciled records after this one; the critic asks for a reconcile next.

Dispatch closed: 1 unit — r11 published as a valid 0/10 walk evaluation (no steps; speed pay farmed by rocking in place; W10 holds); session 3 closed with its whole-session measurement; C1 ledgers and REPORT.md at 17 runs / 23 evaluations

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: e8d999998c4d9e99423e50eaebad378d22809031

## State Impact

- target: smooth-fountain-9832 — round 10 (r11-speedpay, reward-only, warm from r10) is a valid evaluation, 0 of 10: no foot steps (W5 0, W8-low 0.00, RR held up), W10 still passes (−0.043..−0.026 HH); the doubled concave speed Gaussian was farmed by rocking in place (+1.0..+1.65/step vs +0.25 at rest). Session 3 closed at 0/10 over r8, r10, r11: steel feet fixed W10, no round stepped; no session 4 registered
- target: golden-bay-4173 — ot11-runs.json 17 runs/16 attempts/25,968.49 s, none in progress; ot11-evaluations.json 23 evaluations; REPORT.md and test_ot11_report.py pinned to both; session-3 rounds receipt retained
