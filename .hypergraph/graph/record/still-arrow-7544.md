---
node_id: 608dc20c-1a83-5311-bfd7-2445970076b3
slug: still-arrow-7544
title: 'C1: orun5 closing report, a figure per capability; done claimed for critic review'
created_at: '2026-10-08T02:26:45+00:00'
parents:
- dusty-canyon-3027
summary: ''
---
## What

Wrote orun5's closing report, `docs/probes/orun5/REPORT.md`, in commit `a7e8185d`. It has a figure for each capability:
- S1, S2, L1 and R1 are new plots from `capability_figures.py`, which replays each test's own fixture through Cadex's real build, export, observation and evaluation code;
- M1 reuses `m1-rock-vs-circle.png`.

The report also covers:
- P1's centring numbers and hero, and the circle result on the charter's *otherwise* branch;
- P2's numbers, with the attribution caveat;
- the ADR-596 rules, the ledger, and ADRs 587–596;
- eleven remaining defects.

Fixed the critic's ledger mismatch: W5 now says 3–11 laps, matching `dusty-canyon-3027`.

## Why

The critic named this unit: fix W5, then write C1. C1 is the last open charter criterion. Every other criterion already has evidence recorded.

**Deviation:** the critic asked me to reconcile after the report. This dispatch forbids reconciling in a work iteration, so I did not. The tail is now two records, `dusty-canyon-3027` and this one. The done claim is in the report and below, and it waits for the reconcile pass.

## Method

- **W5.** Read the circle evaluations in `orun5-ball-plate/evaluations/*/evaluation.json`. On every seed that ran to the horizon, laps were 3–11, and circle-1 ran 10–11. Circle-5's two early-ended seeds measure 0. The W5 row now says exactly that.
- **Figures.** `capability_figures.py` imports the test modules' fixtures, after the conftest stub. Each figure sweeps what its test checks at a few points:
  - **S1:** a plate turning ±160° at a 20° tilt, and a ball pushed past the 90 mm edge.
  - **S2:** servo stall torque swept from 200 to 3000 N·mm under a held load.
  - **L1:** the four-bar driven 447° at a 0.5 ms step, against the analytic rocker angle.
  - **R1:** the drifting-base trace through `CadexEvaluation.reach_metrics`.

  All are on the dark floor. Each PNG is 31–53 KB.
- **Numbers.** Taken from the run's records and the projects' evaluation files.
- **The two defects the charter carried from orun4.** Both were checked against orun4's report:
  - the checkpoint stall: orun4's ADR-576 already fixed it, and this run did not re-measure it. P2's checkpoints landed evenly, 69–72 s apart, over 3903 s for 1400 iterations, but the progress file keeps no per-iteration times.
  - "not found" before the first script: orun4's ADR-575 already fixed it, and no orun5 project exercised it.

  The report says this rather than calling either defect open or fixed.

## Result

**True now:**
- `docs/probes/orun5/REPORT.md` exists and covers S1, M1, S2, L1, R1, P1, P2, the ADR-596 rules, the ledger (W1–W12: 9 replaced, 1 kept, 2 open, W7 and W12), ADRs 587–596 and the defects.
- Measured in the figures:
  - S1: worst error 0.24 mm through the turn and tilt;
  - S2: the reading saturates on the stall line below the 1816 N·mm gravity load;
  - L1: rocker tip error 0.0025 mm, closure residual 0.0012 mm, against a 0.01 mm contract;
  - R1: a held goal measures 0.0 mm and 316.2 mm, mirroring a world goal.
- **Gates:** only docs and a probe changed. `test_project_docs.py`, `test_licensing_compliance.py` and `test_agent_guidance.py`: 40 passed, 1 skipped, plus 22 passed, 1 skipped. The full suites were not rerun, because no engine or CLI code changed.

**Done claim:** every charter criterion (S1, M1, S2, L1, R1, P1, P2, C1) now has evidence recorded. The terms are stated in the report:
- P1's circle half is on the *otherwise* branch;
- P2's improvement is not attributed;
- L1's fit sweep refuses a loop rather than solving it.

No owner box is ticked.

**Next:**
- The reconcile pass must fold `dusty-canyon-3027` and this record.
- The highest open rung after that is W7: decide the warm-start rule, with an ADR either way.

Dispatch closed: 1 unit — C1 closing report with S1/S2/L1/R1 figures, W5 ledger range fixed, done claimed pending reconcile

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun5
- commit: a7e8185d6a5e7cfeb3c719d2531e6e563bf928fd

## State Impact

- target: grand-otter-5246 — C1 evidence recorded (commit a7e8185d): docs/probes/orun5/REPORT.md covers S1/M1/S2/L1/R1 each with a figure, P1 centring 8/8 and circle on the otherwise branch, P2 11.5 mm 7/10 vs 23.6 mm 2/10 unattributed, ADR-596 rules, LESSONS ledger, ADRs 587-596, eleven remaining defects; done claimed, owner boxes unticked
