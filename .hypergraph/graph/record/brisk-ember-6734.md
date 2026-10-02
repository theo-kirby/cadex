---
node_id: 2d034300-b428-52cb-ae0d-05bfc0063592
slug: brisk-ember-6734
title: 'ot11 R1: r19-contact-sync published (row 31), valid, passes 9 of 10; W9 on the slowest command; session 6 closed after two rounds'
created_at: '2026-10-01T14:16:14+00:00'
parents:
- round-crane-1720
summary: ''
---
## What
Published walk session 6's second round, `r19-contact-sync`, in the same way as r18. That covers the validity check, a receipt with its W9 diagnosis, the filmstrip, both ledgers, the REPORT rows and the report tests. Run row 25, evaluation row 31. The round is valid. It passes **9 of 10** seeds, the best walk round in ot11, and it fails only W9, on seed 1109. Session 6 is closed.

## Why
The critic named this unit: publish r19 when it finishes, the same way as r18, and diagnose W9 from its numbers. It moves R1, the highest-ranked open behaviour criterion, which has its own frontier node (`smooth-fountain-9832`). The critic also said the old plan bet (moving clearance) is banned. This unit is not that bet. Its criterion is R1. The critic asked for the plan view's six pending impacts to be folded "while the GPU is busy". A work iteration is forbidden to reconcile, so I did not fold them. They are left for the next reconcile pass.

## Method
- Waited for the trainer to exit (750/750 iterations, finished, 2,010.27 s supervised, 1,861.1 s trainer) and for the agent's own `evaluate` call (ledger row `evaluated` at 13:45:58 UTC, report `evaluations/35122157a90f-de546ddd91e1`). The actor ran no evaluation.
- Validity:
  - `contact_offsets` is `[]` and no seed is void.
  - The model sha `6cecfa2d…` equals the trained model and r17's and r18's.
  - The task sha `db670704…` equals the trained task and the registered one.
  - rig: HIP 96.7006 and weight 5.05069617762 N, matching the block.
  - The spec block in script_history 0098 is byte-identical to r18's evaluated block (0094), which differs from the frozen `walk-spec-block.txt` only in the HIP/WEIGHT value lines.
  - Revision diff: 0095→0096 is the registered change (the `contact_w` param, plus `contact_sync` replacing `sink`). 0096→0097 is the policy line only (walk_r18→walk_r19 with its sha). 0097→0098 is byte-identical.
- Receipt `docs/probes/ot11/retained/p6-quad-1-r19-evaluation.json`: the same schema as r18's, plus per-seed step counts and per-term reward ranges. Built by a throwaway script, which asserts the hash and offset checks.
- Ledgers regenerated with `runner/run_ledger.py` and `runner/eval_ledger.py`. I checked first that both reproduce the committed receipts exactly, apart from r19 shown as in progress.
- Filmstrip: the product rendered seed 1109, the failing seed, so that one is committed: overview 169 KB and detail 226 KB, both on the dark floor.
- REPORT.md: a run row, an evaluation row, a "Row 31" reading, a revision row, two failure items and the remaining-defects text. `cli/tests/test_ot11_report.py` counts were moved by one.
- cli/tests, CPU-only (`CUDA_VISIBLE_DEVICES=`): 1271 passed, 1 skipped (18 min 22 s).

## Result
- **r19 is valid and passes 9 of 10** (row 31). No seed tips. W1–W8 and W10 pass on all ten: slip 0.090–0.125, tilt 7.9–22.9°, speed_ratio 0.93–1.00, clearance 0.28–0.32 HH, duty 0.45–0.59, W10 −0.022 to −0.013 HH. W9 drops from 1.56–2.33 (r18) to 1.18–1.57.
- **W9 diagnosis: it follows the commanded speed.** Seed 1109 has the lowest command (0.628 HH/s) and the highest ratio, 1.571 against 1.5. 1101 has the next-lowest command (0.647) and the next-highest ratio (1.333). The other eight are 1.18–1.30. At 1109's command the front feet swing for 0.57–0.60 s and step 7 and 8 times, while rear-left keeps a 0.36 s swing and steps 11 times. On every seed the rear feet take shorter steps (median advance 44–71 mm against the front's 56–83 mm), and rear-left takes the most steps on 7 of 10. 1109's shove is the smallest (0.31 N), so the shove does not explain it. The agent's own closing note reached the same reading: train slow commands more, or raise `contact_w`. It would not change the mechanism.
- **Session 6 trained 2 runs, not the 3 it registered.** `rounds.py`'s `over()` counts the project ledger's `evaluated` rows against `--max-runs 22`. The agent re-evaluated r17 at 12:24 UTC, which is the 20th evaluated row, so r19's evaluation was the 22nd. The driver then stopped after turn 1 and never ran turn 2. This is recorded in REPORT *Every failure*. The pre-registration's "three runs" was therefore one run more than the driver allowed. The next session's driver args must count that, or count `train_ended` rows instead of evaluations. That is a driver change, so it needs to be pre-registered.
- No round has passed 10/10, so no confirmation is registered. R1 is not met.
- The GPU is free and no ot11 job is live, which means `src/Mod/cadex` is no longer frozen by session 6.
- The next unit is to pre-register walk session 7 on ot11-quad-1 with r19 declared (9 of 10), giving the agent r19's measurements and the W9-vs-command reading as a measurement, not as an instruction.
- Concern: the plan view `young-crane-9546` still carries six unfolded pending impacts (the critic's note), and its short bet is stale. That belongs to the next reconcile.
- No new dependency.

Dispatch closed: 1 unit — r19-contact-sync published (run row 25, evaluation row 31): valid, 9 of 10, W9 on seed 1109 traced to the lowest commanded speed; session 6 closed after two rounds

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 69f75709fdc0b793a8cfdafd77b15f19810ee83b

## State Impact

- target: smooth-fountain-9832 — r19-contact-sync (run row 25, evaluation row 31, commit 69f75709) is valid on the no-margin 0.004 s model and passes 9 of 10, the best walk round yet: no tips, W1-W8 and W10 on all ten, W9 1.18-1.57 failing only seed 1109 (1.571) at the lowest commanded speed (0.628 HH/s), where the front feet slow their cadence and rear-left does not. Session 6 closed after two rounds (the driver counts evaluations, and the agent re-evaluated r17). No round has passed 10/10; no confirmation registered
- target: golden-bay-4173 — REPORT.md carries 25 runs (24 attempts, 42,335.79 s GPU) and 31 evaluations, with r19's receipt, filmstrip and revision row; cli/tests CPU-only 1271 passed, 1 skipped
