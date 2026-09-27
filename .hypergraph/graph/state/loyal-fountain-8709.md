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
- **Attempt 1 fails the bar** — `ot10-hexapod-1`, revision `7af6db09`: judged blind **13/21 against a bar of 14** (far above the hex3 baseline of 2), P1 0.078, **P2 0.655 FAIL**, P3 3, static fit clear, **swept fit incomplete FAIL**, electronics carried. The agent stripped caps, fillets and the sweep to fit the 300 CPU-s limit [rec: soft-spark-6990].
- **CPU limit mostly removed** (ADR-418, `d14f3b32`): 32-CPU OCCT threading tripled the CPU-s charge of `distToShape`; with workers pinned to 4 CPUs, 15 of attempt 1's 19 CPU refusals accept under the unchanged 300 CPU-s cap, and 4 still exceed it on real exact-distance work [rec: strong-summit-4135].
- **Hexapod attempt 2** — `ot10-hexapod-2`, launched detached at `6dd4ce81` (after ADR-418) [rec: late-glacier-7593]; accepted revision `996a0b7e` scored **14/21 median (meets 14)**, P1 0.022, P2 0.088, P3 3, static fit clean — but the agent turned the swept fit off after the 180 s `_SWEEP_TOTAL_SECONDS` budget ran out on the first hip at 63 components, so it **misses A5** [rec: quiet-basin-1176]. An earlier `ot10-quadruped-1` was killed 8 min in with no design; it is a harness stop, not an attempt [rec: late-glacier-7593].
- **Quadruped attempt** — `ot10-quadruped-2`, revision `27ba92c6`: **16/21 median (meets 14)**, P1 0.004, P2 0.238, P3 3, static fit clean, swept fit off (budget), so it also **misses A5** [rec: western-comet-0121].
- **The sweep now fits a 12-joint robot** (ADR-419, `f08f336b`): the joint sweep measures near moving pairs exactly, bounds far ones (>10 mm box gap, culled lower bound) and stops re-measuring rigid pairs. Replayed on `ot10-hexapod-2` it sweeps **12/12 joints in 112 s** of the 180 s budget (was 0/12; one hip 287 s → 7.3 s). The complete sweep then fails only on knee foot/tibia vs `c_floor` — an undecided policy question, not a measurement gap [rec: western-comet-0121].
- **Next (proposed):** decide, with a measured regression, whether a swept limb against the declared `c_floor` counts against the swept fit (the static block already treats floor rows as advisory); if it counts, no legged design passes unless its knee range clears the ground at stance. A second open concern: `printed_edges.measured` includes `c_floor`, and the quadruped's P2 of 0.238 sits just under 0.25, so correcting it is a frozen-proxy change needing a recorded re-score. No biped attempt is recorded, and no attempt has yet passed a complete swept fit [rec: western-comet-0121].

Status stays `open`: every scored design so far misses on the swept fit, and this criterion fails if any design does [rec: damp-dusk-8045] [rec: quiet-basin-1176] [rec: western-comet-0121].

## Negative knowledge

- [scope: ot10-hexapod-1, one design-only turn, before ADR-418 | confidence: high | evidence: soft-spark-6990, strong-summit-4135] Under a host-dependent CPU cap, the agent meets the budget by deleting the design language's refinements (caps, fillets) and skipping the swept fit. The score then drops on exactly the traits A5 is judged on. A refusal about budget costs quality, not just time.
- [scope: ot10-hexapod-2 and ot10-quadruped-2, before ADR-419 | confidence: high | evidence: quiet-basin-1176, western-comet-0121] When the swept fit's 180 s budget cannot cover a 12-joint robot, the agent turns the sweep off to get accepted — so judged quality can meet the bar while the fit criterion still fails.

## Provenance

- damp-dusk-8045 — ot10 operator-declared charter gap
- soft-spark-6990 — A5 attempt 1: hexapod 13/21 blind (bar 14), P2 0.655 and swept fit fail; the CPU cap is the cause
- strong-summit-4135 — ADR-418: the cap was mostly thread overhead; 15 of 19 refusals now accept, 4 remain on real work
- late-glacier-7593 — hexapod attempt 2 launched on ot10-hexapod-2 at 6dd4ce81; ot10-quadruped-1 a harness stop
- quiet-basin-1176 — hexapod attempt 2: 14/21 meets the bar, P1–P3 pass, swept fit off on budget → misses A5
- western-comet-0121 — ADR-419: 12/12 joints swept in 112 s; quadruped 16/21, swept fit off → misses A5
