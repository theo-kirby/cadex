---
node_id: 151be632-c20a-5d93-b1cc-89f2fd08728e
slug: deep-moss-5363
title: 'ot11 R1: r20-contact35 published (row 32), valid, 0 of 10; contact_w 3.5 fixed 1109''s W9 and broke slip; refused r21 is run row 27'
created_at: '2026-10-01T15:30:24+00:00'
parents:
- scarlet-cove-2359
summary: ''
---
## What
Published walk session 7's first round, `r20-contact35`, the same way as r19: validity check, receipt with a regression diagnosis, filmstrip, both ledgers regenerated, REPORT rows, and report-test counts. Run row 26, evaluation row 32. It is valid and fails **0 of 10**. Also published the refused start `r21-r19-continue` (run row 27, `attempt: false`). `r21b-r19-continue`, session 7's third and last run, is training under the session's supervisor.

## Why
The critic's message named this: check session 7's supervisor, and if r20 has a product evaluation, publish it as r19 was. It moves **R1** (`smooth-fountain-9832`), a charter criterion with its own frontier node, not the banned plan bet (moving clearance), and C1's report (`golden-bay-4173`).

**Not done as asked: the fold.** The critic asked me to fold the two unreconciled records (brisk-ember-6734, scarlet-cove-2359) into R1 and C1. This dispatch's own rules forbid the reconcile skill and state writes in a work iteration, "no exceptions". So I did not fold. The tail is now 3 unreconciled records, which meets the charter's "three unreconciled records" reconcile trigger. The next pass should be the reconcile.

**Blocked criteria, one line each (critic asked):**
- None is blocked.
- R1 is at 9 of 10 (row 31) and moving.
- P1–P4, R2 and R3 have published evidence (r2-confirm-1 and r3-confirm-1 pass 10 of 10) and wait on owner review, not on work.
- C1 waits on R1.

## Method
- **Supervisor.** rounds.py (pid 3241880) is alive. The r20 supervisor ended `finished`, 700/700, 1,913.86 s supervised and 1,765.67 s by the trainer. The agent's own `evaluate` ran at 14:42:35Z, report `evaluations/f924ce70604e-4a341e7b3047`. The actor ran no evaluation.
- **Validity.**
  - `contact_offsets` is `[]` and no seed is void.
  - The model sha `6cecfa2d` equals the trained model and r17–r19's.
  - The task sha `fb3a3d7f` equals the trained `walk_task-task.json` and the trainer receipt. The policy sha `4a341e7b` equals the status file and the receipt.
  - The rig is HIP 96.7006 and weight 5.05069617762.
  - The spec block in script_history 0101 is identical to r19's evaluated block (0098). Against the frozen `walk-spec-block.txt` (sha 487416af) it differs only in the HIP and WEIGHT value lines.
  - Revision chain: 0098 → 0099 is byte-identical source. The agent's change is `contact_w` 3.5 as a parameter value in `script.json`, which is why the revision hash moved. 0099 → 0100 is the policy line only. 0101 is identical to 0100.
- **Receipt** `docs/probes/ot11/retained/p7-quad-1-r20-evaluation.json`, schema `ot11-walk-round-receipt-v1`.
  - Its evaluation block comes from a builder that I first checked against r19's committed receipt: it reproduced that block key for key, with no diff.
  - The script asserts the hash and offset checks.
- **Ledgers** regenerated with `run_ledger.py` (27 runs, 25 attempts, 1 in progress, 44,301.93 s) and `eval_ledger.py` (32 evaluations, 12 judge scores).
  - Row 31's `written_at` moved, because session 7's agent re-evaluated r19 under the same key.
  - Every other number in row 31 is unchanged, and the r19 receipt block still reproduces exactly. The REPORT says so.
- **Filmstrip.** The product rendered seed 1101. Overview 174 KB and detail 231 KB, both on the dark floor (checked visually).
- **REPORT.md.**
  - Run table rows 26 and 27, plus totals: walk 21 runs, 38,953.95 s.
  - The intro now reads 27 runs / 25 attempts / 2 refused. The warm-start list, the in-progress note and the trainer-time sentence are updated: "sixteen walk runs", recomputed at 148–202 s.
  - Evaluation row 32 and its "Row 32" reading, a revision row, failure items (r20, and the refused r21), and the R1 remaining-defects text.
- **Tests.** `cli/tests/test_ot11_report.py` counts were moved (27 runs, 32 evaluations, 25 revisions, 28 failed, two refused). Full cli/tests, CPU-only (`CUDA_VISIBLE_DEVICES=`): 1272 passed, 1 skipped (18 min 38 s).

## Result
- **r20 is valid and fails 0 of 10** (row 32). Raising `contact_w` from 2.0 to 3.5 did what it was meant to on seed 1109 (W9 1.571 → 1.333), but broke slip on all ten seeds:
  - W7 0.156–0.270 against 0.15 (r19: 0.090–0.125). On every seed the foot that slips most is rear-left; the other three feet are at 0.09–0.18.
  - Steps fell to 5–9 per foot (r19: 7–14) and tilt rose to 25.0–28.7° (r19: 7.9–22.9°).
  - 1101 now fails W9 (1.600). W5-share fails on 3 seeds and W8-low on 1. No seed tips.
- **The warm start did not carry r19's gait.** Iteration 1 reads −2.03 reward per step against r19's final 4.47. It reached 1.45 by iteration 50 and ended at 3.56 (best 3.67 at iteration 696), so the run relearned a gait rather than refining one.
- The agent read r20 the same way ("knocked off r19's gait") and registered `r21-r19-continue`: r19's task unchanged, warm from r19, 750 iterations, seed 211.
- **r21 was refused before iteration 0.** It passed `--init-from-task-change` on a byte-identical bundle, which the trainer refuses. It is published as run row 27, `attempt: false`.
- `r21b-r19-continue` (the same settings without the flag) was registered at 15:07:33Z with a 2,350 s budget, so it will end by about 15:47Z. It is the session's third and last run.
- **Concern: the driver counts a refused start as a spent run.** rounds.py counts a policy-less `train_ended` as settled, by design (scarlet-cove-2359). Session 7 therefore trains two policies, not three.
  - This is consistent with the pre-registration ("ended with no policy" counts), so I did not change the driver mid-session.
  - It does disagree with the REPORT's "a refused start is not an attempt". A session 8 driver should not count `attempt: false` ends, and that change has to be pre-registered.
- **Handoff, for the different model taking the next turn.**
  - What I tried: publication of r20 and r21 as above.
  - Next:
    1. Reconcile; the tail is at 3.
    2. When r21b's `evaluated` row lands, publish it the same way: the validity checks, the builder in this record's Method (reproduce r19's block first), the ledgers, the REPORT rows and the test counts, with CPU-only cli/tests while any GPU job runs.
    3. If r21b passes 10 of 10, check the judge's bar, then pre-register and commit an R1 confirmation evaluation before running it. A 10 of 10 is not a pass until the confirmation and the judge both hold.
    4. If it fails, session 7 is over at 3 settled runs. A session 8 needs a pre-registered driver change, so that refused starts do not spend a round.
  - Monitor gotcha: a ledger `evaluated` row has `"at"` *before* `"kind"`, because the keys are sorted. My first watcher grepped them in the other order and missed the row.
- No new dependency. Nothing under `src/Mod/cadex`, `cli/cadex_cli` or `training/` changed. The GPU is held by r21b.

Dispatch closed: 1 unit — r20-contact35 published (run row 26, evaluation row 32): valid, 0 of 10, contact_w 3.5 fixed 1109's W9 but broke slip on all ten (rear-left); refused r21 published as row 27; r21b training as session 7's last run

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: dccb238272444de151edc4cb301f8e78c1327119

## State Impact

- target: smooth-fountain-9832 — r20-contact35 (run row 26, evaluation row 32, commit dccb2382) is valid on the no-margin 0.004 s model and fails 0 of 10: contact_w 2.0 -> 3.5 passed seed 1109's W9 (1.333) but broke slip on all ten (W7 0.156-0.270, rear-left worst on every seed), and the warm start did not carry r19's gait; r21-r19-continue was refused before iteration 0 (run row 27, attempt false); r21b-r19-continue is training as session 7's last run, because the driver counts a refused start as settled. r19 (9 of 10) is still the best round; no confirmation registered
- target: golden-bay-4173 — REPORT.md carries 27 runs (25 attempts, 2 refused, 44,301.93 s GPU) and 32 evaluations, with r20's receipt, filmstrip and revision row; cli/tests CPU-only 1272 passed, 1 skipped
