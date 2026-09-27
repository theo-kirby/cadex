---
node_id: 58dfc260-2bfa-5cf5-b746-e50f471cf37c
slug: loyal-fountain-8709
title: A5. Unassisted designs meet the bar on more than one body plan
created_at: '2026-09-27T15:18:35+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run ot10: **A5. Unassisted designs meet the bar on more than one body plan.** - Frozen cold prompts for a hexapod, a quadruped and one body plan of the run's choosing, with frozen flags, each get one design-only product turn on a new `ot10-*` project. - Every design is accepted with zero failing static fit checks and a complete, passing swept fit. - Every design carries its electronics, is rendered by A2, and is scored blind under A1's procedure. - Every design meets A1's bar, and each one scores above the hex3 baseline. - One failing design fails this criterion. Publish every attempt and every score. [rec: damp-dusk-8045]

Declared target: `gap-a5-unassisted-designs-meet-bar`. This node tracks the criterion as a gap; it becomes working only with causally parented, measured evidence that the criterion is met. The human owns the charter checkbox; roles report results and do not tick it. The directive's impact line is truncated; its wording is resolved from the full charter carried verbatim in the same record [rec: damp-dusk-8045].

- **Prompts frozen** (commit `13246076`): the hexapod prompt verbatim from hex1–hex3, a quadruped, and a biped; `claude-opus-5-5`, `CADEX_EFFORT=medium`, one turn each [rec: soft-spark-6990].
- **Attempt 1 fails the bar** — `ot10-hexapod-1`, revision `7af6db09`: judged blind **13/21 against a bar of 14** (medians T1 2, T2 3, T3 1, T4 1, T5 2, T6 2, T7 2; far above the hex3 baseline of 2), P1 0.078, **P2 0.655 FAIL**, P3 3, static fit clear, **swept fit incomplete at 12/12 FAIL**, electronics carried. The agent stripped caps, fillets and the sweep to fit the 300 CPU-s limit [rec: soft-spark-6990].
- **That limit was measured and mostly removed** (ADR-418, `d14f3b32`). `distToShape` over 1,035 pairs was 74–78% of accept wall time, and 32-CPU OCCT threading tripled its CPU-s charge (the accepted revision: 280 CPU-s unpinned, 94 pinned). With workers pinned to 4 CPUs, 15 of the turn's 19 CPU refusals now accept under the unchanged 300 CPU-s cap. Four (the first full assemblies, revisions 15–17, and the loft at revision 21) still exceed it on real exact-distance work, at ≥390 CPU-s single-threaded. The quadruped and biped attempts may proceed [rec: strong-summit-4135].

Status stays `open`: one design has failed, and this criterion fails if any design does [rec: damp-dusk-8045] [rec: soft-spark-6990].

## Negative knowledge

- [scope: ot10-hexapod-1, one design-only turn, before ADR-418 | confidence: high | evidence: soft-spark-6990, strong-summit-4135] Under a host-dependent CPU cap, the agent meets the budget by deleting the design language's refinements (caps, fillets) and skipping the swept fit. The score then drops on exactly the traits A5 is judged on. A refusal about budget costs quality, not just time.

## Provenance

- damp-dusk-8045 — ot10 operator-declared charter gap
- soft-spark-6990 — A5 attempt 1: hexapod 13/21 blind (bar 14), P2 0.655 and swept fit fail; the CPU cap is the cause
- strong-summit-4135 — ADR-418: the cap was mostly thread overhead; 15 of 19 refusals now accept, 4 remain on real work
