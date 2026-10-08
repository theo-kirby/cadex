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
- The two defects carried from orun4 (checkpoint stall, "not found" before the first script) were reported as fixed by orun4's ADR-576 and ADR-575 and not re-measured; the second has since been measured (below) [rec: still-arrow-7544] [rec: forest-grove-6707].

- **Circle runs after the report** (REPORT §6, its table, the P1 status row, defects 1 and 11, ledger W5/W7): circle-6 (σ narrowed, rocks, laps 0 on 8/8), circle-7 (first use of ADR-597, warm from centring, 3–4 laps at 12–17 mm) and circle-9 (unsaturated doubled off-radius cost, 20.6–24.0 mm), all 0/8 on radius or laps. Defect 1 no longer says ADR-597 is unused. New **defect 12**: no channel carries time, so a phase-tracking reward cannot be written; the `phase` goal kind is designed there, not built. The report now lists twelve defects [rec: flat-hawk-9763] [rec: bold-wind-5086] [rec: damp-orchard-1989].

- **circle-10 and circle-11 in the report** (REPORT §6 paragraphs and tables, P1 status row, defect 11 now at 7/8; LESSONS W5): **defect 12 is resolved by ADR-598** (the `phase` goal kind, built) [rec: tidy-badger-2182] [rec: glad-valley-4220].
- **REPORT §10.3 closed by measurement**: the carried orun4 defect "not found before the first script" was re-measured end to end on a real `cadex mcp` and `cadex app` — a fresh project is listed and returns 200 at its agent's first tool call (0.11 s), never before; `docs/probes/orun5/fresh_project_probe.py` reproduces it. The checkpoint stall (§10.2) is the last carried defect still unmeasured; it needs the GPU and the machine lock [rec: forest-grove-6707].

The charter's "reconcile, then claim done" step: work iterations may not reconcile, so each done claim precedes its fold. This pass folds the three-record tail the REPORT's done-claim paragraph names (`tidy-badger-2182`, `glad-valley-4220`, `forest-grove-6707`); the claim again stands on a reconciled state. Maintainer judgement: status `working`, not `done` — the human owns the checkbox, and roles do not tick it [rec: still-arrow-7544] [rec: forest-grove-6707].

## Negative knowledge

None yet.

## Provenance

- honest-bay-2056 — operator-declared orun5 charter gap (gap-c1-closing-report-docs-probes)
- still-arrow-7544 — REPORT.md written with a figure per capability; done claimed for critic review, owner boxes unticked
- chilly-hill-6548 — REPORT §9, §10 item 1 and ledger W7 updated for ADR-597; only W12 open
- flat-hawk-9763 — REPORT §6, status row, defect 11 and ledger W5 updated with circle-6
- bold-wind-5086 — REPORT §6, defects 1, 11, new 12 (no time channel) and done-claim tail; ledger W5/W7 with circle-7
- damp-orchard-1989 — REPORT §6 circle-9 paragraph and table, defects 1 and 11, three-record done-claim tail; ledger W5/W7 with circle-9
- tidy-badger-2182 — REPORT §6 circle-10, status row, defect 11; defect 12 resolved by ADR-598; LESSONS W5
- glad-valley-4220 — REPORT §6 circle-11, status row and defect 11 at 7/8; LESSONS W5
- forest-grove-6707 — REPORT §10.3 closed: fresh project readable from first tool call (0.11 s); probe added
