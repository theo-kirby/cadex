---
node_id: 5caf58a6-0329-503c-bfda-f8dd7d85aa95
slug: early-bramble-6327
title: 'ot11 R1: r15-stiffspring-clearfoot published (row 27), first valid no-margin walk evaluation, fails 0 of 10; cli/tests 1271 passed on CPU while r16 trains'
created_at: '2026-10-01T10:44:03+00:00'
parents:
- true-tree-5366
summary: ''
---
## What

Published walk session 5's first round, `r15-stiffspring-clearfoot`, as run row 21 and evaluation row 27 of `docs/probes/ot11/REPORT.md`. The receipt is `retained/p5-quad-1-r15-evaluation.json`, plus the seed-1101 filmstrip and detail sheet (278 KB and 117 KB). It is the first walk evaluation on a model with no contact offset and ADR-469's 0.004 s spring, and it is **valid**. It **fails 0 of 10**. I also re-ran `cli/tests` with the GPU hidden: 1271 passed, 1 skipped (commit `01789834`).

## Why

R1 (`smooth-fountain-9832`) is the highest-ranked open criterion that a live session can move, and the critic's item (1) named this unit: evaluate a finished session-5 round, publish it with receipts and filmstrips, and run the void check. r15 ended at 06:19 local. The agent's own `evaluate` tool (the same code as `cadex evaluate`) scored it inside its turn, so I published that stored evaluation and did not re-run it.

**Deviation:** the critic also asked me to fold the 2 unreconciled records (`civic-key-7068`, `true-tree-5366`, and now this one). This dispatch forbids reconcile, `hypergraph update` and state writes in a work iteration, with no exceptions, so I did not fold them. The tail is now 3 records, which is at the charter's reconcile threshold. The next reconcile pass should take it.

The critic asked for `cli/tests` "once the GPU is free". The GPU was free for minutes only: the agent started `r16-alive10` mid-suite. To avoid a third breach of the one-job rule, I ran the suite with `CUDA_VISIBLE_DEVICES="" JAX_PLATFORMS=cpu`. A watcher confirmed that the only GPU occupant throughout was r16's trainer (pid 2676479, parent `cadex_cli.loop`).

## Method

- **Validity checks.**
  - `contact_offsets` is `[]` and the void list is empty (ADR-470).
  - The evaluated revision `bf664d9b` differs from the registered `8b7271f2` only in `policy_on` 0→1 and the policy line (walk_r14 → walk_r15 with its sha256). Revision 0082 is byte-identical to 0081.
  - The model sha (6cecfa2d) and the task sha (7d31a888) equal the trainer receipt's.
  - The spec block equals frozen `walk-spec-block.txt` (sha 487416af) except HIP_MM 96.7006 and WEIGHT_N 5.05069617762, which equal the rig.
- **Ledgers.** Regenerated with `runner/run_ledger.py` and `runner/eval_ledger.py` over the same project order as before: 21 runs, 20 attempts, 34,588.52 s supervised (walk 15 / 29,240.54 s); 27 evaluations, 12 judge scores.
- **REPORT.md.**
  - Run row 21, the totals and evaluation row 27.
  - A "how to read" bullet for row 27, a revision row for r15 (motivated by row 26, answered by row 27) and a failure bullet with the filmstrip link.
  - "Remaining defects": R1 now covers rows 13–27, and the rebuilt-model contact line now cites row 27's W10.
- **Test.** `cli/tests/test_ot11_report.py` counts bumped (21/20 runs, 27 evaluations, 20 revision rows, 23 failed).

## Result

What is true now:
- **r15 fails every seed, and worse than r14.**
  - Seeds 1101, 1102, 1105, 1106 and 1109 tip in 0.50–0.94 s (W1, W2). The filmstrip shows a roll onto its side.
  - Seeds 1103, 1104, 1107, 1108 and 1110 stand the full 10 s without one step on any foot: W5-steps 0, duty 1.0, slip 0.54–0.80, speed_ratio 0.03–0.06.
  - The training episode mean was 280 of 500 steps, and reward/step ended at −1.13.
- **W10 holds on the five seeds that stand** (−0.015 to −0.003 HH; a foot at most 1.45 mm under). On the new spring a loaded standing foot does not sink. W10 under a *stepping* load is still measured only by r14's policy driven on the rebuilt model (`p5-quad-1-rebuilt-depth.json`).
- **Session 5 continues.** The agent revised and started `r16-alive10` itself (06:3x local). Its evaluation is the next unit to publish.
- **Suites.** `cli/tests` 1271 passed / 1 skipped, on CPU. `test-engine` was not re-run, because nothing under `src/Mod/cadex` changed this iteration.

Concern: the tail is now 3 unreconciled records. A reconcile is due, and this iteration was not allowed to do it.

Dispatch closed: 1 unit — r15 (first valid no-margin walk round) published as row 27, failing 0 of 10 (half tip, half never step); cli/tests green on CPU while r16 trains.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 017898348106a6272c315d626bf43db99522691e

## State Impact

- target: smooth-fountain-9832 — walk session 5 round 1 (r15-stiffspring-clearfoot) is the first valid walk evaluation on the no-margin 0.004 s model (row 27, contact_offsets empty) and fails 0 of 10: five seeds tip within 0.94 s, five stand without stepping; W10 holds on the standing seeds (-0.015..-0.003 HH); r16-alive10 is training
- target: golden-bay-4173 — REPORT.md at 21 runs (20 attempts, 34,588.52 s) and 27 evaluations; cli/tests 1271 passed / 1 skipped at 01789834 (run CPU-only to keep the one-GPU-job rule)
