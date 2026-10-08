---
node_id: f1dca22c-fd1c-50f1-970f-f49cef758193
slug: grand-otter-5246
title: C1. Closing report
created_at: '2026-10-07T17:58:14+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run orun5: **C1. Closing report.** The human owns the checkbox; roles report results and do not tick it [rec: honest-bay-2056].

- `docs/probes/orun5/REPORT.md` covers: [rec: honest-bay-2056]
  - each capability, with a still or a plot showing it work; [rec: honest-bay-2056]
  - P1's and P2's results, with their numbers, and P1's hero if it
    passed; [rec: honest-bay-2056]
  - the base-guidance rules added, and the ledger
    (`docs/probes/orun5/LESSONS.md`) of every workaround in the
    reference projects and what replaced it; [rec: honest-bay-2056]
  - every ADR the run added; [rec: honest-bay-2056]
  - the remaining defects. [rec: honest-bay-2056]
- Reconcile, then claim done for critic review without ticking the owner
  boxes. [rec: honest-bay-2056]

**Written; done claimed for critic review, owner boxes unticked** [rec: still-arrow-7544]. `docs/probes/orun5/REPORT.md` (commit `a7e8185d`) covers every item above:

- A figure per capability: S1, S2, L1 and R1 new plots from `docs/probes/orun5/capability_figures.py`, which replays each test's own fixture through Cadex's build, export, observation and evaluation code; M1 reuses `m1-rock-vs-circle.png` [rec: still-arrow-7544] [rec: dusty-canyon-3027]. Measured: S1 worst error 0.24 mm through a ±160° turn at 20° tilt; S2 reading saturates on the stall line below the 1816 N·mm gravity load; L1 rocker-tip error 0.0025 mm and closure residual 0.0012 mm against a 0.01 mm contract; R1 a held goal measures 0.0 mm and 316.2 mm, mirroring a world goal [rec: still-arrow-7544].
- P1 centring 8/8 with its hero, and the circle half on the charter's *otherwise* branch; P2 11.5 mm 7/10 against 23.6 mm 2/10, improvement not attributed; L1's fit sweep refuses a loop rather than solving it [rec: still-arrow-7544].
- The ADR-596 rules, ADRs 587–597, eleven remaining defects, and the ledger `LESSONS.md` W1–W12. Since ADR-597 (W7 replaced, success spec revisable by a declared curriculum step) the ledger reads ten replaced, one kept, one open (W12); REPORT §9 and §10 item 1 updated to match [rec: still-arrow-7544] [rec: chilly-hill-6548].
- The two defects carried from orun4 (checkpoint stall, "not found" before the first script) are reported as fixed by orun4's ADR-576 and ADR-575 and not re-measured this run, rather than called open or fixed [rec: still-arrow-7544].

The charter's "reconcile, then claim done" step: the done claim was made before the reconcile because work iterations may not reconcile; this pass folds `dusty-canyon-3027`, `still-arrow-7544` and `chilly-hill-6548`, so the claim now stands on a reconciled state. Maintainer judgement: status `working`, not `done` — the human owns the checkbox, and roles do not tick it [rec: still-arrow-7544] [rec: chilly-hill-6548].

## Negative knowledge

None yet.

## Provenance

- honest-bay-2056 — operator-declared orun5 charter gap (gap-c1-closing-report-docs-probes)
- still-arrow-7544 — REPORT.md written with a figure per capability; done claimed for critic review, owner boxes unticked
- chilly-hill-6548 — REPORT §9, §10 item 1 and ledger W7 updated for ADR-597; only W12 open
